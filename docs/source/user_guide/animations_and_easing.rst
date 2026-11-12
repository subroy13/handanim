Animations, Visibility & Easing
===============================

``handanim`` provides a full suite of creation, mutation, and deletion animations in :mod:`handanim.animations`.

Creation & Reveal Animations
----------------------------

- :class:`~handanim.animations.sketch.SketchAnimation`: Progressively draws strokes and fills along their path over ``duration`` seconds.
- :class:`~handanim.animations.fade.FadeInAnimation`: Scales the drawable's base opacity from ``initial_opacity`` (default ``0.0``) up to ``1.0 × base_opacity``.

  - Passing ``initial_opacity=0.25`` at ``start_time=0.0`` ensures a hook object is already partially visible on frame 0.
  - Fading in an object that previously faded out automatically restores its original ``base_opacity``.

- :class:`~handanim.animations.easing.PopAnimation`: Scales an object from ``initial_scale`` (default ``0.01``) to ``1.0`` around its center of gravity using :func:`~handanim.animations.easing.ease_out_back` for a springy overshoot pop-in effect.
- :class:`~handanim.animations.zoom.ZoomInAnimation`: Smoothly scales an object from 0 to full size.

Instant Visibility Toggles (:class:`~handanim.animations.visibility.Show`, :class:`~handanim.animations.visibility.Hide`, :class:`~handanim.animations.visibility.Swap`)
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

For frame-accurate hooks, eye blinks, mouth swaps, and step-by-step callouts:

.. code-block:: python

   from handanim import Hide, Show, Swap

   # Visible immediately on frame 0
   scene.add(Show(0.0), hook_banner)

   # Instant blink toggle
   scene.add(Show(1.2), closed_eyelid)
   scene.add(Hide(1.32), closed_eyelid)

   # Atomically swap drawable A for drawable B at t=2.0s (or cross-fade with duration=0.25)
   scene.add(Swap(pose_a, pose_b, start_time=2.0))
   # Or via the Scene shorthand:
   scene.swap(pose_b, pose_a, start_time=3.5, duration=0.2)

Motion & Mutation Animations
----------------------------

- :class:`~handanim.animations.translate.TranslateToAnimation` / :class:`~handanim.animations.translate.TranslateFromAnimation`: Moves an object to or from a target point (`data={"point": (dx, dy)}`).
- :class:`~handanim.animations.rotate.RotateAnimation`: Rotates an object by `angle` degrees around its center of gravity or a custom pivot point.
- :class:`~handanim.animations.color_transition.ColorTransitionAnimation`: Smoothly interpolates stroke/fill color toward a target RGB color.
- :class:`~handanim.animations.fade.FadeOutAnimation` and :class:`~handanim.animations.zoom.ZoomOutAnimation`: Smoothly removes an object from the scene.

Built-In Easing Functions (:mod:`handanim.animations.easing`)
-------------------------------------------------------------

Every :class:`~handanim.core.animation.AnimationEvent` accepts an ``easing_fun`` callable mapping ``t in [0.0, 1.0] -> float``. ``handanim`` exports ready-to-use easing functions at the top level:

- **Linear & Polynomial**:
  :func:`~handanim.animations.easing.linear`,
  :func:`~handanim.animations.easing.ease_in_quad`,
  :func:`~handanim.animations.easing.ease_out_quad`,
  :func:`~handanim.animations.easing.ease_in_out_quad`,
  :func:`~handanim.animations.easing.ease_in_cubic`,
  :func:`~handanim.animations.easing.ease_out_cubic`,
  :func:`~handanim.animations.easing.ease_in_out_cubic`,
  :func:`~handanim.animations.easing.ease_in_out`
- **Spring, Overshoot & Bounce**:
  :func:`~handanim.animations.easing.ease_in_back`,
  :func:`~handanim.animations.easing.ease_out_back`,
  :func:`~handanim.animations.easing.ease_in_out_back`,
  :func:`~handanim.animations.easing.ease_out_elastic`,
  :func:`~handanim.animations.easing.ease_out_bounce`

.. code-block:: python

   from handanim import TranslateFromAnimation, ease_out_back

   scene.add(
       TranslateFromAnimation(
           start_time=0.5,
           duration=0.7,
           data={"point": (0, 200)},
           easing_fun=ease_out_back,
       ),
       card,
   )

Grouping Drawables (:class:`~handanim.core.drawable.DrawableGroup`)
-------------------------------------------------------------------

Combine multiple drawables into a :class:`~handanim.core.drawable.DrawableGroup` to animate them either simultaneously (``grouping="parallel"``) or one after another (``grouping="series"``):

.. code-block:: python

   from handanim import DrawableGroup, SketchAnimation

   steps = DrawableGroup([step1, step2, step3], grouping="series")
   # Subdivides the 3.0s SketchAnimation into three 1.0s sequential reveals
   scene.add(SketchAnimation(start_time=1.0, duration=3.0), steps)

Scene Transitions (:class:`~handanim.animations.transitions.PageTurnTransition` & :class:`~handanim.animations.transitions.PaperCrumpleTransition`)
---------------------------------------------------------------------------------------------------------------------------------------------------

Use scene-level transitions (:class:`~handanim.animations.transitions.SceneTransition`) to turn the drawing board page or crumple the current sheet of paper and toss it aside to reveal a fresh page underneath.

**How Multi-Page Transitions Work:**

- Any world-space drawable created before ``transition.start_time`` belongs to the **outgoing page**: it is folded or crumpled during ``[transition.start_time, transition.end_time)`` and **automatically deactivated** at ``transition.end_time`` (no manual :class:`~handanim.animations.visibility.Hide` calls needed).
- Any world-space drawable created at or after ``transition.start_time`` belongs to the **incoming page** and is progressively uncovered underneath as the old sheet peels or crumples away.
- Drawables on ``scene.overlay`` (such as :class:`~handanim.primitives.captions.Captions` or persistent headers) remain completely unaffected above the transition.
- Enabling ``transition_sound=True`` on :class:`~handanim.core.scene.Scene` (or in :meth:`~handanim.core.scene.Scene.render`) automatically synthesizes and mixes open-source page-turn and paper-crumple sound effects.

1. Folding / Turning the Page (:class:`~handanim.animations.transitions.PageTurnTransition`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Peels the current page across a moving perpendicular-bisector crease line using Sutherland–Hodgman half-plane clipping, rendering the uncovered next page underneath, the remaining unfolded sheet, a soft cast shadow along the crease, and the reflected paper flap with subtle ink bleed-through on the backside:

- **Supported** ``direction`` **values**:
  ``"right_to_left"`` (default), ``"left_to_right"``, ``"bottom_right"`` (or ``"right_corner_to_left_corner"``), ``"bottom_left"`` (or ``"left_corner_to_right_corner"``), ``"top_right"``, ``"top_left"``, ``"bottom_to_top"``, ``"top_to_bottom"``.
- **Customization**: ``bleed_through=0.16`` (opacity of reflected strokes visible through the backside of the paper flap), ``flap_color``, ``border_color``, and ``shadow_opacity``.

2. Crumpling the Paper to the Side (:class:`~handanim.animations.transitions.PaperCrumpleTransition`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Grabs the current sheet of paper, crunches it (along with all strokes drawn on it) into a jagged multi-faceted paper ball (``0..52%`` of ``duration``), and tosses it along a spinning parabolic arc off to the side (``52..100%`` of ``duration``) to open up the next page:

- **Supported** ``direction`` **values**:
  ``"right"`` (default), ``"left"``, ``"top_right"``, ``"bottom_right"``, ``"top_left"``, ``"bottom_left"``.
- **Customization**: ``ball_scale=0.18`` (final radius of the crumpled ball relative to the viewport diagonal) and ``seed=42`` (deterministic facet & crease geometry).

.. code-block:: python

   from handanim import (
       Circle, PageTurnTransition, PaperCrumpleTransition,
       Rectangle, Scene, SketchAnimation, Text,
   )

   scene = Scene(sketch_sound=True, transition_sound=True)

   # Page 1: drawn at t = 0.0 .. 1.5s, then folded diagonally from bottom-right at t = 2.5 .. 3.8s
   p1_box = Rectangle(top_left=(300, 280), width=500, height=320)
   scene.add(SketchAnimation(start_time=0.0, duration=1.5), p1_box)
   scene.add(
       PageTurnTransition(
           start_time=2.5,
           duration=1.3,
           direction="bottom_right",
           bleed_through=0.20,
       )
   )

   # Page 2: drawn at t = 3.2 .. 4.8s, then crumpled into a ball and tossed right at t = 5.5 .. 6.9s
   p2_draft = Circle(center=(800, 500), radius=180)
   scene.add(SketchAnimation(start_time=3.2, duration=1.6), p2_draft)
   scene.add(
       PaperCrumpleTransition(
           start_time=5.5,
           duration=1.4,
           direction="right",
       )
   )

   # Page 3: fresh sheet revealed underneath
   p3_title = Text("Clean Final Page!", position=(888, 500), font_size=48, align="center")
   scene.add(SketchAnimation(start_time=6.2, duration=1.2), p3_title)

   scene.render("transitions.mp4")



