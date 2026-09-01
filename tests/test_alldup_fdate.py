from __future__ import annotations

import os
import sqlite3
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ai_sorter.alldup_full_import import ALLDUP_SHA512_CTYPE


def _as_epoch_seconds(value: object) -> float | None:
    """Convert known AllDup/SQLite date representations to Unix seconds."""
    if value is None:
        return None

    if isinstance(value, memoryview):
        value = value.tobytes()

    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            return None

    if isinstance(value, (int, float)):
        number = float(value)
        if number <= 0:
            return None

        # Unix timestamps in seconds / milliseconds / microseconds / nanoseconds.
        for divisor in (1.0, 1_000.0, 1_000_000.0, 1_000_000_000.0):
            candidate = number / divisor
            if 315532800 <= candidate <= 4102444800:  # 1980-01-01 .. 2100-01-01
                return candidate

        # Delphi TDateTime / OLE Automation date: days since 1899-12-30.
        if 20000 <= number <= 100000:
            return (number - 25569.0) * 86400.0
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


class AllDupFdateTests(unittest.TestCase):
    """Integration test against a real AllDup checksum database.

    Set ALLDUP_DB to the path of a copied/read-only checksum.adb before running
    this test. It deliberately never writes to the AllDup database.
    """

    def test_hashc_fdate_matches_filesystem_modification_time(self) -> None:
        database_path = Path(os.environ["ALLDUP_DB"])
        self.assertTrue(database_path.is_file(), f"AllDup database not found: {database_path}")

        connection = sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                """
                SELECT f.file AS absolute_path,
                       h.fdate AS alldup_fdate
                FROM hashc AS h
                JOIN files AS f ON f.id = h.fileid
                WHERE h.ctype = ?
                  AND f.file IS NOT NULL
                  AND h.fdate IS NOT NULL
                ORDER BY h.id
                LIMIT 200
                """,
                (ALLDUP_SHA512_CTYPE,),
            ).fetchall()
        finally:
            connection.close()

        checked = 0
        failures: list[str] = []

        for row in rows:
            path = Path(str(row["absolute_path"]))
            if not path.is_file():
                continue

            try:
                filesystem_mtime = path.stat().st_mtime
            except OSError:
                continue

            alldup_mtime = _as_epoch_seconds(row["alldup_fdate"])
            if alldup_mtime is None:
                failures.append(f"{path}: unsupported fdate representation {row['alldup_fdate']!r}")
                continue

            checked += 1
            delta = abs(filesystem_mtime - alldup_mtime)
            if delta > 2.0:
                failures.append(
                    f"{path}: filesystem={filesystem_mtime:.3f}, "
                    f"AllDup fdate={row['alldup_fdate']!r} -> {alldup_mtime:.3f}, "
                    f"delta={delta:.3f}s"
                )

            if len(failures) >= 10:
                break

        self.assertGreaterEqual(
            checked,
            10,
            "Not enough existing files with hashc.ctype=5 were available for the fdate check.",
        )
        self.assertFalse(
            failures,
            "AllDup hashc.fdate does not consistently match filesystem modification time:\n"
            + "\n".join(failures),
        )


if __name__ == "__main__":
    unittest.main()
