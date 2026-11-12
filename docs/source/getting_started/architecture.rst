Core Architecture & Design Principles
=====================================

``handanim`` is built around a clean, stateless vector pipeline that separates geometry generation from timeline evaluation and backend rendering.

The Four-Stage Pipeline
-----------------------

.. code-block:: text

   Drawable (Immutable)
      │  .draw()
      ▼
   OpsSet (Vector Operations: MOVE_TO, LINE_TO, CURVE_TO, SET_PEN, ...)
      │  AnimationEvent.apply(opsset, progress)
      ▼
   Animated Frame OpsSet (World Ops + Camera-Invariant Overlay Ops)
      │  Viewport transform
      ▼
   Backend Renderer (Cairo PNG/MP4/SVG/PDF or Native LaTeX TikZ)

1. Immutable ``Drawable`` Objects
---------------------------------

Every shape, text block, math formula, or character rig inherits from :class:`~handanim.core.drawable.Drawable`.

- Calling ``drawable.draw()`` deterministically compiles the primitive into an :class:`~handanim.core.draw_ops.OpsSet`—a flat list of low-level vector instructions (:class:`~handanim.core.draw_ops.Ops`).
- Calling ``drawable.translate(dx, dy)``, ``drawable.scale(sx, sy)``, ``drawable.rotate(deg)``, or ``drawable.center_at(x, y)`` wraps the original drawable in a :class:`~handanim.core.drawable.TransformedDrawable` without mutating the original object.
- :class:`~handanim.core.cache.DrawableCache` caches the base ``OpsSet`` of each drawable by ID so ``draw()`` is only computed once per scene.

2. Vector ``Ops`` and ``OpsSet``
--------------------------------

An :class:`~handanim.core.draw_ops.OpsSet` is a sequence of :class:`~handanim.core.draw_ops.Ops` records. Each operation has:

- ``type`` (:class:`~handanim.core.draw_ops.OpsType`): ``SET_PEN``, ``MOVE_TO``, ``LINE_TO``, ``CURVE_TO``, ``QUAD_CURVE_TO``, ``CLOSE_PATH``, ``DOT``, ``IMAGE``, ``PUSH_CLIP``, or ``POP_CLIP``.
- ``data``: Coordinate tuples, polygon clip vertices, or pen styling dicts (``color``, ``width``, ``opacity``, ``fill``).
- ``partial`` (``float`` in ``[0, 1]``): Used by :class:`~handanim.animations.sketch.SketchAnimation` to slice cubic Bézier curves and line segments mid-stroke.
- ``meta`` (``dict``): Metadata tags for group filtering, base opacity tracking, and overlay layer routing.

3. Stateless ``AnimationEvent`` Transformations
-----------------------------------------------

Every animation (:class:`~handanim.animations.sketch.SketchAnimation`, :class:`~handanim.animations.fade.FadeInAnimation`, :class:`~handanim.animations.translate.TranslateFromAnimation`, :class:`~handanim.animations.pose.PoseAnimation`, etc.) is a pure function:

.. math::

   \text{OpsSet}_{\text{out}} = \text{event.apply}(\text{OpsSet}_{\text{in}}, \text{raw\_progress})

where ``raw_progress`` is mapped through ``event.easing_fun`` (if provided) before computing the transformed ``OpsSet``.

Events are categorized into three lifecycle types (:class:`~handanim.core.animation.AnimationEventType`):

- ``CREATION`` (e.g., ``SketchAnimation``, ``FadeInAnimation``, ``PopAnimation``, ``Show``): Makes the object visible on the timeline starting at ``start_time``.
- ``MUTATION`` (e.g., ``TranslateToAnimation``, ``RotateAnimation``, ``ColorTransitionAnimation``, ``PoseAnimation``): Modifies an active object between ``start_time`` and ``end_time``.
- ``DELETION`` (e.g., ``FadeOutAnimation``, ``Hide``): Deactivates the object at ``end_time``.

4. Two-Layer Viewport Rendering (World vs. Overlay)
---------------------------------------------------

During frame rendering, :class:`~handanim.core.scene.Scene` partitions each frame's operations into two layers:

1. **World Layer** (``scene.add(...)``): Rendered through ``scene._get_viewport_at(t)``, which interpolates any active :class:`~handanim.animations.camera.CameraAnimation` pan/zoom events. When a :class:`~handanim.animations.transitions.SceneTransition` (:class:`~handanim.animations.transitions.PageTurnTransition` or :class:`~handanim.animations.transitions.PaperCrumpleTransition`) is active, world objects are automatically partitioned into outgoing-page and incoming-page ``OpsSet``s, composed with polygonal clipping (``PUSH_CLIP`` / ``POP_CLIP``) and geometric warping, and outgoing-page objects are deactivated once ``transition.end_time`` is reached.
2. **Overlay Layer** (``scene.overlay.add(...)``): Rendered afterward through the static base ``scene.viewport``, keeping HUD elements, watermarks, and word-timed :class:`~handanim.primitives.captions.Captions` pinned on screen regardless of camera movement or page transitions.

