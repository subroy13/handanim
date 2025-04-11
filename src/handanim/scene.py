from typing import List
import cairo
from pathlib import Path
from .primitives.base import BasePrimitive


class Scene:
    def __init__(
        self,
        width: int = 800,
        height: int = 600,
        background_color: tuple[float, float, float] = (1, 1, 1),
    ):
        self.width = width
        self.height = height
        self.background_color = background_color
        self.objects: List[BasePrimitive] = []

    def add(self, drawable: BasePrimitive):
        self.objects.append(drawable)

    def render(self, output_file="output.svg"):
        # create the output directory
        output_path = Path(output_file).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with cairo.SVGSurface(output_file, self.width, self.height) as surface:
            ctx = cairo.Context(surface)

            # fill the background
            ctx.set_source_rgb(*self.background_color)
            ctx.rectangle(0, 0, self.width, self.height)  # fill the entire area
            ctx.fill()

            # draw each object
            for obj in self.objects:
                obj.draw(ctx)
        print(f"Scene rendered to {output_path}")
