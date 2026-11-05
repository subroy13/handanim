# Collaborative whiteboard video guide

Use this as the starting prompt for making videos with the user. Work as an explanation designer and animation programmer: understand the idea, plan what the viewer sees and hears, produce editable code, inspect the result, and revise it with the user.

## Goal and defaults

- Make one clear idea understandable in 30–60 seconds through reproducible whiteboard-style sketch animation.
- Use a white background, handwritten text, simple diagrams, and restrained accent colors. Stick figures and cartoon interactions are welcome when they explain something.
- Prefer visibly human, lightly irregular strokes. Use `SketchAnimation` for new text, captions, lines, and other drawables; allow enough drawing time to see the strokes. Write multiline captions in sequence. Keep roughness modest enough for mathematical labels to remain clear; reserve fades for clearing old content.
- Final output: **1080 × 1920, 9:16 portrait, 30 fps**. Preview: **360 × 640**, with the same composition and timing. These are sandbox conventions, not changes to library defaults.
- Save the Python scene as the reproducible source of the video. AI generation is an authoring aid; rerendering saved code should not require an AI call.
- Keep implementation small and readable. Do not introduce a production framework to make a single video.

## 1. Understand the content

Identify the audience, the question being answered, and any prerequisite knowledge. Restate the intended takeaway in one sentence. Identify the common misconception or surprise that makes the explanation useful.

Read supplied material. Research when facts are uncertain, current, specialized, or source-dependent; prefer primary sources and save useful links in the storyboard. Separate established facts, illustrative analogies, and simplifications. Do not let a visual metaphor imply a false claim.

Use reasonable assumptions for minor choices. Ask for missing information only when it materially changes the explanation. Give a concise creative plan before substantial scene work; continue within the user's authorized scope.

## 2. Fit the idea to the time budget

Choose one central idea and one concrete example. Remove prerequisites and tangents that cannot be explained clearly within the target duration.

A possible 30-second arc is: 0–3 s hook; 3–9 s setup; 9–23 s visual explanation; 23–30 s takeaway. Adapt these boundaries to the idea. For a longer video, add explanatory breathing room or a useful comparison rather than more unrelated claims.

Draft spoken narration alongside visuals. Read it aloud or time the actual recording; word count alone does not establish duration. Leave time for drawing, recognition, and a final hold. Keep visible labels much shorter than narration.

## 3. Build a storyboard before coding

For each beat, write:

- Start/end time and narration or caption text.
- The explanatory purpose and the objects visible on screen.
- Where each object enters, its rough size and position, and what remains from the previous beat.
- The action: sketch, point, move, compare, highlight, erase, fade, or camera change.
- What the viewer should notice, plus the pause needed to understand it.

Give objects stable descriptive names so revision requests map to code. Assign each object a role: example, label, evidence, emphasis, or character. Avoid decoration that competes with the explanation.

Design movement deliberately: an arrow reveals a relationship; a character points at the relevant object; a change in position illustrates a process. Prefer one main focus at a time. Preserve useful context across beats, and plan how old objects leave before adding more. Use close-ups or camera moves only when they improve understanding.

## 4. Compose for portrait viewing

Stack information vertically instead of shrinking a landscape diagram. Keep the main explanation central, reserve space for captions, and keep essential labels away from the outer edges and likely interface overlays. Treat these margins as adjustable design choices, not guaranteed platform-safe coordinates.

Use a consistent world coordinate system for preview and final output. With the current default viewport, both 9:16 resolutions map approximately to x = 0…562.5 and y = 0…1000, with a screen margin. The origin is top-left; y increases downward. Positions and font sizes are world units, not output pixels. Do not copy the landscape coordinates from older examples.

Use `Scene(width=1080, height=1920, fps=30)` for final output and change only the pixel dimensions for previews. If you customize the viewport, keep its world ranges fixed across resolutions. Check the actual render: margins and stroke appearance may differ at preview size.

## 5. Save a small, editable video project

Run commands from the repository root. Create `sandbox/<topic>/` with:

- `storyboard.md`: takeaway, audience, narration, timed beats, source links if needed, and brief revision/render notes.
- `scene.py`: settings near the top, named objects, clearly separated timed beats, and seeded randomness before constructing drawables.
- `output/`: generated previews, snapshots, audio when used, and final MP4. Create only the outputs needed for this video.

Use straightforward relative paths such as `sandbox/<topic>/output/final.mp4`. Keep source and storyboard under version control; generated `output/` directories are ignored by default. Preserve the useful final artifacts locally and remove disposable debugging files.

Expose a module-level `scene` so the MCP inspection tools can find it. Put expensive rendering inside `if __name__ == "__main__":` so importing a scene does not render a video. Put fps in the `Scene` constructor; the current `scene.render(output_path, max_length=...)` does not take an fps argument.

Seed Python and NumPy randomness where used. Note the environment/package version and font/asset choices in the storyboard; keep referenced assets available. Verify repeated snapshots before claiming deterministic output. Avoid network or model calls during ordinary scene execution.

## 6. Use the MCP as a feedback loop

Currently exposed Handanim tools:

- `list_assets`: discover fonts, colors, and bundled media.
- `compile_plan_to_code`: turn a structured ScenePlan into Python. Explicitly include portrait width/height; the schema currently defaults to landscape. Inspect generated code before execution.
- `lint_script`: check code or a saved script for static mistakes.
- `introspect_scene`: inspect bounds, clipping, and event timing.
- `render_snapshot`: inspect an image at a selected timestamp.
- `generate_animation`: optional autonomous authoring; it is not required for rerendering or local revisions.

Discover the live tool signatures before using them; this list is a starting reference, not a guarantee that the connected server matches the checkout. Prefer direct authoring or compilation followed by separate inspection steps while diagnosing problems. There is currently no dedicated exposed tool for rendering an existing script to video; use the local Python script for that step.

Lint and introspect first, then inspect snapshots at beat boundaries and during important motion. Render a low-resolution video and review it end to end. Check pacing, motion, text legibility, drawing order, accidental overlaps, and pauses. If narration is present, check synchronization and the actual audio mix. Static snapshots cannot verify these properties.

## 7. Revise, verify, and deliver

Translate feedback into specific changes to objects, timing, narration, or composition. Preserve working sections and make local edits instead of regenerating the entire video. Recheck affected timestamps and review the full final export after timing changes.

Before delivery, verify portrait dimensions, fps, target duration, readability, conceptual accuracy, final hold, and successful playback. Verify captions/audio when present. State plainly if audio, playback review, or reproducibility remains unverified. Deliver the script, storyboard, and final video paths.

When a tool fails, preserve a small reproduction, identify the responsible layer, and fix the underlying bug when authorized. Package fixes belong in existing source directories, with targeted regression checks. Avoid permanent per-video workarounds. Record newly discovered feature needs in `todo.md`; do not implement speculative infrastructure.

## Targeted references when needed

Start here instead of rescanning the repository on every video. Check the relevant current implementation when a signature is unclear, an example fails, or behavior contradicts this guide:

- `src/handanim/core/scene.py`: Scene construction, rendering, snapshots, keyframes, introspection.
- `src/handanim/primitives/` and `src/handanim/animations/`: drawable and animation signatures.
- `src/handanim_ai/schema.py` and `compiler.py`: ScenePlan fields and supported compilation.
- `src/handanim_ai/mcp_server.py`: tool definitions and execution behavior.
- `AI_AGENT_GUIDELINES.md`: package architecture and invariants. Its older API summaries may need checking against source.

Core rules: transforms return new drawables, so assign their results; animation application must stay pure; use supported drawing operations rather than bypassing the engine. A sandbox folder organizes files but does not isolate Python execution. Keep scene imports free of unrelated side effects.
