import cairo
import numpy as np


class TransformedContext:
    """
    This class helps to transform the context of a Cairo
    drawing coordinates into mathematical type coordinates
    """

    def __init__(self, ctx: cairo.Context, width: int, height: int):
        self._ctx = ctx
        self._width = width
        self._height = height

    def _transform(self, x: float, y: float) -> tuple:
        """
        Transform the coordinates from Cairo to mathematical type coordinates
        (0, 0) is the bottom left corner of the screen
        (width, height) is the top right corner of the screen
        """
        return x, self._height - y  # only the y-axis flips

    def get_current_point(self) -> tuple:
        """
        Get the current point of the context
        """
        x, y = self._ctx.get_current_point()
        return self._transform(x, y)

    def move_to(self, x: float, y: float):
        """
        Move the context to the given coordinates
        """
        x, y = self._transform(x, y)
        self._ctx.move_to(x, y)

    def line_to(self, x: float, y: float):
        """
        Draw a line to the given coordinates from current pencil coordinates
        """
        x, y = self._transform(x, y)
        self._ctx.line_to(x, y)

    def curve_to(
        self, x1: float, y1: float, x2: float, y2: float, x3: float, y3: float
    ):
        """
        Draw a curve to the given coordinates from current pencil coordinates
        (x1, y1) is the first control point
        (x2, y2) is the second control point
        (x3, y3) is the end point
        """
        x1, y1 = self._transform(x1, y1)
        x2, y2 = self._transform(x2, y2)
        x3, y3 = self._transform(x3, y3)
        self._ctx.curve_to(x1, y1, x2, y2, x3, y3)

    def quadratic_curve_to(self, x1: float, y1: float, x2: float, y2: float):
        """
        Draw a quadratic curve to the given coordinates from current pencil coordinates
        (x1, y1) is the control point
        (x2, y2) is the end point
        """
        x0, y0 = self.get_current_point()  # get the current point

        # compute the cubic control points, x(0) = x0, x(1) = x2, x(0.5) = x1
        # we need to compute x(0.33) and x(0.66) to get the control points
        # Convert quadratic to cubic Bézier control points
        cx1 = x0 + (2.0 / 3.0) * (x1 - x0)
        cy1 = y0 + (2.0 / 3.0) * (y1 - y0)
        cx2 = x2 + (2.0 / 3.0) * (x1 - x2)
        cy2 = y2 + (2.0 / 3.0) * (y1 - y2)  # assume linear interpolation
        self._ctx.curve_to(cx1, cy1, cx2, cy2, x2, y2)

    def rectangle(self, x: float, y: float, width: float, height: float):
        """
        Draw a rectangle at the given coordinates with the given width and height
        (x, y) is the bottom left corner
        """
        # as cairo uses the top left corner as starting point for rectangle
        top_left = (x, y + height)
        x, y = self._transform(*top_left)
        self._ctx.rectangle(x, y, width, height)

    def arc(self, x: float, y: float, radius: float, angle1: float, angle2: float):
        """
        Draw an arc at the given coordinates with the given radius and angles
        """
        x, y = self._transform(x, y)
        self._ctx.arc(x, y, radius, angle1, angle2)

    def circle(self, x: float, y: float, radius: float):
        """
        Draw a circle at the given coordinates with the given radius
        """
        x, y = self._transform(x, y)
        self._ctx.arc(x, y, radius, 0, 2 * np.pi)

    # although I can override the __getattr__ method to get the context methods
    # I think it is better to just use the context methods directly
    # because it provides the type hinting
    def save(self):
        """
        Save the current context state
        """
        self._ctx.save()

    def clip(self):
        """
        Clip the current path
        """
        self._ctx.clip()

    def restore(self):
        """
        Restore the context to the previous state
        """
        self._ctx.restore()

    def stroke(self):
        """
        Stroke the current path
        """
        self._ctx.stroke()

    def fill(self):
        """
        Fill the current path
        """
        self._ctx.fill()

    def set_source_rgb(self, r: float, g: float, b: float):
        """
        Set the source color for the context
        """
        self._ctx.set_source_rgb(r, g, b)

    def set_source_rgba(self, r: float, g: float, b: float, a: float):
        """
        Set the source color for the context with alpha
        """
        self._ctx.set_source_rgba(r, g, b, a)

    def set_line_width(self, width: float):
        """
        Set the line width for the context
        """
        self._ctx.set_line_width(width)
