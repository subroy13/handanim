from pathlib import Path

import pytest

from handanim.core.draw_ops import OpsType
from handanim.primitives.math import Math
from handanim.primitives.text import Text
from handanim.stylings.fonts import get_font_info, get_font_path, list_fonts


def test_list_fonts():
    fonts = list_fonts()
    assert "feasibly" in fonts
    assert "hershey_mathlow" in fonts

def test_get_font_info():
    ttf_font = get_font_info("feasibly")
    assert ttf_font is not None
    assert ttf_font["type"] == "ttf"
    assert "file" in ttf_font

    hershey_font = get_font_info("hershey_mathlow")
    assert hershey_font is not None
    assert hershey_font["type"] == "hershey"
    assert "name" in hershey_font


@pytest.mark.parametrize("font_name", ["feasibly", "backstay", "handanimtype1", "noto_sans_math"])
def test_get_font_path_resolves_bundled_package_resources(font_name):
    font_path = Path(get_font_path(font_name))
    assert font_path.is_file(), f"Bundled font {font_name} not found at {font_path}"
    assert "handanim" in font_path.parts and "fonts" in font_path.parts


def test_get_font_path_rejects_hershey_and_unknown():
    with pytest.raises(ValueError):
        get_font_path("hershey_mathlow")
    with pytest.raises(ValueError):
        get_font_path("nonexistent_font")

def test_math_primitive():
    # Test that standard rendering works
    math_primitive = Math(
        tex_expression=r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
        position=(100, 100),
        font_size=24,
    )
    ops = math_primitive.draw()
    assert len(ops.opsset) > 0, "Math drawing returned empty operations set"

    # Verify that the operations are valid
    has_move = False
    for op in ops.opsset:
        if op.type == OpsType.MOVE_TO:
            has_move = True
            break
    assert has_move, "Math drawing should contain MOVE_TO operations"

def test_text_primitive():
    text_primitive = Text(
        text="Hello World",
        position=(200, 200),
        font_size=32,
    )
    ops = text_primitive.draw()
    assert len(ops.opsset) > 0, "Text drawing returned empty operations set"


def test_text_respects_font_name_and_fallback():
    backstay_text = Text("Hello", position=(0, 0), font_size=24, font_name="backstay")
    choice, path = backstay_text.get_random_font_choice()
    assert choice == "backstay"
    assert path == get_font_path("backstay")

    fallback_text = Text("Hello", position=(0, 0), font_size=24, font_name="unknown_font")
    fallback_choice, _ = fallback_text.get_random_font_choice()
    assert fallback_choice == "feasibly"

def test_hershey_math_primitive():
    # Test that Hershey fonts mapping works
    math_primitive = Math(
        tex_expression=r"\alpha \pm \beta",
        position=(100, 100),
        font_size=24,
        font_name="hershey_mathlow",
    )
    ops = math_primitive.draw()
    assert len(ops.opsset) > 0, "Hershey Math drawing returned empty operations set"


@pytest.mark.parametrize("expression", [r"$\triangle$", r"$\angle$", r"$\sim$"])
def test_hershey_geometry_symbols_have_visible_strokes(expression):
    # Previously these glyphs silently disappeared from rendered proofs.
    ops = Math(expression, (0, 0), font_size=24, font_name="hershey_rowmans").draw()
    assert any(op.type in (OpsType.LINE_TO, OpsType.CURVE_TO) for op in ops.opsset)
    bbox = ops.get_bbox()
    assert bbox.width > 0 and bbox.height > 0


def test_hershey_lowercase_g_and_y_descenders():
    math_obj = Math(
        r"$\mathrm{everyone\ yogurt}$",
        (0, 0),
        font_size=30,
        font_name="hershey_rowmans",
    )
    _, h_e, _ = math_obj.get_glyph_opsset(ord("e"), 30)
    _, h_g, _ = math_obj.get_glyph_opsset(ord("g"), 30)
    _, h_y, _ = math_obj.get_glyph_opsset(ord("y"), 30)
    _, h_9, _ = math_obj.get_glyph_opsset(ord("9"), 30)
    _, h_Y, _ = math_obj.get_glyph_opsset(ord("Y"), 30)
    # Lowercase g and y must have the same x-height ascent as 'e', not cap-height like '9' or 'Y'.
    assert h_g == pytest.approx(h_e, abs=1.0)
    assert h_y == pytest.approx(h_e, abs=1.0)
    assert h_g < h_9 - 5.0
    assert h_y < h_Y - 5.0


def test_hershey_hyphen_and_apostrophe():
    # U+2212 minus / hyphen in GLP-1 must sit at mid-height, not on the baseline.
    glp = Math(r"$\mathrm{GLP-1}$", (0, 0), font_size=30, font_name="hershey_rowmans")
    _, h_G, _ = glp.get_glyph_opsset(ord("G"), 30)
    _, h_minus, _ = glp.get_glyph_opsset(0x2212, 30)
    assert h_minus > 0.3 * h_G

    # Straight and curly apostrophes must render visible strokes near cap-height.
    for expr in [r"$\mathrm{everyone's}$", "everyone's", "everyone\u2019s", r"$\mathrm{everyone’s}$"]:
        m = Math(expr, (0, 0), font_size=30, font_name="hershey_rowmans")
        ops_with_apos = m.draw()
        ops_without = Math(r"$\mathrm{everyones}$", (0, 0), font_size=30, font_name="hershey_rowmans").draw()
        assert len(ops_with_apos.opsset) > len(ops_without.opsset)


