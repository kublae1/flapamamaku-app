import asyncio
from datetime import datetime, timezone
from io import BytesIO

from fastapi import UploadFile
from PIL import Image

from app.main import (
    _REQUEST_CLUB_ID,
    _app_config,
    _optimize_logo_image,
    connect,
    get_app_logo,
    init_db,
    upload_app_logo,
)


def _image_bytes(fmt: str, color: tuple[int, int, int, int] = (20, 80, 160, 255)) -> bytes:
    mode = "RGBA" if fmt in {"PNG", "WEBP"} else "RGB"
    image = Image.new(mode, (48, 32), color if mode == "RGBA" else color[:3])
    buffer = BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def _upload(club_id: int, raw: bytes, filename: str, mime: str) -> dict:
    context = _REQUEST_CLUB_ID.set(club_id)
    try:
        upload = UploadFile(
            filename=filename,
            file=BytesIO(raw),
            headers={"content-type": mime},
        )
        return asyncio.run(upload_app_logo(logo=upload, _={"can_manage_settings": True}))
    finally:
        _REQUEST_CLUB_ID.reset(context)


def _config(club_id: int) -> dict:
    context = _REQUEST_CLUB_ID.set(club_id)
    try:
        return _app_config()
    finally:
        _REQUEST_CLUB_ID.reset(context)


def test_logo_format_validation_preserves_supported_types():
    for fmt, mime in (
        ("PNG", "image/png"),
        ("JPEG", "image/jpeg"),
        ("WEBP", "image/webp"),
    ):
        optimized, stored_mime = _optimize_logo_image(_image_bytes(fmt), mime)
        assert optimized
        assert stored_mime == mime
        with Image.open(BytesIO(optimized)) as image:
            assert image.format == fmt


def test_tenant_logo_upload_public_delivery_and_restart_persistence():
    init_db()
    now = datetime.now(timezone.utc).isoformat()

    with connect() as db:
        club2 = db.execute(
            """
            INSERT INTO clubs (
                slug, name, short_name, active,
                primary_color, secondary_color, created_at, updated_at
            ) VALUES (
                'logo-verein-2', 'Logo Verein 2', 'V2', 1,
                '#225588', '#FFFFFF', ?, ?
            )
            """,
            (now, now),
        ).lastrowid
        db.commit()

    club1_source = _image_bytes("PNG", (140, 16, 27, 255))
    club2_source = _image_bytes("PNG", (34, 85, 136, 255))

    config1 = _upload(1, club1_source, "flapamamaku.png", "image/png")
    config2 = _upload(club2, club2_source, "verein2.png", "image/png")

    assert config1["club_id"] == 1
    assert f"club_id=1" in config1["logo_url"]
    assert "&v=" in config1["logo_url"]
    assert config2["club_id"] == club2
    assert f"club_id={club2}" in config2["logo_url"]
    assert "&v=" in config2["logo_url"]
    assert config1["logo_url"] != config2["logo_url"]

    response1 = get_app_logo(club_id=1)
    response2 = get_app_logo(club_id=club2)
    assert response1.media_type == "image/png"
    assert response2.media_type == "image/png"
    assert response1.body.startswith(b"\x89PNG\r\n\x1a\n")
    assert response2.body.startswith(b"\x89PNG\r\n\x1a\n")
    assert response1.body != response2.body
    assert response1.headers["cache-control"] == "public, max-age=300, must-revalidate"
    assert response2.headers["cache-control"] == "public, max-age=300, must-revalidate"

    with connect() as db:
        stored1 = db.execute(
            "SELECT logo, logo_mime FROM clubs WHERE id = 1"
        ).fetchone()
        stored2 = db.execute(
            "SELECT logo, logo_mime FROM clubs WHERE id = ?",
            (club2,),
        ).fetchone()
        assert stored1["logo_mime"] == "image/png"
        assert stored2["logo_mime"] == "image/png"
        assert bytes(stored1["logo"]) == response1.body
        assert bytes(stored2["logo"]) == response2.body

    assert _config(1)["logo_url"] == config1["logo_url"]
    assert _config(club2)["logo_url"] == config2["logo_url"]

    # Re-running init_db models a container restart against the same /data DB.
    init_db()
    after_restart1 = get_app_logo(club_id=1)
    after_restart2 = get_app_logo(club_id=club2)
    assert after_restart1.body == response1.body
    assert after_restart2.body == response2.body
    assert _config(1)["logo_url"] == config1["logo_url"]
    assert _config(club2)["logo_url"] == config2["logo_url"]


def test_logo_replacement_changes_cache_key_without_touching_other_tenant():
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        club2 = db.execute(
            """
            INSERT INTO clubs (
                slug, name, short_name, active,
                primary_color, secondary_color, created_at, updated_at
            ) VALUES (
                'logo-cache-verein', 'Logo Cache Verein', 'LCV', 1,
                '#111111', '#FFFFFF', ?, ?
            )
            """,
            (now, now),
        ).lastrowid
        db.commit()

    _upload(1, _image_bytes("PNG", (1, 2, 3, 255)), "club1.png", "image/png")
    first = _upload(club2, _image_bytes("PNG", (4, 5, 6, 255)), "first.png", "image/png")
    club1_url = _config(1)["logo_url"]

    second = _upload(club2, _image_bytes("PNG", (7, 8, 9, 255)), "second.png", "image/png")
    assert first["logo_url"] != second["logo_url"]
    assert _config(1)["logo_url"] == club1_url


def main() -> None:
    test_logo_format_validation_preserves_supported_types()
    test_tenant_logo_upload_public_delivery_and_restart_persistence()
    test_logo_replacement_changes_cache_key_without_touching_other_tenant()
    print("tenant club logo delivery and persistence ok")


if __name__ == "__main__":
    main()
