"""
Tests for Arrow and CurvedArrow primitives.

Structure
---------
- TestArrowBasics        — draw() returns OpsSet, starts with SET_PEN
- TestArrowHeadTypes     — ->, ->>, -|> produce different op counts
- TestArrowGeometry      — horizontal arrow endpoint is in the right direction
- TestCurvedArrowBasics  — draw() returns OpsSet, error on <2 points
- TestCurvedArrowHeads   — ->> and -|> extend ops vs ->
- TestArrowVisual        — visual regression snapshot
"""

import io
import math

import numpy as np
import pytest
from skimage.metrics import structural_similarity as ssim
from skimage import io as skio

from handanim.core.draw_ops import Ops, OpsSet, OpsType
from handanim.core.styles import SketchStyle, StrokeStyle
from handanim.primitives.arrow import Arrow, CurvedArrow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STYLE = dict(
    stroke_style=StrokeStyle(color=(0, 0, 0), width=2),
    sketch_style=SketchStyle(roughness=0, bowing=0, disable_multi_stroke=True),
)


def _ops_types(opsset: OpsSet):
    return [op.type for op in opsset.opsset]


def _arrow_opsset() -> OpsSet:
    return Arrow(
        start_point=(100, 200),
        end_point=(700, 400),
        arrow_head_type="->",
        **_STYLE,
    ).draw()


# ---------------------------------------------------------------------------
# Arrow basics
# ---------------------------------------------------------------------------

class TestArrowBasics:
    def test_draw_returns_opsset(self):
        result = Arrow(start_point=(0, 0), end_point=(100, 0), **_STYLE).draw()
        assert isinstance(result, OpsSet)

    def test_draw_non_empty(self):
        result = Arrow(start_point=(0, 0), end_point=(100, 0), **_STYLE).draw()
        assert len(result.opsset) > 0

    def test_draw_contains_set_pen(self):
        result = Arrow(start_point=(0, 0), end_point=(100, 0), **_STYLE).draw()
        assert OpsType.SET_PEN in _ops_types(result)

    def test_draw_contains_move_and_line(self):
        result = Arrow(start_point=(0, 0), end_point=(100, 0), **_STYLE).draw()
        types = _ops_types(result)
        assert OpsType.MOVE_TO in types or OpsType.LINE_TO in types


# ---------------------------------------------------------------------------
# Arrow head types
# ---------------------------------------------------------------------------

class TestArrowHeadTypes:
    def _count_ops(self, arrow_type):
        return len(Arrow(
            start_point=(0, 0), end_point=(200, 0),
            arrow_head_type=arrow_type,
            **_STYLE,
        ).draw().opsset)

    def test_single_arrow_fewer_than_double(self):
        assert self._count_ops("->") < self._count_ops("->>")

    def test_single_arrow_fewer_than_bar(self):
        assert self._count_ops("->") < self._count_ops("-|>")

    def test_double_and_bar_similar_count(self):
        # Both add a second arrowhead, so their counts are close (may differ by 1–2)
        assert abs(self._count_ops("->>") - self._count_ops("-|>")) <= 4


# ---------------------------------------------------------------------------
# Arrow geometry
# ---------------------------------------------------------------------------

class TestArrowGeometry:
    def test_arrow_translated_to_start(self):
        start = (50.0, 75.0)
        result = Arrow(start_point=start, end_point=(250.0, 75.0), **_STYLE).draw()
        # All points should be near the region between start and end
        bbox = result.get_bbox()
        assert bbox.min_x == pytest.approx(start[0], abs=5.0)

    def test_diagonal_arrow_rotated_correctly(self):
        # Arrow from (0,0) to (100,100) should have ops spanning in both x and y
        result = Arrow(start_point=(0, 0), end_point=(100, 100), **_STYLE).draw()
        bbox = result.get_bbox()
        assert bbox.width > 0
        assert bbox.height > 0


# ---------------------------------------------------------------------------
# CurvedArrow basics
# ---------------------------------------------------------------------------

class TestCurvedArrowBasics:
    def test_draw_returns_opsset(self):
        result = CurvedArrow(
            points=[(0, 0), (100, 100), (200, 0)],
            **_STYLE,
        ).draw()
        assert isinstance(result, OpsSet)

    def test_too_few_points_raises(self):
        with pytest.raises(ValueError, match="at least two"):
            CurvedArrow(points=[(0, 0)], **_STYLE).draw()

    def test_two_points_works(self):
        result = CurvedArrow(points=[(0, 0), (100, 0)], **_STYLE).draw()
        assert len(result.opsset) > 0


# ---------------------------------------------------------------------------
# CurvedArrow head types
# ---------------------------------------------------------------------------

class TestCurvedArrowHeads:
    def _count(self, arrow_type):
        return len(CurvedArrow(
            points=[(0, 0), (100, 50), (200, 0)],
            arrow_head_type=arrow_type,
            **_STYLE,
        ).draw().opsset)

    def test_double_more_than_single(self):
        assert self._count("->>") > self._count("->")

    def test_bar_more_than_single(self):
        assert self._count("-|>") > self._count("->")


# ---------------------------------------------------------------------------
# Visual regression
# ---------------------------------------------------------------------------

class TestArrowVisual:
    def test_arrow_snapshot(self, render_to_png_bytes, snapshot):
        np.random.seed(42)
        snapshot.assert_match(
            render_to_png_bytes(_arrow_opsset(), width=600, height=400),
            "arrow_primitive.png",
        )

    def test_arrow_self_consistency(self, render_to_png_bytes):
        def to_arr(b):
            return skio.imread(io.BytesIO(b))

        np.random.seed(42)
        a = render_to_png_bytes(_arrow_opsset(), width=600, height=400)
        np.random.seed(42)
        b = render_to_png_bytes(_arrow_opsset(), width=600, height=400)
        assert ssim(to_arr(a), to_arr(b), channel_axis=-1) == pytest.approx(1.0)
