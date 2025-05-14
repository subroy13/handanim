from typing import List, Tuple
import xml.etree.ElementTree as ET
from svgpathtools import parse_path, Line, QuadraticBezier, CubicBezier, Path
from ..core.draw_ops import Ops, OpsType, OpsSet
from ..core.drawable import Drawable


class SVG(Drawable):
    """
    A drawable class that takes either an SVG file path
    or an SVG string and renders it as a Drawable.
    """

    def __init__(
        self,
        svg_paths: List[str],
        position: Tuple[float, float] = (0, 0),
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.svg_paths = svg_paths
        self.position = position

    @classmethod
    def from_svg_file(cls, svg_file_path: str, *args, **kwargs):
        """
        Reads an SVG file and returns its contents as a string.
        """
        tree = ET.parse(svg_file_path)
        root = tree.getroot()

        # Sometimes vtracer does not explicitly include namespaces — handle both cases
        paths = []
        for elem in root.iter():
            if elem.tag.endswith("path"):
                d_attr = elem.attrib.get("d")
                if d_attr:
                    paths.append(d_attr)
        return cls(svg_paths=paths, *args, **kwargs)

    def get_path_structures(
        self, path: Path, initial_point=(0, 0)
    ) -> Tuple[OpsSet, Tuple[float, float]]:
        """
        Parse a path string into a list of paths
        """
        opsset = OpsSet(initial_set=[])
        current_point = initial_point
        for segment in path:
            if isinstance(segment, Line):
                # line segment, has start and end
                start = segment.start
                end = segment.end
                if start.real != current_point[0] or start.imag != current_point[1]:
                    # need to move
                    opsset.add(
                        Ops(
                            OpsType.MOVE_TO,
                            [(start.real, start.imag)],
                        )
                    )
                opsset.add(Ops(OpsType.LINE_TO, [(end.real, end.imag)]))
                current_point = (end.real, end.imag)
            elif isinstance(segment, QuadraticBezier):
                # quadratic bezier, has start, control, and end
                start = segment.start
                control = segment.control
                end = segment.end
                if start.real != current_point[0] or start.imag != current_point[1]:
                    # need to move
                    opsset.add(
                        Ops(
                            OpsType.MOVE_TO,
                            [(start.real, start.imag)],
                        )
                    )
                opsset.add(
                    Ops(
                        OpsType.QUAD_CURVE_TO,
                        [(control.real, control.imag), (end.real, end.imag)],
                    )
                )
                current_point = (end.real, end.imag)
            elif isinstance(segment, CubicBezier):
                # cubic bezier, has start, control1, control2, and end
                start = segment.start
                control1 = segment.control1
                control2 = segment.control2
                end = segment.end
                if start.real != current_point[0] or start.imag != current_point[1]:
                    # need to move
                    opsset.add(
                        Ops(
                            OpsType.MOVE_TO,
                            [(start.real, start.imag)],
                        )
                    )
                opsset.add(
                    Ops(
                        OpsType.CURVE_TO,
                        [
                            (control1.real, control1.imag),
                            (control2.real, control2.imag),
                            (end.real, end.imag),
                        ],
                    )
                )
                current_point = (end.real, end.imag)
            else:
                raise ValueError(f"Unsupported path segment type: {type(segment)}")
        return opsset, current_point

    def get_bbox(self) -> Tuple[float, float, float, float]:
        min_x, min_y, max_x, max_y = (
            float("inf"),
            float("inf"),
            -float("inf"),
            -float("inf"),
        )
        for path_str in self.svg_paths:
            path = parse_path(path_str)
            xmin, xmax, ymin, ymax = path.bbox()  # update bounding boxes
            min_x = min(min_x, xmin)
            max_x = max(max_x, xmax)
            min_y = min(min_y, ymin)
            max_y = max(max_y, ymax)
        return min_x, min_y, max_x, max_y

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

        current_point = self.position
        for path_str in self.svg_paths:
            path = parse_path(path_str)
            ops, end_point = self.get_path_structures(path, initial_point=current_point)
            opsset.extend(ops)
            current_point = end_point

        return opsset
