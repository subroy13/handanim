from handanim.core.animation import Scene, AnimationEvent, AnimationEventType
from handanim.primitives.ellipse import Ellipse
from handanim.core.styles import StrokeStyle, SketchStyle

scene = Scene(width=800, height=600)
ellipse = Ellipse(
    center=(250, 250),
    height=200,
    width=500,
    stroke_style=StrokeStyle(color=(1, 0, 0)),
    sketch_style=SketchStyle(roughness=2),
)
event = AnimationEvent(
    drawable=Ellipse, type=AnimationEventType.SKETCH, start_time=0, duration=3
)
scene.add(event)
scene.render(output_path="output.mp4", fps=20, max_length=5)
