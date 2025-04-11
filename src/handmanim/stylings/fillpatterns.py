from typing import List, Tuple
from abc import ABC, abstractmethod
import cairo
import numpy as np

from ..primitives.lines import Line
from .utils import polygon_hachure_lines
from .styles import FillStyle, SketchStyle, StrokeStyle


class BaseFillPattern(ABC):

    @abstractmethod
    def fill(self, ctx: cairo.Context):
        pass


class HachureFillPattern(BaseFillPattern):

    def __init__(
        self,
        bound_box_list: List[
            List[Tuple[float, float]]
        ],  # defines the bounding box for filling
        fill_style: FillStyle = FillStyle(),
        sketch_style: SketchStyle = SketchStyle(),
    ):
        self.bound_box_list = bound_box_list
        self.fill_style = fill_style
        self.sketch_style = sketch_style

    def render_fill_lines(
        self, ctx: cairo.Context, lines: List[List[Tuple[float, float]]]
    ):
        line_stroke_style = StrokeStyle(
            color=self.fill_style.color,
            line_width=self.fill_style.hachure_line_width,
            opacity=self.fill_style.opacity,
        )
        for line in lines:
            line = Line(
                line[0],
                line[1],
                stroke_style=line_stroke_style,
                sketch_style=self.sketch_style,
            )
            line.draw(ctx)

    def fill_polygons(self, ctx: cairo.Context):
        # get the polygon hachure lines
        linepoints = polygon_hachure_lines(
            self.bound_box_list, self.fill_style, self.sketch_style
        )
        self.render_fill_lines(ctx, linepoints)

    def fill(self, ctx: cairo.Context):
        # save the context
        ctx.save()

        # set the fill style
        r, g, b = self.fill_style.color
        ctx.set_source_rgba(r, g, b, self.fill_style.opacity)
        ctx.set_line_width(self.fill_style.hachure_line_width)

        # fill the polygons from the bounding boxes
        self.fill_polygons(ctx)

        # reset
        ctx.restore()


class HatchFillPattern(HachureFillPattern):

    def fill_polygons(self, ctx):
        # draw the normal hachure lines
        super().fill_polygons(ctx)
        current_fill_style = self.fill_style
        self.fill_style.hachure_angle += 90  # rotate the hachure angle
        super().fill_polygons(ctx)  # fill polygons in a criss-cross pattern
        self.fill_style = current_fill_style  # reset the fill style


class ZigZagFillPattern(HachureFillPattern):

    def fill_polygons(self, ctx):
        gap = max(self.fill_style.hachure_gap, 0.1)

        fill_style_new = self.fill_style
        fill_style_new.hachure_gap = gap  # update the hachure gap
        lines = polygon_hachure_lines(
            self.bound_box_list, fill_style_new, self.sketch_style
        )
        zigzag_angle = np.pi * self.fill_style.hachure_angle / 180
        zigzag_lines = []
        dg = 0.5 * gap * np.array([np.cos(zigzag_angle), np.sin(zigzag_angle)])
        for line in lines:
            start, end = line  # get the start and end point of the line
            zigzag_lines.extend(
                [
                    [start + dg, end],
                    [start - dg, end],
                ]
            )
        self.render_fill_lines(ctx, zigzag_lines)


class ZigZagLineFillPattern(BaseFillPattern):
    def __init__(
        self,
        bound_box_list: List[
            List[Tuple[float, float]]
        ],  # defines the bounding box for filling
        fill_style: FillStyle = FillStyle(),
        sketch_style: SketchStyle = SketchStyle(),
    ):
        self.bound_box_list = bound_box_list
        self.fill_style = fill_style
        self.sketch_style = sketch_style

    def zigzag_lines(
        self,
        lines: List[List[Tuple[float, float]]],  # list of lines
        zo: float,  # zigzag offset factor
    ):
        zigzag_lines = []
        for line in lines:
            start, end = line  # get the start and end point of the line
            length = np.linalg.norm(np.array(end) - np.array(start))
            count = np.round(length / (2 * zo))
            if start[0] > end[0]:
                start, end = end, start
            alpha = np.atan(
                (end[1] - start[1]) / (end[0] - start[0])
            )  # figure out the slope
            trig = np.array([np.cos(alpha), np.sin(alpha)])
            trig_mid = np.array([np.cos(alpha + np.pi / 4), np.sin(alpha + np.pi / 4)])
            for i in range(count):
                lstart = i * 2 * zo
                lend = (i + 1) * 2 * zo
                dz = np.sqrt(2 * zo**2)
                s2 = np.array(start) + lstart * trig
                e2 = np.array(end) + lend * trig
                mid = np.array(start) + dz * trig_mid
                zigzag_lines.append([s2, mid])
                zigzag_lines.append([mid, e2])

    def render_fill_lines(
        self, ctx: cairo.Context, lines: List[List[Tuple[float, float]]]
    ):
        line_stroke_style = StrokeStyle(
            color=self.fill_style.color,
            line_width=self.fill_style.hachure_line_width,
            opacity=self.fill_style.opacity,
        )
        for line in lines:
            line = Line(
                line[0],
                line[1],
                stroke_style=line_stroke_style,
                sketch_style=self.sketch_style,
            )
            line.draw(ctx)

    def fill_polygons(self, ctx):
        gap = max(self.fill_style.hachure_gap, 0.1)
        zo = gap if self.fill_style.zigzag_offset < 0 else self.fill_style.zigzag_offset
        fill_style_new = self.fill_style
        fill_style_new.hachure_gap = gap + zo  # update the hachure gap
        lines = polygon_hachure_lines(
            self.bound_box_list, fill_style_new, self.sketch_style
        )
        zigzag_lines = self.zigzag_lines(
            lines, zo
        )  # calculate the zigzag lines from the hachure lines
        self.render_fill_lines(ctx, zigzag_lines)


class DottedFillPattern(BaseFillPattern):
    def __init__(
        self,
        bound_box_list: List[
            List[Tuple[float, float]]
        ],  # defines the bounding box for filling
        fill_style: FillStyle = FillStyle(),
        sketch_style: SketchStyle = SketchStyle(),
    ):
        self.bound_box_list = bound_box_list
        self.fill_style = fill_style
        self.sketch_style = sketch_style

    def get_dots_on_lines(
        self,
        lines: List[List[Tuple[float, float]]],
    ):
        gap = max(self.fill_style.hachure_gap, 0.1)
        fweight = self.fill_style.fill_weight
        ro = gap / 4
        for line in lines:
            start, end = line  # get the start and end point of the line
            length = np.linalg.norm(np.array(end) - np.array(start))
            count = np.ceil(length / gap) - 1
            offset = length - (count * gap)
            x = (line[0][0] + line[1][0]) / 2 - (gap / 4)
            minY = min(line[0][1], line[1][1])

            for i in range(count):
                y = minY + offset + (i * gap)
                cx = (x - ro) + np.random.uniform() * 2 * ro
                cy = (y - ro) + np.random.uniform() * 2 * ro

                # TODO: implement the point ellipses
                pass
