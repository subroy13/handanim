import numpy as np

from ..core.animation import AnimationEvent, AnimationEventType
from ..core.draw_ops import Ops, OpsSet, OpsType
from ..core.styles import FillStyle
from ..primitives.ellipse import GlowDot


class SketchAnimation(AnimationEvent):
    """
    A class representing a sketch animation event that progressively renders drawing operations.

    This animation supports partial rendering of drawing and fill operations with configurable timing
    and optional glowing dot effects. It allows for smooth, incremental visualization of drawing sequences.

    Attributes:
        wait_before_fill (float): Delay in seconds before starting fill animation, capped at half the total duration.
        sound (bool | None): Per-animation override to turn sketch drawing sound on (`True`) or off (`False`).
            When `None` (default), inherits the scene's `sketch_sound` setting.
        sound_volume (float | None): Optional per-animation volume multiplier (`0.0` to `1.0`) for the sketch sound.
        sound_style (str | None): Optional per-animation sound style (`"chalk"` or `"pen"`).

    Methods:
        get_partial_sketch: Calculates a partial OpsSet representing the current sketching progress.
        apply: Applies the sketch animation to a given OpsSet at a specific progress point.
        set_sound: Enables, disables, or adjusts the volume/style of the sketch sound for this event.
    """

    def __init__(
        self,
        start_time: float = 0.0,
        duration: float = 0.0,
        easing_fun=None,
        data: dict | None = None,
        *,
        wait_before_fill: float | None = None,
        glowing_dot: bool | dict | None = None,
        sound: bool | float | None = None,
        sound_volume: float | None = None,
        sound_style: str | None = None,
    ):
        merged_data = dict(data) if data is not None else {}
        if wait_before_fill is not None:
            merged_data["wait_before_fill"] = float(wait_before_fill)
        if glowing_dot is not None:
            merged_data["glowing_dot"] = glowing_dot
        if sound is not None:
            if isinstance(sound, (int, float)) and not isinstance(sound, bool):
                if float(sound) <= 0.0:
                    merged_data["sound"] = False
                    if sound_volume is None:
                        merged_data["sound_volume"] = 0.0
                else:
                    merged_data["sound"] = True
                    if sound_volume is None:
                        merged_data["sound_volume"] = float(sound)
            else:
                merged_data["sound"] = bool(sound)
        if sound_volume is not None:
            vol = max(0.0, float(sound_volume))
            merged_data["sound_volume"] = vol
            if vol <= 0.0 and "sound" not in merged_data:
                merged_data["sound"] = False
        if sound_style is not None:
            merged_data["sound_style"] = str(sound_style)

        super().__init__(AnimationEventType.CREATION, start_time, duration, easing_fun, merged_data)
        self.wait_before_fill = merged_data.get(
            "wait_before_fill", 0
        )  # seconds to wait before starting fill animation, if any
        self.wait_before_fill = min(self.wait_before_fill, self.duration / 2)  # maximum wait is half of the duration
        self.sound: bool | None = merged_data.get("sound", None)
        self.sound_volume: float | None = (
            float(merged_data["sound_volume"]) if merged_data.get("sound_volume") is not None else None
        )
        self.sound_style: str | None = (
            str(merged_data["sound_style"]) if merged_data.get("sound_style") is not None else None
        )

    def set_sound(
        self,
        enabled: bool = True,
        volume: float | None = None,
        style: str | None = None,
    ) -> "SketchAnimation":
        """Turn sketch sound on or off or adjust its volume/style for this animation event."""
        self.sound = bool(enabled)
        self.data["sound"] = self.sound
        if volume is not None:
            self.sound_volume = max(0.0, float(volume))
            self.data["sound_volume"] = self.sound_volume
            if self.sound_volume <= 0.0:
                self.sound = False
                self.data["sound"] = False
        if style is not None:
            self.sound_style = str(style)
            self.data["sound_style"] = self.sound_style
        return self

    def get_partial_sketch(self, opsset: OpsSet, progress: float) -> OpsSet:
        """
        Calculate a partial OpsSet representing the sketching progress of an operation set.

        Args:
            OpsSet: The full drawn opsset on which to apply partial sketching
            progress (float): The progress of sketching, ranging from 0.0 to 1.0.

        Returns:
            OpsSet: A new OpsSet containing the operations up to the specified progress point,
                    with the last operation potentially being partially completed.
        """
        base_ops = opsset.opsset
        draw_ops_count = 0  # number of opssets used for drawing
        fill_ops_count = 0  # number of opssets used for filling
        fill_mode = False
        for op in base_ops:
            if op.type not in Ops.SETUP_OPS_TYPES:
                if fill_mode:
                    fill_ops_count += 1
                else:
                    draw_ops_count += 1
            elif op.type is OpsType.METADATA and op.data.get("drawing_mode") == "fill":
                fill_mode = True
        total_ops_count = draw_ops_count + fill_ops_count  # total count of drawing ops

        # calculate per ops how much seconds is assigned
        per_op_time = (self.duration - self.wait_before_fill) / total_ops_count

        # calculate the drawing and filling times
        draw_end_time = per_op_time * draw_ops_count
        fill_start_time = draw_end_time + self.wait_before_fill

        # based on progress, find out the total number of ops to be drawn
        if progress * self.duration <= draw_end_time:
            # drawing is not completed yet
            draw_progress = progress * self.duration / draw_end_time if draw_end_time > 0 else 1.0
            exact_active = draw_progress * draw_ops_count
            n_active = int(exact_active)
            partial_amount = exact_active - n_active
        elif progress * self.duration <= fill_start_time:
            # drawing is completed, but filling is not started yet
            n_active = draw_ops_count
            partial_amount = 0.0
        else:
            # filling is in progress
            fill_progress = (progress * self.duration - fill_start_time) / (self.duration - fill_start_time)
            exact_active = draw_ops_count + fill_progress * fill_ops_count
            n_active = int(exact_active)
            partial_amount = exact_active - n_active

        # create a new opsset with the partial ops
        counter = 0
        last_op = None
        new_opsset = OpsSet(initial_set=[])  # initially start with blank opsset
        for op in base_ops:
            if op.type not in Ops.SETUP_OPS_TYPES:
                if counter < n_active:
                    new_opsset.add(op)
                    counter += 1
                else:
                    last_op = op  # the last operation for which it stopped
                    break
            elif counter < n_active or (counter == n_active and partial_amount > 0):
                # other operations keep adding, but don't increase counter
                new_opsset.add(op)
            else:
                break
        if last_op is not None and partial_amount > 0:
            # need to calculate it partially
            new_opsset.add(
                Ops(
                    type=last_op.type,
                    data=last_op.data,
                    partial=partial_amount,
                    meta=last_op.meta,
                )
            )
        return new_opsset

    def _apply(self, opsset: OpsSet, progress: float):
        """
        Apply the sketch animation to an operation set with a given progress.

        This method progressively renders the operations in the opsset based on the current animation progress,
        with an optional glowing dot effect to highlight the current drawing point.

        Args:
            opsset (OpsSet): The set of operations to animate
            progress (float): Animation progress from 0.0 to 1.0

        Returns:
            OpsSet: A new operation set with partially or fully rendered operations
        """
        new_opsset = OpsSet(initial_set=[])
        if progress > 0:
            sketching_opssets = self.get_partial_sketch(opsset, progress)
            new_opsset.extend(sketching_opssets)
            # now we can optionally add a glowing dot for the sketching operation
            if self.data.get("glowing_dot") and progress < 1:
                # the glowing dot should disappear at the end of the sketch
                glow_dot_data = self.data.get("glowing_dot")
                if not isinstance(glow_dot_data, dict):
                    glow_dot_data = {}
                # we need to draw glowing dot
                cx, cy = sketching_opssets.get_current_point()  # get the current point based on sketching

                breathing_factor = 1 + 0.05 * np.sin(
                    2 * np.pi * progress * glow_dot_data.get("frequency", 5)
                )  # have a subtle breathing effect to increase or decrease glow
                dot = GlowDot(
                    center=(cx, cy),
                    radius=glow_dot_data.get("radius", 5) * breathing_factor,
                    fill_style=FillStyle(color=glow_dot_data.get("color", (0.5, 0.5, 0.5))),
                )
                new_opsset.extend(dot.draw())  # add this dot at the end of current path
        else:
            # progress is 0, so nothing should be drawn
            pass
        return new_opsset
