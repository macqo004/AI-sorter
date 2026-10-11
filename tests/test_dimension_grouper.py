from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from ai_sorter.core.database import Database
from ai_sorter.modules.dimension_grouper import DimensionGrouper
from ai_sorter.modules.scanner import Scanner


class DimensionGrouperTests(unittest.TestCase):
    def test_groups_images_and_scanner_reuses_database_identity_after_move(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "sample.png"
            Image.new("RGB", (800, 870), (220, 30, 40)).save(source)

            db = Database(root / "project.db")
            db.open()
            try:
                before = Scanner(db, worker_count=1).scan(root)
                self.assertEqual(before.scanned, 1)
                self.assertEqual(before.failed, 0)

                grouper = DimensionGrouper(db, root, batch_size=8)
                plan = grouper.plan()
                self.assertEqual(plan.considered, 1)
                self.assertEqual(plan.planned_moves, 1)
                self.assertEqual(plan.by_dimension, {"800x870": 1})

                summary = grouper.execute(plan)
                destination = root / "800x870" / "sample.png"
                self.assertEqual(summary.moved, 1)
                self.assertEqual(summary.database_updated, 1)
                self.assertTrue(destination.is_file())
                self.assertFalse(source.exists())

                active_rows = db.connection.execute(
                    "SELECT sha512, absolute_path FROM file_location WHERE location_status = 'ACTIVE'"
                ).fetchall()
                self.assertEqual(len(active_rows), 1)
                self.assertEqual(active_rows[0]["absolute_path"], str(destination.resolve()))

                after = Scanner(db, worker_count=1).scan(root)
                self.assertEqual(after.scanned, 0)
                self.assertEqual(after.skipped, 1)
                self.assertEqual(after.failed, 0)

                second_plan = grouper.plan()
                self.assertEqual(second_plan.considered, 0)
                self.assertEqual(second_plan.planned_moves, 0)
            finally:
                db.close()

    def test_existing_destination_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            nested = root / "nested"
            target_dir = root / "800x870"
            nested.mkdir()
            target_dir.mkdir()
            source = nested / "same.png"
            destination = target_dir / "same.png"
            Image.new("RGB", (800, 870), (10, 20, 30)).save(source)
            Image.new("RGB", (800, 870), (200, 210, 220)).save(destination)
            original_destination = destination.read_bytes()

            db = Database(root / "project.db")
            db.open()
            try:
                grouper = DimensionGrouper(db, root, batch_size=8)
                plan = grouper.plan()
                self.assertEqual(plan.planned_moves, 0)
                self.assertEqual(plan.destination_conflicts, 1)

                summary = grouper.execute(plan)
                self.assertEqual(summary.moved, 0)
                self.assertEqual(summary.skipped_existing, 1)
                self.assertTrue(source.is_file())
                self.assertEqual(destination.read_bytes(), original_destination)
            finally:
                db.close()

    def test_unreadable_image_is_left_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "broken.jpg"
            source.write_bytes(b"not an actual image")

            db = Database(root / "project.db")
            db.open()
            try:
                grouper = DimensionGrouper(db, root, batch_size=8)
                plan = grouper.plan()
                self.assertEqual(plan.considered, 1)
                self.assertEqual(plan.unreadable, 1)
                self.assertEqual(plan.planned_moves, 0)

                summary = grouper.execute(plan)
                self.assertEqual(summary.moved, 0)
                self.assertEqual(summary.unreadable, 1)
                self.assertTrue(source.is_file())
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
