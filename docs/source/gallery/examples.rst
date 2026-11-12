Examples & Visual Gallery
=========================

Explore complete runnable scripts in the `examples/ <https://github.com/subroy13/handanim/tree/master/examples>`_ directory of the repository.

Mathematical Proofs & Geometry
------------------------------

1. Pythagoras Theorem (`examples/pythagoras.py`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Demonstrates polygon construction, rotated square alignment, hachure fills, and sequential :class:`~handanim.animations.sketch.SketchAnimation` reveals.

.. image:: https://raw.githubusercontent.com/subroy13/handanim/master/examples/output/pythagoras.gif
   :width: 520px
   :align: center
   :alt: Pythagoras Theorem Animation

.. code-block:: bash

   poetry run python examples/pythagoras.py

2. Visual Proof of :math:`(a + b)^2` (`examples/a_plus_b_square.py`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Demonstrates geometric partitioning of a square into :math:`a^2`, :math:`b^2`, and two :math:`ab` rectangles alongside step-by-step algebraic equations.

.. image:: https://raw.githubusercontent.com/subroy13/handanim/master/examples/output/a_plus_b_square.gif
   :width: 520px
   :align: center
   :alt: (a+b)^2 Visual Proof

.. code-block:: bash

   poetry run python examples/a_plus_b_square.py

3. Distributive Property (`examples/distributive_property.py`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Shows grouped drawable transformations, :class:`~handanim.animations.translate.TranslateToAnimation`, and equation derivations.

.. image:: https://raw.githubusercontent.com/subroy13/handanim/master/examples/output/distributive_property.gif
   :width: 520px
   :align: center
   :alt: Distributive Property Animation

Flowcharts & Diagrams
---------------------

4. Machine Learning Workflow (`examples/ml_workflow_demo.py`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Demonstrates :class:`~handanim.primitives.flowchart.FlowchartNode`, :class:`~handanim.primitives.flowchart.FlowchartDiamond`, :class:`~handanim.primitives.flowchart.FlowchartConnector`, and :class:`~handanim.primitives.table.Table` animations.

.. image:: https://raw.githubusercontent.com/subroy13/handanim/master/examples/output/ml_workflow_demo.gif
   :width: 520px
   :align: center
   :alt: ML Workflow Demo

.. code-block:: bash

   poetry run python examples/ml_workflow_demo.py

Short-Form Storytelling: Characters, Captions & Sound
-----------------------------------------------------

5. Character Rig, 2-Joint IK & Expressions (`examples/character_rig_demo.py`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Demonstrates a 9:16 portrait scene featuring:

- Hierarchical :class:`~handanim.primitives.character.CharacterRig` (`torso -> head -> eyes/mouth`)
- Analytic 2-joint inverse kinematics (:class:`~handanim.primitives.character.TwoJointLimb`) reaching for whiteboard points
- Swappable :class:`~handanim.primitives.character.VariantSlot` eye blinks (`open` / `blink` / `wink`) and mouth shapes (`neutral` / `talk` / `smile`)
- Smooth keyframe interpolation via :class:`~handanim.animations.pose.PoseAnimation`
- Instant :class:`~handanim.animations.visibility.Show`, :class:`~handanim.animations.visibility.Hide`, and :class:`~handanim.animations.visibility.Swap` events

.. code-block:: bash

   poetry run python examples/character_rig_demo.py

6. Built-In Captions, Camera Overlay & Soundtrack (`examples/captions_overlay_demo.py`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Demonstrates:

- Word-timed :class:`~handanim.primitives.captions.Captions` pinned to ``scene.overlay``
- :class:`~handanim.animations.camera.CameraAnimation` zooming into a diagram while the overlay HUD and captions remain stationary
- Repeating ``"marimba"`` background theme music (`background_music="marimba"`)
- Automatic chalk drawing sound during :class:`~handanim.animations.sketch.SketchAnimation` (`sketch_sound=True`) and board-wiping sound during :class:`~handanim.primitives.eraser.Eraser` (`eraser_sound=True`)

.. code-block:: bash

   poetry run python examples/captions_overlay_demo.py

7. Multi-Page Scene Transitions (`examples/scene_transitions_demo.py`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Demonstrates a 3-page sketchbook story using:

- :class:`~handanim.animations.transitions.PageTurnTransition` folding Page 1 from the bottom-right corner with ink bleed-through on the backside flap
- :class:`~handanim.animations.transitions.PaperCrumpleTransition` grabbing a "wrong draft" on Page 2, crunching all its strokes into a multi-faceted 3D paper ball, and tossing it off to the right to reveal Page 3
- Persistent header badge pinned to ``scene.overlay``
- Automatic ``page_turn`` and ``crumple`` procedural sound effects (`transition_sound=True`) combined with ``sketch_sound=True`` and ``background_music="calm"``

.. code-block:: bash

   poetry run python examples/scene_transitions_demo.py

8. LaTeX Beamer & Native TikZ Export (`examples/tikz_beamer_demo.py`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Demonstrates exporting an animation directly to a compilable LaTeX Beamer presentation using inline TikZ commands (:meth:`~handanim.core.scene.Scene.export_beamer`).

.. code-block:: bash

   poetry run python examples/tikz_beamer_demo.py


