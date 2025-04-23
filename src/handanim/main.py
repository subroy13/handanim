from handanim.core.animation import AnimationEvent, AnimationEventType
from handanim.core.scene import Scene
from handanim.primitives import Ellipse, Circle, Text, Math2, Math, Eraser
from handanim.core.styles import StrokeStyle, SketchStyle, FillStyle

scene = Scene(width=800, height=608)

ellipse = Ellipse(
    center=(300, 300),
    width=200,
    height=500,
    stroke_style=StrokeStyle(color=(1, 0.6, 0), width=2),
    sketch_style=SketchStyle(roughness=2),
    fill_style=FillStyle(color=(1, 0.6, 0), fill_pattern="hachure", hachure_gap=15),
)
event = AnimationEvent(
    type=AnimationEventType.SKETCH, drawable=ellipse, start_time=1, duration=4
)
scene.add(event)
event2 = AnimationEvent(
    drawable=ellipse, type=AnimationEventType.ZOOM_OUT, start_time=3, duration=3
)
scene.add(event2)

text2 = Math2(
    tex_expression=r"$e^{i\pi} + 1 = 0$",
    position=(100, 400),
    stroke_style=StrokeStyle(color=(0, 0, 1)),
    sketch_style=SketchStyle(),
    font_size=96,
)
event = AnimationEvent(
    type=AnimationEventType.SKETCH, drawable=text2, start_time=1, duration=3
)
scene.add(event)

eraser = Eraser(
    objects_to_erase=[text2],
    drawable_cache=scene.drawable_cache,
    stroke_style=StrokeStyle(color=(1, 1, 1)),
)
event = AnimationEvent(
    type=AnimationEventType.SKETCH,
    drawable=eraser,
    start_time=4,
    duration=3,
    data={"glowing_dot": {"radius": 5}},
)
scene.add(event)

scene.render(output_path="output.mp4", fps=30, max_length=8)
# scene.render_snapshot(output_path="output.svg", frame=5, fps=30, max_length=5)
