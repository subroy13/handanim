"""Voice synthesis provider registry and factory."""

from __future__ import annotations

from typing import Any

from .base import BaseVoiceProvider
from .chatterbox_provider import CHATTERBOX_STYLE_PRESETS, ChatterboxProvider
from .kokoro_provider import (
    KOKORO_ALL_VOICES,
    KOKORO_BLEND_PRESETS,
    KOKORO_VOICE_CATALOG,
    KokoroProvider,
)
from .mock_provider import MockVoiceProvider
from .polly_provider import PollyProvider
from .qwen_provider import QwenTTSProvider
from .zonos_provider import ZONOS_BLEND_PRESETS, ZONOS_STEERING_PRESETS, ZonosProvider

PROVIDERS: dict[str, type[BaseVoiceProvider]] = {
    "kokoro": KokoroProvider,
    "polly": PollyProvider,
    "qwen": QwenTTSProvider,
    "chatterbox": ChatterboxProvider,
    "zonos": ZonosProvider,
    "mock": MockVoiceProvider,
}

_PROVIDER_ALIASES: dict[str, str] = {
    "chatterbox-tts": "chatterbox",
    "chatterbox-turbo": "chatterbox",
    "zonos3": "zonos",
    "zonos3-mini": "zonos",
    "zonos3_mini": "zonos",
}


def get_provider(name: str = "kokoro", **kwargs: Any) -> BaseVoiceProvider:
    """Retrieve an initialized voice provider instance.

    Args:
        name: Provider name ('kokoro' [default], 'polly', 'qwen', 'chatterbox', 'zonos', 'mock').
        **kwargs: Provider-specific configuration arguments.

    Returns:
        An instance of BaseVoiceProvider.
    """
    key = name.lower().strip()
    key = _PROVIDER_ALIASES.get(key, key)
    if key not in PROVIDERS:
        valid = ", ".join(repr(k) for k in PROVIDERS)
        raise ValueError(f"Unknown voice provider '{name}'. Available providers: {valid}")

    provider_cls = PROVIDERS[key]
    return provider_cls(**kwargs)


__all__ = [
    "BaseVoiceProvider",
    "ChatterboxProvider",
    "CHATTERBOX_STYLE_PRESETS",
    "KokoroProvider",
    "KOKORO_ALL_VOICES",
    "KOKORO_VOICE_CATALOG",
    "KOKORO_BLEND_PRESETS",
    "MockVoiceProvider",
    "PollyProvider",
    "QwenTTSProvider",
    "ZonosProvider",
    "ZONOS_BLEND_PRESETS",
    "ZONOS_STEERING_PRESETS",
    "PROVIDERS",
    "get_provider",
]
