"""Streamingly organize SHA-512 duplicate groups from the entire AllDup database.

The AllDup database is read-only. By default this is a dry-run; --apply physically
moves files into numbered review folders. Every move verifies the source against the
AllDup SHA-512 before changing the destination. Source deletion happens only after
an independently verified destination exists.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

ALLDUP_SHA512_CTYPE = 5
COPY_BUFFER_SIZE = 1024 * 1024
TEMP_SUFFIX = ".ai-sorter-partial"


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
    verified_moves: int
    elapsed_seconds: float


class DuplicateReviewOrganizer:
    """Process SHA-512 duplicate groups one at a time from all AllDup entries."""

    def __init__(self, alldup_path: Path, destination_root: Path) -> None:
        self.alldup_path = alldup_path.resolve()
        self.destination_root = destination_root.resolve()

    def run(self, *, apply: bool = False, limit_groups: int | None = None) -> OrganizeStats:
        self._validate_paths()
        started = time.perf_counter()
        if self.destination_root.exists() and any(self.destination_root.iterdir()):
            raise ValueError(
                f"Folder docelowy nie jest pusty: {self.destination_root}\n"
                "Dla bezpieczeństwa organizer wymaga pustego folderu docelowego."
            )
        if apply:
            self.destination_root.mkdir(parents=True, exist_ok=True)

        groups = files = existing_files = missing_files = collisions = moved_files = failed_moves = verified_moves = 0
        manifest_stream = None
        manifest_writer = None
        if apply:
            manifest_stream = (self.destination_root / "manifest.csv").open("w", encoding="utf-8-sig", newline="")
            manifest_writer = csv.writer(manifest_stream, delimiter=";")
            manifest_writer.writerow(["sha512", "source_path", "destination_path", "file_size", "status"])
            manifest_stream.flush()

        try:
            for group in self._iter_duplicate_groups(limit_groups):
                groups += 1
                files += len(group)
                existing_items: list[DuplicateFile] = []
                for item in group:
                    if item.source.is_file():
                        existing_files += 1
                        existing_items.append(item)
                    else:
                        missing_files += 1
                if not existing_items:
                    continue

                target_dir = self.destination_root / str(groups)
                if apply:
                    target_dir.mkdir(parents=True, exist_ok=True)
                planned_names: set[str] = set()
                for item in existing_items:
                    target = self._unique_target(target_dir, item.source.name, planned_names)
                    if target.name.lower() != item.source.name.lower():
                        collisions += 1
                    planned_names.add(target.name.lower())
                    if not apply:
                        continue
                    try:
                        self._move_verified(item, target)
                        moved_files += 1
                        verified_moves += 1
                        assert manifest_writer is not None
                        manifest_writer.writerow((item.sha512, str(item.source), str(target), item.size, "MOVED_VERIFIED"))
                    except (OSError, RuntimeError) as exc:
                        failed_moves += 1
                        assert manifest_writer is not None
                        manifest_writer.writerow((item.sha512, str(item.source), f"ERROR: {exc}", item.size, "FAILED_SOURCE_PRESERVED"))
                if manifest_stream is not None:
                    manifest_stream.flush()
        finally:
            if manifest_stream is not None:
                manifest_stream.close()

        return OrganizeStats(groups, files, existing_files, missing_files, collisions,
                             moved_files, failed_moves, verified_moves, time.perf_counter() - started)

    def _validate_paths(self) -> None:
        if not self.alldup_path.is_file():
            raise ValueError(f"Nie znaleziono bazy AllDup: {self.alldup_path}")
        if self.destination_root.exists() and self.destination_root.is_file():
            raise ValueError(f"Folder docelowy jest plikiem: {self.destination_root}")

    def _open_alldup(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self.alldup_path.as_posix()}?mode=ro", uri=True, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _iter_duplicate_groups(self, limit_groups: int | None) -> Iterator[list[DuplicateFile]]:
        connection = self._open_alldup()
        try:
            cursor = connection.execute(
                """
                SELECT h.checksum AS checksum, f.file AS absolute_path, h.fsize AS file_size
                FROM hashc AS h
                JOIN files AS f ON f.id = h.fileid
                WHERE h.ctype = ?
                ORDER BY h.checksum, f.file
                """,
                (ALLDUP_SHA512_CTYPE,),
            )
            current_sha = ""
            current_group: list[DuplicateFile] = []
            groups_emitted = 0
            for row in cursor:
                sha512 = self._normalize_sha512(row["checksum"])
                if not sha512:
                    continue
                item = DuplicateFile(sha512, Path(str(row["absolute_path"])), int(row["file_size"] or 0))
                if current_sha and sha512 != current_sha:
                    if len(current_group) >= 2:
                        yield current_group
                        groups_emitted += 1
                        if limit_groups is not None and groups_emitted >= limit_groups:
                            return
                    current_group = []
                if sha512 != current_sha:
                    current_sha = sha512
                current_group.append(item)
            if current_group and len(current_group) >= 2:
                yield current_group
        finally:
            connection.close()

    @staticmethod
    def _unique_target(directory: Path, filename: str, planned_names: set[str]) -> Path:
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        candidate = directory / filename
        if filename.lower() not in planned_names and not candidate.exists():
            return candidate
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

    @staticmethod
    def _sha512_file(path: Path) -> str:
        digest = hashlib.sha512()
        with path.open("rb", buffering=COPY_BUFFER_SIZE) as stream:
            for chunk in iter(lambda: stream.read(COPY_BUFFER_SIZE), b""):
                digest.update(chunk)
        return digest.hexdigest().lower()

    def _verify_source(self, item: DuplicateFile) -> None:
        source = item.source
        try:
            stat = source.stat()
        except OSError as exc:
            raise RuntimeError(f"Nie można odczytać źródła: {source}: {exc}") from exc
        if stat.st_size != item.size:
            raise RuntimeError(
                f"Rozmiar źródła ({stat.st_size}) nie zgadza się z AllDup ({item.size}); źródło pozostawiono bez zmian."
            )
        source_sha = self._sha512_file(source)
        if source_sha != item.sha512:
            raise RuntimeError("SHA-512 źródła nie zgadza się z AllDup; pliku nie przeniesiono.")

    def _move_verified(self, item: DuplicateFile, target: Path) -> None:
        """Copy and verify before finalizing destination; delete source only after success."""
        source = item.source
        target.parent.mkdir(parents=True, exist_ok=True)
        self._verify_source(item)

        # Never remove/replace the source before a verified destination exists.
        # The temporary file lives next to the final target so finalization remains atomic.
        temp_target = target.with_name(target.name + TEMP_SUFFIX)
        temp_target.unlink(missing_ok=True)
        try:
            shutil.copyfile(source, temp_target)
            actual_size = temp_target.stat().st_size
            if actual_size != item.size:
                raise RuntimeError(
                    f"Rozmiar pliku docelowego ({actual_size}) nie zgadza się z AllDup ({item.size})."
                )
            destination_sha512 = self._sha512_file(temp_target)
            if destination_sha512 != item.sha512:
                raise RuntimeError(
                    "SHA-512 pliku docelowego nie zgadza się z checksumem AllDup; źródło pozostawiono bez zmian."
                )
            if target.exists():
                raise RuntimeError(f"Cel pojawił się podczas operacji: {target}; źródło pozostawiono bez zmian.")
            os.replace(temp_target, target)
            # The destination has already been verified. If deletion fails, keeping both
            # copies is safer than deleting anything else or reporting a false move.
            try:
                source.unlink()
            except OSError as exc:
                raise RuntimeError(
                    f"Cel został zweryfikowany, ale nie udało się usunąć źródła; oba pliki pozostawiono: {exc}"
                ) from exc
        finally:
            temp_target.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Group SHA-512 duplicates from the entire AllDup database into numbered review folders.")
    parser.add_argument("alldup_db", type=Path, help="Path to AllDup checksum.adb")
    parser.add_argument("destination_root", type=Path, help="Empty root for numbered review folders")
    parser.add_argument("--apply", action="store_true", help="Actually move files; default is dry-run")
    parser.add_argument("--limit-groups", type=int, default=None, help="Process at most N duplicate groups")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        stats = DuplicateReviewOrganizer(args.alldup_db, args.destination_root).run(
            apply=args.apply, limit_groups=args.limit_groups
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("Duplicate Review Organizer")
    print(f"AllDup database: {args.alldup_db.resolve()}")
    print(f"Destination: {args.destination_root.resolve()}")
    print(f"Duplicate groups: {stats.groups}")
    print(f"Files in duplicate groups: {stats.files}")
    print(f"Existing source files: {stats.existing_files}")
    print(f"Missing source files: {stats.missing_files}")
    print(f"Filename collisions resolved with _N: {stats.collisions}")
    print(f"Moved files: {stats.moved_files}")
    print(f"Verified moves: {stats.verified_moves}")
    print(f"Failed moves: {stats.failed_moves}")
    print(f"Elapsed: {stats.elapsed_seconds:.3f}s")
    if stats.elapsed_seconds > 0:
        print(f"Groups/sec: {stats.groups / stats.elapsed_seconds:.1f}")
        print(f"Files/sec: {stats.files / stats.elapsed_seconds:.1f}")
    print("Mode: APPLY — files were physically moved." if args.apply else "Mode: DRY-RUN — no files were moved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
