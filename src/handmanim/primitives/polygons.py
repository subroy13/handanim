from typing import List
import cairo

from .base import BasePrimitive
from .lines import Line
from ..constants import RoughOptions


class LinearPath(BasePrimitive):
    def __init__(
        self,
        points: List[tuple[float, float]],
        stroke_color: tuple[float, float, float] = (0, 0, 0),
        stroke_width: float = 1,
        stroke_opacity: float = 1,
        options: RoughOptions = RoughOptions(),
    ):
        self.points = points
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.stroke_opacity = stroke_opacity
        self.options = options

    def draw(self, ctx: cairo.Context, close: bool = False):
        if self.points is None or len(self.points) < 2:
            raise ValueError("LinearPath must have at least two points")
        for i in range(len(self.points) - 1):
            start = self.points[i]
            end = self.points[i + 1]
            line = Line(
                start,
                end,
                self.stroke_color,
                self.stroke_width,
                self.stroke_opacity,
                self.options,
            )
            line.draw(ctx)
        if len(self.points) > 2 and close:
            # do the closing line
            start = self.points[-1]
            end = self.points[0]
            line = Line(
                start,
                end,
                self.stroke_color,
                self.stroke_width,
                self.stroke_opacity,
                self.options,
            )
            line.draw(ctx)


class Polygon(BasePrimitive):
    def __init__(
        self,
        points: List[tuple[float, float]],
        stroke_color: tuple[float, float, float] = (0, 0, 0),
        stroke_width: float = 1,
        stroke_opacity: float = 1,
        options: RoughOptions = RoughOptions(),
    ):
        self.points = points
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.stroke_opacity = stroke_opacity
        self.options = options

    def draw(self, ctx: cairo.Context):
        """
        Draw a polygon with the given points
        """
        if len(self.points) < 3:
            raise ValueError("Polygon must have at least three points")
        linePath = LinearPath(
            self.points,
            self.stroke_color,
            self.stroke_width,
            self.stroke_opacity,
            self.options,
        )
        linePath.draw(ctx, close=True)  # always close the path for a polygon


class Rectangle(Polygon):
    def __init__(
        self,
        top_left: tuple[float, float],
        width: float,
        height: float,
        stroke_color: tuple[float, float, float] = (0, 0, 0),
        stroke_width: float = 1,
        stroke_opacity: float = 1,
        options: RoughOptions = RoughOptions(),
    ):
        x, y = top_left
        super().__init__(
            [
                (x, y),
                (x + width, y),
                (x + width, y + height),
                (x, y + height),
            ],
            stroke_color,
            stroke_width,
            stroke_opacity,
            options,
        )
