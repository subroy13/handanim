Primitives, Flowcharts & Tables
===============================

``handanim`` provides a rich set of geometric, diagramming, and media primitives in :mod:`handanim.primitives`.

Geometric Primitives
--------------------

Lines & Arrows
~~~~~~~~~~~~~~

- :class:`~handanim.primitives.lines.Line`: Hand-drawn line segment between ``start`` and ``end``.
- :class:`~handanim.primitives.lines.LinearPath`: Multi-point polyline path.
- :class:`~handanim.primitives.arrow.Arrow`: Straight arrow with configurable arrowhead styles (``"triangle"``, ``"open"``, ``"stealth"``), double-ended arrows, and label support.
- :class:`~handanim.primitives.arrow.CurvedArrow`: Quadratic/cubic Bézier curved arrow between two points.

Polygons & Rounded Rectangles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- :class:`~handanim.primitives.polygons.Polygon`: Closed polygon from a list of vertices.
- :class:`~handanim.primitives.polygons.Rectangle` and :class:`~handanim.primitives.polygons.Square`: Axis-aligned boxes.
- :class:`~handanim.primitives.polygons.RoundedRectangle`: Box with rounded corners (`border_radius`). Hachure and cross-hatch fills automatically clip cleanly inside the rounded corner contour.
- :class:`~handanim.primitives.polygons.NGon`: Regular $n$-sided polygon given ``center``, ``radius``, and ``n``.

Circles, Ellipses, Arcs & Curves
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- :class:`~handanim.primitives.ellipse.Circle` and :class:`~handanim.primitives.ellipse.Ellipse`
- :class:`~handanim.primitives.ellipse.Arc` and :class:`~handanim.primitives.ellipse.Annulus`
- :class:`~handanim.primitives.curves.Curve`: Smooth Catmull-Rom / cubic spline curve through a sequence of points.

Flowcharts (:mod:`handanim.primitives.flowchart`)
-------------------------------------------------

Build hand-drawn flowcharts either node-by-node or declaratively from a Python dictionary:

.. code-block:: python

   from handanim import Flowchart, FlowchartConnector, FlowchartDiamond, FlowchartNode

   # Declarative construction via Flowchart.from_dict
   chart = Flowchart.from_dict({
       "nodes": [
           {"id": "start", "type": "node", "label": "Input Data", "position": (200, 150), "size": (220, 80)},
           {"id": "check", "type": "diamond", "label": "Valid?", "position": (200, 320), "size": (200, 120)},
           {"id": "done", "type": "node", "label": "Train Model", "position": (200, 520), "size": (220, 80)},
       ],
       "edges": [
           {"from": "start", "to": "check"},
           {"from": "check", "to": "done", "label": "Yes"},
       ],
   })

Tables (:class:`~handanim.primitives.table.Table`)
--------------------------------------------------

Create hand-sketched grids of cells with header styling and row-by-row or cell-by-cell reveal helpers:

.. code-block:: python

   from handanim import SketchAnimation, Table

   table = Table(
       data=[
           ["Order", "Glucose Spike", "Fullness"],
           ["Carbs First", "+62 mg/dL", "Low"],
           ["Protein First", "+24 mg/dL", "High"],
       ],
       top_left=(140, 200),
       col_widths=[260, 260, 220],
       row_height=70,
       header=True,
   )

   # Reveal row by row across 3.0 seconds
   reveal_event = table.animate_by_row(SketchAnimation, start_time=0.5, total_duration=3.0)
   reveal_event.add_to_scene(scene)

SVG, Raster Images & Eraser
---------------------------

- :class:`~handanim.primitives.vector_svg.VectorSVG`: Parses external ``.svg`` files via ``svgelements`` into hand-sketched ``OpsSet`` paths that animate stroke-by-stroke with :class:`~handanim.animations.sketch.SketchAnimation`.
- :class:`~handanim.primitives.raster_image.RasterImage`: Embeds PNG/JPEG bitmaps onto the Cairo canvas with support for translation, scaling, rotation, and opacity fades.
- :class:`~handanim.primitives.eraser.Eraser`: Performs a realistic zigzag pastel-blend wipe over target drawables using the scene's background color, then automatically removes the erased drawables from the active timeline at ``event.end_time``:

.. code-block:: python

   from handanim import Eraser, SketchAnimation

   eraser = Eraser(objects_to_erase=[card, equation])
   scene.add(SketchAnimation(start_time=4.0, duration=0.8), eraser)

