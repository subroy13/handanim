import os
from handanim.core import (
    Scene,
    StrokeStyle,
)
from handanim.animations import SketchAnimation, FadeInAnimation
from handanim.primitives import Math, Text
from handanim.stylings.color import BLUE, GREEN

scene = Scene(width=1920, height=1088)  # blank scene (viewport = 1777, 1000)


text1 = Math(
    tex_expression=r"Pardon my bad handwriting",
    position=(300, 200),
    font_size=96,
    stroke_style=StrokeStyle(color=GREEN, width=2),
)
scene.add(event=SketchAnimation(start_time=0, duration=3), drawable=text1)

text2 = Text(
    text="But, here's a great equation",
    position=(300, 400),
    font_size=96,
    stroke_style=StrokeStyle(color=GREEN, width=2),
)
scene.add(event=FadeInAnimation(start_time=3, duration=3), drawable=text2)

text1 = Math(
    tex_expression=r"$e^{i\pi} + 1 = 0$",
    position=(300, 600),
    font_size=192,
    stroke_style=StrokeStyle(color=BLUE, width=2),
    glow_dot_hint={"color": BLUE, "radius": 5},
    font_name="handanimtype1",
)
scene.add(event=SketchAnimation(start_time=6, duration=3), drawable=text1)

# save the scene
output_root_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "output")
scene.render(os.path.join(output_root_path, "custom_font.mp4"), max_length=10)

# scene.render(os.path.join(output_root_path, "custom_font.gif"), max_length=10)
