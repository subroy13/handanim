from typing import List, Tuple, Optional
import numpy as np
import cairo
from .base import BasePrimitive
from .lines import Line
from ..constants import RoughOptions


class Curve(BasePrimitive):

    def __init__(
        self,
        points: List[Tuple[float, float]],  # the list of points that defines the curve
        close_point: Optional[
            Tuple[float, float]
        ] = None,  # the point to close the curve with
        stroke_color: Tuple[float, float, float] = (0, 0, 0),
        stroke_width: float = 1,
        stroke_opacity: float = 1,
        options: RoughOptions = RoughOptions(),
    ):
        self.points = [np.array(point) for point in points]
        self.close_point = np.array(close_point) if close_point is not None else None
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.stroke_opacity = stroke_opacity
        self.options = options

    def draw_single_curve(self, ctx: cairo.Context):
        """
        Draws a single human style sketchy curve
        """
        if len(self.points) < 2:
            raise ValueError("Curve must have at least two points")
        elif len(self.points) == 2:
            # draw a line
            line = Line(
                self.points[0],
                self.points[1],
                self.stroke_color,
                self.stroke_width,
                self.stroke_opacity,
                self.options,
            )
            line.draw_single_line(ctx, move=True, overlay=True)
        elif len(self.points) == 3:
            ctx.move_to(*self.points[0])
            ctx.curve_to(
                *self.points[1], *self.points[2], *self.points[2]
            )  # draw an approximate quad curve
            ctx.stroke()
        else:
            # there are more points
            s = 1 - self.options.curve_tightness
            ctx.move_to(*self.points[0])  # move to the first point

            for i in range(1, len(self.points) - 2):
                b0 = self.points[i]
                b1 = b0 + s * (self.points[i + 1] - self.points[i - 1]) / 6
                b2 = self.points[i + 1] + s * (self.points[i] - self.points[i + 2]) / 6
                b3 = self.points[i + 1]
                ctx.curve_to(*b1, *b2, *b3)

            # check for closing points
            if self.close_point is not None:
                ro = self.options.max_random_offset
                ctx.line_to(
                    *(
                        self.close_point
                        + np.random.uniform(-ro, ro, size=(2,)) * self.options.roughness
                    )
                )
            ctx.stroke()

    def draw(self, ctx: cairo.Context):
        """
        Draw the curve
        """
        pass
