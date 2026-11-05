"""Unit tests for Scene.introspect() and headless diagnostics."""

from handanim import Rectangle, Scene, SketchAnimation, Text


def test_scene_introspect_clean():
    scene = Scene(width=1920, height=1088)
    rect = Rectangle(top_left=(200, 200), width=400, height=300)
    text = Text(text="Test Intro", position=(500, 100))
    scene.add(SketchAnimation(start_time=0.0, duration=2.0), rect)
    scene.add(SketchAnimation(start_time=1.0, duration=1.5), text)

    report = scene.introspect()
    assert report["num_objects"] == 2
    assert report["fps"] == 24
    assert report["duration"] == 3.0  # max keyframe duration
    assert len(report["errors"]) == 0
    # Objects are within (0, 1777) x (0, 1000), so no off-screen warnings
    assert len(report["warnings"]) == 0


def test_scene_introspect_offscreen_warning():
    scene = Scene(width=1920, height=1088)
    # Place object far outside world viewport [0..1777, 0..1000]
    offscreen_rect = Rectangle(top_left=(2500, 2000), width=100, height=100)
    scene.add(SketchAnimation(start_time=0.0, duration=1.0), offscreen_rect)

    report = scene.introspect()
    assert any("completely outside the world viewport" in w for w in report["warnings"])
