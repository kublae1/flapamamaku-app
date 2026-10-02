from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.main import CURRENT_SCHEMA_VERSION, _token_hash, app, connect, init_db


def ok(response, expected: int = 200):
    assert response.status_code == expected, (
        f"{response.request.method} {response.request.url.path}: "
        f"{response.status_code} {response.text}"
    )
    return response


def image_bytes(rgb: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", (48, 48), rgb)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def create_content(client: TestClient, headers: dict[str, str], section: str, title: str):
    response = ok(
        client.post(
            "/api/content",
            headers=headers,
            json={
                "section": section,
                "title": title,
                "text": f"{title} Inhalt",
                "link_url": "",
                "poll_options": [],
                "poll_allow_suggestions": False,
            },
        )
    )
    return response.json()


def titles(rows):
    return {str(row.get("title") or "") for row in rows}


def names(rows):
    return {str(row.get("name") or "") for row in rows}


def main() -> None:
    db_path = os.environ["FLAPAMAMAKU_DB"]
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass

    init_db()
    assert CURRENT_SCHEMA_VERSION == 19
    client = TestClient(app)

    # 1. Bestehender FLAPAMAMAKU-Login funktioniert.
    ok(
        client.post(
            "/api/auth/bootstrap",
            json={
                "username": "platform-admin",
                "password": "Testpasswort123!",
                "member_id": None,
            },
        )
    )
    login = ok(
        client.post(
            "/api/auth/login",
            json={
                "username": "platform-admin",
                "password": "Testpasswort123!",
            },
        )
    ).json()
    super_token = login["token"]
    super_headers = {"Authorization": f"Bearer {super_token}"}
    assert login["user"]["is_super_admin"] is True
    assert login["user"]["current_club_id"] == 1

    # FLAPAMAMAKU Referenzdaten.
    flapa_news = ok(
        client.post(
            "/api/news",
            headers=super_headers,
            json={
                "title": "FLAPA News",
                "text": "Nur FLAPAMAMAKU",
                "date": "30.09.2026",
            },
        )
    ).json()
    flapa_event = ok(
        client.post(
            "/api/events",
            headers=super_headers,
            json={
                "event_date": "2026-10-01",
                "day": "01",
                "month": "OKT",
                "title": "FLAPA Termin",
                "location": "Luzern",
                "time": "19:00",
            },
        )
    ).json()
    flapa_member = ok(
        client.post(
            "/api/members",
            headers=super_headers,
            json={
                "name": "FLAPA Mitglied",
                "role": "Mitglied",
                "since": "2026",
            },
        )
    ).json()

    flapa_sections = {}
    for section, title in (
        ("hero", "FLAPA Start"),
        ("documents", "FLAPA Dokument"),
        ("gallery", "FLAPA Galerie"),
        ("photos", "FLAPA Fotoalbum"),
        ("sujet", "FLAPA Sujet nächstes Jahr"),
        ("archive", "FLAPA Vergangenes Sujet"),
    ):
        flapa_sections[section] = create_content(
            client, super_headers, section, title
        )

    ok(
        client.post(
            f"/api/content/{flapa_sections['documents']['id']}/document",
            headers=super_headers,
            files={
                "document": (
                    "flapa.pdf",
                    b"%PDF-1.4\nFLAPA\n%%EOF",
                    "application/pdf",
                )
            },
        )
    )
    ok(
        client.post(
            f"/api/content/{flapa_sections['gallery']['id']}/image",
            headers=super_headers,
            files={
                "image": ("flapa-gallery.png", image_bytes((138, 16, 27)), "image/png")
            },
        )
    )
    ok(
        client.post(
            f"/api/content/{flapa_sections['photos']['id']}/images",
            headers=super_headers,
            files=[
                ("images", ("flapa-1.png", image_bytes((138, 16, 27)), "image/png")),
                ("images", ("flapa-2.png", image_bytes((180, 60, 70)), "image/png")),
            ],
        )
    )
    ok(
        client.post(
            f"/api/members/{flapa_member['id']}/photo",
            headers=super_headers,
            files={
                "photo": ("flapa-member.png", image_bytes((138, 16, 27)), "image/png")
            },
        )
    )

    # Push-Gerät für Mandant 1.
    ok(
        client.post(
            "/api/push/register",
            headers=super_headers,
            json={"token": "flapamamaku-device-token-0001", "platform": "android"},
        )
    )
    ok(
        client.post(
            "/api/push/admin/send",
            headers=super_headers,
            json={"title": "FLAPA Push", "body": "Nur FLAPA", "route": "/news"},
        )
    )

    # 2. Startseite / zentrale Konfiguration von FLAPAMAMAKU funktioniert.
    flapa_config = ok(client.get("/api/app-config", headers=super_headers)).json()
    assert flapa_config["app_name"] == "FLAPAMAMAKU"

    flapa_logo_source = image_bytes((138, 16, 27))
    flapa_logo_config = ok(
        client.post(
            "/api/app-config/logo",
            headers=super_headers,
            files={"logo": ("flapamamaku.png", flapa_logo_source, "image/png")},
        )
    ).json()
    assert "club_id=1" in flapa_logo_config["logo_url"]
    flapa_logo_url = flapa_logo_config["logo_url"]
    flapa_logo_public = ok(client.get(flapa_logo_url))
    assert flapa_logo_public.headers["content-type"].startswith("image/png")
    assert flapa_logo_public.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert "FLAPA Start" in titles(
        ok(
            client.get(
                "/api/content?section=hero",
                headers=super_headers,
            )
        ).json()
    )

    # Zweiten neutralen Verein erstellen.
    test_club = ok(
        client.post(
            "/api/clubs",
            headers=super_headers,
            json={
                "slug": "testverein",
                "name": "Testverein",
                "short_name": "TEST",
                "subtitle": "Neutraler Testverein",
                "primary_color": "#225588",
                "secondary_color": "#F2F2F2",
                "description": "Isolationstest",
                "city": "Teststadt",
                "country": "CH",
                "app_title": "Testverein App",
                "welcome_text": "Willkommen beim Testverein",
            },
        )
    ).json()
    test_club_id = int(test_club["id"])

    # 16. Super-Admin kann beide Vereine verwalten.
    accessible = ok(
        client.get("/api/clubs/accessible", headers=super_headers)
    ).json()
    assert {club["slug"] for club in accessible} == {"flapamamaku", "testverein"}
    ok(
        client.post(
            "/api/auth/club",
            headers=super_headers,
            json={"club_id": test_club_id},
        )
    )
    me_test = ok(client.get("/api/auth/me", headers=super_headers)).json()
    assert me_test["current_club_id"] == test_club_id
    assert me_test["is_super_admin"] is True

    # Eigene Konfiguration/Farben von Testverein.
    cfg = ok(
        client.put(
            "/api/app-config",
            headers=super_headers,
            json={
                "app_name": "Testverein",
                "short_name": "TEST",
                "app_subtitle": "Neutraler Testverein",
                "primary_color": "#225588",
                "secondary_color": "#F2F2F2",
                "club_description": "Eigenständige Vereinskonfiguration",
                "city": "Teststadt",
                "country": "CH",
                "app_title": "Testverein App",
                "welcome_text": "Willkommen beim Testverein",
            },
        )
    ).json()
    assert cfg["app_name"] == "Testverein"
    assert cfg["primary_color"] == "#225588"
    assert cfg["secondary_color"] == "#F2F2F2"

    test_logo_config = ok(
        client.post(
            "/api/app-config/logo",
            headers=super_headers,
            files={
                "logo": ("testverein.png", image_bytes((34, 85, 136)), "image/png")
            },
        )
    ).json()
    assert f"club_id={test_club_id}" in test_logo_config["logo_url"]
    assert test_logo_config["logo_url"] != flapa_logo_url
    test_logo_public = ok(client.get(test_logo_config["logo_url"]))
    assert test_logo_public.headers["content-type"].startswith("image/png")
    assert test_logo_public.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert test_logo_public.content != flapa_logo_public.content

    # 3, 4, 6: eigene News, Termine, Mitglieder.
    test_news = ok(
        client.post(
            "/api/news",
            headers=super_headers,
            json={
                "title": "Testverein News",
                "text": "Nur Testverein",
                "date": "30.09.2026",
            },
        )
    ).json()
    test_event = ok(
        client.post(
            "/api/events",
            headers=super_headers,
            json={
                "event_date": "2026-10-02",
                "day": "02",
                "month": "OKT",
                "title": "Testverein Termin",
                "location": "Teststadt",
                "time": "20:00",
            },
        )
    ).json()
    test_member = ok(
        client.post(
            "/api/members",
            headers=super_headers,
            json={
                "name": "Testverein Mitglied",
                "role": "Mitglied",
                "since": "2026",
            },
        )
    ).json()

    # Mitgliederfilter müssen ebenfalls dem Testverein gehören.
    test_filter = ok(
        client.post(
            "/api/member-filters",
            headers=super_headers,
            json={"label": "Testverein Vorstand", "active": True},
        )
    ).json()
    ok(
        client.put(
            f"/api/members/{test_member['id']}",
            headers=super_headers,
            json={
                "name": "Testverein Mitglied",
                "role": "Mitglied",
                "since": "2026",
                "filter_ids": [test_filter["id"]],
            },
        )
    )

    # Dauerhafte Vereinsfotos liegen in Fotoalben; Galerie ist bei externen
    # Vereinen ausschließlich für temporäre Snapshots reserviert.
    test_sections = {}
    for section, title in (
        ("hero", "Testverein Start"),
        ("documents", "Testverein Dokument"),
        ("photos", "Testverein Fotoalbum"),
        ("sujet", "Testverein Sujet nächstes Jahr"),
        ("archive", "Testverein Vergangenes Sujet"),
    ):
        test_sections[section] = create_content(
            client, super_headers, section, title
        )

    ok(
        client.post(
            f"/api/content/{test_sections['documents']['id']}/document",
            headers=super_headers,
            files={
                "document": (
                    "testverein.pdf",
                    b"%PDF-1.4\nTESTVEREIN\n%%EOF",
                    "application/pdf",
                )
            },
        )
    )
    blocked_gallery = client.post(
        "/api/content",
        headers=super_headers,
        json={
            "section": "gallery",
            "title": "Testverein Galerie",
            "text": "",
            "link_url": "",
            "poll_options": [],
            "poll_allow_suggestions": False,
        },
    )
    assert blocked_gallery.status_code == 403
    album = ok(
        client.post(
            f"/api/content/{test_sections['photos']['id']}/images",
            headers=super_headers,
            files=[
                ("images", ("test-1.png", image_bytes((34, 85, 136)), "image/png")),
                ("images", ("test-2.png", image_bytes((50, 110, 160)), "image/png")),
            ],
        )
    ).json()
    assert len(album.get("images") or []) == 2

    ok(
        client.post(
            f"/api/members/{test_member['id']}/photo",
            headers=super_headers,
            files={
                "photo": (
                    "test-member.png",
                    image_bytes((34, 85, 136)),
                    "image/png",
                )
            },
        )
    )

    # Galerie-Snapshot separat testen.
    snapshot = ok(
        client.post(
            "/api/gallery/snapshots?expires_days=7",
            headers=super_headers,
            files={
                "image": (
                    "test-snapshot.png",
                    image_bytes((34, 85, 136)),
                    "image/png",
                )
            },
        )
    ).json()

    # Eigenes Push-Gerät und eigener Push-Verlauf.
    ok(
        client.post(
            "/api/push/register",
            headers=super_headers,
            json={"token": "testverein-device-token-0002", "platform": "ios"},
        )
    )
    ok(
        client.post(
            "/api/push/admin/send",
            headers=super_headers,
            json={"title": "Testverein Push", "body": "Nur Test", "route": "/news"},
        )
    )
    test_push = ok(client.get("/api/push/admin", headers=super_headers)).json()
    assert test_push["registered_devices_total"] == 1
    assert "Testverein Push" in titles(test_push["notifications"])
    assert "FLAPA Push" not in titles(test_push["notifications"])

    # Club-Admin für Testverein anlegen.
    club_admin = ok(
        client.post(
            "/api/users",
            headers=super_headers,
            json={
                "member_id": test_member["id"],
                "username": "testverein-admin",
                "password": "TestvereinPass123!",
                "active": True,
                "role_key": "club_manager",
                "permission_overrides": {},
            },
        )
    ).json()
    club_admin_id = int(club_admin["id"])
    assert club_admin["club_role"] == "club_admin"
    assert club_admin["current_club_id"] == test_club_id

    # Eigene Session für den Testverein-Club-Admin erzeugen.
    club_admin_token = "testverein-club-admin-session-token"
    now = datetime.now(timezone.utc)
    with connect() as db:
        db.execute(
            """
            INSERT INTO sessions (
                token_hash, user_id, expires_at, created_at, active_club_id
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                _token_hash(club_admin_token),
                club_admin_id,
                (now + timedelta(days=1)).isoformat(),
                now.isoformat(),
                test_club_id,
            ),
        )
        db.commit()
    club_headers = {"Authorization": f"Bearer {club_admin_token}"}

    # 5. Anmeldung Ja/Nein funktioniert und bleibt vereinsbezogen.
    ok(
        client.post(
            f"/api/events/{test_event['id']}/registration",
            headers=club_headers,
        ),
        204,
    )
    registrations = ok(
        client.get(
            f"/api/events/{test_event['id']}/registrations",
            headers=club_headers,
        )
    ).json()
    assert any(row["name"] == "Testverein Mitglied" for row in registrations)
    ok(
        client.delete(
            f"/api/events/{test_event['id']}/registration",
            headers=club_headers,
        ),
        204,
    )
    assert ok(
        client.get(
            f"/api/events/{test_event['id']}/registrations",
            headers=club_headers,
        )
    ).json() == []

    # 12. Admin-Funktionen sind auf Testverein begrenzt.
    users_test = ok(client.get("/api/users", headers=club_headers)).json()
    assert {row["username"] for row in users_test} == {"testverein-admin"}
    admin_clubs = ok(
        client.get("/api/clubs/accessible", headers=club_headers)
    ).json()
    assert len(admin_clubs) == 1
    assert admin_clubs[0]["id"] == test_club_id
    club_admin_config = ok(
        client.get("/api/app-config", headers=club_headers)
    ).json()
    assert club_admin_config["club_id"] == test_club_id
    assert club_admin_config["logo_url"] == test_logo_config["logo_url"]

    club_roles = ok(client.get("/api/roles", headers=club_headers)).json()
    assert [row["key"] for row in club_roles] == [
        "member", "editor", "board", "club_manager"
    ]
    assert all(row["key"] != "admin" for row in club_roles)

    club_push = ok(client.get("/api/push/admin", headers=club_headers)).json()
    assert club_push["registered_devices_total"] == 1
    assert "Testverein Push" in titles(club_push["notifications"])
    assert "FLAPA Push" not in titles(club_push["notifications"])

    assert client.get(
        "/api/operator/billing/clubs",
        headers=club_headers,
    ).status_code == 403
    assert client.put(
        f"/api/users/{club_admin_id}/super-admin",
        headers=club_headers,
        json={"enabled": True},
    ).status_code == 403
    denied_switch = client.post(
        "/api/auth/club",
        headers=club_headers,
        json={"club_id": 1},
    )
    assert denied_switch.status_code == 403

    # Sicherheitsinvariante: Selbst eine versehentliche super_admin-Rolle auf
    # einem Nebenverein darf niemals Plattform-/FLAPAMAMAKU-Zugriff geben.
    rogue_user = ok(
        client.post(
            "/api/users",
            headers=super_headers,
            json={
                "member_id": None,
                "username": "secondary-superadmin",
                "password": "SecondaryPass123!",
                "active": True,
                "role_key": "club_manager",
                "permission_overrides": {},
            },
        )
    ).json()
    rogue_user_id = int(rogue_user["id"])
    with connect() as db:
        db.execute(
            """
            UPDATE user_clubs
            SET role = 'super_admin'
            WHERE user_id = ? AND club_id = ?
            """,
            (rogue_user_id, test_club_id),
        )
        db.commit()

    rogue_login = ok(
        client.post(
            "/api/auth/login",
            json={
                "username": "secondary-superadmin",
                "password": "SecondaryPass123!",
            },
        )
    ).json()
    assert rogue_login["user"]["is_super_admin"] is False
    assert rogue_login["user"]["current_club_id"] == test_club_id
    assert [club["id"] for club in rogue_login["clubs"]] == [test_club_id]
    rogue_headers = {"Authorization": f"Bearer {rogue_login['token']}"}
    assert client.post(
        "/api/auth/club",
        headers=rogue_headers,
        json={"club_id": 1},
    ).status_code == 403
    assert client.put(
        f"/api/news/{flapa_news['id']}",
        headers=rogue_headers,
        json={"title": "Fremd", "text": "Nein", "date": "30.09.2026"},
    ).status_code == 404
    assert client.get(
        "/api/operator/billing/clubs",
        headers=rogue_headers,
    ).status_code == 403

    # 15. Club-Admin kann fremde FLAPAMAMAKU-Daten weder lesen noch verändern.
    assert client.put(
        f"/api/news/{flapa_news['id']}",
        headers=club_headers,
        json={"title": "Fremd", "text": "Nein", "date": "30.09.2026"},
    ).status_code == 404
    assert client.delete(
        f"/api/events/{flapa_event['id']}",
        headers=club_headers,
    ).status_code == 404
    assert client.put(
        f"/api/members/{flapa_member['id']}",
        headers=club_headers,
        json={"name": "Fremd", "role": "Mitglied", "since": "2026"},
    ).status_code == 404
    assert client.get(
        f"/api/content/{flapa_sections['documents']['id']}/document",
        headers=club_headers,
    ).status_code == 404
    assert client.get(
        f"/api/members/{flapa_member['id']}/photo",
        headers=club_headers,
    ).status_code == 404
    assert client.post(
        f"/api/events/{flapa_event['id']}/registration",
        headers=club_headers,
    ).status_code == 404

    # Testverein sieht ausschließlich eigene Daten.
    assert titles(ok(client.get("/api/news", headers=club_headers)).json()) == {
        "Testverein News"
    }
    assert titles(ok(client.get("/api/events", headers=club_headers)).json()) == {
        "Testverein Termin"
    }
    assert names(ok(client.get("/api/members", headers=club_headers)).json()) == {
        "Testverein Mitglied"
    }
    for section, expected in (
        ("hero", "Testverein Start"),
        ("documents", "Testverein Dokument"),
        ("photos", "Testverein Fotoalbum"),
        ("sujet", "Testverein Sujet nächstes Jahr"),
        ("archive", "Testverein Vergangenes Sujet"),
    ):
        rows = ok(
            client.get(f"/api/content?section={section}", headers=club_headers)
        ).json()
        assert expected in titles(rows)
        assert all(not title.startswith("FLAPA ") for title in titles(rows))

    # Direkter Zugriff auf Testverein-Uploads funktioniert für Testverein.
    ok(
        client.get(
            f"/api/content/{test_sections['documents']['id']}/document",
            headers=club_headers,
        )
    )
    gallery_rows = ok(
        client.get("/api/content?section=gallery", headers=club_headers)
    ).json()
    assert gallery_rows
    assert all(row.get("is_snapshot") is True for row in gallery_rows)
    first_album_image = int(album["images"][0]["id"])
    ok(
        client.get(
            f"/api/content/{test_sections['photos']['id']}/images/{first_album_image}",
            headers=club_headers,
        )
    )
    ok(
        client.get(
            f"/api/gallery/snapshots/{snapshot['snapshot_id']}/image",
            headers=club_headers,
        )
    )

    # 13. Zurück zu FLAPAMAMAKU: keine Testverein-Daten sichtbar.
    ok(
        client.post(
            "/api/auth/club",
            headers=super_headers,
            json={"club_id": 1},
        )
    )
    flapa_config_again = ok(
        client.get("/api/app-config", headers=super_headers)
    ).json()
    assert flapa_config_again["club_id"] == 1
    assert flapa_config_again["logo_url"] == flapa_logo_url
    assert titles(ok(client.get("/api/news", headers=super_headers)).json()) == {
        "FLAPA News"
    }
    assert titles(ok(client.get("/api/events", headers=super_headers)).json()) == {
        "FLAPA Termin"
    }
    assert names(ok(client.get("/api/members", headers=super_headers)).json()) == {
        "FLAPA Mitglied"
    }
    for section, expected in (
        ("hero", "FLAPA Start"),
        ("documents", "FLAPA Dokument"),
        ("gallery", "FLAPA Galerie"),
        ("photos", "FLAPA Fotoalbum"),
        ("sujet", "FLAPA Sujet nächstes Jahr"),
        ("archive", "FLAPA Vergangenes Sujet"),
    ):
        rows = ok(
            client.get(f"/api/content?section={section}", headers=super_headers)
        ).json()
        assert expected in titles(rows)
        assert all(not title.startswith("Testverein ") for title in titles(rows))

    # Fremde Testverein-Dateien/Bilder sind von FLAPAMAMAKU aus nicht abrufbar.
    assert client.get(
        f"/api/content/{test_sections['documents']['id']}/document",
        headers=super_headers,
    ).status_code == 404
    assert client.get(
        f"/api/members/{test_member['id']}/photo",
        headers=super_headers,
    ).status_code == 404
    assert client.get(
        f"/api/gallery/snapshots/{snapshot['snapshot_id']}/image",
        headers=super_headers,
    ).status_code == 404

    # Push bleibt ebenfalls getrennt.
    flapa_push = ok(client.get("/api/push/admin", headers=super_headers)).json()
    assert flapa_push["registered_devices_total"] == 1
    assert "FLAPA Push" in titles(flapa_push["notifications"])
    assert "Testverein Push" not in titles(flapa_push["notifications"])

    # Systemstatus ist mandantenbezogen.
    flapa_status = ok(client.get("/api/system/status", headers=super_headers)).json()
    assert flapa_status["members"] == 1
    assert flapa_status["registered_devices"] == 1

    # 14. Erneuter Wechsel beweist die Gegenrichtung.
    ok(
        client.post(
            "/api/auth/club",
            headers=super_headers,
            json={"club_id": test_club_id},
        )
    )
    test_status = ok(client.get("/api/system/status", headers=super_headers)).json()
    assert test_status["members"] == 1
    assert test_status["registered_devices"] == 1
    assert titles(ok(client.get("/api/news", headers=super_headers)).json()) == {
        "Testverein News"
    }

    # DB-Schlusskontrolle: keine versehentlich falsch zugeordneten Relationen.
    with connect() as db:
        assert db.execute(
            """
            SELECT COUNT(*)
            FROM member_filter_links
            WHERE member_id = ? AND club_id <> ?
            """,
            (test_member["id"], test_club_id),
        ).fetchone()[0] == 0
        assert db.execute(
            "SELECT COUNT(*) FROM push_tokens WHERE club_id = 1"
        ).fetchone()[0] == 1
        assert db.execute(
            "SELECT COUNT(*) FROM push_tokens WHERE club_id = ?",
            (test_club_id,),
        ).fetchone()[0] == 1

    print("package 9 full tenant isolation ok")


if __name__ == "__main__":
    main()
