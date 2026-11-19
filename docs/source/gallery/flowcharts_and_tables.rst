Theme 2: Data Science, Flowcharts & Tables
==========================================

``handanim`` includes declarative primitives for technical diagrams (:class:`~handanim.primitives.flowchart.Flowchart`) and structured data grids (:class:`~handanim.primitives.table.Table`) with automatic row-by-row or cell-by-cell progressive reveals.

.. tip::

   To regenerate this animation locally:

   .. code-block:: bash

      poetry run python docs/source/gallery/build_gallery.py --only ml_workflow

----

Tutorial 2.1: Machine Learning Pipeline & Model Comparison Table
----------------------------------------------------------------

**Use Case:** Build a split-screen data science explainer with a decision-branching ML workflow (:meth:`~handanim.primitives.flowchart.Flowchart.from_dict`) on the left and a benchmark comparison table (:meth:`~handanim.primitives.table.Table.animate_by_row`) on the right.

.. image:: /_static/gallery/ml_workflow_demo.gif
   :width: 680px
   :align: center
   :alt: Machine Learning Workflow & Model Comparison Table

Key Concepts Demonstrated
~~~~~~~~~~~~~~~~~~~~~~~~~

- **Declarative Flowchart Construction:** Define process nodes, decision diamonds (``"type": "diamond"``), and labeled orthogonal connectors (`from_side` / `to_side`) in a single dictionary passed to ``Flowchart.from_dict()``.
- **Staggered Node & Edge Reveals:** Iterate over ``fc.nodes`` and ``fc.connectors`` to schedule sequential :class:`~handanim.animations.sketch.SketchAnimation` windows.
- **Row-by-Row Table Animation:** Use ``table.animate_by_row(SketchAnimation, start_time=..., total_duration=...)`` to reveal the header row first, followed by each benchmark row.

Complete Tutorial Code
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from handanim.animations import FadeInAnimation, SketchAnimation
   from handanim.core import FillStyle, Scene, SketchStyle, StrokeStyle
   from handanim.primitives import Flowchart, Table, Text
   from handanim.stylings.color import (
       DARK_GRAY, NAVY, PASTEL_BLUE, PASTEL_GREEN, PASTEL_RED, PASTEL_YELLOW,
   )

   scene = Scene(width=1920, height=1080)

   SKETCHY = SketchStyle(roughness=2, bowing=1)
   LIGHT_SKETCHY = SketchStyle(roughness=1, bowing=1)
   PROCESS_STROKE = StrokeStyle(color=NAVY, width=2)
   DIAMOND_STROKE = StrokeStyle(color=(0.5, 0.1, 0.1), width=2)
   CONN_STROKE = StrokeStyle(color=DARK_GRAY, width=1)

   # 1. Section headers
   title = Text(
       text="Machine Learning Workflow",
       position=(889, 52),
       font_size=78,
       stroke_style=StrokeStyle(color=NAVY, width=2),
       sketch_style=LIGHT_SKETCHY,
   )
   label_pipeline = Text(
       text="Training Pipeline",
       position=(340, 100),
       font_size=46,
       stroke_style=StrokeStyle(color=NAVY, width=1),
       sketch_style=LIGHT_SKETCHY,
   )
   label_results = Text(
       text="Model Comparison",
       position=(1310, 100),
       font_size=46,
       stroke_style=StrokeStyle(color=NAVY, width=1),
       sketch_style=LIGHT_SKETCHY,
   )

   # 2. Left half: Flowchart
   fc = Flowchart.from_dict(
       {
           "nodes": [
               {
                   "id": "collect",
                   "label": "Collect Data",
                   "position": [340, 155],
                   "size": [190, 52],
                   "stroke_style": PROCESS_STROKE,
                   "sketch_style": SKETCHY,
                   "fill_style": FillStyle(color=PASTEL_BLUE, hachure_gap=8),
               },
               {
                   "id": "preprocess",
                   "label": "Preprocess",
                   "position": [340, 285],
                   "size": [190, 52],
                   "stroke_style": PROCESS_STROKE,
                   "sketch_style": SKETCHY,
                   "fill_style": FillStyle(color=PASTEL_BLUE, hachure_gap=8),
               },
               {
                   "id": "train",
                   "label": "Train Model",
                   "position": [340, 420],
                   "size": [190, 52],
                   "stroke_style": PROCESS_STROKE,
                   "sketch_style": SKETCHY,
                   "fill_style": FillStyle(color=PASTEL_BLUE, hachure_gap=8),
               },
               {
                   "id": "evaluate",
                   "type": "diamond",
                   "label": "Accuracy OK?",
                   "position": [340, 560],
                   "size": [215, 82],
                   "stroke_style": DIAMOND_STROKE,
                   "sketch_style": SKETCHY,
                   "fill_style": FillStyle(color=PASTEL_YELLOW, hachure_gap=8),
               },
               {
                   "id": "tune",
                   "label": "Tune Params",
                   "position": [630, 560],
                   "size": [180, 52],
                   "stroke_style": PROCESS_STROKE,
                   "sketch_style": SKETCHY,
                   "fill_style": FillStyle(color=PASTEL_RED, hachure_gap=8),
               },
               {
                   "id": "deploy",
                   "label": "Deploy Model",
                   "position": [340, 700],
                   "size": [190, 52],
                   "stroke_style": PROCESS_STROKE,
                   "sketch_style": SKETCHY,
                   "fill_style": FillStyle(color=PASTEL_GREEN, hachure_gap=8),
               },
           ],
           "edges": [
               {"from": "collect", "to": "preprocess", "stroke_style": CONN_STROKE, "sketch_style": SKETCHY},
               {"from": "preprocess", "to": "train", "stroke_style": CONN_STROKE, "sketch_style": SKETCHY},
               {"from": "train", "to": "evaluate", "stroke_style": CONN_STROKE, "sketch_style": SKETCHY},
               {
                   "from": "evaluate",
                   "to": "tune",
                   "from_side": "right",
                   "to_side": "left",
                   "label": "No",
                   "stroke_style": CONN_STROKE,
                   "sketch_style": SKETCHY,
               },
               {
                   "from": "evaluate",
                   "to": "deploy",
                   "from_side": "bottom",
                   "to_side": "top",
                   "label": "Yes",
                   "stroke_style": CONN_STROKE,
                   "sketch_style": SKETCHY,
               },
           ],
       }
   )

   # 3. Right half: Model Comparison Table
   table = Table(
       top_left=(870, 148),
       n_rows=5,
       n_cols=4,
       cell_width=218,
       cell_height=65,
       headers=["Model", "Accuracy", "F1 Score", "Train Time"],
       data=[
           ["Baseline", "72.3 %", "0.71", " 2 min"],
           ["Random Forest", "85.1 %", "0.84", " 8 min"],
           ["Gradient Boost", "89.4 %", "0.88", "15 min"],
           ["Neural Net", "94.2 %", "0.93", "45 min"],
       ],
       cell_font_size=26,
       header_font_size=30,
       stroke_style=StrokeStyle(color=(0.2, 0.2, 0.4), width=1),
       sketch_style=SKETCHY,
       header_stroke_style=StrokeStyle(color=NAVY, width=2),
       header_fill_style=FillStyle(color=PASTEL_BLUE, hachure_gap=7),
   )

   # 4. Schedule animations
   scene.add(FadeInAnimation(start_time=0.0, duration=1.0), title)
   scene.add(FadeInAnimation(start_time=1.0, duration=0.8), label_pipeline)
   scene.add(FadeInAnimation(start_time=1.0, duration=0.8), label_results)

   node_step = 3.2 / len(fc.nodes)
   for i, node in enumerate(fc.nodes):
       scene.add(SketchAnimation(start_time=1.8 + i * node_step, duration=node_step), node)

   conn_step = 1.5 / len(fc.connectors)
   for i, connector in enumerate(fc.connectors):
       scene.add(SketchAnimation(start_time=5.0 + i * conn_step, duration=conn_step), connector)

   header_event, header_drawable = table.animate_by_row(SketchAnimation, start_time=5.8, total_duration=1.0).pairs[0]
   scene.add(header_event, header_drawable)

   data_reveal = table.animate_by_row(SketchAnimation, start_time=6.8, total_duration=4.0)
   for event, drawable in data_reveal.pairs[1:]:
       scene.add(event, drawable)

   scene.render("ml_workflow_demo.gif", max_length=12)
