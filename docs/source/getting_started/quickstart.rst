Quickstart Tutorial
===================

This 5-minute guide walks through the core workflow of building, previewing, and rendering a hand-drawn animation in ``handanim``.

Step 1: Create a ``Scene``
--------------------------

Every animation starts with a :class:`~handanim.core.scene.Scene`, which manages the canvas dimensions, frame rate, coordinate viewport, and timeline:

.. code-block:: python

   from handanim import Scene

   scene = Scene(
       width=1280,
       height=720,
       fps=24,
       background_color=(0.99, 0.98, 0.95),  # warm paper background
   )
   # Optional: map world coordinates 1:1 to pixel coordinates (0..1280, 0..720)
   scene.set_viewport_to_identity()

Step 2: Create Immutable ``Drawable`` Primitives
------------------------------------------------

Primitives define *what* to draw, along with their stroke, sketch, and fill styles:

.. code-block:: python

   from handanim import (
       Arrow, Circle, FillStyle, Math, RoundedRectangle, SketchStyle, StrokeStyle, Text,
   )
   from handanim.stylings.color import BLACK, BLUE, PASTEL_BLUE, PASTEL_ORANGE, RED

   sketch = SketchStyle(roughness=1.5, bowing=1.0)

   title = Text(
       "Pythagorean Identity",
       position=(640, 90),
       font_size=52,
       align="center",
       stroke_style=StrokeStyle(color=BLACK, width=3.0),
   )

   card = RoundedRectangle(
       top_left=(180, 200),
       width=420,
       height=300,
       border_radius=24,
       stroke_style=StrokeStyle(color=BLUE, width=3.5),
       sketch_style=sketch,
       fill_style=FillStyle(color=PASTEL_BLUE, opacity=0.35, hachure_gap=14),
   )

   circle = Circle(
       center=(900, 350),
       radius=140,
       stroke_style=StrokeStyle(color=RED, width=3.5),
       sketch_style=sketch,
       fill_style=FillStyle(color=PASTEL_ORANGE, opacity=0.4, fill_pattern="crosshatch"),
   )

   arrow = Arrow(
       start_point=card.anchor("right"),
       end_point=circle.anchor("left"),
       stroke_style=StrokeStyle(color=BLACK, width=3.0),
   )

   equation = Math(
       r"$\sin^2\theta + \cos^2\theta = 1$",
       font_size=48,
       stroke_style=StrokeStyle(color=BLUE, width=2.8),
   ).center_at(390, 350)

.. important::

   All ``Drawable`` objects in ``handanim`` are **immutable**. Transformation methods such as ``.translate(dx, dy)``, ``.scale(sx, sy)``, ``.rotate(angle)``, and ``.center_at(x, y)`` always return a **new** ``Drawable`` instance.

Step 3: Schedule Animations on the Timeline
-------------------------------------------

Use ``scene.add(event, drawable)`` to bind an :class:`~handanim.core.animation.AnimationEvent` to a drawable:

.. code-block:: python

   from handanim import FadeInAnimation, PopAnimation, Show, SketchAnimation

   # Instant appearance at frame 0
   scene.add(Show(0.0), title)

   # Hand-drawn progressive stroke reveal
   scene.add(SketchAnimation(start_time=0.4, duration=1.5), card)
   scene.add(FadeInAnimation(start_time=1.5, duration=0.8), equation)
   scene.add(SketchAnimation(start_time=2.0, duration=0.8), arrow)

   # Springy overshoot pop-in reveal
   scene.add(PopAnimation(start_time=2.6, duration=0.6), circle)

Step 4: Render Video or Inspect Keyframes
-----------------------------------------

Render to an ``.mp4`` video (or ``.gif``), or export instant SVG/PDF snapshots to inspect layout before a full render:

.. code-block:: python

   # Fast SVG snapshot at t = 3.5 seconds
   scene.render_snapshot("preview.svg", frame_in_seconds=3.5)

   # Render full MP4 with background music and chalk drawing sounds
   scene.render(
       "quickstart.mp4",
       max_length=4.5,
       background_music="marimba",
       sketch_sound=True,
   )

