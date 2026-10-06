"""Compatibility guards for the recovered multi-club backend.

The stable multi-club core predates the annual-sujet domain model. After the
branches were recombined, its legacy /api/content handlers are registered
before the Phase 4/5 handlers. Patch the existing FastAPI dependants so legacy
sujet/archive writes are rejected exactly as in the later application, while
keeping the stable multi-club data model intact.

Phase 4/5 also added a textual ``club_id`` compatibility column to tables that
the integrated multi-club model scopes through user_clubs or active_club_id.
Normalise those compatibility columns after all startup migrations so every
row references an existing numeric club without replacing the canonical
multi-club relations.
"""

from __future__ import annotations

import sqlite3
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


def _columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {str(row["name"]) for row in db.execute(f"PRAGMA table_info({table})")}


def _table_exists(db: sqlite3.Connection, table: str) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def _valid_default_club_id(db: sqlite3.Connection) -> int:
    row = db.execute(
        "SELECT id FROM clubs WHERE active = 1 ORDER BY CASE WHEN id=1 THEN 0 ELSE 1 END, id LIMIT 1"
    ).fetchone()
    if row is None:
        raise RuntimeError("No active club available for tenant recovery")
    return int(row["id"])


def _install_live_compatibility_triggers(db: sqlite3.Connection) -> None:
    """Keep legacy club_id columns valid for rows created after startup."""
    if _table_exists(db, "user_clubs") and _table_exists(db, "users"):
        if "club_id" in _columns(db, "users"):
            db.execute("DROP TRIGGER IF EXISTS user_clubs_compat_user_club_insert")
            db.execute("DROP TRIGGER IF EXISTS user_clubs_compat_user_club_update")
            db.execute(
                """
                CREATE TRIGGER user_clubs_compat_user_club_insert
                AFTER INSERT ON user_clubs
                WHEN NEW.active = 1
                BEGIN
                    UPDATE users
                    SET club_id = NEW.club_id
                    WHERE id = NEW.user_id
                      AND (
                          club_id IS NULL OR
                          NOT EXISTS (
                              SELECT 1 FROM clubs c
                              WHERE c.id = CAST(users.club_id AS INTEGER)
                          )
                      );
                END
                """
            )
            db.execute(
                """
                CREATE TRIGGER user_clubs_compat_user_club_update
                AFTER UPDATE OF club_id, active ON user_clubs
                WHEN NEW.active = 1
                BEGIN
                    UPDATE users
                    SET club_id = NEW.club_id
                    WHERE id = NEW.user_id
                      AND (
                          club_id IS NULL OR
                          NOT EXISTS (
                              SELECT 1 FROM clubs c
                              WHERE c.id = CAST(users.club_id AS INTEGER)
                          )
                      );
                END
                """
            )

    if _table_exists(db, "sessions"):
        cols = _columns(db, "sessions")
        if {"club_id", "active_club_id"}.issubset(cols):
            db.execute("DROP TRIGGER IF EXISTS sessions_compat_club_insert")
            db.execute("DROP TRIGGER IF EXISTS sessions_compat_club_update")
            db.execute(
                """
                CREATE TRIGGER sessions_compat_club_insert
                AFTER INSERT ON sessions
                WHEN NEW.active_club_id IS NOT NULL
                 AND EXISTS (SELECT 1 FROM clubs c WHERE c.id = NEW.active_club_id)
                BEGIN
                    UPDATE sessions SET club_id = NEW.active_club_id
                    WHERE token_hash = NEW.token_hash;
                END
                """
            )
            db.execute(
                """
                CREATE TRIGGER sessions_compat_club_update
                AFTER UPDATE OF active_club_id ON sessions
                WHEN NEW.active_club_id IS NOT NULL
                 AND EXISTS (SELECT 1 FROM clubs c WHERE c.id = NEW.active_club_id)
                BEGIN
                    UPDATE sessions SET club_id = NEW.active_club_id
                    WHERE token_hash = NEW.token_hash;
                END
                """
            )


def _repair_compatibility_club_ids() -> None:
    """Ensure every Phase-4/5 compatibility club_id references a real club."""
    try:
        with main_app.connect() as db:
            if not _table_exists(db, "clubs"):
                return
            default_club_id = _valid_default_club_id(db)

            if _table_exists(db, "users") and "club_id" in _columns(db, "users"):
                db.execute(
                    """
                    UPDATE users
                    SET club_id = COALESCE(
                        (
                            SELECT uc.club_id
                            FROM user_clubs uc
                            JOIN clubs c ON c.id = uc.club_id
                            WHERE uc.user_id = users.id AND uc.active = 1 AND c.active = 1
                            ORDER BY CASE WHEN uc.club_id = ? THEN 0 ELSE 1 END, uc.club_id
                            LIMIT 1
                        ),
                        ?
                    )
                    WHERE club_id IS NULL
                       OR NOT EXISTS (
                           SELECT 1 FROM clubs c
                           WHERE c.id = CAST(users.club_id AS INTEGER)
                       )
                    """,
                    (default_club_id, default_club_id),
                )

            if _table_exists(db, "sessions") and "club_id" in _columns(db, "sessions"):
                session_columns = _columns(db, "sessions")
                if "active_club_id" in session_columns:
                    db.execute(
                        """
                        UPDATE sessions
                        SET club_id = CASE
                            WHEN EXISTS (
                                SELECT 1 FROM clubs c WHERE c.id = sessions.active_club_id
                            ) THEN sessions.active_club_id
                            ELSE ?
                        END
                        WHERE club_id IS NULL
                           OR NOT EXISTS (
                               SELECT 1 FROM clubs c
                               WHERE c.id = CAST(sessions.club_id AS INTEGER)
                           )
                        """,
                        (default_club_id,),
                    )

            for table in ("push_tokens", "gallery_snapshots"):
                if not _table_exists(db, table):
                    continue
                cols = _columns(db, table)
                if "club_id" not in cols or "user_id" not in cols:
                    continue
                safe = table.replace('"', '""')
                db.execute(
                    f"""
                    UPDATE "{safe}"
                    SET club_id = COALESCE(
                        (
                            SELECT uc.club_id
                            FROM user_clubs uc
                            JOIN clubs c ON c.id = uc.club_id
                            WHERE uc.user_id = "{safe}".user_id
                              AND uc.active = 1 AND c.active = 1
                            ORDER BY CASE WHEN uc.club_id = ? THEN 0 ELSE 1 END, uc.club_id
                            LIMIT 1
                        ),
                        ?
                    )
                    WHERE club_id IS NULL
                       OR NOT EXISTS (
                           SELECT 1 FROM clubs c
                           WHERE c.id = CAST("{safe}".club_id AS INTEGER)
                       )
                    """,
                    (default_club_id, default_club_id),
                )

            for table in (
                "annual_sujets",
                "annual_sujet_images",
                "poll_votes",
                "poll_suggestions",
                "push_notifications",
            ):
                if not _table_exists(db, table) or "club_id" not in _columns(db, table):
                    continue
                safe = table.replace('"', '""')
                db.execute(
                    f"""
                    UPDATE "{safe}"
                    SET club_id = ?
                    WHERE club_id IS NULL
                       OR NOT EXISTS (
                           SELECT 1 FROM clubs c
                           WHERE c.id = CAST("{safe}".club_id AS INTEGER)
                       )
                    """,
                    (default_club_id,),
                )

            _install_live_compatibility_triggers(db)
            db.commit()
    except sqlite3.Error:
        main_app.logger.exception("Compatibility club-id recovery failed")
        raise


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

    if _repair_compatibility_club_ids not in main_app.app.router.on_startup:
        main_app.app.router.on_startup.append(_repair_compatibility_club_ids)


install_recovery_guards()
