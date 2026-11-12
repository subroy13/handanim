"""Unit test for Scene.render with voiceanim narration, background music, and auto chalk/eraser SFX."""

from handanim import Circle, Eraser, Line, Scene, SketchAnimation
from voiceanim.providers import MockVoiceProvider


def test_scene_render_with_narration(tmp_path):
    scene = Scene(width=320, height=240, fps=10)
    circle = Circle(center=(160, 120), radius=40)
    scene.add(SketchAnimation(start_time=0.0, duration=0.5), circle)

    provider = MockVoiceProvider()
    narration_clip = provider.synthesize("Drawing a circle.", output_path=tmp_path / "voice.wav")

    output_video = tmp_path / "scene_with_audio.mp4"
    res = scene.render(str(output_video), narration=narration_clip)

    assert str(output_video) == res
    assert output_video.exists()
    assert output_video.stat().st_size > 0


def test_scene_extract_auto_sfx_and_render_with_music_chalk_and_eraser(tmp_path):
    scene = Scene(
        width=320,
        height=240,
        fps=10,
        background_music="marimba",
        sketch_sound=True,
        eraser_sound=True,
    )
    line = Line(start=(40, 120), end=(280, 120))
    eraser = Eraser(objects_to_erase=[line])

    scene.add(SketchAnimation(start_time=0.0, duration=0.4), line)
    scene.add(SketchAnimation(start_time=0.5, duration=0.4), eraser)

    sfx = scene.extract_auto_sfx_events()
    assert len(sfx) == 2
    assert sfx[0]["type"] == "chalk"
    assert sfx[0]["start_time"] == 0.0
    assert sfx[0]["duration"] == 0.4
    assert sfx[1]["type"] == "eraser"
    assert sfx[1]["start_time"] == 0.5
    assert sfx[1]["duration"] == 0.4

    out_mp4 = tmp_path / "scene_full_soundtrack.mp4"
    res = scene.render(str(out_mp4), max_length=1.0)
    assert res == str(out_mp4)
    assert out_mp4.exists()
    assert out_mp4.stat().st_size > 0


