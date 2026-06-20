"""
Tests for ZoomInAnimation and ZoomOutAnimation.

Structure
---------
- TestZoomInBasics     — type, data, return type, easing
- TestZoomInGeometry   — scale factor at progress 0 / 0.5 / 1
- TestZoomOutBasics    — type, reversal
- TestZoomVisual       — visual regression snapshot
"""

import io

import numpy as np
import pytest
from skimage.metrics import structural_similarity as ssim
from skimage import io as skio

from handanim.core.animation import AnimationEventType
from handanim.core.draw_ops import Ops, OpsSet, OpsType
from handanim.animations.zoom import ZoomInAnimation, ZoomOutAnimation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hline_opsset(x0=0.0, x1=100.0, y=50.0) -> OpsSet:
    ops = OpsSet()
    ops.add(Ops(OpsType.SET_PEN, {"color": (0, 0, 0), "width": 2}))
    ops.add(Ops(OpsType.MOVE_TO, [(x0, y)]))
    ops.add(Ops(OpsType.LINE_TO, [(x1, y)]))
    return ops


def _extract_points(opsset: OpsSet):
    pts = []
    for op in opsset.opsset:
        if op.type in (OpsType.MOVE_TO, OpsType.LINE_TO):
            pts.extend(op.data)
    return pts


def _zoom_opsset() -> OpsSet:
    from handanim.primitives.polygons import Rectangle
    from handanim.core.styles import StrokeStyle, SketchStyle

    rect = Rectangle(
        top_left=(300.0, 275.0),
        width=200.0,
        height=100.0,
        stroke_style=StrokeStyle(color=(0.8, 0.2, 0.1), width=2),
        sketch_style=SketchStyle(roughness=1),
    )
    anim = ZoomInAnimation(start_time=0, duration=1.0)
    return anim.apply(rect.draw(), raw_progress=1.0)


# ---------------------------------------------------------------------------
# ZoomIn basics
# ---------------------------------------------------------------------------

class TestZoomInBasics:
    def test_type_is_creation(self):
        assert ZoomInAnimation(start_time=0, duration=1.0).type == AnimationEventType.CREATION

    def test_apply_returns_opsset(self):
        result = ZoomInAnimation(start_time=0, duration=1.0).apply(_make_hline_opsset(), raw_progress=0.5)
        assert isinstance(result, OpsSet)

    def test_easing_is_called(self):
        calls = []
        ZoomInAnimation(
            start_time=0, duration=1.0,
            easing_fun=lambda t: calls.append(t) or t,
        ).apply(_make_hline_opsset(), raw_progress=0.5)
        assert calls == [0.5]

    def test_original_not_mutated(self):
        opsset = _make_hline_opsset()
        before = _extract_points(opsset)
        ZoomInAnimation(start_time=0, duration=1.0).apply(opsset, raw_progress=0.5)
        assert _extract_points(opsset) == pytest.approx(before)


# ---------------------------------------------------------------------------
# ZoomIn geometry
# ---------------------------------------------------------------------------

class TestZoomInGeometry:
    def test_progress_one_returns_full_size(self):
        opsset = _make_hline_opsset(x0=0.0, x1=100.0, y=50.0)
        before = _extract_points(opsset)
        result = ZoomInAnimation(start_time=0, duration=1.0).apply(opsset, raw_progress=1.0)
        after = _extract_points(result)
        # At progress=1 scale=1 → center of gravity preserved, relative positions same
        orig_cx, orig_cy = opsset.get_center_of_gravity()
        res_cx, res_cy = result.get_center_of_gravity()
        assert res_cx == pytest.approx(orig_cx, abs=1e-4)
        assert res_cy == pytest.approx(orig_cy, abs=1e-4)

    def test_progress_zero_collapses_to_center(self):
        # scale=0 collapses all points to the center of gravity
        opsset = _make_hline_opsset(x0=0.0, x1=100.0, y=50.0)
        cx, cy = opsset.get_center_of_gravity()
        result = ZoomInAnimation(start_time=0, duration=1.0).apply(opsset, raw_progress=0.0)
        for pt in _extract_points(result):
            assert pt[0] == pytest.approx(cx, abs=1e-4)
            assert pt[1] == pytest.approx(cy, abs=1e-4)

    def test_progress_half_halves_spread(self):
        # points at x=0 and x=100, center=50.  At scale=0.5 → x=25, x=75
        opsset = _make_hline_opsset(x0=0.0, x1=100.0, y=50.0)
        result = ZoomInAnimation(start_time=0, duration=1.0).apply(opsset, raw_progress=0.5)
        pts = _extract_points(result)
        xs = [p[0] for p in pts]
        assert min(xs) == pytest.approx(25.0, abs=1e-4)
        assert max(xs) == pytest.approx(75.0, abs=1e-4)


# ---------------------------------------------------------------------------
# ZoomOut basics
# ---------------------------------------------------------------------------

class TestZoomOutBasics:
    def test_type_is_deletion(self):
        assert ZoomOutAnimation(start_time=0, duration=1.0).type == AnimationEventType.DELETION

    def test_progress_zero_full_size(self):
        opsset = _make_hline_opsset(x0=0.0, x1=100.0, y=50.0)
        before = _extract_points(opsset)
        result = ZoomOutAnimation(start_time=0, duration=1.0).apply(opsset, raw_progress=0.0)
        orig_cx, orig_cy = opsset.get_center_of_gravity()
        res_cx, res_cy = result.get_center_of_gravity()
        assert res_cx == pytest.approx(orig_cx, abs=1e-4)
        assert res_cy == pytest.approx(orig_cy, abs=1e-4)

    def test_progress_one_collapses_to_center(self):
        opsset = _make_hline_opsset(x0=0.0, x1=100.0, y=50.0)
        cx, cy = opsset.get_center_of_gravity()
        result = ZoomOutAnimation(start_time=0, duration=1.0).apply(opsset, raw_progress=1.0)
        for pt in _extract_points(result):
            assert pt[0] == pytest.approx(cx, abs=1e-4)
            assert pt[1] == pytest.approx(cy, abs=1e-4)

    def test_zoom_out_reverses_zoom_in_at_complement(self):
        opsset = _make_hline_opsset(x0=0.0, x1=100.0, y=50.0)
        in_pts = _extract_points(ZoomInAnimation(start_time=0, duration=1.0).apply(opsset, raw_progress=0.3))
        out_pts = _extract_points(ZoomOutAnimation(start_time=0, duration=1.0).apply(opsset, raw_progress=0.7))
        assert in_pts == pytest.approx(out_pts, abs=1e-4)


# ---------------------------------------------------------------------------
# Visual regression
# ---------------------------------------------------------------------------

class TestZoomVisual:
    def test_zoom_snapshot(self, render_to_png_bytes, snapshot):
        np.random.seed(42)
        snapshot.assert_match(
            render_to_png_bytes(_zoom_opsset(), width=600, height=400),
            "zoom_animation.png",
        )

    def test_zoom_self_consistency(self, render_to_png_bytes):
        def to_arr(b):
            return skio.imread(io.BytesIO(b))

        np.random.seed(42)
        a = render_to_png_bytes(_zoom_opsset(), width=600, height=400)
        np.random.seed(42)
        b = render_to_png_bytes(_zoom_opsset(), width=600, height=400)
        assert ssim(to_arr(a), to_arr(b), channel_axis=-1) == pytest.approx(1.0)
