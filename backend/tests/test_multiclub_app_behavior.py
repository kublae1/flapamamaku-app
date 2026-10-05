from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app, connect, init_db


PASSWORD = "Phase10-Login-Test-2026"


def ok(response, expected: int = 200):
    assert response.status_code == expected, (
        f"{response.request.method} {response.request.url.path}: "
        f"{response.status_code} {response.text}"
    )
    return response


def login(client: TestClient, username: str):
    return ok(
        client.post(
            "/api/auth/login",
            json={"username": username, "password": PASSWORD},
        )
    ).json()


def create_user(
    client: TestClient,
    headers: dict[str, str],
    username: str,
) -> dict:
    return ok(
        client.post(
            "/api/users",
            headers=headers,
            json={
                "member_id": None,
                "username": username,
                "password": PASSWORD,
                "active": True,
                "role_key": "member",
                "permission_overrides": {},
            },
        )
    ).json()


def main() -> None:
    db_path = os.environ["FLAPAMAMAKU_DB"]
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass

    init_db()
    client = TestClient(app)

    # Plattform-Admin bleibt ohne erzwungene Auswahl direkt im Referenzverein.
    ok(
        client.post(
            "/api/auth/bootstrap",
            json={
                "username": "platform-admin",
                "password": PASSWORD,
                "member_id": None,
            },
        )
    )
    super_login = login(client, "platform-admin")
    assert super_login["requires_club_selection"] is False
    assert super_login["user"]["current_club_id"] == 1
    super_headers = {"Authorization": f"Bearer {super_login['token']}"}

    test_club = ok(
        client.post(
            "/api/clubs",
            headers=super_headers,
            json={
                "slug": "testverein",
                "name": "Testverein",
                "short_name": "TEST",
                "primary_color": "#225588",
                "secondary_color": "#FFFFFF",
            },
        )
    ).json()
    test_club_id = int(test_club["id"])

    third_club = ok(
        client.post(
            "/api/clubs",
            headers=super_headers,
            json={
                "slug": "drittverein",
                "name": "Drittverein",
                "short_name": "DRITT",
                "primary_color": "#556677",
                "secondary_color": "#FFFFFF",
            },
        )
    ).json()
    third_club_id = int(third_club["id"])

    # FLAPAMAMAKU-Einzelmitglied: kein Auswahlbildschirm.
    flapa_only = create_user(client, super_headers, "flapa-only")
    assert flapa_only["current_club_id"] == 1

    # Testverein-Einzelmitglied: Login muss automatisch Testverein öffnen.
    ok(
        client.post(
            "/api/auth/club",
            headers=super_headers,
            json={"club_id": test_club_id},
        )
    )
    test_only = create_user(client, super_headers, "test-only")
    assert test_only["current_club_id"] == test_club_id

    # Mehrfachmitglied zuerst in FLAPAMAMAKU anlegen und zusätzlich Testverein zuordnen.
    ok(
        client.post(
            "/api/auth/club",
            headers=super_headers,
            json={"club_id": 1},
        )
    )
    multi = create_user(client, super_headers, "multi-user")
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        db.execute(
            """
            INSERT INTO user_clubs (
                user_id, club_id, role, active, created_at, updated_at
            ) VALUES (?, ?, 'member', 1, ?, ?)
            """,
            (multi["id"], test_club_id, now, now),
        )
        db.commit()

    flapa_login = login(client, "flapa-only")
    assert flapa_login["requires_club_selection"] is False
    assert flapa_login["user"]["current_club_id"] == 1
    assert [club["slug"] for club in flapa_login["clubs"]] == ["flapamamaku"]

    test_login = login(client, "test-only")
    assert test_login["requires_club_selection"] is False
    assert test_login["user"]["current_club_id"] == test_club_id
    assert [club["slug"] for club in test_login["clubs"]] == ["testverein"]

    multi_login = login(client, "multi-user")
    assert multi_login["requires_club_selection"] is True
    assert multi_login["user"]["current_club_id"] == 1
    assert {club["slug"] for club in multi_login["clubs"]} == {
        "flapamamaku",
        "testverein",
    }

    multi_headers = {"Authorization": f"Bearer {multi_login['token']}"}
    switched = ok(
        client.post(
            "/api/auth/club",
            headers=multi_headers,
            json={"club_id": test_club_id},
        )
    ).json()
    assert switched["club_id"] == test_club_id
    assert ok(client.get("/api/auth/me", headers=multi_headers)).json()[
        "current_club_id"
    ] == test_club_id

    # Mehrfachmitglied darf nur in tatsächlich zugeordnete Vereine wechseln.
    denied = client.post(
        "/api/auth/club",
        headers=multi_headers,
        json={"club_id": third_club_id},
    )
    assert denied.status_code == 403

    # Super-Admin sieht alle aktiven Vereine und kann frei wechseln.
    super_clubs = ok(
        client.get("/api/clubs/accessible", headers=super_headers)
    ).json()
    assert {club["slug"] for club in super_clubs} == {
        "flapamamaku",
        "testverein",
        "drittverein",
    }
    ok(
        client.post(
            "/api/auth/club",
            headers=super_headers,
            json={"club_id": third_club_id},
        )
    )
    assert ok(client.get("/api/auth/me", headers=super_headers)).json()[
        "current_club_id"
    ] == third_club_id

    print("package 10 multi-club app behavior ok")


if __name__ == "__main__":
    main()
