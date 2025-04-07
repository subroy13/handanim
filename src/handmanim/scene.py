from typing import List
import cairo
from pathlib import Path
from .primitives import BasePrimitive
from .transformed_context import TransformedContext

class Scene:
    def __init__(self, width: int=800, height: int=600, background_color: tuple[float, float, float] = (1, 1, 1)):
        self.width = width
        self.height = height
        self.background_color = background_color
        self.objects : List[BasePrimitive] = []

    def add(self, drawable: BasePrimitive):
        self.objects.append(drawable)

    def render(self, output_file="output.png"):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        cairo_ctx = cairo.Context(surface)
        ctx = TransformedContext(cairo_ctx, self.width, self.height)  # set the transformed context

        # Fill background
        ctx.set_source_rgb(*self.background_color)
        ctx.rectangle(0, 0, self.width, self.height)
        ctx.fill()

        # Draw each object
        for obj in self.objects:
            obj.draw(ctx)

        # Create output directory if it doesn't exist
        output_path = Path(output_file).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        surface.write_to_png(str(output_path))
        print(f"Scene rendered to {output_path}")
