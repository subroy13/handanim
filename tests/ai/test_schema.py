"""Unit tests for ScenePlan schema, validation, and JSON export."""

from aianim.schema import AnimationSpec, DrawableSpec, ScenePlan, SceneSpec


def test_schema_serialization():
    d1 = DrawableSpec(id="rect_1", type="Rectangle", params={"width": 100, "height": 50})
    a1 = AnimationSpec(drawable_id="rect_1", type="SketchAnimation", start_time=0.0, duration=2.0)
    s1 = SceneSpec(id=1, title="Intro", duration=3.0, drawables=[d1], animations=[a1])
    plan = ScenePlan(title="Test Plan", scenes=[s1])

    data = plan.to_dict()
    assert data["title"] == "Test Plan"
    assert len(data["scenes"]) == 1
    assert data["scenes"][0]["drawables"][0]["id"] == "rect_1"

    json_str = plan.to_json()
    restored = ScenePlan.from_json(json_str)
    assert restored.title == "Test Plan"
    assert restored.scenes[0].drawables[0].type == "Rectangle"
    assert restored.total_duration == 3.0


def test_schema_markdown_codeblock_cleaning():
    json_wrapped = """```json
    {
        "title": "Wrapped Plan",
        "scenes": [
            {
                "id": 1,
                "title": "Scene 1",
                "duration": 2.0,
                "drawables": [{"id": "c1", "type": "Circle"}],
                "animations": [{"drawable_id": "c1", "type": "FadeInAnimation", "start_time": 0.0, "duration": 1.0}]
            }
        ]
    }
    ```"""
    plan = ScenePlan.from_json(json_wrapped)
    assert plan.title == "Wrapped Plan"
    assert len(plan.scenes) == 1


def test_schema_string_scene_id():
    # LLMs frequently return string ids like "scene_1" instead of integer 1
    raw_json = """{
        "title": "String ID Test",
        "scenes": [
            {
                "id": "scene_1",
                "title": "Scene 1",
                "duration": "3s",
                "drawables": [{"id": "d1", "type": "Rectangle"}],
                "animations": [{"drawable_id": "d1", "type": "SketchAnimation", "start_time": "0.5s", "duration": "2.0s"}]
            }
        ]
    }"""
    plan = ScenePlan.from_json(raw_json)
    assert plan.title == "String ID Test"
    assert plan.scenes[0].id == 1
    assert plan.scenes[0].duration == 3.0
    assert plan.scenes[0].animations[0].start_time == 0.5
    assert plan.scenes[0].animations[0].duration == 2.0


def test_schema_validation():
    # Valid plan
    valid_plan = ScenePlan(
        title="Valid",
        scenes=[
            SceneSpec(
                id=1,
                drawables=[DrawableSpec(id="d1", type="Square")],
                animations=[AnimationSpec(drawable_id="d1", type="SketchAnimation", start_time=0.0, duration=1.0)],
            )
        ],
    )
    assert len(valid_plan.validate()) == 0

    # Invalid plan: missing scenes
    empty_plan = ScenePlan(title="Empty")
    assert any("contains no scenes" in err for err in empty_plan.validate())

    # Invalid plan: animation references undefined drawable
    bad_ref_plan = ScenePlan(
        title="Bad Ref",
        scenes=[
            SceneSpec(
                id=1,
                drawables=[DrawableSpec(id="d1", type="Square")],
                animations=[
                    AnimationSpec(drawable_id="d_nonexistent", type="SketchAnimation", start_time=0.0, duration=1.0)
                ],
            )
        ],
    )
    issues = bad_ref_plan.validate()
    assert any("references undefined drawable" in err for err in issues)


def test_json_schema_generation():
    schema = ScenePlan.get_json_schema()
    assert schema["title"] == "ScenePlan"
    assert "scenes" in schema["properties"]
    assert "required" in schema
