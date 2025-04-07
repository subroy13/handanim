import numpy as np
from .base import BasePrimitive
from ..transformed_context import TransformedContext

class Line(BasePrimitive):

    def __init__(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        stroke_color: tuple[float, float, float] = (0, 0, 0),
        stroke_width: float = 1,
        roughness: float = 1.0,  # how much the endpoints are jittered
        pastel: bool = False,  # whether to use pastel colors
        sketch_number: int = 2,  # number of sketch lines
    ):
        self.x1, self.y1 = start
        self.x2, self.y2 = end
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.roughness = roughness
        self.pastel = pastel
        self.sketch_number = sketch_number

    def draw(self, ctx: TransformedContext):
        """
        Draws a hand-drawn-like line with some jitter.
        """
        ctx.save()  # save the current state of the context

        # Set stroke color and width
        r, g, b = self.stroke_color
        ctx.set_source_rgba(r, g, b, 0.3 if self.pastel else 1.0)
        ctx.set_line_width(self.stroke_width)

        # Draw sketchy lines
        for _ in range(self.sketch_number):
            jitter = lambda: np.random.uniform(-self.roughness, self.roughness)
            ctx.move_to(self.x1 + jitter(), self.y1 + jitter())
            ctx.line_to(self.x2 + jitter(), self.y2 + jitter())
            ctx.stroke()

        ctx.restore()  # restore the context to the previous state (to back to original color scheme)
        