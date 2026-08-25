"""Fast AllDup SHA-512 cache import using batched indexed lookups."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ALLDUP_SHA512_CTYPE = 5
BATCH_SIZE = 500

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

class AllDupImporterFast:
    """Compare project locations with AllDup efficiently and optionally cache hashes."""
    def __init__(self, alldup_path: Path, project_path: Path) -> None:
        self.alldup_path = alldup_path.resolve()
        self.project_path = project_path.resolve()

    def run(self, sample_size: int | None = None, apply: bool = False) -> ImportStats:
        if not self.alldup_path.is_file():
            raise ValueError(f"Plik bazy AllDup nie istnieje: {self.alldup_path}")
        if not self.project_path.is_file():
            raise ValueError(f"Baza projektu nie istnieje: {self.project_path}")

        project = self._open_readonly(self.project_path)
        alldup = self._open_readonly(self.alldup_path)
        try:
            query = "SELECT absolute_path, file_size, sha512 FROM file_location WHERE location_status = 'ACTIVE' ORDER BY absolute_path"
            params = ()
            if sample_size is not None:
                query += " LIMIT ?"
                params = (max(1, int(sample_size)),)
            locations = project.execute(query, params).fetchall()
            by_path = {str(row["absolute_path"]): row for row in locations}

            matches: dict[str, str] = {}
            for offset in range(0, len(locations), BATCH_SIZE):
                paths = [str(row["absolute_path"]) for row in locations[offset:offset + BATCH_SIZE]]
                placeholders = ",".join("?" for _ in paths)
                rows = alldup.execute(
                    f"""
                    SELECT f.file, h.fsize, h.checksum
                    FROM files f
                    JOIN hashc h ON h.fileid = f.id AND h.ctype = ?
                    WHERE f.file IN ({placeholders})
                    """,
                    (ALLDUP_SHA512_CTYPE, *paths),
                ).fetchall()
                for row in rows:
                    path = str(row["file"])
                    project_row = by_path.get(path)
                    if project_row is None:
                        continue
                    if int(project_row["file_size"] or -1) != int(row["fsize"] or -2):
                        continue
                    digest = self._normalize_checksum(row["checksum"])
                    if len(digest) == 128:
                        matches[path] = digest

            exact = len(matches)
            suffix = ambiguous = no_path = available = unchanged = conflicts = cacheable = 0
            cache_rows: list[tuple[str, int, str]] = []
            unmatched = [row for row in locations if str(row["absolute_path"]) not in matches]

            for path, alldup_sha in matches.items():
                row = by_path[path]
                current_sha = str(row["sha512"] or "").strip().lower()
                available += 1
                if alldup_sha == current_sha:
                    unchanged += 1
                else:
                    conflicts += 1
                cacheable += 1
                cache_rows.append((path, int(row["file_size"] or 0), alldup_sha))

            for row in unmatched:
                path = str(row["absolute_path"])
                size = int(row["file_size"] or -1)
                current_sha = str(row["sha512"] or "").strip().lower()
                candidates, kind = self._find_suffix_candidates(alldup, path, size)
                if kind == "suffix" and len(candidates) == 1:
                    suffix += 1
                elif kind == "ambiguous":
                    ambiguous += 1
                    continue
                else:
                    no_path += 1
                    continue
                alldup_sha = self._get_sha512(alldup, candidates[0][0], size)
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
                writable = self._open_writable(self.project_path)
                try:
                    self._ensure_cache_table(writable)
                    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    writable.executemany(
                        """
                        INSERT INTO external_hash_cache (absolute_path, file_size, sha512, source, updated_at)
                        VALUES (?, ?, ?, 'alldup', ?)
                        ON CONFLICT(absolute_path, file_size, source) DO UPDATE SET
                            sha512 = excluded.sha512,
                            updated_at = excluded.updated_at
                        """,
                        [(p, s, sha, now) for p, s, sha in cache_rows],
                    )
                    writable.commit()
                    imported = len(cache_rows)
                finally:
                    writable.close()

            return ImportStats(len(locations), exact, suffix, ambiguous, no_path, available, unchanged, conflicts, cacheable, imported)
        finally:
            project.close()
            alldup.close()

    @staticmethod
    def _open_readonly(path: Path) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True, timeout=10)
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
        connection.execute("""
            CREATE TABLE IF NOT EXISTS external_hash_cache (
                absolute_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                sha512 TEXT NOT NULL,
                source TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (absolute_path, file_size, source)
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_external_hash_cache_path ON external_hash_cache(absolute_path)")

    @staticmethod
    def _normalize_checksum(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, memoryview):
            value = value.tobytes()
        if isinstance(value, bytes):
            return value.hex().lower()
        return str(value).strip().lower()

    @staticmethod
    def _normalize_path(value: str) -> str:
        text = value.strip().replace("/", "\\")
        while text.startswith("\\\\?\\"):
            text = text[4:]
        while "\\\\" in text:
            text = text.replace("\\\\", "\\")
        return text.rstrip("\\").casefold()

    @classmethod
    def _find_suffix_candidates(cls, connection: sqlite3.Connection, path: str, size: int) -> tuple[list[tuple[int, str]], str]:
        normalized = cls._normalize_path(path)
        parts = [p for p in normalized.split("\\") if p]
        usable = parts[1:] if parts and parts[0].endswith(":") else parts
        for count in (6, 5, 4, 3):
            if len(usable) < count:
                continue
            suffix = "\\".join(usable[-count:])
            escaped = suffix.replace("!", "!!").replace("%", "!%").replace("_", "!_")
            rows = connection.execute(
                """
                SELECT f.id, f.file
                FROM files f JOIN hashc h ON h.fileid=f.id AND h.fsize=? AND h.ctype=?
                WHERE lower(f.file) LIKE lower(?) ESCAPE '!'
                GROUP BY f.id, f.file LIMIT 2
                """,
                (size, ALLDUP_SHA512_CTYPE, "%\\" + escaped),
            ).fetchall()
            if len(rows) == 1:
                return [(int(rows[0][0]), str(rows[0][1]))], "suffix"
            if len(rows) > 1:
                return [(int(r[0]), str(r[1])) for r in rows], "ambiguous"
        return [], "none"

    @staticmethod
    def _get_sha512(connection: sqlite3.Connection, file_id: int, size: int) -> str | None:
        row = connection.execute(
            "SELECT checksum FROM hashc WHERE fileid=? AND fsize=? AND ctype=? ORDER BY id DESC LIMIT 1",
            (file_id, size, ALLDUP_SHA512_CTYPE),
        ).fetchone()
        return AllDupImporterFast._normalize_checksum(row[0]) if row and row[0] is not None else None
