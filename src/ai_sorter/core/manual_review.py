"""Human review storage kept separate from module analysis results."""

from __future__ import annotations

from datetime import datetime, timezone

from .database import Database, DatabaseError


class ManualReviewStore:
    """Persist user classifications without overwriting module-owned results."""

    LABELS = ("normal", "mostly_monochrome", "monochrome")

    def __init__(self, database: Database) -> None:
        self.database = database
        connection = database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS manual_review (
                    sha512 TEXT PRIMARY KEY,
                    review_label TEXT NOT NULL CHECK (
                        review_label IN ('normal', 'mostly_monochrome', 'monochrome')
                    ),
                    reviewed_at TEXT NOT NULL,
                    FOREIGN KEY (sha512) REFERENCES file_record(sha512) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_manual_review_label ON manual_review(review_label)"
            )
            connection.commit()
        except Exception as exc:
            raise DatabaseError("Nie udało się przygotować tabeli ręcznych ocen.") from exc

    def get_label(self, sha512: str) -> str | None:
        row = self.database.connection.execute(
            "SELECT review_label FROM manual_review WHERE sha512 = ?",
            (sha512,),
        ).fetchone()
        return str(row["review_label"]) if row else None

    def set_label(self, sha512: str, label: str) -> None:
        if label not in self.LABELS:
            raise DatabaseError("Wybrano nieprawidłową kategorię ręcznej oceny.")
        try:
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO manual_review (sha512, review_label, reviewed_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(sha512) DO UPDATE SET
                        review_label = excluded.review_label,
                        reviewed_at = excluded.reviewed_at
                    """,
                    (sha512, label, datetime.now(timezone.utc).isoformat(timespec="seconds")),
                )
        except Exception as exc:
            raise DatabaseError("Nie udało się zapisać ręcznej oceny pliku.") from exc

    def clear_label(self, sha512: str) -> None:
        try:
            with self.database.transaction() as connection:
                connection.execute("DELETE FROM manual_review WHERE sha512 = ?", (sha512,))
        except Exception as exc:
            raise DatabaseError("Nie udało się usunąć ręcznej oceny pliku.") from exc

    def count_by_label(self, shas: list[str]) -> dict[str, int]:
        counts = {"normal": 0, "mostly_monochrome": 0, "monochrome": 0, "unreviewed": 0}
        if not shas:
            return counts
        placeholders = ",".join("?" for _ in shas)
        rows = self.database.connection.execute(
            f"SELECT review_label, COUNT(*) AS count FROM manual_review WHERE sha512 IN ({placeholders}) GROUP BY review_label",
            tuple(shas),
        ).fetchall()
        reviewed = 0
        for row in rows:
            label = str(row["review_label"])
            counts[label] = int(row["count"])
            reviewed += int(row["count"])
        counts["unreviewed"] = len(shas) - reviewed
        return counts
