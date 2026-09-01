from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from ai_sorter.core.database import Database
from ai_sorter.modules.image_dimensions import ImageDimensions
from ai_sorter.modules.scanner import Scanner


class ImageDimensionsTests(unittest.TestCase):
    def test_reads_dimensions_once_and_persists_for_shared_sha(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "first.png"
            second = root / "nested" / "second.png"
            second.parent.mkdir()
            image = Image.new("RGB", (640, 480), "red")
            image.save(first)
            image.save(second)

            db = Database(root / "project.db")
            db.open()
            try:
                Scanner(db, worker_count=1).scan(root)
                summary = ImageDimensions(db, worker_count=1).run()
                self.assertEqual(summary.considered, 1)
                self.assertEqual(summary.processed, 1)
                self.assertEqual(summary.updated, 1)
                self.assertEqual(summary.failed, 0)

                row = db.connection.execute(
                    "SELECT width_px, height_px FROM file_record"
                ).fetchone()
                self.assertEqual((row["width_px"], row["height_px"]), (640, 480))

                second_run = ImageDimensions(db, worker_count=1).run()
                self.assertEqual(second_run.considered, 0)
                self.assertEqual(second_run.processed, 0)
            finally:
                db.close()

    def test_bad_active_location_uses_another_active_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            good = root / "good.png"
            image = Image.new("RGB", (320, 200), "blue")
            image.save(good)

            db = Database(root / "project.db")
            db.open()
            try:
                Scanner(db, worker_count=1).scan(root)
                sha = db.connection.execute("SELECT sha512 FROM file_record").fetchone()[0]
                missing = root / "missing.png"
                db.upsert_file_location(__import__("ai_sorter.core.models", fromlist=["FileLocationRecord"]).FileLocationRecord(
                    sha512=sha,
                    absolute_path=str(missing),
                    file_size=good.stat().st_size,
                    location_status="ACTIVE",
                ))
                summary = ImageDimensions(db, worker_count=1).run()
                self.assertEqual(summary.failed, 0)
                row = db.connection.execute(
                    "SELECT width_px, height_px FROM file_record WHERE sha512 = ?", (sha,)
                ).fetchone()
                self.assertEqual((row["width_px"], row["height_px"]), (320, 200))
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
