"""
hershey_math.py — showcase for Bug 2 fix and F1 extended operator coverage.

Renders six expressions using the Hershey single-stroke font to verify:
  - Bug 2 fix: Latin letters (x, a–z), digits, and NFKD-normalised math-italic
    variants now look up in rowmans (not in mathlow, which encodes Greek).
  - F1: composed glyphs for ±, √, ≤, ≥, ≠, ≈, ∞, →, ∑, ∫, ∂, ∀, ∃, ∈, ⊂.
"""
import os

from handanim.animations.sketch import SketchAnimation
from handanim.core import StrokeStyle
from handanim.core.scene import Scene
from handanim.primitives.math import Math
from handanim.stylings.color import BLACK, BLUE, GREEN, RED


def main():
    scene = Scene(width=1400, height=1000)

    FONT = "hershey_mathlow"
    SW = 2  # stroke width

    expressions = [
        # 1. Quadratic formula — tests: Latin x, Greek α β γ, ±, √, fraction bar
        (
            r"$x = \frac{-\alpha \pm \sqrt{\beta^2 - 4\gamma}}{2}$",
            BLUE,
        ),
        # 2. Inequalities — tests: ≤, ≥, ≠, ≈
        (
            r"$a \leq b, \quad c \geq d, \quad e \neq f, \quad g \approx h$",
            GREEN,
        ),
        # 3. Limits and infinity — tests: →, ∞, Latin lim f x L
        (
            r"$\lim_{x \rightarrow \infty} f(x) = L$",
            BLACK,
        ),
        # 4. Set theory — tests: ∀, ∃, ∈, ⊂, composed symbols
        (
            r"$\forall x \in A, \quad \exists y \in B : x \leq y$",
            RED,
        ),
        # 5. Summation and integral — tests: ∑, ∫, ∂ (fraction bar from rect system)
        (
            r"$\sum_{k=1}^{n} k^2 = \int_{0}^{n} x \, dx$",
            BLUE,
        ),
        # 6. Euler identity — tests: e, i, π, +, =, 0, 1 all via rowmans fallback
        (
            r"$e^{i\pi} + 1 = 0$",
            GREEN,
        ),
    ]

    y_start = 120
    y_step = 145

    for idx, (expr, color) in enumerate(expressions):
        math_obj = Math(
            tex_expression=expr,
            position=(80, y_start + idx * y_step),
            font_size=44,
            font_name=FONT,
            stroke_style=StrokeStyle(color=color, width=SW),
        )
        scene.add(
            SketchAnimation(start_time=idx * 1.5, duration=1.5),
            math_obj,
        )

    output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "hershey_equation.mp4")

    print(f"Rendering → {output_path}")
    scene.render(output_path)
    print("Done.")


if __name__ == "__main__":
    main()
