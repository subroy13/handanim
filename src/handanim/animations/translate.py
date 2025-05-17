from ..core.draw_ops import OpsSet
from ..core.animation import AnimationEvent, AnimationEventType


class TranslateToAnimation(AnimationEvent):
    """
    A class representing a translate to a point animation event.
    """

    def __init__(self, start_time=0, duration=0, easing_fun=None, data=None):
        super().__init__(
            AnimationEventType.MUTATION, start_time, duration, easing_fun, data
        )

    def _opsset_apply(self, opsset: OpsSet, progress: float):
        new_opsset = OpsSet(initial_set=opsset.opsset)
        # calculate the center of gravity for the opsset
        gravity_x, gravity_y = opsset.get_center_of_gravity()
        point_x, point_y = self.data.get("point", (0, 0))
        cur_x, cur_y = (
            progress * point_x + (1 - progress) * gravity_x,
            progress * point_y + (1 - progress) * gravity_y,
        )
        new_opsset.translate(cur_x - gravity_x, cur_y - gravity_y)

    def apply(self, opsset: OpsSet, progress: float):
        return self._opsset_apply(opsset, progress)


class TranslateFromAnimation(TranslateToAnimation):
    """
    A class representing a translate from a point animation event.
    """

    def __init__(self, start_time=0, duration=0, easing_fun=None, data=None):
        super().__init__(
            AnimationEventType.MUTATION, start_time, duration, easing_fun, data
        )

    def apply(self, opsset, progress):
        return super().apply(opsset, 1 - progress)
