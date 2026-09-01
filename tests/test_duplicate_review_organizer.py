from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from ai_sorter.tools.duplicate_review_organizer import DuplicateFile, DuplicateReviewOrganizer


class DuplicateReviewOrganizerTests(unittest.TestCase):
    def test_same_volume_move_verifies_source_and_destination_before_delete(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.jpg"
            destination = root / "review" / "1" / "source.jpg"
            payload = b"stable-content"
            source.write_bytes(payload)
            digest = hashlib.sha512(payload).hexdigest()

            organizer = DuplicateReviewOrganizer(root / "checksum.adb", root / "review")
            item = DuplicateFile(digest, source, len(payload))
            organizer._move_verified(item, destination)

            self.assertFalse(source.exists())
            self.assertEqual(destination.read_bytes(), payload)

    def test_same_volume_move_refuses_changed_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.jpg"
            destination = root / "review" / "1" / "source.jpg"
            original = b"original"
            source.write_bytes(original)
            digest = hashlib.sha512(original).hexdigest()
            source.write_bytes(b"changed")

            organizer = DuplicateReviewOrganizer(root / "checksum.adb", root / "review")
            item = DuplicateFile(digest, source, len(original))
            with self.assertRaises(RuntimeError):
                organizer._move_verified(item, destination)

            self.assertTrue(source.exists())
            self.assertFalse(destination.exists())

    def test_destination_collision_is_resolved_without_parenthetical_suffix(self) -> None:
        organizer = DuplicateReviewOrganizer(Path("checksum.adb"), Path("review"))
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "foo.jpg").write_bytes(b"x")
            planned = {"foo.jpg"}
            target = organizer._unique_target(directory, "foo.jpg", planned)
            self.assertEqual(target.name, "foo_1.jpg")
            self.assertNotIn("(", target.name)


if __name__ == "__main__":
    unittest.main()
