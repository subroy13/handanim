"""Word-level forced alignment for voiceanim AudioClips.

Decouples accurate word-level timestamps from any specific TTS engine so that
expressive models without native duration tensors (e.g. Chatterbox, ZONOS3-Mini,
Qwen3-TTS, ElevenLabs, or recorded speech) still synchronize accurately with
handanim animations.

Supported backends (in ``backend="auto"`` priority order):
1. ``"stable_ts"`` — True forced alignment via ``stable-ts`` (``stable_whisper``).
2. ``"mlx_whisper"`` — Fast Apple Silicon Whisper transcription + script alignment.
3. ``"faster_whisper"`` — CTranslate2 Whisper word timestamps + script alignment.
4. ``"energy"`` — Zero-dependency acoustic speech-burst / pause alignment using NumPy.
5. ``"heuristic"`` — Character-length and punctuation fallback.
"""

from __future__ import annotations

import difflib
import logging
import re
import wave
from pathlib import Path
from typing import Any

import numpy as np

from .schema import AudioClip, SentenceTimestamp, WordTimestamp

logger = logging.getLogger(__name__)


def _estimate_word_timings(text: str, total_duration: float) -> list[WordTimestamp]:
    from .providers.base import BaseVoiceProvider

    return BaseVoiceProvider.estimate_word_timings(text, total_duration)


def _extract_sentences(text: str, word_timings: list[WordTimestamp]) -> list[SentenceTimestamp]:
    from .providers.base import BaseVoiceProvider

    return BaseVoiceProvider.extract_sentences(text, word_timings)


def _normalize_word(word: str) -> str:
    """Normalize a word for fuzzy script-to-transcript alignment."""
    return re.sub(r"[^a-z0-9']+", "", word.lower()).strip("'")


def _read_wav_mono_float(audio_path: str | Path) -> tuple[np.ndarray, int]:
    """Read a WAV file into a mono float32 array in [-1, 1] and its sample rate."""
    path = Path(audio_path)
    try:
        import soundfile as sf

        data, sr = sf.read(str(path), dtype="float32", always_2d=False)
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        return np.asarray(data, dtype=np.float32), int(sr)
    except Exception:
        pass

    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())

    if sampwidth == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0

    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)
    return samples, int(sr)


def _map_recognized_to_script(
    script_words: list[str],
    recognized: list[tuple[str, float, float, float]],
    total_duration: float,
) -> list[WordTimestamp]:
    """Align recognized `(word, start, end, conf)` spans back onto the exact script words.

    Preserves exact script punctuation and spelling while inheriting neural
    timestamps for matched words and interpolating unmatched gaps cleanly.
    """
    if not script_words:
        return []
    if not recognized:
        return _estimate_word_timings(" ".join(script_words), total_duration)

    norm_script = [_normalize_word(w) for w in script_words]
    norm_rec = [_normalize_word(r[0]) for r in recognized]

    matcher = difflib.SequenceMatcher(None, norm_script, norm_rec, autojunk=False)
    assigned: list[tuple[float, float, float] | None] = [None] * len(script_words)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                _, st, en, conf = recognized[j1 + offset]
                assigned[i1 + offset] = (st, en, conf)
        elif tag == "replace" and j2 > j1:
            span_start = recognized[j1][1]
            span_end = recognized[j2 - 1][2]
            span_conf = float(np.mean([r[3] for r in recognized[j1:j2]])) * 0.9
            sub_words = script_words[i1:i2]
            weights = [max(1.0, float(len(_normalize_word(w)) or len(w))) for w in sub_words]
            tot_w = sum(weights)
            cur = span_start
            dur = max(0.04, span_end - span_start)
            for idx, wt in enumerate(weights):
                w_dur = dur * (wt / tot_w)
                assigned[i1 + idx] = (cur, min(total_duration, cur + w_dur), span_conf)
                cur += w_dur

    # Interpolate any remaining None entries from neighboring matched words
    n = len(script_words)
    i = 0
    while i < n:
        if assigned[i] is not None:
            i += 1
            continue
        j = i
        while j < n and assigned[j] is None:
            j += 1
        prev_end = assigned[i - 1][1] if i > 0 and assigned[i - 1] is not None else 0.02
        next_start = assigned[j][0] if j < n and assigned[j] is not None else max(prev_end + 0.05, total_duration)
        gap = max(0.04 * (j - i), next_start - prev_end)
        sub_words = script_words[i:j]
        weights = [max(1.0, float(len(_normalize_word(w)) or len(w))) for w in sub_words]
        tot_w = sum(weights)
        cur = prev_end
        for k, wt in enumerate(weights):
            w_dur = gap * (wt / tot_w)
            assigned[i + k] = (cur, min(total_duration, cur + w_dur * 0.95), 0.75)
            cur += w_dur
        i = j

    results: list[WordTimestamp] = []
    for word, span in zip(script_words, assigned, strict=False):
        assert span is not None
        st = max(0.0, min(total_duration, float(span[0])))
        en = max(st + 0.02, min(total_duration, float(span[1])))
        if en > total_duration:
            en = total_duration
            st = max(0.0, min(st, en))
        results.append(
            WordTimestamp(
                word=word,
                start=round(st, 3),
                end=round(en, 3),
                confidence=round(float(span[2]), 3),
            )
        )
    return results


def _align_energy(
    audio_path: str | Path,
    text: str,
    frame_ms: float = 15.0,
    min_silence_ms: float = 120.0,
) -> list[WordTimestamp]:
    """Acoustic energy/VAD-guided alignment using pure NumPy (zero extra dependencies).

    Detects active speech regions and pauses in the waveform, then distributes
    clause/word durations across active speech intervals instead of across silence.
    """
    samples, sr = _read_wav_mono_float(audio_path)
    total_duration = float(len(samples)) / float(max(1, sr))
    words = text.strip().split()
    if not words or total_duration <= 0:
        return []

    frame_len = max(1, int(round(sr * frame_ms / 1000.0)))
    n_frames = max(1, len(samples) // frame_len)
    trimmed = samples[: n_frames * frame_len].reshape(n_frames, frame_len)
    rms = np.sqrt(np.mean(trimmed**2, axis=1) + 1e-12)

    peak = float(np.percentile(rms, 95))
    noise_floor = float(np.percentile(rms, 10))
    if peak <= 1e-6:
        return _estimate_word_timings(text, total_duration)

    threshold = max(noise_floor * 2.2, peak * 0.08)
    is_speech = rms >= threshold

    # Morphological closing: bridge short intra-word dips (< min_silence_ms)
    min_sil_frames = max(1, int(round(min_silence_ms / frame_ms)))
    speech_mask = is_speech.copy()
    i = 0
    while i < n_frames:
        if not speech_mask[i]:
            j = i
            while j < n_frames and not speech_mask[j]:
                j += 1
            if i > 0 and j < n_frames and (j - i) < min_sil_frames:
                speech_mask[i:j] = True
            i = j
        else:
            i += 1

    # Extract contiguous active speech segments [(start_sec, end_sec), ...]
    segments: list[tuple[float, float]] = []
    i = 0
    while i < n_frames:
        if speech_mask[i]:
            j = i
            while j < n_frames and speech_mask[j]:
                j += 1
            seg_start = i * frame_len / float(sr)
            seg_end = min(total_duration, j * frame_len / float(sr))
            if seg_end - seg_start >= 0.04:
                segments.append((seg_start, seg_end))
            i = j
        else:
            i += 1

    if not segments:
        return _estimate_word_timings(text, total_duration)

    # Split words into punctuation clauses (e.g., "99%?" | "No," | "much smaller!")
    # and assign cumulative active speech time proportionally to word weights.
    weights: list[float] = []
    for w in words:
        clean = _normalize_word(w)
        wt = max(1.2, float(len(clean) or len(w)))
        if any(p in w for p in (".", "!", "?")):
            wt += 0.8
        elif "," in w or "—" in w or ";" in w:
            wt += 0.4
        weights.append(wt)

    seg_durations = [en - st for st, en in segments]
    total_active = sum(seg_durations)
    total_weight = sum(weights)

    def active_time_to_wall(t_active: float) -> float:
        rem = max(0.0, min(total_active, t_active))
        for (st, _en), dur in zip(segments, seg_durations, strict=False):
            if rem <= dur + 1e-9:
                return st + rem
            rem -= dur
        return segments[-1][1]

    timings: list[WordTimestamp] = []
    cur_active = 0.0
    for word, wt in zip(words, weights, strict=False):
        w_active = total_active * (wt / total_weight)
        w_start = active_time_to_wall(cur_active)
        w_end = active_time_to_wall(cur_active + w_active * 0.94)
        if w_end <= w_start:
            w_end = min(total_duration, w_start + 0.04)
        timings.append(
            WordTimestamp(
                word=word,
                start=round(w_start, 3),
                end=round(w_end, 3),
                confidence=0.88,
            )
        )
        cur_active += w_active

    return timings


class ForcedAligner:
    """Forced word-level aligner supporting neural Whisper backends and acoustic VAD fallback."""

    _stable_ts_models: dict[str, Any] = {}
    _faster_whisper_models: dict[str, Any] = {}

    def __init__(
        self,
        backend: str = "auto",
        model_size: str = "base",
        language: str = "en",
    ):
        self.backend = backend.lower().strip()
        self.model_size = model_size
        self.language = language

    @classmethod
    def available_backends(cls) -> list[str]:
        """Return list of currently importable alignment backends on this machine."""
        available: list[str] = []
        for mod_name, backend_name in (
            ("stable_whisper", "stable_ts"),
            ("mlx_whisper", "mlx_whisper"),
            ("faster_whisper", "faster_whisper"),
        ):
            try:
                __import__(mod_name)
                available.append(backend_name)
            except ImportError:
                continue
        available.extend(["energy", "heuristic"])
        return available

    def _align_stable_ts(self, audio_path: Path, text: str, total_duration: float) -> list[WordTimestamp]:
        import stable_whisper

        key = self.model_size
        if key not in self._stable_ts_models:
            self._stable_ts_models[key] = stable_whisper.load_model(self.model_size)
        model = self._stable_ts_models[key]
        result = model.align(str(audio_path), text, language=self.language)
        recognized: list[tuple[str, float, float, float]] = []
        for seg in getattr(result, "segments", []):
            for w in getattr(seg, "words", []):
                word_str = str(getattr(w, "word", "")).strip()
                if word_str:
                    recognized.append(
                        (
                            word_str,
                            float(getattr(w, "start", 0.0)),
                            float(getattr(w, "end", 0.0)),
                            float(getattr(w, "probability", 0.96) or 0.96),
                        )
                    )
        return _map_recognized_to_script(text.strip().split(), recognized, total_duration)

    def _align_mlx_whisper(self, audio_path: Path, text: str, total_duration: float) -> list[WordTimestamp]:
        import mlx_whisper

        repo_map = {
            "tiny": "mlx-community/whisper-tiny-mlx",
            "base": "mlx-community/whisper-base-mlx",
            "small": "mlx-community/whisper-small-mlx",
            "medium": "mlx-community/whisper-medium-mlx",
            "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
        }
        hf_repo = repo_map.get(self.model_size, self.model_size)
        samples, sr = _read_wav_mono_float(audio_path)
        if sr != 16000 and samples.size > 1:
            n_out = max(1, int(round(samples.size * 16000.0 / float(sr))))
            samples = np.interp(
                np.linspace(0.0, float(samples.size - 1), n_out),
                np.arange(samples.size, dtype=np.float64),
                samples.astype(np.float64),
            ).astype(np.float32)
        result = mlx_whisper.transcribe(
            samples,
            path_or_hf_repo=hf_repo,
            word_timestamps=True,
            language=self.language,
        )
        recognized: list[tuple[str, float, float, float]] = []
        for seg in result.get("segments", []):
            for w in seg.get("words", []):
                word_str = str(w.get("word", "")).strip()
                if word_str:
                    recognized.append(
                        (
                            word_str,
                            float(w.get("start", 0.0)),
                            float(w.get("end", 0.0)),
                            float(w.get("probability", 0.95) or 0.95),
                        )
                    )
        return _map_recognized_to_script(text.strip().split(), recognized, total_duration)

    def _align_faster_whisper(self, audio_path: Path, text: str, total_duration: float) -> list[WordTimestamp]:
        from faster_whisper import WhisperModel

        key = self.model_size
        if key not in self._faster_whisper_models:
            self._faster_whisper_models[key] = WhisperModel(self.model_size, device="auto", compute_type="int8")
        model = self._faster_whisper_models[key]
        segments, _info = model.transcribe(str(audio_path), word_timestamps=True, language=self.language)
        recognized: list[tuple[str, float, float, float]] = []
        for seg in segments:
            for w in seg.words or []:
                word_str = str(w.word).strip()
                if word_str:
                    recognized.append((word_str, float(w.start), float(w.end), float(w.probability or 0.95)))
        return _map_recognized_to_script(text.strip().split(), recognized, total_duration)

    def align(
        self,
        audio_path: str | Path,
        text: str,
        duration: float | None = None,
    ) -> tuple[list[WordTimestamp], str]:
        """Align `text` to `audio_path` and return `(word_timestamps, backend_used)`."""
        path = Path(audio_path)
        if duration is None:
            samples, sr = _read_wav_mono_float(path)
            duration = float(len(samples)) / float(max(1, sr))

        if not text.strip() or duration <= 0:
            return [], "none"

        order = (
            ["stable_ts", "mlx_whisper", "faster_whisper", "energy", "heuristic"]
            if self.backend == "auto"
            else [self.backend]
        )

        for candidate in order:
            try:
                if candidate == "stable_ts":
                    return self._align_stable_ts(path, text, duration), "stable_ts"
                if candidate == "mlx_whisper":
                    return self._align_mlx_whisper(path, text, duration), "mlx_whisper"
                if candidate == "faster_whisper":
                    return self._align_faster_whisper(path, text, duration), "faster_whisper"
                if candidate == "energy":
                    return _align_energy(path, text), "energy"
                if candidate == "heuristic":
                    return _estimate_word_timings(text, duration), "heuristic"
                raise ValueError(f"Unknown forced-alignment backend: '{candidate}'")
            except ImportError:
                if self.backend != "auto":
                    raise
                continue
            except Exception as exc:
                if self.backend != "auto":
                    raise
                logger.warning("Forced alignment backend '%s' failed (%s); trying next fallback.", candidate, exc)
                continue

        return _estimate_word_timings(text, duration), "heuristic"


def align_words(
    audio_path: str | Path,
    text: str,
    *,
    backend: str = "auto",
    model_size: str = "base",
    language: str = "en",
    duration: float | None = None,
) -> list[WordTimestamp]:
    """Convenience function to compute word timestamps for an audio file and script text."""
    aligner = ForcedAligner(backend=backend, model_size=model_size, language=language)
    words, _used = aligner.align(audio_path, text, duration=duration)
    return words


def align_clip(
    clip: AudioClip,
    *,
    backend: str = "auto",
    model_size: str = "base",
    language: str = "en",
) -> AudioClip:
    """Re-align an existing `AudioClip` in place and refresh its `words` and `sentences`."""
    aligner = ForcedAligner(backend=backend, model_size=model_size, language=language)
    words, used_backend = aligner.align(clip.audio_path, clip.text, duration=clip.duration)
    clip.words = words
    clip.sentences = _extract_sentences(clip.text, words)
    clip.metadata["alignment_backend"] = used_backend
    return clip
