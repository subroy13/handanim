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
- [x] **Top-level exports** — populate `src/handanim/__init__.py` with the commonly-used classes (`Scene`, `Text`, `Rectangle`, `Circle`, `Arrow`, `SketchAnimation`, `FadeInAnimation`, etc.) so users can write `from handanim import Scene` instead of importing from submodules
- [ ] **PyPI publication** — publish `v0.1.0` so `pip install handanim` works and the package is discoverable
  - [x] Fill in `description` in `pyproject.toml` (currently empty string)
  - [x] Add `license = "MIT"` (or match `LICENSE` file) to `pyproject.toml`
  - [x] Add `classifiers` — e.g. `"Development Status :: 3 - Alpha"`, `"Intended Audience :: Education"`, `"Topic :: Multimedia :: Graphics"`, `"Programming Language :: Python :: 3.11"`
  - [x] Add `keywords` — e.g. `["animation", "hand-drawn", "manim", "math", "whiteboard", "education"]`
  - [x] Add `[tool.poetry.urls]` block with `Homepage`, `Repository`, and `Documentation` links
  - [ ] Wire `[tool.poetry.extras] ai` — list the optional AI deps so `pip install handanim[ai]` pulls them
  - [ ] Verify `README.md` renders correctly as PyPI long description (no raw HTML, no local image paths)
  - [x] Run `poetry build` locally and inspect the `dist/` wheel/sdist for unexpected files
  - [x] Publish to TestPyPI first: `poetry publish --repository testpypi` and verify `pip install --index-url https://test.pypi.org/simple/ handanim` works
  - [ ] Publish to PyPI: `poetry publish`
  - [ ] Add PyPI version badge to `README.md`
  - [ ] Add a GitHub Actions release workflow that runs `poetry publish` automatically on a `v*` tag push
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
- [x] Named anchor methods on `Drawable`: `.anchor("top_left")`, `.anchor("center")`, `.anchor("bottom_right")` — returns `(x, y)` in world coordinates, computed from the bounding box
- [x] `Scene.place_relative(drawable_a, drawable_b, anchor_a, anchor_b, offset)` — helper to position `b` relative to `a` without manual coordinate arithmetic
- [x] **`scene.wait(duration)`** utility — returns the time after a pause; syntactic sugar for computing start times without manual arithmetic


### Cleanup
- [x] Deprecate & Remove Legacy SVG: primitives/svg.py is marked as deprecated and relies on svgpathtools (which is a dev-only dependency according to repo_overview.md). It would be cleaner to remove this file entirely (or move it to a distinct legacy module) to ensure users don't accidentally import it and hit missing dependency errors, enforcing VectorSVG as the sole SVG handler.
- [x] Complete ZigZagLineFillPattern: Implemented in PR #10 — replaces commented-out code with working OpsSet-based implementation. Fixed geometry bugs in original (atan→atan2, perpendicular offset, per-segment midpoint). Registered as `fill_pattern="zigzag"` in `get_filler()`.



---

## Phase 3 — AI Integration (`handanim_ai`)

The `handanim_ai` module already has the two-prompt pipeline scaffolded. Expand it:

- [ ] **Structured scene representation** — replace the free-text scene description passed between the two LLM calls with a JSON schema (list of `{drawable, animation, timing}` objects); makes the codegen prompt more reliable and the output parseable
- [ ] **Code execution & feedback loop** — after `codegen.txt` generates code, execute it in a subprocess, catch exceptions, and feed them back to the LLM for self-correction (1–2 retry loop)
- [ ] **Asset awareness** — let the AI prompt know about files in `fonts/` and an `assets/` folder so it can reference them in generated code
- [ ] **CLI entry point** — `handanim-ai generate "explain the Pythagorean theorem"` that runs the full pipeline and opens the result
- [ ] **Prompt versioning** — move prompts to a structured YAML with version field; makes A/B testing prompt changes easier

---

## Phase 3.5 — Export & Presentation Pipeline

Goal: make handanim output usable beyond standalone MP4 — in slides, web pages, and printable handouts. (Proposed by Subrata)

### SVG / PDF snapshot export

- [x] **`scene.render_keyframes(times, format="svg|pdf")`** — batch export a list of timestamps to numbered SVG or PDF files; computes timeline once. *(Difficulty: easy)*
- [x] **`scene.export_storyboard(n_frames, output_dir)`** — auto-pick `n` evenly-spaced keyframes and export as SVG or PDF. *(Difficulty: easy)*

### Slide deck export

- [x] **Beamer/LaTeX overlay export** — `scene.export_beamer()` exports keyframe PDFs + generates a compilable `slides.tex` with `\only<N>` overlays. *(Difficulty: medium)*
- [x] **Native TikZ backend for Beamer** — `scene.export_beamer(backend="tikz")` emits inline TikZ drawing commands instead of embedded PDF images. Also adds `scene.render_tikz()` for standalone TikZ output. `TikZRenderer` converts OpsSet ops (lines, curves, fills, dots, opacity) to TikZ paths with coordinate transform, colour deduplication, and partial-op support. Compiles cleanly with pdflatex. *(Difficulty: medium)*
- [ ] **reveal.js / HTML export (embed approach)** — export per-slide MP4/GIF clips and embed them into a reveal.js HTML deck. No client-side animation replay, just embedded media. *(Difficulty: medium — template generation + splitting video at keyframe boundaries)*
- [ ] **reveal.js / HTML export (animated SVG replay)** — build a JS-based player that replays the OpsSet timeline in the browser using SVG or Canvas. Would need a completely separate rendering path from Cairo — essentially a second renderer translating OpsSet ops into DOM SVG elements with timed playback. *(Difficulty: hard — Cairo SVG output is flat with no semantic structure matching OpsSet ops)*
- [ ] **SVG+CSS vs SVG+JS animation investigation** — determine whether CSS `@keyframes` on SVG path elements can approximate stroke-by-stroke sketch animation, or whether a small JS player reading a timeline JSON is more practical. *(Difficulty: hard — research/prototyping, uncertain output quality)*

### Handout / static export

- [x] **PDF handout mode** — `scene.render_handout()` produces a single multi-page PDF with one frame per page. *(Difficulty: easy)*
- [ ] **Annotated handout** — allow attaching text annotations per keyframe (e.g., `scene.annotate(t=3.0, text="Note: chain rule applied here")`); render alongside the frame in the PDF. *(Difficulty: medium — needs annotation data model + PDF layout logic)*

---

## Phase 4A — Custom Font Builder (Skeletonization)

Goal: produce high-quality single-stroke glyph paths from existing sources (TTF outlines, real handwriting datasets) and wire them into the rendering pipeline via the custom JSON font format.

### Bug fixes (already done)
- [x] **Text left-edge anchor** — `Text.draw()` now passes `self.position` directly to `_draw_line`, consistent with `Math`; both use top-left anchor.
- [x] **Hershey font/char mapping** — replaced broken `mathlow`/`mathupp` (all chars → charcode 12345) with `greeks`/`greekc` using the correct sequential Latin-proxy encoding; fixed all 48 Greek letter entries in `UNICODE_TO_HERSHEY`.
- [x] **Hershey math symbol coverage** — added `COMPOSED_GLYPHS` hand-drawn strokes for ∑, ∫, ∂, ∇, ∞, ≤, ≥, ≠, ≈, →, ⟨, ⟩, ⌊⌋, ⌈⌉, and more; extended `UNICODE_TO_HERSHEY` for operators and arrows.

### Features to build
- [ ] **Centerline/skeleton extraction** (`tools/fontmaker/make_fonts.py`) — rasterise each TTF glyph (STIX Two Math or DejaVu Math) to a bitmap, apply Zhang-Suen thinning (`skimage`), vectorise the skeleton into smooth spline paths, determine natural stroke order via Eulerian path on connected components, and write to the custom JSON format. *(Difficulty: medium)*
- [ ] **CROHME InkML ingestion** — parse real human pen-stroke sequences from the CROHME dataset (`(x, y, t)` InkML), normalize/smooth/resample, and export to custom JSON; use as priority-1 font source ahead of Hershey and TTF skeleton. *(Difficulty: medium)*
- [ ] **Roughification layer** — deterministic Perlin/simplex noise jitter on `LINE_TO`/`CURVE_TO` control points (amplitude × `roughness`, seeded for reproducibility); apply in `hershey_glyph_opsset` and `custom_glyph_opsset` so all glyph paths look hand-drawn. *(Difficulty: easy-medium)*
- [ ] **Layered font fallback chain** — replace single-backend dispatch in `Math.get_glyph_opsset()` with a priority-ordered chain: custom JSON → Hershey → skeleton TTF → raw TTF outline; configurable per `Math` instance. *(Difficulty: easy)*
- [ ] **Stroke ordering for SketchAnimation** — optional `stroke_order="natural"` flag that groups OpsSet by `MOVE_TO` boundaries and reorders strokes with a nearest-neighbour heuristic so the reveal animates like actual handwriting. *(Difficulty: medium)*
- [ ] **Unified `MathText` primitive** — merge `Math` and `Text` (or add `math=True` flag to `Text`) so `$...$` sections are routed through `MathTextParser` while plain text uses the hand-drawn font, both with a consistent left-edge `position` anchor. *(Difficulty: medium)*
- [ ] **Spacing/kerning fix** — audit the gaps between glyphs in LaTeX math output; likely a mismatch between `MathTextParser` bounding-box reporting and actual single-stroke glyph widths; may require per-glyph kerning tables in the JSON font format. *(Difficulty: medium)*
- [ ] **Math symbol coverage expansion** — extend `handanimtype1.json` to cover ∑, ∫, ∂, ∈, →, ≤, etc.; `tools/fontmaker/symbols.py` has the label list started. *(Difficulty: medium)*

---

## Phase 4B — Neural Font Generation

Goal: generate a usable single-line stroke font from a handful of hand-written samples using learned sequence models.

Note: standard fonts are double-stroke (outlines), but handanim needs single-stroke for the hand-drawn aesthetic. Single-stroke fonts do not support math/LaTeX natively — hence the current approach of LaTeX parsing → custom glyph substitution in `Math` primitive.

- [ ] **Data collection tool** — Jupyter widget using `ipycanvas` that records pen strokes per character as `(x, y, time)` sequences directly in a notebook. *(Difficulty: easy)*
- [ ] **Preprocessing pipeline** — normalize scale, resample to uniform arc-length, center each glyph; output to the existing `handanimtype1.json` format. *(Difficulty: easy)*
- [ ] **Stroke-RNN baseline** — adapt [Sketch-RNN](https://github.com/magenta/magenta/tree/main/magenta/models/sketch_rnn) (Ha & Eck 2017) conditioned on character identity; train on collected samples and/or Google QuickDraw 2019–2020 stroke data. *(Difficulty: medium)*
- [ ] **Transformer alternative** — sequence-to-sequence transformer conditioned on a character token; generates stroke deltas `(dx, dy, pen_up)` autoregressively; evaluate against Sketch-RNN baseline. *(Difficulty: medium-hard)*
- [ ] **WriteVIT (2025)** — investigate the 2025 vision-transformer approach for higher-quality single-stroke output. *(Difficulty: medium-hard)*
- [ ] **Export pipeline** — sample from trained model per character → smooth with Bézier fitting → write to `fonts/custom/<name>.json`. *(Difficulty: easy)*
- [ ] **Quality metric** — DTW distance between generated and reference strokes; character recognition accuracy using a frozen classifier. *(Difficulty: medium)*

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
