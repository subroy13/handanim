from typing import List
import numpy as np

from ..core.drawable import Drawable
from ..core.draw_ops import OpsSet
from .lines import LinearPath
from ..stylings.fillpatterns import get_filler


class Polygon(Drawable):
    def __init__(
        self,
        points: List[tuple[float, float]],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.points = points

    def draw(self) -> OpsSet:
        """
        Draw a polygon with the given points
        """
        opsset = OpsSet()
        if len(self.points) < 3:
            raise ValueError("Polygon must have at least three points")
        linePath = LinearPath(
            self.points, self.stroke_style, self.sketch_style, close=True
        )
        opsset.extend(linePath.draw())  # always close the path for a polygon

        if self.fill_style is not None:
            filler = get_filler([self.points], self.fill_style, self.sketch_style)
            opsset.extend(filler.fill())
        return opsset


class Rectangle(Polygon):
    def __init__(
        self,
        top_left: tuple[float, float],
        width: float,
        height: float,
        *args,
        **kwargs,
    ):
        x, y = top_left
        super().__init__(
            [
                (x, y),
                (x + width, y),
                (x + width, y + height),
                (x, y + height),
            ],
            *args,
            **kwargs,
        )


class NGon(Polygon):
    def __init__(
        self,
        center: tuple[float, float],
        radius: float,
        n: int,
        *args,
        **kwargs,
    ):
        points = []
        center = np.array(center)
        for i in range(n):
            angle = 2 * np.pi * i / n
            point = center + radius * np.array([np.cos(angle), np.sin(angle)])
            points.append(point)
        super().__init__(points, *args, **kwargs)


class Square(Rectangle):
    def __init__(
        self,
        top_left: tuple[float, float],
        side_length: float,
        *args,
        **kwargs,
    ):
        super().__init__(top_left, side_length, side_length, *args, **kwargs)
