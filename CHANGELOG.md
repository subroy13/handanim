# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] — 2026-11-18

### Added
- Full 54-voice Kokoro-82M catalog (`KOKORO_ALL_VOICES`, `KOKORO_VOICE_CATALOG`) and 256-D latent voice blending (`KokoroProvider.blend_voices`, `VoiceEngine.blend_voices`, `KOKORO_BLEND_PRESETS`, weighted strings like `"am_puck:0.6+bm_fable:0.4"`, equal-weight `"am_puck+bm_fable"`, and dicts `{"hm_omega": 0.55, "am_liam": 0.45}`) with automatic phonemizer language inference (`lang="en-us"` / `"en-gb"`) in `voiceanim/providers/kokoro_provider.py`
- Automatic Cairo backend selector (`handanim/core/_cairo.py`, `ensure_cairo()`, `get_cairo_backend()`) with seamless `pycairo` → `cairocffi` fallback and Homebrew/Conda `libcairo` auto-discovery
- Ergonomic `CharacterRig` builder API (`CharacterRig(pivot=...)`, `add_child(name, pivot=..., drawables=...)`, `add_slot(name, variants=...)`, `add_two_joint_limb(...)`, `capture_pose()`, list-of-drawables support in `VariantSlot`) and doctest execution in `.github/workflows/docs.yml`
- `MoveBy(dx, dy)` / `TranslateByAnimation` relative offset animation (`animations/translate.py`)
- Public `Scene.render_frame(t)` single-frame NumPy renderer and `Scene.render(..., crf=..., preset=..., tune=..., workers=...)` multi-worker encoding controls
- `-14.0 LUFS` integrated loudness normalization, true-peak soft-knee limiting (`-1.5 dBFS`), and 2-channel stereo output in `voiceanim/mixer.py`, with rebalanced procedural SFX levels (~12 dB under speech) in `voiceanim/sfx.py`
- Zero-install Google Colab interactive playground (`notebooks/handanim_colab_playground.ipynb`), Hugging Face Spaces Gradio studio (`huggingface_space/`), and 5-second README hero showcase (`docs/source/_static/gallery/hero_showcase.gif` and `hero_showcase.mp4`)

### Fixed
- `Eraser` mid-erase rendering (`animations/sketch.py`, `primitives/eraser.py`, `core/cache.py`): renders the visible eraser stroke and glowing cursor while progressively clipping erased segments instead of drawing nothing mid-erase
- `Scene.get_animated_opsset_at_time` (`core/scene.py`): only uses the finished-event cache when all events on a drawable have finished (`all_complete`) and the drawable has no time-varying scheduled slots, preventing running `PoseAnimation` rigs from freezing after `SketchAnimation`, `PopAnimation`, or `FadeInAnimation` finishes
- `CharacterRig` & `VariantSlot` time propagation (`core/scene.py`, `animations/pose.py`): passes frame time `t / self.fps` to every `CharacterRig` even without an active `PoseAnimation`, and evaluates `PoseAnimation` before non-pose spatial transforms (`TranslateToAnimation`, `MoveBy`) so prior moves are preserved
- `RoundedRectangle` (`primitives/polygons.py`): constructs all four corners from explicit 90-degree circular arcs (fixing the chamfered top-left corner) and supports `corner_radius=` in pixels
- `Scene.add(CameraAnimation(...))` (`core/scene.py`): routes camera events directly to `Scene.add_camera()` instead of raising `ValueError("drawable is required")`
- Snapshot tests (`tests/conftest.py`, `tests/ai/test_models.py`): compares rendered PNG frames by decoded pixel arrays with tolerance for cross-platform FreeType/Cairo differences and uses `pytest.importorskip("boto3")` when `boto3` is absent

---

## [1.0.0] — 2026-11-14

### Removed
- `SVG` legacy primitive (`primitives/svg.py`) — deleted entirely; use `VectorSVG` for all SVG import
- `svgpathtools` dev dependency — no longer needed now that `svg.py` is gone
- `SVG` export removed from `primitives/__init__.py`

### Changed
- `Math.custom_glyph_opsset` now uses `svgelements` (already a runtime dependency) to parse custom font glyph paths, replacing the `SVG`/`svgpathtools` pipeline; bounding box is computed via `OpsSet.get_bbox()` rather than `svgpathtools.Path.bbox()`

### Added
- `PageTurnTransition` and `PaperCrumpleTransition` (`animations/transitions.py`) — scene-level multi-page transitions with polygonal clipping (`OpsType.PUSH_CLIP` / `POP_CLIP`), geometric crease reflection with ink bleed-through, 2-phase paper-ball crunch + parabolic spin-and-toss, and automatic deactivation of previous-page world drawables
- `Show`, `Hide`, and `Swap` (`animations/visibility.py`, `Scene.swap()`) — zero-duration instant visibility toggles and atomic/cross-fade drawable swaps, plus `initial_opacity` and automatic base-opacity restoration on `FadeInAnimation`
- `CharacterRig`, `RigNode`, `VariantSlot`, `TwoJointLimb`, `Pose`, `PoseAnimation`, and `solve_two_joint_ik` (`primitives/character.py`, `animations/pose.py`) — hierarchical 2D character rigging with analytic 2-joint inverse kinematics, swappable eye/mouth expression slots, and smooth keyframe pose interpolation
- `Captions` (`primitives/captions.py`) and `scene.overlay` (`core/scene.py`) — camera-independent overlay layer and single-drawable word-timed caption renderer with active-word highlighting, `max_width` auto-scaling, and pre-chunked dict support
- Built-in easing functions and `PopAnimation` (`animations/easing.py`) — `linear`, `ease_in_quad`, `ease_out_quad`, `ease_in_out_quad`, `ease_in_cubic`, `ease_out_cubic`, `ease_in_out_cubic`, `ease_in_out`, `ease_in_back`, `ease_out_back`, `ease_in_out_back`, `ease_out_elastic`, `ease_out_bounce`
- Ergonomic alignment & font helpers — `Drawable.center_at()`, `Drawable.centred()`, `Drawable.align_to()`, `Text(align=..., font=...)`, and `register_font()` (`stylings/fonts.py`), plus personal-use `UserWarning` and AST linter warning when `backstay` is used
- `voiceanim` procedural audio & soundtrack mixer (`voiceanim/sfx.py`, `voiceanim/mixer.py`, `Scene.render`) — repeating background theme music (`generate_theme_music`, `loop_audio`, `scene.set_background_music`) with speech ducking, plus automatic chalk (`sketch_sound=True`), eraser (`eraser_sound=True`), and page-turn/crumple (`transition_sound=True`) sound effects
- Full Sphinx + Furo documentation suite (`docs/source/`) covering `handanim`, `voiceanim`, and `aianim` for GitHub Pages
- `Drawable.anchor(position)` — returns named anchor points (center, top_left, bottom_right, etc.) in world coordinates from the bounding box
- `Scene.place_relative(target, reference, ...)` — position one drawable relative to another's anchor without manual coordinate math
- `Scene.get_current_time()` — returns the end time of the latest event in the scene
- `Scene.wait(duration)` — returns `get_current_time() + duration` for inserting pauses between animations
- `Scene.render_keyframes(times, ...)` — batch export snapshots at specific timestamps (single timeline computation)
- `Scene.export_storyboard(n_frames, ...)` — export evenly-spaced keyframes as individual SVG/PDF files
- `Scene.render_handout(output_path, ...)` — render a single multi-page PDF with one animation frame per page
- `Scene.export_beamer(output_dir, ...)` — export keyframe PDFs and a compilable Beamer `.tex` file with `\only<N>` overlay transitions; new `backend="tikz"` option emits native TikZ drawing commands instead of embedded PDF images
- `Scene.render_tikz(output_path, ...)` — render a single animation frame as a standalone TikZ/LaTeX file
- `TikZRenderer` (`core/tikz_renderer.py`) — converts OpsSet drawing operations to TikZ path commands; handles coordinate transform (Y-flip), colour deduplication, partial ops, and line width scaling
- Top-level `__init__.py` exports — `from handanim import Scene, Rectangle, SketchAnimation` etc.
- Tests for all new scene utilities and export methods (35 new tests)
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
