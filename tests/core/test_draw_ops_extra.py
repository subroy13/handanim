"""
Additional unit tests for draw_ops.py — covering BoundingBox properties,
Ops repr, OpsSet repr, get_current_point, get_last_ops, add_meta,
CURVE_TO bounding-box, and QUAD_CURVE_TO bounding-box.
"""

import numpy as np
import pytest

from handanim.core.draw_ops import BoundingBox, Ops, OpsSet, OpsType


# ---------------------------------------------------------------------------
# BoundingBox
# ---------------------------------------------------------------------------

class TestBoundingBox:
    def test_width(self):
        bb = BoundingBox(10, 20, 50, 80)
        assert bb.width == 40

    def test_height(self):
        bb = BoundingBox(10, 20, 50, 80)
        assert bb.height == 60

    def test_center(self):
        bb = BoundingBox(0, 0, 100, 200)
        assert bb.center == (50.0, 100.0)

    def test_top_left(self):
        bb = BoundingBox(5, 7, 50, 80)
        assert bb.top_left == (5, 7)

    def test_bottom_right(self):
        bb = BoundingBox(5, 7, 50, 80)
        assert bb.bottom_right == (50, 80)

    def test_zero_area(self):
        bb = BoundingBox(10, 10, 10, 10)
        assert bb.width == 0
        assert bb.height == 0


# ---------------------------------------------------------------------------
# Ops repr
# ---------------------------------------------------------------------------

class TestOpsRepr:
    def test_repr_with_list_data(self):
        op = Ops(OpsType.LINE_TO, [(1.23456, 7.89012)])
        r = repr(op)
        assert "LINE_TO" in r
        assert "1.23" in r

    def test_repr_with_dict_data(self):
        op = Ops(OpsType.SET_PEN, {"color": (0, 0, 0), "width": 2})
        r = repr(op)
        assert "SET_PEN" in r

    def test_repr_partial(self):
        op = Ops(OpsType.LINE_TO, [(10, 20)], partial=0.5)
        r = repr(op)
        assert "0.5" in r


# ---------------------------------------------------------------------------
# OpsSet repr
# ---------------------------------------------------------------------------

class TestOpsSetRepr:
    def test_repr_small_set(self):
        ops = OpsSet()
        for i in range(3):
            ops.add(Ops(OpsType.MOVE_TO, [(i, i)]))
        r = repr(ops)
        assert "OpsSet" in r

    def test_repr_large_set(self):
        ops = OpsSet()
        for i in range(15):
            ops.add(Ops(OpsType.LINE_TO, [(i, i)]))
        r = repr(ops)
        assert "more rows" in r


# ---------------------------------------------------------------------------
# add_meta
# ---------------------------------------------------------------------------

class TestAddMeta:
    def test_meta_set_on_all_ops(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.MOVE_TO, [(0, 0)]))
        ops.add(Ops(OpsType.LINE_TO, [(10, 10)]))
        ops.add_meta({"layer": "base"})
        for op in ops.opsset:
            assert op.meta["layer"] == "base"

    def test_meta_merges_with_existing(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.LINE_TO, [(0, 0)], meta={"group": "A"}))
        ops.add_meta({"layer": "base"})
        assert ops.opsset[0].meta["group"] == "A"
        assert ops.opsset[0].meta["layer"] == "base"

    def test_add_meta_none_uses_empty_dict(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.LINE_TO, [(0, 0)]))
        ops.add_meta(None)
        assert ops.opsset[0].meta == {}


# ---------------------------------------------------------------------------
# get_last_ops
# ---------------------------------------------------------------------------

class TestGetLastOps:
    def test_empty_returns_none(self):
        idx, op = OpsSet().get_last_ops()
        assert idx is None and op is None

    def test_returns_last_geometric_op(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.MOVE_TO, [(0, 0)]))
        ops.add(Ops(OpsType.LINE_TO, [(10, 10)]))
        ops.add(Ops(OpsType.SET_PEN, {"width": 1}))
        _, op = ops.get_last_ops()
        assert op.type == OpsType.LINE_TO

    def test_set_pen_only_returns_none(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.SET_PEN, {"width": 1}))
        _, op = ops.get_last_ops()
        assert op is None

    def test_start_index_skips_last(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.MOVE_TO, [(0, 0)]))
        ops.add(Ops(OpsType.LINE_TO, [(10, 10)]))
        _, op = ops.get_last_ops(start_index=1)
        assert op.type == OpsType.MOVE_TO


# ---------------------------------------------------------------------------
# get_current_point
# ---------------------------------------------------------------------------

class TestGetCurrentPoint:
    def test_empty_returns_origin(self):
        assert OpsSet().get_current_point() == (0, 0)

    def test_move_to_sets_point(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.MOVE_TO, [(30, 40)]))
        assert ops.get_current_point() == (30, 40)

    def test_line_to_full_sets_endpoint(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.MOVE_TO, [(0, 0)]))
        ops.add(Ops(OpsType.LINE_TO, [(80, 60)]))
        assert ops.get_current_point() == (80, 60)

    def test_line_to_partial_interpolates(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.MOVE_TO, [(0, 0)]))
        ops.add(Ops(OpsType.LINE_TO, [(100, 0)], partial=0.5))
        x, y = ops.get_current_point()
        assert x == pytest.approx(50.0, abs=1e-6)
        assert y == pytest.approx(0.0, abs=1e-6)

    def test_curve_to_full_returns_last_control(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.MOVE_TO, [(0, 0)]))
        ops.add(Ops(OpsType.CURVE_TO, [(25, 50), (75, 50), (100, 0)]))
        pt = ops.get_current_point()
        assert pt == (100, 0)

    def test_quad_curve_to_full_returns_endpoint(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.MOVE_TO, [(0, 0)]))
        ops.add(Ops(OpsType.QUAD_CURVE_TO, [(50, 100), (100, 0)]))
        pt = ops.get_current_point()
        assert pt == (100, 0)


# ---------------------------------------------------------------------------
# get_bbox with CURVE_TO
# ---------------------------------------------------------------------------

class TestGetBboxCurves:
    def test_curve_to_bbox_includes_endpoint(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.MOVE_TO, [(0, 0)]))
        ops.add(Ops(OpsType.CURVE_TO, [(0, 100), (100, 100), (100, 0)]))
        bbox = ops.get_bbox()
        assert bbox.min_x == pytest.approx(0, abs=1)
        assert bbox.max_x == pytest.approx(100, abs=1)
        assert bbox.max_y >= 50  # curve bulges upward

    def test_quad_curve_to_bbox(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.MOVE_TO, [(0, 0)]))
        ops.add(Ops(OpsType.QUAD_CURVE_TO, [(50, 100), (100, 0)]))
        bbox = ops.get_bbox()
        assert bbox.min_x == pytest.approx(0, abs=1)
        assert bbox.max_x == pytest.approx(100, abs=1)
        assert bbox.max_y >= 40

    def test_only_set_pen_returns_zero_bbox(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.SET_PEN, {"color": (0, 0, 0)}))
        assert ops.get_bbox() == BoundingBox(0, 0, 0, 0)


# ---------------------------------------------------------------------------
# OpsSet from dict initial_set
# ---------------------------------------------------------------------------

class TestOpsSetFromDict:
    def test_dict_initializer_converted_to_ops(self):
        ops = OpsSet(initial_set=[
            {"type": OpsType.MOVE_TO, "data": [(0, 0)]},
            {"type": OpsType.LINE_TO, "data": [(50, 50)]},
        ])
        assert len(ops.opsset) == 2
        assert all(isinstance(o, Ops) for o in ops.opsset)
