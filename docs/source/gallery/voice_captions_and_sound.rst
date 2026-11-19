Theme 5: Voice Narration, Captions, Camera & Sketch Sound Control
=================================================================

``handanim`` and ``voiceanim`` work together so you can synchronize drawing events to exact spoken words, pin word-by-word highlighted :class:`~handanim.primitives.captions.Captions` onto the camera-independent ``scene.overlay`` layer, loop background music that automatically ducks under speech, and **turn sketch drawing sounds on, off, or down** globally or per individual :class:`~handanim.animations.sketch.SketchAnimation`.

.. tip::

   To regenerate any of the videos on this page locally:

   .. code-block:: bash

      poetry run python docs/source/gallery/build_gallery.py --only sketch_sound_control
      poetry run python docs/source/gallery/build_gallery.py --only captions_overlay
      poetry run python docs/source/gallery/build_gallery.py --only with_audio

----

Tutorial 5.1: Controlling Sketch Sound (On / Off, Volume Tuning & Pen vs. Chalk)
--------------------------------------------------------------------------------

**Use Case:** Sometimes the default chalk drawing sound is not needed on every text label, or you want a subtle, quiet pen sound (``sound_volume=0.12, sound_style="pen"``) rather than a full chalk sound, or you want to turn sketch sound completely off (``sound=False``).

``handanim`` gives you **three levels of control** over sketch sound:

1. **Per-Animation Control on** :class:`~handanim.animations.sketch.SketchAnimation`:

   - ``SketchAnimation(start_time=0.0, duration=1.0, sound=False)`` — Mutes sketch sound for this specific animation (even when ``scene.sketch_sound=True``).
   - ``SketchAnimation(start_time=1.0, duration=1.2, sound=True, sound_volume=0.12, sound_style="pen")`` — Plays a soft felt-pen sound at volume ``0.12`` for this animation.
   - ``SketchAnimation(start_time=2.5, duration=1.0, sound=0.15)`` — Shorthand! Passing a float ``> 0`` enables sketch sound for this event at volume ``0.15`` (passing ``0.0`` mutes it).
   - ``anim.set_sound(enabled=False)`` or ``anim.set_sound(True, volume=0.15, style="pen")`` — Helper method to toggle or tune sound after creating the event.

2. **Scene-Level Control on** :class:`~handanim.core.scene.Scene`:

   - ``Scene(..., sketch_sound=False, sketch_sound_volume=0.25, sketch_sound_style="chalk")`` — Sketch sound is **off by default** (``sketch_sound=False``) and uses a gentle default volume of ``0.25`` when enabled.
   - ``scene.enable_sketch_sound(enabled=True, volume=0.15, style="pen")`` (or ``scene.set_sketch_sound(0.15)``) — Enables and tunes volume across the scene.
   - ``scene.disable_sketch_sound()`` (or ``scene.set_sketch_sound(False)``) — Turns off scene-level sketch sound.

3. **Render-Time Master Override on** :meth:`~handanim.core.scene.Scene.render`:

   - ``scene.render("out.mp4", sketch_sound=False)`` — Master mute: silences all sketch sounds for this render.
   - ``scene.render("out.mp4", sketch_sound=True, sketch_sound_volume=0.15)`` (or ``scene.render("out.mp4", sketch_sound=0.15)``) — Renders with quiet sketch sound at volume ``0.15``.

.. raw:: html

   <div class="tutorial-media">
     <video controls loop playsinline width="680" src="../_static/gallery/sketch_sound_control.mp4"></video>
     <p><em>Comparison of 3 cards in one scene: Card 1 is muted (<code>sound=False</code>), Card 2 uses a quiet felt pen (<code>sound_volume=0.12, sound_style="pen"</code>), and Card 3 uses standard chalk (<code>sound_volume=0.28, sound_style="chalk"</code>).</em></p>
   </div>

Complete Tutorial Code
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from handanim import Circle, FillStyle, RoundedRectangle, Scene, SketchAnimation, StrokeStyle, Text
   from handanim.stylings.color import BLACK, BLUE, GRAY, LIGHT_GRAY, NAVY, PASTEL_BLUE, PASTEL_GREEN, TEAL

   scene = Scene(
       width=960,
       height=540,
       fps=24,
       background_color=(0.99, 0.98, 0.95),
       sketch_sound=True,
       sketch_sound_volume=0.22,
       sketch_sound_style="chalk",
   )
   scene.set_viewport_to_identity()

   # 1. Title sketches SILENTLY (`sound=False`) even though scene.sketch_sound is True
   title = Text(
       "Sketch Sound Control: On / Off & Volume Tuning",
       position=(480, 62),
       font_size=34,
       stroke_style=StrokeStyle(color=NAVY, width=2.4),
   )
   scene.add(SketchAnimation(start_time=0.0, duration=0.8, sound=False), title)

   # 2. Card 1: Explicitly Muted (`sound=False`)
   card_off = RoundedRectangle(
       top_left=(55, 130), width=260, height=320, corner_radius=18,
       stroke_style=StrokeStyle(color=GRAY, width=3.0),
       fill_style=FillStyle(color=LIGHT_GRAY, opacity=0.25, hachure_gap=12),
   )
   label_off = Text("1. Muted (sound=False)", position=(185, 175), font_size=22, stroke_style=StrokeStyle(color=BLACK, width=2.0))
   circle_off = Circle(center=(185, 295), radius=70, stroke_style=StrokeStyle(color=GRAY, width=3.5))
   scene.add(SketchAnimation(start_time=0.9, duration=1.1, sound=False), card_off)
   scene.add(SketchAnimation(start_time=1.0, duration=0.5, sound=False), label_off)
   scene.add(SketchAnimation(start_time=1.2, duration=1.0, sound=False), circle_off)

   # 3. Card 2: Soft Pen Sound (`sound_volume=0.12, sound_style="pen"`)
   card_soft = RoundedRectangle(
       top_left=(350, 130), width=260, height=320, corner_radius=18,
       stroke_style=StrokeStyle(color=TEAL, width=3.0),
       fill_style=FillStyle(color=PASTEL_GREEN, opacity=0.35, hachure_gap=12),
   )
   label_soft = Text("2. Soft Pen (vol=0.12)", position=(480, 175), font_size=22, stroke_style=StrokeStyle(color=TEAL, width=2.0))
   circle_soft = Circle(center=(480, 295), radius=70, stroke_style=StrokeStyle(color=TEAL, width=3.5))
   scene.add(SketchAnimation(start_time=2.4, duration=1.1, sound_volume=0.12, sound_style="pen"), card_soft)
   scene.add(SketchAnimation(start_time=2.5, duration=0.5, sound=False), label_soft)
   scene.add(SketchAnimation(start_time=2.7, duration=1.0, sound_volume=0.12, sound_style="pen"), circle_soft)

   # 4. Card 3: Standard Chalk Sound (`sound_volume=0.28, sound_style="chalk"`)
   card_chalk = RoundedRectangle(
       top_left=(645, 130), width=260, height=320, corner_radius=18,
       stroke_style=StrokeStyle(color=BLUE, width=3.0),
       fill_style=FillStyle(color=PASTEL_BLUE, opacity=0.35, hachure_gap=12),
   )
   label_chalk = Text("3. Chalk (vol=0.28)", position=(775, 175), font_size=22, stroke_style=StrokeStyle(color=BLUE, width=2.0))
   circle_chalk = Circle(center=(775, 295), radius=70, stroke_style=StrokeStyle(color=BLUE, width=3.5))
   scene.add(SketchAnimation(start_time=4.0, duration=1.1, sound_volume=0.28, sound_style="chalk"), card_chalk)
   scene.add(SketchAnimation(start_time=4.1, duration=0.5, sound=False), label_chalk)
   scene.add(SketchAnimation(start_time=4.3, duration=1.0, sound_volume=0.28, sound_style="chalk"), circle_chalk)

   scene.render("sketch_sound_control.mp4", max_length=5.6)

----

Tutorial 5.2: Built-In Captions, Camera Overlay & Soundtrack
------------------------------------------------------------

**Use Case:** Build a 9:16 portrait short where :class:`~handanim.animations.camera.CameraAnimation` zooms into an inscribed triangle while the top HUD banner and word-by-word highlighted :class:`~handanim.primitives.captions.Captions` stay stationary on ``scene.overlay``, accompanied by repeating ``"marimba"`` background music that automatically ducks under speech.

.. raw:: html

   <div class="tutorial-media">
     <video controls loop playsinline width="360" src="../_static/gallery/captions_overlay_demo.mp4"></video>
     <p><em>9:16 short with CameraAnimation zoom, camera-invariant overlay HUD &amp; word-timed Captions, plus marimba music and chalk/eraser SFX.</em></p>
   </div>

Complete Tutorial Code
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from handanim import (
       CameraAnimation, Captions, Circle, Eraser, FillStyle, Math,
       Polygon, RoundedRectangle, Scene, Show, SketchAnimation,
       SketchStyle, StrokeStyle, Text,
   )
   from handanim.core.viewport import Viewport
   from handanim.stylings.color import BLACK, BLUE, PASTEL_BLUE, PASTEL_ORANGE, RED, TEAL
   from voiceanim import VoiceEngine

   viewport = Viewport(
       world_xrange=(0, 1080),
       world_yrange=(0, 1920),
       screen_width=540,
       screen_height=960,
       margin=0,
   )
   scene = Scene(width=540, height=960, fps=24, background_color=(0.99, 0.98, 0.95), viewport=viewport)

   # 1. Synthesize word-timed narration (use provider="kokoro" for local neural TTS or "mock" for offline CI)
   narration = VoiceEngine.synthesize(
       "Watch how built in captions highlight each spoken word while the camera zooms into the triangle.",
       provider="mock",
   )

   # 2. World-space geometry diagram (moves & zooms with CameraAnimation)
   sketch = SketchStyle(roughness=1.4, bowing=1.0)
   circle = Circle(
       center=(540, 820), radius=280,
       stroke_style=StrokeStyle(color=BLUE, width=4.0), sketch_style=sketch,
       fill_style=FillStyle(color=PASTEL_BLUE, opacity=0.2, hachure_gap=18),
   )
   triangle = Polygon(
       points=[(540, 540), (300, 960), (780, 960)],
       stroke_style=StrokeStyle(color=BLACK, width=4.5), sketch_style=sketch,
       fill_style=FillStyle(color=PASTEL_ORANGE, opacity=0.35, hachure_gap=14),
   )
   formula = Math(r"$a^2 + b^2 = c^2$", position=(380, 820), font_size=72, stroke_style=StrokeStyle(color=TEAL, width=3.5))

   scene.add(SketchAnimation(start_time=0.0, duration=1.5), circle)
   scene.add(SketchAnimation(start_time=1.0, duration=1.5), triangle)
   scene.add(SketchAnimation(start_time=2.2, duration=1.2), formula)

   eraser = Eraser(objects_to_erase=[formula], stroke_style=StrokeStyle(width=6.0))
   scene.add(SketchAnimation(start_time=4.4, duration=0.8), eraser)

   # 3. Camera zoom in and pan back out
   scene.add_camera(CameraAnimation(start_time=1.2, duration=2.0, data={"to_xrange": (220, 860), "to_yrange": (420, 1560)}))
   scene.add_camera(CameraAnimation(start_time=3.6, duration=1.6, data={"to_xrange": (0, 1080), "to_yrange": (0, 1920)}))

   # 4. Camera-independent overlay layer: HUD pill + word-timed Captions
   hud_box = RoundedRectangle(
       top_left=(90, 80), width=900, height=110, border_radius=24,
       stroke_style=StrokeStyle(color=BLUE, width=3.0),
       fill_style=FillStyle(color=PASTEL_BLUE, opacity=0.35, hachure_gap=14),
   )
   hud_title = Text("Overlay HUD & Captions (Camera-Invariant)", position=(135, 148), font_size=42, stroke_style=StrokeStyle(color=BLACK, width=3.0))
   scene.overlay.add(Show(0.0), hud_box)
   scene.overlay.add(Show(0.0), hud_title)

   scene.overlay.add(
       Captions(narration, words_per_chunk=3, highlight=RED, color=BLACK, y=1590, font_size=64)
   )

   scene.render(
       "captions_overlay_demo.mp4",
       narration=narration,
       background_music="marimba",
       music_volume=0.18,
       sketch_sound=True,
       sketch_sound_volume=0.18,
       eraser_sound=True,
   )

----

Tutorial 5.3: Word-Synced Voice Narration (`VoiceTimelineSync`)
---------------------------------------------------------------

**Use Case:** Automatically anchor a :class:`~handanim.animations.sketch.SketchAnimation` to the exact millisecond a target word (e.g. ``"circle"``) is spoken in the narration track using :meth:`~voiceanim.timeline.VoiceTimelineSync.sync_event_to_word`.

.. raw:: html

   <div class="tutorial-media">
     <video controls loop playsinline width="620" src="../_static/gallery/with_audio.mp4"></video>
     <p><em>Circle sketch triggered automatically 100ms before the word "circle" is spoken.</em></p>
   </div>

Complete Tutorial Code
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from handanim import Circle, Scene, SketchAnimation, StrokeStyle
   from handanim.stylings.color import BLUE
   from voiceanim import VoiceEngine, VoiceTimelineSync

   # 1. Synthesize narration (defaults to local Kokoro-82M neural TTS)
   narration = VoiceEngine.synthesize(
       "In our first step, we sketch a circle representing Earth.",
       voice="af_heart",
   )

   # 2. Synchronize SketchAnimation to when "circle" is spoken
   circle = Circle(center=(960, 540), radius=100, stroke_style=StrokeStyle(color=BLUE, width=4))
   event, _ = VoiceTimelineSync.sync_event_to_word(
       clip=narration,
       word="circle",
       event_cls=SketchAnimation,
       drawable=circle,
       duration=1.5,
       lead_in=0.1,  # Start sketching 100ms before "circle" is spoken
   )

   scene = Scene(width=1920, height=1080)
   scene.add(event=event, drawable=circle)

   # 3. Render video with synchronized audio muxing
   scene.render("with_audio.mp4", narration=narration)
