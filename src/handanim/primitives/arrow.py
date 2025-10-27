from typing import Tuple, List
import numpy as np

from ..core.draw_ops import OpsSet, Ops, OpsType
from ..core.drawable import Drawable
from ..core.utils import get_line_slope_angle
from .lines import Line, LinearPath
from .curves import Curve

class Arrow(Drawable):

    def __init__(
        self,
        start_point: Tuple[float, float],
        end_point: Tuple[float, float],
        arrow_head_type: str = "->",  # valid values are: ->, ->>, -|>
        arrow_head_size: float = 10.0,
        arrow_head_angle: float = 45.0,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.args = args
        self.kwargs = kwargs
        self.start = start_point
        self.end = end_point
        self.arrow_head_type = arrow_head_type
        self.arrow_head_size = arrow_head_size
        self.arrow_head_angle = arrow_head_angle

    def draw(self):
        opsset = OpsSet(initial_set=[])
        angle = get_line_slope_angle(self.start, self.end)
        arrow_head_angle = np.deg2rad(self.arrow_head_angle)
        arrow_line1 = LinearPath(
            points=[
                self.start,
                (self.end[0], self.start[1]),  # we will rotate later
                (
                    self.end[0] - np.cos(arrow_head_angle) * self.arrow_head_size,
                    self.start[1] - np.sin(arrow_head_angle) * self.arrow_head_size,
                ),
            ],
            *self.args,
            **self.kwargs,
        )
        opsset.extend(arrow_line1.draw())
        opsset.add(Ops(type=OpsType.MOVE_TO, data=[[self.end[0], self.start[1]]]))
        arrow_line2 = Line(
            start=(self.end[0], self.start[1]),
            end=(
                self.end[0] - np.cos(arrow_head_angle) * self.arrow_head_size,
                self.start[1] + np.sin(arrow_head_angle) * self.arrow_head_size,
            ),
        )
        opsset.extend(arrow_line2.draw())

        # check for arrow_head type now
        if self.arrow_head_type == "->>":
            for arrow_scale in [-1, 1]:
                opsset.add(
                    Ops(
                        type=OpsType.MOVE_TO,
                        data=[(self.end[0] - self.arrow_head_size / 2, self.start[1])],
                    )
                )
                arrow_line3 = Line(
                    start=(self.end[0] - self.arrow_head_size / 2, self.start[1]),
                    end=(
                        self.end[0]
                        - self.arrow_head_size / 2
                        - np.cos(arrow_head_angle) * self.arrow_head_size,
                        self.start[1]
                        + arrow_scale * np.sin(arrow_head_angle) * self.arrow_head_size,
                    ),
                )
                opsset.extend(arrow_line3.draw())
        elif self.arrow_head_size == "-|>":
            for arrow_scale in [-1, 1]:
                start_point = (
                    self.end[0] - np.cos(arrow_head_angle) * self.arrow_head_size,
                    self.start[1]
                    + arrow_scale * np.sin(arrow_head_angle) * self.arrow_head_size,
                )
                opsset.add(Ops(type=OpsType.MOVE_TO, data=[start_point]))
                arrow_line3 = Line(
                    start=start_point,
                    end=(self.end[0] - self.arrow_head_size / 2, self.start[1]),
                )
                opsset.extend(arrow_line3.draw())

        opsset.rotate(np.rad2deg(angle), center_of_rotation=self.start)
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
