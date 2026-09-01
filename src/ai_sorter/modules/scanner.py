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
    scanned: int
    saved: int
    skipped: int
    failed: int
    total: int
    current_discovery_path: str | None = None
    last_completed_path: str | None = None


@dataclass(frozen=True, slots=True)
class ScanSummary:
    execution_id: int
    discovered: int
    processed: int
    scanned: int
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
    """Discover supported files and synchronize their filesystem identity into SQLite."""

    module_id = "scanner"
    module_version = "0.4.1"

    def __init__(
        self,
        database: Database,
        worker_count: int = 0,
        db_batch_size: int = 1000,
        queue_multiplier: int = 8,
        lookup_batch_size: int = 500,
    ) -> None:
        self.database = database
        self.worker_count = max(0, worker_count)
        self.db_batch_size = max(100, db_batch_size)
        self.queue_multiplier = max(2, queue_multiplier)
        self.lookup_batch_size = max(100, min(500, lookup_batch_size))
        self._cancel_event = threading.Event()
        self._executor: ThreadPoolExecutor | None = None

    def cancel(self) -> None:
        self._cancel_event.set()

    def scan(self, root: Path, progress_callback: ProgressCallback | None = None) -> ScanSummary:
        root = root.resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"Folder skanowania nie istnieje lub nie jest katalogiem: {root}")

        self._cancel_event.clear()
        self.database.register_module(ModuleRecord(self.module_id, "Scanner", self.module_version, True))
        store = ScannerStore(self.database)
        store.begin_scan()

        started_at = datetime.now(timezone.utc)
        execution_id = self.database.start_module_execution(self.module_id, started_at)
        started_perf = time.perf_counter()
        discovery_start = time.perf_counter()
        discovery_seconds = 0.0
        hash_seconds = 0.0
        database_seconds = 0.0

        discovered = processed = scanned = saved = skipped = failed = missing = 0
        cancelled = False
        status = "FAILED"
        workers = self.worker_count or max(1, min(16, os.cpu_count() or 4))
        max_pending = max(workers * self.queue_multiplier, 32)
        pending: dict[Future[_HashedFile], _FileCandidate] = {}
        save_batch_files: list[FileRecord] = []
        save_batch_locations: list[FileLocationRecord] = []
        touch_batch: list[tuple[str, int, datetime]] = []
        current_discovery_path: str | None = None
        last_completed_path: str | None = None

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

        def emit() -> None:
            self._emit(progress_callback, discovered, processed, scanned, saved, skipped, failed,
                       discovered, current_discovery_path, last_completed_path)

        def persist_completed(done: set[Future[_HashedFile]]) -> None:
            nonlocal processed, scanned, saved, failed, hash_seconds, last_completed_path
            for future in done:
                candidate = pending.pop(future)
                processed += 1
                try:
                    result = future.result()
                    scanned += 1
                    hash_seconds += result.hash_seconds
                    last_completed_path = str(candidate.path)
                    save_batch_files.append(FileRecord(result.sha512, result.candidate.size,
                                                       None, None, result.candidate.modified_at, None, "ACTIVE"))
                    save_batch_locations.append(FileLocationRecord(result.sha512, str(result.candidate.path),
                                                                   result.candidate.size, result.candidate.modified_at,
                                                                   "ACTIVE", execution_id))
                    saved += 1
                except Exception:
                    failed += 1
                    last_completed_path = str(candidate.path)
                emit()

        def process_candidate_batch(candidates: list[_FileCandidate]) -> None:
            nonlocal processed, skipped, database_seconds, current_discovery_path
            if not candidates:
                return
            lookup_start = time.perf_counter()
            known = store.lookup_locations([str(candidate.path) for candidate in candidates])
            database_seconds += time.perf_counter() - lookup_start
            for candidate in candidates:
                current_discovery_path = str(candidate.path)
                if self._can_reuse_hash(known.get(str(candidate.path)), candidate):
                    touch_batch.append((str(candidate.path), candidate.size, candidate.modified_at))
                    skipped += 1
                    processed += 1
                    if len(touch_batch) >= self.db_batch_size:
                        flush_batches()
                    emit()
                    continue
                while len(pending) >= max_pending and not self._cancel_event.is_set():
                    done, _ = wait(pending, return_when=FIRST_COMPLETED)
                    persist_completed(done)
                    if len(save_batch_files) >= self.db_batch_size:
                        flush_batches()
                if self._cancel_event.is_set():
                    return
                if self._executor is None:
                    raise RuntimeError("Scanner worker pool is not available.")
                pending[self._executor.submit(self._hash_file, candidate)] = candidate

        try:
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="scanner") as executor:
                self._executor = executor
                candidate_batch: list[_FileCandidate] = []
                for candidate in self._discover(root):
                    discovered += 1
                    candidate_batch.append(candidate)
                    if len(candidate_batch) >= self.lookup_batch_size:
                        process_candidate_batch(candidate_batch)
                        candidate_batch.clear()
                    if self._cancel_event.is_set():
                        cancelled = True
                        break
                if not self._cancel_event.is_set():
                    process_candidate_batch(candidate_batch)
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
            self._executor = None
            flush_batches()
            self.database.finish_module_execution(ModuleExecutionRecord(
                execution_id, self.module_id, started_at, status,
                processed, saved + skipped, failed
            ))

        return ScanSummary(execution_id, discovered, processed, scanned, saved, skipped, failed, missing,
                           cancelled, time.perf_counter() - started_perf, discovery_seconds, hash_seconds, database_seconds)

    def _discover(self, root: Path) -> Iterable[_FileCandidate]:
        stack = [root]
        while stack and not self._cancel_event.is_set():
            current = stack.pop()
            try:
                with os.scandir(current) as iterator:
                    entries = sorted(iterator, key=lambda entry: entry.name.casefold())
                directories: list[Path] = []
                for entry in entries:
                    if self._cancel_event.is_set():
                        return
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            directories.append(Path(entry.path))
                            continue
                        if not entry.is_file(follow_symlinks=False):
                            continue
                        path = Path(entry.path).resolve()
                        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                            continue
                        stat = entry.stat(follow_symlinks=False)
                        yield _FileCandidate(path, stat.st_size,
                                             datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc))
                    except OSError:
                        continue
                stack.extend(reversed(directories))
            except OSError:
                continue

    @staticmethod
    def _can_reuse_hash(location: FileLocationRecord | None, candidate: _FileCandidate) -> bool:
        return bool(location and location.location_status == "ACTIVE"
                    and location.file_size == candidate.size
                    and location.modified_at == candidate.modified_at)

    @staticmethod
    def _hash_file(candidate: _FileCandidate) -> _HashedFile:
        started = time.perf_counter()
        digest = hashlib.sha512()
        with candidate.path.open("rb", buffering=1024 * 1024) as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return _HashedFile(candidate, digest.hexdigest(), time.perf_counter() - started)

    @staticmethod
    def _emit(callback: ProgressCallback | None, discovered: int, processed: int, scanned: int,
              saved: int, skipped: int, failed: int, total: int,
              current_discovery_path: str | None, last_completed_path: str | None) -> None:
        if callback:
            callback(ScanProgress(discovered, processed, scanned, saved, skipped, failed,
                                  max(0, total), current_discovery_path, last_completed_path))
