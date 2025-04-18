# ✍️ handanim

**handanim** is a lightweight Python animation library for generating whiteboard-style animations — where shapes and text are drawn progressively in a hand-drawn, sketchy fashion. Perfect for educational videos, tutorials, or data storytelling.

## 🔧 Features

- ✅ **Primitive drawing operations**: Supports drawing paths using `MOVE_TO`, `LINE_TO`, `ELLIPSE`, etc.
- ✅ **Stroke-based animation engine**: Each object is animated stroke-by-stroke over frames.
- ✅ **Layered drawing**: Animate multiple objects independently on the same scene.
- ✅ **Handwritten ellipse and shape filling**: Draws ellipses and fills them using customizable stroke patterns (e.g., hatching).
- ✅ **Frame-based scene rendering**: Define frame-by-frame drawing instructions using `OpsSet`.
- ✅ **Composable animation**: Define reusable animation components and orchestrate them using a timeline.
- ✅ **Randomized jitter**: Add natural imperfection to strokes for a human-like feel.
- 📝 **Text support (in progress)**: Handwriting-style rendering of arbitrary text using mock fonts and real TTF font parsing.
- 🎥 **Export to video (via matplotlib/FFmpeg)**: Turn frames into high-quality animations.

## 📦 Installation

```bash
pip install handanim
```

> Note: If you're using real font parsing, you may also need:

```bash
pip install fonttools freetype-py svgpathtools numpy
```

## ✏️ Basic Usage

```python
from handanim.core.animation import Scene, AnimationEvent, AnimationEventType
from handanim.primitives.polygons import NGon

scene = Scene(width = 800, height = 608)
triange = NGon(
    center = (400, 304),
    radius = 100,
    n = 3
)
event = AnimationEvent(
    triange,
    AnimationEventType.SKETCH,
    start_time = 0,
    end_time = 5
)
scene.add(event)
scene.render("triangle_anim.mp4", fps = 30)
```

---

## 🧪 Showcases

- 🎞️ Drawing shapes like triangles, circles, and ellipses
- ✒️ Filling an ellipse using hatching stroke-by-stroke
- 📖 Writing the word `"hello"` using mocked handwriting font, stroke by stroke
- ✨ Multiple object animation with frame-wise timing and overlays

## 🧠 Internals (Architecture)

- `Ops` and `OpsSet`: Describe vector drawing instructions.
- `Scene`: Collects objects and sequences them in time.
- Drawing backend: Uses `cairo` (default), can be extended for other plotting libraries.
- Handwriting: Converts strokes from mock or real fonts into draw operations.

## 🚧 TODO / Roadmap

- [ ] ✅ **Real TTF font parsing** to generate handwritten text strokes
- [ ] 🎨 Support for colors, stroke width, opacity
- [ ] ⏳ Parametric timing per stroke (e.g., fast/slow drawing)
- [ ] 🔤 Text wrapping and multiline support
- [ ] 📐 Bezier curve drawing support
- [ ] 🪄 Export to SVG animation or Lottie
- [ ] 🌐 Web demo / Playground
- [ ] 🧩 Integration with tools like Manim, Streamlit or Jupyter

## 🧑‍💻 Contributing

Contributions welcome! If you have ideas, bug reports, or features you'd love to see — open an issue or pull request.

## 📄 License

MIT License.

## ❤️ Inspiration

Inspired by:

- [3Blue1Brown's manim](https://github.com/3b1b/manim)
- [RoughJS](https://github.com/rough-stuff/rough)
- Whiteboard animation videos
- Interactive teaching tools

## ✨ Made with love by Subhrajyoty Roy
