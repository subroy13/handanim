#!/usr/bin/env python3
"""
CLI entry point for the skeletonisation tool.

Usage examples
--------------
# Process the math preset (default) from NotoSansMath
python -m tools.skeleton.run \\
    --font assets/fonts/ttf/NotoSansMath-Regular.ttf \\
    --out  assets/fonts/custom/noto_sans_math_skeleton.json

# Process only ASCII characters
python -m tools.skeleton.run \\
    --font assets/fonts/ttf/NotoSansMath-Regular.ttf \\
    --preset ascii \\
    --out  assets/fonts/custom/noto_sans_math_skeleton.json

# Process specific codepoints (hex or decimal, space-separated)
python -m tools.skeleton.run \\
    --font   assets/fonts/ttf/NotoSansMath-Regular.ttf \\
    --chars  "0x41 0x42 0x43 0x2211 0x222B" \\
    --out    assets/fonts/custom/noto_sans_math_skeleton.json

# Tune quality parameters
python -m tools.skeleton.run \\
    --font           assets/fonts/ttf/NotoSansMath-Regular.ttf \\
    --size           512 \\
    --spur-threshold 8 \\
    --dp-tolerance   2.0 \\
    --out            assets/fonts/custom/noto_sans_math_skeleton.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _parse_chars(chars_str: str) -> list[int]:
    """Parse a space-separated string of hex (0x…) or decimal codepoints."""
    codepoints = []
    for tok in chars_str.split():
        tok = tok.strip()
        if not tok:
            continue
        if tok.startswith("0x") or tok.startswith("0X"):
            codepoints.append(int(tok, 16))
        elif len(tok) == 1:
            # Single character literal
            codepoints.append(ord(tok))
        else:
            codepoints.append(int(tok))
    return codepoints


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m tools.skeleton.run",
        description="Convert double-stroke TTF glyphs to single-stroke skeleton paths.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--font", required=True,
        help="Path to the input TTF font file.",
    )
    parser.add_argument(
        "--out", required=True,
        help="Output path for the custom JSON font file.",
    )
    parser.add_argument(
        "--preset", default="math",
        choices=["ascii", "math", "all"],
        help="Pre-defined codepoint set to process (default: math).",
    )
    parser.add_argument(
        "--chars", default=None,
        help=(
            "Space-separated codepoints to process (overrides --preset). "
            "Each token can be hex (0x2211) or decimal (8721) or a single character (A)."
        ),
    )
    parser.add_argument(
        "--name", default=None,
        help="Font name stored in the JSON metadata (default: font filename stem).",
    )
    parser.add_argument(
        "--size", type=int, default=512,
        help="Rasterisation bitmap size in pixels (default: 512).",
    )
    parser.add_argument(
        "--spur-threshold", type=int, default=8, dest="spur_threshold",
        help=(
            "Branches shorter than this (pixels) between two junctions are "
            "pruned as junction-cluster artefacts (default: 8)."
        ),
    )
    parser.add_argument(
        "--dp-tolerance", type=float, default=2.0, dest="dp_tolerance",
        help="Douglas–Peucker simplification tolerance in pixels (default: 2.0).",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress progress bar.",
    )

    args = parser.parse_args(argv)

    # Resolve font path relative to the repo root when called from there
    font_path = Path(args.font)
    if not font_path.exists():
        print(f"Error: font file not found: {font_path}", file=sys.stderr)
        sys.exit(1)

    codepoints = _parse_chars(args.chars) if args.chars else None

    # Import here so the module can be imported without triggering heavy deps
    from tools.skeleton.export import build_skeleton_font, save_font

    font_dict = build_skeleton_font(
        font_path=font_path,
        codepoints=codepoints,
        preset=args.preset,
        size=args.size,
        spur_threshold=args.spur_threshold,
        dp_tolerance=args.dp_tolerance,
        font_name=args.name,
        quiet=args.quiet,
    )

    save_font(font_dict, Path(args.out))

    # Summary
    total = len(font_dict["glyphs"])
    with_paths = sum(1 for v in font_dict["glyphs"].values() if v)
    print(f"Done: {with_paths}/{total} glyphs have strokes.")


if __name__ == "__main__":
    main()
