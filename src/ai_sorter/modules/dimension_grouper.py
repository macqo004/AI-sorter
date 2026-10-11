"""Move image files into folders named after their pixel dimensions."""

from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image

from ..core.database import Database, DatabaseError
from ..core.models import ModuleExecutionRecord, ModuleRecord
from ..core.scanner_store import ScannerStore

SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".pns"})
GROUP_DIRECTORY_RE = re.compile(r"^\d+x\d+$")
BATCH_SIZE = 256

GroupingProgressCallback = Callable[["GroupingProgress"], None]


@dataclass(frozen=True, slots=True)
class GroupingProgress:
    processed: int
    total: int
    moved: int
    skipped: int
    failed: int
    current_path: str | None = None
    phase: str = "grouping"


@dataclass(frozen=True, slots=True)
class DimensionGroupingPlan:
    root: Path
    considered: int
    planned_moves: int
    unreadable: int
    destination_conflicts: int
    by_dimension: dict[str, int] = field(default_factory=dict)
    cancelled: bool = False


@dataclass(frozen=True, slots=True)
class DimensionGroupingSummary:
    execution_id: int
    considered: int
    moved: int
    skipped_existing: int
    failed: int
    unreadable: int
    database_updated: int
    database_conflicts_reconciled: int
    cancelled: bool
    elapsed_seconds: float
    by_dimension: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _Candidate:
    source: Path
    destination: Path
    width: int
    height: int


class DimensionGrouper:
    """Group supported images into root-level '<width>x<height>' folders.

    Planning does not change the filesystem. Execution moves files (never copies or
    overwrites them), and synchronizes successful path changes through ScannerStore.
    """

    module_id = "dimension_grouping"
    module_version = "1.0.0"

    def __init__(self, database: Database, root: Path, batch_size: int = BATCH_SIZE) -> None:
        self.database = database
        self.root = root.resolve()
        self.batch_size = max(1, int(batch_size))
        self._cancel_event = threading.Event()
        self._last_plan: DimensionGroupingPlan | None = None

    def cancel(self) -> None:
        """Request cancellation; the current safe batch is reconciled before stopping."""
        self._cancel_event.set()

    def plan(self, progress_callback: GroupingProgressCallback | None = None) -> DimensionGroupingPlan:
        """Inspect dimensions and estimate moves without creating folders or moving files."""
        if not self.root.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.root}")

        self._cancel_event.clear()
        considered = planned_moves = unreadable = destination_conflicts = processed = 0
        by_dimension: dict[str, int] = {}

        for source in self._iter_sources():
            if self._cancel_event.is_set():
                break
            considered += 1
            processed += 1
            try:
                width, height = self._read_dimensions(source)
            except Exception:
                unreadable += 1
                self._emit(progress_callback, processed, 0, 0, 0, unreadable, source, "planning")
                continue

            key = f"{width}x{height}"
            by_dimension[key] = by_dimension.get(key, 0) + 1
            destination = self.root / key / source.name
            if destination.exists():
                destination_conflicts += 1
            elif destination.resolve() != source.resolve():
                planned_moves += 1

            self._emit(progress_callback, processed, 0, planned_moves, 0, unreadable, source, "planning")

        result = DimensionGroupingPlan(
            root=self.root,
            considered=considered,
            planned_moves=planned_moves,
            unreadable=unreadable,
            destination_conflicts=destination_conflicts,
            by_dimension=dict(sorted(by_dimension.items(), key=lambda item: item[0])),
            cancelled=self._cancel_event.is_set(),
        )
        self._last_plan = result
        return result

    def execute(
        self,
        plan: DimensionGroupingPlan | None = None,
        progress_callback: GroupingProgressCallback | None = None,
    ) -> DimensionGroupingSummary:
        """Move eligible files in bounded batches and keep database paths synchronized."""
        if not self.root.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.root}")
        active_plan = plan or self._last_plan
        if active_plan is not None and active_plan.root != self.root:
            raise ValueError("The grouping plan belongs to a different root folder.")

        store = ScannerStore(self.database)
        started_at = datetime.now(timezone.utc)
        started_perf = time.perf_counter()
        self.database.register_module(
            ModuleRecord(self.module_id, "Dimension Grouping", self.module_version, True)
        )
        execution_id = self.database.start_module_execution(self.module_id, started_at)

        processed = moved = skipped_existing = failed = unreadable = 0
        database_updated = database_conflicts_reconciled = 0
        cancelled = False
        status = "FAILED"
        total = active_plan.considered if active_plan is not None else 0
        by_dimension: dict[str, int] = {}

        try:
            candidates: list[_Candidate] = []
            for source in self._iter_sources():
                if self._cancel_event.is_set():
                    cancelled = True
                    break
                processed += 1
                try:
                    width, height = self._read_dimensions(source)
                except Exception:
                    unreadable += 1
                    self._emit(progress_callback, processed, total, moved, skipped_existing, failed + unreadable,
                               source, "grouping")
                    continue

                dimension = f"{width}x{height}"
                by_dimension[dimension] = by_dimension.get(dimension, 0) + 1
                destination = self.root / dimension / source.name
                if destination.resolve() == source.resolve() or destination.exists():
                    skipped_existing += 1
                    self._emit(progress_callback, processed, total, moved, skipped_existing, failed + unreadable,
                               source, "grouping")
                    continue

                candidates.append(_Candidate(source, destination, width, height))
                if len(candidates) >= self.batch_size:
                    result = self._move_batch(candidates, store)
                    moved += result[0]
                    skipped_existing += result[1]
                    failed += result[2]
                    database_updated += result[3]
                    database_conflicts_reconciled += result[4]
                    candidates.clear()
                self._emit(progress_callback, processed, total, moved, skipped_existing, failed + unreadable,
                           source, "grouping")

            if candidates:
                result = self._move_batch(candidates, store)
                moved += result[0]
                skipped_existing += result[1]
                failed += result[2]
                database_updated += result[3]
                database_conflicts_reconciled += result[4]

            cancelled = cancelled or self._cancel_event.is_set()
            status = "CANCELLED" if cancelled else (
                "COMPLETED_WITH_WARNINGS" if failed or unreadable or skipped_existing else "COMPLETED"
            )
        except Exception:
            status = "FAILED"
            raise
        finally:
            self.database.finish_module_execution(
                ModuleExecutionRecord(
                    execution_id,
                    self.module_id,
                    started_at,
                    status,
                    processed,
                    moved,
                    failed + unreadable + skipped_existing,
                )
            )

        return DimensionGroupingSummary(
            execution_id=execution_id,
            considered=processed,
            moved=moved,
            skipped_existing=skipped_existing,
            failed=failed,
            unreadable=unreadable,
            database_updated=database_updated,
            database_conflicts_reconciled=database_conflicts_reconciled,
            cancelled=cancelled,
            elapsed_seconds=time.perf_counter() - started_perf,
            by_dimension=dict(sorted(by_dimension.items(), key=lambda item: item[0])),
        )

    def _move_batch(
        self, candidates: list[_Candidate], store: ScannerStore
    ) -> tuple[int, int, int, int, int]:
        """Move one bounded batch, then commit its path updates as one DB transaction."""
        if not candidates:
            return 0, 0, 0, 0, 0

        paths = [(item.source, item.destination) for item in candidates]
        try:
            prepared = store.prepare_renamed_locations(paths)
        except DatabaseError:
            # Retry individually so one ambiguous identity does not block unrelated files.
            prepared = {}
            safe_candidates: list[_Candidate] = []
            failed = 0
            for item in candidates:
                try:
                    prepared.update(store.prepare_renamed_locations([(item.source, item.destination)]))
                    safe_candidates.append(item)
                except DatabaseError:
                    failed += 1
            candidates = safe_candidates
            if not candidates:
                return 0, 0, failed, 0, 0

        executed: list[tuple[Path, Path]] = []
        skipped = failed_moves = 0
        for item in candidates:
            if self._cancel_event.is_set():
                break
            try:
                if not item.source.is_file():
                    skipped += 1
                    continue
                item.destination.parent.mkdir(parents=True, exist_ok=True)
                if item.destination.exists():
                    skipped += 1
                    continue
                item.source.rename(item.destination)
                executed.append((item.source, item.destination))
            except OSError:
                failed_moves += 1

        if not executed:
            return 0, skipped, failed_moves, 0, 0

        prepared_executed = {
            str(source.resolve()): prepared[str(source.resolve())]
            for source, _ in executed
            if str(source.resolve()) in prepared
        }
        try:
            database_updated, conflicts = store.update_renamed_locations_with_stats(
                executed,
                prepared=prepared_executed,
            )
        except Exception:
            # If DB reconciliation fails, try to restore files from this batch.
            for source, destination in reversed(executed):
                try:
                    if destination.exists() and not source.exists():
                        source.parent.mkdir(parents=True, exist_ok=True)
                        destination.rename(source)
                except OSError:
                    pass
            raise

        return len(executed), skipped, failed_moves, database_updated, conflicts

    def _iter_sources(self) -> Iterable[Path]:
        """Yield supported files, skipping existing root-level dimension folders."""
        for current_root, directories, filenames in os.walk(self.root, topdown=True, followlinks=False):
            current = Path(current_root)
            if current == self.root:
                directories[:] = [
                    name for name in directories
                    if not GROUP_DIRECTORY_RE.fullmatch(name)
                    and not (current / name).is_symlink()
                ]
            else:
                directories[:] = [name for name in directories if not (current / name).is_symlink()]
            directories.sort(key=str.casefold)
            filenames.sort(key=str.casefold)

            for name in filenames:
                path = current / name
                if path.suffix.lower() not in SUPPORTED_EXTENSIONS or path.is_symlink() or not path.is_file():
                    continue
                yield path.resolve()

    @staticmethod
    def _read_dimensions(path: Path) -> tuple[int, int]:
        with Image.open(path) as image:
            width, height = int(image.width), int(image.height)
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid dimensions in image: {path}")
        return width, height

    @staticmethod
    def _emit(
        callback: GroupingProgressCallback | None,
        processed: int,
        total: int,
        moved: int,
        skipped: int,
        failed: int,
        current_path: Path,
        phase: str,
    ) -> None:
        if callback is not None:
            callback(GroupingProgress(processed, total, moved, skipped, failed, str(current_path), phase))
