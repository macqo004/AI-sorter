"""Database-side helpers owned by the Scanner module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .database import Database, DatabaseError
from .models import FileLocationRecord, FileRecord


class ScannerStore:
    """Thin persistence adapter for Scanner-specific synchronization state."""

    LOOKUP_BATCH_SIZE = 500

    def __init__(self, database: Database) -> None:
        self.database = database
        if database.connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        self.connection = database.connection
        self._ensure_last_seen_column()
        self.connection.execute(
            "CREATE TEMP TABLE IF NOT EXISTS scanner_seen_paths (absolute_path TEXT PRIMARY KEY)"
        )
        self.connection.execute(
            "CREATE TEMP TABLE IF NOT EXISTS scanner_clear_shas (sha512 TEXT PRIMARY KEY)"
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

    def lookup_locations(self, absolute_paths: list[str]) -> dict[str, FileLocationRecord]:
        """Return known locations using bounded IN queries instead of one query per file."""
        if not absolute_paths:
            return {}

        result: dict[str, FileLocationRecord] = {}
        unique_paths = list(dict.fromkeys(absolute_paths))
        try:
            for offset in range(0, len(unique_paths), self.LOOKUP_BATCH_SIZE):
                batch = unique_paths[offset : offset + self.LOOKUP_BATCH_SIZE]
                placeholders = ",".join("?" for _ in batch)
                rows = self.connection.execute(
                    f"""
                    SELECT sha512, absolute_path, file_size, modified_at, location_status,
                           last_seen_execution_id
                    FROM file_location
                    WHERE absolute_path IN ({placeholders})
                    """,
                    batch,
                ).fetchall()
                for row in rows:
                    result[row["absolute_path"]] = FileLocationRecord(
                        sha512=row["sha512"],
                        absolute_path=row["absolute_path"],
                        file_size=row["file_size"],
                        modified_at=self._parse_datetime(row["modified_at"]),
                        location_status=row["location_status"],
                        last_seen_execution_id=row["last_seen_execution_id"],
                    )
        except Exception as exc:
            raise DatabaseError(
                "Nie udało się sprawdzić istniejących lokalizacji plików w bazie danych."
            ) from exc
        return result

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
                        (size, modified_at.isoformat(timespec="seconds"), execution_id, path)
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

    def clear_folder(self, root: Path) -> tuple[int, int]:
        """Remove Scanner-owned locations under root and orphaned file identities.

        A temporary SHA table is used instead of a giant ``IN (?, ?, ...)`` list,
        so clearing large roots is not limited by SQLite's bind-parameter limit.
        File records that still have another location are preserved.
        """
        root_text = str(root.resolve()).rstrip("\\/")
        pattern = root_text + "\\%"
        try:
            with self.database.transaction() as connection:
                connection.execute("DELETE FROM scanner_clear_shas")
                connection.execute(
                    """
                    INSERT OR IGNORE INTO scanner_clear_shas (sha512)
                    SELECT DISTINCT sha512
                    FROM file_location
                    WHERE location_status IN ('ACTIVE', 'MISSING')
                      AND (absolute_path = ? OR absolute_path LIKE ?)
                    """,
                    (root_text, pattern),
                )
                affected = int(
                    connection.execute(
                        "SELECT COUNT(*) AS count FROM scanner_clear_shas"
                    ).fetchone()["count"]
                )
                if affected == 0:
                    return 0, 0

                connection.execute(
                    """
                    DELETE FROM file_location
                    WHERE location_status IN ('ACTIVE', 'MISSING')
                      AND (absolute_path = ? OR absolute_path LIKE ?)
                    """,
                    (root_text, pattern),
                )
                orphan_cursor = connection.execute(
                    """
                    DELETE FROM file_record
                    WHERE EXISTS (
                        SELECT 1
                        FROM scanner_clear_shas scs
                        WHERE scs.sha512 = file_record.sha512
                    )
                    AND NOT EXISTS (
                        SELECT 1
                        FROM file_location fl
                        WHERE fl.sha512 = file_record.sha512
                    )
                    """
                )
                return affected, max(0, orphan_cursor.rowcount or 0)
        except Exception as exc:
            raise DatabaseError(
                "Nie udało się wyczyścić wyników Scanner dla wybranego folderu. "
                "Pliki kolekcji nie zostały zmienione."
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
