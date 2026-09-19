from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from ai_sorter.core.database import Database
from ai_sorter.core.models import FileLocationRecord, FileRecord
from ai_sorter.modules.image_format_check import ImageFormatCheck


class ImageFormatCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.db = Database(self.root / "project.db")
        self.db.open()

    def tearDown(self) -> None:
        self.db.close()
        self.temp_dir.cleanup()

    def _register_file(self, path: Path, content: bytes) -> str:
        path.write_bytes(content)
        sha512 = hashlib.sha512(content).hexdigest()
        self.db.upsert_file(FileRecord(sha512=sha512, size_bytes=len(content)))
        self.db.upsert_file_location(
            FileLocationRecord(
                sha512=sha512,
                absolute_path=str(path.resolve()),
                file_size=len(content),
            )
        )
        return sha512

    def test_second_run_skips_existing_result(self) -> None:
        self._register_file(self.root / "one.jpg", b"\xff\xd8\xff" + b"x" * 29)
        self._register_file(self.root / "two.png", b"\x89PNG\r\n\x1a\n" + b"x" * 24)

        first = ImageFormatCheck(self.db, root=self.root).run()
        self.assertEqual(first.processed, 2)
        self.assertEqual(first.skipped, 0)

        second = ImageFormatCheck(self.db, root=self.root).run()
        self.assertEqual(second.processed, 0)
        self.assertEqual(second.skipped, 2)
        self.assertEqual(second.matches, 0)
        self.assertEqual(second.mismatches, 0)

    def test_error_details_are_reported_and_failed_file_is_retried(self) -> None:
        path = self.root / "missing.jpg"
        self._register_file(path, b"\\xff\\xd8\\xff" + b"x" * 29)
        path.unlink()

        first = ImageFormatCheck(self.db, root=self.root, worker_count=1).run()
        self.assertEqual(first.processed, 1)
        self.assertEqual(first.failed, 1)
        self.assertEqual(len(first.errors), 1)
        self.assertIn(str(path.resolve()), first.errors[0])
        self.assertIn("FileNotFoundError:", first.errors[0])

        second = ImageFormatCheck(self.db, root=self.root, worker_count=1).run()
        self.assertEqual(second.processed, 1)
        self.assertEqual(second.skipped, 0)
        self.assertEqual(second.failed, 1)
        self.assertEqual(second.errors, first.errors)


    def test_same_sha_with_new_extension_is_checked_again(self) -> None:
        content = b"\xff\xd8\xff" + b"x" * 29
        sha512 = self._register_file(self.root / "one.jpg", content)

        first = ImageFormatCheck(self.db, root=self.root).run()
        self.assertEqual(first.processed, 1)

        old_path = self.root / "one.jpg"
        new_path = self.root / "one.jpeg"
        old_path.rename(new_path)
        with self.db.transaction() as connection:
            connection.execute(
                "UPDATE file_location SET absolute_path = ? WHERE sha512 = ? AND absolute_path = ?",
                (str(new_path.resolve()), sha512, str(old_path.resolve())),
            )

        second = ImageFormatCheck(self.db, root=self.root).run()
        self.assertEqual(second.processed, 1)
        self.assertEqual(second.skipped, 0)
        self.assertEqual(second.matches, 1)


if __name__ == "__main__":
    unittest.main()
