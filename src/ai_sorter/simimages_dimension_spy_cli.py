"""CLI entry point for the read-only SimImages dimension/fingerprint spy."""

from __future__ import annotations

import argparse
from pathlib import Path

from ai_sorter.core.simimages_dimension_spy import SimImagesDimensionSpy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Probe existing SimImages cache files, read image dimensions, "
            "and look for width/height fields inside m.data."
        )
    )
    parser.add_argument("database", type=Path, help="Path to SimImages Cache.db")
    parser.add_argument("--files", type=int, default=100, help="Readable files to inspect (max 1000)")
    parser.add_argument(
        "--cache-rows",
        type=int,
        default=10000,
        help="Maximum recent cache rows to inspect while looking for existing files",
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = SimImagesDimensionSpy().analyze(
            args.database,
            requested_files=args.files,
            max_cache_rows=args.cache_rows,
            sample_display_count=args.display,
            compute_sha512=args.sha512,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(result.format_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
