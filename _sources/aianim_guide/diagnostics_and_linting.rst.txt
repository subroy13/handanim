AST Guardrails & Headless Scene Introspection
=============================================

To help both human developers and AI agents catch layout and API mistakes early—without waiting for a full video render—``handanim`` and ``aianim`` provide two fast static/headless verification tools.

1. Static AST Code Linter (:func:`~aianim.diagnostics.check_code`)
------------------------------------------------------------------

:func:`~aianim.diagnostics.check_code` parses Python source code into an Abstract Syntax Tree (AST) and checks for ``handanim``-specific pitfalls:

- **Discarded Immutable Transforms (Error)**: Flags standalone calls like ``circle.translate(10, 20)`` or ``rect.scale(2.0)`` whose return value is not assigned (`circle = circle.translate(10, 20)`).
- **Deprecated Legacy SVG Imports (Error/Warning)**: Flags imports of legacy ``SVG`` and recommends :class:`~handanim.primitives.vector_svg.VectorSVG`.
- **Personal-Use Font Warning (`backstay`)**: Warns when ``"backstay"`` is used in code, reminding the author that *BackstaySingleLine* is licensed for personal use only and recommending ``"feasibly"`` for commercial work.
- **Missing Scene Lifecycle Calls (Warning)**: Warns if ``scene.add(...)`` or ``scene.render(...)`` / ``scene.render_snapshot(...)`` is missing.

.. code-block:: python

   from aianim.diagnostics import check_code

   report = check_code("""
   from handanim import Circle, Scene, SketchAnimation
   scene = Scene()
   c = Circle(center=(100, 100), radius=50)
   c.translate(50, 0)  # BUG: return value discarded!
   scene.add(SketchAnimation(start_time=0, duration=1), c)
   scene.render("out.mp4")
   """)

   print("Valid:", report.is_valid)
   print("Errors:", report.errors)
   print("Suggestions:", report.suggestions)

2. Headless Scene Introspection (:meth:`~handanim.core.scene.Scene.introspect`)
-------------------------------------------------------------------------------

Calling :meth:`~handanim.core.scene.Scene.introspect` evaluates the bounding boxes and timeline events of all drawables registered in a :class:`~handanim.core.scene.Scene` **without rendering any video frames**:

- Reports `min_x`, `min_y`, `max_x`, `max_y`, `width`, and `height` for every drawable.
- Emits warnings if any drawable is partially clipped or completely outside ``scene.viewport``.
- Emits warnings if any animation event extends past ``max_length``.

.. code-block:: python

   from handanim import Circle, Scene, SketchAnimation

   scene = Scene(width=1280, height=720)
   scene.set_viewport_to_identity()

   offscreen = Circle(center=(1500, 400), radius=80)
   scene.add(SketchAnimation(start_time=0.0, duration=1.0), offscreen)

   summary = scene.introspect()
   print("Total duration:", summary["duration"])
   print("Warnings:", summary["warnings"])

