"""Unit tests for voiceanim TTS providers (Kokoro, Polly, Qwen, Mock)."""

import io
from pathlib import Path

import pytest

from voiceanim.cache import AudioCache
from voiceanim.providers import (
    KokoroProvider,
    MockVoiceProvider,
    PollyProvider,
    QwenTTSProvider,
    get_provider,
)


def test_get_provider_factory():
    # Kokoro is default provider
    p_default = get_provider()
    assert isinstance(p_default, KokoroProvider)

    p_kokoro = get_provider("kokoro")
    assert isinstance(p_kokoro, KokoroProvider)

    p_polly = get_provider("polly")
    assert isinstance(p_polly, PollyProvider)

    p_qwen = get_provider("qwen")
    assert isinstance(p_qwen, QwenTTSProvider)

    p_mock = get_provider("mock")
    assert isinstance(p_mock, MockVoiceProvider)

    with pytest.raises(ValueError, match="Unknown voice provider"):
        get_provider("unsupported_provider")


def test_mock_voice_provider(tmp_path):
    cache = AudioCache(cache_dir=tmp_path)
    provider = MockVoiceProvider(cache=cache)
    clip = provider.synthesize("Let's draw a triangle with three vertices.")

    assert clip.duration > 0.5
    assert clip.sample_rate == 24000
    assert Path(clip.audio_path).exists()
    assert len(clip.words) == 7
    assert clip.words[0].word == "Let's"
    assert clip.words[-1].word == "vertices."
    assert clip.get_word_time("triangle") is not None


def test_kokoro_provider_fallback(tmp_path):
    cache = AudioCache(cache_dir=tmp_path)
    # Using fallback_to_mock=True allows testing the full pipeline in environments without local weights
    provider = KokoroProvider(cache=cache, fallback_to_mock=True)
    assert provider.name == "kokoro"
    assert "af_heart" in provider.list_voices()
    assert "am_adam" in provider.list_voices()

    clip = provider.synthesize("Whiteboard animation with Kokoro voice.", voice="am_adam")
    assert clip.provider == "kokoro"
    assert clip.voice == "am_adam"
    assert Path(clip.audio_path).exists()
    assert len(clip.words) == 5


def test_qwen_provider_instruction_and_fallback(tmp_path):
    cache = AudioCache(cache_dir=tmp_path)
    provider = QwenTTSProvider(cache=cache, fallback_to_mock=True)
    assert provider.name == "qwen"
    assert "Vivian" in provider.list_voices()

    clip = provider.synthesize(
        "Observe the parabolic motion of the ball.",
        voice="Vivian",
        instruct="Speak with gentle curiosity and dramatic pacing",
    )
    assert clip.provider == "qwen"
    assert clip.instruct == "Speak with gentle curiosity and dramatic pacing"
    assert Path(clip.audio_path).exists()
    assert len(clip.words) == 7


def test_polly_provider_with_mocked_boto3(monkeypatch, tmp_path):
    cache = AudioCache(cache_dir=tmp_path)
    provider = PollyProvider(cache=cache)

    speech_marks_ndjson = (
        '{"time": 100, "type": "sentence", "start": 0, "end": 20, "value": "Draw a blue circle."}\n'
        '{"time": 100, "type": "word", "start": 0, "end": 4, "value": "Draw"}\n'
        '{"time": 450, "type": "word", "start": 5, "end": 6, "value": "a"}\n'
        '{"time": 600, "type": "word", "start": 7, "end": 11, "value": "blue"}\n'
        '{"time": 950, "type": "word", "start": 12, "end": 19, "value": "circle"}\n'
    )
    # 2 seconds of 24kHz 16-bit PCM silence (2 * 24000 * 2 = 96000 bytes)
    mock_pcm_bytes = b"\x00" * 96000

    class MockAudioStream(io.BytesIO):
        pass

    class MockPollyClient:
        def synthesize_speech(self, **kwargs):
            if kwargs.get("OutputFormat") == "json":
                return {"AudioStream": MockAudioStream(speech_marks_ndjson.encode("utf-8"))}
            elif kwargs.get("OutputFormat") == "pcm":
                return {"AudioStream": MockAudioStream(mock_pcm_bytes)}
            raise ValueError(f"Unexpected OutputFormat {kwargs.get('OutputFormat')}")

    monkeypatch.setattr(provider, "_get_client", lambda: MockPollyClient())

    clip = provider.synthesize("Draw a blue circle.", voice="Matthew")
    assert clip.provider == "polly"
    assert clip.voice == "Matthew"
    assert clip.duration == 2.0
    assert len(clip.words) == 4
    # Exact SpeechMark timestamps
    assert clip.get_word_time("Draw") == 0.1
    assert clip.get_word_time("blue") == 0.6
    assert clip.get_word_time("circle") == 0.95
