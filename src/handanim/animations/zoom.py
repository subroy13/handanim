from ..core.draw_ops import OpsSet
from ..core.animation import AnimationEvent, AnimationEventType


class ZoomInAnimation(AnimationEvent):
    """
    A class representing a zoom-in animation event that scales an OpsSet progressively.

    This animation scales the operations set from its original size to a larger size
    based on the provided progress value. It is typically used for creating or
    expanding visual elements.

    Args:
        start_time (int, optional): The start time of the animation. Defaults to 0.
        duration (int, optional): The duration of the animation. Defaults to 0.
        easing_fun (callable, optional): An optional easing function to modify the animation progress. Defaults to None.
        data (Any, optional): Additional data associated with the animation. Defaults to None.
    """

    def __init__(self, start_time=0, duration=0, easing_fun=None, data=None):
        super().__init__(
            AnimationEventType.CREATION, start_time, duration, easing_fun, data
        )

    def _apply_opsset(self, opsset: OpsSet, progress: float):
        new_opsset = OpsSet(initial_set=opsset.opsset)
        new_opsset.scale(progress)
        return new_opsset

    def apply(self, opsset, progress):
        return self._apply_opsset(opsset, progress)


class ZoomOutAnimation(ZoomInAnimation):
    """
    A class representing a zoom-out animation event that scales an OpsSet progressively.

    This animation scales the operations set from its current size to a smaller size
    based on the provided progress value. It is typically used for shrinking or
    removing visual elements.

    Args:
        start_time (int, optional): The start time of the animation. Defaults to 0.
        duration (int, optional): The duration of the animation. Defaults to 0.
        easing_fun (callable, optional): An optional easing function to modify the animation progress. Defaults to None.
        data (Any, optional): Additional data associated with the animation. Defaults to None.
    """

    def __init__(self, start_time=0, duration=0, easing_fun=None, data=None):
        super().__init__(start_time, duration, easing_fun, data)
        self.type = AnimationEventType.DELETION

    def apply(self, opsset, progress):
        return super().apply(opsset, 1 - progress)
