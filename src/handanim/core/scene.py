from typing import Optional, List, Tuple, Dict
import numpy as np
from tqdm import tqdm
import cairo
import imageio.v2 as imageio
import os
import subprocess
import tempfile

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
        self.object_timelines: Dict[str, List[float]] = {}
        self.drawable_groups: dict[str, DrawableGroup] = {}  # stores drawable groups present in the scene

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

    def set_viewport_to_identity(self):
        """
        Resets the viewport to an identity transformation, mapping world coordinates directly to screen coordinates.
        """
        self.viewport = Viewport(
            world_xrange=(0, self.width),
            world_yrange=(0, self.height),
            screen_width=self.width,
            screen_height=self.height,
            margin=0,
        )

    def get_viewport_bounds(self) -> Tuple[float, float, float, float]:
        """
        Retrieves the viewport's boundaries in world coordinates.

        Returns:
            Tuple[float, float, float, float]: A tuple containing (x_min, x_max, y_min, y_max)
            representing the viewport's world coordinate boundaries.
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
        Adds an animation event to a drawable primitive in the scene.

        Handles different scenarios including:
        - Composite animation events (recursively adding sub-events)
        - Drawable groups with parallel or sequential event distribution
        - Single event and drawable cases

        Manages event tracking, drawable caching, and object timelines.

        Args:
            event (AnimationEvent): The animation event to be added.
            drawable (Drawable): The drawable primitive to apply the event to.
        """
        # handle the case for composite events if any
        if isinstance(event, CompositeAnimationEvent):
            for sub_event in event.events:
                self.add(
                    sub_event, drawable
                )  # recursively call add() for the subevents
            return
        
        if isinstance(drawable, DrawableGroup):
            # drawable group are usually a syntactic sugar for applying the event to its elements
            if drawable.grouping_method == "series":
                # Apply the event sequentially to each element in the group
                segmented_events = event.subdivide(len(drawable.elements))
                for sub_drawable, segment_event in zip(
                    drawable.elements, segmented_events
                ):
                    # recursively call add(), but with the duration modified appropriately
                    self.add(event=segment_event, drawable=sub_drawable)
                return
            elif drawable.grouping_method == "parallel":
                # group does not have any drawable opsset, so it is not in cache
                # but group_memberships are useful to calculate the opsset on which events get applied.
                if drawable.id not in self.drawable_groups:
                    self.drawable_groups[drawable.id] = drawable
                event.data["apply_to_group"] = drawable.id  # add more context to the event with the group_id
                for elem in drawable.elements:
                    self.add(event, elem)

                return
            
        else:
            # single simple drawable
            self.drawable_cache.set_drawable_opsset(drawable)
            self.drawable_cache.drawables[drawable.id] = drawable

        # Initialize timeline for the new drawable
        if drawable.id not in self.object_timelines:
            self.object_timelines[drawable.id] = []

        self.events.append((event, drawable.id))

        if event.type is AnimationEventType.CREATION:
            self.object_timelines[drawable.id].append(event.start_time)
        elif event.type is AnimationEventType.DELETION:
            # any object cannot be deleted without being created
            if len(self.object_timelines[drawable.id]) == 0:
                self.object_timelines[drawable.id].append(event.start_time) # assume created at the beginning of deletion event

            self.object_timelines[drawable.id].append(event.end_time)

    def get_active_objects(self, t: float):
        """
        Determines the list of object IDs that are active at a specific time point.

        Calculates object visibility by toggling their active status based on their timeline.
        An object becomes active when its timeline reaches a time point, and its status
        alternates with each subsequent time point.

        Args:
            t (float): The time point (in seconds) to check object activity.

        Returns:
            List[str]: A list of object IDs that are active at the given time point.
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
        drawable_id: str,  # the drawable for which we are drawing this
        opsset: OpsSet,
        event: AnimationEvent,
        progress: float = 1.0,
        drawable_events_mapping: Dict[str, List[AnimationEvent]] = {}
    ) -> OpsSet:
        """
            A function that applies a partial animation event to an OpsSet
            Also handles if any drawable group has some partial animation performed on it
        """
        # check if event is applied normally or on a group
        group_id = event.data.get("apply_to_group", None)
        if group_id is None:
            # simple animation, just apply the opsset blindly
            return event.apply(opsset, progress)
        else:
            # this is a group animation
            group = self.drawable_groups[group_id] # get the drawable group
            group_opsset = OpsSet(initial_set=[])
            for elem in group.elements:
                # for each element of the group, get its final state so far before this event starts
                elem_opsset = self.get_opsset_at_time(elem.id, np.ceil(self.fps * event.start_time) - 1, drawable_events_mapping)
                if elem.id == drawable_id:
                    # if the element id current drawable, then add a meta field to track it
                    elem_opsset.add_meta({'drawable_element_id': elem.id})
                    group_opsset.extend(elem_opsset)
            
            # apply the event on group opsset
            group_opsset = event.apply(group_opsset, 1.0)
            
            # filter only relevant opsset that is useful
            opsset = group_opsset.filter_by_meta_query('drawable_element_id', drawable_id)  
            return opsset


    def get_opsset_at_time(self, drawable_id: str, t: int, drawable_events_mapping: Dict[str, List[AnimationEvent]]) -> OpsSet:
        """
            For a drawable, recovers its current_state based on all previous completed events / transformations
        """
        if self.drawable_cache.has_drawable_oppset(drawable_id):
            opsset = self.drawable_cache.get_drawable_opsset(drawable_id)
            drawable = self.drawable_cache.get_drawable(drawable_id)

            # calculate all the events that has happened for this object till now
            persistent_new_events = [
                e for e in drawable_events_mapping.get(drawable_id, [])
                if e.keep_final_state and t / self.fps >= e.end_time
            ]
            if persistent_new_events:
                persistent_new_events.sort(key = lambda e: e.end_time)
                for event in persistent_new_events:
                    opsset = self.get_animated_opsset(drawable.id, opsset, event, 1.0, drawable_events_mapping)
            return opsset
        else:
            # it is not even added to drawable, so scene.add(...) has not happened for it
            return OpsSet(initial_set=[])
    
    def find_key_frames(self):
        """
            Find the key frames that we need to calculate for the animation
            Key frames are the frames where an object is created or deleted
        """
        event_drawable_ids = sorted(self.events, key=lambda x: x[0].start_time)
        events = [event for event, _ in event_drawable_ids]
        drawable_events_mapping: Dict[str, List[AnimationEvent]] = {}  # track for each drawable, what all events are applied
        for event, drawable_id in event_drawable_ids:
            if drawable_id not in drawable_events_mapping:
                drawable_events_mapping[drawable_id] = [event]
            else:
                drawable_events_mapping[drawable_id].append(event)
        key_frames = [event.start_time for event in events] + [event.end_time for event in events]
        key_frames = list(set(key_frames))
        key_frames.sort()
        return key_frames, drawable_events_mapping


    def create_event_timeline(
        self, max_length: Optional[float] = None, verbose: bool = False
    ):
        """
        Creates a timeline of animation events and calculates the OpsSet for each frame.

        This method processes all drawable events, determines active objects at each frame,
        and generates a list of OpsSet operations representing the animation progression.

        Args:
            fps (int, optional): Frames per second for the animation. Defaults to 30.
            max_length (Optional[float], optional): Maximum duration of the animation. Defaults to None.
            verbose (bool, optional): If True, provides detailed logging during animation calculation. Defaults to False.

        Returns:
            List[OpsSet]: A list of OpsSet operations for each frame in the animation.
        """
        key_frames, drawable_events_mapping = self.find_key_frames()
        if max_length is None:
            max_length = np.ceil(key_frames[-1])
        else:
            key_frames.append(max_length)
        key_frame_indices = np.round(np.array(key_frames) * self.fps).astype(int).tolist()
        scene_opsset_list: List[OpsSet] = []
        current_active_objects: List[str] = []

        # start calculating with a progress bar
        frame_count = int(np.round(max_length * self.fps))
        for t in tqdm(
            range(0, frame_count + 1), desc="Calculating animation frames..."
        ):
            frame_opsset = OpsSet(
                initial_set=[]
            )  # initialize with blank opsset, will add more

            # for each frame, update the current active objects if it is a keyframe
            if t in key_frame_indices:
                current_active_objects = self.get_active_objects(t / self.fps)

            # for each of these active objects, calculate partial opssets to draw
            for object_id in current_active_objects:
                
                # Get the current state of the object at this time, including all previous transformations that has been applied
                current_state_opsset = self.get_opsset_at_time(object_id, t, drawable_events_mapping)
                
                # for every object, there could be multiple events associated
                object_drawable: Drawable = self.drawable_cache.get_drawable(object_id)
                active_events = []
                for event in drawable_events_mapping[object_id]:
                    if object_drawable.glow_dot_hint:
                        event.data["glowing_dot"] = object_drawable.glow_dot_hint
                    if event.start_time <= t / self.fps and t / self.fps <= event.end_time:
                        progress = np.clip(
                            (t / self.fps - event.start_time) / event.duration,
                            0,
                            1,
                        )
                        active_events.append(
                            (event, progress)
                        )  # add the event with its progress

                if len(active_events) == 0: # No active animations
                    # Draw the object in its final persistent state (or original if no persistent events)
                    frame_opsset.extend(current_state_opsset)
                else: 
                    # there are some active events, so animation needs to be calculated
                    animated_opsset = current_state_opsset
                    for event, progress in active_events:
                        animated_opsset = self.get_animated_opsset(object_id, animated_opsset, event, progress, drawable_events_mapping) # calculate the partial opsset

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
        Render a snapshot of the animation at a specific time point as an SVG file.

        This method is useful for debugging and inspecting the state of an animation
        at a precise moment. It generates a single frame from the animation timeline
        and saves it as an SVG image.

        Args:
            output_path (str): Path to the output SVG file.
            frame_in_seconds (float): The exact time point (in seconds) to render.
            max_length (Optional[float], optional): Total duration of the animation. Defaults to None.
            verbose (bool, optional): Enable verbose logging. Defaults to False.
        """
        opsset_list = self.create_event_timeline(max_length, verbose)  # create the animated video
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
        """
        Render the animation as a video file.

        This method generates a video by creating a timeline of animation events
        and rendering each frame using Cairo graphics. The video is saved to the
        specified output path with the configured frame rate.

        Args:
            output_path (str): Path to save the output video file.
            max_length (Optional[float], optional): Maximum duration of the animation. Defaults to None.
            verbose (bool, optional): Enable verbose logging for rendering process. Defaults to False.
        """
        # calculate the events
        opsset_list = self.create_event_timeline(max_length, verbose)
        output_file_ext = os.path.basename(output_path).split(os.path.extsep)[-1]
        if output_file_ext.lower() == "gif":
            tqdm_desc = "Rendering GIF..."
            write_obj = imageio.get_writer(output_path, mode = "I", duration = max_length)
        else:
            tqdm_desc = "Rendering video..."
            write_obj = imageio.get_writer(output_path, fps = self.fps, codec = "libx264")

        with write_obj as writer:
            for frame_ops in tqdm(opsset_list, desc=tqdm_desc):
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
