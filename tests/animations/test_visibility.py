from __future__ import annotations

import pytest

from handanim import (
    FadeInAnimation,
    FadeOutAnimation,
    Hide,
    Line,
    PopAnimation,
    Rectangle,
    Scene,
    Show,
    SketchAnimation,
    SketchStyle,
    StrokeStyle,
    Swap,
    Text,
    ease_in_out,
    ease_out_back,
    ease_out_bounce,
    ease_out_elastic,
    get_font_path,
    linear,
    register_font,
)
from handanim.core.draw_ops import OpsType

FLAT = SketchStyle(roughness=0, bowing=0)


def _pen_opacities(opsset) -> list[float]:
    return [
        float(op.data.get("opacity", 1.0))
        for op in opsset.opsset
        if op.type == OpsType.SET_PEN and isinstance(op.data, dict)
    ]


class TestShowHideSwap:
    def test_show_at_zero_is_visible_on_frame_zero(self):
        scene = Scene(fps=10)
        hook = Line((10, 10), (100, 10), stroke_style=StrokeStyle(opacity=0.8), sketch_style=FLAT)
        scene.add(Show(0.0), hook)

        frames = scene.create_event_timeline(max_length=0.2)
        assert len(frames[0].opsset) > 0
        assert _pen_opacities(frames[0]) == [pytest.approx(0.8)]

    def test_fade_in_initial_opacity_visible_on_frame_zero(self):
        scene = Scene(fps=10)
        hook = Line((10, 10), (100, 10), stroke_style=StrokeStyle(opacity=0.8), sketch_style=FLAT)
        scene.add(FadeInAnimation(start_time=0.0, duration=0.5, initial_opacity=0.25), hook)

        frames = scene.create_event_timeline(max_length=0.5)
        # At t=0.0 (frame 0), opacity = 0.8 * 0.25 = 0.2
        assert _pen_opacities(frames[0]) == [pytest.approx(0.2)]
        # At t=0.5 (frame 5), opacity = 0.8 * 1.0 = 0.8
        assert _pen_opacities(frames[5]) == [pytest.approx(0.8)]

    def test_show_after_fade_out_restores_original_opacity(self):
        scene = Scene(fps=10)
        label = Line((10, 10), (100, 10), stroke_style=StrokeStyle(opacity=0.75), sketch_style=FLAT)
        scene.add(Show(0.0), label)
        scene.add(FadeOutAnimation(start_time=0.2, duration=0.3), label)
        scene.add(Show(0.8), label)

        frames = scene.create_event_timeline(max_length=1.0)
        # Frame 0 (0.0s): visible at 0.75
        assert _pen_opacities(frames[0]) == [pytest.approx(0.75)]
        # Frame 6 (0.6s): hidden after FadeOut
        assert len(frames[6].opsset) == 0
        # Frame 8 (0.8s): shown again with restored 0.75 opacity
        assert _pen_opacities(frames[8]) == [pytest.approx(0.75)]

    def test_sketch_after_fade_out_restores_original_opacity(self):
        scene = Scene(fps=10)
        label = Line((10, 10), (100, 10), stroke_style=StrokeStyle(opacity=0.6), sketch_style=FLAT)
        scene.add(FadeInAnimation(start_time=0.0, duration=0.2), label)
        scene.add(FadeOutAnimation(start_time=0.3, duration=0.2), label)
        scene.add(SketchAnimation(start_time=0.6, duration=0.2), label)

        frames = scene.create_event_timeline(max_length=1.0)
        assert _pen_opacities(frames[9]) == [pytest.approx(0.6)]

    def test_repeated_show_and_hide_blink_toggle(self):
        scene = Scene(fps=10)
        eyelid = Line((0, 0), (20, 0), sketch_style=FLAT)
        scene.add(Show(0.2), eyelid)
        scene.add(Hide(0.4), eyelid)
        scene.add(Show(0.7), eyelid)
        scene.add(Hide(0.9), eyelid)

        assert eyelid.id not in scene.get_active_objects(0.1)
        assert eyelid.id in scene.get_active_objects(0.2)
        assert eyelid.id in scene.get_active_objects(0.3)
        assert eyelid.id not in scene.get_active_objects(0.4)
        assert eyelid.id not in scene.get_active_objects(0.6)
        assert eyelid.id in scene.get_active_objects(0.7)
        assert eyelid.id not in scene.get_active_objects(0.9)

    def test_swap_instant_via_scene_add_and_scene_swap(self):
        scene = Scene(fps=10)
        mouth_closed = Line((0, 0), (20, 0), sketch_style=FLAT)
        mouth_open = Line((0, 0), (20, 10), sketch_style=FLAT)

        scene.add(Show(0.0), mouth_closed)
        scene.add(Swap(mouth_closed, mouth_open, start_time=0.5))
        scene.swap(mouth_open, mouth_closed, start_time=1.0)

        assert mouth_closed.id in scene.get_active_objects(0.2)
        assert mouth_open.id not in scene.get_active_objects(0.2)

        assert mouth_closed.id not in scene.get_active_objects(0.6)
        assert mouth_open.id in scene.get_active_objects(0.6)

        assert mouth_closed.id in scene.get_active_objects(1.1)
        assert mouth_open.id not in scene.get_active_objects(1.1)

    def test_swap_with_crossfade_duration(self):
        scene = Scene(fps=10)
        a = Line((0, 0), (20, 0), sketch_style=FLAT)
        b = Line((0, 10), (20, 10), sketch_style=FLAT)

        scene.add(Show(0.0), a)
        scene.add(Swap(a, b, start_time=0.4, duration=0.4))

        # Mid-crossfade at t=0.6s: both active
        active_mid = scene.get_active_objects(0.6)
        assert a.id in active_mid
        assert b.id in active_mid

        # After crossfade at t=0.9s: only b active
        active_after = scene.get_active_objects(0.9)
        assert a.id not in active_after
        assert b.id in active_after


class TestErgonomicEnhancements:
    def test_drawable_center_at_and_centred_and_align_to(self):
        rect = Rectangle(top_left=(10.0, 20.0), width=100.0, height=50.0, sketch_style=FLAT)
        centered = rect.center_at(540.0, 960.0)
        cx, cy = centered.anchor("center")
        assert cx == pytest.approx(540.0, abs=1.0)
        assert cy == pytest.approx(960.0, abs=1.0)

        centred_uk = rect.centred(200.0, 300.0)
        uk_x, uk_y = centred_uk.anchor("center")
        assert uk_x == pytest.approx(200.0, abs=1.0)
        assert uk_y == pytest.approx(300.0, abs=1.0)

        top_aligned = rect.align_to(540.0, 100.0, anchor="top")
        tx, ty = top_aligned.anchor("top")
        assert tx == pytest.approx(540.0, abs=1.0)
        assert ty == pytest.approx(100.0, abs=1.0)

    def test_text_align_center_and_font_alias(self):
        txt = Text("Centered Title", position=(540, 200), font_size=48, font="feasibly", align="center")
        assert txt.font_name == "feasibly"
        cx, _ = txt.anchor("center")
        assert cx == pytest.approx(540.0, abs=2.0)

    def test_register_font_runtime(self):
        existing_ttf = get_font_path("feasibly")
        registered = register_font("my_custom_alias", existing_ttf)
        assert get_font_path("my_custom_alias") == registered

    def test_easing_functions_and_pop_animation(self):
        assert linear(0.5) == pytest.approx(0.5)
        assert ease_in_out(0.0) == pytest.approx(0.0)
        assert ease_in_out(0.5) == pytest.approx(0.5)
        assert ease_in_out(1.0) == pytest.approx(1.0)
        # ease_out_back overshoots > 1.0 mid-way and lands at 1.0
        assert ease_out_back(0.6) > 1.0
        assert ease_out_back(1.0) == pytest.approx(1.0)
        assert ease_out_elastic(1.0) == pytest.approx(1.0)
        assert ease_out_bounce(1.0) == pytest.approx(1.0)

        rect = Rectangle(top_left=(0.0, 0.0), width=100.0, height=100.0, sketch_style=FLAT)
        pop = PopAnimation(start_time=0.0, duration=0.4)
        mid_ops = pop.apply(rect.draw(), 0.6)
        bbox = mid_ops.get_bbox()
        # Because ease_out_back overshoots at t=0.6, width > 100
        assert bbox.width > 100.0


