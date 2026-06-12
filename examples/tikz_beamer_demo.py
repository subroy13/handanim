"""Demo: export a hand-drawn animation as native TikZ inside a Beamer slide deck.

Produces:
  examples/output/tikz_beamer/slides.tex   — compilable with pdflatex
  examples/output/tikz_standalone.tex       — single-frame standalone TikZ

Usage:
  poetry run python examples/tikz_beamer_demo.py
  cd examples/output/tikz_beamer && pdflatex slides.tex
  cd examples/output && pdflatex tikz_standalone.tex
"""

import os

from handanim.animations import FadeInAnimation, SketchAnimation
from handanim.core import FillStyle, Scene, SketchStyle, StrokeStyle
from handanim.primitives import Circle, Line, NGon, Rectangle, Text
from handanim.stylings.color import BLACK, BLUE, RED

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

scene = Scene(width=1920, height=1088)

title = Text(
    text="TikZ Export Demo",
    position=(400, 100),
    font_size=120,
    stroke_style=StrokeStyle(color=BLUE, width=2),
)
scene.add(SketchAnimation(duration=2), drawable=title)

triangle = NGon(
    center=(500, 500),
    radius=200,
    n=3,
    stroke_style=StrokeStyle(color=RED, width=2),
    fill_style=FillStyle(color=(1.0, 0.9, 0.85)),
    sketch_style=SketchStyle(roughness=2),
)
scene.add(SketchAnimation(start_time=2, duration=2), drawable=triangle)

rect = Rectangle(
    top_left=(900, 350),
    width=350,
    height=250,
    stroke_style=StrokeStyle(color=BLACK, width=2),
    fill_style=FillStyle(color=(0.85, 0.92, 1.0)),
    sketch_style=SketchStyle(roughness=1.5),
)
scene.add(SketchAnimation(start_time=4, duration=2), drawable=rect)

connector = Line(
    start=(700, 500),
    end=(900, 475),
    stroke_style=StrokeStyle(color=BLACK, width=1.5),
)
scene.add(SketchAnimation(start_time=6, duration=1), drawable=connector)

label = Text(
    text="Native LaTeX!",
    position=(950, 700),
    font_size=60,
    stroke_style=StrokeStyle(color=BLUE, width=1.5),
)
scene.add(SketchAnimation(start_time=7, duration=1.5), drawable=label)

# --- TikZ beamer export (native drawing commands, no PDF images) ---
beamer_dir = os.path.join(OUTPUT_DIR, "tikz_beamer")
tex_path = scene.export_beamer(
    beamer_dir,
    n_frames=6,
    backend="tikz",
    title="Handanim TikZ Demo",
)
print(f"Beamer slides: {tex_path}")
print(f"  Compile with: cd {beamer_dir} && pdflatex slides.tex")

# --- Standalone TikZ frame (final state) ---
standalone_path = os.path.join(OUTPUT_DIR, "tikz_standalone.tex")
scene.render_tikz(standalone_path, time=8.5)
print(f"Standalone frame: {standalone_path}")
print(f"  Compile with: pdflatex {standalone_path}")

# --- For comparison: cairo backend ---
cairo_dir = os.path.join(OUTPUT_DIR, "cairo_beamer")
cairo_tex = scene.export_beamer(
    cairo_dir,
    n_frames=6,
    backend="cairo",
    title="Handanim Cairo Demo",
)
print(f"Cairo slides (for comparison): {cairo_tex}")
