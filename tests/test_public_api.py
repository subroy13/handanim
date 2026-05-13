"""Verify that all symbols listed in handanim.__all__ are importable."""

import handanim


def test_all_symbols_importable():
    for name in handanim.__all__:
        obj = getattr(handanim, name)
        assert obj is not None, f"{name} resolved to None"


def test_top_level_import_shorthand():
    from handanim import Scene, Rectangle, SketchAnimation, StrokeStyle, SketchStyle
    assert all(cls is not None for cls in [Scene, Rectangle, SketchAnimation, StrokeStyle, SketchStyle])


def test_all_exports_are_callable_classes():
    for name in handanim.__all__:
        obj = getattr(handanim, name)
        assert callable(obj), f"{name} is not callable"
