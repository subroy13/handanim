from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from ..core.drawable import Drawable, DrawableGroup
from ..core.draw_ops import BoundingBox, Ops, OpsSet, OpsType
from ..core.styles import FillStyle, SketchStyle, StrokeStyle
from ..core.utils import get_line_slope_angle
from .arrow import Arrow
from .lines import Line, LinearPath
from .polygons import Polygon, Rectangle
from .text import Text

_VALID_SIDES = ("top", "bottom", "left", "right", "center")


class FlowchartNode(DrawableGroup):
    """
    A flowchart process node: a Rectangle with a centered Text label.

    position is the center of the node in world coordinates.
    """

    def __init__(
        self,
        label: str,
        position: Tuple[float, float],
        size: Tuple[float, float] = (100.0, 50.0),
        font_size: int = 12,
        stroke_style: StrokeStyle = StrokeStyle(),
        sketch_style: SketchStyle = SketchStyle(),
        fill_style: Optional[FillStyle] = None,
        **kwargs,
    ):
        cx, cy = position
        w, h = size
        self.label = label
        self.position = position
        self.size = size

        rect = Rectangle(
            top_left=(cx - w / 2, cy - h / 2),
            width=w,
            height=h,
            stroke_style=stroke_style,
            sketch_style=sketch_style,
            fill_style=fill_style,
        )
        text = Text(
            text=label,
            position=position,
            font_size=font_size,
            stroke_style=stroke_style,
            sketch_style=sketch_style,
        )
        super().__init__(
            elements=[rect, text],
            grouping_method="parallel",
            stroke_style=stroke_style,
            sketch_style=sketch_style,
            **kwargs,
        )

    def get_anchor(self, side: str = "center") -> Tuple[float, float]:
        cx, cy = self.position
        w, h = self.size
        anchors = {
            "center": (cx, cy),
            "top": (cx, cy - h / 2),
            "bottom": (cx, cy + h / 2),
            "left": (cx - w / 2, cy),
            "right": (cx + w / 2, cy),
        }
        if side not in anchors:
            raise ValueError(f"Unknown anchor '{side}'. Valid: {list(anchors.keys())}")
        return anchors[side]

    def get_bbox(self) -> BoundingBox:
        cx, cy = self.position
        w, h = self.size
        return BoundingBox(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


class FlowchartDiamond(DrawableGroup):
    """
    A flowchart decision node: a diamond polygon with a centered Text label.

    position is the center. size = (width, height) of the diamond's bounding box.
    """

    def __init__(
        self,
        label: str,
        position: Tuple[float, float],
        size: Tuple[float, float] = (100.0, 60.0),
        font_size: int = 12,
        stroke_style: StrokeStyle = StrokeStyle(),
        sketch_style: SketchStyle = SketchStyle(),
        fill_style: Optional[FillStyle] = None,
        **kwargs,
    ):
        cx, cy = position
        hw, hh = size[0] / 2, size[1] / 2
        self.label = label
        self.position = position
        self.size = size

        diamond_points = [
            (cx, cy - hh),    # top
            (cx + hw, cy),    # right
            (cx, cy + hh),    # bottom
            (cx - hw, cy),    # left
        ]
        diamond = Polygon(
            points=diamond_points,
            stroke_style=stroke_style,
            sketch_style=sketch_style,
            fill_style=fill_style,
        )
        text = Text(
            text=label,
            position=position,
            font_size=font_size,
            stroke_style=stroke_style,
            sketch_style=sketch_style,
        )
        super().__init__(
            elements=[diamond, text],
            grouping_method="parallel",
            stroke_style=stroke_style,
            sketch_style=sketch_style,
            **kwargs,
        )

    def get_anchor(self, side: str = "center") -> Tuple[float, float]:
        cx, cy = self.position
        hw, hh = self.size[0] / 2, self.size[1] / 2
        anchors = {
            "center": (cx, cy),
            "top": (cx, cy - hh),
            "bottom": (cx, cy + hh),
            "left": (cx - hw, cy),
            "right": (cx + hw, cy),
        }
        if side not in anchors:
            raise ValueError(f"Unknown anchor '{side}'. Valid: {list(anchors.keys())}")
        return anchors[side]

    def get_bbox(self) -> BoundingBox:
        cx, cy = self.position
        hw, hh = self.size[0] / 2, self.size[1] / 2
        return BoundingBox(cx - hw, cy - hh, cx + hw, cy + hh)


class FlowchartConnector(Drawable):
    """
    An auto-routed arrow between two flowchart nodes.

    Computes an elbow route from from_node.get_anchor(from_side) to
    to_node.get_anchor(to_side) at draw time so that moving a node
    automatically updates the connector without re-construction.

    For straight lines (same axis, opposing sides, perfectly aligned),
    a single Arrow is drawn. Otherwise an L-shaped elbow is used:
    the connector exits from_node in the from_side direction, turns
    once at the midpoint, then arrives at to_node from the to_side
    direction.
    """

    def __init__(
        self,
        from_node: "FlowchartNode | FlowchartDiamond",
        to_node: "FlowchartNode | FlowchartDiamond",
        from_side: str = "bottom",
        to_side: str = "top",
        label: Optional[str] = None,
        label_font_size: int = 10,
        arrow_head_type: str = "->",
        arrow_head_size: float = 10.0,
        arrow_head_angle: float = 45.0,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        if from_side not in _VALID_SIDES:
            raise ValueError(f"from_side must be one of {_VALID_SIDES}")
        if to_side not in _VALID_SIDES:
            raise ValueError(f"to_side must be one of {_VALID_SIDES}")
        self.from_node = from_node
        self.to_node = to_node
        self.from_side = from_side
        self.to_side = to_side
        self.label = label
        self.label_font_size = label_font_size
        self.arrow_head_type = arrow_head_type
        self.arrow_head_size = arrow_head_size
        self.arrow_head_angle = arrow_head_angle
        self.args = args
        self.kwargs = kwargs

    def _compute_waypoints(
        self,
        from_pt: Tuple[float, float],
        from_side: str,
        to_pt: Tuple[float, float],
        to_side: str,
    ) -> List[Tuple[float, float]]:
        fx, fy = from_pt
        tx, ty = to_pt

        # Straight line when nodes are perfectly aligned on the connecting axis
        if from_side in ("top", "bottom") and to_side in ("top", "bottom"):
            if abs(fx - tx) < 1e-6:
                return [from_pt, to_pt]
        if from_side in ("left", "right") and to_side in ("left", "right"):
            if abs(fy - ty) < 1e-6:
                return [from_pt, to_pt]

        # Elbow routing: exit in the from_side direction, turn once, arrive from to_side
        if from_side in ("top", "bottom"):
            mid_y = (fy + ty) / 2
            return [from_pt, (fx, mid_y), (tx, mid_y), to_pt]
        else:
            mid_x = (fx + tx) / 2
            return [from_pt, (mid_x, fy), (mid_x, ty), to_pt]

    def draw(self) -> OpsSet:
        opsset = OpsSet(initial_set=[])

        from_pt = self.from_node.get_anchor(self.from_side)
        to_pt = self.to_node.get_anchor(self.to_side)
        waypoints = self._compute_waypoints(from_pt, self.from_side, to_pt, self.to_side)

        # Draw all intermediate segments as plain Lines
        for i in range(len(waypoints) - 2):
            seg = Line(
                start=waypoints[i],
                end=waypoints[i + 1],
                stroke_style=self.stroke_style,
                sketch_style=self.sketch_style,
            )
            opsset.extend(seg.draw())

        # Final segment carries the arrowhead
        arrow = Arrow(
            start_point=waypoints[-2],
            end_point=waypoints[-1],
            arrow_head_type=self.arrow_head_type,
            arrow_head_size=self.arrow_head_size,
            arrow_head_angle=self.arrow_head_angle,
            stroke_style=self.stroke_style,
            sketch_style=self.sketch_style,
        )
        opsset.extend(arrow.draw())

        # Optional label positioned at the midpoint of the path
        if self.label:
            mid_idx = len(waypoints) // 2
            lx = (waypoints[mid_idx - 1][0] + waypoints[mid_idx][0]) / 2
            ly = (waypoints[mid_idx - 1][1] + waypoints[mid_idx][1]) / 2
            label_text = Text(
                text=self.label,
                position=(lx, ly),
                font_size=self.label_font_size,
                stroke_style=self.stroke_style,
                sketch_style=self.sketch_style,
            )
            opsset.extend(label_text.draw())

        return opsset


class Flowchart(DrawableGroup):
    """
    A complete flowchart assembled from FlowchartNode, FlowchartDiamond, and
    FlowchartConnector primitives.

    Prefer constructing via Flowchart.from_dict(spec) rather than directly.
    """

    def __init__(
        self,
        nodes: List[DrawableGroup],
        connectors: List[FlowchartConnector],
        **kwargs,
    ):
        self.nodes = nodes
        self.connectors = connectors
        super().__init__(elements=nodes + connectors, grouping_method="parallel", **kwargs)

    @classmethod
    def from_dict(cls, spec: Dict[str, Any], **kwargs) -> "Flowchart":
        """
        Build a Flowchart from a declarative spec dict.

        Expected format::

            {
                "nodes": [
                    {
                        "id": "start",
                        "type": "node",        # "node" (default) or "diamond"
                        "label": "Start",
                        "position": [100, 50],
                        "size": [100, 40],     # optional
                        "font_size": 12,       # optional
                    },
                    ...
                ],
                "edges": [
                    {
                        "from": "start",
                        "to": "decision",
                        "from_side": "bottom",  # optional, default "bottom"
                        "to_side": "top",       # optional, default "top"
                        "label": "Yes",         # optional edge label
                    },
                    ...
                ],
            }

        Additional keys in each node or edge dict are forwarded as keyword
        arguments to the underlying primitive (e.g. stroke_style, fill_style).
        """
        _NODE_RESERVED = {"id", "type", "label", "position", "size", "font_size"}
        _EDGE_RESERVED = {"from", "to", "from_side", "to_side", "label"}

        node_map: Dict[str, "FlowchartNode | FlowchartDiamond"] = {}
        node_objects: List[DrawableGroup] = []

        for node_spec in spec.get("nodes", []):
            node_id = node_spec["id"]
            node_type = node_spec.get("type", "node")
            label = node_spec.get("label", "")
            position = tuple(node_spec["position"])
            size = tuple(node_spec.get("size", [100, 50]))
            font_size = node_spec.get("font_size", 12)
            extra = {k: v for k, v in node_spec.items() if k not in _NODE_RESERVED}

            if node_type == "diamond":
                node = FlowchartDiamond(
                    label=label,
                    position=position,
                    size=size,
                    font_size=font_size,
                    **extra,
                )
            else:
                node = FlowchartNode(
                    label=label,
                    position=position,
                    size=size,
                    font_size=font_size,
                    **extra,
                )

            node_map[node_id] = node
            node_objects.append(node)

        connectors: List[FlowchartConnector] = []
        for edge_spec in spec.get("edges", []):
            from_id = edge_spec["from"]
            to_id = edge_spec["to"]
            if from_id not in node_map:
                raise ValueError(f"Edge references unknown node id '{from_id}'")
            if to_id not in node_map:
                raise ValueError(f"Edge references unknown node id '{to_id}'")

            from_side = edge_spec.get("from_side", "bottom")
            to_side = edge_spec.get("to_side", "top")
            label = edge_spec.get("label", None)
            extra = {k: v for k, v in edge_spec.items() if k not in _EDGE_RESERVED}

            connector = FlowchartConnector(
                from_node=node_map[from_id],
                to_node=node_map[to_id],
                from_side=from_side,
                to_side=to_side,
                label=label,
                **extra,
            )
            connectors.append(connector)

        return cls(nodes=node_objects, connectors=connectors, **kwargs)
