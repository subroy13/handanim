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
        sample_rate: int | None = None,
        total_duration: float | None = None,
    ) -> AudioClip:
        """Combine multiple per-scene narration clips into a single aligned audio track.

        Pads with silence between beats so each beat plays at its designated start_time.
        Preserves native sample rate when ``sample_rate=None`` and resamples any mismatched clips.
        """
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Determine total duration and target sample rate
        calculated_end = 0.0
        detected_rates: list[int] = []
        for b in beats:
            if b.clip is not None:
                b_start = b.start_time or 0.0
                calculated_end = max(calculated_end, b_start + b.clip.duration)
                if Path(b.clip.audio_path).exists():
                    with wave.open(str(b.clip.audio_path), "rb") as wf:
                        detected_rates.append(int(wf.getframerate()))
                elif b.clip.sample_rate:
                    detected_rates.append(int(b.clip.sample_rate))

        target_sr = int(sample_rate) if sample_rate is not None else (max(detected_rates) if detected_rates else 24000)
        end_duration = total_duration if total_duration is not None else calculated_end
        total_samples = int(np.ceil(end_duration * target_sr))

        # 2. Allocate 16-bit PCM buffer
        audio_buffer = np.zeros(max(1, total_samples), dtype=np.int16)
        all_words: list[WordTimestamp] = []
        full_text_parts: list[str] = []

        # 3. Paste each beat into buffer (resampling if clip sample rate differs from target_sr)
        for b in beats:
            if b.clip is None or not Path(b.clip.audio_path).exists():
                continue

            b_start = b.start_time or 0.0
            start_sample = int(round(b_start * target_sr))

            with wave.open(str(b.clip.audio_path), "rb") as wf:
                clip_sr = int(wf.getframerate())
                n_channels = int(wf.getnchannels())
                raw_bytes = wf.readframes(wf.getnframes())
                clip_samples = np.frombuffer(raw_bytes, dtype=np.int16)

            if n_channels > 1 and len(clip_samples) >= n_channels:
                clip_samples = clip_samples.reshape(-1, n_channels).mean(axis=1).astype(np.int16)

            if clip_sr != target_sr and len(clip_samples) > 1:
                new_len = max(1, int(round(len(clip_samples) * target_sr / clip_sr)))
                x_old = np.linspace(0.0, 1.0, len(clip_samples), dtype=np.float64)
                x_new = np.linspace(0.0, 1.0, new_len, dtype=np.float64)
                clip_samples = np.clip(
                    np.round(np.interp(x_new, x_old, clip_samples.astype(np.float64))),
                    -32768,
                    32767,
                ).astype(np.int16)

            end_sample = min(len(audio_buffer), start_sample + len(clip_samples))
            if end_sample > start_sample:
                audio_buffer[start_sample:end_sample] = clip_samples[: end_sample - start_sample]

            # Shift word timestamps by b_start
            for w in b.clip.words:
                all_words.append(
                    WordTimestamp(
                        word=w.word,
                        start=round(w.start + b_start, 3),
                        end=round(w.end + b_start, 3),
                        confidence=w.confidence,
                        speaker=w.speaker,
                    )
                )

            full_text_parts.append(b.clip.text or b.text)

        # 4. Write unified WAV
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(target_sr)
            wf.writeframes(audio_buffer.tobytes())

        return AudioClip(
            audio_path=str(output_path),
            duration=round(end_duration, 3),
            sample_rate=target_sr,
            text=" ".join(full_text_parts),
            words=all_words,
            provider="stitched",
            voice="mixed",
            metadata={"beats_count": len(beats)},
        )
