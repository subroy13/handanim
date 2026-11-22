"""voiceanim: Realistic speech synthesis, word-level alignment, and narration sync for handanim."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .aligner import ForcedAligner, align_clip, align_words
from .cache import AudioCache
from .dialogue import DialogueTurn, SpeakerProfile, synthesize_dialogue
from .mixer import mix_audio_with_video, mix_soundtrack
from .pronunciation import latex_to_speech
from .providers import (
    CHATTERBOX_STYLE_PRESETS,
    KOKORO_ALL_VOICES,
    KOKORO_BLEND_PRESETS,
    KOKORO_VOICE_CATALOG,
    PROVIDERS,
    ZONOS_BLEND_PRESETS,
    ZONOS_STEERING_PRESETS,
    BaseVoiceProvider,
    ChatterboxProvider,
    KokoroProvider,
    MockVoiceProvider,
    PollyProvider,
    QwenTTSProvider,
    ZonosProvider,
    get_provider,
)
from .schema import AudioClip, NarrationBeat, SentenceTimestamp, WordTimestamp
from .sfx import (
    generate_theme_music,
    loop_audio,
    synthesize_chalk_sound,
    synthesize_crumple_sound,
    synthesize_ding_sound,
    synthesize_eraser_sound,
    synthesize_page_turn_sound,
    synthesize_pop_sound,
    synthesize_theme_loop,
    synthesize_whoosh_sound,
)
from .timeline import VoiceTimelineSync


class VoiceEngine:
    """Unified facade for voiceanim speech synthesis and narration."""

    @staticmethod
    def get_provider(name: str = "kokoro", **kwargs: Any) -> BaseVoiceProvider:
        """Get an initialized provider instance. Defaults to 'kokoro'."""
        return get_provider(name=name, **kwargs)

    @staticmethod
    def list_providers() -> list[str]:
        """List all supported voice provider names."""
        return list(PROVIDERS.keys())

    @classmethod
    def list_voices(
        cls,
        provider: str = "kokoro",
        category: str | None = None,
        include_blends: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """List available voice IDs for the specified provider (54 built-in voices for Kokoro)."""
        engine = cls.get_provider(provider, **kwargs)
        if isinstance(engine, KokoroProvider):
            return engine.list_voices(category=category, include_blends=include_blends)
        return engine.list_voices()

    @classmethod
    def blend_voices(
        cls,
        voice_spec: Any,
        **kwargs: Any,
    ) -> Any:
        """Compute a blended `(510, 1, 256)` float32 style vector across two or more Kokoro voices."""
        engine = cls.get_provider("kokoro", **kwargs)
        assert isinstance(engine, KokoroProvider)
        return engine.blend_voices(voice_spec)

    @classmethod
    def synthesize(
        cls,
        text: str,
        provider: str = "kokoro",
        voice: Any | None = None,
        speed: float = 1.0,
        instruct: str | None = None,
        output_path: str | Path | None = None,
        preprocess_math: bool = False,
        lang: str | None = None,
        **kwargs: Any,
    ) -> AudioClip:
        """Synthesize speech using the specified provider (defaulting to Kokoro).

        Args:
            text: Text to synthesize into speech.
            provider: Voice provider ('kokoro' [default], 'polly', 'qwen', 'mock').
            voice: Voice name, blend expression (e.g. ``"am_puck:0.6+bm_fable:0.4"``),
                blend preset (e.g. ``"blend_transatlantic"``), weight mapping
                (e.g. ``{"am_puck": 0.6, "bm_fable": 0.4}``), or ``(510, 1, 256)`` style vector.
            speed: Playback rate multiplier (1.0 = normal).
            instruct: Prompt instruction for emotion/prosody/timbre (Qwen3-TTS).
            output_path: Optional explicit output file path.
            preprocess_math: If True, converts inline LaTeX math to spoken English before TTS.
            lang: Optional phonemizer language code for Kokoro (e.g., ``"en-us"``, ``"en-gb"``,
                ``"es"``, ``"fr-fr"``, ``"hi"``, ``"it"``, ``"ja"``, ``"pt-br"``, ``"cmn"``).
            **kwargs: Extra parameters passed to the provider initializer.

        Returns:
            An AudioClip object containing duration and word-level timestamps.
        """
        spoken_text = latex_to_speech(text) if preprocess_math else text

        # Separate per-call synthesis kwargs from provider constructor kwargs
        synth_keys = {
            "exaggeration",
            "cfg_weight",
            "temperature",
            "ref_audio",
            "controls",
            "control_spans",
            "condition_values",
            "speaker_cfg_scale",
            "align",
            "language",
        }
        synth_kwargs: dict[str, Any] = {}
        init_kwargs: dict[str, Any] = {}
        for k, v in kwargs.items():
            if k in synth_keys:
                synth_kwargs[k] = v
            else:
                init_kwargs[k] = v

        if lang is not None:
            synth_kwargs["lang"] = lang

        engine = cls.get_provider(provider, **init_kwargs)
        return engine.synthesize(
            text=spoken_text,
            voice=voice,
            speed=speed,
            instruct=instruct,
            output_path=output_path,
            **synth_kwargs,
        )

    @classmethod
    def synthesize_beats(
        cls,
        beats: Any,
        provider: str = "kokoro",
        voice: Any | None = None,
        speed: float = 1.0,
        instruct: str | None = None,
        output_dir: str | Path | None = None,
        preprocess_math: bool = False,
        align: bool | str = "auto",
        **kwargs: Any,
    ) -> list[NarrationBeat]:
        """Synthesize a sequence of per-beat narration specs with optional per-beat `instruct` directions.

        Each beat in `beats` may be a `NarrationBeat`, a `(id, text)` 2-tuple,
        a `(id, text, instruct)` 3-tuple, or a dict with `id`/`text`/`instruct`/overrides.
        """
        out_dir = Path(output_dir).resolve() if output_dir is not None else None
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)

        results: list[NarrationBeat] = []
        provider_cache: dict[str, BaseVoiceProvider] = {}

        for raw_beat in beats:
            beat = NarrationBeat.from_spec(raw_beat)
            eff_provider = (beat.provider or provider).lower().strip()
            eff_voice = beat.voice if beat.voice is not None else voice
            eff_speed = beat.speed if beat.speed is not None else speed
            eff_instruct = beat.instruct if beat.instruct is not None else instruct

            if eff_provider not in provider_cache:
                provider_cache[eff_provider] = cls.get_provider(eff_provider, **kwargs)
            engine = provider_cache[eff_provider]

            spoken_text = latex_to_speech(beat.text) if preprocess_math else beat.text
            beat_out = (out_dir / f"{beat.id}.wav") if out_dir is not None else None

            call_kwargs: dict[str, Any] = {}
            if beat.exaggeration is not None:
                call_kwargs["exaggeration"] = beat.exaggeration
            if beat.cfg_weight is not None:
                call_kwargs["cfg_weight"] = beat.cfg_weight
            if beat.controls is not None:
                call_kwargs["controls"] = beat.controls
            if beat.ref_audio is not None:
                call_kwargs["ref_audio"] = beat.ref_audio
            if eff_provider in ("chatterbox", "zonos", "zonos3", "zonos3-mini", "qwen"):
                call_kwargs["align"] = align

            clip = engine.synthesize(
                text=spoken_text,
                voice=eff_voice,
                speed=eff_speed,
                instruct=eff_instruct,
                output_path=beat_out,
                **call_kwargs,
            )
            if align and eff_provider not in ("chatterbox", "zonos", "zonos3", "zonos3-mini", "qwen", "polly"):
                if align not in (False, "none") and align != "auto":
                    align_clip(clip, backend=str(align))

            beat.clip = clip
            results.append(beat)

        return results

    @staticmethod
    def align_clip(
        clip: AudioClip,
        backend: str = "auto",
        model_size: str = "base",
        language: str = "en",
    ) -> AudioClip:
        """Run forced alignment on an existing `AudioClip` to refresh its word timestamps."""
        return align_clip(clip, backend=backend, model_size=model_size, language=language)

    @staticmethod
    def synthesize_dialogue(
        turns: Any,
        output_path: str | Path | None = None,
        speakers: dict[str, Any] | None = None,
        default_provider: str = "kokoro",
        pause_between: float = 0.25,
        preprocess_math: bool = True,
        **kwargs: Any,
    ) -> AudioClip:
        """Synthesize a multi-speaker dialogue into a single stitched `AudioClip`."""
        return synthesize_dialogue(
            turns=turns,
            output_path=output_path,
            speakers=speakers,
            default_provider=default_provider,
            pause_between=pause_between,
            preprocess_math=preprocess_math,
            **kwargs,
        )

    @staticmethod
    def generate_theme_music(
        duration: float,
        output_path: str | Path | None = None,
        style: str = "marimba",
        bpm: float = 104.0,
        volume: float = 0.22,
    ) -> AudioClip:
        """Generate repeating open-source background theme music of length `duration`."""
        return generate_theme_music(
            duration=duration,
            output_path=output_path,
            style=style,
            bpm=bpm,
            volume=volume,
        )

    @staticmethod
    def loop_audio(
        audio_source: str | Path | AudioClip,
        duration: float,
        output_path: str | Path | None = None,
        volume: float = 0.22,
    ) -> AudioClip:
        """Repeat an audio file, `AudioClip`, or built-in theme preset to match `duration`."""
        return loop_audio(
            audio_source=audio_source,
            duration=duration,
            output_path=output_path,
            volume=volume,
        )


__all__ = [
    "VoiceEngine",
    "AudioClip",
    "WordTimestamp",
    "SentenceTimestamp",
    "NarrationBeat",
    "AudioCache",
    "ForcedAligner",
    "align_words",
    "align_clip",
    "VoiceTimelineSync",
    "mix_audio_with_video",
    "mix_soundtrack",
    "generate_theme_music",
    "loop_audio",
    "synthesize_chalk_sound",
    "synthesize_eraser_sound",
    "synthesize_page_turn_sound",
    "synthesize_crumple_sound",
    "synthesize_pop_sound",
    "synthesize_whoosh_sound",
    "synthesize_ding_sound",
    "synthesize_theme_loop",
    "BaseVoiceProvider",
    "ChatterboxProvider",
    "CHATTERBOX_STYLE_PRESETS",
    "KokoroProvider",
    "KOKORO_ALL_VOICES",
    "KOKORO_VOICE_CATALOG",
    "KOKORO_BLEND_PRESETS",
    "PollyProvider",
    "QwenTTSProvider",
    "ZonosProvider",
    "ZONOS_BLEND_PRESETS",
    "ZONOS_STEERING_PRESETS",
    "MockVoiceProvider",
    "get_provider",
    "latex_to_speech",
    "DialogueTurn",
    "SpeakerProfile",
    "synthesize_dialogue",
]

