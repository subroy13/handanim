Theme 6: Scientific Storytelling & Academic LaTeX/TikZ Export
=============================================================

``handanim`` supports multi-scene scientific storytelling on dark-mode chalkboards as well as zero-dependency academic export to compilable **LaTeX Beamer slide decks** (inline native TikZ or Cairo PDF overlays), standalone TikZ figures, multi-page PDF handouts, and SVG/PDF storyboards.

.. tip::

   To regenerate these tutorials locally:

   .. code-block:: bash

      poetry run python docs/source/gallery/build_gallery.py --only solar_system
      poetry run python docs/source/gallery/build_gallery.py --only tikz_beamer

----

Tutorial 6.1: The Solar System — Dark-Mode Blackboard Journey
-------------------------------------------------------------

**Use Case:** Build a multi-act astronomy explainer on a black chalkboard (`background_color=BLACK`) using off-screen planet translation (`planet.translate(...)`), parallel group zooming (:class:`~handanim.core.drawable.DrawableGroup` with ``grouping_method="parallel"``), Earth–Moon–Sun scale comparisons, and a procedural starfield reveal.

.. raw:: html

   <div class="tutorial-media">
     <video controls loop muted playsinline width="680" src="../_static/gallery/solar_system_journey.mp4"></video>
     <p><em>Multi-scene dark-mode blackboard journey through the Solar System.</em></p>
   </div>

Complete Tutorial Code
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import numpy as np
   from handanim.animations import (
       FadeInAnimation, FadeOutAnimation, SketchAnimation,
       TranslateToAnimation, ZoomOutAnimation,
   )
   from handanim.core import DrawableGroup, FillStyle, Scene, SketchStyle, StrokeStyle
   from handanim.primitives import Arrow, Circle, Eraser, Line, Text
   from handanim.stylings.color import (
       BLACK, BLUE, ERASER_HINT_COLOR, GRAY, LIGHT_GRAY, ORANGE, RED, WHITE, YELLOW,
   )

   scene = Scene(width=1920, height=1088, background_color=BLACK)
   scene.set_viewport_to_identity()

   text_style = StrokeStyle(color=WHITE)
   planet_sketch = SketchStyle(roughness=2)

   # --- Act 1: Title & Sun ---
   title = Text("The Solar System", position=(960, 500), font_size=72, stroke_style=text_style)
   subtitle = Text("A Journey Through Space and Scale", position=(960, 600), font_size=36, stroke_style=text_style)
   scene.add(FadeInAnimation(start_time=0.0, duration=1.0), drawable=title)
   scene.add(FadeInAnimation(start_time=0.5, duration=1.0), drawable=subtitle)

   eraser = Eraser(
       objects_to_erase=[title, subtitle],
       drawable_cache=scene.drawable_cache,
       glow_dot_hint={"color": ERASER_HINT_COLOR, "radius": 10},
       stroke_style=StrokeStyle(color=BLACK),
   )
   scene.add(SketchAnimation(start_time=2.0, duration=0.5), drawable=eraser)

   sun = Circle(
       center=(960, 600), radius=80,
       stroke_style=StrokeStyle(color=WHITE),
       fill_style=FillStyle(color=YELLOW, hachure_gap=10),
       sketch_style=planet_sketch, id="sun",
   )
   scene.add(SketchAnimation(start_time=2.5, duration=2.0), drawable=sun)

   # --- Act 2: Planet Orbits ---
   planet_data = [
       ("Mercury", 150, 6, GRAY),
       ("Venus", 180, 9, ORANGE),
       ("Earth", 215, 10, BLUE),
       ("Mars", 260, 7, RED),
       ("Jupiter", 380, 25, LIGHT_GRAY),
       ("Saturn", 480, 22, LIGHT_GRAY),
       ("Uranus", 560, 15, LIGHT_GRAY),
       ("Neptune", 620, 14, LIGHT_GRAY),
   ]
   planet_drawables = []
   start_time = 4.0
   for name, orbit_radius, planet_radius, color in planet_data:
       planet = Circle(
           center=(960 + orbit_radius, 600),
           radius=planet_radius,
           stroke_style=StrokeStyle(color=WHITE),
           fill_style=FillStyle(color=color, hachure_gap=6),
           sketch_style=planet_sketch,
       )
       planet_for_anim = planet.translate(offset_x=-(1200 + orbit_radius), offset_y=0)
       orbit = Circle(center=(960, 600), radius=orbit_radius, stroke_style=StrokeStyle(color=WHITE, width=1))

       scene.add(SketchAnimation(start_time=start_time, duration=0.1), drawable=planet_for_anim)
       scene.add(SketchAnimation(start_time=start_time, duration=1.0), drawable=orbit)
       scene.add(
           TranslateToAnimation(
               start_time=start_time + 0.1,
               duration=1.0,
               data={"point": (960 + orbit_radius, 600)},
           ),
           drawable=planet_for_anim,
       )
       planet_drawables.extend([planet_for_anim, orbit])
       start_time += 1.0

   # --- Act 3: Parallel Group ZoomOut & Starfield ---
   planetary_system = DrawableGroup(elements=[sun, *planet_drawables], grouping_method="parallel")
   scene.add(ZoomOutAnimation(start_time=13.0, duration=2.0, data={"factor": 0.2}), drawable=planetary_system)
   scene.add(FadeOutAnimation(start_time=13.0, duration=2.0), drawable=planetary_system)

   rng = np.random.default_rng(42)
   stars = [
       Circle(
           center=(int(rng.integers(50, 1870)), int(rng.integers(50, 1038))),
           radius=float(rng.uniform(1, 3)),
           stroke_style=StrokeStyle(color=WHITE),
       )
       for _ in range(80)
   ]
   for i, star in enumerate(stars):
       scene.add(FadeInAnimation(start_time=15.0 + i * 0.02, duration=0.8), drawable=star)

   final_msg = Text(
       "This is the only home known to us — let's protect it.",
       position=(960, 540), font_size=48, stroke_style=text_style,
   )
   scene.add(SketchAnimation(start_time=16.5, duration=1.5), drawable=final_msg)

   scene.render("solar_system_journey.mp4", max_length=19)

----

Tutorial 6.2: Exporting to LaTeX Beamer Slides, Native TikZ & Handouts
----------------------------------------------------------------------

**Use Case:** Convert any ``handanim`` scene into a compilable **LaTeX Beamer presentation** with ``\only<N>{...}`` step overlays (:meth:`~handanim.core.scene.Scene.export_beamer`), a standalone ``tikzpicture`` (:meth:`~handanim.core.scene.Scene.render_tikz`), or a multi-page PDF lecture handout (:meth:`~handanim.core.scene.Scene.render_handout`).

Complete Tutorial Code
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from handanim.animations import SketchAnimation
   from handanim.core import FillStyle, Scene, SketchStyle, StrokeStyle
   from handanim.primitives import Line, NGon, Rectangle, Text
   from handanim.stylings.color import BLACK, BLUE, RED

   scene = Scene(width=1920, height=1088)

   title = Text(
       text="TikZ Export Demo",
       position=(400, 100),
       font_size=120,
       stroke_style=StrokeStyle(color=BLUE, width=2),
   )
   scene.add(SketchAnimation(duration=2.0), drawable=title)

   triangle = NGon(
       center=(500, 500),
       radius=200,
       n=3,
       stroke_style=StrokeStyle(color=RED, width=2),
       fill_style=FillStyle(color=(1.0, 0.9, 0.85)),
       sketch_style=SketchStyle(roughness=2),
   )
   scene.add(SketchAnimation(start_time=2.0, duration=2.0), drawable=triangle)

   rect = Rectangle(
       top_left=(900, 350),
       width=350,
       height=250,
       stroke_style=StrokeStyle(color=BLACK, width=2),
       fill_style=FillStyle(color=(0.85, 0.92, 1.0)),
       sketch_style=SketchStyle(roughness=1.5),
   )
   scene.add(SketchAnimation(start_time=4.0, duration=2.0), drawable=rect)

   connector = Line(start=(700, 500), end=(900, 475), stroke_style=StrokeStyle(color=BLACK, width=1.5))
   scene.add(SketchAnimation(start_time=6.0, duration=1.0), drawable=connector)

   label = Text("Native LaTeX!", position=(950, 700), font_size=60, stroke_style=StrokeStyle(color=BLUE, width=1.5))
   scene.add(SketchAnimation(start_time=7.0, duration=1.5), drawable=label)

   # 1. Native TikZ Beamer deck (zero external image files, pure LaTeX vector paths)
   tex_path = scene.export_beamer(
       "output/tikz_beamer",
       n_frames=6,
       backend="tikz",
       title="Handanim TikZ Demo",
   )

   # 2. Standalone single-frame TikZ figure (.tex)
   scene.render_tikz("output/tikz_standalone.tex", time=8.5)

   # 3. Multi-page PDF lecture handout
   scene.render_handout("output/lecture_handout.pdf", n_frames=6)
