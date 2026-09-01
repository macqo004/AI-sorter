"""CLI entry point for Image Dimensions metadata extraction."""

from __future__ import annotations

import argparse
from pathlib import Path

from .core.database import Database, DatabaseError
from .modules.image_dimensions import DimensionProgress, ImageDimensions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Populate missing image width/height metadata in the AI-Sorter database."
    )
    parser.add_argument("database", type=Path, help="Path to the AI-Sorter SQLite database")
    parser.add_argument("--workers", type=int, default=0, help="Worker count (0 = automatic)")
    parser.add_argument("--batch-size", type=int, default=256, help="Database update batch size")
    parser.add_argument("--no-progress", action="store_true", help="Suppress progress output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    database = Database(args.database)
    try:
        database.open()
        module = ImageDimensions(database, worker_count=args.workers, batch_size=args.batch_size)

        def progress(item: DimensionProgress) -> None:
            if args.no_progress:
                return
            if item.total:
                percent = item.processed / item.total * 100.0
                print(
                    f"\rImage Dimensions: {item.processed:,}/{item.total:,} "
                    f"({percent:6.2f}%) | updated {item.updated:,} | errors {item.failed:,}",
                    end="",
                    flush=True,
                )

        summary = module.run(progress)
        if not args.no_progress:
            print()
        print("Image Dimensions")
        print(f"Considered: {summary.considered}")
        print(f"Processed: {summary.processed}")
        print(f"Updated: {summary.updated}")
        print(f"Errors: {summary.failed}")
        print(f"Cancelled: {summary.cancelled}")
        print(f"Elapsed: {summary.elapsed_seconds:.3f}s")
        if summary.elapsed_seconds > 0:
            print(f"Rate: {summary.processed / summary.elapsed_seconds:.1f} files/s")
        return 0
    except (DatabaseError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())
