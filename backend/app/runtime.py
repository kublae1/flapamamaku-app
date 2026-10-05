import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from . import main as main_app

app = main_app.app
INSTANCE_ID = main_app.INSTANCE_ID
PLATFORM_DB = Path(os.getenv("FLAPAMAMAKU_PLATFORM_DB", "/platform/platform.db"))

# Production wrapper only. The recovered multi-club core in app.main is the
# single source of truth for club selection, tenant isolation, media, members,
# billing and suspension. Do not inject a second platform/club selector here.
RUNTIME_VERSION = os.getenv("FLAPAMAMAKU_API_VERSION", "0.9.3").strip() or "0.9.3"
main_app.API_VERSION = RUNTIME_VERSION
app.version = RUNTIME_VERSION


_TENANT_TABLES = (
    "news",
    "events",
    "members",
    "member_filters",
    "content_items",
    "content_images",
    "event_registrations",
    "users",
    "sessions",
    "push_tokens",
    "annual_sujets",
    "annual_sujet_images",
    "gallery_snapshots",
    "poll_votes",
    "poll_suggestions",
    "push_notifications",
)


def _columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {str(row["name"]) for row in db.execute(f"PRAGMA table_info({table})")}


def _table_exists(db: sqlite3.Connection, table: str) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def _drop_single_instance_guards(db: sqlite3.Connection) -> None:
    """Remove Phase-4/5 triggers that reject integer multi-club IDs."""
    rows = db.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='trigger'
          AND (name LIKE '%_club_guard_insert' OR name LIKE '%_club_guard_update')
        """
    ).fetchall()
    for row in rows:
        name = str(row["name"]).replace('"', '""')
        db.execute(f'DROP TRIGGER IF EXISTS "{name}"')


def _normalize_club_ids(db: sqlite3.Connection) -> None:
    """Convert legacy instance-slug club IDs back to integrated numeric IDs."""
    if not _table_exists(db, "clubs"):
        return
    for table in _TENANT_TABLES:
        if not _table_exists(db, table) or "club_id" not in _columns(db, table):
            continue
        safe_table = table.replace('"', '""')
        db.execute(
            f"""
            UPDATE "{safe_table}"
            SET club_id = (
                SELECT c.id
                FROM clubs c
                WHERE lower(c.slug) = lower(CAST("{safe_table}".club_id AS TEXT))
                LIMIT 1
            )
            WHERE typeof(club_id) = 'text'
              AND EXISTS (
                SELECT 1 FROM clubs c
                WHERE lower(c.slug) = lower(CAST("{safe_table}".club_id AS TEXT))
              )
            """
        )


def _install_member_mapping(db: sqlite3.Connection) -> None:
    """Persist member identity per user and club instead of globally."""
    required = {"users", "members", "user_clubs"}
    if not all(_table_exists(db, table) for table in required):
        return
    if "club_id" not in _columns(db, "members"):
        return

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS user_club_members (
            user_id INTEGER NOT NULL,
            club_id INTEGER NOT NULL,
            member_id INTEGER,
            PRIMARY KEY(user_id, club_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(club_id) REFERENCES clubs(id),
            FOREIGN KEY(member_id) REFERENCES members(id)
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_club_members_member ON user_club_members(member_id)"
    )

    # Preserve every already-valid legacy association. Cross-club associations
    # are intentionally not copied.
    db.execute(
        """
        INSERT OR IGNORE INTO user_club_members(user_id, club_id, member_id)
        SELECT uc.user_id, uc.club_id,
               CASE WHEN m.club_id = uc.club_id THEN u.member_id ELSE NULL END
        FROM user_clubs uc
        JOIN users u ON u.id = uc.user_id
        LEFT JOIN members m ON m.id = u.member_id
        """
    )

    # Conservative recovery for old records: only map automatically when there
    # is exactly one unambiguous member in that club matching username to either
    # member e-mail or member name.
    missing = db.execute(
        """
        SELECT ucm.user_id, ucm.club_id, u.username
        FROM user_club_members ucm
        JOIN users u ON u.id = ucm.user_id
        WHERE ucm.member_id IS NULL
        """
    ).fetchall()
    for row in missing:
        matches = db.execute(
            """
            SELECT id
            FROM members
            WHERE club_id = ?
              AND (
                lower(trim(email)) = lower(trim(?))
                OR lower(trim(name)) = lower(trim(?))
              )
            ORDER BY id
            """,
            (row["club_id"], row["username"], row["username"]),
        ).fetchall()
        if len(matches) == 1:
            db.execute(
                """
                UPDATE user_club_members
                SET member_id = ?
                WHERE user_id = ? AND club_id = ?
                """,
                (matches[0]["id"], row["user_id"], row["club_id"]),
            )

    # Cross-club member IDs are forbidden at the storage boundary.
    db.execute("DROP TRIGGER IF EXISTS user_club_members_guard_insert")
    db.execute("DROP TRIGGER IF EXISTS user_club_members_guard_update")
    db.execute(
        """
        CREATE TRIGGER user_club_members_guard_insert
        BEFORE INSERT ON user_club_members
        WHEN NEW.member_id IS NOT NULL
         AND NOT EXISTS (
             SELECT 1 FROM members m
             WHERE m.id = NEW.member_id AND m.club_id = NEW.club_id
         )
        BEGIN
            SELECT RAISE(ABORT, 'member belongs to another club');
        END
        """
    )
    db.execute(
        """
        CREATE TRIGGER user_club_members_guard_update
        BEFORE UPDATE OF member_id, club_id ON user_club_members
        WHEN NEW.member_id IS NOT NULL
         AND NOT EXISTS (
             SELECT 1 FROM members m
             WHERE m.id = NEW.member_id AND m.club_id = NEW.club_id
         )
        BEGIN
            SELECT RAISE(ABORT, 'member belongs to another club');
        END
        """
    )

    # A newly assigned member is stored against that member's club.
    db.execute("DROP TRIGGER IF EXISTS users_member_mapping_update")
    db.execute(
        """
        CREATE TRIGGER users_member_mapping_update
        AFTER UPDATE OF member_id ON users
        WHEN NEW.member_id IS NOT NULL
        BEGIN
            INSERT INTO user_club_members(user_id, club_id, member_id)
            SELECT NEW.id, m.club_id, NEW.member_id
            FROM members m
            JOIN user_clubs uc
              ON uc.user_id = NEW.id AND uc.club_id = m.club_id AND uc.active = 1
            WHERE m.id = NEW.member_id
            ON CONFLICT(user_id, club_id) DO UPDATE SET member_id=excluded.member_id;
        END
        """
    )

    db.execute("DROP TRIGGER IF EXISTS user_clubs_member_mapping_insert")
    db.execute(
        """
        CREATE TRIGGER user_clubs_member_mapping_insert
        AFTER INSERT ON user_clubs
        BEGIN
            INSERT OR IGNORE INTO user_club_members(user_id, club_id, member_id)
            SELECT NEW.user_id, NEW.club_id,
                   CASE WHEN m.club_id = NEW.club_id THEN u.member_id ELSE NULL END
            FROM users u
            LEFT JOIN members m ON m.id = u.member_id
            WHERE u.id = NEW.user_id;
        END
        """
    )

    # Keep the legacy column usable for old code paths, but the authoritative
    # identity exposed to clients is resolved below from user_club_members.
    if _table_exists(db, "sessions") and "active_club_id" in _columns(db, "sessions"):
        db.execute("DROP TRIGGER IF EXISTS sessions_member_context_insert")
        db.execute("DROP TRIGGER IF EXISTS sessions_member_context_update")
        db.execute(
            """
            CREATE TRIGGER sessions_member_context_insert
            AFTER INSERT ON sessions
            WHEN NEW.active_club_id IS NOT NULL
            BEGIN
                UPDATE users
                SET member_id = (
                    SELECT ucm.member_id
                    FROM user_club_members ucm
                    WHERE ucm.user_id = NEW.user_id
                      AND ucm.club_id = NEW.active_club_id
                )
                WHERE id = NEW.user_id;
            END
            """
        )
        db.execute(
            """
            CREATE TRIGGER sessions_member_context_update
            AFTER UPDATE OF active_club_id ON sessions
            WHEN NEW.active_club_id IS NOT NULL
            BEGIN
                UPDATE users
                SET member_id = (
                    SELECT ucm.member_id
                    FROM user_club_members ucm
                    WHERE ucm.user_id = NEW.user_id
                      AND ucm.club_id = NEW.active_club_id
                )
                WHERE id = NEW.user_id;
            END
            """
        )


def _scoped_member_id(
    db: sqlite3.Connection,
    user_id: int,
    club_id: int,
) -> int | None:
    if _table_exists(db, "user_club_members"):
        row = db.execute(
            """
            SELECT ucm.member_id
            FROM user_club_members ucm
            LEFT JOIN members m
              ON m.id = ucm.member_id AND m.club_id = ucm.club_id
            WHERE ucm.user_id = ? AND ucm.club_id = ?
              AND (ucm.member_id IS NULL OR m.id IS NOT NULL)
            """,
            (user_id, club_id),
        ).fetchone()
        if row is not None:
            return int(row["member_id"]) if row["member_id"] is not None else None

    # Safe legacy fallback: accept users.member_id only if that member belongs
    # to the active club. A foreign member ID is treated as no mapping.
    row = db.execute(
        """
        SELECT u.member_id
        FROM users u
        JOIN members m ON m.id = u.member_id AND m.club_id = ?
        WHERE u.id = ?
        """,
        (club_id, user_id),
    ).fetchone()
    return int(row["member_id"]) if row is not None and row["member_id"] is not None else None


def _scoped_user_payload(
    db: sqlite3.Connection,
    row: sqlite3.Row,
    club_id: int,
) -> dict[str, Any]:
    user_id = int(row["id"])
    member_id = _scoped_member_id(db, user_id, club_id)
    member_name = ""
    if member_id is not None:
        member = db.execute(
            "SELECT name FROM members WHERE id = ? AND club_id = ?",
            (member_id, club_id),
        ).fetchone()
        if member is not None:
            member_name = str(member["name"] or "")

    club_role = main_app._user_club_access(db, user_id, club_id)
    if club_role is None:
        raise HTTPException(status_code=401, detail="Kein Zugriff auf diesen Verein")

    club = db.execute(
        """
        SELECT id, billing_status, billing_suspension_reason
        FROM clubs
        WHERE id = ? AND active = 1
        """,
        (club_id,),
    ).fetchone()
    if club is None:
        raise HTTPException(status_code=401, detail="Verein nicht gefunden")
    if str(club["billing_status"] or "active") != "active" and club_role != "super_admin":
        reason = str(club["billing_suspension_reason"] or "Ausstehende Zahlung")
        raise HTTPException(status_code=403, detail=f"Verein gesperrt: {reason}")

    item = dict(row)
    item["member_id"] = member_id
    item["member_name"] = member_name
    item["club_role"] = club_role
    item["current_club_id"] = club_id
    item["is_super_admin"] = club_role == "super_admin"
    return main_app._serialize_user(item)


_legacy_current_user = main_app.current_user
_legacy_user_profile = main_app._user_profile


def scoped_current_user(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    token = main_app._extract_token(authorization)
    now = datetime.now(timezone.utc).isoformat()
    with main_app.connect() as db:
        row = db.execute(
            """
            SELECT u.*, s.active_club_id
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
              AND s.expires_at > ?
              AND u.active = 1
            """,
            (main_app._token_hash(token), now),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="Sitzung ungültig oder abgelaufen")
        club_id = int(row["active_club_id"] or main_app._instance_club_id(db))
        return _scoped_user_payload(db, row, club_id)


def scoped_user_profile(user_id: int) -> dict[str, Any]:
    with main_app.connect() as db:
        club_id = main_app._active_club_id(db)
        row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="Benutzer nicht gefunden")
        return _scoped_user_payload(db, row, club_id)


def _rebind_current_user_dependency(dependant: Any) -> None:
    if getattr(dependant, "call", None) is _legacy_current_user:
        dependant.call = scoped_current_user
    for child in getattr(dependant, "dependencies", ()) or ():
        _rebind_current_user_dependency(child)


# Functions such as login() resolve these names dynamically, while FastAPI
# Depends objects captured the original callable during route registration. Fix
# both so every production path uses the same club-scoped identity resolver.
main_app.current_user = scoped_current_user
main_app._user_profile = scoped_user_profile
for _route in app.routes:
    _dependant = getattr(_route, "dependant", None)
    if _dependant is not None:
        _rebind_current_user_dependency(_dependant)


def recover_multiclub_state() -> None:
    try:
        with main_app.connect() as db:
            _drop_single_instance_guards(db)
            _normalize_club_ids(db)
            _install_member_mapping(db)
            db.commit()
    except sqlite3.Error:
        main_app.logger.exception("Multi-club recovery migration failed")
        raise


@app.on_event("startup")
async def run_multiclub_recovery() -> None:
    # main.app's own startup runs first and creates/migrates the base schema.
    recover_multiclub_state()


def platform_access_state() -> tuple[str, str]:
    """Keep Phase-9 external suspension for true one-club pilot instances.

    The recovered FLAPAMAMAKU deployment is an integrated multi-club host and
    therefore uses the stable per-club billing/suspension model in app.main.
    Applying one external status to that host would incorrectly suspend every
    club at once.
    """
    if INSTANCE_ID == "flapamamaku" or not PLATFORM_DB.exists():
        return "active", ""
    try:
        db = sqlite3.connect(f"file:{PLATFORM_DB}?mode=ro", uri=True, timeout=2)
        db.row_factory = sqlite3.Row
        try:
            row = db.execute(
                "SELECT status,suspension_reason FROM platform_clubs WHERE instance_id=? COLLATE NOCASE",
                (INSTANCE_ID,),
            ).fetchone()
        finally:
            db.close()
    except sqlite3.Error:
        return "active", ""
    if not row:
        return "active", ""
    return str(row["status"]), str(row["suspension_reason"] or "")


@app.middleware("http")
async def phase9_pilot_instance_access_control(request: Request, call_next):
    if INSTANCE_ID == "flapamamaku":
        return await call_next(request)
    path = request.url.path
    if path == "/api/health" or path.endswith("flapamamaku-icon.png"):
        return await call_next(request)
    status, reason = platform_access_state()
    if status == "active":
        return await call_next(request)
    message = reason or "Dieser Verein ist durch die Plattformverwaltung vorübergehend gesperrt."
    if path.startswith("/api/"):
        return JSONResponse(
            status_code=423,
            content={"detail": message, "club_status": "suspended"},
        )
    return HTMLResponse(
        status_code=423,
        content=(
            "<!doctype html><html><head><meta charset='utf-8'><title>Verein gesperrt</title>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'></head>"
            "<body style='font-family:system-ui;margin:3rem;max-width:720px'>"
            "<h1>Zugriff vorübergehend gesperrt</h1><p>" + message + "</p></body></html>"
        ),
    )
