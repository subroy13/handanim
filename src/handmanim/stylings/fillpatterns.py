from abc import ABC, abstractmethod
import cairo

from .styles import FillStyle, SketchStyle


class BaseFillPattern(ABC):

    @abstractmethod
    def fill(self, ctx: cairo.Context):
        pass


class HachureFillPattern(BaseFillPattern):

    def __init__(
        self,
        fill_style: FillStyle = FillStyle(),
        sketch_style: SketchStyle = SketchStyle(),
    ):
        self.fill_style = fill_style
        self.sketch_style = sketch_style
