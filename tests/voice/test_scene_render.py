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


def test_sketch_animation_sound_on_off_and_volume_controls():
    import pytest

    # 1. Scene has sketch_sound=True, but one SketchAnimation disables sound, and another lowers volume
    scene = Scene(width=320, height=240, fps=10, sketch_sound=True, sketch_sound_volume=0.30)
    c1 = Circle(center=(80, 120), radius=30)
    c2 = Circle(center=(160, 120), radius=30)
    c3 = Circle(center=(240, 120), radius=30)

    scene.add(SketchAnimation(start_time=0.0, duration=0.5, sound=False), c1)
    scene.add(SketchAnimation(start_time=1.0, duration=0.5, sound_volume=0.12, sound_style="pen"), c2)
    scene.add(SketchAnimation(start_time=2.0, duration=0.5), c3)

    sfx = scene.extract_auto_sfx_events()
    assert len(sfx) == 2
    assert sfx[0]["start_time"] == pytest.approx(1.0)
    assert sfx[0]["volume"] == pytest.approx(0.12)
    assert sfx[0]["style"] == "pen"
    assert sfx[1]["start_time"] == pytest.approx(2.0)
    assert sfx[1]["volume"] == pytest.approx(0.30)
    assert sfx[1]["style"] == "chalk"

    # 2. Master mute via disable_sketch_sound() or include_sketch=False
    scene.disable_sketch_sound()
    # Even when scene.sketch_sound is False, c2 had explicit sound_volume=0.12 unless master-muted via include_sketch=False
    sfx_explicit_only = scene.extract_auto_sfx_events()
    assert len(sfx_explicit_only) == 1
    assert sfx_explicit_only[0]["start_time"] == pytest.approx(1.0)

    # Master mute via include_sketch=False (as in scene.render(..., sketch_sound=False)) silences all sketch sounds
    assert scene.extract_auto_sfx_events(include_sketch=False) == []
    assert scene.extract_auto_sfx_events(sketch_volume=0.0) == []

    # 3. Shorthand float volume in set_sketch_sound / enable_sketch_sound
    scene.set_sketch_sound(0.15, style="pen")
    assert scene.sketch_sound is True
    assert scene.sketch_sound_volume == pytest.approx(0.15)
    assert scene.sketch_sound_style == "pen"

    scene.set_sketch_sound(0.0)
    assert scene.sketch_sound is False

    # 4. Per-animation set_sound helper & float shorthand
    anim = SketchAnimation(start_time=0.0, duration=1.0, sound=0.18)
    assert anim.sound is True
    assert anim.sound_volume == pytest.approx(0.18)
    anim.set_sound(False)
    assert anim.sound is False



