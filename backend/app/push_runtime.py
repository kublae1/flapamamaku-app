import logging
import sqlite3

from . import main as main_app
from .runtime import app

logger = logging.getLogger("flapamamaku.push")


def _drop_obsolete_tenant_triggers() -> list[str]:
    """Remove obsolete tenant triggers left by historical test builds.

    Some older deployments created SQLite triggers on tenant-scoped tables that
    aborted valid writes with the literal error ``wrong club_id``. The current
    integrated multi-club backend scopes reads and writes through the authenticated
    session plus numeric ``club_id`` and therefore does not require these legacy
    guards.

    Only triggers whose stored SQL contains that exact historical error marker are
    removed. No table rows are modified and unrelated triggers are preserved.
    """
    removed: list[str] = []
    with main_app.connect() as db:
        rows = db.execute(
            """
            SELECT name, tbl_name, sql
            FROM sqlite_master
            WHERE type = 'trigger'
            ORDER BY name
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
            removed.append(f"{row['tbl_name']}:{name}")
        if removed:
            db.commit()
    return removed


# Backwards-compatible alias used by earlier diagnostics/tests.
def _drop_obsolete_push_tenant_triggers() -> list[str]:
    return _drop_obsolete_tenant_triggers()


@app.on_event("startup")
def cleanup_obsolete_tenant_triggers() -> None:
    try:
        removed = _drop_obsolete_tenant_triggers()
        if removed:
            logger.warning(
                "Removed obsolete tenant trigger(s): %s",
                ", ".join(removed),
            )
    except sqlite3.Error as exc:
        # Startup must remain available; the affected write will still surface
        # any genuine database error if cleanup was not possible.
        logger.error("Legacy tenant trigger cleanup failed: %s", exc)
