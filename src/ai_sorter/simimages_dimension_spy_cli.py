"""CLI entry point for the read-only SimImages dimension/fingerprint spy."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from ai_sorter.core.simimages_dimension_spy import SimImagesDimensionSpy


# SQLite installations commonly cap the number of bound variables well below
# the 50k IDs produced by the whole-cache stratified sampler. Keep IN() below
# that limit by issuing several bounded queries and merging the rows.
_SQL_VARIABLE_CHUNK = 500
_FAST_CACHE_ROWS = 2_000
_FAST_FILES = 100


def _sample_cache_rows_chunked(
    connection: sqlite3.Connection,
    total_rows: int | None,
    limit: int,
) -> list[sqlite3.Row]:
    columns = """
        m.id AS mid, d.drive AS drive_record, f.folder AS folder,
        m.file AS file_name, m.size AS cache_size, m.time AS cache_time,
        m.data AS data
    """
    if not total_rows or total_rows <= limit:
        return connection.execute(
            f"SELECT {columns} FROM m JOIN f ON f.id=m.fid JOIN d ON d.id=f.did ORDER BY m.id"
        ).fetchall()

    min_id, max_id = connection.execute("SELECT MIN(id), MAX(id) FROM m").fetchone()
    if min_id is None or max_id is None:
        return []

    step = (int(max_id) - int(min_id)) / float(limit)
    unique_ids = sorted(
        {
            int(round(int(min_id) + index * step))
            for index in range(limit)
        }
    )

    collected: list[sqlite3.Row] = []
    for start in range(0, len(unique_ids), _SQL_VARIABLE_CHUNK):
        chunk = unique_ids[start : start + _SQL_VARIABLE_CHUNK]
        placeholders = ",".join("?" for _ in chunk)
        collected.extend(
            connection.execute(
                f"""SELECT {columns}
                    FROM m JOIN f ON f.id=m.fid JOIN d ON d.id=f.did
                    WHERE m.id IN ({placeholders})""",
                tuple(chunk),
            ).fetchall()
        )

    collected.sort(key=lambda row: int(row["mid"]))
    return collected


def _install_chunked_sampler() -> None:
    # The core spy is also used by the GUI. For now the CLI installs a bounded
    # sampler so the installed executable can handle large --cache-rows values
    # without changing the analysis logic itself.
    SimImagesDimensionSpy._sample_cache_rows = staticmethod(_sample_cache_rows_chunked)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Probe existing SimImages cache files, read image dimensions, "
            "and reverse-engineer the m.data fingerprint payload."
        )
    )
    parser.add_argument("database", type=Path, help="Path to SimImages Cache.db")
    parser.add_argument("--files", type=int, default=100, help="Readable files to inspect (max 1000)")
    parser.add_argument(
        "--cache-rows",
        type=int,
        default=10000,
        help="Maximum cache rows to sample across the whole m.id range",
    )
    parser.add_argument(
        "--display",
        type=int,
        default=25,
        help="Number of image samples to print with full m.data payload",
    )
    parser.add_argument(
        "--sha512",
        action="store_true",
        help="Also calculate SHA-512 for the small inspected sample",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help=(
            f"Fast exploratory run: at most {_FAST_CACHE_ROWS:,} cache rows and "
            f"{_FAST_FILES} readable images; SHA-512 is disabled."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    _install_chunked_sampler()
    args = build_parser().parse_args(argv)
    files = args.files
    cache_rows = args.cache_rows
    sha512 = args.sha512
    if args.fast:
        files = min(files, _FAST_FILES)
        cache_rows = min(cache_rows, _FAST_CACHE_ROWS)
        sha512 = False
        print(
            f"FAST MODE: max {cache_rows:,} cache rows, max {files} readable images, SHA-512 disabled"
        )
    try:
        result = SimImagesDimensionSpy().analyze(
            args.database,
            requested_files=files,
            max_cache_rows=cache_rows,
            sample_display_count=args.display,
            compute_sha512=sha512,
        )
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(result.format_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
