"""
Rasterize TTF glyph outlines to binary bitmaps using cairo + svgelements.

Coordinate convention
---------------------
The bitmap has (row=0) at the top and (col=0) at the left.  The transform
applied by `rasterize_glyph` maps font units to pixels as:

    col  =  x_font * size / em
    row  =  size  - y_font * size / em

so that y=0 (baseline) lands at the bottom row and y=em lands at row=0.
To convert back:  x_font = col * em / size,  y_font = (size − row) * em / size.
"""

from __future__ import annotations

import cairo
import numpy as np
from fontTools.pens.svgPathPen import SVGPathPen
from svgelements import Close, CubicBezier
from svgelements import Line as SVGLine
from svgelements import Move, Path as SVGPath, QuadraticBezier


def _draw_svg_path(ctx: cairo.Context, svg_path_str: str) -> None:
    """Parse an SVG path string and replay it onto a Cairo context."""
    for seg in SVGPath(svg_path_str).segments():
        if isinstance(seg, Move):
            ctx.move_to(seg.end.x, seg.end.y)
        elif isinstance(seg, SVGLine):
            ctx.line_to(seg.end.x, seg.end.y)
        elif isinstance(seg, CubicBezier):
            ctx.curve_to(
                seg.control1.x, seg.control1.y,
                seg.control2.x, seg.control2.y,
                seg.end.x, seg.end.y,
            )
        elif isinstance(seg, QuadraticBezier):
            # Elevate quadratic to cubic
            p0 = ctx.get_current_point()
            q1 = (seg.control.x, seg.control.y)
            q2 = (seg.end.x, seg.end.y)
            c1 = (p0[0] + 2/3 * (q1[0] - p0[0]), p0[1] + 2/3 * (q1[1] - p0[1]))
            c2 = (q2[0] + 2/3 * (q1[0] - q2[0]), q2[1] + 2/3 * (q1[1] - q2[1]))
            ctx.curve_to(c1[0], c1[1], c2[0], c2[1], q2[0], q2[1])
        elif isinstance(seg, Close):
            ctx.close_path()


def rasterize_glyph(
    glyph_set,
    glyph_name: str,
    em: int,
    size: int = 512,
) -> np.ndarray | None:
    """
    Render one glyph outline to a binary boolean bitmap of shape (size, size).

    Returns None if the glyph has no contour data (e.g. whitespace).
    """
    pen = SVGPathPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    svg_path_str = pen.getCommands()
    if not svg_path_str.strip():
        return None

    surface = cairo.ImageSurface(cairo.FORMAT_A8, size, size)
    ctx = cairo.Context(surface)

    # Map font units → pixels with Y-flip so baseline is at the bottom
    ctx.scale(size / em, -size / em)
    ctx.translate(0, -em)

    _draw_svg_path(ctx, svg_path_str)

    ctx.set_source_rgba(1, 1, 1, 1)
    ctx.fill()

    buf = surface.get_data()
    arr = np.frombuffer(buf, dtype=np.uint8).copy().reshape(size, size)
    return arr > 127
