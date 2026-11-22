"""Data models and schemas for voiceanim speech synthesis, timestamps, and narration."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class WordTimestamp:
    """Timestamp for an individual spoken word."""

    word: str
    start: float  # seconds
    end: float  # seconds
    confidence: float = 1.0
    speaker: str | None = None

    @property
    def duration(self) -> float:
        return round(max(0.0, self.end - self.start), 6)

    def to_dict(self) -> dict:
        d = asdict(self)
        if d.get("speaker") is None:
            d.pop("speaker", None)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> WordTimestamp:
        return cls(
            word=str(data.get("word", "")),
            start=float(data.get("start", 0.0)),
            end=float(data.get("end", 0.0)),
            confidence=float(data.get("confidence", 1.0)),
            speaker=data.get("speaker"),
        )


@dataclass
class SentenceTimestamp:
    """Timestamp for a sentence or complete phrase."""

    text: str
    start: float
    end: float
    words: list[WordTimestamp] = field(default_factory=list)
    speaker: str | None = None

    @property
    def duration(self) -> float:
        return round(max(0.0, self.end - self.start), 6)

    def to_dict(self) -> dict:
        d = {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "words": [w.to_dict() for w in self.words],
        }
        if self.speaker is not None:
            d["speaker"] = self.speaker
        return d

    @classmethod
    def from_dict(cls, data: dict) -> SentenceTimestamp:
        words = [WordTimestamp.from_dict(w) for w in data.get("words", [])]
        return cls(
            text=str(data.get("text", "")),
            start=float(data.get("start", 0.0)),
            end=float(data.get("end", 0.0)),
            words=words,
            speaker=data.get("speaker"),
        )


@dataclass
class AudioClip:
    """Audio clip representation with speech marks, alignment timestamps, and metadata."""

    audio_path: str
    duration: float
    sample_rate: int = 24000
    text: str = ""
    words: list[WordTimestamp] = field(default_factory=list)
    sentences: list[SentenceTimestamp] = field(default_factory=list)
    provider: str = ""
    voice: str = ""
    instruct: str | None = None
    metadata: dict = field(default_factory=dict)

    def get_word_time(self, target_word: str, occurrence: int = 1) -> float | None:
        """Find the start timestamp in seconds of the N-th occurrence of a word.

        Args:
            target_word: The word to find (case-insensitive, punctuation-stripped).
            occurrence: Which occurrence (1-based index). Defaults to 1 (first).

        Returns:
            Start time in seconds, or None if not found.
        """
        clean_target = re.sub(r"[^\w\s]", "", target_word).strip().lower()
        count = 0
        for w in self.words:
            clean_word = re.sub(r"[^\w\s]", "", w.word).strip().lower()
            if clean_word == clean_target:
                count += 1
                if count == occurrence:
                    return w.start
        return None

    def get_word_range(self, target_word: str, occurrence: int = 1) -> tuple[float, float] | None:
        """Find the (start, end) timestamp range of the N-th occurrence of a word."""
        clean_target = re.sub(r"[^\w\s]", "", target_word).strip().lower()
        count = 0
        for w in self.words:
            clean_word = re.sub(r"[^\w\s]", "", w.word).strip().lower()
            if clean_word == clean_target:
                count += 1
                if count == occurrence:
                    return (w.start, w.end)
        return None

    def export_srt(self, output_path: str | Path | None = None) -> str:
        """Export speech marks as standard SubRip (.srt) subtitle string or file.

        Uses sentence timestamps when available, falling back to word grouping.
        """
        entries: list[SentenceTimestamp | dict] = (
            list(self.sentences) if self.sentences else list(self._group_words_into_phrases())
        )
        srt_lines: list[str] = []

        def format_timestamp(seconds: float) -> str:
            hrs = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int(round((seconds - int(seconds)) * 1000))
            return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

        for idx, entry in enumerate(entries, 1):
            if isinstance(entry, SentenceTimestamp):
                text = entry.text
                start = entry.start
                end = entry.end
            else:
                text = str(entry["text"])
                start = float(entry["start"])
                end = float(entry["end"])

            srt_lines.append(str(idx))
            srt_lines.append(f"{format_timestamp(start)} --> {format_timestamp(end)}")
            srt_lines.append(text)
            srt_lines.append("")

        content = "\n".join(srt_lines)
        if output_path:
            Path(output_path).write_text(content, encoding="utf-8")
        return content

    def export_vtt(self, output_path: str | Path | None = None) -> str:
        """Export speech marks as WebVTT (.vtt) subtitle format."""
        srt_content = self.export_srt()
        # WebVTT uses . instead of , for millisecond separator and has WEBVTT header
        vtt_content = "WEBVTT\n\n" + re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", srt_content)
        if output_path:
            Path(output_path).write_text(vtt_content, encoding="utf-8")
        return vtt_content

    def _group_words_into_phrases(self, words_per_chunk: int = 6) -> list[dict]:
        """Fallback to group word timestamps into manageable subtitle phrases."""
        if not self.words:
            return [{"text": self.text, "start": 0.0, "end": self.duration}]

        chunks = []
        for i in range(0, len(self.words), words_per_chunk):
            chunk_words = self.words[i : i + words_per_chunk]
            phrase = " ".join(w.word for w in chunk_words)
            chunks.append({
                "text": phrase,
                "start": chunk_words[0].start,
                "end": chunk_words[-1].end,
            })
        return chunks

    def to_dict(self) -> dict:
        return {
            "audio_path": self.audio_path,
            "duration": self.duration,
            "sample_rate": self.sample_rate,
            "text": self.text,
            "words": [w.to_dict() for w in self.words],
            "sentences": [s.to_dict() for s in self.sentences],
            "provider": self.provider,
            "voice": self.voice,
            "instruct": self.instruct,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AudioClip:
        return cls(
            audio_path=str(data.get("audio_path", "")),
            duration=float(data.get("duration", 0.0)),
            sample_rate=int(data.get("sample_rate", 24000)),
            text=str(data.get("text", "")),
            words=[WordTimestamp.from_dict(w) for w in data.get("words", [])],
            sentences=[SentenceTimestamp.from_dict(s) for s in data.get("sentences", [])],
            provider=str(data.get("provider", "")),
            voice=str(data.get("voice", "")),
            instruct=data.get("instruct"),
            metadata=dict(data.get("metadata", {})),
        )

    def save_json(self, json_path: str | Path):
        Path(json_path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load_json(cls, json_path: str | Path) -> AudioClip:
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
        return cls.from_dict(data)


@dataclass
class NarrationBeat:
    """A designated beat or section in an animation narration script with optional delivery direction."""

    id: str
    text: str
    instruct: str | None = None
    voice: str | None = None
    provider: str | None = None
    speed: float | None = None
    exaggeration: float | None = None
    cfg_weight: float | None = None
    controls: dict[str, float] | None = None
    ref_audio: str | None = None
    start_time: float | None = None
    target_duration: float | None = None
    clip: AudioClip | None = None

    @classmethod
    def from_spec(cls, spec: NarrationBeat | dict | tuple | list) -> NarrationBeat:
        """Coerce a beat specification into a `NarrationBeat`.

        Accepts:
        - `NarrationBeat` instance
        - 2-tuple `(id, text)`
        - 3-tuple `(id, text, instruct)`
        - dict with keys `id` (or `key`), `text`, and optional `instruct`, `voice`,
          `provider`, `speed`, `exaggeration`, `cfg_weight`, `controls`, `ref_audio`, etc.
        """
        if isinstance(spec, cls):
            return spec
        if isinstance(spec, dict):
            beat_id = str(spec.get("id", spec.get("key", "")))
            return cls(
                id=beat_id,
                text=str(spec.get("text", "")),
                instruct=spec.get("instruct") or spec.get("direction"),
                voice=spec.get("voice"),
                provider=spec.get("provider"),
                speed=float(spec["speed"]) if spec.get("speed") is not None else None,
                exaggeration=float(spec["exaggeration"]) if spec.get("exaggeration") is not None else None,
                cfg_weight=float(spec["cfg_weight"]) if spec.get("cfg_weight") is not None else None,
                controls=dict(spec["controls"]) if spec.get("controls") is not None else None,
                ref_audio=str(spec["ref_audio"]) if spec.get("ref_audio") is not None else None,
                start_time=float(spec["start_time"]) if spec.get("start_time") is not None else None,
                target_duration=float(spec["target_duration"]) if spec.get("target_duration") is not None else None,
            )
        if isinstance(spec, (tuple, list)) and len(spec) >= 2:
            instruct = str(spec[2]) if len(spec) >= 3 and spec[2] is not None else None
            return cls(id=str(spec[0]), text=str(spec[1]), instruct=instruct)
        raise TypeError(f"Unsupported NarrationBeat specification: {spec!r}")
