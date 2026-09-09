"""Qt worker for planning and executing filename renames without blocking the GUI."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from ..core.scanner_store import ScannerStore
from ..renamer import RenameProposal, RenamerEngine, iter_files


class RenamerWorker(QObject):
    """Run Renamer planning/execution on a worker thread."""

    planned = Signal(object)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, database, root: Path, recursive: bool = True) -> None:
        super().__init__()
        self.database = database
        self.root = root
        self.recursive = recursive
        self.engine = RenamerEngine()
        self.proposals: list[RenameProposal] = []

    @Slot()
    def plan(self) -> None:
        try:
            files = iter_files(self.root, recursive=self.recursive)
            self.proposals = self.engine.plan(files)
            self.planned.emit(
                {
                    "root": str(self.root),
                    "scanned": len(files),
                    "changed": len(self.proposals),
                    "unchanged": len(files) - len(self.proposals),
                    "preview": [
                        (str(p.source), str(p.destination), p.reason)
                        for p in self.proposals
                    ],
                }
            )
        except Exception as exc:
            self.failed.emit(f"Nie udało się przygotować planu Renamera: {exc}")

    @Slot()
    def execute(self) -> None:
        try:
            started_at = time.perf_counter()
            executed = self.engine.execute(self.proposals)
            db_updated = ScannerStore(self.database).update_renamed_locations(
                [(proposal.source, proposal.destination) for proposal in executed]
            )
            self.finished.emit(
                {
                    "root": str(self.root),
                    "planned": len(self.proposals),
                    "renamed": len(executed),
                    "database_updated": db_updated,
                    "elapsed_seconds": time.perf_counter() - started_at,
                }
            )
        except Exception as exc:
            self.failed.emit(f"Renamer nie zakończył operacji: {exc}")
