"""Resemble AI Chatterbox TTS provider for expressive speech synthesis and voice cloning.

Supports `ResembleAI/chatterbox` (PyTorch / MPS / CUDA / CPU via `chatterbox-tts`)
and Apple Silicon native MLX weights (`mlx-community/chatterbox-turbo-8bit`,
`mlx-community/chatterbox-fp16`, etc. via `mlx-audio`).

Features:
- Expressiveness control via `exaggeration` (0.0–2.0+) and `cfg_weight` (0.1–1.0)
- Natural-language `instruct` parsing into expressive delivery presets
- Inline paralinguistic tags (`[laugh]`, `[chuckle]`, `[sigh]`, `[gasp]`, `[cough]`)
- Zero-shot voice cloning via `ref_audio` or by passing a `.wav` path as `voice`
- Automatic word-level forced alignment via `voiceanim.aligner.ForcedAligner`
"""

from __future__ import annotations

import logging
import platform
from pathlib import Path
from typing import Any

import numpy as np

from ..aligner import ForcedAligner
from ..cache import AudioCache
from ..schema import AudioClip
from .base import BaseVoiceProvider

logger = logging.getLogger(__name__)

# Built-in expressive delivery profiles for Chatterbox
CHATTERBOX_STYLE_PRESETS: dict[str, dict[str, float]] = {
    "default": {"exaggeration": 0.55, "cfg_weight": 0.50, "temperature": 0.80},
    "energetic": {"exaggeration": 0.85, "cfg_weight": 0.40, "temperature": 0.85},
    "dramatic": {"exaggeration": 1.15, "cfg_weight": 0.35, "temperature": 0.85},
    "playful": {"exaggeration": 0.90, "cfg_weight": 0.42, "temperature": 0.90},
    "calm": {"exaggeration": 0.35, "cfg_weight": 0.60, "temperature": 0.70},
    "storyteller": {"exaggeration": 0.75, "cfg_weight": 0.45, "temperature": 0.82},
}


def parse_chatterbox_instruct(
    instruct: str | None,
    *,
    exaggeration: float | None = None,
    cfg_weight: float | None = None,
    temperature: float | None = None,
    base_preset: str = "default",
) -> dict[str, float]:
    """Translate a natural-language acting direction into Chatterbox acoustic controls."""
    preset = CHATTERBOX_STYLE_PRESETS.get(base_preset, CHATTERBOX_STYLE_PRESETS["default"])
    exag = float(preset["exaggeration"])
    cfg = float(preset["cfg_weight"])
    temp = float(preset["temperature"])

    if instruct:
        low = instruct.lower()
        high_energy_terms = (
            "excited",
            "exciting",
            "energetic",
            "punchy",
            "enthusiastic",
            "dramatic",
            "shock",
            "surpris",
            "incredulous",
            "twist",
            "reveal",
            "catchy",
            "hype",
            "emphatic",
            "hook",
            "playful",
            "amused",
        )
        calm_terms = ("calm", "gentle", "soft", "quiet", "slow", "measured", "serious", "neutral", "flat")
        fast_terms = ("fast", "quick", "brisk", "snappy", "rapid")
        slow_terms = ("slow", "deliberate", "pause", "suspense", "dramatic")

        high_hits = sum(1 for term in high_energy_terms if term in low)
        calm_hits = sum(1 for term in calm_terms if term in low)

        if high_hits > 0:
            exag = min(1.4, max(exag, 0.75 + 0.12 * min(high_hits, 4)))
            cfg = min(cfg, 0.42)
            temp = max(temp, 0.85)
        elif calm_hits > 0:
            exag = min(exag, 0.35)
            cfg = max(cfg, 0.58)
            temp = min(temp, 0.72)

        if any(term in low for term in slow_terms):
            cfg = min(cfg, 0.35)
        elif any(term in low for term in fast_terms):
            cfg = max(cfg, 0.55)

    return {
        "exaggeration": round(float(exaggeration if exaggeration is not None else exag), 3),
        "cfg_weight": round(float(cfg_weight if cfg_weight is not None else cfg), 3),
        "temperature": round(float(temperature if temperature is not None else temp), 3),
    }


class ChatterboxProvider(BaseVoiceProvider):
    """Expressive speech synthesis provider backed by Resemble AI Chatterbox."""

    name = "chatterbox"
    default_voice = "default"
    supported_voices = list(CHATTERBOX_STYLE_PRESETS.keys())

    def __init__(
        self,
        model_id: str | None = None,
        backend: str = "auto",
        device: str = "auto",
        ref_audio: str | Path | None = None,
        exaggeration: float | None = None,
        cfg_weight: float | None = None,
        temperature: float | None = None,
        align_backend: str = "auto",
        cache: AudioCache | None = None,
        fallback_to_mock: bool = False,
    ):
        self.backend = backend.lower().strip()
        self.device = device
        self.ref_audio = str(ref_audio) if ref_audio is not None else None
        self.default_exaggeration = exaggeration
        self.default_cfg_weight = cfg_weight
        self.default_temperature = temperature
        self.align_backend = align_backend
        self.cache = cache or AudioCache()
        self.fallback_to_mock = fallback_to_mock

        if model_id is None:
            is_apple_silicon = platform.system() == "Darwin" and platform.machine() == "arm64"
            self.model_id = (
                "mlx-community/chatterbox-fp16"
                if (self.backend == "mlx" or (self.backend == "auto" and is_apple_silicon))
                else "ResembleAI/chatterbox"
            )
        else:
            self.model_id = model_id

        self._mlx_model = None
        self._torch_model = None

    def _resolve_device(self) -> str:
        if self.device != "auto":
            return self.device
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"

    def _get_mlx_model(self):
        if self._mlx_model is not None:
            return self._mlx_model
        try:
            from mlx_audio.tts.utils import load_model

            mlx_repo = (
                "mlx-community/chatterbox-fp16"
                if self.model_id == "ResembleAI/chatterbox"
                else self.model_id
            )
            logger.info("Loading Chatterbox MLX model '%s'...", mlx_repo)
            self._mlx_model = load_model(mlx_repo)
            return self._mlx_model
        except ImportError:
            return None
        except Exception as exc:
            logger.warning("Could not load Chatterbox via mlx-audio: %s", exc)
            return None

    def _get_torch_model(self):
        if self._torch_model is not None:
            return self._torch_model
        try:
            import torch
            from chatterbox.tts import ChatterboxTTS

            dev = self._resolve_device()
            logger.info("Loading ChatterboxTTS on %s...", dev)

            # Workaround for macOS MPS / CPU checkpoints saved on CUDA
            orig_load = torch.load

            def _patched_load(*args: Any, **kwargs: Any):
                if "map_location" not in kwargs:
                    kwargs["map_location"] = torch.device(dev)
                return orig_load(*args, **kwargs)

            torch.load = _patched_load  # type: ignore[assignment]
            try:
                self._torch_model = ChatterboxTTS.from_pretrained(device=dev)
            finally:
                torch.load = orig_load  # type: ignore[assignment]
            return self._torch_model
        except ImportError:
            return None
        except Exception as exc:
            logger.warning("Could not load ChatterboxTTS: %s", exc)
            return None

    def _synthesize_mlx(
        self,
        text: str,
        ref_audio: str | None,
        speed: float,
        controls: dict[str, float],
    ) -> tuple[np.ndarray, int] | None:
        model = self._get_mlx_model()
        if model is None:
            return None

        gen_kwargs: dict[str, Any] = {
            "text": text,
            "exaggeration": controls["exaggeration"],
            "cfg_weight": controls["cfg_weight"],
            "temperature": controls["temperature"],
            "speed": float(speed),
        }
        if ref_audio:
            gen_kwargs["ref_audio"] = ref_audio

        # Filter kwargs to match the loaded mlx-audio model's generate signature
        import inspect

        sig = inspect.signature(model.generate)
        if not any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            gen_kwargs = {k: v for k, v in gen_kwargs.items() if k in sig.parameters}

        chunks: list[np.ndarray] = []
        sr = int(getattr(model, "sample_rate", 24000))
        for res in model.generate(**gen_kwargs):
            audio = np.asarray(res.audio, dtype=np.float32).ravel()
            chunks.append(audio)
            if hasattr(res, "sample_rate") and res.sample_rate:
                sr = int(res.sample_rate)

        if not chunks:
            return None
        return np.concatenate(chunks), sr

    def _synthesize_torch(
        self,
        text: str,
        ref_audio: str | None,
        controls: dict[str, float],
    ) -> tuple[np.ndarray, int] | None:
        model = self._get_torch_model()
        if model is None:
            return None

        gen_kwargs: dict[str, Any] = {
            "text": text,
            "exaggeration": controls["exaggeration"],
            "cfg_weight": controls["cfg_weight"],
            "temperature": controls["temperature"],
        }
        if ref_audio:
            gen_kwargs["audio_prompt_path"] = ref_audio

        wav = model.generate(**gen_kwargs)
        if hasattr(wav, "detach"):
            wav = wav.detach().cpu().numpy()
        samples = np.asarray(wav, dtype=np.float32).ravel()
        sr = int(getattr(model, "sr", 24000))
        return samples, sr

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float = 1.0,
        instruct: str | None = None,
        output_path: str | Path | None = None,
        *,
        ref_audio: str | Path | None = None,
        exaggeration: float | None = None,
        cfg_weight: float | None = None,
        temperature: float | None = None,
        align: bool | str = "auto",
        **kwargs: Any,
    ) -> AudioClip:
        """Synthesize expressive speech with Chatterbox and compute word timestamps."""
        voice_label = voice or self.default_voice
        effective_ref = str(ref_audio) if ref_audio is not None else self.ref_audio
        if effective_ref is None and voice and Path(voice).is_file():
            effective_ref = str(Path(voice).resolve())

        base_preset = voice_label if voice_label in CHATTERBOX_STYLE_PRESETS else "default"
        controls = parse_chatterbox_instruct(
            instruct,
            exaggeration=exaggeration if exaggeration is not None else self.default_exaggeration,
            cfg_weight=cfg_weight if cfg_weight is not None else self.default_cfg_weight,
            temperature=temperature if temperature is not None else self.default_temperature,
            base_preset=base_preset,
        )

        cache_instruct = (
            f"{instruct or ''}|exag={controls['exaggeration']}|cfg={controls['cfg_weight']}"
            f"|temp={controls['temperature']}|ref={effective_ref or ''}"
        )
        key = self.cache.compute_key(
            provider=self.name,
            model=self.model_id,
            voice=voice_label,
            text=text,
            speed=speed,
            instruct=cache_instruct,
        )

        cached = self.cache.get(key)
        if cached is not None:
            if output_path and str(Path(output_path).resolve()) != str(Path(cached.audio_path).resolve()):
                import shutil

                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(cached.audio_path, str(output_path))
                cached.audio_path = str(output_path)
            return cached

        samples: np.ndarray | None = None
        sample_rate = 24000
        used_backend = "none"

        order = ["mlx", "torch"] if self.backend == "auto" else [self.backend]
        for candidate in order:
            if candidate == "mlx":
                res = self._synthesize_mlx(text, effective_ref, speed, controls)
                if res is not None:
                    samples, sample_rate = res
                    used_backend = "mlx"
                    break
            elif candidate in ("torch", "chatterbox"):
                res = self._synthesize_torch(text, effective_ref, controls)
                if res is not None:
                    samples, sample_rate = res
                    used_backend = "torch"
                    break

        if samples is None:
            if not self.fallback_to_mock:
                raise RuntimeError(
                    "ChatterboxProvider requires either:\n"
                    "  1. Apple Silicon MLX: pip install mlx-audio\n"
                    "  2. Or PyTorch backend: pip install chatterbox-tts torchaudio\n"
                    f"Model requested: {self.model_id}"
                )
            words_count = max(1, len(text.split()))
            est_dur = max(0.5, (words_count / (155.0 * speed)) * 60.0)
            t = np.linspace(0.0, est_dur, int(sample_rate * est_dur), endpoint=False)
            samples = (np.sin(2.0 * np.pi * 440.0 * t) * 0.05).astype(np.float32)
            used_backend = "mock"

        duration = float(len(samples)) / float(sample_rate)
        target_path = Path(output_path) if output_path is not None else (self.cache.cache_dir / f"{key}.wav")
        self.write_wav(target_path, samples, sample_rate=sample_rate)

        align_backend_used = "heuristic"
        if align is False:
            word_timings = self.estimate_word_timings(text, duration)
        else:
            b = self.align_backend if align in (True, "auto") else str(align)
            aligner = ForcedAligner(backend=b)
            word_timings, align_backend_used = aligner.align(target_path, text, duration=duration)

        sentences = self.extract_sentences(text, word_timings)
        clip = AudioClip(
            audio_path=str(target_path),
            duration=round(duration, 3),
            sample_rate=sample_rate,
            text=text,
            words=word_timings,
            sentences=sentences,
            provider=self.name,
            voice=voice_label,
            instruct=instruct,
            metadata={
                "model_id": self.model_id,
                "backend": used_backend,
                "speed": speed,
                "exaggeration": controls["exaggeration"],
                "cfg_weight": controls["cfg_weight"],
                "temperature": controls["temperature"],
                "ref_audio": effective_ref,
                "alignment_backend": align_backend_used,
            },
        )

        self.cache.put(key, clip)
        if output_path is not None:
            clip.audio_path = str(target_path)
        return clip
