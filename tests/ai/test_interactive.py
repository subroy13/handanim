"""Unit tests for the InteractiveSession assistant."""

from handanim_ai.interactive import InteractiveSession
from handanim_ai.models import MockModel
from handanim_ai.schema import ScenePlan


def test_interactive_session_clarification():
    mock = MockModel(responses=["Could you clarify if you prefer a sector/wedge slicing visualization?"])
    session = InteractiveSession(model=mock, verbose=False)

    session.handle_topic_turn("Area of a circle")
    assert len(session.conversation_history) == 2
    assert session.conversation_history[0]["role"] == "user"
    assert session.conversation_history[1]["role"] == "assistant"
    assert "clarify" in session.conversation_history[1]["content"]


def test_interactive_session_direct_plan():
    plan_json = """{
        "title": "Area of a Circle",
        "scenes": [
            {
                "id": "scene_1",
                "title": "Circle",
                "duration": 3.0,
                "drawables": [{"id": "c1", "type": "Circle"}],
                "animations": [{"drawable_id": "c1", "type": "SketchAnimation", "start_time": 0.0, "duration": 2.0}]
            }
        ]
    }"""
    mock = MockModel(responses=["PROCEED_TO_PLAN", plan_json])
    session = InteractiveSession(model=mock, verbose=False)

    session.handle_topic_turn("Draw a circle")
    assert session.current_plan is not None
    assert session.current_plan.title == "Area of a Circle"
    assert session.current_plan.scenes[0].id == 1


def test_prompt_choice_and_text_fallback(monkeypatch):
    session = InteractiveSession(model=MockModel(), verbose=False)

    monkeypatch.setattr("builtins.input", lambda _: "2")
    choice = session.prompt_choice("Choose:", ["Option A", "Option B", "Option C"])
    assert choice == "Option B"

    monkeypatch.setattr("builtins.input", lambda _: "custom input text")
    text = session.prompt_text("Enter text:")
    assert text == "custom input text"


def test_refine_plan():
    initial_plan = ScenePlan.from_dict({
        "title": "Old Plan",
        "scenes": [
            {"id": 1, "title": "S1", "duration": 2.0, "drawables": [], "animations": []}
        ]
    })
    updated_plan_json = """{
        "title": "Refined Plan",
        "scenes": [
            {"id": 1, "title": "S1", "duration": 5.0, "drawables": [], "animations": []}
        ]
    }"""
    mock = MockModel(responses=[updated_plan_json])
    session = InteractiveSession(model=mock, verbose=False)
    session.current_plan = initial_plan

    session.refine_plan("Make it 5 seconds long")
    assert session.current_plan.title == "Refined Plan"
    assert session.current_plan.scenes[0].duration == 5.0
