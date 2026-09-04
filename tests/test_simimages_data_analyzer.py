from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_sorter.core.simimages_data_analyzer import SimImagesDataAnalyzer


class SimImagesDataAnalyzerTests(unittest.TestCase):
    def _create_db(self, directory: Path) -> Path:
        path = directory / "Cache.db"
        connection = sqlite3.connect(path)
        try:
            connection.executescript(
                """
                CREATE TABLE d (id INTEGER PRIMARY KEY, drive TEXT);
                CREATE TABLE f (id INTEGER PRIMARY KEY, did INTEGER, folder TEXT, time INTEGER);
                CREATE TABLE m (
                    id INTEGER PRIMARY KEY,
                    fid INTEGER,
                    file TEXT,
                    size INTEGER,
                    time INTEGER,
                    flags INTEGER,
                    data BLOB
                );
                """
            )
            connection.executemany("INSERT INTO m VALUES (?, ?, ?, ?, ?, ?, ?)", [
                (1, 1, "a.jpg", 100, 132928139400000000, 0, b"abc"),
                (2, 1, "b.jpg", 200, 132928139500000000, 0, b"12345"),
                (3, 1, "c.jpg", 300, 132928139600000000, 0, b"12345"),
            ])
            connection.commit()
        finally:
            connection.close()
        return path

    def test_analyzes_blob_lengths_and_time(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            database_path = self._create_db(Path(temporary))
            blob, time_analysis = SimImagesDataAnalyzer().analyze(database_path, sample_size=3)

        self.assertIsNotNone(blob)
        assert blob is not None
        self.assertEqual(blob.sampled, 3)
        self.assertEqual(blob.blob_count, 3)
        self.assertEqual(blob.min_length, 3)
        self.assertEqual(blob.max_length, 5)
        self.assertEqual(blob.common_lengths[0], (5, 2))
        self.assertEqual(len(blob.samples), 3)
        self.assertIsNotNone(time_analysis)
        assert time_analysis is not None
        self.assertEqual(time_analysis.numeric_count, 3)
        self.assertEqual(time_analysis.min_value, 132928139400000000)
        self.assertEqual(time_analysis.max_value, 132928139600000000)
        self.assertTrue(time_analysis.samples[0].converted != "unrecognized")

    def test_read_only_does_not_modify_database(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            database_path = self._create_db(Path(temporary))
            before = database_path.read_bytes()
            SimImagesDataAnalyzer().analyze(database_path, sample_size=2)
            after = database_path.read_bytes()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
