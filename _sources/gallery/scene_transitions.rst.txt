Theme 4: Multi-Page Sketchbook & Scene Transitions
==================================================

``handanim`` makes multi-page storytelling effortless with first-class paper transition animations (:class:`~handanim.animations.transitions.PageTurnTransition` and :class:`~handanim.animations.transitions.PaperCrumpleTransition`) that automatically clear outgoing world-space objects once the transition completes while keeping ``scene.overlay`` elements fixed on screen.

.. tip::

   To regenerate this animation locally:

   .. code-block:: bash

      poetry run python docs/source/gallery/build_gallery.py --only scene_transitions

----

Tutorial 4.1: 3-Page Sketchbook Story (Page Turn & Paper Crumple)
-----------------------------------------------------------------

**Use Case:** Tell a 3-page visual story on warm sketchbook paper:

1. **Page 1 (0.0s – 3.0s):** Sketch a two-step concept diagram, then peel and fold the page diagonally from the bottom-right corner (:class:`~handanim.animations.transitions.PageTurnTransition`) with mirrored ink bleed-through on the backside flap.
2. **Page 2 (3.4s – 6.8s):** Sketch a "wrong draft" (``2 + 2 = 5 ???``), cross it out with red strokes, and crunch the entire page into a 3D multi-faceted paper ball that gets tossed off to the right (:class:`~handanim.animations.transitions.PaperCrumpleTransition`).
3. **Page 3 (7.2s – 10.3s):** Reveal the clean solution card underneath while the header badge pinned to ``scene.overlay`` remains untouched throughout all three pages.

.. raw:: html

   <div class="tutorial-media">
     <video controls loop playsinline width="680" src="../_static/gallery/scene_transitions_demo.mp4"></video>
     <p><em>3-page sketchbook story with PageTurnTransition, PaperCrumpleTransition, persistent overlay header, and procedural paper SFX (unmute to hear chalk, page-turn, and paper-crumple sounds!).</em></p>
   </div>

Complete Tutorial Code
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from handanim import (
       Arrow, Circle, FillStyle, Line, PageTurnTransition,
       PaperCrumpleTransition, PopAnimation, Rectangle,
       RoundedRectangle, Scene, SketchAnimation, StrokeStyle, Text,
   )

   scene = Scene(
       width=960,
       height=540,
       fps=24,
       background_color=(0.985, 0.975, 0.945),  # warm sketchbook paper
       background_music="calm",
       music_volume=0.14,
       sketch_sound=True,
       sketch_sound_volume=0.22,
       transition_sound=True,
   )

   # Persistent header in the overlay layer (stays fixed across page turns & crumples, muted sketch sound)
   header_badge = RoundedRectangle(
       top_left=(40, 22), width=420, height=52, corner_radius=12,
       stroke_style=StrokeStyle(color=(0.25, 0.23, 0.20), width=2.0),
       fill_style=FillStyle(color=(0.94, 0.92, 0.86), opacity=0.92),
   )
   header_text = Text(
       "HandAnim Sketchbook — Transitions Demo",
       position=(250, 48), font_size=20,
       stroke_style=StrokeStyle(color=(0.18, 0.16, 0.14), width=1.6),
   )
   scene.overlay.add(SketchAnimation(start_time=0.0, duration=0.5, sound=False), header_badge)
   scene.overlay.add(SketchAnimation(start_time=0.1, duration=0.5, sound=False), header_text)

   # --- PAGE 1: Idea 1 -> Folded via PageTurnTransition at t=3.0s ---
   p1_title = Text("Page 1: Turning the Drawing Board Page", position=(888, 170), font_size=38, stroke_style=StrokeStyle(color=(0.15, 0.28, 0.55), width=2.4))
   box_a = RoundedRectangle(top_left=(260, 320), width=360, height=240, corner_radius=20, stroke_style=StrokeStyle(color=(0.18, 0.35, 0.68), width=3.5), fill_style=FillStyle(color=(0.68, 0.82, 0.96), opacity=0.45))
   box_a_label = Text("Step 1: Sketch", position=(440, 440), font_size=32, stroke_style=StrokeStyle(color=(0.12, 0.24, 0.48), width=2.2))
   arrow_ab = Arrow(start_point=(650, 440), end_point=(960, 440), stroke_style=StrokeStyle(color=(0.20, 0.20, 0.20), width=3.5))
   box_b = RoundedRectangle(top_left=(990, 320), width=460, height=240, corner_radius=20, stroke_style=StrokeStyle(color=(0.18, 0.55, 0.34), width=3.5), fill_style=FillStyle(color=(0.72, 0.92, 0.78), opacity=0.45))
   box_b_label = Text("Step 2: Turn Page ->", position=(1220, 440), font_size=32, stroke_style=StrokeStyle(color=(0.12, 0.40, 0.22), width=2.2))

   scene.add(SketchAnimation(start_time=0.2, duration=0.7), p1_title)
   scene.add(SketchAnimation(start_time=0.7, duration=0.7), box_a)
   scene.add(SketchAnimation(start_time=1.0, duration=0.5), box_a_label)
   scene.add(SketchAnimation(start_time=1.3, duration=0.4), arrow_ab)
   scene.add(SketchAnimation(start_time=1.5, duration=0.7), box_b)
   scene.add(SketchAnimation(start_time=1.8, duration=0.5), box_b_label)

   scene.add(PageTurnTransition(start_time=3.0, duration=1.3, direction="bottom_right", bleed_through=0.20))

   # --- PAGE 2: "Wrong Draft" -> Crumpled via PaperCrumpleTransition at t=6.8s ---
   p2_title = Text("Page 2: Wait... This Draft Is Wrong!", position=(888, 175), font_size=38, stroke_style=StrokeStyle(color=(0.72, 0.20, 0.18), width=2.4))
   bad_circle = Circle(center=(620, 470), radius=150, stroke_style=StrokeStyle(color=(0.78, 0.25, 0.20), width=3.5), fill_style=FillStyle(color=(0.98, 0.76, 0.72), opacity=0.45))
   bad_rect = Rectangle(top_left=(920, 330), width=420, height=280, stroke_style=StrokeStyle(color=(0.75, 0.35, 0.15), width=3.5), fill_style=FillStyle(color=(0.98, 0.85, 0.68), opacity=0.45))
   bad_text = Text("2 + 2 = 5 ???", position=(1130, 470), font_size=38, stroke_style=StrokeStyle(color=(0.65, 0.15, 0.15), width=2.5))
   cross_1 = Line(start=(450, 310), end=(1380, 640), stroke_style=StrokeStyle(color=(0.82, 0.12, 0.12), width=5.0))
   cross_2 = Line(start=(1380, 310), end=(450, 640), stroke_style=StrokeStyle(color=(0.82, 0.12, 0.12), width=5.0))

   scene.add(SketchAnimation(start_time=3.5, duration=0.7), p2_title)
   scene.add(SketchAnimation(start_time=4.1, duration=0.7), bad_circle)
   scene.add(SketchAnimation(start_time=4.5, duration=0.7), bad_rect)
   scene.add(SketchAnimation(start_time=4.9, duration=0.5), bad_text)
   scene.add(SketchAnimation(start_time=5.5, duration=0.35), cross_1)
   scene.add(SketchAnimation(start_time=5.8, duration=0.35), cross_2)

   scene.add(PaperCrumpleTransition(start_time=6.8, duration=1.4, direction="right"))

   # --- PAGE 3: Fresh Sheet Underneath ---
   p3_title = Text("Page 3: Fresh Sheet — Clean Solution!", position=(888, 190), font_size=40, stroke_style=StrokeStyle(color=(0.14, 0.48, 0.28), width=2.5))
   final_card = RoundedRectangle(top_left=(420, 310), width=936, height=340, corner_radius=26, stroke_style=StrokeStyle(color=(0.16, 0.52, 0.32), width=4.0), fill_style=FillStyle(color=(0.76, 0.94, 0.82), opacity=0.5))
   final_eq = Text("PageTurnTransition + PaperCrumpleTransition", position=(888, 445), font_size=34, stroke_style=StrokeStyle(color=(0.10, 0.35, 0.20), width=2.3))

   scene.add(SketchAnimation(start_time=7.3, duration=0.7), p3_title)
   scene.add(PopAnimation(start_time=7.8, duration=0.6), final_card)
   scene.add(SketchAnimation(start_time=8.2, duration=0.8), final_eq)

   scene.render("scene_transitions_demo.mp4", max_length=10.3)
