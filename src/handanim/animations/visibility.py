from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.animation import AnimationEvent, AnimationEventType
from ..core.draw_ops import Ops, OpsSet, OpsType

if TYPE_CHECKING:
    from ..core.drawable import Drawable


def restore_base_opacity(opsset: OpsSet) -> OpsSet:
    """Restore original opacity on an OpsSet whose opacity was scaled by a fade."""
    restored_ops: list[Ops] = []
    for op in opsset.opsset:
        if op.type in (OpsType.SET_PEN, OpsType.IMAGE) and isinstance(op.data, dict):
            modified_data = dict(op.data)
            meta = dict(op.meta) if op.meta else {}
            base_opacity = meta.get("base_opacity", op.data.get("opacity", 1.0))
            meta["base_opacity"] = base_opacity
            modified_data["opacity"] = base_opacity
            restored_ops.append(Ops(type=op.type, data=modified_data, partial=op.partial, meta=meta))
        else:
            restored_ops.append(op)
    return OpsSet(initial_set=restored_ops)


class Show(AnimationEvent):
    """Instantly makes a drawable visible at `start_time`, restoring its original opacity.

    Useful for placing hooks on screen at frame 0 (`Show(0)`) or toggling blinks,
    mouth shapes, and labels back on after `Hide` or `FadeOutAnimation`.
    """

    def __init__(
        self,
        start_time: float = 0.0,
        duration: float = 0.0,
        easing_fun=None,
        data: dict | None = None,
    ) -> None:
        super().__init__(AnimationEventType.CREATION, start_time, duration, easing_fun, data)

    def _apply(self, opsset: OpsSet, progress: float) -> OpsSet:
        return restore_base_opacity(opsset)


class Hide(AnimationEvent):
    """Instantly hides a drawable at `start_time`."""

    def __init__(
        self,
        start_time: float = 0.0,
        duration: float = 0.0,
        easing_fun=None,
        data: dict | None = None,
    ) -> None:
        super().__init__(AnimationEventType.DELETION, start_time, duration, easing_fun, data)

    def _apply(self, opsset: OpsSet, progress: float) -> OpsSet:
        return opsset


class Swap(AnimationEvent):
    """Atomically swaps `source` out and `target` in at `start_time`.

    If `duration == 0.0` (default), performs an instant `Hide(start_time)` on `source`
    and `Show(start_time)` on `target`. If `duration > 0.0`, cross-fades between them.

    Usage::

        scene.add(Swap(closed_mouth, open_mouth, 1.2))
        # or
        scene.swap(closed_mouth, open_mouth, 1.2)
    """

    def __init__(
        self,
        source: Drawable,
        target: Drawable,
        start_time: float = 0.0,
        duration: float = 0.0,
        easing_fun=None,
        data: dict | None = None,
    ) -> None:
        super().__init__(AnimationEventType.COMPOSITE, start_time, duration, easing_fun, data)
        self.source = source
        self.target = target

    def _apply(self, opsset: OpsSet, progress: float) -> OpsSet:
        return opsset


ShowAnimation = Show
HideAnimation = Hide
SwapAnimation = Swap

