from __future__ import annotations

import os
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.main import CLUB_FEATURE_DEFAULTS, app, connect, init_db


PASSWORD = "WhiteLabel-Test-2026"

def ok(response, expected: int = 200):
    assert response.status_code == expected, (
        f"{response.request.method} {response.request.url.path}: "
        f"{response.status_code} {response.text}"
    )
    return response


def login(client: TestClient, username: str, password: str = PASSWORD) -> dict:
    return ok(
        client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
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
    super_headers = {"Authorization": f"Bearer {super_login['token']}"}

    before_flapa = ok(
        client.get("/api/app-config", headers=super_headers)
    ).json()
    assert before_flapa["app_name"] == "FLAPAMAMAKU"
    assert before_flapa["club_id"] == 1

    created = ok(
        client.post(
            "/api/clubs",
            headers=super_headers,
            json={
                "slug": "white-label-test",
                "name": "White Label Test",
                "short_name": "WLT",
                "subtitle": "Neutraler Verein",
                "primary_color": "#225588",
                "secondary_color": "#F2F2F2",
                "app_title": "White Label Test",
            },
        )
    ).json()
    club_id = int(created["id"])

    ok(
        client.post(
            "/api/auth/club",
            headers=super_headers,
            json={"club_id": club_id},
        )
    )

    features = {
        key: key not in {"polls", "links"}
        for key in CLUB_FEATURE_DEFAULTS
    }
    labels = {
        key: label
        for key, (label, _) in CLUB_FEATURE_DEFAULTS.items()
    }
    updated_features = ok(
        client.put(
            "/api/app-config/features",
            headers=super_headers,
            json={"features": features, "labels": labels},
        )
    ).json()
    assert updated_features["polls"]["enabled"] is False
    assert updated_features["push_notifications"]["enabled"] is True
    assert updated_features["participant_lists"]["enabled"] is True

    logo_buffer = BytesIO()
    Image.new("RGB", (32, 32), (34, 85, 136)).save(logo_buffer, format="PNG")
    logo_buffer.seek(0)
    ok(
        client.post(
            "/api/app-config/logo",
            headers=super_headers,
            files={"logo": ("logo.png", logo_buffer.getvalue(), "image/png")},
        )
    )

    admin = ok(
        client.post(
            "/api/users",
            headers=super_headers,
            json={
                "member_id": None,
                "username": "white-label-admin",
                "password": PASSWORD,
                "active": True,
                "role_key": "club_manager",
                "permission_overrides": {},
            },
        )
    ).json()
    assert admin["club_role"] == "club_admin"
    assert admin["current_club_id"] == club_id

    club_admin_login = login(client, "white-label-admin")
    assert club_admin_login["requires_club_selection"] is False
    assert club_admin_login["user"]["current_club_id"] == club_id
    assert club_admin_login["user"]["club_role"] == "club_admin"
    assert [club["slug"] for club in club_admin_login["clubs"]] == ["white-label-test"]

    club_headers = {"Authorization": f"Bearer {club_admin_login['token']}"}
    config = ok(client.get("/api/app-config", headers=club_headers)).json()
    assert config["app_name"] == "White Label Test"
    assert config["short_name"] == "WLT"
    assert config["app_subtitle"] == "Neutraler Verein"
    assert config["primary_color"] == "#225588"
    assert config["secondary_color"] == "#F2F2F2"
    assert config["logo_url"] == f"/api/app-config/logo?club_id={club_id}"
    logo_response = client.get(config["logo_url"])
    assert logo_response.status_code == 200
    assert logo_response.headers["content-type"].startswith("image/")
    assert config["features"]["polls"]["enabled"] is False
    assert config["features"]["push_notifications"]["enabled"] is True
    assert config["features"]["participant_lists"]["enabled"] is True

    # The new club admin must not be able to switch to FLAPAMAMAKU.
    denied = client.post(
        "/api/auth/club",
        headers=club_headers,
        json={"club_id": 1},
    )
    assert denied.status_code == 403

    # FLAPAMAMAKU remains intact for the platform admin.
    ok(
        client.post(
            "/api/auth/club",
            headers=super_headers,
            json={"club_id": 1},
        )
    )
    after_flapa = ok(
        client.get("/api/app-config", headers=super_headers)
    ).json()
    assert after_flapa["app_name"] == before_flapa["app_name"]
    assert after_flapa["primary_color"] == before_flapa["primary_color"]
    assert after_flapa["club_id"] == 1

    # Every backend feature key must be represented by the browser onboarding form.
    admin_html = open("static/admin.html", encoding="utf-8").read()
    for key in CLUB_FEATURE_DEFAULTS:
        assert f'data-key="{key}"' in admin_html, key

    with connect() as db:
        membership = db.execute(
            """
            SELECT role, active
            FROM user_clubs
            WHERE user_id = ? AND club_id = ?
            """,
            (admin["id"], club_id),
        ).fetchone()
        assert membership is not None
        assert membership["role"] == "club_admin"
        assert membership["active"] == 1

    print("white-label onboarding end-to-end ok")


if __name__ == "__main__":
    main()
