from typing import Tuple, List
import matplotlib as mpl
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MplPath

from ..core.draw_ops import Ops, OpsType, OpsSet
from ..core.drawable import Drawable
from ..stylings.fonts import get_font_path


class Math(Drawable):

    def __init__(
        self,
        tex_expression: str,
        position: Tuple[float, float],
        font_size: int = 12,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.tex_expression = tex_expression
        self.position = position
        self.font_size = font_size

    def _transform_points(
        self, points: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """
        Transforms a list of points from matplotlib coordinate system to cairo coordinate system
        """
        pos_x, pos_y = self.position
        return [(x, 2 * pos_y - y) for x, y in points]

    def convert_textpath_to_ops(self, drawpath: TextPath) -> OpsSet:
        opsset = OpsSet(initial_set=[])
        for verts, code in drawpath.iter_segments():
            if code == MplPath.MOVETO:
                opsset.add(Ops(OpsType.MOVE_TO, data=self._transform_points([verts])))
            elif code == MplPath.LINETO:
                opsset.add(Ops(OpsType.LINE_TO, data=self._transform_points([verts])))
            elif code == MplPath.CURVE3:
                opsset.add(
                    Ops(
                        OpsType.QUAD_CURVE_TO,
                        data=self._transform_points(verts.reshape(2, 2)),
                    )
                )
            elif code == MplPath.CURVE4:
                opsset.add(
                    Ops(
                        OpsType.CURVE_TO,
                        data=self._transform_points(verts.reshape(3, 2)),
                    )
                )
            elif code == MplPath.CLOSEPOLY:
                opsset.add(Ops(OpsType.CLOSE_PATH, data={}))
            else:
                raise ValueError(f"Unknown path code: {code}")
        return opsset

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
        fp = FontProperties(
            fname=get_font_path("feasibly"),
        )
        current_rcparams = mpl.rcParams.copy()
        mpl.rcParams["mathtext.fontset"] = "custom"
        mpl.rcParams["mathtext.rm"] = fp.get_name()
        mpl.rcParams["mathtext.it"] = fp.get_name()
        mpl.rcParams["mathtext.bf"] = fp.get_name()
        drawpath = TextPath(
            self.position,
            self.tex_expression,
            size=self.font_size,
            prop=fp,
            usetex=False,  # use default mathplotlib handling
        )
        mpl.rcParams = current_rcparams  # once drawing complete, reset back
        opsset.extend(self.convert_textpath_to_ops(drawpath))
        return opsset
