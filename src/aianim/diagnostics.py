"""AST guardrails and code linter for agentic workflows and AI-generated scripts."""

import ast
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DiagnosticReport:
    """Diagnostic outcome containing syntax and semantic linter warnings/errors."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HandanimCodeAuditor(ast.NodeVisitor):
    """AST visitor inspecting handanim-specific coding patterns and anti-patterns."""

    IMMUTABLE_TRANSFORMS = {"translate", "scale", "rotate"}

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.suggestions: list[str] = []
        self.has_scene_add = False
        self.has_scene_render = False

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module and ("handanim.primitives.svg" in node.module or node.module.endswith(".svg")):
            self.errors.append(
                f"Line {node.lineno}: Deprecated import from '{node.module}'. "
                "Use 'VectorSVG' (from handanim import VectorSVG) instead of legacy 'SVG'."
            )
            self.suggestions.append("Replace legacy SVG imports with VectorSVG.")

        for alias in node.names:
            if alias.name == "SVG" and node.module and "vector_svg" not in node.module:
                self.warnings.append(f"Line {node.lineno}: 'SVG' is legacy/deprecated. Use 'VectorSVG' instead.")
        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr):
        """Check for standalone function/method calls that discard return values."""
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
            method_name = node.value.func.attr
            if method_name in self.IMMUTABLE_TRANSFORMS:
                target_name = node.value.func.value.id if isinstance(node.value.func.value, ast.Name) else "object"
                self.errors.append(
                    f"Line {node.lineno}: Discarded return value from immutable transform '{target_name}.{method_name}()'. "
                    f"In handanim, drawables are immutable. You must assign the result: '{target_name} = {target_name}.{method_name}(...)'."
                )
                self.suggestions.append(
                    f"Change '{target_name}.{method_name}(...)' to '{target_name} = {target_name}.{method_name}(...)'."
                )

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "add":
                self.has_scene_add = True
            elif node.func.attr in ("render", "render_snapshot", "render_keyframes"):
                self.has_scene_render = True
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, str) and node.value.strip().lower() == "backstay":
            self.warnings.append(
                f"Line {node.lineno}: Font 'backstay' (BackstaySingleLine) is only allowed for personal use. "
                "Use 'feasibly' or another commercial-friendly font for non-personal projects."
            )
            self.suggestions.append(f"Replace 'backstay' on line {node.lineno} with 'feasibly' if used outside personal projects.")
        self.generic_visit(node)


def check_code(code_str: str) -> DiagnosticReport:
    """Run static AST analysis on handanim Python code.

    Args:
        code_str: Source code string to inspect.

    Returns:
        DiagnosticReport with validity flag, errors, warnings, and suggestions.
    """
    errors: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []

    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return DiagnosticReport(
            is_valid=False,
            errors=[f"SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}"],
            warnings=[],
            suggestions=["Fix the Python syntax error."],
        )

    auditor = HandanimCodeAuditor()
    auditor.visit(tree)

    errors.extend(auditor.errors)
    warnings.extend(auditor.warnings)
    suggestions.extend(auditor.suggestions)

    if not auditor.has_scene_add:
        warnings.append("No 'scene.add()' calls detected. Nothing will be animated on screen.")
        suggestions.append("Add drawables to the scene using 'scene.add(event, drawable)'.")

    if not auditor.has_scene_render:
        warnings.append("No 'scene.render()' or snapshot call detected. The animation will not produce output.")
        suggestions.append("Call 'scene.render(\"output.mp4\")' to render the video.")

    is_valid = len(errors) == 0
    return DiagnosticReport(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        suggestions=suggestions,
    )
