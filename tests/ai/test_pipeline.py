"""Unit tests for the AnimationGenerator pipeline and self-correction feedback loop."""

import tempfile

from aianim.executor import CodeExecutor
from aianim.models import MockModel
from aianim.pipeline import AnimationGenerator
from aianim.prompts.prompt_manager import PromptManager


def test_prompt_manager_discovery_and_formatting():
    pm = PromptManager()
    prompts = pm.list_prompts()
    assert len(prompts) >= 2

    bp = pm.get("big_picture", version="v1")
    assert bp.version == "1.0"
    sys_msg, user_msg = bp.format(topic="Pythagoras", assets="Sample Assets")
    assert "Pythagoras" in user_msg
    assert "Sample Assets" in user_msg


def test_code_executor_success_and_failure():
    executor = CodeExecutor(default_timeout=10.0)

    # Success case
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        target_file = f.name

    valid_code = f"""
with open("{target_file}", "w") as f:
    f.write("done")
"""
    res = executor.execute(valid_code, expected_output=target_file)
    assert res.success is True
    assert res.returncode == 0

    # Runtime error case
    broken_code = "raise RuntimeError('Deliberate test error')"
    err_res = executor.execute(broken_code)
    assert err_res.success is False
    assert err_res.returncode != 0
    assert "Deliberate test error" in err_res.error_summary


def test_pipeline_generate_with_mock_and_retry():
    # Model that outputs valid ScenePlan on step 1, but faulty python code on step 2,
    # then self-corrects on retry step 3!
    scene_json = """{
        "title": "Mock Theorem",
        "scenes": [
            {
                "id": 1,
                "title": "Intro",
                "duration": 2.0,
                "drawables": [{"id": "r1", "type": "Rectangle", "params": {"width": 100, "height": 50}}],
                "animations": [{"drawable_id": "r1", "type": "SketchAnimation", "start_time": 0.0, "duration": 1.0}]
            }
        ]
    }"""

    # First codegen has an unassigned immutable transform:
    faulty_code = """
from handanim import Scene, Rectangle, SketchAnimation
scene = Scene()
r1 = Rectangle(width=100, height=50)
r1.translate(10, 10)  # Linter will fail this!
scene.add(SketchAnimation(), r1)
scene.render("out.svg")
"""

    # Corrected code creates the expected output file
    corrected_code = """
with open("out.svg", "w") as f:
    f.write("<svg></svg>")
"""

    mock = MockModel(responses=[scene_json, faulty_code, corrected_code])
    generator = AnimationGenerator(model=mock)

    result = generator.generate(topic="Test", output_path="out.svg", max_retries=2)
    assert result.success is True
    assert result.retries_used == 1  # Successfully self-corrected!
