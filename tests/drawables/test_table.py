"""
Tests for the Table primitive and TableRevealEvent animation helper.

Structure
---------
- TestTableGeometry        — bbox, cell positions, row/cell counts (no rendering)
- TestTableContent         — header/data label routing
- TestTableDraw            — draw() produces non-empty OpsSet; element counts
- TestTableRevealEvent     — animate_by_row / animate_by_cell timing and pairing
- TestTableAddToScene      — add_to_scene() registers the right events with Scene
- TestTableVisual          — visual regression snapshot
"""

import io
import pytest
import numpy as np

from handanim.core.animation import AnimationEventType, CompositeAnimationEvent
from handanim.core.draw_ops import BoundingBox, OpsSet
from handanim.core.styles import FillStyle, StrokeStyle, SketchStyle
from handanim.primitives.table import Table, TableRevealEvent


# ---------------------------------------------------------------------------
# Minimal animation stub — no real drawing, just carries timing
# ---------------------------------------------------------------------------

class _StubAnim:
    """Minimal animation class with the same constructor signature as AnimationEvent."""

    def __init__(self, start_time=0.0, duration=0.0, **kwargs):
        self.start_time = start_time
        self.duration = duration
        self.end_time = start_time + duration
        self.extra = kwargs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def small_table():
    """3 rows × 2 cols, no headers, no data — bare grid."""
    return Table(
        top_left=(100.0, 50.0),
        n_rows=3,
        n_cols=2,
        cell_width=80.0,
        cell_height=40.0,
    )


@pytest.fixture
def data_table():
    """2 data rows × 3 cols with headers."""
    return Table(
        top_left=(0.0, 0.0),
        n_rows=3,
        n_cols=3,
        cell_width=100.0,
        cell_height=50.0,
        headers=["Name", "Age", "City"],
        data=[
            ["Alice", "30", "NYC"],
            ["Bob", "25", "LA"],
        ],
    )


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

class TestTableGeometry:
    def test_bbox_origin(self, small_table):
        bb = small_table.get_bbox()
        assert bb.min_x == pytest.approx(100.0)
        assert bb.min_y == pytest.approx(50.0)

    def test_bbox_size(self, small_table):
        bb = small_table.get_bbox()
        assert bb.width == pytest.approx(160.0)   # 2 cols × 80
        assert bb.height == pytest.approx(120.0)  # 3 rows × 40

    def test_bbox_bottom_right(self, small_table):
        bb = small_table.get_bbox()
        assert bb.max_x == pytest.approx(260.0)
        assert bb.max_y == pytest.approx(170.0)

    def test_rect_top_left_for_each_cell(self, small_table):
        for r in range(3):
            for c in range(2):
                rect = small_table._rects[r][c]
                expected_x = 100.0 + c * 80.0
                expected_y = 50.0 + r * 40.0
                assert rect.top_left == pytest.approx((expected_x, expected_y))

    def test_rect_dimensions(self, small_table):
        for r in range(3):
            for c in range(2):
                rect = small_table._rects[r][c]
                assert rect.width == pytest.approx(80.0)
                assert rect.height == pytest.approx(40.0)

    def test_text_position_is_cell_center(self, small_table):
        for r in range(3):
            for c in range(2):
                text = small_table._texts[r][c]
                expected_cx = 100.0 + c * 80.0 + 40.0
                expected_cy = 50.0 + r * 40.0 + 20.0
                assert text.position == pytest.approx((expected_cx, expected_cy))

    def test_n_rows_and_cols_stored(self, small_table):
        assert small_table.n_rows == 3
        assert small_table.n_cols == 2

    def test_cells_shape(self, small_table):
        assert len(small_table.cells) == 3
        assert all(len(row) == 2 for row in small_table.cells)

    def test_row_groups_count(self, small_table):
        assert len(small_table.row_groups) == 3

    def test_row_group_contains_only_leaf_drawables(self, small_table):
        from handanim.core.drawable import DrawableGroup
        from handanim.primitives.polygons import Rectangle
        from handanim.primitives.text import Text
        for rg in small_table.row_groups:
            for elem in rg.elements:
                assert not isinstance(elem, DrawableGroup), (
                    "row_group elements must be leaf drawables to avoid "
                    "apply_to_group overwrite in Scene.add()"
                )
                assert isinstance(elem, (Rectangle, Text))

    def test_cell_group_contains_only_leaf_drawables(self, small_table):
        from handanim.core.drawable import DrawableGroup
        from handanim.primitives.polygons import Rectangle
        from handanim.primitives.text import Text
        for r in range(small_table.n_rows):
            for c in range(small_table.n_cols):
                cell = small_table.cells[r][c]
                for elem in cell.elements:
                    assert not isinstance(elem, DrawableGroup)
                    assert isinstance(elem, (Rectangle, Text))

    def test_table_elements_are_all_leaves(self, small_table):
        """Table.elements must be flat leaf drawables (no nested DrawableGroups)."""
        from handanim.core.drawable import DrawableGroup
        for elem in small_table.elements:
            assert not isinstance(elem, DrawableGroup)

    def test_total_leaf_element_count(self, small_table):
        # 3 rows × 2 cols × 2 (rect + text) = 12
        assert len(small_table.elements) == 12


# ---------------------------------------------------------------------------
# Content — header and data label routing
# ---------------------------------------------------------------------------

class TestTableContent:
    def test_header_labels_in_row_0(self, data_table):
        for c, expected in enumerate(["Name", "Age", "City"]):
            assert data_table._texts[0][c].text == expected

    def test_data_labels_in_remaining_rows(self, data_table):
        assert data_table._texts[1][0].text == "Alice"
        assert data_table._texts[1][1].text == "30"
        assert data_table._texts[1][2].text == "NYC"
        assert data_table._texts[2][0].text == "Bob"
        assert data_table._texts[2][1].text == "25"
        assert data_table._texts[2][2].text == "LA"

    def test_empty_table_has_blank_labels(self, small_table):
        for r in range(small_table.n_rows):
            for c in range(small_table.n_cols):
                assert small_table._texts[r][c].text == ""

    def test_no_headers_data_starts_at_row_0(self):
        t = Table(
            top_left=(0, 0),
            n_rows=2,
            n_cols=2,
            cell_width=50,
            cell_height=30,
            data=[["A", "B"], ["C", "D"]],
        )
        assert t._texts[0][0].text == "A"
        assert t._texts[1][1].text == "D"

    def test_partial_data_fills_missing_with_empty(self):
        t = Table(
            top_left=(0, 0),
            n_rows=2,
            n_cols=3,
            cell_width=50,
            cell_height=30,
            data=[["X"]],  # only one cell of data
        )
        assert t._texts[0][0].text == "X"
        assert t._texts[0][1].text == ""
        assert t._texts[0][2].text == ""
        assert t._texts[1][0].text == ""

    def test_header_stroke_style_applied_to_row0(self):
        hs = StrokeStyle(color=(1.0, 0.0, 0.0))
        t = Table(
            top_left=(0, 0),
            n_rows=2,
            n_cols=2,
            cell_width=50,
            cell_height=30,
            headers=["H1", "H2"],
            header_stroke_style=hs,
        )
        assert t._rects[0][0].stroke_style is hs
        assert t._rects[0][1].stroke_style is hs
        # data row should NOT use header style
        assert t._rects[1][0].stroke_style is not hs

    def test_default_header_stroke_falls_back_to_stroke_style(self):
        ss = StrokeStyle(color=(0.0, 0.5, 0.0))
        t = Table(
            top_left=(0, 0),
            n_rows=2,
            n_cols=1,
            cell_width=50,
            cell_height=30,
            headers=["H"],
            stroke_style=ss,
            header_stroke_style=None,
        )
        assert t._rects[0][0].stroke_style is ss


# ---------------------------------------------------------------------------
# draw()
# ---------------------------------------------------------------------------

class TestTableDraw:
    def test_draw_returns_opsset(self, small_table):
        result = small_table.draw()
        assert isinstance(result, OpsSet)

    def test_draw_is_non_empty(self, small_table):
        result = small_table.draw()
        assert len(result.opsset) > 0

    def test_data_table_draw_non_empty(self, data_table):
        result = data_table.draw()
        assert len(result.opsset) > 0

    def test_table_with_fill_draws_more_ops(self):
        bare = Table(top_left=(0, 0), n_rows=2, n_cols=2, cell_width=50, cell_height=30)
        filled = Table(
            top_left=(0, 0), n_rows=2, n_cols=2, cell_width=50, cell_height=30,
            fill_style=FillStyle(color=(0.8, 0.8, 0.8)),
        )
        assert len(filled.draw().opsset) > len(bare.draw().opsset)


# ---------------------------------------------------------------------------
# animate_by_row / animate_by_cell
# ---------------------------------------------------------------------------

class TestTableRevealEvent:
    def test_animate_by_row_returns_table_reveal_event(self, small_table):
        result = small_table.animate_by_row(_StubAnim, start_time=0, total_duration=3.0)
        assert isinstance(result, TableRevealEvent)
        assert isinstance(result, CompositeAnimationEvent)

    def test_animate_by_row_pair_count(self, small_table):
        result = small_table.animate_by_row(_StubAnim, start_time=0, total_duration=3.0)
        assert len(result.pairs) == 3  # one per row

    def test_animate_by_row_drawables_are_row_groups(self, small_table):
        result = small_table.animate_by_row(_StubAnim, start_time=0, total_duration=3.0)
        for i, (_, drawable) in enumerate(result.pairs):
            assert drawable is small_table.row_groups[i]

    def test_animate_by_row_staggered_start_times(self, small_table):
        result = small_table.animate_by_row(_StubAnim, start_time=1.0, total_duration=3.0)
        row_dur = 3.0 / 3
        for r, (event, _) in enumerate(result.pairs):
            assert event.start_time == pytest.approx(1.0 + r * row_dur)

    def test_animate_by_row_equal_durations(self, small_table):
        result = small_table.animate_by_row(_StubAnim, start_time=0, total_duration=6.0)
        for event, _ in result.pairs:
            assert event.duration == pytest.approx(2.0)

    def test_animate_by_row_extra_kwargs_forwarded(self, small_table):
        result = small_table.animate_by_row(_StubAnim, start_time=0, total_duration=3.0, custom_flag=True)
        for event, _ in result.pairs:
            assert event.extra.get("custom_flag") is True

    def test_animate_by_cell_returns_table_reveal_event(self, small_table):
        result = small_table.animate_by_cell(_StubAnim, start_time=0, total_duration=6.0)
        assert isinstance(result, TableRevealEvent)

    def test_animate_by_cell_pair_count(self, small_table):
        result = small_table.animate_by_cell(_StubAnim, start_time=0, total_duration=6.0)
        assert len(result.pairs) == 6  # 3 rows × 2 cols

    def test_animate_by_cell_drawables_are_cells(self, small_table):
        result = small_table.animate_by_cell(_StubAnim, start_time=0, total_duration=6.0)
        for idx, (_, drawable) in enumerate(result.pairs):
            r, c = divmod(idx, small_table.n_cols)
            assert drawable is small_table.cells[r][c]

    def test_animate_by_cell_row_major_order(self, small_table):
        result = small_table.animate_by_cell(_StubAnim, start_time=0, total_duration=6.0)
        n_cells = small_table.n_rows * small_table.n_cols
        cell_dur = 6.0 / n_cells
        for idx, (event, _) in enumerate(result.pairs):
            assert event.start_time == pytest.approx(idx * cell_dur)

    def test_composite_event_span(self, small_table):
        result = small_table.animate_by_row(_StubAnim, start_time=2.0, total_duration=3.0)
        # CompositeAnimationEvent.start_time = min sub-event start
        assert result.start_time == pytest.approx(2.0)

    def test_events_list_length_in_composite(self, small_table):
        result = small_table.animate_by_row(_StubAnim, start_time=0, total_duration=3.0)
        assert len(result.events) == 3


# ---------------------------------------------------------------------------
# add_to_scene integration
# ---------------------------------------------------------------------------

class TestTableAddToScene:
    """
    Verify add_to_scene() calls scene.add() for every (event, drawable) pair.
    Uses a spy object rather than a real Scene to stay fast and deterministic.
    """

    class _SceneSpy:
        def __init__(self):
            self.calls = []

        def add(self, event, drawable):
            self.calls.append((event, drawable))

    def test_add_to_scene_row_calls_scene_add_per_row(self, small_table):
        spy = self._SceneSpy()
        reveal = small_table.animate_by_row(_StubAnim, start_time=0, total_duration=3.0)
        reveal.add_to_scene(spy)
        assert len(spy.calls) == 3

    def test_add_to_scene_cell_calls_scene_add_per_cell(self, small_table):
        spy = self._SceneSpy()
        reveal = small_table.animate_by_cell(_StubAnim, start_time=0, total_duration=6.0)
        reveal.add_to_scene(spy)
        assert len(spy.calls) == 6

    def test_add_to_scene_passes_correct_drawables(self, small_table):
        spy = self._SceneSpy()
        reveal = small_table.animate_by_row(_StubAnim, start_time=0, total_duration=3.0)
        reveal.add_to_scene(spy)
        for (_, actual_drawable), (_, expected_drawable) in zip(spy.calls, reveal.pairs):
            assert actual_drawable is expected_drawable

    def test_add_to_scene_passes_correct_events(self, small_table):
        spy = self._SceneSpy()
        reveal = small_table.animate_by_cell(_StubAnim, start_time=0, total_duration=6.0)
        reveal.add_to_scene(spy)
        for (actual_event, _), (expected_event, _) in zip(spy.calls, reveal.pairs):
            assert actual_event is expected_event


# ---------------------------------------------------------------------------
# Visual regression
# ---------------------------------------------------------------------------

def _table_opsset() -> OpsSet:
    t = Table(
        top_left=(50.0, 80.0),
        n_rows=4,
        n_cols=3,
        cell_width=180.0,
        cell_height=60.0,
        headers=["Product", "Qty", "Price"],
        data=[
            ["Widget A", "12", "$4.50"],
            ["Widget B", "7",  "$9.00"],
            ["Widget C", "20", "$2.25"],
        ],
        header_stroke_style=StrokeStyle(color=(0.1, 0.1, 0.6), width=2),
        header_fill_style=FillStyle(color=(0.8, 0.85, 1.0)),
    )
    return t.draw()


class TestTableVisual:
    def test_table_snapshot(self, render_to_png_bytes, snapshot):
        png = render_to_png_bytes(_table_opsset(), width=700, height=400)
        snapshot.assert_match(png, "table.png")

    def test_table_self_consistency(self, render_to_png_bytes):
        from skimage.metrics import structural_similarity as ssim
        from skimage import io as skio

        np.random.seed(42)
        png_a = render_to_png_bytes(_table_opsset(), width=700, height=400)
        np.random.seed(42)
        png_b = render_to_png_bytes(_table_opsset(), width=700, height=400)

        def to_arr(b):
            return skio.imread(io.BytesIO(b))

        score = ssim(to_arr(png_a), to_arr(png_b), channel_axis=-1)
        assert score == pytest.approx(1.0)
