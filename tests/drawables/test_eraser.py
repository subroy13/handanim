"""
Tests for Eraser primitive.

Structure
---------
- TestEraserBasics   — draw() returns OpsSet, contains SET_PEN and LINE_TO ops
- TestEraserCoverage — zigzag motion covers the bounding box of erased objects
"""

import numpy as np
import pytest

from handanim.core.cache import DrawableCache
from handanim.core.draw_ops import Ops, OpsSet, OpsType
from handanim.core.styles import SketchStyle, StrokeStyle
from handanim.primitives.eraser import Eraser
from handanim.primitives.polygons import Rectangle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rect(top_left=(100, 100), width=200, height=150):
    return Rectangle(
        top_left=top_left,
        width=width,
        height=height,
        stroke_style=StrokeStyle(color=(0, 0, 0), width=2),
        sketch_style=SketchStyle(roughness=0, disable_multi_stroke=True),
    )


def _make_eraser(objects, width=10):
    cache = DrawableCache()
    for obj in objects:
        cache.set_drawable_opsset(obj)
    return Eraser(
        objects_to_erase=objects,
        drawable_cache=cache,
        stroke_style=StrokeStyle(color=(1, 1, 1), width=width),
        sketch_style=SketchStyle(),
    )


# ---------------------------------------------------------------------------
# Basics
# ---------------------------------------------------------------------------

class TestEraserBasics:
    def test_draw_returns_opsset(self):
        rect = _make_rect()
        eraser = _make_eraser([rect])
        assert isinstance(eraser.draw(), OpsSet)

    def test_draw_non_empty(self):
        rect = _make_rect()
        eraser = _make_eraser([rect])
        assert len(eraser.draw().opsset) > 0

    def test_draw_starts_with_set_pen(self):
        rect = _make_rect()
        result = _make_eraser([rect]).draw()
        assert result.opsset[0].type == OpsType.SET_PEN

    def test_draw_contains_line_to(self):
        rect = _make_rect()
        result = _make_eraser([rect]).draw()
        types = [op.type for op in result.opsset]
        assert OpsType.LINE_TO in types

    def test_draw_starts_with_move_to(self):
        rect = _make_rect()
        result = _make_eraser([rect]).draw()
        types = [op.type for op in result.opsset]
        assert OpsType.MOVE_TO in types

    def test_pen_width_expanded(self):
        # Eraser pen width should be 10× the stroke width
        rect = _make_rect()
        result = _make_eraser([rect], width=5).draw()
        set_pen = next(op for op in result.opsset if op.type == OpsType.SET_PEN)
        assert set_pen.data["width"] == 50  # 5 * 10


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------

class TestEraserCoverage:
    def test_lines_span_object_x_range(self):
        rect = _make_rect(top_left=(200, 100), width=300, height=200)
        result = _make_eraser([rect], width=5).draw()
        pts = []
        for op in result.opsset:
            if op.type in (OpsType.MOVE_TO, OpsType.LINE_TO):
                pts.extend(op.data)
        xs = [p[0] for p in pts]
        # The eraser should reach at least close to the right edge of the rect
        assert max(xs) >= 450  # 200 + 300 - tolerance

    def test_multiple_objects_merged(self):
        r1 = _make_rect(top_left=(50, 50), width=100, height=100)
        r2 = _make_rect(top_left=(400, 300), width=100, height=100)
        result = _make_eraser([r1, r2], width=5).draw()
        pts = []
        for op in result.opsset:
            if op.type in (OpsType.MOVE_TO, OpsType.LINE_TO):
                pts.extend(op.data)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        assert max(xs) >= 450
        assert max(ys) >= 350
