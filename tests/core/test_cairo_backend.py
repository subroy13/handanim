"""Tests for automatic Cairo backend selection (pycairo -> cairocffi fallback) and bundled FFmpeg."""

from pathlib import Path
import imageio_ffmpeg

from handanim import Circle, Scene, SketchAnimation, get_cairo_backend
from handanim.core._cairo import ensure_cairo


def test_cairo_backend_auto_and_cairocffi_fallback():
    # Default auto selection loads pycairo or cairocffi
    mod_auto = ensure_cairo()
    assert mod_auto is not None
    assert get_cairo_backend() in ("pycairo", "cairocffi")

    # Forcing cairocffi works without DYLD_FALLBACK_LIBRARY_PATH on macOS/Homebrew
    mod_cffi = ensure_cairo(prefer="cairocffi")
    assert getattr(mod_cffi, "__name__", "") == "cairocffi"
    assert get_cairo_backend() == "cairocffi"
    assert hasattr(mod_cffi.Surface, "__enter__")
    assert hasattr(mod_cffi.Surface, "__exit__")

    # Render a frame using the cairocffi backend
    scene = Scene(width=160, height=120, fps=12)
    scene.add(SketchAnimation(start_time=0.0, duration=0.5), Circle(center=(80, 60), radius=30))
    frame = scene.render_frame(0.5)
    assert frame.shape == (120, 160, 3)

    # Restore auto backend
    ensure_cairo(prefer="auto")


def test_bundled_imageio_ffmpeg_executable():
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    assert ffmpeg_exe
    assert Path(ffmpeg_exe).exists()
