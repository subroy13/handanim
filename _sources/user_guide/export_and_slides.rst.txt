Export Formats, Snapshots, Beamer & TikZ
========================================

Beyond standalone MP4 and GIF videos, ``handanim`` can export animations to vector snapshots, storyboards, printable PDF handouts, and compilable LaTeX Beamer slide decks (using either Cairo PDFs or native inline TikZ).

1. Video & GIF Rendering (:meth:`~handanim.core.scene.Scene.render`)
--------------------------------------------------------------------

.. code-block:: python

   # Render H.264 MP4 (preserves exact pixel dimensions including 1080x1920 and 360x640)
   scene.render(
       "explainer.mp4",
       max_length=10.0,
       narration=clip,
       background_music="marimba",
       sketch_sound=True,
       eraser_sound=True,
   )

   # Render animated GIF
   scene.render("explainer.gif", max_length=5.0)

2. Single-Frame & Batch Snapshots (SVG / PDF / PNG)
---------------------------------------------------

Use :meth:`~handanim.core.scene.Scene.render_snapshot`, :meth:`~handanim.core.scene.Scene.render_keyframes`, and :meth:`~handanim.core.scene.Scene.export_storyboard` to inspect frames visually or export vector illustrations for papers:

.. code-block:: python

   # Single timestamp snapshot (.svg, .pdf, or .png)
   scene.render_snapshot("frame_2s.svg", frame_in_seconds=2.0)

   # Batch export specific timestamps (computes timeline only once)
   scene.render_keyframes(
       times=[0.5, 1.5, 3.0, 4.5],
       output_dir="keyframes/",
       format="svg",
   )

   # Export 6 evenly-spaced storyboard frames
   scene.export_storyboard(n_frames=6, output_dir="storyboard/", format="pdf")

3. Multi-Page Printable PDF Handouts (:meth:`~handanim.core.scene.Scene.render_handout`)
----------------------------------------------------------------------------------------

Generate a single multi-page PDF document with one animation keyframe per page:

.. code-block:: python

   scene.render_handout("lecture_handout.pdf", n_frames=8)

4. LaTeX Beamer Slide Decks & Native TikZ (:meth:`~handanim.core.scene.Scene.export_beamer`)
--------------------------------------------------------------------------------------------

Export keyframes directly into a compilable LaTeX Beamer presentation using ``\only<N>{...}`` overlays so stepping forward in your PDF viewer replays the animation:

.. code-block:: python

   # Mode A: Cairo vector PDFs embedded via \includegraphics
   scene.export_beamer(
       output_dir="slides_cairo/",
       n_frames=6,
       title="Pythagorean Theorem",
       backend="cairo",
   )

   # Mode B: Pure inline LaTeX TikZ paths (no external image files!)
   scene.export_beamer(
       output_dir="slides_tikz/",
       n_frames=6,
       title="Pythagorean Theorem (TikZ)",
       backend="tikz",
       target_width_cm=12.0,
   )

   # Standalone single-frame TikZ .tex file
   scene.render_tikz("diagram.tex", time=3.0, target_width_cm=12.0)

