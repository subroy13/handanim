# ✍️ handanim

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/subroy13/handanim/blob/master/notebooks/handanim_colab_playground.ipynb)
[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/subroy13/handanim)
[![Build and Deploy Docs](https://github.com/subroy13/handanim/actions/workflows/docs.yml/badge.svg)](https://github.com/subroy13/handanim/actions/workflows/docs.yml)
[![PyPI version](https://img.shields.io/pypi/v/handanim.svg)](https://pypi.org/project/handanim/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

**Programmatic whiteboard animation in Python — with auto-synced neural voiceover, procedural chalk & eraser sound effects (`voiceanim`), native LaTeX Beamer/TikZ slide export (`export_beamer()`), and a Model Context Protocol (MCP) server for Claude & Cursor (`aianim`).**

> 🚀 **Zero-Install Browser Playgrounds**:
> - **Google Colab Notebook**: Click **[Open in Colab](https://colab.research.google.com/github/subroy13/handanim/blob/master/notebooks/handanim_colab_playground.ipynb)** ([`notebooks/handanim_colab_playground.ipynb`](notebooks/handanim_colab_playground.ipynb)) for a full interactive Python notebook.
> - **Hugging Face Space (Gradio UI)**: Try the interactive web builder in [`huggingface_space/`](huggingface_space/) ([**🤗 Hugging Face Space**](https://huggingface.co/spaces/subroy13/handanim)).

<p align="center">
  <img src="docs/source/_static/gallery/hero_showcase.gif" width="760" alt="handanim 5-second showcase: handwriting LaTeX math, sketching a flowchart, erasing a section, and panning the camera">
  <br>
  <sub>🔊 <b>Sound on:</b> <a href="docs/source/_static/gallery/hero_showcase.mp4">Watch <code>hero_showcase.mp4</code> with procedural chalk sketching, eraser audio &amp; ducked background music (-14 LUFS stereo)</a></sub>
</p>

```python
from handanim import (
    BLUE, ERASER_HINT_COLOR, NAVY, PASTEL_BLUE, PASTEL_GREEN, PASTEL_ORANGE, RED,
    CameraAnimation, Eraser, FillStyle, Flowchart, Math, Scene, SketchAnimation, StrokeStyle, Text,
)

scene = Scene(width=960, height=540, fps=24, sketch_sound=True, background_music="calm")

formula = Math(r"$y = \sigma(Wx + b)$", position=(80, 70), font_size=64, stroke_style=StrokeStyle(color=BLUE, width=2.5))
draft = Text("Draft: linear only?", position=(80, 215), font_size=36, stroke_style=StrokeStyle(color=RED, width=2))
flow = Flowchart.from_dict({
    "nodes": [
        {"id": "x", "label": "Input x", "position": [220, 390], "size": [190, 74], "font_size": 28, "fill_style": FillStyle(color=PASTEL_BLUE)},
        {"id": "h", "label": "Hidden Wx+b", "position": [540, 390], "size": [230, 74], "font_size": 28, "fill_style": FillStyle(color=PASTEL_ORANGE)},
        {"id": "y", "label": "Output y", "position": [860, 390], "size": [190, 74], "font_size": 28, "fill_style": FillStyle(color=PASTEL_GREEN)},
    ],
    "edges": [
        {"from": "x", "to": "h", "from_side": "right", "to_side": "left"},
        {"from": "h", "to": "y", "from_side": "right", "to_side": "left"},
    ],
})
eraser = Eraser(objects_to_erase=[draft], drawable_cache=scene.drawable_cache, glow_dot_hint={"color": ERASER_HINT_COLOR, "radius": 8})
fixed = Text("Non-linear activation!", position=(80, 215), font_size=38, stroke_style=StrokeStyle(color=NAVY, width=2.2))

scene.add(SketchAnimation(start_time=0.0, duration=1.1), drawable=formula)
scene.add(SketchAnimation(start_time=0.6, duration=0.8), drawable=draft)
scene.add(SketchAnimation(start_time=1.4, duration=1.5), drawable=flow)
scene.add(SketchAnimation(start_time=2.9, duration=0.8), drawable=eraser)
scene.add(SketchAnimation(start_time=3.7, duration=0.6), drawable=fixed)
scene.add(CameraAnimation(start_time=3.6, duration=1.2, data={"to_xrange": (120, 1080), "to_yrange": (40, 580)}))

scene.render("hero_showcase.mp4", max_length=5.0)               # MP4 with synced chalk/eraser SFX + theme music
scene.export_beamer("slides/", n_frames=5, backend="tikz")      # Compilable LaTeX Beamer deck with native TikZ
```

---

## ⚖️ Why `handanim`? (vs. Manim & VideoScribe / Doodly)

| Capability | ✍️ **`handanim`** (`handanim` + `voiceanim` + `aianim`) | 📐 **Manim** (3Blue1Brown / Community) | 🖱️ **VideoScribe / Doodly** |
| :--- | :--- | :--- | :--- |
| **Visual Aesthetic Out of the Box** | **Hand-drawn whiteboard & sketchbook** (progressive stroke-by-stroke sketching, RoughJS-style jitter, hachure & cross-hatch fills, glowing pen tip & physical eraser) | Clean geometric vector lines & smooth mathematical morphs | Pre-baked SVG clipart traced by a static hand cursor |
| **Built-In Procedural Audio (`voiceanim`)** | **Yes — zero external audio editing.** Automatic chalk-on-board sketching, eraser wiping, page-turn/paper-crumple SFX, and ducked theme music mastered to **-14 LUFS stereo** | ❌ None (silent video output; audio must be produced externally) | ⚠️ Manual drag-and-drop stock music loops |
| **Voiceover & Word-Level Sync (`voiceanim`)** | **Built-in offline neural TTS** (Kokoro-82M with **54 voices & 256-D latent voice blending**, Qwen3-TTS, AWS Polly), word-timed `Captions`, and `VoiceTimelineSync` to trigger drawings on exact spoken words | ❌ Requires third-party plugins and manual timestamping | ⚠️ Upload voiceover MP3 and drag elements by hand on a timeline |
| **LLM & Coding-Agent Readiness (`aianim`)** | **First-class MCP Server (`handanim-mcp`)** with 16 tools for Claude Desktop, Cursor, and Windsurf + declarative JSON scene compiler | ❌ No official MCP server or self-validating agent runtime | ❌ Closed proprietary GUI (not scriptable or Git-friendly) |
| **Native LaTeX Beamer / TikZ Export** | **`scene.export_beamer(..., backend="tikz")`** emits a compilable `.tex` slide deck with inline TikZ vector overlays (`\only<n>{...}`) from the exact same Python scene | ❌ Video / PNG / GIF output only | ❌ Video export only |
| **2D Character Rigging & Shorts** | **Hierarchical `CharacterRig`** with 2-joint inverse kinematics (`TwoJointLimb`), automatic blinking & lip-sync `VariantSlot`, plus `9:16` Shorts helpers | ❌ Manual coordinate math | ⚠️ Fixed character pose stamps |

---

## 🧩 Three Integrated Packages in One Install

### 1. ✍️ `handanim` — Sketch Primitives, Math, Flowcharts, 2D Character IK & Beamer Export
- **Handwritten Math & Single-Stroke Fonts**: Render LaTeX formulas (`Math(r"$\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}$")`) and multi-font text traced progressively along genuine stroke paths.
- **Declarative Diagrams & Data**: Built-in `Flowchart.from_dict(...)`, `Table` (with row-by-row reveal `table.animate_by_row(...)`), `BarChart`, `LinePlot`, and SVG vector sketching (`VectorSVG`).
- **2D Character Rigging & Inverse Kinematics**: Build expressive presenters with `CharacterRig`, `add_child`, `add_slot` (scheduled eye blinks and mouth visemes), and analytical 2-joint IK (`add_two_joint_limb`).
- **Physical Sketchbook Transitions**: Turn pages with `PageTurnTransition`, crumple discarded drafts with `PaperCrumpleTransition`, or wipe specific objects mid-scene with `Eraser`.
- **1-Line LaTeX Beamer & TikZ Export**: Turn any animated scene into lecture slides for Overleaf or `pdflatex` with `scene.export_beamer("slides/", n_frames=6, backend="tikz")`.

### 2. 🎙️ `voiceanim` — 54-Voice Local Neural TTS, Voice Blending, Word Sync & Auto SFX
- **54 Built-In Offline Kokoro-82M Voices + 256-D Latent Voice Blending**: Run local neural speech synthesis on CPU or Apple Silicon with zero API keys, and blend any voices in 256-D style space (`voice="am_puck:0.6+bm_fable:0.4"` or presets like `"blend_transatlantic"`, `"blend_professor"`, `"blend_indian_male"`). Also supports `Qwen3-TTS` (`provider="qwen"`) and `AWS Polly` (`provider="polly"`).
- **Word-Level Visual Sync & Dynamic Captions**: Trigger animations on the exact millisecond a word is spoken (`clip.word_time("paradox")`) and overlay dynamic word-highlighted subtitles (`Captions(clip)`).
- **Automatic Procedural Sound Design**: Every `SketchAnimation`, `Eraser`, `PageTurnTransition`, and `PaperCrumpleTransition` automatically synthesizes realistic chalk, eraser, or paper foley, mixed with auto-ducked background music to a broadcast-ready **-14.0 LUFS stereo** master with a true-peak limiter (`-1.5 dBFS`).

```python
from handanim import Captions, Math, Scene, SketchAnimation, StrokeStyle, BLUE
from voiceanim import VoiceEngine, VoiceTimelineSync

# 1. Synthesize narration locally with a 256-D latent blend of two Kokoro voices
clip = VoiceEngine.synthesize(
    "Notice how Euler's identity links five fundamental constants in a single equation.",
    voice="am_puck:0.6+bm_fable:0.4",  # Or any of the 54 voices / "blend_transatlantic"
)

scene = Scene(width=1280, height=720, audio=clip, background_music="marimba", sketch_sound=True)
sync = VoiceTimelineSync(clip)

# 2. Trigger the equation sketch on the exact word "Euler's" and finish on "equation."
t_start, t_end = sync.word_range("Euler's", "equation.")
eq = Math(r"$e^{i\pi} + 1 = 0$", position=(380, 260), font_size=96, stroke_style=StrokeStyle(color=BLUE, width=3))
scene.add(SketchAnimation(start_time=t_start, duration=t_end - t_start), drawable=eq)

# 3. Add word-highlighted subtitles on the camera-invariant overlay layer
scene.overlay.add(Captions.from_audio_clip(clip, position=(640, 620)))
scene.render("euler_explained.mp4")
```

### 3. 🤖 `aianim` — Model Context Protocol (MCP) Server & AI Scene Compiler
Connect Claude Desktop, Claude Code, Cursor, or Windsurf directly to `handanim` so your coding agent can inspect primitives, synthesize voiceovers, read word timestamps, compile declarative scenes, and render videos autonomously:

```bash
# Start the built-in MCP server over stdio (16 tools for scene creation, voice synthesis & rendering)
poetry run handanim-mcp
```

Add to your `claude_desktop_config.json` or `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "handanim": {
      "command": "handanim-mcp"
    }
  }
}
```

---

## 📷 Gallery Highlights

| Pythagorean Theorem (`Math` + `Eraser` + `Polygon`) | ML Workflow (`Flowchart.from_dict` + `Table`) |
| :---: | :---: |
| <img src="docs/source/_static/gallery/pythagoras.gif" width="420"> | <img src="docs/source/_static/gallery/ml_workflow_demo.gif" width="420"> |
| **Algebraic Proof of $(a + b)^2$** | **Distributive Property ($a(b+c) = ab + ac$)** |
| <img src="docs/source/_static/gallery/a_plus_b_square.gif" width="420"> | <img src="docs/source/_static/gallery/distributive_property.gif" width="420"> |

👉 Explore all tutorials—including **2D Character Rigging & IK**, **Sketchbook Page-Turn & Paper-Crumple Transitions**, and **Word-Synced Captions & Audio**—in the [Documentation Gallery](docs/source/gallery/examples.rst).

---

## 🚀 Quickstart & Installation

### ⚡ 1-Command Install (Bundled FFmpeg + Dual Cairo Backend)

- **FFmpeg is bundled automatically**: `handanim` depends on `imageio-ffmpeg`, so MP4 video rendering and stereo audio mastering work out of the box right after `pip install handanim`—no system `ffmpeg` install or `PATH` setup required.
- **Automatic `pycairo` → `cairocffi` fallback**: `handanim` uses prebuilt `pycairo` wheels when available and automatically falls back to pure-Python `cairocffi` (with automatic library discovery for Homebrew `/opt/homebrew/lib`, `/usr/local/lib`, and Conda `$CONDA_PREFIX/lib`). You can check the active backend with `handanim.get_cairo_backend()` or force `HANDANIM_CAIRO_BACKEND=cairocffi`.

#### Option A: From PyPI (`pip`)
```bash
# Windows & platforms with prebuilt pycairo wheels work immediately:
pip install handanim

# With local 54-voice Kokoro-82M neural TTS & audio extras (voiceanim):
pip install "handanim[voice]"

# With AI scene compiler & MCP server extras (aianim) + voiceanim:
pip install "handanim[all]"
```

> **If `pycairo` attempts a source build on Linux/macOS (missing system `libcairo`)**:
> - **Prefer prebuilt wheel**: `pip install --only-binary=:all: pycairo && pip install handanim`
> - **macOS (Homebrew)**: `brew install cairo && pip install handanim`
> - **Ubuntu / Debian / Colab**: `sudo apt-get update && sudo apt-get install -y libcairo2-dev && pip install handanim`

#### Option B: From Source (`poetry`)
```bash
git clone https://github.com/subroy13/handanim.git
cd handanim
poetry install

# List or render any gallery showcase animation
poetry run python docs/source/gallery/build_gallery.py --list
poetry run python docs/source/gallery/build_gallery.py --only hero_showcase
```

#### Option C: Using `conda` / `mamba` (Zero Compiler Needed on Any OS)
```bash
conda create -n handanim python=3.11
conda activate handanim
conda install -c conda-forge cairo pycairo
pip install "handanim[all]"
```

---

## 📄 License & Contributing

- **License**: [MIT License](LICENSE)
- **Contributions**: Pull requests for new sketch primitives, voice providers, character rig presets, and gallery tutorials are always welcome!

> ⭐️ If `handanim` helps your teaching, research talks, or explainer videos, please consider starring the repository on [GitHub](https://github.com/subroy13/handanim)!
