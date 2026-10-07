"""Contract for safe cleanup of obsolete push tenant triggers."""

from __future__ import annotations

import os
from pathlib import Path

DB = Path(os.environ["FLAPAMAMAKU_DB"])
try:
    DB.unlink()
except FileNotFoundError:
    pass

from app import push_runtime  # noqa: E402


def main() -> None:
    with push_runtime.main_app.connect() as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS push_tokens("
            "id INTEGER PRIMARY KEY, club_id INTEGER, token TEXT)"
        )
        db.execute(
            """
            CREATE TRIGGER legacy_push_guard
            BEFORE INSERT ON push_tokens
            WHEN NEW.club_id != 999
            BEGIN
              SELECT RAISE(ABORT, 'wrong club_id');
            END
            """
        )
        db.execute(
            """
            CREATE TRIGGER keep_push_guard
            AFTER INSERT ON push_tokens
            BEGIN
              SELECT 1;
            END
            """
        )
        db.commit()

    removed = push_runtime._drop_obsolete_push_tenant_triggers()
    assert removed == ["legacy_push_guard"], removed

    with push_runtime.main_app.connect() as db:
        rows = db.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='trigger' AND tbl_name='push_tokens' ORDER BY name"
        ).fetchall()
        names = [str(row["name"]) for row in rows]

    assert "legacy_push_guard" not in names
    assert "keep_push_guard" in names
    print("PUSH LEGACY TRIGGER CONTRACT OK")


if __name__ == "__main__":
    main()
