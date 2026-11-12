Model Context Protocol (MCP) Server
===================================

``aianim`` includes a built-in **Model Context Protocol (MCP)** stdio server (:mod:`aianim.mcp_server`) so AI coding agents—such as **Claude Desktop**, **Claude Code**, **Cursor**, and **Google Antigravity**—can interactively author, lint, introspect, synthesize voice for, and visually review ``handanim`` animations.

Starting the MCP Server
-----------------------

.. code-block:: bash

   handanim-ai mcp
   # or
   aianim mcp

Configuring in Claude Desktop / Cursor / Antigravity
----------------------------------------------------

Add the following entry to your MCP client configuration (e.g. ``claude_desktop_config.json`` or ``.cursor/mcp.json``):

.. code-block:: json

   {
     "mcpServers": {
       "handanim": {
         "command": "poetry",
         "args": ["run", "handanim-ai", "mcp"],
         "cwd": "/path/to/handanim"
       }
     }
   }

Tools Exposed by the MCP Server
-------------------------------

1. **Code Guardrails & Layout Introspection**

   - ``lint_handanim_code(code)``: Runs :func:`~aianim.diagnostics.check_code` to catch syntax errors, discarded immutable transforms (`obj.translate(...)` without assignment), deprecated imports, and font license warnings before execution.
   - ``introspect_scene_script(code)``: Executes the scene setup headlessly and runs :meth:`~handanim.core.scene.Scene.introspect` to return bounding boxes, viewport clipping warnings, and event timelines for every drawable.

2. **Visual Snapshot & Keyframe Preview**

   - ``render_scene_snapshot(code, time_in_seconds, output_path)``: Renders a single timestamp of a scene script to an SVG or PNG file so the agent can visually inspect layout and spacing.
   - ``list_available_assets()``: Lists all registered fonts (built-in and user-registered) and available SVG/image assets.

3. **Voice Synthesis & Audio Multiplexing (`voiceanim`)**

   - ``list_voices(provider)``: Lists supported voices for ``kokoro``, ``polly``, ``qwen``, and ``mock``.
   - ``synthesize_narration(text, provider, voice, speed, instruct, output_path)``: Synthesizes speech and returns the audio path, duration, and word-level timestamps.
   - ``get_word_timestamps(text, provider, voice)``: Returns exact `(word, start, end)` timings for aligning visual events and :class:`~handanim.primitives.captions.Captions`.
   - ``mux_video_audio(video_path, audio_path, output_path)``: Multiplexes narration or soundtrack audio into an MP4 video.

