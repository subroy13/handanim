import numpy as np
import cairo
from .base import BasePrimitive
from ..constants import RoughOptions


class Ellipse(BasePrimitive):
    def __init__(
        self,
        center: tuple[float, float],
        width: float,
        height: float,
        stroke_color: tuple[float, float, float] = (0, 0, 0),
        stroke_width: float = 1,
        stroke_opacity: float = 1,
        options: RoughOptions = RoughOptions(),
    ):
        self.center = np.array(center)
        self.width = width
        self.height = height
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.stroke_opacity = stroke_opacity
        self.options = options

    def _get_ellipse_params(
        self,
        width: float,
        height: float,
    ):
        """
        Get the number of points to approximate this ellipse with,
        and approximated radius with random variation
        """
        perimeter = np.sqrt(2 * np.pi * np.sqrt((width / 2) ** 2 + (height / 2) ** 2))
        step_count = np.ceil(
            self.options.curve_step_count * max(1, perimeter / np.sqrt(200))
        )
        increment = 2 * np.pi / step_count
        rx = width / 2
        ry = height / 2
        curve_fit_randomness = 1 - self.options.curve_fitting
        rx += (
            np.random.uniform(low=-1, high=1)
            * rx
            * curve_fit_randomness
            * self.options.roughness
        )
        ry += (
            np.random.uniform(low=-1, high=1)
            * ry
            * curve_fit_randomness
            * self.options.roughness
        )
        return rx, ry, increment

    def _compute_ellipse_points(
        increment: float,
        center: np.ndarray,
        rx: float,
        ry: float,
        offset: float,
        overlap: float,
        roughness: float = 0,
    ):
        """
        Compute the points of an ellipse
        """
        core_only = roughness == 0
        rad = np.array([rx, ry])
        core_points = []
        all_points = []

        get_ellipse_arc = lambda a: np.array([np.cos(a), np.sin(a)])

        if core_only:
            # compute only the core points
            increment = increment / 4  # compute the core points with greater precision
            all_points.append(center + rad * get_ellipse_arc(-increment))
            for a in np.arange(0, 2 * np.pi + increment, increment):
                p = center + rad * get_ellipse_arc(a)
                core_points.append(p)
                all_points.append(p)
            all_points.append(center + rad * get_ellipse_arc(increment))
        else:
            random_offset = np.random.uniform(low=-1, high=1) * roughness - np.pi / 2
            all_points.append(
                center
                + 0.9 * rad * get_ellipse_arc(random_offset - increment)
                + np.random.uniform(low=-1, high=1, size=2) * offset * roughness
            )
            end_angle = 2 * np.pi + random_offset - 0.01
            for a in np.arange(random_offset, end_angle + increment, increment):
                p = (
                    center
                    + rad * get_ellipse_arc(a)
                    + np.random.uniform(low=-1, high=1, size=2) * offset * roughness
                )
                core_points.append(p)
                all_points.append(p)

            # add enbding points for the curve, with overlaping points
            temp_points = (
                np.tile(center, 3)
                + np.random.uniform(low=-1, high=1, size=6) * offset * roughness
            )

            all_points.append(
                temp_points[0:2]
                + rad * get_ellipse_arc(random_offset + 2 * np.pi + overlap * 0.5)
            )
            all_points.append(
                temp_points[2:4] + 0.98 * rad * get_ellipse_arc(random_offset + overlap)
            )
            all_points.append(
                temp_points[4:6]
                + 0.9 * rad * get_ellipse_arc(random_offset + overlap * 0.5)
            )

        return core_points, all_points

    def draw(self, ctx: cairo.Context):
        """
        Draw a sketchy version of an ellipse
        """
        ctx.save()  # save the current state of the context

        # set stroke color and width
        r, g, b = self.stroke_color
        ctx.set_source_rgba(r, g, b, self.stroke_opacity)
        ctx.set_line_width(self.stroke_width)

        # compute the ellipse parameters
        rx, ry, increment = self._get_ellipse_params(self.width, self.height)
        ap1, cp1 = self._compute_ellipse_points(
            increment,
            self.center,
            rx,
            ry,
            1,
            increment
            + np.random.uniform(low=0.1, high=np.random.uniform(low=0.4, high=1))
            * self.options.roughness,
            self.options.roughness,
        )

        # TODO: create curve

        # draw for the second time for sketchy effect
        ap2, _ = self._compute_ellipse_points(
            increment,
            self.center,
            rx,
            ry,
            1.5,
            0,
            self.options.roughness,
        )

        # TODO: create curve again

        # TODO?? Return Path??

        ctx.restore()  # restore the previous state of the context
