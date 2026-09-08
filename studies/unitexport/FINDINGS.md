# U5 — unit body export + measured viewer

**2026-08-16.** Rung U5 of [studies/unitmodels/PLAN.md](../unitmodels/PLAN.md)
§2. Labels per [studies/character/FINDINGS.md](../character/FINDINGS.md).
Code: `toolkit/mapdata/unitexport.py` + `toolkit/mapdata/test_unitexport.py`
(71 checks, floor 71) + `tools/blender/import_gwunit.py`. Exports:
`vault/exports/units/`. Artifacts (summaries, renders, `.blend` scenes):
`vault/research/unitexport/`.

## 1. What shipped

A unit body is an ffna type-2 file exactly like a prop model — **both
anchors decode through `modelfile.py` unchanged** (MEASURED; no unit-side
fork of the geometry decoder was needed) — so `unitexport.py` rides
`modelexport.build_manifest`/`texture_payloads` for FA0+FA5 and adds one
thing props do not have: the FA1 skeleton/animation chunk, as a sidecar in
the `.gwmodel` family.

| Anchor | Chunks | Export |
|---|---|---|
| burrowing worm **116366** (`unit_1C68E`) | FA0 + FA5 + FA6 + FA1 (82,169 B) | 3 sub-models, 825 verts, 2,618 tris, 5 textures, `fa1.bin` + typed skeleton block |
| hatcher body **116703** (`unit_1C7DF`) | FA0 + FA5 | 4 sub-models, 1,463 verts, 3,746 tris, 3 textures, skeleton **recorded absent** with its reason |

The sidecar is two halves, deliberately:

- **`unit_<id>.fa1.bin`** — the whole 0xFA1 payload VERBATIM, with every
  block's `(offset, size)` span recorded in the manifest (the walk's own
  spans, tiling the payload exactly). Undecoded regions (n14, n34, n38,
  n44, n52, n50, n54–n57 contents; the six unnamed sequence-record fields;
  all channel key data) travel at full fidelity for rung U6's writer.
  Nothing is invented.
- **The manifest's `skeleton` block** — the typed summary, every value read
  through `skelfile.py`'s committed U1/U2 layer: sequences (lo/hi span,
  start/end clamp window, duration), the SoA key table (times + tags), the
  per-node summary (count, link hierarchy, base vec3, flags, channel key
  counts), blk48 tracks, sound events, the n3E event track. Channel key
  DATA is summarised (counts), not re-serialised — blk2C is 80,884 of the
  worm's 82,169 bytes and a JSON copy would be a second, divergeable
  encoding of bytes the `.bin` already carries exactly.

Refusals from birth: `resolve_outdir` **delegates to
`mapexport.resolve_outdir`** (default `vault/exports/units/`, the working
tree refused with no override; asserted beside positive controls). A
COMPOSITED shell (116228, FA1-without-FA0) is **refused, not invented** —
its body is rung U4's resolver's to assemble. A manifest with no skeleton
block at all is refused by `skeleton_from_export`, so "old export" can
never read as "no skeleton".

## 2. The check results (all MEASURED, 2026-08-16, `vault/dat_study/Gw.dat`)

- **Re-interleave: 7/7 sub-models** (worm 3/3, hatcher 4/4) — the exported
  per-field arrays re-interleaved by `test_modelexport.py`'s packer
  (imported, `struct.pack_into`, no code shared with any module under
  test) equal the FA0 chunk's own vertex bytes read fresh from the
  archive. Triangle lists 7/7 exact; the position sidecar's own bytes
  (read with `struct.unpack`, never through `load_model`) equal the
  archive's 825 and 1,463 vertices; max 2D radius through the export
  equals the fresh computation (43.1509 / 18.9861).
- **`fa1.bin` byte-identity: 82,169/82,169** — the sidecar off disk IS the
  archive's 0xFA1 payload. This is U6's precondition, already held.
- **Sidecar read-back: 98/98 field comparisons agree** — 10 sequences ×
  (lo, hi, start, end, duration) + the key table + 20 nodes × (link+base,
  channel key counts) + track count + 6 sound events, each compared
  against a FRESH `skelfile.Skeleton` decode of the archive bytes.
  Serialisation changed nothing. The comparison's power is proven both
  sides: a tampered sequence end, a tampered key count and a tampered
  start time on the real record are each caught.
- **Worm durations, off disk:** 2.000, 2.000, 2.733, 0.333, 1.733, 2.000,
  2.000, 2.000, 2.000, 2.000 s (start/end × 1e-5 s; equal to the decoder's
  to the integer).
- **Corruption refusal:** one flipped byte in `fa1.bin` and `load_model`
  refuses naming the file (sha256, same rule as every sidecar).
- Textures: **all 5 + 3 FA5 slots decode to PNG** (`{'atex': 5}` /
  `{'atex': 3}`, zero unresolved, zero errors).

## 3. The pose that shipped: FLAT placement, and why that is the bind pose

**Shipped: the FA0 vertices as stored — no node transform applied to any
vertex.** The alternative (posing sub-models by blk2C base transforms) was
rejected as invention, not as expensive: the worm has **20 nodes and 3
sub-models**, and no sub-model→node binding is measured anywhere
(candidates exist — see §6). What makes the flat placement the **bind
pose** rather than a hope is a measurement the test pins:

> **All 18 channel-carrying nodes' base positions fall INSIDE the stored
> mesh's own bounding box** — 18 of 20 nodes total; the two channel-less
> nodes (0 and 19) sit at the origin, which the mesh's y-range excludes,
> and an unposed node carries no positional claim. MEASURED: mesh bbox
> [-15.6, -43.2, -172.8] .. [15.6, -9.5, 27.7]; the animated bases span
> x ±12.2, y -33.9..-12.0, z -155.9..27.1.

*The review measured this statistic's power and its limit (U5 review,
2026-08-16): the nulls that matter fail decisively — the bases rotated
90° score 1/18, scaled 2× score 0/18, and the hatcher's 1,463 vertices
against this bbox score 0/1463 — while a component-shuffle null passes
18/18, so the check establishes that the base CLOUD occupies the mesh's
region (exactly what this section claims), not per-node correspondence.*

The stored vertices already stand around their skeleton — the worm's
segmented spine runs down the mesh, the two mandible chains (nodes 15/16
and 17/18, the only deep links) sit at its head. The renders confirm the
same thing at the pixel level: both bodies are coherent creatures, not
vertex soup (§4).

The skeleton is **shown, not applied**: one empty per node at its RAW base
(z negated, the mesh's own M4-measured convention), parented along the
measured link hierarchy with world positions kept. Whether a base is
parent-relative or absolute is NOT MEASURED (`skelfile.py`); the empties
take no side — on the worm every deep chain hangs off nodes at or near the
origin-linked root, so the readings coincide there. Test: 20/20 empties at
their bases, 20/20 parents equal to the measured links, 1 root (the one
self-link, node 0).

## 4. The viewer, measured headless

`tools/blender/import_gwunit.py`, driven by the test as a subprocess
(Blender 5.1.1, `--background --factory-startup --python-exit-code 66`).
Everything asserted is computed from the dump or the rendered pixels —
nothing was scored by eye. The render is an instrument: orthographic
camera on the +y axis (screen x = model x, screen y = world up),
transparent film so the silhouette IS the alpha channel, ortho scale in
the dump so the test can PREDICT pixel extents from the export's own bbox.

Test-run measurements (256×256, Cycles, 4 samples):

| Measurement | worm | hatcher |
|---|---|---|
| built mesh | 825 v / 2,618 f (== manifest) | 1,463 v / 3,746 f (== manifest) |
| bbox vs position sidecar | x/y equal; z NEGATED range equal | same |
| textures | 5 materials, 2,618/2,618 faces on imaged materials, 1 UV layer | 3 materials, 3,746/3,746 faces |
| silhouette coverage | 0.0820 | 0.0147 |
| control frame (all hidden) | **exactly 0** | **exactly 0** |
| silhouette px bbox vs prediction | 38×233 vs 36.3×232.7 (±4 px) | 120×232 vs 121.6×232.7 (±4 px) |

Artifacts at 512×512 (`vault/research/unitexport/`): worm 74×465 px vs
72.6×465.5 predicted, coverage 0.0802, covered-pixel mean RGB (101,95,96)
— textures really sampled, not flat shading; hatcher 240×465 vs
243.3×465.5, coverage 0.0136; every control frame 0. The worm render is a
segmented tube with mandibles at the head; the hatcher (with `--opaque`,
below) is a complete humanoid in armor, arms slightly out — a bind-pose
stance. (Those two sentences are description of the artifact PNGs; every
number above is the measurement.)

## 5. FINDING: unit texture alpha is not transparency, and the default render pays for it

The hatcher's default render measures a floating head over an invisible
torso: coverage 0.0147, almost all of it the head and thin edges. The
cause is measured, not guessed:

- The viewer's material path is the prop path's
  (`import_gwmap.gwmodel_materials`), which **wires the texture's alpha
  into the shader** — right for foliage and fences, where it was built.
- The hatcher's diffuse-picked layer is FA5 slot 1 (`tex_1C7DB.png`,
  512×512), whose alpha is **< 26/255 on 99.9% of texels (mean 0.1/255)**.
  The worm's picked diffuse (slot 4) is 97.1% opaque — which is why the
  worm renders solid and the hatcher does not.
- `--opaque` (a display control on `import_gwunit.py` that cuts the alpha
  wire; labeled as a control, not a correction) raises the hatcher's
  coverage **0.0147 → 0.1932** at 256², 0.1894 at 512². The test asserts
  the ≥3× gap so the finding cannot silently regress.

What the alpha channel MEANS on a unit texture is **NOT DECODED** — it
lives with the AMAT chain (0xFAD), the same open the models arc recorded
for which FA5 slot is the diffuse. Neither wiring is knowledge; both are
now measurable.

**That last sentence about the test is no longer how the check reads — see
§5.1, which is what happened when the finding got fixed underneath it.**

## 5.1 The gap closed, and the check that measured it went dead (2026-08-18)

`test_unitexport.py` was the suite's only pre-existing red, and it had been
red since at least 0019052. The failing line was §5's own assertion:

```
[FAIL] --opaque at least triples the hatcher's silhouette coverage
       0.1932 -> 0.1932
```

**Both arms measured the same picture, so the control had stopped
controlling.** Three causes were possible — the flag no longer reaching the
viewer, the alpha wiring no longer applied in either path, or a coverage
metric gone insensitive. It is the second, and it is the benign one.

**MEASURED, cause.** The terrain arc's §7.17 work (commit `c1dad12`) added
`modelexport._alpha_class`, which labels a texture `opaque` / `cutout` /
`erases`, and taught `import_gwmap.gwmodel_materials` to skip the alpha
wiring for the `erases` class only. Exporting the hatcher today:

| FA5 slot | image | `_alpha_class` |
|---|---|---|
| 0 | `tex_2005.png` 256² | opaque |
| **1 (the picked diffuse)** | **`tex_1C7DB.png` 512²** | **erases** |
| 2 | `tex_1C7DD.png` 128² | cutout |

The eraser is the exact texture §5 named. So the default render stopped
wiring its alpha, the torso came back, and the default rose 0.0147 →
0.1932 — which is what `--opaque` had been producing all along. The worm
has no eraser (four cutouts and one opaque), which is why its numbers never
moved. **The `--opaque` flag was never broken and neither was the metric.**

**MEASURED, the tamper probe** (prediction stated before the run, and it
held to four decimals). Question: is the `erases` verdict the *whole*
reason? Take the export's manifest, flip slot 1's `alpha` from `erases` to
`cutout`, change nothing else, re-import:

| arm | coverage | mesh |
|---|---|---|
| default | 0.1932 | 1,463 v / 3,746 f |
| `--opaque` | 0.1932 | 1,463 v / 3,746 f |
| eraser reinstated | **0.0147** | 1,463 v / 3,746 f |
| eraser reinstated + `--opaque` | 0.1932 | 1,463 v / 3,746 f |

0.0147 is §5's number, reproduced on demand. Geometry is identical on
every arm, so the collapse is the alpha wire and nothing else. (The render
is deterministic despite Cycles: 12,659 of 65,536 covered pixels,
bit-identical over three repeat runs — the silhouette is a hard alpha edge,
so sampling noise does not reach it.)

**So the FINDING MOVED and the check was rewritten to assert the new truth,
not relaxed.** One check that could no longer distinguish its arms became
four that can, and the reason there are four is that the obvious single
replacement is vacuous: asserting "default == opaque" is satisfied just as
happily by a viewer that has stopped wiring alpha *at all* as by one that
honours the classification. So:

1. **The classifier names the eraser** (section 2, no Blender needed — it
   is a decoder fact): the hatcher's `erases` list is exactly
   `[tex_1C7DB.png]`. Naming the image matters; a count would pass if the
   verdict moved to another slot.
2. **(a) the gap is closed**: default and `--opaque` agree within 0.005,
   and both are the full body.
3. **(b) the erasure is still REAL** — the positive control, and the one
   that stops (a) being vacuous: reinstate the verdict in a manifest copy
   and coverage collapses to under a third on identical geometry.
4. **(c) `--opaque` still has POWER**: on that tampered manifest it triples
   the coverage back. This is §5's original assertion, kept alive on the
   one input where it can still fail rather than deleted.

**MUTATION-TESTED, all four** — because the defect being fixed here is
precisely a check that could not go red, and asserting the replacement can
would otherwise be the same mistake one level up:

| mutation | reddens |
|---|---|
| wire alpha unconditionally (the pre-§7.17 viewer) | (a), (b) |
| never wire alpha (blanket opaque) | (b), (c) — **(a) passes**, which is the whole argument for (b) |
| `_force_opaque` made a no-op | (c) |
| `_alpha_class` never returns `erases` | the naming check, (a) |

Cost: two extra Blender runs, 8.3 s → 23.6 s; floor 72 → 76.

**What this does NOT say.** The classifier is not a decoding of what
ArenaNet means by this texture's alpha — `_alpha_class` is a floor rule
("alpha that would erase substantially the whole surface cannot be the
artist's transparency"), and §5's NOT DECODED stands unchanged: the AMAT
chain (0xFAD) still owns the real answer. All that is claimed is that the
classifier is what currently decides this render, and that its verdict here
is load-bearing rather than cosmetic.

## 6. Honest opens

1. **The hatcher's opaque body renders dark** (covered-pixel means near
   (93,74,66) default / darker opaque). The layer rule inherited from the
   prop path (first stored-UV layer of the material) picks slot 1 for
   every hatcher sub-model, and slot 1 looks like a mask/gloss map, not
   the colour map; slot 0 (fully opaque, sampled with GENERATED uv, -3) is
   an environment layer. Which FA5 slot is a UNIT's diffuse is the same
   REFUTED/undecoded binding as the prop arc's — blocked on AMAT, recorded
   there, not re-opened here.
2. **Sub-model→node binding.** Both anchors' vertices carry `dat_fvf`
   bit 1 (4 B/vertex, exported verbatim in `raw1.bin`). On a skinned body
   a per-vertex node index would live somewhere like that — UNVERIFIED,
   nothing here reads it, and naming it without a consumer-side derivation
   is exactly the mistake the house rules bar. A U-ladder follow-up could
   disassemble the FA0 consumer's use of the field on a unit body.
3. **Node base: parent-relative vs absolute** — still open from U2; the
   viewer deliberately takes no side (§3). Decidable by disassembling the
   GrTrans stream-2 commit path (0x006737C0 onward), or empirically on a
   corpus file whose deep chain would place the two readings far apart.
4. **COMPOSITED shells** (116228 and the 43-file class) export nothing
   here by design — U4's resolver + this exporter compose the answer;
   the refusal message names U4.
5. **Sequence names/ids:** `u32_01` (hash-like, handed to child models at
   sequence start, UNVERIFIED) is carried raw in both the .bin and the
   summary. Whatever maps wire animation ids to sequence indices is not
   in this chunk.

## 7. Defects found by the checks (recorded because the checks earned them)

- **Background Blender evaluates nothing until asked**: the parent-inverse
  for node empties was taken from a parent's not-yet-evaluated
  `matrix_world` (identity), silently ADDING parent bases into children —
  18/20 empties measured off their bases on the first real run. Fixed with
  an explicit `view_layer.update()` before parenting (and one before the
  summary reads matrices). A viewer without the placement check would
  have shipped it.
- The guessed 0.02 coverage floor was refuted by the hatcher at 0.0147
  and replaced by `COVER_MIN = 0.005` beside the zero-measuring control —
  which then led straight to §5's alpha finding.
- **A defect IN a check, not found by one** (§5.1): §5's `--opaque` gap
  assertion went dead when the terrain arc fixed the erasure upstream, and
  it sat red in the suite rather than announcing that its subject had
  moved. Nothing here can detect that automatically — a check whose two
  arms converge looks exactly like a check whose subject regressed, and
  only reading the cause tells them apart. What the rewrite adds is the
  tamper arm, which keeps the original phenomenon reproducible on demand
  even now that the shipped path no longer exhibits it.

No defects found in the read-only dependencies (`skelfile.py`,
`mdlrefs.py`, `modelfile.py`, `modelexport.py`); none needed a workaround.
