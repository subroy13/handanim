import math
import random
import cairo

class Rectangle:
    def __init__(self, x, y, width, height, stroke_color=(0, 0, 0), stroke_width=2,
                 fill_color=None, roughness=1.0, pastel=False):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.fill_color = fill_color
        self.roughness = roughness
        self.pastel = pastel

    def _draw_sketchy_line(self, ctx, x1, y1, x2, y2):
        """Draws a hand-drawn-like line with some jitter."""
        for _ in range(2):
            jitter = lambda: random.uniform(-self.roughness, self.roughness)
            ctx.move_to(x1 + jitter(), y1 + jitter())
            ctx.line_to(x2 + jitter(), y2 + jitter())
            ctx.stroke()

    def _fill_hachure(self, ctx):
        if self.fill_color is None:
            return

        spacing = 10  # Distance between hatch lines
        angle = math.radians(45)
        sin_a = math.sin(angle)
        cos_a = math.cos(angle)
        tan_a = math.tan(angle)

        x0, y0 = self.x, self.y
        x1, y1 = x0 + self.width, y0 + self.height

        # Clip to rectangle
        ctx.save()
        ctx.rectangle(x0, y0, self.width, self.height)
        ctx.clip()

        # Pastel fill effect
        r, g, b = self.fill_color
        ctx.set_source_rgba(r, g, b, 0.3 if self.pastel else 1.0)
        ctx.set_line_width(1 if not self.pastel else 2)

        # Diagonal lines spaced evenly
        for i in range(y0, y0 + self.width + 2 * int(self.height / tan_a), spacing):
            x_start = x0
            y_start = i
            x_end = x_start + self.width
            y_end = y_start - self.width / cos_a

            for _ in range(2 if self.pastel else 1):
                jitter = lambda: random.uniform(-0.5, 0.5) if self.pastel else 0
                ctx.move_to(x_start + jitter(), y_start + jitter())
                ctx.line_to(x_end + jitter(), y_end + jitter())
                ctx.stroke()

        # Restore context
        ctx.restore()

    def draw(self, ctx: cairo.Context):
        self._fill_hachure(ctx)

        # Stroke rectangle edges in sketchy style
        ctx.set_source_rgb(*self.stroke_color)
        ctx.set_line_width(self.stroke_width)

        x0, y0 = self.x, self.y
        x1, y1 = x0 + self.width, y0 + self.height

        self._draw_sketchy_line(ctx, x0, y0, x1, y0)
        self._draw_sketchy_line(ctx, x1, y0, x1, y1)
        self._draw_sketchy_line(ctx, x1, y1, x0, y1)
        self._draw_sketchy_line(ctx, x0, y1, x0, y0)
