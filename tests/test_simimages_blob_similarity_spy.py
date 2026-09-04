from __future__ import annotations

import unittest

from ai_sorter.core.simimages_blob_similarity_spy import (
    BlobSimilarityPair,
    _blob_distance,
    _pair_key,
    _pearson,
    _spearman,
    _visual_distance,
)


class SimImagesBlobSimilaritySpyTests(unittest.TestCase):
    def test_identical_blobs_have_zero_distance(self) -> None:
        payload = bytes(range(84))
        self.assertEqual(_blob_distance(payload, payload), 0.0)

    def test_blob_distance_is_normalized(self) -> None:
        left = bytes([0] * 84)
        right = bytes([255] * 84)
        self.assertEqual(_blob_distance(left, right), 1.0)

    def test_visual_distance_is_zero_for_identical_fingerprint(self) -> None:
        fingerprint = [0.1, 0.2, 0.3]
        self.assertEqual(_visual_distance(fingerprint, fingerprint), 0.0)

    def test_spearman_detects_same_order(self) -> None:
        values = [1.0, 2.0, 3.0, 4.0]
        self.assertAlmostEqual(_spearman(values, values), 1.0)

    def test_spearman_detects_reverse_order(self) -> None:
        self.assertAlmostEqual(_spearman([1.0, 2.0, 3.0, 4.0], [4.0, 3.0, 2.0, 1.0]), -1.0)

    def test_pearson_requires_variation(self) -> None:
        self.assertIsNone(_pearson([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]))

    def test_pair_key_is_order_independent(self) -> None:
        first = BlobSimilarityPair(20, 10, 0.2, 0.3)
        second = BlobSimilarityPair(10, 20, 0.2, 0.3)
        self.assertEqual(_pair_key(first), _pair_key(second))


if __name__ == "__main__":
    unittest.main()
