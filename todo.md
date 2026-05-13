# handanim — Todo & Roadmap

---

## Bug Fixes (do first)

- [x] **Dead return in SketchAnimation** — remove the duplicate `return new_opsset` at `animations/sketch.py:143`
- [x] **Discarded transform in example** — fix `examples/distributive_property.py:31`: `operator = operator.scale(0.5, 0.5)` (transforms are immutable, return value must be used)
- [x] **`apply_strokes_gradient` stub** — implement or remove; currently returns an empty OpsSet silently (`stylings/strokes.py:62`)
- [x] **Viewport origin offset** — `Viewport.apply_to_context` should translate by `-world_xrange[0] * scale` and `-world_yrange[0] * scale` to support non-zero world origins (`core/viewport.py`)
- [x] **`svgwrite` unused dep** — remove from `requirements.txt` and `pyproject.toml`
- [x] **Legacy `SVG` primitive** — move `svgpathtools` to runtime deps OR deprecate `SVG` in favour of `VectorSVG` and mark it clearly. `VectorSVG` is strictly more capable.
- [x] **Wire up `easing_fun`** — `AnimationEvent` accepts an easing function but no `apply()` implementation ever calls it; either remove it or implement: `progress = easing_fun(raw_progress) if easing_fun else raw_progress` at the top of every `apply()`
- [x] Immutability Violation in stylings/strokes.py: The functions apply_stroke_pressure and apply_strokes_gradient currently mutate the current_pen_data dictionaries directly (e.g., current_pen_data["width"] = ...). Because this dictionary is a reference to the Ops data, it mutates the original operations in place. This violates the core architectural invariant stated in CLAUDE.md that transformations and animations must be stateless. Fix: Use .copy() on current_pen_ops.data before applying new pressure or gradient values and emitting the new Ops.
- [x] Incomplete Eraser Logic (primitives/eraser.py): At line 47, there is a # TODO: do the rotation, perform the zigzag motion here. Currently, the eraser just performs a horizontal bounding-box wipe without mimicking a human zigzag erasing motion or aligning to the stroke paths. This breaks the "hand-drawn" aesthetic constraint for this specific primitive.


---

## Developer Workflow & Release

### CI / CD
- [ ] **CI test workflow** — add `.github/workflows/ci.yml` that runs `pytest --cov` on every push and PR; currently only the docs-deploy workflow exists
- [ ] **Code coverage reporting** — pipe `pytest-cov` output to Codecov (free for OSS) and add a coverage badge to the README; `pytest-cov` is already in dev deps, just needs wiring

### Code quality
- [x] **Ruff** — add `[tool.ruff]` section to `pyproject.toml`; replaces black + isort + flake8 in one fast tool; enforce in CI and document in DEVELOPMENT.md
- [x] **Pre-commit hooks** — add `.pre-commit-config.yaml` running ruff (and optionally mypy) before every commit; add setup one-liner to DEVELOPMENT.md so contributors pick it up automatically
- [x] **Type checking with mypy** — add `[tool.mypy]` section to `pyproject.toml` (start with `strict = false`); run on CI; tighten incrementally as the codebase stabilises

### Package ergonomics
- [ ] **Top-level exports** — populate `src/handanim/__init__.py` with the commonly-used classes (`Scene`, `Text`, `Rectangle`, `Circle`, `Arrow`, `SketchAnimation`, `FadeInAnimation`, etc.) so users can write `from handanim import Scene` instead of importing from submodules
- [ ] **PyPI publication** — fill in the empty `description` field and add `classifiers` / `keywords` to `pyproject.toml`; publish `v0.1.0` to PyPI so `pip install handanim` works and the package is discoverable
- [ ] **Semantic versioning** — adopt SemVer; tag releases in git; use `poetry version patch/minor/major` for bumps; document the release process in DEVELOPMENT.md

### Docs & community files
- [x] **CHANGELOG.md** — create with an "Unreleased" section and retroactively document current feature set; follow the [Keep a Changelog](https://keepachangelog.com) format
- [x] **GitHub issue templates** — add `.github/ISSUE_TEMPLATE/bug_report.md` and `feature_request.md` so incoming issues arrive with the right context filled in
- [x] **PR template** — add `.github/pull_request_template.md` with a checklist (tests updated, docs updated, example added if relevant)
- [x] **Update repo_overview.md** — currently describes the architecture before Phase 2; update to reflect the Flowchart, Table, and new animation types

---

## Phase 1 — Core Hardening & Foundations

These make the library reliable and testable before adding more features.

### Testing strategy
Visual regression testing is the pragmatic approach for an animation library:
- [x] Render a small, deterministic scene to PNG (seed numpy random if needed)
- [x] Store a reference PNG hash (or use pixel-level SSIM comparison via `scikit-image`)
- [x] On subsequent runs, fail if the rendered output diverges beyond a threshold
- [x] Unit-test pure geometry separately: `OpsSet.translate/scale/rotate` are straightforward to assert on coordinates
- [x] Test `SketchAnimation.get_partial_sketch` with known op counts and progress values
- [x] Use `pytest` + `pytest-snapshot` for snapshot management
- [x] Add a `render_snapshot()` call in each test — cheap since these are single-frame SVG renders

### Caching improvements
- [x] **Static object cache** — if an object has no ongoing animation at frame `t`, reuse its final cached OpsSet without entering `get_animated_opsset_at_time` at all
- [x] **Group transform cache** — cache the result of `event.apply(group_opsset, progress)` per frame per group event (not just the "before" state); currently the group OpsSet build is cached but the transform is re-applied per member
- [ ] **Dirty flag on Scene** — track whether `create_event_timeline()` needs re-running after `add()` calls; avoid full recompute on `render_snapshot()` calls. 
  *Note: Needs more thought on this!!*

### Content autofitting
- [x] Add a `BoundingBox` helper type representing a world-coordinate rectangle
- [x] Implement `Text.autofit(bbox: BoundingBox)` — use Cairo `text_extents()` to measure, then scale font size to fill the box
- [x] Implement multi-line text wrapping within a bounding box
- [x] Expose `Drawable.get_bbox()` uniformly so any drawable can report its extent (currently only `SVG` has this)

### Bug
- [x] `get_bbox()` on an OpsSet that has ops but no point data (e.g. only SET_PEN) returns (inf, inf, -inf, -inf) rather than (0, 0, 0, 0). The empty-list early-return doesn't cover that case. The test documents this as the current behavior — worth fixing in a follow-up if `get_bbox()` is ever called on partially-constructed OpsSet objects.

---

## Phase 2 — New Primitives & Animations

### Flowcharts
- [x] `FlowchartNode` — `Rectangle` + `Text`, anchored together as a `DrawableGroup`; takes `label`, `position`, `size`
- [x] `FlowchartDiamond` — decision node (rotated square + text)
- [x] `FlowchartConnector` — `Arrow` that auto-routes between two `FlowchartNode` anchors (by reference, not hard-coded coords)
- [x] `Flowchart.from_dict(spec)` — factory that builds the full graph from a declarative dict `{"nodes": [...], "edges": [...]}`

### Tables
- [x] `Table` drawable — grid of `Rectangle` + `Text` cells; configurable `n_rows`, `n_cols`, `cell_width`, `cell_height`, header styling
- [x] `Table.animate_by_row()` / `.animate_by_cell()` — returns a `CompositeAnimationEvent` that reveals cells in sequence

### Image & Video import
- [x] `RasterImage` drawable — load PNG/JPG via Pillow, render to Cairo surface via `OpsType.IMAGE`; supports translate, scale, rotate, opacity; fades in with SketchAnimation, works with FadeIn/FadeOut
- [ ] `VideoClip` drawable — extract frames from a video file via `moviepy`, render the frame matching the current scene time; useful for compositing hand-drawn annotations over real footage

### New animation types
- [x] **`RotateAnimation`** — animates `OpsSet.rotate(angle * progress)` around the center of gravity; useful for spinning diagrams
- [x] **`ColorTransitionAnimation`** — interpolates `SET_PEN` color between two RGB values across `progress`; complete the `apply_strokes_gradient` stub as a building block
- [x] **`CameraAnimation`** (scene-level) — animate `Viewport` pan/zoom over time; lets the "camera" drift across a large canvas or zoom into a detail

### Coordinate helpers
- [ ] Named anchor methods on `Drawable`: `.anchor("top_left")`, `.anchor("center")`, `.anchor("bottom_right")` — returns `(x, y)` in world coordinates, computed from the bounding box
- [ ] `Scene.place_relative(drawable_a, drawable_b, anchor_a, anchor_b, offset)` — helper to position `b` relative to `a` without manual coordinate arithmetic
- [ ] **`scene.wait(duration, after=None)`** utility — adds blank time; syntactic sugar for advancing the timeline without adding a new drawable


### Cleanup
- [x] Deprecate & Remove Legacy SVG: primitives/svg.py is marked as deprecated and relies on svgpathtools (which is a dev-only dependency according to repo_overview.md). It would be cleaner to remove this file entirely (or move it to a distinct legacy module) to ensure users don't accidentally import it and hit missing dependency errors, enforcing VectorSVG as the sole SVG handler.
- [x] Complete ZigZagLineFillPattern: Implemented in stylings/fillpatterns.py, registered as `fill_pattern="zigzag"` in `get_filler()`.



---

## Phase 3 — AI Integration (`handanim_ai`)

The `handanim_ai` module already has the two-prompt pipeline scaffolded. Expand it:

- [ ] **Structured scene representation** — replace the free-text scene description passed between the two LLM calls with a JSON schema (list of `{drawable, animation, timing}` objects); makes the codegen prompt more reliable and the output parseable
- [ ] **Code execution & feedback loop** — after `codegen.txt` generates code, execute it in a subprocess, catch exceptions, and feed them back to the LLM for self-correction (1–2 retry loop)
- [ ] **Asset awareness** — let the AI prompt know about files in `fonts/` and an `assets/` folder so it can reference them in generated code
- [ ] **CLI entry point** — `handanim-ai generate "explain the Pythagorean theorem"` that runs the full pipeline and opens the result
- [ ] **Prompt versioning** — move prompts to a structured YAML with version field; makes A/B testing prompt changes easier

---

## Phase 4 — Handwriting Font Generation

Goal: generate a usable single-line stroke font from a handful of hand-written samples.

- [ ] **Data collection tool** — a simple web/tablet UI (could be a Jupyter widget using `ipycanvas`) that records pen strokes per character as `(x, y, time)` sequences
- [ ] **Preprocessing pipeline** — normalize scale, resample to uniform arc-length, center each glyph; output to the existing `handanimtype1.json` format
- [ ] **Stroke-RNN baseline** — adapt [Sketch-RNN](https://github.com/magenta/magenta/tree/main/magenta/models/sketch_rnn) or Ha & Eck (2017) to condition on character identity; train on collected samples
- [ ] **Transformer alternative** — sequence-to-sequence transformer conditioned on a character token; generates stroke deltas `(dx, dy, pen_up)` autoregressively
- [ ] **Export pipeline** — sample from trained model per character → smooth with Bezier fitting → write to `fonts/custom/<name>.json`
- [ ] **Quality metric** — DTW distance between generated and reference strokes; character recognition accuracy using a frozen classifier

---

## Phase 5 — Voice & Audio (`larynxanim`)

Long-term: a companion module (possibly a separate repo) that adds audio/voice to handanim scenes.

- [ ] **TTS integration** — generate voice narration from a script string using Coqui TTS or an API (ElevenLabs, OpenAI); save as WAV
- [ ] **Audio-visual sync** — align `AnimationEvent` timings with sentence timestamps from the TTS output (forced alignment via `aeneas` or Whisper)
- [ ] **Final mix** — composite audio + Cairo-rendered video frames using `moviepy`
- [ ] **Auto-subtitle** — burn subtitles onto frames at the aligned timestamps
- [ ] **Lip-sync SVG characters** — parameterize mouth shape in `VectorSVG` characters as named path groups; animate them in sync with phonemes

---

## Architectural Improvements (ongoing)

- [ ] **Deprecate legacy `SVG`** — funnel all SVG import through `VectorSVG`; remove `svgpathtools` as a hard requirement
- [ ] **Unify style location** — `core/styles.py` has type definitions, `stylings/` has utility functions; add a top-level note in each file pointing to the other; consider moving `color.py` constants into `core/styles.py` so a single import suffices
- [ ] **`Scene.add()` return value** — return the `drawable` (or a handle) so calls can be chained: `handle = scene.add(event, rect)`
- [ ] **Type annotations audit** — several functions use `Any` loosely; tighten with `TypeVar` for `Drawable` subclasses and overloads for `OpsSet` transforms
- [ ] **`handanim_ai` as proper subpackage** — rename import path from `handanim_ai` to `handanim.ai` for consistency; adjust `pyproject.toml` package include

---

## Growth & Community

### README & visual presence
- [ ] **Animated GIF showcase in README** — add a grid of 4–6 rendered GIFs near the top of `README.md`; the outputs already exist in `examples/output/`; this is the single highest-leverage change for converting visitors into stars
- [ ] **Manim comparison table** — add a concise feature/complexity comparison vs Manim in the README; position handanim as the lightweight, script-friendly, `pip install`-able alternative for users who find Manim too heavy

### Discoverability
- [ ] **Algorithm & data-structure examples** — add examples for high-search topics: binary search, bubble sort, BFS/DFS graph traversal, Fourier transform; these attract students, educators, and bloggers who link back to the repo
- [ ] **Jupyter inline rendering** — implement `Scene.show()` that renders the animation as an inline IPython display widget; lowers the barrier for data-science users who live in notebooks and never save files first
- [ ] **`handanim-ai` end-to-end demo** — record a short screen capture of the full AI pipeline (text prompt → generated code → rendered GIF); the most shareable asset for social media; publish alongside a working CLI entry point

### Community infrastructure
- [ ] **Enable GitHub Discussions** — turn on the Discussions tab with "Show and Tell", "Q&A", and "Ideas" categories; gives users a place to share creations without opening an issue
- [ ] **"Built with handanim" section in README** — invite users to submit their animations; seed it with the existing example outputs; user-generated social proof compounds over time
- [ ] **Discord or community chat** — a lightweight Discord server (or a link to a GitHub Discussions thread) where contributors can discuss design decisions in real time

### Outreach (one-time actions)
- [ ] **HackerNews "Show HN" post** — write a post linking to the README once the GIF showcase is in place; Tuesday/Wednesday morning UTC is the highest-traffic window
- [ ] **Reddit posts** — post rendered GIFs on r/dataisbeautiful (no code needed, just visuals); post the library on r/Python and r/learnpython with a short code snippet
- [ ] **Twitter / X thread** — post a thread showing 4–5 rendered animations with a "10 lines of Python" angle; animated GIFs perform extremely well on the platform
