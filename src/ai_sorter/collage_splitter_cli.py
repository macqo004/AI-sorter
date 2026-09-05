"""CLI for the standalone collage splitter."""

from __future__ import annotations

import argparse
from pathlib import Path

from ai_sorter.core.collage_splitter import CollageSplitter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect rectangular collage boundaries and optionally split images in place."
    )
    parser.add_argument("paths", nargs="+", type=Path, help="Image files to inspect")
    parser.add_argument("--apply", action="store_true", help="Actually create split images; default is preview only")
    parser.add_argument("--analysis-size", type=int, default=512, help="Maximum analysis dimension")
    parser.add_argument("--threshold", type=float, default=28.0, help="Average edge threshold")
    parser.add_argument("--coverage", type=float, default=0.45, help="Minimum strong-edge coverage")
    parser.add_argument("--min-piece", type=float, default=0.08, help="Minimum piece dimension ratio")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    splitter = CollageSplitter(
        analysis_size=args.analysis_size,
        edge_threshold=args.threshold,
        coverage_threshold=args.coverage,
        min_piece_ratio=args.min_piece,
    )
    exit_code = 0
    for path in args.paths:
        try:
            result = splitter.detect(path)
            print(f"{result.source}")
            print(f"  size: {result.image_width}x{result.image_height}")
            print(f"  rectangles: {len(result.rectangles)}")
            print(f"  confidence: {result.confidence:.3f}")
            for index, rect in enumerate(result.rectangles, start=1):
                print(f"    {index:02d}: ({rect.left},{rect.top})-({rect.right},{rect.bottom}) {rect.width}x{rect.height}")
            if len(result.rectangles) >= 2:
                outputs = splitter.split(result, apply=args.apply)
                if args.apply:
                    for output in outputs:
                        print(f"  created: {output}")
                else:
                    for output in outputs:
                        print(f"  would create: {output}")
            else:
                print("  no collage split detected")
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"ERROR: {path}: {exc}")
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
