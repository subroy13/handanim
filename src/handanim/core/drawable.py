from uuid import uuid4
from .draw_ops import OpsSet

class Drawable:
    """
    A base drawable class that defines the interface for all objects that can be drawn.
    All primitives like Circle, Rectangle, etc. should inherit from this class.
    and implement the draw() method
    """

    def __init__(self, *args, **kwargs):
        self.id = uuid4().hex  # generates an hexadecimal random id
    
    def draw(self) -> OpsSet:
        """
            Provides the list of operations to be performed to 
            draw this particular drawable object on the canvas
        """
        raise NotImplementedError(f"No method for drawing {self.__class__.__name__}")
