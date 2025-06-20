import os
import numpy as np
from handanim.core import Scene
from handanim.core.utils import get_line_slope_angle
from handanim.primitives import CurvedArrow, Curve
from handanim.animations import SketchAnimation

scene = Scene(
    width=1920, height=1088, background_color=(1, 0.9, 0.9)
)  # blank scene (viewport = 1777, 1000)
pts = [(50, 100), (200, 300), (700, 600), (700, 1000)]

end_point = pts[-1]
angle = get_line_slope_angle(pts[-2], pts[-1])
print(f"Angle of the line segment: {angle} radians")

rotation_values = [np.cos(-angle), np.sin(-angle)]

# do negative rotation for the points
rotated_points = [
    (
        end_point[0]
        + rotation_values[0] * (x - end_point[0])
        - rotation_values[1] * (y - end_point[1]),
        end_point[1]
        + rotation_values[1] * (x - end_point[0])
        + rotation_values[0] * (y - end_point[1]),
    )
    for x, y in pts
]


arrow = Curve(points=rotated_points).rotate(np.rad2deg(angle))
print(arrow.draw())

# arrow = CurvedArrow(
#     points=pts,
#     arrow_head_size=50,
#     arrow_head_type="->>",
# )
# scene.add(event=SketchAnimation(start_time=0.25, duration=1.5), drawable=arrow)


# # save as gif
# output_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test.gif")
# scene.render(output_path, max_length=2)
