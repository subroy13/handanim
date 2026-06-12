from handanim.primitives.math import Math
from handanim.primitives.text import Text
from handanim.core.draw_ops import OpsType
from handanim.stylings.fonts import get_font_info, list_fonts

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

