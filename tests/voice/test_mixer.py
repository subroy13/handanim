"""Unit tests for audio and video multiplexing and procedural SFX/music."""

from pathlib import Path

import imageio.v2 as imageio
import numpy as np

from voiceanim import (
    VoiceEngine,
    generate_theme_music,
    loop_audio,
    mix_audio_with_video,
    mix_soundtrack,
    synthesize_chalk_sound,
    synthesize_eraser_sound,
)
from voiceanim.providers import MockVoiceProvider
from voiceanim.sfx import read_audio_mono


def test_mix_audio_with_video(tmp_path):
    # 1. Generate a small test video (10 frames at 10 fps = 1 second)
    video_path = tmp_path / "test_silent.mp4"
    writer = imageio.get_writer(str(video_path), fps=10, codec="libx264", macro_block_size=1)
    for _ in range(10):
        frame = np.full((120, 160, 3), 255, dtype=np.uint8)
        writer.append_data(frame)
    writer.close()
    assert video_path.exists()

    # 2. Generate a test audio WAV
    audio_path = tmp_path / "test_audio.wav"
    provider = MockVoiceProvider()
    provider.synthesize("Testing voiceanim muxer.", output_path=audio_path)
    assert audio_path.exists()

    # 3. Mux them together
    muxed_output = tmp_path / "muxed_video.mp4"
    result_path = mix_audio_with_video(video_path, audio_path, muxed_output)

    assert result_path == str(muxed_output)
    assert muxed_output.exists()
    assert muxed_output.stat().st_size > 0


def test_synthesize_chalk_and_eraser_sounds():
    chalk = synthesize_chalk_sound(duration=0.6, sample_rate=22050, style="chalk")
    eraser = synthesize_eraser_sound(duration=0.6, sample_rate=22050)

    assert len(chalk) == int(0.6 * 22050)
    assert len(eraser) == int(0.6 * 22050)
    # Non-silent and properly bounded in [-1, 1]
    assert 0.01 < float(np.max(np.abs(chalk))) <= 1.0
    assert 0.01 < float(np.max(np.abs(eraser))) <= 1.0


def test_generate_theme_music_and_loop_audio(tmp_path):
    theme_clip = generate_theme_music(duration=2.5, output_path=tmp_path / "theme.wav", style="marimba")
    assert Path(theme_clip.audio_path).is_file()
    samples = read_audio_mono(theme_clip.audio_path, target_sr=22050)
    assert len(samples) == int(round(2.5 * 22050))
    assert float(np.max(np.abs(samples))) > 0.01

    # Loop a short 0.5s audio clip on repeat to 2.0s via loop_audio and VoiceEngine.loop_audio
    short_clip = MockVoiceProvider().synthesize("Short.", output_path=tmp_path / "short.wav")
    looped_clip = loop_audio(short_clip, duration=2.0, output_path=tmp_path / "looped.wav")
    looped_clip_2 = VoiceEngine.loop_audio("calm", duration=1.5, output_path=tmp_path / "calm.wav")
    looped_samples = read_audio_mono(looped_clip.audio_path, target_sr=22050)
    assert len(looped_samples) == int(round(2.0 * 22050))
    assert float(np.max(np.abs(looped_samples))) > 0.01
    assert Path(looped_clip_2.audio_path).is_file()


def test_mix_soundtrack_combines_narration_music_and_sfx(tmp_path):
    provider = MockVoiceProvider()
    narration = provider.synthesize("Hello world", output_path=tmp_path / "narr.wav")
    mixed_wav = mix_soundtrack(
        duration=2.0,
        narration=narration,
        background_music="marimba",
        music_volume=0.2,
        music_loop=True,
        sfx_events=[
            {"type": "chalk", "start_time": 0.1, "duration": 0.5, "volume": 0.4},
            {"type": "eraser", "start_time": 0.8, "duration": 0.5, "volume": 0.5},
        ],
        output_path=tmp_path / "mixed.wav",
    )
    assert Path(mixed_wav).is_file()
    samples = read_audio_mono(mixed_wav, target_sr=22050)
    assert len(samples) == int(round(2.0 * 22050))
    assert float(np.max(np.abs(samples))) > 0.02

