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
