"""Color Analysis module: BW and monochrome detection without semantic AI models."""

from __future__ import annotations

import colorsys
import json
import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from ..core.database import Database, DatabaseError
from ..core.models import ModuleExecutionRecord, ModuleRecord

ProgressCallback = Callable[["ColorProgress"], None]


@dataclass(frozen=True, slots=True)
class ColorAnalysisConfig:
    """Initial deterministic thresholds; later exposed through Configuration Manager."""

    sample_longest_side: int = 256
    bw_channel_delta: int = 12
    bw_ratio: float = 0.995
    mostly_bw_ratio: float = 0.90
    saturation_floor: float = 0.15
    minimum_saturated_ratio: float = 0.20
    monochrome_dominant_ratio: float = 0.82
    mostly_monochrome_dominant_ratio: float = 0.60
    hue_bins: int = 18


@dataclass(frozen=True, slots=True)
class ColorProgress:
    considered: int
    processed: int
    skipped: int
    failed: int
    current_path: str | None = None


@dataclass(frozen=True, slots=True)
class ColorSummary:
    execution_id: int
    considered: int
    processed: int
    skipped: int
    failed: int
    cancelled: bool
    elapsed_seconds: float
    scope_root: str | None = None


@dataclass(frozen=True, slots=True)
class _Target:
    sha512: str
    path: Path


@dataclass(frozen=True, slots=True)
class _Result:
    sha512: str
    payload: dict[str, object]


class ColorAnalysis:
    """Analyse global image colour characteristics and persist module-owned results."""

    module_id = "color_analysis"
    module_version = "0.1.1"
    result_key = "color_analysis"

    def __init__(
        self,
        database: Database,
        config: ColorAnalysisConfig | None = None,
        worker_count: int = 0,
        batch_size: int = 128,
    ) -> None:
        self.database = database
        self.config = config or ColorAnalysisConfig()
        self.worker_count = worker_count or max(1, min(8, (os.cpu_count() or 4) // 2 or 1))
        self.batch_size = max(16, batch_size)
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def run(
        self,
        scope_root: Path | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> ColorSummary:
        normalized_scope: Path | None = None
        if scope_root is not None:
            normalized_scope = scope_root.resolve()
            if not normalized_scope.exists() or not normalized_scope.is_dir():
                raise ValueError(f"Folder zakresu nie istnieje lub nie jest katalogiem: {normalized_scope}")

        started_at = datetime.now(timezone.utc)
        started_perf = time.perf_counter()
        self._cancel_event.clear()
        self.database.register_module(
            ModuleRecord(
                module_id=self.module_id,
                display_name="Color Analysis",
                module_version=self.module_version,
                enabled=True,
            )
        )
        execution_id = self.database.start_module_execution(self.module_id, started_at)

        considered = processed = skipped = failed = 0
        cancelled = False
        status = "FAILED"
        pending: dict[Future[_Result], _Target] = {}
        result_batch: list[_Result] = []

        try:
            with ThreadPoolExecutor(max_workers=self.worker_count, thread_name_prefix="color") as executor:
                for target in self._targets(normalized_scope):
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
                    result_batch.clear()

            cancelled = cancelled or self._cancel_event.is_set()
            status = "CANCELLED" if cancelled else ("COMPLETED_WITH_WARNINGS" if failed else "COMPLETED")
        except DatabaseError:
            status = "FAILED"
            raise
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

        return ColorSummary(
            execution_id=execution_id,
            considered=considered,
            processed=processed,
            skipped=skipped,
            failed=failed,
            cancelled=cancelled,
            elapsed_seconds=time.perf_counter() - started_perf,
            scope_root=str(normalized_scope) if normalized_scope else None,
        )

    def _targets(self, scope_root: Path | None = None) -> Iterable[_Target]:
        connection = self.database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")

        params: list[str] = [self.module_id, self.result_key]
        scope_clause = ""
        if scope_root is not None:
            root_text = str(scope_root).rstrip("\\/")
            prefix = root_text + "\\"
            scope_clause = " AND (fl.absolute_path = ? OR fl.absolute_path LIKE ?)"
            params.extend([root_text, prefix + "%"])

        cursor = connection.execute(
            f"""
            SELECT f.sha512, MIN(fl.absolute_path) AS absolute_path
            FROM file_record AS f
            JOIN file_location AS fl
              ON fl.sha512 = f.sha512 AND fl.location_status = 'ACTIVE'
            WHERE f.status = 'ACTIVE'
              AND NOT EXISTS (
                  SELECT 1
                  FROM analysis_result AS ar
                  WHERE ar.sha512 = f.sha512
                    AND ar.module_id = ?
                    AND ar.result_key = ?
              )
              {scope_clause}
            GROUP BY f.sha512
            ORDER BY f.sha512
            """,
            params,
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
                progress_callback(ColorProgress(0, processed, 0, failed, str(target.path)))
        return processed, failed

    def _persist_batch(self, results: list[_Result], execution_id: int) -> None:
        connection = self.database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
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
                            None,
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
            raise DatabaseError("Nie udało się zapisać wyników analizy kolorów w bazie danych.") from exc

    @staticmethod
    def _analyse_target(target: _Target) -> _Result:
        try:
            from PIL import Image, ImageOps
        except ImportError as exc:
            raise RuntimeError(
                "Moduł Color Analysis nie może wystartować, ponieważ biblioteka Pillow nie jest poprawnie zainstalowana. "
                "Uruchom ponownie installer AI-Sorter, aby naprawić środowisko."
            ) from exc

        config = ColorAnalysisConfig()
        try:
            with Image.open(target.path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                original_width, original_height = image.size
                image.thumbnail(
                    (config.sample_longest_side, config.sample_longest_side),
                    Image.Resampling.BILINEAR,
                )
                pixels = list(image.getdata())
        except Exception as exc:
            raise RuntimeError(f"Nie można przeanalizować obrazu: {target.path}") from exc

        if not pixels:
            raise RuntimeError(f"Obraz nie zawiera analizowalnych pikseli: {target.path}")

        gray_like = 0
        saturated = 0
        hue_weights = [0.0] * config.hue_bins
        for red, green, blue in pixels:
            if max(red, green, blue) - min(red, green, blue) <= config.bw_channel_delta:
                gray_like += 1
            hue, saturation, _value = colorsys.rgb_to_hsv(red / 255.0, green / 255.0, blue / 255.0)
            if saturation >= config.saturation_floor:
                saturated += 1
                hue_index = min(config.hue_bins - 1, int(hue * config.hue_bins))
                hue_weights[hue_index] += saturation

        total = len(pixels)
        gray_ratio = gray_like / total
        saturated_ratio = saturated / total
        total_hue_weight = sum(hue_weights)
        dominant_hue_ratio = (max(hue_weights) / total_hue_weight) if total_hue_weight else 0.0

        is_bw = gray_ratio >= config.bw_ratio
        is_mostly_bw = (not is_bw) and gray_ratio >= config.mostly_bw_ratio
        colorful_enough = saturated_ratio >= config.minimum_saturated_ratio
        is_monochrome = (
            (not is_bw)
            and colorful_enough
            and dominant_hue_ratio >= config.monochrome_dominant_ratio
        )
        is_mostly_monochrome = (
            (not is_bw)
            and (not is_monochrome)
            and colorful_enough
            and dominant_hue_ratio >= config.mostly_monochrome_dominant_ratio
        )

        payload = {
            "is_bw": is_bw,
            "is_mostly_bw": is_mostly_bw,
            "is_monochrome": is_monochrome,
            "is_mostly_monochrome": is_mostly_monochrome,
            "gray_ratio": round(gray_ratio, 6),
            "saturated_ratio": round(saturated_ratio, 6),
            "dominant_hue_ratio": round(dominant_hue_ratio, 6),
            "sample_width": image.width,
            "sample_height": image.height,
            "original_width": original_width,
            "original_height": original_height,
            "config": {
                "sample_longest_side": config.sample_longest_side,
                "bw_channel_delta": config.bw_channel_delta,
                "bw_ratio": config.bw_ratio,
                "mostly_bw_ratio": config.mostly_bw_ratio,
                "saturation_floor": config.saturation_floor,
                "minimum_saturated_ratio": config.minimum_saturated_ratio,
                "monochrome_dominant_ratio": config.monochrome_dominant_ratio,
                "mostly_monochrome_dominant_ratio": config.mostly_monochrome_dominant_ratio,
                "hue_bins": config.hue_bins,
            },
        }
        return _Result(target.sha512, payload)
