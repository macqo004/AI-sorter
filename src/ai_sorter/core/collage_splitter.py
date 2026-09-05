"""Detect and split rectangular image collages without database writes.

V3 treats a collage as a rectangular grid with locally present boundaries.
It first finds long, coherent candidate seams across the whole image, then
checks each candidate inside each grid band. Grid cells are finally merged
where a candidate seam is absent. This avoids recursive splitting of image
content such as hair, bodies, weapons, or background details.
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
class _Line:
    position: int
    score: float
    coverage: float


class CollageSplitter:
    """Split touching rectangular collage panels using a global scaffold."""

    def __init__(
        self,
        *,
        analysis_size: int = 1024,
        min_piece_ratio: float = 0.05,
        edge_threshold: float = 18.0,
        coverage_threshold: float = 0.40,
        smooth_radius: int = 2,
    ) -> None:
        self.analysis_size = max(256, min(1536, int(analysis_size)))
        self.min_piece_ratio = max(0.01, min(0.40, float(min_piece_ratio)))
        self.edge_threshold = max(5.0, min(100.0, float(edge_threshold)))
        self.coverage_threshold = max(0.15, min(0.90, float(coverage_threshold)))
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

    def _detect_grid(
        self,
        image: Image.Image,
        original_width: int,
        original_height: int,
    ) -> tuple[list[Rectangle], float]:
        gray = image.convert("L")
        x_lines = _find_global_lines(
            gray,
            horizontal=False,
            threshold=self.edge_threshold,
            coverage_threshold=self.coverage_threshold,
            radius=self.smooth_radius,
        )
        y_lines = _find_global_lines(
            gray,
            horizontal=True,
            threshold=self.edge_threshold,
            coverage_threshold=self.coverage_threshold,
            radius=self.smooth_radius,
        )

        if not x_lines and not y_lines:
            return [Rectangle(0, 0, original_width, original_height)], 0.0

        x_positions = _dedupe_positions([0] + [line.position for line in x_lines] + [gray.width], gray.width)
        y_positions = _dedupe_positions([0] + [line.position for line in y_lines] + [gray.height], gray.height)
        columns = len(x_positions) - 1
        rows = len(y_positions) - 1
        if columns * rows > 256:
            return [Rectangle(0, 0, original_width, original_height)], 0.0

        active_vertical = [[False] * max(0, columns - 1) for _ in range(rows)]
        active_horizontal = [[False] * columns for _ in range(max(0, rows - 1))]
        seam_scores: list[float] = []

        for row in range(rows):
            top, bottom = y_positions[row], y_positions[row + 1]
            for col in range(columns - 1):
                x = x_positions[col + 1]
                score = _local_line_score(
                    gray, x, top, bottom, horizontal=False, threshold=self.edge_threshold
                )
                active_vertical[row][col] = score >= 0.42
                if active_vertical[row][col]:
                    seam_scores.append(score)

        for row in range(rows - 1):
            y = y_positions[row + 1]
            for col in range(columns):
                left, right = x_positions[col], x_positions[col + 1]
                score = _local_line_score(
                    gray, y, left, right, horizontal=True, threshold=self.edge_threshold
                )
                active_horizontal[row][col] = score >= 0.42
                if active_horizontal[row][col]:
                    seam_scores.append(score)

        components = _grid_components(rows, columns, active_vertical, active_horizontal)
        rectangles: list[Rectangle] = []
        for cells in components:
            min_row = min(row for row, _ in cells)
            max_row = max(row for row, _ in cells)
            min_col = min(col for _, col in cells)
            max_col = max(col for _, col in cells)
            expected = (max_row - min_row + 1) * (max_col - min_col + 1)
            if len(cells) != expected:
                for row, col in cells:
                    rectangles.append(
                        Rectangle(x_positions[col], y_positions[row], x_positions[col + 1], y_positions[row + 1])
                    )
                continue
            rectangles.append(
                Rectangle(
                    x_positions[min_col],
                    y_positions[min_row],
                    x_positions[max_col + 1],
                    y_positions[max_row + 1],
                )
            )

        min_width = gray.width * self.min_piece_ratio
        min_height = gray.height * self.min_piece_ratio
        rectangles = [
            rect for rect in rectangles if rect.width >= min_width and rect.height >= min_height
        ]
        rectangles.sort(key=lambda rect: (rect.top, rect.left))
        if len(rectangles) < 2:
            return [Rectangle(0, 0, original_width, original_height)], 0.0

        scale_x = original_width / gray.width
        scale_y = original_height / gray.height
        scaled_rectangles = [
            Rectangle(
                round(rect.left * scale_x), round(rect.top * scale_y),
                round(rect.right * scale_x), round(rect.bottom * scale_y),
            )
            for rect in rectangles
        ]
        confidence = sum(seam_scores) / len(seam_scores) if seam_scores else 0.0
        return scaled_rectangles, max(0.0, min(1.0, confidence))


def _resize_for_analysis(image: Image.Image, limit: int) -> Image.Image:
    scale = min(1.0, limit / max(image.width, image.height))
    if scale == 1.0:
        return image.copy()
    return image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.BILINEAR,
    )


def _find_global_lines(
    gray: Image.Image,
    *,
    horizontal: bool,
    threshold: float,
    coverage_threshold: float,
    radius: int,
) -> list[_Line]:
    """Find long straight seams; these are positional priors, not final cuts."""
    pixels = gray.load()
    width, height = gray.size
    axis_size = height if horizontal else width
    perpendicular_size = width if horizontal else height
    if axis_size < 32 or perpendicular_size < 32:
        return []

    bin_count = max(8, min(24, perpendicular_size // 32))
    ranges = _ranges(perpendicular_size, bin_count)
    raw: list[float] = []
    coverages: list[float] = []
    local_threshold = max(7.0, threshold * 0.45)

    for position in range(1, axis_size):
        values: list[float] = []
        for start, end in ranges:
            if horizontal:
                changes = [abs(pixels[x, position] - pixels[x, position - 1]) for x in range(start, end)]
            else:
                changes = [abs(pixels[position, y] - pixels[position - 1, y]) for y in range(start, end)]
            values.append(sum(changes) / max(1, len(changes)))
        raw.append(_median(values))
        coverages.append(sum(value >= local_threshold for value in values) / len(values))

    smoothed = _smooth(raw, radius)
    candidates: list[_Line] = []
    margin = max(8, round(axis_size * 0.035))
    for index in range(1, len(smoothed) - 1):
        position = index + 1
        if position < margin or position > axis_size - margin:
            continue
        value = smoothed[index]
        coherent = coverages[index]
        if value < threshold * 0.30 or coherent < coverage_threshold:
            continue
        if value < smoothed[index - 1] or value < smoothed[index + 1]:
            continue
        neighbourhood = smoothed[max(0, index - max(4, radius * 3)):min(len(smoothed), index + max(4, radius * 3) + 1)]
        neighbours = [v for j, v in enumerate(neighbourhood) if j != len(neighbourhood) // 2]
        baseline = _median(neighbours)
        prominence = value / max(1.0, baseline)
        score = min(
            1.0,
            0.55 * min(1.0, value / max(threshold, 1.0))
            + 0.30 * min(1.0, coherent / max(coverage_threshold, 0.01))
            + 0.15 * min(1.0, max(0.0, prominence - 1.0) / 2.0),
        )
        candidates.append(_Line(position, score, coherent))

    candidates.sort(key=lambda line: line.score, reverse=True)
    selected: list[_Line] = []
    min_distance = max(6, round(axis_size * 0.018))
    for candidate in candidates:
        if all(abs(candidate.position - other.position) > min_distance for other in selected):
            selected.append(candidate)
        if len(selected) >= 12:
            break
    if selected:
        strongest = max(line.score for line in selected)
        selected = [line for line in selected if line.score >= max(0.55, strongest * 0.70)]
    return sorted(selected, key=lambda line: line.position)


def _local_line_score(
    gray: Image.Image,
    position: int,
    start: int,
    end: int,
    *,
    horizontal: bool,
    threshold: float,
) -> float:
    """Score a global candidate only inside one grid band."""
    pixels = gray.load()
    length = end - start
    if length < 16:
        return 0.0
    bins = max(4, min(12, length // 32))
    ranges = _ranges(length, bins)
    values: list[float] = []
    for local_start, local_end in ranges:
        a, b = start + local_start, start + local_end
        if horizontal:
            changes = [abs(pixels[x, position] - pixels[x, position - 1]) for x in range(a, b)]
        else:
            changes = [abs(pixels[position, y] - pixels[position - 1, y]) for y in range(a, b)]
        values.append(sum(changes) / max(1, len(changes)))
    strong = sum(value >= threshold for value in values) / len(values)
    strength = min(1.0, _median(values) / max(threshold, 1.0))
    return 0.55 * strong + 0.45 * strength


def _grid_components(
    rows: int,
    columns: int,
    vertical: list[list[bool]],
    horizontal: list[list[bool]],
) -> list[list[tuple[int, int]]]:
    visited: set[tuple[int, int]] = set()
    components: list[list[tuple[int, int]]] = []
    for start_row in range(rows):
        for start_col in range(columns):
            if (start_row, start_col) in visited:
                continue
            stack = [(start_row, start_col)]
            visited.add((start_row, start_col))
            component: list[tuple[int, int]] = []
            while stack:
                row, col = stack.pop()
                component.append((row, col))
                if col > 0 and not vertical[row][col - 1] and (row, col - 1) not in visited:
                    visited.add((row, col - 1)); stack.append((row, col - 1))
                if col < columns - 1 and not vertical[row][col] and (row, col + 1) not in visited:
                    visited.add((row, col + 1)); stack.append((row, col + 1))
                if row > 0 and not horizontal[row - 1][col] and (row - 1, col) not in visited:
                    visited.add((row - 1, col)); stack.append((row - 1, col))
                if row < rows - 1 and not horizontal[row][col] and (row + 1, col) not in visited:
                    visited.add((row + 1, col)); stack.append((row + 1, col))
            components.append(component)
    return components


def _dedupe_positions(values: list[int], maximum: int) -> list[int]:
    result: list[int] = []
    for value in sorted(set(max(0, min(maximum, int(v))) for v in values)):
        if not result or value - result[-1] >= 4:
            result.append(value)
    if not result or result[-1] != maximum:
        result.append(maximum)
    if result[0] != 0:
        result.insert(0, 0)
    return result


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
    result: list[float] = []
    for index in range(len(values)):
        start = max(0, index - radius)
        end = min(len(values), index + radius + 1)
        window = values[start:end]
        result.append(sum(window) / len(window))
    return result


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _unique_output_path(path: Path) -> Path:
    if not path.exists():
        return path
    index = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{index:02d}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1
