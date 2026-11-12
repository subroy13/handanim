"""Visual demo of:
1. Instant Show(0), Hide(t), Swap(a, b, t), and FadeIn after FadeOut restoring base opacity.
2. CharacterRig with parent-child RigNodes, VariantSlots (blinking eyes & mouth shapes),
   PoseAnimation keyframe blending, and TwoJointLimb 2D inverse kinematics reaching targets.
"""

import os

from handanim import (
    CharacterRig,
    Circle,
    Curve,
    FadeInAnimation,
    FadeOutAnimation,
    FillStyle,
    Line,
    Pose,
    PoseAnimation,
    RigNode,
    RoundedRectangle,
    Scene,
    Show,
    SketchAnimation,
    SketchStyle,
    StrokeStyle,
    Swap,
    Text,
    TwoJointLimb,
    VariantSlot,
)
from handanim.stylings.color import BLACK, BLUE, ORANGE, PASTEL_BLUE, PASTEL_GREEN, RED, TEAL

SKETCH = SketchStyle(roughness=1.2, bowing=1.0)
PenBlack = StrokeStyle(color=BLACK, width=3.5)
PenBlue = StrokeStyle(color=BLUE, width=3.5)
PenRed = StrokeStyle(color=RED, width=3.5)


def build_character(origin_x: float = 380.0, origin_y: float = 340.0) -> CharacterRig:
    """Build an articulated hand-drawn character centered at (origin_x, origin_y)."""
    # Head outline (centered above neck at (origin_x, origin_y - 55))
    hx, hy = origin_x, origin_y - 55.0
    head_circle = Circle(
        center=(hx, hy),
        radius=42,
        stroke_style=PenBlack,
        sketch_style=SKETCH,
        fill_style=FillStyle(color=PASTEL_BLUE, opacity=0.25, hachure_gap=10),
    )

    # Eyes VariantSlot ("open" vs "blink")
    eyes_open = RigNode(
        name="eyes_open_group",
        drawables=[
            Circle(center=(hx - 14, hy - 8), radius=4.5, stroke_style=PenBlack, fill_style=FillStyle(color=BLACK)),
            Circle(center=(hx + 14, hy - 8), radius=4.5, stroke_style=PenBlack, fill_style=FillStyle(color=BLACK)),
        ],
    )
    eyes_blink = RigNode(
        name="eyes_blink_group",
        drawables=[
            Line((hx - 20, hy - 8), (hx - 8, hy - 8), stroke_style=PenBlack, sketch_style=SKETCH),
            Line((hx + 8, hy - 8), (hx + 20, hy - 8), stroke_style=PenBlack, sketch_style=SKETCH),
        ],
    )
    eyes_slot = VariantSlot(
        name="eyes",
        variants={"open": eyes_open, "blink": eyes_blink},
        default="open",
        pivot=(hx, hy - 8),
    )
    # Schedule a single natural blink across the 6-second animation
    eyes_slot.set_schedule(
        [
            (0.0, "open"),
            (2.6, "blink"),
            (2.78, "open"),
        ]
    )

    # Mouth VariantSlot ("neutral", "smile", "open")
    mouth_neutral = Line((hx - 12, hy + 14), (hx + 12, hy + 14), stroke_style=PenBlack, sketch_style=SKETCH)
    mouth_smile = Curve(
        points=[(hx - 15, hy + 11), (hx, hy + 22), (hx + 15, hy + 11)],
        stroke_style=PenBlack,
        sketch_style=SKETCH,
    )
    mouth_open = Circle(
        center=(hx, hy + 15),
        radius=8,
        stroke_style=PenRed,
        sketch_style=SKETCH,
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
        pivot=(origin_x, origin_y - 12.0),  # neck pivot
        drawables=[head_circle],
        children=[eyes_slot, mouth_slot],
    )

    # Left arm (shoulder -> elbow -> hand)
    l_shoulder = (origin_x - 10.0, origin_y)
    l_elbow = (origin_x - 55.0, origin_y + 45.0)
    l_hand = (origin_x - 80.0, origin_y + 95.0)
    forearm_l = RigNode(
        name="forearm_l",
        pivot=l_elbow,
        drawables=[
            Line(l_elbow, l_hand, stroke_style=PenBlack, sketch_style=SKETCH),
            Circle(center=l_hand, radius=6, stroke_style=PenBlack, sketch_style=SKETCH),
        ],
    )
    upper_arm_l = RigNode(
        name="upper_arm_l",
        pivot=l_shoulder,
        drawables=[Line(l_shoulder, l_elbow, stroke_style=PenBlack, sketch_style=SKETCH)],
        children=[forearm_l],
    )

    # Right arm (shoulder -> elbow -> hand) configured with 2-joint IK
    r_shoulder = (origin_x + 10.0, origin_y)
    r_elbow = (origin_x + 85.0, origin_y)
    r_hand = (origin_x + 155.0, origin_y)
    forearm_r = RigNode(
        name="forearm_r",
        pivot=r_elbow,
        drawables=[
            Line(r_elbow, r_hand, stroke_style=PenBlue, sketch_style=SKETCH),
            Circle(
                center=r_hand,
                radius=8,
                stroke_style=PenRed,
                sketch_style=SKETCH,
                fill_style=FillStyle(color=RED, opacity=0.5, hachure_gap=5),
            ),
        ],
    )
    upper_arm_r = RigNode(
        name="upper_arm_r",
        pivot=r_shoulder,
        drawables=[
            Line(r_shoulder, r_elbow, stroke_style=PenBlue, sketch_style=SKETCH),
            Circle(center=r_elbow, radius=5, stroke_style=PenBlue, sketch_style=SKETCH),
        ],
        children=[forearm_r],
    )

    # Torso & legs
    hip = (origin_x, origin_y + 130.0)
    torso_drawables = [
        Line((origin_x, origin_y - 12.0), hip, stroke_style=PenBlack, sketch_style=SKETCH),
        Line(hip, (origin_x - 45.0, origin_y + 240.0), stroke_style=PenBlack, sketch_style=SKETCH),
        Line(hip, (origin_x + 45.0, origin_y + 240.0), stroke_style=PenBlack, sketch_style=SKETCH),
    ]
    torso_node = RigNode(
        name="torso",
        pivot=hip,
        drawables=torso_drawables,
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


def main() -> None:
    scene = Scene(width=960, height=540, fps=24, background_color=(0.99, 0.98, 0.95))
    scene.set_viewport_to_identity()

    # 1. Instant Show(0) hook on Frame 0
    hook_title = Text(
        "Character Rig, 2-Joint IK & Show/Hide/Swap",
        position=(60, 48),
        font_size=36,
        stroke_style=StrokeStyle(color=BLUE, width=2.5),
    )
    scene.add(Show(0.0), hook_title)

    # 2. Step banners swapped using Swap(a, b, t)
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

    # 3. Whiteboard diagram card on the right that fades out and fades back in
    board_card = RoundedRectangle(
        top_left=(600, 160),
        width=290,
        height=260,
        border_radius=24,
        stroke_style=StrokeStyle(color=BLACK, width=3.0, opacity=0.85),
        sketch_style=SKETCH,
        fill_style=FillStyle(color=PASTEL_GREEN, opacity=0.35, hachure_gap=12),
    )
    target_high = Circle(
        center=(640, 220),
        radius=16,
        stroke_style=StrokeStyle(color=RED, width=3.0),
        sketch_style=SKETCH,
        fill_style=FillStyle(color=ORANGE, opacity=0.6, hachure_gap=6),
    )
    target_low = Circle(
        center=(630, 360),
        radius=16,
        stroke_style=StrokeStyle(color=BLUE, width=3.0),
        sketch_style=SKETCH,
        fill_style=FillStyle(color=PASTEL_BLUE, opacity=0.6, hachure_gap=6),
    )
    scene.add(SketchAnimation(start_time=0.0, duration=0.8), board_card)
    scene.add(Show(1.8), target_high)
    scene.add(Swap(target_high, target_low, start_time=3.0))

    # Demonstrate FadeOut followed by FadeIn on board_card (restores original opacity)
    scene.add(FadeOutAnimation(start_time=4.0, duration=0.5), board_card)
    scene.add(FadeInAnimation(start_time=4.7, duration=0.6), board_card)
    scene.add(Show(4.7), target_high)

    # 4. Articulated CharacterRig with keyframe poses & IK reaching
    rig = build_character(origin_x=380.0, origin_y=260.0)
    scene.add(Show(0.0), rig)

    pose_rest = Pose(
        angles={"upper_arm_r": 35.0, "forearm_r": 20.0, "head": 0.0},
        variants={"mouth": "neutral"},
    )
    pose_wave_up = Pose(
        angles={"upper_arm_r": -55.0, "forearm_r": -65.0, "head": -6.0},
        variants={"mouth": "smile"},
    )
    pose_wave_down = Pose(
        angles={"upper_arm_r": -25.0, "forearm_r": -20.0, "head": 5.0},
        variants={"mouth": "open"},
    )
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

    output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    mp4_path = os.path.join(output_dir, "character_rig_demo.mp4")
    scene.render(mp4_path, max_length=6.0)
    print(f"Rendered character rig demo to: {mp4_path}")


if __name__ == "__main__":
    main()
