"""Unified Cairo backend loader with automatic pycairo -> cairocffi fallback.

Ensures `import cairo` works across platforms:
1. Tries `pycairo` (`import cairo`) first (which ships self-contained binary wheels on
   Windows, macOS, and manylinux).
2. If `pycairo` is unavailable or `HANDANIM_CAIRO_BACKEND=cairocffi` is set, falls back
   to pure-Python `cairocffi`, automatically searching Homebrew (`/opt/homebrew/lib`,
   `/usr/local/lib`), Conda (`$CONDA_PREFIX/lib`), and system library directories so
   users on macOS Apple Silicon or Conda do not need to configure `DYLD_FALLBACK_LIBRARY_PATH`.
3. Installs `cairocffi` as `sys.modules["cairo"]` via `cairocffi.install_as_pycairo()` and
   adds context-manager (`__enter__`/`__exit__`) compatibility to `cairocffi.Surface`.
"""

from __future__ import annotations

import ctypes.util
import os
import sys
from types import ModuleType

_ACTIVE_BACKEND: str | None = None
_FIND_LIBRARY_PATCHED: bool = False


def _patch_find_library_for_cairo() -> None:
    """Extend `ctypes.util.find_library` to search Homebrew, Conda, and local lib dirs."""
    global _FIND_LIBRARY_PATCHED
    if _FIND_LIBRARY_PATCHED:
        return

    orig_find_library = ctypes.util.find_library

    search_dirs: list[str] = [
        "/opt/homebrew/opt/cairo/lib",
        "/opt/homebrew/lib",
        "/usr/local/opt/cairo/lib",
        "/usr/local/lib",
        "/opt/local/lib",
        os.path.join(sys.prefix, "lib"),
        os.path.join(sys.prefix, "Library", "bin"),
    ]
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        search_dirs.append(os.path.join(conda_prefix, "lib"))
        search_dirs.append(os.path.join(conda_prefix, "Library", "bin"))

    def _enhanced_find_library(name: str) -> str | None:
        found = orig_find_library(name)
        if found:
            return found
        if "cairo" not in name.lower():
            return None
        candidates = (
            f"lib{name}.2.dylib",
            f"lib{name}.dylib",
            "libcairo.2.dylib",
            "libcairo.dylib",
            f"lib{name}.so.2",
            f"lib{name}.so",
            "libcairo.so.2",
            f"{name}.dll",
            f"lib{name}-2.dll",
            "libcairo-2.dll",
        )
        for directory in search_dirs:
            for filename in candidates:
                full_path = os.path.join(directory, filename)
                if os.path.exists(full_path):
                    return full_path
        return None

    ctypes.util.find_library = _enhanced_find_library
    _FIND_LIBRARY_PATCHED = True


def _ensure_surface_context_manager(cairo_mod: ModuleType) -> None:
    """Ensure `cairo.Surface` supports `with cairo.SVGSurface(...) as surface:` in cairocffi."""
    surface_cls = getattr(cairo_mod, "Surface", None)
    if surface_cls is not None and not hasattr(surface_cls, "__enter__"):
        surface_cls.__enter__ = lambda self: self  # type: ignore[attr-defined]
        surface_cls.__exit__ = lambda self, exc_type, exc_val, exc_tb: self.finish()  # type: ignore[attr-defined]


def _load_cairocffi() -> ModuleType:
    """Load `cairocffi` and register it as `cairo` in `sys.modules`."""
    _patch_find_library_for_cairo()
    import cairocffi

    _ensure_surface_context_manager(cairocffi)
    cairocffi.install_as_pycairo()
    return cairocffi


def ensure_cairo(prefer: str | None = None) -> ModuleType:
    """Import and return a pycairo-compatible `cairo` module (`pycairo` or `cairocffi`)."""
    global _ACTIVE_BACKEND

    requested = (prefer or os.environ.get("HANDANIM_CAIRO_BACKEND", "auto")).strip().lower()

    if requested == "cairocffi":
        mod = _load_cairocffi()
        _ACTIVE_BACKEND = "cairocffi"
        return mod

    try:
        import cairo as pycairo_mod

        _ensure_surface_context_manager(pycairo_mod)
        _ACTIVE_BACKEND = (
            "cairocffi" if getattr(pycairo_mod, "__name__", "") == "cairocffi" else "pycairo"
        )
        return pycairo_mod
    except Exception as pycairo_err:
        if requested == "pycairo":
            raise
        try:
            mod = _load_cairocffi()
            _ACTIVE_BACKEND = "cairocffi"
            return mod
        except Exception as cairocffi_err:
            raise ImportError(
                "handanim requires Cairo graphics (`pycairo` or `cairocffi` + `libcairo`).\n"
                "Quick fixes by platform:\n"
                "  - Prebuilt wheel (Windows / macOS / Linux): pip install --only-binary=:all: pycairo\n"
                "  - macOS (Homebrew):                         brew install cairo && pip install pycairo cairocffi\n"
                "  - Ubuntu / Debian / Google Colab:           sudo apt-get update && sudo apt-get install -y libcairo2-dev && pip install pycairo\n"
                "  - Conda (any OS):                           conda install -c conda-forge cairo pycairo\n"
                f"(pycairo error: {pycairo_err}; cairocffi error: {cairocffi_err})"
            ) from cairocffi_err


def get_cairo_backend() -> str:
    """Return the name of the active Cairo backend (`'pycairo'` or `'cairocffi'`)."""
    if _ACTIVE_BACKEND is None:
        ensure_cairo()
    assert _ACTIVE_BACKEND is not None
    return _ACTIVE_BACKEND


cairo = ensure_cairo()

__all__ = ["cairo", "ensure_cairo", "get_cairo_backend"]
