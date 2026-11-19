"""Tests for Phase 5 & Phase 6 storytelling, beat timeline, plotting, emphasis, morph, character, and studio features."""

from __future__ import annotations

from pathlib import Path

import pytest

from handanim import (
    Axes,
    BackgroundGrid,
    BarChart,
    CalloutBubble,
    Captions,
    CharacterRig,
    Circle,
    CountdownTimer,
    CrossOut,
    CurlyBrace,
    CustomTimeDrawable,
    FunctionGraph,
    HighlightMarker,
    Line,
    LineChart,
    MorphAnimation,
    NumberLine,
    PageTurnTransition,
    Pose,
    ProgressBar,
    Rectangle,
    RigNode,
    Scene,
    Show,
    SketchAnimation,
    Square,
    StrokeStyle,
    Text,
    TwoJointLimb,
    VariantSlot,
)
from handanim.core.viewport import Viewport
from handanim.stylings.color import BLACK, BLUE, GREEN, ORANGE, RED, YELLOW
from voiceanim import (
    AudioClip,
    DialogueTurn,
    SpeakerProfile,
    VoiceEngine,
    WordTimestamp,
    latex_to_speech,
    synthesize_dialogue,
)


def test_latex_to_speech():
    assert "e to the i pi" in latex_to_speech("Euler's formula is $e^{i\\pi} + 1 = 0$.")
    assert "integral from 0 to pi of sine" in latex_to_speech(r"\int_0^\pi \sin(x) dx")
    assert "one half" in latex_to_speech(r"\frac{1}{2}")
    assert "a over b" in latex_to_speech(r"\frac{a}{b}")
    assert "square root of x" in latex_to_speech(r"\sqrt{x}")
    assert "sum from i equals 1 to n" in latex_to_speech(r"\sum_{i=1}^{n} x_i^2")
    assert "big O of" in latex_to_speech(r"$O(n \log n)$")

    clip = VoiceEngine.synthesize(
        "The loss is $\\frac{1}{2} x^2$.",
        provider="mock",
        preprocess_math=True,
    )
    assert clip.duration > 0.0
    words_lower = [w.word.lower().strip(".,") for w in clip.words]
    assert "half" in words_lower
    assert "squared" in words_lower


def test_multi_voice_dialogue_and_captions():
    clip = synthesize_dialogue(
        turns=[
            DialogueTurn(speaker="student", text="Wait, why does size 100 fail?"),
            ("professor", "Because 1 outlier shifts the mean by 50 percent!"),
        ],
        speakers={
            "student": SpeakerProfile(name="student", voice="am_adam", provider="mock", color=BLUE, highlight=ORANGE),
            "professor": SpeakerProfile(name="professor", voice="af_heart", provider="mock", color=BLACK, highlight=RED),
        },
        default_provider="mock",
        pause_between=0.2,
    )
    assert clip.duration > 0.5
    assert any(w.speaker == "student" for w in clip.words)
    assert any(w.speaker == "professor" for w in clip.words)
    assert len(clip.sentences) == 2

    captions = Captions(
        clip,
        words_per_chunk=3,
        secondary_highlight=GREEN,
        highlight_numbers=True,
        background_color=(0.95, 0.95, 0.95),
    )
    # Verify chunks never mix speakers
    for idx, grp in enumerate(captions._group_words_respecting_speakers()):
        speakers_in_chunk = {cw.speaker for cw in grp}
        assert len(speakers_in_chunk) == 1, f"Chunk {idx} mixed speakers: {speakers_in_chunk}"

    ops = captions.draw_at_time(clip.words[0].start + 0.01)
    assert len(ops.opsset) > 0


def test_scene_beat_context_manager_and_word_triggers(tmp_path: Path):
    clip1 = AudioClip(
        audio_path="",
        duration=2.0,
        text="First we draw a circle.",
        words=[
            WordTimestamp("First", 0.0, 0.4),
            WordTimestamp("we", 0.4, 0.7),
            WordTimestamp("draw", 0.7, 1.1),
            WordTimestamp("a", 1.1, 1.3),
            WordTimestamp("circle", 1.3, 1.9),
        ],
    )
    clip2 = AudioClip(
        audio_path="",
        duration=2.5,
        text="Then a square appears.",
        words=[
            WordTimestamp("Then", 0.0, 0.5),
            WordTimestamp("a", 0.5, 0.7),
            WordTimestamp("square", 0.7, 1.4),
            WordTimestamp("appears", 1.4, 2.3),
        ],
    )

    scene = Scene(width=360, height=640, fps=15)
    c = Circle(center=(280, 300), radius=45)
    temp_lbl = Text("Temporary label", position=(280, 200), align="center")
    sq = Square(top_left=(220, 420), side_length=90)

    with scene.beat("Hook", narration=clip1, pad_after=0.5) as b1:
        assert b1.start == 0.0
        t_circle = b1.t("circle", lead_in=0.1)
        assert abs(t_circle - 1.2) < 1e-4
        b1.sketch(c, word="circle", lead_in=0.1, duration=0.6)
        b1.fade_in(temp_lbl, at=0.2, duration=0.4, clear_on_exit=True)

    with scene.beat("Body", narration=clip2, pad_after=0.3) as b2:
        # b1 ended at max(2.0, ...) + 0.35 fade cleanup + 0.5 pad_after = 2.85
        assert b2.start > 2.0
        b2.sketch(sq, word="square", duration=0.8)

    assert len(scene.beats) == 2
    stitched = scene.get_stitched_narration()
    assert stitched is not None
    assert len(stitched.words) == 9
    captions = scene.add_beat_captions(words_per_chunk=3)
    assert captions is not None

    # Verify temporary label was active during Beat 1 and deactivated before Beat 2's square
    assert temp_lbl.id in scene.get_active_objects(1.0)
    assert temp_lbl.id not in scene.get_active_objects(b2.start + 0.5)

    snap_path = tmp_path / "beat_snap.png"
    scene.render_snapshot(str(snap_path), frame_in_seconds=b2.start + 1.0)
    assert snap_path.exists()


def test_plots_and_charts_primitives():
    nl = NumberLine(x_range=(-2.0, 2.0), length=300.0, position=(100.0, 500.0), label="x")
    p_zero = nl.n2p(0.0)
    assert abs(p_zero[0] - 250.0) < 1e-5
    assert abs(nl.p2n(p_zero) - 0.0) < 1e-5
    assert len(nl.draw().opsset) > 0

    axes = Axes(
        x_range=(-3.0, 3.0),
        y_range=(-1.0, 9.0),
        width=400.0,
        height=250.0,
        position=(80.0, 180.0),
        include_numbers=True,
        x_label="x",
        y_label="y",
    )
    fg = axes.plot(lambda x: x * x, color=BLUE)
    fg_dashed = axes.plot(lambda x: 2.0 * x + 1.0, color=RED, dashed=True)
    scatter = axes.plot_scatter([(-2, 4), (0, 0), (2, 4)], radius=5.0)
    assert isinstance(fg, FunctionGraph)
    assert len(axes.draw().opsset) > 0
    assert len(fg.draw().opsset) > 0
    assert len(fg_dashed.draw().opsset) > 0
    assert len(scatter.draw().opsset) > 0

    bar_chart = BarChart(
        values=[12, 28, 19, 35],
        labels=["A", "B", "C", "D"],
        title="Sample Group Means",
    )
    assert len(bar_chart.bar_drawables) == 4
    assert len(bar_chart.draw().opsset) > 0
    bx, by = bar_chart.get_bar_top(1)
    assert bx > 70.0 and by < 480.0

    line_chart = LineChart(
        values=[10, 15, 13, 25, 30],
        labels=["T1", "T2", "T3", "T4", "T5"],
        title="Trend Over Time",
    )
    assert len(line_chart.draw().opsset) > 0
    pt2 = line_chart.get_point(2)
    assert len(pt2) == 2


def test_emphasis_primitives_and_morph_animation():
    txt = Text("Key Term", position=(200.0, 200.0), font_size=36)
    hl_marker = HighlightMarker(txt, color=YELLOW, style="marker")
    hl_under = HighlightMarker(txt, color=RED, style="underline")
    brace = CurlyBrace(txt, direction="down", label="Important")
    bubble = CalloutBubble("Notice this outlier!", position=(180.0, 80.0), tail_target=txt)
    cross = CrossOut(txt, style="x", color=RED)

    assert len(hl_marker.draw().opsset) > 0
    assert len(hl_under.draw().opsset) > 0
    assert len(brace.draw().opsset) > 0
    assert len(bubble.draw().opsset) > 0
    assert len(cross.draw().opsset) > 0

    c = Circle(center=(250.0, 250.0), radius=50.0, stroke_style=StrokeStyle(color=BLUE, width=2.0))
    sq = Square(top_left=(200.0, 200.0), side_length=100.0, stroke_style=StrokeStyle(color=RED, width=4.0))
    morph = MorphAnimation(target_drawable=sq, start_time=1.0, duration=1.0)

    c_ops = c.draw()
    mid_ops = morph.apply(c_ops, 0.5)
    end_ops = morph.apply(c_ops, 1.0)
    assert len(mid_ops.opsset) > 0
    assert len(end_ops.opsset) == len(sq.draw().opsset)


def test_character_auto_lipsync_and_point_at():
    mouth_slot = VariantSlot(
        "mouth",
        variants={
            "neutral": Line(start=(95, 105), end=(105, 105)),
            "open": Circle(center=(100, 105), radius=5),
            "smile": Line(start=(93, 104), end=(107, 104)),
        },
        default="neutral",
        pivot=(100, 105),
    )
    eye_slot = VariantSlot(
        "eyes",
        variants={
            "open": Circle(center=(100, 90), radius=4),
            "blink": Line(start=(96, 90), end=(104, 90)),
        },
        default="open",
        pivot=(100, 90),
    )
    eye_slot.add_periodic_switch(0.0, 5.0, pulse_variant="blink", period=2.0, pulse_duration=0.1)
    assert len(eye_slot.schedule) >= 3

    head = RigNode("head", pivot=(100, 100), children=[mouth_slot, eye_slot])
    forearm = RigNode("forearm_r", pivot=(130, 130), drawables=[Line(start=(130, 130), end=(160, 130))])
    upper_arm = RigNode("upper_arm_r", pivot=(100, 130), drawables=[Line(start=(100, 130), end=(130, 130))], children=[forearm])
    root = RigNode("torso", pivot=(100, 150), children=[head, upper_arm])
    limb = TwoJointLimb(name="right_arm", upper_node="upper_arm_r", lower_node="forearm_r", effector_pos=(160, 130))
    rig = CharacterRig(root=root, limbs=[limb], rest_pose=Pose())

    scene = Scene(width=360, height=640, fps=15)
    scene.add(Show(0.0), rig)

    target_box = Rectangle(top_left=(140, 90), width=40, height=40)
    point_anim = rig.point_at(scene, target_box, start_time=0.2, duration=0.4, hold=0.5)
    assert point_anim.duration > 0.8

    clip = AudioClip(
        audio_path="",
        duration=1.2,
        text="Hello world",
        words=[WordTimestamp("Hello", 0.1, 0.5), WordTimestamp("world", 0.6, 1.1)],
    )
    lip_anim = rig.sync_to_audio(scene, clip, start_time=1.5)
    assert lip_anim.duration == pytest.approx(1.2)
    assert mouth_slot.get_active_variant_name(time=1.6) in ("open", "neutral")


def test_introspect_overlaps_safe_zones_contact_sheet_and_background_overlays(tmp_path: Path):
    grid = BackgroundGrid(style="grid", spacing=60.0)
    timer = CountdownTimer(duration=10.0, position=(500.0, 48.0), style="both")
    pbar = ProgressBar(duration=10.0, position=(40.0, 965.0), width=480.0)
    custom_bg = CustomTimeDrawable(
        lambda t, p: Circle(center=(100.0 + 50.0 * p, 100.0), radius=15.0),
        duration=10.0,
    )

    vp = Viewport(
        world_xrange=(0.0, 562.5),
        world_yrange=(0.0, 1000.0),
        screen_width=360,
        screen_height=640,
        margin=20,
    )
    scene = Scene(width=360, height=640, fps=15, viewport=vp)
    scene.background.add(Show(0.0), grid)
    scene.background.add(custom_bg)
    scene.overlay.add(timer)
    scene.overlay.add(pbar)

    # Place two overlapping Text labels at the same position + one label in the bottom Shorts UI zone
    t1 = Text("Overlap Label One", position=(280.0, 400.0), font_size=36, align="center")
    t2 = Text("Overlap Label Two", position=(280.0, 405.0), font_size=36, align="center")
    t_bottom = Text("Too Low For Shorts UI", position=(280.0, 920.0), font_size=32, align="center")

    scene.add(SketchAnimation(start_time=0.0, duration=1.0), t1)
    scene.add(SketchAnimation(start_time=0.0, duration=1.0), t2)
    scene.add(SketchAnimation(start_time=0.0, duration=1.0), t_bottom)
    scene.add(PageTurnTransition(start_time=2.0, duration=0.5))

    # Background and overlay objects survive page-turn transitions while world objects before t=2.0 are cleared
    active_after_turn = scene.get_active_objects(3.0)
    assert grid.id in active_after_turn
    assert timer.id in active_after_turn
    assert t1.id not in active_after_turn

    report = scene.introspect(safe_zone="youtube_shorts", check_overlaps=True)
    assert len(report["overlaps"]) >= 1
    assert any(v["zone"] == "bottom_ui" for v in report["safe_zone_violations"])

    sheet_path = tmp_path / "sheet.png"
    scene.render_contact_sheet(str(sheet_path), timestamps=[0.2, 2.8], cols=2, safe_zone="youtube_shorts")
    assert sheet_path.exists()
