# Font Modelling — TODO

## Bug Fixes

### Bug 1 — `Text` positioning is centre-of-gravity, not left-edge anchor  ✅ FIXED
**File:** `src/handanim/primitives/text.py` — `draw()` single-line branch (lines 233-237)

**Root cause:**  
`_draw_line` is called at `(0, 0)` and then the whole OpsSet is translated so its *centre of gravity* lands at `self.position`. For wide strings at large font sizes the CG can be far right of `x=0`, so the translate overshoots left: e.g. CG at x=800 with `position=(300, 400)` → translate of −500 → text starts off-screen.

`Math.draw()` uses `self.position` as the literal *left-edge* anchor of the first glyph — the two primitives are inconsistent and the user cannot align them.

**Fix:**  
Pass `self.position` directly to `_draw_line` instead of the CG centering trick:
```python
self._draw_line(opsset, self.text, self.position[0], self.position[1])
```
Remove the CG translation that follows.  
Document that `position` is the top-left anchor for both `Text` and `Math`.

---

### Bug 2 — Hershey math rendering misidentifies Latin/digit glyphs  ✅ FIXED
**File:** `src/handanim/primitives/math.py` — `hershey_glyph_opsset()` (lines 142-209)

**Root cause:**  
The Hershey `mathlow` font encodes *Greek* letters using Latin ASCII codes (e.g. `'x'` in mathlow = ξ, `'a'` = α). The fallback path normalises a math-italic unicode (e.g. U+1D465 MATHEMATICAL ITALIC SMALL X) via NFKD to `'x'`, then looks up `'x'` in mathlow — which returns ξ, not x. Plain digits (`'2'`, `'4'`) may not exist in mathlow at all and return empty.

Additionally, `UNICODE_TO_HERSHEY` only covers 25 Greek letters + 6 operators; all other math unicodes (operators, structural glyphs produced by matplotlib's STIX layout engine) silently return an empty OpsSet.

**Fix:**
- Add a Hershey font fallback chain: if glyph is not found in the primary Hershey font, try `rowmans` (covers ASCII alphanumeric) before returning empty.
- Extend `UNICODE_TO_HERSHEY` to cover at least: common operators (≤, ≥, ∞, ∂, ∇, ∫, ∑, ∏, ≠, ≈, ⟨, ⟩, …), arrows, and digits in their math-styled unicodes.
- Use `rowmans` (or `rowmant`) as the default font for any ASCII-range glyph (digits, Latin letters) rather than `mathlow`.

---

## Feature: Hand-drawn Math & Text Rendering

### F1 — Extend Hershey coverage for common math symbols  ✅ DONE
**Priority:** High  
Map additional unicode codepoints in `UNICODE_TO_HERSHEY` using the Hershey `mathspecial`, `greekc`, `symbolic` sub-fonts:
- Integral ∫ (8747), summation ∑ (8721), product ∏ (8719)
- Partial derivative ∂ (8706), nabla ∇ (8711), infinity ∞ (8734)
- Inequality signs ≤ (8804), ≥ (8805), ≠ (8800), ≈ (8776)
- Arrows →, ←, ↑, ↓, ⟹ etc.
- Angle brackets ⟨ ⟩, floor/ceiling ⌊ ⌋ ⌈ ⌉

---

### F2 — Centerline/skeleton extraction pipeline (fontmaker extension)
**Priority:** Medium  
Add a script (in `utils/fontmaker/`) that:
1. Takes a math-capable TTF (STIX Two Math or DejaVu Math — both freely licensed and used internally by matplotlib).
2. Rasterises each glyph to a high-res bitmap.
3. Applies Zhang-Suen or Guo-Hall thinning (`skimage.morphology.thin`) to produce the medial-axis skeleton.
4. Vectorises the skeleton pixels into smooth spline paths.
5. Determines natural stroke order: connected components sorted left-to-right-top-to-bottom; within each component finds the approximate Eulerian path.
6. Writes output in the existing **custom JSON** format (`handanimtype1.json` schema) so it feeds directly into `custom_glyph_opsset` with zero renderer changes.

This gives full LaTeX symbol coverage (any symbol STIX covers) as a one-time precomputation.

---

### F3 — CROHME InkML ingestion for common symbols
**Priority:** Medium  
The CROHME dataset (online handwriting competition) ships InkML files with real human pen-stroke sequences and symbol labels.
1. Parse InkML stroke sequences `(x, y, t)` grouped by symbol label.
2. Normalize to a unit bounding box; optionally DTW-average across multiple writers for a cleaner canonical stroke.
3. Smooth with a Savitzky-Golay filter and resample to a fixed number of control points.
4. Export to custom JSON format.

Covers: digits, Latin letters, Greek letters, and ~100 common math operators (enough for 90 % of educational math content). Use as Priority 1 in the font lookup chain.

---

### F4 — Roughification layer for stroke paths
**Priority:** Medium  
Add an `apply_roughness(opsset, roughness, seed)` utility (in `stylings/utils.py` or `stylings/strokes.py`) that:
- Walks each `LINE_TO` / `CURVE_TO` segment.
- Adds correlated Perlin/simplex noise to control points (amplitude scales with `roughness`).
- Splits long straight segments into shorter ones before jittering so the wobble looks organic.
- Is deterministic for a given `seed` — preserves the stateless `apply()` invariant.

Apply this pass in `custom_glyph_opsset` and `hershey_glyph_opsset` so even programmatically-generated glyphs look hand-drawn.

---

### F5 — Layered font fallback chain
**Priority:** Medium  
Replace the current single-backend dispatch in `Math.get_glyph_opsset()` with a priority-ordered fallback:

```
1. custom JSON  (CROHME-derived, widest hand-drawn coverage)
2. hershey       (Greek + common operators, extended via F1)
3. skeleton TTF  (STIX Two Math skeleton output from F2)
4. raw TTF outline (current behaviour — last resort, looks less natural)
```

Configurable per `Math` instance; default chain picks the best available source automatically.

---

### F6 — Stroke ordering for SketchAnimation on glyph paths
**Priority:** Low  
Currently `SketchAnimation` reveals the OpsSet in declaration order. For skeleton-extracted and CROHME glyphs, stroke order is already natural. For TTF outline glyphs the reveal traces outer then inner contours, which looks like calligraphy-outline drawing rather than writing.

Add an optional `stroke_order="natural"` flag to `SketchAnimation` (or `Math`/`Text`) that:
- Groups the OpsSet into strokes (segments between `MOVE_TO` ops).
- Reorders strokes using a nearest-neighbour heuristic (end of one stroke → closest start of next).
- Feeds the reordered sequence to the animation.

---

### F7 — Unified `MathText` primitive
**Priority:** Low  
Merge `Math` and `Text` into a single `MathText` primitive (or add a `math=True` flag to `Text`) so:
- Plain strings use the hand-drawn font glyph path.
- Strings wrapped in `$...$` are parsed by `MathTextParser` for correct TeX layout.
- Both honour the same `position` semantics (left-edge anchor, consistent with fix in Bug 1).
