# Features

- [ ] Implementation of flowcharts
- [ ] Import images and videos into scene.
- [ ] Showcasing tabular data
- [ ] Add handwriting curve generating AI model

## Bug fixes to be performed

- [ ] Autofitting content based on rect boxes.
- [ ] DrawableGroup (parallel) drawing.
    * Transformations on DrawableGroup should apply w.r.t. its center of gravity.
    * Even in a drawablegroup, individual drawables can be selectively transformed.
    * Drawablegroup may not have a creation event. (Handled)
    * If a drawablegroup has a deletion event, it destroys all its children as well.
    * If a drawablegroup has an animation, then it must be applied after the persistent animations of all its children are applied first.
    * What if? 2 objects have a persistent transformation, then they are grouped -> scale 0.5 -> one object is translated. The persistent animations should apply in order.
    * Check `get_active_drawables`, `_add_and_cache_drawable` and `_get_opsset_at_time`.
