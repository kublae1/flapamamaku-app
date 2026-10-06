import logging
import sqlite3

from . import main as main_app
from .runtime import app

logger = logging.getLogger("flapamamaku.push")


def _drop_obsolete_push_tenant_triggers() -> list[str]:
    """Remove only known legacy push-token triggers from old tenant builds.

    Historical test builds created SQLite triggers on push_tokens that aborted
    writes with the literal error "wrong club_id". The current integrated
    multi-club backend scopes push tokens through the authenticated session and
    numeric club_id, so those legacy triggers are both obsolete and harmful.
    No data rows are changed here.
    """
    removed: list[str] = []
    with main_app.connect() as db:
        rows = db.execute(
            """
            SELECT name, sql
            FROM sqlite_master
            WHERE type = 'trigger' AND tbl_name = 'push_tokens'
            """
        ).fetchall()
        for row in rows:
            sql = str(row["sql"] or "")
            if "wrong club_id" not in sql.lower():
                continue
            name = str(row["name"] or "")
            if not name:
                continue
            quoted = name.replace('"', '""')
            db.execute(f'DROP TRIGGER IF EXISTS "{quoted}"')
            removed.append(name)
        if removed:
            db.commit()
    return removed


@app.on_event("startup")
def cleanup_obsolete_push_tenant_triggers() -> None:
    try:
        removed = _drop_obsolete_push_tenant_triggers()
        if removed:
            logger.warning(
                "Removed obsolete push token tenant trigger(s): %s",
                ", ".join(removed),
            )
    except sqlite3.Error as exc:
        # Startup must remain available; registration will still surface any
        # genuine database error to the API if cleanup was not possible.
        logger.error("Legacy push trigger cleanup failed: %s", exc)
