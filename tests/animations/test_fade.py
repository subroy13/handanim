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
