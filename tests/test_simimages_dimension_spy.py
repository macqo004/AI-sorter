from __future__ import annotations

import unittest

from ai_sorter.core.simimages_dimension_spy import SimImagesDimensionSpy


class SimImagesDimensionSpyTests(unittest.TestCase):
    def test_finds_little_endian_width_height_pair(self) -> None:
        records = [
            (1, 1920, 1080, 1000, (b"X" * 8) + (1920).to_bytes(4, "little") + (1080).to_bytes(4, "little") + b"Y" * 64),
            (2, 1280, 720, 2000, (b"Z" * 8) + (1280).to_bytes(4, "little") + (720).to_bytes(4, "little") + b"Q" * 64),
            (3, 800, 600, 3000, (b"A" * 8) + (800).to_bytes(4, "little") + (600).to_bytes(4, "little") + b"B" * 64),
            (4, 640, 480, 4000, (b"C" * 8) + (640).to_bytes(4, "little") + (480).to_bytes(4, "little") + b"D" * 64),
        ]

        matches = SimImagesDimensionSpy._find_scalar_correlations(records)

        self.assertTrue(any(
            match.offset == 8
            and match.field == "width"
            and match.encoding == "u32le"
            and match.matches == 4
            for match in matches
        ))
        self.assertTrue(any(
            match.offset == 12
            and match.field == "height"
            and match.encoding == "u32le"
            and match.matches == 4
            for match in matches
        ))

    def test_finds_byte_level_dimension_correlation(self) -> None:
        records = []
        for row_id, width, height in [(1, 100, 200), (2, 200, 300), (3, 300, 400), (4, 400, 500), (5, 500, 600)]:
            blob = bytearray(84)
            blob[7] = width
            blob[21] = height
            records.append((row_id, width, height, 1000 + row_id, bytes(blob)))

        correlations = SimImagesDimensionSpy._find_byte_correlations(records)

        self.assertTrue(any(item.offset == 7 and item.field == "width" and item.correlation > 0.99 for item in correlations))
        self.assertTrue(any(item.offset == 21 and item.field == "height" and item.correlation > 0.99 for item in correlations))

    def test_does_not_report_unrelated_payload(self) -> None:
        records = [
            (1, 1920, 1080, 1000, bytes(range(84))),
            (2, 1280, 720, 2000, bytes(reversed(range(84)))),
            (3, 800, 600, 3000, bytes([17] * 84)),
            (4, 640, 480, 4000, bytes([231] * 84)),
            (5, 500, 400, 5000, bytes([99] * 84)),
        ]

        scalar_matches = SimImagesDimensionSpy._find_scalar_correlations(records)
        byte_correlations = SimImagesDimensionSpy._find_byte_correlations(records)
        self.assertFalse(scalar_matches)
        self.assertFalse(byte_correlations)


if __name__ == "__main__":
    unittest.main()
