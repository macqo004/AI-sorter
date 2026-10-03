"""Scanner integration tests using only the Python standard library."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from ai_sorter.core.database import Database
from ai_sorter.core.models import FileLocationRecord, FileRecord
from ai_sorter.modules.scanner import Scanner


class ScannerTests(unittest.TestCase):
    def test_new_file_is_registered_and_same_content_shares_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "a.jpg"
            second = root / "nested" / "b.jpg"
            second.parent.mkdir()
            payload = b"same-content-for-scanner-test"
            first.write_bytes(payload)
            second.write_bytes(payload)

            db = Database(root / "project.db")
            db.open()
            try:
                summary = Scanner(db, worker_count=2).scan(root)
                self.assertEqual(summary.failed, 0)
                self.assertEqual(summary.discovered, 2)
                self.assertEqual(summary.scanned, 2)
                self.assertEqual(summary.skipped, 0)
                status = db.status()
                self.assertEqual(status.file_count, 1)
                self.assertEqual(status.location_count, 2)
            finally:
                db.close()

    def test_scan_repairs_multiple_active_identities_for_one_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file_path = root / "ambiguous.jpg"
            payload = b"scanner-active-identity-repair"
            file_path.write_bytes(payload)

            actual_sha = hashlib.sha512(payload).hexdigest()
            stale_sha = "b" * 128
            db = Database(root / "project.db")
            db.open()
            try:
                candidate = next(Scanner(db, worker_count=1)._discover(root))
                db.upsert_file(FileRecord(actual_sha, candidate.size, modified_at=candidate.modified_at))
                db.upsert_file(FileRecord(stale_sha, candidate.size, modified_at=candidate.modified_at))
                db.upsert_file_location(
                    FileLocationRecord(
                        actual_sha,
                        str(file_path.resolve()),
                        candidate.size,
                        candidate.modified_at,
                        "ACTIVE",
                    )
                )
                db.upsert_file_location(
                    FileLocationRecord(
                        stale_sha,
                        str(file_path.resolve()),
                        candidate.size,
                        candidate.modified_at,
                        "ACTIVE",
                    )
                )

                summary = Scanner(db, worker_count=1).scan(root)
                self.assertEqual(summary.failed, 0)
                self.assertEqual(summary.scanned, 1)

                rows = db.connection.execute(
                    "SELECT sha512, location_status FROM file_location "
                    "WHERE absolute_path = ? ORDER BY sha512",
                    (str(file_path.resolve()),),
                ).fetchall()
                self.assertEqual(
                    [(row["sha512"], row["location_status"]) for row in rows],
                    [(actual_sha, "ACTIVE"), (stale_sha, "MISSING")],
                )
            finally:
                db.close()


    def test_second_scan_reuses_metadata_without_new_file_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file_path = root / "image.png"
            file_path.write_bytes(b"scanner-repeat-test")
            db = Database(root / "project.db")
            db.open()
            try:
                first = Scanner(db).scan(root)
                second = Scanner(db).scan(root)
                self.assertEqual(first.saved, 1)
                self.assertEqual(first.scanned, 1)
                self.assertEqual(second.saved, 0)
                self.assertEqual(second.scanned, 0)
                self.assertEqual(second.skipped, 1)
            finally:
                db.close()

    def test_missing_location_is_marked_after_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file_path = root / "remove-me.webp"
            file_path.write_bytes(b"missing-file-test")
            db = Database(root / "project.db")
            db.open()
            try:
                Scanner(db).scan(root)
                file_path.unlink()
                summary = Scanner(db).scan(root)
                self.assertEqual(summary.missing, 1)
            finally:
                db.close()

    def test_discovery_order_is_alphabetical(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ["S.jpg", "C.jpg", "6.jpg", "M.jpg", "A.jpg"]:
                (root / name).write_bytes(name.encode("ascii"))

            db = Database(root / "project.db")
            db.open()
            try:
                scanner = Scanner(db, worker_count=1)
                names = [candidate.path.name for candidate in scanner._discover(root)]
                self.assertEqual(names, ["6.jpg", "A.jpg", "C.jpg", "M.jpg", "S.jpg"])
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
