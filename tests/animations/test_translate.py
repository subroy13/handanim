"""
Tests for TranslateToAnimation and TranslateFromAnimation.

Structure
---------
- TestTranslateToBasics     — type, data, return type, easing
- TestTranslateToGeometry   — coordinates at progress 0 / 0.5 / 1
- TestTranslateFromBasics   — type, reversal relative to TranslateTo
- TestTranslateVisual       — visual regression snapshot
"""

import io
import math

import numpy as np
import pytest
from skimage.metrics import structural_similarity as ssim
from skimage import io as skio

from handanim.core.animation import AnimationEventType
from handanim.core.draw_ops import Ops, OpsSet, OpsType
from handanim.animations.translate import TranslateFromAnimation, TranslateToAnimation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_square_opsset(cx=100.0, cy=100.0, half=50.0) -> OpsSet:
    ops = OpsSet()
    ops.add(Ops(OpsType.SET_PEN, {"color": (0, 0, 0), "width": 2}))
    ops.add(Ops(OpsType.MOVE_TO, [(cx - half, cy - half)]))
    ops.add(Ops(OpsType.LINE_TO, [(cx + half, cy - half)]))
    ops.add(Ops(OpsType.LINE_TO, [(cx + half, cy + half)]))
    ops.add(Ops(OpsType.LINE_TO, [(cx - half, cy + half)]))
    return ops


def _extract_points(opsset: OpsSet):
    pts = []
    for op in opsset.opsset:
        if op.type in (OpsType.MOVE_TO, OpsType.LINE_TO):
            pts.extend(op.data)
    return pts


def _translate_opsset() -> OpsSet:
    from handanim.primitives.polygons import Rectangle
    from handanim.core.styles import StrokeStyle, SketchStyle

    rect = Rectangle(
        top_left=(50.0, 200.0),
        width=200.0,
        height=100.0,
        stroke_style=StrokeStyle(color=(0.2, 0.5, 0.8), width=2),
        sketch_style=SketchStyle(roughness=1),
    )
    anim = TranslateToAnimation(start_time=0, duration=1.0, data={"point": (600.0, 400.0)})
    return anim.apply(rect.draw(), raw_progress=1.0)


# ---------------------------------------------------------------------------
# TranslateTo basics
# ---------------------------------------------------------------------------

class TestTranslateToBasics:
    def test_type_is_mutation(self):
        assert TranslateToAnimation(start_time=0, duration=1.0).type == AnimationEventType.MUTATION

    def test_default_point_is_origin(self):
        anim = TranslateToAnimation(start_time=0, duration=1.0)
        assert anim.data.get("point", (0, 0)) == (0, 0)

    def test_custom_point_stored(self):
        anim = TranslateToAnimation(start_time=0, duration=1.0, data={"point": (300.0, 400.0)})
        assert anim.data["point"] == (300.0, 400.0)

    def test_apply_returns_opsset(self):
        anim = TranslateToAnimation(start_time=0, duration=1.0, data={"point": (200.0, 200.0)})
        result = anim.apply(_make_square_opsset(), raw_progress=0.5)
        assert isinstance(result, OpsSet)

    def test_easing_is_called(self):
        calls = []
        TranslateToAnimation(
            start_time=0, duration=1.0,
            easing_fun=lambda t: calls.append(t) or t,
            data={"point": (200, 200)},
        ).apply(_make_square_opsset(), raw_progress=0.5)
        assert calls == [0.5]

    def test_original_opsset_not_mutated(self):
        opsset = _make_square_opsset()
        before = _extract_points(opsset)
        TranslateToAnimation(start_time=0, duration=1.0, data={"point": (500, 500)}).apply(
            opsset, raw_progress=1.0
        )
        assert _extract_points(opsset) == pytest.approx(before)


# ---------------------------------------------------------------------------
# TranslateTo geometry
# ---------------------------------------------------------------------------

class TestTranslateToGeometry:
    def test_progress_zero_no_movement(self):
        opsset = _make_square_opsset(cx=100.0, cy=100.0)
        before = _extract_points(opsset)
        anim = TranslateToAnimation(start_time=0, duration=1.0, data={"point": (500.0, 500.0)})
        result = anim.apply(opsset, raw_progress=0.0)
        assert _extract_points(result) == pytest.approx(before, abs=1e-6)

    def test_progress_one_center_reaches_target(self):
        opsset = _make_square_opsset(cx=100.0, cy=100.0)
        target = (300.0, 400.0)
        anim = TranslateToAnimation(start_time=0, duration=1.0, data={"point": target})
        result = anim.apply(opsset, raw_progress=1.0)
        cx, cy = OpsSet(result.opsset).get_center_of_gravity()
        assert cx == pytest.approx(target[0], abs=1e-4)
        assert cy == pytest.approx(target[1], abs=1e-4)

    def test_progress_half_halfway(self):
        opsset = _make_square_opsset(cx=0.0, cy=0.0, half=10.0)
        orig_cx, orig_cy = opsset.get_center_of_gravity()
        target = (200.0, 200.0)
        anim = TranslateToAnimation(start_time=0, duration=1.0, data={"point": target})
        result = anim.apply(opsset, raw_progress=0.5)
        cx, cy = result.get_center_of_gravity()
        expected_x = 0.5 * target[0] + 0.5 * orig_cx
        expected_y = 0.5 * target[1] + 0.5 * orig_cy
        assert cx == pytest.approx(expected_x, abs=1e-4)
        assert cy == pytest.approx(expected_y, abs=1e-4)


# ---------------------------------------------------------------------------
# TranslateFrom basics
# ---------------------------------------------------------------------------

class TestTranslateFromBasics:
    def test_type_is_mutation(self):
        assert TranslateFromAnimation(start_time=0, duration=1.0).type == AnimationEventType.MUTATION

    def test_progress_one_center_at_original(self):
        opsset = _make_square_opsset(cx=100.0, cy=100.0)
        orig_cx, orig_cy = opsset.get_center_of_gravity()
        anim = TranslateFromAnimation(start_time=0, duration=1.0, data={"point": (500.0, 500.0)})
        result = anim.apply(opsset, raw_progress=1.0)
        cx, cy = result.get_center_of_gravity()
        assert cx == pytest.approx(orig_cx, abs=1e-4)
        assert cy == pytest.approx(orig_cy, abs=1e-4)

    def test_translate_from_reverses_translate_to(self):
        opsset = _make_square_opsset(cx=100.0, cy=100.0)
        point = (400.0, 300.0)
        to_anim = TranslateToAnimation(start_time=0, duration=1.0, data={"point": point})
        from_anim = TranslateFromAnimation(start_time=0, duration=1.0, data={"point": point})
        result_to = _extract_points(to_anim.apply(opsset, raw_progress=0.3))
        result_from = _extract_points(from_anim.apply(opsset, raw_progress=0.7))
        assert result_to == pytest.approx(result_from, abs=1e-4)


# ---------------------------------------------------------------------------
# Visual regression
# ---------------------------------------------------------------------------

class TestTranslateVisual:
    def test_translate_snapshot(self, render_to_png_bytes, snapshot):
        np.random.seed(42)
        snapshot.assert_match(
            render_to_png_bytes(_translate_opsset(), width=600, height=400),
            "translate_animation.png",
        )

    def test_translate_self_consistency(self, render_to_png_bytes):
        def to_arr(b):
            return skio.imread(io.BytesIO(b))

        np.random.seed(42)
        a = render_to_png_bytes(_translate_opsset(), width=600, height=400)
        np.random.seed(42)
        b = render_to_png_bytes(_translate_opsset(), width=600, height=400)
        assert ssim(to_arr(a), to_arr(b), channel_axis=-1) == pytest.approx(1.0)
