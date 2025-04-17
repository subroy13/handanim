from handanim.core.animation import Scene, AnimationEvent, AnimationEventType
from handanim.primitives.ellipse import Ellipse
from handanim.primitives.polygons import Rectangle
from handanim.core.styles import StrokeStyle, SketchStyle, FillStyle

scene = Scene(width=800, height=608)
ellipse = Ellipse(
    center=(400, 300),
    height=150,
    width=350,
    stroke_style=StrokeStyle(color=(1, 0, 0)),
    sketch_style=SketchStyle(roughness=2),
    fill_style=FillStyle(),
)
event = AnimationEvent(
    drawable=ellipse, type=AnimationEventType.SKETCH, start_time=0, duration=3
)
scene.add(event)

rect = Rectangle(
    top_left=(400, 300),
    height=150,
    width=350,
    stroke_style=StrokeStyle(color=(0, 0, 1)),
    sketch_style=SketchStyle(roughness=2),
)
event2 = AnimationEvent(
    drawable=rect, type=AnimationEventType.SKETCH, start_time=1, duration=2
)
scene.add(event2)

scene.render(output_path="output.mp4", fps=30, max_length=5)
