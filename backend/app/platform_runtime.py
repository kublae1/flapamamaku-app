from pathlib import Path

from fastapi.staticfiles import StaticFiles

from .platform import app

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="platform-static")
