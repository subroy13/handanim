from typing import Tuple
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
import numpy as np

from ..core.draw_ops import Ops, OpsSet, OpsType
from ..core.drawable import Drawable
from ..stylings.fonts import list_fonts, get_font_path


class CustomPen(BasePen):
    # overwrite some methods to capture the strokes

    def __init__(self, glyphSet, scale: float = 0.01):
        super().__init__(glyphSet)
        self.opsset = OpsSet(initial_set=[])
        self.scale = scale
        self.min_x = self.min_y = float("inf")
        self.max_x = self.max_y = -float("inf")

    def _scale_point(self, pt):
        x, y = pt[0] * self.scale, -pt[1] * self.scale
        # update bounding box
        self.min_x = min(self.min_x, x)
        self.min_y = min(self.min_y, y)
        self.max_x = max(self.max_x, x)
        self.max_y = max(self.max_y, y)
        return (x, y)

    def _moveTo(self, pt):
        self.opsset.add(Ops(OpsType.MOVE_TO, data=[self._scale_point(pt)]))

    def _lineTo(self, pt):
        self.opsset.add(Ops(OpsType.LINE_TO, data=[self._scale_point(pt)]))

    def _curveToOne(self, pt1, pt2, pt3):
        self.opsset.add(
            Ops(
                OpsType.CURVE_TO,
                data=[
                    self._scale_point(pt1),
                    self._scale_point(pt2),
                    self._scale_point(pt3),
                ],
            )
        )

    def _closePath(self):
        self.opsset.add(Ops(OpsType.CLOSE_PATH, data={}))


class Text(Drawable):

    def __init__(
        self,
        text: str,
        position: Tuple[float, float],
        font_size: int = 12,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.text = text
        self.position = position
        self.font_size = font_size
        self.scale_factor = kwargs.get("scale_factor", 1.0)

    def get_random_font_choice(self) -> Tuple[str, str]:
        """
        Chooses a random font from the available fonts
        """
        font_list = list_fonts()
        if self.sketch_style.disable_font_mixture:
            font_choice = font_list[0]
        else:
            font_choice = np.random.choice(font_list)
        return (font_choice, get_font_path(font_choice))

    def get_glyph_strokes(self, char) -> Tuple[OpsSet, float]:
        """
        Gives the glyph operations as well the width of the char for offsetting purpose
        """
        font_choice, font_path = self.get_random_font_choice()
        font = TTFont(font_path)
        glyph_set = font.getGlyphSet()
        cmap = font.getBestCmap()
        glyph_name = cmap.get(ord(char))
        if glyph_name is None:
            return OpsSet(initial_set=[])

        units_per_em = font["head"].unitsPerEm  # usually 1000
        scale = (
            self.scale_factor * self.font_size / units_per_em
        )  # normalize to desired size
        glyph = glyph_set[glyph_name]
        pen = CustomPen(glyph_set, scale=scale)
        glyph.draw(pen)

        width = glyph.width * scale
        return pen.opsset, width

    def get_glyph_space(self) -> Tuple[float, float]:
        """
        Gives the width of the space, or an average width
        """
        font_choice, font_path = self.get_random_font_choice()
        font = TTFont(font_path)
        glyph_set = font.getGlyphSet()
        units_per_em = font["head"].unitsPerEm
        scale = self.scale_factor * self.font_size / units_per_em

        avg_char_width = font["hhea"].advanceWidthMax * scale * 0.5
        space_width = (
            glyph_set["space"].width * scale if "space" in glyph_set else avg_char_width
        )
        return space_width, scale

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
        offset_x, offset_y = self.position
        space_width, glyph_scale = self.get_glyph_space()
        for char in self.text:
            if char == " ":
                offset_x += space_width
                continue
            else:
                glyph_opsset, glyph_width = self.get_glyph_strokes(char)
                glyph_opsset.translate(offset_x, offset_y)
                opsset.extend(glyph_opsset)

                # add small padding
                offset_x += glyph_width + glyph_scale * 5
                offset_y += np.random.uniform(
                    -self.sketch_style.roughness, self.sketch_style.roughness
                )
        return opsset
