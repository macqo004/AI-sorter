from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ai_sorter.core.database import Database
from ai_sorter.core.models import FileLocationRecord, FileRecord, ModuleRecord


VALID_SHA = "a" * 128


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "project.db")
        self.db.open()

    def tearDown(self) -> None:
        self.db.close()
        self.temp_dir.cleanup()

    def test_schema_bootstraps_to_current_version(self) -> None:
        status = self.db.status()
        self.assertTrue(status.connected)
        self.assertEqual(status.schema_version, 3)

    def test_same_sha512_is_one_file_with_multiple_locations(self) -> None:
        modified = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        self.db.upsert_file(
            FileRecord(
                sha512=VALID_SHA,
                size_bytes=123,
                modified_at=modified,
                width_px=1920,
                height_px=1080,
            )
        )
        self.db.upsert_file_location(
            FileLocationRecord(
                sha512=VALID_SHA,
                absolute_path=r"D:\images\one.png",
                file_size=123,
                modified_at=modified,
            )
        )
        self.db.upsert_file_location(
            FileLocationRecord(
                sha512=VALID_SHA,
                absolute_path=r"E:\archive\one.png",
                file_size=123,
                modified_at=modified,
            )
        )

        status = self.db.status()
        self.assertEqual(status.file_count, 1)
        self.assertEqual(status.location_count, 2)
        row = self.db.connection.execute(
            "SELECT width_px, height_px FROM file_record WHERE sha512 = ?", (VALID_SHA,)
        ).fetchone()
        self.assertEqual((row["width_px"], row["height_px"]), (1920, 1080))

    def test_module_registration_and_execution(self) -> None:
        self.db.register_module(
            ModuleRecord(
                module_id="scanner",
                display_name="Scanner",
                module_version="0.1.0",
            )
        )
        execution_id = self.db.start_module_execution(
            "scanner", datetime.now(timezone.utc)
        )
        self.assertGreater(execution_id, 0)
        self.assertEqual(self.db.status().module_count, 1)
        self.assertEqual(self.db.status().execution_count, 1)


if __name__ == "__main__":
    unittest.main()
