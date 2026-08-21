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

from ..core.database import Database, DatabaseError
from ..core.models import FileLocationRecord, FileRecord

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
    """Discover supported files and synchronize their filesystem identity into SQLite."""

    module_id = "scanner"
    module_version = "0.1.0"

    def __init__(self, database: Database, worker_count: int = 0) -> None:
        self.database = database
        self.worker_count = max(0, worker_count)
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """Request cancellation after the currently running file operations finish."""
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
            __import__("ai_sorter.core.models", fromlist=["ModuleRecord"]).ModuleRecord(
                module_id=self.module_id,
                display_name="Scanner",
                module_version=self.module_version,
                enabled=True,
            )
        )

        started_at = datetime.now(timezone.utc)
        execution_id = self.database.start_module_execution(self.module_id, started_at)

        discovered = 0
        processed = 0
        saved = 0
        skipped = 0
        failed = 0
        missing = 0

        try:
            candidates = list(self._discover(root))
            discovered = len(candidates)
            self._emit(progress_callback, discovered, processed, saved, skipped, failed, discovered)

            workers = self.worker_count or max(1, min(16, (os.cpu_count() or 4)))
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="scanner") as executor:
                futures: dict[Future[_HashedFile], _FileCandidate] = {}
                for candidate in candidates:
                    if self._cancel_event.is_set():
                        break
                    if self._can_reuse_hash(candidate):
                        try:
                            self.database.touch_file_location(candidate.path, candidate.size, candidate.modified_at, execution_id)
                            skipped += 1
                        except DatabaseError:
                            failed += 1
                        processed += 1
                        self._emit(progress_callback, discovered, processed, saved, skipped, failed, discovered, str(candidate.path))
                        continue
                    future = executor.submit(self._hash_file, candidate)
                    futures[future] = candidate

                for future in as_completed(futures):
                    candidate = futures[future]
                    if self._cancel_event.is_set():
                        continue
                    processed += 1
                    try:
                        result = future.result()
                        self._persist_hashed(result, execution_id)
                        saved += 1
                    except Exception:
                        failed += 1
                    self._emit(progress_callback, discovered, processed, saved, skipped, failed, discovered, str(candidate.path))

            if not self._cancel_event.is_set():
                missing = self.database.mark_unseen_locations_missing(root, execution_id)

            cancelled = self._cancel_event.is_set()
            status = "CANCELLED" if cancelled else ("FAILED" if failed and failed == processed else "COMPLETED")
        except Exception:
            cancelled = self._cancel_event.is_set()
            status = "CANCELLED" if cancelled else "FAILED"
            raise
        finally:
            self.database.finish_module_execution(
                __import__("ai_sorter.core.models", fromlist=["ModuleExecutionRecord"]).ModuleExecutionRecord(
                    execution_id=execution_id,
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
                            path = Path(entry.path)
                            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                                continue
                            stat = entry.stat(follow_symlinks=False)
                            yield _FileCandidate(
                                path=path.resolve(),
                                size=stat.st_size,
                                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                            )
                        except OSError:
                            continue
            except OSError:
                continue

    def _can_reuse_hash(self, candidate: _FileCandidate) -> bool:
        location = self.database.get_file_location(str(candidate.path))
        if location is None or location.location_status != "ACTIVE":
            return False
        return location.file_size == candidate.size and location.modified_at == candidate.modified_at

    @staticmethod
    def _hash_file(candidate: _FileCandidate) -> _HashedFile:
        digest = hashlib.sha512()
        with candidate.path.open("rb", buffering=1024 * 1024) as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return _HashedFile(candidate=candidate, sha512=digest.hexdigest())

    def _persist_hashed(self, result: _HashedFile, execution_id: int) -> None:
        self.database.upsert_file(
            FileRecord(
                sha512=result.sha512,
                size_bytes=result.candidate.size,
                modified_at=result.candidate.modified_at,
                created_at=None,
                status="ACTIVE",
            )
        )
        self.database.upsert_file_location(
            FileLocationRecord(
                sha512=result.sha512,
                absolute_path=str(result.candidate.path),
                file_size=result.candidate.size,
                modified_at=result.candidate.modified_at,
                location_status="ACTIVE",
                last_seen_execution_id=execution_id,
            )
        )

    @staticmethod
    def _emit(
        callback: ProgressCallback | None,
        discovered: int,
        processed: int,
        saved: int,
        skipped: int,
        failed: int,
        total: int,
        current_path: str | None = None,
    ) -> None:
        if callback is not None:
            callback(ScanProgress(discovered, processed, saved, skipped, failed, total, current_path))
