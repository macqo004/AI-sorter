"""SQLite bootstrap for the application foundation."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1


class Database:
    """Small foundation wrapper around the project SQLite database."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.connection: sqlite3.Connection | None = None

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.initialize_schema()

    def initialize_schema(self) -> None:
        if self.connection is None:
            raise RuntimeError("Database connection is not open.")

        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_metadata (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                schema_version INTEGER NOT NULL
            );

            INSERT INTO schema_metadata (id, schema_version)
            VALUES (1, 1)
            ON CONFLICT(id) DO NOTHING;
            """
        )
        row = self.connection.execute(
            "SELECT schema_version FROM schema_metadata WHERE id = 1"
        ).fetchone()
        if row is None or row["schema_version"] != SCHEMA_VERSION:
            raise RuntimeError(
                f"Unsupported database schema version: "
                f"{row['schema_version'] if row else 'missing'}"
            )
        self.connection.commit()

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None
