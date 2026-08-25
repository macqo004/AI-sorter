"""Safe AllDup SHA-512 cache import and dry-run reporting."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ALLDUP_SHA512_CTYPE = 5


@dataclass(frozen=True, slots=True)
class ImportStats:
    project_locations: int
    exact_matches: int
    suffix_matches: int
    ambiguous_matches: int
    no_path_match: int
    sha512_available: int
    unchanged: int
    conflicts: int
    cacheable: int
    imported: int


class AllDupImporter:
    """Compare project locations with AllDup and optionally cache AllDup SHA-512 values."""

    def __init__(self, alldup_path: Path, project_path: Path) -> None:
        self.alldup_path = alldup_path.resolve()
        self.project_path = project_path.resolve()

    def run(self, sample_size: int | None = None, apply: bool = False) -> ImportStats:
        if not self.alldup_path.is_file():
            raise ValueError(f"Plik bazy AllDup nie istnieje: {self.alldup_path}")
        if not self.project_path.is_file():
            raise ValueError(f"Baza projektu nie istnieje: {self.project_path}")

        project = sqlite3.connect(self.project_path, timeout=10)
        alldup = sqlite3.connect(
            f"file:{self.alldup_path.as_posix()}?mode=ro", uri=True, timeout=10
        )
        project.row_factory = sqlite3.Row
        alldup.row_factory = sqlite3.Row
        try:
            if apply:
                self._ensure_cache_table(project)

            query = """
                SELECT absolute_path, file_size, sha512
                FROM file_location
                WHERE location_status = 'ACTIVE'
                ORDER BY absolute_path
            """
            params: tuple[object, ...] = ()
            if sample_size is not None:
                query += " LIMIT ?"
                params = (max(1, int(sample_size)),)
            locations = project.execute(query, params).fetchall()

            exact = suffix = ambiguous = no_path = available = unchanged = conflicts = cacheable = imported = 0
            for location in locations:
                path = str(location["absolute_path"])
                size = int(location["file_size"] or -1)
                current_sha = str(location["sha512"] or "").strip().lower()

                candidates, match_kind = self._find_candidates(alldup, path, size)
                if match_kind == "exact":
                    exact += 1
                elif match_kind == "suffix":
                    suffix += 1
                elif match_kind == "ambiguous":
                    ambiguous += 1
                else:
                    no_path += 1
                    continue

                if len(candidates) != 1:
                    continue

                alldup_sha = self._get_sha512(alldup, int(candidates[0][0]), size)
                if not alldup_sha:
                    continue
                available += 1

                if alldup_sha == current_sha:
                    unchanged += 1
                else:
                    conflicts += 1

                # Cache every trustworthy AllDup match. This is deliberately
                # separate from the canonical Scanner SHA512 tables.
                cacheable += 1
                if apply:
                    project.execute(
                        """
                        INSERT INTO external_hash_cache
                            (absolute_path, file_size, sha512, source, updated_at)
                        VALUES (?, ?, ?, 'alldup', ?)
                        ON CONFLICT(absolute_path, file_size, source) DO UPDATE SET
                            sha512 = excluded.sha512,
                            updated_at = excluded.updated_at
                        """,
                        (
                            path,
                            size,
                            alldup_sha,
                            datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        ),
                    )
                    imported += 1

            if apply:
                project.commit()

            return ImportStats(
                project_locations=len(locations),
                exact_matches=exact,
                suffix_matches=suffix,
                ambiguous_matches=ambiguous,
                no_path_match=no_path,
                sha512_available=available,
                unchanged=unchanged,
                conflicts=conflicts,
                cacheable=cacheable,
                imported=imported,
            )
        finally:
            project.close()
            alldup.close()

    @staticmethod
    def _ensure_cache_table(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS external_hash_cache (
                absolute_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                sha512 TEXT NOT NULL,
                source TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (absolute_path, file_size, source)
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_external_hash_cache_path ON external_hash_cache(absolute_path)"
        )
        connection.commit()

    @staticmethod
    def _normalize_path(value: str) -> str:
        text = value.strip().replace("/", "\\")
        while text.startswith("\\\\?\\"):
            text = text[4:]
        while "\\\\" in text:
            text = text.replace("\\\\", "\\")
        return text.rstrip("\\").casefold()

    @classmethod
    def _find_candidates(
        cls,
        connection: sqlite3.Connection,
        path: str,
        size: int,
    ) -> tuple[list[tuple[int, str]], str]:
        rows = connection.execute(
            "SELECT id, file FROM files WHERE file = ?", (path,)
        ).fetchall()
        if rows:
            return [(int(row[0]), str(row[1])) for row in rows], "exact"

        normalized = cls._normalize_path(path)
        rows = connection.execute(
            "SELECT id, file FROM files WHERE lower(file) = ?", (normalized,)
        ).fetchall()
        if rows:
            return [(int(row[0]), str(row[1])) for row in rows], "exact"

        parts = [part for part in normalized.split("\\") if part]
        usable = parts[1:] if parts and parts[0].endswith(":") else parts
        for count in (6, 5, 4, 3):
            if len(usable) < count:
                continue
            suffix = "\\".join(usable[-count:])
            escaped = suffix.replace("!", "!!").replace("%", "!%").replace("_", "!_")
            rows = connection.execute(
                """
                SELECT f.id, f.file
                FROM files f
                JOIN hashc h
                  ON h.fileid = f.id
                 AND h.fsize = ?
                 AND h.ctype = ?
                WHERE lower(f.file) LIKE lower(?) ESCAPE '!'
                GROUP BY f.id, f.file
                LIMIT 2
                """,
                (size, ALLDUP_SHA512_CTYPE, "%\\" + escaped),
            ).fetchall()
            if len(rows) == 1:
                return [(int(rows[0][0]), str(rows[0][1]))], "suffix"
            if len(rows) > 1:
                return [(int(row[0]), str(row[1])) for row in rows], "ambiguous"
        return [], "none"

    @staticmethod
    def _get_sha512(
        connection: sqlite3.Connection,
        file_id: int,
        size: int,
    ) -> str | None:
        row = connection.execute(
            """
            SELECT checksum
            FROM hashc
            WHERE fileid = ? AND fsize = ? AND ctype = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (file_id, size, ALLDUP_SHA512_CTYPE),
        ).fetchone()
        if row is None or row[0] is None:
            return None
        blob = row[0]
        if isinstance(blob, memoryview):
            blob = blob.tobytes()
        if isinstance(blob, bytes):
            return blob.hex().lower()
        return str(blob).strip().lower()
