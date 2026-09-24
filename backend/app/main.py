import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field


DB_PATH = Path(os.getenv("FLAPAMAMAKU_DB", "/data/flapamamaku.db"))
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="FLAPAMAMAKU API",
    version="0.7.3",
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

        _ensure_column(db, "news", "image_data", "BLOB")
        _ensure_column(db, "news", "image_mime", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "events", "event_date", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "phone_mobile", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "phone_private", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "phone_work", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "occupation", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "members", "employer", "TEXT NOT NULL DEFAULT ''")

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
    return _serialize_news(row) if resource == "news" else dict(row)


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
    return _serialize_news(row) if resource == "news" else dict(row)


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


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "FLAPAMAMAKU API",
        "admin": "/admin",
        "docs": "/api/docs",
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.7.3"}


@app.get("/admin")
def admin() -> FileResponse:
    return FileResponse(STATIC_DIR / "admin.html")


@app.get("/api/news")
def get_news() -> list[dict[str, Any]]:
    return list_rows("news")


@app.post("/api/news")
def post_news(payload: NewsPayload) -> dict[str, Any]:
    return create_row("news", payload)


@app.put("/api/news/{row_id}")
def put_news(row_id: int, payload: NewsPayload) -> dict[str, Any]:
    return update_row("news", row_id, payload)


@app.delete("/api/news/{row_id}", status_code=204)
def delete_news(row_id: int) -> None:
    delete_row("news", row_id)




@app.post("/api/news/{row_id}/image")
async def upload_news_image(
    row_id: int,
    image: UploadFile = File(...),
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
def get_news_image(row_id: int) -> Response:
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
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.delete("/api/news/{row_id}/image", status_code=204)
def delete_news_image(row_id: int) -> None:
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
def get_events() -> list[dict[str, Any]]:
    return list_rows("events")


@app.post("/api/events")
def post_events(payload: EventPayload) -> dict[str, Any]:
    return create_row("events", payload)


@app.put("/api/events/{row_id}")
def put_events(row_id: int, payload: EventPayload) -> dict[str, Any]:
    return update_row("events", row_id, payload)


@app.delete("/api/events/{row_id}", status_code=204)
def delete_events(row_id: int) -> None:
    delete_row("events", row_id)


@app.get("/api/members")
def get_members() -> list[dict[str, Any]]:
    return list_rows("members")


@app.post("/api/members")
def post_members(payload: MemberPayload) -> dict[str, Any]:
    return create_row("members", payload)


@app.put("/api/members/{row_id}")
def put_members(row_id: int, payload: MemberPayload) -> dict[str, Any]:
    return update_row("members", row_id, payload)


@app.delete("/api/members/{row_id}", status_code=204)
def delete_members(row_id: int) -> None:
    delete_row("members", row_id)
