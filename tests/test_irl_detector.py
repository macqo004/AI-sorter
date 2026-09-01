from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from ai_sorter.core.database import Database
from ai_sorter.modules.irl_detector import IRLDetector
from ai_sorter.modules.scanner import Scanner


class IRLDetectorTests(unittest.TestCase):
    def test_heuristic_runs_and_persists_interpretable_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_path = root / "photo.jpg"
            image = Image.new("RGB", (120, 80), "white")
            for x in range(10, 110):
                for y in range(10, 70):
                    image.putpixel((x, y), ((x * 2) % 255, (y * 3) % 255, (x + y) % 255))
            image.save(image_path, quality=90)

            db = Database(root / "project.db")
            db.open()
            try:
                Scanner(db, worker_count=1).scan(root)
                summary = IRLDetector(db, worker_count=1, scope_root=root).run()
                self.assertEqual(summary.failed, 0)
                self.assertEqual(summary.considered, 1)
                self.assertEqual(summary.processed, 1)
                row = db.connection.execute(
                    "SELECT confidence, payload_json FROM analysis_result WHERE module_id = 'irl_detector'"
                ).fetchone()
                self.assertIsNotNone(row)
                payload = json.loads(row["payload_json"])
                self.assertIn(payload["classification"], {"IRL", "NOT_IRL", "UNCERTAIN"})
                self.assertGreaterEqual(payload["irl_score"], 0.0)
                self.assertLessEqual(payload["irl_score"], 1.0)
            finally:
                db.close()

    def test_scope_is_recursive_and_excludes_other_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            included = root / "included"
            nested = included / "nested"
            excluded = root / "excluded"
            nested.mkdir(parents=True)
            excluded.mkdir()
            Image.new("RGB", (16, 16), "red").save(included / "a.jpg")
            Image.new("RGB", (16, 16), "blue").save(nested / "b.jpg")
            Image.new("RGB", (16, 16), "green").save(excluded / "c.jpg")

            db = Database(root / "project.db")
            db.open()
            try:
                Scanner(db, worker_count=1).scan(root)
                summary = IRLDetector(db, worker_count=1, scope_root=included).run()
                self.assertEqual(summary.considered, 2)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
