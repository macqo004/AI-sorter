"""Qt worker for filesystem/database maintenance operations."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from ..core.database import Database
from ..core.scanner_store import ScannerStore


class MaintenanceWorker(QObject):
    """Run Scanner maintenance without blocking the GUI thread."""

    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, database: Database, operation: str) -> None:
        super().__init__()
        self.database = database
        self.operation = operation

    @Slot()
    def run(self) -> None:
        try:
            store = ScannerStore(self.database)
            if self.operation == "check_locations":
                result = store.check_all_locations(self._on_progress)
            elif self.operation == "cleanup_inactive":
                result = store.cleanup_inactive(self._on_progress)
            else:
                raise ValueError(f"Unknown maintenance operation: {self.operation}")
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))

    def _on_progress(self, current: int, total: int, message: str) -> None:
        self.progress.emit(current, total, message)
