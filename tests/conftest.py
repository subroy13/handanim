import io
import numpy as np
import pytest
import cairo

from handanim.core.draw_ops import OpsSet
from handanim.core.viewport import Viewport


@pytest.fixture(autouse=True)
def seed_numpy():
    """
    Seed numpy RNG before every test so that rough primitives (Line, Rectangle, etc.)
    produce identical jitter values across runs.
    """
    np.random.seed(42)


@pytest.fixture(autouse=True)
def set_snapshot_dir(snapshot):
    """Route all snapshot files to tests/snapshots/ regardless of test file location."""
    snapshot.snapshot_dir = "tests/snapshots"


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
