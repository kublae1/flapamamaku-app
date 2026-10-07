import asyncio
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from . import main as main_app
from . import masterplan_extensions

app = main_app.app
INSTANCE_ID = main_app.INSTANCE_ID
DB_PATH = main_app.DB_PATH
PLATFORM_DB = Path(os.getenv("FLAPAMAMAKU_PLATFORM_DB", "/platform/platform.db"))
PUBLIC_URL = os.getenv("FLAPAMAMAKU_PUBLIC_URL", "").strip().rstrip("/")
RUNTIME_VERSION = os.getenv("FLAPAMAMAKU_API_VERSION", main_app.API_VERSION).strip() or main_app.API_VERSION

# Some production databases still contain legacy tenant guards from older
# masterplan builds. Two known variants can reject the one-time annual-Sujet
# migration: the exact trigger error "wrong club_id", and an obsolete global
# UNIQUE rule reported by SQLite as "UNIQUE constraint failed:
# annual_sujets.is_current". Keep the migration isolated in a savepoint so
# either legacy guard cannot make the whole backend fail at startup. Existing
# content is left untouched and all unrelated integrity failures still abort.
_original_migrate_legacy_sujets = masterplan_extensions._migrate_legacy_sujets


def _safe_migrate_legacy_sujets(db: sqlite3.Connection) -> None:
    savepoint = "runtime_legacy_sujet_migration"
    db.execute(f"SAVEPOINT {savepoint}")
    try:
        _original_migrate_legacy_sujets(db)
    except sqlite3.IntegrityError as exc:
        db.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
        message = str(exc).lower()
        known_legacy_guard = (
            "wrong club_id" in message
            or "unique constraint failed: annual_sujets.is_current" in message
        )
        if not known_legacy_guard:
            db.execute(f"RELEASE SAVEPOINT {savepoint}")
            raise
    finally:
        # RELEASE is valid both after a successful migration and after
        # ROLLBACK TO; guard against a prior explicit release on re-raise.
        try:
            db.execute(f"RELEASE SAVEPOINT {savepoint}")
        except sqlite3.OperationalError as exc:
            if "no such savepoint" not in str(exc).lower():
                raise


masterplan_extensions._migrate_legacy_sujets = _safe_migrate_legacy_sujets
install_masterplan_extensions = masterplan_extensions.install_masterplan_extensions

# FastAPI 0.116 rejects decorated 204 routes when it infers a response body from
# the Python annotation. Register only those routes temporarily as 200, then
# immediately convert the generated APIRoute to 204 + an empty Response class.
# This is restricted to extension installation and does not change normal JSON
# routes or the stable multi-club API.
_original_post = app.post
_original_delete = app.delete


def _bodyless_204_wrapper(original_decorator, method: str):
    def wrapped(path: str, *args, **kwargs):
        if kwargs.get("status_code") != 204:
            return original_decorator(path, *args, **kwargs)

        registration_kwargs = dict(kwargs)
        registration_kwargs["status_code"] = 200

        def decorator(func):
            registered = original_decorator(path, *args, **registration_kwargs)(func)
            for route in reversed(app.router.routes):
                if getattr(route, "path", None) != path:
                    continue
                methods = getattr(route, "methods", set()) or set()
                if method not in methods or getattr(route, "endpoint", None) is not func:
                    continue
                route.status_code = 204
                route.response_class = Response
                route.response_model = None
                route.response_field = None
                break
            return registered

        return decorator

    return wrapped


app.post = _bodyless_204_wrapper(_original_post, "POST")
app.delete = _bodyless_204_wrapper(_original_delete, "DELETE")
try:
    install_masterplan_extensions()
finally:
    app.post = _original_post
    app.delete = _original_delete

# Register the post-masterplan message centre only after the proven extension
# routes have been installed. This module adds non-destructive read-state data,
# tenant-scoped message endpoints and stronger FCM channel routing.
from . import message_center as message_center  # noqa: E402,F401

# Runtime only adds Phase-9 registration/suspension around the proven integrated
# multi-club backend. Club switching and admin rendering stay exclusively in
# app.main so normal club administrators never receive a platform selector.
main_app.API_VERSION = RUNTIME_VERSION
app.version = RUNTIME_VERSION


def _club_name() -> str:
    try:
        db = sqlite3.connect(DB_PATH, timeout=2)
        try:
            row = db.execute(
                "SELECT name FROM clubs WHERE active = 1 ORDER BY id LIMIT 1"
            ).fetchone()
            if not row:
                row = db.execute("SELECT app_name FROM app_config ORDER BY id LIMIT 1").fetchone()
        finally:
            db.close()
        if row and str(row[0] or "").strip():
            return str(row[0]).strip()
    except sqlite3.Error:
        pass
    return "FLAPAMAMAKU" if INSTANCE_ID == "flapamamaku" else INSTANCE_ID


def register_platform_club() -> bool:
    """Idempotently register this deployment in the optional Phase-9 platform DB.

    Existing billing, suspension and accounting state is never overwritten.
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
                name = str(existing["name"] or "").strip()
                url = str(existing["api_base_url"] or "").strip()
                db.execute(
                    """
                    UPDATE platform_clubs SET name=?, api_base_url=?, updated_at=? WHERE id=?
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
    for _ in range(120):
        if await asyncio.to_thread(register_platform_club):
            return
        await asyncio.sleep(2)


@app.on_event("startup")
async def register_with_platform() -> None:
    asyncio.create_task(_platform_registration_loop())


def platform_access_state() -> tuple[str, str]:
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
        return JSONResponse(
            status_code=423,
            content={"detail": message, "club_status": "suspended"},
        )
    return HTMLResponse(
        status_code=423,
        content=(
            "<!doctype html><html><head><meta charset='utf-8'><title>Verein gesperrt</title>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'></head>"
            "<body style='font-family:system-ui;margin:3rem;max-width:720px'>"
            "<h1>Zugriff vorübergehend gesperrt</h1><p>" + message + "</p></body></html>"
        ),
    )
