"""Unit tests for voiceanim content-addressed caching."""

from voiceanim.cache import AudioCache
from voiceanim.schema import AudioClip, WordTimestamp


def test_audio_cache_key_computation():
    k1 = AudioCache.compute_key("kokoro", "af_heart", "Hello world", 1.0)
    k2 = AudioCache.compute_key("kokoro", "af_heart", "Hello world", 1.0)
    assert k1 == k2

    # Different voice
    k3 = AudioCache.compute_key("kokoro", "am_adam", "Hello world", 1.0)
    assert k1 != k3

    # Different speed
    k4 = AudioCache.compute_key("kokoro", "af_heart", "Hello world", 1.2)
    assert k1 != k4

    # Different text
    k5 = AudioCache.compute_key("kokoro", "af_heart", "Different text", 1.0)
    assert k1 != k5

    # Instruction prompt (Qwen)
    k6 = AudioCache.compute_key("qwen", "Vivian", "Hello world", 1.0, instruct="Happy")
    k7 = AudioCache.compute_key("qwen", "Vivian", "Hello world", 1.0, instruct="Sad")
    assert k6 != k7


def test_audio_cache_put_and_get(tmp_path):
    cache = AudioCache(cache_dir=tmp_path)
    key = "test_key_123"

    clip = AudioClip(
        audio_path="",
        duration=2.5,
        text="Sample text",
        words=[WordTimestamp(word="Sample", start=0.1, end=0.8)],
        provider="mock",
        voice="mock_voice",
    )

    audio_bytes = b"RIFFfake_wave_data_here"
    saved_clip = cache.put(key, clip, audio_bytes=audio_bytes)

    assert (tmp_path / f"{key}.wav").exists()
    assert (tmp_path / f"{key}.json").exists()
    assert saved_clip.audio_path == str(tmp_path / f"{key}.wav")

    # Retrieve from cache
    retrieved = cache.get(key)
    assert retrieved is not None
    assert retrieved.duration == 2.5
    assert retrieved.text == "Sample text"
    assert len(retrieved.words) == 1
    assert retrieved.words[0].word == "Sample"

    # Miss
    assert cache.get("nonexistent_key") is None

