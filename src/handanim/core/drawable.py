from typing import List, Tuple, Optional
from uuid import uuid4
from .draw_ops import OpsSet
from ..core.styles import FillStyle, SketchStyle, StrokeStyle


class Drawable:
    """
    A base drawable class that defines the interface for all objects that can be drawn.
    All primitives like Circle, Rectangle, etc. should inherit from this class.
    and implement the draw() method
    """

    def __init__(
        self,
        stroke_style: StrokeStyle = StrokeStyle(),
        sketch_style: SketchStyle = SketchStyle(),
        fill_style: Optional[FillStyle] = None,
    ):
        self.id = uuid4().hex  # generates an hexadecimal random id
        self.stroke_style = stroke_style
        self.sketch_style = sketch_style
        self.fill_style = fill_style

    def draw(self) -> OpsSet:
        """
        Provides the list of operations to be performed to
        draw this particular drawable object on the canvas
        """
        raise NotImplementedError(f"No method for drawing {self.__class__.__name__}")


class DrawableFill:
    """
    A class that defines the different fill styles that can be applied to a drawable object.
    """

    def __init__(
        self,
        bound_box_list: List[
            List[Tuple[float, float]]
        ],  # defines the bounding box for filling
        fill_style: FillStyle = FillStyle(),
        sketch_style: SketchStyle = SketchStyle(),
    ):
        self.bound_box_list = bound_box_list
        self.fill_style = fill_style
        self.sketch_style = sketch_style

    def fill(self) -> OpsSet:
        raise NotImplementedError("fill method not implemented for base fill pattern")
