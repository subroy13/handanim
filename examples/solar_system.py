from typing import List
import os
import numpy as np
from handanim.core import Scene, SketchStyle, StrokeStyle, FillStyle, DrawableGroup, CompositeAnimationEvent, Drawable
from handanim.animations import (
    SketchAnimation,
    FadeInAnimation,
    FadeOutAnimation,
    ZoomInAnimation,
    ZoomOutAnimation,
    TranslateFromAnimation,
    TranslateToAnimation,
)
from handanim.primitives import Text, Circle, Line, RoundedRectangle, Eraser, Arrow
from handanim.stylings.color import YELLOW, WHITE, BLACK, BLUE, GRAY, RED, ORANGE, LIGHT_GRAY, ERASER_HINT_COLOR

scene = Scene(width=1920, height=1088, background_color=BLACK)
scene.set_viewport_to_identity()

# Shared styles
text_style = StrokeStyle(color=WHITE)
eraser_style = StrokeStyle(color=BLACK)
planet_sketch = SketchStyle(roughness=2)
planet_fill = FillStyle(hachure_gap=8)

# # --------------- Scene 1: Intro ---------------
# title = Text("The Solar System", position=(960, 500), font_size=72, stroke_style=text_style)
# subtitle = Text("A Journey Through Space and Scale", position=(960, 600), font_size=36, stroke_style=text_style)
# scene.add(FadeInAnimation(start_time=0, duration=1), drawable=title)
# scene.add(FadeInAnimation(start_time=0.5, duration=1), drawable=subtitle)

# eraser = Eraser(
#     objects_to_erase=[title, subtitle],
#     drawable_cache=scene.drawable_cache,
#     glow_dot_hint={"color": ERASER_HINT_COLOR, "radius": 10},
#     stroke_style=eraser_style,
# )
# scene.add(SketchAnimation(start_time=2, duration=0.5), drawable=eraser)


# sun = Circle(
#     center=(960, 600),
#     radius=80,
#     stroke_style=StrokeStyle(color=WHITE),
#     fill_style=FillStyle(color=YELLOW, hachure_gap=10),
#     sketch_style=planet_sketch,
#     id="sun",
# )

# scene.add(event=SketchAnimation(start_time=2.5, duration=2), drawable=sun)

# # --------------- Scene 2: Planet Orbits ---------------
# planet_data = [
#     # name, orbit_radius, planet_radius, color
#     ("Mercury", 150, 6, GRAY),
#     ("Venus", 180, 9, ORANGE),
#     ("Earth", 215, 10, BLUE),
#     ("Mars", 260, 7, RED),
#     ("Jupiter", 380, 25, LIGHT_GRAY),
#     ("Saturn", 480, 22, LIGHT_GRAY),
#     ("Uranus", 560, 15, LIGHT_GRAY),
#     ("Neptune", 620, 14, LIGHT_GRAY),
# ]

# planet_drawables: List[Drawable] = []
# start_time = 4
# for name, orbit_radius, planet_radius, color in planet_data:
#     planet = Circle(
#         center=(960 + orbit_radius, 600),
#         radius=planet_radius,
#         stroke_style=StrokeStyle(color=WHITE),
#         fill_style=FillStyle(color=color, hachure_gap=6),
#         sketch_style=planet_sketch,
#     )

#     # Create a separate drawable for the animation, starting from off-screen
#     planet_for_anim = planet.translate(offset_x=-(1200 + orbit_radius), offset_y=0)
#     planet_for_anim.id = name.lower()
#     orbit = Circle(center=(960, 600), radius=orbit_radius, stroke_style=StrokeStyle(color=WHITE, width=1))
#     orbit.id = name.lower() + "_orbit"

#     # Draw the planet and its orbit
#     scene.add(SketchAnimation(start_time=start_time, duration=0.1), drawable=planet_for_anim)
#     scene.add(SketchAnimation(start_time=start_time, duration=1.0), drawable=orbit)  # Draw orbit at the same time

#     # Translate the planet to its final position and keep it there.
#     scene.add(
#         event=TranslateToAnimation(
#             start_time=start_time + 0.1,
#             duration=1,
#             data={"point": (960 + orbit_radius, 600)},
#         ),
#         drawable=planet_for_anim,
#     )
#     # Add the animated planet and its orbit to the list for grouping
#     planet_drawables.extend([planet_for_anim, orbit])
#     start_time += 1.0

# # Group them for future transformation
# planetary_system = DrawableGroup(elements=[sun] + planet_drawables, grouping_method="parallel")

# # --------------- Scene 3: Shrinking the Solar System ---------------
# msg = Text("But what does this mean for us?", position=(960, 540), font_size=48, stroke_style=text_style)

# scene.add(ZoomOutAnimation(start_time=13, duration=2, data={"factor": 0.2}), drawable=planetary_system)
# scene.add(FadeOutAnimation(start_time=13, duration=2), drawable=planetary_system)

# scene.add(SketchAnimation(start_time=15, duration=1), drawable=msg)
# scene.add(FadeOutAnimation(start_time=16.5, duration=1), drawable=msg)

# # --------------- Scene 4: Earth-Moon-Sun Scale ---------------
# earth = Circle(
#     center=(400, 500),
#     radius=20,
#     stroke_style=StrokeStyle(color=WHITE),
#     fill_style=FillStyle(color=BLUE, hachure_gap=8),
#     sketch_style=planet_sketch,
# )

# moon = Circle(
#     center=(400, 580),
#     radius=6,
#     stroke_style=StrokeStyle(color=WHITE),
#     fill_style=FillStyle(color=GRAY, hachure_gap=6),
#     sketch_style=planet_sketch,
# )

# moon_line = Line(start=earth.center, end=moon.center, stroke_style=StrokeStyle(color=WHITE))
# moon_label = Text("384,400 km", position=(480, 530), font_size=36, stroke_style=text_style)

# sun_far = Circle(
#     center=(1600, 500),
#     radius=200,
#     stroke_style=StrokeStyle(color=WHITE),
#     fill_style=FillStyle(color=YELLOW, hachure_gap=10),
#     sketch_style=planet_sketch,
# )
# sun_line = Line(start=earth.center, end=sun_far.center, stroke_style=StrokeStyle(color=WHITE))
# sun_label = Text("~150 million km", position=(1000, 550), font_size=36, stroke_style=text_style)

# scale_text = Text("Not to scale, but you get the idea.", position=(950, 900), font_size=36, stroke_style=text_style)

# scene.add(FadeInAnimation(start_time=18, duration=1), drawable=earth)
# scene.add(FadeInAnimation(start_time=18.5, duration=1), drawable=moon)
# scene.add(SketchAnimation(start_time=18.7, duration=1), drawable=moon_line)
# scene.add(FadeInAnimation(start_time=19, duration=1), drawable=moon_label)
# scene.add(FadeInAnimation(start_time=19.3, duration=1), drawable=sun_far)
# scene.add(FadeInAnimation(start_time=19.7, duration=1), drawable=sun_line)
# scene.add(FadeInAnimation(start_time=20, duration=1), drawable=sun_label)
# scene.add(SketchAnimation(start_time=21, duration=1), drawable=scale_text)


# # --------------- Scene 5: Cosmic Perspective ---------------
# scale_group = DrawableGroup(elements=[earth, moon, moon_line, moon_label, sun_far, sun_line, sun_label, scale_text])
# scene.add(FadeOutAnimation(start_time=22.5, duration=1), drawable=scale_group)

# stars = [
#     Circle(
#         center=(np.random.randint(50, 1870), np.random.randint(50, 1038)),
#         radius=np.random.uniform(1, 3),
#         stroke_style=StrokeStyle(color=WHITE),
#     )
#     for _ in range(100)
# ]

# text1 = Text("Humans are tiny...", position=(960, 440), font_size=42, stroke_style=text_style)
# text2 = Text("...but our curiosity is infinite.", position=(960, 520), font_size=42, stroke_style=text_style)

# for i, star in enumerate(stars):
#     scene.add(FadeInAnimation(start_time=24 + i * 0.02, duration=1), drawable=star)

# scene.add(SketchAnimation(start_time=26, duration=1), drawable=text1)
# scene.add(SketchAnimation(start_time=27, duration=1), drawable=text2)
# final_group = DrawableGroup(elements=stars + [text1, text2])
# scene.add(FadeOutAnimation(start_time=28.5, duration=1), drawable=final_group)

# --------------- Scene 6: Final Zoomed View ---------------

tiny_earth = Circle(center=(200, 900), radius=10, fill_style=FillStyle(color=BLUE), sketch_style=planet_sketch)
arrow_to_solar = Arrow(start_point=(600, 200), end_point=(200, 880), stroke_style=StrokeStyle(color=WHITE))
final_msg = Text(
    "This is the only home known to us! Let's protect it.", position=(960, 100), font_size=48, stroke_style=text_style
)

scene.add(SketchAnimation(start_time=1, duration=1), drawable=tiny_earth)
scene.add(SketchAnimation(start_time=1.5, duration=1), drawable=arrow_to_solar)
scene.add(FadeInAnimation(start_time=2, duration=1), drawable=final_msg)

# --------------- End Message ---------------
# end_text = Text("handanim", position=(960, 1000), font_size=24, stroke_style=text_style)
# scene.add(FadeInAnimation(start_time=32, duration=1.5), drawable=end_text)

# --------------- Render All ---------------
# output_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "output", "solar_system_journey.mp4")
# scene.render(output_path, max_length=5)
scene.render_snapshot(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "output", "a_plus_b_square.svg"), frame_in_seconds=3
)
