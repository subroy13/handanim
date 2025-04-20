from typing import List, Tuple, Optional, Union
import numpy as np
from .lines import Line
from ..core.draw_ops import OpsSet, Ops, OpsType
from ..core.drawable import Drawable


class Curve(Drawable):

    def __init__(
        self,
        points: List[Tuple[float, float]],  # the list of points that defines the curve
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.points = [np.array(point) for point in points]

    def draw_single_curve(
        self,
        opsset: OpsSet,
        points: Optional[List[np.ndarray]] = None,
        close_point: Optional[Union[tuple[float, float], np.ndarray]] = None,
    ) -> OpsSet:
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
                stroke_style=self.stroke_style,
                sketch_style=self.sketch_style,
            )
            opsset = line.draw_single_line(opsset, move=True, overlay=True)
        elif len(points) == 3:
            opsset.add(Ops(OpsType.MOVE_TO, data=[points[0]]))
            opsset.add(Ops(OpsType.CURVE_TO, data=[points[1], points[2], points[2]]))
        else:
            # there are more points, handle accordingly
            s = 1 - self.sketch_style.curve_tightness
            opsset.add(Ops(OpsType.MOVE_TO, data=[points[0]]))
            for i in range(1, len(points) - 2):
                b0 = points[i]
                b1 = b0 + s * (points[i + 1] - points[i - 1]) / 6
                b2 = points[i + 1] + s * (points[i] - points[i + 2]) / 6
                b3 = points[i + 1]
                opsset.add(Ops(OpsType.CURVE_TO, data=[b1, b2, b3]))

            # check for closing points
            if close_point is not None:
                ro = self.sketch_style.max_random_offset
                opsset.add(
                    Ops(
                        OpsType.LINE_TO,
                        data=[
                            close_point
                            + np.random.uniform(-ro, ro, size=(2,))
                            + self.sketch_style.roughness
                        ],
                    )
                )
        return opsset

    def draw_single_curve_with_randomization(
        self,
        opsset: OpsSet,
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
            * self.sketch_style.roughness
        )
        new_points = [points[0] + random_offsets[0, :]]
        for i, point in enumerate(points):
            new_points.append(point + random_offsets[(i + 1), :])
        new_points.append(points[-1] + random_offsets[-1, :])
        return self.draw_single_curve(opsset, new_points)

    def draw(self) -> OpsSet:
        """
        Draw the curve
        """
        opsset = OpsSet()
        opsset.add(
            Ops(
                OpsType.SET_PEN,
                data={
                    "color": self.stroke_style.color,
                    "width": self.stroke_style.width,
                    "opacity": self.stroke_style.opacity,
                },
            )
        )

        # draw the underlay and overlay curves
        opsset = self.draw_single_curve_with_randomization(
            opsset, self.points, 1 + self.sketch_style.roughness * 0.2
        )
        if not self.sketch_style.disable_multi_stroke:
            opsset = self.draw_single_curve_with_randomization(
                opsset, self.points, 1.5 * (1 + self.sketch_style.roughness * 0.22)
            )
        return opsset
