"""Unit tests for audio and video multiplexing."""

import imageio.v2 as imageio
import numpy as np

from voiceanim.mixer import mix_audio_with_video
from voiceanim.providers import MockVoiceProvider


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
