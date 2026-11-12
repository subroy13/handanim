Scenes, Viewports & Camera
==========================

The :class:`~handanim.core.scene.Scene` class is the central orchestrator of every ``handanim`` animation.

Creating a Scene
----------------

By default, ``Scene`` initializes a ``1280 × 720`` landscape canvas at ``24 fps`` with a white background:

.. code-block:: python

   from handanim import Scene, Viewport

   # Standard 16:9 landscape scene
   scene = Scene(width=1280, height=720, fps=24, background_color=(1.0, 1.0, 1.0))

   # 9:16 portrait scene (e.g. YouTube Shorts / Reels / TikTok)
   portrait_scene = Scene(
       width=1080,
       height=1920,
       fps=30,
       background_color=(0.98, 0.96, 0.91),
   )
   portrait_scene.set_viewport_to_identity()

World Coordinates vs. Screen Pixels (:class:`~handanim.core.viewport.Viewport`)
-------------------------------------------------------------------------------

A :class:`~handanim.core.viewport.Viewport` maps logical **world coordinates** (`world_xrange`, `world_yrange`) to physical **screen pixel dimensions** (`screen_width`, `screen_height`).

- **Identity Viewport**: ``scene.set_viewport_to_identity()`` maps `(0, width) × (0, height)` directly 1:1 to screen pixels.
- **Resolution-Independent Preview**: You can author all coordinates in `1080 × 1920` world units while rendering fast previews at `360 × 640` or `540 × 960`:

.. code-block:: python

   preview_viewport = Viewport(
       world_xrange=(0, 1080),
       world_yrange=(0, 1920),
       screen_width=360,
       screen_height=640,
       margin=0,
   )
   scene = Scene(width=360, height=640, fps=24, viewport=preview_viewport)

Camera Pan & Zoom (:class:`~handanim.animations.camera.CameraAnimation`)
------------------------------------------------------------------------

Use ``scene.add_camera(CameraAnimation(...))`` to smoothly pan or zoom the viewport across the world canvas over time:

.. code-block:: python

   from handanim import CameraAnimation, ease_in_out

   # Zoom into the region x=[200..880], y=[400..1520] between t=1.5s and t=3.5s
   scene.add_camera(
       CameraAnimation(
           start_time=1.5,
           duration=2.0,
           easing_fun=ease_in_out,
           data={
               "to_xrange": (200, 880),
               "to_yrange": (400, 1520),
           },
       )
   )

Camera-Independent Overlay Layer (``scene.overlay``)
----------------------------------------------------

Any drawable added through ``scene.overlay.add(...)`` (or ``scene.add(..., overlay=True)``) is rendered under the scene's static base viewport **after** camera-transformed world objects. This ensures titles, watermarks, progress bars, and :class:`~handanim.primitives.captions.Captions` stay fixed on screen even while :class:`~handanim.animations.camera.CameraAnimation` pans or zooms:

.. code-block:: python

   from handanim import Captions, Show, Text

   banner = Text("Episode 1: Geometry", position=(540, 80), font_size=42, align="center")
   scene.overlay.add(Show(0.0), banner)

   captions = Captions(narration_clip, words_per_chunk=3, y=1590)
   scene.overlay.add(captions)

Relative Placement & Coordinate Helpers
---------------------------------------

Every :class:`~handanim.core.drawable.Drawable` exposes bounding-box anchors and alignment helpers so you rarely need manual coordinate arithmetic:

- ``drawable.anchor(name)``: Returns `(x, y)` for ``"center"``, ``"top_left"``, ``"top"``, ``"top_right"``, ``"left"``, ``"right"``, ``"bottom_left"``, ``"bottom"``, or ``"bottom_right"``.
- ``drawable.center_at(x, y)`` (or ``drawable.centred(x, y)``): Returns a translated copy centered at `(x, y)`.
- ``drawable.align_to(x, y, anchor="top_left")``: Aligns the specified anchor of the drawable to `(x, y)`.
- ``scene.place_relative(drawable_b, drawable_a, anchor_b="top", anchor_a="bottom", offset=(0, 20))``: Places `drawable_b` relative to `drawable_a`.

