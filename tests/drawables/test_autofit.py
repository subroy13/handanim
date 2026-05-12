"""
Tests for content-autofitting features:
  - BoundingBox type and its derived properties
  - Drawable.get_bbox() on concrete shape primitives
  - Text.autofit() — scales font_size so text fills a BoundingBox
  - Text.wrap()    — pre-computes line breaks to fit text within a BoundingBox width
"""

import numpy as np
import pytest

from handanim.core.draw_ops import BoundingBox, OpsSet
from handanim.core.styles import SketchStyle
from handanim.primitives.lines import Line
from handanim.primitives.polygons import Rectangle
from handanim.primitives.text import Text


# Sketch style with all randomness removed — deterministic endpoints for geometry tests.
FLAT = SketchStyle(roughness=0, bowing=0)


# ---------------------------------------------------------------------------
# BoundingBox
# ---------------------------------------------------------------------------

class TestBoundingBox:
    def test_width_and_height(self):
        bb = BoundingBox(10, 20, 110, 70)
        assert bb.width == 100
        assert bb.height == 50

    def test_center(self):
        bb = BoundingBox(0, 0, 100, 60)
        assert bb.center == (50.0, 30.0)

    def test_top_left(self):
        bb = BoundingBox(15, 25, 80, 90)
        assert bb.top_left == (15, 25)

    def test_bottom_right(self):
        bb = BoundingBox(15, 25, 80, 90)
        assert bb.bottom_right == (80, 90)

    def test_zero_area_point_bbox(self):
        bb = BoundingBox(50, 50, 50, 50)
        assert bb.width == 0
        assert bb.height == 0

    def test_dataclass_equality(self):
        assert BoundingBox(1, 2, 3, 4) == BoundingBox(1, 2, 3, 4)
        assert BoundingBox(1, 2, 3, 4) != BoundingBox(1, 2, 3, 5)


# ---------------------------------------------------------------------------
# Drawable.get_bbox()
# ---------------------------------------------------------------------------

class TestDrawableGetBbox:
    def test_returns_bounding_box_type(self):
        rect = Rectangle((0, 0), 100, 50, sketch_style=FLAT)
        assert isinstance(rect.get_bbox(), BoundingBox)

    def test_rectangle_bbox_width_and_height(self):
        rect = Rectangle((200, 300), 400, 200, sketch_style=FLAT)
        bbox = rect.get_bbox()
        # With roughness=0 and bowing=0, line endpoints are exact.
        assert np.isclose(bbox.width, 400, atol=1)
        assert np.isclose(bbox.height, 200, atol=1)

    def test_rectangle_bbox_origin(self):
        rect = Rectangle((200, 300), 400, 200, sketch_style=FLAT)
        bbox = rect.get_bbox()
        assert np.isclose(bbox.min_x, 200, atol=1)
        assert np.isclose(bbox.min_y, 300, atol=1)

    def test_line_has_positive_extent(self):
        line = Line((0, 0), (300, 200), sketch_style=FLAT)
        bbox = line.get_bbox()
        assert bbox.width > 0
        assert bbox.height > 0

    def test_larger_rectangle_has_larger_bbox(self):
        small = Rectangle((0, 0), 100, 50, sketch_style=FLAT)
        large = Rectangle((0, 0), 400, 200, sketch_style=FLAT)
        assert large.get_bbox().width > small.get_bbox().width
        assert large.get_bbox().height > small.get_bbox().height

    def test_offset_rectangle_shifts_bbox(self):
        # Two same-sized rectangles placed 200 units apart in x and 150 in y.
        rect_a = Rectangle((0, 0), 100, 50, sketch_style=FLAT)
        rect_b = Rectangle((200, 150), 100, 50, sketch_style=FLAT)
        bbox_a = rect_a.get_bbox()
        bbox_b = rect_b.get_bbox()
        assert np.isclose(bbox_b.min_x - bbox_a.min_x, 200, atol=1)
        assert np.isclose(bbox_b.min_y - bbox_a.min_y, 150, atol=1)


# ---------------------------------------------------------------------------
# Text.autofit()
# ---------------------------------------------------------------------------

class TestTextAutofit:
    def test_autofit_changes_font_size(self):
        label = Text("hello", position=(0, 0), font_size=12)
        original = label.font_size
        label.autofit(BoundingBox(0, 0, 500, 100))
        assert label.font_size != original

    def test_autofit_rendered_width_fits_within_bbox(self):
        label = Text("hello", position=(0, 0), font_size=12)
        bbox = BoundingBox(0, 0, 400, 150)
        label.autofit(bbox)
        rendered = label.draw().get_bbox()
        # 10 % tolerance accounts for roughness jitter in the rendered glyph strokes.
        assert rendered.width <= bbox.width * 1.1

    def test_autofit_rendered_height_fits_within_bbox(self):
        label = Text("hello", position=(0, 0), font_size=12)
        bbox = BoundingBox(0, 0, 400, 150)
        label.autofit(bbox)
        rendered = label.draw().get_bbox()
        assert rendered.height <= bbox.height * 1.1

    def test_wider_bbox_gives_larger_font_size(self):
        narrow = Text("hello", position=(0, 0), font_size=12)
        wide   = Text("hello", position=(0, 0), font_size=12)
        narrow.autofit(BoundingBox(0, 0, 200, 100))
        wide.autofit(BoundingBox(0, 0, 600, 100))
        assert wide.font_size > narrow.font_size

    def test_taller_bbox_gives_larger_font_size(self):
        short = Text("hello", position=(0, 0), font_size=12)
        tall  = Text("hello", position=(0, 0), font_size=12)
        short.autofit(BoundingBox(0, 0, 400, 50))
        tall.autofit(BoundingBox(0, 0, 400, 200))
        assert tall.font_size > short.font_size

    def test_autofit_returns_valid_opsset_on_draw(self):
        label = Text("hello", position=(0, 0), font_size=12)
        label.autofit(BoundingBox(0, 0, 400, 150))
        result = label.draw()
        assert isinstance(result, OpsSet)
        assert len(result.opsset) > 0


# ---------------------------------------------------------------------------
# Text.wrap()
# ---------------------------------------------------------------------------

class TestTextWrap:

    def _text(self, content: str, font_size: int = 50) -> Text:
        return Text(content, position=(0, 0), font_size=font_size)

    # --- state after wrap() ---

    def test_wrapped_lines_not_none_after_wrap(self):
        t = self._text("hello world")
        t.wrap(BoundingBox(0, 0, 500, 400))
        assert t._wrapped_lines is not None

    def test_position_set_to_bbox_top_left(self):
        t = self._text("hello world")
        bbox = BoundingBox(100, 200, 700, 500)
        t.wrap(bbox)
        assert t.position == (100, 200)

    def test_line_height_positive_after_wrap(self):
        t = self._text("hello world", font_size=50)
        t.wrap(BoundingBox(0, 0, 500, 400))
        assert t._line_height is not None
        assert t._line_height > 0

    def test_line_height_scales_with_font_size(self):
        small = self._text("hello", font_size=20)
        large = self._text("hello", font_size=80)
        small.wrap(BoundingBox(0, 0, 500, 800))
        large.wrap(BoundingBox(0, 0, 500, 800))
        assert large._line_height > small._line_height

    # --- line-breaking logic ---

    def test_single_word_stays_on_one_line(self):
        t = self._text("hello")
        t.wrap(BoundingBox(0, 0, 1000, 400))
        assert len(t._wrapped_lines) == 1
        assert t._wrapped_lines[0] == "hello"

    def test_text_that_fits_stays_on_one_line(self):
        t = self._text("hi", font_size=20)
        t.wrap(BoundingBox(0, 0, 2000, 400))
        assert len(t._wrapped_lines) == 1

    def test_long_text_wraps_into_multiple_lines(self):
        t = self._text("the quick brown fox jumps over the lazy dog", font_size=80)
        t.wrap(BoundingBox(0, 0, 300, 2000))
        assert len(t._wrapped_lines) > 1

    def test_no_line_exceeds_bbox_width(self):
        t = self._text("the quick brown fox jumps over the lazy dog", font_size=60)
        bbox = BoundingBox(0, 0, 400, 2000)
        t.wrap(bbox)
        for line in t._wrapped_lines:
            width = t._measure_text_width(line)
            assert width <= bbox.width, (
                f"Line '{line}' width {width:.1f} exceeds bbox width {bbox.width}"
            )

    def test_all_words_preserved_after_wrap(self):
        content = "the quick brown fox jumps"
        t = self._text(content, font_size=80)
        t.wrap(BoundingBox(0, 0, 200, 2000))
        reconstructed = " ".join(t._wrapped_lines).split()
        assert reconstructed == content.split()

    def test_narrower_bbox_produces_more_lines(self):
        t_narrow = self._text("the quick brown fox jumps over the lazy dog", font_size=60)
        t_wide   = self._text("the quick brown fox jumps over the lazy dog", font_size=60)
        t_narrow.wrap(BoundingBox(0, 0, 200, 2000))
        t_wide.wrap(BoundingBox(0, 0, 2000, 2000))
        assert len(t_narrow._wrapped_lines) >= len(t_wide._wrapped_lines)

    # --- re-wrapping ---

    def test_wrap_called_twice_updates_lines(self):
        t = self._text("the quick brown fox jumps over the lazy dog", font_size=60)
        t.wrap(BoundingBox(0, 0, 200, 2000))
        lines_narrow = len(t._wrapped_lines)
        t.wrap(BoundingBox(0, 0, 2000, 2000))
        lines_wide = len(t._wrapped_lines)
        assert lines_wide <= lines_narrow

    def test_wrap_updates_position_on_second_call(self):
        t = self._text("hello world")
        t.wrap(BoundingBox(0, 0, 500, 400))
        t.wrap(BoundingBox(300, 150, 800, 600))
        assert t.position == (300, 150)

    # --- draw() integration ---

    def test_draw_after_wrap_returns_non_empty_opsset(self):
        t = self._text("hello world foo bar", font_size=50)
        t.wrap(BoundingBox(0, 0, 300, 800))
        result = t.draw()
        assert isinstance(result, OpsSet)
        assert len(result.opsset) > 0

    def test_draw_without_wrap_still_works(self):
        # Wrapping is opt-in; single-line draw must be unaffected.
        t = self._text("hello", font_size=50)
        result = t.draw()
        assert isinstance(result, OpsSet)
        assert len(result.opsset) > 0
