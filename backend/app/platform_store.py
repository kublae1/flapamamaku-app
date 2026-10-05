import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DB = Path(os.getenv("FLAPAMAMAKU_PLATFORM_DB", "/platform/platform.db"))
SCHEMA_VERSION = 1


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA journal_mode=WAL")
    return db


def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS platform_schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS platform_superusers(
          id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE COLLATE NOCASE,
          password_hash TEXT NOT NULL, salt TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS platform_sessions(
          id INTEGER PRIMARY KEY AUTOINCREMENT, superuser_id INTEGER NOT NULL REFERENCES platform_superusers(id) ON DELETE CASCADE,
          token_hash TEXT NOT NULL UNIQUE, expires_at TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS platform_clubs(
          id INTEGER PRIMARY KEY AUTOINCREMENT, instance_id TEXT NOT NULL UNIQUE COLLATE NOCASE, name TEXT NOT NULL,
          api_base_url TEXT NOT NULL DEFAULT '', billing_email TEXT NOT NULL DEFAULT '', monthly_fee_cents INTEGER NOT NULL DEFAULT 0,
          currency TEXT NOT NULL DEFAULT 'CHF', billing_day INTEGER NOT NULL DEFAULT 1, due_days INTEGER NOT NULL DEFAULT 30,
          auto_suspend_overdue INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','suspended')),
          suspension_reason TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS platform_invoices(
          id INTEGER PRIMARY KEY AUTOINCREMENT, club_id INTEGER NOT NULL REFERENCES platform_clubs(id) ON DELETE RESTRICT,
          invoice_number TEXT NOT NULL UNIQUE, billing_period TEXT NOT NULL, issue_date TEXT NOT NULL, due_date TEXT NOT NULL,
          amount_cents INTEGER NOT NULL, currency TEXT NOT NULL DEFAULT 'CHF', status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','paid','void')),
          paid_at TEXT, created_at TEXT NOT NULL, UNIQUE(club_id,billing_period));
        CREATE TABLE IF NOT EXISTS platform_audit_log(
          id INTEGER PRIMARY KEY AUTOINCREMENT, superuser_id INTEGER, action TEXT NOT NULL, entity_type TEXT NOT NULL,
          entity_id TEXT NOT NULL DEFAULT '', detail TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_platform_invoices_status_due ON platform_invoices(status,due_date);
        """)
        db.execute("INSERT OR IGNORE INTO platform_schema_migrations(version,applied_at) VALUES (?,?)", (SCHEMA_VERSION, now_iso()))
        db.commit()


def make_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240000)
    return digest.hex(), salt.hex()


def verify_password(password, digest, salt):
    candidate, _ = make_password(password, bytes.fromhex(salt))
    return hmac.compare_digest(candidate, digest)


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def audit(db, user_id, action, entity_type, entity_id="", detail=""):
    db.execute("INSERT INTO platform_audit_log(superuser_id,action,entity_type,entity_id,detail,created_at) VALUES (?,?,?,?,?,?)",
               (user_id, action, entity_type, str(entity_id), detail[:1000], now_iso()))


def next_invoice_number(db):
    year = date.today().year
    prefix = f"FMA-{year}-"
    row = db.execute("SELECT invoice_number FROM platform_invoices WHERE invoice_number LIKE ? ORDER BY id DESC LIMIT 1", (prefix + "%",)).fetchone()
    seq = 1
    if row:
        try:
            seq = int(row[0].rsplit("-", 1)[1]) + 1
        except (ValueError, IndexError):
            pass
    return f"{prefix}{seq:05d}"


def create_invoice(db, club, period, user_id=None):
    existing = db.execute("SELECT i.*,c.name club_name FROM platform_invoices i JOIN platform_clubs c ON c.id=i.club_id WHERE i.club_id=? AND i.billing_period=?",
                          (club["id"], period)).fetchone()
    if existing:
        return existing, False
    issue = date.today()
    due = issue + timedelta(days=int(club["due_days"]))
    number = next_invoice_number(db)
    cur = db.execute("INSERT INTO platform_invoices(club_id,invoice_number,billing_period,issue_date,due_date,amount_cents,currency,status,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                     (club["id"], number, period, issue.isoformat(), due.isoformat(), club["monthly_fee_cents"], club["currency"], "open", now_iso()))
    audit(db, user_id, "invoice.create", "invoice", cur.lastrowid, f"{number} / {period}")
    row = db.execute("SELECT i.*,c.name club_name FROM platform_invoices i JOIN platform_clubs c ON c.id=i.club_id WHERE i.id=?", (cur.lastrowid,)).fetchone()
    return row, True


def run_billing(user_id=None):
    created = 0
    suspended = 0
    today = date.today()
    period = today.strftime("%Y-%m")
    with connect() as db:
        clubs = db.execute("SELECT * FROM platform_clubs ORDER BY id").fetchall()
        for club in clubs:
            if club["monthly_fee_cents"] > 0 and today.day >= club["billing_day"]:
                _, was_created = create_invoice(db, club, period, user_id)
                created += int(was_created)
        overdue = db.execute("SELECT DISTINCT c.id FROM platform_clubs c JOIN platform_invoices i ON i.club_id=c.id WHERE c.auto_suspend_overdue=1 AND i.status='open' AND date(i.due_date)<date(?)", (today.isoformat(),)).fetchall()
        for row in overdue:
            club = db.execute("SELECT * FROM platform_clubs WHERE id=?", (row["id"],)).fetchone()
            if club and club["status"] != "suspended":
                reason = "Automatische Sperre: überfällige Rechnung"
                db.execute("UPDATE platform_clubs SET status='suspended',suspension_reason=?,updated_at=? WHERE id=?", (reason, now_iso(), club["id"]))
                audit(db, user_id, "club.auto_suspend", "club", club["id"], reason)
                suspended += 1
        db.commit()
    return {"invoices_created": created, "clubs_suspended": suspended}
