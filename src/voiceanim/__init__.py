"""voiceanim: Realistic speech synthesis, word-level alignment, and narration sync for handanim."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .cache import AudioCache
from .dialogue import DialogueTurn, SpeakerProfile, synthesize_dialogue
from .mixer import mix_audio_with_video, mix_soundtrack
from .pronunciation import latex_to_speech
from .providers import (
    KOKORO_ALL_VOICES,
    KOKORO_BLEND_PRESETS,
    KOKORO_VOICE_CATALOG,
    PROVIDERS,
    BaseVoiceProvider,
    KokoroProvider,
    MockVoiceProvider,
    PollyProvider,
    QwenTTSProvider,
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
        engine = cls.get_provider(provider, **kwargs)
        synth_kwargs: dict[str, Any] = {}
        if lang is not None:
            synth_kwargs["lang"] = lang
        return engine.synthesize(
            text=spoken_text,
            voice=voice,
            speed=speed,
            instruct=instruct,
            output_path=output_path,
            **synth_kwargs,
        )

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
    "KokoroProvider",
    "KOKORO_ALL_VOICES",
    "KOKORO_VOICE_CATALOG",
    "KOKORO_BLEND_PRESETS",
    "PollyProvider",
    "QwenTTSProvider",
    "MockVoiceProvider",
    "get_provider",
    "latex_to_speech",
    "DialogueTurn",
    "SpeakerProfile",
    "synthesize_dialogue",
]

