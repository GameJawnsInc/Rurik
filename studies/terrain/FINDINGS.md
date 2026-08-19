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

**UPDATE 2026-08-19, §13.** The transfer curve is now settled: the BAKE is a
quartic ease-out `255·(1 − (1 − N·L)⁴)`, not the linear `shade/255` this
section assumed, read byte-exact from the generator. **And two claims here are
now CONTESTED by the generator/apply read (§13.3):** that `mul r0, v0, r1`
multiplies by "the vertex diffuse colour = tag 9", and that tag 9 is "applied
per VERTEX". The multiply is real, but both terrain vertex shaders write a
DEPTH-FADE to `v0`, not the lightmap, and where the baked lightmap reaches the
screen was NOT FOUND statically — a live check, not a disassembly one. The N·L
identification of tag 9 stands (it is a baked directional lightmap); how the
renderer consumes it does not, yet.

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
> **BOTH CRASHES WERE MISSED BY THE SAME DEFECT IN MY LOOP, and the owner
> caught both.** The only check was "does the process still exist". It does:
> the ArenaNet assert box is a MODAL DIALOG INSIDE THE SAME PROCESS, so
> `Get-Process` reports ALIVE for as long as it is up. "Alive at all twelve
> checks" and "crashed" are perfectly compatible, and no amount of polling
> liveness would ever have separated them. `crashwatch.ps1` now watches for a
> titled top-level window that is not `ArenaNet_Dx_Window_Class`, which is the
> signal that actually exists -- `Crash.dmp` is NOT reliable: after the
> 2026-08-15 crash no dump existed under the run directory or `%TEMP%`.
>
> **AND THE SECOND DUMP EXONERATES THE INSTRUMENT.** It is an ArenaNet
> assertion in CHARACTER code, with no terrain frame anywhere in the trace:
>
>     Assertion: level < arrsize(s_attribPoints)
>     P:\Code\Gw\Char\CharData.cpp(202)      build 38833
>
> `s_attribPoints` is visible at `ebx-32` as `6, 7, 9, 11, 13, 16, 20,
> ffffffff`, and the failing thread's entry is `0x0024BB99` -- a worker, not
> the render thread. Our three `int3` patches are all one-shot, restored
> before this point, and none is in `CharData`. `START_LEVEL = 1`, so it is
> not the level in `CHARACTER_UPDATE_FACTIONS` either. Filed as a server-side
> character-data bug, out of scope for this arc.
>
> So §7.6's crash is now **probably the same assert rather than unexplained** —
> same client, same server, same character — but that is INFERENCE, not
> measurement: the first crash produced no dump. Treat it as a lead.
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

### 7.9 CLOSED: a selection-sort network, 2048 of 2048 (2026-08-15)

`tile_x`/`tile_y` come free from the reseed: `chunk+0x2A4`'s FIRST dword is the
seed unstepped, so run 1's `0x00080012` is tile **(8,18)** and run 2's
`0x00040002` is **(4,2)**. §7.7's best-fit blocks were (9,18) and (5,2) --
**off by exactly +1 in `tile_x`, both times**, a consistent convention error
rather than noise, and correcting it did NOT move the score. Alignment was
never the residual.

Nor was the other candidate: sorting the RAW tile bytes instead of the mapped
types scores identically (Lornar's `table_a` is not the identity, so this was
a real test), and reversing the tie-break collapses to 0.5%.

**The residual was that the client's sort is UNSTABLE.** The misses are
interior, scattered, and every one is a cell with EQUAL corners coming out in
an order `sorted()` cannot produce: `(4,4,2,4)` yields its equal 4s as 1,0,3,
not 0,1,3; `(4,4,4,2)` yields 1,2,0. A stable sort is stable by construction,
which is why it plateaued at 95%/87% no matter what else was varied.

Testing the standard 4-element comparator networks against the 39 observed
ordering signatures identifies it outright:

| network | strict `>` |
|---|---|
| **selection `[01][02][03][12][13][23]`** | **39/39** |
| bubble / insertion | 30/39 |
| optimal-4 | 29/39 |
| odd-even | 25/39 |

**That is the sequence the disassembly already showed** -- `cmp ecx,edi`,
`cmp ecx,ebx`, `cmp ecx,esi`, `cmp edi,ebx` at `0x0074B57C`.. is element 0
against 1, 2, 3, then 1 against 2, 3. So the code and the data agree, and the
rule generalises to all 75 signatures rather than needing the 39-entry table.

    v = corners; idx = [0,1,2,3]
    for a, b in ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3)):
        if v[a] > v[b]: swap v[a],v[b] and idx[a],idx[b]
    selector = sum(idx[k] << 2k)

**Verified cell by cell: 1024/1024 on tile (8,18), 1024/1024 on (4,2),
2048/2048 total.** Landed as `trnblend.corner_selector` /
`select_corners`, wired into `map_layers`, and `SELECTION` is now
`"selection-sort-network"` instead of `"identity"`.

`test_trnblend.py` §4 runs the derivation against both captures and demands an
exact 2048/2048; it skips loudly without the vault. **A near-match there is a
FAIL by design** -- 95% is what the wrong model scored, and treating it as
"close enough" is exactly how it survived three rounds of tuning.

**One consequence worth stating.** The base layer is now whichever corner
SORTS FIRST, not necessarily the cell's own tile. §6.3 flagged that "which of
them is the opaque base can differ" if the identity assumption was wrong; it
was, and it does. `test_trnblend`'s far-edge check asserted the old behaviour
and was rewritten to test replication directly.

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

### 7.10 The permutation is LOST AT THE FORMAT BOUNDARY (2026-08-15)

Closing the selector (§7.9) did not make the ground look right, and the owner
named the symptom precisely from a Blender screenshot: *"tile selection still
looks random. corners where there should be half-and-half. just mismatched."*

**The layer model is NOT the fault, and that was measured before blaming it.**
Over 7,156 mixed cells of Kamadan, the UNION of each material group's overlay
coverage maps to exactly the right PHYSICAL corners -- **0 failures**. (The
first version of that check compared each overlay against the whole group and
reported 552 "wrong"; it was the check that was wrong, because `_emit`'s
two-layer path deliberately splits a group across two quadrants whose union is
the group. `(25,3,25,25)` emits `{2,3}` and `{0}`, and `{0,2,3}` is right.)

**The defect is in the interchange.** `layers.u16` carries

    bits 0..7 tile   bits 8..9 quadrant   bit 15 rotated

and **no permutation**. Since §7.9 the exporter picks a quadrant whose authored
alpha covers corners in PERMUTED index space, then hands the consumer only
`(tile, quadrant, rotated)`; `tools/blender/import_gwmap.py` places that alpha
by a fixed `LOOP_CORNER` in PHYSICAL space. While `SELECTION` was `"identity"`
the two spaces coincided and nothing showed. They no longer coincide for
**about one cell in seven**, and exactly those cells draw their coverage shape
in the wrong orientation -- a half-edge landing as a corner wedge, which is the
symptom reported.

**AND THE TEST CANNOT SEE IT.** `test_trnblend`'s "no overlay covers a corner
that belongs to the base" computes both sides in the same permuted space, so it
agrees with itself by construction. A check that cannot fail is not a check --
this file has said so about other people's code twice, and here it is ours.

Two candidate fixes, NEITHER chosen, because choosing by reasoning is what
produced the last three wrong turns in this arc:

1. **Resolve it in the exporter** -- map the permuted group mask back to a
   PHYSICAL mask before the `COVER_PRIMARY` lookup, so `(quadrant, rotated)`
   already lives in the consumer's space. Format and importer unchanged.
2. **Widen the format** to carry the selector byte and teach the importer to
   apply it. More invasive, and it pushes client semantics into a consumer
   deliberately kept dumb.

**What decides between them is a measurement that is already built.** The
client assembles the packed `(coverage << 16) | tex` array at `[ebp-0x10]`
immediately before `call 0x757a80` at `0x00761A25`. An `int3` there dumps the
client's OWN per-cell layer descriptors; diffing those against our `layers.u16`
for the same tile block settles whether the client's coverage is expressed in
permuted or physical space, which is precisely what option 1 assumes and has
not verified. The instrument works (§7.6), and the injection window is the
first ~6 seconds of the map load.

### 7.11 THE COVERAGE QUADRANT IS NOT A FUNCTION OF THE CORNERS (2026-08-17)

§7.10 named two candidate fixes and said an `int3` at `0x00761A25` would
decide between them. It ran, and it **refutes the premise both fixes rested
on**. Neither would have worked.

**THE CAPTURE.** `trnhook/trnlayers.c` patches the `call 0x757a80` at the end
of `TrnTexBlendHi` and, instead of restoring on the first hit, **emulates the
5-byte `call rel32`** — push `site+5`, set `Eip` to the callee — so the
breakpoint stays armed and every cell is captured. 2,716 cells hit, 512 stored,
injected at t+1.4s, dump at t+6.7s, **client alive afterwards**. Each entry is
a window of the live frame, which carries the whole answer in one place:

    [ebp-0x10] [ebp-0x0C] [ebp-0x08]   the packed (coverage<<16)|tex descriptors
    [ebp-0x34] [ebp-0x30] [ebp-0x2C] [ebp-0x28]   the four corner TYPES

Slot 0 is the base and its cover word is the VARIATION quadrant, not a mask —
confirmed on `(2,4,4,4)`, where slots 1-2 are `q0`+`q1` for the second
material, exactly what `COVER_PRIMARY[14]`/`COVER_SECOND[14]` predict.

**THE RESULT, and it is a comparison of the client against ITSELF, so it does
not depend on how we read the bits:** of the 26 corner-type tuples seen more
than once, **24 produce more than one overlay result.**

    (2,2,2,4) -> 0x8003 x12 | 0x0001 x6 | 0x0003 x4 | 0x8001 x4
    (2,2,2,3) -> 0x0003 x10 | 0x0001 x4 | 0x8001 x3 | 0x8003 x2
    (2,2,4,4) -> 0x8000 x5  | 0x0000 x5 | 0x0002 x4

Identical corner configurations, up to four different cover words. **The corner
types explain at most 50.8% of cells.** And the alternatives are STRUCTURED,
not noise: `(2,2,2,4)` draws from exactly `{q3, q1, q3R, q1R}`, the four
single-corner shapes. That is a CANDIDATE SET with a per-cell pick — the same
shape as §7.7's finding about the selector.

**So `trnblend` cannot reproduce this, structurally.** It is deterministic in
the corner types and always emits `COVER_PRIMARY[mask]`, one fixed member of
the candidate set. Measured head-to-head on identical inputs: **65 of 212
cells, 30.7%.**

**This is what the owner is looking at.** "Tile selection still looks random" —
part of it *is* random, and we draw one fixed representative everywhere retail
varies. §7.10's permuted-vs-physical question is not the bug, or not the main
one.

**WHAT IS NOT ESTABLISHED, and must not be assumed.** What drives the pick. The
obvious candidate is the PRNG at `chunk+0x2A4` — same generator as the
variation, same answer-shape as §7.7 — but it is NOT measured, and this arc has
three retractions from reasoning past the evidence. The next capture should
record the PRNG state beside each cell and test whether the draw predicts the
choice; the instrument now captures thousands of cells per run and the client
survives it, so this is cheap.

**A CAVEAT ON THIS CAPTURE.** 512 cells from one tile block of Lornar's Pass.
Reconstructing the observed sets through `QUADRANT_COVERS` did NOT line up
cleanly — single-layer groups accompany physical sets dominated by `{2,3}` and
`{3}` across every cover word — which suggests the corner indexing in that
frame may not align with the coverage bit order the way this section assumes.
**The variability result is independent of that** (client against itself, same
inputs); the specific candidate-set memberships are softer and should be
re-derived once the frame's index convention is pinned.

### 7.12 The PRNG is EXONERATED, and the variation rule is confirmed live (2026-08-17)

§7.11 named the PRNG at `chunk+0x2A4` as the obvious suspect for the coverage
pick and refused to assume it. A second capture (`trnlayers2`, window widened
to `ebp+0x20`, PRNG chased through `[ebp-0x18]+0xD4`) settles it, and the
suspect is innocent.

**THE STREAM IS OURS, PROVEN ON LIVE DRAWS.** The pair at `chunk+0x2A4` is not
two RNG states: the first dword is constant `0x00000002` across all 512 cells
and is a field; the SECOND is the live stream, distinct on every cell.
Stepping it with `trnvariation.rng_next` — magic-number division quirk
included — lands on the next cell's value **511 times out of 511**. So the
generator advances **exactly once per cell, unconditionally, with no gaps**,
and our port reproduces the client bit-for-bit over 512 consecutive draws. That
is the strongest confirmation `trnvariation` has: previously it was checked
against its own arithmetic and two static constants, never against the client's
running stream.

**THE DRAW IS SPENT ON THE VARIATION, AND ONLY THAT.**

| hypothesis | result |
|---|---|
| `draw & 3` == BASE quadrant | **512 / 512 = 100.0%** |
| `draw & 3` == overlay quadrant | 75 / 303 = **24.8%** (chance = 25%) |

The first is exact. The second is chance to one decimal place. **One draw per
cell also makes the coverage hypothesis impossible on its face** — the single
draw is already consumed by the variation, so there is nothing left for a
second per-cell choice to consume.

So §7.11's variability is real and its cause is NOT the PRNG. Two corroborating
details from the same capture: `arg4` (tag 3) is 0 on every cell, i.e. "defer
to the PRNG", which is exactly the branch `trnvariation` models; and `arg3`,
the selector, is `0xE4` on the majority with 15 distinct values overall,
consistent with §7.6's identity share and confirming this frame carries the
same selector §7.9 closed.

**What is left for §7.11's cause**, now that the cheap answer is gone: the
overlay quadrant comes from `COVER_PRIMARY`/`COVER_SECOND` indexed by a corner
MASK, so if identical corner TYPES give different cover words, the mask being
indexed is not derived from the types alone. The selector permutes which corner
feeds which position — so the mask is built in permuted space, and cells with
equal types but different selector bytes would index different rows. **That is
now testable offline against this capture** (`arg3` and the types are both in
the frame) and needs no client. It also folds §7.10 back in: if the mask is
permuted, the consumer needs the permutation, which is exactly what
`layers.u16` drops.

### 7.13 CLOSED: the cover word is a function of (types, SELECTOR) (2026-08-17)

Run offline against §7.12's capture, no client needed, because `arg3` and the
corner types sit in the same frame:

| hypothesis | groups | ambiguous | cells explained |
|---|---|---|---|
| corner types alone | 43 | 24 | 21/212 = **9.9%** |
| **types + selector byte** | 87 | **0** | **212/212 = 100.0%** |

**Zero ambiguous groups.** The client's overlay cover words are fully
determined by the corner types together with the per-cell selector permutation.

**So §7.10, §7.11 and §7.12 are ONE finding, not three.** The mask fed to
`COVER_PRIMARY`/`COVER_SECOND` is built in PERMUTED space (§7.9's selector
decides which corner feeds which position), so two cells with identical corner
TYPES but different selector bytes index different table rows and legitimately
draw different quadrants. That is exactly §7.11's "not a function of the
corners" — the missing variable was never randomness, and §7.12 ruled the PRNG
out at 24.8% against a 25% baseline. `trnblend` matches on 30.7% because it
emits one fixed representative of a set the client varies.

**And this is why the ground looks wrong.** `layers.u16` carries
`(tile, quadrant, rotated)` and drops the permutation (§7.10), so a consumer
cannot reconstruct which row was indexed. While `SELECTION` was pinned to the
identity the two spaces coincided and nothing showed; since §7.9 they do not.

**What this makes actionable.** The fix is no longer a guess between two
options: the exporter must emit the cover word for the mask it ACTUALLY built
in permuted space — which it can, because `corner_selector` is exact
(2048/2048, §7.9) and the table lookup is already ours. The consumer stays
dumb and the format stays as it is. **The check that must accompany it** is the
one this arc kept failing to write: compare our emitted cover words against
this capture's, per cell, keyed on (types, selector) — 212 mixed cells of
ground truth that no amount of internal agreement can fake.

**Scope**: 512 cells, one Lornar's Pass tile block, all with `arg4 = 0`
(tag 3 deferring to the PRNG). A block with authored tag-3 values is not
covered and should be captured before the rule is called general.

### 7.14 CORRECTED and IMPLEMENTED: the mask is PHYSICAL (2026-08-17)

§7.13 concluded "the mask is built in PERMUTED space". **That was wrong, and
the offline work that was supposed to implement it refuted it instead.**

**FIRST, A FALSE ALARM WORTH RECORDING.** `corner_selector` scored only 71.5%
against the captured `arg3`, which looked like §7.9 collapsing. It was not: the
prologue stores each corner AFTER fetching it through `arr[(sel>>2k)&3]`, so
`[ebp-0x34..-0x28]` holds the corners **already permuted**. Measured:
**512 of 512 are non-decreasing.** Comparing a sort against its own output is
meaningless, and every "mismatch" was a cell whose types were already
ascending, where our sort correctly returns the identity. §7.9 stands
untouched.

**THEN THE REAL MECHANISM.** With identical SORTED types the client still
varied — `(2,2,2,4)` giving `0x1` in one cell and `0x8003` in another. Decoding
those through `QUADRANT_COVERS`: `q1` covers `{1}`, `q3` rotated covers `{0}`,
`q3` covers `{3}`. Three different PHYSICAL corners. So the table is indexed by
the physical mask, and the selector's job is only to **sort the types so equal
ones sit adjacent**, making the grouping loop a single pass.

| mask built from | vs the client |
|---|---|
| sorted positions (what this module did) | 66/212 = **31.1%** |
| **PHYSICAL positions, via `perm[k]`** | **212/212 = 100.0%** |

**LANDED.** `cell_layers` takes `perm` and ORs `1 << perm[k]` instead of
`1 << k`; `map_layers` computes it from `corner_selector`. The interchange is
unchanged and the importer is unchanged — §7.10's "widen the format" option is
moot, because a physical mask is already in the consumer's space. That is the
fix §7.13 argued for, arrived at by the opposite reasoning.

**AND THE CHECK THAT WOULD HAVE CAUGHT ALL OF THIS** is now
`test_trnblend.py` §5: our cover words against the client's own descriptors,
cell for cell, **212/212 required exactly** — a near-miss is a FAIL, because
the wrong model scored 31.1% and no amount of internal agreement distinguished
it. Sections 1-3 check our model against our model; §4 and §5 check it against
the client. The suite scores 32 with the vault, floor 26 without.

**Scope unchanged from §7.13**: 512 cells, one Lornar's block, all `arg4 = 0`.

### 7.15 The fix reached trnblend and NOT the exporter (2026-08-17)

Landing §7.14 and re-exporting changed **exactly zero bytes** — 0 of 186,368
Kamadan cells. The fix was correct and it went nowhere.

`map_layers` and `mapexport.build_blend_layers` are **two copies of the same
loop**. §7.14 corrected the first; the exporter calls `cell_layers` directly
and kept the pre-selector behaviour. So every `.blend` scene ever rendered from
this arc — including the ones whose screenshots drove §7.10 and §7.11 — was
built without the selector at all.

With the exporter fixed too:

| | cells changed | of mixed |
|---|---|---|
| Kamadan | 26,211 (14.1%) | **77.5%** |
| Lornar's Pass | 111,561 (41.9%) | **76.4%** |

which agrees with the 31.1% match rate §7.14 measured against the client:
roughly three quarters of mixed cells were drawing the wrong row. Rebuilt
scenes move accordingly — Kamadan 58,456 → 48,689 overlay faces with rotated
up 14,183 → 20,113; Lornar's 252,291 → 216,623 with rotated 59,096 → 86,539.

**ONLY THE OUTPUT DIFF CAUGHT THIS.** Every test was green before and after,
because both copies were internally consistent and §5's client check exercises
`cell_layers`, which was already right. `test_mapexport` now asserts the two
loops agree cell for cell, with a fixture that must contain mixed cells or the
check is vacuous. The general lesson is the repo's own: **a rule implemented
twice will drift, and a suite that tests each copy against itself cannot see
it.** Diff the artifact, not just the unit.

### 7.16 The base material was bound from the WRONG TILE (2026-08-17)

The owner rebuilt Kamadan after §7.15 and reported it unchanged: *"still just
looks like randomly chosen tiles."* That is not a blending symptom — coherent
regions had become a scatter, which means cells were drawing a texture that was
not theirs.

**The layer data was innocent, and the compositor proved it.** The same
`layers.u16`, composited in TEXTURE space with no Blender involved, gives grass
above and dirt below with an organic scalloped boundary, seam ratio **0.79**.
So the fault had to be downstream of the data.

**THE CLIENT'S BASE IS THE CORNER THAT SORTS FIRST, NOT THE CELL'S OWN TILE.**
Tested against the capture on the cells where the two hypotheses disagree:

| base texture equals | cells |
|---|---|
| **the SORTED-FIRST corner's type** | **102** |
| the PHYSICAL corner 0's type | 0 |
| neither | 0 |

**And `import_gwmap.py` was binding `material_index` from `gwmap.tiles`** —
the cell's own byte — while the overlays mask the COMPLEMENT of the base. Bind
a different base underneath and every mixed cell shows a material its overlays
were never computed against. Affected **9.5% of Kamadan's faces and 29.0% of
Lornar's**.

Fixed: the base binds from `layers[3*c] & 0xFF`, falling back to `tiles` only
for exports predating the sidecar, where the two are equal by construction.

**THIS IS THE THIRD PLACE THE SAME RULE LIVED.** `trnblend.map_layers`,
`mapexport.build_blend_layers` (§7.15) and now the importer each carried their
own idea of what the base is, and each had to be corrected separately. §7.15's
lesson generalises: a rule implemented three times will drift three ways.

**T5's checks encoded the superseded rule and had to be updated, not
weakened.** Three checks asserted "faces bind by their tile byte" at full
coverage — true while the selector was the identity, false since §7.14. They
now assert the BASE LAYER's tile, still at full sha256 coverage over all
212,992 faces. `test_blenderimport` is 118 green.

### 7.17 Kamadan's stairs: present, correct, and ERASED by their own alpha (2026-08-17)

Reported by the owner against the rebuilt scene: the stairs are missing, but
Blender draws a selection outline where they should be. The outline was the
clue — an outline means the OBJECT is there.

**It was, entirely.** `prop_0005_m4`: 204 vertices, 112 polygons, five
materials, dimensions 775 x 988 x 276 (stair-sized), not hidden in viewport or
render. Across the scene, 516 props have geometry, none empty, none degenerate.
Nothing was missing.

**ALPHA IN THIS CORPUS IS NOT ALWAYS TRANSPARENCY**, which this arc already
knew for terrain (§6.2, where it is a coverage mask) and had not carried over
to props. Two of the five materials draw textures whose alpha is **below 16 on
96–98% of pixels**:

| texture | mean alpha | fraction < 16 |
|---|---|---|
| `tex_32EED.png` | 7.9 | **98.2%** |
| `tex_32EF5.png` | 8.9 | **96.5%** |

The importer wired every texture's alpha into the BSDF unconditionally, and
Blender's default `HASHED` blend then erased those faces. The stairs were
rendered *exactly as instructed*, into nothing.

**The class is small and the corpus says so.** Over Kamadan's 598 prop
textures: **350 fully opaque, 241 genuine cutouts or blends, 7 erasers (1.2%)**.
So a blanket "ignore alpha" is wrong — it would flatten the 241, and the palm
trees beside these stairs are cutouts that render correctly today.

**Why not the material table's `blend` flag**, which is already decoded and
would seem the principled answer: it separates *blended* from the rest, and
foliage is alpha-**tested**, not blended. Using it would have made the palms
opaque rectangles. It solves a different problem.

**The rule, and it is a floor rather than a guess:** alpha that would erase
substantially the whole surface cannot be the artist's transparency, and the
client plainly draws these surfaces — the stairs are walkable in game.
`modelexport._alpha_class` records `opaque`/`cutout`/`erases` per texture at
export, where the pixels are already in hand; the importer skips the alpha
wiring for `erases` only. Measured on Kamadan: 428 texture entries classified,
38 slots across **2 distinct images**, and 54 of 272 scene materials now
correctly opaque.

**The owner's read was that stairs might be "a special type of prop since
they're walkable".** They are not — walkability lives in the pathing chunk and
nothing about this prop is special. The outline being visible while the mesh
was not is what distinguishes "absent" from "invisible", and it is worth
keeping as a diagnostic.

### 7.18 §7.2 REFUTED: there is no second rectangle (2026-08-17)

§7.2 read two UV rectangles in `0x00757A80` — a masked path using the quadrant
table, and an "unmasked" path with its own span (`obj+0x68/0x6C`) and origin
(`obj+0x70/0x74`) — and concluded the BASE layer used the second one. That
conclusion stood for three days as the likeliest cause of large-scale
repetition. **It is wrong.**

**The base never takes that path. 0 of 512 cells.** `0xFFFF` — the value that
selects the unmasked branch — appears only in slots 1 and 2, where it marks an
UNUSED slot (300 and 421 occurrences). Every base descriptor carries a real
cover word, and those are the four variation quadrants in near-equal
proportion: `0x0` 123, `0x1` 125, `0x2` 125, `0x3` 139.

**And the rectangle itself says so.** Captured per cell and constant across all
512: **span = 0.000488 = 1/2048, origin = 0.0625 = 1/16.** A span of 1/2048 is
SUB-TEXEL on a 256-pixel texture — it samples essentially one point. That is
not a terrain rectangle; it is what you write to make an unused slot draw
nothing.

So the `0xFFFF` branch is the no-op path for empty slots, the base goes through
the same quadrant machinery as everything else (which §7.12 already showed from
the other side: `draw & 3` == base quadrant, 512/512), and **there is no second
rectangle to implement.**

**What this costs, honestly.** §7.2 was the last open item that could have
explained a 96-unit repeat, and it has evaporated. If the ground still repeats
visibly at distance, the cause is NOT a missing UV rectangle and the next
suspect is unknown — the candidates left are the lightmap transfer curve
(§8, weak) or something nobody has looked at. If it does not repeat visibly,
there was never anything here to fix.

**A note on how this was found**, because it is the same shape as §7.14's
correction: §7.2 was read out of the disassembly and never tested against a
running client. The test was one added field in an instrument that already
existed and one run. Three days of "likeliest cause" against ten minutes of
measurement.

### 7.19 The whole corpus, offline: 361 maps, and only the 8 shapes exist (2026-08-17)

Everything in §7.6-§7.18 rests on **two tile blocks of one map**. The
derivation itself needs no client, so it can be run over the archive's entire
map population, and was:

| | |
|---|---|
| maps processed | **361 of 361** (`flags == 259`, build 38833) |
| cells sampled | **108,807** |
| layer counts | 64,070 single / 22,941 two / 21,796 three |
| distinct coverage masks emitted | **8** |
| refusals, exceptions, out-of-range quadrants | **NONE** |

**The 8 masks are the interesting number.** They are
`{1, 2, 3, 4, 5, 8, 10, 12}` — exactly `QUADRANT_COVERS` and its rotations:
`q0=12, q1=2, q2=5, q3=8`, rotated `3, 4, 10, 1`. Over 108,807 cells of every
map in the archive the grouping **never once asks for a coverage shape the
authored quadrant set cannot draw**, and never emits a ninth. A wrong mask
rule would have to land outside that closed set eventually; across the corpus
it does not.

This does NOT extend §7.14's 212/212 client agreement beyond its one block —
nothing here is compared against the client, and a rule can be internally
closed and still wrong, which is the trap this arc fell into three times. What
it does rule out is the cheaper failure: a grouping that produces impossible
masks, overflows three layers, or throws on some map nobody exported. It does
none of those anywhere.

**Cost: one command, no client, no vault captures.** Worth re-running after any
edit to `cell_layers` or `corner_selector`.

### 7.20 ANSWERED: the ground does not repeat beyond the mechanism's floor (2026-08-18)

§7.18 killed the last mechanism-level suspect for large-scale repetition, which
left §8's top item as a pure measurement: composite the ground exactly as the
export says to draw it and MEASURE the periodicity, instead of eyeballing a
render. `studies/terrain/repeatprobe.py` is that instrument — the §7.5/§7.16
texture-space compositor rebuilt (the original died with its session
scratchpad, which is why this one is checked in), with its predictions stated
before the first run:

- **P1, instrument validity**: the pre-arc model (identity selector, quadrant
  0 everywhere — "pinned") must show autocorrelation peaks at cell-period
  lags, or the instrument cannot see repetition and the run measured nothing.
- **P2, the question**: if the closed mechanism is what stops the repetition,
  the export ("full") collapses to an ideal-random-quadrant floor ("random":
  base quadrant drawn uniformly per cell, fixed seed); if instead
  full ≈ pinned, the ground still repeats and no hypothesis is left.

**The gate before the measurement** — §7.15's lesson, diff the artifact — the
probe re-derives `layers.u16` from `tiles.u8` + `variation.u8` through
`trnblend`/`trnvariation` and demands byte equality: **PASS on all 186,368
Kamadan cells and all 266,240 Lornar's cells.** The gate caught a real
misreading on its first firing: `.variation.u8` is the AUTHORED tag 3, not
the resolved quadrant, and feeding it in raw tripped the gate on exactly
**75.02% of cells = P(draw ≠ 0)** — the failure signature that identified the
fix. (On Kamadan the authored array is all-zero: the whole city defers to the
PRNG.)

**The result, prominence of the autocorrelation peak at the 1-cell lag**
(luma, mean of the +x/+y profiles; identical-neighbours = adjacent cell pairs
drawing byte-identical ground):

| | full | random floor | pinned ceiling |
|---|---|---|---|
| Kamadan, whole GRID (68% oob filler, see below) | **+0.1050** | +0.1051 | +0.1821 |
| Kamadan focus (256,0), oob filler | +0.6861 | +0.6935 | +0.9831 |
| Kamadan focus (84,165), plaza | +0.0520 | +0.0520 | +0.1063 |
| Kamadan focus (220,265), beach path | +0.1432 | +0.1445 | +0.2897 |
| Kamadan identical-neighbours | **19.27%** | 19.42% | 77.87% |
| Lornar's, whole map | **+0.0239** | +0.0240 | +0.0460 |
| Lornar's focus (0,513) | +0.0481 | +0.0475 | +0.1290 |
| Lornar's identical-neighbours | **8.62%** | 8.74% | 34.94% |

**P1 passes everywhere, and P2 lands on the good branch: the export sits ON
the random floor on every window of both maps** — between −2.5% and +0.7% of
the pinned−random span. The cell arrangement we ship extracts everything the
four-quadrant mechanism can give; there is no residual arrangement defect to
find. Visually the same: the pinned composite shows one-cell staircase edges
on every material boundary and a woven lattice in uniform ground; the full
composite's boundaries are organic (the owner's own criterion from the
retail photograph). PNGs and per-window metrics:
`vault/research/terrain/repeatprobe/`.

**ADVERSARIALLY VERIFIED before this section landed** — two independent
skeptics, each told to refute, both returning SURVIVES, and one real flaw
between them, corrected here rather than found later:

- **The flaw: "whole map" was the wrong label.** 67.8% of Kamadan's cell grid
  (126,408 of 186,368) is a single out-of-bounds filler tile, so the whole-GRID
  row above compares conditions over mostly-void — valid as a comparison (all
  three conditions share the void) but not a statement about "the ground". The
  skeptic recomposited the two verified real-terrain windows at the same res=8
  coarseness: full/random/pinned = **0.0458 / 0.0457 / 0.0740** (plaza) and
  **0.1142 / 0.1145 / 0.2391** (beach) — the same pattern, on real ground.
- **The sampling conventions held to the byte.** An independent hand-sampler
  (PIL, not the toolkit's decoder) reproduced `build_patches` exactly on all
  non-rotated words; the rotated ones differed by exactly one texel, traced
  algebraically to two equally valid discretizations of the same 180°
  rotation about the same centre — applied uniformly to all three conditions,
  so it cannot move a separation measured at 3–10×.
- **The verdict is not a luma artifact.** Recomputed on R, G, B, R−G and G−B
  directly from the PNGs: chroma carries up to 3.5× the periodicity signal of
  luma, and full ≈ random holds on every channel of every window. And
  "random" is a genuine perturbation, not a near-clone of full — it moves
  51–54% of pixels.

**Two numbers worth keeping.** The FLOOR is a property of the ART, not the
arrangement, and that is measured rather than asserted: the mean pairwise
correlation between a texture's four quadrant windows is **+0.611** for
Kamadan's filler tile 25 (floor +0.69) and **+0.148** for Lornar's snow
tile 2 (floor +0.05) — the floor tracks how alike the artist drew the four
variants, and the client has the same floor by construction. And at DISTANCE
the question dissolves: pooled to 1 px per cell, every condition including
pinned scores ≈ +0.01 — cell-scale repetition is invisible at range in any
model; what survives at range is material-region structure.

**The renders agree.** Headless EEVEE renders of the rebuilt scenes
(1280×720, camera at eye height and high-oblique) show no lattice: Lornar's
snowfield-to-horizon shot and Kamadan's canyon path are organic at every
distance in frame. Same directory. Three render-side facts a follow-on
session should not rediscover: **the scenes carry NO light objects** (the
lighting is baked into the `gw_light` vertex colours; render with a plain
white world background, strength 1.0 — an added sun double-lights and washes
the albedo flat), **`gwcam.py` SAVES the .blend it opens** when run as its
docstring shows (`bpy.ops.wm.save_mainfile` on exit — open via
`open_mainfile` and never save, or work on a copy), and **kamadan.blend has a
void-skirt plane at z ≈ −5002** holding 17.7% of its terrain vertices, which
any "find open ground from the bbox" heuristic finds first.

**What this closes and what it does not.** It closes §8's "does the ground
still repeat at distance" — it does not, beyond a floor the art itself sets.
The arrangement we ship is the arrangement the client computes (§7.9's
2048/2048 selector, §7.12's 511/511 stream, §7.14's 212/212 cover words), so
any repetition retail avoids that our RENDER does not, it avoids by rendering
means — fog, mip selection, the lo path, the t3 diffuse/specular lerp, the
lightmap's transfer curve — not by a different layout. The "no hypothesis
left" branch did NOT fire. Scope: the client-truth side still rests on one
`arg4 = 0` Lornar's block (§7.13's caveat), unchanged by this section.

### 7.21 CLOSED: the arg4 = 0 caveat, and claim 1 confirmed against the client (2026-08-18)

**Every prediction §8 recorded before this run came back exact.** Row 34429,
tile block (4,3), 1024 of 1024 cells, client alive afterwards with no assert
dialog.

| | predicted, before the run | measured |
|---|---|---|
| authored / deferred cells | 590 / 434 | **590 / 434** |
| `arg4` histogram | — | `{0:434, 1:189, 2:198, 3:203}` |
| cells where H1's two readings differ | **331** | **331** |

    H1  base quadrant == draw-CONSUMED model : 1024/1024 = 100.0%
    H1  base quadrant == draw-SKIPPED  model :  693/1024 =  67.7%
    H2  an authored cell draws its authored value : 590/590
    H3  our cover words == the client's           : 735/735

**H1 — `trnvariation` CLAIM 1 IS CONFIRMED, and this is its first test.** The
claim is that an authored cell *still consumes its place in the PRNG stream*
and then ignores what it drew; the rival skips the draw and shifts every later
cell in the tile. Both readings are identical on a block where tag 3 is zero,
which is every block ever captured before this one — so a claim carried since
2026-08-14 had never been exposed to a case that could refute it. It survives
at 1024/1024, and the 331 cells where the two disagree are **exactly** the 331
predicted: on every one of them the consume model is right and the skip model
is wrong. 67.7% is what the wrong model scores, which is the useful number —
it is high enough to look like agreement to anyone not differencing the two.

**H2** settles the other half: an authored cell's base quadrant IS the authored
value, 590 of 590, and quadrant 0 appears only among the 434 deferred cells,
which is §3.2's "tag 3 can only pin 1–3" seen from the client side.

**H3 — §7.14 GENERALISES.** The physical-mask cover-word rule reproduces the
client on **735 of 735** mixed cells of a block where 58% of cells carry
authored tag 3. The 212/212 was not one block's accident, and tag 3 does not
interact with the mask at all.

**SO §7.13's SCOPE CAVEAT IS DISCHARGED.** Every client-truth number in
§7.11–§7.14 rested on one Lornar's block with `arg4 = 0`; the rules now hold on
a second map, a second block, and the authored branch that block could not
reach.

**THE INSTRUMENT HAD TO BE AIMED FIRST, and that is the reusable part.**
`trnlayers.c` stores the first 512 cells that hit the breakpoint, so the block
it captures is whichever the client builds first — four runs, four different
un-requested blocks. Standing in the right place cannot aim it either: ranked
by authored density the top four blocks in the archive have **zero** walkable
probes, decorative terrain no player reaches. `trnblock.c` filters on
`chunk+0x2A4`'s first dword, the block's unstepped reseed `(tx << 16) ^ ty`,
and keeps the patch armed until that block completes. This run saw **33,639
hits across 32 distinct blocks** — the client builds the whole map at load —
and kept the 1024 that matched. `layers_row34429_t4_3_tag3.bin`.

**AND IT TOOK TWO RUNS, for a reason worth carrying.** The first came back
`hits 0`, with a perfectly correct ASLR-resolved breakpoint at `0x00DB1A25`
(the client relocated to `0x00A50000`). The client started at 16:30:45, the
map loaded at 16:30:52, and the injection landed at ~16:31:15. **Terrain
builds ONCE, at map load** — arming the hook after that point sees nothing at
all, and a human-paced "poll for the pid, then inject" round trip does not fit
in seven seconds. `autoinject.py` waits at 25 ms and injects in the same
breath: 1.5 s after the process appeared, on a run started *before* the client
was launched. A zero-hit capture is also now diagnosable rather than
ambiguous, because the sidecar records hits, matches and every block id seen —
"the target never built" and "the hook never fired" are different failures and
used to look identical.

**Two run-side notes.** The map is reached with a borrowed map-id slot
(`content/maps.toml [map.27]`, file id `0xB5FF`), and the client draws the
SLOT's name and world map over our terrain — the owner reported the minimap
"didn't really fit the map", which is that split showing, not a fault. Opening
the world map (M) crashed the client on the first run; `Gw.log` stops mid-auth
chatter with no error line, the same signature as §7.6's first crash. Not
diagnosed, plausibly the same label/content mismatch, and avoidable: the
capture needs no input at all.

## 9. The prop fall-through: overstated, not stale, and the fix is in (2026-08-18)

`PLAN.md` §4 and the importer's own docstring recorded this defect as **31.6%
of Kamadan's prop area**, 13 of 207 sub-models, "and for the five rock models
slot 0 is a near-black texture -- which is why they render dark rather than
untextured."

> **THIS SECTION'S FIRST VERSION SAID "31.6% -> 0.11%, stale by 287x", AND
> THAT WAS WRONG** -- caught the same day by dating the code rather than
> trusting the improvement. Both the layered chain and the `none` fallback
> landed in `da35145` at **10:51 on 2026-08-14**, and the 31.6% claim landed in
> `39db117` at **13:01 the same day**. The binding code has not changed since.
> Nothing collapsed, and comparing the two numbers compares two different
> metrics. The corrected account is below. It is a smaller claim and it is the
> true one.

**THE POPULATION NEVER MOVED: 13 sub-models then, 13 now.** Measured on today's
Kamadan export, sub-models with no layered material number **exactly 13** --
the 08-14 count, unchanged. What differs is which of them a reader calls
"falling through":

| metric, same data | sub-models | prop AREA |
|---|---|---|
| A: no layered material (**the 08-14 population**) | **13** | 55.61% |
| B: left at Blender's DEFAULT, no explicit choice | **1** | **0.11%** |

The gap between A and B is the **12 `none`-kind sub-models**, and the reason
they are not a rendering defect is exact rather than approximate: the importer
binds them to `slots[material_index]`, `material_index` is **0 on all 12**, and
`by_image` is built in slot order -- so they land on material slot 0, **the
same slot Blender's default would have given.** Explicit or defaulted, the
pixels are identical. The 31.6% was therefore never 31.6% of *wrongly drawn*
surface; it was the area of sub-models reached by a path nobody trusted.

**Only ONE sub-model is genuinely unbound** -- model `0x3C5AC`, the AMAT
`binary` path, 7 instances, 0.11% of prop area (2,665,424 of 2,342,145,300
area-units) -- and Lornar's Pass has **none at all**, 0 of 391. Measured twice
independently, by me and by an agent that wrote its own scripts and never saw
mine, landing on the same sub-model and the same figures. **The fix below
changes what is drawn on that one sub-model and nowhere else.**

**AND THE ROCKS ARE NOT THIS DEFECT** -- this is the part of the original claim
that is genuinely refuted rather than re-framed, and it is why the 12 above are
not a defect at all. The correction has a measurement behind it:
`tex_3C172.png` really is that texture and really is dark (mean rgba
**[42, 40, 32]**, fully opaque, max channel 107) -- but the 10 models that draw
it (not five; **156 instances**, not 123) are **single-sub-model models whose
material kind is `none`, and it is the ONLY colour map any of them owns.**
Classifying all four slots of the worst offender by pixel statistics:

    slot 0  tex_3C172.png  512x256  mean [42,39,31]   <- the only COLOUR map
    slot 1  tex_3C174.png  512x256  mean [127,127,253]   flat blue: a NORMAL map
    slot 2  tex_32F2E.png  128x128  mean [128,127,127]   grayscale, r constant
    slot 3  tex_2D885.png    64x64  mean [255,255,255]   flat white

**12 of 12** fall-back sub-models draw the only colour map their model owns.
So the binding is right, and the darkness is **the art**, not our bug. That
matters because it was the stated motivation for decoding AMAT.

**THE FIX, and it is the cheap half deliberately.** A sub-model whose material
cannot be resolved now gets its own `gw_unbound_material` -- magenta, no image
-- instead of keeping Blender's default index 0 and drawing whichever image
landed first. This is the prop half of a convention the terrain path already
had (`gw_untextured_<fid>`), whose docstring names this very defect as what it
refuses to repeat. The render gets worse on 0.11% of one map and stops lying.

**AND A CHECK THAT CAN ACTUALLY FAIL**, because the first version could not.
`props_summary` now reports `unbound_faces` and `unbound_meshes` off the BUILT
polygons -- without that the dump cannot express the defect at all, so nothing
outside Blender could see it return. `test_blenderimport` §5b recomputes the
expectation from the **model manifests** rather than the importer's own
bookkeeping, so an importer that went back to defaulting fails even though its
dump stays self-consistent (§7.15's lesson). On Pre-Searing that comparison is
0 against 0 and would pass over the defect, so **§5c BREAKS one on purpose**:
it copies a placed model's family to a scratch dir, points its first sub-model
at an unresolvable material, and requires the marker on exactly those 578
faces. The suite is 122 green, floor 122.

**WHAT IS NOT DONE, and why the plan for it has changed.** `PLAN.md` §4 called
decoding AMAT (`0xFAD`) "the real fix". **It is not the fix for this**, and the
recorded chain is wrong in kind. Read out of the pinned client (build 38797,
`asserts.py` + `codescan.py`, capstone under carve-out 1):

- The layered branch **never touches AMAT at all**. `mtlIndex` selects a
  material with `pixelShaderId != 8`, whose layers carry `texPathIndex`
  resolved through `baseTexs[texPathIndex]` -- bounds- and null-checked exactly
  where `modelfile.py`'s format-derived chain says (`MdlCombine.cpp:568`,
  `MdlTex.cpp:673`). That is independent corroboration of the structural
  reading, from different evidence.
- The `binary` branch is the minority, taken when `pixelShaderId == 8`
  (`MdlLoad.cpp:1150`), and its `amatIndex` is bounds-checked against a
  **separate** `amatPathCount` (`MdlCombine.cpp:632`) that loads an
  out-of-model resource.
- **AMAT is a compiled SHADER binary, not a texture-index table.** Its parser
  keys on 4-byte ASCII chunk tags `TECH` and `PASS`
  (`Dx9ShaderBinary.cpp:482` and `:489`, the literals `0x48434554` and
  `0x53534150` compared in code). So "-> the FA5 slot" is the wrong
  destination: an AMAT file declares its own texture roles internally.

So decoding AMAT is a **shader-decoding arc**, it would buy 0.11% of one map,
and `modelexport.py`'s hypothesis should be corrected rather than pursued.
**LABEL: this last block is DISASSEMBLY, not tested against a running client** —
the exact failure mode that cost this arc four retracted claims (§7.18). The
`TECH`/`PASS` tags and the bounds checks are solid because they are literal
byte comparisons beside their own asserts; **which slot the client calls
"diffuse" is NOT established** and the agent that found this flagged it.

**One non-defect, recorded so it is not chased.** 59 of Kamadan's 145
referenced models have no `.gwmodel.json` at all (40.7%), which looks alarming
and is not: **all 59 have ZERO placements.** The list is the map's model
dependency list, not its placement list. Lornar's is 135 of 135.

## 10. The field of view is 75.000 degrees, and the axis is not (2026-08-18)

`gwcam.py` has carried `--lens 28` marked NOT MEASURED since it was written.
It is measured now, off a running client, and the number is exact.

    fov = 1.3089969158172607 rad = 75.000 degrees, to the last bit
    far plane = 48000.0 units

**HOW, and why it is a read rather than a disassembly claim.** Chasing it
statically ends at a VARIABLE, not a literal, so a static answer would have
been a guess about which constant the camera lands on -- the shape of claim
this arc has retracted four times (§7.18). The trace (build 38797):

- `GmView.cpp`'s frustum builder at **`0x004ED3C0`** takes `fov` as its fourth
  argument and asserts `fov != 0.0f` (**GmView.cpp:3737**). Its failure path
  prints `Invalid frustum:` / `Fov = %f` / `Position = %f, %f, %f`.
- Both callers (`0x004E2866`, `0x004E29F8`) push the float at
  **`0x00C078C4`**, alongside `0x00C07860` and `0x00C0786C` -- the position
  and target that same dump prints.
- That global is FILLED by the camera update `0x004F6360` -> `0x004F3420`
  (`this` = `0x00C079A8`), which asserts it again at **GmCam.cpp:1728**.
- The far plane is the literal at `0x00946EBC` = **48000.0**.

So `toolkit/clientscan/fovread.py` reads the global out of a live client with
`ReadProcessMemory` -- no injection, no breakpoint, nothing written, and no
6-second window to miss.

**THE READ SELF-VALIDATES, which is what makes it a measurement and not a
plausible number.** Beside the fov the same globals gave

    position = (9435.99, 8077.0, -805.42)
    target   = (9826.0,  8077.0, -716.57)

and `content/maps.toml [map.148]` records Pre-Searing's spawn as
**(9826.0, 8077.0)** -- the target equals the map's known spawn point, a
number `fovread.py` was never given. The camera-to-target distance is
**400.0 units**, inside the 25..750 zoom range the wiki documents. An address
read from the wrong place does not land on a coordinate we already knew.

**Conditions**: default settings. `HKCU\\Software\\ArenaNet` does not exist on
this machine, so the client had no saved preferences and started on its own
defaults -- which matters, because the 2018-06-06 patch added an in-game
**Field of View slider**, so this is *a* default and not a universal constant.

**WHAT IS NOT ESTABLISHED, and it is the half that decides framing: WHICH AXIS
the 75 degrees spans.** The three readings are far apart -- at the 1.918
aspect measured on the render area (1920x1001):

| if 75 deg is | vertical | horizontal | diagonal |
|---|---|---|---|
| VERTICAL | 75.000 | 111.612 | 117.864 |
| HORIZONTAL | 43.608 | 75.000 | 81.743 |
| DIAGONAL | 39.063 | 68.463 | 75.000 |

`gwcam.py` takes the **vertical** reading, because ArenaNet's own patch notes
(2018-06-06, GWW) say the client moved to a vertical calculation and
`-oldfov` restores the older **diagonal** one. That is documentation from the
publisher about this exact mechanism, and it is still an assumption.
**One upstream contradicts it**: GuildWarsMapBrowser states 50 degrees
vertical (single witness, UPSTREAM, unverified). Nothing here reproduces 50 on
any reading, so one of the two is wrong and it is not settled by argument.

**Two routes tried that did NOT settle it**, recorded so they are not retried
blind: a memory scan for the projection matrix over **399 MB** of the live
client's committed pages found **zero** true perspective matrices (filtering on
`m23 == 1`, `m33 == 0`, `1 < m22 < 1.5`, `m32 < 0`) -- it is not lying around
in that form. And the `oldfov` flag itself does not carry a second FOV: the
wide string sits at `0x00943254` in a 41-entry `{name, id, flags}` switch
table as **id 25**, whose only reader is the bounds-checked getter
`0x004997A0`, and of its 50 callers exactly **4** push id 25 -- all four
converting the boolean to a MODE (0 or 2) fed to a shared text helper, none
loading a second FOV-shaped constant. So on this build the flag does not
select between two values the way its name suggests. *(Static, untested
against a running client -- and what MODE 0 vs 2 does was not decoded.)*

**THE TEST THAT WOULD CLOSE IT** is geometric and needs one client run: stand
at a known point, screenshot, and locate a world feature whose position we
already know exactly (we ship the terrain heights, so any ridge line will do).
The pixel position of a known world point against a known camera pose gives
the horizontal and vertical fields directly, with no free parameter.

**One correction to a tool while here.** `toolkit/clientscan/asserts.py`'s
census does not contain **GmCam.cpp:1728**, and an agent reasonably challenged
that citation on those grounds. Re-read from the raw bytes at `0x004F38D9`:
`push 0x6C0` (1728), `mov edx, 0x0094E064` -> `P:\\Code\\Gw\\Ui\\Game\\GmCam.cpp`,
`mov ecx, 0x0094D2A4` -> `fov != 0.0f`. The citation stands and the census is
incomplete -- worth knowing before trusting it as exhaustive.

## 11. CLOSED: the 75 degrees is the HORIZONTAL field of view (2026-08-18)

§10 measured the angle and could not name its axis. Two independent tests
settle it, and they agree.

**TEST 1 — the client's own projection scales, from memory.** A perspective
projection holds `m00 = cot(h/2)` and `m11 = cot(v/2)`, and `m11/m00` is the
render aspect. So each reading of "75 degrees" predicts a DIFFERENT pair, and
the pairs are computable exactly. Requiring the two to be **adjacent floats**
(gap ≤ 3 slots, so a coincidence has to be a coincidence of ORDER as well as
of value) over 505 MB of the live client:

| the pair a reading demands | sites found |
|---|---|
| **HORIZONTAL** — `cot(75/2)=1.303225` then `1.303225 × aspect = 2.499693` | **2** |
| VERTICAL — `1.303225 / aspect = 0.679442` then `1.303225` | **0** |
| DIAGONAL — `1.469707` then `2.819018` | **0** |

`0x25D3A6E8` and `0x25DEA770`, gap 1 in both. Standard D3D builds
`xScale = yScale / aspect`, so the SMALLER of the pair is the x scale — and
`cot(75/2)` is the smaller. **The 75 degrees is the horizontal field.** The
looser test in §10's first pass "confirmed" both readings because the two
predicted pairs SHARE the value 1.303225 and differ only by a factor of the
aspect; requiring adjacency is what separates them, and a bare-value search
never could.

**TEST 2 — geometry against a screenshot, which refutes the vertical reading
outright.** Camera pose read live, terrain height read from our own export,
one screenshot (`vault/research/terrain/fov_client.png`, 1920×1001, Ascalon
City):

    camera  (9435.993, 8077.0, -805.418)      target (9826.0, 8077.0, -716.565)
    camera -> target = 400.000 units exactly

All three points share y = 8077, so the whole problem lies in the vertical
plane and the target projects to the exact centre row. The character stands at
the spawn — **(9826, 8077), which is `content/maps.toml [map.148]`'s own
spawn** — and its feet are at row **693** in the image. Inverting each reading
to the ground height it would require:

| reading | vertical fov | required feet Z | vs the terrain (642.02) |
|---|---|---|---|
| 75 is VERTICAL | 75.000 | 586.40 | **−55.62 — BELOW the ground** |
| 75 is HORIZONTAL | 43.608 | 650.97 | +8.95 |
| 75 is DIAGONAL | 39.063 | 658.64 | +16.62 |

**A character cannot stand 55 units under the terrain**, so the vertical
reading is refuted by the picture itself. The horizontal reading needs the
smallest correction — 9 units, which a paved plaza sitting just above the
height lattice supplies — and it is the one test 1 names independently.

**So: horizontal 75.000 degrees, vertical 43.608 degrees at 1920×1001**, and
the vertical moves with the render aspect while the horizontal does not.
`gwcam.py` sets `sensor_fit = HORIZONTAL` and `angle_x = 75 deg` (lens 23.46 mm
on a 36 mm sensor).

**A CONFLICT WITH ARENANET'S OWN PATCH NOTE — now tested, §12.** The
2018-06-06 note says the client moved to a *vertical* calculation with
`-oldfov` restoring a diagonal one, and a horizontal-fixed projection is
neither. §11's first version left that standing; §12 ran the aspect test and
the client held HORIZONTAL fixed.

**Instruments:** `toolkit/clientscan/fovaxis.py` (the adjacency test, read-only)
and `fovread.py`. Both rerun in a minute against any running client.

## 12. THE ASPECT TEST: the client holds HORIZONTAL fixed (2026-08-18)

§11 named the test that would settle §11's own conflict with ArenaNet's patch
note: **run it again at a different window aspect.** A horizontal-fixed
projection keeps `m00` and moves `m11`; a vertical-fixed one does the reverse.
It ran, on one client, resized mid-session from wide to portrait.

| render area | aspect | m00 | m11 | horizontal | vertical |
|---|---|---|---|---|---|
| 1920 x 1001 | 1.918 | **1.303225** | 2.499693 | 75.000 | 43.608 |
| 700 x 1001 | 0.699 | **1.303225** | 0.911346 | **75.000** | 95.311 |

**`m00` does not move. `m11` tracks the aspect exactly.** At the portrait
aspect the vertical reading requires the pair `(1.863612, 1.303225)` and it
appears at **ZERO** sites, against 10 confirmed sites for the horizontal pair;
the diagonal is zero as well. So the field of view the client holds constant is
the HORIZONTAL one, and the vertical is whatever the window makes it — 43.6
degrees on a wide window, 95.3 on a tall one.

**Choosing the aspect was the part that needed care.** At aspect **1.0 the two
hypotheses predict the SAME pair** — `cot(75/2)` twice — so a square window is
the one shape that could not have settled anything. Portrait was chosen for the
opposite reason: below 1.0 the two readings do not merely differ, they **swap
which cotangent is larger**, so the answer is a qualitative flip rather than a
fitted number.

**THREE INDEPENDENT CHECKS THAT THE RESIZE WAS REAL**, because an OS window
resize is not the same thing as a D3D9 swap-chain rebuild and a skeptic rated
that LOW confidence before the run:

1. The client's own record of its render size moved to `(700.0, 1001.0)` at
   **175 sites**; the stale `(1920.0, 1001.0)` survives at 27.
2. **`m11` moved at all.** Had the client ignored the resize, the projection
   would still read 2.499693 — the measurement itself refutes the confound.
3. The portrait screenshot (`fov_client_portrait.png`) shows **no letterbox**:
   the world fills the window, the HUD re-laid itself out, the horizontal
   extent is preserved and the vertical extent grows hugely. That is the same
   verdict from pixels, with no arithmetic at all.

**THE DESIGN WAS REVIEWED ADVERSARIALLY BEFORE IT RAN, and the reviewer
returned FLAWED.** Its primary attack was exactly the aspect-1.0 collision —
and worse than uninformative there, because `fovaxis.py`'s partner check
searches a window that always contains the found float itself, so at aspect 1.0
each hypothesis would *self*-confirm off one stored value. That is a real
defect in the tool at that one aspect. It did not bite because the aspect was
pinned to 0.699 first, where the predictions sit 0.39 apart — roughly 2,000×
the tolerance. **A near-square window is worse than an exact one**: at 0.9999
the two predictions are ~2.6e-4 apart, at the tool's own noise floor, where
exact 1.0 at least fails loudly as UNSETTLED.

**The reviewer's other live confound — a second in-engine camera (minimap,
shadow, cutscene) contributing a matching pair by coincidence — is answered by
the two runs together.** `fovaxis.py` confirms on numeric adjacency alone and
does not tie a hit back to the camera chain, so a decoy is possible in
principle. But a decoy would have to produce the horizontal pair at BOTH
aspects, never produce the vertical pair at either, and have its second value
land on `cot(75/2) × aspect` for two different windows — 2.499693 and then
0.911346. A camera with its own field of view does not track OUR window twice.

**SO THE PATCH NOTE AND THIS CLIENT DISAGREE, and the disagreement is now a
measurement rather than a loose end.** On build 38797, launched without
`-oldfov`, the projection is horizontal-fixed. What that means for ArenaNet's
"vertical calculation" wording is still NOT established — the honest options
are that the slider is expressed horizontally while something else is derived
vertically, that the behaviour changed again after 2018, or that the note
describes the *option's* framing rather than the matrix. **Naming one would be
a guess**, and this arc has retracted four of those. What is measured is the
table above.

**Cost: one client run, two scans, one screenshot.** `fovaxis.py` needs no
argument — it reads the fov and the window itself and recomputes the
predictions, so re-running it after any resize is the whole procedure.

## 13. The lightmap transfer curve: a QUARTIC ease-out, byte-exact (2026-08-19)

Opened to settle §8's last render-affecting item. §6.5 identified tag 9 as a
baked directional lightmap and applied it as `shade / 255` — "the simplest
mapping the measurement allows" — while recording that 348/349 maps saturate
at 255, so a gamma or a scale-and-bias would fit the corpus equally well. That
was a statement about the corpus fit. This closes the curve itself, and it is
neither linear nor a gamma. **Two halves that are not the same question: the
BAKE (what the map compiler writes into the byte) and the APPLY (what the
renderer does with the byte). Settled separately below, and the split matters —
§6.5's "shade/255" is an APPLY claim, "a gamma would fit" is a BAKE claim.**

### 13.1 The bake: `255·(1 − (1 − N·L)⁴)`, reproduced byte-for-byte (OBSERVED)

The generator is `0x0075CC30` — the function customarea/FINDINGS §"Tag 9 is
BAKED" *identified but did not read* ("0x0075CC30 was identified, not read").
Read whole in build 38797. The transfer is a **quartic ease-out**:

```
byte = RoundHalfAwayFromZero( 255 · (1 − (1 − clamp(N·L, 0, 1))⁴) )
```

- **N** = `normalize( Σ_{i=1..4} normalize(tri_i) )`, the four quadrant-triangle
  normals of the 5-point stencil `{C, N, S, W, E}` at ±96 world units, each
  normalized before the sum; every missing edge neighbour is replaced by C
  (verified in all eight border paths).
- **L** = `(cos θ, 0, sin θ)`, θ = tag 0's sun elevation; the `y` term of N·L
  is dropped outright — legal because the client asserts `lightDir.y == 0`
  (`TrnTexIntensity.cpp:342`), which §6.5 already cited from the other side.
- Every step is float32-spilled. Normalization is the client's own **8-bit
  table inverse-sqrt** (`0x0046E530` over a 256-entry table at `0x0093C6C8`),
  whose ~0.4% error is load-bearing. Rounding is **round-half-away-from-zero**
  with no `+0.5` (`0x0046E000`, `Math.cpp:240`).

**VERIFICATION — a replica with no free parameter, `studies/terrain/trnbake.py`.**
It reproduces the stored Bloated tag-9 bytes:

| set | result |
|---|---|
| five corpus maps (Kamadan `0x345CC`, Pre-Searing row 7982, rows 22E2C/46196/32347) | **667,647 / 667,648 cells exact** |
| the e10* CLIENT COMPILES, geometry the replica was never tuned on (LIGHT 36.5°, GRASS 68.7°, e10d A, rungG) | **1024/1024 each** |

The single corpus miss (row 32347, one cell) computes to **exactly 210.5**
under every precision model; build 38797 rounds it to 211, the archive stores
210 — that one map's lightmap was baked by an older binary whose tie broke the
other way. A 1-in-667,648 boundary case; the formula is settled. `trnbake.py`
reads the invsqrt table out of the pinned pristine client at run time and
commits none of it (the measurement pattern `mapbuild` uses for FINDINGS 14's
chunks); a double-precision `1/sqrt` misses a handful of ties per map, so the
table is required for byte-exactness.

**What the curve explains, and what it rules out:**
- The quartic saturates fast, which is **why 348/349 maps peg at 255** and why
  §6.5's linear fit plateaued at r 0.887 — the linear model was this curve seen
  through a correlation coefficient. A gamma is refuted directly: on the clean
  compiled data the best pure power fit is far worse at a nonsense exponent.
- **No cast-shadow term.** The byte depends on five heights and the angle,
  nothing else — proven three ways: no ray-march in the disassembly, byte-exact
  reproduction from heights+angle alone, and e10d's A/B compiles (props differ)
  baking **byte-identically** (1024/1024). Tag 7's shadow record correlates with
  darker tag-9 via slope, not via a term in this bake.
- **The environment chunk's lights do not feed the bake.** e10h LIGHT ≡ e10i
  ENV ≡ e10j SOUND ≡ e10l AUTHORED, shade byte-identical 1024/1024 across all
  three additions; corpus-side, fitted curve parameters vs env tag-3 light
  pairs over 96 maps show |r| < 0.19. **The bake is a pure function of (tag-1
  heights, tag-0 angle).**

*(Two intermediate readings of mine are retracted here for the record: an
"overdriven affine s≈clip(96·N·L+189)" and a "signed N·L without max(0,·)"
were the quartic seen through central-difference normals over one compile. The
affine's a+b>255 was the quartic's fast saturation; the "zero regime" of 30
cells was the clamp d≤0→0, not a shadow term. A curve read through the wrong
normal stencil fits a wrong family convincingly — the byte-exact replica is
what separated them.)*

### 13.2 The apply: the pipeline is COLOUR-NAIVE (OBSERVED, adversarially held)

Does the client apply a colour curve between the shader result and the screen?
**No.** Confirmed against the bytes and survived an independent skeptic that
re-derived the whole census and decoded every embedded ps_2_0/ps_3_0 to rule
out a gamma post-pass:

- **No sRGB anywhere.** `D3DRS_SRGBWRITEENABLE = 194` is structurally
  inexpressible — the shader render-state machine is a 64-entry table
  (`0x00A652D0`) indexed by the D3DRS number and asserted `< 0x40`. Sampler
  bit 11 `D3DSAMP_SRGBTEXTURE` is `NODEF (-1)` in the 32-entry default table
  (`0x00A653D0`) and would trip `result != NODEF` on restore. The terrain path
  reaches the device only through this Gr/Dx9 layer, so sRGB read/write is
  unreachable in the whole image.
- **The gamma slider is scanout-only.** The one `SetGammaRamp` site
  (`0x006D1614`) builds a power-curve LUT `ramp[i] = 65535·(i/255)^(1/g)`, g a
  16.16 pref (default 1.0), and applies it to R/G/B equally post-framebuffer —
  it cannot change the lightmap-vs-texture relationship. No
  `Set/GetDeviceGammaRamp` GDI import exists.
- **Backbuffer is 8-bit integer** (`X8R8G8B8`/`R5G6B5`), no 10-bit or float
  path reachable.

So the client multiplies texture × lighting in **raw stored-byte space** and
displays it naively. For our own Blender reproduction this is the load-bearing
fact: `import_gwmap` multiplies the lightmap in Blender's *scene-linear* space,
which is a different space from the client's byte-space multiply — a real
fidelity gap, but one whose fix is a **visual** question (the two render
differently and only a side-by-side against retail says which is right), so it
is recorded, not guessed. Docstrings in `import_gwmap.py` now carry it.

### 13.3 CONTESTED: whether the baked lightmap reaches `v0` at all

§6.4/§6.5 stated `mul r0, v0, r1` multiplies the blended ground by v0 = the
baked tag-9 lightmap "applied per vertex". The `mul` is real and carries no
modifier (re-confirmed). **The "v0 = tag 9" half is now CONTESTED**, and by the
client's own bytes:

- Both terrain vertex shaders (`0x00A73B00`, `0x00A73910`) write the pixel
  shader's diffuse input as `mul oD0, r2, c10` where **r2 is a view-space
  DEPTH-FADE scalar** (`dp4 v0,c6` through c7/c8/c9), not a lighting term;
  vertex input v3 feeds the tangent basis (oT1..oT3) *after* the oD0 write and
  never reaches v0.
- Neither terrain vertex builder (`0x0075DD50` HI, `0x0075E650` LO) reads the
  shade array; a complete write census of both and every record-touching callee
  (including `0x00757A80`, which the first pass missed) finds only float
  position/UV stores. No terrain code packs a colour byte into the vertex
  stream (0 D3DCOLOR-replicate idioms over the whole terrain code range).
- The baked lightmap is consumed by `TrnTexIntensity` (LUT `0x00BF7678`) into a
  separate **intensity buffer** — whose display consumer was **NOT FOUND
  statically**. A ps-only fixed-function-vertex path (`0x0074BAA2`) exists where
  v0 would be the FF diffuse from a vertex colour element, but the write census
  shows no colour is ever written to the stream, and the vertex declaration is
  synthesized inside `0x006646B0` where static analysis could not read it.

This is a live question and is left as one — the arc's signature failure is
resolving exactly this kind of thing by disassembly (four retractions, §7.2
among them). **The live check** (one client run): capture the vertex
declaration and stream bound for a terrain `DrawIndexedPrimitive`, confirm there
is no COLOR element sourced from tag 9, and read c10 for the draw. Until then,
`import_gwmap` multiplying the ground by the baked lightmap stays the right
call regardless of the outcome: tag 9 IS the map's baked directional lighting,
and if the client instead computes it live, live N·L and baked N·L are the same
quantity — which is also why §6.5's r 0.887 could never have distinguished the
two.

### 13.4 The corpus fit is the WRONG instrument (a method note)

`studies/terrain/shadecurve.py` (new) tried to reproduce §6.5's per-vertex fit
(median r 0.887 / 345 maps) and reached only ~0.50 on the same recipe; the
original method is not preserved in the tree. Its **gate correctly refused** to
print a curve verdict on geometry that failed reproduction — a run that
measured the wrong thing prints no verdict, per the repo's test discipline. The
lesson, recorded so it is not repeated: the retail corpus cannot see this curve
— retail bakes carry cast/AO shadows (e10h's own note: a Lambertian best-fits
5° against a true 36.5°), and the fit is affine-invariant and gamma-blind. **The
right instrument was the vault's client-compiled artifacts of known geometry**,
where the bake is clean — which is what §13.1 used. `shadecurve.py` is kept as
that recorded negative and as a reusable light-direction fitter, gated and
labelled.

## 8. What is still open

- ~~Does the ground still repeat at distance?~~ **ANSWERED 2026-08-18, §7.20:
  NO beyond the art's own floor.** The export sits on the ideal-random floor
  on every window of both maps (pinned control separates 3–9×), and the
  arrangement is the client's own (2048/2048, 511/511, 212/212). If a live
  side-by-side against retail still shows a difference, look at RENDERING —
  fog, mips, the lo path, t3's lerp, the lightmap curve — not at layout.
  Instrument: `studies/terrain/repeatprobe.py`, artifact-gated, reruns offline.
- ~~The `arg4 = 0` scope caveat (§7.13/§7.14).~~ **DISCHARGED 2026-08-18,
  §7.21.** Row 34429 tile (4,3) captured whole: 1024/1024, 590 cells with
  authored tag 3. `trnvariation` claim 1 confirmed against the client for the
  first time (1024/1024 consume vs 693/1024 skip, the 331 differing cells
  exactly as predicted); an authored cell's base quadrant is its authored
  value 590/590; §7.14's cover-word rule holds 735/735 on the authored block.
  The target-selection record below is kept because the reasoning is the
  reusable part.
- **How that target was chosen, and the error worth not repeating.** Corpus
  scanned 2026-08-18: 181 of 349 maps
  author tag 3 somewhere. Ranked by authored count alone the winner is row
  46101 tile (1,1), 767/1024 — **and it is unreachable: 0 of 64 walkable
  probes.** So are the next three (132053 t(2,7), 132040 t(2,4), 59717
  t(7,2)): all 0/64. **Dense authored tag 3 sits mostly on decorative terrain
  the player cannot stand on**, which a density ranking cannot see, and this
  is the same shape of error as §7.5's probe — a number that is correct about
  the wrong thing.
  **The target is `row 34429, file id 0xB5FF, tile block (4,3)`** — 590
  authored of 1024, **50 of 64 probes walkable**, 757 of its 1024 cells
  landing in exactly one trapezoid. Spawn **(1584.0, 1488.0)**, cell
  (144,112), the block's centre: 1 trapezoid in its own mesh, 0 in Kamadan
  and 0 in Pre-Searing, against a base rate of 14.5% walkable over the map's
  rect. Same map's fallbacks, all walkable: t(3,2) 519, t(4,4) 458, t(2,2)
  550. The map is 256×256 and the client's own table cannot name it (35 rival
  rows); it loads by file id through a test slot, the pattern `[map.143]` and
  `[map.144]` already establish.
- **THE PREDICTION, stated before the run and CONFIRMED EXACTLY by §7.21**
  (house rule: a probe with no stated expectation can be rationalised into
  agreeing with anything — this one could not have been, and was not). Block
  (4,3) holds 590 authored cells AND 434 deferred ones, which makes it the
  first block in the arc that can test **`trnvariation` claim 1 — "the draw
  happens either way"** at all. Every prior capture had `arg4 = 0` on every
  cell, where the two readings are identical by construction.
  - **H1-true** (claim 1 stands): an authored cell consumes its place in the
    stream and ignores what it drew.
  - **H1-false**: an authored cell skips the draw, shifting every later cell
    in its tile.
  These predict **different base quadrants on 331 of 1024 cells (32.3%)** —
  the capture discriminates them outright. Under H1-true our model predicts
  for that block: layer counts `{1: 289, 2: 326, 3: 409}`, overlay cover
  words `{0x0:153, 0x1:210, 0x2:133, 0x3:166, 0x8000:105, 0x8001:127,
  0x8002:76, 0x8003:174}`, base quadrants `{0:110, 1:302, 2:311, 3:301}`.
  That quadrant-0 deficit is itself a signature: authored values can only pin
  1–3, so quadrant 0 is reachable only through a draw (§3.2).
  §7.14's cover-word rule should hold unchanged regardless of tag 3; if it
  does not, the 212/212 was one block's accident.
- ~~The lightmap's TRANSFER CURVE.~~ **SETTLED 2026-08-19, §13.1: the BAKE
  is a quartic ease-out `255·(1 − (1 − N·L)⁴)`**, read from the generator
  `0x0075CC30` and reproduced byte-for-byte (667,647/667,648 corpus cells,
  1024/1024 on four client compiles) by `studies/terrain/trnbake.py`. Not
  linear, not gamma; the quartic's fast saturation is why 348/349 maps peg at
  255. No cast-shadow term; the bake is a pure function of (heights, sun
  angle). The APPLY pipeline is colour-NAIVE (§13.2: no sRGB, scanout-only
  gamma slider).
- **NEW, §13.3 — does the baked lightmap reach the screen, and how?**
  CONTESTED. Both terrain vertex shaders write a DEPTH-FADE to the pixel
  shader's `v0`, not the lightmap; the baked lightmap goes to a separate
  intensity buffer whose display consumer was NOT FOUND statically. The live
  check: capture the vertex declaration/stream for a terrain
  `DrawIndexedPrimitive` and read c10. This does not change `import_gwmap`'s
  choice to multiply by tag 9 (a faithful proxy either way), but it is the
  honest state of "how tag 9 is displayed."
- **NEW, §13.2 — Blender multiplies the lightmap in the WRONG SPACE.** The
  client blends in raw byte-space (naive, no sRGB); `import_gwmap` multiplies
  in Blender's scene-linear space. A real fidelity gap, but its fix is visual
  (render headless, compare to retail) rather than a blind colourspace flip.
  `--no-lightmap` remains the control.
- ~~The SOURCE of the per-cell corner selector.~~ ~~What GENERATES it.~~
  **BOTH CLOSED 2026-08-15, §7.6 and §7.9.** `chunk+0x2B4` is a per-cell corner
  PERMUTATION, and it is a **selection-sort comparator network** over the four
  corner types — `[01][02][03][12][13][23]`, swap on strict `>` — reproduced
  **2048 of 2048 cells** over two captures. Landed as
  `trnblend.corner_selector`; `SELECTION` is no longer `"identity"`.
- ~~What picks the coverage quadrant.~~ **CLOSED 2026-08-17, §7.13**: it is a
  function of (corner types, SELECTOR byte) — 212/212 mixed cells, 0 ambiguous
  groups. The PRNG is exonerated (§7.12, 24.8% vs a 25% baseline) and is spent
  entirely on the base variation (512/512).
- ~~Emit the cover word for the permuted mask.~~ **DONE and CORRECTED
  2026-08-17, §7.14**: the mask is PHYSICAL, not permuted — 212/212 against the
  client, where the permuted reading scored 31.1%. Landed in `cell_layers`;
  format and importer unchanged. `test_trnblend` §5 locks it to the capture.
- ~~The permutation is lost at the format boundary (§7.10).~~ **Subsumed by
  §7.13** — same defect, now with the mechanism and a test set.
- ~~The base layer's own UV rectangle.~~ **REFUTED 2026-08-17, §7.18**: there
  is no second rectangle. The base never takes the unmasked path (0 of 512
  cells); `0xFFFF` marks an UNUSED slot, and its span of 1/2048 is sub-texel —
  a placeholder that samples nothing. The last item that could have explained
  large-scale repetition is gone, and no replacement suspect is named.
- The 4-dword table at `0x00A73DF8` = `{3, 3, 3, 0x30}`, the terrain
  factory's argument that lands at stage record +0x10. Named, not
  understood, and asserted nowhere.

- ~~GW's FOV is unmeasured.~~ **MEASURED 2026-08-18, §10: exactly 75.000
  degrees** at default settings, with a far plane of 48000, read live from
  `0x00C078C4` by `toolkit/clientscan/fovread.py` and self-validated against a
  known spawn point. ~~Still open: which axis.~~ **ALSO CLOSED, §11: it is
  the HORIZONTAL field** — the projection's adjacent scale pair puts
  cot(75/2) as the x scale (2 sites; the vertical and diagonal pairs appear
  nowhere), and the vertical reading is refuted geometrically because it would
  put the character 55 units under the terrain. Vertical is 43.608 deg at
  1920x1001 and moves with the aspect. ~~Left open: the conflict with
  ArenaNet's 2018 patch note.~~ **TESTED 2026-08-18, §12**: resized to a
  portrait window mid-session, `m00` stayed pinned at cot(75/2) while `m11`
  tracked the aspect, and the vertical pair scored ZERO sites. The client
  holds HORIZONTAL fixed. Why the patch note says *vertical* remains
  unexplained, and is left that way rather than guessed.
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
