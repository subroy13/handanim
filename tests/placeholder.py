import os
import numpy as np
from handanim.core import Scene, StrokeStyle
from handanim.core.utils import get_line_slope_angle
from handanim.primitives import CurvedArrow, Curve, Arrow, Circle
from handanim.animations import SketchAnimation
from handanim.stylings.color import BLACK, WHITE

# scene = Scene(width=1920, height=1088, background_color=(1, 1, 1))  # blank scene (viewport = 1777, 1000)

start_point = (600, 500)
end_point = (100, 100)
print(get_line_slope_angle(start_point, end_point))

arrow = Arrow(
    start_point=start_point, end_point=end_point, stroke_style=StrokeStyle(color=WHITE, width=10), arrow_head_size=50
)
circle = Circle(center=start_point, radius=100, stroke_style=StrokeStyle(color=WHITE, width=10, opacity=1))

opsset = circle.draw()
opsset.extend(arrow.draw())
# print(opsset)
opsset.quick_view(background_color=BLACK)

# arrow = CurvedArrow(
#     points=pts,
#     arrow_head_size=50,
#     arrow_head_type="->>",
# )
# scene.add(event=SketchAnimation(start_time=0.25, duration=1.5), drawable=arrow)


# # save as gif
# output_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test.gif")
# scene.render(output_path, max_length=2)
