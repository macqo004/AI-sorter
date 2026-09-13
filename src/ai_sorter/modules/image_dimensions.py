"""Cheap image dimension extraction for canonical file identities."""

from __future__ import annotations

import os
import struct
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
    module_version = "0.2.0"

    def __init__(self, database: Database, root: Path | None = None, worker_count: int = 0, batch_size: int = 512) -> None:
        self.database = database
        self.root = root.resolve() if root is not None else None
        self.worker_count = worker_count or max(1, min(8, (os.cpu_count() or 4) // 2 or 1))
        self.batch_size = max(64, batch_size)
        self._cancel_event = threading.Event()
        self._last_progress_at = 0.0

    def cancel(self) -> None:
        self._cancel_event.set()

    def run(self, progress_callback: ProgressCallback | None = None) -> DimensionSummary:
        started_at = datetime.now(timezone.utc)
        started_perf = time.perf_counter()
        self._cancel_event.clear()
        self._last_progress_at = 0.0
        self.database.register_module(ModuleRecord(self.module_id, "Image Dimensions", self.module_version, True))
        execution_id = self.database.start_module_execution(self.module_id, started_at)

        total = self._count_targets()
        considered = total
        processed = updated = skipped = failed = 0
        cancelled = False
        status = "FAILED"
        pending: dict[Future[_Result], _Target] = {}
        result_batch: list[_Result] = []

        def emit(current_path: str | None = None, force: bool = False) -> None:
            nonlocal self
            if progress_callback is None:
                return
            now = time.perf_counter()
            if not force and now - self._last_progress_at < 0.2 and processed < total:
                return
            self._last_progress_at = now
            progress_callback(DimensionProgress(considered, processed, updated, skipped, failed, total, current_path))

        try:
            with ThreadPoolExecutor(max_workers=self.worker_count, thread_name_prefix="dimensions") as executor:
                for target in self._targets():
                    if self._cancel_event.is_set():
                        cancelled = True
                        break
                    pending[executor.submit(self._read_dimensions, target)] = target
                    if len(pending) >= self.worker_count * 8:
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
            emit(None, force=True)
        except DatabaseError:
            status = "FAILED"
            raise
        finally:
            self.database.finish_module_execution(ModuleExecutionRecord(
                execution_id, self.module_id, started_at, status, processed, updated, failed
            ))

        return DimensionSummary(
            execution_id, considered, processed, updated, skipped, failed, cancelled,
            time.perf_counter() - started_perf,
        )

    def _root_filter(self) -> tuple[str, str] | None:
        if self.root is None:
            return None
        root_text = str(self.root).rstrip("\\/")
        return root_text, root_text + "\\%"

    def _count_targets(self) -> int:
        connection = self.database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        root_filter = self._root_filter()
        if root_filter is None:
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
        else:
            root_text, pattern = root_filter
            row = connection.execute(
                """
                SELECT COUNT(DISTINCT f.sha512) AS count
                FROM file_record AS f
                JOIN file_location AS fl ON fl.sha512 = f.sha512 AND fl.location_status = 'ACTIVE'
                WHERE f.status = 'ACTIVE'
                  AND (f.width_px IS NULL OR f.height_px IS NULL)
                  AND (fl.absolute_path = ? OR fl.absolute_path LIKE ?)
                """,
                (root_text, pattern),
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
                FROM file_record AS f
                JOIN file_location AS fl
                  ON fl.sha512 = f.sha512 AND fl.location_status = 'ACTIVE'
                WHERE f.status = 'ACTIVE'
                  AND (f.width_px IS NULL OR f.height_px IS NULL)
                GROUP BY f.sha512
                ORDER BY f.sha512
                """
            )
        else:
            root_text, pattern = root_filter
            cursor = connection.execute(
                """
                SELECT f.sha512, MIN(fl.absolute_path) AS absolute_path
                FROM file_record AS f
                JOIN file_location AS fl
                  ON fl.sha512 = f.sha512 AND fl.location_status = 'ACTIVE'
                WHERE f.status = 'ACTIVE'
                  AND (f.width_px IS NULL OR f.height_px IS NULL)
                  AND (fl.absolute_path = ? OR fl.absolute_path LIKE ?)
                GROUP BY f.sha512
                ORDER BY f.sha512
                """,
                (root_text, pattern),
            )
        for row in cursor:
            yield _Target(str(row["sha512"]), Path(str(row["absolute_path"])))

    @staticmethod
    def _read_dimensions(target: _Target) -> _Result:
        width, height = ImageDimensions._read_dimensions_fast(target.path)
        if width <= 0 or height <= 0:
            raise ValueError("Image has invalid dimensions")
        return _Result(target.sha512, width, height)

    @staticmethod
    def _read_dimensions_fast(path: Path) -> tuple[int, int]:
        """Read dimensions from a tiny header window; fall back to Pillow only for uncommon formats."""
        with path.open("rb", buffering=0) as handle:
            header = handle.read(64)

        # PNG: signature + IHDR width/height.
        if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
            return struct.unpack(">II", header[16:24])

        # GIF: logical screen descriptor width/height, little endian.
        if header[:6] in (b"GIF87a", b"GIF89a") and len(header) >= 10:
            return struct.unpack("<HH", header[6:10])

        # BMP: DIB header variants. Width/height are little endian signed for common BMP/DIB headers.
        if header[:2] == b"BM" and len(header) >= 26:
            dib_size = struct.unpack("<I", header[14:18])[0]
            if dib_size >= 40:
                width = struct.unpack("<i", header[18:22])[0]
                height = abs(struct.unpack("<i", header[22:26])[0])
                return width, height

        # WEBP: RIFF + WEBP container. VP8X stores dimensions directly.
        if header[:4] == b"RIFF" and header[8:12] == b"WEBP" and len(header) >= 30:
            chunk = header[12:16]
            if chunk == b"VP8X" and len(header) >= 30:
                width = 1 + int.from_bytes(header[24:27], "little")
                height = 1 + int.from_bytes(header[27:30], "little")
                return width, height
            if chunk == b"VP8 " and len(header) >= 30:
                marker = header.find(b"\x9d\x01\x2a", 20, 64)
                if marker >= 0 and marker + 7 <= len(header):
                    width = int.from_bytes(header[marker + 3:marker + 5], "little") & 0x3FFF
                    height = int.from_bytes(header[marker + 5:marker + 7], "little") & 0x3FFF
                    return width, height

        # JPEG requires scanning markers until SOF; Pillow remains a safe fallback.
        if header[:2] == b"\xff\xd8":
            with path.open("rb", buffering=0) as handle:
                handle.read(2)
                while True:
                    marker_prefix = handle.read(1)
                    if not marker_prefix:
                        break
                    if marker_prefix != b"\xff":
                        continue
                    marker = handle.read(1)
                    while marker == b"\xff":
                        marker = handle.read(1)
                    if not marker or marker in (b"\xd8", b"\xd9"):
                        continue
                    if marker == b"\xda":
                        break
                    length_data = handle.read(2)
                    if len(length_data) != 2:
                        break
                    segment_length = struct.unpack(">H", length_data)[0]
                    if segment_length < 2:
                        break
                    if marker[0] in (
                        0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                        0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
                    ):
                        dimensions = handle.read(5)
                        if len(dimensions) == 5:
                            height, width = struct.unpack(">HH", dimensions[1:5])
                            return width, height
                        break
                    handle.seek(segment_length - 2, os.SEEK_CUR)

        # TIFF/other uncommon formats: Pillow is the fallback, not the hot path.
        with Image.open(path) as image:
            return int(image.width), int(image.height)

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
