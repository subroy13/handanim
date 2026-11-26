"""Zyphra ZONOS3-Mini TTS provider with activation steering and zero-shot voice cloning.

Supports `Zyphra/ZONOS3-Mini` across three backends:
1. **Local ZONOS3-Mini REST server** (`http://localhost:1919/v2/generate` or `ZONOS_API_URL`)
   with full activation-steering `controls` (`delivery.emotion`, `delivery.projection`,
   `delivery.liveliness`, `delivery.whisper`) and word-level `control_spans`.
2. **Apple Silicon native MLX** (`mlx-community/ZONOS3-Mini` via `mlx-audio`).
3. **PyTorch / Hugging Face** (`Zyphra/ZONOS3-Mini` via `zonos` or `Zyphra/ZONOS3-Mini-hf`
   via `transformers`).
"""

from __future__ import annotations

import io
import json
import logging
import os
import platform
import urllib.error
import urllib.request
import wave
from pathlib import Path
from typing import Any

import numpy as np

from ..aligner import ForcedAligner
from ..cache import AudioCache
from ..schema import AudioClip
from .base import BaseVoiceProvider

logger = logging.getLogger(__name__)

# Curated steering presets for ZONOS3-Mini's /v2/generate controls
ZONOS_STEERING_PRESETS: dict[str, dict[str, float]] = {
    "neutral": {},
    "energetic": {"delivery.emotion": 2.0, "delivery.projection": 1.5, "delivery.liveliness": 1.5},
    "dramatic": {"delivery.emotion": 2.5, "delivery.projection": 2.0, "delivery.liveliness": 2.0},
    "playful": {"delivery.emotion": 2.2, "delivery.liveliness": 1.8},
    "whisper": {"delivery.whisper": 3.0, "delivery.projection": -1.0},
    "calm": {"delivery.liveliness": -0.8, "delivery.projection": -0.4},
}

# Curated 192-D speaker-embedding blend presets for ZONOS3-Mini
ZONOS_BLEND_PRESETS: dict[str, str] = {
    "indian_modern_f": "ananya:0.55+savannah:0.45",
    "indian_modern_m": "arjun:0.55+wyatt:0.45",
    "indian_british_m": "arjun:0.60+rupert:0.40",
    "indian_warm_m": "chaitanya:0.55+wyatt:0.45",
    "transatlantic_m": "jett:0.60+rupert:0.40",
    "british_stem_f": "imogen:0.65+savannah:0.35",
}


def parse_zonos_instruct(
    instruct: str | None,
    explicit_controls: dict[str, float] | None = None,
) -> dict[str, float]:
    """Translate a natural-language acting direction into ZONOS3-Mini steering controls."""
    controls: dict[str, float] = {}
    if instruct:
        low = instruct.lower()
        if any(w in low for w in ("excited", "exciting", "energetic", "punchy", "catchy", "hype", "enthusiastic")):
            controls["delivery.emotion"] = 2.2
            controls["delivery.projection"] = 1.6
            controls["delivery.liveliness"] = 1.6
        if any(w in low for w in ("dramatic", "shock", "surpris", "incredulous", "twist", "reveal")):
            controls["delivery.emotion"] = max(controls.get("delivery.emotion", 0.0), 2.5)
            controls["delivery.liveliness"] = max(controls.get("delivery.liveliness", 0.0), 1.8)
        if any(w in low for w in ("playful", "amused", "cheerful", "happy", "smile")):
            controls["delivery.emotion"] = max(controls.get("delivery.emotion", 0.0), 2.0)
            controls["delivery.liveliness"] = max(controls.get("delivery.liveliness", 0.0), 1.4)
        if any(w in low for w in ("whisper", "secret", "hush", "lean in")):
            controls["delivery.whisper"] = 2.5
        if any(w in low for w in ("calm", "gentle", "measured", "serious", "clear")):
            controls.setdefault("delivery.liveliness", -0.5)

    if explicit_controls:
        controls.update({str(k): float(v) for k, v in explicit_controls.items()})
    return controls


class ZonosProvider(BaseVoiceProvider):
    """Expressive speech synthesis provider backed by Zyphra ZONOS3-Mini."""

    name = "zonos"
    default_voice = "jett"
    supported_voices = [
        "ananya",
        "arjun",
        "chaitanya",
        "cillian",
        "gaspard",
        "ginevra",
        "haoran",
        "imogen",
        "jett",
        "leonor",
        "liesel",
        "lorenzo",
        "meilin",
        "minjun",
        "morgana",
        "rodrigo",
        "rupert",
        "sakura",
        "savannah",
        "seoyeon",
        "sravya",
        "thaddeus",
        "thiago",
        "willow",
        "wolfgang",
        "wyatt",
        "ximena",
    ]

    def __init__(
        self,
        model_id: str | None = None,
        backend: str = "auto",
        api_url: str | None = None,
        device: str = "auto",
        ref_audio: str | Path | None = None,
        language: str = "en-us",
        align_backend: str = "auto",
        cache: AudioCache | None = None,
        fallback_to_mock: bool = False,
    ):
        self.backend = backend.lower().strip()
        self.api_url = (api_url or os.environ.get("ZONOS_API_URL") or "http://127.0.0.1:1919").rstrip("/")
        self.device = device
        self.ref_audio = str(ref_audio) if ref_audio is not None else None
        self.language = language
        self.align_backend = align_backend
        self.cache = cache or AudioCache()
        self.fallback_to_mock = fallback_to_mock

        if model_id is None:
            is_apple_silicon = platform.system() == "Darwin" and platform.machine() == "arm64"
            self.model_id = (
                "mlx-community/ZONOS3-Mini"
                if (self.backend == "mlx" or (self.backend == "auto" and is_apple_silicon))
                else "Zyphra/ZONOS3-Mini"
            )
        else:
            self.model_id = model_id

        self._mlx_model = None
        self._torch_model = None

    def _synthesize_server(
        self,
        text: str,
        voice: str,
        language: str,
        controls: dict[str, float],
        control_spans: list[dict[str, Any]] | None = None,
        timeout: float = 60.0,
    ) -> tuple[np.ndarray, int] | None:
        """Call a locally running ZONOS3-Mini server (`POST /v2/generate`)."""
        url = f"{self.api_url}/v2/generate"
        payload: dict[str, Any] = {
            "text": text,
            "language": language,
            "voice": voice,
            "format": "wav",
            "stream": False,
        }
        if controls:
            payload["controls"] = controls
        if control_spans:
            payload["control_spans"] = control_spans

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                wav_bytes = resp.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            return None

        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            sr = wf.getframerate()
            raw = wf.readframes(wf.getnframes())
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        return samples, int(sr)

    def _get_mlx_model(self):
        if self._mlx_model is not None:
            return self._mlx_model
        try:
            from mlx_audio.tts import load as mlx_tts_load

            mlx_repo = (
                "mlx-community/ZONOS3-Mini"
                if self.model_id in ("Zyphra/ZONOS3-Mini", "Zyphra/ZONOS3-Mini-hf")
                else self.model_id
            )
            logger.info("Loading ZONOS3-Mini MLX model '%s'...", mlx_repo)
            self._mlx_model = mlx_tts_load(mlx_repo)
            return self._mlx_model
        except ImportError:
            return None
        except Exception as exc:
            logger.warning("Could not load ZONOS3-Mini via mlx-audio: %s", exc)
            return None

    def _resolve_mlx_blended_embedding(self, model: Any, voice_spec: str) -> np.ndarray | None:
        """Blend 2+ built-in ZONOS3 192-D speaker embeddings from `'arjun:0.55+wyatt:0.45'` or a preset name."""
        spec = ZONOS_BLEND_PRESETS.get(voice_spec.strip().lower(), voice_spec)
        if "+" not in spec and ":" not in spec:
            return None
        parts = [p.strip() for p in spec.split("+") if p.strip()]
        if not parts:
            return None

        weights: list[tuple[str, float]] = []
        for part in parts:
            if ":" in part:
                v_name, w_str = part.split(":", 1)
                weights.append((v_name.strip().lower(), float(w_str.strip())))
            else:
                weights.append((part.strip().lower(), 1.0))

        total_w = sum(w for _, w in weights)
        if total_w <= 0:
            raise ValueError(f"Invalid ZONOS3 voice blend weights in '{voice_spec}'")

        voices_map = getattr(model, "_voices", None)
        model_path = getattr(getattr(model, "config", None), "model_path", None)
        if not isinstance(voices_map, dict) or not model_path:
            return None

        voices_dir = Path(model_path) / "voices"
        blended: np.ndarray | None = None
        for v_name, wt in weights:
            if v_name not in voices_map:
                raise ValueError(
                    f"Unknown ZONOS3 voice '{v_name}' in blend '{voice_spec}'. Available: {', '.join(sorted(voices_map))}"
                )
            with np.load(voices_dir / voices_map[v_name], allow_pickle=False) as archive:
                vec = np.asarray(archive["embedding"], dtype=np.float32).ravel()
            scaled = vec * float(wt / total_w)
            blended = scaled if blended is None else (blended + scaled)

        assert blended is not None
        return blended.astype(np.float32)

    @staticmethod
    def _sanitize_tts_text(text: str) -> str:
        """Normalize Unicode dashes/quotes that can cause ZONOS3-Mini's tokenizer to code-switch."""
        cleaned = (
            text.replace("\u2013", " ")
            .replace("\u2014", ", ")
            .replace("\u2018", "'")
            .replace("\u2019", "'")
            .replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("\u2026", "...")
        )
        return " ".join(cleaned.split())

    def _synthesize_mlx(
        self,
        text: str,
        voice: str,
        ref_audio: str | None,
        speed: float,
        controls: dict[str, float],
        *,
        language: str = "en-us",
        condition_values: dict[str, float] | None = None,
        speaker_cfg_scale: float | None = None,
        temperature: float | None = None,
        seed: int | None = None,
    ) -> tuple[np.ndarray, int] | None:
        model = self._get_mlx_model()
        if model is None:
            return None

        lang_short = "en" if language.lower().startswith("en") else language.lower().split("-")[0]
        gen_kwargs: dict[str, Any] = {
            "text": self._sanitize_tts_text(text),
            "lang_code": lang_short,
        }
        if condition_values is not None:
            gen_kwargs["condition_values"] = condition_values
        elif speed != 1.0:
            gen_kwargs["speed"] = float(speed)
        if seed is not None:
            gen_kwargs["seed"] = int(seed)
        if temperature is not None:
            gen_kwargs["temperature"] = float(temperature)
        elif controls.get("delivery.liveliness", 0.0) >= 1.5:
            gen_kwargs["temperature"] = 0.72

        if ref_audio:
            gen_kwargs["ref_audio"] = ref_audio
            if speaker_cfg_scale is not None:
                gen_kwargs["speaker_cfg_scale"] = float(speaker_cfg_scale)
        else:
            blended_emb = self._resolve_mlx_blended_embedding(model, voice)
            if blended_emb is not None:
                gen_kwargs["speaker_embedding"] = blended_emb
            else:
                gen_kwargs["voice"] = voice
            if speaker_cfg_scale is not None:
                gen_kwargs["speaker_cfg_scale"] = float(speaker_cfg_scale)
        if controls:
            gen_kwargs["controls"] = controls

        import inspect

        sig = inspect.signature(model.generate)
        if not any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            gen_kwargs = {k: v for k, v in gen_kwargs.items() if k in sig.parameters}

        chunks: list[np.ndarray] = []
        sr = int(getattr(model, "sample_rate", 44100))
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
        language: str,
    ) -> tuple[np.ndarray, int] | None:
        try:
            import torch

            dev = (
                self.device
                if self.device != "auto"
                else ("cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu"))
            )
        except ImportError:
            return None

        # Path A: official `zonos` Python package
        try:
            import torchaudio
            from zonos.conditioning import make_cond_dict
            from zonos.model import Zonos

            if self._torch_model is None:
                repo = "Zyphra/ZONOS3-Mini" if self.model_id.startswith("mlx-community/") else self.model_id
                self._torch_model = Zonos.from_pretrained(repo, device=dev)

            speaker = None
            if ref_audio:
                wav, ref_sr = torchaudio.load(ref_audio)
                speaker = self._torch_model.make_speaker_embedding(wav, ref_sr)

            cond_kwargs: dict[str, Any] = {"text": text, "language": language}
            if speaker is not None:
                cond_kwargs["speaker"] = speaker
            cond = make_cond_dict(**cond_kwargs)
            conditioning = self._torch_model.prepare_conditioning(cond)
            codes = self._torch_model.generate(conditioning)
            audio = self._torch_model.autoencoder.decode(codes)[0].detach().cpu().numpy().ravel().astype(np.float32)
            sr = int(self._torch_model.autoencoder.sampling_rate)
            return audio, sr
        except ImportError:
            pass
        except Exception as exc:
            logger.warning("Zonos PyTorch backend failed: %s", exc)

        # Path B: Hugging Face transformers (`Zyphra/ZONOS3-Mini-hf`)
        try:
            from transformers import AutoModel

            if self._torch_model is None:
                hf_repo = "Zyphra/ZONOS3-Mini-hf"
                self._torch_model = AutoModel.from_pretrained(hf_repo, trust_remote_code=True).to(dev)
            out = self._torch_model.generate(text)
            if hasattr(out, "detach"):
                out = out.detach().cpu().numpy()
            samples = np.asarray(out, dtype=np.float32).ravel()
            sr = int(getattr(self._torch_model, "sampling_rate", 44100))
            return samples, sr
        except ImportError:
            return None
        except Exception as exc:
            logger.warning("Zonos transformers backend failed: %s", exc)
            return None

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float = 1.0,
        instruct: str | None = None,
        output_path: str | Path | None = None,
        *,
        ref_audio: str | Path | None = None,
        language: str | None = None,
        controls: dict[str, float] | None = None,
        control_spans: list[dict[str, Any]] | None = None,
        condition_values: dict[str, float] | None = None,
        speaker_cfg_scale: float | None = None,
        temperature: float | None = None,
        seed: int | None = None,
        align: bool | str = "auto",
        **kwargs: Any,
    ) -> AudioClip:
        """Synthesize speech with ZONOS3-Mini using steering controls or zero-shot cloning."""
        voice_label = voice or self.default_voice
        eff_lang = language or self.language
        effective_ref = str(ref_audio) if ref_audio is not None else self.ref_audio
        if effective_ref is None and voice and Path(voice).is_file():
            effective_ref = str(Path(voice).resolve())

        merged_controls = parse_zonos_instruct(instruct, explicit_controls=controls)
        cache_instruct = json.dumps(
            {
                "instruct": instruct or "",
                "controls": merged_controls,
                "control_spans": control_spans or [],
                "ref_audio": effective_ref or "",
                "lang": eff_lang,
                "speaker_cfg_scale": speaker_cfg_scale,
                "temperature": temperature,
                "seed": seed,
            },
            sort_keys=True,
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
        sample_rate = 44100
        used_backend = "none"

        order = ["server", "mlx", "torch"] if self.backend == "auto" else [self.backend]
        for candidate in order:
            if candidate == "server":
                res = self._synthesize_server(text, voice_label, eff_lang, merged_controls, control_spans)
                if res is not None:
                    samples, sample_rate = res
                    used_backend = "server"
                    break
            elif candidate == "mlx":
                res = self._synthesize_mlx(
                    text,
                    voice_label,
                    effective_ref,
                    speed,
                    merged_controls,
                    language=eff_lang,
                    condition_values=condition_values,
                    speaker_cfg_scale=speaker_cfg_scale,
                    temperature=temperature,
                    seed=seed,
                )
                if res is not None:
                    samples, sample_rate = res
                    used_backend = "mlx"
                    break
            elif candidate in ("torch", "transformers", "zonos"):
                res = self._synthesize_torch(text, effective_ref, eff_lang)
                if res is not None:
                    samples, sample_rate = res
                    used_backend = "torch"
                    break

        if samples is None:
            if not self.fallback_to_mock:
                raise RuntimeError(
                    "ZonosProvider requires one of:\n"
                    "  1. Local ZONOS3-Mini server running at ZONOS_API_URL (default http://127.0.0.1:1919)\n"
                    "  2. Apple Silicon MLX: pip install mlx-audio\n"
                    "  3. Or PyTorch/Zonos: pip install git+https://github.com/Zyphra/Zonos.git\n"
                    f"Model requested: {self.model_id}"
                )
            words_count = max(1, len(text.split()))
            est_dur = max(0.5, (words_count / (155.0 * speed)) * 60.0)
            t = np.linspace(0.0, est_dur, int(sample_rate * est_dur), endpoint=False)
            samples = (np.sin(2.0 * np.pi * 480.0 * t) * 0.05).astype(np.float32)
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
                "language": eff_lang,
                "speed": speed,
                "controls": merged_controls,
                "ref_audio": effective_ref,
                "alignment_backend": align_backend_used,
            },
        )

        self.cache.put(key, clip)
        if output_path is not None:
            clip.audio_path = str(target_path)
        return clip
