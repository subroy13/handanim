import numpy as np
from ..core.draw_ops import OpsSet
from ..core.animation import AnimationEvent, AnimationEventType
from ..core.styles import FillStyle
from ..primitives.ellipse import GlowDot


class SketchAnimation(AnimationEvent):
    """
    A class representing a sketch animation event.
    """

    def __init__(self, start_time=0, duration=0, easing_fun=None, data=None):
        super().__init__(
            AnimationEventType.CREATION, start_time, duration, easing_fun, data
        )

    def apply(self, opsset: OpsSet, progress: float):
        """
        Apply the animation to the given opsset.
        """
        new_opsset = OpsSet(initial_set=[])
        if progress > 0:
            sketching_opssets = opsset.get_partial(progress)
            new_opsset.extend(sketching_opssets)
            # now we can optionally add a glowing dot for the sketching operation
            if self.data.get("glowing_dot"):
                glow_dot_data = self.data.get("glowing_dot")
                if not isinstance(glow_dot_data, dict):
                    glow_dot_data = {}
                # we need to draw glowing dot
                cx, cy = (
                    sketching_opssets.get_current_point()
                )  # get the current point based on sketching

                breathing_factor = 1 + 0.05 * np.sin(
                    2 * np.pi * progress * glow_dot_data.get("frequency", 5)
                )  # have a subtle breathing effect to increase or decrease glow
                dot = GlowDot(
                    center=(cx, cy),
                    radius=glow_dot_data.get("radius", 5) * breathing_factor,
                    fill_style=FillStyle(
                        color=glow_dot_data.get("color", (0.5, 0.5, 0.5))
                    ),
                )
                new_opsset.extend(dot.draw())  # add this dot at the end of current path
        else:
            # progress is 0, so nothing should be drawn
            return new_opsset
