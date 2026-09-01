from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from ai_sorter.tools.duplicate_review_organizer import DuplicateFile, DuplicateReviewOrganizer


class DuplicateReviewOrganizerTests(unittest.TestCase):
    def test_same_volume_move_verifies_source_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.jpg"
            destination = root / "review" / "1" / "source.jpg"
            payload = b"stable-content"
            source.write_bytes(payload)
            digest = hashlib.sha512(payload).hexdigest()

            organizer = DuplicateReviewOrganizer(root / "checksum.adb", root / "review")
            item = DuplicateFile(digest, source, len(payload))
            destination.parent.mkdir(parents=True)
            organizer._move_verified(item, destination)

            self.assertFalse(source.exists())
            self.assertEqual(destination.read_bytes(), payload)

    def test_same_volume_move_refuses_changed_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.jpg"
            destination = root / "review" / "1" / "source.jpg"
            source.write_bytes(b"original")
            digest = hashlib.sha512(b"original").hexdigest()
            source.write_bytes(b"changed")

            organizer = DuplicateReviewOrganizer(root / "checksum.adb", root / "review")
            item = DuplicateFile(digest, source, len(b"original"))
            with self.assertRaises(RuntimeError):
                organizer._move_verified(item, destination)

            self.assertTrue(source.exists())
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
