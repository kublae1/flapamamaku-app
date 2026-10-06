from __future__ import annotations

import io
import os
import sys
import time
from typing import Any

import requests

BASE_URL = os.getenv("PHASE7_BASE_URL", "http://127.0.0.1:8087").rstrip("/")


def fail(message: str) -> None:
    print(f"PHASE7 PRAXISTEST FAILED: {message}", file=sys.stderr)
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
        timeout=20,
        **kwargs,
    )
    if response.status_code not in expected:
        fail(f"{method} {path}: {response.status_code}: {response.text[:500]}")
    return response


def wait_for_server() -> None:
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            if requests.get(f"{BASE_URL}/api/health", timeout=2).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)
    fail("backend did not become healthy")


def login() -> str:
    status = request("GET", "/api/auth/status").json()
    if status.get("bootstrap_required"):
        request(
            "POST",
            "/api/auth/bootstrap",
            expected=(200, 201),
            json={"username": "phase7-admin", "password": "Phase7Test!123"},
        )
    payload = request(
        "POST",
        "/api/auth/login",
        json={"username": "phase7-admin", "password": "Phase7Test!123"},
    ).json()
    token = str(payload.get("token") or "")
    if not token:
        fail("login returned no token")
    return token


def main() -> None:
    wait_for_server()
    token = login()

    health = request("GET", "/api/health").json()
    if health.get("status") != "ok":
        fail("health endpoint is not ok")
    if health.get("instance_id") != "flapamamaku":
        fail(f"unexpected instance: {health.get('instance_id')}")

    status = request("GET", "/api/system/status", token=token).json()
    if status.get("database_integrity") != "ok":
        fail(f"database integrity not ok: {status.get('database_integrity')}")

    backup = request("POST", "/api/system/backups", token=token).json()
    name = str(backup.get("name") or "")
    if not name.endswith(".db"):
        fail("manual backup returned no .db file")

    backup_bytes = request("GET", f"/api/system/backups/{name}", token=token).content
    if len(backup_bytes) < 1024:
        fail("downloaded backup is unexpectedly small")

    restore = request(
        "POST",
        "/api/system/restore",
        token=token,
        files={"backup_file": (name, io.BytesIO(backup_bytes), "application/octet-stream")},
    ).json()
    if restore.get("restored") is not True or restore.get("sessions_cleared") is not True:
        fail(f"restore did not complete safely: {restore}")

    old_token = requests.get(
        f"{BASE_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if old_token.status_code != 401:
        fail(f"restore must invalidate sessions, got {old_token.status_code}")

    token = login()
    backups = request("GET", "/api/system/backups", token=token).json()
    if len(backups) < 2:
        fail("expected manual and pre-restore safety backups")

    status = request("GET", "/api/system/status", token=token).json()
    if status.get("backup_count", 0) < 2:
        fail("system status did not expose backup inventory")
    if status.get("database_integrity") != "ok":
        fail("database integrity failed after restore")

    print("PHASE7 PRAXISTEST OK")


if __name__ == "__main__":
    main()
