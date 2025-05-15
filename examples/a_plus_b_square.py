import os
from handanim.core import (
    AnimationEvent,
    AnimationEventType,
    Scene,
    SketchStyle,
    StrokeStyle,
    FillStyle,
)
from handanim.primitives import Math, Eraser, Square, Line
from handanim.stylings.color import BLUE, RED, BLACK, ERASER_HINT_COLOR

scene = Scene(width=1920, height=1088)  # blank scene (viewport = 1777, 1000)
FONT_NAME = "feasibly"
VALUE_A = 100
VALUE_B = 200

# TODO: Techniques to add
# 1) Need to add a wait event before fill
# 2) Composition of the animation, and make it reusable with partials -> that can be applied to a group of primitives
# 3) Grouping of the primitives


# scene 1: draw the title and fade in
title_text = Math(
    tex_expression=r"$(a + b)^2 = ?$",
    position=(300, 500),
    font_size=192,
    stroke_style=StrokeStyle(color=BLUE, width=2),
    glow_dot_hint={"color": BLUE, "radius": 5},
    font_name=FONT_NAME,
)
scene.add(
    AnimationEvent(
        drawable=title_text,
        type=AnimationEventType.SKETCH,
        start_time=0,
        duration=1,
    )
)
scene.add(
    AnimationEvent(
        drawable=title_text, type=AnimationEventType.FADE_OUT, start_time=1, duration=2
    )
)

# scene 2: draw the square
a_plus_b_sq = Square(
    top_left=(300, 500),
    side_length=(VALUE_A + VALUE_B),
    stroke_style=StrokeStyle(color=BLACK, width=2),
    fill_style=FillStyle(color=BLUE, hachure_gap=10),
    sketch_style=SketchStyle(roughness=3),
)
scene.add(
    AnimationEvent(
        drawable=a_plus_b_sq,
        type=AnimationEventType.SKETCH,
        start_time=3.5,
        duration=3,
    )
)  # rectangle draws from (3.5s to 6.5s)

a_plus_b_label1 = Math(
    tex_expression=r"$a + b$",
    position=(350, 400),
    font_size=60,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    font_name=FONT_NAME,
)
scene.add(
    AnimationEvent(
        drawable=a_plus_b_label1,
        type=AnimationEventType.SKETCH,
        start_time=3.5,
        duration=1,
    )
)
a_plus_b_label2 = Math(
    tex_expression=r"$a + b$",
    position=(650, 650),
    font_size=60,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    font_name=FONT_NAME,
)
scene.add(
    AnimationEvent(
        drawable=a_plus_b_label2,
        type=AnimationEventType.SKETCH,
        start_time=3.5,
        duration=1,
    )
)


a_plus_b_sq_label = Math(
    tex_expression=r"$(a + b)^2$",
    position=(700, 200),
    font_size=96,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    font_name=FONT_NAME,
)
scene.add(
    AnimationEvent(
        drawable=a_plus_b_sq_label,
        type=AnimationEventType.FADE_IN,
        start_time=6.5,
        duration=1,
    )
)

# the other labels should by this time move into this point and zoom out
for label in [a_plus_b_label1, a_plus_b_label2]:
    scene.add(
        AnimationEvent(
            drawable=label,
            type=AnimationEventType.ZOOM_OUT,
            start_time=4.5,
            duration=2,
        )
    )
    scene.add(
        AnimationEvent(
            drawable=label,
            type=AnimationEventType.TRANSLATE_TO_POINT,
            start_time=4.5,
            duration=2,
            data={"point": a_plus_b_sq_label.position},
        )
    )


# scene 3: draw the horizontal and vertical lines
vert_line = Line(
    start=(a_plus_b_sq.top_left[0] + VALUE_A, a_plus_b_sq.top_left[1]),
    end=(
        a_plus_b_sq.top_left[0] + VALUE_A,
        a_plus_b_sq.top_left[1] + a_plus_b_sq.side_length,
    ),
    stroke_style=StrokeStyle(color=BLACK, width=2),
)
scene.add(
    AnimationEvent(
        drawable=vert_line,
        type=AnimationEventType.SKETCH,
        start_time=7,
        duration=1,
    )
)
horiz_line = Line(
    start=(a_plus_b_sq.top_left[0], a_plus_b_sq.top_left[1] + VALUE_A),
    end=(
        a_plus_b_sq.top_left[0] + a_plus_b_sq.side_length,
        a_plus_b_sq.top_left[1] + VALUE_A,
    ),
    stroke_style=StrokeStyle(color=BLACK, width=2),
)
scene.add(
    AnimationEvent(
        drawable=horiz_line,
        type=AnimationEventType.SKETCH,
        start_time=7,
        duration=1,
    )
)

# scene 4: draw the a_sq and b_sq
a_sq = Square(
    top_left=a_plus_b_sq.top_left,
    side_length=VALUE_A,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    fill_style=FillStyle(color=RED, hachure_gap=10),
    sketch_style=SketchStyle(roughness=3),
)
scene.add(
    AnimationEvent(
        drawable=a_sq,
        type=AnimationEventType.SKETCH,
        start_time=8.5,
        duration=2,
    )
)

# add a labels, they zoom out and move to the point


b_sq = Square(
    top_left=(
        a_plus_b_sq.top_left[0] + VALUE_A,
        a_plus_b_sq.top_left[1] + VALUE_A,
    ),
    side_length=VALUE_B,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    fill_style=FillStyle(color=RED, hachure_gap=10),
    sketch_style=SketchStyle(roughness=3),
)
scene.add(
    AnimationEvent(
        drawable=b_sq,
        type=AnimationEventType.SKETCH,
        start_time=10.5,
        duration=2,
    )
)


# save the scene
output_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "output", "a_plus_b_square.mp4"
)
scene.render(output_path, max_length=12)
