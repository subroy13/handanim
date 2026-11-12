voiceanim Overview
==================

``voiceanim`` is ``handanim``'s speech synthesis, word-level alignment, caption timing, background music, and procedural sound-effect subpackage.

Key Capabilities
----------------

1. **Unified TTS Facade (:class:`~voiceanim.VoiceEngine`)**: Synthesize natural speech with millisecond-accurate word and sentence timestamps using local open-weight models (`Kokoro-82M`, `Qwen3-TTS`), cloud APIs (`AWS Polly`), or deterministic CI mocks (`MockVoiceProvider`).
2. **Content-Addressed Caching (:class:`~voiceanim.cache.AudioCache`)**: Hashes `(provider, model, voice, speed, instruct, text)` with SHA-256 so re-running an animation script reuses the cached WAV and word timestamps in `< 1 ms`.
3. **Word-Level Visual Sync (:class:`~voiceanim.timeline.VoiceTimelineSync`)**: Anchor visual ``SketchAnimation`` or ``FadeInAnimation`` events to the exact timestamp when a word or phrase is spoken.
4. **Built-in Word-Timed Captions (:class:`~handanim.primitives.captions.Captions`)**: Render multi-word subtitle chunks with active-word highlighting and automatic width scaling on ``scene.overlay``.
5. **Looping Theme Music & Automatic Chalk/Eraser SFX (:mod:`voiceanim.sfx`, :mod:`voiceanim.mixer`)**: Generate open-source background theme music on repeat (auto-ducked under speech) and automatically play chalk drawing sounds during ``SketchAnimation`` and board-wiping sounds during ``Eraser``.

Core Data Model (:class:`~voiceanim.schema.AudioClip`)
------------------------------------------------------

Every call to ``VoiceEngine.synthesize(...)`` returns an :class:`~voiceanim.schema.AudioClip`:

.. code-block:: python

   from voiceanim import VoiceEngine

   clip = VoiceEngine.synthesize(
       "Welcome to handanim voice synchronization.",
       provider="kokoro",
       voice="af_heart",
       speed=1.0,
   )

   print(clip.audio_path)           # Path to synthesized .wav file
   print(clip.duration)             # Total duration in seconds
   print(clip.word_time("voice"))   # Start timestamp (float) of the word "voice"
   print(clip.word_range("voice", "synchronization"))  # (start, end) tuple

