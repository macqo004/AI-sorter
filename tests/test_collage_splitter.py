from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from ai_sorter.core.collage_splitter import CollageSplitter, Rectangle, _best_split


class CollageSplitterTests(unittest.TestCase):
    def test_detects_vertical_touching_panels(self) -> None:
        image = Image.new("RGB", (200, 100))
        for x in range(200):
            value = (30, 30, 30) if x < 100 else (220, 220, 220)
            for y in range(100):
                image.putpixel((x, y), value)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "collage.png"
            image.save(path)
            result = CollageSplitter().detect(path)
        self.assertEqual(len(result.rectangles), 2)
        self.assertEqual(result.rectangles[0], Rectangle(0, 0, 100, 100))
        self.assertEqual(result.rectangles[1], Rectangle(100, 0, 200, 100))

    def test_detects_horizontal_touching_panels(self) -> None:
        image = Image.new("RGB", (100, 200))
        for y in range(200):
            value = (20, 80, 180) if y < 100 else (220, 160, 30)
            for x in range(100):
                image.putpixel((x, y), value)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "collage.png"
            image.save(path)
            result = CollageSplitter().detect(path)
        self.assertEqual(len(result.rectangles), 2)
        self.assertEqual(result.rectangles[0], Rectangle(0, 0, 100, 100))
        self.assertEqual(result.rectangles[1], Rectangle(0, 100, 100, 200))

    def test_best_split_preserves_orientation(self) -> None:
        image = Image.new("L", (120, 80), 20)
        for x in range(60, 120):
            for y in range(80):
                image.putpixel((x, y), 230)
        split = _best_split(image, 22.0, 0.40, 3)
        self.assertIsNotNone(split)
        assert split is not None
        self.assertEqual(split.orientation, "vertical")
        self.assertAlmostEqual(split.position, 60, delta=3)

    def test_no_split_for_uniform_image(self) -> None:
        image = Image.new("RGB", (200, 100), (120, 120, 120))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "single.png"
            image.save(path)
            result = CollageSplitter().detect(path)
        self.assertEqual(len(result.rectangles), 1)
        self.assertEqual(result.rectangles[0], Rectangle(0, 0, 200, 100))

    def test_apply_writes_next_to_source(self) -> None:
        image = Image.new("RGB", (120, 60))
        for x in range(120):
            value = (0, 0, 0) if x < 60 else (255, 255, 255)
            for y in range(60):
                image.putpixel((x, y), value)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.png"
            image.save(path)
            splitter = CollageSplitter()
            result = splitter.detect(path)
            outputs = splitter.split(result, apply=True)
            self.assertEqual([item.name for item in outputs], ["source_01.png", "source_02.png"])
            self.assertTrue(all(item.parent == path.parent for item in outputs))
            with Image.open(outputs[0]) as left, Image.open(outputs[1]) as right:
                self.assertEqual(left.size, (60, 60))
                self.assertEqual(right.size, (60, 60))


if __name__ == "__main__":
    unittest.main()
