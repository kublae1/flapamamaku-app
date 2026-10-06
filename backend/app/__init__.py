"""FLAPAMAMAKU backend package bootstrap.

Keep the recovered integrated multi-club core and the later Phase 4/5
extensions active for every import path, including direct ``app.main:app``
starts used by CI.  Importing runtime afterwards applies the compatibility
recovery that removes obsolete single-instance guards and scopes member
identity to the active club.
"""

from . import main as _main
from .phase45 import install_phase45

install_phase45(
    _main.app,
    connect=_main.connect,
    current_user=_main.current_user,
    require=_main.require,
    optimize_image=_main._optimize_image,
    instance_id=_main.INSTANCE_ID,
    is_production=_main.IS_PRODUCTION,
)

# Runtime is imported for its compatibility/recovery hooks.  It reuses the same
# FastAPI app object and is intentionally imported only after Phase 4/5 is
# installed, so its initializer wrapper can reconcile the recovered multi-club
# schema after the Phase 4/5 migrations run.
from . import runtime as _runtime  # noqa: E402,F401
