from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_sorter.core.simimages_inspector import SimImagesDatabaseInspector


class SimImagesInspectorTests(unittest.TestCase):
    def test_inspects_schema_and_detects_dimension_checksum_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "Cache.db"
            connection = sqlite3.connect(database)
            try:
                connection.executescript(
                    """
                    CREATE TABLE images (
                        id INTEGER PRIMARY KEY,
                        full_path TEXT NOT NULL,
                        filename TEXT,
                        file_size INTEGER,
                        crc32 TEXT,
                        width INTEGER,
                        height INTEGER
                    );
                    CREATE INDEX idx_images_crc32 ON images(crc32);
                    INSERT INTO images(full_path, filename, file_size, crc32, width, height)
                    VALUES ('C:/images/a.jpg', 'a.jpg', 1234, 'A1B2C3D4', 1920, 1080);
                    """
                )
                connection.commit()
            finally:
                connection.close()

            inspection = SimImagesDatabaseInspector().inspect(database)

            self.assertEqual(len(inspection.tables), 1)
            self.assertEqual(inspection.tables[0].name, "images")
            self.assertIn(("images", "full_path", "strong"), inspection.path_candidates)
            self.assertIn(("images", "crc32", "strong"), inspection.checksum_candidates)
            self.assertIn(("images", "width", "strong"), inspection.width_candidates)
            self.assertIn(("images", "height", "strong"), inspection.height_candidates)
            self.assertEqual(len(inspection.sample_rows), 1)

    def test_inspection_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "Cache.db"
            connection = sqlite3.connect(database)
            try:
                connection.execute("CREATE TABLE images (id INTEGER PRIMARY KEY, width INTEGER)")
                connection.execute("INSERT INTO images(width) VALUES (100)")
                connection.commit()
            finally:
                connection.close()

            before = database.read_bytes()
            SimImagesDatabaseInspector().inspect(database, count_rows=True)
            after = database.read_bytes()
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
