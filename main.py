import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent / "src"))

from handmanim.scene import Scene
from handmanim.primitives.shapes import Circle
from handmanim.primitives.text import Text

scene = Scene(width=800, height=600)
scene.add(Circle(center=(400, 300), radius=100, jitter=0.1))
scene.add(Text("Hello world!", position=(300, 150), font_size=48))
scene.render("output.png")
