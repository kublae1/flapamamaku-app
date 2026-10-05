"""Regression test for the October 2026 tenant/admin production incident.

Proves three invariants:
1. same-origin PC admin requests work in production without X-Club-Instance;
2. an explicitly wrong club instance is still rejected with HTTP 409;
3. legacy administrators degraded by the role migration are repaired to admin.
"""

from __future__ import annotations

import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8091"
INSTANCE_ID = "flapamamaku"


def fail(message: str) -> None:
    print(f"CRITICAL REGRESSION FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def wait_for_server(process: subprocess.Popen[str]) -> None:
    deadline = time.time() + 25
    while time.time() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            fail(f"backend exited early with {process.returncode}: {output[-2000:]}")
        try:
            response = requests.get(f"{BASE_URL}/api/health", timeout=1)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.25)
    fail("backend did not become healthy")


def start_backend(db_path: Path, backup_dir: Path) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.update(
        {
            "FLAPAMAMAKU_DB": str(db_path),
            "FLAPAMAMAKU_BACKUP_DIR": str(backup_dir),
            "FLAPAMAMAKU_INSTANCE_ID": INSTANCE_ID,
            "FLAPAMAMAKU_ENV": "production",
            "FLAPAMAMAKU_ALLOWED_ORIGINS": "https://app.example.invalid",
            "FLAPAMAMAKU_BUILD_SHA": "critical-regression-test",
        }
    )
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8091",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    wait_for_server(process)
    return process


def stop_backend(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def call(
    method: str,
    path: str,
    *,
    token: str | None = None,
    expected: int | tuple[int, ...] = 200,
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
    accepted = (expected,) if isinstance(expected, int) else expected
    if response.status_code not in accepted:
        fail(
            f"{method} {path}: expected {accepted}, got "
            f"{response.status_code}: {response.text[:500]}"
        )
    return response


def bootstrap_and_login() -> str:
    status = call("GET", "/api/auth/status").json()
    if status.get("bootstrap_required"):
        call(
            "POST",
            "/api/auth/bootstrap",
            expected=(200, 201),
            json={"username": "incident-admin", "password": "IncidentTest!123"},
        )
    payload = call(
        "POST",
        "/api/auth/login",
        json={"username": "incident-admin", "password": "IncidentTest!123"},
    ).json()
    token = str(payload.get("token") or "")
    if not token:
        fail("login returned no token")
    return token


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="flapamamaku-critical-") as tmp:
        root = Path(tmp)
        db_path = root / "club.db"
        backup_dir = root / "backups"
        backup_dir.mkdir()

        process = start_backend(db_path, backup_dir)
        try:
            token = bootstrap_and_login()

            # Same-origin PC admin does not manufacture X-Club-Instance.
            me = call("GET", "/api/auth/me", token=token).json()
            if me.get("username") != "incident-admin":
                fail("PC admin session did not resolve without tenant header")

            # A real write operation must also work from the browser admin.
            created = call(
                "POST",
                "/api/news",
                token=token,
                expected=(200, 201),
                json={
                    "title": "Admin-Reparaturtest",
                    "text": "Schreibzugriff funktioniert wieder.",
                    "date": "05.10.2026",
                    "image_url": "",
                },
            ).json()
            if not created.get("id"):
                fail("PC admin write returned no saved record")

            # Mobile/white-label clients that explicitly present another club
            # must remain blocked at the HTTP tenant boundary.
            wrong = call(
                "GET",
                "/api/news",
                token=token,
                headers={"X-Club-Instance": "verein-3"},
                expected=409,
            ).json()
            if wrong.get("expected_instance_id") != INSTANCE_ID:
                fail("wrong-club response did not identify FLAPAMAMAKU")
        finally:
            stop_backend(process)

        # Reproduce the legacy migration damage: historic admin marker remains
        # true, but role_key was downgraded because a newly introduced right
        # defaulted to false.
        with sqlite3.connect(db_path) as db:
            db.execute(
                """
                UPDATE users
                SET role_key = 'member',
                    permission_overrides = ?,
                    can_manage_users = 1
                WHERE username = 'incident-admin'
                """,
                (json.dumps({"can_manage_users": True}),),
            )
            db.commit()

        process = start_backend(db_path, backup_dir)
        try:
            token = bootstrap_and_login()
            repaired = call("GET", "/api/auth/me", token=token).json()
            if repaired.get("role_key") != "admin":
                fail(f"legacy administrator was not repaired: {repaired.get('role_key')}")
            required = (
                "can_news",
                "can_events",
                "can_members",
                "can_documents",
                "can_photos",
                "can_gallery_upload",
                "can_polls",
                "can_links",
                "can_contact",
                "can_about",
                "can_admin_page",
                "can_manage_settings",
                "can_manage_users",
            )
            missing = [key for key in required if repaired.get(key) is not True]
            if missing:
                fail("repaired administrator still lacks rights: " + ", ".join(missing))
        finally:
            stop_backend(process)

    print("CRITICAL TENANT/ADMIN REGRESSION OK")


if __name__ == "__main__":
    main()
