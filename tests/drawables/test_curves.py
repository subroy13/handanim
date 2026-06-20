"""
Tests for Curve primitive.

Structure
---------
- TestCurveDrawSingle    — draw_single_curve edge cases (2, 3, 4+ points, close_point)
- TestCurveRandomized    — draw_single_curve_with_randomization
- TestCurveDraw          — draw() output type, multi-stroke
- TestCurveVisual        — visual regression snapshot
"""

import io

import numpy as np
import pytest
from skimage.metrics import structural_similarity as ssim
from skimage import io as skio

from handanim.core.draw_ops import OpsSet, OpsType
from handanim.core.styles import SketchStyle, StrokeStyle
from handanim.primitives.curves import Curve


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_curve(*pts, roughness=0.0, bowing=0.0, disable_multi=True) -> Curve:
    return Curve(
        points=list(pts),
        stroke_style=StrokeStyle(color=(0, 0, 0), width=2),
        sketch_style=SketchStyle(roughness=roughness, bowing=bowing, disable_multi_stroke=disable_multi),
    )


def _ops_types(opsset: OpsSet):
    return [op.type for op in opsset.opsset]


def _curve_draw_opsset() -> OpsSet:
    return _make_curve(
        (100, 300), (200, 100), (400, 200), (600, 300), (700, 500),
        roughness=1.0, disable_multi=False,
    ).draw()


# ---------------------------------------------------------------------------
# draw_single_curve
# ---------------------------------------------------------------------------

class TestCurveDrawSingle:
    def test_two_points_produces_curve_op(self):
        c = _make_curve((0, 0), (100, 0))
        opsset = OpsSet()
        c.draw_single_curve(opsset)
        types = _ops_types(opsset)
        assert OpsType.CURVE_TO in types or OpsType.LINE_TO in types

    def test_too_few_points_raises(self):
        c = _make_curve((0, 0))
        with pytest.raises(ValueError, match="at least two"):
            c.draw_single_curve(OpsSet())

    def test_three_points_emits_move_and_curve(self):
        c = _make_curve((0, 0), (50, 100), (100, 0))
        opsset = OpsSet()
        c.draw_single_curve(opsset)
        types = _ops_types(opsset)
        assert OpsType.MOVE_TO in types
        assert OpsType.CURVE_TO in types

    def test_four_plus_points_emits_move_and_curves(self):
        c = _make_curve((0, 0), (33, 100), (66, 100), (100, 0))
        opsset = OpsSet()
        c.draw_single_curve(opsset)
        types = _ops_types(opsset)
        assert OpsType.MOVE_TO in types
        assert OpsType.CURVE_TO in types

    def test_close_point_adds_line_to(self):
        c = _make_curve((0, 0), (50, 0), (100, 50), (100, 100))
        opsset = OpsSet()
        c.draw_single_curve(opsset, close_point=(0.0, 0.0))
        types = _ops_types(opsset)
        assert OpsType.LINE_TO in types

    def test_custom_points_override_self_points(self):
        c = _make_curve((0, 0), (100, 0))
        custom = [np.array([0, 0]), np.array([200, 0])]
        opsset = OpsSet()
        c.draw_single_curve(opsset, points=custom)
        # Should not raise and should produce ops
        assert len(opsset.opsset) > 0


# ---------------------------------------------------------------------------
# draw_single_curve_with_randomization
# ---------------------------------------------------------------------------

class TestCurveRandomized:
    def test_returns_opsset(self):
        c = _make_curve((0, 0), (50, 100), (100, 0), (150, 100))
        result = c.draw_single_curve_with_randomization(OpsSet())
        assert isinstance(result, OpsSet)
        assert len(result.opsset) > 0

    def test_different_seeds_different_output(self):
        c = _make_curve((0, 0), (50, 100), (100, 0), roughness=1.0)
        np.random.seed(1)
        r1 = [tuple(pt) for op in c.draw_single_curve_with_randomization(OpsSet()).opsset
              if isinstance(op.data, list) for pt in op.data]
        np.random.seed(2)
        r2 = [tuple(pt) for op in c.draw_single_curve_with_randomization(OpsSet()).opsset
              if isinstance(op.data, list) for pt in op.data]
        assert r1 != r2


# ---------------------------------------------------------------------------
# draw()
# ---------------------------------------------------------------------------

class TestCurveDraw:
    def test_draw_returns_opsset(self):
        result = _make_curve((0, 0), (50, 100), (100, 0)).draw()
        assert isinstance(result, OpsSet)

    def test_draw_starts_with_set_pen(self):
        result = _make_curve((0, 0), (50, 100), (100, 0)).draw()
        assert result.opsset[0].type == OpsType.SET_PEN

    def test_draw_multi_stroke_adds_extra_ops(self):
        single = _make_curve((0, 0), (50, 100), (100, 0), (150, 0), disable_multi=True).draw()
        multi = _make_curve((0, 0), (50, 100), (100, 0), (150, 0), disable_multi=False).draw()
        assert len(multi.opsset) > len(single.opsset)


# ---------------------------------------------------------------------------
# Visual regression
# ---------------------------------------------------------------------------

class TestCurveVisual:
    def test_curve_snapshot(self, render_to_png_bytes, snapshot):
        np.random.seed(42)
        snapshot.assert_match(
            render_to_png_bytes(_curve_draw_opsset(), width=600, height=400),
            "curve_primitive.png",
        )

    def test_curve_self_consistency(self, render_to_png_bytes):
        def to_arr(b):
            return skio.imread(io.BytesIO(b))

        np.random.seed(42)
        a = render_to_png_bytes(_curve_draw_opsset(), width=600, height=400)
        np.random.seed(42)
        b = render_to_png_bytes(_curve_draw_opsset(), width=600, height=400)
        assert ssim(to_arr(a), to_arr(b), channel_axis=-1) == pytest.approx(1.0)
