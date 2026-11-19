"""Audio and video multiplexing and multi-track soundtrack mixing."""

from __future__ import annotations

import logging
import math
import os
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import imageio_ffmpeg
import numpy as np

from .sfx import (
    DEFAULT_SR,
    THEME_PRESETS,
    loop_audio_array,
    read_audio_mono,
    synthesize_chalk_sound,
    synthesize_crumple_sound,
    synthesize_ding_sound,
    synthesize_eraser_sound,
    synthesize_page_turn_sound,
    synthesize_pop_sound,
    synthesize_theme_loop,
    synthesize_whoosh_sound,
    write_wav_mono,
    write_wav_stereo,
)

logger = logging.getLogger(__name__)


def _k_weight_channel(x: np.ndarray, sample_rate: int) -> np.ndarray:
    """Apply ITU-R BS.1770-4 K-weighting filter (high-shelf + RLB high-pass)."""
    if len(x) < 8:
        return x
    try:
        from scipy.signal import lfilter

        # ITU-R BS.1770-4 bilinear transform design for arbitrary sample_rate
        # Stage 1: acoustic head-model high-shelf (+4 dB above ~1.5 kHz)
        f0_1 = 1681.974450955533
        g_1 = 3.999843853973347
        q_1 = 0.7071752369554196
        k1 = math.tan(math.pi * f0_1 / sample_rate)
        vh = 10.0 ** (g_1 / 20.0)
        vb = vh**0.4996667741545416
        a0_1 = 1.0 + k1 / q_1 + k1 * k1
        b1 = np.array(
            [
                (vh + vb * k1 / q_1 + k1 * k1) / a0_1,
                2.0 * (k1 * k1 - vh) / a0_1,
                (vh - vb * k1 / q_1 + k1 * k1) / a0_1,
            ],
            dtype=np.float64,
        )
        a1 = np.array(
            [
                1.0,
                2.0 * (k1 * k1 - 1.0) / a0_1,
                (1.0 - k1 / q_1 + k1 * k1) / a0_1,
            ],
            dtype=np.float64,
        )

        # Stage 2: RLB high-pass filter (~38 Hz)
        f0_2 = 38.13547087602444
        q_2 = 0.5003270373238773
        k2 = math.tan(math.pi * f0_2 / sample_rate)
        a0_2 = 1.0 + k2 / q_2 + k2 * k2
        b2 = np.array([1.0, -2.0, 1.0], dtype=np.float64) / a0_2
        a2 = np.array(
            [
                1.0,
                2.0 * (k2 * k2 - 1.0) / a0_2,
                (1.0 - k2 / q_2 + k2 * k2) / a0_2,
            ],
            dtype=np.float64,
        )
        y = lfilter(b1, a1, x)
        return np.asarray(lfilter(b2, a2, y), dtype=np.float64)
    except Exception:
        return x


def measure_integrated_lufs(audio: np.ndarray, sample_rate: int = DEFAULT_SR) -> float:
    """Measure ITU-R BS.1770-4 integrated loudness in LUFS."""
    arr = np.asarray(audio, dtype=np.float64)
    if arr.size == 0 or float(np.max(np.abs(arr))) < 1e-9:
        return -float("inf")

    try:
        import pyloudnorm as pyln  # type: ignore[import-not-found]

        meter = pyln.Meter(sample_rate)
        return float(meter.integrated_loudness(arr))
    except Exception:
        pass

    if arr.ndim == 1:
        channels = [_k_weight_channel(arr, sample_rate)]
    else:
        channels = [_k_weight_channel(arr[:, c], sample_rate) for c in range(arr.shape[1])]

    n = len(channels[0])
    block_len = int(round(0.4 * sample_rate))
    step_len = max(1, int(round(0.1 * sample_rate)))

    if n < block_len:
        mean_sq = sum(float(np.mean(ch * ch)) for ch in channels)
        return float(-0.691 + 10.0 * math.log10(max(1e-18, mean_sq)))

    starts = range(0, n - block_len + 1, step_len)
    block_powers = np.array(
        [
            sum(float(np.mean(ch[s : s + block_len] ** 2)) for ch in channels)
            for s in starts
        ],
        dtype=np.float64,
    )
    block_lufs = -0.691 + 10.0 * np.log10(np.maximum(1e-18, block_powers))

    # Absolute gate at -70 LUFS
    abs_mask = block_lufs > -70.0
    if not np.any(abs_mask):
        return -float("inf")

    rel_thresh = -0.691 + 10.0 * math.log10(float(np.mean(block_powers[abs_mask]))) - 10.0
    rel_mask = abs_mask & (block_lufs > rel_thresh)
    if not np.any(rel_mask):
        return float(-0.691 + 10.0 * math.log10(float(np.mean(block_powers[abs_mask]))))

    return float(-0.691 + 10.0 * math.log10(float(np.mean(block_powers[rel_mask]))))


def _measure_true_peak(audio: np.ndarray) -> float:
    """Estimate 4x oversampled true peak of a 1D or 2D audio signal."""
    arr = np.asarray(audio, dtype=np.float64)
    if arr.size == 0:
        return 0.0
    sample_peak = float(np.max(np.abs(arr)))
    if len(arr) < 4:
        return sample_peak
    # 4-point cubic/Catmull-Rom midpoint interpolation to catch inter-sample peaks
    if arr.ndim == 1:
        x0, x1, x2, x3 = arr[:-3], arr[1:-2], arr[2:-1], arr[3:]
        mid = -0.0625 * x0 + 0.5625 * x1 + 0.5625 * x2 - 0.0625 * x3
        q1 = -0.0703125 * x0 + 0.8671875 * x1 + 0.2265625 * x2 - 0.0234375 * x3
        q3 = -0.0234375 * x0 + 0.2265625 * x1 + 0.8671875 * x2 - 0.0703125 * x3
        inter_peak = max(
            float(np.max(np.abs(mid))),
            float(np.max(np.abs(q1))),
            float(np.max(np.abs(q3))),
        )
        return max(sample_peak, inter_peak)
    return max(_measure_true_peak(arr[:, c]) for c in range(arr.shape[1]))


def normalize_and_limit(
    audio: np.ndarray,
    sample_rate: int = DEFAULT_SR,
    target_lufs: float | None = -14.0,
    ceiling_dbfs: float = -1.5,
) -> np.ndarray:
    """Normalize integrated loudness to `target_lufs` (-14 LUFS default) with a true-peak soft-knee limiter."""
    y = np.asarray(audio, dtype=np.float64).copy()
    if y.size == 0:
        return y

    if target_lufs is not None:
        current_lufs = measure_integrated_lufs(y, sample_rate=sample_rate)
        if math.isfinite(current_lufs) and current_lufs > -70.0:
            gain = 10.0 ** ((float(target_lufs) - current_lufs) / 20.0)
            y *= gain

    ceiling = 10.0 ** (float(ceiling_dbfs) / 20.0)
    peak = float(np.max(np.abs(y)))
    if peak > ceiling * 0.8:
        thr = ceiling * 0.8
        a = np.abs(y)
        over = a > thr
        y[over] = np.sign(y[over]) * (
            thr + (ceiling - thr) * np.tanh((a[over] - thr) / max(1e-9, ceiling - thr))
        )

    tp = _measure_true_peak(y)
    if tp > ceiling:
        y *= (ceiling * 0.995) / tp

    return y


def mix_soundtrack(
    duration: float,
    narration: Any = None,
    background_music: Any = None,
    music_volume: float = 0.18,
    music_loop: bool = True,
    duck_music: bool = True,
    sfx_events: Sequence[dict[str, Any] | tuple[Any, ...]] | None = None,
    output_path: str | Path | None = None,
    sample_rate: int = DEFAULT_SR,
    target_lufs: float | None = -14.0,
    ceiling_dbfs: float = -1.5,
    stereo: bool = True,
) -> str:
    """Mix narration, repeating background theme music, and timed SFX (chalk, eraser, etc.) into a WAV file.

    Args:
        duration: Total duration of the soundtrack in seconds.
        narration: Optional `AudioClip` or path to a narration audio file.
        background_music: Optional background music source:
            - `True` or `"marimba"` / `"theme"` / `"calm"` / `"upbeat"` for built-in open-source theme music
            - Path to an audio file (`.wav`, `.mp3`, etc.) or an `AudioClip`
        music_volume: Volume multiplier for the background music track (default `0.18`).
        music_loop: Whether to repeat the background music across the full `duration` (default `True`).
        duck_music: Whether to automatically duck background music volume while speech is active.
        sfx_events: List of sound effect dicts `{"type": "chalk"|"eraser"|..., "start_time": float, "duration": float, "volume": float}`
            or tuples `(start_time, kind, duration[, volume])`.
        output_path: Destination `.wav` file path. If `None`, creates a temporary `.wav` file.
        sample_rate: Sample rate in Hz (default `44100`).

    Returns:
        Path to the mixed `.wav` file.
    """
    dur = max(0.1, float(duration))
    n_total = int(round(dur * sample_rate))
    voice_track = np.zeros(n_total, dtype=np.float64)
    has_voice = False

    # 1. Load narration track if present
    if narration is not None:
        narr_path = narration.audio_path if hasattr(narration, "audio_path") else narration
        if narr_path is not None:
            v_samples = read_audio_mono(narr_path, target_sr=sample_rate)
            copy_len = min(n_total, len(v_samples))
            if copy_len > 0:
                voice_track[:copy_len] = v_samples[:copy_len]
                has_voice = True

    # 2. Build background music track (looped on repeat if music_loop=True)
    music_track = np.zeros(n_total, dtype=np.float64)
    if background_music is not None and background_music is not False:
        if background_music is True:
            theme_style = "marimba"
            raw_music = synthesize_theme_loop(bars=4, style=theme_style, sample_rate=sample_rate)
        elif isinstance(background_music, str) and background_music.lower() in THEME_PRESETS:
            raw_music = synthesize_theme_loop(bars=4, style=background_music.lower(), sample_rate=sample_rate)
        elif hasattr(background_music, "audio_path"):
            raw_music = read_audio_mono(background_music.audio_path, target_sr=sample_rate)
        elif isinstance(background_music, (str, Path)):
            raw_music = read_audio_mono(background_music, target_sr=sample_rate)
        elif isinstance(background_music, np.ndarray):
            raw_music = np.asarray(background_music, dtype=np.float64).ravel()
        else:
            raise TypeError(f"Unsupported background_music source: {background_music!r}")

        if music_loop:
            music_track = loop_audio_array(
                raw_music,
                duration=dur,
                sample_rate=sample_rate,
                crossfade=0.04,
                fade_in=0.25,
                fade_out=min(0.8, dur * 0.25),
                volume=music_volume,
            )
        else:
            copy_len = min(n_total, len(raw_music))
            music_track[:copy_len] = raw_music[:copy_len] * float(music_volume)

    # Compute speech activity envelope for auto-ducking music and sketch SFX under voice
    duck_curve: np.ndarray | None = None
    if has_voice and duck_music:
        win_short = max(1, int(0.08 * sample_rate))
        win_smooth = max(1, int(0.22 * sample_rate))
        env = np.convolve(np.abs(voice_track), np.ones(win_short) / win_short, mode="same")
        speech_active = (env > 0.015).astype(np.float64)
        duck_curve = np.clip(
            np.convolve(speech_active, np.ones(win_smooth) / win_smooth, mode="same"),
            0.0,
            1.0,
        )
        music_track *= 1.0 - 0.55 * duck_curve

    # 3. Synthesize and place timed SFX events (chalk, eraser, pop, whoosh, ding)
    sfx_track = np.zeros(n_total, dtype=np.float64)
    if sfx_events:
        for idx, ev in enumerate(sfx_events):
            if isinstance(ev, dict):
                kind = str(ev.get("type", ev.get("kind", "chalk"))).lower()
                start_t = float(ev.get("start_time", ev.get("start", 0.0)))
                ev_dur = float(ev.get("duration", 0.35))
                vol = float(ev.get("volume", 0.25))
                style = str(ev.get("style", "chalk"))
            elif isinstance(ev, (tuple, list)) and len(ev) >= 2:
                start_t = float(ev[0])
                kind = str(ev[1]).lower()
                ev_dur = float(ev[2]) if len(ev) >= 3 else 0.35
                vol = float(ev[3]) if len(ev) >= 4 else 0.25
                style = "chalk"
            else:
                continue

            if ev_dur <= 0.0 or vol <= 0.0 or start_t >= dur:
                continue

            clipped_dur = min(ev_dur, dur - max(0.0, start_t))
            if kind in ("chalk", "sketch", "scribble", "pen"):
                actual_style = "pen" if kind == "pen" else style
                fx_samples = synthesize_chalk_sound(
                    duration=clipped_dur,
                    sample_rate=sample_rate,
                    seed=42 + idx * 17,
                    style=actual_style,
                    volume=vol,
                )
            elif kind in ("eraser", "erase", "wipe"):
                fx_samples = synthesize_eraser_sound(
                    duration=clipped_dur,
                    sample_rate=sample_rate,
                    seed=101 + idx * 23,
                    volume=vol,
                )
            elif kind in ("page_turn", "pageturn", "fold", "turn"):
                fx_samples = synthesize_page_turn_sound(
                    duration=clipped_dur,
                    sample_rate=sample_rate,
                    seed=55 + idx * 19,
                    volume=vol,
                )
            elif kind in ("crumple", "crumble", "paper_crumple"):
                fx_samples = synthesize_crumple_sound(
                    duration=clipped_dur,
                    sample_rate=sample_rate,
                    seed=88 + idx * 29,
                    volume=vol,
                )
            elif kind == "pop":
                fx_samples = synthesize_pop_sound(
                    pitch=1.0 + 0.05 * math.sin(idx),
                    sample_rate=sample_rate,
                    volume=vol,
                )
            elif kind == "whoosh":
                fx_samples = synthesize_whoosh_sound(
                    duration=clipped_dur,
                    sample_rate=sample_rate,
                    volume=vol,
                )
            elif kind == "ding":
                fx_samples = synthesize_ding_sound(
                    sample_rate=sample_rate,
                    volume=vol,
                )
            else:
                continue

            start_sample = max(0, int(round(start_t * sample_rate)))
            end_sample = min(n_total, start_sample + len(fx_samples))
            if end_sample > start_sample:
                sfx_track[start_sample:end_sample] += fx_samples[: end_sample - start_sample]

    if duck_curve is not None:
        sfx_track *= 1.0 - 0.35 * duck_curve

    if stereo:
        # Build a clean stereo mix: centered voice, gentle stereo width on music & SFX
        delay_samples = max(1, int(round(0.00045 * sample_rate)))  # ~0.45ms Haas decorrelation on music
        music_r = np.roll(music_track, delay_samples)
        music_r[:delay_samples] = music_track[:delay_samples]
        left = voice_track + 1.03 * music_track + 0.98 * sfx_track
        right = voice_track + 0.97 * music_r + 1.02 * sfx_track
        combined = np.column_stack([left, right])
    else:
        combined = voice_track + music_track + sfx_track

    combined = normalize_and_limit(
        combined,
        sample_rate=sample_rate,
        target_lufs=target_lufs,
        ceiling_dbfs=ceiling_dbfs,
    )

    if output_path is None:
        fd, tmp_path = tempfile.mkstemp(prefix="handanim_mix_", suffix=".wav")
        os.close(fd)
        output_path = tmp_path

    if stereo:
        return write_wav_stereo(output_path, combined, sample_rate=sample_rate)
    return write_wav_mono(output_path, combined, sample_rate=sample_rate)


def mix_audio_with_video(
    video_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
    duration: float | None = None,
    volume: float = 1.0,
    audio_offset: float = 0.0,
    shortest: bool = True,
    loop_audio: bool = False,
) -> str:
    """Mux an audio track (WAV/MP3) with an existing MP4 video file.

    Uses imageio-ffmpeg's bundled ffmpeg binary for zero external system dependencies.

    Args:
        video_path: Path to source silent or existing video.
        audio_path: Path to source audio track.
        output_path: Destination video path.
        duration: Optional maximum duration in seconds.
        volume: Audio volume multiplier (1.0 = normal).
        audio_offset: Optional audio start delay in seconds.
        shortest: End muxing when the shortest stream ends (default True).
        loop_audio: If True, loop the audio input indefinitely up to the video length.

    Returns:
        The resolved output video path string.
    """
    video_path = Path(video_path).resolve()
    audio_path = Path(audio_path).resolve()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    cmd = [
        ffmpeg_exe,
        "-y",
        "-v",
        "error",
        "-i",
        str(video_path),
    ]
    if loop_audio:
        cmd.extend(["-stream_loop", "-1"])
    cmd.extend([
        "-i",
        str(audio_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
    ])

    if audio_offset > 0:
        delay_ms = int(audio_offset * 1000)
        filter_str = f"adelay={delay_ms}|{delay_ms}"
        if volume != 1.0:
            filter_str += f",volume={volume}"
        cmd.extend(["-filter:a", filter_str])
    elif volume != 1.0:
        cmd.extend(["-filter:a", f"volume={volume}"])

    if duration is not None and duration > 0:
        cmd.extend(["-t", str(duration)])
    elif shortest:
        cmd.append("-shortest")

    cmd.append(str(output_path))

    logger.info("Muxing audio and video: %s", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg audio-video muxing failed (exit code {res.returncode}):\n{res.stderr}")

    return str(output_path)
