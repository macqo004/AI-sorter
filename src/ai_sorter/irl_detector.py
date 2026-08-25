"""CLI entry point for the IRL Detector module."""
from __future__ import annotations

import argparse
from pathlib import Path

from .core.database import Database
from .modules.irl_detector import IRLDetector, IRLProgress


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the offline IRL Detector against an indexed folder scope.")
    parser.add_argument("project", type=Path, help="Path to project.db")
    parser.add_argument("folder", type=Path, help="Folder scope; subfolders are included")
    parser.add_argument("--threads", type=int, default=0, help="Worker count (0 = automatic)")
    args = parser.parse_args()

    database = Database(args.project)
    database.open()
    try:
        last_print = {"processed": -1}

        def progress(value: IRLProgress) -> None:
            if value.processed != last_print["processed"]:
                last_print["processed"] = value.processed
                print(
                    f"Processed: {value.processed} | Errors: {value.failed} | "
                    f"Current: {value.current_path or '—'}",
                    end="\r",
                    flush=True,
                )

        summary = IRLDetector(database, worker_count=args.threads, scope_root=args.folder).run(progress)
        print()
        print("IRL Detector finished" if not summary.cancelled else "IRL Detector cancelled")
        print(f"Considered: {summary.considered}")
        print(f"Processed: {summary.processed}")
        print(f"Skipped: {summary.skipped}")
        print(f"Errors: {summary.failed}")
        print(f"Elapsed: {int(summary.elapsed_seconds)} seconds")
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())
