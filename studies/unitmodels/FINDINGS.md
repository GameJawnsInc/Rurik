# Unit model files — the skeleton chunk, the composites, and the wire

Build 38797, read from the vaulted stock `Gw.exe`
(`vault/client/2026-07-29_221c13772c7a/Gw.exe`, verified pristine on every run)
and from `vault/dat_study/Gw.dat` — no client was launched for any of this.
Wire evidence is from the three live captures with decrypted channels
(`vault/captures/live/20260807T133758`, `20260807T143055`, `20260810T235916`,
origin=live via `toolkit/origin.py`; never `selftest/`, never mixed with ours).

Labels are the project vocabulary
([../character/FINDINGS.md](../character/FINDINGS.md)). The proposed ladder for
this arc is in [PLAN.md](PLAN.md).

**How this document was produced, and what checked what.** Six recon agents
(corpus census, assert sweep, FA1 loader disassembly, trailing blocks,
composite chunks, wire) and two verification agents (a full-population FA1
closure run; an adversarial re-derivation of the trailing-block and composite
claims) all returned — no section below stands on an agent that failed. The
FA1, trailing-block and composite sections are **doubly witnessed** and every
disagreement is recorded below with the verification winning. The census is
cross-corroborated at several points (its flags histogram reproduces
`mapchunks.py`'s exactly; its FA1 size histogram and its row-8316 anomaly
reproduce under the full-population walk). The **assert sweep and the wire
census are single-witness** — the wire agent cross-checked itself against
`studies/smsg/FINDINGS.md`'s independently derived counts (exact match, so
that document's corpus is the same capture), and every assert-absence claim is
a floor over 19,758 of ≥20,131 sites, per `asserts.py`'s own banner.

---

## 1. The answer in one page

**`0x00000FA1` is the skeleton/animation chunk, and it is structurally
decoded.** ArenaNet's loader parses it at `0x00796310` into the object
`MdlSeq.cpp` itself calls `m_skel`; the derived walk closes on the exact final
byte for **14,571 of 14,571 FA1 chunks — the complete `flags=515` population,
every row visited, 371,998,300 bytes, zero failures** (MEASURED). Closure is
*our* assertion, not the client's: the parser's success path
(`0x00796905`) never compares cursor to end — verified independently twice —
so N green walks are N real checks, unlike FA0's client-gated closure.

| | |
|---|---|
| A **prop** | FA0 geometry + FA1 absent-or-degenerate (< ~1 KB: one sequence, no keys) |
| A **unit body** | FA0 geometry + FA1 in the tens-to-hundreds of KB (worm 116366: 82,169 B) |
| A **composite shell** | FA1 without FA0 (+FA6 sound cues, +FA8 linked models); hatcher's 0x0056 file 116228 |
| The wire | GAME_SMSG `0x0056` names the shell/body file, `0x0057` supplies geometry-bearing bodies when the 0x0056 file has none |

**The result worth carrying out of this arc**: FA1's flag byte at +0x08 is a
redundant presence bitmap, and its **bit 0 is ArenaNet's
`MODEL_SKELETON_FLAG_COMPOSITED` (MdlBuild:1556) ⟺ the enclosing file carries
no FA0 chunk — 14,571/14,571, two independent places in the archive**
(MEASURED). And that same bit is what the wire shows: every 0x0056-only
definition's file has its own FA0 (**8/8**), every definition that also got a
0x0057 has a file lacking FA0 (**36/36**), and every 0x0057 model id resolves
to a file carrying FA0 (**43/43** — *population corrected by U4, 2026-08-16:
the noun here was wrong; 43 is the PER-DEFINITION pooled count over all
three captures, not distinct model ids, of which 143055 has 33 (33/33) and
the pool 40 (40/40) — [../unitassembly/FINDINGS.md](../unitassembly/FINDINGS.md)
§4 pins every granularity*) — measured on live capture 20260807T143055
(OBSERVED + MEASURED, two agents, neither knowing the other's result).
COMPOSITED means "my geometry comes from elsewhere", and 0x0057 is where.

> **The withheld cell of this law is now WATCHED, 2026-08-17.** Every row above
> is correspondence — nobody had ever made the client RENDER a declared
> COMPOSITED definition with its 0x0057 withheld. The `composite_withheld`
> probe did (harness `20260817T143717`, control arm differing in exactly the
> one message): **a solid white untextured box, body-sized, at the create's
> position** — no crash, no invisible agent. The client draws a positive
> placeholder where the composite should have hung its geometry, OBSERVED.
> A white box on any spawn is now a diagnosable signature rather than a
> texture mystery. `studies/unitsetup/FINDINGS.md` §8 Q10.

The other headline answers:

- **The flags-2817 stream (M6b's open question) is solved**: it is the tail of
  a 3-row `nextStream` chain (515 head → 1 mid → 2817 tail, bijective) behind
  94.8% of model heads; the other 5.2% chain directly to a texture. Mid and
  tail rows are themselves valid ffna type-2 containers carrying 16
  previously-uncatalogued chunk ids — purpose UNVERIFIED (§2.2).
- **The trailing blocks are named** (§4): H = streak systems (occurs on **0 of
  20,661** geometry chunks in this full retail archive), I = the `vo`/`objCurr`
  switchable-part command lists, J = `m_sClouds` particle sources + emitters —
  and J's size identity is **the client's own equality gate**, not a corpus
  discovery.
- **FA6 is the model's sound-cue list** — every reference reaches an ffna
  type-8 sound descriptor whose own references decode as valid MPEG-1 Layer III
  frame headers, **231/231** (§5.2) — and it lands at the skeleton offsets
  MdlAnim:2040 bounds as `m_soundPathCount`/`m_soundPaths`. **FA8 is a
  linked-model list resolved recursively at load** through a cached
  by-id loader (§5.3).
- **No per-vertex skinning vocabulary exists in the assert corpus** — zero
  hits for `joint`/`weight`, one `Bone` (a MdlCombine switch label), no
  skin-matrix palette; the only skeletal-hierarchy machinery named is
  MdlCombine's push/pop transform stack. RECONSTRUCTION, floor not census:
  GW1 units read as rigid-segment models (§3.10).
- **What is NOT decoded** *(as of the recon; §6 tracks what U2/U3 closed
  the same day)*: the contents of FA1's two big animation payloads
  (blk2C/blk48 — strides byte-exact, elements unnamed; a quaternion reading
  was REFUTED at 4/19,460 — **that refutation is REVERSED in §3.4's dated
  correction**: wrong overlay, real quaternions), the mid/tail chain chunk
  families (classified by U3), chunk 0xFAE (named by U2/U3: n3E's
  model-file table), and the ffna8 descriptor's parameter stream (still
  open). §6 is the honest list.

---

## 2. The corpus and its classes

### 2.1 MFT flags do not classify; the chunk signature does

MEASURED, exact, no decompression. The full-archive flags histogram over all
177,341 rows reproduces `toolkit/mapdata/mapchunks.py`'s documented census
exactly (3: 110,852 · 1: 21,769 · **515: 21,421** · **2817: 21,420** ·
257: 1,118 · 3073: 393 · 259: 349 · 0: 12 · 65283: 7). All three anchors —
116703 (geometry body), 116228 (geometry-less shell), 116366 (unit body) —
resolve via `file_id_table` to **flags=515** rows. So flags=515 is
"addressable model-file head", nothing finer; prop/unit/composite lives in the
chunk-id signature inside that one bucket.

**The archive is full retail, not a study subset** (adversarial verification,
answering the trailing-block recon's own open question): 4.20 GB / 177,341
rows against the pinned client's own `Gw.dat` at 4.20 GB / 177,334. Every
"never occurs" below is therefore the strong claim, scoped to a full-scale
retail archive.

### 2.2 The flags-2817 stream, resolved

MEASURED. Every flags=515 head carries a nonzero `alloc.nextStream`:

- **20,303/21,421 (94.8%)** chain 515 → flags=1 mid → flags=2817 tail.
  Bijective, depth exactly 1 (independently re-derived; matches
  `studies/datwrite/FINDINGS.md`'s separately recorded link).
- **1,118 (5.2%)** skip the chain and point directly at an ATEX texture row
  (725 → flags=257, 393 → flags=3073). Sampled, these are small simple props.
  Whether "no mid/tail" means exactly "no skeleton extras" is unmeasured.
- Mid and tail rows are not file-id addressable (0/21,420 each) and are
  **independently valid ffna type-2 containers** carrying new chunk families:
  mid `0xBB8–0xBBD, 0xBBF–0xBC1` (+ `0xFA3`, `0xFAA`; 27 sub-signatures), tail
  always `0xFAC` (+ `0xFA4`, `0xFA7`, sometimes `0xFAB`; 5 sub-signatures).
  Purpose **UNVERIFIED** — no disassembly of their fetch sites has been done;
  the way FA0/FA1's fetch sites were read is the template (§6).
- `0xFA2` was observed nowhere in any sweep — NOT FOUND, stated as the
  ranges searched. ~~`0xFA9` likewise~~ **REFINED by U3's full-population
  sweep, 2026-08-16**: `0xFA9` EXISTS — 2 heads (rows 176432/176439),
  byte-identical 5,340-byte payloads, not a reference list; the strided
  sweeps this section reported could not see a 2-row population
  ([../mdlrefs/FINDINGS.md](../mdlrefs/FINDINGS.md) §3.3). Contents
  UNVERIFIED (parser `0x00796C30`).
- FA1 exists **only** on head rows: 0/2,722 sampled mid rows and 0/2,678
  sampled tail rows carry one (floor, stride-8 samples).

One anomaly: flags=515 **row 8316** decompresses to 28 bytes with no ffna
magic — found by the census, independently reproduced by the full-population
walk. Unexplained; it is why the head bucket is 21,421 with 21,420 chains.

*Recorded correction:* the trailing-block recon's type-2 first-chunk census
mis-binned 15,094 `0xFAC`-first files as "too short" — the true `0xFAC` bin is
**21,420** (its scanner truncated reads). The FA0 figure was unaffected.

### 2.3 The head-class census

MEASURED, stride-4 over the full 21,421-row range (5,356 rows decoded exactly;
a full decode was started, measured at ~106–120 ms/row, and honestly aborted
for the complete-coverage stride pass). Every sampled row closed on its exact
final byte. Eleven signatures; "≈" is ×4.0002 extrapolation:

| signature | n /5,356 | ≈ full | FA1 min / median / max (bytes) |
|---|---:|---:|---|
| FA0,FA1,FA5 | 1,948 | ≈7,794 | 133 / 149 / 426,231 |
| FA0,FA5 | 1,042 | ≈4,169 | — |
| FA0,FA1,FA5,FA6 | 678 | ≈2,713 | 171 / 1,549 / 817,925 |
| FA0,FA5,FAD | 678 | ≈2,713 | — |
| FA0,FA1,FA5,FAD | 633 | ≈2,533 | 133 / 165 / 522,748 |
| FA0,FA1,FA5,FA6,FAD | 192 | ≈768 | 171 / 1,271 / 1,367,185 |
| **FA1 only** | 78 | ≈312 | 10,417 / 204,150 / 2,946,637 |
| FA1,FA6 | 47 | ≈188 | 86,212 / 452,522 / 965,611 |
| **FA1,FA6,FA8** (116228's shape) | 43 | ≈172 | 1,709 / 18,732 / 1,704,858 |
| FA1,FA8 | 15 | ≈60 | 1,751 / 46,611 / 726,669 |
| FA1,FA6,FAE | 2 | ≈8 | 332,801 / 1,197,297 |

**FA1 size is bimodal, and the full population confirms the sample**: the
14,571-chunk exact histogram is 74.9% under 1 KB / 13.0% 1–5 KB / 4.1%
5–20 KB / 1.8% 20–50 KB / 6.2% over 50 KB, against the census sample's
74.5/13.5/4.0/1.8/5.7 — two independently written scanners, one shape. The
near-zero mode is the degenerate prop skeleton (§3.7a); the heavy tail is the
unit population.

**The "FA1 only" class (≈312 files, all large FA1) is at least partly the FA8
link-target population**: 221 of 257 sampled FA8 references are exactly
FA1-only files (§5.3). RECONSTRUCTION as an explanation — coverage of the
class by FA8 referencers was not measured — but the census's "unexplained
class" is no longer unanchored.

### 2.4 The classifier and the anchors

| file id | signature | reading |
|---|---|---|
| 116703 (hatcher body, the 0x0057 model) | FA0 + FA5 | plain geometry file, no skeleton chunk |
| 116366 (burrowing worm, 0x0056-only on the wire) | FA0 + FA1(82,169) + FA5 + FA6 | self-contained unit: geometry + big skeleton + sound cues |
| 116228 (hatcher's 0x0056 file) | FA6(184) + FA1(29,495) + FA8(94) | geometry-less composite shell |

The classifier (stated as a prediction by the census, and now grounded in the
COMPOSITED bit rather than in size alone): prop = FA0 with FA1 absent/tiny;
unit body = FA0 with large FA1; composite shell = FA1 without FA0, bit 0 set.

### 2.5 A consistency closure across three scanners

The head bucket partitions **exactly**: 20,661 FA0-first (adversarial's
whole-archive census, = the models arc's own §5.3 figure) + 371 FA1-first +
388 FA6-first (both adversarial) + 1 non-ffna anomaly = **21,421**. And
371 + 388 = **759** = the full-population walk's independently derived
geometry-less (COMPOSITED) count. Heads carrying FA1 = 14,571 (68.0% exact,
vs. the census's 67.9% estimate); FA0-without-FA1 works out to 6,849 exact
vs. 6,879 estimated from the stride-4 classes. Three scanners, no shared
code, zero remainder.

---

## 3. The FA1 chunk is the skeleton — derived, then verified at full population

### 3.1 Fetch and parser identity

SOURCE-CODE, build 38797. The get-chunk helper is `0x00907C70` (cdecl:
ctx, chunk_id, &size → ptr|NULL; release `0x00907D30`), with 30 direct call
sites. Exactly two pass `0xFA1`: **`0x00794827`** (the loader) and
`0x0079E9E8` (a second consumer, §6). The loader function `0x00794780`
fetches, in fixed order into the same object: `0xFA6` (`0x007947B7`, →
+0x80/+0x84), `0xFA8` (`0x007947D0`, → +0x10C/+0x110, plus a fresh
`count×4` array at +0x114), `0xFAE` (`0x0079480F`, → +0x9C/+0xA0), then
`0xFA1`. The FA1 gate at `0x0079494C` repeats FA0's exactly: size ≥ 4 and
first u32 == `0x26` (`0x0079495D`), then `call 0x796310` — the parser,
thiscall(begin, end), returning 0 on success.

**This closes the models arc's "second geometry-object producer" question**
(and it was answered independently by both verification agents): `0x00796310`
— the function `studies/models` flagged as the mystery second writer of the
geometry object's fields — **is the FA1 parser**, single xref `0x00794966`,
reached only through `GetChunk(0xFA1)` under the same `0x26` version word FA0
requires. `0xFA0` is fetched on a different path (site `0x0079456C`, inside
the cached by-id loader `0x00794260`) — which is why a shell like 116228
legitimately has FA1 and no geometry.

### 3.2 The object is `m_skel` — and a recorded tension about object identity

The naming is ArenaNet's, not ours. `MdlSeq:300`
`seqIndex < m_skel->m_seqCount` compiles to `cmp edi,[eax+0x6c]` with the
sequence array at `[eax+0x70]`, stride 32 (`0x00792F28–0x00792F53`); the FA1
parser writes exactly those (`0x007964DB` header u32@+0x18 → +0x6C;
`0x007965F5` its built array → +0x70). `MdlBuild:1556`
`(m_skel->m_skeletonFlags & MODEL_SKELETON_FLAG_COMPOSITED) || !m_skel->IsValid()`
reads `test byte [eax+0x38], 4` (`0x0077E8B8`), and the parser sets that bit
from header byte +0x08 bit 0 (`0x00796857/0x0079685D`). So the object FA1
fills is `m_skel`, its +0x6C is `m_seqCount`, its +0x38 is `m_skeletonFlags`.
SOURCE-CODE.

**The tension, recorded rather than smoothed over**: the adversarial pass
proved the same parser also writes the *geometry-family* offsets the FA0
parser writes — +0x78 (`0x00796645`), +0x90 (`0x00796800`), +0x98
(`0x00796836`), **+0xA4 = `m_geoCount`** (`0x00796605`, from `u16@+0x52`),
+0xB8/+0xBC (`0x00796473/0x00796492`) — against FA0's `0x00795529` /
`0x00795707` / `0x00795717` / `0x0079557A` / `0x00795753` / `0x00795772`. And
the FA0 parser **does** write +0xA4 too (`0x0079557A`, from header u32@+0x44 =
`num_models`, gated ≤ 0xFE at `0x00795588`) — refuting the trailing-block
recon's "only writer" claim. Meanwhile FA6's array lands at +0x80/+0x84 of the
FA1 loader's object, where MdlAnim:2040 reads
`m_skel->m_soundPathCount`, while the FA0 parser's object holds
`m_lightningSystemCount` at *its* +0x80 (MdlCombine:2019). Whether `m_skel`
and `m_geom` are two views of one allocation, two objects sharing a layout, or
one layout with per-file role selection — and what two writers of +0xA4 mean
on a file carrying both chunks (load order puts FA0's write last) — is
**UNVERIFIED and open** (§6). Nothing in this arc resolves it, so nothing here
claims to.

### 3.3 The header — 0x58 bytes

Every row's evidence is a printed disassembly instruction in the recon report;
corpus figures are the full 14,571-chunk population. Fields with no consumer
stay unnamed.

| off | type | what | status |
|---|---|---|---|
| +0x00 | u32 | version, must be `0x26` (gate `0x0079495D`); 38 on 14,571/14,571 | SOURCE-CODE + MEASURED |
| +0x04 | u32 | never read by this parser; 0 on 14,571/14,571 | MEASURED |
| +0x08 | u8 | flags → `m_skeletonFlags`; a presence bitmap (§3.8); parser reads only bits 0 and 1\|2; 42 distinct values; +0x09..+0x0B unread | SOURCE-CODE + MEASURED |
| +0x0C,+0x10,+0x1C,+0x24 | u32 | → m_skel +0x3C/+0x40/+0x44/+0xF8 | UNVERIFIED |
| +0x14 | u32 | **n14** — 0x10-byte records `{u32 slot, f32×3}`, looked up by slot 0/1/2 into three vec3 at m_skel+0x48; semantics unnamed; **0 on 227 files** | SOURCE-CODE; contents UNVERIFIED |
| +0x18 | u32 | **`m_seqCount`** — 0x17-byte sequence records (§3.9) | SOURCE-CODE (MdlSeq:300) |
| +0x20 | f32 | → m_skel+0x100, compared against qword const `0x0093CF10`; 16 distinct values | UNVERIFIED |
| +0x28 | f32 | → m_skel+0xFC; 1.0 on 14,411 | UNVERIFIED |
| +0x2C | u32 | **n2C**, asserted `animCount` (MdlLoad:373); **zero is error 12 and never occurs, 0/14,571** | SOURCE-CODE + MEASURED |
| +0x30 | i32 | read signed (`jl` at `0x007968EB`); `0x80000001` on 916 rows | UNVERIFIED |
| +0x34 | u32 | n34 — 24-byte records | SOURCE-CODE |
| +0x38 | u32 | n38 — var-array, elem 0x0C, tail `u32@rec+4 × 4` | SOURCE-CODE |
| +0x3C | u16 | **n3C** — the key table, SoA, ×5 (§3.9) | SOURCE-CODE |
| +0x3E | u16 | n3E — two raw arrays, ×4 then ×8; **fires on 6 files, all close, sabotage 0/6** | VERIFIED (was 0/246) |
| +0x40 | u32 | n40 — ×0x16 | SOURCE-CODE |
| +0x44 | u32 | n44 — ×12 | SOURCE-CODE |
| +0x48 | u32 | **n48**, also asserted `animCount` (MdlLoad:432) — **independent of n2C**: equal on 242/971 (24.9%). The shared name is a helper parameter name, not equality | MEASURED correction |
| +0x4C | u32 | never read; 0 on 14,571/14,571 | MEASURED |
| +0x50 | u16 | n50 — var-array, elem 8, tail ×8 | SOURCE-CODE |
| +0x52 | u16 | n52 — var-array, elem 0x10, count @rec+0xC, tail ×4; **also stored to +0xA4 (`m_geoCount`)** — see §3.2 | SOURCE-CODE |
| +0x54 | u8 | n54 — elem 8, tail ×8 | SOURCE-CODE |
| +0x55 | u8 | n55 — elem 8, tail ×8 (callback `0x796F80` — a transcription error here was **caught by the recon's own sabotage suite** and fixed) | SOURCE-CODE |
| +0x56 | u8 | n56 — elem 8, tail ×5 (callback `0x00796E60`) — **fires on 0 of 14,571**; disasm-only | **UNVERIFIED** |
| +0x57 | u8 | n57 — elem 8, tail ×20 — **fires on 135 files, all close, all four sabotages 0/135** | VERIFIED (was 0/246) |

### 3.4 The block walk

Cursor = begin + 0x58; order is code order (`0x0079632C` on): n14 → n34 →
**blk2C** → n38 → n3C → n18(sequences) → n52 → n40/n44 → **blk48** → n50 →
n54 → n55 → n56 → n57 → n3E. The var-arrays share one helper
(`0x00794C40(cursor, end, count, elem, tailFn)`, assert MdlLoad:107) with five
tail callbacks whose multipliers were each read from their own arithmetic
(×4, ×8, ×20, ×5, and count-at-+0xC ×4). The two big animation blocks:

- **blk2C** (`0x00796AD0`, assert MdlLoad:373): n2C fixed 0x10-byte records,
  then n2C variable records of a 6-byte sub-header `{w0,w2,w4}` +
  `(w0+w4)×16 + w2×20` bytes of payload.
- **blk48** (`0x00796970`, assert MdlLoad:432): n48 fixed 20-byte records,
  then n48 variable records of a 4-byte sub-header + `(w0+w2)×16`.

Element **contents** of both payloads are **NOT DECODED** — strides only. The
recon's one attempt to shortcut this (unit quaternions in the 16-byte groups)
was **REFUTED by its own test**: 4 of 19,460 within 1e-3 of unit norm, median
norm 6.07. They stay unnamed; naming from size is this repo's recorded
mistake.

**REVERSED by U2, 2026-08-16, and the reversal survived adversarial review**
([../anim/FINDINGS.md](../anim/FINDINGS.md)): the "(w0+w4) 16-byte groups +
w2 20-byte groups" reading above is the correct BYTE ACCOUNTING and the
wrong SHAPE — the payload is times-prefix structure-of-arrays channels
(w2 int32 times, then w2 float4 values), read from the samplers' own
address arithmetic (`base + 4·count + 16·idx`, `0x00782990`). At that
alignment the float4s ARE unit quaternions — 16,263,916/16,263,916 within
1%, and 100.000% at 0.1% too — and the client's nlerp renormalizes through
a fast path gated on `len² ∈ [0.9, 1.1]`, only correct for unit inputs.
The 4/19,460 refutation above was TRUE OF THE MISALIGNED OVERLAY and
reproduces as the control (0.30% at equalized tolerance). The paragraph
above is kept as written because the walk's strides were never wrong —
only the shape drawn over them — and a refutation that was itself an
artifact of a framing is exactly the failure mode worth exhibiting.

An **independent second implementation inside the client agrees term for
term**: `0x0079E420` (reached from the second FA1 fetch) walks the same header
— 0x58, n14×16, n34×24, blk2C's identical `(w0+w4)×16 + w2×20`, n38's elem
0x0C + tail×4, n3C×5 — a second compiled witness to the derivation.

### 3.5 Verification: 14,571 / 14,571, and what closure does and does not prove

The verification agent **re-disassembled every stride and gate from the
pinned binary before implementing** (705-line dump of `0x00796310` retained),
then walked the complete population:

| class | closed | of | FA1 bytes min / median / max |
|---|---:|---:|---|
| UNIT_GEOMLESS (no FA0) | 759 | 759 | 1,627 / 208,512 / 2,946,637 |
| UNIT_BODY (FA0, FA1 ≥ 20 KB) | 525 | 525 | 20,152 / 103,567 / 1,367,185 |
| TRANSITION (FA0, 1–20 KB) | 2,373 | 2,373 | |
| PROP control (FA0, < 1 KB) | 10,914 | 10,914 | 133 / 149 / 997 |
| **total** | **14,571** | **14,571** | |

Both anchors byte-exact from the independent implementation (116228:
29,495/29,495; 116366: 82,169/82,169). Run twice, identical counts. The
death-point histogram is **empty** — no gate fired anywhere, including on the
2.9 MB maximum.

**What closure does NOT prove**, stated so the number is not over-read: the
order of adjacent *fixed-size* blocks (closure tests the sum; only blocks that
read a count from the stream pin order — §3.6's structural control); any
element's contents; n56's stride; the 23-byte record's unnamed fields.

### 3.6 Sabotage and controls

52 one-term mutations, each scored on the subpopulation that exercises the
term (full table in the verification run records). Nearly all collapse to
0-to-few. The instructive results:

- **Most wrong terms die at the client's own bounds gates**, not at our
  closure check — i.e. the retail client would itself refuse them. Only
  `n57`'s multiplier and one n3E variant die at closure alone (they sit last,
  with nothing to overrun into).
- **Two survivors were explained by measurement, not assumption**: doubling
  n38's or n50's tail multiplier survives 12%/8.8% because the overshoot lands
  inside the next record and reads a count of 0 there — data aliasing on
  repeated `[2,2]` patterns (row 7868 exhibited), not an unconstrained term.
  The verifier's first explanation (all-zero tails) was **wrong** (5/1,500)
  and is recorded as such.
- **The structural control behaves in both directions**: moving the n38
  var-array past n3C collapses closure 0/690 where n3C>0 (675 dying at the
  *client's* n38 gate) and correctly leaves 400/400 where the move is vacuous.
  No control was written for swapping two fixed blocks — that would be a check
  that cannot fail, and the walker's comments say so.
- **A cross-field invariant the decoder cannot force**: every sequence
  record's `lo ≤ hi ≤ n3C` — lo/hi from the 23-byte records, n3C from the
  header, the key array independently located — holds over **50,127 records,
  21,535 non-zero spans, zero violations**.

**CORRECTED at full population by U1's committed test, 2026-08-16 (later the
same day).** The per-variant `survives=0` figures above were measured at
n=600 per variant; `test_skelfile.py --all` re-ran sixteen variants over
every file that exercises each term and found aliasing survivors in **six
variants both samples had called clean**: hdr=0x54 — 1 of 14,571; hdr=0x5C —
29 of 14,571; n14_elem=12 — 1 of 14,344; n34_elem=20 — 1 of 4,938;
b2c_sub=4 — 1 of 14,571; n3c_elem=4 — 1 of 1,144; n18_elem=0x16 — 2 of
14,571. Same mechanism as the n38 survivor above (a shifted read landing on
bytes that re-close the walk; RECONSTRUCTION for these six — the rows are
printed by the run, not yet individually inspected). The rows: **31419
survives THREE distinct mutations** (hdr=0x54, n14_elem=12, n34_elem=20 —
whatever its bytes are, they absorb a ±4 shift three ways, the obvious first
target for inspection); b2c_sub=4 → 33554; n3c_elem=4 → 153847;
n18_elem=0x16 → 11279 + 150877; hdr=0x5C's 29 include 32876, 33159, 33168,
38002, 38862, 38885, 39950, 69522. Worst
case 0.2%, so every term stays load-bearing — but "collapses to zero" was a
sample truth, and closure on any SINGLE file is correspondingly not proof of
the layout on that file. The test pins the measured ceilings; a run above
one is a regression, not noise. Its other full-population figures land
exactly on the study's: closure 14,571/14,571, order control 690 non-vacuous
→ 0, grid 31,556/31,571 (99.95%), n38_mult 433/3,613 (12.0%).

### 3.7 Corrections the full-population run forced on the derivation — RECORDED

**(a) The format floor is 133 bytes, not the recon's "exactly 149".** 149 is
the *mode* (5,598/14,571); 133 occurs on 11 files where n14 == 0 (the recon's
arithmetic assumed n14 = 1; n14 is 0 on 227 files).

**(b) ArenaNet's MdlAnim:367 prediction (`keyTimes[lo+1] > keyTimes[lo]`)
FAILS at scale.** The recon reported 68/68 strict at n=68; at n=9,321 spans it
is **9,311/9,321 — 10 violations**, all exact duplicate times, one per file in
10 UNIT_GEOMLESS files. The verifier's rescue hypothesis (tag-partitioned
channels) was **REFUTED on exactly the same 10 spans**. What holds corpus-wide
is **non-decreasing: 9,321/9,321**, zero decreases. This is consistent with
the recon's own caveat that MdlAnim:367's array is *not* the one this parser
builds (its access is a stride-4 `fild` int32 array; the parser emits 8-byte
`{tag, f32}` records) — so either the assert governs a different array, or
those 10 files would trip retail. Open (§6). The local-vs-global shape
survives at scale: only 79/913 multi-key files are *globally* sorted, so the
per-span reading passes exactly where the global one fails.

**(c) n57 and n3E moved from UNVERIFIED to VERIFIED** (135 and 6 firing
files; all close; all sabotage variants collapse). **n56 stays UNVERIFIED with
a 59× stronger floor**: 0 of 14,571.

**(d) n2C and n48 are independent counts** despite both being asserted
`animCount` (§3.3 table).

**(e) The key-time scale is real and confirmed at scale**: the constant at
`0x00A571B0` is 1e-5; of 32,356 key values, 31,556 of 31,571 non-zero
(99.95%) are exact integer multiples of **1/30 s**. Tag bytes take only
{1, 2, 6, 19, 20, 21}; the dominant per-span tag-set is {2,6} (7,632 spans).

### 3.8 New — the flag byte at +0x08 is a redundant presence bitmap

MEASURED per-row over all 14,571 chunks, bit set ⟺ field non-zero:

| bit | equivalent to | agreement |
|---|---|---|
| **0** | **the file has NO 0xFA0 chunk** — `MODEL_SKELETON_FLAG_COMPOSITED` (MdlBuild:1556) | **14,571/14,571** |
| 1, 2 | *no corpus correlate* — the only two bits the parser actually reads | unnamed |
| 3 | n34 ≠ 0 | 14,571/14,571 |
| 4 | n18 ≠ 0 — **vacuous** (both sides constant), flagged, not counted | — |
| 5 | n48 ≠ 0 | 14,571/14,571 |
| 6 | n50 ≠ 0 | 14,571/14,571 |
| 7 | n38 ≠ 0 | 14,571/14,571 |

Bit 0 lives inside the FA1 payload; "has an FA0" is a property of the
enclosing container's chunk table — two independent places in the archive,
and nothing in the walk can force the agreement. The irony is recorded: the
bits the parser never reads (3,5,6,7) mirror block presence exactly; the two
it does read (1,2) are the ones with no correlate, and they are the
highest-value next disassembly (§6).

### 3.9 The sequence and key layer

- **The 23-byte sequence record** (copied to a 32-byte in-memory record at
  `0x007965A0–0x007965DD`): `u8 @+0x00`, `u32 @+0x01/+0x05/+0x09/+0x0F`,
  `f32 @+0x13` — all **unnamed** — plus `u8 lo @+0x0D`, `u8 hi @+0x0E`
  selecting `keys[lo:hi]` from the key table. Only lo/hi are named, and only
  because the span-binding test could have refuted them (§3.6).
- **The key table (n3C) is structure-of-arrays**: n3C int32 times (×1e-5 s),
  then n3C tag bytes — not array-of-structs; the naive AoS reading is wrong
  and the SoA loop is quoted in the recon (`0x00796540–0x0079656C`).
- Props are not skeleton-less; they carry a **degenerate** skeleton: 155 of
  246 first-sample chunks under 400 B with `m_seqCount == 1`,
  `animCount == 1`, no keys — which is what the bimodal histogram's near-zero
  mode is.

### 3.10 The vocabulary sweep: no skinning, and a clean layering

Single-witness (asserts agent), floors not censuses, over 19,758 read sites in
66 TUs (16/16 Engine\Model, 8/8 Gw\Composite, 8/8 Engine\Agent, 13/13
Gw\Char, 21/21 Gw\AgentView):

- `joint`: **0 hits**. `weight`: **0 hits**. `skin`: 2, both UI-widget skins.
  `palette`: 24, all indexed-image palettes in Engine\Gr. `bone`: **1** —
  MdlCombine:1425 `No valid case for switch variable 'BoneFlags'`, a switch
  label in the combine-time transform stack (`matrixStack`,
  `transformRemap[]`, `matrixIdTop`, pop-counts). RECONSTRUCTION, explicitly
  inferred from absence over a floor (370 unreadable sites remain): the
  subsystem's asserted vocabulary never names per-vertex skinning; the only
  hierarchy machinery is a push/pop rigid transform list. Consistent with
  rigid-segment characters; not proven by absence.
  **↳ UPGRADED 2026-08-19 — the push/pop reading no longer rests on absence.**
  Every one of those names is a literal string in build 38797, and they sit in
  ONE `.rdata` run at `0x00678F44`–`0x00679160` because MSVC emits a TU's
  assert expressions in source order. Two of them settle the mechanism
  positively rather than by silence:
  `(matrixIdTop >= 0) || !parentId` (`0x00679028`) and
  `matrixStack.Count() <= MDLEXP_CHUNKFLAG_LASTPOPCOUNTMASK` (`0x006790EC`).
  The first ties the stack's TOP to whether the node HAS A PARENT, which is
  what a hierarchy walk asserts on descent and is meaningless to a skin-matrix
  palette; the second bounds the stack's depth by a **pop-count mask carried in
  the chunk flags**, where a palette would be bounded by a hardware register
  count. `popCount <= MDLEXP_GEOANIMFLAG_POPCOUNTMASK` (`0x00679078`) is the
  third witness. **CORROBORATED — it is a rigid push/pop hierarchy flattener,
  not a skinning palette.**
  **And `parentId` is ARENANET'S OWN NAME for the blk2C link byte** — the
  bits-0-7 LINK field of [../anim/FINDINGS.md](../anim/FINDINGS.md) §3.4,
  `< n2C` and `<= own index` on 121,532/121,532 — which moves it from
  RECONSTRUCTION to **OBSERVED**. Two more names in the same run are the
  asserts behind guards `modelwrite.py` already enforces:
  `transformCount <= MAX_TRANSFORM_IDS` (`0x00678F44`, the 1..4 group bound)
  and `sum == transforms->Count()` (`0x00678FA8`, MdlCombine:860's closure).
  A fourth is new information: `(*transformRemap)[src].actionPtCount <
  MDLEXP_MAX_ANIM_ACTIONPOINTS` (`0x006790A8`) shows a remap entry carries an
  **actionPtCount** beside its `.transform` — action points are per-transform,
  and we have never decoded them. OBSERVED, build 38797, by string search
  (`bytes.find`, no disassembler).
- The layering is clean: **Gw\Char** (stats/appearance-slot data) →
  **Engine\Agent** (world object: position, movement, timers — zero
  model vocabulary) → **Gw\AgentView** (render proxy: AvChar's action/sequence
  queues, `seqIndex != SEQ_INDEX_UNDEFINED` at AvChar:8212, `m_composite`) →
  **Engine\Model** (skeleton/geometry/anim) + **Gw\Composite** (per-equip-slot
  layering, race/sex/profession keyed).
- MdlLoad:1150 tests an `MDLEXP_` constant against just-loaded data — the
  on-disk format and the MdlCombine/MdlDecomp "export format" constants are
  one vocabulary, which matters for authoring (the ladder's summit).

### 3.11 Two facts an author needs, measured 2026-08-19

Both came out of the composite-remap pass and neither was written down; both
are cheap to re-run and the commands are in the bullets.

- **A SKELETON IS SHARED ACROSS SHELLS, so editing one edits several
  creatures.** Median per-node base distance between shells claimed to share a
  skeleton, over `Skeleton.load(fid).anims()`:

  | group | n nodes | median per-node distance |
  |---|---|---|
  | 116228 ↔ 184409 | 86 | **0.0002 u** |
  | 116227 ↔ 141551 / 141267 / 141285 / 279140 | 90 | **0.0000 u** (all four) |
  | 116225 ↔ 141286 / 161433 | 105 | **0.0000 u** (both) |

  **The metric is not vacuous, and the control is what says so**: the same
  comparison on a pair nobody claims are related (116228 vs the burrowing worm
  116366) does not even reach the distance test — the node counts differ, 86
  vs 20. Six of the seven pairs are at 0.0000 u, i.e. bit-identical rest
  poses, not merely similar ones. OBSERVED. **Consequence for `skelwrite`: a
  base edit like U7's ×2 reaches every shell in the group, and the file id you
  wrote is not the only creature that changes.** Nothing in the toolkit warns
  about this yet.

- **`transformRemap` is NOT the identity even for a ONE-BODY unit**, so the
  "one body means no renumbering" intuition is wrong. On the client-confirmed
  hatcher pair — shell 116228 (86 blk2C nodes), body 116703 (4 sub-models):
  the body's vertex groups reference **53 distinct transform ids**, and they
  are **sparse** — `min 2`, `max 84`, with **32 gaps** below the maximum
  (0, 1, 3, 4, 6, 7, 11, 12, 14, 15, 16, 17, 25, 30, 46, 47, 50–57, …) and
  **33 of the 86 shell nodes never referenced at all**. That sparse set is
  precisely why the table exists and why `.transform` is a dense counter on
  the OUTPUT side (U9 follow-up in [PLAN.md](PLAN.md)). OBSERVED. It also
  re-explains an old dead end: nodes 51–57 sit in the unreferenced run, which
  is the same region the nearest-joint proxy kept nominating and no vertex
  ever binds to.

---

## 4. The trailing blocks, named

All three blocks after the collision meshes in the `0xFA0` geometry chunk now
carry ArenaNet's names, with the geometry-object offsets pinned by asserts
from two modules each. Corpus figures are whole-archive (20,661 geometry
chunks) unless marked; the adversarial pass re-derived every guard and
reproduced every census figure with its own walker (**4,108/4,108** closure
at stride 5, **1,835/1,835** replicate at stride 11, against the recon's
734/734).

### 4.1 Block H = streak systems + streaks — and it never occurs

SOURCE-CODE: array 1 = `u8@0x31` × 16-byte records → `m_streakSystemCount`
geom+0x90 / `m_streakSystems` +0x94 (MdlCombine:2023); array 2 = `u8@0x32` ×
0x54-byte records → `m_streakCount` +0x98 / `m_streaks` +0x9C (MdlAnim:1122).
Record fields partially read from the consumers (array-1 +0x08 is a bone index
or −1; array-2 +0x04 indexes array 1, per GrStreak:585).

**MEASURED: both counts are zero on 20,661 of 20,661 geometry chunks** — and
since the archive is full retail (§2.1), that is the strong claim. Two
consequences for the repo: `modelfile.py`'s H term has never been exercised by
any corpus file (the models arc's 20,661/20,661 closure is not evidence for
it — a synthetic fixture is the honest test, flagged for U1); and
`modelfile.py` does not implement the client's hard refusal (`u8@0x31 != 0`
with `u8@0x32 == 0` is error 0x1D at `0x00795664`) — moot at 0 occurrences,
but it belongs in the fixture.

### 4.2 Block I = the `vo` / `objCurr` command lists

SOURCE-CODE: `u32@0x48` records → geom+0xB8, each `u32 n` + n × 8-byte
entries `{u32 type; u32 index}`, pointer array → +0xBC. Named by ArenaNet at
both consumers: MdlAnim:1665/1702 `No valid case for switch variable
'vo->type'` and MdlCombine:1940 (`objCurr->type`), with `index` pinned at
entry+4 by MdlCombine:1923 `objCurr->index < geomPtrs[i]->m_geoCount`. Six-way
type dispatch: 0/5 = geoset visibility, 1 = a GrLight handle, 2, 3 =
instance-array pokes, 4 = a **unified index space** `m_geoCount + geom[+0x5C]
+ index` (re-derived independently by the adversarial pass). Each record is a
bit of a 32-bit instance mask at inst+0xD8 — which is why `u32@0x48 ≤ 32`
(max observed 29, 0 over, whole archive).

**Verification against the recon, both directions recorded:**

- Entries at n=2,363 (vs. recon's 1,078): types > 5 — **0**; type-0 index in
  range — **844/844**; swapped-field control fails (656/2,363 "types" > 5).
  CONFIRMED.
- **REFUTED: "type 1 never occurs."** It occurs — 5 of 2,363 entries. A
  small-sample artifact at n=1,078; exactly the repo's "widen before
  believing" trap. Type 5 remains 0/2,363 (a floor over a wider range).
- **Citation corrected**: the ≤32 mechanism is `lea ebx,[edi+1]` @`0x00782330`
  + `add ebx,ebx` @`0x007825BA` (bit = 1 << record index). The recon's cited
  `shl eax,cl` @`0x00782349` shifts by the record's own first u32 (the entry
  count) — what *that* is for is unexplained and left unnamed.
- **The type-0 bound and `m_geoCount` are one fact**: the FA0 parser writes
  geom+0xA4 from header `u32@0x44` (`num_models`) at `0x0079557A`, so the
  corpus check "type-0 index < u32@0x44" (844/844) is MdlCombine:1923's own
  assert with a compiled chain from header to bound.

Block I is the model's switchable-part/variant table. It is **not** a unit
marker: 93–96% of plain FA0+FA5(+FAD) props carry it, against 7–10% of the
FA1-carrying classes. 67% of records are empty (the mask bit itself may be
the payload — open). Presence: **9,571/20,661 (46.32%)**.

### 4.3 Block J = `m_sClouds` + emitters — and its identity is the client's own gate

SOURCE-CODE + MEASURED: `u32@0x34` bytes at geom+0x68, laid out as
`u32@0x38` **`m_sClouds`** records × 0x58 (named by MdlBuild:289–292's
flipbook asserts reading rec +0x3C..+0x4C), `u32@0x3C` **emitter** records ×
0x50 → `m_emitterCount` geom+0x60 (MdlAnim:1121 + MdlLoad:676, two modules),
and `u32@0x40` region-3 records × 0x18.

The recon predicted 0x14 for region 3, the corpus refused it (2,975/3,428),
and it corrected to 0x18 (3,428/3,428, rivals 0/3,428 on the first two
strides, 0/453 on the exercised third) — recorded as a prediction that failed
and was fixed by the artifact. **The adversarial pass then replaced the
derivation entirely**: the recon's appeal to MdlCombine's third pointer does
not carry the extent; the true source is **ArenaNet's own equality gate at
`0x0079621C`/`0x00796228`** — the client *refuses* any block J whose size is
not exactly `0x58a + 0x50b + 0x18c`. So the 3,428/3,428 census is a
precondition every loadable file satisfies by construction, not a corpus
surprise; it still discriminates stride triples (the rivals fail it), but a
census of it can never go red on shipping data. Region 3 is
`0x10·c + 0x04·c + 0x04·c`, the last array a u32 enum remapped through a
4-entry table at `0x00A7972C`.

**Emitters are partitioned among clouds sequentially**:
`Σ sCloud.u32@+0x50 == m_emitterCount` on **664/664** files (adversarial;
recon 340/340), never exceeded, with the mechanism read from the code — a
running byte cursor bounded by MdlLoad:676 — which makes the identity
structural, not statistical. Flipbook gate: 770/770 held where cellX==0,
468/468 discriminating where cellX≠0. Cloud bone field: −1 or a small index,
0 other values in 1,238 records.

Presence: **3,428/20,661 (16.59%)**, and **block J tracks the FA6 chunk**
(65–75% where FA6 is present, 0–10% where not) — the effects population, which
is also the unit population. Region-3 records (453 files, ≤4 each) are
unnamed; geom+0x5C (the sCloud count's field) has no ArenaNet name yet.

### 4.4 The refuted predictions, kept visible

- **Lights are NOT a trailing block**: `m_lightCount` is geom+0x48
  (MdlAnim:1956 + MdlCombine:1949, two modules), written from `u8@0x30` —
  **preamble block A**, 28-byte records, stride confirmed from the consumer
  side. Block A is present on 26 files (0.13%).
- **Sound paths are NOT on the geometry object**: MdlAnim:2040 bounds
  `pathIndex` by `m_skel->m_soundPathCount` — the skeleton — and §5.2 now says
  which chunk fills it. NOT FOUND in `0xFA0`, as a floor.

### 4.5 Census and the anchors

Whole-archive presence: A 26 / B 9 / E 2,293 (11.10%, unnamed) / F 709
(3.43%, `m_lightningSystemCount`, records undecoded) / **H 0** / **I 9,571**
/ **J 3,428**; any trailing block 49.62% — which is exactly the models arc's
old "NoClose" population, closing that account. Anchors, walked independently
by both agents, closing exactly: **116703** — block I = 3 records, all empty;
no J. **116366** — block I = 4 records of 1 entry, every entry type 2,
indices 0..3 (an adversarial detail the recon omitted); block J = 856 B =
0x58·4 + 0x50·6 + 0x18·1, with Σ cloud emitters = 6 = `m_emitterCount` — a
burrowing worm with four particle sources and six emitters, which is what the
naming predicts.

---

## 5. The composite file and the wire

### 5.1 The FA6/FA8/FAE loader, and the record framing — a correction recorded

All the small list chunks — FA5, FAD, FA6, FA8, FAE — go through **one
generic reader** (`0x00796DE0` → `0x00794B70` → `0x00908260`; exactly five
call sites, verified by xref). The recon's §1 framed FA6/FA8 as fixed 6-byte
records `{u16 id0, u16 id1, u16 pad=0}`; its own disassembly then found, and
the adversarial pass settled, that **the client's rule is
variable-length records terminated by the first zero u16 word** — the same
rule FA5's null slots already established in `studies/models` §6.1. The
corpus separates the framings on the shared code path: FA5 breaks fixed-6 on
390 of 2,215 chunks (876 two-byte null slots), while **every FA6/FA8 record
observed is 6 bytes** — including the complete FA6-first population, 388
files, 5,902 records — so `{id0, id1, 0}` is the universal *shape* in this
archive and fixed-6 is not the *rule*. A fixed-6 decoder would silently
mis-frame the first null slot; U3's decoder must implement the terminator.

ArenaNet's own name for a record is **`pathName`** (MdlLoad:2201
`PathIsRelative(pathName)` guards the FA8 loop): the records are NUL-terminated
wide strings, and a 2-wchar one is the file-id spelling
`dependency_file_id` decodes (cf. CpsData:468/469's `FILE_ID_RESERVED_BIT` /
`FILE_ID_MAX_PATH`). The helper-role naming of `0x00470300`/`0x0047E020` is
RECONSTRUCTION (named from call context, not disassembled). Every decoded
pair resolves in `file_id_table(raw=True)` — 400/400 (recon) and the
adversarial's independent sweeps.

Object offsets, confirmed verbatim by both agents: FA6 → +0x80/+0x84, FA8
count → +0x10C, array → +0x110, plus `operator new(count×4)` at +0x114; FAE →
+0x9C/+0xA0; FA5 → +0xC0/+0xC4; FAD → +0xFC/+0x100.

### 5.2 FA6 is the sound-cue list — and it is `m_soundPaths`

MEASURED + CORROBORATED: FA6 references are **uniformly ffna type-8** files
(1,493/1,495 classified, plus 2,466/2,466 in a second sweep and all anchor
lists), each carrying chunk 0x1 (a further dependency list, `len % 6 == 0` on
60/60) and chunk 0x2 (a small tag stream ending `0D 0A` on 60/60, undecoded).
The adversarial pass replaced the recon's negative magic test with a positive
one: **231/231 of the type-8 files' own references decode as valid MPEG-1
Layer III frame headers** (96 kbps at 44.1/32 kHz) — a wrong pair formula does
not produce 231 consecutive valid headers. This converges, from the model
side, with `toolkit/mapdata/soundchunk.py`'s independently written map-side
chain — and it discriminates: the *map*-level dependency list is mixed, the
model-level FA6 list is 100% type-8.

**The synthesis join, made here and labeled as such**: MdlAnim:2040
`pathIndex < m_skel->m_soundPathCount` reads m_skel+0x80; the loader writes
FA6's `(count, array)` to exactly +0x80/+0x84 of the object MdlSeq reads as
`m_skel` (§3.1, §3.2); FA6's records are sound-cue references. Therefore
**`m_soundPathCount`/`m_soundPaths` ARE the FA6 list** — "sound path" is
ArenaNet's name for a model's sound-cue reference. SOURCE-CODE, chained
across two agents' disassembly plus one classification result; no single
dedicated pass verified the chain end-to-end, so U2/U3 should confirm the
consumer at MdlAnim:2040 indexes the parsed FA6 array. This answers the FA1
agents' open question "what fills m_skel+0x80/+0x84".

### 5.3 FA8 is the linked-model list — resolved recursively at load

MEASURED: FA8 targets are uniformly ffna type-2, **none carrying FA0**
(257/257 + all anchors) — but the inference "not renderable, mere
aggregators" is **REFUTED**: **100% carry FA1**, which the client version-
gates and parses into the model object (§3.1), and 221 of 257 carry FA1 *only*
— they aggregate nothing. An FA8 target is a model whose content lives in FA1
instead of FA0.

Two further recon claims corrected by the adversarial pass, both recorded:

- **"The loader does not recurse; the duplication is authoring-side" —
  REFUTED.** The loop at `0x00794850–0x00794926` resolves every link at load
  through the **cached** by-id loader `0x00794260` and dereferences the
  result. The cache (global at 0xF26F10) is why 116228 duplicating 13 of
  15018's 13 own links is cheap; *why* the duplication exists is still open.
- **"FA8's array is CpsBase's `m_linkModels`" — REFUTED**, not merely
  unproven: `arrsize(m_linkModels)` is the compile-time-extent idiom (a fixed
  member array), while +0x114 is `operator new(count×4)` per file. **The real
  compiled bridge is MdlAnim `0x0078231C`**: it reads the +0x114 link array,
  selects a linked model, and walks *that model's* block-I `vo` list under the
  same 32-bit instance mask — joining the composite arc to the trailing-block
  arc in one instruction sequence. Neither recon had it.

**116703 (the hatcher's actual body) appears in none of 116228's FA6/FA8
lists nor one hop deeper** — confirmed byte-for-byte by both agents. The
stated prediction "the shell aggregates the body model" is REFUTED
specifically; the shell's body arrives by the *wire* (0x0057), not by FA8.
FA8 links same-kind shells/FA1-files; the two mechanisms are disjoint.

Caveat, carried from the adversarial pass: FA8 evidence is the thinnest in
this arc — 25 chunks / 257 records plus 4 anchors. Widen before leaning on it.

**FAE**: fetched by the same path, stored at +0x9C/+0xA0; population is
extreme-tail — 2 sightings in the census's stride-4 head sample (≈8 estimated)
and 0 in the adversarial's stride-7 sweep of 7,059 type-2 files. Contents
NOT FOUND; unmeasured.

**CpsData.cpp's "composite data file"** (path-addressed, profession×type
keyed) shows no call into the chunk machinery — the recon's caution that it is
a separate mechanism was verified. Gw\Composite's own object model (equip-slot
table with per-slot `fileId`, `CpsComponent` = model+overlay+textures,
`CpsPlayer` keyed by race/sex/profession, `CpsTex` blit ids shared with
MdlApi/MdlCombine) is documented from asserts in the sweep; its consumer-side
join to the loader's objects is future work.

### 5.4 The wire: 0x0056/0x0057, and the COMPOSITED rule made visible

OBSERVED (three live captures, framed to the exact final byte on all 11 game
connections, via `tape.decode_all` + the schema codec — the same pipeline
`npcdefs.py` uses, including its interval-join against agent-id recycling):

- Capture 20260807T143055: **44 distinct NPC/monster-class definitions** via
  0x0056; **8 are 0x0056-only** (1343, 1399, 1419, 1431, 1432, 1434, 1442,
  2280). Pooled over all three captures: 54 distinct definitions, **zero
  payload disagreements** on any repeated index. The per-capture counts
  exactly reproduce `studies/smsg/FINDINGS.md`'s figures — same corpus.
- **The archive rule** (MEASURED, 56/56 ids resolving via
  `file_id_table(raw=True)`, all ffna type-2): every 0x0056-only definition's
  file **has** FA0 (8/8); every definition with a 0x0057 has a file **lacking**
  FA0 (36/36); every 0x0057 body **has** FA0 (43/43 — the per-definition
  pooled count; U4 corrected this row's noun and pinned the distinct-id
  populations, 33/33 and 40/40). No exceptions. This
  refines `studies/smsg`'s open "what do the composite dwords encode" —
  MEASURED here: they are archive file ids of geometry-bearing files, not
  abstract piece selectors.
- **This rule and §3.8's COMPOSITED bit are the same fact**, measured by two
  agents from opposite ends (archive bit vs. wire traffic) with neither
  knowing the other's result. Synthesis: the client needs a 0x0057 exactly
  when the 0x0056 file's skeleton says COMPOSITED.
- Definition **1471** = file 116228 + model 116703 (nonc ×12) reproduces the
  Hatcher anchor pair byte-for-byte on the live wire; definition **1442** =
  file 116366 (mon1 ×151, 0x0056-only) is the worm.
- 0x0057 list lengths: 97× length-1, 4× length-2, against the client's own
  cap of 8 (CharMsg.cpp:4438 `compositeCount <= MONSTER_COMPOSITE_MAX_DWORDS`).
  All four length-2 messages are on non-combatant definitions (1496/1497,
  file 116377 → models 116759+116760, each carrying its own FA0). n=4 — a
  checked pattern, not a law.

### 5.5 Players, henchmen, and the other appearance messages

- **Players never get 0x0056/0x0057** (the definition space is
  CHAR_CLASS_MONSTER_BASE-tagged; 0 player-class joins in 3 captures). Player
  appearance is 0x0059 PLAYER_INFO's packed appearance dword (sex/profession/
  race bits) — the player-only analogue.
- 0x006E UPDATE_AGENT_VISUAL_EQUIPMENT targets player-class agents **130/130**
  (checked against both agent pools), 0 NPCs.
- **Henchmen/heroes: NOT FOUND** — 0x01BF/0x01C2 occur zero times in all
  three captures (Lakeside County is pre-Searing). Whether a henchman's
  composite differs from a monster's is structurally unanswerable from the
  vault's current contents; it needs a post-Searing capture with a hired
  henchman.
- **Open discrepancy, flagged not resolved**: 0x015E's field 2 is SOURCED as
  `ItCliApi.cpp:2410 msg.fileId`, but the observed values (hundreds) resolve
  in the study archive's file_id_table **zero** times, raw or masked — the
  client's own field name does not settle what it contains.

---

## 6. What is still unknown

Ranked; each names the tool that can settle it. These feed the ladder in
[PLAN.md](PLAN.md).

1. ~~**The animation payload contents**~~ **NAMED by U2, 2026-08-16, and
   the framing here was itself wrong**
   ([../anim/FINDINGS.md](../anim/FINDINGS.md), adversarially reviewed):
   the "16/20-byte groups" were the wrong overlay — the payloads are
   times-prefix SoA channels, blk2C is one record per animated node
   (translation + QUATERNION rotation + aux; the link byte is the
   hierarchy), blk48 is GrTrans stream-3 tracks. **This document's §3.4
   quaternion refutation is REVERSED** — see the dated corrections there.
   Still unnamed inside U2's scope: the aux channel's semantic, blk48's
   render binding, n44 bodies, the n3C tag enum.
2. ~~**Flag bits 1 and 2**~~ **ANSWERED by U2**: the parser ORs them into
   one runtime bit (`m_skeletonFlags & 1`, four consumers: rate fallback +
   root-node bookkeeping), so they are indistinguishable downstream —
   which is WHY no corpus correlate exists. What distinguishes them in
   the header remains unknowable from retail data
   ([../anim/FINDINGS.md](../anim/FINDINGS.md) §4).
3. ~~**The object identity** — m_skel vs m_geom (§3.2)~~ **ANSWERED by U3,
   2026-08-16** ([../mdlrefs/FINDINGS.md](../mdlrefs/FINDINGS.md) §5,
   review-confirmed): TWO objects of two MdlBuild classes (0x15C geometry /
   0x11C skeleton, distinct vtables and deleting destructors, one
   kind-keyed cache at `0xF26F10`); the dual +0xA4 writers target
   different fields of different classes sharing only a displacement —
   §3.2's tension was the one-object assumption. B's constructor pre-fills
   the three n14 vec3 slots at +0x48 (defaults the records overwrite).
4. ~~**MdlAnim:367's actual array**~~ **SETTLED by U2**: the assert lives
   in the shared channel-time lookup helpers and reads the payload
   channels' stride-4 int32 time prefixes, not the n3C table — the 10
   duplicate-time files trip nothing (the binary search never lands the
   asserted pair on a duplicate). The 23-byte record's +0x05/+0x09 ARE
   start/end — but TIMES on the global track clock (MdlSeq `0x00792F56`
   clamp), not frame indices; four fields stay unnamed
   ([../anim/FINDINGS.md](../anim/FINDINGS.md) §2.7, §3.5).
5. **n56's writer** — fires on 0/14,571; only a tool/build that emits it can
   test the stride.
6. ~~**The second FA1 consumer**~~ **NAMED by U2**: `MdlBloat` — the
   by-id/by-path "anim file" loader for the MdlDecomp export side
   (its own error strings name it), neither a validator nor a rewrite
   path; "anim file" is ArenaNet's word for the FA1-only class
   ([../anim/FINDINGS.md](../anim/FINDINGS.md) §5).
7. ~~**The mid/tail chain chunk families**~~ **CLASSIFIED by U3, 2026-08-16**
   ([../mdlrefs/FINDINGS.md](../mdlrefs/FINDINGS.md) §6, review-confirmed):
   tails = the model's collision/visibility payload consumed at runtime by
   MdlApi (callers PrCollision/ZnDef/Sight/MdlTex); mids = MdlDecomp's
   decompile-side 1:1 mirror of the model's own chunk ids — and the
   skeleton/emitter/sound-metadata hypothesis above is accordingly
   REFUTED. The 0xBBE↔0xFA9 pairing predicted chunk FA9 from the code
   side before the corpus produced its 2 carriers. FAE's population is
   exactly 6 (not ≈8) — a linked-model list whose targets all carry
   geometry, the inverse of FA8. Chunk CONTENTS beyond 0xFAC's manifest,
   and the type-8 chunk-0x2 tag stream, stay open (mdlrefs §8).
8. **The FA1-only class** — ~~coverage unmeasured~~ **MEASURED by U3,
   2026-08-16**: exactly 311 heads, of which **284 (91.3%) are FA8
   targets** ([../mdlrefs/FINDINGS.md](../mdlrefs/FINDINGS.md) §7; the 27
   uncovered rows are listed in the sweep artifacts). Still open: how the
   27 are reached, and why FA8 lists duplicate a linked file's own list
   when the loader resolves recursively anyway.
9. **Block-level leftovers**: block E (11.1%, unnamed), block F record fields,
   block J region-3 records, geom+0x5C's name, `vo` types 1 (n=5) and 5
   (n=0), the 67% empty block-I records, `0x00782349`'s `1 << n`.
10. **Wire leftovers**: 0x015E's "fileId"; the henchman capture gap;
    definitions 396/8077 (declared, never instantiated; 8077 duplicates
    1505's payload under a fresh index).
11. **Amet.cpp** (3 generic asserts, unidentified), CpsTex:597's switch on
    `""`, MdlPreload's zero asserts.
12. **Housekeeping owed to other docs**: `studies/models/PLAN.md` M6b should
    be marked resolved (flags-2817); `modelfile.py`'s A/H/I/J docstrings can
    carry the names from §4 (with the client-gate caveat on J and the error-
    0x1D refusal on H); the H-term synthetic fixture; `studies/smsg` §0x0057's
    open question is answered by §5.4.

**Session artifacts are preserved**: the verified FA1 walker
(`verify/fa1walk.py`), the census scripts/JSONL (`census/`), the sabotage
runs, and the per-TU assert sweeps were copied out of the session scratchpad
to `vault/research/unitmodels/2026-08-16-recon/` (225 files). **U1 landed
the same day**: `toolkit/mapdata/skelfile.py` is the committed decoder,
`test_skelfile.py` pins the full-population closure, and the research walker
is now the reference the committed code was reviewed against, not the only
implementation.

---

## 7. Provenance

Every measurement in this document is from the owner's own build-38797 image
(`vault/client/2026-07-29_221c13772c7a/Gw.exe`) and the owner's own archive
(`vault/dat_study/Gw.dat`), via extractors in this repo (`toolkit/clientscan/
asserts.py`, `codescan.py`, `srctree.py`; `toolkit/mapdata/archive.py`,
`modelfile.py`, `mapchunks.py`, `soundchunk.py`, `atex.py`; `toolkit/authsrv/
tape.py` + the schema codec for wire evidence) plus session scratch walkers
that reuse them. No client was launched; nothing was written into `vault/`
outside the established read paths; wire evidence is from the authorized live
captures and pooled captures were never mixed across origins.

Per the 2026-08-12 ruling (`PLAN.md` §7 Q3, refined): offsets, strides,
counts, ids, VAs and layouts here are MEASUREMENT and appear in bulk; assert
expressions are quoted **singly**, each as the evidence for a specific claim
with its file:line; there is no bulk dump of the assert corpus. No asset
bytes are reproduced — the MPEG identification in §5.2 rests on frame-header
field validity counts, not on copied audio; anchor "headers" are printed as
offsets and counts only. Names are committed as ids; nothing here embeds
ArenaNet's authored text or expression.

Second gate: this arc took nothing from upstream — every layout was derived
from the client and the archive, and the one external convergence cited
(§5.2) is this repo's own `soundchunk.py`. No new §6.1 derivation-register
row is required by this document. Decoded *output* (meshes, sounds, any
export) remains ArenaNet's expression and goes to `vault/exports/` only,
under the `resolve_outdir` refusal — the rule the U-ladder's export rungs
inherit from birth.