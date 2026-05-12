"""
Unit tests for OpsSet geometry transforms and query helpers.

These tests are pure Python — no Cairo, no rendering. They construct OpsSet
instances with known coordinates and assert exact output after transforms.
"""

import numpy as np
import pytest

from handanim.core.draw_ops import Ops, OpsSet, OpsType, BoundingBox

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_move_line(x0, y0, x1, y1) -> OpsSet:
    """Minimal OpsSet: MOVE_TO then LINE_TO."""
    ops = OpsSet()
    ops.add(Ops(OpsType.MOVE_TO, [(x0, y0)]))
    ops.add(Ops(OpsType.LINE_TO, [(x1, y1)]))
    return ops


def point_coords(opsset: OpsSet):
    """Return all (x, y) tuples from list-typed ops data, in order."""
    coords = []
    for op in opsset.opsset:
        if isinstance(op.data, list):
            coords.extend(op.data)
    return coords


# ---------------------------------------------------------------------------
# translate
# ---------------------------------------------------------------------------


class TestTranslate:
    def test_shifts_all_points(self):
        ops = make_move_line(10, 20, 30, 40)
        ops.translate(5, -10)
        coords = point_coords(ops)
        assert np.allclose(coords[0], (15, 10))
        assert np.allclose(coords[1], (35, 30))

    def test_preserves_set_pen(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.SET_PEN, {"color": (1, 0, 0), "width": 2}))
        ops.add(Ops(OpsType.MOVE_TO, [(0, 0)]))
        ops.translate(100, 100)
        pen = ops.opsset[0]
        assert pen.type == OpsType.SET_PEN
        assert pen.data == {"color": (1, 0, 0), "width": 2}

    def test_translate_zero_is_identity(self):
        ops = make_move_line(7, 8, 9, 10)
        original = point_coords(ops)
        ops.translate(0, 0)
        assert np.allclose(point_coords(ops), original)


# ---------------------------------------------------------------------------
# scale
# ---------------------------------------------------------------------------


class TestScale:
    def test_uniform_scale_doubles_distance_from_center(self):
        # Two points symmetric around (50, 50): (0,50) and (100,50)
        ops = OpsSet()
        ops.add(Ops(OpsType.MOVE_TO, [(0, 50)]))
        ops.add(Ops(OpsType.LINE_TO, [(100, 50)]))
        ops.scale(2.0)
        coords = point_coords(ops)
        # center-of-gravity is (50,50); scaling by 2 doubles distance from center
        assert np.allclose(coords[0], (-50, 50))
        assert np.allclose(coords[1], (150, 50))

    def test_nonuniform_scale(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.MOVE_TO, [(0, 0)]))
        ops.add(Ops(OpsType.LINE_TO, [(100, 100)]))
        # center = (50, 50)
        ops.scale(2.0, 0.5)
        coords = point_coords(ops)
        # x: 50 + 2*(x-50),  y: 50 + 0.5*(y-50)
        assert np.allclose(coords[0], (-50, 25))
        assert np.allclose(coords[1], (150, 75))

    def test_scale_one_is_identity(self):
        ops = make_move_line(10, 20, 80, 60)
        original = point_coords(ops)
        ops.scale(1.0)
        assert np.allclose(point_coords(ops), original)

    def test_scale_preserves_set_pen(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.SET_PEN, {"width": 3}))
        ops.add(Ops(OpsType.MOVE_TO, [(10, 10)]))
        ops.scale(5.0)
        assert ops.opsset[0].data == {"width": 3}


# ---------------------------------------------------------------------------
# rotate
# ---------------------------------------------------------------------------


class TestRotate:
    def test_rotate_90_degrees(self):
        # Point at (100, 0) relative to center (50, 50) → after 90° CCW → (50, 100)
        ops = OpsSet()
        ops.add(Ops(OpsType.MOVE_TO, [(50, 50)]))  # center point stays put
        ops.add(Ops(OpsType.LINE_TO, [(100, 50)]))  # point 50 units right of center
        ops.rotate(90, center_of_rotation=(50, 50))
        coords = point_coords(ops)
        # after 90° CCW: (100,50) → (50,100)
        assert np.allclose(coords[1], (50, 100), atol=1e-9)

    def test_rotate_360_roundtrip(self):
        ops = make_move_line(30, 70, 90, 130)
        original = point_coords(ops)
        ops.rotate(360)
        assert np.allclose(point_coords(ops), original, atol=1e-9)

    def test_rotate_preserves_set_pen(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.SET_PEN, {"color": (0, 0, 1)}))
        ops.add(Ops(OpsType.MOVE_TO, [(0, 0)]))
        ops.rotate(45)
        assert ops.opsset[0].data == {"color": (0, 0, 1)}

    def test_rotate_180_inverts_offset(self):
        # Center at (50,50). Point at (100,50) is +50 in x.
        # After 180°, it should be at (0,50): -50 in x.
        ops = OpsSet()
        ops.add(Ops(OpsType.MOVE_TO, [(50, 50)]))
        ops.add(Ops(OpsType.LINE_TO, [(100, 50)]))
        ops.rotate(180, center_of_rotation=(50, 50))
        coords = point_coords(ops)
        assert np.allclose(coords[1], (0, 50), atol=1e-9)


# ---------------------------------------------------------------------------
# get_bbox
# ---------------------------------------------------------------------------


class TestGetBbox:
    def test_empty_opsset_returns_zeros(self):
        assert OpsSet().get_bbox() == BoundingBox(0, 0, 0, 0)

    def test_known_coords(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.MOVE_TO, [(10, 5)]))
        ops.add(Ops(OpsType.LINE_TO, [(80, 5)]))
        ops.add(Ops(OpsType.LINE_TO, [(80, 95)]))
        ops.add(Ops(OpsType.LINE_TO, [(10, 95)]))
        bbox = ops.get_bbox()
        assert bbox.min_x == 10
        assert bbox.min_y == 5
        assert bbox.max_x == 80
        assert bbox.max_y == 95
        assert bbox.width == 70
        assert bbox.height == 90
        assert bbox.center == (45, 50)

    def test_set_pen_only_returns_zeros(self):
        # get_bbox early-returns (0,0,0,0) only for a completely empty OpsSet.
        # An OpsSet with ops but no list-typed data (e.g. only SET_PEN) leaves
        # the min/max accumulators at their initial sentinel values.
        # but it is updated to zeros later
        ops = OpsSet()
        ops.add(Ops(OpsType.SET_PEN, {"color": (0, 0, 0)}))
        assert ops.get_bbox() == BoundingBox(0, 0, 0, 0)


# ---------------------------------------------------------------------------
# get_center_of_gravity
# ---------------------------------------------------------------------------


class TestGetCenterOfGravity:
    def test_symmetric_shape(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.MOVE_TO, [(0, 0)]))
        ops.add(Ops(OpsType.LINE_TO, [(100, 0)]))
        ops.add(Ops(OpsType.LINE_TO, [(100, 100)]))
        ops.add(Ops(OpsType.LINE_TO, [(0, 100)]))
        cx, cy = ops.get_center_of_gravity()
        assert np.isclose(cx, 50)
        assert np.isclose(cy, 50)


# ---------------------------------------------------------------------------
# filter_by_meta_query
# ---------------------------------------------------------------------------


class TestFilterByMetaQuery:
    def test_returns_only_matching_ops(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.LINE_TO, [(0, 0)], meta={"group": "A"}))
        ops.add(Ops(OpsType.LINE_TO, [(1, 1)], meta={"group": "B"}))
        ops.add(Ops(OpsType.LINE_TO, [(2, 2)], meta={"group": "A"}))
        result = ops.filter_by_meta_query("group", "A")
        assert len(result.opsset) == 2
        for op in result.opsset:
            assert op.meta["group"] == "A"

    def test_no_match_returns_empty(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.LINE_TO, [(0, 0)], meta={"group": "A"}))
        result = ops.filter_by_meta_query("group", "Z")
        assert len(result.opsset) == 0

    def test_ops_without_meta_are_excluded(self):
        ops = OpsSet()
        ops.add(Ops(OpsType.LINE_TO, [(0, 0)]))  # no meta
        ops.add(Ops(OpsType.LINE_TO, [(1, 1)], meta={"group": "A"}))
        result = ops.filter_by_meta_query("group", "A")
        assert len(result.opsset) == 1


# ---------------------------------------------------------------------------
# extend
# ---------------------------------------------------------------------------


class TestExtend:
    def test_appends_ops_in_order(self):
        a = OpsSet()
        a.add(Ops(OpsType.MOVE_TO, [(0, 0)]))

        b = OpsSet()
        b.add(Ops(OpsType.LINE_TO, [(10, 10)]))
        b.add(Ops(OpsType.LINE_TO, [(20, 20)]))

        a.extend(b)
        assert len(a.opsset) == 3
        assert a.opsset[1].type == OpsType.LINE_TO
        assert a.opsset[2].type == OpsType.LINE_TO

    def test_extend_with_non_opsset_raises(self):
        ops = OpsSet()
        with pytest.raises(TypeError):
            ops.extend([1, 2, 3])
