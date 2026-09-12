"""Qt worker for planning and executing filename renames without blocking the GUI."""

from __future__ import annotations

import os
import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from ..core.database import DatabaseError
from ..renamer import RenameProposal, RenamerEngine
from ..core.scanner_store import ScannerStore


class RenamerWorker(QObject):
    """Run Renamer planning/execution on a worker thread."""

    planned = Signal(object)
    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(str)

    SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".pns"})
    PROGRESS_INTERVAL = 500
    PROGRESS_TIME_SECONDS = 0.15

    def __init__(self, database, root: Path, recursive: bool = True) -> None:
        super().__init__()
        self.database = database
        self.root = root
        self.recursive = recursive
        self.engine = RenamerEngine()
        self.proposals: list[RenameProposal] = []

    def _discover_files(self) -> list[Path]:
        """Collect supported files while keeping the GUI visibly alive."""
        root = self.root.resolve()
        if not root.is_dir():
            raise NotADirectoryError(f"Not a directory: {root}")

        discovered: list[Path] = []
        last_emit = time.perf_counter()
        for current, directories, filenames in os.walk(root):
            directories.sort(key=str.casefold)
            filenames.sort(key=str.casefold)
            current_path = Path(current)
            for filename in filenames:
                if Path(filename).suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                    continue
                discovered.append(current_path / filename)
                now = time.perf_counter()
                if (
                    len(discovered) % self.PROGRESS_INTERVAL == 0
                    or now - last_emit >= self.PROGRESS_TIME_SECONDS
                ):
                    self.progress.emit(
                        len(discovered),
                        0,
                        f"Renamer — discovering files: {len(discovered):,}",
                    )
                    last_emit = now

        discovered.sort(key=lambda path: str(path).casefold())
        self.progress.emit(
            len(discovered),
            0,
            f"Renamer — discovery complete: {len(discovered):,} files",
        )
        return discovered

    @Slot()
    def plan(self) -> None:
        try:
            files = self._discover_files()
            scanned = len(files)
            proposals: list[RenameProposal] = []
            skipped_missing: list[str] = []
            last_emit = time.perf_counter()

            self.progress.emit(0, scanned, "Renamer — planning…")
            for index, source in enumerate(files, start=1):
                try:
                    proposal = self.engine.propose(source)
                    if proposal is not None and proposal.changed:
                        proposals.append(proposal)
                    message = f"Renamer — planning {index:,} / {scanned:,}: {source.name}"
                except FileNotFoundError:
                    skipped_missing.append(str(source))
                    message = (
                        f"Renamer — planning {index:,} / {scanned:,}: "
                        f"skipped missing file: {source.name}"
                    )
                now = time.perf_counter()
                if (
                    index == scanned
                    or index % self.PROGRESS_INTERVAL == 0
                    or now - last_emit >= self.PROGRESS_TIME_SECONDS
                ):
                    self.progress.emit(index, scanned, message)
                    last_emit = now

            self.proposals = self.engine._resolve_conflicts(proposals)
            self.planned.emit(
                {
                    "root": str(self.root),
                    "scanned": scanned,
                    "changed": len(self.proposals),
                    "unchanged": scanned - len(self.proposals) - len(skipped_missing),
                    "skipped_missing": len(skipped_missing),
                    "skipped_missing_paths": skipped_missing,
                    "preview": [
                        (str(p.source), str(p.destination), p.reason)
                        for p in self.proposals
                    ],
                }
            )
        except Exception as exc:
            self.failed.emit(f"Nie udało się przygotować planu Renamera: {exc}")

    def _execute_with_progress(self) -> list[RenameProposal]:
        """Execute the already validated rename plan while reporting completed renames."""
        proposals = [proposal for proposal in self.proposals if proposal.changed]
        self.engine._validate_plan(proposals)
        total = len(proposals)
        for proposal in proposals:
            if not proposal.source.exists():
                raise FileNotFoundError(
                    f"Rename refused because source disappeared: {proposal.source}"
                )

        executed: list[RenameProposal] = []
        temporary: list[tuple[Path, Path, RenameProposal]] = []
        self.progress.emit(0, total, "Renamer — preparing files…")
        try:
            for index, proposal in enumerate(proposals):
                temporary_path = self.engine._temporary_path(proposal.source, index)
                if temporary_path.exists():
                    raise FileExistsError(
                        f"Temporary rename path already exists: {temporary_path}"
                    )
                proposal.source.rename(temporary_path)
                temporary.append((temporary_path, proposal.destination, proposal))

            for completed, (temporary_path, destination, proposal) in enumerate(temporary, start=1):
                temporary_path.rename(destination)
                executed.append(proposal)
                self.progress.emit(
                    completed,
                    total,
                    f"Renamer — {completed:,} / {total:,}: {destination.name}",
                )
        except Exception:
            for temporary_path, destination, proposal in reversed(temporary):
                try:
                    if temporary_path.exists() and not proposal.source.exists():
                        temporary_path.rename(proposal.source)
                except OSError:
                    pass
            raise
        return executed

    def _reconcile_database_after_rename(
        self, paths: list[tuple[Path, Path]]
    ) -> tuple[int, int]:
        """Synchronize DB paths after the filesystem rename."""
        if not paths:
            return 0, 0
        database = self.database
        if database.connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")

        reconciled_conflicts = 0
        updated = 0
        with database.transaction() as connection:
            for source, destination in paths:
                source_text = str(source.resolve())
                destination_text = str(destination.resolve())
                source_rows = connection.execute(
                    "SELECT DISTINCT sha512 FROM file_location WHERE absolute_path = ?",
                    (source_text,),
                ).fetchall()
                destination_rows = connection.execute(
                    "SELECT sha512 FROM file_location WHERE absolute_path = ?",
                    (destination_text,),
                ).fetchall()

                if source_rows:
                    source_shas = {str(row["sha512"]).lower() for row in source_rows}
                    if len(source_shas) != 1:
                        raise DatabaseError(
                            "Nie można jednoznacznie ustalić SHA-512 dla źródłowej lokalizacji: "
                            f"{source_text}"
                        )
                    source_sha = next(iter(source_shas))
                elif destination_rows:
                    destination_shas = {str(row["sha512"]).lower() for row in destination_rows}
                    if len(destination_shas) == 1:
                        updated += 1
                        continue
                    raise DatabaseError(
                        "Nie można jednoznacznie ustalić SHA-512 dla docelowej lokalizacji: "
                        f"{destination_text}"
                    )
                else:
                    continue

                same_sha_destination = any(
                    str(row["sha512"]).lower() == source_sha for row in destination_rows
                )
                stale_destination_rows = [
                    row
                    for row in destination_rows
                    if str(row["sha512"]).lower() != source_sha
                ]

                if stale_destination_rows:
                    connection.execute(
                        "DELETE FROM file_location WHERE absolute_path = ? AND sha512 <> ?",
                        (destination_text, source_sha),
                    )
                    reconciled_conflicts += len(stale_destination_rows)

                if same_sha_destination:
                    connection.execute(
                        "DELETE FROM file_location WHERE absolute_path = ?",
                        (source_text,),
                    )
                    connection.execute(
                        "UPDATE file_location SET location_status = 'ACTIVE' WHERE absolute_path = ? AND sha512 = ?",
                        (destination_text, source_sha),
                    )
                else:
                    connection.execute(
                        "UPDATE file_location SET absolute_path = ?, location_status = 'ACTIVE' WHERE absolute_path = ? AND sha512 = ?",
                        (destination_text, source_text, source_sha),
                    )
                updated += 1

        return updated, reconciled_conflicts

    @Slot()
    def execute(self) -> None:
        try:
            started_at = time.perf_counter()
            executed = self._execute_with_progress()
            db_updated, db_reconciled_conflicts = self._reconcile_database_after_rename(
                [(proposal.source, proposal.destination) for proposal in executed]
            )
            self.finished.emit(
                {
                    "root": str(self.root),
                    "planned": len(self.proposals),
                    "renamed": len(executed),
                    "database_updated": db_updated,
                    "database_reconciled_conflicts": db_reconciled_conflicts,
                    "elapsed_seconds": time.perf_counter() - started_at,
                }
            )
        except Exception as exc:
            self.failed.emit(f"Renamer nie zakończył operacji: {exc}")
