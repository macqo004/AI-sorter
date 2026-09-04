from __future__ import annotations

import unittest

from ai_sorter.core.simimages_dimension_spy import SimImagesDimensionSpy


class SimImagesDimensionSpyTests(unittest.TestCase):
    def test_finds_little_endian_width_height_scalars(self) -> None:
        records = [
            (1, 1920, 1080, b"X" * 8 + (1920).to_bytes(4, "little") + (1080).to_bytes(4, "little") + b"Y" * 64, 1000),
            (2, 1280, 720, b"Z" * 8 + (1280).to_bytes(4, "little") + (720).to_bytes(4, "little") + b"Q" * 64, 2000),
            (3, 800, 600, b"A" * 8 + (800).to_bytes(4, "little") + (600).to_bytes(4, "little") + b"B" * 64, 3000),
        ]
        matches = SimImagesDimensionSpy._find_scalar_hits(records)
        self.assertIn("width = uint32_le at offset 8", matches)
        self.assertIn("height = uint32_le at offset 12", matches)

    def test_byte_stats_cover_all_payload_offsets(self) -> None:
        records = [
            (1, 1920, 1080, bytes(range(84)), 1000),
            (2, 1280, 720, bytes(reversed(range(84))), 2000),
            (3, 800, 600, bytes((x * 3) % 256 for x in range(84)), 3000),
        ]
        stats = SimImagesDimensionSpy._build_byte_stats(records)
        self.assertEqual(len(stats), 84)
        self.assertEqual(stats[0].offset, 0)
        self.assertEqual(stats[-1].offset, 83)

    def test_no_exact_scalar_hit_for_unrelated_payload(self) -> None:
        records = [
            (1, 1920, 1080, bytes(range(84)), 1000),
            (2, 1280, 720, bytes(reversed(range(84))), 2000),
            (3, 800, 600, bytes([17] * 84), 3000),
        ]
        self.assertFalse(SimImagesDimensionSpy._find_scalar_hits(records))


if __name__ == "__main__":
    unittest.main()
