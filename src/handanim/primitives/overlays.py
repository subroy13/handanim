"""Background and foreground overlay primitives: TimeDrivenDrawable, CustomTimeDrawable, CountdownTimer, ProgressBar, and BackgroundGrid."""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np

from ..core.animation import AnimationEvent, AnimationEventType
from ..core.draw_ops import OpsSet
from ..core.drawable import Drawable
from ..core.styles import FillStyle, SketchStyle, StrokeStyle
from ..stylings.color import BLACK, BLUE, GRAY, RED
from .ellipse import Circle
from .lines import Line, LinearPath
from .polygons import Rectangle
from .text import Text


class TimeDrivenAnimation(AnimationEvent):
    """Animation event that delegates per-frame rendering to a `TimeDrivenDrawable`."""

    def __init__(
        self,
        drawable: TimeDrivenDrawable,
        start_time: float = 0.0,
        duration: float = 0.0,
        easing_fun=None,
        data: dict | None = None,
    ) -> None:
        super().__init__(
            type=AnimationEventType.CREATION,
            start_time=start_time,
            duration=duration,
            easing_fun=easing_fun,
            data=data,
        )
        self.drawable = drawable

    def _apply(self, opsset: OpsSet, progress: float) -> OpsSet:
        t = self.start_time + float(progress) * self.duration
        return self.drawable.draw_at_time(t, float(progress))


class TimeDrivenDrawable(Drawable):
    """Base class for self-driving drawables whose appearance depends on scene time `t` and `[0, 1]` progress.

    Subclasses implement `draw_at_time(t: float, progress: float) -> OpsSet` and can be added
    directly to `scene.overlay.add(widget)`, `scene.background.add(widget)`, or `scene.add(widget)`
    without constructing a separate `AnimationEvent`.
    """

    def __init__(
        self,
        duration: float = 10.0,
        start_time: float = 0.0,
        stroke_style: StrokeStyle | None = None,
        sketch_style: SketchStyle | None = None,
        **kwargs,
    ) -> None:
        super().__init__(stroke_style=stroke_style, sketch_style=sketch_style, **kwargs)
        self.duration = max(0.0, float(duration))
        self.start_time = float(start_time)

    def draw_at_time(self, t: float, progress: float | None = None) -> OpsSet:
        """Render the drawable's `OpsSet` at scene timestamp `t` (in seconds)."""
        raise NotImplementedError

    def to_event(self) -> TimeDrivenAnimation:
        """Create the `TimeDrivenAnimation` event that drives this drawable over `[start_time, start_time + duration]`."""
        return TimeDrivenAnimation(
            drawable=self,
            start_time=self.start_time,
            duration=self.duration,
        )

    def draw(self) -> OpsSet:
        """Render the initial state (`t = start_time`, `progress = 0.0`) for static bounds/cache inspection."""
        return self.draw_at_time(self.start_time, 0.0)


class CustomTimeDrawable(TimeDrivenDrawable):
    """Wraps a user callback `render_fn(t: float, progress: float) -> Drawable | OpsSet` as a self-driving drawable.

    Ideal for studio repositories that want to build custom animated logos, watermarks,
    or ambient background overlays on `scene.background` or `scene.overlay`.
    """

    def __init__(
        self,
        render_fn: Callable[[float, float], Drawable | OpsSet],
        duration: float = 10.0,
        start_time: float = 0.0,
        **kwargs,
    ) -> None:
        super().__init__(duration=duration, start_time=start_time, **kwargs)
        self.render_fn = render_fn

    def draw_at_time(self, t: float, progress: float | None = None) -> OpsSet:
        if progress is None:
            progress = (
                float(np.clip((t - self.start_time) / self.duration, 0.0, 1.0))
                if self.duration > 0.0
                else 1.0
            )
        res = self.render_fn(float(t), float(progress))
        if isinstance(res, OpsSet):
            return res
        if isinstance(res, Drawable):
            return res.draw()
        raise TypeError(f"CustomTimeDrawable `render_fn` must return Drawable or OpsSet, got {type(res).__name__}")


class CountdownTimer(TimeDrivenDrawable):
    """A hand-sketched timer / countdown widget for `scene.overlay` or `scene.background`.

    Supports a circular progress arc (`style="ring"`), digital text readout (`style="digital"`),
    or both (`style="both"`), counting down or up over `duration` seconds.
    """

    def __init__(
        self,
        duration: float = 60.0,
        start_time: float = 0.0,
        position: tuple[float, float] = (500.0, 48.0),
        radius: float = 24.0,
        style: str = "both",  # "ring" | "digital" | "both"
        count_down: bool = True,
        time_format: str = "seconds",  # "seconds" ("60s") | "mm:ss" ("1:00") | "number" ("60")
        color: tuple[float, float, float] = BLUE,
        track_color: tuple[float, float, float] = GRAY,
        text_color: tuple[float, float, float] | None = None,
        warn_below: float | None = 10.0,
        warn_color: tuple[float, float, float] = RED,
        font_size: int = 16,
        font_name: str | None = None,
        stroke_width: float = 3.0,
        track_opacity: float = 0.30,
        stroke_style: StrokeStyle | None = None,
        sketch_style: SketchStyle | None = None,
        **kwargs,
    ) -> None:
        if stroke_style is None:
            stroke_style = StrokeStyle(color=color, width=stroke_width)
        if sketch_style is None:
            sketch_style = SketchStyle(roughness=0.35, disable_font_mixture=True)
        super().__init__(
            duration=duration,
            start_time=start_time,
            stroke_style=stroke_style,
            sketch_style=sketch_style,
            **kwargs,
        )
        self.position = (float(position[0]), float(position[1]))
        self.radius = float(radius)
        self.style = style.lower().strip()
        self.count_down = bool(count_down)
        self.time_format = time_format.lower().strip()
        self.color = color
        self.track_color = track_color
        self.text_color = text_color if text_color is not None else BLACK
        self.warn_below = float(warn_below) if warn_below is not None else None
        self.warn_color = warn_color
        self.font_size = int(font_size)
        self.font_name = font_name
        self.stroke_width = float(stroke_width)
        self.track_opacity = float(track_opacity)

    def _format_display_time(self, display_sec: float) -> str:
        sec_int = max(0, int(math.ceil(display_sec - 1e-6)) if self.count_down else int(math.floor(display_sec + 1e-6)))
        if self.time_format in ("mm:ss", "clock"):
            mins = sec_int // 60
            secs = sec_int % 60
            return f"{mins}:{secs:02d}"
        if self.time_format == "number":
            return str(sec_int)
        return f"{sec_int}s"

    def draw_at_time(self, t: float, progress: float | None = None) -> OpsSet:
        if progress is None:
            progress = (
                float(np.clip((t - self.start_time) / self.duration, 0.0, 1.0))
                if self.duration > 0.0
                else 1.0
            )
        p = float(np.clip(progress, 0.0, 1.0))
        elapsed = p * self.duration
        remaining = max(0.0, self.duration - elapsed)
        display_sec = remaining if self.count_down else elapsed
        arc_fraction = (1.0 - p) if self.count_down else p

        is_warn = self.warn_below is not None and remaining <= self.warn_below and self.duration > self.warn_below
        active_col = self.warn_color if is_warn else self.color

        opsset = OpsSet(initial_set=[])
        cx, cy = self.position

        if self.style in ("ring", "both"):
            # Faint circular track
            track = Circle(
                center=(cx, cy),
                radius=self.radius,
                stroke_style=StrokeStyle(
                    color=self.track_color,
                    width=max(1.5, self.stroke_width * 0.75),
                    opacity=self.track_opacity,
                ),
                sketch_style=SketchStyle(roughness=0.25),
            )
            opsset.extend(track.draw())

            # Active arc starting from 12 o'clock (-pi/2)
            if arc_fraction > 0.01:
                n_pts = max(6, int(round(36 * arc_fraction)))
                angles = np.linspace(-math.pi / 2.0, -math.pi / 2.0 + 2.0 * math.pi * arc_fraction, n_pts)
                arc_pts = [
                    (float(cx + self.radius * math.cos(a)), float(cy + self.radius * math.sin(a)))
                    for a in angles
                ]
                arc_path = LinearPath(
                    points=arc_pts,
                    stroke_style=StrokeStyle(color=active_col, width=self.stroke_width),
                    sketch_style=SketchStyle(roughness=0.25),
                )
                opsset.extend(arc_path.draw())

        if self.style in ("digital", "both"):
            label_str = self._format_display_time(display_sec)
            lbl_col = self.warn_color if is_warn else self.text_color
            lbl = Text(
                text=label_str,
                position=(cx, cy + self.font_size * 0.34),
                font_size=self.font_size,
                font_name=self.font_name,
                align="center",
                stroke_style=StrokeStyle(color=lbl_col, width=max(1.6, self.stroke_width * 0.65)),
                sketch_style=SketchStyle(roughness=0.15, disable_font_mixture=True),
            )
            opsset.extend(lbl.draw())

        return opsset


class ProgressBar(TimeDrivenDrawable):
    """A hand-sketched linear progress bar for `scene.overlay` or `scene.background`."""

    def __init__(
        self,
        duration: float = 60.0,
        start_time: float = 0.0,
        position: tuple[float, float] = (40.0, 965.0),
        width: float = 482.5,
        height: float = 8.0,
        direction: str = "horizontal",  # "horizontal" | "vertical"
        color: tuple[float, float, float] = BLUE,
        track_color: tuple[float, float, float] = GRAY,
        track_opacity: float = 0.25,
        fill_opacity: float = 0.85,
        stroke_style: StrokeStyle | None = None,
        sketch_style: SketchStyle | None = None,
        **kwargs,
    ) -> None:
        if stroke_style is None:
            stroke_style = StrokeStyle(color=color, width=1.8)
        if sketch_style is None:
            sketch_style = SketchStyle(roughness=0.35)
        super().__init__(
            duration=duration,
            start_time=start_time,
            stroke_style=stroke_style,
            sketch_style=sketch_style,
            **kwargs,
        )
        self.position = (float(position[0]), float(position[1]))
        self.width = float(width)
        self.height = float(height)
        self.direction = direction.lower().strip()
        self.color = color
        self.track_color = track_color
        self.track_opacity = float(track_opacity)
        self.fill_opacity = float(fill_opacity)

    def draw_at_time(self, t: float, progress: float | None = None) -> OpsSet:
        if progress is None:
            progress = (
                float(np.clip((t - self.start_time) / self.duration, 0.0, 1.0))
                if self.duration > 0.0
                else 1.0
            )
        p = float(np.clip(progress, 0.0, 1.0))
        x0, y0 = self.position
        opsset = OpsSet(initial_set=[])

        if self.track_opacity > 0.0:
            track = Rectangle(
                top_left=(x0, y0),
                width=self.width,
                height=self.height,
                stroke_style=StrokeStyle(color=self.track_color, width=1.2, opacity=self.track_opacity),
                fill_style=FillStyle(color=self.track_color, opacity=self.track_opacity * 0.5, fill_pattern="solid"),
                sketch_style=SketchStyle(roughness=0.2),
            )
            opsset.extend(track.draw())

        if p > 0.005:
            if self.direction == "vertical":
                fill_h = max(1.0, self.height * p)
                bar = Rectangle(
                    top_left=(x0, y0 + self.height - fill_h),
                    width=self.width,
                    height=fill_h,
                    stroke_style=StrokeStyle(color=self.color, width=1.6, opacity=self.fill_opacity),
                    fill_style=FillStyle(color=self.color, opacity=self.fill_opacity, fill_pattern="solid"),
                    sketch_style=self.sketch_style,
                )
            else:
                fill_w = max(1.0, self.width * p)
                bar = Rectangle(
                    top_left=(x0, y0),
                    width=fill_w,
                    height=self.height,
                    stroke_style=StrokeStyle(color=self.color, width=1.6, opacity=self.fill_opacity),
                    fill_style=FillStyle(color=self.color, opacity=self.fill_opacity, fill_pattern="solid"),
                    sketch_style=self.sketch_style,
                )
            opsset.extend(bar.draw())

        return opsset


class BackgroundGrid(Drawable):
    """A subtle hand-sketched paper background (`"grid"`, `"ruled"`, or `"dots"`) for `scene.background`."""

    def __init__(
        self,
        x_range: tuple[float, float] = (0.0, 562.5),
        y_range: tuple[float, float] = (0.0, 1000.0),
        spacing: float = 45.0,
        style: str = "grid",  # "grid" | "ruled" | "dots"
        color: tuple[float, float, float] = (0.72, 0.78, 0.85),
        opacity: float = 0.28,
        line_width: float = 1.0,
        roughness: float = 0.25,
        stroke_style: StrokeStyle | None = None,
        sketch_style: SketchStyle | None = None,
        **kwargs,
    ) -> None:
        if stroke_style is None:
            stroke_style = StrokeStyle(color=color, width=line_width, opacity=opacity)
        if sketch_style is None:
            sketch_style = SketchStyle(roughness=roughness)
        super().__init__(stroke_style=stroke_style, sketch_style=sketch_style, **kwargs)
        self.x_range = (float(x_range[0]), float(x_range[1]))
        self.y_range = (float(y_range[0]), float(y_range[1]))
        self.spacing = max(8.0, float(spacing))
        self.style = style.lower().strip()
        self.color = color
        self.opacity = float(opacity)

    def draw(self) -> OpsSet:
        opsset = OpsSet(initial_set=[])
        x0, x1 = self.x_range
        y0, y1 = self.y_range

        if self.style == "dots":
            xs = np.arange(x0 + self.spacing, x1, self.spacing)
            ys = np.arange(y0 + self.spacing, y1, self.spacing)
            for x in xs:
                for y in ys:
                    dot = Circle(
                        center=(float(x), float(y)),
                        radius=max(1.2, self.stroke_style.width * 1.1),
                        stroke_style=self.stroke_style,
                        fill_style=FillStyle(color=self.color, opacity=self.opacity, fill_pattern="solid"),
                        sketch_style=SketchStyle(roughness=0.1),
                    )
                    opsset.extend(dot.draw())
            return opsset

        # Horizontal lines for both "ruled" and "grid"
        ys = np.arange(y0 + self.spacing, y1, self.spacing)
        for y in ys:
            line = Line(
                start=(x0, float(y)),
                end=(x1, float(y)),
                stroke_style=self.stroke_style,
                sketch_style=self.sketch_style,
            )
            opsset.extend(line.draw())

        if self.style == "grid":
            xs = np.arange(x0 + self.spacing, x1, self.spacing)
            for x in xs:
                line = Line(
                    start=(float(x), y0),
                    end=(float(x), y1),
                    stroke_style=self.stroke_style,
                    sketch_style=self.sketch_style,
                )
                opsset.extend(line.draw())

        return opsset
