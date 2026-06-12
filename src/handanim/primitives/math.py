import json
import unicodedata
from typing import Any

import numpy as np
from fontTools.ttLib import TTFont
from matplotlib.mathtext import MathTextParser
from svgelements import Close as SVGClose
from svgelements import CubicBezier as SVGCubicBezier
from svgelements import Line as SVGLine
from svgelements import Move as SVGMove
from svgelements import Path as SVGPath
from svgelements import QuadraticBezier as SVGQuadBezier

from ..core.draw_ops import Ops, OpsSet, OpsType
from ..core.drawable import Drawable
from ..core.styles import StrokePressure
from ..stylings.strokes import apply_stroke_pressure
from .hershey_constants import (
    COMPOSED_GLYPHS,
    HERSHEY_ASCII_FALLBACK,
    HERSHEY_FONT_UNITS,
    UNICODE_TO_HERSHEY,
)
from .lines import Line
from .text import CustomPen


def _svg_paths_to_opsset(svg_path_strings: list[str]) -> OpsSet:
    opsset = OpsSet(initial_set=[])
    for path_str in svg_path_strings:
        for seg in SVGPath(path_str).segments():
            if isinstance(seg, SVGMove):
                opsset.add(Ops(OpsType.MOVE_TO, [(seg.end.x, seg.end.y)]))
            elif isinstance(seg, SVGLine):
                opsset.add(Ops(OpsType.LINE_TO, [(seg.end.x, seg.end.y)]))
            elif isinstance(seg, SVGQuadBezier):
                opsset.add(Ops(OpsType.QUAD_CURVE_TO, [(seg.control.x, seg.control.y), (seg.end.x, seg.end.y)]))
            elif isinstance(seg, SVGCubicBezier):
                opsset.add(Ops(OpsType.CURVE_TO, [(seg.control1.x, seg.control1.y), (seg.control2.x, seg.control2.y), (seg.end.x, seg.end.y)]))
            elif isinstance(seg, SVGClose):
                opsset.add(Ops(OpsType.CLOSE_PATH, data={}))
    return opsset


# ---------------------------------------------------------------------------
# Hershey rendering helpers
# ---------------------------------------------------------------------------

def _hershey_font_to_opsset(font_name: str, char: str) -> OpsSet | None:
    """Return an OpsSet for `char` in the given Hershey font, or None if not found."""
    from HersheyFonts import HersheyFonts
    font = HersheyFonts()
    font.load_default_font(font_name)
    lines = list(font.lines_for_text(char))
    if not lines:
        return None
    ops = OpsSet(initial_set=[])
    last_point = None
    for p1, p2 in lines:
        if p1 != last_point:
            ops.add(Ops(OpsType.MOVE_TO, data=[p1]))
        ops.add(Ops(OpsType.LINE_TO, data=[p2]))
        last_point = p2
    return ops


def _scale_hershey_opsset(ops: OpsSet, font_size: float) -> tuple[OpsSet, float, float]:
    """Scale an OpsSet from Hershey font units to pixels, translating origin to (0, 0).

    Scales each point directly from the coordinate origin (not from the
    bounding-box centre the way OpsSet.scale() does), then translates so
    that the top-left of the post-scale bounding box is at (0, 0).  This
    is exact for all glyph shapes regardless of symmetry.
    """
    font_scale = font_size / HERSHEY_FONT_UNITS
    # Scale points from origin — bypasses OpsSet.scale() which uses CG
    scaled = OpsSet(initial_set=[])
    for op in ops.opsset:
        if isinstance(op.data, list):
            scaled.add(Ops(
                op.type,
                [(x * font_scale, y * font_scale) for x, y in op.data],
                op.partial,
                op.meta,
            ))
        else:
            scaled.add(op)
    # Use the actual post-scale bbox to normalise origin
    bbox = scaled.get_bbox()
    scaled.translate(-bbox.min_x, -bbox.min_y)
    return scaled, bbox.height, bbox.width


def _apply_roughness(ops: OpsSet, roughness: float) -> OpsSet:
    """Replace straight LINE_TO segments with lightly curved CURVE_TO segments.

    Each segment gets two cubic Bézier control points displaced
    perpendicularly by a random amount proportional to roughness and
    √(segment length).  This gives a hand-drawn wobble without moving
    the endpoints.
    """
    if roughness <= 0:
        return ops
    result = OpsSet(initial_set=[])
    current_pt: tuple[float, float] = (0.0, 0.0)
    for op in ops.opsset:
        if op.type == OpsType.MOVE_TO and isinstance(op.data, list):
            current_pt = tuple(op.data[0])  # type: ignore[assignment]
            result.add(op)
        elif op.type == OpsType.LINE_TO and isinstance(op.data, list):
            end_pt: tuple[float, float] = tuple(op.data[0])  # type: ignore[assignment]
            dx = end_pt[0] - current_pt[0]
            dy = end_pt[1] - current_pt[1]
            length = (dx * dx + dy * dy) ** 0.5
            if length > 0.5:
                # Perpendicular unit vector
                px, py = -dy / length, dx / length
                amp = roughness * (length ** 0.5)
                c1 = (
                    current_pt[0] + dx / 3 + px * np.random.uniform(-amp, amp),
                    current_pt[1] + dy / 3 + py * np.random.uniform(-amp, amp),
                )
                c2 = (
                    current_pt[0] + 2 * dx / 3 + px * np.random.uniform(-amp, amp),
                    current_pt[1] + 2 * dy / 3 + py * np.random.uniform(-amp, amp),
                )
                result.add(Ops(OpsType.CURVE_TO, [c1, c2, end_pt], op.partial, op.meta))
            else:
                result.add(op)
            current_pt = end_pt
        else:
            result.add(op)
            if op.type == OpsType.CURVE_TO and isinstance(op.data, list):
                current_pt = tuple(op.data[-1])  # type: ignore[assignment]
            elif op.type == OpsType.QUAD_CURVE_TO and isinstance(op.data, list):
                current_pt = tuple(op.data[-1])  # type: ignore[assignment]
    return result


def _composed_to_opsset(
    strokes: list[list[tuple[float, float]]], font_size: float
) -> tuple[OpsSet, float, float]:
    """Build an OpsSet from composed glyph stroke definitions and scale it."""
    ops = OpsSet(initial_set=[])
    for stroke in strokes:
        if not stroke:
            continue
        ops.add(Ops(OpsType.MOVE_TO, data=[stroke[0]]))
        for pt in stroke[1:]:
            ops.add(Ops(OpsType.LINE_TO, data=[pt]))
    return _scale_hershey_opsset(ops, font_size)


# ---------------------------------------------------------------------------
# Math drawable
# ---------------------------------------------------------------------------

class Math(Drawable):
    """
    A Drawable class for rendering mathematical expressions using TeX notation.

    Parses a TeX expression via matplotlib's MathTextParser and renders
    individual glyphs using the specified font backend.

    Attributes:
        tex_expression: The TeX expression to render.
        position: Top-left anchor (x, y) for the rendered expression.
        font_size: Logical font size; the base unit is 10 (scale_factor = font_size / 10).
        font_name: Font backend to use (see stylings/fonts.py).
    """

    def __init__(
        self,
        tex_expression: str,
        position: tuple[float, float],
        font_size: int = 12,
        font_name: str = "feasibly",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.tex_expression = tex_expression
        self.position = position
        self.scale_factor = font_size / 10  # base size is 10
        self.parser = MathTextParser("path")
        self.font_name = font_name
        self.font_details: dict[str, Any] = {}
        self.load_font()

    def load_font(self) -> None:
        from ..stylings.fonts import get_font_info, get_font_path

        font_info = get_font_info(self.font_name)
        if not font_info:
            raise ValueError(f"Unknown font: {self.font_name}")

        self.font_details = {"type": font_info["type"]}

        if font_info["type"] == "custom":
            font_path = get_font_path(self.font_name)
            with open(font_path) as f:
                self.font_details.update(json.load(f))
        elif font_info["type"] == "hershey":
            self.font_details["name"] = font_info["name"]
        elif font_info["type"] == "ttf":
            font_path = get_font_path(self.font_name)
            font = TTFont(font_path)
            glyph_set = font.getGlyphSet()
            cmap = font.getBestCmap()
            units_per_em = font["head"].unitsPerEm  # usually 1000
            self.font_details.update({
                "glyph_set": glyph_set,
                "cmap": cmap,
                "units_per_em": units_per_em,
            })

    # ------------------------------------------------------------------
    # Per-backend glyph renderers
    # ------------------------------------------------------------------

    def standard_glyph_opsset(
        self, unicode: int, font_size: int
    ) -> tuple[OpsSet, float, float]:
        glyph_set = self.font_details["glyph_set"]
        cmap = self.font_details["cmap"]
        units_per_em = self.font_details["units_per_em"]
        glyph_name = cmap.get(unicode)
        if glyph_name is None:
            return OpsSet(initial_set=[]), 1.0, 1.0

        scale = font_size / units_per_em
        glyph = glyph_set[glyph_name]
        pen = CustomPen(glyph_set, scale=scale)
        glyph.draw(pen)

        dx, dy = pen.min_x, pen.min_y
        pen.opsset.translate(-dx, -dy)

        width = glyph.width * scale
        height = pen.max_y - pen.min_y
        return pen.opsset, height, width

    def custom_glyph_opsset(
        self, unicode: int, font_size: int
    ) -> tuple[OpsSet, float, float]:
        if str(unicode) not in self.font_details["glyphs"]:
            print(f"Glyph {chr(unicode)!r} (U+{unicode:04X}) not found in custom font")
            return OpsSet(initial_set=[]), 1.0, 1.0
        glyph_svg_paths = self.font_details["glyphs"][str(unicode)]
        svg_ops = _svg_paths_to_opsset(glyph_svg_paths)
        font_units = self.font_details["metadata"]["font_size"]
        font_scale = font_size / font_units
        bbox = svg_ops.get_bbox()
        width = bbox.width * font_scale
        height = bbox.height * font_scale
        svg_ops.scale(font_scale)
        svg_ops.translate(-bbox.min_x * font_scale, -bbox.min_y * font_scale)
        return svg_ops, height, width

    def hershey_glyph_opsset(
        self, unicode: int, font_size: int
    ) -> tuple[OpsSet, float, float]:
        roughness = self.sketch_style.roughness

        def _finish(ops: OpsSet, h: float, w: float) -> tuple[OpsSet, float, float]:
            if roughness > 0:
                ops = _apply_roughness(ops, roughness)
            return ops, h, w

        # 1. Composed glyphs: explicit hand-defined stroke shapes take priority.
        if unicode in COMPOSED_GLYPHS:
            return _finish(*_composed_to_opsset(COMPOSED_GLYPHS[unicode], font_size))

        # 2. Explicit Hershey font mapping (standard Greek, blackboard bold, etc.)
        if unicode in UNICODE_TO_HERSHEY:
            font_name, char = UNICODE_TO_HERSHEY[unicode]
            ops = _hershey_font_to_opsset(font_name, char)
            if ops is not None:
                return _finish(*_scale_hershey_opsset(ops, font_size))

        # 3. NFKD normalisation for math-variant Unicode codepoints.
        #    Examples: U+1D6FC MATHEMATICAL ITALIC SMALL ALPHA → α (U+03B1 = 945)
        #              U+1D465 MATHEMATICAL ITALIC SMALL X     → x (U+0078 = 120)
        char = chr(unicode)
        normalized = unicodedata.normalize("NFKD", char)
        if len(normalized) == 1:
            nfkd_cp = ord(normalized)
            # Re-check the explicit table with the normalised codepoint.
            # This is the critical step that was missing: without it, math-italic
            # Greek letters would not find their ('mathlow', …) mapping.
            if nfkd_cp in UNICODE_TO_HERSHEY:
                font_name, hershey_char = UNICODE_TO_HERSHEY[nfkd_cp]
                ops = _hershey_font_to_opsset(font_name, hershey_char)
                if ops is not None:
                    return _finish(*_scale_hershey_opsset(ops, font_size))
            # For ASCII-range normalised chars, use rowmans (not the base font
            # which may encode Greek at Latin character positions).
            if 32 <= nfkd_cp <= 127:
                char = normalized

        if 32 <= ord(char) <= 127:
            ops = _hershey_font_to_opsset(HERSHEY_ASCII_FALLBACK, char)
            if ops is not None:
                return _finish(*_scale_hershey_opsset(ops, font_size))

        # 4. Last resort: try the font the user explicitly selected.
        base_font_name = self.font_details["name"]
        ops = _hershey_font_to_opsset(base_font_name, char)
        if ops is not None:
            return _finish(*_scale_hershey_opsset(ops, font_size))

        print(f"Hershey: U+{unicode:04X} ({chr(unicode)!r}) not found — skipping")
        return OpsSet(initial_set=[]), 1.0, 1.0

    def get_glyph_opsset(
        self, unicode: int, font_size: int
    ) -> tuple[OpsSet, float, float]:
        if self.font_details["type"] == "custom":
            return self.custom_glyph_opsset(unicode, font_size)
        elif self.font_details["type"] == "hershey":
            return self.hershey_glyph_opsset(unicode, font_size)
        else:
            return self.standard_glyph_opsset(unicode, font_size)

    def draw(self) -> OpsSet:
        opsset = OpsSet(initial_set=[])
        opsset.add(Ops(OpsType.SET_PEN, {
            "color":   self.stroke_style.color,
            "opacity": self.stroke_style.opacity,
            "width":   self.stroke_style.width,
        }))

        parse_out = self.parser.parse(self.tex_expression)
        glyphs = parse_out.glyphs   # (font, font_size, codepoint, offset_x, offset_y)
        boxes  = parse_out.rects    # (x, y, width, height) — fraction bars, vinculum, etc.

        for glyph in glyphs:
            font, font_size, unicode, *rest = glyph
            offset_x, offset_y = rest[-2:]

            glyph_opsset, glyph_height, glyph_width = self.get_glyph_opsset(
                unicode,
                font_size=font_size * self.scale_factor,  # type: ignore[arg-type]
            )
            draw_x = offset_x * self.scale_factor + self.position[0]
            draw_y = (
                self.position[1]
                + (10 * self.scale_factor - glyph_height)
                - offset_y * self.scale_factor
            )
            glyph_opsset.translate(draw_x, draw_y)

            opsset.add(Ops(OpsType.SET_PEN, {
                "color":   self.stroke_style.color,
                "opacity": self.stroke_style.opacity,
                "width":   self.stroke_style.width,
            }))
            opsset.extend(glyph_opsset)

        # Draw fraction bars, radical vinculum, etc. (returned as rectangles)
        current_stroke_width = self.stroke_style.width
        for box in boxes:
            x, y, width, height = box
            self.stroke_style.width = height / 2 * self.scale_factor
            draw_x = self.position[0] + self.scale_factor * x
            draw_y = self.position[1] + (10 - height / 2 - y) * self.scale_factor
            line = Line(
                start=(draw_x, draw_y),
                end=(draw_x + self.scale_factor * width, draw_y),
                stroke_style=self.stroke_style,
            )
            opsset.extend(line.draw())
        self.stroke_style.width = current_stroke_width

        if self.stroke_style.stroke_pressure != StrokePressure.CONSTANT:
            opsset = apply_stroke_pressure(opsset, self.stroke_style.stroke_pressure)

        return opsset
