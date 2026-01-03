"""

Vector SVG - authored by Hamd Waseem (https://github.com/hamdivazim/)

A drawable class that accepts an SVG document and renders it as a Drawable
as close to the original SVG as possible.

"""


from typing import List, Tuple, Optional, Union
from svgelements import (
    SVG as SVGParser, Path, Shape, Color, 
    Line, QuadraticBezier, CubicBezier, Move, Close
)

from ..core.drawable import Drawable
from ..core.draw_ops import OpsSet, Ops, OpsType


class VectorSVG(Drawable):
    """
    A drawable class that accepts an SVG document and renders it as a Drawable
    as close to the original SVG as possible.

    .. note:: 
       This feature was contributed by Hamd Waseem (https://github.com/hamdivazim).

    Attributes:
        svg_doc: The parsed SVG document object from svgelements.
        position (tuple[float, float]): The base (x, y) offset for the SVG.
    """

    def __init__(
        self, 
        svg_doc, 
        position: tuple[float, float] = (0, 0), 
        *args, 
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.svg_doc = svg_doc
        self.position = position

    @classmethod
    def from_svg_file(cls, svg_file_path: str, *args, **kwargs) -> "VectorSVG":
        """
        Create a VectorSVG instance from a file path
        """
        svg_doc = SVGParser.parse(svg_file_path)
        return cls(svg_doc=svg_doc, *args, **kwargs)

    def _parse_color_and_opacity(
        self, 
        color_obj
    ) -> Tuple[Optional[Tuple[float, float, float]], float]:
        """
        Converts colors to a single solid RGB tuple and alpha value
        """
        if color_obj is None:
            return None, 0.0

        # Standard color handling
        if isinstance(color_obj, Color):
            if color_obj.value is None:
                return None, 0.0
            return (
                color_obj.red / 255.0,
                color_obj.green / 255.0,
                color_obj.blue / 255.0
            ), color_obj.alpha / 255.0

        return None, 0.0

    def draw(self) -> OpsSet:
        """
        Parse SVG elements and convert them into a set of drawing operations
        """
        opsset = OpsSet(initial_set=[])
        base_x, base_y = float(self.position[0]), float(self.position[1])

        for element in self.svg_doc.elements():
            if not isinstance(element, (Shape, Path)):
                continue
            
            # skip hidden elements
            visibility = element.values.get('visibility')
            display = element.values.get('display')
            if visibility == 'hidden' or display == 'none':
                continue

            fill_rgb, fill_alpha = self._parse_color_and_opacity(element.fill)
            stroke_rgb, stroke_alpha = self._parse_color_and_opacity(element.stroke)
            
            try:
                stroke_width = float(element.stroke_width)
            except (ValueError, TypeError):
                stroke_width = 1.0

            # determine drawing operations
            operations = []
            if fill_rgb: 
                operations.append(("fill", fill_rgb, fill_alpha))
            if stroke_rgb: 
                operations.append(("stroke", stroke_rgb, stroke_alpha))
            
            if not operations:
                continue

            # handle transforms and path conversion
            path_element = Path(element) if isinstance(element, Shape) else element
            if hasattr(element, 'transform') and element.transform:
                path_element = path_element * element.transform

            path_element.approximate_arcs_with_cubics()
            
            try:
                path_segments = list(path_element.segments())
            except Exception:
                continue
                
            if not path_segments:
                continue

            # coordinate helper
            def off(p): 
                if p is None: return (0, 0)
                return (
                    getattr(p, 'x', p.real) + base_x, 
                    getattr(p, 'y', p.imag) + base_y
                )

            for mode, rgb, alpha in operations:
                opsset.add(Ops(OpsType.SET_PEN, {
                    "mode": mode, 
                    "color": rgb, 
                    "opacity": alpha, 
                    "width": stroke_width
                }))

                first_point = True
                for seg in path_segments:
                    if isinstance(seg, Move):
                        opsset.add(Ops(OpsType.MOVE_TO, [off(seg.end)]))
                        first_point = False
                        continue

                    if isinstance(seg, Close):
                        opsset.add(Ops(OpsType.CLOSE_PATH, {}))
                        continue

                    start_pos, end_pos = off(seg.start), off(seg.end)
                    if first_point:
                        opsset.add(Ops(OpsType.MOVE_TO, [start_pos]))
                        first_point = False

                    if isinstance(seg, Line):
                        opsset.add(Ops(OpsType.LINE_TO, [end_pos]))
                    elif isinstance(seg, QuadraticBezier):
                        opsset.add(Ops(OpsType.QUAD_CURVE_TO, [off(seg.control), end_pos]))
                    elif isinstance(seg, CubicBezier):
                        opsset.add(Ops(OpsType.CURVE_TO, [off(seg.control1), off(seg.control2), end_pos]))

        return opsset