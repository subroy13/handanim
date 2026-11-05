"""Unit test for Scene.render with voiceanim narration."""

from handanim import Circle, Scene, SketchAnimation
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

