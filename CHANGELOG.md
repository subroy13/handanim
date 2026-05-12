# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Removed
- `SVG` legacy primitive (`primitives/svg.py`) — deleted entirely; use `VectorSVG` for all SVG import
- `svgpathtools` dev dependency — no longer needed now that `svg.py` is gone
- `SVG` export removed from `primitives/__init__.py`

### Changed
- `Math.custom_glyph_opsset` now uses `svgelements` (already a runtime dependency) to parse custom font glyph paths, replacing the `SVG`/`svgpathtools` pipeline; bounding box is computed via `OpsSet.get_bbox()` rather than `svgpathtools.Path.bbox()`

### Added
- `RotateAnimation` — animates an OpsSet rotating by a configurable angle around an explicit pivot or the center of gravity
- `ColorTransitionAnimation` — interpolates every `SET_PEN` color in an OpsSet between `start_color` and `end_color` across progress
- `CameraAnimation` — animates the scene viewport (pan/zoom) over time via `scene.add_camera()`; world-range interpolation with optional explicit `from_*` range
- `Scene.add_camera()` / `Scene._get_viewport_at()` — camera event pipeline decoupled from the drawable pipeline
- Test suite reorganized into subdirectories: `tests/animations/`, `tests/drawables/`, `tests/core/`
- Per-animation test files: `test_sketch.py`, `test_rotate.py`, `test_color_transition.py`, `test_camera.py`

### Changed
- `OpsSet.__init__` now accepts `Sequence[dict | Ops] | None` (was `list[dict | Ops]`) — resolves list-invariance mypy errors across the animation layer
- `DrawableGroup.__init__` `elements` parameter changed to `Sequence[Drawable]`

### Fixed
- `fillpatterns.py`: variable shadowing bug where `line` (list) was overwritten by `Line` object — `.draw()` was silently called on a list
- `fillpatterns.py`: `Ops(OpsType.CLOSE_PATH)` missing required `data` argument
- `arrow.py`: `*self.args` unpacked after keyword arguments (`start=`, `end=`) — multiple-values-for-keyword-argument bug; dropped the redundant positional passthrough
- `svg.py` / `vector_svg.py`: same star-arg-after-keyword pattern in `cls(...)` classmethod calls

### Developer
- Added `[tool.ruff]` and `[tool.mypy]` config to `pyproject.toml`
- 335 ruff violations auto-fixed (import modernization, whitespace, type-hint syntax)
- All remaining manual violations resolved: B026, B006, E731, B905
- Zero mypy errors in `src/handanim` (non-strict mode)
- Added `.pre-commit-config.yaml` — ruff runs on every commit
- Updated `DEVELOPMENT.md`: fixed stale test paths, added Linting, Type Checking, Pre-commit sections

---

## [0.1.0] — 2025-01-01

Initial public release.

### Added

**Core engine**
- `Ops` / `OpsSet` — universal drawing instruction format; Cairo-backed rendering
- `OpsSet` geometry transforms: `translate`, `scale`, `rotate`
- `OpsSet.get_bbox()` / `get_center_of_gravity()` / `quick_view()`
- `BoundingBox` helper type with `top_left`, `width`, `height`
- `Drawable` base class with immutable transform API (`.translate()`, `.scale()`, `.rotate()` return new objects)
- `TransformedDrawable` — deferred transform that wraps a base drawable
- `DrawableGroup` — batch drawable with `"series"` and `"parallel"` grouping modes
- `DrawableCache` — static object cache and group-transform cache for rendering performance
- `AnimationEvent` — base class with `start_time`, `duration`, `easing_fun`, `subdivide()`
- `CompositeAnimationEvent` — chains multiple animation events
- `AnimationEventType.CREATION` / `MUTATION` — controls object visibility timeline
- `Scene` — frame-based rendering orchestrator with `add()`, `render()`, `render_snapshot()`
- `Viewport` — world-to-screen coordinate mapping with `apply_to_context()`
- `StrokeStyle`, `FillStyle`, `SketchStyle` style types

**Primitives**
- `Line`, `LinearPath` — rough sketchy lines with bowing and jitter
- `Curve` — smooth multi-point bezier curve with roughness
- `Arrow`, `CurvedArrow` — directional arrows with `->`, `->>`, `-|>` head styles
- `Polygon`, `Rectangle`, `Square`, `NGon`, `RoundedRectangle`, `RoundedSquare`
- `Ellipse`, `Circle`, `GlowDot`
- `Text` — handwritten font rendering from bundled stroke fonts; `autofit(bbox)` for automatic sizing
- `Math` — LaTeX expression rendering via matplotlib MathTextParser
- `Eraser` — whiteout animation with zigzag human-like motion
- `VectorSVG` — full-fidelity SVG import (color, fill, opacity, transforms) via `svgelements`
- `SVG` — legacy path-only SVG import (deprecated; `VectorSVG` preferred)
- `FlowchartNode`, `FlowchartDiamond`, `FlowchartConnector`, `Flowchart` — declarative flowchart builder
- `Table` — grid of Rectangle + Text cells with header styling, `animate_by_row()` / `animate_by_cell()`

**Animations**
- `SketchAnimation` — progressive stroke reveal (CREATION type)
- `FadeInAnimation`, `FadeOutAnimation` — opacity fade via SET_PEN alpha
- `ZoomInAnimation`, `ZoomOutAnimation` — scale from/to center
- `TranslateToAnimation`, `TranslateFromAnimation`, `TranslateToPersistAnimation`

**Stylings**
- Named color constants (`BLUE`, `RED`, `BLACK`, …) in `stylings/color.py`
- Hachure, hatch, and solid fill pattern generators
- Stroke pressure and gradient utilities (`apply_stroke_pressure`, `apply_strokes_gradient`)
- Font loading and glyph-to-stroke conversion pipeline

**AI module (`handanim_ai`)**
- Two-stage LLM pipeline: topic → scene description → Python code
- OpenRouter client (`models.py`) with configurable model selection

**Developer tooling**
- `pytest` + `pytest-snapshot` test suite with visual regression via SSIM
- `pytest-cov` for coverage reporting
- Sphinx documentation with Furo theme
