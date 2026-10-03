from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from ai_sorter.core.database import Database, DatabaseError
from ai_sorter.core.models import FileLocationRecord, FileRecord
from ai_sorter.renamer import RenameProposal, RenamerEngine
from ai_sorter.gui.renamer_worker_fixed import RenamerWorker
from ai_sorter.modules.scanner import Scanner


class RenamerWorkerDatabaseTests(unittest.TestCase):
    def test_ambiguous_active_source_sha_is_rejected_before_filesystem_rename(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "070_x19.jpg"
            destination = root / "070.jpg"
            source.write_bytes(b"test")

            first_sha = "a" * 128
            second_sha = "b" * 128
            db = Database(root / "project.db")
            db.open()
            try:
                db.upsert_file(FileRecord(first_sha, 4))
                db.upsert_file(FileRecord(second_sha, 4))
                db.upsert_file_location(
                    FileLocationRecord(first_sha, str(source.resolve()), 4, location_status="ACTIVE")
                )
                db.upsert_file_location(
                    FileLocationRecord(second_sha, str(source.resolve()), 4, location_status="ACTIVE")
                )

                worker = RenamerWorker(db, root)
                worker.proposals = [
                    RenameProposal(source, destination, "test", True, "test")
                ]

                with self.assertRaises(DatabaseError):
                    worker._execute_with_progress()

                self.assertTrue(source.exists())
                self.assertFalse(destination.exists())
            finally:
                db.close()


    def test_scan_rename_scan_reuses_existing_sha512(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "9Cloud.us_0332-sample.jpg"
            source.write_bytes(b"rename-and-scan-integration")

            db = Database(root / "project.db")
            db.open()
            try:
                first = Scanner(db, worker_count=1).scan(root)
                self.assertEqual(first.scanned, 1)
                self.assertEqual(first.skipped, 0)

                proposal = RenamerEngine().propose(source)
                self.assertIsNotNone(proposal)
                assert proposal is not None
                self.assertEqual(proposal.destination.name, "sample.jpg")

                worker = RenamerWorker(db, root)
                worker.proposals = [proposal]
                executed = worker._execute_with_progress()
                self.assertEqual(len(executed), 1)
                updated, conflicts = worker._reconcile_database_after_rename(
                    [(proposal.source, proposal.destination) for proposal in executed]
                )
                self.assertEqual(updated, 1)
                self.assertEqual(conflicts, 0)

                second = Scanner(db, worker_count=1).scan(root)
                self.assertEqual(second.scanned, 0)
                self.assertEqual(second.skipped, 1)
                self.assertEqual(second.failed, 0)

                row = db.connection.execute(
                    "SELECT sha512, location_status FROM file_location "
                    "WHERE absolute_path = ? AND location_status = 'ACTIVE'",
                    (str((root / "sample.jpg").resolve()),),
                ).fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row["location_status"], "ACTIVE")
                self.assertEqual(row["sha512"], hashlib.sha512(b"rename-and-scan-integration").hexdigest())
            finally:
                db.close()


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
