# Ptolemy's theorem — a short visual proof

## Brief

One takeaway: for a convex cyclic quadrilateral ABCD, in cyclic order,
**AC · BD = AB · CD + BC · AD**.

Audience: students who know similar triangles and the inscribed-angle theorem.
Duration: 58 seconds. Final: 1080 × 1920, 30 fps; preview: 360 × 640.
Visual language: whiteboard, handwritten single-stroke lettering, quiet gray circle,
blue first pair, orange second pair, green conclusion. No decorative character is
needed: the geometric construction is the main action.

## Mathematical argument

Choose K on the segment AC such that angle ABK = angle DBC.

1. Angle BAK = angle BDC because both stand on chord BC. Together with the
   constructed equal angles at B, this gives ABK ~ DBC (A ↔ D, B ↔ B, K ↔ C).
   Thus AK/CD = AB/BD, so BD · AK = AB · CD.
2. Subtracting the constructed equal angles from angle ABC gives CBK = ABD.
   Also BCK = BDA, both standing on chord AB. Hence BCK ~ BDA
   (B ↔ B, C ↔ D, K ↔ A). Thus KC/AD = BC/BD, so BD · KC = BC · AD.
3. Add, use AK + KC = AC, and obtain the stated identity.

The auxiliary ray lies inside angle ABC, so its intersection K with AC is interior.
The code constructs K from the angle condition, not from the identity being proved.
The specific drawing is illustrative; the argument applies to every nondegenerate
convex cyclic quadrilateral with that vertex order.

Reference: [Kiran S. Kedlaya, Geometry Unbound, §8.2, Theorem 8.2.1](https://kskedlaya.org/geometryunbound/gu-060118.pdf),
printed pp. 67–68. It gives a similar-triangle auxiliary-point proof; this video
uses an angle construction and splits AC instead of BD. Narration and artwork
here are original.

## Timed visual beats

- **0–4 s:** Write the title, sketch the circle and four sides, label A–D.
  Hook: a simple circle hides an unexpected identity.
- **4–11.5 s:** State the cyclic-order hypothesis. Draw AC and BD; show the
  proposed diagonal-product / opposite-side-product identity.
- **11.5–19.5 s:** Draw BK, mark K on AC. Mark ABK and DBC with matching blue
  single arcs. Show the construction condition explicitly.
- **19.5–27 s:** Trace and hatch ABK and DBC in blue. Single arcs show the
  construction; double arcs at A and D show equal inscribed angles on chord BC.
  Write the similarity and corresponding-side ratio.
- **27–32 s:** Turn the ratio into BD · AK = AB · CD and hold it.
- **32–40 s:** Fade the first pair, trace BCK and BDA in orange. Single arcs
  show the remaining equal angles at B; double arcs at C and D stand on chord AB.
  Show the second similarity and ratio; retain the first product as a reminder.
- **40–45.5 s:** Write BD · KC = BC · AD below the first identity.
- **45.5–50 s:** Color AK blue and KC orange on the original diagonal. Stack
  and add both identities.
- **50–58 s:** Replace AK + KC by AC. Draw a green frame around Ptolemy's
  identity and hold the conclusion for reading.

## Narration draft

Use the screen labels to support the narration. A synthetic local voice may be
used for the first review; keep the video understandable with its burned-in
captions and formulas even without sound.

- 0.6: “Ptolemy's theorem. A beautiful visual proof.”
- 4.5: “Four points, in order, on a circle.”
- 8.2: “Diagonals and sides obey this identity.”
- 11.7: “Choose K on A C, so these two angles at B are equal.”
- 19.7: “Angles on the same chord are equal. So triangles A B K and D B C are similar.”
- 27.1: “Matching sides give the first product identity.”
- 32.2: “The remaining angles at B match too. The circle gives a second similar pair.”
- 40.1: “Matching sides now give the second product identity.”
- 45.7: “Add the two identities.”
- 50.1: “A K plus K C is A C. And that is Ptolemy's theorem.”

## Reproduction

From the repository root:

```sh
.venv/bin/python sandbox/ptolemy/scene.py --preview
.venv/bin/python sandbox/ptolemy/scene.py
.venv/bin/python sandbox/ptolemy/narration.py
```

The script exports a module-level `scene` for MCP linting, introspection, and
snapshots. Main settings and palette are at the top. World ranges are explicitly
fixed to (0, 562.5) × (0, 1000) at both resolutions, with no viewport margin.
Python and NumPy seed: 20261104. Text: bundled Feasibly single-line TTF, selected
by the current Text implementation when font mixture is disabled. Formulas:
Hershey rowmans. Package: handanim 0.1.0 from this checkout. No external artwork.

`narration.py` generates ten local macOS Samantha voice clips at 185 words/minute,
checks each actual duration against its scene slot, places them in a 58-second
mono 24 kHz WAV, and combines it with `silent.mp4` using imageio's FFmpeg.
The final file is `output/ptolemy.mp4`. Existing clips are reused only when the
voice, rate, and saved transcript agree. Voice generation requires macOS; saved
WAV clips can be reused elsewhere. Do not run the narration/mux step until the
silent video render has finished. Output clips and their transcripts are local
render artifacts, ignored by Git along with the other generated media.

## Validation and first-render findings

- Final H.264 MP4: 1080 × 1920, 30 fps, 1,741 video frames, approximately 58.03 s.
  The scene renderer includes its final endpoint frame. Narration is 58 s,
  AAC in the final MP4. Revised file size approximately 1.60 MB.
- FFmpeg decoded the entire final video/audio without errors. The narration WAV
  is nonempty, peaks at 26,633 / 32,768, and every spoken clip fits its beat.
- Reviewed a nine-frame contact sheet from the preview and full-resolution MCP
  snapshots for the similar pairs and conclusion. This is sampled visual QA;
  a full human playback/listening review is still pending.
- Independent rerenders of the conclusion at 55.5 s produced identical PNG
  SHA-256 hashes (revised sketch style): `735734db140df245d4d6cade077e0b1a7429db584d4cb88f3b24f81824a01232`.
  This establishes same-environment snapshot reproducibility, not identical
  encoding or fonts across arbitrary platforms.
- Verified the angle construction, interior placement of K, and both length
  identities on the displayed geometry and 40 varied cyclic quadrilaterals.
  These checks supplement the general argument above.
- MCP lint: valid, no warnings. MCP introspection: 94 objects, no warnings/errors.
  These static checks did not detect missing glyphs; rendered review did.
- Fixed four underlying issues: missing geometry glyphs, font asset discovery,
  portrait dimensions being rounded by the encoder, and fading translucent
  hatching becoming opaque. All 148 targeted tests passed. The connected MCP
  process needs restarting before its cached asset-discovery function updates.
- No music or sound effects. The narration is a synthetic draft voice; replace
  it with a human recording if preferred. No claim of a listening review.

## Revision: more human drawing

- Geometry: roughness 0.30 → 1.1, bowing 0.10 → 0.35, maximum random offset
  0.65 → 1.25. Lettering roughness 0 → 0.18; keep mathematical labels legible.
- Every one of the 94 creation events now uses SketchAnimation, including
  captions, headings, the eyebrow, and chapter tracks. Minimum drawing duration:
  0.45 s. Chapter headings draw over 1.1 s. Caption lines draw sequentially,
  with writing durations scaled to their length, capped at 1.25 s per line.
- Fades only clear old content. Geometry, proof, beat boundaries, and saved
  narration remain the same. Updated the agent guide to carry this preference
  forward for future videos.
- Re-rendered the portrait video and narrated preview, checked full decoding,
  and repeated the seeded conclusion snapshot. Layout inspection still reports
  no warnings/errors. Full human viewing/listening review remains pending.
