"""Convert OpsSet drawing operations to TikZ commands for native LaTeX output.

This module provides a renderer that translates the internal drawing
operation stream (OpsSet) into TikZ path commands.  The resulting code
can be embedded directly in a beamer slide or standalone LaTeX document,
producing truly native vector output instead of rasterised PDF images.

Coordinate convention
---------------------
handanim world space is Y-down (origin at top-left), while TikZ is Y-up.
The renderer flips Y and scales world units to centimetres so the picture
fits a configurable target width (default 12 cm, matching ``\\textwidth``
on a 16:9 beamer slide with default margins).
"""

from __future__ import annotations

from .draw_ops import OpsSet, OpsType
from .utils import get_bezier_points_from_quadcurve, slice_bezier
from .viewport import Viewport


def _fmt(x: float) -> str:
    """Format a float, stripping trailing zeros for compact output."""
    s = f"{x:.4f}"
    s = s.rstrip("0").rstrip(".")
    return s


def _coord(x: float, y: float) -> str:
    return f"({_fmt(x)},{_fmt(y)})"


class TikZRenderer:
    """Converts an OpsSet into TikZ drawing commands.

    Parameters
    ----------
    viewport : Viewport
        The viewport that defines the world coordinate system.
    target_width_cm : float
        Width of the output tikzpicture in centimetres.
    background_color : tuple[float, float, float] | None
        Optional RGB background (0-1 range).
    precision : int
        Decimal digits kept in coordinates and widths.
    """

    def __init__(
        self,
        viewport: Viewport,
        target_width_cm: float = 12.0,
        background_color: tuple[float, float, float] | None = None,
        precision: int = 4,
    ):
        self.viewport = viewport
        self.background_color = background_color
        self.precision = precision

        world_w = viewport.world_xrange[1] - viewport.world_xrange[0]
        world_h = viewport.world_yrange[1] - viewport.world_yrange[0]

        scale_x = target_width_cm / world_w
        scale_y = (target_width_cm * world_h / world_w) / world_h
        self.scale = min(scale_x, scale_y)
        self.width_cm = world_w * self.scale
        self.height_cm = world_h * self.scale

        self._color_counter = 0
        self._color_cache: dict[tuple[float, float, float], str] = {}

    def _transform(self, x: float, y: float) -> tuple[float, float]:
        """Map world coordinates to TikZ coordinates (Y-flipped, cm)."""
        tx = (x - self.viewport.world_xrange[0]) * self.scale
        ty = (self.viewport.world_yrange[1] - y) * self.scale
        return tx, ty

    def _scale_width(self, w: float) -> float:
        """Scale a world-unit line width to centimetres."""
        return w * self.scale

    def _get_color_name(self, r: float, g: float, b: float) -> str:
        key = (round(r, 3), round(g, 3), round(b, 3))
        if key not in self._color_cache:
            self._color_counter += 1
            self._color_cache[key] = f"ha{self._color_counter}"
        return self._color_cache[key]

    def _color_definitions(self) -> list[str]:
        """Return \\definecolor lines for every colour used so far."""
        lines = []
        for (r, g, b), name in sorted(self._color_cache.items(), key=lambda x: x[1]):
            lines.append(f"\\definecolor{{{name}}}{{rgb}}{{{r},{g},{b}}}")
        return lines

    # ------------------------------------------------------------------
    #  Path building helpers
    # ------------------------------------------------------------------

    def _flush_path(
        self,
        path_cmds: list[str],
        mode: str,
        color_name: str | None,
        line_width_cm: float | None,
        opacity: float,
    ) -> str | None:
        """Emit a \\draw or \\fill command for the accumulated path."""
        if not path_cmds:
            return None

        cmd = "\\fill" if mode == "fill" else "\\draw"
        opts: list[str] = []
        if color_name:
            opts.append(f"color={color_name}")
        if mode != "fill" and line_width_cm is not None:
            pts = line_width_cm / 0.03528  # 1pt = 0.03528cm
            opts.append(f"line width={_fmt(pts)}pt")
        if opacity < 1.0:
            key = "fill opacity" if mode == "fill" else "opacity"
            opts.append(f"{key}={_fmt(opacity)}")

        opt_str = ", ".join(opts)
        path_str = " ".join(path_cmds)
        return f"  {cmd}[{opt_str}] {path_str};"

    # ------------------------------------------------------------------
    #  Main conversion
    # ------------------------------------------------------------------

    def render_opsset(self, opsset: OpsSet) -> list[str]:
        """Convert an OpsSet to a list of TikZ drawing command strings.

        Returns a list of strings, each a complete TikZ command
        (``\\draw[...] ...;`` or ``\\fill[...] ...;``).
        """
        commands: list[str] = []
        path_cmds: list[str] = []
        current_point: tuple[float, float] | None = None

        # pen state
        mode = "stroke"
        color_name: str | None = None
        line_width_cm: float | None = None
        opacity: float = 1.0

        def flush():
            line = self._flush_path(path_cmds, mode, color_name, line_width_cm, opacity)
            if line:
                commands.append(line)
            path_cmds.clear()

        for ops in opsset.opsset:
            if ops.type == OpsType.MOVE_TO:
                pt = ops.data[0]
                tx, ty = self._transform(float(pt[0]), float(pt[1]))
                path_cmds.append(_coord(tx, ty))
                current_point = (float(pt[0]), float(pt[1]))

            elif ops.type == OpsType.LINE_TO:
                pt = ops.data[0]
                x1, y1 = float(pt[0]), float(pt[1])
                if ops.partial < 1.0 and current_point is not None:
                    x0, y0 = current_point
                    x1 = x0 + ops.partial * (x1 - x0)
                    y1 = y0 + ops.partial * (y1 - y0)
                tx, ty = self._transform(x1, y1)
                path_cmds.append(f"-- {_coord(tx, ty)}")
                current_point = (x1, y1)

            elif ops.type == OpsType.CURVE_TO:
                cp1 = ops.data[0]
                cp2 = ops.data[1]
                end = ops.data[2]
                p1 = (float(cp1[0]), float(cp1[1]))
                p2 = (float(cp2[0]), float(cp2[1]))
                p3 = (float(end[0]), float(end[1]))

                if ops.partial < 1.0 and current_point is not None:
                    sliced = slice_bezier(current_point, p1, p2, p3, ops.partial)
                    p1, p2, p3 = sliced[0], sliced[1], sliced[2]

                t1 = self._transform(*p1)
                t2 = self._transform(*p2)
                t3 = self._transform(*p3)
                path_cmds.append(
                    f".. controls {_coord(*t1)} and {_coord(*t2)} .. {_coord(*t3)}"
                )
                current_point = (float(end[0]), float(end[1])) if ops.partial >= 1.0 else p3

            elif ops.type == OpsType.QUAD_CURVE_TO:
                q1 = ops.data[0]
                q2 = ops.data[1]
                q1f = (float(q1[0]), float(q1[1]))
                q2f = (float(q2[0]), float(q2[1]))
                if current_point is None:
                    current_point = (0.0, 0.0)
                p1, p2, p3 = get_bezier_points_from_quadcurve(current_point, q1f, q2f)
                if ops.partial < 1.0:
                    sliced = slice_bezier(current_point, p1, p2, p3, ops.partial)
                    p1, p2, p3 = sliced[0], sliced[1], sliced[2]
                t1 = self._transform(*p1)
                t2 = self._transform(*p2)
                t3 = self._transform(*p3)
                path_cmds.append(
                    f".. controls {_coord(*t1)} and {_coord(*t2)} .. {_coord(*t3)}"
                )
                current_point = q2f if ops.partial >= 1.0 else p3

            elif ops.type == OpsType.CLOSE_PATH:
                path_cmds.append("-- cycle")

            elif ops.type == OpsType.SET_PEN:
                flush()
                mode = ops.data.get("mode", "stroke")
                color = ops.data.get("color")
                if color:
                    r, g, b = float(color[0]), float(color[1]), float(color[2])
                    color_name = self._get_color_name(r, g, b)
                opacity = float(ops.data.get("opacity", 1.0))
                width = ops.data.get("width")
                if width:
                    line_width_cm = self._scale_width(float(width))

            elif ops.type == OpsType.DOT:
                flush()
                cx, cy = ops.data.get("center", (0, 0))
                radius = float(ops.data.get("radius", 1))
                tx, ty = self._transform(float(cx), float(cy))
                tr = radius * self.scale
                dot_opts = []
                if color_name:
                    dot_opts.append(f"color={color_name}")
                if opacity < 1.0:
                    dot_opts.append(f"fill opacity={_fmt(opacity)}")
                opt_str = ", ".join(dot_opts)
                commands.append(f"  \\fill[{opt_str}] {_coord(tx, ty)} circle ({_fmt(tr)}cm);")

            elif ops.type == OpsType.METADATA:
                pass

        # flush any remaining path
        flush()
        return commands

    def render_tikzpicture(self, opsset: OpsSet) -> str:
        """Return a complete ``tikzpicture`` environment string for one frame.

        Includes colour definitions, optional background rectangle,
        and all drawing commands.
        """
        # register background colour first so it appears in definitions
        bg_name: str | None = None
        if self.background_color:
            r, g, b = self.background_color
            bg_name = self._get_color_name(r, g, b)

        draw_cmds = self.render_opsset(opsset)

        lines: list[str] = []
        lines.append("\\begin{tikzpicture}")

        for cdef in self._color_definitions():
            lines.append(f"  {cdef}")

        w, h = _fmt(self.width_cm), _fmt(self.height_cm)
        lines.append(f"  \\useasboundingbox (0,0) rectangle ({w},{h});")

        if bg_name:
            lines.append(f"  \\fill[{bg_name}] (0,0) rectangle ({w},{h});")

        lines.extend(draw_cmds)
        lines.append("\\end{tikzpicture}")
        return "\n".join(lines)

    def reset_colors(self):
        """Clear the colour cache between frames to keep definitions local."""
        self._color_counter = 0
        self._color_cache.clear()


def opsset_to_tikz(
    opsset: OpsSet,
    viewport: Viewport,
    target_width_cm: float = 12.0,
    background_color: tuple[float, float, float] | None = None,
) -> str:
    """Convenience: convert a single OpsSet to a tikzpicture string."""
    renderer = TikZRenderer(viewport, target_width_cm, background_color)
    return renderer.render_tikzpicture(opsset)
