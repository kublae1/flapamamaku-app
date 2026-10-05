from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="flap-phase68-") as temp_dir:
        root = Path(temp_dir)
        db_path = root / "flapamamaku.db"
        backup_dir = root / "backups"

        os.environ["FLAPAMAMAKU_DB"] = str(db_path)
        os.environ["FLAPAMAMAKU_BACKUP_DIR"] = str(backup_dir)
        os.environ["FLAPAMAMAKU_INSTANCE_ID"] = "flapamamaku"
        os.environ["FLAPAMAMAKU_ENV"] = "development"

        from app import main as api

        api.DB_PATH = db_path
        api.BACKUP_DIR = backup_dir
        api.init_db()

        with api.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS phase68_probe (id INTEGER PRIMARY KEY, value TEXT NOT NULL)"
            )
            db.execute("INSERT OR REPLACE INTO phase68_probe(id, value) VALUES (1, 'before')")
            db.commit()

        backup = api._create_database_backup("phase68-test")
        assert backup.exists(), "backup file was not created"
        assert backup.parent == backup_dir, "backup was created outside configured directory"
        assert api._validate_restore_database(backup) == api.CURRENT_SCHEMA_VERSION

        with api.connect() as db:
            db.execute("UPDATE phase68_probe SET value = 'after' WHERE id = 1")
            db.commit()

        result = api._restore_database_backup(backup)
        assert result["restored"] is True
        assert result["current_schema_version"] == api.CURRENT_SCHEMA_VERSION
        assert result["sessions_cleared"] is True
        assert result["safety_backup"]["name"].endswith(".db")

        with api.connect() as db:
            restored = db.execute("SELECT value FROM phase68_probe WHERE id = 1").fetchone()
            integrity = db.execute("PRAGMA integrity_check").fetchone()
        assert restored is not None and restored[0] == "before", "restore did not recover backup state"
        assert integrity is not None and str(integrity[0]).lower() == "ok"

        corrupt = backup_dir / "corrupt.db"
        corrupt.write_bytes(b"not-a-sqlite-database")
        try:
            api._validate_restore_database(corrupt)
        except RuntimeError:
            pass
        else:
            raise AssertionError("corrupt backup was accepted")

        backups = api._backup_files()
        assert any(path.name == backup.name for path in backups)
        assert any("before-restore" in path.name for path in backups)

        print("Phase 6 operations validation passed")
        print(f"schema={api.CURRENT_SCHEMA_VERSION}")
        print(f"backup_count={len(backups)}")


if __name__ == "__main__":
    main()
