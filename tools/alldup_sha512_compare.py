"""Compare a sample of AI-Sorter SHA512 values against AllDup's hasha table.

Usage:
    python tools/alldup_sha512_compare.py "C:\\Users\\PC\\AppData\\Roaming\\AllDup\\db\\checksum.adb" "C:\\path\\to\\project.db" [sample_size]

Both databases are opened read-only. No checksums are recalculated and no database is modified.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this script directly from the repository root.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_sorter.core.alldup_inspector import AllDupDatabaseInspector  # noqa: E402


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print(
            "Użycie:\n"
            "  python tools/alldup_sha512_compare.py <checksum.adb> <project.db> [sample_size]"
        )
        return 2

    alldup_path = Path(sys.argv[1])
    project_path = Path(sys.argv[2])
    sample_size = int(sys.argv[3]) if len(sys.argv) == 4 else 50

    try:
        result = AllDupDatabaseInspector().correlate_project_db(
            alldup_path,
            project_path,
            sample_size=sample_size,
        )
    except (ValueError, RuntimeError) as exc:
        print(f"Błąd: {exc}")
        return 1

    print(result.format_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
