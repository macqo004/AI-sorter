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

            alldup_exact: dict[str, list[sqlite3.Row]] = {}
            alldup_name_size: dict[tuple[str, int], list[sqlite3.Row]] = {}

            # Build only the small lookup structures we need from AllDup.
            # We keep all file rows but only lightweight path/id/size fields in Python.
            files = alldup.execute("SELECT id, file FROM files").fetchall()
            for row in files:
                path = str(row["file"])
                normalized = normalize_path(path)
                alldup_exact.setdefault(normalized, []).append(row)

            # Fetch hash data only for candidate file IDs. The full table is not loaded.
            hash_cache: dict[int, list[sqlite3.Row]] = {}
            for row in samples:
                project_path_text = str(row["absolute_path"])
                norm = normalize_path(project_path_text)
                candidates = list(alldup_exact.get(norm, ()))

                if not candidates:
                    name = basename(project_path_text)
                    size = int(row["file_size"] or -1)
                    if size >= 0:
                        fallback = alldup.execute(
                            """
                            SELECT f.id, f.file
                            FROM files f
                            WHERE lower(f.file) = lower(?)
                            """,
                            (name,),
                        ).fetchall()
                        # Size is checked against hasha.fsize below, so keep only unique filename candidates.
                        candidates = fallback

                for candidate in candidates:
                    file_id = int(candidate["id"])
                    if file_id not in hash_cache:
                        hash_cache[file_id] = alldup.execute(
                            "SELECT algo, fsize, checksum FROM hasha WHERE fileid = ? ORDER BY id",
                            (file_id,),
                        ).fetchall()

            paths_found = 0
            exact_path_matches = 0
            fallback_matches = 0
            checksum_matches = 0
            checksum_mismatches = 0
            no_hash_row = 0
            ambiguous_fallbacks = 0
            no_path_match = 0
            algo_counts: dict[int, int] = {}
            diagnostic_project = []
            diagnostic_alldup = []

            for sample in samples:
                path = str(sample["absolute_path"])
                our_sha = str(sample["sha512"]).lower()
                size = int(sample["file_size"] or -1)
                norm = normalize_path(path)
                candidates = list(alldup_exact.get(norm, ()))
                match_type = "EXACT PATH"

                if candidates:
                    exact_path_matches += 1
                else:
                    name = basename(path)
                    fallback_rows = alldup.execute(
                        "SELECT id, file FROM files WHERE lower(file) = lower(?)",
                        (name,),
                    ).fetchall()
                    size_filtered = []
                    for candidate in fallback_rows:
                        file_id = int(candidate["id"])
                        hashes = hash_cache.get(file_id)
                        if hashes is None:
                            hashes = alldup.execute(
                                "SELECT algo, fsize, checksum FROM hasha WHERE fileid = ? ORDER BY id",
                                (file_id,),
                            ).fetchall()
                            hash_cache[file_id] = hashes
                        if any(int(h["fsize"]) == size for h in hashes):
                            size_filtered.append(candidate)
                    candidates = size_filtered
                    match_type = "NAME+SIZE"
                    if len(candidates) == 1:
                        fallback_matches += 1
                    elif len(candidates) > 1:
                        ambiguous_fallbacks += 1
                        candidates = []

                if not candidates:
                    no_path_match += 1
                    no_hash_row += 1
                    if len(diagnostic_project) < 5:
                        diagnostic_project.append(path)
                    continue

                paths_found += 1
                candidate_hashes = []
                all_algos = set()
                matching_algos = set()
                for candidate in candidates:
                    file_id = int(candidate["id"])
                    hashes = hash_cache[file_id]
                    for h in hashes:
                        all_algos.add(int(h["algo"]))
                        if int(h["fsize"]) != size:
                            continue
                        checksum = sha_hex(h["checksum"])
                        if checksum:
                            candidate_hashes.append((int(h["algo"]), checksum))
                            if checksum == our_sha:
                                matching_algos.add(int(h["algo"]))

                if not candidate_hashes:
                    no_hash_row += 1
                elif matching_algos:
                    checksum_matches += 1
                    for algo in matching_algos:
                        algo_counts[algo] = algo_counts.get(algo, 0) + 1
                else:
                    checksum_mismatches += 1

                if match_type == "NAME+SIZE" and len(diagnostic_alldup) < 5:
                    diagnostic_alldup.append(str(candidates[0]["file"]))

            print("AllDup ↔ AI-Sorter SHA512 correlation")
            print()
            print(f"Sample: {len(samples)}")
            print(f"Paths found in AllDup: {paths_found}")
            print(f"  Exact normalized path matches: {exact_path_matches}")
            print(f"  Fallback name+size matches: {fallback_matches}")
            print(f"  Ambiguous fallbacks rejected: {ambiguous_fallbacks}")
            print(f"No path match: {no_path_match}")
            print(f"SHA512 matches: {checksum_matches}")
            print(f"SHA512 mismatches: {checksum_mismatches}")
            print(f"Files with no usable hasha row: {no_hash_row}")
            print()
            print("Matching algo values:")
            if algo_counts:
                for algo, count in sorted(algo_counts.items()):
                    print(f"  {algo}: {count}")
            else:
                print("  none")

            if diagnostic_project:
                print()
                print("Example AI-Sorter paths with no match:")
                for item in diagnostic_project:
                    print(f"  {item}")
            if diagnostic_alldup:
                print()
                print("Example AllDup paths used by fallback matching:")
                for item in diagnostic_alldup:
                    print(f"  {item}")

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
