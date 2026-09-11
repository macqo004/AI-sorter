"""Repair one database location after a successful filesystem rename.

Usage:
    python repair-renamer-destination.py project.db "M:\\z\\JPG\\0\\0c80b2f867453c0f055492754621da.jpg" --apply

The tool hashes the real file, removes conflicting database location rows at
that exact path when the real SHA-512 is known to the project DB, restores the
correct location row, and marks other locations for the same SHA as MISSING
when their files no longer exist.
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path


def sha512_file(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_db", type=Path)
    parser.add_argument("path", type=Path)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_db = args.project_db.resolve()
    path = args.path.resolve()

    if not project_db.is_file():
        print(f"ERROR: database does not exist: {project_db}")
        return 1
    if not path.is_file():
        print(f"ERROR: file does not exist: {path}")
        return 1

    actual_sha = sha512_file(path)
    file_size = path.stat().st_size
    modified_at = datetime.fromtimestamp(path.stat().st_mtime).replace(microsecond=0).isoformat(sep=" ")

    connection = sqlite3.connect(project_db)
    connection.row_factory = sqlite3.Row
    try:
        destination_rows = connection.execute(
            "SELECT sha512, absolute_path, location_status FROM file_location WHERE absolute_path = ?",
            (str(path),),
        ).fetchall()
        file_record = connection.execute(
            "SELECT sha512, size_bytes, status FROM file_record WHERE sha512 = ?",
            (actual_sha,),
        ).fetchone()
        same_sha_locations = connection.execute(
            "SELECT sha512, absolute_path, location_status FROM file_location WHERE sha512 = ?",
            (actual_sha,),
        ).fetchall()

        print("Renamer DB destination repair")
        print(f"Database: {project_db}")
        print(f"File:     {path}")
        print(f"Size:     {file_size}")
        print(f"SHA-512:  {actual_sha}")
        print(f"Destination DB rows: {len(destination_rows)}")
        for row in destination_rows:
            print(f"  DB: {row['sha512']} | {row['location_status']} | {row['absolute_path']}")
        print(f"Matching file_record: {'yes' if file_record else 'no'}")
        print(f"Locations for actual SHA: {len(same_sha_locations)}")

        if not file_record:
            print("ERROR: actual SHA-512 is not present in file_record; no DB changes made.")
            return 2

        stale_same_sha = []
        for row in same_sha_locations:
            location = Path(row["absolute_path"])
            if not location.is_file():
                stale_same_sha.append(row["absolute_path"])
        print(f"Non-existing locations for actual SHA: {len(stale_same_sha)}")
        for location in stale_same_sha[:20]:
            print(f"  MISSING candidate: {location}")
        if len(stale_same_sha) > 20:
            print(f"  ... {len(stale_same_sha) - 20} more")

        if not args.apply:
            print("Mode: DRY-RUN — no database changes were made.")
            return 0

        with connection:
            connection.execute(
                "DELETE FROM file_location WHERE absolute_path = ? AND sha512 <> ?",
                (str(path), actual_sha),
            )
            connection.execute(
                """
                INSERT INTO file_location
                    (sha512, absolute_path, file_size, modified_at, location_status)
                VALUES (?, ?, ?, ?, 'ACTIVE')
                ON CONFLICT(sha512, absolute_path) DO UPDATE SET
                    file_size = excluded.file_size,
                    modified_at = excluded.modified_at,
                    location_status = 'ACTIVE'
                """,
                (actual_sha, str(path), file_size, modified_at),
            )
            if stale_same_sha:
                connection.executemany(
                    "UPDATE file_location SET location_status = 'MISSING' WHERE sha512 = ? AND absolute_path = ?",
                    [(actual_sha, location) for location in stale_same_sha],
                )

        print(f"Removed conflicting destination rows: {len(destination_rows) - sum(1 for row in destination_rows if row['sha512'] == actual_sha)}")
        print(f"Marked stale same-SHA locations MISSING: {len(stale_same_sha)}")
        print("Mode: APPLY — database repaired.")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
