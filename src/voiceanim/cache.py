"""Content-addressed audio cache for deterministic and reproducible voice generation."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from .schema import AudioClip


class AudioCache:
    """Manages cached synthesized speech waveforms and metadata JSON files.

    Guarantees strict reproducibility: identical inputs produce identical hashes,
    allowing re-renders of whiteboard animations to avoid redundant API or model synthesis.
    """

    def __init__(self, cache_dir: str | Path = ".voiceanim_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_key(
        provider: str,
        voice: str,
        text: str,
        speed: float = 1.0,
        model: str | None = None,
        instruct: str | None = None,
    ) -> str:
        """Generate a SHA-256 hash identifying the exact speech synthesis parameters."""
        normalized_text = text.strip()
        raw = f"{provider.lower()}:{model or ''}:{voice}:{speed:.2f}:{instruct or ''}:{normalized_text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> AudioClip | None:
        """Retrieve a cached AudioClip if both .wav and .json exist and are intact."""
        wav_path = self.cache_dir / f"{key}.wav"
        json_path = self.cache_dir / f"{key}.json"

        if not wav_path.exists() or not json_path.exists():
            return None

        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            data["audio_path"] = str(wav_path)
            return AudioClip.from_dict(data)
        except Exception:
            return None

    def put(
        self,
        key: str,
        clip: AudioClip,
        audio_bytes: bytes | None = None,
        source_audio_path: str | Path | None = None,
    ) -> AudioClip:
        """Store an AudioClip and its waveform into the cache.

        Args:
            key: The SHA-256 cache key.
            clip: AudioClip metadata.
            audio_bytes: Optional raw bytes of the audio (WAV/MP3).
            source_audio_path: Optional path to an existing audio file to copy into cache.

        Returns:
            Updated AudioClip pointing to the cached audio file path.
        """
        wav_path = self.cache_dir / f"{key}.wav"
        json_path = self.cache_dir / f"{key}.json"

        if audio_bytes is not None:
            wav_path.write_bytes(audio_bytes)
        elif source_audio_path is not None and Path(source_audio_path).exists():
            if str(Path(source_audio_path).resolve()) != str(wav_path.resolve()):
                shutil.copyfile(str(source_audio_path), str(wav_path))
        elif clip.audio_path and Path(clip.audio_path).exists():
            if str(Path(clip.audio_path).resolve()) != str(wav_path.resolve()):
                shutil.copyfile(str(clip.audio_path), str(wav_path))

        clip_data = clip.to_dict()
        clip_data["audio_path"] = str(wav_path)
        json_path.write_text(json.dumps(clip_data, indent=2), encoding="utf-8")

        clip.audio_path = str(wav_path)
        return clip

    def clear(self):
        """Remove all files from the cache directory."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
