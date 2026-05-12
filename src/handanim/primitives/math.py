import json
from typing import Any

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
from ..stylings.fonts import get_font_path
from ..stylings.strokes import apply_stroke_pressure
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


class Math(Drawable):
    """
    A Drawable class for rendering mathematical expressions using TeX notation.

    This class parses a TeX expression and renders individual glyphs using a specified font,
    supporting custom positioning, scaling, and stroke styling.

    Attributes:
        tex_expression (str): The TeX mathematical expression to render
        position (Tuple[float, float]): The starting position for rendering the expression
        font_size (int, optional): The size of the font, defaults to 12
        font_name (str): The name of the font to use for rendering, defaults to "feasibly"

    Methods:
        get_glyph_opsset: Extracts the operations set for a single unicode glyph
        draw: Renders the entire mathematical expression as a set of drawing operations
    """

    def __init__(
        self,
        tex_expression: str,
        position: tuple[float, float],
        font_size: int = 12,
        font_name: str = "handanimtype1",
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

    def load_font(self):
        font_path = get_font_path(self.font_name)
        if font_path.endswith(".json"):
            # this is custom-made svg font
            with open(font_path) as f:
                self.font_details = json.load(f)
                self.font_details["type"] = "custom"
        else:
            font = TTFont(font_path)
            glyph_set = font.getGlyphSet()
            cmap = font.getBestCmap()
            units_per_em = font["head"].unitsPerEm  # usually 1000
            self.font_details = {
                "type": "standard",
                "glyph_set": glyph_set,
                "cmap": cmap,
                "units_per_em": units_per_em,
            }

    def standard_glyph_opsset(
        self, unicode: int, font_size: int
    ) -> tuple[OpsSet, float, float]:
        glyph_set = self.font_details["glyph_set"]
        cmap = self.font_details["cmap"]
        units_per_em = self.font_details["units_per_em"]
        glyph_name = cmap.get(unicode)
        if glyph_name is None:
            return OpsSet(initial_set=[]), 1.0, 1.0

        scale = font_size / units_per_em  # normalize to desired size
        glyph = glyph_set[glyph_name]
        pen = CustomPen(glyph_set, scale=scale)
        glyph.draw(pen)

        # now get the bounding box
        dx, dy = pen.min_x, pen.min_y
        pen.opsset.translate(-dx, -dy)  # so top-left is (0, 0)

        width = glyph.width * scale
        height = pen.max_y - pen.min_y
        return pen.opsset, height, width

    def custom_glyph_opsset(
        self, unicode: int, font_size: int
    ) -> tuple[OpsSet, float, float]:
        if str(unicode) not in self.font_details["glyphs"]:
            print(f"Glyph {chr(unicode)}, unicode {unicode} not found in font")
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

    def get_glyph_opsset(
        self, unicode: int, font_size: int
    ) -> tuple[OpsSet, float, float]:
        """
        Returns the opset for a single glyph of a unicode number
        """
        if self.font_details["type"] == "custom":
            # this is custom-made svg font
            return self.custom_glyph_opsset(unicode, font_size)
        else:
            return self.standard_glyph_opsset(unicode, font_size)

    def draw(self) -> OpsSet:
        opsset = OpsSet(initial_set=[])
        opsset.add(
            Ops(
                OpsType.SET_PEN,
                {
                    "color": self.stroke_style.color,
                    "opacity": self.stroke_style.opacity,
                    "width": self.stroke_style.width,
                },
            )
        )

        # parse and extract the glyphs from matplotlib parsing
        parse_out = self.parser.parse(self.tex_expression)
        glyphs = (
            parse_out.glyphs
        )  # list of tuple of (font, font_size, char, offset_x, offset_y)
        boxes = parse_out.rects  # list of tuple of (x, y, width, height)

        for glyph in glyphs:
            # offset_x = postion of the glyph relative to start at 0.0
            # offset_y = position of the glyph relative to the baseline
            font, font_size, unicode, offset_x, offset_y = glyph
            glyph_opsset, glyph_height, glyph_width = self.get_glyph_opsset(
                unicode,
                font_size=font_size * self.scale_factor,  # type: ignore[arg-type]
            )
            draw_x = offset_x * self.scale_factor + self.position[0]
            draw_y = (
                self.position[1]
                + (10 * self.scale_factor - glyph_height)
                - offset_y * self.scale_factor
            )  # this ensures the lower edge matches the baseline
            glyph_opsset.translate(draw_x, draw_y)

            # draw glyph
            opsset.add(
                Ops(
                    OpsType.SET_PEN,
                    {
                        "color": self.stroke_style.color,
                        "opacity": self.stroke_style.opacity,
                        "width": self.stroke_style.width,
                    },
                )
            )
            opsset.extend(glyph_opsset)  # continue adding to the opset for each glyph

        # finally draw the lines
        current_stroke_width = self.stroke_style.width
        for box in boxes:
            x, y, width, height = box  # we will approximate by a thick line
            self.stroke_style.width = height / 2 * self.scale_factor
            draw_x, draw_y = (
                self.position[0] + self.scale_factor * x,
                self.position[1] + (10 - height / 2 - y) * self.scale_factor,
            )

            line = Line(
                start=(draw_x, draw_y),
                end=(draw_x + self.scale_factor * width, draw_y),
                stroke_style=self.stroke_style,
            )
            opsset.extend(line.draw())
        self.stroke_style.width = current_stroke_width

        # for the character strokes, apply pen pressures
        if self.stroke_style.stroke_pressure != StrokePressure.CONSTANT:
            opsset = apply_stroke_pressure(opsset, self.stroke_style.stroke_pressure)

        return opsset
