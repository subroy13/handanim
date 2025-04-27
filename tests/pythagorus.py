from handanim.core.animation import AnimationEvent, AnimationEventType
from handanim.core.scene import Scene
from handanim.core.styles import StrokeStyle, SketchStyle, FillStyle
from handanim.primitives import Math, Eraser

scene = Scene(width=1920, height=1088)  # blank scene

# scene 1: draw the title
title_text = Math(
    tex_expression="Pythagoras' Theorem",
    position=(300, 500),
    font_size=96,
    stroke_style=StrokeStyle(color=(0, 0, 1), width=2),
    glow_dot_hint={"color": (0, 0, 1), "radius": 5},
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
    glow_dot_hint={"color": (0.7, 0.7, 0.7), "radius": 10},
)
scene.add(
    AnimationEvent(
        drawable=eraser, type=AnimationEventType.SKETCH, start_time=3.5, duration=1.5
    )
)


# save the scene
scene.render("pythagoras.mp4", max_length=10)
