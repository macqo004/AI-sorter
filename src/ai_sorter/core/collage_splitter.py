"""Detect and split rectangular image collages without database writes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps


@dataclass(frozen=True, slots=True)
class Rectangle:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


@dataclass(frozen=True, slots=True)
class SplitResult:
    source: Path
    image_width: int
    image_height: int
    rectangles: tuple[Rectangle, ...]
    confidence: float


class CollageSplitter:
    """Conservative image splitter based on strong local color transitions."""

    def __init__(
        self,
        *,
        analysis_size: int = 512,
        min_piece_ratio: float = 0.08,
        edge_threshold: float = 28.0,
        coverage_threshold: float = 0.45,
        smooth_radius: int = 3,
    ) -> None:
        self.analysis_size = max(64, min(1024, int(analysis_size)))
        self.min_piece_ratio = max(0.01, min(0.40, float(min_piece_ratio)))
        self.edge_threshold = max(5.0, min(120.0, float(edge_threshold)))
        self.coverage_threshold = max(0.20, min(0.90, float(coverage_threshold)))
        self.smooth_radius = max(1, min(12, int(smooth_radius)))

    def detect(self, path: Path) -> SplitResult:
        source = Path(path).resolve()
        if not source.is_file():
            raise ValueError(f"Plik nie istnieje: {source}")
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            width, height = image.size
            scaled = _resize_for_analysis(image, self.analysis_size)
            rectangles, confidence = self._detect_recursive(scaled, width, height)
        return SplitResult(source, width, height, tuple(rectangles), confidence)

    def split(self, result: SplitResult, *, apply: bool = False) -> tuple[Path, ...]:
        if len(result.rectangles) < 2:
            return ()
        if not apply:
            return tuple(
                result.source.parent / f"{result.source.stem}_{index:02d}{result.source.suffix}"
                for index in range(1, len(result.rectangles) + 1)
            )
        with Image.open(result.source) as image:
            image = ImageOps.exif_transpose(image)
            paths: list[Path] = []
            for index, rect in enumerate(result.rectangles, start=1):
                destination = result.source.parent / f"{result.source.stem}_{index:02d}{result.source.suffix}"
                destination = _unique_output_path(destination)
                crop = image.crop((rect.left, rect.top, rect.right, rect.bottom))
                crop.save(destination)
                paths.append(destination)
            return tuple(paths)

    def _detect_recursive(self, image: Image.Image, original_width: int, original_height: int) -> tuple[list[Rectangle], float]:
        scale_x = original_width / image.width
        scale_y = original_height / image.height
        pending = [Rectangle(0, 0, image.width, image.height)]
        leaves: list[Rectangle] = []
        scores: list[float] = []
        while pending:
            rect = pending.pop()
            crop = image.crop((rect.left, rect.top, rect.right, rect.bottom))
            split = _best_split(crop, self.edge_threshold, self.coverage_threshold, self.smooth_radius)
            if split is None or min(split.score, 1.0) < 0.20:
                leaves.append(rect)
                scores.append(split.score if split else 0.0)
                continue
            orientation, position, score = split.orientation, split.position, split.score
            if orientation == "vertical":
                left = Rectangle(rect.left, rect.top, rect.left + position, rect.bottom)
                right = Rectangle(rect.left + position, rect.top, rect.right, rect.bottom)
            else:
                left = Rectangle(rect.left, rect.top, rect.right, rect.top + position)
                right = Rectangle(rect.left, rect.top + position, rect.right, rect.bottom)
            if min(left.width / image.width, left.height / image.height, right.width / image.width, right.height / image.height) < self.min_piece_ratio:
                leaves.append(rect)
                scores.append(score)
                continue
            pending.extend((right, left))
        rectangles = [
            Rectangle(
                round(rect.left * scale_x), round(rect.top * scale_y),
                round(rect.right * scale_x), round(rect.bottom * scale_y),
            )
            for rect in leaves
            if rect.width > 1 and rect.height > 1
        ]
        rectangles.sort(key=lambda r: (r.top, r.left))
        confidence = sum(scores) / len(scores) if scores else 0.0
        return rectangles, max(0.0, min(1.0, confidence))


@dataclass(frozen=True, slots=True)
class _Split:
    orientation: str
    position: int
    score: float


def _resize_for_analysis(image: Image.Image, limit: int) -> Image.Image:
    scale = min(1.0, limit / max(image.width, image.height))
    if scale == 1.0:
        return image
    return image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.BILINEAR)


def _best_split(image: Image.Image, threshold: float, coverage: float, smooth_radius: int) -> _Split | None:
    rgb = image.convert("RGB")
    width, height = rgb.size
    if width < 16 and height < 16:
        return None
    gray = rgb.convert("L")
    vertical_scores = _axis_scores(gray, horizontal=False, radius=smooth_radius)
    horizontal_scores = _axis_scores(gray, horizontal=True, radius=smooth_radius)
    best_v = _candidate(vertical_scores, threshold, coverage, smooth_radius)
    best_h = _candidate(horizontal_scores, threshold, coverage, smooth_radius)
    candidates = [candidate for candidate in (best_v, best_h) if candidate is not None]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.score)


def _axis_scores(gray: Image.Image, *, horizontal: bool, radius: int) -> list[float]:
    pixels = gray.load()
    width, height = gray.size
    scores: list[float] = []
    if horizontal:
        for y in range(radius, height - radius):
            changes = [abs(pixels[x, y] - pixels[x, y - 1]) for x in range(width)]
            strong = sum(1 for value in changes if value >= 20)
            score = (sum(changes) / max(1, len(changes))) * (strong / max(1, len(changes)))
            scores.append(score)
    else:
        for x in range(radius, width - radius):
            changes = [abs(pixels[x, y] - pixels[x - 1, y]) for y in range(height)]
            strong = sum(1 for value in changes if value >= 20)
            score = (sum(changes) / max(1, len(changes))) * (strong / max(1, len(changes)))
            scores.append(score)
    return scores


def _candidate(scores: list[float], threshold: float, coverage: float, radius: int) -> _Split | None:
    if len(scores) < 8:
        return None
    ranked = sorted(enumerate(scores, start=radius), key=lambda pair: pair[1], reverse=True)
    position, raw = ranked[0]
    if raw < threshold * coverage:
        return None
    start = max(0, position - radius)
    end = min(len(scores), position + radius + 1)
    window = scores[start:end]
    mean = sum(window) / len(window)
    score = min(1.0, max(0.0, mean / max(1.0, threshold * 2.0)))
    return _Split("horizontal" if len(scores) >= 0 and False else "vertical", position, score)


def _unique_output_path(path: Path) -> Path:
    if not path.exists():
        return path
    index = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{index:02d}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1
