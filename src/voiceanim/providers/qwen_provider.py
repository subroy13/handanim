"""Qwen3-TTS provider with prompt-driven natural language instruction control.

Supports Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice and 0.6B models for multi-dimensional
acoustic attribute control (timbre, emotion, rhythm, and prosody) via natural language instructions.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

from ..cache import AudioCache
from ..schema import AudioClip
from .base import BaseVoiceProvider

logger = logging.getLogger(__name__)


class QwenTTSProvider(BaseVoiceProvider):
    """Qwen3-TTS model provider supporting natural language instruction prompts.

    Allows fine-grained, prompt-based control over emotion, prosody, and style:
        engine.synthesize("...", instruct="Speak with inquisitive warmth, pausing after questions")
    """

    name = "qwen"
    default_voice = "Vivian"
    supported_voices = [
        "Vivian",  # Versatile expressive female
        "Ryan",  # Dynamic natural male
        "Uncle_Martin",  # Wise authoritative older male
        "Serena",  # Calm instructional female
        "Aiden",  # Youthful energetic male
    ]

    def __init__(
        self,
        model_id: str = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        cache: AudioCache | None = None,
        hf_token: str | None = None,
        device: str = "auto",
        fallback_to_mock: bool = False,
    ):
        self.model_id = model_id
        self.cache = cache or AudioCache()
        self.hf_token = hf_token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")
        self.device = device
        self.fallback_to_mock = fallback_to_mock
        self._model = None

    def _get_local_model(self):
        """Lazy loader for local qwen-tts pipeline if installed."""
        if self._model is not None:
            return self._model

        try:
            import torch
            from qwen_tts import Qwen3TTSModel  # type: ignore

            device_map = "mps" if torch.backends.mps.is_available() else ("cuda:0" if torch.cuda.is_available() else "cpu")
            logger.info("Loading %s on %s...", self.model_id, device_map)
            self._model = Qwen3TTSModel.from_pretrained(
                self.model_id,
                device_map=device_map,
                dtype=torch.bfloat16 if device_map != "cpu" else torch.float32,
            )
            return self._model
        except ImportError:
            return None
        except Exception as e:
            logger.warning("Could not load local Qwen3TTSModel: %s", e)
            return None

    def _synthesize_hf_api(
        self,
        text: str,
        voice: str,
        instruct: str | None = None,
    ) -> tuple[np.ndarray, int] | None:
        """Call Hugging Face Inference API router if HF_TOKEN is configured."""
        if not self.hf_token:
            return None

        try:
            import urllib.error
            import urllib.request

            url = f"https://api-inference.huggingface.co/models/{self.model_id}"
            payload = {
                "inputs": text,
                "parameters": {
                    "speaker": voice,
                    "instruct": instruct or "Speak naturally and clearly",
                },
            }
            import json

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.hf_token}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                audio_bytes = resp.read()
                # Parse WAV bytes
                import io
                import wave

                with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                    sr = wf.getframerate()
                    frames = wf.readframes(wf.getnframes())
                    samples = np.frombuffer(frames, dtype=np.int16)
                    return samples, sr
        except Exception as e:
            logger.warning("HF Inference API request failed: %s", e)
            return None

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float = 1.0,
        instruct: str | None = None,
        output_path: str | Path | None = None,
        language: str = "English",
        **kwargs: Any,
    ) -> AudioClip:
        voice = voice or self.default_voice
        key = self.cache.compute_key(
            provider=self.name,
            model=self.model_id,
            voice=voice,
            text=text,
            speed=speed,
            instruct=instruct,
        )

        # 1. Check content-addressed cache
        cached_clip = self.cache.get(key)
        if cached_clip is not None:
            if output_path and str(Path(output_path).resolve()) != str(Path(cached_clip.audio_path).resolve()):
                import shutil

                shutil.copyfile(cached_clip.audio_path, str(output_path))
                cached_clip.audio_path = str(output_path)
            return cached_clip

        sample_rate = 24000
        samples: np.ndarray | None = None

        # 2. Try local model
        local_model = self._get_local_model()
        if local_model is not None:
            wavs, sr = local_model.generate_custom_voice(
                text=text,
                language=language,
                speaker=voice,
                instruct=instruct or "Speak naturally and clearly",
            )
            samples = wavs[0]
            sample_rate = sr

        # 3. Try Hugging Face API
        if samples is None:
            api_result = self._synthesize_hf_api(text, voice, instruct)
            if api_result is not None:
                samples, sample_rate = api_result

        # 4. Fallback if not available
        if samples is None:
            if not self.fallback_to_mock:
                raise RuntimeError(
                    f"Qwen3-TTS provider requires either:\n"
                    f"  1. Local 'qwen-tts' package: pip install qwen-tts\n"
                    f"  2. Or Hugging Face token in environment: export HF_TOKEN=your_token\n"
                    f"Model requested: {self.model_id}"
                )
            # Generate simulated mock waveform
            words_count = max(1, len(text.split()))
            duration = max(0.5, (words_count / (150 * speed)) * 60.0)
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            samples = (np.sin(2 * np.pi * 520 * t) * 0.05).astype(np.float32)

        duration = float(len(samples)) / float(sample_rate)

        # 5. Write output WAV
        target_path = output_path or (self.cache.cache_dir / f"{key}.wav")
        self.write_wav(target_path, samples, sample_rate=sample_rate)

        # 6. Extract word timings
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
            metadata={
                "model_id": self.model_id,
                "language": language,
                "speed": speed,
            },
        )

        # 7. Store into cache
        self.cache.put(key, clip)
        if output_path:
            clip.audio_path = str(output_path)
        return clip
