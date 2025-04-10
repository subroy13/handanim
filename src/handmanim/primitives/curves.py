from typing import List, Tuple, Optional, Union
import numpy as np
import cairo
from .base import BasePrimitive
from .lines import Line
from ..constants import RoughOptions


class Curve(BasePrimitive):

    def __init__(
        self,
        points: List[Tuple[float, float]],  # the list of points that defines the curve
        stroke_color: Tuple[float, float, float] = (0, 0, 0),
        stroke_width: float = 1,
        stroke_opacity: float = 1,
        options: RoughOptions = RoughOptions(),
    ):
        self.points = [np.array(point) for point in points]
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.stroke_opacity = stroke_opacity
        self.options = options

    def draw_single_curve(
        self,
        ctx: cairo.Context,
        points: Optional[List[np.ndarray]] = None,
        close_point: Optional[Union[tuple[float, float], np.ndarray]] = None,
    ):
        """
        Draws a single human style sketchy curve
        """
        if points is None:
            points = self.points
        if close_point is not None and isinstance(close_point, tuple):
            close_point = np.array(close_point)
        if len(points) < 2:
            raise ValueError("Curve must have at least two points")
        elif len(points) == 2:
            # draw a line
            line = Line(
                points[0],
                points[1],
                self.stroke_color,
                self.stroke_width,
                self.stroke_opacity,
                self.options,
            )
            line.draw_single_line(ctx, move=True, overlay=True)
        elif len(points) == 3:
            ctx.move_to(*points[0])
            ctx.curve_to(
                *points[1], *points[2], *points[2]
            )  # draw an approximate quad curve
            ctx.stroke()
        else:
            # there are more points, handle accordingly
            s = 1 - self.options.curve_tightness
            ctx.move_to(*points[0])  # move to the first point
            for i in range(1, len(points) - 2):
                b0 = points[i]
                b1 = b0 + s * (points[i + 1] - points[i - 1]) / 6
                b2 = points[i + 1] + s * (points[i] - points[i + 2]) / 6
                b3 = points[i + 1]
                ctx.curve_to(*b1, *b2, *b3)

            # check for closing points
            if close_point is not None:
                ro = self.options.max_random_offset
                ctx.line_to(
                    *(
                        close_point
                        + np.random.uniform(-ro, ro, size=(2,)) * self.options.roughness
                    )
                )
            ctx.stroke()

    def draw_single_curve_with_randomization(
        self,
        ctx: cairo.Context,
        points: Optional[List[np.ndarray]] = None,
        offset: float = 1.0,
    ):
        """
        Draw a single human style sketchy curve with random derivations
        """
        if points is None:
            points = self.points
        # add the start and end point twice with random offsets
        random_offsets = (
            np.random.uniform(-offset, offset, size=(len(points) + 2, 2))
            * self.options.roughness
        )
        new_points = [points[0] + random_offsets[0, :]]
        for i, point in enumerate(points):
            new_points.append(point + random_offsets[(i + 1), :])
        new_points.append(points[-1] + random_offsets[-1, :])
        self.draw_single_curve(ctx, new_points)

    def draw(self, ctx: cairo.Context):
        """
        Draw the curve
        """
        ctx.save()  # save the current state of the context

        # Set stroke color and width
        r, g, b = self.stroke_color
        ctx.set_source_rgba(r, g, b, self.stroke_opacity)
        ctx.set_line_width(self.stroke_width)

        # draw the underlay and overlay curves
        self.draw_single_curve_with_randomization(
            ctx, self.points, 1 + self.options.roughness * 0.2
        )
        if not self.options.disable_multi_stroke:
            self.draw_single_curve_with_randomization(
                ctx, self.points, 1.5 * (1 + self.options.roughness * 0.22)
            )

        # restore the context to its previous state
        ctx.restore()
