import io
import sys
from pathlib import Path

import cairo
import numpy as np
import pytest

src_dir = str(Path(__file__).parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from handanim.core.draw_ops import OpsSet  # noqa: E402
from handanim.core.viewport import Viewport  # noqa: E402


@pytest.fixture(autouse=True)
def seed_numpy():
    """
    Seed numpy RNG before every test so that rough primitives (Line, Rectangle, etc.)
    produce identical jitter values across runs.
    """
    np.random.seed(42)


@pytest.fixture(autouse=True)
def set_snapshot_dir(snapshot):
    """Route all snapshot files to tests/snapshots/ and compare PNG snapshots with pixel tolerance."""
    snapshot.snapshot_dir = Path("tests/snapshots")
    orig_assert_match = snapshot.assert_match

    def _tolerant_assert_match(value, snapshot_name):
        if getattr(snapshot, "_snapshot_update", False) or not isinstance(value, bytes) or not str(snapshot_name).endswith(".png"):
            return orig_assert_match(value, snapshot_name)

        snap_path = Path(snapshot.snapshot_dir) / str(snapshot_name)
        if not snap_path.is_file():
            return orig_assert_match(value, snapshot_name)

        from PIL import Image

        actual_img = np.asarray(Image.open(io.BytesIO(value)).convert("RGB"), dtype=np.float32)
        expected_img = np.asarray(Image.open(snap_path).convert("RGB"), dtype=np.float32)
        assert actual_img.shape == expected_img.shape, (
            f"Snapshot {snapshot_name} shape mismatch: {actual_img.shape} vs {expected_img.shape}"
        )
        # Allow minor Cairo anti-aliasing / FreeType font rasterization differences across OS & library versions
        mad = float(np.mean(np.abs(actual_img - expected_img)))
        frac_diff = float(np.mean(np.max(np.abs(actual_img - expected_img), axis=-1) > 32.0))
        assert mad <= 8.0 and frac_diff <= 0.05, (
            f"Snapshot {snapshot_name} diverged beyond tolerance (mean abs diff={mad:.2f}, differing pixels={frac_diff * 100:.2f}%)"
        )

    snapshot.assert_match = _tolerant_assert_match


@pytest.fixture
def render_to_png_bytes():
    """
    Factory fixture: renders an OpsSet to an in-memory PNG and returns the raw bytes.

    Usage::

        def test_something(render_to_png_bytes):
            png = render_to_png_bytes(my_opsset)
    """

    def _render(opsset: OpsSet, width: int = 400, height: int = 300) -> bytes:
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)

        # white background
        ctx.set_source_rgb(1, 1, 1)
        ctx.paint()

        viewport = Viewport(
            world_xrange=(0, 1000),
            world_yrange=(0, 750),
            screen_width=width,
            screen_height=height,
            margin=10,
        )
        viewport.apply_to_context(ctx)
        opsset.render(ctx)

        buf = io.BytesIO()
        surface.write_to_png(buf)
        return buf.getvalue()

    return _render
