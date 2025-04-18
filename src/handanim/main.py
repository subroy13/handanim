from handanim.core.animation import Scene, AnimationEvent, AnimationEventType

# from handanim.primitives.ellipse import Ellipse
from handanim.primitives.text import Text
from handanim.core.styles import StrokeStyle, SketchStyle, FillStyle

scene = Scene(width=800, height=608)
text = Text(
    text="Hello World!",
    position=(100, 100),
    stroke_style=StrokeStyle(color=(1, 0, 0), width=8),
    sketch_style=SketchStyle(),
    font_size=48,
)
event = AnimationEvent(
    type=AnimationEventType.SKETCH, drawable=text, start_time=1, duration=3
)
scene.add(event)

scene.render(output_path="output.mp4", fps=30, max_length=5)
