from __future__ import annotations

import copy
import os

from app.main import (
    BootstrapPayload,
    ClubCreatePayload,
    ContentPayload,
    MemberPayload,
    NewsPayload,
    _REQUEST_CLUB_ID,
    _create_club_backup_payload,
    _server_migration_checksum,
    _validate_server_migration_envelope,
    _merge_club_backup,
    bootstrap,
    connect,
    create_club,
    create_row,
    init_db,
    post_content,
)


def main() -> None:
    init_db()
    super_user = bootstrap(
        BootstrapPayload(
            username="club-backup-root",
            password="Testpass123!",
            member_id=None,
        )
    )

    flapa_news = create_row(
        "news",
        NewsPayload(
            title="FLAPA bleibt",
            text="Darf durch Vereinsimport nicht verändert werden",
            date="01.10.2026",
        ),
    )
    assert flapa_news["club_id"] == 1

    club = create_club(
        ClubCreatePayload(
            slug="backup-test",
            name="Backup Test",
            short_name="BT",
            subtitle="Backup Verein",
        ),
        user=super_user,
    )
    club_id = int(club["id"])

    context = _REQUEST_CLUB_ID.set(club_id)
    try:
        own_news = create_row(
            "news",
            NewsPayload(
                title="Original Vereinsnews",
                text="Nur dieser Verein",
                date="01.10.2026",
            ),
        )
        own_member = create_row(
            "members",
            MemberPayload(
                name="Backup Mitglied",
                role="Mitglied",
                since="2026",
            ),
        )
        own_album = post_content(
            ContentPayload(
                section="photos",
                title="Backup Fotoalbum",
                text="Dauerhafte Vereinsfotos",
            ),
            user=super_user,
        )

        with connect() as db:
            db.execute(
                """
                UPDATE members
                SET photo_data = ?, photo_mime = ?
                WHERE id = ? AND club_id = ?
                """,
                (b"club-photo-bytes", "image/webp", own_member["id"], club_id),
            )
            db.execute(
                """
                INSERT INTO content_images (
                    content_id, image_data, image_mime, sort_order,
                    created_at, club_id
                ) VALUES (?, ?, ?, 1, ?, ?)
                """,
                (
                    own_album["id"],
                    b"album-image-bytes",
                    "image/webp",
                    "2026-10-01T08:00:00+00:00",
                    club_id,
                ),
            )
            db.commit()

        payload = _create_club_backup_payload(club_id)
        assert payload["format"] == "flapamamaku-club-backup"
        assert payload["club_id"] == club_id
        assert payload["club_slug"] == "backup-test"
        assert "users" not in payload["tables"]
        assert "push_tokens" not in payload["tables"]
        assert "push_notifications" not in payload["tables"]
        assert "club_invoices" not in payload["tables"]
        assert "gallery_snapshots" not in payload["tables"]

        news_rows = payload["tables"]["news"]
        assert any(row["id"] == own_news["id"] for row in news_rows)
        member_rows = payload["tables"]["members"]
        member_backup = next(row for row in member_rows if row["id"] == own_member["id"])
        assert member_backup["photo_data"]["__blob_b64__"]
        image_rows = payload["tables"]["content_images"]
        assert len(image_rows) == 1
        assert image_rows[0]["image_data"]["__blob_b64__"]

        with connect() as db:
            db.execute(
                "UPDATE news SET title = ? WHERE id = ? AND club_id = ?",
                ("Nach Backup geändert", own_news["id"], club_id),
            )
            db.execute(
                "UPDATE clubs SET subtitle = ? WHERE id = ?",
                ("Nach Backup geändert", club_id),
            )
            db.commit()

        result = _merge_club_backup(payload, club_id)
        assert result["imported"] is True
        assert result["mode"] == "merge"
        assert result["safety_backup"]["name"].endswith(".db")

        with connect() as db:
            restored_news = db.execute(
                "SELECT title FROM news WHERE id = ? AND club_id = ?",
                (own_news["id"], club_id),
            ).fetchone()
            assert restored_news["title"] == "Original Vereinsnews"
            restored_club = db.execute(
                "SELECT subtitle FROM clubs WHERE id = ?",
                (club_id,),
            ).fetchone()
            assert restored_club["subtitle"] == "Backup Verein"
            flapa = db.execute(
                "SELECT title FROM news WHERE id = ? AND club_id = 1",
                (flapa_news["id"],),
            ).fetchone()
            assert flapa["title"] == "FLAPA bleibt"

        invalid = copy.deepcopy(payload)
        invalid["club_id"] = 1
        backups_before = len(list((os.environ.get("FLAPAMAMAKU_BACKUP_DIR") and __import__("pathlib").Path(os.environ["FLAPAMAMAKU_BACKUP_DIR"]).glob("*.db")) or []))
        try:
            _merge_club_backup(invalid, club_id)
        except RuntimeError as exc:
            assert "anderen Verein" in str(exc)
        else:
            raise AssertionError("Cross-club import must be rejected")
        backups_after = len(list((os.environ.get("FLAPAMAMAKU_BACKUP_DIR") and __import__("pathlib").Path(os.environ["FLAPAMAMAKU_BACKUP_DIR"]).glob("*.db")) or []))
        assert backups_after == backups_before

        migration_payload = {
            "format": "flapamamaku-server-migration",
            "format_version": 2,
            "club_slug": "backup-test",
            "club_name": "Backup Test",
            "club_backup": payload,
            "users": [],
            "memberships": [],
            "manifest": {
                "club_id": club_id,
                "club_slug": "backup-test",
                "club_name": "Backup Test",
                "exported_at": "2026-10-02T10:00:00+00:00",
                "source_server_url": "https://source.example.ch",
                "schema_version": payload["schema_version"],
                "package_version": 2,
                "checksum_sha256": "",
            },
        }
        migration_payload["manifest"]["checksum_sha256"] = _server_migration_checksum(migration_payload)
        assert _validate_server_migration_envelope(migration_payload) is migration_payload

        tampered = copy.deepcopy(migration_payload)
        tampered["club_name"] = "Manipuliert"
        try:
            _validate_server_migration_envelope(tampered)
        except RuntimeError as exc:
            assert "Prüfsumme" in str(exc)
        else:
            raise AssertionError("Manipuliertes Migrationspaket muss abgelehnt werden")

        legacy_migration_payload = copy.deepcopy(migration_payload)
        legacy_migration_payload["format_version"] = 1
        legacy_migration_payload.pop("manifest")
        assert _validate_server_migration_envelope(legacy_migration_payload) is legacy_migration_payload

        html = open("static/admin.html", encoding="utf-8").read()
        assert 'id="club-backup-card"' in html
        assert 'id="club-backup-download"' in html
        assert 'id="club-restore-start"' in html
    finally:
        _REQUEST_CLUB_ID.reset(context)

    print("club-scoped backup export/import ok")


if __name__ == "__main__":
    main()
