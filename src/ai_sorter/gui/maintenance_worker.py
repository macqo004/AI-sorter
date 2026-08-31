"""Qt worker for filesystem/database maintenance operations."""

from __future__ import annotations

import os

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
        connection = self._connection()
        total = int(connection.execute(
            "SELECT COUNT(*) AS count FROM file_location WHERE location_status = 'ACTIVE'"
        ).fetchone()["count"])
        checked = missing = 0
        batch: list[str] = []
        cursor = connection.execute(
            "SELECT absolute_path FROM file_location WHERE location_status = 'ACTIVE' ORDER BY absolute_path"
        )
        for row in cursor:
            path_text = str(row["absolute_path"])
            try:
                exists = os.path.isfile(path_text)
            except OSError:
                exists = False
            checked += 1
            if not exists:
                batch.append(path_text)
            if len(batch) >= BATCH_SIZE:
                missing += self._mark_missing_batch(batch)
                batch.clear()
            self.progress.emit(checked, max(1, total), "Checking file locations…")
        if batch:
            missing += self._mark_missing_batch(batch)
        self.progress.emit(checked, max(1, total), "Checking file locations…")
        return f"Checked: {checked:,}\nMarked missing: {missing:,}"

    def _mark_missing_batch(self, paths: list[str]) -> int:
        connection = self._connection()
        connection.execute("BEGIN")
        try:
            connection.executemany(
                "UPDATE file_location SET location_status = 'MISSING' WHERE absolute_path = ? AND location_status = 'ACTIVE'",
                [(path,) for path in paths],
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return len(paths)

    def _cleanup_inactive(self) -> str:
        connection = self._connection()
        inactive_count = int(connection.execute(
            "SELECT COUNT(*) AS count FROM file_location WHERE location_status <> 'ACTIVE'"
        ).fetchone()["count"])
        orphan_count = int(connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM file_record fr
            WHERE NOT EXISTS (
                SELECT 1 FROM file_location fl
                WHERE fl.sha512 = fr.sha512 AND fl.location_status = 'ACTIVE'
            )
            """
        ).fetchone()["count"])
        total = inactive_count + orphan_count
        current = 0
        removed_locations = removed_records = 0

        while True:
            rows = connection.execute(
                f"SELECT rowid FROM file_location WHERE location_status <> 'ACTIVE' LIMIT {BATCH_SIZE}"
            ).fetchall()
            if not rows:
                break
            rowids = [int(row["rowid"]) for row in rows]
            placeholders = ",".join("?" for _ in rowids)
            connection.execute("BEGIN")
            try:
                cursor = connection.execute(
                    f"DELETE FROM file_location WHERE rowid IN ({placeholders})", rowids
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            count = max(0, cursor.rowcount or 0)
            removed_locations += count
            current += count
            self.progress.emit(min(current, max(1, total)), max(1, total), "Removing inactive locations…")

        while True:
            rows = connection.execute(
                f"""
                SELECT rowid FROM file_record fr
                WHERE NOT EXISTS (SELECT 1 FROM file_location fl WHERE fl.sha512 = fr.sha512)
                LIMIT {BATCH_SIZE}
                """
            ).fetchall()
            if not rows:
                break
            rowids = [int(row["rowid"]) for row in rows]
            placeholders = ",".join("?" for _ in rowids)
            connection.execute("BEGIN")
            try:
                cursor = connection.execute(
                    f"DELETE FROM file_record WHERE rowid IN ({placeholders})", rowids
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            count = max(0, cursor.rowcount or 0)
            removed_records += count
            current += count
            self.progress.emit(min(current, max(1, total)), max(1, total), "Removing orphan file records…")

        self.progress.emit(max(1, total), max(1, total), "Cleanup complete.")
        return (
            f"Removed locations: {removed_locations:,}\n"
            f"Removed orphan file records: {removed_records:,}"
        )
