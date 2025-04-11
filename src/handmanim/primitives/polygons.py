from typing import List
import cairo

from .base import BasePrimitive
from .lines import LinearPath
from ..stylings.styles import StrokeStyle, SketchStyle, FillStyle


class Polygon(BasePrimitive):
    def __init__(
        self,
        points: List[tuple[float, float]],
        stroke_style: StrokeStyle = StrokeStyle(),
        fill_style: FillStyle = FillStyle(),
        sketch_style: SketchStyle = SketchStyle(),
    ):
        self.points = points
        self.stroke_style = stroke_style
        self.fill_style = fill_style
        self.sketch_style = sketch_style

    def draw(self, ctx: cairo.Context):
        """
        Draw a polygon with the given points
        """
        if len(self.points) < 3:
            raise ValueError("Polygon must have at least three points")
        linePath = LinearPath(self.points, self.stroke_style, self.sketch_style)
        linePath.draw(ctx, close=True)  # always close the path for a polygon


class Rectangle(Polygon):
    def __init__(
        self,
        top_left: tuple[float, float],
        width: float,
        height: float,
        stroke_style: StrokeStyle = StrokeStyle(),
        fill_style: FillStyle = FillStyle(),
        sketch_style: SketchStyle = SketchStyle(),
    ):
        x, y = top_left
        super().__init__(
            [
                (x, y),
                (x + width, y),
                (x + width, y + height),
                (x, y + height),
            ],
            stroke_style,
            fill_style,
            sketch_style,
        )
