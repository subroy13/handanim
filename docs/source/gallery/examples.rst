Gallery & Tutorials Showcase
============================

Welcome to the **handanim Documentation Gallery**. Every tutorial in this gallery is organized around a practical whiteboard animation theme and includes both the rendered output (GIF or MP4 with audio) and the complete, self-contained Python source code.

.. note::

   All gallery media lives inside the documentation bundle (``docs/source/_static/gallery/``) and can be regenerated at any time using the unified gallery builder script:

   .. code-block:: bash

      # List all available gallery tutorials
      poetry run python docs/source/gallery/build_gallery.py --list

      # Render a single tutorial (e.g. sketch_sound_control)
      poetry run python docs/source/gallery/build_gallery.py --only sketch_sound_control

      # Rebuild all gallery GIFs and MP4 videos
      poetry run python docs/source/gallery/build_gallery.py --all

----

Visual Gallery by Theme
-----------------------

.. raw:: html

   <div class="gallery-grid">
     <div class="gallery-item">
       <div>
         <span class="tutorial-badge">Theme 1 · Math &amp; Geometry</span>
         <img src="../_static/gallery/pythagoras.gif" alt="Pythagoras Theorem Animation">
       </div>
       <p><strong><a href="math_and_geometry.html">Mathematical Proofs &amp; Geometry</a></strong><br>
       Pythagorean theorem, visual proof of (a + b)², distributive property with SVG, and single-stroke Hershey calculus.</p>
     </div>

     <div class="gallery-item">
       <div>
         <span class="tutorial-badge">Theme 1 · Algebraic Proof</span>
         <img src="../_static/gallery/a_plus_b_square.gif" alt="(a+b)^2 Visual Proof">
       </div>
       <p><strong><a href="math_and_geometry.html#tutorial-1-2-geometric-proof-of-a-b-2-a-2-2ab-b-2">Binomial Expansion (a + b)²</a></strong><br>
       Area partitioning into a², b², and two ab rectangles with CompositeAnimationEvent &amp; flying labels.</p>
     </div>

     <div class="gallery-item">
       <div>
         <span class="tutorial-badge">Theme 2 · Flowcharts &amp; Tables</span>
         <img src="../_static/gallery/ml_workflow_demo.gif" alt="ML Workflow &amp; Table Demo">
       </div>
       <p><strong><a href="flowcharts_and_tables.html">Data Science, Flowcharts &amp; Tables</a></strong><br>
       Declarative ML training pipeline Flowchart paired with a row-by-row animated model benchmark Table.</p>
     </div>

     <div class="gallery-item">
       <div>
         <span class="tutorial-badge">Theme 3 · Character Rigging &amp; IK</span>
         <video controls loop muted playsinline src="../_static/gallery/character_rig_demo.mp4"></video>
       </div>
       <p><strong><a href="character_animation.html">2D Character Rigging &amp; 2-Joint IK</a></strong><br>
       Articulated CharacterRig with scheduled eye blinks, mouth variants, PoseAnimation, and 2-joint IK reaching targets.</p>
     </div>

     <div class="gallery-item">
       <div>
         <span class="tutorial-badge">Theme 4 · Notebook Transitions</span>
         <video controls loop muted playsinline src="../_static/gallery/scene_transitions_demo.mp4"></video>
       </div>
       <p><strong><a href="scene_transitions.html">Multi-Page Sketchbook Transitions</a></strong><br>
       3-page story using PageTurnTransition (with ink bleed-through) and PaperCrumpleTransition (3D paper ball toss).</p>
     </div>

     <div class="gallery-item">
       <div>
         <span class="tutorial-badge">Theme 5 · Sketch Sound Control</span>
         <video controls loop playsinline src="../_static/gallery/sketch_sound_control.mp4"></video>
       </div>
       <p><strong><a href="voice_captions_and_sound.html">Voice, Captions &amp; Sketch Sound Control</a></strong><br>
       Turn sketch sound on/off, tune volume per SketchAnimation or globally, and pin word-timed Captions to scene.overlay.</p>
     </div>

     <div class="gallery-item">
       <div>
         <span class="tutorial-badge">Theme 5 · 9:16 Portrait Short</span>
         <video controls loop muted playsinline style="max-height: 260px;" src="../_static/gallery/captions_overlay_demo.mp4"></video>
       </div>
       <p><strong><a href="voice_captions_and_sound.html#tutorial-5-2-built-in-captions-camera-overlay-soundtrack">Camera-Invariant Captions &amp; HUD</a></strong><br>
       CameraAnimation pan/zoom while overlay HUD &amp; word-by-word highlighted Captions stay pinned on screen.</p>
     </div>

     <div class="gallery-item">
       <div>
         <span class="tutorial-badge">Theme 6 · Blackboard &amp; LaTeX</span>
         <video controls loop muted playsinline src="../_static/gallery/solar_system_journey.mp4"></video>
       </div>
       <p><strong><a href="storytelling_and_export.html">Scientific Storytelling &amp; LaTeX/TikZ Export</a></strong><br>
       Dark-mode Solar System journey, plus native TikZ &amp; LaTeX Beamer slide deck export.</p>
     </div>
   </div>

----

Browse Tutorials by Theme
-------------------------

.. toctree::
   :maxdepth: 2

   math_and_geometry
   flowcharts_and_tables
   character_animation
   scene_transitions
   voice_captions_and_sound
   storytelling_and_export
