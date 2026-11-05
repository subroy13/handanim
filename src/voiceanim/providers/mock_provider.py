"""Mock text-to-speech provider for zero-cost, offline testing and CI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..cache import AudioCache
from ..schema import AudioClip
from .base import BaseVoiceProvider


class MockVoiceProvider(BaseVoiceProvider):
    """Deterministic mock provider that generates synthetic tone WAV files with word timestamps."""

    name = "mock"
    default_voice = "mock_narrator"
    supported_voices = ["mock_narrator", "mock_female", "mock_male"]

    def __init__(self, cache: AudioCache | None = None, words_per_minute: float = 160.0):
        self.cache = cache or AudioCache()
        self.words_per_minute = words_per_minute

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float = 1.0,
        instruct: str | None = None,
        output_path: str | Path | None = None,
        **kwargs: Any,
    ) -> AudioClip:
        voice = voice or self.default_voice
        key = self.cache.compute_key(
            provider=self.name,
            voice=voice,
            text=text,
            speed=speed,
            instruct=instruct,
        )

        cached_clip = self.cache.get(key)
        if cached_clip is not None:
            if output_path and str(Path(output_path).resolve()) != str(Path(cached_clip.audio_path).resolve()):
                import shutil

                shutil.copyfile(cached_clip.audio_path, str(output_path))
                cached_clip.audio_path = str(output_path)
            return cached_clip

        sample_rate = 24000
        words = text.strip().split()
        words_count = max(1, len(words))
        duration = max(0.4, (words_count / (self.words_per_minute * speed)) * 60.0)

        # Generate a gentle, pleasant synthetic tone (440Hz with soft fade-in and fade-out)
        total_samples = int(sample_rate * duration)
        t = np.linspace(0, duration, total_samples, endpoint=False)
        waveform = np.sin(2 * np.pi * 440 * t) * 0.1

        # Apply smooth envelope
        fade_len = min(int(sample_rate * 0.05), total_samples // 4)
        if fade_len > 0:
            fade_in = np.linspace(0, 1, fade_len)
            fade_out = np.linspace(1, 0, fade_len)
            waveform[:fade_len] *= fade_in
            waveform[-fade_len:] *= fade_out

        target_path = output_path or (self.cache.cache_dir / f"{key}.wav")
        self.write_wav(target_path, waveform.astype(np.float32), sample_rate=sample_rate)

        word_timings = self.estimate_word_timings(text, duration)
        sentences = self.extract_sentences(text, word_timings)

        clip = AudioClip(
            audio_path=str(target_path),
            duration=round(duration, 3),
            sample_rate=sample_rate,
            text=text,
            words=word_timings,
            sentences=sentences,
            provider=self.name,
            voice=voice,
            instruct=instruct,
            metadata={"mock": True},
        )

        self.cache.put(key, clip)
        if output_path:
            clip.audio_path = str(output_path)
        return clip
