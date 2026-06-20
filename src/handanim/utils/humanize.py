import numpy as np

from ..core.draw_ops import Ops, OpsSet, OpsType
from ..core.styles import StrokePressure


# ── Geometric bowing helpers ─────────────────────────────────────────────────

def bow_segment(
    start: tuple[float, float] | np.ndarray,
    end: tuple[float, float] | np.ndarray,
    amplitude: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (c1, c2) cubic Bézier control points that bow a segment naturally.

    Both control points share the same perpendicular displacement (no S-curve
    inflection) and sit at a shared random diverge fraction in [0.2, 0.4],
    matching the technique used in Line.draw_single_line.

    amplitude: maximum perpendicular displacement in world units.
    """
    start = np.asarray(start, dtype=float)
    end = np.asarray(end, dtype=float)
    delta = end - start
    length = float(np.linalg.norm(delta))
    if length < 1e-6:
        return start.copy(), end.copy()

    perp = np.array([-delta[1], delta[0]]) / length  # left-perpendicular unit vector
    side = np.random.uniform(-amplitude, amplitude)
    diverge = np.random.uniform(0.2, 0.4)

    c1 = start + delta * diverge + perp * side
    c2 = start + delta * 2 * diverge + perp * side
    return c1, c2


def jitter_point(
    pt: tuple[float, float] | np.ndarray,
    amplitude: float,
) -> np.ndarray:
    """Displace a point by uniform random noise in both axes."""
    return np.asarray(pt, dtype=float) + np.random.uniform(-amplitude, amplitude, size=2)


# ── OpsSet-level humanization passes ─────────────────────────────────────────

def apply_roughness(ops: OpsSet, roughness: float, font_size: float) -> OpsSet:
    """Replace LINE_TO segments with naturally bowed CURVE_TO segments.

    Amplitude = roughness * sqrt(length * font_size / 24), which keeps
    roughness dimensionless (≈ % of font_size for a full-height stroke)
    while giving shorter segments proportionally less wobble.  Uses
    bow_segment so both control points bow consistently to one side.
    """
    if roughness <= 0:
        return ops
    result = OpsSet(initial_set=[])
    current_pt = np.zeros(2)
    for op in ops.opsset:
        if op.type == OpsType.MOVE_TO and isinstance(op.data, list):
            current_pt = np.asarray(op.data[0], dtype=float)
            result.add(op)
        elif op.type == OpsType.LINE_TO and isinstance(op.data, list):
            end_pt = np.asarray(op.data[0], dtype=float)
            length = float(np.linalg.norm(end_pt - current_pt))
            if length > 0.5:
                amp = roughness * (length * font_size / 24) ** 0.5
                c1, c2 = bow_segment(current_pt, end_pt, amp)
                result.add(Ops(
                    OpsType.CURVE_TO,
                    [c1.tolist(), c2.tolist(), end_pt.tolist()],
                    op.partial,
                    op.meta,
                ))
            else:
                result.add(op)
            current_pt = end_pt
        else:
            result.add(op)
            if op.type == OpsType.CURVE_TO and isinstance(op.data, list):
                current_pt = np.asarray(op.data[-1], dtype=float)
            elif op.type == OpsType.QUAD_CURVE_TO and isinstance(op.data, list):
                current_pt = np.asarray(op.data[-1], dtype=float)
    return result


# ── Stroke post-processing (moved from stylings/strokes.py) ──────────────────

def apply_stroke_pressure(opsset: OpsSet, stroke_pressure: StrokePressure) -> OpsSet:
    """Apply variable pen width and opacity to simulate ink pressure.

    Interleaves SET_PEN updates at random intervals along the stroke so that
    width and opacity vary with a smooth sinusoidal profile over the full path.
    """
    def pressure_profile(t: float, min_val: float = 0.75, max_val: float = 1.25) -> float:
        mid = (min_val + max_val) / 2
        scale = (max_val - min_val) / 2
        return mid + scale * np.sin(2 * t * np.pi)

    new_opsset = OpsSet(initial_set=[])
    current_pen_ops = None
    n_opsset = len(opsset.opsset)
    for i, ops in enumerate(opsset.opsset):
        if ops.type == OpsType.SET_PEN:
            current_pen_ops = ops

        if i % np.random.randint(3, 6) == 0:
            if stroke_pressure == StrokePressure.CONSTANT:
                scale_width, scale_opacity = 1.0, 1.0
            else:
                scale_width = pressure_profile(i / n_opsset, min_val=0.5, max_val=2)
                if stroke_pressure == StrokePressure.PROPORTIONAL:
                    scale_opacity = pressure_profile(i / n_opsset, min_val=0.7, max_val=1)
                else:
                    scale_opacity = pressure_profile(i / n_opsset, min_val=1, max_val=0.7)
            if current_pen_ops is not None:
                pen_data = dict(current_pen_ops.data).copy()
                pen_data["width"] = pen_data.get("width", 1) * scale_width
                pen_data["opacity"] = pen_data.get("opacity", 1) * scale_opacity
                new_opsset.add(Ops(type=OpsType.SET_PEN, data=pen_data))

        new_opsset.add(ops)
    return new_opsset


def apply_strokes_gradient(
    opsset: OpsSet,
    start_color: tuple[float, float, float],
    end_color: tuple[float, float, float],
    n_steps: int = 10,
) -> OpsSet:
    """Interpolate SET_PEN colour linearly from start_color to end_color."""
    def lerp_color(a, b, t):
        return tuple((1 - t) * ca + t * cb for ca, cb in zip(a, b, strict=False))

    new_opsset = OpsSet(initial_set=[])
    current_pen_ops = None
    switch_at_idx = 0
    n_opsset = len(opsset.opsset)
    for i, ops in enumerate(opsset.opsset):
        if ops.type == OpsType.SET_PEN:
            current_pen_ops = ops

        if i >= switch_at_idx and current_pen_ops is not None:
            pen_data = dict(current_pen_ops.data).copy()
            pen_data["color"] = lerp_color(start_color, end_color, i / n_opsset)
            new_opsset.add(Ops(type=OpsType.SET_PEN, data=pen_data))
            switch_at_idx += round(n_opsset / n_steps)

        new_opsset.add(ops)
    return new_opsset
