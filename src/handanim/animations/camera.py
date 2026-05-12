
from ..core.animation import AnimationEvent, AnimationEventType
from ..core.draw_ops import OpsSet
from ..core.viewport import Viewport


class CameraAnimation(AnimationEvent):
    """
    Animates the Scene viewport (pan and/or zoom) over time.

    Instead of touching any drawable's OpsSet, this animation changes the world
    ranges that the Viewport maps to the screen — the "camera" moves, not the content.

    Args:
        start_time: When the animation begins (seconds).
        duration: Length of the animation (seconds).
        easing_fun: Optional easing function applied to progress.
        data: Dict with optional keys:
            - "from_xrange" (tuple[float, float]): World x range at progress=0.
              Defaults to wherever the camera currently is.
            - "from_yrange" (tuple[float, float]): World y range at progress=0.
              Defaults to wherever the camera currently is.
            - "to_xrange"   (tuple[float, float]): World x range at progress=1.
              Defaults to from_xrange (no movement on x).
            - "to_yrange"   (tuple[float, float]): World y range at progress=1.
              Defaults to from_yrange (no movement on y).

    Usage::

        scene.add_camera(CameraAnimation(
            start_time=5, duration=3,
            data={
                "to_xrange": (400, 800),
                "to_yrange": (200, 600),
            }
        ))
    """

    def __init__(self, start_time=0.0, duration=0.0, easing_fun=None, data=None):
        super().__init__(AnimationEventType.MUTATION, start_time, duration, easing_fun, data)

    def _apply(self, opsset: OpsSet, progress: float) -> OpsSet:
        # CameraAnimation operates on the Viewport, not on OpsSets.
        # Returning the opsset unchanged makes it safe if mistakenly used with scene.add().
        return opsset

    def apply_to_viewport(self, current: Viewport, progress: float) -> Viewport:
        """
        Return a new Viewport interpolated toward the target world ranges.

        Args:
            current: The viewport state immediately before this event (used as
                     the from_* default when not explicitly specified).
            progress: Animation progress from 0.0 to 1.0.

        Returns:
            A new Viewport instance with interpolated world ranges.
        """
        from_xrange: tuple[float, float] = self.data.get("from_xrange", current.world_xrange)
        from_yrange: tuple[float, float] = self.data.get("from_yrange", current.world_yrange)
        to_xrange: tuple[float, float] = self.data.get("to_xrange", from_xrange)
        to_yrange: tuple[float, float] = self.data.get("to_yrange", from_yrange)

        new_xrange = (
            (1 - progress) * from_xrange[0] + progress * to_xrange[0],
            (1 - progress) * from_xrange[1] + progress * to_xrange[1],
        )
        new_yrange = (
            (1 - progress) * from_yrange[0] + progress * to_yrange[0],
            (1 - progress) * from_yrange[1] + progress * to_yrange[1],
        )

        return Viewport(
            world_xrange=new_xrange,
            world_yrange=new_yrange,
            screen_width=current.screen_width,
            screen_height=current.screen_height,
            margin=current.margin,
        )
