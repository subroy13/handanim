✍️ handanim Documentation
=========================

.. raw:: html

   <div class="hero-banner">
     <p><strong>handanim</strong> is a Python library and agentic studio for creating whiteboard-style, hand-drawn animations, mathematical proofs, and narrated short-form explainers.</p>
     <p>
       <a href="https://pypi.org/project/handanim/"><img src="https://img.shields.io/pypi/v/handanim.svg" alt="PyPI Version"></a>
       <a href="https://github.com/subroy13/handanim"><img src="https://img.shields.io/github/stars/subroy13/handanim?style=social" alt="GitHub Stars"></a>
       <a href="https://github.com/subroy13/handanim/actions/workflows/docs.yml"><img src="https://github.com/subroy13/handanim/actions/workflows/docs.yml/badge.svg" alt="Docs Status"></a>
     </p>
   </div>

The Unified Whiteboard Ecosystem
--------------------------------

``handanim`` ships three tightly integrated packages in a single installation:

.. raw:: html

   <div class="feature-grid">
     <div class="feature-card">
       <h3>🎨 <code>handanim</code> — Core Visual Engine</h3>
       <p>Hand-sketched geometric primitives, LaTeX &amp; Hershey math, flowcharts, tables, hierarchical 2D character rigs with 2-joint IK, multi-page scene transitions (<code>PageTurnTransition</code> &amp; <code>PaperCrumpleTransition</code>), camera pan/zoom, camera-invariant overlays, and export to MP4, GIF, SVG, PDF, Beamer, and native TikZ.</p>
     </div>
     <div class="feature-card">
       <h3>🎙️ <code>voiceanim</code> — Voice, Music &amp; SFX</h3>
       <p>Word-aligned speech synthesis (Kokoro-82M local TTS, Qwen3-TTS, AWS Polly), word-by-word <code>Captions</code> highlighting, repeating background theme music with speech ducking, and automatic chalk, eraser, page-turn, and paper-crumple sound effects.</p>
     </div>
     <div class="feature-card">
       <h3>🤖 <code>aianim</code> — Agentic Studio &amp; MCP</h3>
       <p>Structured <code>ScenePlan</code> compiler, self-healing execution loop, static AST guardrails (<code>check_code</code>), headless layout/timing introspection (<code>Scene.introspect</code>), and a ready-to-use Model Context Protocol server (<code>handanim-ai mcp</code>).</p>
     </div>
   </div>

Visual Showcase
---------------

.. raw:: html

   <div class="gallery-grid">
     <div class="gallery-item">
       <img src="https://raw.githubusercontent.com/subroy13/handanim/master/examples/output/pythagoras.gif" alt="Pythagoras Theorem Animation">
       <p><strong>Pythagoras Theorem</strong> — Hand-sketched geometry with hachure fills</p>
     </div>
     <div class="gallery-item">
       <img src="https://raw.githubusercontent.com/subroy13/handanim/master/examples/output/a_plus_b_square.gif" alt="(a+b)^2 Visual Proof">
       <p><strong>Algebraic Proof of (a + b)²</strong> — Step-by-step visual derivation</p>
     </div>
   </div>

30-Second Quick Example
-----------------------

Create a hand-drawn scene with narration, word-by-word highlighted captions, repeating background theme music, and automatic chalk drawing and eraser sound effects:

.. code-block:: python

   from handanim import (
       Captions, Circle, Eraser, Math, Scene, SketchAnimation, StrokeStyle, Text,
   )
   from handanim.stylings.color import BLACK, BLUE, RED, TEAL
   from voiceanim import VoiceEngine

   # 1. Synthesize word-timed narration (uses local Kokoro-82M or MockVoiceProvider)
   clip = VoiceEngine.synthesize(
       "Let us sketch a circle and Euler's identity on the whiteboard.",
       provider="kokoro",
       voice="af_heart",
   )

   # 2. Build a 9:16 portrait or 16:9 landscape whiteboard scene
   scene = Scene(width=1080, height=1920, fps=30, background_color=(0.99, 0.98, 0.95))
   scene.set_viewport_to_identity()

   title = Text("Whiteboard Demo", position=(540, 220), font_size=64, align="center")
   circle = Circle(center=(540, 780), radius=220, stroke_style=StrokeStyle(color=BLUE, width=4))
   formula = Math(r"$e^{i\pi} + 1 = 0$", position=(340, 1150), font_size=72, stroke_style=StrokeStyle(color=TEAL, width=3.5))
   eraser = Eraser(objects_to_erase=[circle])

   scene.add(SketchAnimation(start_time=0.0, duration=1.0), title)
   scene.add(SketchAnimation(start_time=0.8, duration=1.5), circle)
   scene.add(SketchAnimation(start_time=2.2, duration=1.4), formula)
   scene.add(SketchAnimation(start_time=4.0, duration=0.8), eraser)

   # 3. Pin word-timed captions on the camera-independent overlay layer
   scene.overlay.add(Captions(clip, words_per_chunk=3, highlight=RED, color=BLACK, y=1590))

   # 4. Render with narration, looping marimba theme music, and auto chalk/eraser SFX
   scene.render(
       "demo.mp4",
       narration=clip,
       background_music="marimba",
       sketch_sound=True,
       eraser_sound=True,
   )


.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting_started/installation
   getting_started/quickstart
   getting_started/architecture

.. toctree::
   :maxdepth: 2
   :caption: User Guide (handanim)

   user_guide/scenes_and_viewports
   user_guide/primitives_and_layout
   user_guide/text_math_and_fonts
   user_guide/styling_and_fills
   user_guide/animations_and_easing
   user_guide/characters_and_shorts
   user_guide/export_and_slides

.. toctree::
   :maxdepth: 2
   :caption: Voice, Captions & Sound (voiceanim)

   voiceanim_guide/overview
   voiceanim_guide/tts_providers
   voiceanim_guide/sync_and_captions
   voiceanim_guide/music_and_sfx

.. toctree::
   :maxdepth: 2
   :caption: AI Studio & MCP (aianim)

   aianim_guide/overview
   aianim_guide/cli_and_interactive
   aianim_guide/mcp_server
   aianim_guide/diagnostics_and_linting

.. toctree::
   :maxdepth: 2
   :caption: Showcase

   gallery/examples

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/handanim
   api/handanim.core
   api/handanim.primitives
   api/handanim.animations
   api/handanim.stylings
   api/voiceanim
   api/aianim
