Voice Providers (Kokoro, Qwen3-TTS, Polly, Mock)
================================================

``voiceanim`` supports four interchangeable speech synthesis providers via :func:`~voiceanim.VoiceEngine.synthesize` and :func:`~voiceanim.get_provider`.

1. Local Open-Weight Default: ``KokoroProvider`` (``provider="kokoro"``)
------------------------------------------------------------------------

Uses the lightweight 82M-parameter Kokoro ONNX model for fast, high-fidelity local inference on CPU or Apple Silicon without cloud API keys. ``KokoroProvider`` exposes all **54 built-in voice embeddings** in ``voices-v1.0.bin`` as well as **256-D latent voice blending**:

.. code-block:: python

   from voiceanim import VoiceEngine

   clip = VoiceEngine.synthesize(
       "Pythagoras discovered a fundamental relation in right triangles.",
       provider="kokoro",
       voice="am_fenrir",  # Any of the 54 built-in voices or a blend expression
       speed=1.0,
   )

All 54 Built-In Kokoro Voices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can query the catalog programmatically with ``VoiceEngine.list_voices("kokoro", category=..., include_blends=True)`` or inspect :data:`~voiceanim.KOKORO_VOICE_CATALOG`:

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Category
     - Voice IDs
   * - ``american_female`` (11)
     - ``af_alloy``, ``af_aoede``, ``af_bella``, ``af_heart``, ``af_jessica``, ``af_kore``, ``af_nicole``, ``af_nova``, ``af_river``, ``af_sarah``, ``af_sky``
   * - ``american_male`` (9)
     - ``am_adam``, ``am_echo``, ``am_eric``, ``am_fenrir``, ``am_liam``, ``am_michael``, ``am_onyx``, ``am_puck``, ``am_santa``
   * - ``british_female`` (4)
     - ``bf_alice``, ``bf_emma``, ``bf_isabella``, ``bf_lily``
   * - ``british_male`` (4)
     - ``bm_daniel``, ``bm_fable``, ``bm_george``, ``bm_lewis``
   * - ``hindi`` / Indian English (4)
     - ``hf_alpha``, ``hf_beta``, ``hm_omega``, ``hm_psi``
   * - ``spanish`` (3)
     - ``ef_dora``, ``em_alex``, ``em_santa``
   * - ``french`` (1)
     - ``ff_siwis``
   * - ``italian`` (2)
     - ``if_sara``, ``im_nicola``
   * - ``japanese`` (5)
     - ``jf_alpha``, ``jf_gongitsune``, ``jf_nezumi``, ``jf_tebukuro``, ``jm_kumo``
   * - ``portuguese`` (3)
     - ``pf_dora``, ``pm_alex``, ``pm_santa``
   * - ``mandarin`` (8)
     - ``zf_xiaobei``, ``zf_xiaoni``, ``zf_xiaoxiao``, ``zf_xiaoyi``, ``zm_yunjian``, ``zm_yunxi``, ``zm_yunxia``, ``zm_yunyang``

256-D Latent Voice Blending
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every Kokoro voice is a ``(510, 1, 256)`` ``float32`` style matrix. ``KokoroProvider`` lets you linearly interpolate two or more voices to craft custom timbres, smooth out single-voice artifacts, or mix regional accents (all weights are automatically normalized to sum to ``1.0``):

.. code-block:: python

   from voiceanim import VoiceEngine

   # 1. Weighted blend expression string ('+' or ',' separator)
   clip = VoiceEngine.synthesize(
       "Blending sixty percent Puck with forty percent Fable.",
       voice="am_puck:0.6+bm_fable:0.4",
   )

   # 2. Equal-weight shorthand (50% / 50%)
   clip_equal = VoiceEngine.synthesize(
       "Equal blend of Fenrir and Onyx.",
       voice="am_fenrir+am_onyx",
   )

   # 3. Dictionary or sequence of (voice, weight) pairs
   clip_dict = VoiceEngine.synthesize(
       "Warm Indian-English presenter blend.",
       voice={"hm_omega": 0.55, "am_liam": 0.45},
   )

   # 4. Built-in named blend presets
   clip_preset = VoiceEngine.synthesize(
       "Using a built-in named blend preset.",
       voice="blend_transatlantic",  # Or "blend_professor", "blend_storyteller",
                                     # "blend_host_female", "blend_indian_male", "blend_indian_female"
   )

   # 5. Pre-compute a reusable (510, 1, 256) style vector directly
   custom_style = VoiceEngine.blend_voices({"af_aoede": 0.6, "af_kore": 0.4})
   clip_style = VoiceEngine.synthesize("Synthesized from a style matrix.", voice=custom_style)

Phonemizer Language Selection (``lang``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, ``KokoroProvider`` selects ``lang="en-gb"`` when the dominant voice is British (``bf_*`` or ``bm_*``) and ``lang="en-us"`` otherwise (so cross-accent voices such as ``hm_omega`` or ``hf_alpha`` pronounce English scripts naturally out of the box). To synthesize non-English scripts or force a specific phonemizer, pass ``lang`` explicitly:

.. code-block:: python

   clip_uk = VoiceEngine.synthesize(
       "Schedule and aluminium pronunciation.",
       voice="am_puck:0.5+bm_daniel:0.5",
       lang="en-gb",
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
