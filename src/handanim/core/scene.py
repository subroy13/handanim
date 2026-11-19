import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import imageio.v2 as imageio
import numpy as np
from tqdm import tqdm

from ..utils.geometry import cairo_surface_to_numpy
from ._cairo import cairo
from .animation import AnimationEvent, AnimationEventType, CompositeAnimationEvent
from .cache import DrawableCache, GroupFrameCache
from .draw_ops import Ops, OpsSet
from .drawable import Drawable, DrawableGroup
from .viewport import Viewport


class _OverlayLayer:
    """Camera-independent foreground overlay layer proxy attached to a `Scene`.

    Objects added via `scene.overlay.add(...)` are rendered using the scene's
    base static viewport above the world canvas rather than the camera-animated
    viewport, so HUD elements, timers, logos, and captions stay fixed on screen
    during `CameraAnimation` pan/zoom and across `SceneTransition` page turns.
    """

    def __init__(self, scene: "Scene") -> None:
        self._scene = scene

    def add(
        self,
        event: AnimationEvent | Drawable,
        drawable: Drawable | None = None,
    ) -> Drawable | None:
        return self._scene.add(event, drawable, overlay=True)

    def swap(
        self,
        source: Drawable,
        target: Drawable,
        start_time: float = 0.0,
        duration: float = 0.0,
        easing_fun=None,
    ) -> None:
        self._scene.swap(
            source,
            target,
            start_time=start_time,
            duration=duration,
            easing_fun=easing_fun,
            overlay=True,
        )


class _BackgroundLayer:
    """Camera-independent background layer proxy attached to a `Scene`.

    Objects added via `scene.background.add(...)` are rendered using the scene's
    base static viewport underneath the world canvas, remaining unaffected by
    `CameraAnimation` pan/zoom and `SceneTransition` page turns. Ideal for
    paper grids, watermarks, background logos, and ambient progress/timer rings.
    """

    def __init__(self, scene: "Scene") -> None:
        self._scene = scene

    def add(
        self,
        event: AnimationEvent | Drawable,
        drawable: Drawable | None = None,
    ) -> Drawable | None:
        return self._scene.add(event, drawable, background=True)

    def swap(
        self,
        source: Drawable,
        target: Drawable,
        start_time: float = 0.0,
        duration: float = 0.0,
        easing_fun=None,
    ) -> None:
        self._scene.swap(
            source,
            target,
            start_time=start_time,
            duration=duration,
            easing_fun=easing_fun,
            background=True,
        )


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
        narration: Any = None,
        audio: Any = None,
        background_music: Any = None,
        music_volume: float = 0.18,
        music_loop: bool = True,
        sketch_sound: bool | float = False,
        sketch_sound_volume: float = 0.25,
        sketch_sound_style: str = "chalk",
        eraser_sound: bool | float = False,
        eraser_sound_volume: float = 0.45,
        transition_sound: bool | float = False,
        transition_sound_volume: float = 0.45,
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.background_color = background_color
        self.drawable_cache = DrawableCache(background_color=background_color)
        self.frame_cache = GroupFrameCache()
        self.events: list[tuple[AnimationEvent, str]] = []
        self.object_timelines: dict[str, list[float]] = {}
        self._auto_created_times: dict[str, float] = {}
        self.drawable_groups: dict[str, DrawableGroup] = {}  # stores drawable groups present in the scene
        self.camera_events: list = []  # CameraAnimation events; typed as List to avoid circular import
        self.transitions: list = []  # SceneTransition events
        self.beats: list = []  # BeatContext instances registered via `with scene.beat(...)`
        self._beat_cursor: float = 0.0
        self.background_drawable_ids: set[str] = set()
        self.overlay_drawable_ids: set[str] = set()
        self.background = _BackgroundLayer(self)
        self.overlay = _OverlayLayer(self)
        self.narration: Any = narration if narration is not None else audio
        self.background_music: Any = background_music
        self.music_volume: float = float(music_volume)
        self.music_loop: bool = bool(music_loop)
        if isinstance(sketch_sound, (int, float)) and not isinstance(sketch_sound, bool):
            self.sketch_sound = float(sketch_sound) > 0.0
            self.sketch_sound_volume = max(0.0, float(sketch_sound))
        else:
            self.sketch_sound = bool(sketch_sound)
            self.sketch_sound_volume = max(0.0, float(sketch_sound_volume))
        self.sketch_sound_style: str = str(sketch_sound_style)
        if isinstance(eraser_sound, (int, float)) and not isinstance(eraser_sound, bool):
            self.eraser_sound = float(eraser_sound) > 0.0
            self.eraser_sound_volume = max(0.0, float(eraser_sound))
        else:
            self.eraser_sound = bool(eraser_sound)
            self.eraser_sound_volume = max(0.0, float(eraser_sound_volume))
        if isinstance(transition_sound, (int, float)) and not isinstance(transition_sound, bool):
            self.transition_sound = float(transition_sound) > 0.0
            self.transition_sound_volume = max(0.0, float(transition_sound_volume))
        else:
            self.transition_sound = bool(transition_sound)
            self.transition_sound_volume = max(0.0, float(transition_sound_volume))

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
        event: AnimationEvent | Drawable,
        drawable: Drawable | None = None,
        *,
        overlay: bool = False,
        background: bool = False,
    ):
        """
        Adds an animation event to a drawable primitive in the scene.

        Handles different scenarios including:
        - Self-driving drawables such as `Captions`, `CountdownTimer`, `ProgressBar`, or `TimeDrivenDrawable`
        - `Swap(a, b, t)` events (e.g. `scene.add(Swap(a, b, t))`)
        - Composite animation events (recursively adding sub-events)
        - Drawable groups with parallel or sequential event distribution
        - Single event and drawable cases

        Manages event tracking, drawable caching, and object timelines.

        Args:
            event (AnimationEvent | Drawable): The animation event (or self-driving drawable) to be added.
            drawable (Drawable, optional): The drawable primitive to apply the event to.
            overlay (bool, optional): If True, renders the drawable in the camera-independent foreground overlay layer.
            background (bool, optional): If True, renders the drawable in the camera-independent background layer.
        """
        from ..animations.camera import CameraAnimation
        from ..animations.fade import FadeInAnimation, FadeOutAnimation
        from ..animations.transitions import SceneTransition
        from ..animations.visibility import Hide, Show, Swap
        from ..primitives.captions import Captions

        if isinstance(event, SceneTransition):
            self.add_transition(event)
            return
        if isinstance(event, CameraAnimation):
            self.add_camera(event)
            return

        if drawable is None and hasattr(event, "to_event") and callable(event.to_event):
            drawable = event  # type: ignore[assignment]
            event = drawable.to_event()  # type: ignore[attr-defined]

        if isinstance(event, Swap):
            if event.duration > 0.0:
                self.add(
                    FadeOutAnimation(
                        start_time=event.start_time,
                        duration=event.duration,
                        easing_fun=event.easing_fun,
                    ),
                    event.source,
                    overlay=overlay,
                    background=background,
                )
                self.add(
                    FadeInAnimation(
                        start_time=event.start_time,
                        duration=event.duration,
                        easing_fun=event.easing_fun,
                    ),
                    event.target,
                    overlay=overlay,
                    background=background,
                )
            else:
                self.add(Hide(start_time=event.start_time), event.source, overlay=overlay, background=background)
                self.add(Show(start_time=event.start_time), event.target, overlay=overlay, background=background)
            return

        if not isinstance(event, AnimationEvent):
            raise TypeError(f"Expected AnimationEvent, got {type(event).__name__}")
        if drawable is None:
            raise ValueError("`drawable` is required when adding a standard AnimationEvent")

        if isinstance(drawable, Captions):
            center_x = (self.viewport.world_xrange[0] + self.viewport.world_xrange[1]) / 2.0
            drawable.set_default_x(center_x)

        # handle the case for composite events if any
        if isinstance(event, CompositeAnimationEvent):
            for sub_event in event.events:
                self.add(sub_event, drawable, overlay=overlay, background=background)  # recursively call add() for the subevents
            return drawable

        if isinstance(drawable, DrawableGroup):
            # drawable group are usually a syntactic sugar for applying the event to its elements
            if drawable.grouping_method == "series":
                # Apply the event sequentially to each element in the group
                segmented_events = event.subdivide(len(drawable.elements))
                for sub_drawable, segment_event in zip(drawable.elements, segmented_events, strict=False):
                    # recursively call add(), but with the duration modified appropriately
                    self.add(event=segment_event, drawable=sub_drawable, overlay=overlay, background=background)
                return drawable
            elif drawable.grouping_method == "parallel":
                # group does not have any drawable opsset, so it is not in cache
                # but group_memberships are useful to calculate the opsset on which events get applied.
                if drawable.id not in self.drawable_groups:
                    self.drawable_groups[drawable.id] = drawable
                event.data["apply_to_group"] = drawable.id  # add more context to the event with the group_id
                for elem in drawable.elements:
                    self.add(event, elem, overlay=overlay, background=background)

                return drawable

        else:
            # single simple drawable
            self.drawable_cache.background_color = self.background_color
            if hasattr(drawable, "objects_to_erase"):
                drawable.drawable_cache = self.drawable_cache  # type: ignore[attr-defined]
            self.drawable_cache.set_drawable_opsset(drawable)
            self.drawable_cache.drawables[drawable.id] = drawable

        if overlay:
            self.overlay_drawable_ids.add(drawable.id)
        if background:
            self.background_drawable_ids.add(drawable.id)

        # Initialize timeline for the new drawable
        if drawable.id not in self.object_timelines:
            self.object_timelines[drawable.id] = []

        self.events.append((event, drawable.id))

        if event.type is AnimationEventType.CREATION:
            if drawable.id in self._auto_created_times:
                auto_time = self._auto_created_times.pop(drawable.id)
                if auto_time in self.object_timelines[drawable.id]:
                    self.object_timelines[drawable.id].remove(auto_time)
            if hasattr(drawable, "objects_to_erase"):
                self.object_timelines[drawable.id].append(event.start_time)
                self.object_timelines[drawable.id].append(event.end_time)
                for target in self._iter_erased_drawables(drawable.objects_to_erase):
                    if target.id not in self.object_timelines:
                        self.object_timelines[target.id] = []
                    if len(self.object_timelines[target.id]) == 0:
                        self.object_timelines[target.id].append(event.start_time)
                        self._auto_created_times[target.id] = event.start_time
                    self.object_timelines[target.id].append(event.end_time)
                    self.object_timelines[target.id].sort()
            else:
                self.object_timelines[drawable.id].sort()
                if len(self.object_timelines[drawable.id]) % 2 == 1:
                    self.object_timelines[drawable.id][-1] = min(
                        self.object_timelines[drawable.id][-1], event.start_time
                    )
                else:
                    self.object_timelines[drawable.id].append(event.start_time)
        elif event.type is AnimationEventType.DELETION:
            # any object cannot be deleted without being created
            if len(self.object_timelines[drawable.id]) == 0:
                self.object_timelines[drawable.id].append(
                    event.start_time
                )  # assume created at the beginning of deletion event
                self._auto_created_times[drawable.id] = event.start_time

            self.object_timelines[drawable.id].append(event.end_time)
        elif event.type is AnimationEventType.MUTATION:
            if len(self.object_timelines[drawable.id]) == 0:
                self.object_timelines[drawable.id].append(event.start_time)
                self._auto_created_times[drawable.id] = event.start_time

        self.object_timelines[drawable.id].sort()
        return drawable

    def swap(
        self,
        source: Drawable,
        target: Drawable,
        start_time: float = 0.0,
        duration: float = 0.0,
        easing_fun=None,
        *,
        overlay: bool = False,
        background: bool = False,
    ) -> None:
        """Atomically hide `source` and show `target` at `start_time` (or cross-fade if `duration > 0`)."""
        from ..animations.visibility import Swap

        self.add(
            Swap(source, target, start_time=start_time, duration=duration, easing_fun=easing_fun),
            overlay=overlay,
            background=background,
        )

    def _iter_erased_drawables(self, drawables: Sequence[Drawable]) -> list[Drawable]:
        result: list[Drawable] = []
        for item in drawables:
            if isinstance(item, DrawableGroup):
                result.extend(self._iter_erased_drawables(item.elements))
            else:
                result.append(item)
        return result

    def get_current_time(self) -> float:
        """Returns the end time of the latest event or beat cursor in the scene, or 0.0 if empty."""
        t = float(self._beat_cursor)
        if self.events:
            t = max(t, max(event.end_time for event, _ in self.events))
        if self.camera_events:
            t = max(t, max(event.end_time for event in self.camera_events))
        if self.transitions:
            t = max(t, max(tr.end_time for tr in self.transitions))
        return t

    def wait(self, duration: float) -> float:
        """Insert a pause of `duration` seconds after the current last event.

        Returns the time at which the next event should start.

        Usage::

            scene.add(SketchAnimation(start_time=0, duration=2), rect)
            t = scene.wait(1.0)  # t = 3.0
            scene.add(SketchAnimation(start_time=t, duration=2), circle)
        """
        new_t = self.get_current_time() + duration
        self._beat_cursor = max(self._beat_cursor, new_t)
        return new_t

    def beat(
        self,
        name: str = "",
        narration: Any = None,
        duration: float | None = None,
        start_time: float | None = None,
        pad_before: float = 0.0,
        pad_after: float = 0.3,
        transition_on_exit: Any = None,
    ):
        """Open a voice-driven `BeatContext` block for relative timeline authoring.

        Usage::

            with scene.beat("Intro", narration=clip1, pad_after=0.4) as b:
                b.sketch(title, at=0.0, duration=1.0)
                b.sketch(diagram, word="triangle", duration=1.5, clear_on_exit=True)
        """
        from .beat import BeatContext

        return BeatContext(
            scene=self,
            name=name,
            narration=narration,
            duration=duration,
            start_time=start_time,
            pad_before=pad_before,
            pad_after=pad_after,
            transition_on_exit=transition_on_exit,
        )

    def get_stitched_narration(self, output_path: str | Path | None = None):
        """Stitch all narration `AudioClip`s attached to `scene.beat(...)` blocks into a single master `AudioClip`."""
        from voiceanim.schema import AudioClip, NarrationBeat, WordTimestamp
        from voiceanim.timeline import VoiceTimelineSync

        narration_beats: list[NarrationBeat] = []
        dict_words: list[WordTimestamp] = []
        max_end = 0.0

        for idx, b in enumerate(self.beats):
            if b.narration is None:
                continue
            clip_obj: AudioClip | None = None
            if isinstance(b.narration, AudioClip):
                clip_obj = b.narration
            elif isinstance(b.narration, dict):
                clip_obj = AudioClip.from_dict(b.narration)

            if clip_obj is not None:
                max_end = max(max_end, b.start + clip_obj.duration)
                if clip_obj.audio_path and os.path.exists(clip_obj.audio_path):
                    narration_beats.append(
                        NarrationBeat(
                            id=b.name or f"beat_{idx + 1}",
                            text=clip_obj.text,
                            start_time=b.start,
                            target_duration=b.effective_duration,
                            clip=clip_obj,
                        )
                    )
                else:
                    for w in clip_obj.words:
                        dict_words.append(
                            WordTimestamp(
                                word=w.word,
                                start=round(w.start + b.start, 3),
                                end=round(w.end + b.start, 3),
                                confidence=w.confidence,
                                speaker=w.speaker,
                            )
                        )

        if narration_beats:
            if output_path is None:
                import tempfile

                fd, tmp_wav = tempfile.mkstemp(prefix="handanim_beats_", suffix=".wav")
                os.close(fd)
                output_path = tmp_wav
            total_dur = max(self.get_current_time(), max_end)
            return VoiceTimelineSync.stitch_narration_beats(
                narration_beats,
                output_path=output_path,
                total_duration=total_dur,
            )

        if dict_words:
            return AudioClip(
                audio_path="",
                duration=round(max(self.get_current_time(), max_end), 3),
                words=dict_words,
                provider="beats",
                voice="mixed",
            )
        return None

    def add_beat_captions(self, **caption_kwargs: Any):
        """Create and attach a `Captions` drawable on `scene.overlay` from all `scene.beat()` narrations."""
        from ..primitives.captions import Captions

        stitched = self.get_stitched_narration()
        if stitched is None:
            return None
        captions = Captions(stitched, **caption_kwargs)
        self.overlay.add(captions)
        return captions

    @staticmethod
    def place_relative(
        target: "Drawable",
        reference: "Drawable",
        target_anchor: str = "center",
        reference_anchor: str = "center",
        offset: tuple[float, float] = (0.0, 0.0),
    ) -> "Drawable":
        """Position `target` so that its anchor aligns with a reference drawable's anchor.

        Returns the translated target — does not mutate the original (consistent with
        the immutability invariant).

        Args:
            target: The drawable to reposition.
            reference: The drawable to align against.
            target_anchor: Anchor name on the target (e.g. "top_left", "center").
            reference_anchor: Anchor name on the reference.
            offset: Additional (dx, dy) offset after alignment.

        Usage::

            label = Text("hello", position=(0, 0))
            label = Scene.place_relative(label, rect, "top", "bottom", offset=(0, -20))
        """
        ref_point = reference.anchor(reference_anchor)
        tgt_point = target.anchor(target_anchor)
        dx = ref_point[0] - tgt_point[0] + offset[0]
        dy = ref_point[1] - tgt_point[1] + offset[1]
        return target.translate(dx, dy)

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

    def add_transition(self, transition) -> None:
        """Register a `SceneTransition` (such as `PageTurnTransition` or `PaperCrumpleTransition`).

        Transitions fold or crumple all world-space drawables created before
        `transition.start_time`, revealing a fresh page underneath and automatically
        deactivating the previous page's world drawables once `transition.end_time`
        is reached. Overlay drawables (`scene.overlay`) remain unaffected.
        """
        self.transitions.append(transition)
        self.transitions.sort(key=lambda tr: tr.start_time)

    def _get_last_shown_time(self, object_id: str, t: float) -> float:
        """Return the latest timestamp <= t at which `object_id` became active."""
        active = False
        last_shown = 0.0
        for time in sorted(self.object_timelines.get(object_id, [])):
            if t >= time:
                active = not active
                if active:
                    last_shown = float(time)
            else:
                break
        return last_shown

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
        alternates with each subsequent time point. World-space objects whose latest creation
        preceded a completed `SceneTransition` (`last_shown_time < tr.start_time` and
        `t >= tr.end_time`) are automatically deactivated.

        Args:
            t (float): The time point (in seconds) to check object activity.

        Returns:
            List[str]: A list of object IDs that are active at the given time point.
        """
        active_list: list[str] = []
        for object_id in self.object_timelines:
            active = False  # everything starts with blank screen
            last_shown = 0.0
            for time in sorted(self.object_timelines[object_id]):
                if t >= time:
                    active = not active  # switch status
                    if active:
                        last_shown = float(time)
                else:
                    # time has increased beyond t
                    break
            if (
                active
                and self.transitions
                and object_id not in self.overlay_drawable_ids
                and object_id not in self.background_drawable_ids
            ):
                if any(tr.start_time > last_shown and t >= tr.end_time for tr in self.transitions):
                    active = False
            if active:
                active_list.append(object_id)
        return active_list

    def find_key_frames(self) -> tuple[list[float], dict[str, list[AnimationEvent]]]:
        """
        Find the key frames that we need to calculate for the animation
        Key frames are the frames where an object is created or deleted
        """
        from ..animations.pose import PoseAnimation

        event_drawable_ids = sorted(
            self.events,
            key=lambda x: (
                0 if isinstance(x[0], PoseAnimation) else 1,
                x[0].start_time,
                x[0].end_time,
                0 if x[0].type is AnimationEventType.DELETION else 1,
            ),
        )
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
        if self.transitions:
            key_frames.extend([tr.start_time for tr in self.transitions])
            key_frames.extend([tr.end_time for tr in self.transitions])
        key_frames = list(set(key_frames))
        key_frames.sort()
        return key_frames, drawable_events_mapping

    def get_object_event_and_progress(
        self, object_id: str, t: int, drawable_events_mapping: dict[str, list[AnimationEvent]]
    ) -> list[tuple[AnimationEvent, float]]:
        object_drawable: Drawable = self.drawable_cache.get_drawable(object_id)
        t_sec = t / self.fps
        event_and_progress = []
        for event in drawable_events_mapping.get(object_id, []):
            event.data["current_time"] = t_sec
            if object_drawable.glow_dot_hint:
                event.data["glowing_dot"] = object_drawable.glow_dot_hint
            if event.end_time <= t_sec:
                event_and_progress.append((event, 1.0))  # add completed event
            elif event.start_time <= t_sec:
                # event has started, but not completed yet
                progress = np.clip(
                    (t_sec - event.start_time) / event.duration,
                    0,
                    1,
                )
                event_and_progress.append((event, progress))
        return event_and_progress

    def _is_time_varying_drawable(self, drawable_id: str) -> bool:
        drawable = self.drawable_cache.drawables.get(drawable_id)
        if drawable is None:
            return False
        if getattr(drawable, "is_time_driven", False):
            return True
        if hasattr(drawable, "draw_with_pose") and callable(drawable.draw_with_pose):
            return True
        return False

    def get_animated_opsset_at_time(
        self,
        drawable_id: str,
        t: int,
        event_and_progress: list[tuple[AnimationEvent, float]],
        drawable_events_mapping: dict[str, list[AnimationEvent]],
    ) -> OpsSet:
        is_time_varying = self._is_time_varying_drawable(drawable_id)
        all_complete = len(event_and_progress) > 0 and all(p == 1.0 for _, p in event_and_progress)

        # look at the last event, which if completed (and all prior events are completed), will be tracked from cache
        if len(event_and_progress) == 0:
            drawable = self.drawable_cache.drawables.get(drawable_id)
            if is_time_varying and drawable is not None and hasattr(drawable, "draw_with_pose"):
                return drawable.draw_with_pose(time=t / self.fps)
            return self.drawable_cache.get_drawable_opsset(drawable_id)
        elif all_complete and not is_time_varying:
            if self.drawable_cache.exists_in_cache(drawable_id, event_and_progress[-1][0].id):
                return self.drawable_cache.get_drawable_opsset(drawable_id, event_and_progress[-1][0].id)

        if len(event_and_progress) > 1:
            opsset = self.get_animated_opsset_at_time(
                drawable_id, t, event_and_progress[:-1], drawable_events_mapping
            )  # everything except the last event
        else:
            drawable = self.drawable_cache.drawables.get(drawable_id)
            if is_time_varying and drawable is not None and hasattr(drawable, "draw_with_pose"):
                opsset = drawable.draw_with_pose(time=t / self.fps)
            else:
                opsset = self.drawable_cache.get_drawable_opsset(drawable_id)  # get the initial draw opsset

        # now we need to apply the last transformation only
        event, progress = event_and_progress[-1]
        if event.type is AnimationEventType.CREATION:
            from ..animations.fade import FadeInAnimation
            from ..animations.visibility import restore_base_opacity

            if not isinstance(event, FadeInAnimation):
                opsset = restore_base_opacity(opsset)
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

        if all_complete and not is_time_varying:
            if not self.drawable_cache.exists_in_cache(drawable_id, event.id):
                self.drawable_cache.set_drawable_event_opsset(
                    drawable_id, event.id, opsset
                )  # save to cache only when all events up to this point are completed

        return opsset

    def _compute_frame_opsset(
        self,
        t: int,
        drawable_events_mapping: dict[str, list[AnimationEvent]],
    ) -> OpsSet:
        """Compute the `OpsSet` for a single frame index `t` (`t_sec = t / self.fps`)."""
        frame_opsset = OpsSet(initial_set=[])
        t_sec = t / self.fps

        current_active_objects = self.get_active_objects(t_sec)
        background_objects = [oid for oid in current_active_objects if oid in self.background_drawable_ids]
        world_objects = [
            oid
            for oid in current_active_objects
            if oid not in self.overlay_drawable_ids and oid not in self.background_drawable_ids
        ]
        overlay_objects = [oid for oid in current_active_objects if oid in self.overlay_drawable_ids]

        active_tr = None
        if self.transitions:
            active_trs = [
                tr for tr in self.transitions if tr.start_time <= t_sec < tr.end_time and tr.duration > 0
            ]
            if active_trs:
                active_tr = active_trs[-1]

        self.frame_cache.reset()
        background_frame_ops = OpsSet(initial_set=[])
        outgoing_world_ops = OpsSet(initial_set=[])
        incoming_world_ops = OpsSet(initial_set=[])
        overlay_frame_ops = OpsSet(initial_set=[])

        for object_id in background_objects + world_objects + overlay_objects:
            event_and_progress = self.get_object_event_and_progress(object_id, t, drawable_events_mapping)
            is_time_varying = self._is_time_varying_drawable(object_id)

            all_complete = event_and_progress and all([p == 1.0 for _, p in event_and_progress])
            last_event_id = event_and_progress[-1][0].id if event_and_progress else None

            if (
                all_complete
                and not is_time_varying
                and last_event_id is not None
                and self.drawable_cache.exists_in_cache(object_id, last_event_id)
            ):
                animated_opsset = self.drawable_cache.get_drawable_opsset(object_id, last_event_id)
            else:
                animated_opsset = self.get_animated_opsset_at_time(
                    drawable_id=object_id,
                    t=t,
                    event_and_progress=event_and_progress,
                    drawable_events_mapping=drawable_events_mapping,
                )
            if object_id in self.background_drawable_ids:
                tagged_bg_ops = [
                    Ops(
                        type=op.type,
                        data=op.data,
                        partial=op.partial,
                        meta={**(op.meta or {}), "background": True},
                    )
                    for op in animated_opsset.opsset
                ]
                background_frame_ops.extend(OpsSet(initial_set=tagged_bg_ops))
            elif object_id in self.overlay_drawable_ids:
                tagged_ops = [
                    Ops(
                        type=op.type,
                        data=op.data,
                        partial=op.partial,
                        meta={**(op.meta or {}), "overlay": True},
                    )
                    for op in animated_opsset.opsset
                ]
                overlay_frame_ops.extend(OpsSet(initial_set=tagged_ops))
            elif active_tr is not None:
                last_shown = self._get_last_shown_time(object_id, t_sec)
                if last_shown < active_tr.start_time:
                    outgoing_world_ops.extend(animated_opsset)
                else:
                    incoming_world_ops.extend(animated_opsset)
            else:
                frame_opsset.extend(animated_opsset)

        if background_frame_ops.opsset:
            combined = OpsSet(initial_set=list(background_frame_ops.opsset))
            combined.extend(frame_opsset)
            frame_opsset = combined

        if active_tr is not None:
            raw_progress = float(np.clip((t_sec - active_tr.start_time) / active_tr.duration, 0.0, 1.0))
            transitioned_world = active_tr.apply_transition(
                outgoing_ops=outgoing_world_ops,
                incoming_ops=incoming_world_ops,
                raw_progress=raw_progress,
                viewport=self._get_viewport_at(t_sec),
                background_color=self.background_color,
            )
            frame_opsset.extend(transitioned_world)

        if overlay_frame_ops.opsset:
            frame_opsset.extend(overlay_frame_ops)

        return frame_opsset

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
            max_length = float(np.ceil(key_frames[-1])) if key_frames else 0.0
        else:
            key_frames.append(max_length)
        scene_opsset_list: list[OpsSet] = []

        # start calculating with a progress bar
        frame_count = int(np.round(max_length * self.fps))
        for t in tqdm(range(0, frame_count + 1), desc="Calculating animation frames..."):
            scene_opsset_list.append(self._compute_frame_opsset(t, drawable_events_mapping))
        return scene_opsset_list

    def introspect(
        self,
        max_length: float | None = None,
        safe_zone: str | None = None,
        check_overlaps: bool = True,
    ) -> dict:
        """Analyze the scene layout, active drawable collisions, and platform safe zones without rendering frames.

        Performs headless static inspection:
        - Calculates bounding boxes for all registered drawables.
        - Identifies objects placed outside the visible world viewport.
        - Checks platform UI safe zones when `safe_zone="youtube_shorts"` or `"youtube_landscape"` is specified.
        - Detects unintended bounding-box overlaps between simultaneously active drawables at keyframe timestamps.
        - Audits event timing (creation, duration, deletion) and active intervals.
        - Reports warnings and errors in a machine-readable dictionary suitable for AI agents.

        Returns:
            dict containing duration, viewport, objects, overlaps, safe_zone_violations, warnings, and errors.
        """
        key_frames, drawable_events_mapping = self.find_key_frames()
        total_duration = (
            max_length
            if max_length is not None
            else (float(np.ceil(key_frames[-1])) if len(key_frames) > 0 else 0.0)
        )

        world_min_x, world_max_x = self.viewport.world_xrange
        world_min_y, world_max_y = self.viewport.world_yrange
        world_w = world_max_x - world_min_x
        world_h = world_max_y - world_min_y

        warnings: list[str] = []
        errors: list[str] = []
        object_summaries: list[dict] = []
        bbox_by_id: dict[str, Any] = {}
        safe_zone_violations: list[dict] = []
        overlaps: list[dict] = []

        norm_safe_zone = safe_zone.lower().strip() if isinstance(safe_zone, str) else None

        # Track group co-membership so sibling elements in a FlowchartNode / Table / DrawableGroup
        # do not trigger false-positive collision warnings against each other.
        same_group_pairs: set[tuple[str, str]] = set()
        for grp in self.drawable_groups.values():
            elem_ids = [e.id for e in grp.elements]
            for i in range(len(elem_ids)):
                for j in range(i + 1, len(elem_ids)):
                    same_group_pairs.add((elem_ids[i], elem_ids[j]))
                    same_group_pairs.add((elem_ids[j], elem_ids[i]))

        for drawable_id, events in drawable_events_mapping.items():
            drawable = self.drawable_cache.drawables.get(drawable_id)
            d_type = type(drawable).__name__ if drawable else "Unknown"

            # Check bbox
            bbox_dict: dict | None = None
            try:
                opsset = self.drawable_cache.get_drawable_opsset(drawable_id)
                bbox = opsset.get_bbox()
                if all(np.isfinite([bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y])):
                    bbox_by_id[drawable_id] = bbox
                bbox_dict = {
                    "min_x": round(float(bbox.min_x), 2),
                    "min_y": round(float(bbox.min_y), 2),
                    "max_x": round(float(bbox.max_x), 2),
                    "max_y": round(float(bbox.max_y), 2),
                    "width": round(float(bbox.width), 2),
                    "height": round(float(bbox.height), 2),
                }

                is_hud_or_bg = (
                    drawable_id in self.overlay_drawable_ids
                    or drawable_id in self.background_drawable_ids
                    or d_type in ("Captions", "BackgroundGrid")
                )

                # Check if off-screen (for world-space drawables)
                if not is_hud_or_bg and (
                    bbox.max_x < world_min_x
                    or bbox.min_x > world_max_x
                    or bbox.max_y < world_min_y
                    or bbox.min_y > world_max_y
                ):
                    warnings.append(
                        f"Object '{drawable_id}' ({d_type}) is completely outside the world viewport "
                        f"[{world_min_x}..{world_max_x}, {world_min_y}..{world_max_y}]."
                    )
                elif not is_hud_or_bg and (
                    bbox.min_x < world_min_x
                    or bbox.max_x > world_max_x
                    or bbox.min_y < world_min_y
                    or bbox.max_y > world_max_y
                ):
                    warnings.append(
                        f"Object '{drawable_id}' ({d_type}) partially clips outside viewport bounds: "
                        f"bbox={bbox_dict} vs viewport x=[{world_min_x}, {world_max_x}], y=[{world_min_y}, {world_max_y}]."
                    )

                # Platform Safe-Zone Checks (for world-space drawables)
                if norm_safe_zone and not is_hud_or_bg and drawable_id in bbox_by_id:
                    if norm_safe_zone in ("youtube_shorts", "shorts", "reels", "tiktok"):
                        bottom_limit = world_min_y + 0.80 * world_h
                        top_limit = world_min_y + 0.06 * world_h
                        right_strip_x = world_min_x + 0.86 * world_w
                        right_strip_y = world_min_y + 0.35 * world_h
                        if bbox.max_y > bottom_limit:
                            msg = (
                                f"Safe-zone warning ({norm_safe_zone}): Object '{drawable_id}' ({d_type}) "
                                f"extends into bottom caption/UI overlay zone (max_y={bbox.max_y:.1f} > {bottom_limit:.1f})."
                            )
                            warnings.append(msg)
                            safe_zone_violations.append({"id": drawable_id, "type": d_type, "zone": "bottom_ui", "bbox": bbox_dict})
                        if bbox.min_y < top_limit:
                            msg = (
                                f"Safe-zone warning ({norm_safe_zone}): Object '{drawable_id}' ({d_type}) "
                                f"extends into top status-bar zone (min_y={bbox.min_y:.1f} < {top_limit:.1f})."
                            )
                            warnings.append(msg)
                            safe_zone_violations.append({"id": drawable_id, "type": d_type, "zone": "top_ui", "bbox": bbox_dict})
                        if bbox.max_x > right_strip_x and bbox.max_y > right_strip_y:
                            msg = (
                                f"Safe-zone warning ({norm_safe_zone}): Object '{drawable_id}' ({d_type}) "
                                f"extends into right-side action button strip (max_x={bbox.max_x:.1f} > {right_strip_x:.1f})."
                            )
                            warnings.append(msg)
                            safe_zone_violations.append({"id": drawable_id, "type": d_type, "zone": "right_action_strip", "bbox": bbox_dict})
                    elif norm_safe_zone in ("youtube_landscape", "landscape"):
                        margin_x = 0.05 * world_w
                        margin_top = 0.05 * world_h
                        margin_bottom = 0.12 * world_h
                        if (
                            bbox.min_x < world_min_x + margin_x
                            or bbox.max_x > world_max_x - margin_x
                            or bbox.min_y < world_min_y + margin_top
                            or bbox.max_y > world_max_y - margin_bottom
                        ):
                            msg = (
                                f"Safe-zone warning ({norm_safe_zone}): Object '{drawable_id}' ({d_type}) "
                                f"intrudes into landscape title/scrubber safe margin (bbox={bbox_dict})."
                            )
                            warnings.append(msg)
                            safe_zone_violations.append({"id": drawable_id, "type": d_type, "zone": "landscape_margin", "bbox": bbox_dict})
            except Exception as e:
                errors.append(f"Could not compute bounding box for '{drawable_id}': {e}")

            # Check events
            event_summaries = []
            for ev in events:
                event_summaries.append({
                    "id": ev.id,
                    "type": ev.type.name if hasattr(ev.type, "name") else str(ev.type),
                    "class": type(ev).__name__,
                    "start_time": ev.start_time,
                    "duration": ev.duration,
                    "end_time": ev.end_time,
                })
                if ev.end_time > total_duration:
                    warnings.append(
                        f"Event '{type(ev).__name__}' on '{drawable_id}' ends at t={ev.end_time:.2f}s, "
                        f"beyond total scene duration of {total_duration:.2f}s."
                    )

            object_summaries.append({
                "id": drawable_id,
                "type": d_type,
                "bbox": bbox_dict,
                "events": event_summaries,
            })

        # Check active drawable collisions across keyframe timestamps
        if check_overlaps and len(bbox_by_id) >= 2:
            sample_times = sorted(set([0.0] + [float(t) for t in key_frames if 0.0 <= t <= total_duration]))
            reported_pairs: set[tuple[str, str]] = set()
            text_like_types = {"Text", "Math"}
            container_types = {"Rectangle", "RoundedRectangle", "Square", "RoundedSquare", "Circle", "Ellipse", "Polygon", "Axes", "BarChart", "LineChart", "Table"}

            for t_probe in sample_times:
                active_ids = [
                    oid
                    for oid in self.get_active_objects(t_probe)
                    if oid in bbox_by_id
                    and oid not in self.overlay_drawable_ids
                    and oid not in self.background_drawable_ids
                ]
                for i in range(len(active_ids)):
                    id_a = active_ids[i]
                    d_a = self.drawable_cache.drawables.get(id_a)
                    if d_a is None or getattr(d_a, "is_emphasis_overlay", False) or hasattr(d_a, "objects_to_erase"):
                        continue
                    type_a = type(d_a).__name__
                    b_a = bbox_by_id[id_a]

                    for j in range(i + 1, len(active_ids)):
                        id_b = active_ids[j]
                        pair_key = (min(id_a, id_b), max(id_a, id_b))
                        if pair_key in reported_pairs or (id_a, id_b) in same_group_pairs:
                            continue
                        d_b = self.drawable_cache.drawables.get(id_b)
                        if d_b is None or getattr(d_b, "is_emphasis_overlay", False) or hasattr(d_b, "objects_to_erase"):
                            continue
                        type_b = type(d_b).__name__
                        b_b = bbox_by_id[id_b]

                        # Only flag when at least one object is Text/Math (or both are distinct labels/diagrams)
                        if type_a not in text_like_types and type_b not in text_like_types:
                            continue

                        ix0 = max(b_a.min_x, b_b.min_x)
                        iy0 = max(b_a.min_y, b_b.min_y)
                        ix1 = min(b_a.max_x, b_b.max_x)
                        iy1 = min(b_a.max_y, b_b.max_y)
                        if ix1 <= ix0 or iy1 <= iy0:
                            continue

                        inter_area = (ix1 - ix0) * (iy1 - iy0)
                        area_a = max(1e-6, b_a.width * b_a.height)
                        area_b = max(1e-6, b_b.width * b_b.height)
                        overlap_ratio = inter_area / min(area_a, area_b)

                        # Ignore intentional label-inside-container (e.g. Text centered inside a Rectangle box)
                        a_inside_b = (
                            type_b in container_types
                            and b_a.min_x >= b_b.min_x - 2.0
                            and b_a.max_x <= b_b.max_x + 2.0
                            and b_a.min_y >= b_b.min_y - 2.0
                            and b_a.max_y <= b_b.max_y + 2.0
                        )
                        b_inside_a = (
                            type_a in container_types
                            and b_b.min_x >= b_a.min_x - 2.0
                            and b_b.max_x <= b_a.max_x + 2.0
                            and b_b.min_y >= b_a.min_y - 2.0
                            and b_b.max_y <= b_a.max_y + 2.0
                        )
                        if a_inside_b or b_inside_a:
                            continue

                        if overlap_ratio >= 0.15:
                            reported_pairs.add(pair_key)
                            ov_entry = {
                                "object_a": id_a,
                                "type_a": type_a,
                                "object_b": id_b,
                                "type_b": type_b,
                                "time": round(t_probe, 2),
                                "overlap_ratio": round(float(overlap_ratio), 2),
                            }
                            overlaps.append(ov_entry)
                            warnings.append(
                                f"Overlap warning at t={t_probe:.2f}s: '{id_a}' ({type_a}) and '{id_b}' ({type_b}) "
                                f"intersect ({overlap_ratio * 100:.0f}% overlap)."
                            )

        return {
            "duration": total_duration,
            "fps": self.fps,
            "viewport": {
                "world_xrange": list(self.viewport.world_xrange),
                "world_yrange": list(self.viewport.world_yrange),
                "screen_width": self.width,
                "screen_height": self.height,
            },
            "num_objects": len(object_summaries),
            "objects": object_summaries,
            "overlaps": overlaps,
            "safe_zone_violations": safe_zone_violations,
            "warnings": warnings,
            "errors": errors,
        }

    def render_frame(
        self,
        t: float,
        output_path: str | Path | None = None,
        opsset: OpsSet | None = None,
    ) -> np.ndarray:
        """Render a single frame at time `t` (seconds) and return an `(H, W, 3)` uint8 RGB numpy array.

        Evaluates only the requested timestamp `t` (unless a precomputed `opsset` is provided),
        avoiding full timeline computation for single stills. If `output_path` is provided,
        also writes the frame to disk (`.png`, `.svg`, or `.pdf`).
        """
        t_sec = float(t)
        if opsset is None:
            _, drawable_events_mapping = self.find_key_frames()
            frame_index = max(0, int(np.round(t_sec * self.fps)))
            opsset = self._compute_frame_opsset(frame_index, drawable_events_mapping)

        if output_path is not None:
            self._render_frame(opsset, str(output_path), t_sec)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        ctx = cairo.Context(surface)
        if self.background_color is not None:
            ctx.set_source_rgb(*self.background_color)
        ctx.paint()
        self._render_opsset_on_context(ctx, opsset, t_sec)
        arr = cairo_surface_to_numpy(surface)
        surface.finish()
        return np.ascontiguousarray(arr[:, :, :3])

    def render_snapshot(
        self,
        output_path: str,
        frame_in_seconds: float,
        max_length: float | None = None,
    ):
        """Render a snapshot of the animation at a specific time point as an SVG, PNG, or PDF file.

        Evaluates only the requested timestamp `frame_in_seconds` rather than computing
        all frames across the full video timeline.

        Args:
            output_path (str): Path to the output file (.svg, .png, or .pdf).
            frame_in_seconds (float): The exact time point (in seconds) to render.
            max_length (Optional[float], optional): Total duration of the animation. Defaults to None.
        """
        key_frames, drawable_events_mapping = self.find_key_frames()
        if max_length is None:
            max_length = float(np.ceil(key_frames[-1])) if key_frames else 0.0
        frame_count = max(0, int(np.round(max_length * self.fps)))
        frame_index = int(np.clip(np.round(frame_in_seconds * self.fps), 0, frame_count))
        frame_ops = self._compute_frame_opsset(frame_index, drawable_events_mapping)
        self._render_frame(frame_ops, output_path, frame_in_seconds)

    def render_contact_sheet(
        self,
        output_path: str,
        timestamps: Sequence[float] | None = None,
        n_frames: int = 6,
        cols: int = 3,
        cell_width: int = 360,
        safe_zone: str | None = None,
        max_length: float | None = None,
    ) -> str:
        """Render multiple timestamp snapshots into a single annotated PNG grid image.

        Ideal for fast LLM visual review of an entire storyboard in one image call.
        """
        key_frames, drawable_events_mapping = self.find_key_frames()
        total_duration = (
            float(max_length)
            if max_length is not None
            else (float(np.ceil(key_frames[-1])) if key_frames else 1.0)
        )
        frame_count = max(0, int(np.round(total_duration * self.fps)))

        if timestamps is not None and len(timestamps) > 0:
            times = [float(t) for t in timestamps]
        elif self.beats:
            times = [max(b.start, b.end - 0.05) for b in self.beats]
        else:
            count = max(1, int(n_frames))
            times = (
                [i * total_duration / (count - 1) for i in range(count)]
                if count > 1
                else [total_duration * 0.5]
            )

        cols = max(1, min(len(times), int(cols)))
        rows = int(np.ceil(len(times) / cols))
        aspect = self.height / max(1, self.width)
        cell_w = max(120, int(cell_width))
        cell_h = max(120, int(round(cell_w * aspect)))
        pad = 12
        sheet_w = cols * cell_w + (cols + 1) * pad
        sheet_h = rows * cell_h + (rows + 1) * pad

        sheet_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, sheet_w, sheet_h)
        sheet_ctx = cairo.Context(sheet_surface)
        sheet_ctx.set_source_rgb(0.14, 0.15, 0.18)
        sheet_ctx.paint()

        norm_sz = safe_zone.lower().strip() if isinstance(safe_zone, str) else None

        for idx, t in enumerate(times):
            r = idx // cols
            c = idx % cols
            ox = pad + c * (cell_w + pad)
            oy = pad + r * (cell_h + pad)

            frame_index = int(np.clip(np.round(t * self.fps), 0, frame_count))
            frame_ops = self._compute_frame_opsset(frame_index, drawable_events_mapping)

            tile_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
            tile_ctx = cairo.Context(tile_surface)
            if self.background_color is not None:
                tile_ctx.set_source_rgb(*self.background_color)
            tile_ctx.paint()
            self._render_opsset_on_context(tile_ctx, frame_ops, t)

            sheet_ctx.save()
            sheet_ctx.translate(ox, oy)
            sheet_ctx.scale(cell_w / self.width, cell_h / self.height)
            sheet_ctx.set_source_surface(tile_surface, 0, 0)
            sheet_ctx.paint()
            sheet_ctx.restore()

            # Optional safe-zone overlay guides
            if norm_sz in ("youtube_shorts", "shorts", "reels", "tiktok"):
                sheet_ctx.save()
                sheet_ctx.set_source_rgba(0.9, 0.2, 0.2, 0.55)
                sheet_ctx.set_line_width(1.5)
                sheet_ctx.set_dash([5.0, 4.0])
                # Top 6% and bottom 20% lines
                sheet_ctx.move_to(ox, oy + cell_h * 0.06)
                sheet_ctx.line_to(ox + cell_w, oy + cell_h * 0.06)
                sheet_ctx.move_to(ox, oy + cell_h * 0.80)
                sheet_ctx.line_to(ox + cell_w, oy + cell_h * 0.80)
                # Right action strip
                sheet_ctx.rectangle(ox + cell_w * 0.86, oy + cell_h * 0.35, cell_w * 0.14, cell_h * 0.45)
                sheet_ctx.stroke()
                sheet_ctx.restore()

            # Timestamp badge in top-left of tile
            badge_text = f"#{idx + 1}  t={t:.2f}s"
            sheet_ctx.save()
            sheet_ctx.set_source_rgba(0.08, 0.09, 0.11, 0.78)
            sheet_ctx.rectangle(ox + 6, oy + 6, 118, 24)
            sheet_ctx.fill()
            sheet_ctx.set_source_rgb(1.0, 1.0, 1.0)
            sheet_ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            sheet_ctx.set_font_size(13)
            sheet_ctx.move_to(ox + 12, oy + 22)
            sheet_ctx.show_text(badge_text)
            sheet_ctx.restore()

        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
        sheet_surface.write_to_png(output_path)
        sheet_surface.finish()
        return output_path

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

    def _render_opsset_on_context(
        self,
        ctx: cairo.Context,
        frame_ops: OpsSet,
        frame_in_seconds: float,
    ) -> None:
        """Render background ops under the static viewport, world ops under the camera viewport, and overlay ops on top."""
        background_ops_list: list[Ops] = []
        world_ops_list: list[Ops] = []
        overlay_ops_list: list[Ops] = []
        for op in frame_ops.opsset:
            if op.meta and op.meta.get("background"):
                background_ops_list.append(op)
            elif op.meta and op.meta.get("overlay"):
                overlay_ops_list.append(op)
            else:
                world_ops_list.append(op)

        if background_ops_list:
            ctx.save()
            self.viewport.apply_to_context(ctx)
            OpsSet(initial_set=background_ops_list).render(ctx)
            ctx.restore()

        if world_ops_list or (not background_ops_list and not overlay_ops_list):
            ctx.save()
            self._get_viewport_at(frame_in_seconds).apply_to_context(ctx)
            OpsSet(initial_set=world_ops_list).render(ctx)
            ctx.restore()

        if overlay_ops_list:
            ctx.save()
            self.viewport.apply_to_context(ctx)
            OpsSet(initial_set=overlay_ops_list).render(ctx)
            ctx.restore()

    def _render_frame(self, frame_ops: OpsSet, output_path: str, frame_in_seconds: float):
        """Render a single frame OpsSet to an SVG, PNG, or PDF file based on the file extension."""
        ext = os.path.splitext(output_path)[1].lower()
        surface: cairo.Surface
        if ext == ".pdf":
            surface = cairo.PDFSurface(output_path, self.width, self.height)
        elif ext == ".png":
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        else:
            surface = cairo.SVGSurface(output_path, self.width, self.height)
        ctx = cairo.Context(surface)
        if self.background_color is not None:
            ctx.set_source_rgb(*self.background_color)
        ctx.paint()
        self._render_opsset_on_context(ctx, frame_ops, frame_in_seconds)
        if ext == ".png":
            surface.write_to_png(output_path)
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
            self._render_opsset_on_context(ctx, opsset_list[frame_index], t)
            surface.show_page()
        surface.finish()
        return output_path

    def render_tikz(
        self,
        output_path: str,
        time: float = 0.0,
        target_width_cm: float = 12.0,
        max_length: float | None = None,
    ) -> str:
        """Render a single animation frame as a standalone TikZ/LaTeX file.

        Args:
            output_path: Path to write the ``.tex`` file.
            time: Timestamp (in seconds) to render.
            target_width_cm: Width of the tikzpicture in centimetres.
            max_length: Total animation duration override.

        Returns:
            The output file path.
        """
        from .tikz_renderer import TikZRenderer

        key_frames, drawable_events_mapping = self.find_key_frames()
        if max_length is None:
            max_length = float(np.ceil(key_frames[-1])) if key_frames else 0.0
        frame_count = max(0, int(np.round(max_length * self.fps)))
        frame_index = int(np.clip(np.round(time * self.fps), 0, frame_count))
        frame_ops = self._compute_frame_opsset(frame_index, drawable_events_mapping)

        renderer = TikZRenderer(self.viewport, target_width_cm, self.background_color)
        tikz_body = renderer.render_tikzpicture(frame_ops)

        tex = (
            "\\documentclass[border=2mm]{standalone}\n"
            "\\usepackage{tikz}\n"
            "\\begin{document}\n"
            f"{tikz_body}\n"
            "\\end{document}\n"
        )
        with open(output_path, "w") as f:
            f.write(tex)
        return output_path

    def export_beamer(
        self,
        output_dir: str,
        n_frames: int = 6,
        times: list[float] | None = None,
        title: str = "Handanim Slides",
        max_length: float | None = None,
        backend: str = "cairo",
        target_width_cm: float = 12.0,
    ) -> str:
        """Export animation keyframes as a compilable Beamer/LaTeX slide deck.

        Each keyframe becomes one overlay on a single frame, so the slides
        animate forward when presented.

        With ``backend="cairo"`` (default), each keyframe is rendered as a
        Cairo PDF and embedded via ``\\includegraphics``.

        With ``backend="tikz"``, keyframes are emitted as inline TikZ
        drawing commands — native LaTeX vector graphics, no external files.

        Args:
            output_dir: Directory to write output files and the .tex file.
            n_frames: Number of evenly-spaced keyframes (ignored if `times` given).
            times: Explicit list of timestamps to render.
            title: Title shown on the Beamer title page.
            max_length: Total animation duration override.
            backend: ``"cairo"`` for PDF-image overlays, ``"tikz"`` for native TikZ.
            target_width_cm: Width of tikzpicture (only used with ``backend="tikz"``).

        Returns:
            Path to the generated .tex file.
        """
        os.makedirs(output_dir, exist_ok=True)
        opsset_list = self.create_event_timeline(max_length)
        total_frames = len(opsset_list)
        total_duration = total_frames / self.fps
        if times is None:
            times = [i * total_duration / (n_frames - 1) for i in range(n_frames)] if n_frames > 1 else [0.0]

        if backend == "tikz":
            return self._export_beamer_tikz(opsset_list, total_frames, times, title, output_dir, target_width_cm)
        return self._export_beamer_cairo(opsset_list, total_frames, times, title, output_dir)

    def _export_beamer_cairo(
        self,
        opsset_list: list,
        total_frames: int,
        times: list[float],
        title: str,
        output_dir: str,
    ) -> str:
        pdf_filenames = []
        for i, t in enumerate(times):
            frame_index = int(np.clip(np.round(t * self.fps), 0, total_frames - 1))
            filename = f"slide_{i:03d}.pdf"
            self._render_frame(opsset_list[frame_index], os.path.join(output_dir, filename), t)
            pdf_filenames.append(filename)

        overlay_lines = []
        for i, fname in enumerate(pdf_filenames, start=1):
            overlay_lines.append(
                f"    \\only<{i}>{{\\includegraphics[width=\\textwidth]{{{fname}}}}}"
            )
        overlays = "\n".join(overlay_lines)

        tex_content = (
            "\\documentclass{beamer}\n"
            "\\usepackage{graphicx}\n"
            f"\\title{{{title}}}\n"
            "\\date{}\n"
            "\\begin{document}\n"
            "\\begin{frame}\n"
            "\\titlepage\n"
            "\\end{frame}\n"
            "\\begin{frame}{}\n"
            f"{overlays}\n"
            "\\end{frame}\n"
            "\\end{document}\n"
        )
        tex_path = os.path.join(output_dir, "slides.tex")
        with open(tex_path, "w") as f:
            f.write(tex_content)
        return tex_path

    def _export_beamer_tikz(
        self,
        opsset_list: list,
        total_frames: int,
        times: list[float],
        title: str,
        output_dir: str,
        target_width_cm: float,
    ) -> str:
        from .tikz_renderer import TikZRenderer

        overlay_lines = []
        for i, t in enumerate(times):
            frame_index = int(np.clip(np.round(t * self.fps), 0, total_frames - 1))
            renderer = TikZRenderer(self.viewport, target_width_cm, self.background_color)
            tikz_body = renderer.render_tikzpicture(opsset_list[frame_index])
            indent = "\n".join(f"    {line}" for line in tikz_body.splitlines())
            overlay_lines.append(f"  \\only<{i + 1}>{{\n{indent}\n  }}")

        overlays = "\n".join(overlay_lines)

        tex_content = (
            "\\documentclass{beamer}\n"
            "\\usepackage{tikz}\n"
            f"\\title{{{title}}}\n"
            "\\date{}\n"
            "\\begin{document}\n"
            "\\begin{frame}\n"
            "\\titlepage\n"
            "\\end{frame}\n"
            "\\begin{frame}{}\n"
            f"{overlays}\n"
            "\\end{frame}\n"
            "\\end{document}\n"
        )
        tex_path = os.path.join(output_dir, "slides.tex")
        with open(tex_path, "w") as f:
            f.write(tex_content)
        return tex_path

    def set_background_music(
        self,
        music: Any = "marimba",
        volume: float = 0.18,
        loop: bool = True,
    ) -> None:
        """Configure background theme music or audio to play (and optionally loop) in rendered videos.

        Args:
            music: Theme preset (`"marimba"`, `"calm"`, `"upbeat"`), `True`, `AudioClip`, or path to a WAV/MP3 file.
            volume: Volume multiplier for the music track (default `0.18`).
            loop: If True (default), repeats the background music across the full video duration.
        """
        self.background_music = music
        self.music_volume = float(volume)
        self.music_loop = bool(loop)

    def enable_sketch_sound(
        self,
        enabled: bool | float = True,
        volume: float | None = None,
        style: str | None = None,
    ) -> None:
        """Turn on/off or adjust chalk / sketch-pen drawing sounds during `SketchAnimation` events.

        Args:
            enabled: `True` / `False` to toggle sketch sound on or off, or a float volume multiplier
                (e.g. `0.15` to enable at volume 0.15, or `0.0` to turn off).
            volume: Optional volume multiplier (`0.0` to `1.0`, default `0.25`). Setting `volume=0` turns sound off.
            style: Optional drawing sound style (`"chalk"` or `"pen"`).
        """
        if isinstance(enabled, (int, float)) and not isinstance(enabled, bool):
            vol = max(0.0, float(enabled))
            self.sketch_sound_volume = vol
            self.sketch_sound = vol > 0.0
        else:
            if volume is not None:
                self.sketch_sound_volume = max(0.0, float(volume))
            self.sketch_sound = bool(enabled) and (self.sketch_sound_volume > 0.0)
        if style is not None:
            self.sketch_sound_style = str(style)

    def disable_sketch_sound(self) -> None:
        """Turn off automatic chalk / sketch-pen drawing sounds."""
        self.sketch_sound = False

    def set_sketch_sound(
        self,
        enabled: bool | float = True,
        volume: float | None = None,
        style: str | None = None,
    ) -> None:
        """Configure or toggle automatic sketch sound (alias for `enable_sketch_sound`)."""
        self.enable_sketch_sound(enabled=enabled, volume=volume, style=style)

    def enable_eraser_sound(
        self,
        enabled: bool | float = True,
        volume: float | None = None,
    ) -> None:
        """Automatically play board/paper erasing sounds during `Eraser` animations."""
        if isinstance(enabled, (int, float)) and not isinstance(enabled, bool):
            vol = max(0.0, float(enabled))
            self.eraser_sound_volume = vol
            self.eraser_sound = vol > 0.0
        else:
            if volume is not None:
                self.eraser_sound_volume = max(0.0, float(volume))
            self.eraser_sound = bool(enabled) and (self.eraser_sound_volume > 0.0)

    def disable_eraser_sound(self) -> None:
        """Turn off automatic eraser sounds."""
        self.eraser_sound = False

    def enable_transition_sound(
        self,
        enabled: bool | float = True,
        volume: float | None = None,
    ) -> None:
        """Automatically play page-turn and paper-crumple sounds during `SceneTransition` animations."""
        if isinstance(enabled, (int, float)) and not isinstance(enabled, bool):
            vol = max(0.0, float(enabled))
            self.transition_sound_volume = vol
            self.transition_sound = vol > 0.0
        else:
            if volume is not None:
                self.transition_sound_volume = max(0.0, float(volume))
            self.transition_sound = bool(enabled) and (self.transition_sound_volume > 0.0)

    def disable_transition_sound(self) -> None:
        """Turn off automatic scene transition sounds."""
        self.transition_sound = False

    def extract_auto_sfx_events(
        self,
        include_sketch: bool | float | None = None,
        include_eraser: bool | float | None = None,
        include_transition: bool | float | None = None,
        sketch_volume: float | None = None,
        sketch_style: str | None = None,
        eraser_volume: float | None = None,
        transition_volume: float | None = None,
    ) -> list[dict[str, Any]]:
        """Extract non-overlapping chalk sketch, eraser, and transition SFX intervals from the scene timeline."""
        from ..animations.sketch import SketchAnimation
        from ..animations.transitions import PageTurnTransition, PaperCrumpleTransition

        base_sketch_vol = self.sketch_sound_volume if sketch_volume is None else max(0.0, float(sketch_volume))
        base_sketch_style = self.sketch_sound_style if sketch_style is None else str(sketch_style)
        base_eraser_vol = self.eraser_sound_volume if eraser_volume is None else max(0.0, float(eraser_volume))
        base_transition_vol = (
            self.transition_sound_volume if transition_volume is None else max(0.0, float(transition_volume))
        )

        master_mute_sketch = False
        if include_sketch is None:
            do_sketch = self.sketch_sound and (base_sketch_vol > 0.0)
        elif isinstance(include_sketch, (int, float)) and not isinstance(include_sketch, bool):
            if float(include_sketch) <= 0.0:
                do_sketch = False
                master_mute_sketch = True
            else:
                do_sketch = True
                if sketch_volume is None:
                    base_sketch_vol = float(include_sketch)
        else:
            do_sketch = bool(include_sketch) and (base_sketch_vol > 0.0)
            if not include_sketch:
                master_mute_sketch = True
        if sketch_volume is not None and float(sketch_volume) <= 0.0:
            do_sketch = False
            master_mute_sketch = True

        if include_eraser is None:
            do_eraser = self.eraser_sound and (base_eraser_vol > 0.0)
        elif isinstance(include_eraser, (int, float)) and not isinstance(include_eraser, bool):
            do_eraser = float(include_eraser) > 0.0
            if do_eraser and eraser_volume is None:
                base_eraser_vol = float(include_eraser)
        else:
            do_eraser = bool(include_eraser) and (base_eraser_vol > 0.0)

        if include_transition is None:
            do_transition = self.transition_sound and (base_transition_vol > 0.0)
        elif isinstance(include_transition, (int, float)) and not isinstance(include_transition, bool):
            do_transition = float(include_transition) > 0.0
            if do_transition and transition_volume is None:
                base_transition_vol = float(include_transition)
        else:
            do_transition = bool(include_transition) and (base_transition_vol > 0.0)

        sketch_intervals: list[tuple[float, float, float, str]] = []
        eraser_intervals: list[tuple[float, float]] = []

        for event, drawable_id in self.events:
            if event.duration <= 0.0:
                continue
            drawable = self.drawable_cache.drawables.get(drawable_id)
            is_eraser = drawable is not None and hasattr(drawable, "objects_to_erase")

            if is_eraser:
                if do_eraser:
                    eraser_intervals.append((float(event.start_time), float(event.end_time)))
            elif isinstance(event, SketchAnimation) and not master_mute_sketch:
                ev_sound = getattr(event, "sound", event.data.get("sound", None))
                ev_vol = getattr(event, "sound_volume", event.data.get("sound_volume", None))
                ev_style = getattr(event, "sound_style", event.data.get("sound_style", None))

                if ev_sound is False or (ev_vol is not None and float(ev_vol) <= 0.0):
                    continue
                if ev_sound is True or (ev_vol is not None and float(ev_vol) > 0.0) or do_sketch:
                    vol = float(ev_vol) if ev_vol is not None else base_sketch_vol
                    style = str(ev_style) if ev_style is not None else base_sketch_style
                    if vol > 0.0:
                        sketch_intervals.append((float(event.start_time), float(event.end_time), vol, style))

        def _merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
            if not intervals:
                return []
            sorted_iv = sorted(intervals, key=lambda x: (x[0], x[1]))
            merged: list[tuple[float, float]] = [sorted_iv[0]]
            for st, en in sorted_iv[1:]:
                prev_st, prev_en = merged[-1]
                if st <= prev_en + 0.02:
                    merged[-1] = (prev_st, max(prev_en, en))
                else:
                    merged.append((st, en))
            return merged

        def _merge_sketch_intervals(
            intervals: list[tuple[float, float, float, str]]
        ) -> list[tuple[float, float, float, str]]:
            if not intervals:
                return []
            sorted_iv = sorted(intervals, key=lambda x: (x[0], x[1]))
            merged: list[tuple[float, float, float, str]] = [sorted_iv[0]]
            for st, en, vol, style in sorted_iv[1:]:
                prev_st, prev_en, prev_vol, prev_style = merged[-1]
                # Merge if intervals strictly overlap in time, or if they are back-to-back with identical volume & style
                same_cfg = abs(vol - prev_vol) < 1e-6 and style == prev_style
                if st < prev_en - 1e-6 or (st <= prev_en + 0.02 and same_cfg):
                    merged[-1] = (prev_st, max(prev_en, en), max(prev_vol, vol), prev_style)
                else:
                    merged.append((st, en, vol, style))
            return merged

        sfx_events: list[dict[str, Any]] = []
        for st, en, vol, style in _merge_sketch_intervals(sketch_intervals):
            sfx_events.append(
                {
                    "type": "chalk",
                    "start_time": st,
                    "duration": en - st,
                    "volume": vol,
                    "style": style,
                }
            )
        for st, en in _merge_intervals(eraser_intervals):
            sfx_events.append(
                {
                    "type": "eraser",
                    "start_time": st,
                    "duration": en - st,
                    "volume": base_eraser_vol,
                }
            )
        if do_transition:
            for tr in self.transitions:
                if tr.duration <= 0.0:
                    continue
                if isinstance(tr, PaperCrumpleTransition):
                    tr_type = "crumple"
                elif isinstance(tr, PageTurnTransition):
                    tr_type = "page_turn"
                else:
                    tr_type = "page_turn"
                sfx_events.append(
                    {
                        "type": tr_type,
                        "start_time": float(tr.start_time),
                        "duration": float(tr.duration),
                        "volume": base_transition_vol,
                    }
                )
        sfx_events.sort(key=lambda d: float(d["start_time"]))
        return sfx_events

    def render(
        self,
        output_path: str,
        max_length: float | None = None,
        narration: Any = None,
        background_music: Any = None,
        music_volume: float | None = None,
        music_loop: bool | None = None,
        sketch_sound: bool | float | None = None,
        sketch_sound_volume: float | None = None,
        sketch_sound_style: str | None = None,
        eraser_sound: bool | float | None = None,
        eraser_sound_volume: float | None = None,
        transition_sound: bool | float | None = None,
        transition_sound_volume: float | None = None,
        sfx_events: Sequence[dict[str, Any] | tuple[Any, ...]] | None = None,
        *,
        crf: int | None = None,
        preset: str | None = None,
        tune: str | None = None,
        workers: int = 1,
    ):
        """
        Render the animation as a video file, optionally mixing narration, repeating
        background theme music, and automatic chalk/eraser/transition sound effects.

        Args:
            output_path (str): Path to save the output video file.
            max_length (Optional[float], optional): Maximum duration of the animation. Defaults to None.
            narration (Optional[Any], optional): An AudioClip instance from voiceanim or path to a WAV/MP3 file.
            background_music (Optional[Any], optional): Theme preset (`"marimba"`, `"calm"`, `"upbeat"`), `True`,
                `AudioClip`, or path to a music file. Defaults to `self.background_music`.
            music_volume (Optional[float], optional): Background music volume multiplier.
            music_loop (Optional[bool], optional): Whether to repeat background music for the whole video.
            sketch_sound (Optional[bool | float], optional): `True`/`False` to turn automatic chalk sound on/off
                during `SketchAnimation`, or a float volume multiplier (e.g. `0.15` for quiet sketch sound, `0.0` to mute).
            sketch_sound_volume (Optional[float], optional): Volume multiplier (`0.0` to `1.0`) for sketch sounds.
            sketch_sound_style (Optional[str], optional): Style of sketch sound (`"chalk"` or `"pen"`).
            eraser_sound (Optional[bool | float], optional): If True (or positive float), adds erasing sound during `Eraser`.
            eraser_sound_volume (Optional[float], optional): Volume multiplier for eraser sounds.
            transition_sound (Optional[bool | float], optional): If True (or positive float), adds page-turn/crumple sound.
            transition_sound_volume (Optional[float], optional): Volume multiplier for transition sounds.
            sfx_events (Optional[Sequence], optional): Extra custom sound effect events to mix in.
        """
        bg_music = self.background_music if background_music is None else background_music
        bg_vol = self.music_volume if music_volume is None else float(music_volume)
        bg_loop = self.music_loop if music_loop is None else bool(music_loop)

        narration_audio_path: str | None = None
        if narration is None and self.narration is not None:
            narration = self.narration
        if narration is None and any(getattr(b, "narration", None) is not None for b in self.beats):
            narration = self.get_stitched_narration()
        if narration is not None:
            if hasattr(narration, "audio_path") and narration.audio_path:
                narration_audio_path = str(narration.audio_path)
                if max_length is None and hasattr(narration, "duration"):
                    key_frames, _ = self.find_key_frames()
                    kf_len = float(np.ceil(key_frames[-1])) if key_frames else 0.0
                    max_length = max(kf_len, float(narration.duration))
            elif isinstance(narration, (str, Path)):
                narration_audio_path = str(narration)

        # calculate the events
        opsset_list = self.create_event_timeline(max_length)
        output_file_ext = os.path.basename(output_path).split(os.path.extsep)[-1].lower()
        video_duration = max(0.1, (len(opsset_list) - 1) / self.fps) if len(opsset_list) > 1 else 0.5

        auto_sfx = self.extract_auto_sfx_events(
            include_sketch=sketch_sound,
            include_eraser=eraser_sound,
            include_transition=transition_sound,
            sketch_volume=sketch_sound_volume,
            sketch_style=sketch_sound_style,
            eraser_volume=eraser_sound_volume,
            transition_volume=transition_sound_volume,
        )
        all_sfx: list[dict[str, Any] | tuple[Any, ...]] = list(auto_sfx)
        if sfx_events:
            all_sfx.extend(sfx_events)

        needs_audio = (
            narration_audio_path is not None
            or (bg_music is not None and bg_music is not False)
            or len(all_sfx) > 0
        )

        # If audio muxing is needed, render video to a temporary path first
        temp_video_path: str | None = None
        target_video_path = output_path
        if needs_audio and output_file_ext != "gif":
            import tempfile
            fd, temp_video_path = tempfile.mkstemp(suffix=f".{output_file_ext}")
            os.close(fd)
            target_video_path = temp_video_path

        n_workers = max(1, int(workers))
        if output_file_ext == "gif":
            tqdm_desc = "Rendering GIF..."
            write_obj = imageio.get_writer(target_video_path, mode="I", duration=max_length)
            with write_obj as writer:
                for i, frame_ops in enumerate(tqdm(opsset_list, desc=tqdm_desc)):
                    frame_np = self.render_frame(i / self.fps, opsset=frame_ops)
                    writer.append_data(frame_np)  # type: ignore[attr-defined]
        elif n_workers > 1 and len(opsset_list) >= n_workers:
            import subprocess
            import tempfile
            from concurrent.futures import ThreadPoolExecutor

            import imageio_ffmpeg

            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            n_frames = len(opsset_list)
            bounds = [round(n_frames * k / n_workers) for k in range(n_workers + 1)]
            tmp_dir = tempfile.mkdtemp(prefix="handanim_parts_")
            parts = [os.path.join(tmp_dir, f"part_{k}.mp4") for k in range(n_workers)]

            def _encode_chunk(i0: int, i1: int, part_out: str) -> None:
                cmd = [
                    ffmpeg_exe,
                    "-y",
                    "-loglevel",
                    "error",
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "rgb24",
                    "-s",
                    f"{self.width}x{self.height}",
                    "-r",
                    str(self.fps),
                    "-i",
                    "-",
                    "-c:v",
                    "libx264",
                    "-preset",
                    str(preset or "veryfast"),
                    "-crf",
                    str(crf if crf is not None else 18),
                ]
                if tune is not None:
                    cmd.extend(["-tune", str(tune)])
                cmd.extend(["-pix_fmt", "yuv420p", part_out])
                proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                assert proc.stdin is not None
                for idx in range(i0, i1):
                    frame_arr = self.render_frame(idx / self.fps, opsset=opsset_list[idx])
                    proc.stdin.write(frame_arr[:, :, :3].tobytes())
                proc.stdin.close()
                rc = proc.wait()
                if rc != 0:
                    raise RuntimeError(f"FFmpeg worker chunk encoding failed with exit code {rc}")

            try:
                with ThreadPoolExecutor(max_workers=n_workers) as pool:
                    futures = [
                        pool.submit(_encode_chunk, bounds[k], bounds[k + 1], parts[k])
                        for k in range(n_workers)
                    ]
                    for fut in futures:
                        fut.result()
                list_file = os.path.join(tmp_dir, "concat.txt")
                with open(list_file, "w", encoding="utf-8") as fh:
                    fh.write("".join(f"file '{os.path.abspath(p)}'\n" for p in parts))
                subprocess.run(
                    [
                        ffmpeg_exe,
                        "-y",
                        "-loglevel",
                        "error",
                        "-f",
                        "concat",
                        "-safe",
                        "0",
                        "-i",
                        list_file,
                        "-c",
                        "copy",
                        target_video_path,
                    ],
                    check=True,
                )
            finally:
                for p in parts:
                    if os.path.exists(p):
                        os.unlink(p)
                concat_p = os.path.join(tmp_dir, "concat.txt")
                if os.path.exists(concat_p):
                    os.unlink(concat_p)
                if os.path.isdir(tmp_dir):
                    os.rmdir(tmp_dir)
        else:
            tqdm_desc = "Rendering video..."
            output_params: list[str] = []
            if crf is not None:
                output_params.extend(["-crf", str(int(crf))])
            if preset is not None:
                output_params.extend(["-preset", str(preset)])
            if tune is not None:
                output_params.extend(["-tune", str(tune)])
            writer_kwargs: dict[str, Any] = {
                "fps": self.fps,
                "codec": "libx264",
                "macro_block_size": 1,
            }
            if output_params:
                writer_kwargs["output_params"] = output_params
            write_obj = imageio.get_writer(target_video_path, **writer_kwargs)
            with write_obj as writer:
                for i, frame_ops in enumerate(tqdm(opsset_list, desc=tqdm_desc)):
                    frame_np = self.render_frame(i / self.fps, opsset=frame_ops)
                    writer.append_data(frame_np)  # type: ignore[attr-defined]

        # Mux audio if requested
        if needs_audio and temp_video_path is not None:
            mixed_wav_path: str | None = None
            try:
                from voiceanim.mixer import mix_audio_with_video, mix_soundtrack

                if (bg_music is not None and bg_music is not False) or len(all_sfx) > 0:
                    mixed_wav_path = mix_soundtrack(
                        duration=video_duration,
                        narration=narration,
                        background_music=bg_music,
                        music_volume=bg_vol,
                        music_loop=bg_loop,
                        sfx_events=all_sfx,
                    )
                    mix_audio_with_video(temp_video_path, mixed_wav_path, output_path)
                elif narration_audio_path is not None:
                    mix_audio_with_video(temp_video_path, narration_audio_path, output_path)
            finally:
                if mixed_wav_path is not None and os.path.exists(mixed_wav_path):
                    os.unlink(mixed_wav_path)
                if os.path.exists(temp_video_path):
                    os.unlink(temp_video_path)

        return output_path
