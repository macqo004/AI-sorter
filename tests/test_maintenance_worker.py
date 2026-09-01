from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_sorter.core.database import Database
from ai_sorter.core.models import FileLocationRecord, FileRecord
from ai_sorter.gui.maintenance_worker import MaintenanceWorker
from ai_sorter.modules.scanner import Scanner


class MaintenanceWorkerTests(unittest.TestCase):
    def test_cleanup_removes_missing_but_preserves_archived_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            present = root / "present.jpg"
            present.write_bytes(b"present")
            missing = root / "missing.jpg"

            db = Database(root / "project.db")
            db.open()
            try:
                Scanner(db, worker_count=1).scan(root)
                sha = db.connection.execute("SELECT sha512 FROM file_record").fetchone()[0]
                db.upsert_file_location(FileLocationRecord(
                    sha512=sha,
                    absolute_path=str(missing),
                    file_size=7,
                    location_status="MISSING",
                ))
                archived_sha = "a" * 128
                db.upsert_file(FileRecord(archived_sha, 10, status="ARCHIVED"))

                worker = MaintenanceWorker(db, "cleanup_inactive")
                text = worker._cleanup_inactive()

                remaining_missing = db.connection.execute(
                    "SELECT COUNT(*) FROM file_location WHERE location_status = 'MISSING'"
                ).fetchone()[0]
                archived = db.connection.execute(
                    "SELECT status FROM file_record WHERE sha512 = ?", (archived_sha,)
                ).fetchone()[0]
                self.assertEqual(remaining_missing, 0)
                self.assertEqual(archived, "ARCHIVED")
                self.assertIn("Removed missing locations", text)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
