from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from ai_sorter.core.database import Database
from ai_sorter.core.models import FileLocationRecord, FileRecord
from ai_sorter.image_extension_fixer import ImageExtensionFixer


class ExtensionCollisionTests(unittest.TestCase):
    def test_existing_destination_is_skipped_without_blocking_other_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = Database(root / "project.db")
            db.open()
            try:
                blocked = root / "blocked.jpeg"
                existing = root / "blocked.jpg"
                safe = root / "safe.jpeg"
                blocked.write_bytes(b"\xff\xd8\xffblocked")
                existing.write_bytes(b"existing destination")
                safe.write_bytes(b"\xff\xd8\xffsafe")

                for source in (blocked, safe):
                    content = source.read_bytes()
                    sha512 = hashlib.sha512(content).hexdigest()
                    db.upsert_file(FileRecord(sha512=sha512, size_bytes=len(content)))
                    db.upsert_file_location(FileLocationRecord(
                        sha512=sha512, absolute_path=str(source.resolve()), file_size=len(content)
                    ))
                    db.record_module_result(
                        sha512, "image_format_check", "image_format_check:.jpeg",
                        {"extension": ".jpeg", "detected_format": "JPEG",
                         "canonical_extension": ".jpg", "matches": True}, confidence=1.0
                    )

                proposals = ImageExtensionFixer(db, root).plan()

                self.assertEqual(len(proposals), 1)
                self.assertEqual(proposals[0].source, safe.resolve())
                self.assertEqual(proposals[0].destination, (root / "safe.jpg").resolve())
                self.assertEqual(existing.read_bytes(), b"existing destination")
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
