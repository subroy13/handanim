import os
from handanim.core import Scene
from handanim.primitives import Arrow
from handanim.animations import SketchAnimation

scene = Scene(width=1920, height=1088, background_color=(1, 0.9, 0.9))  # blank scene (viewport = 1777, 1000)

arrow = Arrow(
    start_point=(50, 100),
    end_point=(700, 1000),
    arrow_head_size=50,
    arrow_head_type="->>"
)
scene.add(
    event = SketchAnimation(start_time=0.25, duration=1.5),
    drawable=arrow
)


# save as gif
output_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test.gif")
scene.render(output_path, max_length=2)
