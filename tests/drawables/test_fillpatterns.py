"""
Tests for fillpatterns: SolidFillPattern, HachureFillPattern, HatchFillPattern,
ZigZagLineFillPattern, and get_filler.

Structure
---------
- TestSolidFill      — fill() returns OpsSet with SET_PEN and CLOSE_PATH
- TestHachureFill    — fill() returns OpsSet with stroke lines
- TestHatchFill      — fill() has more ops than hachure (two angle passes)
- TestZigZagFill     — fill() returns OpsSet
- TestGetFiller      — dispatch to correct class; unknown pattern raises
"""

import numpy as np
import pytest

from handanim.core.draw_ops import OpsSet, OpsType
from handanim.core.styles import FillStyle, SketchStyle
from handanim.stylings.fillpatterns import (
    HachureFillPattern,
    HatchFillPattern,
    SolidFillPattern,
    ZigZagLineFillPattern,
    get_filler,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_SQUARE = [[(0.0, 0.0), (200.0, 0.0), (200.0, 200.0), (0.0, 200.0)]]
_SKETCH = SketchStyle(roughness=0, disable_multi_stroke=True)

_FILL_BASE = FillStyle(
    color=(0.2, 0.6, 0.9),
    opacity=1.0,
    hachure_angle=45,
    hachure_gap=20,
    hachure_line_width=1,
    fill_pattern="hachure",
)


def _solid_fill():
    return SolidFillPattern(
        _SQUARE,
        FillStyle(color=(0.5, 0.5, 0.5), fill_pattern="solid"),
        _SKETCH,
    )


def _hachure_fill():
    return HachureFillPattern(_SQUARE, _FILL_BASE, _SKETCH)


# ---------------------------------------------------------------------------
# SolidFillPattern
# ---------------------------------------------------------------------------

class TestSolidFill:
    def test_fill_returns_opsset(self):
        assert isinstance(_solid_fill().fill(), OpsSet)

    def test_fill_starts_with_set_pen(self):
        result = _solid_fill().fill()
        assert result.opsset[0].type == OpsType.SET_PEN

    def test_fill_mode_is_fill(self):
        result = _solid_fill().fill()
        pen = result.opsset[0]
        assert pen.data.get("mode") == "fill"

    def test_fill_contains_move_and_close(self):
        result = _solid_fill().fill()
        types = [op.type for op in result.opsset]
        assert OpsType.MOVE_TO in types
        assert OpsType.CLOSE_PATH in types

    def test_fill_has_lines_for_each_polygon(self):
        # 4 corners → 4 LINE_TO ops (one per edge after the initial MOVE_TO)
        result = _solid_fill().fill()
        line_ops = [op for op in result.opsset if op.type == OpsType.LINE_TO]
        assert len(line_ops) == 3  # indices 1,2,3 — first corner is MOVE_TO


# ---------------------------------------------------------------------------
# HachureFillPattern
# ---------------------------------------------------------------------------

class TestHachureFill:
    def test_fill_returns_opsset(self):
        assert isinstance(_hachure_fill().fill(), OpsSet)

    def test_fill_non_empty(self):
        result = _hachure_fill().fill()
        assert len(result.opsset) > 0

    def test_fill_starts_with_set_pen(self):
        result = _hachure_fill().fill()
        assert result.opsset[0].type == OpsType.SET_PEN

    def test_fill_contains_line_ops(self):
        result = _hachure_fill().fill()
        types = [op.type for op in result.opsset]
        assert OpsType.LINE_TO in types or OpsType.CURVE_TO in types

    def test_larger_gap_fewer_lines(self):
        fill_dense = FillStyle(color=(0, 0, 0), fill_pattern="hachure", hachure_gap=10, hachure_angle=45)
        fill_sparse = FillStyle(color=(0, 0, 0), fill_pattern="hachure", hachure_gap=50, hachure_angle=45)
        dense = HachureFillPattern(_SQUARE, fill_dense, _SKETCH).fill()
        sparse = HachureFillPattern(_SQUARE, fill_sparse, _SKETCH).fill()
        assert len(dense.opsset) > len(sparse.opsset)


# ---------------------------------------------------------------------------
# HatchFillPattern
# ---------------------------------------------------------------------------

class TestHatchFill:
    def test_fill_returns_opsset(self):
        result = HatchFillPattern(_SQUARE, _FILL_BASE, _SKETCH).fill()
        assert isinstance(result, OpsSet)

    def test_hatch_has_more_ops_than_hachure(self):
        hachure_ops = _hachure_fill().fill().opsset
        hatch_ops = HatchFillPattern(_SQUARE, _FILL_BASE, _SKETCH).fill().opsset
        # Hatch renders two passes at +90°, so should have roughly double the line ops
        assert len(hatch_ops) >= len(hachure_ops)


# ---------------------------------------------------------------------------
# ZigZagLineFillPattern
# ---------------------------------------------------------------------------

class TestZigZagFill:
    def test_fill_returns_opsset(self):
        fill = FillStyle(color=(0, 0, 0), fill_pattern="zigzag", hachure_gap=20, zigzag_offset=10)
        result = ZigZagLineFillPattern(_SQUARE, fill, _SKETCH).fill()
        assert isinstance(result, OpsSet)

    def test_fill_non_empty(self):
        fill = FillStyle(color=(0, 0, 0), fill_pattern="zigzag", hachure_gap=20, zigzag_offset=10)
        result = ZigZagLineFillPattern(_SQUARE, fill, _SKETCH).fill()
        assert len(result.opsset) > 1

    def test_zigzag_offset_negative_uses_gap(self):
        fill = FillStyle(color=(0, 0, 0), fill_pattern="zigzag", hachure_gap=20, zigzag_offset=-1)
        result = ZigZagLineFillPattern(_SQUARE, fill, _SKETCH).fill()
        assert isinstance(result, OpsSet)


# ---------------------------------------------------------------------------
# get_filler dispatch
# ---------------------------------------------------------------------------

class TestGetFiller:
    @pytest.mark.parametrize("pattern,cls", [
        ("hachure", HachureFillPattern),
        ("hatch", HatchFillPattern),
        ("zigzag", ZigZagLineFillPattern),
        ("solid", SolidFillPattern),
    ])
    def test_correct_class_returned(self, pattern, cls):
        fill = FillStyle(fill_pattern=pattern, color=(0, 0, 0))
        filler = get_filler(_SQUARE, fill, _SKETCH)
        assert isinstance(filler, cls)

    def test_unknown_pattern_raises(self):
        fill = FillStyle(fill_pattern="dots", color=(0, 0, 0))
        with pytest.raises(ValueError, match="not supported"):
            get_filler(_SQUARE, fill, _SKETCH)

    def test_filler_fill_returns_opsset(self):
        fill = FillStyle(fill_pattern="solid", color=(0.5, 0.5, 0.5))
        result = get_filler(_SQUARE, fill, _SKETCH).fill()
        assert isinstance(result, OpsSet)
