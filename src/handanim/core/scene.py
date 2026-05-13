import os

import cairo
import imageio.v2 as imageio
import numpy as np
from tqdm import tqdm

from .animation import AnimationEvent, AnimationEventType, CompositeAnimationEvent
from .cache import DrawableCache, GroupFrameCache
from .draw_ops import OpsSet
from .drawable import Drawable, DrawableGroup
from .utils import cairo_surface_to_numpy
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
        viewport: Viewport | None = None,
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.background_color = background_color
        self.drawable_cache = DrawableCache()
        self.frame_cache = GroupFrameCache()
        self.events: list[tuple[AnimationEvent, str]] = []
        self.object_timelines: dict[str, list[float]] = {}
        self.drawable_groups: dict[str, DrawableGroup] = {}  # stores drawable groups present in the scene
        self.camera_events: list = []  # CameraAnimation events; typed as List to avoid circular import

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

    def get_viewport_bounds(self) -> tuple[float, float, float, float]:
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
                self.add(sub_event, drawable)  # recursively call add() for the subevents
            return

        if isinstance(drawable, DrawableGroup):
            # drawable group are usually a syntactic sugar for applying the event to its elements
            if drawable.grouping_method == "series":
                # Apply the event sequentially to each element in the group
                segmented_events = event.subdivide(len(drawable.elements))
                for sub_drawable, segment_event in zip(drawable.elements, segmented_events, strict=False):
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
                self.object_timelines[drawable.id].append(
                    event.start_time
                )  # assume created at the beginning of deletion event

            self.object_timelines[drawable.id].append(event.end_time)

    def get_current_time(self) -> float:
        """Returns the end time of the latest event in the scene, or 0.0 if empty."""
        t = 0.0
        if self.events:
            t = max(t, max(event.end_time for event, _ in self.events))
        if self.camera_events:
            t = max(t, max(event.end_time for event in self.camera_events))
        return t

    def wait(self, duration: float) -> float:
        """Insert a pause of `duration` seconds after the current last event.

        Returns the time at which the next event should start.

        Usage::

            scene.add(SketchAnimation(start_time=0, duration=2), rect)
            t = scene.wait(1.0)  # t = 3.0
            scene.add(SketchAnimation(start_time=t, duration=2), circle)
        """
        return self.get_current_time() + duration

    def add_camera(self, event) -> None:
        """
        Register a CameraAnimation that controls the viewport over time.

        Camera events are kept separate from drawable events and are applied
        per-frame in the render loop without touching any drawable's OpsSet.

        Args:
            event: A CameraAnimation instance (or any object with an
                   apply_to_viewport(viewport, progress) method).
        """
        self.camera_events.append(event)

    def _get_viewport_at(self, t: float) -> Viewport:
        """
        Return the viewport state at time t by replaying all camera events.

        Events are processed in start-time order.  Each completed event advances
        the running viewport state to its target; an in-progress event interpolates
        from the current state toward its target.  If from_xrange / from_yrange are
        not specified on an event, the camera starts from wherever it currently is.

        Args:
            t: Time in seconds.

        Returns:
            A Viewport instance representing the camera position at time t.
        """
        if not self.camera_events:
            return self.viewport

        sorted_events = sorted(self.camera_events, key=lambda e: e.start_time)
        current = self.viewport

        for event in sorted_events:
            if t < event.start_time:
                break  # sorted — nothing later will have started either
            raw_progress = (
                np.clip((t - event.start_time) / event.duration, 0.0, 1.0)
                if event.duration > 0
                else 1.0
            )
            progress = event.easing_fun(raw_progress) if event.easing_fun else raw_progress
            current = event.apply_to_viewport(current, progress)

        return current

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
        active_list: list[str] = []
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

    def find_key_frames(self):
        """
        Find the key frames that we need to calculate for the animation
        Key frames are the frames where an object is created or deleted
        """
        event_drawable_ids = sorted(self.events, key=lambda x: x[0].start_time)
        events = [event for event, _ in event_drawable_ids]
        drawable_events_mapping: dict[str, list[AnimationEvent]] = (
            {}
        )  # track for each drawable, what all events are applied
        for event, drawable_id in event_drawable_ids:
            if drawable_id not in drawable_events_mapping:
                drawable_events_mapping[drawable_id] = [event]
            else:
                drawable_events_mapping[drawable_id].append(event)
        key_frames = [event.start_time for event in events] + [event.end_time for event in events]
        key_frames = list(set(key_frames))
        key_frames.sort()
        return key_frames, drawable_events_mapping

    def get_object_event_and_progress(
        self, object_id: str, t: int, drawable_events_mapping: dict[str, list[AnimationEvent]]
    ) -> list[tuple[AnimationEvent, float]]:
        object_drawable: Drawable = self.drawable_cache.get_drawable(object_id)
        event_and_progress = []
        for event in drawable_events_mapping.get(object_id, []):
            if object_drawable.glow_dot_hint:
                event.data["glowing_dot"] = object_drawable.glow_dot_hint
            if event.end_time <= t / self.fps:
                event_and_progress.append((event, 1.0))  # add completed event
            elif event.start_time <= t / self.fps:
                # event has started, but not completed yet
                progress = np.clip(
                    (t / self.fps - event.start_time) / event.duration,
                    0,
                    1,
                )
                event_and_progress.append((event, progress))
        return event_and_progress

    def get_animated_opsset_at_time(
        self,
        drawable_id: str,
        t: int,
        event_and_progress: list[tuple[AnimationEvent, float]],
        drawable_events_mapping: dict[str, list[AnimationEvent]],
    ) -> OpsSet:
        # look at the last event, which if completed, will be tracked from cache
        if len(event_and_progress) == 0:
            return self.drawable_cache.get_drawable_opsset(drawable_id)
        elif event_and_progress[-1][1] == 1:
            if self.drawable_cache.exists_in_cache(drawable_id, event_and_progress[-1][0].id):
                return self.drawable_cache.get_drawable_opsset(drawable_id, event_and_progress[-1][0].id)

        if len(event_and_progress) > 1:
            opsset = self.get_animated_opsset_at_time(
                drawable_id, t, event_and_progress[:-1], drawable_events_mapping
            )  # everything except the last event
        else:
            opsset = self.drawable_cache.get_drawable_opsset(drawable_id)  # get the initial draw opsset

        # now we need to apply the last transformation only
        event, progress = event_and_progress[-1]
        group_id = event.data.get("apply_to_group", None)
        if group_id is None:
            # simple animation, just apply the opsset blindly
            opsset = event.apply(opsset, progress)
        else:
            # this is a group animation

            # first check if the transformed cached key exist already
            group_opsset = self.frame_cache.get_transformed(group_id, event.id, progress)
            if group_opsset is None:
                # the transformed key does not exist, how about initial cache?
                group_opsset = self.frame_cache.get_pretransform(group_id, event.id)

                if group_opsset is None:
                    # calculate the group opsset for group level animation
                    group = self.drawable_groups[group_id]  # get the drawable group
                    group_opsset = OpsSet(initial_set=[])
                    for elem in group.elements:
                        # for each element of the group, we need to figure out its animated opsset at time before the current event
                        filtered_elem_events = []
                        elem_event_and_progress = self.get_object_event_and_progress(
                            elem.id, t, drawable_events_mapping
                        )
                        for elem_event, elem_progress in elem_event_and_progress:
                            if elem_event.id == event.id:
                                break
                            filtered_elem_events.append(
                                (elem_event, elem_progress)
                            )  # keep appending until we reach the current event

                        elem_opsset = self.get_animated_opsset_at_time(
                            elem.id, t, filtered_elem_events, drawable_events_mapping
                        )

                        # append meta to track individual elements of the group later
                        elem_opsset.add_meta({"drawable_element_id": elem.id})
                        group_opsset.extend(elem_opsset)

                    # store in cache to be reused
                    self.frame_cache.set_pretransform(group_id, event.id, group_opsset)

                # here, we need to apply the group transformation
                group_opsset = event.apply(group_opsset, progress)
                self.frame_cache.set_transformed(group_id, event.id, progress, group_opsset)  # write back to the cache

            # now filter for the current drawable's opsset only
            opsset = group_opsset.filter_by_meta_query("drawable_element_id", drawable_id)

        if progress == 1:
            if not self.drawable_cache.exists_in_cache(drawable_id, event.id):
                self.drawable_cache.set_drawable_event_opsset(
                    drawable_id, event.id, opsset
                )  # save to cache for last event if progress = 1

        return opsset

    def create_event_timeline(self, max_length: float | None = None):
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
        scene_opsset_list: list[OpsSet] = []
        current_active_objects: list[str] = []

        # start calculating with a progress bar
        frame_count = int(np.round(max_length * self.fps))
        for t in tqdm(range(0, frame_count + 1), desc="Calculating animation frames..."):
            frame_opsset = OpsSet(initial_set=[])  # initialize with blank opsset, will add more

            # for each frame, update the current active objects if it is a keyframe
            if t in key_frame_indices:
                current_active_objects = self.get_active_objects(t / self.fps)

            # for each of these active objects, calculate what all events need to apply upto which progress
            self.frame_cache.reset()  # reset this cache for each frame
            for object_id in current_active_objects:
                event_and_progress = self.get_object_event_and_progress(object_id, t, drawable_events_mapping)

                # if all animations are complete for this object, we can draw from cache
                all_complete = event_and_progress and all([p == 1.0 for _, p in event_and_progress])
                last_event_id = event_and_progress[-1][0].id

                if all_complete and self.drawable_cache.exists_in_cache(object_id, last_event_id):
                    # a fully completed animation list exists in cache now, can fetch from last event's drawable
                    animated_opsset = self.drawable_cache.get_drawable_opsset(object_id, last_event_id)
                else:
                    # now we have all the events, so get the animated opsset
                    animated_opsset = self.get_animated_opsset_at_time(
                        drawable_id=object_id,
                        t=t,
                        event_and_progress=event_and_progress,
                        drawable_events_mapping=drawable_events_mapping,
                    )
                frame_opsset.extend(animated_opsset)
            scene_opsset_list.append(frame_opsset)  # create the list of ops at scene
        return scene_opsset_list

    def render_snapshot(
        self,
        output_path: str,
        frame_in_seconds: float,
        max_length: float | None = None,
    ):
        """Render a snapshot of the animation at a specific time point as an SVG or PDF file.

        Args:
            output_path (str): Path to the output file (.svg or .pdf).
            frame_in_seconds (float): The exact time point (in seconds) to render.
            max_length (Optional[float], optional): Total duration of the animation. Defaults to None.
        """
        opsset_list = self.create_event_timeline(max_length)
        frame_index = int(np.clip(np.round(frame_in_seconds * self.fps), 0, len(opsset_list) - 1))
        self._render_frame(opsset_list[frame_index], output_path, frame_in_seconds)

    def export_storyboard(
        self,
        n_frames: int,
        output_dir: str,
        format: str = "svg",
        max_length: float | None = None,
    ) -> list[str]:
        """Export evenly-spaced keyframes as a storyboard.

        Args:
            n_frames: Number of frames to export.
            output_dir: Directory to write output files.
            format: "svg" or "pdf".
            max_length: Total animation duration override.

        Returns:
            List of output file paths.
        """
        os.makedirs(output_dir, exist_ok=True)
        opsset_list = self.create_event_timeline(max_length)
        total_frames = len(opsset_list)
        total_duration = total_frames / self.fps
        times = [i * total_duration / (n_frames - 1) for i in range(n_frames)] if n_frames > 1 else [0.0]
        paths = []
        for i, t in enumerate(times):
            frame_index = int(np.clip(np.round(t * self.fps), 0, total_frames - 1))
            filename = f"storyboard_{i:03d}_{t:.2f}.{format}"
            output_path = os.path.join(output_dir, filename)
            self._render_frame(opsset_list[frame_index], output_path, t)
            paths.append(output_path)
        return paths

    def _render_frame(self, frame_ops: OpsSet, output_path: str, frame_in_seconds: float):
        """Render a single frame OpsSet to an SVG or PDF file based on the file extension."""
        ext = os.path.splitext(output_path)[1].lower()
        if ext == ".pdf":
            surface = cairo.PDFSurface(output_path, self.width, self.height)
        else:
            surface = cairo.SVGSurface(output_path, self.width, self.height)
        ctx = cairo.Context(surface)
        if self.background_color is not None:
            ctx.set_source_rgb(*self.background_color)
        ctx.paint()
        self._get_viewport_at(frame_in_seconds).apply_to_context(ctx)
        frame_ops.render(ctx)
        surface.finish()

    def render_keyframes(
        self,
        times: list[float],
        output_dir: str,
        format: str = "svg",
        prefix: str = "frame",
        max_length: float | None = None,
    ) -> list[str]:
        """Batch export snapshots at multiple timestamps.

        Computes the event timeline once, then renders each requested frame.

        Args:
            times: List of timestamps (in seconds) to export.
            output_dir: Directory to write output files.
            format: "svg" or "pdf".
            prefix: Filename prefix; files are named {prefix}_{i:03d}_{time:.2f}.{format}.
            max_length: Total animation duration override.

        Returns:
            List of output file paths.
        """
        os.makedirs(output_dir, exist_ok=True)
        opsset_list = self.create_event_timeline(max_length)
        paths = []
        for i, t in enumerate(times):
            frame_index = int(np.clip(np.round(t * self.fps), 0, len(opsset_list) - 1))
            filename = f"{prefix}_{i:03d}_{t:.2f}.{format}"
            output_path = os.path.join(output_dir, filename)
            self._render_frame(opsset_list[frame_index], output_path, t)
            paths.append(output_path)
        return paths

    def render_handout(
        self,
        output_path: str,
        n_frames: int = 6,
        times: list[float] | None = None,
        max_length: float | None = None,
    ) -> str:
        """Render a single multi-page PDF with one animation frame per page.

        Either provide explicit `times` or let `n_frames` evenly-spaced keyframes
        be chosen automatically.

        Args:
            output_path: Path to the output PDF file.
            n_frames: Number of evenly-spaced frames (ignored if `times` is given).
            times: Explicit list of timestamps (in seconds) to render.
            max_length: Total animation duration override.

        Returns:
            The output file path.
        """
        opsset_list = self.create_event_timeline(max_length)
        total_frames = len(opsset_list)
        total_duration = total_frames / self.fps
        if times is None:
            times = [i * total_duration / (n_frames - 1) for i in range(n_frames)] if n_frames > 1 else [0.0]

        surface = cairo.PDFSurface(output_path, self.width, self.height)
        for t in times:
            frame_index = int(np.clip(np.round(t * self.fps), 0, total_frames - 1))
            ctx = cairo.Context(surface)
            if self.background_color is not None:
                ctx.set_source_rgb(*self.background_color)
            ctx.paint()
            self._get_viewport_at(t).apply_to_context(ctx)
            opsset_list[frame_index].render(ctx)
            surface.show_page()
        surface.finish()
        return output_path

    def render(self, output_path: str, max_length: float | None = None):
        """
        Render the animation as a video file.

        This method generates a video by creating a timeline of animation events
        and rendering each frame using Cairo graphics. The video is saved to the
        specified output path with the configured frame rate.

        Args:
            output_path (str): Path to save the output video file.
            max_length (Optional[float], optional): Maximum duration of the animation. Defaults to None.
        """
        # calculate the events
        opsset_list = self.create_event_timeline(max_length)
        output_file_ext = os.path.basename(output_path).split(os.path.extsep)[-1]
        if output_file_ext.lower() == "gif":
            tqdm_desc = "Rendering GIF..."
            write_obj = imageio.get_writer(output_path, mode="I", duration=max_length)
        else:
            tqdm_desc = "Rendering video..."
            write_obj = imageio.get_writer(output_path, fps=self.fps, codec="libx264")

        with write_obj as writer:
            for i, frame_ops in enumerate(tqdm(opsset_list, desc=tqdm_desc)):
                surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
                ctx = cairo.Context(surface)  # create cairo context

                # optional background
                if self.background_color is not None:
                    ctx.set_source_rgb(*self.background_color)
                ctx.paint()

                self._get_viewport_at(i / self.fps).apply_to_context(ctx)
                frame_ops.render(ctx)  # applies the operations to cairo context

                frame_np = cairo_surface_to_numpy(surface)
                writer.append_data(frame_np)  # type: ignore[attr-defined]
