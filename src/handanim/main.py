from handanim.scene import Scene
from handanim.primitives import Line, Circle, Ellipse, Rectangle, Polygon, NGon
from handanim.stylings.styles import SketchStyle, StrokeStyle, FillStyle

scene = Scene(width=500, height=500, background_color=(1, 1, 1))
# scene.add(
#     NGon(
#         center=(250, 250),
#         radius=100,
#         n=5,
#         stroke_style=StrokeStyle(color=(1, 0, 0)),
#         fill_style=FillStyle(color=(0, 0, 1), hachure_gap=10),
#         sketch_style=SketchStyle(roughness=2),
#     )
# )
scene.add(
    Ellipse(
        center=(250, 250),
        height=200,
        width=500,
        stroke_style=StrokeStyle(color=(1, 0, 0)),
        fill_style=FillStyle(
            color=(0, 0, 1), opacity=0.3, hachure_gap=4, fill_pattern="solid"
        ),
        sketch_style=SketchStyle(roughness=2),
    )
)

scene.render("output.svg")
