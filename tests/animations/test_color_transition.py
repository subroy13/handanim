"""
Tests for ColorTransitionAnimation.

Structure
---------
- TestColorTransitionBasics        — type, color param defaults, apply return type
- TestColorTransitionInterpolation — SET_PEN color at progress 0 / 0.5 / 1
- TestColorTransitionOpPreservation — non-SET_PEN ops untouched; SET_PEN without color untouched
- TestColorTransitionVisual        — visual regression snapshot
"""

import io

import numpy as np
import pytest
from skimage.metrics import structural_similarity as ssim
from skimage import io as skio

from handanim.core.animation import AnimationEventType
from handanim.core.draw_ops import Ops, OpsSet, OpsType
from handanim.animations.color_transition import ColorTransitionAnimation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hline_opsset(x0=100.0, x1=200.0, y=0.0, color=(0.0, 0.0, 0.0)) -> OpsSet:
    ops = OpsSet(initial_set=[])
    ops.add(Ops(OpsType.SET_PEN, {"color": color, "width": 2}))
    ops.add(Ops(OpsType.MOVE_TO, [(x0, y)]))
    ops.add(Ops(OpsType.LINE_TO, [(x1, y)]))
    return ops


def _get_set_pen_colors(opsset: OpsSet):
    return [op.data["color"] for op in opsset.opsset if op.type == OpsType.SET_PEN and "color" in op.data]


def _extract_points(opsset: OpsSet):
    pts = []
    for op in opsset.opsset:
        if op.type in (OpsType.MOVE_TO, OpsType.LINE_TO):
            pts.extend(op.data)
    return pts


def _color_transition_opsset() -> OpsSet:
    from handanim.primitives.polygons import Rectangle
    from handanim.core.styles import StrokeStyle, SketchStyle

    rect = Rectangle(
        top_left=(200.0, 225.0),
        width=400.0,
        height=200.0,
        stroke_style=StrokeStyle(color=(0.0, 0.0, 0.0), width=2),
        sketch_style=SketchStyle(roughness=1),
    )
    anim = ColorTransitionAnimation(
        start_time=0, duration=1.0,
        data={"start_color": (0.8, 0.0, 0.0), "end_color": (0.0, 0.0, 0.8)},
    )
    return anim.apply(rect.draw(), raw_progress=0.5)


# ---------------------------------------------------------------------------
# Basics
# ---------------------------------------------------------------------------

class TestColorTransitionBasics:
    def test_type_is_mutation(self):
        assert ColorTransitionAnimation(start_time=0, duration=1.0).type == AnimationEventType.MUTATION

    def test_default_start_color(self):
        assert ColorTransitionAnimation(start_time=0, duration=1.0).start_color == (0.0, 0.0, 0.0)

    def test_default_end_color(self):
        assert ColorTransitionAnimation(start_time=0, duration=1.0).end_color == (1.0, 1.0, 1.0)

    def test_custom_colors_stored(self):
        anim = ColorTransitionAnimation(
            start_time=0, duration=1.0,
            data={"start_color": (1.0, 0.0, 0.0), "end_color": (0.0, 0.0, 1.0)},
        )
        assert anim.start_color == (1.0, 0.0, 0.0)
        assert anim.end_color == (0.0, 0.0, 1.0)

    def test_apply_returns_opsset(self):
        anim = ColorTransitionAnimation(
            start_time=0, duration=1.0,
            data={"start_color": (1.0, 0.0, 0.0), "end_color": (0.0, 0.0, 1.0)},
        )
        assert isinstance(anim.apply(_make_hline_opsset(), raw_progress=0.5), OpsSet)


# ---------------------------------------------------------------------------
# Interpolation
# ---------------------------------------------------------------------------

class TestColorTransitionInterpolation:
    def _anim(self):
        return ColorTransitionAnimation(
            start_time=0, duration=1.0,
            data={"start_color": (1.0, 0.0, 0.0), "end_color": (0.0, 0.0, 1.0)},
        )

    def test_progress_zero_gives_start_color(self):
        colors = _get_set_pen_colors(self._anim().apply(_make_hline_opsset(), raw_progress=0.0))
        assert len(colors) == 1
        assert colors[0] == pytest.approx((1.0, 0.0, 0.0), abs=1e-6)

    def test_progress_one_gives_end_color(self):
        colors = _get_set_pen_colors(self._anim().apply(_make_hline_opsset(), raw_progress=1.0))
        assert len(colors) == 1
        assert colors[0] == pytest.approx((0.0, 0.0, 1.0), abs=1e-6)

    def test_progress_half_gives_midpoint(self):
        colors = _get_set_pen_colors(self._anim().apply(_make_hline_opsset(), raw_progress=0.5))
        assert len(colors) == 1
        assert colors[0] == pytest.approx((0.5, 0.0, 0.5), abs=1e-6)

    def test_multiple_set_pen_ops_all_updated(self):
        opsset = OpsSet(initial_set=[])
        opsset.add(Ops(OpsType.SET_PEN, {"color": (0.0, 0.0, 0.0), "width": 1}))
        opsset.add(Ops(OpsType.MOVE_TO, [(0.0, 0.0)]))
        opsset.add(Ops(OpsType.LINE_TO, [(100.0, 0.0)]))
        opsset.add(Ops(OpsType.SET_PEN, {"color": (0.0, 0.0, 0.0), "width": 2}))
        opsset.add(Ops(OpsType.LINE_TO, [(200.0, 0.0)]))

        anim = ColorTransitionAnimation(
            start_time=0, duration=1.0,
            data={"start_color": (1.0, 0.0, 0.0), "end_color": (0.0, 1.0, 0.0)},
        )
        colors = _get_set_pen_colors(anim.apply(opsset, raw_progress=1.0))
        assert len(colors) == 2
        for c in colors:
            assert c == pytest.approx((0.0, 1.0, 0.0), abs=1e-6)

    def test_original_opsset_not_mutated(self):
        original = _make_hline_opsset(color=(0.5, 0.5, 0.5))
        before = _get_set_pen_colors(original)
        ColorTransitionAnimation(
            start_time=0, duration=1.0,
            data={"start_color": (1.0, 0.0, 0.0), "end_color": (0.0, 0.0, 1.0)},
        ).apply(original, raw_progress=1.0)
        assert _get_set_pen_colors(original) == pytest.approx(before)


# ---------------------------------------------------------------------------
# Op preservation
# ---------------------------------------------------------------------------

class TestColorTransitionOpPreservation:
    def test_non_set_pen_ops_unchanged(self):
        original = _make_hline_opsset(x0=111, x1=222, y=33)
        result = ColorTransitionAnimation(
            start_time=0, duration=1.0,
            data={"start_color": (1.0, 0.0, 0.0), "end_color": (0.0, 0.0, 1.0)},
        ).apply(original, raw_progress=0.7)
        assert _extract_points(original) == pytest.approx(_extract_points(result))

    def test_set_pen_without_color_key_is_untouched(self):
        opsset = OpsSet(initial_set=[])
        opsset.add(Ops(OpsType.SET_PEN, {"width": 3}))
        opsset.add(Ops(OpsType.MOVE_TO, [(0.0, 0.0)]))
        result = ColorTransitionAnimation(
            start_time=0, duration=1.0,
            data={"start_color": (1.0, 0.0, 0.0), "end_color": (0.0, 0.0, 1.0)},
        ).apply(opsset, raw_progress=0.5)
        for op in result.opsset:
            if op.type == OpsType.SET_PEN:
                assert "color" not in op.data

    def test_op_count_preserved(self):
        original = _make_hline_opsset()
        result = ColorTransitionAnimation(
            start_time=0, duration=1.0,
            data={"start_color": (1.0, 0.0, 0.0), "end_color": (0.0, 0.0, 1.0)},
        ).apply(original, raw_progress=0.5)
        assert len(result.opsset) == len(original.opsset)

    def test_non_color_pen_fields_preserved(self):
        original = _make_hline_opsset(color=(0.0, 0.0, 0.0))
        result = ColorTransitionAnimation(
            start_time=0, duration=1.0,
            data={"start_color": (1.0, 0.0, 0.0), "end_color": (0.0, 0.0, 1.0)},
        ).apply(original, raw_progress=0.5)
        for op in result.opsset:
            if op.type == OpsType.SET_PEN and "color" in op.data:
                assert op.data.get("width") == 2


# ---------------------------------------------------------------------------
# Visual regression
# ---------------------------------------------------------------------------

class TestColorTransitionVisual:
    def test_color_transition_snapshot(self, render_to_png_bytes, snapshot):
        np.random.seed(42)
        snapshot.assert_match(
            render_to_png_bytes(_color_transition_opsset(), width=600, height=400),
            "color_transition_animation.png",
        )

    def test_color_transition_self_consistency(self, render_to_png_bytes):
        def to_arr(b):
            return skio.imread(io.BytesIO(b))

        np.random.seed(42)
        a = render_to_png_bytes(_color_transition_opsset(), width=600, height=400)
        np.random.seed(42)
        b = render_to_png_bytes(_color_transition_opsset(), width=600, height=400)
        assert ssim(to_arr(a), to_arr(b), channel_axis=-1) == pytest.approx(1.0)
