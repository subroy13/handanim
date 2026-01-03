from ..core.draw_ops import OpsSet
from ..core.animation import AnimationEvent, AnimationEventType


class TranslateToAnimation(AnimationEvent):
    """
    A class representing a translate to a point animation event.

    This animation translates an OpsSet from its current center of gravity to a specified point
    over the course of the animation's duration, using an optional easing function.

    Args:
        start_time (float, optional): The start time of the animation. Defaults to 0.
        duration (float, optional): The duration of the animation. Defaults to 0.
        easing_fun (callable, optional): An optional easing function to modify animation progress. Defaults to None.
        data (dict, optional): A dictionary containing animation data, including the target 'point'. Defaults to None.

    Methods:
        _opsset_apply: Calculates and applies the translation of the OpsSet.
        apply: Applies the translation to the given OpsSet at the specified progress.
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
        return new_opsset

    def apply(self, opsset: OpsSet, progress: float):
        return self._opsset_apply(opsset, progress)

class TranslateToPersistAnimation(AnimationEvent):
    """
    A class representing a translate to a point animation event, persisting its final point.

    .. note:: 
        This feature was contributed by Hamd Waseem (https://github.com/hamdivazim)

    This animation translates an OpsSet from its current center of gravity to a specified point
    over the course of the animation's duration, using an optional easing function.

    Args:
        start_time (float, optional): The start time of the animation. Defaults to 0.
        duration (float, optional): The duration of the animation. Defaults to 0.
        easing_fun (callable, optional): An optional easing function to modify animation progress. Defaults to None.
        data (dict, optional): A dictionary containing animation data, including the target 'point'. Defaults to None.

    Methods:
        _opsset_apply: Calculates and applies the translation of the OpsSet.
        apply: Applies the translation to the given OpsSet at the specified progress.
    """

    def __init__(self, start_time=0, duration=0, easing_fun=None, data=None):
        super().__init__(
            AnimationEventType.MUTATION, start_time, duration, easing_fun, data
        )

    def _opsset_apply(self, opsset: OpsSet, progress: float):
        # Get the target point
        point_x, point_y = self.data.get("point", (0, 0))
        gravity_x, gravity_y = opsset.get_center_of_gravity()

        dx = (point_x - gravity_x) * progress
        dy = (point_y - gravity_y) * progress

        new_opsset = OpsSet(initial_set=opsset.opsset)
        new_opsset.translate(dx, dy)

        # persist new position        
        if progress >= 1.0:
            opsset.translate(dx, dy) 

        return new_opsset

    def apply(self, opsset: OpsSet, progress: float):
        return self._opsset_apply(opsset, progress)


class TranslateFromAnimation(TranslateToAnimation):
    """
    A class representing a translate from a point animation event.

    This animation translates an OpsSet from a specified point to its current center of gravity
    over the course of the animation's duration, using an optional easing function.

    Inherits from TranslateToAnimation and reverses the progress to achieve the "from" translation effect.

    Args:
        start_time (float, optional): The start time of the animation. Defaults to 0.
        duration (float, optional): The duration of the animation. Defaults to 0.
        easing_fun (callable, optional): An optional easing function to modify animation progress. Defaults to None.
        data (dict, optional): A dictionary containing animation data, including the starting 'point'. Defaults to None.

    Methods:
        apply: Applies the translation from the specified point to the OpsSet's center of gravity.
    """

    def __init__(self, start_time=0, duration=0, easing_fun=None, data=None):
        super().__init__(start_time, duration, easing_fun, data)

    def apply(self, opsset, progress):
        return super().apply(opsset, 1 - progress)
