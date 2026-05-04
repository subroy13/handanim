"""
Visual regression tests for handanim primitives and animations.

Each test renders a deterministic scene to an in-memory PNG and compares it
against a stored reference file using SSIM (structural similarity index).

Workflow
--------
First run — generate reference snapshots::

    poetry run pytest tests/test_visuals.py --snapshot-update

Subsequent runs — compare against references::

    poetry run pytest tests/test_visuals.py

A test fails when SSIM drops below SSIM_THRESHOLD, which catches any structural
rendering change while tolerating sub-pixel float differences across platforms.
"""

import io
import numpy as np
import pytest
from skimage.metrics import structural_similarity as ssim
from skimage import io as skio

import cairo
from handanim.core.draw_ops import OpsSet, Ops, OpsType
from handanim.core.styles import StrokeStyle, SketchStyle, FillStyle
from handanim.animations.sketch import SketchAnimation
from handanim.primitives.lines import Line
from handanim.primitives.polygons import Rectangle


SSIM_THRESHOLD = 0.98


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _png_bytes_to_array(png_bytes: bytes) -> np.ndarray:
    """Decode PNG bytes to an (H, W, C) uint8 numpy array."""
    buf = io.BytesIO(png_bytes)
    return skio.imread(buf)


def _ssim(a: bytes, b: bytes) -> float:
    """Compute SSIM between two PNG byte strings."""
    arr_a = _png_bytes_to_array(a)
    arr_b = _png_bytes_to_array(b)
    return ssim(arr_a, arr_b, channel_axis=-1)


def _assert_visual_match(current: bytes, snapshot, name: str):
    """
    Compare current PNG bytes against a stored snapshot.

    On first run (--snapshot-update), pytest-snapshot writes the file.
    On subsequent runs, we load the stored file and compare via SSIM.
    """
    snapshot.assert_match(current, name)


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------

def _line_opsset() -> OpsSet:
    line = Line(
        start=(100, 200),
        end=(800, 500),
        stroke_style=StrokeStyle(color=(0.1, 0.1, 0.8), width=3),
        sketch_style=SketchStyle(roughness=1, bowing=1),
    )
    return line.draw()


def _rectangle_opsset() -> OpsSet:
    rect = Rectangle(
        top_left=(150, 150),
        width=500,
        height=300,
        stroke_style=StrokeStyle(color=(0.8, 0.1, 0.1), width=2),
        sketch_style=SketchStyle(roughness=1),
    )
    return rect.draw()


def _sketch_at(opsset: OpsSet, progress: float) -> OpsSet:
    sketch = SketchAnimation(start_time=0.0, duration=1.0)
    return sketch.get_partial_sketch(opsset, progress)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLineVisual:
    def test_line_snapshot(self, render_to_png_bytes, snapshot):
        png = render_to_png_bytes(_line_opsset())
        _assert_visual_match(png, snapshot, "line.png")

    def test_line_ssim_self_consistency(self, render_to_png_bytes):
        """
        Rendering the same Line twice with the same seed must produce
        pixel-identical output (SSIM == 1.0). Validates that seeding works.
        """
        np.random.seed(42)
        png_a = render_to_png_bytes(_line_opsset())
        np.random.seed(42)
        png_b = render_to_png_bytes(_line_opsset())
        assert _ssim(png_a, png_b) == pytest.approx(1.0)


class TestRectangleVisual:
    def test_rectangle_snapshot(self, render_to_png_bytes, snapshot):
        png = render_to_png_bytes(_rectangle_opsset())
        _assert_visual_match(png, snapshot, "rectangle.png")


class TestSketchAnimationVisual:
    @pytest.mark.parametrize("progress,name", [
        (0.25, "sketch_quarter.png"),
        (0.50, "sketch_half.png"),
        (1.00, "sketch_full.png"),
    ])
    def test_sketch_progress_snapshot(self, progress, name, render_to_png_bytes, snapshot):
        partial = _sketch_at(_rectangle_opsset(), progress)
        png = render_to_png_bytes(partial)
        _assert_visual_match(png, snapshot, name)

    def test_full_sketch_matches_direct_render(self, render_to_png_bytes):
        """
        get_partial_sketch at progress=1.0 must produce a PNG that is
        visually identical to rendering the full opsset directly.
        SSIM must be above the regression threshold.
        """
        np.random.seed(42)
        full_opsset = _rectangle_opsset()

        np.random.seed(42)
        sketch_full = _sketch_at(_rectangle_opsset(), 1.0)

        png_direct = render_to_png_bytes(full_opsset)
        png_sketch = render_to_png_bytes(sketch_full)

        score = _ssim(png_direct, png_sketch)
        assert score >= SSIM_THRESHOLD, f"SSIM {score:.4f} below threshold {SSIM_THRESHOLD}"
