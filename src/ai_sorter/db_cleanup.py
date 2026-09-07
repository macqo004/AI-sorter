"""Safe SQLite database cleanup utility for AI-Sorter."""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import time
from pathlib import Path


class DatabaseCleanupError(RuntimeError):
    """Raised when database cleanup cannot be completed safely."""


def _database_report(connection: sqlite3.Connection) -> tuple[int, int, int, int]:
    page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
    page_count = int(connection.execute("PRAGMA page_count").fetchone()[0])
    freelist_count = int(connection.execute("PRAGMA freelist_count").fetchone()[0])
    reserved_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
    _ = reserved_size  # Keep the tuple focused while making page_size explicit above.
    return page_size, page_count, freelist_count, page_size * freelist_count


def _integrity_check(connection: sqlite3.Connection) -> str:
    row = connection.execute("PRAGMA integrity_check").fetchone()
    return str(row[0]) if row else "unknown"


def cleanup_database(
    database_path: Path,
    *,
    apply: bool,
    backup_path: Path | None = None,
) -> tuple[int, int, int, float]:
    database_path = database_path.resolve()
    if not database_path.is_file():
        raise DatabaseCleanupError(f"Nie znaleziono bazy: {database_path}")

    before_size = database_path.stat().st_size
    started = time.perf_counter()

    connection = sqlite3.connect(database_path, timeout=60)
    try:
        connection.execute("PRAGMA busy_timeout=60000")
        connection.execute("PRAGMA foreign_keys=ON")
        integrity = _integrity_check(connection)
        if integrity != "ok":
            raise DatabaseCleanupError(f"integrity_check przed cleanup nie przeszedł: {integrity}")

        page_size, page_count, freelist_count, reclaimable = _database_report(connection)

        print(f"Database: {database_path}")
        print(f"File size before: {before_size:,} bytes")
        print(f"Page size: {page_size:,} bytes")
        print(f"Page count: {page_count:,}")
        print(f"Free pages: {freelist_count:,}")
        print(f"Potential reclaim from free pages: {reclaimable:,} bytes")

        if not apply:
            return before_size, before_size, reclaimable, time.perf_counter() - started

        if backup_path is not None:
            backup_path = backup_path.resolve()
            if backup_path == database_path:
                raise DatabaseCleanupError("Ścieżka backupu nie może wskazywać na project.db.")
            if backup_path.exists():
                raise DatabaseCleanupError(f"Backup już istnieje: {backup_path}")
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(database_path, backup_path)
            print(f"Backup created: {backup_path}")

        connection.execute("VACUUM")
        connection.commit()

        integrity_after = _integrity_check(connection)
        if integrity_after != "ok":
            raise DatabaseCleanupError(f"integrity_check po VACUUM nie przeszedł: {integrity_after}")
    finally:
        connection.close()

    after_size = database_path.stat().st_size
    elapsed = time.perf_counter() - started
    return before_size, after_size, reclaimable, elapsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bezpiecznie sprawdza i kompresuje SQLite project.db przez VACUUM."
    )
    parser.add_argument("database", type=Path, help="Ścieżka do project.db")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Wykonaj VACUUM i zmniejsz fizyczny rozmiar pliku. Bez tej opcji tylko raport.",
    )
    parser.add_argument(
        "--backup",
        type=Path,
        help="Opcjonalna ścieżka kopii bezpieczeństwa wykonywanej przed VACUUM.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        before, after, reclaimable, elapsed = cleanup_database(
            args.database,
            apply=args.apply,
            backup_path=args.backup,
        )
    except (OSError, sqlite3.Error, DatabaseCleanupError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Potential reclaim before cleanup: {reclaimable:,} bytes")
    if args.apply:
        saved = max(0, before - after)
        print(f"File size after: {after:,} bytes")
        print(f"Space reclaimed: {saved:,} bytes")
        print(f"Elapsed: {elapsed:.3f}s")
        print("Integrity check: OK")
        print("Mode: APPLY — database was rebuilt with VACUUM.")
    else:
        print("Mode: REPORT — database was not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
