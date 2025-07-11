from typing import List, Tuple
import numpy as np

from ..primitives.lines import Line
from .utils import polygon_hachure_lines
from ..core.styles import FillStyle, SketchStyle, StrokeStyle
from ..core.drawable import DrawableFill
from ..core.draw_ops import OpsSet, Ops, OpsType


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
            opsset.add(Ops(OpsType.CLOSE_PATH))
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

    def render_fill_lines(self, lines: List[List[Tuple[float, float]]]) -> OpsSet:
        line_stroke_style = StrokeStyle(
            color=self.fill_style.color,
            line_width=self.fill_style.hachure_line_width,
            opacity=self.fill_style.opacity,
        )
        opsset = OpsSet(initial_set=[])
        for line in lines:
            line = Line(
                line[0],
                line[1],
                stroke_style=line_stroke_style,
                sketch_style=self.sketch_style,
            )
            opsset.extend(line.draw())
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


# class ZigZagFillPattern(DrawableFill):

#     def fill_polygons(self, ctx):
#         gap = max(self.fill_style.hachure_gap, 0.1)

#         fill_style_new = self.fill_style
#         fill_style_new.hachure_gap = gap  # update the hachure gap
#         lines = polygon_hachure_lines(
#             self.bound_box_list, fill_style_new, self.sketch_style
#         )
#         zigzag_angle = np.pi * self.fill_style.hachure_angle / 180
#         zigzag_lines = []
#         dg = 0.5 * gap * np.array([np.cos(zigzag_angle), np.sin(zigzag_angle)])
#         for line in lines:
#             start, end = line  # get the start and end point of the line
#             zigzag_lines.extend(
#                 [
#                     [start + dg, end],
#                     [start - dg, end],
#                 ]
#             )
#         self.render_fill_lines(ctx, zigzag_lines)


# class ZigZagLineFillPattern(DrawableFill):
#     # TODO: Check and fix this

#     def zigzag_lines(
#         self,
#         lines: List[List[Tuple[float, float]]],  # list of lines
#         zo: float,  # zigzag offset factor
#     ):
#         zigzag_lines = []
#         for line in lines:
#             start, end = line  # get the start and end point of the line
#             length = np.linalg.norm(np.array(end) - np.array(start))
#             count = int(np.round(length / (2 * zo)))
#             if start[0] > end[0]:
#                 start, end = end, start
#             alpha = np.atan(
#                 (end[1] - start[1]) / (end[0] - start[0])
#             )  # figure out the slope
#             trig = np.array([np.cos(alpha), np.sin(alpha)])
#             trig_mid = np.array([np.cos(alpha + np.pi / 4), np.sin(alpha + np.pi / 4)])
#             for i in range(count):
#                 lstart = i * 2 * zo
#                 lend = (i + 1) * 2 * zo
#                 dz = np.sqrt(2 * zo**2)
#                 s2 = np.array(start) + lstart * trig
#                 e2 = np.array(end) + lend * trig
#                 mid = np.array(start) + dz * trig_mid
#                 zigzag_lines.append([s2, mid])
#                 zigzag_lines.append([mid, e2])
#         return zigzag_lines

#     def render_fill_lines(
#         self, ctx: cairo.Context, lines: List[List[Tuple[float, float]]]
#     ):
#         line_stroke_style = StrokeStyle(
#             color=self.fill_style.color,
#             line_width=self.fill_style.hachure_line_width,
#             opacity=self.fill_style.opacity,
#         )
#         for line in lines:
#             line = Line(
#                 line[0],
#                 line[1],
#                 stroke_style=line_stroke_style,
#                 sketch_style=self.sketch_style,
#             )
#             line.draw(ctx)

#     def fill(self, ctx):
#         gap = max(self.fill_style.hachure_gap, 0.1)
#         zo = gap if self.fill_style.zigzag_offset < 0 else self.fill_style.zigzag_offset
#         fill_style_new = self.fill_style
#         fill_style_new.hachure_gap = gap + zo  # update the hachure gap
#         lines = polygon_hachure_lines(
#             self.bound_box_list, fill_style_new, self.sketch_style
#         )
#         zigzag_lines = self.zigzag_lines(
#             lines, zo
#         )  # calculate the zigzag lines from the hachure lines
#         self.render_fill_lines(ctx, zigzag_lines)


def get_filler(
    bound_box_list: List[List[Tuple[float, float]]],
    fill_style: FillStyle = FillStyle(),
    sketch_style=SketchStyle(),
) -> DrawableFill:
    cls_name = None
    if fill_style.fill_pattern == "hachure":
        cls_name = HachureFillPattern
    elif fill_style.fill_pattern == "hatch":
        cls_name = HatchFillPattern
    elif fill_style.fill_pattern == "solid":
        cls_name = SolidFillPattern
    else:
        raise ValueError(f"fill pattern {fill_style.fill_pattern} not supported")
    return cls_name(bound_box_list, fill_style, sketch_style)
