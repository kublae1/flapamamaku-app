from __future__ import annotations

import io

from PIL import Image

from app.main import (
    MAX_IMAGE_DIMENSION,
    MAX_STORED_IMAGE_BYTES,
    TARGET_STORED_IMAGE_BYTES,
    _optimize_image,
)


def _jpeg_bytes(width: int, height: int, quality: int = 95) -> bytes:
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            pixels[x, y] = (
                (x * 13 + y * 7) % 256,
                (x * 5 + y * 17) % 256,
                (x * 19 + y * 3) % 256,
            )
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=quality)
    return output.getvalue()


def main() -> None:
    original = _jpeg_bytes(2600, 1800)
    optimized, mime = _optimize_image(original, "image/jpeg")

    assert mime == "image/webp"
    assert len(optimized) < len(original)
    assert len(optimized) <= MAX_STORED_IMAGE_BYTES

    with Image.open(io.BytesIO(optimized)) as image:
        assert max(image.size) <= MAX_IMAGE_DIMENSION
        assert image.width / image.height == pytest_approx(2600 / 1800, rel=0.02)

    # Realistic uploads should normally meet the compact target.
    assert len(optimized) <= TARGET_STORED_IMAGE_BYTES

    # Already small images must still remain compact and valid.
    small = _jpeg_bytes(480, 320, quality=90)
    small_optimized, small_mime = _optimize_image(small, "image/jpeg")
    assert small_mime == "image/webp"
    assert len(small_optimized) <= MAX_STORED_IMAGE_BYTES
    with Image.open(io.BytesIO(small_optimized)) as image:
        assert image.size == (480, 320)

    print(
        "image optimization ok:",
        {
            "original_bytes": len(original),
            "optimized_bytes": len(optimized),
            "small_bytes": len(small_optimized),
        },
    )


def pytest_approx(value: float, rel: float) -> object:
    # Tiny local helper avoids adding pytest as a runtime dependency.
    class Approx:
        def __eq__(self, other: object) -> bool:
            try:
                actual = float(other)
            except (TypeError, ValueError):
                return False
            tolerance = abs(value) * rel
            return abs(actual - value) <= tolerance

    return Approx()


if __name__ == "__main__":
    main()
