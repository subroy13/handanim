"""
ML Workflow Demo
================
A single scene that combines both new primitives:

  LEFT  — Flowchart  : the ML training pipeline (collect → preprocess →
                        train → evaluate → deploy / tune)
  RIGHT — Table      : model comparison results that the pipeline produces

Scene timeline
--------------
  0.0 - 1.0  : main title fades in
  1.0 - 1.8  : section labels ("Pipeline" / "Results") fade in
  1.8 - 5.0  : pipeline nodes sketch in one by one
  5.0 - 6.5  : pipeline connectors sketch in one by one
  5.8 - 6.8  : results table header sketches in   (overlaps connector tail)
  6.8 - 10.8 : table data rows sketch in row by row (1 s each, 4 rows)
"""

import os

from handanim.core import Scene, StrokeStyle, SketchStyle, FillStyle
from handanim.animations import SketchAnimation, FadeInAnimation
from handanim.primitives import Text
from handanim.primitives.flowchart import Flowchart
from handanim.primitives.table import Table
from handanim.stylings.color import (
    BLACK,
    NAVY,
    DARK_GRAY,
    PASTEL_BLUE,
    PASTEL_GREEN,
    PASTEL_YELLOW,
    PASTEL_RED,
)

# ---------------------------------------------------------------------------
# Scene  (viewport ≈ 1778 × 1000 world units)
# ---------------------------------------------------------------------------
scene = Scene(width=1920, height=1080)

# ---------------------------------------------------------------------------
# Shared styles
# ---------------------------------------------------------------------------
SKETCHY = SketchStyle(roughness=2, bowing=1)
LIGHT_SKETCHY = SketchStyle(roughness=1, bowing=1)

PROCESS_STROKE = StrokeStyle(color=NAVY, width=2)
DIAMOND_STROKE = StrokeStyle(color=(0.5, 0.1, 0.1), width=2)
CONN_STROKE = StrokeStyle(color=DARK_GRAY, width=1)

PROCESS_FILL = FillStyle(color=PASTEL_BLUE, hachure_gap=8)
DIAMOND_FILL = FillStyle(color=PASTEL_YELLOW, hachure_gap=8)
TERMINAL_FILL = FillStyle(color=PASTEL_GREEN, hachure_gap=8)
TUNE_FILL = FillStyle(color=PASTEL_RED, hachure_gap=8)

HEADER_STROKE = StrokeStyle(color=NAVY, width=2)
HEADER_FILL = FillStyle(color=PASTEL_BLUE, hachure_gap=7)
CELL_STROKE = StrokeStyle(color=(0.2, 0.2, 0.4), width=1)

# ---------------------------------------------------------------------------
# Main title  (centred across full width)
# ---------------------------------------------------------------------------
title = Text(
    text="Machine Learning Workflow",
    position=(889, 52),
    font_size=78,
    stroke_style=StrokeStyle(color=NAVY, width=2),
    sketch_style=LIGHT_SKETCHY,
)

# ---------------------------------------------------------------------------
# Section labels
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Flowchart — left half  (nodes centred at x ≈ 340)
#
#   Collect Data  (340, 155)
#        ↓
#   Preprocess    (340, 285)
#        ↓
#   Train Model   (340, 420)
#        ↓
#   Accuracy OK?  (340, 560)   ── No ──►   Tune Params  (630, 560)
#        ↓ Yes
#   Deploy Model  (340, 700)
#
# "No" connector: both anchors at y = 560  →  straight horizontal line
# "Yes" connector: both anchors at x = 340 →  straight vertical line
# ---------------------------------------------------------------------------
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
                "fill_style": PROCESS_FILL,
            },
            {
                "id": "preprocess",
                "label": "Preprocess",
                "position": [340, 285],
                "size": [190, 52],
                "stroke_style": PROCESS_STROKE,
                "sketch_style": SKETCHY,
                "fill_style": PROCESS_FILL,
            },
            {
                "id": "train",
                "label": "Train Model",
                "position": [340, 420],
                "size": [190, 52],
                "stroke_style": PROCESS_STROKE,
                "sketch_style": SKETCHY,
                "fill_style": PROCESS_FILL,
            },
            {
                "id": "evaluate",
                "type": "diamond",
                "label": "Accuracy OK?",
                "position": [340, 560],
                "size": [215, 82],
                "stroke_style": DIAMOND_STROKE,
                "sketch_style": SKETCHY,
                "fill_style": DIAMOND_FILL,
            },
            {
                "id": "tune",
                "label": "Tune Params",
                "position": [630, 560],
                "size": [180, 52],
                "stroke_style": PROCESS_STROKE,
                "sketch_style": SKETCHY,
                "fill_style": TUNE_FILL,
            },
            {
                "id": "deploy",
                "label": "Deploy Model",
                "position": [340, 700],
                "size": [190, 52],
                "stroke_style": PROCESS_STROKE,
                "sketch_style": SKETCHY,
                "fill_style": TERMINAL_FILL,
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

# ---------------------------------------------------------------------------
# Table — right half
#
# top_left = (870, 148),  5 rows × 4 cols,  cell 218 × 65
# Total footprint: 872 × 325   (fits within right half 870–1778)
# ---------------------------------------------------------------------------
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
    stroke_style=CELL_STROKE,
    sketch_style=SKETCHY,
    header_stroke_style=HEADER_STROKE,
    header_fill_style=HEADER_FILL,
)

# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------

# Titles
scene.add(FadeInAnimation(start_time=0.0, duration=1.0), title)
scene.add(FadeInAnimation(start_time=1.0, duration=0.8), label_pipeline)
scene.add(FadeInAnimation(start_time=1.0, duration=0.8), label_results)

# Flowchart nodes — each gets an equal slice of the 3.2 s window
NODE_START = 1.8
NODE_TOTAL = 3.2
node_step = NODE_TOTAL / len(fc.nodes)
for i, node in enumerate(fc.nodes):
    scene.add(
        SketchAnimation(start_time=NODE_START + i * node_step, duration=node_step),
        node,
    )

# Flowchart connectors — each gets an equal slice of the 1.5 s window
CONN_START = 5.0
CONN_TOTAL = 1.5
conn_step = CONN_TOTAL / len(fc.connectors)
for i, connector in enumerate(fc.connectors):
    scene.add(
        SketchAnimation(start_time=CONN_START + i * conn_step, duration=conn_step),
        connector,
    )

# Table header — sketches in as the last connector is being drawn
header_event, header_drawable = table.animate_by_row(
    SketchAnimation,
    start_time=5.8,
    total_duration=1.0,
).pairs[0]
scene.add(header_event, header_drawable)

# Table data rows — staggered 1 s each, beginning once the header is done
data_reveal = table.animate_by_row(
    SketchAnimation,
    start_time=6.8,
    total_duration=4.0,
)
for event, drawable in data_reveal.pairs[1:]:  # skip header (pairs[0])
    scene.add(event, drawable)

# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
output_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "output", "ml_workflow_demo.gif")
scene.render(output_path, max_length=12)
