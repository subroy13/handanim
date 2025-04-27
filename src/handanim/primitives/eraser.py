from typing import List
from ..core.drawable import Drawable, DrawableCache
from ..core.draw_ops import OpsSet, Ops, OpsType


class Eraser(Drawable):

    def __init__(
        self,
        objects_to_erase: List[Drawable],
        drawable_cache: DrawableCache,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.objects_to_erase = objects_to_erase
        self.drawable_cache = drawable_cache

    def draw(self) -> OpsSet:
        """
        Calculates the zigzag motion of the eraser
        """
        opsset = OpsSet(initial_set=[])
        opsset.add(
            Ops(
                OpsType.SET_PEN,
                {
                    "color": self.stroke_style.options.get("color", (1, 1, 1)),
                    "width": self.stroke_style.width * 10,  # make it like pastel blend
                    "opacity": self.stroke_style.opacity,
                },
            )
        )

        min_x, min_y, max_x, max_y = self.drawable_cache.calculate_bounding_box(
            self.objects_to_erase
        )

        # TODO: do the rotation, perform the zigzag motion here
        spacing = self.stroke_style.width * 10
        y = min_y
        opsset.add(Ops(OpsType.MOVE_TO, [(min_x, min_y)]))  # move to top left corner
        while y <= max_y:
            opsset.add(Ops(OpsType.LINE_TO, [(max_x, y)]))
            y += spacing
            if y <= max_y:
                # we can do zigzag motion now
                opsset.add(Ops(OpsType.LINE_TO, [(min_x, y)]))

        return opsset
