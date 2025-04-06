import numpy as np
import cairo

class Circle:
    def __init__(self, center=(0, 0), radius=1.0, stroke_width=2.0, color=(0, 0, 0), jitter=0.015):
        self.center = center
        self.radius = radius
        self.stroke_width = stroke_width
        self.color = color  # RGB tuple
        self.jitter = jitter  # How much randomness to add to the outline

    def _jitter_point(self, angle):
        r = self.radius + np.random.uniform(-self.jitter, self.jitter)
        x = self.center[0] + r * np.cos(angle)
        y = self.center[1] + r * np.sin(angle)
        return x, y

    def draw(self, ctx: cairo.Context):
        ctx.save()
        ctx.set_line_width(self.stroke_width)
        ctx.set_source_rgb(*self.color)

        angles = np.linspace(0, 2 * np.pi, 100)
        points = [self._jitter_point(a) for a in angles]

        ctx.move_to(*points[0])
        for pt in points[1:]:
            ctx.line_to(*pt)
        ctx.close_path()
        ctx.stroke()
        ctx.restore()
