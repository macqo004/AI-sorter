"""CLI for safe AllDup SHA-512 cache import."""
from __future__ import annotations

import argparse
from pathlib import Path

from .core.alldup_importer import AllDupImporter


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Porównuje lokalizacje AI-Sorter z AllDup i opcjonalnie zapisuje "
            "potwierdzone SHA-512 do osobnego cache. Domyślnie nie zapisuje nic."
        )
    )
    parser.add_argument("alldup", type=Path, help="Ścieżka do checksum.adb")
    parser.add_argument("project", type=Path, help="Ścieżka do project.db")
    parser.add_argument("--sample", type=int, default=None, help="Ogranicz liczbę sprawdzanych lokalizacji")
    parser.add_argument("--apply", action="store_true", help="Zapisz potwierdzone checksumy do external_hash_cache")
    args = parser.parse_args()

    try:
        stats = AllDupImporter(args.alldup, args.project).run(
            sample_size=args.sample,
            apply=args.apply,
        )
    except (ValueError, RuntimeError) as exc:
        print(f"Błąd: {exc}")
        return 1

    print("AllDup SHA-512 cache import")
    print()
    print(f"Project locations: {stats.project_locations}")
    print(f"Exact path matches: {stats.exact_matches}")
    print(f"Different-root suffix matches: {stats.suffix_matches}")
    print(f"Ambiguous matches rejected: {stats.ambiguous_matches}")
    print(f"No path match: {stats.no_path_match}")
    print(f"SHA512 available in AllDup: {stats.sha512_available}")
    print(f"Same as current Scanner SHA512: {stats.unchanged}")
    print(f"SHA512 conflicts: {stats.conflicts}")
    print(f"Cacheable matches: {stats.cacheable}")
    print(f"Imported to cache: {stats.imported}")
    print()
    if args.apply:
        print("Mode: APPLY — external_hash_cache was updated; canonical Scanner SHA512 records were not overwritten.")
    else:
        print("Mode: DRY-RUN — no database data was written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
