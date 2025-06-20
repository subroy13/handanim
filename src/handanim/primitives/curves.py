from typing import List, Tuple, Optional, Union
import numpy as np
from .lines import Line
from ..core.draw_ops import OpsSet, Ops, OpsType
from ..core.drawable import Drawable
from ..core.utils import get_line_slope_angle


class Curve(Drawable):
    """
    A class representing a curve that can be drawn with a sketchy, hand-drawn style.

    Allows creating curves with multiple points, supporting various drawing techniques
    including single line, quadratic, and more complex multi-point curves with
    randomization to simulate hand-drawn appearance.

    Attributes:
        points (List[np.ndarray]): List of points defining the curve's shape.
    """

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


class CurvedArrow(Drawable):

    def __init__(
        self,
        points: List[Tuple[float, float]],  # the list of points that defines the curve
        arrow_head_type: str = "->",  # valid values are: ->, ->>, -|>
        arrow_head_size: float = 10.0,
        arrow_head_angle: float = 45.0,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.args = args
        self.kwargs = kwargs
        self.points = points
        self.arrow_head_type = arrow_head_type
        self.arrow_head_size = arrow_head_size
        self.arrow_head_angle = arrow_head_angle

    def draw(self) -> OpsSet:
        opsset = OpsSet(initial_set=[])

        # get the arrow head angle from last two points
        if len(self.points) < 2:
            raise ValueError("CurvedArrow must have at least two points")

        end_point = self.points[-1]
        angle = get_line_slope_angle(self.points[-2], end_point)
        arrow_head_angle = np.deg2rad(self.arrow_head_angle)
        rotation_values = [np.cos(-angle), np.sin(-angle)]

        # do negative rotation for the points
        rotated_points = [
            (
                end_point[0]
                + rotation_values[0] * (x - end_point[0])
                - rotation_values[1] * (y - end_point[1]),
                end_point[1]
                + rotation_values[1] * (x - end_point[0])
                + rotation_values[0] * (y - end_point[1]),
            )
            for x, y in self.points
        ]

        # draw the curve
        curve = Curve(rotated_points, *self.args, **self.kwargs)
        opsset.extend(curve.draw())

        # draw the arrow head
        for arrow_scale in [-1, 1]:
            arrow_line = Line(
                start=end_point,
                end=(
                    end_point[0] - np.cos(arrow_head_angle) * self.arrow_head_size,
                    end_point[1]
                    + arrow_scale * np.sin(arrow_head_angle) * self.arrow_head_size,
                ),
                *self.args,
                **self.kwargs,
            )
            opsset.extend(arrow_line.draw())
            opsset.add(
                Ops(OpsType.MOVE_TO, data=[end_point])
            )  # move to the end point again

        # check for the arrow head type
        if self.arrow_head_type == "->>":
            for arrow_scale in [-1, 1]:
                arrow_line = Line(
                    start=(end_point[0] - self.arrow_head_size / 2, end_point[1]),
                    end=(
                        end_point[0]
                        - self.arrow_head_size / 2
                        - np.cos(arrow_head_angle) * self.arrow_head_size,
                        end_point[1]
                        + arrow_scale * np.sin(arrow_head_angle) * self.arrow_head_size,
                    ),
                    *self.args,
                    **self.kwargs,
                )
                opsset.extend(arrow_line.draw())
                opsset.add(
                    Ops(OpsType.MOVE_TO, data=[end_point])
                )  # move to the end point again

        elif self.arrow_head_type == "-|>":
            for arrow_scale in [-1, 1]:
                arrow_line = Line(
                    start=(end_point[0] - self.arrow_head_size / 2, end_point[1]),
                    end=(
                        end_point[0] - np.cos(arrow_head_angle) * self.arrow_head_size,
                        end_point[1]
                        + arrow_scale * np.sin(arrow_head_angle) * self.arrow_head_size,
                    ),
                    *self.args,
                    **self.kwargs,
                )
                opsset.extend(arrow_line.draw())
                opsset.add(
                    Ops(OpsType.MOVE_TO, data=[end_point])
                )  # move to the end point again

        # finally, rotate the opset back to the original angle
        opsset.rotate(np.rad2deg(angle), center_of_rotation=end_point)
        return opsset
