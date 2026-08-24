"""Compare AI-Sorter SHA512 values against AllDup without modifying either database."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def normalize_path(value: str) -> str:
    text = value.strip().replace("/", "\\")
    while text.startswith("\\\\?\\"):
        text = text[4:]
    while "\\\\" in text:
        text = text.replace("\\\\", "\\")
    return text.rstrip("\\").casefold()


def basename(value: str) -> str:
    return normalize_path(value).rsplit("\\", 1)[-1]


def sha_hex(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.hex().casefold()
    if isinstance(value, memoryview):
        return value.tobytes().hex().casefold()
    try:
        return bytes(value).hex().casefold()
    except Exception:
        return str(value).casefold()


def open_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ValueError(f"Baza nie istnieje: {path}")
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def fetch_hash_rows(alldup: sqlite3.Connection, file_id: int) -> list[sqlite3.Row]:
    return alldup.execute(
        "SELECT algo, fsize, checksum FROM hasha WHERE fileid = ? ORDER BY id",
        (file_id,),
    ).fetchall()


def exact_file_candidates(alldup: sqlite3.Connection, path: str) -> list[sqlite3.Row]:
    # `files.file` has a unique index in the inspected AllDup database, so keep
    # this lookup index-friendly and try only the most likely path spellings.
    variants = []
    normalized = path.replace("/", "\\")
    variants.append(path)
    if normalized != path:
        variants.append(normalized)
    if path.startswith("\\\\?\\"):
        variants.append(path[4:])
    elif path.startswith("\\\\"):
        variants.append("\\\\?\\" + path)

    seen: set[int] = set()
    result: list[sqlite3.Row] = []
    for variant in variants:
        rows = alldup.execute(
            "SELECT id, file FROM files WHERE file = ?",
            (variant,),
        ).fetchall()
        for row in rows:
            file_id = int(row["id"])
            if file_id not in seen:
                seen.add(file_id)
                result.append(row)
    return result


def suffix_candidates(alldup: sqlite3.Connection, path: str, size: int) -> list[sqlite3.Row]:
    """Try a bounded suffix lookup for cases where one DB has a different root.

    This is diagnostic/fallback only. It is deliberately rejected when multiple
    files share the same basename and size.
    """
    name = basename(path)
    rows = alldup.execute(
        """
        SELECT f.id, f.file
        FROM files f
        JOIN hasha h ON h.fileid = f.id AND h.fsize = ?
        WHERE f.file LIKE ? ESCAPE '\\'
        GROUP BY f.id, f.file
        LIMIT 10
        """,
        (size, "%" + "\\" + name),
    ).fetchall()
    return rows


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print("Użycie: ai-sorter-alldup-sha512 <checksum.adb> <project.db> [sample_size]")
        return 2

    alldup_path = Path(sys.argv[1])
    project_path = Path(sys.argv[2])
    sample_size = max(1, min(500, int(sys.argv[3]) if len(sys.argv) == 4 else 50))

    try:
        project = open_readonly(project_path)
        alldup = open_readonly(alldup_path)
        try:
            samples = project.execute(
                """
                SELECT fl.absolute_path, fl.sha512, fl.file_size
                FROM file_location fl
                JOIN file_record fr ON fr.sha512 = fl.sha512
                WHERE fl.location_status = 'ACTIVE'
                  AND fr.status = 'ACTIVE'
                ORDER BY RANDOM()
                LIMIT ?
                """,
                (sample_size,),
            ).fetchall()

            exact_matches = suffix_matches = ambiguous = no_path = 0
            checksum_matches = checksum_mismatches = no_hash = 0
            algo_counts: dict[int, int] = {}
            diagnostics_project: list[str] = []
            diagnostics_all_dup: list[str] = []

            for sample in samples:
                path = str(sample["absolute_path"])
                our_sha = str(sample["sha512"]).lower()
                size = int(sample["file_size"] or -1)

                candidates = exact_file_candidates(alldup, path)
                match_type = "exact"
                if candidates:
                    exact_matches += 1
                else:
                    candidates = suffix_candidates(alldup, path, size) if size >= 0 else []
                    if len(candidates) == 1:
                        suffix_matches += 1
                        match_type = "suffix"
                    elif len(candidates) > 1:
                        ambiguous += 1
                        candidates = []

                if not candidates:
                    no_path += 1
                    if len(diagnostics_project) < 5:
                        diagnostics_project.append(path)
                    continue

                hash_rows: list[sqlite3.Row] = []
                for candidate in candidates:
                    rows = fetch_hash_rows(alldup, int(candidate["id"]))
                    hash_rows.extend(rows)
                    if match_type == "suffix" and len(diagnostics_all_dup) < 5:
                        diagnostics_all_dup.append(str(candidate["file"]))

                usable = [row for row in hash_rows if int(row["fsize"]) == size]
                if not usable:
                    no_hash += 1
                    continue

                matching_algos: set[int] = set()
                for row in usable:
                    digest = sha_hex(row["checksum"])
                    if digest == our_sha:
                        matching_algos.add(int(row["algo"]))

                if matching_algos:
                    checksum_matches += 1
                    for algo in matching_algos:
                        algo_counts[algo] = algo_counts.get(algo, 0) + 1
                else:
                    checksum_mismatches += 1

            print("AllDup ↔ AI-Sorter SHA512 correlation")
            print()
            print(f"Sample: {len(samples)}")
            print(f"Exact normalized-path matches: {exact_matches}")
            print(f"Fallback suffix name+size matches: {suffix_matches}")
            print(f"Ambiguous suffix matches rejected: {ambiguous}")
            print(f"No path match: {no_path}")
            print(f"SHA512 matches: {checksum_matches}")
            print(f"SHA512 mismatches: {checksum_mismatches}")
            print(f"Files with no usable hasha row: {no_hash}")
            print()
            print("Matching algo values:")
            if algo_counts:
                for algo, count in sorted(algo_counts.items()):
                    print(f"  {algo}: {count}")
            else:
                print("  none")

            print()
            print("AllDup path samples (database format):")
            for row in alldup.execute("SELECT file FROM files ORDER BY id LIMIT 5").fetchall():
                print(f"  {row['file']}")

            if diagnostics_project:
                print()
                print("AI-Sorter paths that did not match:")
                for value in diagnostics_project:
                    print(f"  {value}")
            if diagnostics_all_dup:
                print()
                print("AllDup paths matched by suffix fallback:")
                for value in diagnostics_all_dup:
                    print(f"  {value}")

            print()
            print("Safety: both databases were opened read-only; no writes or checksum recalculation were performed.")
            return 0
        finally:
            project.close()
            alldup.close()
    except (ValueError, sqlite3.Error) as exc:
        print(f"Błąd: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
