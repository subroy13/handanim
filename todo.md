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
- [ ] `RasterImage` drawable — load PNG/JPG via Pillow, render to Cairo surface as an OpsSet-compatible operation (needs a new `OpsType.RASTER_IMAGE` or direct Cairo `set_source_surface`)
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
- [ ] Complete ZigZagLineFillPattern: In stylings/fillpatterns.py, the ZigZagLineFillPattern class is currently commented out entirely with a # TODO: Check and fix this. Completing this would provide a fantastic new sketchy fill style (like a back-and-forth colored pencil shading) to complement the existing hatching.



---

## Phase 3 — AI Integration (`handanim_ai`)

The `handanim_ai` module already has the two-prompt pipeline scaffolded. Expand it:

- [ ] **Structured scene representation** — replace the free-text scene description passed between the two LLM calls with a JSON schema (list of `{drawable, animation, timing}` objects); makes the codegen prompt more reliable and the output parseable
- [ ] **Code execution & feedback loop** — after `codegen.txt` generates code, execute it in a subprocess, catch exceptions, and feed them back to the LLM for self-correction (1–2 retry loop)
- [ ] **Asset awareness** — let the AI prompt know about files in `fonts/` and an `assets/` folder so it can reference them in generated code
- [ ] **CLI entry point** — `handanim-ai generate "explain the Pythagorean theorem"` that runs the full pipeline and opens the result
- [ ] **Prompt versioning** — move prompts to a structured YAML with version field; makes A/B testing prompt changes easier

---

## Phase 4 — Neural Handwriting Font Generation

**Goal:** replace the static TTF/JSON font lookup in `Text` and `Math` with a neural stroke model that generates natural-looking handwritten strokes per character or symbol on demand. The model runs as a lightweight optional extra (`pip install handanim[stroke]`) with no PyTorch dependency at inference time.

**Branch:** `feat/font-modelling`

---

### Code layout to create

```
tools/stroke_model/          # PyTorch lives here — training only, not installed
├── model.py                 # SketchRNN architecture (PyTorch)
├── preprocess.py            # raw stroke data → normalised training tensors
├── train.py                 # training loop + checkpoint saving
├── export.py                # PyTorch checkpoint → ONNX file
└── collect.py               # data collection UI (Jupyter widget)

src/handanim/fonts/
└── stroke_model.py          # ONNX inference wrapper — no torch import
```

`text.draw()` and `math.draw()` import only from `src/handanim/fonts/stroke_model.py`. The PyTorch architecture in `tools/` is a training-time artifact only; once the `.onnx` is exported it is no longer needed at runtime.

---

### Step 1 — Data sourcing and format

**Stroke format (standard across all sources):**
Every sample is a variable-length sequence of tuples `(dx, dy, pen_state)` where:
- `dx`, `dy` — displacement from previous point (delta encoding, normalised to unit variance)
- `pen_state` — `0` = pen drawing, `1` = pen lifted / start next stroke, `2` = end of sequence

**Data sources (use all three together):**

- [ ] **HASYv2** ([paper](https://arxiv.org/abs/1701.08380), [download](https://zenodo.org/record/259444)) — 32,116 handwritten samples of 369 LaTeX math symbols (`\alpha`, `\sum`, `\int`, `\frac`, Greek letters, operators, etc.). This is the primary source for math coverage. License: CC BY 4.0. Each sample is a 32×32 PNG + ground-truth LaTeX label. Convert bitmaps to stroke sequences via thinning + vectorisation (`skimage.morphology.skeletonize` → chain-code → delta encoding); store results in the canonical `(dx, dy, pen_state)` format.

- [ ] **QuickDraw** ([download](https://github.com/googlecreativelab/quickdraw-dataset)) — ~50M stroke samples across 345 categories. Use the `full/simplified/` NDJSON files for the alphanumeric categories (`a`–`z`, `0`–`9`). Already in stroke-delta format — just filter, normalise, and trim to max sequence length. License: CC BY 4.0.

- [ ] **Synthetic bootstrap from existing JSON font** — convert `fonts/handanimtype1.json` SVG path strings to stroke sequences using the same `_svg_paths_to_opsset` pipeline in `math.py`: sample uniform points along each path segment, compute deltas, encode pen state from path structure. Free; gives immediate coverage for ASCII. Label each stroke with its character. Use as a low-weight supplement (not a primary source — strokes will be too smooth).

- [ ] **Store all preprocessed data** in a single `.npz` file per dataset split (`train.npz`, `val.npz`) with arrays: `strokes` (ragged, stored as object array or padded), `labels` (integer character/symbol ids), `lengths` (sequence lengths before padding). Define a shared `vocab.json` mapping character/LaTeX-symbol strings to integer ids; keep it in `tools/stroke_model/vocab.json` and also copy it alongside any exported ONNX file.

---

### Step 2 — Preprocessing (`tools/stroke_model/preprocess.py`)

- [ ] **Normalise scale** — for each glyph, scale so that the bounding box height = 1.0 (preserve aspect ratio)
- [ ] **Resample to uniform arc-length** — interpolate so consecutive points are equidistant; use 96 points per glyph as the default target length (configurable)
- [ ] **Compute deltas** — convert absolute `(x, y)` to `(dx, dy)`; clip outlier deltas at ±3σ
- [ ] **Pad / truncate** to a fixed max length (e.g. 200 steps); store `lengths` array to mask padding in the loss
- [ ] **Augment during training only** — small random rotation (±15°), scale jitter (0.9–1.1×), time-stretch (resample to ±10% of target length then re-pad); do NOT augment val/test

---

### Step 3 — Model architecture (`tools/stroke_model/model.py`)

Use a **Sketch-RNN** (Ha & Eck, 2018 — [paper](https://arxiv.org/abs/1704.03477)) conditioned on a character identity token. Rationale: generates `(dx, dy, pen_state)` natively, checkpoint size ~3–8 MB, fast autoregressive inference (no KV-cache complexity), well-understood failure modes.

- [ ] **Encoder** — single-layer bidirectional LSTM, hidden size 256; reads the input stroke sequence; outputs a latent vector `z` via reparameterisation (VAE-style); condition on character id by concatenating a learned embedding (vocab size × 64) to the input at every step
- [ ] **Decoder** — single-layer LSTM, hidden size 512; at each step takes `(prev_point, z, char_embedding)` as input; outputs parameters of a Gaussian Mixture Model (20 components) over `(dx, dy)` plus a 3-way categorical over `pen_state`
- [ ] **Loss** — reconstruction loss = negative log-likelihood of the MDN output + cross-entropy over pen state; KL divergence term on `z` with KL annealing (start weight 0 → 1 over first 20% of training)
- [ ] **Config** — expose all hyperparameters via a YAML config file (`tools/stroke_model/config.yaml`): hidden sizes, num mixtures, latent dim, max sequence length, learning rate, batch size, KL weight schedule

---

### Step 4 — Training (`tools/stroke_model/train.py`)

- [ ] Self-contained script; no external trainer framework (standard PyTorch training loop is sufficient for this model size)
- [ ] Dependencies (training only, never installed by `pip install handanim`): `torch>=2.0`, `numpy`, `pyyaml`, `tqdm`
- [ ] Save checkpoint every N epochs as `checkpoints/epoch_{n}.pt`; also save `best.pt` tracking lowest val loss
- [ ] Log train loss, val loss, and KL weight to a simple CSV (`training_log.csv`) so progress is inspectable without tensorboard
- [ ] Provide a `--resume` flag to continue from a checkpoint
- [ ] Target: val NLL < 0.5 on HASYv2 + QuickDraw combined; typically achieved in ~50 epochs on a laptop GPU

---

### Step 5 — Export to ONNX (`tools/stroke_model/export.py`)

- [ ] Load `best.pt`; run `torch.onnx.export` with `opset_version=17`
- [ ] Export the **decoder only** (the encoder is only needed at training time for the VAE; at inference, sample `z` from the prior `N(0, I)` or use a fixed `z=0` for deterministic output)
- [ ] Verify the ONNX model output matches the PyTorch output to within 1e-4 (use `onnxruntime` to run both)
- [ ] Bundle `vocab.json` alongside the ONNX file — they must be versioned together
- [ ] Output: `stroke_model_v1.onnx` + `vocab.json` ready for upload to Hugging Face Hub

---

### Step 6 — Hugging Face Hub hosting

- [ ] Create a model repo at `huggingface.co/subroy13/handanim-stroke-model`
- [ ] Upload `stroke_model_v1.onnx` and `vocab.json` to the repo; use git tags for versioning (`v1`, `v2`, …)
- [ ] Write a model card (`README.md` in the HF repo) describing: training data, character coverage, performance metrics, how to use via `handanim[stroke]`
- [ ] Add `huggingface_hub` as an optional runtime dependency alongside `onnxruntime` in `pyproject.toml`:
  ```toml
  [tool.poetry.extras]
  stroke = ["onnxruntime", "huggingface-hub"]
  ```

---

### Step 7 — Inference integration (`src/handanim/fonts/stroke_model.py`)

- [ ] **`StrokeModel` class** with:
  - `StrokeModel.load(model_name="subroy13/handanim-stroke-model", revision="v1")` — downloads `stroke_model_v1.onnx` and `vocab.json` to `~/.handanim/models/` via `huggingface_hub.hf_hub_download`; caches locally; no re-download on subsequent calls
  - `StrokeModel.generate(char: str, temperature: float = 0.8) -> OpsSet` — runs one autoregressive decode pass through the ONNX session; converts `(dx, dy, pen_state)` output to an OpsSet (`MOVE_TO`, `LINE_TO`, `CLOSE_PATH` ops); scales to match the requested font size
  - Raises `ImportError` with `pip install handanim[stroke]` message if `onnxruntime` is not installed

- [ ] **Fallback in `Text.draw()` and `Math.custom_glyph_opsset()`**:
  ```python
  try:
      from ..fonts.stroke_model import StrokeModel
      model = StrokeModel.load()
      return model.generate(char)
  except (ImportError, FileNotFoundError):
      return self._legacy_font_draw(char)   # existing TTF / JSON path
  ```
  Stroke model is opt-in; existing behaviour is the default until `handanim[stroke]` is installed.

- [ ] **`StrokeModel` is not imported at module load time** — use a lazy import inside `draw()` so that importing `handanim` never triggers an `onnxruntime` import or a network call

---

### Step 8 — Data collection tool for custom handwriting (`tools/stroke_model/collect.py`)

- [ ] Jupyter widget using `ipycanvas` — display one character prompt at a time; record raw `(x, y, timestamp)` on pen-down events; save each sample as JSON on pen-up
- [ ] Collect at least 5 samples per character; show a progress bar over the full target character set (configurable subset — e.g. Latin only, or Latin + digits + common math)
- [ ] Save collected data to `data/my_style/raw/{char_id}/{sample_n}.json`
- [ ] `preprocess.py` can be pointed at this directory: `python preprocess.py --data data/my_style/raw --out data/my_style/train.npz`
- [ ] `train.py --config config.yaml --data data/my_style/train.npz --pretrained best.pt` — fine-tune from the public pretrained checkpoint on the user's collected samples; typically 10–20 epochs sufficient for style transfer
- [ ] `export.py` outputs `my_style_v1.onnx`; user places it in `~/.handanim/models/` and sets `font="my_style"` in their scene:
  ```python
  Text("Hello", font="my_style", ...)
  ```

---

### Step 9 — Quality metrics

- [ ] **DTW distance** — Dynamic Time Warping between generated stroke and nearest reference stroke in the val set; lower is better; use `dtaidistance` library
- [ ] **Recognisability** — run generated strokes through a frozen CNN classifier (train a simple ResNet-18 on the HASYv2 bitmaps); target top-1 accuracy > 85% on math symbols
- [ ] **Diversity** — generate 10 samples per character; compute mean pairwise DTW; a good model should show variation, not copy a single template
- [ ] Log all three metrics in `train.py` at the end of each epoch alongside the NLL loss

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

- [x] **Deprecate legacy `SVG`** — funnel all SVG import through `VectorSVG`; remove `svgpathtools` as a hard requirement
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


## More Ideas

- Paper folding pattern in background and paper folding into ball animation for screen change.
- "Recall that I said this" (Pick a folded paper ball up and show the previous screen).
- 