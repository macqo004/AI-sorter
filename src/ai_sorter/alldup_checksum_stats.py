"""Read-only aggregate checksum statistics for an AllDup SQLite database."""
from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path

HASH_TABLES = (("hasha", "algo"), ("hashc", "ctype"), ("hashp", "ctype"))
SHA512_WHERE = "ctype = 5 AND length(checksum) = 64 AND checksum IS NOT NULL"


@dataclass(frozen=True, slots=True)
class ChecksumStat:
    table: str
    kind_column: str
    kind_value: int | None
    checksum_bytes: int | None
    rows: int
    non_null: int


@dataclass(frozen=True, slots=True)
class Sha512Audit:
    rows: int
    distinct_files: int
    distinct_sha512: int
    duplicate_groups: int | None = None
    duplicate_file_excess: int | None = None
    max_group_size: int | None = None


@dataclass(frozen=True, slots=True)
class ChecksumStats:
    database_path: Path
    database_size_bytes: int
    table_rows: dict[str, int]
    stats: tuple[ChecksumStat, ...]
    sha512_audit: Sha512Audit

    @property
    def sha512_hashc_rows(self) -> int:
        return self.sha512_audit.rows

    def format_text(self, include_distribution: bool = False) -> str:
        lines = [
            "AllDup checksum statistics",
            "",
            f"Database: {self.database_path}",
            f"Database size: {self.database_size_bytes:,} bytes",
            "",
            "Table totals:",
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
                lines.append(
                    f"    {row.kind_column}={kind} | checksum_bytes={length} | "
                    f"rows={row.rows:,} | non_null={row.non_null:,}"
                )

        audit = self.sha512_audit
        lines.extend(
            (
                "",
                "SHA-512 audit (hashc.ctype=5, 64-byte checksum):",
                f"  checksum rows: {audit.rows:,}",
                f"  distinct files: {audit.distinct_files:,}",
                f"  unique SHA-512 values: {audit.distinct_sha512:,}",
                f"  extra rows over unique SHA: {audit.rows - audit.distinct_sha512:,}",
            )
        )

        if include_distribution:
            lines.extend(
                (
                    "",
                    "SHA-512 duplicate distribution:",
                    f"  duplicate SHA-512 groups: {audit.duplicate_groups:,}",
                    f"  duplicate file excess: {audit.duplicate_file_excess:,}",
                    f"  largest SHA-512 group: {audit.max_group_size:,} files",
                )
            )
        else:
            lines.extend(("", "Duplicate distribution: not calculated (use --distribution)."))

        lines.extend(("", "Safety: database opened read-only; no schema or data writes are performed."))
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


def _collect_sha512_audit(connection: sqlite3.Connection, include_distribution: bool) -> Sha512Audit:
    row = connection.execute(
        f"SELECT COUNT(*) AS rows, COUNT(DISTINCT fileid) AS distinct_files, "
        f"COUNT(DISTINCT checksum) AS distinct_sha512 FROM hashc WHERE {SHA512_WHERE}"
    ).fetchone()
    if row is None:
        raise RuntimeError("Nie udało się odczytać statystyk SHA-512 z AllDup.")

    if not include_distribution:
        return Sha512Audit(
            rows=int(row["rows"]),
            distinct_files=int(row["distinct_files"]),
            distinct_sha512=int(row["distinct_sha512"]),
        )

    duplicate = connection.execute(
        f"SELECT COUNT(*) AS duplicate_groups, "
        f"COALESCE(SUM(group_size - 1), 0) AS duplicate_file_excess, "
        f"COALESCE(MAX(group_size), 0) AS max_group_size FROM ("
        f"SELECT checksum, COUNT(*) AS group_size FROM hashc WHERE {SHA512_WHERE} "
        "GROUP BY checksum HAVING COUNT(*) > 1)"
    ).fetchone()
    if duplicate is None:
        raise RuntimeError("Nie udało się odczytać rozkładu duplikatów SHA-512.")

    return Sha512Audit(
        rows=int(row["rows"]),
        distinct_files=int(row["distinct_files"]),
        distinct_sha512=int(row["distinct_sha512"]),
        duplicate_groups=int(duplicate["duplicate_groups"]),
        duplicate_file_excess=int(duplicate["duplicate_file_excess"]),
        max_group_size=int(duplicate["max_group_size"]),
    )


def collect_stats(path: Path, include_distribution: bool = False) -> ChecksumStats:
    path = path.resolve()
    connection = _connect_read_only(path)
    try:
        table_rows = {}
        for table in ("files", "hasha", "hashc", "hashp"):
            table_rows[table] = int(
                connection.execute(f'SELECT COUNT(*) AS count FROM "{table}"').fetchone()["count"]
            )

        stats = []
        for table, kind_column in HASH_TABLES:
            rows = connection.execute(
                f"SELECT {kind_column} AS kind_value, length(checksum) AS checksum_bytes, "
                f"COUNT(*) AS row_count, SUM(CASE WHEN checksum IS NOT NULL THEN 1 ELSE 0 END) AS non_null "
                f"FROM {table} GROUP BY {kind_column}, length(checksum) ORDER BY {kind_column}, length(checksum)"
            ).fetchall()
            stats.extend(
                ChecksumStat(
                    table,
                    kind_column,
                    int(r["kind_value"]) if r["kind_value"] is not None else None,
                    int(r["checksum_bytes"]) if r["checksum_bytes"] is not None else None,
                    int(r["row_count"]),
                    int(r["non_null"] or 0),
                )
                for r in rows
            )

        sha512_audit = _collect_sha512_audit(connection, include_distribution)
        return ChecksumStats(path, path.stat().st_size, table_rows, tuple(stats), sha512_audit)
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect aggregate checksum/type statistics in an AllDup database (read-only)."
    )
    parser.add_argument("alldup_db", type=Path)
    parser.add_argument(
        "--distribution",
        action="store_true",
        help="Calculate the full SHA-512 duplicate-group distribution (more expensive).",
    )
    args = parser.parse_args(argv)
    try:
        print(collect_stats(args.alldup_db, include_distribution=args.distribution).format_text(args.distribution))
        return 0
    except (OSError, sqlite3.Error, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
