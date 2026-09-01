"""Read-only aggregate checksum statistics for an AllDup SQLite database."""
from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path

HASH_TABLES = (("hasha", "algo"), ("hashc", "ctype"), ("hashp", "ctype"))

@dataclass(frozen=True, slots=True)
class ChecksumStat:
    table: str
    kind_column: str
    kind_value: int | None
    checksum_bytes: int | None
    rows: int
    non_null: int

@dataclass(frozen=True, slots=True)
class ChecksumStats:
    database_path: Path
    database_size_bytes: int
    table_rows: dict[str, int]
    stats: tuple[ChecksumStat, ...]

    @property
    def sha512_hashc_rows(self) -> int:
        return sum(r.rows for r in self.stats if r.table == "hashc" and r.kind_value == 5 and r.checksum_bytes == 64)

    def format_text(self) -> str:
        lines = [
            "AllDup checksum statistics", "", f"Database: {self.database_path}",
            f"Database size: {self.database_size_bytes:,} bytes", "", "Table totals:",
        ]
        for table, count in self.table_rows.items():
            lines.append(f"  {table}: {count:,}")
        lines.extend(("", "Checksum distributions (grouped by type and BLOB length):"))
        for table in ("hasha", "hashc", "hashp"):
            lines.append(f"  [{table}]")
            table_stats = [r for r in self.stats if r.table == table]
            if not table_stats:
                lines.append("    none")
                continue
            for row in table_stats:
                kind = "NULL" if row.kind_value is None else str(row.kind_value)
                length = "NULL" if row.checksum_bytes is None else str(row.checksum_bytes)
                lines.append(f"    {row.kind_column}={kind} | checksum_bytes={length} | rows={row.rows:,} | non_null={row.non_null:,}")
        lines.extend(("", "SHA-512 candidate:", f"  hashc.ctype=5 + 64-byte checksum rows: {self.sha512_hashc_rows:,}", "", "Safety: database opened read-only; no schema or data writes are performed."))
        return "\n".join(lines)

def _connect_read_only(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ValueError(f"Nie znaleziono bazy AllDup: {path}")
    with path.open("rb") as stream:
        if stream.read(16) != b"SQLite format 3\x00":
            raise ValueError(f"Plik nie wygląda na bazę SQLite: {path}")
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection

def collect_stats(path: Path) -> ChecksumStats:
    path = path.resolve()
    connection = _connect_read_only(path)
    try:
        table_rows = {}
        for table in ("files", "hasha", "hashc", "hashp"):
            table_rows[table] = int(connection.execute(f'SELECT COUNT(*) AS count FROM "{table}"').fetchone()["count"])
        stats = []
        for table, kind_column in HASH_TABLES:
            rows = connection.execute(f"SELECT {kind_column} AS kind_value, length(checksum) AS checksum_bytes, COUNT(*) AS row_count, SUM(CASE WHEN checksum IS NOT NULL THEN 1 ELSE 0 END) AS non_null FROM {table} GROUP BY {kind_column}, length(checksum) ORDER BY {kind_column}, length(checksum)").fetchall()
            stats.extend(ChecksumStat(table, kind_column, int(r["kind_value"]) if r["kind_value"] is not None else None, int(r["checksum_bytes"]) if r["checksum_bytes"] is not None else None, int(r["row_count"]), int(r["non_null"] or 0)) for r in rows)
        return ChecksumStats(path, path.stat().st_size, table_rows, tuple(stats))
    finally:
        connection.close()

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect aggregate checksum/type statistics in an AllDup database (read-only).")
    parser.add_argument("alldup_db", type=Path)
    args = parser.parse_args(argv)
    try:
        print(collect_stats(args.alldup_db).format_text())
        return 0
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
