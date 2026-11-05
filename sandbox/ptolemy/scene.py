"""A 58-second portrait proof. Run from the repository root.

    .venv/bin/python sandbox/ptolemy/scene.py --preview
    .venv/bin/python sandbox/ptolemy/scene.py

The saved scene is self-contained; no model calls or network access are used.
"""

import random
import sys
from pathlib import Path

import numpy as np

from handanim import (
    Circle,
    FadeOutAnimation,
    FillStyle,
    Line,
    LinearPath,
    Math,
    Polygon,
    Scene,
    SketchAnimation,
    SketchStyle,
    StrokeStyle,
    Text,
)
from handanim.core.viewport import Viewport

# Main settings: positions are world coordinates, independent of render size.
PREVIEW = "--preview" in sys.argv
WIDTH, HEIGHT = (360, 640) if PREVIEW else (1080, 1920)
FPS = 30
DURATION = 58
SEED = 20261104
OUTPUT = Path("sandbox/ptolemy/output")
INK = (0.12, 0.17, 0.22)
MUTED = (0.40, 0.45, 0.48)
PALE = (0.78, 0.81, 0.82)
BLUE = (0.04, 0.39, 0.72)
ORANGE = (0.82, 0.30, 0.09)
GREEN = (0.08, 0.49, 0.34)
SKETCH = SketchStyle(roughness=1.1, bowing=0.35, max_random_offset=1.25)
LETTERING = SketchStyle(roughness=0.18, disable_font_mixture=True)

random.seed(SEED)
np.random.seed(SEED)
scene = Scene(
    width=WIDTH,
    height=HEIGHT,
    fps=FPS,
    viewport=Viewport((0, 562.5), (0, 1000), WIDTH, HEIGHT, margin=0),
)


def show(obj, start, duration=0.6, end=None):
    """Draw every new object stroke by stroke; fade only when clearing a beat."""
    scene.add(SketchAnimation(start_time=start, duration=max(duration, 0.45)), obj)
    if end is not None:
        scene.add(FadeOutAnimation(start_time=end - 0.25, duration=0.25), obj)
    return obj


def text(name, words, y, size=24, color=INK, x=281.25):
    obj = Text(
        words,
        (0, 0),
        font_size=size,
        id=name,
        stroke_style=StrokeStyle(color=color, width=1.15),
        sketch_style=LETTERING,
    )
    bbox = obj.get_bbox()
    # Position by actual ink bounds, rather than font advance widths.
    placed = obj.translate(x - bbox.center[0], y - bbox.center[1])
    placed.id = name
    return placed


def formula(name, expression, y, size=28, color=INK):
    obj = Math(
        expression,
        (0, 0),
        font_size=size,
        font_name="hershey_rowmans",
        id=name,
        stroke_style=StrokeStyle(color=color, width=1.15),
        sketch_style=LETTERING,
    )
    bbox = obj.get_bbox()
    placed = obj.translate(281.25 - bbox.center[0], y - bbox.center[1])
    placed.id = name
    return placed


def segment(name, p, q, color=INK, width=1.6):
    return Line(p, q, id=name, stroke_style=StrokeStyle(color=color, width=width), sketch_style=SKETCH)


def angle_mark(name, vertex, p, q, radius, color, double=False):
    """The short arc between two rays; a second arc distinguishes AA pairs."""
    a = np.arctan2(*(p - vertex)[::-1])
    b = np.arctan2(*(q - vertex)[::-1])
    sweep = (b - a + np.pi) % (2 * np.pi) - np.pi
    marks = []
    for i in range(2 if double else 1):
        theta = np.linspace(a, a + sweep, 20)
        points = vertex + (radius + i * 4) * np.column_stack([np.cos(theta), np.sin(theta)])
        marks.append(
            LinearPath(
                points.tolist(),
                id=f"{name}_{i}",
                sketch_style=SKETCH,
                stroke_style=StrokeStyle(color=color, width=1.7),
            )
        )
    return marks


def triangle(name, points, color):
    return Polygon(
        [p.tolist() for p in points],
        id=name,
        sketch_style=SKETCH,
        stroke_style=StrokeStyle(color=color, width=2.3),
        fill_style=FillStyle(color=color, opacity=0.16, fill_pattern="hachure", hachure_gap=11),
    )


def caption(name, lines, start, end):
    cursor = start
    for i, words in enumerate(lines):
        # Write the lines in order, with enough time to see the pen strokes.
        duration = max(0.55, min(1.25, len(words) * 0.027))
        show(text(f"{name}_{i}", words, 865 + i * 33, size=24), cursor, duration, end)
        cursor += duration + 0.08


def heading(words, start, end):
    show(text(f"step_{start}", words, 163, size=18, color=MUTED), start, 1.1, end)


# Geometry: A, B, C, D occur in that order around the circle.
CENTER = np.array([281.25, 365.0])
R = 178.0
A, B, C, D = [CENTER + R * np.array([np.cos(t), np.sin(t)]) for t in np.deg2rad([230, 320, 60, 155])]

# Construct BK by rotating BA through the signed angle DBC, then intersect AC.
# No use of Ptolemy's product identity is needed to locate K.
u, v = D - B, C - B
theta = np.arctan2(u[0] * v[1] - u[1] * v[0], np.dot(u, v))
c, s = np.cos(theta), np.sin(theta)
ray = np.array([[c, -s], [s, c]]) @ (A - B)
fraction, _ = np.linalg.solve(np.column_stack([C - A, -ray]), B - A)
K = A + fraction * (C - A)


# 0–11 s: the theorem and its hypotheses.
show(text("eyebrow", "A VISUAL PROOF", 40, 16, MUTED), 0, 0.7)
show(text("title", "Ptolemy's theorem", 84, 42), 0.2, 1.6)
show(text("subtitle", "One extra line. Two similar pairs.", 123, 21, MUTED), 1.7, 1)
heading("01 / FOUR POINTS, ONE CIRCLE", 0.5, 11.5)
circumcircle = Circle(
    CENTER,
    R,
    id="circumcircle",
    sketch_style=SKETCH,
    stroke_style=StrokeStyle(color=PALE, width=1.2),
)
show(circumcircle, 0.8, 1.8)
for i, (p, q) in enumerate([(A, B), (B, C), (C, D), (D, A)]):
    show(segment(f"side_{i}", p, q), 2.5 + i * 0.4, 0.5)
for name, p, offset in [
    ("A", A, (-18, -17)),
    ("B", B, (21, -12)),
    ("C", C, (14, 25)),
    ("D", D, (-21, 8)),
]:
    show(text(f"vertex_{name}", name, p[1] + offset[1], 27, x=p[0] + offset[0]), 3.7, 0.5)
show(segment("diagonal_AC", A, C, MUTED, 1.3), 6, 1)
show(segment("diagonal_BD", B, D, MUTED, 1.3), 7, 1)
show(text("claim_intro", "Diagonals and opposite sides", 619, 23, MUTED), 5.2, 0.5, 11.5)
show(formula("claim", r"$AC\cdot BD = AB\cdot CD + BC\cdot AD$", 690, 25), 7.6, 1.8, 11.5)
caption("hook", ["A circle hides a beautiful identity."], 0.5, 4.3)
caption("hypothesis", ["Four distinct points, in order,", "on the same circle."], 4.4, 8.1)
caption("statement", ["Multiply the diagonals.", "Can opposite sides give the same result?"], 8.2, 11.5)


# 11.5–19.5 s: a single auxiliary line defines the two similar pairs.
heading("02 / THE CLEVER EXTRA LINE", 11.5, 19.5)
show(segment("construction_BK", B, K, INK, 1.7), 11.6, 1.2)
show(Circle(K, 3, id="point_K", stroke_style=StrokeStyle(color=INK, width=2), sketch_style=SKETCH), 12.5, 0.3)
show(text("vertex_K", "K", K[1] + 26, 25, x=K[0] - 5), 12.8, 0.4)
for arc in angle_mark("chosen_ABK", B, A, K, 29, BLUE) + angle_mark("chosen_DBC", B, D, C, 29, BLUE):
    show(arc, 13.1, 0.7, 19.5)
show(text("construction_label", "Choose K on AC so that", 625, 25), 12, 0.7, 19.5)
show(formula("construction_angles", r"$\angle ABK = \angle DBC$", 688, 30, BLUE), 13.2, 1, 19.5)
show(text("construction_note", "The blue angles match by construction.", 748, 20, MUTED), 14.5, 0.7, 19.5)
caption("choose", ["One extra line: BK.", "Make these two angles equal."], 11.6, 19.5)


# 19.5–32 s: ABK ~ DBC, with explicit AA evidence and a length ratio.
heading("03 / FIRST SIMILAR PAIR", 19.5, 32)
for name, points in [("triangle_ABK", [A, B, K]), ("triangle_DBC", [D, B, C])]:
    show(triangle(name, points, BLUE), 19.6, 0.9, 32)
for arc in (
    angle_mark("first_B1", B, A, K, 29, BLUE)
    + angle_mark("first_B2", B, D, C, 29, BLUE)
    + angle_mark("first_A", A, B, K, 24, BLUE, double=True)
    + angle_mark("first_D", D, B, C, 24, BLUE, double=True)
):
    show(arc, 20.4, 0.5, 32)
show(formula("similar_blue", r"$\triangle ABK \sim \triangle DBC$", 615, 28, BLUE), 20.3, 1, 32)
show(text("blue_reason", "Same chord BC gives the double arcs.", 660, 20, MUTED), 21.5, 0.5, 27)
show(formula("ratio_blue", r"$\frac{AK}{CD}=\frac{AB}{BD}$", 716, 28, BLUE), 23.4, 1.1, 27)
show(formula("product_blue", r"$BD\cdot AK = AB\cdot CD$", 754, 31, BLUE), 27.2, 1.1, 45.5)
caption("first_AA", ["Same chord, equal angles.", "Two angles match: the triangles are similar."], 19.6, 26.8)
caption("first_product", ["Matching sides give", "the first product identity."], 27, 32)


# 32–45.5 s: the complementary angles at B and the chord AB give a second AA pair.
heading("04 / SECOND SIMILAR PAIR", 32, 45.5)
for name, points in [("triangle_BCK", [B, C, K]), ("triangle_BDA", [B, D, A])]:
    show(triangle(name, points, ORANGE), 32.1, 0.9, 45.5)
for arc in (
    angle_mark("second_B1", B, C, K, 40, ORANGE)
    + angle_mark("second_B2", B, D, A, 40, ORANGE)
    + angle_mark("second_C", C, B, K, 24, ORANGE, double=True)
    + angle_mark("second_D", D, B, A, 24, ORANGE, double=True)
):
    show(arc, 32.8, 0.6, 45.5)
show(formula("similar_orange", r"$\triangle BCK \sim \triangle BDA$", 615, 28, ORANGE), 32.5, 1, 45.5)
show(text("orange_reason", "Remaining angles at B match too.", 658, 20, MUTED), 33.6, 0.5, 39.8)
show(text("orange_chord", "Double arcs stand on chord AB.", 689, 19, MUTED), 34.4, 0.5, 39.8)
show(formula("ratio_orange", r"$\frac{KC}{AD}=\frac{BC}{BD}$", 715, 27, ORANGE), 36.2, 1, 39.8)
# Keep the blue identity as a reminder; place the second one below it.
show(formula("product_orange", r"$BD\cdot KC = BC\cdot AD$", 802, 31, ORANGE), 40, 1.2, 45.5)
caption("second_AA", ["The remaining angles at B match.", "The circle gives another similar pair."], 32.1, 39.8)
caption("second_product", ["Matching sides give", "the second product identity."], 40, 45.5)


# 45.5–58 s: reassemble AC and add the two identities.
heading("05 / ADD THE TWO PIECES", 45.5, 58)
show(segment("piece_AK", A, K, BLUE, 3.2), 45.6, 0.8)
show(segment("piece_KC", K, C, ORANGE, 3.2), 46.3, 0.8)
show(text("piece_AK_label", "AK", 310, 22, BLUE, x=197), 46, 0.5)
show(text("piece_KC_label", "KC", 476, 22, ORANGE, x=294), 46.6, 0.5)
show(formula("add_blue", r"$BD\cdot AK = AB\cdot CD$", 610, 29, BLUE), 45.6, 0.6, 50)
show(formula("add_orange", r"$BD\cdot KC = BC\cdot AD$", 656, 29, ORANGE), 46.1, 0.6, 50)
show(segment("addition_rule", (87, 690), (475, 690), PALE, 1), 47, 0.5, 50)
show(formula("sum", r"$BD(AK+KC)=AB\cdot CD+BC\cdot AD$", 735, 24), 47.4, 1.1, 50)
show(formula("whole_diagonal", r"$AK+KC=AC$", 628, 32, GREEN), 50, 1)
show(formula("result", r"$AC\cdot BD = AB\cdot CD + BC\cdot AD$", 711, 27, GREEN), 51, 1.6)
show(
    LinearPath(
        [(58, 677), (58, 750), (504, 750), (504, 677)],
        id="result_box",
        stroke_style=StrokeStyle(color=GREEN, width=1.5),
        sketch_style=SKETCH,
    ),
    52.4,
    1.1,
)
show(text("closing", "Ptolemy, proved.", 794, 29, GREEN), 54, 0.9)
caption("add", ["Add the two identities."], 45.6, 50)
caption("finish", ["AK + KC is the whole diagonal AC.", "And that is Ptolemy's theorem."], 50, 58)
for i, start in enumerate([0.1, 11.5, 19.5, 32, 45.5]):
    x = 66 + i * 88
    show(segment(f"chapter_track_{i}", (x, 944), (x + 78, 944), PALE, 1), 0, 0.45)
    show(segment(f"chapter_done_{i}", (x, 944), (x + 78, 944), GREEN, 1.6), start, 0.4)


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    name = "preview" if PREVIEW else "silent"
    scene.render(str(OUTPUT / f"{name}.mp4"), max_length=DURATION)
