from __future__ import annotations

import sqlite3
from pathlib import Path

from ai_sorter.alldup_checksum_stats import collect_stats


def _make_db(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE files (id INTEGER PRIMARY KEY, file TEXT);
            CREATE TABLE hasha (id INTEGER PRIMARY KEY, fileid INTEGER, algo INTEGER, checksum BLOB);
            CREATE TABLE hashc (id INTEGER PRIMARY KEY, fileid INTEGER, ctype INTEGER, checksum BLOB);
            CREATE TABLE hashp (id INTEGER PRIMARY KEY, fileid INTEGER, ctype INTEGER, checksum BLOB);
            """
        )
        connection.executemany(
            "INSERT INTO files(id, file) VALUES (?, ?)",
            [(1, "a.jpg"), (2, "b.jpg"), (3, "c.jpg")],
        )
        sha_a = bytes.fromhex("00" * 64)
        sha_b = bytes.fromhex("11" * 64)
        connection.executemany(
            "INSERT INTO hashc(id, fileid, ctype, checksum) VALUES (?, ?, ?, ?)",
            [(1, 1, 5, sha_a), (2, 2, 5, sha_a), (3, 3, 5, sha_b)],
        )
        connection.commit()
    finally:
        connection.close()


def test_sha512_audit_counts_rows_files_and_unique_values(tmp_path: Path) -> None:
    db = tmp_path / "AllDup.db"
    _make_db(db)

    stats = collect_stats(db)

    assert stats.sha512_audit.rows == 3
    assert stats.sha512_audit.distinct_files == 3
    assert stats.sha512_audit.distinct_sha512 == 2
    assert stats.sha512_audit.duplicate_groups is None


def test_sha512_audit_distribution_is_optional(tmp_path: Path) -> None:
    db = tmp_path / "AllDup.db"
    _make_db(db)

    stats = collect_stats(db, include_distribution=True)

    assert stats.sha512_audit.duplicate_groups == 1
    assert stats.sha512_audit.duplicate_file_excess == 1
    assert stats.sha512_audit.max_group_size == 2


def test_non_sha512_checksum_rows_do_not_enter_audit(tmp_path: Path) -> None:
    db = tmp_path / "AllDup.db"
    _make_db(db)

    connection = sqlite3.connect(db)
    try:
        connection.execute(
            "INSERT INTO hashc(id, fileid, ctype, checksum) VALUES (?, ?, ?, ?)",
            (4, 3, 1, b"not-sha512"),
        )
        connection.commit()
    finally:
        connection.close()

    stats = collect_stats(db)
    assert stats.sha512_audit.rows == 3
    assert stats.sha512_audit.distinct_sha512 == 2
