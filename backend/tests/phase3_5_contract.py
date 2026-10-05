"""End-to-end acceptance contract for Masterplan phases 3-5 after tenant recovery.

The production target is again the proven integrated multi-club backend: several
clubs may coexist in one database, while every tenant-owned row is scoped by the
active numeric club_id. The external X-Club-Instance header still protects a
managed app from accidentally talking to another server instance.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

import requests

BASE_URL = os.getenv("PHASE35_BASE_URL", "http://127.0.0.1:8087").rstrip("/")
DB_PATH = Path(os.getenv("FLAPAMAMAKU_DB", "/tmp/flapamamaku-phase35.db"))
INSTANCE_ID = os.getenv("FLAPAMAMAKU_INSTANCE_ID", "flapamamaku").strip().lower()


def fail(message: str) -> None:
    print(f"PHASE3-5 CONTRACT FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def call(
    method: str,
    path: str,
    *,
    token: str | None = None,
    expected: tuple[int, ...] = (200,),
    headers: dict[str, str] | None = None,
    **kwargs: Any,
) -> requests.Response:
    request_headers = dict(headers or {})
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers=request_headers,
        timeout=10,
        **kwargs,
    )
    if response.status_code not in expected:
        fail(
            f"{method} {path}: expected {expected}, got "
            f"{response.status_code}: {response.text[:500]}"
        )
    return response


def login_admin() -> str:
    login = call(
        "POST",
        "/api/auth/login",
        json={"username": "phase1-admin", "password": "Phase1Test!123"},
    ).json()
    token = str(login.get("token") or "")
    if not token:
        fail("admin login returned no token")
    return token


def verify_tenant_http_boundary(token: str) -> None:
    wrong = call(
        "GET",
        "/api/news",
        token=token,
        headers={"X-Club-Instance": "another-club"},
        expected=(409,),
    )
    payload = wrong.json()
    if payload.get("expected_instance_id") != INSTANCE_ID:
        fail("wrong-instance response did not identify the configured server instance")

    correct = call(
        "GET",
        "/api/news",
        token=token,
        headers={"X-Club-Instance": INSTANCE_ID},
    )
    if correct.headers.get("X-Club-Instance") != INSTANCE_ID:
        fail("successful API response is missing X-Club-Instance binding")


def verify_annual_sujet_lifecycle(token: str) -> None:
    first = call(
        "POST",
        "/api/sujets",
        token=token,
        json={
            "year": 2026,
            "title": "Sujet 2026",
            "motto": "Archiv-Motto",
            "text": "Erstes Jahres-Sujet",
            "is_current": True,
        },
    ).json()
    first_id = int(first["id"])
    if not first.get("is_current") or first.get("section") != "sujet":
        fail("first annual Sujet was not activated")

    second = call(
        "POST",
        "/api/sujets",
        token=token,
        json={
            "year": 2027,
            "title": "Sujet 2027",
            "motto": "Aktuelles Motto",
            "text": "Zweites Jahres-Sujet",
            "is_current": True,
        },
    ).json()
    second_id = int(second["id"])

    current = call("GET", "/api/sujets/current", token=token).json()
    if int(current.get("id", 0)) != second_id or int(current.get("year", 0)) != 2027:
        fail("activating a new Sujet did not switch the canonical current Sujet")
    if current.get("motto") != "Aktuelles Motto":
        fail("Sujet motto did not round-trip through API/database")

    all_sujets = call("GET", "/api/sujets?scope=all", token=token).json()
    current_rows = [row for row in all_sujets if row.get("is_current")]
    if len(current_rows) != 1 or int(current_rows[0]["id"]) != second_id:
        fail("annual Sujet invariant does not enforce exactly one active Sujet")
    archived_first = next((row for row in all_sujets if int(row.get("id", 0)) == first_id), None)
    if archived_first is None or archived_first.get("section") != "archive":
        fail("previous current Sujet was not automatically archived")

    updated = call(
        "PUT",
        f"/api/sujets/{second_id}",
        token=token,
        json={
            "year": 2027,
            "title": "Sujet 2027 aktualisiert",
            "motto": "Neues Motto",
            "text": "Aktualisierte Beschreibung",
            "is_current": True,
        },
    ).json()
    if updated.get("motto") != "Neues Motto" or updated.get("title") != "Sujet 2027 aktualisiert":
        fail("annual Sujet update was not persisted")

    for section in ("sujet", "archive"):
        call(
            "POST",
            "/api/content",
            token=token,
            expected=(409,),
            json={
                "section": section,
                "title": "Legacy write",
                "text": "must fail",
                "link_url": "",
                "poll_options": [],
                "poll_allow_suggestions": False,
            },
        )

    call("DELETE", f"/api/sujets/{first_id}", token=token, expected=(200, 204))
    call("DELETE", f"/api/sujets/{second_id}", token=token, expected=(200, 204))


def verify_integrated_multiclub_schema() -> None:
    if not DB_PATH.exists():
        fail(f"isolated database not found at {DB_PATH}")

    tenant_tables = [
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
    ]
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        tables = {
            str(row["name"])
            for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "clubs" not in tables or "user_clubs" not in tables:
            fail("integrated multi-club tables are missing")

        default_club = db.execute(
            "SELECT id, slug FROM clubs WHERE id = 1"
        ).fetchone()
        if default_club is None or str(default_club["slug"]) != "flapamamaku":
            fail("default FLAPAMAMAKU club was not preserved")

        for table in tenant_tables:
            if table not in tables:
                fail(f"tenant table missing: {table}")
            columns = {
                str(row["name"])
                for row in db.execute(f"PRAGMA table_info({table})")
            }
            if "club_id" not in columns:
                fail(f"{table} is missing club_id")

            orphan_count = int(
                db.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM {table} t
                    LEFT JOIN clubs c ON c.id = CAST(t.club_id AS INTEGER)
                    WHERE t.club_id IS NULL OR c.id IS NULL
                    """
                ).fetchone()[0]
            )
            if orphan_count:
                fail(f"{table} contains rows without a valid club")

        # Multi-club means more than one club ID must be legal. Add a second club
        # and prove a tenant row can be assigned to it without one-instance guards.
        now = "2026-10-05T00:00:00+00:00"
        cursor = db.execute(
            """
            INSERT INTO clubs(slug,name,short_name,active,created_at,updated_at)
            VALUES ('phase35-second','Phase35 Second','P35',1,?,?)
            """,
            (now, now),
        )
        second_club = int(cursor.lastrowid)
        news = db.execute(
            """
            INSERT INTO news(title,text,date,created_at,club_id)
            VALUES ('Second club row','isolated','05.10.2026',?,?)
            """,
            (now, second_club),
        )
        row = db.execute(
            "SELECT club_id FROM news WHERE id = ?",
            (news.lastrowid,),
        ).fetchone()
        if row is None or int(row["club_id"]) != second_club:
            fail("second club tenant row was not stored with its numeric club_id")
        db.rollback()


def main() -> None:
    token = login_admin()
    verify_tenant_http_boundary(token)
    verify_annual_sujet_lifecycle(token)
    verify_integrated_multiclub_schema()
    print("PHASE3-5 CONTRACT OK: integrated multi-club isolation")


if __name__ == "__main__":
    main()
