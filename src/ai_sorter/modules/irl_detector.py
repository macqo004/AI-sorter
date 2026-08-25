"""Heuristic IRL (real-life photograph) detector.

This first generation deliberately avoids external AI models. It produces an
interpretable score plus IRL / NOT_IRL / UNCERTAIN classification so the
thresholds can later be calibrated against human-reviewed samples.
"""
from __future__ import annotations

import json
import math
import os
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from ..core.database import Database, DatabaseError
from ..core.models import ModuleExecutionRecord, ModuleRecord

ProgressCallback = Callable[["IRLProgress"], None]


@dataclass(frozen=True, slots=True)
class IRLConfig:
    sample_longest_side: int = 256
    high_score_threshold: float = 0.78
    low_score_threshold: float = 0.30
    entropy_low: float = 3.0
    entropy_high: float = 7.4
    color_count_low: int = 24
    color_count_high: int = 160
    edge_density_low: float = 0.03
    edge_density_high: float = 0.24
    camera_exif_bonus: float = 0.55
    exif_bonus: float = 0.12
    photo_aspect_bonus: float = 0.06
    diversity_bonus: float = 0.08
    texture_bonus: float = 0.09
    flat_color_penalty: float = 0.12


@dataclass(frozen=True, slots=True)
class IRLProgress:
    considered: int
    processed: int
    skipped: int
    failed: int
    current_path: str | None = None


@dataclass(frozen=True, slots=True)
class IRLSummary:
    execution_id: int
    considered: int
    processed: int
    skipped: int
    failed: int
    cancelled: bool
    elapsed_seconds: float


@dataclass(frozen=True, slots=True)
class _Target:
    sha512: str
    path: Path


@dataclass(frozen=True, slots=True)
class _Result:
    sha512: str
    payload: dict[str, object]


class IRLDetector:
    module_id = "irl_detector"
    module_version = "0.1.0"
    result_key = "irl_detection"

    def __init__(
        self,
        database: Database,
        config: IRLConfig | None = None,
        worker_count: int = 0,
        batch_size: int = 128,
        scope_root: Path | None = None,
    ) -> None:
        self.database = database
        self.config = config or IRLConfig()
        self.worker_count = worker_count or max(1, min(8, (os.cpu_count() or 4) // 2 or 1))
        self.batch_size = max(16, batch_size)
        self.scope_root = scope_root.resolve() if scope_root else None
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def run(self, progress_callback: ProgressCallback | None = None) -> IRLSummary:
        started_at = datetime.now(timezone.utc)
        started_perf = time.perf_counter()
        self._cancel_event.clear()
        self.database.register_module(ModuleRecord(self.module_id, "IRL Detector", self.module_version, True))
        execution_id = self.database.start_module_execution(self.module_id, started_at)

        considered = processed = skipped = failed = 0
        cancelled = False
        status = "FAILED"
        pending: dict[Future[_Result], _Target] = {}
        result_batch: list[_Result] = []

        try:
            with ThreadPoolExecutor(max_workers=self.worker_count, thread_name_prefix="irl") as executor:
                for target in self._targets():
                    considered += 1
                    if self._cancel_event.is_set():
                        cancelled = True
                        break
                    pending[executor.submit(self._analyse_target, target)] = target
                    if len(pending) >= self.worker_count * 4:
                        done, _ = wait(pending, return_when=FIRST_COMPLETED)
                        processed, failed = self._consume_done(
                            done, pending, result_batch, processed, failed, progress_callback
                        )
                        if len(result_batch) >= self.batch_size:
                            self._persist_batch(result_batch, execution_id)
                            result_batch.clear()

                while pending:
                    done, _ = wait(pending, return_when=FIRST_COMPLETED)
                    processed, failed = self._consume_done(
                        done, pending, result_batch, processed, failed, progress_callback
                    )
                    if len(result_batch) >= self.batch_size:
                        self._persist_batch(result_batch, execution_id)
                        result_batch.clear()

                if result_batch:
                    self._persist_batch(result_batch, execution_id)

            cancelled = cancelled or self._cancel_event.is_set()
            status = "CANCELLED" if cancelled else ("COMPLETED_WITH_WARNINGS" if failed else "COMPLETED")
        finally:
            self.database.finish_module_execution(
                ModuleExecutionRecord(
                    execution_id=execution_id,
                    module_id=self.module_id,
                    started_at=started_at,
                    status=status,
                    processed_count=processed,
                    success_count=processed - failed,
                    failure_count=failed,
                )
            )

        return IRLSummary(execution_id, considered, processed, skipped, failed, cancelled, time.perf_counter() - started_perf)

    def _targets(self) -> Iterable[_Target]:
        connection = self.database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        params: list[str] = [self.module_id, self.result_key]
        scope_clause = ""
        if self.scope_root is not None:
            root = str(self.scope_root).rstrip("\\/")
            scope_clause = " AND (fl.absolute_path = ? OR fl.absolute_path LIKE ?)"
            params.extend([root, root + "\\%"])  # type: ignore[arg-type]

        cursor = connection.execute(
            f"""
            SELECT f.sha512, MIN(fl.absolute_path) AS absolute_path
            FROM file_record f
            JOIN file_location fl ON fl.sha512 = f.sha512 AND fl.location_status = 'ACTIVE'
            WHERE f.status = 'ACTIVE'
              AND NOT EXISTS (
                  SELECT 1 FROM analysis_result ar
                  WHERE ar.sha512 = f.sha512 AND ar.module_id = ? AND ar.result_key = ?
              ){scope_clause}
            GROUP BY f.sha512
            ORDER BY f.sha512
            """,
            tuple(params),
        )
        for row in cursor:
            yield _Target(str(row["sha512"]), Path(str(row["absolute_path"])))

    def _consume_done(
        self,
        done: set[Future[_Result]],
        pending: dict[Future[_Result], _Target],
        result_batch: list[_Result],
        processed: int,
        failed: int,
        progress_callback: ProgressCallback | None,
    ) -> tuple[int, int]:
        for future in done:
            target = pending.pop(future)
            try:
                result_batch.append(future.result())
                processed += 1
            except Exception:
                failed += 1
            if progress_callback:
                progress_callback(IRLProgress(0, processed, 0, failed, str(target.path)))
        return processed, failed

    def _persist_batch(self, results: list[_Result], execution_id: int) -> None:
        if not results:
            return
        try:
            with self.database.transaction() as connection:
                connection.executemany(
                    """
                    INSERT INTO analysis_result
                        (sha512, module_id, result_key, confidence, payload_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(sha512, module_id, result_key) DO UPDATE SET
                        confidence = excluded.confidence,
                        payload_json = excluded.payload_json,
                        updated_at = excluded.updated_at
                    """,
                    [
                        (
                            result.sha512,
                            self.module_id,
                            self.result_key,
                            result.payload.get("irl_score"),
                            json.dumps(
                                {**result.payload, "execution_id": execution_id, "module_version": self.module_version},
                                ensure_ascii=False,
                                sort_keys=True,
                            ),
                        )
                        for result in results
                    ],
                )
        except Exception as exc:
            raise DatabaseError("Nie udało się zapisać wyników IRL Detector w bazie danych.") from exc

    def _analyse_target(self, target: _Target) -> _Result:
        try:
            from PIL import Image, ImageStat
        except ImportError as exc:
            raise RuntimeError("Moduł IRL Detector wymaga biblioteki Pillow.") from exc

        try:
            with Image.open(target.path) as source:
                image = source.convert("RGB")
                original_width, original_height = image.size
                exif = image.getexif()
                image.thumbnail((self.config.sample_longest_side, self.config.sample_longest_side), Image.Resampling.BILINEAR)
                pixels = list(image.getdata())
        except Exception as exc:
            raise RuntimeError(f"Nie można przeanalizować obrazu: {target.path}") from exc

        if not pixels:
            raise RuntimeError(f"Obraz nie zawiera analizowalnych pikseli: {target.path}")

        gray = image.convert("L")
        entropy = ImageStat.Stat(gray).entropy
        quantized = image.resize((64, 64), Image.Resampling.BILINEAR).quantize(colors=256)
        palette_counts = quantized.getcolors(maxcolors=256 * 64 * 64) or []
        unique_colors = len(palette_counts)

        edge_count = 0
        flat_pairs = 0
        pixel_pairs = 0
        small = image.resize((64, 64), Image.Resampling.BILINEAR)
        rgb = list(small.getdata())
        width, height = small.size
        for y in range(height):
            base = y * width
            for x in range(width):
                current = rgb[base + x]
                if x + 1 < width:
                    right = rgb[base + x + 1]
                    delta = abs(current[0] - right[0]) + abs(current[1] - right[1]) + abs(current[2] - right[2])
                    edge_count += delta
                    flat_pairs += delta <= 12
                    pixel_pairs += 1
                if y + 1 < height:
                    down = rgb[base + width + x]
                    delta = abs(current[0] - down[0]) + abs(current[1] - down[1]) + abs(current[2] - down[2])
                    edge_count += delta
                    flat_pairs += delta <= 12
                    pixel_pairs += 1

        mean_edge = edge_count / max(1, pixel_pairs * 3 * 255)
        flat_ratio = flat_pairs / max(1, pixel_pairs)
        aspect = original_width / original_height if original_height else 1.0
        photo_aspect = 1.0 if any(abs(aspect - candidate) <= 0.05 for candidate in (4 / 3, 3 / 2, 16 / 9, 1.0)) else 0.0

        camera_exif = any(key in exif for key in (0x010F, 0x0110, 0x920A, 0x829A, 0x829D))
        any_exif = len(exif) > 0

        def normalized(value: float, low: float, high: float) -> float:
            if high <= low:
                return 0.0
            return max(0.0, min(1.0, (value - low) / (high - low)))

        entropy_score = normalized(entropy, self.config.entropy_low, self.config.entropy_high)
        diversity_score = normalized(unique_colors, self.config.color_count_low, self.config.color_count_high)
        texture_score = normalized(mean_edge, self.config.edge_density_low, self.config.edge_density_high)

        score = 0.0
        score += entropy_score * 0.22
        score += diversity_score * 0.18
        score += texture_score * 0.15
        score += photo_aspect * self.config.photo_aspect_bonus
        score += self.config.camera_exif_bonus if camera_exif else 0.0
        score += self.config.exif_bonus if any_exif and not camera_exif else 0.0
        score += self.config.diversity_bonus if diversity_score >= 0.65 else 0.0
        score += self.config.texture_bonus if texture_score >= 0.55 else 0.0
        score -= self.config.flat_color_penalty if flat_ratio >= 0.70 else 0.0
        score = max(0.0, min(1.0, score))

        if score >= self.config.high_score_threshold:
            classification = "IRL"
        elif score <= self.config.low_score_threshold:
            classification = "NOT_IRL"
        else:
            classification = "UNCERTAIN"

        payload = {
            "classification": classification,
            "irl_score": round(score, 6),
            "entropy": round(entropy, 6),
            "unique_colors_64x64": unique_colors,
            "normalized_edge_density": round(mean_edge, 6),
            "flat_pair_ratio": round(flat_ratio, 6),
            "aspect_ratio": round(aspect, 6),
            "photo_aspect_match": bool(photo_aspect),
            "has_exif": any_exif,
            "camera_exif": camera_exif,
            "sample_width": image.width,
            "sample_height": image.height,
            "original_width": original_width,
            "original_height": original_height,
            "config": {
                "high_score_threshold": self.config.high_score_threshold,
                "low_score_threshold": self.config.low_score_threshold,
                "sample_longest_side": self.config.sample_longest_side,
            },
        }
        return _Result(target.sha512, payload)
