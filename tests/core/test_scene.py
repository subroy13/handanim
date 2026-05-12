"""
Tests for Scene: construction, add(), active-object logic, timeline computation,
get_animated_opsset_at_time, create_event_timeline, and render_snapshot.
"""

import os
import numpy as np
import pytest

from handanim.core.scene import Scene
from handanim.core.animation import AnimationEvent, AnimationEventType, CompositeAnimationEvent
from handanim.core.drawable import DrawableGroup
from handanim.core.draw_ops import OpsSet
from handanim.core.styles import SketchStyle
from handanim.core.viewport import Viewport
from handanim.animations.sketch import SketchAnimation
from handanim.primitives.lines import Line
from handanim.primitives.polygons import Rectangle


FLAT = SketchStyle(roughness=0, bowing=0)


def make_line():
    return Line((0, 0), (100, 100), sketch_style=FLAT)


def make_rect():
    return Rectangle((0, 0), 200, 100, sketch_style=FLAT)


def make_sketch(start=0.0, duration=1.0):
    return SketchAnimation(start_time=start, duration=duration)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestSceneConstruction:
    def test_default_dimensions(self):
        s = Scene()
        assert s.width == 1280
        assert s.height == 720

    def test_custom_dimensions(self):
        s = Scene(width=800, height=600)
        assert s.width == 800
        assert s.height == 600

    def test_default_fps(self):
        assert Scene().fps == 24

    def test_custom_fps(self):
        assert Scene(fps=12).fps == 12

    def test_default_background_white(self):
        assert Scene().background_color == (1, 1, 1)

    def test_custom_viewport_is_stored(self):
        vp = Viewport(
            world_xrange=(0, 500),
            world_yrange=(0, 500),
            screen_width=100,
            screen_height=100,
        )
        s = Scene(viewport=vp)
        assert s.viewport is vp

    def test_default_viewport_wider_than_tall(self):
        s = Scene(width=1280, height=720)
        x_min, x_max, y_min, y_max = s.get_viewport_bounds()
        assert (x_max - x_min) > (y_max - y_min)

    def test_events_list_starts_empty(self):
        assert Scene().events == []

    def test_object_timelines_starts_empty(self):
        assert Scene().object_timelines == {}

    def test_drawable_groups_starts_empty(self):
        assert Scene().drawable_groups == {}


# ---------------------------------------------------------------------------
# Viewport helpers
# ---------------------------------------------------------------------------

class TestViewportMethods:
    def test_set_viewport_to_identity_x_range(self):
        s = Scene(width=800, height=600)
        s.set_viewport_to_identity()
        x_min, x_max, _, _ = s.get_viewport_bounds()
        assert x_min == 0
        assert x_max == 800

    def test_set_viewport_to_identity_y_range(self):
        s = Scene(width=800, height=600)
        s.set_viewport_to_identity()
        _, _, y_min, y_max = s.get_viewport_bounds()
        assert y_min == 0
        assert y_max == 600

    def test_get_viewport_bounds_returns_four_values(self):
        assert len(Scene().get_viewport_bounds()) == 4

    def test_get_viewport_bounds_min_less_than_max(self):
        x_min, x_max, y_min, y_max = Scene().get_viewport_bounds()
        assert x_min < x_max
        assert y_min < y_max


# ---------------------------------------------------------------------------
# add()
# ---------------------------------------------------------------------------

class TestSceneAdd:
    def test_add_registers_event(self):
        s = Scene()
        s.add(make_sketch(), make_line())
        assert len(s.events) == 1

    def test_add_registers_drawable_in_timelines(self):
        s = Scene()
        line = make_line()
        s.add(make_sketch(), line)
        assert line.id in s.object_timelines

    def test_creation_event_records_start_time(self):
        s = Scene()
        line = make_line()
        s.add(make_sketch(start=2.0), line)
        assert s.object_timelines[line.id] == [2.0]

    def test_deletion_event_records_end_time(self):
        s = Scene()
        line = make_line()
        s.add(make_sketch(start=0.0, duration=1.0), line)
        del_event = AnimationEvent(AnimationEventType.DELETION, start_time=3.0, duration=0.0)
        s.add(del_event, line)
        # DELETION appends end_time = start_time + duration = 3.0
        assert 3.0 in s.object_timelines[line.id]

    def test_deletion_without_prior_creation_auto_creates(self):
        s = Scene()
        line = make_line()
        del_event = AnimationEvent(AnimationEventType.DELETION, start_time=2.0, duration=0.0)
        s.add(del_event, line)
        assert len(s.object_timelines[line.id]) >= 1

    def test_multiple_drawables_get_independent_timelines(self):
        s = Scene()
        a, b = make_line(), make_rect()
        s.add(make_sketch(start=0.0), a)
        s.add(make_sketch(start=1.0), b)
        assert a.id in s.object_timelines
        assert b.id in s.object_timelines
        assert s.object_timelines[a.id] != s.object_timelines[b.id]

    def test_composite_event_expands_into_sub_events(self):
        s = Scene()
        line = make_line()
        e1 = make_sketch(start=0.0, duration=1.0)
        e2 = make_sketch(start=1.0, duration=1.0)
        s.add(CompositeAnimationEvent([e1, e2]), line)
        assert len(s.events) == 2

    def test_parallel_group_registers_all_elements(self):
        s = Scene()
        a, b = make_line(), make_rect()
        group = DrawableGroup([a, b], grouping_method="parallel")
        s.add(make_sketch(), group)
        assert a.id in s.object_timelines
        assert b.id in s.object_timelines

    def test_parallel_group_stores_group_reference(self):
        s = Scene()
        a, b = make_line(), make_rect()
        group = DrawableGroup([a, b], grouping_method="parallel")
        s.add(make_sketch(), group)
        assert group.id in s.drawable_groups

    def test_parallel_group_event_carries_group_id(self):
        s = Scene()
        a, b = make_line(), make_rect()
        group = DrawableGroup([a, b], grouping_method="parallel")
        event = make_sketch()
        s.add(event, group)
        assert event.data.get("apply_to_group") == group.id

    def test_series_group_registers_all_elements(self):
        s = Scene()
        a, b = make_line(), make_rect()
        group = DrawableGroup([a, b], grouping_method="series")
        # Use base AnimationEvent (CREATION) — SketchAnimation.subdivide() doesn't
        # accept the 'type' kwarg that subdivide() forwards to cls().
        event = AnimationEvent(AnimationEventType.CREATION, start_time=0.0, duration=2.0)
        s.add(event, group)
        assert a.id in s.object_timelines
        assert b.id in s.object_timelines

    def test_series_group_splits_duration(self):
        s = Scene()
        a, b = make_line(), make_rect()
        group = DrawableGroup([a, b], grouping_method="series")
        event = AnimationEvent(AnimationEventType.CREATION, start_time=0.0, duration=2.0)
        s.add(event, group)
        total = sum(e.duration for e, _ in s.events)
        assert abs(total - 2.0) < 1e-9

    def test_drawable_cached_after_add(self):
        s = Scene()
        line = make_line()
        s.add(make_sketch(), line)
        assert s.drawable_cache.exists_in_cache(line.id)


# ---------------------------------------------------------------------------
# get_active_objects
# ---------------------------------------------------------------------------

class TestGetActiveObjects:
    def _scene(self, create_start=0.0, create_dur=0.5, fps=4):
        s = Scene(fps=fps)
        line = make_line()
        s.add(SketchAnimation(start_time=create_start, duration=create_dur), line)
        return s, line

    def test_no_active_objects_before_creation(self):
        s, line = self._scene(create_start=2.0)
        assert line.id not in s.get_active_objects(0.0)

    def test_object_active_at_creation_time(self):
        s, line = self._scene(create_start=0.0)
        assert line.id in s.get_active_objects(0.0)

    def test_object_still_active_after_animation_ends(self):
        s, line = self._scene(create_start=0.0, create_dur=0.5)
        assert line.id in s.get_active_objects(5.0)

    def test_object_inactive_after_deletion(self):
        s = Scene(fps=4)
        line = make_line()
        s.add(make_sketch(start=0.0, duration=0.5), line)
        s.add(AnimationEvent(AnimationEventType.DELETION, start_time=1.0, duration=0.0), line)
        assert line.id not in s.get_active_objects(2.0)

    def test_two_objects_tracked_independently(self):
        s = Scene(fps=4)
        a, b = make_line(), make_rect()
        s.add(SketchAnimation(start_time=0.0, duration=0.5), a)
        s.add(SketchAnimation(start_time=2.0, duration=0.5), b)
        active = s.get_active_objects(1.0)
        assert a.id in active
        assert b.id not in active

    def test_empty_scene_returns_empty_list(self):
        s = Scene()
        assert s.get_active_objects(0.0) == []


# ---------------------------------------------------------------------------
# find_key_frames
# ---------------------------------------------------------------------------

class TestFindKeyFrames:
    def test_returns_sorted_list_and_mapping(self):
        s = Scene(fps=4)
        line = make_line()
        s.add(make_sketch(start=0.0, duration=1.0), line)
        key_frames, mapping = s.find_key_frames()
        assert key_frames == sorted(key_frames)
        assert isinstance(mapping, dict)

    def test_key_frames_include_event_start(self):
        s = Scene(fps=4)
        line = make_line()
        s.add(make_sketch(start=0.5, duration=1.0), line)
        key_frames, _ = s.find_key_frames()
        assert 0.5 in key_frames

    def test_key_frames_include_event_end(self):
        s = Scene(fps=4)
        line = make_line()
        s.add(make_sketch(start=0.5, duration=1.0), line)
        key_frames, _ = s.find_key_frames()
        assert 1.5 in key_frames

    def test_no_duplicate_key_frames(self):
        s = Scene(fps=4)
        a, b = make_line(), make_rect()
        s.add(make_sketch(start=0.0, duration=1.0), a)
        s.add(make_sketch(start=0.0, duration=1.0), b)
        key_frames, _ = s.find_key_frames()
        assert len(key_frames) == len(set(key_frames))

    def test_mapping_contains_drawable_id(self):
        s = Scene(fps=4)
        line = make_line()
        s.add(make_sketch(start=0.0, duration=1.0), line)
        _, mapping = s.find_key_frames()
        assert line.id in mapping

    def test_mapping_contains_event(self):
        s = Scene(fps=4)
        line = make_line()
        event = make_sketch(start=0.0, duration=1.0)
        s.add(event, line)
        _, mapping = s.find_key_frames()
        assert event in mapping[line.id]


# ---------------------------------------------------------------------------
# get_object_event_and_progress
# ---------------------------------------------------------------------------

class TestGetObjectEventAndProgress:
    def _setup(self, start=0.0, duration=1.0, fps=4):
        s = Scene(fps=fps)
        line = make_line()
        event = SketchAnimation(start_time=start, duration=duration)
        s.add(event, line)
        _, mapping = s.find_key_frames()
        return s, line, event, mapping

    def test_completed_event_returns_progress_one(self):
        s, line, event, mapping = self._setup(start=0.0, duration=1.0, fps=4)
        # t=8 frames → 2.0s; event ends at 1.0s → fully completed
        result = s.get_object_event_and_progress(line.id, t=8, drawable_events_mapping=mapping)
        assert len(result) == 1
        assert result[0][1] == 1.0

    def test_in_progress_event_returns_fraction(self):
        s, line, event, mapping = self._setup(start=0.0, duration=2.0, fps=4)
        # t=4 frames → 1.0s; event runs 0..2s → progress 0.5
        result = s.get_object_event_and_progress(line.id, t=4, drawable_events_mapping=mapping)
        assert len(result) == 1
        assert abs(result[0][1] - 0.5) < 1e-6

    def test_before_event_start_returns_empty(self):
        s, line, event, mapping = self._setup(start=2.0, duration=1.0, fps=4)
        # t=0 → 0.0s < start=2.0s
        result = s.get_object_event_and_progress(line.id, t=0, drawable_events_mapping=mapping)
        assert result == []

    def test_at_start_time_returns_zero_progress(self):
        s, line, event, mapping = self._setup(start=1.0, duration=2.0, fps=4)
        # t=4 → 1.0s = start_time; progress = (1.0-1.0)/2.0 = 0.0
        result = s.get_object_event_and_progress(line.id, t=4, drawable_events_mapping=mapping)
        assert len(result) == 1
        assert result[0][1] == pytest.approx(0.0, abs=1e-6)

    def test_returns_event_object_in_tuple(self):
        s, line, event, mapping = self._setup(start=0.0, duration=1.0, fps=4)
        result = s.get_object_event_and_progress(line.id, t=2, drawable_events_mapping=mapping)
        assert result[0][0] is event


# ---------------------------------------------------------------------------
# get_animated_opsset_at_time
# ---------------------------------------------------------------------------

class TestGetAnimatedOpssetAtTime:
    def _setup(self, start=0.0, duration=1.0, fps=4):
        s = Scene(fps=fps)
        line = make_line()
        event = SketchAnimation(start_time=start, duration=duration)
        s.add(event, line)
        _, mapping = s.find_key_frames()
        return s, line, event, mapping

    def test_empty_event_list_returns_initial_opsset(self):
        s, line, event, mapping = self._setup()
        result = s.get_animated_opsset_at_time(line.id, 0, [], mapping)
        assert isinstance(result, OpsSet)

    def test_completed_event_returns_non_empty_opsset(self):
        s, line, event, mapping = self._setup(start=0.0, duration=1.0, fps=4)
        result = s.get_animated_opsset_at_time(line.id, 8, [(event, 1.0)], mapping)
        assert isinstance(result, OpsSet)
        assert len(result.opsset) > 0

    def test_completed_event_gets_written_to_cache(self):
        s, line, event, mapping = self._setup(start=0.0, duration=1.0, fps=4)
        s.get_animated_opsset_at_time(line.id, 8, [(event, 1.0)], mapping)
        assert s.drawable_cache.exists_in_cache(line.id, event.id)

    def test_cache_hit_returns_identical_op_count(self):
        s, line, event, mapping = self._setup(start=0.0, duration=1.0, fps=4)
        ep = [(event, 1.0)]
        r1 = s.get_animated_opsset_at_time(line.id, 8, ep, mapping)
        r2 = s.get_animated_opsset_at_time(line.id, 8, ep, mapping)
        assert len(r1.opsset) == len(r2.opsset)

    def test_partial_progress_returns_opsset(self):
        s, line, event, mapping = self._setup(start=0.0, duration=2.0, fps=4)
        result = s.get_animated_opsset_at_time(line.id, 4, [(event, 0.5)], mapping)
        assert isinstance(result, OpsSet)

    def test_zero_progress_returns_empty_opsset(self):
        s, line, event, mapping = self._setup(start=0.0, duration=2.0, fps=4)
        result = s.get_animated_opsset_at_time(line.id, 0, [(event, 0.0)], mapping)
        # SketchAnimation at progress=0 draws nothing
        assert len(result.opsset) == 0

    def test_partial_has_fewer_ops_than_complete(self):
        s, line, event, mapping = self._setup(start=0.0, duration=2.0, fps=4)
        partial = s.get_animated_opsset_at_time(line.id, 4, [(event, 0.5)], mapping)
        full = s.get_animated_opsset_at_time(line.id, 8, [(event, 1.0)], mapping)
        assert len(partial.opsset) <= len(full.opsset)

    def test_two_chained_events_triggers_recursive_call(self):
        s, line, event1, mapping = self._setup(start=0.0, duration=1.0, fps=4)
        # Manually append a second event to mapping to trigger the recursive code path
        # (len(event_and_progress) > 1 branch, line 242 of scene.py).
        event2 = SketchAnimation(start_time=1.0, duration=1.0)
        mapping[line.id].append(event2)
        ep = [(event1, 1.0), (event2, 0.5)]
        result = s.get_animated_opsset_at_time(line.id, 6, ep, mapping)
        assert isinstance(result, OpsSet)


# ---------------------------------------------------------------------------
# create_event_timeline
# ---------------------------------------------------------------------------

class TestCreateEventTimeline:
    def test_returns_list_of_opssets(self):
        s = Scene(fps=4)
        s.add(make_sketch(start=0.0, duration=0.5), make_line())
        result = s.create_event_timeline()
        assert isinstance(result, list)
        assert all(isinstance(f, OpsSet) for f in result)

    def test_frame_count_matches_duration_at_fps(self):
        s = Scene(fps=4)
        s.add(make_sketch(start=0.0, duration=1.0), make_line())
        result = s.create_event_timeline()
        # max_length = ceil(1.0) = 1.0; frames = 0..4 inclusive → 5
        assert len(result) == 5

    def test_max_length_overrides_natural_duration(self):
        s = Scene(fps=4)
        s.add(make_sketch(start=0.0, duration=0.5), make_line())
        result = s.create_event_timeline(max_length=2.0)
        # frame_count = round(2.0 * 4) = 8; range(0, 9) → 9
        assert len(result) == 9

    def test_frame_before_creation_is_empty(self):
        s = Scene(fps=4)
        s.add(SketchAnimation(start_time=0.5, duration=0.5), make_line())
        result = s.create_event_timeline()
        # frame 0 → t=0.0s; object appears at 0.5s → nothing drawn yet
        assert len(result[0].opsset) == 0

    def test_frame_after_completion_is_non_empty(self):
        s = Scene(fps=4)
        s.add(SketchAnimation(start_time=0.0, duration=0.5), make_line())
        result = s.create_event_timeline()
        # last frame → object fully drawn
        assert len(result[-1].opsset) > 0

    def test_two_objects_both_in_final_frame(self):
        s = Scene(fps=4)
        s.add(make_sketch(start=0.0, duration=0.5), make_line())
        s.add(make_sketch(start=0.0, duration=0.5), make_rect())
        result = s.create_event_timeline()
        assert len(result[-1].opsset) > 0

    def test_static_cache_hit_on_second_timeline(self):
        # Run timeline twice; the second run should read from drawable_cache for
        # completed frames (no assertion on internal state, just that it doesn't error
        # and returns the same frame count).
        s = Scene(fps=4)
        s.add(make_sketch(start=0.0, duration=0.5), make_line())
        result1 = s.create_event_timeline()
        result2 = s.create_event_timeline()
        assert len(result1) == len(result2)

    def test_object_deleted_disappears_from_later_frames(self):
        s = Scene(fps=4)
        line = make_line()
        s.add(make_sketch(start=0.0, duration=0.5), line)
        s.add(AnimationEvent(AnimationEventType.DELETION, start_time=1.0, duration=0.0), line)
        result = s.create_event_timeline(max_length=2.0)
        # frame at t=1.5s (index 6) should be empty — object deleted at t=1.0
        assert len(result[6].opsset) == 0


# ---------------------------------------------------------------------------
# render_snapshot
# ---------------------------------------------------------------------------

class TestRenderSnapshot:
    def test_creates_svg_file(self, tmp_path):
        s = Scene(width=400, height=300, fps=4)
        s.add(make_sketch(start=0.0, duration=0.5), make_line())
        out = str(tmp_path / "snap.svg")
        s.render_snapshot(out, frame_in_seconds=0.5)
        assert os.path.exists(out)

    def test_svg_file_is_non_empty(self, tmp_path):
        s = Scene(width=400, height=300, fps=4)
        s.add(make_sketch(start=0.0, duration=0.5), make_line())
        out = str(tmp_path / "snap.svg")
        s.render_snapshot(out, frame_in_seconds=0.5)
        assert os.path.getsize(out) > 0

    def test_snapshot_at_zero_seconds(self, tmp_path):
        s = Scene(width=400, height=300, fps=4)
        s.add(make_sketch(start=0.0, duration=0.5), make_line())
        out = str(tmp_path / "snap0.svg")
        s.render_snapshot(out, frame_in_seconds=0.0)
        assert os.path.exists(out)

    def test_snapshot_beyond_end_clamps_gracefully(self, tmp_path):
        s = Scene(width=400, height=300, fps=4)
        s.add(make_sketch(start=0.0, duration=0.5), make_line())
        out = str(tmp_path / "snapclamp.svg")
        s.render_snapshot(out, frame_in_seconds=999.0)
        assert os.path.exists(out)

    def test_snapshot_with_custom_max_length(self, tmp_path):
        s = Scene(width=400, height=300, fps=4)
        s.add(make_sketch(start=0.0, duration=0.5), make_line())
        out = str(tmp_path / "snapmax.svg")
        s.render_snapshot(out, frame_in_seconds=1.0, max_length=2.0)
        assert os.path.exists(out)
