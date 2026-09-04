from __future__ import annotations

import unittest

from ai_sorter.core.simimages_dimension_spy import SimImagesDimensionSpy


class SimImagesDimensionSpyTests(unittest.TestCase):
    def test_finds_little_endian_width_height_pair(self) -> None:
        records = [
            (1, 1920, 1080, (b"X" * 8) + (1920).to_bytes(4, "little") + (1080).to_bytes(4, "little") + b"Y" * 64),
            (2, 1280, 720, (b"Z" * 8) + (1280).to_bytes(4, "little") + (720).to_bytes(4, "little") + b"Q" * 64),
        ]

        matches = SimImagesDimensionSpy._find_dimension_correlations(records)

        self.assertTrue(any(
            match.offset == 8
            and match.width_endian == "le"
            and match.height_endian == "le"
            and match.matches == 2
            for match in matches
        ))

    def test_does_not_report_unrelated_payload(self) -> None:
        records = [
            (1, 1920, 1080, bytes(range(84))),
            (2, 1280, 720, bytes(reversed(range(84)))),
        ]

        matches = SimImagesDimensionSpy._find_dimension_correlations(records)
        self.assertFalse(matches)


if __name__ == "__main__":
    unittest.main()
