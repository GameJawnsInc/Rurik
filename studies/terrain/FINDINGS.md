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

## 3. What is still open

- **T3**: how a cell samples its 128×128 quadrant, and the UV scale. §2.1 gives
  the mechanism; the arithmetic is unmeasured.
- **T4**: the two 512×512 V8U8 bump maps nothing decodes.
- `table_b` — Kamadan's values are `{5, 7, 13, 15, 17, 19, 21, 23, 81, 85}`,
  all odd. UNVERIFIED, and not on the critical path.
- Terrain tag 0's `tex_word`, `tex_f12`, `tex_f16`. Named, not understood.
