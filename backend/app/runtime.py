import os

from . import main as main_app

app = main_app.app

# Production wrapper only. The recovered multi-club core in app.main is the
# single source of truth for club selection, tenant isolation, media, members,
# billing and suspension. Do not inject a second platform/club selector here.
RUNTIME_VERSION = os.getenv("FLAPAMAMAKU_API_VERSION", "0.9.3").strip() or "0.9.3"
main_app.API_VERSION = RUNTIME_VERSION
app.version = RUNTIME_VERSION
