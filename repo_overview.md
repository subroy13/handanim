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
│   │   │   ├── drawable.py     # Drawable, TransformedDrawable, DrawableGroup, DrawableCache
│   │   │   ├── animation.py    # AnimationEvent, CompositeAnimationEvent
│   │   │   ├── scene.py        # Scene — orchestrator and rendering pipeline
│   │   │   ├── styles.py       # StrokeStyle, FillStyle, SketchStyle (type definitions)
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
│   │   │   ├── eraser.py       # Eraser — whiteout animation with zigzag human-like motion
│   │   │   ├── vector_svg.py   # VectorSVG — full-fidelity SVG import (color, fill, transforms)
│   │   │   ├── svg.py          # SVG — legacy path-only SVG import (deprecated)
│   │   │   ├── flowchart.py    # FlowchartNode, FlowchartDiamond, FlowchartConnector, Flowchart
│   │   │   └── table.py        # Table — grid of Rectangle+Text cells with row/cell animations
│   │   └── stylings/           # Style utility functions
│   │       ├── color.py        # Named color constants (BLUE, RED, BLACK, …)
│   │       ├── fillpatterns.py # Hachure/fill pattern generation → OpsSet
│   │       ├── fonts.py        # Font loading and glyph-to-stroke conversion
│   │       ├── strokes.py      # Stroke pressure and gradient utilities
│   │       └── utils.py        # Shared styling helpers
│   └── handanim_ai/            # AI-assisted animation scripting
│       ├── models.py           # OpenRouter LLM client
│       └── prompts/
│           ├── big_picture.txt # Prompt: topic → scene-by-scene description
│           └── codegen.txt     # Prompt: scene description → handanim Python code
├── examples/                   # Runnable example scripts
├── fonts/                      # Bundled font files (.ttf) and custom JSON stroke fonts
├── tests/                      # Test suite (currently minimal)
├── utils/
│   └── fontmaker/              # Prototype tool: raster glyphs → vector stroke JSON
└── docs/                       # Sphinx documentation source
```

---

## Architecture: Four-Layer Design

### Layer 1 — Drawing Instructions (`Ops` / `OpsSet`)
The lowest level. An `Ops` is a single drawing command:
`MOVE_TO`, `LINE_TO`, `CURVE_TO`, `QUAD_CURVE_TO`, `CLOSE_PATH`, `SET_PEN`, `DOT`, `METADATA`.

An `OpsSet` is an ordered list of `Ops` that Cairo renders directly. `OpsSet` also owns the geometry transforms (`translate`, `scale`, `rotate`) and a `quick_view()` debug helper that opens an SVG in the browser.

### Layer 2 — Drawables (shapes)
`Drawable` subclasses produce an `OpsSet` via `draw()`. Transforms are **immutable** — `.translate()` / `.scale()` / `.rotate()` return a new `TransformedDrawable` rather than mutating state.

`DrawableGroup` wraps multiple drawables for batch animation:
- `"series"` — event time-subdivided across elements in order
- `"parallel"` — same event applied to the composite group OpsSet; `drawable_element_id` metadata tags individual results for extraction afterward

### Layer 3 — Animation Events
`AnimationEvent` binds a `Drawable` to an animation type over `start_time`/`duration`. The `apply(opsset, progress)` method receives the current OpsSet and a 0.0–1.0 progress float, and returns a modified OpsSet.

### Layer 4 — Scene (orchestrator)
`Scene` maintains:
- `DrawableCache` — stores each drawable's initial OpsSet and caches the OpsSet after every completed event (keyed by `drawable_id + event_id`)
- Event list and object timelines (toggle-based visibility via creation/deletion events)
- `camera_events` list — separate pipeline for `CameraAnimation` events; `_get_viewport_at(t)` interpolates the viewport per-frame without touching drawable OpsSet data
- `create_event_timeline()` — iterates every frame, calls the recursive `get_animated_opsset_at_time()` to compose the full animation history for each active object, assembles per-frame OpsSet lists, and renders to Cairo

The **key architectural invariant** is the recursive cache pattern: when an event completes (`progress == 1`), its output OpsSet is saved. All subsequent events on that drawable receive this cached OpsSet as input, so animation chains are stateless and composable — no mutation needed.

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
| `fonttools` | Font parsing for Text/Math primitives |
| `matplotlib` | LaTeX math expression rendering (Math primitive) |
| `moviepy` / `imageio` | Video encoding (MP4, GIF) |
| `svgelements` | Full-fidelity SVG parsing (VectorSVG) |
| `tqdm` | Progress bars during rendering |

Dev-only (not required at runtime):
| `svgpathtools` | Used by legacy `SVG` primitive only |
| `vtracer`, `opencv-python`, `scikit-image` | Font generation utilities |
| `ruff` | Linting and formatting |
| `mypy` | Static type checking |

---

## Running Examples

```bash
# Install dependencies
poetry install

# Pythagoras theorem
poetry run python examples/pythagoras.py

# (a+b)² visual proof
poetry run python examples/a_plus_b_square.py

# Distributive property with SVG character
poetry run python examples/distributive_property.py
```

---

## Known Limitations

| # | Limitation | Location |
|---|---|---|
| 1 | `ZigZagLineFillPattern` is commented out — a sketchy back-and-forth pencil fill style pending implementation | `stylings/fillpatterns.py` |
