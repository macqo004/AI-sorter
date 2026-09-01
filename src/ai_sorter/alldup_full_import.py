"""Full AllDup -> AI-Sorter Scanner database importer.

Imports AllDup SHA-512 identities and physical file locations directly into the
canonical Scanner tables. The AllDup source database is always opened read-only.
The project database is updated in bounded batches and can be resumed safely.
"""
from __future__ import annotations

import argparse
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

ALLDUP_SHA512_CTYPE = 5
DEFAULT_BATCH_SIZE = 2000
ProgressCallback = Callable[[int, int, int, int], None]


@dataclass(frozen=True, slots=True)
class FullImportStats:
    source_rows: int
    valid_rows: int
    invalid_rows: int
    unique_files: int
    unique_locations: int
    imported_files: int
    imported_locations: int
    conflicts: int
    elapsed_seconds: float


class AllDupFullImporter:
    """Import the canonical SHA-512 + path dataset from AllDup into Scanner DB."""

    module_id = "alldup_full_import"
    module_version = "0.1.0"

    def __init__(self, alldup_path: Path, project_path: Path, batch_size: int = DEFAULT_BATCH_SIZE) -> None:
        self.alldup_path = alldup_path.resolve()
        self.project_path = project_path.resolve()
        self.batch_size = max(100, int(batch_size))

    def run(
        self,
        *,
        sample_size: int | None = None,
        apply: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> FullImportStats:
        started = time.perf_counter()
        if not self.alldup_path.is_file():
            raise ValueError(f"Nie znaleziono bazy AllDup: {self.alldup_path}")
        if not self.project_path.is_file():
            raise ValueError(f"Nie znaleziono bazy Scanner: {self.project_path}")

        source = self._open_alldup_readonly(self.alldup_path)
        project = self._open_project(apply=apply)
        try:
            source_rows = self._count_source_rows(source, sample_size)
            valid_rows = invalid_rows = processed = 0
            imported_files = imported_locations = conflicts = 0
            files_batch: list[tuple[str, int]] = []
            locations_batch: list[tuple[str, str, int]] = []

            query = """
                SELECT f.file AS absolute_path,
                       h.fsize AS file_size,
                       h.checksum AS checksum
                FROM hashc AS h
                JOIN files AS f ON f.id = h.fileid
                WHERE h.ctype = ?
                ORDER BY f.id, f.file, h.id
            """
            params: list[object] = [ALLDUP_SHA512_CTYPE]
            if sample_size is not None:
                params.append(max(1, int(sample_size)))
                query += " LIMIT ?"

            cursor = source.execute(query, tuple(params))
            for row in cursor:
                processed += 1
                path = str(row["absolute_path"] or "").strip()
                size = int(row["file_size"] or 0)
                sha512 = self._normalize_sha512(row["checksum"])
                if not path or not sha512 or size < 0:
                    invalid_rows += 1
                else:
                    valid_rows += 1
                    files_batch.append((sha512, size))
                    locations_batch.append((sha512, path, size))

                if len(locations_batch) >= self.batch_size:
                    if apply:
                        f_count, l_count, c_count = self._persist_batch(project, files_batch, locations_batch)
                        imported_files += f_count
                        imported_locations += l_count
                        conflicts += c_count
                        project.commit()
                    files_batch.clear()
                    locations_batch.clear()
                    if progress_callback:
                        progress_callback(processed, source_rows, imported_locations, conflicts)

            if apply and locations_batch:
                f_count, l_count, c_count = self._persist_batch(project, files_batch, locations_batch)
                imported_files += f_count
                imported_locations += l_count
                conflicts += c_count
                project.commit()

            if progress_callback:
                progress_callback(processed, source_rows, imported_locations, conflicts)

            unique_files, unique_locations = self._counts(project)
            return FullImportStats(
                source_rows=source_rows,
                valid_rows=valid_rows,
                invalid_rows=invalid_rows,
                unique_files=unique_files if apply else 0,
                unique_locations=unique_locations if apply else 0,
                imported_files=imported_files,
                imported_locations=imported_locations,
                conflicts=conflicts,
                elapsed_seconds=time.perf_counter() - started,
            )
        finally:
            project.close()
            source.close()

    @staticmethod
    def _open_alldup_readonly(path: Path) -> sqlite3.Connection:
        connection = sqlite3.connect(
            f"file:{path.as_posix()}?mode=ro", uri=True, timeout=30
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    @staticmethod
    def _open_project(path: Path, *, apply: bool) -> sqlite3.Connection:
        connection = sqlite3.connect(path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        if not apply:
            connection.execute("PRAGMA query_only = ON")
        return connection

    @staticmethod
    def _count_source_rows(source: sqlite3.Connection, sample_size: int | None) -> int:
        row = source.execute(
            "SELECT COUNT(*) AS count FROM hashc WHERE ctype = ?",
            (ALLDUP_SHA512_CTYPE,),
        ).fetchone()
        total = int(row["count"] if row else 0)
        return min(total, max(0, int(sample_size))) if sample_size is not None else total

    @staticmethod
    def _counts(project: sqlite3.Connection) -> tuple[int, int]:
        files = int(project.execute("SELECT COUNT(*) AS count FROM file_record").fetchone()["count"])
        locations = int(project.execute("SELECT COUNT(*) AS count FROM file_location").fetchone()["count"])
        return files, locations

    def _persist_batch(
        self,
        project: sqlite3.Connection,
        files: list[tuple[str, int]],
        locations: list[tuple[str, str, int]],
    ) -> tuple[int, int, int]:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        project.executemany(
            """
            INSERT INTO file_record
                (sha512, size_bytes, width_px, height_px, modified_at, created_at, status)
            VALUES (?, ?, NULL, NULL, NULL, ?, 'ACTIVE')
            ON CONFLICT(sha512) DO UPDATE SET
                size_bytes = CASE
                    WHEN file_record.size_bytes IS NULL OR file_record.size_bytes = 0
                    THEN excluded.size_bytes ELSE file_record.size_bytes END,
                status = 'ACTIVE'
            """,
            [(sha, size, now) for sha, size in files],
        )

        project.execute("DROP TABLE IF EXISTS temp.alldup_import_stage")
        project.execute(
            """
            CREATE TEMP TABLE alldup_import_stage (
                sha512 TEXT NOT NULL,
                absolute_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                PRIMARY KEY (sha512, absolute_path)
            )
            """
        )
        project.executemany(
            "INSERT OR IGNORE INTO alldup_import_stage (sha512, absolute_path, file_size) VALUES (?, ?, ?)",
            locations,
        )

        conflicts_row = project.execute(
            """
            SELECT COUNT(*) AS count
            FROM alldup_import_stage s
            JOIN file_location fl
              ON fl.absolute_path = s.absolute_path
             AND fl.location_status = 'ACTIVE'
             AND fl.sha512 <> s.sha512
            """
        ).fetchone()
        conflicts = int(conflicts_row["count"] if conflicts_row else 0)

        project.execute(
            """
            INSERT INTO file_location
                (sha512, absolute_path, file_size, modified_at, location_status, last_seen_execution_id)
            SELECT s.sha512, s.absolute_path, s.file_size, NULL, 'ACTIVE', NULL
            FROM alldup_import_stage s
            WHERE NOT EXISTS (
                SELECT 1
                FROM file_location fl
                WHERE fl.absolute_path = s.absolute_path
                  AND fl.location_status = 'ACTIVE'
                  AND fl.sha512 <> s.sha512
            )
            ON CONFLICT(sha512, absolute_path) DO UPDATE SET
                file_size = excluded.file_size,
                location_status = 'ACTIVE'
            """
        )
        imported_locations = int(
            project.execute("SELECT COUNT(*) AS count FROM alldup_import_stage").fetchone()["count"]
        ) - conflicts
        return len(files), max(0, imported_locations), conflicts

    @staticmethod
    def _normalize_sha512(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, memoryview):
            value = value.tobytes()
        if isinstance(value, bytes):
            value = value.hex()
        digest = str(value).strip().lower()
        if len(digest) != 128 or any(ch not in "0123456789abcdef" for ch in digest):
            return ""
        return digest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Importuje SHA-512 i ścieżki plików bezpośrednio z bazy AllDup "
            "do canonicalnych tabel Scanner DB."
        )
    )
    parser.add_argument("alldup_db", type=Path, help="Ścieżka do checksum.adb")
    parser.add_argument("project_db", type=Path, help="Ścieżka do project.db")
    parser.add_argument("--sample", type=int, default=None, help="Importuj tylko pierwsze N rekordów źródłowych")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Rozmiar batcha zapisu")
    parser.add_argument("--apply", action="store_true", help="Rzeczywiście zapisz dane do project.db")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    importer = AllDupFullImporter(args.alldup_db, args.project_db, args.batch_size)

    def progress(current: int, total: int, imported: int, conflicts: int) -> None:
        if total:
            print(
                f"\rAllDup import: {current:,}/{total:,} ({current / total * 100:6.2f}%) "
                f"| imported locations {imported:,} | conflicts {conflicts:,}",
                end="",
                flush=True,
            )

    try:
        stats = importer.run(sample_size=args.sample, apply=args.apply, progress_callback=progress)
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"\nERROR: {exc}")
        return 1

    print()
    print("AllDup Full Import")
    print(f"Source rows: {stats.source_rows:,}")
    print(f"Valid rows: {stats.valid_rows:,}")
    print(f"Invalid rows: {stats.invalid_rows:,}")
    print(f"Unique SHA-512 files in project DB: {stats.unique_files:,}")
    print(f"Unique locations in project DB: {stats.unique_locations:,}")
    print(f"Imported file records (batch rows): {stats.imported_files:,}")
    print(f"Imported locations (batch rows): {stats.imported_locations:,}")
    print(f"Path conflicts skipped: {stats.conflicts:,}")
    print(f"Elapsed: {stats.elapsed_seconds:.3f}s")
    print("Mode: APPLY — Scanner DB was updated." if args.apply else "Mode: DRY-RUN — Scanner DB was not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
