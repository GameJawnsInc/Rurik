# Prop model files

Build 38797, read from the vaulted stock `Gw.exe` as a file and from
`vault/dat_study/Gw.dat` — no client was launched for any of this.

Labels are the project vocabulary
([../character/FINDINGS.md](../character/FINDINGS.md)). The ladder and its
remaining rungs are in [PLAN.md](PLAN.md).

---

## 1. The answer in one page (M1–M2, 2026-08-13)

Prop geometry is decoded and committed: `toolkit/mapdata/modelfile.py`,
pinned by `test_modelfile.py` (57 checks, 68 under `--all`).

| | |
|---|---|
| Container | `ffna` type 2. Chunks `0xFA0` geometry, `0xFA1`/`0xFA5` texture filenames, `0xFA6`, `0xFAD` AMAT |
| Geometry chunk | `u32 num_models` @ +0x44, `u16 collision_count` @ +0x4C, preamble to +0x54 **undecoded**, then sub-models, then collision meshes, closing on the exact final byte |
| Sub-model | nine `u32` header, `ti` u16 triangle indices, `nv` interleaved vertices, an opaque trailing block |
| Vertex stride | **the client's own three tables**, VA `0x00BF5B80` / `0xBF5BC0` / `0xBF5BE0`, summed by the accessor at `0x00688010` |
| Load-bearing oracle | prop `f11` == `scale × max 2D vertex radius`, **12,782 of 12,875** at 1e-5 |

**The thing worth carrying out of this arc**: a decoder that closed on 1,741
model files, kept every index in range, and satisfied a two-file oracle on
99.15% of props **still had a wrong stride rule**, and the corpus could not
show it. The client's own table could, and did.

---

## 2. The stride: our rule, and the client's (M2)

M1 shipped a byte-cost rule reconstructed from the survey — `+12` for bit 0,
`+4` for bit 1, `+12` for bit 2, `+8` per bit of `0xF0`, `+24` for any bit of
`0x3000`. It closed 1,741 of 2,048 model files and produced thirteen
`(dat_fvf, stride)` pairs.

**SOURCE-CODE.** The client computes the stride from three `u32` tables:

```
FVF0 @ 0x00BF5BE0  (16)  0 8 8 16 8 16 16 24 8 16 16 24 16 24 24 32
FVF1 @ 0x00BF5BC0  ( 8)  0 12 12 24 12 24 24 36
FVF2 @ 0x00BF5B80  (16)  0 12 4 16 12 24 16 28 4 16 8 20 16 28 20 32

0x00688010  push ebp / mov ebp, esp
0x00688013  mov edx, [ebp+0x10]        ; fvf
0x00688018  shr ecx, 0xC               ; and 0xF -> FVF0
0x0068801D  shr eax, 8                 ; and 0xF -> FVF0
0x00688028  mov esi, [ecx*4 + 0xbf5be0]
0x0068802F  add esi, [eax*4 + 0xbf5be0]
0x00688041  add esi, [eax*4 + 0xbf5bc0]   ; (fvf>>4)&7  -> FVF1
0x0068804D  add esi, [eax*4 + 0xbf5b80]   ; fvf&0xF     -> FVF2
```

The caller's file word reaches it through
`((d & 0xFF0) << 4) | ((d >> 8) & 0x30) | (d & 0xF)`.

The two rules **agree on twelve of the thirteen pairs and differ on 60,168 of
the 65,536 possible words** — they coincide exactly where the corpus lives.
That is why a wrong rule survived a corpus-wide check.

### 2.1 `dat_fvf 0x2C` never existed

The thirteenth pair, `(44, 20)`, had one corpus sighting: file id `0x1BAE2`,
the single AMBIGUOUS model file, which closed at **both** offsets 97 and 101
with every index in range under both. M1 chose the lower (97) and read format
`0x2C` there.

Under the client's tables **only 101 closes**, and the format there is the
common 21. The corpus holds **twelve** formats.

**The cross-file oracle confirms the correction from a source that shares
nothing with the binary.** That model's props:

| rule | model max 2D radius | props whose `f11` matches |
|---|---|---|
| our byte-cost (M1) | 1269.62 | **0 of 16** |
| the client's tables (M2) | 40.13 | **16 of 16** |

and that is the entire corpus-wide improvement, 12,766 → **12,782 of 12,875**.
§A5's unexplained population shrinks from 109 props to 93.

**GuildWarsMapBrowser was right and we were wrong.** Its FVF tables *are*
these client tables; [../customarea/FINDINGS.md](../customarea/FINDINGS.md)
§B6 recorded "the byte-cost rule disagrees with GWMB's table once
(`dat_fvf 0x2C`)" as an open question, and it resolves in upstream's favour.
No GWMB code or table is used — the tables here were read out of the client.

### 2.2 The ambiguity moved rather than vanished

Under the client's tables a **different** file is ambiguous — `0x25AA9`,
closing at 170 and 65,842 — while `0x1BAE2` became unique. The aggregate
census is unchanged at 1,741 unique / 1 ambiguous / 306 no-close, which is a
coincidence of composition, and exactly the kind of thing a census-only check
would hide. Both rules pick 170 for `0x25AA9`, so nothing downstream moves.

---

## 3. The vertex field map (M2)

**MEASURED.** All three tables are additive over their bits — each of the 40
entries equals the sum of its set bits' costs — so the client's own data
states every field's size:

| `dat_fvf` bit | bytes | field | how it was established |
|---|---|---|---|
| 0 | 12 | position `f32 x,y,z` @ offset 0 | the `f11` oracle |
| 1 | 4 | a small **index** | **UNVERIFIED** — see below |
| 2 | 12 | **normal**, unit | unit on **90,108 / 90,108**; control 2.7% |
| 3 | 4 | — | absent from every corpus format |
| 12, 13 | 12 each | **tangent frame**, unit | unit on 10,017/10,017 each; bit 12 ⟂ normal on **93.0%**, control 26.0% |
| 4–11 | 8 each | **texcoords** `f32 u,v`, up to 8 sets | 97.8% within ±16, range −519.7 … 520.4 |
| 14, 15 | — | dropped by the remap | cost nothing |

Field **order** within a vertex is the client's table order (bits 0–3, then
12–13, then 4–11). A permutation would give the same stride, so the order is
corroborated by the unit-length tests landing at the offsets that order
computes and collapsing four bytes away — not by the total.

**Each name is a refutable prediction, never an inference from a size.** That
rule exists because `envchunk.py`'s tag 6 was named "the main environment
record" from its size alone and turned out to be the water record.

### 3.1 Bit 1 is not a colour

The D3DCOLOR reading is **REFUTED**: its high three bytes are zero on
9,128 of 9,128 sampled vertices and its low byte takes ten values, all ≤ 9.
It is a small integer index. Naming it (matrix index? material slot?) would
be the size-inference mistake again, so it stays **UNVERIFIED** and
`modelfile.py` carries it as bytes.

### 3.2 Retail UVs wrap

97.8% of texcoords sit inside ±16, but the full range is −519.7 … 520.4. A
consumer must wrap, not clamp — recorded because clamping would look correct
on nearly every vertex and destroy the rest.

---

## 4. The interchange, and what checking it found (M3)

`toolkit/mapdata/modelexport.py` writes a `.gwmodel` family to
`vault/exports/models/`, keyed by file id because 80.1% of prop models are
used by more than one map. Pinned by `test_modelexport.py` (44 checks, 45
under `--all`).

### 4.1 De-interleaving is what makes the export checkable

A model file stores vertices interleaved at a stride of 20–84 bytes. The
exporter splits them into typed per-field arrays — a real transformation, not
a copy — so the arrays can be put back together and compared against the
bytes ArenaNet wrote:

> re-interleave(exported arrays) == the geometry chunk's own vertex bytes,
> read fresh from `Gw.dat`

**519 of 519 sub-models over both reference maps, all nine formats.** The
re-interleaver lives in the test, written out of `struct.pack_into`, sharing
no code with the module it checks.

**It failed on its first run, and that is the point.** The exporter's first
version silently dropped `dat_fvf` bits 12/13 — the tangent frame, 24 bytes a
vertex — on every format carrying them. Six sub-models of format 12405 failed
the comparison; **nothing else could have noticed**, because a dropped field
costs no vertex, no triangle and no radius, and the mesh renders fine. Byte-
exactness is also what forces the two unnamed fields (bits 1 and 3) to be
carried verbatim.

### 4.2 The oracle survives serialisation

`f11 == scale × max 2D radius` now runs through the written interchange: the
radius is recomputed from the exported position sidecar **read back off
disk**, against prop records in a map file the module never opens. **474 of
474 and 664 of 664**, equal to `test_modelfile.py`'s in-memory figures — the
stated prediction, since serialising must not change the geometry.

### 4.3 Collision meshes: invariants the decoder cannot force

`ModelGeometry.decode` validates render indices only — its refusal loops over
`submodels` and never touches `collisions`, asserted on its own source — so
these are facts about ArenaNet's bytes rather than about our decoder. Over
both reference maps (25 models, 28 meshes):

| claim | result | control |
|---|---|---|
| every collision index < its mesh's `nv` | **2,265 / 2,265** | unforced by the decoder |
| every mesh is a triangle list (`ni % 3 == 0`) | **28 / 28** | rival header order `(nv, ni)`: **7 / 28** |
| every collision vertex is referenced | 28 / 28 | — |

The rival-order control is what pins the collision header's field order as
`u32 ni` first. Corpus-wide (14-map sample, an independent agent's census):
141 of 1,742 closed models carry one (8.09%), 148 meshes, `nv` 4–158 (median
15); collision and render meshes share a coordinate space (radius ratio
median 0.92, null pairings collapsing); and they are **open surfaces, not
hulls** — 0 of 148 closed manifolds, 133 of 148 disc-like.

### 4.4 The oracle this rung was scoped around does not exist

M3's criterion said a decoded collision mesh could be checked against the
outline rings retail ships, citing e10d. **That was this study's own error,
and it propagated from [PLAN.md](PLAN.md) into the rung.** What e10d actually
establishes:

- Its "the compiler also instances the model's own collision footprint" is
  **INFERRED from a single navmesh delta on a single prop**.
- That prop's model (file id 209883) carries **zero collision meshes** —
  `collision_count = 0` at +0x4C in both archives. So the attribution is
  **refuted for the only instance ever run**.
- e10d **never opened a model file**: `readback.py` imports no `modelfile`.
- Run A's compiled props record carried `points = 0` and an **empty ring**;
  the footprint that appeared went into the **path chunk `0x20000008`**, not
  the props stream.
- The ring transform e10d did establish is **translation only** (`x + dx`,
  `y + dy`), and both runs used rot (0,0,0), so it measured nothing about
  rotation.

And the populations make the check untestable anyway: on the reference maps,
props with a ring and props on a collision-carrying model are **disjoint** —
Kamadan 46 and 30 with **0** both, Pre-Searing 34 and 23 with **0**. Corpus-
wide it is 28 of 14,095, about what independence predicts (~44), so there is
no anti-correlation to report either. *(The first reading of this — "disjoint,
therefore anti-correlated" — was itself the §B4 small-sample trap, caught by
widening from 2 maps to 14.)*

Section 5 of the test pins those populations so the negative survives as a
measurement. §4.3's invariants are what replaced it.

### 4.5 Which checks are load-bearing, measured

Eight sabotaged exporters were built and the suite run against each:

| sabotage | checks reddened |
|---|---|
| drop normals | 2 (re-interleave 0/33) |
| drop the tangent frame | 2 (re-interleave 32/33 — only **one** default-sample sub-model has one, so the population guard beside it is what really holds this) |
| drop the unnamed fields | 2 (re-interleave 27/33) |
| `vertex_base` always 0 | 3 (re-interleave 17/33) |
| truncate a vertex | **9** — and **0** before the read-backs were guarded |
| weaken `resolve_outdir` | 1 (the default-destination check alone) |
| memcpy loader | **0** — correctly: its files are still right |
| memcpy loader **+ corrupted sidecar** | **1**, and only `_sidecar_positions` |

Two of those are worth carrying:

**A truncated vertex array killed the run rather than failing it.** It raised
`IndexError` inside section 3; the process died, the two headline checks never
executed, and `checks.py` never reached its verdict — no banner, no floor
shortfall. That is the one failure the ledger cannot see, and
`test_content.py` records the same shape. The read-backs are now guarded and
the exception is itself a named check, because a bare `try/except` would have
replaced the traceback with silence.

**The memcpy loader exposed that every check read geometry through
`load_model`.** A loader that stashes the source block and rebuilds its arrays
from it passes the re-interleave *and* both f11 oracles. On its own that is
harmless — the written files are still correct — but pair it with a corrupted
sidecar and nothing saw the defect. `_sidecar_positions` unpacks the file with
`struct.unpack` and never calls the module's loader; against that pair it is
the only check that fires.

## 5. Blender, and the z sign (M4)

`tools/blender/import_gwmap.py` gives each prop ArenaNet's real geometry when
a `.gwmodel` family sits beside the map export. **Kamadan: 516 props over 71
mesh datablocks. Pre-Searing: 864 over 152** — one datablock per model file
id, shared by every prop using it. Both maps render recognizably (§1's goal
for this rung): Kamadan as crenellated walls, palms, awnings and a domed
building; Pre-Searing as forested hillsides with a bridge.

A prop whose model does not decode keeps its measured proxy, so a placement
is never lost — 200 of Pre-Searing's 864. `obj["gw_real"]` says which path a
prop took and `--proxies-only` forces the proxy path as a control.

### 5.1 Model-space z shares the world's convention

**MEASURED, which is what the rung required.** Scoring every prop of both
reference maps by whether its geometry ends up ABOVE the terrain it stands on
— things rest on the ground, they do not hang under it:

| | Kamadan | Pre-Searing |
|---|---|---|
| negate model z (the terrain's convention) | **73.2%** | **83.3%** |
| leave it as stored | 23.8% | 6.5% |

Scored again at object level, off the meshes Blender actually built:
**0.961 above ground against 0.032** for a control that reflects each mesh
about its own placement point.

The diagnostic that explains it: a model's own z runs from about **+34 to
−642** (median over Kamadan's 71 decoded models), i.e. it extends from just
under its origin far into negative z — which is *up* once negated, exactly
what a tree or a wall standing on its base should do.

One honest note on method: a null control that shuffles which model each prop
points at does **not** collapse (63.1% / 81.5%). That is expected and is
stated rather than buried — the metric tests the *sign*, not model identity,
and it is the sign flip that has to fail. It does.

### 5.2 What M4 did not settle

Which of `dat_fvf` bits 12/13 is tangent versus binormal is still open. It did
not need settling here because nothing yet lights the meshes; it becomes real
at M5, when materials arrive.

## 6. What is still unknown

- **The preamble** (+0x54 → sub-model array) — located by search, so ~15% of
  files never close (Kamadan 15/86 models, Pre-Searing **77/229**). Per-map
  rates vary far more than the corpus average suggests.
- **§A5's second population**: 93 props whose model closed cleanly and whose
  `f11` is grossly wrong. Disjoint from the no-close files; unexplained.
- **Bits 1 and 3** of the format word.
- **Which of bits 12/13 is tangent vs binormal**, and why 7% of tangent-frame
  vectors are not orthogonal to their normal (UV seams and mirrored shells
  are the expectation, unmeasured).
- **The sub-model `unk` word and the trailing blocks.**
- **The flags-2817 stream** — 21,420 type-2 rows nobody has opened.
- **Texture binding**: `0xFA1`/`0xFA5` → archive rows resolve (all 430 of
  Kamadan's), but UV-set → texture-stage assignment is not established. M5.

---

## 7. Provenance

The three tables are **strides** — explicitly on the permitted side of the
gate (`PLAN.md` §7 Q3: levels, bounds, counts, **strides**, ids, offsets,
addresses, layouts). They are 40 integers, they live in `modelfile.py` with
their VAs and their build, and `test_modelfile.py` §5 re-reads them out of the
vaulted image through its own PE walk and requires the literals to match — so
the module's copy is pinned to ArenaNet's bytes rather than to a
transcription, and a build change is a red test rather than silent drift.

`modelfile.py` is read-only and has no writer. **M3's writer
(`modelexport.py`) treats a decoded mesh as ArenaNet's EXPRESSION** — the
strictest case — and its guard was present from birth rather than retrofitted,
because `atex.py` once shipped a writer with no guard at all. It DELEGATES to
`mapexport.resolve_outdir` rather than reimplementing the rule, so there is one
implementation and one behaviour; the test asserts the delegation and requires
both to refuse the same tree, each refusal beside a positive control that an
ordinary scratch path is still allowed.
