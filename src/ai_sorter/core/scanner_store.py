"""Database-side helpers owned by the Scanner module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .database import Database, DatabaseError
from .models import FileLocationRecord, FileRecord


class ScannerStore:
    """Thin persistence adapter for Scanner-specific synchronization state."""

    LOOKUP_BATCH_SIZE = 500
    CLEANUP_BATCH_SIZE = 1000

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
        columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(file_location)").fetchall()}
        if "last_seen_execution_id" not in columns:
            self.connection.execute("ALTER TABLE file_location ADD COLUMN last_seen_execution_id INTEGER")
            self.connection.commit()

    def begin_scan(self) -> None:
        self.connection.execute("DELETE FROM scanner_seen_paths")
        self.connection.commit()

    def lookup_locations(self, absolute_paths: list[str]) -> dict[str, FileLocationRecord]:
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
            raise DatabaseError("Nie udało się sprawdzić istniejących lokalizacji plików w bazie danych.") from exc
        return result

    def touch_batch(self, items: list[tuple[str, int, datetime]], execution_id: int) -> None:
        if not items:
            return
        try:
            with self.database.transaction() as connection:
                connection.executemany(
                    """
                    UPDATE file_location
                    SET file_size = ?, modified_at = ?, location_status = 'ACTIVE',
                        last_seen_execution_id = ?
                    WHERE absolute_path = ?
                    """,
                    [(size, self._windows_time(modified_at), execution_id, path) for path, size, modified_at in items],
                )
                connection.executemany(
                    "INSERT OR IGNORE INTO scanner_seen_paths (absolute_path) VALUES (?)",
                    [(path,) for path, _, _ in items],
                )
        except Exception as exc:
            raise DatabaseError("Nie udało się zapisać bieżącego stanu lokalizacji plików.") from exc

    def persist_batch(self, files: list[FileRecord], locations: list[FileLocationRecord], execution_id: int) -> None:
        if not files:
            return
        try:
            with self.database.transaction() as connection:
                connection.executemany(
                    """
                    INSERT INTO file_record
                        (sha512, size_bytes, width_px, height_px, modified_at, created_at, status)
                    VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP), ?)
                    ON CONFLICT(sha512) DO UPDATE SET
                        size_bytes = excluded.size_bytes,
                        width_px = COALESCE(excluded.width_px, file_record.width_px),
                        height_px = COALESCE(excluded.height_px, file_record.height_px),
                        modified_at = excluded.modified_at,
                        status = excluded.status
                    """,
                    [
                        (
                            record.sha512.lower(),
                            record.size_bytes,
                            record.width_px,
                            record.height_px,
                            self._windows_time(record.modified_at),
                            self._windows_time(record.created_at),
                            record.status,
                        )
                        for record in files
                    ],
                )
                connection.executemany(
                    """
                    INSERT INTO file_location
                        (sha512, absolute_path, file_size, modified_at, location_status, last_seen_execution_id)
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
                            self._windows_time(record.modified_at),
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
            raise DatabaseError("Nie udało się zapisać partii wyników skanowania w bazie danych.") from exc

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
                      AND (absolute_path = ? OR absolute_path LIKE ?)
                      AND absolute_path NOT IN (SELECT absolute_path FROM scanner_seen_paths)
                    """,
                    (root_text, pattern),
                )
                return max(0, cursor.rowcount)
        except Exception as exc:
            raise DatabaseError("Nie udało się ustalić, które lokalizacje plików są już niedostępne.") from exc

    def clear_folder(self, root: Path) -> tuple[int, int]:
        root_text = str(root.resolve()).rstrip("\\/")
        pattern = root_text + "\\%"
        try:
            with self.database.transaction() as connection:
                connection.execute("DELETE FROM scanner_clear_shas")
                connection.execute(
                    """
                    INSERT OR IGNORE INTO scanner_clear_shas (sha512)
                    SELECT DISTINCT sha512 FROM file_location
                    WHERE location_status IN ('ACTIVE', 'MISSING')
                      AND (absolute_path = ? OR absolute_path LIKE ?)
                    """,
                    (root_text, pattern),
                )
                affected = int(connection.execute("SELECT COUNT(*) AS count FROM scanner_clear_shas").fetchone()["count"])
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
                    WHERE EXISTS (SELECT 1 FROM scanner_clear_shas scs WHERE scs.sha512 = file_record.sha512)
                      AND status = 'ACTIVE'
                      AND NOT EXISTS (SELECT 1 FROM file_location fl WHERE fl.sha512 = file_record.sha512)
                    """
                )
                return affected, max(0, orphan_cursor.rowcount or 0)
        except Exception as exc:
            raise DatabaseError("Nie udało się wyczyścić wyników Scanner dla wybranego folderu. Pliki kolekcji nie zostały zmienione.") from exc

    def check_all_locations(self) -> tuple[int, int]:
        checked = missing = 0
        try:
            cursor = self.connection.execute("SELECT absolute_path FROM file_location WHERE location_status = 'ACTIVE'")
            missing_paths: list[str] = []
            for row in cursor:
                path = Path(str(row["absolute_path"]))
                checked += 1
                try:
                    exists = path.is_file()
                except OSError:
                    exists = False
                if not exists:
                    missing_paths.append(str(path))
                    if len(missing_paths) >= self.CLEANUP_BATCH_SIZE:
                        missing += self._mark_missing_batch(missing_paths)
                        missing_paths.clear()
            if missing_paths:
                missing += self._mark_missing_batch(missing_paths)
            return checked, missing
        except Exception as exc:
            raise DatabaseError("Nie udało się sprawdzić aktualności lokalizacji plików.") from exc

    def _mark_missing_batch(self, paths: list[str]) -> int:
        if not paths:
            return 0
        with self.database.transaction() as connection:
            cursor = connection.executemany(
                "UPDATE file_location SET location_status = 'MISSING' WHERE absolute_path = ? AND location_status = 'ACTIVE'",
                [(path,) for path in paths],
            )
            return max(0, cursor.rowcount or 0)

    def cleanup_inactive(self) -> tuple[int, int]:
        """Delete only MISSING locations and orphaned ACTIVE identities; retain ARCHIVED history."""
        removed_locations = removed_records = 0
        try:
            while True:
                with self.database.transaction() as connection:
                    cursor = connection.execute(
                        f"""
                        DELETE FROM file_location
                        WHERE rowid IN (
                            SELECT rowid FROM file_location
                            WHERE location_status = 'MISSING'
                            LIMIT {self.CLEANUP_BATCH_SIZE}
                        )
                        """
                    )
                    count = max(0, cursor.rowcount or 0)
                removed_locations += count
                if count < self.CLEANUP_BATCH_SIZE:
                    break

            while True:
                with self.database.transaction() as connection:
                    cursor = connection.execute(
                        f"""
                        DELETE FROM file_record
                        WHERE rowid IN (
                            SELECT fr.rowid FROM file_record AS fr
                            WHERE fr.status = 'ACTIVE'
                              AND NOT EXISTS (SELECT 1 FROM file_location fl WHERE fl.sha512 = fr.sha512)
                            LIMIT {self.CLEANUP_BATCH_SIZE}
                        )
                        """
                    )
                    count = max(0, cursor.rowcount or 0)
                removed_records += count
                if count < self.CLEANUP_BATCH_SIZE:
                    break
            return removed_locations, removed_records
        except Exception as exc:
            raise DatabaseError("Nie udało się usunąć nieaktywnych danych Scanner. Pliki kolekcji nie zostały zmienione.") from exc

    @staticmethod
    def _windows_time(value: datetime | None) -> str | None:
        """Store the local Windows-style timestamp displayed in file Properties to whole seconds."""
        return value.replace(microsecond=0, tzinfo=None).isoformat(sep=" ") if value is not None else None

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
