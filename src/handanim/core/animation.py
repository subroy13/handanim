from typing import Optional
from enum import Enum
from .drawable import Drawable


class AnimationEventType(Enum):
    SKETCH = "sketch"  # draw like you are meant to using human style
    FADE_IN = "fade_in"  # appear from a point
    FADE_OUT = "fade_out"  # disappear into a point


class AnimationEvent:
    """
    Represents an animation event
    happening on the scene
    """

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


class Scene:
    """
    Scene is a single snapshot of a
    animation video using the primitives
    """

    def __init__(
        self,
        width: int = 800,
        height: int = 600,
        background_color: tuple[float, float, float] = (1, 1, 1),
    ):
        self.width = width
        self.height = height
        self.background_color = background_color
        self.objects = {}
        self.objects_metadata = {}
        self.events = []

    def add(
        self,
        event: Optional[AnimationEvent] = None,
        drawable: Optional[Drawable] = None,
    ):
        if event is None and drawable is None:
            raise ValueError("Either event or drawable must be present")
        elif event is None:
            event = AnimationEvent(
                drawable, type=AnimationEventType.SKETCH
            )  # create the basic event
        self.events.append(event)
        object_id = event.drawable.id  # the id of the object to draw
        self.objects[object_id] = event.drawable  # add the object to the scene
        self.objects_metadata[object_id] = {
            "active": True,  # by default, every object is active
        }

    def get_active_drawables(self, t):
        # calculate for each drawable what is the time, it remains active
        pass
