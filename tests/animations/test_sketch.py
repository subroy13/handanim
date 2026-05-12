"""
Tests for SketchAnimation.

Structure
---------
- TestGetPartialSketch  — pure logic: op counts at various progress values
- TestApply             — apply() / easing / wait_before_fill clamping
- TestSketchVisual      — visual regression: partial-sketch snapshots
"""

import io

import numpy as np
import pytest
from skimage.metrics import structural_similarity as ssim
from skimage import io as skio

from handanim.core.draw_ops import Ops, OpsSet, OpsType
from handanim.core.styles import StrokeStyle, SketchStyle
from handanim.animations.sketch import SketchAnimation
from handanim.primitives.polygons import Rectangle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_draw_opsset(n_draw: int, n_fill: int = 0) -> OpsSet:
    """
    Build an OpsSet with n_draw LINE_TO draw ops, then (if n_fill > 0) a
    METADATA fill-mode separator followed by n_fill LINE_TO fill ops.
    """
    ops = OpsSet()
    ops.add(Ops(OpsType.SET_PEN, {"color": (0, 0, 0), "width": 1}))
    ops.add(Ops(OpsType.MOVE_TO, [(0, 0)]))
    for i in range(n_draw):
        ops.add(Ops(OpsType.LINE_TO, [(float(i + 1) * 10, 0)]))

    if n_fill > 0:
        ops.add(Ops(OpsType.METADATA, {"drawing_mode": "fill"}))
        ops.add(Ops(OpsType.SET_PEN, {"color": (0.5, 0.5, 0.5), "width": 1}))
        ops.add(Ops(OpsType.MOVE_TO, [(0, 5)]))
        for i in range(n_fill):
            ops.add(Ops(OpsType.LINE_TO, [(float(i + 1) * 10, 5)]))

    return ops


def count_drawing_ops(opsset: OpsSet) -> int:
    return sum(1 for op in opsset.opsset if op.type not in Ops.SETUP_OPS_TYPES)


def make_sketch(duration: float = 1.0, wait_before_fill: float = 0.0) -> SketchAnimation:
    return SketchAnimation(start_time=0.0, duration=duration, data={"wait_before_fill": wait_before_fill})


def _rectangle_opsset() -> OpsSet:
    rect = Rectangle(
        top_left=(150, 150),
        width=500,
        height=300,
        stroke_style=StrokeStyle(color=(0.8, 0.1, 0.1), width=2),
        sketch_style=SketchStyle(roughness=1),
    )
    return rect.draw()


def _sketch_at(opsset: OpsSet, progress: float) -> OpsSet:
    sketch = SketchAnimation(start_time=0.0, duration=1.0)
    return sketch.get_partial_sketch(opsset, progress)


# ---------------------------------------------------------------------------
# get_partial_sketch
# ---------------------------------------------------------------------------

class TestGetPartialSketch:
    def test_progress_zero_yields_no_drawing_ops(self):
        opsset = make_draw_opsset(n_draw=4)
        sketch = make_sketch(duration=1.0)
        result = sketch.get_partial_sketch(opsset, 0.0)
        assert count_drawing_ops(result) == 0

    def test_progress_one_yields_all_draw_ops(self):
        opsset = make_draw_opsset(n_draw=4)
        sketch = make_sketch(duration=1.0)
        result = sketch.get_partial_sketch(opsset, 1.0)
        assert count_drawing_ops(result) == 4

    def test_progress_half_yields_roughly_half_draw_ops(self):
        opsset = make_draw_opsset(n_draw=4)
        sketch = make_sketch(duration=1.0)
        result = sketch.get_partial_sketch(opsset, 0.5)
        assert count_drawing_ops(result) == 2

    def test_progress_one_with_fill_yields_all_ops(self):
        opsset = make_draw_opsset(n_draw=4, n_fill=2)
        sketch = make_sketch(duration=1.0)
        result = sketch.get_partial_sketch(opsset, 1.0)
        assert count_drawing_ops(result) == 6

    def test_draw_phase_complete_before_fill_starts_with_wait(self):
        """
        wait_before_fill=0.4, duration=1.0 → draw_end=0.6, fill_start=1.0.
        At progress=0.7 all 4 draw ops are done but zero fill ops started.
        """
        opsset = make_draw_opsset(n_draw=4, n_fill=4)
        sketch = make_sketch(duration=1.0, wait_before_fill=0.4)
        result = sketch.get_partial_sketch(opsset, 0.7)
        assert count_drawing_ops(result) == 4

    def test_fill_phase_progress(self):
        """
        No wait, 4+4=8 total ops. At progress=0.875: draw done, fill_progress=0.75
        → int(0.75*4)=3 fill ops. Total = 7.
        """
        opsset = make_draw_opsset(n_draw=4, n_fill=4)
        sketch = make_sketch(duration=1.0, wait_before_fill=0.0)
        result = sketch.get_partial_sketch(opsset, 0.875)
        assert count_drawing_ops(result) == 7

    def test_returns_new_opsset_does_not_mutate_input(self):
        opsset = make_draw_opsset(n_draw=4)
        original_len = len(opsset.opsset)
        make_sketch(duration=1.0).get_partial_sketch(opsset, 0.5)
        assert len(opsset.opsset) == original_len


# ---------------------------------------------------------------------------
# apply() / easing
# ---------------------------------------------------------------------------

class TestApply:
    def test_apply_returns_empty_at_zero_progress(self):
        opsset = make_draw_opsset(n_draw=4)
        result = make_sketch(duration=1.0).apply(opsset, 0.0)
        assert count_drawing_ops(result) == 0

    def test_apply_returns_full_at_progress_one(self):
        opsset = make_draw_opsset(n_draw=4)
        result = make_sketch(duration=1.0).apply(opsset, 1.0)
        assert count_drawing_ops(result) == 4

    def test_easing_fun_transforms_progress(self):
        opsset = make_draw_opsset(n_draw=8)
        sketch_with_easing = SketchAnimation(start_time=0.0, duration=1.0, easing_fun=lambda p: p ** 2)
        sketch_no_easing = make_sketch(duration=1.0)
        result_eased = sketch_with_easing.apply(opsset, 0.5)
        result_direct = sketch_no_easing._apply(opsset, 0.25)
        assert count_drawing_ops(result_eased) == count_drawing_ops(result_direct)

    def test_apply_without_easing_is_identity_passthrough(self):
        opsset = make_draw_opsset(n_draw=6)
        sketch = make_sketch(duration=1.0)
        assert count_drawing_ops(sketch.apply(opsset, 0.5)) == count_drawing_ops(sketch._apply(opsset, 0.5))

    def test_wait_before_fill_clamped_to_half_duration(self):
        sketch = SketchAnimation(start_time=0.0, duration=2.0, data={"wait_before_fill": 5.0})
        assert sketch.wait_before_fill == 1.0


# ---------------------------------------------------------------------------
# Visual regression
# ---------------------------------------------------------------------------

class TestSketchVisual:
    @pytest.mark.parametrize("progress,name", [
        (0.25, "sketch_quarter.png"),
        (0.50, "sketch_half.png"),
        (1.00, "sketch_full.png"),
    ])
    def test_sketch_progress_snapshot(self, progress, name, render_to_png_bytes, snapshot):
        partial = _sketch_at(_rectangle_opsset(), progress)
        snapshot.assert_match(render_to_png_bytes(partial), name)

    def test_full_sketch_matches_direct_render(self, render_to_png_bytes):
        """get_partial_sketch at progress=1.0 must be visually identical to the full OpsSet."""
        SSIM_THRESHOLD = 0.98
        np.random.seed(42)
        full_opsset = _rectangle_opsset()
        np.random.seed(42)
        sketch_full = _sketch_at(_rectangle_opsset(), 1.0)
        png_direct = render_to_png_bytes(full_opsset)
        png_sketch = render_to_png_bytes(sketch_full)

        def to_arr(b):
            return skio.imread(io.BytesIO(b))

        score = ssim(to_arr(png_direct), to_arr(png_sketch), channel_axis=-1)
        assert score >= SSIM_THRESHOLD, f"SSIM {score:.4f} below threshold {SSIM_THRESHOLD}"
