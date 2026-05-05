# CLAUDE.md — handanim

> See [repo_overview.md](repo_overview.md) for the full module map, dependency table, and known bug list.
> See [todo.md](todo.md) for the phased roadmap and open issues.

---

## What this project is

**handanim** is a Python library for creating whiteboard-style, hand-drawn animations programmatically. It renders to MP4, GIF, or SVG. The user writes Python code that composes shapes, styles, and timed animation events; the library takes care of the rest.

The long-term arc is threefold:
1. **A great animation toolkit** — expressive, composable, hand-drawn feel with a clean Python API
2. **An AI-scriptable system** — LLMs should be able to think in scenes and write valid handanim code; the `handanim_ai` module scaffolds this
3. **A handwriting font pipeline** — generate realistic single-line stroke fonts from samples of real handwriting, using RNN/transformer models

---

## Guiding Vision

> *Reproducible, but hand-sketchy.*

Every output must look like it was drawn by a careful human hand — wobbly lines, hachure fills, natural stroke pressure — while being fully reproducible from code. The aesthetic is the product, not an afterthought.

This means:
- The "roughness" and "sketchy" feel must be preserved at all costs when touching rendering code
- New primitives should integrate with `SketchStyle` and `StrokeStyle`; they should not look crisp/digital by default
- When adding new drawing primitives, they must produce output that a `SketchAnimation` can animate stroke-by-stroke

---

## Architectural Invariants — Do Not Break These

### 1. Drawables are stateless and immutable
`Drawable.translate()`, `.scale()`, `.rotate()` **return a new `TransformedDrawable`** — they do not mutate the original.  
Always use the return value: `obj = obj.translate(dx, dy)`.  
Never add mutable state to a `Drawable` subclass.

### 2. `AnimationEvent.apply()` must be a pure function
`apply(opsset, progress)` must not have side effects. It receives an OpsSet, returns a new one. It must not mutate `opsset`, modify `self`, or touch the scene.  
The `Scene` caches the output of completed events and re-uses it as input to later events. Any side effect here will corrupt the timeline.

### 3. OpsSet is the universal interface between layers
Shapes produce OpsSet. Animations consume and return OpsSet. Cairo consumes OpsSet.  
No layer should reach past OpsSet to touch Cairo directly — that is `OpsSet.render()`'s job only.

### 4. Easing and progress
The `progress` value passed to `apply()` is always in `[0.0, 1.0]`. If `easing_fun` is set on an event, apply it first: `progress = self.easing_fun(raw_progress) if self.easing_fun else raw_progress`. This is currently unimplemented everywhere — wire it in when touching any `apply()` method.

---

## Code Style

- **No unnecessary comments** — name things well instead; only comment non-obvious invariants or external constraints
- **Docstrings on important functions** — Add verbose docstrings for all important functions, as documentations are generated from it.
- **Type annotations** — use them on all new public functions; prefer specific types over `Any`
- **No defensive checks on internal paths** — only validate at system boundaries (file paths, user-supplied coordinates, external API calls)
- **Prefer returning new objects** — consistent with the immutability design; avoid `opsset.opsset = ...` mutations inside animation code except in `OpsSet`'s own transform methods

---

## How the Rendering Pipeline Works (summary)

```
Scene.render()
  └─ create_event_timeline()          # one OpsSet per frame
       └─ for each active drawable:
            get_animated_opsset_at_time(drawable_id, t, event_and_progress)
              └─ recursive: apply events in order, cache completed ones
                   └─ event.apply(opsset, progress) → OpsSet
  └─ for each frame OpsSet:
       viewport.apply_to_context(ctx)
       opsset.render(ctx)              # the only Cairo call
       write frame to video
```

The cache key for a completed event state is `"{drawable_id}__{event_id}"`.  
The initial OpsSet (before any animation) is cached as `"{drawable_id}__init"`.

---

## Where to Add Things

| What | Where |
|---|---|
| New shape | New file in `primitives/`, subclass `Drawable`, implement `draw() -> OpsSet` |
| New animation | New file in `animations/`, subclass `AnimationEvent`, implement `apply(opsset, progress) -> OpsSet` |
| New style option | Add field to `StrokeStyle` / `FillStyle` / `SketchStyle` in `core/styles.py` |
| New fill pattern | `stylings/fillpatterns.py`, must return an `OpsSet` |
| New color constant | `stylings/color.py` |
| AI prompt | `handanim_ai/prompts/` as a `.txt` file |
| New example | `examples/` as a standalone runnable script |

---

## Things to Be Careful About

- **`SVG` vs `VectorSVG`** — there are two SVG importers. `VectorSVG` (using `svgelements`) is the current one with full color/transform support. `SVG` (using `svgpathtools`) is legacy, paths-only, and deprecated. Prefer `VectorSVG`. Do not add new code that imports from `primitives/svg.py`.
- **`DrawableGroup` parallel mode** — uses `drawable_element_id` metadata on OpsSet to extract individual results after a group transformation. If you touch group animation logic in `scene.py`, test with nested groups.
- **Viewport coordinates** — the default world space is `(0, 1777) × (0, 1000)` for a 1920×1088 scene. All primitive positions are in this coordinate system, not pixels.
- **`SketchAnimation` and fill** — `get_partial_sketch` splits draw ops from fill ops using a `METADATA` op with `drawing_mode == "fill"`. Primitives that have both a stroked outline and a fill must emit this metadata correctly.

---

## Current Priorities (see todo.md for full list)

1. Add visual regression tests before expanding the surface area further
2. Implement `FlowchartNode` / `FlowchartConnector` as the next major primitive cluster
3. Complete `apply_strokes_gradient` and wire up `ColorTransitionAnimation`
4. Improve caching (static object cache, group transform result cache)
