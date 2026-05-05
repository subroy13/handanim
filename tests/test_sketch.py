"""
Unit tests for SketchAnimation logic.

All tests operate on OpsSet objects directly — no Cairo, no rendering.
The key invariant: get_partial_sketch is a pure function of (opsset, progress)
that returns a new OpsSet containing the correct slice of drawing operations.
"""

import pytest
from handanim.core.draw_ops import Ops, OpsSet, OpsType
from handanim.animations.sketch import SketchAnimation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_draw_opsset(n_draw: int, n_fill: int = 0) -> OpsSet:
    """
    Build an OpsSet with n_draw LINE_TO draw ops, then (if n_fill > 0) a
    METADATA fill-mode separator followed by n_fill LINE_TO fill ops.

    Each group is preceded by a SET_PEN (a setup op, not counted by the sketch logic).
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
    """Count non-setup ops (LINE_TO, CURVE_TO, etc.) in result."""
    return sum(
        1 for op in opsset.opsset
        if op.type not in Ops.SETUP_OPS_TYPES
    )


def make_sketch(duration: float = 1.0, wait_before_fill: float = 0.0) -> SketchAnimation:
    return SketchAnimation(
        start_time=0.0,
        duration=duration,
        data={"wait_before_fill": wait_before_fill},
    )


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
        # At exactly 0.5, n_active = int(0.5 * 4) = 2
        assert count_drawing_ops(result) == 2

    def test_progress_one_with_fill_yields_all_ops(self):
        opsset = make_draw_opsset(n_draw=4, n_fill=2)
        sketch = make_sketch(duration=1.0)
        result = sketch.get_partial_sketch(opsset, 1.0)
        assert count_drawing_ops(result) == 6  # 4 draw + 2 fill

    def test_draw_phase_complete_before_fill_starts_with_wait(self):
        """
        With wait_before_fill=0.4 and duration=1.0:
        - draw_end_time  = per_op_time * 4 = (1.0 - 0.4) / 4 * 4 = 0.6
        - fill_start_time = 0.6 + 0.4 = 1.0
        At progress=0.7 (time=0.7s), we are in the wait window → all 4 draw
        ops are done but zero fill ops have started.
        """
        opsset = make_draw_opsset(n_draw=4, n_fill=4)
        sketch = make_sketch(duration=1.0, wait_before_fill=0.4)
        result = sketch.get_partial_sketch(opsset, 0.7)
        assert count_drawing_ops(result) == 4

    def test_fill_phase_progress(self):
        """
        No wait. 4 draw + 4 fill = 8 total ops.
        At progress=0.875, time=0.875, draw is done (0.5s covers all 4 draw),
        fill_progress = (0.875 - 0.5) / 0.5 = 0.75 → int(0.75*4)=3 fill ops.
        Total = 4 + 3 = 7.
        """
        opsset = make_draw_opsset(n_draw=4, n_fill=4)
        sketch = make_sketch(duration=1.0, wait_before_fill=0.0)
        result = sketch.get_partial_sketch(opsset, 0.875)
        assert count_drawing_ops(result) == 7

    def test_returns_new_opsset_does_not_mutate_input(self):
        opsset = make_draw_opsset(n_draw=4)
        original_len = len(opsset.opsset)
        sketch = make_sketch(duration=1.0)
        sketch.get_partial_sketch(opsset, 0.5)
        assert len(opsset.opsset) == original_len


# ---------------------------------------------------------------------------
# apply() / easing
# ---------------------------------------------------------------------------

class TestApply:
    def test_apply_returns_empty_at_zero_progress(self):
        opsset = make_draw_opsset(n_draw=4)
        sketch = make_sketch(duration=1.0)
        result = sketch.apply(opsset, 0.0)
        assert count_drawing_ops(result) == 0

    def test_apply_returns_full_at_progress_one(self):
        opsset = make_draw_opsset(n_draw=4)
        sketch = make_sketch(duration=1.0)
        result = sketch.apply(opsset, 1.0)
        assert count_drawing_ops(result) == 4

    def test_easing_fun_transforms_progress(self):
        """
        easing_fun = lambda p: p ** 2
        Calling apply(opsset, 0.5) should behave identically to
        calling _apply(opsset, 0.25) — the easing squares the progress.
        """
        opsset = make_draw_opsset(n_draw=8)
        sketch_with_easing = SketchAnimation(
            start_time=0.0,
            duration=1.0,
            easing_fun=lambda p: p ** 2,
        )
        sketch_no_easing = make_sketch(duration=1.0)

        result_eased = sketch_with_easing.apply(opsset, 0.5)
        result_direct = sketch_no_easing._apply(opsset, 0.25)

        assert count_drawing_ops(result_eased) == count_drawing_ops(result_direct)

    def test_apply_without_easing_is_identity_passthrough(self):
        """No easing_fun: apply(progress) == _apply(progress)."""
        opsset = make_draw_opsset(n_draw=6)
        sketch = make_sketch(duration=1.0)
        assert count_drawing_ops(sketch.apply(opsset, 0.5)) == \
               count_drawing_ops(sketch._apply(opsset, 0.5))

    def test_wait_before_fill_clamped_to_half_duration(self):
        """wait_before_fill > duration/2 is silently clamped to duration/2."""
        sketch = SketchAnimation(
            start_time=0.0,
            duration=2.0,
            data={"wait_before_fill": 5.0},  # way too large
        )
        assert sketch.wait_before_fill == 1.0  # clamped to 2.0/2
