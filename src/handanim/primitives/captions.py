from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..core.animation import AnimationEvent, AnimationEventType
from ..core.draw_ops import Ops, OpsSet, OpsType
from ..core.drawable import Drawable
from ..core.styles import SketchStyle, StrokeStyle
from ..stylings.color import BLACK, RED
from .text import Text


@dataclass
class CaptionWord:
    """Normalized word timing entry for `Captions`."""

    word: str
    start: float
    end: float


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
        if hasattr(item, "word") and hasattr(item, "start") and hasattr(item, "end"):
            w_text = str(item.word).strip()
            w_start = float(item.start)
            w_end = float(item.end)
        elif isinstance(item, dict):
            if "words" in item and isinstance(item["words"], Sequence):
                has_pre_chunks = True
                chunk_group: list[CaptionWord] = []
                for sub in item["words"]:
                    if isinstance(sub, dict):
                        sw_text = str(sub.get("word", sub.get("text", sub.get("d", "")))).strip()
                        sw_start = float(sub.get("start", sub.get("s", 0.0)))
                        sw_end = float(sub.get("end", sub.get("e", 0.0)))
                        if sw_text:
                            cw = CaptionWord(word=sw_text, start=sw_start, end=sw_end)
                            words.append(cw)
                            chunk_group.append(cw)
                if chunk_group:
                    pre_chunks.append(chunk_group)
                continue
            w_text = str(item.get("word", item.get("text", item.get("d", "")))).strip()
            w_start = float(item.get("start", item.get("s", 0.0)))
            w_end = float(item.get("end", item.get("e", 0.0)))
        elif isinstance(item, (tuple, list)) and len(item) >= 3:
            w_text = str(item[0]).strip()
            w_start = float(item[1])
            w_end = float(item[2])
        else:
            raise TypeError(f"Unsupported word timestamp entry: {item!r}")

        if w_text:
            words.append(CaptionWord(word=w_text, start=w_start, end=w_end))

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

        raw_chunks: list[list[CaptionWord]] = (
            self._prechunked_groups
            if self._prechunked_groups is not None
            else [
                self.words[i : i + self.words_per_chunk]
                for i in range(0, len(self.words), self.words_per_chunk)
            ]
        )

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

            built_words: list[_BuiltCaptionWord] = []
            for cw, w_width in zip(chunk_words, measured_widths, strict=False):
                word_drawable = Text(
                    text=cw.word,
                    position=(cursor_x, self.y),
                    font_size=self.font_size,
                    font_name=self.font_name,
                    scale_factor=chunk_scale,
                    stroke_style=StrokeStyle(
                        color=self.color,
                        width=self.stroke_style.width,
                        opacity=self.stroke_style.opacity,
                    ),
                    sketch_style=self.sketch_style,
                )
                normal_ops = word_drawable.draw()
                highlight_ops = _recolor_opsset(
                    normal_ops,
                    color=self.highlight,
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

            chunk_start = built_words[0].start
            chunk_end = built_words[-1].end
            built_chunks.append(
                _BuiltCaptionChunk(
                    words=built_words,
                    start=chunk_start,
                    end=chunk_end,
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
