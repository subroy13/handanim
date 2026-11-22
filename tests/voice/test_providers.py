"""Unit tests for voiceanim TTS providers (Kokoro, Polly, Qwen, Mock)."""

import io
from pathlib import Path

import numpy as np
import pytest

from voiceanim import (
    KOKORO_ALL_VOICES,
    KOKORO_BLEND_PRESETS,
    KOKORO_VOICE_CATALOG,
    VoiceEngine,
)
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
    voices = provider.list_voices()
    assert len(voices) == 54
    assert len(KOKORO_ALL_VOICES) == 54
    assert "af_heart" in voices
    assert "am_adam" in voices
    assert "am_fenrir" in voices
    assert "am_puck" in voices
    assert "bm_fable" in voices
    assert "hm_omega" in voices
    assert "zf_xiaobei" in voices

    # Category filtering and blend presets
    am_voices = provider.list_voices(category="american_male")
    assert len(am_voices) == 9
    assert "am_fenrir" in am_voices
    assert "af_heart" not in am_voices

    with_blends = provider.list_voices(include_blends=True)
    assert len(with_blends) == 54 + len(KOKORO_BLEND_PRESETS)
    assert "blend_transatlantic" in with_blends

    with pytest.raises(ValueError, match="Unknown Kokoro voice category"):
        provider.list_voices(category="klingon")

    clip = provider.synthesize("Whiteboard animation with Kokoro voice.", voice="am_adam")
    assert clip.provider == "kokoro"
    assert clip.voice == "am_adam"
    assert Path(clip.audio_path).exists()
    assert len(clip.words) == 5


def test_kokoro_voice_blending_and_mocked_engine(monkeypatch, tmp_path):
    cache = AudioCache(cache_dir=tmp_path)
    provider = KokoroProvider(cache=cache, fallback_to_mock=True)

    # 1. Verify parsing of various blend syntax forms
    assert KokoroProvider.parse_voice_spec("am_puck:0.6+bm_fable:0.4") == [
        ("am_puck", pytest.approx(0.6)),
        ("bm_fable", pytest.approx(0.4)),
    ]
    assert KokoroProvider.parse_voice_spec("am_puck:60,bm_fable:40") == [
        ("am_puck", pytest.approx(0.6)),
        ("bm_fable", pytest.approx(0.4)),
    ]
    assert KokoroProvider.parse_voice_spec("am_fenrir+am_onyx") == [
        ("am_fenrir", pytest.approx(0.5)),
        ("am_onyx", pytest.approx(0.5)),
    ]
    assert KokoroProvider.parse_voice_spec({"hm_omega": 0.55, "am_liam": 0.45}) == [
        ("hm_omega", pytest.approx(0.55)),
        ("am_liam", pytest.approx(0.45)),
    ]
    assert KokoroProvider.parse_voice_spec("blend_transatlantic") == [
        ("am_puck", pytest.approx(0.6)),
        ("bm_fable", pytest.approx(0.4)),
    ]

    with pytest.raises(ValueError, match="Unknown Kokoro voice"):
        KokoroProvider.parse_voice_spec("nonexistent_voice:0.5+am_adam:0.5")

    with pytest.raises(ValueError, match="must be positive"):
        KokoroProvider.parse_voice_spec("am_puck:0+bm_fable:1")

    # 2. Language inference from dominant voice
    assert KokoroProvider.infer_language("am_puck:0.6+bm_fable:0.4") == "en-us"
    assert KokoroProvider.infer_language("am_puck:0.3+bm_fable:0.7") == "en-gb"
    assert KokoroProvider.infer_language("hm_omega:0.55+am_liam:0.45") == "en-us"
    assert KokoroProvider.infer_language("hm_omega", native_non_english=True) == "hi"

    # 3. Verify linear combination of (510, 1, 256) style tensors on a mocked engine
    style_puck = np.full((510, 1, 256), 2.0, dtype=np.float32)
    style_fable = np.full((510, 1, 256), 12.0, dtype=np.float32)
    captured_calls: list[dict] = []

    class DummyKokoroEngine:
        voices = {v: np.ones((510, 1, 256), dtype=np.float32) for v in KOKORO_ALL_VOICES}
        voices["am_puck"] = style_puck
        voices["bm_fable"] = style_fable

        def get_voice_style(self, name: str) -> np.ndarray:
            return self.voices[name]

        def create(self, text: str, voice, speed: float = 1.0, lang: str = "en-us"):
            captured_calls.append({"text": text, "voice": voice, "speed": speed, "lang": lang})
            return np.zeros(24000, dtype=np.float32), 24000

    monkeypatch.setattr(provider, "_get_engine", lambda: DummyKokoroEngine())

    blended_vec = provider.blend_voices("am_puck:0.6+bm_fable:0.4")
    assert blended_vec.shape == (510, 1, 256)
    assert blended_vec.dtype == np.float32
    # 0.6 * 2.0 + 0.4 * 12.0 = 1.2 + 4.8 = 6.0
    assert np.allclose(blended_vec, 6.0)

    clip = provider.synthesize(
        "Testing blended voice synthesis.",
        voice={"am_puck": 0.6, "bm_fable": 0.4},
    )
    assert clip.voice == "am_puck:0.6+bm_fable:0.4"
    assert clip.metadata["lang"] == "en-us"
    assert clip.metadata["blend_components"] == [
        {"voice": "am_puck", "weight": 0.6},
        {"voice": "bm_fable", "weight": 0.4},
    ]
    assert len(captured_calls) == 1
    assert isinstance(captured_calls[0]["voice"], np.ndarray)
    assert np.allclose(captured_calls[0]["voice"], 6.0)

    # VoiceEngine facade convenience methods
    assert len(VoiceEngine.list_voices("kokoro")) == 54
    assert len(VoiceEngine.list_voices("kokoro", category="british_female")) == len(
        KOKORO_VOICE_CATALOG["british_female"]
    )


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


def test_chatterbox_and_zonos_providers_and_aliases(tmp_path):
    from voiceanim import ChatterboxProvider, NarrationBeat, ZonosProvider

    assert isinstance(get_provider("chatterbox"), ChatterboxProvider)
    assert isinstance(get_provider("chatterbox-turbo"), ChatterboxProvider)
    assert isinstance(get_provider("zonos"), ZonosProvider)
    assert isinstance(get_provider("zonos3"), ZonosProvider)
    assert isinstance(get_provider("zonos3-mini"), ZonosProvider)

    cache = AudioCache(cache_dir=tmp_path)

    cb = ChatterboxProvider(cache=cache, backend="torch", fallback_to_mock=True)
    clip_cb = cb.synthesize(
        "Ninety-nine percent? No, much smaller!",
        voice="energetic",
        instruct="Incredulous question, then punchy playful reveal",
    )
    assert clip_cb.provider == "chatterbox"
    assert clip_cb.instruct == "Incredulous question, then punchy playful reveal"
    assert clip_cb.metadata["exaggeration"] > 0.85
    assert clip_cb.metadata["cfg_weight"] <= 0.42
    assert Path(clip_cb.audio_path).exists()
    assert len(clip_cb.words) == 5

    zn = ZonosProvider(cache=cache, backend="torch", fallback_to_mock=True)
    clip_zn = zn.synthesize(
        "Ninety-nine percent? No, much smaller!",
        voice="jett",
        instruct="Excited dramatic reveal with playful energy",
    )
    assert clip_zn.provider == "zonos"
    assert clip_zn.metadata["controls"]["delivery.emotion"] >= 2.2
    assert clip_zn.metadata["controls"]["delivery.liveliness"] >= 1.6
    assert Path(clip_zn.audio_path).exists()
    assert len(clip_zn.words) == 5

    # Per-beat direction specs via VoiceEngine.synthesize_beats
    beats = VoiceEngine.synthesize_beats(
        [
            ("hook", "What is the chance it is spam?", "Curious, upbeat hook"),
            ("answer", "Ninety-nine percent? No, much smaller!", "Incredulous, punchy reveal"),
            NarrationBeat(id="outro", text="Let's see why.", instruct="Warm, inviting"),
        ],
        provider="chatterbox",
        output_dir=tmp_path / "beats",
        cache=cache,
        backend="torch",
        fallback_to_mock=True,
    )
    assert len(beats) == 3
    assert beats[1].instruct == "Incredulous, punchy reveal"
    assert beats[1].clip is not None
    assert Path(beats[1].clip.audio_path).name == "answer.wav"


def test_forced_aligner_energy_and_clip_alignment(tmp_path):
    from voiceanim import ForcedAligner, align_clip
    from voiceanim.providers.base import BaseVoiceProvider

    # Build a synthetic WAV with two speech bursts separated by a 0.6s silence pause
    sr = 24000
    t_burst1 = np.linspace(0.0, 0.5, int(0.5 * sr), endpoint=False)
    burst1 = (0.4 * np.sin(2.0 * np.pi * 220.0 * t_burst1)).astype(np.float32)
    silence = np.zeros(int(0.6 * sr), dtype=np.float32)
    t_burst2 = np.linspace(0.0, 0.7, int(0.7 * sr), endpoint=False)
    burst2 = (0.4 * np.sin(2.0 * np.pi * 260.0 * t_burst2)).astype(np.float32)
    samples = np.concatenate([burst1, silence, burst2])

    wav_path = tmp_path / "two_bursts.wav"
    BaseVoiceProvider.write_wav(wav_path, samples, sample_rate=sr)

    aligner = ForcedAligner(backend="energy")
    words, used = aligner.align(wav_path, "Ninety-nine percent? No, much smaller!")
    assert used == "energy"
    assert len(words) == 5
    # First word starts near 0.0, last word lands inside second burst (> 1.1s)
    assert words[0].start < 0.1
    assert words[-1].end > 1.3

    # Verify align_clip updates an AudioClip in place
    cache = AudioCache(cache_dir=tmp_path / "cache")
    clip = MockVoiceProvider(cache=cache).synthesize("Hello world!")
    aligned = align_clip(clip, backend="energy")
    assert aligned.metadata["alignment_backend"] == "energy"
    assert len(aligned.words) == 2
