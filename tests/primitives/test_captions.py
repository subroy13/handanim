from __future__ import annotations

import numpy as np

from handanim import (
    CameraAnimation,
    Captions,
    Line,
    Scene,
    Show,
    SketchStyle,
    StrokeStyle,
)
from handanim.core.draw_ops import OpsType
from handanim.stylings.color import BLACK, BLUE, RED
from voiceanim.schema import AudioClip, WordTimestamp

FLAT = SketchStyle(roughness=0, bowing=0)


def _sample_clip() -> AudioClip:
    words = [
        WordTimestamp(word="Hello", start=0.1, end=0.4),
        WordTimestamp(word="world", start=0.45, end=0.8),
        WordTimestamp(word="from", start=0.85, end=1.1),
        WordTimestamp(word="handanim", start=1.3, end=1.7),
        WordTimestamp(word="shorts", start=1.75, end=2.1),
    ]
    return AudioClip(
        audio_path="dummy.wav",
        duration=2.3,
        words=words,
        text="Hello world from handanim shorts",
    )


def _pen_colors(opsset) -> list[tuple[float, float, float]]:
    return [
        tuple(op.data["color"])
        for op in opsset.opsset
        if op.type == OpsType.SET_PEN and isinstance(op.data, dict) and "color" in op.data
    ]


class TestCaptions:
    def test_chunks_and_active_word_highlighting(self):
        clip = _sample_clip()
        captions = Captions(clip, words_per_chunk=3, highlight=RED, color=BLACK, y=1590, x=540)

        # Before first word (t=0.0): empty
        assert len(captions.draw_at_time(0.0).opsset) == 0

        # During "Hello" (t=0.25): chunk 0 active; word 0 RED, words 1 & 2 BLACK
        ops_w0 = captions.draw_at_time(0.25)
        assert _pen_colors(ops_w0) == [RED, BLACK, BLACK]

        # During "world" (t=0.6): chunk 0 active; word 1 RED, words 0 & 2 BLACK
        ops_w1 = captions.draw_at_time(0.6)
        assert _pen_colors(ops_w1) == [BLACK, RED, BLACK]

        # During "handanim" (t=1.5): chunk 1 active (2 words); word 0 RED, word 1 BLACK
        ops_chunk1 = captions.draw_at_time(1.5)
        assert _pen_colors(ops_chunk1) == [RED, BLACK]

        # After clip ends (t=2.25): empty
        assert len(captions.draw_at_time(2.25).opsset) == 0

    def test_captions_adds_single_event_to_scene_overlay(self):
        clip = _sample_clip()
        scene = Scene(width=360, height=640, fps=10)
        scene.set_viewport_to_identity()
        captions = Captions(clip, words_per_chunk=3, highlight=RED, y=520)

        scene.overlay.add(captions)

        assert len(scene.events) == 1
        assert captions.id in scene.overlay_drawable_ids

        frames = scene.create_event_timeline(max_length=2.3)
        # Frame at t=0.6s (index 6) should have overlay ops with RED highlight on word 2
        frame_6 = frames[6]
        assert len(frame_6.opsset) > 0
        assert all(op.meta and op.meta.get("overlay") is True for op in frame_6.opsset)
        assert _pen_colors(frame_6) == [BLACK, RED, BLACK]

    def test_overlay_ignores_camera_animation(self, tmp_path):
        scene = Scene(width=200, height=200, fps=10)
        scene.set_viewport_to_identity()

        # Draw a blue world line and a red overlay line
        world_line = Line((20, 50), (80, 50), stroke_style=StrokeStyle(color=BLUE, width=4), sketch_style=FLAT)
        overlay_line = Line((20, 150), (80, 150), stroke_style=StrokeStyle(color=RED, width=4), sketch_style=FLAT)

        scene.add(Show(0.0), world_line)
        scene.overlay.add(Show(0.0), overlay_line)

        # Pan the camera strongly right by +500 units from t=0 to t=1.0
        scene.add_camera(
            CameraAnimation(
                start_time=0.0,
                duration=1.0,
                data={
                    "to_xrange": (500, 700),
                    "to_yrange": (0, 200),
                },
            )
        )

        opsset_list = scene.create_event_timeline(max_length=1.0)
        png_t0 = str(tmp_path / "f0.png")
        png_t1 = str(tmp_path / "f1.png")
        scene._render_frame(opsset_list[0], png_t0, 0.0)
        scene._render_frame(opsset_list[-1], png_t1, 1.0)

        import imageio.v2 as imageio

        img0 = imageio.imread(png_t0)
        img1 = imageio.imread(png_t1)

        # At y=150 (overlay line), the red pixels at x=50 must remain identical between t=0 and t=1
        assert np.allclose(img0[150, 50, :3], img1[150, 50, :3])
        assert img1[150, 50, 0] > 200 and img1[150, 50, 2] < 50  # still RED

        # At y=50 (world line), the blue line at x=50 was panned off-screen at t=1 (now white background)
        assert img0[50, 50, 2] > 200 and img0[50, 50, 0] < 50  # BLUE at t=0
        assert img1[50, 50, 0] > 240 and img1[50, 50, 1] > 240 and img1[50, 50, 2] > 240  # WHITE at t=1

    def test_captions_auto_scales_wide_chunks_to_max_width(self):
        words = [
            WordTimestamp(word="Supercalifragilistic", start=0.0, end=0.5),
            WordTimestamp(word="expialidocious", start=0.5, end=1.0),
            WordTimestamp(word="extraordinary", start=1.0, end=1.5),
        ]
        clip = AudioClip(audio_path="dummy.wav", duration=1.6, words=words, text=" ".join(w.word for w in words))

        unscaled = Captions(clip, words_per_chunk=3, font_size=64, max_width=None, x=540, y=1590)
        scaled = Captions(clip, words_per_chunk=3, font_size=64, max_width=300.0, x=540, y=1590)

        unscaled_bbox = unscaled.draw_at_time(0.2).get_bbox()
        scaled_bbox = scaled.draw_at_time(0.2).get_bbox()

        assert unscaled_bbox.width > 300.0
        assert scaled_bbox.width <= 305.0

    def test_captions_supports_prechunked_json_format(self):
        raw_chunks = [
            {
                "s": 0.1,
                "e": 0.9,
                "words": [
                    {"d": "Order", "s": 0.1, "e": 0.4},
                    {"d": "smart.", "s": 0.45, "e": 0.9},
                ],
            },
            {
                "s": 1.0,
                "e": 1.8,
                "words": [
                    {"d": "Eat", "s": 1.0, "e": 1.3},
                    {"d": "protein", "s": 1.35, "e": 1.6},
                    {"d": "first.", "s": 1.62, "e": 1.8},
                ],
            },
        ]
        captions = Captions(raw_chunks, highlight=RED, color=BLACK, x=540, y=1590)
        assert len(captions.chunks) == 2
        assert _pen_colors(captions.draw_at_time(0.2)) == [RED, BLACK]
        assert _pen_colors(captions.draw_at_time(1.45)) == [BLACK, RED, BLACK]

