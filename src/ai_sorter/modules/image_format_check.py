"""Cheap detection of an image's real format versus its filename extension."""
from __future__ import annotations

import json
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

ProgressCallback = Callable[["FormatProgress"], None]

SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".pns"})
EXPECTED_FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP", ".gif": "GIF", ".bmp": "BMP", ".pns": "PNG"}
CANONICAL_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "GIF": ".gif", "BMP": ".bmp"}
MIME_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "GIF": "image/gif", "BMP": "image/bmp"}


@dataclass(frozen=True, slots=True)
class FormatProgress:
    considered: int
    processed: int
    skipped: int
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
    skipped: int
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
    result_key: str
    extension: str
    detected_format: str
    mime_type: str | None
    canonical_extension: str | None
    matches: bool


class ImageFormatCheck:
    """Compare declared image extensions with the real on-disk format."""

    module_id = "image_format_check"
    module_version = "0.1.4"
    result_key_prefix = "image_format_check:"

    def __init__(self, database: Database, root: Path | None = None, worker_count: int = 0, batch_size: int = 512) -> None:
        self.database = database
        self.root = root.resolve() if root is not None else None
        self.worker_count = worker_count or max(1, min(12, os.cpu_count() or 4))
        self.batch_size = max(64, batch_size)
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    @staticmethod
    def _extension_filter_sql(alias: str = "file_location") -> str:
        return " OR ".join(f"lower({alias}.absolute_path) LIKE ?" for _ in sorted(SUPPORTED_EXTENSIONS))

    @staticmethod
    def _extension_params() -> tuple[str, ...]:
        return tuple(f"%{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))

    @classmethod
    def _checked_result_sql(cls) -> tuple[str, tuple[str, ...]]:
        parts: list[str] = []
        params: list[str] = []
        for extension in sorted(SUPPORTED_EXTENSIONS):
            parts.append("(lower(fl.absolute_path) LIKE ? AND ar.result_key = ?)")
            params.extend((f"%{extension}", cls.result_key_prefix + extension))
        return " OR ".join(parts), tuple(params)

    def run(self, progress_callback: ProgressCallback | None = None) -> FormatSummary:
        started_at = datetime.now(timezone.utc)
        started_perf = time.perf_counter()
        self._cancel_event.clear()
        self.database.register_module(ModuleRecord(self.module_id, "Image Format / Extension Check", self.module_version, True))
        execution_id = self.database.start_module_execution(self.module_id, started_at)

        total, skipped = self._count_targets()
        considered = processed = matches = mismatches = failed = 0
        cancelled = False
        status = "FAILED"
        pending: dict[Future[_Result], _Target] = {}
        result_batch: list[_Result] = []
        last_emit = 0.0
        last_emit_count = 0

        def emit(path: str | None = None, *, force: bool = False) -> None:
            nonlocal last_emit, last_emit_count
            if progress_callback is None:
                return
            now = time.monotonic()
            if not force and processed - last_emit_count < 250 and now - last_emit < 0.2:
                return
            last_emit = now
            last_emit_count = processed
            progress_callback(FormatProgress(considered, processed, skipped, matches, mismatches, failed, total, path))

        def consume(done: set[Future[_Result]]) -> None:
            nonlocal processed, matches, mismatches, failed
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

        try:
            with ThreadPoolExecutor(max_workers=self.worker_count, thread_name_prefix="format-check") as executor:
                for target in self._targets():
                    considered += 1
                    if self._cancel_event.is_set():
                        cancelled = True
                        break
                    pending[executor.submit(self._detect, target)] = target
                    if len(pending) >= self.worker_count * 8:
                        done, _ = wait(pending, return_when=FIRST_COMPLETED)
                        consume(done)
                        if len(result_batch) >= self.batch_size:
                            self._persist_batch(result_batch, execution_id)
                            result_batch.clear()

                while pending:
                    done, _ = wait(pending, return_when=FIRST_COMPLETED)
                    consume(done)
                    if len(result_batch) >= self.batch_size:
                        self._persist_batch(result_batch, execution_id)
                        result_batch.clear()

                if result_batch:
                    self._persist_batch(result_batch, execution_id)

            cancelled = cancelled or self._cancel_event.is_set()
            status = "CANCELLED" if cancelled else ("COMPLETED_WITH_WARNINGS" if failed else "COMPLETED")
            emit(None, force=True)
        except DatabaseError:
            status = "FAILED"
            raise
        finally:
            self.database.finish_module_execution(ModuleExecutionRecord(execution_id, self.module_id, started_at, status, processed, processed - failed, failed))

        return FormatSummary(execution_id, considered, processed, skipped, matches, mismatches, failed, cancelled, time.perf_counter() - started_perf)

    def _root_filter(self) -> tuple[str, str] | None:
        if self.root is None:
            return None
        root = str(self.root).rstrip("\\/")
        return root, root + "\\%"

    def _count_targets(self) -> tuple[int, int]:
        connection = self.database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        extension_sql = self._extension_filter_sql("fl")
        extension_params = self._extension_params()
        checked_sql, checked_params = self._checked_result_sql()
        root_filter = self._root_filter()
        base_from = "FROM file_location AS fl"
        root_sql = ""
        root_params: tuple[str, ...] = ()
        if root_filter is not None:
            root, pattern = root_filter
            root_sql = " AND (fl.absolute_path=? OR fl.absolute_path LIKE ?)"
            root_params = (root, pattern)

        base_where = f"fl.location_status='ACTIVE' AND ({extension_sql}){root_sql}"
        row = connection.execute(
            f"SELECT COUNT(*) AS count {base_from} WHERE {base_where}",
            (*extension_params, *root_params),
        ).fetchone()
        all_count = int(row["count"]) if row else 0

        row = connection.execute(
            f"""
            SELECT COUNT(*) AS count
            {base_from}
            WHERE {base_where}
              AND NOT EXISTS (
                  SELECT 1
                  FROM analysis_result AS ar
                  WHERE ar.sha512 = fl.sha512
                    AND ar.module_id = ?
                    AND ({checked_sql})
              )
            """,
            (*extension_params, *root_params, self.module_id, *checked_params),
        ).fetchone()
        pending_count = int(row["count"]) if row else 0
        return pending_count, all_count - pending_count

    def _targets(self) -> Iterable[_Target]:
        connection = self.database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        extension_sql = self._extension_filter_sql("fl")
        extension_params = self._extension_params()
        checked_sql, checked_params = self._checked_result_sql()
        root_filter = self._root_filter()
        root_sql = ""
        root_params: tuple[str, ...] = ()
        if root_filter is not None:
            root, pattern = root_filter
            root_sql = " AND (fl.absolute_path=? OR fl.absolute_path LIKE ?)"
            root_params = (root, pattern)

        cursor = connection.execute(
            f"""
            SELECT fl.sha512, fl.absolute_path
            FROM file_location AS fl
            WHERE fl.location_status='ACTIVE'
              AND ({extension_sql})
              {root_sql}
              AND NOT EXISTS (
                  SELECT 1
                  FROM analysis_result AS ar
                  WHERE ar.sha512 = fl.sha512
                    AND ar.module_id = ?
                    AND ({checked_sql})
              )
            ORDER BY fl.absolute_path
            """,
            (*extension_params, *root_params, self.module_id, *checked_params),
        )
        for row in cursor:
            yield _Target(str(row["sha512"]), Path(str(row["absolute_path"])))

    @staticmethod
    def _detect(target: _Target) -> _Result:
        extension = target.path.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported image extension: {target.path}")
        with target.path.open("rb") as stream:
            header = stream.read(32)
        detected = ImageFormatCheck._detect_signature(header)
        expected = EXPECTED_FORMATS[extension]
        canonical = CANONICAL_EXTENSIONS.get(detected)
        return _Result(target.sha512, ImageFormatCheck.result_key_prefix + extension, extension, detected, MIME_TYPES.get(detected), canonical, detected == expected)

    @staticmethod
    def _detect_signature(header: bytes) -> str:
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "PNG"
        if header.startswith(b"\xff\xd8\xff"):
            return "JPEG"
        if header.startswith((b"GIF87a", b"GIF89a")):
            return "GIF"
        if header.startswith(b"BM"):
            return "BMP"
        if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
            return "WEBP"
        return "UNKNOWN"

    def _persist_batch(self, results: list[_Result], execution_id: int) -> None:
        if not results:
            return
        try:
            with self.database.transaction() as connection:
                connection.executemany(
                    """
                    INSERT INTO analysis_result (sha512, module_id, result_key, confidence, payload_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(sha512, module_id, result_key) DO UPDATE SET
                        confidence=excluded.confidence, payload_json=excluded.payload_json, updated_at=excluded.updated_at
                    """,
                    [
                        (result.sha512, self.module_id, result.result_key, 1.0, json.dumps({
                            "extension": result.extension,
                            "detected_format": result.detected_format,
                            "mime_type": result.mime_type,
                            "canonical_extension": result.canonical_extension,
                            "matches": result.matches,
                            "execution_id": execution_id,
                            "module_version": self.module_version,
                        }, ensure_ascii=False, sort_keys=True))
                        for result in results
                    ],
                )
        except Exception as exc:
            raise DatabaseError("Nie udało się zapisać wyników sprawdzania formatów obrazów.") from exc
