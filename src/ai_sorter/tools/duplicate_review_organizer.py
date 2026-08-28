"""Streamingly organize SHA-512 duplicate groups into a review tree."""
from __future__ import annotations

import argparse
import csv
import os
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ALLDUP_SHA512_CTYPE = 5


@dataclass(frozen=True, slots=True)
class DuplicateFile:
    sha512: str
    source: Path
    size: int


@dataclass(frozen=True, slots=True)
class OrganizeStats:
    groups: int
    files: int
    existing_files: int
    missing_files: int
    collisions: int
    moved_files: int
    failed_moves: int
    elapsed_seconds: float


class DuplicateReviewOrganizer:
    """Find SHA-512 duplicate groups in AllDup and process them one group at a time."""

    def __init__(self, alldup_path: Path, source_root: Path, destination_root: Path) -> None:
        self.alldup_path = alldup_path.resolve()
        self.source_root = source_root.resolve()
        self.destination_root = destination_root.resolve()

    def run(self, *, apply: bool = False, limit_groups: int | None = None) -> OrganizeStats:
        self._validate_paths()
        started = time.perf_counter()

        if apply:
            if not self.destination_root.exists():
                self.destination_root.mkdir(parents=True)
            elif any(self.destination_root.iterdir()):
                raise ValueError(
                    f"Folder docelowy nie jest pusty: {self.destination_root}\n"
                    "Dla bezpieczeństwa organizer wymaga pustego folderu docelowego."
                )
        elif self.destination_root.exists() and any(self.destination_root.iterdir()):
            raise ValueError(
                f"Folder docelowy nie jest pusty: {self.destination_root}\n"
                "Dry-run również wymaga pustego folderu docelowego."
            )

        groups = files = existing_files = missing_files = collisions = moved_files = failed_moves = 0
        manifest_stream = None
        manifest_writer = None

        if apply:
            manifest_path = self.destination_root / "manifest.csv"
            manifest_stream = manifest_path.open("w", encoding="utf-8-sig", newline="")
            manifest_writer = csv.writer(manifest_stream, delimiter=";")
            manifest_writer.writerow(["sha512", "source_path", "destination_path", "file_size"])
            manifest_stream.flush()

        try:
            for group in self._iter_duplicate_groups(limit_groups):
                groups += 1
                files += len(group)
                for item in group:
                    if item.source.is_file():
                        existing_files += 1
                    else:
                        missing_files += 1

                target_dir = self.destination_root / str(groups)
                planned_names: set[str] = set()
                if apply:
                    target_dir.mkdir(parents=True, exist_ok=True)

                for item in group:
                    if not item.source.is_file():
                        continue
                    target = self._unique_target(target_dir, item.source.name, planned_names)
                    if target.name != item.source.name:
                        collisions += 1
                    planned_names.add(target.name.lower())

                    if apply:
                        try:
                            os.replace(item.source, target)
                            moved_files += 1
                            assert manifest_writer is not None
                            manifest_writer.writerow((item.sha512, str(item.source), str(target), item.size))
                        except OSError as exc:
                            failed_moves += 1
                            assert manifest_writer is not None
                            manifest_writer.writerow((item.sha512, str(item.source), f"ERROR: {exc}", item.size))
                if manifest_stream is not None:
                    manifest_stream.flush()
        finally:
            if manifest_stream is not None:
                manifest_stream.close()

        return OrganizeStats(
            groups=groups,
            files=files,
            existing_files=existing_files,
            missing_files=missing_files,
            collisions=collisions,
            moved_files=moved_files,
            failed_moves=failed_moves,
            elapsed_seconds=time.perf_counter() - started,
        )

    def _validate_paths(self) -> None:
        if not self.alldup_path.is_file():
            raise ValueError(f"Nie znaleziono bazy AllDup: {self.alldup_path}")
        if not self.source_root.is_dir():
            raise ValueError(f"Nie znaleziono folderu źródłowego: {self.source_root}")
        try:
            self.destination_root.relative_to(self.source_root)
        except ValueError:
            return
        raise ValueError(
            "Folder docelowy nie może znajdować się wewnątrz folderu źródłowego. "
            "Wybierz osobne drzewo DuplicateReview."
        )

    def _open_alldup(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            f"file:{self.alldup_path.as_posix()}?mode=ro", uri=True, timeout=30
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _iter_duplicate_groups(self, limit_groups: int | None):
        """Yield duplicate groups one at a time; never materialize the whole database result."""
        root = str(self.source_root).rstrip("\\/")
        prefix = root + "\\%"
        limit_clause = " LIMIT ?" if limit_groups is not None else ""

        connection = self._open_alldup()
        try:
            params: list[object] = [ALLDUP_SHA512_CTYPE, root, prefix]
            if limit_groups is not None:
                params.append(int(limit_groups))

            group_cursor = connection.execute(
                f"""
                SELECT h.checksum AS checksum
                FROM files f
                JOIN hashc h
                  ON h.fileid = f.id
                 AND h.ctype = ?
                WHERE f.file = ? OR f.file LIKE ?
                GROUP BY h.checksum
                HAVING COUNT(*) >= 2
                ORDER BY lower(hex(h.checksum))
                {limit_clause}
                """,
                tuple(params),
            )

            for group_row in group_cursor:
                checksum_blob = group_row["checksum"]
                sha512 = self._normalize_sha512(checksum_blob)
                if not sha512:
                    continue

                file_cursor = connection.execute(
                    """
                    SELECT f.file AS absolute_path, h.fsize AS file_size
                    FROM files f
                    JOIN hashc h
                      ON h.fileid = f.id
                     AND h.ctype = ?
                    WHERE (f.file = ? OR f.file LIKE ?)
                      AND h.checksum = ?
                    ORDER BY f.file
                    """,
                    (ALLDUP_SHA512_CTYPE, root, prefix, checksum_blob),
                )
                group = [
                    DuplicateFile(
                        sha512=sha512,
                        source=Path(str(item["absolute_path"])),
                        size=int(item["file_size"] or 0),
                    )
                    for item in file_cursor
                ]
                if len(group) >= 2:
                    yield group
        finally:
            connection.close()

    @staticmethod
    def _unique_target(directory: Path, filename: str, planned_names: set[str]) -> Path:
        """Return a short collision-safe name such as foo.jpg, foo_1.jpg, foo_2.jpg."""
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        target = directory / filename
        if filename.lower() not in planned_names and not target.exists():
            return target

        counter = 1
        while True:
            candidate_name = f"{stem}_{counter}{suffix}"
            candidate = directory / candidate_name
            if candidate_name.lower() not in planned_names and not candidate.exists():
                return candidate
            counter += 1

    @staticmethod
    def _normalize_sha512(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, memoryview):
            value = value.tobytes()
        if isinstance(value, bytes):
            digest = value.hex().lower()
        else:
            digest = str(value).strip().lower()
        if len(digest) != 128 or any(ch not in "0123456789abcdef" for ch in digest):
            return ""
        return digest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Group SHA-512 duplicates from AllDup into numbered review folders."
    )
    parser.add_argument("alldup_db", type=Path, help="Path to AllDup checksum.adb")
    parser.add_argument("source_root", type=Path, help="Root whose files are eligible for moving")
    parser.add_argument("destination_root", type=Path, help="Empty root for numbered review folders")
    parser.add_argument("--apply", action="store_true", help="Actually move files; default is dry-run")
    parser.add_argument("--limit-groups", type=int, default=None, help="Process at most N duplicate groups")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        stats = DuplicateReviewOrganizer(
            args.alldup_db, args.source_root, args.destination_root
        ).run(apply=args.apply, limit_groups=args.limit_groups)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("Duplicate Review Organizer")
    print(f"Source root: {args.source_root.resolve()}")
    print(f"Destination: {args.destination_root.resolve()}")
    print(f"Duplicate groups: {stats.groups}")
    print(f"Files in duplicate groups: {stats.files}")
    print(f"Existing source files: {stats.existing_files}")
    print(f"Missing source files: {stats.missing_files}")
    print(f"Filename collisions resolved with _N: {stats.collisions}")
    print(f"Moved files: {stats.moved_files}")
    print(f"Failed moves: {stats.failed_moves}")
    print(f"Elapsed: {stats.elapsed_seconds:.3f}s")
    if stats.elapsed_seconds > 0:
        print(f"Groups/sec: {stats.groups / stats.elapsed_seconds:.1f}")
        print(f"Files/sec: {stats.files / stats.elapsed_seconds:.1f}")
    print("Mode: APPLY — files were physically moved." if args.apply else "Mode: DRY-RUN — no files were moved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
