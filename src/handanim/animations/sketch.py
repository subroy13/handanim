import numpy as np
from ..core.draw_ops import OpsSet, Ops, OpsType
from ..core.animation import AnimationEvent, AnimationEventType
from ..core.styles import FillStyle
from ..primitives.ellipse import GlowDot


class SketchAnimation(AnimationEvent):
    """
    A class representing a sketch animation event.
    """

    def __init__(self, start_time=0, duration=0, easing_fun=None, data=None):
        super().__init__(
            AnimationEventType.CREATION, start_time, duration, easing_fun, data
        )
        if data is None:
            data = {}
        self.wait_before_fill = data.get(
            "wait_before_fill", 0
        )  # seconds to wait before starting fill animation, if any
        self.wait_before_fill = min(
            self.wait_before_fill, self.duration / 2
        )  # maximum wait is half of the duration

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
            draw_progress = progress * self.duration / draw_end_time
            n_active = int(draw_progress * draw_ops_count)
        elif progress * self.duration <= fill_start_time:
            # drawing is completed, but filling is not started yet
            n_active = draw_ops_count
        else:
            # filling is in progress
            fill_progress = (progress * self.duration - fill_start_time) / (
                self.duration - fill_start_time
            )
            n_active = draw_ops_count + int(fill_progress * fill_ops_count)

        # create a new opsset with the partial ops
        counter = 0
        last_op = None
        new_opsset = OpsSet(initial_set=[])  # initially start with blank opsset
        for op in base_ops:
            if op.type not in Ops.SETUP_OPS_TYPES and counter < n_active:
                new_opsset.add(op)
                counter += 1
            elif counter < n_active:
                # other operations keep adding, but don't increase counter
                new_opsset.add(op)
            else:
                last_op = op  # the last operation for which it stopped
                break
        if last_op is not None and (progress * total_ops_count - n_active) > 0:
            # need to calculate it partially
            new_opsset.add(
                Ops(
                    type=last_op.type,
                    data=last_op.data,
                    partial=progress * total_ops_count - n_active,
                )
            )
        return new_opsset

    def apply(self, opsset: OpsSet, progress: float):
        """
        Apply the animation to the given opsset.
        """
        new_opsset = OpsSet(initial_set=[])
        if progress > 0:
            sketching_opssets = self.get_partial_sketch(opsset, progress)
            new_opsset.extend(sketching_opssets)
            # now we can optionally add a glowing dot for the sketching operation
            if self.data.get("glowing_dot"):
                glow_dot_data = self.data.get("glowing_dot")
                if not isinstance(glow_dot_data, dict):
                    glow_dot_data = {}
                # we need to draw glowing dot
                cx, cy = (
                    sketching_opssets.get_current_point()
                )  # get the current point based on sketching

                breathing_factor = 1 + 0.05 * np.sin(
                    2 * np.pi * progress * glow_dot_data.get("frequency", 5)
                )  # have a subtle breathing effect to increase or decrease glow
                dot = GlowDot(
                    center=(cx, cy),
                    radius=glow_dot_data.get("radius", 5) * breathing_factor,
                    fill_style=FillStyle(
                        color=glow_dot_data.get("color", (0.5, 0.5, 0.5))
                    ),
                )
                new_opsset.extend(dot.draw())  # add this dot at the end of current path
        else:
            # progress is 0, so nothing should be drawn
            pass
        return new_opsset
