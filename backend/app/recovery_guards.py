"""Compatibility guards for the recovered multi-club backend.

The stable multi-club core predates the annual-sujet domain model.  After the
branches were recombined, its legacy /api/content handlers are registered
before the Phase 4/5 handlers.  Patch the existing FastAPI dependants so legacy
sujet/archive writes are rejected exactly as in the later application, while
keeping the stable multi-club data model intact.
"""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException

from . import main as main_app


_BLOCKED_SECTIONS = {"sujet", "archive"}


def _guard_content_write(original: Callable[..., Any]) -> Callable[..., Any]:
    def guarded(*args: Any, **kwargs: Any) -> Any:
        payload = kwargs.get("payload")
        if payload is None and args:
            payload = args[0]
        section = str(getattr(payload, "section", "") or "").strip().lower()
        if section in _BLOCKED_SECTIONS:
            raise HTTPException(
                status_code=409,
                detail="Sujet-Inhalte werden über die Jahres-Sujet-Verwaltung gepflegt.",
            )
        return original(*args, **kwargs)

    guarded.__name__ = getattr(original, "__name__", "guarded_content_write")
    guarded.__doc__ = getattr(original, "__doc__", None)
    return guarded


def install_recovery_guards() -> None:
    if getattr(main_app.app.state, "recovery_guards_installed", False):
        return
    main_app.app.state.recovery_guards_installed = True

    for route in main_app.app.routes:
        if getattr(route, "path", None) != "/api/content":
            continue
        methods = set(getattr(route, "methods", set()) or set())
        if not ({"POST", "PUT"} & methods):
            continue
        dependant = getattr(route, "dependant", None)
        original = getattr(dependant, "call", None)
        if callable(original):
            dependant.call = _guard_content_write(original)


install_recovery_guards()
