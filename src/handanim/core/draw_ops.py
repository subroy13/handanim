from typing import Any, List, Union, Tuple, Optional, Dict
from enum import Enum
import json
import numpy as np
import cairo
import tempfile
import webbrowser
from .utils import (
    slice_bezier,
    get_bezier_points_from_quadcurve,
    get_bezier_extreme_points,
)
from .viewport import Viewport


class OpsType(Enum):
    SET_PEN = "set_pen"
    MOVE_TO = "move_to"
    METADATA = "metadata"
    # this is a dummy opsset that does nothing except hold some metadata
    LINE_TO = "line_to"
    CURVE_TO = "curve_to"
    QUAD_CURVE_TO = "quad_curve_to"
    CLOSE_PATH = "close_path"
    DOT = "dot"


class Ops:
    """
    Represents a drawing operation to be performed in the animation system.

    Attributes:
        SETUP_OPS_TYPES (List[OpsType]): Types of operations considered setup operations.
        type (OpsType): The type of drawing operation.
        data (Any): The data used to perform the drawing operation.
        partial (float, optional): Fraction of the operation to be performed, defaults to 1.0.
    """

    SETUP_OPS_TYPES = [OpsType.SET_PEN, OpsType.MOVE_TO, OpsType.METADATA]

    def __init__(self, type: OpsType, data: Any, partial: float = 1.0, meta: Optional[Dict] = None):
        self.type = type
        self.data = data  # the data to use to perform draw operation
        self.partial = partial  # how much of the ops needs to be performed
        self.meta = meta

    def __repr__(self):
        if isinstance(self.data, list) or isinstance(self.data, np.ndarray):
            rounded_data = [[np.round(x, 2) for x in point] for point in self.data]
        else:
            rounded_data = self.data
        return f"Ops({self.type}, {json.dumps(rounded_data)}, {self.partial})"


class OpsSet:
    """
    Represents a collection of drawing operations with methods for manipulation and rendering.

    Provides functionality to:
    - Add, extend, and manage a list of drawing operations
    - Calculate bounding box and center of gravity
    - Perform transformations like translation, scaling, and rotation
    - Render operations to a Cairo context

    Attributes:
        opsset (List[Ops]): A list of drawing operations to be performed.
    """

    def __init__(self, initial_set: List[Dict | Ops] = []):
        converted_set: List[Ops] = []
        for ops in initial_set:
            if isinstance(ops, dict):
                converted_set.append(Ops(**ops))
            else:
                converted_set.append(ops)
        self.opsset = converted_set

    def __repr__(self):
        if len(self.opsset) <= 10:
            return "OpsSet:" + "\n\t".join([str(ops) for ops in self.opsset])
        else:
            return (
                "OpsSet:\n"
                + "\n".join([str(ops) for ops in self.opsset[:5]])
                + f"\n\t(... {len(self.opsset) - 10} more rows)\n"
                + "\n".join([str(ops) for ops in self.opsset[-5:]])
            )

    def add_meta(self, meta: dict = {}):
        for ops in self.opsset:
            if ops.meta is None:
                ops.meta = meta
            ops.meta.update(meta)  # merge the key and values

    def filter_by_meta_query(self, meta_key: str, meta_value: Any):
        new_opsset = []
        for ops in self.opsset:
            if ops.meta is None:
                continue
            if ops.meta.get(meta_key) == meta_value:
                new_opsset.append(ops)
        return OpsSet(new_opsset)

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
        Calculate the bounding box that encompasses all points in the operations set.

        Returns:
            A tuple of (min_x, min_y, max_x, max_y) representing the coordinates
            of the bounding box. Returns (0, 0, 0, 0) if the operations set is empty.

        Note:
            Currently supports only list-type point data. Curve calculations
            are not fully implemented.
        """
        if len(self.opsset) == 0:
            return (0, 0, 0, 0)
        else:
            min_x = min_y = float("inf")
            max_x = max_y = float("-inf")
            current_point = (0, 0)
            for ops in self.opsset:
                if ops.type in [OpsType.CURVE_TO, OpsType.QUAD_CURVE_TO]:
                    p0 = current_point  # current point is the start of the curve
                    if ops.type == OpsType.CURVE_TO:
                        p1, p2, p3 = ops.data
                    elif ops.type == OpsType.QUAD_CURVE_TO:
                        q1, q2 = ops.data
                        p1, p2, p3 = get_bezier_points_from_quadcurve(p0, q1, q2)
                    current_point = p3  # update current point to end of curve
                    # now get the range
                    xmin, xmax, ymin, ymax = get_bezier_extreme_points(p0, p1, p2, p3)
                    min_x = min(min_x, xmin)
                    max_x = max(max_x, xmax)
                    min_y = min(min_y, ymin)
                    max_y = max(max_y, ymax)
                else:
                    data = ops.data
                    if isinstance(data, list):
                        for point in data:
                            # update current point
                            current_point = point

                            # update bounding box
                            min_x = min(min_x, point[0])
                            min_y = min(min_y, point[1])
                            max_x = max(max_x, point[0])
                            max_y = max(max_y, point[1])
            return min_x, min_y, max_x, max_y

    def get_center_of_gravity(self) -> Tuple[float, float]:
        """
        Calculate the approximate geometric center of the operations set.

        Returns:
            A tuple of (x, y) coordinates representing the center point,
            computed as the midpoint of the bounding box.
        """
        min_x, min_y, max_x, max_y = self.get_bbox()
        return (min_x + max_x) / 2, (min_y + max_y) / 2

    def get_last_ops(self, start_index: int = 0) -> Tuple[Optional[float], Optional[Ops]]:
        """
        Retrieve the last valid operation from the operations set.

        Args:
            start_index (int, optional): Starting index for searching backwards. Defaults to 0.

        Returns:
            Tuple[Optional[float], Optional[Ops]]: A tuple containing the index and the last valid operation.
            Returns (None, None) if no valid operation is found.

        Note:
            Valid operations include MOVE_TO, LINE_TO, CURVE_TO, and QUAD_CURVE_TO.
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
        Retrieves the current drawing point from the last operation in the operations set.

        Returns:
            A tuple (x, y) representing the current drawing point, considering partial operations
            and different types of drawing operations (move, line, curve, quadratic curve).
            Returns (0, 0) if no valid point can be determined.
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
        Translates all operations in the opsset by a specified (x, y) offset.

        Applies the translation relative to the current center of gravity of the operations.
        Modifies the operations in-place by adding the offset to each point's coordinates.
        Non-point operations (like set pen type) are preserved without modification.

        Args:
            offset_x (float): The x-axis translation amount
            offset_y (float): The y-axis translation amount
        """
        new_ops = []
        for ops in self.opsset:
            if isinstance(ops.data, list):
                # ops.data is list means, everything is a point
                new_data = [(x + offset_x, y + offset_y) for x, y in ops.data]
                new_ops.append(Ops(ops.type, new_data, ops.partial, ops.meta))
            else:
                new_ops.append(ops)  # keep same ops
        self.opsset = new_ops

    def scale(self, scale_x: float, scale_y: Optional[float] = None):
        """
        Scales the operations in the opsset relative to its center of gravity.

        Applies uniform or non-uniform scaling to all point-based operations. If only scale_x is provided,
        the scaling is uniform in both x and y directions. The scaling is performed relative to the
        current center of gravity of the operations.

        Args:
            scale_x (float): The scaling factor for the x-axis.
            scale_y (float, optional): The scaling factor for the y-axis.
                                        Defaults to the same value as scale_x for uniform scaling.
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
                new_ops.append(Ops(ops.type, new_data, ops.partial, ops.meta))
            else:
                new_ops.append(ops)  # keep same ops for set pen type operations
        self.opsset = new_ops  # update the ops list

    def rotate(self, angle: float, center_of_rotation: Optional[Tuple[float, float]] = None):
        """
        Rotates the operations in the opsset by a specified angle around its center of gravity.

        Applies a rotation transformation to all point-based operations relative to the current
        center of gravity. The rotation is performed in degrees and uses a standard 2D rotation matrix.

        Args:
            angle (float): The rotation angle in degrees. Positive values rotate counterclockwise.
        """
        # first translate so that center of gravity is at (0, 0)
        if center_of_rotation is None:
            center_of_rotation = self.get_center_of_gravity()
        rotation_values = [np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle))]

        new_ops = []
        for ops in self.opsset:
            if isinstance(ops.data, list):
                # ops.data is list means, everything is a point
                new_data = [
                    (
                        center_of_rotation[0]
                        + rotation_values[0] * (x - center_of_rotation[0])
                        - rotation_values[1] * (y - center_of_rotation[1]),
                        center_of_rotation[1]
                        + rotation_values[1] * (x - center_of_rotation[0])
                        + rotation_values[0] * (y - center_of_rotation[1]),
                    )
                    for x, y in ops.data
                ]  # performs multiplication of rotation matrix explcitly
                new_ops.append(Ops(ops.type, new_data, ops.partial, ops.meta))
            else:
                new_ops.append(ops)  # keep same ops for set pen type operations
        self.opsset = new_ops  # update the ops list

    def render(self, ctx: cairo.Context, initial_mode: str = "stroke"):
        """
        Renders the operation set on a Cairo graphics context.

        This method iterates through a series of drawing operations and applies them to the
        provided Cairo context. It supports various operation types including move, line,
        curve, and quadratic curve drawing, as well as path closing and pen/style configuration.

        Args:
            ctx (cairo.Context): The Cairo graphics context to render operations on.
            initial_mode (str, optional): The initial rendering mode, either "stroke" or "fill".
                Defaults to "stroke".

        Raises:
            NotImplementedError: If an unsupported operation type is encountered.
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
                mode = ops.data.get("mode", "stroke")  # update the mode based on current ops
                if ops.data.get("color"):
                    r, g, b = ops.data.get("color")
                    ctx.set_source_rgba(r, g, b, ops.data.get("opacity", 1))
                if ops.data.get("width"):
                    ctx.set_line_width(ops.data.get("width"))
            elif ops.type == OpsType.METADATA:
                pass  # ignore metadata ops
            elif ops.type == OpsType.DOT:
                has_path = True
                x, y = ops.data.get("center", (0, 0))
                ctx.move_to(x, y)
                ctx.arc(x, y, ops.data.get("radius", 1), 0, 2 * np.pi)
            else:
                raise NotImplementedError(f"Unknown operation type {ops.type}")

        # at the end of everything, check if stroke or fill is needed to complete the drawing
        if has_path and mode == "stroke":
            ctx.stroke()
        elif has_path and mode == "fill":
            ctx.fill()

    def quick_view(
        self,
        width: int = 800,
        height: int = 600,
        background_color: Tuple[float, float, float] = (1, 1, 1),
        block: bool = True,
    ):
        """
        Renders the OpsSet to a temporary SVG file and opens it in a web browser for quick viewing.

        This is a utility for debugging. It automatically creates a viewport that fits the content.

        Args:
            width (int): The width of the output SVG image.
            height (int): The height of the output SVG image.
            background_color (Tuple[float, float, float]): The RGB background color. Defaults to white.
            block (bool): If True, the script will pause execution until Enter is pressed in the console.
        """
        if not self.opsset:
            print("Cannot quick_view an empty OpsSet.")
            return

        with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False, encoding="utf-8") as tmp_file:
            tmp_filename = tmp_file.name

        # Get bounding box to create a viewport that fits the content
        viewport = Viewport(
            world_xrange=(0, 1000 * (width / height)),
            world_yrange=(0, 1000),
            screen_width=width,
            screen_height=height,
            margin=20,
        )

        with cairo.SVGSurface(tmp_filename, width, height) as surface:
            ctx = cairo.Context(surface)
            ctx.set_source_rgb(*background_color)
            ctx.paint()
            viewport.apply_to_context(ctx)
            self.render(ctx)
            surface.finish()

        webbrowser.open_new_tab(f"file://{tmp_filename}")

        if block:
            print(f"Quick view opened in browser. Press Enter in this console to continue...")
            input()
