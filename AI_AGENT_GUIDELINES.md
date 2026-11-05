# AI_AGENT_GUIDELINES.md — handanim

> **Quick Reference for AI Agents:** This guide provides the complete architectural mental model, directory map, invariant rules, and developer workflows for `handanim`. Read this document to understand what exists, where each component lives, and how data flows through the library without re-scanning the entire codebase.

For collaborative 30–60 second portrait whiteboard videos, start with [sandbox/AGENTS.md](sandbox/AGENTS.md). It contains the production workflow, current MCP tool names, portrait settings, and targeted source references. Use this architecture guide when changing the package itself.

---

## 1. Project Identity & Guiding Philosophy

**handanim** is a lightweight, Pythonic library for creating whiteboard-style, hand-drawn animations programmatically. It renders to MP4, GIF, SVG snapshots, or LaTeX TikZ / Beamer slides.

### The Guiding Principle: *"Reproducible, but hand-sketchy."*
- Every visual element should look like it was drawn by a human hand (natural wobble, subtle stroke jitter, pressure variation, hachure/cross-hatch fills).
- Clean, crisp digital lines are an anti-pattern. New primitives and styles must integrate with `SketchStyle`, `StrokeStyle`, and `FillStyle`.
- Deterministic and reproducible: Randomness must be controllable (seeded) so renders are consistent across runs.

---

## 2. Essential Commands & Development Workflow

The project uses Python 3.11+ and Poetry. System library prerequisite: `cairo` (via `brew install cairo` or `apt-get install libcairo2-dev`).

```bash
# Run full test suite (500+ tests)
poetry run pytest
# Or directly with local venv:
.venv/bin/pytest

# Run tests for a specific area
.venv/bin/pytest tests/core/test_opsset.py
.venv/bin/pytest tests/animations/test_sketch.py
.venv/bin/pytest tests/drawables/test_primitives.py

# Run tests by name expression
.venv/bin/pytest -k "test_rotate"

# Run with test coverage
.venv/bin/pytest --cov=src/handanim --cov-report=term-missing

# Linting & Formatting
poetry run ruff check .
poetry run ruff format .

# Type checking
poetry run mypy src/handanim

# Run an example animation
poetry run python examples/pythagoras.py
poetry run python examples/ml_workflow_demo.py
poetry run python examples/hershey_math.py
```

---

## 3. Architectural Invariants — Non-Negotiable Rules

Any modification to `handanim` must uphold these invariants:

### Invariant 1: Drawables are Immutable & Stateless
- `Drawable.translate()`, `.scale()`, `.rotate()` **must return a new `TransformedDrawable`**. They never mutate the original object in place.
- Example pattern:
  ```python
  # CORRECT:
  square = square.translate(100, 200)

  # WRONG (never do this):
  square.x += 100
  ```
- Never add mutable internal state to `Drawable` subclasses.

### Invariant 2: `AnimationEvent.apply()` is a Pure Function
- Signature: `apply(self, opsset: OpsSet, progress: float) -> OpsSet`
- Pure function requirement: Given an input `OpsSet` and a progress float `[0.0, 1.0]`, return a **new** transformed `OpsSet`.
- **Zero side effects**: Never mutate the input `opsset`, never mutate `self`, and never touch the `Scene`.
- The `Scene` caches the output of completed events (`progress == 1.0`) and feeds that cached output into downstream events. Any side effect corrupts the entire animation timeline.
- Easing: If `self.easing_fun` is defined, apply easing first:
  ```python
  progress = self.easing_fun(raw_progress) if self.easing_fun else raw_progress
  ```

### Invariant 3: OpsSet is the Universal Lingua Franca
- **Drawables** produce `OpsSet` via `.draw()`.
- **Animations** consume an `OpsSet` and return a new `OpsSet` via `.apply()`.
- **Renderers** consume `OpsSet` (e.g. `OpsSet.render(ctx)` for Cairo, `tikz_renderer.py` for LaTeX).
- **No layer may bypass OpsSet** to draw directly to Cairo. Direct Cairo calls are strictly confined to `OpsSet.render()` and `Scene.render()`.

### Invariant 4: World Coordinate Space vs Screen Viewport
- Default world space is **`(0, 1777) × (0, 1000)`** (matching 16:9 aspect ratio for 1920×1088 output).
- Origin `(0, 0)` is at the **top-left**; coordinates increase rightward (x) and downward (y).
- All primitives, positions, and layout coordinates are specified in world units, not raw pixels.
- `Viewport` handles the conversion from world space to output video/image pixels during rendering.

### Invariant 5: OpsSet Metadata Protocol
- Drawing modes are distinguished using `METADATA` ops:
  - Outline/stroke ops are tagged with `drawing_mode="stroke"` (or default).
  - Fill ops (e.g., hachure patterns) are preceded by `METADATA` with `drawing_mode="fill"`.
  - `SketchAnimation` relies on this split to sketch outlines first, then shade fills.
- `DrawableGroup` parallel animations tag ops with `drawable_element_id` so individual transformed results can be decomposed after group-level operations.

---

## 4. Codebase Map — "What Does What"

```
handanim/
├── src/
│   ├── handanim/                  # Core library package
│   │   ├── core/                  # Core abstractions and engine
│   │   ├── primitives/            # All drawable shapes & primitives
│   │   ├── animations/            # All animation event types
│   │   ├── stylings/              # Colors, fills, fonts, strokes
│   │   └── utils/                 # Geometry & humanization utilities
│   └── handanim_ai/               # AI generation pipeline (LLM prompts & schemas)
├── tools/                         # Offline tools (font creation, ML stroke model)
├── fonts/                         # Bundled TTF and custom JSON fonts
├── examples/                      # Runnable reference scripts
└── tests/                         # Pytest test suite
```

### 4.1. Core Module (`src/handanim/core/`)

| File | Primary Responsibilities |
|---|---|
| `draw_ops.py` | Defines `Ops` (atomic draw commands: `MOVE_TO`, `LINE_TO`, `CURVE_TO`, `QUAD_CURVE_TO`, `CLOSE_PATH`, `SET_PEN`, `DOT`, `IMAGE`, `METADATA`) and `OpsSet` (ordered list of Ops, affine transforms `translate`/`scale`/`rotate`, bounding box `get_bbox()`, Cairo execution `render()`, and quick browser debug `quick_view()`). |
| `drawable.py` | `Drawable` abstract base class (`draw() -> OpsSet`). `TransformedDrawable` for immutable affine wraps. `DrawableGroup` for grouping drawables with `"series"` or `"parallel"` animation execution modes. |
| `animation.py` | `AnimationEvent` base class (`apply(opsset, progress) -> OpsSet`), `AnimationEventType` enum (`CREATION`, `TRANSFORMATION`, `DELETION`), `CompositeAnimationEvent`. |
| `scene.py` | `Scene` class — the main orchestrator. Manages drawable registry, timeline construction (`create_event_timeline()`), caching, camera tracks, and rendering to MP4/GIF/PNG/SVG/TikZ. |
| `cache.py` | `DrawableCache` — manages memoized `OpsSet` states for each drawable: initial state (`{id}__init`) and post-event state (`{id}__{event_id}`). |
| `styles.py` | Dataclasses for styling: `StrokeStyle` (color, width, alpha, roughness), `FillStyle` (color, pattern, angle, spacing, alpha), `SketchStyle` (composite styling). |
| `viewport.py` | `Viewport` — maps world coordinates `(0, 1777) × (0, 1000)` to screen surfaces with pan/zoom support. |
| `tikz_renderer.py` | Converts `OpsSet` instructions into LaTeX TikZ code for inclusion in TeX/Beamer documents. |
| `utils.py` | Math utilities: cubic/quadratic Bézier evaluation, splitting, arc lengths, bounding box calculations. |

### 4.2. Primitives (`src/handanim/primitives/`)

All primitives inherit from `Drawable` and implement `draw() -> OpsSet`.

| File | Classes & Purpose |
|---|---|
| `lines.py` | `Line(start, end)`, `LinearPath(points)` — hand-drawn line segments. |
| `curves.py` | `Curve(points)` — smooth Bézier curves through control points with hand-drawn jitter. |
| `arrow.py` | `Arrow(start, end)`, `CurvedArrow(start, end, control_offset)` — directional arrows with sketchy arrowheads. |
| `polygons.py` | `Polygon(vertices)`, `Rectangle(x, y, w, h)`, `Square(x, y, side)`, `NGon(center, radius, n)`, `RoundedRectangle`, `RoundedSquare`. All support strokes + hachure fills. |
| `ellipse.py` | `Ellipse(center, rx, ry)`, `Circle(center, radius)`, `GlowDot(center, radius)`. |
| `text.py` | `Text(text, x, y, font_size, font_name)` — renders handwritten text using Hershey, TTF, or custom JSON fonts. Includes `.autofit(bbox)` to fit text neatly within shapes. |
| `math.py` | `Math(latex_expr, x, y)` — renders LaTeX math formulas via `matplotlib.mathtext.MathTextParser` combined with stroke fonts. |
| `hershey_constants.py` | Codepoint lookup tables mapping Unicode math & Greek symbols to Hershey font representations. |
| `eraser.py` | `Eraser(target, duration)` — produces a realistic zigzag whiteout wipe animation over another drawable. |
| `raster_image.py` | `RasterImage(file_path, x, y, width, height)` — renders PNG/JPEG images into Cairo surfaces with optional sketchy borders. |
| `vector_svg.py` | `VectorSVG(svg_path, x, y, scale)` — **Modern SVG importer** using `svgelements`. Full fidelity: retains paths, fills, strokes, colors, transforms. |
| `svg.py` | *DEPRECATED* legacy SVG importer using `svgpathtools`. **Do not use in new code**; always prefer `VectorSVG`. |
| `flowchart.py` | `FlowchartNode`, `FlowchartDiamond`, `FlowchartConnector`, and `Flowchart` — high-level primitives for creating diagrams and workflows. |
| `table.py` | `Table(data, x, y, col_widths, row_heights)` — tabular grid of cells (rectangles + text) with cell/row-level reveal animations (`TableRevealEvent`). |

### 4.3. Animations (`src/handanim/animations/`)

All animations inherit from `AnimationEvent` and implement `apply(opsset, progress) -> OpsSet`.

| File | Classes & Purpose |
|---|---|
| `sketch.py` | `SketchAnimation` — progressively reveals strokes from 0% to 100% path length, followed by revealing hachure fills. |
| `fade.py` | `FadeInAnimation`, `FadeOutAnimation` — modulates opacity / pen alpha across operations. |
| `zoom.py` | `ZoomInAnimation`, `ZoomOutAnimation` — scales the `OpsSet` around a pivot (default: bounding box center). |
| `translate.py` | `TranslateToAnimation`, `TranslateFromAnimation`, `TranslateToPersistAnimation` — moves objects across world coordinates. |
| `rotate.py` | `RotateAnimation` — rotates the `OpsSet` by angle $\theta$ around a pivot. |
| `color_transition.py` | `ColorTransitionAnimation` — smoothly interpolates `SET_PEN` stroke/fill colors between start and end palettes. |
| `camera.py` | `CameraAnimation` — pans and zooms the scene-level `Viewport` over time. Handled separately in `Scene` timeline creation. |

### 4.4. Stylings & Utilities (`src/handanim/stylings/` and `src/handanim/utils/`)

- `stylings/color.py`: Color constants (`BLACK`, `WHITE`, `RED`, `BLUE`, `GREEN`, `YELLOW`, `GRAY`, etc.) and hex/RGB conversion.
- `stylings/fillpatterns.py`: Generates hachure, cross-hatch, and dots fill patterns for closed polygons as `OpsSet`.
- `stylings/fonts.py`: Font manager registry resolving font names to TTF files, Hershey stroke tables, or custom JSON glyph paths.
- `stylings/strokes.py`: Applies natural pen pressure curves, stroke perturbation, and gradients.
- `utils/humanize.py`: Adds human-like wobble, jitter, overshoot, and uneven line velocity.
- `utils/geometry.py`: Geometric primitives, intersections, convex hulls, and bounding box math.

### 4.5. AI & Agentic Tooling (`src/handanim_ai/`)

`handanim_ai` provides an autonomous generation pipeline, AST code guardrails, and an MCP server for local AI agents:
- `schema.py`: Strongly typed `ScenePlan`, `SceneSpec`, `DrawableSpec`, `AnimationSpec` dataclasses, validation, and JSON Schema generator for tool-calling.
- `compiler.py`: `plan_to_python()` — deterministic compiler converting a `ScenePlan` directly into executable Python.
- `diagnostics.py`: `check_code(code_str)` — AST linter catching unassigned immutable transforms (`obj.translate()`), legacy imports, and syntax errors.
- `models.py`: Multi-provider LLM interface supporting **AWS Bedrock** (Converse API), OpenRouter, and MockModel.
- `prompts/`: Versioned YAML templates (`prompts/v1/big_picture.yaml`, `codegen.yaml`, `correction.yaml`) managed via `PromptManager`.
- `assets.py`: Dynamic scanner discovering available fonts, colors, and media assets for prompt injection.
- `executor.py` & `pipeline.py`: Subprocess runner with timeout, error extraction, and a 1-2 retry self-correction feedback loop.
- `mcp_server.py`: Model Context Protocol (MCP) stdio server (`handanim-ai mcp`) exposing tools (`render_snapshot`, `introspect_scene`, `lint_script`, `list_assets`, `compile_plan_to_code`) to Claude Code, Claude Desktop, Cursor, and Gemini.
- `cli.py`: Streamlined CLI with two focused modes: Interactive Bedrock Studio (`handanim-ai`) and MCP Server (`handanim-ai mcp`).

### 4.6. Offline Tools
- `tools/fontmaker/`: Offline pipeline converting scanned hand-drawn glyph sheets (`make_grid_sheet.py`) into skeletonized vector JSON fonts (`make_fonts.py`).
- `tools/stroke_model/`: Sequence model (PyTorch) trained on UNIPEN data to predict natural handwriting stroke order.

---

## 5. Rendering Pipeline & Timeline Dataflow

Understanding how a `Scene` turns code into frames:

```
1. User defines Scene & Drawables:
   scene = Scene(width=1920, height=1088, fps=30)
   scene.add(shape)
   scene.play(SketchAnimation(shape, start_time=0.0, duration=1.5))
   scene.play(TranslateToAnimation(shape, dx=200, dy=0, start_time=1.5, duration=1.0))

2. Scene.render() builds the timeline:
   create_event_timeline():
     - Calculates total scene duration.
     - For each frame t = 0 .. N-1:
         - Interpolate camera viewport if CameraAnimations exist: _get_viewport_at(t).
         - For each active drawable at time t:
             get_animated_opsset_at_time(drawable_id, t):
               - If t == 0: return cache[f"{drawable_id}__init"]
               - Find all past completed events: return cached OpsSet from cache[f"{drawable_id}__{event_id}"]
               - Find currently active event at time t:
                   progress = (t - event.start_time) / event.duration
                   current_opsset = event.apply(prior_cached_opsset, progress)
               - Return current_opsset

3. Per-frame rasterization:
   For each frame:
     - Set up Cairo context from Viewport.
     - For each drawable's current_opsset:
         current_opsset.render(cairo_ctx)
     - Pipe frame buffer to MoviePy / ImageIO (or write SVG snapshot).
```

---

## 6. How-To Cheatsheet: Adding New Features

### Adding a New Primitive
1. Create `src/handanim/primitives/<name>.py`.
2. Subclass `Drawable`.
3. Implement `draw(self) -> OpsSet`:
   - Emit `SET_PEN` with stroke parameters.
   - Emit path ops (`MOVE_TO`, `LINE_TO`, `CURVE_TO`, etc.) with humanized jitter (`humanize.py`).
   - If fill is enabled, call `fillpatterns.py` and tag fill ops with `METADATA(data={"drawing_mode": "fill"})`.
4. Export in `src/handanim/primitives/__init__.py` and top-level `src/handanim/__init__.py`.
5. Add unit tests in `tests/drawables/test_<name>.py`.

### Adding a New Animation
1. Create `src/handanim/animations/<name>.py`.
2. Subclass `AnimationEvent`.
3. Implement `apply(self, opsset: OpsSet, progress: float) -> OpsSet`:
   - Compute `progress = self.easing_fun(progress) if self.easing_fun else progress`.
   - Return a new `OpsSet` (e.g. by modifying ops coordinates or pen attributes).
   - **Do not modify the incoming `opsset` in-place.**
4. Export in `src/handanim/animations/__init__.py` and top-level `src/handanim/__init__.py`.
5. Add unit tests in `tests/animations/test_<name>.py`.

---

## 7. Common Pitfalls & Edge Cases

1. **In-place Mutation Traps**:
   Never modify `Ops.data` dictionaries in place. When transforming an operation, always create a new `Ops` or call `.copy()` on dictionaries before mutation.

2. **SVG Importer Selection**:
   Always use `VectorSVG` (`from handanim import VectorSVG`). Never import or suggest `from handanim.primitives.svg import SVG`, which is deprecated and lacks fill/transform support.

3. **`DrawableGroup` Parallel Mode**:
   When parallel animations transform a `DrawableGroup`, elements are unpacked and individually identified by `drawable_element_id` in `METADATA`. If touching group rendering logic in `scene.py`, always verify nested group tests pass.

4. **Coordinate Confusion**:
   Remember that `handanim` uses world coordinates (default width 1777, height 1000). Never hardcode pixel values like `1920` or `1088` into primitive positions.

5. **Code Style & Documentation**:
   - Provide clear docstrings for all public classes and methods.
   - Use strict type annotations (`OpsSet`, `Optional[float]`, etc.). Avoid indiscriminate `Any`.
   - Maintain the existing clean test conventions using `pytest`.

---

## 8. AI Integration (`handanim-ai`)

`handanim-ai` provides two complementary workflows:

1. **Interactive Assistant** (`poetry run handanim-ai` or `poetry run handanim-ai interactive`):
   - Direct conversational experience for human creators using AWS Bedrock.
   - Interactive arrow-key menus (`questionary`) and rich terminal panels/syntax trees (`rich`).
   - Under-the-hood prompt visibility (`--verbose`) and instant plan refinement / self-repair.

2. **Model Context Protocol (MCP) Server** (`poetry run handanim-ai mcp`):
   - Stdio JSON-RPC server conforming to the MCP specification for external agents (Claude Desktop, Claude Code, Cursor, Gemini).
   - Tools: `list_primitives_and_styles`, `introspect_scene_api`, `lint_handanim_code`, `execute_and_verify_code`, `render_snapshot_preview`.
   - Outputs base64 PNG snapshots directly into agent context for visual feedback without file uploads.


