import numpy as np
from .base import BasePrimitive
from .line import Line
from ..transformed_context import TransformedContext

class RectangleFillType:
    DIAGONAL = "diagonal"
    ANTI_DIAGONAL = "anti_diagonal"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    CHECKER = "checker"
    CHECKER_DIAGONAL = "checker_diagonal"



class Rectangle(BasePrimitive):
    """
        A class to represent a rectangle in a hand-drawn style.
    """
    def __init__(
        self,
        bottom_left: tuple[float, float],
        width: float,
        height: float,
        stroke_color: tuple[float, float, float] = (0, 0, 0),
        stroke_width: float = 1,
        roughness: float = 1.0,
        pastel: bool = False,  # whether to use pastel colors
        sketch_number: int = 2,  # number of sketch lines
        fill_color: tuple[float, float, float] = None,  # fill color
        fill_type: RectangleFillType = RectangleFillType.DIAGONAL,  # fill type
        fill_spacing: float = 10,  # spacing between fill lines
    ):
        self.x, self.y = bottom_left
        self.width = width
        self.height = height
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.roughness = roughness
        self.pastel = pastel
        self.sketch_number = sketch_number
        self.fill_color = fill_color
        self.fill_type = fill_type
        self.fill_spacing = fill_spacing

    def _draw_sketchy_line(self, start: tuple[float, float], end: tuple[float, float], ctx: TransformedContext):
        """
            Draws a hand-drawn-like line with some jitter
        """
        line = Line(start, end, self.stroke_color, self.stroke_width, self.roughness, self.pastel, self.sketch_number)
        line.draw(ctx)

    def _fill_hachure(self, ctx: TransformedContext):
        """
            Fills the rectangle with a filling pattern
        """
        if self.fill_color is None:
            return

        # clip to rectangle
        ctx.save()
        ctx.rectangle(self.x, self.y, self.width, self.height)
        ctx.clip()

        # pastel fill effect
        r, g, b = self.fill_color
        ctx.set_source_rgba(r, g, b, 0.3 if self.pastel else 1.0)
        ctx.set_line_width(1 if not self.pastel else 2)  # thicker lines for pastel

        # now draw the filling pattern
        spacing = self.fill_spacing  # distance between hatch lines
        if self.fill_type == RectangleFillType.HORIZONTAL:
            for ysub in np.arange(self.y, self.y + self.height, spacing):
                ctx.move_to(self.x, ysub)
                ctx.line_to(self.x + self.width, ysub)
                ctx.stroke()
        elif self.fill_type == RectangleFillType.VERTICAL:
            for xsub in np.arange(self.x, self.x + self.width, spacing):
                ctx.move_to(xsub, self.y)
                ctx.line_to(xsub, self.y + self.height)
                ctx.stroke()
        elif self.fill_type == RectangleFillType.CHECKER:
            # both horizontal and vertical lines
            for ysub in np.arange(self.y, self.y + self.height, spacing):
                ctx.move_to(self.x, ysub)
                ctx.line_to(self.x + self.width, ysub)
                ctx.stroke()
            for xsub in np.arange(self.x, self.x + self.width, spacing):
                ctx.move_to(xsub, self.y)
                ctx.line_to(xsub, self.y + self.height)
                ctx.stroke()
        elif self.fill_type == RectangleFillType.DIAGONAL:
            # diagonal hatch lines
            angle = np.radians(45)
            tan_a = np.tan(angle)
            for ysub in np.arange(self.y, self.y + self.height + self.width * tan_a, self.fill_spacing):
                ctx.move_to(self.x, ysub)
                ctx.line_to(self.x + self.width, ysub - self.width / tan_a)
                ctx.stroke()
        elif self.fill_type == RectangleFillType.ANTI_DIAGONAL:
            # anti-diagonal hatch lines
            angle = np.radians(45)
            tan_a = np.tan(angle)
            for ysub in np.arange(self.y - self.width * tan_a, self.y + self.height, self.fill_spacing):
                ctx.move_to(self.x, ysub)
                ctx.line_to(self.x + self.width, ysub + self.width * tan_a)
                ctx.stroke()
        elif self.fill_type == RectangleFillType.CHECKER_DIAGONAL:
            # both diagonal and anti-diagonal lines
            angle = np.radians(45)
            tan_a = np.tan(angle)
            for ysub in np.arange(self.y, self.y + self.height + self.width * tan_a, self.fill_spacing):
                ctx.move_to(self.x, ysub)
                ctx.line_to(self.x + self.width, ysub - self.width / tan_a)
                ctx.stroke()
            for ysub in np.arange(self.y - self.width * tan_a, self.y + self.height, self.fill_spacing):
                ctx.move_to(self.x, ysub)
                ctx.line_to(self.x + self.width, ysub + self.width * tan_a)
                ctx.stroke()
        else:
            raise ValueError(f"Unknown fill type: {self.fill_type}")
        
        # restore context
        ctx.restore()

    def draw(self, ctx: TransformedContext):
        """
            Draws the rectangle with a hand-drawn-like style.
        """
        # Draw the fill pattern
        self._fill_hachure(ctx)

        # Draw the rectangle edges in sketchy style
        ctx.set_source_rgb(*self.stroke_color)
        ctx.set_line_width(self.stroke_width)

        x0, y0 = self.x, self.y
        x1, y1 = x0 + self.width, y0 + self.height

        self._draw_sketchy_line((x0, y0), (x1, y0), ctx)
        self._draw_sketchy_line((x1, y0), (x1, y1), ctx)
        self._draw_sketchy_line((x1, y1), (x0, y1), ctx)
        self._draw_sketchy_line((x0, y1), (x0, y0), ctx)

