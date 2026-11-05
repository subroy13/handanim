"""Unit tests for the HandanimMCPServer JSON-RPC protocol implementation."""

import json

from aianim.mcp_server import HandanimMCPServer


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


def test_mcp_voice_tools_listed():
    server = HandanimMCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/list",
        "params": {},
    }
    resp = server.handle_request(req)
    tool_names = [t["name"] for t in resp["result"]["tools"]]
    assert "list_voices" in tool_names
    assert "synthesize_narration" in tool_names
    assert "get_word_timestamps" in tool_names
    assert "mux_video_audio" in tool_names


def test_mcp_list_voices():
    server = HandanimMCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "list_voices",
            "arguments": {},
        },
    }
    resp = server.handle_request(req)
    data = json.loads(resp["result"]["content"][0]["text"])
    assert data["default_provider"] == "kokoro"
    assert list(data["providers"].keys()) == ["kokoro"]
    assert "af_heart" in data["providers"]["kokoro"]["voices"]


def test_mcp_synthesize_and_timestamps(tmp_path):
    server = HandanimMCPServer()
    out_wav = str(tmp_path / "voice_mcp.wav")
    req = {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {
            "name": "synthesize_narration",
            "arguments": {
                "text": "Hello world from MCP",
                "provider": "mock",
                "output_path": out_wav,
            },
        },
    }
    resp = server.handle_request(req)
    assert not resp["result"].get("isError")
    res = json.loads(resp["result"]["content"][0]["text"])
    assert res["word_count"] == 4
    assert res["duration"] > 0

    req_align = {
        "jsonrpc": "2.0",
        "id": 8,
        "method": "tools/call",
        "params": {
            "name": "get_word_timestamps",
            "arguments": {
                "text": "Hello world from MCP",
                "provider": "mock",
            },
        },
    }
    resp_align = server.handle_request(req_align)
    res_align = json.loads(resp_align["result"]["content"][0]["text"])
    assert len(res_align["words"]) == 4
    assert res_align["words"][0]["word"] == "Hello"
    assert res_align["words"][0]["start"] >= 0.0


def test_mcp_mux_video_audio(tmp_path, monkeypatch):
    import aianim.mcp_server as mcp_mod

    server = HandanimMCPServer()
    v_path = tmp_path / "vid.mp4"
    v_path.write_bytes(b"dummy_vid")
    a_path = tmp_path / "aud.wav"
    a_path.write_bytes(b"dummy_aud")
    out_path = str(tmp_path / "muxed.mp4")

    monkeypatch.setattr(mcp_mod, "mix_audio_with_video", lambda **kw: out_path)

    req = {
        "jsonrpc": "2.0",
        "id": 9,
        "method": "tools/call",
        "params": {
            "name": "mux_video_audio",
            "arguments": {
                "video_path": str(v_path),
                "audio_path": str(a_path),
                "output_path": out_path,
            },
        },
    }
    resp = server.handle_request(req)
    assert not resp["result"].get("isError")
    res = json.loads(resp["result"]["content"][0]["text"])
    assert res["success"] is True
    assert res["output_path"] == out_path


