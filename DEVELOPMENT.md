# DEVELOPMENT.md — handanim

Developer reference for setting up, testing, documenting, and running handanim locally.

---

## Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/) for dependency management
- Cairo system library (`pycairo` requires it; see platform notes below)

### Cairo installation

**macOS**
```bash
brew install cairo pkg-config
```

**Ubuntu / Debian**
```bash
sudo apt-get install libcairo2-dev pkg-config python3-dev
```

**Windows** — install via the [GTK for Windows Runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases).

---

## Setup

```bash
# Clone and enter the repo
git clone <repo-url>
cd handanim

# Install all dependencies (runtime + dev)
poetry install --with dev

# Activate the virtual environment (optional, for a plain shell)
poetry shell
```

---

## Running the Tests

### Full test suite

```bash
poetry run python3 -m pytest
```

### Run a specific test file

```bash
poetry run python3 -m pytest tests/core/test_opsset.py
poetry run python3 -m pytest tests/animations/test_sketch.py
poetry run python3 -m pytest tests/drawables/test_primitives.py
```

### Run a single test by name

```bash
poetry run python3 -m pytest -k "test_rotate_90_degrees"
```

### Verbose output

```bash
poetry run python3 -m pytest -v
```

---

## Test Coverage

Coverage is measured with `pytest-cov`. The `--cov-report=term-missing` flag shows exact line numbers not covered — open the file alongside the report to see which branches are untested.

### Terminal report (line numbers)

```bash
poetry run python3 -m pytest --cov=src/handanim --cov-report=term-missing
```

### HTML report (browsable, colour-coded per file)

```bash
poetry run python3 -m pytest --cov=src/handanim --cov-report=html
open htmlcov/index.html        # macOS
xdg-open htmlcov/index.html    # Linux
```

### Single module only

```bash
poetry run python3 -m pytest --cov=src/handanim/primitives/text --cov-report=term-missing
```

### Enforce a minimum threshold (useful in CI)

```bash
poetry run python3 -m pytest --cov=src/handanim --cov-fail-under=50
```

---

## Visual Regression Tests

Visual regression tests live in `tests/animations/`, `tests/drawables/`, etc. They render small deterministic scenes to PNG and compare them against reference files stored in `tests/snapshots/` using [SSIM](https://scikit-image.org/docs/stable/api/skimage.metrics.html#skimage.metrics.structural_similarity).

**How numpy seeding makes renders deterministic:** every test runs with `numpy.random.seed(42)` (set via the `seed_numpy` autouse fixture in `conftest.py`). This makes the random jitter in rough primitives (Line, Rectangle, etc.) identical across runs.

### Regenerate reference snapshots

Run this after intentionally changing rendering output — for example, after modifying a primitive's draw method or a style default:

```bash
poetry run python3 -m pytest tests/ --snapshot-update
```

Review the diff in `tests/snapshots/` before committing to make sure the visual change is intentional.

### Failure threshold

A visual test fails when SSIM drops below **0.98**. This catches structural rendering changes while tolerating sub-pixel float differences across platforms.

---

## Building the Documentation

Docs are built with [Sphinx](https://www.sphinx-doc.org/) using the [Furo](https://pradyunsg.me/furo/) theme. Docstrings are pulled in automatically via `sphinx.ext.autodoc`.

```bash
# Build HTML docs
cd docs
poetry run make html

# Output is written to docs/build/html/
# Open in browser
open build/html/index.html        # macOS
xdg-open build/html/index.html    # Linux
```

### Regenerating the API stubs

If you add a new module and want it to appear in the docs, regenerate the `.rst` stubs from the project root:

```bash
poetry run sphinx-apidoc -o docs/source src/handanim --force
```

Then rebuild HTML as above.

### Live reload during doc writing

```bash
poetry run sphinx-autobuild docs/source docs/build/html
# Serves at http://127.0.0.1:8000 and reloads on file change
```

> `sphinx-autobuild` is not in the dev dependencies by default. Install it once with `poetry add --group dev sphinx-autobuild`.

---

## Running Examples

Each script in `examples/` is a self-contained scene that renders to an MP4 (written to `examples/output/`).

```bash
# Pythagoras theorem — text, polygons, eraser
poetry run python3 examples/pythagoras.py

# (a+b)² visual proof — algebra with hand-drawn shapes
poetry run python3 examples/a_plus_b_square.py

# Distributive property with an SVG character
poetry run python3 examples/distributive_property.py

# Solar system orbit animation
poetry run python3 examples/solar_system.py

# Custom font rendering
poetry run python3 examples/custom_font.py
```

Output files land in `examples/output/`. The examples are the canonical "does this actually work end-to-end" check — run one before and after touching rendering code.

---

## Quick Smoke Test (no video output)

To verify a primitive renders without errors, use `OpsSet.quick_view()`. It renders to a temporary SVG and opens it in your browser:

```python
from handanim.primitives import Rectangle
from handanim.core.styles import StrokeStyle, SketchStyle

rect = Rectangle(
    top_left=(100, 100),
    width=400,
    height=300,
    stroke_style=StrokeStyle(color=(0.1, 0.1, 0.8), width=2),
    sketch_style=SketchStyle(roughness=1),
)
rect.draw().quick_view()
```

Run it with:

```bash
poetry run python3 -c "
from handanim.primitives import Rectangle
from handanim.core.styles import StrokeStyle
rect = Rectangle((100,100), 400, 300, stroke_style=StrokeStyle(color=(0,0,0.8), width=2))
rect.draw().quick_view(block=False)
"
```

---

## Exporting Snapshots & Handouts

Beyond full video rendering, the `Scene` class provides several ways to export individual frames and static documents.

### Single snapshot (SVG or PDF)

```python
scene.render_snapshot("frame_at_3s.svg", frame_in_seconds=3.0)
scene.render_snapshot("frame_at_3s.pdf", frame_in_seconds=3.0)  # format from extension
```

### Batch keyframe export

Export specific timestamps as individual files (one timeline computation, many outputs):

```python
paths = scene.render_keyframes(
    times=[0.0, 2.5, 5.0, 8.0],
    output_dir="output/keyframes",
    format="svg",  # or "pdf"
)
```

### Storyboard (evenly-spaced keyframes)

```python
paths = scene.export_storyboard(n_frames=8, output_dir="output/storyboard", format="svg")
```

### Multi-page PDF handout

Produces a single PDF file with one animation frame per page — useful as lecture handouts:

```python
# Auto-pick 6 evenly-spaced frames
scene.render_handout("handout.pdf")

# Or specify exact timestamps
scene.render_handout("handout.pdf", times=[0.0, 2.5, 5.0, 8.0, 12.0])
```

### Beamer slide deck

Export keyframe PDFs and a compilable `.tex` file with overlay transitions:

```python
# Cairo backend (default) — embeds rendered PDF images
tex_path = scene.export_beamer("output/slides", n_frames=8, title="Pythagorean Theorem")
# Then compile: cd output/slides && pdflatex slides.tex
```

#### Native TikZ backend

For truly native LaTeX vector output (no external PDF images), use the TikZ backend:

```python
# TikZ backend — inline drawing commands, no external files
tex_path = scene.export_beamer("output/slides", n_frames=8, backend="tikz", title="My Talk")
# Produces a single .tex file with \begin{tikzpicture} inside each \only<N>
```

The TikZ backend converts OpsSet drawing operations to TikZ path commands: `\draw` for strokes, `\fill` for fills, cubic Bezier `controls` for curves, and `\definecolor` for colour management. The hand-drawn roughness is preserved since each wobbly line segment becomes a Bezier curve in TikZ.

### Standalone TikZ frame

Export a single animation frame as a compilable standalone TikZ document:

```python
scene.render_tikz("frame.tex", time=2.5, target_width_cm=10.0)
# pdflatex frame.tex
```

---

## Positioning & Timeline Utilities

### Named anchors

Every `Drawable` can report named anchor points from its bounding box:

```python
rect.anchor("center")        # (cx, cy)
rect.anchor("top_left")      # (min_x, min_y)
rect.anchor("bottom_right")  # (max_x, max_y)
rect.anchor("right")         # (max_x, cy)
# Also: "top", "bottom", "left", "top_right", "bottom_left"
```

### Relative positioning

Position one drawable relative to another without manual coordinate arithmetic:

```python
label = Text("hello", position=(0, 0))
label = Scene.place_relative(label, rect, target_anchor="top", reference_anchor="bottom", offset=(0, -20))
```

### Timeline utilities

```python
scene.add(SketchAnimation(start_time=0, duration=2), rect)
t = scene.wait(1.0)   # t = 3.0 — returns the time after a 1s pause
scene.add(SketchAnimation(start_time=t, duration=2), circle)

scene.get_current_time()  # returns the end time of the latest event
```

---

## Project Layout Cheat Sheet

```
src/handanim/
├── core/          # OpsSet, Drawable, AnimationEvent, Scene, Viewport, TikZRenderer, styles
├── primitives/    # Line, Rectangle, Ellipse, Arrow, Text, Math, VectorSVG, RasterImage, …
├── animations/    # SketchAnimation, FadeIn/Out, Zoom, Translate, Rotate, ColorTransition, Camera
└── stylings/      # color constants, fill patterns, stroke utilities

tests/
├── conftest.py             # shared fixtures (seed_numpy, render_to_png_bytes)
├── snapshots/              # reference PNGs for visual regression
├── core/                   # OpsSet, Scene unit tests (no Cairo)
├── animations/             # per-animation tests (sketch, rotate, color_transition, camera, …)
└── drawables/              # visual regression tests for primitives, table, flowchart, …

examples/        # runnable end-to-end scene scripts
docs/            # Sphinx source and build output
```

---

## Linting & Formatting

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting — it replaces black, isort, and flake8 in a single fast tool.

```bash
# Check for violations
poetry run ruff check src/

# Auto-fix fixable violations
poetry run ruff check --fix src/

# Format code
poetry run ruff format src/
```

Configuration lives in `pyproject.toml` under `[tool.ruff]` and `[tool.ruff.lint]`.

---

## Type Checking

We use [mypy](https://mypy.readthedocs.io/) for static type analysis (non-strict mode).

```bash
poetry run mypy src/handanim --no-strict-optional
```

Configuration lives in `pyproject.toml` under `[tool.mypy]`.

---

## Pre-commit Hooks

[pre-commit](https://pre-commit.com/) runs ruff automatically before every commit.

```bash
# Install pre-commit (once per machine)
pip install pre-commit

# Install the hooks into this repo (once per clone)
pre-commit install

# Run hooks manually against all files
pre-commit run --all-files
```

After `pre-commit install`, every `git commit` will run ruff and fix/format staged Python files before the commit lands.

---

## Useful One-Liners

```bash
# Check that the package imports cleanly
poetry run python3 -c "import handanim; print('ok')"

# List all test node IDs without running them
poetry run python3 -m pytest --collect-only -q

# Run only tests that don't touch Cairo (fast pure-logic subset)
poetry run python3 -m pytest tests/core/ tests/animations/test_sketch.py -k "not Visual"

# Show which snapshot files exist
ls tests/snapshots/
```
