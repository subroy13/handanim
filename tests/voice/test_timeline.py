"""Unit tests for VoiceTimelineSync."""

from handanim import Circle, SketchAnimation
from voiceanim.providers import MockVoiceProvider
from voiceanim.schema import NarrationBeat
from voiceanim.timeline import VoiceTimelineSync


def test_sync_event_to_word(tmp_path):
    provider = MockVoiceProvider()
    clip = provider.synthesize("Next, we sketch a circle on the canvas.")

    circle = Circle(center=(100, 100), radius=30)
    event, target = VoiceTimelineSync.sync_event_to_word(
        clip=clip,
        word="circle",
        event_cls=SketchAnimation,
        drawable=circle,
        duration=1.2,
        lead_in=0.1,
    )

    assert target is circle
    assert isinstance(event, SketchAnimation)
    assert event.duration == 1.2
    # The start_time should be slightly before the word "circle"
    circle_word_start = clip.get_word_time("circle")
    assert circle_word_start is not None
    assert abs(event.start_time - max(0.0, circle_word_start - 0.1)) < 1e-4


def test_validate_beat_fit():
    provider = MockVoiceProvider()
    c1 = provider.synthesize("A very short beat.")  # ~1.5s
    c2 = provider.synthesize("This is a much longer explanation of complex geometry that takes more time.")  # ~4.5s

    beats = [
        NarrationBeat(id="b1", text="A very short beat.", target_duration=5.0, clip=c1),
        NarrationBeat(id="b2", text="...", target_duration=1.0, clip=c2),  # Overflows!
    ]

    warnings = VoiceTimelineSync.validate_beat_fit(beats)
    assert len(warnings) == 1
    assert "b2" in warnings[0]
    assert "exceeds visual slot" in warnings[0]


def test_stitch_narration_beats(tmp_path):
    provider = MockVoiceProvider()
    c1 = provider.synthesize("Beat one.", output_path=tmp_path / "c1.wav")
    c2 = provider.synthesize("Beat two.", output_path=tmp_path / "c2.wav")

    beats = [
        NarrationBeat(id="1", text="Beat one.", start_time=0.5, clip=c1),
        NarrationBeat(id="2", text="Beat two.", start_time=4.0, clip=c2),
    ]

    out_wav = tmp_path / "combined.wav"
    unified_clip = VoiceTimelineSync.stitch_narration_beats(beats, out_wav, total_duration=7.0)

    assert unified_clip.duration == 7.0
    assert out_wav.exists()
    assert len(unified_clip.words) == 4
    # The second beat's words should have their timestamps shifted by start_time=4.0
    second_beat_first_word = [w for w in unified_clip.words if "two" in w.word.lower()][0]
    assert second_beat_first_word.start >= 4.0

