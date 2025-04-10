class RoughOptions:

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
