"""Qt worker for filesystem/database maintenance operations."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from ..core.database import Database, DatabaseError
from ..core.scanner_store import ScannerStore


class MaintenanceWorker(QObject):
    """Run Scanner maintenance without blocking the GUI thread."""

    progress = Signal(int, int, str)
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, database: Database, operation: str) -> None:
        super().__init__()
        self.database = database
        self.operation = operation

    @Slot()
    def run(self) -> None:
        try:
            if self.operation == "check_locations":
                result = self._check_all_locations()
            elif self.operation == "cleanup_inactive":
                result = self._cleanup_inactive()
            else:
                raise ValueError(f"Unknown maintenance operation: {self.operation}")
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))

    def _store(self) -> ScannerStore:
        return ScannerStore(self.database)

    def _check_all_locations(self) -> str:
        connection = self.database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        total = int(connection.execute(
            "SELECT COUNT(*) AS count FROM file_location WHERE location_status = 'ACTIVE'"
        ).fetchone()["count"])
        self.progress.emit(0, max(1, total), "Checking file locations and metadata…")
        checked, missing, size_mismatch, timestamp_mismatch = self._store().check_all_locations()
        self.progress.emit(checked, max(1, total), "Location check complete.")
        return (
            f"Checked: {checked:,}\n"
            f"Marked missing: {missing:,}\n"
            f"Size mismatches: {size_mismatch:,}\n"
            f"Timestamp mismatches: {timestamp_mismatch:,}"
        )

    def _cleanup_inactive(self) -> str:
        self.progress.emit(0, 1, "Cleaning inactive Scanner data…")
        removed_locations, removed_records = self._store().cleanup_inactive()
        self.progress.emit(1, 1, "Inactive Scanner data cleanup complete.")
        return (
            f"Removed missing locations: {removed_locations:,}\n"
            f"Removed orphan ACTIVE file records: {removed_records:,}"
        )
