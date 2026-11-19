"""Hand-sketched BarChart and LineChart primitives for statistical storytelling."""

from __future__ import annotations

from collections.abc import Sequence

from ..core.draw_ops import OpsSet
from ..core.drawable import Drawable, DrawableGroup
from ..core.styles import FillStyle, SketchStyle, StrokeStyle
from ..stylings.color import BLACK, BLUE, GREEN, ORANGE, PURPLE, RED, TEAL
from .ellipse import Circle
from .lines import Line, LinearPath
from .polygons import Rectangle
from .text import Text

_DEFAULT_PALETTE: list[tuple[float, float, float]] = [
    BLUE,
    RED,
    GREEN,
    ORANGE,
    PURPLE,
    TEAL,
]


def _format_num(val: float) -> str:
    if abs(val - round(val)) < 1e-6:
        return str(int(round(val)))
    return f"{val:.2g}"


class BarChart(Drawable):
    """A hand-sketched bar chart with category labels, value annotations, and per-bar sub-drawables.

    Attributes:
        axes_drawable (Drawable): The L-shaped baseline and vertical axis drawable.
        bar_drawables (list[Drawable]): Individual bar (+ label/value) drawables in left-to-right order.
        bars_group (DrawableGroup): A `"series"` `DrawableGroup` of `bar_drawables` for sequential reveal.
    """

    def __init__(
        self,
        values: Sequence[float],
        labels: Sequence[str] | None = None,
        position: tuple[float, float] = (70.0, 220.0),
        width: float = 420.0,
        height: float = 260.0,
        y_range: tuple[float, float] | None = None,
        bar_colors: Sequence[tuple[float, float, float]] | tuple[float, float, float] | None = None,
        fill_opacity: float = 0.65,
        fill_strategy: str = "hachure",
        bar_width_ratio: float = 0.62,
        show_values: bool = True,
        value_suffix: str = "",
        title: str | None = None,
        font_size: int = 18,
        font_name: str | None = None,
        stroke_style: StrokeStyle | None = None,
        sketch_style: SketchStyle | None = None,
        **kwargs,
    ) -> None:
        if stroke_style is None:
            stroke_style = StrokeStyle(color=BLACK, width=2.2)
        if sketch_style is None:
            sketch_style = SketchStyle(roughness=1.0)
        super().__init__(stroke_style=stroke_style, sketch_style=sketch_style, **kwargs)

        if not values:
            raise ValueError("BarChart `values` must not be empty")
        self.values = [float(v) for v in values]
        self.labels = [str(lbl) for lbl in labels] if labels is not None else [f"#{i + 1}" for i in range(len(values))]
        self.position = (float(position[0]), float(position[1]))
        self.width = float(width)
        self.height = float(height)

        max_v = max(self.values)
        min_v = min(0.0, min(self.values))
        if y_range is not None:
            self.y_range = (float(y_range[0]), float(y_range[1]))
        else:
            top_v = max_v * 1.15 if max_v > 0 else 1.0
            self.y_range = (min_v, top_v)

        if bar_colors is None:
            self.bar_colors = [_DEFAULT_PALETTE[i % len(_DEFAULT_PALETTE)] for i in range(len(self.values))]
        elif (
            isinstance(bar_colors, tuple)
            and len(bar_colors) == 3
            and all(isinstance(c, (int, float)) for c in bar_colors)
        ):
            self.bar_colors = [bar_colors for _ in self.values]  # type: ignore[misc]
        else:
            cols: list[tuple[float, float, float]] = [
                (float(c[0]), float(c[1]), float(c[2])) for c in bar_colors  # type: ignore[index]
            ]
            self.bar_colors = [cols[i % len(cols)] for i in range(len(self.values))]

        self.fill_opacity = float(fill_opacity)
        self.fill_strategy = str(fill_strategy)
        self.bar_width_ratio = float(bar_width_ratio)
        self.show_values = bool(show_values)
        self.value_suffix = str(value_suffix)
        self.title = title
        self.font_size = int(font_size)
        self.font_name = font_name

        self.axes_drawable: DrawableGroup
        self.bar_drawables: list[DrawableGroup] = []
        self._bar_tops: list[tuple[float, float]] = []
        self._build_components()
        self.bars_group = DrawableGroup(elements=list(self.bar_drawables), grouping_method="series")

    def _val_to_y(self, val: float) -> float:
        y_min, y_max = self.y_range
        py = self.position[1]
        frac = (float(val) - y_min) / max(1e-9, y_max - y_min)
        return py + self.height - frac * self.height

    def get_bar_top(self, index: int) -> tuple[float, float]:
        """Return the world-space `(x, y)` coordinates of the top-center of bar `index`."""
        return self._bar_tops[index]

    def _build_components(self) -> None:
        px, py = self.position
        y_zero = self._val_to_y(0.0)

        axis_elements: list[Drawable] = [
            Line(
                start=(px, py),
                end=(px, py + self.height),
                stroke_style=self.stroke_style,
                sketch_style=self.sketch_style,
            ),
            Line(
                start=(px, y_zero),
                end=(px + self.width, y_zero),
                stroke_style=self.stroke_style,
                sketch_style=self.sketch_style,
            ),
        ]
        if self.title:
            axis_elements.append(
                Text(
                    text=self.title,
                    position=(px + self.width / 2.0, py - self.font_size * 0.9),
                    font_size=int(self.font_size * 1.2),
                    font_name=self.font_name,
                    align="center",
                    stroke_style=self.stroke_style,
                    sketch_style=SketchStyle(roughness=0.25, disable_font_mixture=True),
                )
            )
        self.axes_drawable = DrawableGroup(elements=axis_elements, grouping_method="parallel")

        n = len(self.values)
        slot_w = self.width / n
        bar_w = slot_w * self.bar_width_ratio

        self.bar_drawables = []
        self._bar_tops = []

        for i, val in enumerate(self.values):
            col = self.bar_colors[i]
            cx = px + (i + 0.5) * slot_w
            bx = cx - bar_w / 2.0
            y_val = self._val_to_y(val)
            top_y = min(y_zero, y_val)
            bar_h = max(2.0, abs(y_zero - y_val))
            self._bar_tops.append((cx, top_y))

            rect = Rectangle(
                top_left=(bx, top_y),
                width=bar_w,
                height=bar_h,
                stroke_style=StrokeStyle(color=col, width=self.stroke_style.width),
                fill_style=FillStyle(
                    color=col,
                    opacity=self.fill_opacity,
                    fill_pattern=self.fill_strategy,
                    hachure_gap=6.0,
                ),
                sketch_style=self.sketch_style,
            )
            bar_items: list[Drawable] = [rect]

            if i < len(self.labels) and self.labels[i]:
                lbl = Text(
                    text=self.labels[i],
                    position=(cx, py + self.height + self.font_size * 0.95),
                    font_size=self.font_size,
                    font_name=self.font_name,
                    align="center",
                    stroke_style=StrokeStyle(color=self.stroke_style.color, width=1.6),
                    sketch_style=SketchStyle(roughness=0.2, disable_font_mixture=True),
                )
                bar_items.append(lbl)

            if self.show_values:
                val_lbl = Text(
                    text=f"{_format_num(val)}{self.value_suffix}",
                    position=(cx, top_y - self.font_size * 0.45),
                    font_size=max(12, int(self.font_size * 0.9)),
                    font_name=self.font_name,
                    align="center",
                    stroke_style=StrokeStyle(color=col, width=1.8),
                    sketch_style=SketchStyle(roughness=0.2, disable_font_mixture=True),
                )
                bar_items.append(val_lbl)

            self.bar_drawables.append(DrawableGroup(elements=bar_items, grouping_method="parallel"))

    def draw(self) -> OpsSet:
        opsset = OpsSet(initial_set=[])
        opsset.extend(self.axes_drawable.draw())
        for b in self.bar_drawables:
            opsset.extend(b.draw())
        return opsset


class LineChart(Drawable):
    """A hand-sketched line chart with data markers, optional category labels, and point coordinate lookup."""

    def __init__(
        self,
        values: Sequence[float],
        x_values: Sequence[float] | None = None,
        labels: Sequence[str] | None = None,
        position: tuple[float, float] = (70.0, 220.0),
        width: float = 420.0,
        height: float = 260.0,
        y_range: tuple[float, float] | None = None,
        color: tuple[float, float, float] = BLUE,
        show_points: bool = True,
        point_radius: float = 5.0,
        title: str | None = None,
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

        if not values:
            raise ValueError("LineChart `values` must not be empty")
        self.values = [float(v) for v in values]
        self.x_values = (
            [float(x) for x in x_values]
            if x_values is not None
            else [float(i) for i in range(len(self.values))]
        )
        self.labels = [str(lbl) for lbl in labels] if labels is not None else None
        self.position = (float(position[0]), float(position[1]))
        self.width = float(width)
        self.height = float(height)

        max_v = max(self.values)
        min_v = min(0.0, min(self.values))
        if y_range is not None:
            self.y_range = (float(y_range[0]), float(y_range[1]))
        else:
            span = max(1.0, max_v - min_v)
            self.y_range = (min_v, max_v + span * 0.12)

        self.color = color
        self.show_points = bool(show_points)
        self.point_radius = float(point_radius)
        self.title = title
        self.font_size = int(font_size)

    def get_point(self, index: int) -> tuple[float, float]:
        """Return the world-space `(wx, wy)` coordinates of the `index`-th data point."""
        px, py = self.position
        x_min, x_max = min(self.x_values), max(self.x_values)
        y_min, y_max = self.y_range

        xv = self.x_values[index]
        yv = self.values[index]
        x_frac = (xv - x_min) / max(1e-9, x_max - x_min) if x_max > x_min else 0.5
        y_frac = (yv - y_min) / max(1e-9, y_max - y_min)
        wx = px + 20.0 + x_frac * max(10.0, self.width - 40.0)
        wy = py + self.height - y_frac * self.height
        return (wx, wy)

    def draw(self) -> OpsSet:
        opsset = OpsSet(initial_set=[])
        px, py = self.position

        # Axes frame
        opsset.extend(
            Line(
                start=(px, py),
                end=(px, py + self.height),
                stroke_style=self.stroke_style,
                sketch_style=self.sketch_style,
            ).draw()
        )
        opsset.extend(
            Line(
                start=(px, py + self.height),
                end=(px + self.width, py + self.height),
                stroke_style=self.stroke_style,
                sketch_style=self.sketch_style,
            ).draw()
        )

        if self.title:
            opsset.extend(
                Text(
                    text=self.title,
                    position=(px + self.width / 2.0, py - self.font_size * 0.9),
                    font_size=int(self.font_size * 1.2),
                    align="center",
                    stroke_style=self.stroke_style,
                    sketch_style=SketchStyle(roughness=0.25, disable_font_mixture=True),
                ).draw()
            )

        pts = [self.get_point(i) for i in range(len(self.values))]
        if len(pts) >= 2:
            line_path = LinearPath(
                points=pts,
                stroke_style=StrokeStyle(color=self.color, width=max(2.5, self.stroke_style.width * 1.2)),
                sketch_style=self.sketch_style,
            )
            opsset.extend(line_path.draw())

        if self.show_points:
            for pt in pts:
                dot = Circle(
                    center=pt,
                    radius=self.point_radius,
                    stroke_style=StrokeStyle(color=self.color, width=1.8),
                    fill_style=FillStyle(color=self.color, opacity=0.9, fill_pattern="solid"),
                    sketch_style=SketchStyle(roughness=0.6),
                )
                opsset.extend(dot.draw())

        if self.labels:
            for i, lbl_str in enumerate(self.labels[: len(pts)]):
                wx, _ = pts[i]
                lbl = Text(
                    text=lbl_str,
                    position=(wx, py + self.height + self.font_size * 0.95),
                    font_size=self.font_size,
                    align="center",
                    stroke_style=StrokeStyle(color=self.stroke_style.color, width=1.6),
                    sketch_style=SketchStyle(roughness=0.2, disable_font_mixture=True),
                )
                opsset.extend(lbl.draw())

        return opsset
