"""Audio and video multiplexing using bundled ffmpeg binary."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import imageio_ffmpeg

logger = logging.getLogger(__name__)


def mix_audio_with_video(
    video_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
    duration: float | None = None,
    volume: float = 1.0,
) -> str:
    """Mux an audio track (WAV/MP3) with an existing MP4 video file.

    Uses imageio-ffmpeg's bundled ffmpeg binary for zero external system dependencies.

    Args:
        video_path: Path to source silent or existing video.
        audio_path: Path to source audio track.
        output_path: Destination video path.
        duration: Optional maximum duration in seconds.
        volume: Audio volume multiplier (1.0 = normal).

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
    ]

    if volume != 1.0:
        cmd.extend(["-filter:a", f"volume={volume}"])

    if duration is not None and duration > 0:
        cmd.extend(["-t", str(duration)])
    else:
        cmd.append("-shortest")

    cmd.append(str(output_path))

    logger.info("Muxing audio and video: %s", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg audio-video muxing failed (exit code {res.returncode}):\n{res.stderr}")

    return str(output_path)

