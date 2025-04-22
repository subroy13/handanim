from typing import Optional, List
import numpy as np
from tqdm import tqdm
import cairo
import imageio.v2 as imageio

from .utils import cairo_surface_to_numpy
from .animation import AnimationEvent, AnimationEventType, get_animated_opsset
from .drawable import Drawable, DrawableCache
from .draw_ops import OpsSet


class Scene:
    """
    Scene is where all the magic happens
    """

    def __init__(
        self,
        width: int = 800,
        height: int = 608,
        background_color: tuple[float, float, float] = (1, 1, 1),
    ):
        self.width = width
        self.height = height
        self.background_color = background_color
        self.drawable_cache = DrawableCache()
        self.events: List[AnimationEvent] = []
        self.object_timelines = {}

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
            )  # create the basic sketch event
        self.events.append(event)
        drawable = event.drawable

        if not self.drawable_cache.has_drawable_oppset(drawable.id):
            self.drawable_cache.set_drawable_opsset(drawable)
            self.object_timelines[drawable.id] = []

        if event.type in AnimationEvent.CREATION_EVENT_TYPES:
            self.object_timelines[drawable.id].append(event.start_time)
        elif event.type in AnimationEvent.DESTROY_EVENT_TYPES:
            self.object_timelines[drawable.id].append(event.end_time)

    def get_active_objects(self, t: float):
        """
        At a timepoint t (in seconds), return the list of object_ids
        that needs to be active on the scene
        """
        active_list: List[str] = []
        for object_id in self.object_timelines:
            active = False  # everything starts with blank screen
            for time in self.object_timelines[object_id]:
                if t >= time:
                    active = not active  # switch status
                else:
                    # time has increased beyond t
                    break
            if active:
                active_list.append(object_id)
        return active_list

    def create_event_timeline(self, fps: int = 30, max_length: Optional[float] = None):
        """
        Calculates the timeline of events in which order
        need to process the opssets and what to draw
        for each frame
        """
        events: List[AnimationEvent] = self.events
        events.sort(key=lambda x: x.start_time)  # sort events in place
        key_frames = [event.start_time for event in events] + [
            event.end_time for event in events
        ]
        if max_length is None:
            max_length = np.round(key_frames[-1])
        else:
            max_length = np.round(max_length * fps)  # else convert to frames
            key_frames.append(max_length)
        key_frames = list(set(key_frames))
        key_frames.sort()
        key_frames = np.round(
            np.array(key_frames) * fps
        ).tolist()  # this converts seconds to frames
        scene_opsset_list: List[OpsSet] = []
        current_active_objects: List[str] = []

        # start calculating with a progress bar
        for t in tqdm(range(0, max_length + 1), desc="Calculating animation frames..."):
            frame_opsset = OpsSet(
                initial_set=[]
            )  # initialize with blank opsset, will add more

            # for each frame, update the current active objects if it is a keyframe
            if t in key_frames:
                current_active_objects = self.get_active_objects(t / fps)

            # for each of these active objects, calculate partial opssets to draw
            for object_id in current_active_objects:
                object_opsset: OpsSet = self.drawable_cache.get_drawable_opsset(
                    object_id
                )

                # for every object, there could be multiple events associated
                active_events = []
                for event in events:
                    # find the relevant events
                    if (
                        event.drawable.id == object_id
                        and event.start_time <= t / fps
                        and t / fps <= event.end_time
                    ):
                        progress = np.clip(
                            (t / fps - event.start_time) / event.duration,
                            0,
                            1,
                        )
                        active_events.append(
                            (event, progress)
                        )  # add the event with its progress
                if len(active_events) == 0:
                    # no active events, but object is active
                    # object is completely visible, so draw fully
                    frame_opsset.extend(object_opsset)
                else:
                    # there are some active events, so animation needs to be calcualted
                    partial_opsset = get_animated_opsset(
                        object_opsset, active_events
                    )  # calculate the partial opsset

                    frame_opsset.extend(partial_opsset)
            scene_opsset_list.append(frame_opsset)  # create the list of ops at scene
        return scene_opsset_list

    def render_snapshot(
        self,
        output_path: str,  # must be an svg file path
        frame: float,  # the precise second index for the frame to render
        fps: int = 20,
        max_length: Optional[float] = None,  # number of seconds to create the video for
    ):
        """
        This is a helper function used to debug video snapshots
        """
        opsset_list = self.create_event_timeline(
            fps, max_length
        )  # create the animated video
        frame_index = np.clip(
            np.round(frame * fps), 0, len(opsset_list) - 1
        )  # get the frame index
        frame_ops: OpsSet = opsset_list[frame_index]
        with cairo.SVGSurface(output_path, self.width, self.height) as surface:
            ctx = cairo.Context(surface)  # create cairo context

            # set the background color
            if self.background_color is not None:
                ctx.set_source_rgb(*self.background_color)
            ctx.paint()

            frame_ops.render(ctx)
            surface.finish()

    def render(
        self, output_path: str, fps: int = 20, max_length: Optional[float] = None
    ):
        # calculate the events
        opsset_list = self.create_event_timeline(fps, max_length)
        with imageio.get_writer(output_path, fps=fps, codec="libx264") as writer:
            for frame_ops in tqdm(opsset_list, desc="Rendering video..."):
                surface = cairo.ImageSurface(
                    cairo.FORMAT_ARGB32, self.width, self.height
                )
                ctx = cairo.Context(surface)  # create cairo context

                # optional background
                if self.background_color is not None:
                    ctx.set_source_rgb(*self.background_color)
                ctx.paint()

                frame_ops.render(ctx)  # applies the operations to cairo context

                frame_np = cairo_surface_to_numpy(surface)
                writer.append_data(frame_np)
