"""Regression for cross-club member identity leakage.

A user's visible member identity must be resolved by (user_id, active_club_id),
never by the historical global users.member_id alone.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app import main
from app.runtime import app


def ok(response, expected: int = 200):
    assert response.status_code == expected, (
        f"{response.request.method} {response.request.url.path}: "
        f"{response.status_code} {response.text}"
    )
    return response


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def main_test() -> None:
    db_path = os.environ["FLAPAMAMAKU_DB"]
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass

    with TestClient(app) as client:
        ok(
            client.post(
                "/api/auth/bootstrap",
                json={"username": "root", "password": "RootTest!123", "member_id": None},
            )
        )
        root_login = ok(
            client.post(
                "/api/auth/login",
                json={"username": "root", "password": "RootTest!123"},
            )
        ).json()
        root_token = root_login["token"]
        root_headers = auth(root_token)

        member_a = ok(
            client.post(
                "/api/members",
                headers=root_headers,
                json={
                    "name": "Mitglied A",
                    "role": "Mitglied",
                    "since": "2026",
                    "email": "mitglied.a@example.invalid",
                },
            )
        ).json()

        user_a = ok(
            client.post(
                "/api/users",
                headers=root_headers,
                json={
                    "member_id": member_a["id"],
                    "username": "mitglied.a@example.invalid",
                    "password": "MemberTest!123",
                    "active": True,
                    "role_key": "member",
                    "permission_overrides": {},
                },
            )
        ).json()
        user_a_id = int(user_a["id"])

        club_b = ok(
            client.post(
                "/api/clubs",
                headers=root_headers,
                json={
                    "slug": "verein-b",
                    "name": "Verein B",
                    "short_name": "B",
                    "subtitle": "",
                    "primary_color": "#225588",
                    "secondary_color": "#FFFFFF",
                    "description": "",
                    "website": "",
                    "email": "",
                    "phone": "",
                    "address": "",
                    "city": "Luzern",
                    "country": "CH",
                    "app_title": "Verein B",
                    "welcome_text": "",
                },
            )
        ).json()
        club_b_id = int(club_b["id"])

        ok(
            client.post(
                "/api/auth/club",
                headers=root_headers,
                json={"club_id": club_b_id},
            )
        )
        member_b = ok(
            client.post(
                "/api/members",
                headers=root_headers,
                json={
                    "name": "Mitglied B",
                    "role": "Mitglied",
                    "since": "2026",
                    "email": "mitglied.b@example.invalid",
                },
            )
        ).json()

        # Give the same login explicit access to B and define its B identity.
        now = datetime.now(timezone.utc).isoformat()
        with main.connect() as db:
            db.execute(
                """
                INSERT INTO user_clubs(user_id,club_id,role,active,created_at,updated_at)
                VALUES (?,?, 'member',1,?,?)
                """,
                (user_a_id, club_b_id, now, now),
            )
            db.execute(
                """
                INSERT INTO user_club_members(user_id,club_id,member_id)
                VALUES (?,?,?)
                ON CONFLICT(user_id,club_id) DO UPDATE SET member_id=excluded.member_id
                """,
                (user_a_id, club_b_id, int(member_b["id"])),
            )
            db.commit()

        login_a = ok(
            client.post(
                "/api/auth/login",
                json={
                    "username": "mitglied.a@example.invalid",
                    "password": "MemberTest!123",
                },
            )
        ).json()
        token_a = login_a["token"]
        headers_a = auth(token_a)
        assert login_a["requires_club_selection"] is True

        # Initial club is A. Deliberately corrupt the legacy global pointer to B.
        with main.connect() as db:
            db.execute(
                "UPDATE users SET member_id=? WHERE id=?",
                (int(member_b["id"]), user_a_id),
            )
            db.commit()

        me_a = ok(client.get("/api/auth/me", headers=headers_a)).json()
        assert int(me_a["current_club_id"]) == 1
        assert int(me_a["member_id"]) == int(member_a["id"])
        assert me_a["member_name"] == "Mitglied A"

        # Switch to B and then corrupt the global pointer in the other direction.
        ok(
            client.post(
                "/api/auth/club",
                headers=headers_a,
                json={"club_id": club_b_id},
            )
        )
        with main.connect() as db:
            db.execute(
                "UPDATE users SET member_id=? WHERE id=?",
                (int(member_a["id"]), user_a_id),
            )
            db.commit()

        me_b = ok(client.get("/api/auth/me", headers=headers_a)).json()
        assert int(me_b["current_club_id"]) == club_b_id
        assert int(me_b["member_id"]) == int(member_b["id"])
        assert me_b["member_name"] == "Mitglied B"

        # Storage itself must reject a cross-club member mapping.
        with main.connect() as db:
            try:
                db.execute(
                    """
                    UPDATE user_club_members
                    SET member_id=?
                    WHERE user_id=? AND club_id=?
                    """,
                    (int(member_b["id"]), user_a_id, 1),
                )
                db.commit()
            except sqlite3.IntegrityError:
                db.rollback()
            else:
                raise AssertionError("cross-club member mapping was accepted")

    print("TENANT MEMBER IDENTITY REGRESSION OK")


if __name__ == "__main__":
    main_test()
