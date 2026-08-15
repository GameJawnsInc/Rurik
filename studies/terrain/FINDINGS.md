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

## 6. Rung T6 — the blend, and why the ground stops repeating (2026-08-14)

**Landed.** Two mechanisms, both read out of build 38797, both reproduced in
`toolkit/` (stdlib, tested) and consumed by Blender as a resolved sidecar so
the client's rules have exactly one implementation.

### 6.1 The per-cell variation is a PRNG draw (MEASURED)

`trnvariation.py`. Per cell, `0x00761800`:

- **one draw ALWAYS** (`0x007618B3`..`0x007618CE`) — the tag-3 forced branch
  calls the generator and *discards* the result, so a consumer that skips it
  desynchronises every later cell in the tile;
- `quadrant = draw & 3` (`0x007618CB`, a plain mask), or the raw 1/2/3 when
  tag 3 forces it;
- the primary layer's rotation bit **can never be set** — the mask clears it
  and tag 3 is two bits wide;
- `seed = (tile.x << 16) ^ tile.y` (`0x00761C80`), x in the high word, zero
  becoming `0x075BD924`;
- **one reseed per 32×32 tile**, row-major, both axes ascending. Settled by
  the tag-3 cursor: it advances 8 bytes per row and is never reset across the
  outer loop, so 32 rows consume exactly 256 bytes = one tile's tag-3 data.
  The outer loop's back-edge is `0x0075E3D7 → 0x0075DF9E`.

**The generator is NOT `s' = 48271·s mod (2³¹−1)`, and this is the trap.**
`0x0046D120` computes the modulo by magic-number division (`0xBC8F1391`,
`>>47`), whose quotient is one too high on **3.79% of states** (measured by
search over 200,000, independently of the reading agent's ~3.8%), and the
correction adds `0x80000000` rather than the modulus — which does not cancel
it. On those states the client returns `(48271·s mod 2147483647) + 1`. A
"tidied up" clean-modulo port drifts on one draw in twenty-six.

### 6.2 The four quadrants are COVERAGE MASKS, not just variants (DERIVED)

`trnblend.py`. A cell samples the tile bytes of its four corners — its own
cell and the `+x`, `+y`, `+xy` neighbours, which are also vertices V0..V3 —
maps each through `tileTypes` (tag 4), and groups them: corners sharing a
**type** need no seam. Each group's 4-bit corner mask indexes a 16-entry
table at `0x00BF78D8` giving the quadrant, a 180° rotation flag, and
optionally a second layer.

**What that table means was not in the read; it is derived here, and it is
the rung's real finding.** Each 128×128 quadrant of a terrain texture is an
authored **alpha coverage shape**:

| quadrant | covers corners |
|---|---|
| 0 | {2, 3} — an edge |
| 1 | {1} — a corner |
| 2 | {0, 2} — the other edge |
| 3 | {3} — a corner |

with rotation mapping corner *k* → 3−*k*, which reaches all four edges and
all four corners. Three independent supports, none of them forced:

- the cover sets are read off the four rows that are unrotated and
  single-layer (masks 12, 2, 5, 8);
- **the client's own inverse table at `0x00BF7808` is `{12, 2, 5, 8}`** — a
  different array, in the lo path, which never reads `0x00BF78D8`;
- predicting all 16 rows and requiring each row's layers to cover exactly its
  own mask: **15 of 16**, the miss being the empty mask 0 the grouping loop
  cannot emit. The six two-layer rows are the sharp part, since a union of
  two separately looked-up quadrants has to land exactly. A mirror-in-x rival
  rotation scores 8 of 16 and is kept as a live control.

So **the blend mask is ArenaNet's, not a gradient we invented**: bind the
layer's texture at the named quadrant and its own alpha does the masking.
This also retires §3.5's framing — the alpha is not merely "a blend mask",
it is a *corner-coverage* mask with a table naming which shape goes where.

### 6.2b The quadrants are alpha shapes and NOT colour variants — a correction

**MEASURED 2026-08-14, and it corrects this arc's own claims.** Over eight of
Kamadan's terrain textures, comparing the four 128×128 quadrants pairwise
inside the sampled window:

| | mean pairwise difference |
|---|---|
| **ALPHA** | **118 – 134** of 255 |
| RGB | **4 – 21** of 255 |

So a texture's four quadrants are very nearly the SAME PICTURE carrying FOUR
DIFFERENT COVERAGE MASKS. Two consequences, and the second is a retraction:

- **It independently corroborates §6.2.** If the quadrants were four visual
  variants of a material — the reading T3 recorded and this document
  repeated — their RGB would differ substantially and their alpha need not.
  The measurement is the other way round by an order of magnitude, which is
  what "each quadrant is an authored corner-coverage shape" predicts and
  what a variant reading does not.
- **RETRACTED: that per-cell variation removes the ground's repetition.**
  §6.1 and the T6 commit message both said so, and `test_blenderimport`
  carried it as a check's rationale. It is wrong. Variation selects a
  coverage mask; on these eight textures it barely moves the colour. What
  variation actually buys is correct per-cell MASK selection, which is what
  makes tile boundaries blend.

> **STRUCK 2026-08-14, the same day, by the owner and then by measurement.**
> This entry continued: *"**The visible tiling of the ground at close range
> is INHERENT** — one cell is 96 world units showing one 111-texel image of
> its material (T3), and the client draws exactly that … the colour
> repetition is ArenaNet's and is not something a renderer can fix without
> inventing detail she did not ship."* **That is false, and it was the second
> wrong claim in this arc from the same cause** — reasoning from our own
> render instead of comparing against the client. The owner went to Kamadan
> in the retail client and photographed the same ground: organic grass/dirt
> boundaries, no 96-unit grid. §7 has what the client actually does. Two
> narrower errors inside the struck text are worth keeping visible: the RGB
> table above is **eight** textures, and over all **101** it is 4–35 mean with
> a max of 231 (§7.1), so "very nearly the SAME PICTURE" does not generalise;
> and "the client draws exactly that" was never measured — the UV writer has
> **two different rectangles** and we had only found one (§7.2).

The claim that survives is narrower and still worth having: T5 pinned every
cell to quadrant 0, which forced the WRONG COVERAGE SHAPE everywhere, not a
duller picture.

### 6.3 What is reproduced, and what is a translation

`mapexport` ships `.layers.u16` — three slots per cell, `(rot<<15) |
(quad<<8) | tile`, `0xFFFF` unused — so Blender draws rather than re-derives.
Kamadan: 81.9% of cells single-layer, 58,456 overlay quads. Pre-Searing:
262,310 overlay faces over 148,882 cells, 68,201 rotated, and Blender's
built geometry equals a recomputation from the sidecar exactly.

Two honest departures, both labelled at the call site:

- **The client composites in ONE pass** through three texture stages
  (measured: `0x006D34DA` binds N stages, one `DrawIndexedPrimitive` at
  `0x006D3A2B`, `ALPHABLENDENABLE=0` so the polygon is written opaque).
  Blender has no equivalent, so the layers become coplanar geometry drawn
  back-to-front with a 0.35-unit lift — a translation of the composite, not
  a copy of it, and the lift is ours.

### 6.4 The composite formula, OBSERVED — ArenaNet's own shader

This section first shipped the formula as INFERRED, reasoning from the
architecture ("a single pass with per-stage ops is only consistent with the
mask being consumed in the combiner"). **It did not have to stay inferred.**
The terrain material builder at `0x0074B9D0` (`TrnTex.cpp`) selects one of
four paths by device caps, and the preferred one hands a **binary ps_1_1
pixel shader, 128 bytes at `0x00A737E8`**, to `0x00664110`. Decoded whole:

```
tex t0 ; tex t1 ; tex t2 ; tex t3
lrp r1, t1.wwww, t1, t0      ; r1 = lerp(t0, t1, t1.a)
lrp r1, t2.wwww, t2, r1      ; r1 = lerp(r1, t2, t2.a)
mul r0, v0, r1               ; r0 = diffuse  * r1
mul r1, v1, r1               ; r1 = specular * r1
lrp r0, t3.wwww, r1, r0      ; r0 = lerp(r0, r1, t3.a)
```

`lrp dst, s0, s1, s2` is `s2 + s0*(s1 - s2)`. So: **layer 0 opaque, then
each additional layer lerped over the accumulator by ITS OWN texture
alpha** — the formula this repo drew coplanar geometry to reproduce, read
out of ArenaNet's shader tokens rather than argued from her architecture.

The **fixed-function fallback agrees**, which is a second witness from a
different mechanism. Path C/D build stage ops from literal tables at
`0x00A73E08`/`0x00A73E38`, and the `GR_TEXOP → D3DTEXTUREOP` decoder at
`0x00A65B78` (24 entries × 3 dwords, located from `Dx9ShaderStage.cpp` at
`0x006DA8E7`) reads them as:

```
stage 0: SELECTARG1          stage 2: BLENDTEXTUREALPHA
stage 1: BLENDTEXTUREALPHA   stage 3: MODULATE, no texture
```

That decoder is itself cross-checked four ways, the sharpest being
ArenaNet's own assert `GrStage:350 layerFlags & GR_TEXFLAG_MODULATE_2X_ARG`
setting op 14, which the table maps to `D3DTOP_MODULATE2X`.

**Two things this opens, and they are the next visible wins.** `mul r0, v0,
r1` modulates the blended ground by the **vertex diffuse colour** — which is
terrain tag 9, the baked directional lightmap `terrain.py` already decodes
and `mapexport` already ships as `.shade.u8`, and which nothing in Blender
currently applies. And `t3` is not a tile layer at all: its alpha blends
between the diffuse and specular lighting terms, which is what T3's fourth
texcoord set (chunk space, one repeat per 32 cells) addresses.
- **Which corner is the BASE rests on an assumption.** Each corner is
  fetched as `arr[(sel >> 2k) & 3]` where `sel` is a per-cell byte from a
  chunk-local array at `chunk+0x2B4` that the builder fills before the loop;
  where it comes from is NOT FOUND. `trnblend.SELECTION` assumes the
  identity, which makes corner 0 the cell's own tile and agrees with T2's
  separately measured "the raw byte indexes `m_tiles` directly". If that is
  wrong the SET of layers is unchanged and which one is opaque can differ.

### 6.5 Tag 9 applied — the lightmap the shader asked for

`mul r0, v0, r1` (§6.4) multiplies the composited ground by the vertex
diffuse colour, and terrain tag 9 is a BAKED DIRECTIONAL LIGHTMAP measured
in `terrain.py`: fitting `255 * max(0, N.L)` gives median Pearson r 0.887
over 345 maps, the best-fit elevation tracks tag 0's angle field with
Spearman 0.9352, and the azimuth control puts the light on +x with no y
component on 343 of 345 — which is the client's own
`TrnTexIntensity:342 lightDir.y == 0`.

It is attached **per VERTEX**, and that follows from the file rather than
from taste: tag 9 holds `dimX * dimY` bytes, the same grid as tag 1, whose
samples are measured to sit at cell CORNERS. So the far column and row
replicate exactly as `corner_heights` does. Kamadan's lattice means 0.862
over 187,233 vertices, Lornar's Pass 0.719 over 267,393; both span the full
0..1, so the multiply is visible rather than a no-op. The overlay geometry
samples the same lattice, so a blended layer is lit identically to the
ground beneath it.

What is NOT settled is the transfer curve — see §7.

---

## 7. The assembly rule — what we get wrong (2026-08-14, MEASURED)

Opened because the owner isolated the overlay object in Blender and read it
correctly on sight: *"this is similar to the Wang tiles … these connect a
certain way in order to properly blend together different terrain textures …
need to figure out how the game properly assembles these to not repeat corner
tiles or use other mismatches like we're currently doing."*

### 7.1 The coverage model, confirmed from the DATA (MEASURED)

§6.2 derived `QUADRANT_COVERS` from the client's tables. This measures it from
the exported pictures instead, which is a genuinely separate witness: for each
of Kamadan's 101 terrain textures, the mean alpha of each 128×128 quadrant's
four 64×64 corner blocks, thresholded at 128.

| per-quadrant covered-corner masks | textures |
|---|---|
| `q0=1100 q1=0010 q2=0101 q3=1000` — **exactly `QUADRANT_COVERS`** | **97** |
| one quadrant one corner off (threshold cases) | 4 |

**97 of 101 with no fitting and no free parameter.** The Wang reading is now
carried by the client's forward table, the client's inverse table at
`0x00BF7808`, and the alpha channel of the art.

RGB across quadrants is **not** near-identical, correcting §6.2b: 100 of 101
textures differ, mean 4–35 of 255, max as high as 231. Quadrants are coverage
shapes **and** distinct art.

### 7.2 The UV writer has TWO rectangles, and we implement one (MEASURED)

`0x00757A80`, the per-layer UV write, called once per cell from the end of
`TrnTexBlendHi` (`0x00761A25`) with an array of up to three packed dwords.
Each dword splits — `movzx eax, bx` / `shr ebx, 0x10` at `0x00757A9C` — into

    low 16 bits  = index into a texture-pointer array at obj+0xA0 (count obj+0xA8)
    high 16 bits = the coverage selector, or 0xFFFF for "no mask, full cell"

and the call site builds it as `(cover << 16) | tex` (`shl eax,0x10; or eax,ebx`
at `0x00761A0F`), reading `cover` from `0x00BF78DC` — the same stride-8 table
pair §6.2 already has. `edi` inside the writer is `obj+0x3C`
(`lea ecx,[ecx+0x3c]`, `0x00761A22`). The two paths then diverge:

| | origin | span |
|---|---|---|
| **unmasked** (`0xFFFF`) | `obj+0x70`, `obj+0x74` | `obj+0x68`, `obj+0x6C` |
| **masked** | `quadtable[sel & ~0x8000]` (stride 8 at `obj+0x80`) **+ the texture's own** `[tex+0x10]`, `[tex+0x14]` | `obj+0x78`, `obj+0x7C` |

Two separate span fields and two separate origin schemes. **We use one
rectangle — the inner 111/256 window at the quadrant offset — for every
layer, and no per-texture origin at all.** The base layer in the client does
not go through the quadrant table; it has its own `(origin, span)` pair.
Whether those advance per cell is NOT FOUND and is the open question that
decides whether the base repeats every 96 units (§8).

The rotation reading of §6.2 survives unchanged: `test ebx, 0x8000` at
`0x00757B43` swaps V0↔V3 and V1↔V2.

### 7.3 The corner selector is per-cell DATA, and we hardcode it (MEASURED)

§6.3 assumed the identity selection and the open list recorded the selector as
NOT FOUND. Its *form* and its *traffic* are now measured, its source is not.

`TrnTexBlendHi`'s prologue (`0x0076181B`..`0x0076185E`) decomposes arg3 into
four 2-bit fields and uses each to pick one of **four** row cursors passed as
arg2, confirming the `arr[(sel >> 2k) & 3]` form §6.3 guessed. At the call site
(`0x0075E0E3`) arg3 is a byte read through a pointer at `[ebp-0x38]` that is
**incremented once per cell** (`inc dword ptr [ebp-0x38]`, `0x0075E10A`). So
`sel` walks a per-cell array and is not a constant.

`trnblend.SELECTION = "identity"` pins it to `0xE4` for every cell. The
consequence is exactly what the owner saw: along a straight material boundary
every cell picks the same quadrant, so the authored edge undulates with a
period of exactly one cell. **Four cursors with a 2-bit pick per corner is an
orientation mechanism** — the same coverage shapes reused permuted — which is
the standard way a Wang set avoids a visible repeat.

Two more things this settles. arg4 is `(byte[edi] >> cl) & 3` with the shift
base advancing by 2 per cell (`add ebx, 2`, `0x0075E10D`) — that is **terrain
tag 3**, four cells per byte, and `TrnTexBlendHi` tests it against zero, which
corroborates `trnvariation`'s "0 defers to the PRNG". And arg2's four entries
are filled from two row cursors each read **before and after** a call that
advances them, matching `trnblend`'s "corner 0 = this cell, 1 = +x, 2 = +y,
3 = +x+y" from the other side.

### 7.4 Hunting the selector's filler: three things closed, the question open

The array is **`chunk+0x2B4`**, and its address is formed exactly once in the
image — `lea eax, [ebx + 0x2b4]` at `0x0075DF60`, stored to `[ebp-0x38]` and
walked a byte per cell. It is inline chunk memory, not a pointer: the read is
`movzx eax, byte ptr [eax]` with no indirection.

**Nothing in the image writes it.** `--field 0x2B4` finds six stores, all on
unrelated objects (`0x004362B3`, `0x004362BC`, `0x00438ABD`, `0x00438F58`,
`0x004393B7`, `0x00855F54`), and three address-taking sites of which only
`0x0075DF60` is terrain — the read itself. So the fill goes through a pointer
the anchored scan cannot follow. `codescan` names its own blind spots and one
of them fits exactly: a method whose `this` is the RNG object at `chunk+0x2A4`
writing `[this+0x10]` **is** `chunk+0x2B4`, spelled with displacement `0x10`,
and no sweep for `0x2B4` can see it.

**RULED OUT — it is not an undecoded terrain tag,** which is worth having
because it is the cheap explanation and it is wrong. `terrain.py` decodes tags
0, 1, 2, 3, 4, 5, 7, 9; tags 6 and 8 occur in none of the 349 maps and the tag
sequence is fixed (`SEQUENCE_SHORT` / `SEQUENCE_LONG`, 325 + 24). §6.3's "NOT
map data" therefore survives a real test rather than standing on assumption.

**Two things fell out that are not about the selector at all, and both
corroborate `trnvariation` from sites it was not built from:**

- `0x00761C80` is the per-tile-block reseed, and it is
  `(a << 16) ^ b` — `mov edx,[eax]; shl edx,0x10; xor edx,[eax+4]` — which is
  `trnvariation.reseed` instruction for instruction.
- `0x0046D2E0` is `RNG::seed`, and its zero-seed fallback is **`0x075BD924`**,
  which is `trnvariation.DEFAULT_SEED`. Independent of the draw loop the
  constant was originally read from.
- **NEW, and unmodelled:** that seeder writes **two** state dwords, `[ecx]` and
  `[ecx+4]`, both to the same value. `trnvariation` models a single state. Two
  states seeded identically diverge only if they are stepped differently, so
  this may be inert for our purposes or may be the second stream that varies
  the selector. UNVERIFIED, and it is the cheapest lead left.

**The live read was attempted 2026-08-15 and got most of the way.** Recorded
because the two blockers cost the session and neither is about terrain:

- **A loopback run could not start at all**, and the fix is not the obvious
  one. `contentids.preflight` refuses because maps 146/148 name `0x1B97D`,
  which no 38797-era archive binds *plainly* — row 7982 carries the bit-31
  spelling, a rename pending a replacement the loopback builds can never
  install because their updater is killed. **Re-cutting from `dat_study` does
  not fix it: `dat_study` is the stale side** (`binds_plainly` is `None` there
  too). MFT row counts place it exactly — `C:\gw` and the build-38833 run
  directory both hold 177,753 rows, `dat_study` 177,342, the 38797 run copy
  177,335. The pairing that passes 10/10 is **both sides at the 38833
  generation**: client `vault/run/2026-08-13_64fae3b1369b`, server a fresh
  study copy cut from `C:\gw` (`vault/dat_study_38833/`, additive, nothing
  existing touched). `contentids.py`'s own docstring already says why —
  "**0** in the build-38833 run directory, where every pending replacement has
  landed" — and warns that refreshing one side only is the loud-on-client,
  silent-on-server failure.
- **`vault/content/attributes.toml` cites `toolkit/clientscan/attribtable.py`,
  which exists only on branch `claude/combat-end-to-end-a2242b`.** Shared vault
  data referencing an unmerged tool makes `content.py` refuse in every other
  tree. `deploy.py --repo-content-only` is the sanctioned way past it.

With that pairing the client reached Kamadan and the probe **found the map's
tile bytes in the live process**, so the read path works. The chunk itself was
NOT identified: the "`+0`/`+4` are the block counts" guess came from `ebx` in
`0x0074B440`, a DIFFERENT function, and is not the chunk's layout; and the
bytes matched are almost certainly the file buffer rather than
`[chunk+0x80]`. It failed loudly rather than returning a wrong array, which is
the only good thing to say about it. **Next session: anchor on the chunk, not
on data it points at** — walk `[ebp-0x40]` in `0x0075DD50` from its own
caller, or breakpoint-free, find the RNG pair at `+0x2A4` adjacent to a live
`+0x1D0` subobject.

**Anchoring on the chunk, 2026-08-15: four probes, no read, three facts.** The
client was in Kamadan on loopback each time and its tile bytes were located in
process memory every run, so the machinery works; what failed is every attempt
to name the object that owns `+0x2B4`.

- **`chunk+0x80` is `tileTypes`, NOT the tile array** — and this document's own
  `trnblend.py` docstring already said so (*"mapped through `tileTypes`
  (terrain tag 4, `terrain+0x80`)"*). Two probes were built on the opposite
  reading and found per-block pointer tables. The proof is at the call site:
  `arg2`'s four entries are filled with `movzx eax, byte ptr [eax]`, i.e. raw
  tile BYTES 0..255, so `byte[ecx + [arg1+0x80]]` is a 256-entry table lookup.
  **Read our own findings before re-deriving them from the disassembly.**
- **Kamadan's `table_a` is the IDENTITY**, `0..50`. So for this map tile byte
  == tile type and `trnblend`'s grouping is unaffected by tag 4 — worth knowing
  before treating a Kamadan measurement as evidence about the type mapping. It
  also makes `table_a` useless as a memory needle, which cost one timed-out
  scan.
- **The client stores the tile bytes in FILE order.** The detiled spelling
  (`mapexport.detile`) does not appear anywhere in the process, so the
  reordering is ours, applied on export, and not something the client
  materialises. `table_b` does not appear in byte form at all.

Every object reachable from a pointer to the tile array is dominated by a
**stride-0x400 table of per-tile-block pointers** at each of `+0x80`, `+0xD8`,
`+0xDC`, `+0xE0`, `+0x84`. So the tile-array pointer does not sit at a small
fixed offset from the chunk, and that whole family of anchors is spent.
**What is left is the direct route: `[ebp-0x40]` in `0x0075DD50` is the chunk,
so take it from the function's own argument** — a breakpoint, a hook DLL
(CLAUDE.md carve-out 3 permits the toolchain), or a hardware watchpoint on the
tile-array pointer. Guessing offsets from data the chunk points at has now
failed four times and should not be tried a fifth.

**What this costs to finish: one live read, not more static analysis.** Two
rounds of anchored scanning have now bounded the question without answering it,
and `toolkit/harness/keytap.py` already does cross-process `ReadProcessMemory`
with ASLR-correct module bases in pure `ctypes`. Reading `chunk+0x2B4` while
standing in a map settles in one observation both what the values are and
whether they change per tile block — which is the repo's own rule (capture and
read; the wins never came from reasoning about the client).

### 7.6 THE SELECTOR IS READ: a per-cell corner PERMUTATION (OBSERVED)

**2026-08-15, Lornar's Pass, loopback, build 38833.** `int3` at `0x0075DD50`
and `0x0075E650`, injected at **t+0.4s** -- before the map exists -- with two
controls passing in the same run: the DLL's own `int3` seen by its handler,
and the caller's branch point `0x007434E5` (`test eax, 0x2000`) firing, which
is on the path and must precede either callee.

    terrain hit: YES at the LO path (0x0075E650)
    chunk 0x1CA4EFE0
    rng +0x2A4 = 0x00080012, 0x0A0E2CE4

**`chunk+0x2B4` holds 16 distinct byte values and ALL SIXTEEN ARE
PERMUTATIONS of (0,1,2,3).** Not a subset that happens to look like one -- 16
of 16, decoded as the client decodes them, `(sel >> 2k) & 3` for k in 0..3:

| byte | (c0,c1,c2,c3) | count | byte | (c0,c1,c2,c3) | count |
|---|---|---|---|---|---|
| `0xE4` | (0,1,2,3) identity | 877 | `0xD8` | (0,2,1,3) | 7 |
| `0x39` | (1,2,3,0) | 25 | `0x87` | (3,1,0,2) | 3 |
| `0x27` | (3,1,2,0) | 21 | `0x36` | (2,1,3,0) | 2 |
| `0xB4` | (0,1,3,2) | 16 | `0x4B` | (3,2,0,1) | 2 |
| `0xE1` | (1,0,2,3) | 15 | `0x1E` | (2,3,1,0) | 1 |
| `0x2D` | (1,3,2,0) | 14 | `0xC9` | (1,2,0,3) | 1 |
| `0x78` | (0,2,3,1) | 14 | `0xD2` | (2,0,1,3) | 1 |
| `0x4E` | (2,3,0,1) | 13 | `0xC6` | (2,1,0,3) | 12 |

**85.6% identity, 14.4% permuted.** So `trnblend.SELECTION = "identity"` is
right for six cells in seven and WRONG for the seventh, and the owner's read
off the isolated Blender overlay -- *"these connect a certain way ... to not
repeat corner tiles or use other mismatches like we're currently doing"* --
is confirmed: the permutation is the orientation mechanism that stops one
authored coverage shape repeating with a period of exactly one cell.

**The array is LIVE, not a fixed table.** The DLL's own header, counted from
memory a moment before the file was dumped, reported 18 distinct values and
546/1024 identity; the dump reports 16 and 877. Two reads of the same address
seconds apart disagree, which means it is regenerated per tile block -- and
the `rng` pair beside it says which block: `0x00080012` is
`(8 << 16) ^ 18`, `trnvariation.reseed(8, 18)` **observed live**, the third
independent confirmation of that function.

Capture: `vault/research/terrain/selector_lornars_tile8_18.bin`.

> **REPLICATED 2026-08-15, and the second run ended with the client ALIVE.**
> Same procedure, fresh process: hit at **t+6.4s** again, both controls PASS,
> chunk `0x1AFE7CE8`. Liveness was then polled every 15s for **three minutes
> after the hit** -- the step missing the first time -- and the client was
> alive at all twelve checks with a flat working set (~290 MB), still alive at
> 222s when it was stopped deliberately. So the instrument does not kill the
> client at the hit, and the first run's crash remains unexplained rather than
> attributable.
>
> **The claim replicates and the identity share does NOT:**
>
> | | distinct | non-permutations | identity |
> |---|---|---|---|
> | run 1 | 16 | **0** | 85.6% |
> | run 2 | 18 | **0** | 50.8% |
>
> Union across both: **18 distinct values, all 18 permutations of (0,1,2,3),
> zero exceptions.** The captures are not byte-identical and the identity
> share swings from 86% to 51%, which is the per-tile-block regeneration
> showing up as a difference rather than as an assertion. Second capture:
> `vault/research/terrain/selector_lornars_run2.bin`.
>
> **THE FIRST RUN'S CLIENT CRASHED, and the owner noticed it before I did.**
> My script exited the moment it saw the hit and never re-checked liveness, so
> I reported the run clean. It was not. What the timestamps do establish is
> that the crash came LONG AFTER the read: process start ~16:00:28.6, hit and
> file write at 16:00:35 (t+6.4s), and the harness then logged `body is in the
> map` at t+15.2s and held for thirteen further ticks. So the capture is not
> from a dying process.
>
> The cause is NOT FOUND -- no dump, and `Gw.log` simply stops mid-auth
> chatter with no error line. It is a fair suspicion that the instrument did
> it: `poke()` flips page protection on executing code from inside a vectored
> handler while ~48 threads run, and nothing here shows that is safe.
>
> Two internal checks argue the DATA survived regardless, and both would fail
> on a corrupt read: `rng` is exactly `(8 << 16) ^ 18` for the block being
> built, and all 16 selector bytes decode to valid permutations. Neither
> happens by accident. **Treat §7.6's numbers as sound and the METHOD as
> unproven** -- a re-run that ends with the client still alive is what turns
> this from one good capture into a repeatable measurement, and it should
> check liveness AFTER the hit rather than exiting on it.

**What this un-blocks and what it does not.** It answers §8's top open item.
It does NOT by itself fix the renderer: the permutation must be derived, not
captured, because a consumer cannot ship a memory dump -- so the next question
is what generates it, and the `rng` pair 16 bytes before it is the obvious
suspect now that both are observable in the same read.

### 7.7 What generates the permutation: corner pattern picks a PAIR, the PRNG picks one

**MEASURED 2026-08-15, offline, from the run-1 capture plus the archive** — no
client needed, which is why it is worth doing before another live run.

Tile block (9,18) of Lornar's Pass, 1024 cells, corner types from terrain tag
2 through tag 4, compared against the captured selector byte:

**LAW 1 — a uniform cell is ALWAYS the identity. 835 of 835, ZERO
counterexamples.** Not "usually": a cell whose four corners share one type is
never permuted. That alone kills the reading that this is a per-cell random
draw, which would put identity at 1 in 24.

**LAW 2 — for a mixed cell the corner PATTERN determines a small CANDIDATE
SET, and something picks within it.** Patterns are canonicalised
material-agnostically (`(0,1,1,1)` means "corner 0 differs, the rest agree"):

| pattern | candidates | split |
|---|---|---|
| `(0,0,0,0)` | `0xE4` | 835 |
| `(0,1,1,1)` | `0x39` / `0xE4` | 24 / 15 |
| `(0,0,0,1)` | `0x27` / `0xE4` | 21 / 17 |
| `(0,1,0,0)` | `0xE1` / `0x78` | 15 / 12 |
| `(0,0,1,0)` | `0xB4` / `0xC6` | 15 / 12 |
| `(0,0,1,1)` | `0x4E` / `0xE4` | 12 / 10 |
| `(0,1,0,1)` | `0x2D` / `0xD8` | 11 / 7 |
| three-material patterns | 4 candidates each | n ≤ 7 |

Every two-material pattern gets **exactly two** candidates in a near-even
split; three-material patterns get four. **92.2% of the block is predictable
from the corner pattern alone** (944/1024), and the residual is the choice
within each pair.

**So the generator is `f(corner pattern, one PRNG draw)`**, and the two halves
explain what was previously puzzling. The pattern half is why 18 of 24
permutations appear and the other 6 never do — only reachable candidates
occur. The PRNG half is why the identity share swung 85.6% → 50.8% between
two blocks (§7.6) while the law itself did not move: different stream, same
rule. The reseed `(tile_x << 16) ^ tile_y` and `trnvariation` already
reproduce that stream.

**CROSS-VALIDATED against run 2 (block (5,2), a different block), and the
single-block caveat above was the right one to raise:**

- **LAW 1 survives untouched.** Run 1: 835 uniform cells, 0 violations. Run 2:
  363 uniform cells, 0 violations. **1,198 of 1,198 across two captures.**
- **LAW 2's two-material pairs PREDICTED run 2 exactly.** All seven
  two-material patterns added ZERO new values out of sample, including
  `(0,0,0,1)` where run 1 saw n=38 and run 2 saw n=101. A candidate set
  derived from tens of cells predicted hundreds. That is the difference
  between a fit and a law.
- **The three-material sets were under-sampled, exactly as flagged, and they
  converge on SIX.** `(0,1,2,2)`, `(0,1,2,1)`, `(0,0,1,2)` and `(0,1,0,2)` all
  reach 6 candidates once both blocks are pooled — run 1 had seen 4, 4, 1 and
  1. Run 2 also contributes `0x6C`, a 19th permutation.

So the arity is **2 candidates for a two-material cell, 6 for a
three-material one** — which is a much sharper target for the table than "a
small set", and 91.9% of run 2's cells (941/1024) drew a value run 1 had
already named.

### 7.8 The writer is `0x0074B440`, and the generator is a SORT (2026-08-15)

**Found by walking back from the breakpoint, which is what the working
instrument is for.** `trnint3c.dll` captures 512 bytes of stack at the hit;
`[esp]` is `0x007434F8` (the return address after `call 0x75e650`, confirming
the caller) and two frames up sit `0x00745422` and `0x00745750`.

That region contains `0x00745143  lea edi, [esi + 0x1d0]`, and
`0x007451CF  call 0x74b440` passes it in `ecx`. `0x0074B440` opens
`mov [ebp-0x20], ecx`, so `this` = `chunk+0x1d0`, and at `0x0074B4EC` it
computes `this + 0xE4` -- **which is `chunk+0x2B4`.** The array nothing
appeared to write is written through a displacement of `0xE4` from a
subobject, exactly the blind spot §7.4 named. *This function was disassembled
hours earlier in the same session and dismissed, because the `+0xe4` was
matched against the wrong base.*

**`0x0074B540`.. is a SORTING NETWORK.** It loads the four corner type bytes
into `edx/edi/ebx/esi`, seeds four index values 0,1,2,3 in
`[ebp-0xc]/[ebp+8]/[ebp-4]/[ebp-0x10]`, and runs `cmp` + conditional-swap
pairs that permute **values and indices together**. The selector byte is the
resulting index permutation.

**This retires the PRNG hypothesis of §7.7.** The "coin flip" is not a random
draw -- it is *which material has the lower type id*. Deterministic, and
derivable from data we already ship, so a consumer needs no stream replay.

Predicting the byte from a plain stable ASCENDING sort of the four corner
types, against both captures:

| capture | ascending / source-index | identity-only baseline |
|---|---|---|
| block (9,18) | **95.2%** | 85.6% |
| block (5,2) | **87.0%** | 50.8% |

Descending scores 81.5% / 35.4%, so the direction is settled. The arity falls
out exactly: two materials -> 2 orderings, three -> 3! = 6, which is what
§7.7 measured before the mechanism was known.

**NOT CLOSED, and the residual has two candidate causes I have not
separated:** the block indices `(9,18)` and `(5,2)` were INFERRED by best fit
rather than read from the capture, so an off-by-one contaminates every cell;
and the client's comparator/tie-break may not be a plain stable sort. Either
produces exactly this high-but-imperfect signature. Both are cheap to settle
-- record `tile_x`/`tile_y` in the capture (the reseed at `chunk+0x2A4`
already encodes it) and transcribe the network's swap order literally.

Stack capture: `vault/research/terrain/stack_lornars_run3.bin`.

**What is still needed for a consumer**, and it is now a small question rather
than an open-ended one: the candidate TABLE (which pair each pattern maps to,
almost certainly a static array near `0x00BF78D8`'s neighbours) and the DRAW
ORDER (how many PRNG values a cell consumes, and whether uniform cells consume
one). Both are testable offline against the two captures already in the vault.

### 7.5 The seam is not where it looked — a measurement, and a bug in the probe

`scratchpad/composite.py` composites the ground from our own `layers.u16` in
texture space, with no camera and no lighting, and scores

    seam ratio = mean |dRGB| across cell boundaries / between interior pixels

Kamadan (208,238), 6×6 cells: **0.83**. Cell boundaries are no worse than the
texture's own gradient, so our per-cell *assembly* is continuous and the grid
the eye reads is **not** a seam — it is the base repeating identically, which
§8.2 says is the rectangle we did not implement.

The first run of that probe scored 1.19 and it was **the probe that was
wrong**: it flipped cell blocks for world-`+y`-up without flipping rows inside
them, so every cell was drawn mirrored and each blend ran backwards. Recorded
because it is the same failure mode as the render this arc has been trusting —
a picture that looks plausible and is measuring its own bug.

## 8. What is still open

- **The lightmap's TRANSFER CURVE.** Tag 9 is applied as of 2026-08-14
  (§6.5) but as the simplest mapping the measurement allows, `shade / 255`
  as a linear multiplier. `terrain.py` records that 348 of 349 maps saturate
  at 255, so a gamma or a scale-and-bias would fit the corpus equally well
  and none is measured. `--no-lightmap` is the control.
- ~~The SOURCE of the per-cell corner selector.~~ **READ 2026-08-15, §7.6.**
  `chunk+0x2B4` holds a per-cell **corner permutation**: 16 distinct bytes, all
  16 permutations of (0,1,2,3), 85.6% identity. `trnblend.SELECTION =
  "identity"` is right for six cells in seven and wrong for the seventh.
  **What replaces it as the open item: what GENERATES the permutation.** The
  array is regenerated per tile block (two reads seconds apart disagree), and
  the PRNG pair sits 16 bytes before it at `chunk+0x2A4` — observed live as
  `reseed(8, 18)`. A consumer must derive the permutation, not capture it.
- **The base layer's own UV rectangle** — `obj+0x68/0x6C` (span) and
  `obj+0x70/0x74` (origin), §7.2. If the caller advances the origin per cell
  the base tiles continuously and there is no 96-unit repeat; if it does not,
  there is. NOT FOUND, and it decides the thing the owner's screenshot is
  about. The per-texture atlas origin `[tex+0x10]/[tex+0x14]` is unread too.
- The 4-dword table at `0x00A73DF8` = `{3, 3, 3, 0x30}`, the terrain
  factory's argument that lands at stage record +0x10. Named, not
  understood, and asserted nowhere.

- The quadrant's ORIENTATION (which axis is `+u`) is a convention, not a
  measurement. (The two entries that stood here — T6 "DEFERRED" and "tag 3
  is not exported, so T5 pins quadrant 0" — were both stale: T6 landed and
  tag 3 is exported. Struck 2026-08-14.)
- The extra leading dependency's MEANING (§4.2): 8 files — 4 plain ATEX, 4
  DDS of which two are 512×512 V8U8 bump maps nothing decodes — paired with
  tag3b's four floats. UNVERIFIED.
- `table_b` — Kamadan's values are `{5, 7, 13, 15, 17, 19, 21, 23, 81, 85}`,
  all odd. UNVERIFIED, and not on the critical path.
- Terrain tag 0's `tex_word`, `tex_f12`, `tex_f16`. Named, not understood.
