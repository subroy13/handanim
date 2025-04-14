from typing import Tuple
import numpy as np

from .curves import Curve
from ..core.drawable import Drawable
from ..core.draw_ops import OpsSet, Ops, OpsType
from ..stylings.fillpatterns import get_filler


class Ellipse(Drawable):
    def __init__(
        self,
        center: Tuple[float, float],
        width: float,
        height: float,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.center = np.array(center)
        self.width = width
        self.height = height

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
            self.sketch_style.curve_step_count * max(1, perimeter / np.sqrt(200))
        )
        increment = 2 * np.pi / step_count
        rx = width / 2
        ry = height / 2
        curve_fit_randomness = 1 - self.sketch_style.curve_fitting
        rx += (
            np.random.uniform(low=-1, high=1)
            * rx
            * curve_fit_randomness
            * self.sketch_style.roughness
        )
        ry += (
            np.random.uniform(low=-1, high=1)
            * ry
            * curve_fit_randomness
            * self.sketch_style.roughness
        )
        return rx, ry, increment

    def _compute_ellipse_points(
        self,
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

    def draw_ellipse_border(self, opsset: OpsSet) -> Tuple[list, OpsSet]:
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
            * self.sketch_style.roughness,
            self.sketch_style.roughness,
        )

        # create the first ellipse stroke
        curve1 = Curve(
            points=ap1,
            stroke_style=self.stroke_style,
            sketch_style=self.sketch_style,
        )
        opsset = curve1.draw_single_curve(opsset)

        if (
            not self.sketch_style.disable_multi_stroke
            and self.sketch_style.roughness > 0
        ):
            # draw for the second time for sketchy effect
            ap2, _ = self._compute_ellipse_points(
                increment,
                self.center,
                rx,
                ry,
                1.5,
                0,
                self.sketch_style.roughness,
            )
            curve2 = Curve(
                points=ap2,
                stroke_style=self.stroke_style,
                sketch_style=self.sketch_style,
            )
            opsset = curve2.draw_single_curve(opsset)

        return cp1, opsset

    def draw(self) -> OpsSet:
        """
        Draw a sketchy version of an ellipse
        """
        opsset = OpsSet(
            [
                Ops(
                    OpsType.SET_PEN,
                    data={
                        "color": self.stroke_style.color,
                        "width": self.stroke_style.width,
                        "opacity": self.stroke_style.opacity,
                    },
                )
            ]
        )

        core_points, opsset = self.draw_ellipse_border(
            opsset
        )  # draw the ellipse border

        if self.fill_style is not None:
            filler = get_filler([core_points], self.fill_style, self.sketch_style)
            opsset.extend(filler.fill())


class Circle(Ellipse):
    def __init__(
        self,
        center: tuple[float, float],
        radius: float,
        *args,
        **kwargs,
    ):
        super().__init__(
            center,
            2 * radius,
            2 * radius,
            *args,
            **kwargs,
        )
