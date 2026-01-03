"""
Distributive Property animation
Written by Hamd Waseem (https://github.com/hamdivazim)
"""

import os
from handanim.core import Scene, SketchStyle, StrokeStyle, FillStyle, DrawableGroup
from handanim.animations import (
    SketchAnimation,
    FadeInAnimation,
    TranslateToPersistAnimation,
)
from handanim.primitives import Math, Text, Rectangle
from handanim.primitives.vector_svg import VectorSVG
from handanim.stylings.color import BLUE, BLACK, ORANGE

scene = Scene(width=1920, height=1080)
FONT_NAME = "feasibly"

assets_dir = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "assets"
)

# title and operator
svg_path = os.path.join(assets_dir, "professor.svg")
operator = VectorSVG.from_svg_file(
    svg_path,
    position=(1500, 700),
    glow_dot_hint={"color": BLUE, "radius": 5},
)
operator.scale(0.5, 0.5)
scene.add(
    event=SketchAnimation(start_time=0.5, duration=2),
    drawable=operator,
)
title_text = Text(
    text="Distributive Property",
    position=(500, 120),
    font_size=120,
    stroke_style=StrokeStyle(color=BLUE, width=2),
    glow_dot_hint={"color": BLUE, "radius": 5},
)
scene.add(
    event=SketchAnimation(start_time=0.5, duration=2),
    drawable=title_text,
)

# rectangles
rect_ab = Rectangle(
    top_left=(400, 500),
    width=200,
    height=150,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    fill_style=FillStyle(color=BLUE, hachure_gap=10),
)
rect_ac = Rectangle(
    top_left=(1200, 500),
    width=300,
    height=150,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    fill_style=FillStyle(color=ORANGE, hachure_gap=10),
)

scene.add(
    event=SketchAnimation(start_time=2.5, duration=1.5),
    drawable=rect_ab,
)
scene.add(
    event=SketchAnimation(start_time=3.0, duration=1.5),
    drawable=rect_ac,
)

# labels
label_a = Math(r"$a$", position=(310, 525), font_size=70)
label_b = Math(r"$b$", position=(470, 400), font_size=70)
label_c = Math(r"$c$", position=(1350, 400), font_size=70)

scene.add(
    event=FadeInAnimation(start_time=4.0, duration=0.5),
    drawable=label_a,
)
scene.add(
    event=FadeInAnimation(start_time=4.2, duration=0.5),
    drawable=label_b,
)
scene.add(
    event=FadeInAnimation(start_time=4.4, duration=0.5),
    drawable=label_c,
)

# assembly animation
scene.add(
    event=TranslateToPersistAnimation(
        start_time=5.5, duration=1, data={"point": (1550, 600)}
    ),
    drawable=operator,
)
scene.add(
    event=TranslateToPersistAnimation(
        start_time=7.0, duration=2, data={"point": (750, 575)}
    ),
    drawable=rect_ac,
)
scene.add(
    event=TranslateToPersistAnimation(
        start_time=7.0, duration=2, data={"point": (750, 450)}
    ),
    drawable=label_c,
)
scene.add(
    event=TranslateToPersistAnimation(
        start_time=7.0, duration=2, data={"point": (1000, 600)}
    ),
    drawable=operator,
)

# final equation
final_formula = Math(
    tex_expression=r"$a(b + c) = ab + ac$",
    position=(400, 200),
    font_size=110,
    stroke_style=StrokeStyle(color=BLACK, width=3),
    font_name=FONT_NAME,
)
scene.add(
    event=SketchAnimation(start_time=9.5, duration=2),
    drawable=final_formula,
)

# render
output_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "output", "distributive_property.mp4"
)
scene.render(output_path, max_length=12)
