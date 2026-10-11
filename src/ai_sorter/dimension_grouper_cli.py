"""CLI entry point for dimension-based image folder grouping."""

from __future__ import annotations

import argparse
from pathlib import Path

from .core.database import Database, DatabaseError
from .modules.dimension_grouper import DimensionGrouper, GroupingProgress


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Group image files into folders named WIDTHxHEIGHT."
    )
    parser.add_argument("database", type=Path, help="Path to the AI-Sorter SQLite database")
    parser.add_argument("root", type=Path, help="Folder containing images to group")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Move files. Without this flag, only show the plan.",
    )
    parser.add_argument("--batch-size", type=int, default=256, help="Files per database synchronization batch")
    parser.add_argument("--no-progress", action="store_true", help="Suppress progress output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    database = Database(args.database)

    try:
        database.open()
        module = DimensionGrouper(database, args.root, batch_size=args.batch_size)

        def progress(item: GroupingProgress) -> None:
            if args.no_progress:
                return
            phase = "Planning" if item.phase == "planning" else "Grouping"
            suffix = f"/{item.total:,}" if item.total > 0 else ""
            print(
                f"\r{phase}: {item.processed:,}{suffix} | "
                f"moved {item.moved:,} | skipped {item.skipped:,} | errors {item.failed:,}",
                end="",
                flush=True,
            )

        plan = module.plan(progress)
        if not args.no_progress:
            print()
        print("Dimension Grouping plan")
        print(f"Folder: {plan.root}")
        print(f"Images inspected: {plan.considered:,}")
        print(f"Proposed moves: {plan.planned_moves:,}")
        print(f"Unreadable images: {plan.unreadable:,}")
        print(f"Existing destination conflicts: {plan.destination_conflicts:,}")
        print("Dimension groups:")
        for dimension, count in sorted(plan.by_dimension.items(), key=lambda item: (-item[1], item[0])):
            print(f"  {dimension}: {count:,}")

        if plan.cancelled:
            print("Planning cancelled. No files were moved.")
            return 2
        if not args.apply:
            print("Dry run only. Use --apply to move files.")
            return 0

        summary = module.execute(plan, progress)
        if not args.no_progress:
            print()
        print("Dimension Grouping result")
        print(f"Images inspected: {summary.considered:,}")
        print(f"Files moved: {summary.moved:,}")
        print(f"Database locations updated: {summary.database_updated:,}")
        print(f"Database conflicts reconciled: {summary.database_conflicts_reconciled:,}")
        print(f"Skipped because destination exists: {summary.skipped_existing:,}")
        print(f"Unreadable images: {summary.unreadable:,}")
        print(f"Other errors: {summary.failed:,}")
        print(f"Cancelled: {summary.cancelled}")
        print(f"Elapsed: {summary.elapsed_seconds:.3f}s")
        return 0 if not summary.failed and not summary.unreadable else 1
    except (DatabaseError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())
