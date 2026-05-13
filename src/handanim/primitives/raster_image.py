import numpy as np
import cairo

from ..core.drawable import Drawable
from ..core.draw_ops import Ops, OpsSet, OpsType
from ..core.styles import SketchStyle, StrokeStyle


def _load_image_surface(image_path: str) -> cairo.ImageSurface:
    """Load an image file into a cairo.ImageSurface.

    Supports PNG natively. For JPEG, BMP, TIFF, etc., falls back to Pillow.
    """
    if image_path.lower().endswith(".png"):
        return cairo.ImageSurface.create_from_png(image_path)

    from PIL import Image

    img = Image.open(image_path).convert("RGBA")
    arr = np.array(img)
    # Cairo expects pre-multiplied BGRA in native byte order
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    alpha = a.astype(np.float32) / 255.0
    bgra = np.zeros((*arr.shape[:2], 4), dtype=np.uint8)
    bgra[:, :, 0] = (b * alpha).astype(np.uint8)
    bgra[:, :, 1] = (g * alpha).astype(np.uint8)
    bgra[:, :, 2] = (r * alpha).astype(np.uint8)
    bgra[:, :, 3] = a
    h, w = bgra.shape[:2]
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    buf = surface.get_data()
    flat = bgra.tobytes()
    buf[:len(flat)] = flat
    surface.mark_dirty()
    return surface


class RasterImage(Drawable):
    """A drawable that places a raster image (PNG, JPEG, etc.) into the scene.

    The image is positioned in world coordinates. If only one of width/height
    is given, the other is computed to preserve the aspect ratio.  If neither
    is given, the image's pixel dimensions are used as world-coordinate size.

    Args:
        image_path: Path to the image file.
        position: Top-left corner in world coordinates (x, y).
        width: Display width in world coordinates.
        height: Display height in world coordinates.
        opacity: Initial opacity (0.0 transparent, 1.0 opaque).
    """

    def __init__(
        self,
        image_path: str,
        position: tuple[float, float] = (0, 0),
        width: float | None = None,
        height: float | None = None,
        opacity: float = 1.0,
        **kwargs,
    ):
        kwargs.pop("stroke_style", None)
        kwargs.pop("sketch_style", None)
        super().__init__(
            stroke_style=StrokeStyle(),
            sketch_style=SketchStyle(roughness=0),
            **kwargs,
        )
        self.image_path = image_path
        self.position = position
        self.opacity = opacity

        self._surface = _load_image_surface(image_path)
        img_w = self._surface.get_width()
        img_h = self._surface.get_height()

        if width is not None and height is not None:
            self._width = width
            self._height = height
        elif width is not None:
            self._width = width
            self._height = width * (img_h / img_w)
        elif height is not None:
            self._height = height
            self._width = height * (img_w / img_h)
        else:
            self._width = float(img_w)
            self._height = float(img_h)

    def draw(self) -> OpsSet:
        ops = Ops(
            type=OpsType.IMAGE,
            data={
                "surface": self._surface,
                "x": self.position[0],
                "y": self.position[1],
                "width": self._width,
                "height": self._height,
                "opacity": self.opacity,
            },
        )
        return OpsSet(initial_set=[ops])
