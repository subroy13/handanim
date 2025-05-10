from enum import Enum


class StrokePressure(Enum):
    """
    A class that defines the pressure of the strokes
    """

    CONSTANT = "constant"
    PROPORTIONAL = "proportional"
    INVERSE = "inverse"


# defines the 3 major types of styling configurations
class StrokeStyle:
    """
    A class that defines the styling configurations for the strokes
    of the boundaries of the primitives.

    Allows customization of stroke appearance including color, width, opacity,
    and pressure characteristics. Defaults to a black, 1-pixel wide constant
    pressure stroke with full opacity.

    Attributes:
        options (dict): Raw keyword arguments passed during initialization
        color (tuple): RGB color tuple, defaults to black (0, 0, 0)
        width (int/float): Stroke width in pixels, defaults to 1
        opacity (float): Stroke opacity from 0-1, defaults to 1
        stroke_pressure (StrokePressure): Pressure mode for stroke rendering,
            defaults to StrokePressure.CONSTANT
    """

    def __init__(self, **kwargs):
        if kwargs is None:
            kwargs = {}
        self.options = kwargs
        self.color = kwargs.get("color", (0, 0, 0))
        self.width = kwargs.get("width", 1)
        self.opacity = kwargs.get("opacity", 1)
        self.stroke_pressure = kwargs.get("stroke_pressure", StrokePressure.CONSTANT)


class FillStyle:
    """
    A class that defines the styling configurations for the fills of the primitives.

    Allows customization of fill appearance including color, opacity, fill pattern,
    hachure settings, and fill weight. Defaults to a black fill with full opacity
    and hachure pattern.

    Attributes:
        options (dict): Raw keyword arguments passed during initialization
        color (tuple): RGB color tuple, defaults to black (0, 0, 0)
        opacity (float): Fill opacity from 0-1, defaults to 1
        fill_pattern (str): Pattern for filling, defaults to "hachure"
        hachure_angle (int): Angle of hachure lines in degrees, defaults to 45
        hachure_gap (int): Gap between hachure lines, defaults to 4
        hachure_line_width (int): Width of hachure lines, defaults to 1
        zigzag_offset (int): Offset for zigzag pattern, defaults to -1
        fill_weight (int): Weight/thickness of fill, defaults to 2
    """

    def __init__(self, **kwargs):
        if kwargs is None:
            kwargs = {}
        self.options = kwargs
        self.color = kwargs.get("color", (0, 0, 0))
        self.opacity = kwargs.get("opacity", 1)
        self.fill_pattern = kwargs.get("fill_pattern", "hachure")
        self.hachure_angle = kwargs.get("hachure_angle", 45)
        self.hachure_gap = kwargs.get("hachure_gap", 4)
        self.hachure_line_width = kwargs.get("hachure_line_width", 1)
        self.zigzag_offset = kwargs.get("zigzag_offset", -1)
        self.fill_weight = kwargs.get("fill_weight", 2)


class SketchStyle:
    """
    A class that defines the styling configurations for sketchy, hand-drawn style renderings.

    Attributes:
        bowing (int): Amount of bowing/waviness in lines, defaults to 1
        max_random_offset (int): Maximum random offset for sketch lines, defaults to 2
        roughness (int): Roughness of sketch lines, defaults to 1
        curve_tightness (int): Tightness of curves, defaults to 0
        curve_fitting (float): Curve fitting parameter, defaults to 0.95
        curve_step_count (int): Number of steps for curve rendering, defaults to 9
        disable_multi_stroke (bool): Flag to disable multi-stroke rendering, defaults to False
        disable_font_mixture (bool): Flag to disable font mixture, defaults to True
    """

    def __init__(self, **kwargs):
        if kwargs is None:
            kwargs = {}
        self.options = kwargs
        self.bowing = kwargs.get("bowing", 1)
        self.max_random_offset = kwargs.get("max_random_offset", 2)
        self.roughness = kwargs.get("roughness", 1)
        self.curve_tightness = kwargs.get("curve_tightness", 0)
        self.curve_fitting = kwargs.get("curve_fitting", 0.95)
        self.curve_step_count = kwargs.get("curve_step_count", 9)
        self.disable_multi_stroke = kwargs.get("disable_multi_stroke", False)
        self.disable_font_mixture = kwargs.get("disable_font_mixture", True)
