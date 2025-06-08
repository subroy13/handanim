import os
from handanim.core import (
    Scene,
    SketchStyle,
    StrokeStyle,
    FillStyle,
    DrawableGroup,
    CompositeAnimationEvent,
)
from handanim.animations import (
    SketchAnimation,
    FadeOutAnimation,
    ZoomOutAnimation,
    TranslateToAnimation,
    FadeInAnimation,
)
from handanim.primitives import Math, Eraser, Square, Line, Rectangle
from handanim.stylings.color import BLUE, RED, BLACK, ERASER_HINT_COLOR, ORANGE

scene = Scene(width=1920, height=1088)  # blank scene (viewport = 1777, 1000)
FONT_NAME = "feasibly"
VALUE_A = 100
VALUE_B = 200
A_PLUS_B = VALUE_A + VALUE_B
sq_top_left = (300, 500)


# scene 1: draw the title and fade in
title_text = Math(
    tex_expression=r"$(a + b)^2 = ?$",
    position=sq_top_left,
    font_size=192,
    stroke_style=StrokeStyle(color=BLUE, width=2),
    glow_dot_hint={"color": BLUE, "radius": 5},
    font_name=FONT_NAME,
)

scene.add(
    event=CompositeAnimationEvent(
        events=[
            SketchAnimation(duration=1),
            FadeOutAnimation(start_time=1, duration=2),
        ]
    ),
    drawable=title_text,
)


# scene 2: draw the square
a_plus_b_sq = Square(
    top_left=sq_top_left,
    side_length=A_PLUS_B,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    fill_style=FillStyle(color=BLUE, hachure_gap=10),
    sketch_style=SketchStyle(roughness=3),
)
scene.add(event=SketchAnimation(start_time=3.5, duration=3), drawable=a_plus_b_sq)
# rectangle draws from (3.5s to 6.5s)

a_plus_b_label_group = DrawableGroup(
    elements=[
        Math(
            tex_expression=r"$a + b$",
            position=pos,
            font_size=60,
            stroke_style=StrokeStyle(color=BLACK, width=2),
            font_name=FONT_NAME,
        )
        for pos in [
            (sq_top_left[0] + A_PLUS_B / 2, sq_top_left[1] - 100),
            (sq_top_left[0] + A_PLUS_B + 50, sq_top_left[1] + A_PLUS_B / 2),
        ]
    ]
)
a_plus_b_sq_label = Math(
    tex_expression=r"$(a + b)^2$",
    position=(600, 200),
    font_size=96,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    font_name=FONT_NAME,
)

# the other labels should by this time move into this point and zoom out
scene.add(
    CompositeAnimationEvent(
        events=[
            SketchAnimation(start_time=3.5, duration=1),
            ZoomOutAnimation(start_time=4.5, duration=2),
            TranslateToAnimation(
                start_time=4.5, duration=2, data={"point": a_plus_b_sq_label.position}
            ),
        ]
    ),
    drawable=a_plus_b_label_group,
)
scene.add(
    event=FadeInAnimation(start_time=6.5, duration=1),
    drawable=a_plus_b_sq_label,
)  # it should start appearing at 6.5s


# scene 3: draw the horizontal and vertical lines
vert_line = Line(
    start=(sq_top_left[0] + VALUE_A, sq_top_left[1]),
    end=(sq_top_left[0] + VALUE_A, sq_top_left[1] + A_PLUS_B),
    stroke_style=StrokeStyle(color=BLACK, width=2),
)
horiz_line = Line(
    start=(sq_top_left[0], sq_top_left[1] + VALUE_A),
    end=(sq_top_left[0] + A_PLUS_B, sq_top_left[1] + VALUE_A),
    stroke_style=StrokeStyle(color=BLACK, width=2),
)
horiz_vert_line_group = DrawableGroup(elements=[vert_line, horiz_line])
scene.add(
    event=SketchAnimation(start_time=7, duration=1), drawable=horiz_vert_line_group
)

# scene 4: draw the a_sq and b_sq
a_sq = Square(
    top_left=sq_top_left,
    side_length=VALUE_A,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    fill_style=FillStyle(color=RED, hachure_gap=10, hachure_angle=135),
    sketch_style=SketchStyle(roughness=3),
)
scene.add(SketchAnimation(start_time=8.5, duration=2), drawable=a_sq)

# add labels, they zoom out and move to the point
a_label_group = DrawableGroup(
    elements=[
        Math(
            tex_expression=r"$a$",
            position=pos,
            font_size=60,
            stroke_style=StrokeStyle(color=BLACK, width=2),
            font_name=FONT_NAME,
        )
        for pos in [
            (sq_top_left[0] + VALUE_A / 2, sq_top_left[1] - 100),
            (sq_top_left[0] - 100, sq_top_left[1] + VALUE_A / 2),
        ]
    ]
)
a_sq_label = Math(
    tex_expression=r"$= a^2$",
    position=(950, 200),
    font_size=96,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    font_name=FONT_NAME,
)

# the other labels should by this time move into this point and zoom out
scene.add(
    CompositeAnimationEvent(
        events=[
            SketchAnimation(start_time=10.5, duration=1),
            ZoomOutAnimation(start_time=11.5, duration=2),
            TranslateToAnimation(
                start_time=11.5, duration=2, data={"point": a_sq_label.position}
            ),
        ]
    ),
    drawable=a_label_group,
)
scene.add(
    event=FadeInAnimation(start_time=13.5, duration=1),
    drawable=a_sq_label,
)


b_sq = Square(
    top_left=(sq_top_left[0] + VALUE_A, sq_top_left[1] + VALUE_A),
    side_length=VALUE_B,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    fill_style=FillStyle(color=RED, hachure_gap=10, hachure_angle=135),
    sketch_style=SketchStyle(roughness=3),
)
scene.add(SketchAnimation(start_time=13.5, duration=2), drawable=b_sq)

# add labels, they zoom out and move to the point
b_label_group = DrawableGroup(
    elements=[
        Math(
            tex_expression=r"$b$",
            position=pos,
            font_size=60,
            stroke_style=StrokeStyle(color=BLACK, width=2),
            font_name=FONT_NAME,
        )
        for pos in [
            (sq_top_left[0] + VALUE_A + VALUE_B / 2, sq_top_left[1] + A_PLUS_B + 100),
            (sq_top_left[0] + A_PLUS_B + 100, sq_top_left[1] + VALUE_A + VALUE_B / 2),
        ]
    ]
)
b_sq_label = Math(
    tex_expression=r"$+ b^2$",
    position=(1200, 200),
    font_size=96,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    font_name=FONT_NAME,
)

# the other labels should by this time move into this point and zoom out
scene.add(
    CompositeAnimationEvent(
        events=[
            SketchAnimation(start_time=15.5, duration=1),
            ZoomOutAnimation(start_time=16.5, duration=2),
            TranslateToAnimation(
                start_time=16.5, duration=2, data={"point": b_sq_label.position}
            ),
        ]
    ),
    drawable=b_label_group,
)
scene.add(
    event=FadeInAnimation(start_time=18.5, duration=1),
    drawable=b_sq_label,
)

# scene 5: add the rectangles
a_b_rect = Rectangle(
    top_left=(sq_top_left[0] + VALUE_A, sq_top_left[1]),
    width=VALUE_B,
    height=VALUE_A,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    fill_style=FillStyle(color=ORANGE, hachure_gap=10, hachure_angle=135),
    sketch_style=SketchStyle(roughness=3),
)
scene.add(SketchAnimation(start_time=19.5, duration=2), drawable=a_b_rect)

a_b_label = Math(
    tex_expression=r"$+ ab$",
    position=(1350, 200),
    font_size=96,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    font_name=FONT_NAME,
)
a_b_rect_label_group = DrawableGroup(
    elements=[
        Math(
            tex_expression=label,
            position=(posx, posy),
            font_size=60,
            stroke_style=StrokeStyle(color=BLACK, width=2),
            font_name=FONT_NAME,
        )
        for label, posx, posy in [
            (
                r"$a$",
                sq_top_left[0] + VALUE_A + VALUE_B + 50,
                sq_top_left[1] + VALUE_A / 2,
            ),
            (
                r"$b$",
                sq_top_left[0] + VALUE_A + VALUE_B / 2,
                sq_top_left[1] - 100,
            ),
        ]
    ]
)
# the other labels should by this time move into this point and zoom out
scene.add(
    CompositeAnimationEvent(
        events=[
            SketchAnimation(start_time=21.5, duration=1),
            ZoomOutAnimation(start_time=22.5, duration=2),
            TranslateToAnimation(
                start_time=22.5, duration=2, data={"point": a_b_label.position}
            ),
        ]
    ),
    drawable=a_b_rect_label_group,
)
scene.add(
    event=FadeInAnimation(start_time=24.5, duration=1),
    drawable=a_b_label,
)

# second rectangle
a_b_rect2 = Rectangle(
    top_left=(sq_top_left[0], sq_top_left[1] + VALUE_A),
    width=VALUE_A,
    height=VALUE_B,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    fill_style=FillStyle(color=ORANGE, hachure_gap=10, hachure_angle=135),
    sketch_style=SketchStyle(roughness=3),
)
scene.add(SketchAnimation(start_time=25.5, duration=2), drawable=a_b_rect2)

a_b_label2 = Math(
    tex_expression=r"$+ ab$",
    position=(1550, 200),
    font_size=96,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    font_name=FONT_NAME,
)
a_b_rect_label_group2 = DrawableGroup(
    elements=[
        Math(
            tex_expression=label,
            position=(posx, posy),
            font_size=60,
            stroke_style=StrokeStyle(color=BLACK, width=2),
            font_name=FONT_NAME,
        )
        for label, posx, posy in [
            (
                r"$b$",
                sq_top_left[0] - 100,
                sq_top_left[1] + VALUE_A + VALUE_B / 2,
            ),
            (
                r"$a$",
                sq_top_left[0] + VALUE_A / 2,
                sq_top_left[1] + A_PLUS_B + 50,
            ),
        ]
    ]
)
# the other labels should by this time move into this point and zoom out
scene.add(
    CompositeAnimationEvent(
        events=[
            SketchAnimation(start_time=27.5, duration=1),
            ZoomOutAnimation(start_time=28.5, duration=2),
            TranslateToAnimation(
                start_time=28.5, duration=2, data={"point": a_b_label2.position}
            ),
        ]
    ),
    drawable=a_b_rect_label_group2,
)
scene.add(
    event=FadeInAnimation(start_time=30.5, duration=1),
    drawable=a_b_label2,
)


# add final equation
final_eq = Math(
    tex_expression=r"$= a^2 + b^2 + 2ab$",
    position=(950, 320),
    font_size=96,
    stroke_style=StrokeStyle(color=BLUE, width=2),
    font_name=FONT_NAME,
)
scene.add(
    event=SketchAnimation(start_time=32.5, duration=1.5),
    drawable=final_eq,
)


# save the scene
output_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "output", "a_plus_b_square.mp4"
)
scene.render(output_path, max_length=35)
