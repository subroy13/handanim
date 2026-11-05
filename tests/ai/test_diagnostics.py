"""Unit tests for AST linter and code guardrails."""

from aianim.diagnostics import check_code


def test_diagnostics_valid_code():
    code = """
from handanim import Scene, Rectangle, SketchAnimation
from handanim.stylings.color import BLUE

scene = Scene(width=1920, height=1088)
rect = Rectangle(x=100, y=100, width=200, height=100)
rect = rect.translate(50, 50)
scene.add(event=SketchAnimation(start_time=0.0, duration=2.0), drawable=rect)
scene.render("output.mp4")
"""
    report = check_code(code)
    assert report.is_valid is True
    assert len(report.errors) == 0


def test_diagnostics_unassigned_immutable_transform():
    # Calling rect.translate() as an unassigned statement should trigger an error!
    code = """
from handanim import Scene, Rectangle, SketchAnimation

scene = Scene()
rect = Rectangle(x=100, y=100, width=200, height=100)
rect.translate(50, 50)  # ERROR: discarded return value!
scene.add(SketchAnimation(), rect)
scene.render("out.mp4")
"""
    report = check_code(code)
    assert report.is_valid is False
    assert any("Discarded return value from immutable transform 'rect.translate()'" in e for e in report.errors)


def test_diagnostics_deprecated_svg_import():
    code = """
from handanim.primitives.svg import SVG
from handanim import Scene

scene = Scene()
svg_elem = SVG("file.svg")
scene.add(None, svg_elem)
scene.render("out.mp4")
"""
    report = check_code(code)
    assert report.is_valid is False
    assert any("Deprecated import from 'handanim.primitives.svg'" in e for e in report.errors)


def test_diagnostics_syntax_error():
    code = "def broken_code( : invalid"
    report = check_code(code)
    assert report.is_valid is False
    assert any("SyntaxError" in e for e in report.errors)

