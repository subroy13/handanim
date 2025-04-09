import numpy as np
import cairo
from .base import BasePrimitive
from ..constants import RoughOptions


class Line(BasePrimitive):
    def __init__(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        stroke_color: tuple[float, float, float] = (0, 0, 0),
        stroke_width: float = 1,
        stroke_opacity: float = 1,
        options: RoughOptions = RoughOptions(),
    ):
        self.start = np.array(start)
        self.end = np.array(end)
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.stroke_opacity = stroke_opacity
        self.options = options

    def draw_single_line(
        self,
        ctx: cairo.Context,  # the context to use to draw
        move: bool = False,  # should we move to the specific position before drawing?
        overlay: bool = False,  # is this the second pass?
    ):
        length = np.linalg.norm(
            self.end - self.start
        )  # get the length of the line segment
        roughness_gain = np.clip(
            -0.0016668 * length + 1.233334, 0.4, 1
        )  # calculate roughness gain (dampending factor)
        offset = min(length / 10, self.options.max_random_offset)

        # get the divergence point for bowing effect
        diverge_point = np.random.uniform(low=0.2, high=0.4)
        mid_disp = self.options.bowing * offset * (self.end - self.start) / 200
        mid_disp = np.array([mid_disp[1], mid_disp[0]])  # this is normal to the line

        # random generator functions
        random_jitter = (
            lambda x: np.random.uniform(low=-offset, high=offset, size=(x,))
            * roughness_gain
            * self.options.roughness
        )
        jitter_scale = 0.5 if overlay else 1

        # draw the curved lines, based on move and overlay
        if move:
            ctx.move_to(*(self.start + random_jitter(2) * jitter_scale))

        ctx.curve_to(
            *(
                mid_disp
                + self.start
                + (self.end - self.start) * diverge_point
                + random_jitter(2) * jitter_scale
            ),
            *(
                mid_disp
                + self.start
                + 2 * (self.end - self.start) * diverge_point
                + random_jitter(2) * jitter_scale
            ),  # curve controls are placed close to the start points
            *(self.end + random_jitter(2) * jitter_scale),
        )
        ctx.stroke()

    def draw(self, ctx: cairo.Context):
        """
        Draws a hand-drawn-like line with some jitter.
        """
        ctx.save()  # save the current state of the context

        # Set stroke color and width
        r, g, b = self.stroke_color
        ctx.set_source_rgba(r, g, b, self.stroke_opacity)
        ctx.set_line_width(self.stroke_width)

        # draw the sketchy lines
        self.draw_single_line(ctx, move=True, overlay=False)
        self.draw_single_line(ctx, move=True, overlay=True)

        ctx.restore()  # restore the context to its previous state
