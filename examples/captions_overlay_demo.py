"""Visual demo of:
1. Built-in word-timed Captions(clip, words_per_chunk=3, highlight=RED, y=1590).
2. Camera-independent `scene.overlay` layer that keeps captions and HUD banners
   pinned on screen while `CameraAnimation` pans and zooms across the whiteboard.
"""

import os

from handanim import (
    CameraAnimation,
    Captions,
    Circle,
    Eraser,
    FillStyle,
    Math,
    Polygon,
    RoundedRectangle,
    Scene,
    Show,
    SketchAnimation,
    SketchStyle,
    StrokeStyle,
    Text,
)
from handanim.core.viewport import Viewport
from handanim.stylings.color import BLACK, BLUE, PASTEL_BLUE, PASTEL_ORANGE, RED, TEAL
from voiceanim.providers.mock_provider import MockVoiceProvider


def main() -> None:
    # 9:16 portrait video (540x960 preview mapped from 1080x1920 world space)
    viewport = Viewport(
        world_xrange=(0, 1080),
        world_yrange=(0, 1920),
        screen_width=540,
        screen_height=960,
        margin=0,
    )
    scene = Scene(
        width=540,
        height=960,
        fps=24,
        background_color=(0.99, 0.98, 0.95),
        viewport=viewport,
    )

    # 1. Generate deterministic word-timed narration clip
    provider = MockVoiceProvider()
    narration = provider.synthesize(
        "Watch how built in captions highlight each spoken word while the camera zooms into the triangle.",
        speed=1.0,
    )

    # 2. World-space geometry diagram (moves & zooms with the camera)
    sketch = SketchStyle(roughness=1.4, bowing=1.0)
    circle = Circle(
        center=(540, 820),
        radius=280,
        stroke_style=StrokeStyle(color=BLUE, width=4.0),
        sketch_style=sketch,
        fill_style=FillStyle(color=PASTEL_BLUE, opacity=0.2, hachure_gap=18),
    )
    triangle = Polygon(
        points=[(540, 540), (300, 960), (780, 960)],
        stroke_style=StrokeStyle(color=BLACK, width=4.5),
        sketch_style=sketch,
        fill_style=FillStyle(color=PASTEL_ORANGE, opacity=0.35, hachure_gap=14),
    )
    formula = Math(
        r"$a^2 + b^2 = c^2$",
        position=(380, 820),
        font_size=72,
        stroke_style=StrokeStyle(color=TEAL, width=3.5),
    )

    scene.add(SketchAnimation(start_time=0.0, duration=1.5), circle)
    scene.add(SketchAnimation(start_time=1.0, duration=1.5), triangle)
    scene.add(SketchAnimation(start_time=2.2, duration=1.2), formula)

    # Erase the formula near the end with automatic eraser sound
    eraser = Eraser(objects_to_erase=[formula], stroke_style=StrokeStyle(width=6.0))
    scene.add(SketchAnimation(start_time=4.4, duration=0.8), eraser)

    # 3. CameraAnimation: zoom in on the inscribed triangle and pan back out
    scene.add_camera(
        CameraAnimation(
            start_time=1.2,
            duration=2.0,
            data={
                "to_xrange": (220, 860),
                "to_yrange": (420, 1560),
            },
        )
    )
    scene.add_camera(
        CameraAnimation(
            start_time=3.6,
            duration=1.6,
            data={
                "to_xrange": (0, 1080),
                "to_yrange": (0, 1920),
            },
        )
    )

    # 4. Overlay layer: top HUD pill + word-by-word Captions (ignore CameraAnimation!)
    hud_box = RoundedRectangle(
        top_left=(90, 80),
        width=900,
        height=110,
        border_radius=24,
        stroke_style=StrokeStyle(color=BLUE, width=3.0),
        fill_style=FillStyle(color=PASTEL_BLUE, opacity=0.35, hachure_gap=14),
    )
    hud_title = Text(
        "Overlay HUD & Captions (Camera-Invariant)",
        position=(135, 148),
        font_size=42,
        stroke_style=StrokeStyle(color=BLACK, width=3.0),
    )
    scene.overlay.add(Show(0.0), hud_box)
    scene.overlay.add(Show(0.0), hud_title)

    captions = Captions(
        narration,
        words_per_chunk=3,
        highlight=RED,
        color=BLACK,
        y=1590,
        font_size=64,
        highlight_stroke_width=4.0,
    )
    scene.overlay.add(captions)

    output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    mp4_path = os.path.join(output_dir, "captions_overlay_demo.mp4")
    scene.render(
        mp4_path,
        max_length=max(5.5, narration.duration + 0.4),
        narration=narration,
        background_music="marimba",
        music_volume=0.18,
        music_loop=True,
        sketch_sound=True,
        eraser_sound=True,
    )
    print(f"Rendered captions & overlay demo to: {mp4_path}")


if __name__ == "__main__":
    main()
