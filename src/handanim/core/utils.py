from typing import Tuple, List
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


def solve_quad_eqn(
    a: float, b: float, c: float, ignore_error: bool = False
) -> Tuple[float, float]:
    # solve a quadratic equation of form ax^2 + bx + c = 0
    if a == 0 and not np.isclose(b, 0):
        return (-c / b, -c / b)  # as it is linear in this case
    elif a == 0 and np.isclose(b, 0):
        return (None, None)  # no solution
    dis = b**2 - 4 * a * c
    if dis < 0 and not ignore_error:
        raise ValueError(f"The equation {a}x^2 + {b}x + {c} = 0 has complex roots")
    elif dis < 0 and ignore_error:
        return (None, None)
    else:
        return ((-b + np.sqrt(dis)) / (2 * a), (-b - np.sqrt(dis)) / (2 * a))


def get_bezier_extreme_points(
    p0: Tuple[float, float],  # initial point
    p1: Tuple[float, float],  # control point 1
    p2: Tuple[float, float],  # control point 2
    p3: Tuple[float, float],  # end point
) -> List[Tuple[float, float]]:
    # the curve p(t) = (1-t)^3 p0 + 3(1-t)^2 * t * p1 + 3 (1-t) * t^2 * p2 + t^3 p3
    # p'(t) = 3(1-t)^2 (p1 - p0) + 6(1-t)t (p2 - p1) + 3t^2 * (p3 - p2)
    points = np.array([p0, p1, p2, p3])
    a = (
        9 * (points[1] - points[0])
        - 6 * (points[2] - points[1])
        + 3 * (points[3] - points[2])
    )
    b = -6 * (points[1] - points[0]) + 6 * (points[2] - points[1])
    c = 3 * (points[1] - points[0])
    tvals = [0, 1]
    tx1, tx2 = solve_quad_eqn(a[0], b[0], c[0], ignore_error=True)
    ty1, ty2 = solve_quad_eqn(a[1], b[1], c[1], ignore_error=True)
    for tx in [tx1, tx2, ty1, ty2]:
        if tx is not None and 0 < tx < 1:
            tvals.append(tx)

    # found all t values, now compute the points
    extreme_points = []
    for t in tvals:
        p = (
            (1 - t) ** 3 * points[0]
            + 3 * (1 - t) ** 2 * t * points[1]
            + 3 * (1 - t) * t**2 * points[2]
            + t**3 * points[3]
        )
        extreme_points.append(p)

    xmin = min(p[0] for p in extreme_points)
    xmax = max(p[0] for p in extreme_points)
    ymin = min(p[1] for p in extreme_points)
    ymax = max(p[1] for p in extreme_points)

    return (xmin, xmax, ymin, ymax)


def get_line_slope_angle(p0: Tuple[float, float], p1: Tuple[float, float]) -> float:
    """
    Calculate the angle of the line segment defined by two points.

    Args:
        p0 (Tuple[float, float]): The first point (x0, y0)
        p1 (Tuple[float, float]): The second point (x1, y1)

    Returns:
        float: The angle in radians of the line segment from p0 to p1
    """
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    return np.arctan2(dy, dx)
