from __future__ import annotations

import asyncio
import io

from fastapi import HTTPException, UploadFile
from PIL import Image
from starlette.datastructures import Headers

from app.main import (
    BootstrapPayload,
    _REQUEST_CLUB_ID,
    _require_permanent_gallery_allowed,
    bootstrap,
    connect,
    init_db,
    post_gallery_snapshot,
)


def _png_bytes() -> bytes:
    image = Image.new("RGB", (64, 48), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _upload() -> UploadFile:
    return UploadFile(
        file=io.BytesIO(_png_bytes()),
        filename="snapshot.png",
        headers=Headers({"content-type": "image/png"}),
    )


async def _assert_snapshot_days(user: dict, days: int) -> None:
    item = await post_gallery_snapshot(
        image=_upload(),
        expires_days=days,
        user=user,
    )
    assert item["is_snapshot"] is True
    assert item["expires_at"]


async def main_async() -> None:
    init_db()
    user = bootstrap(
        BootstrapPayload(
            username="snapshot-admin",
            password="Testpass123!",
            member_id=None,
        )
    )

    for days in (1, 3, 7):
        await _assert_snapshot_days(user, days)

    try:
        await post_gallery_snapshot(
            image=_upload(),
            expires_days=14,
            user=user,
        )
    except HTTPException as exc:
        assert exc.status_code == 422
    else:
        raise AssertionError("14-day snapshots must be rejected")

    token = _REQUEST_CLUB_ID.set(2)
    try:
        with connect() as db:
            try:
                _require_permanent_gallery_allowed(db, "gallery")
            except HTTPException as exc:
                assert exc.status_code == 403
            else:
                raise AssertionError("External clubs must not create permanent gallery entries")

            _require_permanent_gallery_allowed(db, "photos")
    finally:
        _REQUEST_CLUB_ID.reset(token)

    print("gallery snapshot retention ok")


if __name__ == "__main__":
    asyncio.run(main_async())
