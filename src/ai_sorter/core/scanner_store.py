"""Database-side helpers owned by the Scanner module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .database import Database, DatabaseError
from .models import FileLocationRecord


class ScannerStore:
    """Thin persistence adapter for Scanner-specific synchronization state."""

    def __init__(self, database: Database) -> None:
        self.database = database
        if database.connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        self.connection = database.connection
        self.connection.execute(
            "CREATE TEMP TABLE IF NOT EXISTS scanner_seen_paths (absolute_path TEXT PRIMARY KEY)"
        )
        self.connection.commit()

    def begin_scan(self) -> None:
        self.connection.execute("DELETE FROM scanner_seen_paths")
        self.connection.commit()

    def get_file_location(self, absolute_path: str) -> FileLocationRecord | None:
        row = self.connection.execute(
            """
            SELECT sha512, absolute_path, file_size, modified_at, location_status,
                   last_seen_execution_id
            FROM file_location
            WHERE absolute_path = ?
            """,
            (absolute_path,),
        ).fetchone()
        if row is None:
            return None
        return FileLocationRecord(
            sha512=row["sha512"],
            absolute_path=row["absolute_path"],
            file_size=row["file_size"],
            modified_at=self._parse_datetime(row["modified_at"]),
            location_status=row["location_status"],
            last_seen_execution_id=row["last_seen_execution_id"],
        )

    def mark_seen(self, absolute_path: str, execution_id: int) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO scanner_seen_paths (absolute_path) VALUES (?)",
            (absolute_path,),
        )
        self.connection.execute(
            """
            UPDATE file_location
            SET location_status = 'ACTIVE',
                last_seen_execution_id = ?,
                modified_at = modified_at
            WHERE absolute_path = ?
            """,
            (execution_id, absolute_path),
        )
        self.connection.commit()

    def touch_location(
        self,
        absolute_path: str,
        file_size: int,
        modified_at: datetime,
        execution_id: int,
    ) -> None:
        self.connection.execute(
            """
            UPDATE file_location
            SET file_size = ?, modified_at = ?, location_status = 'ACTIVE',
                last_seen_execution_id = ?
            WHERE absolute_path = ?
            """,
            (file_size, modified_at.isoformat(timespec="seconds"), execution_id, absolute_path),
        )
        self.mark_seen(absolute_path, execution_id)
        self.connection.commit()

    def persist_location(self, record: FileLocationRecord, execution_id: int) -> None:
        self.database.upsert_file_location(record)
        self.connection.execute(
            """
            UPDATE file_location
            SET last_seen_execution_id = ?, location_status = 'ACTIVE'
            WHERE sha512 = ? AND absolute_path = ?
            """,
            (execution_id, record.sha512.lower(), record.absolute_path),
        )
        self.connection.execute(
            "INSERT OR IGNORE INTO scanner_seen_paths (absolute_path) VALUES (?)",
            (record.absolute_path,),
        )
        self.connection.commit()

    def mark_missing_under_root(self, root: Path) -> int:
        root_text = str(root.resolve()).rstrip("\\/")
        pattern = root_text + "\\%"
        cursor = self.connection.execute(
            """
            UPDATE file_location
            SET location_status = 'MISSING'
            WHERE location_status = 'ACTIVE'
              AND absolute_path LIKE ?
              AND absolute_path NOT IN (SELECT absolute_path FROM scanner_seen_paths)
            """,
            (pattern,),
        )
        self.connection.commit()
        return max(0, cursor.rowcount)

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
