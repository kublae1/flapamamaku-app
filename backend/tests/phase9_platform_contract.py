import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def call(base, path, method="GET", data=None, token=None, expect=None):
    body = None if data is None else json.dumps(data).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(base + path, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            raw = response.read()
            if expect is not None:
                assert response.status == expect, (path, response.status, raw)
            ctype = response.headers.get("Content-Type", "")
            return response.status, raw if "application/pdf" in ctype else json.loads(raw or b"{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        if expect is None or exc.code != expect:
            raise AssertionError((path, exc.code, raw)) from exc
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, raw


def wait(base, path):
    for _ in range(80):
        try:
            status, _ = call(base, path)
            if status == 200:
                return
        except Exception:
            time.sleep(0.15)
    raise RuntimeError("service did not become ready: " + base + path)


def main():
    with tempfile.TemporaryDirectory(prefix="phase9-") as tmp:
        tmp = Path(tmp)
        platform_db = tmp / "platform.db"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        env["FLAPAMAMAKU_PLATFORM_DB"] = str(platform_db)
        env["FLAPAMAMAKU_PLATFORM_BILLING_INTERVAL_SECONDS"] = "3600"

        platform = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.platform_runtime:app", "--host", "127.0.0.1", "--port", "8093"],
            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        club = None
        try:
            pbase = "http://127.0.0.1:8093"
            wait(pbase, "/api/platform/health")
            _, health = call(pbase, "/api/platform/health")
            assert health["schema"] == 1 and health["integrity"] == "ok" and not health["bootstrapped"]
            call(pbase, "/api/platform/dashboard", expect=401)
            call(pbase, "/api/platform/bootstrap", "POST", {"username": "platform-admin", "password": "Phase9Test!123"}, expect=200)
            call(pbase, "/api/platform/bootstrap", "POST", {"username": "second", "password": "Phase9Test!456"}, expect=409)
            _, login = call(pbase, "/api/platform/login", "POST", {"username": "platform-admin", "password": "Phase9Test!123"})
            token = login["token"]

            clubs = [
                ("flapamamaku", "FLAPAMAMAKU"),
                ("pilot-verein-a", "Pilot Verein A"),
                ("pilot-verein-b", "Pilot Verein B"),
            ]
            ids = {}
            for instance, name in clubs:
                _, row = call(pbase, "/api/platform/clubs", "POST", {
                    "instance_id": instance,
                    "name": name,
                    "api_base_url": "https://" + instance + ".example.invalid",
                    "billing_email": instance + "@example.invalid",
                    "monthly_fee_cents": 2500,
                    "currency": "CHF",
                    "billing_day": 1,
                    "due_days": 30,
                    "auto_suspend_overdue": True,
                }, token=token)
                ids[instance] = row["id"]

            _, dash = call(pbase, "/api/platform/dashboard", token=token)
            assert dash["clubs_total"] == 3 and dash["clubs_active"] == 3
            _, billing = call(pbase, "/api/platform/billing/run", "POST", token=token)
            assert billing["invoices_created"] == 3
            _, invoices = call(pbase, "/api/platform/invoices", token=token)
            assert len(invoices) == 3 and all(i["amount_cents"] == 2500 for i in invoices)
            status, pdf = call(pbase, f"/api/platform/invoices/{invoices[0]['id']}/pdf", token=token)
            assert status == 200 and pdf.startswith(b"%PDF-1.4")

            pilot_id = ids["pilot-verein-a"]
            call(pbase, f"/api/platform/clubs/{pilot_id}/suspend", "POST", {"reason": "Phase 9 Sperrtest"}, token=token)

            club_env = env.copy()
            club_env["FLAPAMAMAKU_DB"] = str(tmp / "club.db")
            club_env["FLAPAMAMAKU_BACKUP_DIR"] = str(tmp / "backups")
            club_env["FLAPAMAMAKU_INSTANCE_ID"] = "pilot-verein-a"
            club_env["FLAPAMAMAKU_ENV"] = "development"
            club = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.runtime:app", "--host", "127.0.0.1", "--port", "8094"],
                cwd=ROOT, env=club_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            cbase = "http://127.0.0.1:8094"
            wait(cbase, "/api/health")
            _, blocked = call(cbase, "/api/news", expect=423)
            assert blocked["club_status"] == "suspended"
            call(pbase, f"/api/platform/clubs/{pilot_id}/resume", "POST", token=token)
            status, _ = call(cbase, "/api/news")
            assert status == 200

            with sqlite3.connect(platform_db) as db:
                inv = db.execute("SELECT id FROM platform_invoices WHERE club_id=?", (pilot_id,)).fetchone()[0]
                db.execute("UPDATE platform_invoices SET due_date=? WHERE id=?", ((date.today()-timedelta(days=1)).isoformat(), inv))
                db.commit()
            _, billing2 = call(pbase, "/api/platform/billing/run", "POST", token=token)
            assert billing2["clubs_suspended"] == 1
            call(cbase, "/api/news", expect=423)
            call(pbase, f"/api/platform/invoices/{inv}/paid", "POST", token=token)
            status, _ = call(cbase, "/api/news")
            assert status == 200

            _, audit = call(pbase, "/api/platform/audit", token=token)
            actions = {row["action"] for row in audit}
            assert {"platform.bootstrap", "club.create", "invoice.create", "club.suspend", "invoice.paid"}.issubset(actions)
            with sqlite3.connect(platform_db) as db:
                assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                assert db.execute("SELECT COUNT(*) FROM platform_clubs").fetchone()[0] == 3
            print("PHASE9 PLATFORM CONTRACT OK: superuser, 3 clubs, billing, PDF, suspend/resume, audit")
        finally:
            if club is not None:
                club.terminate(); club.wait(timeout=5)
            platform.terminate(); platform.wait(timeout=5)


if __name__ == "__main__":
    main()
