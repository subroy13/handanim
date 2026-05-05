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
poetry run python3 -m pytest tests/test_opsset.py
poetry run python3 -m pytest tests/test_sketch.py
poetry run python3 -m pytest tests/test_visuals.py
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

Visual regression tests live in `tests/test_visuals.py`. They render small deterministic scenes to PNG and compare them against reference files stored in `tests/snapshots/` using [SSIM](https://scikit-image.org/docs/stable/api/skimage.metrics.html#skimage.metrics.structural_similarity).

**How numpy seeding makes renders deterministic:** every test runs with `numpy.random.seed(42)` (set via the `seed_numpy` autouse fixture in `conftest.py`). This makes the random jitter in rough primitives (Line, Rectangle, etc.) identical across runs.

### Regenerate reference snapshots

Run this after intentionally changing rendering output — for example, after modifying a primitive's draw method or a style default:

```bash
poetry run python3 -m pytest tests/test_visuals.py --snapshot-update
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

## Project Layout Cheat Sheet

```
src/handanim/
├── core/          # OpsSet, Drawable, AnimationEvent, Scene, Viewport, styles
├── primitives/    # Line, Rectangle, Ellipse, Arrow, Text, Math, VectorSVG, …
├── animations/    # SketchAnimation, FadeIn/Out, Zoom, Translate
└── stylings/      # color constants, fill patterns, stroke utilities

tests/
├── conftest.py          # shared fixtures (seed_numpy, render_to_png_bytes)
├── snapshots/           # reference PNGs for visual regression
├── test_opsset.py       # geometry unit tests (no Cairo)
├── test_sketch.py       # SketchAnimation logic tests (no Cairo)
└── test_visuals.py      # visual regression tests (Cairo + pytest-snapshot)

examples/        # runnable end-to-end scene scripts
docs/            # Sphinx source and build output
```

---

## Useful One-Liners

```bash
# Check that the package imports cleanly
poetry run python3 -c "import handanim; print('ok')"

# List all test node IDs without running them
poetry run python3 -m pytest --collect-only -q

# Run only tests that don't touch Cairo (fast pure-logic subset)
poetry run python3 -m pytest tests/test_opsset.py tests/test_sketch.py

# Show which snapshot files exist
ls tests/snapshots/
```
