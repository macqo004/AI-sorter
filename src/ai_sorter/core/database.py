"""SQLite database access layer and schema management."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .models import (
    DatabaseStatus,
    FileLocationRecord,
    FileRecord,
    ModuleExecutionRecord,
    ModuleRecord,
)

SCHEMA_VERSION = 3


class DatabaseError(RuntimeError):
    """Human-readable application-level database error."""


class Database:
    """Owns the SQLite connection and exposes application-safe DB operations."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.connection: sqlite3.Connection | None = None

    def open(self) -> None:
        if self.connection is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            connection = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA busy_timeout = 10000")
            self.connection = connection
            self._ensure_schema_metadata()
            self._migrate()
        except sqlite3.Error as exc:
            if self.connection is not None:
                self.connection.close()
                self.connection = None
            raise DatabaseError(
                "Nie udało się otworzyć lub przygotować bazy danych projektu. "
                "Pliki kolekcji nie zostały zmienione."
            ) from exc

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def is_open(self) -> bool:
        return self.connection is not None

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._require_connection()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    def status(self) -> DatabaseStatus:
        connection = self._require_connection()
        row = connection.execute(
            "SELECT schema_version FROM schema_metadata WHERE id = 1"
        ).fetchone()
        return DatabaseStatus(
            connected=True,
            path=str(self.path),
            schema_version=int(row["schema_version"]) if row else None,
            file_count=self._count("file_record"),
            location_count=self._count("file_location"),
            module_count=self._count("module"),
            execution_count=self._count("module_execution"),
        )

    def upsert_file(self, record: FileRecord) -> None:
        self._validate_sha512(record.sha512)
        connection = self._require_connection()
        try:
            connection.execute(
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
                (
                    record.sha512.lower(), record.size_bytes, record.width_px, record.height_px,
                    self._iso(record.modified_at), self._iso(record.created_at), record.status,
                ),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise DatabaseError("Nie udało się zapisać identyfikatora pliku w bazie danych.") from exc

    def upsert_file_location(self, record: FileLocationRecord) -> None:
        self._validate_sha512(record.sha512)
        connection = self._require_connection()
        self._ensure_file_location_last_seen_column()
        try:
            connection.execute(
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
                (
                    record.sha512.lower(), record.absolute_path, record.file_size,
                    self._iso(record.modified_at), record.location_status,
                    record.last_seen_execution_id,
                ),
            )
            connection.commit()
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            raise DatabaseError("Nie można zapisać lokalizacji, ponieważ jej plik nie ma zarejestrowanej tożsamości.") from exc
        except sqlite3.Error as exc:
            connection.rollback()
            raise DatabaseError("Nie udało się zapisać lokalizacji pliku w bazie danych.") from exc

    def register_module(self, record: ModuleRecord) -> None:
        connection = self._require_connection()
        try:
            connection.execute(
                """
                INSERT INTO module (module_id, display_name, module_version, enabled)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(module_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    module_version = excluded.module_version,
                    enabled = excluded.enabled
                """,
                (record.module_id, record.display_name, record.module_version, 1 if record.enabled else 0),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise DatabaseError("Nie udało się zarejestrować modułu w bazie danych.") from exc

    def start_module_execution(self, module_id: str, started_at: datetime) -> int:
        connection = self._require_connection()
        try:
            cursor = connection.execute(
                "INSERT INTO module_execution (module_id, started_at, status) VALUES (?, ?, 'RUNNING')",
                (module_id, self._iso(started_at)),
            )
            connection.commit()
            return int(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            raise DatabaseError("Nie można uruchomić wykonania modułu, ponieważ moduł nie jest zarejestrowany.") from exc
        except sqlite3.Error as exc:
            connection.rollback()
            raise DatabaseError("Nie udało się zapisać rozpoczęcia wykonania modułu.") from exc

    def finish_module_execution(self, record: ModuleExecutionRecord) -> None:
        connection = self._require_connection()
        try:
            connection.execute(
                """
                UPDATE module_execution
                SET status = ?, processed_count = ?, success_count = ?, failure_count = ?
                WHERE execution_id = ?
                """,
                (record.status, record.processed_count, record.success_count, record.failure_count, record.execution_id),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise DatabaseError("Nie udało się zapisać zakończenia wykonania modułu.") from exc

    def record_module_result(self, sha512: str, module_id: str, result_key: str, payload: dict, confidence: float | None = None) -> None:
        self._validate_sha512(sha512)
        connection = self._require_connection()
        try:
            connection.execute(
                """
                INSERT INTO analysis_result
                    (sha512, module_id, result_key, confidence, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(sha512, module_id, result_key) DO UPDATE SET
                    confidence = excluded.confidence,
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (sha512.lower(), module_id, result_key, confidence,
                 json.dumps(payload, ensure_ascii=False, sort_keys=True)),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise DatabaseError("Nie udało się zapisać wyniku modułu w bazie danych.") from exc

    def _ensure_schema_metadata(self) -> None:
        connection = self._require_connection()
        connection.execute("CREATE TABLE IF NOT EXISTS schema_metadata (id INTEGER PRIMARY KEY CHECK (id = 1), schema_version INTEGER NOT NULL)")
        row = connection.execute("SELECT schema_version FROM schema_metadata WHERE id = 1").fetchone()
        if row is None:
            connection.execute("INSERT INTO schema_metadata (id, schema_version) VALUES (1, 1)")
            connection.commit()

    def _migrate(self) -> None:
        connection = self._require_connection()
        row = connection.execute("SELECT schema_version FROM schema_metadata WHERE id = 1").fetchone()
        current = int(row["schema_version"]) if row else 1
        if current > SCHEMA_VERSION:
            raise DatabaseError(f"Baza projektu pochodzi z nowszej wersji aplikacji (schema {current}). Ta wersja programu nie może jej bezpiecznie otworzyć.")
        try:
            if current < 2:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS file_record (
                        sha512 TEXT PRIMARY KEY,
                        size_bytes INTEGER,
                        modified_at TEXT,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'ARCHIVED'))
                    );
                    CREATE TABLE IF NOT EXISTS file_location (
                        sha512 TEXT NOT NULL,
                        absolute_path TEXT NOT NULL,
                        file_size INTEGER,
                        modified_at TEXT,
                        location_status TEXT NOT NULL DEFAULT 'ACTIVE',
                        PRIMARY KEY (sha512, absolute_path),
                        FOREIGN KEY (sha512) REFERENCES file_record(sha512) ON DELETE CASCADE
                    );
                    CREATE TABLE IF NOT EXISTS module (
                        module_id TEXT PRIMARY KEY,
                        display_name TEXT NOT NULL,
                        module_version TEXT NOT NULL,
                        enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1))
                    );
                    CREATE TABLE IF NOT EXISTS module_execution (
                        execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        module_id TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'RUNNING',
                        processed_count INTEGER NOT NULL DEFAULT 0,
                        success_count INTEGER NOT NULL DEFAULT 0,
                        failure_count INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY (module_id) REFERENCES module(module_id)
                    );
                    CREATE TABLE IF NOT EXISTS analysis_result (
                        sha512 TEXT NOT NULL,
                        module_id TEXT NOT NULL,
                        result_key TEXT NOT NULL,
                        confidence REAL,
                        payload_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (sha512, module_id, result_key),
                        FOREIGN KEY (sha512) REFERENCES file_record(sha512) ON DELETE CASCADE,
                        FOREIGN KEY (module_id) REFERENCES module(module_id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_file_location_path ON file_location(absolute_path);
                    CREATE INDEX IF NOT EXISTS idx_module_execution_module ON module_execution(module_id);
                    CREATE INDEX IF NOT EXISTS idx_analysis_result_module ON analysis_result(module_id);
                    UPDATE schema_metadata SET schema_version = 2 WHERE id = 1;
                    """
                )
                current = 2
            if current < 3:
                columns = {row["name"] for row in connection.execute("PRAGMA table_info(file_record)").fetchall()}
                if "width_px" not in columns:
                    connection.execute("ALTER TABLE file_record ADD COLUMN width_px INTEGER")
                if "height_px" not in columns:
                    connection.execute("ALTER TABLE file_record ADD COLUMN height_px INTEGER")
                connection.execute("UPDATE schema_metadata SET schema_version = 3 WHERE id = 1")
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise DatabaseError("Nie udało się zaktualizować schematu bazy danych projektu. Baza nie została pozostawiona w częściowo zmigrowanym stanie.") from exc

    def _ensure_file_location_last_seen_column(self) -> None:
        columns = {row["name"] for row in self._require_connection().execute("PRAGMA table_info(file_location)").fetchall()}
        if "last_seen_execution_id" not in columns:
            self._require_connection().execute("ALTER TABLE file_location ADD COLUMN last_seen_execution_id INTEGER")
            self._require_connection().commit()

    def _count(self, table: str) -> int:
        row = self._require_connection().execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
        return int(row["count"])

    def _require_connection(self) -> sqlite3.Connection:
        if self.connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        return self.connection

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        return value.isoformat(timespec="seconds") if value is not None else None

    @staticmethod
    def _validate_sha512(value: str) -> None:
        normalized = value.strip().lower()
        if len(normalized) != 128 or any(character not in "0123456789abcdef" for character in normalized):
            raise DatabaseError("Podany identyfikator SHA512 ma nieprawidłowy format.")
