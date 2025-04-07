import cairo

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
        self._ctx.circle(x, y, radius)

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
