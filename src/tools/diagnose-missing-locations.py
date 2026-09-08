from __future__ import annotations

import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path


DEFAULT_DB = Path(r"P:\ai-sorter\data\project.db")
DRIVE_RE = re.compile(r"^([A-Za-z]:)[\\/]")
LETTER_DIR_RE = re.compile(r"[\\/]([A-Za-z])[\\/]")


def main() -> int:
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 2

    try:
        connection = sqlite3.connect(db_path)
    except sqlite3.Error as exc:
        print(f"Could not open database: {exc}")
        return 2

    try:
        connection.row_factory = sqlite3.Row
        print(f"Database: {db_path}")
        print()

        print("Status counts:")
        for row in connection.execute(
            "SELECT location_status, COUNT(*) AS count "
            "FROM file_location GROUP BY location_status ORDER BY location_status"
        ):
            print(f"  {row['location_status']}: {row['count']:,}")

        print()
        print("Root/status counts:")
        for row in connection.execute(
            "SELECT substr(absolute_path, 1, 3) AS root, location_status, COUNT(*) AS count "
            "FROM file_location "
            "GROUP BY root, location_status "
            "ORDER BY root, location_status"
        ):
            print(f"  {row['root']!r:6} {row['location_status']:<8} {row['count']:,}")

        rows = connection.execute(
            "SELECT absolute_path "
            "FROM file_location "
            "WHERE location_status = 'MISSING' "
            "ORDER BY absolute_path"
        ).fetchall()

        print()
        print(f"MISSING locations: {len(rows):,}")
        if not rows:
            return 0

        drive_counts: Counter[str] = Counter()
        letter_counts: Counter[str] = Counter()
        suspicious: list[tuple[str, str]] = []

        for row in rows:
            path = row["absolute_path"]
            drive = DRIVE_RE.match(path)
            drive_counts[drive.group(1).upper() if drive else "<other>"] += 1

            match = LETTER_DIR_RE.search(path)
            if match:
                letter_counts[match.group(1).lower()] += 1

            for pair in ("\\a", "\\b", "\\f", "\\n", "\\r", "\\t", "\\v"):
                if pair in path:
                    suspicious.append((pair, path))
                    break

        print()
        print("MISSING by drive:")
        for drive, count in sorted(drive_counts.items()):
            print(f"  {drive:<8} {count:,}")

        print()
        print("MISSING by first single-letter directory occurrence:")
        for letter, count in sorted(letter_counts.items()):
            print(f"  {letter}: {count:,}")

        print()
        print("First 100 MISSING paths:")
        for row in rows[:100]:
            print(row["absolute_path"])

        print()
        print(f"Paths containing a backslash + escape-like letter: {len(suspicious):,}")
        for pair, path in suspicious[:100]:
            print(f"  {pair!r}  {path!r}")

        print()
        print("Exact stored path representations (repr) for first 20 MISSING rows:")
        for row in rows[:20]:
            path = row["absolute_path"]
            print(repr(path))

    finally:
        connection.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
