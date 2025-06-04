# ✍️ handanim

[![Build and Deploy Docs](https://github.com/subroy13/handanim/actions/workflows/docs.yml/badge.svg)](https://github.com/subroy13/handanim/actions/workflows/docs.yml)

> A Python library to create whiteboard-style, hand-drawn animations for educational videos, tutorials or data storytelling.

**handanim** lets you programmatically animate hand-drawn diagrams, geometric shapes, handwritten text, and visual explanations — ideal for online teaching, explainer videos, and mathematical illustrations.

> ⭐️ If you like this project, please consider starring it on [GitHub](https://github.com/subroy13/handanim)! Your support helps the project grow.

## ✨ Features

- Draw and animate shapes (lines, ellipses, polygons) with a hand-drawn feel
- Fill objects with sketch-style strokes (hatching, scribbles)
- Animate handwritten text using custom fonts
- Export vector images (SVG) or videos (MP4).
- Intuitive Python API for creating scenes and timelines

## 📷 Example Output

<p align="center">
  <img src="./examples/output/pythagoras.gif" width="500">
</p>

_(Example animation of a Pythagoras Theorem — see `examples/pythagoras.py`)_

## 🚀 Quickstart

```bash
# Install dependencies (requires Python 3.13+)
poetry install

# Run example animation
poetry run python examples/pythagoras.py
```

### ✏️ Basic Usage

```python
from handanim.core import Scene
from handanim.animations import SketchAnimation
from handanim.primitives import NGon

scene = Scene(width = 800, height = 608)
triangle = NGon(
    center = (400, 304),
    radius = 100,
    n = 3
)
scene.add(SketchAnimation(start_time = 0, end_time = 5), drawable = triangle)
scene.render("triangle_anim.mp4", fps = 30)
```

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

We welcome contributions!

You can help by:

- Adding new animation primitives (e.g., Bezier curves, arrows)
- Improving rendering quality and styles, caching and optimization.
- Writing example scripts or tutorials
- Reporting bugs and suggesting features

Please see `CONTRIBUTING.md` (coming soon) for guidelines.

## ❤️ Inspiration

Inspired by:

- [3Blue1Brown's manim](https://github.com/3b1b/manim)
- [RoughJS](https://github.com/rough-stuff/rough)
- Whiteboard animation videos
- Interactive teaching tools

⭐️ **Support handanim!**

If you find this project useful, please give it a star on [GitHub](https://github.com/subroy13/handanim).

It motivates me to keep improving it and helps others discover it!

> ✨ Made with love by Subhrajyoty Roy

---

## 🧠 Internals (Architecture)

1. `core`: Core capabilities.

   - `drawable.py`: Defines the structure that can be drawn.
   - `styles.py`: Defines the styling oriented options that can be configured.
   - `draw_ops.py`: Defines the opsets, the basic structure that is used to draw. Along with the rendering logic for the opsset into the cairo context.
   - `utils.py`: Some utility functions that does not fit anywhere else
   - `animation.py`: Defines the animation structures.
   - `scene.py`: Defines the scene, which is the main entry point for the user.

2. Models.
   - `Ops` and `OpsSet`: Describe vector drawing instructions.
   - `Scene`: Collects objects and sequences them in time.
   - Handwriting: Converts strokes from mock or real fonts into draw operations.

## 💡 Features Coming soon

1. Arrows
2. Flowcharts diagrams
3. Importing images and videos into the scene.
4. Autofitting content based on the size of textbox
5. Showcasing tabular data with headers.
