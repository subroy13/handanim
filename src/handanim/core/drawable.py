from typing import List, Tuple, Optional, Dict, Union
from uuid import uuid4
from .draw_ops import OpsSet
from .styles import FillStyle, SketchStyle, StrokeStyle


class Drawable:
    """
    A base class representing a drawable object with drawing, transformation, and styling capabilities.

    This class provides a standard interface for creating drawable objects that can be drawn on a canvas.
    Subclasses must implement the draw() method to define specific drawing operations.

    Attributes:
        id (str): A unique hexadecimal identifier for the drawable object.
        stroke_style (StrokeStyle): Defines the stroke styling for the drawable.
        sketch_style (SketchStyle): Defines the sketch styling for the drawable.
        fill_style (Optional[FillStyle]): Optional fill style for the drawable.
        glow_dot_hint (Dict): Optional configuration for glow dot rendering.

    Methods:
        draw(): Abstract method to generate drawing operations.
        translate(): Creates a translated version of the drawable.
        scale(): Creates a scaled version of the drawable.
        rotate(): Creates a rotated version of the drawable.
    """

    def __init__(
        self,
        stroke_style: StrokeStyle = StrokeStyle(),
        sketch_style: SketchStyle = SketchStyle(),
        fill_style: Optional[FillStyle] = None,
        glow_dot_hint: Optional[Union[Dict, bool]] = None,
    ):
        self.id = uuid4().hex  # generates an hexadecimal random id
        self.stroke_style = stroke_style
        self.sketch_style = sketch_style
        self.fill_style = fill_style
        self.glow_dot_hint = glow_dot_hint if isinstance(glow_dot_hint, dict) else {}

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"

    def draw(self) -> OpsSet:
        """
        Provides the list of operations to be performed to
        draw this particular drawable object on the canvas
        """
        raise NotImplementedError(f"No method for drawing {self.__class__.__name__}")

    def translate(self, offset_x: float, offset_y: float):
        """
        Translates the drawable object by the given offset
        """
        return TransformedDrawable(
            self, "translate", {"offset_x": offset_x, "offset_y": offset_y}
        )

    def scale(self, scale_x: float, scale_y: float):
        """
        Scales the drawable object by the given scale factors
        """
        return TransformedDrawable(
            self, "scale", {"scale_x": scale_x, "scale_y": scale_y}
        )

    def rotate(self, angle: float):
        """
        Rotates the drawable object by the given angle
        """
        return TransformedDrawable(self, "rotate", {"angle": angle})


class TransformedDrawable(Drawable):
    """
    A drawable object that applies a transformation to a base drawable.

    Allows dynamic transformation of drawable objects by applying a specified
    transformation function to the base drawable's operation set.

    Attributes:
        base_drawable (Drawable): The original drawable object to be transformed
        transformation_function (callable): Name of the transformation method to apply
        transformation_args (dict): Arguments for the transformation method

    Raises:
        ValueError: If the transformation function is invalid or not callable
    """

    def __init__(
        self,
        base_drawable: Drawable,
        transformation_function: callable,
        transformation_args: dict = {},
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.base_drawable = base_drawable
        self.transformation_function = transformation_function
        self.transformation_args = transformation_args

    def draw(self) -> OpsSet:
        """
        Overrides the draw method of the base drawable object
        """
        # apply the base drawable's draw method
        opsset = self.base_drawable.draw()
        if not hasattr(opsset, self.transformation_function):
            raise ValueError(
                f"Invalid transformation function {self.transformation_function}"
            )
        elif not callable(getattr(opsset, self.transformation_function)):
            raise ValueError(
                f"Transformation function {self.transformation_function} is not callable"
            )
        else:
            return getattr(opsset, self.transformation_function)(
                **self.transformation_args
            )


class DrawableFill:
    """
    A class representing a fill style for drawable objects, defining how an area should be filled.

    Allows specification of bounding boxes, fill styles, and sketch styles for rendering.

    Attributes:
        bound_box_list (List[List[Tuple[float, float]]]): Defines the bounding boxes for filling
        fill_style (FillStyle): Specifies the fill style parameters
        sketch_style (SketchStyle): Specifies the sketch style parameters

    Raises:
        NotImplementedError: If the fill method is not implemented in a subclass
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
    A cache management class for storing and retrieving drawable objects and their corresponding operation sets.

    Provides methods to:
    - Store and retrieve drawable objects and their computed operation sets
    - Check for existing drawable operation sets
    - Calculate bounding boxes for multiple drawables

    Attributes:
        cache (dict[str, OpsSet]): A mapping of drawable IDs to their computed operation sets
        drawables (dict[str, Drawable]): A mapping of drawable IDs to their drawable objects
    """

    def __init__(self):
        self.cache: dict[str, OpsSet] = {}
        self.drawables: dict[str, Drawable] = {}

    def has_drawable_oppset(self, drawable_id: str) -> bool:
        return drawable_id in self.cache

    def set_drawable_opsset(self, drawable: Drawable):
        self.drawables[drawable.id] = drawable
        self.cache[drawable.id] = drawable.draw()  # calculate opsset and store

    def get_drawable(self, drawable_id: str) -> Drawable:
        return self.drawables.get(drawable_id, None)

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


class DrawableGroup(Drawable):
    """
    A drawable group that manages a collection of drawable elements with specified grouping behavior.

    Allows applying transformations or animations to multiple drawable objects either in parallel or series.

    Args:
        elements (List[Drawable]): A list of drawable objects to be grouped.
        grouping_method (str, optional): Determines how animations are applied.
            Can be 'parallel' (default) or 'series'. Defaults to 'parallel'.

    Attributes:
        elements (List[Drawable]): The list of drawable elements in the group.
        grouping_method (str): The method used for applying transformations.
    """

    def __init__(
        self, elements: List[Drawable], grouping_method="parallel", *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.elements = elements
        assert grouping_method in ["parallel", "series"]
        self.grouping_method = grouping_method

    def draw(self) -> OpsSet:
        """
        This is useful to apply transformations
        to the entire group of objects at once
        """
        final_set = OpsSet(initial_set=[])
        for elem in self.elements:
            final_set.extend(elem.draw())
        return final_set
