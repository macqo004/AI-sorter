from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from ai_sorter.core.database import Database
from ai_sorter.core.models import FileLocationRecord, FileRecord
from ai_sorter.image_extension_fixer import ImageExtensionFixer


class ImageExtensionFixerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.db = Database(self.root / "project.db")
        self.db.open()

    def tearDown(self) -> None:
        self.db.close()
        self.temp_dir.cleanup()

    def _register_result(self, path: Path, content: bytes, payload: dict) -> str:
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
        self.db.record_module_result(
            sha512,
            "image_format_check",
            f"image_format_check:{path.suffix.lower()}",
            payload,
            confidence=1.0,
        )
        return sha512

    def test_plan_uses_canonical_extension_from_format_check(self) -> None:
        content = b"\x89PNG\r\n\x1a\n" + b"payload"
        source = self.root / "picture.jpg"
        sha512 = self._register_result(
            source,
            content,
            {
                "extension": ".jpg",
                "detected_format": "PNG",
                "canonical_extension": ".png",
                "matches": False,
            },
        )

        proposals = ImageExtensionFixer(self.db, self.root).plan()

        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].source, source.resolve())
        self.assertEqual(proposals[0].destination, (self.root / "picture.png").resolve())
        self.assertEqual(proposals[0].sha512, sha512)

    def test_execute_changes_only_extension_and_preserves_content(self) -> None:
        content = b"\x89PNG\r\n\x1a\n" + b"payload"
        source = self.root / "picture.jpg"
        sha512 = self._register_result(
            source,
            content,
            {
                "extension": ".jpg",
                "detected_format": "PNG",
                "canonical_extension": ".png",
                "matches": False,
            },
        )

        fixer = ImageExtensionFixer(self.db, self.root)
        proposals = fixer.plan()
        changed = fixer.execute(proposals)

        destination = self.root / "picture.png"
        self.assertEqual(changed, 1)
        self.assertFalse(source.exists())
        self.assertTrue(destination.is_file())
        self.assertEqual(destination.read_bytes(), content)
        self.assertEqual(hashlib.sha512(destination.read_bytes()).hexdigest(), sha512)

        row = self.db.connection.execute(
            "SELECT sha512, absolute_path FROM file_location WHERE sha512 = ?", (sha512,)
        ).fetchone()
        self.assertEqual(row["sha512"], sha512)
        self.assertEqual(row["absolute_path"], str(destination.resolve()))

    def test_existing_destination_refuses_entire_plan_without_overwrite(self) -> None:
        source_content = b"\x89PNG\r\n\x1a\nsource"
        destination_content = b"do not overwrite"
        source = self.root / "picture.jpg"
        destination = self.root / "picture.png"
        self._register_result(
            source,
            source_content,
            {
                "extension": ".jpg",
                "detected_format": "PNG",
                "canonical_extension": ".png",
                "matches": False,
            },
        )
        destination.write_bytes(destination_content)

        fixer = ImageExtensionFixer(self.db, self.root)
        with self.assertRaises(FileExistsError):
            fixer.plan()

        self.assertTrue(source.exists())
        self.assertEqual(source.read_bytes(), source_content)
        self.assertTrue(destination.exists())
        self.assertEqual(destination.read_bytes(), destination_content)

    def test_matching_result_is_not_changed(self) -> None:
        content = b"\xff\xd8\xff" + b"payload"
        source = self.root / "picture.jpg"
        self._register_result(
            source,
            content,
            {
                "extension": ".jpg",
                "detected_format": "JPEG",
                "canonical_extension": ".jpg",
                "matches": True,
            },
        )

        self.assertEqual(ImageExtensionFixer(self.db, self.root).plan(), [])


if __name__ == "__main__":
    unittest.main()
