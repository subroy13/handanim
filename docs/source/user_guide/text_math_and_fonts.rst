Text, Math & Fonts
==================

``handanim`` provides two complementary text-rendering primitives: :class:`~handanim.primitives.text.Text` for single-line/multi-line handwritten strings and :class:`~handanim.primitives.math.Math` for LaTeX mathematical expressions and Hershey single-stroke typography.

Handwritten Text (:class:`~handanim.primitives.text.Text`)
----------------------------------------------------------

``Text`` converts glyph contours from bundled or user-registered TrueType (``.ttf``) fonts into vector ``OpsSet`` paths:

.. code-block:: python

   from handanim import StrokeStyle, Text
   from handanim.stylings.color import BLACK

   # Left-aligned (default), center-aligned, or right-aligned around position=(x, y)
   heading = Text(
       "Chapter 1: Calculus",
       position=(540, 140),
       font_size=56,
       font_name="feasibly",   # or font="feasibly"
       align="center",
       stroke_style=StrokeStyle(color=BLACK, width=2.8),
   )

Content Autofitting & Multi-Line Wrapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use :meth:`~handanim.primitives.text.Text.autofit` with a :class:`~handanim.core.draw_ops.BoundingBox` to automatically wrap and scale text to fit inside a box or card:

.. code-block:: python

   from handanim.core.draw_ops import BoundingBox

   paragraph = Text("A long explanation that wraps automatically inside the card.")
   paragraph = paragraph.autofit(
       BoundingBox(min_x=120, min_y=200, max_x=960, max_y=420),
       wrap=True,
   )

LaTeX & Hershey Math (:class:`~handanim.primitives.math.Math`)
--------------------------------------------------------------

``Math`` parses LaTeX math strings using Matplotlib's ``MathTextParser`` and renders symbols using custom single-stroke JSON fonts, Hershey vector fonts, or TTF fonts:

.. code-block:: python

   from handanim import Math

   # Custom single-stroke math font (default: "handanimtype1")
   quadratic = Math(
       r"$x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$",
       position=(200, 300),
       font_size=48,
   )

   # Hershey single-stroke vector fonts ("hershey_rowmans", "hershey_mathlow", "hershey_cursive")
   geometry_proof = Math(
       r"$\triangle ABC \sim \triangle DEF \implies \angle A = \angle D$",
       position=(200, 450),
       font_size=42,
       font_name="hershey_rowmans",
   )

Bundled Fonts & Registering Custom Fonts
----------------------------------------

``handanim`` ships with the following built-in fonts out of the box (discoverable via :func:`~handanim.stylings.fonts.list_fonts`):

- ``"feasibly"`` — *FeasiblySingleLine* (TTF, commercial-safe default)
- ``"handanimtype1"`` — Custom single-stroke JSON font for math & text
- ``"noto_sans_math"`` — Skeletonized *Noto Sans Math* JSON font (OFL-1.1)
- ``"hershey_rowmans"``, ``"hershey_mathlow"``, ``"hershey_cursive"`` — Hershey vector stroke fonts
- ``"backstay"`` — *BackstaySingleLine* (TTF, **personal use only**)

.. warning::

   The ``"backstay"`` font (*BackstaySingleLine*) is licensed for **personal use only**. Using ``font_name="backstay"`` in code emits a :exc:`UserWarning` (and a warning in ``aianim``'s AST linter) reminding you to use ``"feasibly"`` or another commercial-friendly font for commercial projects. Default ``Text(...)`` instances never select ``"backstay"`` unless explicitly requested.

Registering Your Own Font at Runtime
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use :func:`~handanim.stylings.fonts.register_font` to register any ``.ttf`` or custom ``.json`` font in memory (or persist it to ``~/.handanim/config.json`` with ``persist=True``):

.. code-block:: python

   from handanim import Text, register_font

   register_font("kalam", "/path/to/Kalam-Regular.ttf", font_type="ttf", persist=False)
   note = Text("Custom registered font!", position=(540, 300), font_size=48, font="kalam", align="center")

