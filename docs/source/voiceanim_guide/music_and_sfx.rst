Background Music & Automatic Chalk / Eraser SFX
===============================================

``voiceanim`` includes a 100% open-source procedural sound synthesis engine (:mod:`voiceanim.sfx`) and multi-track soundtrack mixer (:mod:`voiceanim.mixer`) integrated directly with :meth:`~handanim.core.scene.Scene.render`.

1. Repeating Background Theme Music
-----------------------------------

Add repeating background music to any ``handanim`` video in two ways:

Option A: Directly in ``Scene`` or ``scene.render(...)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a built-in open-source theme preset (``"marimba"``, ``"calm"``, ``"upbeat"``), ``True``, an :class:`~voiceanim.schema.AudioClip`, or a path to your own ``.wav`` / ``.mp3`` file:

.. code-block:: python

   from handanim import Scene

   scene = Scene(width=1080, height=1920, fps=30)
   # Configure on the scene:
   scene.set_background_music("marimba", volume=0.18, loop=True)

   # Or pass directly to scene.render():
   scene.render(
       "video_with_music.mp4",
       narration=clip,
       background_music="marimba",  # Loops seamlessly & auto-ducks under speech!
       music_volume=0.18,
       music_loop=True,
   )

When ``narration`` is also provided, :func:`~voiceanim.mixer.mix_soundtrack` automatically ducks the background music volume while the narrator is speaking so the voice stays crystal clear.

Option B: Standalone via ``voiceanim`` Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use :func:`~voiceanim.sfx.generate_theme_music` or :func:`~voiceanim.sfx.loop_audio` (also available on :class:`~voiceanim.VoiceEngine`) to generate or repeat any audio clip to a target duration:

.. code-block:: python

   from voiceanim import VoiceEngine, generate_theme_music, loop_audio

   # Generate 30 seconds of repeating marimba theme music
   theme_clip = generate_theme_music(duration=30.0, style="marimba", bpm=104.0, volume=0.22)

   # Or loop any short WAV/MP3 file seamlessly for 30 seconds
   looped_clip = loop_audio("my_short_loop.wav", duration=30.0, volume=0.20)

2. Automatic Chalk Sketch Sound During ``SketchAnimation`` (On / Off & Volume Control)
--------------------------------------------------------------------------------------

Sketch drawing sound is **off by default** (``sketch_sound=False``) and uses a soft, non-distracting default volume (``0.25``) when enabled. When narration is present, continuous sketch sounds are also automatically ducked by 35% while the speaker is talking.

You can turn sketch sound **on, off, or down** at three levels:

Option A: Per-Animation Control on ``SketchAnimation``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Control sound on any individual :class:`~handanim.animations.sketch.SketchAnimation` using ``sound``, ``sound_volume``, and ``sound_style``:

.. code-block:: python

   from handanim import SketchAnimation

   # 1. Mute sketch sound on a specific animation (e.g. a title or small label)
   silent_sketch = SketchAnimation(start_time=0.0, duration=1.0, sound=False)

   # 2. Play a quiet felt-pen sound on a specific animation
   quiet_pen = SketchAnimation(
       start_time=1.2,
       duration=1.5,
       sound=True,
       sound_volume=0.12,
       sound_style="pen",
   )

   # 3. Shorthand: pass a float volume directly (0.0 mutes, > 0 enables at that volume)
   subtle_chalk = SketchAnimation(start_time=3.0, duration=1.5, sound=0.15)

   # 4. Toggle or adjust after creation
   subtle_chalk.set_sound(enabled=False)

Option B: Scene-Level Control
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configure or toggle sketch sound across the entire :class:`~handanim.core.scene.Scene`:

.. code-block:: python

   # Enable with softer volume (0.15) and felt-pen style
   scene.enable_sketch_sound(enabled=True, volume=0.15, style="pen")  # style="chalk" or "pen"

   # Or use the shorthand alias:
   scene.set_sketch_sound(0.15)   # enables at volume 0.15
   scene.set_sketch_sound(False)  # turns off sketch sound
   scene.disable_sketch_sound()   # turns off sketch sound

Option C: Render-Time Master Override
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Override sketch sound or its volume for a single :meth:`~handanim.core.scene.Scene.render` call:

.. code-block:: python

   # Master mute for this render:
   scene.render("silent_sketch.mp4", sketch_sound=False)

   # Render with quiet sketch sound (volume=0.12):
   scene.render("quiet_sketch.mp4", sketch_sound=True, sketch_sound_volume=0.12)

3. Automatic Board-Wiping Sound During ``Eraser``
-------------------------------------------------

When ``eraser_sound=True`` is enabled (or passed to ``scene.render(..., eraser_sound=True)``), any :class:`~handanim.primitives.eraser.Eraser` animation automatically plays a realistic back-and-forth felt/rubber board-erasing sound (:func:`~voiceanim.sfx.synthesize_eraser_sound`) matched to the duration of the wipe:

.. code-block:: python

   from handanim import Eraser, SketchAnimation

   scene.enable_eraser_sound(enabled=True, volume=0.55)

   eraser = Eraser(objects_to_erase=[diagram])
   scene.add(SketchAnimation(start_time=5.0, duration=0.9), eraser)

   scene.render("erased_demo.mp4", sketch_sound=True, eraser_sound=True)

4. Automatic Page-Turn & Paper-Crumple Sounds (``transition_sound=True``)
-------------------------------------------------------------------------

When ``transition_sound=True`` is enabled on :class:`~handanim.core.scene.Scene` (via ``Scene(..., transition_sound=True)``, :meth:`~handanim.core.scene.Scene.enable_transition_sound`, or ``scene.render(..., transition_sound=True)``), ``handanim`` automatically synthesizes procedural paper sound effects timed to every :class:`~handanim.animations.transitions.SceneTransition`:

- :class:`~handanim.animations.transitions.PageTurnTransition` triggers :func:`~voiceanim.sfx.synthesize_page_turn_sound` (a subtle corner-lift flick, swept paper-on-paper sliding friction, and a soft crease-settling pat).
- :class:`~handanim.animations.transitions.PaperCrumpleTransition` triggers :func:`~voiceanim.sfx.synthesize_crumple_sound` (a dense cascade of dry paper-crinkle micro-bursts and stiff paper snaps during the crunch phase, followed by an aerodynamic whoosh as the crumpled ball is tossed aside).

.. code-block:: python

   from handanim import PageTurnTransition, PaperCrumpleTransition, Scene

   scene = Scene(sketch_sound=True, transition_sound=True)
   scene.enable_transition_sound(enabled=True, volume=0.55)

   scene.add(PageTurnTransition(start_time=3.0, duration=1.2, direction="bottom_right"))
   scene.add(PaperCrumpleTransition(start_time=6.5, duration=1.4, direction="right"))

   scene.render("notebook_story.mp4")

5. Additional Procedural SFX (``pop``, ``whoosh``, ``ding``, ``page_turn``, ``crumple``)
----------------------------------------------------------------------------------------

You can also pass custom timed sound effects via ``sfx_events`` to :meth:`~handanim.core.scene.Scene.render` or :func:`~voiceanim.mixer.mix_soundtrack`:

.. code-block:: python

   scene.render(
       "full_sfx.mp4",
       sketch_sound=True,
       eraser_sound=True,
       transition_sound=True,
       sfx_events=[
           {"type": "pop", "start_time": 1.2, "volume": 0.5},
           {"type": "whoosh", "start_time": 3.0, "duration": 0.4, "volume": 0.45},
           {"type": "ding", "start_time": 4.5, "volume": 0.5},
       ],
   )


