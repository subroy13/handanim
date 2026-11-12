"""Open-source procedural sound effects (chalk sketch, eraser, UI SFX) and looping background music."""

from __future__ import annotations

import math
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

import numpy as np

from .schema import AudioClip

DEFAULT_SR = 44100


def _fft_bandpass(x: np.ndarray, lo_hz: float, hi_hz: float, sr: int = DEFAULT_SR) -> np.ndarray:
    """Zero-dependency smooth frequency-domain bandpass filter."""
    n = len(x)
    if n == 0:
        return x
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    spec = np.fft.rfft(x)

    # Smooth raised-cosine roll-off around lo_hz and hi_hz
    lo_bw = max(20.0, lo_hz * 0.15)
    hi_bw = max(40.0, hi_hz * 0.15)

    low_gain = np.clip((freqs - (lo_hz - lo_bw)) / (2.0 * lo_bw), 0.0, 1.0)
    low_gain = 0.5 - 0.5 * np.cos(np.pi * low_gain)

    high_gain = 1.0 - np.clip((freqs - (hi_hz - hi_bw)) / (2.0 * hi_bw), 0.0, 1.0)
    high_gain = 0.5 - 0.5 * np.cos(np.pi * high_gain)

    mask = low_gain * high_gain
    return np.fft.irfft(spec * mask, n=n)


def _bandpass(x: np.ndarray, lo_hz: float, hi_hz: float, sr: int = DEFAULT_SR) -> np.ndarray:
    """Bandpass filter using scipy if available, falling back to smooth FFT bandpass."""
    if len(x) < 16:
        return x
    try:
        from scipy.signal import butter, sosfilt

        nyq = sr / 2.0
        lo = max(10.0, min(lo_hz, nyq * 0.95)) / nyq
        hi = max(lo + 0.01, min(hi_hz, nyq * 0.98)) / nyq
        sos = butter(2, [lo, hi], btype="band", output="sos")
        return np.asarray(sosfilt(sos, x), dtype=np.float64)
    except Exception:
        return _fft_bandpass(x, lo_hz, hi_hz, sr)


def _highpass(x: np.ndarray, cutoff_hz: float, sr: int = DEFAULT_SR) -> np.ndarray:
    return _bandpass(x, cutoff_hz, sr * 0.48, sr)


def _lowpass(x: np.ndarray, cutoff_hz: float, sr: int = DEFAULT_SR) -> np.ndarray:
    return _bandpass(x, 15.0, cutoff_hz, sr)


def write_wav_mono(path: str | Path, samples: np.ndarray, sample_rate: int = DEFAULT_SR) -> str:
    """Write a 1D float64 numpy array in [-1, 1] to a 16-bit PCM mono WAV file."""
    out_path = Path(path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(samples, -0.99, 0.99)
    pcm16 = (clipped * 32767.0).astype(np.int16)
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())
    return str(out_path)


def read_audio_mono(path: str | Path, target_sr: int = DEFAULT_SR) -> np.ndarray:
    """Read any audio file (.wav, .mp3, .ogg, .m4a) into a 1D float64 array at `target_sr`."""
    audio_path = Path(path).expanduser().resolve()
    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Fast path for standard WAV via wave or soundfile
    samples: np.ndarray | None = None
    sr: int = target_sr

    if audio_path.suffix.lower() == ".wav":
        try:
            with wave.open(str(audio_path), "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                sr = wf.getframerate()
                n_frames = wf.getnframes()
                raw = wf.readframes(n_frames)
            if sampwidth == 2:
                arr = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
                if n_channels > 1:
                    arr = arr.reshape(-1, n_channels).mean(axis=1)
                samples = arr
        except Exception:
            samples = None

    if samples is None:
        try:
            import soundfile as sf

            data, sr = sf.read(str(audio_path), dtype="float64")
            samples = data.mean(axis=1) if data.ndim > 1 else data
        except Exception:
            samples = None

    # Fallback via bundled ffmpeg for MP3/M4A/OGG/float WAV
    if samples is None:
        import imageio_ffmpeg

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_wav = Path(tmp.name)
        try:
            cmd = [
                ffmpeg_exe,
                "-y",
                "-v",
                "error",
                "-i",
                str(audio_path),
                "-ac",
                "1",
                "-ar",
                str(target_sr),
                "-f",
                "wav",
                str(tmp_wav),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"Failed to decode audio {audio_path}: {res.stderr}")
            with wave.open(str(tmp_wav), "rb") as wf:
                sr = wf.getframerate()
                raw = wf.readframes(wf.getnframes())
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
        finally:
            if tmp_wav.exists():
                tmp_wav.unlink()

    if sr != target_sr and len(samples) > 0:
        new_len = max(1, int(round(len(samples) * target_sr / sr)))
        old_idx = np.linspace(0.0, 1.0, len(samples))
        new_idx = np.linspace(0.0, 1.0, new_len)
        samples = np.interp(new_idx, old_idx, samples)

    return samples


def synthesize_chalk_sound(
    duration: float,
    sample_rate: int = DEFAULT_SR,
    seed: int = 42,
    style: str = "chalk",
    volume: float = 0.45,
) -> np.ndarray:
    """Synthesize an open-source chalk or sketch-pen drawing sound over `duration` seconds.

    Combines:
    - Initial chalk-to-board contact tap transient
    - High-frequency chalky grain (1800-7200 Hz) + warm board resonance (800-1750 Hz)
    - Hand-stroke velocity modulation (8-14 Hz) with natural micro-lifts between sub-strokes
    """
    dur = max(0.05, float(duration))
    n = int(round(dur * sample_rate))
    if n <= 0:
        return np.zeros(0, dtype=np.float64)

    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=np.float64) / sample_rate

    noise = rng.standard_normal(n)
    if style == "pen":
        grit = _bandpass(noise, 2100.0, 7800.0, sample_rate) * 0.75
        body = _bandpass(noise, 950.0, 2100.0, sample_rate) * 0.25
    else:
        # Chalk on slate/whiteboard: gritty high band + warm resonant mid band + occasional squeak harmonic
        grit = _bandpass(noise, 1750.0, 6800.0, sample_rate) * 0.65
        body = _bandpass(noise, 720.0, 1700.0, sample_rate) * 0.35

    texture = grit + body

    # Hand-stroke cadence modulation (simulates repeated hand strokes and micro-lifts)
    stroke_rate = rng.uniform(8.5, 13.5)
    sub_rate = rng.uniform(2.5, 4.2)
    phase1 = rng.uniform(0.0, 2.0 * math.pi)
    phase2 = rng.uniform(0.0, 2.0 * math.pi)

    flutter = 0.52 + 0.48 * np.abs(np.sin(2.0 * math.pi * stroke_rate * t + phase1))
    # Brief micro-lifts where the hand turns or lifts between segments
    lift_wave = np.sin(2.0 * math.pi * sub_rate * t + phase2)
    micro_lift = np.where(lift_wave < -0.78, 0.18, 1.0)
    # Smooth the micro-lift transitions over 12ms
    smooth_win = max(1, int(0.012 * sample_rate))
    if smooth_win > 1 and len(micro_lift) > smooth_win:
        kernel = np.ones(smooth_win) / smooth_win
        micro_lift = np.convolve(micro_lift, kernel, mode="same")

    # Initial chalk contact tap (first 8ms)
    tap_len = min(n, int(0.008 * sample_rate))
    tap = np.zeros(n, dtype=np.float64)
    if tap_len > 0:
        tap_t = np.arange(tap_len) / sample_rate
        tap_burst = _bandpass(rng.standard_normal(tap_len), 1200.0, 5200.0, sample_rate)
        tap[:tap_len] = tap_burst * np.exp(-tap_t / 0.002) * 0.55

    # Overall attack & release envelope
    attack = np.minimum(1.0, t / 0.018)
    release = np.minimum(1.0, np.maximum(0.0, (dur - t) / 0.04))
    env = attack * release

    signal = (texture * flutter * micro_lift * env + tap) * 0.36 * float(volume)
    return np.asarray(np.clip(signal, -0.95, 0.95), dtype=np.float64)


def synthesize_eraser_sound(
    duration: float,
    sample_rate: int = DEFAULT_SR,
    seed: int = 101,
    volume: float = 0.55,
) -> np.ndarray:
    """Synthesize an open-source felt/rubber eraser wiping sound over `duration` seconds.

    Models a rhythmic back-and-forth zigzag wiping motion across the board:
    - Soft low-mid felt friction (280-1900 Hz) + warm board rub (160-520 Hz)
    - Alternating forward/backward swipe envelope (4.5-6.5 swipes/sec)
    """
    dur = max(0.06, float(duration))
    n = int(round(dur * sample_rate))
    if n <= 0:
        return np.zeros(0, dtype=np.float64)

    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=np.float64) / sample_rate

    noise = rng.standard_normal(n)
    # Forward swipe has slightly brighter friction; return swipe is warmer
    bright_rub = _bandpass(noise, 450.0, 2200.0, sample_rate)
    warm_rub = _bandpass(noise, 200.0, 950.0, sample_rate)

    swipe_hz = rng.uniform(2.4, 3.3)  # 1 full cycle = 2 swipes (back and forth ~5-6.5 swipes/sec)
    swipe_phase = 2.0 * math.pi * swipe_hz * t
    # Blend between bright forward stroke and warm back stroke
    forward_weight = 0.5 + 0.5 * np.sin(swipe_phase)
    rub = forward_weight * bright_rub * 0.65 + (1.0 - forward_weight) * warm_rub * 0.85

    # Velocity peaks in the middle of each swipe and dips briefly at the turnaround points
    swipe_speed = 0.25 + 0.75 * (np.sin(swipe_phase) ** 2)

    attack = np.minimum(1.0, t / 0.025)
    release = np.minimum(1.0, np.maximum(0.0, (dur - t) / 0.05))
    env = attack * release

    signal = rub * swipe_speed * env * 0.42 * float(volume)
    return np.asarray(np.clip(signal, -0.95, 0.95), dtype=np.float64)


def synthesize_pop_sound(pitch: float = 1.0, sample_rate: int = DEFAULT_SR, volume: float = 0.5) -> np.ndarray:
    """Synthesize a crisp cartoon pop sound effect."""
    dur = 0.11
    n = int(round(dur * sample_rate))
    t = np.arange(n, dtype=np.float64) / sample_rate
    freq = (920.0 * np.exp(-t * 19.0) + 410.0) * float(pitch)
    phase = 2.0 * np.pi * np.cumsum(freq) / sample_rate
    env = np.minimum(1.0, t / 0.002) * np.exp(-np.maximum(t - 0.002, 0.0) / 0.04)
    return np.asarray(np.sin(phase) * env * float(volume), dtype=np.float64)


def synthesize_whoosh_sound(duration: float = 0.38, sample_rate: int = DEFAULT_SR, volume: float = 0.45) -> np.ndarray:
    """Synthesize a smooth transition whoosh sound effect."""
    dur = max(0.1, float(duration))
    n = int(round(dur * sample_rate))
    rng = np.random.default_rng(77)
    noise = rng.standard_normal(n)
    t_norm = np.linspace(0.0, 1.0, n)
    low_band = _bandpass(noise, 250.0, 950.0, sample_rate)
    high_band = _bandpass(noise, 800.0, 2800.0, sample_rate)
    sweep = np.sin(np.pi * t_norm) ** 1.6
    combined = (1.0 - sweep) * low_band + sweep * high_band
    env = np.sin(np.pi * t_norm) ** 2
    return np.asarray(combined * env * 0.4 * float(volume), dtype=np.float64)


def synthesize_ding_sound(sample_rate: int = DEFAULT_SR, volume: float = 0.45) -> np.ndarray:
    """Synthesize a pleasant two-note bell ding sound effect."""
    dur = 0.95
    n = int(round(dur * sample_rate))
    t = np.arange(n, dtype=np.float64) / sample_rate

    def _tone(f: float, t_arr: np.ndarray) -> np.ndarray:
        y = np.zeros_like(t_arr)
        for ratio, amp, dec in ((1.0, 1.0, 0.48), (2.76, 0.32, 0.22), (5.4, 0.15, 0.11)):
            y += amp * np.sin(2.0 * np.pi * f * ratio * t_arr) * np.exp(-t_arr / dec)
        return np.asarray(y * np.minimum(1.0, t_arr / 0.003), dtype=np.float64)

    note1 = _tone(1046.5, t)
    offset = int(0.08 * sample_rate)
    out = note1.copy()
    if offset < n:
        out[offset:] += _tone(1568.0, t[: n - offset]) * 0.9
    return np.asarray(np.clip(out * 0.28 * float(volume), -0.95, 0.95), dtype=np.float64)


def synthesize_page_turn_sound(
    duration: float = 0.9,
    sample_rate: int = DEFAULT_SR,
    seed: int = 55,
    volume: float = 0.5,
) -> np.ndarray:
    """Synthesize an open-source paper page-turn / sheet-folding sound over `duration` seconds.

    Combines:
    - Subtle initial corner-lift paper flick
    - Smoothly swept paper-on-paper sliding friction (900-5800 Hz)
    - Gentle settling crease pat near the end of the turn
    """
    dur = max(0.12, float(duration))
    n = int(round(dur * sample_rate))
    if n <= 0:
        return np.zeros(0, dtype=np.float64)

    rng = np.random.default_rng(seed)
    t_norm = np.linspace(0.0, 1.0, n)

    noise = rng.standard_normal(n)
    warm_slide = _bandpass(noise, 750.0, 2400.0, sample_rate)
    crisp_rustle = _bandpass(noise, 2200.0, 6200.0, sample_rate)

    # Sweep from warm lift -> crisp mid-turn fold -> warm settle
    arch = np.sin(np.pi * t_norm) ** 1.4
    slide = (1.0 - 0.65 * arch) * warm_slide * 0.6 + (0.35 + 0.65 * arch) * crisp_rustle * 0.75
    slide_env = np.sin(np.pi * t_norm) ** 1.25

    # Initial corner-lift flick at t ~ 0.03 * dur
    flick = np.zeros(n, dtype=np.float64)
    flick_len = min(n, int(0.035 * sample_rate))
    if flick_len > 0:
        ft = np.arange(flick_len, dtype=np.float64) / sample_rate
        flick_noise = _bandpass(rng.standard_normal(flick_len), 1800.0, 6800.0, sample_rate)
        flick[:flick_len] = flick_noise * np.exp(-ft / 0.008) * 0.55

    # Soft crease settle pat at ~85% of duration
    settle = np.zeros(n, dtype=np.float64)
    settle_start = int(0.82 * n)
    settle_len = min(n - settle_start, int(0.06 * sample_rate))
    if settle_len > 0:
        st = np.arange(settle_len, dtype=np.float64) / sample_rate
        settle_noise = _bandpass(rng.standard_normal(settle_len), 500.0, 2600.0, sample_rate)
        settle[settle_start : settle_start + settle_len] = settle_noise * np.exp(-st / 0.015) * 0.45

    signal = (slide * slide_env * 0.38 + flick + settle) * float(volume)
    return np.asarray(np.clip(signal, -0.95, 0.95), dtype=np.float64)


def synthesize_crumple_sound(
    duration: float = 1.0,
    sample_rate: int = DEFAULT_SR,
    seed: int = 88,
    volume: float = 0.55,
) -> np.ndarray:
    """Synthesize an open-source paper crumpling and toss sound over `duration` seconds.

    Combines:
    - A dense cascade of dry, crisp paper-crinkle micro-bursts (1.4-8.5 kHz) + stiff paper snaps (0..70% of duration)
    - A light aerodynamic toss whoosh (55..100% of duration) as the crumpled ball flies off to the side
    """
    dur = max(0.15, float(duration))
    n = int(round(dur * sample_rate))
    if n <= 0:
        return np.zeros(0, dtype=np.float64)

    rng = np.random.default_rng(seed)
    out = np.zeros(n, dtype=np.float64)

    # 1. Cascade of crisp paper-crinkle bursts during the crunch phase (0 .. 0.72 * dur)
    crunch_end = 0.74 * dur
    n_bursts = max(14, int(round(26 * min(1.5, dur))))
    for k in range(n_bursts):
        # Cluster bursts slightly more densely in the middle of the squeeze
        u = (k + rng.uniform(0.1, 0.9)) / n_bursts
        burst_t = crunch_end * (0.04 + 0.92 * (u**0.9))
        burst_dur = float(rng.uniform(0.010, 0.036))
        b_len = min(int(round(burst_dur * sample_rate)), n - int(round(burst_t * sample_rate)))
        if b_len <= 8:
            continue

        b_start = max(0, int(round(burst_t * sample_rate)))
        raw_b = rng.standard_normal(b_len)
        lo_f = float(rng.uniform(1200.0, 2600.0))
        hi_f = float(rng.uniform(5200.0, 8800.0))
        crinkle = _bandpass(raw_b, lo_f, hi_f, sample_rate) * 0.75
        snap = _bandpass(raw_b, 550.0, 1600.0, sample_rate) * 0.35

        bt = np.arange(b_len, dtype=np.float64) / sample_rate
        tau = burst_dur * float(rng.uniform(0.22, 0.38))
        env = np.minimum(1.0, bt / 0.0015) * np.exp(-bt / max(0.002, tau))
        amp = float(rng.uniform(0.45, 1.0)) * math.sin(math.pi * min(1.0, u * 1.15)) ** 0.5
        out[b_start : b_start + b_len] += (crinkle + snap) * env * amp * 0.52

    # 2. Continuous subtle paper friction bed underneath the crinkles
    crunch_n = min(n, int(round(crunch_end * sample_rate)))
    if crunch_n > 16:
        bed_noise = _bandpass(rng.standard_normal(crunch_n), 1100.0, 5400.0, sample_rate)
        bed_env = np.sin(np.pi * np.linspace(0.0, 1.0, crunch_n)) ** 1.3
        out[:crunch_n] += bed_noise * bed_env * 0.14

    # 3. Toss whoosh in the second half (0.50 .. 0.98 * dur)
    whoosh_start = int(round(0.48 * n))
    whoosh_len = n - whoosh_start
    if whoosh_len > 32:
        w_sound = synthesize_whoosh_sound(
            duration=whoosh_len / sample_rate,
            sample_rate=sample_rate,
            volume=0.55,
        )
        copy_len = min(whoosh_len, len(w_sound))
        out[whoosh_start : whoosh_start + copy_len] += w_sound[:copy_len]

    signal = out * float(volume)
    peak = float(np.max(np.abs(signal))) if len(signal) > 0 else 0.0
    if peak > 0.92:
        signal = np.tanh(signal / peak * 1.2) * 0.90
    return np.asarray(np.clip(signal, -0.95, 0.95), dtype=np.float64)


# ---------------------------------------------------------------------------
# Background Theme Music Synthesis & Seamless Looping
# ---------------------------------------------------------------------------


def _marimba_note(freq: float, duration: float = 0.48, sample_rate: int = DEFAULT_SR) -> np.ndarray:
    n = int(round(duration * sample_rate))
    t = np.arange(n, dtype=np.float64) / sample_rate
    y = np.sin(2.0 * np.pi * freq * t) * np.exp(-t / 0.26)
    y += 0.32 * np.sin(2.0 * np.pi * freq * 3.98 * t) * np.exp(-t / 0.048)
    y += 0.10 * np.sin(2.0 * np.pi * freq * 9.15 * t) * np.exp(-t / 0.018)
    return y * np.minimum(1.0, t / 0.003)


def _warm_pad_note(freq: float, duration: float = 1.8, sample_rate: int = DEFAULT_SR) -> np.ndarray:
    n = int(round(duration * sample_rate))
    t = np.arange(n, dtype=np.float64) / sample_rate
    y = 0.65 * np.sin(2.0 * np.pi * freq * t)
    y += 0.25 * np.sin(2.0 * np.pi * freq * 2.0 * t)
    y += 0.10 * np.sin(2.0 * np.pi * freq * 3.0 * t)
    attack = np.minimum(1.0, t / 0.08)
    decay = np.exp(-t / max(0.4, duration * 0.75))
    return y * attack * decay


def _bass_note(freq: float, duration: float = 0.5, sample_rate: int = DEFAULT_SR) -> np.ndarray:
    n = int(round(duration * sample_rate))
    t = np.arange(n, dtype=np.float64) / sample_rate
    y = np.sin(2.0 * np.pi * freq * t) + 0.22 * np.sin(4.0 * np.pi * freq * t)
    return y * np.minimum(1.0, t / 0.01) * np.exp(-t / 0.34)


def _shaker_hit(sample_rate: int = DEFAULT_SR, rng: np.random.Generator | None = None) -> np.ndarray:
    if rng is None:
        rng = np.random.default_rng(19)
    n = int(round(0.055 * sample_rate))
    t = np.arange(n, dtype=np.float64) / sample_rate
    noise = _highpass(rng.standard_normal(n), 5500.0, sample_rate)
    return noise * np.exp(-t / 0.016) * 0.28


def synthesize_theme_loop(
    bars: int = 4,
    bpm: float = 104.0,
    style: str = "marimba",
    sample_rate: int = DEFAULT_SR,
) -> np.ndarray:
    """Synthesize a seamless multi-bar open-source background theme loop.

    Supported styles:
    - ``"marimba"`` / ``"theme"``: Warm marimba arpeggio + soft bass + light shaker (default)
    - ``"calm"``: Gentle acoustic/electric-piano warm chord progression without percussion
    - ``"upbeat"``: Brighter tempo-locked marimba + pulse
    """
    beat_sec = 60.0 / max(40.0, float(bpm))
    bar_sec = 4.0 * beat_sec
    total_sec = bars * bar_sec
    tail_sec = 0.6  # allow reverb/decay tail to wrap around seamlessly for looping
    n_loop = int(round(total_sec * sample_rate))
    n_buf = n_loop + int(round(tail_sec * sample_rate))
    buf = np.zeros(n_buf, dtype=np.float64)
    rng = np.random.default_rng(23)

    def _midi_to_hz(m: int) -> float:
        return float(440.0 * (2.0 ** ((m - 69.0) / 12.0)))

    # Classic warm I - V - vi - IV progression in C major
    progression = [
        (60, [60, 64, 67, 72]),
        (55, [55, 59, 62, 67]),
        (57, [57, 60, 64, 69]),
        (53, [53, 57, 60, 65]),
    ]
    arp_pattern = [0, 2, 1, 3, 2, 1, 3, 2]

    for b in range(bars):
        root_midi, chord_midis = progression[b % len(progression)]
        bar_start = b * bar_sec

        if style == "calm":
            # Gentle arpeggiated warm pad chords
            for step_idx, note_idx in enumerate([0, 1, 2, 3]):
                t0 = bar_start + step_idx * beat_sec
                idx = int(round(t0 * sample_rate))
                note = _warm_pad_note(_midi_to_hz(chord_midis[note_idx]), duration=beat_sec * 1.8, sample_rate=sample_rate) * 0.26
                end_idx = min(n_buf, idx + len(note))
                buf[idx:end_idx] += note[: end_idx - idx]
            bass = _bass_note(_midi_to_hz(root_midi - 12), duration=bar_sec * 0.9, sample_rate=sample_rate) * 0.25
            b_idx = int(round(bar_start * sample_rate))
            b_end = min(n_buf, b_idx + len(bass))
            buf[b_idx:b_end] += bass[: b_end - b_idx]
        else:
            pitch_shift = 12 if style != "upbeat" else 12
            # 8th-note marimba arpeggio
            for e in range(8):
                t0 = bar_start + e * (beat_sec / 2.0)
                idx = int(round(t0 * sample_rate))
                vel = 0.34 if (e % 2 == 0) else 0.24
                note = _marimba_note(_midi_to_hz(chord_midis[arp_pattern[e]] + pitch_shift), 0.45, sample_rate) * vel
                end_idx = min(n_buf, idx + len(note))
                buf[idx:end_idx] += note[: end_idx - idx]

            # Quarter-note warm bass
            for q in range(4):
                t0 = bar_start + q * beat_sec
                idx = int(round(t0 * sample_rate))
                vel = 0.30 if (q % 2 == 0) else 0.20
                bass = _bass_note(_midi_to_hz(root_midi - 24), beat_sec * 0.95, sample_rate) * vel
                end_idx = min(n_buf, idx + len(bass))
                buf[idx:end_idx] += bass[: end_idx - idx]

            # 16th-note soft shaker
            for s in range(16):
                t0 = bar_start + s * (beat_sec / 4.0)
                idx = int(round(t0 * sample_rate))
                vel = 0.22 if (s % 4 == 2) else (0.12 if (s % 2 == 0) else 0.06)
                shk = _shaker_hit(sample_rate, rng) * vel
                end_idx = min(n_buf, idx + len(shk))
                buf[idx:end_idx] += shk[: end_idx - idx]

    # Fold the reverb/decay tail past n_loop back into the start of the loop for click-free seamless repeat
    tail = buf[n_loop:]
    loop_out = buf[:n_loop].copy()
    wrap_len = min(len(tail), len(loop_out))
    if wrap_len > 0:
        loop_out[:wrap_len] += tail[:wrap_len]

    peak = float(np.max(np.abs(loop_out))) if len(loop_out) > 0 else 1.0
    if peak > 0.95:
        loop_out *= 0.95 / peak
    return loop_out


def loop_audio_array(
    audio: np.ndarray,
    duration: float,
    sample_rate: int = DEFAULT_SR,
    crossfade: float = 0.04,
    fade_in: float = 0.25,
    fade_out: float = 0.6,
    volume: float = 1.0,
) -> np.ndarray:
    """Repeat a 1D audio array seamlessly to fill `duration` seconds."""
    target_n = max(1, int(round(float(duration) * sample_rate)))
    if len(audio) == 0:
        return np.zeros(target_n, dtype=np.float64)

    src = np.asarray(audio, dtype=np.float64).ravel()
    cf_samples = min(int(round(crossfade * sample_rate)), len(src) // 4)

    if len(src) >= target_n:
        out = src[:target_n].copy()
    elif cf_samples <= 1:
        reps = int(math.ceil(target_n / len(src)))
        out = np.tile(src, reps)[:target_n].copy()
    else:
        out = np.zeros(target_n, dtype=np.float64)
        step = len(src) - cf_samples
        pos = 0
        first = True
        fade_up = np.linspace(0.0, 1.0, cf_samples)
        fade_dn = 1.0 - fade_up
        while pos < target_n:
            chunk = src.copy()
            if not first:
                chunk[:cf_samples] *= fade_up
            write_end = min(target_n, pos + len(chunk))
            seg_len = write_end - pos
            if not first and seg_len > 0:
                ov_len = min(cf_samples, seg_len)
                out[pos : pos + ov_len] *= fade_dn[:ov_len]
            out[pos:write_end] += chunk[:seg_len]
            pos += step
            first = False

    fi_samples = min(target_n // 2, int(round(fade_in * sample_rate)))
    if fi_samples > 1:
        out[:fi_samples] *= np.linspace(0.0, 1.0, fi_samples)

    fo_samples = min(target_n // 2, int(round(fade_out * sample_rate)))
    if fo_samples > 1:
        out[target_n - fo_samples :] *= np.linspace(1.0, 0.0, fo_samples)

    return np.asarray(np.clip(out * float(volume), -0.99, 0.99), dtype=np.float64)


THEME_PRESETS = {"marimba", "theme", "calm", "upbeat"}


def generate_theme_music(
    duration: float,
    output_path: str | Path | None = None,
    style: str = "marimba",
    bpm: float = 104.0,
    volume: float = 0.22,
    fade_in: float = 0.3,
    fade_out: float = 0.8,
    sample_rate: int = DEFAULT_SR,
) -> AudioClip:
    """Generate a repeating open-source background theme music track for `duration` seconds.

    Args:
        duration: Total duration in seconds.
        output_path: Optional destination `.wav` path. Uses a temporary file if omitted.
        style: Theme preset (`"marimba"`, `"theme"`, `"calm"`, or `"upbeat"`).
        bpm: Tempo in beats per minute.
        volume: Output amplitude scaling (default `0.22` for background music).
        fade_in: Fade-in duration in seconds.
        fade_out: Fade-out duration in seconds.
        sample_rate: Sample rate in Hz.

    Returns:
        An `AudioClip` pointing to the generated WAV file.
    """
    base_loop = synthesize_theme_loop(bars=4, bpm=bpm, style=style, sample_rate=sample_rate)
    looped = loop_audio_array(
        base_loop,
        duration=duration,
        sample_rate=sample_rate,
        crossfade=0.0,
        fade_in=fade_in,
        fade_out=fade_out,
        volume=volume,
    )
    if output_path is None:
        fd, tmp_name = tempfile.mkstemp(prefix="handanim_theme_", suffix=".wav")
        import os

        os.close(fd)
        output_path = tmp_name

    wav_path = write_wav_mono(output_path, looped, sample_rate=sample_rate)
    return AudioClip(
        audio_path=wav_path,
        duration=float(duration),
        words=[],
        sentences=[],
        text=f"[theme:{style}]",
        provider="voiceanim.sfx",
        voice=style,
    )


def loop_audio(
    audio_source: str | Path | AudioClip | Any,
    duration: float,
    output_path: str | Path | None = None,
    volume: float = 0.22,
    fade_in: float = 0.3,
    fade_out: float = 0.8,
    sample_rate: int = DEFAULT_SR,
) -> AudioClip:
    """Repeat an audio file, `AudioClip`, or built-in theme preset to fill `duration` seconds.

    Args:
        audio_source: Path to a WAV/MP3 audio file, an `AudioClip`, or a preset name
            (`"marimba"`, `"theme"`, `"calm"`, `"upbeat"`).
        duration: Target total duration in seconds.
        output_path: Optional destination `.wav` file path.
        volume: Volume multiplier applied to the looped audio.
        fade_in: Fade-in duration at the start (seconds).
        fade_out: Fade-out duration at the end (seconds).
        sample_rate: Audio sample rate in Hz.

    Returns:
        An `AudioClip` pointing to the looped WAV file.
    """
    if isinstance(audio_source, str) and audio_source.lower() in THEME_PRESETS:
        return generate_theme_music(
            duration=duration,
            output_path=output_path,
            style=audio_source.lower(),
            volume=volume,
            fade_in=fade_in,
            fade_out=fade_out,
            sample_rate=sample_rate,
        )

    src_path: str | Path
    if hasattr(audio_source, "audio_path"):
        src_path = audio_source.audio_path
    elif isinstance(audio_source, (str, Path)):
        src_path = audio_source
    else:
        raise TypeError(f"Unsupported audio_source for loop_audio: {audio_source!r}")

    samples = read_audio_mono(src_path, target_sr=sample_rate)
    looped = loop_audio_array(
        samples,
        duration=duration,
        sample_rate=sample_rate,
        crossfade=0.04,
        fade_in=fade_in,
        fade_out=fade_out,
        volume=volume,
    )
    if output_path is None:
        fd, tmp_name = tempfile.mkstemp(prefix="handanim_loop_", suffix=".wav")
        import os

        os.close(fd)
        output_path = tmp_name

    wav_path = write_wav_mono(output_path, looped, sample_rate=sample_rate)
    return AudioClip(
        audio_path=wav_path,
        duration=float(duration),
        words=[],
        sentences=[],
        text=f"[loop:{Path(src_path).name}]",
        provider="voiceanim.sfx",
        voice="loop",
    )
