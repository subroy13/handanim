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
    of the boundaries of the primitives
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
    A class that defines the styling configurations for the fills
    of the primitives
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
    A class that defines the styling configurations for the
    sketchy versions of the human-style drawings
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
