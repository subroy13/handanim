"""
Visual quality check for the skeleton pipeline.

For each requested glyph renders three panels side-by-side:
  [original filled outline]  [skeleton overlaid on outline]  [skeleton alone]

Each stroke in the skeleton is drawn in a distinct colour so you can see
where the pen lifts occur and whether the stroke count / ordering is sane.

Usage
-----
# Default set of symbols saved to tools/skeleton/showcase.png
poetry run python3 -m tools.skeleton.showcase

# Custom set of characters
poetry run python3 -m tools.skeleton.showcase --chars "A B ∑ ∫ ∞ α π"

# Specify font / json / output explicitly
poetry run python3 -m tools.skeleton.showcase \\
    --font assets/fonts/ttf/NotoSansMath-Regular.ttf \\
    --json assets/fonts/custom/noto_sans_math_skeleton.json \\
    --out  tools/skeleton/showcase.png \\
    --size 256
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from fontTools.ttLib import TTFont

# ---------------------------------------------------------------------------
# Default showcase set: a mix of Latin, Greek, and math symbols
# ---------------------------------------------------------------------------
_DEFAULT_CHARS = "A B E H I O R α β π Σ ∑ ∫ ∞ ∂ ∇ ≤ ≈"

# Colour cycle used for individual strokes
_STROKE_COLOURS = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231",
    "#911eb4", "#42d4f4", "#f032e6", "#bfef45",
    "#fabed4", "#469990", "#dcbeff", "#9a6324",
]


def _parse_svg_path(path_str: str) -> list[tuple[float, float]]:
    """
    Parse an "M x,y L x,y L x,y …" path string into a list of (x, y) points.

    Only M and L tokens are handled (the JSON format from export.py uses
    polyline paths only).
    """
    points: list[tuple[float, float]] = []
    tokens = path_str.split()
    for tok in tokens:
        if tok.startswith("M") or tok.startswith("L"):
            coords = tok[1:].split(",")
            points.append((float(coords[0]), float(coords[1])))
    return points


def _font_to_pixel(
    pts: list[tuple[float, float]],
    em: float,
    size: int,
) -> list[tuple[float, float]]:
    """Convert screen-unit (x, y) coords to pixel (col, row) for imshow.

    Coordinates in the skeleton JSON use Y-DOWN convention (y=0 at top,
    y=em at bottom), so the mapping to (col, row) is a straight scale.
    """
    scale = size / em
    return [(x * scale, y * scale) for x, y in pts]


def draw_glyph_row(
    axes: list[plt.Axes],
    bitmap: np.ndarray | None,
    json_paths: list[str],
    em: float,
    size: int,
    char: str,
) -> None:
    """Fill in one row of three axes for a single glyph."""
    ax_orig, ax_over, ax_skel = axes

    blank = np.zeros((size, size), dtype=np.uint8)

    for ax in axes:
        ax.set_xlim(0, size)
        ax.set_ylim(size, 0)
        ax.set_aspect("equal")
        ax.xaxis.set_major_locator(ticker.NullLocator())
        ax.yaxis.set_major_locator(ticker.NullLocator())

    # --- left panel: original bitmap ---
    bmp = bitmap if bitmap is not None else blank
    ax_orig.imshow(bmp, cmap="Greys", vmin=0, vmax=1, interpolation="nearest")
    ax_orig.set_title(f"'{char}'  original", fontsize=8)

    # --- middle + right panels: skeleton strokes ---
    ax_over.imshow(bmp, cmap="Greys", vmin=0, vmax=1, alpha=0.35, interpolation="nearest")
    ax_over.set_title("skeleton overlay", fontsize=8)
    ax_skel.set_facecolor("#f8f8f8")
    ax_skel.set_title("skeleton alone", fontsize=8)

    for i, path_str in enumerate(json_paths):
        colour = _STROKE_COLOURS[i % len(_STROKE_COLOURS)]
        pts = _parse_svg_path(path_str)
        if not pts:
            continue
        px = _font_to_pixel(pts, em, size)
        cols = [p[0] for p in px]
        rows = [p[1] for p in px]

        lw = 1.5
        ms = 3.0
        for ax in (ax_over, ax_skel):
            ax.plot(cols, rows, color=colour, linewidth=lw, solid_capstyle="round")
            # Mark endpoints so it's easy to see where each stroke starts/ends
            ax.plot(cols[0],  rows[0],  "o", color=colour, markersize=ms)
            ax.plot(cols[-1], rows[-1], "s", color=colour, markersize=ms)


def showcase(
    font_path: str,
    json_path: str,
    chars: list[str],
    size: int,
    out_path: str,
) -> None:
    # Load font and skeleton JSON
    ttfont = TTFont(font_path)
    cmap   = ttfont.getBestCmap()
    gset   = ttfont.getGlyphSet()
    em     = ttfont["head"].unitsPerEm

    with open(json_path, encoding="utf-8") as f:
        skel_json = json.load(f)
    glyphs_dict = skel_json["glyphs"]

    # Import here to avoid heavy deps at module level
    from tools.skeleton.rasterize import rasterize_glyph

    # Filter chars to those actually in the font
    valid = [(ch, ord(ch)) for ch in chars if ord(ch) in cmap]
    if not valid:
        print("None of the requested characters are in the font cmap.", file=sys.stderr)
        sys.exit(1)

    n = len(valid)
    fig, all_axes = plt.subplots(
        n, 3,
        figsize=(9, 3.0 * n),
        squeeze=False,
    )
    fig.suptitle(
        f"Skeleton quality check — {Path(font_path).name}",
        fontsize=11, y=1.0,
    )

    for row_idx, (ch, cp) in enumerate(valid):
        glyph_name = cmap[cp]
        try:
            bitmap = rasterize_glyph(gset, glyph_name, em, size=size)
        except Exception as exc:
            print(f"Warning: could not rasterise U+{cp:04X} '{ch}': {exc}")
            bitmap = None

        json_paths = glyphs_dict.get(str(cp), [])

        draw_glyph_row(
            axes=list(all_axes[row_idx]),
            bitmap=bitmap,
            json_paths=json_paths,
            em=float(em),
            size=size,
            char=ch,
        )

    fig.tight_layout()
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved showcase → {out}  ({n} glyphs, {n*3} panels)")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python3 -m tools.skeleton.showcase",
        description="Visual quality check for the skeleton pipeline.",
    )
    parser.add_argument(
        "--font",
        default="assets/fonts/ttf/NotoSansMath-Regular.ttf",
        help="TTF font file (default: NotoSansMath-Regular.ttf).",
    )
    parser.add_argument(
        "--json",
        default="assets/fonts/custom/noto_sans_math_skeleton.json",
        help="Skeleton JSON font file (default: noto_sans_math_skeleton.json).",
    )
    parser.add_argument(
        "--chars",
        default=_DEFAULT_CHARS,
        help="Space-separated characters to visualise (default: mixed set).",
    )
    parser.add_argument(
        "--out",
        default="tools/skeleton/showcase.png",
        help="Output PNG path (default: tools/skeleton/showcase.png).",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=256,
        help="Rasterisation size in pixels (default: 256).",
    )
    args = parser.parse_args(argv)

    font_path = Path(args.font)
    json_path = Path(args.json)

    if not font_path.exists():
        print(f"Font not found: {font_path}", file=sys.stderr)
        sys.exit(1)
    if not json_path.exists():
        print(f"Skeleton JSON not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    chars = [c for c in args.chars.split() if c]

    showcase(
        font_path=str(font_path),
        json_path=str(json_path),
        chars=chars,
        size=args.size,
        out_path=args.out,
    )


if __name__ == "__main__":
    main()
