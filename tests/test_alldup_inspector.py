"""Tests for the read-only AllDup database inspector."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_sorter.core.alldup_inspector import AllDupDatabaseInspector


class AllDupInspectorTests(unittest.TestCase):
    def test_inspector_reads_schema_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "checksum.adb"
            connection = sqlite3.connect(path)
            try:
                connection.execute("CREATE TABLE files (sha512 TEXT, file_path TEXT, file_size INTEGER)")
                connection.execute("CREATE INDEX idx_files_sha512 ON files(sha512)")
                connection.execute(
                    "INSERT INTO files (sha512, file_path, file_size) VALUES (?, ?, ?)",
                    ("a" * 128, r"C:\test\image.jpg", 1234),
                )
                connection.commit()
            finally:
                connection.close()

            before = path.stat().st_mtime_ns
            inspection = AllDupDatabaseInspector().inspect(path)
            after = path.stat().st_mtime_ns

            self.assertEqual(before, after)
            self.assertEqual(len(inspection.tables), 1)
            self.assertEqual(inspection.tables[0].name, "files")
            self.assertIn(("files", "sha512", "strong"), inspection.hash_candidates)
            self.assertIn(("files", "file_path", "strong"), inspection.path_candidates)
            self.assertIn(("files", "file_size", "strong"), inspection.size_candidates)
            self.assertIsNone(inspection.tables[0].row_count)


if __name__ == "__main__":
    unittest.main()
