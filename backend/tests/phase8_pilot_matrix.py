from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
PROFILE_DIR = ROOT / "config" / "white-label"
PILOT_NAMES = ("pilot-verein-a", "pilot-verein-b", "pilot-verein-c")


def current_schema_version() -> int:
    source = (BACKEND / "app" / "main.py").read_text(encoding="utf-8")
    match = re.search(r"^CURRENT_SCHEMA_VERSION\s*=\s*(\d+)\s*$", source, re.MULTILINE)
    assert match is not None, "CURRENT_SCHEMA_VERSION not found"
    return int(match.group(1))


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
    expected_schema = current_schema_version()
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

        observed: dict[str, list[str]] = {}
        for instance_id, db_path in databases.items():
            with sqlite3.connect(db_path) as db:
                db.row_factory = sqlite3.Row
                version = int(
                    db.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()[0]
                )
                assert version == expected_schema, (
                    f"{instance_id}: unexpected schema version {version}; expected {expected_schema}"
                )

                root_club = db.execute(
                    "SELECT id, slug FROM clubs WHERE active = 1 ORDER BY id LIMIT 1"
                ).fetchone()
                assert root_club is not None, f"{instance_id}: no active root club"

                rows = db.execute("SELECT title, club_id FROM news ORDER BY id").fetchall()
                assert len(rows) == 1
                assert rows[0]["title"] == instance_id
                assert int(rows[0]["club_id"]) == int(root_club["id"])

                # The recovered architecture intentionally supports multiple clubs
                # in one database. Phase-8 therefore verifies referential tenant
                # ownership instead of the obsolete single-instance text guard.
                foreign = db.execute(
                    "SELECT COUNT(*) FROM news n LEFT JOIN clubs c ON c.id = n.club_id WHERE c.id IS NULL"
                ).fetchone()[0]
                assert int(foreign) == 0, f"{instance_id}: orphaned tenant content"
                observed[instance_id] = [str(row["title"]) for row in rows]

        for instance_id in PILOT_NAMES:
            assert observed[instance_id] == [instance_id]

    print(
        f"Phase 8 pilot matrix passed for 3 isolated deployments at schema {expected_schema}; "
        "integrated multi-club ownership preserved"
    )


if __name__ == "__main__":
    main()
