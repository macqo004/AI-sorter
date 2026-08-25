"""Fast AllDup SHA-512 cache import with read-only dry-run support."""
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

        readonly_project = self._open_readonly(self.project_path)
        alldup = self._open_readonly(self.alldup_path)
        try:
            locations_query = """
                SELECT absolute_path, file_size, sha512
                FROM file_location
                WHERE location_status = 'ACTIVE'
                ORDER BY absolute_path
            """
            params: tuple[object, ...] = ()
            if sample_size is not None:
                locations_query += " LIMIT ?"
                params = (max(1, int(sample_size)),)

            exact_rows = self._bulk_exact_matches(
                alldup,
                self.project_path,
                params,
            )
            locations = readonly_project.execute(locations_query, params).fetchall()

            exact_by_path = {str(row["absolute_path"]): row for row in exact_rows}
            unmatched = [row for row in locations if str(row["absolute_path"]) not in exact_by_path]

            exact = len(exact_rows)
            suffix = ambiguous = no_path = available = unchanged = conflicts = cacheable = 0
            cache_rows: list[tuple[str, int, str]] = []

            for row in exact_rows:
                path = str(row["absolute_path"])
                size = int(row["file_size"] or -1)
                current_sha = str(row["sha512"] or "").strip().lower()
                alldup_sha = self._normalize_checksum(row["checksum"])
                if len(alldup_sha) != 128:
                    continue
                available += 1
                if alldup_sha == current_sha:
                    unchanged += 1
                else:
                    conflicts += 1
                cacheable += 1
                cache_rows.append((path, size, alldup_sha))

            for location in unmatched:
                path = str(location["absolute_path"])
                size = int(location["file_size"] or -1)
                current_sha = str(location["sha512"] or "").strip().lower()
                candidates, match_kind = self._find_suffix_candidates(alldup, path, size)
                if match_kind == "suffix" and len(candidates) == 1:
                    suffix += 1
                elif match_kind == "ambiguous":
                    ambiguous += 1
                    continue
                else:
                    no_path += 1
                    continue

                alldup_sha = self._get_sha512(alldup, int(candidates[0][0]), size)
                if not alldup_sha:
                    continue
                available += 1
                if alldup_sha == current_sha:
                    unchanged += 1
                else:
                    conflicts += 1
                cacheable += 1
                cache_rows.append((path, size, alldup_sha))

            imported = 0
            if apply and cache_rows:
                writable_project = self._open_writable(self.project_path)
                try:
                    self._ensure_cache_table(writable_project)
                    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    writable_project.executemany(
                        """
                        INSERT INTO external_hash_cache
                            (absolute_path, file_size, sha512, source, updated_at)
                        VALUES (?, ?, ?, 'alldup', ?)
                        ON CONFLICT(absolute_path, file_size, source) DO UPDATE SET
                            sha512 = excluded.sha512,
                            updated_at = excluded.updated_at
                        """,
                        [(path, size, sha, now) for path, size, sha in cache_rows],
                    )
                    writable_project.commit()
                    imported = len(cache_rows)
                finally:
                    writable_project.close()

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
            readonly_project.close()
            alldup.close()

    @classmethod
    def _bulk_exact_matches(
        cls,
        alldup: sqlite3.Connection,
        project_path: Path,
        params: tuple[object, ...],
    ) -> list[sqlite3.Row]:
        project_uri = f"file:{project_path.as_posix()}?mode=ro"
        attached = False
        try:
            alldup.execute("ATTACH DATABASE ? AS projectdb", (project_uri,))
            attached = True
            limit_sql = " LIMIT ?" if params else ""
            query = f"""
                SELECT
                    p.absolute_path,
                    p.file_size,
                    p.sha512,
                    h.checksum AS checksum
                FROM projectdb.file_location AS p
                JOIN main.files AS f
                  ON f.file = p.absolute_path
                JOIN main.hashc AS h
                  ON h.fileid = f.id
                 AND h.fsize = p.file_size
                 AND h.ctype = ?
                WHERE p.location_status = 'ACTIVE'
                ORDER BY p.absolute_path
                {limit_sql}
            """
            query_params = (ALLDUP_SHA512_CTYPE, *params)
            return alldup.execute(query, query_params).fetchall()
        finally:
            if attached:
                try:
                    alldup.execute("DETACH DATABASE projectdb")
                except sqlite3.Error:
                    pass

    @staticmethod
    def _open_readonly(path: Path) -> sqlite3.Connection:
        uri = f"file:{path.as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @staticmethod
    def _open_writable(path: Path) -> sqlite3.Connection:
        connection = sqlite3.connect(path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

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
    def _find_suffix_candidates(
        cls,
        connection: sqlite3.Connection,
        path: str,
        size: int,
    ) -> tuple[list[tuple[int, str]], str]:
        normalized = cls._normalize_path(path)
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
    def _get_sha512(connection: sqlite3.Connection, file_id: int, size: int) -> str | None:
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
        return AllDupImporter._normalize_checksum(row[0])

    @staticmethod
    def _normalize_checksum(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, memoryview):
            value = value.tobytes()
        if isinstance(value, bytes):
            return value.hex().lower()
        return str(value).strip().lower()
