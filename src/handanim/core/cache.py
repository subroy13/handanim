from typing import Optional, List, Dict, Tuple

from .draw_ops import OpsSet
from .drawable import Drawable


class DrawableCache:
    """
    A cache management class for storing and retrieving drawable objects and their corresponding operation sets.
    It caches the state of a drawable object after a choice of particular event, or at initialization.

    Provides methods to:
    - Store and retrieve drawable objects and their computed operation sets, at different key frames
    - Check for existing drawable operation sets
    - Calculate bounding boxes for multiple drawables

    Attributes:
        cache (dict[str, OpsSet]): A mapping of drawable IDs to their computed operation sets
        drawables (dict[str, Drawable]): A mapping of drawable IDs to their drawable objects
    """

    def __init__(self):
        self.cache: dict[str, OpsSet] = {}
        self.drawables: dict[str, Drawable] = {}

    def get_cachekey(self, drawable_id: str, event_id: Optional[str] = None):
        if event_id is None:
            return f"{drawable_id}__init"
        else:
            return f"{drawable_id}__{event_id}"

    def set_drawable_opsset(self, drawable: Drawable, opsset: Optional[OpsSet] = None):
        cachekey = self.get_cachekey(drawable.id)
        self.drawables[cachekey] = drawable
        if opsset is None:
            opsset = drawable.draw()
        self.cache[cachekey] = opsset  # calculate opsset and store

    def set_drawable_event_opsset(self, drawable_id: str, event_id: str, opsset: OpsSet):
        cachekey = self.get_cachekey(drawable_id, event_id)
        self.cache[cachekey] = opsset

    def get_drawable(self, drawable_id: str) -> Drawable:
        return self.drawables[drawable_id]

    def exists_in_cache(self, drawable_id: str, event_id: Optional[str] = None) -> bool:
        cachekey = self.get_cachekey(drawable_id, event_id)
        return cachekey in self.cache

    def get_drawable_opsset(self, drawable_id: str, event_id: Optional[str] = None) -> OpsSet:
        cachekey = self.get_cachekey(drawable_id, event_id)
        return self.cache.get(cachekey, OpsSet(initial_set=[]))

    def calculate_bounding_box(self, drawables: List[Drawable]):
        """
        Calculates the bounding box for a list of drawables
        stored in the cache
        """
        merge_opsset = OpsSet(initial_set=[])
        for drawable in drawables:
            merge_opsset.extend(self.get_drawable_opsset(drawable.id))
        return merge_opsset.get_bbox()


class GroupFrameCache:
    """
    Per-frame cache for group animation transforms. Must be reset at the start
    of each frame via reset(). Stores two slots per (group, event):
      - pre-transform: the assembled group OpsSet before event.apply()
      - transformed:   the result of event.apply(group_opsset, progress)
    """

    def __init__(self):
        self._pretransform: Dict[Tuple[str, str], OpsSet] = {}
        self._transformed: Dict[Tuple[str, str, int], OpsSet] = {}

    def get_pretransform(self, group_id: str, event_id: str) -> Optional[OpsSet]:
        return self._pretransform.get((group_id, event_id))

    def set_pretransform(self, group_id: str, event_id: str, opsset: OpsSet):
        self._pretransform[(group_id, event_id)] = opsset

    def get_transformed(self, group_id: str, event_id: str, progress: float) -> Optional[OpsSet]:
        return self._transformed.get((group_id, event_id, int(progress * 1000)))

    def set_transformed(self, group_id: str, event_id: str, progress: float, opsset: OpsSet):
        self._transformed[(group_id, event_id, int(progress * 1000))] = opsset

    def reset(self):
        self._pretransform.clear()
        self._transformed.clear()
