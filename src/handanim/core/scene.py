from typing import Optional, List, Tuple, Dict
import numpy as np
from tqdm import tqdm
import cairo
import imageio.v2 as imageio

from .utils import cairo_surface_to_numpy
from .animation import AnimationEvent, CompositeAnimationEvent, AnimationEventType
from .drawable import Drawable, DrawableCache, DrawableGroup
from .draw_ops import OpsSet
from .viewport import Viewport


class Scene:
    """
    A Scene represents an animation composition where drawables and events are managed.

    Handles the creation, timeline, and rendering of animated graphics with configurable
    viewport, background, and frame settings. Supports creating snapshots and full video
    renders of animated sequences.

    Attributes:
        width (int): Width of the rendering surface in pixels.
        height (int): Height of the rendering surface in pixels.
        fps (int): Frames per second for video rendering.
        background_color (tuple): RGB color for scene background.
        viewport (Viewport): Defines coordinate mapping between world and screen space.
    """

    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        fps: int = 24,
        background_color: tuple[float, float, float] = (1, 1, 1),
        viewport: Optional[Viewport] = None,
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.background_color = background_color
        self.drawable_cache = DrawableCache()
        self.events: List[Tuple[AnimationEvent, str]] = []
        self.object_timelines: Dict[str, List[int]] = {}

        if viewport is not None:
            self.viewport = viewport
        else:
            self.viewport = Viewport(
                world_xrange=(
                    0,
                    1000 * (width / height),
                ),  # adjusted to match aspect ratio
                world_yrange=(0, 1000),
                screen_width=width,
                screen_height=height,
                margin=20,
            )

    def get_viewport_bounds(self) -> Tuple[float, float, float, float]:
        """
        Returns the bounds of the viewport in world coordinates
        """
        return (
            self.viewport.world_xrange[0],
            self.viewport.world_xrange[1],
            self.viewport.world_yrange[0],
            self.viewport.world_yrange[1],
        )

    def add(
        self,
        event: AnimationEvent,
        drawable: Drawable,
    ):
        """
        Applies an animation event to a drawable primitive and
        adds it to the scene
        """
        # handle the case for composite events if any
        if isinstance(event, CompositeAnimationEvent):
            for sub_event in event.events:
                self.add(
                    sub_event, drawable
                )  # recursively call add() for the subevents
            return

        # handle the case for drawable groups
        if isinstance(drawable, DrawableGroup):
            if drawable.grouping_method == "parallel":
                for sub_drawable in drawable.elements:
                    # recursively call add() method, as a syntantic sugar
                    self.add(event, drawable=sub_drawable)
            else:
                segmented_events = event.subdivide(len(drawable.elements))
                for sub_drawable, segment_event in zip(
                    drawable.elements, segmented_events
                ):
                    # recursively call add(), but with the duration modified appropriately
                    self.add(event=segment_event, drawable=sub_drawable)
            return

        # handle the simple single event and drawable case
        self.events.append((event, drawable.id))
        if not self.drawable_cache.has_drawable_oppset(drawable.id):
            self.drawable_cache.set_drawable_opsset(drawable)
            self.object_timelines[drawable.id] = []

        if event.type is AnimationEventType.CREATION:
            self.object_timelines[drawable.id].append(event.start_time)
        elif event.type is AnimationEventType.DELETION:
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

    def get_animated_opsset(
        self,
        opsset: OpsSet,
        animation_events: List[Tuple[AnimationEvent, float]],
        verbose: bool = False,
    ):
        """
        Returns the opsset with the events applied
        """
        # TODO: need to check later if the sketching events need to be applied first?
        current_opsset = opsset
        for event, progress in animation_events:
            current_opsset = event.apply(current_opsset, progress)
            if verbose:
                print(f"{round(progress, 2)} of {str(event)}")
        return current_opsset

    def create_event_timeline(
        self, fps: int = 30, max_length: Optional[float] = None, verbose: bool = False
    ):
        """
        Calculates the timeline of events in which order
        need to process the opssets and what to draw
        for each frame
        """
        event_drawable_ids = sorted(self.events, key=lambda x: x[0].start_time)
        events = [event for event, _ in event_drawable_ids]
        drawable_events_mapping: Dict[str, List[AnimationEvent]] = {}
        for event, drawable_id in event_drawable_ids:
            if drawable_id not in drawable_events_mapping:
                drawable_events_mapping[drawable_id] = [event]
            else:
                drawable_events_mapping[drawable_id].append(event)
        key_frames = [event.start_time for event in events] + [
            event.end_time for event in events
        ]
        if max_length is None:
            max_length = np.ceil(key_frames[-1])
        else:
            key_frames.append(max_length)
        key_frames = list(set(key_frames))
        key_frames.sort()
        key_frame_indices = np.round(np.array(key_frames) * fps).astype(int).tolist()
        scene_opsset_list: List[OpsSet] = []
        current_active_objects: List[str] = []

        # start calculating with a progress bar
        frame_count = int(np.round(max_length * fps))
        for t in tqdm(
            range(0, frame_count + 1), desc="Calculating animation frames..."
        ):
            frame_opsset = OpsSet(
                initial_set=[]
            )  # initialize with blank opsset, will add more

            # for each frame, update the current active objects if it is a keyframe
            if t in key_frame_indices:
                current_active_objects = self.get_active_objects(t / fps)

            # for each of these active objects, calculate partial opssets to draw
            for object_id in current_active_objects:
                object_opsset: OpsSet = self.drawable_cache.get_drawable_opsset(
                    object_id
                )
                object_drawable: Drawable = self.drawable_cache.get_drawable(object_id)

                # for every object, there could be multiple events associated
                active_events = []
                for event in drawable_events_mapping[object_id]:
                    if object_drawable.glow_dot_hint:
                        event.data["glowing_dot"] = object_drawable.glow_dot_hint
                    if event.start_time <= t / fps and t / fps <= event.end_time:
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
                    # there are some active events, so animation needs to be calculated
                    animated_opsset = self.get_animated_opsset(
                        object_opsset, active_events, verbose
                    )  # calculate the partial opsset

                    frame_opsset.extend(animated_opsset)
            scene_opsset_list.append(frame_opsset)  # create the list of ops at scene
        return scene_opsset_list

    def render_snapshot(
        self,
        output_path: str,  # must be an svg file path
        frame_in_seconds: float,  # the precise second index for the frame to render
        max_length: Optional[float] = None,  # number of seconds to create the video for
        verbose: bool = False,
    ):
        """
        This is a helper function used to debug video snapshots
        """
        opsset_list = self.create_event_timeline(
            self.fps, max_length, verbose
        )  # create the animated video
        frame_index = int(
            np.clip(np.round(frame_in_seconds * self.fps), 0, len(opsset_list) - 1)
        )  # get the frame index
        frame_ops: OpsSet = opsset_list[frame_index]
        with cairo.SVGSurface(output_path, self.width, self.height) as surface:
            ctx = cairo.Context(surface)  # create cairo context

            # set the background color
            if self.background_color is not None:
                ctx.set_source_rgb(*self.background_color)
            ctx.paint()

            self.viewport.apply_to_context(ctx)
            frame_ops.render(ctx)
            surface.finish()

    def render(
        self, output_path: str, max_length: Optional[float] = None, verbose=False
    ):
        # calculate the events
        opsset_list = self.create_event_timeline(self.fps, max_length, verbose)
        with imageio.get_writer(output_path, fps=self.fps, codec="libx264") as writer:
            for frame_ops in tqdm(opsset_list, desc="Rendering video..."):
                surface = cairo.ImageSurface(
                    cairo.FORMAT_ARGB32, self.width, self.height
                )
                ctx = cairo.Context(surface)  # create cairo context

                # optional background
                if self.background_color is not None:
                    ctx.set_source_rgb(*self.background_color)
                ctx.paint()

                self.viewport.apply_to_context(ctx)
                frame_ops.render(ctx)  # applies the operations to cairo context

                frame_np = cairo_surface_to_numpy(surface)
                writer.append_data(frame_np)
