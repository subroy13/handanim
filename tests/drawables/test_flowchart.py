"""
Tests for flowchart primitives: FlowchartNode, FlowchartDiamond,
FlowchartConnector, and Flowchart.from_dict.

Structure
---------
- TestFlowchartNodeAnchors    — pure geometry, no rendering
- TestFlowchartDiamondAnchors — pure geometry, no rendering
- TestFlowchartConnectorRouting — waypoint routing logic
- TestFlowchartFromDict       — factory construction and error paths
- TestFlowchartDraw           — draw() produces non-empty OpsSet
- TestFlowchartVisual         — visual regression snapshot
"""

import pytest
import numpy as np

from handanim.core.draw_ops import BoundingBox, OpsSet
from handanim.primitives.flowchart import (
    Flowchart,
    FlowchartConnector,
    FlowchartDiamond,
    FlowchartNode,
)


# ---------------------------------------------------------------------------
# Shared fixture: a minimal two-node spec
# ---------------------------------------------------------------------------

@pytest.fixture
def two_node_spec():
    return {
        "nodes": [
            {"id": "a", "label": "Start", "position": [200, 100], "size": [120, 40]},
            {"id": "b", "label": "End",   "position": [200, 250], "size": [120, 40]},
        ],
        "edges": [
            {"from": "a", "to": "b"},
        ],
    }


# ---------------------------------------------------------------------------
# FlowchartNode — anchors and bounding box
# ---------------------------------------------------------------------------

class TestFlowchartNodeAnchors:
    def setup_method(self):
        self.node = FlowchartNode(
            label="Step",
            position=(200.0, 150.0),
            size=(120.0, 60.0),
        )

    def test_center_anchor(self):
        assert self.node.get_anchor("center") == (200.0, 150.0)

    def test_top_anchor(self):
        assert self.node.get_anchor("top") == (200.0, 120.0)

    def test_bottom_anchor(self):
        assert self.node.get_anchor("bottom") == (200.0, 180.0)

    def test_left_anchor(self):
        assert self.node.get_anchor("left") == (140.0, 150.0)

    def test_right_anchor(self):
        assert self.node.get_anchor("right") == (260.0, 150.0)

    def test_invalid_anchor_raises(self):
        with pytest.raises(ValueError, match="Unknown anchor"):
            self.node.get_anchor("diagonal")

    def test_get_bbox(self):
        bbox = self.node.get_bbox()
        assert isinstance(bbox, BoundingBox)
        assert bbox.min_x == pytest.approx(140.0)
        assert bbox.min_y == pytest.approx(120.0)
        assert bbox.max_x == pytest.approx(260.0)
        assert bbox.max_y == pytest.approx(180.0)
        assert bbox.width == pytest.approx(120.0)
        assert bbox.height == pytest.approx(60.0)

    def test_bbox_center_matches_position(self):
        bbox = self.node.get_bbox()
        assert bbox.center == pytest.approx(self.node.position)


# ---------------------------------------------------------------------------
# FlowchartDiamond — anchors and bounding box
# ---------------------------------------------------------------------------

class TestFlowchartDiamondAnchors:
    def setup_method(self):
        self.diamond = FlowchartDiamond(
            label="Yes?",
            position=(300.0, 200.0),
            size=(100.0, 60.0),
        )

    def test_center_anchor(self):
        assert self.diamond.get_anchor("center") == (300.0, 200.0)

    def test_top_anchor_is_apex(self):
        assert self.diamond.get_anchor("top") == (300.0, 170.0)

    def test_bottom_anchor_is_nadir(self):
        assert self.diamond.get_anchor("bottom") == (300.0, 230.0)

    def test_left_anchor(self):
        assert self.diamond.get_anchor("left") == (250.0, 200.0)

    def test_right_anchor(self):
        assert self.diamond.get_anchor("right") == (350.0, 200.0)

    def test_invalid_anchor_raises(self):
        with pytest.raises(ValueError, match="Unknown anchor"):
            self.diamond.get_anchor("top_left")

    def test_get_bbox(self):
        bbox = self.diamond.get_bbox()
        assert bbox.min_x == pytest.approx(250.0)
        assert bbox.min_y == pytest.approx(170.0)
        assert bbox.max_x == pytest.approx(350.0)
        assert bbox.max_y == pytest.approx(230.0)

    def test_bbox_center_matches_position(self):
        bbox = self.diamond.get_bbox()
        assert bbox.center == pytest.approx(self.diamond.position)


# ---------------------------------------------------------------------------
# FlowchartConnector — waypoint routing
# ---------------------------------------------------------------------------

class TestFlowchartConnectorRouting:
    def setup_method(self):
        self.node_a = FlowchartNode("A", (200, 100), (120, 40))
        self.node_b = FlowchartNode("B", (200, 300), (120, 40))
        self.node_c = FlowchartNode("C", (450, 100), (120, 40))

    def _connector(self, from_node, to_node, from_side="bottom", to_side="top"):
        return FlowchartConnector(
            from_node=from_node,
            to_node=to_node,
            from_side=from_side,
            to_side=to_side,
        )

    # Straight paths — perfectly axis-aligned, opposing sides

    def test_straight_vertical_same_column(self):
        c = self._connector(self.node_a, self.node_b, "bottom", "top")
        from_pt = self.node_a.get_anchor("bottom")
        to_pt = self.node_b.get_anchor("top")
        wps = c._compute_waypoints(from_pt, "bottom", to_pt, "top")
        assert wps == [from_pt, to_pt]

    def test_straight_horizontal_same_row(self):
        node_right = FlowchartNode("R", (450, 100), (120, 40))
        c = self._connector(self.node_a, node_right, "right", "left")
        from_pt = self.node_a.get_anchor("right")
        to_pt = node_right.get_anchor("left")
        wps = c._compute_waypoints(from_pt, "right", to_pt, "left")
        assert wps == [from_pt, to_pt]

    # Elbow paths — misaligned nodes

    def test_elbow_bottom_to_top_different_column(self):
        c = self._connector(self.node_a, self.node_c, "bottom", "top")
        from_pt = self.node_a.get_anchor("bottom")  # (200, 120)
        to_pt = self.node_c.get_anchor("top")        # (450, 80)
        wps = c._compute_waypoints(from_pt, "bottom", to_pt, "top")
        # should produce 4 waypoints with an elbow at mid_y
        assert len(wps) == 4
        mid_y = (from_pt[1] + to_pt[1]) / 2
        assert wps[0] == from_pt
        assert wps[1] == pytest.approx((from_pt[0], mid_y))
        assert wps[2] == pytest.approx((to_pt[0], mid_y))
        assert wps[3] == to_pt

    def test_elbow_right_to_left_different_row(self):
        node_low = FlowchartNode("D", (450, 300), (120, 40))
        c = self._connector(self.node_a, node_low, "right", "left")
        from_pt = self.node_a.get_anchor("right")   # (260, 100)
        to_pt   = node_low.get_anchor("left")        # (390, 300)
        wps = c._compute_waypoints(from_pt, "right", to_pt, "left")
        assert len(wps) == 4
        mid_x = (from_pt[0] + to_pt[0]) / 2
        assert wps[1] == pytest.approx((mid_x, from_pt[1]))
        assert wps[2] == pytest.approx((mid_x, to_pt[1]))

    def test_invalid_from_side_raises(self):
        with pytest.raises(ValueError, match="from_side"):
            FlowchartConnector(self.node_a, self.node_b, from_side="diagonal")

    def test_invalid_to_side_raises(self):
        with pytest.raises(ValueError, match="to_side"):
            FlowchartConnector(self.node_a, self.node_b, to_side="nowhere")


# ---------------------------------------------------------------------------
# Flowchart.from_dict — factory construction and validation
# ---------------------------------------------------------------------------

class TestFlowchartFromDict:
    def test_basic_construction(self, two_node_spec):
        fc = Flowchart.from_dict(two_node_spec)
        assert len(fc.nodes) == 2
        assert len(fc.connectors) == 1

    def test_node_types(self, two_node_spec):
        fc = Flowchart.from_dict(two_node_spec)
        assert isinstance(fc.nodes[0], FlowchartNode)
        assert isinstance(fc.nodes[1], FlowchartNode)

    def test_diamond_node_type(self):
        spec = {
            "nodes": [
                {"id": "d", "type": "diamond", "label": "OK?", "position": [100, 100]},
            ],
            "edges": [],
        }
        fc = Flowchart.from_dict(spec)
        assert isinstance(fc.nodes[0], FlowchartDiamond)

    def test_connector_references_correct_nodes(self, two_node_spec):
        fc = Flowchart.from_dict(two_node_spec)
        conn = fc.connectors[0]
        assert conn.from_node is fc.nodes[0]
        assert conn.to_node is fc.nodes[1]

    def test_default_edge_sides(self, two_node_spec):
        fc = Flowchart.from_dict(two_node_spec)
        conn = fc.connectors[0]
        assert conn.from_side == "bottom"
        assert conn.to_side == "top"

    def test_custom_edge_sides(self):
        spec = {
            "nodes": [
                {"id": "x", "label": "X", "position": [100, 100]},
                {"id": "y", "label": "Y", "position": [300, 100]},
            ],
            "edges": [
                {"from": "x", "to": "y", "from_side": "right", "to_side": "left"},
            ],
        }
        fc = Flowchart.from_dict(spec)
        conn = fc.connectors[0]
        assert conn.from_side == "right"
        assert conn.to_side == "left"

    def test_edge_label_forwarded(self):
        spec = {
            "nodes": [
                {"id": "a", "label": "A", "position": [100, 100]},
                {"id": "b", "label": "B", "position": [100, 300]},
            ],
            "edges": [{"from": "a", "to": "b", "label": "Yes"}],
        }
        fc = Flowchart.from_dict(spec)
        assert fc.connectors[0].label == "Yes"

    def test_unknown_from_node_raises(self):
        spec = {
            "nodes": [{"id": "a", "label": "A", "position": [0, 0]}],
            "edges": [{"from": "missing", "to": "a"}],
        }
        with pytest.raises(ValueError, match="missing"):
            Flowchart.from_dict(spec)

    def test_unknown_to_node_raises(self):
        spec = {
            "nodes": [{"id": "a", "label": "A", "position": [0, 0]}],
            "edges": [{"from": "a", "to": "ghost"}],
        }
        with pytest.raises(ValueError, match="ghost"):
            Flowchart.from_dict(spec)

    def test_empty_spec_produces_empty_flowchart(self):
        fc = Flowchart.from_dict({"nodes": [], "edges": []})
        assert fc.nodes == []
        assert fc.connectors == []

    def test_node_position_and_size_preserved(self):
        spec = {
            "nodes": [
                {"id": "n", "label": "N", "position": [150, 250], "size": [80, 30]},
            ],
            "edges": [],
        }
        fc = Flowchart.from_dict(spec)
        node = fc.nodes[0]
        assert node.position == (150, 250)
        assert node.size == (80, 30)

    def test_multiple_edges_from_diamond(self):
        spec = {
            "nodes": [
                {"id": "q",   "type": "diamond", "label": "OK?", "position": [200, 150]},
                {"id": "yes", "label": "Done",   "position": [200, 300]},
                {"id": "no",  "label": "Retry",  "position": [400, 150]},
            ],
            "edges": [
                {"from": "q", "to": "yes", "label": "Yes"},
                {"from": "q", "to": "no",  "from_side": "right", "to_side": "left", "label": "No"},
            ],
        }
        fc = Flowchart.from_dict(spec)
        assert len(fc.connectors) == 2
        assert fc.connectors[0].label == "Yes"
        assert fc.connectors[1].label == "No"
        assert fc.connectors[1].from_side == "right"


# ---------------------------------------------------------------------------
# FlowchartNode / Diamond / Connector — draw() produces non-empty OpsSet
# ---------------------------------------------------------------------------

class TestFlowchartDraw:
    def test_node_draw_returns_opsset(self):
        node = FlowchartNode("Hello", (200, 150), (120, 60))
        result = node.draw()
        assert isinstance(result, OpsSet)
        assert len(result.opsset) > 0

    def test_diamond_draw_returns_opsset(self):
        diamond = FlowchartDiamond("Yes?", (200, 150), (100, 60))
        result = diamond.draw()
        assert isinstance(result, OpsSet)
        assert len(result.opsset) > 0

    def test_connector_draw_returns_opsset(self):
        node_a = FlowchartNode("A", (200, 100), (120, 40))
        node_b = FlowchartNode("B", (200, 300), (120, 40))
        conn = FlowchartConnector(node_a, node_b)
        result = conn.draw()
        assert isinstance(result, OpsSet)
        assert len(result.opsset) > 0

    def test_connector_with_label_draw_returns_opsset(self):
        node_a = FlowchartNode("A", (200, 100), (120, 40))
        node_b = FlowchartNode("B", (200, 300), (120, 40))
        conn = FlowchartConnector(node_a, node_b, label="step")
        result = conn.draw()
        assert isinstance(result, OpsSet)
        assert len(result.opsset) > 0

    def test_flowchart_draw_combines_all_elements(self, two_node_spec):
        fc = Flowchart.from_dict(two_node_spec)
        result = fc.draw()
        assert isinstance(result, OpsSet)
        assert len(result.opsset) > 0

    def test_flowchart_draw_has_more_ops_than_single_node(self, two_node_spec):
        fc = Flowchart.from_dict(two_node_spec)
        single_node_ops = fc.nodes[0].draw()
        full_ops = fc.draw()
        assert len(full_ops.opsset) > len(single_node_ops.opsset)


# ---------------------------------------------------------------------------
# Visual regression — flowchart snapshot
# ---------------------------------------------------------------------------

def _flowchart_opsset() -> OpsSet:
    from handanim.core.styles import StrokeStyle, SketchStyle
    spec = {
        "nodes": [
            {"id": "start",    "label": "Start",   "position": [500, 80],  "size": [160, 50]},
            {"id": "decision", "type": "diamond", "label": "Check?",
             "position": [500, 220], "size": [160, 80]},
            {"id": "yes",      "label": "Process", "position": [500, 380], "size": [160, 50]},
            {"id": "no",       "label": "Skip",    "position": [760, 220], "size": [140, 50]},
        ],
        "edges": [
            {"from": "start",    "to": "decision"},
            {"from": "decision", "to": "yes",  "label": "Yes"},
            {"from": "decision", "to": "no",   "from_side": "right", "to_side": "left", "label": "No"},
        ],
    }
    fc = Flowchart.from_dict(spec)
    return fc.draw()


class TestFlowchartVisual:
    def test_flowchart_snapshot(self, render_to_png_bytes, snapshot):
        png = render_to_png_bytes(_flowchart_opsset(), width=500, height=500)
        snapshot.assert_match(png, "flowchart.png")

    def test_flowchart_self_consistency(self, render_to_png_bytes):
        """Same seed must produce pixel-identical output across two renders."""
        from skimage.metrics import structural_similarity as ssim
        import io
        from skimage import io as skio

        np.random.seed(42)
        png_a = render_to_png_bytes(_flowchart_opsset(), width=500, height=500)
        np.random.seed(42)
        png_b = render_to_png_bytes(_flowchart_opsset(), width=500, height=500)

        def to_arr(b):
            return skio.imread(io.BytesIO(b))

        score = ssim(to_arr(png_a), to_arr(png_b), channel_axis=-1)
        assert score == pytest.approx(1.0)
