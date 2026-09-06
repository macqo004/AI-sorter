"""Qt worker for filesystem/database maintenance operations."""

from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import QObject, Signal, Slot

from ..core.database import Database, DatabaseError

BATCH_SIZE = 1000


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

    def _connection(self):
        connection = self.database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        return connection

    def _check_all_locations(self) -> str:
        """Check active paths and cheap filesystem metadata without reading file content."""
        connection = self._connection()
        total = int(connection.execute(
            "SELECT COUNT(*) AS count FROM file_location WHERE location_status = 'ACTIVE'"
        ).fetchone()["count"])
        checked = missing = inaccessible = size_mismatch = timestamp_mismatch = 0
        cursor = connection.execute(
            """
            SELECT absolute_path, file_size, modified_at
            FROM file_location
            WHERE location_status = 'ACTIVE'
            ORDER BY absolute_path
            """
        )
        self.progress.emit(0, max(1, total), "Checking file locations and metadata…")
        while True:
            rows = cursor.fetchmany(BATCH_SIZE)
            if not rows:
                break
            missing_paths: list[str] = []
            for row in rows:
                path_text = str(row["absolute_path"])
                try:
                    stat = os.stat(path_text)
                except FileNotFoundError:
                    checked += 1
                    missing += 1
                    missing_paths.append(path_text)
                    continue
                except OSError:
                    checked += 1
                    inaccessible += 1
                    continue

                checked += 1
                expected_size = row["file_size"]
                expected_modified = row["modified_at"]
                if expected_size is not None and int(stat.st_size) != int(expected_size):
                    size_mismatch += 1
                if expected_modified is not None:
                    actual_modified = datetime.fromtimestamp(stat.st_mtime).replace(microsecond=0)
                    if actual_modified != expected_modified:
                        timestamp_mismatch += 1

            if missing_paths:
                self._mark_missing_batch(missing_paths)
            self.progress.emit(checked, max(1, total), "Checking file locations and metadata…")

        return (
            f"Checked: {checked:,}\n"
            f"Marked missing: {missing:,}\n"
            f"Inaccessible/errors: {inaccessible:,}\n"
            f"Size mismatches: {size_mismatch:,}\n"
            f"Timestamp mismatches: {timestamp_mismatch:,}"
        )

    def _mark_missing_batch(self, paths: list[str]) -> int:
        if not paths:
            return 0
        with self.database.transaction() as connection:
            cursor = connection.executemany(
                "UPDATE file_location SET location_status = 'MISSING' WHERE absolute_path = ? AND location_status = 'ACTIVE'",
                [(path,) for path in paths],
            )
            return max(0, cursor.rowcount or 0)

    def _cleanup_inactive(self) -> str:
        connection = self._connection()
        # Only MISSING locations are cleanup candidates. Other non-ACTIVE values,
        # if introduced later for audit/history, are retained until explicitly handled.
        inactive_count = int(connection.execute(
            "SELECT COUNT(*) AS count FROM file_location WHERE location_status = 'MISSING'"
        ).fetchone()["count"])
        orphan_count = int(connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM file_record fr
            WHERE fr.status = 'ACTIVE'
              AND NOT EXISTS (
                  SELECT 1 FROM file_location fl WHERE fl.sha512 = fr.sha512
              )
            """
        ).fetchone()["count"])
        total = inactive_count + orphan_count
        current = 0
        removed_locations = removed_records = 0
        self.progress.emit(0, max(1, total), "Preparing inactive-data cleanup…")

        while True:
            rows = connection.execute(
                f"SELECT rowid FROM file_location WHERE location_status = 'MISSING' LIMIT {BATCH_SIZE}"
            ).fetchall()
            if not rows:
                break
            rowids = [int(row["rowid"]) for row in rows]
            placeholders = ",".join("?" for _ in rowids)
            with self.database.transaction() as connection:
                cursor = connection.execute(f"DELETE FROM file_location WHERE rowid IN ({placeholders})", rowids)
                count = max(0, cursor.rowcount or 0)
            removed_locations += count
            current += count
            self.progress.emit(min(current, max(1, total)), max(1, total), "Removing missing locations…")

        while True:
            rows = connection.execute(
                f"""
                SELECT rowid FROM file_record fr
                WHERE fr.status = 'ACTIVE'
                  AND NOT EXISTS (SELECT 1 FROM file_location fl WHERE fl.sha512 = fr.sha512)
                LIMIT {BATCH_SIZE}
                """
            ).fetchall()
            if not rows:
                break
            rowids = [int(row["rowid"]) for row in rows]
            placeholders = ",".join("?" for _ in rowids)
            with self.database.transaction() as connection:
                cursor = connection.execute(f"DELETE FROM file_record WHERE rowid IN ({placeholders})", rowids)
                count = max(0, cursor.rowcount or 0)
            removed_records += count
            current += count
            self.progress.emit(min(current, max(1, total)), max(1, total), "Removing orphan ACTIVE file records…")

        self.progress.emit(max(1, total), max(1, total), "Cleanup complete.")
        return f"Removed missing locations: {removed_locations:,}\nRemoved orphan ACTIVE file records: {removed_records:,}"
