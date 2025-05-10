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

# scene 1: draw the title
title_text = Text(
    text="Pythagoras' Theorem",
    position=(300, 500),
    font_size=192,
    stroke_style=StrokeStyle(color=BLUE, width=2),
    glow_dot_hint={"color": BLUE, "radius": 5},
)
scene.add(
    AnimationEvent(
        drawable=title_text,
        type=AnimationEventType.SKETCH,
        start_time=0,
        duration=3,
    )
)

# then erase the title
eraser = Eraser(
    objects_to_erase=[title_text],
    drawable_cache=scene.drawable_cache,
    glow_dot_hint={"color": ERASER_HINT_COLOR, "radius": 10},
)
scene.add(
    AnimationEvent(
        drawable=eraser, type=AnimationEventType.SKETCH, start_time=3.5, duration=1.5
    )
)  # ends at 5 seconds


# scene 2: draw the right triangle
right_triangle = Polygon(
    points=[
        (500, 500),
        (500, 700),
        (900, 700),
    ],
    stroke_style=StrokeStyle(color=BLACK, width=2),
    sketch_style=SketchStyle(roughness=5),
    fill_style=FillStyle(color=RED, hachure_gap=10),
)
scene.add(
    AnimationEvent(
        drawable=right_triangle,
        type=AnimationEventType.SKETCH,
        start_time=6,
        duration=3,
    )
)

# draw line labels
line_labels = [("a", (450, 600)), ("b", (700, 800)), ("c", (700, 550))]
for label, pos in line_labels:
    text = Text(text=label, position=pos, font_size=96)
    scene.add(
        AnimationEvent(
            drawable=text,
            type=AnimationEventType.SKETCH,
            start_time=8,
            duration=2,
        )
    )

# write pythagorus formula
pyth_form = Math(
    tex_expression=r"$a^2 + b^2 = c^2$",
    position=(900, 300),
    font_size=128,
    stroke_style=StrokeStyle(color=BLUE, width=2),
)
scene.add(
    AnimationEvent(
        drawable=pyth_form,
        type=AnimationEventType.SKETCH,
        start_time=10,
        duration=3,
    )
)

# save the scene
output_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "output", "pythagoras.mp4"
)
scene.render(output_path, max_length=15)
# scene.render_snapshot("pythagoras.svg", frame_in_seconds=3, max_length=15)
