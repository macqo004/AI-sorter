"""Filesystem Scanner module."""

from __future__ import annotations

import hashlib
import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from ..core.database import Database
from ..core.models import FileLocationRecord, FileRecord, ModuleExecutionRecord, ModuleRecord
from ..core.scanner_store import ScannerStore

SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".pns"})
ProgressCallback = Callable[["ScanProgress"], None]


@dataclass(frozen=True, slots=True)
class ScanProgress:
    discovered: int
    processed: int
    saved: int
    skipped: int
    failed: int
    total: int
    current_path: str | None = None


@dataclass(frozen=True, slots=True)
class ScanSummary:
    execution_id: int
    discovered: int
    processed: int
    saved: int
    skipped: int
    failed: int
    missing: int
    cancelled: bool
    elapsed_seconds: float
    discovery_seconds: float
    hash_seconds: float
    database_seconds: float


@dataclass(frozen=True, slots=True)
class _FileCandidate:
    path: Path
    size: int
    modified_at: datetime


@dataclass(frozen=True, slots=True)
class _HashedFile:
    candidate: _FileCandidate
    sha512: str
    hash_seconds: float


class Scanner:
    """Discover supported files and synchronize filesystem identity into SQLite."""

    module_id = "scanner"
    module_version = "0.2.0"

    def __init__(
        self,
        database: Database,
        worker_count: int = 0,
        db_batch_size: int = 1000,
        queue_multiplier: int = 8,
    ) -> None:
        self.database = database
        self.worker_count = max(0, worker_count)
        self.db_batch_size = max(100, db_batch_size)
        self.queue_multiplier = max(2, queue_multiplier)
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """Request cancellation after currently running file operations finish."""
        self._cancel_event.set()

    def scan(
        self,
        root: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> ScanSummary:
        root = root.resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"Folder skanowania nie istnieje lub nie jest katalogiem: {root}")

        self._cancel_event.clear()
        self.database.register_module(
            ModuleRecord(
                module_id=self.module_id,
                display_name="Scanner",
                module_version=self.module_version,
                enabled=True,
            )
        )
        store = ScannerStore(self.database)
        store.begin_scan()

        started_at = datetime.now(timezone.utc)
        execution_id = self.database.start_module_execution(self.module_id, started_at)
        started_perf = time.perf_counter()
        discovery_start = time.perf_counter()
        discovery_seconds = 0.0
        hash_seconds = 0.0
        database_seconds = 0.0

        discovered = processed = saved = skipped = failed = missing = 0
        cancelled = False
        status = "FAILED"
        workers = self.worker_count or max(1, min(16, os.cpu_count() or 4))
        max_pending = max(workers * self.queue_multiplier, 32)
        pending: dict[Future[_HashedFile], _FileCandidate] = {}
        save_batch_files: list[FileRecord] = []
        save_batch_locations: list[FileLocationRecord] = []
        touch_batch: list[tuple[str, int, datetime]] = []

        def flush_batches() -> None:
            nonlocal database_seconds
            if save_batch_files:
                db_start = time.perf_counter()
                store.persist_batch(save_batch_files, save_batch_locations, execution_id)
                database_seconds += time.perf_counter() - db_start
                save_batch_files.clear()
                save_batch_locations.clear()
            if touch_batch:
                db_start = time.perf_counter()
                store.touch_batch(touch_batch, execution_id)
                database_seconds += time.perf_counter() - db_start
                touch_batch.clear()

        def persist_completed(done: set[Future[_HashedFile]]) -> None:
            nonlocal processed, saved, failed, hash_seconds, database_seconds
            for future in done:
                candidate = pending.pop(future)
                processed += 1
                try:
                    result = future.result()
                    hash_seconds += result.hash_seconds
                    save_batch_files.append(
                        FileRecord(
                            sha512=result.sha512,
                            size_bytes=result.candidate.size,
                            modified_at=result.candidate.modified_at,
                            created_at=None,
                            status="ACTIVE",
                        )
                    )
                    save_batch_locations.append(
                        FileLocationRecord(
                            sha512=result.sha512,
                            absolute_path=str(result.candidate.path),
                            file_size=result.candidate.size,
                            modified_at=result.candidate.modified_at,
                            location_status="ACTIVE",
                            last_seen_execution_id=execution_id,
                        )
                    )
                    saved += 1
                    self._emit(progress_callback, discovered, processed, saved, skipped, failed, -1, str(candidate.path))
                except Exception:
                    failed += 1
                    self._emit(progress_callback, discovered, processed, saved, skipped, failed, -1, str(candidate.path))

        try:
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="scanner") as executor:
                for candidate in self._discover(root):
                    discovered += 1
                    if self._cancel_event.is_set():
                        cancelled = True
                        break

                    if self._can_reuse_hash(store, candidate):
                        touch_batch.append((str(candidate.path), candidate.size, candidate.modified_at))
                        skipped += 1
                        processed += 1
                        if len(touch_batch) >= self.db_batch_size:
                            flush_batches()
                        self._emit(progress_callback, discovered, processed, saved, skipped, failed, -1, str(candidate.path))
                    else:
                        while len(pending) >= max_pending and not self._cancel_event.is_set():
                            done, _ = wait(pending, return_when=FIRST_COMPLETED)
                            persist_completed(done)
                            if len(save_batch_files) >= self.db_batch_size:
                                flush_batches()

                        if self._cancel_event.is_set():
                            cancelled = True
                            break
                        pending[executor.submit(self._hash_file, candidate)] = candidate

                discovery_seconds = time.perf_counter() - discovery_start

                while pending:
                    done, _ = wait(pending, return_when=FIRST_COMPLETED)
                    persist_completed(done)
                    if len(save_batch_files) >= self.db_batch_size:
                        flush_batches()

                flush_batches()

            cancelled = cancelled or self._cancel_event.is_set()
            if not cancelled:
                db_start = time.perf_counter()
                missing = store.mark_missing_under_root(root)
                database_seconds += time.perf_counter() - db_start
            status = "CANCELLED" if cancelled else ("FAILED" if failed and saved + skipped == 0 else "COMPLETED")
        finally:
            flush_batches()
            self.database.finish_module_execution(
                ModuleExecutionRecord(
                    execution_id=execution_id,
                    module_id=self.module_id,
                    started_at=started_at,
                    status=status,
                    processed_count=processed,
                    success_count=saved + skipped,
                    failure_count=failed,
                )
            )

        return ScanSummary(
            execution_id=execution_id,
            discovered=discovered,
            processed=processed,
            saved=saved,
            skipped=skipped,
            failed=failed,
            missing=missing,
            cancelled=cancelled,
            elapsed_seconds=time.perf_counter() - started_perf,
            discovery_seconds=discovery_seconds,
            hash_seconds=hash_seconds,
            database_seconds=database_seconds,
        )

    def _discover(self, root: Path) -> Iterable[_FileCandidate]:
        stack = [root]
        while stack and not self._cancel_event.is_set():
            current = stack.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        if self._cancel_event.is_set():
                            return
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(Path(entry.path))
                                continue
                            if not entry.is_file(follow_symlinks=False):
                                continue
                            path = Path(entry.path).resolve()
                            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                                continue
                            stat = entry.stat(follow_symlinks=False)
                            yield _FileCandidate(
                                path=path,
                                size=stat.st_size,
                                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(microsecond=0),
                            )
                        except OSError:
                            continue
            except OSError:
                continue

    @staticmethod
    def _can_reuse_hash(store: ScannerStore, candidate: _FileCandidate) -> bool:
        location = store.get_file_location(str(candidate.path))
        return bool(
            location
            and location.location_status == "ACTIVE"
            and location.file_size == candidate.size
            and location.modified_at == candidate.modified_at
        )

    @staticmethod
    def _hash_file(candidate: _FileCandidate) -> _HashedFile:
        started = time.perf_counter()
        digest = hashlib.sha512()
        with candidate.path.open("rb", buffering=1024 * 1024) as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return _HashedFile(candidate, digest.hexdigest(), time.perf_counter() - started)

    @staticmethod
    def _emit(
        callback: ProgressCallback | None,
        discovered: int,
        processed: int,
        saved: int,
        skipped: int,
        failed: int,
        total: int,
        current_path: str | None,
    ) -> None:
        if callback:
            callback(ScanProgress(discovered, processed, saved, skipped, failed, total, current_path))
