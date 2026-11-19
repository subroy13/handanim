"""Editorial emphasis primitives: HighlightMarker, CurlyBrace, CalloutBubble, and CrossOut."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from ..core.draw_ops import BoundingBox, OpsSet
from ..core.drawable import Drawable
from ..core.styles import FillStyle, SketchStyle, StrokeStyle
from ..stylings.color import BLACK, RED, WHITE, YELLOW
from .lines import Line, LinearPath
from .polygons import Polygon
from .text import Text


def _resolve_bbox(
    target_or_bbox: Drawable | BoundingBox | tuple[Any, ...],
) -> BoundingBox:
    if isinstance(target_or_bbox, BoundingBox):
        return target_or_bbox
    if isinstance(target_or_bbox, Drawable):
        return target_or_bbox.get_bbox()
    if isinstance(target_or_bbox, (tuple, list)):
        if len(target_or_bbox) == 4 and all(isinstance(v, (int, float)) for v in target_or_bbox):
            x0, y0, x1, y1 = (float(v) for v in target_or_bbox)
            return BoundingBox(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        if len(target_or_bbox) == 2 and all(isinstance(p, (tuple, list)) and len(p) == 2 for p in target_or_bbox):
            (x0, y0), (x1, y1) = target_or_bbox
            return BoundingBox(
                min(float(x0), float(x1)),
                min(float(y0), float(y1)),
                max(float(x0), float(x1)),
                max(float(y0), float(y1)),
            )
    raise TypeError(f"Expected Drawable, BoundingBox, or coordinate bounds, got {type(target_or_bbox).__name__}")


class HighlightMarker(Drawable):
    """A translucent chisel-tip highlighter stroke or sketchy underline over a target drawable or bbox.

    Usage::

        hl = HighlightMarker(key_term, color=YELLOW, opacity=0.35)
        scene.add(SketchAnimation(start_time=1.0, duration=0.6), hl)
    """

    is_emphasis_overlay: bool = True

    def __init__(
        self,
        target: Drawable | BoundingBox | tuple[Any, ...],
        color: tuple[float, float, float] = YELLOW,
        opacity: float = 0.35,
        padding: float = 6.0,
        style: str = "marker",  # "marker" | "underline" | "box"
        passes: int = 2,
        stroke_style: StrokeStyle | None = None,
        sketch_style: SketchStyle | None = None,
        **kwargs,
    ) -> None:
        bbox = _resolve_bbox(target)
        height = max(12.0, bbox.height + 2.0 * float(padding))
        default_width = height * 0.65 if style == "marker" else 3.5
        if stroke_style is None:
            stroke_style = StrokeStyle(color=color, width=default_width, opacity=opacity)
        if sketch_style is None:
            sketch_style = SketchStyle(roughness=0.9)
        super().__init__(stroke_style=stroke_style, sketch_style=sketch_style, **kwargs)
        self.target_bbox = bbox
        self.color = color
        self.opacity = float(opacity)
        self.padding = float(padding)
        self.style = style
        self.passes = max(1, int(passes))

    def draw(self) -> OpsSet:
        opsset = OpsSet(initial_set=[])
        b = self.target_bbox
        x0 = b.min_x - self.padding
        x1 = b.max_x + self.padding
        y0 = b.min_y - self.padding * 0.5
        y1 = b.max_y + self.padding * 0.5

        if self.style == "underline":
            uy = b.max_y + self.padding * 0.6
            for i in range(self.passes):
                dy = i * 2.5
                line = Line(
                    start=(x0, uy + dy),
                    end=(x1, uy + dy - 1.0),
                    stroke_style=StrokeStyle(color=self.color, width=self.stroke_style.width, opacity=self.opacity),
                    sketch_style=self.sketch_style,
                )
                opsset.extend(line.draw())
            return opsset

        if self.style == "box":
            poly = Polygon(
                points=[(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                stroke_style=StrokeStyle(color=self.color, width=self.stroke_style.width, opacity=self.opacity),
                sketch_style=self.sketch_style,
            )
            return poly.draw()

        # Default "marker": wide translucent horizontal sweeps across the target's vertical span
        cy = (y0 + y1) / 2.0
        span_h = max(8.0, y1 - y0)
        stroke_w = max(6.0, span_h / max(1.0, self.passes * 0.72))
        marker_stroke = StrokeStyle(color=self.color, width=stroke_w, opacity=self.opacity)
        for i in range(self.passes):
            if self.passes == 1:
                py = cy
            else:
                frac = i / (self.passes - 1) - 0.5
                py = cy + frac * span_h * 0.42
            start_pt = (x0, py) if i % 2 == 0 else (x1, py)
            end_pt = (x1, py) if i % 2 == 0 else (x0, py)
            sweep = Line(
                start=start_pt,
                end=end_pt,
                stroke_style=marker_stroke,
                sketch_style=self.sketch_style,
            )
            opsset.extend(sweep.draw())
        return opsset


class CurlyBrace(Drawable):
    """A hand-drawn curly brace (`{`) spanning a drawable or two endpoints, with an optional label.

    Attributes:
        tip_point (tuple[float, float]): World-space coordinates of the central point of the brace.
        label_position (tuple[float, float]): Suggested anchor point for a text/math label outside the tip.
    """

    is_emphasis_overlay: bool = True

    def __init__(
        self,
        target_or_p1: Drawable | BoundingBox | tuple[float, float],
        p2: tuple[float, float] | None = None,
        direction: str = "down",  # "down" | "up" | "left" | "right"
        amplitude: float = 16.0,
        offset: float = 8.0,
        label: str | None = None,
        font_size: int = 22,
        font_name: str | None = None,
        stroke_style: StrokeStyle | None = None,
        sketch_style: SketchStyle | None = None,
        **kwargs,
    ) -> None:
        if stroke_style is None:
            stroke_style = StrokeStyle(color=BLACK, width=2.2)
        if sketch_style is None:
            sketch_style = SketchStyle(roughness=0.7)
        super().__init__(stroke_style=stroke_style, sketch_style=sketch_style, **kwargs)

        self.direction = direction.lower()
        self.amplitude = float(amplitude)
        self.offset = float(offset)
        self.label = label
        self.font_size = int(font_size)
        self.font_name = font_name

        if p2 is not None and isinstance(target_or_p1, (tuple, list)) and len(target_or_p1) == 2:
            self.p1 = (float(target_or_p1[0]), float(target_or_p1[1]))
            self.p2 = (float(p2[0]), float(p2[1]))
        else:
            bbox = _resolve_bbox(target_or_p1)
            if self.direction == "down":
                self.p1 = (bbox.min_x, bbox.max_y + self.offset)
                self.p2 = (bbox.max_x, bbox.max_y + self.offset)
            elif self.direction == "up":
                self.p1 = (bbox.min_x, bbox.min_y - self.offset)
                self.p2 = (bbox.max_x, bbox.min_y - self.offset)
            elif self.direction == "left":
                self.p1 = (bbox.min_x - self.offset, bbox.min_y)
                self.p2 = (bbox.min_x - self.offset, bbox.max_y)
            elif self.direction == "right":
                self.p1 = (bbox.max_x + self.offset, bbox.min_y)
                self.p2 = (bbox.max_x + self.offset, bbox.max_y)
            else:
                raise ValueError("CurlyBrace `direction` must be 'down', 'up', 'left', or 'right'")

        self.tip_point, self.label_position, self._curve_points = self._compute_brace_geometry()

    def _compute_brace_geometry(
        self,
    ) -> tuple[tuple[float, float], tuple[float, float], list[tuple[float, float]]]:
        p1 = np.array(self.p1, dtype=float)
        p2 = np.array(self.p2, dtype=float)
        vec = p2 - p1
        length = float(np.linalg.norm(vec))
        if length < 1e-6:
            pt = (float(p1[0]), float(p1[1]))
            return pt, pt, [pt]

        u = vec / length
        # Outward normal based on direction
        if self.direction == "down":
            n = np.array([0.0, 1.0])
        elif self.direction == "up":
            n = np.array([0.0, -1.0])
        elif self.direction == "left":
            n = np.array([-1.0, 0.0])
        elif self.direction == "right":
            n = np.array([1.0, 0.0])
        else:
            n = np.array([-u[1], u[0]])

        amp = min(self.amplitude, max(6.0, length * 0.22))
        # Parameterize brace profile along s in [0, 1]
        s_vals = np.linspace(0.0, 1.0, 41)
        pts: list[tuple[float, float]] = []
        for s in s_vals:
            if s < 0.12:
                t = s / 0.12
                h = 0.5 * (1.0 - math.cos(math.pi * t * 0.5))
            elif s < 0.38:
                h = 0.5
            elif s <= 0.5:
                t = (s - 0.38) / 0.12
                h = 0.5 + 0.5 * (1.0 - math.cos(math.pi * t * 0.5))
            elif s <= 0.62:
                t = (0.62 - s) / 0.12
                h = 0.5 + 0.5 * (1.0 - math.cos(math.pi * t * 0.5))
            elif s <= 0.88:
                h = 0.5
            else:
                t = (1.0 - s) / 0.12
                h = 0.5 * (1.0 - math.cos(math.pi * t * 0.5))
            pos = p1 + s * vec + (h * amp) * n
            pts.append((float(pos[0]), float(pos[1])))

        mid = 0.5 * (p1 + p2)
        tip = mid + amp * n
        lbl_pos = tip + (self.font_size * 0.95 + 6.0) * n
        return (float(tip[0]), float(tip[1])), (float(lbl_pos[0]), float(lbl_pos[1])), pts

    def draw(self) -> OpsSet:
        opsset = OpsSet(initial_set=[])
        path = LinearPath(
            points=self._curve_points,
            stroke_style=self.stroke_style,
            sketch_style=self.sketch_style,
        )
        opsset.extend(path.draw())

        if self.label:
            align = "center"
            if self.direction == "left":
                align = "right"
            elif self.direction == "right":
                align = "left"
            lbl = Text(
                text=self.label,
                position=self.label_position,
                font_size=self.font_size,
                font_name=self.font_name,
                align=align,
                stroke_style=self.stroke_style,
                sketch_style=SketchStyle(roughness=0.25, disable_font_mixture=True),
            )
            opsset.extend(lbl.draw())
        return opsset


class CalloutBubble(Drawable):
    """A hand-sketched speech or annotation callout bubble with a pointer tail aimed at `tail_target`."""

    is_emphasis_overlay: bool = True

    def __init__(
        self,
        text: str,
        position: tuple[float, float] = (100.0, 100.0),
        tail_target: Drawable | tuple[float, float] | None = None,
        width: float | None = None,
        height: float | None = None,
        padding: float = 16.0,
        font_size: int = 22,
        font_name: str | None = None,
        fill_color: tuple[float, float, float] = WHITE,
        fill_opacity: float = 0.92,
        stroke_style: StrokeStyle | None = None,
        sketch_style: SketchStyle | None = None,
        **kwargs,
    ) -> None:
        if stroke_style is None:
            stroke_style = StrokeStyle(color=BLACK, width=2.2)
        if sketch_style is None:
            sketch_style = SketchStyle(roughness=0.8)
        super().__init__(stroke_style=stroke_style, sketch_style=sketch_style, **kwargs)
        self.text = str(text)
        self.position = (float(position[0]), float(position[1]))
        self.padding = float(padding)
        self.font_size = int(font_size)
        self.font_name = font_name
        self.fill_color = fill_color
        self.fill_opacity = float(fill_opacity)

        lines = self.text.splitlines() or [self.text]
        helper = Text(
            text="M",
            position=(0.0, 0.0),
            font_size=self.font_size,
            font_name=self.font_name,
            stroke_style=self.stroke_style,
            sketch_style=SketchStyle(roughness=0.0, disable_font_mixture=True),
        )
        max_line_w = max((helper._measure_text_width(line) for line in lines), default=80.0)
        line_h = self.font_size * 1.25
        self.width = float(width) if width is not None else max(90.0, max_line_w + 2.0 * self.padding)
        self.height = float(height) if height is not None else max(48.0, len(lines) * line_h + 1.8 * self.padding)

        if isinstance(tail_target, Drawable):
            tb = tail_target.get_bbox()
            self.tail_point: tuple[float, float] | None = ((tb.min_x + tb.max_x) / 2.0, (tb.min_y + tb.max_y) / 2.0)
        elif isinstance(tail_target, (tuple, list)) and len(tail_target) == 2:
            self.tail_point = (float(tail_target[0]), float(tail_target[1]))
        else:
            self.tail_point = None

    def draw(self) -> OpsSet:
        opsset = OpsSet(initial_set=[])
        x0, y0 = self.position
        x1 = x0 + self.width
        y1 = y0 + self.height
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0

        # Build outline polygon with optional pointer tail on the nearest edge
        tail_w = min(22.0, self.width * 0.18, self.height * 0.25)
        pts: list[tuple[float, float]]
        if self.tail_point is None:
            pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        else:
            tx, ty = self.tail_point
            dx = tx - cx
            dy = ty - cy
            if abs(dy) >= abs(dx):
                if dy >= 0:
                    # Bottom edge tail
                    bx = float(np.clip(tx, x0 + tail_w * 1.2, x1 - tail_w * 1.2))
                    pts = [
                        (x0, y0),
                        (x1, y0),
                        (x1, y1),
                        (bx + tail_w * 0.6, y1),
                        (tx, ty),
                        (bx - tail_w * 0.6, y1),
                        (x0, y1),
                    ]
                else:
                    # Top edge tail
                    bx = float(np.clip(tx, x0 + tail_w * 1.2, x1 - tail_w * 1.2))
                    pts = [
                        (x0, y0),
                        (bx - tail_w * 0.6, y0),
                        (tx, ty),
                        (bx + tail_w * 0.6, y0),
                        (x1, y0),
                        (x1, y1),
                        (x0, y1),
                    ]
            else:
                if dx >= 0:
                    # Right edge tail
                    by = float(np.clip(ty, y0 + tail_w * 1.2, y1 - tail_w * 1.2))
                    pts = [
                        (x0, y0),
                        (x1, y0),
                        (x1, by - tail_w * 0.6),
                        (tx, ty),
                        (x1, by + tail_w * 0.6),
                        (x1, y1),
                        (x0, y1),
                    ]
                else:
                    # Left edge tail
                    by = float(np.clip(ty, y0 + tail_w * 1.2, y1 - tail_w * 1.2))
                    pts = [
                        (x0, y0),
                        (x1, y0),
                        (x1, y1),
                        (x0, y1),
                        (x0, by + tail_w * 0.6),
                        (tx, ty),
                        (x0, by - tail_w * 0.6),
                    ]

        bubble_poly = Polygon(
            points=pts,
            stroke_style=self.stroke_style,
            fill_style=FillStyle(color=self.fill_color, opacity=self.fill_opacity, fill_pattern="solid"),
            sketch_style=self.sketch_style,
        )
        opsset.extend(bubble_poly.draw())

        lines = self.text.splitlines() or [self.text]
        line_h = self.font_size * 1.25
        start_y = cy - (len(lines) - 1) * line_h * 0.5 + self.font_size * 0.32
        for idx, line in enumerate(lines):
            txt = Text(
                text=line,
                position=(cx, start_y + idx * line_h),
                font_size=self.font_size,
                font_name=self.font_name,
                align="center",
                stroke_style=StrokeStyle(color=self.stroke_style.color, width=max(1.8, self.stroke_style.width * 0.85)),
                sketch_style=SketchStyle(roughness=0.25, disable_font_mixture=True),
            )
            opsset.extend(txt.draw())

        return opsset


class CrossOut(Drawable):
    """A bold hand-sketched red 'X' or strike-through over a target drawable to debunk a misconception."""

    is_emphasis_overlay: bool = True

    def __init__(
        self,
        target: Drawable | BoundingBox | tuple[Any, ...],
        style: str = "x",  # "x" | "strike"
        color: tuple[float, float, float] = RED,
        width: float = 4.2,
        padding: float = 6.0,
        stroke_style: StrokeStyle | None = None,
        sketch_style: SketchStyle | None = None,
        **kwargs,
    ) -> None:
        if stroke_style is None:
            stroke_style = StrokeStyle(color=color, width=width)
        if sketch_style is None:
            sketch_style = SketchStyle(roughness=1.2)
        super().__init__(stroke_style=stroke_style, sketch_style=sketch_style, **kwargs)
        self.target_bbox = _resolve_bbox(target)
        self.style = style.lower()
        self.padding = float(padding)

    def draw(self) -> OpsSet:
        opsset = OpsSet(initial_set=[])
        b = self.target_bbox
        x0 = b.min_x - self.padding
        x1 = b.max_x + self.padding
        y0 = b.min_y - self.padding
        y1 = b.max_y + self.padding

        if self.style == "strike":
            cy = (y0 + y1) / 2.0
            opsset.extend(
                Line(start=(x0, cy + 2.0), end=(x1, cy - 2.0), stroke_style=self.stroke_style, sketch_style=self.sketch_style).draw()
            )
            opsset.extend(
                Line(start=(x0, cy + 6.0), end=(x1, cy + 2.0), stroke_style=self.stroke_style, sketch_style=self.sketch_style).draw()
            )
        else:
            opsset.extend(
                Line(start=(x0, y0), end=(x1, y1), stroke_style=self.stroke_style, sketch_style=self.sketch_style).draw()
            )
            opsset.extend(
                Line(start=(x0, y1), end=(x1, y0), stroke_style=self.stroke_style, sketch_style=self.sketch_style).draw()
            )
        return opsset
