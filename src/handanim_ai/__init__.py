"""handanim_ai: AI generation pipeline, MCP server, and agentic toolkit for handanim."""

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from .assets import format_assets_markdown, get_available_assets
from .compiler import plan_to_python
from .diagnostics import DiagnosticReport, check_code
from .executor import CodeExecutor, ExecutionResult
from .interactive import InteractiveSession
from .mcp_server import HandanimMCPServer
from .models import (
    BaseLLMModel,
    BedrockModel,
    MockModel,
    OpenRouterModel,
    get_model,
)
from .pipeline import AnimationGenerator, PipelineResult
from .prompts.prompt_manager import PromptManager
from .schema import AnimationSpec, DrawableSpec, ScenePlan, SceneSpec

__all__ = [
    # Schema & Compiler
    "ScenePlan",
    "SceneSpec",
    "DrawableSpec",
    "AnimationSpec",
    "plan_to_python",
    # Diagnostics & Linter
    "check_code",
    "DiagnosticReport",
    # Interactive CLI Session
    "InteractiveSession",
    # Execution & Pipeline
    "AnimationGenerator",
    "PipelineResult",
    "CodeExecutor",
    "ExecutionResult",
    # Models
    "BaseLLMModel",
    "BedrockModel",
    "OpenRouterModel",
    "MockModel",
    "get_model",
    # Assets & Prompts
    "PromptManager",
    "get_available_assets",
    "format_assets_markdown",
    # MCP Server
    "HandanimMCPServer",
]

