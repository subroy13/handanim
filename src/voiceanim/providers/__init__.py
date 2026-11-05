"""Voice synthesis provider registry and factory."""

from __future__ import annotations

from typing import Any

from .base import BaseVoiceProvider
from .kokoro_provider import KokoroProvider
from .mock_provider import MockVoiceProvider
from .polly_provider import PollyProvider
from .qwen_provider import QwenTTSProvider

PROVIDERS: dict[str, type[BaseVoiceProvider]] = {
    "kokoro": KokoroProvider,
    "polly": PollyProvider,
    "qwen": QwenTTSProvider,
    "mock": MockVoiceProvider,
}


def get_provider(name: str = "kokoro", **kwargs: Any) -> BaseVoiceProvider:
    """Retrieve an initialized voice provider instance.

    Args:
        name: Provider name ('kokoro' [default], 'polly', 'qwen', 'mock').
        **kwargs: Provider-specific configuration arguments.

    Returns:
        An instance of BaseVoiceProvider.
    """
    key = name.lower().strip()
    if key not in PROVIDERS:
        valid = ", ".join(repr(k) for k in PROVIDERS)
        raise ValueError(f"Unknown voice provider '{name}'. Available providers: {valid}")

    provider_cls = PROVIDERS[key]
    return provider_cls(**kwargs)

