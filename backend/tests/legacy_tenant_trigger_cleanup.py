"""Regression test for cleanup of obsolete tenant triggers.

Historical production/test databases may still contain SQLite triggers that
abort valid writes with the literal error ``wrong club_id``.  The current
multi-club runtime must remove only those obsolete guards and leave unrelated
triggers untouched.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


with tempfile.TemporaryDirectory(prefix="flapamamaku-trigger-test-") as tmp:
    db_path = Path(tmp) / "flapamamaku.db"
    os.environ["FLAPAMAMAKU_DB"] = str(db_path)
    os.environ["FLAPAMAMAKU_BACKUP_DIR"] = str(Path(tmp) / "backups")
    os.environ["FLAPAMAMAKU_INSTANCE_ID"] = "flapamamaku"
    os.environ["FLAPAMAMAKU_ENV"] = "development"

    from app import main  # noqa: E402

    main.init_db()

    with main.connect() as db:
        db.execute(
            """
            CREATE TRIGGER legacy_news_wrong_club
            BEFORE INSERT ON news
            WHEN NEW.club_id != 999
            BEGIN
              SELECT RAISE(ABORT, 'wrong club_id');
            END
            """
        )
        db.execute(
            """
            CREATE TRIGGER legacy_events_wrong_club
            BEFORE INSERT ON events
            WHEN NEW.club_id != 999
            BEGIN
              SELECT RAISE(ABORT, 'wrong club_id');
            END
            """
        )
        db.execute(
            """
            CREATE TRIGGER keep_unrelated_news_trigger
            AFTER INSERT ON news
            BEGIN
              SELECT 1;
            END
            """
        )
        db.commit()

    from app import push_runtime  # noqa: E402

    removed = push_runtime._drop_obsolete_tenant_triggers()
    assert "news:legacy_news_wrong_club" in removed, removed
    assert "events:legacy_events_wrong_club" in removed, removed

    with main.connect() as db:
        remaining = {
            str(row["name"])
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            ).fetchall()
        }

    assert "legacy_news_wrong_club" not in remaining, remaining
    assert "legacy_events_wrong_club" not in remaining, remaining
    assert "keep_unrelated_news_trigger" in remaining, remaining

print("legacy tenant trigger cleanup: ok")
