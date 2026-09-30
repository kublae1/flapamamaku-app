from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app, connect, init_db


PASSWORD = "Billing-Test-2026"


def ok(response, expected: int = 200):
    assert response.status_code == expected, (
        f"{response.request.method} {response.request.url.path}: "
        f"{response.status_code} {response.text}"
    )
    return response


def login(client: TestClient, username: str):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": PASSWORD},
    )


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
            json={"username": "platform-admin", "password": PASSWORD, "member_id": None},
        )
    )
    super_login = ok(login(client, "platform-admin")).json()
    super_headers = {"Authorization": f"Bearer {super_login['token']}"}

    created = ok(
        client.post(
            "/api/clubs",
            headers=super_headers,
            json={
                "slug": "zahlungs-testverein",
                "name": "Zahlungs Testverein",
                "short_name": "ZTV",
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
    admin = ok(
        client.post(
            "/api/users",
            headers=super_headers,
            json={
                "member_id": None,
                "username": "ztv-admin",
                "password": PASSWORD,
                "active": True,
                "role_key": "admin",
                "permission_overrides": {},
            },
        )
    ).json()
    assert admin["current_club_id"] == club_id

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
    settings = ok(
        client.put(
            f"/api/operator/billing/clubs/{club_id}",
            headers=super_headers,
            json={
                "billing_email": "rechnung@example.invalid",
                "amount_rappen": 12000,
                "interval_months": 12,
                "due_days": 30,
                "next_invoice_date": yesterday,
                "auto_suspend": True,
            },
        )
    ).json()
    assert settings["billing_amount_rappen"] == 12000
    assert settings["billing_status"] == "active"

    first_run = ok(
        client.post("/api/operator/billing/run", headers=super_headers)
    ).json()
    assert first_run["created_invoices"] == 1

    invoices = ok(
        client.get(
            f"/api/operator/billing/clubs/{club_id}/invoices",
            headers=super_headers,
        )
    ).json()
    assert len(invoices) == 1
    invoice_id = int(invoices[0]["id"])
    assert invoices[0]["status"] == "open"
    assert invoices[0]["amount_rappen"] == 12000

    with connect() as db:
        db.execute(
            "UPDATE club_invoices SET due_date = ? WHERE id = ?",
            (yesterday, invoice_id),
        )
        db.commit()

    second_run = ok(
        client.post("/api/operator/billing/run", headers=super_headers)
    ).json()
    assert second_run["suspended_clubs"] == 1

    blocked = login(client, "ztv-admin")
    assert blocked.status_code == 403
    assert "Verein gesperrt" in blocked.json()["detail"]

    # The operator must keep access to the suspended club.
    switched = ok(
        client.post(
            "/api/auth/club",
            headers=super_headers,
            json={"club_id": club_id},
        )
    ).json()
    assert switched["club_id"] == club_id
    assert switched["club_role"] == "super_admin"

    paid = ok(
        client.post(
            f"/api/operator/billing/invoices/{invoice_id}/paid",
            headers=super_headers,
        )
    ).json()
    assert paid["status"] == "paid"

    restored = ok(login(client, "ztv-admin")).json()
    assert restored["user"]["current_club_id"] == club_id

    third_run = ok(
        client.post("/api/operator/billing/run", headers=super_headers)
    ).json()
    assert third_run["created_invoices"] == 0

    billing = ok(
        client.get("/api/operator/billing/clubs", headers=super_headers)
    ).json()
    club = next(item for item in billing if int(item["id"]) == club_id)
    assert club["billing_status"] == "active"
    assert club["open_invoice_count"] == 0

    flapa = next(item for item in billing if int(item["id"]) == 1)
    assert flapa["billing_status"] == "active"

    print("club billing and suspension end-to-end ok")


if __name__ == "__main__":
    main()
