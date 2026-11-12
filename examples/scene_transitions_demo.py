"""Visual & audio demo of SceneTransition animations: PageTurnTransition and PaperCrumpleTransition.

Renders a 3-page notebook sketch story:
- Page 1: Brainstorming a sketch diagram -> turned from the bottom-right corner (`PageTurnTransition`)
- Page 2: A "bad draft" messy equation/diagram -> crumpled into a paper ball and tossed right (`PaperCrumpleTransition`)
- Page 3: The final clean solution revealed underneath!
"""

import os

from handanim import (
    Arrow,
    Circle,
    FillStyle,
    Line,
    PageTurnTransition,
    PaperCrumpleTransition,
    PopAnimation,
    Rectangle,
    RoundedRectangle,
    Scene,
    SketchAnimation,
    StrokeStyle,
    Text,
)


def build_scene_transitions_demo() -> Scene:
    scene = Scene(
        width=960,
        height=540,
        fps=24,
        background_color=(0.985, 0.975, 0.945),  # warm sketchbook paper
        background_music="calm",
        music_volume=0.14,
        sketch_sound=True,
        transition_sound=True,
    )

    # Persistent sketchbook header in the overlay layer (stays fixed across page turns!)
    header_badge = RoundedRectangle(
        top_left=(40, 22),
        width=420,
        height=52,
        corner_radius=12,
        stroke_style=StrokeStyle(color=(0.25, 0.23, 0.20), width=2.0),
        fill_style=FillStyle(color=(0.94, 0.92, 0.86), opacity=0.92),
    )
    header_text = Text(
        "HandAnim Sketchbook — Transitions Demo",
        position=(250, 48),
        font_size=20,
        stroke_style=StrokeStyle(color=(0.18, 0.16, 0.14), width=1.6),
    )
    scene.overlay.add(SketchAnimation(start_time=0.0, duration=0.5), header_badge)
    scene.overlay.add(SketchAnimation(start_time=0.1, duration=0.5), header_text)

    # =========================================================================
    # PAGE 1: Idea 1 — Folding the paper (0.0s -> 3.0s, turned at 3.0s..4.3s)
    # =========================================================================
    p1_title = Text(
        "Page 1: Turning the Drawing Board Page",
        position=(888, 170),
        font_size=38,
        stroke_style=StrokeStyle(color=(0.15, 0.28, 0.55), width=2.4),
    )
    box_a = RoundedRectangle(
        top_left=(260, 320),
        width=360,
        height=240,
        corner_radius=20,
        stroke_style=StrokeStyle(color=(0.18, 0.35, 0.68), width=3.5),
        fill_style=FillStyle(color=(0.68, 0.82, 0.96), opacity=0.45),
    )
    box_a_label = Text(
        "Step 1: Sketch",
        position=(440, 440),
        font_size=32,
        stroke_style=StrokeStyle(color=(0.12, 0.24, 0.48), width=2.2),
    )
    arrow_ab = Arrow(
        start_point=(650, 440),
        end_point=(960, 440),
        stroke_style=StrokeStyle(color=(0.20, 0.20, 0.20), width=3.5),
    )
    box_b = RoundedRectangle(
        top_left=(990, 320),
        width=460,
        height=240,
        corner_radius=20,
        stroke_style=StrokeStyle(color=(0.18, 0.55, 0.34), width=3.5),
        fill_style=FillStyle(color=(0.72, 0.92, 0.78), opacity=0.45),
    )
    box_b_label = Text(
        "Step 2: Turn Page ->",
        position=(1220, 440),
        font_size=32,
        stroke_style=StrokeStyle(color=(0.12, 0.40, 0.22), width=2.2),
    )
    p1_note = Text(
        "Watch the corner peel & ink bleed-through on the backside!",
        position=(888, 720),
        font_size=28,
        stroke_style=StrokeStyle(color=(0.35, 0.32, 0.28), width=1.8),
    )

    scene.add(SketchAnimation(start_time=0.2, duration=0.7), p1_title)
    scene.add(SketchAnimation(start_time=0.7, duration=0.7), box_a)
    scene.add(SketchAnimation(start_time=1.0, duration=0.5), box_a_label)
    scene.add(SketchAnimation(start_time=1.3, duration=0.4), arrow_ab)
    scene.add(SketchAnimation(start_time=1.5, duration=0.7), box_b)
    scene.add(SketchAnimation(start_time=1.8, duration=0.5), box_b_label)
    scene.add(SketchAnimation(start_time=2.1, duration=0.6), p1_note)

    # Transition 1: Fold Page 1 diagonally from bottom-right corner to top-left (3.0s -> 4.3s)
    scene.add(
        PageTurnTransition(
            start_time=3.0,
            duration=1.3,
            direction="bottom_right",
            bleed_through=0.20,
        )
    )

    # =========================================================================
    # PAGE 2: A "Wrong Draft" that gets crumpled up (3.4s -> 6.8s, crumpled 6.8s..8.2s)
    # =========================================================================
    p2_title = Text(
        "Page 2: Wait... This Draft Is Wrong!",
        position=(888, 175),
        font_size=38,
        stroke_style=StrokeStyle(color=(0.72, 0.20, 0.18), width=2.4),
    )
    bad_circle = Circle(
        center=(620, 470),
        radius=150,
        stroke_style=StrokeStyle(color=(0.78, 0.25, 0.20), width=3.5),
        fill_style=FillStyle(color=(0.98, 0.76, 0.72), opacity=0.45),
    )
    bad_rect = Rectangle(
        top_left=(920, 330),
        width=420,
        height=280,
        stroke_style=StrokeStyle(color=(0.75, 0.35, 0.15), width=3.5),
        fill_style=FillStyle(color=(0.98, 0.85, 0.68), opacity=0.45),
    )
    bad_text = Text(
        "2 + 2 = 5 ???",
        position=(1130, 470),
        font_size=38,
        stroke_style=StrokeStyle(color=(0.65, 0.15, 0.15), width=2.5),
    )
    cross_1 = Line(
        start=(450, 310),
        end=(1380, 640),
        stroke_style=StrokeStyle(color=(0.82, 0.12, 0.12), width=5.0),
    )
    cross_2 = Line(
        start=(1380, 310),
        end=(450, 640),
        stroke_style=StrokeStyle(color=(0.82, 0.12, 0.12), width=5.0),
    )
    p2_note = Text(
        "Let's crumple this sheet and toss it aside!",
        position=(888, 740),
        font_size=30,
        stroke_style=StrokeStyle(color=(0.55, 0.20, 0.18), width=2.0),
    )

    scene.add(SketchAnimation(start_time=3.5, duration=0.7), p2_title)
    scene.add(SketchAnimation(start_time=4.1, duration=0.7), bad_circle)
    scene.add(SketchAnimation(start_time=4.5, duration=0.7), bad_rect)
    scene.add(SketchAnimation(start_time=4.9, duration=0.5), bad_text)
    scene.add(SketchAnimation(start_time=5.5, duration=0.35), cross_1)
    scene.add(SketchAnimation(start_time=5.8, duration=0.35), cross_2)
    scene.add(SketchAnimation(start_time=6.1, duration=0.5), p2_note)

    # Transition 2: Crumple Page 2 into a paper ball and toss it to the right (6.8s -> 8.2s)
    scene.add(
        PaperCrumpleTransition(
            start_time=6.8,
            duration=1.4,
            direction="right",
        )
    )

    # =========================================================================
    # PAGE 3: Fresh Sheet Underneath (7.2s -> 10.2s)
    # =========================================================================
    p3_title = Text(
        "Page 3: Fresh Sheet — Clean Solution!",
        position=(888, 190),
        font_size=40,
        stroke_style=StrokeStyle(color=(0.14, 0.48, 0.28), width=2.5),
    )
    final_card = RoundedRectangle(
        top_left=(420, 310),
        width=936,
        height=340,
        corner_radius=26,
        stroke_style=StrokeStyle(color=(0.16, 0.52, 0.32), width=4.0),
        fill_style=FillStyle(color=(0.76, 0.94, 0.82), opacity=0.5),
    )
    final_eq = Text(
        "PageTurnTransition + PaperCrumpleTransition",
        position=(888, 445),
        font_size=34,
        stroke_style=StrokeStyle(color=(0.10, 0.35, 0.20), width=2.3),
    )
    final_sub = Text(
        "Zero-boilerplate multi-page scenes with procedural sound!",
        position=(888, 540),
        font_size=28,
        stroke_style=StrokeStyle(color=(0.22, 0.32, 0.26), width=1.9),
    )

    scene.add(SketchAnimation(start_time=7.3, duration=0.7), p3_title)
    scene.add(PopAnimation(start_time=7.8, duration=0.6), final_card)
    scene.add(SketchAnimation(start_time=8.2, duration=0.8), final_eq)
    scene.add(SketchAnimation(start_time=8.8, duration=0.7), final_sub)

    return scene


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    output_mp4 = os.path.join(out_dir, "scene_transitions_demo.mp4")
    demo_scene = build_scene_transitions_demo()
    demo_scene.render(output_mp4, max_length=10.3)
    print(f"Rendered scene transitions demo to: {output_mp4}")

