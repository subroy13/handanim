from typing import Optional, List
from enum import Enum
import numpy as np
import cairo
import imageio.v2 as imageio

from .renderer import cairo_surface_to_numpy, render_opsset
from .drawable import Drawable
from .draw_ops import OpsSet, OpsType, Ops


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
        return f"AnimationEvent(type={self.type}, start_time={self.start_time}, duration={self.duration}, end_time={self.end_time}) for {str(self.drawable)}"


class Scene:
    """
    Scene is a single snapshot of a
    animation video using the primitives
    """

    CREATION_EVENT_TYPES = [
        AnimationEventType.SKETCH,
        AnimationEventType.FADE_IN,
        AnimationEventType.ZOOM_IN,
    ]
    DESTROY_EVENT_TYPES = [AnimationEventType.FADE_OUT, AnimationEventType.ZOOM_OUT]

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
        if object_id not in self.objects:
            self.objects[object_id] = event.drawable  # add the object to the scene
            self.objects_metadata[object_id] = {
                "active_timeline": [],
                "opsset": event.drawable.draw(),
            }  # initialize

        # if creation type event
        if event.type in self.CREATION_EVENT_TYPES:
            self.objects_metadata[object_id]["active_timeline"].append(event.start_time)
        elif event.type in self.DESTROY_EVENT_TYPES:
            self.objects_metadata[object_id]["active_timeline"].append(event.end_time)

    def get_active_objects(self, t: float):
        """
        At a timepoint t, return the list of object_ids
        that needs to be active on the scene
        """
        active_list: List[str] = []
        for object_id in self.objects_metadata:
            active = False  # everything starts with blank screen
            for time in self.objects_metadata[object_id]["active_timeline"]:
                if t >= time:
                    active = not active  # switch status
                else:
                    # time has increased beyond t
                    break
            if active:
                active_list.append(object_id)
        return active_list

    def get_animated_opset(
        self, opsset: OpsSet, animation_type: AnimationEventType, progress: float = 1.0
    ):
        """
        Get the progress proportion of the OpsSets calculated for the
        specific type of animation
        """
        if progress <= 0:
            return OpsSet(initial_set=[])
        progress = min(progress, 1.0)
        base_ops = opsset.opsset

        if animation_type == AnimationEventType.SKETCH:
            n_count = len(
                [op for op in base_ops if op.type != OpsType.SET_PEN]
            )  # counters are based on the non set-pen operations
            n_active = int(progress * n_count)
            counter = 0
            last_op = None
            new_opsset = OpsSet(initial_set=[])  # initially start with blank opsset
            for op in base_ops:
                if op.type != OpsType.SET_PEN and counter < n_active:
                    new_opsset.add(op)
                    counter += 1
                elif counter < n_active:
                    # set pen operations keep adding
                    new_opsset.add(op)
                else:
                    last_op = op  # the last operation for which it stopped
                    break

            if last_op is not None and (progress * n_count - n_active) > 0:
                # need to calculate it partially
                last_op.partial = progress * n_count - n_active
                new_opsset.add(last_op)
            return new_opsset
        elif animation_type in {
            AnimationEventType.FADE_IN,
            AnimationEventType.FADE_OUT,
        }:
            new_opsset = OpsSet(initial_set=[])
            mod_opacity = (
                progress
                if animation_type == AnimationEventType.FADE_IN
                else 1 - progress
            )
            for op in base_ops:
                if op.type == OpsType.SET_PEN:
                    modifed_data = dict(op.data)
                    modifed_data["opacity"] = mod_opacity
                    new_opsset.add(
                        Ops(type=OpsType.SET_PEN, data=modifed_data, partial=op.partial)
                    )
                else:
                    new_opsset.add(op)  # add as it is
            return new_opsset
        elif animation_type in {
            AnimationEventType.ZOOM_IN,
            AnimationEventType.ZOOM_OUT,
        }:
            # TODO: handle this case by sending proper set_pen event
            return opsset
        else:
            raise NotImplementedError("Other animation methods are not yet implemented")

    def create_event_timeline(
        self,
        fps: int = 20,
        max_length: Optional[float] = None,  # number of seconds to create the video for
    ) -> List[OpsSet]:
        events: List[AnimationEvent] = self.events
        events.sort(key=lambda x: x.start_time)  # sort events in place
        key_frames = [event.start_time for event in events] + [
            event.end_time for event in events
        ]
        key_frames.sort()
        key_frames = np.round(
            np.array(key_frames) * fps
        ).tolist()  # this converts seconds to frames

        scene_opsset_list: List[OpsSet] = []
        current_active_objects = None
        if max_length is None:
            max_length = np.round(key_frames[-1])
        else:
            max_length = np.round(max_length * fps)  # else convert to frames
        for t in range(0, max_length):
            frame_opsset = OpsSet(
                initial_set=[]
            )  # initialize with blank opsset, will add more

            # for each frame need to compute the operation sets
            if t in key_frames:
                # there is some event change
                current_active_objects = self.get_active_objects(t)

            # for these active objects, calculate partial opssets to draw
            for object_id in current_active_objects:
                object_opsset: OpsSet = self.objects_metadata[object_id]["opsset"]
                active_event = None
                for event in events:
                    # find the relevant event
                    if (
                        event.drawable.id == object_id
                        and event.start_time <= t / fps
                        and t / fps <= event.end_time
                    ):
                        active_event = event
                        break
                if active_event is None:
                    # there is no event at this time, but object is active
                    # object is completely visible, so draw fully
                    frame_opsset.extend(object_opsset)
                else:
                    # there was an active event
                    progress = np.clip(
                        (t / fps - active_event.start_time) / active_event.duration,
                        0,
                        1,
                    )
                    partial_opsset = self.get_animated_opset(
                        object_opsset, active_event.type, progress
                    )
                    frame_opsset.extend(partial_opsset)
            scene_opsset_list.append(frame_opsset)  # create the list of ops at scene
        return scene_opsset_list

    def render(
        self, output_path: str, fps: int = 20, max_length: Optional[float] = None
    ):
        # calculate the events
        opsset_list = self.create_event_timeline(fps, max_length)
        with imageio.get_writer(output_path, fps=fps, codec="libx264") as writer:
            for frame_ops in opsset_list:
                surface = cairo.ImageSurface(
                    cairo.FORMAT_ARGB32, self.width, self.height
                )
                ctx = cairo.Context(surface)  # create cairo context

                # optional background
                if self.background_color is not None:
                    ctx.set_source_rgb(*self.background_color)
                ctx.paint()

                render_opsset(ctx, frame_ops)  # applies the operations to cairo context

                frame_np = cairo_surface_to_numpy(surface)
                writer.append_data(frame_np)
