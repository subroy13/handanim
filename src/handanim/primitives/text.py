from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from svgelements import Close as SVGClose
from svgelements import CubicBezier as SVGCubicBezier
from svgelements import Line as SVGLine
from svgelements import Move as SVGMove
from svgelements import Path as SVGPath
from svgelements import QuadraticBezier as SVGQuadBezier

from ..core.draw_ops import BoundingBox, Ops, OpsSet, OpsType
from ..core.drawable import Drawable
from ..stylings.fonts import (
    BACKSTAY_PERSONAL_USE_WARNING,
    get_font_info,
    get_font_path,
    list_fonts,
)

# Normalize typographic quotes to ASCII when a font lacks curly-quote glyphs
_QUOTE_FALLBACK = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
}


def _fallback_symbol_svg_d(char: str, cap_h: float = 680.0) -> tuple[str, float] | None:
    """Return `(svg_path_d, advance_width)` in 1000-UPM Y-up font units for common symbols (₹, →, ×, ÷, ≈, –)."""
    h = float(cap_h)
    mid = 0.44 * h
    if char == "₹":
        # Official Udaya Kumar Indian Rupee open-stroke geometry (top bar, mid bar, bowl + leg)
        y_top = h
        y_bar = 0.72 * h
        y_waist = 0.44 * h
        d = (
            f"M 55 {y_top:.1f} L 495 {y_top:.1f} "
            f"M 55 {y_bar:.1f} L 495 {y_bar:.1f} "
            f"M 165 {y_top:.1f} C 405 {y_top:.1f} 420 {y_waist:.1f} 120 {y_waist:.1f} L 445 0"
        )
        return d, 560.0
    if char == "→":
        d = (
            f"M 50 {mid:.1f} L 530 {mid:.1f} "
            f"M 390 {mid + 0.22 * h:.1f} L 535 {mid:.1f} L 390 {mid - 0.22 * h:.1f}"
        )
        return d, 600.0
    if char == "←":
        d = (
            f"M 535 {mid:.1f} L 55 {mid:.1f} "
            f"M 195 {mid + 0.22 * h:.1f} L 50 {mid:.1f} L 195 {mid - 0.22 * h:.1f}"
        )
        return d, 600.0
    if char == "×":
        lo, hi = 0.22 * h, 0.68 * h
        return f"M 85 {lo:.1f} L 415 {hi:.1f} M 85 {hi:.1f} L 415 {lo:.1f}", 500.0
    if char == "÷":
        d = (
            f"M 70 {mid:.1f} L 430 {mid:.1f} "
            f"M 235 {mid + 0.22 * h:.1f} L 265 {mid + 0.22 * h:.1f} "
            f"M 235 {mid - 0.22 * h:.1f} L 265 {mid - 0.22 * h:.1f}"
        )
        return d, 500.0
    if char == "≈":
        y1, y2 = mid + 0.15 * h, mid - 0.15 * h
        d = (
            f"M 65 {y1:.1f} C 165 {y1 + 110:.1f} 315 {y1 - 110:.1f} 435 {y1:.1f} "
            f"M 65 {y2:.1f} C 165 {y2 + 110:.1f} 315 {y2 - 110:.1f} 435 {y2:.1f}"
        )
        return d, 510.0
    if char == "–":
        return f"M 55 {mid:.1f} L 445 {mid:.1f}", 500.0
    if char == "—":
        return f"M 40 {mid:.1f} L 680 {mid:.1f}", 720.0
    if char in ("·", "•"):
        r = 24.0 if char == "·" else 40.0
        cx, cy = 160.0, mid
        d = (
            f"M {cx - r:.1f} {cy:.1f} "
            f"C {cx - r:.1f} {cy + r:.1f} {cx + r:.1f} {cy + r:.1f} {cx + r:.1f} {cy:.1f} "
            f"C {cx + r:.1f} {cy - r:.1f} {cx - r:.1f} {cy - r:.1f} {cx - r:.1f} {cy:.1f}"
        )
        return d, 320.0
    return None


def _svg_d_to_opsset(d: str, scale: float, flip_y: bool = True) -> OpsSet:
    """Convert an SVG path `d` string into a scaled `OpsSet`."""
    ops = OpsSet(initial_set=[])
    if not d or not d.strip():
        return ops
    sy = -scale if flip_y else scale
    for seg in SVGPath(d).segments():
        if isinstance(seg, SVGMove) and seg.end is not None:
            ops.add(Ops(OpsType.MOVE_TO, [(seg.end.x * scale, seg.end.y * sy)]))
        elif isinstance(seg, SVGLine) and seg.end is not None:
            ops.add(Ops(OpsType.LINE_TO, [(seg.end.x * scale, seg.end.y * sy)]))
        elif isinstance(seg, SVGQuadBezier) and seg.control is not None and seg.end is not None:
            ops.add(
                Ops(
                    OpsType.QUAD_CURVE_TO,
                    [
                        (seg.control.x * scale, seg.control.y * sy),
                        (seg.end.x * scale, seg.end.y * sy),
                    ],
                )
            )
        elif (
            isinstance(seg, SVGCubicBezier)
            and seg.control1 is not None
            and seg.control2 is not None
            and seg.end is not None
        ):
            ops.add(
                Ops(
                    OpsType.CURVE_TO,
                    [
                        (seg.control1.x * scale, seg.control1.y * sy),
                        (seg.control2.x * scale, seg.control2.y * sy),
                        (seg.end.x * scale, seg.end.y * sy),
                    ],
                )
            )
        elif isinstance(seg, SVGClose):
            ops.add(Ops(OpsType.CLOSE_PATH, data={}))
    return ops


@dataclass(frozen=True)
class _SVGFontData:
    units_per_em: float
    default_adv: float
    space_adv: float
    cap_height: float
    glyphs: dict[str, tuple[str, float]]  # unicode_char -> (d, horiz_adv_x)
    kerning: dict[tuple[str, str], float]  # (char1, char2) -> kern_adjustment_units


@lru_cache(maxsize=32)
def _load_ttf(font_path: str) -> TTFont:
    return TTFont(font_path)


@lru_cache(maxsize=32)
def _load_svg_font(font_path: str) -> _SVGFontData:
    tree = ET.parse(font_path)
    root = tree.getroot()
    ns = {"s": "http://www.w3.org/2000/svg"}

    font_el = root.find(".//s:font", ns)
    if font_el is None:
        font_el = root.find(".//font")
    if font_el is None:
        raise ValueError(f"No <font> element found in SVG font: {font_path}")

    default_adv = float(font_el.attrib.get("horiz-adv-x", "500"))
    face_el = font_el.find("s:font-face", ns)
    if face_el is None:
        face_el = font_el.find("font-face")

    units_per_em = float(face_el.attrib.get("units-per-em", "1000")) if face_el is not None else 1000.0
    cap_height = float(face_el.attrib.get("cap-height", "680")) if face_el is not None else 680.0

    glyph_els = font_el.findall("s:glyph", ns) or font_el.findall("glyph")
    glyphs: dict[str, tuple[str, float]] = {}
    name_to_char: dict[str, str] = {}

    for g in glyph_els:
        uni = g.attrib.get("unicode")
        if not uni:
            continue
        adv = float(g.attrib.get("horiz-adv-x", str(default_adv)))
        d = g.attrib.get("d", "")
        # Prefer first single-char entry if duplicate glyph alternates exist
        if uni not in glyphs:
            glyphs[uni] = (d, adv)
        gname = g.attrib.get("glyph-name")
        if gname and len(uni) == 1 and gname not in name_to_char:
            name_to_char[gname] = uni

    space_adv = glyphs[" "][1] if " " in glyphs else default_adv * 0.6

    # Measure true visual cap height from 'H' or '8' if available (some EMS fonts declare 500 when caps reach 680)
    for probe in ("H", "8", "I"):
        if probe in glyphs and glyphs[probe][0]:
            probe_ops = _svg_d_to_opsset(glyphs[probe][0], 1.0, flip_y=False)
            if len(probe_ops.opsset) > 0:
                measured_h = probe_ops.get_bbox().max_y
                if measured_h > 200.0:
                    cap_height = float(measured_h)
                    break

    hkern_els = font_el.findall("s:hkern", ns) or font_el.findall("hkern")
    kerning: dict[tuple[str, str], float] = {}
    for hk in hkern_els:
        k_val = float(hk.attrib.get("k", "0"))
        if k_val == 0:
            continue
        lefts: list[str] = []
        rights: list[str] = []
        if "u1" in hk.attrib:
            lefts.extend(c for c in hk.attrib["u1"].split(",") if len(c) == 1)
        if "g1" in hk.attrib:
            lefts.extend(name_to_char[g] for g in hk.attrib["g1"].split(",") if g in name_to_char)
        if "u2" in hk.attrib:
            rights.extend(c for c in hk.attrib["u2"].split(",") if len(c) == 1)
        if "g2" in hk.attrib:
            rights.extend(name_to_char[g] for g in hk.attrib["g2"].split(",") if g in name_to_char)
        for c1 in lefts:
            for c2 in rights:
                # SVG <hkern k="..."> subtracts k from horizontal advance
                kerning[(c1, c2)] = -k_val

    return _SVGFontData(
        units_per_em=units_per_em,
        default_adv=default_adv,
        space_adv=space_adv,
        cap_height=cap_height,
        glyphs=glyphs,
        kerning=kerning,
    )


@lru_cache(maxsize=16)
def _load_custom_json_font(font_path: str) -> tuple[float, dict[int, list[str]]]:
    with open(font_path, encoding="utf-8") as fh:
        raw = json.load(fh)
    meta = raw.get("metadata", {})
    em = float(meta.get("font_size", 1000.0))
    glyphs: dict[int, list[str]] = {}
    for k, paths in raw.get("glyphs", {}).items():
        try:
            code = int(k)
        except ValueError:
            if len(k) == 1:
                code = ord(k)
            else:
                continue
        if isinstance(paths, list):
            glyphs[code] = [str(p) for p in paths]
    return em, glyphs


class CustomPen(BasePen):
    # overwrite some methods to capture the strokes

    def __init__(self, glyphSet, scale: float = 0.01):
        super().__init__(glyphSet)
        self.opsset = OpsSet(initial_set=[])
        self.scale = scale
        self.min_x = self.min_y = float("inf")
        self.max_x = self.max_y = -float("inf")

    def _scale_point(self, pt):
        x, y = pt[0] * self.scale, -pt[1] * self.scale
        # update bounding box
        self.min_x = min(self.min_x, x)
        self.min_y = min(self.min_y, y)
        self.max_x = max(self.max_x, x)
        self.max_y = max(self.max_y, y)
        return (x, y)

    def _moveTo(self, pt):
        self.opsset.add(Ops(OpsType.MOVE_TO, data=[self._scale_point(pt)]))

    def _lineTo(self, pt):
        self.opsset.add(Ops(OpsType.LINE_TO, data=[self._scale_point(pt)]))

    def _curveToOne(self, pt1, pt2, pt3):
        self.opsset.add(
            Ops(
                OpsType.CURVE_TO,
                data=[
                    self._scale_point(pt1),
                    self._scale_point(pt2),
                    self._scale_point(pt3),
                ],
            )
        )

    def _closePath(self):
        self.opsset.add(Ops(OpsType.CLOSE_PATH, data={}))


class Text(Drawable):
    """
    A Drawable text primitive that renders text using single-line or outline font glyphs.

    Supports TTF fonts (`type="ttf"`), open-path SVG 1.1 single-line plotter fonts
    (`type="svg"`, e.g. `"casual_hand"`, `"blueprint_sans"`, `"architect_hand"`),
    custom skeletonized JSON fonts (`type="custom"`), and Hershey stroke fonts
    (`type="hershey"`), plus built-in open-stroke fallbacks for symbols like `₹`.
    """

    def __init__(
        self,
        text: str,
        position: tuple[float, float] = (0.0, 0.0),
        font_size: int = 12,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.text = text
        self.position = position
        self.font_size = font_size
        self.font_name: str | None = kwargs.get("font_name") or kwargs.get("font")
        if self.font_name == "backstay":
            import warnings

            warnings.warn(BACKSTAY_PERSONAL_USE_WARNING, UserWarning, stacklevel=2)
        self.align: str = kwargs.get("align", "left")
        if self.align not in ("left", "center", "right"):
            raise ValueError(f"Invalid align '{self.align}', choose from: 'left', 'center', 'right'")
        self.scale_factor = kwargs.get("scale_factor", 1.0)
        self._wrapped_lines: list[str] | None = None
        self._line_height: float | None = None

    def _resolve_font_spec(self) -> tuple[str, str, str]:
        """Return `(font_choice, font_type, path_or_hershey_name)`."""
        if self.font_name:
            info = get_font_info(self.font_name)
            if info is not None:
                ftype = info.get("type", "ttf")
                if ftype == "hershey":
                    return (self.font_name, "hershey", info["name"])
                return (self.font_name, ftype, get_font_path(self.font_name))
            return ("feasibly", "ttf", get_font_path("feasibly"))

        # Default random choice among commercial-safe TTF fonts for backward compatibility
        font_list = [
            f
            for f in list_fonts()
            if f != "backstay" and (info := get_font_info(f)) is not None and info.get("type") == "ttf"
        ]
        if not font_list:
            font_list = ["feasibly"]
        if self.sketch_style.disable_font_mixture:
            font_choice = font_list[0]
        else:
            font_choice = str(np.random.choice(font_list))
        return (font_choice, "ttf", get_font_path(font_choice))

    def get_random_font_choice(self) -> tuple[str, str]:
        """Return `(font_choice, font_path_or_id)` for the resolved font."""
        choice, _ftype, loc = self._resolve_font_spec()
        return (choice, loc)

    def get_glyph_strokes(self, char: str) -> tuple[OpsSet, float]:
        """Return `(glyph_opsset, advance_width)` for `char` in world units."""
        _choice, ftype, loc = self._resolve_font_spec()

        if ftype == "svg":
            svg_font = _load_svg_font(loc)
            scale = self.scale_factor * self.font_size / svg_font.units_per_em
            entry = svg_font.glyphs.get(char)
            if entry is None and char in _QUOTE_FALLBACK:
                entry = svg_font.glyphs.get(_QUOTE_FALLBACK[char])
            if entry is not None:
                d_str, adv = entry
                return _svg_d_to_opsset(d_str, scale, flip_y=True), adv * scale
            fb = _fallback_symbol_svg_d(char, cap_h=svg_font.cap_height)
            if fb is not None:
                d_str, adv = fb
                return _svg_d_to_opsset(d_str, scale, flip_y=True), adv * scale
            return OpsSet(initial_set=[]), 0.0

        if ftype == "custom":
            em, glyphs = _load_custom_json_font(loc)
            scale = self.scale_factor * self.font_size / em
            paths = glyphs.get(ord(char))
            if paths is None and char in _QUOTE_FALLBACK:
                paths = glyphs.get(ord(_QUOTE_FALLBACK[char]))
            if paths:
                ops = OpsSet(initial_set=[])
                for p_str in paths:
                    # Custom skeleton JSON stores Y-down coordinates around baseline ~950
                    ops.extend(_svg_d_to_opsset(p_str, scale, flip_y=False))
                ops.translate(0.0, -0.95 * em * scale)
                bbox = ops.get_bbox()
                width = max(0.25 * self.font_size, bbox.max_x) if len(ops.opsset) > 0 else 0.35 * self.font_size
                return ops, width
            fb = _fallback_symbol_svg_d(char, cap_h=680.0)
            if fb is not None:
                d_str, adv = fb
                s1000 = self.scale_factor * self.font_size / 1000.0
                return _svg_d_to_opsset(d_str, s1000, flip_y=True), adv * s1000
            return OpsSet(initial_set=[]), 0.0

        if ftype == "hershey":
            from .hershey_constants import HERSHEY_BASELINE, HERSHEY_FONT_UNITS
            from .math import _hershey_font_to_opsset

            lookup_char = _QUOTE_FALLBACK.get(char, char)
            raw_ops = _hershey_font_to_opsset(loc, lookup_char)
            if raw_ops is not None and len(raw_ops.opsset) > 0:
                h_scale = self.scale_factor * self.font_size / HERSHEY_FONT_UNITS
                scaled = OpsSet(initial_set=[])
                for op in raw_ops.opsset:
                    if isinstance(op.data, list):
                        scaled.add(
                            Ops(
                                op.type,
                                [(x * h_scale, (y - HERSHEY_BASELINE) * h_scale) for x, y in op.data],
                                op.partial,
                                op.meta,
                            )
                        )
                    else:
                        scaled.add(op)
                bbox = scaled.get_bbox()
                scaled.translate(-bbox.min_x, 0.0)
                return scaled, bbox.width + 0.08 * self.font_size
            fb = _fallback_symbol_svg_d(char, cap_h=680.0)
            if fb is not None:
                d_str, adv = fb
                s1000 = self.scale_factor * self.font_size / 1000.0
                return _svg_d_to_opsset(d_str, s1000, flip_y=True), adv * s1000
            return OpsSet(initial_set=[]), 0.0

        # Default: TTF
        font = _load_ttf(loc)
        glyph_set = font.getGlyphSet()
        cmap = font.getBestCmap()
        units_per_em = font["head"].unitsPerEm
        scale = self.scale_factor * self.font_size / units_per_em
        glyph_name = cmap.get(ord(char))
        if glyph_name is None and char in _QUOTE_FALLBACK:
            glyph_name = cmap.get(ord(_QUOTE_FALLBACK[char]))
        if glyph_name is None:
            fb = _fallback_symbol_svg_d(char, cap_h=0.68 * units_per_em)
            if fb is not None:
                d_str, adv = fb
                s1000 = self.scale_factor * self.font_size / 1000.0
                return _svg_d_to_opsset(d_str, s1000, flip_y=True), adv * s1000
            return (OpsSet(initial_set=[]), 0.0)

        glyph = glyph_set[glyph_name]
        pen = CustomPen(glyph_set, scale=scale)
        glyph.draw(pen)
        width = glyph.width * scale
        return pen.opsset, width

    def _get_kern_offset(self, prev_char: str | None, char: str) -> float:
        """Return horizontal kerning adjustment in world units for `(prev_char, char)`."""
        if prev_char is None:
            return 0.0
        _choice, ftype, loc = self._resolve_font_spec()
        if ftype == "svg":
            svg_font = _load_svg_font(loc)
            k = svg_font.kerning.get((prev_char, char), 0.0)
            if k != 0.0:
                return k * (self.scale_factor * self.font_size / svg_font.units_per_em)
        return 0.0

    def get_glyph_space(self) -> tuple[float, float]:
        """Return `(space_width, glyph_scale)` in world units."""
        _choice, ftype, loc = self._resolve_font_spec()
        if ftype == "svg":
            svg_font = _load_svg_font(loc)
            scale = self.scale_factor * self.font_size / svg_font.units_per_em
            return svg_font.space_adv * scale, scale
        if ftype == "custom":
            em, _ = _load_custom_json_font(loc)
            scale = self.scale_factor * self.font_size / em
            return 0.34 * self.font_size * self.scale_factor, scale
        if ftype == "hershey":
            from .hershey_constants import HERSHEY_FONT_UNITS

            scale = self.scale_factor * self.font_size / HERSHEY_FONT_UNITS
            return 0.34 * self.font_size * self.scale_factor, scale

        font = _load_ttf(loc)
        glyph_set = font.getGlyphSet()
        units_per_em = font["head"].unitsPerEm
        scale = self.scale_factor * self.font_size / units_per_em

        avg_char_width = font["hhea"].advanceWidthMax * scale * 0.5
        space_width = glyph_set["space"].width * scale if "space" in glyph_set else avg_char_width
        return space_width, scale

    def _measure_text_width(self, text: str) -> float:
        """Return the total world-space width of a single line of text at the current font_size."""
        space_width, glyph_scale = self.get_glyph_space()
        _choice, ftype, _loc = self._resolve_font_spec()
        extra_pad = 0.0 if ftype == "svg" else glyph_scale * 5
        total = 0.0
        prev_c: str | None = None
        for char in text:
            if char == " ":
                total += space_width
                prev_c = " "
            else:
                total += self._get_kern_offset(prev_c, char)
                _, glyph_width = self.get_glyph_strokes(char)
                total += glyph_width + extra_pad
                prev_c = char
        return total

    def wrap(self, bbox: BoundingBox, line_height_factor: float = 1.5):
        """
        Pre-compute line breaks so that no line of text exceeds bbox.width.
        """
        words = self.text.split(" ")
        lines: list[str] = []
        current_words: list[str] = []

        for word in words:
            candidate = " ".join(current_words + [word])
            if current_words and self._measure_text_width(candidate) > bbox.width:
                lines.append(" ".join(current_words))
                current_words = [word]
            else:
                current_words.append(word)

        if current_words:
            lines.append(" ".join(current_words))

        self._wrapped_lines = lines
        self._line_height = self.font_size * line_height_factor
        self.position = bbox.top_left

    def autofit(self, bbox: BoundingBox):
        reference_size = 10
        self.font_size = reference_size
        self.position = (0, 0)

        draw_ops = self.draw()
        draw_bbox = draw_ops.get_bbox()

        scale_x = bbox.width / draw_bbox.width
        scale_y = bbox.height / draw_bbox.height

        self.font_size = min(reference_size * scale_x, reference_size * scale_y)  # type: ignore[assignment]
        self.position = (bbox.top_left[0] - draw_bbox.top_left[0], bbox.top_left[1] - draw_bbox.top_left[1])

    def _draw_line(self, opsset: OpsSet, line: str, start_x: float, start_y: float):
        """Render a single line of text into opsset, starting at (start_x, start_y)."""
        if self.align == "center":
            start_x = start_x - self._measure_text_width(line) / 2.0
        elif self.align == "right":
            start_x = start_x - self._measure_text_width(line)
        space_width, glyph_scale = self.get_glyph_space()
        _choice, ftype, _loc = self._resolve_font_spec()
        extra_pad = 0.0 if ftype == "svg" else glyph_scale * 5
        offset_x, offset_y = start_x, start_y
        prev_c: str | None = None
        for char in line:
            if char == " ":
                offset_x += space_width
                prev_c = " "
            else:
                offset_x += self._get_kern_offset(prev_c, char)
                glyph_opsset, glyph_width = self.get_glyph_strokes(char)
                glyph_opsset.translate(offset_x, offset_y)
                opsset.extend(glyph_opsset)
                offset_x += glyph_width + extra_pad
                offset_y += np.random.uniform(
                    -self.sketch_style.roughness, self.sketch_style.roughness
                )
                prev_c = char

    def draw(self) -> OpsSet:
        opsset = OpsSet(initial_set=[])
        opsset.add(
            Ops(
                OpsType.SET_PEN,
                {
                    "color": self.stroke_style.color,
                    "opacity": self.stroke_style.opacity,
                    "width": self.stroke_style.width,
                },
            )
        )

        if self._wrapped_lines is not None:
            line_height = self._line_height or self.font_size * 1.5
            start_x, start_y = self.position
            for i, line in enumerate(self._wrapped_lines):
                self._draw_line(opsset, line, start_x, start_y + i * line_height)
        else:
            self._draw_line(opsset, self.text, self.position[0], self.position[1])

        return opsset
