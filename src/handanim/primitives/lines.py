from typing import List
import numpy as np

from ..core.draw_ops import OpsSet, Ops, OpsType
from ..core.drawable import Drawable


class Line(Drawable):
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

    def draw(self) -> OpsSet:
        """
        Draws a hand-drawn-like line with some jitter.
        """
        opsset = OpsSet()
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
        return opsset


class LinearPath(Drawable):
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
        opsset = OpsSet()
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
