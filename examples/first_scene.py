import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from handmanim.scene import Scene
from handmanim.primitives.shapes import Circle
from handmanim.primitives.text import Text

scene = Scene()
scene.add(Circle(center=(0, 0), radius=1))
scene.play(Text("Hello world!", style="handwritten"))
scene.render("out.mp4")
