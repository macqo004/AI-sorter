"""Database-side helpers owned by the Scanner module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .database import Database, DatabaseError
from .models import FileLocationRecord, FileRecord


class ScannerStore:
    """Thin persistence adapter for Scanner-specific synchronization state."""

    def __init__(self, database: Database) -> None:
        self.database = database
        if database.connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        self.connection = database.connection
        self._ensure_last_seen_column()
        self.connection.execute(
            "CREATE TEMP TABLE IF NOT EXISTS scanner_seen_paths (absolute_path TEXT PRIMARY KEY)"
        )
        self.connection.commit()

    def _ensure_last_seen_column(self) -> None:
        columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(file_location)").fetchall()
        }
        if "last_seen_execution_id" not in columns:
            self.connection.execute(
                "ALTER TABLE file_location ADD COLUMN last_seen_execution_id INTEGER"
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

    def touch_batch(
        self,
        items: list[tuple[str, int, datetime]],
        execution_id: int,
    ) -> None:
        if not items:
            return
        try:
            with self.database.transaction() as connection:
                connection.executemany(
                    """
                    UPDATE file_location
                    SET file_size = ?,
                        modified_at = ?,
                        location_status = 'ACTIVE',
                        last_seen_execution_id = ?
                    WHERE absolute_path = ?
                    """,
                    [
                        (
                            size,
                            modified_at.isoformat(timespec="seconds"),
                            execution_id,
                            path,
                        )
                        for path, size, modified_at in items
                    ],
                )
                connection.executemany(
                    "INSERT OR IGNORE INTO scanner_seen_paths (absolute_path) VALUES (?)",
                    [(path,) for path, _, _ in items],
                )
        except Exception as exc:
            raise DatabaseError(
                "Nie udało się zapisać bieżącego stanu lokalizacji plików."
            ) from exc

    def persist_batch(
        self,
        files: list[FileRecord],
        locations: list[FileLocationRecord],
        execution_id: int,
    ) -> None:
        if not files:
            return
        try:
            with self.database.transaction() as connection:
                connection.executemany(
                    """
                    INSERT INTO file_record
                        (sha512, size_bytes, modified_at, created_at, status)
                    VALUES (?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP), ?)
                    ON CONFLICT(sha512) DO UPDATE SET
                        size_bytes = excluded.size_bytes,
                        modified_at = excluded.modified_at,
                        status = excluded.status
                    """,
                    [
                        (
                            record.sha512.lower(),
                            record.size_bytes,
                            self._iso(record.modified_at),
                            self._iso(record.created_at),
                            record.status,
                        )
                        for record in files
                    ],
                )
                connection.executemany(
                    """
                    INSERT INTO file_location
                        (sha512, absolute_path, file_size, modified_at, location_status,
                         last_seen_execution_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(sha512, absolute_path) DO UPDATE SET
                        file_size = excluded.file_size,
                        modified_at = excluded.modified_at,
                        location_status = excluded.location_status,
                        last_seen_execution_id = excluded.last_seen_execution_id
                    """,
                    [
                        (
                            record.sha512.lower(),
                            record.absolute_path,
                            record.file_size,
                            self._iso(record.modified_at),
                            record.location_status,
                            execution_id,
                        )
                        for record in locations
                    ],
                )
                connection.executemany(
                    "INSERT OR IGNORE INTO scanner_seen_paths (absolute_path) VALUES (?)",
                    [(record.absolute_path,) for record in locations],
                )
        except Exception as exc:
            raise DatabaseError(
                "Nie udało się zapisać partii wyników skanowania w bazie danych."
            ) from exc

    def mark_missing_under_root(self, root: Path) -> int:
        root_text = str(root.resolve()).rstrip("\\/")
        pattern = root_text + "\\%"
        try:
            with self.database.transaction() as connection:
                cursor = connection.execute(
                    """
                    UPDATE file_location
                    SET location_status = 'MISSING'
                    WHERE location_status = 'ACTIVE'
                      AND absolute_path LIKE ?
                      AND absolute_path NOT IN (SELECT absolute_path FROM scanner_seen_paths)
                    """,
                    (pattern,),
                )
                return max(0, cursor.rowcount)
        except Exception as exc:
            raise DatabaseError(
                "Nie udało się ustalić, które lokalizacje plików są już niedostępne."
            ) from exc

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        return value.isoformat(timespec="seconds") if value is not None else None

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
