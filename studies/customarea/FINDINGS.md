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

**Three hazards, all cheap to remove — and all removed, 2026-08-10, `0d4278a` on
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

**Fixed, `0d4278a`.** Hazard 1: the tuple is now `MUTATING_DESTS`, named once, and the
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
| **A2** | ✅ **Landed 2026-08-10, `0d4278a`.** Fixed `datwrite.py`'s `--verify`/`--replace` no-op; wrote `test_datwrite.py` on a synthetic archive | Met, and it found a **fourth** defect nobody had diagnosed: `fix_mft_self_crc()` read through a stale buffered handle and could leave the archive failing its own self-checksum while reporting it correct | **cheap** | — |
| **A3** | ✅ **Landed 2026-08-10, `0d4278a`** — folded into A2. `replace()` writes the whole block reservation as one journalled put, payload followed by zeros | Met. Both the tail-zeroing and the whole-reservation journal fell out of one change, and `--revert`'s "the client wrote here" detector now covers the reservation | **cheap** | A2 |
| **B1** | `toolkit/mapdata/terrain.py`: decode a Bloated terrain chunk to `(map.toml, height.f32, tiles.u8, tag3.bin, tag9.bin, tag4/5, tag7 opaque)` and re-encode | **A retail terrain chunk round-trips byte-identically on 349 of 349 maps.** Anything less names the wrong layout | **cheap→moderate** | A1 |
| **B2** | Whole-file round-trip: decode and re-encode an entire Bloated map payload | 349/349 byte-identical, both stages | **cheap** | B1 |
| **B3** | Blender importer (`tools/blender/`, outside `toolkit/` — `bpy` is not stdlib) | A retail map's terrain appears in Blender at 96 units/cell with the right orientation, **and GWMB's export of the same map agrees after a transform declared in writing before the comparison runs** (it negates height and flips row order; it emits `(dims+1)²` vertices to our `dims²` samples). An undeclared transform makes this rung meaningless in both directions | **cheap** | B1, and §16-P6 resolved |
| ~~**C1**~~ | ❌ **DELETED 2026-08-10 — answered statically by C0 (§17.2).** Normal load requests stream **1**, the re-bloat read requests **0**, the write-back targets **1**. Traced through five frames and re-derived from the other end by the verifier, then paired with the archive's `(flags 3, stream 1)` / `(1, 0)` structure at 349/349 | — no launch was needed | — | — |
| **C2** | **The zero-authored-bytes delivery test.** Row 46196's payload, written stored over a candidate row, three arms (matched partner / stale partner / one size field off by four). **Pre-flight:** the first two items are now **satisfied by the tool itself** as of `0d4278a` — `replace()` journals the whole reservation and zeroes the freed tail, so §8 hazards 2 and 3 no longer need handling at the experiment level. Still mandatory: set `spawn_x`/`spawn_y` inside the copied map's own rect (≈1536, 1536 — its extent is 0..3072 on both axes, and every existing `maps.toml` spawn is thousands of units away); verify offline that the spawn lands in **exactly one** trapezoid of the authored mesh, the same test every other `maps.toml` row carries; diff the target row's MFT entry (offset/size/compression/crc) **before and after every arm** | Arm 1 loads and we stand on a flat square; arm 3 **must** fail with `Attempting to re-bloat`. Arm 2 vs 1 tells us whether a map is one payload or two. **"Loaded, but the MFT row changed" is a first-class outcome, not a pass** — arm 3's expected failure runs the re-bloat path, which re-opens `Gw.dat` for writing, so a successful re-bloat there rebuilds the *original retail map* into the row and "arm 2 loaded" would otherwise read as "a stale partner is fine" | **research, 1 launch** | A2, A3, C0, C1 |
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
`--modules` prints 855 basenames from 865 distinct path strings, not 856 (**and
that gap was a defect, not a rounding — see the note under B12 below**); the
`Map`/`Model` tree is 92 files in 14 directories, not 93 in 13; every Bloated map
row carries exactly **2** file ids (the `{4: 2}` outlier is our own
`archive.py:file_id_table()` registering bit-31 ids under both raw and masked
forms — our helper double-counting, not a property of the archive).

> **Follow-up, 2026-08-11 — the 865 → 855 gap above was `--modules` silently
> merging modules.** OBSERVED. B12 recorded the discrepancy as a count to correct;
> it was `Asserts.modules()` grouping by BASENAME while the printer showed
> `mods[m][0].file`, i.e. the path of whichever colliding file held the lowest VA.
> Nine basenames on build 38797 name two source files each, so nine rows summed
> two modules under one of their names and the other file was absent from the
> census entirely. The two largest rows of that report described no file in the
> image: `Base\rtl\Array.h` (4431 sites) and `Base\rtl\List.h` (3288) printed as
> 4433 and 3295 under their `.cpp` siblings' paths. The one that would have
> produced a wrong *finding* is `PrApi` — `Gw\Pref\PrApi.cpp` (67, preferences)
> and `Engine\Map\Props\PrApi.cpp` (19, props) are unrelated modules 2.4 MB apart,
> printed as one row of 86 against the preferences path, so "props has no
> PrApi.cpp" read as absence. `modules()` now keys on the full path and prints 864
> rows over 19,758 sites; the tenth apparent collision, `Base\Compress\CmpIo.h` vs
> `Base\compress\CmpIo.h`, is one file spelled two ways by two translation units
> and is merged with both spellings named. Regression: `test_codescan.py` §8/§9.

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
**Applied**, then **largely closed at the tool level 2026-08-10 (`0d4278a`)**: a
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

> **FIXED 2026-08-10, `ef4b393`** — "The largest free run holds a live MFT, and the
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
   A shrinking `--replace` frees blocks; `0d4278a` made `--revert` honest about the whole
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

> **FIXED 2026-08-10, `7da3ccd`** — "asserts.py knew one of the idiom's three shapes, and
> --field one encoding of two" — with `2ef6f95` following up on the call sites. The three
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
full-reservation journal from `0d4278a` is what makes the revert honest; it does not stop
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

---

## 22. OBSERVED: the retail client loaded a map we built (2026-08-11)

C2's procedure with one substitution — our bytes instead of a copy of ArenaNet's. Same
target row, same pre-flight, same post-flight, same four discriminators.

### 22.1 What was delivered

`mapbuild.build(...)` with `PathChunk.minimal`, a 32×32 flat grid at height −13, and row
46196's four terrain-texture **file ids** borrowed by reference:

- **7,841 bytes, 9 chunks, 97.04% generated** — 7,609 B computed from parameters, 232 B the
  §14 constants read from the archive at run time. No chunk of it was copied from any map.
- **All 16 of `gates()`'s open-time rules pass.**
- Mesh: **1 plane, 1 trapezoid.** The spawn (1536, 1536) lands in exactly **1**; Kamadan's
  spawn and a point past the far corner land in **0**.

The trapezoid count is a **three-way discriminator**, which is what makes this run readable:
**ours 1**, C2's copy of row 46196 **2**, the original occupant of row 71496 **27**. A
re-bloat could not have produced our number.

Written **stored** into row 71496 of both copies, head only — §20 established the Stripped
partner is not consulted on a successful load, so one payload is what an authoring tool
emits, and the partner was left holding the original area's stream.

### 22.2 The result

**It loaded.** All four discriminators, and the prediction was written before the run:

| discriminator | expected | observed |
|---|---|---|
| `Gw.log` | no failure, no re-bloat | **none** |
| gamesrv navmesh | `1 planes, 1 trapezoids` | **`[map] navmesh 0x287D3: 1 planes, 1 trapezoids`** |
| post-flight diff | 71496 and 71497 unchanged | **neither changed** — only scratch rows 8315–8317 |
| the row after exit | still 7,841 B / 9 chunks / 1 trapezoid | **unchanged** |

The harness reached its `body is in the map` checkpoint at t+8.4 s, from the client's own
messages rather than from a screenshot.

**On the screenshots, read against their control.** Both of our runs caught the client
mid-crossfade with the loading overlay at 100%, which on its own proves nothing. What makes
them worth recording is the **positive control from the same session**: Kamadan, on an
untouched archive, was captured at **0% "Connecting" with no scene at all** — and it scored
PASS on the same checkpoints. Ours shows a rendered world underneath: flat tiled ground, the
character standing on it, a full HUD and a small square minimap. Our run got *further*
visually than the control did, so the images are consistent with the measured result rather
than evidence against it. **They are not themselves the evidence.** The four discriminators
are.

### 22.3 What this settles, and what it does not

**Settled: the whole pipeline closes.** Numbers → `mapbuild` → 97% generated bytes →
`datwrite` → the retail client, which loads it, places a character in it, and writes nothing
back. §21.5's standing caveat — *"nothing built here has been loaded by a client"* — is
retired.

Also settled, as a by-product: a map with **9 chunks instead of 18 loads**. Ten of row
46196's chunk kinds are absent — Props, Zones, Mission, Environment, Light, Shore, Sight,
Sound and two Dependencies lists — which confirms §17.3's "a chunk kind absent from the file
is default-constructed, not rejected" **behaviourally** rather than from the disassembly.

**Not settled, and worth being exact about:**

- **The client's own collision was never tested.** The character stood at the spawn; nothing
  walked it into the boundary of a one-trapezoid mesh. Whether the client agrees with our
  navmesh is the obvious next question and it needs input, not bytes.
- **The terrain was never verified as *ours* pixel by pixel.** The gamesrv's trapezoid count
  proves the server read our geometry; the client's rendering of it is attested only by a
  crossfade frame. A screenshot after the overlay clears would close that, and the overlay
  did not clear within a 25 s hold.
- **Textures are borrowed by file id.** The four ATTX ids come from row 46196. That is the
  route §5 endorses and it is not authored art.
- The build still borrows 232 bytes of §14 constants, by design and by the provenance rule.

### 22.4 Housekeeping

Both copies were re-cut from `dat_study` afterwards and verified byte-identical to their
pristine snapshots (`--diff` exit 0 on each). `dat_study` and `C:\gw` were never write
targets. The other session's run directory was never touched. Artifacts are in
`vault/research/c2-delivery-2026-08-11/` and the payload in
`vault/research/d1-mapbuild-2026-08-11/ours_head.bin`.

---

## 23. OBSERVED: the client collides against geometry we authored (2026-08-11)

§22.3's first open item, in full: *"The client's own collision was never tested. The
character stood at the spawn; nothing walked it into the boundary of a one-trapezoid
mesh. Whether the client agrees with our navmesh is the obvious next question and it
needs input, not bytes."*

Run sheet, predictions and artifacts: `vault/research/e1-collision-2026-08-11/`.

### 23.1 Why one map could not have answered it

D1's map puts the mesh over exactly the terrain rect, 0..3072. Walk into the edge and
stop, and three explanations fit the same number: the client read our pathing chunk; the
client stopped on the terrain's own extent, or the borrowed Collision chunk, or the
obstacle grid, and never looked at our trapezoids; or the walk ended for some other
reason. So E1 runs **two maps whose only difference is where the mesh ends.**

| | mesh rect | boundary from the spawn (1536, 1536) |
|---|---|---|
| **FULL** | 0..3072 — D1's delivered bytes, unchanged | 1536 units |
| **INNER** | 1024..2048 | 512 units |

Built by decoding D1's own delivered payload and swapping ONE chunk, so "everything else
is identical" is a property of the procedure rather than a hope. Measured, not asserted:
**33 of 7,841 bytes differ**, both files are **7,841 B**, the other eight chunks compare
equal by id, form and payload, and both pass **16 of 16** open-time gates. The obstacle
grid stays 3×3 over the full rect in both — it is an open-time rule, and moving it too
would have spoiled the control.

### 23.2 The instrument, and why it is the keyboard

A click cannot measure this. It sends GAME_CMSG 0x003E and the client then waits to be
granted a destination, so where it goes is a fact about **our** `clip_to_walkable` — two
of our own components agreeing, which proves nothing.

A held key can. It sends 0x003D; our server answers with `AGENT_MOVE_DIRECTION`, a
direction and nothing else, and its own integrator broadcasts no position at all
(`authsrv.py`: *"NOTHING IS BROADCAST FROM HERE"*, and on this path *"there is nothing to
clip — we are not naming a point"*). The client walks itself and **reports where it is in
slot 1 of every 0x003D**. Every number below is a byte the client transmitted.

New this rung: `dc.hold_key` and `session.py --walk`, which runs after the spawn verdict
because a walk before the character is standing in the map measures nothing. Plan,
identical in all three runs: `W:8 S:20 W:8 A:1 W:8 S:20`.

**The first control run measured nothing, and that is recorded because the failure is
invisible.** `hold_key` was written like `press_key` and `press_enter`, which pass
`bScan=0`. Held into a client that was foreground and fully in the world, for 65 seconds,
it produced **zero** client messages: the character did not move, did not turn, and
nothing appeared in the open chat box either. `press_enter`'s own docstring names the
reason without following it through — this is a DirectX client reading the **raw input**
path, which carries the hardware scan code, and a synthetic event with `bScan=0` carries
no key at all as far as that path is concerned. A UI-level reader takes the virtual key
and is happy, which is why Enter at login and the skill-slot keys always worked. With
`MapVirtualKey(vk, MAPVK_VK_TO_VSC)` supplied, the same run walked 2,545 units. **Every
leg reported `held 8.0s of 8.0s` in both runs**, so the harness's own report could not
tell the two apart — only the capture could.

### 23.3 The result

| | control (Kamadan, untouched) | **FULL** | **INNER** |
|---|---|---|---|
| position reports | 29 | 50 | 44 |
| bounding box | 2125 × 2902 | **3072.0 × 3072.0** | **1024.0 × 1024.5** |
| box corners | — | (0.0, 0.0)..(3072.0, 3072.0) | (1024.0, 1024.0)..(2048.0, 2048.5) |
| farthest from spawn | — | 2124.1 | 724.1 (= 512√2) |
| reports outside the mesh rect | — | **0 of 50** | 1 of 44, by **0.5 units** |
| server-side off-mesh stops | — | 0 | 0 |

**The two boxes stand in the ratio 3.00 to 1, which is the ratio of the two rectangles,
and 33 bytes inside one chunk are the whole difference between the files.** The terrain
chunk is byte-identical across the two runs, so the character walked on the same ground
and stopped in different places.

The trace is not merely bounded, it is **pinned**. On FULL the client hits `x = 3072.0`
and then reports 3072.0 exactly for five consecutive samples while `y` climbs — a wall
slide — and does the same at `x = 0.0`, `y = 3072.0` and `y = 0.0`. On INNER it does the
identical thing at 1024.0 and 2048.0, and all four of its stops are the two corners
(2048, 2048) and (1024, 2048). There is no inset: the client treats our trapezoid's edge
as the walkable limit to the bit.

**So the retail client's collision comes from the pathing chunk we wrote.** §21's
`PathChunk.minimal` carried the standing label *"UNVERIFIED against a client: nothing
here has been loaded"*; it is verified now, in the only way that could have verified it.

Both arms are clean by C2's discriminators: no `Attempting to re-bloat.` in `Gw.log`, row
71496 unchanged and still reading the arm's own payload after the client exited, the
server copy showing only our own in-place write, and only the client's scratch rows
8315/8316 moving. The gamesrv read `1 planes, 1 trapezoids` in both.

### 23.4 What it settles, and what it does not

**Settled.** The authoring loop closes on geometry as well as bytes: a rectangle chosen in
Python became a wall the retail client will not let a character through. §22.3's first
open item is retired.

Also settled in passing: **the loading overlay does clear** — §22.3 could only report a
crossfade frame. The INNER run's mid-walk screenshots show our terrain rendered from
inside the world: a flat tiled plain, an empty horizon, and a minimap that is a
featureless brown disc where Kamadan's is a detailed city. That is our terrain being
drawn, which §22.3 listed as attested only by the server's trapezoid count. It is not a
pixel-by-pixel verification and is not offered as one.

**Not settled, and the limit is worth stating exactly:**

- **This does not isolate WHICH part of the pathing chunk the client read.**
  `PathChunk.minimal` shrinks the plane's boundary polygon, its trapezoid and its
  point-location DAG together, so all three moved at once. The result is a fact about the
  chunk's walkable geometry, not about the trapezoid list specifically. Separating them —
  shrink the trapezoid while leaving the boundary polygon at full extent, and the reverse
  — is one more pair of 33-byte edits and is the natural next rung.
- **The 0.5-unit excursion is real and is not rounded away.** One report of 44 landed at
  y = 2048.5, and our own server's `clip_to_walkable` printed `standing at (1535, 2049),
  which the navmesh does not cover`. Whether that is the client's collision radius, an
  interpolation artefact, or a genuine half-unit of tolerance is NOT FOUND.
- **Nothing here tests portals, multiple planes, or elevation.** One plane, one trapezoid,
  no neighbours. `minimal`'s DAG remains INFERRED for every shape other than the one
  tested: both branches of its single y-node reach the same sink, so the split test still
  never has to mean anything.
- **The client's collision model is not measured** — radius, step height and how it slides
  are all out of scope. Only the question of whether our trapezoids feed it.

### 23.5 The courtyard, and one soft observation

A third map was built for the operator to walk by hand:
`vault/research/e1-collision-2026-08-11/build_courtyard.py`. It swaps **two** chunks of
the delivered payload rather than one — terrain and path — raising the height field 613
units everywhere outside a 1,920-unit square and putting the mesh rect on that square, so
the boundary sits at the foot of a bank you can see. Still 7,841 B, still 16 of 16 gates,
and the FINDINGS 14 constants, map parameters and texture dependencies are the delivered
map's own bytes. The agreement is asserted before it ships: over all 1,024 cells,
*walkable* equals *every one of the cell's four corner samples is floor* — zero
disagreements, 400 walkable cells. The first version of that check compared against the
single cell a point falls in and reported 164 disagreements that were the check's fault:
samples sit at cell CORNERS, so the cells at the courtyard's edge are the ramp.

**This map is a demo and not an experiment**, and the distinction matters enough to write
down: with the bank and the mesh agreeing, a character that stops has two reasons to and
the run cannot say which stopped it. §23.3's pair is what separates them.

The operator walked it and reported that it **"felt like stock"**. That is a subjective
report from one person and it is recorded as one — it is not a measurement and nothing
above rests on it. It is worth keeping anyway, because the failure modes it would have
caught are ones no assertion here looks for: a floor you sink into, a bank you slide down,
a camera that clips, movement that stutters at the boundary. None were reported.

~~Also worth recording from the same session: the terrain height field reached the client
correctly on the first attempt.~~ **RETRACTED the same day — §25. It did not. The client
drew that map inside out**, the walkable square standing 613 units ABOVE its surround
instead of below it, and the sentence above was written from the operator's "felt like
stock" without anyone looking at a frame. The map WAS non-flat and it WAS walked, so §8
item 10(c) is met in the narrow sense; what is not true is that it came out right.

---

## 24. OBSERVED: the collision is the TRAPEZOID, and tag 7 is not a boundary (2026-08-11)

§23.4's first open item: E1 moved `polyData` and the trapezoid together, so its result
named the pathing chunk's walkable geometry and no part of it. Two more arms, each moving
exactly one. Prediction, outcome table and prior are in
`vault/research/e1-collision-2026-08-11/E1-RUNSHEET.md`, written before either ran.

### 24.1 Tag 7 is not a boundary polygon, and reading said so before any client did

`TAG_BOUNDARY` is **our** name for tag 7. `polyData` is the client's own header field
name and asserts nothing about what the points are. MEASURED over 117 planes of 8 maps:

| polyData points per plane | planes |
|---|---|
| **1** | **102** |
| 2 | 11 |
| 3, 7, 16, 35 | 1 each |

Row 71496's single plane has **27 trapezoids and one polyData point**; row 26209's has 26
and one. **One point cannot bound 26 trapezoids.** Whatever tag 7 is, it is not an outline
of the walkable region, and the name should not have implied it was. What it IS remains
**NOT FOUND**. §23.4 and `pathchunk.minimal`'s docstring both said "the boundary polygon"
and are corrected at their call sites.

`minimal` writes **four** points where every retail one-plane map writes one. That
deviation is in all five maps loaded so far and has never been refused.

### 24.2 The two arms

Each moves one structure and nothing else. Both 7,841 B, **33 bytes apart**, 16 of 16
gates, every other chunk byte-identical to §23's FULL. The control that makes them
one-variable arms: **`split_chunk(FULL, FULL)` reproduces the delivered chunk EXACTLY**,
so a hand-built plane merely resembling `minimal`'s cannot be the difference.

| | polyData | trapezoid | **reported bounding box** | farthest from spawn |
|---|---|---|---|---|
| §23 FULL | 0..3072 | 0..3072 | 3072.0 × 3072.0 | 2124.1 |
| §23 INNER | 1024..2048 | 1024..2048 | 1024.0 × 1024.5 | 724.1 |
| **TRAP** | 0..3072 | **1024..2048** | **1024.0 × 1024.5** | **724.1** |
| **POLY** | **1024..2048** | 0..3072 | **3072.0 × 3072.0** | 2130.1 |

**The box follows the trapezoid in all four maps and polyData in none.** TRAP reproduces
INNER to the tenth of a unit — same box, same 724.1, same single 0.5-unit excursion —
while its polyData covers the whole map. POLY walks the full 3072 square with **44 of its
50 reports outside the polyData rect, up to 1,024 units past it**.

Of the five outcomes the run sheet named in advance, this is the first: **collision reads
the trapezoid, and polyData plays no part in it.** Intersection is refuted by POLY, union
by TRAP, and the polyData reading by both.

A by-product worth its own line: **POLY's geometry is impossible and the client did not
care.** Its trapezoid extends 1,024 units past its own polyData on every side, which no
retail map does — and it loaded, ran, and let the character walk the whole trapezoid.
So the loader does not validate the trapezoid against tag 7. Both arms are clean by C2's
discriminators: no re-bloat line, no crash dialog, row 71496 still holding its own arm's
payload after the client exited.

### 24.3 What this fixes, and what it does not

**It licenses the model our own server already uses.** `pathmap.PathingMap` reads
trapezoids and portals and ignores tag 7 entirely. That was an implementation choice made
before anything had tested it; the arms say it models the field the client actually uses.
Had POLY been the confining arm, the server would have been reading the wrong structure
for a year.

**It narrows `minimal`'s INFERRED parts.** The trapezoid's spans are now OBSERVED as
collision geometry. The DAG is untouched by this: `minimal`'s single y-node splits at 0
and sends both children to the same sink, so no branch of it depends on a coordinate, and
these arms could not have tested it. Portals, neighbours, multiple planes and elevation
remain untested — E1b, like E1, is one plane and one trapezoid.

**And §17.4 said so first, from the other side.** Its table of the Bloated load path has
tag 7 marked ✗ — *"Skipped by size. The tag is not checked; only the size field matters,
because tag 8 must land at the next offset"* — and its own summary calls the tag **"dead
weight for a Bloated map — never read, only its size field matters."** That was read out
of the disassembly and written down before any of this ran, and POLY is the behavioural
confirmation of it: the client walked 1,024 units past a polygon it never loaded. Two
independent methods, and it is worth saying plainly that **I did not connect them until
after the run** — the prior in the run sheet was argued from retail's point counts, not
from our own disassembly of the loader, which had already answered it.

It also explains the point counts. §17.4 continues: tag 7 *"is the input to the bloat
handler, so a map that ever gets re-bloated is rebuilt from whatever polygon is in the
Stripped stream."* The Bloated copy is a vestige of the compile that produced it, which is
why one point satisfies a plane with 27 trapezoids. **Nothing here tests the STRIPPED
stream's tag 7**, where the polygon is the real input, and E3 is the rung that would.

**Neither arm tests the DAG's point location**, which is the obvious next thing: a plane
with two trapezoids and a y-node that actually splits between them would make the split
value mean something for the first time.

---

## 25. OBSERVED: a greater stored height is LOWER in the world (2026-08-11)

Found by accident, from an operator's bug report, against a claim this repository had
written down twice and tested three times without ever being able to see it.

### 25.1 How it surfaced

The operator walked §23.5's courtyard by hand and reported that the floor and the
character models sometimes stopped being drawn when backing into a corner. Chasing that
produced a screenshot — and then, on re-reading the run's own auto-captured frames, this:

**The walkable square is drawn as a MESA.** `vault/captures/harness/20260811T161925/hold007.png`
shows the character standing on a brick-topped plateau with sheer cliffs falling away on
two sides and a lower brick shelf beyond. The map was authored **floor −13 inside
576..2496, rim +600 outside**. The client drew the floor 613 units **above** the rim.

### 25.2 The experiment, one variable

Same map, one number changed: the rim from **+600** to **−626** — still 613 units from
the floor, the other sign. Everything else byte-for-byte identical, 7,841 B, 16 of 16
gates.

| stored | floor | surround | **drawn** |
|---|---|---|---|
| courtyard | −13 | **+600** | a mesa: the floor 613 **above** the surround |
| courtyard2 | −13 | **−626** | a walled enclosure: the surround 613 **above** the floor |

The operator's words on the second: *"the walls are up now and the camera acts accordingly
being constrained by them."*

**So rendered up is the NEGATIVE of the stored value.** Two runs, one sign, opposite
pictures. This is the only property of the terrain chunk that no amount of round-tripping
could have caught: every map built in this arc before the courtyard was **flat**, and a
flat field has no sign.

### 25.3 What is corrected, and it is ours

`mapexport.py`'s conventions block, rule 4, read: *"**Heights are NOT negated.** The load
path applies no transform at all — tag 1 reaches the client's buffers through `memcpy` and
nothing else (FINDINGS 17.4). GuildWarsMapBrowser's `Terrain.cpp::GenerateTerrainMesh`
negates every height; that is ITS renderer's convention and FINDINGS 16-P5 records it as
such."* `tools/blender/import_gwmap.py` carried the same paragraph.

The `memcpy` observation is **true and was never the point**. It is a fact about bytes
reaching a buffer; it says nothing about which way that buffer's axis points. The headline
drawn from it was wrong, and the dismissal of the one upstream that had it right was
wrong with it.

**GWMB negates every height and agrees with the client.** §16-P5's filing of that as "ITS
renderer's convention" is CORRECTED — it is the client's convention, and upstream had it
before we did. Same shape as §24's tag-7 result from the opposite direction: there we had
the answer in our own notes and did not connect it; here somebody else had it and we
argued it away.

**What is NOT corrected**, because it was never wrong:

- The prop-z orientation oracle (§4, `test_mapexport`, `test_blenderimport`, scoring 0.304
  / 0.734 against three rival layouts) compares **stored** prop z from chunk `0x20000004`
  against **stored** terrain height. Both are in the same convention, so the oracle
  measures LAYOUT — which cell a sample belongs to — and is unaffected by the sign of the
  axis. It remains correct and its numbers stand.
- The terrain codec. Nothing in encode/decode touches the sign; 349/349 byte-identical is
  a statement about bytes and stays true.
- `mapexport`'s output. An interchange is entitled to carry the stored value as long as it
  says which it is, and it does.

**What IS now known to be wrong: the Blender mesh is upside down.**
`tools/blender/import_gwmap.py` puts the stored float in z, so a retail map imported there
shows every valley as a hill. It is left that way ON PURPOSE for now and labelled at the
call site: `test_blenderimport`'s oracle looks up prop z in Blender's own vertex buffer,
props and terrain share the stored convention, and negating one without the other would
break an oracle that is currently right. Both sides have to move together and the 0.7338
has to be re-measured. `PLAN.md` §8 item 10(f).

### 25.4 A second observation, from the same sentence

*"the camera acts accordingly being constrained by them"* — **the client's camera collides
against terrain.** OBSERVED, from one operator report on one map, so it is not a
measurement of the rule; but it retroactively explains the mesa map's behaviour, where a
camera trailing a character standing on a plateau had nothing at all to stop it leaving
the world.

### 25.5 The rendering fault is NOT settled by this

The bug report that started it is still open, and the mesa reading explains only part of
it. What the investigation established, all OBSERVED from the run's own frames joined to
the position trace:

- **It is not the corner.** The character stood on the EXACT south-east corner at
  20:20:09Z and both bracketing frames draw normally; it also stood on the exact north-west
  and south-west corners earlier, all normal. Three of four corners touched precisely, only
  the fourth visit degraded.
- **It is two-staged, five seconds apart.** Character models stop drawing at 20:20:12Z
  while the floor is still drawn; the floor stops at 20:20:17Z. **No position predicate
  produces that ordering**, and nothing yet explains it. The surviving candidate is two
  different cull radii, models shorter than terrain — UNVERIFIED, and no per-pass radius
  has been found in the client.
- **It did not recover within the run.** Every frame from 20:20:17Z to the end is degraded
  and the session disconnects at 20:20:31Z. The operator's reported recovery is real but is
  not in this capture.
- **The dark-teal expanse is the map's own background**, present in the correctly-drawn
  frames with geometry on top of it. Not water.
- Killed with reasons: the terrain chunk's draw-distance field (tag 0 +0x08 = 24576.0
  drives a chunk window of radius ≥ 3 chunks about the camera, and this map is ONE 32×32
  chunk, so its floor is inside the window at every possible value); `MapVis`'s
  camera-block asserts at `0x00710057`–`0x007100AB`, arithmetically unreachable; and the
  water plane.

`--shots` was added to `session.py` for this: it screenshots during the hold so an operator
can provoke a fault with both hands. The frames it caught are what dated the fault and what
refuted the corner story — including the operator's own description of a recovery.

---

## 26. The terrain cull is reproducible, recovers, and is NOT about our relief (2026-08-11)

§25.5 left the fault with no mechanism. It is now scriptable, and three arms
narrow it. Run sheet and predictions: `vault/research/e1-collision-2026-08-11/`.

### 26.1 What had to be built first, and what it cost

Two input verbs, both of which emitted bytes and did nothing:

- `hold_key` with `bScan=0` — held W for 65 s into a live client that ignored
  every keystroke (§23.2).
- `orbit` with `SetCursorPos` — **MEASURED: terrain 78.8% before the pitch step
  and 79.1% after.** The pointer warps; no input event is synthesised; a client
  on the raw input path sees nothing.

Both were caught by the operator watching a screen, not by a test — and a test
cannot catch the second on its own, since both versions emit a button down, a
sequence of moves and a button up. **Every "zoomed out and pitched up" claim
made before this was measured is void**: only `zoom` ever did anything, so the
condition that reproduces the fault is zoom plus movement and does NOT include
any camera pitch.

`framestat.py` is the measure, calibrated against real pixels: background is
`rgb ~ (32,64,64)`, terrain is grey/brown with `r >= b`. Its first version
counted the teal background AS terrain and reported 95–99% terrain on frames
with none in them — a measure that cannot separate the two states says the fault
did not happen.

### 26.2 The bisection

One plan, `zoom:-16 wait:2 W:8 S:20 W:8 A:1 W:8 S:20`, `--no-enemy`,
`--shots 1`. Terrain is 70–79% in a normal frame and 0.1–0.4% in a degraded one.

| arm | terrain | TERRAIN GONE | MODELS GONE | BOTH |
|---|---|---:|---:|---:|
| **mesa** | walkable square drawn HIGH | **12 of 70** | 0 | 0 |
| **walls** | walkable square drawn LOW | **0 of 66** | 17 | 0 |
| **flat** | −13 everywhere, no relief | **12 of 70** | 1 | **5** |

**The relief is refuted.** Flat has none and degrades exactly as much as the
mesa — so the mesa reading in §25, which explained the fault by a camera falling
off a plateau, does not survive its own test.

**Walls is clean for a reason that is not a fix.** Its frames show the camera
jammed against a wall with the whole viewport filled by wall texture; the
character is occluded to a sliver. That is the constraint the operator reported
("the camera acts accordingly being constrained by them"), and it means the
camera never got far from the character in that arm. Its 17 MODELS GONE are
**occlusion, not a culling failure** — the skin measure cannot tell those apart
and is not offered as evidence here.

**Flat is the only arm reproducing BOTH stages together**, which is the closest
anything has come to the operator's original ordering.

### 26.3 Where that leaves it

**The operator's judgement, and it is the one to record.** With the height sign
corrected the map is what it was meant to be — a plateau with a square dug out —
and the camera pulling back over the plateau when you stand near a wall is
*"stock enough"*. That is the reading of someone who has played this game, on the
map as designed, and it fits every arm above: the two arms that degrade are the
ones where the camera can get out over nothing, and neither is a shape a playable
map has.

**A follow-up of mine died immediately and is recorded so nobody retries it.**
The obvious next idea was "retail leaves an unwalkable margin around the playable
area and we do not". MEASURED against the archive: row 46196 — the ladder's own
template, a shipped map — has walkable geometry spanning its **entire** map rect,
margin **0**, exactly like our flat map. So do 7982 and Kamadan. Only 26209/71496
(768) and 116610 (4,457) have one. **Retail has no such rule.**

So this is filed as a **cosmetic artefact of a test map missing ten chunk kinds**
— Environment and Light among them, so there is no sky, no fog and nothing to
draw when the camera looks at empty space — and NOT as a defect in anything the
authoring path produces. Reopening it needs a map that has those chunks, which is
a different rung. What is now OBSERVED and was not before:

- the fault is **reproducible under script**, 12 of 70 frames, twice on the same
  map with the same plan;
- it **recovers** — terrain returns the moment the walk turns away;
- **it is not combat.** The operator's original run had 0 damage and 0 revives;
  two of this session's runs had 11 and 6, because main's newest commits made
  the Hatcher lethal mid-session. Those two runs are discarded and every arm
  above is `--no-enemy` with 0 combat events. **The operator caught that too.**

Still NOT FOUND: any per-pass cull radius in the client, and any explanation of
why the two passes cross five seconds apart.

---

## 27. OBSERVED: the neighbour graph is collision, and it is 8 bytes (2026-08-11)

`PathChunk.minimal` emits one trapezoid per plane and no neighbours, so nothing
in this arc had ever asked the client to cross from one trapezoid into another.
"The client honours the trapezoid list" and "the client walks the neighbour
graph" predicted the same thing on every map built so far.

### 27.1 No DAG was invented

MFT row 46196 — the ladder's own template — ships a plane with exactly **two**
trapezoids over the rect 0..3072, which is our map's rect, so its 419-byte
pathing chunk drops into our map unchanged and re-encodes byte-identically.
What was delivered is ArenaNet's own geometry in our file.

    trap 1   y    0..2976     <- the spawn (1536, 1536)
    trap 0   y 2976..3072
    linked   trap0.neighbours = (-, -, 1, -),  trap1.neighbours = (0, -, -, -)

The control clears those two entries to `NO_NEIGHBOUR` and touches nothing else.
Both arms are **7,957 B and differ in 8 bytes**; same trapezoids, same DAG, same
edges, same polyData, same every other chunk, 16 of 16 gates on both. **`pathmap`
reports them identically** — it reads trapezoids and ignores neighbours — so our
own reader cannot tell them apart and only the client can.

### 27.2 The result

| | position reports | pinned at y = 2976 | crossings of the split | min y |
|---|---:|---:|---:|---:|
| **LINKED** | 49 | **0** | **2** | 0 |
| **CUT** | 79 | **39 of 79** | 1 | 1536 |

**With the link cut, the character spends half the run stuck on the internal
edge**, reporting y = 2976.0 exactly for 39 consecutive samples while x slides
along it — the same wall-slide signature §23 measured at the mesh boundary. With
the link intact it never touches the edge and crosses twice.

So the neighbour graph is **collision data the client enforces**, not routing
metadata it merely carries. Two trapezoids that both exist, both decode, both
contain walkable points and share an edge are still not connected unless the
edge is named.

### 27.3 One asymmetry, unexplained

The CUT arm crossed the split **once, northward**, before getting stuck. Entry
into trapezoid 0 succeeded; every later attempt to leave it southward failed.
Whether that is the client resolving entry differently from exit, or a diagonal
step overshooting the edge, is **NOT FOUND**. It is recorded rather than smoothed
over: a clean reading would have had zero crossings in the CUT arm.

Also not settled: the DAG. Both arms carry row 46196's, unmodified, so nothing
here says what an x-node or a y-node tests — only that the neighbour slots on the
trapezoid records are load-bearing. Authoring a plane whose geometry is not row
46196's still needs that, and `PathChunk.minimal` still cannot express two
trapezoids.

---

## 28. OBSERVED: the point-location DAG, and the portal record (2026-08-11)

`edgeVectors` was NOT FOUND for the whole arc, and `PathChunk.minimal` sidesteps
the DAG by sending both children of its one y-node to the same sink. Both are
settled here, from the archive, by two independent implementations.

### 28.1 The DAG

**`edges` is a POINT POOL, not vectors.** A y-node compares the query's y
against `edges[edge].y`; **`child0` is taken when ABOVE**. An x-node names a
SEGMENT by its two endpoints `edges[edgeA] -> edges[edgeB]`, evaluates that
segment's x at the query's y, and compares; **`child0` is LEFT**. `root_type`
names the kind of node 0. A sink's payload is a trapezoid index.

Measured by walking the DAG and comparing against brute-force
`Trapezoid.contains` over the corpus:

| | queries | agreement |
|---|---:|---:|
| reader, 47 maps / 1,061 planes | 974,951 | **0.999875** |
| refuter, **289 maps the reader never used** | 2,964,320 | **0.999931** |
| whole corpus, 349 maps / 11,795 planes | 3,613,537 | **0.999935** |

Every disagreement lies within **0.010 world units** of an edge, and of the
uniformly-sampled points **zero** disagree. The rivals are not close:

| rival | interior agreement |
|---|---:|
| y-node children swapped | **0.000000** |
| x-node children swapped | **0.000000** |
| y-node compares `edges[e].x` | 0.091 |
| x-node as a vertical line at an endpoint | 0.683 |

A second method that samples no points at all: propagating the y-constraint down
the DAG, **every sink is reached on exactly one contiguous y range, 123,152 of
123,152**, and that range equals its trapezoid's own y span. Under the swapped
reading **122,972 of 123,152 sinks become unreachable**. And over all 349 maps,
`sorted(sinks) == range(n_traps)` — **a bijection on 11,795 of 11,795 planes**.

Two supporting corpus laws, both exceptionless: `edges[edgeA].y >= edges[edgeB].y`
on **3,872,385 of 3,872,385** x-nodes, so a segment is always stored top-to-bottom;
and trapezoids do not overlap — 17 hairline pairs of 2,824,893, none more than
0.01 units in both dimensions.

**Not settled:** the tie convention at exact float equality (nothing in the data
decides it, and brute force's own closed interval is equally arbitrary); what
~60% of `edges` entries are, since only 989,728 of 2,488,209 coincide with a
trapezoid corner; and 95,761 x-nodes with a horizontal segment, which the model
cannot evaluate and which no query in 3.9M ever reached. **UNVERIFIED against the
client**: this is the archive's bytes agreeing with themselves under a model, not
the client's own query code.

**Do not switch `PathingMap.containing()` to the DAG.** It is slower in Python
(~2.5 µs against ~1.1 µs) and the two structures disagree within 0.011 units of
an edge — exactly where the 5.5% off-mesh player positions live.

### 28.2 The portal record

`<4HB` = `(traps u16, offset u16, neighbour u16, pair_id u16, flag u8)`, tag 9.
Each field is pinned by a corpus law AND by the client's own machine code:

| field | meaning | evidence |
|---|---|---|
| `traps` | COUNT of this plane's trapezoids on the crossing | `sum(traps) == len(portalTraps)` on **11,792/11,792** planes; reading `offset` as the count scores 140/11,792 |
| `offset` | start index into tag 10 `portalTraps` | the `[offset, offset+traps)` slices PARTITION portalTraps, 11,792/11,792; swapped scores 1/11,792 |
| `neighbour` | the OTHER plane's index | equals the partner's own plane **42,847/42,847**; never its own |
| `pair_id` | the crossing id, shared by exactly two ends, **1-based** | group sizes `{2: 42847}` — no singleton, no triple; value 0 unused by 346 of 346 maps |
| `flag` | write **0** | 0 on all 85,694 retail portals. Meaning NOT FOUND, but it is not padding — the import copies it to runtime +4 |

**What a wrong portal costs, which is why none of this was guessed:** a trapezoid
naming a portal whose pair never resolved hits `PathDir:1496/1532`, and FINDINGS
records that the client asserts and then **dereferences anyway**. `offset+traps`
running past `portalTraps` is checked by nothing at all — the client indexes
straight off `pathMap+0x38` and reads whatever follows.

### 28.3 What this unblocks

`PathChunk.minimal` can now be given a real sibling: a plane whose two trapezoids
are chosen rather than copied from row 46196, with a DAG derived from the split
rather than inherited. §27 put ArenaNet's own two-trapezoid plane in front of a
client; this is what it takes to author one.

---

## 29. Two planes load. A portal whose ends do not coincide crashes. (2026-08-11)

The first authored two-plane map: two planes side by side, x 0..2048 and
2048..3072, two trapezoids each, a DAG derived from §28's semantics rather than
copied. Built by `build_portal.py`, which asserts §28's five portal rules before
writing anything.

### 29.1 What the two arms did

| arm | portals | result |
|---|---|---|
| **PORTAL-CUT** | 0 | **loads, and the whole walk completes** |
| **PORTAL-JOINED** | 2, one pair | **CRASHES: `Assertion: index < m_count`, `Base\rtl\Array.h(587)`, 17 s in** |

**So two planes are fine and the portal record is the fault** — the arms are the
same file but for the portal, and the cut one survives 65 s of walking.

**And the cut arm is a result in its own right: planes are NOT joined by
adjacency.** The character's reported bounding box is
**(0.0, 63.9) .. (2048.0, 3072.0)** — pinned at x = 2048.0 exactly, 0 of 76
reports outside plane 0 — even though plane 1's trapezoid begins at that very
coordinate and the terrain is continuous across it. Two planes that touch are two
worlds. Only a portal can join them, which is what §28 said the record is for.

### 29.2 Which field is wrong, and it is none of them

Every field of the emitted portal is inside the range retail uses, measured
after the crash rather than assumed before it: `portal_left`/`portal_right` are
plane-local (1,391 of 1,391 retail entries are `< len(plane.portals)`),
`portalTraps` holds plane-local trapezoid indices, and `pair_id` runs 1..189.
§28's five rules all passed. **The rule set was incomplete, and it was shipped to
a client on the strength of being complete.**

The one property that distinguishes our portal from all 85,694 retail ones was
recorded as UNVERIFIED by the study that produced the recipe: *"Whether the
client REQUIRES the two ends to coincide geometrically. Retail does so to
float32 precision, but nothing in the load path validates it... A non-coincident
pair would most likely load and produce wrong movement rather than refuse, but
that is UNVERIFIED and I did not build one."*

**CORRECTED, before the follow-up arm ran.** The first version of this section
said our pair was disjoint and therefore in a category retail never uses. It is
not. Measured on the emitted bytes rather than assumed from the design: our two
ends' bounding boxes are `(0,0,2048,3072)` and `(2048,0,3072,3072)`, so the
x overlap is **exactly 0** — **edge-touch**, which is **16.5% of retail (48 of
291 pairs)** and not the 0% category at all. The claim was wrong and the
hypothesis it supported is much weaker than stated: retail ships edge-touching
pairs and ours crashed.

So **what makes our portal different from all 85,694 retail ones is still NOT
FOUND.** Every field is in range, `traps = 2` occurs 184 times, and edge-touch
occurs 48 times. Candidates not yet eliminated include `plane_map`, whose values
this arc has always recorded as NOT FOUND and which we wrote as `[0, 0]` — retail
is non-decreasing with values that are plainly not plane indices (row 7982 with
58 planes begins `[0, 6, 8, 9, 10, 15, 16, 22, ...]`).

### 29.3 The harness said PASS

`judge()` runs before the walk, so the verdict was read from the spawn
checkpoints twelve seconds before the client died, and every later step logged
`NO WINDOW` — which reads like a focus problem rather than a corpse. Fixed:
`walk_legs` checks `proc.poll()` before each step and stops loudly, and a client
that dies mid-plan **retracts the verdict**. Discovered by the operator reading a
crash log, not by anything here.

### 29.4 Next

An arm with two planes that OVERLAP in x and y, joined at a coincident pair —
which is the shape every retail portal has, and the shape this one did not.

---

## 30. OBSERVED: `plane_map` is a per-plane PROP INDEX (2026-08-12)

Two client crashes, identical: `Assertion: index < m_count`,
`P:\Code\Base\rtl\Array.h(587)`. Read out of the client rather than guessed at,
after two hypotheses that measured well and were wrong.

### 30.1 The mechanism

The two runs relocated to different bases (`0x490000`, `0x680000`), so every RVA
in the 21-frame chain is unambiguous. With `ImageBase 0x400000` (pefile,
`DllCharacteristics 0x8140` = ASLR):

| VA | what |
|---|---|
| `0x00487BDB` | the generic assert reporter's own eip-capture — 20,144 callers, not a bounds helper |
| `0x0073C57F` | **the site.** `props->propArray[propIndex]`, one caller in the image |
| `0x00738D82` | `PrApi.cpp:573/574` |
| `0x0070A4B0` | `MapQueryAltitude()` |
| … | the per-frame avatar path — which is why it fires 17 s in and not at load |

The array is `props->propArray`, `m_data` at `props+0x194` and `m_count` at
`props+0x19C` — named by ArenaNet's own assert at `PrIntersect.cpp:135`,
*"propIndex < props->propArray.Count()"*, which emits the byte-identical
`cmp edi, dword ptr [esi+0x19c]`.

The index comes from **`PathGetProp`** (`0x00721C40`, self-named by its log
string), which does `imul ecx, esi, 0x54` / `add ecx, [edi+0x18]` — indexing the
plane array by the query point's **zplane** — and returns that plane's stored
prop index **unvalidated**. Only the plane index is bounds-checked
(`PathApi:510`); the prop index never is.

And that stored value is ours. `PathDataImport`'s tag-12 handler at `0x007254B0`
forces `map[0] = (-1, -1)` — **plane 0 IS the terrain** — starts its loop at
`i = 1`, and stores `plane_map[i]` into `map[i].propIndex`. **So every plane
above 0 is mounted on a prop, and tag 12 is a per-plane PROP INDEX.** It is not
a plane index, and it has been NOT FOUND for this whole arc.

We wrote `plane_map = [0, 0]` into a map carrying no props chunk at all, so
`propArray.Count()` is 0 and `0 < 0` fails.

**Why the two no-portal controls lived**, which is the part that makes this
explanation load-bearing rather than plausible: `MapQueryAltitude` at
`0x0070A433` does `cmp dword ptr [ecx], 0; je 0x70A4D7` — **if the position's
zplane is 0 the prop lookup is skipped entirely.** Without a portal the character
can never leave plane 0, so the crashing code is never reached. The portal is
what lets zplane become 1. That also explains why the ends' geometry made no
difference: edge-touch and a 1,024-unit overlap crash identically because
neither is what the client objected to.

### 30.2 The gate, and its real control

`mapbuild.gates()` gains a seventeenth rule: **every REACHABLE plane above 0
must name a prop that exists.** Reachability is the closure of `{0}` under "plane
i has a portal whose neighbour is j", and it is what makes the rule more than
"does this file have a portal".

| | our gate | naive "has a portal" |
|---|---:|---:|
| the 2 crashing payloads | **RED 2/2** | RED 2/2 |
| the 10 loading payloads | GREEN 10/10 | GREEN 10/10 |
| **150 retail maps, 4,756 planes, 148 multi-plane** | **RED 0** | **RED 148** |

**The twelve payloads cannot discriminate and are not offered as if they could**
— crashers and controls differ only in the portal, so any portal-keyed predicate
separates them identically. The corpus is the evidence: our rule is red on none
of 150 retail maps where the rival is red on 148.

### 30.3 What this does and does not license

**Settled:** tag 12's meaning, the reason both portal arms crashed, and why both
cut arms survived. A gate that would have refused the payload before it reached
a client.

**Not settled:**

- **The zplane transition was RECONSTRUCTION, and it is now MEASURED — and it was
  WRONG.** §30.1 argued the avatar must have stepped onto plane 1, because
  `MapQueryAltitude` short-circuits when the position's zplane is 0. The captures
  already on disk refute it. Slot 2 of GAME_CMSG 0x003D is the client's own plane,
  and across all three runs it is **0 in every single report**:

  | run | position reports | plane field |
  |---|---:|---|
  | portalcut (no portal) | 76 | **0 on 76 of 76** |
  | overlapcut (no portal) | 76 | **0 on 76 of 76** |
  | overlap (PORTAL, crashed) | **1** | **0** |

  The character never left plane 0 in any run, including the one that crashed —
  and the crashing run sent exactly ONE position report before dying, i.e. it died
  almost the moment the character began to move.

  **So the trigger is a QUERY on plane 1, not OCCUPANCY of it.** Something asks
  for the altitude of a point on the far plane — a path evaluation across the
  portal is the obvious candidate — and that is enough. The defect is unchanged
  (plane 1 names a prop that does not exist) and so is the gate, which keys on
  REACHABILITY rather than on where the avatar stands; if anything this is why
  reachability was the right predicate. But §30.1's sentence "the portal is what
  lets zplane become 1" is a RECONSTRUCTION that the data does not support, and
  what the portal actually does is make plane 1 *queryable*. NOT FOUND: which
  call site issues that query.
- **A legal two-plane map is not yet authorable.** It needs chunk `0x20000004`
  with `propCount > max(plane_map[1:])`, and that record's layout is NOT FOUND in
  this toolkit. Whether a dummy prop suffices, or the prop's model must actually
  carry the surface the plane describes, is untested.
- **Collapsing to one plane would be a VACUOUS fix.** zplane is then permanently
  0, the short-circuit fires, and the assert is unreachable by construction —
  which is exactly why the cut arms walked clean for 65 s. A green single-plane
  run says the map is walkable and says nothing about `plane_map`.
- The gate is a static check against the crash we understand. **A map passing all
  17 gates is not a map a client will accept** — this one passed 16.

---

## 31. OBSERVED: a portal we authored, and the control that had to crash (2026-08-12)

§30 named what stopped every portal: tag 12 is a per-plane PROP INDEX and our
maps carried no props chunk. This adds the chunk rather than removing the plane,
and runs the control that makes a green run mean something.

### 31.1 The two arms

Both 14,976 B into row 26209's 45,056 B reservation, **differing in ONE u16** at
offset 14900 — tag 12 entry 1.

| | `plane_map` | gates | run |
|---|---|---|---|
| **portalprop** | `[0, 0]` — prop 0 of 67 | **18 of 18** | walked 65 s, no crash |
| **portalpropbad** | `[0, 67]` — one past the end | **RED**, by the §30 gate | **crashed** |

The props chunk (6,585 B) and its model dependencies (89 B) are **carried from
row 33086 at run time**, never stored — `mapbuild`'s FINDINGS 14 pattern. Their
insertion point is read from a real map rather than chosen: retail puts
`0x20000004` immediately after Map Parameters and `0x21000004` immediately after
that, and our chunk order stays a subsequence of row 33086's.

### 31.2 The portal joins two planes

| | portalcut (no portal) | **portalprop** |
|---|---|---|
| bounding box | (0, 64)..**(2048**, 3072) | (0, 0)..**(3072**, 3072) |
| plane field the client reported | **0 on 76 of 76** | **0 on 30, 1 on 19** |
| reports past x = 2048 | 0 | **17** |

Plane 0 is x 0..2048 and plane 1 is x 1792..3072, overlapping by 256 units with
the spawn clear of it. Without the portal the character is pinned at x = 2048.0
and never reports plane 1; with it, it crosses and reports plane 1 on 19 of 49.

**This also settles §30.3 from the other side.** That section measured the plane
field as 0 in every report of every run and concluded the crash was a QUERY on
plane 1 rather than occupancy of it. Both hold: the transition is real and
happens on a working portal, and the crashed runs never reached it because they
died first.

### 31.3 The control, and why it is worth the crash

`portalpropbad` crashed with `Assertion: index < m_count, Array.h(587)`, and the
crash log is not merely "it crashed":

- It loaded at **BaseAddr 0x00400000**, so the trace carries the STATIC addresses
  and they are §30's, unmodified: `0x0073C57F` ← `0x00738D82` ← `0x0070A4B0`.
- The call frame reads `Rt:0073c57f Arg:1c93e808 **00000043** 00000000`, and at
  the fault **`edi = 0x43 = 67`**.

**67 is `propCount`. It is the number we wrote into tag 12, appearing in the
register the disassembly said holds the index.** The diagnosis did not merely
predict a crash; it predicted which value would be in which register, and that
is what arrived.

### 31.4 What this settles, and what it does not

**Settled.** A portal we authored works: two planes, four trapezoids, a DAG
derived from the split, a portal pair, and a props chunk that makes plane 1
legal. §8 item 10(b) is done. And a prop index only has to be IN RANGE — prop 0
of row 33086's 67 is somewhere else entirely in the world and the client did not
care, which answers §30's open question about whether the prop must actually
carry the surface.

**Not settled:**

- **What plane 1 looks like underfoot is untested.** The character crossed and
  kept walking; nothing measured its z, and our terrain is flat, so a plane
  mounted on a prop whose model is elsewhere may well be placing the character on
  nothing. The interesting version of this rung is a plane whose prop IS its
  surface.
- **One prop index was tried, not the space.** `[0, 0]` works and `[0, 67]`
  crashes; nothing between was tested.
- **The harness said PASS over the crash**, again, for a new reason: `judge()`
  runs before the walk, walk_legs retracts when the client dies BETWEEN steps,
  and this client died during the HOLD. Fixed — a hold-time exit now retracts the
  verdict too. That is two distinct paths to a false PASS found in two days, both
  from the same root: the verdict is computed early and nothing downgraded it.

## 32. The round trip out of Blender, and what its headline is worth (2026-08-12)

**OBSERVED.** A retail map's terrain goes out to the neutral interchange, into
Blender, onto disk as a `.blend`, back out through a *separate* Blender process,
and returns **byte-identical**: Pre-Searing's 212,992 heights (851,968 B),
212,992 tile bytes and 212,992 shade bytes, sha256 for sha256. Two processes and
not one scene, because a round trip inside a single session establishes that two
functions are inverses and says nothing about whether the `.blend` carried
anything.

`tools/blender/export_gwmap.py` is the new half. It undoes four things, and each
is a place a silent exporter loses work:

| undone | why it can go wrong |
|---|---|
| the lattice, re-derived from world POSITIONS | vertex order shares the importer's convention |
| the manufactured far edge, dropped | the file holds `dimX*dimY`, the mesh `(dimX+1)²` |
| z, negated back | FINDINGS 25 — raising a vertex LOWERS the stored value |
| the metadata, carried but CROSS-CHECKED | tag 0 and the tile tables are not in a mesh |

### The headline is the weak half, and that was measured rather than argued

A memcpy passes it. **MEASURED:** with `_stamp` stashing the height array on the
object and the exporter preferring it, a tool that reads no vertex and
understands nothing keeps **all six byte-identity checks GREEN — including
ArenaNet's 851,968 bytes** — and is caught by exactly two checks. Both are in the
edit path, and the decisive one is the **sculpt**: one vertex moved in Blender by
a literal `+250.0`, requiring exactly that cell to move by exactly `−250.0` in
the stored convention. `453.0 → 203.0`, one cell of 6,144. Without it the whole
file is satisfied by a tool that copies bytes.

This is the same shape as `test_mapfile`'s stored-size control and
`test_agentlife`'s twelve combat constants: the impressive number was never the
check. Three sabotages were run and each landed where predicted —

| sabotage | prediction | result |
|---|---|---|
| the negation dropped | several sections | 4 red, across 4 sections |
| the memcpy above | sections 1 and 5 stay GREEN | exactly so; 2 red |
| the residual check deleted | only the 0.5-unit band | exactly so; 40-unit case still green |

### An identity `matrix_world` multiply is not a no-op on signed zero

**OBSERVED, and it cost one byte of 24,576.** A stored height of `0.0` reaches
Blender as `-0.0` (the importer negates), survives `from_pydata`, and survives
the `.blend` — both checked directly against the bit patterns. Then
`-0.0 * 1.0 + 0.0` evaluates to `+0.0`, because IEEE addition of the two zeroes
yields the positive one. Negating back therefore produced `-0.0`, and one cell
came back `00000080` where ArenaNet's byte was `00000000`: **numerically
identical, bytewise not.** A tolerance would have hidden it; a bare digest would
have reported "the heights are wrong" and sent a reader to the de-tiling. The
export now skips the transform when there is no transform, and the comparison
reports byte-differs and value-differs *separately* so the next one names itself.

### The far edge is named for its effect, because it has two causes

The count is `manufactured_edge_unstorable`, not "edited". Sculpting a far-edge
vertex puts it on the list and the stored heights come back **identical** — the
drop happened. Sculpting the **last real column beside it** puts the same vertex
on the same list and the stored heights **change**, in exactly that cell. One
number, two meanings; an exporter conflating them reports the wrong thing about a
perfectly legitimate edit. Both are checked.

### Authored from nothing

A mesh built in Blender by script, with no stamp to carry, exports and reaches
`mapbuild`, which assembles a map file passing **all 17** of the client's
open-time gates. Terrain authored in Blender is now a thing the loader accepts.

### What this does NOT establish

- **Terrain only.** Props, zones, water and the navmesh do not go through
  Blender. An author edits the height field and nothing else.
- **The navmesh is still hand-authored**, and it is what the client actually
  collides against (§23, §24). A sculpted hill in Blender changes what is *drawn*
  and does not move a single trapezoid.
- **No client run.** Nothing here was loaded by the retail client. The strongest
  claim is `gates()`, which is our reading of the loader's rules, not the loader.
- The `0.0`/`-0.0` finding is about our transform, not about ArenaNet's format.

## 33. The compiler's input side, and E3's contract is wrong (2026-08-12)

**OBSERVED.** Chunk `0x10000008` — the Stripped partner's pathing chunk, the
thing §17.2 specified as rung E3's authored input — now has a codec
(`pathchunk.StrippedPath`). **349 of 349 retail chunks re-encode byte-identically**
and **349 of 349 are exactly `19 + 8n` bytes**, which confirms §17.2's arithmetic
against the archive rather than against a disassembly pass.

Nothing in the tree could read this chunk before today. The contract had been
read out of the client and measured once; there was no encoder, no decoder and
no test, so authoring one was not possible and the 349/349 figure rested on a
single unreproducible sweep.

### The framing is NOT the Bloated chunk's, and they share a signature

|  | Bloated `0x20000008` | Stripped `0x10000008` |
|---|---|---|
| header | 12 bytes, `<III>` | **9 bytes, `<IBI>`** |
| version | `u32` 12 | **`u8` 12** |
| records | `u8 tag, u32 size` | **`u8 tag`, unsized** |

So Bloated tag 7 is `u8 7, u32 size, u16 n, n × Vec2f` and Stripped tag 7 is
`u8 7, u16 n, n × Vec2f`. Read either with the other's reader and the u16 count
is consumed as the low half of a u32 size — a **plausible desync, not an error**.
Both codecs now refuse the other's bytes and that is a checked control.

### THE CORRECTION: the boundary polygon is CARRIED, not compiled

§17.2 specified E3 as *"publish a stream-0 payload holding the boundary polygon;
the client compiles stage 1 → 2"*. That reads the polygon as the compiler's
geometric input. **MEASURED, and it is not.**

- The Stripped boundary is **identical to the Bloated boundary, point for point,
  in 349 of 349 maps.** So is the sequence number. It survives compilation
  unchanged.
- **28 maps ship a boundary of two points or fewer** — 15 of them a *single
  point*. Pinned case, file id `0x9F5E`: its entire Stripped pathing chunk is
  **27 bytes** holding the one point `(-4380.0, -1860.0)`, and its Bloated
  partner carries **3,437 trapezoids over 24 planes**.

27 bytes cannot encode 3,437 trapezoids. **Whatever the compiler builds the
navmesh from, it is not tag 7.** The existing check that Bloated tag 7 is a copy
of plane 0's `polyData` fits: the boundary is a small per-plane polygon carried
through, not the map outline.

**What this costs E3.** Its headline economy — *"cheapest trigger, fewest
authored bytes"* — conflated *the Stripped pathing chunk is tiny* with *the
compiler's input is tiny*. The trigger is still cheap (a zero-length stream-1
payload); the **input** is not. Pre-Searing's Stripped stream is ~900 KB, and the
mesh presumably comes from the terrain and collision chunks — consistent with the
module names `PathBuild.cpp` and **`PathFlood.cpp`** on the builder's closure
(§17.1, Track C), a flood fill being a terrain operation and not a polygon one.

E3 is not dead and is arguably now **more** valuable: if the compiler floods our
terrain, it closes the gap §32 left open, where a Blender-authored hill changes
what is drawn and moves no trapezoid. But it must be respecified before it is
run, and the cost is a whole Stripped map rather than 19 + 8n bytes.

### What is still NOT FOUND

- **`sync_hash`.** 349 distinct values, one per map, no pattern measured. It is
  carried, never derived — the honest position, and a limit on E3, since a
  compiler that validates it would reject anything we author.
- **`sync_flag`** is 0 in all 349. Constant, meaning unknown.
- **The winding is ours.** `StrippedPath.rect`'s docstring first claimed retail
  had a convention; the corpus refutes it — **169 counter-clockwise, 151
  clockwise, 29 degenerate**. Whether the compiler cares is unknown and only E3
  can say.
- **What the compiler actually reads** is now the open question, and it is
  answerable offline by reading `PathBuild.cpp`/`PathFlood.cpp`'s closure for the
  chunks it touches — no client needed.

## 34. What the map compiler reads — terrain and props are hard gates (2026-08-12)

**The question §33 left open, answered from the client's own instructions.** When
the client converts stage 1 → stage 2, the Path builder reads **no chunk by id**.
It reads the already-bloated *in-memory objects* of Terrain, Props, Zones and
Collision, plus the Map Parameters rect and flags, out of a **0x34-byte
converter-local** that ArenaNet's own assert text calls `state`.

Four agents, two adversarial skeptics, and every load-bearing address below
re-disassembled independently before it was written down.

### The dispatch

```
s_chunkInfo[0x08].bloat = 0x00712640          MapData.cpp
  0x00712643  target stage must be 2, else return 1 untouched
  0x00712650  mapType 2 (server maps) REFUSED -- assert at 0x00712656
  0x0071266E  ecx = [ebp+0x1c] = state
  0x00712671  edx = [ecx+0x2C]  -> je return 0   TERRAIN IS A HARD GATE
  0x00712678  cmp [ecx+0x24],0  -> je return 0   PROPS IS A HARD GATE
  0x0071269D  call 0x007217D0 with ELEVEN args (add esp,0x2c)
     -> 0x007217D0  PathApi, validates srcData/srcSize and the output buffer
     -> 0x00724990  copies state into a ctx at ebp-0x7c, then runs a
                    SEVEN-ENTRY pipeline table at 0xBF72F0..0xBF730C
```

**The two `je`s are unconditional and unguarded: with no terrain object or no
props object the Path chunk is not built at all.** That is the strongest single
result in the study.

### The `state` struct — every field pinned to its writing instruction

| off | object | written at | by |
|---|---|---|---|
| +0x00..0x0F | map rect, 4×f32 | 0x0070D977–0x0070D98A | Map Parameters |
| +0x10 | flags (normalised ≥1, range-checked ≤3) | 0x0070D990 | Map Parameters |
| +0x24 | **props** | `0x00712324 mov [esi+0x24],eax` | Props |
| +0x28 | **zones** | `0x00712134 mov [edi+0x28],eax` | Zones |
| +0x2C | **terrain** | `0x00711F72 mov [esi+0x2c],eax` | Terrain |
| +0x30 | **collision** | `0x00712BAA mov [ecx+0x30],eax` | Collision |

All four object writes were verified by direct disassembly here, not taken on an
agent's report. The Collision one loads `ecx` from `[ebp+0x1c]` explicitly — the
same argument slot the Path handler reads — which is what proves the struct
identity rather than merely being consistent with it.

### The seven-stage pipeline, and where the boundary goes

The table at **0xBF72F0** (7 entries, bound `cmp esi,0xBF730C`) sits immediately
before the per-plane table `pathchunk.PLANE_TAG_ORDER` already uses. It had never
been dumped.

| # | VA | does | reads |
|---|---|---|---|
| 0 | 0x00724910 | 9-byte Stripped header in, 12-byte out | — |
| 1 | 0x00724770 | **copies tag 7 through**, size `n*8+2` | ctx+0x0C |
| 2 | **0x00724670** | **the mesh builder** → 0x0072FB80; emits tag 8 | terrain, props, collision, flags, rect |
| 3 | 0x007243C0 | tag 12 | ctx+0x74 |
| 4 | 0x007244C0 | tag 13 obstacles → ZnApi | **zones** |
| 5 | 0x007242E0 | tag 14 through | ctx+0x28 |
| 6 | 0x00724380 | 0xFF terminator | — |

**This settles §33 mechanically.** Tag 7 is copied by pass 1; the mesh is built by
pass 2, which never touches it. The client's own `n*8+2` emit is the same `8` as
the `19 + 8n` law measured from the archive — two sides, no shared input. And the
table's tag order, read out of `.data`, reproduces `pathchunk.CHUNK_TAG_ORDER`
exactly, which was derived here from the file format alone.

### The flood grid IS the terrain lattice

**OBSERVED.** Grid allocated `(w+2)·(h+2)·16` with a one-cell border
(0x0072CBBA); index `dims->w·row + col`, 16 bytes per cell. Sibling 0x0072CFD0
reads four corner heights per quad into vec3s whose x/y are ±96.0, and the
world-to-cell divisor is the double 96.0 at 0x0094DE10 — the same cell pitch
`test_terrain.py` pins independently from the file side. **One flood cell per
terrain cell, two triangles per quad**, classified by slope against 10/45/40° or
15/35/30° depending on a mode flag.

**So the compiler floods OUR terrain.** That is exactly the mechanism §32 hoped
for: it is how a Blender-authored hill could become a navmesh.

### Where the angles disagreed

- **The corpus cannot name the compiler's inputs, and the skeptic wins.** A
  size-ranking method scored **AUC 0.463 — below a coin flip** — against the true
  input set; it would have named Mission, Environment and Light while leaving
  Terrain, Collision and Map Parameters off. Its own nuisance floor, built from
  eight chunks the builder never touches, is partial r **+0.478**. The corpus
  contributed exactly two things: the row-33833 counterexample and a seed→plane
  relation. **Take the input set from the disassembly and nothing from the
  ranking.**
- **A confident zero was correctly reached on an insufficient basis.** "0
  references to `s_chunkInfo`" scoped only the base address 0xA6CF78, but the
  dispatch encodes `0xA6CF90` (base + 0x18) with the index already scaled by 5 —
  so a base-scoped sweep is blind to 9 of 12 references *including the dispatch
  itself*. Re-run with a positive control that fires (5 refs from the converter
  root, 0 from the Path root), the zero is real. Right answer, wrong warrant,
  recorded separately. Same shape as `test_codescan` §7's three defects.
- **8 pushes vs 11.** One angle printed an abridged listing; the real call takes
  eleven and hands the callee the **entire `state`**. An independent count agreed
  on 11. **So the reachable input set is a floor, not a ceiling.**

### What this does NOT establish

1. **Nobody has run the compiler.** Everything above is a claim about
   instructions in a file. No map authored, no conversion executed, no client
   observed compiling anything.
2. **We have not shown the shipped client ever runs this path at load time.** All
   349 retail maps ship with *both* streams already built. Whether the runtime
   ever converts — or whether stage 2 is always pre-baked by ArenaNet's own tool
   and the converter is dead weight in the retail image — is **NOT ESTABLISHED**,
   and it decides whether E3 authors stage 1 at all.
3. **The trapezoid algorithm was not read.** Six flood/contour callees
   (0x0072E0E0, 0x0072D670, 0x0072D730, 0x0072D7E0, 0x0072E810, 0x0072D450) were
   not disassembled. The seed/flood/contour reading is INFERRED from call
   structure.
4. **3,953 indirect calls were not followed**, and `codescan --xrefs` does not
   search indirect or computed targets at all. Three within this arc are
   unresolved.
5. **The assert census is short by ~370 sites image-wide.** Every per-module
   count is a floor — and the clean negative "no assert in PathBuild/PathFlood
   names terrain, height, grid, cell or prop" is **actively misleading**: the code
   does precisely what those asserts do not mention. A reader of the census alone
   would conclude the builder consumes nothing but segments, and would be wrong.
6. **Collision has never been observed non-empty** — a 9-byte stub in 349/349.
7. **The walkability mode flag was not traced to a source**, so which of our
   authored slopes count as walkable is unknown.
8. **No `mapType` of any real map was measured.** NOT FOUND.
9. **Nothing here is covered by a test.** None of it is in the suite.

### What rung E3 must now author

Mandatory, or no Path chunk is produced at all: **Terrain (0x02)** bloating to a
non-null object, and **Props (0x04)** bloating to a non-null object — props
supplies the portal/collision point pairs the decomposition runs over. Required
by the surrounding machinery: **Map Parameters (0x0C)** (41 B, signature
0x5943EEEF, version byte 2), **Zones (0x03)**, and a **Collision (0x0E)** 9-byte
stub. The Stripped **Path (0x08)** chunk itself is carried through verbatim and
its boundary is not the mesh; one point demonstrably suffices.

**Ruled out as geometry sources:** Locations and Sight are 9-byte constant stubs
on 349/349 and are not passed to the builder. Sight is generated from nothing —
9 bytes in, up to 478,412 out — so it needs no authoring.

**The next honest step is not more static analysis.** It is authoring a minimal
Stripped map and observing whether a Bloated Path chunk appears — the first
experiment in this arc that could come back "no".

## 35. OBSERVED: the client compiles a map, and reproduces ArenaNet's bytes exactly (2026-08-12)

**Rung E3's premise is confirmed, and the largest open question in the arc is
answered YES.** The shipped retail client runs the stage 1 → 2 converter at load
time. Given a map whose Bloated stream is zero length, it logs, compiles the
navmesh from the Stripped partner, and writes the result back into the archive —
**byte-identical to what ArenaNet shipped**.

Run 2026-08-12, `vault/research/e3-rebloat-2026-08-12/`, on
`vault/run/2026-07-29_221c13772c7a-c2/Gw.dat` (a copy; `dat_study` and `C:\gw`
were read-only throughout).

### What was done

`rebloat.py --arm` replaced map 143's Bloated stream (file id `0x287D3`, MFT row
71496, 9,284 B stored / 33,021 B payload, **27 trapezoids over 1 plane**) with a
**zero-length** payload, zeroing its whole 9,728-byte reservation and journalling
every byte first. This is FINDINGS 17.1's cheapest trigger and deliberately not
the corrupt-chunk one, which C2's arm 3b showed produces an access violation with
no re-bloat attempt (§20.3).

Post-arm, **all ten of the client's own open-time rules still passed** — measured
on the real 4.2 GB archive, not just on the built fixture. Live rows fell
177,329 → 177,328, which is the zeroed row leaving the live set.

The client was then launched caged against our own server (ours-DH build,
loopback) and sent to map 143.

### What the client did

`Gw.log`, from the unguarded log site FINDINGS 17.1 predicted:

```
Perf: Map file '0x0287d3' failed to load.  Attempting to re-bloat.
```

And then it rebuilt it. The row **relocated**, exactly as predicted — a
reservation is `ceil(size/512)*512`, so a zero-length row reserves nothing and
the client's free map took the blocks:

| | before | after |
|---|---|---|
| offset | `0x63C64200` | **`0x4B82E00`** |
| size | 9,284 | 9,284 |
| compression | 8 → **0** (by the arm) | **8** |
| stored CRC | `0x12ACFE34` → 0 (by the arm) | **`0x12ACFE34`** |

### The result, and it is stronger than the experiment asked for

**The rebuild is byte-identical to ArenaNet's shipped payload, in both forms:**

| | client's rebuild | ArenaNet's ship |
|---|---|---|
| stored (compressed), 9,284 B | `85cb3f332c8a29e0…` | `85cb3f332c8a29e0…` |
| decompressed payload, 33,021 B | `acfc8e7501e94b9e…` | `acfc8e7501e94b9e…` |

Same trapezoid count (27), same plane count (1), same 18 chunks — and the same
bytes, compression included.

**THE ARM DEMONSTRABLY APPLIED**, which is the check that makes the above mean
anything rather than being what a failed arm looks like. The journal records the
pre-arm bytes: the reservation went from `c01d010266bc75c9…` to all zeros, size
9284 → 0, **compression 8 → 0**, crc `0x12ACFE34` → 0. The compression field is
the clincher: the arm set it to 0 and it is 8 again, so the client rewrote the
row wholesale rather than anything having failed to take. `rebloat.py` prints a
warning on byte-identity for exactly this reason, and the warning is what
prompted the check.

### What this corroborates, and it was flagged as INFERRED

FINDINGS 17.1 named an unmeasured claim as "the cheapest possible test of the
whole model": *whether retail's Bloated streams were shipped by ArenaNet or
produced by this client at download time* — INFERRED from the two bloat entry
points, `FcApi:1393/1394`'s paired `downloadIndex`/`bloatIndex` meter, and
`MapData:997` *"Only clients can bloat client maps"*.

**A compiler reproducing a shipped payload to the bit is what you see when the
shipped payload came out of that compiler.** The alternative — that ArenaNet's
own offline tool and this client independently emit identical compressed streams
— is not credible. So the INFERRED claim is now CORROBORATED, by an experiment
nobody designed to test it, and **every retail Bloated map in the archive is an
output of the compiler we want to borrow.**

### Archive hygiene

Post-flight `datcheck --diff`: TIER 0 descriptor counter 26881 → 26886, MFT
moved; TIER 1 four relocations — row 71496 plus rows **8315/8316/8317**, the
client's own scratch rows, which are the known baseline churn C2 established and
which moved in every arm of that rung too. TIER 2 (the directory invariant)
unchanged both ways. All ten open-time rules and all three CRC rules pass after.
The copy was re-cut from `dat_study` afterwards and the journal marked CONSUMED —
reverting it after the client relocated rows would corrupt rather than restore.

### What this does NOT establish

1. **n = 1.** One map, one run. Small (27 trapezoids, one plane, 64×64 cells).
   Nothing here says a large multi-plane map recompiles, or recompiles
   identically.
2. **It says NOTHING about terrain we authored.** This map's Stripped stream is
   ArenaNet's, so what was demonstrated is that the compiler reproduces
   *ArenaNet's* input faithfully. Whether it floods a height field WE wrote is
   the next experiment and is not evidence in hand.
3. **"Non-null" is not "usable".** FINDINGS 34's hard gates require terrain and
   props objects to exist. That an authored Stripped map would bloat to objects
   the builder accepts is untested.
4. **The re-bloat wrote to the archive**, which is a hazard, not a convenience:
   any run of an authored map is a run that mutates the copy it was given.
5. **We did not observe the mesh being USED.** The character spawned and the run
   passed its checkpoints, but nothing here walked the rebuilt navmesh or
   collided against it.

## 36. OBSERVED: the compiler builds from the Stripped stream WE supply (2026-08-12)

**§35 showed the client compiles. This shows it compiles OUR INPUT.** Given a
Stripped stream that belongs to a different map entirely, the client built that
map's navmesh — byte-identical to the donor's shipped Bloated payload — under the
file id of the map it was asked for.

### The design, and the prediction stated before the run

§35's result had an obvious alternative reading: the client might have restored
map 143 from a cache, a download, or something keyed to the file id, and the
byte-identity would then say nothing about compilation. This separates those.

On a copy: row 71497 (map 143's Stripped partner) was replaced with **row 46197's**
Stripped payload — the ladder template map, 32×32 cells — and row 71496 (map 143's
Bloated stream) was zeroed. Nothing else changed. The two candidate meshes are far
apart and both are known:

| | trapezoids | Bloated payload |
|---|---|---|
| map 143's own (row 71496) | 27 | 33,021 B |
| the donor's own (row 46196) | **2** | **8,471 B** |

**PREDICTION, recorded before launching:** if the compiler reads the Stripped
stream we supply, the rebuild holds **2 trapezoids over 1 plane**, not 27.

### The result

`Gw.log` again: `Map file '0x0287d3' failed to load.  Attempting to re-bloat.`

The rebuild is **8,471 B, 18 chunks, 2 trapezoids over 1 plane** — and
byte-identical to the donor's shipped map:

| | payload | sha256 |
|---|---|---|
| client's rebuild of `0x287D3` | 8,471 B | `4178b052f0037fa8…` |
| row 46196, the DONOR's shipped map | 8,471 B | `4178b052f0037fa8…` |
| row 71496, map 143's original | 33,021 B | `acfc8e7501e94b9e…` |

`rebuild == donor` **True**. `rebuild == map 143's original` **False**.

### What this establishes

**The compiler's input is the bytes in stream 0 of the row, and nothing else.**
Not a cache, not the file id, not a download — the client produced a map it had
never been asked for, because that is what the Stripped stream we wrote said.

Combined with §35 (the rebuild reproduces ArenaNet's own bytes) and §34 (terrain
and props are hard gates and the flood grid IS the terrain lattice), the route
rung E3 was named for is now open end to end **except for one missing piece**:

> **Author a Stripped stream → the retail client builds the Bloated map,
> navmesh included.**

### The one thing still in the way

`0x10000002`, the STRIPPED terrain chunk, is a different encoding from the
Bloated `0x20000002` and `terrain.py` refuses it — *"terrain version 1619525649
!= 17 (the client compares the full u32)"*. Both share the signature
`0x87821134` and the version byte `0x11`, and the stripped form is roughly half
the size corpus-wide (ratio 0.4673), so it is a packing of the same logical data
rather than a different structure. **Until that codec exists we can deliver
somebody else's terrain but not our own**, which is exactly the gap between this
result and §32's Blender pipeline.

### Archive hygiene

Post-flight: descriptor counter 26881 → 26886, five relocations (rows 71496 and
71497 plus the client's three scratch rows), directory invariant unchanged both
ways, all ten open-time rules and all three CRC rules pass. The copy was re-cut
from `dat_study`; both journals are marked CONSUMED, because reverting after the
client relocated rows would corrupt rather than restore. `dat_study` and `C:\gw`
were read-only throughout.

### What this does NOT establish

1. **Still n = 1**, and the donor is a 32×32 one-plane map — the simplest in the
   archive. Nothing here says a large or multi-plane Stripped stream recompiles.
2. **The terrain is still ArenaNet's.** Both maps in this experiment are theirs.
   No byte we authored has been through the compiler.
3. **Nothing walked the rebuilt mesh.** The character spawned and the run passed
   its checkpoints; collision against the 2-trapezoid mesh was not tested, and
   the spawn (1536, 1536) happens to lie inside both candidate rects, which is
   why the run could not fail for the wrong reason.
4. **The Bloated stream must be made to FAIL for any of this to happen.** This is
   a repair path, not a normal load — an authored map still has to ship a broken
   or absent stage 2 to get compiled, and what the client does with a
   *permanently* zero-length stream across sessions is untested.

## 37. The STRIPPED terrain codec — the last piece of the E3 route (2026-08-12)

**§36 left one thing in the way and named it: `0x10000002`.** This section is
that chunk, read out of the client and then checked against the archive. A height
field authored in Blender can now be written into a Stripped stream. **Whether
the client compiles ground we wrote is the next experiment and is not evidence in
hand** — §36 handed the compiler somebody else's terrain, and this is what makes
handing it ours possible, not what shows the result.

The evidence is not the round trip. It is that the height field this codec pulls
out of a Huffman-coded bit stream **equals, sample for sample, the one
`terrain.py` reads out of the BLOATED chunk** — a different encoding, written by
a different subsystem, that the codec never looks at.

MEASURED 2026-08-12 over the whole corpus, 1,205 s:

| | |
|---|---|
| height field equals the Bloated chunk's, sample for sample | **349/349** |
| dims, tiles, both tile tables, tag 3, distance, texture fields | **349/349** |
| tag 7 decodes to the same 272x272 bitmaps | **349/349** |
| the Bloated lightmap's bytes do NOT occur in the Stripped chunk | **349/349** |
| byte-identical re-encode | **349/349** |
| reconstructed vs carried | 144,594,950 / 220,180,662 = **65.67%** |

That first row is **60,468,224 float32 samples** — FINDINGS 19's own corpus
total for tag 1 — recovered from compressed bits. The byte-identity is the
weaker claim and never appears without the census beside it.

### Where it came from

`s_chunkInfo[0x02].bloat = 0x00711EC0` calls **0x00759550**, whose two asserts
name `TrnDataBloat.cpp:730/731` (`!stripDataLength || stripData`, `buffer`). It
drives an **eleven-entry pipeline table at 0x00A74958** — `{fn, f32 cost}` —
exactly the shape §34 found for the Path converter's seven at 0xBF72F0.

| # | VA | emits | reads from the Stripped cursor |
|---|---|---|---|
| 0 | 0x00759380 | the 8-byte Bloated header | **5 bytes**: `u32` sig, `u8` version |
| 1 | 0x00758CC0 | tag 0, 26 B | 1 + 9 bytes |
| 2 | 0x00758A10 | tag 1, `dimX*dimY*4` B | the bit-coded height field |
| 3 | 0x007590F0 | tag 2 | `dimX*dimY` bytes, verbatim |
| 4 | 0x00759140 | tag 4 | `u8 n`, `u3 w`, n entries of w bits |
| 5 | 0x00758F10 | tag 5 | the same shape |
| 6 | 0x00759320 | tag 3 | `dimX*dimY/4` bytes, verbatim |
| 7 | 0x00758AD0 | tag 9 | **nothing at all** |
| 8 | 0x00758B60 | tag 7 | the shadow blocks, optional |
| 9 | 0x00758C40 | tag 3' | 17 bytes, verbatim, optional |
| 10 | 0x007589D0 | 0xFF | 1 byte |

Record headers come from `0x0073E410` (read) and `0x0073E580` (write), and the
split is the same one `pathchunk.StrippedPath` found from the other side: **at
stage 1 a record header is ONE byte, the tag**; at stage 0 or 2 it is
`{u8 tag, u32 size}`.

### Tag 9 is BAKED, not stored — and it explains §19's lightmap fit

**Stage 7 reads nothing from the cursor.** It computes `sin`/`cos` of tag 0's sun
elevation (0x005BC0F0 / 0x005BC4F0), builds the vector `(f(t), 0, g(t))`, and
hands it with the height field to **0x0075CC30**. The Bloated chunk's
`dimX*dimY`-byte lightmap is generated at load time.

FINDINGS 19 fitted `255 * max(0, N.L)` to tag 9 and reported a median Pearson r
of **0.887 over 345 maps**, an elevation tracking tag 0's angle field at Spearman
**0.9352**, and the light on the +x axis with no y component on **343 of 345**.
That fit was measuring this generator. The client's own
`TrnTexIntensity:342 lightDir.y == 0` is the same statement from a third side.
`test_strippedterrain.py` pins the consequence with a check the archive could
refuse: the Bloated shade bytes **do not occur anywhere in the Stripped chunk**.

### The height codec

Per 32x32 terrain tile, in the same tile-row-major order `Terrain.index` uses,
and inside each tile a raster of 8x8 sub-blocks of 4x4 samples:

* a 40-bit block header — `s16 dcBase`, `u4 dcBits-1`, `s16 escBase`,
  `u4 escBits-1`. Five bytes, so the byte-align that follows is already
  satisfied and the table always starts on a byte.
* a canonical Huffman table over 1024 symbols: `u8 w-1`, eighteen counts of `w`
  bits, then one 10-bit symbol per code in canonical order. 18 is the client's
  own `maxLength` argument at 0x00764AC0 and 10 is `bitLength(1023)`.
* 64 sub-blocks. Coefficient 0 is `dcBase + u<dcBits>`; the other fifteen are
  symbols read as `symbol - 512`, with **symbol 1023 escaping** to
  `escBase + u<escBits>`.
* the sixteen coefficients are a 4x4 integer transform, inverted
  columns-then-rows by `(a,b,c,d) -> (a-b-c, c+a-b, a+b-d, d+a+b)`, and written
  as float32 at `out[r*32 + c]`.

The bit reader is `TrnBitStore.h` — ctor 0x00758920, `Read` 0x007593F0, asserts
at lines 52 (`bitCount < 8 * sizeof(dword)`) and 128 (`bitCount`). It is
MSB-first over big-endian words with a 32-bit sliding window.

### Every coding parameter is DERIVED, and each was measured to be

This is what makes a green decode an assertion rather than a comparison of a
value with itself. The decoder **refuses** a file whose stored parameter
disagrees with what its own samples need — so the counts below are a 187-block
census over three maps, and the corpus-wide decode asserts the same thing on
every block of every map by refusing:

| parameter | derivation | measured |
|---|---|---|
| `dcBase` | `min(the block's 64 DC coefficients)` | 187/187 blocks |
| `escBase` | `min(the block's escaped coefficients)` | 66/66 |
| `dcBits` | `max(bitLength(dc - dcBase), 1)` | 187/187 |
| `escBits` | `max(bitLength(esc - escBase), 1)` | 66/66 |
| `w` (table) | `max(bitLength(max count), 1)` | 187/187 |
| `w` (tags 4/5) | `max(bitLength(max entry), 1)` | 6/6 records |
| the symbol SET | exactly the symbols the block uses | 187/187 |
| every align pad | zero | 187/187 |

**One thing is carried: which code length each symbol gets** — the counts array
and the symbol order within it. That is ArenaNet's frequency model, the samples
cannot recover it, and a Huffman construction of ours would match their bytes
only by coincidence. 22 of 187 sampled blocks have a symbol list that is not
merely sorted, so the order is load-bearing. Tags 2, 3 and the optional second
tag 3 are carried because the FORMAT carries them; there is no encoding under
them to understand.

### A correction to `terrain.py`: the 1-ULP caveat is retired

That file records the sun angle as landing "within 1 ULP of `b*pi/508`", with
`float32(b*pi/508)` reproducing 39 of 55 stored bit patterns and the best
alternative, `float32(1.5707963705062866*b/254)`, reproducing 53 of 55.

The client computes neither. At **0x00758D99** it evaluates

```
(float)((double)b * 282.74334716796875 / 45720.0)
```

where 282.74334716796875 is `(double)(float)(90*pi)` — a float32 constant
promoted, so 90pi is rounded ONCE before the divide — and 45720 is 508*90. It
reproduces the Bloated chunk's stored float on **349 of 349** maps.

The two retired formulations differ from it at **88** and **3** of 256 indices
respectively, and both are run as controls that must disagree. **The corpus
confirms `terrain.py`'s own number from the other side**: 63 of 349 maps carry an
angle index where `b*pi/508` differs, and it is wrong on all 63 — leaving
349 − 63 = **286**, which is exactly the "286 of 349" that file measured
independently before anyone had read the client's expression.

### Traps, each paid for once

* **The Stripped header is FIVE bytes, not eight.** `terrain.py`'s own docstring
  said "signature, then `u16 17`, then `u16 0x6088`". The version is a byte and
  0x6088 is not a field at all — it is the first two bytes of tag 0's body.
  Reading eight puts the first record header three bytes late. Corrected there.
* **Tag 0 stores dimY before dimX.** Every square map agrees under either
  reading; 416x512 does not.
* **Tag 0 stores the cell pitch, and the client compares it against 96.0** with
  an `fucompp` against the f32 at 0x0094DE38. It is the only place in either
  stream where the pitch is written down; every other appearance, including
  `terrain.py`'s `CELL_PITCH` and the flood grid's divisor, is compiled in.
* **The client's post-decode untile/retile pair is the identity.** 0x007630F0
  and 0x00763060 are mirror images and their composition does nothing; the
  decoded array is already in the Bloated chunk's tiled order. Do not read that
  pair as evidence of a layout change.
* The client reads tags 2 and 3 with **no bounds check at all** — 0x00763030
  copies `dimX*dimY` bytes from the cursor whatever remains.

### A real constraint on authored terrain, and it is small

`_inverse4`'s matrix has determinant 8, so its image is an index-8 sublattice of
Z^4 and a four-vector is representable only when `w == x (mod 2)`,
`y == z (mod 2)` and `w + x == y + z (mod 4)`. Applied along both axes, a 4x4
sample block lives on an index-8^8 sublattice of Z^16. **A freely authored height
field is essentially never on it.**

`snap_block` projects onto the nearest representable field. MEASURED on the
random and smooth synthetic fields `test_strippedterrain.py` builds — not on
anything retail, which is already on the lattice by construction: the worst
sample moves **4 world units**, against a **96.0**-unit cell pitch and a corpus
height range of about 25,000. It is a real quantisation and it is negligible;
both halves belong in the record. What it does to a *Blender-sculpted* field of
the kind §32 produces is untested.

An encoder that TRUNCATED instead of refusing would move a height by a fraction
of a unit, encode cleanly, and round-trip — and byte-identity could never see it,
because such an encoder is only ever run on retail blocks already on the lattice.
`_forward4` refuses; `test_strippedterrain.py` builds the truncating version and
requires the two to disagree off the lattice and agree exactly on it.

### What this does NOT establish

1. **Nothing authored by this codec has been through the client.** Everything
   above is a claim about a file format, checked against the archive. The E3
   experiment that would close it — author a Stripped terrain chunk, zero the
   Bloated stream, and watch the client compile — has not been run.
2. **The lightmap generator was not reproduced.** 0x0075CC30 was identified, not
   read. We know tag 9 is baked; we cannot predict its bytes, and nothing here
   needs to, because the client bakes it.
3. **The shadow record is carried through this codec's own boundary.** Tag 7
   goes through `terrain.ShadowBlock`, so its 272x272 bitmap is decoded and its
   128-byte tail derived — but `trnshadow` owns that, and nothing here re-read
   `TrnCodecShadow`'s stripped reader at 0x0074AAE0 to check that the two agree
   for a reason rather than by construction.
4. **Whether a tag-7-less or table-less map loads was not tested.** Both records
   are optional in the pipeline and no corpus map omits them.
5. **The Huffman construction is ours.** `HuffmanTable.for_frequencies` builds a
   legal table, not ArenaNet's. Nothing in the image builds one — there is no
   `TrnDataStrip` in the assert census — so an authored chunk will be a different
   size from what their tool would emit, and how different is unmeasured.

## 38. OBSERVED: the client compiled a navmesh over ground WE authored (2026-08-12)

**The rung the whole E3 ladder was built for.** A height field written by
`strippedterrain.py` — never in any archive, exactly representable on the
transform's lattice — went into a map's Stripped stream, and the retail client
compiled a navmesh from it. **The mesh stops at world x = 1152.0, which is the
cell boundary we authored, to the unit.**

Run 2026-08-12, `vault/research/e3-terrain-2026-08-12/`, on
`vault/run/2026-07-29_221c13772c7a-c2/Gw.dat` (a copy; `dat_study` and `C:\gw`
were read-only throughout). `PREDICTION.md` in that directory was written before
anything was armed and is quoted rather than reconstructed below.

### The design, and why its null result is a measurement

This is §36's experiment with one thing changed. §36 wrote row 46197's Stripped
stream — the 32x32 ladder template — into map 143's Stripped slot with map 143's
Bloated stream zeroed, and watched the client build **the donor's map**,
byte-identical to what ArenaNet shipped. So the "compiler ignored our change"
outcome is not a prediction here. It is a run that already happened.

**The one change: the height field of chunk `0x10000002`.** Nothing else — same
dims, same tag 0 fields, same tile indices, same two tile tables, same tag 3,
same shadow blocks, and the other seventeen chunks byte-identical, asserted by
re-decoding the whole container and diffing chunk by chunk.

| grid | stored height | what it is |
|---|---|---|
| `gx < 12` | sawtooth **−13 / −1013** on `(gx+gy) & 1` | slope **86.1°** per triangle |
| `gx >= 12` | flat **−13** | the donor's own height, unchanged |

The 86.1° is computed from the ±96.0 quad corner spacing FINDINGS 34 read out of
`0x0072CFD0`, and is over every threshold in both of that section's sets
(10/45/40° and 15/35/30°). The field snapped to the lattice with **worst move 0**,
so what follows is a claim about the client and not about our quantiser.

### The predictions, recorded before arming

* **P1** `Gw.log` emits the re-bloat line.
* **P2** the rebuilt Bloated terrain holds our field exactly, 1,024 of 1,024.
* **P3** the rebuilt map differs from §36's `4178b052…`.
* **P4 — the decisive one** the walkable-area share in `x < 1152` falls from
  **37.3% to under 5%**. *"If the compiler ignores our terrain and builds from
  props, zones and collision alone, that share stays near 37.3% and P4 fails
  while P2 may still pass."*

### The result

`Gw.log`, on a file cleared before the run so the line could not be §36's:

```
Perf: Map file '0x0287d3' failed to load.  Attempting to re-bloat.
```

| | control (§36, OBSERVED) | this run |
|---|---|---|
| terrain samples equal to ours | — | **1,024 / 1,024** |
| map payload / sha | 8,471 B `4178b052f0037fa8` | 8,471 B **`a1087453ef8ebb65`** |
| Path chunk | 419 B, 1 plane, 2 trapezoids | 419 B, 1 plane, 2 trapezoids |
| **trapezoid x extent** | **0 .. 3072** | **1152 .. 3072** |
| walkable area | 9,414,144 | **5,898,240** |
| **walkable area with x < 1152** | **3,515,904 (37.3%)** | **0 (0.0%)** |

All four pass. **P4 did not merely clear its threshold, it went to zero**, and
5,898,240 is exactly the control's `x >= 1152` portion — the flat half came
through untouched while the sawtoothed strip left the mesh entirely.

**1152.0 = 12 × 96.** The compiler cut the navmesh at the cell boundary we
chose. That is not a statistical result about a region; it is an exact
coincidence between an authored grid column and an emitted float.

### The trap this run walked into, and the only reason it is legible

**The trapezoid count did not change. Two before, two after, 419 bytes both
times.** A comparison on counts — which is what `rebloat.py --verify` prints and
what the first draft of this experiment would have used — reads this run as
"nothing happened". `PREDICTION.md` named that failure mode before the run
(*"Comparing trapezoid counts without comparing geometry… the area split is the
measurement"*) and the area split is what carries the finding.

Worth stating plainly because it cuts the other way too: §35 and §36 both
reported matching counts as corroboration, and a count is weak evidence in both
directions.

### What the flood does with slope, from the other side

FINDINGS 34 read the classifier out of x86 and could not say which mode flag was
in force. This run does not settle that either — 86.1° is unwalkable under both
sets by design, chosen so the result could not depend on the answer. What it
does establish is that **the classifier runs on the height field at all**, on
one flood cell per terrain cell, with the boundary landing on a cell edge.

### Archive hygiene

Post-flight `datcheck --diff`: TIER 0 descriptor counter 26,881 → 26,886 and the
MFT moved; TIER 1 five relocations — our rows 71496 and 71497 plus the client's
own scratch rows 8315/8316/8317, the baseline churn C2 established and which
moved in every arm of that rung. TIER 2 (the directory invariant) unchanged both
ways. All three CRC rules pass after.

Row 71496 was rebuilt into `0x3B2DC00` — **the address row 8317 had just
vacated**, which is the MFT-derived coalescing free map of FINDINGS 18.11 doing
exactly what it is documented to do.

Both journals are marked `.CONSUMED.json` and the copy was re-cut from
`dat_study`, verified back to MFT self-crc `0x9BFFD25C` with rows 46197, 71496
and 71497 at their original sizes and CRCs. Reverting after the client relocated
rows would corrupt rather than restore.

### A defect this experiment's own review found, and it was not in the experiment

An adversarial review of the runsheet raised 39 objections across four lenses; 22
were judged and **one survived**, and it was about the repo rather than the run:
`datwrite.py` — the only tool that opens the archive `r+b` — did **not** refuse
`vault/dat_study`. `rebloat.guard_target()` had refused it since that tool
existed and its docstring claimed datwrite did too. No checksum catches the
mistake: `--replace` fixes the entry CRC and the MFT self-CRC as it goes, so a
mutated snapshot verifies clean forever. Closed by `datwrite.guard_source()` on
`Writer.__init__` — deliberately not inside `guard()`, which `revert()` shares,
because replaying a journal is the one legitimate write to `dat_study`.
`test_datwrite.py` section 0b pins all three facts.

### What this does NOT establish

1. **Only the terrain is ours.** The props, zones, collision and Map Parameters
   in this map are ArenaNet's. FINDINGS 34's props hard gate was satisfied by
   their data, not ours.
2. **32x32, one plane, one run.** Nothing here says a large or multi-plane
   authored field compiles, and n = 1.
3. **Nothing walked the mesh.** The run passed its checkpoints and spawned at
   (1536, 1536) — inside the surviving half by design, so the spawn could not
   fail for the wrong reason — but no collision against the new edge at 1152 was
   observed. That the trapezoids stop there is a fact about the emitted chunk,
   not about where a character can stand.
4. **The walkability mode flag is still NOT FOUND.** This run was built so the
   answer could not matter.
5. **The large-map wall stands.** `datwrite --replace` writes uncompressed and
   refuses to relocate, so an authored stream only fits where it is smaller than
   the row's existing reservation. Map 143's own 64x64 file is 12,495 B
   uncompressed against a 4,608-byte reservation — the first design of this
   experiment, recorded in `PREDICTION.md` and killed by it. **Until something
   can compress a stream the way ArenaNet's archive does, authoring is confined
   to maps that shrink.**
6. **This is still the repair path.** An authored map must ship a broken or
   absent stage 2 to be compiled at all, and every run of one mutates the archive
   it is given.

## 39. OBSERVED: the client read a row we relocated 1.6 GB (2026-08-12)

**`datmove.py` shipped with one standing caveat — *no client has ever read a row
this module moved* — and this retires it.** Map 143's Stripped partner was moved
from `0x63C66800` to `0x323A400`, stored uncompressed instead of compressed, and
the client found it, compiled from it, and produced **ArenaNet's shipped map to
the byte**.

Run 2026-08-12, `vault/research/e9-datmove-2026-08-12/`, on
`vault/run/2026-07-29_221c13772c7a-c2/Gw.dat`. `PREDICTION.md` there was written
before any write.

### The design, and why its control was already measured

FINDINGS 35 zeroed map 143's Bloated stream and watched the client rebuild it
from row 71497 — 33,021 B, sha `acfc8e7501e94b9e`, 27 trapezoids, byte-identical
to ArenaNet's ship. In that run row 71497 sat where ArenaNet put it.

This run changes **where those bytes live and nothing else about them**.

| row 71497 | FINDINGS 35 | this run |
|---|---|---|
| content | 12,495 B decompressed | **identical**, sha `1438cbdb9d50682a` |
| offset | `0x63C66800` | **`0x323A400`** — 1.6 GB earlier |
| stored | 4,544 B, compression 8 | 12,495 B, **compression 0** |
| reservation | 4,608 B | 12,800 B |

Compression 0 and a changed size were already established by FINDINGS 36, which
wrote a stored payload into this same row with `datwrite --replace`. **The one
property this run adds is the offset**, which is the one `datwrite` refuses to
change and the one nothing had tested.

Placement came from `datmove --plan`, and on the real archive it reproduced
`datplan`'s own corpus figures: **208 usable runs, largest 953,856 B, 6 runs
withheld whole** for carrying container generations.

### The result — all three predictions

`Gw.log`, on a log moved aside first:

```
Perf: Map file '0x0287d3' failed to load.  Attempting to re-bloat.
```

| | predicted | observed |
|---|---|---|
| rebuilt payload | 33,021 B `acfc8e7501e94b9e` | **33,021 B `acfc8e7501e94b9e`** |
| mesh | 27 trapezoids, 1 plane | **27 trapezoids, 1 plane** |
| row 71497 after | still `0x323A400`, 12,495 B, comp 0 | **unchanged on all three** |

**The client followed a 1.6 GB relocation, read a stored row where a compressed
one had been, and emitted ArenaNet's own bytes.** The offset field in the MFT is
therefore load-bearing at load time and the client holds no cached address for a
map's partner row.

### One thing that reproduced without being asked

Row 71496 was rebuilt at **`0x4B82E00`** — the same address FINDINGS 35 recorded
for its rebuild of the same row. Two runs, days apart, with a differently-laid
archive between them, and the client's MFT-derived free map chose the same place.
That is consistent with the best-fit allocator FINDINGS 18 read at `0x00478C50`
and is the closest thing to a corroboration of it we have, though it is **one
coincidence and not a measurement** — nothing here varied the free map on purpose.

### Archive hygiene

Post-flight: descriptor counter 26,881 → 26,886; five relocations — rows 71496
and 71497 plus the client's scratch rows 8315/8316/8317, the same baseline churn
every arm of this rung has shown. TIER 2 (the directory invariant) unchanged both
ways. **`datmove --check-overlaps` reports 0 overlapping row pairs after a client
session on a relocated archive**, which is the invariant `test_datmove.py` is
built around, now checked against a real 4.2 GB archive the client has written to
rather than a fixture.

Both journals marked `.CONSUMED.json` and the copy re-cut from `dat_study`.
`dat_study` and `C:\gw` were read-only throughout, with `guard_source()` live.

### What this does NOT establish

1. **One row, one map, one load.** A relocation the client tolerates at load
   time is not one that survives a play session.
2. **Nothing watched the freed space.** The move released 4,608 B at
   `0x63C66800` and the arm released more; FINDINGS 18 records the client
   relocating and resizing its own rows during ordinary play, and whether it
   reclaims those blocks — and what that does to a row we moved — was not
   observed.
3. **The relocated row was ArenaNet's own content.** This says the client
   follows the offset; it says nothing new about authored bytes, which is
   FINDINGS 38's result and a different question.
4. **The capacity limit is untouched by this.** 176 of 349 map rows are still
   larger than the largest run `datplan` will hand over. Relocation makes
   authoring possible where a run exists, not everywhere.

## 40. A relocated row survived four client sessions — and the movement half did not run (2026-08-12)

**FINDINGS 39's remaining caveat, half-answered.** A row moved by `datmove.py`
stayed exactly where it was put across four consecutive client sessions and was
still functionally readable at the end. **The other half of the design — a
session with the character actually moving — did not happen, and the write-up
below says so rather than rounding it up.**

Run 2026-08-12, `vault/research/e9b-durability-2026-08-12/`, on the `-c2` copy.
`PREDICTION.md` there was recorded before any write.

### The design problem this rung had to solve first

**Row 71497 is a map's STRIPPED partner, and the client only reads it when
re-bloating.** An ordinary load reads the Bloated stream and never touches it. So
"the row is unchanged after N sessions" is worth nothing on its own — it is
exactly what you would see if the client's allocator never ran at all.

**The control is rows 8315/8316/8317**, the client's own scratch rows, which
FINDINGS 20, 35, 38 and 39 each recorded relocating every session.

### What ran

Row 71497 moved `0x63C66800` → `0x323A400`, uncompressed, 12,495 B — the same
move as FINDINGS 39 — then four client sessions, **no arming for the first
three** so they were ordinary loads.

| after | row 71497 | payload sha | scratch rows | freed range |
|---|---|---|---|---|
| the move | `0x323A400` | `1438cbdb9d50682a` | 8315 `0x461AA00`, 8316 `0x3983600`, 8317 `0x3B2DC00` | empty |
| session 1 | **unchanged** | **unchanged** | **all three moved** | empty |
| session 2 | **unchanged** | **unchanged** | 8315/8316 moved BACK, 8317 held | empty |
| session 3 | **unchanged** | **unchanged** | 8315/8316 moved again | empty |
| session 4 (armed) | **unchanged** | **unchanged** | — | empty |

**P1 (control) PASSED**: the allocator was demonstrably live in every session,
and 8315/8316 alternating between two address pairs across sessions 1→2→3 is the
double-buffer FINDINGS 18 describes, seen here from the row side.

**P2 PASSED**: row 71497 never moved and its payload sha never changed.

**P3 PASSED**: after all of it, arming row 71496 and loading once more produced
ArenaNet's shipped map again — 33,021 B, sha `acfc8e7501e94b9e`, 27 trapezoids.
So the row was not merely bytes in place; it was still the row the compiler
reads.

Post-flight: descriptor counter 26,881 → **26,895** (fourteen, against five for a
single session), five relocations, TIER 2 unchanged, and
`datmove --check-overlaps` reports **0 overlapping pairs** on the real 4.2 GB
archive after four sessions.

**The freed 4,608 B at `0x63C66800` was never claimed** by anything, in any
session. No prediction was made on that and none is drawn from it: nine blocks in
a 4.2 GB archive over four short sessions is very little opportunity.

### THE MOVEMENT SESSION DID NOT RUN, and this is the honest part

Session 3 was supposed to be the different one — `--walk "W:6 D:4 S:5 A:4"`,
19 seconds of held keys — so that the run was not four identical loads. It was
not:

* `W:6` and `D:4` completed in full (10.0 s).
* The client then **lost the foreground**, and `S:5` and `A:4` were cut to
  **1.50 s each** by `hold_key`'s own foreground check.
* `content/npcs.toml`'s `[npc.hatcher]` — **our own server's** NPC, spawned
  hostile at (1536, 1836), 300 units from the spawn point — was attacking
  throughout. The gamesrv log records **7 damage events and
  `player hit by skill 253: 0/100`**. The character died.
* **Session 3 is the ONLY one of the four with any damage at all**; the other
  three record zero. It is also the only one that moved, which is the obvious
  explanation and is not established here.

So the intended contrast — three loads plus one session of movement — collapsed
to four sessions of which one had 10 seconds of movement and a death. **A death
is more client activity rather than less**, so this does not weaken P1, P2 or P3,
all of which are facts about the archive and about a control that fired
regardless. What it does mean is that **movement-driven client writes remain
untested**, and any later claim that "walking around does not disturb a relocated
row" is not supported by this run.

*This section originally described session 3 as a session with the character
moving, and the death was noticed only because the owner said so mid-run. The
log had it the whole time. Recorded rather than edited away: the failure was
treating an in-game event as irrelevant to an in-game measurement because it was
irrelevant to the archive measurement sitting next to it.*

### What this does NOT establish

1. **Four short sessions on one map is not a play session.** No zoning between
   maps, no inventory writes, no character save, no clean movement.
2. **Nothing pressured the allocator.** The freed range stayed empty, so this
   run never observed the client *wanting* space near our row. A durability test
   that forces an allocation is the stronger version and has not been built.
3. **One row, one map, one archive copy.**
4. The relocated content was ArenaNet's own; this says nothing further about
   authored bytes beyond FINDINGS 38.

## 41. OBSERVED: what the compiler actually needs is SEVEN chunks, and FINDINGS 34 named the wrong set (2026-08-12)

**Rung E10a.** FINDINGS 34 read the mandatory input set off the client's
instructions. This measures it against the client, one removal at a time, and
the disassembly was wrong in both directions: it missed a chunk that is required
and listed one that is not. **A Stripped map needs 7 of its 18 chunks to compile
to a navmesh**, and the mesh is byte-identical to the full map's.

Run 2026-08-12, `vault/research/e10a-minmap-2026-08-12/`, six client sessions.
Donor row 46197 (18 chunks, 2,951 B), written into map 143's Stripped slot with
the Bloated stream zeroed — the FINDINGS 36 setup, whose own compile is OBSERVED
three times over: 8,471 B, Path 419 B, 1 plane, **2 trapezoids**.

**The surgery tool's control**: keeping all 18 chunks reproduces the donor
byte-identically, so any later difference is the removal and not the tool.

### The runs

| # | chunks | change | outcome |
|---|---|---|---|
| 1 | 7 | FINDINGS 34's predicted set | **CRASH** — `deps`, TrnCreate:242 |
| 2 | 8 | + Terrain Dependencies `0x11000002` | **COMPILES** 7,833 B, Path 419 B, 2 traps |
| 3 | 7 | − Collision `0x1000000E` | **COMPILES** 7,816 B, Path 419 B, 2 traps |
| 4 | 6 | − Zones `0x10000003` | **CRASH** — `state->zones`, MapData:660 |
| 5 | 6 | − Props `0x10000004` | **no crash, NO REBUILD**, `Error: Creating default map` |
| 6 | 6 | − Path `0x10000008` | **COMPILES** 7,389 B — but **NO MESH** |

### The minimal set, MEASURED

| chunk | bytes | |
|---|---|---|
| `0x10000000` Header | 8 | |
| `0x1000000C` Map Parameters | 41 | |
| `0x10000004` Props | 12 | hard gate |
| `0x10000003` Zones | 34 | must precede Terrain |
| `0x10000002` Terrain | 2,123 | ours since §37 |
| `0x11000002` Terrain Dependencies | 29 | **§34 missed this** |
| `0x10000008` Path | 27 | ours since §33 |

**2,274 B of the donor's 2,951.** Everything outside terrain and path is
**124 bytes**, which is what an authored map has to supply beyond the two chunks
we can already write.

### Three corrections to FINDINGS 34

1. **`0x11000002` is REQUIRED and was not on the list.** Without the terrain's
   own Dependencies chunk the builder asserts `deps`.
2. **Collision `0x1000000E` is NOT required.** The list has it under "required by
   the surrounding machinery"; removed, the map compiles to the same mesh. Its
   9-byte stub satisfies `state+0x30` for something the Path builder does not
   need.
3. **Order matters, and nothing had said so.** Both crashes fire from inside the
   TERRAIN bloat handler (`s_chunkInfo[0x02].bloat = 0x00711EC0`; the caller
   frames resolve to `0x00711F6F` and `0x00711F93`, which bracket §34's
   `0x00711F72 mov [esi+0x2c],eax`). **Terrain bloat reads `state->zones`**, so
   Zones must be processed BEFORE Terrain. The donor's file order already does
   — Props, Zones, Collision, Terrain — and an authored map must too.

### Four failure signatures, and they are all different

This is the part a disassembly could not have given, and each is diagnostic:

* **assert `deps`** — a chunk the terrain builder dereferences is absent.
* **assert `state->zones`** — a converter-state field its consumer requires.
  §34 named that struct `state` from assert text and mapped +0x28 to zones by
  disassembly; the client has now named `state->zones` itself, which is
  corroboration from the other side.
* **`Error: Creating default map`, no rebuild, NO CRASH** — the props gate. §34
  read it as `cmp [ecx+0x24],0 → je return 0`, an early return rather than an
  assert, and that is exactly what it looks like from outside.
* **a rebuild with no `0x20000008` at all** — the Stripped Path chunk is the
  carrier the pipeline is driven from (§33, §34 pass 1). Remove it and the
  converter still runs and still writes a map; there is simply no mesh in it.

### A trap this run walked into

**Run 5's harness verdict was `RUN VERDICT: PASS`.** The client reached a map and
put a body in it — the DEFAULT map, because ours would not load. A harness pass
means the client got somewhere, not that it got where we sent it. The archive is
the instrument; the verdict is not.

### Method notes

**`mapbuild.gates()` cannot pre-filter a stage 1 map.** Its seventeen rules
demand `0x2000000C`, `0x20000002` and `0x20000008` and assert every chunk is
stage 2, so an UNMODIFIED retail Stripped map fails five of them. That is the
function working correctly on the wrong input. The control caught it before any
client was spent; trusted, it would have refused every variant here and reported
nothing.

**The harness captured neither crash dialog** — no `final.png`, no crash text in
either capture directory. Both were read off the screen by the owner.
`test_harness.py`'s claim that the crash-dialog capture is the only
machine-readable evidence an assert leaves is exactly right, and on these two
runs it produced none. That is a gap in the harness, not in the result, and it
is why both asserts are recorded here from a transcription.

### What this does NOT establish

1. **Header, Map Parameters and Terrain Dependencies were never removed.** They
   are in the minimal set because they were never tested out of it, not because
   a run showed they are required. Three runs would settle it.
2. **One map, 32x32, one plane.** A larger or multi-plane map may need more.
3. **"Compiles" is not "is correct".** The 7-chunk variants produce a mesh
   byte-identical to the full map's, but nothing walked any of them, and a map
   missing ten chunks is missing textures, sound, environment and light — this
   says what the COMPILER needs, not what a playable map needs.
4. **The removals are not independent.** Each run removed from the previous
   surviving set, so an interaction between two removed chunks would not show.

## 42. The minimal set, completed — and the loader NAMES the chunk it is missing (2026-08-12)

**Closes FINDINGS 41's two open ends and corrects one of its claims.** All seven
members of the minimal set have now been removed individually. More useful than
the answer: **the client reports which chunk it could not use, by name**, and
FINDINGS 41 missed that because it read the last line of `Gw.log` instead of the
last four.

### The full removal table

Every row is one client session against the FINDINGS 36 setup. The set is
Header, Map Parameters, Props, Zones, Terrain, Terrain Dependencies, Path.

| removed | re-bloat attempted | what the client said | mesh |
|---|---|---|---|
| Terrain Deps `0x11000002` | yes | assert **`deps`**, TrnCreate:242 | — |
| Zones `0x10000003` | yes | assert **`state->zones`**, MapData:660 | — |
| Map Parameters `0x1000000C` | yes | assert **`dims.x * XY_DIST == context->mapRect.x1 - context->mapRect.x0`**, TrnDataBloat:191 | — |
| Terrain `0x10000002` | yes | `corrupt chunk 'Terrain Stripped Data'` | — |
| Props `0x10000004` | yes | `corrupt chunk 'Path Stripped Data'` | — |
| Path `0x10000008` | yes | *(nothing)* — rebuilt 7,389 B | **NO Path chunk** |
| Header `0x10000000` | **no** | `missing chunk 'Header Stripped Data'` | — |
| Collision `0x1000000E` | yes | *(nothing)* | **419 B, 2 traps** |

**All seven are required.** Collision is the only chunk of FINDINGS 34's list
that is not.

### Three things this adds

**1. The loader names the chunk.** `Error: Map '0x0287d3' missing chunk 'Header
Stripped Data'` and `corrupt chunk 'Terrain Stripped Data'` are the client
telling us its own requirement in its own words. It distinguishes *missing* from
*corrupt*, and — measured here — an absent Header is "missing" while an absent
Terrain or Path is "corrupt", so the two words are not synonyms for absence.
This is a far better instrument than watching for a rebuilt row, and it was
available from run 1.

**2. The Header is refused BEFORE the re-bloat; everything else after.** Its row
is the only one with no `Attempting to re-bloat` line. So there are two distinct
stages of requirement — what the container needs to open at all, and what the
converter needs to run — and only the Header sits in the first.

**3. The rect invariant is the client's own expression.** Removing Map
Parameters leaves the rect zeroed and the terrain bloat asserts
`dims.x * XY_DIST == mapRect.x1 - mapRect.x0`. That is `terrain.py`'s cell pitch
of 96.0, measured from the archive as `rect/dims` on 349 of 349 maps, now stated
by the client. **`XY_DIST` is ArenaNet's name for it.** It is also a hard
authoring rule: an authored map's rect must equal `dims * 96.0` exactly, or the
converter asserts rather than compiling something wrong.

### The correction to FINDINGS 41

That section reported the props removal as *"`Error: Creating default map`, no
rebuild, NO CRASH — the props gate, exactly as §34 read it"*. The mechanism
reading survives; the evidence quoted for it does not. Re-run with the whole log
read, the props removal says:

```
Perf: Map file '0x0287d3' failed to load.  Attempting to re-bloat.
Error: Map '0x0287d3' corrupt chunk 'Path Stripped Data'
```

So the re-bloat runs, the Path builder produces nothing (consistent with §34's
`cmp [ecx+0x24],0 → je return 0`), and the loader then rejects the map because
the Path chunk is unusable. **`Creating default map` is the third line of that
sequence, not the finding.** §41 read `tail -1` and reported a conclusion the
next three lines would have sharpened — the same shape as the trapezoid-count
trap that section itself warns about.

### The harness gap, closed

FINDINGS 41 recorded that neither crash dialog was captured and both were read
off the screen. **The extraction was never broken.** `capture_error_dialog`
finds the dialog, and the assert text sits in a hidden `Edit` control (id 1003)
that is readable without clicking anything — which matters, because the control
next to it is **`&Send report to ArenaNet`**, and clicking in that dialog would
upload a crash report from a patched client to the vendor.

What was missing was a CALL SITE: `capture_error_dialog` was reachable only from
`hold_open()`, which `run_client` invokes under `if a.keep_open:`. A plain
`--hold N` run never called it. It is now called unconditionally in
`run_client`'s `finally`, **before** `dc.close_client`, which destroys the
dialog. Both of this section's asserts — `dims.x * XY_DIST ...` and `deps` —
were captured automatically by that path on ordinary runs, which is the check
that it works.

`test_harness.py` asserts the call on the SYNTAX TREE rather than by grep,
because "in the finally" and "before close_client" are both invisible to a text
search, with a control that the ordering test fails on a reversed finally.

### What this does NOT establish

1. **One map, 32x32, one plane, and removals are not independent** — each run
   removed from the previous surviving set, so an interaction between two
   removed chunks would not show.
2. **"Required" here means "this map would not compile without it"**, not that
   the chunk's CONTENT matters. Every removal used ArenaNet's own bytes for the
   chunks that stayed; nothing yet says a minimal or authored Zones or Props
   would satisfy the same gates.
3. The `missing`/`corrupt` distinction is measured on four chunks, not
   systematically — it is a lead about the loader's vocabulary, not a rule.

## 43. OBSERVED: the retail client compiled a map we ASSEMBLED — rung E10 (2026-08-12)

**The arc's destination.** A whole Stripped map built from typed parameters —
**97.69% of its bytes generated**, 54 borrowed across three named chunks — went
into the archive with its Bloated stream zeroed, and the retail client compiled
it into a navmesh that follows the ground we wrote. All four predictions, all
recorded before arming, passed.

And it cost one failure that was worth more than the success: **the Stripped
Path chunk's boundary point is a flood SEED, and it must stand on walkable
ground.**

Run 2026-08-12, `vault/research/e10-authored-2026-08-12/`.

### What was assembled

Seven chunks, FINDINGS 42's measured requirement, in the donor's own order.

| chunk | bytes | origin |
|---|---|---|
| `0x10000000` Header | 8 | borrowed |
| `0x1000000C` Map Parameters | 41 | **generated** — `mapbuild.encode_map_parameters` |
| `0x10000004` Props | 12 | borrowed (§34's hard gate) |
| `0x10000003` Zones | 34 | borrowed |
| `0x10000002` Terrain | 2,188 | **generated** — `StrippedTerrain.build` from a height field |
| `0x11000002` Terrain Dependencies | 29 | **generated** from 4 file ids read at run time |
| `0x10000008` Path | 27 | **generated** |

**2,400 B. GENERATED 2,285 (97.69%), BORROWED 54 (2.31%).** The three borrowed
chunks are read from the owner's archive at run time and never stored in this
repo — `mapbuild.py`'s pattern for FINDINGS 14's five, and the builder refuses
(`NoConstants`) without an archive.

**The dependency chunk is generated and lands byte-identical to the donor's**,
built by `mapchunks.encode_dependencies` from the four ids `[17246, 23369,
22972, 22269]` read at run time. Ids are measurements and CLAUDE.md's ruling
permits them; the bytes are ours.

Two of FINDINGS 42's rules are obeyed by construction rather than by luck: Zones
precedes Terrain, and the rect is DERIVED as `dims * 96.0` so
`dims.x * XY_DIST == mapRect.x1 - mapRect.x0` holds.

### The failure, and what it taught

The first build put the Path chunk's single boundary point at the rect's corner,
`(0, 0)`. The client asserted:

```
Assertion: segments->Count()          PathData:365
```

Zero segments for the decomposition. The height field was FINDINGS 38's, which
had already compiled — so the terrain was not the difference. Diffing our four
generated chunks against the donor's semantically found it:

| | donor | ours |
|---|---|---|
| Terrain Dependencies | 4 ids | **byte-identical** |
| Map Parameters | `-0.0` origin, real UUID | `0.0`, zero UUID, **same flags** |
| **Path boundary** | **(1472.0, 1564.0)** | **(0.0, 0.0)** |

The donor's point is in its walkable interior. Ours was at a corner which, on
this height field, is **inside the sawtooth and unwalkable**. Moving it to
(2112, 1536) — in the flat half, nothing else changed — compiled.

**So the boundary point is a seed for the flood, and seeding it on unwalkable
ground produces no segments at all.** FINDINGS 34 read pass 2's callees as
seed/flood/contour and labelled that INFERRED from call structure; this is the
first observation of the seed behaving like one. It is also a hard authoring
rule, and it is not discoverable from the corpus: every retail map's point is
already somewhere sensible.

*This does not overturn FINDINGS 33.* That section showed the boundary is
CARRIED into the Bloated chunk rather than compiled from, and that one point
suffices — both still hold. What is new is that the point is also USED, and
where it sits matters.

### The result

`Gw.log`: the re-bloat line and nothing else — no error, no assert.

| | predicted | observed |
|---|---|---|
| **P1** no crash, map rebuilt | — | **7,814 B, 7 chunks** |
| **P2** our height field, exactly | 1,024/1,024 | **1,024/1,024** |
| **P3** a Path chunk exists | yes | **419 B, 1 plane, 2 trapezoids** |
| **P4** mesh confined to the flat half | `x < 1152` under 5% | **0.0%**, extent **1152..3072** |

The mesh is the same one FINDINGS 38 produced — 419 B, 2 trapezoids, extent
1152..3072, walkable area 5,898,240 — but from a map this repository assembled
rather than from an edit of ArenaNet's file.

### What this does NOT establish

1. **54 bytes are still theirs**, and one of them is the props chunk that
   satisfies §34's hard gate. **No map here has authored props**, so nothing has
   been placed in a world we built, and the props record format remains
   unread (342 distinct sizes over 349 maps).
2. **Nothing walked it.** The character spawns at (1536, 1536), inside the flat
   half by design. The mesh's edge at 1152 is a fact about the emitted chunk.
3. **32x32, one plane, one run**, and the map has no textures, sound,
   environment or light — this is what the COMPILER accepts, not a playable map.
4. **The seed reading is one observation.** A corner seed on a map whose corner
   is walkable was not tried, so "unwalkable seed" rather than "corner seed" is
   the better-supported of the two readings but not the only one.
5. The `-0.0` vs `0.0` rect origin and the zero UUID differ from the donor's and
   were NOT isolated; they rode along in both the failing and succeeding builds,
   so neither is implicated and neither is cleared.

## 44. The props chunk, read — and the survey that said it could not be (2026-08-12)

**`0x10000004` decodes and re-encodes byte-identically, 349 of 349.** It was the
last chunk `stripbuild.py` borrowed and the only one that mattered: §34 makes it
a hard gate, so while it was borrowed a map from this toolkit could have our
ground and **not one tree, wall, door or portal standing on it**. `BORROWED` is
now Header and Zones alone — 42 bytes, and 98.20% of the map ours.

The record is **variable length**, which is why `PROPS.md`'s survey found no law
and correctly refused to invent one.

### The layout

    u32 signature 0x39583392
    u8  version 17
    u8 0   u16 n     n prop records, each 20 + 4*points bytes:
                         u16 model
                         f32 x, y, z
                         u32 extra                 (meaning UNVERIFIED)
                         u8  flags
                         u8  points
                         (i16 dx, i16 dy) * points -- a CLOSED outline
    u8 4   u16 n     n * {u16 value, u16 prop}
    u8 6   u8 word, u16 n   n * {u16 value, u16 prop}      (optional)
    u8 255           terminator, and the last byte of the chunk

**285,670 props over 349 maps.** 37,548 carry an outline; 37,505 of those return
to their first point and **43 do not**, which is recorded rather than rounded
away. 262 maps carry a tag-6 section; 87 carry none at all, which is a different
file from the 114 that carry it empty.

### Why the earlier survey found nothing, which is the useful part

`PROPS.md` tested `9 + n*k` and `12 + n*k` for every stride to 200 and got 0/349
every time. **Both readings were wrong in the same way and neither was careless.**
A fixed stride cannot close on a variable-length record, so the whole family of
tests was doomed before it ran; and the count it read was a `u32` at +5, which
straddles the tag byte, so on a chunk holding **no props at all** it reported
262,144. The two smallest chunks it reasoned from are the two least informative
in the corpus — 12 bytes and 16 bytes, both entirely empty sections.

`PROPS.md` was right to stop where it did. What it was missing was not effort but
a **bigger sample**: the structure is plain in any map with real content, and
invisible in the two it had.

### How each field was pinned, because a walk that closes proves nothing

A tolerant walk closes on anything, so none of the below rests on the walk.

* **The stride came from an oracle in a chunk this codec never reads.** Slide a
  window over the raw bytes and keep every offset whose float pair lands inside
  the map RECT, which lives in Map Parameters `0x1000000C`. Pooled over twelve
  maps the gap histogram is **49.1% gap-4 and 40.9% gap-16, alternating** — two
  in-rect pairs per record, 4 + 16 = **20** — and the first hit is at offset
  **10** in all twelve, which is what puts a u16 in front of the floats.
* **Tag 6's extra header byte was forced by the data.** Read as
  `{u8 tag, u16 count}` its count came out 0, 256, 512, 768 … a multiple of 256
  every time. One more byte moves it into place, and that is also exactly what
  makes the 16-byte chunk close: `06 00 00 00 FF` is tag, word, count 0,
  terminator.
* **Tag 6's stride is uniquely determined.** 4 closes 349/349. 1, 2, 6, 8, 12,
  16 and 20 each close 200/349 — precisely the maps whose tag-6 count is zero,
  where the stride cannot matter. **The 149 maps with a non-zero count are the
  measurement**; without them the sweep would have been vacuous, which is why
  the test asserts the sample contains one.
* **The alignment is uniquely determined.** Putting the model u16 at the END of
  the record and giving tag 0 a five-byte header shifts section 0 by exactly two
  bytes and is otherwise self-consistent — it is what a stride-20 hexdump
  suggests, and a version of it is what `PROPS.md` was written under. It closes
  for **0 of 349**, and is kept as a control.
* **Tags 4 and 6 index the prop array.** The corpus had 17,002 chances to say
  otherwise — 6,355 tag-4 and 10,647 tag-6 references — and every one lands below
  its map's prop count.
* **The oracle, on the whole corpus: 285,670 of 285,670 prop positions are
  inside their map's rect.** If the record layout were off by any amount the
  floats would be garbage.

### What the corpus cannot decide, asserted rather than glossed

Tag 6's count **must** be a u16: one map carries 611 entries. Tag 4's largest is
**81**, so `{u8 tag, u16 count}` and `{u8 tag, u8 count, u8 pad}` fit its bytes
equally well and **the corpus cannot separate them**. `test_props.py` asserts
both bounds, so the day an archive holds a map with 256 tag-4 entries the file
goes red and says the ambiguity is gone.

### The client, read AFTERWARDS — and it agreed

Everything above came out of the archive alone. The disassembly of build 38797
was done after the codec was written and could have refuted it; it did not, and
it settled the one thing the corpus cannot.

**`PROPS.md` was tracing the wrong reader, and that is why it got nowhere.**
There are two props chunks and two pipelines:

| | entry | reads | section header |
|---|---|---|---|
| `s_chunkInfo[0x04].load` | `0x00712200` → `0x0073CC80` | **Bloated** `0x20000004` | `{u8 tag, u32 size}` |
| `s_chunkInfo[0x04].bloat` | `0x00712280` → `0x0073E260` | **Stripped** `0x10000004` | `{u8 tag}` |

`PROPS.md`'s chain ends at `0x0073CC80` — the **Bloated** reader. No amount of
following it could have produced a framing that fits the Stripped bytes. Both
pipelines share one tag reader, `0x0073E410`, whose `fmt` argument picks the
header width (dispatch at `0x0073E433`); the Stripped side passes 1.

The Stripped pipeline is an eight-entry stage table at `0x00BF74B4`. Four stages
READ — tags 0, 4, 6 and 255 — and **that is exactly the set the corpus walk
found in 349 of 349 maps**, arrived at from the other side. Tags 1, 2 and 3 are
WRITE-only: the compiler generates them into the Bloated stream from tag 0.

What the code settles that the archive could not:

* **Tag 4's count is a u16** — `0x0073E1A6 movzx esi, word ptr [eax]`. The
  corpus could not decide this and `test_props.py` still asserts the ambiguity,
  because the ambiguity is a true fact about the corpus.
* **Tag 6's second byte must be ZERO** — `0x0073D8D3 cmp byte ptr [eax], 0`. It
  is a validated field, not padding, and `props.py` now refuses a non-zero one.
* **The `extra` u32 is FOUR bytes, not one field** — read at four separate
  addresses. Three (`0x0073DE88`, `0x0073DE6D`, `0x0073DE5D`) are `fild`-scaled
  and feed `0x0073B4C0`, which fills two 12-byte vectors: a packed rotation,
  INFERRED. The fourth (`0x0073DE2D`) is scaled into a float: a scale, INFERRED.
  The widths are measured; the meanings are not. *(Both readings are now
  CORROBORATED by the compiler's own output, and this sentence's two counts
  were corrected on the same day — §45: the scale byte is 0x7F on **135,079**
  props, not the 35,593 this line first claimed, which reproduces under no
  population; and "the rotation bytes are zero on 180,391" counts props with
  rot[0]==rot[1]==0 — a pure yaw — while all-three-zero is 46,371.)*
* **The outline is in PROP-LOCAL coordinates.** The client sign-extends each
  pair and adds the prop's own x and y back (`0x0073DF4F`, `0x0073DF67`).
* **The client's version gate accepts 0x11 AND 0x12** (`0x0073E224`,
  `0x0073E228`). The corpus is 0x11 on 349/349. `props.py` refuses 0x12 on
  purpose: no version branch was found in the framing, but "probably the same"
  is a guess.

Three independent reads and an adversarial refutation were run. The refuter
wrote its OWN walker from its OWN disassembly, sharing no code with `props.py`,
and reported: **the framing is correct and I could not break it.** Six factual
errors were found across the reports, all in citations and sample sizes; none
touched the format. Its walker consumed **349 of 349** to the exact byte and
reproduced 262 tag-6 maps, 285,670 props and 334,725 outline points exactly.

**THE CROSS-STREAM ORACLE is the strongest single result, and it is 349 of 349.**
The Bloated props record is 48 bytes with an 8-byte ring point where the Stripped
one is 20 and 4, and the compiler derives one from the other. So the Bloated
tag-0 section's declared size is predictable from the STRIPPED input alone:

    bloated_tag0_size == 2 + 48 * props + 8 * outline_points

**349 of 349, zero mismatches.** No walker can force that: it predicts a `u32`
in a stream it never reads. Its sabotage controls over 40 maps all went red --
stride 21 → 1/40, stride 19 → 1/40, count as u32 → 0/40, count as u8 → 0/40, no
trailer → 3/40, trailer stride 8 → 3/40, tag 6 mandatory → 19/40, tag 6 without
its pad byte → 21/40, against a 40/40 baseline.

Three details worth carrying:

* **Tag 6 is optional because the reader saves and restores the cursor**
  (`0x0073D891` / `0x0073D8A2`). The shared reader advances past the tag byte
  *before* comparing it, so a stage that may not match must back out by hand.
  That is why the 12-byte chunk parses at all: `0xFF` fails the tag-6 match
  without consuming a byte, and stage 7 then matches it. Read out of the code,
  not fitted to the file.
* **`model` is a filename index into chunk `0x21000004`** (`0x0073DE0E`), which
  is why it does not index tag 4 and why its pooled range is 0..439.
* **The rotation and scale bytes have formulas**: each angle is `b * 2*pi/256`,
  the scale is `b * (255/128)/256 + 1/128`, so scale runs [1/128, ~1.992] in 256
  steps. Constants at `0x00949D00`, `0x00946E80`, `0x00A70340`, `0x00953AB0`.

**The props gate FINDINGS 34 asserted is now read directly**, and there is a
second one it does not name. The Path bloat handler tests
`cmp dword ptr [ecx+0x24], 0` at `0x00712678` and returns 0 -- so a props chunk
that fails to bloat leaves the slot NULL and **silently kills the Path chunk**,
with no assert. The props load handler has its own gate at `0x00712207`
(`!map->props`, `MapData.cpp:976`), so the object hangs at `map+0x7C` and at
`state+0x24`.

### The correction the refutation earned: only tag 6 is optional

The first read said every stage restores the cursor on a mismatch, so every
section is optional. **That is false in both pipelines, and it was the one
sentence an authoring tool would act on.** Only tag 6's stage saves and restores
(`0x0073D891` / `0x0073D8A2`) and returns 1. Tags 0, 4 and 255 return 0 on a
mismatch, and the driver turns any 0 into total failure at `0x0073E33D` — so
`0x00712280` never builds the props object.

**The failure is silent, and that is why this matters.** With no props object,
`state+0x24` stays NULL, and the Path bloat gate at `0x00712678` returns 0
before it ever reaches the decomposition. No assert, no log line: just a map
that compiles with no navmesh. Our own tooling would have read that as "the
compiler ignored our mesh" and looked in entirely the wrong place.

`props.py` refused a chunk missing tag 0 or tag 4 as of this correction — it had
been more permissive than the client, which for an AUTHORING tool is the
dangerous direction. Retail carries both on 349 of 349, so the refusal cannot
fire on ArenaNet's files; `test_props.py` builds both malformed chunks and a
positive control (tag 0 + tag 4 + terminator with no tag 6, which 87 real maps
ship). The same mechanism forces ORDER as well as presence: the shared reader
advances the cursor *before* comparing the tag, so a stage that mismatches
without a save/restore has already moved it.

### What is still UNVERIFIED

1. **The rotation and scale readings are INFERRED**, from the client's
   arithmetic rather than from any assert or any measurement of an effect. ~~The
   tag-4 and tag-6 `value` words recur across maps, so they are ids rather than
   per-map hashes; also not measured.~~ **The `value` words are MEASURED as of
   2026-08-27 ([toolkit/mapdata/refscan.py](../../toolkit/mapdata/refscan.py),
   `test_refscan.py`, 17 checks) and the id reading holds for tag 4 only.**
   Recurrence was never able to separate the two — small indices collide across
   maps for the same reason small integers do — and the bound separates them at
   once: **tag 6's `value` is under `len(props)` on 10,647 of 10,647 rows** in
   149 maps, **tag 4's on 212 of 6,355** with values to 65,521. So tag 6's
   `PropRef` has BOTH words indexing the prop array and is a prop-to-prop
   relation, while tag 4's is the wide cross-map id namespace this item guessed
   at. The bound is not an artefact of scale: `max(value)/(len(props)-1)` runs
   to a median of **0.939** (p75 0.981, 90 of 149 maps over 0.9, 7 landing on
   `len(props)-1` exactly) against tag 4's median of **94.6**, and the shuffle
   control — re-scoring each map's values against another map's prop count —
   puts **32.2%** out of range, so the ceiling belongs to *this* map. Still
   NOT established: that the indexed array is the prop array rather than
   another per-map array of the same length, and what the relation means. Ten
   tag-6 rows are self-references, which a 40-map sample reported as zero. The
   rotation and scale readings above remain INFERRED and are untouched by this.
   The u16 at +0x00 is **not** an index into
   tag 4 — measured from both sides, 209,960 of 285,670 land outside it.
2. **Nothing has been PLACED yet.** `stripbuild.build()` takes a `props=`
   argument and defaults to `minimal()`, the empty chunk. That the client
   compiles a map with props WE authored — with a real model id and a real
   outline — is the next run, and it is not this finding.

### The check that would have caught a memcpy

The headline is the weak half and is reported that way. `test_props.py` builds
the saboteur — decode by stashing the blob, encode by handing it back — runs it,
and requires it to **pass** the 349/349 byte-identity while failing the three
mutation controls that grow a decoded chunk in place and require the emitted
counts to move. It is caught by 3 of 3, read back by a walker written in the
test out of `int.from_bytes` that imports nothing from the module.

`minimal()` — a props chunk authored from nothing, no archive and no donor —
is byte-identical to row 46197's, the smallest in the archive.

## 45. The Bloated props chunk, read — the oracle becomes a test, and (e10d) is staged (2026-08-12)

**Chunk `0x20000004` is read, read-only, and the cross-stream oracle is now
section 9 of `test_props.py`** — 349 of 349 under `--all` (110 checks, 718 s
measured), where it had lived only in §44's prose and a workflow scratchpad.
`props.BloatedProps` is the reader; it deliberately has NO `encode` (the test
asserts that), because five of its six sections are carried opaquely and a
round trip could only be a memcpy wearing a headline.

### The framing, measured from the archive

Header is **5 bytes** — u32 `0x39583392`, u8 version 17, the SAME pair the
Stripped chunk opens with, where Bloated TERRAIN has an 8-byte `<II>` header.
(§5's earlier "u16 version, u32 array size" read the same bytes with the tag
byte folded into the version; both close because the tag is 0.) Then
`{u8 tag, u32 size}` sections in the order **0, 1, 2, 3, 4, [6], 255**, tag 6
optional and present EXACTLY when the Stripped chunk carries its tag-6
section — 349/349 — terminator declaring size 0 and ending the payload.

### The record, and the corroborations it carries

Tag 0: u16 count == the Stripped prop count, then records **in the same order
as the Stripped array**, 48 bytes + 8 per ring point:

    +0x00 u16    model    == Stripped          \
    +0x02 f32[3] x,y,z    == Stripped, bytewise | 285,670 of 285,670
    +0x2E u8     flags    == Stripped           | records, corpus-wide,
    +0x2F u8     points   == Stripped          /  via corresponds()
    +0x0E f32[3] basis_a, +0x1A f32[3] basis_b -- from the rot bytes
    +0x26 f32    scale    == f32(b*(255/128)/256 + 1/128)  EXACTLY
    +0x2A f32    radius   == §5's cross-file identity (see below)
    +0x30..      ring     == f32(prop.x+dx), f32(prop.y+dy)  BYTE-EXACT

**Three of §44's INFERRED readings are now corroborated by the compiler's own
output:**

* **The scale formula is exact on every record in the corpus.** Not close —
  the f32 the compiler wrote equals the formula of the Stripped byte to the
  bit, 285,670/285,670.
* **The rot bytes are single-axis rotations of a constant basis.** At rot
  (0,0,0) the two vectors are (−0,−0,−1),(0,1,−0) on **46,371 of 46,371**
  corpus-wide. On the twelve-map probe, single-nonzero-byte records close
  against `b·2π/256` about x (sign −, 94/94), y (+, 72/72), z (−, 400/400)
  at 2e-3. **Composition order for multi-byte rotations is NOT measured.**
* **The +42 float is §5's placement radius.** New evidence at model
  granularity: file id 209883's radius/scale is **exactly 595.0 on all 414
  retail instances**.

The ring is world-space: byte-exact `f32(prop.x+dx)` — the client's
add-the-position-back (`0x0073DF4F/67`), done at compile time. Corpus ring
population equals the Stripped outline-point population: **334,725**.

### Two corrections to §44's prose, from the same sweep

* "the rotation bytes are zero on 180,391" — the NUMBER is real, the
  POPULATION was misnamed: 180,391 counts `rot[0]==rot[1]==0` (pure yaw,
  which is also §5's 180,393 for `vecA==(0,0,-1)` seen from the other side —
  a z-rotation leaves the vertical axis fixed). All-three-zero is **46,371**.
* "the scale byte is 0x7F on 35,593" — **does not reproduce under any
  population tried**: measured 135,079 (scale==0x7F), 30,174 (∧ rot zero).
  §44 and `props.py` are corrected in place.

### The props-deps pairing, and stripbuild learned it

**`0x11000004` (Stripped props dependencies) is present EXACTLY when the map
has props — 349/349**, closing the loop monsterai's study saw from the
Bloated side (the three zero-prop maps are exactly the three absentees; the
map-143 target row 71496 is one of them). `stripbuild.build()` now takes
`prop_dep_ids` and generates the chunk into retail's slot, immediately after
the props chunk; both unpaired configurations are REFUSED, as is a `model`
index past the list — the handoff's known trap, turned into a refusal
(`test_stripbuild` §3d, floor 40 → 46).

### (e10d) is STAGED and holds for the owner's go

`vault/research/e10d-props-2026-08-12/`: two builds identical but for the
prop's outline (A none, B a closed ±100 square), model 209883 chosen by
corpus sweep, first authored `0x11000004`, predictions RECORDED before
arming (`PREDICTIONS.md` — the oracle says the compiled tag-0 sizes must be
**50** and **90**; the radius must be f32(592.6939697265625)), and
`readback.py` proven end-to-end against the untouched study archive. The
harness is another session's; nothing arms until the owner says go.

## 46. OBSERVED: the client compiled a map with a prop WE placed — rung (e10d), both runs (2026-08-12)

**PLACE SOMETHING is done.** Two client runs, one variable apart — the same
authored prop with and without a closed outline — and every load-bearing
prediction hit. Run record: `vault/research/e10d-props-2026-08-12/`
(PREDICTIONS.md written before arming, RESULTS-A.md and RESULTS-B.md written
immediately after each run, both compiled heads and path chunks saved).

The prop: model index 0 → file id 209883 via our own `0x11000004`, at
(2400, 2400, −13) on FINDINGS 43's map, scale byte 0x7F, flags 0. Run A: no
outline. Run B: a closed ±100 square, 5 points. Procedure was rung E3's, on
the C2 archive, re-cut and verified pristine before each arm.

| | A (no outline) | B (±100 ring) |
|---|---|---|
| compiled head | 8,417 B, 8 chunks | 8,481 B, 8 chunks |
| `0x21000004` | **[209883]** | **[209883]** |
| tag-0 size (oracle: 50 / 90) | **50** | **90** |
| `corresponds()` | **CLEAN** | **CLEAN**, ring back edge-exact |
| radius +42 | `672c1444` | `672c1444` |
| path chunk | 835 B, **7 trapezoids** | 739 B, **5 trapezoids** |

What the pair establishes:

* **The compiler keeps our props, bit-faithfully.** Positions bytewise, the
  scale formula exact, and the +42 radius BYTE-IDENTICAL to what all 296
  retail records of this model at this scale carry — the compiled record is
  indistinguishable from ArenaNet's own pipeline output.
* **The cross-stream oracle holds on OUR input**, not just retail's 349.
* **The outline is collision geometry, edge for edge.** B's navmesh hole is
  exactly the authored square — trapezoid boundaries at 2300/2500 on both
  axes — with all four inside-ring probes flipping walkable→not and no
  outside-ring probe moving.
* **A prop with NO outline still carves** — run A's mesh holds an irregular
  ~±40-unit polygon hole at the prop, so the compiler ALSO instances the
  model file's own collision sub-mesh (§5). P5-A's "the outline is the props
  chunk's only geometry" was falsified, in the branch the predictions
  reserved. Retail gives this model ~149-unit outlines against its ~40-unit
  intrinsic footprint, so the two are not redundant in retail data either.

Two prediction defects, kept: the predicted radius NUMBER was derived from a
ratio the corpus probe had rounded to three decimals (`round(x, 3)` printed
"exactly 595.0" for ≈594.9998) — the compiled bytes matching retail's is the
stronger, correct statement; and P5-A's mesh prediction was wrong as above.
A constant quoted from a rounded probe is not a constant.

NOT established at readback time — the first two CLOSED the same day by the
owner's own session (build B re-staged, owner in the map): **model 209883 is
a TREE, rendered standing at (2400, 2400)** — which retroactively explains
every number (visual radius ~595 is the canopy, intrinsic ~±40 collision is
the trunk, retail's ~149 outlines are a canopy footprint) — and **the felt
collision in-client is a small square box around it**: the authored ±100
ring, walked into. Still open: whether the ring UNIONS with or REPLACES the
model footprint (the ~±40 carve lies inside the ±100 ring, so the union IS
the ring — a ring excluding the model footprint would distinguish);
generalisation past one model, one map, one position each way.

## 47. OBSERVED: the Blender loop is CLOSED — rung (e10-next), one run, all predictions hit (2026-08-12)

**A terrain a human tool authored came back bit-faithful through ArenaNet's
own compiler, with five placed trees carving the navmesh where we drew their
rings.** Run record: `vault/research/e10next-blender-2026-08-12/`
(PREDICTIONS.md before arming, RESULTS.md immediately after; one run).

The scene: `author_scene.py` in headless Blender — a flat plaza around the
spawn, rolling sines, one gaussian landmark hill, every height integer —
through `export_gwmap.py` to the interchange, then `build_map.py` into
`stripbuild` with five trees (model 209883) on near-flat cells, each with
the proven ±100 ring. 3,045 B staged, 98.59% generated.

| | predicted | observed |
|---|---|---|
| compiled head | — | 11,749 B, 8 chunks, `0x21000004` = [209883] |
| **heights, via the BLOATED codec** | **1,024/1,024** | **1,024/1,024** |
| props tag-0 (oracle) | 442 | **442** |
| `corresponds()` | clean | **CLEAN**, radii `672c1444` ×5 |
| mesh probes | 12 stated | **12 of 12** — spawn and hill flank walkable, five tree centres not, five outside probes are |

Two mechanisms the driver had to learn, both now written into it:

* **The export was PROVEN against the design before anything else** — all
  1,024 samples equal the formula, which pins the interchange's world
  row-major order and the stored-z sign in one check.
* **A freely authored field is essentially never on the terrain transform's
  lattice.** The first build quietly moved 610 samples; `snap_block()` FIRST
  (worst move: 4 stored units against a 96-unit cell) makes the round trip
  exact and puts the quantisation error in the record instead of in-game.
  Tree heights are computed from the SNAPPED field, not the design.

The hill flank at ~22° compiled WALKABLE, consistent with both of FINDINGS
34's candidate threshold sets; which set is in force is still undecided.
The owner walked the compiled map in a live session the same day and
confirmed it: the plaza, the trees, the rings and the climbable hill all
read in-game the way the chunks say.
NOT established: textures, sound, environment, lighting (the map renders
with the default tile stretched over authored slopes — the owner has seen
what that looks like); anything past one run of one scene.

## 48. OBSERVED: the slope-threshold set is 15/35/30, boundary 35 — rung (e10e), the ramp map (2026-08-12)

**FINDINGS 34's open question is measured.** The flood classifier reads slope
against `10/45/40°` or `15/35/30°` on a mode flag; the sets share no values,
so one map answers both which set and which number. Five ramp strips whose
snapped interior slopes bracket every candidate cutoff (26.6..29.4, 32.0,
36.1..37.6, 41.5..41.9, 46.5..47.8 degrees), a flat apron with the seed and
spawn, a flat plateau atop each strip. Predictions before arming; one run;
run record `vault/research/e10e-threshold-2026-08-12/`.

**Pattern `WW...`: the 32.0° strip compiled WALKABLE and the 36.1° strip did
not.** The cut is measured inside (32.0°, 36.1°); **35 is the only candidate
in the window**, every number of the `10/45/40` set is excluded, and the set
in force is **`15/35/30`**. The apron control walked; the anchors agree (22°
walkable in §47, 86° not in §38/43).

Second result, free: **walkable area is connectivity-pruned from the flood
seed.** The plateau row repeats the ramp row 5 of 5 — a FLAT plateau above a
too-steep ramp is absent from the mesh entirely. "Walkable" in the compiled
chunk means *reachable and gentle*, not gentle alone.

`stripbuild.SEED_UNWALKABLE_DEG` stays at 30, now a measured 5° margin
rather than the value merely safe under both readings; its comment records
the measurement. What the run does NOT settle: the roles of the set's other
two numbers (15 and 30 — candidate "unsure"/"amble" boundaries, unread), and
whether the mode flag can select the other set on some map kind; every map
this toolkit compiles goes through the path measured here.

## 49. OBSERVED: the terrain wears our paint — rung (e10f), textures (2026-08-12)

**Rung F2 is done, one variable against the map the owner had just walked.**
Heights and all five trees extracted byte-for-byte from (e10-next)'s
NEXT.bin; only the texturing fields changed: tag 2 painted by height band
(plaza / low rolling / high rolling / hill top — census 84/363/472/105),
tags 4/5 and tex_word taken from the DONOR's own tables at run time
([0,1,2,3], [11,21,17,7], 8421) — ArenaNet's pairing for the four
dependency files the map already ships, because table_b is a property of
the TEXTURE (a function of the file, 17,083/17,089) and inventing one is
wrong when reading it is free.

Readback, all predictions HIT: the compiled Bloated terrain carries the
painted tag 2 **VERBATIM**, both tables and tex_word carried, deps
unchanged, props oracle 442 and `corresponds()` clean, heights 1,024/1,024.
**And the owner walked it: the ground wears the four painted bands.** The
tile table is what selects among the terrain dependency files, per cell,
and the whole chain — paint in this toolkit, compile in the retail client,
render on screen — is closed. Run record:
`vault/research/e10f-textures-2026-08-12/`.

Kept honest: tables/tex_word changed alongside the paint (to
correct-by-retail values), so the claim rests on the SPATIAL pattern, which
only tag 2 can produce. Still NOT FOUND: what table_a's staircase grouping
means, and what table_b's 7 bits classify. Not tried: dependency ids from a
DIFFERENT biome (the four textures here are the template's own set).

## 50. OBSERVED: another biome's ground — rung (e10g), Pre-Searing grass on Ascalon geometry (2026-08-12)

One variable past §49: WHICH FILES. GRASS.bin is (e10f)'s map byte-for-byte
in heights, trees, paint and staircase; the four dependency ids were swapped
to Pre-Searing's four most-used ground textures — ranked by its OWN tile
census at run time, slots [12, 19, 15, 18] of its 59 → files
[112780, 112787, 112786, 112784] — with table_b following its files
([17, 17, 23, 17] from Pre-Searing's own pairing), because §49's reading
says table_b is the texture's property and must travel with it.

One run, readback all HIT (deps carried, tiles VERBATIM, oracle 442,
corresponds clean, heights 1,024/1,024), **and the owner walked it: Pre-
Searing ground on Ascalon-template geometry.** Texture files are ordinary
archive files selected per-slot by the dependency list; nothing ties a map
to its biome's set. With §49 this closes the texturing mechanism at the
level an authoring tool needs: the tile byte selects the slot, the slot
names the file, both under our control, both compiling and rendering. Run
record: `vault/research/e10g-grass-2026-08-12/`.

Still NOT FOUND, unchanged: table_a's grouping semantics, table_b's 7 bits.

## 51. OBSERVED: the sun moves and the sky arrives — rungs (e10h) and (e10i) (2026-08-12/13)

Two runs, one variable each, run records
`vault/research/e10h-light-2026-08-12/` and `…/e10i-environment-2026-08-12/`.

### (e10h) the sun: tag 0's angle byte re-bakes the lightmap

One byte against the grass map — angle index 194 → 103, 68.7° → 36.5° by
the client's own expression — and the compiler re-baked **985 of 1,024**
tag-9 bytes. The elevation sweep orders correctly: each compile's lightmap
best-fits a sun on ITS OWN side (the low-angle compile fits low, the
high-angle fits high), which is the §49-era lightmap reading measured from
the AUTHORING side for the first time. **The pre-registered two-way
inequality itself MISSED, and the defect is the prediction model's**: a
pure N·L fit carries no CAST SHADOWS, which dominate at a low sun and drag
a Lambertian best-fit far below the true elevation (best |r| 0.93 at 5°
against a true 36.5°). Kept as a model defect beside the mechanism's HIT.
Owner's eyes: "hard to tell" — and (e10i) explains why.

### (e10i) the environment chunk brings the sky, the ambient light, and the horizon

The pair our maps never carried — `0x10000009` + `0x11000009`, present on
every retail map sampled — added in retail's slot after the Path chunk:
Pre-Searing's 639 B payload BORROWED at run time (not understood, named in
the census), the deps regenerated from its 10 ids. The compiler accepted
the ten-chunk configuration and carried the payload **VERBATIM** to
`0x20000009`. **Owner, verbatim: "yep that's a sky, and it was key to the
lighting. the ocean looks much better now."** Three facts in one: the sky
was the missing environment chunk all along; ambient/light colors ride in
it, which is why (e10h)'s visual was masked under the void; and the
horizon water plane reads from it too, on a map with no water chunk of its
own.

`stripbuild.build()` now takes `env_payload`/`env_dep_ids` — together or
not at all, counted BORROWED (`test_stripbuild` §3e, floor 46 → 51). The
presentation ladder now stands: textures painted (§49), biomes swapped
(§50), the sun ours (§51), the sky borrowed whole (§51). Still not
understood: the environment payload's 639 bytes; still absent: sound.

## 52. OBSERVED: the map has a voice — rung (e10j), sound (2026-08-13)

The last presentation pair: `0x10000012` + `0x11000012`, present on most
retail maps and never on ours. Pre-Searing's 89 B payload BORROWED at run
time (not understood, named in the census), its 3 audio-file ids (`ffna`
type 8) regenerated as ours, the pair after the environment pair — the file
stays a subsequence of retail's total order. One run: the compiler carried
the payload VERBATIM to `0x20000012`. **Owner, verbatim: "background audio
plays birds and wind."** Pre-Searing's ambience on our authored map.

`stripbuild.build()` takes `sound_payload`/`sound_dep_ids` under the
environment pair's rules (together or not at all, counted BORROWED —
`test_stripbuild` §3e, floor 51 → 54). Run record:
`vault/research/e10j-sound-2026-08-12/`.

**The presentation ladder is walked**: textures painted per cell (§49),
biomes swapped (§50), the sun authored (§51), the sky and now the ambience
borrowed whole (§51, §52). What "borrowed whole" leaves open is authoring:
the environment's 639 bytes and the sound chunk's 89 are carried, not
understood, and understanding them is the difference between wearing
Pre-Searing's weather and writing our own.

## 53. OBSERVED: the two payloads, understood — env `0x10000009` and sound `0x10000012` (2026-08-13)

The §52 close named the debt precisely — "carried, not understood" — and this
section pays it. Both chunks are now decoded to typed fields and re-encoded
**349 of 349 byte-identically** (`toolkit/mapdata/envchunk.py`,
`soundchunk.py`); the corpus is the whole population, because Stripped equals
Bloated 349/349 for both kinds, so the compiler provably never rewrites these
bytes. Method was the house's: derive the framing from the 349-map corpus
alone, then read the client's own loaders to settle what the bytes could not —
and the client CORRECTED the corpus three times, which is why the disassembly
was not optional.

### Sound `0x10000012` — a positioned-emitter layer

The corpus gave the outer shape to arithmetic: every payload is `17 + 24k`
bytes (MEASURED 349/349), a 16-byte header plus `k` fixed 24-byte records plus a
`0xFF` terminator. The loader at VA `0x00712EE0 → 0x0076afc0` named every field:

    header:  u32 'msnd', u32 version 2, u8 0, u16 idx_a, u16 idx_b, u8 1, u16 k
    record:  u16 dep_a, u16 dep_b, i32 x, i32 y, u32 r_lo, u32 r_hi, u32 r_mid

`idx_a`/`idx_b` are the map's DEFAULT ambience — two indices into the sibling
Dependencies chunk `0x11000012`, `0xFFFF` for none; the 20 maps whose pair is
`(0xFFFF, 0xFFFF)` are EXACTLY the 20 with no dep chunk (MEASURED, both
directions). A record is a positioned emitter: `(x, y)` lands inside the map's
own Map Parameters rect in **318 of 318** records — the same cross-chunk oracle
that cracked props (§45), from a chunk the sound codec never reads, and a
±1-byte shift of the read collapses it to 0/318. The three radii are stored
`lo, hi, mid` on disk but the loader enforces `lo ≤ mid ≤ hi` (`0x0076b2ed`)
and **squares each with `fmul st,st`** (`0x0076b42a`) for a sqrt-free distance
compare — so they are attenuation radii, MEASURED as squared distances,
INFERRED as min/knee/max. The scout's guess that records and deps were separate
subsystems was REFUTED — records index the dep list too. And the loader does NO
magic dispatch on a dep's file type (`0x0076b190` just bounds-checks and
addrefs), which is why the ~112 emitters naming a texture rather than an
`ffna8` sound are a real open question and not a decode error. The sounds
themselves are one hop deeper: a dep resolves to an `ffna8` descriptor whose own
chunk-1 lists the raw MPEG / `AMP` audio — this chunk PLACES sounds, it does not
contain them.

### Environment `0x10000009` — parallel arrays and a spatial zone list

The 639-byte mystery is a spatial environment SYSTEM. Framing (loader
`0x00712750 → 0x0071ef70`, corpus 349/349):

    header:  u32 0x92991030, u16 version 16, u16 flag        (8 bytes)
    then sections {u8 tag, u16 count, count*record} ascending, then one 0xFF.

Tags 0–7 are PARALLEL ARRAYS of environment aspects; **tag9 is a zone list**.
A zone is a world-space circle `{u16 sel[8], i32 x, i32 y, u32 r_in, u32 r_out}`
whose `sel[8]` names one record from each of the eight arrays, overriding the
map default inside its blend band. The clincher, MEASURED: all 73 maps with no
zones have every aspect array at count exactly 1. "Several environments per map,
blended" is SPATIAL, not day/night — day/night keyframes were NOT FOUND. **tag2
is fog** — `{u8 r,g,b, u32 near, u32 far, i32, i32}`, `near < far` 1745/1745,
Pre-Searing reading hazy-blue 6200/22500 over a bright map with one dark-fog
corner — and tag12 is optional per-region boundary polygons.

**And `tag8` is the map's DEFAULT selector tuple**, which is what makes the
architecture close: its 17 bytes are EIGHT u16 selectors, one per aspect array in
tag order, plus one byte. So the default environment and a zone's environment are
the same kind of object — a pick from each array — and a zone is that tuple plus
a circle. The slot-to-array mapping is forced by the resolver at `0x0071F2F0`,
which bounds each slot against its own array's count and indexes with that
array's stride (`imul ecx, eax, 0x39` for tag6's 57 bytes, and so on), and by the
corpus: all 20,936 zone slot reads are in bounds, while rotating the assignment
by one puts 3,562 out and the full 8×8 discrimination matrix has a zero diagonal
with 55 of 56 off-diagonal cells non-zero.

### The three corrections the client forced

A corpus grammar can close 349/349 and still be wrong, and this one was, three
times — each a thing that misparses some map:

1. **The header is 8 bytes, not 5.** Offsets 4–7 are `{u16 version, u16 flag}`
   (`0x0071f1ad`), not a 5-byte `{u32 sig, u8 ver}`.
2. **The tag5-width flag is the header word at offset 6, not tag0's count.**
   The loader branches on the header dword's high u16 (`0x0071f1d5`); the header
   flag and tag0's count DISAGREE in 168 of 349 maps, and using tag0's count
   would pick the wrong tag5 width in 92. tag0 is a real 10-byte aspect array.
3. **tag8 is a real, always-present 17-byte section** — the map-global default
   environment (`envGlobal`) — which the corpus grammar had folded into tag7's
   tail as a phantom "18-byte tail whose leading u16 == 8." That 8 was the tag
   byte.

The `EnvDataImport` asserts also settled what `envArray` is: the strings at
`0x0072032d` and `0x0072044a` read verbatim `tag->index < ...envArray.Count()`
and bound tag11's and tag12's indices against the tag9 zone array — so
`envArray` is the zone list, not tag6, closing a question the corpus could only
guess at.

### THE SUN IS WRITTEN TWICE, and the two copies agree

`tag8`'s seventeenth byte is the SUN ELEVATION, stored as a byte-turn: the
loader multiplies it by the f64 at `0xA6EE50` = `float32(2π)/256`
(`fmul` at `0x0071FBD8`). The Stripped TERRAIN chunk's tag-0 `angle_index`
encodes the same authored angle under its own scaling
(`b × 282.74334716796875/45720`), and the ratio between the two quantisations is
exactly `127/32`. So one chunk predicts the other, and it does:

- **313 of 349 maps agree within one terrain quantum** (0.354°), median residual
  +0.011°; 308 agree EXACTLY under `floor(b₈ × 3.96875 + 0.5) == angle_index`.
  The tolerance figure is the one to quote because the exact one is
  **rounding-dependent**: `b₈ = 48` lands on exactly 190.5, two maps carry it,
  and banker's rounding scores 307 where round-half-up scores 308 — one of those
  two maps really does store 191. A number that moves with your rounding mode is
  not the number to put in a headline.
- Controls all collapse: the same byte read at +0x0E or +0x0F → 0/349; every
  other one of tag8's 17 bytes → 0/349 each; the NEIGHBOURING byte scaled
  identically → 0/349 (this one is in the test); shuffled map pairing → 42/349;
  rival scalings `π/256` and `π/64` → 0/349.
- **The 34 disagreements are not scattered**: 28 carry terrain byte 127 —
  exactly 45.00°, the modal default — against an authored env angle, i.e. the
  terrain copy was left unset. That is a story about ArenaNet's tools, not a
  failure of the reading.

Two independent subsystems, written by different code, storing one physical
quantity — the shape that made §51's lightmap reading trustworthy, now measured
from the environment side. Terrain bakes the lightmap from its copy; the env
copy drives the runtime sky. This also explains a thing (e10h) could not: our
authored maps moved the terrain byte and left the env chunk borrowed, so the
baked lightmap and the runtime sky disagreed about where the sun was.

### tag6 is the WATER record — a correction worth stating loudly

An earlier draft of this section called tag6 "the main environment record",
which was inferred from nothing but its size (57 bytes, the largest). The
consumer disassembly refutes it: the selected tag6 record reaches `MapWater`'s
parameter setter as one struct, and its floats are a water shader's. `+0x05` is
the water plane's base height — **the one float the zone blender refuses to
interpolate**, copied from the dominant zone instead (`fld [ecx+0x98]` at
`0x00717B01`) — `+0x09` is a wave amplitude scaling a five-sine surface sum, and
two `(tiling-scale, scroll-speed)` pairs drive texture matrices through
`GrTrans`. `+0x00` is a mode enum the loader VALIDATES rather than tolerates:
`cmp eax, 3; ja <abort>` at `0x0071F6F3` into a four-arm jump table, so a value
above 3 aborts the entire import. `+0x02..+0x04` are padding, zero in 865 of 865
records. The two u32s are D3DCOLOR `0xAARRGGBB`.

This is why the owner's (e10i) observation — "**the ocean looks much better
now**" — was literally true and not a side effect of the sky: the environment
chunk carries the water parameters, and our maps had none until that rung.

### What the audit caught, and why the pass is worth trusting

Fifteen namings went to independent skeptics that re-disassembled the cited VA
*and* re-ran the corpus claim. **Three came back REFUTED, and all three in the
same way**: the offsets and mechanics reproduced exactly, and the NAME
overreached its evidence. tag6's `+0x00` really is a validated 0..3 enum with a
real four-arm jump table, but "water technique" rested on a downstream citation
the disassembly did not support; tag5's `+0x05` really does map to zone+0x7c,
but "layer texture slot 2" claimed more than the code showed; tag1's three bytes
really are each normalised `/256`, but "an RGB triple" is ruled against by the
corpus, which carries typed colour triples with a different profile. Those are
recorded as structure-without-a-name rather than quietly promoted, which is the
difference between this pass and a plausible story.

## 54. OBSERVED: our own bytes compile — rung (e10l), authored env + sound (2026-08-13)

Every rung to (e10j) put ArenaNet's environment and sound payloads in front of
the client BYTE-FOR-BYTE, because nobody could read them. §53 decoded both. This
rung is the consequence and the gate: a map whose env and sound chunks were
**assembled by `envchunk.py` and `soundchunk.py` from typed fields**, carrying
bytes that exist in no retail map. Owner away, so the verdict is entirely
MECHANICAL — no screenshot, no listening.

Three deltas against (e10j)'s map, ten chunks untouched: three sound emitters at
our own positions and radii; fog record 0 recoloured to (198,150,96) at
1200/7000; and **the zone list grown 11 → 12**. The client compiled it —
`Perf: Map file '0x0287d3' failed to load.  Attempting to re-bloat.` — produced a
2,695 B Path chunk (22 trapezoids), asserted nothing, and carried **both payloads
verbatim**: env 671 B sha `20cd4337d0f71d1d`, sound 89 B sha `ebc366325090eb2f`,
identical to what we wrote.

**The zone growth is the load-bearing delta**, and the reason this run is worth
more than "it still works". Growing the list changed a section COUNT, so every
byte downstream of tag9 shifted. A codec that replayed stored counts — precisely
the saboteur `test_envchunk` §2 builds and runs — would have emitted a chunk
declaring 11 zones while carrying 12, and ArenaNet's own parser would have
desynced into tag11. It did not. **The count re-derivation is now checked against
the real consumer rather than against our own decoder**, which is the one thing a
round-trip test structurally cannot do.

The sun came out a corroboration instead of a delta: our terrain carries
`angle_index` 103, §53's 127/32 ratio predicts env sun byte 26, and the map
already carried 26 — the cross-chunk agreement reproduced on an authored map.

### Three procedural defects, all mine, and what caught each

None was a defect in the map or the codecs; all three printed something
confident and wrong, which is why they are recorded rather than quietly fixed.

1. **The wrong archive was armed.** `vault/dat_c2/Gw.dat` is a throwaway copy;
   the client reads `vault/run/…-c2/Gw.dat`, a SEPARATE REAL FILE. The earlier
   rungs' own journals record the run-dir path and settled it in one command.
2. **`ar.entries[row]` is off by one** — `entries` is a list, `entry.index` is
   the MFT row. Positional indexing read the NEIGHBOURING row, so the first
   readback reported a "compiled head" that was really our own stripped input.
   That reads as *the client ignored us*, not as a lookup bug.
3. **The client was never sent to the map.** The harness spawns in the default
   map; map 143 needs `--game-args "--map 143"`. Two runs passed the harness
   verdict — *"body is in the map"* — while loading a map that needed no
   compile. **A harness PASS is a claim about reaching A map, not OURS**; only
   `Gw.log`'s re-bloat line says the compile happened, and its ABSENCE is what
   named this.

What caught (2) is worth keeping: **`datcheck --diff` said the client had changed
nothing, contradicting the readback, and the diff was right.** Two instruments
disagreeing is how a wrong confident number gets found; one instrument alone
would have shipped the story.

### State

`stripbuild.build()` now takes typed `sound` and `env` objects alongside the
borrowed-payload parameters, so a map can carry ambience and weather it authored
rather than inherited. What is still borrowed by necessity: the dependency
FILES themselves (an `ffna8` sound descriptor, a sky texture) are ArenaNet
assets referenced by run-time id, which is the `borrowed_constants` pattern and
not a gap. Run record: `vault/research/e10l-authored-2026-08-13/`.

## 55. OBSERVED: ArenaNet names three of the fields itself (2026-08-13)

§53 left two threads: tag6's two unnamed floats, and what tag0/tag1/tag3 ARE as
aspects. A consumer-side pass closed most of it — offline, no client — and the
best evidence in the whole arc turned up here, because **the client looks its
shader constants up BY NAME and the name strings are in the image**. These are
not our labels.

| field | name | how we know |
|---|---|---|
| tag6 `+0x21` | **`waterFresnel`** | string `0x00A6C430`, bound to the handle uploaded at `0x0070B0F2` |
| tag6 `+0x25` | **`waterSpecularColor`** (scales an RGB triple) | string `0x00A6C474`, upload at `0x0070B134` |
| tag6 `+0x29` | projective texture-matrix scale, used as `0.5 / value` | `0x0070AD21`, installed on `GrTrans` slot 3 |

Both water coefficients are 0..1 in 865/865 and both are also **gates**:
`+0x21 > 0` and `+0x25 != 0` each promote the water technique, so the only path
that reads a field is unlocked by that same field. A pleasing consequence: 128
records set the specular strength but only 72 also set fresnel, so **56 records
carry a value the technique gate can never reach** — a fact about ArenaNet's
authoring tool, not about the format.

**tag1 is the POST-PROCESS aspect**, named the same way, from the client's own
19-entry constant table at `0xBF7DA8`: `{u8 BloomAmount, u8 PostProcSaturation,
u8 PostProcTintColor.w, u8 B, u8 G, u8 R}`. The corpus is what makes those the
*right* names rather than plausible ones — saturation is 255 (i.e. 1.0) on **648
of 741** records, which is what a defaulted parameter looks like and what a
second bloom scalar would not, and the tint strength is 0 on **571 of 741**.
It also corrects this repo: the earlier reading called bytes 3–4 "a raw u16",
and it is not an index at all, it is two thirds of a packed colour stored B,G,R.

**tag3 is the DIRECTIONAL LIGHT**: two `{u8 r, u8 g, u8 b, u8 intensity}` pairs
fed to `GrLight` setters (`0x0067B560`, `0x0067B6A0`), with the direction set
beside them asserting `GrLight:400 m_type == GR_LIGHT_DIRECTIONAL`. Colour-ness
is forced independently of the call: the zone blender reads `+0x50/+0x51/+0x52`
as **three separate bytes**, which a u16 id could not survive. That also
**REFUTES** a standing suspicion — tag3's u16s are not dep-list indices, they are
the low bytes of a colour.

### What stayed NOT FOUND, and why that is the right answer

**tag0** (ten bytes, fully read out), **tag4** (a bare dep reference) and
**tag7** (two angles, a weight and a magnitude — a direction and a distance in
shape) have no name here. For tag0 the consumer was never reached: the
dispatcher hands its zone index to `0x0071A4C0`, which nobody disassembled. That
is recorded as *unattempted*, not as absence — the ranges actually searched are
in the run record. Naming tag7 "wind" would have been easy and is exactly the
move that made tag6 "the main environment record" in the first place.

### The audit earned its keep again

Ten positive namings went to skeptics; **two came back REFUTED**. One is a
lesson about statistics rather than disassembly: an agent reported "no
correlation between the water coefficients and the mode enum" as MEASURED, and
its own numbers refute it — the fresnel rate by mode is 6.2% / 60.4% / 20.4% /
20.3%, χ² = 92.4, and 0 of 2000 cluster-preserving permutations reach it. The
other trimmed tag1's umbrella name from "bloom" to post-process and replaced one
inferred sub-name with the constant table above. A third verdict corrected *my
own* handoff: the `EnvApi:165` sites I flagged as a getter family are not
getters.

`envchunk.py` gains `postproc()` and `lights()`; `test_envchunk` pins the two
population facts that carry the names (floor 25 → 28, 40 checks under `--all`).

### What this buys, and what it does not

Sound is understood end to end at the map-chunk level — an emitter can be
AUTHORED from `{dep, x, y, radii}` with the descriptor borrowed. Environment is
understood as framing plus fog and zones — enough to author fog and to place
zones, not enough to write a tag6 main-environment record from nothing (its ten
floats are unnamed and the client stores them raw). So the honest state is:
**sound is authorable; environment is editable** — and neither has yet been
client-confirmed in an AUTHORED (rather than borrowed) form, so promoting the
codecs into `stripbuild` as an authoring path waits on a client run the way
every prior rung did. `soundchunk.py` +
`test_soundchunk.py` (floor 21) and `envchunk.py` + `test_envchunk.py`
(floor 20) land the codecs; the dep-reference oracle (env dep fields all in
bounds of `0x11000009`, 0 of 5,897, versus 5,087 violations one byte off) and
the emitter-in-rect oracle (sound, 318/318) are each a chunk the codec never
reads refuting a wrong framing. Full record and probes:
`vault/research/envsound-2026-08-13/`.


## 56. OBSERVED: RUNG G — one command, from `content/` to a map you walk (2026-08-13)

Rung G is the top of the ladder in §"the rungs": *"someone models a shape in
Blender, runs one command, and walks around it in the retail client."* Its
dependency column reads **all of the above**, and as of today all of the above
is done. This is the integration, and it is one command:

    python toolkit/mapdata/deploy.py --area plaza --install --launch --dat <copy>

`content/areas.toml` holds the recipe — geometry, seed, donors, what to borrow,
how many trees — with `source = "invented"`, which is the honest label: the
geometry is ours, chosen rather than observed. `deploy.py` does geometry →
borrow → assemble → verify → install → launch → **read back**, refusing at each
step rather than continuing.

**The run.** The client compiled it: `Perf: Map file '0x0287d3' failed to load.
Attempting to re-bloat.` Compiled head 17,731 B, and every readback check green:

| check | result |
|---|---|
| the client re-compiled | 6,627 B path chunk, **55 trapezoids built from our terrain** |
| compiled height field == authored | **1024/1024** samples |
| our environment carried VERBATIM | 639 B |
| our sound carried VERBATIM | 89 B |
| our props are in the compiled map | 5 of 5 |
| the spawn lands in exactly ONE trapezoid | 1, with Kamadan's and Ascalon's spawns scoring **0** as controls |

The map is **3,941 B, 77.90% generated by us** — 770 borrowed bytes, every one
named: Header 8, Zones 34, environment 639, sound 89. The 55 trapezoids are
worth a second look: (e10l)'s flat map compiled to 22, and this one has a
plaza, a rise and a dip. The client's own compiler is reading a shape we
designed.

### Three defects the composition had, and none of them was in a component

Every module this command drives has its own test and all of them were green.
The bugs were in the JOINS, which is what an integration rung is for:

1. **The two kinds of borrowing are not the same kind.** The first run took the
   structural constants (Header, Zones) from the biome donor, and Pre-Searing's
   Zones chunk is **7,208 bytes** against the 32×32 reference map's 34 — an
   11,115-byte map for a 4,608-byte reservation. Zones is per-map; structure
   must come from a map shaped like ours and only the biome should come from
   somewhere pretty. The schema now has two fields, because one field invited
   the mistake.
2. **The client you launch must own the archive you armed.** Every run
   directory has its own `Gw.dat`. The first launch armed the C2 copy and ran
   the DEFAULT client — FINDINGS 54's defect from the other side, and it failed
   loudly only by luck (a file lock). `deploy.py` now derives the exe from
   `--dat` and refuses if no client sits beside it.
3. **A documented stage that no line runs is a docstring.** The command's own
   docstring promised a readback stage that did not exist; it exists now, and
   the test asserts `main()` actually calls it.

### The check that could not fail

Worth recording on its own. Section 3 of `test_deploy` asserts on the syntax
tree that the exe is derived from the archive path — and its first version
asked whether `main()` contained any `join(dirname(dat), …)`. It does, **twice**,
because the output path defaults the same way. Sabotaging the exe to a constant
left the check answering True: a check that could not fail, sitting in a file
whose whole job is catching this. It now targets the assignment to `exe`
specifically, and **runs the sabotage as a negative control** so it can never go
vacuous again. The lesson is the repo's own and it keeps needing relearning —
a symbol appearing in a test is not a check.

### What rung G does not do

It is **not a hot reload**. The client compiles a map when it loads one, so
iterating means running the command again. And the dependency FILES stay
ArenaNet's: an `ffna8` sound descriptor, a sky texture, a tree model are
referenced by run-time id out of the owner's own archive, which is the
`borrowed_constants` pattern rather than a gap. What is ours is the terrain,
the navmesh seed, the prop placement, the surface, and now the recipe.

Run record: `vault/research/rungG-2026-08-13/`.


## 57. OBSERVED: the size ceiling was the ROW, not the format (2026-08-13, offline)

Every map this toolkit ever built was 32x32, and it was easy to assume the
codec imposed that. It does not: `terrain._gate_dims` caps at **16,777,216
cells**, so 96x96's 9,216 is not close to a limit. The cap was the ROW.
`datwrite` writes UNCOMPRESSED and refuses to grow a reservation — correctly,
since its invariant is same row, same offset, same length — so an authored map
only fit where it was SMALLER than what ArenaNet had compressed into that row.
`datmove` was built for this in FINDINGS 38 and had never been used from the
authoring path.

| dims | payload | map 143's row |
|---|---|---|
| 32x32 | 3,941 B | fits |
| 64x64 | 10,654 B | **no** |
| 96x96 | 21,926 B | **no** |

`deploy.py --area vale --install` now picks the VERB from the size — replace in
place when it fits, relocate when it does not — and a **96x96 map, 21,926 B,
went into a row reserving 4,608**. Offline verification, all green: terrain
round trip **9,216/9,216** exact, **96.03% ours** (770 borrowed bytes, every one
named), row 71497 relocated `0x63C66800 → 0x6FF0A00`, `datcheck --preflight`
**10 of 10** open-time rules clear, **0 overlapping row pairs**, and the
`--diff` showing exactly the two rows we touched. **No client run** — the
harness was in use by another session — so this is staged, not walked.

### `snap_block` is a one-tile function, and that is the finding

The verifier refused the first 96x96 build: **134 of 9,216 samples lost** after
snapping. `snap_block` takes exactly one 32x32 tile — its docstring says "1024
integer samples" and it strides by `CHUNK_SIZE` — and I handed it a whole map,
so tile 0 was projected and the other eight were not.

**It fails in the worst possible direction.** A linear field is exactly
representable *without* snapping, so the failure is invisible to every obvious
test: a gentle ramp lost 0, a steep ramp lost 0, a **400-unit cliff** lost 0,
and a smooth curve lost 2,752. Only CURVATURE goes missing — which is precisely
what an authored landscape is made of, and precisely what a Blender sculpt
produces. The reported worst error stayed at 2 units while a sixth of the map
was wrong, and every lost slot sat past index 1024.

`strippedterrain.snap_field(samples, dim_x, dim_y)` now walks tile by tile.
`test_deploy` §4 pins 32/64/96 at exact round trips and runs `snap_block` alone
as the NEGATIVE CONTROL, asserting both that it still loses samples and that the
losses start past the first tile — the fingerprint rather than a coincidence.

### An exit code is not evidence

`deploy` passed `--check-overlaps` to `datmove`. That is a READ-ONLY verb which
returns before any move: it exited **0** having written nothing, `deploy`
reported *"installed and armed"*, and the archive still held ArenaNet's own
64x64 map — while the head had been armed, so the next client run would have
recompiled **retail's map** and every readback check would have described it.
The install path now READS THE ROW BACK and compares it against what it wrote,
because a writer returning success and an archive disagreeing is a case where
the archive wins.

A third defect rode along and is worth one line: the test written to pin the
second one first GREPPED THE SOURCE TEXT for `--check-overlaps` and went red on
its own explanatory comment about the flag. It reads the argument list off the
syntax tree now. A grep cannot tell an argument from prose — the same lesson
`test_cmsgnames.py` recorded, relearned.

### THE RUN: every prediction hit

Executed the same day once the harness freed up, harness-driven (no owner
input). **A 96x96 map, relocated into a row reserving 4,096 bytes, compiled in
the retail client.**

    [PASS] the client re-compiled the map            10,459 B path chunk
           mesh: 88 trapezoids the client built from our terrain
    [PASS] the compiled height field equals ours     9,216/9,216 samples
    [PASS] our environment payload carried VERBATIM  639 B
    [PASS] our sound payload carried VERBATIM         89 B
    [PASS] our 12 props are in the compiled map
    [PASS] the spawn (4608, 4608) lands in exactly one trapezoid

No assert, no crash dialog. Baseline for scale: the 32x32 plaza compiled to
**55 trapezoids over 1,024 cells**, this to **88 over 9,216**.

### And it answers FINDINGS 39's standing question

FINDINGS 39 moved a real map's partner 1.6 GB and the client found it, compiled
from it and emitted ArenaNet's own bytes — but whether a relocated row SURVIVES
a play session was left explicitly unmeasured. **It does.** After the session:
`datcheck --preflight` **10 of 10**, `datmove --check-overlaps` **0 overlapping
pairs**, and our relocated partner still sits at `0x6FF0A00`, 21,926 B,
byte-untouched. The client relocated its OWN compiled head to a new extent,
which is the client doing what it always does rather than a symptom.

Run record: `vault/research/size-2026-08-13/`.


## 58. OBSERVED: a shape sculpted in Blender, standing in the client (2026-08-13)

Rung G's sentence is *"someone models a shape in Blender, runs one command, and
walks around it"*, and the rung shipped with that proved by a PYTHON GENERATOR
— `--blend` was wired and had never run. It has now, through the artist's own
round trip: export an area to interchange, import it into Blender, **sculpt it
by moving vertices** (a radial basin with a smoothstep falloff, 620 vertices;
a hard-crested ridge, 455), save the `.blend`, and deploy it.

    terrain round trip 4,096/4,096 samples exact       92.34% ours
    [PASS] the client re-compiled the map     3,016 B path chunk
           mesh: 13 trapezoids built from our terrain
    [PASS] the compiled height field equals ours    4,096/4,096
    [PASS] environment 639 B and sound 89 B carried VERBATIM
    [PASS] our 8 props present; spawn in exactly one trapezoid

**13 trapezoids against the plaza's 55 over the same 4,096 cells** — the sculpt
made most of the map unwalkable, which is what a 900-unit ridge and a steep
basin rim do. That is a fact about the shape, not a defect. The basin was the
edit worth making: it is CURVATURE, the thing §57's one-tile snap defect
destroyed silently while cliffs round-tripped perfectly.

### A brush produces fractions, and the pipeline forbade them

`deploy` REFUSED the first sculpt — *"a non-integer height reached the
exporter"*. That refusal was correct while the only producer was a generator
emitting integers, and **wrong the moment a real sculpt arrived**: 1,004 of
4,096 heights came back fractional, which is simply what moving a vertex with a
falloff does. It now ROUNDS and REPORTS, exactly as the lattice snap does —
worst residual 0.500 against a 96-unit cell pitch, against a snap that moves
samples by up to 4 anyway. Non-finite values are still refused, because there
is no value to round them to. A rule written for one producer became a wall in
front of the only workflow the rung is named for.

### The sculpt that never ran

The scene script imported the area with `runpy.run_path`. The importer ends in
`sys.exit()`, `run_path` propagated the `SystemExit`, and the script ended
there — **silently, with Blender exiting 0 and a `.blend` saved by nobody**.
The scene on disk was the unsculpted import. Deploying it would have shipped
the generator's own terrain under the name of a Blender sculpt and every check
downstream would have passed, because every check downstream is about the
pipeline rather than about provenance of the shape. It was caught only because
the `sculpt:` report lines were missing from the output — i.e. by a print, not
by a check. `SystemExit` is a `BaseException`, which is the same family of trap
`test_stripbuild`'s vault gate hit in §43.

### Two more, briefly

`gen_plaza` has a cliff built into it: at `gx == mid` the dip side (+4/cell)
meets the rise side (−8/cell), a 168-unit step measuring **61°**. The first
seed sat on that seam and `stripbuild` refused it, correctly, naming
PathData:365.

And the harness now refuses to launch when the server's archive and the
client's bind one file id to different files — a guard from the parallel
map-rows arc, and a good one, which the arm-and-recompile loop trips BY DESIGN.

**That is now answered inside `deploy` rather than by an env var in a shell.**
`--dat` already decides which client runs, so it decides which world the server
serves: the launch sets `RURIK_DAT` to that archive and hands the environment to
the harness. The guard then passes because the situation is actually right —
server and client path against the same authored map — rather than because it
was bypassed. `test_deploy` §3 pins it with two NEGATIVE CONTROLS — pointing the
server elsewhere, and building the env without handing it over, which is exactly
the shape of a fix that does nothing.

> **RETRACTED 2026-08-13, same day, by §59.** This paragraph continued: *"The
> known hazard is stated rather than discovered: a running client holds its
> archive open, so a server wanting to re-read mid-session could be refused;
> MEASURED 2026-08-13, the run completes, because the server reads the world at
> startup before the client launches."* **The word MEASURED was doing work no
> measurement supported.** The *world* is read at startup; the *navmesh* is not
> — `load_pathmap` runs at instance bring-up, after the client is up and
> holding the archive open — so that read returned EACCES and collision turned
> off silently. The run "completing" was the fallback working, not the hazard
> being absent. §59 has the numbers and the fix.

A second robustness gap fell out of the same run: `rebloat --arm` refuses a
head that is ALREADY zero length, rightly, since it cannot record a baseline
mesh from a row that has none. But "already armed" is not an error for THIS
command — the client recompiles on load either way, and `deploy` is meant to be
re-run while iterating on a shape. Every re-run after an interrupted one was a
dead end; it now checks the head and says so instead.

With both in place the whole thing is one command again, exit 0, no env var and
no flags papering over anything:

    deploy.py --area sculpt --blend vale.blend --install --launch --dat <copy>

Run record: `vault/research/blender-2026-08-13/`.

## 59. OBSERVED: the server never once walked on our ground (2026-08-13, offline)

Rungs (e10*), G and H all read the same way: *the client compiled our map and
the character walked around in it.* True, and it is one half of a claim that
reads as two. **The other half — that the SERVER agreed about where the ground
was — was false on every compiler-route run this project has made.**

Found by a completeness critic over six scouting reports, then verified here.

### 59.1 Two failures, one cause, both silent

`load_pathmap`'s only call site was instance bring-up (`authsrv.py`, inside the
connection handler). That is *after* a client has connected. Two regimes:

| when | what the server read | what happened |
|---|---|---|
| before `RURIK_DAT` | its default `vault/dat_study/Gw.dat` | **ArenaNet's map 143**, 27 trapezoids, while the client drew ours |
| after `RURIK_DAT` | our run archive — correctly | **EACCES.** A running Guild Wars client holds its own `Gw.dat` open exclusively |

Neither failed a test. Neither failed the harness. The first is quiet because
ArenaNet's mesh is a perfectly valid mesh; the second because `load_pathmap`
catches, prints one line and returns `None`, and the caller's documented
fallback is *no collision*. `20260813T112706` — rung G's own headline run —
logs `[map] navmesh 0x287D3: 1 planes, 27 trapezoids`.

### 59.2 How wrong was it? The walkable sets are DISJOINT

Prediction-first, on the sculpt map (64×64, rect 0..6144), 4,096-point grid:

| | result |
|---|---|
| **P1** spawn walkable on ours / on ArenaNet's | **True / False** — HOLDS |
| **P2** *(predicted)* >50% of samples disagree | **FAILS** — 11.8% |
| **the statistic P2 should have been** | walkable on **both: 0**; 484 disagreements = 49 + 435 **exactly** |
| **C1** every mesh agrees with itself | 13/13, 27/27, 1270/1270 — the query is sound |
| **C2** Kamadan over the same rect | 0% walkable — the control does not collapse |

**P2 was the wrong statistic and is recorded as failing rather than quietly
restated.** Both meshes are mostly empty over that rect, so *unwalkable on
both* scores as agreement and dilutes the rate. The set relation is what
carries it: across 4,096 points the server and the client never once agreed
that the same spot was standable. 16 vault runs carry
`standing at (…), which the navmesh does not cover — collision suspended`.

### 59.3 The fix, and why it is inherently TWO runs

`prewarm_pathmap(map_id)` reads the navmesh **at startup**, from the `--map`
branch — the only moment the archive both holds our map and is unlocked.
Verified: with `RURIK_DAT` on the run archive it returns **13 trapezoids**
(ours); with the default it returns **27** (ArenaNet's); on an unconfigured map
it refuses and says why.

It cannot rescue the run that installs. `--install` arms the head to zero *so
that* the client recompiles, so at that server's startup there is no compiled
mesh to read — and once the client is up the archive is locked. **The run that
produces the mesh can never serve it.** `deploy --serve` therefore launches a
second time, unarmed, and the verdict is the server's own log line matched
against a count read from the archive by `pathmap` — two independent readers of
the same bytes, never a predicted constant.

`load_pathmap` also names `PermissionError` separately now: *Permission denied*
on a file the process owns reads as a broken install, and the cause is a client.

### 59.4 What this does and does not touch

**Does not:** the readback checks run offline after the client exits and stand
unchanged; client-side confinement to authored geometry is established
independently by §23 (two maps differing in 33 bytes, bounding boxes in the
ratio of the two mesh rects).

**Does:** every "walked" sentence in §§54–58 means *the client drew and confined
us to our geometry*, not *the server pathed on it*. And the retraction in §58 is
the lesson — the word MEASURED was attached to a hazard nobody had measured, in
a document whose whole purpose is to separate those.

`test_deploy` §6 pins it (floor 25 → 35); the sabotage that deletes the one
startup call was built and run and reddens exactly 2 checks.

### 59.5 THE RUN: both predictions confirmed (2026-08-13)

Stated before arming: run 1 (armed) must FAIL to pre-warm, since the head is
zero and there is no compiled mesh yet; run 2 (`--serve`, unarmed) must succeed
and name the archive's own count. A pre-warm that SUCCEEDED on run 1 would have
meant something was serving stale geometry and the fix was wrong.

| run | dir | the server's own log |
|---|---|---|
| 1, armed | `20260813T183010` | `no navmesh for 0x287D3: not an FFNA file: b''` → **PRE-WARM FAILED … serves NO collision** |
| 2, `--serve` | `20260813T183027` | **`[map] navmesh 0x287D3: 1 planes, 13 trapezoids`** |

`b''` is the load reading the armed head: empty, exactly as designed. Between
the two, the client compiled a 3,016 B path chunk into that row, and run 2's
server read it at startup. `serve_run` matched it against the 13 `pathmap` reads
from the archive — two independent readers of the same bytes — and the command
exited 0. **The server and the client now agree about the ground.**

Full readback unchanged and green: heights 4,096/4,096, env 639 B and sound 89 B
verbatim, 8 props, spawn in exactly one trapezoid, 92.34% ours.

### 59.6 A third defect the run exposed: `--hold` was decoration

The two runs started **17 seconds apart under `--hold 40`**. `session.hold_open`
is gated on `keep_open`, which only the tape chain sets, and `deploy` passed
`--hold` alone — so every run of this command has torn down as soon as the body
reached the map. Nothing failed, because the client compiles during LOAD and
that fits inside the un-held window; the flag was naming a wait that never
happened, and a bigger map is where that stops being free. `launch()` passes
`--keep-open` now, asked of the syntax tree rather than grepped (the comment
explaining the rule would satisfy a grep), sabotage reddens 1.

## 60. OBSERVED: an authored area gets a population (2026-08-13)

R5's criterion is *"a new zone in TOML, hot-reloaded, walked"*. The toolkit could
author a zone's **ground** long before anything standing on it, and an area with
a tree in it and nothing alive is a diorama. `authsrv --area NAME` serves the
`content/world.toml` spawn rows carrying `area = NAME`; `deploy --launch` passes
it. **Three bodies stood in the sculpt map at their declared coordinates**, run
`20260813T185442`:

    AREA: sculpt -- 3 spawn row(s). This REPLACES the standing test enemy.
    'sculpt_farside': Hatcher [Collector] at (2596, 3520) absolute, hostile
    'sculpt_hostile': Hatcher [Collector] at (2619, 2921) absolute, hostile
    'sculpt_watcher': Hatcher [Collector] at (2934, 3046) absolute, noncombatant
    area 'sculpt': 3 of 3 placed

Nothing here is new protocol — every body goes out through `create_agent_world`,
the call the enemy rung proved. What is new is that the SET of bodies, their
positions, allegiances and health come from content rows.

### 60.1 This is what rung (I) was for

The load-bearing rule is that a body goes out **only where the navmesh says
there is ground**, and §59 is why that could not have been enforced before: the
server held either ArenaNet's geometry for the same map id or no mesh at all. It
is not a formality — **the sculpt map is 1.2% walkable by area**, 13 trapezoids
over 64×64, because a Blender basin and a hard ridge leave most of the terrain
steeper than the client's walkable band. A coordinate picked by eye is ground
about **one time in eighty**. Every shipped position is a trapezoid centre read
out of the mesh the client itself compiled, and the server re-checks each
against that mesh: on the mesh it stands, near it it is nudged and the distance
REPORTED, beyond 480 units it is REFUSED. A body standing where the server's own
collision says nothing exists makes everything downstream reason about it
wrongly.

### 60.2 The defect, and it reported PASS

**The first populated run placed ZERO bodies and every check was green.**
`spawn_population` reached for `agents.WORLD.get("npc", …)` — the raw content
row, whose `enc_name` is a list of 16-bit string ids — where `agents._row()`
encodes it first. `npc_properties` then built a message the codec refused:

    ValueError: string of 28 code units exceeds cap 8

The throw landed **inside instance bring-up**, after the map had loaded. So the
harness reported PASS, all six map readback checks were green (correctly — they
are about the map), the serve check matched the navmesh, and the command exited
0. The only evidence was a traceback in a log nobody was reading, and three
bodies that were not there. **It was caught because the owner looked at the
screen**, which is how rung E10a's client asserts were caught too.

Two things changed, because either alone leaves the hole:

* `agents.npc_template(key)` is public and documents the difference; the raw row
  is not a usable template.
* `deploy --serve` now reads `area 'X': N of M placed` out of the server's own
  log and fails without it. Separate from the mesh check because they fail
  separately: bodies are created well after the navmesh is read, so a throw
  there leaves the mesh line correct and every map check green.

### 60.3 What the tests could and could not do

`test_population.py` (floor 38, no vault/socket/client — the mesh is
`pathchunk.minimal()`). **Sections 0–2 did not catch the defect and could not**:
they check which rows are selected and where a body may stand, and the bug was
in entry construction. Section 2b encodes every shipped row through the real
codec, with the raw row reproduced as a negative control so the section can tell
the fix from the bug.

Seven sabotages built and run, all seven redden — but the two worth keeping are
the ones that did **not** at first:

* one **CRASHED**: refusing any shared `definition` makes the real rows
  unloadable, and the positive controls called `area_population` directly, so
  the run died with a bare traceback, no verdict banner and no ledger — the trap
  `vaultpath.require_dir` set for `test_stripbuild`. Everything goes through
  `accepts()` now.
* one passed **GREEN**: the bounded-search check computed its probe point as
  `-(PLACE_SEARCH_RADIUS + 2*PLACE_SEARCH_STEP)`, so raising the radius to
  100,000 moved the probe with it. A symbol appearing in a test file is not a
  check — the same defect `test_agentlife` records, where twelve of fourteen
  combat constants could be set wrong with all 125 checks green. Both constants
  are now asserted against **literals written in the test file**.

The `definition` rule has a shape worth keeping: sharing an index is ALLOWED
within one npc template — a definition is per-instance and outlives its agents,
and ArenaNet sends one for 140 re-creates of one worm — and REFUSED across two,
since the array is a raw index and the second row would silently overwrite the
first.

---

## 61. OBSERVED: an empty area is a STATE, and plaza's population never existed (2026-08-20, offline)

Two follow-ups WORLDMAPS-W2 flagged and did not chase
(`vault/research/worldmaps/WORLDMAPS-W2-RUN.md`, RESULTS P6). They turned out to
be one thing seen from two sides: `deploy` could not tell an empty area from a
crashed server, so it reported one as the other, and then the transcript it
produced was read as evidence that something had gone missing.

### 61.1 The serve check scored a correct run as a failure

`spawn_population` has **two** legitimate exits, §60's and this one:

    [c1] area 'plaza': no population rows; the world is the player and the geometry

`PLACED_RE` matched only `area 'X': N of M placed`, so the no-rows line fell
through to the arm written for a server that **crashed** mid-placement, and
`serve_run` printed *"the server never got as far as placing bodies"* and
returned 1. **Both arms of W2 hit it.** Each had served the mesh correctly — 55
trapezoids, the server's own count against the archive's — and each ended:

    SERVE CHECK FAILED -- the client walked on our map and the server did not

which was false in both. The finding survived because a human read
`gamesrv.log:122` and overrode the transcript. That is the failure mode worth
naming: the check was not merely wrong, it was wrong in the direction that
**discards a good result**, and the only thing standing between W2 and a
retracted finding was somebody not believing the tool.

`serve_run` now returns one of three verdicts — `SERVE_PASS`,
`SERVE_UNPOPULATED`, `SERVE_FAILED` — and `main()` returns 1 from exactly one
branch, which tests `SERVE_FAILED`. **The mesh stays load-bearing and the
ordering is the claim**: an empty area may downgrade a PASS to
SERVED-UNPOPULATED and may **never** lift a FAILED. A server that threw still
prints neither line, so "no line at all" still means what it meant.

The new verdict would be a check that cannot fail on its own — the server says
"nothing here", we write it down, green — so it carries a **second reader**:
`spawn_row_count` mirrors `area_population`'s two predicates and `serve_run`
refuses when the two disagree in either direction. The same pattern as the mesh
half, and for the same reason.

### 61.2 The content drift did not happen: two different fives

W2 recorded that *"plaza's population rows are gone from the loaded world where
FINDINGS-56-era runs had them"*. **They were never there.** The "5 of 5" in
§56's table is its own line, and it is not about bodies:

| §56's row | what it counts |
|---|---|
| our props are in the compiled map — **5 of 5** | `StrippedProps` → `BloatedProps`, chunk `0x20000004`, static scenery baked into the map's geometry by the client's own compiler |
| `area 'X': N of M placed` | live NPC bodies, `spawn_population`, a server that is running |

Four independent readings, and none of them needed a client:

1. **`content/world.toml` has never held a plaza spawn row.** Across every
   commit that has ever touched the file, the only value `area` has ever taken
   is `"sculpt"`.
2. **The vault overlay holds no `world.toml` at all** — the suspect W2 named,
   and it is empty of spawn rows and of any mention of plaza.
3. **The corpus has no such line.** Every `N of M placed` line in
   `vault/captures/harness/` reads `area 'sculpt': 3 of 3 placed`, seven of
   them. There is no plaza placement line, and no "5 of 5" line, anywhere.
4. **The rung-G run record contains the word "placed" zero times.** Its five is
   `props: 5 at [(30, 15), (1, 30), (4, 1), (20, 30), (21, 1)]`.

And the timeline settles it independently of all four. §56's run was
**11:25–11:31** on 2026-08-13 and the document was committed at 11:32
(`fef0de9`). `spawn_population` did not exist until **18:48 that evening**
(`46effa6`), seven hours later — the commit that introduced population at all,
and it populated **sculpt**, whose three positions are trapezoid centres read
out of the sculpt mesh. At the moment of the §56 run there was no population
feature, `--area` was not forwarded to the gamesrv, and no area had rows.

**Nothing moved, so nothing is restored.** Plaza is a geometry area: it is the
32×32 shape the toolkit uses to prove a map compiles, and its emptiness is the
thing §61.1's new verdict now says out loud instead of misreporting.

The hazard is the reading, and it is recorded rather than fixed, because §56's
table is correct as written — both quantities are legitimately five, they sit
one rung apart in the same arc, and `deploy.py` prints them within thirty lines
of each other in the same transcript. The guard against re-deriving this
conflation is in the tool now: a server that finds nothing where our content
binds rows is a `SERVE_FAILED` that names both counts, so the next time
somebody suspects a lost population the run itself answers.

**Labels.** 61.1 OBSERVED (two client runs, both banked, plus twenty checks
driven red by eight sabotages). 61.2 OBSERVED — it is a census over the repo's
own history and the capture corpus, with `sculpt`'s three rows as the positive
control that the same query finds what is really there.
