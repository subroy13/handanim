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

    def _fill_hachure(self, ctx: TransformedContext):
        """
        Fills the ellipse with a filling pattern
        """
        if self.fill_color is None:
            return

        # clip to ellipse
        ctx.save()

        # draw the curves
        (
            ctx_top_left,
            top,
            ctx_top_right,
            ctx_bottom_right,
            bottom,
            ctx_bottom_left,
        ) = self._get_ellipse_bezier_points(exact=True)
        ctx.move_to(*top)
        ctx.curve_to(*ctx_top_right, *ctx_bottom_right, *bottom)
        ctx.curve_to(*ctx_bottom_left, *ctx_top_left, *top)
        ctx.clip()

        # apply the fill pattern
        apply_hachure_fill_patterns(
            ctx,
            (
                self.x - self.width / 2,
                self.y - self.height / 2,
                self.width,
                self.height,
            ),
            self.fill_type,
            self.fill_spacing,
            self.fill_color,
        )
        ctx.restore()  # restore context

    def _get_ellipse_bezier_points(self, exact=False):
        """
        Draws an approximate ellipse using bezier curves
        """
        # calculate the top and bottom end points
        if exact:
            jitters = (0, 0, 0)
        else:
            jitters = np.random.uniform(-self.roughness, self.roughness, size=(3,))

        top = (self.x + jitters[0], self.y + self.height / 2 + jitters[1])
        bottom = (self.x + jitters[0], self.y - self.height / 2 + jitters[2])

        # determine the control points
        SCALE_FACTOR = 4 / 3
        ctx_top_left = (self.x - self.width / 2 * SCALE_FACTOR, top[1])
        ctx_top_right = (self.x + self.width / 2 * SCALE_FACTOR, top[1])
        ctx_bottom_left = (self.x - self.width / 2 * SCALE_FACTOR, bottom[1])
        ctx_bottom_right = (self.x + self.width / 2 * SCALE_FACTOR, bottom[1])

        # return the points
        return [
            ctx_top_left,
            top,
            ctx_top_right,
            ctx_bottom_right,
            bottom,
            ctx_bottom_left,
        ]

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
            (
                ctx_top_left,
                top,
                ctx_top_right,
                ctx_bottom_right,
                bottom,
                ctx_bottom_left,
            ) = self._get_ellipse_bezier_points()
            ctx.move_to(*top)
            ctx.curve_to(*ctx_top_right, *ctx_bottom_right, *bottom)
            ctx.stroke()  # create the curve stroke

            ctx.move_to(*bottom)
            ctx.curve_to(*ctx_bottom_left, *ctx_top_left, *top)
            ctx.stroke()  # create the curve stroke

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
