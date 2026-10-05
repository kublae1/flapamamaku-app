"""Phase-1 contract smoke test.

This test deliberately uses the public HTTP API instead of importing FastAPI
internals. It verifies the binding data flow Admin/API -> database -> App-facing
GET endpoints for the core Phase-1 resources. Annual Sujet/archive content is
owned by the canonical Phase-4 Sujet domain and is therefore explicitly
excluded from legacy /api/content CRUD.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

import requests

BASE_URL = os.getenv("PHASE1_BASE_URL", "http://127.0.0.1:8087").rstrip("/")


def fail(message: str) -> None:
    print(f"PHASE1 CONTRACT FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    expected: tuple[int, ...] = (200,),
    **kwargs: Any,
) -> requests.Response:
    headers = dict(kwargs.pop("headers", {}))
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers=headers,
        timeout=10,
        **kwargs,
    )
    if response.status_code not in expected:
        fail(
            f"{method} {path}: expected {expected}, got "
            f"{response.status_code}: {response.text[:500]}"
        )
    return response


def wait_for_server() -> None:
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            response = requests.get(f"{BASE_URL}/api/health", timeout=2)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)
    fail("backend did not become healthy within 30 seconds")


def login_admin() -> str:
    status = request("GET", "/api/auth/status").json()
    if status.get("bootstrap_required"):
        request(
            "POST",
            "/api/auth/bootstrap",
            json={"username": "phase1-admin", "password": "Phase1Test!123"},
            expected=(200, 201),
        )
    login = request(
        "POST",
        "/api/auth/login",
        json={"username": "phase1-admin", "password": "Phase1Test!123"},
    ).json()
    token = str(login.get("token") or "")
    if not token:
        fail("login returned no token")
    user = login.get("user") or {}
    for permission in ("can_news", "can_events", "can_members", "can_photos"):
        if user.get(permission) is not True:
            fail(f"bootstrap admin is missing {permission}")
    return token


def assert_in_collection(items: list[dict[str, Any]], row_id: int, title_key: str, title: str) -> None:
    row = next((item for item in items if item.get("id") == row_id), None)
    if row is None:
        fail(f"created row {row_id} missing from collection")
    if row.get(title_key) != title:
        fail(f"row {row_id} has wrong {title_key}: {row.get(title_key)!r}")


def exercise_news(token: str) -> None:
    created = request(
        "POST",
        "/api/news",
        token=token,
        json={
            "title": "Phase 1 News",
            "text": "Persistenztest",
            "date": "03.10.2026",
            "image_url": "",
        },
    ).json()
    row_id = int(created["id"])
    assert_in_collection(request("GET", "/api/news", token=token).json(), row_id, "title", "Phase 1 News")
    updated = request(
        "PUT",
        f"/api/news/{row_id}",
        token=token,
        json={
            "title": "Phase 1 News aktualisiert",
            "text": "Persistenztest",
            "date": "03.10.2026",
            "image_url": "",
        },
    ).json()
    if updated.get("title") != "Phase 1 News aktualisiert":
        fail("news update was not persisted")
    request("DELETE", f"/api/news/{row_id}", token=token, expected=(200, 204))


def exercise_events(token: str) -> None:
    created = request(
        "POST",
        "/api/events",
        token=token,
        json={
            "event_date": "2026-10-20",
            "day": "20",
            "month": "OKT",
            "title": "Phase 1 Termin",
            "location": "Luzern",
            "time": "19:00",
        },
    ).json()
    row_id = int(created["id"])
    assert_in_collection(request("GET", "/api/events", token=token).json(), row_id, "title", "Phase 1 Termin")
    updated = request(
        "PUT",
        f"/api/events/{row_id}",
        token=token,
        json={
            "event_date": "2026-10-21",
            "day": "21",
            "month": "OKT",
            "title": "Phase 1 Termin aktualisiert",
            "location": "Luzern",
            "time": "20:00",
        },
    ).json()
    if updated.get("event_date") != "2026-10-21":
        fail("event update was not persisted")
    request("DELETE", f"/api/events/{row_id}", token=token, expected=(200, 204))


def exercise_members(token: str) -> None:
    payload = {
        "name": "Phase 1 Mitglied",
        "role": "Test",
        "since": "2026",
        "birth_date": "",
        "status": "Aktiv",
        "member_group": "",
        "engagement": "",
        "filter_ids": [],
        "partner_name": "",
        "phone_mobile": "",
        "phone_private": "",
        "phone_work": "",
        "email": "",
        "address": "",
        "occupation": "",
        "employer": "",
        "employer_url": "",
    }
    created = request("POST", "/api/members", token=token, json=payload).json()
    row_id = int(created["id"])
    assert_in_collection(request("GET", "/api/members", token=token).json(), row_id, "name", "Phase 1 Mitglied")
    payload["name"] = "Phase 1 Mitglied aktualisiert"
    updated = request("PUT", f"/api/members/{row_id}", token=token, json=payload).json()
    if updated.get("name") != payload["name"]:
        fail("member update was not persisted")
    request("DELETE", f"/api/members/{row_id}", token=token, expected=(200, 204))


def exercise_content(token: str) -> None:
    for section in ("hero", "photos", "gallery", "documents", "links"):
        title = f"Phase 1 {section}"
        created = request(
            "POST",
            "/api/content",
            token=token,
            json={
                "section": section,
                "title": title,
                "text": "Contract smoke",
                "link_url": "",
                "poll_options": [],
                "poll_allow_suggestions": False,
            },
        ).json()
        row_id = int(created["id"])
        items = request("GET", f"/api/content?section={section}", token=token).json()
        assert_in_collection(items, row_id, "title", title)
        request("DELETE", f"/api/content/{row_id}", token=token, expected=(200, 204))

    # Phase 4 deliberately removes Sujet/archive writes from generic content CRUD.
    # A 409 proves callers cannot create a second hidden source of truth.
    for section in ("sujet", "archive"):
        request(
            "POST",
            "/api/content",
            token=token,
            expected=(409,),
            json={
                "section": section,
                "title": f"Legacy {section}",
                "text": "must be rejected",
                "link_url": "",
                "poll_options": [],
                "poll_allow_suggestions": False,
            },
        )


def exercise_auth_guards(token: str) -> None:
    response = requests.get(f"{BASE_URL}/api/news", timeout=10)
    if response.status_code != 401:
        fail(f"unauthenticated news read should be 401, got {response.status_code}")

    me = request("GET", "/api/auth/me", token=token).json()
    if not me.get("username"):
        fail("/api/auth/me returned no username")


def main() -> None:
    wait_for_server()
    config = request("GET", "/api/app-config").json()
    if not str(config.get("instance_id") or "").strip():
        fail("/api/app-config returned no instance_id")

    token = login_admin()
    exercise_auth_guards(token)
    exercise_news(token)
    exercise_events(token)
    exercise_members(token)
    exercise_content(token)
    print("PHASE1 CONTRACT OK")


if __name__ == "__main__":
    main()
