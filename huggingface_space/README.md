---
title: HandAnim Whiteboard Studio
emoji: ✍️
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: "5.12.0"
app_file: app.py
pinned: false
license: mit
tags:
  - animation
  - whiteboard
  - tts
  - kokoro
  - video-generation
  - latex
  - tikz
  - math
short_description: Programmatic whiteboard animations with 54-voice neural TTS
---

# ✍️ HandAnim — Interactive Whiteboard Animation Studio

Try **[`handanim`](https://github.com/subroy13/handanim)** directly in your browser!

- **Tab 1 — Instant Voiced Whiteboard Builder**: Type a title, a LaTeX equation, flowchart steps, and a narration script, choose from **54 built-in Kokoro-82M voices** or **256-D latent voice blends** (e.g. `blend_transatlantic`, `am_puck:0.6+bm_fable:0.4`), and render an `.mp4` with **chalk sketching audio, eraser foley, ducked background music (-14 LUFS stereo), and word-synced captions**—plus copy-pasteable **Python code** and **LaTeX Beamer / TikZ `.tex` slides**.
- **Tab 2 — Preset Showcase Switcher**: Render 1-click showcase animations (*Neural Layer Flowchart + Eraser*, *Euler's Identity Voiced Proof*, *2D Character Rig with 2-Joint IK*, *Pythagorean Theorem Proof*).

## 📦 Install Locally

```bash
pip install "handanim[voice]"
```

- **GitHub Repository**: [https://github.com/subroy13/handanim](https://github.com/subroy13/handanim)
- **Documentation**: [https://subroy13.github.io/handanim/](https://subroy13.github.io/handanim/)
- **Google Colab Playground**: [Open in Colab](https://colab.research.google.com/github/subroy13/handanim/blob/master/notebooks/handanim_colab_playground.ipynb)
