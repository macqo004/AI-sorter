"""Persistent human review labels for database-backed result browsing."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from .database import Database, DatabaseError


class ManualReviewStore:
    """Store human classifications separately from module-generated results."""

    VALID_LABELS = {"normal", "mostly_monochrome", "monochrome"}

    def __init__(self, database: Database) -> None:
        self.database = database
        connection = database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        self.connection = connection
        self._ensure_table()

    def _ensure_table(self) -> None:
        try:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS manual_review (
                    sha512 TEXT PRIMARY KEY,
                    label TEXT NOT NULL CHECK (label IN ('normal', 'mostly_monochrome', 'monochrome')),
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (sha512) REFERENCES file_record(sha512) ON DELETE CASCADE
                )
                """
            )
            self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_manual_review_label ON manual_review(label)"
            )
            self.connection.commit()
        except sqlite3.Error as exc:
            raise DatabaseError(
                "Nie udało się przygotować tabeli ręcznej oceny wyników. "
                "Baza projektu nie została zmieniona poza wymaganym przygotowaniem tej tabeli."
            ) from exc

    def get_label(self, sha512: str) -> str | None:
        try:
            row = self.connection.execute(
                "SELECT label FROM manual_review WHERE sha512 = ?",
                (sha512.lower(),),
            ).fetchone()
            return str(row["label"]) if row else None
        except sqlite3.Error as exc:
            raise DatabaseError("Nie udało się odczytać ręcznej oceny pliku.") from exc

    def set_label(self, sha512: str, label: str) -> None:
        normalized_sha = sha512.strip().lower()
        if len(normalized_sha) != 128 or any(ch not in "0123456789abcdef" for ch in normalized_sha):
            raise DatabaseError("Nieprawidłowy SHA512 pliku.")
        if label not in self.VALID_LABELS:
            raise DatabaseError("Wybrano nieprawidłową kategorię ręcznej oceny.")

        try:
            self.connection.execute(
                """
                INSERT INTO manual_review (sha512, label, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(sha512) DO UPDATE SET
                    label = excluded.label,
                    updated_at = excluded.updated_at
                """,
                (normalized_sha, label, datetime.now(timezone.utc).isoformat(timespec="seconds")),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise DatabaseError(
                "Nie można zapisać ręcznej oceny, ponieważ plik nie istnieje już jako rekord w bazie projektu."
            ) from exc
        except sqlite3.Error as exc:
            self.connection.rollback()
            raise DatabaseError("Nie udało się zapisać ręcznej oceny pliku.") from exc

    def clear_label(self, sha512: str) -> None:
        try:
            self.connection.execute(
                "DELETE FROM manual_review WHERE sha512 = ?",
                (sha512.strip().lower(),),
            )
            self.connection.commit()
        except sqlite3.Error as exc:
            self.connection.rollback()
            raise DatabaseError("Nie udało się usunąć ręcznej oceny pliku.") from exc
