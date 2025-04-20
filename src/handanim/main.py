from handanim.core.animation import Scene, AnimationEvent, AnimationEventType

from handanim.primitives import Ellipse, Circle, Text
from handanim.primitives.math import Math, Math2
from handanim.core.styles import StrokeStyle, SketchStyle, FillStyle

scene = Scene(width=800, height=608)

# ellipse = Circle(
#     center=(300, 300),
#     radius=100,
#     stroke_style=StrokeStyle(color=(1, 0.6, 0), width=2),
#     sketch_style=SketchStyle(),
#     fill_style=FillStyle(color=(1, 0.6, 0), fill_pattern="hachure"),
# )
# event = AnimationEvent(
#     type=AnimationEventType.SKETCH, drawable=ellipse, start_time=1, duration=3
# )
# scene.add(event)

text2 = Math2(
    tex_expression=r"$e^{i\pi} + 1 = 0$",
    position=(100, 300),
    stroke_style=StrokeStyle(color=(0, 0, 1)),
    sketch_style=SketchStyle(),
    font_size=96,
)
event = AnimationEvent(
    type=AnimationEventType.SKETCH, drawable=text2, start_time=1, duration=3
)
scene.add(event)


scene.render(output_path="output.mp4", fps=30, max_length=5)
# scene.render_snapshot(output_path="output.svg", frame=5, fps=30, max_length=5)
