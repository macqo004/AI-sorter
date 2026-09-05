"""Collage splitter V4.

The detector treats touching collages as a grid problem rather than recursively
splitting arbitrary image edges.  Strong straight-line candidates are found
from 1-D edge projections, regular line spacing is used to reject content
edges, and every candidate seam is then validated locally.  No database is
read or written.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
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
class _Line:
    position: int
    score: float


class CollageSplitter:
    """Detect rectangular collage panels without touching the database."""

    def __init__(
        self,
        *,
        analysis_size: int = 1024,
        min_piece_ratio: float = 0.05,
        edge_threshold: float = 18.0,
        coverage_threshold: float = 0.25,
        smooth_radius: int = 2,
    ) -> None:
        self.analysis_size = max(256, min(1536, int(analysis_size)))
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
            rectangles, confidence = self._detect_grid(scaled, width, height)
        return SplitResult(source, width, height, tuple(rectangles), confidence)

    def split(self, result: SplitResult, *, apply: bool = False) -> tuple[Path, ...]:
        if len(result.rectangles) < 2:
            return ()
        outputs = tuple(
            result.source.parent / f"{result.source.stem}_{i:02d}{result.source.suffix}"
            for i in range(1, len(result.rectangles) + 1)
        )
        if not apply:
            return outputs
        with Image.open(result.source) as image:
            image = ImageOps.exif_transpose(image)
            created: list[Path] = []
            for i, rect in enumerate(result.rectangles, 1):
                destination = _unique_output_path(outputs[i - 1])
                image.crop((rect.left, rect.top, rect.right, rect.bottom)).save(destination)
                created.append(destination)
            return tuple(created)

    def _detect_grid(
        self, image: Image.Image, original_width: int, original_height: int
    ) -> tuple[list[Rectangle], float]:
        gray = image.convert("L")
        x_lines = _regular_lines(
            gray, horizontal=False, threshold=self.edge_threshold, smooth_radius=self.smooth_radius
        )
        y_lines = _regular_lines(
            gray, horizontal=True, threshold=self.edge_threshold, smooth_radius=self.smooth_radius
        )

        # The regular-grid detector is deliberately conservative.  A hard
        # limit prevents a noisy image from becoming a huge artificial grid.
        if len(x_lines) > 6 or len(y_lines) > 6:
            return [Rectangle(0, 0, original_width, original_height)], 0.0

        xs = _dedupe([0] + [line.position for line in x_lines] + [gray.width])
        ys = _dedupe([0] + [line.position for line in y_lines] + [gray.height])
        cols, rows = len(xs) - 1, len(ys) - 1
        if cols * rows > 64:
            return [Rectangle(0, 0, original_width, original_height)], 0.0

        # A candidate line is a real seam only when its local edge evidence is
        # present across the current band.  Missing seams mean adjacent cells
        # belong to one larger panel.
        v_active = [[False] * (cols - 1) for _ in range(rows)]
        h_active = [[False] * cols for _ in range(rows - 1)]
        seam_scores: list[float] = []

        for r in range(rows):
            for c in range(cols - 1):
                score = _local_seam(gray, xs[c + 1], ys[r], ys[r + 1], horizontal=False, threshold=self.edge_threshold)
                v_active[r][c] = score >= self.coverage_threshold
                if v_active[r][c]:
                    seam_scores.append(score)

        for r in range(rows - 1):
            for c in range(cols):
                score = _local_seam(gray, ys[r + 1], xs[c], xs[c + 1], horizontal=True, threshold=self.edge_threshold)
                h_active[r][c] = score >= self.coverage_threshold
                if h_active[r][c]:
                    seam_scores.append(score)

        components = _components(rows, cols, v_active, h_active)
        rectangles: list[Rectangle] = []
        for cells in components:
            r0, r1 = min(r for r, _ in cells), max(r for r, _ in cells)
            c0, c1 = min(c for _, c in cells), max(c for _, c in cells)
            expected = (r1 - r0 + 1) * (c1 - c0 + 1)
            if len(cells) != expected:
                # Non-rectangular connected components cannot be represented by
                # one crop; keep their cells separate rather than inventing a
                # crop that contains another panel.
                for r, c in cells:
                    rectangles.append(Rectangle(xs[c], ys[r], xs[c + 1], ys[r + 1]))
            else:
                rectangles.append(Rectangle(xs[c0], ys[r0], xs[c1 + 1], ys[r1 + 1]))

        min_w = gray.width * self.min_piece_ratio
        min_h = gray.height * self.min_piece_ratio
        rectangles = [r for r in rectangles if r.width >= min_w and r.height >= min_h]
        rectangles.sort(key=lambda r: (r.top, r.left))
        if len(rectangles) < 2:
            return [Rectangle(0, 0, original_width, original_height)], 0.0

        sx, sy = original_width / gray.width, original_height / gray.height
        scaled = [
            Rectangle(round(r.left * sx), round(r.top * sy), round(r.right * sx), round(r.bottom * sy))
            for r in rectangles
        ]
        confidence = sum(seam_scores) / len(seam_scores) if seam_scores else 0.0
        return scaled, max(0.0, min(1.0, confidence))


def _resize_for_analysis(image: Image.Image, limit: int) -> Image.Image:
    scale = min(1.0, limit / max(image.width, image.height))
    if scale == 1.0:
        return image.copy()
    return image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.BILINEAR,
    )


def _regular_lines(gray: Image.Image, *, horizontal: bool, threshold: float, smooth_radius: int) -> list[_Line]:
    """Find a small set of straight, approximately periodic seam positions.

    Mean edge projections are intentionally used here instead of the median
    used by earlier versions.  A panel border can be strong on only part of
    its length because the two adjacent photos can have similar colours.
    Regular-spacing selection then rejects most internal picture edges.
    """
    pixels = gray.load()
    width, height = gray.size
    axis = height if horizontal else width
    perp = width if horizontal else height
    if axis < 64 or perp < 64:
        return []

    projection: list[float] = []
    for p in range(1, axis):
        total = 0.0
        if horizontal:
            for x in range(perp):
                total += abs(pixels[x, p] - pixels[x, p - 1])
        else:
            for y in range(perp):
                total += abs(pixels[p, y] - pixels[p - 1, y])
        projection.append(total / perp)

    smoothed = _smooth(projection, smooth_radius)
    candidates: list[_Line] = []
    margin = max(8, round(axis * 0.04))
    for i in range(2, len(smoothed) - 2):
        p = i + 1
        value = smoothed[i]
        if p < margin or p > axis - margin:
            continue
        if value < threshold * 0.45:
            continue
        if value < smoothed[i - 1] or value < smoothed[i + 1]:
            continue
        left = smoothed[max(0, i - 8):i]
        right = smoothed[i + 1:min(len(smoothed), i + 9)]
        baseline = _median(left + right)
        score = min(1.0, 0.55 * min(1.0, value / threshold) + 0.45 * min(1.0, value / max(1.0, baseline * 2.0)))
        candidates.append(_Line(p, score))

    # Keep the strongest local maxima before looking for a lattice.
    candidates.sort(key=lambda line: line.score, reverse=True)
    shortlist: list[_Line] = []
    min_distance = max(8, round(axis * 0.025))
    for line in candidates:
        if all(abs(line.position - other.position) >= min_distance for other in shortlist):
            shortlist.append(line)
        if len(shortlist) >= 14:
            break

    return _select_regular(shortlist, axis)


def _select_regular(candidates: list[_Line], axis: int) -> list[_Line]:
    """Select the strongest 2..5-line arithmetic lattice from candidates."""
    if len(candidates) < 2:
        return []
    best: tuple[float, tuple[_Line, ...]] | None = None
    # Most image collages have a useful repeated panel width/height.  Do not
    # consider tiny spacing: those are much more likely to be picture detail.
    min_gap = max(24, round(axis * 0.12))
    for count in range(2, min(5, len(candidates)) + 1):
        for combo in combinations(candidates, count):
            positions = sorted(line.position for line in combo)
            gaps = [b - a for a, b in zip(positions, positions[1:])]
            if min(gaps) < min_gap:
                continue
            mean_gap = sum(gaps) / len(gaps)
            variation = max(gaps) - min(gaps)
            regularity = max(0.0, 1.0 - variation / max(1.0, mean_gap * 0.22))
            strength = sum(line.score for line in combo) / count
            span = (positions[-1] - positions[0]) / axis
            # Prefer three or more coherent lines, but allow two-line collages.
            count_bonus = 0.06 * min(count - 2, 2)
            score = 0.52 * regularity + 0.38 * strength + 0.10 * min(1.0, span / 0.45) + count_bonus
            if best is None or score > best[0]:
                best = (score, combo)
    if best is None or best[0] < 0.55:
        return []
    return sorted(best[1], key=lambda line: line.position)


def _local_seam(gray: Image.Image, position: int, start: int, end: int, *, horizontal: bool, threshold: float) -> float:
    pixels = gray.load()
    length = end - start
    if length < 24:
        return 0.0
    values: list[float] = []
    strong = 0
    for q in range(start, end):
        if horizontal:
            value = abs(pixels[q, position] - pixels[q, position - 1])
        else:
            value = abs(pixels[position, q] - pixels[position - 1, q])
        values.append(float(value))
        if value >= threshold:
            strong += 1
    coverage = strong / length
    strength = min(1.0, _median(values) / threshold)
    return 0.60 * coverage + 0.40 * strength


def _components(rows: int, cols: int, vertical: list[list[bool]], horizontal: list[list[bool]]) -> list[list[tuple[int, int]]]:
    seen: set[tuple[int, int]] = set()
    result: list[list[tuple[int, int]]] = []
    for sr in range(rows):
        for sc in range(cols):
            if (sr, sc) in seen:
                continue
            stack = [(sr, sc)]
            seen.add((sr, sc))
            cells: list[tuple[int, int]] = []
            while stack:
                r, c = stack.pop()
                cells.append((r, c))
                if c > 0 and not vertical[r][c - 1] and (r, c - 1) not in seen:
                    seen.add((r, c - 1)); stack.append((r, c - 1))
                if c < cols - 1 and not vertical[r][c] and (r, c + 1) not in seen:
                    seen.add((r, c + 1)); stack.append((r, c + 1))
                if r > 0 and not horizontal[r - 1][c] and (r - 1, c) not in seen:
                    seen.add((r - 1, c)); stack.append((r - 1, c))
                if r < rows - 1 and not horizontal[r][c] and (r + 1, c) not in seen:
                    seen.add((r + 1, c)); stack.append((r + 1, c))
            result.append(cells)
    return result


def _dedupe(values: list[int]) -> list[int]:
    result: list[int] = []
    for value in sorted(set(values)):
        if not result or value - result[-1] >= 4:
            result.append(value)
    return result


def _smooth(values: list[float], radius: int) -> list[float]:
    if radius <= 0:
        return values[:]
    result: list[float] = []
    for i in range(len(values)):
        start, end = max(0, i - radius), min(len(values), i + radius + 1)
        result.append(sum(values[start:end]) / (end - start))
    return result


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    m = len(ordered) // 2
    return ordered[m] if len(ordered) % 2 else (ordered[m - 1] + ordered[m]) / 2.0


def _unique_output_path(path: Path) -> Path:
    if not path.exists():
        return path
    index = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{index:02d}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1
