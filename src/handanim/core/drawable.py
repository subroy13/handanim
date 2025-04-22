from typing import List, Tuple, Optional
from uuid import uuid4
from .draw_ops import OpsSet
from .styles import FillStyle, SketchStyle, StrokeStyle


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

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"

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


class DrawableCache:
    """
    A class that implements a cache for the opssets
    related to various drawable objects
    """

    def __init__(self):
        self.cache: dict[str, OpsSet] = {}

    def has_drawable_oppset(self, drawable_id: str) -> bool:
        return drawable_id in self.cache

    def set_drawable_opsset(self, drawable: Drawable):
        self.cache[drawable.id] = drawable.draw()  # calculate opsset and store

    def get_drawable_opsset(self, drawable_id: str) -> OpsSet:
        return self.cache.get(drawable_id, OpsSet(initial_set=[]))

    def calculate_bounding_box(self, drawables: List[Drawable]):
        """
        Calculates the bounding box for a list of drawables
        stored in the cache
        """
        merge_opsset = OpsSet(initial_set=[])
        for drawable in drawables:
            merge_opsset.extend(self.get_drawable_opsset(drawable.id))
        return merge_opsset.get_bbox()
