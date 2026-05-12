from typing import Tuple

from ..core.draw_ops import Ops, OpsSet, OpsType
from ..core.animation import AnimationEvent, AnimationEventType


def _lerp_color(
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
    t: float,
) -> Tuple[float, float, float]:
    return tuple((1 - t) * ca + t * cb for ca, cb in zip(a, b))  # type: ignore[return-value]


class ColorTransitionAnimation(AnimationEvent):
    """
    Interpolates every SET_PEN color in an OpsSet from `start_color` to `end_color`.

    At progress=0 all strokes are rendered with `start_color`; at progress=1 they
    use `end_color`.  The fill color (if present) is interpolated identically.

    Args:
        start_time: When the animation begins (seconds).
        duration: Length of the animation (seconds).
        easing_fun: Optional easing function.
        data: Dict with keys:
            - "start_color" (tuple[float,float,float]): RGB at progress 0. Required.
            - "end_color"   (tuple[float,float,float]): RGB at progress 1. Required.
    """

    def __init__(self, start_time=0.0, duration=0.0, easing_fun=None, data=None):
        super().__init__(AnimationEventType.MUTATION, start_time, duration, easing_fun, data)
        self.start_color: Tuple[float, float, float] = self.data.get("start_color", (0.0, 0.0, 0.0))
        self.end_color: Tuple[float, float, float] = self.data.get("end_color", (1.0, 1.0, 1.0))

    def _apply(self, opsset: OpsSet, progress: float) -> OpsSet:
        current_color = _lerp_color(self.start_color, self.end_color, progress)
        new_ops = []
        for op in opsset.opsset:
            if op.type == OpsType.SET_PEN:
                pen_data = dict(op.data).copy()
                if "color" in pen_data:
                    pen_data["color"] = current_color
                new_ops.append(Ops(type=OpsType.SET_PEN, data=pen_data))
            else:
                new_ops.append(op)
        return OpsSet(initial_set=new_ops)
