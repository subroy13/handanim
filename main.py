import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent / "src"))

from handmanim.scene import Scene
from handmanim.primitives.rectangle import Rectangle

scene = Scene(width=300, height=300)
scene.add(Rectangle(100, 100, 150, 120, stroke_color=(0, 0, 1), fill_color=(1, 0, 0), roughness=1.5, pastel=True))
scene.render("output.png")
