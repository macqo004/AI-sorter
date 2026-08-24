"""Tests for persistent manual review labels."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_sorter.core.database import Database
from ai_sorter.core.manual_review import ManualReviewStore
from ai_sorter.core.module_result_cleanup import ModuleResultCleanup
from ai_sorter.modules.color_analysis import ColorAnalysis
from ai_sorter.modules.scanner import Scanner
from PIL import Image


class ManualReviewTests(unittest.TestCase):
    def _setup(self) -> tuple[Database, Path, tempfile.TemporaryDirectory[str]]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        image_path = root / "test.png"
        Image.new("RGB", (32, 32), (180, 20, 20)).save(image_path)
        db = Database(root / "project.db")
        db.open()
        Scanner(db, worker_count=1).scan(root)
        return db, image_path, temp

    def test_review_survives_module_result_cleanup(self) -> None:
        db, image_path, temp = self._setup()
        try:
            ColorAnalysis(db, worker_count=1).run()
            sha = db.connection.execute("SELECT sha512 FROM file_record LIMIT 1").fetchone()["sha512"]
            reviews = ManualReviewStore(db)
            reviews.set_label(sha, "mostly_monochrome")
            self.assertEqual(reviews.get_label(sha), "mostly_monochrome")

            cleanup = ModuleResultCleanup(db)
            self.assertEqual(cleanup.clear_results("color_analysis", "color_analysis", image_path.parent), 1)
            self.assertEqual(reviews.get_label(sha), "mostly_monochrome")
        finally:
            db.close()
            temp.cleanup()

    def test_review_labels_can_be_changed_and_cleared(self) -> None:
        db, _image_path, temp = self._setup()
        try:
            sha = db.connection.execute("SELECT sha512 FROM file_record LIMIT 1").fetchone()["sha512"]
            reviews = ManualReviewStore(db)
            reviews.set_label(sha, "monochrome")
            self.assertEqual(reviews.get_label(sha), "monochrome")
            reviews.set_label(sha, "normal")
            self.assertEqual(reviews.get_label(sha), "normal")
            reviews.clear_label(sha)
            self.assertIsNone(reviews.get_label(sha))
        finally:
            db.close()
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
