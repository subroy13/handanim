"""
Visual regression tests for core primitive drawables: Line and Rectangle.

Workflow
--------
First run — generate reference snapshots::

    pytest tests/drawables/test_primitives.py --snapshot-update

Subsequent runs compare against the stored references.
"""

import io

import numpy as np
import pytest
from skimage.metrics import structural_similarity as ssim
from skimage import io as skio

from handanim.core.draw_ops import OpsSet
from handanim.core.styles import StrokeStyle, SketchStyle
from handanim.primitives.lines import Line
from handanim.primitives.polygons import Rectangle


SSIM_THRESHOLD = 0.98


def _png_bytes_to_array(png_bytes: bytes) -> np.ndarray:
    return skio.imread(io.BytesIO(png_bytes))


def _ssim(a: bytes, b: bytes) -> float:
    return ssim(_png_bytes_to_array(a), _png_bytes_to_array(b), channel_axis=-1)


def _line_opsset() -> OpsSet:
    return Line(
        start=(100, 200),
        end=(800, 500),
        stroke_style=StrokeStyle(color=(0.1, 0.1, 0.8), width=3),
        sketch_style=SketchStyle(roughness=1, bowing=1),
    ).draw()


def _rectangle_opsset() -> OpsSet:
    return Rectangle(
        top_left=(150, 150),
        width=500,
        height=300,
        stroke_style=StrokeStyle(color=(0.8, 0.1, 0.1), width=2),
        sketch_style=SketchStyle(roughness=1),
    ).draw()


class TestLineVisual:
    def test_line_snapshot(self, render_to_png_bytes, snapshot):
        snapshot.assert_match(render_to_png_bytes(_line_opsset()), "line.png")

    def test_line_ssim_self_consistency(self, render_to_png_bytes):
        np.random.seed(42)
        a = render_to_png_bytes(_line_opsset())
        np.random.seed(42)
        b = render_to_png_bytes(_line_opsset())
        assert _ssim(a, b) == pytest.approx(1.0)


class TestRectangleVisual:
    def test_rectangle_snapshot(self, render_to_png_bytes, snapshot):
        snapshot.assert_match(render_to_png_bytes(_rectangle_opsset()), "rectangle.png")
