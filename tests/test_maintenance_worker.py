from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from ai_sorter.core.database import Database
from ai_sorter.core.models import FileLocationRecord, FileRecord
from ai_sorter.gui.maintenance_worker import MaintenanceWorker
from ai_sorter.modules.scanner import Scanner


class MaintenanceWorkerTests(unittest.TestCase):
    def test_check_locations_reports_size_and_timestamp_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            present = root / "present.jpg"
            present.write_bytes(b"present")
            expected_size = present.stat().st_size
            expected_modified = datetime.fromtimestamp(present.stat().st_mtime).replace(microsecond=0)

            db = Database(root / "project.db")
            db.open()
            try:
                sha = "b" * 128
                db.upsert_file(FileRecord(sha, expected_size, modified_at=expected_modified, status="ACTIVE"))
                db.upsert_file_location(FileLocationRecord(
                    sha512=sha,
                    absolute_path=str(present),
                    file_size=expected_size,
                    modified_at=expected_modified,
                    location_status="ACTIVE",
                ))

                present.write_bytes(b"present-but-changed")
                os.utime(present, (present.stat().st_atime, present.stat().st_mtime + 5))

                text = MaintenanceWorker(db, "check_locations")._check_all_locations()

                status = db.connection.execute(
                    "SELECT location_status FROM file_location WHERE sha512 = ?", (sha,)
                ).fetchone()[0]
                self.assertEqual(status, "ACTIVE")
                self.assertIn("Size mismatches: 1", text)
                self.assertIn("Timestamp mismatches: 1", text)
                self.assertIn("Marked missing: 0", text)
            finally:
                db.close()

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
