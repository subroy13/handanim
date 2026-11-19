"""Unified gallery builder for handanim documentation tutorials.

Generates the videos (.mp4) and animations (.gif) showcased in the
Sphinx documentation gallery (`docs/source/_static/gallery/`).

Usage:
    poetry run python docs/source/gallery/build_gallery.py --list
    poetry run python docs/source/gallery/build_gallery.py --only sketch_sound_control
    poetry run python docs/source/gallery/build_gallery.py --all
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

import numpy as np

from handanim import (
    Arrow,
    CameraAnimation,
    Captions,
    CharacterRig,
    Circle,
    CompositeAnimationEvent,
    Curve,
    DrawableGroup,
    Eraser,
    FadeInAnimation,
    FadeOutAnimation,
    FillStyle,
    Flowchart,
    Line,
    Math,
    NGon,
    PageTurnTransition,
    PaperCrumpleTransition,
    Polygon,
    PopAnimation,
    Pose,
    PoseAnimation,
    Rectangle,
    RigNode,
    RoundedRectangle,
    Scene,
    Show,
    SketchAnimation,
    SketchStyle,
    Square,
    StrokeStyle,
    Swap,
    Table,
    Text,
    TranslateToAnimation,
    TwoJointLimb,
    VariantSlot,
    VectorSVG,
    ZoomOutAnimation,
)
from handanim.core.viewport import Viewport
from handanim.stylings.color import (
    BLACK,
    BLUE,
    DARK_GRAY,
    ERASER_HINT_COLOR,
    GRAY,
    GREEN,
    LIGHT_GRAY,
    NAVY,
    ORANGE,
    PASTEL_BLUE,
    PASTEL_GREEN,
    PASTEL_ORANGE,
    PASTEL_RED,
    PASTEL_YELLOW,
    RED,
    TEAL,
    WHITE,
    YELLOW,
)
from voiceanim import VoiceTimelineSync
from voiceanim.providers.mock_provider import MockVoiceProvider

REPO_ROOT = Path(__file__).resolve().parents[3]
ASSETS_DIR = REPO_ROOT / "assets"
GALLERY_OUT_DIR = REPO_ROOT / "docs" / "source" / "_static" / "gallery"


# ============================================================================
# Theme 1: Mathematical Proofs & Geometry
# ============================================================================


def render_pythagoras(out_dir: Path = GALLERY_OUT_DIR) -> str:
    """Tutorial 1.1: Visual introduction to the Pythagorean Theorem."""
    scene = Scene(width=1920, height=1088)
    title_text = Text(
        text="Pythagoras' Theorem",
        position=(300, 500),
        font_size=192,
        stroke_style=StrokeStyle(color=BLUE, width=2),
        glow_dot_hint={"color": BLUE, "radius": 5},
    )
    scene.add(SketchAnimation(duration=3), drawable=title_text)

    eraser = Eraser(
        objects_to_erase=[title_text],
        drawable_cache=scene.drawable_cache,
        glow_dot_hint={"color": ERASER_HINT_COLOR, "radius": 10},
    )
    scene.add(SketchAnimation(start_time=3.5, duration=1.5), drawable=eraser)

    right_triangle = Polygon(
        points=[(500, 500), (500, 700), (900, 700)],
        stroke_style=StrokeStyle(color=BLACK, width=2),
        sketch_style=SketchStyle(roughness=5),
        fill_style=FillStyle(color=RED, hachure_gap=10),
    )
    scene.add(SketchAnimation(start_time=6, duration=3), drawable=right_triangle)

    line_labels = [("a", (450, 600)), ("b", (700, 800)), ("c", (700, 550))]
    label_group = DrawableGroup(
        elements=[Text(text=label, position=pos, font_size=96) for label, pos in line_labels]
    )
    scene.add(SketchAnimation(start_time=8, duration=2), drawable=label_group)

    pyth_form = Math(
        tex_expression=r"$a^2 + b^2 = c^2$",
        position=(900, 300),
        font_size=128,
        stroke_style=StrokeStyle(color=BLUE, width=2),
        font_name="feasibly",
    )
    scene.add(SketchAnimation(start_time=10, duration=3), drawable=pyth_form)

    out_path = str(out_dir / "pythagoras.gif")
    return scene.render(out_path, max_length=15)


def render_a_plus_b_square(out_dir: Path = GALLERY_OUT_DIR) -> str:
    """Tutorial 1.2: Geometric & algebraic proof of (a + b)^2 = a^2 + 2ab + b^2."""
    scene = Scene(width=1920, height=1088)
    font_name = "feasibly"
    val_a, val_b = 100, 200
    a_plus_b = val_a + val_b
    sq_top_left = (300, 500)

    title_text = Math(
        tex_expression=r"$(a + b)^2 = ?$",
        position=sq_top_left,
        font_size=192,
        stroke_style=StrokeStyle(color=BLUE, width=2),
        glow_dot_hint={"color": BLUE, "radius": 5},
        font_name=font_name,
    )
    scene.add(
        CompositeAnimationEvent(
            events=[SketchAnimation(duration=1), FadeOutAnimation(start_time=1, duration=2)]
        ),
        drawable=title_text,
    )

    a_plus_b_sq = Square(
        top_left=sq_top_left,
        side_length=a_plus_b,
        stroke_style=StrokeStyle(color=BLACK, width=2),
        fill_style=FillStyle(color=BLUE, hachure_gap=10),
        sketch_style=SketchStyle(roughness=3),
    )
    scene.add(SketchAnimation(start_time=3.5, duration=3), drawable=a_plus_b_sq)

    a_plus_b_sq_label = Math(
        tex_expression=r"$(a + b)^2 = a^2 + 2ab + b^2$",
        position=(520, 200),
        font_size=96,
        stroke_style=StrokeStyle(color=BLACK, width=2),
        font_name=font_name,
    )
    scene.add(FadeInAnimation(start_time=6.5, duration=1.5), drawable=a_plus_b_sq_label)

    vert_line = Line(
        start=(sq_top_left[0] + val_a, sq_top_left[1]),
        end=(sq_top_left[0] + val_a, sq_top_left[1] + a_plus_b),
        stroke_style=StrokeStyle(color=BLACK, width=2),
    )
    horiz_line = Line(
        start=(sq_top_left[0], sq_top_left[1] + val_a),
        end=(sq_top_left[0] + a_plus_b, sq_top_left[1] + val_a),
        stroke_style=StrokeStyle(color=BLACK, width=2),
    )
    scene.add(SketchAnimation(start_time=7, duration=1), drawable=DrawableGroup(elements=[vert_line, horiz_line]))

    a_sq = Square(
        top_left=sq_top_left,
        side_length=val_a,
        stroke_style=StrokeStyle(color=BLACK, width=2),
        fill_style=FillStyle(color=RED, hachure_gap=10, hachure_angle=135),
        sketch_style=SketchStyle(roughness=3),
    )
    b_sq = Square(
        top_left=(sq_top_left[0] + val_a, sq_top_left[1] + val_a),
        side_length=val_b,
        stroke_style=StrokeStyle(color=BLACK, width=2),
        fill_style=FillStyle(color=RED, hachure_gap=10, hachure_angle=135),
        sketch_style=SketchStyle(roughness=3),
    )
    rect1 = Rectangle(
        top_left=(sq_top_left[0] + val_a, sq_top_left[1]),
        width=val_b,
        height=val_a,
        stroke_style=StrokeStyle(color=BLACK, width=2),
        fill_style=FillStyle(color=ORANGE, hachure_gap=10, hachure_angle=135),
        sketch_style=SketchStyle(roughness=3),
    )
    rect2 = Rectangle(
        top_left=(sq_top_left[0], sq_top_left[1] + val_a),
        width=val_a,
        height=val_b,
        stroke_style=StrokeStyle(color=BLACK, width=2),
        fill_style=FillStyle(color=ORANGE, hachure_gap=10, hachure_angle=135),
        sketch_style=SketchStyle(roughness=3),
    )
    scene.add(SketchAnimation(start_time=8.2, duration=1.2), drawable=a_sq)
    scene.add(SketchAnimation(start_time=9.5, duration=1.2), drawable=b_sq)
    scene.add(SketchAnimation(start_time=10.8, duration=1.2), drawable=rect1)
    scene.add(SketchAnimation(start_time=12.0, duration=1.2), drawable=rect2)

    out_path = str(out_dir / "a_plus_b_square.gif")
    return scene.render(out_path, max_length=14)


def render_distributive_property(out_dir: Path = GALLERY_OUT_DIR) -> str:
    """Tutorial 1.3: Visual proof of the Distributive Property a(b + c) = ab + ac."""
    scene = Scene(width=1920, height=1080)
    svg_path = ASSETS_DIR / "professor.svg"
    operator = VectorSVG.from_svg_file(
        str(svg_path),
        position=(1500, 700),
        glow_dot_hint={"color": BLUE, "radius": 5},
    ).scale(0.5, 0.5)
    scene.add(SketchAnimation(start_time=0.5, duration=2), drawable=operator)

    title_text = Text(
        text="Distributive Property",
        position=(500, 120),
        font_size=120,
        stroke_style=StrokeStyle(color=BLUE, width=2),
        glow_dot_hint={"color": BLUE, "radius": 5},
    )
    scene.add(SketchAnimation(start_time=0.5, duration=2), drawable=title_text)

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
    scene.add(SketchAnimation(start_time=2.5, duration=1.5), drawable=rect_ab)
    scene.add(SketchAnimation(start_time=3.0, duration=1.5), drawable=rect_ac)

    label_a = Math(r"$a$", position=(310, 525), font_size=70)
    label_b = Math(r"$b$", position=(470, 400), font_size=70)
    label_c = Math(r"$c$", position=(1350, 400), font_size=70)
    scene.add(FadeInAnimation(start_time=4.0, duration=0.5), drawable=label_a)
    scene.add(FadeInAnimation(start_time=4.2, duration=0.5), drawable=label_b)
    scene.add(FadeInAnimation(start_time=4.4, duration=0.5), drawable=label_c)

    scene.add(TranslateToAnimation(start_time=5.5, duration=1, data={"point": (1550, 600)}), drawable=operator)
    scene.add(TranslateToAnimation(start_time=7.0, duration=2, data={"point": (750, 575)}), drawable=rect_ac)
    scene.add(TranslateToAnimation(start_time=7.0, duration=2, data={"point": (750, 450)}), drawable=label_c)
    scene.add(TranslateToAnimation(start_time=7.0, duration=2, data={"point": (1000, 600)}), drawable=operator)

    final_formula = Math(
        tex_expression=r"$a(b + c) = ab + ac$",
        position=(400, 200),
        font_size=110,
        stroke_style=StrokeStyle(color=BLACK, width=3),
        font_name="feasibly",
    )
    scene.add(SketchAnimation(start_time=9.5, duration=2), drawable=final_formula)

    out_path = str(out_dir / "distributive_property.gif")
    return scene.render(out_path, max_length=12)


def render_hershey_math(out_dir: Path = GALLERY_OUT_DIR) -> str:
    """Tutorial 1.4: Single-stroke Hershey math and calculus expressions."""
    scene = Scene(width=1264, height=960)
    expressions = [
        (r"$x = \frac{-\alpha \pm \sqrt{\beta^2 - 4\gamma}}{2}$", BLUE),
        (r"$a \leq b, \quad c \geq d, \quad e \neq f, \quad g \approx h$", GREEN),
        (r"$\lim_{x \rightarrow \infty} f(x) = L$", BLACK),
        (r"$\forall x \in A, \quad \exists y \in B : x \leq y$", RED),
        (r"$\sum_{k=1}^{n} k^2 = \int_{0}^{n} x \, dx$", BLUE),
        (r"$e^{i\pi} + 1 = 0$", GREEN),
    ]
    for idx, (expr, color) in enumerate(expressions):
        math_obj = Math(
            tex_expression=expr,
            position=(80, 120 + idx * 145),
            font_size=44,
            font_name="hershey_mathlow",
            stroke_style=StrokeStyle(color=color, width=2),
        )
        scene.add(SketchAnimation(start_time=idx * 1.5, duration=1.5), math_obj)

    out_path = str(out_dir / "hershey_equation.mp4")
    return scene.render(out_path)


# ============================================================================
# Theme 2: Flowcharts & Tables
# ============================================================================


def render_ml_workflow(out_dir: Path = GALLERY_OUT_DIR) -> str:
    """Tutorial 2.1: Machine Learning Pipeline Flowchart & Model Comparison Table."""
    scene = Scene(width=1920, height=1080)
    sketchy = SketchStyle(roughness=2, bowing=1)
    light_sketchy = SketchStyle(roughness=1, bowing=1)
    process_stroke = StrokeStyle(color=NAVY, width=2)
    diamond_stroke = StrokeStyle(color=(0.5, 0.1, 0.1), width=2)
    conn_stroke = StrokeStyle(color=DARK_GRAY, width=1)

    title = Text(
        text="Machine Learning Workflow",
        position=(889, 52),
        font_size=78,
        stroke_style=StrokeStyle(color=NAVY, width=2),
        sketch_style=light_sketchy,
    )
    label_pipeline = Text(
        text="Training Pipeline",
        position=(340, 100),
        font_size=46,
        stroke_style=StrokeStyle(color=NAVY, width=1),
        sketch_style=light_sketchy,
    )
    label_results = Text(
        text="Model Comparison",
        position=(1310, 100),
        font_size=46,
        stroke_style=StrokeStyle(color=NAVY, width=1),
        sketch_style=light_sketchy,
    )

    fc = Flowchart.from_dict(
        {
            "nodes": [
                {
                    "id": "collect",
                    "label": "Collect Data",
                    "position": [340, 155],
                    "size": [190, 52],
                    "stroke_style": process_stroke,
                    "sketch_style": sketchy,
                    "fill_style": FillStyle(color=PASTEL_BLUE, hachure_gap=8),
                },
                {
                    "id": "preprocess",
                    "label": "Preprocess",
                    "position": [340, 285],
                    "size": [190, 52],
                    "stroke_style": process_stroke,
                    "sketch_style": sketchy,
                    "fill_style": FillStyle(color=PASTEL_BLUE, hachure_gap=8),
                },
                {
                    "id": "train",
                    "label": "Train Model",
                    "position": [340, 420],
                    "size": [190, 52],
                    "stroke_style": process_stroke,
                    "sketch_style": sketchy,
                    "fill_style": FillStyle(color=PASTEL_BLUE, hachure_gap=8),
                },
                {
                    "id": "evaluate",
                    "type": "diamond",
                    "label": "Accuracy OK?",
                    "position": [340, 560],
                    "size": [215, 82],
                    "stroke_style": diamond_stroke,
                    "sketch_style": sketchy,
                    "fill_style": FillStyle(color=PASTEL_YELLOW, hachure_gap=8),
                },
                {
                    "id": "tune",
                    "label": "Tune Params",
                    "position": [630, 560],
                    "size": [180, 52],
                    "stroke_style": process_stroke,
                    "sketch_style": sketchy,
                    "fill_style": FillStyle(color=PASTEL_RED, hachure_gap=8),
                },
                {
                    "id": "deploy",
                    "label": "Deploy Model",
                    "position": [340, 700],
                    "size": [190, 52],
                    "stroke_style": process_stroke,
                    "sketch_style": sketchy,
                    "fill_style": FillStyle(color=PASTEL_GREEN, hachure_gap=8),
                },
            ],
            "edges": [
                {"from": "collect", "to": "preprocess", "stroke_style": conn_stroke, "sketch_style": sketchy},
                {"from": "preprocess", "to": "train", "stroke_style": conn_stroke, "sketch_style": sketchy},
                {"from": "train", "to": "evaluate", "stroke_style": conn_stroke, "sketch_style": sketchy},
                {
                    "from": "evaluate",
                    "to": "tune",
                    "from_side": "right",
                    "to_side": "left",
                    "label": "No",
                    "stroke_style": conn_stroke,
                    "sketch_style": sketchy,
                },
                {
                    "from": "evaluate",
                    "to": "deploy",
                    "from_side": "bottom",
                    "to_side": "top",
                    "label": "Yes",
                    "stroke_style": conn_stroke,
                    "sketch_style": sketchy,
                },
            ],
        }
    )

    table = Table(
        top_left=(870, 148),
        n_rows=5,
        n_cols=4,
        cell_width=218,
        cell_height=65,
        headers=["Model", "Accuracy", "F1 Score", "Train Time"],
        data=[
            ["Baseline", "72.3 %", "0.71", " 2 min"],
            ["Random Forest", "85.1 %", "0.84", " 8 min"],
            ["Gradient Boost", "89.4 %", "0.88", "15 min"],
            ["Neural Net", "94.2 %", "0.93", "45 min"],
        ],
        cell_font_size=26,
        header_font_size=30,
        stroke_style=StrokeStyle(color=(0.2, 0.2, 0.4), width=1),
        sketch_style=sketchy,
        header_stroke_style=StrokeStyle(color=NAVY, width=2),
        header_fill_style=FillStyle(color=PASTEL_BLUE, hachure_gap=7),
    )

    scene.add(FadeInAnimation(start_time=0.0, duration=1.0), title)
    scene.add(FadeInAnimation(start_time=1.0, duration=0.8), label_pipeline)
    scene.add(FadeInAnimation(start_time=1.0, duration=0.8), label_results)

    node_step = 3.2 / len(fc.nodes)
    for i, node in enumerate(fc.nodes):
        scene.add(SketchAnimation(start_time=1.8 + i * node_step, duration=node_step), node)

    conn_step = 1.5 / len(fc.connectors)
    for i, connector in enumerate(fc.connectors):
        scene.add(SketchAnimation(start_time=5.0 + i * conn_step, duration=conn_step), connector)

    header_event, header_drawable = table.animate_by_row(SketchAnimation, start_time=5.8, total_duration=1.0).pairs[0]
    scene.add(header_event, header_drawable)

    data_reveal = table.animate_by_row(SketchAnimation, start_time=6.8, total_duration=4.0)
    for event, drawable in data_reveal.pairs[1:]:
        scene.add(event, drawable)

    out_path = str(out_dir / "ml_workflow_demo.gif")
    return scene.render(out_path, max_length=12)


# ============================================================================
# Theme 3: 2D Character Rigging, Inverse Kinematics & Poses
# ============================================================================


def _build_character_rig(origin_x: float = 380.0, origin_y: float = 260.0) -> CharacterRig:
    sketch = SketchStyle(roughness=1.2, bowing=1.0)
    pen_black = StrokeStyle(color=BLACK, width=3.5)
    pen_blue = StrokeStyle(color=BLUE, width=3.5)
    pen_red = StrokeStyle(color=RED, width=3.5)

    hx, hy = origin_x, origin_y - 55.0
    head_circle = Circle(
        center=(hx, hy),
        radius=42,
        stroke_style=pen_black,
        sketch_style=sketch,
        fill_style=FillStyle(color=PASTEL_BLUE, opacity=0.25, hachure_gap=10),
    )

    eyes_open = RigNode(
        name="eyes_open_group",
        drawables=[
            Circle(center=(hx - 14, hy - 8), radius=4.5, stroke_style=pen_black, fill_style=FillStyle(color=BLACK)),
            Circle(center=(hx + 14, hy - 8), radius=4.5, stroke_style=pen_black, fill_style=FillStyle(color=BLACK)),
        ],
    )
    eyes_blink = RigNode(
        name="eyes_blink_group",
        drawables=[
            Line((hx - 20, hy - 8), (hx - 8, hy - 8), stroke_style=pen_black, sketch_style=sketch),
            Line((hx + 8, hy - 8), (hx + 20, hy - 8), stroke_style=pen_black, sketch_style=sketch),
        ],
    )
    eyes_slot = VariantSlot(
        name="eyes",
        variants={"open": eyes_open, "blink": eyes_blink},
        default="open",
        pivot=(hx, hy - 8),
    )
    eyes_slot.set_schedule([(0.0, "open"), (2.6, "blink"), (2.78, "open")])

    mouth_neutral = Line((hx - 12, hy + 14), (hx + 12, hy + 14), stroke_style=pen_black, sketch_style=sketch)
    mouth_smile = Curve(
        points=[(hx - 15, hy + 11), (hx, hy + 22), (hx + 15, hy + 11)],
        stroke_style=pen_black,
        sketch_style=sketch,
    )
    mouth_open = Circle(
        center=(hx, hy + 15),
        radius=8,
        stroke_style=pen_red,
        sketch_style=sketch,
        fill_style=FillStyle(color=RED, opacity=0.35, hachure_gap=6),
    )
    mouth_slot = VariantSlot(
        name="mouth",
        variants={"neutral": mouth_neutral, "smile": mouth_smile, "open": mouth_open},
        default="neutral",
        pivot=(hx, hy + 14),
    )

    head_node = RigNode(
        name="head",
        pivot=(origin_x, origin_y - 12.0),
        drawables=[head_circle],
        children=[eyes_slot, mouth_slot],
    )

    l_shoulder = (origin_x - 10.0, origin_y)
    l_elbow = (origin_x - 55.0, origin_y + 45.0)
    l_hand = (origin_x - 80.0, origin_y + 95.0)
    forearm_l = RigNode(
        name="forearm_l",
        pivot=l_elbow,
        drawables=[
            Line(l_elbow, l_hand, stroke_style=pen_black, sketch_style=sketch),
            Circle(center=l_hand, radius=6, stroke_style=pen_black, sketch_style=sketch),
        ],
    )
    upper_arm_l = RigNode(
        name="upper_arm_l",
        pivot=l_shoulder,
        drawables=[Line(l_shoulder, l_elbow, stroke_style=pen_black, sketch_style=sketch)],
        children=[forearm_l],
    )

    r_shoulder = (origin_x + 10.0, origin_y)
    r_elbow = (origin_x + 85.0, origin_y)
    r_hand = (origin_x + 155.0, origin_y)
    forearm_r = RigNode(
        name="forearm_r",
        pivot=r_elbow,
        drawables=[
            Line(r_elbow, r_hand, stroke_style=pen_blue, sketch_style=sketch),
            Circle(
                center=r_hand,
                radius=8,
                stroke_style=pen_red,
                sketch_style=sketch,
                fill_style=FillStyle(color=RED, opacity=0.5, hachure_gap=5),
            ),
        ],
    )
    upper_arm_r = RigNode(
        name="upper_arm_r",
        pivot=r_shoulder,
        drawables=[
            Line(r_shoulder, r_elbow, stroke_style=pen_blue, sketch_style=sketch),
            Circle(center=r_elbow, radius=5, stroke_style=pen_blue, sketch_style=sketch),
        ],
        children=[forearm_r],
    )

    hip = (origin_x, origin_y + 130.0)
    torso_node = RigNode(
        name="torso",
        pivot=hip,
        drawables=[
            Line((origin_x, origin_y - 12.0), hip, stroke_style=pen_black, sketch_style=sketch),
            Line(hip, (origin_x - 45.0, origin_y + 240.0), stroke_style=pen_black, sketch_style=sketch),
            Line(hip, (origin_x + 45.0, origin_y + 240.0), stroke_style=pen_black, sketch_style=sketch),
        ],
        children=[head_node, upper_arm_l, upper_arm_r],
    )
    right_arm_limb = TwoJointLimb(
        name="right_arm",
        upper_node="upper_arm_r",
        lower_node="forearm_r",
        effector_pos=r_hand,
        bend_direction=1,
    )
    return CharacterRig(root=torso_node, limbs=[right_arm_limb])


def render_character_rig(out_dir: Path = GALLERY_OUT_DIR) -> str:
    """Tutorial 3.1: Character Rig, 2-Joint IK & Show/Hide/Swap."""
    sketch = SketchStyle(roughness=1.2, bowing=1.0)
    scene = Scene(width=960, height=540, fps=24, background_color=(0.99, 0.98, 0.95))
    scene.set_viewport_to_identity()

    hook_title = Text(
        "Character Rig, 2-Joint IK & Show/Hide/Swap",
        position=(60, 48),
        font_size=36,
        stroke_style=StrokeStyle(color=BLUE, width=2.5),
    )
    scene.add(Show(0.0), hook_title)

    step1_badge = Text(
        "Step 1: Parent-Child Wave + Blink & Mouth Variants",
        position=(60, 95),
        font_size=26,
        stroke_style=StrokeStyle(color=TEAL, width=2.0),
    )
    step2_badge = Text(
        "Step 2: 2-Joint IK Limb Reaches Moving Targets",
        position=(60, 95),
        font_size=26,
        stroke_style=StrokeStyle(color=RED, width=2.0),
    )
    step3_badge = Text(
        "Step 3: FadeOut -> FadeIn Restores Opacity",
        position=(60, 95),
        font_size=26,
        stroke_style=StrokeStyle(color=BLUE, width=2.0),
    )
    scene.add(Show(0.0), step1_badge)
    scene.add(Swap(step1_badge, step2_badge, start_time=2.0))
    scene.add(Swap(step2_badge, step3_badge, start_time=4.0))

    board_card = RoundedRectangle(
        top_left=(600, 160),
        width=290,
        height=260,
        border_radius=24,
        stroke_style=StrokeStyle(color=BLACK, width=3.0, opacity=0.85),
        sketch_style=sketch,
        fill_style=FillStyle(color=PASTEL_GREEN, opacity=0.35, hachure_gap=12),
    )
    target_high = Circle(
        center=(640, 220),
        radius=16,
        stroke_style=StrokeStyle(color=RED, width=3.0),
        sketch_style=sketch,
        fill_style=FillStyle(color=ORANGE, opacity=0.6, hachure_gap=6),
    )
    target_low = Circle(
        center=(630, 360),
        radius=16,
        stroke_style=StrokeStyle(color=BLUE, width=3.0),
        sketch_style=sketch,
        fill_style=FillStyle(color=PASTEL_BLUE, opacity=0.6, hachure_gap=6),
    )
    scene.add(SketchAnimation(start_time=0.0, duration=0.8), board_card)
    scene.add(Show(1.8), target_high)
    scene.add(Swap(target_high, target_low, start_time=3.0))
    scene.add(FadeOutAnimation(start_time=4.0, duration=0.5), board_card)
    scene.add(FadeInAnimation(start_time=4.7, duration=0.6), board_card)
    scene.add(Show(4.7), target_high)

    rig = _build_character_rig(origin_x=380.0, origin_y=260.0)
    scene.add(Show(0.0), rig)

    pose_rest = Pose(angles={"upper_arm_r": 35.0, "forearm_r": 20.0, "head": 0.0}, variants={"mouth": "neutral"})
    pose_wave_up = Pose(angles={"upper_arm_r": -55.0, "forearm_r": -65.0, "head": -6.0}, variants={"mouth": "smile"})
    pose_wave_down = Pose(angles={"upper_arm_r": -25.0, "forearm_r": -20.0, "head": 5.0}, variants={"mouth": "open"})
    pose_reach_high = Pose(
        angles={"torso": 6.0, "head": 4.0},
        ik_targets={"right_arm": (640.0, 220.0)},
        variants={"mouth": "open"},
    )
    pose_reach_low = Pose(
        angles={"torso": 10.0, "head": 8.0},
        ik_targets={"right_arm": (630.0, 360.0)},
        variants={"mouth": "smile"},
    )
    pose_celebrate = Pose(
        angles={"torso": 0.0, "upper_arm_l": 70.0, "forearm_l": 35.0},
        ik_targets={"right_arm": (640.0, 220.0)},
        variants={"mouth": "smile"},
    )

    scene.add(
        PoseAnimation.from_keyframes(
            rig=rig,
            keyframes=[
                (0.0, pose_rest),
                (0.7, pose_wave_up),
                (1.3, pose_wave_down),
                (1.9, pose_wave_up),
                (2.4, pose_reach_high),
                (3.3, pose_reach_low),
                (4.3, pose_rest),
                (5.0, pose_celebrate),
                (5.8, pose_celebrate),
            ],
        ),
        rig,
    )

    out_path = str(out_dir / "character_rig_demo.mp4")
    return scene.render(out_path, max_length=6.0)


# ============================================================================
# Theme 4: Multi-Page Sketchbook & Scene Transitions
# ============================================================================


def render_scene_transitions(out_dir: Path = GALLERY_OUT_DIR) -> str:
    """Tutorial 4.1: Multi-page notebook transitions (PageTurnTransition & PaperCrumpleTransition)."""
    scene = Scene(
        width=960,
        height=540,
        fps=24,
        background_color=(0.985, 0.975, 0.945),
        background_music="calm",
        music_volume=0.14,
        sketch_sound=True,
        sketch_sound_volume=0.22,
        transition_sound=True,
    )

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
    scene.overlay.add(SketchAnimation(start_time=0.0, duration=0.5, sound=False), header_badge)
    scene.overlay.add(SketchAnimation(start_time=0.1, duration=0.5, sound=False), header_text)

    # Page 1
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

    scene.add(
        PageTurnTransition(
            start_time=3.0,
            duration=1.3,
            direction="bottom_right",
            bleed_through=0.20,
        )
    )

    # Page 2
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
    cross_1 = Line(start=(450, 310), end=(1380, 640), stroke_style=StrokeStyle(color=(0.82, 0.12, 0.12), width=5.0))
    cross_2 = Line(start=(1380, 310), end=(450, 640), stroke_style=StrokeStyle(color=(0.82, 0.12, 0.12), width=5.0))
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

    scene.add(PaperCrumpleTransition(start_time=6.8, duration=1.4, direction="right"))

    # Page 3
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

    out_path = str(out_dir / "scene_transitions_demo.mp4")
    return scene.render(out_path, max_length=10.3)


# ============================================================================
# Theme 5: Voice Narration, Captions, Camera & Sketch Sound Control
# ============================================================================


def render_captions_overlay(out_dir: Path = GALLERY_OUT_DIR) -> str:
    """Tutorial 5.2: Built-in word-timed Captions, CameraAnimation & Overlay HUD."""
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

    provider = MockVoiceProvider()
    narration = provider.synthesize(
        "Watch how built in captions highlight each spoken word while the camera zooms into the triangle.",
        speed=1.0,
    )

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

    eraser = Eraser(objects_to_erase=[formula], stroke_style=StrokeStyle(width=6.0))
    scene.add(SketchAnimation(start_time=4.4, duration=0.8), eraser)

    scene.add_camera(
        CameraAnimation(
            start_time=1.2,
            duration=2.0,
            data={"to_xrange": (220, 860), "to_yrange": (420, 1560)},
        )
    )
    scene.add_camera(
        CameraAnimation(
            start_time=3.6,
            duration=1.6,
            data={"to_xrange": (0, 1080), "to_yrange": (0, 1920)},
        )
    )

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

    out_path = str(out_dir / "captions_overlay_demo.mp4")
    return scene.render(
        out_path,
        max_length=max(5.5, narration.duration + 0.4),
        narration=narration,
        background_music="marimba",
        music_volume=0.18,
        music_loop=True,
        sketch_sound=True,
        sketch_sound_volume=0.20,
        eraser_sound=True,
    )


def render_sketch_sound_control(out_dir: Path = GALLERY_OUT_DIR) -> str:
    """Tutorial 5.3: Turning sketch sound on/off and adjusting volume per-animation & globally."""
    scene = Scene(
        width=960,
        height=540,
        fps=24,
        background_color=(0.99, 0.98, 0.95),
        sketch_sound=True,
        sketch_sound_volume=0.22,
        sketch_sound_style="chalk",
    )
    scene.set_viewport_to_identity()

    title = Text(
        "Sketch Sound Control: On / Off & Volume Tuning",
        position=(480, 62),
        font_size=34,
        stroke_style=StrokeStyle(color=NAVY, width=2.4),
    )
    # 1. Title sketches SILENTLY (`sound=False`) even though scene.sketch_sound is True
    scene.add(SketchAnimation(start_time=0.0, duration=0.8, sound=False), title)

    # Card 1: Silent Sketch (`sound=False`)
    card_off = RoundedRectangle(
        top_left=(55, 130),
        width=260,
        height=320,
        corner_radius=18,
        stroke_style=StrokeStyle(color=GRAY, width=3.0),
        fill_style=FillStyle(color=LIGHT_GRAY, opacity=0.25, hachure_gap=12),
    )
    label_off = Text("1. Muted (sound=False)", position=(185, 175), font_size=22, stroke_style=StrokeStyle(color=BLACK, width=2.0))
    circle_off = Circle(center=(185, 295), radius=70, stroke_style=StrokeStyle(color=GRAY, width=3.5))
    scene.add(SketchAnimation(start_time=0.9, duration=1.1, sound=False), card_off)
    scene.add(SketchAnimation(start_time=1.0, duration=0.5, sound=False), label_off)
    scene.add(SketchAnimation(start_time=1.2, duration=1.0, sound=False), circle_off)

    # Card 2: Soft Pen Sound (`sound_volume=0.12, sound_style="pen"`)
    card_soft = RoundedRectangle(
        top_left=(350, 130),
        width=260,
        height=320,
        corner_radius=18,
        stroke_style=StrokeStyle(color=TEAL, width=3.0),
        fill_style=FillStyle(color=PASTEL_GREEN, opacity=0.35, hachure_gap=12),
    )
    label_soft = Text("2. Soft Pen (vol=0.12)", position=(480, 175), font_size=22, stroke_style=StrokeStyle(color=TEAL, width=2.0))
    circle_soft = Circle(center=(480, 295), radius=70, stroke_style=StrokeStyle(color=TEAL, width=3.5))
    scene.add(SketchAnimation(start_time=2.4, duration=1.1, sound_volume=0.12, sound_style="pen"), card_soft)
    scene.add(SketchAnimation(start_time=2.5, duration=0.5, sound=False), label_soft)
    scene.add(SketchAnimation(start_time=2.7, duration=1.0, sound_volume=0.12, sound_style="pen"), circle_soft)

    # Card 3: Standard Chalk Sound (`sound_volume=0.28, sound_style="chalk"`)
    card_chalk = RoundedRectangle(
        top_left=(645, 130),
        width=260,
        height=320,
        corner_radius=18,
        stroke_style=StrokeStyle(color=BLUE, width=3.0),
        fill_style=FillStyle(color=PASTEL_BLUE, opacity=0.35, hachure_gap=12),
    )
    label_chalk = Text("3. Chalk (vol=0.28)", position=(775, 175), font_size=22, stroke_style=StrokeStyle(color=BLUE, width=2.0))
    circle_chalk = Circle(center=(775, 295), radius=70, stroke_style=StrokeStyle(color=BLUE, width=3.5))
    scene.add(SketchAnimation(start_time=4.0, duration=1.1, sound_volume=0.28, sound_style="chalk"), card_chalk)
    scene.add(SketchAnimation(start_time=4.1, duration=0.5, sound=False), label_chalk)
    scene.add(SketchAnimation(start_time=4.3, duration=1.0, sound_volume=0.28, sound_style="chalk"), circle_chalk)

    out_path = str(out_dir / "sketch_sound_control.mp4")
    return scene.render(out_path, max_length=5.6)


def render_with_audio(out_dir: Path = GALLERY_OUT_DIR) -> str:
    """Tutorial 5.1: Synchronizing SketchAnimation to spoken words with VoiceTimelineSync."""
    provider = MockVoiceProvider()
    narration = provider.synthesize("In our first step, we sketch a circle representing Earth.")
    circle = Circle(center=(960, 540), radius=100, stroke_style=StrokeStyle(color=BLUE, width=4))
    event, _ = VoiceTimelineSync.sync_event_to_word(
        clip=narration,
        word="circle",
        event_cls=SketchAnimation,
        drawable=circle,
        duration=1.5,
        lead_in=0.1,
    )
    scene = Scene(width=1920, height=1080)
    scene.add(event=event, drawable=circle)
    out_path = str(out_dir / "with_audio.mp4")
    return scene.render(out_path, narration=narration)


# ============================================================================
# Theme 6: Scientific Storytelling & Academic LaTeX/TikZ Export
# ============================================================================


def render_solar_system(out_dir: Path = GALLERY_OUT_DIR) -> str:
    """Tutorial 6.1: Multi-scene dark-mode blackboard journey through the Solar System."""
    rng = np.random.default_rng(42)
    scene = Scene(width=1920, height=1088, background_color=BLACK)
    scene.set_viewport_to_identity()

    text_style = StrokeStyle(color=WHITE)
    planet_sketch = SketchStyle(roughness=2)

    title = Text("The Solar System", position=(960, 500), font_size=72, stroke_style=text_style)
    subtitle = Text("A Journey Through Space and Scale", position=(960, 600), font_size=36, stroke_style=text_style)
    scene.add(FadeInAnimation(start_time=0, duration=1), drawable=title)
    scene.add(FadeInAnimation(start_time=0.5, duration=1), drawable=subtitle)

    eraser = Eraser(
        objects_to_erase=[title, subtitle],
        drawable_cache=scene.drawable_cache,
        glow_dot_hint={"color": ERASER_HINT_COLOR, "radius": 10},
        stroke_style=StrokeStyle(color=BLACK),
    )
    scene.add(SketchAnimation(start_time=2, duration=0.5), drawable=eraser)

    sun = Circle(
        center=(960, 600),
        radius=80,
        stroke_style=StrokeStyle(color=WHITE),
        fill_style=FillStyle(color=YELLOW, hachure_gap=10),
        sketch_style=planet_sketch,
        id="sun",
    )
    scene.add(SketchAnimation(start_time=2.5, duration=2), drawable=sun)

    planet_data = [
        ("Mercury", 150, 6, GRAY),
        ("Venus", 180, 9, ORANGE),
        ("Earth", 215, 10, BLUE),
        ("Mars", 260, 7, RED),
        ("Jupiter", 380, 25, LIGHT_GRAY),
        ("Saturn", 480, 22, LIGHT_GRAY),
        ("Uranus", 560, 15, LIGHT_GRAY),
        ("Neptune", 620, 14, LIGHT_GRAY),
    ]
    planet_drawables = []
    start_time = 4.0
    for name, orbit_radius, planet_radius, color in planet_data:
        planet = Circle(
            center=(960 + orbit_radius, 600),
            radius=planet_radius,
            stroke_style=StrokeStyle(color=WHITE),
            fill_style=FillStyle(color=color, hachure_gap=6),
            sketch_style=planet_sketch,
        )
        planet_for_anim = planet.translate(offset_x=-(1200 + orbit_radius), offset_y=0)
        planet_for_anim.id = name.lower()
        orbit = Circle(center=(960, 600), radius=orbit_radius, stroke_style=StrokeStyle(color=WHITE, width=1))
        orbit.id = name.lower() + "_orbit"

        scene.add(SketchAnimation(start_time=start_time, duration=0.1), drawable=planet_for_anim)
        scene.add(SketchAnimation(start_time=start_time, duration=1.0), drawable=orbit)
        scene.add(
            TranslateToAnimation(
                start_time=start_time + 0.1,
                duration=1.0,
                data={"point": (960 + orbit_radius, 600)},
            ),
            drawable=planet_for_anim,
        )
        planet_drawables.extend([planet_for_anim, orbit])
        start_time += 1.0

    planetary_system = DrawableGroup(elements=[sun, *planet_drawables], grouping_method="parallel")
    scene.add(ZoomOutAnimation(start_time=13, duration=2, data={"factor": 0.2}), drawable=planetary_system)
    scene.add(FadeOutAnimation(start_time=13, duration=2), drawable=planetary_system)

    stars = [
        Circle(
            center=( int(rng.integers(50, 1870)), int(rng.integers(50, 1038)) ),
            radius=float(rng.uniform(1, 3)),
            stroke_style=StrokeStyle(color=WHITE),
        )
        for _ in range(60)
    ]
    for i, star in enumerate(stars):
        scene.add(FadeInAnimation(start_time=15.0 + i * 0.02, duration=0.8), drawable=star)

    final_msg = Text(
        "This is the only home known to us — let's protect it.",
        position=(960, 540),
        font_size=48,
        stroke_style=text_style,
    )
    scene.add(SketchAnimation(start_time=16.5, duration=1.5), drawable=final_msg)

    out_path = str(out_dir / "solar_system_journey.mp4")
    return scene.render(out_path, max_length=19)


def render_tikz_beamer(out_dir: Path = GALLERY_OUT_DIR) -> str:
    """Tutorial 6.2: Export a scene to native TikZ and LaTeX Beamer slides."""
    scene = Scene(width=1920, height=1088)
    title = Text("TikZ Export Demo", position=(400, 100), font_size=120, stroke_style=StrokeStyle(color=BLUE, width=2))
    triangle = NGon(
        center=(500, 500),
        radius=200,
        n=3,
        stroke_style=StrokeStyle(color=RED, width=2),
        fill_style=FillStyle(color=(1.0, 0.9, 0.85)),
        sketch_style=SketchStyle(roughness=2),
    )
    rect = Rectangle(
        top_left=(900, 350),
        width=350,
        height=250,
        stroke_style=StrokeStyle(color=BLACK, width=2),
        fill_style=FillStyle(color=(0.85, 0.92, 1.0)),
        sketch_style=SketchStyle(roughness=1.5),
    )
    connector = Line(start=(700, 500), end=(900, 475), stroke_style=StrokeStyle(color=BLACK, width=1.5))
    label = Text("Native LaTeX!", position=(950, 700), font_size=60, stroke_style=StrokeStyle(color=BLUE, width=1.5))

    scene.add(SketchAnimation(duration=2), drawable=title)
    scene.add(SketchAnimation(start_time=2, duration=2), drawable=triangle)
    scene.add(SketchAnimation(start_time=4, duration=2), drawable=rect)
    scene.add(SketchAnimation(start_time=6, duration=1), drawable=connector)
    scene.add(SketchAnimation(start_time=7, duration=1.5), drawable=label)

    tex_dir = out_dir / "tikz_beamer"
    tex_path = scene.export_beamer(str(tex_dir), n_frames=6, backend="tikz", title="Handanim TikZ Demo")
    return tex_path


def render_hero_showcase(out_dir: Path = GALLERY_OUT_DIR) -> str:
    """5-second README Hero Showcase: LaTeX math + Flowchart + Eraser + Camera pan + Chalk/Eraser SFX."""
    scene = Scene(width=960, height=540, fps=24, sketch_sound=True, background_music="calm")

    formula = Math(
        r"$y = \sigma(Wx + b)$",
        position=(80, 70),
        font_size=64,
        stroke_style=StrokeStyle(color=BLUE, width=2.5),
    )
    draft = Text(
        "Draft: linear only?",
        position=(80, 215),
        font_size=36,
        stroke_style=StrokeStyle(color=RED, width=2),
    )
    flow = Flowchart.from_dict(
        {
            "nodes": [
                {
                    "id": "x",
                    "label": "Input x",
                    "position": [220, 390],
                    "size": [190, 74],
                    "font_size": 28,
                    "fill_style": FillStyle(color=PASTEL_BLUE),
                },
                {
                    "id": "h",
                    "label": "Hidden Wx+b",
                    "position": [540, 390],
                    "size": [230, 74],
                    "font_size": 28,
                    "fill_style": FillStyle(color=PASTEL_ORANGE),
                },
                {
                    "id": "y",
                    "label": "Output y",
                    "position": [860, 390],
                    "size": [190, 74],
                    "font_size": 28,
                    "fill_style": FillStyle(color=PASTEL_GREEN),
                },
            ],
            "edges": [
                {"from": "x", "to": "h", "from_side": "right", "to_side": "left"},
                {"from": "h", "to": "y", "from_side": "right", "to_side": "left"},
            ],
        }
    )
    eraser = Eraser(
        objects_to_erase=[draft],
        drawable_cache=scene.drawable_cache,
        glow_dot_hint={"color": ERASER_HINT_COLOR, "radius": 8},
    )
    fixed = Text(
        "Non-linear activation!",
        position=(80, 215),
        font_size=38,
        stroke_style=StrokeStyle(color=NAVY, width=2.2),
    )

    scene.add(SketchAnimation(start_time=0.0, duration=1.1), drawable=formula)
    scene.add(SketchAnimation(start_time=0.6, duration=0.8), drawable=draft)
    scene.add(SketchAnimation(start_time=1.4, duration=1.5), drawable=flow)
    scene.add(SketchAnimation(start_time=2.9, duration=0.8), drawable=eraser)
    scene.add(SketchAnimation(start_time=3.7, duration=0.6), drawable=fixed)
    scene.add(
        CameraAnimation(
            start_time=3.6,
            duration=1.2,
            data={"to_xrange": (120, 1080), "to_yrange": (40, 580)},
        )
    )

    mp4_path = str(out_dir / "hero_showcase.mp4")
    gif_path = str(out_dir / "hero_showcase.gif")
    scene.render(mp4_path, max_length=5.0)
    scene.render(gif_path, max_length=5.0)
    return mp4_path


GALLERY_BUILDERS: dict[str, Callable[[Path], str]] = {
    "hero_showcase": render_hero_showcase,
    "pythagoras": render_pythagoras,
    "a_plus_b_square": render_a_plus_b_square,
    "distributive_property": render_distributive_property,
    "hershey_math": render_hershey_math,
    "ml_workflow": render_ml_workflow,
    "character_rig": render_character_rig,
    "scene_transitions": render_scene_transitions,
    "captions_overlay": render_captions_overlay,
    "sketch_sound_control": render_sketch_sound_control,
    "with_audio": render_with_audio,
    "solar_system": render_solar_system,
    "tikz_beamer": render_tikz_beamer,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build handanim documentation gallery media.")
    parser.add_argument("--list", action="store_true", help="List available gallery builders.")
    parser.add_argument("--only", type=str, help="Render a single named gallery item.")
    parser.add_argument("--all", action="store_true", help="Render all gallery items.")
    args = parser.parse_args()

    GALLERY_OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.list:
        for name in GALLERY_BUILDERS:
            print(f" - {name}")
        return

    if args.only:
        if args.only not in GALLERY_BUILDERS:
            raise SystemExit(f"Unknown gallery item '{args.only}'. Available: {', '.join(GALLERY_BUILDERS)}")
        out = GALLERY_BUILDERS[args.only](GALLERY_OUT_DIR)
        print(f"Rendered {args.only} -> {out}")
        return

    if args.all:
        for name, fn in GALLERY_BUILDERS.items():
            out = fn(GALLERY_OUT_DIR)
            print(f"Rendered {name} -> {out}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
