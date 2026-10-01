from __future__ import annotations

import io
import os
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from app.main import _ensure_noster_default_hero, connect, init_db


def main() -> None:
    db_path = os.environ["FLAPAMAMAKU_DB"]
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass

    init_db()
    now = datetime.now(timezone.utc).isoformat()

    with connect() as db:
        flapa_before = int(
            db.execute(
                "SELECT COUNT(*) FROM content_items WHERE club_id = 1 AND section = 'hero'"
            ).fetchone()[0]
        )

        cursor = db.execute(
            """
            INSERT INTO clubs (
                slug, name, short_name, active,
                primary_color, secondary_color, website,
                created_at, updated_at
            ) VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)
            """,
            (
                "noster",
                "Nostradamus",
                "Noster",
                "#111111",
                "#FFFFFF",
                "https://www.noster.ch/",
                now,
                now,
            ),
        )
        noster_id = int(cursor.lastrowid)

        other = db.execute(
            """
            INSERT INTO clubs (
                slug, name, short_name, active,
                primary_color, secondary_color,
                created_at, updated_at
            ) VALUES (?, ?, ?, 1, ?, ?, ?, ?)
            """,
            (
                "anderer-verein",
                "Anderer Verein",
                "ANDERER",
                "#225588",
                "#FFFFFF",
                now,
                now,
            ),
        )
        other_id = int(other.lastrowid)
        db.commit()

        _ensure_noster_default_hero(db)
        db.commit()

        hero = db.execute(
            """
            SELECT id, title, image_data
            FROM content_items
            WHERE club_id = ? AND section = 'hero'
            ORDER BY id DESC
            LIMIT 1
            """,
            (noster_id,),
        ).fetchone()
        assert hero is not None
        assert hero["title"] == "NOSTRADAMUS"
        assert hero["image_data"] is None

        image_row = db.execute(
            """
            SELECT image_data, image_mime
            FROM content_images
            WHERE content_id = ? AND club_id = ?
            """,
            (hero["id"], noster_id),
        ).fetchone()
        assert image_row is not None
        assert image_row["image_mime"] == "image/jpeg"

        with Image.open(io.BytesIO(image_row["image_data"])) as image:
            assert image.size == (1200, 1600)
            assert image.format == "JPEG"

        assert (
            db.execute(
                "SELECT COUNT(*) FROM content_items WHERE club_id = ? AND section = 'hero'",
                (other_id,),
            ).fetchone()[0]
            == 0
        )
        assert (
            db.execute(
                "SELECT COUNT(*) FROM content_items WHERE club_id = 1 AND section = 'hero'"
            ).fetchone()[0]
            == flapa_before
        )

        image_count = int(
            db.execute(
                "SELECT COUNT(*) FROM content_images WHERE content_id = ? AND club_id = ?",
                (hero["id"], noster_id),
            ).fetchone()[0]
        )
        _ensure_noster_default_hero(db)
        db.commit()
        image_count_after = int(
            db.execute(
                "SELECT COUNT(*) FROM content_images WHERE content_id = ? AND club_id = ?",
                (hero["id"], noster_id),
            ).fetchone()[0]
        )
        assert image_count == image_count_after == 1

    start_screen = Path("../lib/screens/start_screen.dart").read_text(encoding="utf-8")
    assert "final isFlapamamaku = store.currentClubId == 1;" in start_screen
    assert "!isFlapamamaku && store.appLogoUrl.isNotEmpty" in start_screen
    assert "final fallbackAsset = isFlapamamaku ? flapamamakuFallbackHero : '';" in start_screen

    print("noster tenant hero ok")


if __name__ == "__main__":
    main()
