from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from ai_sorter.core.database import Database
from ai_sorter.modules.color_analysis import ColorAnalysis
from ai_sorter.modules.scanner import Scanner


class ScannerTimestampAndScopeTests(unittest.TestCase):
    def test_scanner_stores_local_whole_second_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_path = root / "timestamp.png"
            Image.new("RGB", (8, 8), "white").save(image_path)

            db = Database(root / "project.db")
            db.open()
            try:
                candidate = next(Scanner(db, worker_count=1)._discover(root))
                self.assertIsNone(candidate.modified_at.tzinfo)
                self.assertEqual(candidate.modified_at.microsecond, 0)
                Scanner(db, worker_count=1).scan(root)
                stored = db.connection.execute(
                    "SELECT modified_at FROM file_location WHERE absolute_path = ?",
                    (str(image_path.resolve()),),
                ).fetchone()[0]
                self.assertEqual(stored, candidate.modified_at.isoformat(sep=" "))
            finally:
                db.close()

    def test_color_analysis_scope_is_recursive(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scope = root / "scope"
            nested = scope / "nested"
            other = root / "other"
            nested.mkdir(parents=True)
            other.mkdir()
            Image.new("RGB", (16, 16), "white").save(scope / "a.jpg")
            Image.new("RGB", (16, 16), "white").save(nested / "b.jpg")
            Image.new("RGB", (16, 16), "white").save(other / "c.jpg")

            db = Database(root / "project.db")
            db.open()
            try:
                Scanner(db, worker_count=1).scan(root)
                summary = ColorAnalysis(db, worker_count=1, scope_root=scope).run()
                self.assertEqual(summary.considered, 2)
                self.assertEqual(summary.processed, 2)
                self.assertEqual(summary.failed, 0)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
