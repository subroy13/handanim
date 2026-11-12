"""Scene-level page-turn (paper fold) and paper-crumple transition animations."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from ..core.animation import AnimationEvent, AnimationEventType
from ..core.draw_ops import Ops, OpsSet, OpsType
from ..core.viewport import Viewport
from .easing import ease_in_out


def _polygon_fill_and_stroke_ops(
    points: list[tuple[float, float]],
    fill_color: tuple[float, float, float] | None = None,
    fill_opacity: float = 1.0,
    stroke_color: tuple[float, float, float] | None = None,
    stroke_width: float = 2.5,
    stroke_opacity: float = 1.0,
) -> OpsSet:
    """Emit fill and/or stroke operations for a closed polygon."""
    ops = OpsSet(initial_set=[])
    if len(points) < 3:
        return ops

    if fill_color is not None and fill_opacity > 0.0:
        ops.add(
            Ops(
                OpsType.SET_PEN,
                {
                    "color": fill_color,
                    "opacity": float(np.clip(fill_opacity, 0.0, 1.0)),
                    "mode": "fill",
                },
            )
        )
        ops.add(Ops(OpsType.MOVE_TO, [points[0]]))
        for pt in points[1:]:
            ops.add(Ops(OpsType.LINE_TO, [pt]))
        ops.add(Ops(OpsType.CLOSE_PATH, {}))

    if stroke_color is not None and stroke_opacity > 0.0 and stroke_width > 0.0:
        ops.add(
            Ops(
                OpsType.SET_PEN,
                {
                    "color": stroke_color,
                    "width": float(stroke_width),
                    "opacity": float(np.clip(stroke_opacity, 0.0, 1.0)),
                    "mode": "stroke",
                },
            )
        )
        ops.add(Ops(OpsType.MOVE_TO, [points[0]]))
        for pt in points[1:]:
            ops.add(Ops(OpsType.LINE_TO, [pt]))
        ops.add(Ops(OpsType.CLOSE_PATH, {}))

    return ops


def _clip_polygon_halfplane(
    poly: list[tuple[float, float]],
    mid: tuple[float, float],
    normal: tuple[float, float],
    keep_positive: bool,
) -> list[tuple[float, float]]:
    """Sutherland-Hodgman polygon clipping against the half-plane `(P - mid) . normal >= 0` (or `<= 0`)."""
    if not poly:
        return []

    mx, my = mid
    nx, ny = normal
    sign = 1.0 if keep_positive else -1.0

    def _dist(p: tuple[float, float]) -> float:
        return ((p[0] - mx) * nx + (p[1] - my) * ny) * sign

    out: list[tuple[float, float]] = []
    n = len(poly)
    for i in range(n):
        curr_pt = poly[i]
        prev_pt = poly[(i - 1) % n]
        d_curr = _dist(curr_pt)
        d_prev = _dist(prev_pt)

        curr_in = d_curr >= -1e-7
        prev_in = d_prev >= -1e-7

        if curr_in:
            if not prev_in:
                denom = d_prev - d_curr
                t = d_prev / denom if abs(denom) > 1e-12 else 0.5
                ix = prev_pt[0] + t * (curr_pt[0] - prev_pt[0])
                iy = prev_pt[1] + t * (curr_pt[1] - prev_pt[1])
                out.append((ix, iy))
            out.append(curr_pt)
        elif prev_in:
            denom = d_prev - d_curr
            t = d_prev / denom if abs(denom) > 1e-12 else 0.5
            ix = prev_pt[0] + t * (curr_pt[0] - prev_pt[0])
            iy = prev_pt[1] + t * (curr_pt[1] - prev_pt[1])
            out.append((ix, iy))

    return out


def _reflect_point(
    pt: tuple[float, float],
    mid: tuple[float, float],
    normal: tuple[float, float],
) -> tuple[float, float]:
    """Reflect a 2D point across the line passing through `mid` with unit normal `normal`."""
    d = (pt[0] - mid[0]) * normal[0] + (pt[1] - mid[1]) * normal[1]
    return (pt[0] - 2.0 * d * normal[0], pt[1] - 2.0 * d * normal[1])


def _transform_opsset_points(
    opsset: OpsSet,
    point_fn,
    opacity_scale: float = 1.0,
) -> OpsSet:
    """Apply an arbitrary 2D point mapping `point_fn((x, y))` to every point in `opsset`."""
    out: list[Ops] = []
    for op in opsset.opsset:
        if op.type == OpsType.SET_PEN and isinstance(op.data, dict):
            new_pen = dict(op.data)
            if opacity_scale != 1.0:
                base_op = float(new_pen.get("opacity", 1.0))
                new_pen["opacity"] = float(np.clip(base_op * opacity_scale, 0.0, 1.0))
            out.append(Ops(op.type, new_pen, op.partial, dict(op.meta) if op.meta else None))
        elif op.type == OpsType.DOT and isinstance(op.data, dict):
            new_dot = dict(op.data)
            if "center" in new_dot:
                cx, cy = new_dot["center"]
                new_dot["center"] = point_fn((float(cx), float(cy)))
            out.append(Ops(op.type, new_dot, op.partial, dict(op.meta) if op.meta else None))
        elif op.type == OpsType.IMAGE and isinstance(op.data, dict):
            new_img = dict(op.data)
            ix, iy = float(new_img.get("x", 0.0)), float(new_img.get("y", 0.0))
            nx, ny = point_fn((ix, iy))
            new_img["x"] = nx
            new_img["y"] = ny
            new_img["opacity"] = float(new_img.get("opacity", 1.0)) * opacity_scale
            out.append(Ops(op.type, new_img, op.partial, dict(op.meta) if op.meta else None))
        elif isinstance(op.data, list):
            new_pts = [point_fn((float(x), float(y))) for x, y in op.data]
            out.append(Ops(op.type, new_pts, op.partial, dict(op.meta) if op.meta else None))
        else:
            out.append(op)
    return OpsSet(initial_set=out)


class SceneTransition(AnimationEvent):
    """Base class for scene-level page transitions (`PageTurnTransition`, `PaperCrumpleTransition`).

    When added to a `Scene` via `scene.add_transition(transition)` or `scene.add(transition)`:

    - All world drawables created before `transition.start_time` belong to the outgoing page
      and are automatically deactivated at `transition.end_time`.
    - Any world drawables created at or after `transition.start_time` belong to the newly
      revealed page underneath.
    - Camera-invariant `scene.overlay` drawables (e.g. `Captions`) remain untouched above the page.
    """

    sfx_type: str = "page_turn"

    def __init__(
        self,
        start_time: float = 0.0,
        duration: float = 1.0,
        easing_fun=ease_in_out,
        data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            type=AnimationEventType.MUTATION,
            start_time=start_time,
            duration=duration,
            easing_fun=easing_fun,
            data=data,
        )

    def _apply(self, opsset: OpsSet, progress: float) -> OpsSet:
        return opsset

    def apply_transition(
        self,
        outgoing_ops: OpsSet,
        incoming_ops: OpsSet,
        raw_progress: float,
        viewport: Viewport,
        background_color: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> OpsSet:
        """Compose the outgoing and incoming page `OpsSet`s at `raw_progress` in `[0, 1]`."""
        raise NotImplementedError


class PageTurnTransition(SceneTransition):
    """Folds and turns the current drawing sheet across the board to reveal the next page.

    Supported `direction` values:
    - ``"right_to_left"`` (default): Lifts the right side of the paper and folds it left.
    - ``"left_to_right"``: Lifts the left side of the paper and folds it right.
    - ``"bottom_right"`` (or ``"right_corner_to_left_corner"``): Peels the bottom-right corner diagonally across to top-left.
    - ``"bottom_left"`` (or ``"left_corner_to_right_corner"``): Peels the bottom-left corner diagonally across to top-right.
    - ``"top_right"``: Peels the top-right corner diagonally across to bottom-left.
    - ``"top_left"``: Peels the top-left corner diagonally across to bottom-right.
    - ``"bottom_to_top"``: Flips the bottom edge of the notepad upward.
    - ``"top_to_bottom"``: Flips the top edge downward.
    """

    sfx_type = "page_turn"

    VALID_DIRECTIONS = {
        "right_to_left",
        "left_to_right",
        "bottom_right",
        "bottom_left",
        "top_right",
        "top_left",
        "right_corner_to_left_corner",
        "left_corner_to_right_corner",
        "bottom_to_top",
        "top_to_bottom",
    }

    def __init__(
        self,
        start_time: float = 0.0,
        duration: float = 1.0,
        direction: str = "right_to_left",
        bleed_through: float = 0.16,
        flap_color: tuple[float, float, float] | None = None,
        border_color: tuple[float, float, float] = (0.32, 0.30, 0.27),
        shadow_opacity: float = 0.14,
        easing_fun=ease_in_out,
        data: dict[str, Any] | None = None,
    ) -> None:
        direction_norm = direction.lower().strip()
        if direction_norm not in self.VALID_DIRECTIONS:
            raise ValueError(f"Unsupported direction {direction!r}. Choose from {sorted(self.VALID_DIRECTIONS)}")
        super().__init__(
            start_time=start_time,
            duration=duration,
            easing_fun=easing_fun,
            data={
                **(data or {}),
                "direction": direction_norm,
                "bleed_through": float(bleed_through),
            },
        )
        self.direction = direction_norm
        self.bleed_through = float(np.clip(bleed_through, 0.0, 1.0))
        self.flap_color = flap_color
        self.border_color = border_color
        self.shadow_opacity = float(np.clip(shadow_opacity, 0.0, 1.0))

    def _get_peel_endpoints(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        """Return `(source_anchor, target_anchor)` for the lifted paper corner/edge."""
        w = x1 - x0
        h = y1 - y0
        cx = 0.5 * (x0 + x1)
        cy = 0.5 * (y0 + y1)

        d = self.direction
        if d == "right_to_left":
            # Slight natural upward lift as the right edge turns across to the left
            return (x1, cy + 0.08 * h), (x0 - 1.15 * w, cy - 0.10 * h)
        if d == "left_to_right":
            return (x0, cy + 0.08 * h), (x1 + 1.15 * w, cy - 0.10 * h)
        if d in ("bottom_right", "right_corner_to_left_corner"):
            return (x1, y1), (x0 - 0.95 * w, y0 - 0.95 * h)
        if d in ("bottom_left", "left_corner_to_right_corner"):
            return (x0, y1), (x1 + 0.95 * w, y0 - 0.95 * h)
        if d == "top_right":
            return (x1, y0), (x0 - 0.95 * w, y1 + 0.95 * h)
        if d == "top_left":
            return (x0, y0), (x1 + 0.95 * w, y1 + 0.95 * h)
        if d == "bottom_to_top":
            return (cx + 0.06 * w, y1), (cx - 0.08 * w, y0 - 1.15 * h)
        # top_to_bottom
        return (cx + 0.06 * w, y0), (cx - 0.08 * w, y1 + 1.15 * h)

    def apply_transition(
        self,
        outgoing_ops: OpsSet,
        incoming_ops: OpsSet,
        raw_progress: float,
        viewport: Viewport,
        background_color: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> OpsSet:
        p = float(np.clip(raw_progress, 0.0, 1.0))
        if self.easing_fun is not None:
            p = float(np.clip(self.easing_fun(p), 0.0, 1.0))

        if p <= 0.001:
            return outgoing_ops
        if p >= 0.999:
            return incoming_ops

        x0, x1 = float(viewport.world_xrange[0]), float(viewport.world_xrange[1])
        y0, y1 = float(viewport.world_yrange[0]), float(viewport.world_yrange[1])
        page_rect: list[tuple[float, float]] = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

        src_pt, dst_pt = self._get_peel_endpoints(x0, y0, x1, y1)
        # Interpolate lifted corner position A'(p)
        ax, ay = src_pt
        ap_x = ax + p * (dst_pt[0] - ax)
        ap_y = ay + p * (dst_pt[1] - ay)

        # Crease line L(p) is the perpendicular bisector of A and A'(p)
        mid = (0.5 * (ax + ap_x), 0.5 * (ay + ap_y))
        dx = ax - ap_x
        dy = ay - ap_y
        norm_len = math.hypot(dx, dy)
        if norm_len < 1e-6:
            return outgoing_ops
        normal = (dx / norm_len, dy / norm_len)  # points toward the lifted side A

        # Partition the page rectangle into stationary (d <= 0) and lifted/uncovered (d >= 0)
        stationary_poly = _clip_polygon_halfplane(page_rect, mid, normal, keep_positive=False)
        lifted_poly = _clip_polygon_halfplane(page_rect, mid, normal, keep_positive=True)
        flap_poly = [_reflect_point(pt, mid, normal) for pt in lifted_poly]

        result = OpsSet(initial_set=[])

        # 1. Revealed incoming page in the lifted region
        if len(lifted_poly) >= 3 and len(incoming_ops.opsset) > 0:
            result.add(Ops(OpsType.PUSH_CLIP, lifted_poly))
            result.extend(incoming_ops)
            result.add(Ops(OpsType.POP_CLIP, {}))

        # 2. Stationary unfolded portion of the outgoing page
        if len(stationary_poly) >= 3:
            result.extend(
                _polygon_fill_and_stroke_ops(
                    stationary_poly,
                    fill_color=background_color,
                    fill_opacity=1.0,
                )
            )
            if len(outgoing_ops.opsset) > 0:
                result.add(Ops(OpsType.PUSH_CLIP, stationary_poly))
                result.extend(outgoing_ops)
                result.add(Ops(OpsType.POP_CLIP, {}))

        # 3. Cast shadow along the crease line + Folded paper flap
        if len(flap_poly) >= 3:
            # Slightly offset shadow under the flap
            shadow_offset = max(8.0, 0.018 * (x1 - x0))
            shadow_poly = [(px + normal[0] * shadow_offset, py + normal[1] * shadow_offset) for px, py in flap_poly]
            result.add(Ops(OpsType.PUSH_CLIP, page_rect))
            result.extend(
                _polygon_fill_and_stroke_ops(
                    shadow_poly,
                    fill_color=(0.12, 0.11, 0.10),
                    fill_opacity=self.shadow_opacity * (1.0 - 0.3 * p),
                )
            )

            # Backside of the lifted sheet (slightly warmer/darker than front background_color)
            back_color = self.flap_color or (
                max(0.0, background_color[0] * 0.94 - 0.01),
                max(0.0, background_color[1] * 0.93 - 0.015),
                max(0.0, background_color[2] * 0.90 - 0.02),
            )
            result.extend(
                _polygon_fill_and_stroke_ops(
                    flap_poly,
                    fill_color=back_color,
                    fill_opacity=0.98,
                )
            )

            # Reflected bleed-through of outgoing drawings on the back of the folded flap
            if self.bleed_through > 0.0 and len(outgoing_ops.opsset) > 0:
                reflected_ops = _transform_opsset_points(
                    outgoing_ops,
                    lambda pt: _reflect_point(pt, mid, normal),
                    opacity_scale=self.bleed_through,
                )
                result.add(Ops(OpsType.PUSH_CLIP, flap_poly))
                result.extend(reflected_ops)
                result.add(Ops(OpsType.POP_CLIP, {}))

            # Sketchy hand-drawn outline around the folded flap and crease
            result.extend(
                _polygon_fill_and_stroke_ops(
                    flap_poly,
                    stroke_color=self.border_color,
                    stroke_width=2.8,
                    stroke_opacity=0.85,
                )
            )
            result.add(Ops(OpsType.POP_CLIP, {}))

        return result


class PaperCrumpleTransition(SceneTransition):
    """Crumples the current sheet of paper into a jagged paper ball and tosses it off to the side.

    Supported `direction` values:
    - ``"right"`` (default): Crumples toward center and tosses off the right edge.
    - ``"left"``: Crumples toward center and tosses off the left edge.
    - ``"top_right"``, ``"bottom_right"``, ``"top_left"``, ``"bottom_left"``
    """

    sfx_type = "crumple"

    VALID_DIRECTIONS = {
        "right",
        "left",
        "top_right",
        "bottom_right",
        "top_left",
        "bottom_left",
    }

    def __init__(
        self,
        start_time: float = 0.0,
        duration: float = 1.0,
        direction: str = "right",
        seed: int = 42,
        paper_color: tuple[float, float, float] | None = None,
        border_color: tuple[float, float, float] = (0.32, 0.30, 0.27),
        easing_fun=ease_in_out,
        data: dict[str, Any] | None = None,
    ) -> None:
        direction_norm = direction.lower().strip()
        if direction_norm not in self.VALID_DIRECTIONS:
            raise ValueError(f"Unsupported direction {direction!r}. Choose from {sorted(self.VALID_DIRECTIONS)}")
        super().__init__(
            start_time=start_time,
            duration=duration,
            easing_fun=easing_fun,
            data={
                **(data or {}),
                "direction": direction_norm,
                "seed": int(seed),
            },
        )
        self.direction = direction_norm
        self.seed = int(seed)
        self.paper_color = paper_color
        self.border_color = border_color

        # Pre-generate deterministic crumple geometry in normalized [-1, 1]^2 sheet coordinates
        rng = np.random.default_rng(self.seed)
        self._n_perim = 28
        self._perim_radii = rng.uniform(0.68, 1.26, size=self._n_perim)
        self._perim_angle_jitter = rng.uniform(-0.09, 0.09, size=self._n_perim)

        # Internal facet vertices for 3D crumpled paper creases
        n_inner = 12
        inner_angles = np.linspace(0.0, 2.0 * math.pi, n_inner, endpoint=False) + rng.uniform(-0.2, 0.2, size=n_inner)
        inner_r = rng.uniform(0.22, 0.65, size=n_inner)
        self._inner_pts = [(float(r * math.cos(a)), float(r * math.sin(a))) for r, a in zip(inner_r, inner_angles, strict=False)]
        self._facet_shades = rng.uniform(0.86, 0.97, size=self._n_perim)

    @staticmethod
    def _rect_perimeter_point(t_norm: float) -> tuple[float, float]:
        """Map `t_norm` in `[0, 1)` around the perimeter of `[-1, 1]^2`."""
        s = (t_norm % 1.0) * 4.0
        if s < 1.0:
            return (-1.0 + 2.0 * s, -1.0)
        if s < 2.0:
            return (1.0, -1.0 + 2.0 * (s - 1.0))
        if s < 3.0:
            return (1.0 - 2.0 * (s - 2.0), 1.0)
        return (-1.0, 1.0 - 2.0 * (s - 3.0))

    def _get_toss_vector(self, w: float, h: float) -> tuple[float, float, float]:
        """Return `(dx, dy, spin_degrees)` for the toss phase."""
        d = self.direction
        if d == "left":
            return (-0.82 * w, 0.12 * h, -260.0)
        if d == "top_right":
            return (0.80 * w, -0.55 * h, 240.0)
        if d == "bottom_right":
            return (0.80 * w, 0.55 * h, 280.0)
        if d == "top_left":
            return (-0.80 * w, -0.55 * h, -240.0)
        if d == "bottom_left":
            return (-0.80 * w, 0.55 * h, -280.0)
        # default "right"
        return (0.82 * w, 0.12 * h, 260.0)

    def apply_transition(
        self,
        outgoing_ops: OpsSet,
        incoming_ops: OpsSet,
        raw_progress: float,
        viewport: Viewport,
        background_color: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> OpsSet:
        p = float(np.clip(raw_progress, 0.0, 1.0))
        if self.easing_fun is not None:
            p = float(np.clip(self.easing_fun(p), 0.0, 1.0))

        if p <= 0.001:
            return outgoing_ops
        if p >= 0.999:
            return incoming_ops

        x0, x1 = float(viewport.world_xrange[0]), float(viewport.world_xrange[1])
        y0, y1 = float(viewport.world_yrange[0]), float(viewport.world_yrange[1])
        w = x1 - x0
        h = y1 - y0
        cx0 = 0.5 * (x0 + x1)
        cy0 = 0.5 * (y0 + y1)

        # Phase 1: Crunch sheet into a ball (p: 0 -> 0.65)
        crunch = float(np.clip(p / 0.65, 0.0, 1.0))
        crunch_smooth = crunch * crunch * (3.0 - 2.0 * crunch)

        # Phase 2: Toss the crumpled ball off to the side along a parabolic arc (p: 0.45 -> 1.0)
        toss = float(np.clip((p - 0.45) / 0.55, 0.0, 1.0))
        toss_quad = toss * toss

        dx_target, dy_target, total_spin_deg = self._get_toss_vector(w, h)
        # Parabolic arc lift (-sin(pi * toss)) + slight hand-grab shake during crunch
        shake_x = 0.012 * w * math.sin(crunch * 5.0 * math.pi) * (1.0 - toss)
        shake_y = 0.010 * h * math.cos(crunch * 4.0 * math.pi) * (1.0 - toss)
        arc_lift = -0.16 * h * math.sin(math.pi * toss)

        ball_cx = cx0 + shake_x + dx_target * toss_quad
        ball_cy = cy0 + shake_y + dy_target * toss_quad + arc_lift

        spin_rad = math.radians(total_spin_deg * (0.15 * crunch_smooth + 0.85 * toss_quad))
        cos_s = math.cos(spin_rad)
        sin_s = math.sin(spin_rad)

        # Ball radius when fully crumpled (~16% of min dimension)
        ball_radius = 0.16 * min(w, h) * (1.0 - 0.18 * toss)

        def _map_norm_pt(nx: float, ny: float) -> tuple[float, float]:
            """Map normalized sheet coordinate `(nx, ny)` in `[-1, 1]^2` to world position at progress `p`."""
            # Flat world offset from center
            flat_dx = nx * (0.5 * w)
            flat_dy = ny * (0.5 * h)

            # Accordion spatial fold waves + radial contraction toward ball
            r = math.hypot(nx, ny)
            theta = math.atan2(ny, nx)
            fold_wave = 0.22 * math.sin(3.5 * nx + 2.5 * ny + 1.2) + 0.15 * math.cos(4.0 * nx - 3.0 * ny)
            target_r = ball_radius * min(1.15, 0.35 + 0.65 * r) * (1.0 + fold_wave * 0.45)
            target_theta = theta + fold_wave * 0.35

            crumpled_dx = target_r * math.cos(target_theta)
            crumpled_dy = target_r * math.sin(target_theta)

            # Blend from flat sheet to crumpled ball
            lx = (1.0 - crunch_smooth) * flat_dx + crunch_smooth * crumpled_dx
            ly = (1.0 - crunch_smooth) * flat_dy + crunch_smooth * crumpled_dy

            # Apply spin rotation and ball center translation
            rx = cos_s * lx - sin_s * ly
            ry = sin_s * lx + cos_s * ly
            return (ball_cx + rx, ball_cy + ry)

        # Build the outer perimeter polygon of the crumpling sheet
        perim_world: list[tuple[float, float]] = []
        for k in range(self._n_perim):
            t_norm = k / self._n_perim
            rx0, ry0 = self._rect_perimeter_point(t_norm)
            flat_dx = rx0 * (0.5 * w)
            flat_dy = ry0 * (0.5 * h)

            base_ang = math.atan2(ry0, rx0) + float(self._perim_angle_jitter[k])
            rad_k = ball_radius * float(self._perim_radii[k])
            crumpled_dx = rad_k * math.cos(base_ang)
            crumpled_dy = rad_k * math.sin(base_ang)

            lx = (1.0 - crunch_smooth) * flat_dx + crunch_smooth * crumpled_dx
            ly = (1.0 - crunch_smooth) * flat_dy + crunch_smooth * crumpled_dy
            wx = ball_cx + cos_s * lx - sin_s * ly
            wy = ball_cy + sin_s * lx + cos_s * ly
            perim_world.append((wx, wy))

        result = OpsSet(initial_set=[])

        # 1. Incoming new page is drawn across the clean board underneath
        if len(incoming_ops.opsset) > 0:
            result.extend(incoming_ops)

        # 2. Drop shadow underneath the crumpling sheet / ball
        shadow_shift = 10.0 + 18.0 * crunch_smooth
        shadow_poly = [(px + shadow_shift, py + shadow_shift) for px, py in perim_world]
        result.extend(
            _polygon_fill_and_stroke_ops(
                shadow_poly,
                fill_color=(0.12, 0.11, 0.10),
                fill_opacity=0.14 * (1.0 - 0.3 * toss),
            )
        )

        # 3. Base fill of the crumpling paper sheet
        sheet_color = self.paper_color or background_color
        result.extend(
            _polygon_fill_and_stroke_ops(
                perim_world,
                fill_color=sheet_color,
                fill_opacity=1.0,
            )
        )

        # 4. Warped outgoing drawings clipped inside the crumpling paper boundary
        if len(outgoing_ops.opsset) > 0:
            def _warp_world_pt(pt: tuple[float, float]) -> tuple[float, float]:
                nx = (pt[0] - cx0) / max(1.0, 0.5 * w)
                ny = (pt[1] - cy0) / max(1.0, 0.5 * h)
                return _map_norm_pt(nx, ny)

            warped_outgoing = _transform_opsset_points(
                outgoing_ops,
                _warp_world_pt,
                opacity_scale=max(0.25, 1.0 - 0.65 * crunch_smooth),
            )
            result.add(Ops(OpsType.PUSH_CLIP, perim_world))
            result.extend(warped_outgoing)
            result.add(Ops(OpsType.POP_CLIP, {}))

        # 5. Shaded 3D paper facets & hand-drawn internal crease ridges (ramp in as crunch progresses)
        if crunch_smooth > 0.05:
            inner_world = [_map_norm_pt(ix, iy) for ix, iy in self._inner_pts]
            n_inner = len(inner_world)
            crease_opacity = float(np.clip(crunch_smooth * 0.85, 0.0, 0.85))
            facet_fill_alpha = float(np.clip(crunch_smooth * 0.55, 0.0, 0.55))

            # Triangular facets connecting perimeter vertices to inner crease vertices
            for k in range(0, self._n_perim, 2):
                p_a = perim_world[k]
                p_b = perim_world[(k + 2) % self._n_perim]
                in_pt = inner_world[(k // 2) % n_inner]
                shade = float(self._facet_shades[k])
                f_color = (
                    max(0.0, sheet_color[0] * shade),
                    max(0.0, sheet_color[1] * shade),
                    max(0.0, sheet_color[2] * (shade - 0.02)),
                )
                result.extend(
                    _polygon_fill_and_stroke_ops(
                        [p_a, p_b, in_pt],
                        fill_color=f_color,
                        fill_opacity=facet_fill_alpha,
                        stroke_color=self.border_color,
                        stroke_width=1.8,
                        stroke_opacity=crease_opacity * 0.75,
                    )
                )

            # Star/web of central crumple ridges connecting inner vertices
            for j in range(n_inner):
                p1 = inner_world[j]
                p2 = inner_world[(j + 1) % n_inner]
                p3 = inner_world[(j + 3) % n_inner]
                result.extend(
                    _polygon_fill_and_stroke_ops(
                        [p1, p2, p3],
                        stroke_color=self.border_color,
                        stroke_width=2.0,
                        stroke_opacity=crease_opacity,
                    )
                )

        # 6. Crisp outer border of the crumpling paper sheet
        result.extend(
            _polygon_fill_and_stroke_ops(
                perim_world,
                stroke_color=self.border_color,
                stroke_width=2.8,
                stroke_opacity=0.9,
            )
        )

        return result


__all__ = [
    "SceneTransition",
    "PageTurnTransition",
    "PaperCrumpleTransition",
]
