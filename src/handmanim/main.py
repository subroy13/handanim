# import sys
# from pathlib import Path

# sys.path.append(str(Path(__file__).resolve().parent / "src"))

from handmanim.scene import Scene
from handmanim.primitives import Line, Rectangle

scene = Scene(width=300, height=300)
scene.add(Line((0, 0), (100, 200), stroke_color=(0, 0, 1), roughness=2))
scene.add(Rectangle((50, 50), 100, 200, stroke_color=(1, 0, 0), roughness=2, fill_color=(0, 1, 0), fill_type="diagonal", fill_spacing=10))
scene.render("output.png")
