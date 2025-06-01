from ..core.draw_ops import OpsSet
from ..core.animation import AnimationEvent, AnimationEventType


class ZoomInAnimation(AnimationEvent):
    """
    A class representing a zoom-in animation event.
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
    A class representing a zoom-out animation event.
    """

    def __init__(self, start_time=0, duration=0, easing_fun=None, data=None):
        super().__init__(start_time, duration, easing_fun, data)
        self.type = AnimationEventType.DELETION

    def apply(self, opsset, progress):
        return super().apply(opsset, 1 - progress)
