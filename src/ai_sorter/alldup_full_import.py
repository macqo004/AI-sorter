"""CLI for importing AllDup SHA-512/path data into AI-Sorter."""
from __future__ import annotations

import argparse
from pathlib import Path

from .core.alldup_full_importer import AllDupFullImporter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Importuj SHA-512 i ścieżki z AllDup dla wskazanego folderu i podfolderów."
    )
    parser.add_argument("alldup", type=Path, help="Ścieżka do checksum.adb")
    parser.add_argument("project", type=Path, help="Ścieżka do project.db")
    parser.add_argument("root", type=Path, help="Korzeń zakresu importu")
    parser.add_argument("--limit", type=int, default=None, help="Maksymalna liczba rekordów do pobrania")
    parser.add_argument("--batch-size", type=int, default=10000, help="Rozmiar transakcji zapisu (domyślnie 10000)")
    parser.add_argument("--apply", action="store_true", help="Zapisz dane do project.db; bez tego tylko benchmark/preview")
    args = parser.parse_args()

    try:
        stats = AllDupFullImporter(args.alldup, args.project).run(
            args.root,
            limit=args.limit,
            batch_size=args.batch_size,
            apply=args.apply,
        )
    except (ValueError, RuntimeError) as exc:
        print(f"Błąd: {exc}")
        return 1

    print("AllDup → AI-Sorter full import")
    print()
    print(f"Root: {args.root.resolve()}")
    print(f"Selected rows: {stats.selected_rows}")
    print(f"Rows with SHA512: {stats.selected_rows - stats.skipped_without_sha512}")
    print(f"Skipped without SHA512: {stats.skipped_without_sha512}")
    print(f"Imported locations: {stats.imported_locations}")
    print(f"New file identities: {stats.new_file_records}")
    print(f"Elapsed: {stats.elapsed_seconds:.3f} s")
    print(f"Rate: {stats.rows_per_second:,.1f} rows/s")
    print()
    print("Mode: APPLY — project.db updated." if args.apply else "Mode: BENCHMARK/DRY-RUN — project.db not changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
