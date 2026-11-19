"""Voice-driven Beat context manager (`scene.beat()`) for relative timeline authoring."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .animation import AnimationEvent
    from .drawable import Drawable
    from .scene import Scene


@dataclass
class _ExitCleanupSpec:
    drawables: list[Drawable]
    duration: float = 0.35
    mode: str = "fade"  # "fade" | "hide" | "erase"
    overlay: bool = False


@dataclass
class BeatContext:
    """Context manager representing a self-contained narrative beat on a `Scene` timeline.

    Automatically tracks the beat's start time, derives its duration from an attached
    `AudioClip` (or explicit `duration`), resolves spoken word timestamps relative to the
    beat via `b.t("word")`, and cleans up temporary beat-scoped drawables on exit via
    `b.clear_on_exit(...)`.
    """

    scene: Scene
    name: str = ""
    narration: Any = None
    duration: float | None = None
    start_time: float | None = None
    pad_before: float = 0.0
    pad_after: float = 0.3
    transition_on_exit: Any = None
    _entered_start: float = field(default=0.0, init=False)
    _local_cursor: float = field(default=0.0, init=False)
    _exit_cleanups: list[_ExitCleanupSpec] = field(default_factory=list, init=False)
    _scoped_drawables: list[Drawable] = field(default_factory=list, init=False)
    _resolved_end: float = field(default=0.0, init=False)

    def __enter__(self) -> BeatContext:
        base_start = (
            float(self.start_time)
            if self.start_time is not None
            else float(self.scene._beat_cursor if hasattr(self.scene, "_beat_cursor") else self.scene.get_current_time())
        )
        self._entered_start = round(base_start + max(0.0, float(self.pad_before)), 4)
        self._local_cursor = self._entered_start

        clip_dur = 0.0
        if self.narration is not None and hasattr(self.narration, "duration"):
            clip_dur = float(self.narration.duration)
        elif isinstance(self.narration, dict) and "duration" in self.narration:
            clip_dur = float(self.narration["duration"])

        if self.duration is not None:
            eff_dur = max(float(self.duration), clip_dur)
        elif clip_dur > 0.0:
            eff_dur = clip_dur
        else:
            eff_dur = 0.0

        self._resolved_end = round(self._entered_start + eff_dur, 4)
        return self

    @property
    def start(self) -> float:
        """Absolute start timestamp (in seconds) of this beat in the scene."""
        return self._entered_start

    @property
    def cursor(self) -> float:
        """Current time cursor inside this beat (updated as events are scheduled)."""
        return self._local_cursor

    @property
    def end(self) -> float:
        """Absolute end timestamp (in seconds) of this beat (before `pad_after` and exit cleanups)."""
        return max(self._resolved_end, self._local_cursor)

    @property
    def effective_duration(self) -> float:
        """Total active duration of this beat in seconds."""
        return round(max(0.0, self.end - self.start), 4)

    def rel(self, offset: float = 0.0) -> float:
        """Convert a beat-relative offset (in seconds) into an absolute scene timestamp."""
        return round(self.start + float(offset), 4)

    def t(
        self,
        word: str | None = None,
        occurrence: int = 1,
        lead_in: float = 0.0,
        offset: float = 0.0,
        default: float = 0.0,
    ) -> float:
        """Return the absolute scene timestamp when `word` is spoken in this beat's narration.

        If `word` is `None`, returns `self.start + offset`.
        If `word` is not found in `self.narration`, falls back to `self.start + default + offset`.
        """
        if word is None:
            return round(max(0.0, self.start + float(offset)), 4)

        rel_word_start: float | None = None
        if self.narration is not None:
            if hasattr(self.narration, "get_word_time"):
                rel_word_start = self.narration.get_word_time(word, occurrence=occurrence)
            elif isinstance(self.narration, dict) and "words" in self.narration:
                from voiceanim.schema import AudioClip

                clip_obj = AudioClip.from_dict(self.narration)
                rel_word_start = clip_obj.get_word_time(word, occurrence=occurrence)

        if rel_word_start is None:
            rel_word_start = float(default)

        abs_t = self.start + float(rel_word_start) - float(lead_in) + float(offset)
        return round(max(self.start, abs_t), 4)

    def word_range(self, word: str, occurrence: int = 1) -> tuple[float, float]:
        """Return the absolute `(start, end)` scene timestamps for `word` in this beat."""
        if self.narration is not None and hasattr(self.narration, "get_word_range"):
            rng = self.narration.get_word_range(word, occurrence=occurrence)
            if rng is not None:
                return (round(self.start + rng[0], 4), round(self.start + rng[1], 4))
        return (self.start, min(self.end, self.start + 0.5))

    def _resolve_at(
        self,
        at: float | str | None = None,
        word: str | None = None,
        occurrence: int = 1,
        lead_in: float = 0.0,
        offset: float = 0.0,
        relative: bool = True,
    ) -> float:
        """Resolve an event start timestamp from `at` (offset or word) or `word`."""
        if isinstance(at, str):
            return self.t(at, occurrence=occurrence, lead_in=lead_in, offset=offset)
        if word is not None:
            return self.t(word, occurrence=occurrence, lead_in=lead_in, offset=float(at or 0.0) + float(offset))
        if at is None:
            return round(self._local_cursor + float(offset), 4)
        val = float(at) + float(offset)
        return round(self.start + val if relative else val, 4)

    def add(
        self,
        event: AnimationEvent,
        drawable: Drawable,
        *,
        overlay: bool = False,
        clear_on_exit: bool = False,
    ) -> Drawable:
        """Add an animation event to the scene within this beat and update the beat cursor."""
        self.scene.add(event, drawable, overlay=overlay)
        self._local_cursor = max(self._local_cursor, float(event.end_time))
        if drawable not in self._scoped_drawables:
            self._scoped_drawables.append(drawable)
        if clear_on_exit:
            self.clear_on_exit(drawable, overlay=overlay)
        return drawable

    def sketch(
        self,
        drawable: Drawable,
        at: float | str | None = None,
        *,
        word: str | None = None,
        occurrence: int = 1,
        lead_in: float = 0.08,
        offset: float = 0.0,
        duration: float = 1.0,
        relative: bool = True,
        overlay: bool = False,
        clear_on_exit: bool = False,
        **sketch_kwargs: Any,
    ) -> Drawable:
        """Schedule a `SketchAnimation` on `drawable` inside this beat."""
        from ..animations.sketch import SketchAnimation

        st = self._resolve_at(
            at=at, word=word, occurrence=occurrence, lead_in=lead_in, offset=offset, relative=relative
        )
        ev = SketchAnimation(start_time=st, duration=float(duration), **sketch_kwargs)
        return self.add(ev, drawable, overlay=overlay, clear_on_exit=clear_on_exit)

    def fade_in(
        self,
        drawable: Drawable,
        at: float | str | None = None,
        *,
        word: str | None = None,
        occurrence: int = 1,
        lead_in: float = 0.0,
        offset: float = 0.0,
        duration: float = 0.6,
        relative: bool = True,
        overlay: bool = False,
        clear_on_exit: bool = False,
        **fade_kwargs: Any,
    ) -> Drawable:
        """Schedule a `FadeInAnimation` on `drawable` inside this beat."""
        from ..animations.fade import FadeInAnimation

        st = self._resolve_at(
            at=at, word=word, occurrence=occurrence, lead_in=lead_in, offset=offset, relative=relative
        )
        ev = FadeInAnimation(start_time=st, duration=float(duration), **fade_kwargs)
        return self.add(ev, drawable, overlay=overlay, clear_on_exit=clear_on_exit)

    def pop_in(
        self,
        drawable: Drawable,
        at: float | str | None = None,
        *,
        word: str | None = None,
        occurrence: int = 1,
        lead_in: float = 0.0,
        offset: float = 0.0,
        duration: float = 0.45,
        relative: bool = True,
        overlay: bool = False,
        clear_on_exit: bool = False,
        **pop_kwargs: Any,
    ) -> Drawable:
        """Schedule a springy `PopAnimation` on `drawable` inside this beat."""
        from ..animations.easing import PopAnimation

        st = self._resolve_at(
            at=at, word=word, occurrence=occurrence, lead_in=lead_in, offset=offset, relative=relative
        )
        ev = PopAnimation(start_time=st, duration=float(duration), **pop_kwargs)
        return self.add(ev, drawable, overlay=overlay, clear_on_exit=clear_on_exit)

    def show(
        self,
        drawable: Drawable,
        at: float | str | None = 0.0,
        *,
        word: str | None = None,
        occurrence: int = 1,
        offset: float = 0.0,
        relative: bool = True,
        overlay: bool = False,
        clear_on_exit: bool = False,
    ) -> Drawable:
        """Instantly show `drawable` at `at` (default `0.0` relative to beat start)."""
        from ..animations.visibility import Show

        st = self._resolve_at(
            at=at, word=word, occurrence=occurrence, lead_in=0.0, offset=offset, relative=relative
        )
        ev = Show(start_time=st)
        return self.add(ev, drawable, overlay=overlay, clear_on_exit=clear_on_exit)

    def hide(
        self,
        drawable: Drawable,
        at: float | str | None = None,
        *,
        word: str | None = None,
        occurrence: int = 1,
        offset: float = 0.0,
        relative: bool = True,
        overlay: bool = False,
    ) -> Drawable:
        """Instantly hide `drawable` at `at`."""
        from ..animations.visibility import Hide

        st = self._resolve_at(
            at=at, word=word, occurrence=occurrence, lead_in=0.0, offset=offset, relative=relative
        )
        ev = Hide(start_time=st)
        return self.add(ev, drawable, overlay=overlay, clear_on_exit=False)

    def wait(self, duration: float) -> float:
        """Advance the beat's internal cursor by `duration` seconds and return the new absolute time."""
        self._local_cursor = round(self._local_cursor + max(0.0, float(duration)), 4)
        return self._local_cursor

    def clear_on_exit(
        self,
        *drawables: Drawable | Sequence[Drawable],
        duration: float = 0.35,
        mode: str = "fade",
        overlay: bool = False,
    ) -> None:
        """Register drawables to be automatically cleared when this beat finishes.

        Args:
            *drawables: Drawables (or sequences of drawables) to clear at beat exit.
            duration: Duration of fade/erase cleanup (ignored for `mode="hide"`).
            mode: `"fade"` (default `FadeOutAnimation`), `"hide"` (`Hide`), or `"erase"` (`Eraser`).
            overlay: Whether the drawables belong to the overlay layer.
        """
        flat: list[Drawable] = []
        for item in drawables:
            if isinstance(item, (list, tuple)):
                flat.extend(item)
            else:
                flat.append(item)  # type: ignore[arg-type]
        if flat:
            self._exit_cleanups.append(
                _ExitCleanupSpec(drawables=flat, duration=float(duration), mode=mode, overlay=overlay)
            )

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            return

        beat_end = self.end
        cleanup_end = beat_end

        for spec in self._exit_cleanups:
            if spec.mode == "hide" or spec.duration <= 0.0:
                from ..animations.visibility import Hide

                for d in spec.drawables:
                    self.scene.add(Hide(start_time=beat_end), d, overlay=spec.overlay)
            elif spec.mode == "erase":
                from ..animations.sketch import SketchAnimation
                from ..primitives.eraser import Eraser

                eraser = Eraser(objects_to_erase=spec.drawables, drawable_cache=self.scene.drawable_cache)
                self.scene.add(
                    SketchAnimation(start_time=beat_end, duration=spec.duration),
                    eraser,
                    overlay=spec.overlay,
                )
                cleanup_end = max(cleanup_end, beat_end + spec.duration)
            else:
                from ..animations.fade import FadeOutAnimation

                for d in spec.drawables:
                    self.scene.add(
                        FadeOutAnimation(start_time=beat_end, duration=spec.duration),
                        d,
                        overlay=spec.overlay,
                    )
                cleanup_end = max(cleanup_end, beat_end + spec.duration)

        if self.transition_on_exit is not None:
            tr = self.transition_on_exit
            tr.start_time = cleanup_end
            tr.end_time = cleanup_end + tr.duration
            self.scene.add_transition(tr)
            cleanup_end = max(cleanup_end, tr.end_time)

        self._resolved_end = round(cleanup_end, 4)
        next_cursor = round(cleanup_end + max(0.0, float(self.pad_after)), 4)
        self.scene._beat_cursor = max(getattr(self.scene, "_beat_cursor", 0.0), next_cursor)
        self.scene.beats.append(self)
