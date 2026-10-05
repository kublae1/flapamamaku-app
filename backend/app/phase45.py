from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field


class SujetPayload(BaseModel):
    year: int = Field(ge=1900, le=2200)
    title: str = Field(min_length=1, max_length=200)
    motto: str = Field(default="", max_length=300)
    text: str = ""
    is_current: bool = False


class ImageOrderPayload(BaseModel):
    image_ids: list[int]


def install_phase45(
    app: Any,
    *,
    connect: Callable[[], sqlite3.Connection],
    current_user: Callable[..., dict[str, Any]],
    require: Callable[[str], Any],
    optimize_image: Callable[[bytes, str], tuple[bytes, str]],
    instance_id: str,
    is_production: bool,
) -> None:
    """Install Phase 4 annual-sujet model and Phase 5 tenant guard.

    One backend process still represents exactly one autonomous club database.
    The tenant guard prevents an app/admin client configured for another club
    from silently crossing the instance boundary. Security-sensitive session
    and device rows are additionally bound to the configured instance ID.
    """

    if getattr(app.state, "phase45_installed", False):
        return
    app.state.phase45_installed = True

    def columns(db: sqlite3.Connection, table: str) -> set[str]:
        return {str(row["name"]) for row in db.execute(f"PRAGMA table_info({table})")}

    def ensure_column(
        db: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        if column not in columns(db, table):
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def migrate_legacy_sujets(db: sqlite3.Connection) -> None:
        existing = int(db.execute("SELECT COUNT(*) FROM annual_sujets").fetchone()[0])
        if existing:
            return

        rows = db.execute(
            """
            SELECT *
            FROM content_items
            WHERE section IN ('sujet', 'archive')
            ORDER BY CASE WHEN section = 'sujet' THEN 0 ELSE 1 END,
                     sort_order ASC, id ASC
            """
        ).fetchall()
        if not rows:
            return

        used_years: set[int] = set()
        current_assigned = False
        now_year = datetime.now(timezone.utc).year
        for row in rows:
            title = str(row["title"] or "").strip() or "Sujet"
            match = re.search(r"\b(19\d{2}|20\d{2}|21\d{2})\b", title)
            if match:
                year = int(match.group(1))
            else:
                created = str(row["created_at"] or "")
                created_match = re.match(r"(\d{4})", created)
                if created_match:
                    year = int(created_match.group(1))
                else:
                    year = now_year + (1 if row["section"] == "sujet" else 0)

            if row["section"] == "archive":
                while year in used_years:
                    year -= 1
            else:
                while year in used_years:
                    year += 1
            used_years.add(year)

            is_current = row["section"] == "sujet" and not current_assigned
            current_assigned = current_assigned or is_current
            created_at = str(row["created_at"] or datetime.now(timezone.utc).isoformat())
            cursor = db.execute(
                """
                INSERT INTO annual_sujets (
                    year, title, text, is_current, sort_order,
                    created_at, updated_at, migrated_content_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    year,
                    title,
                    str(row["text"] or ""),
                    1 if is_current else 0,
                    int(row["sort_order"] or row["id"] or 0),
                    created_at,
                    created_at,
                    int(row["id"]),
                ),
            )
            sujet_id = int(cursor.lastrowid)

            image_rows = db.execute(
                """
                SELECT image_data, image_mime, sort_order, created_at
                FROM content_images
                WHERE content_id = ?
                ORDER BY sort_order ASC, id ASC
                """,
                (row["id"],),
            ).fetchall()
            for image in image_rows:
                db.execute(
                    """
                    INSERT INTO annual_sujet_images (
                        sujet_id, image_data, image_mime, sort_order, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        sujet_id,
                        image["image_data"],
                        image["image_mime"],
                        int(image["sort_order"] or 0),
                        str(image["created_at"] or created_at),
                    ),
                )

            if not image_rows and row["image_data"]:
                db.execute(
                    """
                    INSERT INTO annual_sujet_images (
                        sujet_id, image_data, image_mime, sort_order, created_at
                    ) VALUES (?, ?, ?, 1, ?)
                    """,
                    (
                        sujet_id,
                        row["image_data"],
                        str(row["image_mime"] or "image/jpeg"),
                        created_at,
                    ),
                )

    def init_phase45() -> None:
        with connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS annual_sujets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    motto TEXT NOT NULL DEFAULT '',
                    text TEXT NOT NULL DEFAULT '',
                    logo_data BLOB,
                    logo_mime TEXT NOT NULL DEFAULT '',
                    is_current INTEGER NOT NULL DEFAULT 0,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    migrated_content_id INTEGER
                )
                """
            )
            db.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS annual_sujets_one_current
                ON annual_sujets(is_current)
                WHERE is_current = 1
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS annual_sujet_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sujet_id INTEGER NOT NULL,
                    image_data BLOB NOT NULL,
                    image_mime TEXT NOT NULL DEFAULT '',
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(sujet_id) REFERENCES annual_sujets(id)
                )
                """
            )
            ensure_column(db, "annual_sujets", "motto", "TEXT NOT NULL DEFAULT ''")
            ensure_column(db, "annual_sujets", "logo_data", "BLOB")
            ensure_column(db, "annual_sujets", "logo_mime", "TEXT NOT NULL DEFAULT ''")

            tenant_tables = [
                "news", "events", "members", "member_filters", "content_items",
                "content_images", "event_registrations", "users", "sessions",
                "push_tokens", "annual_sujets", "annual_sujet_images",
            ]
            for table in tenant_tables:
                exists = db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
                    (table,),
                ).fetchone()
                if exists is None:
                    continue
                ensure_column(
                    db,
                    table,
                    "club_id",
                    f"TEXT NOT NULL DEFAULT '{instance_id}'",
                )
                db.execute(
                    f"UPDATE {table} SET club_id = ? WHERE club_id = '' OR club_id IS NULL",
                    (instance_id,),
                )
                db.execute(
                    f"CREATE INDEX IF NOT EXISTS {table}_club_id_idx ON {table}(club_id)"
                )
                safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", table)
                db.execute(
                    f"""
                    CREATE TRIGGER IF NOT EXISTS {safe_name}_club_guard_insert
                    BEFORE INSERT ON {table}
                    WHEN NEW.club_id <> '{instance_id}'
                    BEGIN
                      SELECT RAISE(ABORT, 'wrong club_id');
                    END
                    """
                )
                db.execute(
                    f"""
                    CREATE TRIGGER IF NOT EXISTS {safe_name}_club_guard_update
                    BEFORE UPDATE OF club_id ON {table}
                    WHEN NEW.club_id <> '{instance_id}'
                    BEGIN
                      SELECT RAISE(ABORT, 'wrong club_id');
                    END
                    """
                )

            ensure_column(
                db,
                "sessions",
                "instance_id",
                f"TEXT NOT NULL DEFAULT '{instance_id}'",
            )
            ensure_column(
                db,
                "push_tokens",
                "instance_id",
                f"TEXT NOT NULL DEFAULT '{instance_id}'",
            )
            db.execute(
                "UPDATE sessions SET instance_id = ? WHERE instance_id = ''",
                (instance_id,),
            )
            db.execute(
                "UPDATE push_tokens SET instance_id = ? WHERE instance_id = ''",
                (instance_id,),
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS sessions_instance_idx ON sessions(instance_id, token_hash)"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS push_tokens_instance_idx ON push_tokens(instance_id, enabled)"
            )
            migrate_legacy_sujets(db)
            now = datetime.now(timezone.utc).isoformat()
            db.execute(
                """
                INSERT OR IGNORE INTO schema_migrations(version, name, applied_at)
                VALUES (9, 'annual-sujet-domain-model', ?)
                """,
                (now,),
            )
            db.execute(
                """
                INSERT OR IGNORE INTO schema_migrations(version, name, applied_at)
                VALUES (10, 'tenant-session-device-binding', ?)
                """,
                (now,),
            )
            db.commit()

    app.state.phase45_initializer = init_phase45

    @app.on_event("startup")
    async def phase45_startup() -> None:
        init_phase45()

    public_without_tenant = {
        "/api/health",
        "/api/app-config",
        "/api/app-config/logo",
    }

    @app.middleware("http")
    async def tenant_guard(request: Request, call_next: Callable[..., Any]) -> Response:
        path = request.url.path
        supplied = request.headers.get("x-club-instance", "").strip().lower()
        if supplied and supplied != instance_id:
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "Die Anfrage gehört zu einer anderen Vereinsinstanz.",
                    "expected_instance_id": instance_id,
                },
                headers={"X-Club-Instance": instance_id},
            )

        requires_tenant = (
            is_production
            and path.startswith("/api/")
            and path not in public_without_tenant
        )
        if requires_tenant and not supplied:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "Vereinsinstanz fehlt in der Anfrage.",
                    "expected_instance_id": instance_id,
                },
                headers={"X-Club-Instance": instance_id},
            )

        response = await call_next(request)
        response.headers["X-Club-Instance"] = instance_id
        return response

    def serialize_sujet(row: sqlite3.Row) -> dict[str, Any]:
        with connect() as db:
            images = db.execute(
                """
                SELECT id, sort_order, created_at
                FROM annual_sujet_images
                WHERE sujet_id = ?
                ORDER BY sort_order ASC, id ASC
                """,
                (row["id"],),
            ).fetchall()
        image_items = [
            {
                "id": int(image["id"]),
                "url": f"/api/sujets/{row['id']}/images/{image['id']}",
                "sort_order": int(image["sort_order"] or 0),
                "created_at": str(image["created_at"] or ""),
                "legacy": False,
            }
            for image in images
        ]
        image_urls = [image["url"] for image in image_items]
        return {
            "id": int(row["id"]),
            "annual_sujet": True,
            "year": int(row["year"]),
            "is_current": bool(row["is_current"]),
            "section": "sujet" if row["is_current"] else "archive",
            "title": str(row["title"] or ""),
            "motto": str(row["motto"] or ""),
            "text": str(row["text"] or ""),
            "logo_url": f"/api/sujets/{row['id']}/logo" if row["logo_data"] else "",
            "link_url": "",
            "sort_order": int(row["sort_order"] or 0),
            "created_at": str(row["created_at"] or ""),
            "updated_at": str(row["updated_at"] or ""),
            "images": image_items,
            "image_urls": image_urls,
            "image_url": image_urls[0] if image_urls else "",
            "document_url": "",
            "document_name": "",
            "document_mime": "",
            "poll_options": [],
            "poll_allow_suggestions": False,
            "poll_counts": [],
            "poll_total_votes": 0,
            "poll_my_vote": None,
            "poll_my_suggestion_index": None,
            "poll_my_suggestion_text": "",
            "poll_voters": [],
            "poll_suggestions": [],
        }

    def get_sujet_row(sujet_id: int) -> sqlite3.Row:
        with connect() as db:
            row = db.execute(
                "SELECT * FROM annual_sujets WHERE id = ?",
                (sujet_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Sujet nicht gefunden")
        return row

    @app.get("/api/sujets")
    def list_sujets(
        scope: str = "all",
        _: dict[str, Any] = Depends(current_user),
    ) -> list[dict[str, Any]]:
        if scope not in {"all", "current", "archive"}:
            raise HTTPException(status_code=422, detail="Unbekannter Sujet-Bereich")
        sql = "SELECT * FROM annual_sujets"
        if scope == "current":
            sql += " WHERE is_current = 1"
        elif scope == "archive":
            sql += " WHERE is_current = 0"
        sql += " ORDER BY is_current DESC, year DESC, sort_order ASC, id DESC"
        with connect() as db:
            rows = db.execute(sql).fetchall()
        return [serialize_sujet(row) for row in rows]

    @app.get("/api/sujets/current")
    def current_sujet(
        _: dict[str, Any] = Depends(current_user),
    ) -> dict[str, Any]:
        with connect() as db:
            row = db.execute(
                """
                SELECT * FROM annual_sujets
                WHERE is_current = 1
                ORDER BY year DESC, id DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Kein aktuelles Sujet vorhanden")
        return serialize_sujet(row)

    def save_sujet(payload: SujetPayload, sujet_id: int | None = None) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with connect() as db:
            if payload.is_current:
                db.execute("UPDATE annual_sujets SET is_current = 0 WHERE is_current = 1")
            try:
                if sujet_id is None:
                    next_order = int(
                        db.execute(
                            "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM annual_sujets"
                        ).fetchone()[0]
                    )
                    cursor = db.execute(
                        """
                        INSERT INTO annual_sujets (
                            year, title, motto, text, is_current, sort_order,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            payload.year,
                            payload.title.strip(),
                            payload.motto.strip(),
                            payload.text.strip(),
                            1 if payload.is_current else 0,
                            next_order,
                            now,
                            now,
                        ),
                    )
                    sujet_id = int(cursor.lastrowid)
                else:
                    cursor = db.execute(
                        """
                        UPDATE annual_sujets
                        SET year = ?, title = ?, motto = ?, text = ?, is_current = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            payload.year,
                            payload.title.strip(),
                            payload.motto.strip(),
                            payload.text.strip(),
                            1 if payload.is_current else 0,
                            now,
                            sujet_id,
                        ),
                    )
                    if cursor.rowcount == 0:
                        raise HTTPException(status_code=404, detail="Sujet nicht gefunden")
                db.commit()
            except sqlite3.IntegrityError as exc:
                raise HTTPException(
                    status_code=409,
                    detail=f"Für das Jahr {payload.year} besteht bereits ein Sujet.",
                ) from exc
            row = db.execute(
                "SELECT * FROM annual_sujets WHERE id = ?",
                (sujet_id,),
            ).fetchone()
        return serialize_sujet(row)

    @app.post("/api/sujets")
    def post_sujet(
        payload: SujetPayload,
        _: dict[str, Any] = Depends(require("can_photos")),
    ) -> dict[str, Any]:
        return save_sujet(payload)

    @app.put("/api/sujets/{sujet_id}")
    def put_sujet(
        sujet_id: int,
        payload: SujetPayload,
        _: dict[str, Any] = Depends(require("can_photos")),
    ) -> dict[str, Any]:
        return save_sujet(payload, sujet_id)

    @app.post("/api/sujets/{sujet_id}/logo")
    async def upload_sujet_logo(
        sujet_id: int,
        logo: UploadFile = File(...),
        _: dict[str, Any] = Depends(require("can_photos")),
    ) -> dict[str, Any]:
        raw = await logo.read()
        if not raw:
            raise HTTPException(status_code=422, detail="Leere Logo-Datei")
        optimized, mime = optimize_image(raw, logo.content_type or "image/jpeg")
        with connect() as db:
            cursor = db.execute(
                "UPDATE annual_sujets SET logo_data = ?, logo_mime = ?, updated_at = ? WHERE id = ?",
                (optimized, mime, datetime.now(timezone.utc).isoformat(), sujet_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Sujet nicht gefunden")
            db.commit()
            row = db.execute("SELECT * FROM annual_sujets WHERE id = ?", (sujet_id,)).fetchone()
        return serialize_sujet(row)

    @app.delete("/api/sujets/{sujet_id}/logo")
    def delete_sujet_logo(
        sujet_id: int,
        _: dict[str, Any] = Depends(require("can_photos")),
    ) -> None:
        with connect() as db:
            cursor = db.execute(
                "UPDATE annual_sujets SET logo_data = NULL, logo_mime = '', updated_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), sujet_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Sujet nicht gefunden")
            db.commit()

    @app.get("/api/sujets/{sujet_id}/logo")
    def get_sujet_logo(
        sujet_id: int,
        _: dict[str, Any] = Depends(current_user),
    ) -> Response:
        with connect() as db:
            row = db.execute(
                "SELECT logo_data, logo_mime FROM annual_sujets WHERE id = ?",
                (sujet_id,),
            ).fetchone()
        if row is None or not row["logo_data"]:
            raise HTTPException(status_code=404, detail="Sujet-Logo nicht gefunden")
        return Response(content=row["logo_data"], media_type=row["logo_mime"] or "image/jpeg")

    @app.delete("/api/sujets/{sujet_id}", status_code=204)
    def delete_sujet(
        sujet_id: int,
        _: dict[str, Any] = Depends(require("can_photos")),
    ) -> None:
        with connect() as db:
            db.execute("DELETE FROM annual_sujet_images WHERE sujet_id = ?", (sujet_id,))
            cursor = db.execute("DELETE FROM annual_sujets WHERE id = ?", (sujet_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Sujet nicht gefunden")
            db.commit()

    @app.post("/api/sujets/{sujet_id}/images")
    async def upload_sujet_images(
        sujet_id: int,
        images: list[UploadFile] = File(...),
        _: dict[str, Any] = Depends(require("can_photos")),
    ) -> dict[str, Any]:
        if not images:
            raise HTTPException(status_code=400, detail="Keine Bilder ausgewählt")
        if len(images) > 30:
            raise HTTPException(status_code=413, detail="Maximal 30 Bilder pro Upload")
        get_sujet_row(sujet_id)
        prepared: list[tuple[bytes, str]] = []
        allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        for image in images:
            if image.content_type not in allowed:
                raise HTTPException(status_code=415, detail="Nicht unterstützter Bildtyp")
            prepared.append(optimize_image(await image.read(), image.content_type or ""))

        now = datetime.now(timezone.utc).isoformat()
        with connect() as db:
            max_order = int(
                db.execute(
                    "SELECT COALESCE(MAX(sort_order), 0) FROM annual_sujet_images WHERE sujet_id = ?",
                    (sujet_id,),
                ).fetchone()[0]
            )
            db.executemany(
                """
                INSERT INTO annual_sujet_images (
                    sujet_id, image_data, image_mime, sort_order, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (sujet_id, data, mime, max_order + index + 1, now)
                    for index, (data, mime) in enumerate(prepared)
                ],
            )
            db.execute(
                "UPDATE annual_sujets SET updated_at = ? WHERE id = ?",
                (now, sujet_id),
            )
            db.commit()
        return serialize_sujet(get_sujet_row(sujet_id))

    @app.put("/api/sujets/{sujet_id}/images/order")
    def reorder_sujet_images(
        sujet_id: int,
        payload: ImageOrderPayload,
        _: dict[str, Any] = Depends(require("can_photos")),
    ) -> dict[str, Any]:
        get_sujet_row(sujet_id)
        if len(payload.image_ids) != len(set(payload.image_ids)):
            raise HTTPException(status_code=422, detail="Doppelte Bild-ID")
        with connect() as db:
            current_ids = {
                int(row["id"])
                for row in db.execute(
                    "SELECT id FROM annual_sujet_images WHERE sujet_id = ?",
                    (sujet_id,),
                ).fetchall()
            }
            if set(payload.image_ids) != current_ids:
                raise HTTPException(status_code=422, detail="Bildreihenfolge ist unvollständig")
            for position, image_id in enumerate(payload.image_ids, start=1):
                db.execute(
                    "UPDATE annual_sujet_images SET sort_order = ? WHERE id = ? AND sujet_id = ?",
                    (position, image_id, sujet_id),
                )
            db.execute(
                "UPDATE annual_sujets SET updated_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), sujet_id),
            )
            db.commit()
        return serialize_sujet(get_sujet_row(sujet_id))

    @app.get("/api/sujets/{sujet_id}/images/{image_id}")
    def get_sujet_image(
        sujet_id: int,
        image_id: int,
        _: dict[str, Any] = Depends(current_user),
    ) -> Response:
        with connect() as db:
            row = db.execute(
                """
                SELECT image_data, image_mime
                FROM annual_sujet_images
                WHERE id = ? AND sujet_id = ?
                """,
                (image_id, sujet_id),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Bild nicht gefunden")
        return Response(
            content=row["image_data"],
            media_type=str(row["image_mime"] or "application/octet-stream"),
            headers={"Cache-Control": "private, max-age=3600"},
        )

    @app.delete("/api/sujets/{sujet_id}/images/{image_id}", status_code=204)
    def delete_sujet_image(
        sujet_id: int,
        image_id: int,
        _: dict[str, Any] = Depends(require("can_photos")),
    ) -> None:
        with connect() as db:
            cursor = db.execute(
                "DELETE FROM annual_sujet_images WHERE id = ? AND sujet_id = ?",
                (image_id, sujet_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Bild nicht gefunden")
            db.execute(
                "UPDATE annual_sujets SET updated_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), sujet_id),
            )
            db.commit()
