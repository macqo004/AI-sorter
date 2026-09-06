from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from ai_sorter.alldup_full_import import ALLDUP_SHA512_CTYPE, AllDupFullImporter
from ai_sorter.core.database import Database
from ai_sorter.core.models import FileLocationRecord
from ai_sorter.modules.scanner import Scanner


SHA_A = "a" * 128
SHA_B = "b" * 128
SHA_C = "c" * 128


class AllDupFullImportTests(unittest.TestCase):
    def _make_alldup(self, path: Path, conflict_path: str | None = None) -> None:
        connection = sqlite3.connect(path)
        try:
            connection.executescript(
                """
                CREATE TABLE files (
                    id INTEGER PRIMARY KEY,
                    file TEXT NOT NULL
                );
                CREATE TABLE hashc (
                    id INTEGER PRIMARY KEY,
                    fileid INTEGER NOT NULL,
                    fsize INTEGER NOT NULL,
                    fdate INTEGER,
                    ctype INTEGER NOT NULL,
                    checksum BLOB
                );
                """
            )
            rows = [
                (1, r"M:\collection\one.jpg"),
                (2, r"N:\archive\same.jpg"),
                (3, r"M:\collection\other.png"),
            ]
            if conflict_path:
                rows.append((4, conflict_path))
            connection.executemany("INSERT INTO files (id, file) VALUES (?, ?)", rows)
            hashes = [
                (1, 1, 100, None, ALLDUP_SHA512_CTYPE, bytes.fromhex(SHA_A)),
                (2, 2, 100, None, ALLDUP_SHA512_CTYPE, bytes.fromhex(SHA_A)),
                (3, 3, 200, None, ALLDUP_SHA512_CTYPE, bytes.fromhex(SHA_B)),
            ]
            if conflict_path:
                hashes.append((4, 4, 300, None, ALLDUP_SHA512_CTYPE, bytes.fromhex(SHA_C)))
            connection.executemany(
                "INSERT INTO hashc (id, fileid, fsize, fdate, ctype, checksum) VALUES (?, ?, ?, ?, ?, ?)",
                hashes,
            )
            connection.commit()
        finally:
            connection.close()

    def test_import_builds_canonical_identity_and_multiple_locations(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            alldup = root / "checksum.adb"
            project_path = root / "project.db"
            self._make_alldup(alldup)

            db = Database(project_path)
            db.open()
            db.close()

            stats = AllDupFullImporter(alldup, project_path, batch_size=2).run(apply=True)
            self.assertEqual(stats.source_rows, 3)
            self.assertEqual(stats.valid_rows, 3)
            self.assertEqual(stats.conflicts, 0)
            self.assertEqual(stats.unique_files, 2)
            self.assertEqual(stats.unique_locations, 3)

            db = Database(project_path)
            db.open()
            try:
                self.assertEqual(db.status().file_count, 2)
                self.assertEqual(db.status().location_count, 3)
                row = db.connection.execute(
                    "SELECT COUNT(*) AS count FROM file_record WHERE sha512 = ?", (SHA_A,)
                ).fetchone()
                self.assertEqual(row["count"], 1)
                row = db.connection.execute(
                    "SELECT COUNT(*) AS count FROM file_location WHERE sha512 = ?", (SHA_A,)
                ).fetchone()
                self.assertEqual(row["count"], 2)
            finally:
                db.close()

    def test_dry_run_does_not_modify_project_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            alldup = root / "checksum.adb"
            project_path = root / "project.db"
            self._make_alldup(alldup)

            db = Database(project_path)
            db.open()
            initial = db.status()
            db.close()

            stats = AllDupFullImporter(alldup, project_path).run(apply=False)
            self.assertEqual(stats.source_rows, 3)

            db = Database(project_path)
            db.open()
            try:
                self.assertEqual(db.status().file_count, initial.file_count)
                self.assertEqual(db.status().location_count, initial.location_count)
            finally:
                db.close()

    def test_import_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            alldup = root / "checksum.adb"
            project_path = root / "project.db"
            self._make_alldup(alldup)
            db = Database(project_path)
            db.open()
            db.close()

            first = AllDupFullImporter(alldup, project_path).run(apply=True)
            second = AllDupFullImporter(alldup, project_path).run(apply=True)
            self.assertEqual(first.unique_files, 2)
            self.assertEqual(second.unique_files, 2)
            self.assertEqual(second.unique_locations, 3)

    def test_path_conflict_does_not_replace_existing_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            alldup = root / "checksum.adb"
            project_path = root / "project.db"
            conflict = r"M:\collection\conflict.jpg"
            self._make_alldup(alldup, conflict)
            db = Database(project_path)
            db.open()
            try:
                db.upsert_file_location(FileLocationRecord(
                    sha512=SHA_A,
                    absolute_path=conflict,
                    file_size=100,
                ))
            finally:
                db.close()

            stats = AllDupFullImporter(alldup, project_path).run(apply=True)
            self.assertEqual(stats.conflicts, 1)
            db = Database(project_path)
            db.open()
            try:
                owner = db.connection.execute(
                    "SELECT sha512 FROM file_location WHERE absolute_path = ?", (conflict,)
                ).fetchone()[0]
                self.assertEqual(owner, SHA_A)
            finally:
                db.close()

    def test_imported_hashc_timestamp_allows_scanner_to_skip_rehash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "one.jpg"
            image.write_bytes(b"stable-content")
            stat = image.stat()
            modified = datetime.fromtimestamp(stat.st_mtime).replace(microsecond=0)
            filetime = int((modified.timestamp() + 11644473600) * 10_000_000)

            alldup = root / "checksum.adb"
            connection = sqlite3.connect(alldup)
            try:
                connection.executescript(
                    """
                    CREATE TABLE files (id INTEGER PRIMARY KEY, file TEXT NOT NULL);
                    CREATE TABLE hashc (
                        id INTEGER PRIMARY KEY,
                        fileid INTEGER,
                        fsize INTEGER,
                        fdate INTEGER,
                        ctype INTEGER,
                        checksum BLOB
                    );
                    """
                )
                connection.execute("INSERT INTO files (id, file) VALUES (?, ?)", (1, str(image)))
                connection.execute(
                    "INSERT INTO hashc (id, fileid, fsize, fdate, ctype, checksum) VALUES (?, ?, ?, ?, ?, ?)",
                    (1, 1, stat.st_size, filetime, ALLDUP_SHA512_CTYPE, bytes.fromhex(SHA_A)),
                )
                connection.commit()
            finally:
                connection.close()

            project_path = root / "project.db"
            db = Database(project_path)
            db.open()
            db.close()
            stats = AllDupFullImporter(alldup, project_path).run(apply=True)
            self.assertEqual(stats.timestamped_rows, 1)

            db = Database(project_path)
            db.open()
            imported = db.connection.execute(
                "SELECT modified_at FROM file_location WHERE absolute_path = ?", (str(image),)
            ).fetchone()[0]
            db.close()
            self.assertEqual(imported, modified.isoformat(sep=" "))

            db = Database(project_path)
            db.open()
            try:
                summary = Scanner(db, worker_count=1).scan(root)
            finally:
                db.close()
            self.assertEqual(summary.skipped, 1)
            self.assertEqual(summary.scanned, 0)
            self.assertEqual(summary.failed, 0)


if __name__ == "__main__":
    unittest.main()
