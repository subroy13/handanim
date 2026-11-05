"""Abstract base class and utilities for speech synthesis providers."""

from __future__ import annotations

import wave
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np

from ..schema import AudioClip, SentenceTimestamp, WordTimestamp


class BaseVoiceProvider(ABC):
    """Abstract interface for a text-to-speech provider."""

    name: str = "base"
    default_voice: str = ""
    supported_voices: list[str] = []

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float = 1.0,
        instruct: str | None = None,
        output_path: str | Path | None = None,
        **kwargs: Any,
    ) -> AudioClip:
        """Synthesize text into speech and return an AudioClip with timestamps.

        Args:
            text: Text to speak.
            voice: Voice name or ID. If None, uses default_voice.
            speed: Speech rate multiplier (1.0 = normal).
            instruct: Natural language instruction for tone/prosody/emotion (used by Qwen3-TTS).
            output_path: Optional explicit output WAV path. If None, writes to a temp or cache path.
            **kwargs: Extra provider-specific parameters.

        Returns:
            An AudioClip instance containing the path, duration, and word timestamps.
        """
        pass

    def list_voices(self) -> list[str]:
        """Return the list of supported voice IDs."""
        return list(self.supported_voices)

    @staticmethod
    def estimate_word_timings(
        text: str,
        total_duration: float,
        start_offset: float = 0.05,
    ) -> list[WordTimestamp]:
        """Heuristically estimate word timestamps proportional to character length and punctuation.

        Used when a provider returns audio without native alignment speech marks.
        """
        words = text.strip().split()
        if not words or total_duration <= 0:
            return []

        # Weigh words by length, adding weight for punctuation pauses
        weights = []
        for w in words:
            weight = max(1.0, len(w))
            if any(p in w for p in (".", "!", "?", ";", ":")):
                weight += 2.5
            elif "," in w or "—" in w:
                weight += 1.2
            weights.append(weight)

        total_weight = sum(weights)
        usable_duration = max(0.1, total_duration - start_offset - 0.05)
        scale = usable_duration / total_weight

        timings: list[WordTimestamp] = []
        curr = start_offset
        for word, wt in zip(words, weights, strict=False):
            duration = wt * scale
            # Small 20ms gap between words
            word_end = min(total_duration, curr + duration * 0.92)
            timings.append(
                WordTimestamp(
                    word=word,
                    start=round(curr, 3),
                    end=round(word_end, 3),
                    confidence=0.85,
                )
            )
            curr += duration

        return timings

    @staticmethod
    def extract_sentences(
        text: str,
        word_timings: list[WordTimestamp],
    ) -> list[SentenceTimestamp]:
        """Group word timestamps into sentence boundaries based on terminal punctuation."""
        if not word_timings:
            return []

        sentences: list[SentenceTimestamp] = []
        curr_words: list[WordTimestamp] = []
        curr_text_parts: list[str] = []

        for wt in word_timings:
            curr_words.append(wt)
            curr_text_parts.append(wt.word)

            if any(wt.word.endswith(p) for p in (".", "!", "?")):
                sentence_text = " ".join(curr_text_parts)
                sentences.append(
                    SentenceTimestamp(
                        text=sentence_text,
                        start=curr_words[0].start,
                        end=curr_words[-1].end,
                        words=list(curr_words),
                    )
                )
                curr_words = []
                curr_text_parts = []

        if curr_words:
            sentence_text = " ".join(curr_text_parts)
            sentences.append(
                SentenceTimestamp(
                    text=sentence_text,
                    start=curr_words[0].start,
                    end=curr_words[-1].end,
                    words=list(curr_words),
                )
            )

        return sentences

    @staticmethod
    def write_wav(
        file_path: str | Path,
        samples: np.ndarray,
        sample_rate: int = 24000,
    ) -> None:
        """Write 1D numpy array samples (float32 [-1, 1] or int16) to standard 16-bit PCM WAV."""
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        if samples.dtype == np.float32 or samples.dtype == np.float64:
            # Clip and convert float in [-1.0, 1.0] to int16
            clipped = np.clip(samples, -1.0, 1.0)
            int16_samples = (clipped * 32767.0).astype(np.int16)
        elif samples.dtype == np.int16:
            int16_samples = samples
        else:
            int16_samples = samples.astype(np.int16)

        with wave.open(str(file_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(int16_samples.tobytes())
