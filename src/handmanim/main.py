from handmanim.scene import Scene
from handmanim.primitives import Line
from handmanim.constants import RoughOptions

scene = Scene(width=800, height=600, background_color=(1, 1, 1))
scene.add(
    Line(
        start=(100, 400),
        end=(500, 200),
        stroke_width=1,
        stroke_color=(1, 0, 0),
        options=RoughOptions(roughness=5),
    )
)
scene.render("output.svg")
