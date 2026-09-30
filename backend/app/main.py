import asyncio
import calendar
import base64
import hashlib
import hmac
import io
import json
import logging
import os
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account
from pydantic import BaseModel, Field
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageSequence


DB_PATH = Path(os.getenv("FLAPAMAMAKU_DB", "/data/flapamamaku.db"))
BACKUP_DIR = Path(os.getenv("FLAPAMAMAKU_BACKUP_DIR", "/data/backups"))
BACKUP_RETENTION = max(3, int(os.getenv("FLAPAMAMAKU_BACKUP_RETENTION", "14")))
BACKUP_INTERVAL_SECONDS = max(
    3600,
    int(os.getenv("FLAPAMAMAKU_BACKUP_INTERVAL_SECONDS", "86400")),
)
MAX_BACKUP_UPLOAD_BYTES = max(
    10 * 1024 * 1024,
    int(os.getenv("FLAPAMAMAKU_MAX_BACKUP_UPLOAD_BYTES", str(256 * 1024 * 1024))),
)
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
SESSION_LIFETIME_DAYS = max(
    1,
    int(os.getenv("FLAPAMAMAKU_SESSION_LIFETIME_DAYS", "90")),
)
LOGIN_RATE_WINDOW_SECONDS = max(
    60,
    int(os.getenv("FLAPAMAMAKU_LOGIN_RATE_WINDOW_SECONDS", "600")),
)
LOGIN_RATE_MAX_ATTEMPTS = max(
    3,
    int(os.getenv("FLAPAMAMAKU_LOGIN_RATE_MAX_ATTEMPTS", "5")),
)
LOGIN_LOCKOUT_SECONDS = max(
    60,
    int(os.getenv("FLAPAMAMAKU_LOGIN_LOCKOUT_SECONDS", "900")),
)
_LOGIN_RATE_LOCK = threading.Lock()
_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
_LOGIN_LOCKED_UNTIL: dict[str, float] = {}

API_VERSION = "0.8.69"
# Stable identifier for one autonomous club instance. It is public metadata and
# lets a white-label app reject an accidentally configured server of another club.
INSTANCE_ID = (
    os.getenv("FLAPAMAMAKU_INSTANCE_ID", "flapamamaku").strip().lower()
    or "flapamamaku"
)
if not all(char.isalnum() or char == "-" for char in INSTANCE_ID):
    raise RuntimeError("FLAPAMAMAKU_INSTANCE_ID may only contain a-z, 0-9 and '-'")
# Exposed via /api/health to verify which backend image is actually deployed.
BUILD_SHA = os.getenv("FLAPAMAMAKU_BUILD_SHA", "development").strip() or "development"
CURRENT_SCHEMA_VERSION = 17
APP_ENV = os.getenv("FLAPAMAMAKU_ENV", "development").strip().lower()
IS_PRODUCTION = APP_ENV == "production"
logger = logging.getLogger("flapamamaku.push")
FIREBASE_SERVICE_ACCOUNT_JSON = os.getenv(
    "FLAPAMAMAKU_FIREBASE_SERVICE_ACCOUNT_JSON",
    "",
).strip()
PUSH_ICON_URL = os.getenv(
    "FLAPAMAMAKU_PUSH_ICON_URL",
    "https://flapamamaku.kublaecloud.synology.me/flapamamaku-icon.png",
).strip()
BILLING_ISSUER_NAME = (
    os.getenv("FLAPAMAMAKU_BILLING_ISSUER_NAME", "Vereinsplattform").strip()
    or "Vereinsplattform"
)
BILLING_ISSUER_ADDRESS = os.getenv(
    "FLAPAMAMAKU_BILLING_ISSUER_ADDRESS",
    "",
).strip()
BILLING_PAYMENT_INFO = os.getenv(
    "FLAPAMAMAKU_BILLING_PAYMENT_INFO",
    "",
).strip()

if not FIREBASE_SERVICE_ACCOUNT_JSON:
    firebase_b64 = os.getenv(
        "FLAPAMAMAKU_FIREBASE_SERVICE_ACCOUNT_B64",
        "",
    ).strip()
    if firebase_b64:
        try:
            FIREBASE_SERVICE_ACCOUNT_JSON = base64.b64decode(
                firebase_b64
            ).decode("utf-8")
        except Exception:
            FIREBASE_SERVICE_ACCOUNT_JSON = ""

app = FastAPI(
    title="FLAPAMAMAKU API",
    version=API_VERSION,
    docs_url=None if IS_PRODUCTION else "/api/docs",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
    redoc_url=None,
)

_REQUEST_CLUB_ID: ContextVar[int | None] = ContextVar(
    "flapamamaku_request_club_id",
    default=None,
)

ALLOWED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FLAPAMAMAKU_ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]


def _production_readiness() -> dict[str, Any]:
    checks: dict[str, bool] = {
        "production_mode": IS_PRODUCTION,
        "cors_not_wildcard": bool(ALLOWED_ORIGINS) and "*" not in ALLOWED_ORIGINS,
        "cors_https_only": bool(ALLOWED_ORIGINS) and all(
            origin.startswith("https://") for origin in ALLOWED_ORIGINS
        ),
        "api_docs_disabled": app.docs_url is None and app.openapi_url is None,
        "database_exists": DB_PATH.exists(),
        "schema_current": _schema_version() == CURRENT_SCHEMA_VERSION,
        "build_identified": BUILD_SHA != "development",
        "session_lifetime_bounded": 1 <= SESSION_LIFETIME_DAYS <= 90,
    }

    database_integrity = "missing"
    if DB_PATH.exists():
        try:
            with connect() as db:
                row = db.execute("PRAGMA integrity_check").fetchone()
                database_integrity = str(row[0]).lower() if row else "unknown"
        except sqlite3.Error:
            database_integrity = "error"
    checks["database_integrity"] = database_integrity == "ok"

    backups = _backup_files()
    if backups:
        age = datetime.now(timezone.utc).timestamp() - backups[0].stat().st_mtime
        checks["recent_backup"] = age <= max(BACKUP_INTERVAL_SECONDS * 2, 172800)
    else:
        checks["recent_backup"] = False

    return {
        "ready": all(checks.values()),
        "checks": checks,
        "allowed_origins": ALLOWED_ORIGINS,
        "database_integrity": database_integrity,
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    context_token = None
    authorization = request.headers.get("authorization", "")
    if authorization.startswith("Bearer "):
        raw_token = authorization[7:].strip()
        if raw_token:
            try:
                with connect() as db:
                    session = db.execute(
                        """
                        SELECT active_club_id
                        FROM sessions
                        WHERE token_hash = ? AND expires_at > ?
                        """,
                        (
                            _token_hash(raw_token),
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    ).fetchone()
                    if session is not None and session["active_club_id"]:
                        context_token = _REQUEST_CLUB_ID.set(
                            int(session["active_club_id"])
                        )
            except sqlite3.Error:
                context_token = None
    try:
        response = await call_next(request)
    finally:
        if context_token is not None:
            _REQUEST_CLUB_ID.reset(context_token)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    if request.url.path.startswith("/api/auth/") or request.url.path.startswith("/admin"):
        response.headers["Cache-Control"] = "no-store"
    if IS_PRODUCTION:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


PERMISSION_FIELDS = (
    "can_news",
    "can_events",
    "can_members",
    "can_documents",
    "can_photos",
    "can_gallery_upload",
    "can_polls",
    "can_links",
    "can_contact",
    "can_about",
    "can_admin_page",
    "can_manage_settings",
    "can_manage_users",
)


ROLE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "member": {
        "label": "Mitglied",
        "permissions": {key: False for key in PERMISSION_FIELDS},
    },
    "editor": {
        "label": "Redaktion",
        "permissions": {
            key: key in {
                "can_news", "can_events", "can_documents", "can_photos",
                "can_gallery_upload", "can_polls", "can_links", "can_contact",
                "can_about", "can_admin_page",
            }
            for key in PERMISSION_FIELDS
        },
    },
    "board": {
        "label": "Vorstand",
        "permissions": {
            key: key != "can_manage_users"
            for key in PERMISSION_FIELDS
        },
    },
    "club_manager": {
        "label": "Vereinsverwaltung",
        "permissions": {
            key: key in {"can_admin_page", "can_manage_settings"}
            for key in PERMISSION_FIELDS
        },
    },
    "admin": {
        "label": "Administrator",
        "permissions": {key: True for key in PERMISSION_FIELDS},
    },
}


CLUB_FEATURE_DEFAULTS: dict[str, tuple[str, bool]] = {
    "news": ("News", True),
    "events": ("Termine", True),
    "members": ("Mitglieder", True),
    "documents": ("Dokumente", True),
    "gallery": ("Galerie", True),
    "photos": ("Fotoalben", True),
    "sujet_next": ("Sujet nächstes Jahr", True),
    "sujet_archive": ("Vergangene Sujet", True),
    "polls": ("Umfragen", True),
    "links": ("Links", True),
    "push_notifications": ("Push-Nachrichten", True),
    "calendar": ("Kalender", True),
    "participant_lists": ("Teilnehmerlisten", True),
}


def _normalize_role_key(value: str) -> str:
    role_key = str(value or "member").strip().lower()
    if role_key not in ROLE_DEFINITIONS:
        raise HTTPException(status_code=422, detail="Unbekannte Benutzerrolle")
    return role_key


def _normalize_permission_overrides(values: dict[str, bool] | None) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for key, value in (values or {}).items():
        if key not in PERMISSION_FIELDS:
            raise HTTPException(status_code=422, detail=f"Unbekannte Berechtigung: {key}")
        result[key] = bool(value)
    return result


def _effective_permissions(
    role_key: str,
    overrides: dict[str, bool] | None = None,
) -> dict[str, bool]:
    normalized_role = role_key if role_key in ROLE_DEFINITIONS else "member"
    permissions = dict(ROLE_DEFINITIONS[normalized_role]["permissions"])
    permissions.update(_normalize_permission_overrides(overrides))
    return permissions


class NewsPayload(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1)
    date: str
    image_url: str = ""


class EventPayload(BaseModel):
    event_date: str = ""
    day: str
    month: str
    title: str = Field(min_length=1, max_length=200)
    location: str = ""
    time: str = ""


class MemberPayload(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    role: str = "Präsident"
    since: str = ""
    birth_date: str = ""
    status: str = "Aktiv"
    member_group: str = ""
    engagement: str = ""
    filter_ids: list[int] = []
    partner_name: str = ""
    phone_mobile: str = ""
    phone_private: str = ""
    phone_work: str = ""
    email: str = ""
    address: str = ""
    occupation: str = ""
    employer: str = ""
    employer_url: str = ""


class MemberSelfUpdatePayload(BaseModel):
    partner_name: str = ""
    phone_mobile: str = ""
    phone_private: str = ""
    phone_work: str = ""
    email: str = ""
    address: str = ""
    occupation: str = ""
    employer: str = ""
    employer_url: str = ""
    engagement: str = ""


class MemberFilterPayload(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    active: bool = True


class ContentPayload(BaseModel):
    section: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=200)
    text: str = ""
    link_url: str = ""
    poll_options: list[str] = []
    poll_allow_suggestions: bool = False


class PollPayload(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    text: str = ""
    options: list[str]
    allow_suggestions: bool = False


class AppConfigPayload(BaseModel):
    app_name: str = Field(default="FLAPAMAMAKU", min_length=1, max_length=80)
    short_name: str = Field(default="", max_length=80)
    app_subtitle: str = Field(default="Fasnachtsgruppe Luzern", max_length=120)
    primary_color: str = Field(default="#8A101B", pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: str = Field(default="#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")
    club_description: str = Field(default="", max_length=4000)
    website_url: str = Field(default="", max_length=500)
    contact_email: str = Field(default="", max_length=320)
    contact_phone: str = Field(default="", max_length=80)
    club_address: str = Field(default="", max_length=500)
    city: str = Field(default="", max_length=160)
    country: str = Field(default="", max_length=120)
    app_title: str = Field(default="", max_length=120)
    welcome_text: str = Field(default="", max_length=2000)
    show_sujet: bool = True
    label_sujet: str = Field(default="Sujet nächstes Jahr", min_length=1, max_length=80)
    show_archive: bool = True
    label_archive: str = Field(default="Vergangene Sujet", min_length=1, max_length=80)
    show_photos: bool = True
    label_photos: str = Field(default="Fotoalben", min_length=1, max_length=80)
    show_documents: bool = True
    label_documents: str = Field(default="Dokumente", min_length=1, max_length=80)
    show_polls: bool = True
    label_polls: str = Field(default="Umfragen", min_length=1, max_length=80)
    show_links: bool = True
    label_links: str = Field(default="Links", min_length=1, max_length=80)


class ClubFeaturesPayload(BaseModel):
    features: dict[str, bool]
    labels: dict[str, str] = Field(default_factory=dict)


class ClubSwitchPayload(BaseModel):
    club_id: int = Field(gt=0)


class ClubCreatePayload(BaseModel):
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=120)
    short_name: str = Field(default="", max_length=80)
    subtitle: str = Field(default="", max_length=120)
    primary_color: str = Field(default="#8A101B", pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: str = Field(default="#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")
    description: str = Field(default="", max_length=4000)
    website: str = Field(default="", max_length=500)
    email: str = Field(default="", max_length=320)
    phone: str = Field(default="", max_length=80)
    address: str = Field(default="", max_length=500)
    city: str = Field(default="", max_length=160)
    country: str = Field(default="", max_length=120)
    app_title: str = Field(default="", max_length=120)
    welcome_text: str = Field(default="", max_length=2000)


class ClubBillingSettingsPayload(BaseModel):
    billing_email: str = Field(default="", max_length=320)
    amount_rappen: int = Field(default=0, ge=0, le=100000000)
    interval_months: int = Field(default=12, ge=1, le=24)
    due_days: int = Field(default=30, ge=1, le=90)
    grace_days: int = Field(default=0, ge=0, le=365)
    next_invoice_date: str = Field(default="", max_length=10)
    auto_suspend: bool = True


class ClubBillingSuspendPayload(BaseModel):
    reason: str = Field(default="Ausstehende Zahlung", min_length=1, max_length=500)


class PollVotePayload(BaseModel):
    option_index: int = Field(ge=0, le=20)


class PollSuggestionPayload(BaseModel):
    text: str = Field(min_length=1, max_length=120)


class ContentImageOrderPayload(BaseModel):
    image_ids: list[int]


class ContentOrderPayload(BaseModel):
    item_ids: list[int]


class LoginPayload(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=6, max_length=200)


class BootstrapPayload(LoginPayload):
    member_id: int | None = None


class UserPayload(BaseModel):
    member_id: int | None = None
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(default="", max_length=200)
    active: bool = True
    can_news: bool = False
    can_events: bool = False
    can_members: bool = False
    can_documents: bool = False
    can_photos: bool = False
    can_gallery_upload: bool = False
    can_polls: bool = False
    can_links: bool = False
    can_contact: bool = False
    can_about: bool = False
    can_admin_page: bool = False
    can_manage_settings: bool = False
    can_manage_users: bool = False
    role_key: str = Field(default="member", max_length=40)
    permission_overrides: dict[str, bool] = Field(default_factory=dict)


class PushTokenPayload(BaseModel):
    token: str = Field(min_length=20, max_length=4096)
    platform: str = Field(default="android", max_length=20)


class PushTokenDeletePayload(BaseModel):
    token: str = Field(min_length=20, max_length=4096)


class ManualPushPayload(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=500)
    route: str = Field(default="", max_length=80)


TABLES: dict[str, tuple[str, type[BaseModel]]] = {
    "news": (
        """
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            text TEXT NOT NULL,
            date TEXT NOT NULL,
            image_url TEXT NOT NULL DEFAULT '',
            image_data BLOB,
            image_mime TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """,
        NewsPayload,
    ),
    "events": (
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date TEXT NOT NULL DEFAULT '',
            day TEXT NOT NULL,
            month TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT NOT NULL DEFAULT '',
            time TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """,
        EventPayload,
    ),
    "members": (
        """
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Präsident',
            since TEXT NOT NULL DEFAULT '',
            birth_date TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Aktiv',
            member_group TEXT NOT NULL DEFAULT '',
            engagement TEXT NOT NULL DEFAULT '',
            partner_name TEXT NOT NULL DEFAULT '',
            phone_mobile TEXT NOT NULL DEFAULT '',
            phone_private TEXT NOT NULL DEFAULT '',
            phone_work TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            address TEXT NOT NULL DEFAULT '',
            occupation TEXT NOT NULL DEFAULT '',
            employer TEXT NOT NULL DEFAULT '',
            employer_url TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            photo_data BLOB,
            photo_mime TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """,
        MemberPayload,
    ),
}


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


MAX_UPLOAD_IMAGE_BYTES = 30 * 1024 * 1024
MAX_STORED_IMAGE_BYTES = 12 * 1024 * 1024
MAX_IMAGE_DIMENSION = 1600


def _optimize_image(data: bytes, mime: str) -> tuple[bytes, str]:
    """Resize/compress uploads without cropping; preserve aspect ratio."""
    if not data:
        raise HTTPException(status_code=400, detail="Empty image")
    if len(data) > MAX_UPLOAD_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image too large")

    normalized_mime = (mime or "").lower().strip()
    try:
        with Image.open(io.BytesIO(data)) as source:
            if normalized_mime == "image/gif" or (source.format or "").upper() == "GIF":
                frames: list[Image.Image] = []
                durations: list[int] = []
                loop = int(source.info.get("loop", 0) or 0)
                for frame in ImageSequence.Iterator(source):
                    resized = frame.convert("RGBA")
                    resized.thumbnail(
                        (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION),
                        Image.Resampling.LANCZOS,
                    )
                    frames.append(
                        resized.convert("P", palette=Image.Palette.ADAPTIVE)
                    )
                    durations.append(int(frame.info.get("duration", source.info.get("duration", 100)) or 100))

                if not frames:
                    raise HTTPException(status_code=400, detail="Invalid image")

                output = io.BytesIO()
                frames[0].save(
                    output,
                    format="GIF",
                    save_all=True,
                    append_images=frames[1:],
                    optimize=True,
                    loop=loop,
                    duration=durations,
                )
                optimized = output.getvalue()
                optimized_mime = "image/gif"
            else:
                image = ImageOps.exif_transpose(source)
                image.thumbnail(
                    (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION),
                    Image.Resampling.LANCZOS,
                )
                if image.mode not in {"RGB", "RGBA"}:
                    image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

                output = io.BytesIO()
                image.save(
                    output,
                    format="WEBP",
                    quality=82,
                    method=6,
                    lossless=False,
                )
                optimized = output.getvalue()
                optimized_mime = "image/webp"
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=415, detail="Invalid or unsupported image") from exc

    if not optimized:
        raise HTTPException(status_code=400, detail="Image optimization failed")
    if len(optimized) > MAX_STORED_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Optimized image is still too large")
    return optimized, optimized_mime


def _columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}


def _ensure_column(
    db: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    if column not in _columns(db, table):
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _ensure_club_column(db: sqlite3.Connection, table: str) -> None:
    """Add the first tenant ownership column without changing legacy record IDs."""
    _ensure_column(db, table, "club_id", "INTEGER NOT NULL DEFAULT 1")
    db.execute(
        f"UPDATE {table} SET club_id = 1 WHERE club_id IS NULL OR club_id = 0"
    )
    db.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{table}_club_id ON {table}(club_id)"
    )


def _apply_schema_migrations(db: sqlite3.Connection) -> None:
    """Record ordered schema migrations after the legacy bootstrap is reconciled."""
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    migrations: list[tuple[int, str]] = [
        (1, "baseline-v0.8.33"),
        (2, "app-config-foundation"),
        (3, "app-config-logo"),
        (4, "app-config-club-details"),
        (5, "app-config-modules"),
        (6, "user-roles-and-permission-overrides"),
        (7, "club-instance-binding"),
        (8, "club-settings-permission"),
        (9, "multi-tenant-clubs-foundation"),
        (10, "flapamamaku-club-data-migration"),
        (11, "user-club-memberships"),
        (12, "club-features"),
        (13, "session-active-club"),
        (14, "club-provisioning"),
        (15, "push-tenant-isolation"),
        (16, "club-billing-and-suspension"),
        (17, "club-billing-pdf-and-grace"),
    ]
    applied = {
        int(row["version"])
        for row in db.execute("SELECT version FROM schema_migrations").fetchall()
    }
    now = datetime.now(timezone.utc).isoformat()
    for version, name in migrations:
        if version in applied:
            continue
        db.execute(
            """
            INSERT INTO schema_migrations (version, name, applied_at)
            VALUES (?, ?, ?)
            """,
            (version, name, now),
        )


def _schema_version() -> int:
    if not DB_PATH.exists():
        return 0
    try:
        with connect() as db:
            row = db.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations"
            ).fetchone()
            return int(row["version"] if row is not None else 0)
    except sqlite3.Error:
        return 0


def _backup_files() -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    patterns = [f"{INSTANCE_ID}-*.db"]
    # Keep existing FLAPAMAMAKU backups visible after upgrading from schema <= 6.
    if INSTANCE_ID == "flapamamaku":
        patterns.append("flapamamaku-*.db")
    files: dict[Path, None] = {}
    for pattern in patterns:
        for path in BACKUP_DIR.glob(pattern):
            if path.is_file():
                files[path] = None
    return sorted(
        files,
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def _backup_info(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "name": path.name,
        "instance_id": INSTANCE_ID,
        "size_bytes": stat.st_size,
        "created_at": datetime.fromtimestamp(
            stat.st_mtime,
            tz=timezone.utc,
        ).isoformat(),
    }


def _prune_backups() -> None:
    for path in _backup_files()[BACKUP_RETENTION:]:
        try:
            path.unlink()
        except OSError:
            logger.exception("Could not remove old backup %s", path)


def _create_database_backup(reason: str = "automatic") -> Path:
    if not DB_PATH.exists():
        raise RuntimeError("Database does not exist")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    safe_reason = "".join(
        char for char in reason.lower().strip()
        if char.isalnum() or char in {"-", "_"}
    ) or "backup"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = BACKUP_DIR / f"{INSTANCE_ID}-{timestamp}-{safe_reason}.db"

    with sqlite3.connect(DB_PATH) as source, sqlite3.connect(target) as destination:
        source.backup(destination)

    with sqlite3.connect(target) as check:
        result = check.execute("PRAGMA integrity_check").fetchone()
        if result is None or str(result[0]).lower() != "ok":
            try:
                target.unlink()
            except OSError:
                pass
            raise RuntimeError("Backup integrity check failed")

    _prune_backups()
    logger.info("Database backup created: %s", target)
    return target


def _ensure_automatic_backup() -> None:
    files = _backup_files()
    if files:
        age = datetime.now(timezone.utc).timestamp() - files[0].stat().st_mtime
        if age < BACKUP_INTERVAL_SECONDS:
            return
    _create_database_backup("automatic")


def _validate_restore_database(path: Path) -> int:
    try:
        with sqlite3.connect(path) as db:
            integrity = db.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or str(integrity[0]).lower() != "ok":
                raise RuntimeError("Backup integrity check failed")

            tables = {
                str(row[0])
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            required = {
                "users",
                "members",
                "sessions",
                "schema_migrations",
                "app_config",
            }
            if not required.issubset(tables):
                raise RuntimeError("Backup does not contain a valid club database")

            row = db.execute(
                "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
            ).fetchone()
            schema_version = int(row[0] if row is not None else 0)
            if schema_version > CURRENT_SCHEMA_VERSION:
                raise RuntimeError(
                    f"Backup schema {schema_version} is newer than supported schema "
                    f"{CURRENT_SCHEMA_VERSION}"
                )

            app_columns = {
                str(row[1])
                for row in db.execute("PRAGMA table_info(app_config)").fetchall()
            }
            if "instance_id" in app_columns:
                instance_row = db.execute(
                    "SELECT instance_id FROM app_config WHERE id = 1"
                ).fetchone()
                source_instance = (
                    str(instance_row[0]).strip().lower()
                    if instance_row is not None and instance_row[0]
                    else ""
                )
                if not source_instance:
                    raise RuntimeError("Backup has no club instance identity")
                if source_instance != INSTANCE_ID:
                    raise RuntimeError(
                        "Backup belongs to another club instance "
                        f"({source_instance}); expected {INSTANCE_ID}"
                    )
            elif INSTANCE_ID != "flapamamaku":
                raise RuntimeError(
                    "Legacy backup has no club instance identity and cannot be "
                    "restored into this club"
                )
            return schema_version
    except sqlite3.Error as exc:
        raise RuntimeError("Backup is not a readable SQLite database") from exc


def _restore_database_backup(source: Path) -> dict[str, Any]:
    schema_version = _validate_restore_database(source)
    safety_backup = _create_database_backup("before-restore")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    replacement = DB_PATH.with_name(f".{DB_PATH.name}.restore-{secrets.token_hex(6)}")
    try:
        with sqlite3.connect(source) as src, sqlite3.connect(replacement) as dst:
            src.backup(dst)
        _validate_restore_database(replacement)
        os.replace(replacement, DB_PATH)
        init_db()
        with connect() as db:
            db.execute("DELETE FROM sessions")
            db.commit()
    except Exception:
        try:
            replacement.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    logger.warning(
        "Database restored from %s; safety backup: %s",
        source.name,
        safety_backup.name,
    )
    return {
        "restored": True,
        "source_name": source.name,
        "source_schema_version": schema_version,
        "current_schema_version": _schema_version(),
        "safety_backup": _backup_info(safety_backup),
        "sessions_cleared": True,
    }


def init_db() -> None:
    with connect() as db:
        for ddl, _ in TABLES.values():
            db.execute(ddl)

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS clubs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE COLLATE NOCASE,
                name TEXT NOT NULL,
                short_name TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                logo BLOB,
                logo_mime TEXT NOT NULL DEFAULT '',
                primary_color TEXT NOT NULL DEFAULT '#8A101B',
                secondary_color TEXT NOT NULL DEFAULT '#FFFFFF',
                description TEXT NOT NULL DEFAULT '',
                website TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                address TEXT NOT NULL DEFAULT '',
                city TEXT NOT NULL DEFAULT '',
                country TEXT NOT NULL DEFAULT '',
                app_title TEXT NOT NULL DEFAULT '',
                welcome_text TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        club_now = datetime.now(timezone.utc).isoformat()
        db.execute(
            """
            INSERT OR IGNORE INTO clubs (
                slug, name, short_name, active,
                primary_color, secondary_color,
                created_at, updated_at
            ) VALUES (
                'flapamamaku', 'FLAPAMAMAKU', 'FLAPAMAMAKU', 1,
                '#8A101B', '#FFFFFF',
                ?, ?
            )
            """,
            (club_now, club_now),
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS club_features (
                club_id INTEGER NOT NULL,
                feature_key TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
                label TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (club_id, feature_key),
                FOREIGN KEY(club_id) REFERENCES clubs(id)
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_club_features_club_id ON club_features(club_id)"
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS app_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                app_name TEXT NOT NULL DEFAULT 'FLAPAMAMAKU',
                app_subtitle TEXT NOT NULL DEFAULT 'Fasnachtsgruppe Luzern',
                primary_color TEXT NOT NULL DEFAULT '#8A101B',
                updated_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            INSERT OR IGNORE INTO app_config (
                id, app_name, app_subtitle, primary_color, updated_at
            ) VALUES (1, 'FLAPAMAMAKU', 'Fasnachtsgruppe Luzern', '#8A101B', ?)
            """,
            (datetime.now(timezone.utc).isoformat(),),
        )
        _ensure_column(db, "app_config", "instance_id", "TEXT NOT NULL DEFAULT ''")
        instance_row = db.execute(
            "SELECT instance_id FROM app_config WHERE id = 1"
        ).fetchone()
        stored_instance = (
            str(instance_row["instance_id"]).strip().lower()
            if instance_row is not None and instance_row["instance_id"]
            else ""
        )
        if stored_instance and stored_instance != INSTANCE_ID:
            raise RuntimeError(
                "Database belongs to another club instance "
                f"({stored_instance}); configured instance is {INSTANCE_ID}"
            )
        if not stored_instance:
            db.execute(
                "UPDATE app_config SET instance_id = ? WHERE id = 1",
                (INSTANCE_ID,),
            )

        # Compatibility bridge for existing single-club deployments:
        # before shared multi-tenancy, club 1 represented the configured
        # FLAPAMAMAKU_INSTANCE_ID even when its slug had not yet existed in
        # the new clubs registry. Keep the same row/id and bind it to that
        # instance instead of creating or moving club-owned data.
        if INSTANCE_ID != "flapamamaku":
            mapped_club = db.execute(
                "SELECT id FROM clubs WHERE slug = ?",
                (INSTANCE_ID,),
            ).fetchone()
            club_count = int(
                db.execute("SELECT COUNT(*) FROM clubs").fetchone()[0]
            )
            reference_club = db.execute(
                "SELECT id FROM clubs WHERE id = 1 AND slug = 'flapamamaku'"
            ).fetchone()
            if mapped_club is None and club_count == 1 and reference_club is not None:
                db.execute(
                    """
                    UPDATE clubs
                    SET slug = ?, updated_at = ?
                    WHERE id = 1
                    """,
                    (
                        INSTANCE_ID,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

        _ensure_column(db, "clubs", "subtitle", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "clubs", "billing_status", "TEXT NOT NULL DEFAULT 'active'")
        _ensure_column(db, "clubs", "billing_email", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "clubs", "billing_amount_rappen", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(db, "clubs", "billing_interval_months", "INTEGER NOT NULL DEFAULT 12")
        _ensure_column(db, "clubs", "billing_due_days", "INTEGER NOT NULL DEFAULT 30")
        _ensure_column(db, "clubs", "billing_grace_days", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(db, "clubs", "billing_next_invoice_date", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "clubs", "billing_auto_suspend", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(db, "clubs", "billing_suspension_reason", "TEXT NOT NULL DEFAULT ''")

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS club_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                club_id INTEGER NOT NULL,
                invoice_number TEXT NOT NULL UNIQUE,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                issue_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                amount_rappen INTEGER NOT NULL CHECK (amount_rappen >= 0),
                currency TEXT NOT NULL DEFAULT 'CHF',
                status TEXT NOT NULL DEFAULT 'open',
                paid_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(club_id, period_start),
                FOREIGN KEY(club_id) REFERENCES clubs(id)
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_club_invoices_club_id "
            "ON club_invoices(club_id)"
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_club_invoices_due_status "
            "ON club_invoices(due_date, status)"
        )
        legacy_subtitle = db.execute(
            "SELECT app_subtitle FROM app_config WHERE id = 1"
        ).fetchone()
        if legacy_subtitle is not None:
            db.execute(
                """
                UPDATE clubs
                SET subtitle = ?
                WHERE id = 1 AND subtitle = ''
                """,
                (str(legacy_subtitle["app_subtitle"] or ""),),
            )

        _ensure_column(db, "app_config", "logo_data", "BLOB")
        _ensure_column(db, "app_config", "logo_mime", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "app_config", "club_description", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "app_config", "website_url", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "app_config", "contact_email", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "app_config", "contact_phone", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "app_config", "club_address", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "app_config", "show_sujet", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(db, "app_config", "label_sujet", "TEXT NOT NULL DEFAULT 'Sujet nächstes Jahr'")
        _ensure_column(db, "app_config", "show_archive", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(db, "app_config", "label_archive", "TEXT NOT NULL DEFAULT 'Vergangene Sujet'")
        _ensure_column(db, "app_config", "show_photos", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(db, "app_config", "label_photos", "TEXT NOT NULL DEFAULT 'Fotoalben'")
        _ensure_column(db, "app_config", "show_documents", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(db, "app_config", "label_documents", "TEXT NOT NULL DEFAULT 'Dokumente'")
        _ensure_column(db, "app_config", "show_polls", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(db, "app_config", "label_polls", "TEXT NOT NULL DEFAULT 'Umfragen'")
        _ensure_column(db, "app_config", "show_links", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(db, "app_config", "label_links", "TEXT NOT NULL DEFAULT 'Links'")

        feature_now = datetime.now(timezone.utc).isoformat()
        legacy_features = db.execute(
            """
            SELECT
                show_sujet, label_sujet,
                show_archive, label_archive,
                show_photos, label_photos,
                show_documents, label_documents,
                show_polls, label_polls,
                show_links, label_links
            FROM app_config
            WHERE id = 1
            """
        ).fetchone()
        for club in db.execute("SELECT id FROM clubs").fetchall():
            club_id = int(club["id"])
            for feature_key, (default_label, default_enabled) in CLUB_FEATURE_DEFAULTS.items():
                enabled = default_enabled
                label = default_label
                if club_id == 1 and legacy_features is not None:
                    legacy_map = {
                        "sujet_next": ("show_sujet", "label_sujet"),
                        "sujet_archive": ("show_archive", "label_archive"),
                        "photos": ("show_photos", "label_photos"),
                        "documents": ("show_documents", "label_documents"),
                        "polls": ("show_polls", "label_polls"),
                        "links": ("show_links", "label_links"),
                    }
                    if feature_key in legacy_map:
                        show_key, label_key = legacy_map[feature_key]
                        enabled = bool(legacy_features[show_key])
                        label = str(legacy_features[label_key] or default_label)
                db.execute(
                    """
                    INSERT OR IGNORE INTO club_features (
                        club_id, feature_key, enabled, label, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        club_id,
                        feature_key,
                        int(enabled),
                        label,
                        feature_now,
                        feature_now,
                    ),
                )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS member_filters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL UNIQUE COLLATE NOCASE,
                active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS member_filter_links (
                member_id INTEGER NOT NULL,
                filter_id INTEGER NOT NULL,
                PRIMARY KEY(member_id, filter_id),
                FOREIGN KEY(member_id) REFERENCES members(id),
                FOREIGN KEY(filter_id) REFERENCES member_filters(id)
            )
            """
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS content_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section TEXT NOT NULL,
                title TEXT NOT NULL,
                text TEXT NOT NULL DEFAULT '',
                link_url TEXT NOT NULL DEFAULT '',
                image_data BLOB,
                image_mime TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )

        _ensure_column(db, "content_items", "document_data", "BLOB")
        _ensure_column(db, "content_items", "document_mime", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "content_items", "document_name", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "content_items", "poll_options", "TEXT NOT NULL DEFAULT '[]'")
        _ensure_column(
            db,
            "content_items",
            "poll_allow_suggestions",
            "INTEGER NOT NULL DEFAULT 0",
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS poll_votes (
                poll_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                option_index INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(poll_id, user_id),
                FOREIGN KEY(poll_id) REFERENCES content_items(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS poll_suggestions (
                poll_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                option_index INTEGER NOT NULL,
                suggestion_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(poll_id, user_id),
                FOREIGN KEY(poll_id) REFERENCES content_items(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS content_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER NOT NULL,
                image_data BLOB NOT NULL,
                image_mime TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(content_id) REFERENCES content_items(id)
            )
            """
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS gallery_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                image_data BLOB NOT NULL,
                image_mime TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS push_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                platform TEXT NOT NULL DEFAULT 'android',
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS push_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                route TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                sent_at TEXT,
                last_error TEXT NOT NULL DEFAULT ''
            )
            """
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS push_deliveries (
                notification_id INTEGER NOT NULL,
                token_id INTEGER NOT NULL,
                sent_at TEXT,
                last_error TEXT NOT NULL DEFAULT '',
                PRIMARY KEY(notification_id, token_id),
                FOREIGN KEY(notification_id) REFERENCES push_notifications(id),
                FOREIGN KEY(token_id) REFERENCES push_tokens(id)
            )
            """
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                can_news INTEGER NOT NULL DEFAULT 0,
                can_events INTEGER NOT NULL DEFAULT 0,
                can_members INTEGER NOT NULL DEFAULT 0,
                can_documents INTEGER NOT NULL DEFAULT 0,
                can_photos INTEGER NOT NULL DEFAULT 0,
                can_polls INTEGER NOT NULL DEFAULT 0,
                can_links INTEGER NOT NULL DEFAULT 0,
                can_contact INTEGER NOT NULL DEFAULT 0,
                can_about INTEGER NOT NULL DEFAULT 0,
                can_admin_page INTEGER NOT NULL DEFAULT 0,
                can_manage_users INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(member_id) REFERENCES members(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_clubs (
                user_id INTEGER NOT NULL,
                club_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'member'
                    CHECK (role IN ('super_admin', 'club_admin', 'member')),
                active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, club_id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(club_id) REFERENCES clubs(id)
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_clubs_club_id ON user_clubs(club_id)"
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS event_registrations (
                event_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (event_id, user_id),
                FOREIGN KEY(event_id) REFERENCES events(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        _ensure_column(db, "sessions", "active_club_id", "INTEGER")
        db.execute(
            """
            UPDATE sessions
            SET active_club_id = 1
            WHERE active_club_id IS NULL OR active_club_id = 0
            """
        )

        _ensure_column(db, "news", "image_data", "BLOB")
        _ensure_column(db, "news", "image_mime", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "news", "sort_order", "INTEGER NOT NULL DEFAULT 0")
        news_order_rows = db.execute(
            "SELECT id, sort_order FROM news ORDER BY created_at DESC, id DESC"
        ).fetchall()
        if news_order_rows and all(int(row["sort_order"] or 0) == 0 for row in news_order_rows):
            for position, row in enumerate(news_order_rows, start=1):
                db.execute(
                    "UPDATE news SET sort_order = ? WHERE id = ?",
                    (position, row["id"]),
                )
        _ensure_column(db, "events", "event_date", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "phone_mobile", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "phone_private", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "phone_work", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "occupation", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "employer", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "employer_url", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "birth_date", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "status", "TEXT NOT NULL DEFAULT 'Aktiv'")
        _ensure_column(db, "members", "member_group", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "engagement", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "users", "can_manage_settings", "INTEGER NOT NULL DEFAULT 0")
        db.execute(
            """
            UPDATE users
            SET can_manage_settings = 1
            WHERE can_manage_users = 1 AND can_manage_settings = 0
            """
        )

        _ensure_column(db, "members", "sort_order", "INTEGER NOT NULL DEFAULT 0")
        db.execute(
            """
            UPDATE members
            SET sort_order = id
            WHERE sort_order = 0
            """
        )
        _ensure_column(db, "members", "photo_data", "BLOB")
        _ensure_column(db, "members", "photo_mime", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "sort_order", "INTEGER NOT NULL DEFAULT 0")

        member_order_rows = db.execute(
            "SELECT id, sort_order FROM members ORDER BY name COLLATE NOCASE ASC, id ASC"
        ).fetchall()
        if member_order_rows and all(int(row["sort_order"] or 0) == 0 for row in member_order_rows):
            for position, row in enumerate(member_order_rows, start=1):
                db.execute(
                    "UPDATE members SET sort_order = ? WHERE id = ?",
                    (position, row["id"]),
                )
        _ensure_column(
            db,
            "users",
            "can_gallery_upload",
            "INTEGER NOT NULL DEFAULT 0",
        )

        _ensure_column(
            db,
            "users",
            "role_key",
            "TEXT NOT NULL DEFAULT 'member'",
        )
        _ensure_column(
            db,
            "users",
            "permission_overrides",
            "TEXT NOT NULL DEFAULT ''",
        )

        legacy_role_rows = db.execute(
            "SELECT * FROM users WHERE permission_overrides = ''"
        ).fetchall()
        for legacy_user in legacy_role_rows:
            legacy_permissions = {
                key: bool(legacy_user[key])
                for key in PERMISSION_FIELDS
            }
            if all(legacy_permissions.values()):
                role_key = "admin"
                overrides: dict[str, bool] = {}
            else:
                role_key = "member"
                overrides = legacy_permissions
            db.execute(
                """
                UPDATE users
                SET role_key = ?, permission_overrides = ?
                WHERE id = ?
                """,
                (
                    role_key,
                    json.dumps(overrides, ensure_ascii=False, sort_keys=True),
                    legacy_user["id"],
                ),
            )

        membership_now = datetime.now(timezone.utc).isoformat()
        db.execute(
            """
            INSERT OR IGNORE INTO user_clubs (
                user_id, club_id, role, active, created_at, updated_at
            )
            SELECT
                u.id,
                1,
                CASE
                    WHEN u.role_key = 'admin' OR u.can_manage_users = 1
                    THEN 'club_admin'
                    ELSE 'member'
                END,
                u.active,
                ?,
                ?
            FROM users u
            """,
            (membership_now, membership_now),
        )

        super_admin_exists = db.execute(
            """
            SELECT 1 FROM user_clubs
            WHERE role = 'super_admin' AND active = 1
            LIMIT 1
            """
        ).fetchone()
        if super_admin_exists is None:
            platform_admin = db.execute(
                """
                SELECT uc.user_id
                FROM user_clubs uc
                JOIN users u ON u.id = uc.user_id
                WHERE uc.club_id = 1
                  AND uc.active = 1
                  AND u.active = 1
                  AND u.can_manage_users = 1
                ORDER BY u.id ASC
                LIMIT 1
                """
            ).fetchone()
            if platform_admin is not None:
                db.execute(
                    """
                    UPDATE user_clubs
                    SET role = 'super_admin', updated_at = ?
                    WHERE user_id = ? AND club_id = 1
                    """,
                    (membership_now, platform_admin["user_id"]),
                )

        _ensure_column(
            db,
            "content_items",
            "sort_order",
            "INTEGER NOT NULL DEFAULT 0",
        )
        db.execute(
            """
            UPDATE content_items
            SET sort_order = id
            WHERE sort_order = 0
            """
        )

        _ensure_column(
            db,
            "content_images",
            "sort_order",
            "INTEGER NOT NULL DEFAULT 0",
        )
        db.execute(
            """
            UPDATE content_images
            SET sort_order = id
            WHERE sort_order = 0
            """
        )

        legacy_rows = db.execute(
            """
            SELECT id, image_data, image_mime, created_at
            FROM content_items
            WHERE image_data IS NOT NULL
            """
        ).fetchall()
        for legacy in legacy_rows:
            max_order = db.execute(
                """
                SELECT COALESCE(MAX(sort_order), 0)
                FROM content_images
                WHERE content_id = ?
                """,
                (legacy["id"],),
            ).fetchone()[0]
            db.execute(
                """
                INSERT INTO content_images (
                    content_id, image_data, image_mime, sort_order, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    legacy["id"],
                    legacy["image_data"],
                    legacy["image_mime"],
                    max_order + 1,
                    legacy["created_at"],
                ),
            )
            db.execute(
                """
                UPDATE content_items
                SET image_data = NULL, image_mime = ''
                WHERE id = ?
                """,
                (legacy["id"],),
            )

        if db.execute("SELECT COUNT(*) FROM member_filters").fetchone()[0] == 0:
            now = datetime.now(timezone.utc).isoformat()
            for position, label in enumerate(["Aktiv", "Ehrenmitglied", "Vorstand", "Wagenbau", "Verstorben"], start=1):
                db.execute(
                    """
                    INSERT INTO member_filters (label, active, sort_order, created_at)
                    VALUES (?, 1, ?, ?)
                    """,
                    (label, position, now),
                )

        member_columns = _columns(db, "members")
        if "phone" in member_columns:
            db.execute(
                """
                UPDATE members
                SET phone_mobile = phone
                WHERE phone_mobile = '' AND phone <> ''
                """
            )

        # Package 2: assign all existing FLAPAMAMAKU-owned records to club 1.
        # API filtering and multi-club user membership are intentionally deferred
        # to the following controlled packages.
        direct_club_tables = (
            "news",
            "events",
            "members",
            "app_config",
            "member_filters",
            "content_items",
            "content_images",
            "gallery_snapshots",
            "push_tokens",
            "push_notifications",
        )
        relation_club_tables = (
            "member_filter_links",
            "poll_votes",
            "poll_suggestions",
            "push_deliveries",
            "event_registrations",
        )
        for table in (*direct_club_tables, *relation_club_tables):
            _ensure_club_column(db, table)

        # Keep current FLAPAMAMAKU appearance/configuration as the source of truth
        # while introducing the central clubs row. Nothing in the app reads these
        # copied fields yet, so existing runtime behaviour remains unchanged.
        config = db.execute("SELECT * FROM app_config WHERE id = 1").fetchone()
        if config is not None:
            db.execute(
                """
                UPDATE clubs
                SET
                    name = ?,
                    short_name = ?,
                    logo = ?,
                    logo_mime = ?,
                    primary_color = ?,
                    description = ?,
                    website = ?,
                    email = ?,
                    phone = ?,
                    address = ?,
                    app_title = ?,
                    updated_at = ?
                WHERE id = 1 AND slug = 'flapamamaku'
                """,
                (
                    str(config["app_name"] or "FLAPAMAMAKU"),
                    str(config["app_name"] or "FLAPAMAMAKU"),
                    config["logo_data"],
                    str(config["logo_mime"] or ""),
                    str(config["primary_color"] or "#8A101B"),
                    str(config["club_description"] or ""),
                    str(config["website_url"] or ""),
                    str(config["contact_email"] or ""),
                    str(config["contact_phone"] or ""),
                    str(config["club_address"] or ""),
                    str(config["app_name"] or "FLAPAMAMAKU"),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

        _apply_schema_migrations(db)
        db.commit()


async def _snapshot_cleanup_loop() -> None:
    while True:
        await asyncio.sleep(3600)
        with connect() as db:
            db.execute(
                "DELETE FROM gallery_snapshots WHERE expires_at <= ?",
                (datetime.now(timezone.utc).isoformat(),),
            )
            db.commit()


async def _backup_loop() -> None:
    while True:
        await asyncio.sleep(3600)
        try:
            await asyncio.to_thread(_ensure_automatic_backup)
        except Exception:
            logger.exception("Automatic database backup failed")


def _firebase_access() -> tuple[str, str] | None:
    if not FIREBASE_SERVICE_ACCOUNT_JSON:
        return None
    try:
        info = json.loads(FIREBASE_SERVICE_ACCOUNT_JSON)
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/firebase.messaging"],
        )
        credentials.refresh(GoogleAuthRequest())
        project_id = str(info.get("project_id") or "").strip()
        if not credentials.token or not project_id:
            logger.error("Firebase credentials incomplete: token/project_id missing")
            return None
        return credentials.token, project_id
    except Exception as exc:
        logger.error("Firebase authentication failed: %s", exc)
        return None


def _firebase_diagnostic() -> dict[str, Any]:
    configured = bool(FIREBASE_SERVICE_ACCOUNT_JSON)
    if not configured:
        return {
            "delivery_configured": False,
            "firebase_auth_ready": False,
            "firebase_project_id": "",
            "firebase_error": "Firebase service account is not configured",
        }
    try:
        info = json.loads(FIREBASE_SERVICE_ACCOUNT_JSON)
        project_id = str(info.get("project_id") or "").strip()
        client_email = str(info.get("client_email") or "").strip()
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/firebase.messaging"],
        )
        credentials.refresh(GoogleAuthRequest())
        return {
            "delivery_configured": True,
            "firebase_auth_ready": bool(credentials.token and project_id),
            "firebase_project_id": project_id,
            "firebase_client_email": client_email,
            "firebase_error": "",
        }
    except Exception as exc:
        return {
            "delivery_configured": True,
            "firebase_auth_ready": False,
            "firebase_project_id": "",
            "firebase_client_email": "",
            "firebase_error": str(exc)[:500],
        }


def _send_fcm_message(
    *,
    access_token: str,
    project_id: str,
    device_token: str,
    title: str,
    body: str,
    kind: str,
    route: str,
) -> tuple[bool, bool, str]:
    payload = {
        "message": {
            "token": device_token,
            "notification": {
                "title": title,
                "body": body,
                **({"image": PUSH_ICON_URL} if PUSH_ICON_URL else {}),
            },
            "data": {
                "kind": kind,
                "route": route,
            },
            "android": {
                "priority": "high",
                "notification": {
                    "icon": "ic_stat_flapamamaku",
                    **({"image": PUSH_ICON_URL} if PUSH_ICON_URL else {}),
                },
            },
            "apns": {
                "headers": {
                    "apns-priority": "10",
                },
            },
        },
    }
    request = urllib.request.Request(
        f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response.read()
        return True, False, ""
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        invalid = exc.code in {400, 404} and (
            "UNREGISTERED" in detail
            or "registration-token-not-registered" in detail
        )
        return False, invalid, f"HTTP {exc.code}: {detail}"
    except Exception as exc:
        return False, False, str(exc)[:1000]


def _deliver_pending_push() -> None:
    firebase = _firebase_access()
    if firebase is None:
        return
    access_token, project_id = firebase
    now = datetime.now(timezone.utc).isoformat()

    with connect() as db:
        notifications = db.execute(
            """
            SELECT *
            FROM push_notifications
            WHERE sent_at IS NULL
            ORDER BY id ASC
            LIMIT 10
            """
        ).fetchall()

        for notification in notifications:
            tokens = db.execute(
                """
                SELECT *
                FROM push_tokens
                WHERE enabled = 1 AND club_id = ?
                ORDER BY id ASC
                """,
                (notification["club_id"],),
            ).fetchall()
            if not tokens:
                continue

            had_transient_error = False
            for token in tokens:
                delivered = db.execute(
                    """
                    SELECT sent_at
                    FROM push_deliveries
                    WHERE notification_id = ? AND token_id = ? AND club_id = ?
                    """,
                    (notification["id"], token["id"], notification["club_id"]),
                ).fetchone()
                if delivered is not None and delivered["sent_at"]:
                    continue

                ok, invalid, error = _send_fcm_message(
                    access_token=access_token,
                    project_id=project_id,
                    device_token=token["token"],
                    title=notification["title"],
                    body=notification["body"],
                    kind=notification["kind"],
                    route=notification["route"],
                )

                if invalid:
                    db.execute("DELETE FROM push_tokens WHERE id = ?", (token["id"],))
                    db.execute(
                        """
                        DELETE FROM push_deliveries
                        WHERE notification_id = ? AND token_id = ? AND club_id = ?
                        """,
                        (notification["id"], token["id"], notification["club_id"]),
                    )
                    continue

                db.execute(
                    """
                    INSERT INTO push_deliveries (
                        notification_id, token_id, sent_at, last_error, club_id
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(notification_id, token_id) DO UPDATE SET
                        sent_at = excluded.sent_at,
                        last_error = excluded.last_error,
                        club_id = excluded.club_id
                    """,
                    (
                        notification["id"],
                        token["id"],
                        now if ok else None,
                        error,
                        notification["club_id"],
                    ),
                )
                if not ok:
                    had_transient_error = True
                    logger.error(
                        "FCM delivery failed for notification %s token %s: %s",
                        notification["id"],
                        token["id"],
                        error,
                    )

            remaining = db.execute(
                """
                SELECT COUNT(*)
                FROM push_tokens pt
                WHERE pt.enabled = 1
                  AND pt.club_id = ?
                  AND NOT EXISTS (
                      SELECT 1
                      FROM push_deliveries pd
                      WHERE pd.notification_id = ?
                        AND pd.token_id = pt.id
                        AND pd.club_id = ?
                        AND pd.sent_at IS NOT NULL
                  )
                """,
                (
                    notification["club_id"],
                    notification["id"],
                    notification["club_id"],
                ),
            ).fetchone()[0]

            if remaining == 0 and not had_transient_error:
                db.execute(
                    """
                    UPDATE push_notifications
                    SET sent_at = ?, last_error = ''
                    WHERE id = ?
                    """,
                    (now, notification["id"]),
                )
            elif had_transient_error:
                db.execute(
                    """
                    UPDATE push_notifications
                    SET last_error = 'Mindestens eine Zustellung wird erneut versucht'
                    WHERE id = ?
                    """,
                    (notification["id"],),
                )
        db.commit()




def _require_super_admin(user: dict[str, Any]) -> None:
    if not bool(user.get("is_super_admin")):
        raise HTTPException(
            status_code=403,
            detail="Nur Super-Admins dürfen die Vereinsabrechnung verwalten",
        )


def _parse_billing_date(value: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="Datum muss im Format JJJJ-MM-TT angegeben werden",
        ) from exc
    return parsed.replace(tzinfo=timezone.utc)


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _invoice_row(item: sqlite3.Row) -> dict[str, Any]:
    result = dict(item)
    result["amount_chf"] = round(int(result["amount_rappen"]) / 100, 2)
    return result


def _display_invoice_date(value: str) -> str:
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        return value


def _invoice_pdf_bytes(
    invoice: dict[str, Any],
    club: dict[str, Any],
) -> bytes:
    canvas = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(canvas)
    title_font = ImageFont.load_default(size=48)
    heading_font = ImageFont.load_default(size=30)
    body_font = ImageFont.load_default(size=24)
    small_font = ImageFont.load_default(size=20)

    margin_x = 90
    y = 80
    draw.text((margin_x, y), "Vereinsrechnung", fill="black", font=title_font)
    y += 88

    issuer_lines = [BILLING_ISSUER_NAME]
    if BILLING_ISSUER_ADDRESS:
        issuer_lines.extend(
            line.strip()
            for line in BILLING_ISSUER_ADDRESS.splitlines()
            if line.strip()
        )
    draw.multiline_text(
        (margin_x, y),
        "\n".join(issuer_lines),
        fill="black",
        font=body_font,
        spacing=8,
    )

    recipient_lines = [str(club.get("name") or club.get("slug") or "Verein")]
    address = str(club.get("address") or "").strip()
    city = str(club.get("city") or "").strip()
    country = str(club.get("country") or "").strip()
    billing_email = str(club.get("billing_email") or "").strip()
    for value in (address, city, country, billing_email):
        if value:
            recipient_lines.extend(
                line.strip()
                for line in value.splitlines()
                if line.strip()
            )
    draw.multiline_text(
        (700, y),
        "\n".join(recipient_lines),
        fill="black",
        font=body_font,
        spacing=8,
    )

    y = 420
    draw.text(
        (margin_x, y),
        f"Rechnung Nr. {invoice['invoice_number']}",
        fill="black",
        font=heading_font,
    )
    y += 56
    details = [
        ("Rechnungsdatum", _display_invoice_date(str(invoice["issue_date"]))),
        ("Zahlungsziel", _display_invoice_date(str(invoice["due_date"]))),
        (
            "Leistungsperiode",
            f"{_display_invoice_date(str(invoice['period_start']))} bis "
            f"{_display_invoice_date(str(invoice['period_end']))}",
        ),
    ]
    for label, value in details:
        draw.text((margin_x, y), f"{label}: {value}", fill="black", font=body_font)
        y += 42

    y += 48
    draw.text((margin_x, y), "Leistung", fill="black", font=heading_font)
    draw.text((900, y), "Betrag", fill="black", font=heading_font)
    y += 54
    draw.line((margin_x, y, 1150, y), fill="black", width=2)
    y += 28

    description = (
        "Nutzung der Vereinsplattform für die Leistungsperiode "
        f"{_display_invoice_date(str(invoice['period_start']))} bis "
        f"{_display_invoice_date(str(invoice['period_end']))}"
    )
    draw.text((margin_x, y), description, fill="black", font=body_font)
    amount = f"CHF {int(invoice['amount_rappen']) / 100:.2f}"
    draw.text((900, y), amount, fill="black", font=body_font)
    y += 84
    draw.line((margin_x, y, 1150, y), fill="black", width=2)
    y += 28
    draw.text((760, y), "Gesamtbetrag", fill="black", font=heading_font)
    draw.text((900, y + 48), amount, fill="black", font=heading_font)

    y += 180
    draw.text((margin_x, y), "Zahlungsinformationen", fill="black", font=heading_font)
    y += 48
    payment_text = BILLING_PAYMENT_INFO or (
        "Bitte den Rechnungsbetrag gemäss vereinbarter Zahlungsart begleichen "
        "und die Rechnungsnummer als Referenz angeben."
    )
    payment_lines = []
    for raw_line in payment_text.splitlines() or [payment_text]:
        words = raw_line.split()
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) > 78 and current:
                payment_lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            payment_lines.append(current)
    draw.multiline_text(
        (margin_x, y),
        "\n".join(payment_lines),
        fill="black",
        font=body_font,
        spacing=8,
    )

    footer = (
        f"Rechnung {invoice['invoice_number']} · "
        f"Status: {'bezahlt' if invoice.get('status') == 'paid' else 'offen'}"
    )
    draw.text((margin_x, 1640), footer, fill="black", font=small_font)

    buffer = io.BytesIO()
    canvas.save(buffer, format="PDF", resolution=150.0)
    return buffer.getvalue()


def _run_billing_cycle() -> dict[str, int]:
    today_dt = datetime.now(timezone.utc)
    today = today_dt.date().isoformat()
    created = 0
    suspended = 0

    with connect() as db:
        clubs = db.execute(
            """
            SELECT
                id, billing_amount_rappen, billing_interval_months,
                billing_due_days, billing_grace_days, billing_next_invoice_date,
                billing_auto_suspend
            FROM clubs
            WHERE active = 1
              AND billing_amount_rappen > 0
              AND billing_next_invoice_date != ''
            """
        ).fetchall()

        for club in clubs:
            club_id = int(club["id"])
            next_date = _parse_billing_date(
                str(club["billing_next_invoice_date"])
            )
            interval = max(1, int(club["billing_interval_months"] or 12))
            generated_for_club = 0
            while next_date.date().isoformat() <= today and generated_for_club < 120:
                period_start = next_date.date().isoformat()
                next_period = _add_months(next_date, interval)
                period_end = (next_period - timedelta(days=1)).date().isoformat()
                issue_date = today
                due_date = (
                    today_dt + timedelta(days=max(1, int(club["billing_due_days"] or 30)))
                ).date().isoformat()
                invoice_number = (
                    f"{today_dt.year:04d}-{club_id:04d}-"
                    f"{period_start.replace('-', '')}"
                )
                cursor = db.execute(
                    """
                    INSERT OR IGNORE INTO club_invoices (
                        club_id, invoice_number, period_start, period_end,
                        issue_date, due_date, amount_rappen, currency,
                        status, paid_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'CHF', 'open', '', ?, ?)
                    """,
                    (
                        club_id,
                        invoice_number,
                        period_start,
                        period_end,
                        issue_date,
                        due_date,
                        int(club["billing_amount_rappen"]),
                        today_dt.isoformat(),
                        today_dt.isoformat(),
                    ),
                )
                if cursor.rowcount:
                    created += 1
                next_date = next_period
                generated_for_club += 1

            db.execute(
                """
                UPDATE clubs
                SET billing_next_invoice_date = ?, updated_at = ?
                WHERE id = ?
                """,
                (next_date.date().isoformat(), today_dt.isoformat(), club_id),
            )

        overdue = db.execute(
            """
            SELECT DISTINCT c.id
            FROM clubs c
            JOIN club_invoices i ON i.club_id = c.id
            WHERE c.active = 1
              AND c.billing_auto_suspend = 1
              AND i.status = 'open'
              AND date(
                    i.due_date,
                    '+' || MAX(0, c.billing_grace_days) || ' days'
                  ) < ?
            """,
            (today,),
        ).fetchall()
        for row in overdue:
            cursor = db.execute(
                """
                UPDATE clubs
                SET
                    billing_status = 'suspended',
                    billing_suspension_reason = 'Offene Rechnung überfällig',
                    updated_at = ?
                WHERE id = ?
                  AND billing_status != 'suspended'
                """,
                (today_dt.isoformat(), int(row["id"])),
            )
            suspended += cursor.rowcount

        db.commit()

    return {"created_invoices": created, "suspended_clubs": suspended}


async def _billing_loop() -> None:
    while True:
        await asyncio.sleep(3600)
        try:
            await asyncio.to_thread(_run_billing_cycle)
        except Exception:
            logger.exception("Automatic club billing cycle failed")


async def _push_delivery_loop() -> None:
    while True:
        await asyncio.sleep(15)
        if FIREBASE_SERVICE_ACCOUNT_JSON:
            await asyncio.to_thread(_deliver_pending_push)


@app.on_event("startup")
async def startup() -> None:
    init_db()
    try:
        await asyncio.to_thread(_ensure_automatic_backup)
    except Exception:
        logger.exception("Initial automatic database backup failed")
    try:
        await asyncio.to_thread(_run_billing_cycle)
    except Exception:
        logger.exception("Initial club billing cycle failed")
    asyncio.create_task(_snapshot_cleanup_loop())
    asyncio.create_task(_backup_loop())
    asyncio.create_task(_push_delivery_loop())
    asyncio.create_task(_billing_loop())


def _hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
    return digest.hex(), salt.hex()


def _check_password(password: str, password_hash: str, salt_hex: str) -> bool:
    digest, _ = _hash_password(password, salt_hex)
    return hmac.compare_digest(digest, password_hash)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _login_rate_key(request: Request, username: str) -> str:
    host = request.client.host if request.client else "unknown"
    normalized = username.strip().lower()
    return hashlib.sha256(f"{host}|{normalized}".encode()).hexdigest()


def _check_login_rate_limit(key: str) -> None:
    now = time.monotonic()
    with _LOGIN_RATE_LOCK:
        locked_until = _LOGIN_LOCKED_UNTIL.get(key, 0.0)
        if locked_until > now:
            retry_after = max(1, int(locked_until - now) + 1)
            raise HTTPException(
                status_code=429,
                detail="Zu viele fehlgeschlagene Anmeldeversuche. Bitte später nochmals versuchen.",
                headers={"Retry-After": str(retry_after)},
            )
        if locked_until:
            _LOGIN_LOCKED_UNTIL.pop(key, None)

        attempts = [
            stamp
            for stamp in _LOGIN_ATTEMPTS.get(key, [])
            if now - stamp <= LOGIN_RATE_WINDOW_SECONDS
        ]
        if attempts:
            _LOGIN_ATTEMPTS[key] = attempts
        else:
            _LOGIN_ATTEMPTS.pop(key, None)


def _record_login_failure(key: str) -> None:
    now = time.monotonic()
    with _LOGIN_RATE_LOCK:
        attempts = [
            stamp
            for stamp in _LOGIN_ATTEMPTS.get(key, [])
            if now - stamp <= LOGIN_RATE_WINDOW_SECONDS
        ]
        attempts.append(now)
        if len(attempts) >= LOGIN_RATE_MAX_ATTEMPTS:
            _LOGIN_ATTEMPTS.pop(key, None)
            _LOGIN_LOCKED_UNTIL[key] = now + LOGIN_LOCKOUT_SECONDS
        else:
            _LOGIN_ATTEMPTS[key] = attempts


def _clear_login_failures(key: str) -> None:
    with _LOGIN_RATE_LOCK:
        _LOGIN_ATTEMPTS.pop(key, None)
        _LOGIN_LOCKED_UNTIL.pop(key, None)


def _serialize_user(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item.pop("password_hash", None)
    item.pop("password_salt", None)
    role_key = str(item.get("role_key") or "member")
    if role_key not in ROLE_DEFINITIONS:
        role_key = "member"
    try:
        overrides = json.loads(str(item.get("permission_overrides") or "{}"))
        if not isinstance(overrides, dict):
            overrides = {}
    except Exception:
        overrides = {}
    overrides = _normalize_permission_overrides(overrides)
    effective = _effective_permissions(role_key, overrides)
    for key in PERMISSION_FIELDS:
        item[key] = effective[key]
    item["role_key"] = role_key
    item["role_label"] = ROLE_DEFINITIONS[role_key]["label"]
    item["permission_overrides"] = overrides
    item["active"] = bool(item.get("active", 0))
    return item


def _user_profile(user_id: int) -> dict[str, Any]:
    with connect() as db:
        club_id = _active_club_id(db)
        row = db.execute(
            """
            SELECT
                u.*,
                m.name AS member_name
            FROM users u
            LEFT JOIN members m
              ON m.id = u.member_id
             AND m.club_id = ?
            WHERE u.id = ?
            """,
            (club_id, user_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="Benutzer nicht gefunden")
        club_role = _user_club_access(db, user_id, club_id)
        if club_role is None:
            raise HTTPException(status_code=401, detail="Kein Zugriff auf diesen Verein")
        item = dict(row)
        item["club_role"] = club_role
        item["current_club_id"] = club_id
        item["is_super_admin"] = club_role == "super_admin"
    return _serialize_user(item)


def _extract_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Anmeldung erforderlich")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Anmeldung erforderlich")
    return token


def _is_super_admin(db: sqlite3.Connection, user_id: int) -> bool:
    return bool(
        db.execute(
            """
            SELECT 1
            FROM user_clubs
            WHERE user_id = ? AND active = 1 AND role = 'super_admin'
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    )


def _user_club_access(
    db: sqlite3.Connection,
    user_id: int,
    club_id: int,
) -> str | None:
    if _is_super_admin(db, user_id):
        return "super_admin"
    row = db.execute(
        """
        SELECT role
        FROM user_clubs
        WHERE user_id = ? AND club_id = ? AND active = 1
        """,
        (user_id, club_id),
    ).fetchone()
    return str(row["role"]) if row is not None else None


def _accessible_club_rows(
    db: sqlite3.Connection,
    user_id: int,
) -> list[sqlite3.Row]:
    if _is_super_admin(db, user_id):
        return db.execute(
            """
            SELECT
                id, slug, name, short_name, active, primary_color,
                billing_status
            FROM clubs
            WHERE active = 1
            ORDER BY name COLLATE NOCASE, id
            """
        ).fetchall()
    return db.execute(
        """
        SELECT
            c.id, c.slug, c.name, c.short_name, c.active, c.primary_color,
            c.billing_status
        FROM clubs c
        JOIN user_clubs uc ON uc.club_id = c.id
        WHERE uc.user_id = ?
          AND uc.active = 1
          AND c.active = 1
          AND c.billing_status = 'active'
        ORDER BY c.name COLLATE NOCASE, c.id
        """,
        (user_id,),
    ).fetchall()


def current_user(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    token = _extract_token(authorization)
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        row = db.execute(
            """
            SELECT u.*, s.active_club_id, m.name AS member_name
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            LEFT JOIN members m
              ON m.id = u.member_id
             AND m.club_id = s.active_club_id
            WHERE s.token_hash = ?
              AND s.expires_at > ?
              AND u.active = 1
            """,
            (_token_hash(token), now),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="Sitzung ungültig oder abgelaufen")

        club_id = int(row["active_club_id"] or _instance_club_id(db))
        club = db.execute(
            """
            SELECT id, billing_status, billing_suspension_reason
            FROM clubs
            WHERE id = ? AND active = 1
            """,
            (club_id,),
        ).fetchone()
        club_role = _user_club_access(db, int(row["id"]), club_id)
        if club is None or club_role is None:
            raise HTTPException(status_code=401, detail="Kein Zugriff auf diesen Verein")
        if str(club["billing_status"] or "active") != "active" and club_role != "super_admin":
            reason = str(club["billing_suspension_reason"] or "Ausstehende Zahlung")
            raise HTTPException(
                status_code=403,
                detail=f"Verein gesperrt: {reason}",
            )

        item = dict(row)
        item["club_role"] = club_role
        item["current_club_id"] = club_id
        item["is_super_admin"] = club_role == "super_admin"
    return _serialize_user(item)


def require(permission: str):
    def dependency(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        if not user.get(permission, False):
            raise HTTPException(status_code=403, detail="Keine Berechtigung")
        return user
    return dependency


def table_or_404(name: str) -> tuple[str, type[BaseModel]]:
    table = TABLES.get(name)
    if table is None:
        raise HTTPException(status_code=404, detail="Unknown resource")
    return table


def _instance_club_id(db: sqlite3.Connection) -> int:
    row = db.execute(
        "SELECT id FROM clubs WHERE slug = ? AND active = 1",
        (INSTANCE_ID,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Active club not found for instance '{INSTANCE_ID}'")
    return int(row["id"])


def _active_club_id(db: sqlite3.Connection) -> int:
    """Resolve the current request club, falling back to the instance club."""
    request_club_id = _REQUEST_CLUB_ID.get()
    if request_club_id is not None:
        row = db.execute(
            "SELECT id FROM clubs WHERE id = ? AND active = 1",
            (request_club_id,),
        ).fetchone()
        if row is not None:
            return int(row["id"])
    return _instance_club_id(db)


def _club_features(
    db: sqlite3.Connection,
    club_id: int | None = None,
) -> dict[str, dict[str, Any]]:
    resolved_club_id = club_id if club_id is not None else _active_club_id(db)
    rows = db.execute(
        """
        SELECT feature_key, enabled, label
        FROM club_features
        WHERE club_id = ?
        ORDER BY feature_key
        """,
        (resolved_club_id,),
    ).fetchall()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        result[str(row["feature_key"])] = {
            "enabled": bool(row["enabled"]),
            "label": str(row["label"] or ""),
        }
    return result


def _club_feature_enabled(
    db: sqlite3.Connection,
    feature_key: str,
    club_id: int | None = None,
) -> bool:
    feature = _club_features(db, club_id).get(feature_key)
    if feature is not None:
        return bool(feature["enabled"])
    default = CLUB_FEATURE_DEFAULTS.get(feature_key)
    return bool(default[1]) if default is not None else False


def _set_club_features(
    db: sqlite3.Connection,
    club_id: int,
    features: dict[str, bool],
    labels: dict[str, str] | None = None,
) -> None:
    labels = labels or {}
    unknown = sorted(set(features) - set(CLUB_FEATURE_DEFAULTS))
    unknown_labels = sorted(set(labels) - set(CLUB_FEATURE_DEFAULTS))
    if unknown or unknown_labels:
        invalid = ", ".join(unknown + unknown_labels)
        raise HTTPException(
            status_code=422,
            detail=f"Unbekanntes Modul: {invalid}",
        )

    now = datetime.now(timezone.utc).isoformat()
    for feature_key, enabled in features.items():
        default_label = CLUB_FEATURE_DEFAULTS[feature_key][0]
        label = str(labels.get(feature_key) or default_label).strip()[:80]
        db.execute(
            """
            INSERT INTO club_features (
                club_id, feature_key, enabled, label, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(club_id, feature_key) DO UPDATE SET
                enabled = excluded.enabled,
                label = CASE
                    WHEN excluded.label <> '' THEN excluded.label
                    ELSE club_features.label
                END,
                updated_at = excluded.updated_at
            """,
            (club_id, feature_key, int(bool(enabled)), label, now, now),
        )


RESOURCE_FEATURES: dict[str, str] = {
    "news": "news",
    "events": "events",
    "members": "members",
}

SECTION_FEATURES: dict[str, str] = {
    "documents": "documents",
    "gallery": "gallery",
    "photos": "photos",
    "sujet": "sujet_next",
    "archive": "sujet_archive",
    "polls": "polls",
    "links": "links",
    "whatsapp": "links",
}


def _require_club_feature(
    db: sqlite3.Connection,
    feature_key: str,
) -> None:
    if not _club_feature_enabled(db, feature_key):
        raise HTTPException(status_code=404, detail="Modul nicht aktiviert")


def _require_resource_feature(
    db: sqlite3.Connection,
    resource: str,
) -> None:
    feature_key = RESOURCE_FEATURES.get(resource)
    if feature_key is not None:
        _require_club_feature(db, feature_key)


def _require_section_feature(
    db: sqlite3.Connection,
    section: str,
) -> None:
    feature_key = SECTION_FEATURES.get(section)
    if feature_key is not None:
        _require_club_feature(db, feature_key)


def _active_club_membership(
    db: sqlite3.Connection,
    user_id: int,
) -> sqlite3.Row | None:
    return db.execute(
        """
        SELECT uc.user_id, uc.club_id, uc.role, uc.active
        FROM user_clubs uc
        WHERE uc.user_id = ?
          AND uc.club_id = ?
          AND uc.active = 1
        """,
        (user_id, _active_club_id(db)),
    ).fetchone()


def _require_active_club_row(
    db: sqlite3.Connection,
    table: str,
    row_id: int,
) -> sqlite3.Row:
    club_id = _active_club_id(db)
    row = db.execute(
        f"SELECT * FROM {table} WHERE id = ? AND club_id = ?",
        (row_id, club_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return row


def _serialize_news(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    has_image = bool(item.pop("image_data", None))
    item.pop("image_mime", None)
    if has_image:
        item["image_url"] = f"/api/news/{item['id']}/image"
    return item


def _serialize_member(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    has_photo = bool(item.pop("photo_data", None))
    item.pop("photo_mime", None)
    item["photo_url"] = (
        f"/api/members/{item['id']}/photo" if has_photo else ""
    )
    with connect() as db:
        item["filter_ids"] = [
            int(link["filter_id"])
            for link in db.execute(
                """
                SELECT filter_id
                FROM member_filter_links
                WHERE member_id = ? AND club_id = ?
                ORDER BY filter_id ASC
                """,
                (item["id"], _active_club_id(db)),
            ).fetchall()
        ]
    return item


CONTENT_PUSH_RULES = {
    "documents": ("document", "Neues Dokument", "/more"),
    "polls": ("poll", "Neue Umfrage", "/more"),
    "photos": ("photo_album", "Neues Fotoalbum", "/more"),
    "gallery": ("gallery", "Neuer Galerie-Inhalt", "/gallery"),
    "sujet": ("sujet", "Neues Sujet", "/more"),
    "archive": ("archive", "Neuer Archiv-Inhalt", "/more"),
}


def _queue_push_notification(
    db: sqlite3.Connection,
    *,
    kind: str,
    title: str,
    body: str = "",
    route: str = "",
) -> None:
    db.execute(
        """
        INSERT INTO push_notifications (
            kind, title, body, route, created_at, club_id
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            kind,
            title[:200],
            body[:500],
            route,
            datetime.now(timezone.utc).isoformat(),
            _active_club_id(db),
        ),
    )


def list_rows(resource: str) -> list[dict[str, Any]]:
    table_or_404(resource)
    if resource == "news":
        order = "sort_order ASC, created_at DESC, id DESC"
    elif resource == "events":
        order = (
            "CASE WHEN event_date = '' THEN '9999-12-31' ELSE event_date END ASC, "
            "time ASC, id ASC"
        )
    elif resource == "members":
        order = "sort_order ASC, name COLLATE NOCASE ASC, id ASC"
    else:
        order = "name COLLATE NOCASE ASC, id ASC"

    with connect() as db:
        _require_resource_feature(db, resource)
        club_id = _active_club_id(db)
        rows = db.execute(
            f"SELECT * FROM {resource} WHERE club_id = ? ORDER BY {order}",
            (club_id,),
        ).fetchall()

    if resource == "news":
        return [_serialize_news(row) for row in rows]
    if resource == "members":
        return [_serialize_member(row) for row in rows]
    return [dict(row) for row in rows]


def create_row(resource: str, payload: BaseModel) -> dict[str, Any]:
    table_or_404(resource)
    data = payload.model_dump()
    member_filter_ids = data.pop("filter_ids", []) if resource == "members" else []
    data["created_at"] = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        _require_resource_feature(db, resource)
        data["club_id"] = _active_club_id(db)
        if resource in {"members", "news"}:
            data["sort_order"] = db.execute(
                f"SELECT COALESCE(MAX(sort_order), 0) + 1 FROM {resource} WHERE club_id = ?",
                (data["club_id"],),
            ).fetchone()[0]
    columns = list(data.keys())
    placeholders = ", ".join("?" for _ in columns)
    sql = (
        f"INSERT INTO {resource} ({', '.join(columns)}) "
        f"VALUES ({placeholders})"
    )
    with connect() as db:
        cursor = db.execute(sql, [data[column] for column in columns])
        if resource == "members":
            for filter_id in sorted(set(member_filter_ids)):
                db.execute(
                    "INSERT OR IGNORE INTO member_filter_links (member_id, filter_id, club_id) VALUES (?, ?, ?)",
                    (cursor.lastrowid, filter_id, _active_club_id(db)),
                )
        db.commit()
        row = db.execute(
            f"SELECT * FROM {resource} WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    if resource == "news":
        return _serialize_news(row)
    if resource == "members":
        return _serialize_member(row)
    return dict(row)


def update_row(resource: str, row_id: int, payload: BaseModel) -> dict[str, Any]:
    table_or_404(resource)
    data = payload.model_dump()
    member_filter_ids = data.pop("filter_ids", []) if resource == "members" else []
    assignments = ", ".join(f"{column} = ?" for column in data)
    with connect() as db:
        _require_resource_feature(db, resource)
        cursor = db.execute(
            f"UPDATE {resource} SET {assignments} WHERE id = ? AND club_id = ?",
            [*data.values(), row_id, _active_club_id(db)],
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Entry not found")
        if resource == "members":
            db.execute(
                "DELETE FROM member_filter_links WHERE member_id = ? AND club_id = ?",
                (row_id, _active_club_id(db)),
            )
            for filter_id in sorted(set(member_filter_ids)):
                db.execute(
                    """
                    INSERT OR IGNORE INTO member_filter_links
                        (member_id, filter_id, club_id)
                    VALUES (?, ?, ?)
                    """,
                    (row_id, filter_id, _active_club_id(db)),
                )
        db.commit()
        row = db.execute(
            f"SELECT * FROM {resource} WHERE id = ? AND club_id = ?",
            (row_id, _active_club_id(db)),
        ).fetchone()
    if resource == "news":
        return _serialize_news(row)
    if resource == "members":
        return _serialize_member(row)
    return dict(row)


def delete_row(resource: str, row_id: int) -> None:
    table_or_404(resource)
    with connect() as db:
        _require_resource_feature(db, resource)
        cursor = db.execute(
            f"DELETE FROM {resource} WHERE id = ? AND club_id = ?",
            (row_id, _active_club_id(db)),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Entry not found")
        db.commit()


CONTENT_PERMISSIONS = {
    "hero": "can_photos",
    "sujet": "can_photos",
    "archive": "can_photos",
    "gallery": "can_photos",
    "documents": "can_documents",
    "photos": "can_photos",
    "polls": "can_polls",
    "links": "can_links",
    "whatsapp": "can_links",
    "contact": "can_contact",
    "about": "can_about",
}


def _serialize_content(
    row: sqlite3.Row,
    user_id: int | None = None,
) -> dict[str, Any]:
    item = dict(row)
    item.pop("image_data", None)
    item.pop("image_mime", None)
    has_document = bool(item.pop("document_data", None))
    document_mime = str(item.pop("document_mime", "") or "")
    document_name = str(item.get("document_name", "") or "")
    with connect() as db:
        image_rows = db.execute(
            """
            SELECT id, sort_order, created_at
            FROM content_images
            WHERE content_id = ?
            ORDER BY sort_order ASC, id ASC
            """,
            (item["id"],),
        ).fetchall()
        if item.get("section") == "polls":
            try:
                options = json.loads(item.get("poll_options") or "[]")
            except Exception:
                options = []
            if not isinstance(options, list):
                options = []
            options = [str(value).strip() for value in options if str(value).strip()]
            counts = [0 for _ in options]
            for vote in db.execute(
                """
                SELECT option_index, COUNT(*) AS count
                FROM poll_votes
                WHERE poll_id = ?
                GROUP BY option_index
                """,
                (item["id"],),
            ).fetchall():
                index = int(vote["option_index"])
                if 0 <= index < len(counts):
                    counts[index] = int(vote["count"])
            my_vote = None
            if user_id is not None:
                vote = db.execute(
                    "SELECT option_index FROM poll_votes WHERE poll_id = ? AND user_id = ?",
                    (item["id"], user_id),
                ).fetchone()
                if vote is not None:
                    my_vote = int(vote["option_index"])
            voter_rows = db.execute(
                """
                SELECT
                    pv.option_index,
                    COALESCE(NULLIF(TRIM(m.name), ''), u.username) AS voter_name
                FROM poll_votes pv
                JOIN users u ON u.id = pv.user_id
                LEFT JOIN members m ON m.id = u.member_id
                WHERE pv.poll_id = ?
                ORDER BY voter_name COLLATE NOCASE ASC, u.id ASC
                """,
                (item["id"],),
            ).fetchall()
            suggestion_rows = db.execute(
                """
                SELECT
                    ps.option_index,
                    ps.suggestion_text,
                    COALESCE(NULLIF(TRIM(m.name), ''), u.username) AS member_name
                FROM poll_suggestions ps
                JOIN users u ON u.id = ps.user_id
                LEFT JOIN members m ON m.id = u.member_id
                WHERE ps.poll_id = ?
                ORDER BY ps.created_at ASC, ps.user_id ASC
                """,
                (item["id"],),
            ).fetchall()

            my_suggestion_index = None
            my_suggestion_text = ""
            if user_id is not None:
                suggestion = db.execute(
                    """
                    SELECT option_index, suggestion_text
                    FROM poll_suggestions
                    WHERE poll_id = ? AND user_id = ?
                    """,
                    (item["id"], user_id),
                ).fetchone()
                if suggestion is not None:
                    index = int(suggestion["option_index"])
                    if 0 <= index < len(options):
                        my_suggestion_index = index
                        my_suggestion_text = str(options[index] or "").strip()

            item["poll_options"] = options
            item["poll_allow_suggestions"] = bool(
                item.get("poll_allow_suggestions", 0)
            )
            item["poll_counts"] = counts
            item["poll_total_votes"] = sum(counts)
            item["poll_my_vote"] = my_vote
            item["poll_my_suggestion_index"] = my_suggestion_index
            item["poll_my_suggestion_text"] = my_suggestion_text
            item["poll_voters"] = [
                {
                    "name": str(voter["voter_name"] or "").strip(),
                    "option_index": int(voter["option_index"]),
                }
                for voter in voter_rows
                if str(voter["voter_name"] or "").strip()
            ]
            item["poll_suggestions"] = [
                {
                    "member_name": str(suggestion["member_name"] or "").strip(),
                    "text": (
                        str(options[int(suggestion["option_index"])]).strip()
                        if 0 <= int(suggestion["option_index"]) < len(options)
                        else str(suggestion["suggestion_text"] or "").strip()
                    ),
                    "option_index": int(suggestion["option_index"]),
                    "vote_count": (
                        counts[int(suggestion["option_index"])]
                        if 0 <= int(suggestion["option_index"]) < len(counts)
                        else 0
                    ),
                }
                for suggestion in suggestion_rows
                if str(suggestion["suggestion_text"] or "").strip()
            ]
        else:
            item["poll_options"] = []
            item["poll_allow_suggestions"] = False
            item["poll_counts"] = []
            item["poll_total_votes"] = 0
            item["poll_my_vote"] = None
            item["poll_my_suggestion_index"] = None
            item["poll_my_suggestion_text"] = ""
            item["poll_voters"] = []
            item["poll_suggestions"] = []
    images = [
        {
            "id": image_row["id"],
            "url": f"/api/content/{item['id']}/images/{image_row['id']}",
            "legacy": False,
            "sort_order": image_row["sort_order"],
            "created_at": image_row["created_at"],
        }
        for image_row in image_rows
    ]
    image_urls = [image["url"] for image in images]
    item["images"] = images
    item["image_urls"] = image_urls
    item["image_url"] = image_urls[0] if image_urls else ""
    item["document_url"] = (
        f"/api/content/{item['id']}/document" if has_document else ""
    )
    item["document_name"] = document_name
    item["document_mime"] = document_mime if has_document else ""
    return item

def _cleanup_expired_snapshots(db: sqlite3.Connection) -> None:
    db.execute(
        "DELETE FROM gallery_snapshots WHERE expires_at <= ?",
        (datetime.now(timezone.utc).isoformat(),),
    )


def _serialize_snapshot(
    row: sqlite3.Row,
    user: dict[str, Any],
) -> dict[str, Any]:
    owner_name = row["member_name"] or row["username"]
    can_delete = row["user_id"] == user["id"] or bool(user.get("can_photos", False))
    return {
        "id": None,
        "snapshot_id": row["id"],
        "section": "gallery",
        "title": f"Snapshot von {owner_name}",
        "text": "",
        "link_url": "",
        "sort_order": -1,
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "is_snapshot": True,
        "can_delete": can_delete,
        "image_url": f"/api/gallery/snapshots/{row['id']}/image",
        "image_urls": [f"/api/gallery/snapshots/{row['id']}/image"],
        "images": [],
    }


def _content_permission(section: str) -> str:
    permission = CONTENT_PERMISSIONS.get(section)
    if permission is None:
        raise HTTPException(status_code=422, detail="Unbekannter Bereich")
    return permission


def _require_content_permission(
    section: str,
    user: dict[str, Any],
) -> None:
    permission = _content_permission(section)
    if not user.get(permission, False):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")


def _app_config() -> dict[str, Any]:
    with connect() as db:
        club_id = _active_club_id(db)
        club = db.execute(
            "SELECT * FROM clubs WHERE id = ?",
            (club_id,),
        ).fetchone()
        app_row = db.execute(
            """
            SELECT app_subtitle
            FROM app_config
            WHERE id = 1
            """
        ).fetchone()
        features = _club_features(db, club_id)

    if club is None:
        raise RuntimeError("Active club configuration is missing")

    def enabled(key: str) -> bool:
        value = features.get(key)
        if value is not None:
            return bool(value["enabled"])
        default = CLUB_FEATURE_DEFAULTS.get(key)
        return bool(default[1]) if default is not None else False

    def label(key: str) -> str:
        value = features.get(key)
        if value is not None and str(value["label"] or "").strip():
            return str(value["label"]).strip()
        default = CLUB_FEATURE_DEFAULTS.get(key)
        return default[0] if default is not None else key

    return {
        "instance_id": INSTANCE_ID,
        "club_id": int(club["id"]),
        "slug": str(club["slug"] or ""),
        "app_name": str(club["name"] or "FLAPAMAMAKU"),
        "short_name": str(club["short_name"] or club["name"] or ""),
        "app_subtitle": str(club["subtitle"] or ""),
        "primary_color": str(club["primary_color"] or "#8A101B"),
        "secondary_color": str(club["secondary_color"] or "#FFFFFF"),
        "logo_url": "/api/app-config/logo" if club["logo"] else "",
        "club_description": str(club["description"] or ""),
        "website_url": str(club["website"] or ""),
        "contact_email": str(club["email"] or ""),
        "contact_phone": str(club["phone"] or ""),
        "club_address": str(club["address"] or ""),
        "city": str(club["city"] or ""),
        "country": str(club["country"] or ""),
        "app_title": str(club["app_title"] or ""),
        "welcome_text": str(club["welcome_text"] or ""),
        "features": features,
        "show_news": enabled("news"),
        "show_events": enabled("events"),
        "show_members": enabled("members"),
        "show_gallery": enabled("gallery"),
        "show_sujet": enabled("sujet_next"),
        "label_sujet": label("sujet_next"),
        "show_archive": enabled("sujet_archive"),
        "label_archive": label("sujet_archive"),
        "show_photos": enabled("photos"),
        "label_photos": label("photos"),
        "show_documents": enabled("documents"),
        "label_documents": label("documents"),
        "show_polls": enabled("polls"),
        "label_polls": label("polls"),
        "show_links": enabled("links"),
        "label_links": label("links"),
        "show_push_notifications": enabled("push_notifications"),
        "show_calendar": enabled("calendar"),
        "show_participant_lists": enabled("participant_lists"),
    }

def _club_setup_status() -> dict[str, Any]:
    config = _app_config()
    with connect() as db:
        administrator_ready = bool(
            db.execute(
                """
                SELECT 1
                FROM users u
                JOIN user_clubs uc ON uc.user_id = u.id
                WHERE u.active = 1
                  AND u.can_manage_users = 1
                  AND uc.club_id = ?
                  AND uc.active = 1
                LIMIT 1
                """,
                (_active_club_id(db),),
            ).fetchone()
        )

    app_name = str(config.get("app_name") or "").strip()
    identity_ready = bool(app_name)
    if INSTANCE_ID != "flapamamaku" and app_name.upper() == "FLAPAMAMAKU":
        identity_ready = False

    contact_ready = any(
        str(config.get(key) or "").strip()
        for key in ("contact_email", "contact_phone", "website_url")
    )
    modules_ready = any(
        bool(config.get(key))
        for key in (
            "show_sujet",
            "show_archive",
            "show_photos",
            "show_documents",
            "show_polls",
            "show_links",
        )
    )

    required = {
        "administrator": {
            "ok": administrator_ready,
            "label": "Hauptadministrator vorhanden",
        },
        "identity": {
            "ok": identity_ready,
            "label": "Vereinsname eingerichtet",
        },
        "contact": {
            "ok": contact_ready,
            "label": "Mindestens eine Kontaktmöglichkeit erfasst",
        },
        "modules": {
            "ok": modules_ready,
            "label": "Mindestens ein Inhaltsmodul aktiviert",
        },
    }

    recommended = {
        "logo": {
            "ok": bool(str(config.get("logo_url") or "").strip()),
            "label": "Vereinslogo hinterlegt",
        },
        "description": {
            "ok": bool(str(config.get("club_description") or "").strip()),
            "label": "Vereinsbeschreibung erfasst",
        },
        "backup": {
            "ok": bool(_backup_files()),
            "label": "Mindestens ein Backup vorhanden",
        },
        "push": {
            "ok": bool(FIREBASE_SERVICE_ACCOUNT_JSON),
            "label": "Push-Zustellung konfiguriert",
        },
        "production": {
            "ok": bool(_production_readiness()["ready"]),
            "label": "Öffentlicher Produktionsbetrieb bereit",
        },
    }

    required_done = sum(1 for item in required.values() if item["ok"])
    recommended_done = sum(1 for item in recommended.values() if item["ok"])
    return {
        "instance_id": INSTANCE_ID,
        "required_complete": required_done == len(required),
        "required_done": required_done,
        "required_total": len(required),
        "recommended_done": recommended_done,
        "recommended_total": len(recommended),
        "required": required,
        "recommended": recommended,
    }


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "FLAPAMAMAKU API",
        "admin": "/admin",
        "docs": "/api/docs",
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    readiness = _production_readiness()
    return {
        "status": "ok",
        "instance_id": INSTANCE_ID,
        "version": API_VERSION,
        "build_sha": BUILD_SHA,
        "schema_version": _schema_version(),
        "production_ready": readiness["ready"],
    }


@app.get("/api/app-config")
def get_app_config() -> dict[str, Any]:
    return _app_config()


@app.get("/api/app-config/features")
def get_app_features() -> dict[str, dict[str, Any]]:
    with connect() as db:
        return _club_features(db)


@app.put("/api/app-config/features")
def put_app_features(
    payload: ClubFeaturesPayload,
    _: dict[str, Any] = Depends(require("can_manage_settings")),
) -> dict[str, dict[str, Any]]:
    with connect() as db:
        club_id = _active_club_id(db)
        _set_club_features(db, club_id, payload.features, payload.labels)
        db.commit()
        return _club_features(db, club_id)


@app.put("/api/app-config")
def put_app_config(
    payload: AppConfigPayload,
    _: dict[str, Any] = Depends(require("can_manage_settings")),
) -> dict[str, Any]:
    values = payload.model_dump()
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        club_id = _active_club_id(db)
        db.execute(
            """
            UPDATE clubs
            SET
                name = ?,
                short_name = ?,
                subtitle = ?,
                primary_color = ?,
                secondary_color = ?,
                description = ?,
                website = ?,
                email = ?,
                phone = ?,
                address = ?,
                city = ?,
                country = ?,
                app_title = ?,
                welcome_text = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                values["app_name"].strip(),
                values["short_name"].strip() or values["app_name"].strip(),
                values["app_subtitle"].strip(),
                values["primary_color"].upper(),
                values["secondary_color"].upper(),
                values["club_description"].strip(),
                values["website_url"].strip(),
                values["contact_email"].strip(),
                values["contact_phone"].strip(),
                values["club_address"].strip(),
                values["city"].strip(),
                values["country"].strip(),
                values["app_title"].strip(),
                values["welcome_text"].strip(),
                now,
                club_id,
            ),
        )

        _set_club_features(
            db,
            club_id,
            {
                "sujet_next": bool(values["show_sujet"]),
                "sujet_archive": bool(values["show_archive"]),
                "photos": bool(values["show_photos"]),
                "documents": bool(values["show_documents"]),
                "polls": bool(values["show_polls"]),
                "links": bool(values["show_links"]),
            },
            {
                "sujet_next": values["label_sujet"].strip(),
                "sujet_archive": values["label_archive"].strip(),
                "photos": values["label_photos"].strip(),
                "documents": values["label_documents"].strip(),
                "polls": values["label_polls"].strip(),
                "links": values["label_links"].strip(),
            },
        )

        if club_id == 1:
            # Keep the legacy module columns synchronized during the transition.
            db.execute(
                """
                UPDATE app_config
                SET
                    app_subtitle = ?,
                    show_sujet = ?,
                    label_sujet = ?,
                    show_archive = ?,
                    label_archive = ?,
                    show_photos = ?,
                    label_photos = ?,
                    show_documents = ?,
                    label_documents = ?,
                    show_polls = ?,
                    label_polls = ?,
                    show_links = ?,
                    label_links = ?,
                    updated_at = ?
                WHERE id = 1
                """,
                (
                    values["app_subtitle"].strip(),
                    int(values["show_sujet"]),
                    values["label_sujet"].strip(),
                    int(values["show_archive"]),
                    values["label_archive"].strip(),
                    int(values["show_photos"]),
                    values["label_photos"].strip(),
                    int(values["show_documents"]),
                    values["label_documents"].strip(),
                    int(values["show_polls"]),
                    values["label_polls"].strip(),
                    int(values["show_links"]),
                    values["label_links"].strip(),
                    now,
                ),
            )

        # Keep the original FLAPAMAMAKU compatibility row synchronized while
        # the app migrates to the central clubs configuration.
        if club_id == 1:
            db.execute(
                """
                UPDATE app_config
                SET
                    app_name = ?,
                    primary_color = ?,
                    club_description = ?,
                    website_url = ?,
                    contact_email = ?,
                    contact_phone = ?,
                    club_address = ?
                WHERE id = 1
                """,
                (
                    values["app_name"].strip(),
                    values["primary_color"].upper(),
                    values["club_description"].strip(),
                    values["website_url"].strip(),
                    values["contact_email"].strip(),
                    values["contact_phone"].strip(),
                    values["club_address"].strip(),
                ),
            )
        db.commit()
    return _app_config()

@app.get("/api/app-config/logo")
def get_app_logo() -> Response:
    with connect() as db:
        row = db.execute(
            "SELECT logo, logo_mime FROM clubs WHERE id = ?",
            (_active_club_id(db),),
        ).fetchone()
    if row is None or not row["logo"]:
        raise HTTPException(status_code=404, detail="Logo nicht vorhanden")
    return Response(
        content=row["logo"],
        media_type=row["logo_mime"] or "image/webp",
        headers={"Cache-Control": "no-cache"},
    )


@app.post("/api/app-config/logo")
async def upload_app_logo(
    logo: UploadFile = File(...),
    _: dict[str, Any] = Depends(require("can_manage_settings")),
) -> dict[str, Any]:
    raw = await logo.read()
    optimized, mime = _optimize_image(raw, logo.content_type or "")
    with connect() as db:
        club_id = _active_club_id(db)
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            """
            UPDATE clubs
            SET logo = ?, logo_mime = ?, updated_at = ?
            WHERE id = ?
            """,
            (optimized, mime, now, club_id),
        )
        if club_id == 1:
            db.execute(
                """
                UPDATE app_config
                SET logo_data = ?, logo_mime = ?, updated_at = ?
                WHERE id = 1
                """,
                (optimized, mime, now),
            )
        db.commit()
    return _app_config()


@app.delete("/api/app-config/logo", status_code=204)
def delete_app_logo(
    _: dict[str, Any] = Depends(require("can_manage_settings")),
) -> None:
    with connect() as db:
        club_id = _active_club_id(db)
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            """
            UPDATE clubs
            SET logo = NULL, logo_mime = '', updated_at = ?
            WHERE id = ?
            """,
            (now, club_id),
        )
        if club_id == 1:
            db.execute(
                """
                UPDATE app_config
                SET logo_data = NULL, logo_mime = '', updated_at = ?
                WHERE id = 1
                """,
                (now,),
            )
        db.commit()


@app.get("/admin")
def admin() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "admin.html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "flapamamaku-icon.png",
        media_type="image/png",
    )


@app.get("/flapamamaku-icon.png", include_in_schema=False)
def flapamamaku_icon() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "flapamamaku-icon.png",
        media_type="image/png",
    )


@app.get("/api/system/status")
def system_status(
    _: dict[str, Any] = Depends(require("can_manage_users")),
) -> dict[str, Any]:
    backups = _backup_files()
    latest_backup = _backup_info(backups[0]) if backups else None
    latest_backup_age_seconds: int | None = None
    if backups:
        latest_backup_age_seconds = max(
            0,
            int(datetime.now(timezone.utc).timestamp() - backups[0].stat().st_mtime),
        )

    database_integrity = "unbekannt"
    active_users = 0
    active_sessions = 0
    members = 0
    registered_devices = 0
    queued_push = 0
    try:
        with connect() as db:
            integrity = db.execute("PRAGMA quick_check").fetchone()
            database_integrity = (
                str(integrity[0]).lower() if integrity is not None else "unbekannt"
            )
            club_id = _active_club_id(db)
            active_users = int(
                db.execute(
                    """
                    SELECT COUNT(*)
                    FROM user_clubs uc
                    JOIN users u ON u.id = uc.user_id
                    WHERE uc.club_id = ? AND uc.active = 1 AND u.active = 1
                    """,
                    (club_id,),
                ).fetchone()[0]
            )
            active_sessions = int(
                db.execute(
                    "SELECT COUNT(*) FROM sessions WHERE active_club_id = ?",
                    (club_id,),
                ).fetchone()[0]
            )
            members = int(
                db.execute(
                    "SELECT COUNT(*) FROM members WHERE club_id = ?",
                    (club_id,),
                ).fetchone()[0]
            )
            registered_devices = int(
                db.execute(
                    """
                    SELECT COUNT(*)
                    FROM push_tokens
                    WHERE enabled = 1 AND club_id = ?
                    """,
                    (club_id,),
                ).fetchone()[0]
            )
            queued_push = int(
                db.execute(
                    """
                    SELECT COUNT(*)
                    FROM push_notifications
                    WHERE sent_at IS NULL AND club_id = ?
                    """,
                    (club_id,),
                ).fetchone()[0]
            )
    except sqlite3.Error:
        database_integrity = "fehler"

    storage_total = 0
    storage_free = 0
    try:
        stat = os.statvfs(DB_PATH.parent)
        storage_total = int(stat.f_blocks * stat.f_frsize)
        storage_free = int(stat.f_bavail * stat.f_frsize)
    except OSError:
        pass

    backup_ok = (
        latest_backup_age_seconds is not None
        and latest_backup_age_seconds <= max(BACKUP_INTERVAL_SECONDS * 2, 172800)
    )
    schema_ok = _schema_version() == CURRENT_SCHEMA_VERSION
    database_ok = database_integrity == "ok"
    overall_status = "ok" if database_ok and schema_ok and backup_ok else "warning"

    return {
        "overall_status": overall_status,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "api_version": API_VERSION,
        "instance_id": INSTANCE_ID,
        "build_sha": BUILD_SHA,
        "schema_version": _schema_version(),
        "expected_schema_version": CURRENT_SCHEMA_VERSION,
        "schema_ok": schema_ok,
        "database_integrity": database_integrity,
        "database_ok": database_ok,
        "database_path": str(DB_PATH),
        "database_size_bytes": DB_PATH.stat().st_size if DB_PATH.exists() else 0,
        "storage_total_bytes": storage_total,
        "storage_free_bytes": storage_free,
        "backup_directory": str(BACKUP_DIR),
        "backup_retention": BACKUP_RETENTION,
        "backup_count": len(backups),
        "latest_backup": latest_backup,
        "latest_backup_age_seconds": latest_backup_age_seconds,
        "backup_ok": backup_ok,
        "active_users": active_users,
        "active_sessions": active_sessions,
        "members": members,
        "registered_devices": registered_devices,
        "queued_push": queued_push,
    }


@app.get("/api/system/readiness")
def system_readiness(
    _: dict[str, Any] = Depends(require("can_manage_users")),
) -> dict[str, Any]:
    readiness = _production_readiness()
    return {
        **readiness,
        "environment": APP_ENV,
        "instance_id": INSTANCE_ID,
        "api_version": API_VERSION,
        "build_sha": BUILD_SHA,
        "session_lifetime_days": SESSION_LIFETIME_DAYS,
        "expected_schema_version": CURRENT_SCHEMA_VERSION,
    }


@app.get("/api/system/setup-status")
def system_setup_status(
    _: dict[str, Any] = Depends(require("can_manage_settings")),
) -> dict[str, Any]:
    return _club_setup_status()


@app.get("/api/system/backups")
def list_backups(
    _: dict[str, Any] = Depends(require("can_manage_users")),
) -> list[dict[str, Any]]:
    return [_backup_info(path) for path in _backup_files()]


@app.post("/api/system/backups")
def create_backup(
    _: dict[str, Any] = Depends(require("can_manage_users")),
) -> dict[str, Any]:
    try:
        path = _create_database_backup("manual")
    except Exception as exc:
        logger.exception("Manual database backup failed")
        raise HTTPException(status_code=500, detail="Backup konnte nicht erstellt werden") from exc
    return _backup_info(path)


@app.get("/api/system/backups/{filename}")
def download_backup(
    filename: str,
    _: dict[str, Any] = Depends(require("can_manage_users")),
) -> FileResponse:
    candidate = BACKUP_DIR / Path(filename).name
    valid_prefix = candidate.name.startswith(f"{INSTANCE_ID}-")
    if INSTANCE_ID == "flapamamaku":
        valid_prefix = valid_prefix or candidate.name.startswith("flapamamaku-")
    if (
        candidate.parent != BACKUP_DIR
        or not valid_prefix
        or candidate.suffix != ".db"
        or not candidate.is_file()
    ):
        raise HTTPException(status_code=404, detail="Backup nicht gefunden")
    return FileResponse(
        candidate,
        media_type="application/octet-stream",
        filename=candidate.name,
    )


@app.post("/api/system/restore")
async def restore_backup(
    backup_file: UploadFile = File(...),
    _: dict[str, Any] = Depends(require("can_manage_users")),
) -> dict[str, Any]:
    filename = Path(backup_file.filename or "").name
    if not filename.lower().endswith(".db"):
        raise HTTPException(status_code=400, detail="Bitte eine .db-Backupdatei auswählen")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    temporary = BACKUP_DIR / f".restore-upload-{secrets.token_hex(8)}.db"
    total = 0
    try:
        with temporary.open("wb") as handle:
            while True:
                chunk = await backup_file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_BACKUP_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="Backupdatei ist zu gross",
                    )
                handle.write(chunk)

        if total == 0:
            raise HTTPException(status_code=400, detail="Backupdatei ist leer")

        try:
            result = await asyncio.to_thread(_restore_database_backup, temporary)
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Database restore failed")
            raise HTTPException(
                status_code=500,
                detail="Datenbank konnte nicht wiederhergestellt werden",
            ) from exc

        result["uploaded_name"] = filename
        return result
    finally:
        await backup_file.close()
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not remove temporary restore upload %s", temporary)


@app.get("/api/auth/status")
def auth_status() -> dict[str, bool]:
    with connect() as db:
        count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    return {"bootstrap_required": count == 0}


@app.get("/api/auth/bootstrap-members")
def bootstrap_members() -> list[dict[str, Any]]:
    with connect() as db:
        count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count:
            raise HTTPException(status_code=403, detail="Ersteinrichtung abgeschlossen")
        rows = db.execute(
            "SELECT id, name FROM members ORDER BY name COLLATE NOCASE"
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/auth/bootstrap")
def bootstrap(payload: BootstrapPayload) -> dict[str, Any]:
    with connect() as db:
        count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count:
            raise HTTPException(status_code=409, detail="Ersteinrichtung bereits abgeschlossen")

        password_hash, salt = _hash_password(payload.password)
        now = datetime.now(timezone.utc).isoformat()
        values = [1 for _ in PERMISSION_FIELDS]
        cursor = db.execute(
            f"""
            INSERT INTO users (
                member_id, username, password_hash, password_salt, active,
                {", ".join(PERMISSION_FIELDS)}, role_key, permission_overrides, created_at
            ) VALUES (?, ?, ?, ?, 1, {", ".join("?" for _ in PERMISSION_FIELDS)}, 'admin', '{{}}', ?)
            """,
            [
                payload.member_id,
                payload.username.strip(),
                password_hash,
                salt,
                *values,
                now,
            ],
        )
        user_id = cursor.lastrowid
        db.execute(
            """
            INSERT INTO user_clubs (
                user_id, club_id, role, active, created_at, updated_at
            ) VALUES (?, ?, 'super_admin', 1, ?, ?)
            """,
            (user_id, _active_club_id(db), now, now),
        )
        db.commit()
    return _user_profile(user_id)


@app.post("/api/auth/login")
def login(request: Request, payload: LoginPayload) -> dict[str, Any]:
    rate_key = _login_rate_key(request, payload.username)
    _check_login_rate_limit(rate_key)

    with connect() as db:
        row = db.execute(
            """
            SELECT u.*
            FROM users u
            WHERE u.username = ? COLLATE NOCASE
              AND u.active = 1
            """,
            (payload.username.strip(),),
        ).fetchone()
        if row is None or not _check_password(
            payload.password,
            row["password_hash"],
            row["password_salt"],
        ):
            _record_login_failure(rate_key)
            raise HTTPException(status_code=401, detail="Benutzername oder Passwort falsch")

        user_id = int(row["id"])
        clubs = _accessible_club_rows(db, user_id)
        if not clubs:
            suspended = db.execute(
                """
                SELECT c.billing_suspension_reason
                FROM clubs c
                JOIN user_clubs uc ON uc.club_id = c.id
                WHERE uc.user_id = ?
                  AND uc.active = 1
                  AND c.active = 1
                  AND c.billing_status != 'active'
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            if suspended is not None:
                reason = str(
                    suspended["billing_suspension_reason"] or "Ausstehende Zahlung"
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"Verein gesperrt: {reason}",
                )
            _record_login_failure(rate_key)
            raise HTTPException(status_code=401, detail="Keinem aktiven Verein zugeordnet")

        instance_club_id = _instance_club_id(db)
        club_ids = [int(club["id"]) for club in clubs]
        if _is_super_admin(db, user_id) or instance_club_id in club_ids:
            initial_club_id = instance_club_id
        else:
            initial_club_id = club_ids[0]

        requires_club_selection = (
            not _is_super_admin(db, user_id) and len(clubs) > 1
        )

        _clear_login_failures(rate_key)
        token = secrets.token_urlsafe(48)
        now_dt = datetime.now(timezone.utc)
        expires = (now_dt + timedelta(days=SESSION_LIFETIME_DAYS)).isoformat()
        db.execute(
            "DELETE FROM sessions WHERE expires_at <= ?",
            (now_dt.isoformat(),),
        )
        db.execute(
            """
            INSERT INTO sessions (
                token_hash, user_id, expires_at, created_at, active_club_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                _token_hash(token),
                user_id,
                expires,
                now_dt.isoformat(),
                initial_club_id,
            ),
        )
        db.commit()

        club_payload = [
            {
                **dict(club),
                "current": int(club["id"]) == initial_club_id,
            }
            for club in clubs
        ]

    return {
        "token": token,
        "expires_at": expires,
        "user": current_user(authorization=f"Bearer {token}"),
        "clubs": club_payload,
        "requires_club_selection": requires_club_selection,
    }


@app.post("/api/auth/logout", status_code=204)
def logout(
    authorization: str | None = Header(default=None),
) -> None:
    token = _extract_token(authorization)
    with connect() as db:
        db.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
        db.commit()


@app.get("/api/auth/me")
def me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return user


@app.get("/api/clubs/accessible")
def accessible_clubs(
    user: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    with connect() as db:
        rows = _accessible_club_rows(db, int(user["id"]))
    return [
        {
            **dict(row),
            "current": int(row["id"]) == int(user["current_club_id"]),
        }
        for row in rows
    ]


@app.post("/api/clubs")
def create_club(
    payload: ClubCreatePayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    if not bool(user.get("is_super_admin")):
        raise HTTPException(
            status_code=403,
            detail="Nur Super-Admins dürfen Vereine anlegen",
        )

    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        try:
            cursor = db.execute(
                """
                INSERT INTO clubs (
                    slug, name, short_name, subtitle, active,
                    primary_color, secondary_color,
                    description, website, email, phone, address,
                    city, country, app_title, welcome_text,
                    created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, 1,
                    ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?
                )
                """,
                (
                    payload.slug.strip().lower(),
                    payload.name.strip(),
                    payload.short_name.strip() or payload.name.strip(),
                    payload.subtitle.strip(),
                    payload.primary_color.upper(),
                    payload.secondary_color.upper(),
                    payload.description.strip(),
                    payload.website.strip(),
                    payload.email.strip(),
                    payload.phone.strip(),
                    payload.address.strip(),
                    payload.city.strip(),
                    payload.country.strip(),
                    payload.app_title.strip(),
                    payload.welcome_text.strip(),
                    now,
                    now,
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Vereins-Slug bereits vorhanden")

        club_id = int(cursor.lastrowid)
        _set_club_features(
            db,
            club_id,
            {
                key: default_enabled
                for key, (_, default_enabled) in CLUB_FEATURE_DEFAULTS.items()
            },
            {
                key: default_label
                for key, (default_label, _) in CLUB_FEATURE_DEFAULTS.items()
            },
        )
        db.commit()

        row = db.execute(
            """
            SELECT
                id, slug, name, short_name, subtitle, active,
                primary_color, secondary_color,
                description, website, email, phone, address,
                city, country, app_title, welcome_text,
                created_at, updated_at
            FROM clubs
            WHERE id = ?
            """,
            (club_id,),
        ).fetchone()
    return dict(row)


@app.get("/api/operator/billing/clubs")
def operator_billing_clubs(
    user: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    _require_super_admin(user)
    with connect() as db:
        rows = db.execute(
            """
            SELECT
                c.id, c.slug, c.name, c.short_name, c.active,
                c.billing_status, c.billing_email,
                c.billing_amount_rappen, c.billing_interval_months,
                c.billing_due_days, c.billing_next_invoice_date,
                c.billing_auto_suspend, c.billing_suspension_reason,
                COALESCE(SUM(
                    CASE WHEN i.status = 'open' THEN i.amount_rappen ELSE 0 END
                ), 0) AS open_amount_rappen,
                COALESCE(SUM(
                    CASE WHEN i.status = 'open' THEN 1 ELSE 0 END
                ), 0) AS open_invoice_count
            FROM clubs c
            LEFT JOIN club_invoices i ON i.club_id = c.id
            GROUP BY c.id
            ORDER BY c.name COLLATE NOCASE, c.id
            """
        ).fetchall()
    return [
        {
            **dict(row),
            "billing_auto_suspend": bool(row["billing_auto_suspend"]),
            "open_amount_chf": round(int(row["open_amount_rappen"]) / 100, 2),
        }
        for row in rows
    ]


@app.put("/api/operator/billing/clubs/{club_id}")
def operator_update_billing_settings(
    club_id: int,
    payload: ClubBillingSettingsPayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    _require_super_admin(user)
    next_invoice_date = payload.next_invoice_date.strip()
    if next_invoice_date:
        _parse_billing_date(next_invoice_date)
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        cursor = db.execute(
            """
            UPDATE clubs
            SET
                billing_email = ?,
                billing_amount_rappen = ?,
                billing_interval_months = ?,
                billing_due_days = ?,
                billing_next_invoice_date = ?,
                billing_auto_suspend = ?,
                updated_at = ?
            WHERE id = ? AND active = 1
            """,
            (
                payload.billing_email.strip(),
                payload.amount_rappen,
                payload.interval_months,
                payload.due_days,
                next_invoice_date,
                int(payload.auto_suspend),
                now,
                club_id,
            ),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Verein nicht gefunden")
        db.commit()
        row = db.execute(
            """
            SELECT
                id, slug, name, billing_status, billing_email,
                billing_amount_rappen, billing_interval_months,
                billing_due_days, billing_next_invoice_date,
                billing_auto_suspend, billing_suspension_reason
            FROM clubs
            WHERE id = ?
            """,
            (club_id,),
        ).fetchone()
    result = dict(row)
    result["billing_auto_suspend"] = bool(result["billing_auto_suspend"])
    result["billing_amount_chf"] = round(
        int(result["billing_amount_rappen"]) / 100,
        2,
    )
    return result


@app.get("/api/operator/billing/clubs/{club_id}/invoices")
def operator_club_invoices(
    club_id: int,
    user: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    _require_super_admin(user)
    with connect() as db:
        club = db.execute("SELECT id FROM clubs WHERE id = ?", (club_id,)).fetchone()
        if club is None:
            raise HTTPException(status_code=404, detail="Verein nicht gefunden")
        rows = db.execute(
            """
            SELECT *
            FROM club_invoices
            WHERE club_id = ?
            ORDER BY issue_date DESC, id DESC
            """,
            (club_id,),
        ).fetchall()
    return [_invoice_row(row) for row in rows]


@app.post("/api/operator/billing/run")
def operator_run_billing(
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, int]:
    _require_super_admin(user)
    return _run_billing_cycle()


@app.post("/api/operator/billing/clubs/{club_id}/suspend")
def operator_suspend_club(
    club_id: int,
    payload: ClubBillingSuspendPayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    _require_super_admin(user)
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        cursor = db.execute(
            """
            UPDATE clubs
            SET billing_status = 'suspended',
                billing_suspension_reason = ?,
                updated_at = ?
            WHERE id = ? AND active = 1
            """,
            (payload.reason.strip(), now, club_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Verein nicht gefunden")
        db.commit()
    return {"club_id": club_id, "billing_status": "suspended"}


@app.post("/api/operator/billing/clubs/{club_id}/reactivate")
def operator_reactivate_club(
    club_id: int,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    _require_super_admin(user)
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        cursor = db.execute(
            """
            UPDATE clubs
            SET billing_status = 'active',
                billing_suspension_reason = '',
                updated_at = ?
            WHERE id = ? AND active = 1
            """,
            (now, club_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Verein nicht gefunden")
        db.commit()
    return {"club_id": club_id, "billing_status": "active"}


@app.post("/api/operator/billing/invoices/{invoice_id}/paid")
def operator_mark_invoice_paid(
    invoice_id: int,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    _require_super_admin(user)
    now_dt = datetime.now(timezone.utc)
    today = now_dt.date().isoformat()
    with connect() as db:
        invoice = db.execute(
            "SELECT * FROM club_invoices WHERE id = ?",
            (invoice_id,),
        ).fetchone()
        if invoice is None:
            raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
        club_id = int(invoice["club_id"])
        db.execute(
            """
            UPDATE club_invoices
            SET status = 'paid', paid_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (now_dt.isoformat(), now_dt.isoformat(), invoice_id),
        )
        overdue = db.execute(
            """
            SELECT 1
            FROM club_invoices
            WHERE club_id = ?
              AND status = 'open'
              AND due_date < ?
            LIMIT 1
            """,
            (club_id, today),
        ).fetchone()
        if overdue is None:
            db.execute(
                """
                UPDATE clubs
                SET billing_status = 'active',
                    billing_suspension_reason = '',
                    updated_at = ?
                WHERE id = ?
                """,
                (now_dt.isoformat(), club_id),
            )
        db.commit()
        row = db.execute(
            "SELECT * FROM club_invoices WHERE id = ?",
            (invoice_id,),
        ).fetchone()
    return _invoice_row(row)


@app.post("/api/auth/club")
def switch_active_club(
    payload: ClubSwitchPayload,
    authorization: str | None = Header(default=None),
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    token = _extract_token(authorization)
    with connect() as db:
        club = db.execute(
            """
            SELECT id, slug, name, active, billing_status, billing_suspension_reason
            FROM clubs
            WHERE id = ? AND active = 1
            """,
            (payload.club_id,),
        ).fetchone()
        if club is None:
            raise HTTPException(status_code=404, detail="Verein nicht gefunden")
        role = _user_club_access(db, int(user["id"]), int(payload.club_id))
        if role is None:
            raise HTTPException(status_code=403, detail="Kein Zugriff auf diesen Verein")
        if str(club["billing_status"] or "active") != "active" and role != "super_admin":
            reason = str(club["billing_suspension_reason"] or "Ausstehende Zahlung")
            raise HTTPException(status_code=403, detail=f"Verein gesperrt: {reason}")
        cursor = db.execute(
            """
            UPDATE sessions
            SET active_club_id = ?
            WHERE token_hash = ? AND user_id = ?
            """,
            (payload.club_id, _token_hash(token), user["id"]),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=401, detail="Sitzung nicht gefunden")
        db.commit()
    return {
        "club_id": int(club["id"]),
        "slug": str(club["slug"]),
        "name": str(club["name"]),
        "club_role": role,
    }


@app.get("/api/roles")
def get_roles(
    _: dict[str, Any] = Depends(require("can_manage_users")),
) -> list[dict[str, Any]]:
    return [
        {
            "key": key,
            "label": definition["label"],
            "permissions": definition["permissions"],
        }
        for key, definition in ROLE_DEFINITIONS.items()
    ]


@app.get("/api/users")
def get_users(
    _: dict[str, Any] = Depends(require("can_manage_users")),
) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute(
            """
            SELECT
                u.*,
                m.name AS member_name,
                uc.role AS club_role,
                uc.club_id AS current_club_id
            FROM users u
            JOIN user_clubs uc
              ON uc.user_id = u.id
             AND uc.club_id = ?
             AND uc.active = 1
            LEFT JOIN members m
              ON m.id = u.member_id
             AND m.club_id = uc.club_id
            ORDER BY u.username COLLATE NOCASE
            """,
            (_active_club_id(db),),
        ).fetchall()
    return [_serialize_user(row) for row in rows]


@app.post("/api/users")
def post_user(
    payload: UserPayload,
    _: dict[str, Any] = Depends(require("can_manage_users")),
) -> dict[str, Any]:
    if len(payload.password) < 6:
        raise HTTPException(status_code=422, detail="Passwort muss mindestens 6 Zeichen haben")
    password_hash, salt = _hash_password(payload.password)
    role_key = _normalize_role_key(payload.role_key)
    overrides = _normalize_permission_overrides(payload.permission_overrides)
    if not overrides and role_key == "member":
        legacy_permissions = {
            key: bool(getattr(payload, key))
            for key in PERMISSION_FIELDS
        }
        if any(legacy_permissions.values()):
            overrides = legacy_permissions
    effective = _effective_permissions(role_key, overrides)
    now = datetime.now(timezone.utc).isoformat()

    with connect() as db:
        try:
            cursor = db.execute(
                f"""
                INSERT INTO users (
                    member_id, username, password_hash, password_salt, active,
                    {", ".join(PERMISSION_FIELDS)}, role_key, permission_overrides, created_at
                ) VALUES (?, ?, ?, ?, ?, {", ".join("?" for _ in PERMISSION_FIELDS)}, ?, ?, ?)
                """,
                [
                    payload.member_id,
                    payload.username.strip(),
                    password_hash,
                    salt,
                    int(payload.active),
                    *[int(effective[key]) for key in PERMISSION_FIELDS],
                    role_key,
                    json.dumps(overrides, ensure_ascii=False, sort_keys=True),
                    now,
                ],
            )
            user_id = cursor.lastrowid
            club_role = "club_admin" if effective["can_manage_users"] else "member"
            db.execute(
                """
                INSERT INTO user_clubs (
                    user_id, club_id, role, active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    _active_club_id(db),
                    club_role,
                    int(payload.active),
                    now,
                    now,
                ),
            )
            db.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Benutzername bereits vorhanden")
    return _user_profile(user_id)


@app.put("/api/users/{user_id}")
def put_user(
    user_id: int,
    payload: UserPayload,
    actor: dict[str, Any] = Depends(require("can_manage_users")),
) -> dict[str, Any]:
    role_key = _normalize_role_key(payload.role_key)
    overrides = _normalize_permission_overrides(payload.permission_overrides)
    if not overrides and role_key == "member":
        legacy_permissions = {
            key: bool(getattr(payload, key))
            for key in PERMISSION_FIELDS
        }
        if any(legacy_permissions.values()):
            overrides = legacy_permissions
    effective = _effective_permissions(role_key, overrides)

    if user_id == actor["id"] and not effective["can_manage_users"]:
        raise HTTPException(
            status_code=400,
            detail="Eigenes Recht zur Benutzerverwaltung kann nicht entfernt werden",
        )

    assignments = [
        "member_id = ?",
        "username = ?",
        "active = ?",
        "role_key = ?",
        "permission_overrides = ?",
    ]
    values: list[Any] = [
        payload.member_id,
        payload.username.strip(),
        int(payload.active),
        role_key,
        json.dumps(overrides, ensure_ascii=False, sort_keys=True),
    ]
    for key in PERMISSION_FIELDS:
        assignments.append(f"{key} = ?")
        values.append(int(effective[key]))

    password_changed = bool(payload.password)
    if payload.password:
        if len(payload.password) < 6:
            raise HTTPException(status_code=422, detail="Passwort muss mindestens 6 Zeichen haben")
        password_hash, salt = _hash_password(payload.password)
        assignments.extend(["password_hash = ?", "password_salt = ?"])
        values.extend([password_hash, salt])

    values.append(user_id)
    with connect() as db:
        club_id = _active_club_id(db)
        target = db.execute(
            """
            SELECT 1
            FROM user_clubs
            WHERE user_id = ? AND club_id = ? AND active = 1
            """,
            (user_id, club_id),
        ).fetchone()
        if target is None:
            raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
        try:
            cursor = db.execute(
                f"UPDATE users SET {', '.join(assignments)} WHERE id = ?",
                values,
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
            if password_changed:
                db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            db.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Benutzername bereits vorhanden")
    return _user_profile(user_id)


@app.delete("/api/users/{user_id}/sessions", status_code=204)
def revoke_user_sessions(
    user_id: int,
    _: dict[str, Any] = Depends(require("can_manage_users")),
) -> None:
    with connect() as db:
        club_id = _active_club_id(db)
        user = db.execute(
            """
            SELECT u.id
            FROM users u
            JOIN user_clubs uc ON uc.user_id = u.id
            WHERE u.id = ? AND uc.club_id = ? AND uc.active = 1
            """,
            (user_id, club_id),
        ).fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
        db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        db.commit()


@app.delete("/api/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    actor: dict[str, Any] = Depends(require("can_manage_users")),
) -> None:
    if user_id == actor["id"]:
        raise HTTPException(status_code=400, detail="Eigenes Konto kann nicht gelöscht werden")
    with connect() as db:
        club_id = _active_club_id(db)
        membership = db.execute(
            """
            SELECT role
            FROM user_clubs
            WHERE user_id = ? AND club_id = ? AND active = 1
            """,
            (user_id, club_id),
        ).fetchone()
        if membership is None:
            raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")

        db.execute(
            "DELETE FROM user_clubs WHERE user_id = ? AND club_id = ?",
            (user_id, club_id),
        )
        remaining = db.execute(
            "SELECT 1 FROM user_clubs WHERE user_id = ? LIMIT 1",
            (user_id,),
        ).fetchone()
        if remaining is None:
            db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()


@app.post("/api/gallery/snapshots")
async def post_gallery_snapshot(
    image: UploadFile = File(...),
    expires_days: int = 14,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    if not (user.get("can_gallery_upload", False) or user.get("can_photos", False)):
        raise HTTPException(status_code=403, detail="Keine Berechtigung für Galerie-Snapshots")
    if expires_days not in {7, 14, 30}:
        raise HTTPException(status_code=422, detail="Ablaufzeit muss 7, 14 oder 30 Tage sein")
    raw_data = await image.read()
    mime = image.content_type or ""
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        if raw_data.startswith(b"\xff\xd8\xff"):
            mime = "image/jpeg"
        elif raw_data.startswith(b"\x89PNG\r\n\x1a\n"):
            mime = "image/png"
        elif len(raw_data) >= 12 and raw_data[:4] == b"RIFF" and raw_data[8:12] == b"WEBP":
            mime = "image/webp"
        else:
            raise HTTPException(status_code=415, detail="Unsupported image type")
    data, mime = _optimize_image(raw_data, mime)

    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=expires_days)
    with connect() as db:
        _cleanup_expired_snapshots(db)
        cursor = db.execute(
            """
            INSERT INTO gallery_snapshots (
                user_id, image_data, image_mime, created_at, expires_at, club_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                data,
                mime,
                now.isoformat(),
                expires.isoformat(),
                _active_club_id(db),
            ),
        )
        db.commit()
        row = db.execute(
            """
            SELECT gs.*, u.username, m.name AS member_name
            FROM gallery_snapshots gs
            JOIN users u ON u.id = gs.user_id
            LEFT JOIN members m
              ON m.id = u.member_id
             AND m.club_id = gs.club_id
            WHERE gs.id = ? AND gs.club_id = ?
            """,
            (cursor.lastrowid, _active_club_id(db)),
        ).fetchone()
    return _serialize_snapshot(row, user)


@app.get("/api/gallery/snapshots/{snapshot_id}/image")
def get_gallery_snapshot_image(
    snapshot_id: int,
    _: dict[str, Any] = Depends(current_user),
) -> Response:
    with connect() as db:
        _cleanup_expired_snapshots(db)
        row = db.execute(
            """
            SELECT image_data, image_mime
            FROM gallery_snapshots
            WHERE id = ? AND club_id = ? AND expires_at > ?
            """,
            (
                snapshot_id,
                _active_club_id(db),
                datetime.now(timezone.utc).isoformat(),
            ),
        ).fetchone()
        db.commit()
    if row is None:
        raise HTTPException(status_code=404, detail="Snapshot nicht gefunden oder abgelaufen")
    return Response(
        content=row["image_data"],
        media_type=row["image_mime"] or "image/jpeg",
        headers={"Cache-Control": "private, max-age=300"},
    )


@app.delete("/api/gallery/snapshots/{snapshot_id}", status_code=204)
def delete_gallery_snapshot(
    snapshot_id: int,
    user: dict[str, Any] = Depends(current_user),
) -> None:
    with connect() as db:
        club_id = _active_club_id(db)
        row = db.execute(
            """
            SELECT user_id
            FROM gallery_snapshots
            WHERE id = ? AND club_id = ?
            """,
            (snapshot_id, club_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Snapshot nicht gefunden")
        if row["user_id"] != user["id"] and not user.get("can_photos", False):
            raise HTTPException(status_code=403, detail="Keine Berechtigung")
        db.execute(
            "DELETE FROM gallery_snapshots WHERE id = ? AND club_id = ?",
            (snapshot_id, club_id),
        )
        db.commit()


def _serialize_push_notification(
    row: sqlite3.Row | dict[str, Any],
) -> dict[str, Any]:
    item = dict(row)
    item["delivered_count"] = int(item.get("delivered_count", 0) or 0)
    item["failed_count"] = int(item.get("failed_count", 0) or 0)
    item["status"] = (
        "sent"
        if item.get("sent_at")
        else ("error" if item.get("last_error") else "queued")
    )
    return item


@app.get("/api/push/admin")
def get_push_admin(
    _: dict[str, Any] = Depends(require("can_manage_users")),
) -> dict[str, Any]:
    with connect() as db:
        club_id = _active_club_id(db)
        registered_devices_total = int(
            db.execute(
                "SELECT COUNT(*) FROM push_tokens WHERE enabled = 1 AND club_id = ?",
                (club_id,),
            ).fetchone()[0]
        )
        queued_notifications = int(
            db.execute(
                """
                SELECT COUNT(*)
                FROM push_notifications
                WHERE sent_at IS NULL AND club_id = ?
                """,
                (club_id,),
            ).fetchone()[0]
        )
        rows = db.execute(
            """
            SELECT
                pn.*,
                (
                    SELECT COUNT(*)
                    FROM push_deliveries pd
                    WHERE pd.notification_id = pn.id
                      AND pd.club_id = pn.club_id
                      AND pd.sent_at IS NOT NULL
                ) AS delivered_count,
                (
                    SELECT COUNT(*)
                    FROM push_deliveries pd
                    WHERE pd.notification_id = pn.id
                      AND pd.club_id = pn.club_id
                      AND pd.sent_at IS NULL
                      AND pd.last_error <> ''
                ) AS failed_count
            FROM push_notifications pn
            WHERE pn.club_id = ?
            ORDER BY pn.id DESC
            LIMIT 50
            """,
            (club_id,),
        ).fetchall()
        last_delivery_error = db.execute(
            """
            SELECT pd.last_error
            FROM push_deliveries pd
            JOIN push_notifications pn ON pn.id = pd.notification_id
            WHERE pd.club_id = ?
              AND pn.club_id = ?
              AND pd.last_error IS NOT NULL
              AND pd.last_error <> ''
            ORDER BY pd.rowid DESC
            LIMIT 1
            """,
            (club_id, club_id),
        ).fetchone()

    return {
        "registered_devices_total": registered_devices_total,
        "queued_notifications": queued_notifications,
        "last_delivery_error": (
            str(last_delivery_error["last_error"])[:500]
            if last_delivery_error is not None
            else ""
        ),
        "notifications": [_serialize_push_notification(row) for row in rows],
        **_firebase_diagnostic(),
    }


@app.post("/api/push/admin/send")
def send_manual_push(
    payload: ManualPushPayload,
    _: dict[str, Any] = Depends(require("can_manage_users")),
) -> dict[str, Any]:
    route = payload.route.strip()
    allowed_routes = {"", "/news", "/events", "/gallery", "/more"}
    if route not in allowed_routes:
        raise HTTPException(status_code=422, detail="Unbekanntes Push-Ziel")

    with connect() as db:
        _queue_push_notification(
            db,
            kind="manual",
            title=payload.title.strip(),
            body=payload.body.strip(),
            route=route,
        )
        notification_id = int(db.execute("SELECT last_insert_rowid()").fetchone()[0])
        db.commit()
        row = db.execute(
            """
            SELECT
                pn.*,
                0 AS delivered_count,
                0 AS failed_count
            FROM push_notifications pn
            WHERE pn.id = ? AND pn.club_id = ?
            """,
            (notification_id, _active_club_id(db)),
        ).fetchone()
    return _serialize_push_notification(row)


@app.post("/api/push/register")
def register_push_token(
    payload: PushTokenPayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    platform = payload.platform.lower().strip()
    if platform not in {"android", "ios"}:
        raise HTTPException(status_code=422, detail="Unbekannte Plattform")
    with connect() as db:
        db.execute(
            """
            INSERT INTO push_tokens (
                user_id, token, platform, enabled, created_at, updated_at, club_id
            ) VALUES (?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT(token) DO UPDATE SET
                user_id = excluded.user_id,
                platform = excluded.platform,
                enabled = 1,
                updated_at = excluded.updated_at,
                club_id = excluded.club_id
            """,
            (
                user["id"],
                payload.token,
                platform,
                now,
                now,
                _active_club_id(db),
            ),
        )
        db.commit()
    return {"registered": True}


@app.delete("/api/push/register", status_code=204)
def unregister_push_token(
    payload: PushTokenDeletePayload,
    user: dict[str, Any] = Depends(current_user),
) -> None:
    with connect() as db:
        db.execute(
            """
            DELETE FROM push_tokens
            WHERE token = ? AND user_id = ? AND club_id = ?
            """,
            (payload.token, user["id"], _active_club_id(db)),
        )
        db.commit()


@app.get("/api/push/status")
def push_status(
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    with connect() as db:
        club_id = _active_club_id(db)
        count = db.execute(
            """
            SELECT COUNT(*)
            FROM push_tokens
            WHERE user_id = ? AND enabled = 1 AND club_id = ?
            """,
            (user["id"], club_id),
        ).fetchone()[0]
        total_devices = db.execute(
            "SELECT COUNT(*) FROM push_tokens WHERE enabled = 1 AND club_id = ?",
            (club_id,),
        ).fetchone()[0]
        queued = db.execute(
            """
            SELECT COUNT(*)
            FROM push_notifications
            WHERE sent_at IS NULL AND club_id = ?
            """,
            (club_id,),
        ).fetchone()[0]
        last_delivery_error = db.execute(
            """
            SELECT pd.last_error
            FROM push_deliveries pd
            JOIN push_notifications pn ON pn.id = pd.notification_id
            WHERE pd.club_id = ?
              AND pn.club_id = ?
              AND pd.last_error IS NOT NULL
              AND pd.last_error <> ''
            ORDER BY pd.rowid DESC
            LIMIT 1
            """,
            (club_id, club_id),
        ).fetchone()
    diagnostic = _firebase_diagnostic()
    return {
        "registered_devices": count,
        "registered_devices_total": total_devices,
        "queued_notifications": queued,
        "last_delivery_error": (
            last_delivery_error["last_error"][:500]
            if last_delivery_error is not None
            else ""
        ),
        **diagnostic,
    }


def _normalize_poll_options(
    values: list[str],
    allow_suggestions: bool = False,
) -> list[str]:
    options = [str(value).strip() for value in values if str(value).strip()]
    if len(options) < 2 and not allow_suggestions:
        raise HTTPException(
            status_code=422,
            detail="Eine Umfrage benötigt mindestens zwei Antwortmöglichkeiten",
        )
    if len(options) > 21:
        raise HTTPException(
            status_code=422,
            detail="Maximal 21 Antwortoptionen möglich",
        )
    normalized = [value.casefold() for value in options]
    if len(set(normalized)) != len(normalized):
        raise HTTPException(
            status_code=422,
            detail="Antwortmöglichkeiten dürfen nicht doppelt vorkommen",
        )
    return options


def _create_poll(
    payload: PollPayload,
    user: dict[str, Any],
) -> dict[str, Any]:
    if not user.get("can_polls", False):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")
    options = _normalize_poll_options(
        payload.options,
        allow_suggestions=payload.allow_suggestions,
    )
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        max_order = db.execute(
            """
            SELECT COALESCE(MAX(sort_order), 0)
            FROM content_items
            WHERE section = 'polls' AND club_id = ?
            """,
            (_active_club_id(db),),
        ).fetchone()[0]
        cursor = db.execute(
            """
            INSERT INTO content_items (
                section, title, text, link_url, poll_options,
                poll_allow_suggestions, sort_order, created_at, club_id
            ) VALUES ('polls', ?, ?, '', ?, ?, ?, ?, ?)
            """,
            (
                payload.title,
                payload.text,
                json.dumps(options, ensure_ascii=False),
                int(payload.allow_suggestions),
                max_order + 1,
                now,
                _active_club_id(db),
            ),
        )
        rule = CONTENT_PUSH_RULES.get("polls")
        if rule is not None:
            kind, prefix, route = rule
            _queue_push_notification(
                db,
                kind=kind,
                title=f"{prefix}: {payload.title}",
                body=payload.text,
                route=route,
            )
        db.commit()
        row = db.execute(
            "SELECT * FROM content_items WHERE id = ? AND club_id = ?",
            (cursor.lastrowid, _active_club_id(db)),
        ).fetchone()
    return _serialize_content(row, user["id"])


def _update_poll(
    poll_id: int,
    payload: PollPayload,
    user: dict[str, Any],
) -> dict[str, Any]:
    if not user.get("can_polls", False):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")
    options = _normalize_poll_options(
        payload.options,
        allow_suggestions=payload.allow_suggestions,
    )
    with connect() as db:
        existing = _require_active_club_row(db, "content_items", poll_id)
        if existing["section"] != "polls":
            raise HTTPException(status_code=404, detail="Umfrage nicht gefunden")
        db.execute(
            """
            UPDATE content_items
            SET title = ?, text = ?, link_url = '',
                poll_options = ?, poll_allow_suggestions = ?
            WHERE id = ? AND section = 'polls' AND club_id = ?
            """,
            (
                payload.title,
                payload.text,
                json.dumps(options, ensure_ascii=False),
                int(payload.allow_suggestions),
                poll_id,
                _active_club_id(db),
            ),
        )
        db.commit()
        row = _require_active_club_row(db, "content_items", poll_id)
    return _serialize_content(row, user["id"])


def _delete_poll(
    poll_id: int,
    user: dict[str, Any],
) -> None:
    if not user.get("can_polls", False):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")
    with connect() as db:
        existing = _require_active_club_row(db, "content_items", poll_id)
        if existing["section"] != "polls":
            raise HTTPException(status_code=404, detail="Umfrage nicht gefunden")
        club_id = _active_club_id(db)
        db.execute(
            "DELETE FROM poll_votes WHERE poll_id = ? AND club_id = ?",
            (poll_id, club_id),
        )
        db.execute(
            "DELETE FROM poll_suggestions WHERE poll_id = ? AND club_id = ?",
            (poll_id, club_id),
        )
        db.execute(
            "DELETE FROM content_images WHERE content_id = ? AND club_id = ?",
            (poll_id, club_id),
        )
        db.execute(
            """
            DELETE FROM content_items
            WHERE id = ? AND section = 'polls' AND club_id = ?
            """,
            (poll_id, club_id),
        )
        db.commit()


@app.get("/api/polls")
def get_polls(
    user: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    with connect() as db:
        _require_club_feature(db, "polls")
        rows = db.execute(
            """
            SELECT *
            FROM content_items
            WHERE section = 'polls' AND club_id = ?
            ORDER BY sort_order ASC, id ASC
            """,
            (_active_club_id(db),),
        ).fetchall()
    return [_serialize_content(row, user["id"]) for row in rows]


@app.post("/api/polls")
def post_poll(
    payload: PollPayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    return _create_poll(payload, user)


@app.put("/api/polls/{poll_id}")
def put_poll(
    poll_id: int,
    payload: PollPayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    return _update_poll(poll_id, payload, user)


@app.delete("/api/polls/{poll_id}", status_code=204)
def delete_poll(
    poll_id: int,
    user: dict[str, Any] = Depends(current_user),
) -> None:
    _delete_poll(poll_id, user)


@app.get("/api/content")
def get_content(
    section: str | None = None,
    user: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM content_items WHERE club_id = ?"
    if section:
        _content_permission(section)
        sql += " AND section = ?"
    sql += " ORDER BY sort_order ASC, id ASC"

    with connect() as db:
        _cleanup_expired_snapshots(db)
        if section:
            _require_section_feature(db, section)
        values: list[Any] = [_active_club_id(db)]
        if section:
            values.append(section)
        rows = db.execute(sql, values).fetchall()
        if not section:
            rows = [
                row for row in rows
                if SECTION_FEATURES.get(str(row["section"])) is None
                or _club_feature_enabled(
                    db,
                    SECTION_FEATURES[str(row["section"])],
                )
            ]
        snapshots: list[sqlite3.Row] = []
        if section is None or section == "gallery":
            snapshots = db.execute(
                """
                SELECT gs.*, u.username, m.name AS member_name
                FROM gallery_snapshots gs
                JOIN users u ON u.id = gs.user_id
                LEFT JOIN members m ON m.id = u.member_id
                WHERE gs.expires_at > ? AND gs.club_id = ?
                ORDER BY gs.created_at DESC, gs.id DESC
                """,
                (datetime.now(timezone.utc).isoformat(), _active_club_id(db)),
            ).fetchall()
        db.commit()

    items = [_serialize_content(row, user["id"]) for row in rows]
    items.extend(_serialize_snapshot(row, user) for row in snapshots)
    return items


@app.put("/api/content/order")
def reorder_content_items(
    payload: ContentOrderPayload,
    user: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    if not payload.item_ids:
        return []

    with connect() as db:
        club_id = _active_club_id(db)
        placeholders = ",".join("?" for _ in payload.item_ids)
        rows = db.execute(
            f"""
            SELECT id, section
            FROM content_items
            WHERE id IN ({placeholders}) AND club_id = ?
            """,
            [*payload.item_ids, club_id],
        ).fetchall()

        if len(rows) != len(set(payload.item_ids)):
            raise HTTPException(status_code=422, detail="Eintragsreihenfolge ist ungültig")

        sections = {row["section"] for row in rows}
        if len(sections) != 1:
            raise HTTPException(
                status_code=422,
                detail="Reihenfolge kann nur innerhalb eines Bereichs geändert werden",
            )

        section = next(iter(sections))
        _require_content_permission(section, user)
        _require_section_feature(db, section)

        current_rows = db.execute(
            """
            SELECT id
            FROM content_items
            WHERE section = ? AND club_id = ?
            ORDER BY sort_order ASC, id ASC
            """,
            (section, club_id),
        ).fetchall()
        current_ids = [row["id"] for row in current_rows]
        if set(current_ids) != set(payload.item_ids):
            raise HTTPException(
                status_code=422,
                detail="Eintragsreihenfolge ist unvollständig",
            )

        for position, item_id in enumerate(payload.item_ids, start=1):
            db.execute(
                """
                UPDATE content_items
                SET sort_order = ?
                WHERE id = ? AND section = ? AND club_id = ?
                """,
                (position, item_id, section, club_id),
            )
        db.commit()

        ordered = db.execute(
            """
            SELECT *
            FROM content_items
            WHERE section = ? AND club_id = ?
            ORDER BY sort_order ASC, id ASC
            """,
            (section, club_id),
        ).fetchall()
    return [_serialize_content(row, user["id"]) for row in ordered]

@app.post("/api/content")
def post_content(
    payload: ContentPayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    _require_content_permission(payload.section, user)
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        _require_section_feature(db, payload.section)
        max_order = db.execute(
            """
            SELECT COALESCE(MAX(sort_order), 0)
            FROM content_items
            WHERE section = ? AND club_id = ?
            """,
            (payload.section, _active_club_id(db)),
        ).fetchone()[0]
        cursor = db.execute(
            """
            INSERT INTO content_items (
                section, title, text, link_url, poll_options,
                poll_allow_suggestions, sort_order, created_at, club_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.section,
                payload.title,
                payload.text,
                payload.link_url,
                json.dumps(
                    [value.strip() for value in payload.poll_options if value.strip()],
                    ensure_ascii=False,
                ) if payload.section == "polls" else "[]",
                int(payload.poll_allow_suggestions)
                if payload.section == "polls" else 0,
                max_order + 1,
                now,
                _active_club_id(db),
            ),
        )
        rule = CONTENT_PUSH_RULES.get(payload.section)
        if rule is not None:
            kind, prefix, route = rule
            _queue_push_notification(
                db,
                kind=kind,
                title=f"{prefix}: {payload.title}",
                body=payload.text,
                route=route,
            )
        db.commit()
        row = _require_active_club_row(db, "content_items", cursor.lastrowid)
    return _serialize_content(row, user["id"])


@app.put("/api/content/{row_id}")
def put_content(
    row_id: int,
    payload: ContentPayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    _require_content_permission(payload.section, user)
    with connect() as db:
        current = _require_active_club_row(db, "content_items", row_id)
        _require_content_permission(current["section"], user)
        db.execute(
            """
            UPDATE content_items
            SET section = ?, title = ?, text = ?, link_url = ?,
                poll_options = ?, poll_allow_suggestions = ?
            WHERE id = ? AND club_id = ?
            """,
            (
                payload.section,
                payload.title,
                payload.text,
                payload.link_url,
                json.dumps(
                    [value.strip() for value in payload.poll_options if value.strip()],
                    ensure_ascii=False,
                ) if payload.section == "polls" else "[]",
                int(payload.poll_allow_suggestions)
                if payload.section == "polls" else 0,
                row_id,
                _active_club_id(db),
            ),
        )
        db.commit()
        row = _require_active_club_row(db, "content_items", row_id)
    return _serialize_content(row)


@app.delete("/api/content/{row_id}", status_code=204)
def delete_content(
    row_id: int,
    user: dict[str, Any] = Depends(current_user),
) -> None:
    with connect() as db:
        row = _require_active_club_row(db, "content_items", row_id)
        _require_content_permission(row["section"], user)
        club_id = _active_club_id(db)
        db.execute("DELETE FROM content_images WHERE content_id = ? AND club_id = ?", (row_id, club_id))
        db.execute("DELETE FROM poll_votes WHERE poll_id = ? AND club_id = ?", (row_id, club_id))
        db.execute("DELETE FROM poll_suggestions WHERE poll_id = ? AND club_id = ?", (row_id, club_id))
        db.execute("DELETE FROM content_items WHERE id = ? AND club_id = ?", (row_id, club_id))
        db.commit()


@app.post("/api/content/{row_id}/document")
async def upload_content_document(
    row_id: int,
    document: UploadFile = File(...),
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    with connect() as db:
        existing = _require_active_club_row(db, "content_items", row_id)
        _require_content_permission(existing["section"], user)
        if existing["section"] != "documents":
            raise HTTPException(status_code=422, detail="PDF nur bei Dokumenten erlaubt")

        data = await document.read()
        if not data:
            raise HTTPException(status_code=400, detail="Leere PDF-Datei")
        if len(data) > 20 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="PDF ist grösser als 20 MB")
        mime = (document.content_type or "").lower()
        filename = (document.filename or "dokument.pdf").strip()
        is_pdf = mime == "application/pdf" or filename.lower().endswith(".pdf")
        if not is_pdf or not data.startswith(b"%PDF"):
            raise HTTPException(status_code=415, detail="Nur PDF-Dateien sind erlaubt")

        db.execute(
            """
            UPDATE content_items
            SET document_data = ?, document_mime = 'application/pdf', document_name = ?
            WHERE id = ? AND club_id = ?
            """,
            (data, filename, row_id, _active_club_id(db)),
        )
        db.commit()
        row = _require_active_club_row(db, "content_items", row_id)
    return _serialize_content(row, user["id"])


@app.get("/api/content/{row_id}/document")
def get_content_document(
    row_id: int,
    _: dict[str, Any] = Depends(current_user),
) -> Response:
    with connect() as db:
        row = db.execute(
            """
            SELECT document_data, document_mime, document_name
            FROM content_items
            WHERE id = ? AND club_id = ?
            """,
            (row_id, _active_club_id(db)),
        ).fetchone()
    if row is None or row["document_data"] is None:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
    filename = str(row["document_name"] or "dokument.pdf").replace('"', "")
    return Response(
        content=row["document_data"],
        media_type=row["document_mime"] or "application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, max-age=300",
        },
    )


@app.delete("/api/content/{row_id}/document", status_code=204)
def delete_content_document(
    row_id: int,
    user: dict[str, Any] = Depends(current_user),
) -> None:
    with connect() as db:
        existing = _require_active_club_row(db, "content_items", row_id)
        _require_content_permission(existing["section"], user)
        db.execute(
            """
            UPDATE content_items
            SET document_data = NULL, document_mime = '', document_name = ''
            WHERE id = ? AND club_id = ?
            """,
            (row_id, _active_club_id(db)),
        )
        db.commit()


@app.post("/api/polls/{poll_id}/vote")
def vote_poll(
    poll_id: int,
    payload: PollVotePayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    with connect() as db:
        poll = _require_active_club_row(db, "content_items", poll_id)
        if poll["section"] != "polls":
            raise HTTPException(status_code=404, detail="Umfrage nicht gefunden")
        try:
            options = json.loads(poll["poll_options"] or "[]")
        except Exception:
            options = []
        if payload.option_index >= len(options):
            raise HTTPException(status_code=422, detail="Antwortoption ungültig")
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            """
            INSERT INTO poll_votes (
                poll_id, user_id, option_index, created_at, club_id
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(poll_id, user_id) DO UPDATE SET
                option_index = excluded.option_index,
                created_at = excluded.created_at
            """,
            (
                poll_id,
                user["id"],
                payload.option_index,
                now,
                _active_club_id(db),
            ),
        )
        db.commit()
        row = _require_active_club_row(db, "content_items", poll_id)
    return _serialize_content(row, user["id"])


@app.post("/api/polls/{poll_id}/suggest-and-vote")
def suggest_and_vote_poll(
    poll_id: int,
    payload: PollSuggestionPayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    suggestion = payload.text.strip()
    if not suggestion:
        raise HTTPException(status_code=422, detail="Vorschlag darf nicht leer sein")

    with connect() as db:
        poll = _require_active_club_row(db, "content_items", poll_id)
        if poll["section"] != "polls":
            raise HTTPException(status_code=404, detail="Umfrage nicht gefunden")
        if not bool(poll["poll_allow_suggestions"]):
            raise HTTPException(
                status_code=403,
                detail="Eigene Vorschläge sind bei dieser Umfrage deaktiviert",
            )

        try:
            options = json.loads(poll["poll_options"] or "[]")
        except Exception:
            options = []
        if not isinstance(options, list):
            options = []
        options = [str(value).strip() for value in options if str(value).strip()]

        owned = db.execute(
            """
            SELECT option_index
            FROM poll_suggestions
            WHERE poll_id = ? AND user_id = ? AND club_id = ?
            """,
            (poll_id, user["id"], _active_club_id(db)),
        ).fetchone()

        if owned is not None:
            option_index = int(owned["option_index"])
            if not (0 <= option_index < len(options)):
                db.execute(
                    """
                    DELETE FROM poll_suggestions
                    WHERE poll_id = ? AND user_id = ? AND club_id = ?
                    """,
                    (poll_id, user["id"], _active_club_id(db)),
                )
                owned = None
            else:
                duplicate_index = next(
                    (
                        index
                        for index, value in enumerate(options)
                        if index != option_index
                        and value.casefold() == suggestion.casefold()
                    ),
                    None,
                )
                if duplicate_index is not None:
                    raise HTTPException(
                        status_code=409,
                        detail="Dieser Vorschlag ist bereits vorhanden",
                    )
                options[option_index] = suggestion
                db.execute(
                    """
                    UPDATE content_items
                    SET poll_options = ?
                    WHERE id = ? AND club_id = ?
                    """,
                    (
                        json.dumps(options, ensure_ascii=False),
                        poll_id,
                        _active_club_id(db),
                    ),
                )
                now = datetime.now(timezone.utc).isoformat()
                db.execute(
                    """
                    UPDATE poll_suggestions
                    SET suggestion_text = ?, updated_at = ?
                    WHERE poll_id = ? AND user_id = ? AND club_id = ?
                    """,
                    (
                        suggestion,
                        now,
                        poll_id,
                        user["id"],
                        _active_club_id(db),
                    ),
                )

        if owned is None:
            existing_index = next(
                (
                    index
                    for index, value in enumerate(options)
                    if value.casefold() == suggestion.casefold()
                ),
                None,
            )
            if existing_index is not None:
                option_index = existing_index
            else:
                if len(options) >= 21:
                    raise HTTPException(
                        status_code=422,
                        detail="Maximal 21 Antwortoptionen möglich",
                    )
                options.append(suggestion)
                option_index = len(options) - 1
                now = datetime.now(timezone.utc).isoformat()
                db.execute(
                    """
                    UPDATE content_items
                    SET poll_options = ?
                    WHERE id = ? AND club_id = ?
                    """,
                    (
                        json.dumps(options, ensure_ascii=False),
                        poll_id,
                        _active_club_id(db),
                    ),
                )
                db.execute(
                    """
                    INSERT INTO poll_suggestions (
                        poll_id, user_id, option_index, suggestion_text,
                        created_at, updated_at, club_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        poll_id,
                        user["id"],
                        option_index,
                        suggestion,
                        now,
                        now,
                        _active_club_id(db),
                    ),
                )

        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            """
            INSERT INTO poll_votes (
                poll_id, user_id, option_index, created_at, club_id
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(poll_id, user_id) DO UPDATE SET
                option_index = excluded.option_index,
                created_at = excluded.created_at
            """,
            (
                poll_id,
                user["id"],
                option_index,
                now,
                _active_club_id(db),
            ),
        )
        db.commit()
        row = _require_active_club_row(db, "content_items", poll_id)
    return _serialize_content(row, user["id"])


@app.post("/api/content/{row_id}/images")
async def upload_content_images(
    row_id: int,
    images: list[UploadFile] = File(...),
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    if not images:
        raise HTTPException(status_code=400, detail="Keine Bilder ausgewählt")
    if len(images) > 30:
        raise HTTPException(status_code=413, detail="Maximal 30 Bilder pro Upload")

    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    prepared: list[tuple[bytes, str]] = []
    for image in images:
        if image.content_type not in allowed_types:
            raise HTTPException(status_code=415, detail="Unsupported image type")
        data, optimized_mime = _optimize_image(
            await image.read(),
            image.content_type or "",
        )
        prepared.append((data, optimized_mime))

    with connect() as db:
        existing = _require_active_club_row(db, "content_items", row_id)
        _require_content_permission(existing["section"], user)
        now = datetime.now(timezone.utc).isoformat()
        max_order = db.execute(
            """
            SELECT COALESCE(MAX(sort_order), 0)
            FROM content_images
            WHERE content_id = ? AND club_id = ?
            """,
            (row_id, _active_club_id(db)),
        ).fetchone()[0]
        db.executemany(
            """
            INSERT INTO content_images (
                content_id, image_data, image_mime, sort_order, created_at, club_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row_id,
                    data,
                    mime,
                    max_order + index + 1,
                    now,
                    _active_club_id(db),
                )
                for index, (data, mime) in enumerate(prepared)
            ],
        )
        db.commit()
        row = _require_active_club_row(db, "content_items", row_id)
    return _serialize_content(row)


@app.put("/api/content/{row_id}/images/order")
def reorder_content_images(
    row_id: int,
    payload: ContentImageOrderPayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    with connect() as db:
        existing = _require_active_club_row(db, "content_items", row_id)
        _require_content_permission(existing["section"], user)
        club_id = _active_club_id(db)

        rows = db.execute(
            """
            SELECT id
            FROM content_images
            WHERE content_id = ? AND club_id = ?
            """,
            (row_id, club_id),
        ).fetchall()
        current_ids = {row["id"] for row in rows}
        requested_ids = payload.image_ids
        if len(requested_ids) != len(set(requested_ids)):
            raise HTTPException(status_code=422, detail="Doppelte Bild-ID")
        if set(requested_ids) != current_ids:
            raise HTTPException(
                status_code=422,
                detail="Bildreihenfolge ist unvollständig oder ungültig",
            )

        for position, image_id in enumerate(requested_ids, start=1):
            db.execute(
                """
                UPDATE content_images
                SET sort_order = ?
                WHERE id = ? AND content_id = ? AND club_id = ?
                """,
                (position, image_id, row_id, club_id),
            )
        db.commit()
        row = _require_active_club_row(db, "content_items", row_id)
    return _serialize_content(row)


@app.get("/api/content/{row_id}/images/{image_id}")
def get_content_gallery_image(
    row_id: int,
    image_id: int,
    _: dict[str, Any] = Depends(current_user),
) -> Response:
    with connect() as db:
        row = db.execute(
            """
            SELECT ci.image_data, ci.image_mime
            FROM content_images ci
            JOIN content_items c ON c.id = ci.content_id
            WHERE ci.id = ?
              AND ci.content_id = ?
              AND ci.club_id = ?
              AND c.club_id = ?
            """,
            (
                image_id,
                row_id,
                _active_club_id(db),
                _active_club_id(db),
            ),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(
        content=row["image_data"],
        media_type=row["image_mime"] or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@app.delete("/api/content/{row_id}/images/{image_id}", status_code=204)
def delete_content_gallery_image(
    row_id: int,
    image_id: int,
    user: dict[str, Any] = Depends(current_user),
) -> None:
    with connect() as db:
        existing = _require_active_club_row(db, "content_items", row_id)
        _require_content_permission(existing["section"], user)
        cursor = db.execute(
            """
            DELETE FROM content_images
            WHERE id = ? AND content_id = ? AND club_id = ?
            """,
            (image_id, row_id, _active_club_id(db)),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Bild nicht gefunden")
        db.commit()


@app.delete("/api/content/{row_id}/images", status_code=204)
def delete_all_content_images(
    row_id: int,
    user: dict[str, Any] = Depends(current_user),
) -> None:
    with connect() as db:
        existing = _require_active_club_row(db, "content_items", row_id)
        _require_content_permission(existing["section"], user)
        club_id = _active_club_id(db)
        db.execute(
            """
            DELETE FROM content_images
            WHERE content_id = ? AND club_id = ?
            """,
            (row_id, club_id),
        )
        db.execute(
            """
            UPDATE content_items
            SET image_data = NULL, image_mime = ''
            WHERE id = ? AND club_id = ?
            """,
            (row_id, club_id),
        )
        db.commit()


@app.post("/api/content/{row_id}/image")
async def upload_content_image(
    row_id: int,
    image: UploadFile = File(...),
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if image.content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Unsupported image type")

    data, optimized_mime = _optimize_image(
        await image.read(),
        image.content_type or "",
    )

    with connect() as db:
        existing = _require_active_club_row(db, "content_items", row_id)
        _require_content_permission(existing["section"], user)
        club_id = _active_club_id(db)
        db.execute(
            """
            UPDATE content_items
            SET image_data = ?, image_mime = ?
            WHERE id = ? AND club_id = ?
            """,
            (data, optimized_mime, row_id, club_id),
        )
        db.commit()
        row = _require_active_club_row(db, "content_items", row_id)
    return _serialize_content(row)


@app.get("/api/content/{row_id}/image")
def get_content_image(
    row_id: int,
    _: dict[str, Any] = Depends(current_user),
) -> Response:
    with connect() as db:
        row = db.execute(
            """
            SELECT image_data, image_mime
            FROM content_items
            WHERE id = ? AND club_id = ?
            """,
            (row_id, _active_club_id(db)),
        ).fetchone()
    if row is None or row["image_data"] is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(
        content=row["image_data"],
        media_type=row["image_mime"] or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@app.delete("/api/content/{row_id}/image", status_code=204)
def delete_content_image(
    row_id: int,
    user: dict[str, Any] = Depends(current_user),
) -> None:
    with connect() as db:
        existing = _require_active_club_row(db, "content_items", row_id)
        _require_content_permission(existing["section"], user)
        db.execute(
            """
            UPDATE content_items
            SET image_data = NULL, image_mime = ''
            WHERE id = ? AND club_id = ?
            """,
            (row_id, _active_club_id(db)),
        )
        db.commit()


@app.put("/api/news/order")
def reorder_news(
    payload: ContentOrderPayload,
    _: dict[str, Any] = Depends(require("can_news")),
) -> list[dict[str, Any]]:
    if not payload.item_ids:
        return []

    with connect() as db:
        club_id = _active_club_id(db)
        current_ids = {
            int(row["id"])
            for row in db.execute(
                "SELECT id FROM news WHERE club_id = ?",
                (club_id,),
            ).fetchall()
        }
        if set(payload.item_ids) != current_ids:
            raise HTTPException(
                status_code=422,
                detail="News-Reihenfolge ist unvollständig",
            )
        for position, news_id in enumerate(payload.item_ids, start=1):
            db.execute(
                """
                UPDATE news
                SET sort_order = ?
                WHERE id = ? AND club_id = ?
                """,
                (position, news_id, club_id),
            )
        db.commit()

    return list_rows("news")


@app.get("/api/news")
def get_news(
    _: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    return list_rows("news")


@app.post("/api/news")
def post_news(
    payload: NewsPayload,
    _: dict[str, Any] = Depends(require("can_news")),
) -> dict[str, Any]:
    item = create_row("news", payload)
    with connect() as db:
        _queue_push_notification(
            db,
            kind="news",
            title=payload.title,
            body=payload.text,
            route="/news",
        )
        db.commit()
    return item


@app.put("/api/news/{row_id}")
def put_news(
    row_id: int,
    payload: NewsPayload,
    _: dict[str, Any] = Depends(require("can_news")),
) -> dict[str, Any]:
    return update_row("news", row_id, payload)


@app.delete("/api/news/{row_id}", status_code=204)
def delete_news(
    row_id: int,
    _: dict[str, Any] = Depends(require("can_news")),
) -> None:
    delete_row("news", row_id)


@app.post("/api/news/{row_id}/image")
async def upload_news_image(
    row_id: int,
    image: UploadFile = File(...),
    _: dict[str, Any] = Depends(require("can_news")),
) -> dict[str, Any]:
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if image.content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Unsupported image type")

    data, optimized_mime = _optimize_image(
        await image.read(),
        image.content_type or "",
    )

    with connect() as db:
        cursor = db.execute(
            """
            UPDATE news
            SET image_data = ?, image_mime = ?, image_url = ''
            WHERE id = ? AND club_id = ?
            """,
            (data, optimized_mime, row_id, _active_club_id(db)),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Entry not found")
        db.commit()
        row = db.execute(
            "SELECT * FROM news WHERE id = ? AND club_id = ?",
            (row_id, _active_club_id(db)),
        ).fetchone()
    return _serialize_news(row)


@app.get("/api/news/{row_id}/image")
def get_news_image(
    row_id: int,
    _: dict[str, Any] = Depends(current_user),
) -> Response:
    with connect() as db:
        row = db.execute(
            """
            SELECT image_data, image_mime
            FROM news
            WHERE id = ? AND club_id = ?
            """,
            (row_id, _active_club_id(db)),
        ).fetchone()

    if row is None or row["image_data"] is None:
        raise HTTPException(status_code=404, detail="Image not found")

    return Response(
        content=row["image_data"],
        media_type=row["image_mime"] or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@app.delete("/api/news/{row_id}/image", status_code=204)
def delete_news_image(
    row_id: int,
    _: dict[str, Any] = Depends(require("can_news")),
) -> None:
    with connect() as db:
        cursor = db.execute(
            """
            UPDATE news
            SET image_data = NULL, image_mime = '', image_url = ''
            WHERE id = ? AND club_id = ?
            """,
            (row_id, _active_club_id(db)),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Entry not found")
        db.commit()


@app.get("/api/events")
def get_events(
    user: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    items = list_rows("events")
    with connect() as db:
        counts = {
            row["event_id"]: row["count"]
            for row in db.execute(
                """
                SELECT event_id, COUNT(*) AS count
                FROM event_registrations
                WHERE club_id = ?
                GROUP BY event_id
                """,
                (_active_club_id(db),),
            ).fetchall()
        }
        mine = {
            row["event_id"]
            for row in db.execute(
                """
                SELECT event_id
                FROM event_registrations
                WHERE user_id = ? AND club_id = ?
                """,
                (user["id"], _active_club_id(db)),
            ).fetchall()
        }
    for item in items:
        item["registration_count"] = counts.get(item["id"], 0)
        item["registered_by_me"] = item["id"] in mine
    return items


@app.post("/api/events")
def post_events(
    payload: EventPayload,
    _: dict[str, Any] = Depends(require("can_events")),
) -> dict[str, Any]:
    item = create_row("events", payload)
    with connect() as db:
        _queue_push_notification(
            db,
            kind="event",
            title=f"Neuer Termin: {payload.title}",
            body=" ".join(part for part in [payload.event_date, payload.time, payload.location] if part),
            route="/events",
        )
        db.commit()
    return item


@app.put("/api/events/{row_id}")
def put_events(
    row_id: int,
    payload: EventPayload,
    _: dict[str, Any] = Depends(require("can_events")),
) -> dict[str, Any]:
    item = update_row("events", row_id, payload)
    with connect() as db:
        _queue_push_notification(
            db,
            kind="event_update",
            title=f"Termin geändert: {payload.title}",
            body=" ".join(part for part in [payload.event_date, payload.time, payload.location] if part),
            route="/events",
        )
        db.commit()
    return item


@app.get("/api/events/{row_id}/registrations")
def get_event_registrations(
    row_id: int,
    _: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    with connect() as db:
        club_id = _active_club_id(db)
        event = db.execute(
            "SELECT id FROM events WHERE id = ? AND club_id = ?",
            (row_id, club_id),
        ).fetchone()
        if event is None:
            raise HTTPException(status_code=404, detail="Termin nicht gefunden")
        rows = db.execute(
            """
            SELECT COALESCE(NULLIF(m.name, ''), u.username) AS name
            FROM event_registrations r
            JOIN users u ON u.id = r.user_id
            LEFT JOIN members m ON m.id = u.member_id
            WHERE r.event_id = ?
              AND r.club_id = ?
              AND u.active = 1
            ORDER BY name COLLATE NOCASE
            """,
            (row_id, club_id),
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/events/{row_id}/registration", status_code=204)
def register_for_event(
    row_id: int,
    user: dict[str, Any] = Depends(current_user),
) -> None:
    with connect() as db:
        club_id = _active_club_id(db)
        event = db.execute(
            "SELECT id FROM events WHERE id = ? AND club_id = ?",
            (row_id, club_id),
        ).fetchone()
        if event is None:
            raise HTTPException(status_code=404, detail="Termin nicht gefunden")
        db.execute(
            """
            INSERT OR IGNORE INTO event_registrations (
                event_id, user_id, created_at, club_id
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                row_id,
                user["id"],
                datetime.now(timezone.utc).isoformat(),
                club_id,
            ),
        )
        db.commit()


@app.delete("/api/events/{row_id}/registration", status_code=204)
def unregister_from_event(
    row_id: int,
    user: dict[str, Any] = Depends(current_user),
) -> None:
    with connect() as db:
        club_id = _active_club_id(db)
        event = db.execute(
            "SELECT id FROM events WHERE id = ? AND club_id = ?",
            (row_id, club_id),
        ).fetchone()
        if event is None:
            raise HTTPException(status_code=404, detail="Termin nicht gefunden")
        db.execute(
            """
            DELETE FROM event_registrations
            WHERE event_id = ? AND user_id = ? AND club_id = ?
            """,
            (row_id, user["id"], club_id),
        )
        db.commit()


@app.delete("/api/events/{row_id}", status_code=204)
def delete_events(
    row_id: int,
    _: dict[str, Any] = Depends(require("can_events")),
) -> None:
    with connect() as db:
        club_id = _active_club_id(db)
        db.execute(
            "DELETE FROM event_registrations WHERE event_id = ? AND club_id = ?",
            (row_id, club_id),
        )
        db.commit()
    delete_row("events", row_id)


@app.get("/api/member-filters")
def get_member_filters(
    _: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute(
            """
            SELECT id, label, active, sort_order
            FROM member_filters
            WHERE club_id = ?
            ORDER BY sort_order ASC, label COLLATE NOCASE ASC, id ASC
            """,
            (_active_club_id(db),),
        ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "label": row["label"],
            "active": bool(row["active"]),
            "sort_order": int(row["sort_order"]),
        }
        for row in rows
    ]


@app.post("/api/member-filters")
def post_member_filter(
    payload: MemberFilterPayload,
    _: dict[str, Any] = Depends(require("can_members")),
) -> dict[str, Any]:
    with connect() as db:
        sort_order = db.execute(
            """
            SELECT COALESCE(MAX(sort_order), 0) + 1
            FROM member_filters
            WHERE club_id = ?
            """,
            (_active_club_id(db),),
        ).fetchone()[0]
        try:
            cursor = db.execute(
                """
                INSERT INTO member_filters (
                    label, active, sort_order, created_at, club_id
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    payload.label.strip(),
                    1 if payload.active else 0,
                    sort_order,
                    datetime.now(timezone.utc).isoformat(),
                    _active_club_id(db),
                ),
            )
            db.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Filter existiert bereits")
        row = db.execute(
            """
            SELECT id, label, active, sort_order
            FROM member_filters
            WHERE id = ? AND club_id = ?
            """,
            (cursor.lastrowid, _active_club_id(db)),
        ).fetchone()
    return {
        "id": int(row["id"]),
        "label": row["label"],
        "active": bool(row["active"]),
        "sort_order": int(row["sort_order"]),
    }


@app.put("/api/member-filters/order")
def reorder_member_filters(
    payload: ContentOrderPayload,
    _: dict[str, Any] = Depends(require("can_members")),
) -> list[dict[str, Any]]:
    with connect() as db:
        club_id = _active_club_id(db)
        ids = {
            int(row["id"])
            for row in db.execute(
                "SELECT id FROM member_filters WHERE club_id = ?",
                (club_id,),
            )
        }
        if set(payload.item_ids) != ids:
            raise HTTPException(status_code=422, detail="Filterreihenfolge ist unvollständig")
        for position, filter_id in enumerate(payload.item_ids, start=1):
            db.execute(
                """
                UPDATE member_filters
                SET sort_order = ?
                WHERE id = ? AND club_id = ?
                """,
                (position, filter_id, club_id),
            )
        db.commit()
    return get_member_filters(_)


@app.put("/api/member-filters/{filter_id}")
def put_member_filter(
    filter_id: int,
    payload: MemberFilterPayload,
    _: dict[str, Any] = Depends(require("can_members")),
) -> dict[str, Any]:
    with connect() as db:
        try:
            cursor = db.execute(
                """
                UPDATE member_filters
                SET label = ?, active = ?
                WHERE id = ? AND club_id = ?
                """,
                (
                    payload.label.strip(),
                    1 if payload.active else 0,
                    filter_id,
                    _active_club_id(db),
                ),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Filter nicht gefunden")
            db.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Filter existiert bereits")
        row = db.execute(
            """
            SELECT id, label, active, sort_order
            FROM member_filters
            WHERE id = ? AND club_id = ?
            """,
            (filter_id, _active_club_id(db)),
        ).fetchone()
    return {
        "id": int(row["id"]),
        "label": row["label"],
        "active": bool(row["active"]),
        "sort_order": int(row["sort_order"]),
    }


@app.delete("/api/member-filters/{filter_id}", status_code=204)
def delete_member_filter(
    filter_id: int,
    _: dict[str, Any] = Depends(require("can_members")),
) -> None:
    with connect() as db:
        club_id = _active_club_id(db)
        db.execute(
            """
            DELETE FROM member_filter_links
            WHERE filter_id = ? AND club_id = ?
            """,
            (filter_id, club_id),
        )
        cursor = db.execute(
            "DELETE FROM member_filters WHERE id = ? AND club_id = ?",
            (filter_id, club_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Filter nicht gefunden")
        db.commit()


@app.put("/api/members/me")
def put_my_member(
    payload: MemberSelfUpdatePayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    member_id = user.get("member_id")
    if member_id is None:
        raise HTTPException(status_code=400, detail="Benutzer ist keinem Mitglied zugeordnet")

    data = payload.model_dump()
    assignments = ", ".join(f"{column} = ?" for column in data)
    with connect() as db:
        cursor = db.execute(
            f"UPDATE members SET {assignments} WHERE id = ? AND club_id = ?",
            [*data.values(), member_id, _active_club_id(db)],
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Mitglied nicht gefunden")
        db.commit()
        row = db.execute(
            "SELECT * FROM members WHERE id = ? AND club_id = ?",
            (member_id, _active_club_id(db)),
        ).fetchone()
    return _serialize_member(row)


@app.post("/api/members/me/photo")
async def upload_my_member_photo(
    photo: UploadFile = File(...),
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    member_id = user.get("member_id")
    if member_id is None:
        raise HTTPException(status_code=400, detail="Benutzer ist keinem Mitglied zugeordnet")

    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if photo.content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Unsupported image type")

    data, optimized_mime = _optimize_image(
        await photo.read(),
        photo.content_type or "",
    )

    with connect() as db:
        cursor = db.execute(
            """
            UPDATE members
            SET photo_data = ?, photo_mime = ?
            WHERE id = ? AND club_id = ?
            """,
            (data, optimized_mime, member_id, _active_club_id(db)),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Mitglied nicht gefunden")
        db.commit()
        row = db.execute(
            "SELECT * FROM members WHERE id = ? AND club_id = ?",
            (member_id, _active_club_id(db)),
        ).fetchone()
    return _serialize_member(row)


@app.delete("/api/members/me/photo", status_code=204)
def delete_my_member_photo(
    user: dict[str, Any] = Depends(current_user),
) -> None:
    member_id = user.get("member_id")
    if member_id is None:
        raise HTTPException(status_code=400, detail="Benutzer ist keinem Mitglied zugeordnet")
    with connect() as db:
        cursor = db.execute(
            """
            UPDATE members
            SET photo_data = NULL, photo_mime = ''
            WHERE id = ? AND club_id = ?
            """,
            (member_id, _active_club_id(db)),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Mitglied nicht gefunden")
        db.commit()


@app.get("/api/members")
def get_members(
    _: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    return list_rows("members")


@app.put("/api/members/order")
def reorder_members(
    payload: ContentOrderPayload,
    _: dict[str, Any] = Depends(require("can_members")),
) -> list[dict[str, Any]]:
    if not payload.item_ids:
        return []

    with connect() as db:
        club_id = _active_club_id(db)
        placeholders = ",".join("?" for _ in payload.item_ids)
        rows = db.execute(
            f"""
            SELECT id
            FROM members
            WHERE id IN ({placeholders}) AND club_id = ?
            """,
            [*payload.item_ids, club_id],
        ).fetchall()
        if len(rows) != len(set(payload.item_ids)):
            raise HTTPException(status_code=422, detail="Mitgliederreihenfolge ist ungültig")

        all_ids = [
            row["id"]
            for row in db.execute(
                """
                SELECT id
                FROM members
                WHERE club_id = ?
                ORDER BY sort_order ASC, name COLLATE NOCASE ASC, id ASC
                """,
                (club_id,),
            ).fetchall()
        ]
        if set(all_ids) != set(payload.item_ids):
            raise HTTPException(status_code=422, detail="Mitgliederreihenfolge ist unvollständig")

        for position, member_id in enumerate(payload.item_ids, start=1):
            db.execute(
                """
                UPDATE members
                SET sort_order = ?
                WHERE id = ? AND club_id = ?
                """,
                (position, member_id, club_id),
            )
        db.commit()
        ordered = db.execute(
            """
            SELECT *
            FROM members
            WHERE club_id = ?
            ORDER BY sort_order ASC, name COLLATE NOCASE ASC, id ASC
            """,
            (club_id,),
        ).fetchall()

    return [_serialize_member(row) for row in ordered]


@app.post("/api/members")
def post_members(
    payload: MemberPayload,
    _: dict[str, Any] = Depends(require("can_members")),
) -> dict[str, Any]:
    item = create_row("members", payload)
    with connect() as db:
        club_id = _active_club_id(db)
        max_order = db.execute(
            """
            SELECT COALESCE(MAX(sort_order), 0)
            FROM members
            WHERE id != ? AND club_id = ?
            """,
            (item["id"], club_id),
        ).fetchone()[0]
        db.execute(
            """
            UPDATE members
            SET sort_order = ?
            WHERE id = ? AND club_id = ?
            """,
            (int(max_order or 0) + 1, item["id"], club_id),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM members WHERE id = ? AND club_id = ?",
            (item["id"], club_id),
        ).fetchone()
    return _serialize_member(row)


@app.put("/api/members/{row_id}")
def put_members(
    row_id: int,
    payload: MemberPayload,
    _: dict[str, Any] = Depends(require("can_members")),
) -> dict[str, Any]:
    return update_row("members", row_id, payload)


@app.post("/api/members/{row_id}/photo")
async def upload_member_photo(
    row_id: int,
    photo: UploadFile = File(...),
    _: dict[str, Any] = Depends(require("can_members")),
) -> dict[str, Any]:
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if photo.content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Unsupported image type")

    data, optimized_mime = _optimize_image(
        await photo.read(),
        photo.content_type or "",
    )

    with connect() as db:
        cursor = db.execute(
            """
            UPDATE members
            SET photo_data = ?, photo_mime = ?
            WHERE id = ? AND club_id = ?
            """,
            (data, optimized_mime, row_id, _active_club_id(db)),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Mitglied nicht gefunden")
        db.commit()
        row = db.execute(
            "SELECT * FROM members WHERE id = ? AND club_id = ?",
            (row_id, _active_club_id(db)),
        ).fetchone()
    return _serialize_member(row)


@app.get("/api/members/{row_id}/photo")
def get_member_photo(
    row_id: int,
    _: dict[str, Any] = Depends(current_user),
) -> Response:
    with connect() as db:
        row = db.execute(
            """
            SELECT photo_data, photo_mime
            FROM members
            WHERE id = ? AND club_id = ?
            """,
            (row_id, _active_club_id(db)),
        ).fetchone()
    if row is None or row["photo_data"] is None:
        raise HTTPException(status_code=404, detail="Photo not found")

    return Response(
        content=row["photo_data"],
        media_type=row["photo_mime"] or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@app.delete("/api/members/{row_id}/photo", status_code=204)
def delete_member_photo(
    row_id: int,
    _: dict[str, Any] = Depends(require("can_members")),
) -> None:
    with connect() as db:
        cursor = db.execute(
            """
            UPDATE members
            SET photo_data = NULL, photo_mime = ''
            WHERE id = ? AND club_id = ?
            """,
            (row_id, _active_club_id(db)),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Mitglied nicht gefunden")
        db.commit()


@app.delete("/api/members/{row_id}", status_code=204)
def delete_members(
    row_id: int,
    _: dict[str, Any] = Depends(require("can_members")),
) -> None:
    with connect() as db:
        db.execute(
            """
            DELETE FROM member_filter_links
            WHERE member_id = ? AND club_id = ?
            """,
            (row_id, _active_club_id(db)),
        )
        db.commit()
    delete_row("members", row_id)
