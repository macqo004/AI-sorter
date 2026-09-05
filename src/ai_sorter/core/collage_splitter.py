"""Detect and split rectangular image collages without database writes.

V2 deliberately does not assume that a boundary runs through the whole image.
For every currently analysed rectangle it looks for locally coherent seams and
recursively reconstructs the rectangular panels from those seams.
"""

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


@dataclass(frozen=True, slots=True)
class _Split:
    orientation: str
    position: int
    score: float


class CollageSplitter:
    """Split touching rectangular collage panels using local seam evidence."""

    def __init__(
        self,
        *,
        analysis_size: int = 768,
        min_piece_ratio: float = 0.05,
        edge_threshold: float = 18.0,
        coverage_threshold: float = 0.25,
        smooth_radius: int = 2,
    ) -> None:
        self.analysis_size = max(128, min(1536, int(analysis_size)))
        self.min_piece_ratio = max(0.01, min(0.40, float(min_piece_ratio)))
        self.edge_threshold = max(5.0, min(100.0, float(edge_threshold)))
        self.coverage_threshold = max(0.10, min(0.90, float(coverage_threshold)))
        self.smooth_radius = max(1, min(8, int(smooth_radius)))

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
        outputs = tuple(
            result.source.parent / f"{result.source.stem}_{index:02d}{result.source.suffix}"
            for index in range(1, len(result.rectangles) + 1)
        )
        if not apply:
            return outputs
        with Image.open(result.source) as image:
            image = ImageOps.exif_transpose(image)
            created: list[Path] = []
            for index, rect in enumerate(result.rectangles, start=1):
                destination = _unique_output_path(outputs[index - 1])
                crop = image.crop((rect.left, rect.top, rect.right, rect.bottom))
                crop.save(destination)
                created.append(destination)
            return tuple(created)

    def _detect_recursive(
        self,
        image: Image.Image,
        original_width: int,
        original_height: int,
    ) -> tuple[list[Rectangle], float]:
        scale_x = original_width / image.width
        scale_y = original_height / image.height
        pending = [Rectangle(0, 0, image.width, image.height)]
        leaves: list[Rectangle] = []
        split_scores: list[float] = []

        while pending:
            rect = pending.pop()
            crop = image.crop((rect.left, rect.top, rect.right, rect.bottom))
            split = _best_split(
                crop,
                self.edge_threshold,
                self.coverage_threshold,
                self.smooth_radius,
            )
            if split is None or split.score < 0.30:
                leaves.append(rect)
                continue

            if split.orientation == "vertical":
                first = Rectangle(rect.left, rect.top, rect.left + split.position, rect.bottom)
                second = Rectangle(rect.left + split.position, rect.top, rect.right, rect.bottom)
            else:
                first = Rectangle(rect.left, rect.top, rect.right, rect.top + split.position)
                second = Rectangle(rect.left, rect.top + split.position, rect.right, rect.bottom)

            if _too_small(first, image, self.min_piece_ratio) or _too_small(second, image, self.min_piece_ratio):
                leaves.append(rect)
                continue

            pending.extend((second, first))
            split_scores.append(split.score)

        if len(leaves) < 2:
            return [Rectangle(0, 0, original_width, original_height)], 0.0

        rectangles = [
            Rectangle(
                round(rect.left * scale_x),
                round(rect.top * scale_y),
                round(rect.right * scale_x),
                round(rect.bottom * scale_y),
            )
            for rect in leaves
            if rect.width > 1 and rect.height > 1
        ]
        rectangles.sort(key=lambda item: (item.top, item.left))
        confidence = sum(split_scores) / len(split_scores) if split_scores else 0.0
        return rectangles, max(0.0, min(1.0, confidence))


def _resize_for_analysis(image: Image.Image, limit: int) -> Image.Image:
    scale = min(1.0, limit / max(image.width, image.height))
    if scale == 1.0:
        return image.copy()
    return image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.BILINEAR,
    )


def _best_split(
    image: Image.Image,
    threshold: float,
    coverage_threshold: float,
    radius: int,
) -> _Split | None:
    width, height = image.size
    if width < 32 and height < 32:
        return None

    gray = image.convert("L")
    candidates = []
    candidates.extend(
        _boundary_candidates(
            gray,
            horizontal=False,
            threshold=threshold,
            coverage_threshold=coverage_threshold,
            radius=radius,
        )
    )
    candidates.extend(
        _boundary_candidates(
            gray,
            horizontal=True,
            threshold=threshold,
            coverage_threshold=coverage_threshold,
            radius=radius,
        )
    )
    return max(candidates, key=lambda item: item.score) if candidates else None


def _boundary_candidates(
    gray: Image.Image,
    *,
    horizontal: bool,
    threshold: float,
    coverage_threshold: float,
    radius: int,
) -> list[_Split]:
    """Find seam candidates using local bins along the seam.

    A collage boundary normally affects a large fraction of the seam, while
    an object edge (hair, body, weapon, background detail) is usually local.
    The median bin response suppresses those local false positives.  We keep
    all plausible local peaks rather than selecting one global line.
    """
    pixels = gray.load()
    width, height = gray.size
    axis_size = height if horizontal else width
    perpendicular_size = width if horizontal else height
    if axis_size < 24 or perpendicular_size < 24:
        return []

    bin_count = max(6, min(16, perpendicular_size // 32))
    ranges = _ranges(perpendicular_size, bin_count)
    raw: list[float] = []
    coverage: list[float] = []

    for position in range(1, axis_size):
        bin_values: list[float] = []
        for start, end in ranges:
            if horizontal:
                changes = [
                    abs(pixels[x, position] - pixels[x, position - 1])
                    for x in range(start, end)
                ]
            else:
                changes = [
                    abs(pixels[position, y] - pixels[position - 1, y])
                    for y in range(start, end)
                ]
            bin_values.append(sum(changes) / max(1, len(changes)))

        raw.append(_median(bin_values))
        coverage.append(
            sum(value >= threshold for value in bin_values) / max(1, len(bin_values))
        )

    smoothed = _smooth(raw, radius)
    margin = max(6, round(axis_size * 0.05))
    minimum = max(5.0, threshold * 0.30)
    candidates: list[_Split] = []
    neighbourhood = max(3, radius * 3)

    for index in range(1, len(smoothed) - 1):
        position = index + 1
        if position < margin or position > axis_size - margin:
            continue
        value = smoothed[index]
        if value < minimum:
            continue
        if value < smoothed[index - 1] or value < smoothed[index + 1]:
            continue

        start = max(0, index - neighbourhood)
        end = min(len(smoothed), index + neighbourhood + 1)
        neighbours = smoothed[start:index] + smoothed[index + 1:end]
        baseline = _median(neighbours)
        prominence = value / max(1.0, baseline)
        coherence = coverage[index]

        # Either the seam is coherent across many bins, or it is exceptionally
        # prominent locally. This is deliberately less strict than V1.
        if coherence < coverage_threshold and prominence < 1.8:
            continue

        strength_score = min(1.0, value / max(threshold, 1.0))
        coherence_score = min(1.0, coherence / max(coverage_threshold, 0.01))
        prominence_score = min(1.0, max(0.0, prominence - 1.0) / 2.0)
        score = min(
            1.0,
            0.40 * strength_score
            + 0.35 * coherence_score
            + 0.25 * prominence_score,
        )
        candidates.append(
            _Split("horizontal" if horizontal else "vertical", position, score)
        )

    # Nearby peaks are the same physical seam. Keep the strongest one.
    candidates.sort(key=lambda item: item.position)
    merged: list[_Split] = []
    merge_distance = max(2, radius * 2 + 1)
    for candidate in candidates:
        if merged and candidate.position - merged[-1].position <= merge_distance:
            if candidate.score > merged[-1].score:
                merged[-1] = candidate
        else:
            merged.append(candidate)
    return merged


def _ranges(length: int, count: int) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for index in range(count):
        start = round(index * length / count)
        end = round((index + 1) * length / count)
        if end > start:
            result.append((start, end))
    return result


def _smooth(values: list[float], radius: int) -> list[float]:
    if radius <= 0 or len(values) < 3:
        return values[:]
    return [
        sum(values[max(0, index - radius):min(len(values), index + radius + 1)])
        / len(values[max(0, index - radius):min(len(values), index + radius + 1)])
        for index in range(len(values))
    ]


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _too_small(rect: Rectangle, full: Image.Image, minimum: float) -> bool:
    return rect.width < full.width * minimum or rect.height < full.height * minimum


def _unique_output_path(path: Path) -> Path:
    if not path.exists():
        return path
    index = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{index:02d}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1
