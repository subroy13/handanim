from typing import Tuple
import cairo
import numpy as np


def slice_bezier(p0, p1, p2, p3, t):
    """
    Slice a Bezier curve at a given parameter t.

    Computes intermediate points along a cubic Bezier curve at a specified interpolation point.

    Args:
        p0 (array-like): Starting point of the Bezier curve
        p1 (array-like): First control point
        p2 (array-like): Second control point
        p3 (array-like): Ending point of the Bezier curve
        t (float): Interpolation parameter between 0 and 1

    Returns:
        list: A list of three points representing the sliced Bezier curve segment
    """
    p0, p1, p2, p3 = np.array(p0), np.array(p1), np.array(p2), np.array(p3)
    p12 = (p1 - p0) * t + p0
    p23 = (p2 - p1) * t + p1
    p34 = (p3 - p2) * t + p2
    p123 = (p23 - p12) * t + p12
    p234 = (p34 - p23) * t + p23
    p1234 = (p234 - p123) * t + p123

    return [p12, p123, p1234]


def get_bezier_points_from_quadcurve(
    p0: Tuple[float, float], q1: Tuple[float, float], q2: Tuple[float, float]
):
    """
    Convert a quadratic Bezier curve to a cubic Bezier curve representation.

    Transforms control points from a quadratic curve (with two control points)
    to an equivalent cubic curve (with three control points) using linear interpolation.

    Args:
        p0 (Tuple[float, float]): Starting point of the quadratic curve
        q1 (Tuple[float, float]): Control point of the quadratic curve
        q2 (Tuple[float, float]): Ending point of the quadratic curve

    Returns:
        Tuple[list, list, list]: Intermediate control points for the cubic Bezier curve
    """
    p1 = (1 / 3 * np.array(p0) + 2 / 3 * np.array(q1)).tolist()
    p2 = (1 / 3 * np.array(q1) + 2 / 3 * np.array(q2)).tolist()
    p3 = q2
    return p1, p2, p3


def cairo_surface_to_numpy(surface: cairo.ImageSurface):
    """
    Convert a Cairo surface to a numpy array with RGBA color channel ordering.

    Transforms the image surface data from Cairo's ARGB format to a numpy array
    with RGBA color channels, suitable for further image processing or saving.

    Args:
        surface (cairo.ImageSurface): The source Cairo image surface to convert

    Returns:
        numpy.ndarray: A numpy array representing the image with shape (height, width, 4)
            and dtype np.uint8, with color channels reordered from BGR to RGB
    """
    buf = surface.get_data()
    w = surface.get_width()
    h = surface.get_height()
    a = np.ndarray(shape=(h, w, 4), dtype=np.uint8, buffer=buf)
    # Cairo is ARGB, convert to RGBA for imageio
    return a[:, :, [2, 1, 0, 3]]  # BGR → RGB with alpha
