import os
import sqlite3
from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

from .main import INSTANCE_ID, app

PLATFORM_DB = Path(os.getenv("FLAPAMAMAKU_PLATFORM_DB", "/platform/platform.db"))


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
