from enum import Enum
from typing import List, Tuple
from .drawable import Drawable
from .draw_ops import OpsType, OpsSet, Ops


class AnimationEventType(Enum):
    SKETCH = "sketch"  # draw like you are meant to using human style
    FADE_IN = "fade_in"  # appear from opacity 0 to 1
    FADE_OUT = "fade_out"  # disappear into opacity 0
    ZOOM_IN = "zoom_in"  # appear from point to object
    ZOOM_OUT = "zoom_out"  # appear from object into point


class AnimationEvent:
    """
    Represents an animation event
    happening on the scene
    """

    CREATION_EVENT_TYPES = [
        AnimationEventType.SKETCH,
        AnimationEventType.FADE_IN,
        AnimationEventType.ZOOM_IN,
    ]
    DESTROY_EVENT_TYPES = [AnimationEventType.FADE_OUT, AnimationEventType.ZOOM_OUT]

    def __init__(
        self,
        drawable: Drawable,  # the drawable object for which the animation happens
        type: AnimationEventType,  # the type of animation
        start_time: float = 0,  # the starting time point  (in seconds)
        duration: float = 0,  # the duration of the animation (in seconds)
        easing_fun=None,  # easing function to use
    ):
        self.drawable = drawable
        self.type = type
        self.start_time = start_time
        self.duration = duration
        self.end_time = start_time + duration
        self.easing_fun = easing_fun

    def __repr__(self) -> str:
        return (
            f"AnimationEvent(type={self.type}, start_time={self.start_time},",
            f"duration={self.duration}, end_time={self.end_time}) for {str(self.drawable)}",
        )


def get_animated_opsset(
    opsset: OpsSet,
    animation_events: List[Tuple[AnimationEvent, float]],
):
    """
    Get the animated opset for the given animation event
       -> Here we have a list of animation events, and for each we have a progress (between 0.0 and 1.0)

    1. First, we need to apply if sketching operation is there => as that gives partial offset
    """

    new_opsset = OpsSet(initial_set=[])
    base_ops = opsset.opsset

    # apply sketching operations first if present
    sketching_events = [
        event
        for event in animation_events
        if event[0].type == AnimationEventType.SKETCH
    ]
    for event, progress in sketching_events:
        if progress > 0:
            n_count = len(
                [op for op in base_ops if op.type not in Ops.SETUP_OPS_TYPES]
            )  # counters are based on the non set-pen operations
            n_active = int(progress * n_count)
            counter = 0
            last_op = None
            new_opsset = OpsSet(initial_set=[])  # initially start with blank opsset
            for op in base_ops:
                if op.type not in Ops.SETUP_OPS_TYPES and counter < n_active:
                    new_opsset.add(op)
                    counter += 1
                elif counter < n_active:
                    # set pen operations keep adding, but don't increase counter
                    new_opsset.add(op)
                else:
                    last_op = op  # the last operation for which it stopped
                    break
            if last_op is not None and (progress * n_count - n_active) > 0:
                # need to calculate it partially
                new_opsset.add(
                    Ops(
                        type=last_op.type,
                        data=last_op.data,
                        partial=progress * n_count - n_active,
                    )
                )

    if len(sketching_events) == 0:
        # no sketching operations, so just add the base opset
        new_opsset.extend(opsset)

    # add more event operations
    for event, progress in animation_events:
        if event.type in {AnimationEventType.FADE_IN, AnimationEventType.FADE_OUT}:
            mod_opacity = (
                progress if event.type == AnimationEventType.FADE_IN else 1 - progress
            )
            for i, op in enumerate(new_opsset.opsset):
                if op.type == OpsType.SET_PEN:
                    modifed_data = {
                        k: mod_opacity if k == "opacity" else v
                        for k, v in op.data.items()
                    }
                    new_opsset.opsset[i] = Ops(
                        type=OpsType.SET_PEN, data=modifed_data, partial=op.partial
                    )
        elif event.type in {AnimationEventType.ZOOM_IN, AnimationEventType.ZOOM_OUT}:
            mod_scale = (
                progress if event.type == AnimationEventType.ZOOM_IN else 1 - progress
            )
            new_opsset.scale(mod_scale)  # perform scaling

    return new_opsset
