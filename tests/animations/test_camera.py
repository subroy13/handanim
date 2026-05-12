"""
Tests for CameraAnimation and Scene._get_viewport_at.

Structure
---------
- TestCameraAnimationBasics   — type, _apply passthrough, apply_to_viewport return type
- TestCameraAnimationViewport — interpolation at progress 0 / 0.5 / 1, from_* overrides
- TestSceneGetViewportAt      — no events, pre-start, mid-event, post-event, chained events
"""

import pytest
import numpy as np

from handanim.core.animation import AnimationEventType
from handanim.core.draw_ops import Ops, OpsSet, OpsType
from handanim.core.viewport import Viewport
from handanim.animations.camera import CameraAnimation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hline_opsset() -> OpsSet:
    ops = OpsSet(initial_set=[])
    ops.add(Ops(OpsType.SET_PEN, {"color": (0.0, 0.0, 0.0), "width": 2}))
    ops.add(Ops(OpsType.MOVE_TO, [(100.0, 0.0)]))
    ops.add(Ops(OpsType.LINE_TO, [(200.0, 0.0)]))
    return ops


def _base_viewport() -> Viewport:
    return Viewport(world_xrange=(0, 1000), world_yrange=(0, 750), screen_width=800, screen_height=600, margin=0)


def _scene_with_camera(*events):
    from handanim.core.scene import Scene
    s = Scene(width=800, height=600)
    for e in events:
        s.add_camera(e)
    return s


# ---------------------------------------------------------------------------
# Basics
# ---------------------------------------------------------------------------

class TestCameraAnimationBasics:
    def test_type_is_mutation(self):
        assert CameraAnimation(start_time=0, duration=1).type == AnimationEventType.MUTATION

    def test_apply_on_opsset_returns_opsset_unchanged(self):
        ops = _make_hline_opsset()
        result = CameraAnimation(start_time=0, duration=1).apply(ops, raw_progress=0.5)
        assert isinstance(result, OpsSet)
        assert len(result.opsset) == len(ops.opsset)

    def test_apply_to_viewport_returns_viewport(self):
        anim = CameraAnimation(start_time=0, duration=1, data={"to_xrange": (100, 900)})
        assert isinstance(anim.apply_to_viewport(_base_viewport(), progress=0.5), Viewport)

    def test_apply_to_viewport_preserves_screen_dimensions(self):
        vp = _base_viewport()
        result = CameraAnimation(start_time=0, duration=1, data={"to_xrange": (100, 900)}).apply_to_viewport(vp, 1.0)
        assert result.screen_width == vp.screen_width
        assert result.screen_height == vp.screen_height
        assert result.margin == vp.margin


# ---------------------------------------------------------------------------
# apply_to_viewport — interpolation
# ---------------------------------------------------------------------------

class TestCameraAnimationViewport:
    def _zoom_anim(self):
        return CameraAnimation(
            start_time=0, duration=1,
            data={"to_xrange": (200, 800), "to_yrange": (150, 600)},
        )

    def test_progress_zero_no_change(self):
        vp = _base_viewport()
        result = self._zoom_anim().apply_to_viewport(vp, progress=0.0)
        assert result.world_xrange == pytest.approx(vp.world_xrange)
        assert result.world_yrange == pytest.approx(vp.world_yrange)

    def test_progress_one_reaches_target(self):
        vp = _base_viewport()
        result = self._zoom_anim().apply_to_viewport(vp, progress=1.0)
        assert result.world_xrange == pytest.approx((200, 800))
        assert result.world_yrange == pytest.approx((150, 600))

    def test_progress_half_midpoint(self):
        vp = _base_viewport()
        result = self._zoom_anim().apply_to_viewport(vp, progress=0.5)
        # xrange (0,1000)→(200,800) at 0.5 → (100, 900)
        assert result.world_xrange == pytest.approx((100.0, 900.0))
        # yrange (0,750)→(150,600) at 0.5 → (75, 675)
        assert result.world_yrange == pytest.approx((75.0, 675.0))

    def test_explicit_from_range_overrides_current(self):
        """When from_xrange is given, interpolation starts from it, not the current viewport."""
        anim = CameraAnimation(
            start_time=0, duration=1,
            data={"from_xrange": (500, 1500), "to_xrange": (0, 1000)},
        )
        result = anim.apply_to_viewport(_base_viewport(), progress=0.0)
        assert result.world_xrange == pytest.approx((500, 1500))

    def test_no_to_range_means_no_change(self):
        anim = CameraAnimation(start_time=0, duration=1, data={})
        vp = _base_viewport()
        for p in (0.0, 0.5, 1.0):
            result = anim.apply_to_viewport(vp, progress=p)
            assert result.world_xrange == pytest.approx(vp.world_xrange)
            assert result.world_yrange == pytest.approx(vp.world_yrange)

    def test_easing_only_runs_inside_apply(self):
        """apply_to_viewport bypasses easing; easing runs only via .apply()."""
        calls = []
        anim = CameraAnimation(
            start_time=0, duration=1,
            easing_fun=lambda t: calls.append(t) or t,
            data={"to_xrange": (200, 800)},
        )
        anim.apply_to_viewport(_base_viewport(), progress=0.5)
        assert calls == []


# ---------------------------------------------------------------------------
# Scene._get_viewport_at
# ---------------------------------------------------------------------------

class TestSceneGetViewportAt:
    def test_no_camera_events_returns_base_viewport(self):
        s = _scene_with_camera()
        vp = s._get_viewport_at(t=5.0)
        assert vp.world_xrange == pytest.approx(s.viewport.world_xrange)
        assert vp.world_yrange == pytest.approx(s.viewport.world_yrange)

    def test_before_event_starts_returns_base_viewport(self):
        s = _scene_with_camera(CameraAnimation(start_time=10, duration=3, data={"to_xrange": (200, 800)}))
        vp = s._get_viewport_at(t=5.0)
        assert vp.world_xrange == pytest.approx(s.viewport.world_xrange)

    def test_at_event_midpoint_interpolates(self):
        s = _scene_with_camera(CameraAnimation(start_time=0, duration=2, data={"to_xrange": (0, 500)}))
        vp = s._get_viewport_at(t=1.0)  # progress = 0.5
        expected_x1 = 0.5 * s.viewport.world_xrange[1] + 0.5 * 500
        assert vp.world_xrange[1] == pytest.approx(expected_x1)

    def test_after_event_ends_reaches_target(self):
        s = _scene_with_camera(
            CameraAnimation(start_time=0, duration=2, data={"to_xrange": (100, 600), "to_yrange": (50, 400)})
        )
        vp = s._get_viewport_at(t=5.0)
        assert vp.world_xrange == pytest.approx((100, 600))
        assert vp.world_yrange == pytest.approx((50, 400))

    def test_chained_events_second_starts_from_first_target(self):
        """Second event defaults from_* to where the first event ended."""
        s = _scene_with_camera(
            CameraAnimation(start_time=0, duration=1, data={"to_xrange": (0, 500)}),
            CameraAnimation(start_time=2, duration=1, data={"to_xrange": (0, 250)}),
        )
        # At t=2.5: second event at progress=0.5, from=(0,500) → to=(0,250) → (0,375)
        assert s._get_viewport_at(t=2.5).world_xrange == pytest.approx((0, 375))

    def test_add_camera_stores_event(self):
        s = _scene_with_camera()
        anim = CameraAnimation(start_time=0, duration=1)
        s.add_camera(anim)
        assert len(s.camera_events) == 1
        assert s.camera_events[0] is anim
