"""CLI for dry-run and execution of deterministic filename renames."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .renamer import DEFAULT_RULES, RenamerEngine, iter_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan and execute deterministic filename cleanup rules."
    )
    parser.add_argument("root", type=Path, help="Directory containing files to rename")
    parser.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Scan subdirectories recursively (default: enabled)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually rename files; without this flag the command is a dry-run.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Optional CSV report path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        sources = iter_files(args.root, recursive=args.recursive)
        engine = RenamerEngine(DEFAULT_RULES)
        proposals = engine.plan(sources)

        print("AI-Sorter Renamer")
        print(f"Root: {args.root.resolve()}")
        print(f"Files inspected: {len(sources):,}")
        print(f"Rename proposals: {len(proposals):,}")
        print()
        for proposal in proposals:
            print(f"{proposal.source} -> {proposal.destination} [{proposal.reason}]")

        if args.csv:
            args.csv.parent.mkdir(parents=True, exist_ok=True)
            with args.csv.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.writer(stream, delimiter=";")
                writer.writerow(["source", "destination", "rule", "reason", "status"])
                for proposal in proposals:
                    writer.writerow(
                        [
                            str(proposal.source),
                            str(proposal.destination),
                            proposal.rule_id,
                            proposal.reason,
                            "PLANNED",
                        ]
                    )

        if not args.apply:
            print("Mode: DRY-RUN — no files were renamed.")
            return 0

        executed = engine.execute(proposals)
        print(f"Renamed: {len(executed):,}")
        print("Mode: APPLY — files were renamed.")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
