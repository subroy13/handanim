from typing import Any, List, Union, Tuple, Optional
from enum import Enum
import json
import numpy as np
import cairo
from .utils import slice_bezier, get_bezier_points_from_quadcurve


class OpsType(Enum):
    SET_PEN = "set_pen"
    MOVE_TO = "move_to"
    LINE_TO = "line_to"
    CURVE_TO = "curve_to"
    QUAD_CURVE_TO = "quad_curve_to"
    CLOSE_PATH = "close_path"
    DOT = "dot"


class Ops:
    """
    Describes a drawing operation to be performed
    """

    SETUP_OPS_TYPES = [OpsType.SET_PEN, OpsType.MOVE_TO]

    def __init__(self, type: OpsType, data: Any, partial: float = 1.0):
        self.type = type
        self.data = data  # the data to use to perform draw operation
        self.partial = partial  # how much of the ops needs to be performed

    def __repr__(self):
        if isinstance(self.data, list) or isinstance(self.data, np.ndarray):
            rounded_data = [[np.round(x, 2) for x in point] for point in self.data]
        else:
            rounded_data = self.data
        return f"Ops({self.type}, {json.dumps(rounded_data)}, {self.partial})"


class OpsSet:

    def __init__(self, initial_set: List[Union[dict, Ops]] = []):
        if len(initial_set) == 0 or isinstance(initial_set[0], Ops):
            self.opsset = initial_set
        else:
            self.opsset = [Ops(**d) for d in initial_set]

    def __repr__(self):
        return "OpsSet:" + "\n\t".join([str(ops) for ops in self.opsset])

    def add(self, ops: Union[Ops, dict]):
        if isinstance(ops, dict):
            ops = Ops(**ops)
        self.opsset.append(ops)

    def extend(self, other_opsset: Any):
        if isinstance(other_opsset, OpsSet):
            for op in other_opsset.opsset:
                self.opsset.append(op)
        else:
            raise TypeError("other value is not an opsset")

    def get_bbox(self) -> Tuple[float, float, float, float]:
        """
        Get the bounding box for the opset
        """
        if len(self.opsset) == 0:
            return (0, 0, 0, 0)
        else:
            min_x = min_y = float("inf")
            max_x = max_y = float("-inf")
            for ops in self.opsset:
                # TODO: modify this calculation for curves
                data = ops.data
                if isinstance(data, list):
                    for point in data:
                        # update bounding box
                        min_x = min(min_x, point[0])
                        min_y = min(min_y, point[1])
                        max_x = max(max_x, point[0])
                        max_y = max(max_y, point[1])
            return min_x, min_y, max_x, max_y

    def get_center_of_gravity(self) -> Tuple[float, float]:
        """
        Get an approximate center of gravity of the opset
        """
        min_x, min_y, max_x, max_y = self.get_bbox()
        return (min_x + max_x) / 2, (min_y + max_y) / 2

    def get_last_ops(
        self, start_index: int = 0
    ) -> Tuple[Optional[float], Optional[Ops]]:
        """
        Get valid last and second last ops
        """
        if start_index >= len(self.opsset):
            return None, None
        for index, ops in enumerate(self.opsset[::-1][start_index:]):
            if ops.type in {
                OpsType.MOVE_TO,
                OpsType.LINE_TO,
                OpsType.CURVE_TO,
                OpsType.QUAD_CURVE_TO,
            }:
                return index, ops
        return None, None

    def get_current_point(self):
        """
        Given a opsset, get the current point of the drawing from last operation
        """
        if len(self.opsset) == 0:
            return (0, 0)
        else:
            last_index, last_op = self.get_last_ops()
            if last_op is None:
                return (0, 0)

            second_last_op = self.get_last_ops(last_index + 1)[1]
            if second_last_op is None:
                return last_op.data[0]
            if last_op.type == OpsType.MOVE_TO:
                return last_op.data[0]
            elif last_op.type == OpsType.LINE_TO:
                if last_op.partial < 1:
                    x0, y0 = second_last_op.data[0]
                    x1, y1 = last_op.data[0]
                    x = x0 + last_op.partial * (x1 - x0)  # calculate vectors
                    y = y0 + last_op.partial * (y1 - y0)
                    return (x, y)
                else:
                    return last_op.data[0]
            elif last_op.type == OpsType.CURVE_TO:
                if last_op.partial < 1:
                    p0 = second_last_op.data[0]
                    p1, p2, p3 = last_op.data[0], last_op.data[1], last_op.data[2]
                    cp1, cp2, ep = slice_bezier(p0, p1, p2, p3, last_op.partial)
                    return ep
                else:
                    return last_op.data[-1]
            elif last_op.type == OpsType.QUAD_CURVE_TO:
                if last_op.partial < 1:
                    p0 = second_last_op.data[0]
                    q1, q2 = last_op.data[0], last_op.data[1]
                    p1, p2, p3 = get_bezier_points_from_quadcurve(p0, q1, q2)
                    cp1, cp2, ep = slice_bezier(p0, p1, p2, last_op.partial)
                    return ep
                else:
                    return last_op.data[-1]

    def translate(self, offset_x: float, offset_y: float):
        """
        Translates every operation of the opsset by the (offset_x, offset_y) amount
        in relative to its center of gravity
        """
        new_ops = []
        for ops in self.opsset:
            if isinstance(ops.data, list):
                # ops.data is list means, everything is a point
                new_data = [(x + offset_x, y + offset_y) for x, y in ops.data]
                new_ops.append(Ops(ops.type, new_data, ops.partial))
            else:
                new_ops.append(ops)  # keep same ops
        self.opsset = new_ops

    def scale(self, scale_x: float, scale_y: Optional[float] = None):
        """
        Scales every operation of the opsset by the (scale_x, scale_y) amount
        in relative to its center of gravity
        """
        if scale_y is None:
            scale_y = scale_x

        # first translate so that center of gravity is at (0, 0)
        center_of_gravity = self.get_center_of_gravity()

        # now apply scaling
        new_ops = []
        for ops in self.opsset:
            if isinstance(ops.data, list):
                # ops.data is list means, everything is a point
                new_data = [
                    (
                        center_of_gravity[0] + scale_x * (x - center_of_gravity[0]),
                        center_of_gravity[1] + scale_y * (y - center_of_gravity[1]),
                    )
                    for x, y in ops.data
                ]
                new_ops.append(Ops(ops.type, new_data, ops.partial))
            else:
                new_ops.append(ops)  # keep same ops for set pen type operations
        self.opsset = new_ops  # update the ops list

    def rotate(self, angle: float):
        """
        Rotates every operation of the opsset by the angle amount of degrees
        in relative to its center of gravity
        """
        # first translate so that center of gravity is at (0, 0)
        center_of_gravity = self.get_center_of_gravity()
        rotation_values = [np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle))]

        new_ops = []
        for ops in self.opsset:
            if isinstance(ops.data, list):
                # ops.data is list means, everything is a point
                new_data = [
                    (
                        center_of_gravity[0]
                        + rotation_values[0] * (x - center_of_gravity[0])
                        - rotation_values[1] * (y - center_of_gravity[1]),
                        center_of_gravity[1]
                        + rotation_values[1] * (x - center_of_gravity[0])
                        + rotation_values[0] * (y - center_of_gravity[1]),
                    )
                    for x, y in ops.data
                ]  # performs multiplication of rotation matrix explcitly
                new_ops.append(Ops(ops.type, new_data, ops.partial))
            else:
                new_ops.append(ops)  # keep same ops for set pen type operations
        self.opsset = new_ops  # update the ops list

    def render(self, ctx: cairo.Context, initial_mode: str = "stroke"):
        """
        Renders the opset on the cairo context
        """
        mode = initial_mode
        has_path = False  # initially there is no path
        for ops in self.opsset:
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
                    cp1, cp2, ep = slice_bezier(p0, p1, p2, p3, ops.partial)
                    ctx.curve_to(*cp1, *cp2, *ep)
                else:
                    ctx.curve_to(*ops.data[0], *ops.data[1], *ops.data[2])
            elif ops.type == OpsType.QUAD_CURVE_TO:
                has_path = True
                q1, q2 = ops.data[0], ops.data[1]
                p0 = ctx.get_current_point()
                p1, p2, p3 = get_bezier_points_from_quadcurve(p0, q1, q2)
                if ops.partial < 1.0:
                    cp1, cp2, ep = slice_bezier(p0, p1, p2, p3, ops.partial)
                    ctx.curve_to(*cp1, *cp2, *ep)
                else:
                    ctx.curve_to(*p1, *p2, *p3)
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
            elif ops.type == OpsType.DOT:
                has_path = True
                x, y = ops.data.get("center", (0, 0))
                ctx.move_to(x, y)
                ctx.arc(x, y, ops.data.get("radius", 1), 0, 2 * np.pi)
            else:
                raise NotImplementedError("Unknown operation type")

        # at the end of everything, check if stroke or fill is needed to complete the drawing
        if has_path and mode == "stroke":
            ctx.stroke()
        elif has_path and mode == "fill":
            ctx.fill()
