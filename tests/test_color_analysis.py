"""Tests for DOC-102 Color Analysis."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from ai_sorter.core.database import Database
from ai_sorter.modules.color_analysis import ColorAnalysis
from ai_sorter.modules.scanner import Scanner


class ColorAnalysisTests(unittest.TestCase):
    def _run(self, image: Image.Image) -> tuple[Database, Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        image_path = root / "test.png"
        image.save(image_path)
        db = Database(root / "project.db")
        db.open()
        Scanner(db, worker_count=1).scan(root)
        # Keep the TemporaryDirectory alive by attaching it to the database instance.
        db._test_tempdir = temp  # type: ignore[attr-defined]
        return db, image_path

    def test_black_and_white_image(self) -> None:
        image = Image.new("RGB", (32, 32), "white")
        for x in range(16):
            for y in range(32):
                image.putpixel((x, y), (0, 0, 0))
        db, _ = self._run(image)
        try:
            summary = ColorAnalysis(db, worker_count=1).run()
            self.assertEqual(summary.failed, 0)
            row = db.connection.execute(
                "SELECT payload_json FROM analysis_result WHERE module_id = 'color_analysis'"
            ).fetchone()
            payload = json.loads(row["payload_json"])
            self.assertTrue(payload["is_bw"])
            self.assertFalse(payload["is_mostly_bw"])
        finally:
            db.close()

    def test_strongly_red_image_is_monochrome(self) -> None:
        image = Image.new("RGB", (32, 32), (180, 20, 20))
        db, _ = self._run(image)
        try:
            ColorAnalysis(db, worker_count=1).run()
            row = db.connection.execute(
                "SELECT payload_json FROM analysis_result WHERE module_id = 'color_analysis'"
            ).fetchone()
            payload = json.loads(row["payload_json"])
            self.assertFalse(payload["is_bw"])
            self.assertTrue(payload["is_monochrome"])
        finally:
            db.close()

    def test_existing_result_is_reused(self) -> None:
        image = Image.new("RGB", (16, 16), "white")
        db, _ = self._run(image)
        try:
            first = ColorAnalysis(db, worker_count=1).run()
            second = ColorAnalysis(db, worker_count=1).run()
            self.assertEqual(first.processed, 1)
            self.assertEqual(second.processed, 0)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
