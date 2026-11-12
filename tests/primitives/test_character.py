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

