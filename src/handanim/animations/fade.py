from ..core.draw_ops import OpsSet, Ops, OpsType
from ..core.animation import AnimationEvent, AnimationEventType


class FadeInAnimation(AnimationEvent):
    """
    A class representing a fade-in animation event that gradually increases the opacity of elements.

    This animation applies a progressive opacity change from 0 to 1 over a specified duration,
    creating a smooth fade-in effect for graphical elements.

    Args:
        start_time (float, optional): The time at which the animation begins. Defaults to 0.
        duration (float, optional): The total duration of the animation. Defaults to 0.
        easing_fun (callable, optional): An optional function to modify the animation's progress curve. Defaults to None.
        data (dict, optional): Additional data associated with the animation. Defaults to None.
    """

    def __init__(self, start_time=0.0, duration=0.0, easing_fun=None, data=None):
        super().__init__(AnimationEventType.CREATION, start_time, duration, easing_fun, data)

    def _opsset_apply(self, opsset: OpsSet, progress: float):
        current_ops_list = []
        for op in opsset.opsset:
            if op.type == OpsType.SET_PEN:
                modifed_data = {k: progress if k == "opacity" else v for k, v in op.data.items()}
                current_ops_list.append(Ops(type=OpsType.SET_PEN, data=modifed_data, partial=op.partial, meta=op.meta))
            else:
                current_ops_list.append(op)
        new_opsset = OpsSet(initial_set=current_ops_list)
        return new_opsset

    def apply(self, opsset: OpsSet, progress: float):
        return self._opsset_apply(opsset, progress)


class FadeOutAnimation(FadeInAnimation):
    """
    A class representing a fade-out animation event that gradually decreases the opacity of elements.

    This animation applies a progressive opacity change from 1 to 0 over a specified duration,
    creating a smooth fade-out effect for graphical elements.

    Args:
        start_time (float, optional): The time at which the animation begins. Defaults to 0.
        duration (float, optional): The total duration of the animation. Defaults to 0.
        easing_fun (callable, optional): An optional function to modify the animation's progress curve. Defaults to None.
        data (dict, optional): Additional data associated with the animation. Defaults to None.
    """

    def __init__(self, start_time=0.0, duration=0.0, easing_fun=None, data=None):
        super().__init__(start_time, duration, easing_fun, data)
        self.type = AnimationEventType.DELETION  # override the type

    def apply(self, opsset, progress):
        return super().apply(opsset, 1 - progress)
