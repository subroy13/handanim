"""MorphAnimation: Smooth path and stroke interpolation between two drawables."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..core.animation import AnimationEvent, AnimationEventType
from ..core.draw_ops import Ops, OpsSet, OpsType
from ..core.drawable import Drawable
from ..utils.geometry import get_bezier_points_from_quadcurve


def _extract_subpaths(opsset: OpsSet) -> list[tuple[dict[str, Any], np.ndarray]]:
    """Convert an `OpsSet` into a list of `(pen_dict, points_Nx2)` polyline subpaths."""
    subpaths: list[tuple[dict[str, Any], np.ndarray]] = []
    current_pen: dict[str, Any] = {"color": (0.0, 0.0, 0.0), "width": 2.0, "opacity": 1.0, "mode": "stroke"}
    current_pts: list[tuple[float, float]] = []
    last_pt: tuple[float, float] = (0.0, 0.0)

    def _flush() -> None:
        nonlocal current_pts
        if len(current_pts) >= 2:
            subpaths.append((dict(current_pen), np.array(current_pts, dtype=float)))
        elif len(current_pts) == 1:
            pt = current_pts[0]
            subpaths.append((dict(current_pen), np.array([pt, pt], dtype=float)))
        current_pts = []

    for op in opsset.opsset:
        if op.type == OpsType.SET_PEN and isinstance(op.data, dict):
            _flush()
            current_pen = {
                "color": tuple(op.data.get("color", (0.0, 0.0, 0.0))),
                "width": float(op.data.get("width", 2.0)),
                "opacity": float(op.data.get("opacity", 1.0)),
                "mode": str(op.data.get("mode", "stroke")),
            }
        elif op.type == OpsType.MOVE_TO and isinstance(op.data, (list, tuple)) and len(op.data) >= 1:
            _flush()
            pt = (float(op.data[0][0]), float(op.data[0][1]))
            current_pts = [pt]
            last_pt = pt
        elif op.type == OpsType.LINE_TO and isinstance(op.data, (list, tuple)) and len(op.data) >= 1:
            pt = (float(op.data[0][0]), float(op.data[0][1]))
            if not current_pts:
                current_pts = [last_pt]
            current_pts.append(pt)
            last_pt = pt
        elif op.type == OpsType.CURVE_TO and isinstance(op.data, (list, tuple)) and len(op.data) >= 3:
            if not current_pts:
                current_pts = [last_pt]
            p0 = np.array(last_pt, dtype=float)
            p1 = np.array([float(op.data[0][0]), float(op.data[0][1])], dtype=float)
            p2 = np.array([float(op.data[1][0]), float(op.data[1][1])], dtype=float)
            p3 = np.array([float(op.data[2][0]), float(op.data[2][1])], dtype=float)
            for s in np.linspace(0.125, 1.0, 8):
                u = 1.0 - s
                b = (u**3) * p0 + 3 * (u**2) * s * p1 + 3 * u * (s**2) * p2 + (s**3) * p3
                current_pts.append((float(b[0]), float(b[1])))
            last_pt = (float(p3[0]), float(p3[1]))
        elif op.type == OpsType.QUAD_CURVE_TO and isinstance(op.data, (list, tuple)) and len(op.data) >= 2:
            if not current_pts:
                current_pts = [last_pt]
            q0 = last_pt
            q1 = (float(op.data[0][0]), float(op.data[0][1]))
            q2 = (float(op.data[1][0]), float(op.data[1][1]))
            c1, c2, c3 = get_bezier_points_from_quadcurve(q0, q1, q2)
            p0 = np.array(q0, dtype=float)
            p1 = np.array(c1, dtype=float)
            p2 = np.array(c2, dtype=float)
            p3 = np.array(c3, dtype=float)
            for s in np.linspace(0.125, 1.0, 8):
                u = 1.0 - s
                b = (u**3) * p0 + 3 * (u**2) * s * p1 + 3 * u * (s**2) * p2 + (s**3) * p3
                current_pts.append((float(b[0]), float(b[1])))
            last_pt = q2
        elif op.type == OpsType.CLOSE_PATH:
            if len(current_pts) >= 2:
                current_pts.append(current_pts[0])
                last_pt = current_pts[0]
            _flush()
        elif op.type == OpsType.DOT and isinstance(op.data, dict):
            _flush()
            center = op.data.get("center", (0.0, 0.0))
            r = float(op.data.get("radius", 2.0))
            cx, cy = float(center[0]), float(center[1])
            angles = np.linspace(0.0, 2.0 * np.pi, 13)
            circle_pts = np.column_stack([cx + r * np.cos(angles), cy + r * np.sin(angles)])
            subpaths.append((dict(current_pen), circle_pts))

    _flush()
    return subpaths


def _resample_polyline(pts: np.ndarray, n_points: int) -> np.ndarray:
    """Resample an `N x 2` polyline uniformly by arc length to `n_points x 2`."""
    if len(pts) == 0:
        return np.zeros((n_points, 2), dtype=float)
    if len(pts) == 1:
        return np.repeat(pts[:1], n_points, axis=0)
    diffs = np.diff(pts, axis=0)
    seg_lengths = np.linalg.norm(diffs, axis=1)
    total_len = float(np.sum(seg_lengths))
    if total_len < 1e-8:
        return np.repeat(pts[:1], n_points, axis=0)
    cum = np.concatenate([[0.0], np.cumsum(seg_lengths)])
    targets = np.linspace(0.0, total_len, n_points)
    x_new = np.interp(targets, cum, pts[:, 0])
    y_new = np.interp(targets, cum, pts[:, 1])
    return np.column_stack([x_new, y_new])


def _match_subpath_lists(
    src_list: list[tuple[dict[str, Any], np.ndarray]],
    tgt_list: list[tuple[dict[str, Any], np.ndarray]],
    points_per_subpath: int = 24,
) -> tuple[list[tuple[dict[str, Any], np.ndarray]], list[tuple[dict[str, Any], np.ndarray]]]:
    """Ensure `src_list` and `tgt_list` have the same number of resampled subpaths."""
    if not src_list and not tgt_list:
        return [], []
    if not src_list:
        center = np.mean(np.vstack([pts for _, pts in tgt_list]), axis=0)
        src_list = [(tgt_list[0][0], np.array([center, center], dtype=float))]
    if not tgt_list:
        center = np.mean(np.vstack([pts for _, pts in src_list]), axis=0)
        tgt_list = [(src_list[0][0], np.array([center, center], dtype=float))]

    m = max(len(src_list), len(tgt_list))
    matched_src: list[tuple[dict[str, Any], np.ndarray]] = []
    matched_tgt: list[tuple[dict[str, Any], np.ndarray]] = []

    for i in range(m):
        s_pen, s_pts = src_list[int(i * len(src_list) / m)]
        t_pen, t_pts = tgt_list[int(i * len(tgt_list) / m)]
        matched_src.append((s_pen, _resample_polyline(s_pts, points_per_subpath)))
        matched_tgt.append((t_pen, _resample_polyline(t_pts, points_per_subpath)))

    return matched_src, matched_tgt


class MorphAnimation(AnimationEvent):
    """Smoothly morphs the stroke paths, colors, and widths of a drawable into `target`.

    Usage::

        scene.add(SketchAnimation(start_time=0.0, duration=1.5), circle)
        scene.add(MorphAnimation(target_drawable=square, start_time=2.0, duration=1.5), circle)
    """

    def __init__(
        self,
        target_drawable: Drawable | OpsSet | None = None,
        start_time: float = 0.0,
        duration: float = 1.0,
        easing_fun=None,
        points_per_subpath: int = 24,
        data: dict | None = None,
    ) -> None:
        data_dict = dict(data) if data else {}
        if target_drawable is None:
            target_drawable = data_dict.get("target_drawable")
        self.target_drawable = target_drawable
        self.points_per_subpath = int(data_dict.get("points_per_subpath", points_per_subpath))
        data_dict["target_drawable"] = self.target_drawable
        data_dict["points_per_subpath"] = self.points_per_subpath
        super().__init__(AnimationEventType.MUTATION, start_time, duration, easing_fun, data_dict)
        self._cached_target_ops: OpsSet | None = None

    def _get_target_opsset(self) -> OpsSet:
        if self._cached_target_ops is not None:
            return self._cached_target_ops
        if isinstance(self.target_drawable, OpsSet):
            self._cached_target_ops = self.target_drawable
        elif isinstance(self.target_drawable, Drawable):
            self._cached_target_ops = self.target_drawable.draw()
        else:
            self._cached_target_ops = OpsSet(initial_set=[])
        return self._cached_target_ops

    def _apply(self, opsset: OpsSet, progress: float) -> OpsSet:
        p = float(np.clip(progress, 0.0, 1.0))
        if p <= 0.0:
            return opsset
        target_ops = self._get_target_opsset()
        if p >= 1.0:
            return target_ops

        src_sub = _extract_subpaths(opsset)
        tgt_sub = _extract_subpaths(target_ops)
        matched_src, matched_tgt = _match_subpath_lists(
            src_sub,
            tgt_sub,
            points_per_subpath=self.points_per_subpath,
        )

        out_ops: list[Ops] = []
        for (s_pen, s_pts), (t_pen, t_pts) in zip(matched_src, matched_tgt, strict=False):
            sc = np.array(s_pen.get("color", (0.0, 0.0, 0.0)), dtype=float)
            tc = np.array(t_pen.get("color", (0.0, 0.0, 0.0)), dtype=float)
            col = tuple(float(v) for v in ((1.0 - p) * sc + p * tc))
            width = (1.0 - p) * float(s_pen.get("width", 2.0)) + p * float(t_pen.get("width", 2.0))
            opacity = (1.0 - p) * float(s_pen.get("opacity", 1.0)) + p * float(t_pen.get("opacity", 1.0))
            mode = t_pen.get("mode", "stroke") if p >= 0.5 else s_pen.get("mode", "stroke")

            interp_pts = (1.0 - p) * s_pts + p * t_pts
            out_ops.append(
                Ops(
                    type=OpsType.SET_PEN,
                    data={"color": col, "width": width, "opacity": opacity, "mode": mode},
                )
            )
            out_ops.append(Ops(type=OpsType.MOVE_TO, data=[(float(interp_pts[0, 0]), float(interp_pts[0, 1]))]))
            for pt in interp_pts[1:]:
                out_ops.append(Ops(type=OpsType.LINE_TO, data=[(float(pt[0]), float(pt[1]))]))
            if mode == "fill":
                out_ops.append(Ops(type=OpsType.CLOSE_PATH, data={}))

        return OpsSet(initial_set=out_ops)
