# handanim: Architectural Overview & Development Plan

This document outlines the core architecture of the `handanim` library and proposes a plan for future development and enhancements.

## 1. Core Architecture

`handanim` is designed with a layered and modular architecture that separates drawing logic, animation timing, and rendering. This makes the system flexible and extensible.

### Key Components:

1.  **Drawing Primitives (`Ops` & `OpsSet`)**:
    -   The foundation of the rendering engine is a set of low-level drawing operations (`Ops`), such as `MOVE_TO`, `LINE_TO`, and `CURVE_TO`.
    -   These are grouped into an `OpsSet`, which is an ordered list of instructions required to draw a complete shape. `OpsSet` objects are the final output that the rendering backend consumes.

2.  **Drawable Objects (`Drawable`)**:
    -   These are high-level representations of shapes (e.g., `NGon`, `Line`, `Text`).
    -   Each `Drawable` is responsible for generating its corresponding `OpsSet` via its `.draw()` method.
    -   They are stateless by design. Transformations (like `translate`, `scale`, `rotate`) do not modify the object but instead return a new `TransformedDrawable` instance. This is a clean, functional approach that prevents side effects.

3.  **Animation & Timing (`AnimationEvent`)**:
    -   `AnimationEvent` connects a `Drawable` to a specific animation type (e.g., `SketchAnimation`) over a defined time interval (`start_time`, `end_time`).
    -   The event's `.apply()` method is responsible for modifying an `OpsSet` based on the animation's progress (a float from 0.0 to 1.0).

4.  **The Conductor (`Scene`)**:
    -   The `Scene` class is the main user-facing entry point. It orchestrates the entire animation.
    -   It maintains a list of all `AnimationEvent`s and a `DrawableCache` to store pre-calculated `OpsSet`s for performance.
    -   **Rendering Pipeline**: When `render()` is called, the `Scene` calculates the state for each frame. For a given time `t`:
        - It determines which `Drawable` objects are "active" (visible).
        - For each active object, it finds any ongoing `AnimationEvent`s.
        - It retrieves the base `OpsSet` from the cache.
        - It applies the animation transformations to the `OpsSet` based on the current progress.
        - The final, combined `OpsSet` for the frame is rendered to a Cairo surface.

### Design Decisions & Strengths:

-   **Decoupling**: The separation of `Drawable` (what to draw) from `AnimationEvent` (how to animate it) is a major strength. It allows for combining any shape with any animation.
-   **Immutability**: The functional approach to transformations on `Drawable`s makes the system predictable.
-   **Extensibility**: Adding a new shape requires creating a new `Drawable` subclass. Adding a new animation effect requires a new `AnimationEvent` subclass. The core `Scene` logic remains untouched.

### Known Limitations & Future Considerations:

-   **Object Visibility**: The `Scene.get_active_objects` method uses a simple toggle mechanism based on creation/deletion events. This is efficient but would need to be adapted to support more complex visibility patterns (e.g., an object blinking on and off multiple times).
-   **Font Generation**: The `utils/fontmaker` script is a prototype for converting raster glyphs to vector paths. It currently uses skeletonization, with plans for more advanced techniques (e.g., ML-based) in the future.

## 2. Proposed Development Plan

### Recent Improvements

-   **Intuitive Animation Persistence**: The `keep_final_state` flag on `AnimationEvent` now defaults to `True`. This makes animations "stick" to their final state by default, which is more intuitive for users. The previous behavior (reverting to the original state) can be achieved by setting `keep_final_state=False`.
-   **Polished Sketching Effect**: The `glowing_dot` in `SketchAnimation` now correctly disappears when the animation completes (`progress=1.0`), providing a cleaner visual finish.

Based on the current structure and the "Features Coming Soon" in the `README.md`, here are some areas we can focus on.

### Phase 1: Enhancing Core Primitives & Features

1.  **Improve Text Handling**:
    -   Implement "autofitting" of text within a bounding box. This would involve calculating text extents using `fonttools` or Cairo and dynamically adjusting font size or wrapping.
    -   Support for multi-line text and basic alignment (left, center, right).
2.  **Refine Dependency Management**:
    -   Standardize on either `pycairo` or `cairocffi` to simplify the dependency tree and installation process. `cairocffi` is often easier for cross-platform distribution.

### Phase 2: Advanced Features & Performance

1.  **Caching & Performance Optimization**:
    -   The current `create_event_timeline` re-calculates the `OpsSet` for every object on every frame. We can introduce a more sophisticated caching layer. For static objects (visible but not being animated), their `OpsSet` can be cached and reused across frames.
2.  **Complex Animations**:
    -   Introduce more animation types, such as `FadeIn`, `FadeOut`, and `Transform`, which would animate properties like color, position, and scale between two states.
3.  **Diagramming Tools**:
    -   Build higher-level objects for flowcharts and tables. A `Table` drawable could be composed of `Rectangle` and `Text` objects, managed within a `DrawableGroup`.
