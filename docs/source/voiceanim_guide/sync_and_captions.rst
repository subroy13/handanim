Word-Level Sync & Built-In Captions
===================================

``voiceanim`` and ``handanim`` make it effortless to synchronize drawings and captions to spoken words.

Synchronizing Animations to Spoken Words (:class:`~voiceanim.timeline.VoiceTimelineSync`)
-----------------------------------------------------------------------------------------

Instead of hard-coding timestamps, query the :class:`~voiceanim.schema.AudioClip` or use :class:`~voiceanim.timeline.VoiceTimelineSync`:

.. code-block:: python

   from handanim import Circle, Scene, SketchAnimation
   from voiceanim import VoiceEngine, VoiceTimelineSync

   clip = VoiceEngine.synthesize(
       "First we draw the outer circle, then we label the radius.",
       provider="mock",
   )

   scene = Scene()
   circle = Circle(center=(640, 360), radius=150)

   # Automatically starts sketching 0.1s before the word "circle" is spoken
   event = VoiceTimelineSync.sync_event_to_word(
       clip=clip,
       word="circle",
       event_cls=SketchAnimation,
       duration=1.2,
       lead_in=0.1,
   )
   scene.add(event, circle)

Built-In Word-By-Word Captions (:class:`~handanim.primitives.captions.Captions`)
--------------------------------------------------------------------------------

Creating word-by-word highlighted subtitles manually would require hundreds of ``Text`` and ``ColorTransitionAnimation`` events. :class:`~handanim.primitives.captions.Captions` replaces all of that with **one drawable and one timeline event**, and automatically scales down wide chunks so they never clip off-screen:

.. code-block:: python

   from handanim import Captions, Scene
   from handanim.stylings.color import BLACK, RED

   scene = Scene(width=1080, height=1920, fps=30)
   scene.set_viewport_to_identity()

   captions = Captions(
       clip,
       words_per_chunk=3,          # Words displayed per subtitle chunk
       highlight=RED,              # Active spoken word color
       color=BLACK,                # Inactive word color in the current chunk
       y=1590,                     # Vertical position in world coordinates
       font_size=56,
       max_width=960.0,            # Auto-scales wide chunks to fit within 960px
       highlight_stroke_width=3.8,
   )

   # Add to scene.overlay so CameraAnimation pan/zoom never moves the captions!
   scene.overlay.add(captions)

.. tip::

   ``Captions`` accepts an :class:`~voiceanim.schema.AudioClip`, a list of :class:`~voiceanim.schema.WordTimestamp` objects, a list of `(word, start, end)` tuples, or pre-chunked JSON dictionaries (`[{"s": 0.1, "e": 0.9, "words": [{"d": "Order", "s": 0.1, "e": 0.4}, ...]}]`).

Exporting External ``.srt`` and ``.vtt`` Subtitles
--------------------------------------------------

You can also export standard subtitle files directly from any :class:`~voiceanim.schema.AudioClip`:

.. code-block:: python

   clip.export_srt("subtitles.srt", words_per_cue=5)
   clip.export_vtt("subtitles.vtt", words_per_cue=5)

