import cairo
import os
from pathlib import Path

class Scene:
    def __init__(self, width=800, height=600, background_color=(1, 1, 1)):
        self.width = width
        self.height = height
        self.background_color = background_color
        self.objects = []

    def add(self, drawable):
        self.objects.append(drawable)

    def render(self, output_file="output.png"):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        ctx = cairo.Context(surface)

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
