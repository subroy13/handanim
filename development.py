"""
development.py -- sample diagnostic scripts.
"""

import sys
import unicodedata
import numpy as np
import matplotlib.pyplot as plt
from HersheyFonts import HersheyFonts

from handanim.primitives.math import Math
from handanim.core.draw_ops import OpsSet, OpsType, Ops
from handanim.core.utils import get_bezier_points_from_quadcurve


def _sample_cubic_bezier(p0, p1, p2, p3, n=20):
    """Return n evenly-spaced points along a cubic Bezier curve."""
    t = np.linspace(0, 1, n)
    p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
    pts = (
        (1 - t) ** 3 * p0[:, None]
        + 3 * (1 - t) ** 2 * t * p1[:, None]
        + 3 * (1 - t) * t**2 * p2[:, None]
        + t**3 * p3[:, None]
    ).T  # shape (n, 2)
    return pts.tolist()


def visualize_opsset(opsset: OpsSet, title: str = "OpsSet strokes", flip_y: bool = True):
    """
    Plot every stroke in *opsset* as a separate line on a matplotlib figure.

    Each MOVE_TO starts a new stroke; LINE_TO / CURVE_TO / QUAD_CURVE_TO add
    sampled points. Control points are not shown — only the rendered path.

    Args:
        flip_y: Invert the y-axis so that the coordinate origin is at the
                top-left (matching screen/SVG conventions). Default True.
    """
    strokes: list[list[tuple[float, float]]] = []
    current_stroke: list[tuple[float, float]] = []
    current_pt: tuple[float, float] = (0.0, 0.0)

    for op in opsset.opsset:
        if op.type == OpsType.MOVE_TO and isinstance(op.data, list):
            if current_stroke:
                strokes.append(current_stroke)
            current_pt = tuple(op.data[0])
            current_stroke = [current_pt]

        elif op.type == OpsType.LINE_TO and isinstance(op.data, list):
            end_pt = tuple(op.data[0])
            current_stroke.append(end_pt)
            current_pt = end_pt

        elif op.type == OpsType.CURVE_TO and isinstance(op.data, list):
            p1, p2, p3 = op.data[0], op.data[1], op.data[2]
            pts = _sample_cubic_bezier(current_pt, p1, p2, p3)
            current_stroke.extend(tuple(p) for p in pts[1:])
            current_pt = tuple(p3)

        elif op.type == OpsType.QUAD_CURVE_TO and isinstance(op.data, list):
            q1, q2 = op.data[0], op.data[1]
            p1, p2, p3 = get_bezier_points_from_quadcurve(current_pt, q1, q2)
            pts = _sample_cubic_bezier(current_pt, p1, p2, p3)
            current_stroke.extend(tuple(p) for p in pts[1:])
            current_pt = tuple(q2)

        elif op.type == OpsType.CLOSE_PATH:
            if current_stroke:
                current_stroke.append(current_stroke[0])  # close loop visually

    if current_stroke:
        strokes.append(current_stroke)

    fig, ax = plt.subplots(figsize=(10, 6))
    cmap = plt.cm.tab10
    for i, stroke in enumerate(strokes):
        xs = [p[0] for p in stroke]
        ys = [p[1] for p in stroke]
        color = cmap(i % 10)
        ax.plot(xs, ys, color=color, linewidth=1.5)
        ax.plot(xs[0], ys[0], "o", color=color, markersize=4)  # stroke start

    bbox = opsset.get_bbox()
    ax.set_xlim(bbox.min_x - 2, bbox.max_x + 2)
    ax.set_ylim(bbox.min_y - 2, bbox.max_y + 2)
    if flip_y:
        ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.set_title(f"{title}  ({len(strokes)} strokes)")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


# ----------------------------------------------------------------------------

abc = Math(
    tex_expression=r"$\alpha + \beta = \gamma$",
    position=(0, 0),
)
parse_out = abc.parser.parse(abc.tex_expression)
glyphs = parse_out.glyphs  # (font, font_size, codepoint, offset_x, offset_y)
boxes = parse_out.rects  # (x, y, width, height) — fraction bars, vinculum, etc.

# ------------
# Check a single Hershey glyph

f_ml = HersheyFonts()
f_ml.load_default_font("greeks")
lines = list(f_ml.lines_for_text("a"))
print(lines)

ops = OpsSet(initial_set=[])
last_point = None
for p1, p2 in lines:
    if p1 != last_point:
        ops.add(Ops(OpsType.MOVE_TO, data=[p1]))
    ops.add(Ops(OpsType.LINE_TO, data=[p2]))
    last_point = p2

visualize_opsset(ops)
