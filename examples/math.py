import os
from handanim.core import (
    AnimationEvent,
    AnimationEventType,
    Scene,
    SketchStyle,
    StrokeStyle,
    FillStyle,
)
from handanim.primitives import Text, Eraser, Polygon, Math
from handanim.stylings.color import *

scene = Scene(width=1920, height=1088)  # blank scene (viewport = 1777, 1000)

text1 = Math(
    tex_expression=r"$e^{i\pi} + 1 = 0$",
    position=(300, 500),
    font_size=192,
    stroke_style=StrokeStyle(color=BLUE, width=2),
    glow_dot_hint={"color": BLUE, "radius": 5},
    font_name="handanimtype1",
)
scene.add(
    AnimationEvent(
        drawable=text1,
        type=AnimationEventType.SKETCH,
        start_time=0,
        duration=3,
    )
)

# save the scene
output_root_path = os.path.dirname(os.path.realpath(__file__))
scene.render(os.path.join(output_root_path, "sample.mp4"), max_length=5)
# scene.render_snapshot(
#     os.path.join(output_root_path, "sample.svg"), frame_in_seconds=3, max_length=4
# )
