"""Model Context Protocol (MCP) server for handanim.

Enables Claude Code, Claude Desktop, Cursor, and Gemini to natively inspect,
lint, compile, snapshot, and generate handanim whiteboard animations.
"""

import base64
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .assets import get_available_assets
from .compiler import plan_to_python
from .diagnostics import check_code
from .pipeline import AnimationGenerator


class HandanimMCPServer:
    """Stdio-based JSON-RPC 2.0 Model Context Protocol Server."""

    SERVER_NAME = "handanim-mcp"
    SERVER_VERSION = "0.1.0"
    PROTOCOL_VERSION = "2024-11-05"

    def __init__(self):
        self.tools = {
            "render_snapshot": {
                "description": "Render a single keyframe snapshot of a handanim animation script at time 't' and return the image (base64 PNG) directly for visual inspection.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "script_path": {
                            "type": "string",
                            "description": "Absolute or relative path to the Python animation script",
                        },
                        "time": {"type": "number", "description": "Timestamp in seconds to render", "default": 1.0},
                        "output_path": {"type": "string", "description": "Optional output image path (.png or .svg)"},
                    },
                    "required": ["script_path"],
                },
            },
            "introspect_scene": {
                "description": "Headlessly inspect a handanim script to analyze layout, bounding boxes, off-screen viewport clipping, and event timing collisions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "script_path": {"type": "string", "description": "Path to the Python animation script"},
                        "max_length": {"type": "number", "description": "Optional max duration override"},
                    },
                    "required": ["script_path"],
                },
            },
            "lint_script": {
                "description": "Run AST guardrails and static analysis on handanim code. Catches unassigned immutable transforms, deprecated imports, and syntax errors.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Python source code string"},
                        "script_path": {
                            "type": "string",
                            "description": "Path to Python script (alternative to 'code')",
                        },
                    },
                },
            },
            "list_assets": {
                "description": "List all available typography fonts (TTF, custom stroke JSON, Hershey), standard named colors, and bundled media assets.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            "compile_plan_to_code": {
                "description": "Compile a structured ScenePlan specification dictionary into canonical, executable handanim Python code.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "scene_plan": {"type": "object", "description": "ScenePlan JSON object"},
                        "output_path": {"type": "string", "description": "Video output path", "default": "output.mp4"},
                    },
                    "required": ["scene_plan"],
                },
            },
            "generate_animation": {
                "description": "Autonomously generate an animation from a natural language topic using AI, complete with self-correction.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "Topic or explanation request"},
                        "output_path": {"type": "string", "description": "Target video path", "default": "output.mp4"},
                        "use_compiler": {
                            "type": "boolean",
                            "description": "Whether to use deterministic compiler",
                            "default": True,
                        },
                    },
                    "required": ["topic"],
                },
            },
        }

    def run(self):
        """Main stdio loop reading JSON-RPC requests."""
        sys.stderr.write(
            f"[{self.SERVER_NAME} v{self.SERVER_VERSION}] MCP server started on stdio (JSON-RPC 2.0).\n"
            f"Waiting for client connection... (Press Ctrl+C to stop)\n"
        )
        sys.stderr.flush()

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                method = request.get("method", "unknown")
                sys.stderr.write(f"[{self.SERVER_NAME}] Received request: {method}\n")
                sys.stderr.flush()

                response = self.handle_request(request)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except Exception as e:
                err_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": f"Internal error: {e}"},
                }
                sys.stdout.write(json.dumps(err_response) + "\n")
                sys.stdout.flush()

    def handle_request(self, req: dict[str, Any]) -> dict[str, Any] | None:
        msg_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": self.PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": self.SERVER_NAME,
                        "version": self.SERVER_VERSION,
                    },
                },
            }

        elif method == "notifications/initialized":
            return None

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        elif method == "tools/list":
            tool_list = [
                {
                    "name": name,
                    "description": meta["description"],
                    "inputSchema": meta["inputSchema"],
                }
                for name, meta in self.tools.items()
            ]
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tool_list}}

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})
            try:
                content = self.call_tool(tool_name, args)
                return {"jsonrpc": "2.0", "id": msg_id, "result": {"content": content}}
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Tool error ({tool_name}): {e}"}],
                        "isError": True,
                    },
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method '{method}' not found"},
            }

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> list[dict[str, Any]]:
        """Dispatch tool calls and format MCP tool response content."""
        if tool_name == "list_assets":
            assets = get_available_assets()
            return [{"type": "text", "text": json.dumps(assets, indent=2)}]

        elif tool_name == "lint_script":
            code = args.get("code")
            script_path = args.get("script_path")
            if not code and script_path:
                code = Path(script_path).read_text(encoding="utf-8")
            if not code:
                return [{"type": "text", "text": "Error: Either 'code' or 'script_path' must be provided."}]

            diag = check_code(code)
            return [{"type": "text", "text": json.dumps(diag.to_dict(), indent=2)}]

        elif tool_name == "compile_plan_to_code":
            scene_plan = args.get("scene_plan", {})
            output_path = args.get("output_path", "output.mp4")
            code = plan_to_python(scene_plan, output_path=output_path)
            return [{"type": "text", "text": code}]

        elif tool_name == "introspect_scene":
            script_path = args.get("script_path")
            max_length = args.get("max_length")
            if not script_path or not os.path.exists(script_path):
                return [{"type": "text", "text": f"Error: script file '{script_path}' not found."}]

            # Execute a short runner that imports the script, calls scene.introspect() and prints JSON
            runner_code = f"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path('{os.path.abspath(script_path)}').parent))
import importlib.util
spec = importlib.util.spec_from_file_location("user_scene", "{os.path.abspath(script_path)}")
mod = importlib.util.module_from_spec(spec)
# Patch scene.render to be a no-op during introspection
from handanim import Scene
orig_render = Scene.render
Scene.render = lambda *args, **kwargs: None
try:
    spec.loader.exec_module(mod)
    scene_obj = getattr(mod, 'scene', None)
    if not scene_obj:
        for val in mod.__dict__.values():
            if isinstance(val, Scene):
                scene_obj = val
                break
    if scene_obj:
        print("---JSON_START---")
        print(json.dumps(scene_obj.introspect(max_length={max_length})))
        print("---JSON_END---")
    else:
        print("ERROR: No 'scene' variable found in script.")
finally:
    Scene.render = orig_render
"""
            proc = subprocess.run([sys.executable, "-c", runner_code], capture_output=True, text=True)
            if "---JSON_START---" in proc.stdout:
                json_str = proc.stdout.split("---JSON_START---")[1].split("---JSON_END---")[0].strip()
                return [{"type": "text", "text": json_str}]
            return [{"type": "text", "text": f"Introspection output:\n{proc.stdout}\nErrors:\n{proc.stderr}"}]

        elif tool_name == "render_snapshot":
            script_path = args.get("script_path")
            t = float(args.get("time", 1.0))
            output_path = args.get("output_path") or f"snapshot_{t:.1f}.png"

            if not script_path or not os.path.exists(script_path):
                return [{"type": "text", "text": f"Error: script file '{script_path}' not found."}]

            runner_code = f"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path('{os.path.abspath(script_path)}').parent))
import importlib.util
spec = importlib.util.spec_from_file_location("user_scene", "{os.path.abspath(script_path)}")
mod = importlib.util.module_from_spec(spec)
from handanim import Scene
orig_render = Scene.render
Scene.render = lambda *args, **kwargs: None
try:
    spec.loader.exec_module(mod)
    scene_obj = getattr(mod, 'scene', None)
    if not scene_obj:
        for val in mod.__dict__.values():
            if isinstance(val, Scene):
                scene_obj = val
                break
    if scene_obj:
        scene_obj.render_snapshot('{os.path.abspath(output_path)}', frame_in_seconds={t})
        print("SNAPSHOT_SUCCESS")
    else:
        print("ERROR: No scene object found.")
finally:
    Scene.render = orig_render
"""
            proc = subprocess.run([sys.executable, "-c", runner_code], capture_output=True, text=True)
            if "SNAPSHOT_SUCCESS" in proc.stdout and os.path.exists(output_path):
                content = [{"type": "text", "text": f"Snapshot rendered successfully to {output_path} at t={t}s"}]
                if output_path.lower().endswith(".png"):
                    with open(output_path, "rb") as f:
                        b64_data = base64.b64encode(f.read()).decode("utf-8")
                    content.append(
                        {
                            "type": "image",
                            "data": b64_data,
                            "mimeType": "image/png",
                        }
                    )
                return content
            return [{"type": "text", "text": f"Failed to render snapshot:\n{proc.stdout}\n{proc.stderr}"}]

        elif tool_name == "generate_animation":
            topic = args.get("topic", "")
            output_path = args.get("output_path", "output.mp4")
            use_compiler = args.get("use_compiler", True)
            generator = AnimationGenerator()
            result = generator.generate(topic=topic, output_path=output_path, use_compiler=use_compiler)
            return [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "success": result.success,
                            "output_path": result.output_path,
                            "retries_used": result.retries_used,
                            "error": result.error,
                            "code": result.code,
                        },
                        indent=2,
                    ),
                }
            ]

        else:
            raise ValueError(f"Unknown tool '{tool_name}'")


def main():
    """CLI entry point for handanim MCP server."""
    server = HandanimMCPServer()
    server.run()


if __name__ == "__main__":
    main()
