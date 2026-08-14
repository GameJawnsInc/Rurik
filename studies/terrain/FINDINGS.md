# Terrain texturing — findings

Labels are the project vocabulary
([studies/character/FINDINGS.md](../character/FINDINGS.md)). The arc's scope and
ladder are in [PLAN.md](PLAN.md).

---

## 1. Rung T1 — ATTX is a capability (2026-08-14, MEASURED)

**Landed.** `atex.split_trailer` splits an ATTX row into its ATEX container and
its trailer, and `atex.decode_rgba` reads one end to end.

### 1.1 The population, whole rather than sampled

Every figure below is over **all 1,648 ATTX rows** of
`vault/dat_study/Gw.dat`, found by a stride-1 peek of all 177,341 MFT rows —
no sampling. Independently re-measured by a second agent whose MFT walk, magic
peek, level walk and footer read share no code with the first (only
`gwdat.decompress` in common); verdict CONFIRMED.

| fact | result |
|---|---|
| record walk lands on a boundary whose next 4 bytes are `ffna` | **1,648 / 1,648** |
| the `ffna` type byte there | **7 on 1,648 / 1,648** |
| levels walked == full mip chain | **1,648 / 1,648** (9 every time) |
| distinct trailer lengths | **1** — 21,923 bytes |
| distinct (fourcc, w, h) | **1** — DXT3 256×256 |
| rows where the walk does NOT land on `ffna` | **0** |
| distinct head lengths | **578**, from 368 to 68,156 |

That last row is the one that matters for the design: the head is **not** a
fixed size, so the boundary genuinely has to be located.

### 1.2 ArenaNet declares the boundary herself

The last 12 bytes of every ATTX row are `{u32 head length, u32 0, b"XTTA"}` —
the ATTX magic byte-reversed — and that u32 **equals the walk's answer on
1,648 of 1,648**. Controls: it equals the total length on **0 of 1,648** and
head−12 on **0 of 1,648**.

CORROBORATED from the client's own writer: the ATTX bloat step at
`0x007582A0` builds the `ffna` type-7 riff and appends exactly this footer.

This is why `split_trailer` **refuses** a footer that disagrees with the walk
rather than preferring either. Two witnesses disagreeing is a finding.

> **A CORRECTION TO CARRY.** The first agent read the tag as `b"XETA"`. Its
> skeptic re-measured and found `b"XTTA"` on 1,648 of 1,648 and `XETA` on **0**.
> The disassembly agent, working from the writer rather than the data, also
> produced `XTTA`. Two independent witnesses beat one.

### 1.3 The trailer is a second, smaller copy of the same image

Sample of 106 rows, CONFIRMED by a skeptic that re-derived the DDS header and
the DXT mip arithmetic itself:

- `ffna` type 7, **exactly two chunks on 106 of 106**: `0x1` of 21,888 bytes
  and `0x2` of 2 bytes.
- Chunk `0x1` is a **complete, valid DDS** — 128×128, DXT3, 4 mips — and
  `128 + the full mip chain` equals the chunk size exactly on 106 of 106.
- The chunk walk closes at **+21,911**; the remaining 12 bytes are the footer,
  not a chunk.
- INFERRED, well supported: chunk `0x2` is an **RGB565 average colour** of the
  texture (median error 2.49/255 against a null of 25.04, 30/30, with four
  rival packings and a byte-order control all far worse).
- INFERRED: the DDS is an independent half-resolution re-encode of the same
  image the ATEX holds — colour MAE beats the null 30/30 at all four mips, but
  **0 of 30 byte-identical**, so it is a re-encode and not a copy.

### 1.4 `b"ffna"` occurs exactly once per file — which is why the test is synthetic

MEASURED: the sequence occurs **exactly once on 1,648 of 1,648**, at the true
boundary, and before it on **0**. So `find` and `rfind` both happen to work on
today's archive.

That is precisely why `test_atex.py`'s section 1b builds a container designed
to separate the three answers instead of sampling one. A control that agrees
with the corpus proves nothing about the build that ships next, and `rfind` is
what the scratch probe that scoped this arc actually used.

### 1.5 The rung criterion, met on the whole corpus

All **349 of 349** maps carry exactly one `0x21000002`; **17,113** references
resolve to **1,656 distinct** texture file ids.

```
magics:  {ATTX: 1648, ATEX: 4, DDS: 4}
shapes:  {DXT3 256x256: 1648, DXT1 256x256: 4}
closes_exactly: 1652 of 1652 ATEX-family
decode_rgba:    1652 of 1652 ATEX-family
```

**The population is MIXED and T4 must handle three shapes**, not the one
Kamadan suggested. The four DDS are correctly refused by `split_trailer` (they
are not ATEX at all): two are 256×256 A8R8G8B8 that `atex.dds_rgba` already
reads, and **two are 512×512 V8U8 bump maps that nothing in this tree decodes**.

The control that makes the closure claim mean anything: parsing a row WHOLE,
trailer not removed, raises on **127 of 127** probed and closes on **0** — so
trailer removal is what produces the closure, not our walk agreeing with itself.

### 1.6 A measurement that was zero because of the filter in front of it

`atex.py` recorded `PASS_TERRAIN_BORDERS` (code bit `0x10`) as used by
**"0 of 49,800 sampled levels"**. It is used by **51 of 51** of Kamadan's
terrain textures, and by every ATTX row.

The sample could not have contained one: `parse` RAISED on all 1,648 ATTX rows
until this rung landed, so the only files that use the pass *named for terrain*
were exactly the files the parser refused. Corrected in place at the constant.

**A population measured through a filter that excludes the phenomenon reports
zero and looks like evidence.**

---

## 2. Rung T2 — the tile binding is DIRECT (2026-08-14, UPSTREAM→client-read)

**Read out of the client, and it settles the question `PLAN.md` §3 named as the
arc's highest risk.** Build 38797, `vault/client/2026-07-29_221c13772c7a`.

In `TrnTexBlendLo` the **raw per-cell tile byte** from terrain tag 2 is used
twice:

- as an index into `tileTypes` (terrain `+0x80`, which tag 4 fills), and
- **unmodified, as the index into the texture array `m_tiles`** (`TrnTex+0xa0`).

`tileTypes[tile]` is only ever **compared between the four corners** of a cell
to decide how many blend layers to emit; it is never used as an index.
`TrnTexBlendHi` does the same and packs the raw byte into its descriptor as
`(variation << 16) | tile`.

**So the reading is `dep[tile]`, not `dep[table_a[tile]]`** — the indirection
the corpus could not decide, decided from the code. It matters: `table_a` is
not the identity on 41 of 80 maps.

> This is a single-witness result from a disassembly and is labelled as such.
> The corpus half is still worth running as T2's confirmation, because 41 maps
> discriminate the two readings and a render is a cheap second witness.

### 2.1 A bonus that explains the 2×2 atlas

Terrain **tag 3**'s 2-bit-per-cell plane — recorded in `terrain.py` as NOT
FOUND after four dead hypotheses — is the per-cell **tile VARIATION selector**:
`0` means take the PRNG's pick, `1/2/3` force an entry of the 4-word table at
`0x00BF7808`.

That is what the four quadrants of a 256×256 terrain texture are for, and it
means T3's UV question has a named answer to test rather than a scale to tune.

---

## 3. Rung T3 — the atlas and the UVs (2026-08-14, MEASURED)

### 3.1 One cell samples 111×111 texels of one 128×128 quadrant

Read out of build 38797's terrain chunk builders. Terrain texcoords are
**generated at chunk-build time and stored in the vertex buffer**; nothing in
the map file carries a texcoord or a scale.

- hi path (`0x0075DD50`): FVF `0xF05` — position + normal + **four texcoord
  sets**, stride 56, **four unshared vertices per cell**. 32×32 cells → 4,096
  vertices, and the pool is exactly `0x38000` = 4096 × 56.
- lo path (`0x0075E650`): FVF `0x105`, stride 32, 33×33 = 1,089 shared vertices,
  one texcoord set.
- sets 0/1/2 are **three tile LAYERS**: `uv = tileVar[var] + atlasTile[tile].uv0`
- `du = 0.5/tilesX − 17.0/atlasWidth` = **111 texels for every legal tile
  count** (algebraically 128 − 17), verified at counts 3, 16, 31, 32, 47, 59, 63
- `tileVar[0..3]` = texel `(128*(v&1) + 8.5, 128*(v>>1) + 8.5)` — so
  **variation v IS quadrant v**
- set 3 is chunk space: `1/32` per cell, one repeat = 32 cells = 3072 units

**So one cell = one full variant = 96 world units = 111 texels.**

**REFUTED, and it was the rung's stated hypothesis:** the scale comes from
neither `tex_f12`/`tex_f16` nor `tex_word` nor a divisor of `CELL_PITCH`. Every
operand is a compile-time literal (256-texel tile, the 0.5 quadrant split, the
8.5-texel inset) plus the tile count, **which cancels**. Corroborated from the
corpus: `tex_f12` and `tex_f16` are an exact `k/255` on **240 of 240** values
over 120 maps — they are bytes, not scales.

> Skeptic's correction, carried because it would bite an implementer: the
> rotation flag is **bit 31 of the packed `(variation << 16) | tile` dword**,
> i.e. bit 15 of the *variation* word. The tested register at `0x00757B43` has
> already been shifted right by 16.

### 3.2 The variation, and why the ground does not shimmer

The four words at `0x00BF7808` are `{12, 2, 5, 8}` — the **lo path's inverse
lookup** from variation to corner-mask slot; the hi path never reads them. Both
paths agree that variation *v* selects quadrant *v*.

Variation 0 means "take the PRNG's pick": Lehmer/MINSTD
(`s' = 48271·s mod 2³¹−1`), **re-seeded per 32×32 tile with
`seed = (tile.x << 16) ^ tile.y`**, and *both* branches of the variation test
draw, so stream position is a pure function of the cell's index — the terrain
is deterministic. Variation 0 is **99.9426% of 5,153,792 cells over 24 maps**,
so tag 3 is a sparse authored override, and it can only pin quadrants 1–3:
quadrant 0 is reachable only through the draw.

### 3.3 Tag 3's bit order: INFERRED → MEASURED

`terrain.py` records the bit-pair position as not established, on the grounds
that any self-consistent convention round-trips. That was true while tag 3 had
no meaning; the client now decides it, and **`bits_at`'s `(i & 3) * 2` guess is
exactly right** — two consumers read the de-tiled buffer with a shift counter
starting at 0 and stepping `+2 & 7`.

The corpus settles it a **second** time and agrees: cross-byte co-occurrence
collapses onto a monotone function of true distance, `C(3→0) = 50.546%` against
`C(0→3) = 33.770%` (ratio 1.497, z = 31.1), and the reversed reading demands
the opposite inequality. A null shuffling byte *positions* while keeping
*contents* collapses the ratio to 1.010/0.966/0.855.

Both of `terrain.py`'s stated controls reproduce exactly: all-zero on **168 of
349** maps, median **0.0957%** of bytes non-zero where present.

### 3.4 A DEFECT IN OUR DECODER, found by a skeptic

**`atex.decode_rgba` did not return what the client uploads.** The border pass
claims the band blocks so the payload never stores them — and the client then
**regenerates** them (`0x006C2FA5` → `0x006C22A0`, source block `(x^3, y^3)`
per border axis with an in-block reversal). We implemented only the first gate
and left them zero.

Measured on one texture, and the control is the sharp half:

```
border-band pixels: 15360, changed by the fix: 15360
  of those, ZERO before the fix: 15360 (100.0%)
interior pixels:    50176, changed by the fix: 0   <- must be 0
```

`atex.mirror_borders` now fills them: within a tile, column `band−1−k` takes
column `band+k`.

**This corrects a measurement made in this very session.** Before the fix I
measured the band's alpha as "a hard zero at the rim" and concluded a quadrant
was an alpha-bordered splat. **The zero was ours.** A tile is a 112×112 image
inside an 8-pixel *mirrored* band, the four variants share that band and are
therefore interchangeable at any cell boundary — which is exactly what a
per-cell variation selector requires.

The rule's form is confirmed at level 1, where the pass is gated off and the
band IS stored: **83.24% exact pixel match against 63.23% for the nearest
rival**. It cannot be 100% — level 1's band was mirrored *before* DXT
compression, so a 4×4 block straddling the axis re-compresses asymmetrically —
and an earlier version of this check demanded byte equality, got 0 of 60, and
was wrong about the oracle rather than about the rule.

### 3.5 What survives from the pre-fix reading

The alpha **is** a blend mask: only 7 of 192 tiles are fully opaque, 178 of 192
span the full 0..255, and the median tile has 46.9% of its pixels at
intermediate alpha. With three tile layers per cell, terrain is genuinely
multi-layer blended — so a T5 that draws one opaque layer per cell will not
reproduce it, and should say so rather than look broken.

---

## 4. Rung T4 — the textures exported beside the map (2026-08-14, MEASURED)

**Landed.** `mapexport.build_terrain_textures` resolves every tile byte to a
PNG under `terrain/` (keyed by file id, shared between maps like `models/`),
and the `.gwmap` manifest (format_version 3) gains a `terrain_textures` block:
one row per tile naming its file id, the MFT's (size, crc), and its image or
the reason it has none. `test_mapexport.py` sections 4c and 8.

### 4.1 The resolution law, measured whole and enforced as a refusal

Over **all 349 maps** (this rung's scan, 2026-08-14):

| fact | result |
|---|---|
| `len(dep) == len(table_a) + (1 if tag3b else 0)` | **349 / 349** |
| `max(tiles) < len(table_a)` | **349 / 349** |
| maps carrying the second tag-3 record | **24**, = the offset-1 maps |

So the exporter's rule is `file_id = dep[tile + offset]`, with the offset
decided by the second tag-3 record's presence — T2's DIRECT binding plus
`terrain.py`'s tag-5 realignment, now confirmed as the *texture* binding on
the whole corpus. Both equalities are REFUSALS in the exporter, not warnings.

> **A CORRECTION.** `PLAN.md` §2's scoping table recorded
> `len(table_a) == len(terrain dep list)` on "80 of 80" map heads. That is
> true only of maps WITHOUT the second tag-3 record; on the 24 that carry it
> the dep list is one longer. The 80-head sample either missed all 24 or the
> probe read the wrong pair; either way the corpus-wide law is the one above.

### 4.2 The mixed population is entirely the LEADING entry

T1 found the terrain set MIXED — 1,648 ATTX + 4 plain ATEX + 4 DDS — and the
rung brief said T4 must handle three shapes. Where those shapes actually sit
is now MEASURED, and it collapses the worry:

- **Every tile-position entry on every map is ATTX: 17,089 of 17,089.**
- **All 8 non-ATTX files appear ONLY as the extra leading entry** of the 24
  tag3b maps — the 4 plain ATEX on 16 maps, the 4 DDS on 8 maps (e.g. row
  56835 leads with `0x475C8`, 494,516 bytes, plausibly one of the two
  512×512 V8U8 bump maps).

So **no retail tile byte can name an undecodable texture** — the V8U8 problem
lives entirely in the slot the binding never indexes. The exporter records
the leading entry with its archive identity and does NOT decode it: what it
is for is UNVERIFIED (the tag3b record's four floats arrive beside it, which
smells like a detail/far-texture pairing, and that is a smell, not a
measurement). The skipped-tile path (reason recorded, never dropped, and in
Blender its own empty slot) is kept and exercised synthetically, because a
future archive owes us nothing.

### 4.3 What the export is and is not

Kamadan: 51 tiles → 51 images, `dep_offset` 0, census `{ATTX: 51}`, every
distinct tile byte in use resolving — the rung criterion, checked from the
tiles sidecar rather than the block's claim about itself. The sha256 negative
control: one flipped byte in one PNG refuses the whole export at load. The
PNGs are derived ArenaNet bytes and land in the vault; `resolve_outdir`'s
working-tree refusal covers them unchanged.

---

## 5. Rung T5 — the ground gets a material (2026-08-14, MEASURED)

**Landed.** `import_gwmap.apply_terrain_textures`: one Blender material per
distinct texture image, `material_index` per face from the `gw_tile`
attribute through the manifest's tile table — the props pattern on the
ground. `test_blenderimport.py` sections 2b and 5; the criterion is asserted
against the SIDECAR: every tile's slot material equals the image the manifest
names for it, and the per-face indices — recomputed outside Blender from
`tiles.u8` through the dump's slot table — sha256-match what Blender read
back off its own built polygons (212,992 of 212,992 faces on Pre-Searing).
`--no-terrain-textures` is the control, on both the synthetic and the real
map.

Three stated limits, all deliberate:

- **One opaque layer per cell, no alpha wired.** §3.5 stands: only 7 of 192
  tiles are fully opaque, retail blends three layers per cell with alpha as
  the mask, so tiles that are authored as alpha OVERLAYS (Kamadan's plaza
  pavement, rock edges) render their unwritten regions as opaque white-grey.
  Blending is T6.
  > **CORRECTED the same day, after the first human look at the scene.**
  > This section first blamed ALL the visible striping on that content
  > limitation, and most of it was OURS: Blender premultiplies a
  > STRAIGHT-mode image for rendering, so the un-wired Color output was
  > arriving as RGB × alpha and every cell drew its blend mask as a dark
  > band over clean ground colour — the same in-cell band position across
  > different tile types, which a content explanation cannot produce and
  > which is what exposed it. MEASURED on the exported PNGs: window
  > luminance flat (e.g. 139..158), window alpha banded (25–52 of 112 rows
  > below 128). The images are now loaded CHANNEL_PACKED — alpha is DATA,
  > exactly what a splat mask is — and the terrain is smooth-shaded, since
  > both vertex layouts T3 read carry per-vertex normals and the faceted
  > stair-step look was the importer's artifact, not the archive's. What
  > remains after the fix is the real content limit above, plus the
  > per-cell quadrant repetition.
- **Every cell samples quadrant 0** through T3's measured window — inner
  111×111 texels, corners inset 8.5 — because the interchange does not carry
  tag 3 and nothing reproduces the per-cell PRNG draw. Which world axis maps
  to +u is a CONVENTION chosen in the importer and named there; nothing
  measured orients the quadrant yet.
- **A tile with no decodable texture gets its OWN empty magenta slot**
  (`gw_untextured_<fid>`), never slot 0 — the prop material fall-through
  (31.6% of Kamadan's prop area silently drawing whichever image landed
  first) is the defect this refuses to repeat. §4.2 says retail can never hit
  this path; the check exists for the archive that ships next.

---

## 6. What is still open

- **T6**: blending between tiles — the three per-cell layers, the alpha
  mask, and which corner-tile combination selects the two overlay layers.
  DEFERRED with the reason in PLAN.md §3.
- The per-cell variation: tag 3 is decoded (§2.1, §3.3) but not exported,
  and the PRNG draw is not reproduced, so T5 pins quadrant 0. Also the
  quadrant's ORIENTATION (which axis is +u) is a convention, not a
  measurement.
- The extra leading dependency's MEANING (§4.2): 8 files — 4 plain ATEX, 4
  DDS of which two are 512×512 V8U8 bump maps nothing decodes — paired with
  tag3b's four floats. UNVERIFIED.
- `table_b` — Kamadan's values are `{5, 7, 13, 15, 17, 19, 21, 23, 81, 85}`,
  all odd. UNVERIFIED, and not on the critical path.
- Terrain tag 0's `tex_word`, `tex_f12`, `tex_f16`. Named, not understood.
