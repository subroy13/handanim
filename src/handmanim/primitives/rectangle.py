import cairo
import random
import math

class Rectangle:
    def __init__(self, x, y, width, height, stroke_color=(0, 0, 0),
                 fill_color=None, roughness=1.0, bowing=0.0, stroke_width=2.0):
        self.x, self.y = x, y
        self.width, self.height = width, height
        self.stroke_color = stroke_color
        self.fill_color = fill_color
        self.roughness = roughness
        self.bowing = bowing
        self.stroke_width = stroke_width

    def _draw_rough_line(self, ctx, x1, y1, x2, y2):
        # Introduce curvature using bowing
        mid_x = (x1 + x2) / 2 + random.uniform(-self.bowing, self.bowing)
        mid_y = (y1 + y2) / 2 + random.uniform(-self.bowing, self.bowing)

        # Slightly jitter start and end
        x1 += random.uniform(-self.roughness, self.roughness)
        y1 += random.uniform(-self.roughness, self.roughness)
        x2 += random.uniform(-self.roughness, self.roughness)
        y2 += random.uniform(-self.roughness, self.roughness)

        ctx.move_to(x1, y1)
        ctx.curve_to(mid_x, mid_y, mid_x, mid_y, x2, y2)
        ctx.stroke()

    def _fill_hachure(self, ctx):
        if self.fill_color is None:
            return

        spacing = 6  # Distance between hatch lines
        angle = math.radians(-45)
        sin_a = math.sin(angle)
        cos_a = math.cos(angle)

        # Compute bounding box
        x0, y0 = self.x, self.y
        x1, y1 = x0 + self.width, y0 + self.height

        ctx.set_source_rgb(*self.fill_color)
        ctx.set_line_width(1)

        # Draw hatching lines
        for i in range(-int(self.height), int(self.width * 2), spacing):
            x_start = x0 + i * cos_a
            y_start = y0 + i * sin_a
            x_end = x_start + self.height / sin_a
            y_end = y_start - self.height / cos_a

            ctx.move_to(x_start, y_start)
            ctx.line_to(x_end, y_end)
            ctx.stroke()

    def draw(self, ctx: cairo.Context):
        ctx.save()
        ctx.set_line_width(self.stroke_width)
        ctx.set_source_rgb(*self.stroke_color)

        if self.fill_color:
            self._fill_hachure(ctx)

        # Get rectangle points
        points = [
            (self.x, self.y),
            (self.x + self.width, self.y),
            (self.x + self.width, self.y + self.height),
            (self.x, self.y + self.height)
        ]

        for i in range(4):
            p1 = points[i]
            p2 = points[(i + 1) % 4]
            self._draw_rough_line(ctx, *p1, *p2)

        ctx.restore()
