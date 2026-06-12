"""Tests for the TikZ rendering backend."""

import os
import subprocess

import pytest

from handanim.animations import FadeInAnimation, SketchAnimation
from handanim.core import FillStyle, Scene, SketchStyle, StrokeStyle
from handanim.core.draw_ops import Ops, OpsSet, OpsType
from handanim.core.tikz_renderer import TikZRenderer, opsset_to_tikz
from handanim.core.viewport import Viewport
from handanim.primitives import Circle, Line, NGon, Rectangle


@pytest.fixture
def viewport():
    return Viewport(world_xrange=(0, 1000), world_yrange=(0, 750))


@pytest.fixture
def renderer(viewport):
    return TikZRenderer(viewport, target_width_cm=10.0)


# ------------------------------------------------------------------ #
#  TikZRenderer unit tests
# ------------------------------------------------------------------ #

class TestCoordinateTransform:
    def test_origin_maps_to_bottom_left(self, renderer, viewport):
        tx, ty = renderer._transform(0, 750)
        assert abs(tx) < 0.001
        assert abs(ty) < 0.001

    def test_top_right_maps_to_top_right(self, renderer, viewport):
        tx, ty = renderer._transform(1000, 0)
        assert abs(tx - renderer.width_cm) < 0.001
        assert abs(ty - renderer.height_cm) < 0.001

    def test_y_is_flipped(self, renderer):
        _, y_top = renderer._transform(500, 0)
        _, y_bottom = renderer._transform(500, 750)
        assert y_top > y_bottom

    def test_aspect_ratio_preserved(self, renderer):
        assert abs(renderer.width_cm / renderer.height_cm - 1000 / 750) < 0.01


class TestColorCache:
    def test_same_color_reuses_name(self, renderer):
        n1 = renderer._get_color_name(1.0, 0.0, 0.0)
        n2 = renderer._get_color_name(1.0, 0.0, 0.0)
        assert n1 == n2

    def test_different_colors_get_different_names(self, renderer):
        n1 = renderer._get_color_name(1.0, 0.0, 0.0)
        n2 = renderer._get_color_name(0.0, 1.0, 0.0)
        assert n1 != n2

    def test_color_definitions_output(self, renderer):
        renderer._get_color_name(0.5, 0.5, 0.5)
        defs = renderer._color_definitions()
        assert len(defs) == 1
        assert "\\definecolor" in defs[0]
        assert "0.5,0.5,0.5" in defs[0]

    def test_reset_clears_cache(self, renderer):
        renderer._get_color_name(1.0, 0.0, 0.0)
        renderer.reset_colors()
        assert len(renderer._color_cache) == 0


class TestRenderOpsset:
    def test_empty_opsset(self, renderer):
        opsset = OpsSet([])
        cmds = renderer.render_opsset(opsset)
        assert cmds == []

    def test_line(self, renderer):
        ops = OpsSet([
            Ops(OpsType.SET_PEN, {"color": (0, 0, 0), "width": 1, "opacity": 1}),
            Ops(OpsType.MOVE_TO, [(100, 100)]),
            Ops(OpsType.LINE_TO, [(200, 200)]),
        ])
        cmds = renderer.render_opsset(ops)
        assert len(cmds) == 1
        assert "\\draw" in cmds[0]
        assert "--" in cmds[0]

    def test_curve(self, renderer):
        ops = OpsSet([
            Ops(OpsType.SET_PEN, {"color": (0, 0, 0), "width": 1, "opacity": 1}),
            Ops(OpsType.MOVE_TO, [(0, 0)]),
            Ops(OpsType.CURVE_TO, [(100, 0), (200, 100), (300, 100)]),
        ])
        cmds = renderer.render_opsset(ops)
        assert len(cmds) == 1
        assert "controls" in cmds[0]

    def test_closed_path(self, renderer):
        ops = OpsSet([
            Ops(OpsType.SET_PEN, {"color": (0, 0, 0), "width": 1, "opacity": 1}),
            Ops(OpsType.MOVE_TO, [(0, 0)]),
            Ops(OpsType.LINE_TO, [(100, 0)]),
            Ops(OpsType.LINE_TO, [(100, 100)]),
            Ops(OpsType.CLOSE_PATH, []),
        ])
        cmds = renderer.render_opsset(ops)
        assert "cycle" in cmds[0]

    def test_fill_mode(self, renderer):
        ops = OpsSet([
            Ops(OpsType.SET_PEN, {"color": (1, 0, 0), "width": 1, "opacity": 1, "mode": "fill"}),
            Ops(OpsType.MOVE_TO, [(0, 0)]),
            Ops(OpsType.LINE_TO, [(100, 0)]),
            Ops(OpsType.LINE_TO, [(50, 50)]),
            Ops(OpsType.CLOSE_PATH, []),
        ])
        cmds = renderer.render_opsset(ops)
        assert "\\fill" in cmds[0]

    def test_opacity_in_output(self, renderer):
        ops = OpsSet([
            Ops(OpsType.SET_PEN, {"color": (0, 0, 0), "width": 1, "opacity": 0.5}),
            Ops(OpsType.MOVE_TO, [(0, 0)]),
            Ops(OpsType.LINE_TO, [(100, 100)]),
        ])
        cmds = renderer.render_opsset(ops)
        assert "opacity=0.5" in cmds[0]

    def test_full_opacity_omitted(self, renderer):
        ops = OpsSet([
            Ops(OpsType.SET_PEN, {"color": (0, 0, 0), "width": 1, "opacity": 1.0}),
            Ops(OpsType.MOVE_TO, [(0, 0)]),
            Ops(OpsType.LINE_TO, [(100, 100)]),
        ])
        cmds = renderer.render_opsset(ops)
        assert "opacity" not in cmds[0]

    def test_dot(self, renderer):
        ops = OpsSet([
            Ops(OpsType.SET_PEN, {"color": (1, 0, 0), "width": 1, "opacity": 1}),
            Ops(OpsType.DOT, {"center": (500, 375), "radius": 5}),
        ])
        cmds = renderer.render_opsset(ops)
        assert any("circle" in c for c in cmds)

    def test_multiple_pen_changes(self, renderer):
        ops = OpsSet([
            Ops(OpsType.SET_PEN, {"color": (1, 0, 0), "width": 1, "opacity": 1}),
            Ops(OpsType.MOVE_TO, [(0, 0)]),
            Ops(OpsType.LINE_TO, [(100, 0)]),
            Ops(OpsType.SET_PEN, {"color": (0, 0, 1), "width": 2, "opacity": 1}),
            Ops(OpsType.MOVE_TO, [(200, 0)]),
            Ops(OpsType.LINE_TO, [(300, 0)]),
        ])
        cmds = renderer.render_opsset(ops)
        assert len(cmds) == 2

    def test_partial_line(self, renderer):
        ops = OpsSet([
            Ops(OpsType.SET_PEN, {"color": (0, 0, 0), "width": 1, "opacity": 1}),
            Ops(OpsType.MOVE_TO, [(0, 0)]),
            Ops(OpsType.LINE_TO, [(100, 0)], partial=0.5),
        ])
        cmds = renderer.render_opsset(ops)
        assert len(cmds) == 1
        # endpoint should be at ~(50, 0) in world coords
        assert "\\draw" in cmds[0]

    def test_metadata_ignored(self, renderer):
        ops = OpsSet([
            Ops(OpsType.SET_PEN, {"color": (0, 0, 0), "width": 1, "opacity": 1}),
            Ops(OpsType.METADATA, {"drawing_mode": "fill"}),
            Ops(OpsType.MOVE_TO, [(0, 0)]),
            Ops(OpsType.LINE_TO, [(100, 100)]),
        ])
        cmds = renderer.render_opsset(ops)
        assert len(cmds) == 1
        assert "metadata" not in cmds[0].lower()


class TestTikzpicture:
    def test_contains_begin_end(self, renderer):
        ops = OpsSet([
            Ops(OpsType.SET_PEN, {"color": (0, 0, 0), "width": 1, "opacity": 1}),
            Ops(OpsType.MOVE_TO, [(0, 0)]),
            Ops(OpsType.LINE_TO, [(100, 100)]),
        ])
        result = renderer.render_tikzpicture(ops)
        assert result.startswith("\\begin{tikzpicture}")
        assert result.endswith("\\end{tikzpicture}")

    def test_has_bounding_box(self, renderer):
        ops = OpsSet([])
        result = renderer.render_tikzpicture(ops)
        assert "\\useasboundingbox" in result

    def test_background_fill(self, viewport):
        renderer = TikZRenderer(viewport, background_color=(1.0, 1.0, 1.0))
        result = renderer.render_tikzpicture(OpsSet([]))
        assert "\\fill" in result
        assert "rectangle" in result

    def test_no_background_when_none(self, renderer):
        result = renderer.render_tikzpicture(OpsSet([]))
        lines = result.splitlines()
        fill_lines = [l for l in lines if "\\fill" in l]
        assert len(fill_lines) == 0


class TestConvenienceFunction:
    def test_opsset_to_tikz(self, viewport):
        ops = OpsSet([
            Ops(OpsType.SET_PEN, {"color": (0, 0, 0), "width": 1, "opacity": 1}),
            Ops(OpsType.MOVE_TO, [(50, 50)]),
            Ops(OpsType.LINE_TO, [(100, 100)]),
        ])
        result = opsset_to_tikz(ops, viewport)
        assert "\\begin{tikzpicture}" in result
        assert "\\draw" in result


# ------------------------------------------------------------------ #
#  Scene integration tests
# ------------------------------------------------------------------ #

class TestSceneRenderTikz:
    def test_render_tikz_creates_file(self, tmp_path):
        scene = Scene(width=400, height=300)
        r = Rectangle(top_left=(100, 100), width=200, height=100)
        scene.add(SketchAnimation(start_time=0, duration=1), drawable=r)
        out = scene.render_tikz(str(tmp_path / "out.tex"), time=0.5)
        assert os.path.exists(out)

    def test_render_tikz_standalone_structure(self, tmp_path):
        scene = Scene(width=400, height=300)
        r = Rectangle(top_left=(100, 100), width=200, height=100)
        scene.add(SketchAnimation(start_time=0, duration=1), drawable=r)
        out = scene.render_tikz(str(tmp_path / "out.tex"), time=1.0)
        with open(out) as f:
            content = f.read()
        assert "\\documentclass" in content
        assert "\\usepackage{tikz}" in content
        assert "\\begin{document}" in content
        assert "\\begin{tikzpicture}" in content

    def test_render_tikz_target_width(self, tmp_path):
        scene = Scene(width=400, height=300)
        r = Rectangle(top_left=(100, 100), width=200, height=100)
        scene.add(SketchAnimation(start_time=0, duration=1), drawable=r)
        out = scene.render_tikz(str(tmp_path / "out.tex"), time=1.0, target_width_cm=8.0)
        with open(out) as f:
            content = f.read()
        assert "8" in content


class TestExportBeamerTikz:
    def test_tikz_backend_produces_tex(self, tmp_path):
        scene = Scene(width=400, height=300)
        r = Rectangle(top_left=(100, 100), width=200, height=100)
        scene.add(SketchAnimation(start_time=0, duration=1), drawable=r)
        tex = scene.export_beamer(str(tmp_path), n_frames=3, backend="tikz")
        assert os.path.exists(tex)

    def test_tikz_backend_no_pdf_files(self, tmp_path):
        scene = Scene(width=400, height=300)
        r = Rectangle(top_left=(100, 100), width=200, height=100)
        scene.add(SketchAnimation(start_time=0, duration=1), drawable=r)
        scene.export_beamer(str(tmp_path), n_frames=3, backend="tikz")
        pdf_files = [f for f in os.listdir(str(tmp_path)) if f.endswith(".pdf")]
        assert len(pdf_files) == 0

    def test_tikz_backend_has_overlays(self, tmp_path):
        scene = Scene(width=400, height=300)
        r = Rectangle(top_left=(100, 100), width=200, height=100)
        scene.add(SketchAnimation(start_time=0, duration=1), drawable=r)
        tex = scene.export_beamer(str(tmp_path), n_frames=4, backend="tikz")
        with open(tex) as f:
            content = f.read()
        for i in range(1, 5):
            assert f"\\only<{i}>" in content
        assert "\\begin{tikzpicture}" in content
        assert "\\includegraphics" not in content

    def test_tikz_backend_uses_tikz_package(self, tmp_path):
        scene = Scene(width=400, height=300)
        r = Rectangle(top_left=(100, 100), width=200, height=100)
        scene.add(SketchAnimation(start_time=0, duration=1), drawable=r)
        tex = scene.export_beamer(str(tmp_path), n_frames=2, backend="tikz")
        with open(tex) as f:
            content = f.read()
        assert "\\usepackage{tikz}" in content
        assert "\\usepackage{graphicx}" not in content

    def test_cairo_backend_still_works(self, tmp_path):
        scene = Scene(width=400, height=300)
        r = Rectangle(top_left=(100, 100), width=200, height=100)
        scene.add(SketchAnimation(start_time=0, duration=1), drawable=r)
        tex = scene.export_beamer(str(tmp_path), n_frames=3, backend="cairo")
        with open(tex) as f:
            content = f.read()
        assert "\\includegraphics" in content
        pdf_files = [f for f in os.listdir(str(tmp_path)) if f.endswith(".pdf")]
        assert len(pdf_files) == 3

    def test_default_backend_is_cairo(self, tmp_path):
        scene = Scene(width=400, height=300)
        r = Rectangle(top_left=(100, 100), width=200, height=100)
        scene.add(SketchAnimation(start_time=0, duration=1), drawable=r)
        tex = scene.export_beamer(str(tmp_path), n_frames=2)
        with open(tex) as f:
            content = f.read()
        assert "\\includegraphics" in content


class TestTikzCompilation:
    """These tests require pdflatex. Skip if not installed."""

    @pytest.fixture(autouse=True)
    def check_pdflatex(self):
        result = subprocess.run(["pdflatex", "--version"], capture_output=True)
        if result.returncode != 0:
            pytest.skip("pdflatex not available")

    def test_standalone_compiles(self, tmp_path):
        scene = Scene(width=400, height=300)
        r = Rectangle(top_left=(100, 100), width=200, height=100)
        scene.add(SketchAnimation(start_time=0, duration=1), drawable=r)
        tex = scene.render_tikz(str(tmp_path / "test.tex"), time=1.0)
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(tmp_path), tex],
            capture_output=True, timeout=30,
        )
        assert result.returncode == 0
        assert (tmp_path / "test.pdf").exists()

    def test_beamer_tikz_compiles(self, tmp_path):
        scene = Scene(width=400, height=300)
        l = Line(start=(50, 50), end=(350, 50))
        r = Rectangle(top_left=(100, 100), width=200, height=100)
        scene.add(SketchAnimation(start_time=0, duration=1), drawable=l)
        scene.add(SketchAnimation(start_time=1, duration=1), drawable=r)
        tex = scene.export_beamer(str(tmp_path), n_frames=3, backend="tikz", title="Test")
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(tmp_path), tex],
            capture_output=True, timeout=30,
        )
        assert result.returncode == 0
        assert (tmp_path / "slides.pdf").exists()
