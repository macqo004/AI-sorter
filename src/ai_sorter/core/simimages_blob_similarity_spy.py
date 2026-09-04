"""Read-only experiment for checking whether SimImages BLOBs encode visual similarity."""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from ai_sorter.core.simimages_dimension_spy import SimImagesDimensionSpy


@dataclass(frozen=True, slots=True)
class BlobSimilarityPair:
    left_id: int
    right_id: int
    visual_distance: float
    blob_distance: float


@dataclass(frozen=True, slots=True)
class BlobSimilarityResult:
    requested_images: int
    usable_images: int
    pair_count: int
    spearman_correlation: float | None
    visual_top_count: int
    blob_top_count: int
    top_overlap_count: int
    closest_visual_pairs: tuple[BlobSimilarityPair, ...]
    closest_blob_pairs: tuple[BlobSimilarityPair, ...]

    def format_text(self) -> str:
        lines = [
            "SimImages BLOB similarity experiment",
            f"Requested images: {self.requested_images:,}",
            f"Usable images: {self.usable_images:,}",
            f"Pairs compared: {self.pair_count:,}",
            f"Spearman correlation (visual distance vs BLOB distance): {_fmt(self.spearman_correlation)}",
            f"Top visual pairs compared: {self.visual_top_count}",
            f"Top BLOB pairs compared: {self.blob_top_count}",
            f"Overlap of top sets: {self.top_overlap_count}",
            "",
            "Closest by visual distance:",
        ]
        for pair in self.closest_visual_pairs:
            lines.append(
                f"  {pair.left_id} <-> {pair.right_id} | "
                f"visual={pair.visual_distance:.6f} | blob={pair.blob_distance:.6f}"
            )
        lines.append("")
        lines.append("Closest by BLOB distance:")
        for pair in self.closest_blob_pairs:
            lines.append(
                f"  {pair.left_id} <-> {pair.right_id} | "
                f"blob={pair.blob_distance:.6f} | visual={pair.visual_distance:.6f}"
            )
        lines.append("")
        lines.append(
            "Safety: SQLite is opened read-only and images are read only for a small visual fingerprint. "
            "No cache row or image file is modified."
        )
        return "\n".join(lines)


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:+.4f}"


class SimImagesBlobSimilaritySpy:
    """Compare BLOB distances against a simple visual distance on live cache rows."""

    def analyze(
        self,
        database_path: Path,
        *,
        requested_images: int = 120,
        max_cache_rows: int = 10_000,
        visual_size: int = 32,
        top_fraction: float = 0.10,
        display_count: int = 10,
    ) -> BlobSimilarityResult:
        requested_images = max(4, min(300, int(requested_images)))
        max_cache_rows = max(requested_images, min(100_000, int(max_cache_rows)))
        visual_size = max(8, min(64, int(visual_size)))
        top_fraction = max(0.01, min(0.50, float(top_fraction)))
        display_count = max(0, min(20, int(display_count)))

        sampled = SimImagesDimensionSpy().analyze(
            database_path,
            requested_files=requested_images,
            max_cache_rows=max_cache_rows,
            sample_display_count=requested_images,
            compute_sha512=False,
        )

        fingerprints: list[tuple[int, list[float], bytes]] = []
        for row in sampled.rows:
            try:
                visual = _visual_fingerprint(Path(row.path), visual_size)
            except Exception:
                continue
            payload = bytes.fromhex(row.payload_hex)
            if not payload:
                continue
            fingerprints.append((row.row_id, visual, payload))

        pairs: list[BlobSimilarityPair] = []
        for left, right in itertools.combinations(fingerprints, 2):
            pairs.append(
                BlobSimilarityPair(
                    left_id=left[0],
                    right_id=right[0],
                    visual_distance=_visual_distance(left[1], right[1]),
                    blob_distance=_blob_distance(left[2], right[2]),
                )
            )

        correlation = _spearman(
            [pair.visual_distance for pair in pairs],
            [pair.blob_distance for pair in pairs],
        )
        top_n = max(1, int(len(pairs) * top_fraction)) if pairs else 0
        visual_sorted = sorted(pairs, key=lambda pair: (pair.visual_distance, pair.left_id, pair.right_id))
        blob_sorted = sorted(pairs, key=lambda pair: (pair.blob_distance, pair.left_id, pair.right_id))
        visual_ids = {_pair_key(pair) for pair in visual_sorted[:top_n]}
        blob_ids = {_pair_key(pair) for pair in blob_sorted[:top_n]}

        return BlobSimilarityResult(
            requested_images=requested_images,
            usable_images=len(fingerprints),
            pair_count=len(pairs),
            spearman_correlation=correlation,
            visual_top_count=top_n,
            blob_top_count=top_n,
            top_overlap_count=len(visual_ids & blob_ids),
            closest_visual_pairs=tuple(visual_sorted[:display_count]),
            closest_blob_pairs=tuple(blob_sorted[:display_count]),
        )


def _visual_fingerprint(path: Path, size: int) -> list[float]:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("L")
        image.thumbnail((size, size), Image.Resampling.BILINEAR)
        canvas = Image.new("L", (size, size), color=0)
        offset = ((size - image.width) // 2, (size - image.height) // 2)
        canvas.paste(image, offset)
        return [value / 255.0 for value in canvas.tobytes()]


def _visual_distance(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return math.inf
    return sum((a - b) ** 2 for a, b in zip(left, right)) / len(left)


def _blob_distance(left: bytes, right: bytes) -> float:
    length = min(len(left), len(right))
    if length == 0:
        return math.inf
    return sum(abs(a - b) for a, b in zip(left[:length], right[:length])) / (length * 255.0)


def _pair_key(pair: BlobSimilarityPair) -> tuple[int, int]:
    return min(pair.left_id, pair.right_id), max(pair.left_id, pair.right_id)


def _rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        while end < len(order) and values[order[end]] == values[order[cursor]]:
            end += 1
        rank = (cursor + end - 1) / 2.0 + 1.0
        for index in order[cursor:end]:
            ranks[index] = rank
        cursor = end
    return ranks


def _spearman(left: list[float], right: list[float]) -> float | None:
    if len(left) < 3 or len(left) != len(right):
        return None
    return _pearson(_rank(left), _rank(right))


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) < 3 or len(left) != len(right):
        return None
    mean_left = sum(left) / len(left)
    mean_right = sum(right) / len(right)
    centered_left = [value - mean_left for value in left]
    centered_right = [value - mean_right for value in right]
    denom_left = math.sqrt(sum(value * value for value in centered_left))
    denom_right = math.sqrt(sum(value * value for value in centered_right))
    if denom_left == 0.0 or denom_right == 0.0:
        return None
    return sum(a * b for a, b in zip(centered_left, centered_right)) / (denom_left * denom_right)
