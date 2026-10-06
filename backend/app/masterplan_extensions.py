from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from . import main as main_app


class ExtendedEventPayload(BaseModel):
    event_date: str = ""
    day: str
    month: str
    title: str = Field(min_length=1, max_length=200)
    location: str = ""
    time: str = ""
    end_time: str = ""
    meeting_point: str = ""
    description: str = ""
    responsible: str = ""
    registration_deadline: str = ""
    registration_enabled: bool = True
    document_url: str = ""


class SujetPayload(BaseModel):
    year: int = Field(ge=1900, le=2200)
    title: str = Field(min_length=1, max_length=200)
    motto: str = Field(default="", max_length=300)
    text: str = ""
    is_current: bool = False


class ImageOrderPayload(BaseModel):
    image_ids: list[int]


def _columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {str(row["name"]) for row in db.execute(f"PRAGMA table_info({table})")}


def _ensure_column(db: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if column not in _columns(db, table):
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _year_from_legacy(row: sqlite3.Row, used: set[int]) -> int:
    title = str(row["title"] or "")
    match = re.search(r"\b(19\d{2}|20\d{2}|21\d{2})\b", title)
    if match:
        year = int(match.group(1))
    else:
        created = str(row["created_at"] or "")
        created_match = re.match(r"(\d{4})", created)
        year = int(created_match.group(1)) if created_match else datetime.now(timezone.utc).year
        if str(row["section"]) == "sujet":
            year += 1
    step = 1 if str(row["section"]) == "sujet" else -1
    while year in used:
        year += step
    used.add(year)
    return year


def _migrate_legacy_sujets(db: sqlite3.Connection) -> None:
    clubs = db.execute("SELECT id FROM clubs ORDER BY id").fetchall()
    content_columns = _columns(db, "content_items")
    image_columns = _columns(db, "content_images") if "content_images" in {
        str(r["name"]) for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    } else set()

    for club in clubs:
        club_id = int(club["id"])
        existing = int(
            db.execute("SELECT COUNT(*) FROM annual_sujets WHERE club_id = ?", (club_id,)).fetchone()[0]
        )
        if existing:
            continue
        rows = db.execute(
            """
            SELECT * FROM content_items
            WHERE club_id = ? AND section IN ('sujet','archive')
            ORDER BY CASE WHEN section='sujet' THEN 0 ELSE 1 END, sort_order ASC, id ASC
            """,
            (club_id,),
        ).fetchall()
        if not rows:
            continue
        used: set[int] = set()
        current_assigned = False
        for row in rows:
            year = _year_from_legacy(row, used)
            is_current = str(row["section"]) == "sujet" and not current_assigned
            current_assigned = current_assigned or is_current
            created_at = str(row["created_at"] or datetime.now(timezone.utc).isoformat())
            cursor = db.execute(
                """
                INSERT INTO annual_sujets(
                    club_id,year,title,motto,text,is_current,sort_order,created_at,updated_at,migrated_content_id
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    club_id,
                    year,
                    str(row["title"] or "Sujet").strip() or "Sujet",
                    "",
                    str(row["text"] or ""),
                    1 if is_current else 0,
                    int(row["sort_order"] or row["id"] or 0),
                    created_at,
                    created_at,
                    int(row["id"]),
                ),
            )
            sujet_id = int(cursor.lastrowid)
            image_rows: list[sqlite3.Row] = []
            if image_columns:
                image_rows = db.execute(
                    """
                    SELECT * FROM content_images
                    WHERE content_id = ? AND club_id = ?
                    ORDER BY sort_order ASC, id ASC
                    """,
                    (int(row["id"]), club_id),
                ).fetchall()
            for image in image_rows:
                if not image["image_data"]:
                    continue
                db.execute(
                    """
                    INSERT INTO annual_sujet_images(
                        sujet_id,club_id,image_data,image_mime,sort_order,created_at
                    ) VALUES (?,?,?,?,?,?)
                    """,
                    (
                        sujet_id,
                        club_id,
                        image["image_data"],
                        str(image["image_mime"] or "image/jpeg"),
                        int(image["sort_order"] or 0),
                        str(image["created_at"] or created_at),
                    ),
                )
            if not image_rows and {"image_data", "image_mime"}.issubset(content_columns) and row["image_data"]:
                db.execute(
                    """
                    INSERT INTO annual_sujet_images(
                        sujet_id,club_id,image_data,image_mime,sort_order,created_at
                    ) VALUES (?,?,?,?,1,?)
                    """,
                    (
                        sujet_id,
                        club_id,
                        row["image_data"],
                        str(row["image_mime"] or "image/jpeg"),
                        created_at,
                    ),
                )


def init_masterplan_schema() -> None:
    with main_app.connect() as db:
        for column, definition in {
            "end_time": "TEXT NOT NULL DEFAULT ''",
            "meeting_point": "TEXT NOT NULL DEFAULT ''",
            "description": "TEXT NOT NULL DEFAULT ''",
            "responsible": "TEXT NOT NULL DEFAULT ''",
            "registration_deadline": "TEXT NOT NULL DEFAULT ''",
            "registration_enabled": "INTEGER NOT NULL DEFAULT 1",
            "document_url": "TEXT NOT NULL DEFAULT ''",
        }.items():
            _ensure_column(db, "events", column, definition)

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS annual_sujets(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                club_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                title TEXT NOT NULL,
                motto TEXT NOT NULL DEFAULT '',
                text TEXT NOT NULL DEFAULT '',
                logo_data BLOB,
                logo_mime TEXT NOT NULL DEFAULT '',
                is_current INTEGER NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                migrated_content_id INTEGER,
                UNIQUE(club_id, year),
                FOREIGN KEY(club_id) REFERENCES clubs(id)
            )
            """
        )
        db.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS annual_sujets_one_current_per_club
            ON annual_sujets(club_id) WHERE is_current = 1
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS annual_sujet_images(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sujet_id INTEGER NOT NULL,
                club_id INTEGER NOT NULL,
                image_data BLOB NOT NULL,
                image_mime TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(sujet_id) REFERENCES annual_sujets(id),
                FOREIGN KEY(club_id) REFERENCES clubs(id)
            )
            """
        )
        db.execute("CREATE INDEX IF NOT EXISTS annual_sujets_club_idx ON annual_sujets(club_id, year)")
        db.execute("CREATE INDEX IF NOT EXISTS annual_sujet_images_club_idx ON annual_sujet_images(club_id, sujet_id)")
        _migrate_legacy_sujets(db)
        db.commit()


def _club_id() -> int:
    with main_app.connect() as db:
        return int(main_app._active_club_id(db))


def _serialize_sujet(row: sqlite3.Row) -> dict[str, Any]:
    club_id = int(row["club_id"])
    with main_app.connect() as db:
        images = db.execute(
            """
            SELECT id,sort_order,created_at FROM annual_sujet_images
            WHERE sujet_id=? AND club_id=? ORDER BY sort_order ASC,id ASC
            """,
            (int(row["id"]), club_id),
        ).fetchall()
    image_items = [
        {
            "id": int(image["id"]),
            "url": f"/api/sujets/{int(row['id'])}/images/{int(image['id'])}",
            "sort_order": int(image["sort_order"] or 0),
            "created_at": str(image["created_at"] or ""),
        }
        for image in images
    ]
    urls = [item["url"] for item in image_items]
    return {
        "id": int(row["id"]),
        "club_id": club_id,
        "annual_sujet": True,
        "year": int(row["year"]),
        "is_current": bool(row["is_current"]),
        "section": "sujet" if row["is_current"] else "archive",
        "title": str(row["title"] or ""),
        "motto": str(row["motto"] or ""),
        "text": str(row["text"] or ""),
        "logo_url": f"/api/sujets/{int(row['id'])}/logo" if row["logo_data"] else "",
        "sort_order": int(row["sort_order"] or 0),
        "created_at": str(row["created_at"] or ""),
        "updated_at": str(row["updated_at"] or ""),
        "images": image_items,
        "image_urls": urls,
        "image_url": urls[0] if urls else "",
    }


def _sujet_row(sujet_id: int, club_id: int) -> sqlite3.Row:
    with main_app.connect() as db:
        row = db.execute(
            "SELECT * FROM annual_sujets WHERE id=? AND club_id=?",
            (sujet_id, club_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Sujet nicht gefunden")
    return row


def _find_route(path: str, method: str) -> tuple[Any, Callable[..., Any]] | tuple[None, None]:
    for route in list(main_app.app.router.routes):
        if getattr(route, "path", None) == path and method in (getattr(route, "methods", set()) or set()):
            return route, route.endpoint
    return None, None


def _remove_route(route: Any) -> None:
    if route is not None and route in main_app.app.router.routes:
        main_app.app.router.routes.remove(route)


def install_masterplan_extensions() -> None:
    if getattr(main_app.app.state, "recovery_masterplan_extensions", False):
        return
    main_app.app.state.recovery_masterplan_extensions = True

    @main_app.app.on_event("startup")
    async def _masterplan_startup() -> None:
        init_masterplan_schema()

    # Block obsolete Sujet/archive writes while preserving all other stable CRUD.
    content_route, content_endpoint = _find_route("/api/content", "POST")
    if content_endpoint is not None:
        _remove_route(content_route)

        @main_app.app.post("/api/content")
        def guarded_content_post(
            payload: main_app.ContentPayload,
            user: dict[str, Any] = Depends(main_app.current_user),
        ) -> dict[str, Any]:
            if payload.section in {"sujet", "archive"}:
                raise HTTPException(
                    status_code=409,
                    detail="Sujet-Inhalte werden über die Jahres-Sujet-Verwaltung gepflegt.",
                )
            return content_endpoint(payload, user)

    # Extend event create/update while reusing stable multi-club CRUD + push logic.
    post_route, post_endpoint = _find_route("/api/events", "POST")
    if post_endpoint is not None:
        _remove_route(post_route)

        @main_app.app.post("/api/events")
        def extended_post_event(
            payload: ExtendedEventPayload,
            user: dict[str, Any] = Depends(main_app.require("can_events")),
        ) -> dict[str, Any]:
            return post_endpoint(payload, user)

    put_route, put_endpoint = _find_route("/api/events/{row_id}", "PUT")
    if put_endpoint is not None:
        _remove_route(put_route)

        @main_app.app.put("/api/events/{row_id}")
        def extended_put_event(
            row_id: int,
            payload: ExtendedEventPayload,
            user: dict[str, Any] = Depends(main_app.require("can_events")),
        ) -> dict[str, Any]:
            return put_endpoint(row_id, payload, user)

    registration_route, registration_endpoint = _find_route("/api/events/{row_id}/registration", "POST")
    if registration_endpoint is not None:
        _remove_route(registration_route)

        @main_app.app.post("/api/events/{row_id}/registration", status_code=204)
        def guarded_event_registration(
            row_id: int,
            user: dict[str, Any] = Depends(main_app.current_user),
        ) -> None:
            with main_app.connect() as db:
                club_id = int(main_app._active_club_id(db))
                event = db.execute(
                    """
                    SELECT registration_enabled,registration_deadline
                    FROM events WHERE id=? AND club_id=?
                    """,
                    (row_id, club_id),
                ).fetchone()
            if event is None:
                raise HTTPException(status_code=404, detail="Termin nicht gefunden")
            if not bool(event["registration_enabled"]):
                raise HTTPException(status_code=409, detail="Für diesen Termin ist keine Anmeldung möglich")
            deadline = str(event["registration_deadline"] or "").strip()
            if deadline:
                try:
                    value = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                    if value.tzinfo is None:
                        value = value.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) > value.astimezone(timezone.utc):
                        raise HTTPException(status_code=409, detail="Der Anmeldeschluss ist abgelaufen")
                except ValueError:
                    pass
            return registration_endpoint(row_id, user)

    @main_app.app.get("/api/sujets")
    def list_sujets(
        scope: str = "all",
        _: dict[str, Any] = Depends(main_app.current_user),
    ) -> list[dict[str, Any]]:
        if scope not in {"all", "current", "archive"}:
            raise HTTPException(status_code=422, detail="Unbekannter Sujet-Bereich")
        club_id = _club_id()
        sql = "SELECT * FROM annual_sujets WHERE club_id=?"
        params: list[Any] = [club_id]
        if scope == "current":
            sql += " AND is_current=1"
        elif scope == "archive":
            sql += " AND is_current=0"
        sql += " ORDER BY is_current DESC,year DESC,sort_order ASC,id DESC"
        with main_app.connect() as db:
            rows = db.execute(sql, params).fetchall()
        return [_serialize_sujet(row) for row in rows]

    @main_app.app.get("/api/sujets/current")
    def current_sujet(_: dict[str, Any] = Depends(main_app.current_user)) -> dict[str, Any]:
        club_id = _club_id()
        with main_app.connect() as db:
            row = db.execute(
                "SELECT * FROM annual_sujets WHERE club_id=? AND is_current=1 ORDER BY year DESC,id DESC LIMIT 1",
                (club_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Kein aktuelles Sujet vorhanden")
        return _serialize_sujet(row)

    @main_app.app.post("/api/sujets")
    def create_sujet(
        payload: SujetPayload,
        _: dict[str, Any] = Depends(main_app.require("can_photos")),
    ) -> dict[str, Any]:
        club_id = _club_id()
        now = datetime.now(timezone.utc).isoformat()
        with main_app.connect() as db:
            if payload.is_current:
                db.execute("UPDATE annual_sujets SET is_current=0,updated_at=? WHERE club_id=?", (now, club_id))
            next_order = int(
                db.execute("SELECT COALESCE(MAX(sort_order),0)+1 FROM annual_sujets WHERE club_id=?", (club_id,)).fetchone()[0]
            )
            try:
                cursor = db.execute(
                    """
                    INSERT INTO annual_sujets(
                        club_id,year,title,motto,text,is_current,sort_order,created_at,updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        club_id,payload.year,payload.title.strip(),payload.motto.strip(),payload.text.strip(),
                        1 if payload.is_current else 0,next_order,now,now,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise HTTPException(status_code=409, detail="Für dieses Jahr existiert bereits ein Sujet") from exc
            db.commit()
            row = db.execute("SELECT * FROM annual_sujets WHERE id=?", (int(cursor.lastrowid),)).fetchone()
        return _serialize_sujet(row)

    @main_app.app.put("/api/sujets/{sujet_id}")
    def update_sujet(
        sujet_id: int,
        payload: SujetPayload,
        _: dict[str, Any] = Depends(main_app.require("can_photos")),
    ) -> dict[str, Any]:
        club_id = _club_id()
        now = datetime.now(timezone.utc).isoformat()
        with main_app.connect() as db:
            existing = db.execute("SELECT id FROM annual_sujets WHERE id=? AND club_id=?", (sujet_id,club_id)).fetchone()
            if existing is None:
                raise HTTPException(status_code=404, detail="Sujet nicht gefunden")
            if payload.is_current:
                db.execute("UPDATE annual_sujets SET is_current=0,updated_at=? WHERE club_id=? AND id<>?", (now,club_id,sujet_id))
            try:
                db.execute(
                    """
                    UPDATE annual_sujets SET year=?,title=?,motto=?,text=?,is_current=?,updated_at=?
                    WHERE id=? AND club_id=?
                    """,
                    (payload.year,payload.title.strip(),payload.motto.strip(),payload.text.strip(),1 if payload.is_current else 0,now,sujet_id,club_id),
                )
            except sqlite3.IntegrityError as exc:
                raise HTTPException(status_code=409, detail="Für dieses Jahr existiert bereits ein Sujet") from exc
            db.commit()
            row = db.execute("SELECT * FROM annual_sujets WHERE id=? AND club_id=?", (sujet_id,club_id)).fetchone()
        return _serialize_sujet(row)

    @main_app.app.delete("/api/sujets/{sujet_id}", status_code=204)
    def delete_sujet(
        sujet_id: int,
        _: dict[str, Any] = Depends(main_app.require("can_photos")),
    ) -> None:
        club_id = _club_id()
        with main_app.connect() as db:
            row = db.execute("SELECT id FROM annual_sujets WHERE id=? AND club_id=?", (sujet_id,club_id)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Sujet nicht gefunden")
            db.execute("DELETE FROM annual_sujet_images WHERE sujet_id=? AND club_id=?", (sujet_id,club_id))
            db.execute("DELETE FROM annual_sujets WHERE id=? AND club_id=?", (sujet_id,club_id))
            db.commit()

    @main_app.app.post("/api/sujets/{sujet_id}/logo")
    async def upload_sujet_logo(
        sujet_id: int,
        logo: UploadFile = File(...),
        _: dict[str, Any] = Depends(main_app.require("can_photos")),
    ) -> dict[str, Any]:
        club_id = _club_id()
        raw = await logo.read()
        if not raw:
            raise HTTPException(status_code=422, detail="Leere Logo-Datei")
        optimized, mime = main_app._optimize_image(raw, logo.content_type or "image/jpeg")
        with main_app.connect() as db:
            cursor = db.execute(
                "UPDATE annual_sujets SET logo_data=?,logo_mime=?,updated_at=? WHERE id=? AND club_id=?",
                (optimized,mime,datetime.now(timezone.utc).isoformat(),sujet_id,club_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Sujet nicht gefunden")
            db.commit()
            row = db.execute("SELECT * FROM annual_sujets WHERE id=? AND club_id=?", (sujet_id,club_id)).fetchone()
        return _serialize_sujet(row)

    @main_app.app.get("/api/sujets/{sujet_id}/logo")
    def get_sujet_logo(
        sujet_id: int,
        _: dict[str, Any] = Depends(main_app.current_user),
    ) -> Response:
        row = _sujet_row(sujet_id, _club_id())
        if not row["logo_data"]:
            raise HTTPException(status_code=404, detail="Sujet-Logo nicht gefunden")
        return Response(content=row["logo_data"], media_type=str(row["logo_mime"] or "image/jpeg"))

    @main_app.app.delete("/api/sujets/{sujet_id}/logo", status_code=204)
    def delete_sujet_logo(
        sujet_id: int,
        _: dict[str, Any] = Depends(main_app.require("can_photos")),
    ) -> None:
        club_id = _club_id()
        with main_app.connect() as db:
            cursor = db.execute(
                "UPDATE annual_sujets SET logo_data=NULL,logo_mime='',updated_at=? WHERE id=? AND club_id=?",
                (datetime.now(timezone.utc).isoformat(),sujet_id,club_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Sujet nicht gefunden")
            db.commit()

    @main_app.app.post("/api/sujets/{sujet_id}/images")
    async def upload_sujet_images(
        sujet_id: int,
        images: list[UploadFile] = File(...),
        _: dict[str, Any] = Depends(main_app.require("can_photos")),
    ) -> dict[str, Any]:
        club_id = _club_id()
        _sujet_row(sujet_id, club_id)
        with main_app.connect() as db:
            next_order = int(
                db.execute("SELECT COALESCE(MAX(sort_order),0)+1 FROM annual_sujet_images WHERE sujet_id=? AND club_id=?", (sujet_id,club_id)).fetchone()[0]
            )
            for image in images:
                raw = await image.read()
                if not raw:
                    continue
                optimized,mime = main_app._optimize_image(raw,image.content_type or "image/jpeg")
                db.execute(
                    """
                    INSERT INTO annual_sujet_images(sujet_id,club_id,image_data,image_mime,sort_order,created_at)
                    VALUES (?,?,?,?,?,?)
                    """,
                    (sujet_id,club_id,optimized,mime,next_order,datetime.now(timezone.utc).isoformat()),
                )
                next_order += 1
            db.commit()
            row = db.execute("SELECT * FROM annual_sujets WHERE id=? AND club_id=?", (sujet_id,club_id)).fetchone()
        return _serialize_sujet(row)

    @main_app.app.get("/api/sujets/{sujet_id}/images/{image_id}")
    def get_sujet_image(
        sujet_id: int,
        image_id: int,
        _: dict[str, Any] = Depends(main_app.current_user),
    ) -> Response:
        club_id = _club_id()
        with main_app.connect() as db:
            row = db.execute(
                "SELECT image_data,image_mime FROM annual_sujet_images WHERE id=? AND sujet_id=? AND club_id=?",
                (image_id,sujet_id,club_id),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Sujet-Bild nicht gefunden")
        return Response(content=row["image_data"],media_type=str(row["image_mime"] or "image/jpeg"))

    @main_app.app.delete("/api/sujets/{sujet_id}/images/{image_id}", status_code=204)
    def delete_sujet_image(
        sujet_id: int,
        image_id: int,
        _: dict[str, Any] = Depends(main_app.require("can_photos")),
    ) -> None:
        club_id = _club_id()
        with main_app.connect() as db:
            cursor = db.execute(
                "DELETE FROM annual_sujet_images WHERE id=? AND sujet_id=? AND club_id=?",
                (image_id,sujet_id,club_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Sujet-Bild nicht gefunden")
            db.commit()
