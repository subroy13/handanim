from typing import Optional, Tuple

from ..core.draw_ops import OpsSet
from ..core.animation import AnimationEvent, AnimationEventType


class RotateAnimation(AnimationEvent):
    """
    Animates a rotation of an OpsSet from 0 to `angle` degrees over the duration.

    The rotation is applied around the center of gravity by default, or around
    a fixed `center` point if provided in data.

    Args:
        start_time: When the animation begins (seconds).
        duration: Length of the animation (seconds).
        easing_fun: Optional easing function.
        data: Dict with optional keys:
            - "angle" (float): Total rotation angle in degrees. Default 360.
            - "center" (tuple[float, float]): Fixed pivot point. Default: center of gravity.
    """

    def __init__(self, start_time=0.0, duration=0.0, easing_fun=None, data=None):
        super().__init__(AnimationEventType.MUTATION, start_time, duration, easing_fun, data)
        self.angle = self.data.get("angle", 360)
        self.center: Optional[Tuple[float, float]] = self.data.get("center", None)

    def _apply(self, opsset: OpsSet, progress: float) -> OpsSet:
        new_opsset = OpsSet(initial_set=opsset.opsset)
        pivot = self.center if self.center is not None else new_opsset.get_center_of_gravity()
        new_opsset.rotate(self.angle * progress, center_of_rotation=pivot)
        return new_opsset
