"""Compare a sample of AI-Sorter SHA512 values against AllDup's hasha table."""
from __future__ import annotations

import sys
from pathlib import Path

from ai_sorter.core.alldup_inspector import AllDupDatabaseInspector


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print("Użycie: python -m ai_sorter.tools.alldup_sha512_compare <checksum.adb> <project.db> [sample_size]")
        return 2
    alldup_path = Path(sys.argv[1])
    project_path = Path(sys.argv[2])
    sample_size = int(sys.argv[3]) if len(sys.argv) == 4 else 50
    try:
        result = AllDupDatabaseInspector().correlate_project_db(
            alldup_path, project_path, sample_size=sample_size
        )
    except (ValueError, RuntimeError) as exc:
        print(f"Błąd: {exc}")
        return 1
    print(result.format_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
