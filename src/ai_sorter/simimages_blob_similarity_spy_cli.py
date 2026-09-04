from __future__ import annotations

import argparse
from pathlib import Path

from ai_sorter.core.simimages_blob_similarity_spy import SimImagesBlobSimilaritySpy


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare SimImages BLOB distance with visual image distance.")
    parser.add_argument("database", type=Path, help="Path to SimilarImages Cache.db")
    parser.add_argument("--files", type=int, default=120, help="Number of live image rows to compare")
    parser.add_argument("--cache-rows", type=int, default=10_000, help="Maximum cache rows to inspect")
    parser.add_argument("--visual-size", type=int, default=32, help="Visual fingerprint side length")
    parser.add_argument("--top", type=float, default=0.10, help="Fraction used for nearest-pair overlap")
    parser.add_argument("--display", type=int, default=10, help="Number of closest pairs to display")
    args = parser.parse_args()

    result = SimImagesBlobSimilaritySpy().analyze(
        args.database,
        requested_images=args.files,
        max_cache_rows=args.cache_rows,
        visual_size=args.visual_size,
        top_fraction=args.top,
        display_count=args.display,
    )
    print(result.format_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
