"""Fades preserve the relative opacity of translucent strokes and images."""

import pytest

from handanim import FadeInAnimation, FadeOutAnimation
from handanim.core.draw_ops import Ops, OpsSet, OpsType


@pytest.mark.parametrize("kind", [OpsType.SET_PEN, OpsType.IMAGE])
@pytest.mark.parametrize("animation", [FadeInAnimation, FadeOutAnimation])
@pytest.mark.parametrize("progress", [0.0, 0.5, 1.0])
def test_fade_scales_existing_opacity_without_mutation(kind, animation, progress):
    original = OpsSet([Ops(kind, {"opacity": 0.16})])
    result = animation(duration=1).apply(original, progress)
    factor = progress if animation is FadeInAnimation else 1 - progress
    assert result.opsset[0].data["opacity"] == pytest.approx(0.16 * factor)
    assert original.opsset[0].data["opacity"] == 0.16


@pytest.mark.parametrize("kind", [OpsType.SET_PEN, OpsType.IMAGE])
def test_fade_defaults_missing_opacity_to_opaque(kind):
    original = OpsSet([Ops(kind, {})])
    result = FadeInAnimation(duration=1).apply(original, 0.5)
    assert result.opsset[0].data["opacity"] == 0.5
    assert original.opsset[0].data == {}


def test_fade_in_after_fade_out_restores_original_opacity():
    from handanim import Line, Scene
    from handanim.core.styles import StrokeStyle

    scene = Scene(fps=10)
    line = Line((0, 0), (100, 100), stroke_style=StrokeStyle(opacity=0.8))
    scene.add(FadeInAnimation(start_time=0.0, duration=0.5), line)
    scene.add(FadeOutAnimation(start_time=0.5, duration=0.5), line)
    scene.add(FadeInAnimation(start_time=1.0, duration=0.5), line)

    frames = scene.create_event_timeline(max_length=1.5)
    # At t = 1.2s (frame index 12 at 10 fps), progress into the second FadeIn is 0.4
    frame_1_2s = frames[12]
    pen_ops = [op for op in frame_1_2s.opsset if op.type == OpsType.SET_PEN]
    assert len(pen_ops) > 0
    assert pen_ops[0].data["opacity"] == pytest.approx(0.8 * 0.4)

    # At t = 1.5s (frame index 15), full original opacity is restored
    frame_1_5s = frames[15]
    pen_ops_end = [op for op in frame_1_5s.opsset if op.type == OpsType.SET_PEN]
    assert pen_ops_end[0].data["opacity"] == pytest.approx(0.8)
