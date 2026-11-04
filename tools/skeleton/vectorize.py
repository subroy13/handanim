"""
Convert pixel-coordinate branches to SVG path strings in font-unit space.

Pipeline per branch
-------------------
1.  Pixel (row, col)  →  font units (x, y)  via the inverse of the rasterise
    transform:  x = col * em / size,  y = (size − row) * em / size
2.  Douglas–Peucker simplification to remove collinear / near-collinear points.
3.  Format as an SVG polyline path: "M x0,y0 L x1,y1 L x2,y2 …"
    (LINE_TO segments; the rendering pipeline's apply_roughness converts these
     to natural-looking cubic Béziers at draw time).
"""

from __future__ import annotations

import math


# ---------------------------------------------------------------------------
# Coordinate transform
# ---------------------------------------------------------------------------

def pixels_to_font(
    branch: list[tuple[int, int]],
    em: int,
    size: int,
) -> list[tuple[float, float]]:
    """Convert (row, col) pixel coords to (x, y) screen-unit coords.

    Y increases downward (screen convention, matching handanimtype1 and the
    custom_glyph_opsset renderer).  Row 0 (top of bitmap) maps to y=0; row=size
    (bottom / baseline) maps to y=em.
    """
    scale = em / size
    return [(col * scale, row * scale) for row, col in branch]


# ---------------------------------------------------------------------------
# Douglas–Peucker simplification
# ---------------------------------------------------------------------------

def _perp_distance(
    point: tuple[float, float],
    line_start: tuple[float, float],
    line_end: tuple[float, float],
) -> float:
    """Perpendicular distance from `point` to the line through start→end."""
    x0, y0 = point
    x1, y1 = line_start
    x2, y2 = line_end
    dx, dy = x2 - x1, y2 - y1
    denom = math.hypot(dx, dy)
    if denom < 1e-9:
        return math.hypot(x0 - x1, y0 - y1)
    return abs(dx * (y1 - y0) - (x1 - x0) * dy) / denom


def _rdp(
    points: list[tuple[float, float]],
    lo: int,
    hi: int,
    tolerance: float,
    keep: list[bool],
) -> None:
    if hi <= lo + 1:
        return
    max_d, max_i = 0.0, lo
    for i in range(lo + 1, hi):
        d = _perp_distance(points[i], points[lo], points[hi])
        if d > max_d:
            max_d, max_i = d, i
    if max_d > tolerance:
        keep[max_i] = True
        _rdp(points, lo, max_i, tolerance, keep)
        _rdp(points, max_i, hi, tolerance, keep)


def simplify(
    coords: list[tuple[float, float]],
    tolerance: float = 2.0,
    min_points: int = 2,
) -> list[tuple[float, float]]:
    """
    Douglas–Peucker simplification.

    `tolerance` is in font units (same coordinate space as `coords`).
    Always preserves the first and last point.
    """
    n = len(coords)
    if n <= min_points:
        return list(coords)
    keep = [False] * n
    keep[0] = keep[-1] = True
    _rdp(coords, 0, n - 1, tolerance, keep)
    return [p for p, k in zip(coords, keep) if k]


# ---------------------------------------------------------------------------
# SVG path string builder
# ---------------------------------------------------------------------------

def to_svg_path(coords: list[tuple[float, float]]) -> str:
    """Emit an SVG polyline as "M x,y L x,y …" (handanim custom font format)."""
    if not coords:
        return ""
    parts = [f"M{coords[0][0]:.2f},{coords[0][1]:.2f}"]
    for x, y in coords[1:]:
        parts.append(f"L{x:.2f},{y:.2f}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Full branch vectorisation
# ---------------------------------------------------------------------------

def vectorize_branch(
    branch: list[tuple[int, int]],
    em: int,
    size: int,
    tolerance: float = 2.0,
) -> str | None:
    """
    Convert a pixel branch to a simplified SVG path string in font units.

    Returns None if the branch collapses to a single point after simplification.
    """
    font_coords = pixels_to_font(branch, em, size)
    simplified  = simplify(font_coords, tolerance=tolerance * em / size)
    if len(simplified) < 2:
        return None
    return to_svg_path(simplified)
