"""Hand-sketched coordinate axes, number lines, and function graphs for educational videos."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

import numpy as np

from ..core.draw_ops import OpsSet
from ..core.drawable import Drawable, DrawableGroup
from ..core.styles import FillStyle, SketchStyle, StrokeStyle
from ..stylings.color import BLACK, BLUE, RED
from .arrow import Arrow
from .ellipse import Circle
from .lines import Line, LinearPath
from .text import Text


def _format_tick_number(val: float) -> str:
    if abs(val - round(val)) < 1e-6:
        return str(int(round(val)))
    return f"{val:.2g}"


class NumberLine(Drawable):
    """A hand-sketched 1D number line with ticks, optional number labels, and coordinate conversion.

    In `handanim`'s world coordinate system (top-left origin, `y` downward), the number line
    extends horizontally from `position = (x0, y0)` to `(x0 + length, y0)`.
    """

    def __init__(
        self,
        x_range: tuple[float, float] = (-5.0, 5.0),
        length: float = 400.0,
        position: tuple[float, float] = (80.0, 500.0),
        tick_step: float = 1.0,
        tick_size: float = 12.0,
        include_ticks: bool = True,
        include_numbers: bool = True,
        include_arrows: bool = True,
        font_size: int = 20,
        label: str | None = None,
        stroke_style: StrokeStyle | None = None,
        sketch_style: SketchStyle | None = None,
        **kwargs,
    ) -> None:
        if stroke_style is None:
            stroke_style = StrokeStyle(color=BLACK, width=2.2)
        if sketch_style is None:
            sketch_style = SketchStyle(roughness=1.0)
        super().__init__(stroke_style=stroke_style, sketch_style=sketch_style, **kwargs)
        self.x_range = (float(x_range[0]), float(x_range[1]))
        if self.x_range[1] <= self.x_range[0]:
            raise ValueError("NumberLine `x_range[1]` must be greater than `x_range[0]`")
        self.length = float(length)
        self.position = (float(position[0]), float(position[1]))
        self.tick_step = float(tick_step)
        self.tick_size = float(tick_size)
        self.include_ticks = bool(include_ticks)
        self.include_numbers = bool(include_numbers)
        self.include_arrows = bool(include_arrows)
        self.font_size = int(font_size)
        self.label = label

    def n2p(self, value: float) -> tuple[float, float]:
        """Map a scalar number `value` to its world-space `(x, y)` point on the number line."""
        x_min, x_max = self.x_range
        frac = (float(value) - x_min) / (x_max - x_min)
        wx = self.position[0] + frac * self.length
        wy = self.position[1]
        return (wx, wy)

    def p2n(self, point: tuple[float, float]) -> float:
        """Map a world-space point `(wx, wy)` back to the scalar value on the number line."""
        x_min, x_max = self.x_range
        frac = (float(point[0]) - self.position[0]) / max(1e-9, self.length)
        return x_min + frac * (x_max - x_min)

    def draw(self) -> OpsSet:
        opsset = OpsSet(initial_set=[])
        x0, y0 = self.position
        x1 = x0 + self.length

        if self.include_arrows:
            mid_x = (x0 + x1) / 2.0
            left_arrow = Arrow(
                start_point=(mid_x, y0),
                end_point=(x0, y0),
                arrow_head_size=10.0,
                stroke_style=self.stroke_style,
                sketch_style=self.sketch_style,
            )
            right_arrow = Arrow(
                start_point=(mid_x, y0),
                end_point=(x1, y0),
                arrow_head_size=10.0,
                stroke_style=self.stroke_style,
                sketch_style=self.sketch_style,
            )
            opsset.extend(left_arrow.draw())
            opsset.extend(right_arrow.draw())
        else:
            axis_line = Line(
                start=(x0, y0),
                end=(x1, y0),
                stroke_style=self.stroke_style,
                sketch_style=self.sketch_style,
            )
            opsset.extend(axis_line.draw())

        if self.tick_step > 0 and (self.include_ticks or self.include_numbers):
            x_min, x_max = self.x_range
            start_tick = math.ceil(x_min / self.tick_step - 1e-7) * self.tick_step
            val = start_tick
            half_tick = self.tick_size / 2.0
            while val <= x_max + 1e-7:
                tx, ty = self.n2p(val)
                if self.include_ticks:
                    tick = Line(
                        start=(tx, ty - half_tick),
                        end=(tx, ty + half_tick),
                        stroke_style=self.stroke_style,
                        sketch_style=self.sketch_style,
                    )
                    opsset.extend(tick.draw())
                if self.include_numbers:
                    lbl_str = _format_tick_number(val)
                    lbl = Text(
                        text=lbl_str,
                        position=(tx, ty + half_tick + self.font_size * 0.8),
                        font_size=self.font_size,
                        align="center",
                        stroke_style=StrokeStyle(color=self.stroke_style.color, width=max(1.5, self.stroke_style.width * 0.8)),
                        sketch_style=SketchStyle(roughness=0.2, disable_font_mixture=True),
                    )
                    opsset.extend(lbl.draw())
                val += self.tick_step

        if self.label:
            title_lbl = Text(
                text=self.label,
                position=(x1 + 14.0, y0 + self.font_size * 0.3),
                font_size=int(self.font_size * 1.1),
                stroke_style=self.stroke_style,
                sketch_style=SketchStyle(roughness=0.3, disable_font_mixture=True),
            )
            opsset.extend(title_lbl.draw())

        return opsset


class FunctionGraph(Drawable):
    """A hand-sketched curve $y = f(x)$ plotted on an `Axes` coordinate system."""

    def __init__(
        self,
        func: Callable[[float], float],
        axes: Axes,
        x_range: tuple[float, float] | None = None,
        num_samples: int = 120,
        color: tuple[float, float, float] = BLUE,
        stroke_width: float = 3.0,
        dashed: bool = False,
        dash_length: float = 10.0,
        gap_length: float = 6.0,
        clip_to_axes: bool = True,
        stroke_style: StrokeStyle | None = None,
        sketch_style: SketchStyle | None = None,
        **kwargs,
    ) -> None:
        if stroke_style is None:
            stroke_style = StrokeStyle(color=color, width=stroke_width)
        if sketch_style is None:
            sketch_style = SketchStyle(roughness=0.8)
        super().__init__(stroke_style=stroke_style, sketch_style=sketch_style, **kwargs)
        self.func = func
        self.axes = axes
        self.x_range = x_range if x_range is not None else axes.x_range
        self.num_samples = max(4, int(num_samples))
        self.dashed = bool(dashed)
        self.dash_length = float(dash_length)
        self.gap_length = float(gap_length)
        self.clip_to_axes = bool(clip_to_axes)

    def draw(self) -> OpsSet:
        x_min, x_max = float(self.x_range[0]), float(self.x_range[1])
        y_min, y_max = self.axes.y_range
        xs = np.linspace(x_min, x_max, self.num_samples)

        segments: list[list[tuple[float, float]]] = []
        current_seg: list[tuple[float, float]] = []

        for x_val in xs:
            try:
                y_val = float(self.func(float(x_val)))
            except Exception:
                y_val = float("nan")
            if not math.isfinite(y_val):
                if len(current_seg) >= 2:
                    segments.append(current_seg)
                current_seg = []
                continue
            if self.clip_to_axes and (y_val < y_min or y_val > y_max):
                if len(current_seg) >= 2:
                    segments.append(current_seg)
                current_seg = []
                continue
            current_seg.append(self.axes.c2p(float(x_val), y_val))

        if len(current_seg) >= 2:
            segments.append(current_seg)

        opsset = OpsSet(initial_set=[])
        for seg in segments:
            if not self.dashed:
                path = LinearPath(
                    points=seg,
                    stroke_style=self.stroke_style,
                    sketch_style=self.sketch_style,
                )
                opsset.extend(path.draw())
            else:
                opsset.extend(self._draw_dashed_segment(seg))
        return opsset

    def _draw_dashed_segment(self, points: list[tuple[float, float]]) -> OpsSet:
        opsset = OpsSet(initial_set=[])
        cycle = max(2.0, self.dash_length + self.gap_length)
        acc = 0.0
        for i in range(len(points) - 1):
            p0 = np.array(points[i], dtype=float)
            p1 = np.array(points[i + 1], dtype=float)
            seg_len = float(np.linalg.norm(p1 - p0))
            if seg_len < 1e-6:
                continue
            pos_in_cycle = acc % cycle
            if pos_in_cycle < self.dash_length:
                line = Line(
                    start=(float(p0[0]), float(p0[1])),
                    end=(float(p1[0]), float(p1[1])),
                    stroke_style=self.stroke_style,
                    sketch_style=self.sketch_style,
                )
                opsset.extend(line.draw())
            acc += seg_len
        return opsset


class Axes(Drawable):
    """A hand-sketched 2D Cartesian coordinate system with ticks, labels, and plotting helpers.

    Maps mathematical coordinates `(x, y)` (where `y` increases upward) onto `handanim`'s
    world coordinate box anchored at `position = (left, top)` with size `(width, height)`.
    """

    def __init__(
        self,
        x_range: tuple[float, float] = (-5.0, 5.0),
        y_range: tuple[float, float] = (-3.0, 3.0),
        width: float = 420.0,
        height: float = 280.0,
        position: tuple[float, float] = (70.0, 220.0),
        x_step: float | None = 1.0,
        y_step: float | None = 1.0,
        tick_size: float = 8.0,
        include_ticks: bool = True,
        include_numbers: bool = False,
        include_arrows: bool = True,
        x_label: str | None = None,
        y_label: str | None = None,
        font_size: int = 18,
        stroke_style: StrokeStyle | None = None,
        sketch_style: SketchStyle | None = None,
        **kwargs,
    ) -> None:
        if stroke_style is None:
            stroke_style = StrokeStyle(color=BLACK, width=2.2)
        if sketch_style is None:
            sketch_style = SketchStyle(roughness=1.0)
        super().__init__(stroke_style=stroke_style, sketch_style=sketch_style, **kwargs)
        self.x_range = (float(x_range[0]), float(x_range[1]))
        self.y_range = (float(y_range[0]), float(y_range[1]))
        if self.x_range[1] <= self.x_range[0] or self.y_range[1] <= self.y_range[0]:
            raise ValueError("Axes `x_range` and `y_range` must have max > min")
        self.width = float(width)
        self.height = float(height)
        self.position = (float(position[0]), float(position[1]))
        self.x_step = float(x_step) if x_step is not None else None
        self.y_step = float(y_step) if y_step is not None else None
        self.tick_size = float(tick_size)
        self.include_ticks = bool(include_ticks)
        self.include_numbers = bool(include_numbers)
        self.include_arrows = bool(include_arrows)
        self.x_label = x_label
        self.y_label = y_label
        self.font_size = int(font_size)

    def c2p(self, x: float, y: float) -> tuple[float, float]:
        """Convert mathematical coordinates `(x, y)` into world coordinates `(wx, wy)`."""
        x_min, x_max = self.x_range
        y_min, y_max = self.y_range
        px, py = self.position
        wx = px + ((float(x) - x_min) / (x_max - x_min)) * self.width
        wy = py + self.height - ((float(y) - y_min) / (y_max - y_min)) * self.height
        return (wx, wy)

    def p2c(self, wx: float, wy: float) -> tuple[float, float]:
        """Convert world coordinates `(wx, wy)` into mathematical coordinates `(x, y)`."""
        x_min, x_max = self.x_range
        y_min, y_max = self.y_range
        px, py = self.position
        x = x_min + ((float(wx) - px) / max(1e-9, self.width)) * (x_max - x_min)
        y = y_min + ((py + self.height - float(wy)) / max(1e-9, self.height)) * (y_max - y_min)
        return (x, y)

    @property
    def origin_point(self) -> tuple[float, float]:
        """World-space point where the x-axis and y-axis intersect (clamped to `[x_range, y_range]`)."""
        ox = float(np.clip(0.0, self.x_range[0], self.x_range[1]))
        oy = float(np.clip(0.0, self.y_range[0], self.y_range[1]))
        return self.c2p(ox, oy)

    def plot(
        self,
        func: Callable[[float], float],
        x_range: tuple[float, float] | None = None,
        num_samples: int = 120,
        color: tuple[float, float, float] = BLUE,
        stroke_width: float = 3.0,
        dashed: bool = False,
        **kwargs,
    ) -> FunctionGraph:
        """Create a `FunctionGraph` drawable for `y = func(x)` on these axes."""
        return FunctionGraph(
            func=func,
            axes=self,
            x_range=x_range,
            num_samples=num_samples,
            color=color,
            stroke_width=stroke_width,
            dashed=dashed,
            **kwargs,
        )

    def plot_scatter(
        self,
        points: Sequence[tuple[float, float]],
        radius: float = 5.5,
        color: tuple[float, float, float] = RED,
        fill_opacity: float = 0.85,
        grouping_method: str = "parallel",
    ) -> DrawableGroup:
        """Create a `DrawableGroup` of hand-sketched scatter dots at mathematical `(x, y)` coordinates."""
        dots: list[Drawable] = []
        for x_val, y_val in points:
            wx, wy = self.c2p(float(x_val), float(y_val))
            dot = Circle(
                center=(wx, wy),
                radius=float(radius),
                stroke_style=StrokeStyle(color=color, width=1.8),
                fill_style=FillStyle(color=color, opacity=fill_opacity, fill_pattern="solid"),
                sketch_style=SketchStyle(roughness=0.8),
            )
            dots.append(dot)
        return DrawableGroup(elements=dots, grouping_method=grouping_method)

    def draw(self) -> OpsSet:
        opsset = OpsSet(initial_set=[])
        ox, oy = self.origin_point
        x_left, _ = self.c2p(self.x_range[0], 0.0)
        x_right, _ = self.c2p(self.x_range[1], 0.0)
        _, y_bottom = self.c2p(0.0, self.y_range[0])
        _, y_top = self.c2p(0.0, self.y_range[1])

        if self.include_arrows:
            x_axis = Arrow(
                start_point=(x_left, oy),
                end_point=(x_right, oy),
                arrow_head_size=10.0,
                stroke_style=self.stroke_style,
                sketch_style=self.sketch_style,
            )
            y_axis = Arrow(
                start_point=(ox, y_bottom),
                end_point=(ox, y_top),
                arrow_head_size=10.0,
                stroke_style=self.stroke_style,
                sketch_style=self.sketch_style,
            )
            opsset.extend(x_axis.draw())
            opsset.extend(y_axis.draw())
        else:
            opsset.extend(
                Line(start=(x_left, oy), end=(x_right, oy), stroke_style=self.stroke_style, sketch_style=self.sketch_style).draw()
            )
            opsset.extend(
                Line(start=(ox, y_bottom), end=(ox, y_top), stroke_style=self.stroke_style, sketch_style=self.sketch_style).draw()
            )

        half_t = self.tick_size / 2.0
        # X ticks
        if self.x_step is not None and self.x_step > 0 and (self.include_ticks or self.include_numbers):
            x_min, x_max = self.x_range
            vx = math.ceil(x_min / self.x_step - 1e-7) * self.x_step
            while vx <= x_max + 1e-7:
                if abs(vx) > 1e-7 or (self.x_range[0] > 0 or self.x_range[1] < 0):
                    tx, _ = self.c2p(vx, 0.0)
                    if self.include_ticks:
                        opsset.extend(
                            Line(
                                start=(tx, oy - half_t),
                                end=(tx, oy + half_t),
                                stroke_style=self.stroke_style,
                                sketch_style=self.sketch_style,
                            ).draw()
                        )
                    if self.include_numbers:
                        lbl = Text(
                            text=_format_tick_number(vx),
                            position=(tx, oy + half_t + self.font_size * 0.85),
                            font_size=self.font_size,
                            align="center",
                            stroke_style=StrokeStyle(color=self.stroke_style.color, width=1.6),
                            sketch_style=SketchStyle(roughness=0.2, disable_font_mixture=True),
                        )
                        opsset.extend(lbl.draw())
                vx += self.x_step

        # Y ticks
        if self.y_step is not None and self.y_step > 0 and (self.include_ticks or self.include_numbers):
            y_min, y_max = self.y_range
            vy = math.ceil(y_min / self.y_step - 1e-7) * self.y_step
            while vy <= y_max + 1e-7:
                if abs(vy) > 1e-7 or (self.y_range[0] > 0 or self.y_range[1] < 0):
                    _, ty = self.c2p(0.0, vy)
                    if self.include_ticks:
                        opsset.extend(
                            Line(
                                start=(ox - half_t, ty),
                                end=(ox + half_t, ty),
                                stroke_style=self.stroke_style,
                                sketch_style=self.sketch_style,
                            ).draw()
                        )
                    if self.include_numbers:
                        lbl = Text(
                            text=_format_tick_number(vy),
                            position=(ox - half_t - 6.0, ty + self.font_size * 0.3),
                            font_size=self.font_size,
                            align="right",
                            stroke_style=StrokeStyle(color=self.stroke_style.color, width=1.6),
                            sketch_style=SketchStyle(roughness=0.2, disable_font_mixture=True),
                        )
                        opsset.extend(lbl.draw())
                vy += self.y_step

        if self.x_label:
            xl = Text(
                text=self.x_label,
                position=(x_right + 10.0, oy + self.font_size * 0.35),
                font_size=int(self.font_size * 1.15),
                stroke_style=self.stroke_style,
                sketch_style=SketchStyle(roughness=0.2, disable_font_mixture=True),
            )
            opsset.extend(xl.draw())

        if self.y_label:
            yl = Text(
                text=self.y_label,
                position=(ox, y_top - self.font_size * 0.9),
                font_size=int(self.font_size * 1.15),
                align="center",
                stroke_style=self.stroke_style,
                sketch_style=SketchStyle(roughness=0.2, disable_font_mixture=True),
            )
            opsset.extend(yl.draw())

        return opsset
