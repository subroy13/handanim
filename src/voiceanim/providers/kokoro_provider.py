"""Kokoro-82M local offline TTS provider.

High-fidelity, 82M-parameter lightweight open-weight TTS model running on macOS
via ONNX runtime or PyTorch.
"""

from __future__ import annotations

import logging
import os
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np

from ..cache import AudioCache
from ..schema import AudioClip
from .base import BaseVoiceProvider

logger = logging.getLogger(__name__)

KOKORO_MODEL_URL = "https://huggingface.co/fastrtc/kokoro-onnx/resolve/main/kokoro-v1.0.onnx"
KOKORO_VOICES_URL = "https://huggingface.co/fastrtc/kokoro-onnx/resolve/main/voices-v1.0.bin"


class KokoroProvider(BaseVoiceProvider):
    """Local, offline text-to-speech provider using the Kokoro-82M model."""

    name = "kokoro"
    default_voice = "af_heart"
    supported_voices = [
        "af_heart",  # Warm American female (flagship voice)
        "af_bella",  # Bright American female
        "af_nicole",  # Soft American female
        "af_sky",  # Animated American female
        "am_adam",  # Conversational American male
        "am_michael",  # Clear American male
        "bf_emma",  # British female
        "bf_isabella",  # Expressive British female
        "bm_george",  # British male narrator
        "bm_lewis",  # British male deep
    ]

    def __init__(
        self,
        model_dir: str | Path | None = None,
        cache: AudioCache | None = None,
        fallback_to_mock: bool = False,
    ):
        self.model_dir = Path(model_dir or os.path.expanduser("~/.cache/voiceanim/kokoro"))
        self.cache = cache or AudioCache()
        self.fallback_to_mock = fallback_to_mock
        self._kokoro_instance = None
        self._onnx_available = None

    def _ensure_model_files(self) -> tuple[Path, Path]:
        """Verify model weights exist locally or download from Hugging Face."""
        self.model_dir.mkdir(parents=True, exist_ok=True)
        model_path = self.model_dir / "kokoro-v1.0.onnx"
        voices_path = self.model_dir / "voices-v1.0.bin"

        if not model_path.exists():
            logger.info("Downloading Kokoro-82M ONNX model from Hugging Face...")
            urllib.request.urlretrieve(KOKORO_MODEL_URL, str(model_path))

        if not voices_path.exists():
            logger.info("Downloading Kokoro voice profiles from Hugging Face...")
            urllib.request.urlretrieve(KOKORO_VOICES_URL, str(voices_path))

        return model_path, voices_path

    def _get_engine(self):
        """Lazy loader for Kokoro ONNX engine."""
        if self._kokoro_instance is not None:
            return self._kokoro_instance

        try:
            from kokoro_onnx import Kokoro

            model_path, voices_path = self._ensure_model_files()
            self._kokoro_instance = Kokoro(str(model_path), str(voices_path))
            self._onnx_available = True
            return self._kokoro_instance
        except ImportError as err:
            self._onnx_available = False
            if self.fallback_to_mock:
                return None
            raise ImportError(
                "Kokoro TTS requires 'kokoro-onnx' and 'soundfile'. "
                "Install them with:\n"
                "    poetry run pip install kokoro-onnx soundfile\n"
                "Or use the AWS Polly provider ('--provider polly') or Mock provider."
            ) from err
        except Exception as e:
            if self.fallback_to_mock:
                return None
            raise RuntimeError(f"Failed to initialize Kokoro model: {e}") from e

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float = 1.0,
        instruct: str | None = None,
        output_path: str | Path | None = None,
        **kwargs: Any,
    ) -> AudioClip:
        voice = voice or self.default_voice
        key = self.cache.compute_key(
            provider=self.name,
            voice=voice,
            text=text,
            speed=speed,
            instruct=instruct,
        )

        # 1. Check content-addressable cache first
        cached_clip = self.cache.get(key)
        if cached_clip is not None:
            if output_path and str(Path(output_path).resolve()) != str(Path(cached_clip.audio_path).resolve()):
                import shutil

                shutil.copyfile(cached_clip.audio_path, str(output_path))
                cached_clip.audio_path = str(output_path)
            return cached_clip

        # 2. Synthesize using Kokoro engine
        engine = self._get_engine()
        sample_rate = 24000

        if engine is not None:
            samples, sample_rate = engine.create(text, voice=voice, speed=speed)
            duration = float(len(samples)) / float(sample_rate)
        else:
            # Fallback mock synthesis if engine is not available
            words_count = max(1, len(text.split()))
            duration = max(0.5, (words_count / (150 * speed)) * 60.0)
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            samples = (np.sin(2 * np.pi * 440 * t) * 0.05).astype(np.float32)

        # 3. Write WAV
        target_path = output_path or (self.cache.cache_dir / f"{key}.wav")
        self.write_wav(target_path, samples, sample_rate=sample_rate)

        # 4. Compute word timestamps & sentence boundaries
        word_timings = self.estimate_word_timings(text, duration)
        sentences = self.extract_sentences(text, word_timings)

        clip = AudioClip(
            audio_path=str(target_path),
            duration=round(duration, 3),
            sample_rate=sample_rate,
            text=text,
            words=word_timings,
            sentences=sentences,
            provider=self.name,
            voice=voice,
            instruct=instruct,
            metadata={"speed": speed, "samples_count": len(samples)},
        )

        # 5. Store into cache
        self.cache.put(key, clip)
        if output_path:
            clip.audio_path = str(output_path)
        return clip
