from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
PROFILE_DIR = ROOT / "config" / "white-label"
PILOT_NAMES = ("pilot-verein-a", "pilot-verein-b", "pilot-verein-c")


def run_instance(profile: dict[str, object], db_path: Path, backup_dir: Path) -> None:
    code = r'''
from app import main
main.init_db()
with main.connect() as db:
    db.execute(
        "INSERT INTO news(title, text, date, image_url, sort_order, created_at) VALUES (?, ?, ?, '', 1, ?)",
        (main.INSTANCE_ID, "pilot-isolation", "2026-10-05", "2026-10-05T00:00:00+00:00"),
    )
    db.commit()
print(main.INSTANCE_ID)
'''
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(BACKEND),
            "FLAPAMAMAKU_DB": str(db_path),
            "FLAPAMAMAKU_BACKUP_DIR": str(backup_dir),
            "FLAPAMAMAKU_INSTANCE_ID": str(profile["instance_id"]),
            "FLAPAMAMAKU_ENV": "development",
        }
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip().splitlines()[-1] == profile["instance_id"]


def main() -> None:
    profiles: list[dict[str, object]] = []
    for name in PILOT_NAMES:
        path = PROFILE_DIR / f"{name}.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        assert profile["id"] == name
        assert profile["instance_id"] == name
        assert profile["allow_server_change"] is False
        profiles.append(profile)

    assert len({str(p["instance_id"]) for p in profiles}) == 3
    assert len({str(p["api_base_url"]) for p in profiles}) == 3

    with tempfile.TemporaryDirectory(prefix="flap-pilot-matrix-") as temp_dir:
        root = Path(temp_dir)
        databases: dict[str, Path] = {}

        for profile in profiles:
            instance_id = str(profile["instance_id"])
            instance_root = root / instance_id
            instance_root.mkdir(parents=True)
            db_path = instance_root / "flapamamaku.db"
            run_instance(profile, db_path, instance_root / "backups")
            databases[instance_id] = db_path

        for instance_id, db_path in databases.items():
            with sqlite3.connect(db_path) as db:
                db.row_factory = sqlite3.Row
                version = int(
                    db.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()[0]
                )
                rows = db.execute("SELECT title, club_id FROM news").fetchall()
                assert version == 10, f"{instance_id}: unexpected schema version {version}"
                assert len(rows) == 1
                assert rows[0]["title"] == instance_id
                assert rows[0]["club_id"] == instance_id

                try:
                    db.execute(
                        "INSERT INTO news(title, text, date, image_url, sort_order, created_at, club_id) "
                        "VALUES ('cross-tenant', 'forbidden', '2026-10-05', '', 2, '2026-10-05', ?)",
                        ("another-club",),
                    )
                    db.commit()
                except sqlite3.IntegrityError:
                    db.rollback()
                else:
                    raise AssertionError(f"{instance_id}: tenant guard accepted foreign club_id")

        observed = {}
        for instance_id, db_path in databases.items():
            with sqlite3.connect(db_path) as db:
                observed[instance_id] = [row[0] for row in db.execute("SELECT title FROM news")]
        for instance_id in PILOT_NAMES:
            assert observed[instance_id] == [instance_id]

    print("Phase 8 pilot matrix passed for 3 isolated club instances")


if __name__ == "__main__":
    main()
