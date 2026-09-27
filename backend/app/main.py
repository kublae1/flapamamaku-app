import asyncio
import base64
import hashlib
import hmac
import io
import json
import logging
import os
import secrets
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account
from pydantic import BaseModel, Field
from PIL import Image, ImageOps, ImageSequence


DB_PATH = Path(os.getenv("FLAPAMAMAKU_DB", "/data/flapamamaku.db"))
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
SESSION_EXPIRES_AT = "9999-12-31T23:59:59+00:00"
API_VERSION = "0.8.30"
APP_ENV = os.getenv("FLAPAMAMAKU_ENV", "development").strip().lower()
IS_PRODUCTION = APP_ENV == "production"
logger = logging.getLogger("flapamamaku.push")
FIREBASE_SERVICE_ACCOUNT_JSON = os.getenv(
    "FLAPAMAMAKU_FIREBASE_SERVICE_ACCOUNT_JSON",
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

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("FLAPAMAMAKU_ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
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
    "can_manage_users",
)


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


class PollVotePayload(BaseModel):
    option_index: int = Field(ge=0, le=20)


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
    can_manage_users: bool = False


class PushTokenPayload(BaseModel):
    token: str = Field(min_length=20, max_length=4096)
    platform: str = Field(default="android", max_length=20)


class PushTokenDeletePayload(BaseModel):
    token: str = Field(min_length=20, max_length=4096)


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


def init_db() -> None:
    with connect() as db:
        for ddl, _ in TABLES.values():
            db.execute(ddl)

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
            },
            "data": {
                "kind": kind,
                "route": route,
            },
            "android": {
                "priority": "high",
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
                WHERE enabled = 1
                ORDER BY id ASC
                """
            ).fetchall()
            if not tokens:
                continue

            had_transient_error = False
            for token in tokens:
                delivered = db.execute(
                    """
                    SELECT sent_at
                    FROM push_deliveries
                    WHERE notification_id = ? AND token_id = ?
                    """,
                    (notification["id"], token["id"]),
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
                        WHERE notification_id = ? AND token_id = ?
                        """,
                        (notification["id"], token["id"]),
                    )
                    continue

                db.execute(
                    """
                    INSERT INTO push_deliveries (
                        notification_id, token_id, sent_at, last_error
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT(notification_id, token_id) DO UPDATE SET
                        sent_at = excluded.sent_at,
                        last_error = excluded.last_error
                    """,
                    (
                        notification["id"],
                        token["id"],
                        now if ok else None,
                        error,
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
                  AND NOT EXISTS (
                      SELECT 1
                      FROM push_deliveries pd
                      WHERE pd.notification_id = ?
                        AND pd.token_id = pt.id
                        AND pd.sent_at IS NOT NULL
                  )
                """,
                (notification["id"],),
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


async def _push_delivery_loop() -> None:
    while True:
        await asyncio.sleep(15)
        if FIREBASE_SERVICE_ACCOUNT_JSON:
            await asyncio.to_thread(_deliver_pending_push)


@app.on_event("startup")
async def startup() -> None:
    init_db()
    asyncio.create_task(_snapshot_cleanup_loop())
    asyncio.create_task(_push_delivery_loop())


def _hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
    return digest.hex(), salt.hex()


def _check_password(password: str, password_hash: str, salt_hex: str) -> bool:
    digest, _ = _hash_password(password, salt_hex)
    return hmac.compare_digest(digest, password_hash)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _serialize_user(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item.pop("password_hash", None)
    item.pop("password_salt", None)
    for key in PERMISSION_FIELDS:
        item[key] = bool(item.get(key, 0))
    item["active"] = bool(item.get("active", 0))
    return item


def _user_profile(user_id: int) -> dict[str, Any]:
    with connect() as db:
        row = db.execute(
            """
            SELECT u.*, m.name AS member_name
            FROM users u
            LEFT JOIN members m ON m.id = u.member_id
            WHERE u.id = ?
            """,
            (user_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Benutzer nicht gefunden")
    return _serialize_user(row)


def _extract_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Anmeldung erforderlich")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Anmeldung erforderlich")
    return token


def current_user(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    token = _extract_token(authorization)
    with connect() as db:
        row = db.execute(
            """
            SELECT u.*
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND u.active = 1
            """,
            (_token_hash(token),),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Sitzung ungültig oder abgelaufen")
    return _serialize_user(row)


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
                WHERE member_id = ?
                ORDER BY filter_id ASC
                """,
                (item["id"],),
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
            kind, title, body, route, created_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            kind,
            title[:200],
            body[:500],
            route,
            datetime.now(timezone.utc).isoformat(),
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
        rows = db.execute(
            f"SELECT * FROM {resource} ORDER BY {order}"
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
    if resource in {"members", "news"}:
        with connect() as db:
            data["sort_order"] = db.execute(
                f"SELECT COALESCE(MAX(sort_order), 0) + 1 FROM {resource}"
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
                    "INSERT OR IGNORE INTO member_filter_links (member_id, filter_id) VALUES (?, ?)",
                    (cursor.lastrowid, filter_id),
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
        cursor = db.execute(
            f"UPDATE {resource} SET {assignments} WHERE id = ?",
            [*data.values(), row_id],
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Entry not found")
        if resource == "members":
            db.execute("DELETE FROM member_filter_links WHERE member_id = ?", (row_id,))
            for filter_id in sorted(set(member_filter_ids)):
                db.execute(
                    "INSERT OR IGNORE INTO member_filter_links (member_id, filter_id) VALUES (?, ?)",
                    (row_id, filter_id),
                )
        db.commit()
        row = db.execute(
            f"SELECT * FROM {resource} WHERE id = ?",
            (row_id,),
        ).fetchone()
    if resource == "news":
        return _serialize_news(row)
    if resource == "members":
        return _serialize_member(row)
    return dict(row)


def delete_row(resource: str, row_id: int) -> None:
    table_or_404(resource)
    with connect() as db:
        cursor = db.execute(
            f"DELETE FROM {resource} WHERE id = ?",
            (row_id,),
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
            SELECT id, sort_order
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

            item["poll_options"] = options
            item["poll_counts"] = counts
            item["poll_total_votes"] = sum(counts)
            item["poll_my_vote"] = my_vote
            item["poll_voters"] = [
                {
                    "name": str(voter["voter_name"] or "").strip(),
                    "option_index": int(voter["option_index"]),
                }
                for voter in voter_rows
                if str(voter["voter_name"] or "").strip()
            ]
        else:
            item["poll_options"] = []
            item["poll_counts"] = []
            item["poll_total_votes"] = 0
            item["poll_my_vote"] = None
            item["poll_voters"] = []
    images = [
        {
            "id": image_row["id"],
            "url": f"/api/content/{item['id']}/images/{image_row['id']}",
            "legacy": False,
            "sort_order": image_row["sort_order"],
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


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "FLAPAMAMAKU API",
        "admin": "/admin",
        "docs": "/api/docs",
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": API_VERSION}


@app.get("/admin")
def admin() -> FileResponse:
    return FileResponse(STATIC_DIR / "admin.html")


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
                {", ".join(PERMISSION_FIELDS)}, created_at
            ) VALUES (?, ?, ?, ?, 1, {", ".join("?" for _ in PERMISSION_FIELDS)}, ?)
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
        db.commit()
        user_id = cursor.lastrowid
    return _user_profile(user_id)


@app.post("/api/auth/login")
def login(payload: LoginPayload) -> dict[str, Any]:
    with connect() as db:
        row = db.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE AND active = 1",
            (payload.username.strip(),),
        ).fetchone()
        if row is None or not _check_password(
            payload.password,
            row["password_hash"],
            row["password_salt"],
        ):
            raise HTTPException(status_code=401, detail="Benutzername oder Passwort falsch")

        token = secrets.token_urlsafe(48)
        now_dt = datetime.now(timezone.utc)
        expires = SESSION_EXPIRES_AT
        db.execute(
            """
            INSERT INTO sessions (token_hash, user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                _token_hash(token),
                row["id"],
                expires,
                now_dt.isoformat(),
            ),
        )
        db.commit()

    return {
        "token": token,
        "expires_at": expires,
        "user": _user_profile(row["id"]),
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
    return _user_profile(user["id"])


@app.get("/api/users")
def get_users(
    _: dict[str, Any] = Depends(require("can_manage_users")),
) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute(
            """
            SELECT u.*, m.name AS member_name
            FROM users u
            LEFT JOIN members m ON m.id = u.member_id
            ORDER BY u.username COLLATE NOCASE
            """
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
    data = payload.model_dump(exclude={"password"})
    now = datetime.now(timezone.utc).isoformat()

    with connect() as db:
        try:
            cursor = db.execute(
                f"""
                INSERT INTO users (
                    member_id, username, password_hash, password_salt, active,
                    {", ".join(PERMISSION_FIELDS)}, created_at
                ) VALUES (?, ?, ?, ?, ?, {", ".join("?" for _ in PERMISSION_FIELDS)}, ?)
                """,
                [
                    data["member_id"],
                    data["username"].strip(),
                    password_hash,
                    salt,
                    int(data["active"]),
                    *[int(data[key]) for key in PERMISSION_FIELDS],
                    now,
                ],
            )
            db.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Benutzername bereits vorhanden")
    return _user_profile(cursor.lastrowid)


@app.put("/api/users/{user_id}")
def put_user(
    user_id: int,
    payload: UserPayload,
    actor: dict[str, Any] = Depends(require("can_manage_users")),
) -> dict[str, Any]:
    data = payload.model_dump(exclude={"password"})
    assignments = ["member_id = ?", "username = ?", "active = ?"]
    values: list[Any] = [
        data["member_id"],
        data["username"].strip(),
        int(data["active"]),
    ]
    for key in PERMISSION_FIELDS:
        assignments.append(f"{key} = ?")
        values.append(int(data[key]))

    password_changed = bool(payload.password)
    if payload.password:
        if len(payload.password) < 6:
            raise HTTPException(status_code=422, detail="Passwort muss mindestens 6 Zeichen haben")
        password_hash, salt = _hash_password(payload.password)
        assignments.extend(["password_hash = ?", "password_salt = ?"])
        values.extend([password_hash, salt])

    if user_id == actor["id"] and not data["can_manage_users"]:
        raise HTTPException(
            status_code=400,
            detail="Eigenes Recht zur Benutzerverwaltung kann nicht entfernt werden",
        )

    values.append(user_id)
    with connect() as db:
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
        user = db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
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
        db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        cursor = db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
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
                user_id, image_data, image_mime, created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                data,
                mime,
                now.isoformat(),
                expires.isoformat(),
            ),
        )
        db.commit()
        row = db.execute(
            """
            SELECT gs.*, u.username, m.name AS member_name
            FROM gallery_snapshots gs
            JOIN users u ON u.id = gs.user_id
            LEFT JOIN members m ON m.id = u.member_id
            WHERE gs.id = ?
            """,
            (cursor.lastrowid,),
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
            WHERE id = ? AND expires_at > ?
            """,
            (snapshot_id, datetime.now(timezone.utc).isoformat()),
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
        row = db.execute(
            "SELECT user_id FROM gallery_snapshots WHERE id = ?",
            (snapshot_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Snapshot nicht gefunden")
        if row["user_id"] != user["id"] and not user.get("can_photos", False):
            raise HTTPException(status_code=403, detail="Keine Berechtigung")
        db.execute("DELETE FROM gallery_snapshots WHERE id = ?", (snapshot_id,))
        db.commit()


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
                user_id, token, platform, enabled, created_at, updated_at
            ) VALUES (?, ?, ?, 1, ?, ?)
            ON CONFLICT(token) DO UPDATE SET
                user_id = excluded.user_id,
                platform = excluded.platform,
                enabled = 1,
                updated_at = excluded.updated_at
            """,
            (user["id"], payload.token, platform, now, now),
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
            "DELETE FROM push_tokens WHERE token = ? AND user_id = ?",
            (payload.token, user["id"]),
        )
        db.commit()


@app.get("/api/push/status")
def push_status(
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    with connect() as db:
        count = db.execute(
            "SELECT COUNT(*) FROM push_tokens WHERE user_id = ? AND enabled = 1",
            (user["id"],),
        ).fetchone()[0]
        total_devices = db.execute(
            "SELECT COUNT(*) FROM push_tokens WHERE enabled = 1",
        ).fetchone()[0]
        queued = db.execute(
            "SELECT COUNT(*) FROM push_notifications WHERE sent_at IS NULL",
        ).fetchone()[0]
        last_delivery_error = db.execute(
            """
            SELECT last_error
            FROM push_deliveries
            WHERE last_error IS NOT NULL AND last_error <> ''
            ORDER BY rowid DESC
            LIMIT 1
            """
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


@app.get("/api/content")
def get_content(
    section: str | None = None,
    user: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM content_items"
    values: list[Any] = []
    if section:
        _content_permission(section)
        sql += " WHERE section = ?"
        values.append(section)
    sql += " ORDER BY sort_order ASC, id ASC"

    with connect() as db:
        _cleanup_expired_snapshots(db)
        rows = db.execute(sql, values).fetchall()
        snapshots: list[sqlite3.Row] = []
        if section is None or section == "gallery":
            snapshots = db.execute(
                """
                SELECT gs.*, u.username, m.name AS member_name
                FROM gallery_snapshots gs
                JOIN users u ON u.id = gs.user_id
                LEFT JOIN members m ON m.id = u.member_id
                WHERE gs.expires_at > ?
                ORDER BY gs.created_at DESC, gs.id DESC
                """,
                (datetime.now(timezone.utc).isoformat(),),
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
        rows = db.execute(
            f"""
            SELECT id, section
            FROM content_items
            WHERE id IN ({",".join("?" for _ in payload.item_ids)})
            """,
            payload.item_ids,
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

        current_rows = db.execute(
            """
            SELECT id
            FROM content_items
            WHERE section = ?
            ORDER BY sort_order ASC, id ASC
            """,
            (section,),
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
                WHERE id = ? AND section = ?
                """,
                (position, item_id, section),
            )
        db.commit()

        ordered = db.execute(
            """
            SELECT *
            FROM content_items
            WHERE section = ?
            ORDER BY sort_order ASC, id ASC
            """,
            (section,),
        ).fetchall()
    return [_serialize_content(row) for row in ordered]


@app.post("/api/content")
def post_content(
    payload: ContentPayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    _require_content_permission(payload.section, user)
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        if payload.section == "sujet":
            archive_max = db.execute(
                """
                SELECT COALESCE(MAX(sort_order), 0)
                FROM content_items
                WHERE section = 'archive'
                """
            ).fetchone()[0]
            current_sujets = db.execute(
                """
                SELECT id
                FROM content_items
                WHERE section = 'sujet'
                ORDER BY sort_order ASC, id ASC
                """
            ).fetchall()
            for offset, current_sujet in enumerate(current_sujets, start=1):
                db.execute(
                    """
                    UPDATE content_items
                    SET section = 'archive', sort_order = ?
                    WHERE id = ?
                    """,
                    (archive_max + offset, current_sujet["id"]),
                )

        max_order = db.execute(
            """
            SELECT COALESCE(MAX(sort_order), 0)
            FROM content_items
            WHERE section = ?
            """,
            (payload.section,),
        ).fetchone()[0]
        cursor = db.execute(
            """
            INSERT INTO content_items (
                section, title, text, link_url, poll_options, sort_order, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
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
                max_order + 1,
                now,
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
        row = db.execute(
            "SELECT * FROM content_items WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return _serialize_content(row, user["id"])


@app.put("/api/content/{row_id}")
def put_content(
    row_id: int,
    payload: ContentPayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    _require_content_permission(payload.section, user)
    with connect() as db:
        current = db.execute(
            "SELECT section FROM content_items WHERE id = ?",
            (row_id,),
        ).fetchone()
        if current is None:
            raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
        _require_content_permission(current["section"], user)
        if payload.section == "sujet":
            archive_max = db.execute(
                """
                SELECT COALESCE(MAX(sort_order), 0)
                FROM content_items
                WHERE section = 'archive'
                """
            ).fetchone()[0]
            other_sujets = db.execute(
                """
                SELECT id
                FROM content_items
                WHERE section = 'sujet' AND id != ?
                ORDER BY sort_order ASC, id ASC
                """,
                (row_id,),
            ).fetchall()
            for offset, other_sujet in enumerate(other_sujets, start=1):
                db.execute(
                    """
                    UPDATE content_items
                    SET section = 'archive', sort_order = ?
                    WHERE id = ?
                    """,
                    (archive_max + offset, other_sujet["id"]),
                )

        db.execute(
            """
            UPDATE content_items
            SET section = ?, title = ?, text = ?, link_url = ?, poll_options = ?,
                sort_order = CASE WHEN ? = 'sujet' THEN 1 ELSE sort_order END
            WHERE id = ?
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
                payload.section,
                row_id,
            ),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM content_items WHERE id = ?",
            (row_id,),
        ).fetchone()
    return _serialize_content(row)


@app.delete("/api/content/{row_id}", status_code=204)
def delete_content(
    row_id: int,
    user: dict[str, Any] = Depends(current_user),
) -> None:
    with connect() as db:
        row = db.execute(
            "SELECT section FROM content_items WHERE id = ?",
            (row_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
        _require_content_permission(row["section"], user)
        db.execute("DELETE FROM content_images WHERE content_id = ?", (row_id,))
        db.execute("DELETE FROM poll_votes WHERE poll_id = ?", (row_id,))
        db.execute("DELETE FROM content_items WHERE id = ?", (row_id,))
        db.commit()


@app.post("/api/content/{row_id}/document")
async def upload_content_document(
    row_id: int,
    document: UploadFile = File(...),
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    with connect() as db:
        existing = db.execute(
            "SELECT * FROM content_items WHERE id = ?",
            (row_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
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
            WHERE id = ?
            """,
            (data, filename, row_id),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM content_items WHERE id = ?",
            (row_id,),
        ).fetchone()
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
            WHERE id = ?
            """,
            (row_id,),
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
        existing = db.execute(
            "SELECT section FROM content_items WHERE id = ?",
            (row_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
        _require_content_permission(existing["section"], user)
        db.execute(
            """
            UPDATE content_items
            SET document_data = NULL, document_mime = '', document_name = ''
            WHERE id = ?
            """,
            (row_id,),
        )
        db.commit()


@app.post("/api/polls/{poll_id}/vote")
def vote_poll(
    poll_id: int,
    payload: PollVotePayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    with connect() as db:
        poll = db.execute(
            "SELECT * FROM content_items WHERE id = ? AND section = 'polls'",
            (poll_id,),
        ).fetchone()
        if poll is None:
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
            INSERT INTO poll_votes (poll_id, user_id, option_index, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(poll_id, user_id) DO UPDATE SET
                option_index = excluded.option_index,
                created_at = excluded.created_at
            """,
            (poll_id, user["id"], payload.option_index, now),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM content_items WHERE id = ?",
            (poll_id,),
        ).fetchone()
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
        existing = db.execute(
            "SELECT * FROM content_items WHERE id = ?",
            (row_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
        _require_content_permission(existing["section"], user)
        if existing["section"] == "gallery" and len(prepared) != 1:
            raise HTTPException(
                status_code=422,
                detail="Galerie-Einträge dürfen genau ein Bild enthalten",
            )
        now = datetime.now(timezone.utc).isoformat()
        if existing["section"] in {"sujet", "gallery"}:
            db.execute(
                "DELETE FROM content_images WHERE content_id = ?",
                (row_id,),
            )
            max_order = 0
        else:
            max_order = db.execute(
                """
                SELECT COALESCE(MAX(sort_order), 0)
                FROM content_images
                WHERE content_id = ?
                """,
                (row_id,),
            ).fetchone()[0]
        db.executemany(
            """
            INSERT INTO content_images (
                content_id, image_data, image_mime, sort_order, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                (row_id, data, mime, max_order + index + 1, now)
                for index, (data, mime) in enumerate(prepared)
            ],
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM content_items WHERE id = ?",
            (row_id,),
        ).fetchone()
    return _serialize_content(row)


@app.put("/api/content/{row_id}/images/order")
def reorder_content_images(
    row_id: int,
    payload: ContentImageOrderPayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    with connect() as db:
        existing = db.execute(
            "SELECT * FROM content_items WHERE id = ?",
            (row_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
        _require_content_permission(existing["section"], user)

        rows = db.execute(
            "SELECT id FROM content_images WHERE content_id = ?",
            (row_id,),
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
                WHERE id = ? AND content_id = ?
                """,
                (position, image_id, row_id),
            )
        db.commit()
        row = db.execute(
            "SELECT * FROM content_items WHERE id = ?",
            (row_id,),
        ).fetchone()
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
            SELECT image_data, image_mime
            FROM content_images
            WHERE id = ? AND content_id = ?
            """,
            (image_id, row_id),
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
        existing = db.execute(
            "SELECT section FROM content_items WHERE id = ?",
            (row_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
        _require_content_permission(existing["section"], user)
        cursor = db.execute(
            "DELETE FROM content_images WHERE id = ? AND content_id = ?",
            (image_id, row_id),
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
        existing = db.execute(
            "SELECT section FROM content_items WHERE id = ?",
            (row_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
        _require_content_permission(existing["section"], user)
        db.execute(
            "DELETE FROM content_images WHERE content_id = ?",
            (row_id,),
        )
        db.execute(
            """
            UPDATE content_items
            SET image_data = NULL, image_mime = ''
            WHERE id = ?
            """,
            (row_id,),
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
        existing = db.execute(
            "SELECT section FROM content_items WHERE id = ?",
            (row_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
        _require_content_permission(existing["section"], user)
        db.execute(
            """
            UPDATE content_items
            SET image_data = ?, image_mime = ?
            WHERE id = ?
            """,
            (data, optimized_mime, row_id),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM content_items WHERE id = ?",
            (row_id,),
        ).fetchone()
    return _serialize_content(row)


@app.get("/api/content/{row_id}/image")
def get_content_image(
    row_id: int,
    _: dict[str, Any] = Depends(current_user),
) -> Response:
    with connect() as db:
        row = db.execute(
            "SELECT image_data, image_mime FROM content_items WHERE id = ?",
            (row_id,),
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
        existing = db.execute(
            "SELECT section FROM content_items WHERE id = ?",
            (row_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
        _require_content_permission(existing["section"], user)
        db.execute(
            """
            UPDATE content_items
            SET image_data = NULL, image_mime = ''
            WHERE id = ?
            """,
            (row_id,),
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
        current_ids = {
            int(row["id"]) for row in db.execute("SELECT id FROM news").fetchall()
        }
        if set(payload.item_ids) != current_ids:
            raise HTTPException(
                status_code=422,
                detail="News-Reihenfolge ist unvollständig",
            )
        for position, news_id in enumerate(payload.item_ids, start=1):
            db.execute(
                "UPDATE news SET sort_order = ? WHERE id = ?",
                (position, news_id),
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
            WHERE id = ?
            """,
            (data, optimized_mime, row_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Entry not found")
        db.commit()
        row = db.execute("SELECT * FROM news WHERE id = ?", (row_id,)).fetchone()
    return _serialize_news(row)


@app.get("/api/news/{row_id}/image")
def get_news_image(
    row_id: int,
    _: dict[str, Any] = Depends(current_user),
) -> Response:
    with connect() as db:
        row = db.execute(
            "SELECT image_data, image_mime FROM news WHERE id = ?",
            (row_id,),
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
            WHERE id = ?
            """,
            (row_id,),
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
                GROUP BY event_id
                """
            ).fetchall()
        }
        mine = {
            row["event_id"]
            for row in db.execute(
                "SELECT event_id FROM event_registrations WHERE user_id = ?",
                (user["id"],),
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
        event = db.execute("SELECT id FROM events WHERE id = ?", (row_id,)).fetchone()
        if event is None:
            raise HTTPException(status_code=404, detail="Termin nicht gefunden")
        rows = db.execute(
            """
            SELECT COALESCE(NULLIF(m.name, ''), u.username) AS name
            FROM event_registrations r
            JOIN users u ON u.id = r.user_id
            LEFT JOIN members m ON m.id = u.member_id
            WHERE r.event_id = ? AND u.active = 1
            ORDER BY name COLLATE NOCASE
            """,
            (row_id,),
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/events/{row_id}/registration", status_code=204)
def register_for_event(
    row_id: int,
    user: dict[str, Any] = Depends(current_user),
) -> None:
    with connect() as db:
        event = db.execute("SELECT id FROM events WHERE id = ?", (row_id,)).fetchone()
        if event is None:
            raise HTTPException(status_code=404, detail="Termin nicht gefunden")
        db.execute(
            """
            INSERT OR IGNORE INTO event_registrations (event_id, user_id, created_at)
            VALUES (?, ?, ?)
            """,
            (row_id, user["id"], datetime.now(timezone.utc).isoformat()),
        )
        db.commit()


@app.delete("/api/events/{row_id}/registration", status_code=204)
def unregister_from_event(
    row_id: int,
    user: dict[str, Any] = Depends(current_user),
) -> None:
    with connect() as db:
        db.execute(
            "DELETE FROM event_registrations WHERE event_id = ? AND user_id = ?",
            (row_id, user["id"]),
        )
        db.commit()


@app.delete("/api/events/{row_id}", status_code=204)
def delete_events(
    row_id: int,
    _: dict[str, Any] = Depends(require("can_events")),
) -> None:
    with connect() as db:
        db.execute("DELETE FROM event_registrations WHERE event_id = ?", (row_id,))
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
            ORDER BY sort_order ASC, label COLLATE NOCASE ASC, id ASC
            """
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
            "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM member_filters"
        ).fetchone()[0]
        try:
            cursor = db.execute(
                """
                INSERT INTO member_filters (label, active, sort_order, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    payload.label.strip(),
                    1 if payload.active else 0,
                    sort_order,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            db.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Filter existiert bereits")
        row = db.execute(
            "SELECT id, label, active, sort_order FROM member_filters WHERE id = ?",
            (cursor.lastrowid,),
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
        ids = {int(row["id"]) for row in db.execute("SELECT id FROM member_filters")}
        if set(payload.item_ids) != ids:
            raise HTTPException(status_code=422, detail="Filterreihenfolge ist unvollständig")
        for position, filter_id in enumerate(payload.item_ids, start=1):
            db.execute(
                "UPDATE member_filters SET sort_order = ? WHERE id = ?",
                (position, filter_id),
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
                "UPDATE member_filters SET label = ?, active = ? WHERE id = ?",
                (payload.label.strip(), 1 if payload.active else 0, filter_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Filter nicht gefunden")
            db.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Filter existiert bereits")
        row = db.execute(
            "SELECT id, label, active, sort_order FROM member_filters WHERE id = ?",
            (filter_id,),
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
        db.execute("DELETE FROM member_filter_links WHERE filter_id = ?", (filter_id,))
        cursor = db.execute("DELETE FROM member_filters WHERE id = ?", (filter_id,))
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
            f"UPDATE members SET {assignments} WHERE id = ?",
            [*data.values(), member_id],
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Mitglied nicht gefunden")
        db.commit()
        row = db.execute(
            "SELECT * FROM members WHERE id = ?",
            (member_id,),
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
            WHERE id = ?
            """,
            (data, optimized_mime, member_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Mitglied nicht gefunden")
        db.commit()
        row = db.execute(
            "SELECT * FROM members WHERE id = ?",
            (member_id,),
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
            WHERE id = ?
            """,
            (member_id,),
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
        rows = db.execute(
            f"""
            SELECT id
            FROM members
            WHERE id IN ({",".join("?" for _ in payload.item_ids)})
            """,
            payload.item_ids,
        ).fetchall()

        if len(rows) != len(set(payload.item_ids)):
            raise HTTPException(status_code=422, detail="Mitgliederreihenfolge ist ungültig")

        current_ids = {
            row["id"] for row in db.execute("SELECT id FROM members").fetchall()
        }
        if set(payload.item_ids) != current_ids:
            raise HTTPException(
                status_code=422,
                detail="Mitgliederreihenfolge ist unvollständig",
            )

        for position, member_id in enumerate(payload.item_ids, start=1):
            db.execute(
                "UPDATE members SET sort_order = ? WHERE id = ?",
                (position, member_id),
            )
        db.commit()

    return list_rows("members")


@app.post("/api/members")
def post_members(
    payload: MemberPayload,
    _: dict[str, Any] = Depends(require("can_members")),
) -> dict[str, Any]:
    item = create_row("members", payload)
    with connect() as db:
        max_order = db.execute(
            "SELECT COALESCE(MAX(sort_order), 0) FROM members WHERE id != ?",
            (item["id"],),
        ).fetchone()[0]
        db.execute(
            "UPDATE members SET sort_order = ? WHERE id = ?",
            (int(max_order or 0) + 1, item["id"]),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM members WHERE id = ?",
            (item["id"],),
        ).fetchone()
    return _serialize_member(row)


@app.put("/api/members/order")
def reorder_members(
    payload: ContentOrderPayload,
    _: dict[str, Any] = Depends(require("can_members")),
) -> list[dict[str, Any]]:
    if not payload.item_ids:
        return []

    with connect() as db:
        rows = db.execute(
            f"SELECT id FROM members WHERE id IN ({','.join('?' for _ in payload.item_ids)})",
            payload.item_ids,
        ).fetchall()
        if len(rows) != len(set(payload.item_ids)):
            raise HTTPException(status_code=422, detail="Mitgliederreihenfolge ist ungültig")

        all_ids = [row["id"] for row in db.execute(
            "SELECT id FROM members ORDER BY sort_order ASC, name COLLATE NOCASE ASC, id ASC"
        ).fetchall()]
        if set(all_ids) != set(payload.item_ids):
            raise HTTPException(status_code=422, detail="Mitgliederreihenfolge ist unvollständig")

        for position, member_id in enumerate(payload.item_ids, start=1):
            db.execute(
                "UPDATE members SET sort_order = ? WHERE id = ?",
                (position, member_id),
            )
        db.commit()
        ordered = db.execute(
            "SELECT * FROM members ORDER BY sort_order ASC, name COLLATE NOCASE ASC, id ASC"
        ).fetchall()

    return [_serialize_member(row) for row in ordered]


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
            WHERE id = ?
            """,
            (data, optimized_mime, row_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Mitglied nicht gefunden")
        db.commit()
        row = db.execute(
            "SELECT * FROM members WHERE id = ?",
            (row_id,),
        ).fetchone()
    return _serialize_member(row)


@app.get("/api/members/{row_id}/photo")
def get_member_photo(
    row_id: int,
    _: dict[str, Any] = Depends(current_user),
) -> Response:
    with connect() as db:
        row = db.execute(
            "SELECT photo_data, photo_mime FROM members WHERE id = ?",
            (row_id,),
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
            WHERE id = ?
            """,
            (row_id,),
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
        db.execute("DELETE FROM member_filter_links WHERE member_id = ?", (row_id,))
        db.commit()
    delete_row("members", row_id)
