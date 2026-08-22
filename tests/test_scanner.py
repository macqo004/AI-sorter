"""Scanner integration tests using only the Python standard library."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_sorter.core.database import Database
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
                discovered_paths: list[str] = []
                scanner = Scanner(db, worker_count=1)
                scanner.scan(root, lambda progress: discovered_paths.append(progress.current_discovery_path or ""))
                seen = [path for path in discovered_paths if path.endswith(("6.jpg", "A.jpg", "C.jpg", "M.jpg", "S.jpg"))]
                self.assertEqual(
                    [Path(path).name for path in seen[-5:]],
                    ["6.jpg", "A.jpg", "C.jpg", "M.jpg", "S.jpg"],
                )
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
