Theme 1: Mathematical Proofs & Geometry
=======================================

``handanim`` makes it effortless to build step-by-step geometric proofs, algebraic derivations, and calculus explainers with authentic hand-sketched strokes, hachure fills, glowing pen tips, and both LaTeX and single-stroke Hershey math fonts.

.. tip::

   To regenerate any of the animations on this page locally:

   .. code-block:: bash

      poetry run python docs/source/gallery/build_gallery.py --only pythagoras
      poetry run python docs/source/gallery/build_gallery.py --only a_plus_b_square
      poetry run python docs/source/gallery/build_gallery.py --only distributive_property
      poetry run python docs/source/gallery/build_gallery.py --only hershey_math

----

Tutorial 1.1: Visual Introduction to the Pythagorean Theorem
------------------------------------------------------------

**Use Case:** Introduce a geometric theorem by sketching a title with a glowing pen tip (`glow_dot_hint`), wiping the board clean with :class:`~handanim.primitives.eraser.Eraser`, drawing a hachure-filled right triangle (:class:`~handanim.primitives.polygons.Polygon`), labeling its sides with a :class:`~handanim.core.drawable.DrawableGroup`, and writing the equation :math:`a^2 + b^2 = c^2` using :class:`~handanim.primitives.math.Math`.

.. image:: /_static/gallery/pythagoras.gif
   :width: 640px
   :align: center
   :alt: Pythagoras Theorem Animation

Complete Tutorial Code
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from handanim.animations import SketchAnimation
   from handanim.core import DrawableGroup, FillStyle, Scene, SketchStyle, StrokeStyle
   from handanim.primitives import Eraser, Math, Polygon, Text
   from handanim.stylings.color import BLACK, BLUE, ERASER_HINT_COLOR, RED

   scene = Scene(width=1920, height=1088)

   # 1. Sketch the title with a glowing blue dot at the pen tip
   title_text = Text(
       text="Pythagoras' Theorem",
       position=(300, 500),
       font_size=192,
       stroke_style=StrokeStyle(color=BLUE, width=2),
       glow_dot_hint={"color": BLUE, "radius": 5},
   )
   scene.add(SketchAnimation(start_time=0.0, duration=3.0), drawable=title_text)

   # 2. Wipe the title off the board with an Eraser
   eraser = Eraser(
       objects_to_erase=[title_text],
       drawable_cache=scene.drawable_cache,
       glow_dot_hint={"color": ERASER_HINT_COLOR, "radius": 10},
   )
   scene.add(SketchAnimation(start_time=3.5, duration=1.5), drawable=eraser)

   # 3. Sketch the right-angled triangle with diagonal red hachure shading
   right_triangle = Polygon(
       points=[(500, 500), (500, 700), (900, 700)],
       stroke_style=StrokeStyle(color=BLACK, width=2),
       sketch_style=SketchStyle(roughness=5),
       fill_style=FillStyle(color=RED, hachure_gap=10),
   )
   scene.add(SketchAnimation(start_time=6.0, duration=3.0), drawable=right_triangle)

   # 4. Sketch the side labels (a, b, c) sequentially as a group
   line_labels = [("a", (450, 600)), ("b", (700, 800)), ("c", (700, 550))]
   label_group = DrawableGroup(
       elements=[Text(text=label, position=pos, font_size=96) for label, pos in line_labels]
   )
   scene.add(SketchAnimation(start_time=8.0, duration=2.0), drawable=label_group)

   # 5. Write the Pythagorean identity
   pyth_form = Math(
       tex_expression=r"$a^2 + b^2 = c^2$",
       position=(900, 300),
       font_size=128,
       stroke_style=StrokeStyle(color=BLUE, width=2),
       font_name="feasibly",
   )
   scene.add(SketchAnimation(start_time=10.0, duration=3.0), drawable=pyth_form)

   scene.render("pythagoras.gif", max_length=15)

----

Tutorial 1.2: Geometric Proof of :math:`(a + b)^2 = a^2 + 2ab + b^2`
--------------------------------------------------------------------

**Use Case:** Visually prove the binomial expansion by partitioning a square of side :math:`a + b` into two smaller squares (:math:`a^2` and :math:`b^2`) and two rectangles (:math:`ab`), using :class:`~handanim.core.animation.CompositeAnimationEvent` to chain :class:`~handanim.animations.sketch.SketchAnimation`, :class:`~handanim.animations.zoom.ZoomOutAnimation`, and :class:`~handanim.animations.translate.TranslateToAnimation` as terms fly into the top equation.

.. image:: /_static/gallery/a_plus_b_square.gif
   :width: 640px
   :align: center
   :alt: (a+b)^2 Visual Proof

Complete Tutorial Code
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from handanim.animations import (
       FadeInAnimation, FadeOutAnimation, SketchAnimation, TranslateToAnimation, ZoomOutAnimation,
   )
   from handanim.core import (
       CompositeAnimationEvent, DrawableGroup, FillStyle, Scene, SketchStyle, StrokeStyle,
   )
   from handanim.primitives import Line, Math, Rectangle, Square
   from handanim.stylings.color import BLACK, BLUE, ORANGE, RED

   scene = Scene(width=1920, height=1088)
   FONT_NAME = "feasibly"
   VALUE_A, VALUE_B = 100, 200
   A_PLUS_B = VALUE_A + VALUE_B
   sq_top_left = (300, 500)

   # 1. Intro prompt: sketch and fade out "(a + b)^2 = ?"
   title_text = Math(
       tex_expression=r"$(a + b)^2 = ?$",
       position=sq_top_left,
       font_size=192,
       stroke_style=StrokeStyle(color=BLUE, width=2),
       glow_dot_hint={"color": BLUE, "radius": 5},
       font_name=FONT_NAME,
   )
   scene.add(
       CompositeAnimationEvent(
           events=[SketchAnimation(duration=1.0), FadeOutAnimation(start_time=1.0, duration=2.0)]
       ),
       drawable=title_text,
   )

   # 2. Draw outer (a + b) square and animate side labels into the top header
   a_plus_b_sq = Square(
       top_left=sq_top_left,
       side_length=A_PLUS_B,
       stroke_style=StrokeStyle(color=BLACK, width=2),
       fill_style=FillStyle(color=BLUE, hachure_gap=10),
       sketch_style=SketchStyle(roughness=3),
   )
   scene.add(SketchAnimation(start_time=3.5, duration=3.0), drawable=a_plus_b_sq)

   a_plus_b_label_group = DrawableGroup(
       elements=[
           Math(r"$a + b$", position=pos, font_size=60, font_name=FONT_NAME)
           for pos in [
               (sq_top_left[0] + A_PLUS_B / 2, sq_top_left[1] - 100),
               (sq_top_left[0] + A_PLUS_B + 50, sq_top_left[1] + A_PLUS_B / 2),
           ]
       ]
   )
   a_plus_b_sq_label = Math(r"$(a + b)^2$", position=(600, 200), font_size=96, font_name=FONT_NAME)

   scene.add(
       CompositeAnimationEvent(
           events=[
               SketchAnimation(start_time=3.5, duration=1.0),
               ZoomOutAnimation(start_time=4.5, duration=2.0),
               TranslateToAnimation(start_time=4.5, duration=2.0, data={"point": a_plus_b_sq_label.position}),
           ]
       ),
       drawable=a_plus_b_label_group,
   )
   scene.add(FadeInAnimation(start_time=6.5, duration=1.0), drawable=a_plus_b_sq_label)

   # 3. Partition the square with horizontal and vertical split lines
   vert_line = Line(
       start=(sq_top_left[0] + VALUE_A, sq_top_left[1]),
       end=(sq_top_left[0] + VALUE_A, sq_top_left[1] + A_PLUS_B),
   )
   horiz_line = Line(
       start=(sq_top_left[0], sq_top_left[1] + VALUE_A),
       end=(sq_top_left[0] + A_PLUS_B, sq_top_left[1] + VALUE_A),
   )
   scene.add(SketchAnimation(start_time=7.0, duration=1.0), drawable=DrawableGroup(elements=[vert_line, horiz_line]))

   # 4. Highlight sub-regions: a^2, b^2, and two ab rectangles
   a_sq = Square(
       top_left=sq_top_left,
       side_length=VALUE_A,
       fill_style=FillStyle(color=RED, hachure_gap=10, hachure_angle=135),
   )
   b_sq = Square(
       top_left=(sq_top_left[0] + VALUE_A, sq_top_left[1] + VALUE_A),
       side_length=VALUE_B,
       fill_style=FillStyle(color=RED, hachure_gap=10, hachure_angle=135),
   )
   ab_rect1 = Rectangle(
       top_left=(sq_top_left[0] + VALUE_A, sq_top_left[1]),
       width=VALUE_B,
       height=VALUE_A,
       fill_style=FillStyle(color=ORANGE, hachure_gap=10, hachure_angle=135),
   )
   ab_rect2 = Rectangle(
       top_left=(sq_top_left[0], sq_top_left[1] + VALUE_A),
       width=VALUE_A,
       height=VALUE_B,
       fill_style=FillStyle(color=ORANGE, hachure_gap=10, hachure_angle=135),
   )
   scene.add(SketchAnimation(start_time=8.5, duration=1.5), drawable=a_sq)
   scene.add(SketchAnimation(start_time=10.2, duration=1.5), drawable=b_sq)
   scene.add(SketchAnimation(start_time=12.0, duration=1.5), drawable=ab_rect1)
   scene.add(SketchAnimation(start_time=13.7, duration=1.5), drawable=ab_rect2)

   scene.render("a_plus_b_square.gif", max_length=16)

----

Tutorial 1.3: Distributive Property with SVG Illustration
---------------------------------------------------------

**Use Case:** Combine an external SVG character (:class:`~handanim.primitives.vector_svg.VectorSVG`) with geometric area blocks (`ab` and `ac`) that slide together via :class:`~handanim.animations.translate.TranslateToAnimation` to visually demonstrate :math:`a(b + c) = ab + ac`.

.. image:: /_static/gallery/distributive_property.gif
   :width: 640px
   :align: center
   :alt: Distributive Property Animation

Complete Tutorial Code
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from handanim.animations import FadeInAnimation, SketchAnimation, TranslateToAnimation
   from handanim.core import FillStyle, Scene, StrokeStyle
   from handanim.primitives import Math, Rectangle, Text, VectorSVG
   from handanim.stylings.color import BLACK, BLUE, ORANGE

   scene = Scene(width=1920, height=1080)

   # 1. Load an SVG character and scale it using immutable transformation
   operator = VectorSVG.from_svg_file(
       "assets/professor.svg",
       position=(1500, 700),
       glow_dot_hint={"color": BLUE, "radius": 5},
   ).scale(0.5, 0.5)
   scene.add(SketchAnimation(start_time=0.5, duration=2.0), drawable=operator)

   title_text = Text(
       text="Distributive Property",
       position=(500, 120),
       font_size=120,
       stroke_style=StrokeStyle(color=BLUE, width=2),
   )
   scene.add(SketchAnimation(start_time=0.5, duration=2.0), drawable=title_text)

   # 2. Sketch two rectangles of height 'a' and widths 'b' and 'c'
   rect_ab = Rectangle(
       top_left=(400, 500),
       width=200,
       height=150,
       stroke_style=StrokeStyle(color=BLACK, width=2),
       fill_style=FillStyle(color=BLUE, hachure_gap=10),
   )
   rect_ac = Rectangle(
       top_left=(1200, 500),
       width=300,
       height=150,
       stroke_style=StrokeStyle(color=BLACK, width=2),
       fill_style=FillStyle(color=ORANGE, hachure_gap=10),
   )
   scene.add(SketchAnimation(start_time=2.5, duration=1.5), drawable=rect_ab)
   scene.add(SketchAnimation(start_time=3.0, duration=1.5), drawable=rect_ac)

   # 3. Fade in side labels and slide the second rectangle to join the first
   label_a = Math(r"$a$", position=(310, 525), font_size=70)
   label_b = Math(r"$b$", position=(470, 400), font_size=70)
   label_c = Math(r"$c$", position=(1350, 400), font_size=70)
   scene.add(FadeInAnimation(start_time=4.0, duration=0.5), drawable=label_a)
   scene.add(FadeInAnimation(start_time=4.2, duration=0.5), drawable=label_b)
   scene.add(FadeInAnimation(start_time=4.4, duration=0.5), drawable=label_c)

   scene.add(TranslateToAnimation(start_time=7.0, duration=2.0, data={"point": (750, 575)}), drawable=rect_ac)
   scene.add(TranslateToAnimation(start_time=7.0, duration=2.0, data={"point": (750, 450)}), drawable=label_c)

   # 4. Sketch the final algebraic identity
   final_formula = Math(
       tex_expression=r"$a(b + c) = ab + ac$",
       position=(400, 200),
       font_size=110,
       stroke_style=StrokeStyle(color=BLACK, width=3),
       font_name="feasibly",
   )
   scene.add(SketchAnimation(start_time=9.5, duration=2.0), drawable=final_formula)

   scene.render("distributive_property.gif", max_length=12)

----

Tutorial 1.4: Single-Stroke Hershey Math & Calculus Board
---------------------------------------------------------

**Use Case:** Render multi-line symbolic mathematics (quadratic formula, inequalities, limits, set theory quantifiers, summations, integrals, and Euler's identity) using single-stroke Hershey fonts (``font_name="hershey_mathlow"``) so every symbol is drawn as a true single-line pen trajectory rather than a hollow glyph outline.

.. raw:: html

   <div class="tutorial-media">
     <video controls loop muted playsinline width="620" src="../_static/gallery/hershey_equation.mp4"></video>
     <p><em>Single-stroke Hershey math rendering across 6 calculus &amp; algebra formulas.</em></p>
   </div>

Complete Tutorial Code
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from handanim.animations import SketchAnimation
   from handanim.core import Scene, StrokeStyle
   from handanim.primitives import Math
   from handanim.stylings.color import BLACK, BLUE, GREEN, RED

   scene = Scene(width=1264, height=960)

   expressions = [
       (r"$x = \frac{-\alpha \pm \sqrt{\beta^2 - 4\gamma}}{2}$", BLUE),
       (r"$a \leq b, \quad c \geq d, \quad e \neq f, \quad g \approx h$", GREEN),
       (r"$\lim_{x \rightarrow \infty} f(x) = L$", BLACK),
       (r"$\forall x \in A, \quad \exists y \in B : x \leq y$", RED),
       (r"$\sum_{k=1}^{n} k^2 = \int_{0}^{n} x \, dx$", BLUE),
       (r"$e^{i\pi} + 1 = 0$", GREEN),
   ]

   for idx, (expr, color) in enumerate(expressions):
       math_obj = Math(
           tex_expression=expr,
           position=(80, 120 + idx * 145),
           font_size=44,
           font_name="hershey_mathlow",
           stroke_style=StrokeStyle(color=color, width=2),
       )
       scene.add(SketchAnimation(start_time=idx * 1.5, duration=1.5), math_obj)

   scene.render("hershey_equation.mp4")
