import asyncio
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

from . import main as main_app

app = main_app.app
INSTANCE_ID = main_app.INSTANCE_ID
DB_PATH = main_app.DB_PATH
PLATFORM_DB = Path(os.getenv("FLAPAMAMAKU_PLATFORM_DB", "/platform/platform.db"))
PUBLIC_URL = os.getenv("FLAPAMAMAKU_PUBLIC_URL", "").strip().rstrip("/")
RUNTIME_VERSION = os.getenv("FLAPAMAMAKU_API_VERSION", "0.9.2").strip() or "0.9.2"

# Keep the visible backend version aligned with the repaired Phase-9 runtime
# without rewriting historical migration code in app.main.
main_app.API_VERSION = RUNTIME_VERSION
app.version = RUNTIME_VERSION


def _club_name() -> str:
    try:
        db = sqlite3.connect(DB_PATH, timeout=2)
        try:
            row = db.execute("SELECT app_name FROM app_config WHERE id=1").fetchone()
        finally:
            db.close()
        if row and str(row[0] or "").strip():
            return str(row[0]).strip()
    except sqlite3.Error:
        pass
    return "FLAPAMAMAKU" if INSTANCE_ID == "flapamamaku" else INSTANCE_ID


def register_platform_club() -> bool:
    """Register this running club instance in the shared Phase-9 platform DB.

    Registration is intentionally idempotent. Existing billing, suspension and
    accounting values are never overwritten by a club runtime.
    """
    if not PLATFORM_DB.exists():
        return False
    try:
        db = sqlite3.connect(PLATFORM_DB, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            table = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='platform_clubs'"
            ).fetchone()
            if not table:
                return False
            now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            existing = db.execute(
                "SELECT id,name,api_base_url FROM platform_clubs WHERE instance_id=? COLLATE NOCASE",
                (INSTANCE_ID,),
            ).fetchone()
            if existing is None:
                db.execute(
                    """
                    INSERT INTO platform_clubs(
                      instance_id,name,api_base_url,billing_email,monthly_fee_cents,
                      currency,billing_day,due_days,auto_suspend_overdue,status,
                      suspension_reason,created_at,updated_at
                    ) VALUES (?,?,?,'',0,'CHF',1,30,0,'active','',?,?)
                    """,
                    (INSTANCE_ID, _club_name(), PUBLIC_URL, now, now),
                )
            else:
                # Only fill discovery metadata when it is still empty/generic.
                name = str(existing["name"] or "").strip()
                url = str(existing["api_base_url"] or "").strip()
                db.execute(
                    """
                    UPDATE platform_clubs
                    SET name=?, api_base_url=?, updated_at=?
                    WHERE id=?
                    """,
                    (
                        _club_name() if not name or name == INSTANCE_ID else name,
                        PUBLIC_URL if PUBLIC_URL and not url else url,
                        now,
                        existing["id"],
                    ),
                )
            db.commit()
            return True
        finally:
            db.close()
    except sqlite3.Error:
        return False


async def _platform_registration_loop() -> None:
    # The platform service and the club backend can start in parallel. Retry
    # until the shared platform schema is ready instead of requiring manual club creation.
    for _ in range(120):
        if await asyncio.to_thread(register_platform_club):
            return
        await asyncio.sleep(2)


@app.on_event("startup")
async def register_with_platform() -> None:
    asyncio.create_task(_platform_registration_loop())


def platform_access_state():
    if not PLATFORM_DB.exists():
        return "active", ""
    try:
        db = sqlite3.connect(f"file:{PLATFORM_DB}?mode=ro", uri=True, timeout=2)
        db.row_factory = sqlite3.Row
        try:
            row = db.execute(
                "SELECT status,suspension_reason FROM platform_clubs WHERE instance_id=? COLLATE NOCASE",
                (INSTANCE_ID,),
            ).fetchone()
        finally:
            db.close()
    except sqlite3.Error:
        return "active", ""
    if not row:
        return "active", ""
    return str(row["status"]), str(row["suspension_reason"] or "")


@app.middleware("http")
async def platform_access_control(request: Request, call_next):
    path = request.url.path
    if path == "/api/health" or path.endswith("flapamamaku-icon.png"):
        return await call_next(request)
    status, reason = platform_access_state()
    if status != "suspended":
        return await call_next(request)
    message = reason or "Dieser Verein ist durch die Plattformverwaltung vorübergehend gesperrt."
    if path.startswith("/api/"):
        return JSONResponse(status_code=423, content={"detail": message, "club_status": "suspended"})
    return HTMLResponse(
        status_code=423,
        content=(
            "<!doctype html><html><head><meta charset='utf-8'><title>Verein gesperrt</title>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'></head>"
            "<body style='font-family:system-ui;margin:3rem;max-width:720px'>"
            "<h1>Zugriff vorübergehend gesperrt</h1><p>" + message + "</p></body></html>"
        ),
    )
