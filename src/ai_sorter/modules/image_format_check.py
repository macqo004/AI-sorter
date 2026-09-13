"""Cheap detection of an image's real format versus its filename extension."""
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

ProgressCallback = Callable[["FormatProgress"], None]

SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".pns"})
EXPECTED_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
    ".gif": "GIF",
    ".bmp": "BMP",
    ".pns": "PNG",
}
MIME_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
    "BMP": "image/bmp",
}


@dataclass(frozen=True, slots=True)
class FormatProgress:
    considered: int
    processed: int
    matches: int
    mismatches: int
    failed: int
    total: int
    current_path: str | None = None


@dataclass(frozen=True, slots=True)
class FormatSummary:
    execution_id: int
    considered: int
    processed: int
    matches: int
    mismatches: int
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
    extension: str
    detected_format: str
    mime_type: str | None
    matches: bool


class ImageFormatCheck:
    """Compare declared image extensions with the format reported by Pillow."""

    module_id = "image_format_check"
    module_version = "0.1.0"
    result_key = "image_format_check"

    def __init__(self, database: Database, root: Path | None = None, worker_count: int = 0, batch_size: int = 256) -> None:
        self.database = database
        self.root = root.resolve() if root is not None else None
        self.worker_count = worker_count or max(1, min(8, (os.cpu_count() or 4) // 2 or 1))
        self.batch_size = max(32, batch_size)
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def run(self, progress_callback: ProgressCallback | None = None) -> FormatSummary:
        started_at = datetime.now(timezone.utc)
        started_perf = time.perf_counter()
        self._cancel_event.clear()
        self.database.register_module(ModuleRecord(self.module_id, "Image Format / Extension Check", self.module_version, True))
        execution_id = self.database.start_module_execution(self.module_id, started_at)

        total = self._count_targets()
        considered = processed = matches = mismatches = failed = 0
        cancelled = False
        status = "FAILED"
        pending: dict[Future[_Result], _Target] = {}
        result_batch: list[_Result] = []

        def emit(path: str | None = None) -> None:
            if progress_callback:
                progress_callback(FormatProgress(considered, processed, matches, mismatches, failed, total, path))

        try:
            with ThreadPoolExecutor(max_workers=self.worker_count, thread_name_prefix="format-check") as executor:
                for target in self._targets():
                    considered += 1
                    if self._cancel_event.is_set():
                        cancelled = True
                        break
                    pending[executor.submit(self._detect, target)] = target
                    if len(pending) >= self.worker_count * 4:
                        done, _ = wait(pending, return_when=FIRST_COMPLETED)
                        for future in done:
                            item = pending.pop(future)
                            processed += 1
                            try:
                                result = future.result()
                                result_batch.append(result)
                                if result.matches:
                                    matches += 1
                                else:
                                    mismatches += 1
                            except Exception:
                                failed += 1
                            emit(str(item.path))
                        if len(result_batch) >= self.batch_size:
                            self._persist_batch(result_batch, execution_id)
                            result_batch.clear()

                while pending:
                    done, _ = wait(pending, return_when=FIRST_COMPLETED)
                    for future in done:
                        item = pending.pop(future)
                        processed += 1
                        try:
                            result = future.result()
                            result_batch.append(result)
                            if result.matches:
                                matches += 1
                            else:
                                mismatches += 1
                        except Exception:
                            failed += 1
                        emit(str(item.path))
                    if len(result_batch) >= self.batch_size:
                        self._persist_batch(result_batch, execution_id)
                        result_batch.clear()

                if result_batch:
                    self._persist_batch(result_batch, execution_id)

            cancelled = cancelled or self._cancel_event.is_set()
            status = "CANCELLED" if cancelled else ("COMPLETED_WITH_WARNINGS" if failed else "COMPLETED")
        except DatabaseError:
            status = "FAILED"
            raise
        finally:
            self.database.finish_module_execution(
                ModuleExecutionRecord(execution_id, self.module_id, started_at, status, processed, processed - failed, failed)
            )

        return FormatSummary(execution_id, considered, processed, matches, mismatches, failed, cancelled, time.perf_counter() - started_perf)

    def _root_filter(self) -> tuple[str, str] | None:
        if self.root is None:
            return None
        root = str(self.root).rstrip("\\/")
        return root, root + "\\%"

    def _count_targets(self) -> int:
        connection = self.database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        root_filter = self._root_filter()
        if root_filter is None:
            row = connection.execute(
                """
                SELECT COUNT(DISTINCT f.sha512) AS count
                FROM file_record AS f JOIN file_location AS fl ON fl.sha512=f.sha512 AND fl.location_status='ACTIVE'
                WHERE f.status='ACTIVE'
                """
            ).fetchone()
        else:
            root, pattern = root_filter
            row = connection.execute(
                """
                SELECT COUNT(DISTINCT f.sha512) AS count
                FROM file_record AS f JOIN file_location AS fl ON fl.sha512=f.sha512 AND fl.location_status='ACTIVE'
                WHERE f.status='ACTIVE' AND (fl.absolute_path=? OR fl.absolute_path LIKE ?)
                """, (root, pattern)
            ).fetchone()
        return int(row["count"]) if row else 0

    def _targets(self) -> Iterable[_Target]:
        connection = self.database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        root_filter = self._root_filter()
        if root_filter is None:
            cursor = connection.execute(
                """
                SELECT f.sha512, MIN(fl.absolute_path) AS absolute_path
                FROM file_record AS f JOIN file_location AS fl ON fl.sha512=f.sha512 AND fl.location_status='ACTIVE'
                WHERE f.status='ACTIVE' GROUP BY f.sha512 ORDER BY f.sha512
                """
            )
        else:
            root, pattern = root_filter
            cursor = connection.execute(
                """
                SELECT f.sha512, MIN(fl.absolute_path) AS absolute_path
                FROM file_record AS f JOIN file_location AS fl ON fl.sha512=f.sha512 AND fl.location_status='ACTIVE'
                WHERE f.status='ACTIVE' AND (fl.absolute_path=? OR fl.absolute_path LIKE ?)
                GROUP BY f.sha512 ORDER BY f.sha512
                """, (root, pattern)
            )
        for row in cursor:
            yield _Target(str(row["sha512"]), Path(str(row["absolute_path"])))

    @staticmethod
    def _detect(target: _Target) -> _Result:
        extension = target.path.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported image extension: {target.path}")
        with Image.open(target.path) as image:
            detected = (image.format or "UNKNOWN").upper()
        expected = EXPECTED_FORMATS[extension]
        return _Result(target.sha512, extension, detected, MIME_TYPES.get(detected), detected == expected)

    def _persist_batch(self, results: list[_Result], execution_id: int) -> None:
        if not results:
            return
        try:
            import json
            with self.database.transaction() as connection:
                connection.executemany(
                    """
                    INSERT INTO analysis_result (sha512, module_id, result_key, confidence, payload_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(sha512, module_id, result_key) DO UPDATE SET
                        confidence=excluded.confidence, payload_json=excluded.payload_json, updated_at=excluded.updated_at
                    """,
                    [(
                        r.sha512, self.module_id, self.result_key, 1.0,
                        json.dumps({"extension": r.extension, "detected_format": r.detected_format,
                                    "mime_type": r.mime_type, "matches": r.matches,
                                    "execution_id": execution_id, "module_version": self.module_version},
                                   ensure_ascii=False, sort_keys=True)
                    ) for r in results]
                )
        except Exception as exc:
            raise DatabaseError("Nie udało się zapisać wyników sprawdzania formatów obrazów.") from exc
