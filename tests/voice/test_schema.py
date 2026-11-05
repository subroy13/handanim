"""Unit tests for voiceanim data models and schemas."""

import pytest

from voiceanim.schema import AudioClip, NarrationBeat, SentenceTimestamp, WordTimestamp


def test_word_timestamp():
    wt = WordTimestamp(word="circle", start=1.25, end=1.85)
    assert pytest.approx(wt.duration) == 0.6
    d = wt.to_dict()
    assert d["word"] == "circle"
    assert d["start"] == 1.25
    assert d["end"] == 1.85

    restored = WordTimestamp.from_dict(d)
    assert restored.word == "circle"
    assert restored.start == 1.25
    assert restored.end == 1.85


def test_sentence_timestamp():
    w1 = WordTimestamp(word="Draw", start=0.0, end=0.4)
    w2 = WordTimestamp(word="a", start=0.4, end=0.5)
    w3 = WordTimestamp(word="circle.", start=0.5, end=1.1)

    st = SentenceTimestamp(text="Draw a circle.", start=0.0, end=1.1, words=[w1, w2, w3])
    assert st.duration == 1.1
    assert len(st.words) == 3

    d = st.to_dict()
    restored = SentenceTimestamp.from_dict(d)
    assert restored.text == "Draw a circle."
    assert len(restored.words) == 3
    assert restored.words[2].word == "circle."


def test_audio_clip_word_lookup():
    words = [
        WordTimestamp(word="Let's", start=0.1, end=0.4),
        WordTimestamp(word="draw", start=0.4, end=0.8),
        WordTimestamp(word="a", start=0.8, end=0.9),
        WordTimestamp(word="circle,", start=0.9, end=1.5),
        WordTimestamp(word="and", start=1.5, end=1.7),
        WordTimestamp(word="another", start=1.7, end=2.1),
        WordTimestamp(word="circle.", start=2.1, end=2.7),
    ]

    clip = AudioClip(
        audio_path="dummy.wav",
        duration=3.0,
        sample_rate=24000,
        text="Let's draw a circle, and another circle.",
        words=words,
        provider="kokoro",
        voice="af_heart",
    )

    # First occurrence of "circle"
    assert clip.get_word_time("circle") == 0.9
    assert clip.get_word_range("circle") == (0.9, 1.5)

    # Second occurrence of "circle"
    assert clip.get_word_time("circle", occurrence=2) == 2.1
    assert clip.get_word_range("circle", occurrence=2) == (2.1, 2.7)

    # Third occurrence (nonexistent)
    assert clip.get_word_time("circle", occurrence=3) is None

    # Punctuation stripping and case insensitivity
    assert clip.get_word_time("DRAW") == 0.4
    assert clip.get_word_time("nonexistent") is None


def test_audio_clip_srt_vtt_export(tmp_path):
    words = [
        WordTimestamp(word="First", start=0.2, end=0.6),
        WordTimestamp(word="step.", start=0.6, end=1.2),
    ]
    sentences = [
        SentenceTimestamp(text="First step.", start=0.2, end=1.2, words=words)
    ]
    clip = AudioClip(
        audio_path="dummy.wav",
        duration=2.0,
        text="First step.",
        words=words,
        sentences=sentences,
    )

    srt = clip.export_srt()
    assert "00:00:00,200 --> 00:00:01,200" in srt
    assert "First step." in srt

    vtt = clip.export_vtt()
    assert "WEBVTT" in vtt
    assert "00:00:00.200 --> 00:00:01.200" in vtt

    # File export test
    srt_file = tmp_path / "subs.srt"
    clip.export_srt(srt_file)
    assert srt_file.exists()
    assert "First step." in srt_file.read_text()


def test_narration_beat():
    beat = NarrationBeat(id="scene_1", text="Welcome to whiteboard animation", target_duration=4.0)
    assert beat.id == "scene_1"
    assert beat.target_duration == 4.0
    assert beat.clip is None
