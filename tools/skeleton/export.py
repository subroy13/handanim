"""
Assemble per-glyph SVG paths into the handanim custom JSON font format and
write to disk.

Custom font JSON schema
-----------------------
{
    "metadata": {
        "font_name": "<name>",
        "font_size": <em>         # coordinate reference height (= units_per_em)
    },
    "glyphs": {
        "<codepoint_int_as_str>": ["M x,y L x,y …", …],  # one string per stroke
        …
    }
}

Coordinate space: font units [0, em] in both axes; y increases upward.
An empty list for a codepoint means the glyph has no visible strokes
(whitespace, combining marks with no outline, etc.) and is intentionally
skipped.
"""

from __future__ import annotations

import json
from pathlib import Path

from fontTools.ttLib import TTFont
from tqdm import tqdm

from .rasterize import rasterize_glyph
from .skeletonize import extract_branches
from .stroke_order import order_strokes
from .vectorize import vectorize_branch


# ---------------------------------------------------------------------------
# Pre-defined codepoint sets
# ---------------------------------------------------------------------------

def _latin_math_codepoints(cmap: dict[int, str]) -> list[int]:
    """Latin A–Z / a–z, digits 0–9, common punctuation and ASCII operators."""
    ascii_printable = list(range(0x20, 0x7F))
    return [cp for cp in ascii_printable if cp in cmap]


def _math_preset_codepoints(cmap: dict[int, str]) -> list[int]:
    """Practical math subset: ASCII + Greek + common math operators + arrows."""
    ranges = [
        range(0x20,  0x7F),    # ASCII printable
        range(0x0391, 0x03CA), # Greek capitals + lowercase
        range(0x2200, 0x2300), # Math operators block
        range(0x2190, 0x21FF), # Arrows
        range(0x2308, 0x2310), # Ceiling/floor brackets
        range(0x27E8, 0x27EA), # Mathematical angle brackets
        range(0x1D400, 0x1D800), # Mathematical Alphanumeric Symbols (partial)
    ]
    cps: list[int] = []
    for r in ranges:
        for cp in r:
            if cp in cmap:
                cps.append(cp)
    return sorted(set(cps))


PRESETS = {
    "ascii":  _latin_math_codepoints,
    "math":   _math_preset_codepoints,
    "all":    lambda cmap: sorted(cmap.keys()),
}


# ---------------------------------------------------------------------------
# Core build function
# ---------------------------------------------------------------------------

def build_skeleton_font(
    font_path: str | Path,
    codepoints: list[int] | None = None,
    preset: str = "math",
    size: int = 512,
    spur_threshold: int = 8,
    dp_tolerance: float = 2.0,
    font_name: str | None = None,
    quiet: bool = False,
) -> dict:
    """
    Rasterise, thin, trace, and vectorise glyphs from a TTF font.

    Parameters
    ----------
    font_path:
        Path to the TTF font file.
    codepoints:
        Explicit list of Unicode codepoints to process.  If None, the preset
        is used.
    preset:
        One of "ascii", "math", "all".  Ignored when `codepoints` is given.
    size:
        Rasterisation bitmap size in pixels (square).  512 gives good quality.
    spur_threshold:
        Branches shorter than this (in pixels) between two junctions are
        pruned as junction-cluster artefacts.
    dp_tolerance:
        Douglas–Peucker tolerance in pixels (scaled to font units internally).
    font_name:
        Name stored in the JSON metadata.  Defaults to the font filename stem.
    quiet:
        Suppress progress bar.

    Returns
    -------
    dict with keys "metadata" and "glyphs".
    """
    font = TTFont(font_path)
    cmap = font.getBestCmap()
    glyph_set = font.getGlyphSet()
    em = font["head"].unitsPerEm

    if font_name is None:
        font_name = Path(font_path).stem

    if codepoints is None:
        builder = PRESETS.get(preset, PRESETS["math"])
        codepoints = builder(cmap)

    # Filter to codepoints actually present in the font
    codepoints = [cp for cp in codepoints if cp in cmap]

    glyphs: dict[str, list[str]] = {}
    skipped = 0

    it = tqdm(codepoints, desc="Skeletonising", unit="glyph", disable=quiet)
    for cp in it:
        glyph_name = cmap[cp]
        try:
            bitmap = rasterize_glyph(glyph_set, glyph_name, em, size=size)
        except Exception:
            skipped += 1
            continue

        if bitmap is None or not bitmap.any():
            # Whitespace / invisible glyph — store empty list so callers know
            # it's intentionally absent rather than missing from the JSON
            glyphs[str(cp)] = []
            continue

        branches = extract_branches(bitmap, spur_threshold=spur_threshold)
        if not branches:
            glyphs[str(cp)] = []
            continue

        ordered = order_strokes(branches)

        paths: list[str] = []
        for branch in ordered:
            svg = vectorize_branch(branch, em, size, tolerance=dp_tolerance)
            if svg:
                paths.append(svg)

        glyphs[str(cp)] = paths

    if skipped and not quiet:
        print(f"  Warning: {skipped} glyphs could not be rasterised and were skipped.")

    return {
        "metadata": {
            "font_name": font_name,
            "font_size": float(em),
        },
        "glyphs": glyphs,
    }


def save_font(font_dict: dict, output_path: str | Path) -> None:
    """Write the font dict to a JSON file with compact float formatting."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(font_dict, f, separators=(",", ":"), ensure_ascii=False)
    print(f"Saved {len(font_dict['glyphs'])} glyphs → {output_path}")
