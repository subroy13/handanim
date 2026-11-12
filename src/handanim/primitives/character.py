from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from ..core.draw_ops import OpsSet
from ..core.drawable import Drawable


def _wrap_deg(angle: float) -> float:
    """Wrap angle in degrees to (-180, 180]."""
    wrapped = (angle + 180.0) % 360.0 - 180.0
    return 180.0 if wrapped == -180.0 else wrapped


def solve_two_joint_ik(
    root_pos: tuple[float, float],
    mid_pos: tuple[float, float],
    end_pos: tuple[float, float],
    target_pos: tuple[float, float],
    bend_direction: int = 1,
) -> tuple[float, float]:
    """Solve 2D two-bone analytic inverse kinematics using the Law of Cosines.

    Given rest joint positions `(root_pos, mid_pos, end_pos)` and a desired
    `target_pos` (in the same coordinate frame as `root_pos`), returns the
    local rotation angles `(upper_angle_deg, lower_angle_deg)` for a
    parent-child bone pair so that `end_pos` reaches `target_pos` (or stretches
    toward it if out of reach).

    Args:
        root_pos: Rest position of the root joint (e.g. shoulder or hip).
        mid_pos: Rest position of the middle joint (e.g. elbow or knee).
        end_pos: Rest position of the end effector (e.g. wrist/hand or ankle/foot).
        target_pos: Desired position for the end effector.
        bend_direction: `+1` or `-1` selecting which side the middle joint bends toward.

    Returns:
        Tuple `(upper_angle_deg, lower_angle_deg)` in degrees.
    """
    v1x = mid_pos[0] - root_pos[0]
    v1y = mid_pos[1] - root_pos[1]
    v2x = end_pos[0] - mid_pos[0]
    v2y = end_pos[1] - mid_pos[1]

    l1 = float(np.hypot(v1x, v1y))
    l2 = float(np.hypot(v2x, v2y))
    if l1 < 1e-8 or l2 < 1e-8:
        return 0.0, 0.0

    theta1_rest = float(np.arctan2(v1y, v1x))
    theta2_rest = float(np.arctan2(v2y, v2x))

    tx = target_pos[0] - root_pos[0]
    ty = target_pos[1] - root_pos[1]
    raw_dist = float(np.hypot(tx, ty))
    theta_target = float(np.arctan2(ty, tx)) if raw_dist > 1e-8 else theta1_rest

    min_reach = max(1e-9, abs(l1 - l2))
    max_reach = l1 + l2
    d = float(np.clip(raw_dist, min_reach, max_reach))

    cos_alpha = float(np.clip((l1 * l1 + d * d - l2 * l2) / (2.0 * l1 * d), -1.0, 1.0))
    alpha = float(np.arccos(cos_alpha))
    sign = 1.0 if bend_direction >= 0 else -1.0

    theta1_new = theta_target + sign * alpha
    elbow_x = root_pos[0] + l1 * np.cos(theta1_new)
    elbow_y = root_pos[1] + l1 * np.sin(theta1_new)
    clamped_tx = root_pos[0] + d * np.cos(theta_target)
    clamped_ty = root_pos[1] + d * np.sin(theta_target)
    theta2_new = float(np.arctan2(clamped_ty - elbow_y, clamped_tx - elbow_x))

    delta_theta1 = float(np.rad2deg(theta1_new - theta1_rest))
    delta_theta2 = float(np.rad2deg(theta2_new - theta2_rest - (theta1_new - theta1_rest)))
    return _wrap_deg(delta_theta1), _wrap_deg(delta_theta2)


@dataclass
class Pose:
    """Declarative snapshot of a `CharacterRig` configuration.

    Attributes:
        angles: Mapping of node name to local rotation delta in degrees.
        offsets: Mapping of node name to local `(dx, dy)` translation offset.
        scales: Mapping of node name to local `(sx, sy)` scale multiplier.
        ik_targets: Mapping of limb name to world-space `(x, y)` target point.
        variants: Mapping of `VariantSlot` name to active variant key.
    """

    angles: dict[str, float] = field(default_factory=dict)
    offsets: dict[str, tuple[float, float]] = field(default_factory=dict)
    scales: dict[str, tuple[float, float]] = field(default_factory=dict)
    ik_targets: dict[str, tuple[float, float]] = field(default_factory=dict)
    variants: dict[str, str] = field(default_factory=dict)

    def copy(self) -> Pose:
        return Pose(
            angles=dict(self.angles),
            offsets=dict(self.offsets),
            scales=dict(self.scales),
            ik_targets=dict(self.ik_targets),
            variants=dict(self.variants),
        )

    def get_angle(self, name: str) -> float:
        return float(self.angles.get(name, 0.0))

    def get_offset(self, name: str) -> tuple[float, float]:
        return self.offsets.get(name, (0.0, 0.0))

    def get_scale(self, name: str) -> tuple[float, float]:
        return self.scales.get(name, (1.0, 1.0))

    def get_variant(self, name: str, default: str) -> str:
        return self.variants.get(name, default)

    def interpolate(self, other: Pose, progress: float) -> Pose:
        """Linearly interpolate joint angles, offsets, scales, and IK targets."""
        p = float(np.clip(progress, 0.0, 1.0))

        all_angle_keys = set(self.angles.keys()) | set(other.angles.keys())
        angles = {
            k: (1.0 - p) * self.get_angle(k) + p * other.get_angle(k)
            for k in all_angle_keys
        }

        all_offset_keys = set(self.offsets.keys()) | set(other.offsets.keys())
        offsets = {}
        for k in all_offset_keys:
            ox0, oy0 = self.get_offset(k)
            ox1, oy1 = other.get_offset(k)
            offsets[k] = ((1.0 - p) * ox0 + p * ox1, (1.0 - p) * oy0 + p * oy1)

        all_scale_keys = set(self.scales.keys()) | set(other.scales.keys())
        scales = {}
        for k in all_scale_keys:
            sx0, sy0 = self.get_scale(k)
            sx1, sy1 = other.get_scale(k)
            scales[k] = ((1.0 - p) * sx0 + p * sx1, (1.0 - p) * sy0 + p * sy1)

        all_ik_keys = set(self.ik_targets.keys()) | set(other.ik_targets.keys())
        ik_targets = {}
        for k in all_ik_keys:
            if k in self.ik_targets and k in other.ik_targets:
                tx0, ty0 = self.ik_targets[k]
                tx1, ty1 = other.ik_targets[k]
                ik_targets[k] = ((1.0 - p) * tx0 + p * tx1, (1.0 - p) * ty0 + p * ty1)
            elif p >= 0.5 and k in other.ik_targets:
                ik_targets[k] = other.ik_targets[k]
            elif p < 0.5 and k in self.ik_targets:
                ik_targets[k] = self.ik_targets[k]

        variants = dict(self.variants)
        if p >= 0.5:
            variants.update(other.variants)

        return Pose(
            angles=angles,
            offsets=offsets,
            scales=scales,
            ik_targets=ik_targets,
            variants=variants,
        )


def _node_matrix(
    pivot: tuple[float, float],
    angle_deg: float,
    offset: tuple[float, float],
    scale: tuple[float, float],
) -> np.ndarray:
    """Build 3x3 homogeneous 2D transform matrix for scale & rotate around pivot + offset."""
    px, py = pivot
    sx, sy = scale
    rad = np.deg2rad(angle_deg)
    cos_a = float(np.cos(rad))
    sin_a = float(np.sin(rad))
    dx, dy = offset

    # Point transform:
    # 1) shift by -pivot
    # 2) scale by (sx, sy)
    # 3) rotate by angle_deg
    # 4) shift by +pivot + offset
    m00 = cos_a * sx
    m01 = -sin_a * sy
    m10 = sin_a * sx
    m11 = cos_a * sy
    tx = px - m00 * px - m01 * py + dx
    ty = py - m10 * px - m11 * py + dy
    return np.array(
        [
            [m00, m01, tx],
            [m10, m11, ty],
            [0.0, 0.0, 1.0],
        ],
        dtype=float,
    )


def _scale_opsset_around_point(
    opsset: OpsSet,
    scale_x: float,
    scale_y: float,
    center: tuple[float, float],
) -> None:
    """Scale an OpsSet in-place around an explicit pivot point."""
    if scale_x == 1.0 and scale_y == 1.0:
        return
    cx, cy = center
    opsset.translate(-cx, -cy)
    # Scale around origin directly
    from ..core.draw_ops import Ops, OpsType

    new_ops = []
    for ops in opsset.opsset:
        if ops.type == OpsType.IMAGE and isinstance(ops.data, dict):
            img_data = dict(ops.data)
            img_data["x"] = scale_x * ops.data["x"]
            img_data["y"] = scale_y * ops.data["y"]
            img_data["width"] = ops.data["width"] * abs(scale_x)
            img_data["height"] = ops.data["height"] * abs(scale_y)
            new_ops.append(Ops(ops.type, img_data, ops.partial, ops.meta))
        elif isinstance(ops.data, list):
            new_data = [(scale_x * x, scale_y * y) for x, y in ops.data]
            new_ops.append(Ops(ops.type, new_data, ops.partial, ops.meta))
        else:
            new_ops.append(ops)
    opsset.opsset = new_ops
    opsset.translate(cx, cy)


class RigNode(Drawable):
    """A hierarchical transform node with its own pivot and child nodes.

    Children attached to a `RigNode` inherit its rotation (around `pivot`),
    scale (around `pivot`), and translation (`offset`).
    """

    def __init__(
        self,
        name: str,
        pivot: tuple[float, float] = (0.0, 0.0),
        drawables: Sequence[Drawable] | None = None,
        children: Sequence[RigNode] | None = None,
        angle: float = 0.0,
        offset: tuple[float, float] = (0.0, 0.0),
        scale_factor: tuple[float, float] = (1.0, 1.0),
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.name = name
        self.pivot = pivot
        self.drawables: list[Drawable] = list(drawables) if drawables else []
        self.children: list[RigNode] = list(children) if children else []
        self.angle = angle
        self.offset = offset
        self.scale_factor = scale_factor
        self._cached_opssets: dict[str, OpsSet] = {}

    def _get_cached_drawable_opsset(
        self,
        drawable: Drawable,
        pose: Pose | None = None,
        time: float | None = None,
    ) -> OpsSet:
        """Return a fresh OpsSet for `drawable`, caching static primitives so roughness does not boil frame-to-frame."""
        if isinstance(drawable, RigNode):
            return drawable.draw_with_pose(pose=pose, time=time)
        if drawable.id not in self._cached_opssets:
            self._cached_opssets[drawable.id] = drawable.draw()
        return OpsSet(initial_set=list(self._cached_opssets[drawable.id].opsset))

    def add_child(self, child: RigNode) -> RigNode:
        self.children.append(child)
        return child

    def find_node(self, name: str) -> RigNode | None:
        if self.name == name:
            return self
        for child in self.children:
            found = child.find_node(name)
            if found is not None:
                return found
        return None

    def find_path(self, name: str) -> list[RigNode] | None:
        if self.name == name:
            return [self]
        for child in self.children:
            sub_path = child.find_path(name)
            if sub_path is not None:
                return [self] + sub_path
        return None

    def get_local_transform_params(
        self, pose: Pose | None = None
    ) -> tuple[float, tuple[float, float], tuple[float, float]]:
        angle = self.angle + (pose.get_angle(self.name) if pose else 0.0)
        pose_ox, pose_oy = pose.get_offset(self.name) if pose else (0.0, 0.0)
        offset = (self.offset[0] + pose_ox, self.offset[1] + pose_oy)
        pose_sx, pose_sy = pose.get_scale(self.name) if pose else (1.0, 1.0)
        scale = (self.scale_factor[0] * pose_sx, self.scale_factor[1] * pose_sy)
        return angle, offset, scale

    def _draw_own_primitives(self, pose: Pose | None = None, time: float | None = None) -> OpsSet:
        opsset = OpsSet(initial_set=[])
        for d in self.drawables:
            opsset.extend(self._get_cached_drawable_opsset(d, pose=pose, time=time))
        return opsset

    def draw_with_pose(self, pose: Pose | None = None, time: float | None = None) -> OpsSet:
        """Evaluate this node and all descendants under `pose` via forward kinematics."""
        combined = self._draw_own_primitives(pose=pose, time=time)
        for child in self.children:
            combined.extend(child.draw_with_pose(pose=pose, time=time))

        angle, offset, scale = self.get_local_transform_params(pose)
        if scale != (1.0, 1.0):
            _scale_opsset_around_point(combined, scale[0], scale[1], self.pivot)
        if angle != 0.0:
            combined.rotate(angle, center_of_rotation=self.pivot)
        if offset != (0.0, 0.0):
            combined.translate(offset[0], offset[1])
        return combined

    def draw(self) -> OpsSet:
        return self.draw_with_pose(pose=None)


class VariantSlot(RigNode):
    """A swappable sprite/shape slot (e.g. eyes or mouth) attached to a parent `RigNode`.

    Inherits all parent transforms while switching its active drawable based on
    the current `Pose.variants[name]` or a scheduled time series.
    """

    def __init__(
        self,
        name: str,
        variants: dict[str, Drawable],
        default: str | None = None,
        pivot: tuple[float, float] = (0.0, 0.0),
        *args,
        **kwargs,
    ) -> None:
        super().__init__(name, pivot, *args, **kwargs)
        if not variants:
            raise ValueError("VariantSlot requires at least one variant drawable")
        self.variants = dict(variants)
        self.default = default if default is not None else next(iter(variants.keys()))
        self.schedule: list[tuple[float, str]] = []

    def set_schedule(self, entries: Sequence[tuple[float, str]]) -> None:
        """Set a time-sorted schedule of `(timestamp, variant_name)` switches."""
        self.schedule = sorted([(float(t), str(v)) for t, v in entries], key=lambda item: item[0])

    def add_switch(self, time: float, variant_name: str) -> None:
        """Schedule a switch to `variant_name` at `time` (in seconds)."""
        if variant_name not in self.variants:
            raise ValueError(f"Unknown variant '{variant_name}' for slot '{self.name}'")
        self.schedule.append((float(time), variant_name))
        self.schedule.sort(key=lambda item: item[0])

    def get_active_variant_name(self, pose: Pose | None = None, time: float | None = None) -> str:
        if pose is not None and self.name in pose.variants:
            return pose.variants[self.name]
        if time is not None and self.schedule:
            active = self.default
            for t_switch, v_name in self.schedule:
                if time >= t_switch:
                    active = v_name
                else:
                    break
            return active
        return self.default

    def _draw_own_primitives(self, pose: Pose | None = None, time: float | None = None) -> OpsSet:
        variant_key = self.get_active_variant_name(pose=pose, time=time)
        drawable = self.variants.get(variant_key, self.variants[self.default])
        return self._get_cached_drawable_opsset(drawable, pose=pose, time=time)


@dataclass
class TwoJointLimb:
    """Two-bone inverse kinematics chain descriptor (e.g. upper arm + forearm).

    Attributes:
        name: Identifier used in `Pose.ik_targets[name]`.
        upper_node: Name of the upper `RigNode` (e.g. `"upper_arm_r"`).
        lower_node: Name of the lower `RigNode` (e.g. `"forearm_r"`), which must be
            a child of `upper_node`.
        effector_pos: Rest position of the end effector (e.g. hand/wrist or foot).
        bend_direction: `+1` or `-1` controlling which way the middle joint bends.
    """

    name: str
    upper_node: str
    lower_node: str
    effector_pos: tuple[float, float]
    bend_direction: int = 1


class CharacterRig(Drawable):
    """Articulated 2D character rig combining hierarchical ``RigNode`` objects, ``TwoJointLimb`` IK, and ``VariantSlot`` nodes."""

    def __init__(
        self,
        root: RigNode,
        limbs: Sequence[TwoJointLimb] | None = None,
        rest_pose: Pose | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.root = root
        self.limbs: dict[str, TwoJointLimb] = {limb.name: limb for limb in (limbs or [])}
        self.rest_pose = rest_pose.copy() if rest_pose is not None else Pose()

    def add_limb(self, limb: TwoJointLimb) -> None:
        self.limbs[limb.name] = limb

    def get_node(self, name: str) -> RigNode:
        node = self.root.find_node(name)
        if node is None:
            raise KeyError(f"RigNode '{name}' not found in CharacterRig")
        return node

    def _get_world_matrix_for_path(
        self, path: Sequence[RigNode], pose: Pose | None = None
    ) -> np.ndarray:
        mat = np.eye(3, dtype=float)
        for node in path:
            angle, offset, scale = node.get_local_transform_params(pose)
            mat = mat @ _node_matrix(node.pivot, angle, offset, scale)
        return mat

    def transform_point_for_node(
        self,
        node_name: str,
        point: tuple[float, float],
        pose: Pose | None = None,
    ) -> tuple[float, float]:
        """Transform a rest-space `point` attached to `node_name` into world coordinates under `pose`."""
        resolved_pose = self.resolve_pose(pose)
        path = self.root.find_path(node_name)
        if path is None:
            raise KeyError(f"RigNode '{node_name}' not found in CharacterRig")
        mat = self._get_world_matrix_for_path(path, resolved_pose)
        vec = mat @ np.array([point[0], point[1], 1.0], dtype=float)
        return (float(vec[0]), float(vec[1]))

    def get_joint_world_pos(
        self, node_name: str, pose: Pose | None = None
    ) -> tuple[float, float]:
        """Return the world-space position of `node_name`'s pivot under `pose`."""
        node = self.get_node(node_name)
        return self.transform_point_for_node(node_name, node.pivot, pose=pose)

    def get_limb_effector_world_pos(
        self, limb_name: str, pose: Pose | None = None
    ) -> tuple[float, float]:
        """Return the world-space position of a `TwoJointLimb`'s end effector under `pose`."""
        if limb_name not in self.limbs:
            raise KeyError(f"Limb '{limb_name}' not found in CharacterRig")
        limb = self.limbs[limb_name]
        return self.transform_point_for_node(limb.lower_node, limb.effector_pos, pose=pose)

    def resolve_pose(self, pose: Pose | None = None) -> Pose:
        """Merge `pose` with `rest_pose` and solve any `ik_targets` into concrete joint angles."""
        merged = self.rest_pose.copy()
        if pose is not None:
            merged.angles.update(pose.angles)
            merged.offsets.update(pose.offsets)
            merged.scales.update(pose.scales)
            merged.ik_targets.update(pose.ik_targets)
            merged.variants.update(pose.variants)

        for limb_name, target_world in merged.ik_targets.items():
            if limb_name not in self.limbs:
                raise KeyError(f"Unknown IK limb '{limb_name}'")
            limb = self.limbs[limb_name]
            upper_path = self.root.find_path(limb.upper_node)
            if upper_path is None:
                raise KeyError(f"Upper node '{limb.upper_node}' not found for limb '{limb_name}'")
            upper_node = upper_path[-1]
            lower_node = self.get_node(limb.lower_node)

            # Map world target into the upper_node's parent coordinate space
            parent_path = upper_path[:-1]
            if parent_path:
                parent_mat = self._get_world_matrix_for_path(parent_path, merged)
                inv_parent = np.linalg.inv(parent_mat)
                local_vec = inv_parent @ np.array([target_world[0], target_world[1], 1.0], dtype=float)
                target_local = (float(local_vec[0]), float(local_vec[1]))
            else:
                target_local = target_world

            # Account for any local offset on upper_node
            u_ox, u_oy = merged.get_offset(upper_node.name)
            total_u_ox = upper_node.offset[0] + u_ox
            total_u_oy = upper_node.offset[1] + u_oy
            adjusted_target = (target_local[0] - total_u_ox, target_local[1] - total_u_oy)

            u_angle, l_angle = solve_two_joint_ik(
                root_pos=upper_node.pivot,
                mid_pos=lower_node.pivot,
                end_pos=limb.effector_pos,
                target_pos=adjusted_target,
                bend_direction=limb.bend_direction,
            )
            merged.angles[upper_node.name] = u_angle - upper_node.angle
            merged.angles[lower_node.name] = l_angle - lower_node.angle

        return merged

    def reach(
        self,
        limb_name: str,
        target_pos: tuple[float, float],
        base_pose: Pose | None = None,
    ) -> Pose:
        """Return a new `Pose` with `limb_name`'s IK angles solved to reach `target_pos`."""
        pose = base_pose.copy() if base_pose is not None else self.rest_pose.copy()
        pose.ik_targets[limb_name] = target_pos
        return self.resolve_pose(pose)

    def draw_with_pose(self, pose: Pose | None = None, time: float | None = None) -> OpsSet:
        resolved = self.resolve_pose(pose)
        return self.root.draw_with_pose(pose=resolved, time=time)

    def draw(self) -> OpsSet:
        return self.draw_with_pose(pose=self.rest_pose)
