"""Generate a local draft voice, align it to the scene, and mux the final MP4.

Run after scene.py from the repository root:
    .venv/bin/python sandbox/ptolemy/narration.py

Uses macOS 'say' only to create missing voice clips. Saved WAVs can be reused
on other platforms; imageio-ffmpeg supplies the video/audio encoder.
"""

import shutil
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np

OUTPUT = Path("sandbox/ptolemy/output")
VOICE = "Samantha"
WORDS_PER_MINUTE = 185
SAMPLE_RATE = 24000
DURATION = 58

# Start, latest end, original narration. Keep these aligned with scene.py.
NARRATION = [
    (0.6, 4.3, "Ptolemy's theorem. A beautiful visual proof."),
    (4.5, 8.1, "Four points, in order, on a circle."),
    (8.2, 11.5, "Diagonals and sides obey this identity."),
    (11.7, 19.4, "Choose K on A C, so these two angles at B are equal."),
    (19.7, 26.8, "Angles on the same chord are equal. So triangles A B K and D B C are similar."),
    (27.1, 31.8, "Matching sides give the first product identity."),
    (32.2, 39.8, "The remaining angles at B match too. The circle gives a second similar pair."),
    (40.1, 45.3, "Matching sides now give the second product identity."),
    (45.7, 49.8, "Add the two identities."),
    (50.1, 57.5, "A K plus K C is A C. And that is Ptolemy's theorem."),
]


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    audio = np.zeros(DURATION * SAMPLE_RATE, dtype=np.int16)
    for i, (start, end, words) in enumerate(NARRATION):
        clip = OUTPUT / f"voice_{i:02d}.wav"
        transcript = clip.with_suffix(".txt")
        voice_settings = f"{VOICE}\n{WORDS_PER_MINUTE}\n{words}\n"
        if not clip.exists() or not transcript.exists() or transcript.read_text() != voice_settings:
            if shutil.which("say") is None:
                raise RuntimeError("Generate the draft voice on macOS or supply the saved voice WAV clips.")
            subprocess.run(
                [
                    "say",
                    "-v",
                    VOICE,
                    "-r",
                    str(WORDS_PER_MINUTE),
                    "--data-format=LEI16@24000",
                    "-o",
                    str(clip),
                    words,
                ],
                check=True,
            )
            transcript.write_text(voice_settings)
        with wave.open(str(clip), "rb") as reader:
            assert (reader.getnchannels(), reader.getsampwidth(), reader.getframerate()) == (1, 2, SAMPLE_RATE)
            samples = np.frombuffer(reader.readframes(reader.getnframes()), dtype="<i2")
        length = len(samples) / SAMPLE_RATE
        if length == 0 or length > end - start:
            raise ValueError(f"Voice {i}: {length:.2f}s for a {end - start:.2f}s slot. Revise the narration.")
        offset = round(start * SAMPLE_RATE)
        audio[offset : offset + len(samples)] = samples
        print(f"Voice {i}: {start:.1f}–{start + length:.2f}s / latest end {end:.1f}s", flush=True)

    narration = OUTPUT / "narration.wav"
    with wave.open(str(narration), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(SAMPLE_RATE)
        writer.writeframes(audio.tobytes())

    subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-y",
            "-v",
            "warning",
            "-i",
            str(OUTPUT / "silent.mp4"),
            "-i",
            str(narration),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-t",
            str(DURATION),
            "-movflags",
            "+faststart",
            str(OUTPUT / "ptolemy.mp4"),
        ],
        check=True,
    )
    print(f"Saved {OUTPUT / 'ptolemy.mp4'}")
