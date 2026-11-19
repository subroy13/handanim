"""Kokoro-82M local offline TTS provider.

High-fidelity, 82M-parameter lightweight open-weight TTS model running on macOS
via ONNX runtime or PyTorch, supporting all 54 built-in voice embeddings as well
as arbitrary 256-D latent style-vector blending across voices.
"""

from __future__ import annotations

import hashlib
import logging
import os
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from ..cache import AudioCache
from ..schema import AudioClip
from .base import BaseVoiceProvider

logger = logging.getLogger(__name__)

KOKORO_MODEL_URL = "https://huggingface.co/fastrtc/kokoro-onnx/resolve/main/kokoro-v1.0.onnx"
KOKORO_VOICES_URL = "https://huggingface.co/fastrtc/kokoro-onnx/resolve/main/voices-v1.0.bin"

# Full catalog of all 54 voice embeddings shipped in Kokoro v1.0 (voices-v1.0.bin)
KOKORO_VOICE_CATALOG: dict[str, list[str]] = {
    "american_female": [
        "af_alloy",
        "af_aoede",
        "af_bella",
        "af_heart",
        "af_jessica",
        "af_kore",
        "af_nicole",
        "af_nova",
        "af_river",
        "af_sarah",
        "af_sky",
    ],
    "american_male": [
        "am_adam",
        "am_echo",
        "am_eric",
        "am_fenrir",
        "am_liam",
        "am_michael",
        "am_onyx",
        "am_puck",
        "am_santa",
    ],
    "british_female": [
        "bf_alice",
        "bf_emma",
        "bf_isabella",
        "bf_lily",
    ],
    "british_male": [
        "bm_daniel",
        "bm_fable",
        "bm_george",
        "bm_lewis",
    ],
    "spanish": [
        "ef_dora",
        "em_alex",
        "em_santa",
    ],
    "french": [
        "ff_siwis",
    ],
    "hindi": [
        "hf_alpha",
        "hf_beta",
        "hm_omega",
        "hm_psi",
    ],
    "italian": [
        "if_sara",
        "im_nicola",
    ],
    "japanese": [
        "jf_alpha",
        "jf_gongitsune",
        "jf_nezumi",
        "jf_tebukuro",
        "jm_kumo",
    ],
    "portuguese": [
        "pf_dora",
        "pm_alex",
        "pm_santa",
    ],
    "mandarin": [
        "zf_xiaobei",
        "zf_xiaoni",
        "zf_xiaoxiao",
        "zf_xiaoyi",
        "zm_yunjian",
        "zm_yunxi",
        "zm_yunxia",
        "zm_yunyang",
    ],
}

KOKORO_ALL_VOICES: list[str] = [
    voice_id
    for group in KOKORO_VOICE_CATALOG.values()
    for voice_id in group
]

# Built-in named 256-D latent voice blend presets
KOKORO_BLEND_PRESETS: dict[str, str] = {
    "blend_transatlantic": "am_puck:0.6+bm_fable:0.4",
    "blend_professor": "am_fenrir:0.55+am_onyx:0.45",
    "blend_storyteller": "bm_fable:0.6+am_liam:0.4",
    "blend_host_female": "af_aoede:0.6+af_kore:0.4",
    "blend_indian_male": "hm_omega:0.55+am_liam:0.45",
    "blend_indian_female": "hf_alpha:0.55+af_aoede:0.45",
    # Studio aliases for convenience
    "studio_transatlantic": "am_puck:0.6+bm_fable:0.4",
    "studio_professor": "am_fenrir:0.55+am_onyx:0.45",
    "studio_indian_en": "hm_omega:0.55+am_liam:0.45",
    "studio_indian_f": "hf_alpha:0.55+af_aoede:0.45",
    "studio_host_f": "af_aoede:0.6+af_kore:0.4",
}

VoiceSpec = str | Mapping[str, float] | Sequence[tuple[str, float] | str] | np.ndarray


class KokoroProvider(BaseVoiceProvider):
    """Local, offline text-to-speech provider using the Kokoro-82M model.

    Supports all 54 built-in Kokoro v1.0 voices as well as arbitrary weighted
    blends of voices in the 256-D style embedding space:
    - Single voice ID: ``voice="am_fenrir"``, ``voice="bm_fable"``, ``voice="af_aoede"``
    - Named blend preset: ``voice="blend_transatlantic"``, ``voice="blend_professor"``
    - Weighted blend string: ``voice="am_puck:0.6+bm_fable:0.4"`` or ``"am_puck:60,bm_fable:40"``
    - Equal-weight blend string: ``voice="am_puck+bm_fable"`` (50% / 50%)
    - Dictionary of weights: ``voice={"am_puck": 0.6, "bm_fable": 0.4}``
    - Sequence of ``(voice, weight)`` pairs or voice names: ``voice=[("am_puck", 0.6), ("bm_fable", 0.4)]``
    - Pre-computed ``(510, 1, 256)`` float32 NumPy style array
    """

    name = "kokoro"
    default_voice = "af_heart"
    supported_voices = list(KOKORO_ALL_VOICES)
    voice_catalog = KOKORO_VOICE_CATALOG
    blend_presets = KOKORO_BLEND_PRESETS

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

    def list_voices(
        self,
        category: str | None = None,
        include_blends: bool = False,
    ) -> list[str]:
        """Return available Kokoro voice IDs.

        Args:
            category: Optional category filter (e.g., ``"american_male"``,
                ``"american_female"``, ``"british_male"``, ``"british_female"``,
                ``"hindi"``, ``"spanish"``, ``"french"``, ``"italian"``,
                ``"japanese"``, ``"portuguese"``, ``"mandarin"``).
            include_blends: If True, appends built-in named blend presets.
        """
        if category is not None:
            key = category.lower().strip()
            if key not in self.voice_catalog:
                valid = ", ".join(sorted(self.voice_catalog.keys()))
                raise ValueError(f"Unknown Kokoro voice category '{category}'. Valid categories: {valid}")
            voices = list(self.voice_catalog[key])
        else:
            voices = list(self.supported_voices)

        if include_blends:
            for preset_name in self.blend_presets:
                if preset_name not in voices:
                    voices.append(preset_name)
        return voices

    @classmethod
    def parse_voice_spec(
        cls,
        voice_spec: str | Mapping[str, float] | Sequence[tuple[str, float] | str] | None,
        available_voices: set[str] | None = None,
    ) -> list[tuple[str, float]]:
        """Parse a voice name, blend expression, dict, or sequence into normalized ``(voice_id, weight)`` pairs.

        Weights are normalized so that they sum to ``1.0``.
        """
        if voice_spec is None:
            voice_spec = cls.default_voice

        valid_voices = available_voices if available_voices is not None else set(cls.supported_voices)

        raw_pairs: list[tuple[str, float]] = []

        if isinstance(voice_spec, str):
            spec_str = voice_spec.strip()
            if not spec_str:
                spec_str = cls.default_voice

            # Expand top-level named preset if exact match
            if spec_str in cls.blend_presets:
                spec_str = cls.blend_presets[spec_str]

            # Split on '+' or ','
            normalized_expr = spec_str.replace(",", "+")
            tokens = [tok.strip() for tok in normalized_expr.split("+") if tok.strip()]
            if not tokens:
                raise ValueError(f"Invalid empty voice specification: {voice_spec!r}")

            for tok in tokens:
                if ":" in tok:
                    v_name, w_str = tok.split(":", 1)
                    v_name = v_name.strip()
                    try:
                        weight = float(w_str.strip())
                    except ValueError as err:
                        raise ValueError(
                            f"Invalid blend weight '{w_str}' for voice '{v_name}' in '{voice_spec}'."
                        ) from err
                else:
                    v_name = tok.strip()
                    weight = 1.0

                if weight <= 0:
                    raise ValueError(f"Voice blend weight must be positive, got {weight} for '{v_name}'.")

                # Allow recursive expansion if a blend component itself is a preset
                if v_name in cls.blend_presets:
                    sub_pairs = cls.parse_voice_spec(cls.blend_presets[v_name], available_voices=valid_voices)
                    for sub_v, sub_w in sub_pairs:
                        raw_pairs.append((sub_v, weight * sub_w))
                else:
                    raw_pairs.append((v_name, weight))

        elif isinstance(voice_spec, Mapping):
            if not voice_spec:
                raise ValueError("Voice blend mapping cannot be empty.")
            for v_name, weight_val in voice_spec.items():
                v_str = str(v_name).strip()
                weight = float(weight_val)
                if weight <= 0:
                    raise ValueError(f"Voice blend weight must be positive, got {weight} for '{v_str}'.")
                if v_str in cls.blend_presets:
                    sub_pairs = cls.parse_voice_spec(cls.blend_presets[v_str], available_voices=valid_voices)
                    for sub_v, sub_w in sub_pairs:
                        raw_pairs.append((sub_v, weight * sub_w))
                else:
                    raw_pairs.append((v_str, weight))

        elif isinstance(voice_spec, Sequence):
            if not voice_spec:
                raise ValueError("Voice blend sequence cannot be empty.")
            for item in voice_spec:
                if isinstance(item, str):
                    v_str = item.strip()
                    weight = 1.0
                elif isinstance(item, Sequence) and len(item) == 2:
                    v_str = str(item[0]).strip()
                    weight = float(item[1])
                else:
                    raise TypeError(
                        f"Expected voice name string or (voice, weight) pair in blend sequence, got {item!r}"
                    )
                if weight <= 0:
                    raise ValueError(f"Voice blend weight must be positive, got {weight} for '{v_str}'.")
                if v_str in cls.blend_presets:
                    sub_pairs = cls.parse_voice_spec(cls.blend_presets[v_str], available_voices=valid_voices)
                    for sub_v, sub_w in sub_pairs:
                        raw_pairs.append((sub_v, weight * sub_w))
                else:
                    raw_pairs.append((v_str, weight))
        else:
            raise TypeError(f"Unsupported voice specification type: {type(voice_spec).__name__}")

        # Combine duplicate voice entries in order of first appearance
        merged: dict[str, float] = {}
        for v_name, weight in raw_pairs:
            if valid_voices and v_name not in valid_voices:
                raise ValueError(
                    f"Unknown Kokoro voice '{v_name}'. Call KokoroProvider().list_voices() to inspect all 54 voices."
                )
            merged[v_name] = merged.get(v_name, 0.0) + weight

        total_weight = sum(merged.values())
        if total_weight <= 0:
            raise ValueError("Total voice blend weight must be greater than 0.")

        return [(v_name, weight / total_weight) for v_name, weight in merged.items()]

    @classmethod
    def format_voice_spec(
        cls,
        voice_spec: VoiceSpec | None,
        available_voices: set[str] | None = None,
    ) -> str:
        """Convert any voice specification into a canonical string label for caching and metadata."""
        if isinstance(voice_spec, np.ndarray):
            digest = hashlib.sha256(np.ascontiguousarray(voice_spec, dtype=np.float32).tobytes()).hexdigest()[:12]
            return f"custom_style_{digest}"

        if isinstance(voice_spec, str):
            stripped = voice_spec.strip()
            if stripped in cls.blend_presets:
                return stripped

        pairs = cls.parse_voice_spec(voice_spec, available_voices=available_voices)
        if len(pairs) == 1:
            return pairs[0][0]
        return "+".join(f"{v_name}:{weight:.3f}".rstrip("0").rstrip(".") for v_name, weight in pairs)

    @classmethod
    def infer_language(
        cls,
        voice_spec: VoiceSpec | None,
        native_non_english: bool = False,
    ) -> str:
        """Infer espeak-ng phonemizer language code from the dominant voice in `voice_spec`.

        By default (`native_non_english=False`), British voices (`bf_*`, `bm_*`)
        select `"en-gb"` and all other voices default to `"en-us"` so cross-accent
        voices (e.g. `hm_omega`, `hf_alpha`) speak English scripts seamlessly.
        When `native_non_english=True`, non-English prefixes map to their native
        espeak-ng language code (`"es"`, `"fr-fr"`, `"hi"`, `"it"`, `"ja"`, `"pt-br"`, `"cmn"`).
        """
        if isinstance(voice_spec, np.ndarray):
            return "en-us"

        try:
            pairs = cls.parse_voice_spec(voice_spec, available_voices=set())
        except Exception:
            return "en-us"

        if not pairs:
            return "en-us"

        dominant_voice = max(pairs, key=lambda item: item[1])[0]
        prefix = dominant_voice[:1].lower()

        if prefix == "b":
            return "en-gb"
        if not native_non_english:
            return "en-us"

        native_map = {
            "a": "en-us",
            "b": "en-gb",
            "e": "es",
            "f": "fr-fr",
            "h": "hi",
            "i": "it",
            "j": "ja",
            "p": "pt-br",
            "z": "cmn",
        }
        return native_map.get(prefix, "en-us")

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
                logger.warning(
                    "kokoro-onnx is not installed in this Python environment (%s); falling back to mock sine-wave audio.",
                    err,
                )
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

    def blend_voices(
        self,
        voice_spec: str | Mapping[str, float] | Sequence[tuple[str, float] | str],
    ) -> np.ndarray:
        """Compute a blended `(510, 1, 256)` float32 style embedding from two or more Kokoro voices.

        Args:
            voice_spec: A blend string (e.g. ``"am_puck:0.6+bm_fable:0.4"`` or ``"am_puck+bm_fable"``),
                preset name (e.g. ``"blend_transatlantic"``), dict ``{"am_puck": 0.6, "bm_fable": 0.4}``,
                or sequence of ``(voice_name, weight)`` pairs.

        Returns:
            A ``(510, 1, 256)`` float32 NumPy style vector suitable for passing to ``synthesize(voice=...)``.
        """
        engine = self._get_engine()
        available = set(engine.voices.keys()) if (engine is not None and hasattr(engine, "voices")) else None
        pairs = self.parse_voice_spec(voice_spec, available_voices=available)

        if engine is None:
            # Deterministic synthetic style tensor when running in mock fallback mode
            blended = np.zeros((510, 1, 256), dtype=np.float32)
            for v_name, weight in pairs:
                seed = int.from_bytes(hashlib.sha256(v_name.encode("utf-8")).digest()[:4], "little")
                rng = np.random.default_rng(seed)
                blended += float(weight) * rng.standard_normal((510, 1, 256), dtype=np.float32)
            return blended

        blended_style: np.ndarray | None = None
        for v_name, weight in pairs:
            style = np.asarray(engine.get_voice_style(v_name), dtype=np.float32)
            if blended_style is None:
                blended_style = style * float(weight)
            else:
                blended_style = blended_style + style * float(weight)

        assert blended_style is not None
        return blended_style.astype(np.float32)

    def _resolve_engine_voice(
        self,
        voice: VoiceSpec | None,
        engine: Any,
    ) -> tuple[str | np.ndarray, str, list[tuple[str, float]]]:
        """Resolve `voice` into `(engine_voice_arg, canonical_voice_label, components)`."""
        if isinstance(voice, np.ndarray):
            arr = np.asarray(voice, dtype=np.float32)
            label = self.format_voice_spec(arr)
            return arr, label, [(label, 1.0)]

        available = (
            set(engine.voices.keys()) | set(self.supported_voices)
            if (engine is not None and hasattr(engine, "voices"))
            else set(self.supported_voices)
        )
        pairs = self.parse_voice_spec(voice, available_voices=available)
        label = self.format_voice_spec(voice, available_voices=available)

        if len(pairs) == 1 and engine is not None:
            return pairs[0][0], label, pairs

        if engine is None:
            return label, label, pairs

        blended_style: np.ndarray | None = None
        for v_name, weight in pairs:
            style = np.asarray(engine.get_voice_style(v_name), dtype=np.float32)
            if blended_style is None:
                blended_style = style * float(weight)
            else:
                blended_style = blended_style + style * float(weight)

        assert blended_style is not None
        return blended_style.astype(np.float32), label, pairs

    def synthesize(
        self,
        text: str,
        voice: VoiceSpec | None = None,
        speed: float = 1.0,
        instruct: str | None = None,
        output_path: str | Path | None = None,
        lang: str | None = None,
        **kwargs: Any,
    ) -> AudioClip:
        engine = self._get_engine()
        engine_voice, voice_label, components = self._resolve_engine_voice(voice, engine)
        resolved_lang = lang or self.infer_language(voice)

        cache_voice_key = voice_label if resolved_lang == "en-us" else f"{voice_label}@{resolved_lang}"
        key = self.cache.compute_key(
            provider=self.name,
            voice=cache_voice_key,
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
        sample_rate = 24000

        if engine is not None:
            try:
                samples, sample_rate = engine.create(
                    text,
                    voice=engine_voice,
                    speed=speed,
                    lang=resolved_lang,
                )
            except TypeError:
                # Backwards compatibility for custom/mocked engine.create without `lang` parameter
                samples, sample_rate = engine.create(
                    text,
                    voice=engine_voice,
                    speed=speed,
                )
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

        metadata: dict[str, Any] = {
            "speed": speed,
            "samples_count": len(samples),
            "lang": resolved_lang,
        }
        if len(components) > 1:
            metadata["blend_components"] = [
                {"voice": v_name, "weight": round(weight, 4)} for v_name, weight in components
            ]

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
            metadata=metadata,
        )

        # 5. Store into cache
        self.cache.put(key, clip)
        if output_path:
            clip.audio_path = str(output_path)
        return clip
