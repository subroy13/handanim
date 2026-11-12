Styling, Sketch Aesthetics & Fills
==================================

``handanim`` separates visual styling into three composable style classes in :mod:`handanim.core.styles`:

1. :class:`~handanim.core.styles.StrokeStyle` — Pen color, line width, opacity, and pressure modulation.
2. :class:`~handanim.core.styles.SketchStyle` — Hand-drawn imperfection (`roughness`, `bowing`, `max_random_offset`).
3. :class:`~handanim.core.styles.FillStyle` — Interior fill pattern (`hachure`, `crosshatch`, `zigzag`, `solid`), angle, and gap spacing.

Stroke Styling (:class:`~handanim.core.styles.StrokeStyle`)
-----------------------------------------------------------

.. code-block:: python

   from handanim import StrokePressure, StrokeStyle
   from handanim.stylings.color import BLUE

   pen = StrokeStyle(
       color=BLUE,
       width=3.5,
       opacity=0.95,
       stroke_pressure=StrokePressure.TAPER_BOTH,  # optional pen pressure tapering
   )

Sketch Imperfection (:class:`~handanim.core.styles.SketchStyle`)
----------------------------------------------------------------

Inspired by RoughJS, ``SketchStyle`` controls how "hand-sketched" vs. "crisp geometric" a primitive appears:

.. code-block:: python

   from handanim import SketchStyle

   # Crisp, clean geometric lines (useful for small UI elements or character eyes)
   clean_style = SketchStyle(roughness=0.0, bowing=0.0)

   # Expressive, loose hand-drawn marker strokes
   sketchy_style = SketchStyle(
       roughness=2.0,
       bowing=1.5,
       max_random_offset=2.5,
       disable_font_mixture=True,
   )

Hand-Sketched Fill Patterns (:class:`~handanim.core.styles.FillStyle`)
----------------------------------------------------------------------

Instead of flat digital fills, ``handanim`` fills polygons, circles, and rounded rectangles with hand-drawn hatch strokes:

- ``fill_pattern="hachure"`` (default): Parallel diagonal hatch lines at ``hachure_angle`` (in degrees) spaced by ``hachure_gap``.
- ``fill_pattern="crosshatch"``: Two perpendicular passes of hachure lines.
- ``fill_pattern="zigzag"``: Continuous connected zigzag fill stroke (:class:`~handanim.stylings.fillpatterns.ZigZagLineFillPattern`).
- ``fill_pattern="solid"``: Standard solid vector fill.

.. code-block:: python

   from handanim import Circle, FillStyle
   from handanim.stylings.color import PASTEL_GREEN

   filled_circle = Circle(
       center=(400, 300),
       radius=120,
       fill_style=FillStyle(
           color=PASTEL_GREEN,
           opacity=0.45,
           fill_pattern="zigzag",
           hachure_angle=45,
           hachure_gap=12,
       ),
   )

Color Palettes (:mod:`handanim.stylings.color`)
-----------------------------------------------

:mod:`handanim.stylings.color` exports normalized `(R, G, B)` tuples in `[0.0, 1.0]` for whiteboard contrast, including:

- **Primary & Ink Colors**: ``BLACK``, ``WHITE``, ``RED``, ``BLUE``, ``GREEN``, ``ORANGE``, ``PURPLE``, ``TEAL``, ``BROWN``, ``GRAY``, ``DARK_GRAY``
- **Pastel Hatching Colors**: ``PASTEL_BLUE``, ``PASTEL_RED``, ``PASTEL_GREEN``, ``PASTEL_ORANGE``, ``PASTEL_PURPLE``, ``PASTEL_YELLOW``
- **Hex Helper**: Convert any `#RRGGBB` string via ``hex_to_rgb("#2563EB")``.

