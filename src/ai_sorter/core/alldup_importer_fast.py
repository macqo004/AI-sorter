"""Streaming AllDup SHA-512 cache importer using bounded batches."""
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
    """Compare project locations with AllDup efficiently without loading millions of rows into RAM."""

    def __init__(self, alldup_path: Path, project_path: Path) -> None:
        self.alldup_path = alldup_path.resolve()
        self.project_path = project_path.resolve()

    def run(self, sample_size: int | None = None, apply: bool = False, allow_suffix: bool = False) -> ImportStats:
        if not self.alldup_path.is_file():
            raise ValueError(f"Plik bazy AllDup nie istnieje: {self.alldup_path}")
        if not self.project_path.is_file():
            raise ValueError(f"Baza projektu nie istnieje: {self.project_path}")

        project = self._open_readonly(self.project_path)
        alldup = self._open_readonly(self.alldup_path)
        writable: sqlite3.Connection | None = None
        try:
            total = self._count_project_locations(project)
            limit = max(1, int(sample_size)) if sample_size is not None else None
            if limit is not None:
                total = min(total, limit)

            if apply:
                writable = self._open_writable(self.project_path)
                self._ensure_cache_table(writable)

            stats = {
                "project_locations": 0,
                "exact_matches": 0,
                "suffix_matches": 0,
                "ambiguous_matches": 0,
                "no_path_match": 0,
                "sha512_available": 0,
                "unchanged": 0,
                "conflicts": 0,
                "cacheable": 0,
                "imported": 0,
            }

            cursor = project.execute(
                """
                SELECT absolute_path, file_size, sha512
                FROM file_location
                WHERE location_status = 'ACTIVE'
                ORDER BY absolute_path
                """
            )
            remaining = limit
            while True:
                batch_size = BATCH_SIZE if remaining is None else min(BATCH_SIZE, remaining)
                if batch_size <= 0:
                    break
                locations = cursor.fetchmany(batch_size)
                if not locations:
                    break
                stats["project_locations"] += len(locations)
                if remaining is not None:
                    remaining -= len(locations)

                by_path = {str(row["absolute_path"]): row for row in locations}
                exact_matches = self._find_exact_matches(alldup, by_path)
                stats["exact_matches"] += len(exact_matches)

                cache_rows: list[tuple[str, int, str]] = []
                matched_paths = set(exact_matches)
                for path, digest in exact_matches.items():
                    row = by_path[path]
                    stats["sha512_available"] += 1
                    current_sha = str(row["sha512"] or "").strip().lower()
                    if digest == current_sha:
                        stats["unchanged"] += 1
                    else:
                        stats["conflicts"] += 1
                    stats["cacheable"] += 1
                    cache_rows.append((path, int(row["file_size"] or 0), digest))

                if allow_suffix:
                    for row in locations:
                        path = str(row["absolute_path"])
                        if path in matched_paths:
                            continue
                        size = int(row["file_size"] or -1)
                        candidates, kind = self._find_suffix_candidates(alldup, path, size)
                        if kind == "suffix" and len(candidates) == 1:
                            stats["suffix_matches"] += 1
                        elif kind == "ambiguous":
                            stats["ambiguous_matches"] += 1
                            continue
                        else:
                            stats["no_path_match"] += 1
                            continue
                        digest = self._get_sha512(alldup, candidates[0][0], size)
                        if not digest:
                            stats["no_path_match"] += 1
                            continue
                        stats["sha512_available"] += 1
                        current_sha = str(row["sha512"] or "").strip().lower()
                        if digest == current_sha:
                            stats["unchanged"] += 1
                        else:
                            stats["conflicts"] += 1
                        stats["cacheable"] += 1
                        cache_rows.append((path, size, digest))
                else:
                    stats["no_path_match"] += len(locations) - len(matched_paths)

                if writable is not None and cache_rows:
                    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    writable.executemany(
                        """
                        INSERT INTO external_hash_cache
                            (absolute_path, file_size, sha512, source, updated_at)
                        VALUES (?, ?, ?, 'alldup', ?)
                        ON CONFLICT(absolute_path, file_size, source) DO UPDATE SET
                            sha512 = excluded.sha512,
                            updated_at = excluded.updated_at
                        """,
                        [(path, size, digest, now) for path, size, digest in cache_rows],
                    )
                    writable.commit()
                    stats["imported"] += len(cache_rows)

            return ImportStats(**stats)
        finally:
            if writable is not None:
                writable.close()
            project.close()
            alldup.close()

    @staticmethod
    def _count_project_locations(connection: sqlite3.Connection) -> int:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM file_location WHERE location_status = 'ACTIVE'"
        ).fetchone()
        return int(row["count"]) if row else 0

    @staticmethod
    def _find_exact_matches(connection: sqlite3.Connection, by_path: dict[str, sqlite3.Row]) -> dict[str, str]:
        paths = list(by_path)
        if not paths:
            return {}
        placeholders = ",".join("?" for _ in paths)
        rows = connection.execute(
            f"""
            SELECT f.file, h.checksum
            FROM files f
            JOIN hashc h ON h.fileid = f.id AND h.ctype = ?
            WHERE f.file IN ({placeholders})
            """,
            (ALLDUP_SHA512_CTYPE, *paths),
        ).fetchall()
        result: dict[str, str] = {}
        for row in rows:
            digest = AllDupImporterFast._normalize_checksum(row["checksum"])
            path = str(row["file"])
            if len(digest) == 128 and path not in result:
                result[path] = digest
        return result

    @staticmethod
    def _open_readonly(path: Path) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    @staticmethod
    def _open_writable(path: Path) -> sqlite3.Connection:
        connection = sqlite3.connect(path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
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
                FROM files f
                JOIN hashc h ON h.fileid = f.id AND h.fsize = ? AND h.ctype = ?
                WHERE lower(f.file) LIKE lower(?) ESCAPE '!'
                GROUP BY f.id, f.file
                LIMIT 2
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
