"""
Tests for VectorSVG primitive.

Structure
---------
- TestVectorSVGParse      — from_svg_string produces a VectorSVG; draw() returns OpsSet
- TestVectorSVGColorParse — _parse_color_and_opacity handles None and Color objects
- TestVectorSVGOps        — draw output contains expected op types for simple shapes
- TestVectorSVGPosition   — position offset shifts coordinates
"""

import pytest

from handanim.core.draw_ops import OpsSet, OpsType
from handanim.primitives.vector_svg import VectorSVG


# ---------------------------------------------------------------------------
# Minimal SVG fixtures
# ---------------------------------------------------------------------------

_SVG_LINE = """
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <line x1="10" y1="10" x2="190" y2="190" stroke="black" stroke-width="2"/>
</svg>
"""

_SVG_RECT = """
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <rect x="20" y="20" width="160" height="160" stroke="blue" stroke-width="2" fill="none"/>
</svg>
"""

_SVG_FILLED_CIRCLE = """
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <circle cx="100" cy="100" r="50" fill="red" stroke="none"/>
</svg>
"""

_SVG_EMPTY = """
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
</svg>
"""

_SVG_QUADRATIC = """
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <path d="M 10 80 Q 100 10 190 80" stroke="green" stroke-width="2" fill="none"/>
</svg>
"""

_SVG_CUBIC = """
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <path d="M 10 80 C 40 10 160 10 190 80" stroke="purple" stroke-width="2" fill="none"/>
</svg>
"""

_SVG_HIDDEN = """
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <rect x="20" y="20" width="160" height="160" stroke="black" stroke-width="2" fill="none" visibility="hidden"/>
</svg>
"""


def _make_svg(svg_string: str, position=(0.0, 0.0)):
    return VectorSVG.from_svg_string(svg_string, position=position)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

class TestVectorSVGParse:
    def test_from_svg_string_returns_vector_svg(self):
        v = _make_svg(_SVG_LINE)
        assert isinstance(v, VectorSVG)

    def test_draw_returns_opsset(self):
        assert isinstance(_make_svg(_SVG_LINE).draw(), OpsSet)

    def test_empty_svg_returns_empty_opsset(self):
        result = _make_svg(_SVG_EMPTY).draw()
        assert len(result.opsset) == 0

    def test_hidden_element_not_drawn(self):
        result = _make_svg(_SVG_HIDDEN).draw()
        # No geometric ops should be present
        geo_types = {OpsType.LINE_TO, OpsType.CURVE_TO, OpsType.MOVE_TO}
        assert not any(op.type in geo_types for op in result.opsset)


# ---------------------------------------------------------------------------
# Op types for shapes
# ---------------------------------------------------------------------------

class TestVectorSVGOps:
    def test_line_produces_line_to(self):
        result = _make_svg(_SVG_LINE).draw()
        types = [op.type for op in result.opsset]
        assert OpsType.LINE_TO in types

    def test_rect_produces_multiple_line_to(self):
        result = _make_svg(_SVG_RECT).draw()
        line_ops = [op for op in result.opsset if op.type == OpsType.LINE_TO]
        assert len(line_ops) >= 3  # three remaining sides after initial MOVE_TO

    def test_quadratic_path_produces_quad_curve(self):
        result = _make_svg(_SVG_QUADRATIC).draw()
        types = [op.type for op in result.opsset]
        assert OpsType.QUAD_CURVE_TO in types or OpsType.CURVE_TO in types

    def test_cubic_path_produces_curve_to(self):
        result = _make_svg(_SVG_CUBIC).draw()
        types = [op.type for op in result.opsset]
        assert OpsType.CURVE_TO in types

    def test_set_pen_present(self):
        result = _make_svg(_SVG_RECT).draw()
        types = [op.type for op in result.opsset]
        assert OpsType.SET_PEN in types

    def test_filled_circle_set_pen_mode_fill(self):
        result = _make_svg(_SVG_FILLED_CIRCLE).draw()
        fill_pens = [op for op in result.opsset if op.type == OpsType.SET_PEN and op.data.get("mode") == "fill"]
        assert len(fill_pens) > 0


# ---------------------------------------------------------------------------
# Position offset
# ---------------------------------------------------------------------------

class TestVectorSVGPosition:
    def test_position_shifts_coordinates(self):
        offset = (100.0, 50.0)
        v_origin = _make_svg(_SVG_LINE, position=(0.0, 0.0))
        v_shifted = _make_svg(_SVG_LINE, position=offset)

        def extract_pts(opsset):
            pts = []
            for op in opsset.opsset:
                if isinstance(op.data, list):
                    pts.extend(op.data)
            return pts

        pts_origin = extract_pts(v_origin.draw())
        pts_shifted = extract_pts(v_shifted.draw())

        for (ox, oy), (sx, sy) in zip(pts_origin, pts_shifted):
            assert sx == pytest.approx(ox + offset[0], abs=1e-4)
            assert sy == pytest.approx(oy + offset[1], abs=1e-4)


# ---------------------------------------------------------------------------
# Color parsing
# ---------------------------------------------------------------------------

class TestColorParsing:
    def _instance(self):
        return _make_svg(_SVG_LINE)

    def test_none_color_returns_none_and_zero_alpha(self):
        v = self._instance()
        rgb, alpha = v._parse_color_and_opacity(None)
        assert rgb is None
        assert alpha == 0.0
