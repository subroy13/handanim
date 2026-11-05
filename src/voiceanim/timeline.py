"""Animation timeline synchronization with spoken narration."""

from __future__ import annotations

import logging
import wave
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from .schema import AudioClip, NarrationBeat, WordTimestamp

logger = logging.getLogger(__name__)


class VoiceTimelineSync:
    """Utilities to synchronize handanim drawing animations with narration timestamps."""

    @staticmethod
    def sync_event_to_word(
        clip: AudioClip,
        word: str,
        event_cls: type[Any] | Callable[..., Any],
        drawable: Any,
        duration: float = 1.5,
        lead_in: float = 0.0,
        occurrence: int = 1,
        **event_kwargs: Any,
    ) -> tuple[Any, Any]:
        """Create an animation event timed precisely to a spoken word in the narration.

        Args:
            clip: Synthesized narration AudioClip with word timestamps.
            word: The keyword to synchronize with.
            event_cls: Animation class (e.g. SketchAnimation, FadeInAnimation).
            drawable: Target drawable object.
            duration: Animation duration.
            lead_in: Seconds to start *before* the word is spoken (e.g. 0.1s for natural pen arrival).
            occurrence: Which occurrence of the word to match (1-based).
            **event_kwargs: Extra kwargs passed to the animation event constructor.

        Returns:
            Tuple of (initialized_event, drawable).
        """
        word_start = clip.get_word_time(word, occurrence=occurrence)
        if word_start is None:
            logger.warning("Word '%s' (occurrence %d) not found in narration. Defaulting start_time to 0.0s.", word, occurrence)
            start_time = 0.0
        else:
            start_time = max(0.0, word_start - lead_in)

        event = event_cls(start_time=round(start_time, 3), duration=duration, **event_kwargs)
        return event, drawable

    @staticmethod
    def validate_beat_fit(beats: list[NarrationBeat]) -> list[str]:
        """Check whether narration audio fits within designated animation timing slots."""
        warnings: list[str] = []
        for b in beats:
            if b.clip is not None and b.target_duration is not None:
                if b.clip.duration > b.target_duration:
                    excess = b.clip.duration - b.target_duration
                    warnings.append(
                        f"Beat '{b.id}': Spoken audio ({b.clip.duration:.2f}s) exceeds visual slot "
                        f"({b.target_duration:.2f}s) by {excess:.2f}s. Narration may overlap."
                    )
        return warnings

    @staticmethod
    def stitch_narration_beats(
        beats: list[NarrationBeat],
        output_path: str | Path,
        sample_rate: int = 24000,
        total_duration: float | None = None,
    ) -> AudioClip:
        """Combine multiple per-scene narration clips into a single aligned audio track.

        Pads with silence between beats so each beat plays at its designated start_time.
        """
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Determine total duration
        calculated_end = 0.0
        for b in beats:
            if b.clip is not None:
                b_start = b.start_time or 0.0
                calculated_end = max(calculated_end, b_start + b.clip.duration)

        end_duration = total_duration if total_duration is not None else calculated_end
        total_samples = int(np.ceil(end_duration * sample_rate))

        # 2. Allocate 16-bit PCM buffer
        audio_buffer = np.zeros(total_samples, dtype=np.int16)
        all_words: list[WordTimestamp] = []
        full_text_parts: list[str] = []

        # 3. Paste each beat into buffer
        for b in beats:
            if b.clip is None or not Path(b.clip.audio_path).exists():
                continue

            b_start = b.start_time or 0.0
            start_sample = int(round(b_start * sample_rate))

            with wave.open(str(b.clip.audio_path), "rb") as wf:
                raw_bytes = wf.readframes(wf.getnframes())
                clip_samples = np.frombuffer(raw_bytes, dtype=np.int16)

            end_sample = min(total_samples, start_sample + len(clip_samples))
            audio_buffer[start_sample:end_sample] = clip_samples[: end_sample - start_sample]

            # Shift word timestamps by b_start
            for w in b.clip.words:
                all_words.append(
                    WordTimestamp(
                        word=w.word,
                        start=round(w.start + b_start, 3),
                        end=round(w.end + b_start, 3),
                        confidence=w.confidence,
                    )
                )

            full_text_parts.append(b.clip.text or b.text)

        # 4. Write unified WAV
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_buffer.tobytes())

        return AudioClip(
            audio_path=str(output_path),
            duration=round(end_duration, 3),
            sample_rate=sample_rate,
            text=" ".join(full_text_parts),
            words=all_words,
            provider="stitched",
            voice="mixed",
            metadata={"beats_count": len(beats)},
        )
