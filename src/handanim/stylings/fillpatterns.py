import copy

import numpy as np

from ..core.draw_ops import Ops, OpsSet, OpsType
from ..core.drawable import DrawableFill
from ..core.styles import FillStyle, SketchStyle, StrokeStyle
from ..primitives.lines import Line
from .utils import polygon_hachure_lines


class SolidFillPattern(DrawableFill):
    """
    A fill pattern implementation for solid color fills.

    This class extends DrawableFill and provides a method to create a solid color fill
    for a given set of bounding boxes. It sets the pen color, opacity, and fills the
    specified geometric shapes by drawing lines connecting the box vertices.

    Attributes:
        bound_box_list (list): A list of bounding boxes to be filled
        fill_style (FillStyle): Style parameters for the fill
        sketch_style (SketchStyle, optional): Sketch style parameters

    Returns:
        OpsSet: A set of drawing operations to render the solid fill
    """

    def __init__(self, bound_box_list, fill_style=..., sketch_style=...):
        super().__init__(bound_box_list, fill_style, sketch_style)

    def fill(self) -> OpsSet:
        opsset = OpsSet(
            [
                Ops(
                    OpsType.SET_PEN,
                    data={
                        "color": self.fill_style.color,
                        "opacity": self.fill_style.opacity,
                        "mode": "fill",
                    },
                )
            ]
        )
        for box in self.bound_box_list:
            opsset.add(Ops(OpsType.MOVE_TO, data=[box[0]]))
            for i in range(1, len(box)):
                opsset.add(Ops(OpsType.LINE_TO, data=[box[i]]))
            opsset.add(Ops(OpsType.CLOSE_PATH, data={}))
        return opsset


class HachureFillPattern(DrawableFill):
    """
    A base class for hachure fill patterns that renders fill lines for polygons.

    This class provides methods to render hachure lines with a specific stroke style
    and sketch style. The render_fill_lines method converts a list of line points
    into drawable Line objects with the specified styling.

    Attributes:
        fill_style (FillStyle): Style parameters for the fill
        sketch_style (SketchStyle, optional): Sketch style parameters for line rendering

    Methods:
        render_fill_lines: Converts line points to drawable Line objects
        fill: Generates hachure lines for a set of polygons and renders them
    """

    def render_fill_lines(self, lines: list[list[tuple[float, float]]]) -> OpsSet:
        line_stroke_style = StrokeStyle(
            color=self.fill_style.color,
            line_width=self.fill_style.hachure_line_width,
            opacity=self.fill_style.opacity,
        )
        opsset = OpsSet(initial_set=[])
        for line_pts in lines:
            line_drawable = Line(
                line_pts[0],
                line_pts[1],
                stroke_style=line_stroke_style,
                sketch_style=self.sketch_style,
            )
            opsset.extend(line_drawable.draw())
        return opsset

    def fill(self):
        opsset = OpsSet(
            [
                Ops(
                    OpsType.SET_PEN,
                    data={
                        "color": self.fill_style.color,
                        "opacity": self.fill_style.opacity,
                        "width": self.fill_style.hachure_line_width,
                        "mode": "stroke",
                    },
                )
            ]
        )

        # get the polygon hachure lines
        linepoints = polygon_hachure_lines(
            self.bound_box_list, self.fill_style, self.sketch_style
        )
        opsset.extend(self.render_fill_lines(linepoints))
        return opsset


class HatchFillPattern(HachureFillPattern):
    """
    Generates a hatch fill pattern by rendering hachure lines at two perpendicular angles.

    Creates an OpsSet with two sets of hachure lines rotated 90 degrees from each other,
    creating a criss-cross fill pattern. Preserves the original fill style after rendering.

    Returns:
        OpsSet: A set of drawing operations representing the hatch fill pattern.
    """

    def fill(self):
        opsset = OpsSet(
            [
                Ops(
                    OpsType.SET_PEN,
                    data={
                        "color": self.fill_style.color,
                        "opacity": self.fill_style.opacity,
                        "width": self.fill_style.hachure_line_width,
                        "mode": "stroke",
                    },
                )
            ]
        )

        # get the polygon hachure lines
        linepoints = polygon_hachure_lines(
            self.bound_box_list, self.fill_style, self.sketch_style
        )
        opsset.extend(self.render_fill_lines(linepoints))
        current_fill_style = self.fill_style
        self.fill_style.hachure_angle += 90  # rotate the hachure angle
        opsset.extend(
            self.render_fill_lines(linepoints)
        )  # fill in a criss-cross pattern
        self.fill_style = current_fill_style  # reset the fill style
        return opsset


class ZigZagLineFillPattern(HachureFillPattern):
    """
    Fills polygons with a zigzag line pattern — like back-and-forth colored pencil shading.

    Takes the same hachure lines as HachureFillPattern, then subdivides each line into
    segments and offsets midpoints perpendicular to the line direction, alternating sides.
    The zigzag_offset field in FillStyle controls the amplitude; when negative, defaults
    to the hachure gap.
    """

    def _to_zigzag(self, lines: list[list[tuple[float, float]]], zo: float) -> list[list[tuple[float, float]]]:
        zigzag_lines = []
        for line_pts in lines:
            start = np.array(line_pts[0])
            end = np.array(line_pts[1])
            diff = end - start
            length = np.linalg.norm(diff)
            if length < 1e-6:
                continue
            d = diff / length
            n = np.array([-d[1], d[0]])
            count = max(int(np.round(length / (2 * zo))), 1)
            seg_len = length / count
            for i in range(count):
                s = start + i * seg_len * d
                e = start + (i + 1) * seg_len * d
                mid = (s + e) / 2 + ((-1) ** i) * zo * n
                zigzag_lines.append([s.tolist(), mid.tolist()])
                zigzag_lines.append([mid.tolist(), e.tolist()])
        return zigzag_lines

    def fill(self):
        opsset = OpsSet([Ops(OpsType.SET_PEN, data={"color": self.fill_style.color, "opacity": self.fill_style.opacity, "width": self.fill_style.hachure_line_width, "mode": "stroke"})])
        gap = max(self.fill_style.hachure_gap, 0.1)
        zo = gap if self.fill_style.zigzag_offset < 0 else self.fill_style.zigzag_offset
        fill_style_wider = copy.copy(self.fill_style)
        fill_style_wider.hachure_gap = gap + zo
        linepoints = polygon_hachure_lines(self.bound_box_list, fill_style_wider, self.sketch_style)
        zigzag_pts = self._to_zigzag(linepoints, zo)
        opsset.extend(self.render_fill_lines(zigzag_pts))
        return opsset


def get_filler(
    bound_box_list: list[list[tuple[float, float]]],
    fill_style: FillStyle = FillStyle(),
    sketch_style=SketchStyle(),
) -> DrawableFill:
    cls_name = None
    if fill_style.fill_pattern == "hachure":
        cls_name = HachureFillPattern
    elif fill_style.fill_pattern == "hatch":
        cls_name = HatchFillPattern
    elif fill_style.fill_pattern == "zigzag":
        cls_name = ZigZagLineFillPattern
    elif fill_style.fill_pattern == "solid":
        cls_name = SolidFillPattern  # type: ignore[assignment]
    else:
        raise ValueError(f"fill pattern {fill_style.fill_pattern} not supported")
    return cls_name(bound_box_list, fill_style, sketch_style)
