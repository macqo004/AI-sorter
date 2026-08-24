"""Diagnostic comparison of AI-Sorter and AllDup checksums.

Both databases are opened read-only. For a small sample of paths that exist in
both databases, the tool prints every checksum row from AllDup's hasha/hashc/hashp
tables and recomputes SHA-512 directly from the file on disk.
"""

from __future__ import annotations

import hashlib
import sys
import sqlite3
from pathlib import Path

from .core.alldup_inspector import AllDupDatabaseInspector


def _sha512_from_disk(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb", buffering=1024 * 1024) as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _connect_ro(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print(
            "Użycie:\n"
            "  python -m ai_sorter.alldup_checksum_details <checksum.adb> <project.db> [details_count]"
        )
        return 2

    alldup_path = Path(sys.argv[1]).resolve()
    project_path = Path(sys.argv[2]).resolve()
    details_count = max(1, min(25, int(sys.argv[3])) if len(sys.argv) == 4 else 10)

    if not alldup_path.is_file():
        print(f"Błąd: nie znaleziono bazy AllDup: {alldup_path}")
        return 1
    if not project_path.is_file():
        print(f"Błąd: nie znaleziono bazy projektu: {project_path}")
        return 1

    inspector = AllDupDatabaseInspector()
    try:
        project = _connect_ro(project_path)
        alldup = _connect_ro(alldup_path)
        try:
            samples = project.execute(
                """
                SELECT fl.absolute_path, fl.sha512
                FROM file_location fl
                JOIN file_record fr ON fr.sha512 = fl.sha512
                WHERE fl.location_status = 'ACTIVE'
                  AND fr.status = 'ACTIVE'
                ORDER BY RANDOM()
                LIMIT 500
                """,
            ).fetchall()

            print("AllDup ↔ AI-Sorter checksum diagnostic")
            print("Safety: both databases are read-only; no database writes are performed.")
            print(f"Requested detailed files: {details_count}")
            print()

            detailed = 0
            for sample in samples:
                if detailed >= details_count:
                    break
                path_text = str(sample["absolute_path"])
                our_sha = str(sample["sha512"]).lower()
                path = Path(path_text)

                files = alldup.execute(
                    "SELECT id, file FROM files WHERE lower(file) = lower(?) LIMIT 1",
                    (path_text,),
                ).fetchone()
                if files is None:
                    continue

                fileid = int(files["id"])
                actual_sha = None
                actual_status = "NOT READ"
                try:
                    actual_sha = _sha512_from_disk(path)
                    actual_status = "MATCH" if actual_sha == our_sha else "MISMATCH"
                except OSError as exc:
                    actual_status = f"READ ERROR: {exc}"

                print(f"FILE #{detailed + 1}")
                print(f"Path: {path_text}")
                print(f"AllDup fileid: {fileid}")
                print(f"AI-Sorter SHA512: {our_sha}")
                print(f"Actual SHA512:    {actual_sha or '—'}")
                print(f"Scanner vs disk:  {actual_status}")

                for table in ("hasha", "hashc", "hashp"):
                    if table == "hasha":
                        query = "SELECT algo AS kind, checksum FROM hasha WHERE fileid = ? ORDER BY id"
                        kind_name = "algo"
                    else:
                        query = "SELECT ctype AS kind, checksum FROM " + table + " WHERE fileid = ? ORDER BY id"
                        kind_name = "ctype"
                    rows = alldup.execute(query, (fileid,)).fetchall()
                    print(f"{table}: {len(rows)} row(s)")
                    for row in rows:
                        blob = row["checksum"]
                        if blob is None:
                            length = 0
                            hex_value = "NULL"
                        else:
                            raw = blob if isinstance(blob, bytes) else bytes(blob)
                            length = len(raw)
                            hex_value = raw.hex()
                        relation = ""
                        if actual_sha and hex_value != "NULL" and hex_value.casefold() == actual_sha.casefold():
                            relation = "  <-- MATCHES DISK SHA512"
                        print(f"  {kind_name}={row['kind']} | bytes={length} | hex={hex_value}{relation}")

                print()
                detailed += 1

            if detailed == 0:
                print("Nie znaleziono żadnego wspólnego pliku do szczegółowej analizy.")
                return 1
            print(f"Detailed files analyzed: {detailed}")
            return 0
        finally:
            project.close()
            alldup.close()
    except (sqlite3.Error, ValueError, RuntimeError) as exc:
        print(f"Błąd: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
