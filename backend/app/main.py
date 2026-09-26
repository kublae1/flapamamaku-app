import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field


DB_PATH = Path(os.getenv("FLAPAMAMAKU_DB", "/data/flapamamaku.db"))
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
SESSION_DAYS = 30

app = FastAPI(
    title="FLAPAMAMAKU API",
    version="0.8.10",
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


PERMISSION_FIELDS = (
    "can_news",
    "can_events",
    "can_members",
    "can_documents",
    "can_photos",
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
    can_polls: bool = False
    can_links: bool = False
    can_contact: bool = False
    can_about: bool = False
    can_admin_page: bool = False
    can_manage_users: bool = False


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
                created_at TEXT NOT NULL,
                FOREIGN KEY(content_id) REFERENCES content_items(id)
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


@app.on_event("startup")
def startup() -> None:
    init_db()


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
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        row = db.execute(
            """
            SELECT u.*
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > ? AND u.active = 1
            """,
            (_token_hash(token), now),
        ).fetchone()
        db.commit()
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
    "contact": "can_contact",
    "about": "can_about",
}


def _serialize_content(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    has_legacy_image = bool(item.pop("image_data", None))
    item.pop("image_mime", None)
    image_urls: list[str] = []
    if has_legacy_image:
        image_urls.append(f"/api/content/{item['id']}/image")
    with connect() as db:
        image_rows = db.execute(
            "SELECT id FROM content_images WHERE content_id = ? ORDER BY id ASC",
            (item["id"],),
        ).fetchall()
    image_urls.extend(
        f"/api/content/{item['id']}/images/{image_row['id']}"
        for image_row in image_rows
    )
    item["image_urls"] = image_urls
    item["image_url"] = image_urls[0] if image_urls else ""
    return item


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
    return {"status": "ok", "version": "0.8.10"}


@app.get("/admin")
def admin() -> FileResponse:
    return FileResponse(STATIC_DIR / "admin.html")


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
        expires = now_dt + timedelta(days=SESSION_DAYS)
        db.execute(
            """
            INSERT INTO sessions (token_hash, user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                _token_hash(token),
                row["id"],
                expires.isoformat(),
                now_dt.isoformat(),
            ),
        )
        db.commit()

    return {
        "token": token,
        "expires_at": expires.isoformat(),
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
            db.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Benutzername bereits vorhanden")
    return _user_profile(user_id)


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


@app.get("/api/content")
def get_content(
    section: str | None = None,
    _: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM content_items"
    values: list[Any] = []
    if section:
        _content_permission(section)
        sql += " WHERE section = ?"
        values.append(section)
    sql += " ORDER BY created_at DESC, id DESC"

    with connect() as db:
        rows = db.execute(sql, values).fetchall()
    return [_serialize_content(row) for row in rows]


@app.post("/api/content")
def post_content(
    payload: ContentPayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    _require_content_permission(payload.section, user)
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        cursor = db.execute(
            """
            INSERT INTO content_items (
                section, title, text, link_url, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (payload.section, payload.title, payload.text, payload.link_url, now),
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
        db.executemany(
            """
            INSERT INTO content_images (
                content_id, image_data, image_mime, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            [(row_id, data, mime, now) for data, mime in prepared],
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
    return create_row("news", payload)


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
    return create_row("events", payload)


@app.put("/api/events/{row_id}")
def put_events(
    row_id: int,
    payload: EventPayload,
    _: dict[str, Any] = Depends(require("can_events")),
) -> dict[str, Any]:
    return update_row("events", row_id, payload)


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
