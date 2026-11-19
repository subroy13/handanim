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

        variants = dict(other.variants) if p >= 0.5 else dict(self.variants)

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

    def add_child(
        self,
        child_or_name: RigNode | str,
        pivot: tuple[float, float] | None = None,
        drawables: Sequence[Drawable] | None = None,
        children: Sequence[RigNode] | None = None,
        angle: float = 0.0,
        offset: tuple[float, float] = (0.0, 0.0),
        scale_factor: tuple[float, float] = (1.0, 1.0),
        *args,
        **kwargs,
    ) -> RigNode:
        if isinstance(child_or_name, RigNode):
            child = child_or_name
        elif isinstance(child_or_name, str):
            node_pivot = pivot if pivot is not None else self.pivot
            child = RigNode(
                name=child_or_name,
                pivot=node_pivot,
                drawables=drawables,
                children=children,
                angle=angle,
                offset=offset,
                scale_factor=scale_factor,
                *args,
                **kwargs,
            )
        else:
            raise TypeError("add_child expects a RigNode instance or a string node name")
        self.children.append(child)
        return child

    def add_slot(
        self,
        slot_or_name: VariantSlot | str,
        variants: dict[str, Drawable | Sequence[Drawable]] | None = None,
        default: str | None = None,
        pivot: tuple[float, float] | None = None,
        *args,
        **kwargs,
    ) -> VariantSlot:
        if isinstance(slot_or_name, VariantSlot):
            slot = slot_or_name
        elif isinstance(slot_or_name, str):
            if not variants:
                raise ValueError("variants dict is required when creating a VariantSlot by name")
            slot_pivot = pivot if pivot is not None else self.pivot
            slot = VariantSlot(
                name=slot_or_name,
                variants=variants,
                default=default,
                pivot=slot_pivot,
                *args,
                **kwargs,
            )
        else:
            raise TypeError("add_slot expects a VariantSlot instance or a string slot name")
        self.children.append(slot)
        return slot

    def has_scheduled_variants(self) -> bool:
        """Return True if this node or any descendant `VariantSlot` has a non-empty time schedule."""
        if isinstance(self, VariantSlot) and bool(self.schedule):
            return True
        return any(child.has_scheduled_variants() for child in self.children)

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

    def draw(self, time: float | None = None) -> OpsSet:
        return self.draw_with_pose(pose=None, time=time)


class VariantSlot(RigNode):
    """A swappable sprite/shape slot (e.g. eyes or mouth) attached to a parent `RigNode`.

    Inherits all parent transforms while switching its active drawable based on
    the current `Pose.variants[name]` or a scheduled time series.
    """

    def __init__(
        self,
        name: str,
        variants: dict[str, Drawable | Sequence[Drawable]] | None = None,
        default: str | None = None,
        pivot: tuple[float, float] = (0.0, 0.0),
        *args,
        **kwargs,
    ) -> None:
        super().__init__(name, pivot, *args, **kwargs)
        if not variants:
            raise ValueError("VariantSlot requires at least one variant drawable")
        normalized_variants: dict[str, Drawable] = {}
        for k, v in variants.items():
            if isinstance(v, Drawable):
                normalized_variants[k] = v
            elif isinstance(v, (list, tuple)):
                normalized_variants[k] = RigNode(
                    name=f"{name}_{k}",
                    pivot=pivot,
                    drawables=list(v),
                )
            else:
                raise TypeError(f"Variant '{k}' in VariantSlot '{name}' must be a Drawable or list of Drawables")
        self.variants = normalized_variants
        self.default = default if default is not None else next(iter(normalized_variants.keys()))
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

    def add_periodic_switch(
        self,
        start_time: float,
        end_time: float,
        pulse_variant: str = "blink",
        base_variant: str | None = None,
        period: float = 3.2,
        pulse_duration: float = 0.11,
    ) -> None:
        """Schedule periodic brief switches (e.g. eye blinks) between `start_time` and `end_time`."""
        base_v = base_variant if base_variant is not None else self.default
        if pulse_variant not in self.variants:
            raise ValueError(f"Unknown variant '{pulse_variant}' for slot '{self.name}'")
        if base_v not in self.variants:
            raise ValueError(f"Unknown variant '{base_v}' for slot '{self.name}'")
        period = max(0.05, float(period))
        pulse_duration = max(0.01, min(period * 0.8, float(pulse_duration)))
        t = float(start_time) + period * 0.5
        self.add_switch(float(start_time), base_v)
        while t + pulse_duration <= float(end_time):
            self.add_switch(round(t, 4), pulse_variant)
            self.add_switch(round(t + pulse_duration, 4), base_v)
            t += period

    def add_cycle(
        self,
        start_time: float,
        end_time: float,
        variants: Sequence[str] | None = None,
        interval: float = 0.14,
        rest_variant: str | None = None,
    ) -> None:
        """Cycle through `variants` every `interval` seconds from `start_time` to `end_time`."""
        cycle_list = list(variants) if variants else list(self.variants.keys())
        if not cycle_list:
            return
        for v in cycle_list:
            if v not in self.variants:
                raise ValueError(f"Unknown variant '{v}' for slot '{self.name}'")
        rest_v = rest_variant if rest_variant is not None else self.default
        step = max(0.02, float(interval))
        t = float(start_time)
        idx = 0
        while t < float(end_time) - 1e-6:
            self.add_switch(round(t, 4), cycle_list[idx % len(cycle_list)])
            t += step
            idx += 1
        self.add_switch(round(float(end_time), 4), rest_v)

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
        root: RigNode | None = None,
        limbs: Sequence[TwoJointLimb] | None = None,
        rest_pose: Pose | None = None,
        pivot: tuple[float, float] = (0.0, 0.0),
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.root = root if root is not None else RigNode(name="root", pivot=pivot)
        self.limbs: dict[str, TwoJointLimb] = {limb.name: limb for limb in (limbs or [])}
        self.rest_pose = rest_pose.copy() if rest_pose is not None else Pose()

    def add_child(
        self,
        child_or_name: RigNode | str,
        pivot: tuple[float, float] | None = None,
        drawables: Sequence[Drawable] | None = None,
        children: Sequence[RigNode] | None = None,
        angle: float = 0.0,
        offset: tuple[float, float] = (0.0, 0.0),
        scale_factor: tuple[float, float] = (1.0, 1.0),
        *args,
        **kwargs,
    ) -> RigNode:
        """Attach a child `RigNode` directly to `self.root`."""
        return self.root.add_child(
            child_or_name,
            pivot=pivot,
            drawables=drawables,
            children=children,
            angle=angle,
            offset=offset,
            scale_factor=scale_factor,
            *args,
            **kwargs,
        )

    def add_slot(
        self,
        slot_or_name: VariantSlot | str,
        variants: dict[str, Drawable | Sequence[Drawable]] | None = None,
        default: str | None = None,
        pivot: tuple[float, float] | None = None,
        *args,
        **kwargs,
    ) -> VariantSlot:
        """Attach a `VariantSlot` directly to `self.root`."""
        return self.root.add_slot(
            slot_or_name,
            variants=variants,
            default=default,
            pivot=pivot,
            *args,
            **kwargs,
        )

    def add_limb(self, limb: TwoJointLimb) -> None:
        self.limbs[limb.name] = limb

    def add_two_joint_limb(
        self,
        name: str,
        parent: RigNode | str | None = None,
        root_pivot: tuple[float, float] = (0.0, 0.0),
        length1: float = 80.0,
        length2: float = 70.0,
        bend_direction: int = 1,
        *,
        mid_pivot: tuple[float, float] | None = None,
        effector_pos: tuple[float, float] | None = None,
        effector: tuple[float, float] | None = None,
        upper_node: RigNode | str | None = None,
        lower_node: RigNode | str | None = None,
        upper_drawables: Sequence[Drawable] | None = None,
        lower_drawables: Sequence[Drawable] | None = None,
        stroke_style=None,
        sketch_style=None,
    ) -> TwoJointLimb:
        """Create or register a two-joint IK limb (`upper_node -> lower_node`) on this rig."""
        from .lines import Line

        if effector_pos is None and effector is not None:
            effector_pos = effector
        if upper_node is None and lower_node is None and isinstance(parent, str) and isinstance(root_pivot, str):
            upper_node = parent
            lower_node = root_pivot

        if upper_node is not None and lower_node is not None:
            u_name = upper_node.name if isinstance(upper_node, RigNode) else str(upper_node)
            l_name = lower_node.name if isinstance(lower_node, RigNode) else str(lower_node)
            if effector_pos is None:
                l_node_obj = self.get_node(l_name)
                effector_pos = (l_node_obj.pivot[0] + float(length2), l_node_obj.pivot[1])
            limb = TwoJointLimb(
                name=name,
                upper_node=u_name,
                lower_node=l_name,
                effector_pos=effector_pos,
                bend_direction=bend_direction,
            )
            self.add_limb(limb)
            return limb

        if parent is None:
            parent_node = self.root
        elif isinstance(parent, str):
            parent_node = self.get_node(parent)
        elif isinstance(parent, RigNode):
            parent_node = parent
        else:
            raise TypeError("parent must be a RigNode, node name string, or None")

        mid_pt = mid_pivot if mid_pivot is not None else (root_pivot[0] + float(length1), root_pivot[1])
        eff_pt = effector_pos if effector_pos is not None else (mid_pt[0] + float(length2), mid_pt[1])

        line_kwargs = {}
        if stroke_style is not None:
            line_kwargs["stroke_style"] = stroke_style
        if sketch_style is not None:
            line_kwargs["sketch_style"] = sketch_style

        u_draws = (
            list(upper_drawables)
            if upper_drawables is not None
            else [Line(root_pivot, mid_pt, **line_kwargs)]
        )
        l_draws = (
            list(lower_drawables)
            if lower_drawables is not None
            else [Line(mid_pt, eff_pt, **line_kwargs)]
        )

        u_node = parent_node.add_child(
            f"{name}_upper",
            pivot=root_pivot,
            drawables=u_draws,
        )
        l_node = u_node.add_child(
            f"{name}_lower",
            pivot=mid_pt,
            drawables=l_draws,
        )
        limb = TwoJointLimb(
            name=name,
            upper_node=u_node.name,
            lower_node=l_node.name,
            effector_pos=eff_pt,
            bend_direction=bend_direction,
        )
        self.add_limb(limb)
        return limb

    def capture_pose(self) -> Pose:
        """Return a copy of the rig's current rest pose."""
        return self.rest_pose.copy()

    def has_scheduled_variants(self) -> bool:
        """Return True if any `VariantSlot` in this rig has a non-empty time schedule."""
        return self.root.has_scheduled_variants()

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

    def point_at(
        self,
        scene: object | None,
        target: Drawable | tuple[float, float],
        limb_name: str | None = None,
        start_time: float = 0.0,
        duration: float = 0.5,
        hold: float = 1.0,
        return_duration: float = 0.45,
        return_to_rest: bool = True,
        base_pose: Pose | None = None,
        overlay: bool = False,
    ):
        """Animate `limb_name` reaching/pointing toward `target` (a `Drawable` or `(x, y)` tuple).

        Returns the created `PoseAnimation` (and registers it on `scene` if `scene` is provided).
        """
        from ..animations.pose import PoseAnimation

        if isinstance(target, Drawable):
            bbox = target.get_bbox()
            target_pt = ((bbox.min_x + bbox.max_x) / 2.0, (bbox.min_y + bbox.max_y) / 2.0)
        elif isinstance(target, (tuple, list)) and len(target) == 2:
            target_pt = (float(target[0]), float(target[1]))
        else:
            raise TypeError("point_at `target` must be a Drawable or (x, y) tuple")

        if limb_name is None:
            if not self.limbs:
                raise ValueError("CharacterRig has no registered limbs for `point_at`")
            limb_name = next(iter(self.limbs.keys()))

        start_pose = base_pose.copy() if base_pose is not None else self.rest_pose.copy()
        reached_pose = self.reach(limb_name, target_pt, base_pose=start_pose)

        st = float(start_time)
        dur = max(0.01, float(duration))
        keyframes: list[tuple[float, Pose]] = [
            (st, start_pose),
            (st + dur, reached_pose),
        ]
        if hold > 0.0:
            keyframes.append((st + dur + float(hold), reached_pose))
        if return_to_rest and return_duration > 0.0:
            keyframes.append((st + dur + max(0.0, float(hold)) + float(return_duration), start_pose))

        anim = PoseAnimation.from_keyframes(rig=self, keyframes=keyframes)
        if scene is not None and hasattr(scene, "add"):
            scene.add(anim, self, overlay=overlay)  # type: ignore[attr-defined]
        return anim

    def sync_to_audio(
        self,
        scene: object | None,
        audio_clip: object,
        start_time: float = 0.0,
        mouth_slot: str = "mouth",
        open_variant: str = "open",
        closed_variant: str = "neutral",
        smile_variant: str | None = "smile",
        head_node: str | None = "head",
        head_bob_angle: float = 2.0,
        interval: float = 0.11,
        overlay: bool = False,
    ):
        """Drive mouth `VariantSlot` lip-sync and subtle head bobbing from `audio_clip`.

        Reads word timing intervals (and WAV amplitude envelope when available) from
        `audio_clip` to schedule mouth switches on `mouth_slot`, and creates a
        `PoseAnimation` spanning the narration duration so `draw_with_pose(..., time=t)`
        is evaluated on every frame.
        """
        from ..animations.pose import PoseAnimation

        slot_node = self.root.find_node(mouth_slot)
        slot: VariantSlot | None = slot_node if isinstance(slot_node, VariantSlot) else None

        clip_dur = float(getattr(audio_clip, "duration", 0.0) or 0.0)
        words = list(getattr(audio_clip, "words", []) or [])
        if isinstance(audio_clip, dict):
            clip_dur = float(audio_clip.get("duration", clip_dur))
            words = list(audio_clip.get("words", words))
        if words and clip_dur <= 0.0:
            last_end = max(
                float(getattr(w, "end", w.get("end", 0.0) if isinstance(w, dict) else 0.0))
                for w in words
            )
            clip_dur = max(clip_dur, last_end)

        st = float(start_time)
        step = max(0.04, float(interval))

        if slot is not None:
            open_v = open_variant if open_variant in slot.variants else slot.default
            closed_v = closed_variant if closed_variant in slot.variants else slot.default
            smile_v = (
                smile_variant
                if (smile_variant is not None and smile_variant in slot.variants)
                else closed_v
            )
            slot.add_switch(st, closed_v)

            if words:
                for w in words:
                    w_start = float(getattr(w, "start", w.get("start", 0.0) if isinstance(w, dict) else 0.0))
                    w_end = float(getattr(w, "end", w.get("end", 0.0) if isinstance(w, dict) else 0.0))
                    if w_end <= w_start:
                        continue
                    slot.add_cycle(
                        start_time=st + w_start,
                        end_time=st + w_end,
                        variants=[open_v, closed_v] if open_v != closed_v else [open_v],
                        interval=step,
                        rest_variant=closed_v,
                    )
                slot.add_switch(round(st + clip_dur, 4), smile_v)
            elif clip_dur > 0.0:
                slot.add_cycle(
                    start_time=st,
                    end_time=st + clip_dur,
                    variants=[open_v, closed_v],
                    interval=step,
                    rest_variant=smile_v,
                )

        # Build subtle head-bobbing PoseAnimation across [st, st + clip_dur]
        base = self.rest_pose.copy()
        keyframes: list[tuple[float, Pose]] = [(st, base)]
        has_head = head_node is not None and self.root.find_node(head_node) is not None
        if clip_dur > 0.0:
            t_cur = st
            idx = 0
            bob_step = max(0.25, step * 3.0)
            while t_cur < st + clip_dur - 1e-6:
                p_kf = base.copy()
                if has_head and head_node is not None and abs(head_bob_angle) > 1e-6:
                    sign = 1.0 if idx % 2 == 0 else -1.0
                    p_kf.angles[head_node] = base.get_angle(head_node) + sign * float(head_bob_angle)
                keyframes.append((round(t_cur, 4), p_kf))
                t_cur += bob_step
                idx += 1
            keyframes.append((round(st + clip_dur, 4), base.copy()))
        else:
            keyframes.append((st + 0.1, base.copy()))

        anim = PoseAnimation.from_keyframes(rig=self, keyframes=keyframes)
        if scene is not None and hasattr(scene, "add"):
            scene.add(anim, self, overlay=overlay)  # type: ignore[attr-defined]
        return anim

    def draw_with_pose(self, pose: Pose | None = None, time: float | None = None) -> OpsSet:
        resolved = self.resolve_pose(pose)
        return self.root.draw_with_pose(pose=resolved, time=time)

    def draw(self, time: float | None = None) -> OpsSet:
        return self.draw_with_pose(pose=self.rest_pose, time=time)
