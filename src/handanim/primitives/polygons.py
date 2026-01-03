from typing import List
import numpy as np

from ..core.drawable import Drawable
from ..core.draw_ops import OpsSet, Ops, OpsType
from .lines import LinearPath
from .curves import Curve
from ..stylings.fillpatterns import get_filler


class Polygon(Drawable):
    """
    A Polygon class representing a drawable polygon shape.

    This class allows creating polygons with a list of points, drawing them with optional
    stroke and fill styles. It ensures the polygon has at least three points and can
    render the polygon using a closed linear path with optional filling.

    Attributes:
        points (List[tuple[float, float]]): A list of (x, y) coordinates defining the polygon vertices.

    Raises:
        ValueError: If fewer than three points are provided.
    """

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
        opsset = OpsSet(initial_set=[])
        if len(self.points) < 3:
            raise ValueError("Polygon must have at least three points")
        linePath = LinearPath(
            self.points,
            close=True,
            stroke_style=self.stroke_style,
            sketch_style=self.sketch_style,
        )
        opsset.extend(linePath.draw())  # always close the path for a polygon

        if self.fill_style is not None:
            opsset.add(Ops(type=OpsType.METADATA, data={"drawing_mode": "fill"}))
            filler = get_filler([self.points], self.fill_style, self.sketch_style)
            opsset.extend(filler.fill())
        return opsset


class Rectangle(Polygon):
    """
    A Rectangle class representing a rectangular polygon shape.

    This class creates a rectangle by specifying its top-left corner coordinates,
    width, and height. It inherits from the Polygon class and generates the four
    vertices of the rectangle automatically.

    Args:
        top_left (tuple[float, float]): Coordinates of the top-left corner of the rectangle.
        width (float): Width of the rectangle.
        height (float): Height of the rectangle.
    """

    def __init__(
        self,
        top_left: tuple[float, float],
        width: float,
        height: float,
        *args,
        **kwargs,
    ):
        x, y = top_left
        self.top_left = top_left
        self.width = width
        self.height = height
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
        self.side_length = side_length
        super().__init__(top_left, side_length, side_length, *args, **kwargs)


class RoundedRectangle(Drawable):

    def __init__(
        self,
        top_left: tuple[float, float],
        width: float,
        height: float,
        border_radius: float = 0.1,  # this is a percentage of the rectangle height or width
        *args,
        **kwargs,
    ):
        self.top_left = top_left
        self.width = width
        self.height = height
        self.border_radius = border_radius
        self.args = args
        self.kwargs = kwargs
        super().__init__(*args, **kwargs)
        
    def draw(self) -> OpsSet:
        opsset = OpsSet(initial_set=[])
        x, y = self.top_left
        border_radius = self.border_radius * min(self.width, self.height)
        points = [
            (x + border_radius, y),
            (x + self.width - border_radius, y),
            (x + self.width, y + border_radius),
            (x + self.width, y + self.height - border_radius),
            (x + self.width - border_radius, y + self.height),
            (x + border_radius, y + self.height),
            (x, y + self.height - border_radius),
            (x, y + border_radius),
            (x + border_radius, y),  # Closing the path
        ]
        curve = Curve(points, *self.args, **self.kwargs)
        opsset.extend(curve.draw())

        if self.fill_style is not None:
            bound_box = [
                (x, y),
                (x + self.width, y),
                (x + self.width, y + self.height),
                (x, y + self.height),
            ]
            opsset.add(Ops(type=OpsType.METADATA, data={"drawing_mode": "fill"}))
            filler = get_filler([bound_box], self.fill_style, self.sketch_style)
            opsset.extend(filler.fill())
        return opsset


class RoundedSquare(RoundedRectangle):
    def __init__(
        self,
        top_left: tuple[float, float],
        side_length: float,
        border_radius: float = 0.1,  # this is a percentage of the rectangle height or width
        *args,
        **kwargs,
    ):
        self.side_length = side_length
        super().__init__(
            top_left, side_length, side_length, border_radius, *args, **kwargs
        )
