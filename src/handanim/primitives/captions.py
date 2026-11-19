from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..core.animation import AnimationEvent, AnimationEventType
from ..core.draw_ops import Ops, OpsSet, OpsType
from ..core.drawable import Drawable
from ..core.styles import FillStyle, SketchStyle, StrokeStyle
from ..stylings.color import BLACK, RED
from .polygons import RoundedRectangle
from .text import Text


@dataclass
class CaptionWord:
    """Normalized word timing entry for `Captions`."""

    word: str
    start: float
    end: float
    speaker: str | None = None
    em: bool = False
    color: tuple[float, float, float] | None = None


@dataclass
class _BuiltCaptionWord:
    word: str
    start: float
    end: float
    normal_ops: OpsSet
    highlight_ops: OpsSet


@dataclass
class _BuiltCaptionChunk:
    words: list[_BuiltCaptionWord]
    start: float
    end: float
    bg_ops: OpsSet | None = None


def _recolor_opsset(
    opsset: OpsSet,
    color: tuple[float, float, float],
    width: float | None = None,
) -> OpsSet:
    """Return a copy of `opsset` with `SET_PEN` stroke color (and optional width) replaced."""
    new_ops: list[Ops] = []
    for op in opsset.opsset:
        if op.type == OpsType.SET_PEN and isinstance(op.data, dict):
            data = dict(op.data)
            data["color"] = color
            if width is not None:
                data["width"] = width
            meta = dict(op.meta) if op.meta else None
            new_ops.append(Ops(type=OpsType.SET_PEN, data=data, partial=op.partial, meta=meta))
        else:
            new_ops.append(op)
    return OpsSet(initial_set=new_ops)


def _extract_caption_words(
    clip: Any,
) -> tuple[list[CaptionWord], float, list[list[CaptionWord]] | None]:
    """Extract normalized `CaptionWord` list, total duration, and optional pre-grouped chunks."""
    raw_words: Sequence[Any] = []
    total_duration = 0.0

    if hasattr(clip, "words"):
        raw_words = clip.words
        if hasattr(clip, "duration"):
            total_duration = float(clip.duration)
    elif isinstance(clip, dict):
        raw_words = clip.get("words", [])
        total_duration = float(clip.get("duration", 0.0))
    elif isinstance(clip, Sequence):
        raw_words = clip
    else:
        raise TypeError(
            "Captions `clip` must be an AudioClip, a dict with 'words', or a sequence of word timing entries"
        )

    words: list[CaptionWord] = []
    pre_chunks: list[list[CaptionWord]] = []
    has_pre_chunks = False

    for item in raw_words:
        w_speaker: str | None = None
        w_em: bool = False
        w_color: tuple[float, float, float] | None = None

        if hasattr(item, "word") and hasattr(item, "start") and hasattr(item, "end"):
            w_text = str(item.word).strip()
            w_start = float(item.start)
            w_end = float(item.end)
            w_speaker = getattr(item, "speaker", None)
            w_em = bool(getattr(item, "em", False))
            w_color = getattr(item, "color", None)
        elif isinstance(item, dict):
            if "words" in item and isinstance(item["words"], Sequence):
                has_pre_chunks = True
                chunk_group: list[CaptionWord] = []
                parent_spk = item.get("speaker")
                for sub in item["words"]:
                    if isinstance(sub, dict):
                        sw_text = str(sub.get("word", sub.get("text", sub.get("d", "")))).strip()
                        sw_start = float(sub.get("start", sub.get("s", 0.0)))
                        sw_end = float(sub.get("end", sub.get("e", 0.0)))
                        sw_spk = sub.get("speaker", parent_spk)
                        sw_em = bool(sub.get("em", False))
                        raw_sc = sub.get("color")
                        sw_col = (
                            (float(raw_sc[0]), float(raw_sc[1]), float(raw_sc[2]))
                            if raw_sc is not None and len(raw_sc) >= 3
                            else None
                        )
                        if sw_text:
                            cw = CaptionWord(
                                word=sw_text,
                                start=sw_start,
                                end=sw_end,
                                speaker=sw_spk,
                                em=sw_em,
                                color=sw_col,
                            )
                            words.append(cw)
                            chunk_group.append(cw)
                if chunk_group:
                    pre_chunks.append(chunk_group)
                continue
            w_text = str(item.get("word", item.get("text", item.get("d", "")))).strip()
            w_start = float(item.get("start", item.get("s", 0.0)))
            w_end = float(item.get("end", item.get("e", 0.0)))
            w_speaker = item.get("speaker")
            w_em = bool(item.get("em", False))
            raw_wc = item.get("color")
            w_color = (
                (float(raw_wc[0]), float(raw_wc[1]), float(raw_wc[2]))
                if raw_wc is not None and len(raw_wc) >= 3
                else None
            )
        elif isinstance(item, (tuple, list)) and len(item) >= 3:
            w_text = str(item[0]).strip()
            w_start = float(item[1])
            w_end = float(item[2])
            if len(item) >= 4 and isinstance(item[3], str):
                w_speaker = item[3]
        else:
            raise TypeError(f"Unsupported word timestamp entry: {item!r}")

        if w_text:
            words.append(
                CaptionWord(
                    word=w_text,
                    start=w_start,
                    end=w_end,
                    speaker=w_speaker,
                    em=w_em,
                    color=w_color,
                )
            )

    if words:
        total_duration = max(total_duration, max(w.end for w in words))
    return words, total_duration, (pre_chunks if has_pre_chunks else None)


class CaptionsAnimation(AnimationEvent):
    """Single timeline event that drives a `Captions` drawable across the narration duration."""

    def __init__(
        self,
        captions: Captions | None = None,
        start_time: float = 0.0,
        duration: float | None = None,
        easing_fun=None,
        data: dict | None = None,
    ) -> None:
        data_dict = dict(data) if data else {}
        if captions is None:
            captions = data_dict.get("captions")
        self.captions = captions
        if duration is None:
            duration = captions.duration if captions is not None else 0.0
        data_dict["captions"] = self.captions
        super().__init__(AnimationEventType.CREATION, start_time, float(duration), easing_fun, data_dict)

    def apply(self, opsset: OpsSet, raw_progress: float) -> OpsSet:
        if self.captions is None:
            return opsset
        p = float(np.clip(raw_progress, 0.0, 1.0))
        t = self.start_time + p * self.duration
        return self.captions.draw_at_time(t)

    def _apply(self, opsset: OpsSet, progress: float) -> OpsSet:
        if self.captions is None:
            return opsset
        t = self.start_time + progress * self.duration
        return self.captions.draw_at_time(t)


class Captions(Drawable):
    """Word-timed narration captions rendered as a single drawable + single animation event.

    Groups spoken words from `clip` into chunks of `words_per_chunk`, pre-caches
    base and highlighted `OpsSet`s for each word, and highlights the active word
    at any timestamp `t`.

    Usage::

        captions = Captions(clip, words_per_chunk=3, highlight=RED, y=1590)
        scene.overlay.add(captions)
    """

    def __init__(
        self,
        clip: Any,
        words_per_chunk: int = 3,
        highlight: tuple[float, float, float] = RED,
        color: tuple[float, float, float] = BLACK,
        y: float = 1590.0,
        x: float | None = None,
        font_size: int = 48,
        font_name: str | None = None,
        align: str = "center",
        word_spacing: float | None = None,
        max_width: float | None = 960.0,
        start_time: float = 0.0,
        max_hold_gap: float = 0.25,
        stroke_style: StrokeStyle | None = None,
        sketch_style: SketchStyle | None = None,
        highlight_stroke_width: float | None = None,
        speaker_colors: dict[str, tuple[float, float, float]] | None = None,
        speaker_highlights: dict[str, tuple[float, float, float]] | None = None,
        secondary_highlight: tuple[float, float, float] | None = None,
        highlight_numbers: bool = False,
        background_color: tuple[float, float, float] | None = None,
        background_opacity: float = 0.85,
        background_padding: float = 14.0,
        **kwargs,
    ) -> None:
        if stroke_style is None:
            stroke_style = StrokeStyle(color=color, width=2.5)
        if sketch_style is None:
            sketch_style = SketchStyle(roughness=0.0, disable_font_mixture=True)
        super().__init__(stroke_style=stroke_style, sketch_style=sketch_style, **kwargs)

        if words_per_chunk < 1:
            raise ValueError("words_per_chunk must be >= 1")
        if align not in ("center", "left", "right"):
            raise ValueError("align must be one of 'center', 'left', or 'right'")

        self.clip = clip
        self.words, self.clip_duration, self._prechunked_groups = _extract_caption_words(clip)
        self.words_per_chunk = int(words_per_chunk)
        self.highlight = highlight
        self.color = color
        self.y = float(y)
        self.x: float | None = float(x) if x is not None else None
        self.font_size = int(font_size)
        self.font_name = font_name
        self.align = align
        self.word_spacing = word_spacing
        self.max_width: float | None = float(max_width) if max_width is not None else None
        self.start_time = float(start_time)
        self.max_hold_gap = float(max_hold_gap)
        self.highlight_stroke_width = highlight_stroke_width
        self.speaker_colors: dict[str, tuple[float, float, float]] = dict(speaker_colors or {})
        self.speaker_highlights: dict[str, tuple[float, float, float]] = dict(speaker_highlights or {})
        self.secondary_highlight = secondary_highlight
        self.highlight_numbers = bool(highlight_numbers)
        self.background_color = background_color
        self.background_opacity = float(background_opacity)
        self.background_padding = float(background_padding)

        # Populate speaker color defaults from clip.metadata["speakers"] if present
        clip_meta = getattr(clip, "metadata", None) or (clip.get("metadata") if isinstance(clip, dict) else None)
        if isinstance(clip_meta, dict) and isinstance(clip_meta.get("speakers"), dict):
            for spk_name, spk_cfg in clip_meta["speakers"].items():
                if isinstance(spk_cfg, dict):
                    if spk_name not in self.speaker_colors and spk_cfg.get("color") is not None:
                        c_val = spk_cfg["color"]
                        self.speaker_colors[spk_name] = (float(c_val[0]), float(c_val[1]), float(c_val[2]))
                    if spk_name not in self.speaker_highlights and spk_cfg.get("highlight") is not None:
                        h_val = spk_cfg["highlight"]
                        self.speaker_highlights[spk_name] = (float(h_val[0]), float(h_val[1]), float(h_val[2]))

        self._built_center_x: float | None = None
        self._chunks: list[_BuiltCaptionChunk] = []

    @property
    def chunks(self) -> list[_BuiltCaptionChunk]:
        self._ensure_built()
        return self._chunks

    @property
    def duration(self) -> float:
        return self.clip_duration

    def set_default_x(self, center_x: float) -> None:
        """Set default horizontal anchor if `x` was not explicitly provided."""
        if self.x is None and self._built_center_x != center_x:
            self._build_chunks(center_x)

    def _group_words_respecting_speakers(self) -> list[list[CaptionWord]]:
        """Group words into chunks of at most `words_per_chunk`, splitting on speaker changes."""
        if self._prechunked_groups is not None:
            return self._prechunked_groups
        groups: list[list[CaptionWord]] = []
        current: list[CaptionWord] = []
        for cw in self.words:
            if current and (
                len(current) >= self.words_per_chunk
                or (cw.speaker is not None and current[-1].speaker is not None and cw.speaker != current[-1].speaker)
            ):
                groups.append(current)
                current = [cw]
            else:
                current.append(cw)
        if current:
            groups.append(current)
        return groups

    def _resolve_word_colors(
        self,
        cw: CaptionWord,
    ) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        """Return `(normal_color, active_highlight_color)` for a caption word."""
        base_col = self.speaker_colors.get(cw.speaker, self.color) if cw.speaker else self.color
        active_col = self.speaker_highlights.get(cw.speaker, self.highlight) if cw.speaker else self.highlight

        is_num = bool(re.search(r"\d", cw.word))
        if cw.color is not None:
            base_col = cw.color
        elif (cw.em or (self.highlight_numbers and is_num)) and self.secondary_highlight is not None:
            base_col = self.secondary_highlight
        elif cw.em and self.secondary_highlight is None:
            base_col = active_col
        return base_col, active_col

    def _build_chunks(self, anchor_x: float) -> None:
        self._built_center_x = anchor_x
        self._chunks = []
        if not self.words:
            return

        # Measure space width using a helper Text instance
        helper_text = Text(
            text=" ",
            position=(0.0, 0.0),
            font_size=self.font_size,
            font_name=self.font_name,
            stroke_style=StrokeStyle(color=self.color, width=self.stroke_style.width, opacity=self.stroke_style.opacity),
            sketch_style=self.sketch_style,
        )
        default_space_w, _ = helper_text.get_glyph_space()
        space_w = float(self.word_spacing) if self.word_spacing is not None else float(default_space_w * 1.15)

        raw_chunks = self._group_words_respecting_speakers()

        built_chunks: list[_BuiltCaptionChunk] = []
        for chunk_words in raw_chunks:
            measured_widths: list[float] = []
            for cw in chunk_words:
                w = helper_text._measure_text_width(cw.word)
                measured_widths.append(float(w))

            total_width = sum(measured_widths) + max(0, len(chunk_words) - 1) * space_w
            chunk_scale = (
                min(1.0, self.max_width / total_width)
                if (self.max_width is not None and self.max_width > 0.0 and total_width > 0.0)
                else 1.0
            )
            scaled_total_width = total_width * chunk_scale
            if self.align == "center":
                cursor_x = anchor_x - scaled_total_width / 2.0
            elif self.align == "right":
                cursor_x = anchor_x - scaled_total_width
            else:
                cursor_x = anchor_x

            start_x = cursor_x
            built_words: list[_BuiltCaptionWord] = []
            for cw, w_width in zip(chunk_words, measured_widths, strict=False):
                base_col, active_col = self._resolve_word_colors(cw)
                word_drawable = Text(
                    text=cw.word,
                    position=(cursor_x, self.y),
                    font_size=self.font_size,
                    font_name=self.font_name,
                    scale_factor=chunk_scale,
                    stroke_style=StrokeStyle(
                        color=base_col,
                        width=self.stroke_style.width,
                        opacity=self.stroke_style.opacity,
                    ),
                    sketch_style=self.sketch_style,
                )
                normal_ops = word_drawable.draw()
                highlight_ops = _recolor_opsset(
                    normal_ops,
                    color=active_col,
                    width=self.highlight_stroke_width,
                )
                built_words.append(
                    _BuiltCaptionWord(
                        word=cw.word,
                        start=cw.start + self.start_time,
                        end=cw.end + self.start_time,
                        normal_ops=normal_ops,
                        highlight_ops=highlight_ops,
                    )
                )
                cursor_x += (w_width + space_w) * chunk_scale

            bg_ops: OpsSet | None = None
            if self.background_color is not None:
                pad = self.background_padding
                line_h = self.font_size * chunk_scale * 1.15
                pill = RoundedRectangle(
                    top_left=(start_x - pad, self.y - pad * 0.6),
                    width=scaled_total_width + 2.0 * pad,
                    height=line_h + 1.2 * pad,
                    border_radius=min(16.0, (line_h + 1.2 * pad) * 0.35),
                    stroke_style=StrokeStyle(color=self.background_color, width=0.5, opacity=self.background_opacity),
                    fill_style=FillStyle(
                        color=self.background_color,
                        opacity=self.background_opacity,
                        fill_pattern="solid",
                    ),
                    sketch_style=SketchStyle(roughness=0.0),
                )
                bg_ops = pill.draw()

            chunk_start = built_words[0].start
            chunk_end = built_words[-1].end
            built_chunks.append(
                _BuiltCaptionChunk(
                    words=built_words,
                    start=chunk_start,
                    end=chunk_end,
                    bg_ops=bg_ops,
                )
            )

        # Bridge small intra-narration gaps between consecutive chunks so captions don't flicker
        if self.max_hold_gap > 0.0:
            for i in range(len(built_chunks) - 1):
                gap = built_chunks[i + 1].start - built_chunks[i].end
                if 0.0 < gap <= self.max_hold_gap:
                    built_chunks[i].end = built_chunks[i + 1].start

        self._chunks = built_chunks

    def _ensure_built(self) -> None:
        target_x = self.x if self.x is not None else (self._built_center_x if self._built_center_x is not None else 540.0)
        if not self._chunks and self.words:
            self._build_chunks(target_x)

    def get_active_chunk_index(self, t: float) -> int | None:
        """Return the index of the caption chunk active at timestamp `t`, or `None`."""
        self._ensure_built()
        for idx, chunk in enumerate(self._chunks):
            if chunk.start <= t <= chunk.end:
                return idx
        return None

    def draw_at_time(self, t: float) -> OpsSet:
        """Return the `OpsSet` for the caption chunk active at timestamp `t` (in seconds)."""
        self._ensure_built()
        idx = self.get_active_chunk_index(t)
        if idx is None:
            return OpsSet(initial_set=[])

        chunk = self._chunks[idx]
        result = OpsSet(initial_set=[])
        if chunk.bg_ops is not None:
            result.extend(chunk.bg_ops)

        # Determine which word in the chunk is highlighted at time t
        active_word_idx: int | None = None
        for w_idx, bw in enumerate(chunk.words):
            if bw.start <= t <= bw.end:
                active_word_idx = w_idx
                break

        # If t falls in a tiny micro-gap between two words inside the same chunk,
        # keep the most recently started word highlighted if within max_hold_gap
        if active_word_idx is None and self.max_hold_gap > 0.0:
            for w_idx in range(len(chunk.words) - 1):
                bw_curr = chunk.words[w_idx]
                bw_next = chunk.words[w_idx + 1]
                if bw_curr.end < t < bw_next.start and (bw_next.start - bw_curr.end) <= self.max_hold_gap:
                    active_word_idx = w_idx
                    break

        for w_idx, bw in enumerate(chunk.words):
            if w_idx == active_word_idx:
                result.extend(bw.highlight_ops)
            else:
                result.extend(bw.normal_ops)
        return result

    def to_event(self) -> CaptionsAnimation:
        """Create the `CaptionsAnimation` event that drives this `Captions` drawable."""
        total_end = (
            max((w.end for w in self.words), default=self.clip_duration)
            if self.words
            else self.clip_duration
        )
        return CaptionsAnimation(
            captions=self,
            start_time=self.start_time,
            duration=max(0.0, total_end),
        )

    def draw(self) -> OpsSet:
        """Draw the first chunk in its initial state (used for static bbox / cache initialization)."""
        self._ensure_built()
        if not self._chunks:
            return OpsSet(initial_set=[])
        first_chunk = self._chunks[0]
        return self.draw_at_time(first_chunk.start)
