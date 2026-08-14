# The model geometry arc — scope

**PROPOSAL, 2026-08-13.** A proposal until the owner adopts it, like every scope
in this repo. Written at the end of the session that landed the props-export arc
(PLAN §8, 2026-08-13 entry), because that arc ends at proxies and this is the
arc that replaces them.

**Goal:** prop model files decoded to real meshes — triangles, then UVs and
diffuse textures — landing in `tools/blender/import_gwmap.py` as instanced
geometry where the proxies stand today. The day it lands, `kamadan.blend` is
the city, not 516 cylinders.

Labels are the project vocabulary
([studies/character/FINDINGS.md](../character/FINDINGS.md)).

---

## 1. Where this arc starts, and it is not from zero

The knowledge below is MEASURED and already written up in
[studies/customarea/FINDINGS.md](../customarea/FINDINGS.md) §5 (with its §A/§B
corrections) — cited here, not restated. **What does NOT exist is committed
code**: the measurements came from study-session scratch scripts that were never
promoted, so nothing in `toolkit/` opens a model file today.

- **The container is known.** Model files are `ffna` type 2, MFT flags 515
  (a second stream of 21,420 type-2 rows carries flags 2817 — unexplored).
  Chunk map: `0xFA0` geometry, `FA1`/`FA5` texture filenames (2,048/2,048
  sampled parse; all 430 of Kamadan's resolve, ten are DDS), `FA6` (174
  sampled), `FAD` AMAT materials (479 sampled).
- **The geometry chunk is half-read.** `u32 num_models` at `+0x44`,
  `u16 collision_count` at `+0x4C`, nine-`u32` sub-model headers, `u16`
  triangle-list indices (divisible by 3 in 519/519 sub-models, 0/519 out of
  range), interleaved vertices, trailing blocks, collision meshes. Thirteen
  vertex formats observed, strides 20..84.
- **The oracle already exists, and it is strong.** The placement radius
  identity — `f11 == scale × max 2D vertex radius of the referenced model` —
  holds at 1e-5 on **12,766 of 12,875 props across 14 maps**, spans eight
  decode steps across two files, and is rotation-independent (238/238 non-yaw
  props). Every future regression in the model decode moves it. The verifier
  derived the vertex stride WITHOUT GWMB's lookup tables, so the stride source
  is independent of upstream.
- **The failures are known and separated** (§A5): ~15% of model files never
  yield a unique closing sub-model walk (the preamble between `+0x54` and the
  sub-model array is located by search, not decoded), and a disjoint ~0.5%
  close cleanly with `f11` grossly wrong. Fixing the first will not explain
  the second.
- **The texture layer is OPEN, end to end**
  ([studies/texture/FINDINGS.md](../texture/FINDINGS.md)): ATEX decode is
  client-corroborated and `atex.py`/`dxt1.py` are committed, tested toolkit
  code. The model arc's texture half is resolution + UVs, not a format
  reverse.
- **The delivery seam is standing.** `import_gwmap.py` already places every
  prop with its transform (compiled basis, measured 'ZXY' composition), scale
  and `gw_model_file_id` custom property. Replacing a proxy mesh datablock
  with a decoded one is a local change; nothing upstream of the Blender step
  moves.
- ~~**e10d gave a second cross-file oracle for free**: the client's compiler
  instances the model's own collision footprint into the Bloated stream (run
  record `vault/research/e10d-props-2026-08-12/`), so a decoded collision mesh
  can be checked against outline rings retail ships.~~
  **WRONG, AND IT WAS THIS DOCUMENT'S ERROR — struck 2026-08-13 by M3's
  recon.** e10d established no such thing. Its "the compiler also instances
  the model's own collision footprint" is INFERRED from a single navmesh
  delta on a single prop, and **that prop's model carries ZERO collision
  meshes** (file id 209883, `collision_count = 0` at +0x4C in both archives).
  e10d never opened a model file — `readback.py` imports no `modelfile` — so
  no comparison between a ring and a collision mesh has ever been made. Run
  A's compiled props record carried `points = 0` and an EMPTY ring, and the
  footprint that appeared went into the PATH chunk `0x20000008`, not the
  props stream. The transform e10d did establish for rings is TRANSLATION
  ONLY (`corresponds()` requires `x + dx`, `y + dy`, no rotation, no scale),
  and both its runs used rot (0,0,0) so it measured nothing about rotation at
  all. **M3's criterion inherited this error from here**; see §3 for what
  replaced it. The lesson is the one this repo keeps relearning: a scope
  written from a summary of a summary carries the summary's inference as
  though it were the measurement.

## 2. What is genuinely unknown (the actual work)

1. **The sub-model header semantics** — nine `u32`s, partially read. Which
   fields carry the vertex format (FVF), counts and offsets.
2. **The vertex formats' field maps.** Position is effectively pinned by the
   radius identity; normals, UVs and colour per format are not. §B6 is the
   caution: the existing 13-format accounting was fitted and tested on the
   same 519 sub-models, and disagrees with GWMB's table at least once
   (`dat_fvf 0x2C`). The second witness must be the client's own FVF
   dispatch, not more corpus.
3. **The preamble** (`+0x54` → sub-model array): the ~15% non-closing
   population, plus §B5's ~0.05% ambiguous closures — one file closes at two
   genuinely different parses, so "the walk closed" alone is not identity.
4. **Texture binding**: FA1/FA5 filename → archive row resolution is proven
   in the study; UV channel selection and AMAT semantics are not. (Diffuse
   only for this arc; AMAT beyond that is out of scope.)
5. **Model-space conventions**: winding, normals, and the local z sign
   against the world's (FINDINGS 25 negation is about the WORLD; whether a
   model's local frame shares it is unmeasured).
6. **The flags-2817 second stream** — 21,420 type-2 rows nobody has opened.

## 3. The ladder

Each rung has a criterion the artifact can refute and a kill/keep decision.
Sessions are estimates, not commitments.

| Rung | What | Criterion | Est. |
|---|---|---|---|
| **M1** ✅ | `toolkit/mapdata/modelfile.py` + `test_modelfile.py`: the KNOWN layout as committed code — chunk walk, sub-model walk, positions | **DONE 2026-08-13, criterion met exactly**: the radius identity reproduces at 12,766/12,875 (`--all`, 165 s) and 474/474 + 664/664 on the reference maps, pinned as the test's floor-guarded oracle with the 3D rival as control; closure census 1,741/1/306 and thirteen format pairs, all pinned. The reference-map model census: Kamadan 86 used models (71 close), Pre-Searing 229 (152 close — a 33.6% no-close rate against the corpus ~15%, pinned per map). **New finding**: the corpus's single `dat_fvf 0x2C` sighting is the ambiguous file 0x1BAE2's chosen parse (its rival parse is format 21), so the rare format's existence AND §B6's GWMB-table disagreement both rest on an uncertain read — M2 must settle it from the client. | 1 session |
| **M2** ✅ | The vertex-format table, client-corroborated: FVF dispatch read from the loader, field maps for position/normal/UV per format | **DONE 2026-08-13 — and it CORRECTED M1 rather than confirming it.** The client's three stride tables (VA `0x00BF5B80`/`BC0`/`BE0`, accessor `0x00688010`) replaced our byte-cost rule: the two agree on all twelve real formats and differ on 60,168 of 65,536 words, which is why a wrong rule survived a corpus-wide check. **`dat_fvf 0x2C` never existed** — its one sighting was our misparse of the ambiguous file, and the cross-file oracle confirms the fix from a source sharing nothing with the binary (that model's props: **f11 0/16 → 16/16**, the whole corpus improvement 12,766 → **12,782**). GWMB was right; §B6 resolves in upstream's favour. Field map derived from the tables' per-bit additivity and each name established by refutable prediction: **normal unit on 90,108/90,108** (control 2.7%), tangent frame unit with 93.0% orthogonality (control 26.0%), texcoords wrapping past ±16, and **bit 1's colour reading REFUTED** (small index, purpose UNVERIFIED). Test floor 34 → 57 (68 under `--all`), with the module's tables pinned to the vaulted image by the test's own PE walk. | 1 session |
| **M3** | Mesh assembly to the interchange: a `.gwmodel` sidecar family in `vault/exports/` (positions + triangles first) | A decoded mesh's max 2D radius equals `f11/scale` per instance (M1's oracle, now per-mesh); decoded collision meshes vs retail outline rings (the e10d oracle) on outlined props | 1 session |
| **M4** | Blender: real meshes replace proxies, instanced per file id, transform/scale/z-sign settled by rendering against terrain | Kamadan renders recognizably; prop mesh bottoms sit on terrain at the placement rate the proxies scored (0.7338/0.304 baselines); local z sign MEASURED, not assumed | 1 session |
| **M5** | Textures: FA1/FA5 → `atex.py` → images → Blender diffuse materials; the ten DDS get a stdlib reader | Reference-map textures resolve at the study's rate; UV sanity is statistical (coverage, seam rate) plus render inspection — stated as the weak half, because no strong UV oracle exists | 1 session |
| **M6** | (stretch) the 15% preamble decode, the 0.5% `f11` mystery, the flags-2817 stream census | Each is its own finding; none blocks M1–M5 | open |

**Order matters:** M1 before everything (the oracle must live in committed,
floor-guarded code before anything leans on it); M2 before M3 (triangles
without a client-corroborated format table would be §B6 again); M4 lands the
user-visible result; M5 is the finish.

## 4. Evidence strategy

- **The radius identity is the load-bearing oracle at every rung.** It cannot
  be forced by our decoder (it crosses two files and eight steps), and it is
  already measured, so M1's job is to make it a floor-guarded regression pin
  the way `test_props.py` pinned `corresponds()`.
- **Verbatim-first applies to the FVF table**: the client's dispatch is the
  authority; GWMB's table is UPSTREAM and the corpus fit is RECONSTRUCTION
  until the client agrees. **VINDICATED 2026-08-13 and in the direction
  nobody predicted** — this line was written expecting to correct upstream
  again (`dat_fvf 0x2C`) and the client corrected *us* instead: GWMB's tables
  ARE the client's, our corpus-fitted rule was wrong, and the only reason it
  survived M1 is that the two agree exactly where the corpus lives. Read the
  authority, not the fit, even when the fit closes 1,741 files.
- **Failure populations stay separated** (§A5's lesson): the test reports
  non-closing, ambiguous-closing and `f11`-disagreeing files as three numbers,
  never one, and the M1 floor pins each.
- **No check that cannot fail**: the sub-model walk's closure is necessary but
  not identity (§B5), so M1 must carry the two-parse ambiguous file as a named
  case, not a rounding error.

## 5. Provenance and the second gate

- **Format knowledge is MEASUREMENT** — strides, offsets, counts, field maps
  live in code and docs normally (PLAN §7 Q3 boundary).
- **Decoded output is ArenaNet's EXPRESSION.** Meshes, textures and any
  `.gwmodel`/`.blend` carrying them go to `vault/exports/` only.
  `mapexport.resolve_outdir` is the enforced precedent; `modelfile.py`'s
  writer takes the same refusal FROM BIRTH — `atex.py --make` nearly
  truncating `Gw.dat` is why write guards are not retrofitted here. Tests are
  synthetic-first with vault-gated sections, the established pattern.
- **No model bytes enter the repo, ever.** Test fixtures are built from
  `struct.pack`, as `test_props.py` and `test_mapexport.py` §4b already do.
- **Second gate:** GWMB's FFNA model pattern/sources are the obvious
  hypothesis source and its licence (permissive, credit + repo link, not MIT)
  is already satisfied for four modules. **The §6.1 row for the model-format
  pattern is added BEFORE any module borrows from it** — the `gwdat.py`
  lesson. Everything load-bearing is re-derived (corpus closure + the client's
  own loader), with upstream as the witness, which is the posture every prior
  GWMB row records.

## 6. Non-goals

- **Skeletons and animation** — props carry none (MEASURED, FINDINGS §5's
  stated negative), and creature models are a different file class.
- **AMAT materials beyond diffuse.**
- **Authoring NEW models.** Reuse-by-file-id is already the authoring route
  for populated custom areas; nothing here changes the write direction.
- **The client rendering anything differently.** This arc is entirely
  offline: archive → interchange → Blender. No client runs are required at
  any rung (the e10d oracle uses data already captured).

## 7. Kill criteria, stated up front

- If M2's client dive cannot settle the formats the REFERENCE maps use inside
  two sessions, land M3 on positions+triangles for the formats that ARE
  settled and report the rest as carried — partial geometry beats another
  fitted table.
- If the UV half has no better evidence than "the render looks right" after
  M5's statistical checks, it ships labelled RECONSTRUCTION and the doc says
  which maps it was eyeballed on.
- The ~15% non-closing population does not block anything: 85% closure covers
  the corpus's shared models heavily (80.1% of models are multi-map), and the
  census in M1 will say exactly how many of Kamadan's and Pre-Searing's
  models fall in the gap. If it is many, M6's preamble work is promoted; if
  few, proxies remain for those props and the count is printed.
  **ANSWERED by M1 (2026-08-13), and it is more than the corpus average
  suggested**: Kamadan 15 of 86 models (42 of 516 props keep proxies),
  Pre-Searing 77 of 229 (200 of 864 props — 23%). The per-map rate varies
  hard, so M6's preamble decode is worth more than the ~15% figure implied;
  it stays unblocking, but it is promoted from "stretch" to "the first thing
  to try after M4 renders".
