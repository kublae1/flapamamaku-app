import asyncio
import base64
import hashlib
import hmac
import json
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


DB_PATH = Path(os.getenv("FLAPAMAMAKU_DB", "/data/flapamamaku.db"))
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
SESSION_EXPIRES_AT = "9999-12-31T23:59:59+00:00"
API_VERSION = "0.8.20"
APP_ENV = os.getenv("FLAPAMAMAKU_ENV", "development").strip().lower()
IS_PRODUCTION = APP_ENV == "production"
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
    partner_name: str = ""
    phone_mobile: str = ""
    phone_private: str = ""
    phone_work: str = ""
    email: str = ""
    address: str = ""
    occupation: str = ""
    employer: str = ""
    employer_url: str = ""


class ContentPayload(BaseModel):
    section: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=200)
    text: str = ""
    link_url: str = ""


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
            partner_name TEXT NOT NULL DEFAULT '',
            phone_mobile TEXT NOT NULL DEFAULT '',
            phone_private TEXT NOT NULL DEFAULT '',
            phone_work TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            address TEXT NOT NULL DEFAULT '',
            occupation TEXT NOT NULL DEFAULT '',
            employer TEXT NOT NULL DEFAULT '',
            employer_url TEXT NOT NULL DEFAULT '',
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
        _ensure_column(db, "events", "event_date", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "phone_mobile", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "phone_private", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "phone_work", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "occupation", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "employer", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "employer_url", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "photo_data", "BLOB")
        _ensure_column(db, "members", "photo_mime", "TEXT NOT NULL DEFAULT ''")
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
            return None
        return credentials.token, project_id
    except Exception:
        return None


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
    return item


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
        order = "created_at DESC, id DESC"
    elif resource == "events":
        order = (
            "CASE WHEN event_date = '' THEN '9999-12-31' ELSE event_date END ASC, "
            "time ASC, id ASC"
        )
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
    data["created_at"] = datetime.now(timezone.utc).isoformat()
    columns = list(data.keys())
    placeholders = ", ".join("?" for _ in columns)
    sql = (
        f"INSERT INTO {resource} ({', '.join(columns)}) "
        f"VALUES ({placeholders})"
    )
    with connect() as db:
        cursor = db.execute(sql, [data[column] for column in columns])
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
    assignments = ", ".join(f"{column} = ?" for column in data)
    with connect() as db:
        cursor = db.execute(
            f"UPDATE {resource} SET {assignments} WHERE id = ?",
            [*data.values(), row_id],
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Entry not found")
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
    "motto": "can_photos",
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


def _serialize_content(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item.pop("image_data", None)
    item.pop("image_mime", None)
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
    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty image")
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large")

    mime = image.content_type or ""
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        if data.startswith(b"\xff\xd8\xff"):
            mime = "image/jpeg"
        elif data.startswith(b"\x89PNG\r\n\x1a\n"):
            mime = "image/png"
        elif len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            mime = "image/webp"
        else:
            raise HTTPException(status_code=415, detail="Unsupported image type")

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
        queued = db.execute(
            "SELECT COUNT(*) FROM push_notifications WHERE sent_at IS NULL",
        ).fetchone()[0]
    return {
        "registered_devices": count,
        "queued_notifications": queued,
        "delivery_configured": bool(FIREBASE_SERVICE_ACCOUNT_JSON),
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

    items = [_serialize_content(row) for row in rows]
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
                section, title, text, link_url, sort_order, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.section,
                payload.title,
                payload.text,
                payload.link_url,
                max_order + 1,
                now,
            ),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM content_items WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return _serialize_content(row)


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
        db.execute(
            """
            UPDATE content_items
            SET section = ?, title = ?, text = ?, link_url = ?
            WHERE id = ?
            """,
            (
                payload.section,
                payload.title,
                payload.text,
                payload.link_url,
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
        db.execute("DELETE FROM content_items WHERE id = ?", (row_id,))
        db.commit()


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
        data = await image.read()
        if not data:
            raise HTTPException(status_code=400, detail="Empty image")
        if len(data) > 12 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Image too large")
        prepared.append((data, image.content_type or "application/octet-stream"))

    with connect() as db:
        existing = db.execute(
            "SELECT * FROM content_items WHERE id = ?",
            (row_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
        _require_content_permission(existing["section"], user)
        now = datetime.now(timezone.utc).isoformat()
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

    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty image")
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large")

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
            (data, image.content_type, row_id),
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

    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty image")
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large")

    with connect() as db:
        cursor = db.execute(
            """
            UPDATE news
            SET image_data = ?, image_mime = ?, image_url = ''
            WHERE id = ?
            """,
            (data, image.content_type, row_id),
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


@app.get("/api/members")
def get_members(
    _: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    return list_rows("members")


@app.post("/api/members")
def post_members(
    payload: MemberPayload,
    _: dict[str, Any] = Depends(require("can_members")),
) -> dict[str, Any]:
    return create_row("members", payload)


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

    data = await photo.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty image")
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large")

    with connect() as db:
        cursor = db.execute(
            """
            UPDATE members
            SET photo_data = ?, photo_mime = ?
            WHERE id = ?
            """,
            (data, photo.content_type, row_id),
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
    delete_row("members", row_id)
