from typing import Tuple
import cairo


class Viewport:
    """
    A viewport that transforms mathematical coordinates to pixel coordinates for rendering.

    Handles scaling and translation between world coordinates and screen pixels,
    ensuring proper mapping and centering within a specified margin.

    Attributes:
        world_xrange (Tuple[float, float]): The x-coordinate range in world space.
        world_yrange (Tuple[float, float]): The y-coordinate range in world space.
        screen_width (int): The width of the rendering surface in pixels.
        screen_height (int): The height of the rendering surface in pixels.
        margin (int): The margin around the rendered content.
    """

    def __init__(
        self,
        world_xrange: Tuple[float, float],
        world_yrange: Tuple[float, float],
        screen_width: int = 1920,
        screen_height: int = 1080,
        margin: int = 50,
    ):
        self.world_xrange = world_xrange
        self.world_yrange = world_yrange
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.margin = margin

    def apply_to_context(self, ctx: cairo.Context):
        """
        Apply the scaling and translation to the cairo context
        so that drawing in world coordinates will map to screen pixels
        """
        world_width = self.world_xrange[1] - self.world_xrange[0]
        world_height = self.world_yrange[1] - self.world_yrange[0]

        scale_x = (self.screen_width - self.margin * 2) / world_width
        scale_y = (self.screen_height - self.margin * 2) / world_height
        scale = min(scale_x, scale_y)  # scale to fit the smaller dimension

        # translation to account for margin and centering
        ctx.translate(self.margin, self.margin)
        ctx.scale(scale, scale)
