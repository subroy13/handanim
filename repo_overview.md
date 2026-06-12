# handanim — Repository Overview

**handanim** is a Python library for creating whiteboard-style, hand-drawn animations programmatically. It targets educational videos, mathematical explainers, and data storytelling. The output is a rendered MP4, GIF, or SVG snapshot.

Inspired by [3Blue1Brown's manim](https://github.com/3b1b/manim) and [RoughJS](https://github.com/rough-stuff/rough), but designed to be lighter, more Pythonic, and AI-scriptable.

---

## Repository Layout

```
handanim/
├── src/
│   ├── handanim/               # Core library
│   │   ├── core/               # Fundamental abstractions
│   │   │   ├── draw_ops.py     # Ops, OpsSet — low-level drawing instructions
│   │   │   ├── drawable.py     # Drawable, TransformedDrawable, DrawableGroup
│   │   │   ├── animation.py    # AnimationEvent, CompositeAnimationEvent
│   │   │   ├── cache.py        # DrawableCache — per-event OpsSet memoisation
│   │   │   ├── scene.py        # Scene — orchestrator and rendering pipeline
│   │   │   ├── styles.py       # StrokeStyle, FillStyle, SketchStyle (type definitions)
│   │   │   ├── tikz_renderer.py # OpsSet → TikZ path command converter
│   │   │   ├── viewport.py     # Viewport — world-to-screen coordinate mapping
│   │   │   └── utils.py        # Bezier math helpers
│   │   ├── animations/         # AnimationEvent subclasses
│   │   │   ├── sketch.py       # SketchAnimation — progressive stroke reveal
│   │   │   ├── fade.py         # FadeInAnimation, FadeOutAnimation
│   │   │   ├── zoom.py         # ZoomInAnimation, ZoomOutAnimation
│   │   │   ├── translate.py    # TranslateToAnimation, TranslateFromAnimation, TranslateToPersistAnimation
│   │   │   ├── rotate.py       # RotateAnimation — angle interpolation around a pivot
│   │   │   ├── color_transition.py  # ColorTransitionAnimation — SET_PEN color interpolation
│   │   │   └── camera.py       # CameraAnimation — viewport pan/zoom (scene-level)
│   │   ├── primitives/         # Drawable subclasses (shapes)
│   │   │   ├── lines.py        # Line, LinearPath
│   │   │   ├── curves.py       # Curve
│   │   │   ├── arrow.py        # Arrow, CurvedArrow
│   │   │   ├── polygons.py     # Polygon, Rectangle, Square, NGon, Rounded variants
│   │   │   ├── ellipse.py      # Ellipse, Circle, GlowDot
│   │   │   ├── text.py         # Text — handwritten font rendering; autofit() for bbox-fitting
│   │   │   ├── math.py         # Math — LaTeX expression rendering via matplotlib
│   │   │   ├── hershey_constants.py  # Unicode → Hershey font/char mappings; COMPOSED_GLYPHS
│   │   │   ├── eraser.py       # Eraser — whiteout animation with zigzag human-like motion
│   │   │   ├── raster_image.py # RasterImage — PNG/JPEG import as Cairo surface
│   │   │   ├── vector_svg.py   # VectorSVG — full-fidelity SVG import (color, fill, transforms)
│   │   │   ├── flowchart.py    # FlowchartNode, FlowchartDiamond, FlowchartConnector, Flowchart
│   │   │   └── table.py        # Table — grid of Rectangle+Text cells with row/cell animations
│   │   └── stylings/           # Style utility functions
│   │       ├── color.py        # Named color constants (BLUE, RED, BLACK, …)
│   │       ├── fillpatterns.py # Hachure/fill pattern generation → OpsSet
│   │       ├── fonts.py        # Font registry: TTF, custom JSON, and Hershey backends
│   │       ├── strokes.py      # Stroke pressure and gradient utilities
│   │       └── utils.py        # Shared styling helpers
│   └── handanim_ai/            # AI-assisted animation scripting
│       ├── models.py           # OpenRouter LLM client
│       └── prompts/
│           ├── big_picture.txt # Prompt: topic → scene-by-scene description
│           └── codegen.txt     # Prompt: scene description → handanim Python code
├── tools/                      # Offline developer tools (not part of the installed package)
│   ├── fontmaker/              # Custom font builder: grid image → vector stroke JSON
│   │   ├── make_grid_sheet.py  # Renders a printable glyph grid for hand-drawing
│   │   ├── make_fonts.py       # Extracts glyphs, skeletonises, vectorises → JSON font file
│   │   └── symbols.py          # Symbol label list shared across fontmaker scripts
│   └── stroke_model/           # Neural stroke-order model (experimental)
│       ├── train.py            # Trains a sequence model on UNIPEN handwriting data
│       └── data/               # Raw and processed UNIPEN datasets
├── fonts/                      # Bundled font files
│   ├── *.ttf                   # TTF fonts (Caveat, FeasiblySingleLine, PermanentMarker, …)
│   └── custom/                 # Custom JSON stroke fonts (handanimtype1.json, …)
├── examples/                   # Runnable end-to-end scene scripts
│   ├── pythagoras.py           # Pythagorean theorem — polygons, text, eraser
│   ├── a_plus_b_square.py      # (a+b)² visual proof — algebra with hand-drawn shapes
│   ├── distributive_property.py # Distributive law with an SVG character
│   ├── solar_system.py         # Orbital animation — circles, camera
│   ├── custom_font.py          # Custom JSON font rendering demo
│   ├── hershey_math.py         # Hershey-based hand-drawn math expression demo
│   ├── ml_workflow_demo.py     # ML pipeline flowchart animation
│   ├── tikz_beamer_demo.py     # Beamer slide export with TikZ backend
│   └── assets/                 # Supporting SVG/image assets for examples
├── tests/                      # Test suite
│   ├── conftest.py             # Shared fixtures (seed_numpy, render_to_png_bytes)
│   ├── core/                   # OpsSet, Scene, TikZ renderer unit tests
│   ├── animations/             # Per-animation tests (sketch, rotate, color_transition, camera)
│   ├── drawables/              # Visual regression tests for primitives, table, flowchart
│   └── test_public_api.py      # Smoke-tests for the top-level handanim.__init__ exports
├── docs/                       # Sphinx documentation source
├── development.py              # Interactive diagnostic / development scratch script
└── pyproject.toml              # Project metadata and Poetry dependency config
```

---

## Architecture: Four-Layer Design

### Layer 1 — Drawing Instructions (`Ops` / `OpsSet`)
The lowest level. An `Ops` is a single drawing command:
`MOVE_TO`, `LINE_TO`, `CURVE_TO`, `QUAD_CURVE_TO`, `CLOSE_PATH`, `SET_PEN`, `DOT`, `IMAGE`, `METADATA`.

An `OpsSet` is an ordered list of `Ops` that Cairo renders directly. `OpsSet` also owns the geometry transforms (`translate`, `scale`, `rotate`), bounding-box queries (`get_bbox`), and a `quick_view()` debug helper that renders to a temporary SVG and opens it in the browser.

### Layer 2 — Drawables (shapes)
`Drawable` subclasses produce an `OpsSet` via `draw()`. Transforms are **immutable** — `.translate()` / `.scale()` / `.rotate()` return a new `TransformedDrawable` rather than mutating state.

`DrawableGroup` wraps multiple drawables for batch animation:
- `"series"` — event time-subdivided across elements in order
- `"parallel"` — same event applied to the composite group OpsSet; `drawable_element_id` metadata tags individual results for extraction afterward

### Layer 3 — Animation Events
`AnimationEvent` binds a `Drawable` to an animation type over `start_time`/`duration`. The `apply(opsset, progress)` method receives the current OpsSet and a 0.0–1.0 progress float, and returns a modified OpsSet. Every `apply()` must be a pure function — no side effects.

### Layer 4 — Scene (orchestrator)
`Scene` maintains:
- `DrawableCache` (`core/cache.py`) — stores each drawable's initial OpsSet and caches the result after every completed event (keyed by `drawable_id + event_id`), so animation chains are stateless and composable
- Event list and object timelines (toggle-based visibility via creation/deletion events)
- `camera_events` list — separate pipeline for `CameraAnimation`; `_get_viewport_at(t)` interpolates the viewport per-frame without touching drawable OpsSet data
- `create_event_timeline()` — iterates every frame, calls the recursive `get_animated_opsset_at_time()` to compose the full animation history for each active object, assembles per-frame OpsSet lists, and renders to Cairo

The **key architectural invariant** is the recursive cache pattern: when an event completes (`progress == 1`), its output OpsSet is saved. All subsequent events on that drawable receive this cached OpsSet as input — no mutation ever needed.

---

## Math Rendering Pipeline

The `Math` primitive renders a LaTeX expression by:
1. Parsing the expression with `matplotlib.mathtext.MathTextParser` to obtain glyph positions and fraction-bar rectangles.
2. Looking up each Unicode codepoint in the font backend:
   - **TTF** (`standard_glyph_opsset`): draws via `fonttools` and a custom `CustomPen`, producing cubic Bézier OpsSet paths scaled from the font's `unitsPerEm`.
   - **Hershey** (`hershey_glyph_opsset`): resolves the codepoint through a priority chain — COMPOSED_GLYPHS hand-drawn strokes → `UNICODE_TO_HERSHEY` table → NFKD normalisation → ASCII fallback (`rowmans`). Uses `greeks` for lowercase Greek and `greekc` for uppercase Greek (both sequential Latin-proxy encoding; `mathlow`/`mathupp` are broken in pyhershey).
   - **Custom JSON** (`custom_glyph_opsset`): reads SVG path strings from the JSON font file and converts via `svgelements`.
3. Optionally applying `_apply_roughness` to replace straight LINE_TO segments with wobbly cubic Béziers.
4. Assembling all glyph OpsSet objects with their layout offsets, then appending fraction-bar lines drawn by `Line`.

---

## Font Backends

| Backend | How loaded | Glyph source | Roughness |
|---|---|---|---|
| TTF | `fonttools.TTFont` | Cubic Bézier outlines from glyph set | Via `_apply_roughness` |
| Hershey | `HersheyFonts` | Strokes from `greeks` / `greekc` / `rowmans` / `COMPOSED_GLYPHS` | Native — lines already wobbly |
| Custom JSON | JSON file in `fonts/custom/` | SVG path strings (drawn by hand in fontmaker tool) | Via `_apply_roughness` |

The font registry (`stylings/fonts.py`) maps friendly font names to backend type and file path so callers use `font_name="feasibly"` without knowing the backend.

---

## Tools

### `tools/fontmaker/` — Custom Font Builder
A standalone pipeline for creating new hand-drawn JSON fonts:

1. **`make_grid_sheet.py`** — Prints a grid sheet (PNG) with every glyph symbol labelled. The artist fills in each cell by hand, photographs or scans it, and returns the image.
2. **`make_fonts.py`** — Takes the filled-in grid image, detects cell boundaries, extracts each glyph, applies Zhang-Suen skeletonisation (`skimage.morphology.skeletonize`) to extract the centerline, vectorises the skeleton into SVG paths, and writes the result to the custom JSON format (`fonts/custom/*.json`).
3. **`symbols.py`** — Shared symbol label list (Latin letters, digits, Greek letters, math operators) used by both scripts.

The JSON output feeds directly into `custom_glyph_opsset` in `Math` with zero renderer changes needed.

### `tools/stroke_model/` — Neural Stroke Model (Experimental)
A sequence model trained on the UNIPEN handwriting dataset to predict natural stroke order for math symbols. `train.py` loads pre-processed `.pkl` data, defines a PyTorch model, and trains it. The trained model is intended to improve stroke ordering in the fontmaker pipeline.

---

## Key Design Principles

1. **Immutability on Drawables** — transforms return new objects; the original is never changed
2. **Stateless `apply()`** — every `AnimationEvent.apply()` must be a pure function of `(opsset, progress)`; side effects will break the cache
3. **OpsSet is the universal currency** — every layer speaks OpsSet; Cairo is only touched in `OpsSet.render()` and `Scene.render()`
4. **Decoupling** — shapes know nothing about animation; animations know nothing about scene topology

---

## Dependencies

| Package | Purpose |
|---|---|
| `pycairo` / `cairocffi` | Cairo bindings for rendering |
| `numpy` | Geometry / Bezier math |
| `fonttools` | TTF font parsing for Text/Math primitives |
| `matplotlib` | LaTeX math expression parsing (Math primitive) |
| `moviepy` / `imageio` | Video encoding (MP4, GIF) |
| `svgelements` | Full-fidelity SVG parsing (VectorSVG) |
| `HersheyFonts` | Hershey stroke font data (greeks, greekc, rowmans, …) |
| `tqdm` | Progress bars during rendering |

Dev-only (not required at runtime):

| Package | Purpose |
|---|---|
| `opencv-python`, `scikit-image`, `Pillow` | Image processing in fontmaker tool |
| `torch` | Stroke model training |
| `ruff` | Linting and formatting |
| `mypy` | Static type checking |
| `pytest`, `pytest-cov` | Test suite and coverage |

---

## Running Examples

```bash
# Install dependencies
poetry install

# Pythagorean theorem — text, polygons, eraser
poetry run python examples/pythagoras.py

# (a+b)² visual proof
poetry run python examples/a_plus_b_square.py

# Hershey hand-drawn math expressions
poetry run python examples/hershey_math.py

# ML pipeline flowchart
poetry run python examples/ml_workflow_demo.py

# Beamer slide export with TikZ backend
poetry run python examples/tikz_beamer_demo.py
```

---

## Known Limitations

| # | Limitation | Location |
|---|---|---|
| 1 | `ZigZagLineFillPattern` is commented out — a sketchy back-and-forth pencil fill style pending implementation | `stylings/fillpatterns.py` |
| 2 | Fontmaker centerline extraction works well for thick marker glyphs but can produce spurious branches on thin serif strokes | `tools/fontmaker/make_fonts.py` |
| 3 | `handanim_ai` scripting requires an OpenRouter API key and is not tested in CI | `src/handanim_ai/` |
