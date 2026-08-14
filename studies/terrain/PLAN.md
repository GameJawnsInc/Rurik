# The terrain texturing arc — scope

**PROPOSAL, 2026-08-14.** A proposal until the owner adopts it, like every scope
in this repo. Written the day the props round trip landed, because that arc ends
with a fully textured prop layer standing on **bare grey ground**.

**Goal:** the map's own surface textured — the tile byte every terrain face
already carries resolved to ArenaNet's ground texture, exported beside the map,
and drawn in Blender. The day it lands, `kamadan.blend` is a place rather than a
prop collection floating over a white slab.

Labels are the project vocabulary
([studies/character/FINDINGS.md](../character/FINDINGS.md)).

---

## 1. Why this arc exists, measured rather than asserted

Read out of `vault/exports/blend/kamadan_p.blend` in Blender itself:

```
objects:  516 props: has an imaged material
            1 other: NO material slot          <- the terrain
faces:  186368  57.0%  face has NO material    <- the terrain
        140340  43.0%  face draws an image     <- every prop
```

The terrain is **the only object in the scene with no material**, and it is 57%
of the faces and very nearly all of the visible area. Nothing is broken: the
importer attaches `gw_tile` and `gw_shade` as per-face attributes and stops
there, because nothing in this tree maps a tile byte to a texture.

---

## 2. Where this arc starts, and it is a long way from zero

Everything in this section is MEASURED, 2026-08-14, against
`vault/dat_study/Gw.dat`.

**The texture set is already in the map file.** Every map carries a
`0x21000002` *Bloated Dependencies Terrain* chunk beside its terrain data,
and `mapfile.decode_dependencies` already reads it. Kamadan's holds **51 file
ids**, every one resolving.

**Those textures decode TODAY.** All 51 are `ATTX` / `DXT3` / 256x256, and
**51 of 51 decoded to PNG** in the scratch probe that scoped this arc, using
nothing that is not already committed:

```
decoded 51 of 51 terrain textures
trailer lengths: {21923: 51}
shapes: {'DXT3 256x256': 51}
```

That works because `test_atex.py` already MEASURED what an ATTX row is: an ATEX
container with an `ffna` type-7 trailer of exactly 21,923 bytes on 106 of 106
rows, whose removal leaves a container that closes to the exact byte. The 51
terrain rows agree — a second, independent population, from a different
selection rule. **The ATEX level codec, `dxt1.py` and `png.py` are all in place**;
this arc adds no image decoding at all.

**The binding has a very strong structural signature.** Over 80 map heads:

| fact | result |
|---|---|
| `len(table_a) == len(terrain dep list)` | **80 of 80** |
| `len(table_b) == len(terrain dep list)` | **80 of 80** |
| max tile byte inside that length | **80 of 80** |
| Kamadan: distinct tile bytes / dep entries | 50 distinct, range 0..50 / 51 |

Three independent 51s on Kamadan — dependency entries, both tile tables, and the
observed tile-byte range. A tile byte names one of the map's terrain textures.

**What the corpus has NOT yet settled is which indirection.** `table_a` is the
identity `0..n-1` on **39 of 80** maps and is NOT on **41 of 80**, and the
non-identity ones carry REPEATS:

```
row 23945  dep  57  table_a starts [0, 0, 1, 2, 3, 4, 5, ...]
row 25427  dep  39  table_a starts [0, 1, 2, ..., 9, 9, 10, ...]
```

So `dep[tile]` and `dep[table_a[tile]]` are the same answer on 39 maps and
different on 41. That is a real discriminating population, and picking the
reading that happens to look plausible on Kamadan — where `table_a` IS the
identity — would be exactly the mistake `modelexport` made when it read
`material_index` as an FA5 index and put specular maps on the buildings.

**Unknowns, stated as unknowns:**

- `table_b` — Kamadan's values are `{5, 7, 13, 15, 17, 19, 21, 23, 81, 85}`,
  all ODD, so bit 0 is always set. UNVERIFIED. Not on the critical path.
- The 256x256 image reads as a 2x2 arrangement of ground variants **with
  alpha**, which is what a blended splat layer looks like. How a cell samples
  it — and therefore the UV scale — is NOT DECODED.
- Terrain tag 0 carries `tex_word = 8485`, `tex_f12 = 0.541`, `tex_f16 = 0.604`
  and `chunk_distance = 24576.0`. Named, not understood.

---

## 3. The ladder

Each rung is independently landable and leaves the tree green. The visible
payoff arrives at **T4**; T5 and T6 are quality.

### T1 — ATTX becomes a capability instead of a documented refusal — **DONE 2026-08-14**

Landed; results in [FINDINGS.md](FINDINGS.md) §1. Criterion was met on the
WHOLE corpus rather than the ≥50-map sample asked for: 349 of 349 maps, 1,656
distinct textures, **1,652 of 1,652 ATEX-family close and decode**. Two things
came out that the rung did not go looking for — ArenaNet's own 12-byte footer
declaring the boundary (an independent witness, 1,648/1,648), and the
correction that `PASS_TERRAIN_BORDERS` is used by every ATTX row rather than
"0 of 49,800". One requirement CHANGED: the terrain set is **mixed** — 1,648
ATTX, 4 plain ATEX, 4 DDS, two of which are V8U8 bump maps nothing decodes —
so T4 handles three shapes, not one.

`atex.parse` raises on 106 of 106 ATTX rows today, and `test_atex.py` asserts
that asymmetry as a finding. Promote the scratch probe: locate the trailer by
**parsing the `ffna` container**, never by the constant 21,923, and report its
length per row so a variable one is a measurement rather than a crash.

*Criterion:* every terrain texture of a ≥50-map sample decodes, the container
closes to the exact byte with the trailer removed, and the trailer length is
reported as a census rather than asserted as a constant.
*Test:* `test_atex.py`'s ATTX section flips direction and must fail if either
half regresses — a relabelled synthetic ATEX must still parse, and a real ATTX
must now decode where it previously raised.
*Risk:* low. Two independent populations already agree.

### T2 — the tile → texture binding — **ANSWERED FROM THE CLIENT 2026-08-14**

**The reading is `dep[tile]`, DIRECT.** In `TrnTexBlendLo` the raw per-cell
tile byte indexes the texture array `m_tiles` unmodified; the table it also
feeds is only ever COMPARED between a cell's four corners to decide how many
blend layers to emit, never used as an index. [FINDINGS.md](FINDINGS.md) §2.

This is a SINGLE witness from a disassembly, so the corpus half below is still
worth running as confirmation — 41 of 80 maps discriminate the two readings,
which makes a render a cheap second witness. What is no longer true is that
this rung blocks the arc.

It also produced the answer to T3's mechanism for free: terrain **tag 3**'s
2-bit plane, recorded in `terrain.py` as NOT FOUND after four dead hypotheses,
is the per-cell **tile variation selector**, which is what the four quadrants
of a 256×256 terrain texture are.

<details><summary>the original rung, kept for its criterion</summary>

State the prediction first, then decide `dep[tile]` vs `dep[table_a[tile]]` on
the **41 discriminating maps**. Two routes, and the second is the one that
counts: the client's own terrain loader (which reads the same chunk, and whose
accessor will index one of the two ways), and a statistical oracle over the
corpus.

*Criterion:* one reading survives with the rival kept as a LIVE control that
collapses, in the shape `test_modelfile.py` uses for the retired stride rule —
two live answers, not prose.
*Risk:* was **the highest in the arc**, and the reason T3–T5 were not to be
started until it landed. Everything downstream renders plausibly under the
wrong reading.

</details>

### T3 — the atlas, and where the UVs come from — **DONE 2026-08-14**

Landed; [FINDINGS.md](FINDINGS.md) §3. One cell = one 128x128 variant = 96
world units, sampling its inner 111x111 texels. The rung's own stated
hypothesis was REFUTED: the scale comes from no map field at all, only
compile-time literals plus a tile count that cancels. It also found a DEFECT
in our decoder -- the border band is regenerated by the client and we left it
zero -- which had already corrupted a measurement made in the same session.

<details><summary>the original rung</summary>

What one repeat covers in world units, DERIVED from a named field
(`tile_size`, `tex_f12`, `chunk_distance`) rather than tuned until it looks
right, with the rivals kept and required to score worse.

*Criterion:* a refutable prediction stated before the render, and a control
that a wrong scale is visibly and measurably wrong.
*Risk:* medium. May need the client's terrain shader constants.

</details>

### T4 — export: terrain textures beside the map

PNG sidecars plus a per-tile table in the `.gwmap` manifest naming each tile's
file id **and the MFT's (size, crc)** — a file id is archive state, the same
rule the props model table already follows.

*Criterion:* every distinct tile byte a map uses resolves; sha256 manifest with
a negative control; the existing refusal that keeps derived ArenaNet bytes out
of the working tree still fires.
*Risk:* low. Same shape as `modelexport.texture_payloads`.

### T5 — Blender: the ground gets a material

One material per distinct tile texture, `material_index` per face from the
`gw_tile` attribute the importer **already writes**. No shader work, no
blending — the same pattern the props use.

*Criterion:* every face's material index resolves to the texture its tile byte
names, asserted against the **sidecar** rather than against the importer's own
choice, plus a `--no-terrain-textures` control.
*Risk:* low.

### T6 — blending between tiles (DEFERRED, with the reason)

GW blends adjacent ground types, and the alpha in these atlases is presumably
how. T5 gives hard edges at tile boundaries. That is honest and a great deal
better than grey, and blending is a separate question that should not hold up
the visible result.

---

## 4. Fold in while here: the prop fall-through

Not part of this arc, but adjacent and cheap, and it is a live defect.

`gwmodel_mesh` appends every image a model owns to `mesh.materials` and only
sets `poly.material_index` for sub-models it could bind. Every other face keeps
the default **0** and silently draws whichever image landed first. MEASURED on
Kamadan: **31.6% of prop screen area** (13 of 207 sub-models, but the most
instanced ones), and for the five rock models — 123 props — slot 0 is
`tex_3C172.png`, mean rgba `[41, 39, 31]`. That is why Kamadan's rocks render
near-black.

All 13 are the AMAT path (`kind: "none"` where the geometry chunk's `mtlCount`
is 0, `kind: "binary"` where `mtlIndex` runs past the layered array). Decoding
AMAT (`0xFAD`) is the real fix and is its own arc. **The cheap half is to stop
lying**: give unbound faces their own empty slot so they read as unbound rather
than impersonating a bound surface. The render gets worse and the scene gets
honest — the same trade this repo has taken every other time.

---

## 5. What this arc does NOT do

- It does not touch the server, the wire, or any capture.
- It writes no ArenaNet bytes into the tree; every PNG lands in `vault/`.
- It does not decode AMAT, terrain blending, water, or the shore chunk.
- It does not claim the render is what the client draws. It claims each face
  carries the texture the archive names for its tile.
