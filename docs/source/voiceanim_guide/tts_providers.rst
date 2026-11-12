Voice Providers (Kokoro, Qwen3-TTS, Polly, Mock)
================================================

``voiceanim`` supports four interchangeable speech synthesis providers via :func:`~voiceanim.VoiceEngine.synthesize` and :func:`~voiceanim.get_provider`.

1. Local Open-Weight Default: ``KokoroProvider`` (``provider="kokoro"``)
------------------------------------------------------------------------

Uses the lightweight 82M-parameter Kokoro ONNX/PyTorch model for fast, high-fidelity local inference on CPU or Apple Silicon without cloud API keys:

.. code-block:: python

   from voiceanim import VoiceEngine

   clip = VoiceEngine.synthesize(
       "Pythagoras discovered a fundamental relation in right triangles.",
       provider="kokoro",
       voice="af_heart",  # Presets: "af_heart", "am_adam", "bf_emma", "bm_george"
       speed=1.0,
   )

2. Instruction-Controllable Local TTS: ``QwenTTSProvider`` (``provider="qwen"``)
--------------------------------------------------------------------------------

Supports ``Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`` (and ``0.6B``) with natural-language ``instruct`` control over emotion, prosody, and speaking style:

.. code-block:: python

   clip = VoiceEngine.synthesize(
       "Wait—look at what happens when we swap the order!",
       provider="qwen",
       voice="Chelsie",
       instruct="Speak in an enthusiastic, curious storytelling tone.",
   )

3. Cloud Neural & Generative TTS: ``PollyProvider`` (``provider="polly"``)
--------------------------------------------------------------------------

Uses AWS Polly (`boto3`) and native Polly ``SpeechMarks`` for exact word and sentence boundary timestamps:

.. code-block:: python

   clip = VoiceEngine.synthesize(
       "Cloud synthesis with native AWS Polly SpeechMarks.",
       provider="polly",
       voice="Matthew",  # Or "Ruth", "Joanna", "Stephen"
   )

4. Offline Deterministic CI / Testing: ``MockVoiceProvider`` (``provider="mock"``)
----------------------------------------------------------------------------------

Synthesizes a lightweight sine-wave tone track with proportional word timestamps—ideal for unit tests, CI pipelines, and layout prototyping without downloading TTS weights:

.. code-block:: python

   clip = VoiceEngine.synthesize(
       "Fast offline test narration with deterministic word timings.",
       provider="mock",
   )

Multi-Beat Narration Stitching
------------------------------

For longer videos organized into beats or scenes, use :class:`~voiceanim.schema.NarrationBeat` and ``stitch_narration_beats`` in :mod:`voiceanim.timeline` to combine clips with configurable silence padding while shifting word timestamps automatically.

