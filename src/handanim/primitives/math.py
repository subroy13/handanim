from typing import Tuple, List
import matplotlib as mpl
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MplPath
from matplotlib.mathtext import MathTextParser
from fontTools.ttLib import TTFont

from ..core.draw_ops import Ops, OpsType, OpsSet
from ..core.drawable import Drawable
from ..stylings.fonts import get_font_path
from .text import CustomPen
from .lines import Line


class Math(Drawable):

    def __init__(
        self,
        tex_expression: str,
        position: Tuple[float, float],
        font_size: int = 12,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.tex_expression = tex_expression
        self.position = position
        self.font_size = font_size

    def _transform_points(
        self, points: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """
        Transforms a list of points from matplotlib coordinate system to cairo coordinate system
        """
        pos_x, pos_y = self.position
        return [(x, 2 * pos_y - y) for x, y in points]

    def convert_textpath_to_ops(self, drawpath: TextPath) -> OpsSet:
        opsset = OpsSet(initial_set=[])
        for verts, code in drawpath.iter_segments():
            if code == MplPath.MOVETO:
                opsset.add(Ops(OpsType.MOVE_TO, data=self._transform_points([verts])))
            elif code == MplPath.LINETO:
                opsset.add(Ops(OpsType.LINE_TO, data=self._transform_points([verts])))
            elif code == MplPath.CURVE3:
                opsset.add(
                    Ops(
                        OpsType.QUAD_CURVE_TO,
                        data=self._transform_points(verts.reshape(2, 2)),
                    )
                )
            elif code == MplPath.CURVE4:
                opsset.add(
                    Ops(
                        OpsType.CURVE_TO,
                        data=self._transform_points(verts.reshape(3, 2)),
                    )
                )
            elif code == MplPath.CLOSEPOLY:
                opsset.add(Ops(OpsType.CLOSE_PATH, data={}))
            else:
                raise ValueError(f"Unknown path code: {code}")
        return opsset

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
        fp = FontProperties(
            fname=get_font_path("feasibly"),
        )
        current_rcparams = mpl.rcParams.copy()
        mpl.rcParams["mathtext.fontset"] = "custom"
        mpl.rcParams["mathtext.rm"] = fp.get_name()
        mpl.rcParams["mathtext.it"] = fp.get_name()
        mpl.rcParams["mathtext.bf"] = fp.get_name()
        drawpath = TextPath(
            self.position,
            self.tex_expression,
            size=self.font_size,
            prop=fp,
            usetex=False,  # use default mathplotlib handling
        )
        mpl.rcParams = current_rcparams  # once drawing complete, reset back
        opsset.extend(self.convert_textpath_to_ops(drawpath))
        return opsset


class Math2(Drawable):

    def __init__(
        self,
        tex_expression: str,
        position: Tuple[float, float],
        font_size: int = 12,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.tex_expression = tex_expression
        self.position = position
        self.scale_factor = font_size / 10  # base size is 10
        self.parser = MathTextParser("path")
        self.font_name = "notosans_math"

    def get_glyph_opsset(
        self, unicode: int, font_size: int
    ) -> Tuple[OpsSet, float, float]:
        """
        Returns the opset for a single glyph of a unicode number
        """
        font = TTFont(get_font_path(self.font_name))
        glyph_set = font.getGlyphSet()
        cmap = font.getBestCmap()
        glyph_name = cmap.get(unicode)
        if glyph_name is None:
            return OpsSet(initial_set=[]), 1.0, 1.0

        units_per_em = font["head"].unitsPerEm  # usually 1000
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
                font_size=font_size
                * self.scale_factor,  # scale the font size appropriately
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

        return opsset
