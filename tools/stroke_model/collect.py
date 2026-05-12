"""
Interactive stroke collection tool — Jupyter widget.

Usage (in a Jupyter notebook):
    from collect import StrokeCollector
    collector = StrokeCollector(output_file="my_strokes.json")
    collector.show()   # renders the canvas for the first symbol
    # Draw each symbol; press "Next" to advance, "Clear" to redo, "Save" to flush to disk

Output format (one entry per symbol):
    {
        "symbol": "α",
        "unicode": 945,
        "strokes": [
            [[x1, y1], [x2, y2], ...],   # stroke 1 (pen-down → pen-up)
            [[x3, y3], [x4, y4], ...]    # stroke 2
        ]
    }

Each inner list is one continuous pen stroke; a new list starts every time the pen lifts.
Requires: pip install ipycanvas ipywidgets
"""

from __future__ import annotations

import json
from pathlib import Path

# ipycanvas and ipywidgets are not in the poetry deps — install manually in the notebook env:
#   pip install ipycanvas ipywidgets
try:
    import ipywidgets as widgets
    from ipycanvas import Canvas, hold_canvas
except ImportError as e:
    raise ImportError("Run `pip install ipycanvas ipywidgets` before using StrokeCollector.") from e

from symbols import SYMBOL_LABELS

CANVAS_SIZE = 400  # px


class StrokeCollector:
    """Jupyter widget for recording handwritten stroke sequences symbol by symbol."""

    def __init__(
        self,
        output_file: str = "strokes.json",
        symbols: list[str] = SYMBOL_LABELS,
        canvas_size: int = CANVAS_SIZE,
    ):
        self.output_file = Path(output_file)
        self.symbols = symbols
        self.canvas_size = canvas_size

        self._current_idx = 0
        self._current_strokes: list[list[list[float]]] = []
        self._active_stroke: list[list[float]] = []
        self._is_drawing = False
        self._collected: list[dict] = self._load_existing()

        self._build_ui()

    def _load_existing(self) -> list[dict]:
        if self.output_file.exists():
            with open(self.output_file) as f:
                return json.load(f)
        return []

    def _build_ui(self):
        self._canvas = Canvas(width=self.canvas_size, height=self.canvas_size)
        self._canvas.fill_style = "white"
        self._canvas.fill_rect(0, 0, self.canvas_size, self.canvas_size)

        self._label = widgets.Label(value=self._symbol_label())
        self._progress = widgets.Label(value=self._progress_label())

        btn_clear = widgets.Button(description="Clear", button_style="warning")
        btn_next = widgets.Button(description="Next", button_style="success")
        btn_save = widgets.Button(description="Save to disk", button_style="info")

        btn_clear.on_click(lambda _: self._on_clear())
        btn_next.on_click(lambda _: self._on_next())
        btn_save.on_click(lambda _: self._save())

        self._canvas.on_mouse_down(self._on_mouse_down)
        self._canvas.on_mouse_move(self._on_mouse_move)
        self._canvas.on_mouse_up(self._on_mouse_up)

        self._ui = widgets.VBox([
            self._label,
            self._progress,
            self._canvas,
            widgets.HBox([btn_clear, btn_next, btn_save]),
        ])

    def show(self):
        """Display the collector widget in the notebook."""
        from IPython.display import display
        display(self._ui)

    # --- event handlers ---

    def _on_mouse_down(self, x: float, y: float):
        self._is_drawing = True
        self._active_stroke = [[x, y]]

    def _on_mouse_move(self, x: float, y: float):
        if not self._is_drawing:
            return
        self._active_stroke.append([x, y])
        with hold_canvas(self._canvas):
            prev = self._active_stroke[-2]
            self._canvas.stroke_style = "black"
            self._canvas.line_width = 3
            self._canvas.begin_path()
            self._canvas.move_to(prev[0], prev[1])
            self._canvas.line_to(x, y)
            self._canvas.stroke()

    def _on_mouse_up(self, x: float, y: float):
        if self._is_drawing and len(self._active_stroke) > 1:
            self._active_stroke.append([x, y])
            self._current_strokes.append(self._active_stroke)
        self._active_stroke = []
        self._is_drawing = False

    def _on_clear(self):
        self._current_strokes = []
        self._active_stroke = []
        self._canvas.clear()
        self._canvas.fill_style = "white"
        self._canvas.fill_rect(0, 0, self.canvas_size, self.canvas_size)

    def _on_next(self):
        if not self._current_strokes:
            return
        symbol = self.symbols[self._current_idx]
        self._collected.append({
            "symbol": symbol,
            "unicode": ord(symbol),
            "strokes": self._current_strokes,
        })
        self._current_idx = min(self._current_idx + 1, len(self.symbols) - 1)
        self._current_strokes = []
        self._on_clear()
        self._label.value = self._symbol_label()
        self._progress.value = self._progress_label()

    def _save(self):
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(self._collected, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(self._collected)} glyphs to {self.output_file}")

    def _symbol_label(self) -> str:
        sym = self.symbols[self._current_idx]
        return f"Draw: {sym}  (U+{ord(sym):04X})"

    def _progress_label(self) -> str:
        return f"{self._current_idx + 1} / {len(self.symbols)}"
