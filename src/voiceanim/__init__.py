"""voiceanim: Realistic speech synthesis, word-level alignment, and narration sync for handanim."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .cache import AudioCache
from .mixer import mix_audio_with_video, mix_soundtrack
from .providers import (
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
    def synthesize(
        cls,
        text: str,
        provider: str = "kokoro",
        voice: str | None = None,
        speed: float = 1.0,
        instruct: str | None = None,
        output_path: str | Path | None = None,
        **kwargs: Any,
    ) -> AudioClip:
        """Synthesize speech using the specified provider (defaulting to Kokoro).

        Args:
            text: Text to synthesize into speech.
            provider: Voice provider ('kokoro' [default], 'polly', 'qwen', 'mock').
            voice: Voice name or ID.
            speed: Playback rate multiplier (1.0 = normal).
            instruct: Prompt instruction for emotion/prosody/timbre (Qwen3-TTS).
            output_path: Optional explicit output file path.
            **kwargs: Extra parameters passed to the provider.

        Returns:
            An AudioClip object containing duration and word-level timestamps.
        """
        engine = cls.get_provider(provider, **kwargs)
        return engine.synthesize(
            text=text,
            voice=voice,
            speed=speed,
            instruct=instruct,
            output_path=output_path,
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
    "PollyProvider",
    "QwenTTSProvider",
    "MockVoiceProvider",
    "get_provider",
]

