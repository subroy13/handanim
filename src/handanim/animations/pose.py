from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from ..core.animation import AnimationEvent, AnimationEventType
from ..core.draw_ops import OpsSet
from ..primitives.character import CharacterRig, Pose


class PoseAnimation(AnimationEvent):
    """Animates a `CharacterRig` between poses by blending joint angles, offsets, scales, and IK targets.

    Supports both two-pose transitions (`from_pose -> to_pose`) and multi-keyframe
    sequences (`keyframes=[(t0, pose0), (t1, pose1), ...]`).
    """

    def __init__(
        self,
        rig: CharacterRig | None = None,
        to_pose: Pose | None = None,
        from_pose: Pose | None = None,
        start_time: float = 0.0,
        duration: float = 0.0,
        keyframes: Sequence[tuple[float, Pose]] | None = None,
        easing_fun=None,
        data: dict | None = None,
    ) -> None:
        data_dict = dict(data) if data else {}
        if rig is None:
            rig = data_dict.get("rig")
        if to_pose is None:
            to_pose = data_dict.get("to_pose")
        if from_pose is None:
            from_pose = data_dict.get("from_pose")
        if keyframes is None:
            keyframes = data_dict.get("keyframes")

        self.rig: CharacterRig | None = rig
        self.keyframes: list[tuple[float, Pose]] | None = None

        if keyframes is not None and len(keyframes) >= 1:
            sorted_kf = sorted([(float(t), p.copy()) for t, p in keyframes], key=lambda item: item[0])
            self.keyframes = sorted_kf
            start_time = sorted_kf[0][0]
            duration = max(0.0, sorted_kf[-1][0] - sorted_kf[0][0])
            self.from_pose = sorted_kf[0][1]
            self.to_pose = sorted_kf[-1][1]
        else:
            self.from_pose = (
                from_pose.copy()
                if from_pose is not None
                else (rig.rest_pose.copy() if rig is not None else Pose())
            )
            self.to_pose = to_pose.copy() if to_pose is not None else self.from_pose.copy()

        data_dict["rig"] = self.rig
        data_dict["from_pose"] = self.from_pose
        data_dict["to_pose"] = self.to_pose
        if self.keyframes is not None:
            data_dict["keyframes"] = self.keyframes

        super().__init__(AnimationEventType.MUTATION, start_time, duration, easing_fun, data_dict)

    @classmethod
    def from_keyframes(
        cls,
        rig: CharacterRig,
        keyframes: Sequence[tuple[float, Pose]],
        easing_fun=None,
    ) -> PoseAnimation:
        """Create a `PoseAnimation` from a sequence of `(timestamp, Pose)` keyframes."""
        return cls(rig=rig, keyframes=keyframes, easing_fun=easing_fun)

    def get_pose_at_progress(self, raw_progress: float) -> tuple[Pose, float]:
        """Compute the blended `Pose` and scene timestamp at `raw_progress` in [0, 1]."""
        p = float(np.clip(raw_progress, 0.0, 1.0))
        current_time = self.start_time + p * self.duration

        if self.keyframes is not None and len(self.keyframes) >= 2:
            if current_time <= self.keyframes[0][0]:
                return self.keyframes[0][1].copy(), current_time
            if current_time >= self.keyframes[-1][0]:
                return self.keyframes[-1][1].copy(), current_time

            for i in range(len(self.keyframes) - 1):
                t0, pose0 = self.keyframes[i]
                t1, pose1 = self.keyframes[i + 1]
                if t0 <= current_time <= t1:
                    seg_dur = t1 - t0
                    seg_p = (current_time - t0) / seg_dur if seg_dur > 1e-9 else 1.0
                    eased_p = float(self.easing_fun(seg_p)) if self.easing_fun else seg_p
                    return pose0.interpolate(pose1, eased_p), current_time

        eased_p = float(self.easing_fun(p)) if self.easing_fun else p
        return self.from_pose.interpolate(self.to_pose, eased_p), current_time

    def apply(self, opsset: OpsSet, raw_progress: float) -> OpsSet:
        if self.rig is None:
            return opsset
        pose, current_time = self.get_pose_at_progress(raw_progress)
        return self.rig.draw_with_pose(pose=pose, time=current_time)

    def _apply(self, opsset: OpsSet, progress: float) -> OpsSet:
        if self.rig is None:
            return opsset
        pose = self.from_pose.interpolate(self.to_pose, progress)
        current_time = self.start_time + progress * self.duration
        return self.rig.draw_with_pose(pose=pose, time=current_time)

