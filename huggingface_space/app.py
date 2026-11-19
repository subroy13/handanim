"""Hugging Face Space Gradio App for HandAnim (`handanim` + `voiceanim`).

Zero-install interactive browser studio for rendering hand-drawn whiteboard
animations with 54-voice Kokoro-82M neural TTS, 256-D latent voice blending,
procedural chalk/eraser sound effects, word-synced captions, 2D character IK,
and native LaTeX Beamer/TikZ slide export.
"""

from __future__ import annotations

from pathlib import Path
import tempfile

from handanim import (
    BLACK,
    BLUE,
    ERASER_HINT_COLOR,
    NAVY,
    PASTEL_BLUE,
    PASTEL_GREEN,
    PASTEL_ORANGE,
    PASTEL_YELLOW,
    RED,
    CameraAnimation,
    Captions,
    CharacterRig,
    Circle,
    Eraser,
    FillStyle,
    Flowchart,
    Line,
    Math,
    MoveBy,
    Polygon,
    Pose,
    PoseAnimation,
    Scene,
    Show,
    SketchAnimation,
    SketchStyle,
    StrokeStyle,
    Text,
)
from voiceanim import (
    KOKORO_ALL_VOICES,
    KOKORO_BLEND_PRESETS,
    VoiceEngine,
    VoiceTimelineSync,
)

FEATURED_VOICE_CHOICES: list[tuple[str, str]] = [
    ("🌟 blend_transatlantic (60% am_puck + 40% bm_fable)", "blend_transatlantic"),
    ("🌟 blend_professor (55% am_fenrir + 45% am_onyx)", "blend_professor"),
    ("🌟 blend_storyteller (60% bm_fable + 40% am_liam)", "blend_storyteller"),
    ("🌟 blend_host_female (60% af_aoede + 40% af_kore)", "blend_host_female"),
    ("🌟 blend_indian_male (55% hm_omega + 45% am_liam)", "blend_indian_male"),
    ("🌟 blend_indian_female (55% hf_alpha + 45% af_aoede)", "blend_indian_female"),
    ("🎙️ am_fenrir (Energetic American Male)", "am_fenrir"),
    ("🎙️ am_puck (Crisp American Male STEM Explainer)", "am_puck"),
    ("🎙️ am_liam (Warm American Male Narrator)", "am_liam"),
    ("🎙️ am_onyx (Deep American Male Documentary)", "am_onyx"),
    ("🎙️ bm_fable (Expressive British Male Storyteller)", "bm_fable"),
    ("🎙️ bm_daniel (Crisp British Male Presenter)", "bm_daniel"),
    ("🎙️ af_aoede (Natural American Female Host)", "af_aoede"),
    ("🎙️ af_kore (Clear American Female Educator)", "af_kore"),
    ("🎙️ af_heart (Warm American Female Default)", "af_heart"),
    ("🎙️ bf_lily (Articulate British Female)", "bf_lily"),
    ("🔇 None (Chalk/Eraser SFX & Music Only)", "none"),
]

_featured_ids = {v_id for _, v_id in FEATURED_VOICE_CHOICES}
for _v in KOKORO_ALL_VOICES:
    if _v not in _featured_ids:
        FEATURED_VOICE_CHOICES.append((f"Voice: {_v}", _v))


def _synthesize_safe(
    text: str,
    voice_id: str,
    speed: float,
    out_wav: Path,
):
    """Synthesize speech with Kokoro-82M, falling back gracefully to MockVoiceProvider if offline."""
    try:
        provider = VoiceEngine.get_provider("kokoro", fallback_to_mock=True)
        return provider.synthesize(
            text=text,
            voice=voice_id,
            speed=speed,
            output_path=out_wav,
        )
    except Exception:
        provider = VoiceEngine.get_provider("mock")
        return provider.synthesize(
            text=text,
            voice="mock_narrator",
            speed=speed,
            output_path=out_wav,
        )


def build_custom_whiteboard(
    title_text: str,
    latex_formula: str,
    flowchart_steps: str,
    narration_text: str,
    voice_choice: str,
    custom_blend: str,
    speed: float,
    bg_music: str,
    enable_sfx: bool,
    enable_captions: bool,
) -> tuple[str, str, str]:
    """Render a custom whiteboard scene from form inputs and return `(mp4_path, python_code, tikz_code)`."""
    work_dir = Path(tempfile.mkdtemp(prefix="handanim_space_"))
    active_voice = (custom_blend or "").strip() or voice_choice
    music_arg = None if bg_music == "none" else bg_music

    clip = None
    total_dur = 4.5
    if active_voice != "none" and narration_text.strip():
        clip = _synthesize_safe(
            text=narration_text.strip(),
            voice_id=active_voice,
            speed=float(speed),
            out_wav=work_dir / "voice.wav",
        )
        total_dur = max(3.5, round(clip.duration + 0.6, 2))

    scene = Scene(
        width=960,
        height=540,
        fps=24,
        audio=clip,
        background_music=music_arg,
        sketch_sound=bool(enable_sfx),
    )

    cursor = 0.0
    if title_text.strip():
        title_obj = Text(
            text=title_text.strip(),
            position=(480, 62),
            font_size=44,
            stroke_style=StrokeStyle(color=NAVY, width=2.4),
        )
        scene.add(SketchAnimation(start_time=0.0, duration=0.9), drawable=title_obj)
        cursor = 0.7

    if latex_formula.strip():
        clean_expr = latex_formula.strip().strip("$").strip()
        expr = f"${clean_expr}$"
        math_obj = Math(
            tex_expression=expr,
            position=(140, 145),
            font_size=64,
            stroke_style=StrokeStyle(color=BLUE, width=2.6),
        )
        scene.add(SketchAnimation(start_time=cursor, duration=1.2), drawable=math_obj)
        cursor += 1.0

    steps = [s.strip() for s in flowchart_steps.split(",") if s.strip()][:4]
    if steps:
        palette = [PASTEL_BLUE, PASTEL_ORANGE, PASTEL_GREEN, PASTEL_YELLOW]
        n = len(steps)
        xs = [int(180 + i * (600 / max(1, n - 1))) for i in range(n)] if n > 1 else [480]
        nodes = [
            {
                "id": f"n{i}",
                "label": label,
                "position": [xs[i], 345],
                "size": [max(160, min(220, int(680 / n))), 70],
                "font_size": 24,
                "fill_style": FillStyle(color=palette[i % len(palette)]),
            }
            for i, label in enumerate(steps)
        ]
        edges = [
            {"from": f"n{i}", "to": f"n{i + 1}", "from_side": "right", "to_side": "left"}
            for i in range(n - 1)
        ]
        flow = Flowchart.from_dict({"nodes": nodes, "edges": edges})
        flow_dur = max(1.0, min(2.2, total_dur - cursor - 0.5))
        scene.add(SketchAnimation(start_time=cursor, duration=flow_dur), drawable=flow)

    if clip is not None and enable_captions:
        captions = Captions.from_audio_clip(clip, position=(480, 475), font_size=30)
        scene.overlay.add(captions.create_animation(), drawable=captions)

    mp4_path = str(work_dir / "custom_whiteboard.mp4")
    scene.render(mp4_path, max_length=total_dur)

    tex_path = scene.export_beamer(
        str(work_dir / "slides"),
        n_frames=4,
        backend="tikz",
        title=title_text.strip() or "HandAnim Slide",
        max_length=total_dur,
    )
    tikz_code = Path(tex_path).read_text(encoding="utf-8")

    clean_display = latex_formula.strip().strip("$").strip()
    expr_display = f"${clean_display}$" if clean_display else ""

    python_code = f'''from handanim import (
    BLUE, NAVY, PASTEL_BLUE, PASTEL_GREEN, PASTEL_ORANGE,
    Captions, FillStyle, Flowchart, Math, Scene, SketchAnimation, StrokeStyle, Text,
)
from voiceanim import VoiceEngine

clip = VoiceEngine.synthesize(
    {narration_text.strip()!r},
    voice={active_voice!r},
    speed={round(float(speed), 2)},
)

scene = Scene(
    width=960,
    height=540,
    fps=24,
    audio=clip,
    background_music={music_arg!r},
    sketch_sound={bool(enable_sfx)},
)

title = Text({title_text.strip()!r}, position=(480, 62), font_size=44, stroke_style=StrokeStyle(color=NAVY, width=2.4))
formula = Math(r{expr_display!r}, position=(140, 145), font_size=64, stroke_style=StrokeStyle(color=BLUE, width=2.6))
scene.add(SketchAnimation(start_time=0.0, duration=0.9), drawable=title)
scene.add(SketchAnimation(start_time=0.7, duration=1.2), drawable=formula)
'''
    if steps:
        python_code += f"""
flow = Flowchart.from_dict({{"nodes": {[{'id': f'n{i}', 'label': s, 'position': [180 + i * 260, 345], 'size': [190, 70]} for i, s in enumerate(steps)]!r}, "edges": {[{'from': f'n{i}', 'to': f'n{i+1}', 'from_side': 'right', 'to_side': 'left'} for i in range(len(steps)-1)]!r}}})
scene.add(SketchAnimation(start_time=1.7, duration=1.5), drawable=flow)
"""
    if enable_captions:
        python_code += """
captions = Captions.from_audio_clip(clip, position=(480, 475), font_size=30)
scene.overlay.add(captions.create_animation(), drawable=captions)
"""
    python_code += """
scene.render("whiteboard.mp4")
scene.export_beamer("slides/", n_frames=4, backend="tikz")
"""
    return mp4_path, python_code, tikz_code


def render_preset_demo(
    preset_name: str,
    voice_choice: str,
    bg_music: str,
) -> tuple[str, str, str]:
    """Render one of the 4 built-in showcase presets and return `(mp4_path, python_code, tikz_code)`."""
    work_dir = Path(tempfile.mkdtemp(prefix="handanim_preset_"))
    music_arg = None if bg_music == "none" else bg_music
    active_voice = "blend_transatlantic" if voice_choice == "none" else voice_choice

    if preset_name.startswith("1."):
        scene = Scene(width=960, height=540, fps=24, sketch_sound=True, background_music=music_arg)
        formula = Math(
            r"$y = \sigma(Wx + b)$",
            position=(80, 70),
            font_size=64,
            stroke_style=StrokeStyle(color=BLUE, width=2.5),
        )
        draft = Text(
            "Draft: linear only?",
            position=(80, 215),
            font_size=36,
            stroke_style=StrokeStyle(color=RED, width=2),
        )
        flow = Flowchart.from_dict(
            {
                "nodes": [
                    {
                        "id": "x",
                        "label": "Input x",
                        "position": [220, 390],
                        "size": [190, 74],
                        "font_size": 28,
                        "fill_style": FillStyle(color=PASTEL_BLUE),
                    },
                    {
                        "id": "h",
                        "label": "Hidden Wx+b",
                        "position": [540, 390],
                        "size": [230, 74],
                        "font_size": 28,
                        "fill_style": FillStyle(color=PASTEL_ORANGE),
                    },
                    {
                        "id": "y",
                        "label": "Output y",
                        "position": [860, 390],
                        "size": [190, 74],
                        "font_size": 28,
                        "fill_style": FillStyle(color=PASTEL_GREEN),
                    },
                ],
                "edges": [
                    {"from": "x", "to": "h", "from_side": "right", "to_side": "left"},
                    {"from": "h", "to": "y", "from_side": "right", "to_side": "left"},
                ],
            }
        )
        eraser = Eraser(
            objects_to_erase=[draft],
            drawable_cache=scene.drawable_cache,
            glow_dot_hint={"color": ERASER_HINT_COLOR, "radius": 8},
        )
        fixed = Text(
            "Non-linear activation!",
            position=(80, 215),
            font_size=38,
            stroke_style=StrokeStyle(color=NAVY, width=2.2),
        )
        scene.add(SketchAnimation(start_time=0.0, duration=1.1), drawable=formula)
        scene.add(SketchAnimation(start_time=0.6, duration=0.8), drawable=draft)
        scene.add(SketchAnimation(start_time=1.4, duration=1.5), drawable=flow)
        scene.add(SketchAnimation(start_time=2.9, duration=0.8), drawable=eraser)
        scene.add(SketchAnimation(start_time=3.7, duration=0.6), drawable=fixed)
        scene.add(
            CameraAnimation(
                start_time=3.6,
                duration=1.2,
                data={"to_xrange": (120, 1080), "to_yrange": (40, 580)},
            )
        )
        max_len = 5.0
        py_code = """from handanim import (
    BLUE, ERASER_HINT_COLOR, NAVY, PASTEL_BLUE, PASTEL_GREEN, PASTEL_ORANGE, RED,
    CameraAnimation, Eraser, FillStyle, Flowchart, Math, Scene, SketchAnimation, StrokeStyle, Text,
)

scene = Scene(width=960, height=540, fps=24, sketch_sound=True, background_music="calm")
formula = Math(r"$y = \\sigma(Wx + b)$", position=(80, 70), font_size=64, stroke_style=StrokeStyle(color=BLUE, width=2.5))
draft = Text("Draft: linear only?", position=(80, 215), font_size=36, stroke_style=StrokeStyle(color=RED, width=2))
flow = Flowchart.from_dict({
    "nodes": [
        {"id": "x", "label": "Input x", "position": [220, 390], "size": [190, 74], "font_size": 28, "fill_style": FillStyle(color=PASTEL_BLUE)},
        {"id": "h", "label": "Hidden Wx+b", "position": [540, 390], "size": [230, 74], "font_size": 28, "fill_style": FillStyle(color=PASTEL_ORANGE)},
        {"id": "y", "label": "Output y", "position": [860, 390], "size": [190, 74], "font_size": 28, "fill_style": FillStyle(color=PASTEL_GREEN)},
    ],
    "edges": [
        {"from": "x", "to": "h", "from_side": "right", "to_side": "left"},
        {"from": "h", "to": "y", "from_side": "right", "to_side": "left"},
    ],
})
eraser = Eraser(objects_to_erase=[draft], drawable_cache=scene.drawable_cache, glow_dot_hint={"color": ERASER_HINT_COLOR, "radius": 8})
fixed = Text("Non-linear activation!", position=(80, 215), font_size=38, stroke_style=StrokeStyle(color=NAVY, width=2.2))

scene.add(SketchAnimation(start_time=0.0, duration=1.1), drawable=formula)
scene.add(SketchAnimation(start_time=0.6, duration=0.8), drawable=draft)
scene.add(SketchAnimation(start_time=1.4, duration=1.5), drawable=flow)
scene.add(SketchAnimation(start_time=2.9, duration=0.8), drawable=eraser)
scene.add(SketchAnimation(start_time=3.7, duration=0.6), drawable=fixed)
scene.add(CameraAnimation(start_time=3.6, duration=1.2, data={"to_xrange": (120, 1080), "to_yrange": (40, 580)}))
scene.render("hero_showcase.mp4", max_length=5.0)
"""

    elif preset_name.startswith("2."):
        clip = _synthesize_safe(
            text="Euler's identity connects five fundamental mathematical constants in a single equation.",
            voice_id=active_voice,
            speed=1.0,
            out_wav=work_dir / "euler.wav",
        )
        sync = VoiceTimelineSync(clip)
        t_start, t_end = sync.word_range("Euler's", "equation.")
        scene = Scene(
            width=960,
            height=540,
            fps=24,
            audio=clip,
            background_music=music_arg,
            sketch_sound=True,
        )
        title = Text("Euler's Identity", position=(480, 80), font_size=48, stroke_style=StrokeStyle(color=NAVY, width=2.5))
        eq = Math(r"$e^{i\pi} + 1 = 0$", position=(240, 195), font_size=84, stroke_style=StrokeStyle(color=BLUE, width=3.0))
        scene.add(SketchAnimation(start_time=0.0, duration=0.8), drawable=title)
        scene.add(SketchAnimation(start_time=t_start, duration=max(1.2, t_end - t_start)), drawable=eq)
        captions = Captions.from_audio_clip(clip, position=(480, 465), font_size=32)
        scene.overlay.add(captions.create_animation(), drawable=captions)
        max_len = max(3.5, round(clip.duration + 0.4, 2))
        py_code = f"""from handanim import BLUE, NAVY, Captions, Math, Scene, SketchAnimation, StrokeStyle, Text
from voiceanim import VoiceEngine, VoiceTimelineSync

clip = VoiceEngine.synthesize(
    "Euler's identity connects five fundamental mathematical constants in a single equation.",
    voice={active_voice!r},
)
sync = VoiceTimelineSync(clip)
t_start, t_end = sync.word_range("Euler's", "equation.")

scene = Scene(width=960, height=540, fps=24, audio=clip, background_music={music_arg!r}, sketch_sound=True)
scene.add(SketchAnimation(start_time=0.0, duration=0.8), Text("Euler's Identity", position=(480, 80), font_size=48, stroke_style=StrokeStyle(color=NAVY, width=2.5)))
scene.add(SketchAnimation(start_time=t_start, duration=max(1.2, t_end - t_start)), Math(r"$e^{{i\\pi}} + 1 = 0$", position=(240, 195), font_size=84, stroke_style=StrokeStyle(color=BLUE, width=3.0)))

captions = Captions.from_audio_clip(clip, position=(480, 465), font_size=32)
scene.overlay.add(captions.create_animation(), drawable=captions)
scene.render("euler_voiced.mp4")
"""

    elif preset_name.startswith("3."):
        rig = CharacterRig(pivot=(320, 330))
        torso = rig.root
        torso.drawables.append(Line((320, 220), (320, 330), stroke_style=StrokeStyle(color=BLACK, width=4)))
        torso.drawables.append(Line((320, 330), (285, 430), stroke_style=StrokeStyle(color=BLACK, width=4)))
        torso.drawables.append(Line((320, 330), (355, 430), stroke_style=StrokeStyle(color=BLACK, width=4)))
        head = torso.add_child(
            "head",
            pivot=(320, 220),
            drawables=[
                Circle(
                    center=(320, 175),
                    radius=36,
                    stroke_style=StrokeStyle(color=BLACK, width=3.5),
                    fill_style=FillStyle(color=PASTEL_BLUE, opacity=0.35),
                )
            ],
        )
        eyes = head.add_slot(
            "eyes",
            variants={
                "open": [Circle((308, 170), 4), Circle((332, 170), 4)],
                "blink": [Line((303, 170), (313, 170)), Line((327, 170), (337, 170))],
            },
        )
        eyes.set_schedule([(0.0, "open"), (1.1, "blink"), (1.28, "open"), (2.4, "blink"), (2.58, "open")])
        upper_r = torso.add_child(
            "upper_r",
            pivot=(325, 235),
            drawables=[Line((325, 235), (390, 235), stroke_style=StrokeStyle(color=BLUE, width=3.5))],
        )
        upper_r.add_child(
            "lower_r",
            pivot=(390, 235),
            drawables=[
                Line((390, 235), (455, 235), stroke_style=StrokeStyle(color=BLUE, width=3.5)),
                Circle((455, 235), 7, stroke_style=StrokeStyle(color=RED, width=3)),
            ],
        )
        rig.add_two_joint_limb(
            "right_arm",
            upper_node="upper_r",
            lower_node="lower_r",
            effector_pos=(455, 235),
            bend_direction=1,
        )

        scene = Scene(width=960, height=540, fps=24, background_music=music_arg, sketch_sound=True)
        board = Math(r"$a^2 + b^2 = c^2$", position=(520, 130), font_size=56, stroke_style=StrokeStyle(color=NAVY, width=2.5))
        scene.add(SketchAnimation(start_time=0.2, duration=1.4), drawable=board)
        scene.add(Show(0.0), drawable=rig)
        scene.add(
            PoseAnimation.from_keyframes(
                rig,
                [
                    (0.0, Pose(ik_targets={"right_arm": (440, 270)})),
                    (1.4, Pose(angles={"head": -8.0}, ik_targets={"right_arm": (520, 175)})),
                    (3.0, Pose(angles={"head": 5.0}, ik_targets={"right_arm": (620, 220)})),
                ],
            ),
            drawable=rig,
        )
        scene.add(MoveBy(dx=90, dy=0, start_time=1.4, duration=1.6), drawable=rig)
        max_len = 3.4
        py_code = """from handanim import (
    BLACK, BLUE, NAVY, PASTEL_BLUE, RED,
    CharacterRig, Circle, FillStyle, Line, Math, MoveBy, Pose, PoseAnimation, Scene, Show, SketchAnimation, StrokeStyle,
)

rig = CharacterRig(pivot=(320, 330))
torso = rig.root
torso.drawables.extend([
    Line((320, 220), (320, 330), stroke_style=StrokeStyle(color=BLACK, width=4)),
    Line((320, 330), (285, 430), stroke_style=StrokeStyle(color=BLACK, width=4)),
    Line((320, 330), (355, 430), stroke_style=StrokeStyle(color=BLACK, width=4)),
])
head = torso.add_child("head", pivot=(320, 220), drawables=[
    Circle((320, 175), 36, stroke_style=StrokeStyle(color=BLACK, width=3.5), fill_style=FillStyle(color=PASTEL_BLUE, opacity=0.35)),
])
eyes = head.add_slot("eyes", variants={
    "open": [Circle((308, 170), 4), Circle((332, 170), 4)],
    "blink": [Line((303, 170), (313, 170)), Line((327, 170), (337, 170))],
})
eyes.set_schedule([(0.0, "open"), (1.1, "blink"), (1.28, "open"), (2.4, "blink"), (2.58, "open")])

upper_r = torso.add_child("upper_r", pivot=(325, 235), drawables=[Line((325, 235), (390, 235), stroke_style=StrokeStyle(color=BLUE, width=3.5))])
upper_r.add_child("lower_r", pivot=(390, 235), drawables=[
    Line((390, 235), (455, 235), stroke_style=StrokeStyle(color=BLUE, width=3.5)),
    Circle((455, 235), 7, stroke_style=StrokeStyle(color=RED, width=3)),
])
rig.add_two_joint_limb("right_arm", "upper_r", "lower_r", effector=(455, 235), bend_direction=1)

scene = Scene(width=960, height=540, fps=24, sketch_sound=True)
scene.add(SketchAnimation(start_time=0.2, duration=1.4), Math(r"$a^2 + b^2 = c^2$", position=(520, 130), font_size=56))
scene.add(Show(0.0), drawable=rig)
scene.add(PoseAnimation.from_keyframes(rig, [
    (0.0, Pose(ik_targets={"right_arm": (440, 270)})),
    (1.4, Pose(angles={"head": -8.0}, ik_targets={"right_arm": (520, 175)})),
    (3.0, Pose(angles={"head": 5.0}, ik_targets={"right_arm": (620, 220)})),
]), drawable=rig)
scene.add(MoveBy(dx=90, dy=0, start_time=1.4, duration=1.6), drawable=rig)
scene.render("character_ik.mp4", max_length=3.4)
"""

    else:
        scene = Scene(width=960, height=540, fps=24, sketch_sound=True, background_music=music_arg)
        title = Text("Pythagoras' Theorem", position=(480, 220), font_size=68, stroke_style=StrokeStyle(color=BLUE, width=2.5))
        eraser = Eraser(
            objects_to_erase=[title],
            drawable_cache=scene.drawable_cache,
            glow_dot_hint={"color": ERASER_HINT_COLOR, "radius": 9},
        )
        tri = Polygon(
            points=[(220, 160), (220, 410), (540, 410)],
            stroke_style=StrokeStyle(color=BLACK, width=2.5),
            sketch_style=SketchStyle(roughness=3),
            fill_style=FillStyle(color=RED, hachure_gap=10),
        )
        eq = Math(r"$a^2 + b^2 = c^2$", position=(530, 210), font_size=64, stroke_style=StrokeStyle(color=BLUE, width=2.5))
        scene.add(SketchAnimation(start_time=0.0, duration=1.1), drawable=title)
        scene.add(SketchAnimation(start_time=1.3, duration=0.9), drawable=eraser)
        scene.add(SketchAnimation(start_time=2.3, duration=1.2), drawable=tri)
        scene.add(SketchAnimation(start_time=3.3, duration=1.1), drawable=eq)
        max_len = 4.8
        py_code = """from handanim import (
    BLACK, BLUE, ERASER_HINT_COLOR, RED,
    Eraser, FillStyle, Math, Polygon, Scene, SketchAnimation, SketchStyle, StrokeStyle, Text,
)

scene = Scene(width=960, height=540, fps=24, sketch_sound=True, background_music="calm")
title = Text("Pythagoras' Theorem", position=(480, 220), font_size=68, stroke_style=StrokeStyle(color=BLUE, width=2.5))
eraser = Eraser(objects_to_erase=[title], drawable_cache=scene.drawable_cache, glow_dot_hint={"color": ERASER_HINT_COLOR, "radius": 9})
tri = Polygon(points=[(220, 160), (220, 410), (540, 410)], stroke_style=StrokeStyle(color=BLACK, width=2.5), sketch_style=SketchStyle(roughness=3), fill_style=FillStyle(color=RED, hachure_gap=10))
eq = Math(r"$a^2 + b^2 = c^2$", position=(530, 210), font_size=64, stroke_style=StrokeStyle(color=BLUE, width=2.5))

scene.add(SketchAnimation(start_time=0.0, duration=1.1), drawable=title)
scene.add(SketchAnimation(start_time=1.3, duration=0.9), drawable=eraser)
scene.add(SketchAnimation(start_time=2.3, duration=1.2), drawable=tri)
scene.add(SketchAnimation(start_time=3.3, duration=1.1), drawable=eq)
scene.render("pythagoras.mp4", max_length=4.8)
"""

    mp4_path = str(work_dir / "preset_demo.mp4")
    scene.render(mp4_path, max_length=max_len)
    tex_path = scene.export_beamer(
        str(work_dir / "slides"),
        n_frames=4,
        backend="tikz",
        title="HandAnim Preset Deck",
        max_length=max_len,
    )
    tikz_code = Path(tex_path).read_text(encoding="utf-8")
    return mp4_path, py_code, tikz_code


def create_demo_app():
    import gradio as gr

    with gr.Blocks(title="HandAnim — Whiteboard Animation Studio") as demo:
        gr.Markdown(
            """
            # ✍️ HandAnim — Interactive Whiteboard Animation Studio
            **Programmatic whiteboard animation in Python** with **54-voice Kokoro-82M neural TTS & 256-D latent voice blending (`voiceanim`)**, **procedural chalk & eraser sound effects (-14 LUFS stereo)**, **2D character inverse kinematics**, and **1-line LaTeX Beamer/TikZ slide export (`export_beamer()`)**.

            📦 [`pip install "handanim[voice]"`](https://pypi.org/project/handanim/) &nbsp;|&nbsp; ⭐ [GitHub: `subroy13/handanim`](https://github.com/subroy13/handanim) &nbsp;|&nbsp; 🚀 [Full Python Playground on Google Colab](https://colab.research.google.com/github/subroy13/handanim/blob/master/notebooks/handanim_colab_playground.ipynb)
            """
        )

        with gr.Tabs():
            with gr.TabItem("🎨 1. Instant Voiced Whiteboard Builder"):
                with gr.Row():
                    with gr.Column(scale=5):
                        title_in = gr.Textbox(
                            label="Slide / Whiteboard Title",
                            value="How a Neural Layer Works",
                        )
                        latex_in = gr.Textbox(
                            label="Handwritten LaTeX Math Formula",
                            value=r"$y = \sigma(Wx + b)$",
                        )
                        flow_in = gr.Textbox(
                            label="Flowchart Nodes (comma-separated, up to 4 steps)",
                            value="Input x, Weights Wx+b, Activation y",
                        )
                        narration_in = gr.Textbox(
                            label="Voiceover Narration Script (Kokoro-82M Neural TTS)",
                            value="A neural layer multiplies inputs by weights, adds a bias, and applies a non-linear activation.",
                            lines=2,
                        )
                        voice_in = gr.Dropdown(
                            label="Voice / 256-D Latent Blend Preset (54 Built-In Voices)",
                            choices=FEATURED_VOICE_CHOICES,
                            value="blend_transatlantic",
                        )
                        custom_blend_in = gr.Textbox(
                            label="Optional Custom 256-D Voice Blend Override (e.g. am_puck:0.6+bm_fable:0.4 or hm_omega:0.55+am_liam:0.45)",
                            value="",
                            placeholder="Leave blank to use the dropdown selection above",
                        )
                        with gr.Row():
                            speed_in = gr.Slider(
                                label="Speech Speed",
                                minimum=0.75,
                                maximum=1.35,
                                step=0.05,
                                value=1.0,
                            )
                            music_in = gr.Dropdown(
                                label="Background Music (Auto-Ducked)",
                                choices=["calm", "marimba", "upbeat", "none"],
                                value="calm",
                            )
                        with gr.Row():
                            sfx_in = gr.Checkbox(label="Procedural Chalk & Eraser SFX", value=True)
                            captions_in = gr.Checkbox(label="Word-Synced Captions Overlay", value=True)

                        render_btn = gr.Button("🎬 Render Whiteboard MP4 + Python + TikZ Slides", variant="primary")

                    with gr.Column(scale=6):
                        video_out = gr.Video(label="Rendered Whiteboard Animation (.mp4 with -14 LUFS Stereo Audio)")
                        with gr.Accordion("🐍 Copy Generated Python Script", open=True):
                            py_out = gr.Code(language="python", label="Python Code")
                        with gr.Accordion("📄 Copy Generated LaTeX Beamer / TikZ Slide Deck (.tex)", open=False):
                            tikz_out = gr.Code(language="latex", label="LaTeX Beamer + Inline TikZ")

                render_btn.click(
                    fn=build_custom_whiteboard,
                    inputs=[
                        title_in,
                        latex_in,
                        flow_in,
                        narration_in,
                        voice_in,
                        custom_blend_in,
                        speed_in,
                        music_in,
                        sfx_in,
                        captions_in,
                    ],
                    outputs=[video_out, py_out, tikz_out],
                )

            with gr.TabItem("⚡ 2. One-Click Preset Showcase"):
                with gr.Row():
                    with gr.Column(scale=4):
                        preset_in = gr.Radio(
                            label="Choose a Built-In Showcase Scene",
                            choices=[
                                "1. Hero Showcase: LaTeX Math + Flowchart + Eraser + Camera Pan",
                                "2. Euler's Identity with Voiced Narration & Word-Synced Captions",
                                "3. 2D Character Rig with 2-Joint Inverse Kinematics & Auto-Blink",
                                "4. Pythagorean Theorem Visual Proof with Board Eraser",
                            ],
                            value="1. Hero Showcase: LaTeX Math + Flowchart + Eraser + Camera Pan",
                        )
                        preset_voice_in = gr.Dropdown(
                            label="Voice (used by voiced presets)",
                            choices=FEATURED_VOICE_CHOICES,
                            value="blend_transatlantic",
                        )
                        preset_music_in = gr.Dropdown(
                            label="Background Music",
                            choices=["calm", "marimba", "upbeat", "none"],
                            value="calm",
                        )
                        preset_btn = gr.Button("▶️ Render Preset Animation", variant="primary")

                    with gr.Column(scale=6):
                        preset_video_out = gr.Video(label="Preset Whiteboard Animation (.mp4)")
                        with gr.Accordion("🐍 Copy Preset Python Script", open=True):
                            preset_py_out = gr.Code(language="python", label="Python Code")
                        with gr.Accordion("📄 Copy Preset LaTeX Beamer / TikZ Deck (.tex)", open=False):
                            preset_tikz_out = gr.Code(language="latex", label="LaTeX Beamer + Inline TikZ")

                preset_btn.click(
                    fn=render_preset_demo,
                    inputs=[preset_in, preset_voice_in, preset_music_in],
                    outputs=[preset_video_out, preset_py_out, preset_tikz_out],
                )

    return demo


if __name__ == "__main__":
    app = create_demo_app()
    app.launch()
