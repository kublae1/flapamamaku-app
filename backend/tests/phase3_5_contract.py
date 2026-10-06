"""Recovery acceptance contract for Masterplan phases 3-5.

The stable 175c23b line already has an integrated multi-club database. This
contract validates Masterplan behavior without re-introducing the obsolete
one-process/one-text-club guard that caused the regression.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

BASE_URL = os.getenv("PHASE35_BASE_URL", "http://127.0.0.1:8087").rstrip("/")
DB_PATH = Path(os.getenv("FLAPAMAMAKU_DB", "/tmp/flapamamaku-phase35.db"))


def fail(message: str) -> None:
    print(f"PHASE3-5 CONTRACT FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def call(method: str, path: str, *, token: str | None = None, expected: tuple[int, ...] = (200,), **kwargs: Any) -> requests.Response:
    headers = dict(kwargs.pop("headers", {}) or {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.request(method, BASE_URL + path, headers=headers, timeout=10, **kwargs)
    if response.status_code not in expected:
        fail(f"{method} {path}: expected {expected}, got {response.status_code}: {response.text[:500]}")
    return response


def login_admin() -> tuple[str, dict[str, Any]]:
    login = call(
        "POST", "/api/auth/login",
        json={"username": "phase1-admin", "password": "Phase1Test!123"},
    ).json()
    token = str(login.get("token") or "")
    if not token:
        fail("admin login returned no token")
    me = call("GET", "/api/auth/me", token=token).json()
    return token, me


def verify_extended_events(token: str) -> None:
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    event = call(
        "POST", "/api/events", token=token,
        json={
            "event_date": "2026-10-20",
            "day": "20",
            "month": "OKT",
            "title": "Masterplan Termin",
            "location": "Luzern",
            "time": "19:00",
            "end_time": "22:00",
            "meeting_point": "Bahnhof Luzern",
            "description": "Recovery Vertrag",
            "responsible": "Vorstand",
            "registration_deadline": future_deadline,
            "registration_enabled": True,
            "document_url": "https://example.invalid/termin.pdf",
        },
    ).json()
    event_id = int(event["id"])
    rows = call("GET", "/api/events", token=token).json()
    stored = next(row for row in rows if int(row["id"]) == event_id)
    for key, expected in {
        "end_time": "22:00",
        "meeting_point": "Bahnhof Luzern",
        "description": "Recovery Vertrag",
        "responsible": "Vorstand",
        "document_url": "https://example.invalid/termin.pdf",
    }.items():
        if stored.get(key) != expected:
            fail(f"extended event field {key} did not round-trip")

    call("POST", f"/api/events/{event_id}/registration", token=token, expected=(204,))
    call("DELETE", f"/api/events/{event_id}/registration", token=token, expected=(204,))

    event["registration_enabled"] = False
    event.pop("registration_count", None)
    event.pop("registered_by_me", None)
    call("PUT", f"/api/events/{event_id}", token=token, json={
        key: event.get(key) for key in (
            "event_date", "day", "month", "title", "location", "time", "end_time",
            "meeting_point", "description", "responsible", "registration_deadline",
            "registration_enabled", "document_url"
        )
    })
    call("POST", f"/api/events/{event_id}/registration", token=token, expected=(409,))
    call("DELETE", f"/api/events/{event_id}", token=token, expected=(204,))


def verify_annual_sujet_lifecycle(token: str) -> tuple[int, int]:
    first = call(
        "POST", "/api/sujets", token=token,
        json={"year": 2026, "title": "Sujet 2026", "motto": "Archiv-Motto", "text": "Erstes Jahres-Sujet", "is_current": True},
    ).json()
    second = call(
        "POST", "/api/sujets", token=token,
        json={"year": 2027, "title": "Sujet 2027", "motto": "Aktuelles Motto", "text": "Zweites Jahres-Sujet", "is_current": True},
    ).json()
    first_id, second_id = int(first["id"]), int(second["id"])
    current = call("GET", "/api/sujets/current", token=token).json()
    if int(current.get("id", 0)) != second_id or current.get("motto") != "Aktuelles Motto":
        fail("canonical current annual Sujet is wrong")
    all_rows = call("GET", "/api/sujets?scope=all", token=token).json()
    active = [row for row in all_rows if row.get("is_current")]
    if len(active) != 1 or int(active[0]["id"]) != second_id:
        fail("exactly-one-current Sujet invariant failed")
    archived = next((row for row in all_rows if int(row.get("id", 0)) == first_id), None)
    if archived is None or archived.get("section") != "archive":
        fail("previous current Sujet was not archived")

    updated = call(
        "PUT", f"/api/sujets/{second_id}", token=token,
        json={"year": 2027, "title": "Sujet 2027 aktualisiert", "motto": "Neues Motto", "text": "Aktualisiert", "is_current": True},
    ).json()
    if updated.get("motto") != "Neues Motto":
        fail("Sujet motto update was not persisted")

    for section in ("sujet", "archive"):
        call(
            "POST", "/api/content", token=token, expected=(409,),
            json={"section": section, "title": "Legacy write", "text": "must fail", "link_url": "", "poll_options": [], "poll_allow_suggestions": False},
        )
    return first_id, second_id


def verify_cross_club_isolation(token: str, original_club_id: int) -> None:
    club = call(
        "POST", "/api/clubs", token=token,
        json={
            "slug": "phase35-isolation",
            "name": "Phase 3-5 Isolation",
            "short_name": "P35",
            "primary_color": "#225588",
            "secondary_color": "#F2F2F2",
        },
    ).json()
    other_id = int(club["id"])
    call("POST", "/api/auth/club", token=token, json={"club_id": other_id})
    if call("GET", "/api/sujets?scope=all", token=token).json():
        fail("new club can see Sujet data from original club")
    other = call(
        "POST", "/api/sujets", token=token,
        json={"year": 2030, "title": "Isolation Sujet", "motto": "Nur anderer Verein", "text": "isoliert", "is_current": True},
    ).json()
    if int(other.get("club_id", 0)) != other_id:
        fail("new Sujet was not assigned to active club")
    call("POST", "/api/auth/club", token=token, json={"club_id": original_club_id})
    titles = {row.get("title") for row in call("GET", "/api/sujets?scope=all", token=token).json()}
    if "Isolation Sujet" in titles:
        fail("Sujet from second club leaked into original club")


def verify_sqlite_club_integrity() -> None:
    if not DB_PATH.exists():
        fail(f"database not found at {DB_PATH}")
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        tables = {str(row["name"]) for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required = {"annual_sujets", "annual_sujet_images", "news", "events", "members", "content_items", "users", "sessions"}
        missing = required - tables
        if missing:
            fail(f"tenant tables missing: {sorted(missing)}")
        for table in sorted(required):
            columns = {str(row["name"]) for row in db.execute(f"PRAGMA table_info({table})")}
            if "club_id" not in columns:
                # Integrated sessions bind through active_club_id. Users are
                # intentionally many-to-many through user_clubs, not a single
                # club_id column. Both references must remain valid.
                if table == "sessions" and "active_club_id" in columns:
                    bad = db.execute(
                        "SELECT COUNT(*) FROM sessions s LEFT JOIN clubs c ON c.id=s.active_club_id WHERE s.active_club_id IS NOT NULL AND c.id IS NULL"
                    ).fetchone()[0]
                    if bad:
                        fail("sessions contain invalid active_club_id")
                    continue
                if table == "users" and "user_clubs" in tables:
                    bad = db.execute(
                        "SELECT COUNT(*) FROM user_clubs uc LEFT JOIN users u ON u.id=uc.user_id LEFT JOIN clubs c ON c.id=uc.club_id WHERE u.id IS NULL OR c.id IS NULL"
                    ).fetchone()[0]
                    if bad:
                        fail("user_clubs contains invalid user/club references")
                    continue
                fail(f"{table} is missing club_id")
            bad = db.execute(
                f"SELECT COUNT(*) FROM {table} t LEFT JOIN clubs c ON c.id=t.club_id WHERE t.club_id IS NOT NULL AND c.id IS NULL"
            ).fetchone()[0]
            if bad:
                fail(f"{table} contains orphaned club references")


def main() -> None:
    token, me = login_admin()
    original_club_id = int(me.get("current_club_id") or 0)
    if original_club_id <= 0:
        fail("login has no active club")
    verify_extended_events(token)
    first_id, second_id = verify_annual_sujet_lifecycle(token)
    verify_cross_club_isolation(token, original_club_id)
    verify_sqlite_club_integrity()
    call("DELETE", f"/api/sujets/{first_id}", token=token, expected=(200, 204))
    call("DELETE", f"/api/sujets/{second_id}", token=token, expected=(200, 204))
    print("PHASE3-5 CONTRACT OK: extended events, annual Sujet, integrated club isolation")


if __name__ == "__main__":
    main()
