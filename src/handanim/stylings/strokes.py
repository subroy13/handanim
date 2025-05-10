from typing import Tuple, List
import numpy as np

from ..core.draw_ops import Ops, OpsSet, OpsType
from ..core.styles import StrokePressure


def apply_stroke_pressure(
    opsset: OpsSet,
    stroke_pressure: StrokePressure,
) -> OpsSet:
    """
    This function applies different pressure to the strokes
    by interleaving different set pen operations with varying
    pressure values.
    """

    # create a pressure profile based on the stroke style
    def pressure_profile(t, min_val=0.75, max_val=1.25):
        """
        Return a pressure profile value based on the progress of the curve
        """
        mid = (min_val + max_val) / 2
        scale = (max_val - min_val) / 2
        return mid + scale * np.sin(2 * t * np.pi)  # smooth in-out

    new_opsset = OpsSet(initial_set=[])
    current_pen_ops = None
    n_opsset = len(opsset.opsset)
    for i, ops in enumerate(opsset.opsset):
        if ops.type == OpsType.SET_PEN:
            current_pen_ops = ops

        if i % np.random.randint(3, 6) == 0:
            # apply pressure to the current pen operation
            if stroke_pressure == StrokePressure.CONSTANT:
                scale_width, scale_opacity = 1, 1
            else:
                scale_width = pressure_profile(i / n_opsset, min_val=0.5, max_val=2)
                if stroke_pressure == StrokePressure.PROPORTIONAL:
                    scale_opacity = pressure_profile(
                        i / n_opsset, min_val=0.7, max_val=1
                    )
                else:
                    scale_opacity = pressure_profile(
                        i / n_opsset, min_val=1, max_val=0.7
                    )  # reverse opacity
            if current_pen_ops is not None:
                current_pen_data = current_pen_ops.data
                current_pen_data["width"] = (
                    current_pen_data.get("width", 1) * scale_width
                )
                current_pen_data["opacity"] = (
                    current_pen_data.get("opacity", 1) * scale_opacity
                )
                new_opsset.add(Ops(type=OpsType.SET_PEN, data=current_pen_data))

        new_opsset.add(ops)  # add the current ops anyway
    return new_opsset


def apply_strokes_gradient(
    opsset: OpsSet,
    start_color: Tuple[float, float, float],
    end_color: Tuple[float, float, float],
) -> OpsSet:
    """
    This function applies gradient coloring to the strokes
    by interleaving different set pen operations with varying
    color values.
    """

    def interpolate_color(
        color_start: Tuple[float, float, float],
        color_end: Tuple[float, float, float],
        t: float,
    ):
        return tuple((1 - t) * a + t * b for a, b in zip(color_start, color_end))

    new_opsset = OpsSet(initial_set=[])
    return new_opsset
