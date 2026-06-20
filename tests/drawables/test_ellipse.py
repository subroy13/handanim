"""
Tests for Ellipse, Circle, and GlowDot primitives.

Structure
---------
- TestEllipseBasics   — draw() returns OpsSet, starts with SET_PEN
- TestEllipseParams   — different roughness/multi-stroke flags affect op count
- TestCircle          — Circle as special ellipse (width == height)
- TestGlowDot         — draw() returns multi-layer OpsSet with DOT ops
- TestEllipseVisual   — visual regression snapshot
"""

import io

import numpy as np
import pytest
from skimage.metrics import structural_similarity as ssim
from skimage import io as skio

from handanim.core.draw_ops import OpsSet, OpsType
from handanim.core.styles import FillStyle, SketchStyle, StrokeStyle
from handanim.primitives.ellipse import Circle, Ellipse, GlowDot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STROKE = StrokeStyle(color=(0.1, 0.3, 0.8), width=2)
_SKETCH_SMOOTH = SketchStyle(roughness=0, disable_multi_stroke=True)
_SKETCH_ROUGH = SketchStyle(roughness=2, disable_multi_stroke=False)


def _ellipse(roughness=0.0, disable_multi=True, fill_style=None):
    return Ellipse(
        center=(300, 250),
        width=200,
        height=100,
        stroke_style=_STROKE,
        sketch_style=SketchStyle(roughness=roughness, disable_multi_stroke=disable_multi),
        fill_style=fill_style,
    )


def _ellipse_opsset() -> OpsSet:
    return _ellipse(roughness=1.0, disable_multi=False).draw()


# ---------------------------------------------------------------------------
# Ellipse basics
# ---------------------------------------------------------------------------

class TestEllipseBasics:
    def test_draw_returns_opsset(self):
        assert isinstance(_ellipse().draw(), OpsSet)

    def test_draw_non_empty(self):
        assert len(_ellipse().draw().opsset) > 0

    def test_draw_starts_with_set_pen(self):
        result = _ellipse().draw()
        assert result.opsset[0].type == OpsType.SET_PEN

    def test_draw_contains_move_to(self):
        result = _ellipse().draw()
        types = [op.type for op in result.opsset]
        assert OpsType.MOVE_TO in types or OpsType.CURVE_TO in types


# ---------------------------------------------------------------------------
# Ellipse parameters
# ---------------------------------------------------------------------------

class TestEllipseParams:
    def test_multi_stroke_adds_ops(self):
        # With same roughness, enabling multi-stroke adds a second ellipse pass
        single = _ellipse(roughness=2, disable_multi=True).draw()
        multi = _ellipse(roughness=2, disable_multi=False).draw()
        assert len(multi.opsset) > len(single.opsset)

    def test_with_fill_adds_more_ops(self):
        no_fill = _ellipse(roughness=0, disable_multi=True).draw()
        with_fill = _ellipse(
            roughness=0,
            disable_multi=True,
            fill_style=FillStyle(fill_pattern="solid", color=(0.5, 0.5, 0.5)),
        ).draw()
        assert len(with_fill.opsset) > len(no_fill.opsset)

    def test_large_ellipse_has_reasonable_bbox(self):
        e = Ellipse(
            center=(500, 400),
            width=400,
            height=200,
            stroke_style=_STROKE,
            sketch_style=_SKETCH_SMOOTH,
        )
        bbox = e.draw().get_bbox()
        # Center should be roughly at (500, 400); allow large tolerance for sketchy rendering
        cx, cy = bbox.center
        assert 300 <= cx <= 700
        assert 200 <= cy <= 600


# ---------------------------------------------------------------------------
# Circle
# ---------------------------------------------------------------------------

class TestCircle:
    def test_circle_is_ellipse_subclass(self):
        assert issubclass(Circle, Ellipse)

    def test_circle_has_equal_width_height(self):
        c = Circle(center=(100, 100), radius=50, stroke_style=_STROKE, sketch_style=_SKETCH_SMOOTH)
        assert c.width == c.height

    def test_circle_draw_returns_opsset(self):
        c = Circle(center=(200, 200), radius=80, stroke_style=_STROKE, sketch_style=_SKETCH_SMOOTH)
        assert isinstance(c.draw(), OpsSet)


# ---------------------------------------------------------------------------
# GlowDot
# ---------------------------------------------------------------------------

class TestGlowDot:
    def test_draw_returns_opsset(self):
        dot = GlowDot(
            center=(200, 200),
            radius=5,
            stroke_style=_STROKE,
            fill_style=FillStyle(color=(1, 1, 0), fill_pattern="solid"),
        )
        result = dot.draw()
        assert isinstance(result, OpsSet)

    def test_draw_contains_dot_ops(self):
        dot = GlowDot(
            center=(200, 200),
            radius=5,
            stroke_style=_STROKE,
            fill_style=FillStyle(color=(1, 1, 0), fill_pattern="solid"),
        )
        types = [op.type for op in dot.draw().opsset]
        assert OpsType.DOT in types

    def test_draw_has_multiple_layers(self):
        dot = GlowDot(
            center=(200, 200),
            radius=5,
            stroke_style=_STROKE,
            fill_style=FillStyle(color=(1, 1, 0), fill_pattern="solid"),
        )
        dot_ops = [op for op in dot.draw().opsset if op.type == OpsType.DOT]
        assert len(dot_ops) == 4  # four glow layers

    def test_layers_have_increasing_radius(self):
        dot = GlowDot(
            center=(0, 0),
            radius=10,
            stroke_style=_STROKE,
            fill_style=FillStyle(color=(1, 0, 0), fill_pattern="solid"),
        )
        radii = [op.data["radius"] for op in dot.draw().opsset if op.type == OpsType.DOT]
        assert radii == sorted(radii)


# ---------------------------------------------------------------------------
# Visual regression
# ---------------------------------------------------------------------------

class TestEllipseVisual:
    def test_ellipse_snapshot(self, render_to_png_bytes, snapshot):
        np.random.seed(42)
        snapshot.assert_match(
            render_to_png_bytes(_ellipse_opsset(), width=600, height=400),
            "ellipse_primitive.png",
        )

    def test_ellipse_self_consistency(self, render_to_png_bytes):
        def to_arr(b):
            return skio.imread(io.BytesIO(b))

        np.random.seed(42)
        a = render_to_png_bytes(_ellipse_opsset(), width=600, height=400)
        np.random.seed(42)
        b = render_to_png_bytes(_ellipse_opsset(), width=600, height=400)
        assert ssim(to_arr(a), to_arr(b), channel_axis=-1) == pytest.approx(1.0)
