from __future__ import annotations

import pytest

from handanim import (
    CharacterRig,
    Circle,
    Line,
    Pose,
    PoseAnimation,
    RigNode,
    Scene,
    Show,
    SketchStyle,
    TwoJointLimb,
    VariantSlot,
    solve_two_joint_ik,
)

FLAT = SketchStyle(roughness=0, bowing=0)


def _build_arm_rig() -> CharacterRig:
    """Create a simple torso -> upper_arm -> forearm character rig with eyes and mouth slots."""
    torso_line = Line((0, 0), (0, 100), sketch_style=FLAT)
    upper_arm_line = Line((0, 0), (50, 0), sketch_style=FLAT)
    forearm_line = Line((50, 0), (90, 0), sketch_style=FLAT)

    eyes_open = Circle(center=(0, -30), radius=5, sketch_style=FLAT)
    eyes_blink = Line((-5, -30), (5, -30), sketch_style=FLAT)
    eyes_slot = VariantSlot(
        name="eyes",
        variants={"open": eyes_open, "blink": eyes_blink},
        default="open",
        pivot=(0, -30),
    )

    mouth_neutral = Line((-6, -15), (6, -15), sketch_style=FLAT)
    mouth_open = Circle(center=(0, -15), radius=4, sketch_style=FLAT)
    mouth_slot = VariantSlot(
        name="mouth",
        variants={"neutral": mouth_neutral, "open": mouth_open},
        default="neutral",
        pivot=(0, -15),
    )

    head_node = RigNode(
        name="head",
        pivot=(0, 0),
        children=[eyes_slot, mouth_slot],
    )

    forearm_node = RigNode(
        name="forearm",
        pivot=(50, 0),
        drawables=[forearm_line],
    )
    upper_arm_node = RigNode(
        name="upper_arm",
        pivot=(0, 0),
        drawables=[upper_arm_line],
        children=[forearm_node],
    )
    torso_node = RigNode(
        name="torso",
        pivot=(0, 50),
        drawables=[torso_line],
        children=[head_node, upper_arm_node],
    )

    right_arm_limb = TwoJointLimb(
        name="right_arm",
        upper_node="upper_arm",
        lower_node="forearm",
        effector_pos=(90, 0),
        bend_direction=1,
    )
    return CharacterRig(root=torso_node, limbs=[right_arm_limb])


class TestCharacterRigAndPoses:
    def test_parent_child_forward_kinematics_moves_child_pivot_with_parent(self):
        rig = _build_arm_rig()

        # Rest pose: shoulder at (0, 0), elbow at (50, 0), wrist at (90, 0)
        assert rig.get_joint_world_pos("upper_arm") == pytest.approx((0.0, 0.0), abs=1e-5)
        assert rig.get_joint_world_pos("forearm") == pytest.approx((50.0, 0.0), abs=1e-5)
        assert rig.get_limb_effector_world_pos("right_arm") == pytest.approx((90.0, 0.0), abs=1e-5)

        # Rotate upper_arm by +90 deg: elbow moves to (0, 50) and wrist moves to (0, 90)
        pose_shoulder_90 = Pose(angles={"upper_arm": 90.0})
        assert rig.get_joint_world_pos("forearm", pose=pose_shoulder_90) == pytest.approx((0.0, 50.0), abs=1e-4)
        assert rig.get_limb_effector_world_pos("right_arm", pose=pose_shoulder_90) == pytest.approx((0.0, 90.0), abs=1e-4)

        # Now ALSO rotate forearm by -90 deg around the moving elbow (0, 50):
        # forearm points back along +x from (0, 50) -> wrist at (40, 50)
        pose_both = Pose(angles={"upper_arm": 90.0, "forearm": -90.0})
        assert rig.get_joint_world_pos("forearm", pose=pose_both) == pytest.approx((0.0, 50.0), abs=1e-4)
        assert rig.get_limb_effector_world_pos("right_arm", pose=pose_both) == pytest.approx((40.0, 50.0), abs=1e-4)

    def test_two_joint_ik_reaches_target_point(self):
        rig = _build_arm_rig()
        target = (45.0, 45.0)  # distance = hypot(45, 45) ~ 63.64 < 90.0
        pose_ik = Pose(ik_targets={"right_arm": target})

        wrist_world = rig.get_limb_effector_world_pos("right_arm", pose=pose_ik)
        assert wrist_world == pytest.approx(target, abs=1e-3)

    def test_two_joint_ik_with_moved_torso_still_reaches_world_target(self):
        rig = _build_arm_rig()
        # Shift torso by (100, 200) and ask right_arm to reach (140, 230) in world space
        target_world = (140.0, 230.0)
        pose = Pose(
            offsets={"torso": (100.0, 200.0)},
            ik_targets={"right_arm": target_world},
        )
        wrist_world = rig.get_limb_effector_world_pos("right_arm", pose=pose)
        assert wrist_world == pytest.approx(target_world, abs=1e-3)

    def test_two_joint_ik_clamps_gracefully_when_out_of_reach(self):
        # Upper length = 50, lower length = 40, max reach = 90
        u_deg, l_deg = solve_two_joint_ik(
            root_pos=(0.0, 0.0),
            mid_pos=(50.0, 0.0),
            end_pos=(90.0, 0.0),
            target_pos=(0.0, 200.0),  # straight along +y, distance 200 > 90
        )
        assert u_deg == pytest.approx(90.0, abs=1e-2)
        assert l_deg == pytest.approx(0.0, abs=1e-2)

    def test_variant_slot_switches_in_pose_and_schedule(self):
        rig = _build_arm_rig()
        eyes_node = rig.get_node("eyes")
        assert isinstance(eyes_node, VariantSlot)

        # Default variant is "open" (Circle has more ops than a 1-segment Line)
        ops_open = rig.draw_with_pose(Pose(variants={"eyes": "open"}))
        ops_blink = rig.draw_with_pose(Pose(variants={"eyes": "blink"}))
        assert len(ops_open.opsset) > len(ops_blink.opsset)

        # Time schedule on eyes slot
        eyes_node.set_schedule([(0.0, "open"), (0.5, "blink"), (0.7, "open")])
        assert eyes_node.get_active_variant_name(time=0.2) == "open"
        assert eyes_node.get_active_variant_name(time=0.6) == "blink"
        assert eyes_node.get_active_variant_name(time=0.9) == "open"

    def test_pose_animation_interpolates_in_scene(self):
        rig = _build_arm_rig()
        scene = Scene(fps=10)
        scene.add(Show(0.0), rig)

        pose_start = Pose(angles={"upper_arm": 0.0})
        pose_end = Pose(angles={"upper_arm": 90.0}, variants={"mouth": "open"})
        anim = PoseAnimation(
            rig=rig,
            from_pose=pose_start,
            to_pose=pose_end,
            start_time=0.0,
            duration=1.0,
        )
        scene.add(anim, rig)

        blended_mid, _ = anim.get_pose_at_progress(0.5)
        assert blended_mid.get_angle("upper_arm") == pytest.approx(45.0, abs=1e-5)

        frames = scene.create_event_timeline(max_length=1.0)
        assert len(frames) == 11
        assert all(len(f.opsset) > 0 for f in frames)

    def test_pose_animation_from_keyframes(self):
        rig = _build_arm_rig()
        p0 = Pose(angles={"upper_arm": 0.0})
        p1 = Pose(angles={"upper_arm": 60.0})
        p2 = Pose(angles={"upper_arm": 20.0})

        anim = PoseAnimation.from_keyframes(
            rig=rig,
            keyframes=[(0.0, p0), (0.5, p1), (1.0, p2)],
        )
        pose_quarter, t_q = anim.get_pose_at_progress(0.25)
        assert t_q == pytest.approx(0.25)
        assert pose_quarter.get_angle("upper_arm") == pytest.approx(30.0, abs=1e-5)

        pose_three_quarter, t_tq = anim.get_pose_at_progress(0.75)
        assert t_tq == pytest.approx(0.75)
        assert pose_three_quarter.get_angle("upper_arm") == pytest.approx(40.0, abs=1e-5)

    def test_rig_caches_primitive_opssets_to_prevent_frame_boiling(self):
        rough_style = SketchStyle(roughness=3.0, bowing=2.0)
        head = Circle(center=(0, 0), radius=40, sketch_style=rough_style)
        node = RigNode(name="head", pivot=(0, 0), drawables=[head])
        rig = CharacterRig(root=node)

        ops1 = rig.draw_with_pose(Pose())
        ops2 = rig.draw_with_pose(Pose())
        assert [op.data for op in ops1.opsset] == [op.data for op in ops2.opsset]

    def test_moving_character_does_not_freeze_after_draw_in_or_completed_event(self):
        from handanim.animations.sketch import SketchAnimation

        rig = _build_arm_rig()
        scene = Scene(fps=10)
        # Draw-in finishes at t=0.5s while PoseAnimation continues until t=2.0s
        scene.add(SketchAnimation(start_time=0.0, duration=0.5), rig)
        scene.add(
            PoseAnimation(
                rig=rig,
                from_pose=Pose(angles={"upper_arm": 0.0}),
                to_pose=Pose(angles={"upper_arm": 90.0}),
                start_time=0.0,
                duration=2.0,
            ),
            rig,
        )

        frames = scene.create_event_timeline(max_length=2.0)
        # Frame 5 (t=0.5s), Frame 10 (t=1.0s), Frame 15 (t=1.5s), Frame 20 (t=2.0s)
        # must all have distinct arm coordinates as PoseAnimation progresses
        pts_t05 = [op.data for op in frames[5].opsset]
        pts_t10 = [op.data for op in frames[10].opsset]
        pts_t15 = [op.data for op in frames[15].opsset]
        pts_t20 = [op.data for op in frames[20].opsset]
        assert pts_t05 != pts_t10
        assert pts_t10 != pts_t15
        assert pts_t15 != pts_t20

    def test_characters_guide_builder_api_runs_end_to_end(self):
        scene = Scene(width=1080, height=1920, fps=10)
        scene.set_viewport_to_identity()
        clean = SketchStyle(roughness=0.25, bowing=0.2)

        rig = CharacterRig(pivot=(540, 960))
        torso = rig.root.add_child(
            "torso",
            pivot=(540, 960),
            drawables=[Line((540, 720), (540, 960), sketch_style=clean)],
        )
        head = torso.add_child(
            "head",
            pivot=(540, 720),
            drawables=[Circle(center=(540, 650), radius=65, sketch_style=clean)],
        )

        eyes = VariantSlot(
            "eyes",
            pivot=(540, 640),
            variants={
                "open": [
                    Circle((520, 640), 7, sketch_style=clean),
                    Circle((560, 640), 7, sketch_style=clean),
                ],
                "blink": [
                    Line((512, 640), (528, 640), sketch_style=clean),
                    Line((552, 640), (568, 640), sketch_style=clean),
                ],
            },
            default="open",
        )
        head.add_slot(eyes)

        right_arm = rig.add_two_joint_limb(
            "right_arm",
            parent=torso,
            root_pivot=(540, 750),
            length1=110.0,
            length2=100.0,
            bend_direction=1,
        )
        assert right_arm.name == "right_arm"

        pose_idle = rig.capture_pose()
        pose_point = Pose(
            angles={"head": -8.0},
            ik_targets={"right_arm": (720, 640)},
            variants={"eyes": "blink"},
        )

        scene.add(Show(0.0), rig)
        scene.add(
            PoseAnimation(
                rig=rig,
                keyframes=[
                    (0.0, pose_idle),
                    (0.8, pose_point),
                    (1.6, pose_idle),
                ],
                start_time=0.5,
                duration=1.6,
            ),
            rig,
        )

        frames = scene.create_event_timeline(max_length=2.2)
        assert len(frames) == 23
        # Frame at t=0.5s (idle) and frame at t=1.3s (pointing + blinking) must differ
        assert [op.data for op in frames[5].opsset] != [op.data for op in frames[13].opsset]

    def test_rig_blinks_with_show_only_and_after_pose_animation_ends(self):
        # 1) Rig shown with Show(0.0) and a blink schedule (no PoseAnimation at all)
        rig1 = _build_arm_rig()
        eyes1 = rig1.get_node("eyes")
        assert isinstance(eyes1, VariantSlot)
        eyes1.set_schedule([(0.0, "open"), (0.5, "blink"), (0.8, "open")])

        scene1 = Scene(fps=10)
        scene1.add(Show(0.0), rig1)
        frames1 = scene1.create_event_timeline(max_length=1.0)
        # t=0.2s (frame 2: open) vs t=0.6s (frame 6: blink) vs t=0.9s (frame 9: open)
        assert len(frames1[2].opsset) > len(frames1[6].opsset)
        assert len(frames1[9].opsset) > len(frames1[6].opsset)

        # 2) Rig with a PoseAnimation ending at t=0.5s still blinks at t=1.2s after PoseAnimation ends
        rig2 = _build_arm_rig()
        eyes2 = rig2.get_node("eyes")
        assert isinstance(eyes2, VariantSlot)
        eyes2.set_schedule([(0.0, "open"), (1.2, "blink"), (1.5, "open")])

        scene2 = Scene(fps=10)
        scene2.add(Show(0.0), rig2)
        scene2.add(
            PoseAnimation(
                rig=rig2,
                from_pose=Pose(angles={"upper_arm": 0.0}),
                to_pose=Pose(angles={"upper_arm": 45.0}),
                start_time=0.0,
                duration=0.5,
            ),
            rig2,
        )
        frames2 = scene2.create_event_timeline(max_length=1.8)
        # At t=0.8s (frame 8, after pose ended): eyes open
        # At t=1.3s (frame 13, after pose ended): eyes blink
        # At t=1.7s (frame 17, after pose ended): eyes open again
        assert len(frames2[8].opsset) > len(frames2[13].opsset)
        assert len(frames2[17].opsset) > len(frames2[13].opsset)

    def test_running_animation_does_not_freeze_when_pop_fade_or_color_event_finishes(self):
        from handanim.animations.color_transition import ColorTransitionAnimation
        from handanim.animations.easing import PopAnimation
        from handanim.animations.translate import TranslateToAnimation
        from handanim.primitives.polygons import Rectangle

        rect = Rectangle(top_left=(100, 100), width=80, height=50, sketch_style=FLAT)
        scene = Scene(fps=10)
        scene.add(Show(0.0), rect)
        # Long translation (0.0 -> 2.0s) combined with shorter Pop (0.1 -> 0.5s) and ColorTransition (0.2 -> 0.6s)
        scene.add(TranslateToAnimation(start_time=0.0, duration=2.0, data={"point": (400, 100)}), rect)
        scene.add(PopAnimation(start_time=0.1, duration=0.4), rect)
        scene.add(
            ColorTransitionAnimation(
                start_time=0.2,
                duration=0.4,
                data={"from_color": (0, 0, 0), "to_color": (1, 0, 0)},
            ),
            rect,
        )

        frames = scene.create_event_timeline(max_length=2.0)
        cx_t06 = frames[6].get_center_of_gravity()[0]
        cx_t12 = frames[12].get_center_of_gravity()[0]
        cx_t18 = frames[18].get_center_of_gravity()[0]
        assert cx_t06 < cx_t12 < cx_t18

    def test_characters_guide_rst_code_blocks_execute_cleanly(self):
        from pathlib import Path

        rst_path = Path(__file__).resolve().parents[2] / "docs" / "source" / "user_guide" / "characters_and_shorts.rst"
        lines = rst_path.read_text(encoding="utf-8").splitlines()
        code_blocks: list[str] = []
        i = 0
        while i < len(lines):
            if lines[i].strip().startswith(".. code-block:: python"):
                i += 1
                while i < len(lines) and not lines[i].strip():
                    i += 1
                block_lines: list[str] = []
                while i < len(lines) and (not lines[i].strip() or lines[i].startswith("   ")):
                    block_lines.append(lines[i][3:] if lines[i].startswith("   ") else "")
                    i += 1
                code_blocks.append("\n".join(block_lines))
            else:
                i += 1

        assert len(code_blocks) >= 2
        ns: dict = {}
        for block in code_blocks:
            exec(block, ns)  # noqa: S102
        assert "scene" in ns and "rig" in ns

    def test_pose_animation_preserves_earlier_translate_to_move(self):
        from handanim.animations.translate import TranslateToAnimation

        rig = _build_arm_rig()
        scene = Scene(fps=10)
        scene.add(Show(0.0), rig)
        # Move rig from its initial center (~45, 35) to (300, 200) between t=0.0 and t=0.5s
        scene.add(TranslateToAnimation(start_time=0.0, duration=0.5, data={"point": (300.0, 200.0)}), rig)
        # Then run a PoseAnimation starting later at t=0.8s..1.4s
        scene.add(
            PoseAnimation(
                rig=rig,
                from_pose=Pose(angles={"upper_arm": 0.0}),
                to_pose=Pose(angles={"upper_arm": 60.0}),
                start_time=0.8,
                duration=0.6,
            ),
            rig,
        )

        frames = scene.create_event_timeline(max_length=1.5)
        # At t=0.6s (after move, before pose) and at t=1.2s (during pose), rig remains translated near x=300
        cx_before_pose = frames[6].get_center_of_gravity()[0]
        cx_during_pose = frames[12].get_center_of_gravity()[0]
        assert cx_before_pose == pytest.approx(300.0, abs=5.0)
        assert cx_during_pose == pytest.approx(300.0, abs=5.0)

    def test_rounded_rectangle_four_arcs_and_corner_radius_kwarg(self):
        from handanim.primitives.polygons import RoundedRectangle

        rr = RoundedRectangle(
            top_left=(100.0, 200.0),
            width=200.0,
            height=100.0,
            corner_radius=20.0,
            sketch_style=FLAT,
        )
        assert rr.border_radius == pytest.approx(20.0)
        ops = rr.draw()
        pts = [op.data[0] for op in ops.opsset if isinstance(op.data, list) and len(op.data) == 1]
        # Top-left corner arc must pass through (100 + r*(1 - cos(45deg)), 200 + r*(1 - sin(45deg)))
        # rather than a straight chamfer cut between (100, 220) and (120, 200).
        expected_arc_mid = (100.0 + 20.0 * (1.0 - 0.70710678), 200.0 + 20.0 * (1.0 - 0.70710678))
        dists = [((px - expected_arc_mid[0]) ** 2 + (py - expected_arc_mid[1]) ** 2) ** 0.5 for px, py in pts]
        assert min(dists) < 0.5




