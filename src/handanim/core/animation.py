from enum import Enum
from typing import List
from .draw_ops import OpsSet


class AnimationEventType(Enum):
    """
    An enumeration representing different types of animation events.
    """

    CREATION = "creation"
    MUTATION = "mutation"
    DELETION = "deletion"
    COMPOSITE = "composite"


class AnimationEvent:
    """
    Represents an animation event occurring on a scene with configurable properties.

    Args:
        type (AnimationEventType): The type of animation to be performed.
        start_time (float, optional): The starting time point of the animation in seconds. Defaults to 0.
        duration (float, optional): The duration of the animation in seconds. Defaults to 0.
        easing_fun (callable, optional): An optional easing function to modify animation progression. Defaults to None.
        data (dict, optional): Additional configuration data specific to the animation type. Defaults to an empty dict.
    """

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
            f"{self.__class__.__name__}(type={self.type}, start_time={self.start_time},"
            f"duration={self.duration}, end_time={self.end_time})"
        )

    def apply(self, opsset: OpsSet, progress: float) -> OpsSet:
        """
        Applies the progress percentage of the given
        animation event to the given opsset
        """
        raise NotImplementedError(
            "apply() method not implemented for basic animation event"
        )

    def subdivide(self, n_division: int):
        """
        Returns subdivision of an event into n_division segments
        """
        cls = self.__class__
        return [
            cls(
                type=self.type,
                start_time=self.start_time + i * self.duration / n_division,
                easing_fun=self.easing_fun,
                data=self.data,
                duration=self.duration / n_division,
            )
            for i in range(n_division)
        ]


class CompositeAnimationEvent(AnimationEvent):
    """
    Represents a composite animation event that combines multiple animation events.

    Args:
        events (List[AnimationEvent]): A list of animation events to be combined.
        easing_fun (callable, optional): An optional easing function to apply to the composite event.
        data (dict, optional): Additional configuration data for the composite animation event.

    Attributes:
        events (List[AnimationEvent]): The list of animation events in the composite event.
    """

    def __init__(
        self,
        events: List[AnimationEvent],
        easing_fun=None,
        data=None,
    ):
        self.events = events
        start_time = min([event.start_time for event in events])
        duration = max([event.duration for event in events])
        super().__init__(
            AnimationEventType.COMPOSITE, start_time, duration, easing_fun, data
        )
