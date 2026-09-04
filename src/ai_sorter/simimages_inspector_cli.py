"""CLI entry point for inspecting a SimImages SQLite cache read-only."""

from __future__ import annotations

import argparse
from pathlib import Path

from ai_sorter.core.simimages_inspector import SimImagesDatabaseInspector


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect a SimImages SQLite cache without modifying it."
    )
    parser.add_argument("database", type=Path, help="Path to SimImages Cache.db")
    parser.add_argument(
        "--count-rows",
        action="store_true",
        help="Count rows in every table. This can be expensive on very large tables.",
    )
    parser.add_argument(
        "--no-samples",
        action="store_true",
        help="Do not read sample rows.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    inspector = SimImagesDatabaseInspector()
    try:
        result = inspector.inspect(
            args.database,
            count_rows=args.count_rows,
            sample_rows=0 if args.no_samples else 3,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(result.format_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
