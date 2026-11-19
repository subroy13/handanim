"""Multi-voice dialogue synthesis ("Socratic conversations") for voiceanim."""

from __future__ import annotations

import tempfile
import wave
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .pronunciation import latex_to_speech
from .providers import get_provider
from .schema import AudioClip, SentenceTimestamp, WordTimestamp


@dataclass
class SpeakerProfile:
    """Voice and visual theme configuration for a dialogue participant."""

    name: str
    voice: str = "af_heart"
    provider: str = "kokoro"
    speed: float = 1.0
    instruct: str | None = None
    color: tuple[float, float, float] | None = None
    highlight: tuple[float, float, float] | None = None


@dataclass
class DialogueTurn:
    """A single spoken turn in a multi-speaker dialogue."""

    speaker: str
    text: str
    voice: str | None = None
    provider: str | None = None
    speed: float | None = None
    instruct: str | None = None
    pause_after: float | None = None


def synthesize_dialogue(
    turns: Sequence[DialogueTurn | dict[str, Any] | tuple[str, str]],
    output_path: str | Path | None = None,
    speakers: dict[str, SpeakerProfile | dict[str, Any] | str] | None = None,
    default_provider: str = "kokoro",
    pause_between: float = 0.25,
    preprocess_math: bool = True,
    sample_rate: int = 24000,
    **provider_kwargs: Any,
) -> AudioClip:
    """Synthesize a multi-speaker dialogue into a single stitched `AudioClip`.

    Each word and sentence timestamp in the returned `AudioClip` carries its
    `speaker` name, and `clip.metadata["turns"]` / `clip.metadata["speakers"]`
    record per-turn boundaries and speaker color themes for `Captions`.

    Args:
        turns: Sequence of `DialogueTurn` objects, dicts `{"speaker": ..., "text": ...}`,
            or `(speaker, text)` tuples.
        output_path: Optional output WAV path. If omitted, writes to a temporary file.
        speakers: Optional mapping from speaker name to `SpeakerProfile`, config dict,
            or voice ID string (e.g. `{"student": "am_adam", "professor": "af_heart"}`).
        default_provider: Default provider when not specified by speaker/turn (`"kokoro"`).
        pause_between: Default silence padding in seconds between consecutive turns.
        preprocess_math: If True (default), runs `latex_to_speech` on each turn's text.
        sample_rate: Output WAV sample rate (default `24000`).
    """
    speaker_map: dict[str, SpeakerProfile] = {}
    if speakers:
        for spk_name, cfg in speakers.items():
            if isinstance(cfg, SpeakerProfile):
                speaker_map[spk_name] = cfg
            elif isinstance(cfg, str):
                speaker_map[spk_name] = SpeakerProfile(
                    name=spk_name,
                    voice=cfg,
                    provider=default_provider,
                )
            elif isinstance(cfg, dict):
                speaker_map[spk_name] = SpeakerProfile(
                    name=spk_name,
                    voice=str(cfg.get("voice", "af_heart")),
                    provider=str(cfg.get("provider", default_provider)),
                    speed=float(cfg.get("speed", 1.0)),
                    instruct=cfg.get("instruct"),
                    color=tuple(cfg["color"]) if cfg.get("color") is not None else None,  # type: ignore[arg-type]
                    highlight=tuple(cfg["highlight"]) if cfg.get("highlight") is not None else None,  # type: ignore[arg-type]
                )

    normalized_turns: list[DialogueTurn] = []
    for item in turns:
        if isinstance(item, DialogueTurn):
            normalized_turns.append(item)
        elif isinstance(item, dict):
            normalized_turns.append(
                DialogueTurn(
                    speaker=str(item.get("speaker", "narrator")),
                    text=str(item.get("text", "")),
                    voice=item.get("voice"),
                    provider=item.get("provider"),
                    speed=float(item["speed"]) if item.get("speed") is not None else None,
                    instruct=item.get("instruct"),
                    pause_after=float(item["pause_after"]) if item.get("pause_after") is not None else None,
                )
            )
        elif isinstance(item, (tuple, list)) and len(item) >= 2:
            normalized_turns.append(DialogueTurn(speaker=str(item[0]), text=str(item[1])))
        else:
            raise TypeError(f"Unsupported dialogue turn: {item!r}")

    if output_path is None:
        fd, tmp_wav = tempfile.mkstemp(prefix="voiceanim_dialogue_", suffix=".wav")
        import os

        os.close(fd)
        target_path = Path(tmp_wav)
    else:
        target_path = Path(output_path).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)

    # Default voice alternation if speaker not explicitly configured
    default_voices = ["af_heart", "am_adam", "bf_emma", "bm_george"]
    seen_speakers: list[str] = []

    turn_clips: list[tuple[DialogueTurn, AudioClip, float]] = []
    for idx, turn in enumerate(normalized_turns):
        if turn.speaker not in seen_speakers:
            seen_speakers.append(turn.speaker)
        spk_idx = seen_speakers.index(turn.speaker)
        profile = speaker_map.get(turn.speaker)

        prov_name = turn.provider or (profile.provider if profile else default_provider)
        voice_id = turn.voice or (
            profile.voice if profile else default_voices[spk_idx % len(default_voices)]
        )
        speed = turn.speed if turn.speed is not None else (profile.speed if profile else 1.0)
        instruct = turn.instruct if turn.instruct is not None else (profile.instruct if profile else None)
        pause = (
            float(turn.pause_after)
            if turn.pause_after is not None
            else (float(pause_between) if idx < len(normalized_turns) - 1 else 0.0)
        )

        spoken_text = latex_to_speech(turn.text) if preprocess_math else turn.text
        provider = get_provider(prov_name, **provider_kwargs)
        clip = provider.synthesize(
            text=spoken_text,
            voice=voice_id,
            speed=speed,
            instruct=instruct,
        )
        turn_clips.append((turn, clip, max(0.0, pause)))

    # Calculate total duration and stitch PCM samples
    cursor = 0.0
    turn_Start_times: list[float] = []
    for _turn, clip, pause in turn_clips:
        turn_Start_times.append(cursor)
        cursor += clip.duration + pause

    total_duration = max(0.0, cursor)
    total_samples = int(np.ceil(total_duration * sample_rate))
    audio_buffer = np.zeros(max(1, total_samples), dtype=np.int16)

    all_words: list[WordTimestamp] = []
    all_sentences: list[SentenceTimestamp] = []
    turn_metadata: list[dict[str, Any]] = []
    full_text_parts: list[str] = []

    for (turn, clip, _pause), start_t in zip(turn_clips, turn_Start_times, strict=False):
        if Path(clip.audio_path).exists():
            with wave.open(str(clip.audio_path), "rb") as wf:
                clip_sr = wf.getframerate()
                raw_bytes = wf.readframes(wf.getnframes())
                clip_samples = np.frombuffer(raw_bytes, dtype=np.int16)
            if clip_sr != sample_rate and len(clip_samples) > 1:
                new_len = int(round(len(clip_samples) * sample_rate / clip_sr))
                x_old = np.linspace(0.0, 1.0, len(clip_samples))
                x_new = np.linspace(0.0, 1.0, max(1, new_len))
                clip_samples = np.interp(x_new, x_old, clip_samples.astype(np.float32)).astype(np.int16)

            start_sample = int(round(start_t * sample_rate))
            end_sample = min(len(audio_buffer), start_sample + len(clip_samples))
            if end_sample > start_sample:
                audio_buffer[start_sample:end_sample] = clip_samples[: end_sample - start_sample]

        turn_words: list[WordTimestamp] = []
        for w in clip.words:
            shifted_w = WordTimestamp(
                word=w.word,
                start=round(w.start + start_t, 3),
                end=round(w.end + start_t, 3),
                confidence=w.confidence,
                speaker=turn.speaker,
            )
            all_words.append(shifted_w)
            turn_words.append(shifted_w)

        all_sentences.append(
            SentenceTimestamp(
                text=turn.text,
                start=round(start_t, 3),
                end=round(start_t + clip.duration, 3),
                words=turn_words,
                speaker=turn.speaker,
            )
        )
        turn_metadata.append(
            {
                "speaker": turn.speaker,
                "text": turn.text,
                "start": round(start_t, 3),
                "end": round(start_t + clip.duration, 3),
                "voice": clip.voice,
            }
        )
        full_text_parts.append(f"{turn.speaker}: {turn.text}")

    with wave.open(str(target_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_buffer.tobytes())

    speaker_theme_meta: dict[str, dict[str, Any]] = {}
    for spk_name, prof in speaker_map.items():
        speaker_theme_meta[spk_name] = {
            "voice": prof.voice,
            "provider": prof.provider,
            "color": list(prof.color) if prof.color is not None else None,
            "highlight": list(prof.highlight) if prof.highlight is not None else None,
        }

    return AudioClip(
        audio_path=str(target_path),
        duration=round(total_duration, 3),
        sample_rate=sample_rate,
        text=" ".join(full_text_parts),
        words=all_words,
        sentences=all_sentences,
        provider=default_provider,
        voice="dialogue",
        metadata={
            "turns": turn_metadata,
            "speakers": speaker_theme_meta,
        },
    )
