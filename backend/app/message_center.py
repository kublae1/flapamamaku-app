import json
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from . import main as main_app

app = main_app.app

NORMAL_CHANNEL_ID = "club_messages_v2"
URGENT_CHANNEL_ID = "urgent_messages_v2"
NORMAL_RETENTION_DAYS = 90
URGENT_RETENTION_DAYS = 180


class ManualMessagePayload(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=500)
    route: str = Field(default="", max_length=80)
    urgency: Literal["normal", "urgent"] = "normal"


def init_message_center_schema() -> None:
    with main_app.connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS message_reads (
                message_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                club_id INTEGER NOT NULL,
                read_at TEXT NOT NULL,
                PRIMARY KEY(message_id, user_id, club_id),
                FOREIGN KEY(message_id) REFERENCES push_notifications(id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(club_id) REFERENCES clubs(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS message_deletions (
                message_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                club_id INTEGER NOT NULL,
                deleted_at TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT 'manual',
                PRIMARY KEY(message_id, user_id, club_id),
                FOREIGN KEY(message_id) REFERENCES push_notifications(id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(club_id) REFERENCES clubs(id)
            )
            """
        )
        db.execute(
            """
            CREATE INDEX IF NOT EXISTS message_reads_user_club_idx
            ON message_reads(user_id, club_id, read_at)
            """
        )
        db.execute(
            """
            CREATE INDEX IF NOT EXISTS message_deletions_user_club_idx
            ON message_deletions(user_id, club_id, deleted_at)
            """
        )
        db.commit()


@app.on_event("startup")
def _message_center_startup() -> None:
    init_message_center_schema()


def _active_ids(user: dict[str, Any]) -> tuple[int, int]:
    return int(user["id"]), int(user["current_club_id"])


def _serialize_message(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "kind": str(row["kind"] or ""),
        "title": str(row["title"] or ""),
        "body": str(row["body"] or ""),
        "route": str(row["route"] or ""),
        "created_at": str(row["created_at"] or ""),
        "read": row["read_at"] is not None,
        "read_at": str(row["read_at"] or ""),
        "urgent": str(row["kind"] or "") == "manual_urgent",
    }


def _apply_retention(db: sqlite3.Connection, *, user_id: int, club_id: int) -> None:
    """Hide expired messages for this user without deleting shared club history."""
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        """
        INSERT OR IGNORE INTO message_deletions(message_id,user_id,club_id,deleted_at,reason)
        SELECT n.id,?,?,?,'retention'
        FROM push_notifications n
        WHERE n.club_id=?
          AND (
            (n.kind='manual_urgent' AND datetime(n.created_at) < datetime('now', ?))
            OR
            (n.kind!='manual_urgent' AND datetime(n.created_at) < datetime('now', ?))
          )
        """,
        (
            user_id,
            club_id,
            now,
            club_id,
            f"-{URGENT_RETENTION_DAYS} days",
            f"-{NORMAL_RETENTION_DAYS} days",
        ),
    )


def _hide_message(
    db: sqlite3.Connection,
    *,
    message_id: int,
    user_id: int,
    club_id: int,
    reason: str = "manual",
) -> None:
    row = db.execute(
        "SELECT id FROM push_notifications WHERE id=? AND club_id=?",
        (message_id, club_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Mitteilung nicht gefunden")
    db.execute(
        """
        INSERT INTO message_deletions(message_id,user_id,club_id,deleted_at,reason)
        VALUES (?,?,?,?,?)
        ON CONFLICT(message_id,user_id,club_id)
        DO UPDATE SET deleted_at=excluded.deleted_at, reason=excluded.reason
        """,
        (message_id, user_id, club_id, datetime.now(timezone.utc).isoformat(), reason),
    )


@app.get("/api/messages")
def list_messages(
    user: dict[str, Any] = Depends(main_app.current_user),
) -> list[dict[str, Any]]:
    user_id, club_id = _active_ids(user)
    init_message_center_schema()
    with main_app.connect() as db:
        _apply_retention(db, user_id=user_id, club_id=club_id)
        db.commit()
        rows = db.execute(
            """
            SELECT n.id,n.kind,n.title,n.body,n.route,n.created_at,r.read_at
            FROM push_notifications n
            LEFT JOIN message_reads r
              ON r.message_id=n.id AND r.user_id=? AND r.club_id=?
            LEFT JOIN message_deletions d
              ON d.message_id=n.id AND d.user_id=? AND d.club_id=?
            WHERE n.club_id=? AND d.message_id IS NULL
            ORDER BY n.id DESC
            LIMIT 200
            """,
            (user_id, club_id, user_id, club_id, club_id),
        ).fetchall()
    return [_serialize_message(row) for row in rows]


@app.get("/api/messages/unread-count")
def unread_message_count(
    user: dict[str, Any] = Depends(main_app.current_user),
) -> dict[str, int]:
    user_id, club_id = _active_ids(user)
    init_message_center_schema()
    with main_app.connect() as db:
        _apply_retention(db, user_id=user_id, club_id=club_id)
        db.commit()
        count = int(
            db.execute(
                """
                SELECT COUNT(*)
                FROM push_notifications n
                LEFT JOIN message_reads r
                  ON r.message_id=n.id AND r.user_id=? AND r.club_id=?
                LEFT JOIN message_deletions d
                  ON d.message_id=n.id AND d.user_id=? AND d.club_id=?
                WHERE n.club_id=? AND r.message_id IS NULL AND d.message_id IS NULL
                """,
                (user_id, club_id, user_id, club_id, club_id),
            ).fetchone()[0]
        )
    return {"unread": count}


@app.post("/api/messages/{message_id}/read")
def mark_message_read(
    message_id: int,
    user: dict[str, Any] = Depends(main_app.current_user),
) -> dict[str, Any]:
    user_id, club_id = _active_ids(user)
    init_message_center_schema()
    now = datetime.now(timezone.utc).isoformat()
    with main_app.connect() as db:
        row = db.execute(
            "SELECT id FROM push_notifications WHERE id=? AND club_id=?",
            (message_id, club_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Mitteilung nicht gefunden")
        db.execute(
            """
            INSERT INTO message_reads(message_id,user_id,club_id,read_at)
            VALUES (?,?,?,?)
            ON CONFLICT(message_id,user_id,club_id)
            DO UPDATE SET read_at=excluded.read_at
            """,
            (message_id, user_id, club_id, now),
        )
        db.commit()
    return {"ok": True, "read_at": now}


@app.post("/api/messages/read-all")
def mark_all_messages_read(
    user: dict[str, Any] = Depends(main_app.current_user),
) -> dict[str, Any]:
    user_id, club_id = _active_ids(user)
    init_message_center_schema()
    now = datetime.now(timezone.utc).isoformat()
    with main_app.connect() as db:
        db.execute(
            """
            INSERT INTO message_reads(message_id,user_id,club_id,read_at)
            SELECT n.id,?,?,?
            FROM push_notifications n
            LEFT JOIN message_deletions d
              ON d.message_id=n.id AND d.user_id=? AND d.club_id=?
            WHERE n.club_id=? AND d.message_id IS NULL
            ON CONFLICT(message_id,user_id,club_id)
            DO UPDATE SET read_at=excluded.read_at
            """,
            (user_id, club_id, now, user_id, club_id, club_id),
        )
        db.commit()
    return {"ok": True, "read_at": now}


@app.delete("/api/messages/{message_id}")
def delete_message_for_user(
    message_id: int,
    user: dict[str, Any] = Depends(main_app.current_user),
) -> dict[str, Any]:
    user_id, club_id = _active_ids(user)
    init_message_center_schema()
    with main_app.connect() as db:
        _hide_message(
            db,
            message_id=message_id,
            user_id=user_id,
            club_id=club_id,
        )
        db.commit()
    return {"ok": True}


@app.delete("/api/messages/read")
def delete_read_messages_for_user(
    user: dict[str, Any] = Depends(main_app.current_user),
) -> dict[str, int | bool]:
    user_id, club_id = _active_ids(user)
    init_message_center_schema()
    now = datetime.now(timezone.utc).isoformat()
    with main_app.connect() as db:
        before = db.total_changes
        db.execute(
            """
            INSERT OR IGNORE INTO message_deletions(message_id,user_id,club_id,deleted_at,reason)
            SELECT n.id,?,?,?,'manual_read_all'
            FROM push_notifications n
            JOIN message_reads r
              ON r.message_id=n.id AND r.user_id=? AND r.club_id=?
            WHERE n.club_id=?
            """,
            (user_id, club_id, now, user_id, club_id, club_id),
        )
        deleted = db.total_changes - before
        db.commit()
    return {"ok": True, "deleted": deleted}


@app.delete("/api/messages")
def delete_all_messages_for_user(
    user: dict[str, Any] = Depends(main_app.current_user),
) -> dict[str, int | bool]:
    user_id, club_id = _active_ids(user)
    init_message_center_schema()
    now = datetime.now(timezone.utc).isoformat()
    with main_app.connect() as db:
        before = db.total_changes
        db.execute(
            """
            INSERT OR IGNORE INTO message_deletions(message_id,user_id,club_id,deleted_at,reason)
            SELECT id,?,?,?,'manual_all'
            FROM push_notifications
            WHERE club_id=?
            """,
            (user_id, club_id, now, club_id),
        )
        deleted = db.total_changes - before
        db.commit()
    return {"ok": True, "deleted": deleted}


@app.post("/api/push/admin/send-v2")
def send_manual_message(
    payload: ManualMessagePayload,
    _: dict[str, Any] = Depends(main_app.require("can_manage_users")),
) -> dict[str, Any]:
    route = payload.route.strip()
    allowed_routes = {"", "/news", "/events", "/gallery", "/more", "/messages"}
    if route not in allowed_routes:
        raise HTTPException(status_code=422, detail="Unbekanntes Push-Ziel")
    kind = "manual_urgent" if payload.urgency == "urgent" else "manual"
    with main_app.connect() as db:
        main_app._queue_push_notification(
            db,
            kind=kind,
            title=payload.title.strip(),
            body=payload.body.strip(),
            route=route,
        )
        db.commit()
    return {"status": "queued", "urgency": payload.urgency}


def send_fcm_message_v2(
    *,
    access_token: str,
    project_id: str,
    device_token: str,
    title: str,
    body: str,
    kind: str,
    route: str,
) -> tuple[bool, bool, str]:
    urgent = kind == "manual_urgent"
    channel_id = URGENT_CHANNEL_ID if urgent else NORMAL_CHANNEL_ID
    payload = {
        "message": {
            "token": device_token,
            "notification": {"title": title, "body": body},
            "data": {
                "kind": kind,
                "route": route,
                "urgency": "urgent" if urgent else "normal",
            },
            "android": {
                "priority": "high",
                "notification": {
                    "channel_id": channel_id,
                    "icon": "ic_stat_flapamamaku",
                    "sound": "default",
                    **({"image": main_app.PUSH_ICON_URL} if main_app.PUSH_ICON_URL else {}),
                },
            },
            "apns": {
                "headers": {"apns-priority": "10"},
                "payload": {"aps": {"sound": "default"}},
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


# The existing delivery worker resolves this module-global function at runtime.
# Replacing it here therefore strengthens delivery without duplicating the queue
# or changing the proven push worker/session logic.
main_app._send_fcm_message = send_fcm_message_v2
