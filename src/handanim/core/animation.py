from enum import Enum
from typing import List, Tuple
import numpy as np
from .draw_ops import OpsType, OpsSet, Ops
from .styles import FillStyle
from ..primitives.ellipse import GlowDot


class AnimationEventType(Enum):
    SKETCH = "sketch"  # draw like you are meant to using human style
    FADE_IN = "fade_in"  # appear from opacity 0 to 1
    FADE_OUT = "fade_out"  # disappear into opacity 0
    ZOOM_IN = "zoom_in"  # appear from point to object
    ZOOM_OUT = "zoom_out"  # appear from object into point
    TRANSLATE_FROM_POINT = "translate_from_point"  # translate from point to object
    TRANSLATE_TO_POINT = "translate_to_point"  # translate from object to point


class AnimationEvent:
    """
    Represents an animation event occurring on a scene with configurable properties.

    Attributes:
        CREATION_EVENT_TYPES (List[AnimationEventType]): Animation types that signify object creation.
        DESTROY_EVENT_TYPES (List[AnimationEventType]): Animation types that signify object destruction.

    Args:
        type (AnimationEventType): The type of animation to be performed.
        start_time (float, optional): The starting time point of the animation in seconds. Defaults to 0.
        duration (float, optional): The duration of the animation in seconds. Defaults to 0.
        easing_fun (callable, optional): An optional easing function to modify animation progression. Defaults to None.
        data (dict, optional): Additional configuration data specific to the animation type. Defaults to an empty dict.
    """

    CREATION_EVENT_TYPES = [
        AnimationEventType.SKETCH,
        AnimationEventType.FADE_IN,
        AnimationEventType.ZOOM_IN,
    ]
    DESTROY_EVENT_TYPES = [
        AnimationEventType.FADE_OUT,
        AnimationEventType.ZOOM_OUT,
    ]

    def __init__(
        self,
        type: AnimationEventType,  # the type of animation
        start_time: float = 0,  # the starting time point  (in seconds)
        duration: float = 0,  # the duration of the animation (in seconds)
        easing_fun=None,  # easing function to use
        data: dict = None,  # additional data for the animation, depending on the animation type
    ):
        self.type = type
        self.start_time = start_time
        self.duration = duration
        self.end_time = start_time + duration
        self.easing_fun = easing_fun
        self.data = data or {}

    def __repr__(self) -> str:
        return (
            f"AnimationEvent(type={self.type}, start_time={self.start_time},"
            f"duration={self.duration}, end_time={self.end_time})",
        )

    def subdivide(self, n_division: int):
        """
        Returns subdivision of an event into n_division segments
        """
        return [
            AnimationEvent(
                type=self.type,
                start_time=self.start_time + i * self.duration / n_division,
                easing_fun=self.easing_fun,
                data=self.data,
                duration=self.duration / n_division,
            )
            for i in range(n_division)
        ]


def get_sketching_opsset(
    opsset: OpsSet,
    progress: float,
):
    """
    Calculate a partial OpsSet representing the sketching progress of an operation set.

    Args:
        opsset (OpsSet): The original set of operations to be partially sketched.
        progress (float): The progress of sketching, ranging from 0.0 to 1.0.

    Returns:
        OpsSet: A new OpsSet containing the operations up to the specified progress point,
                with the last operation potentially being partially completed.
    """
    base_ops = opsset.opsset
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
    return new_opsset


def get_animated_opsset(
    opsset: OpsSet, animation_events: List[Tuple[AnimationEvent, float]]
):
    """
    Animate an OpsSet based on a list of animation events.

    Applies various animation transformations like sketching, fading, zooming, and translating
    to the input OpsSet according to the specified animation events and their progress.

    Key transformations include:
    - Sketching operations with optional glowing dot
    - Opacity changes (fade in/out)
    - Scaling (zoom in/out)
    - Translation from/to specific points


    Args:
        opsset (OpsSet): The original set of operations to be animated.
        animation_events (List[Tuple[AnimationEvent, float]]): A list of animation events
            with their corresponding progress values (0.0 to 1.0).

    Returns:
        OpsSet: A new OpsSet with applied animation transformations.
    """

    new_opsset = OpsSet(initial_set=[])  # initialize a blank opsset
    # apply sketching operations first if present
    sketching_events = [
        event
        for event in animation_events
        if event[0].type == AnimationEventType.SKETCH
    ]
    for event, progress in sketching_events:
        if progress > 0:
            sketching_opssets = get_sketching_opsset(opsset, progress)
            new_opsset.extend(sketching_opssets)
            # now we can optionally add a glowing dot for the sketching operation
            if event.data.get("glowing_dot"):
                glow_dot_data = event.data.get("glowing_dot")
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
        elif event.type in {
            AnimationEventType.TRANSLATE_FROM_POINT,
            AnimationEventType.TRANSLATE_TO_POINT,
        }:
            # calculate the center of gravity for the opsset
            gravity_x, gravity_y = opsset.get_center_of_gravity()
            point_x, point_y = event.data.get("point", (0, 0))
            coef = (
                1 - progress
                if event.type == AnimationEventType.TRANSLATE_FROM_POINT
                else progress
            )
            cur_x, cur_y = (
                coef * point_x + (1 - coef) * gravity_x,
                coef * point_y + (1 - coef) * gravity_y,
            )
            new_opsset.translate(cur_x - gravity_x, cur_y - gravity_y)

    return new_opsset
