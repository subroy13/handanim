import cairo
import numpy as np
from .draw_ops import OpsSet, OpsType


def render_opsset(
    ctx: cairo.Context,
    opsset: OpsSet,
    initial_mode: str = "stroke",  # initialize with stroke mode
):
    """
    Applies a list of opssets on to the cairo context
    for drawing
    """
    mode = initial_mode
    has_path = False  # initially there is no path
    for ops in opsset.opsset:
        if ops.type == OpsType.MOVE_TO:
            ctx.move_to(*ops.data[0])
        elif ops.type == OpsType.LINE_TO:
            has_path = True
            ctx.line_to(*ops.data[0])
        elif ops.type == OpsType.CURVE_TO:
            has_path = True
            ctx.curve_to(*ops.data[0], *ops.data[1], *ops.data[2])
        elif ops.type == OpsType.CLOSE_PATH:
            has_path = True
            ctx.close_path()
        elif ops.type == OpsType.SET_PEN:
            if has_path and mode == "stroke":
                ctx.stroke()  # handle last stroke / fill performed
            elif has_path and mode == "fill":
                ctx.fill()
            has_path = False  # reset the path for this new pen setup
            mode = ops.data.get(
                "mode", "stroke"
            )  # update the mode based on current ops
            if ops.data.get("color"):
                r, g, b = ops.data.get("color")
                ctx.set_source_rgba(r, g, b, ops.data.get("opacity", 1))
            if ops.data.get("width"):
                ctx.set_line_width(ops.data.get("width"))
        else:
            raise NotImplementedError("Unknown operation type")


def cairo_surface_to_numpy(surface: cairo.ImageSurface):
    """Convert a Cairo surface to a numpy array"""
    buf = surface.get_data()
    w = surface.get_width()
    h = surface.get_height()
    a = np.ndarray(shape=(h, w, 4), dtype=np.uint8, buffer=buf)
    # Cairo is ARGB, convert to RGBA for imageio
    return a[:, :, [2, 1, 0, 3]]  # BGR → RGB with alpha
