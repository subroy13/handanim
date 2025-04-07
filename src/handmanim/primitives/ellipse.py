import numpy as np
from .base import BasePrimitive
from ..transformed_context import TransformedContext
from ..stylings.fill_patterns import HachureFillPatterns, apply_hachure_fill_patterns

class Ellipse(BasePrimitive):
    """
        A class to represent an ellipse in a hand-drawn style.
    """
    def __init__(
        self,
        center: tuple[float, float],
        width: float,
        height: float,
        stroke_color: tuple[float, float, float] = (0, 0, 0),
        stroke_width: float = 1,
        roughness: float = 1.0,
        pastel: bool = False,  # whether to use pastel colors
        sketch_number: int = 2,  # number of sketch lines
        fill_color: tuple[float, float, float] = None,  # fill color
        fill_type: HachureFillPatterns = HachureFillPatterns.DIAGONAL,  # fill type
        fill_spacing: float = 10,  # spacing between fill lines
    ):
        self.x, self.y = center
        self.width = width
        self.height = height
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.roughness = roughness
        self.pastel = pastel
        self.sketch_number = sketch_number
        self.fill_color = fill_color
        self.fill_type = fill_type
        self.fill_spacing = fill_spacing

    def _get_ellipse_points(self, num_points: int = 100):
        """
            Draw an ellipse using the parametric equation.
            x = a * cos(t)
            y = b * sin(t)
        """
        t = np.linspace(0, 2 * np.pi, num_points)
        jitters = np.random.uniform(-self.roughness, self.roughness, size=(num_points, 2))
        x = self.x + self.width / 2 * np.cos(t) + jitters[:, 0]
        y = self.y + self.height / 2 * np.sin(t) + jitters[:, 1]
        return x, y
    
    def _fill_hachure(self, ctx: TransformedContext):
        """
            Fills the ellipse with a filling pattern
        """
        if self.fill_color is None:
            return

        # clip to ellipse
        ctx.save()
        ctx.ellipse(self.x, self.y, self.width, self.height)
        ctx.clip()

        # apply the fill pattern
        apply_hachure_fill_patterns(
            ctx,
            (self.x, self.y, self.width, self.height),
            self.fill_type,
            self.fill_spacing,
            self.fill_color,
        )
        ctx.restore()  # restore context

    def draw(self, ctx: TransformedContext):
        """
            Draws the ellipse with a hand-drawn-like style.
        """
        ctx.save()  # saves the current state

        # Draw the fill pattern
        self._fill_hachure(ctx)

        # draw the edges in sketchy style
        ctx.set_source_rgb(*self.stroke_color)
        ctx.set_line_width(self.stroke_width)

        # Draw the ellipse outline
        for _ in range(self.sketch_number):
            x, y = self._get_ellipse_points()
            for i in range(len(x) - 1):
                xm = (x[i] + x[i + 1]) / 2
                ym = (y[i] + y[i + 1]) / 2
                ctx.move_to(x[i], y[i])
                ctx.line_to(x[i + 1], y[i + 1])
                ctx.stroke()

        ctx.restore()  # restore the context to the previous state (to back to original color scheme)
            
class Circle(Ellipse):
    """
        A class to represent a circle in a hand-drawn style.
    """
    def __init__(
        self,
        center: tuple[float, float],
        radius: float,
        **kwargs,
    ):
        super().__init__(
            center=center,
            width=radius * 2,
            height=radius * 2,
            **kwargs,
        )
        self.radius = radius
