"""Cheap image dimension extraction for canonical file identities."""

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image

from ..core.database import Database, DatabaseError
from ..core.models import ModuleExecutionRecord, ModuleRecord

ProgressCallback = Callable[["DimensionProgress"], None]


@dataclass(frozen=True, slots=True)
class DimensionProgress:
    considered: int
    processed: int
    updated: int
    skipped: int
    failed: int
    total: int
    current_path: str | None = None


@dataclass(frozen=True, slots=True)
class DimensionSummary:
    execution_id: int
    considered: int
    processed: int
    updated: int
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
    width_px: int
    height_px: int


class ImageDimensions:
    """Populate missing width/height metadata without hashing image contents."""

    module_id = "image_dimensions"
    module_version = "0.1.3"

    def __init__(self, database: Database, worker_count: int = 0, batch_size: int = 256) -> None:
        self.database = database
        self.worker_count = worker_count or max(1, min(8, (os.cpu_count() or 4) // 2 or 1))
        self.batch_size = max(32, batch_size)
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def run(self, progress_callback: ProgressCallback | None = None) -> DimensionSummary:
        started_at = datetime.now(timezone.utc)
        started_perf = time.perf_counter()
        self._cancel_event.clear()
        self.database.register_module(ModuleRecord(self.module_id, "Image Dimensions", self.module_version, True))
        execution_id = self.database.start_module_execution(self.module_id, started_at)

        total = self._count_targets()
        considered = total
        processed = updated = skipped = failed = 0
        cancelled = False
        status = "FAILED"
        pending: dict[Future[_Result], _Target] = {}
        result_batch: list[_Result] = []

        def emit(current_path: str | None = None) -> None:
            if progress_callback:
                progress_callback(DimensionProgress(considered, processed, updated, skipped, failed, total, current_path))

        try:
            with ThreadPoolExecutor(max_workers=self.worker_count, thread_name_prefix="dimensions") as executor:
                for target in self._targets():
                    if self._cancel_event.is_set():
                        cancelled = True
                        break
                    pending[executor.submit(self._read_dimensions, target)] = target
                    if len(pending) >= self.worker_count * 4:
                        done, _ = wait(pending, return_when=FIRST_COMPLETED)
                        for future in done:
                            target_item = pending.pop(future)
                            processed += 1
                            try:
                                result_batch.append(future.result())
                            except Exception:
                                failed += 1
                            emit(str(target_item.path))
                        if len(result_batch) >= self.batch_size:
                            updated += self._persist_batch(result_batch)
                            result_batch.clear()

                while pending:
                    done, _ = wait(pending, return_when=FIRST_COMPLETED)
                    for future in done:
                        target_item = pending.pop(future)
                        processed += 1
                        try:
                            result_batch.append(future.result())
                        except Exception:
                            failed += 1
                        emit(str(target_item.path))
                    if len(result_batch) >= self.batch_size:
                        updated += self._persist_batch(result_batch)
                        result_batch.clear()

                if result_batch:
                    updated += self._persist_batch(result_batch)
                    result_batch.clear()

            cancelled = cancelled or self._cancel_event.is_set()
            status = "CANCELLED" if cancelled else ("COMPLETED_WITH_WARNINGS" if failed else "COMPLETED")
        except DatabaseError:
            status = "FAILED"
            raise
        finally:
            self.database.finish_module_execution(ModuleExecutionRecord(
                execution_id, self.module_id, started_at, status, processed, updated, failed
            ))

        return DimensionSummary(execution_id, considered, processed, updated, skipped, failed, cancelled,
                                time.perf_counter() - started_perf)

    def _count_targets(self) -> int:
        connection = self.database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        row = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM file_record AS f
            WHERE f.status = 'ACTIVE'
              AND (f.width_px IS NULL OR f.height_px IS NULL)
              AND EXISTS (
                  SELECT 1 FROM file_location AS fl
                  WHERE fl.sha512 = f.sha512 AND fl.location_status = 'ACTIVE'
              )
            """
        ).fetchone()
        return int(row["count"]) if row else 0

    def _targets(self) -> Iterable[_Target]:
        connection = self.database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        cursor = connection.execute(
            """
            SELECT f.sha512, fl.absolute_path
            FROM file_record AS f
            JOIN file_location AS fl
              ON fl.sha512 = f.sha512 AND fl.location_status = 'ACTIVE'
            WHERE f.status = 'ACTIVE'
              AND (f.width_px IS NULL OR f.height_px IS NULL)
            ORDER BY f.sha512, fl.absolute_path
            """
        )
        current_sha: str | None = None
        chosen_path: Path | None = None
        first_path: Path | None = None
        for row in cursor:
            sha = str(row["sha512"])
            path = Path(str(row["absolute_path"]))
            if sha != current_sha:
                if current_sha is not None:
                    yield _Target(current_sha, chosen_path or first_path or Path(""))
                current_sha = sha
                chosen_path = None
                first_path = path
            if chosen_path is None:
                try:
                    if path.is_file():
                        chosen_path = path
                except OSError:
                    pass
        if current_sha is not None:
            yield _Target(current_sha, chosen_path or first_path or Path(""))

    @staticmethod
    def _read_dimensions(target: _Target) -> _Result:
        with Image.open(target.path) as image:
            width, height = image.size
        if width <= 0 or height <= 0:
            raise ValueError("Image has invalid dimensions")
        return _Result(target.sha512, int(width), int(height))

    def _persist_batch(self, results: list[_Result]) -> int:
        if not results:
            return 0
        connection = self.database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        try:
            with self.database.transaction() as db:
                cursor = db.executemany(
                    """
                    UPDATE file_record
                    SET width_px = ?, height_px = ?
                    WHERE sha512 = ? AND (width_px IS NULL OR height_px IS NULL)
                    """,
                    [(r.width_px, r.height_px, r.sha512) for r in results],
                )
                return max(0, cursor.rowcount or 0)
        except Exception as exc:
            raise DatabaseError("Nie udało się zapisać wymiarów obrazów w bazie danych.") from exc
