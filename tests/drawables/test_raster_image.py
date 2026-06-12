"""Tests for RasterImage primitive and IMAGE OpsType integration."""

import os
import cairo
import numpy as np
import pytest

from handanim.core.draw_ops import BoundingBox, Ops, OpsSet, OpsType
from handanim.core.scene import Scene
from handanim.core.styles import SketchStyle
from handanim.animations.sketch import SketchAnimation
from handanim.animations.fade import FadeInAnimation, FadeOutAnimation
from handanim.primitives.raster_image import RasterImage


@pytest.fixture
def png_path(tmp_path):
    """Create a 20x10 red PNG and return its path."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 20, 10)
    ctx = cairo.Context(surface)
    ctx.set_source_rgb(1, 0, 0)
    ctx.paint()
    p = str(tmp_path / "red.png")
    surface.write_to_png(p)
    return p


@pytest.fixture
def jpg_path(tmp_path):
    """Create a 30x20 blue JPEG and return its path."""
    from PIL import Image
    img = Image.new("RGB", (30, 20), color=(0, 0, 255))
    p = str(tmp_path / "blue.jpg")
    img.save(p)
    return p


# ---------------------------------------------------------------------------
# Construction & draw
# ---------------------------------------------------------------------------

class TestRasterImageConstruction:
    def test_draw_returns_single_image_op(self, png_path):
        ri = RasterImage(png_path, position=(10, 20), width=100, height=50)
        ops = ri.draw()
        assert len(ops.opsset) == 1
        assert ops.opsset[0].type == OpsType.IMAGE

    def test_explicit_width_and_height(self, png_path):
        ri = RasterImage(png_path, position=(0, 0), width=200, height=100)
        data = ri.draw().opsset[0].data
        assert data["width"] == 200
        assert data["height"] == 100

    def test_width_only_preserves_aspect_ratio(self, png_path):
        ri = RasterImage(png_path, position=(0, 0), width=100)
        data = ri.draw().opsset[0].data
        assert data["width"] == 100
        assert data["height"] == pytest.approx(50.0)

    def test_height_only_preserves_aspect_ratio(self, png_path):
        ri = RasterImage(png_path, position=(0, 0), height=50)
        data = ri.draw().opsset[0].data
        assert data["height"] == 50
        assert data["width"] == pytest.approx(100.0)

    def test_no_size_uses_pixel_dimensions(self, png_path):
        ri = RasterImage(png_path, position=(0, 0))
        data = ri.draw().opsset[0].data
        assert data["width"] == 20.0
        assert data["height"] == 10.0

    def test_position_stored_correctly(self, png_path):
        ri = RasterImage(png_path, position=(50, 75))
        data = ri.draw().opsset[0].data
        assert data["x"] == 50
        assert data["y"] == 75

    def test_default_opacity_is_one(self, png_path):
        ri = RasterImage(png_path, position=(0, 0))
        data = ri.draw().opsset[0].data
        assert data["opacity"] == 1.0

    def test_custom_opacity(self, png_path):
        ri = RasterImage(png_path, position=(0, 0), opacity=0.5)
        data = ri.draw().opsset[0].data
        assert data["opacity"] == 0.5

    def test_jpeg_loading(self, jpg_path):
        ri = RasterImage(jpg_path, position=(0, 0), width=100)
        ops = ri.draw()
        assert len(ops.opsset) == 1
        assert ops.opsset[0].type == OpsType.IMAGE


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------

class TestRasterImageBBox:
    def test_bbox_matches_position_and_size(self, png_path):
        ri = RasterImage(png_path, position=(10, 20), width=100, height=50)
        bbox = ri.draw().get_bbox()
        assert bbox.min_x == 10
        assert bbox.min_y == 20
        assert bbox.max_x == 110
        assert bbox.max_y == 70

    def test_bbox_center(self, png_path):
        ri = RasterImage(png_path, position=(0, 0), width=200, height=100)
        cx, cy = ri.draw().get_bbox().center
        assert cx == pytest.approx(100)
        assert cy == pytest.approx(50)


# ---------------------------------------------------------------------------
# Transforms
# ---------------------------------------------------------------------------

class TestRasterImageTransforms:
    def test_translate(self, png_path):
        ri = RasterImage(png_path, position=(10, 20), width=100, height=50)
        ops = ri.draw()
        ops.translate(30, 40)
        bbox = ops.get_bbox()
        assert bbox.min_x == pytest.approx(40)
        assert bbox.min_y == pytest.approx(60)
        assert bbox.width == pytest.approx(100)
        assert bbox.height == pytest.approx(50)

    def test_scale(self, png_path):
        ri = RasterImage(png_path, position=(0, 0), width=100, height=50)
        ops = ri.draw()
        ops.scale(2.0, 2.0)
        bbox = ops.get_bbox()
        assert bbox.width == pytest.approx(200)
        assert bbox.height == pytest.approx(100)

    def test_rotate_stores_angle(self, png_path):
        ri = RasterImage(png_path, position=(100, 100), width=100, height=50)
        ops = ri.draw()
        ops.rotate(45.0)
        data = ops.opsset[0].data
        assert data.get("rotation") == pytest.approx(45.0)

    def test_drawable_translate_returns_new(self, png_path):
        ri = RasterImage(png_path, position=(10, 20), width=100, height=50)
        moved = ri.translate(50, 50)
        assert moved is not ri
        bbox = moved.draw().get_bbox()
        assert bbox.min_x == pytest.approx(60)
        assert bbox.min_y == pytest.approx(70)


# ---------------------------------------------------------------------------
# Scene integration
# ---------------------------------------------------------------------------

class TestRasterImageScene:
    def test_sketch_animation_renders(self, png_path, tmp_path):
        s = Scene(width=400, height=300, fps=4)
        img = RasterImage(png_path, position=(100, 100), width=200, height=100)
        s.add(SketchAnimation(start_time=0.0, duration=0.5), img)
        out = str(tmp_path / "out.svg")
        s.render_snapshot(out, frame_in_seconds=0.5)
        assert os.path.exists(out)
        assert os.path.getsize(out) > 0

    def test_sketch_at_half_progress_has_partial_opacity(self, png_path):
        img = RasterImage(png_path, position=(0, 0), width=100, height=50)
        anim = SketchAnimation(start_time=0.0, duration=1.0)
        result = anim._apply(img.draw(), 0.5)
        assert len(result.opsset) > 0
        for op in result.opsset:
            if op.type == OpsType.IMAGE:
                assert op.partial < 1.0

    def test_fadein_modifies_image_opacity(self, png_path):
        img = RasterImage(png_path, position=(0, 0), width=100, height=50)
        anim = FadeInAnimation(start_time=0.0, duration=1.0)
        result = anim._apply(img.draw(), 0.5)
        for op in result.opsset:
            if op.type == OpsType.IMAGE:
                assert op.data["opacity"] == pytest.approx(0.5)

    def test_fadeout_modifies_image_opacity(self, png_path):
        img = RasterImage(png_path, position=(0, 0), width=100, height=50)
        anim = FadeOutAnimation(start_time=0.0, duration=1.0)
        result = anim._apply(img.draw(), 0.5)
        for op in result.opsset:
            if op.type == OpsType.IMAGE:
                assert op.data["opacity"] == pytest.approx(0.5)

    def test_pdf_render(self, png_path, tmp_path):
        s = Scene(width=400, height=300, fps=4)
        img = RasterImage(png_path, position=(100, 100), width=200, height=100)
        s.add(SketchAnimation(start_time=0.0, duration=0.5), img)
        out = str(tmp_path / "out.pdf")
        s.render_snapshot(out, frame_in_seconds=0.5)
        assert os.path.exists(out)
        assert os.path.getsize(out) > 0
