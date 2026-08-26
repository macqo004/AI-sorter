"""Streamed AllDup -> AI-Sorter import of SHA-512 identities and locations."""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

ALLDUP_SHA512_CTYPE = 5
DEFAULT_BATCH_SIZE = 10_000


@dataclass(frozen=True, slots=True)
class FullImportStats:
    selected_rows: int
    imported_locations: int
    new_file_records: int
    skipped_without_sha512: int
    elapsed_seconds: float

    @property
    def rows_per_second(self) -> float:
        return self.selected_rows / self.elapsed_seconds if self.elapsed_seconds > 0 else 0.0


class AllDupFullImporter:
    """Import AllDup SHA-512 + paths without reading files from disk."""

    def __init__(self, alldup_path: Path, project_path: Path) -> None:
        self.alldup_path = alldup_path.resolve()
        self.project_path = project_path.resolve()

    def run(
        self,
        root: Path,
        *,
        limit: int | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        apply: bool = False,
    ) -> FullImportStats:
        if not self.alldup_path.is_file():
            raise ValueError(f"Nie znaleziono bazy AllDup: {self.alldup_path}")
        if not self.project_path.is_file():
            raise ValueError(f"Nie znaleziono bazy projektu: {self.project_path}")

        root_text = str(root.resolve()).rstrip("\\/")
        like_prefix = root_text + "\\%"
        batch_size = max(500, int(batch_size))
        started = time.perf_counter()

        alldup = sqlite3.connect(
            f"file:{self.alldup_path.as_posix()}?mode=ro", uri=True, timeout=30
        )
        project = sqlite3.connect(self.project_path, timeout=30)
        alldup.row_factory = sqlite3.Row
        project.row_factory = sqlite3.Row
        try:
            project.execute("PRAGMA foreign_keys = ON")
            project.execute("PRAGMA busy_timeout = 30000")

            # Prefix range on the indexed files.file column. No file contents are read.
            query = """
                SELECT f.file AS absolute_path,
                       h.fsize AS file_size,
                       h.checksum AS checksum
                FROM files AS f
                JOIN hashc AS h
                  ON h.fileid = f.id
                 AND h.ctype = ?
                WHERE f.file = ? OR f.file LIKE ?
                ORDER BY f.file
            """
            cursor = alldup.execute(query, (ALLDUP_SHA512_CTYPE, root_text, like_prefix))

            selected = imported = new_records = skipped = 0
            remaining = max(0, int(limit)) if limit is not None else None

            while True:
                fetch_count = batch_size if remaining is None else min(batch_size, remaining)
                if fetch_count <= 0:
                    break
                rows = cursor.fetchmany(fetch_count)
                if not rows:
                    break

                selected += len(rows)
                if remaining is not None:
                    remaining -= len(rows)

                valid_rows: list[tuple[str, int, str]] = []
                for row in rows:
                    digest = self._normalize_checksum(row["checksum"])
                    if len(digest) != 128:
                        skipped += 1
                        continue
                    valid_rows.append((str(row["absolute_path"]), int(row["file_size"] or 0), digest))

                if apply and valid_rows:
                    new_records += self._write_batch(project, valid_rows)
                    imported += len(valid_rows)

            return FullImportStats(
                selected_rows=selected,
                imported_locations=imported,
                new_file_records=new_records,
                skipped_without_sha512=skipped,
                elapsed_seconds=time.perf_counter() - started,
            )
        finally:
            alldup.close()
            project.close()

    @staticmethod
    def _write_batch(
        connection: sqlite3.Connection,
        rows: list[tuple[str, int, str]],
    ) -> int:
        unique_sha = list({sha for _, _, sha in rows})
        new_records = 0
        if unique_sha:
            placeholders = ",".join("?" for _ in unique_sha)
            before = int(
                connection.execute(
                    f"SELECT COUNT(*) AS count FROM file_record WHERE sha512 IN ({placeholders})",
                    tuple(unique_sha),
                ).fetchone()["count"]
            )
        else:
            before = len(unique_sha)

        with connection:
            connection.executemany(
                """
                INSERT INTO file_record
                    (sha512, size_bytes, modified_at, created_at, status)
                VALUES (?, ?, NULL, CURRENT_TIMESTAMP, 'ACTIVE')
                ON CONFLICT(sha512) DO UPDATE SET
                    size_bytes = excluded.size_bytes,
                    status = 'ACTIVE'
                """,
                [(sha, size) for _, size, sha in rows],
            )
            connection.executemany(
                """
                INSERT INTO file_location
                    (sha512, absolute_path, file_size, modified_at, location_status)
                VALUES (?, ?, ?, NULL, 'ACTIVE')
                ON CONFLICT(sha512, absolute_path) DO UPDATE SET
                    file_size = excluded.file_size,
                    location_status = 'ACTIVE'
                """,
                [(sha, path, size) for path, size, sha in rows],
            )
        new_records = max(0, len(unique_sha) - before)
        return new_records

    @staticmethod
    def _normalize_checksum(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, memoryview):
            value = value.tobytes()
        if isinstance(value, bytes):
            return value.hex().lower()
        return str(value).strip().lower()
