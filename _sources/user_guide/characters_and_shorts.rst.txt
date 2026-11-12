Character Rigs, Poses & 2-Joint IK
==================================

Recurring characters make short-form explainers feel like stories rather than static slides. :mod:`handanim.primitives.character` and :mod:`handanim.animations.pose` provide hierarchical parent-child transform trees, analytic 2-joint inverse kinematics (IK), swappable expression slots, and keyframe-blending pose animations.

Hierarchical ``RigNode`` & ``CharacterRig``
-------------------------------------------

A :class:`~handanim.primitives.character.RigNode` is a transform group with its own ``pivot``, ``angle`` (degrees), ``offset``, and ``scale``. Child nodes inherit their parent's transform via forward kinematics—so rotating an upper arm around the shoulder automatically carries the forearm and hand with it, and tilting the head carries the eyes and mouth.

.. note::

   ``RigNode`` automatically caches the base ``OpsSet`` of its static child primitives once, preventing random ``SketchStyle`` roughness or hachure lines from "boiling" (re-sampling jitter) across frames during :class:`~handanim.animations.pose.PoseAnimation`.

Building a Character with Swappable Eyes/Mouth & IK Limbs
---------------------------------------------------------

- :class:`~handanim.primitives.character.VariantSlot`: Holds named drawable variants (e.g. ``eyes={"open": ..., "blink": ..., "wink": ...}``, ``mouth={"neutral": ..., "talk": ..., "smile": ...}``) attached to a parent ``RigNode``.
- :class:`~handanim.primitives.character.TwoJointLimb`: Creates a two-bone chain (e.g. ``upper_arm`` + ``forearm``) and uses :func:`~handanim.primitives.character.solve_two_joint_ik` (2D law-of-cosines solver) to reach for any target `(x, y)` coordinate.

.. code-block:: python

   from handanim import (
       CharacterRig, Circle, Curve, Line, Pose, PoseAnimation, Show, SketchStyle, VariantSlot,
   )

   clean = SketchStyle(roughness=0.25, bowing=0.2)

   rig = CharacterRig(pivot=(540, 960))
   torso = rig.root.add_child("torso", pivot=(540, 960), drawables=[
       Line((540, 720), (540, 960), sketch_style=clean),
   ])

   head = torso.add_child("head", pivot=(540, 720), drawables=[
       Circle(center=(540, 650), radius=65, sketch_style=clean),
   ])

   # Swappable eye & mouth slots attached to the head node
   eyes = VariantSlot(
       "eyes",
       pivot=(540, 640),
       variants={
           "open": [Circle((520, 640), 7, sketch_style=clean), Circle((560, 640), 7, sketch_style=clean)],
           "blink": [Line((512, 640), (528, 640), sketch_style=clean), Line((552, 640), (568, 640), sketch_style=clean)],
       },
       default="open",
   )
   head.add_slot(eyes)

   # Two-joint right arm with analytic IK reaching support
   right_arm = rig.add_two_joint_limb(
       "right_arm",
       parent=torso,
       root_pivot=(540, 750),
       length1=110.0,
       length2=100.0,
       bend_direction=1,
   )

Blending Poses with :class:`~handanim.animations.pose.PoseAnimation`
--------------------------------------------------------------------

Define :class:`~handanim.primitives.character.Pose` snapshots (specifying joint angles, node offsets, IK targets, and active slot variants) and interpolate smoothly between them over time using :class:`~handanim.animations.pose.PoseAnimation`:

.. code-block:: python

   # Neutral starting pose
   pose_idle = rig.capture_pose()

   # Wave & point at (720, 640) while smiling/blinking
   pose_point = Pose(
       angles={"head": -8.0},
       ik_targets={"right_arm": (720, 640)},
       variants={"eyes": "blink"},
   )

   scene.add(Show(0.0), rig)
   scene.add(
       PoseAnimation(
           rig=rig,
           keyframes=[
               (0.0, pose_idle),
               (0.8, pose_point),
               (1.6, pose_idle),
           ],
           start_time=0.5,
           duration=1.6,
       ),
       rig,
   )

