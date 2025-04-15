import cairo
import numpy as np
from .draw_ops import OpsSet, OpsType


def interpolate_bezier(p0, p1, p2, p3, t):
    """De Casteljau's algorithm to split a cubic Bezier curve at t."""

    def lerp(a, b, t):
        return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t

    p01 = lerp(p0, p1, t)
    p12 = lerp(p1, p2, t)
    p23 = lerp(p2, p3, t)
    p012 = lerp(p01, p12, t)
    p123 = lerp(p12, p23, t)
    p0123 = lerp(p012, p123, t)

    return (p01, p012, p0123)


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
            if ops.partial < 1.0:
                x0, y0 = ctx.get_current_point()
                x1, y1 = ops.data[0]
                x = x0 + ops.partial * (x1 - x0)  # calculate vectors
                y = y0 + ops.partial * (y1 - y0)
                ctx.line_to(x, y)
            else:
                ctx.line_to(*ops.data[0])
        elif ops.type == OpsType.CURVE_TO:
            has_path = True
            if ops.partial < 1.0:
                p0 = ctx.get_current_point()
                p1, p2, p3 = ops.data[0], ops.data[1], ops.data[2]
                cp1, cp2, ep = interpolate_bezier(p0, p1, p2, p3, ops.partial)
                ctx.curve_to(*cp1, *cp2, *ep)
            else:
                ctx.curve_to(
                    *ops.data[0], *ops.data[1], *ops.data[2]
                )  # TODO: Need to implement De Casteljau's algorithm
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

    # at the end of everything, check if stroke or fill is needed to complete the drawing
    if has_path and mode == "stroke":
        ctx.stroke()
    elif has_path and mode == "fill":
        ctx.fill()


def cairo_surface_to_numpy(surface: cairo.ImageSurface):
    """Convert a Cairo surface to a numpy array"""
    buf = surface.get_data()
    w = surface.get_width()
    h = surface.get_height()
    a = np.ndarray(shape=(h, w, 4), dtype=np.uint8, buffer=buf)
    # Cairo is ARGB, convert to RGBA for imageio
    return a[:, :, [2, 1, 0, 3]]  # BGR → RGB with alpha
