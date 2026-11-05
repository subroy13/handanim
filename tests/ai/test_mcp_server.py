"""Unit tests for the HandanimMCPServer JSON-RPC protocol implementation."""

import json

from handanim_ai.mcp_server import HandanimMCPServer


def test_mcp_initialize():
    server = HandanimMCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {},
    }
    resp = server.handle_request(req)
    assert resp["id"] == 1
    assert resp["result"]["serverInfo"]["name"] == "handanim-mcp"
    assert "tools" in resp["result"]["capabilities"]


def test_mcp_tools_list():
    server = HandanimMCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    }
    resp = server.handle_request(req)
    tool_names = [t["name"] for t in resp["result"]["tools"]]
    assert "render_snapshot" in tool_names
    assert "introspect_scene" in tool_names
    assert "lint_script" in tool_names
    assert "list_assets" in tool_names
    assert "compile_plan_to_code" in tool_names


def test_mcp_call_lint_script():
    server = HandanimMCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "lint_script",
            "arguments": {
                "code": "from handanim import Scene\nscene = Scene()\nscene.add(None, None)\nscene.render('out.mp4')"
            },
        },
    }
    resp = server.handle_request(req)
    content = resp["result"]["content"][0]["text"]
    parsed = json.loads(content)
    assert parsed["is_valid"] is True


def test_mcp_assets_report_registered_bundled_fonts():
    content = HandanimMCPServer().call_tool("list_assets", {})
    fonts = json.loads(content[0]["text"])["fonts"]
    assert "feasibly" in fonts["ttf"]
    assert "handanimtype1" in fonts["custom_json"]
    assert "hershey_rowmans" in fonts["hershey"]


def test_mcp_call_compile_plan():
    server = HandanimMCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "compile_plan_to_code",
            "arguments": {
                "scene_plan": {
                    "title": "Compiled",
                    "scenes": [
                        {
                            "id": 1,
                            "drawables": [{"id": "s1", "type": "Square"}],
                            "animations": [
                                {"drawable_id": "s1", "type": "SketchAnimation", "start_time": 0, "duration": 1}
                            ],
                        }
                    ],
                }
            },
        },
    }
    resp = server.handle_request(req)
    code = resp["result"]["content"][0]["text"]
    assert "from handanim import" in code
    assert "s1 = Square(" in code
