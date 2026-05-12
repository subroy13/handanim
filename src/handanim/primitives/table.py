from typing import Any

from ..core.animation import CompositeAnimationEvent
from ..core.draw_ops import BoundingBox
from ..core.drawable import DrawableGroup
from ..core.styles import FillStyle, SketchStyle, StrokeStyle
from .polygons import Rectangle
from .text import Text


class TableRevealEvent(CompositeAnimationEvent):
    """
    A CompositeAnimationEvent that pairs each sub-event with its target drawable.

    Returned by Table.animate_by_row() and Table.animate_by_cell().  Because
    Scene.add() always requires an explicit drawable, callers must unpack these
    pairs themselves — use add_to_scene() as a one-liner convenience.

    Attributes:
        pairs: List of (AnimationEvent, DrawableGroup) in reveal order.

    Usage::

        reveal = table.animate_by_row(SketchAnimation, start_time=0, total_duration=3)
        reveal.add_to_scene(scene)

        # or inspect and filter manually:
        for event, drawable in reveal.pairs:
            scene.add(event, drawable)
    """

    def __init__(self, pairs: list[tuple[Any, DrawableGroup]]):
        self.pairs = pairs
        super().__init__(events=[e for e, _ in pairs])

    def add_to_scene(self, scene: Any) -> None:
        for event, drawable in self.pairs:
            scene.add(event, drawable)


class Table(DrawableGroup):
    """
    A grid of Rectangle + Text cells with optional header-row styling.

    Each cell is a DrawableGroup([rect, text]) stored in self.cells[row][col].
    Row groups (self.row_groups[r]) contain the leaf rect/text drawables for
    all cells in that row — they are kept flat (no nested DrawableGroups) so
    that group-level scene animations apply correctly.

    The Table itself is a flat parallel DrawableGroup of all leaf drawables,
    so scene.add(event, table) animates every cell simultaneously.

    Args:
        top_left: (x, y) world coordinates of the table's top-left corner.
        n_rows: Total rows, including the header row if headers is provided.
        n_cols: Number of columns.
        cell_width: Width of each cell in world units.
        cell_height: Height of each cell in world units.
        data: 2-D list of cell strings, indexed [row][col]. Rows with a header
            start at data[0] = row 1 of the grid. Missing entries default to "".
        headers: Column header strings for row 0. If provided, row 0 uses
            header_stroke_style / header_fill_style instead of the defaults.
        cell_font_size: Font size for data cells.
        header_font_size: Font size for header cells.
        stroke_style: Stroke style for data cells.
        sketch_style: Sketch style shared by all cells.
        fill_style: Fill style for data cells (None = no fill).
        header_stroke_style: Override stroke style for header cells.
        header_fill_style: Override fill style for header cells.
    """

    def __init__(
        self,
        top_left: tuple[float, float],
        n_rows: int,
        n_cols: int,
        cell_width: float,
        cell_height: float,
        data: list[list[str]] | None = None,
        headers: list[str] | None = None,
        cell_font_size: int = 12,
        header_font_size: int = 14,
        stroke_style: StrokeStyle = StrokeStyle(),
        sketch_style: SketchStyle = SketchStyle(),
        fill_style: FillStyle | None = None,
        header_fill_style: FillStyle | None = None,
        header_stroke_style: StrokeStyle | None = None,
        **kwargs,
    ):
        self.top_left = top_left
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.cell_width = cell_width
        self.cell_height = cell_height

        _hss = header_stroke_style if header_stroke_style is not None else stroke_style
        _hfs = header_fill_style if header_fill_style is not None else fill_style

        # Build rect and text primitives for each cell
        self._rects: list[list[Rectangle]] = []
        self._texts: list[list[Text]] = []

        for r in range(n_rows):
            row_rects: list[Rectangle] = []
            row_texts: list[Text] = []
            is_header_row = headers is not None and r == 0

            for c in range(n_cols):
                x = top_left[0] + c * cell_width
                y = top_left[1] + r * cell_height
                cx = x + cell_width / 2
                cy = y + cell_height / 2

                ss = _hss if is_header_row else stroke_style
                fs = _hfs if is_header_row else fill_style
                fs_size = header_font_size if is_header_row else cell_font_size

                if is_header_row:
                    label = headers[c] if c < len(headers) else ""
                elif data is not None:
                    data_row = r if headers is None else r - 1
                    row_data = data[data_row] if data_row < len(data) else []
                    label = row_data[c] if c < len(row_data) else ""
                else:
                    label = ""

                rect = Rectangle(
                    top_left=(x, y),
                    width=cell_width,
                    height=cell_height,
                    stroke_style=ss,
                    sketch_style=sketch_style,
                    fill_style=fs,
                )
                text = Text(
                    text=label,
                    position=(cx, cy),
                    font_size=fs_size,
                    stroke_style=ss,
                    sketch_style=sketch_style,
                )
                row_rects.append(rect)
                row_texts.append(text)

            self._rects.append(row_rects)
            self._texts.append(row_texts)

        # Cell groups: DrawableGroup([rect, text]) — only leaf drawables inside
        self.cells: list[list[DrawableGroup]] = [
            [
                DrawableGroup(
                    elements=[self._rects[r][c], self._texts[r][c]],
                    grouping_method="parallel",
                )
                for c in range(n_cols)
            ]
            for r in range(n_rows)
        ]

        # Row groups: flat list of all leaf drawables in that row (no nesting).
        # This ensures scene.add(event, row_group) sets apply_to_group correctly
        # without being overwritten by a deeper DrawableGroup level.
        self.row_groups: list[DrawableGroup] = [
            DrawableGroup(
                elements=[item for c in range(n_cols) for item in (self._rects[r][c], self._texts[r][c])],
                grouping_method="parallel",
            )
            for r in range(n_rows)
        ]

        # Table's own elements: all leaf drawables, flat — so scene.add(event, table)
        # distributes correctly without nested-group apply_to_group conflicts.
        all_leaves = [
            item for r in range(n_rows) for c in range(n_cols) for item in (self._rects[r][c], self._texts[r][c])
        ]
        super().__init__(
            elements=all_leaves,
            grouping_method="parallel",
            stroke_style=stroke_style,
            sketch_style=sketch_style,
            **kwargs,
        )

    def get_bbox(self) -> BoundingBox:
        return BoundingBox(
            self.top_left[0],
            self.top_left[1],
            self.top_left[0] + self.n_cols * self.cell_width,
            self.top_left[1] + self.n_rows * self.cell_height,
        )

    def animate_by_row(
        self,
        anim_class: type,
        start_time: float = 0.0,
        total_duration: float = 1.0,
        **anim_kwargs,
    ) -> TableRevealEvent:
        """
        Build a staggered row-reveal animation.

        Each row gets an equal slice of total_duration, starting after the
        previous row's slice begins.  All cells in a row animate in parallel.

        Args:
            anim_class: Any AnimationEvent subclass (e.g. SketchAnimation).
            start_time: When the first row's animation begins, in seconds.
            total_duration: Total wall-clock span covering all rows.
            **anim_kwargs: Forwarded to each anim_class constructor.

        Returns:
            TableRevealEvent whose .add_to_scene(scene) registers all pairs.
        """
        row_duration = total_duration / self.n_rows
        pairs = [
            (
                anim_class(
                    start_time=start_time + r * row_duration,
                    duration=row_duration,
                    **anim_kwargs,
                ),
                self.row_groups[r],
            )
            for r in range(self.n_rows)
        ]
        return TableRevealEvent(pairs)

    def animate_by_cell(
        self,
        anim_class: type,
        start_time: float = 0.0,
        total_duration: float = 1.0,
        **anim_kwargs,
    ) -> TableRevealEvent:
        """
        Build a staggered cell-reveal animation in row-major order.

        Each cell gets an equal slice of total_duration.  Both the rect and
        the text inside a cell animate together (the cell's DrawableGroup is
        the target).

        Args:
            anim_class: Any AnimationEvent subclass (e.g. SketchAnimation).
            start_time: When the first cell's animation begins, in seconds.
            total_duration: Total wall-clock span covering all cells.
            **anim_kwargs: Forwarded to each anim_class constructor.

        Returns:
            TableRevealEvent whose .add_to_scene(scene) registers all pairs.
        """
        n_cells = self.n_rows * self.n_cols
        cell_duration = total_duration / n_cells
        pairs = [
            (
                anim_class(
                    start_time=start_time + (r * self.n_cols + c) * cell_duration,
                    duration=cell_duration,
                    **anim_kwargs,
                ),
                self.cells[r][c],
            )
            for r in range(self.n_rows)
            for c in range(self.n_cols)
        ]
        return TableRevealEvent(pairs)
