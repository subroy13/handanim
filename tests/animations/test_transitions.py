import os

import cairo
import numpy as np
import pytest

from handanim import (
    Circle,
    FillStyle,
    PageTurnTransition,
    PaperCrumpleTransition,
    Rectangle,
    Scene,
    SketchAnimation,
    StrokeStyle,
    Text,
)
from handanim.core.draw_ops import Ops, OpsSet, OpsType
from voiceanim import mix_soundtrack, synthesize_crumple_sound, synthesize_page_turn_sound


def test_push_pop_clip_opsset_render_and_bbox():
    """Verify PUSH_CLIP and POP_CLIP render cleanly on a Cairo context and do not distort get_bbox."""
    ops = OpsSet(
        initial_set=[
            Ops(OpsType.PUSH_CLIP, [(100.0, 100.0), (300.0, 100.0), (300.0, 300.0), (100.0, 300.0)]),
            Ops(OpsType.SET_PEN, {"color": (0.1, 0.2, 0.8), "width": 3.0, "opacity": 1.0, "mode": "stroke"}),
            Ops(OpsType.MOVE_TO, [(50.0, 150.0)]),
            Ops(OpsType.LINE_TO, [(350.0, 250.0)]),
            Ops(OpsType.CLOSE_PATH, {}),
            Ops(OpsType.POP_CLIP, None),
        ]
    )
    bbox = ops.get_bbox()
    assert bbox.min_x == pytest.approx(50.0)
    assert bbox.max_x == pytest.approx(350.0)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 400, 400)
    ctx = cairo.Context(surface)
    ops.render(ctx)


@pytest.mark.parametrize(
    "direction",
    [
        "right_to_left",
        "left_to_right",
        "bottom_to_top",
        "top_to_bottom",
        "bottom_right",
        "bottom_left",
        "top_right",
        "top_left",
    ],
)
def test_page_turn_transition_directions(direction: str):
    """Test PageTurnTransition across all supported cardinal and corner fold directions."""
    scene = Scene(width=640, height=360, fps=10)
    rect = Rectangle(
        top_left=(200, 200),
        width=400,
        height=300,
        stroke_style=StrokeStyle(color=(0.1, 0.2, 0.7), width=3.0),
        fill_style=FillStyle(color=(0.4, 0.7, 0.9), opacity=0.5),
    )
    outgoing_ops = rect.draw()
    circle = Circle(
        center=(800, 500),
        radius=120,
        stroke_style=StrokeStyle(color=(0.8, 0.2, 0.1), width=3.0),
    )
    incoming_ops = circle.draw()

    tr = PageTurnTransition(start_time=1.0, duration=1.0, direction=direction)
    for raw_p in (0.1, 0.45, 0.85):
        composed = tr.apply_transition(
            outgoing_ops=outgoing_ops,
            incoming_ops=incoming_ops,
            raw_progress=raw_p,
            viewport=scene.viewport,
            background_color=scene.background_color,
        )
        assert len(composed.opsset) > 0
        # Verify PUSH_CLIP and POP_CLIP are balanced
        pushes = sum(1 for op in composed.opsset if op.type == OpsType.PUSH_CLIP)
        pops = sum(1 for op in composed.opsset if op.type == OpsType.POP_CLIP)
        assert pushes == pops
        assert pushes >= 2


def test_page_turn_invalid_direction():
    with pytest.raises(ValueError, match="Unsupported direction"):
        PageTurnTransition(start_time=0.0, duration=1.0, direction="diagonal_invalid")


@pytest.mark.parametrize(
    "direction",
    ["right", "left", "top_right", "bottom_right", "top_left", "bottom_left"],
)
def test_paper_crumple_transition_phases(direction: str):
    """Test PaperCrumpleTransition during both the crunch phase and parabolic toss phase."""
    scene = Scene(width=640, height=360, fps=10)
    rect = Rectangle(
        top_left=(300, 250),
        width=500,
        height=350,
        stroke_style=StrokeStyle(color=(0.2, 0.5, 0.2), width=3.0),
    )
    outgoing_ops = rect.draw()
    incoming_ops = Circle(center=(700, 500), radius=150).draw()

    tr = PaperCrumpleTransition(start_time=1.0, duration=1.2, direction=direction, seed=123)
    for raw_p in (0.15, 0.4, 0.65, 0.9):
        composed = tr.apply_transition(
            outgoing_ops=outgoing_ops,
            incoming_ops=incoming_ops,
            raw_progress=raw_p,
            viewport=scene.viewport,
            background_color=scene.background_color,
        )
        assert len(composed.opsset) > 0
        pushes = sum(1 for op in composed.opsset if op.type == OpsType.PUSH_CLIP)
        pops = sum(1 for op in composed.opsset if op.type == OpsType.POP_CLIP)
        assert pushes == pops == 1


def test_scene_transitions_deactivate_previous_page_and_preserve_overlay(tmp_path):
    """Verify Scene automatically deactivates old-page world objects after a transition while keeping overlays."""
    scene = Scene(width=480, height=270, fps=10, transition_sound=True)

    page1_box = Rectangle(top_left=(200, 200), width=300, height=200)
    page2_circle = Circle(center=(800, 500), radius=140)
    page3_text = Text("Page 3", position=(800, 500), font_size=48)
    hud_title = Text(" Persistent Header ", position=(800, 80), font_size=32)

    # Persistent HUD in overlay
    scene.overlay.add(SketchAnimation(start_time=0.0, duration=0.3), hud_title)

    # Page 1: drawn at t=0..0.5, turned at t=1.0..2.0
    scene.add(SketchAnimation(start_time=0.0, duration=0.5), page1_box)
    scene.add(PageTurnTransition(start_time=1.0, duration=1.0, direction="bottom_right"))

    # Page 2: drawn at t=1.5..2.3, crumpled at t=2.5..3.5
    scene.add(SketchAnimation(start_time=1.5, duration=0.8), page2_circle)
    scene.add(PaperCrumpleTransition(start_time=2.5, duration=1.0, direction="right"))

    # Page 3: drawn at t=3.0..3.8
    scene.add(SketchAnimation(start_time=3.0, duration=0.8), page3_text)

    # Check active objects before, during, and after transitions
    active_t08 = scene.get_active_objects(0.8)
    assert page1_box.id in active_t08
    assert hud_title.id in active_t08

    # Mid-PageTurn (t=1.6): both page1_box (outgoing) and page2_circle (incoming) are active
    active_t16 = scene.get_active_objects(1.6)
    assert page1_box.id in active_t16
    assert page2_circle.id in active_t16
    assert hud_title.id in active_t16

    # After PageTurn (t=2.2): page1_box is deactivated, page2_circle and hud_title remain active
    active_t22 = scene.get_active_objects(2.2)
    assert page1_box.id not in active_t22
    assert page2_circle.id in active_t22
    assert hud_title.id in active_t22

    # After PaperCrumple (t=3.7): page1_box and page2_circle are deactivated, page3_text and hud_title are active
    active_t37 = scene.get_active_objects(3.7)
    assert page1_box.id not in active_t37
    assert page2_circle.id not in active_t37
    assert page3_text.id in active_t37
    assert hud_title.id in active_t37

    # Check auto SFX extraction includes both page_turn and crumple
    sfx = scene.extract_auto_sfx_events()
    sfx_types = [item["type"] for item in sfx]
    assert "page_turn" in sfx_types
    assert "crumple" in sfx_types

    # Render snapshot during PageTurn and PaperCrumple
    snap1 = str(tmp_path / "mid_page_turn.png")
    snap2 = str(tmp_path / "mid_crumple.png")
    scene.render_snapshot(snap1, frame_in_seconds=1.5)
    scene.render_snapshot(snap2, frame_in_seconds=3.0)
    assert os.path.exists(snap1) and os.path.getsize(snap1) > 0
    assert os.path.exists(snap2) and os.path.getsize(snap2) > 0


def test_transition_sfx_synthesis_and_soundtrack(tmp_path):
    """Verify procedural page_turn and crumple audio synthesis and mixing."""
    arr_pt = synthesize_page_turn_sound(duration=1.1)
    arr_cr = synthesize_crumple_sound(duration=1.3)

    assert isinstance(arr_pt, np.ndarray) and arr_pt.size > 10000
    assert isinstance(arr_cr, np.ndarray) and arr_cr.size > 10000
    assert float(np.max(np.abs(arr_pt))) > 0.01
    assert float(np.max(np.abs(arr_cr))) > 0.01

    mixed_wav = str(tmp_path / "mixed.wav")
    out = mix_soundtrack(
        duration=3.0,
        sfx_events=[
            {"type": "page_turn", "start_time": 0.2, "duration": 1.0, "volume": 0.6},
            {"type": "crumple", "start_time": 1.5, "duration": 1.2, "volume": 0.6},
        ],
        output_path=mixed_wav,
    )
    assert os.path.exists(out) and os.path.getsize(out) > 1000
