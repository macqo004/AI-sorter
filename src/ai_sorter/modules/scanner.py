"""Filesystem Scanner module."""

from __future__ import annotations

import hashlib
import os
import threading
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
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


@dataclass(frozen=True, slots=True)
class _FileCandidate:
    path: Path
    size: int
    modified_at: datetime


@dataclass(frozen=True, slots=True)
class _HashedFile:
    candidate: _FileCandidate
    sha512: str


class Scanner:
    """Discover supported files and synchronize filesystem identity into SQLite."""

    module_id = "scanner"
    module_version = "0.1.0"

    def __init__(self, database: Database, worker_count: int = 0) -> None:
        self.database = database
        self.worker_count = max(0, worker_count)
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
        discovered = processed = saved = skipped = failed = missing = 0
        cancelled = False
        status = "FAILED"
        workers = self.worker_count or max(1, min(16, os.cpu_count() or 4))

        try:
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="scanner") as executor:
                pending: dict[Future[_HashedFile], _FileCandidate] = {}
                max_pending = max(4, workers * 4)

                for candidate in self._discover(root):
                    if self._cancel_event.is_set():
                        cancelled = True
                        break
                    discovered += 1

                    if self._can_reuse_hash(store, candidate):
                        try:
                            store.touch_location(str(candidate.path), candidate.size, candidate.modified_at, execution_id)
                            skipped += 1
                        except Exception:
                            failed += 1
                        processed += 1
                        self._emit(progress_callback, discovered, processed, saved, skipped, failed, -1, str(candidate.path))
                        continue

                    pending[executor.submit(self._hash_file, candidate)] = candidate
                    if len(pending) >= max_pending:
                        processed, saved, failed = self._drain_one_batch(
                            pending, store, execution_id, processed, saved, skipped, failed, progress_callback, discovered
                        )

                while pending:
                    processed, saved, failed = self._drain_one_batch(
                        pending, store, execution_id, processed, saved, skipped, failed, progress_callback, discovered
                    )

            cancelled = cancelled or self._cancel_event.is_set()
            if not cancelled:
                missing = store.mark_missing_under_root(root)
            status = "CANCELLED" if cancelled else ("FAILED" if failed and saved + skipped == 0 else "COMPLETED")
        finally:
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

        return ScanSummary(execution_id, discovered, processed, saved, skipped, failed, missing, cancelled)

    def _drain_one_batch(
        self,
        pending: dict[Future[_HashedFile], _FileCandidate],
        store: ScannerStore,
        execution_id: int,
        processed: int,
        saved: int,
        skipped: int,
        failed: int,
        progress_callback: ProgressCallback | None,
        discovered: int,
    ) -> tuple[int, int, int]:
        for future in as_completed(list(pending)):
            candidate = pending.pop(future)
            processed += 1
            try:
                result = future.result()
                self.database.upsert_file(
                    FileRecord(
                        sha512=result.sha512,
                        size_bytes=result.candidate.size,
                        modified_at=result.candidate.modified_at,
                        created_at=None,
                        status="ACTIVE",
                    )
                )
                store.persist_location(
                    FileLocationRecord(
                        sha512=result.sha512,
                        absolute_path=str(result.candidate.path),
                        file_size=result.candidate.size,
                        modified_at=result.candidate.modified_at,
                        location_status="ACTIVE",
                    ),
                    execution_id,
                )
                saved += 1
            except Exception:
                failed += 1
            self._emit(progress_callback, discovered, processed, saved, skipped, failed, -1, str(candidate.path))
        return processed, saved, failed

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
        digest = hashlib.sha512()
        with candidate.path.open("rb", buffering=1024 * 1024) as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return _HashedFile(candidate, digest.hexdigest())

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
