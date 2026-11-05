"""Unit tests for the ScenePlan to Python deterministic compiler."""

import ast

from aianim.compiler import plan_to_python
from aianim.schema import AnimationSpec, DrawableSpec, ScenePlan, SceneSpec


def test_plan_to_python_compilation():
    plan = ScenePlan(
        title="Pythagoras",
        total_duration=5.0,
        scenes=[
            SceneSpec(
                id=1,
                title="Triangle",
                duration=3.0,
                drawables=[
                    DrawableSpec(
                        id="rect_a",
                        type="Rectangle",
                        params={"x": 200, "y": 300, "width": 150, "height": 100},
                        styles={"color": "BLUE", "width": 3, "fill_color": "RED"},
                    ),
                    DrawableSpec(
                        id="txt_title",
                        type="Text",
                        params={"text": "Hello Handanim", "x": 500, "y": 200},
                        styles={"color": "BLACK"},
                    ),
                ],
                animations=[
                    AnimationSpec(drawable_id="rect_a", type="SketchAnimation", start_time=0.0, duration=1.5),
                    AnimationSpec(drawable_id="txt_title", type="FadeInAnimation", start_time=1.5, duration=1.0),
                ],
            )
        ],
    )

    code = plan_to_python(plan, output_path="test_out.mp4")

    # Verify code is syntactically valid Python
    tree = ast.parse(code)
    assert tree is not None

    # Verify key elements
    assert "from handanim import" in code
    assert "Rectangle" in code
    assert "SketchAnimation" in code
    assert "FadeInAnimation" in code
    assert "scene = Scene(width=1920, height=1088)" in code
    assert "rect_a = Rectangle(" in code
    assert "scene.add(event=SketchAnimation" in code
    assert 'scene.render("test_out.mp4", max_length=5.0)' in code
