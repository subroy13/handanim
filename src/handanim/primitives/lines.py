from typing import List, Tuple
import numpy as np

from ..core.styles import StrokePressure
from ..core.draw_ops import OpsSet, Ops, OpsType
from ..core.drawable import Drawable
from ..stylings.strokes import apply_stroke_pressure


class Line(Drawable):
    """
    A drawable line primitive that generates hand-drawn style lines with randomized jitter and bowing effects.

    Supports customizable stroke and sketch styles, with options for line curvature, roughness,
    and multiple line passes to create a hand-drawn appearance. Allows for optional stroke pressure
    variations and provides methods to draw single or overlapping lines.

    Attributes:
        start (np.ndarray): Starting point coordinates of the line
        end (np.ndarray): Ending point coordinates of the line
    """

    def __init__(
        self, start: tuple[float, float], end: tuple[float, float], *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.start = np.array(start)
        self.end = np.array(end)

    def draw_single_line(
        self,
        opsset: OpsSet,
        move: bool = False,  # should we move to the specific position before drawing?
        overlay: bool = False,  # is this the second pass?
    ) -> OpsSet:
        length = np.linalg.norm(
            self.end - self.start
        )  # get the length of the line segment
        roughness_gain = np.clip(
            -0.0016668 * length + 1.233334, 0.4, 1
        )  # calculate roughness gain (dampending factor)
        offset = min(length / 10, self.sketch_style.max_random_offset)

        # get the divergence point for bowing effect
        diverge_point = np.random.uniform(low=0.2, high=0.4)
        mid_disp = self.sketch_style.bowing * offset * (self.end - self.start) / 200
        mid_disp = np.array([mid_disp[1], mid_disp[0]])  # this is normal to the line

        # random generator functions
        random_jitter = (
            lambda x: np.random.uniform(low=-offset, high=offset, size=(x,))
            * roughness_gain
            * self.sketch_style.roughness
        )
        jitter_scale = 0.5 if overlay else 1

        # draw the curved lines, based on move and overlay
        if move:
            opsset.add(
                Ops(
                    OpsType.MOVE_TO, data=[self.start + random_jitter(2) * jitter_scale]
                )
            )

        opsset.add(
            Ops(
                OpsType.CURVE_TO,
                data=[
                    mid_disp
                    + self.start
                    + (self.end - self.start) * diverge_point
                    + random_jitter(2) * jitter_scale,
                    mid_disp
                    + self.start
                    + 2 * (self.end - self.start) * diverge_point
                    + random_jitter(2) * jitter_scale,
                    self.end + random_jitter(2) * jitter_scale,
                ],
            )
        )
        return opsset

    def draw(self) -> OpsSet:
        """
        Draws a hand-drawn-like line with some jitter.
        """
        opsset = OpsSet(initial_set=[])
        opsset.add(
            Ops(
                OpsType.SET_PEN,
                {
                    "color": self.stroke_style.color,
                    "width": self.stroke_style.width,
                    "opacity": self.stroke_style.opacity,
                },
            )
        )

        # draw the sketchy lines
        opsset = self.draw_single_line(opsset, move=True, overlay=False)
        opsset = self.draw_single_line(opsset, move=True, overlay=True)

        # apply stroke pressure if available
        if self.stroke_style.stroke_pressure != StrokePressure.CONSTANT:
            opsset = apply_stroke_pressure(opsset, self.stroke_style.stroke_pressure)

        return opsset


class LinearPath(Drawable):
    """
    A drawable linear path that connects a series of points, with optional closing of the path.

    Attributes:
        points (List[tuple[float, float]]): A list of (x, y) coordinate points defining the path.
        close (bool, optional): Whether to connect the last point back to the first point. Defaults to False.

    Raises:
        ValueError: If fewer than two points are provided.

    The path is drawn by creating Line objects between consecutive points,
    with optional path closure if specified.
    """

    def __init__(
        self,
        points: List[tuple[float, float]],
        close: bool = False,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.points = points
        self.close = close

    def draw(self) -> OpsSet:
        if self.points is None or len(self.points) < 2:
            raise ValueError("LinearPath must have at least two points")
        opsset = OpsSet(initial_set=[])
        for i in range(len(self.points) - 1):
            start = self.points[i]
            end = self.points[i + 1]
            line = Line(
                start,
                end,
                self.stroke_style,
                self.sketch_style,
            )
            opsset.extend(line.draw())

        if len(self.points) > 2 and self.close:
            # do the closing line
            start = self.points[-1]
            end = self.points[0]
            line = Line(
                start,
                end,
                self.stroke_style,
                self.sketch_style,
            )
            opsset.extend(line.draw())
        return opsset


class Arrow(Drawable):

    def __init__(
        self,
        start_point: Tuple[float, float],
        end_point: Tuple[float, float],
        arrow_head_type: str = "->",  # valid values are: ->, ->>, -|>
        arrow_head_size: float = 10.0,
        arrow_head_angle: float = 45.0,
        *args,
        **kwargs
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
        angle = np.arctan((self.end[1] - self.start[1])/(self.end[0] - self.start[0]) )
        arrow_head_angle = np.deg2rad(self.arrow_head_angle)
        arrow_line1 = LinearPath(
            points = [
                self.start,
                [self.end[0], self.start[1]], # we will rotate later
                [
                    self.end[0] - np.cos(arrow_head_angle) * self.arrow_head_size, 
                    self.start[1] - np.sin(arrow_head_angle) * self.arrow_head_size
                ]
            ],
            *self.args,
            **self.kwargs
        )
        opsset.extend(arrow_line1.draw())
        opsset.add(Ops(
            type=OpsType.MOVE_TO,
            data=[[self.end[0], self.start[1]]]
        ))
        arrow_line2 = Line(
            start=(self.end[0], self.start[1]),
            end=[
                    self.end[0] - np.cos(arrow_head_angle) * self.arrow_head_size, 
                    self.start[1] + np.sin(arrow_head_angle) * self.arrow_head_size
                ]
        )
        opsset.extend(arrow_line2.draw())

        # check for arrow_head type now
        if self.arrow_head_type == "->>":
            for arrow_scale in [-1, 1]:
                opsset.add(Ops(
                    type=OpsType.MOVE_TO,
                    data=[(self.end[0] - self.arrow_head_size / 2, self.start[1])]
                ))
                arrow_line3 = Line(
                    start=(self.end[0] - self.arrow_head_size / 2, self.start[1]),
                    end=[
                        self.end[0] - self.arrow_head_size / 2 - np.cos(arrow_head_angle) * self.arrow_head_size, 
                        self.start[1] + arrow_scale * np.sin(arrow_head_angle) * self.arrow_head_size
                    ]
                )
                opsset.extend(arrow_line3.draw())
        elif self.arrow_head_size == "-|>":
            for arrow_scale in [-1, 1]:
                start_point = [
                    self.end[0] - np.cos(arrow_head_angle) * self.arrow_head_size, 
                    self.start[1] + arrow_scale * np.sin(arrow_head_angle) * self.arrow_head_size
                ]
                opsset.add(Ops(
                    type=OpsType.MOVE_TO,
                    data=[start_point]
                ))
                arrow_line3 = Line(
                    start=start_point,
                    end=(self.end[0] - self.arrow_head_size / 2, self.start[1])
                )
                opsset.extend(arrow_line3.draw())
        
        opsset.rotate(np.rad2deg(angle), center_of_rotation=self.start)
        return opsset