from typing import List, Optional
import cairo
import numpy as np

from .base import BasePrimitive
from .lines import LinearPath
from ..stylings.styles import StrokeStyle, SketchStyle, FillStyle
from ..stylings.fillpatterns import get_filler


class Polygon(BasePrimitive):
    def __init__(
        self,
        points: List[tuple[float, float]],
        stroke_style: StrokeStyle = StrokeStyle(),
        fill_style: Optional[FillStyle] = None,
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

        if self.fill_style is not None:
            filler = get_filler([self.points], self.fill_style, self.sketch_style)
            filler.fill(ctx)


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


class NGon(Polygon):
    def __init__(
        self,
        center: tuple[float, float],
        radius: float,
        n: int,
        stroke_style: StrokeStyle = StrokeStyle(),
        fill_style: FillStyle = FillStyle(),
        sketch_style: SketchStyle = SketchStyle(),
    ):
        points = []
        center = np.array(center)
        for i in range(n):
            angle = 2 * np.pi * i / n
            point = center + radius * np.array([np.cos(angle), np.sin(angle)])
            points.append(point)
        super().__init__(points, stroke_style, fill_style, sketch_style)


class Square(Rectangle):
    def __init__(
        self,
        top_left: tuple[float, float],
        side_length: float,
        stroke_style: StrokeStyle = StrokeStyle(),
        fill_style: FillStyle = FillStyle(),
        sketch_style: SketchStyle = SketchStyle(),
    ):
        super().__init__(
            top_left, side_length, side_length, stroke_style, fill_style, sketch_style
        )
