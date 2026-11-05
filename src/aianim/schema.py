"""Structured scene representation and validation schema for AI-assisted animation."""

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DrawableSpec:
    """Specification for a visual shape or element."""

    id: str
    type: str  # e.g., 'Rectangle', 'Text', 'Math', 'Circle', 'Line', 'Arrow'
    params: dict[str, Any] = field(default_factory=dict)
    styles: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DrawableSpec":
        return cls(
            id=str(data.get("id", "")),
            type=str(data.get("type", "Rectangle")),
            params=dict(data.get("params", {})),
            styles=dict(data.get("styles", {})),
        )


@dataclass
class AnimationSpec:
    """Specification for an animation applied to a drawable."""

    drawable_id: str
    type: str  # e.g., 'SketchAnimation', 'FadeInAnimation', 'TranslateToAnimation'
    start_time: float = 0.0
    duration: float = 1.0
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnimationSpec":
        try:
            start_time = float(data.get("start_time", 0.0))
        except (ValueError, TypeError):
            digits = "".join(ch for ch in str(data.get("start_time", "")) if ch.isdigit() or ch == ".")
            start_time = float(digits) if digits else 0.0

        try:
            duration = float(data.get("duration", 1.0))
        except (ValueError, TypeError):
            digits = "".join(ch for ch in str(data.get("duration", "")) if ch.isdigit() or ch == ".")
            duration = float(digits) if digits else 1.0

        return cls(
            drawable_id=str(data.get("drawable_id", "")),
            type=str(data.get("type", "SketchAnimation")),
            start_time=start_time,
            duration=duration,
            params=dict(data.get("params", {})),
        )


@dataclass
class SceneSpec:
    """Specification for an individual scene segment."""

    id: int | str = 1
    title: str = ""
    duration: float = 5.0
    drawables: list[DrawableSpec] = field(default_factory=list)
    animations: list[AnimationSpec] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SceneSpec":
        raw_id = data.get("id", 1)
        try:
            scene_id: int | str = int(raw_id)
        except (ValueError, TypeError):
            digits = "".join(ch for ch in str(raw_id) if ch.isdigit())
            scene_id = int(digits) if digits else str(raw_id)

        try:
            duration = float(data.get("duration", 5.0))
        except (ValueError, TypeError):
            digits = "".join(ch for ch in str(data.get("duration", "")) if ch.isdigit() or ch == ".")
            duration = float(digits) if digits else 5.0

        drawables = [DrawableSpec.from_dict(d) if isinstance(d, dict) else d for d in data.get("drawables", [])]
        animations = [AnimationSpec.from_dict(a) if isinstance(a, dict) else a for a in data.get("animations", [])]
        return cls(
            id=scene_id,
            title=str(data.get("title", "")),
            duration=duration,
            drawables=drawables,
            animations=animations,
        )


@dataclass
class ScenePlan:
    """Complete structured plan for a multi-scene handanim animation."""

    title: str
    description: str = ""
    total_duration: float = 0.0
    width: int = 1920
    height: int = 1088
    scenes: list[SceneSpec] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScenePlan":
        scenes = [SceneSpec.from_dict(s) if isinstance(s, dict) else s for s in data.get("scenes", [])]
        try:
            total_duration = float(data.get("total_duration", 0.0))
        except (ValueError, TypeError):
            total_duration = 0.0

        if total_duration <= 0 and scenes:
            total_duration = sum(s.duration for s in scenes)

        return cls(
            title=str(data.get("title", "Untitled Animation")),
            description=str(data.get("description", "")),
            total_duration=total_duration,
            width=int(data.get("width", 1920)),
            height=int(data.get("height", 1088)),
            scenes=scenes,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, json_str: str) -> "ScenePlan":
        """Parse from JSON string, handling optional markdown fence wrapping."""
        cleaned = json_str.strip()
        if "```" in cleaned:
            import re

            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
            if match:
                cleaned = match.group(1).strip()
        data = json.loads(cleaned)
        return cls.from_dict(data)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def validate(self) -> list[str]:
        """Validate structure and return list of validation warning/error messages."""
        issues: list[str] = []
        if not self.scenes:
            issues.append("ScenePlan contains no scenes.")

        seen_drawables: set[str] = set()
        for scene in self.scenes:
            for d in scene.drawables:
                if not d.id:
                    issues.append(f"Drawable in scene {scene.id} is missing an 'id'.")
                elif d.id in seen_drawables:
                    issues.append(f"Duplicate drawable id '{d.id}' across scenes.")
                else:
                    seen_drawables.add(d.id)

            for a in scene.animations:
                if not a.drawable_id:
                    issues.append(f"Animation in scene {scene.id} missing target 'drawable_id'.")
                elif a.drawable_id not in seen_drawables:
                    issues.append(f"Animation in scene {scene.id} references undefined drawable '{a.drawable_id}'.")
                if a.duration < 0:
                    issues.append(f"Animation on '{a.drawable_id}' has negative duration {a.duration}.")
                if a.start_time < 0:
                    issues.append(f"Animation on '{a.drawable_id}' has negative start_time {a.start_time}.")

        return issues

    @classmethod
    def get_json_schema(cls) -> dict[str, Any]:
        """Return the OpenAPI / JSON Schema definition for tool-calling."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "ScenePlan",
            "description": "Structured animation specification for handanim whiteboard animations.",
            "type": "object",
            "required": ["title", "scenes"],
            "properties": {
                "title": {"type": "string", "description": "Title of the animation"},
                "description": {"type": "string", "description": "High-level summary of the explanation"},
                "total_duration": {"type": "number", "description": "Total length of video in seconds"},
                "width": {"type": "integer", "default": 1920},
                "height": {"type": "integer", "default": 1088},
                "scenes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "drawables", "animations"],
                        "properties": {
                            "id": {"type": "integer", "description": "Scene index (1-based)"},
                            "title": {"type": "string", "description": "Scene title/heading"},
                            "duration": {"type": "number", "description": "Scene duration in seconds"},
                            "drawables": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["id", "type"],
                                    "properties": {
                                        "id": {"type": "string", "description": "Unique identifier, e.g. 'title_text'"},
                                        "type": {
                                            "type": "string",
                                            "enum": [
                                                "Rectangle",
                                                "Square",
                                                "RoundedRectangle",
                                                "RoundedSquare",
                                                "Circle",
                                                "Ellipse",
                                                "Polygon",
                                                "Line",
                                                "LinearPath",
                                                "Arrow",
                                                "CurvedArrow",
                                                "Curve",
                                                "Text",
                                                "Math",
                                                "Eraser",
                                                "FlowchartNode",
                                                "FlowchartDiamond",
                                                "FlowchartConnector",
                                                "Table",
                                            ],
                                        },
                                        "params": {
                                            "type": "object",
                                            "description": "Coordinates and shape arguments (world space 0..1777, 0..1000)",
                                        },
                                        "styles": {
                                            "type": "object",
                                            "description": "Color, stroke width, fill, and roughness settings",
                                        },
                                    },
                                },
                            },
                            "animations": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["drawable_id", "type", "start_time", "duration"],
                                    "properties": {
                                        "drawable_id": {"type": "string"},
                                        "type": {
                                            "type": "string",
                                            "enum": [
                                                "SketchAnimation",
                                                "FadeInAnimation",
                                                "FadeOutAnimation",
                                                "ZoomInAnimation",
                                                "ZoomOutAnimation",
                                                "TranslateToAnimation",
                                                "TranslateFromAnimation",
                                                "RotateAnimation",
                                                "ColorTransitionAnimation",
                                            ],
                                        },
                                        "start_time": {"type": "number"},
                                        "duration": {"type": "number"},
                                        "params": {"type": "object"},
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }
