from handmanim.scene import Scene
from handmanim.primitives import Line, Circle, Ellipse
from handmanim.constants import RoughOptions

scene = Scene(width=500, height=500, background_color=(1, 1, 1))
radius_list = [25, 50, 100, 200]
for r in radius_list:
    scene.add(
        Ellipse(
            center=(250, 250),
            height=r,
            width=2 * r,
            stroke_width=1,
            stroke_color=(1, 0, 0),
            options=RoughOptions(roughness=1),
        )
    )

scene.render("output.svg")
