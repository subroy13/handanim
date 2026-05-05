from typing import List, Optional, Tuple
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
import numpy as np

from ..core.draw_ops import Ops, OpsSet, OpsType, BoundingBox
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
    """
    A Drawable text primitive that renders text using font glyphs with customizable styling.

    Supports rendering text with random font selection, scaling, and sketch-style variations.
    Converts text characters into drawing operations (OpsSet) that can be rendered.

    Attributes:
        text (str): The text to be rendered
        position (Tuple[float, float]): Starting position for text rendering
        font_size (int, optional): Size of the rendered text. Defaults to 12.
        scale_factor (float, optional): Additional scaling factor. Defaults to 1.0.

    Methods:
        get_random_font_choice(): Selects a font for text rendering
        get_glyph_strokes(char): Converts a character into drawing operations
        get_glyph_space(): Calculates character and space widths
        draw(): Generates the complete set of drawing operations for the text
    """

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
        self._wrapped_lines: Optional[List[str]] = None
        self._line_height: Optional[float] = None

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
            return (OpsSet(initial_set=[]), 0)

        units_per_em = font["head"].unitsPerEm  # usually 1000
        scale = self.scale_factor * self.font_size / units_per_em  # normalize to desired size
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
        space_width = glyph_set["space"].width * scale if "space" in glyph_set else avg_char_width
        return space_width, scale

    def _measure_text_width(self, text: str) -> float:
        """Return the total world-space width of a single line of text at the current font_size."""
        space_width, glyph_scale = self.get_glyph_space()
        total = 0.0
        for char in text:
            if char == " ":
                total += space_width
            else:
                _, glyph_width = self.get_glyph_strokes(char)
                total += glyph_width + glyph_scale * 5
        return total

    def wrap(self, bbox: BoundingBox, line_height_factor: float = 1.5):
        """
        Pre-compute line breaks so that no line of text exceeds bbox.width.

        Splits self.text on spaces and greedily accumulates words onto the current
        line until adding the next word would exceed bbox.width, then starts a new
        line. The text block is anchored at bbox.top_left.

        Args:
            bbox: The bounding box to wrap text within.
            line_height_factor: Multiplier on font_size for the vertical gap between
                lines. 1.5 gives comfortable spacing; 1.2 is tighter.
        """
        words = self.text.split(" ")
        lines: List[str] = []
        current_words: List[str] = []

        for word in words:
            candidate = " ".join(current_words + [word])
            if current_words and self._measure_text_width(candidate) > bbox.width:
                lines.append(" ".join(current_words))
                current_words = [word]
            else:
                current_words.append(word)

        if current_words:
            lines.append(" ".join(current_words))

        self._wrapped_lines = lines
        self._line_height = self.font_size * line_height_factor
        self.position = bbox.top_left

    def autofit(self, bbox: BoundingBox):
        reference_size = 10
        self.font_size = reference_size
        self.position = (0, 0)  # set position at top left of the screen

        draw_ops = self.draw()  # run draw at the reference size
        draw_bbox = draw_ops.get_bbox()

        # we want draw_bbox.top_left to match up with bbox.top_left
        # we want draw_bbox.width to match up with bbox.width
        scale_x = bbox.width / draw_bbox.width
        scale_y = bbox.height / draw_bbox.height

        # set final font size and position
        self.font_size = min(reference_size * scale_x, reference_size * scale_y)
        self.position = (bbox.top_left[0] - draw_bbox.top_left[0], bbox.top_left[1] - draw_bbox.top_left[1])

    def _draw_line(self, opsset: OpsSet, line: str, start_x: float, start_y: float):
        """Render a single line of text into opsset, starting at (start_x, start_y)."""
        space_width, glyph_scale = self.get_glyph_space()
        offset_x, offset_y = start_x, start_y
        for char in line:
            if char == " ":
                offset_x += space_width
            else:
                glyph_opsset, glyph_width = self.get_glyph_strokes(char)
                glyph_opsset.translate(offset_x, offset_y)
                opsset.extend(glyph_opsset)
                offset_x += glyph_width + glyph_scale * 5
                offset_y += np.random.uniform(
                    -self.sketch_style.roughness, self.sketch_style.roughness
                )

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

        if self._wrapped_lines is not None:
            # Multi-line mode: position is the top-left anchor set by wrap().
            # Each line is placed at an increasing y offset; no CG re-centering
            # because the caller explicitly laid out the text within a bbox.
            line_height = self._line_height or self.font_size * 1.5
            start_x, start_y = self.position
            for i, line in enumerate(self._wrapped_lines):
                self._draw_line(opsset, line, start_x, start_y + i * line_height)
        else:
            # Single-line mode: draw at position (0,0) then translate so the
            # center of gravity lands at self.position, matching original behaviour.
            self._draw_line(opsset, self.text, 0, 0)
            cg = opsset.get_center_of_gravity()
            opsset.translate(self.position[0] - cg[0], self.position[1] - cg[1])

        return opsset
