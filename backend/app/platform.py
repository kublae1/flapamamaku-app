import asyncio
import os
import secrets
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from .platform_store import audit, connect, create_invoice, hash_token, init_db, make_password, now_iso, run_billing, verify_password

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
SESSION_DAYS = max(1, min(90, int(os.getenv("FLAPAMAMAKU_PLATFORM_SESSION_DAYS", "30"))))
BILLING_INTERVAL_SECONDS = max(300, int(os.getenv("FLAPAMAMAKU_PLATFORM_BILLING_INTERVAL_SECONDS", "3600")))
app = FastAPI(title="FLAPAMAMAKU Platform", version="0.9.0", docs_url=None, redoc_url=None, openapi_url=None)


def clean_instance_id(value):
    value = value.strip().lower()
    if not value or not all(ch.isalnum() or ch == "-" for ch in value):
        raise HTTPException(422, "Instanz-ID darf nur a-z, 0-9 und '-' enthalten")
    return value


def club_dict(row):
    return {**dict(row), "auto_suspend_overdue": bool(row["auto_suspend_overdue"]), "monthly_fee": round(row["monthly_fee_cents"] / 100, 2)}


def invoice_dict(row):
    out = dict(row)
    out["amount"] = round(row["amount_cents"] / 100, 2)
    return out


class BootstrapPayload(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=10, max_length=200)


class LoginPayload(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)


class ClubPayload(BaseModel):
    instance_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    api_base_url: str = Field(default="", max_length=500)
    billing_email: str = Field(default="", max_length=320)
    monthly_fee_cents: int = Field(default=0, ge=0, le=10_000_000)
    currency: str = Field(default="CHF", min_length=3, max_length=3)
    billing_day: int = Field(default=1, ge=1, le=28)
    due_days: int = Field(default=30, ge=1, le=180)
    auto_suspend_overdue: bool = False


class SuspendPayload(BaseModel):
    reason: str = Field(default="Manuelle Sperre durch Plattformadministrator", max_length=500)


class InvoicePayload(BaseModel):
    club_id: int
    billing_period: str = Field(pattern=r"^\d{4}-\d{2}$")


def require_superuser(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Superuser-Anmeldung erforderlich")
    token = authorization.split(" ", 1)[1].strip()
    with connect() as db:
        row = db.execute("SELECT u.* FROM platform_sessions s JOIN platform_superusers u ON u.id=s.superuser_id WHERE s.token_hash=? AND u.active=1 AND datetime(s.expires_at)>datetime(?)", (hash_token(token), now_iso())).fetchone()
        if not row:
            raise HTTPException(401, "Sitzung abgelaufen oder ungültig")
        return row


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
@app.get("/platform")
def ui():
    return FileResponse(STATIC_DIR / "platform.html")


@app.get("/api/platform/health")
def health():
    init_db()
    with connect() as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        schema = db.execute("SELECT COALESCE(MAX(version),0) FROM platform_schema_migrations").fetchone()[0]
        users = db.execute("SELECT COUNT(*) FROM platform_superusers WHERE active=1").fetchone()[0]
    return {"status": "ok", "schema": schema, "integrity": integrity, "bootstrapped": users > 0}


@app.post("/api/platform/bootstrap")
def bootstrap(payload: BootstrapPayload):
    init_db()
    with connect() as db:
        if db.execute("SELECT 1 FROM platform_superusers LIMIT 1").fetchone():
            raise HTTPException(409, "Plattform-Superuser ist bereits eingerichtet")
        digest, salt = make_password(payload.password)
        cur = db.execute("INSERT INTO platform_superusers(username,password_hash,salt,active,created_at) VALUES (?,?,?,?,?)", (payload.username.strip(), digest, salt, 1, now_iso()))
        audit(db, cur.lastrowid, "platform.bootstrap", "superuser", cur.lastrowid)
        db.commit()
    return {"created": True}


@app.post("/api/platform/login")
def login(payload: LoginPayload):
    init_db()
    with connect() as db:
        user = db.execute("SELECT * FROM platform_superusers WHERE username=? COLLATE NOCASE AND active=1", (payload.username.strip(),)).fetchone()
        if not user or not verify_password(payload.password, user["password_hash"], user["salt"]):
            raise HTTPException(401, "Benutzername oder Passwort falsch")
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
        db.execute("INSERT INTO platform_sessions(superuser_id,token_hash,expires_at,created_at) VALUES (?,?,?,?)", (user["id"], hash_token(token), expires.replace(microsecond=0).isoformat(), now_iso()))
        audit(db, user["id"], "auth.login", "superuser", user["id"])
        db.commit()
    return {"token": token, "expires_at": expires.replace(microsecond=0).isoformat(), "username": user["username"]}


@app.get("/api/platform/dashboard")
def dashboard(user=Depends(require_superuser)):
    del user
    today = date.today().isoformat()
    with connect() as db:
        total = db.execute("SELECT COUNT(*) FROM platform_clubs").fetchone()[0]
        active = db.execute("SELECT COUNT(*) FROM platform_clubs WHERE status='active'").fetchone()[0]
        open_count = db.execute("SELECT COUNT(*) FROM platform_invoices WHERE status='open'").fetchone()[0]
        overdue = db.execute("SELECT COUNT(*) FROM platform_invoices WHERE status='open' AND date(due_date)<date(?)", (today,)).fetchone()[0]
        cents = db.execute("SELECT COALESCE(SUM(amount_cents),0) FROM platform_invoices WHERE status='open'").fetchone()[0]
    return {"clubs_total": total, "clubs_active": active, "clubs_suspended": total-active, "invoices_open": open_count, "invoices_overdue": overdue, "open_amount": round(cents/100, 2)}


@app.get("/api/platform/clubs")
def list_clubs(user=Depends(require_superuser)):
    del user
    with connect() as db:
        return [club_dict(r) for r in db.execute("SELECT * FROM platform_clubs ORDER BY name COLLATE NOCASE").fetchall()]


@app.post("/api/platform/clubs")
def create_club(payload: ClubPayload, user=Depends(require_superuser)):
    instance = clean_instance_id(payload.instance_id)
    with connect() as db:
        try:
            cur = db.execute("INSERT INTO platform_clubs(instance_id,name,api_base_url,billing_email,monthly_fee_cents,currency,billing_day,due_days,auto_suspend_overdue,status,suspension_reason,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,'active','',?,?)", (instance,payload.name.strip(),payload.api_base_url.strip().rstrip('/'),payload.billing_email.strip(),payload.monthly_fee_cents,payload.currency.upper(),payload.billing_day,payload.due_days,int(payload.auto_suspend_overdue),now_iso(),now_iso()))
        except Exception as exc:
            raise HTTPException(409, "Instanz-ID existiert bereits") from exc
        audit(db, user["id"], "club.create", "club", cur.lastrowid, instance)
        db.commit()
        return club_dict(db.execute("SELECT * FROM platform_clubs WHERE id=?", (cur.lastrowid,)).fetchone())


@app.put("/api/platform/clubs/{club_id}")
def update_club(club_id: int, payload: ClubPayload, user=Depends(require_superuser)):
    instance = clean_instance_id(payload.instance_id)
    with connect() as db:
        cur = db.execute("UPDATE platform_clubs SET instance_id=?,name=?,api_base_url=?,billing_email=?,monthly_fee_cents=?,currency=?,billing_day=?,due_days=?,auto_suspend_overdue=?,updated_at=? WHERE id=?", (instance,payload.name.strip(),payload.api_base_url.strip().rstrip('/'),payload.billing_email.strip(),payload.monthly_fee_cents,payload.currency.upper(),payload.billing_day,payload.due_days,int(payload.auto_suspend_overdue),now_iso(),club_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Verein nicht gefunden")
        audit(db, user["id"], "club.update", "club", club_id, instance)
        db.commit()
        return club_dict(db.execute("SELECT * FROM platform_clubs WHERE id=?", (club_id,)).fetchone())


@app.post("/api/platform/clubs/{club_id}/suspend")
def suspend(club_id: int, payload: SuspendPayload, user=Depends(require_superuser)):
    reason = payload.reason.strip() or "Manuelle Sperre durch Plattformadministrator"
    with connect() as db:
        cur = db.execute("UPDATE platform_clubs SET status='suspended',suspension_reason=?,updated_at=? WHERE id=?", (reason,now_iso(),club_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Verein nicht gefunden")
        audit(db,user["id"],"club.suspend","club",club_id,reason); db.commit()
    return {"suspended": True}


@app.post("/api/platform/clubs/{club_id}/resume")
def resume(club_id: int, user=Depends(require_superuser)):
    with connect() as db:
        cur = db.execute("UPDATE platform_clubs SET status='active',suspension_reason='',updated_at=? WHERE id=?", (now_iso(),club_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Verein nicht gefunden")
        audit(db,user["id"],"club.resume","club",club_id); db.commit()
    return {"active": True}


@app.get("/api/platform/invoices")
def invoices(user=Depends(require_superuser)):
    del user
    with connect() as db:
        rows = db.execute("SELECT i.*,c.name club_name FROM platform_invoices i JOIN platform_clubs c ON c.id=i.club_id ORDER BY i.issue_date DESC,i.id DESC").fetchall()
        return [invoice_dict(r) for r in rows]


@app.post("/api/platform/invoices")
def invoice_create(payload: InvoicePayload, user=Depends(require_superuser)):
    with connect() as db:
        club = db.execute("SELECT * FROM platform_clubs WHERE id=?", (payload.club_id,)).fetchone()
        if not club:
            raise HTTPException(404, "Verein nicht gefunden")
        row, created = create_invoice(db, club, payload.billing_period, user["id"])
        db.commit()
        if not created:
            raise HTTPException(409, "Rechnung für diesen Abrechnungsmonat existiert bereits")
        return invoice_dict(row)


@app.post("/api/platform/invoices/{invoice_id}/paid")
def paid(invoice_id: int, user=Depends(require_superuser)):
    with connect() as db:
        inv = db.execute("SELECT * FROM platform_invoices WHERE id=?", (invoice_id,)).fetchone()
        if not inv:
            raise HTTPException(404, "Rechnung nicht gefunden")
        db.execute("UPDATE platform_invoices SET status='paid',paid_at=? WHERE id=?", (now_iso(),invoice_id))
        audit(db,user["id"],"invoice.paid","invoice",invoice_id,inv["invoice_number"])
        overdue = db.execute("SELECT 1 FROM platform_invoices WHERE club_id=? AND status='open' AND date(due_date)<date(?) LIMIT 1", (inv["club_id"],date.today().isoformat())).fetchone()
        club = db.execute("SELECT * FROM platform_clubs WHERE id=?", (inv["club_id"],)).fetchone()
        if club and not overdue and club["status"] == "suspended" and str(club["suspension_reason"]).startswith("Automatische Sperre:"):
            db.execute("UPDATE platform_clubs SET status='active',suspension_reason='',updated_at=? WHERE id=?", (now_iso(),club["id"]))
        db.commit()
    return {"paid": True}


@app.post("/api/platform/billing/run")
def billing(user=Depends(require_superuser)):
    return run_billing(user["id"])


@app.get("/api/platform/audit")
def audit_rows(user=Depends(require_superuser)):
    del user
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT * FROM platform_audit_log ORDER BY id DESC LIMIT 250").fetchall()]


@app.get("/api/platform/invoices/{invoice_id}/pdf")
def pdf(invoice_id: int, user=Depends(require_superuser)):
    del user
    with connect() as db:
        row = db.execute("SELECT i.*,c.name club_name FROM platform_invoices i JOIN platform_clubs c ON c.id=i.club_id WHERE i.id=?", (invoice_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Rechnung nicht gefunden")
    text = f"FLAPAMAMAKU Plattformabrechnung\nRechnung {row['invoice_number']}\nVerein {row['club_name']}\nPeriode {row['billing_period']}\nFaellig {row['due_date']}\nBetrag {row['currency']} {row['amount_cents']/100:.2f}\nStatus {row['status']}"
    stream = "BT /F1 11 Tf 54 790 Td " + " Tj 0 -20 Td ".join(f"({line.replace('(','[').replace(')',']')})" for line in text.splitlines()) + " Tj ET"
    s = stream.encode("latin-1", errors="replace")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>", b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>", b"<< /Length "+str(len(s)).encode()+b" >>\nstream\n"+s+b"\nendstream", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out=bytearray(b"%PDF-1.4\n"); offsets=[0]
    for i,obj in enumerate(objs,1): offsets.append(len(out)); out.extend(f"{i} 0 obj\n".encode()+obj+b"\nendobj\n")
    xref=len(out); out.extend(f"xref\n0 6\n0000000000 65535 f \n".encode())
    for off in offsets[1:]: out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return Response(bytes(out), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={row['invoice_number']}.pdf"})


async def billing_loop():
    while True:
        try: run_billing(None)
        except Exception: pass
        await asyncio.sleep(BILLING_INTERVAL_SECONDS)


@app.on_event("startup")
async def startup():
    init_db(); asyncio.create_task(billing_loop())
