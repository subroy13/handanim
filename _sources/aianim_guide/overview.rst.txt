aianim Overview (Agentic Animation Studio)
==========================================

``aianim`` (also accessible via ``handanim_ai`` for backward compatibility) connects ``handanim`` and ``voiceanim`` to Large Language Models and AI coding agents.

Architecture of the ``aianim`` Pipeline
---------------------------------------

.. code-block:: text

   Natural Language Topic ("Explain the Pythagorean theorem")
      │
      ▼
   1. Scene Planner LLM ──► Structured ScenePlan JSON Schema (aianim.schema)
      │
      ├──► 2a. SceneCompiler (Deterministic JSON -> Python Code)
      │          OR
      └──► 2b. Codegen LLM + AST Linter (check_code)
                 │
                 ▼
   3. Self-Healing CodeExecutor (Subprocess Execution + Error Feedback Retry Loop)
      │
      ▼
   4. Rendered Video (.mp4) + SVG Keyframe Snapshots

Key Components
--------------

- **Structured Schema (:mod:`aianim.schema`)**: Defines :class:`~aianim.schema.ScenePlan`, :class:`~aianim.schema.DrawableSpec`, and :class:`~aianim.schema.AnimationSpec` so LLMs plan scenes using a validated JSON structure rather than brittle free-form text.
- **Deterministic Compiler (:class:`~aianim.compiler.SceneCompiler`)**: Compiles a :class:`~aianim.schema.ScenePlan` directly into runnable ``handanim`` Python code without requiring a second LLM call.
- **Self-Correction Executor (:class:`~aianim.executor.CodeExecutor`)**: Runs generated scripts in an isolated subprocess, captures tracebacks, and feeds errors back to the model for automatic repair.
- **Multi-Provider LLM Support (:mod:`aianim.models`)**: Supports **AWS Bedrock** Converse API (`BedrockModel` for Claude 3.5 Sonnet, Amazon Nova, Llama 3), **OpenRouter** (`OpenRouterModel`), and offline **MockModel** (`MockModel`) for testing.
- **MCP Server (:mod:`aianim.mcp_server`)**: Exposes linting, headless scene introspection, snapshot rendering, and voice synthesis tools over the Model Context Protocol (`handanim-ai mcp`).

