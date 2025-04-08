# import sys
# from pathlib import Path
# sys.path.append(str(Path(__file__).resolve().parent))

from handmanim.scene import Scene
from handmanim.primitives import Line, Rectangle, Ellipse, Circle

scene = Scene(width=1200, height=800)
# scene.add(Line((0, 0), (100, 200), stroke_color=(0, 0, 1), roughness=2))
scene.add(
    Rectangle(
        (50, 50),
        100,
        200,
        stroke_color=(1, 0, 0),
        roughness=2,
        fill_color=(0, 1, 0),
        fill_type="diagonal",
        fill_spacing=10,
    )
)
scene.add(
    Ellipse(
        (600, 400),
        400,
        300,
        stroke_color=(0, 1, 0),
        roughness=5.0,
        fill_color=(0, 0, 1),
        fill_type="checker",
    )
)
# scene.add(Circle((50, 50), 100, stroke_color=(0, 1, 0), roughness = 2, fill_color=None, fill_type = "checker_diagonal"))

scene.render("output.png")
