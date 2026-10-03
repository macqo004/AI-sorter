from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_sorter.core.database import Database
from ai_sorter.core.models import FileLocationRecord, FileRecord
from ai_sorter.gui.renamer_worker_fixed import RenamerWorker


class RenamerWorkerDatabaseTests(unittest.TestCase):
    def test_reconcile_ignores_stale_missing_sha_at_source_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "070_x19.jpg"
            destination = root / "070.jpg"
            active_sha = "a" * 128
            stale_sha = "b" * 128

            db = Database(root / "project.db")
            db.open()
            try:
                db.upsert_file(FileRecord(active_sha, 100))
                db.upsert_file(FileRecord(stale_sha, 100))
                db.upsert_file_location(
                    FileLocationRecord(active_sha, str(source.resolve()), 100, location_status="ACTIVE")
                )
                db.upsert_file_location(
                    FileLocationRecord(stale_sha, str(source.resolve()), 100, location_status="MISSING")
                )

                worker = RenamerWorker(db, root)
                updated, reconciled = worker._reconcile_database_after_rename(
                    [(source, destination)]
                )

                self.assertEqual(updated, 1)
                self.assertEqual(reconciled, 0)

                active_row = db.connection.execute(
                    "SELECT sha512, location_status FROM file_location "
                    "WHERE absolute_path = ? AND sha512 = ?",
                    (str(destination.resolve()), active_sha),
                ).fetchone()
                self.assertIsNotNone(active_row)
                self.assertEqual(active_row["location_status"], "ACTIVE")

                stale_row = db.connection.execute(
                    "SELECT sha512, location_status FROM file_location "
                    "WHERE absolute_path = ? AND sha512 = ?",
                    (str(source.resolve()), stale_sha),
                ).fetchone()
                self.assertIsNotNone(stale_row)
                self.assertEqual(stale_row["location_status"], "MISSING")
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
