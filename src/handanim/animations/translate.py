from ..core.animation import AnimationEvent, AnimationEventType
from ..core.draw_ops import OpsSet


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

    def __init__(self, start_time=0.0, duration=0.0, easing_fun=None, data=None):
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

    def _apply(self, opsset: OpsSet, progress: float):
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

    def _apply(self, opsset, progress):
        return super()._apply(opsset, 1 - progress)


class MoveBy(AnimationEvent):
    """Translate an `OpsSet` by a relative `(dx, dy)` offset over `duration` seconds."""

    def __init__(
        self,
        dx: float = 0.0,
        dy: float = 0.0,
        start_time: float = 0.0,
        duration: float = 0.0,
        easing_fun=None,
        data: dict | None = None,
        *,
        offset: tuple[float, float] | None = None,
    ) -> None:
        merged_data = dict(data) if data else {}
        if offset is not None:
            dx, dy = float(offset[0]), float(offset[1])
        elif "offset" in merged_data and dx == 0.0 and dy == 0.0:
            off = merged_data["offset"]
            dx, dy = float(off[0]), float(off[1])
        elif ("dx" in merged_data or "dy" in merged_data) and dx == 0.0 and dy == 0.0:
            dx = float(merged_data.get("dx", 0.0))
            dy = float(merged_data.get("dy", 0.0))
        self.dx = float(dx)
        self.dy = float(dy)
        merged_data["dx"] = self.dx
        merged_data["dy"] = self.dy
        merged_data["offset"] = (self.dx, self.dy)
        super().__init__(
            AnimationEventType.MUTATION,
            start_time=start_time,
            duration=duration,
            easing_fun=easing_fun,
            data=merged_data,
        )

    def _opsset_apply(self, opsset: OpsSet, progress: float) -> OpsSet:
        new_opsset = OpsSet(initial_set=list(opsset.opsset))
        new_opsset.translate(self.dx * progress, self.dy * progress)
        return new_opsset

    def _apply(self, opsset: OpsSet, progress: float) -> OpsSet:
        return self._opsset_apply(opsset, progress)


TranslateByAnimation = MoveBy

