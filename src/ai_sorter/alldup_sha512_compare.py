"""Compare AI-Sorter SHA512 values against AllDup without modifying either database."""
from __future__ import annotations

import sys
from pathlib import Path

from .core.alldup_inspector import AllDupDatabaseInspector


def main() -> int:
    if len(sys.argv) < 3 or len(sys.argv) > 5:
        print(
            "Użycie: ai-sorter-alldup-sha512 <checksum.adb> <project.db> [sample_size] [--verify-disk]"
        )
        return 2

    alldup_path = Path(sys.argv[1])
    project_path = Path(sys.argv[2])
    sample_size = 50
    verify_disk = False

    for argument in sys.argv[3:]:
        if argument == "--verify-disk":
            verify_disk = True
        else:
            sample_size = int(argument)

    try:
        result = AllDupDatabaseInspector().correlate_project_db(
            alldup_path,
            project_path,
            sample_size=sample_size,
            verify_disk=verify_disk,
        )
    except (ValueError, RuntimeError) as exc:
        print(f"Błąd: {exc}")
        return 1

    print(result.format_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
