"""
Tests for RotateAnimation.

Structure
---------
- TestRotateAnimationBasics    — type, angle param, center param, easing
- TestRotateAnimationGeometry  — coordinate transforms at progress 0 / 0.5 / 1
- TestRotateAnimationCenter    — custom pivot vs center-of-gravity pivot
- TestRotateVisual             — visual regression snapshot
"""

import io
import math

import numpy as np
import pytest
from skimage.metrics import structural_similarity as ssim
from skimage import io as skio

from handanim.core.animation import AnimationEventType
from handanim.core.draw_ops import Ops, OpsSet, OpsType
from handanim.animations.rotate import RotateAnimation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hline_opsset(x0=100.0, x1=200.0, y=0.0, color=(0.0, 0.0, 0.0)) -> OpsSet:
    ops = OpsSet(initial_set=[])
    ops.add(Ops(OpsType.SET_PEN, {"color": color, "width": 2}))
    ops.add(Ops(OpsType.MOVE_TO, [(x0, y)]))
    ops.add(Ops(OpsType.LINE_TO, [(x1, y)]))
    return ops


def _extract_points(opsset: OpsSet):
    pts = []
    for op in opsset.opsset:
        if op.type in (OpsType.MOVE_TO, OpsType.LINE_TO):
            pts.extend(op.data)
    return pts


def _rotate_opsset() -> OpsSet:
    from handanim.primitives.polygons import Rectangle
    from handanim.core.styles import StrokeStyle, SketchStyle

    rect = Rectangle(
        top_left=(300.0, 275.0),
        width=200.0,
        height=100.0,
        stroke_style=StrokeStyle(color=(0.1, 0.1, 0.6), width=2),
        sketch_style=SketchStyle(roughness=1),
    )
    anim = RotateAnimation(start_time=0, duration=1.0, data={"angle": 45})
    return anim.apply(rect.draw(), raw_progress=1.0)


# ---------------------------------------------------------------------------
# Basics
# ---------------------------------------------------------------------------

class TestRotateAnimationBasics:
    def test_type_is_mutation(self):
        assert RotateAnimation(start_time=0, duration=1.0).type == AnimationEventType.MUTATION

    def test_default_angle_is_360(self):
        assert RotateAnimation(start_time=0, duration=1.0).angle == 360

    def test_custom_angle_stored(self):
        assert RotateAnimation(start_time=0, duration=1.0, data={"angle": 90}).angle == 90

    def test_no_center_defaults_to_none(self):
        assert RotateAnimation(start_time=0, duration=1.0).center is None

    def test_custom_center_stored(self):
        anim = RotateAnimation(start_time=0, duration=1.0, data={"center": (50.0, 75.0)})
        assert anim.center == (50.0, 75.0)

    def test_apply_returns_opsset(self):
        result = RotateAnimation(start_time=0, duration=1.0, data={"angle": 90}).apply(
            _make_hline_opsset(), raw_progress=0.5
        )
        assert isinstance(result, OpsSet)

    def test_easing_is_called(self):
        calls = []
        RotateAnimation(start_time=0, duration=1.0, easing_fun=lambda t: calls.append(t) or t).apply(
            _make_hline_opsset(), raw_progress=0.5
        )
        assert calls == [0.5]


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

class TestRotateAnimationGeometry:
    def test_progress_zero_no_rotation(self):
        anim = RotateAnimation(start_time=0, duration=1.0, data={"angle": 90})
        original = _make_hline_opsset(x0=100, x1=200, y=0)
        result = anim.apply(original, raw_progress=0.0)
        for (ox, oy), (rx, ry) in zip(_extract_points(original), _extract_points(result)):
            assert rx == pytest.approx(ox, abs=1e-6)
            assert ry == pytest.approx(oy, abs=1e-6)

    def test_progress_one_full_angle(self):
        """(100,0)-(200,0) rotated 90° CCW about midpoint (150,0) → (150,−50)-(150,50)."""
        anim = RotateAnimation(start_time=0, duration=1.0, data={"angle": 90})
        pts = _extract_points(anim.apply(_make_hline_opsset(x0=100, x1=200, y=0), raw_progress=1.0))
        assert pts[0] == pytest.approx((150.0, -50.0), abs=1e-6)
        assert pts[1] == pytest.approx((150.0,  50.0), abs=1e-6)

    def test_progress_half_half_angle(self):
        """progress=0.5, angle=90 → 45° rotation of (100,0) about (150,0)."""
        anim = RotateAnimation(start_time=0, duration=1.0, data={"angle": 90})
        pts = _extract_points(anim.apply(_make_hline_opsset(x0=100, x1=200, y=0), raw_progress=0.5))
        half = 50 / math.sqrt(2)
        assert pts[0][0] == pytest.approx(150 - half, abs=1e-4)
        assert pts[0][1] == pytest.approx(-half, abs=1e-4)

    def test_original_opsset_is_not_mutated(self):
        original = _make_hline_opsset(x0=100, x1=200, y=0)
        before = _extract_points(original)
        RotateAnimation(start_time=0, duration=1.0, data={"angle": 90}).apply(original, raw_progress=1.0)
        assert _extract_points(original) == pytest.approx(before)

    def test_360_degree_returns_to_original(self):
        anim = RotateAnimation(start_time=0, duration=1.0, data={"angle": 360})
        original = _make_hline_opsset(x0=100, x1=200, y=50)
        result = anim.apply(original, raw_progress=1.0)
        for (ox, oy), (rx, ry) in zip(_extract_points(original), _extract_points(result)):
            assert rx == pytest.approx(ox, abs=1e-4)
            assert ry == pytest.approx(oy, abs=1e-4)


# ---------------------------------------------------------------------------
# Custom pivot
# ---------------------------------------------------------------------------

class TestRotateAnimationCenter:
    def test_custom_center_overrides_gravity(self):
        opsset = _make_hline_opsset(x0=100, x1=200, y=0)
        pts_gravity = _extract_points(
            RotateAnimation(start_time=0, duration=1.0, data={"angle": 90}).apply(opsset, raw_progress=1.0)
        )
        pts_origin = _extract_points(
            RotateAnimation(start_time=0, duration=1.0, data={"angle": 90, "center": (0.0, 0.0)}).apply(
                opsset, raw_progress=1.0
            )
        )
        assert pts_gravity != pytest.approx(pts_origin)

    def test_custom_center_at_origin_90_degrees(self):
        """(100,0)-(200,0) rotated 90° CCW about (0,0) → (0,100)-(0,200)."""
        anim = RotateAnimation(start_time=0, duration=1.0, data={"angle": 90, "center": (0.0, 0.0)})
        pts = _extract_points(anim.apply(_make_hline_opsset(x0=100, x1=200, y=0), raw_progress=1.0))
        assert pts[0] == pytest.approx((0.0, 100.0), abs=1e-4)
        assert pts[1] == pytest.approx((0.0, 200.0), abs=1e-4)


# ---------------------------------------------------------------------------
# Visual regression
# ---------------------------------------------------------------------------

class TestRotateVisual:
    def test_rotate_snapshot(self, render_to_png_bytes, snapshot):
        np.random.seed(42)
        snapshot.assert_match(render_to_png_bytes(_rotate_opsset(), width=600, height=400), "rotate_animation.png")

    def test_rotate_self_consistency(self, render_to_png_bytes):
        def to_arr(b):
            return skio.imread(io.BytesIO(b))

        np.random.seed(42)
        a = render_to_png_bytes(_rotate_opsset(), width=600, height=400)
        np.random.seed(42)
        b = render_to_png_bytes(_rotate_opsset(), width=600, height=400)
        assert ssim(to_arr(a), to_arr(b), channel_axis=-1) == pytest.approx(1.0)
