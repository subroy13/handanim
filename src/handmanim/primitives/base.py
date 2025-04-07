from abc import ABC, abstractmethod

class BasePrimitive(ABC):
    """
        A base primitive class that defines the interface for all primitives.
        All primitives like Circle, Rectangle, etc. should inherit from this class.
        and implement the draw() method
    """

    @abstractmethod
    def draw(self, ctx):
        """
            Draw the primitive on the given cairo context.
            This method should be implemented by all subclasses.
        """
        pass