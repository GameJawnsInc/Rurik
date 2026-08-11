# Can we author a custom area?

Six survey tracks, each adversarially re-verified by a second agent, then synthesised.
This document is the synthesis. Where the verifier weakened or refuted a survey claim,
the corrected claim is what appears in the body and the correction is recorded in
§11 — the corrections are the most instructive part of the pass.

Two corrections in §11 were found during synthesis rather than by either the surveyor
or the verifier, and one of them dissolves what a whole track called its strongest
result. That is a fact about how this document was made: nothing here was accepted
because two agents agreed.

## Labels

| Label | Meaning |
|---|---|
| **MEASURED** | Checked against real bytes on this machine. We say which bytes. |
| **SOURCE-CODE** | Read in some project's source, including ArenaNet's own compiled-in asserts. Nobody's source is ground truth. |
| **INFERRED** | Our reasoning on top of the above. |
| **NOT FOUND** | We looked and there is no answer in what we have. This is a real result. |

Corpus throughout is `C:\gd\Rurik\vault\dat_study\Gw.dat` (4,198,489,600 B,
177,341 addressable MFT rows) and the vaulted stock client
`vault/client/2026-07-29_221c13772c7a/Gw.exe`, build 38797. "349/349" means every
map-flagged row in the archive. Nothing in the repo was modified; the archive was
opened read-only; no client was patched or launched.

---

## 1. The honest answer

**Yes, and the two halves cost wildly different amounts.**

**The export half is nearly done and the rest is a weekend.** Terrain is readable
today — the chunk's `{u8 tag, u32 size}` record walk closes to the exact final byte
on 349 of 349 maps (MEASURED), the heightmap is raw `float32`, one sample per cell,
on a **96.0-unit pitch that two different chunks agree on in 349/349** (MEASURED),
the storage order is 32×32 tiles with grid row 0 at world maxY (MEASURED, argmax on
345 of 346 maps against four rival layouts), and prop placements are fully decoded
with a cross-file identity that validates eight decode steps at once (MEASURED,
12,766/12,875). A Blender importer is a few hundred lines over three files, and
GuildWarsMapBrowser ships a prebuilt `.exe` whose JSON export is an external oracle
we can compare against without copying a line of its code.

*"A weekend" is the decoding estimate and it excludes the interchange conventions,
which are **not** settled: the height sign, the up axis, and whether a sample sits at
a cell centre or a cell corner are all open (§12), and §11-D quietly resolves the last
of those in the opposite direction to §2. Those three are the entire job for a Blender
importer. The available oracle does not settle them either — it commits to its own
answer: GWMB's `Terrain.cpp::GenerateTerrainMesh` **negates every height**, flips the
row order, and builds a `(dims+1)²` vertex grid. See §16-P5/P6; the transform between
our convention and its must be declared before B3 runs, or B3 goes red on a correct
implementation.*

**The import half is a month, and it is a month of *experiments*, not of decoding.**
Writing the archive is not the blocker — that is close to solved. The blocker is
that **nobody has ever built a Guild Wars 1 map**, so nothing tells us what the
client demands of a map file it did not write. Every one of the 21 mirrored
repositories reads the archive; not one writes a map, and the community's entire
modding tradition is TexMod texture replacement, which cannot add geometry
(SOURCE-CODE + four differently-shaped web searches). That is *nobody tried*, not
*somebody tried and hit a wall* — but it means there is no oracle for the output
side except the client itself.

**The single hardest blocker, named precisely:** the client loads a map from the
*Bloated* stream, and four of that stream's chunks (Terrain, Zones, Props, Path)
plus one it *generates* (Sight) account for 708 of the 724 decompressed megabytes in
the corpus, of which we can currently emit only Terrain's framing and Path's record
layout. **But the client also carries its own map compiler.** The *Stripped* stream —
the second MFT row every map has — holds the Path chunk as **19 + 8n bytes: a
boundary polygon and nothing else** (MEASURED, 349/349), against 156 MB of
Bloated trapezoid meshes corpus-wide, and holds Sight as a **9-byte stub** against
29.9 MB. `PathBuild.cpp` in the shipping binary is a full trapezoidal-decomposition
builder with a point-location DAG (SOURCE-CODE, 28 asserts), and `MapData.cpp:997`
says *"Only clients can bloat client maps"* (SOURCE-CODE). So the navmesh may not
need to be authored at all.

Whether that path is reachable is the question everything turns on, and it is
**NOT FOUND**. The only bloat driver we have traced runs *after* a failed Bloated
load (`Map file '%s' failed to load. Attempting to re-bloat.`) and writes its result
back into `Gw.dat` — but the driver at `0x00707330` has a second caller nobody has
followed.

> **ANSWERED 2026-08-10 by rung C0 — see §17.** The client does **not** compile a map
> on a normal load. `0x00707330` has exactly two callers and neither is on the load
> path: one is reachable only after a failed stream open or a failed chunk parse, and
> the second (`0x00707EEB` — the untraced one this paragraph names) is not inside
> `MapLoad` at all but inside the **content-download / patch-install** pipeline. The
> decisive independent measurement: `s_chunkInfo+0x18` is loaded by **exactly one
> instruction in the entire 10.5 MB image**, inside the stage converter, whose only
> caller is inside the driver.
>
> **But the compiler is still reachable, deliberately.** The repair reads the *other*
> MFT row — normal load requests stream 1, the re-bloat requests stream 0, the
> write-back targets stream 1 — so publishing a Stripped boundary polygon and making
> the Bloated stream fail gets the client to compile a navmesh for us and write it into
> `Gw.dat`. The cheapest trigger is a **zero-length** stream-1 payload. That is rung E3,
> and it is now specified rather than hoped for.

**The smallest experiment that moves it is offline, and this document originally got
that wrong.** The draft recommended a caged launch (rung C2) as the cheapest next
move. The completeness critic refuted that on the pass's own terms, and the
correction stands as §16-P1: **not one chunk `load` handler was disassembled.** Six
rows of §12 say *"read the handler at 0x007129F0 / 0x007125E0 / 0x007131E0"*; all
three addresses were already extracted from `s_chunkInfo` in this very pass, capstone
is inside the read-only carve-out and was used all day — for the dispatch table, the
bloat gates, the stage converter and the BSP index space — and never once on a
chunk's own load body. The same hole sits under this section's central argument: the
second caller of the bloat driver, at `0x707eeb`, was never followed.

> **Rung C0 — an afternoon with capstone, no launch, no authored bytes.**
> Disassemble the Map Parameters load handler (`0x007129F0` — does anything read the
> 349-distinct 16-byte field?), the Path load handler (`0x007125E0` — what is
> `sequence`, and what does `PATH_SEQUENCE_FAST_SAVE` deserialise?), and follow
> `0x707eeb` to find out whether bloat runs on a normal load or only as the
> post-failure repair.

That is cheaper than C1 or C2, it runs against a vaulted binary with no client
launched, and it answers the questions C1 and C2 **cannot** — including the one this
section calls pivotal. The launch experiments stay on the ladder; they are no longer
first, and their specification has three defects the critic found and §9 now carries:
the negative control's expected outcome is *the client writing into `Gw.dat`* through
a revert mechanism §8 proves incomplete (§16-P2), the arrival point lands outside the
map (§16-P3), and the target row's "unclaimed" status is not derivable from any source
we are licensed to rely on (§16-P7).

---

## 2. What we can read today, what needs known work, and what is genuinely unknown

### Readable today, no new decoding

| Thing | Status |
|---|---|
| Archive container, MFT, file-id table, decompression | MEASURED, implemented, tested (`toolkit/mapdata/`) |
| Map file discovery: 349 map rows, each with a Stripped partner | MEASURED 349/349 |
| Chunk table walk to the exact byte, both stages | MEASURED 698/698 |
| Chunk id decomposition and ArenaNet's own name for all 23 kinds | SOURCE-CODE + MEASURED |
| Terrain: dims, heightmap, tile indices, tile table, all size laws, tile layout, world pitch, orientation | MEASURED 349/349 |
| Navmesh: planes, trapezoids, neighbours, portals, obstacles | MEASURED, implemented (`pathmap.py`) |
| Prop placements: position, orthonormal rotation basis, scale, radius, model reference, footprint ring | MEASURED 349/349 |
| Prop model geometry: triangle-list indices, interleaved vertices, 13 vertex formats | MEASURED, ~85% of model files |
| Every dependency reference a map makes: 134,290 refs → 21,998 distinct rows | **Resolution** MEASURED 134,290/134,290; **payload typing sampled n≈32–40 per kind**, not corpus-wide (§16-P8) |
| Map bounds, and the fact they do **not** reliably contain the navmesh | MEASURED 289 inside / 60 outside |
| Three archive checksums | MEASURED, implemented |

### Reachable with known work (decoding, no client needed)

- **Terrain record payloads.** The *framing* is solved on 349/349; the *contents* of
  tags 3 (2 bits/cell), 4/5 (the tile-type tables), 7 (per-32×32-block, variable +
  128-byte tail) and 9 (one full-range u8/cell) are not. The client names the
  codecs: `TrnCodecShadow.cpp`, `TrnTexLight.cpp`, `TrnBitStore.h`.
- **Props record layout in the Bloated stream.** Variable-length with a
  per-prop bounding-vertex tail; the count is proven correct (349/349 agreement
  across stages), so the array's start is not in doubt.
- **Zones (0x03).** Undecoded in both stages. 349/349 present, ~1,548 distinct
  model files referenced. GuildWarsMapBrowser's `Chunk5` reader desyncs after 4–6
  elements when reimplemented; a `{u8 tag, u32 size}` walk closes at no start
  offset 0..16.
- **Sight (0x11).** 29.9 MB corpus-wide, opaque past `THGS`/version 2. **Generated**
  by the bloat step, not transformed — Stripped Sight is a 9-byte stub in 349/349.
- **The model file preamble** between the geometry chunk's `+0x54` and the sub-model
  array. We locate the array by searching for the offset at which the walk closes;
  ~85% of model files yield a unique closing offset.
- **Stripped Terrain**, which is bit-packed through `TrnCodecHeight`.

### Genuinely unknown

- **Which stream the client renders.** MEASURED: only the Bloated row is
  addressable (0 of 349 Stripped rows carries a file id). That proves a *server*
  cannot name Stripped; it does not prove what the *client* reads.
- **Whether the client bloats on a normal load or only after a failure.**
- **What makes a map file acceptable** beyond the per-chunk magic/version gates.
  Two cross-file identities exist that a writer would have to reproduce (§7).
- **Whether the Path chunk's neighbour indices are validated or merely used.**
- **Whether the client re-grids or resamples the heightmap**, and whether the
  samples are cell centres or corners (three conventions scored; the two reference
  maps rank them differently — NOT FOUND).
- **What height a bridge or a second storey sits at.** The heightmap is
  single-valued per (x,y) and the navmesh has no z. `FORMAT.md`'s standing negative
  is unchanged, and sharpened: the height exists, attached to a *prop*, not to a
  plane.

---

## 3. The chunk census

A map file is an ArenaNet "Riff" (`ffna`) container, type 3. The chunk id decomposes
as `(stage << 28) | (chunkType << 24) | baseId` — stage 1 = **Stripped**, 2 =
**Bloated**, 0 = **Raw** (never shipped); chunkType 0 = **Data**, 1 =
**Dependencies**. Those are the client's own UTF-16 strings, read from
`s_stageText` @ `0xBF7128` and `s_typeText` @ `0xBF7134` (SOURCE-CODE, re-read
independently by the verifier). The `chunkType << 24` term is INFERRED from
`chunkType < arrsize(s_typeText) == 2` plus the archive's own bit-24 histogram —
the composition site only ORs a constant.

`s_chunkInfo` @ VA `0x00A6CF78` is 23 records × 40 bytes: `load` at +8, a cost
`f32` at +32, a UTF-16 name at +36 (SOURCE-CODE; the stride is refutable — 40 bytes
decodes 23/23 names as clean UTF-16, while 32/36/44/48 give 0/3/3/4, and the code
indexes with `lea eax,[eax+eax*4]` then `[eax*8 + 0xa6cf78]`).

MEASURED over all 349 Bloated files (8,047 chunks) and all 349 Stripped files
(8,047 chunks): stage nibble is 2 in 8,047/8,047 and 1 in 8,047/8,047; chunkType is
only ever 0 (11,590) or 1 (4,504); no baseId ≥ 0x17. Nineteen of the 23 baseIds
occur. **The four that never occur are exactly the four with a NULL `load`
pointer** — and that is causal, not correlational: the loader's chunk loop asserts
both `ptr->id < arrsize(s_chunkInfo)` (MapData:4415) **and** `info.load != NULL`
(MapData:4417) for every chunk, and MapData:4557 says
`mapType != MAP_TYPE_EDIT || mapStage == MAP_STAGE_RAW` — edit-type maps exist only
at stage Raw (SOURCE-CODE).

Four map-type manifests are compiled in at `0xa6d498`, 16 bytes each, ending exactly
where the first chunk name begins: **type 0 = 19 chunks (what ships)**, types 1 and 3
= 21 (they add the two Editor slots), **type 2 = 9 — the server map**
(SOURCE-CODE). The type-0 manifest's 19 baseIds are member-for-member the 19 the
archive independently yields.

### Data chunks (type 0)

| baseId | ArenaNet's name | Present | Bloated total | Stripped total | Bloat does | Magic / ver |
|---:|---|---:|---:|---:|---|---|
| 0x00 | Header | 349 | 8 B ea | identical | — | `0x39871124` v3 |
| 0x02 | **Terrain** | 349 | **471.2 MB** | 220.2 MB | transforms | `0x87821134` v17 |
| 0x03 | **Zones** | 349 | 3.9 MB | 1.53 MB | transforms | `0x59220320` v10 (u16 `0x010A` Stripped) |
| 0x04 | **Props** | 349 | 50.3 MB | 7.13 MB | transforms | `0x39583392` v17 |
| 0x06 | Water | 349 | 5 B ea | identical | — | none (u32 1 + 1 flag) |
| 0x07 | Mission | 349 | small | identical | — | `0x40010020` v10 |
| 0x08 | **Path** | 349 | **156.5 MB** | **48,671 B total** | transforms | `0xEEFE704C` v12 (u8 in Stripped) |
| 0x09 | Environment | 349 | small | identical | — | `0x92991030` v16 |
| 0x0A | Locations | 349 | 13 B ea | 9 B ea | pads 4 B | `0x090923F8` |
| 0x0C | Map Parameters | 349 | 41 B ea | identical | — | `0x5943EEEF` v2 |
| 0x0E | Collision | 349 | 9 B ea | identical | — | `0xFA9A8550` |
| 0x0F | Light | 349 | small | identical | — | `LITE` v2 |
| 0x10 | Shore | 349 | 1.8 MB | identical | — | `SHOR` v3 |
| 0x11 | **Sight** | 349 | **29.9 MB** | **3,141 B total (9 B ea)** | **generates** | `SGHT` v2 |
| 0x12 | Sound | 349 | small | identical | — | `msnd` v2 |
| 0x13 | CubeMap | 207 | 3.9 MB | identical | — | `CUBE` v2 |
| 0x14 | VisData | 235 | 4.6 MB | identical | — | `VISD` |
| 0x15 | Occluders | 117 | small | identical | — | `BCUF` v1 |
| 0x16 | PathEngine | **1** | 69,570 B | identical | — | `mesh` v0 |

Never occur: 0x01 *Editor (old)*, 0x05 *Obsolete (1)*, 0x0B *Obsolete (2)*,
0x0D *Editor* — the four NULL-load slots.

### Dependencies chunks (type 1)

All share `0x29939830` / version 1, then 6-byte entries `{u16 id0, u16 id1, u16 pad}`.
`(size − 5) % 6 == 0` in 2,252/2,252 chunks; the third u16 is 0 in all 134,290 entries
(that it is *padding* is INFERRED). File id `= (id0 − 0xFF00FF) + id1 × 0xFF00`.

| Kind | Present | Refs | **Distinct rows** | Payload type |
|---|---:|---:|---:|---|
| Terrain (`0x21000002`) | 349 | 17,113 | 1,656 | ATTX (overwhelmingly; see §11-F) |
| Zones (`0x21000003`) | 324 | 41,896 | **1,548** | `ffna` type 2 (models) |
| Props (`0x21000004`) | 346 | 60,096 | **18,733** | `ffna` type 2 + ATEX |
| Water (`0x21000006`) | 349 | 11,168 | **32** | ATEX — **the same 32 files in all 349 maps** |
| Environment (`0x21000009`) | 347 | 2,877 | 303 | ATEX + DDS + `ffna` type 8 |
| Shore (`0x21000010`) | 208 | 319 | 7 | ATEX |
| Sound (`0x21000012`) | 329 | 821 | 633 | `ffna` type 8 |

**All 134,290 references resolve; 0 unresolved** (MEASURED). The null model was
measured rather than asserted: a random id in the observed range resolves 45.1% of
the time, and a `+1` perturbation still resolves 67% — so *one* reference resolving
is weak evidence and only the 134,290-for-134,290 sweep is strong.

### Chunk order

Chunk order is a **single total order**: 321 ordered pairs observed, **0 contradictory
pairs**, in both stages. The 17 mandatory chunks appear in exactly one relative order
in 349/349 maps; 32 distinct full orders once the optional chunks interleave. The
longest ordering has 25 entries and 348/349 files are subsequences of it; the
exception is row 26209, which appends PathEngine.

### The two streams

**A map is two MFT rows.** All 349 Bloated rows (flags 259) carry exactly one
`nextStream` partner; all 349 partners are flags 1, `ffna` type 3, and carry
**stage-nibble-1 chunk ids**. Chain depth is 1 in 349/349. **0 of 349 partners
carries a file id of its own**, and every Bloated row carries exactly two.
A full scan of all 21,769 compressed flags-1 rows yields exactly
`{ffna type 2: 21,420, ffna type 3: 349}` — the 349 partners are the only type-3
files outside the map rows (MEASURED; this is a completeness check nobody had run).

Masking the stage nibble, **20 chunk kinds are byte-identical between a map's two
stages wherever both carry them** (13 Data + all 7 Dependencies). Eleven of those
occur in all 349 pairs; nine occur in 117–347. Only six differ, and substantively
there are **four transformed (Terrain, Zones, Props, Path), one generated (Sight),
and one four-byte pad (Locations)**.

---

## 4. Terrain

Chunk `0x20000002`. **Header is 8 bytes** — `u32` signature `0x87821134`, `u32`
version 17 — then `{u8 tag, u32 size, payload}` records from +8, terminated by
`{255, 0}`. (The Stripped form reads better as `u16` version 17 plus a `u16` that is
0 in Bloated and `0x6088` in Stripped.) Note the **pathing chunk's header is 12
bytes, not 8** — a writer that assumes one header length emits a broken chunk.

The walk closes on the physical final byte in **349/349**, on a hardened walker that
does *not* stop at tag 255. Two tag sequences exist:

- `0, 1, 2, 4, 5, 3, 9, 7, 255` — **325 maps**
- `0, 1, 2, 4, 5, 3, 9, 7, 3, 255` — **24 maps** (a second, 17-byte tag-3 record)

Controls: reading the record as `{u32 size, u8 tag}` fails 349/349; the correct
framing started at offset 12 instead of 8 fails 349/349.

### Records

| Tag | Size law | Status | Content |
|---|---|---|---|
| 0 | exactly 26 B, 349/349 | MEASURED | `u32 dimX`, `u32 dimY`, `f32` (24576.0 ×348 / 55296.0 ×1), `f32` angle (0.0989–1.5461 rad, 55 values), `u16`, `f32`, `f32` |
| 1 | `dimX*dimY*4`, 349/349 | MEASURED | float32 heights, **every value an exact integer** across ~64 M samples; corpus range −19,632 .. 5,002 |
| 2 | `dimX*dimY`, 349/349 | MEASURED | one u8 per cell, index into tag 4's table (max ≤ n−1 in 349/349, equality in 332) |
| 4 | `u8 n` + n bytes, 349/349 | MEASURED | tile-type table; n = 3..63; identity permutation in only 252/349, so it is real |
| 5 | `u8 n` + n bytes, same n, 349/349 | MEASURED | parallel to tag 4 |
| 3 | `dimX*dimY/4`, **349/349** | MEASURED | 2 bits per cell; all-zero in ~155 maps |
| 9 | `dimX*dimY`, 349/349 | MEASURED | one full-range u8 per cell (lighting/shadow) |
| 7 | `(dimX/32)*(dimY/32)` blocks of `{u32 k, k bytes, 128 bytes}`, 349/349 | MEASURED | per-32×32-block; 59,051 blocks corpus-wide |
| 3′ | 17 B, in 24 maps | MEASURED | `u8 0x01` + four `f32`; the last three floats are byte-identical across different maps |

### World geometry

**The cell pitch is 96.0 world units, established three ways.**

1. MEASURED: `(maxX−minX)/dimX` and `(maxY−minY)/dimY` from the Map Parameters
   chunk `0x2000000C` (41 B: `u32 0x5943EEEF`, `u8` version 2, four `f32`
   `x0,y0,x1,y1`, then five undocumented `u32`) give **exactly one distinct value
   across all 349 maps: (96.0, 96.0)**, at 1e-6. Two chunks written by different
   subsystems predicting one another; one grid row of error anywhere produces a
   second value. A `(dim−1)` divisor gives 96.15–96.50 — it visibly failed first.
2. MEASURED from the binary: `TrnDataBloat:191` compiles to
   `fmul qword ptr [0x94DE10]`, and that qword is the IEEE double **96.0**. The
   register offsets `[esi+0xC]/[+0x10]/[+0x14]/[+0x18]` independently pin the
   mapRect field order to `x0,y0,x1,y1`.
3. The field GuildWarsMapBrowser calls `cellSize` is **not** the cell size — it is
   24576.0 = 256×96 on 348 maps and 55296.0 = 576×96 on one, constant across 104
   different grid sizes. (This was already recorded in
   `studies/mapdata/FORMAT.md`; Track 6 re-derived it without citing it.)

Grid dims are a multiple of 32 in 349/349 — the client's `CHUNK_SIZE`, which is
MEASURED from the binary twice: `TrnCodecHeight:166/167` compile to
`test byte ptr [esi],0x1f` / `test byte ptr [esi+4],0x1f`, and `TrnChunkBox:150`
compiles to `cmp esi,0x155` = 341 = (4⁵−1)/3, so `CHUNK_SIZE_LOG2 == 5`. Observed
dims: 104 distinct pairs, dimX 32..768, dimY 32..1024, **largest by area 768×384**;
`TrnCreate:52/53` caps both at 4096.

### Storage layout

```
index(gx, gy) = ((gy>>5) * (dimX>>5) + (gx>>5)) * 1024 + (gy&31) * 32 + (gx&31)
gx = int((wx - x0) / 96.0)
gy = int((y1 - wy) / 96.0)          # grid row 0 is world maxY
```

MEASURED corpus-wide by a cross-chunk test: prop z from chunk `0x20000004` against
terrain height, aligned by the mapRect. Over the 346 maps with props, tile-row-major
/ cell-row-major is the **argmax on 345**, median fraction of props within 100 units
**0.504** against 0.247 (nearest rival), 0.089 (the flat row-major layout upstream
implies), 0.087, 0.063. The orientation `row0 = maxY` beats the y-flip control on
**345 of 346** (0.504 vs 0.082). One map prefers an x-flip.

An **independent structural corroboration was attempted and failed**, and we report
the null: tag 7 gives exactly one block per 32×32 tile, so block *k*'s payload length
should track the variance of `H[k*1024 : (k+1)*1024]` if the grouping is right — a
statistic blind to within-tile ordering. Over 25 maps the Spearman correlation has
median 0.181 and is negative on 8, against a shuffle control at −0.028. Tag 7's
payload length is not driven by terrain roughness. Don't spend the afternoon on it.

**Where the bounds fail.** The Map Parameters rect does **not** reliably contain the
navmesh: 289 maps inside, 60 outside, worst 2,141 units (row 29026). This is
reported as a failing check. A pipeline that clips authored geometry to the declared
bounds would be imposing a rule retail does not.

---

## 5. Props and models

**Prop geometry is referenced, not embedded.** 8,420 distinct model file ids across
the corpus, 285,670 instances, **6,748 models (80.1%) used by more than one map**,
most-shared in 152 of 349 maps, most-instanced 1,608 placements. 1,672 models are
single-map, so the measurement discriminates. **A custom area can reuse retail props
by file id**, which is the cheapest possible route to a populated scene.

**Chunk `0x20000004`.** Header: `u32 0x39583392`, `u16` version 17, `u32` array size,
`u16` prop count, then count records of `48 + 8N` bytes. The walk consumes exactly
the declared size in **349/349** maps. *(Implementation trap: the size field is
measured from offset 10 and includes the `u16` count, so `consumed = p − 10`.)*
Fixed strides 40/44/48/52/56 all fail to close.

Record layout (MEASURED, and pinned by an offset scan in which orthonormality holds
at **exactly one** byte offset and fails by 60+ orders of magnitude at every
neighbour):

```
+0   u16  filename index  → chunk 0x21000004
+2   f32  x, y, z
+14  f32[3]  vector a   — the vertical axis; (0,0,-1) in 180,393 of 285,670
+26  f32[3]  vector b   — horizontal facing; b[2]==0 in 185,389 of 285,670
+38  f32  scale
+42  f32  radius        — see the cross-file identity below
+46  u8   flags (73 distinct values corpus-wide; meaning unknown)
+47  u8   ring point count
+48  ring_count × Vec2f  — a world-space footprint polygon
```

GuildWarsMapBrowser names +26/+30 `sin_angle`/`cos_angle`; that is **correct for the
~65% of props that are a pure yaw** and lands on `b[0], b[1]`. The remaining ~35%
carry a genuine 3D tilt. Nobody has stated which direction is up, though GWMB negates
the third position float — an authoring tool needs that sign.

**The load-bearing check — a cross-file identity nothing in our decoder can force:**

> `prop.f11 == prop.scale × max(sqrt(x² + y²))` over the vertices of the model file
> the prop references.

MEASURED at 1e-5 on **12,766 of 12,875 props across 14 maps** (the verifier
recomputed it with a vertex stride that does not pass through GWMB's lookup tables
at all). Five rival definitions were tried and all fail; the 3D-radius rival scores
103/12,875. The number spans two files and eight decode steps — prop offsets →
filename index → 6-byte record → id formula → file-id table → MFT row → geometry
chunk → sub-model offset → vertex stride. **It also holds for the 238 reference-map
props whose basis is *not* a pure yaw (55/55 and 183/183), so `f11` is a model-space
quantity, rotation-independent** — an authoring tool must recompute it from the
model, never from a placed bounding box.

**Model files.** `ffna` type 2, MFT flags 515 (a second stream of 21,420 type-2 rows
carries flags 2817). Chunks `0x00000FA0` (geometry), `FA1`/`FA5` (texture filenames,
2,048/2,048 sampled), `FA6` (174), `FAD` (AMAT materials, 479). Geometry: `u32`
num_models at `+0x44`, `u16` collision_count at `+0x4C`, then nine-`u32` sub-model
headers, `u16` triangle-list indices, interleaved vertices, trailing blocks, then
collision meshes. Indices divisible by 3 in 519/519 sub-models and **0 of 519 out of
range**. Thirteen distinct vertex formats observed, strides 20..84.

**Failures, honestly:** ~15% of model files never yield a unique closing sub-model
walk, and *separately* ~0.5% of props whose model *did* close have an `f11` that
disagrees grossly (worst 97%). Those are **disjoint populations** — fixing the
preamble decode will not explain the second.

**A cross-check that came back negative, with a control showing it had power:**
prop placements do **not** correspond to the pathing chunk's static obstacles.
0 of 27 and 0 of 894 obstacles have any prop within 100 units; medians 1,511 and
1,356 units; a uniform-random control inside the obstacle bounding box gives 1,204
and 1,105, so real obstacles are if anything *farther* from props than noise. All
three axis pairings were tested, so this is not a frame artifact. Whatever the
tag-13 obstacles are, they are not scenery.

**NOT FOUND in map files:** spawn points, portals or map links, zone names. Those
come from the server, which is ours — `content/maps.toml` already carries the one
field (`file_id`) a new area needs to be reachable.

**NOT FOUND in prop model files:** bones or skeletons. Expected — props are static.

---

## 6. What the client's loader accepts

All SOURCE-CODE unless marked, read from the vaulted stock `Gw.exe` (19,620 assert
sites, 1 distinct callee, `single-routine=True`; 1,131 sites across 92 files in 14
`Map`/`Model` directories).

**Gates that are real `jne`→fail, not asserts:** the pathing chunk requires
signature `== 0xEEFE704C` **and** version `== 12` exactly; terrain requires
`0x87821134` / 17. Every chunk kind has a magic that appears as an immediate
somewhere in `.text`, and corpus-wide each kind shows exactly one magic and one
version at its full *n* (MEASURED).

**Structural acceptance, per chunk, in the loader's own loop:** `ptr->id < 23` and
`s_chunkInfo[id].load != NULL` (MapData:4415/4417). Plus
`mapType != MAP_TYPE_EDIT || mapStage == MAP_STAGE_RAW` (MapData:4557).

**Sub-record framing is stage-dependent, from the client's own reader *and*
writer.** Raw and Bloated: `u8 tag` + `u32 size` (5 bytes). **Stripped: `u8 tag`
alone, no size field.** `tag < 256` on both paths. Reader at `0x0073e410`, writer at
`0x0073e580` — two functions compiled from different lines, agreeing.

**Confirmed on real bytes:** the Stripped Path chunk is `19 + 8n` bytes in
**349/349**, tags `(7, 14, 255)` in 349/349, tag 8 (planes) in **0** of 349. That
size law is refutable by construction — a `u32` size field after the tag would add
4n bytes and break it on every map.

**No checksum over decompressed content.** Searched all 19,620 assert expressions
for crc/checksum/hash/digest: the only hits are the archive layer's own CRC-32 over
stored bytes and a model geoset cache key. The map-file gates are magic-equality and
version-equality only. This is a **bounded negative** — a digest computed with no
assert and no log string would not have been seen.

**Failure behaviour.** `MapLoad` (`0x00707bb0`) calls the loader; on failure it logs
`Creating default map` and synthesises an empty map rather than crashing. Only if
*that* fails does it assert. The `Map.cpp(1762) assert(found)` that `FORMAT.md`
records is a **terrain-altitude query on the empty default map**, not a loader
validation — the containing function returns a float and its only preceding call is
`TrnQueryAlt`. Each of the three relevant wide log strings has exactly one xref in
`.text`, so there is no ambiguity about which path emits them.

**The client builds at load, and writes the result back.** Nine of the 23 chunk
kinds carry a bloat handler at **`s_chunkInfo+0x18`**: Terrain, Zones, Props, Path,
Locations, Map Parameters, Collision, Sight, PathEngine. Each gates on
`stage != 2 → return` and then on map type; **for a type-0 client map none of the
gates fires.** The driver at `0x00707330` runs the stage converter to target stage 2,
re-opens the file for *writing*, and writes the converted buffer back
(`Map '%s' could not be opened for writing` is the failure branch).

**The strongest corroboration in the whole pass, and neither surveyor ran it:**
comparing Stripped and Bloated bytes per chunk kind across the corpus, **all eleven
Data kinds without a bloat handler have a size ratio of exactly 1.0000, and six of
the nine with one shrink** (Path 0.0003, Sight 0.0001, Props 0.1416, Zones 0.3899,
Terrain 0.4673, Locations 0.6923). The binary's compiled-in table predicts the
archive's byte counts, 20 kinds for 20.

*The offset above was wrong in the first version of this document and is corrected
here. It read `+0x14`, which is **null in all 23 rows**; the bloat pointer is at
`+0x18`. MEASURED 2026-08-10 by re-dumping the table (`s_chunkInfo` @ `0x00A6CF78`,
23 × 40 B, full record: `+0x00 fn, +0x04 fn, +0x08 LOAD, +0x0C 0, +0x10 fn on row 0
only, +0x14 0, +0x18 BLOAT, +0x1C 0, +0x20 f32 cost, +0x24 UTF-16 name`). **The list
of nine is unaffected and exactly right** — the nine rows with a non-null `+0x18` are
precisely Terrain, Zones, Props, Path, Locations, Map Parameters, Collision, Sight and
PathEngine, and the four NULL-load rows are precisely 0x01, 0x05, 0x0B, 0x0D. So the
"20 kinds for 20" corroboration stands on a correct list read from a mis-stated
offset — the measurement was right and the citation was not, which is worth recording
because the citation is what a later reader would have used.*

**The map compiler is in the shipping binary.** `PathBuild.cpp` has 28 asserts
naming `SINK_NODE`/`X_NODE`, `above[0..1]`/`below[0..1]` link symmetry, a stack, a
deleteQueue, a nodeList, `def->trapezoidCount < 1024`, and
`trapezoidList[SIDE_LEFT]/[SIDE_RIGHT]`. `PathFlood.cpp` adds an edge table and
`pointCount % 2 == 0`. That is the classical randomized trapezoidal decomposition
plus a point-location DAG, over line segments.

**But `PathDataImport.cpp` bounds-checks everything stored**: index <
`trapezoidCount` (four call sites, MEASURED clean 2,094,666/2,094,666), sink/y/x
node counts, `*rootType == X_NODE`, `!pairRef->portal->pair` (pairing resolved at
import), and `Endian(hdr->sequence) != PATH_SEQUENCE_FAST_SAVE` — which implies a
second path serialisation exists. **Both the builder and the importer are in the
same binary.** Which one runs for a client map is the pivotal unknown.

**Corpus checks against the client's own asserts** (MEASURED, 349 maps, 11,795
planes, 1,032,259 trapezoids): coordinate bound 1,032,259/1,032,259; `right.x >=
left.x` 1,032,259/1,032,259; neighbour index in range 2,094,666/2,094,666;
neighbour *symmetry* 2,094,666/2,094,666; portal index in range 166,596/166,596;
per-plane portal count < 65535 11,795/11,795; the tag walk and plane walk each
consume the chunk to the exact byte 349/349.

**One assert is REFUTED as a constraint on shipped data:** `trapezoidCount < 1024`
fails on 259 of 11,795 planes, max 7,664. **All 259 are plane index 0** — exactly
one per map — and plane 0 is the largest plane in 348/349 maps, holding a median
89% of a map's trapezoids. The rule is *"the ground plane is unbounded, every other
plane stays under 1024"*, which is actionable; "259 violations" is not.

---

## 7. Two cross-file identities a writer must reproduce

Both MEASURED at 349/349, both spanning a map's two independently compressed streams:

1. The **tag-14 `u32`** in the Path chunk is byte-identical between Stripped and
   Bloated. (This extends `FORMAT.md`'s "18 of 18" to 349 of 349 and corrects it —
   the identity is the `u32`, not the whole 5-byte record. The trailing flag byte is
   `0x00` in every Stripped file and `0x01` in 318 of 349 Bloated files.)
2. The **`u32` at Bloated Path payload +8 equals the `u32` at Stripped Path +5** in
   349/349. This was filed as an open question by the surveyor who had already
   written the identical test one record later.

Additionally the Map Parameters chunk's trailing four `u32` are **349-distinct** —
one value per map, byte-identical between a map's two stages. A 16-byte content id
is the obvious reading and it is **untested**. Reading the load handler at
`0x007129F0` would settle whether the client ever compares it.

---

## 8. The write path, arithmetically

**Size is not the blocker, and the obvious reading of the constraint is inverted.**
`datwrite.py --replace` refuses only when `len(new) > ceil(size/512)*512`, so a
*shrinking* payload's budget is the row's **entire block reservation**, not its
0–508 bytes of padding.

| Quantity | Value (MEASURED) |
|---|---|
| Map rows (flags 259) | 349, all compression 8 |
| Reservation: min / p10 / median / p90 / max | 1,024 / 217,088 / 961,536 / 1,466,368 / 2,094,080 B |
| Total reservation across map rows | 303,006,720 B |
| Block-padding slack | 0–508 B (median 228; 5 rows at zero) |
| Rows whose reservation could hold the smallest complete map | **348 of 349** |
| Reservations overlapping the next allocated extent | **0 of 177,341** |
| Extents misaligned from 512, or past EOF | 0, 0 |
| Free space | 32,528,384 B in 214 whole-block runs; 12 runs ≥64 KB; largest 14,718,976 B |
| Claimable erased MFT rows | **0** (all 12 size-0 rows are the reserved 4–15) |
| MFT spare inside its own reservation | 48 B = 2 rows |
| File-id table spare | 376 B = 47 pairs |

**Round-tripping a retail map is out.** Decompressed/stored ratios run 1.87–10.80
(mean 2.58) over 29 maps and **0 of 29** fit their own reservation. "Decompress a
retail map, edit it, write it back" does not work; only a genuinely small authored
map fits.

**No map has ever shipped stored** — 0 of 38,621 stored rows begins with an `ffna`
type-3 payload (MEASURED). Stored is nonetheless the right bet, and the argument is
a module boundary rather than a precedent: compression lives in
`Base/Rtl/Exe/ExeArchive.cpp` and `Base/Compress/*`, and **0 of MapData.cpp's 118
asserts mentions compression, extraBytes, inflate, huff, deflate or stored**
(SOURCE-CODE). `studies/datwrite/FINDINGS.md` §10 already observed the client render
a compression-0 ATEX row.

**Three checksums, all reproduce, and `datwrite.py` maintains all three:** the file
header's CRC-32 over bytes `0x00..0x0C` only (7 controls at other lengths all
differ); MFT row 3's self-CRC over `mft[0:0x48]` continued over `mft[0x60:]` (two
controls differ); and each entry's CRC over its **stored** bytes (47/47 real rows
sampled).

**Three hazards, all cheap to remove — and all removed, 2026-08-10, `6f07fff` on
`main`, along with a fourth this pass never saw.** The section below is left standing
as written because the diagnosis is what mattered; what follows each item is what
actually landed. **A fourth defect was found by the new test**, and it is the worst of
the four: `fix_mft_self_crc()` read the MFT through `Archive`'s buffered **read-only**
handle, opened before any of our writes, so a seek back inside its 8 KB window was
answered from a pre-write copy. It compared the old CRC to the old bytes, printed
`MFT self-crc already correct`, and **left the archive failing its own self-checksum**
— intermittently, depending on where the buffer window fell. All four share one shape:
*the tool reports success for work it did not do, and not one of them can fail a
checksum.* That is the exact failure class this document's §16 was written about, found
in our own writer rather than in a format reading.

1. **`datwrite.py` has a live bug.** `main()` computes
   `mutating = (args.corrupt_crc or args.overwrite or args.corrupt_mft_crc)` —
   **`args.replace` is missing.** `--verify --replace ROW --data f` prints
   `[PASS] all rules hold`, returns without ever calling `replace()`, and exits 0.
   The one operation this entire pipeline depends on silently does nothing when
   combined with the verify flag that the recommended procedure leads with.
2. **A shrinking replace journals only what it writes.** `Writer.put()` reads
   exactly `len(data)` as its `before` record, so replacing a 1.96 MB row with 20 KB
   captures 20 KB. The client's free list is rederived from the entry table at every
   open (MEASURED, `studies/datwrite/FINDINGS.md`) and the client is OBSERVED
   relocating live rows during play — so if it takes the freed blocks, `--revert`
   restores the first 20 KB, reports success, leaves all three CRC rules verifying,
   and the retail map is gone. INFERRED, untested. One line fixes it: dump
   `Archive.raw(entry)` before the first write.
3. **A shrinking replace leaves the original payload's tail** sitting inside the
   row's own reservation, immediately after the authored bytes. Whether the reader
   trusts the size field or scans past it is untested. Zero-fill the tail.

**Fixed, `6f07fff`.** Hazard 1: the tuple is now `MUTATING_DESTS`, named once, and the
test checks it against the parser's own actions so the next flag added cannot drift out
of it — and `is_mutating()` compares identity rather than truthiness, because **row 0
was the same bug waiting on a different input**. Hazards 2 and 3 turned out to be one
fix: `replace()` now writes the **whole block reservation as a single journalled put** —
payload followed by zeros — which is also the only form in which the journal's `after`
field can be told the truth, so `--revert`'s "the client wrote here" detector covers the
reservation instead of its first few kilobytes.

**`datwrite.py` now has a test**, `toolkit/mapdata/test_datwrite.py`, named in
`CLAUDE.md`'s suite in the same commit. It builds its own 4 KB archive in a temp
directory — never `Gw.dat`, never `C:\gw`, and **section 0 is that refusal**. Its
fixture restates the two self-referential checksum rules longhand from `test_datcrc.py`
rather than importing `datwrite`'s own, so section 1 is not the subject agreeing with
itself. Floor 31 from a green run; every headline check was confirmed red against the
pre-fix tool. This closes what was the sharpest single risk in this document: the only
tool in the project that opens the 4.2 GB archive `r+b` had no test at all.

**Relocation is not needed for a first experiment** and is not implemented. Ninety-eight
of the 349 map rows are named by nobody — but that is a **single-witness** result
from one unlicensed mirror's table, so "unclaimed" means *unnamed by the one source
we checked*, not *unused by retail*. Recommended target: row 136294, file ids
`0x4759B` / `0x5D030`, reservation 1,960,960 B, partner row 136295 at 843,264 B.
Twenty-seven unclaimed rows have ≥1 MiB.

**The reference implementation already exists in the archive.** MFT row 46196:
784 B stored / 8,471 decompressed, 18 chunks, 32×32 grid (the minimum), extent
exactly 3072×3072, **all 1,024 heights identical at −13.0**, one distinct tile byte,
4 terrain textures, no prop-filenames chunk, a 51-byte empty prop chunk, and a
**419-byte navmesh: 1 plane, 2 trapezoids, 0 portals**. Its own reservation is only
1,024 B so it cannot host itself uncompressed, but it is the template.

*(It is not quite the "flat box" it reads as: trapezoid 0 has `xTopLeft` 480.0
against `xBottomLeft` 0.0 — a diagonal corner cut. A true axis-aligned rectangle
would be one trapezoid; this needs two precisely because it isn't one.)*

---

## 9. The ladder

Ordered, dependency-aware. Acceptance criteria in `PLAN.md` §3 style — each is a
thing that can come back red.

**Every launch rung inherits the house rules and they are written into the rungs, not
left to prose.** Any rung that writes bytes operates on **a copy of the archive in a
run directory — never `vault/dat_study/Gw.dat`, never `C:\gw`**. Any rung that starts a
client goes through `cage.assert_launch_safe(exe, host)` with the ours-DH build bound
to loopback, and names its account per `toolkit/harness/accounts.py`. Any rung that
ships code adds its test to `CLAUDE.md`'s suite list **in the same commit**.

| # | Rung | Acceptance criterion | Cost | Needs |
|---|---|---|---|---|
| **A-1** | Land the `PLAN.md` §6.1 derivation-register row for the **terrain layout** (GWMB, custom licence, credit required) and add the two missing **GWCA** rows | The row exists before any code uses the layout — `CLAUDE.md` requires it *first*, and the existing `gwdat.py`/`pathmap.py` rows do not cover terrain | **cheap** | — |
| **A0** | Cache a per-map chunk index in the vault (row → `{chunk_id: (offset, size)}` + first 64 B of each chunk) — **in `vault/` only, never the repo, and no test fixture derived from it** | A full-corpus chunk query runs in under 5 s where it now takes 13–18 min | **cheap** | — |
| **C0** | ✅ **Landed 2026-08-10 — §17.** Disassembled the load handlers for Map Parameters, Terrain, Path and PathEngine, plus the dispatcher, the bloat driver and both its callers | Met. Read sets and reject sets enumerated per handler; the 16-byte field identified as a UUIDv4 the loader never compares; `sequence` read, compared and discarded; **bloat does not run on a normal load**. Three rungs deleted as a result | **cheap, offline** | — |
| **A1** | `toolkit/mapdata/mapchunks.py` — the 23-slot name table, the stage/type decomposition, the Dependencies decoder, the two stage framings | `test_mapchunks.py` asserts 349 pairs, 698 tiled, 134,290/134,290 refs, terrain size laws 349/349, floor set from a real green run; line added to `CLAUDE.md`'s suite in the same commit | **cheap** | A0 |
| **A2** | ✅ **Landed 2026-08-10, `6f07fff`.** Fixed `datwrite.py`'s `--verify`/`--replace` no-op; wrote `test_datwrite.py` on a synthetic archive | Met, and it found a **fourth** defect nobody had diagnosed: `fix_mft_self_crc()` read through a stale buffered handle and could leave the archive failing its own self-checksum while reporting it correct | **cheap** | — |
| **A3** | ✅ **Landed 2026-08-10, `6f07fff`** — folded into A2. `replace()` writes the whole block reservation as one journalled put, payload followed by zeros | Met. Both the tail-zeroing and the whole-reservation journal fell out of one change, and `--revert`'s "the client wrote here" detector now covers the reservation | **cheap** | A2 |
| **B1** | `toolkit/mapdata/terrain.py`: decode a Bloated terrain chunk to `(map.toml, height.f32, tiles.u8, tag3.bin, tag9.bin, tag4/5, tag7 opaque)` and re-encode | **A retail terrain chunk round-trips byte-identically on 349 of 349 maps.** Anything less names the wrong layout | **cheap→moderate** | A1 |
| **B2** | Whole-file round-trip: decode and re-encode an entire Bloated map payload | 349/349 byte-identical, both stages | **cheap** | B1 |
| **B3** | Blender importer (`tools/blender/`, outside `toolkit/` — `bpy` is not stdlib) | A retail map's terrain appears in Blender at 96 units/cell with the right orientation, **and GWMB's export of the same map agrees after a transform declared in writing before the comparison runs** (it negates height and flips row order; it emits `(dims+1)²` vertices to our `dims²` samples). An undeclared transform makes this rung meaningless in both directions | **cheap** | B1, and §16-P6 resolved |
| ~~**C1**~~ | ❌ **DELETED 2026-08-10 — answered statically by C0 (§17.2).** Normal load requests stream **1**, the re-bloat read requests **0**, the write-back targets **1**. Traced through five frames and re-derived from the other end by the verifier, then paired with the archive's `(flags 3, stream 1)` / `(1, 0)` structure at 349/349 | — no launch was needed | — | — |
| **C2** | **The zero-authored-bytes delivery test.** Row 46196's payload, written stored over a candidate row, three arms (matched partner / stale partner / one size field off by four). **Pre-flight:** the first two items are now **satisfied by the tool itself** as of `6f07fff` — `replace()` journals the whole reservation and zeroes the freed tail, so §8 hazards 2 and 3 no longer need handling at the experiment level. Still mandatory: set `spawn_x`/`spawn_y` inside the copied map's own rect (≈1536, 1536 — its extent is 0..3072 on both axes, and every existing `maps.toml` spawn is thousands of units away); verify offline that the spawn lands in **exactly one** trapezoid of the authored mesh, the same test every other `maps.toml` row carries; diff the target row's MFT entry (offset/size/compression/crc) **before and after every arm** | Arm 1 loads and we stand on a flat square; arm 3 **must** fail with `Attempting to re-bloat`. Arm 2 vs 1 tells us whether a map is one payload or two. **"Loaded, but the MFT row changed" is a first-class outcome, not a pass** — arm 3's expected failure runs the re-bloat path, which re-opens `Gw.dat` for writing, so a successful re-bloat there rebuilds the *original retail map* into the row and "arm 2 loaded" would otherwise read as "a stale partner is fine" | **research, 1 launch** | A2, A3, C0, C1 |
| ~~**C3**~~ | ❌ **DELETED 2026-08-10 — answered by C0 (§17.1): only after failure.** Its test premise was also impossible as written: there is no such thing as a "Stripped-only map", because a file id can only resolve to a `FIRST_STREAM` row and all 349 of those are stream 1 | — | — | — |
| **D1** | Hand-author a Bloated map from our own builder — 32×32, flat, 2-trapezoid navmesh, everything else copied from the owner's archive at runtime | Our builder's output is **byte-identical to row 46196's payload**, **and the run reports which chunks it generated versus which it carried, with a floor on generated bytes.** Byte-identity alone can go green on a program that copies 8,471 bytes — §14 forbids the 232 bytes of ArenaNet constants from entering the repo, so a copying builder is the *expected* shape and the criterion must measure the part that isn't copying | **moderate** | B2, C2 |
| **D2** | Change one number: raise a 4×4 block of heights by 500 units | The bump is visible in game and the client's collision agrees with our server's — walk onto it and the server's `on_mesh` stays true | **cheap** | D1 |
| ~~**E1**~~ | ❌ **DELETED as a paired launch, 2026-08-10 — answered by C0 (§17.2): on a normal load the client IMPORTS.** `PathDataImport` is the only Path module reachable from the load closure, the importer hardcodes stage 2 (`push 2` at `0x00725124`), and its bounds checks are per-record asserts rather than a builder. §16-P4's carefully-repaired arm is moot. **What E1 was selecting between (E2 vs E3) is now a cost decision, not an experiment** | — and one thing it would *not* have caught: a structurally-valid-but-geometrically-wrong mesh loads **silently** and stops the client on the first query that walks a bad portal, because asserts terminate the process (§17.3) | — | — |
| **E2** | If E1 says *import*: a trapezoidal-decomposition generator over the height lattice with a slope threshold | Our generated navmesh for a retail map's terrain reproduces ≥90% of that map's own walkable area, and `pathmap.py` reads back what we wrote | **research, weeks** | E1 |
| **E3** | **Provoke the client's own compiler** (specified by C0, §17.2): publish a stream-0 Stripped payload holding the boundary polygon, make the *same file id*'s stream-1 payload fail — cheapest trigger is **zero length** — and the client logs, compiles stage 1 → 2, writes into stream 1, and retries once. Input contract known exactly: `u32 0xEEFE704C`, `u8 12`, `u32 sequence`, then unsized `{7: u16 n, n × Vec2f}`, `{14: u32, u8}`, `{255}` — **19 + 8n bytes, 349/349** | A Stripped-authored area is walkable and its navmesh, read back after the client's write-back, is one we did not author. **Must run on an archive copy** — but ~~the write-back grows the payload ~2× and `ExeFile:252/253`'s bounds are asserts whose store executes unconditionally on both branches~~ **that reason is REFUTED (§18.11): those asserts bound a heap buffer, not an archive row, and are unreachable.** The real reasons are the client's MFT-derived coalescing free map, the open-time reconcile that *deletes* undirectoried rows, and the relocation that staleness every offset we recorded. **Pre-flight and post-flight per §18.11** | **cheap, but writes to the archive** | D1; §17.7's reservation question **settled 2026-08-10, §18** |
| **F1** | Props by reuse: place retail models by file id, correct `f11` recomputed from the model | A named retail prop appears at the authored position, orientation and scale, and its `f11` matches the cross-file identity | **moderate** | D2, Props record decode |
| **F2** | Terrain textures: point `0x21000002` at borrowed ATTX file ids | The authored terrain renders with a chosen retail texture set rather than a default | **cheap** | D2 |
| **G** | **A Blender-authored area, hot-reloaded, walked.** `map.toml` in `content/`, geometry from Blender, served by our own server | Someone models a shape in Blender, runs one command, and walks around it in the retail client | **the whole ladder** | all of the above |

Rungs A-1–A3, B1–B3 **and C0** are entirely offline and touch no client. **C0 comes
first** — it is an afternoon, it needs no launch, and it can collapse C1, C3 and the
largest term in §10's estimate before any byte is written. C1 and C2 remain the
behavioural pivot for everything from D onward.

---

## 10. Cost, plainly

- **Export half (A0–A3, B1–B3): a weekend.** Everything it needs is measured. The
  terrain round-trip is the only piece with any risk, and its failure mode is
  informative rather than blocking.
- **Delivery half (C1–C2): two caged sessions.** Zero authored bytes. This is the
  highest information-per-hour work in the whole plan and it should be done next.
- **Minimum viable custom area (D1–D2): one to two weeks** after C2, most of it in
  the Bloated Props/Zones record layouts if a map must carry them non-trivially —
  and it may not, since row 46196 ships with an empty prop chunk and no
  prop-filenames chunk at all.
- **Navmesh (E): a week if the client rebuilds, a month if it imports.** This is the
  single largest variance in the estimate, and E1 collapses it for the price of one
  paired experiment.

  **Resolved 2026-08-10 (§17.2), and not in the comfortable direction: it imports.**
  The honest restatement is that the variance narrowed at *both* ends rather than
  collapsing. The month-branch is now the default **and it is specified rather than
  speculative** — C0 handed over the complete Path read set including the
  point-location DAG's tagged child-reference encoding, which nobody had and which
  10,829,572 corpus references confirm. The week-branch survives as E3: a named,
  offline-preparable experiment that provokes the client's own compiler. Saying the
  estimate collapsed to a week would be the comfortable lie.
- **A polished pipeline (F–G): a month beyond that**, mostly in props, textures and
  the Blender-side ergonomics.

**So: do C0 first, then C1 and C2, and only then the exporter.** C0 is an afternoon
against a vaulted binary with nothing launched, and it bears directly on the largest
single line item in this estimate — if the second caller of the bloat driver shows the
client compiling a map on a normal load, the navmesh term collapses from a month to a
week before any experiment runs. C1 and C2 are still cheaper than the export work and
still cannot be done later without redoing decisions.

**The estimate assumes a custom area is a durable artifact, and nobody checked.**
Every SOURCE-CODE claim here — `s_chunkInfo` @ `0xA6CF78`, the four map-type
manifests, `version == 12` / `== 17`, the nine bloat handlers — comes from build 38797
alone, while `vault/client/2026-04-30_b174de1f2d8d` is a second stock build the suite
already exercises on both. If the accepted chunk versions move between builds, §10
needs a maintenance line and a custom area is per-build rather than permanent. One
command answers it (§16-P10).

---

## 11. Corrections ledger

Recorded rather than overwritten, per house style.

### A. Refuted by the verifiers

**A1 — A fabricated corroboration.** Track 1 claimed the `s_chunkInfo` cost floats
summing to exactly 1.0 was confirmed by the client's own `MsProgress.h:86` assert
`cost <= 1.0f`. It is not. The asserted `cost` is `1.0f / chunkCount`, computed 90
bytes earlier at `0x007142B4`, and **cannot fail for N ≥ 1** — a check that cannot
fail, presented as the thing that makes the table trustworthy. The floats do sum to
1.0 in f32, which is a weak-but-real check on the +32 offset. A **real** check at the
same site was missed and is now in §3: the loop asserts `id < 23` *and*
`load != NULL` for every chunk.

**A2 — A reproduction step that cannot reproduce.** `scratchpad/chunkinfo.py` decodes
UTF-16 names as ASCII and prints one letter per row. The values in the report are
right; the named script did not produce them.

**A3 — A phantom exception class, from a dropped record.** Track 2's three corpus
scripts collapsed the tag stream with `{tag: (b, sz) for ...}`. Twenty-four maps
carry two tag-3 records, so the second overwrote the first. This produced a false
`ok_t3 325/349`, a false "identical tag set in all 349", a false cross-chunk
correlation, and an entire blocker. **Correct:** tag 3 is `dx*dy/4` in **349/349**;
24 maps carry an *extra* 17-byte tag-3 record. The tag *walk* was never wrong — it
consumed the chunk exactly, extra record and all. Only the summary lost data, which
is why the error survived a check that looked airtight.

**A4 — "10 unresolved texture references" was an artifact.** Track 3 reported 10 of
Kamadan's `0x00000FA5` entries failing to resolve. All 430 resolve; ten are DDS.
The smaller denominator came from the script skipping any model whose *geometry*
walk had failed, silently conditioning the texture census on the geometry parse.

**A5 — Two failure populations conflated.** Track 3's blocker said the 93 `f11`
identity failures were the non-closing model files "seen from the other side". They
cannot be: `f11` is only computed on models that closed. ~15% never close; a
separate ~0.5% close cleanly and are grossly wrong. Fixing the preamble decode
addresses the first and will not explain the second.

**A6 — A refutability argument that refutes nothing.** Track 4 argued the BSP bias
constants `0x80000000`/`0x40000000` were "the only pair for which the compiler could
skip the subtraction" at strides 12 and 24. Any multiple of 2³⁰ cancels at both.
The encoding is nonetheless real — the verifier supplied a per-column classification
of the file's own node blocks that separates float columns from biased index
columns, and it holds.

### B. Weakened

**B1 — "349/349 byte-identical across stages"** flattens present-in counts of
117–347 into 349/349 for 9 of the 20 identical kinds. And *Locations* belongs on the
"transformed" list only on a technicality (a four-byte pad), while *Sight* is
**generated**, not rewritten — its Stripped form is a 9-byte stub. Substantively:
four transformed, one generated, one padded.

**B2 — "Stripped Terrain is smaller than the heightmap it expands to"** was
demonstrated on Kamadan and asserted for the corpus. It holds on **278 of 349**
maps. The conclusion (a bit-packed codec, named by `TrnCodecHeight.cpp`) is probably
right; this particular argument supports it on 80% of the corpus.

**B3 — "Prop z equals terrain height"** is an overstatement. Corpus-wide median
`|dz|` is 97.4 units and ~50% of props land within 100. It is decisive against every
control tested (8,000–12,500 units off), which is all it was used for — but it is an
agreement, not an equality.

**B4 — "Closed ring, 1,782 of 1,782"** was a 4% sample generalised. Corpus-wide,
**37,505 of 37,548 (99.885%) are closed; 43 are open polylines** across 22 maps. An
exporter must not assume closure.

**B5 — "Never more than one offset qualifies" for the sub-model walk** is false;
~0.05% of model files are ambiguous, including one that closes at two genuinely
different parses. The "nothing was fitted" argument rested on it being zero.

**B6 — The vertex-format accounting was fitted and tested on the same 519
sub-models.** Thirteen formats occur within 14 maps, not nine, and the byte-cost
rule disagrees with GWMB's table once (`dat_fvf 0x2C`). The "no skeleton data"
negative rested on that accounting and needs restating.

**B7 — "Terrain textures are ATTX, 335 of 335"** was 7 maps. Over 39 maps:
**1,878 ATTX, 2 ATEX, 1 DDS of 1,881**. The formula is confirmed (background ATTX
rate in the archive is ~0.5%, and no-offset / swapped variants resolve 0/1,881) —
but an **off-by-one** formula still resolves 1,271 and returns 1,143 ATTX, so
"it resolved to the expected magic" is a weaker check than it looks.

**B8 — "Header word1 == the FFNA type byte" is two constants agreeing.** Both sides
have zero variance across 698 files (and the fields are 13 bytes apart, not 5).
It becomes a real check the moment a type-4 map exists — and by the same survey's
finding, none does.

**B9 — The chunk-table walk is a much narrower integrity check than claimed.** 198
of 200 single-bit flips through row 46196 still walk clean; even restricting flips
to the 144 chunk-header bytes catches only 138 of 300. It proves the decompressor
emitted the right *number* of bytes and that the headers are mutually consistent.
It says nothing about 98% of the file.

**B10 — The `alloc.stream` evidence.** The measurement is good — the flags high byte
is distinct within **all 21,770** multi-entry chains, against controls
(`crc&0xFF`, `offset&0xFF`, `size&0xFF`) that collide in 56–618 of them. But the
stated low-byte control was designed to fail, and the "independent corroboration"
from `Gw.log` is **vacuous**: row 174325 is a lone single-stream file whose stream
could only ever have been 0. The claim "the client could equally have said
`stream 0x1`" is false. Drop the log line from the argument; keep the measurement.

**B11 — "The navmesh independent witness count is ONE."** `gw-preservation/server`'s
`pathing/import.go` is a complete, tested, fuzzed pathing-chunk parser citing
**nobody** — the same "unattributed, unknown independence" status the same survey
granted that repo's decompressor, applied inconsistently. GWCA (MIT, and itself a
fork pair) carries runtime `PathingTrapezoid`/`PathingMap` structs. Neither GWCA
repo appears in the licence table, and they are the two MIT-licensed navmesh
artifacts in the whole mirror set.

**B12 — Numeric slips worth carrying:** stored/decompressed ratios are 1.87–10.80
over 29 maps, not 1.96–3.36 over 10; the navmesh overhang maximum is 2,141 units,
not ~700; grid dims max out at 768×384 by area (no 768×1024 map exists); the
Bloated Path chunk range is 419–950,208 B; `m_bitOffset % 8 == 4` is
`TrnChunk:490`, not `TrnBitStore`; four bit-31 file ids land on map rows, not two;
`--modules` prints 855 basenames from 865 distinct path strings, not 856; the
`Map`/`Model` tree is 92 files in 14 directories, not 93 in 13; every Bloated map
row carries exactly **2** file ids (the `{4: 2}` outlier is our own
`archive.py:file_id_table()` registering bit-31 ids under both raw and masked
forms — our helper double-counting, not a property of the archive).

**B13 — Provenance of the assert evidence.** Track 1's reproduce block claims the
asserts were read from the vaulted build; `asserts.py` has `DEFAULT_EXE =
r"C:\gw\Gw.exe"` and no `--exe` was passed, so they came from the owner's install.
Read-only, so no rule was broken — but the stated provenance was wrong, and the
tool's own output header said so.

### C. Found during synthesis, missed by both surveyor and verifier

**C1 — Track 4's "strongest cross-chunk check" is a one-byte-shifted read of tag 0.**
It claimed the Terrain chunk's `u32` at `+0x0C` equals `256 × dimX` and at `+0x10`
equals `256 × dimY` (349/349), with `+0x08` a constant 6656 and `+0x14` the float
`−2.0` in 348/349 — and its verifier called this "the strongest claim in the
survey", answerable only by a genuine cross-chunk prediction.

It is arithmetic. The Terrain payload is `+0 sig, +4 version, +8 tag byte, +9 u32
size=26, +13 u32 dimX, +17 u32 dimY, +21 f32 cellSize`. Reading a `u32` at +8 picks
up the tag byte plus the size: `26 << 8 = 6656`. At +12 it picks up the size's high
byte plus dimX's low three: `256 × dimX`. At +16, likewise `256 × dimY`. At +20 it
picks up dimY's high byte plus the low three bytes of the `cellSize` float:
`0x00 00 00 C0` = **−2.0f** for 24576.0, and `0x58000000` = 5.63e14 for 55296.0 —
which is exactly why the "outlier" is row 33086, the `cellSize` outlier.

**MEASURED on this machine**, rows 22371, 7982, 46196 and 33086, all four predicted
values landing exactly (`scratchpad/syn_offset.py`). Track 4's finding is Track 2's
tag-0 fields read one byte early. Its 349/349 is real and means nothing new, and it
dissolves two of its own open questions ("what is the constant 6656?", "which map is
the −2.0 outlier?"). Neither the surveyor nor the verifier noticed, because the
numbers were beautiful and the prediction did hold.

**C2 — The Stripped/Bloated size comparison inverts a headline recommendation.**
Track 5's blocker 1 concluded "authoring Bloated is strictly cheaper and is the
recommended route". Per chunk kind across 349 maps, Path is 156,494,153 B Bloated
against **48,671 B Stripped** and Sight 29,859,532 against **3,141 B**. For the
navmesh, authoring Stripped is roughly three thousand times less work. Nobody had
measured the two streams against each other.

The correct synthesis is **per chunk, not per stream**: Bloated Terrain is *raw
float32* and Stripped Terrain is bit-packed, so Bloated is cheaper there; Bloated
Path is a full trapezoid mesh and Stripped Path is a boundary polygon, so Stripped is
drastically cheaper there. **You cannot mix — a file is one stage.** For a small
hand-authored area the Bloated route wins anyway, because row 46196's whole navmesh
is 419 bytes and 2 trapezoids. The Stripped route only pays off once the terrain is
complex enough that its navmesh must be derived.

**C3 — Facts left in hand.** Several results were one line away from data already
collected and were filed as open questions instead: tag 3 == `dx*dy/4` and tag 9 ==
`dx*dy` corpus-wide; `tag4size == tag5size` in 349/349; tag 4/5 are `u8 count + n
bytes` and the count equals the terrain-texture reference count in 36 of 39 maps
(a cross-chunk relation); the 24 double-tag-3 maps' extra record is 17 bytes in all
24; the 17 mandatory chunks appear in a single relative order in 349/349 (filed as
"inferred from 6, cheap to settle" by a pass that ran the corpus three times); every
map payload is `ffna` type 3 in 349/349 and 349/349, which is the assumption
everything else sits on; PathEngine is row 26209 and the terrain `+0x14` outlier is
row 33086.

### D. Corrections this document owes upstream files

- `studies/mapdata/FORMAT.md`: OpenTyria's pathing parser and GuildWarsMapBrowser's
  pathing pattern are **one witness** — GWMB's README credits ldufr, the author of
  OpenTyria, for the pathing map. FORMAT.md lists them as separate sources.
- `FORMAT.md`: "100 map rows are named by nobody" should read **98** (the gap was
  the two bit-31 Pre-Searing ids its lookup could not resolve at the time), and
  "25 bit-31 ids, two of which land on map rows" should read **four**.
- `FORMAT.md`: "stage 2 is the larger, apparently final form" — the vocabulary
  should be ArenaNet's own, **Stripped** and **Bloated**, and the addressable row is
  the Bloated one.
- `FORMAT.md`'s tag-14 identity: "18 of 18" is now **349 of 349**, and the identity
  is the `u32`, not the whole 5-byte record.
- `FORMAT.md`'s open question "Does the client load stage-1 or stage-2?" is
  **half-answered**: a server can only ever *name* the Bloated row (0 of 349
  Stripped rows carries a file id). What the client reads is still open, and is
  rung C1.
- GuildWarsMapBrowser's `ZoneChunk` signature `0x59220329` / version `0xA0` is wrong
  against the bytes; its adjacent `ZoneChunkStub` gives `0x59220320` / `0x010A`,
  which is **correct** — upstream got the stub right and the full form wrong, and
  the answer was in the mirror all along.
- GuildWarsMapBrowser labels `0x20000011` `EnvironmentExtraChunk`; the signature
  spells `SGHT`, the client's own table names the slot **Sight**, and the client has
  an `Engine\Map\Sight\` module.
- GuildWarsMapBrowser's terrain pattern reads the tags **positionally** as 0..7 —
  and so does its shipping C++ parser. That is not a desync (the framing carries its
  own sizes); what is wrong is the **tag identities and names**: its "tag5" is the
  file's tag 3, its "tag6 Shadow Map" is the file's tag 9, and **tag 6 does not
  exist in any of the 349 maps**.
- "One height per grid *vertex*" is upstream's wording, not a measurement, and it is
  probably backwards: extent `= dims × 96` exactly means `gx*gy` samples span `gx`
  cells. A Blender importer built on the vertex reading will be one cell short in
  each axis.

---

## 12. Open questions

| Question | What would answer it |
|---|---|
| **Which stream does the client render, and does it read both?** | Rung C1: `--corrupt-crc` on a map's Stripped partner and, as positive control, on the Bloated row. The gate at `ExeFile.cpp` logs `File 0x%x stream 0x%x is corrupt` and names the stream — the literal exists at file offset `0x53DB40`. Run both arms; one alone cannot distinguish "not read" from "not checked". |
| **Is the bloat path reachable on a normal load, or only as the re-bloat repair?** | The driver at `0x00707330` has two callers; only one (downstream of the failure log) has been traced. Follow `0x707eeb`. Then rung C3. |
| **Does the client rebuild the navmesh or import it?** | Rung E1's paired arm: one build with a correct navmesh, one structurally valid but geometrically wrong. If you can walk where the stored mesh has no trapezoid, it rebuilt. |
| **Does a custom area need both streams, or one?** | Rung C2 arm 2 — a stale Stripped partner. Behavioural, not static. |
| **Is the four-`u32` field at Map Parameters +25 a content id the loader checks?** | Disassemble the Map Parameters load handler at `0x007129F0`. It is 349-distinct and byte-identical across a map's two stages. |
| **What is the Path `sequence` field?** 224 distinct small ints, identical across stages | `PathDataImport:89` only says `!= PATH_SEQUENCE_FAST_SAVE` (0xFFFFFFFF). Read the handler at `0x007125E0`. |
| **What is `PATH_SEQUENCE_FAST_SAVE`'s serialisation?** A format the client refuses is uninteresting; one it accepts and that is easier to generate would be transformative | Same handler. |
| **What do terrain tags 3, 4, 5, 7 and 9 encode?** | The client names the codecs: `TrnCodecShadow` (run-length), `TrnBitStore` (bit packing), `TrnTexBlendHi/Lo`, `TrnTexLight`, `TrnMap`'s `m_shadowData`. Tag 9 is the shadow/light candidate on size alone. Tag 7's 128-byte tail is exactly a 32×32 one-bit mask. |
| **Why do 24 maps carry a second, 17-byte tag-3 record?** Its last three floats are byte-identical across different maps | Name the 24 rows against `studies/areatable/FINDINGS.md`'s map-id table and see whether they fall into one category (arenas, guild halls, mission variants). Those same 24 are exactly the maps whose `0x21000002` chunk carries one extra entry. |
| **Are the heightmap's samples at cell centres or corners?** | Three conventions scored; Pre-Searing marginally prefers corners, Kamadan prefers nearest-cell. `TrnMap:935` asserts `rect.x1 <= dims.x + 1`, hinting at a `dims+1` vertex grid the file does not store. **NOT FOUND.** |
| **Why does the navmesh overhang the declared bounds on 60 of 349 maps, by up to 2,141 units?** | Either the rect is not the clip boundary, or those maps carry navmesh outside the rendered terrain (instanced sub-areas would explain it). |
| **What is the Zones chunk?** Undecoded in both stages; its Stripped form carries UTF-16 authoring paths its Bloated form does not, so bloat is lossy in the authoring direction | Walk both stages to the exact byte using `ZnMap/ZnDef/ZnZone/ZnZoneBsp/ZnZonePop`'s asserts as the vocabulary. |
| **What is Sight?** 29.9 MB, *generated* by bloat, size correlates with prop count (r=0.860) | Read `StBuild.cpp`'s 17 asserts and `StApi`/`StQuery`'s 6. Per-prop line-of-sight occlusion volumes is the obvious guess. |
| **Why does Water carry 5 bytes while naming 32 textures — the same 32 in every map?** | `MapWater.cpp` has 12 asserts. The fixed global set reframes this: the 32 are not per-map content. |
| **Are Collision (9 B constant) and Locations (13 B constant) server-side-only chunks?** Both have live load handlers, and `MapData:2691` says *"Cannot bloat server collision data"* | Read the two handlers. |
| **What is PathEngine, and why does exactly one map have it?** Row 26209, 69,570 B, tag `mesh` followed by a NUL-separated field-name schema rather than a version and sized records; byte-identical across stages, so bloat does not produce it | A second, incompatible pathing representation. Read the handler at `0x007131E0`. |
| **Which of a map's two file ids does the client accept?** The server sends the smaller (397/397 upstream); both resolve to the same row | Send the larger and watch. |
| **Does the client validate the Dependencies list at load?** | Decides whether a custom map can reference art incrementally. Point one dependency at a nonexistent id and watch. |
| **Are trapezoid neighbour indices validated or merely used?** `PathDir.cpp` asserts on portals but nothing was found asserting on neighbours | If unvalidated, a generated navmesh has more slack than the import asserts suggest. |
| **Does the client re-grid or resample the heightmap?** | Decides whether the raw-float32 interchange is exact or merely convenient. |
| **Does shrinking a row let the client's allocator take the freed tail?** | One session diff after a shrinking write. Decides whether the journal is a sufficient revert mechanism. |
| **What does GWMB's JSON export say about terrain we decoded?** | The cheapest external check available; needs an owner decision to download the prebuilt `.exe` into `vault/`. |

---

## 13. How much to trust these sources

**The true independent witness count, per thing we need:**

| Knowledge | Witnesses | Notes |
|---|---:|---|
| Archive container, MFT, decompression | **1 established lineage + 2 unattributed** | kytulendu/GWDatBrowser → GuildWarsMapBrowser (credited in its own README, naming four file pairs). `gw-preservation/fileserver-utils` (Go) and `Fournux/Tyria-Extractor` (Rust) carry no attribution at all — unknown independence. |
| **FFNA map chunk layout and terrain** | **1 lineage, 2 artifacts** | GuildWarsMapBrowser is the only *project* in the 21-repo mirror set describing the terrain chunk — but **not its only artifact, and this document's draft said otherwise**. Besides the ImHex pattern and `FFNA_MapFile.h`'s struct read (both of which imply the flat row-major layout §4 refutes at 0.089), its **shipping renderer** `SourceFiles/Terrain.cpp::GenerateTerrainMesh` walks `32 × 32` sub-grids filling `grid[dim_z − k][l]` from a linearly incrementing counter — *which is §4's own de-tiling formula plus the row flip*. So §4's tiling and orientation result had an upstream corroborator sitting in the mirror the whole time (same lineage, so still one witness — but the pattern and the renderer disagree with each other, and only the pattern was read). Everything load-bearing in §4 was re-derived from bytes or from ArenaNet's own asserts. |
| **Navmesh** | **1 attributed + 1 unattributed + 1 runtime** | GWMB's README credits **ldufr** for the pathing map — and ldufr wrote OpenTyria, so *OpenTyria and GWMB agreeing is one witness counted twice*. Separately, `gw-preservation/server/pathing/import.go` is a complete parser with tests and a fuzz test citing nobody, and GWCA (MIT, fork pair) carries runtime trapezoid structs. |
| Blender interchange | **1, and one-directional** | GWMB exports Gw.dat → JSON → Blender. Nothing imports. |
| **Whether anyone has written a map** | **0** | No writer in any mirror; GWMB's only writes are `stb_image_write`/TIFF/CSV. The official wiki's mod catalogue is entirely TexMod/uMod texture replacement, which cannot add geometry. Four differently-shaped web searches returned the same read-only tool set. |

**Fork pairs that are one witness, not two:** `Jonathan-Greve/GuildWarsMapBrowser` +
`gwdevhub/GuildWarsMapBrowser`; `GregLando113/GWCA` + `JaborGW/GWCA`. GWToolboxpp's
`GwDat/CREDITS.txt` states its derivation from GWMB and reproduces GWMB's licence in
full; Tyria-Extractor cites GWMB by file path for the file-id formula. So GWMB,
GWToolboxpp, Tyria-Extractor and Py4GW_Reforged_Native are **one witness**, not four.
`GWToolboxpp/Utils/ArenaNetFileParser.h` and
`Py4GW_Reforged_Native/include/GW/textures/arenanet_file_parser.h` both carry map
chunk-id inventories that stop at `0x20000014` — the same lineage, the same gap.

*(The claim that gwdevhub's fork "has no `.hexpat` at all" is false — it carries
`FFNA_ImHexPatterns/ffna_type_3.txt`, and both forks ship `FFNA_MapFile.h/.cpp`. The
one-witness conclusion is unaffected, but the stated reason was wrong, and a wrong
reason invites someone to later count the C++ as a second witness.)*

**A note on a claim `FORMAT.md` makes:** that `fileserver-utils`' decompressor tables
matching GWMB's byte-for-byte is "genuine cross-lineage corroboration" is weaker than
stated. Those tables are the *client's own*, so two independent correct readers
produce identical bytes by construction. The match distinguishes "both read the
client correctly" from nothing.

**ArenaNet's compiled-in asserts are a genuinely separate lineage** and the most
valuable source in this pass — but an assert names an identifier, it does not define
it. Everything sourced that way is labelled SOURCE-CODE, and where it is load-bearing
it was paired with a measurement (`CHUNK_SIZE == 32` read two ways from the binary
*and* measured on 349 maps; `XY_DIST == 96.0` read as a literal double *and* measured
across two chunks on 349 maps; the nine bloat handlers read from a table *and*
confirmed by the archive's own byte counts, 20 kinds for 20).

---

## 14. Licensing

Second gate, separate from provenance. Per `CLAUDE.md`, a derivation register row in
`PLAN.md` §6.1 must land **before** a module takes an algorithm, layout or constant
table from any upstream.

| Repo | Licence | Bearing on this work |
|---|---|---|
| Jonathan-Greve / gwdevhub **GuildWarsMapBrowser** | Custom — permissive but **requires a repo link and visible credit**; **not MIT** | Already registered for `gwdat.py` (xentax) and `pathmap.py` (the pathing pattern). **A new row is needed before the terrain layout is used** — the existing rows do not cover it. |
| gwdevhub **GWToolboxpp** | MIT — **but** its `Utils/GwDat/` is GWMB-derived and carries GWMB's licence | Using that directory inherits GWMB's obligations, not MIT's. |
| **GWCA** (GregLando113, JaborGW) | MIT | **Missing from every prior licence table**, and the only MIT-licensed navmesh artifact in the mirror set. Add before citing. |
| Fournux **Tyria-Extractor** | MIT | Clean; touches no map geometry. Its synthetic-archive fixture generator is the noted starting point for `test_datwrite.py`. |
| ldufr **OpenTyria** | Unlicense (public domain) | No obligation. Same lineage as GWMB's pathing. |
| ldufr **Headquarter** | MIT | Does not read `Gw.dat` at all. |
| apoguita **Py4GW_Reforged_Native** | Apache 2.0 | Embeds the same ATEX decompressor. |
| gwnative, gw_in_browser | GPLv3 | — |
| sgwlpr | AGPLv3 | — |
| GameRevision **GWLP-R** | BSD-style | — |
| **No licence at all** — all rights reserved, verify-only per `CLAUDE.md` | | `gw-preservation/server` (**including `pathing/`, and the map table used for the claimed/unclaimed split**), `gw-preservation/fileserver-utils`, `network-logger`, `network-log-explorer`, `GWLP-R-Utils`, `Py4GW`, `Py4GW_Reforged`, `gw-web-player` |

**Provenance constraint the builder must be designed around.** Five mandatory chunks
are byte-identical ArenaNet constants across all 349 maps — `0x20000000` (8 B),
`0x2000000A` (13 B), `0x2000000E` (9 B), `0x21000006` (197 B), plus `0x20000006`
(5 B, two values). That is **232 bytes of borrowed material per map file**, and they
must **never** enter the repo, not even as hex literals in a builder. The builder
reads them from the owner's own archive at run time and refuses without one, exactly
as `repoint_skill` borrows an existing file id rather than shipping art. Better
long-term: decode them — 8, 5, 13 and 9 bytes are almost certainly
signature + version + zero counts, and `0x20000006` taking two values across 349
maps is a decode candidate, not a constant. `0x21000006` at 197 bytes is the one that
will resist.

---

## 15. Reproduce

All 114 scripts from the six tracks plus this synthesis, and the 31 MB of measurement
output they produced, are preserved at **`vault/research/customarea-2026-08-10/`**.
They were written to a session-temporary scratchpad and would have been swept; the
vault is where they belong, because some of the JSON dumps carry archive bytes and
`vault/` is gitignored and local. **The draft of this section pointed at the temp
directory** — a reproduce section citing a path that deletes itself is not a reproduce
section, and every corpus figure in this document traces back to those files.

During the analysis nothing was written to the repo or the vault; the archive and the
client were opened read-only; no client was patched or launched. Afterwards, two
things were written: this document, and that vault directory.

The one script written for this document:

```
python scratchpad/syn_offset.py
  # rows 22371, 7982, 46196, 33086: proves Track 4's "+0x08 / +0x0C / +0x10 / +0x14"
  # terrain header fields are tag 0's own dims read one byte early.
  #   u32@+8  == 6656 == 26<<8            (tag byte + tag-0 size)
  #   u32@+12 == 256*dimX                 f32@+20 == -2.0  (or 5.63e14 on row 33086)
```

Corpus passes are slow — each decompresses 349 or 698 map payloads and takes
7–20 minutes. **Build the cached chunk index (rung A0) before iterating**; that is
the difference between a check that gets run once and a check that gets run.

Client-side reads must pass `--exe` explicitly:

```
EXE="C:/gd/Rurik/vault/client/2026-07-29_221c13772c7a/Gw.exe"
python toolkit/clientscan/asserts.py --exe "$EXE" --modules
python toolkit/clientscan/asserts.py --exe "$EXE" --file MapData --unique
python toolkit/clientscan/asserts.py --exe "$EXE" --grep XY_DIST
```

`asserts.py`'s default is `C:\gw\Gw.exe`. Omitting `--exe` reads the owner's install
— read-only, so no rule is broken, but the provenance you report will be wrong.

---

## 16. What this pass did not do

A final agent read the draft against the repo's own documents and asked only *what is
missing*. Its findings are recorded here rather than folded away, because the useful
ones are structural: they say where this document is more confident than its evidence.
The four that changed the document's conclusions (P1, P2, P3, P5) are already applied
above in §1, §9, §10 and §13; the rest are open work.

**P1 — a whole modality never run.** Not one chunk `load` handler was disassembled,
though six rows of §12 ask for exactly that and every address was already in hand.
The second caller of the bloat driver at `0x707eeb` — on which §1's central "the
client may compile our map for us" argument depends — was never followed. **Applied:**
this is now rung C0 and it comes first.

**P2 — the delivery test's negative control writes into `Gw.dat`.** Arm 3's *expected*
outcome is `Attempting to re-bloat`, which re-opens the archive for writing. Combined
with §8's hazards 2 and 3 (a shrinking replace journals only `len(new)`, and the
original tail survives), the client may write a bloat of the stale partner over our
bytes, possibly past the reservation — after which `--revert` restores bytes at an
offset the entry no longer uses, reports success, and all three CRC rules still verify.
**Applied**, then **largely closed at the tool level 2026-08-10 (`6f07fff`)**: a
shrinking `replace()` now journals the whole block reservation and zeroes the tail, so
the revert mechanism is sound and the experiment no longer has to compensate for it.
What remains at the experiment level is the before/after MFT diff on every arm and
treating "loaded, but the row changed" as a first-class outcome — because a *relocation*
by the client still moves the row out from under a byte-offset revert, and relocation
remains the one archive operation nobody has exercised.

**P3 — the delivery test had no spawn point.** Row 46196's extent is `0..3072` on both
axes; every spawn in `content/maps.toml` is thousands of units away. The player would
arrive off-mesh, `clip_to_walkable` would refuse to move them, and the recorded result
would be "arm 1 failed". **Applied.**

**P4 — E1 could not have distinguished rebuild from import.** Our own server clips
movement against the same `PathingMap`, so with both reading the deliberately-wrong
mesh the server stops the player before the client's opinion is observable. **Applied:**
E1 now requires the two to disagree on purpose, plus a positive control.

**P5 — the document contradicted upstream's shipping renderer.** §4 attributed the flat
row-major layout to GWMB and refuted it at 0.089. True of its ImHex pattern and struct
reader; **false of `Terrain.cpp::GenerateTerrainMesh`**, which implements §4's own
de-tiling plus the row flip — and negates every height, and builds a `(dims+1)²` vertex
grid. **Applied** in §13 and in B3's criterion, which would otherwise have gone red on a
correct implementation.

**P6 — nobody established the up axis or the height sign, and the document contradicts
itself on cell-versus-vertex.** §2 and §12 record it NOT FOUND; §11-D asserts the vertex
reading is "probably backwards" and draws an importer conclusion from it. For a Blender
importer these three *are* the job. The prop-z-versus-terrain agreement already ran and
agreed on **un-negated** heights — that is the measured convention to state, with GWMB's
negation labelled a renderer convention.

**RESOLVED 2026-08-10 by rung C0 (§17.4, Terrain), and §11-D was the one that had it
right.** Samples are at **cell CORNERS**: the client allocates a
`(dimX/32 + 1) × (dimY/32 + 1)` chunk grid, fills only the real tiles from the file, and
**synthesises the extra column and row by replicating their neighbours** — with a
per-chunk min/max pass over `mov eax, 0x441` = **1089 = 33×33** samples for a 32-cell
chunk, and no half-cell offset anywhere in the world↔grid conversion. So an authoring
tool stores `dims × dims` samples and the client manufactures the `dims+1` lattice; if a
Blender mesh carries a genuine `(dims+1)²` grid, **the far edge is discarded**. And the
load path applies **no transform to heights at all** — tag 1 reaches the buffers through
`memcpy` and nothing else, confirming the un-negated convention. GWMB's negation is
a renderer convention, as P5 said.

**P7 — "unclaimed" is not derivable from anything we may rely on.** The 98/349 split
comes from `gw-preservation`'s table, which has no licence; per `CLAUDE.md` the only
permitted use is verifying a value we derived ourselves, and we cannot derive
"unused by retail" — `FORMAT.md` already measured that the client's own area table never
names a map file, so `studies/areatable`'s complete map-id→name solution cannot be
joined to archive rows. §8 flags this as single-witness and then selects row 136294 on
that basis anyway. The honest statement: there are **0 provably-dead rows in the
archive**, and C2 either accepts that it may overwrite a live retail area in the owner's
own copy — with the full-reservation backup as the recovery mechanism — or it does not
run.

**P8 — a silent cap.** §3's Dependencies payload-type column is ~32–40 sampled rows per
kind, printed beside a corpus-wide 134,290/134,290 resolution figure, and §2 promoted it
to "typed". This pass already contains that exact extrapolation failing once (§11-B7:
ATTX 335/335 on 7 maps became 1,878 ATTX / 2 ATEX / 1 DDS on 39). **Applied** in §2;
the fix is to resolve the magic for all 21,998 distinct rows once, from the ids already
collected in `refs.json`.

**P9 — D1's criterion was weaker than it read.** **Applied:** it now requires a
generated-versus-carried report with a floor.

**P10 — a second stock build sits unused in the vault.** Build fragility was never
asked, so we do not know whether a custom area is durable or per-build. **Applied** as a
paragraph in §10; one `asserts.py` run against `2026-04-30_b174de1f2d8d` answers it, and
if the tables match it is a real second witness for one command.

**P11 — the ladder had dropped the repo's operating rules.** No rung named the archive
copy, `cage.assert_launch_safe`, the account, or the §6.1 register row; B1–B3 carried no
suite line. **Applied** as the paragraph above the ladder and as rung A-1.

**P12 — numbers owed reconciliation.** §1's "708 of 724 MB" is four chunks excluding
Zones; five including it is 711.8. `studies/datwrite/FINDINGS.md` needs two correction
rows (its flags table calls flags-`0x0001` rows "stage-2 payloads" and its flags high
byte CONTESTED — this document resolves both). Free-space figures differ from that
document's — 32,528,384 B in 214 whole-block runs here against 85,261,813 B in 176,248
regions there — different measures, never reconciled, which is precisely the
two-authorities failure `PLAN.md` §3's rule exists to prevent. And `FORMAT.md`'s 177,342
entries against this pass's 177,341 addressable rows belongs in the ledger.

**RECONCILED 2026-08-10 (§18.7), and both figures were right.** The difference is
`sum(alignup(size,512) − size)` = 52,733,429 B of dead space *inside* rows' own
reservations — predicted before the run and holding to the byte on two independent
readers. The MFT-headroom pair differs by the MFT's own 48 B of block padding. **Two
corrections to this P12 entry itself:** `studies/datwrite/FINDINGS.md` *already carried*
the reconciliation verbatim, so P12 described this document failing to carry a resolution
the other one had, not a genuine disagreement; and P12's third disputed figure is not
disputed — `datwrite`'s 176,033 **reproduces exactly** under the definition the rule it
evidences actually needs. Do not overwrite it. **And the reconciled number means less than
either document thought:** 88.5% of that "free" space holds live shadow generations of the
archive's own MFT and file-id table, so genuinely unclaimed space is **3,742,720 B in 209
runs, largest 953,856 B** — below the median map head reservation.

**P13 — §12 proposes a join the repo has already shown is impossible.** Naming the 24
double-tag-3 maps "against `studies/areatable`'s map-id table" cannot work: that table
carries no map file id. The only routes are GWMB's renderer by eye or the wiki, both
owner-gated.

### The critic's verdict on the headline

Quoted, because it is the fairest summary of this document's standing:

> The read-side headline is supported; the cost model and the "one cheap launch settles
> it" framing are not yet. […] **"The export half is a weekend"** rests on a decoder that
> has never written a byte and on an interchange whose two hardest conventions — height
> sign / up axis, and cell-versus-vertex — are unresolved and internally contradicted.
> **"The client also carries its own map compiler"** is entirely SOURCE-CODE from one
> build, with no `load` handler read and no second-caller trace — a well-posed hypothesis
> presented one register too confidently for something the whole estimate's largest
> variance depends on. […] None of that touches the "yes" — a custom area does look
> reachable. It means the document should be read as: **the reading is done, the
> specification of the first experiment is not**, and the cheapest next move is not C1 or
> C2 but an afternoon with capstone on the chunk load handlers.
---

## 17. Rung C0 — the chunk load handlers (2026-08-10)

Five survey tracks, each adversarially re-verified by a second agent, then synthesised.
Tracks: **A** the bloat flow and the second caller of `0x00707330`; **B** Map Parameters
`0x007129F0`; **C** Path `0x007125E0`; **D** Terrain `0x00711DF0` (not asked for by C0's
specification, taken because the Terrain handler is the one an exporter is built
against); **E** PathEngine `0x007131E0` plus the other slots of `s_chunkInfo`.

The verifiers returned **124 verdicts: 90 CONFIRMED, 21 WEAKENED, 11 REFUTED, 2
UNCHECKABLE.** Every refuted and weakened claim is carried here in its **corrected**
form and recorded in §17.6. Three of the refutations changed an authoring conclusion and
one killed a proposed experiment. Two of the five surveys shipped a "check that cannot
fail" of their own, in a pass whose brief named that defect explicitly — both are in the
ledger.

Everything below is read-only against `vault/client/2026-07-29_221c13772c7a/Gw.exe`
(build 38797, ImageBase `0x00400000`, 10,483,904 bytes) and
`vault/dat_study/Gw.dat` opened read-only. Nothing in the repo was modified, no client
was patched or launched, `C:\gw` was listed and never written.

---

### 17.1 The answer, plainly

**No. The client does not compile a map on a normal load. Bloat runs only as a
post-failure repair — and the repair is cheaply, deliberately triggerable, which is a
better answer than "no" sounds.**

The tracks do not disagree. Track A answered it directly and Track C corroborated it
from the opposite end with a control that could have failed.

**Track A, MEASURED.** The bloat driver `0x00707330` has exactly two callers and no
function-pointer references (`codescan --xrefs`: 2 direct rel32, **0 data words** — the
zero rules out a dispatch table reaching it, and both passes reproduced it).

- Caller 1, `0x007079BB`, sits inside the map-file loader `0x00707650` and is reachable
  **only** after a failed stream open or a chunk parse that returned 0. The verifier
  rebuilt the control-flow graph independently with predecessor sets (402 instructions,
  `0x00707650`–`0x00707AFE`): the predecessors of the failure block `0x007077EC` are
  exactly `{0x00707731` (open returned 0)`, 0x007077E9` (parse returned 0)`}`. On success
  the `jne` at `0x007077E1` transfers straight to `0x00707AF6` and nothing downstream of
  the bloat call reaches it. The attempt counter starts at 1 and gives up at 2 — **exactly
  one re-bloat per load call.**
- Caller 2, `0x00707EEB` — the one §1 and §16-P1 said nobody had followed — is **not
  inside `MapLoad`**. `MapLoad` ends at `0x00707CE2` with `ret` and int3 padding; the call
  is 0x209 bytes past it, inside a 137-byte unconditional wrapper `0x00707EA0` whose
  single caller is arm 3 of an 8-entry jump table in `P:\Code\Gw\Download\DnBloat.cpp`,
  whose single caller is `0x007D75E0` in `P:\Code\Net\FileCli\FcArchive.cpp` — the
  **content-download / patch-install** pipeline (`rec->incrementalBloat`,
  `progress->bloatIndex == s_indexTotal`). It is a download-time step, not a load-time one.

Independently and exhaustively: `s_chunkInfo+0x18` (the bloat handler) is loaded by
**exactly one instruction in the entire 10,483,904-byte image**, at `0x00713C5F`, inside
the stage converter `0x00713630`, which has exactly one caller — inside the driver. The
load path cannot reach a bloat handler. Two independent whole-image byte scans agree on
which twelve references to the table exist and where.

**Track C, the control.** The same reachability tool at the same depth, run both ways:
from the Path bloat builder `0x00724670`, 202 functions reaching **14 `PathBuild.cpp`
and 6 `PathFlood.cpp`** assert sites and **0** `PathDataImport`; from 19 seeded load-path
roots, 226 functions reaching **9 `PathDataImport` sites** (which is all nine in the
binary) and **0** of either builder module. The control could have failed and did not.
Correction carried from the verifier: the two closures share 186 functions of common
infrastructure (Array, Hash, Str, allocators), so the right sentence is *"they share no
Path-module code, and neither the bloat driver nor the builder `0x0072FB80` is reachable
from the load path"* — not "not a line of code".

**What the rung gains, and it is the useful half.** The repair reads a **different MFT
row** than the load. The client resolves a file id to a head row, then walks
`alloc.nextStream` (`+0x10`) matching `alloc.stream` (`+0x0F`) against a requested byte:
**1 on a normal load** (the Bloated row), **0 on the re-bloat read** (the Stripped
partner), then converts stage 1 → 2 and writes the result back to **stream 1**, addressed
by `(fileId, streamId)` rather than by MFT offset. The archive corroborates the walker at
349/349 and 171,025/171,025: the rows the repo calls "flags 259" are exactly
`(alloc.flags 3, alloc.stream 1)`, all 349 partners are exactly `(1, 0)` with
`nextStream == 0`, chain length is 1 in 349/349, and no partner is named by the file-id
table.

So the route §1 hoped for exists. **It is a deliberately-provoked repair, not a normal
load**, and it is triggerable three ways, cheapest first: a **zero-length** stream-1
payload (the loader's `size == 0` branch at `0x00707749` falls straight through to the
re-bloat with no parse attempted — verified instruction by instruction), a stream-1
payload that is not `ffna`/type 3, or a structurally valid payload with a wrong chunk
magic. The first needs the fewest authored bytes.

One thing this does **not** establish, and it is the cheapest possible test of the whole
model: whether retail's Bloated streams were shipped by ArenaNet or produced by this
client at download time. The two bloat entry points, `FcApi:1393/1394`'s paired
`downloadIndex`/`bloatIndex` progress meter, and `MapData:997` *"Only clients can bloat
client maps"* all point at locally-generated — **INFERRED, not measured.** Two machines'
archives, or one archive across an update, would settle it, and if it is true then every
retail Bloated map in this archive is already an output of the compiler we want to borrow.

---

### 17.2 What this changes in the study

**§1's central argument moves register.** *"The client also carries its own map
compiler… whether that path is reachable is NOT FOUND"* becomes: **the compiler is
reachable, by making the Bloated stream fail, and the repair writes its output into
`Gw.dat`.** That is a real route and a real hazard in one sentence. §1 should stop
describing it as something that might happen on a normal load.

**Three rungs can be deleted. Deleting a rung is a result.**

| Rung | Status | Why |
|---|---|---|
| **C1** — "which stream does the client read?" | **DELETE** | Answered statically. Normal load requests stream **1**; the re-bloat read requests **0**; the write-back requests **1** with mode 2. Traced through five frames from `0x00470D50`'s arg2 to the byte compare at `0x0047AB11`, re-derived from the other end by the verifier via the byte store at `0x004715A9`, and paired with the archive's (3,1)/(1,0) structure at 349/349. No launch needed. *Caveat if anyone revives it: `File 0x%x stream 0x%x is corrupt` has exactly one reference in the image (`0x004763F6`, ANSI not wide) and two passes failed to locate its containing function — C1's whole instrument rests on an unlocated function.* |
| **C3** — "does the client bloat on a normal load?" | **DELETE** | Answered above. Its test premise is also impossible as written: there is no such thing as a "Stripped-only map", because a file id can only resolve to a `FLAG_FIRST_STREAM` row and all 349 of those are stream 1. |
| **E1** — "navmesh: rebuild or import?" | **DELETE as a paired launch** | On a normal load the client **imports**: `PathDataImport` is the only Path module on the load closure, the importer hardcodes stage 2 (`push 2` at `0x00725124`), and its bounds checks are per-record asserts, not a builder. §16-P4's carefully-repaired paired arm is no longer needed to learn this. What E1 was selecting between (E2 vs E3) is now a cost decision, not an experimental one. |

**C2 survives and its arm design changes.** Arm 3's expected `Attempting to re-bloat` is
not a harmless log — it is the client compiling the **stale partner** into the head row.
The before/after MFT diff §16-P2 requires must cover **both rows of the pair**, and the
pre-flight full-reservation dump must cover the head row specifically, because that is
the row the client overwrites. A second instrument became available: the riff-type
refusal `Map '%s' is not a valid riff type` is **unguarded** (the surveyor filed it as
guarded; the verifier refuted that — there is no `call 0x62af70` on that path), so it
fires on delivery arm (b) exactly where C2 wants a signal. `Attempting to re-bloat` is
also unguarded; the other three map messages (`Map '%s' failed to load`, `Creating
default map`, `could not be opened for writing`) are each suppressed unless a bit read as
`(evtCtx[0x14] >> 2) & 1` is clear.

**E3 survives and is now specified rather than hoped for.** Publish a stream-0 (Stripped)
payload holding the boundary polygon; make the stream-1 payload of the *same file id*
fail; the client logs, compiles stage 1 → 2, writes into stream 1, and retries once. The
Stripped Path input contract is now known exactly: `u32 0xEEFE704C`, `u8 12`, `u32
sequence`, then unsized `{7: u16 n, n × Vec2f}`, `{14: u32, u8}`, `{255}` — **19 + 8n
bytes, 349/349** — with stage 0 of the bloat pipeline hard-gating the signature and the
version *byte*.

**§10's largest variance does not collapse to a week, and saying it does would be the
comfortable lie.** "A week if the client rebuilds, a month if it imports" — it imports.
The honest restatement: **the month-branch is the default and it is now specified rather
than speculative** (Track C handed over the complete Path read set, including the DAG
child-reference encoding nobody had), while **the week-branch is a named, offline-preparable
experiment** (E3) that writes into the archive and must be run on a copy. The variance is
narrowed at both ends rather than removed.

**A new hazard is now the single most important open safety question for C2**, and it is
answerable offline: `ExeFile.cpp:252 totalBytes <= m_totalBytes` and `:253 extraBytes <=
totalBytes` are asserts inside `0x00477F90`, and the next three instructions
(`0x00478155`–`0x0047815B`) execute the store **unconditionally on both branches** — the
assert does not guard it. A Stripped → Bloated conversion grows the payload roughly 2×
(Terrain's bloat ratio 0.4673 inverted), so the head row must grow. Whether the archive
relocates, refuses, or writes past the reservation is unestablished, and relocation
remains the one archive operation nobody has exercised (§16-P2).

**Six rows of §12 close or narrow.** Detailed in §17.7.

---

### 17.3 How a handler is called — the dispatcher

The chunk loop is `0x00714150`. It fetches `s_chunkInfo[id]` and calls the load slot with
**nine cdecl arguments** (`add esp, 0x24`). The frame layout, corrected — the surveyor of
Track E offered this as "the key the other C0 tracks need" and put `mapType` in the wrong
slot; the verifier refuted it from the call site and from Terrain's own
`Clients cannot create server maps` assert:

| Slot | Meaning |
|---|---|
| `[ebp+0x08]` | a per-map-type **stage constant** from the manifest header `+8` — **not** the file's stage |
| `[ebp+0x0C]` | a pointer (Map Parameters' bloat handler passes a literal string address in the same slot) |
| `[ebp+0x10]` | **mapType** |
| `[ebp+0x18]` | payload **size** (out-param of `0x00907C70`) |
| `[ebp+0x1C]` | payload **pointer** |
| `[ebp+0x28]` | `MapData*` |

Three structural facts about the dispatcher matter to an author more than any single
handler:

- **`s_chunkInfo[id].load` is fetched and called with no null check.** `mov eax,[ebp+0x18]`
  / `mov eax,[eax+8]` / `call eax`, nothing in between. The `+0x00` and `+0x04` slots
  *are* null-checked before their indirect calls; `+0x08` is not. A chunk carrying one of
  the four dead ids (0x01, 0x05, 0x0B, 0x0D) does not fail cleanly — it calls address 0.
- **The `ptr->id < 23` assert does not guard the index.** `0x007142F4` fires the assert and
  the very next instructions compute `[id*5*8 + 0xA6CF80]` unconditionally.
- **A chunk kind absent from the file is default-constructed, not rejected** — the loader
  calls the `+0x00` slot with the map extent. Only Header has a NULL `+0x00`. This
  materially widens what a minimal authored map may omit.

**The slots, settled (Track E, and confirmed on a second build):** `+0x00` is the per-chunk
**constructor**, `+0x04` the **destructor** (called in reverse manifest order by
`0x007140C0` and by the loader's error unwind at `0x00714700`), `+0x08` **load**, `+0x18`
**bloat**, `+0x20` an `f32` cost, `+0x24` a UTF-16 name. `+0x10` is a **writer slot**,
non-NULL on exactly one row — Header's `0x00711CD0`, which emits `{u32 0x39871124, u32 3}`
and returns 1. Its inverse is the Header load at `0x00711C80`. **No instruction in the
image indexes `+0x10`**, so the client's only per-chunk serialisers are the bloat handlers.
`+0x0C`, `+0x14`, `+0x1C` and `+0x20` are read by nothing.

**Asserts are worse than hard gates in this build, and that inverts the usual intuition.**
All 19,620 sites are compiled in and call `0x00487BC0` unconditionally, which calls the
reporter `0x00488210` unconditionally. The reporter's 704-byte body
(`0x00488210`–`0x004884D0`) contains **zero `0xC3`, zero `0xC2` and zero `0xCB` bytes** —
no `ret` opcode exists anywhere in it, measured at the byte level so alignment cannot hide
one — and it ends `push 1; call 0x005BC094; int3`. `0x005BC094` is
`push 0; push 2; push [ebp+8]; call 0x005BBF04`, the MSVC CRT `exit(code)` → `doexit(code,
0, 2)` idiom, and the reporter imports only `GetCurrentThread`, `GetThreadContext`,
`VirtualAlloc`, `VirtualFree` — no user32, so no dialog. **MEASURED:** the reporter cannot
return. **INFERRED (strong):** it terminates the process.

For an authoring tool the ranking is therefore inverted: **a hard gate makes the chunk
fail and `MapLoad` synthesises an empty default map; an assert stops the client.** A
*structural* authoring error (bad magic, wrong version, missing record, size overrun) is
the safe failure. A *semantic* one (out-of-range neighbour index, oversized count, unknown
rootType) is the unsafe one. Design C2's negative controls accordingly.

---

### 17.4 Read sets and reject sets

**Offsets listed as not read are free for an author** — the client will accept any bytes
there. Offsets listed as read but uncompared are consumed silently: getting them wrong
misplaces the world rather than producing an error.

#### Map Parameters — `0x2000000C`, load `0x007129F0` → `0x0070D920`

A 9-instruction thunk into a 299-byte reader. **Every one of the 41 payload bytes is
read.** There is no unused offset inside the chunk; bytes past `+0x29` are free, because
the gate is `size >= 41`, not `== 41`.

| Offset | Width | Read? | What the client does |
|---|---|---|---|
| +0x00 | u32 | ✓ | `== 0x5943EEEF` or return 0. **Hard gate.** |
| +0x04 | u8 | ✓ | `== 2` or return 0. **Hard gate.** A *byte*, so the rect floats start at the unaligned offset +5. |
| +0x05..+0x14 | 4×f32 | ✓ | `mapRect.{x0,y0,x1,y1}` → MapParams+0x00..+0x0C. **Copied verbatim. Zero x87 instructions in the whole function** — no clamp, no NaN test, no `x1>=x0`, no comparison against dims. |
| +0x15 | u32 | ✓ | Flags. Top byte: if 0, rewritten to 1 in memory; if ≥3, bit 0x20 ORed in. The whole word is handed to Terrain's create call as argument 1. |
| +0x19..+0x28 | 16 B | ✓ | An **RFC 4122 version-4 UUID**. XORed in place, four dwords against one key `H(filename) ^ 2·H(filename+1)`. Never compared to anything. |
| +0x29 onward | — | ✗ | **Free.** No shipped map is longer than 41. |

**Reject set.** Data pointer NULL, size `== 0x10` exactly (an early-out with no visible
motive), size `< 5`, signature mismatch, version mismatch, size `< 41` — all **hard
gates** to a common `xor eax,eax; ret 0xc` epilogue. The only assert in the function is
`MapParams:325 filename[0]`, and it is not a data check. A failure is **not partial**: the
dispatcher unloads every chunk already loaded, logs `Map '<id>' corrupt chunk 'Bloated
Data Map Parameters'`, and `MapLoad` falls back to the empty default map.

**Archive:** 349/349 carry `0x5943EEEF`, version 2, exactly 41 bytes; 0/349 are 16 bytes.

**The 16-byte field is a content id and the client never checks it.** MEASURED: in 349 of
349 maps the version nibble (MS byte order, byte 7 high nibble) is exactly 4 and the
variant bits are exactly `0b10`, while all 126 other bits sit at 0.486–0.512
ones-frequency — a test with a 1-in-64 chance per map that passed 349 times. Kamadan (row
22371) reads `b6e21d73-3fa0-43d4-99cb-af2f4d0e8152`. The loader contains exactly nine
`cmp`/`test` instructions and none touches those bytes; the constructor `memset`s them to
zero; and an image-wide scan of all 1,089 `call 0x0047F660` sites (the current-map
accessor) found zero displacements in `0x18..0x27` **while detecting the adjacent rect
floats** — the positive control that gives the negative its power. Both passes reproduced
1,089 sites and zero hits.

**Corrected register (verifier).** Report this as *"no read found, by a scan that
demonstrably detects the adjacent fields"* — not as closed. The MapParams pointer escapes
as a bare pointer through Terrain (`lea eax,[esi+4]` at `0x00711E38` →
`0x007587B0` → `0x00761E70`), and neither pass followed that chain. §12's row narrows to a
well-controlled negative with one named uncovered route.

**Rect placement is a convention, not a rule.** The client's own constructor produces
`x0 = -(cx>>1)·3072`, `x1 = (cx-(cx>>1))·3072` with `cx = dimX/32`. That matches the file
bit-exactly on **348 of 349** maps — row 46196 stores literal negative zero, as the formula
predicts — and **row 29590 ships a symmetric rect instead**. Extent `% 3072.0 == 0` on both
axes in 349/349. Follow the constructor's formula; do not build a validator that treats
deviation as an error, because retail deviates.

#### Terrain — `0x20000002`, load `0x00711DF0` → `0x007587B0` → `0x00761E70`

A wrapper into an 11-entry step table at `0x00A74F28` (`{fn, f32 cost}`, costs summing to
1.0399999991059303), each step demanding one tag in one order: **header, 0, 1, 2, 4, 5, 3,
9, 7, [3], 255**. There is no dispatch loop. That pipeline is exactly the two tag sequences
§4 measured (325 + 24 of 349), and the optional ninth step — the only one that saves the
cursor and returns success on a tag mismatch — is *why* 24 maps carry a second 17-byte
tag-3 record.

| Record | Read? | What the client does |
|---|---|---|
| header +0x00 | ✓ | `== 0x87821134`. **Hard gate.** |
| header +0x04 | ✓ | `== 0x11` as a **full u32**. **Hard gate.** (Corpus: high 16 bits zero 349/349, so the full-width compare is a real authoring constraint.) |
| tag 0 +0x00/+0x04 | ✓ | dimX, dimY. `% 32 == 0` and `dimX*dimY <= 0x1000000` — both **hard gates**. |
| tag 0 +0x08 | ✓ | `f32`, gated `>= 0.0`. Consumed as `max(3, (int)(v / 3072.0))` — **a distance in whole 32×32 terrain chunks, not a cell size.** 3072 = 32 × 96. |
| tag 0 +0x0C | ✓ | `f32` angle, gated `>= 0.0` and `<= 1.5707963705062866`. A u8 quantised as `b·90π/45720`; **all 349 corpus values land exactly on that lattice**, b ∈ [16, 250], 54 distinct. b=254 is bit-exactly the gate constant; b=255 is the one writable value the reader rejects. |
| tag 0 +0x10/+0x12/+0x16 | ✓ | u16, then two **unaligned** f32 floored at 0.01. All three go to the texture subsystem; none constrains geometry. |
| tag 1 | ✓ | Heightmap. `(dimY/32)×(dimX/32)` consecutive 4096-byte tiles, **plain `memcpy`, no transform**. |
| tag 2 / tag 9 | ✓ | Two u8 planes, **same reader**, same 32×32 tiling, same edge replication, different destinations. |
| tag 4 / tag 5 | ✓ | `u8 n` + n bytes each. Tag 5's bytes are masked `& 0x7F` — bit 7 discarded (unexercised: 0 of 17,089 corpus bytes set it). |
| tag 3 | ✓ | 2 bits/cell, tiled, de-tiled into a flat buffer. **Per-cell, no +1 edge extension** — unlike tags 1/2/9. |
| tag 7 | ✓ | Per 32×32 block `{u32 k, k bytes, 128 bytes}`. **The only record whose declared size is load-bearing** — it sizes the reserve. The block count comes from the object, not the file, and **the loop bounds-checks nothing**: a short tag 7 is read past its end. |
| tag 3′ +0x00 | ✗ | **Never read.** The 0x01 byte in all 24 maps is free. |
| tag 3′ +0x01..+0x10 | ✓ | Four f32 → TrnTex +0x291C/+0x2920/+0x2928/+0x292C, **in record order** (see §17.6). |
| tag 255 | header only | Terminator; its size field is ignored and nothing after it is read. |

**Per-record `size` is advisory for every tag but 7.** `0x0073E410` returns
`end >= cursor+5+size` and **never adds size to the cursor**; each step advances by a
length derived from dims. A size that is too small is silently accepted; only an overrun
rejects. Our own walkers are stricter than the client, which is the right way round.

**Two questions §12 filed NOT FOUND close here.**

1. **Samples are at cell CORNERS (vertices).** The chunk grid is allocated
   `(dimX/32 + 1) × (dimY/32 + 1)`; only `(dimX/32) × (dimY/32)` tiles are filled from the
   file; the loader then synthesises the extra column by replicating each row's column-31
   float and the extra row by replicating the last real row. The verifier found the
   decisive site the survey missed: step 2's unlisted post-call `0x0074A800` → `0x0074A620`
   runs a per-chunk min/max over `mov eax, 0x441` = **1089 = 33×33** samples for a 32-cell
   chunk. ArenaNet's own vocabulary agrees (`TrnQueryBasic:385 vertexRect`,
   `TrnMap:935/936/999/1000 rect.x1 <= dims.x + 1`). And the falsifier is absent:
   `0x0074DB5C`–`0x0074DB9A` computes `x0 + 96·i` and `y1 − 96·j` with **no half-cell
   offset anywhere**.
2. **The load path applies no transform to heights.** Tag 1 reaches the buffers through
   `memcpy` and nothing else — no negation, no resample, no re-grid. *Weakened from the
   survey's phrasing:* the `fchs` opcode scan the survey leaned on omitted the height-query
   solver `0x0074E220`, which holds five of the 28 sites (they are the `−b` of a quadratic).
   The structural argument carries the claim; the opcode scan does not. GWMB's negation
   remains a renderer convention (§16-P5). Worth stating for an importer:
   **86.4% of all corpus height samples are negative**, range −19,632..+5,002, every value
   an exact integer.

**Corrected caps.** `TrnCreate:52/53`'s 4096 dimension cap is **not** on the load path —
`0x007583F0` has exactly one caller, inside the create-empty path reached from the
`+0x00` slot. The loader's own caps are `dims % 32 == 0` and `dimX·dimY <= 2^24`. The area
gate is 57× above the largest shipped map (768×384 = 294,912) and cannot be exercised by
shipped data.

**Terrain has no world extent of its own.** The mapRect arrives from Map Parameters through
the import context. Corpus-wide join, run this session and closing an item the survey had
checked on five maps: **chunk `0x2000000C` is at chunk index 1 — the second chunk,
immediately after the header — on 349/349, and Terrain at index 5–8.** Map Parameters
precedes Terrain on every shipped map.

#### Path — `0x20000008`, load `0x007125E0` → `0x00721950` → `0x00724F90`

A fixed seven-stage table at `0x00A6F278` driving **header(12 B) → skip one record → tag 8
→ tag 12 → tag 13 → tag 14 → tag 255**, with `push 2` hardcoding the Bloated framing. No
dispatch, no reordering, no omission. The archive shows exactly `(7, 8, 12, 13, 14, 255)`
on **349/349** and the walk closes to the final byte on 349/349.

| Record | Read? | What the client does |
|---|---|---|
| +0x00 | ✓ | `== 0xEEFE704C`. **Hard gate.** |
| +0x04 | ✓ | `== 12` exactly, as a u32. **Hard gate.** |
| +0x08 `sequence` | ✓, discarded | `cmp dword [esi+8], -1` → assert `PathDataImport:89`, then **falls through**. Never stored, never re-read. **`PATH_SEQUENCE_FAST_SAVE == 0xFFFFFFFF`, read from the immediate, not from the assert string.** |
| tag 7 (boundary polygon) | ✗ | **Skipped by size.** The tag is not checked; only the size field matters, because tag 8 must land at the next offset. |
| tag 8 | ✓ | planeCount, then per plane a **fixed 10-record table** at `0xBF730C` in order 0, 11, 1, 2, 3, 4, 5, 6, 10, 9 with disk strides 32/8/8/44/1/16/12/4/4/9. |
| tag 12 | ✓ | `u16 n` + n u16. Element 0 is not read from the file. |
| tag 13 | ✓ | `u16 w, u16 h, u16 m`, then w·h 3-byte tiles and m 12-byte records. **Size == 6 + 3wh + 12m, 349/349.** |
| tag 14 +0x00 | ✗ | **Stepped over without being dereferenced.** §7's cross-stage identity #1 is not a load-path constraint. |
| tag 14 +0x04 | ✓ | If non-zero → `Client pathing data out of sync with server. You may observe your character 'warping' during movement.` and **carry on**. Retail ships it set on **318 of 349** maps. |
| tag 255 | header only | Terminator; its size is ignored. |

**Reject set.** All framing failures are **hard gates** and all index checks are
**asserts** — which, given §17.3, means the index checks are the dangerous ones. The four
trapezoid neighbour indices do `cmp ebx,[eax+0x14]` / `jb ok` / assert
`PathDataImport:50` / **then compute `base + index·48` and store the pointer anyway**. The
function *has* a failure epilogue at `0x007261C0` and uses it for the length checks; it is
simply not wired to the index checks. `portalLeft`/`portalRight` and every portal field are
copied with **no comparison at all** at load; the only bounds on them
(`PathDir:1494/1530`) live in the query path.

**The biggest gap either pass found, and it is an encoding an author must reproduce.**
`0x007264A0` decodes every point-location DAG child reference as a tagged index:
`0xFFFFFFFF` → NULL; `>= 0x80000000` → sink node, bounded with assert
`PathDataImport:64`; `>= 0x40000000` → y node, `PathDataImport:68`; otherwise x node,
`PathDataImport:72`. The survey's read set omitted it entirely. **MEASURED, with the
prediction written before the run: 10,829,572 child references across all 349 maps decode
into the four buckets with zero out-of-range indices** — xnode 4,462,623, null 2,784,573,
ynode 2,125,005, sink 1,457,371. Relatedly, the 16-byte x-node record carries **two** edge
indices, not one: `{u32 edgeA, u32 edgeB, u32 child0, u32 child1}`; the 12-byte y-node is
`{u32 edge, u32 child0, u32 child1}`.

**Corpus checks the survey filed "not checked" and the verifier ran, all clean:** x-node
edge indices 3,872,385/3,872,385; y-node 1,542,401/1,542,401; 85,694 portals with zero
`offset+traps` / `neighbour` / `traps` violations; 2,064,518 `portalLeft`/`portalRight`
values in range; and the neighbour figure §6 already carried reproduced exactly —
4,129,036 fields, 2,034,370 sentinels, **2,094,666 in range**, which is what that number
counted. **`rootType` is 1 on 11,795 of 11,795 planes** — values 0 and 2 never occur, so
the code's three modes are real and retail exercises exactly one.

**The Stripped stream cannot reach this loader.** Its u32 at +4 reads as
`12 | (sequence << 8)` and fails the version gate on **347/349**; the two exceptions
(rows 32333 and 36590, sequence 0) clear the gate and then desync inside tag 7. Recorded so
nobody later reports "the version gate rejects all Stripped chunks" as 349/349.

**Sequence, answered both ways.** The loader discards it. The **bloat** handler copies it
verbatim from the Stripped 9-byte header into the Bloated 12-byte one — which explains
§7's identity #2 as a property of ArenaNet's writer rather than a constraint the loader
enforces (`sequence == sequence` across stages, 349/349, 224 distinct values in 0..4601,
0 of 349 equal to `0xFFFFFFFF`).

**The "second serialisation" the assert implies is the Stripped stream**, and the code that
consumes it is the bloat handler — not an alternative loader. `0x007261E0` is 0x49 bytes
long, contains no store of `[esi+8]` and no branch to a second parser.

**pathmap.py's plane layout gains a second witness.** §13 counts the navmesh as one
lineage (GWMB credits ldufr, who wrote OpenTyria) plus two unattributed artifacts. The
client's own dispatch table and readers agree with `PLANE_LAYOUT` on **all ten tags and all
ten element sizes**, re-walked independently: 11,795 planes, 1,032,259 trapezoids, closing
on the exact final byte of tag 8 on 349/349.

#### PathEngine — `0x20000016`, load `0x007131E0` → `0x00737210` → `0x007374A0`

**`Gw.exe` reads zero bytes of this payload.** The handler forwards `(size, pointer)`
untouched to a vtable call with the literal format name `"tok"`, and the chunk is the
commercial **PathEngine SDK's** own self-describing mesh — module paths
`P:\Code\Engine\Map\PathEngine\PeApi.cpp` / `PeObject.cpp`, DLL name string
`PathEngine.dll`, resolved by `LoadLibraryA` + `GetProcAddress(ordinal 1)`.

**Reject set, both branches SUCCESS:** payload size == 0 → return 1 without touching the
payload; `PeObject->interface == NULL` → return 1 without touching the payload. The second
is the branch that runs: **no `PathEngine.dll` exists in either vaulted client snapshot or
in `C:\gw`** (recursive search, both). So the object never materialises, the loader reports
success having parsed nothing, and **every byte offset of a PathEngine chunk is free.**

It is nonetheless live code, not vestigial. `Map.cpp:1195–1239` asks `PeObject::IsLoaded`
first and, when it answers yes, routes the client's path query through PathEngine
**instead of** the trapezoid navmesh. A compile-time-present, runtime-dead alternate
back-end whose only trigger is a DLL nobody ships.

**Decoded anyway, because it is a free cross-check.** The `tok` payload declares
`mesh{majorRelease=5, minorRelease=8}` in its own data — **PathEngine SDK 5.08** — and the
token walk consumes **exactly 69,570 of 69,570 bytes**, yielding **1,960 vertices and
2,862 triangles**, 8,586/8,586 vertex indices in range, extents x/y ∈ [−3072, 3072],
z ∈ [196, 3312]. `edge{k}Connection` is the neighbouring triangle's index under the
convention *edge k = (v_k, v_{k+1})*: **3,840 attributes, 3,840 geometrically shared edges,
3,840/3,840 agreement**, stored on exactly one half-edge each, 906 boundary edges carrying
none. Three of four rival width models crash and the fourth misses by one byte — the
closure is a real check. Rows 26209 and 26210 carry byte-identical copies (sha256 match),
which the bloat handler predicts: `0x00713240` is a verbatim buffer append.

---

### 17.5 The authoring specification, assembled

**Container and order.**

- Emit **Map Parameters before Terrain**. Terrain carries no world rect; it copies one out
  of the map object that only Map Parameters fills. 349/349 retail maps put Map Parameters
  at chunk index 1.
- **Never author chunk id 0x01, 0x05, 0x0B or 0x0D.** Those four have a NULL load slot and
  the fetch is not null-checked: the client jumps to address 0. Ids ≥ 23 are worse — the
  assert fires and the index runs past the table anyway.
- **A chunk kind may be omitted.** Absent kinds are default-constructed from the `+0x00`
  slot. Only Header must be present (it is the sole NULL `+0x00`).
- **Emit two MFT rows with the right `alloc` bytes.** Head: `alloc.flags = 3`
  (USED|FIRST_STREAM), `alloc.stream = 1`, `alloc.nextStream = <partner index>`. Partner:
  `alloc.flags = 1`, `alloc.stream = 0`, `alloc.nextStream = 0`. Only the head may be named
  by the file-id table. Writing 259 and 1 as opaque u16 "flags" happens to produce exactly
  this — and `archive.py`'s `Entry.counter` must be renamed `next_stream` before any writer
  treats it as a counter (see §17.6).

**Map Parameters — 41 bytes, all load-bearing.**

- Signature `0x5943EEEF`, version byte `2` — hard gates. The version is a **byte**, so the
  four rect floats begin at the unaligned offset +5. A writer that pads to align them emits
  a broken chunk.
- Never emit exactly 16 bytes; a gate at `0x0070D935` rejects that size and nothing else.
- The rect is copied with **no validation at all** and handed to Terrain as an input. Extent
  must be a multiple of 3072.0 on both axes (349/349, and it falls out of `extent = dims·96`
  automatically). Follow the constructor's centring formula; do not enforce it.
- The 16-byte field: **emit a fresh UUIDv4.** Zero is known-safe (the constructor memsets
  it), reuse is safe (nothing compares it), but a real UUID is what every shipped map does
  and it keeps the field legible.
- The flags word: copy `0x03000020` (the corpus mode, 92 of 349) or accept that a 0 top byte
  is rewritten to 1 in memory. Only bits in `0x07000039` are ever set in any shipped map;
  the middle 16 bits are zero in 349/349.

**Terrain.**

- Cell pitch is **96.0 and is not yours to choose** — a compile-time constant on the Bloated
  path and a hard `== 96.0` equality gate on the Stripped path.
- Dims must be multiples of 32; the real area cap is `dimX·dimY <= 2^24`, not 4096 per axis.
- **Store `dims × dims` samples; the client manufactures the `dims+1` vertex column and row
  by duplicating their neighbours.** If your source mesh has a genuine `(dims+1)²` lattice,
  the far edge you supply is discarded — plan that mapping, do not discover it.
- **Do not negate heights.** Store float32 as your world-up value. Declare the transform in
  writing before comparing against GWMB (§16-P5/P6).
- Grid row 0 is world maxY. File index for tags 1/2/9:
  `((gy>>5)·(dimX>>5) + (gx>>5))·1024 + (gy&31)·32 + (gx&31)`. Do **not** confuse this with
  the client's in-memory stride, which is `(dimX>>5)+1`.
- Mandatory tag order, no substitutions: header, 0, 1, 2, 4, 5, 3, 9, 7, [3], 255. Every
  plane's ten sub-records likewise. There is no dispatch loop anywhere in this format.
- `tag 0 +0x08` is a **chunk-count distance**: emit a multiple of 3072.0, ≥ 9216.0 (below
  that it clamps to 3). 24576.0 is what 348 of 349 maps use.
- `tag 0 +0x0C` must be `b·90π/45720` in float32 for integer b ∈ [0, 254]. b=255 is rejected.
- **Tag 7's size field is load-bearing**; emit `4·nBlocks + Σk + 128·nBlocks` exactly, and
  know that a short tag 7 is read past its end with no bounds check.
- The second tag-3 record is safe to omit (325 of 349 omit it); if emitted, its leading byte
  is never read.

**Path.**

- **Author the Bloated chunk if you want the client to load it as-is** — the loader
  hardcodes stage 2 and a Stripped Path chunk fails the version gate on 347 of 349 maps.
  §11-C2's "Stripped Path is three thousand times less work" remains true about *bytes*;
  the client only accepts those bytes through the bloat handler.
- `sequence` is free: read, compared, discarded. Do not write `0xFFFFFFFF` (assert → stop).
  It need not match the Stripped copy — §7 lists that identity as something a writer must
  reproduce, and on the Bloated load path it is not.
- The boundary polygon (tag 7) is **dead weight for a Bloated map** — never read, only its
  size field matters. But it *is* the input to the bloat handler, so a map that ever gets
  re-bloated is rebuilt from whatever polygon is in the Stripped stream.
- **Get every index right, for a different reason than expected.** Nothing rejects a bad
  neighbour, portal, node or tag-12 index — it asserts and dereferences anyway, and an
  assert stops the client. Use `0xFFFFFFFF` for "no neighbour"; it short-circuits before any
  check. Reproduce the DAG child-reference tag space exactly (§17.4).
- A structurally-valid-but-geometrically-wrong mesh **loads silently** and stops the client
  the first time a query walks a bad portal. Worth knowing before any deliberately-wrong-mesh
  arm.
- tag 12 is `u16 n` + n u16 with `n == planeCount` — except on the three one-plane maps
  (26209, 46196, 71496), where n == 0 and the record is 2 bytes. Row 46196 is the ladder's
  template, so a builder that copies its shape gets the second form.
- tag 14: set the flag byte to 0 and the out-of-sync warning never appears. Retail ships it
  set on 318 of 349 maps, so it is not a correctness signal worth chasing.

**PathEngine.** Don't emit one. It buys nothing — 69 KB that the shipping executable never
reads, carried by exactly one retail map. *Corollary cutting the other way:* it is the
safest possible place to put a deliberately malformed payload in a delivery experiment,
because a refusal then provably came from the container walk or the CRC, not from chunk
validation.

**Header.** The one chunk we can emit with the client's own code as an oracle: `0x00711CD0`
writes exactly `{u32 0x39871124, u32 3}` and `0x00711C80` accepts exactly that.

---

### 17.6 Corrections ledger

Recorded rather than overwritten. Owed to earlier sections first.

**To §6 — the bloat-handler offset.** `+0x14` is null in all 23 rows; the bloat pointer is
at **`+0x18`**. Already corrected in §6 and re-confirmed here from four independent
directions, including the dispatcher's own arithmetic (`lea eax,[eax+eax*4]` then
`[eax*8 + 0xA6CF78]`, so the record is 40 bytes) and a second stock build. **The list of
nine is exactly right.**

**To §6 — "each gates on `stage != 2 → return` and then on map type."** Three refinements.
(1) The non-2 case returns **1 (success)**, not merely returns. (2) **Map Parameters has no
map-type gate at all.** (3) Collision's map-type failure is a hard `xor eax,eax; ret`, not
merely an assert. The generalisation holds for Collision and Locations, not for Map
Parameters.

**To §6 — the LOAD side's "stage" is not the file's stage.** The value a load handler tests
is `manifest[mapType].stage`, a compile-time constant (2 for map types 0, 2 and 3; 0 for the
Editor type), reached through a frame slot the loader overwrites with the manifest base at
`0x00714213`. For a client map the check is unconditionally satisfied whichever stream was
read. **This kills a proposed C1 instrument** (PathEngine's stage assert firing on a
Stripped stream) that a survey had offered as a free passive signal.

**To §3 — `s_chunkInfo`'s full record, and the manifest's.** Record:
`+0x00 ctor, +0x04 dtor, +0x08 LOAD, +0x0C 0, +0x10 writer (Header only), +0x14 0,
+0x18 BLOAT, +0x1C 0, +0x20 f32 cost, +0x24 UTF-16 name`. The map-type manifest header is
16 bytes `{u32 count, entries*, u32 stage, u32 ?}` and its 8-byte entries are
**`{u32 chunkId, u32 flag}`, not `{id, f32 cost}`** — the second word is 0 everywhere except
map type 2, where Props and Terrain carry 1. Reinterpreted as f32 it gives denormals of
1.4e-45. Type 2's records include chunkType 1 entries, the first **direct** evidence for the
`chunkType << 24` term §3 could only label INFERRED.

**To §11-A1 — the check that cannot fail, confirmed twice over and extended.** Both the
parser (`0x007142B7`) and the converter (`0x007138B3`) compute `1.0 / chunkCount` with
`fld1; fdivrp` and then assert `cost <= 1.0f` on *that*, with the count-0 case exiting
before the assert. And the extension nobody had: **no instruction in the image takes the
address `s_chunkInfo + k·40 + 0x20`.** The per-chunk cost weights (0.5 Terrain / 0.15 Props /
0.15 Path / 0.1 Sight / 0.05 Zones / 0.03 VisData / 0.02 Occluders, summing to exactly 1.00)
are read by nothing. §11-A1's "weak-but-real check on the +32 offset" is the only thing that
column supports.

**To §7 — both cross-stage identities are weaker constraints than stated.** Identity #1
(tag-14 u32) is **stepped over** by the loader without being dereferenced. Identity #2
(`sequence`) is discarded by the loader and copied verbatim by the bloat writer — a property
of the writer, not a rule the reader enforces. Identity #1 matters only on the bloat path,
where the builder compares its own computed value against it with `setne` at `0x0072435C`.
A **third** identity, unrecorded: the Path tag-7 boundary polygon is byte-identical across a
map's two independently compressed streams on 349/349.

**To §7 / §12 — the Map Parameters 16-byte field.** Identified as an RFC 4122 v4 UUID
(349/349 on version nibble and variant bits), **not compared to anything by the loader**.
The "obvious reading" is confirmed as an identification and demoted as a constraint.

**To §4 — three items.** (1) The `f32` at tag 0 +0x08 (GWMB's misnamed `cellSize`) is
consumed as `max(3, v/3072.0)` — a distance in whole terrain chunks. (2) `TrnCreate:52/53`'s
4096 cap is on the create-empty path, not the loader; the loader's caps are `dims % 32 == 0`
and `dimX·dimY <= 2^24`. (3) tag 0's angle is a u8 quantised over [0, π/2] in 254 steps, and
all 349 corpus values sit exactly on that lattice.

**To §12 — cell-versus-corner is no longer NOT FOUND.** Corners. Four sites in the binary,
including a 33×33 = 1089-sample per-chunk bounding box, and the absence of any half-cell
offset in the world↔grid conversion.

**To §13 — the navmesh witness count improves.** The client's own 10-entry dispatch table
and its ten readers are a genuinely separate witness for `pathmap.py`'s plane layout, and
they agree on **all ten tags and all ten element sizes**. That turns a one-lineage layout
into a client-corroborated one.

**To `toolkit/mapdata/archive.py`, and to `studies/datwrite/FINDINGS.md`.** `Entry.counter`
is misnamed: it is `alloc.nextStream`, an MFT row index (44,700 rows archive-wide resolve).
`Entry.flags` is **two independent bytes**, `alloc.flags` (+0x0E, bit 0 USED, bit 1
FIRST_STREAM) and `alloc.stream` (+0x0F). ArenaNet's own asserts name all three
(`ExeArchive:1418/1419/1421/1422`). This resolves the flags-high-byte question §16-P12
records as CONTESTED. The archive-wide stream histogram is
`{0: 132,633, 1: 1,467, 2: 21,421, 11: 21,420, 12: 393, 255: 7}` — the 21,420 rows at stream
11 are the partners of the 21,421 stream-2 heads, i.e. §3's "21,420 `ffna` type 2" bucket
seen from the other side.

**Refuted within this pass** (survey claim → corrected claim):

| Refuted | Corrected |
|---|---|
| `Map '%s' is not a valid riff type` is guarded by `0x0062AF70` | **Unguarded.** It joins `Attempting to re-bloat` as a message an experiment can rely on — and it is the one that fires on C2's delivery arm (b). |
| "I audited every read of `[ebp+0x18]`; they dereference +0x00 and +0x08 and nothing else" | There is a third: `+0x24` at `0x007146DB`, the chunk name feeding the parser's own missing/corrupt report. The `+0x18` negative is untouched; the sentence that closed the scope was false, in a rung whose deliverable *is* the read set. |
| Map Parameters' flags `>= 3` test drives the global at `0x00F26CA4` | It does not. The `call 0x007914E0` sits in the `top byte == 0` branch and its argument is computed **after** the byte is rewritten to 1 — provably the constant 0. A check that cannot fail, inside a report commissioned to hunt for them. The `>= 3` test ORs `0x20` and does nothing else. Two further consumers (`0x0070D760`, `0x0070D770`) were missed. |
| Terrain tag 3′'s four floats go to the setter as `(0, +0x0D, +0x09, +0x05, +0x01)` | Transposed. Record order: `+0x01 → TrnTex+0x291C, +0x05 → +0x2920, +0x09 → +0x2928, +0x0D → +0x292C`. An authoring tool using the survey's tuple would swap two components. |
| Terrain's angle gates fail on NaN | **NaN passes both.** `test ah,5; jnp` and `test ah,0x41; je` both let unordered through — and the same survey correctly noted this for the adjacent field. |
| The load handler's `mapType` is at `[ebp+0x0C]` | `[ebp+0x10]`. Offered as "the key the other C0 tracks need"; the evidence for it came from a different frame. |
| Terrain's bloat assert reads *"Client cannot create server maps"* | *"Clients cannot **bloat** server maps"*. Three near-identical strings exist and were merged. The constructor's own gate is `mapType == 0` exactly, not `{0, 3}`. |
| A bloat handler returning 0 logs `corrupt` at severity 1 (`0x00713F72`) | Severity **0**, at `0x00713FD0`. `0x00713F72` is the Dependencies-chunk read failure. Both abort the conversion. |
| Load and bloat "do not share a line of code" | They share **186 functions** of common infrastructure. What is true and load-bearing: no Path-module code is shared and the builder is unreachable from the load path. |
| tag-14's 31/349 and 318/349 are "two measurements meeting at one number they could easily have missed" | Arithmetically forced by the same report's other two 349/349 results. The real corroboration is the mechanism (`setne` at `0x0072435C`), which explains both numbers. |
| "Asserts are live but are NOT gates" | The *dispatcher* `0x00487BC0` returns; the *reporter* it calls cannot (zero `ret` opcode bytes in 704, byte-level). An assert is a stop, not a log. Three authoring implications rested on the weaker reading. |

**Systematic, and worth naming because it will recur.** Four of the five surveys cited
`s_chunkInfo` and similar accesses at the address of the instruction's **displacement
field** rather than the instruction (`+0x18` at `0x00713C62` when the `mov` is at
`0x00713C5F`, and so on). Disassembling at the cited VA desyncs into garbage — two verifiers
hit exactly that. Cite instruction boundaries.

---

### 17.7 Open questions

| Question | What would answer it |
|---|---|
| **Does a fresh install already carry stage-2 chunks?** The strongest unmeasured claim in this rung is that retail's Bloated streams are locally generated at download time | Two machines' archives, or one archive before and after an update. If true, every retail Bloated map is already an output of the compiler we want to borrow — the best possible news for E3, and the cheapest test of the whole model. |
| ~~**Can the write-back exceed the row's reservation?**~~ | **ANSWERED 2026-08-10, §18: no.** `ArchiveWriteFile`'s byte count is the identical dword handed to `SetEntry`, and `SetEntry` frees the old extent and allocates a fresh `roundUp(size, 512)` one — **there is no in-place write on the path, so there is nothing to overrun.** The premise was wrong too: `ExeFile:252/253` bound a heap scratch buffer, not an archive row, and both are unreachable from the guards above them. What §18 found instead are three *other* damage mechanisms, all of which require our writer to create them first. |
| **Is `0x004763F6` — the sole reference to `File 0x%x stream 0x%x is corrupt` — reachable?** | Two passes failed to bound the containing function (no int3 padding for at least 0x200 bytes back). If C1 is ever revived, this must be settled first. |
| **What sets the bit `0x0062AF70` reads?** It returns `(eventContext[0x14] >> 2) & 1` and suppresses three of the four map log messages | `EvtApi.cpp`. If it is set in normal play, an experiment relying on `Map '%s' failed to load` sees nothing. |
| **What is DnBloat's `Bloating mismatch %#x type %u` comparing?** `0x00834DA9` memcmps the handler's output against a caller-supplied buffer | One function-length disassembly. If the download path expects bloat to be deterministic, that is a free oracle for rung D1's generated-versus-carried criterion. |
| **What does the Path tag-14 u32 hash?** The bloat writer compares `[ctx+0x28]` against it with `setne` | Trace `[ctx+0x28]` back through `0x0072FB80`. Knowing it would let an authoring tool emit a value that survives a re-bloat with the flag clear. |
| **What does the Terrain flags word's top byte mean?** Values 0..5, three routes into the global at `0x00F26CA4`, and the whole word goes to Terrain's create call | `0x0071473C` and `0x007140E4` are the two unexamined call sites. The only field in Map Parameters an author cannot yet reason about. |
| **What are terrain tags 3, 4, 5 and 9?** Shape, tiling and consumers are now known; meaning is not. Tag 7 **is** named — `TrnMap::m_shadowData`, from the assert expression inside its own reader | `TrnTexLight:810/616` is the vocabulary for tag 9. *Note:* the link from tag 7 to `TrnCodecShadow:245` rests on filename adjacency only — the call chain is four levels away and unestablished. UNVERIFIED, not SOURCE-CODE. |
| **Is tag 4's `n` the same `count` as `MAP_TILE_MAX_COUNT == 63`?** The constant is real and the corpus maximum is exactly 63 | The call chain from tag 4's consumer to `0x00761CA0` was traced by both passes and does not close. The saturation is suggestive; the identification is INFERRED. |
| **What are archive streams 2, 11, 12 and 255?** 21,421 heads at stream 2 each with a stream-11 partner, 1,118 non-map rows at stream 1, 393 at 12, 7 at 255 | Nothing here needs it, but a writer that ever wants a third stream on a map row should know what the existing multi-stream kinds do first. |
| **Which map is row 26209, and why does it alone carry PathEngine?** | Still owner-gated per §16-P13 — the area table carries no map file id. GWMB's renderer by eye, or the wiki. |
| **What are `tok` type tags other than 3 and 4, and does attribute omission mean "absent" or "default"?** | One chunk is one witness and it exercises two tags. Settled for `edge{k}Connection` (3,840/3,840); unsettled in general. There is no second `tok` file in the archive. |
| **Why `L"FILT"`?** The Map Parameters bloat handler salts the UUID with that four-character constant where the loader uses the map's filename | Unexplained. Harmless — it is itself evidence that nothing validates the field, since two mutually inconsistent decodings coexist in one process. |
| **What is the load-path filename string, exactly?** | `MapLoad`'s argument 0. Until it is pinned the XOR key cannot be computed for a real map. Curiosity, not blocking — nothing reads the result. |

---

### 17.8 Trust note

**Everything structural in §17 is SOURCE-CODE from ONE build — 38797 — read out of a
disassembly. A disassembly says what the code *can* do, not what it does.** Where it is
load-bearing it was paired with something the archive can refute, and those pairings are
where the confidence actually comes from:

- The bloat flow is SOURCE-CODE (control flow, re-derived by an independent CFG walker with
  predecessor sets), paired with the MFT cross-tab that its stream-selector reading predicts:
  349/349 heads `(3,1)`, 349/349 partners `(1,0)`, chain depth 1, 0 partners named by the
  file-id table, 0 of 171,025 file-id entries naming a row with `alloc.flags & 3 != 3`.
- The Map Parameters read set is SOURCE-CODE, paired with a UUIDv4 test that had a 1-in-64
  chance per map and passed 349 times, plus the constructor's rect formula predicting the
  stored floats bit-exactly on 348/349 — including the one map that breaks it.
- The Terrain step table is SOURCE-CODE, paired with the tag sequences it permits and no
  others (325 + 24 = 349), the angle lattice (349/349, not just the extrema), and the
  Map-Parameters-before-Terrain join (349/349, run corpus-wide this session).
- The Path pipeline is SOURCE-CODE, paired with a tag sequence, a walk closure, four
  previously-unrun index sweeps, and 10,829,572 DAG child references decoding into four
  buckets with zero failures.
- The `+0x18`/`+0x10`/`+0x20` negatives are MEASURED — exhaustive byte scans of the whole
  image, run twice on independent tooling, agreeing on which twelve references exist.

**Where the single-build risk bites hardest:** the accepted versions (`12` for Path, `17`
for Terrain, `2` for Map Parameters), the magic constants, and every VA in this section. If
those move between builds, a custom area is per-build rather than permanent.

**§16-P10 is now partly closed, in the study's favour.** In
`vault/client/2026-04-30_b174de1f2d8d`, `s_chunkInfo` sits at VA `0x00A602B8` — located by
finding the wide `PathEngine` string and backing out 22 records of 40 bytes, with the Header
name pointer landing exactly on `base + 0x24`. All 23 rows dump with **identical names, an
identical null/non-null pattern in every one of the eight function slots, an identical cost
column, `+0x10` non-NULL on Header alone, and the same four NULL-load rows.** The layout and
population are a genuine second witness; only the addresses move. The accepted chunk
versions were **not** re-checked and remain the open half.

**Two process notes worth carrying.** A verifier shipped a
fixture-resolves-to-nothing bug in its own corpus script (`ffna_chunks` is a generator,
consumed twice) that only its printed error list caught — the same defect `CLAUDE.md` warns
about, from the verifier's side. And a linear capstone sweep from an arbitrary range start
desyncs and reports zero, which produced one nearly-filed false refutation; absence claims
should say which decoding discipline produced them.

**Reproduce.** All scripts and dumps are preserved at
**`vault/research/c0-load-handlers-2026-08-10/`** (81 entries, 2.4 MB, per-track
subdirectories, plus `tracks-verified.json` holding all five surveys with their
verifiers' 124 verdicts). They were written to a session scratchpad that deletes itself
— §15's trap again, caught this time because the synthesis flagged it. Repo tools were used unchanged with `--exe` passed explicitly on every
invocation; the previous pass's provenance misreport came from omitting it. Key addresses
for anyone continuing: `MapLoad 0x00707BB0` → map-file loader `0x00707650` → chunk parser
`0x00714150` / bloat driver `0x00707330` → stage converter `0x00713630`; archive side
`0x00470D50` → `0x00471530` → `0x00475A20` → `0x00477060` → `0x004792D0` → **stream walker
`0x0047AA40`**; download side `0x007D75E0` → `0x00834CF0` → `0x00834E40` → `0x00907F60`.

---

## 18. The reservation question — can a client write-back damage what it was not asked to write? (2026-08-10)

Five tracks, each surveyed and then re-derived by an adversarial verifier, against build
38797 and five copies of the archive. Offline throughout: no client launched, no byte
written to the repo, every archive opened `'rb'`, `datwrite.py` read and never run.

---

### 18.1 The verdict

**C2 and E3 may run against an archive copy. The client's write-back cannot exceed a
row's block reservation, and this is now established as a positive bound rather than a
failed search: in `ArchiveWriteFile` (`0x00479B90`) the byte count pushed to the disk
write at `0x00479C4B` is the identical dword handed to `SetEntry` at `0x00479C38`, and
`SetEntry` (`0x0047CD20`) frees the row's old extent and allocates a fresh one of
`roundUp(size, 512)` — there is no in-place write anywhere on the path, so there is
nothing to overrun.** All five outcomes the client can produce are bounded; the one that
happens is *relocate*. But "the archive cannot be damaged" does **not** follow, and the
mechanisms that can damage it were all found in this pass rather than assumed away:
the client's free map is derived from the MFT at open and coalesces adjacent runs, so a
wrong MFT hands the allocator live bytes; an **unconditional open-time reconcile pass
deletes any `USED|FIRST_STREAM` row absent from the file-id table**, by name, in the log;
and 88.5% of the 32,528,384 B this study calls "free space" turns out to hold live
shadow generations of the archive's own container rows. **Every one of those is something
*our* writer can create — none is something the client does unprovoked to a healthy
archive.** The precautions are in §18.12; the two that are new and mandatory are a
pre-flight that the copy passes the client's *own* open-time checks (12-byte header CRC,
block alignment, EOF bound, no overlapping reservations, the directory invariant both
ways, and bit 0 of the u32 at file offset `0x1C` clear), and a post-flight 24-byte MFT
diff, because **no checksum in the archive can detect a relocation and none is repaired
away by the client**. **If this reading is wrong, the worst case is bounded and it is
severe**: there is no slack anywhere in the map band — 348 of 349 map head rows abut the
next allocated row with zero free bytes, 349 of 349 partners likewise — so an unbounded
2× head write destroys that map's own stage-2 partner outright in 304 of 305 cases and
tramples a median of 13 and up to 638 live row payloads. That is the cost of being wrong,
and it is why the copy-only rule is not relaxed by anything here.

**§17.7's "single most important remaining safety question" is answered: no, the
write-back cannot exceed the reservation. §17.2's `ExeFile:252/253` hazard is REFUTED —
those asserts are about an in-memory scratch buffer, not an archive row, and both are
unreachable from the arithmetic of the guards immediately above them.**

---

### 18.2 The four outcomes, ranked by evidence

| # | Outcome | Verdict | Evidence |
|---|---|---|---|
| **b** | **Relocate cleanly** | **This is what happens.** | SOURCE-CODE on three tracks, re-derived independently by three verifiers: `SetEntry` reads the row's current size exactly once (`0x0047CDD4`), uses it only to free (`0x0047CDEA`), then allocates fresh (`0x0047CDFA`). Whole function decoded, 292 B, both boundaries pinned by `int3` (`0x0047CC60` / `0x0047CE44`), all eleven comparison sites accounted for, **none comparing new size against old**. Corroborated MEASURED: rows 8315/8316/8317 moved between two archive states, and `datwrite` §5/§6 observed the same live. |
| **a** | **Refuse to grow** | **REFUTED. There is no refusal path anywhere.** | `AllocSpace` (`0x00478C50`) has no error return and no out-parameter: on a miss it bumps the 64-bit end-of-file cursor at `archive+0x08` (`0x00478D17`–`0x00478D27`) and returns the *old* end. `SetEntry` does not test the allocator's return except as an assert. `Map '%s' could not be opened for writing` is effectively dead — a mode-2 (write-only) open never consults the archive at all (`0x00475A95` `test bl,3` → `0x00475AD1` `test bl,1` → `mov eax,1; ret 0xc` at `0x00475B21`). **A read-only `Gw.dat` is not caught by that branch**, so an experimenter who marks the copy read-only expecting a clean refusal gets nothing. |
| **c** | **Die on an assert** | **Real, and the store ordering is now known.** On the `ExeFile:252/253` path the asserts are unreachable *and* precede the store *and* the store is in-memory anyway, so an assert death there leaves the archive untouched. Elsewhere the ordering is the other way round. | Asserts terminate: the reporter `0x00488210`–`0x004884CC` decodes to **167 instructions, zero `ret`, zero branches leaving the range, zero indirect jumps**, ending `push 1; call 0x5BC094; int3`. Two store-before-guard sites found: `SetEntry` writes offset/size/extraBytes/crc at `0x0047CE09`–`0x0047CE18` **before** the `ExeArchive:1894` assert at `0x0047CE24`; harmless only because the process dies before any flush. Two assert deaths that would hit an experiment are named in §18.9 (items 5, 6). |
| **d** | **Write past the reservation into a neighbour** | **No path found — and the search was a bound, not an absence.** One residual, stated. | All seven read sites of the write callback were enumerated (`codescan --field 0x120 --in ExeArchive`, range `0x004787B7`–`0x0047CE29`, 8 instructions of which 1 is the store at `0x0047977C`). Three are allocation-backed and in each the byte count is the same u32 just handed to `SetEntry` — `0x00479C4B` (payload), `0x00479D43` (file-id table), `0x00479E11` (MFT). A fourth family (`0x00479455`, `0x004794E5`, `0x00479B08`, `0x0047B4DC`) writes 16 bytes at the hard-coded file offset `0x10`, which lands inside row 1 (offset 0, size 32) — the one index `SetEntry` refuses to relocate. **Residual:** the final hop is `call dword [0xC02BC8]` at `0x0047FEC4` and nothing in the image initialises that slot with a literal address, so the trace ends unresolved. If that path sector-rounded the count with a mask ≥ 1024 a write could exceed the 512-rounded reservation. Argued against, INFERRED not traced: 176,247 of 177,329 entry sizes are not multiples of 512 and 35,871 are odd, so if the archive's writes reached `NtFile:762` (`!(bytes & file->sectorSizeMask)`, `0x00484A0B`) with a nonzero mask the client could not have produced this archive without dying. |

The allocator provably never returns a run smaller than the block-rounded request — the
step that carried the whole safety argument and that the first pass never checked.
`best.size` is seeded `0xFFFFFFFF` at `0x00478CFD`; the search predicate `0x00479280`
keeps only exact fits or the smallest strictly-larger run (`0x00479297`
`cmp [ecx+8],esi; jbe`); the miss test at `0x00478D12` is exactly that sentinel.
Two caveats on it, both currently vacuous and both worth a writer knowing: the comparator
**mixes signedness** (`sub eax,esi` + `jns`/`jle` signed against `cmp [ecx+8],esi; jbe`
unsigned), and the block round-up at `0x00478CC5`–`0x00478CE6` is **32-bit with no carry
check**, so a request in `[0xFFFFFE01, 0xFFFFFFFF]` rounds to less than itself. Largest
`alloc.size` in the corpus: 6,247,580 (July), 6,209,032 (April) — 687× and 692× below the
threshold; largest free run 14,718,976 B, far below `0x7FFFFFFF`.

---

### 18.3 What the write-back actually asks for

The re-bloat asks for exactly the bytes the stage converter emitted, Huffman-compressed
by `P:\Code\Base\Compress\CmpApi.cpp`, and the archive honours it without ever asking
whether it fits. Frames, closed on both sides: loader `0x00707650` → bloat driver
`0x00707330` → stage converter `0x00713630` → `File::Write 0x00471430` → `0x00475B30`
→ `0x00477F90` (compress + frame) → `0x00479B90` (resolve row, crc) → `0x0047CD20`
(free + allocate + stamp) → `0x00478C50` / `0x0047B500`, then the raw write callback at
`archive+0x120`.

Three things a writer must not mis-model:

- **The MFT u16 at `+0x0C` is `extraBytes`, not a compression id.** MEASURED twice on
  independent readers: histogram over 177,341 rows is `{0: 38,633, 8: 138,708}`;
  `ExeArchive:1873 extraBytes <= size` violations **0 of 177,341**; and **138,708 of
  138,708** rows carrying 8 end with the dword `0x80010008` that `0x00478109` writes,
  against **0 of 38,620** controls. `archive.py`'s `compression` name is the wrong name
  for the right behaviour — 8 means "the last 8 bytes are a trailer", exactly equivalent
  to "compressed" only because `0x00477F90` emits the trailer solely on the branch where
  compression beat the raw size by ≥ 8. That equivalence is a property of the producers,
  not of the format: `SetEntry` accepts any u16 ≤ size. `datwrite.py`'s
  `compression → 0` on a stored replace is correspondingly correct.
- **The allocation is `roundUp(size, 512)`, not `size`.** Only the entry's `size` field
  is exact. The tail of the reservation is never written and keeps whatever was there.
- **The free is deferred.** `FreeSpace` (`0x0047B500`) never touches the two BTrees the
  allocator searches — it appends the span to a pending list at `[this+0x14]`
  (`0x0047B5E0`–`0x0047B643`), and nothing sits between the free and the alloc inside
  `SetEntry`. **So a row can never be re-allocated onto its own just-freed extent within
  one commit.** Rows 2 (file-id table) and 3 (the MFT) go through `SetEntry` on every
  flush (`0x00479D34`, `0x00479DE2`).

Two corrections to §17.2, both CONFIRMED adversarially. `ExeFile.cpp:252
totalBytes <= m_totalBytes` and `:253 extraBytes <= totalBytes` are about a heap file
buffer allocated at `0x00474510` (`[+0x24] = m_totalBytes`, `[+0x10] = extraBytes`,
payload inline at `+0x2C`, capacity `bytes+4`), not an archive row. Both are unreachable:
guard 1 at `0x004780F5` falls through only when `produced < requested`, guard 2 at
`0x00478100` only when `requested − produced ≥ 8`, so `edi = produced+8 ≤ requested` at
`0x00478123` and `edi ≥ 8` at `0x0047813C`. And "the store executes unconditionally on
both branches" was moot from the start, because both branches are calls into a reporter
that terminates the process, and the store writes an in-memory length.

---

### 18.4 The three mechanisms that *can* damage a row nobody wrote

Ranked by how likely an experiment is to trip them.

**(1) The open-time reconcile deletes rows.** NEW, and the most consequential single
finding in this pass. `ArchiveOpen` calls `0x0047B650` unconditionally at `0x004797B4`.
Inside it: validate the 12-byte header CRC (`0x0047B6CD`–`0x0047B6DD`, failure →
`0x0047BE38`, whose route in `ArchiveOpen` tail-jumps to `ArchiveCreate` at `0x004797EC`);
read the modification-in-progress bit (`0x0047B6FB` `test byte [esi+0x1c],2`); `LoadMft`
(`0x0047B739`); fetch the file-id stream (`0x0047B7B0`); then **the reconcile at
`0x0047B7D7` → `0x0047BE50`**, which is *not* gated by the dirty flag — its only guards
are "at least one USED row at index ≥ 16" and "the directory stream exists with
`extraBytes == 0`", both true of every healthy archive. Inside the reconcile, walking
8-byte records: `0x0047C077` logs `L"Entry %u exists in directory but not mft"` and
removes the directory record (`0x0047C08B`); `0x0047C0F6` logs
`L"Entry %u exists in mft but not directory"` and **calls the delete path at
`0x0047C110` → `0x0047A7B0`, which frees the extent (`0x0047A8AC`) and memsets the
24-byte row (`0x0047A8B8`)**. Both wide strings were dumped from the image and both exist
in the April build too.

MEASURED, and this is what makes it actionable rather than alarming: **every MFT row ≥ 16
with `alloc.flags == USED|FIRST_STREAM` has a directory record pointing at it — 0 orphans
out of 132,628 (`C:\gw`) and 132,626 (study) — and every directory record points at a
USED row — 0 violations out of 171,024 / 171,022.** On a healthy archive the pass is a
no-op. A hand-authored row that breaks the invariant would be the *first* violation in a
132,626-row corpus, and it would be logged by name and deleted. Non-first streams
(`+0x0E == 1`) are reached through `nextStream`, not the directory, and are not covered
by the reconcile's key — which is the shape of the ~44,700 USED-but-undirectoried rows,
all benign.

**(2) The free map is derived from the MFT at open, and the coalescer merges across it.**
The rebuild `0x0047B270` walks the entries in ascending offset order
(`0x0047B310`–`0x0047B42B`), stores the running cursor into `m_endOfFile`
(`0x0047B3D3`/`0x0047B3D6`), asserts each gap is whole blocks (`ExeArchive:708` at
`0x0047B3EE`), hands each gap to `FreeSpace` at `0x0047B40C`, and **flushes the pending
list into the BTrees at `0x0047B447`**. The drainer `0x00479F20` coalesces on both sides
via two exact-adjacency searches on the by-offset tree, merges sizes
(`add [ebx+8],ecx` at `0x0047A132` and `0x0047A183`) and re-inserts (`0x0047A1D3`,
`0x0047A1DF`) — the only two non-allocator callers of the tree insert `0x00472EE0`. **So
an MFT that describes extents which do not match the file hands the client a wrong free
map, and the coalescer will merge live bytes into it.** The MFT is the safety-critical
artifact, not the payloads.

*Cross-track reconciliation, and the single most useful thing this synthesis does.*
Track A's verifier traced `0x00472EE0` to exactly four rel32 call sites — the two
allocator splits and the two drainer inserts — found none at load, and concluded that the
premise "the free map is derived from the MFT at open" is **not merely unproven but
contradicted**, which would have made a freshly opened archive allocate only at EOF.
Track B's survey closes it from the other end: the load-time path reaches those same two
inserts *through the deferred route*, `0x0047B40C` → pending list → `0x0047B447` →
`0x00479F20` → `0x0047A1D3`/`0x0047A1DF`. Track C's verifier independently narrowed
`0x00479F20` to exactly two callers, `0x0047949F` and `0x0047B447`, and observed that
`0x0047B447` sits in the same routine that enqueues at `0x0047B40C`. **Three agents saw
the same four call sites; only one saw the load-time path into them.** The premise holds,
`datwrite`'s MEASURED statement of it stands, and Track A's residual hazard is confirmed
rather than dissolved. It is also a clean example of why an absence claim from a direct
rel32 sweep is weaker than it reads: the caller was there, one level of indirection away.

**(3) MFT row recycling.** `LoadMft` pushes rows with `FLAG_ENTRY_USED` clear onto a
spare stack (predicate `0x0047C420`/`0x0047C424`, push `0x0047C4C9`–`0x0047C51A`) and
`NewEntry` pops LIFO (`0x00478F35`–`0x00478F44`), highest index first. **Any row we leave
with bit 0 of `+0x0E` clear at index ≥ 16 will be handed to an unrelated new file at the
next launch, extent and all.** Corroborated MEASURED: row 35301 was consumed between two
archive states while rows 4..15 were untouched.

**The scan starts at `INDEX_FIRST_FILE = 16`, not at row 0** — `0x0047C3E3`
`cmp edi,0x10` / `0x0047C3EC` `lea eax,[ecx+0x180]` (= base + 16×24), with the constant
named in ArenaNet's own assert strings (`firstMftIndex >= INDEX_FIRST_FILE` at
`0x00478E4C`, `index < INDEX_FIRST_FILE` at `0x0047902F`). **This is the client's own
confirmation of `datplan.py`'s `FIRST_CLAIMABLE_ROW = 16`**, which the repo had inferred
from the behaviour of two archives and a comment that ends "Claiming one would look fine
right up until it did not." It would have. Rows 0..15 are structurally reserved.

One further mover the "SetEntry has exactly three call sites" framing hides: there is an
**inlined free-then-realloc outside `SetEntry`** at `0x0047A446`/`0x0047A44F`, storing
the new offset itself (`0x0047A456`/`0x0047A45B`) into an entry-shaped struct at
`esi+0x18`. `FreeSpace` has four callers and `AllocSpace` two; the extent-moving surface
is bounded by those, not by `SetEntry`'s three.

---

### 18.5 The detector

§16-P2 established that the checksum triad cannot detect a relocation. This pass confirms
why and gives the byte list. The client recomputes the entry CRC from the bytes it just
wrote (`0x00479C2A` → `SetEntry` arg 4 → `0x0047CE18`), recomputes the MFT self-CRC on
every flush (`0x00479E60`, over `mft[0x00:0x48]` continued over `mft[0x60 : 24*count]`),
and the header CRC covers 12 bytes it never touches. **A relocated row is fully
self-consistent.** A journalled byte-offset revert after a relocation writes the old
payload to an extent nothing points at, reports success, and leaves all three rules
verifying.

**TIER 0 — 48 bytes, sufficient to prove nothing happened.** `header[0x10:0x20]`
(mftOffset u64, mftSize u32, flags u32), and at `header.mftOffset`, the MFT descriptor's
u32 at `+0x04`. Read the header **first** — the MFT itself may have moved. The counter is
the part that carries the signal (measured 26,722 / 26,881 / 26,548 across three
archives, and `descriptor[+0x0C] == len(mft)/24` on all three); **`mftOffset` alone is
not a change signal** — it was byte-identical at `0xF8BEFE00` across 159 flushes in one
diffed pair. The counter is incremented (`0x00479DA9`–`0x00479DAF`, wrap-skip at
`0x00479DB2`) inside the same in-memory buffer the self-CRC then covers and that is
issued as one write, so counter and content can disagree only through a torn write.

**TIER 1 — all 24 bytes of every MFT entry, excluding rows 0, 2 and 3** (which change on
any flush and are corroboration only). Interpret per field:

| Diff shape | Meaning |
|---|---|
| `offset`/`size`/`extraBytes`/`crc` changed, `+0x0E..+0x13` identical | Same file, same row, **new extent** — the silent relocation. Journalled bytes are now orphaned. |
| `+0x0E` or `+0x0F` changed | The row index was **recycled**. Different file now; our row is gone as an identity, not just as an offset. |
| All 24 bytes zero | **Deleted** (memset at `0x0047A8B8`) — extent freed, payload left on disk, index spare-listed. |
| `+0x10` alone changed on an otherwise stable row | A sibling stream was added and the head relinked (`0x00478FF3`). Benign. |

**TIER 2 — the directory invariant, both ways** (new, and the only check that catches a
scan-triggered delete): every `USED|FIRST_STREAM` row at index ≥ 16 has a file-id record
pointing at it, and every file-id record points at a USED row. Unlike the three
checksums, this is not something the client repairs on its way past — it *enforces* it, by
deleting.

**Do not use as detectors.** The entry CRC (archive-wide invariant, 3,000 of 3,000 random
rows verify — a check that cannot fail; the "19/19 rewritten rows verify" figure is the
same invariant counted twice, and row 3 does not even satisfy the naive form of it). The
MFT self-CRC. The header CRC. A file-id lookup — MEASURED, **0 of 171,020 shared ids
changed their target row** across a diff containing 18 relocations; only four bit-31 ids
moved at all, and a comparison must mask bit 31 before concluding an id changed. And
**"row out of offset order" is worthless as a fingerprint** — 14,717 of 177,328 row-order
pairs already have a decreasing offset, including 53 of 348 map heads.

**Do not plan `--revert` on reading back the old offset.** MEASURED: of 18 rows that
relocated between two archive states, only 14 still hold their prior payload at the old
offset. Free and alloc do no I/O — a bounded scan over `0x00478000`–`0x0047D000` (66 entry
points, 6,880 instructions, restart-at-every-function-entry discipline) finds zero I/O-slot
loads and zero indirect calls inside `AllocSpace [0x478C50,0x478E30)`, `SetEntry`,
`NewEntry` or `FreeSpace [0x0047B500,0x0047B64C]` — so the old bytes survive **until
something reuses the blocks**, and in this corpus four of eighteen already had.

---

### 18.6 The empirical blast radius, independent of what the code does

The map band has no slack at all. All MEASURED on `vault/dat_study/Gw.dat`, reproduced
exactly by two independent readers.

- **349 map head rows** (`alloc.flags 3, alloc.stream 1`), each resolving through
  `Entry.counter` to a distinct live partner (`flags 1, stream 0`); 0 anomalies, all
  compression 8, no partner points onward.
- **348 of 349 heads abut the next allocated row with zero free bytes. 349 of 349
  partners likewise.** Total gap behind all 349 heads is 1,368,064 B, all of it behind a
  single row (169666).
- **For 305 of the 348 abutting heads the row immediately downstream is that map's own
  stage-2 partner.** Computed two ways ("followed by *some* partner" and "followed by its
  *own* partner") and both come to 305.

| Overrun | Heads overrunning | Median spill | Max spill | Live payloads trampled | Median / max victims | Own partner destroyed |
|---|---|---|---|---|---|---|
| 1.5× | 348 of 349 | 479,586 B | 1,046,488 B | 2,692 | 2 / 182 | fully 258, partly 47, untouched 0 (of 305) |
| 2.0× | 349 of 349 | 958,256 B | 2,093,344 B | 10,553 | 13 / 638 | fully 304, partly 1, untouched 0 |
| 3.0× | 349 of 349 | — | — | 21,415 | 32 / 702 | fully 305 |

No overrun runs past EOF at any multiplier — the worst 3× head write ends at
`0xF85C7EA4` inside a `0xFA3FDE00` file, and that test could have gone the other way
(the highest map head sits 10.6 MB from the end of a 4.2 GB file). Classes trampled at
2.0× archive-wide: `0x0003` 6,166 (58.4%), `0x0001` 1,677, `0x0203` 1,400, `0x0B01`
1,208, `0x0103` 96 — so 96 of them are *other* map heads and 1,677 are map partners.

**Growth without an overrun is affordable for one map and not for many.** At 1.5× no head
stays inside its reservation, one extends into adjacent free space, 348 must relocate; at
2× and 3× all 349 relocate. No single grown row exceeds the largest free run even at 3×
(largest need 6,281,216 B). Greedily packing *all* of them: 22 of 348 at 1.5×, 12 of 349
at 3×. Re-bloating all 349 sequentially in one session, deferred frees uncoalesced: **320
of 349 extend the file.** Extending the file is the *safe* outcome — the miss path bumps
the cursor and the write grows the file — and on the July archive the computed cursor
equals the file size exactly, so there is nothing past the last reservation to clobber.

**That last property is not a property of the design.** On
`vault/client/2026-04-30_b174de1f2d8d/Gw.dat` (4,196,497,128 B, 177,310 rows, 145 gaps)
the computed cursor is `0xF9E08800` with **4,255,464 bytes of physical file past it**, and
the file does not end on a block boundary (mod 512 = 232). The slack is exactly the
declared MFT size, and cursor + mftSize == file size to the byte: it is an abandoned
previous MFT. On an archive with trailing slack the bump path **overwrites existing
physical bytes and does not grow the file** — the opposite of what a single-corpus reading
would tell a writer.

---

### 18.7 §16-P12 reconciled — and what the number actually means

**The free-space figures reconcile exactly. They measure different things.**

| Measure | Value | What it is |
|---|---|---|
| A | **32,528,384 B in 214 runs** | Gaps between block **reservations** — space a new file can occupy |
| B | 85,261,813 B in 176,248 regions | Gaps between **payloads** |
| B − A | 52,733,429 B | `sum(alignup(size,512) − size)` over live rows — dead space *inside* rows' own reservations |

`B − A == padding` was predicted before the run and holds to the byte, on two independent
readers. All 214 A-runs are ≥ 512 B and block-aligned at both ends. **A is the right
number for "could a grown row find a home".**

Two corrections to the P12 entry itself. First, **the reconciliation already existed** —
`studies/datwrite/FINDINGS.md` carries it verbatim, with the same 52,733,429 and the same
"the real figure is 32,528,384 bytes in 214 runs". P12's "different measures, never
reconciled" described this document's failure to carry a resolution the other document
had. Second, **P12's third disputed figure is not disputed**: `datwrite`'s "176,033 of
177,329 entries sit exactly that far from their neighbour" **reproduces exactly** under
the definition the rule it evidences actually needs — rows whose next offset is exactly
`alignup(size)` away *and* whose padding is nonzero, i.e. rows that were actually rounded
up. Study copy: **176,033**. Install copy: 176,019. The identity is visible in the other
figures: reservation-abuts 177,114 minus payload-abuts 1,081 = 176,033. **Do not overwrite
that line with 177,114.** One track declared it NOT FOUND after four definitions and
proposed replacing a correct measurement; four tries is not a decoding discipline.

**MFT headroom, 14,719,024 vs 14,718,976: both correct, differing by the MFT's own 48 B
of block padding = 2 rows.** `datwrite` measured from the payload end (`0xF8FFEFD0`),
this document from the reservation end (`0xF8FFF000`); next allocated row at `0xF9E08800`.
The MFT's spare fell 216 B (9 rows) → 48 B (2 rows) across one diffed pair, matching the
7 rows created exactly.

**And now the correction that changes what all of this is for.** Reading the *bytes*
inside the runs rather than counting the gaps: **the five largest runs — 28,785,664 B,
88.5% of all "free" space — each begin with a live container generation.** Three shadow
MFTs carrying valid `Mft\x1a` headers and declaring 177,342 / 176,874 / 176,489 entries,
at `0xF8FFF000`, `0xF57D5000` and `0xF8699A00`; an **exact byte-for-byte copy** of the
live file-id table at `0xF77B6000`; a near-copy (171 bytes differ over 1,368,200) at
`0xF8290400`. 58.2% of the bytes inside the 214 runs are non-zero. Excluding
shadow-bearing runs, genuinely unclaimed space is **3,742,720 B in 209 runs, largest
953,856 B — below the median map head reservation of 961,536 B.**

That the client rotates its containers through these slots is not speculation: in
`vault/run/2026-07-29_221c13772c7a-probe/Gw.dat` the **live** MFT sits at `0xF8FFF000`,
the very run this study named as its largest free space, with `0xF8BEFE00` left as the
shadow. `vault/run-live/...` has its live MFT at `0xF8FFFE00`. **INFERRED mechanism,
which reconciles three tracks that could not each reach it alone:** deferred free means a
container's just-freed extent is unavailable to the allocation that immediately follows,
so best-fit takes the *previous* generation's extent, already coalesced into the free set
at open — an A/B alternation between two same-sized slots that looks nothing like
allocation. That is why the best-fit placement model reproduces rows 2 and 3 on the July
archive and misses on the April archive: rows 2 and 3 are not being placed by policy at
all. **NOT ESTABLISHED:** whether the alternation is strict — row 3 was observed unchanged
at `0xF8BEFE00` across 159 flushes, which a strict ping-pong does not predict for an odd
count. Worth one further pass; it does not change any safety conclusion here.

**Operational consequence, and it is concrete.** `toolkit/mapdata/datplan.py`'s
`free_runs()` sorts runs **largest first** (line 156) and `plan_insert()` takes the first
qualifying run (line 178). For any payload under 14,718,976 B, the plan therefore places a
new file at the start of the largest run — **`0xF8FFF000`, on top of the archive's MFT
rotation slot and the live MFT location in the probe copy.** `datplan` is a planner and
applies nothing, so nothing is damaged; but the plan is wrong, and C2/E3 must not follow
it. The fix is to exclude runs whose first bytes carry a container signature (`Mft\x1a`,
or a plausible file-id table), or to prefer the *smallest* qualifying run, which is also
what the client itself does.

> **FIXED 2026-08-10, `ae96f28`** — "The largest free run holds a live MFT, and the
> planner aimed every insert at it." `datplan.py` no longer aims at the rotation slot,
> and `toolkit/mapdata/test_datplan.py` (new, in `CLAUDE.md`'s suite) pins it. The
> paragraph above is kept as written because it is the finding; this note is its
> disposition. **The measurement it rests on still stands and still constrains C2/E3:**
> usable space is 3,742,720 B in 209 runs, largest 953,856 B — below the median map head
> reservation of 961,536 B — not the 32.5 MB in 214 runs that counting gaps suggests.

---

### 18.8 What would still have to be true for the archive to be damaged

Stated as preconditions so a reader can judge the residual risk. None of 1–7 is something
the client does unprovoked to a healthy archive; every one of them is something our
writer, or a careless copy, can create.

1. **Our writer leaves the MFT describing extents that do not match the file.** Then the
   free map derived at open is wrong, the coalescer merges live bytes into it, and the
   client's next allocation — of any row, not necessarily ours — is entitled to them.
   A shrinking `--replace` frees blocks; `6f07fff` made `--revert` honest about the whole
   reservation, but it does not stop the client taking the blocks.
2. **We author a `USED|FIRST_STREAM` row at index ≥ 16 with no file-id record** (or a
   record with no row). The open-time reconcile deletes it, logs it by name, and frees its
   extent. Currently 0 violations in 132,626 rows.
3. **We leave a row at index ≥ 16 with bit 0 of `+0x0E` clear.** `LoadMft` spare-lists it
   and `NewEntry` hands it out LIFO at the next launch.
4. **We place authored bytes in "free" space that holds a shadow container.** The next
   rotation writes over us, or we destroy the generation the client would have rotated
   into. See `datplan` above.
5. **We hand the client a copy with bit 0 of the u32 at file offset `0x1C` set.**
   `0x0047B470` is called on the **first write of a session** (`0x00479BB0`–`0x00479BBB`,
   `cmp [esi+0x130],0; jne; call`), and it asserts `!header.IsModificationInProgress()` at
   `0x0047B4A3`. Asserts terminate. A copy taken from a mid-write archive is a booby trap,
   and `datwrite.py` never touches `0x1C`. MEASURED: that dword reads `0x00000000` on all
   cleanly-closed archives on this machine.
6. **We leave overlapping extents.** The open-time rebuild refuses (returns 0 via
   `0x0047B45A`) and the client goes to "Repairing corrupt archive"; an overlapping *free*
   is fatal (`ExeArchive:420` at `0x004791CC`, `:441` at `0x0047913C`). Note the rebuild
   **normalises** a misaligned offset rather than refusing it (`0x0047B35C`–`0x0047B384`),
   so misalignment is *not* caught — vacuous on both corpora (0 misaligned) but not a
   guard to rely on.
7. **We touch `header[0x00:0x0C]`.** The client validates those 12 bytes on **every** open
   (`0x0047B6CD` `push 0xc` → `0x0047B6D2` → `0x0047B6DA` `cmp [esi+0xc],eax` →
   `0x0047B6DD jne 0x47be38`) and the failure route in `ArchiveOpen` tail-jumps to
   **`ArchiveCreate`** at `0x004797EC`. The risk is the archive being rebuilt, not an
   error dialog.
8. **Unresolved:** the final indirect write at `0x0047FEC4` sector-rounds its byte count
   with a mask ≥ 1024. Argued against by corpus (§18.2 row d), not traced.

**The positive result, at full coverage.** A byte-for-byte diff of the whole 4,198,489,600
bytes of `C:\gw\Gw.dat` against `vault/dat_study/Gw.dat` gives 1,022 maximal differing runs
totalling 116,311 bytes, and **zero of them fall inside the payload or the reservation of
any row whose 24-byte MFT entry is byte-identical across the two copies** (the single
apparent hit is one byte at file offset `0x18`, the header's own MFT-size field). 118 runs
lie in the MFT, 527 in the extents of the 20 changed and 7 new rows, 376 (2,109 bytes) in
space free in both. The same test against the probe copy: 73 runs, 2,344 bytes, 5 changed
rows, 0 payload hits. **Whatever wrote these archives touched nothing outside the rows
whose table entries it changed.**

One honest limit on that: **the diff has no established direction or agent.**
`vault/dat_study/Gw.dat` has `LastWriteTime` 2026-08-05 13:53:41 (earlier than its own
`CreationTime`, the signature of a timestamp-preserving `Copy-Item` per `RUNBOOK.md`) while
`C:\gw\Gw.dat` was written 2026-08-06 22:29:25 — the copy called the "before" state is the
one written last, and its row count runs the other way (177,342 → 177,335). Structurally
the study copy is the later logical state (7 rows appended, MFT grown 168 B, row 35301
revived, and study rows 177327–177331 carry `nextStream` pointers to rows that do not exist
in the install copy). So the states are real and their mutual consistency is measured;
"the client wrote 26 extents in one session" is an attribution the bytes do not carry.
Two states of an archive being mutually consistent is not by itself evidence that a write
is safe — the code reading in §18.2–18.4 is what carries that.

---

### 18.9 Corrections ledger

House style: every REFUTED and WEAKENED verdict in its corrected form. The corrections are
the most instructive part, and this pass produced 26 of them across five verifiers.

**Refuted**

| Claim as first written | Corrected form |
|---|---|
| "`ExeFile:252/253` bound the archive row's reservation and the store executes unconditionally on both branches" (§17.2) | They bound a heap file buffer's own length, both are unreachable from the guards above them, and both branches call a reporter that terminates. Not a hazard at all. |
| "A row's extent moves if and only if the client wrote that row; there is no compactor" | No compactor is right. Rows are also **destroyed by an open-time reconcile pass** (`0x0047BE50` → `0x0047A7B0`), and extents also move through an **inlined free-then-realloc** outside `SetEntry` (`0x0047A446`/`0x0047A44F`). `SetEntry`'s three call sites do not bound where extents move; `FreeSpace`'s four and `AllocSpace`'s two do. |
| "`LoadMft` pushes every row with `FLAG_ENTRY_USED` clear onto the spare stack" | It starts at `INDEX_FIRST_FILE = 16` (`0x0047C3EC` `lea eax,[ecx+0x180]`). Rows 0..15 are never recycled — which is why rows 4..15 sit USED-clear in three archives while a lineage appended 7 fresh rows rather than consuming any of them. The survey measured this and read it as confirming the opposite. |
| "The computed cursor equals the physical file size, so any bump allocation grows the file" | True of the July archive only. The April archive has 4,255,464 B of physical file past the cursor. **Trailing slack is invisible to the free list and is exactly where the bump path writes.** |
| "Best fit with a head split predicts rows 2 and 3's placement; the archive refutes worst fit" | The tail-split refutation holds on the July archive. The placement model **fails outright on the April archive** (row 2 misses, row 3 misses under all three policies), and the reason is that rows 2 and 3 are containers rotating between fixed slots, not allocator output. A one-corpus confirmation of a model that fails on the second corpus is not corroboration. |
| "The client relocated 18 rows including row 2, the file-id table — a container row, so `datwrite` §6's 'scratch rows only' is refuted" | **Row 2 moved no data.** Both extents hold byte-identical 1,368,200-byte file-id tables, in both archives independently; the whole-file diff (116,311 bytes) cannot contain a 1.37 MB relocation. It is a pointer flip between two maintained slots. `datwrite` §6 is **not** refuted by row 2. What *is* demonstrated for the free list is small rows: 8315/8316/8317 moved with different content, and 12 pre-sized `0xFF03` slots were consumed. |
| "`datwrite`'s 176,033 is not reproducible under four disciplines; the correct figure is 177,114" | 176,033 reproduces **exactly** under the fifth definition — the one the rule it evidences actually needs. The repo figure is correct; do not replace it. |
| "The MFT has room for two more rows; whether it grows in place or relocates is open" | Answered by a copy that was never opened: in the probe run copy the live MFT is at `0xF8FFF000`, relocated at unchanged size. **The client relocates rather than growing in place, into a slot that already held the previous generation.** |
| "Only `0x00478FB8` writes `+0x0E` through an entry-struct base" | `0x004790CA` (`mov dword [esi+0xc], 0x30000`, in `0x00479010`) is a third, missed by the *corrected* overlap-aware scan built to catch exactly that class. Six further `+0x0C`/`+0x10` store pairs in `0x0047C6xx`–`0x0047C9xx` remain unclassified. |

**Weakened**

| Claim as first written | Corrected form |
|---|---|
| "Best fit with a lowest-offset tie-break" | Best fit by size, yes. The lowest-offset tie-break holds **only for an exact-size match**: the out-slot copy at `0x00479297`/`0x0047929A` requires a strict improvement, so among equal-sized runs the winner is whichever the descent meets first. 33 of 66 free-run size classes have more than one member. |
| "The positioned write extends the file" | INFERRED, not traced. The trace ends at `call dword [0xC02BC8]` (`0x0047FEC4`) with nothing in the image initialising the slot. What *is* established is that the archive layer never truncates or extends. |
| "The rebuild refuses a misaligned entry offset" | It **normalises** it (`0x0047B35C`–`0x0047B384`). Vacuous on both corpora, but the refusal set is narrower than modelled. |
| "There is no path where a caller's length and the allocation's length can diverge" | True after enumerating all seven callback sites, which the survey did not do. Four of them write 16 bytes at the hard-coded file offset `0x10` with no allocation in the path — benign **by measurement** (row 1 is offset 0, size 32, the one index that cannot relocate), not by the argument given. |
| "Every one of the 349 map head rows could re-allocate out of existing free space without extending the file" | True one row at a time. Run sequentially, **320 of 349 extend the file**. And against genuinely unclaimed (shadow-free) space, only 173 of 349 fit at 1.0×, 115 at 2.0×, 83 at 3.0×. |
| "A write-only open never fails" | Confirmed through four frames; the fifth (`0x0046FC40`, handle-table registration, the value the driver actually tests) is unfollowed. Say "no failure path found in four of five frames". Also: write opens get **no multi-archive fallback** (`0x00470D7A`–`0x00470D7E`, retry loop at `0x00470E04` gated on the read bit). |
| "19 of 19 client-written rows verify their entry CRC at the new offset" | A check that cannot fail: **every** row satisfies the rule (3,000 of 3,000 random rows). The real evidence is the source-code half. And the hand-picked set excludes row 3, which does *not* satisfy the naive form — the diff-derived set scores 19/20. |
| "Rows 2 and 3 relocate as a matter of course" | Both always *change*; only row 2 was observed to *move*. Row 3 stayed at `0xF8BEFE00` across 159 flushes with a size change in between. |
| "An unwanted relocation is recoverable from the old offset" | 14 of 18 in the only corpus that can test it. Do not build `--revert` on it. |
| "The header CRC covers 12 bytes the client never writes, so it can never fail" | Right about the writer, misleading about the consequence: there is a **reader** on every open at `0x0047B6D2`, and its failure route tail-jumps to `ArchiveCreate`. |
| "The 14.7 MB run is the MFT's headroom / the largest free run" | It is the **MFT rotation region** and it holds a complete shadow MFT. Same for four of the other five largest runs. |
| "gwdat's declared-size check is circular and therefore vacuous" | One-sided, not vacuous: the loop bound forbids an over-long payload but a truncated or undecodable stream still fails the equality. Also unstated and now measured: **all 138,708 compressed rows have `size % 4 == 0`**, which is what makes `(len(data)//4)*4 − 4` land on the trailer word at all. |
| "`0x00477F90` contains no `ret` inside its stated range" | Bounds correct (653 B, `0x28D`), refutation criterion false — there is a second `ret 0x18` at `0x004781DB`. The correct criterion is a prologue or unpadded code past `0x0047821A`. |
| "The 1,368,064 B run is *probably* a vacated file-id table (INFERRED, with a null model)" | **Upgrade to MEASURED**: reading the bytes shows a near-copy of the live file-id table (171 bytes differ over 1,368,200). The null-model argument stood in for a read nobody did. An **exact** copy sits in a different run at `0xF77B6000`. |

**Smaller corrections worth carrying:** `SetEntry` is 292 B with six ExeArchive asserts
and eleven comparison sites (not 289/five/ten), and it has a **zero-size branch**
(`0x0047CDF5 test ebx,ebx; je 0x47CE01`) that skips the allocator and stamps offset 0 —
a branch on the new size, inside a claim that there is none. Five instructions sit between
the free and the alloc, not three (the material point, that none is a call, holds). The
write callback is at `archive+0x120`, not `+0x124`, and is NULL entirely on a read-only
open (selected branchlessly at `0x00476D2C` `and eax, 0x4747A0`). `CmpApi`'s verbatim
threshold is savings ≥ 4 (`0x0046B01B`) while `ExeFile`'s trailer threshold is ≥ 8
(`0x00478100`), so in a 4–7 byte band a real compressed stream is computed and discarded.
`[ebp+0x14]` inside `0x00477F90` holds the byte count only until `0x004780B5`, after which
it holds the payload pointer — anyone re-deriving the guard arithmetic will misread it.
The reporter is 167 instructions over 702 bytes (not 176/701). At flush the client
validates MFT row 0's magic (`0x00479D81 cmp [ebx],0x1a74664d`), **increments the u32 at
MFT+0x04** and stores the entry count at MFT+0x0C — `archive.py` names neither and
`datwrite.py` updates neither. `archive.py` reads neither file offset `0x14` (MFT offset
high half) nor `0x1C` (the modification flag).

---

### 18.10 Tooling defects that affect every absence claim in this repo

Three, all found this pass, all in tools whose entire purpose is preventing false absence
claims. Every past absence claim leaning on them needs re-reading.

> **FIXED 2026-08-10, `27c30a9`** — "asserts.py knew one of the idiom's three shapes, and
> --field one encoding of two" — with `c8e5884` following up on the call sites. The three
> defects below are kept as written; this note is their disposition. **The consequence
> does not go away with the fix:** every absence claim made in this repo *before* those
> commits was produced by the broken scanners, and this section's point was never the
> three bugs but that class of claim. §18.10's own example is the warning — the
> conclusion happened to hold **by luck of alignment, not by the discipline claimed**.

1. **`codescan.py --xrefs`'s data-word sweep is 4-byte-aligned only** (`if p % 4 == 0` in
   `xrefs()`), so three of four alignments are invisible. Demonstrated inside this very
   path: the allocator's comparator `0x00479280` is pushed as a literal at `0x00478CF5`
   and `--xrefs` reports "0 direct rel32 reference(s), 0 data word(s)". An unaligned
   all-sections re-sweep confirms `0x00472EE0` genuinely has zero occurrences at any
   alignment — so the conclusion held, **by luck of alignment, not by the discipline
   claimed**.
2. **`codescan.py --field` matches only the disp32 encoding** and requires the instruction
   to *end* on those four bytes. `--field 0xE --in ExeArchive` reports "0 instructions,
   0 stores" while `0x00478FB8 mov byte [edi+0xe], al` sits in that exact range. Anything
   under `0x80`, or any store wider than its displacement's field, is invisible.
3. **`asserts.py` silently omits sites that share a tail block.** `ExeArchive:1905/1906`
   are compiled in at `0x0047901E`/`0x0047902F` and `0x0047CE63`/`0x0047CE74` but do not
   appear in `--file ExeArchive --unique`, because the push/mov/mov/call pattern is broken
   by a `jmp` to a shared epilogue. **"96 sites, 60 lines" is a floor, not a census.**

One positive: **the C0 displacement-field defect did not recur.** Across all five surveys
and five verifications, every cited VA re-syncs cleanly under an independent decode. The
one apparent exception is a convention difference — `asserts.py` reports a site at its
`mov edx,<file>`, one instruction after the compare a survey cites.

---

### 18.11 Rungs C2 and E3, respecified

Both remain **copy-only**, in a run directory, never `vault/dat_study/Gw.dat`, never
`C:\gw`. What this pass adds is a pre-flight and a post-flight, and a correction to *why*
the copy rule exists.

**Pre-flight on the copy, before any launch (all offline, all cheap):**

- **bit 0 of the u32 at file offset `0x1C` is clear.** Otherwise `0x0047B4A3` asserts on
  the client's first write and the process dies with no useful message. A copy taken from a
  mid-write archive is a booby trap and `datwrite.py` cannot see it.
- **`header[0x00:0x0C]` untouched**, CRC-32 over exactly those 12 bytes matching
  `header[0x0C]`. The client validates this on every open and the failure route reaches
  `ArchiveCreate`.
- **Every extent 512-aligned, inside EOF, and non-overlapping.** The client walks all of
  this at open (`0x0047C390`–`0x0047C3D9`) and the rebuild refuses on an overlap.
- **The directory invariant, both ways** (§18.5 Tier 2). Any authored row must be either a
  `USED|FIRST_STREAM` row *with* a file-id record, or a non-first stream reached through
  `nextStream`. A `USED|FIRST_STREAM` row with no record is deleted at the next open.
- **No authored row at index < 16**, and **no row at index ≥ 16 left with `USED` clear**.
- **Do not place authored bytes into "free" space by offset.** If a plan is needed, it must
  exclude container-shadow-bearing runs; `datplan.py`'s largest-first placement currently
  targets `0xF8FFF000`, the MFT rotation slot. Usable space is 3,742,720 B in 209 runs,
  largest 953,856 B — not 32.5 MB in 214.
- Snapshot **Tier 0 (48 B) + Tier 1 (the full 24-byte MFT) + Tier 2 (the invariant)**.

**Post-flight after every arm, before drawing any conclusion:** re-read the header first
(the MFT may have moved), then the descriptor counter at `header.mftOffset + 0x04`, then
diff all 24 bytes of every entry and interpret per §18.5's table, then re-run the
invariant. **"Loaded, but the MFT row changed" remains a first-class outcome**, and it is
now four distinguishable outcomes rather than one.

**C2 specifically.** The §16-P2 relocation hazard is confirmed as a mechanism and is
rarer than it read — a container was observed re-allocated in place 159 consecutive times
— but arm 3's expected re-bloat *will* free the row's extent and take a fresh one, and the
deferred free guarantees it cannot land back on the old extent within the same commit. Do
not expect `--revert`'s byte offsets to remain meaningful after arm 3, and do not expect to
read the old payload back from the vacated offset (14 of 18 in the corpus). The
full-reservation journal from `6f07fff` is what makes the revert honest; it does not stop
the client taking the blocks.

**E3 specifically.** Its stated reason for requiring an archive copy — "the write-back
grows the payload ~2× and `ExeFile:252/253`'s bounds are asserts whose store executes
unconditionally on both branches" — is **wrong and should be replaced**. Those asserts are
about a heap buffer and are unreachable; the ~2× growth is handled by relocation and
cannot overrun anything. The correct reasons to require a copy are: the client's free map
is derived from the MFT at open and coalesces; the open-time reconcile deletes
undirectoried rows; the client relocates the row and every offset we recorded goes stale;
and the client may append at EOF and grow the file. The growth itself is affordable — no
single grown map row exceeds the largest free run even at 3× — but best fit takes the
*smallest* qualifying run, which for a ~2 MB payload means one of the five largest runs,
all of which currently hold stale container generations. **That is the client legitimately
reusing its own free space and is not a hazard to us; it is a hazard only if *we* have put
something there first.**

---

### 18.12 Open questions

| Question | What would answer it |
|---|---|
| **What does `call dword [0xC02BC8]` (`0x0047FEC4`) do with the byte count?** The last hop of every archive write, and nothing in the image initialises that slot with a literal address. If it sector-rounds with a mask ≥ 1024 the reservation bound has a hole. | Runtime, or finding the initialiser. The corpus argument (176,247 of 177,329 sizes not multiples of 512, 35,871 odd) is strong but is INFERRED. |
| **Is the container ping-pong strict?** Five copies show the MFT and file-id table at a small set of recurring slots with complete prior generations in the alternates, and deferred-free + best-fit predicts alternation — but row 3 was unchanged across 159 flushes. | Diff the run copies pairwise against the install copy; the probe copy already carries the MFT in the alternate slot. |
| **Does `0x0046AEB0` guarantee `produced <= srcLen`?** It takes **no output-capacity argument** — its overlap asserts at `0x0046AEC5`/`0x0046AEE6` use `srcLen` for both buffers — so the caller's `bytes+4` payload capacity is the only guarantee. | Read the compressor. A violation is a heap overrun inside the client's own process, not archive damage; it does not touch §18.2. |
| **What triggers the delete path's other three callers?** `0x0047A7B0` has four (`0x0047955D`, `0x00479843`, `0x0047BD89`, `0x0047C110`); only the reconcile one is traced. | One disassembly each. It decides whether an authored row can be deleted on a path other than the invariant violation. |
| **Can `extraBytes` ever be a value other than 0 or 8?** `SetEntry` accepts any u16 ≤ size; `0x00477F90` only ever produces 0 or 8; the download side (`0x007D75E0` / FcArchive, `0x00907F60`) was not read, nor was the fourth caller `0x007D9FE7`. | Read the download writer. `archive.py` raises rather than mis-decodes, but a writer should know the field's range. |
| **Do rows 177320–177331's `alloc.stream 0xFF → 0x00` transitions really imply delete-and-recreate within one session?** The only `+0x0F` writers found require the row to have been spare-listed. | Bounded — the store scan covered `0x00478000`–`0x0047D000` only, and an entry-pointer-holding writer outside that range is not excluded. |
| **What does `alloc.stream 0xFF` mean?** Seven such rows in the study copy, nineteen in the install copy, preferentially consumed, and no immediate `0xFF` is compared anywhere in the scanned range. | Reads like a pre-sized scratch pool. NOT FOUND. |
| **What sets bit 31 of a file id?** Two bit-31 ids had the bit cleared and were re-homed; two were released to `(0,0)`; no plain id was ever re-pointed. `archive.py`'s "why the bit is set is NOT ESTABLISHED" stands, but **"a bit-31 id is not stable across sessions" is now MEASURED** and belongs in that docstring. | — |
| **Does `0x0047B7E0` (the 1 MB-buffered scan with progress callbacks, `ExeArchive:2592/2615/2665/2679/2718`) run on every open or only on repair?** It is gated by the dirty flag `edi`, unlike the reconcile — but if it is a self-repair it could mask a bad `datwrite` rather than surface it. | Follow the `edi` gate at `0x0047B7E2`. |

---

### 18.13 Trust note and reproduce

**Everything structural in §18 is SOURCE-CODE read from a disassembly of ONE build,
38797. A disassembly says what the code *can* do, not what it does.** The one thing that
is two builds is the *source version*: `asserts.py --file ExeArchive --unique` returns 96
sites over 60 distinct source lines on both vaulted stock clients, with the two line-number
sets identical and only the addresses moved — so the write path is not build-fragile at the
source level, and **every VA in this section is.** Both reconcile log strings exist in both
builds.

Where the reading is load-bearing it is paired with something the archive could have
refuted, and that is where the confidence comes from: the `extraBytes` reading against a
two-sided corpus sweep (138,708/138,708 with the sentinel, 0/38,620 controls, zero
exceptions in either direction, on two independent readers); `IsFixedLocation == (mftIndex
== 1)` against the rival predicate (rows 2 and 3 have nonzero crc *and* nonzero offset, and
exactly one of 177,329 USED rows has crc 0); the free-space reconciliation against a
predicted identity; the reconcile pass against an invariant that could have gone red on any
of 132,626 rows; and the modification-in-progress bit against a predicted file offset that
reads 0 on every cleanly-closed archive.

Where it is not paired, it is labelled: the container ping-pong mechanism is INFERRED, the
sector-mask argument is INFERRED, and the last hop of the write is NOT FOUND.

**Scope of the archive evidence.** Five copies were read: `vault/dat_study/Gw.dat`
(4,198,489,600 B, 177,342 MFT count), `C:\gw\Gw.dat` (read-only, same size, 177,335),
`vault/client/2026-04-30_b174de1f2d8d/Gw.dat` (4,196,497,128 B, 177,310),
`vault/run/2026-07-29_221c13772c7a-probe/Gw.dat` (177,335, MFT at `0xF8FFF000`) and
`vault/run-live/2026-07-29_221c13772c7a/Gw.dat` (177,476, MFT at `0xF8FFFE00`, free space
27,571,712 B in 135 runs). **Two headline claims in this pass were properties of one
archive and were caught only by the second** — the trailing-slack claim and the placement
model. A one-archive sweep is a spot check with a large n.

**Operational note, recorded because it happened during a pass that was supposed to be
offline and nothing here launched anything.**
`vault/run/2026-07-29_221c13772c7a/Gw.dat` became exclusively locked partway through the
session — readable at the start, `PermissionError` minutes later, `LastWriteTime` that
evening. A Guild Wars client took the archive while this pass was running. The copy was
skipped rather than worked around.

**Reproduce.** Every `codescan.py` and `asserts.py` invocation passed `--exe` explicitly;
omitting it is how a previous pass misreported provenance. Every archive was opened
`'rb'`; `datwrite.py` and `datplan.py` were read as code and never run; no client was
launched or patched; nothing was written to the repo. Scripts and dumps are preserved at
**`vault/research/reservation-2026-08-10/`** (66 entries, 9.1 MB, plus
`tracks-verified.json` holding all five surveys with their verifiers' verdicts), alongside
`c0-load-handlers-2026-08-10/` and `customarea-2026-08-10/`. They were written to a session
scratchpad that self-deletes — **§15's trap again**, caught because the synthesis flagged it.

Key addresses for whoever continues (build 38797):

```
write entry      0x00477F90   (sole caller 0x00475B30; four callers of that)
archive write    0x00479B90   (crc 0x004716A0; disk write 0x00479C5D via archive+0x120)
SetEntry         0x0047CD20   (free 0x0047B500, alloc 0x00478C50; three callers)
allocator        0x00478C50   (search 0x00472EB0, comparator 0x00479280, EOF bump 0x00478D17)
free (deferred)  0x0047B500   -> pending list [this+0x14]
drain/coalesce   0x00479F20   (callers 0x0047949F, 0x0047B447; inserts 0x0047A1D3/0x0047A1DF)
rebuild at open  0x0047B270   (walk 0x0047B310-0x0047B42B, gap->free 0x0047B40C, flush 0x0047B447)
open pass        0x0047B650   (hdr crc 0x0047B6D2, LoadMft 0x0047C160, reconcile 0x0047B7D7)
reconcile        0x0047BE50   (delete 0x0047C110, dir-remove 0x0047C08B)
delete row       0x0047A7B0   (free 0x0047A8AC, memset 0x0047A8B8, spare push 0x0047A91C)
NewEntry         0x00478E30   (flags +0x0E at 0x00478FB8, stream +0x0F at 0x00478FBE)
flush            0x00479C90   (row 2 at 0x00479D34, row 3 at 0x00479DE2, self-crc 0x00479E60)
BeginModification 0x0047B470  (file offset 0x1C bit 0; called on first write from 0x00479BB0)
assert reporter  0x00488210   (167 instructions, zero rets, terminates)
```

---

## 19. Rung B1 — the terrain round-trip, and where the Bloated streams come from (2026-08-11)

The first rung in this arc that produced code, and the first claim it could have failed.
Three modules, three tests, two adversarial verifications, two digs. Everything offline:
no client launched, no archive written, every open `'rb'`.

### 19.1 B1 landed: 349 of 349

`python toolkit/mapdata/test_terrain.py --all` decodes every retail terrain chunk in
`vault/dat_study/Gw.dat` to typed values, **drops the original**, re-encodes, and gets the
archive's bytes back. 58 checks, 440 s, and the count is the headline: **349 of 349
byte-identical**, both tag sequences (325 nine-record, 24 ten-record), 59,051/59,051 tag-7
blocks walked, 60,468,224/60,468,224 height samples finite and exact integers.

**What it proves versus what it carries, because the difference is the whole point.** The
verifier classified every byte of four real chunks rather than trusting the docstring:
**1,824,846 of 3,535,277 B (51.6%) are reconstructed from typed values; 1,710,431 B
(48.4%) are carried through.** Reconstructed: the 8-byte header, every `{u8 tag, u32 size}`
record header with its size re-derived rather than stored, tag 0's seven fields, all
heights, the tag 4/5 count bytes, tag 7's per-block `k`, tag 3'. Carried: tag 2 tiles,
tag 3 bits, tag 9 shade, both table bodies, tag 7 payloads and tails. **A round-trip over
carried bytes proves framing, not meaning**, and this document says so rather than
rounding 349/349 up to "we understand the terrain chunk".

`trnshadow.py` then moved the largest carried block out of that category — tag 7 now
decodes and re-encodes from the bitmap alone, 59,051/59,051 — but **it is not yet wired
into `terrain.py`**, so 48.4% is what today's 349/349 actually rests on. Wiring it in is
the cheapest next improvement and drops the carried fraction toward ~20%.

### 19.2 What the verifiers broke

Both builds shipped a check that could not fail. That is two for two, in a pass whose
brief named that defect explicitly — the failure mode is not rare and is not going away.

**`mapchunks` — OVERSTATED, four major defects, all fixed.**

1. **The headline cache check could not fail in the mode the test normally runs.** With a
   warm cache three sections all read the cache and nothing re-ran `index_file`. Sabotage
   — every chunk offset `+4` — produced `ALL CHECKS PASSED (64 checks)`, exit 0, including
   `[PASS] the cached index equals a fresh ffna_chunks walk`. The same sabotage now
   produces 3 FAILs.
2. **The dependency-alias claim was checked per chunk, not per record**, excusing every
   byte difference in any chunk holding one aliased pair — **84 of 2,252 chunks excused
   wholesale.** The claim was true; the test did not establish it.
3. **The rule asked the module under test whether the module was right.**
   `is_canonical_pair` was defined through the same function that produced the re-encode,
   so a consistent encoder error cancels. The test now states `canonical = a < 0xFF00`
   itself.
4. **The derivation-register gate was skipped** — the module took GWMB's Dependencies
   record and pair-to-file-id formula, its own docstring said UPSTREAM, and there was no
   §6.1 row and no `THIRD-PARTY-NOTICES.md` entry. **The `gwdat.py` shape exactly**, in
   the same session that added a register row for terrain to avoid precisely this. Fixed
   in both files.

**`terrain` — SOUND, one major defect fixed.** The "349 of 349" rested on
`ok == len(picks)` over a row filter **whose size nothing checked**. `CORPUS_MAPS = 349`
was declared with a MEASURED comment and used by **zero** checks; a wrong `MAP_FLAGS`
would have selected three rows and printed "3 of 3", green. That is `test_codec.py`'s
glob-matching-nothing failure at one remove, in the rung built to be falsifiable. The
population is now asserted and an empty sample cannot pass.

Four independent sabotages (cell pitch, shadow-tail stride, angle recomputation, swapped
tag-0 fields) all went red, and the orchestrator reproduced one: pitch 96.0 -> 95.0 gives
4 failed checks, restore gives green.

### 19.3 Corrections — the document was wrong here

| § | Was | Now |
|---|---|---|
| §4, §17.4 | terrain angles "land exactly on that lattice" | **Within 1 ULP, not bit-exact.** `float32(b*90pi/45720)` reproduces 39/55 patterns and 286/349 maps; `float32(1.5707963705062866*b/254)` reproduces 53/55 and 347/349. **Consequence for an author: store the decoded float32 verbatim, never recompute from `b`.** |
| §17.4 | "54 distinct" angle values | **55** — §4 already said 55; §17.4 was the wrong one |
| §4 | "the last three tag-3' floats are byte-identical across different maps" | **Refuted.** 24 records, 22 distinct 4-tuples, 20 distinct last-three |
| §4 | tag 3 all-zero in "~155 maps" | **168 of 349** |
| §4 | "3,151 records" (recon) | **3,165** = 325x9 + 24x10 |
| §3 | the dependency pair encoding, decode only | **It aliases and is not one-to-one.** The radix is `0xFF00`, so `id0 >= 0xFF00` names the same file as `(id0-0xFF00, id1+1)` — and **ArenaNet's own writer uses both forms: 85 entries in 84 of 2,252 chunks across 76 maps.** A byte-preserving writer must encode from the stored triples, not from ids. No upstream records this. |

### 19.4 Dig A — the Bloated streams are generated locally, on the download path

**Settled from the write path, not from comparing archives** — and the archive comparison
is reported as the near-null it was. `FcArchive`'s download-commit `0x007D75E0` is the only
caller of the `DnBloat` dispatcher; for `ffna` type 3 the map handler receives a **NULL**
output array, so FcArchive writes the downloaded bytes **verbatim into stream 0** while the
same handler runs the stage converter with `mapStage = 2` and writes stream 1.

The falsification test passed: **the stage converter has exactly one caller image-wide on
both builds and is never invoked with stage 1 — nothing in the client can produce a
Stripped stream.** Archive checks it was asked to refute: stream 1 carries stage-2 chunk
ids 8,047/8,047 over 349/349; stream 0 carries stage-1 ids 8,047/8,047 over 349/349; head
row index < partner row index 348/349 across all seven copies, and the one exception is
itself evidence — map `0x46547`, a Bloated row re-created with its Stripped partner
unmoved, the corpus's only Bloated-only rewrite, and the source of §18.6's 1,368,064 B gap.

**The null kept:** cross-archive comparison was nearly powerless. All seven vault copies
are one install lineage, 349/349 map pairs are byte-identical across all 21 pairings but
one, and only 307 of 170,695 file ids changed across a three-month build gap — **zero
maps**. On archive comparison alone this dig reports NOT FOUND.

**What this changes, and the caveat that limits it.** Because the client compiles Bloated
itself, an authoring tool needs to emit only a **Stripped** map: Sight (9-byte stub to
29.9 MB) and Path (19+8n boundary polygon to 156 MB of trapezoid mesh) never need to be
authored. That is the largest practical result of the session. **But we do not control
downloads**, so the only trigger we can reach is still the failed-load re-bloat — rung E3,
which needs an archive write and a launch. And it stays **UNVERIFIED** whether re-bloating
a Stripped stream today reproduces bytes stored by a build we did not download under; that
is D1's criterion, and until it is measured, "the client generates it" does not yet mean
"the client will generate ours."

### 19.5 Dig B — three terrain records solved, two refused

- **tag 7 = a shadow bitmap. SOLVED.** 272x272 one-bit samples per 32x32 tile (8 per cell,
  one-cell skirt), RLE **per row, each row restarting at 0**, `0xFF` = "+254 and continue"
  (SOURCE-CODE, `0x00761210`, assert `TrnCodecShadow:245 run`). The 128-byte tail is 1024
  bits MSB-first, set if and only if all 100 samples of the **10x10** window are set.
  **59,051/59,051 blocks re-encode byte-identically; 60,468,224/60,468,224 tail bits
  reproduced.** Controls fail as required — 8x8 misses 1,562,798 bits, 12x12 misses
  611,928. A set bit means IN SHADOW, checked against tag 9 (186.0 vs 236.6 mean shade)
  rather than assumed. **NOT established: what casts the shadow.** A terrain-only raycast
  predicts the flag only weakly (41.9% against a 33.6% base rate), consistent with props
  baked in, but INFERRED.
- **tag 9 = a baked directional lightmap. SOLVED.** `255*max(0, N.L)` from the tag-1
  heightfield gives **median Pearson r = 0.887 over 345 maps**; the best-fit elevation
  tracks tag 0 `+0x0C` with Spearman **0.9352**, and +x-with-zero-y is the argmax on
  **343 of 345** — matching the client's own `TrnTexIntensity:342 lightDir.y == 0`.
  **So tag 0's angle is the sun elevation.** The transfer curve is *not* settled (348/349
  saturate at 255), so `terrain.py` stores bytes and invents no formula.
- **tag 4 = `tileTypes` (`TrnTex:218`), shape solved, meaning NOT FOUND.** `n <= 63` is
  `MAP_TILE_MAX_COUNT`, SOURCE-CODE. It is **not a permutation — it is a staircase**:
  `A[0] == 0`, every step 0 or +1, **349/349**, and `max(A) < len(terrain deps)` 349/349.
- **tag 5 = a property of the texture, its 7 bits NOT FOUND.** Slot `i` pairs with the
  map's `i`-th Terrain Dependencies file and the value is a function of that file on
  **17,083 of 17,089 slot uses across 1,648 files**, against a shuffle null of about
  6,180. Bit 0 is set 17,089/17,089 and bit 7 in 0 — which is why the client's `& 0x7F` is
  unexercised.
- **tag 3 — layout tightened, meaning NOT FOUND, four hypotheses killed and recorded.**
  The de-tiler at `0x0074AC50` copies 32 iterations of 8 bytes striding `dx/4`, so a byte
  covers four consecutive **x** cells of one row — **"one byte per 2x2 block" is refuted
  from the client's own code.** All-zero on 168/349; where present, a median 0.10% of bytes
  are non-zero and the three values are near-uniform (840/805/816), i.e. a random 3-way
  choice rather than a flag. It does **not** mark steep ground (0.9635 vs 0.9627), is not a
  tile-type property, not the map edge, does not follow height, and does **not** track the
  tag-7 shadow (lift 1.20 / 0.78 / 0.59, inconsistent in sign). Whatever selects it is not
  in this chunk.
- **A new cross-chunk law.** The 24 ten-record maps are **exactly** the 24 whose terrain
  dependency list is one longer than `n` (24/24 both ways), and the extra file is the
  **first** entry — realigning slot `i` to dependency `i+1` there makes tag 5's texture
  function exact, **880/880**.

### 19.6 Open questions closed

- **§17.7, "what is `Bloating mismatch %#x type %u` comparing?"** — after a successful
  bloat, if `newData.Bytes() != 0` it requires `newData.Bytes() >= inputLen` and
  `memcmp(newData.Data(), input, inputLen) == 0`. Bloat is a **verbatim extension** of its
  input for ATEX/ATTX and types 4-5. **It never runs for maps** — the map handler gets a
  NULL output array.
- **§18.12, "what does `alloc.stream 0xFF` mean?"** — `0x007D9FE7` passes literal `0xFF`
  as the stream argument to both `ArchiveFilePrepare` and `ArchiveWriteFile`, confirming
  arg0 is the stream index.
- **§18.6's 1,368,064 B gap** behind row 169666 — the abandoned Bloated extent of map
  `0x46547`.

### 19.7 What is next

Cheap and offline: wire `trnshadow` into `terrain.py` so tag 7 stops being carried; then
B2 (the whole-file round-trip) and B3 (the Blender importer), which are now unblocked and
whose hardest conventions §17.4 already settled.

Everything past that needs the two gates this arc has deliberately not crossed — **an
archive write and a client launch**. Rung C2 remains specified in §18.11 with its
pre-flight and post-flight; E3 is the one that would prove the client compiles a navmesh
we did not author.

**Reproduce.** `python toolkit/mapdata/test_terrain.py --all` (440 s), plus
`test_mapchunks.py` and `test_trnshadow.py`. Full suite at the time of this section:
**40 of 40 green**, the list derived from `CLAUDE.md` rather than hand-maintained.

### 19.8 trnshadow wired in — tag 7 is decoded, not carried (2026-08-11)

§19.1 reported the round-trip resting on **48.4% carried bytes**, and named wiring
`trnshadow` into `terrain.py` as the cheapest way to shrink that. Done.

**Carried is now 28.9%**, measured over Kamadan, Pre-Searing and row 46196 (3,119,778 B
of chunk, 901,092 B carried). What remains carried is tag 2's tile indices, tag 3's bits,
tag 9's shade bytes and the two table bodies — every one of them a record whose *meaning*
§19.5 could not settle, which is the right place for the line to sit. **The 349/349
byte-identical round-trip still holds** with tag 7 reconstructed rather than copied.

`ShadowBlock`'s authoritative member is now `rows`, a 272×272 bitmap; `payload` and `tail`
are properties that regenerate from it, so **neither stored field survives the decode**.

**The decoder refuses a block whose stored tail its own bitmap disproves.** That is the
point of the exercise rather than a nicety: keeping the stored tail would re-encode
byte-identically and hide the disagreement — a round-trip comparing a value with itself,
which is the trap §19.2 caught twice already.

Three things worth recording because they were not free:

- **A circular import.** `trnshadow` imported `Terrain` at module scope, so `terrain`
  importing `trnshadow` failed at load. Fixed by making the low-level module standalone:
  it now declares `CHUNK_SIZE` and `SHADOW_TAIL` itself and imports `Terrain` inside its
  CLI. The dependency runs one way, low to high.
- **`encode_rows` was 13× too slow to leave alone.** It walked all 73,984 bits of every
  block — 5.21 ms on a real map, about 6 minutes of pure encoding across 59,051 blocks,
  which is how a whole-archive check becomes one nobody runs. It now steps transition to
  transition (`rest & -rest` isolates the next one), **0.39 ms/block, byte-identical to
  the sample loop on 391 blocks and to the archive on the same 391.** The full corpus run
  went from 440 s to 559 s rather than to ~800 s.
- **The refusal shipped broken and a test now covers it.** The first version called
  `len()` on `tail_disagreement`'s return, which is a count, turning a clean refusal into
  a `TypeError` — an error path nothing exercised. The new check asserts the exception
  **type**, and deliberately does not use the file's `raises()` helper, because that
  helper swallows every exception and would have scored the `TypeError` as a pass.
  Sabotaged (`if False and ...`), the check goes red; restored, green.

**A pleasant confirmation nobody set out to make.** `Terrain.blank()` used to carry the
caveat NOT CLIENT-LOADABLE because its tag-7 blocks had a zero-length payload while
`k == 0` occurs in 0 of 59,051 retail blocks. Its blocks now hold a real all-clear bitmap,
which the run coder emits as 272 rows of `0xFF 0x12` — **`k == 544`, and 544 is exactly
the corpus minimum.** An all-clear tile is what a flat unshadowed grid should have, and
retail's smallest block agrees with it to the byte. That caveat is gone; `blank()` is
still not a loadable *map*, but its terrain chunk is no longer the reason.

### 19.9 Rung B2 — the whole-file codec, and the number it makes impossible to hide (2026-08-11)

`toolkit/mapdata/mapfile.py` decodes a decompressed `ffna` map payload into a typed
container — magic, type byte, and an ordered list of chunks — and re-encodes it.

**349 of 349 Bloated and 349 of 349 Stripped, byte-identical.** 8,047 chunks per stage,
964,291,436 bytes, 0 refusals, 0 misdispatched chunks. Bloated 604 s, Stripped 149 s.
This is the first time anything in the toolkit has **emitted** an FFNA container;
`archive.ffna_chunks` only ever walked one.

**The count is worth its exit code only because of what sits under it.** A whole-file
round-trip is the most fakeable check in this arc: a codec that stores each chunk's `size`
and writes it back round-trips every file it can walk — including all seventeen kinds it
carries opaquely — and would print 698 of 698 while being a memcpy with extra steps.

Three things make it real:

- **`Chunk` has no size attribute and `MapFile` has no size list.** Verified structurally
  by the orchestrator: the slots are `chunk_id, form, note, value` and `magic, ffna_type,
  chunks`. There is nothing to replay. `encode()` produces the payload first and writes
  `len(payload)` second.
- **The control mutates a decoded chunk IN PLACE** until its payload changes length, and
  requires the emitted size field to move with it. Reproduced independently against
  ArenaNet's own bytes on row 46196: shortening chunk 1 by four bytes moved its table entry
  41 → 37, the file shrank by exactly 4, and the table still closed to the byte.
- **The builder found a defect in its own control**, which is the instructive part. The
  first version *replaced* `mf.chunks[idx]` with a freshly built `Chunk` — so a sabotaged
  encoder that stamps a stored size at decode time carried no stale size into the
  replacement and **passed the entire section, 22 checks to 0**. Mutating the object the
  decoder built is the whole design. Four sabotages now go red: a per-`Chunk` stored size
  (3 red), a per-`MapFile` stored size list (3 red), a dict-keyed encoder that loses file
  order (6 red), and a tolerant chunk walk (2 red).

**The byte census, which the test prints and asserts rather than leaving to a docstring:**

| | Bloated (723,597,618 B) | Stripped (240,693,818 B) |
|---|---|---|
| container framing | 66,121 B (0.01%) | 66,121 B (0.03%) |
| Terrain, reconstructed | 335,105,844 B (46.31%) | 0 |
| Terrain, carried inside `terrain.py` | 136,087,682 B (18.81%) | 0 |
| Dependencies | 817,000 B (0.11%) | 817,000 B (0.34%) |
| other chunks, carried | 251,520,971 B (34.76%) | 239,810,697 B (99.63%) |

**Corpus-wide: 34.92% reconstructed, 65.07% carried.** The test asserts that sentence as a
check — *"MOST OF THE CORPUS BY WEIGHT IS CARRIED, and this says so"* — because a 698-of-698
headline with no such line beside it would read as far more understanding than we have.

**The Stripped stream is 99.63% bytes this module does not read**, and that is the honest
reading of its 349/349: it establishes the container framing and nothing about content.
Stripped terrain is bit-packed through `TrnCodecHeight` and is still undecoded; the pathing
chunk is 156 MB corpus-wide and `pathmap.py` has no encoder, so both are carried.

**Two totals land that our decoder cannot force**, which is the kind of corroboration this
arc keeps looking for. Terrain's 335,105,844 + 136,087,682 = 471.2 MB is exactly §3's
Bloated Terrain figure, measured in a different pass by a different walker. And the
Dependencies total is exactly `134,290 × 6 + 2,252 × 5 = 817,000` — §3's reference and
chunk counts, arrived at from the other side.

**The Stripped carry is a decision, not a fall-through**, and is checked as one: the
Stripped terrain chunk `0x10000002` comes back carried in 349/349, **0 of 349 Bloated files
carry it**, and `Terrain.from_chunk` refuses that id outright. Dependencies are encoded from
the stored `(id0, id1, pad)` triples, so the 85 aliased entries across 76 maps survive —
encoding from file ids would have silently rewritten them into canonical form.

Sections 1–2 (25 checks) build a whole map file from nothing and need no vault; a
vault-less run correctly fails on the floor rather than going green.

### 19.10 Rung B3 — a retail map in Blender, the right way up (2026-08-11)

`toolkit/mapdata/mapexport.py` writes a map's terrain to a neutral interchange —
`<name>.gwmap.json` plus de-tiled `.heights.f32` / `.tiles.u8` / `.shade.u8` sidecars, each
sha256'd in the manifest — and `tools/blender/import_gwmap.py` builds it as a Blender mesh.
The JSON carries its own `conventions` block, so a file states the rules it was written
under rather than relying on a reader to remember them.

**Blender 5.1.1 ran, headless, on Pre-Searing (row 7982, 416×512 cells):
213,921 vertices, 212,992 quads, every face 4-sided.** Bounding box
`[-18432, -24576, -4966] .. [21504, 24576, 799]` — x/y equal the Map Parameters chunk's
rect **to the bit**, z equal to the stored heights' min/max. Reproduced by the orchestrator
from a fresh export.

`tools/` is a new directory and the **only** place `bpy` is permitted; `CLAUDE.md`'s
stdlib rule binds `toolkit/`, and `test_blenderimport.py` lives under `toolkit/`, never
imports the importer, and drives Blender as a subprocess.

#### The orientation is established, not assumed

This rung's whole risk is a confidently upside-down mesh, and our exporter agreeing with
our importer would prove nothing. The oracle is a **different chunk**: sample the exported
height field at each prop's `(x, y)` from `0x20000004` and compare with that prop's stored
`z`. Prediction stated first, then measured — and re-measured by the orchestrator with an
independent prop reader and independent indexing, touching no export code:

| layout | frac \|dz\| < 100 | median \|dz\| | outside grid |
|---|---|---|---|
| **baseline** | **0.7338** | **29.96** | 0 |
| y-flip | 0.0775 | 667.20 | 0 |
| x-flip | 0.1389 | 571.53 | 0 |

Both controls collapse, on identical sample sizes (864 props, 0 outside under every
layout, so no control loses on population). The independent walk also closed the prop array
exactly — 43,490 of 43,490 declared bytes — which re-confirms §5's record layout from
outside the module that uses it.

Two results nobody arranged:

- **Kamadan scores 0.3043, well below §4's 0.504 corpus median, and is reported at its real
  value.** It is a dense city whose props sit on roofs — exactly where a single-valued
  heightmap has nothing to say (§2's standing negative). Its controls collapse just as hard,
  which is the claim actually under test.
- **The not-de-tiled control scores 0.0853 on Kamadan** — reproducing §4's 0.089 for the
  flat row-major rival, from the opposite direction and by a different route.

#### Three defects that only running could have found

1. **The first Blender-side oracle could not see the defect it was named for.** It indexed
   the dumped buffer as `(gy*(dimX+1)+gx)*3+2`, sharing its row convention with the code
   under test. Sabotage — `wy = y0 + j*pitch`, the whole map upside down — left the
   baseline *unchanged*: the z values had not moved within the buffer, only the vertices
   they belonged to had. Rewritten to look each vertex up **by the world coordinates Blender
   stored**. Under the restored sabotage the baseline now collapses to 0.0822 and the y-flip
   control rises to 0.7292 — the mesh is measurably upside down.
2. **`blender --background --python x.py` exits 0 even when the script raises.** MEASURED on
   5.1.1: traceback printed, process reports success. A pipeline trusting the bare exit code
   reads a refused import as a completed one. `--python-exit-code 66` is passed now and the
   test asserts that exact value rather than "non-zero" — its first version asserted
   `rc != 0` and went red against a *working* importer.
3. **The exporter wrote 745 KB of derived ArenaNet data into the working tree.** `REPO_ROOT`
   was one `dirname` short, so it named `toolkit/` and the guard meant to keep exports out
   of the repo pointed at the wrong place. Fixed, and the resolved root is now pinned
   against a tree the test finds independently, so the refusal targets cannot move with the
   bug. Exports default to `vault/exports/`.

Also caught: the floor was left at a placeholder 46, so a vault-less run printed
`ALL CHECKS PASSED (65 checks)` — the `test_codec.py` failure exactly. Floor is 108 from a
real green run; sections 0–4 score 65 and go red without an archive.

#### Two honest limits

- **The mesh bounding box is a weaker check than it looks, and the test says so**: a mesh
  whose rows run bottom-to-top has the *same* bounding box. That is measured rather than
  asserted — a control reverses the row order, fixes the digest so the file verifies
  perfectly, and requires the bbox to be unchanged. It is precisely why the prop oracle
  exists.
- **The GWMB comparison in this rung's original acceptance criterion was NOT done.** Its
  prebuilt `.exe` is not in the vault and §12 records downloading it as an owner decision.
  The rung stands on the prop-z oracle instead, which has the advantage of being a chunk we
  decode ourselves rather than another reader of the same lineage. If the GWMB export is
  ever wanted as a second witness, §16-P5 still applies: it negates height and flips row
  order, and the transform must be declared before the comparison runs.

**Not exported, deliberately:** tag 3, whose bit-pair position inside a byte is not
established by anything measured — unpacking it would be a convention we invented and could
never refute. Tags 2 and 9 are transported as arrays with their meanings labelled unsettled;
moving bytes is transport, not understanding.

**Reproduce.**

```
python toolkit/mapdata/mapexport.py --row 7982 --out <dir>
"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background \
    --python-exit-code 66 --python tools/blender/import_gwmap.py -- \
    <dir>/row_7982.gwmap.json --dump <dir>/mesh.json
```

---

## 20. Rung C2 — OBSERVED: the client loaded a map from a row it did not come from (2026-08-11)

The first rung in this arc to write an archive and launch a client. Owner-authorised.
Four arms, each with a pre-flight, a per-arm snapshot and a post-flight diff. Both copies
were re-cut from `dat_study` afterwards and verified byte-identical to their pristine
snapshots.

### 20.1 The answer

**Yes. Delivery works, and a custom area is ONE payload.**

Arms 1 and 2 both loaded. Row 46196's map payload — ArenaNet's own bytes, re-emitted
through `mapfile.MapFile.encode()` and required to equal the archive's own bytes before
being written — was placed **stored** over row 71496, a live retail area, and the retail
client loaded it, rendered it, and put a character in it.

| arm | partner | result |
|---|---|---|
| **2 — stale partner** | left as the original area's 12,495 B Stripped stream | **loaded**, no re-bloat, no row change |
| **1 — matched** | written to the copied map's own 2,951 B Stripped stream | **loaded**, no re-bloat, no row change |
| 3 — chunk-table size +4 | as arm 1 | **loaded anyway — the control did not control** |
| **3b — terrain signature, one bit** | as arm 1 | **REFUSED by name, then crashed** |

Three things follow, and the first is the one that shrinks the authoring job:

- **The Stripped partner is not consulted on a successful load.** Arm 2 ran first, when the
  partner was genuinely stale, and the map still loaded — with all three of the run sheet's
  discriminators holding: `check_target` after the client exited still read 8,471 B / 18
  chunks / 1 plane / 2 trapezoids rather than the original's ~33,021 B / 27; the post-flight
  showed rows 71496 and 71497 **unchanged**; and `Gw.log` carried no
  `failed to load. Attempting to re-bloat.` So **an authoring tool emits one Bloated map
  file**, and §17.5's "author the Bloated chunk if you want the client to load it as-is" is
  now OBSERVED rather than inferred.
- **A map file may ship STORED.** §8 measured that **0 of 38,621 stored rows begins with an
  `ffna` type-3 payload** — no map has ever shipped uncompressed. Both arms wrote
  `compression 8 -> 0` and the client read them. The Huffman encoder is not needed for maps.
- **The server agreed it was reading the delivered map**, not the pristine occupant:
  `[map] navmesh 0x287D3: 1 planes, 2 trapezoids` on every arm, against the original's 27.

### 20.2 Arm 3 did not control anything, and that is a finding

Arm 3 changed the **chunk table's** last size field, 17 → 21, so the final chunk claims four
bytes that are not in the file. Our own walker refuses it (`archive.ffna_chunks` raises).
**The client loaded it** — no failure line, no re-bloat, rows unchanged.

**So the client's FFNA chunk walk does not validate that the last chunk's declared size fits
the file.** §17.4 had already measured that terrain's per-record sizes are advisory to the
client and that "our own walkers are stricter than the client, which is the right way
round"; this extends the same asymmetry to the container's own chunk table. It also means
an arm designed around *our* strictness tests nothing, which is exactly what happened.

### 20.3 Arm 3b — the control that fired, and it corrects §6

Arm 3b flips **one bit** of the Bloated terrain chunk's signature (`0x87821134` →
`0x87821135`), which §17.4 measured as a hard `jne`→fail gate. The container still walks 18
chunks, so this isolates the content gate from the framing. Prediction was stated first.

The client's own words, from `Gw.log`:

```
Error: Terrain: Failed to import data.
Error: Map '0x0287d3' corrupt chunk 'Terrain Bloated Data'
```

Our file id, our chunk, named in ArenaNet's own vocabulary — `Terrain` + stage `Bloated` +
type `Data`, which is exactly §3's decomposition of `0x20000002` read back to us by the
client. That is the strongest confirmation of §3's chunk-naming the corpus could give.

Then **it crashed**: `c0000005`, "Memory at address 00000017 could not be read", one second
into the map, with the crash's own Error Logs carrying the same two lines.

**This corrects §6 and §17.3.** Both say the loader "logs `Creating default map` and
synthesises an empty map rather than crashing. Only if *that* fails does it assert."
MEASURED: a map whose terrain chunk fails its hard gate produces **no `Creating default map`
line at all**, **no re-bloat attempt**, and an access violation — not an assert, and not a
graceful fallback. The failure path is less forgiving than the disassembly suggested.

Two consequences for authoring: a structurally-plausible map with one wrong magic **kills
the client**, so the authoring pipeline's own validators are the safety net rather than the
loader's; and the re-bloat path did **not** fire for a corrupt chunk, which narrows §17.1's
model of when the client compiles a map — E3 cannot assume a bad Bloated chunk is enough to
provoke it.

### 20.4 What the archive did, and the baseline that made it readable

**The positive control earned its place.** Run against untouched copies before any write, it
loaded Kamadan *and* showed the client relocating rows **8315, 8316, 8317** — the known
scratch rows — with the descriptor counter moving 26881 → 26885. Every subsequent arm moved
the same rows and nothing else, so the baseline is what makes "our rows did not change"
mean anything. Without it, the first arm's diff would have shown three relocations and been
unreadable.

**No arm relocated 71496 or 71497.** The client wrote to its archive on every run — it
always does — but never to the rows under test.

**No checksum could have told us any of this.** §18.5 predicted it and it held: `--verify`
passed after every arm regardless. The 24-byte MFT diff is the only detector.

### 20.5 §16-P7, honoured rather than argued away

Row 71496 is **a live retail area and we still do not know which one** — 64×64 cells, 27
trapezoids, rect −3072..3072. It was chosen by arithmetic as the smallest reservation of
348 candidates that holds both payloads, so it displaced less than any other choice would
have. Everything happened on two dedicated copies; `dat_study` and `C:\gw` were never write
targets, and both copies were re-cut afterwards and verified byte-identical to their
pristine snapshots (`--diff` exit 0 on each).

### 20.6 A harness change the run forced

The operator could not tell when the harness was about to synthesise input, and competing
mouse or keyboard input makes a run fail for a reason unrelated to what was being tested —
worse than a plain failure, because the transcript still looks like evidence.
`drive_client.warn_hands_off()` now prints a countdown before any click or keypress, wired
into both `drive_client.py`'s action loop and `session.py`'s `_play`, with `--warn SECONDS`
(default 3, `0` for unattended runs). In `session.py` it fires **after login completes**
rather than at launch, because that is when the clicking starts — a warning at launch would
expire during the load screen.

There is no cleverer fix available: our input *is* real input as far as Windows is
concerned, so the client cannot be asked to ignore the human's while accepting ours.

*None of C2's conclusions depends on input timing.* The verdicts come from the capture, the
archive diffs, the server's navmesh line and `Gw.log` — no keystroke can write
`corrupt chunk 'Terrain Bloated Data'`.

### 20.7 What C2 leaves

**D1 is now the next rung and its criterion is unchanged**: author a map from our own
builder rather than copying one of ArenaNet's, byte-identically to row 46196's payload, and
report generated-versus-carried with a floor. C2 removed delivery from the risk list —
what remains is entirely about *bytes we write*.

**E3 is weakened as specified.** It assumed a failed Bloated load provokes the compiler;
arm 3b failed a Bloated load and got a crash instead. The re-bloat's trigger is narrower
than §17.1 modelled, and the cheapest remaining probe for it is the **zero-length** stream-1
payload §17.1 names, which is a different failure mode from a corrupt chunk.

---

## 21. Rung D1 — a map built from numbers, equal to ArenaNet's own bytes (2026-08-11)

Two modules. `pathchunk.py` encodes the pathing chunk, which nothing could do before —
`pathmap.py` reads one and is on the running server's path, so it was left untouched.
`mapbuild.py` assembles a whole map from typed parameters plus the §14 constants read from
an archive at run time.

### 21.1 The two halves of the criterion

**Half 1 — byte identity. `build_like(46196)` equals the archive's 8,471 bytes.** The
verifier widened it rather than accepting it: rows 7982 (2,925,270 B) and 26209
(103,623 B) too, then a sweep of **14 maps from 8 KB to 3.29 MB — 14 identical, 0 not**.
So the builder is general, not tuned to one row.

**Half 2 — the census, because half 1 alone can go green on a copier.**

| | bytes | % |
|---|---:|---:|
| **generated** | **7,814** | **92.24%** |
| framing (magic, type byte, chunk table — every size re-derived) | 149 | |
| Terrain `0x20000002` — `terrain.Terrain.encode` | 7,165 | |
| Path `0x20000008` — `pathchunk.PathChunk.encode` | 419 | |
| Map Parameters `0x2000000C` | 41 | |
| Dependencies `0x21000002` + `0x21000009` | 40 | |
| **carried** | **657** | **7.76%** |
| Props 51, Zones 42, Mission 69, Environment 178, Light 7, Shore 17, Sight 44, Sound 17 | 425 | |
| the five §14 constants | 232 | |

**Strictly 5,502 B / 64.95%**, once the 2,312 B of terrain arrays that reach the encoder as
opaque `bytes` are subtracted — the same accounting `mapfile.byte_census` uses.

**The 92.24% is a property of row 46196, not of the builder or the format**, and the
verifier is right to press on it: across its 14-map sweep the figure ranges **75.00% to
92.94%** generated (23.26%–71.64% strict), and row 26209 is 32.18%. Row 46196 is the
ladder's template precisely because it is the simplest map ArenaNet shipped.

**Row 46196's 7,165-byte terrain chunk is generated from fourteen numbers and two 4-byte
tile tables.** Every array in it is uniform, so the parameters reduce to scalars and the
shadow block is regenerated by the run coder.

**`build_flat(32, 32, height=-13.0)` → 7,804 bytes over 8 chunks, 97.03% generated**, with
only the 232 borrowed bytes carried. Reproduced by the orchestrator. It satisfies all 17 of
the client's known gates: dims % 32, extent = dims × 96.0 on both axes, extent % 3072, the
tag sequence, the obstacle grid at 1024/cell, path version 12, no NULL-load chunk id, Map
Parameters before Terrain, and a chunk order read from a real map at run time rather than
typed in. **UNVERIFIED against a client — nothing built here has been loaded.**

### 21.2 The Path encoder: 349 of 349

Every retail pathing chunk decodes to typed values and re-encodes byte-identically.
Nothing declared is stored: every record `size`, all eight plane-header counts and every
element count is **re-derived on encode**.

That distinction is not decoration, and the sabotage table is why:

| sabotage | headline round-trip | caught by |
|---|---|---|
| **pure memcpy** — stash the input, hand it back | **PASS, 3 of 3** | the derivation controls alone, 7 FAILs |
| plane header counts replayed from the file | **PASS, 3 of 3** | one control, 2 FAILs |
| tag 11's size written as the true length | FAIL | 10 FAILs |
| the terrain chunk's 8-byte header | FAIL | 21 FAILs |

**A codec that understood nothing printed `349 of 349`.** It is caught only by mutating a
decoded chunk in place until a payload changes length and requiring the emitted size and
count to move — read back by a walker the test writes out of `int.from_bytes`. That is the
third time this arc has found the same shape (B2's stored-size encoder, B1's cache) and the
first time the naive version would have scored a perfect corpus result.

**Three corpus laws not previously recorded**, all 349/349: tag 7's payload is
byte-identical to plane 0's `polyData` with the count prefixed (FORMAT.md had this for
Kamadan alone — it is corpus-wide, and the encoder records it rather than enforcing it);
**tag 13's obstacle grid is the Map Parameters rect at exactly 1024 units per cell**; and
every sink node names a trapezoid of its own plane, which is what licenses reading a sink
payload as a trapezoid index.

Nothing is normalised, and the verifier proved it both ways: sabotaging tag 11's doubling
gives 0 of 8, and normalising tag 12's two-byte one-plane form fails **naming row 46196** —
the very map D1 targets.

### 21.3 §14 is wrong in its headline and right in its parenthesis

**One of the five "constants" is not constant.** Measured over 12 maps: four are
byte-identical 12/12, but `0x20000006` (Water) takes **two** values, 3 maps to 9. §14's body
says "byte-identical across all 349 maps"; only its parenthesis says "(5 B, two values)".

The first builder trusted the sentence — **and rows 46196 and 7982 both happened to agree
with their donor, so it round-tripped and looked correct.** `build_like` now verifies each
borrowed constant against the map it is rebuilding, substitutes that map's own bytes, and
names the substitution in the report and the chunk's provenance line. The donor is by
default a *different* map, so byte-identity is evidence for §14 rather than a tautology.

**§14's body sentence should be corrected to match its own parenthesis.**

### 21.4 The provenance guard was one checkout short

`mapbuild.resolve_out` refused to write derived ArenaNet data into the working tree it sits
in — but **a git worktree is not the main checkout**, so `--out` into the *other* tree of
the same repository was allowed. Fixed to refuse every working tree of the repo.

Recorded because it is B3's `REPO_ROOT` defect one level up: the first guard knew about one
root, the second knows about the set. And the verifier's own first fix for it was vacuous —
it asked `mapbuild.working_tree_roots()` for the list and then required each to be refused,
so a function returning `[]` would have passed. That is the same failure this arc keeps
finding, this time inside the fix for it.

### 21.5 Left open, honestly

- **The strict census is applied inconsistently.** It subtracts the terrain arrays that
  arrive as opaque bytes but not the pathing chunk's obstacle tiles, which are NOT-FOUND
  bytes copied verbatim in exactly the same way — 27 B on row 46196, 972 B on row 116610 —
  nor the borrowed file ids inside the two generated Dependencies chunks.
- **Nothing built here has been loaded by a client.** D1's criterion is byte identity, and
  byte identity to a map the client already accepts (C2) is strong evidence, but it is not
  the same statement.
- The DAG in `PathChunk.minimal` is INFERRED: `rootType = 1` because retail is 1 on
  11,795/11,795, with one y-node sending both children to one sink so the split's `edge`
  never has to mean anything — which is as well, since what an edge vector *is*
  geometrically remains NOT FOUND.

### 21.6 What D1 leaves

The authoring direction now exists end to end **as bytes**: numbers in, a client-shaped map
file out, 97% of it generated. What has never happened is a client loading one.

That is the natural next experiment and it is C2 with one substitution — the same
pre-flight, the same post-flight, the same target row, `build_flat`'s bytes instead of a
copy of row 46196's. C2 proved the delivery path with ArenaNet's own bytes precisely so
that this run would be a test of *our* bytes and nothing else.
