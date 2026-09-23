import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


DB_PATH = Path(os.getenv("FLAPAMAMAKU_DB", "/data/flapamamaku.db"))
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="FLAPAMAMAKU API",
    version="0.7.0",
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
    phone: str = ""
    email: str = ""
    address: str = ""


TABLES: dict[str, tuple[str, type[BaseModel]]] = {
    "news": (
        """
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            text TEXT NOT NULL,
            date TEXT NOT NULL,
            image_url TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """,
        NewsPayload,
    ),
    "events": (
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            phone TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            address TEXT NOT NULL DEFAULT '',
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


def init_db() -> None:
    with connect() as db:
        for ddl, _ in TABLES.values():
            db.execute(ddl)
        db.commit()


@app.on_event("startup")
def startup() -> None:
    init_db()


def table_or_404(name: str) -> tuple[str, type[BaseModel]]:
    table = TABLES.get(name)
    if table is None:
        raise HTTPException(status_code=404, detail="Unknown resource")
    return table


def list_rows(resource: str) -> list[dict[str, Any]]:
    table_or_404(resource)
    order = "created_at DESC, id DESC" if resource == "news" else "id DESC"
    with connect() as db:
        rows = db.execute(
            f"SELECT * FROM {resource} ORDER BY {order}"
        ).fetchall()
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


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "FLAPAMAMAKU API",
        "admin": "/admin",
        "docs": "/api/docs",
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.7.0"}


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
