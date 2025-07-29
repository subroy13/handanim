import os
from handanim.core import (
    Scene, SketchStyle, StrokeStyle, FillStyle,
    DrawableGroup, CompositeAnimationEvent
)
from handanim.animations import (
    SketchAnimation, FadeInAnimation, FadeOutAnimation, ZoomInAnimation,
    ZoomOutAnimation, TranslateFromAnimation, TranslateToAnimation
)
from handanim.primitives import (
    Text, Circle, Line, RoundedRectangle, Eraser, Arrow
)
from handanim.stylings.color import (
    YELLOW, WHITE, BLACK, BLUE, GRAY, RED, ORANGE, LIGHT_GRAY, ERASER_HINT_COLOR
)

scene = Scene(width=1920, height=1088, background_color=BLACK)
scene.set_viewport_to_identity()

# Shared styles
text_style = StrokeStyle(color=WHITE)
eraser_style = StrokeStyle(color=BLACK)
planet_sketch = SketchStyle(roughness=2)
planet_fill = FillStyle(hachure_gap=8)

# --------------- Scene 1: Intro ---------------
title = Text("The Solar System", position=(960, 500), font_size=72, stroke_style=text_style)
subtitle = Text("A Journey Through Space and Scale", position=(960, 600), font_size=36, stroke_style=text_style)
scene.add(FadeInAnimation(start_time=0, duration=1), drawable=title)
scene.add(FadeInAnimation(start_time=0.5, duration=1), drawable=subtitle)

eraser = Eraser(
    objects_to_erase=[title, subtitle],
    drawable_cache=scene.drawable_cache,
    glow_dot_hint={"color": ERASER_HINT_COLOR, "radius": 10},
    stroke_style=eraser_style
)
scene.add(SketchAnimation(start_time=2, duration=0.5), drawable=eraser)


sun = Circle(
        center=(960, 600), 
        radius=120, 
        stroke_style=StrokeStyle(color=WHITE),
        fill_style=FillStyle(color=YELLOW, hachure_gap=10), 
        sketch_style=planet_sketch
    )

scene.add(
    event=SketchAnimation(start_time=2.5, duration=2),
    drawable=sun
)

# --------------- Scene 2: Planet Orbits ---------------
planet_data = [
    ("Mercury", 200, GRAY),
    ("Venus", 240, ORANGE),
    ("Earth", 280, BLUE),
    ("Mars", 320, RED),
    ("Jupiter", 400, LIGHT_GRAY),
    ("Saturn", 470, LIGHT_GRAY),
    ("Uranus", 540, LIGHT_GRAY),
    ("Neptune", 600, LIGHT_GRAY),
]

planet_drawables = []
start_time = 4
for idx, (name, radius, color) in enumerate(planet_data):
    planet = Circle(
        center=(960 + radius, 600),
        radius=8 + idx * 2,
        stroke_style=StrokeStyle(color=WHITE),
        fill_style=FillStyle(color=color, hachure_gap=6),
        sketch_style=planet_sketch
    )
    orbit = Circle(center=(960, 600), radius=radius, stroke_style=StrokeStyle(color=WHITE, width=1))
    planet = planet.translate(offset_x=-800, offset_y=0)  # move off-screen to the left
    scene.add(SketchAnimation(start_time=start_time, duration=0.5), drawable=orbit)
    scene.add(SketchAnimation(start_time=start_time, duration=0.1), drawable=planet)
    scene.add(
        TranslateToAnimation(start_time=start_time + 0.5, duration=1, 
                             data={"point": (960 + radius, 600)}),
        drawable=planet
    )

    planet_drawables.extend([orbit, planet])
    start_time += 0.7

# # Group them for future transformation
# planetary_system = DrawableGroup(elements=[sun] + planet_drawables)

# # --------------- Scene 3: Shrinking the Solar System ---------------
# msg = Text("But what does this mean for us?", position=(960, 540), font_size=48, stroke_style=text_style)

# scene.add(CompositeAnimationEvent([
#     ZoomOutAnimation(start_time=11, duration=2),
# ]), drawable=planetary_system)

# scene.add(SketchAnimation(start_time=13, duration=1), drawable=msg)

# # --------------- Scene 4: Earth-Moon-Sun Scale ---------------
# earth = Circle(center=(400, 500), radius=20, stroke_style=StrokeStyle(color=BLACK),
#                fill_style=FillStyle(color=BLUE, hachure_gap=8), sketch_style=planet_sketch)

# moon = Circle(center=(480, 500), radius=6, stroke_style=StrokeStyle(color=BLACK),
#               fill_style=FillStyle(color=GRAY, hachure_gap=6), sketch_style=planet_sketch)

# moon_line = Line(start=(400, 500), end=(480, 500), stroke_style=StrokeStyle(color=WHITE))
# moon_label = Text("384,400 km", position=(440, 530), font_size=24, stroke_style=text_style)

# sun_far = Circle(center=(1600, 500), radius=200, stroke_style=StrokeStyle(color=BLACK),
#                  fill_style=FillStyle(color=YELLOW, hachure_gap=10), sketch_style=planet_sketch)

# sun_label = Text("Sun ~150 million km", position=(1600, 750), font_size=24, stroke_style=text_style)

# scale_box = RoundedRectangle(
#     top_left=(300, 850), width=700, height=100,
#     stroke_style=StrokeStyle(color=WHITE), sketch_style=SketchStyle(roughness=2))

# scene.add(FadeInAnimation(start_time=15, duration=1), drawable=earth)
# scene.add(FadeInAnimation(start_time=15.5, duration=1), drawable=moon)
# scene.add(FadeInAnimation(start_time=15.7, duration=1), drawable=moon_line)
# scene.add(FadeInAnimation(start_time=16, duration=1), drawable=moon_label)
# scene.add(FadeInAnimation(start_time=16.3, duration=1), drawable=sun_far)
# scene.add(FadeInAnimation(start_time=16.7, duration=1), drawable=sun_label)
# scene.add(FadeInAnimation(start_time=17, duration=1), drawable=scale_box)


# # --------------- Scene 5: Cosmic Perspective ---------------
# scene.add(FadeOutAnimation(start_time=18.5, duration=1), drawable=scale_box)

# eraser = Eraser(
#     objects_to_erase=[scale_box],
#     drawable_cache=scene.drawable_cache,
#     glow_dot_hint={"color": ERASER_HINT_COLOR, "radius": 10},
# )
# scene.add(SketchAnimation(start_time=20, duration=2), drawable=eraser)

# stars = [Circle(center=(x, y), radius=2, stroke_style=StrokeStyle(color=WHITE)) for x, y in
#          [(100, 200), (300, 400), (600, 150), (800, 500), (1100, 300), (1400, 650), (1700, 200)]]

# text1 = Text("Humans are tiny...", position=(960, 440), font_size=42, stroke_style=text_style)
# text2 = Text("...but our curiosity is infinite.", position=(960, 520), font_size=42, stroke_style=text_style)

# for i, star in enumerate(stars):
#     scene.add(FadeInAnimation(start_time=22 + i * 0.2, duration=1), drawable=star)

# scene.add(SketchAnimation(start_time=24, duration=1), drawable=text1)
# scene.add(SketchAnimation(start_time=25, duration=1), drawable=text2)


# # --------------- Scene 6: Final Zoomed View ---------------
# tiny_earth = Circle(center=(200, 900), radius=10, stroke_style=StrokeStyle(color=BLUE), sketch_style=planet_sketch)
# arrow_to_solar = Arrow(start_point=(200, 900), end_point=(800, 600), stroke_style=StrokeStyle(color=WHITE))
# final_msg = Text("Keep exploring.", position=(960, 100), font_size=48, stroke_style=text_style)

# scene.add(SketchAnimation(start_time=27, duration=1), drawable=tiny_earth)
# scene.add(SketchAnimation(start_time=27.5, duration=1), drawable=arrow_to_solar)
# scene.add(FadeInAnimation(start_time=28, duration=1), drawable=final_msg)

# # --------------- End Message ---------------
# end_text = Text("Let's keep exploring the universe.", position=(960, 1000), font_size=24, stroke_style=text_style)
# scene.add(FadeInAnimation(start_time=29, duration=1.5), drawable=end_text)

# --------------- Render All ---------------
output_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "output", "solar_system_journey.mp4"
)
scene.render(output_path, max_length=17)

