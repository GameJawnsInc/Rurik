# The animation payloads, named — rung U2 of the unit-model arc

Build 38797, read from the vaulted stock `Gw.exe`
(`vault/client/2026-07-29_221c13772c7a/Gw.exe`, the pinned pristine client)
and the owner's study archive (`vault/dat_study/Gw.dat`), via
`toolkit/clientscan/codescan.py`, `asserts.py`, and scratch measurement
scripts whose disassembly dumps and result JSONs are preserved under
`vault/research/anim/`. No client was launched. Labels are the project
vocabulary ([../character/FINDINGS.md](../character/FINDINGS.md)); the
evidence base this rung starts from is
[../unitmodels/FINDINGS.md](../unitmodels/FINDINGS.md) (cited below as
UM §n), and the rung's contract is `studies/unitmodels/PLAN.md` §2 U2.

**Method note.** Every consumer below was read from the pinned binary; every
layout claim then earned (or failed) a corpus prediction stated before the
run, with a control that can fail. The corpus runs cover the complete
flags=515 population — the same 14,571-chunk population U1's decoder closes
byte-exact. Failed predictions are kept visible in §6.

---

## 1. The answer in one page

**The two big animation payloads are decoded.** The recon's "16/20-byte
group" framing was the wrong overlay: inside each record's variable payload
the client reads **times-prefix structure-of-arrays channels** — `N` int32
key times (units of 1e-5 s, the global animation clock) followed by `N`
values — and samples them by binary search + interpolation. The same SoA
pattern turned out to govern four more structures nobody had framed that
way: the n40 sound-event table, the n3E event track, blk48's sections, and
FA0's block-B light tracks.

| structure | what it is | evidence |
|---|---|---|
| **blk2C** | one record per **animated node** (`anim` is ArenaNet's word): `{f32 base[3]; u32 flags}` + payload `{u16 w0,w2,w4}`, then **w0 translation keys** (times + vec3, lerp, applied as base+delta), **w2 rotation keys** (times + float4 **quaternions**, shortest-path nlerp), **w4 keys** (times + vec3, second applier — scale-like, name UNVERIFIED) | §2.1–2.3, §3 |
| **blk48** | a second track list applied to Gr channel-set 3 (blk2C uses set 2): `{f32 base[3]; u32 flags; u32 u10}` + payload `{u16 w0,w2}`, both sections times + vec3; flag bit 27 = **looping** (time = global clock mod last key), bit 29 = constant mode | §2.4 |
| **n40** | the **sound-cue event table**, itself SoA: n40 sorted u32 sequence indices, then n40 18-byte bodies `{i32 time; u32 pathIndex; …}`; `pathIndex` is bounds-checked by MdlAnim:2040 against `m_soundPathCount` and indexes the **FA6 array** — the FA6 ⟺ m_soundPaths join is now confirmed at the consumer, end to end | §2.6 |
| **n3E** | a **timed event track**: arrA = int32 event times (binary-searched), arrB = `{u32 type; u32 param}`; type 0 resolves `param` through the **FAE array** (m_skel+0xA0) to a model file reference and loads it — FAE is n3E's file table | §2.5 |
| **seq record** | disk `u32@+0x05` / `u32@+0x09` are the sequence's **start/end times** (1e-5 s, the key-time clock): the play call adds its float offset ×1e5 to start and clamps to end (`MdlSeq 0x00792F56`) | §2.7 |
| **n34** | per-**emitter attachment** records (24 B, vec3 at +4): blk2C flag bits 8–12 say how many of them bind to each node, distributing block J's emitters over the animated nodes — the MdlAnim:1121/1122 asserts require the counts to exhaust exactly | §2.2, §3 |

**MdlAnim:367's array is settled** (UM §6.4): the assert lives in the shared
key-lookup helpers `0x0077EC70`/`0x0077ED30`, which read exactly these
stride-4 int32 channel time prefixes — **not** the n3C key table (8-byte
`{tag, f32 s}` records in memory). The 10 duplicate-time corpus files
violate nothing the client asserts: their duplicates are in n3C spans,
which no `keyTimes[lo+1]>keyTimes[lo]` ever sees.

**The header flag bits 1/2 have a consumer-side answer** (UM §6.2): the
parser ORs them into ONE runtime bit — `m_skeletonFlags & 1` — so the two
bits are indistinguishable downstream, which is why no corpus correlate
exists. Its four consumers gate an animation-rate path (zero rate falls
back to header f20 → m_skel+0x100) and root-node (+0x58) bookkeeping. §4.

**The second FA1 consumer is `MdlBloat`** (UM §6.6): its error strings name
it — `MdlBloat: unable to find anim file 0x%x` — a by-id/by-path **anim
file** loader whose walker re-locates the FA1 blocks for the
MdlDecomp/export side. "Anim file" is ArenaNet's name for the FA1-only
class (UM §2.3, ≈312 files — the FA8 link-target population). §5.

## 2. The consumers, function by function

All VAs build 38797. Disassembly dumps: `vault/research/anim/dis_*.txt`.

### 2.0 The shifted skeleton view, and why earlier scans found nothing

MdlAnim does not read `m_skel` fields at the loader object's displacements.
The per-frame functions compute **S = B + 0x38** (B = the loader/model
object) and carry S (`0x0077FEA4`, `0x00780090`: `lea eax,[ebx+0x38]` with
a null guard) — so blk2C sits at `[S+0x7C]`, blk48 at `[S+0x8C]`, the n3E
arrays at `[S+0x58/0x5C/0x60]`, n2C at `[S+0x74]`. A `--field 0xB4` scan
over MdlAnim finds zero hits for exactly this reason. The FA8 link array is
read B-relative at `[B+0x114]` in the same functions, pinning B's identity.
SOURCE-CODE.

### 2.1 The sampling core: 0x0077EC70 / 0x0077ED30, and the samplers

* `0x0077EC70` — `f(int32* keyTimes, int keyCount, int time, int* outIdx)
  -> float frac`. Asserts `keyCount >= 2` (MdlAnim:328) and
  `keyTimes[lo+1]>keyTimes[lo]` (MdlAnim:367). Clamps below the first key
  (returns 0.0, idx 0) and above the last (returns 1.0, idx count−2), else
  binary-searches and returns `(t − k[i]) / (k[i+1] − k[i])`. **12 call
  sites, all in MdlAnim.**
* `0x0077ED30` — the index-only variant (assert `keyCount >= 2`,
  MdlAnim:294). 2 call sites.
* `0x00782910` — the **vec3 channel sampler**: `(base, count, time, out)`.
  Calls `0x0077EC70(base, count, time, …)` — **the first `count` int32s of
  a section ARE the key times** — then lerps the two 12-byte vec3 values at
  `base + 4·count + 12·idx`. This is the instruction-level refutation of
  the AoS "16-byte group" framing: same byte count, different shape.
* `0x00782990` — the **rotation channel sampler**: times prefix, then
  16-byte float4 values at `base + 4·count + 16·idx`; the two values go to
  `0x00783D70`, which computes the 4-component dot, flips the second
  quaternion's weight when dot < 0 (constants: threshold 0.0 at
  `0x0093C1B0`, −1.0 at `0x0093CF24`), and blends — **shortest-path
  quaternion nlerp**. **And it renormalizes — found by the review, and it
  is this section's strongest instruction-level evidence: after the blend
  the function computes the result's squared 4-length and takes a
  first-order fast normalization (`(3−len²)/2`, constant 3.0 at
  `0x00948610`) gated on `len² ∈ [0.9, 1.1]` (`0x00948564`/`0x009485E8`)
  — a fast path only correct when the INPUTS are unit, assumed by the
  code before any corpus is consulted.** Quaternion-specific math; a
  plain vec4 lerp has no shortest-path branch. `0x00783F10` then composes quaternion + position
  into the 3×4 transform handed to Gr (`0x00671FF0(slot, row0, row1,
  row2)`).

### 2.2 The per-node loop: 0x00780060 (assert `skel1&&skel2`, MdlAnim:1031)

The per-frame apply. Resolves skel1/skel2 (each optionally re-targeted
through the FA8 link array `[B+0x114]`), then loops `i` over `[B+0xAC]`
(= n2C, the asserted `animCount`) pairing **skel1's and skel2's i-th blk2C
record**:

* `rec = [S+0x7C] + 0x14·i` — the in-memory record is the disk 16 bytes
  verbatim + a pointer (+0x10) to that record's payload (helper
  `0x00796AD0` copies the whole variable region after the record array and
  wires per-record pointers — `dis_00796AD0_blk2C.txt`).
* Three sampling paths: cached-cursor (`0x00783870`), time==0
  (`0x00781B20`), and transition blend (`0x0077F9F0`, which samples BOTH
  records' channels and combines `base1 + (1−w)·s1 + w·s2`).
* `0x00781B20` is the cleanest witness for the record itself: sample w0
  section → **add the record's three base floats** → position; sample w2
  section → nlerp → compose with position; w4 section → sampler `0x782910`
  again but applied via `0x006747A0` (the applier blk48's second channel
  and the bit-29 constant path also use). The record's first 12 bytes are
  a **base translation vec3**; +0x0C is a **flag dword**:

| blk2C flags | consumer | meaning |
|---|---|---|
| bits 0–7 | `0x00780150`: `movzx` byte → `0x006737C0(2, byte)` per node | **the node's LINK** (parent/attach reference): always < n2C, always ≤ own index — 121,532/121,532 each, §3.4; the byte selects a GrTrans stream-2 slot before the node's channels apply |
| bits 8–12 | `0x0078020F`: `(flags & 0x1F00) >> 8` → `0x00783510` | **emitter-attach count**: consumes that many n34 records (24 B, vec3 at +4, indexed by a running counter that also indexes the 36-byte runtime emitter slots at CTX+0xA0), wiring block-J emitters to this node's transform. After the loop the client asserts the counters exhausted exactly: `emitterIndex == m_geom->m_emitterCount` (MdlAnim:1121), `streakEmitterIndex == m_geom->m_streakCount` (:1122) |
| bit 26 | `0x007801C1` | **node carries the next light**: consumes one 28-byte block-A light record (`[geom+0x4C]`, stride 0x1C) and one light handle (CTX+0x84); the record's first byte picks one of two Gr attach calls (`0x0067B830`/`0x0067B740`). MdlAnim:1954's `anim->lightId` names the record family |
| bit 28 | `0x00780275` | skip the node's Gr commit (`0x00669CA0`) |
| bits 30/31 | `0x00781BEE` | apply a **mirror transform** from a global 0x6C-stride table (`0x00BF7B88`), bit 31 selecting which half |

* The record's three base floats are also consumed as consecutive
  differences (`0 − a, a − b, b − c`) at `0x00780228` on one path —
  observed, not explained.

### 2.3 What this makes blk2C

One record per **articulated node**, each carrying its LINK to an
earlier node (flags bits 0–7, §3.4) — the rigid-segment hierarchy
FINDINGS UM §3.10 predicted from the assert vocabulary, now measured in
the data; per node a translation channel,
a rotation channel (quaternions, uncompressed float4), and a third vec3
channel. n2C = node count — which is why the degenerate prop skeleton is
`n2C == 1` (one static node) and why `n2C == 0` is the client's hard
reject. The refuted "unit quaternions in the 16-byte groups" (UM §3.4) was
measuring AoS 16-byte windows across what is actually times-then-values —
§3's re-test against the true layout is the corrected measurement, with
the old overlay re-run alongside as the control.

### 2.4 blk48: 0x0078032A (second half of the same function)

Loops `[B+0xC0]` (n48) records at `[B+0xC4]`, in-memory stride 0x18 (disk
20 bytes verbatim + payload pointer at +0x14, helper `0x00796970`).
Sub-header is **4 bytes `{w0, w2}`**; both sections are times + 12-byte
vec3 values, sampled by the same `0x00782910`. Differences from blk2C:

* Applied to Gr channel-set **3** (`0x00780347 push 3`) where blk2C used
  set 2; section 1 lands via `0x00674FE0`, section 2 via `0x006747A0`.
* flags bit 27 (`0x0078035F`): **looping** — the record's own period is
  read from its LAST key times (`times0[w0−1]`, `times1[w2−1]`, max) and
  the sample time is `globalClock % period` (`0x007803A3`, clock at
  `0x00F26BB8`, advanced by `dt × 1e5` — `0x00782A00`, constant at
  `0x00A77DB0`).
* flags bit 29 (`0x00780471`): constant mode — applies fixed vectors
  `{0.5, 0.5, 0}` / `{0.5, −0.5, 1.0}` (constants `0x009458BC`,
  `0x0093CF20`) through the same two appliers.
* The disk record's `u32@+0x10` is not read on this path — unnamed.

RECONSTRUCTION, stated as such: the 0.5-centered constants, the two-channel
translate+scale shape, the looping flag and the separate Gr channel-set
smell like **texture-coordinate animation** (UV scroll/scale tracks); no
instruction read here proves the render-side binding, so blk48's records
are labeled "channel-set-3 tracks" and nothing stronger.

### 2.5 n3E + FAE: 0x0077FE70

Walks `[S+0x58/0x5C/0x60]` = n3E count / arrA / arrB. arrA is int32 event
times (searched by `0x0077ED30`); for events in the frame's time window,
arrB's 8-byte record `{u32 type; u32 param}` is dispatched: **type 0**
reads `[B+0xA0]` — the **FAE array** — at `param`, resolves the reference
against the model's own path (`0x00470300` etc.) and requests a `' mdl'`
resource (`0x0046FE40`). So n3E is a timed event track and FAE is its
model-file table (UM §5.3's "contents NOT FOUND" for FAE is closed to
this extent). Non-zero types bail out of this function — other consumers
not located. SOURCE-CODE for type 0; the corpus fires n3E on 6 files (§3).

### 2.6 n40: 0x00780C70 (asserts MdlAnim:2040)

The sound-cue event scanner. Reads `[B+0x74]` (n40) and `[B+0x7C]` (the
n40n44 blob), and frames the n40 region as **SoA**: the first n40 u32s are
a SORTED array of sequence indices (the function lower-bounds it against
the current sequence index — `0x00780CE0`), followed by n40 **18-byte
bodies**. Body `+0x00` is an int32 event time — SEQUENCE-RELATIVE, per
§3.6's measurement (99.6% within [0, end−start], absolute refuted) —
checked against the frame's window; body `+0x04` is `pathIndex`, asserted
`pathIndex < m_skel->m_soundPathCount` (MdlAnim:2040, `[B+0x80]`) and used
to index `[B+0x84]` — **the parsed FA6 array**. The chain UM §5.2 asked
U2/U3 to confirm is compiled fact: FA6 record → `m_soundPaths[pathIndex]`
→ path resolution → sound. (The n40 "elem 0x16" of the parser is therefore
4 index bytes + 18 body bytes per record, not a 22-byte record shape.)
The n44 12-byte tail records' consumer was NOT located in this pass.

### 2.7 The sequence record: 0x00792EB4–0x00792F9C (MdlSeq)

The play-sequence call converts its float args (seconds) ×1e5 to the int
clock (asserts name them: `blendTime`, `rampInTime`, `rampOutTime`,
`blendRatio` — MdlSeq:293/749), asserts `seqIndex < m_skel->m_seqCount`
(MdlSeq:300), fetches the 32-byte in-memory record, and at `0x00792F56`
computes `current = clamp(offset×1e5 + rec[+0x08], …, rec[+0x0C])` — i.e.
in-memory +0x08/+0x0C (disk `u32@+0x05` / `u32@+0x09`) are the sequence's
**start and end times** on the same 1e-5-s clock as every key above.
UM §6.4's "frame range, UNVERIFIED" is now a measured time range (§3).
The record field at in-memory +0x00 (disk `u32@+0x01`) is passed to
attached child emitter models when the sequence starts
(`0x00793540 → 0x00792CA0`) — id-like, still unnamed. Disk `u8@+0x00`,
`u32@+0x0F`, `f32@+0x13` remain unnamed (f32 explored in §3).

In-memory record map (built at `0x007965A0–0x007965DD`), for reference:
`+0x00←u32@1, +0x04←u8@0, +0x08←u32@5 (start), +0x0C←u32@9 (end),
+0x10←f32@0x13, +0x14←u32@0xF, +0x18 = hi−lo (span key count),
+0x1C = &keys[lo]` — and the in-memory KEY records at B+0x8C are 8-byte
`{u32 tag; f32 seconds}` (tag FIRST; the disk SoA is converted at
`0x00796540–0x0079656C` multiplying by the 1e-5 constant `0x00A571B0`).

### 2.8 Bonus, recorded for the models arc: FA0 block B = light tracks

`0x007809D0` (asserts MdlAnim:1954/1956) iterates `[geom+0x50]` records
via the pointer array `[geom+0x54]` — the FA0 preamble **block B** (9
files archive-wide, unnamed until now): `{u32 lightId (1-based, indexes
block A); …; u32 count1; u32 count2}` with payload from +0x18: count1
int32 times + count1 **3-byte RGB** values (byte-lerped per channel), then
a count2 second channel. Light **color animation** tracks. Not corpus-run
here (9 files; the models arc owns FA0).

## 3. The corpus verdict — predictions stated first, then the run

Every run covers the complete flags=515 population (21,421 head rows,
14,571 FA1 chunks — the U1 population exactly; the one non-ffna anomaly
row 8316 excluded as always). Scripts and raw JSON in
`vault/research/anim/` (`animcorpus.py`/`corpus_blk2c48.json`,
`seqcorpus.py`/`corpus_seqrec.json`, `strictcheck.py`, `n40corpus.py`,
`parentcorpus.py` and their JSONs); each script's docstring states its
predictions, written before it ran. Population: 121,532 blk2C records
(nodes), 1,794 blk48 records, 70,474 sequence records.

### 3.1 The channel layout — CONFIRMED, with the old refutation explained

| prediction | result |
|---|---|
| P4 **quaternions**: the w2 sections' float4 values (at section+4·N, per the SoA layout) are unit-norm within 1% | **16,263,916 / 16,263,916 — 100.000%** (norm histogram entirely within [0.5,1.5) about 1.0) |
| P4 **control**: the 2026-08-16 AoS overlay re-run as recorded | 6 / 19,460 within 1e-3 — reproduces the study's 4/19,460: the refutation was true of the WRONG OVERLAY. *Review correction (R-2): as first run, the control got a 10× tighter tolerance than the claim (1e-3 vs 1%) and a head-of-corpus 19,460-value cap — a control given a harder test than its hypothesis. The review re-ran BOTH overlays at the SAME 1% on its own stride-15 sample: SoA 963,066/963,066 (100.000% — and 100.000% at 0.1%, so the tolerance is not load-bearing), AoS 478/159,838 (0.30%), null control 153/119,006 (0.13%). The separation stands with the asymmetry removed* |
| P1 **no consumed channel has exactly 1 key** (the sampler asserts `keyCount >= 2` and is called whenever a section is non-empty) | **0 violations over 102,727 sections** (21,750 w0 + 70,007 w2 + 9,176 w4 + 1,761 + 33 blk48) |
| P5 vec3/float4 values all finite | 0 non-finite anywhere |
| P3 times sane | 0 negative; max 29,600,003 = 296.0 s (both blk2C and blk48 share the ceiling — one global track timeline) |
| P2 times **strictly** increasing per section | **FAILED as stated**: 628/21,750 w0, 757/70,007 w2, 10/9,176 w4, 2/1,761 blk48 sections violate strictness — see §3.2 |

### 3.2 Strictness vs. duplicates — the prediction that failed, resolved

The strict form of P2 was wrong. A follow-up pass (`strictcheck.py`,
prediction stated before the run) split the violations: of 102,727
sections, **1,397 carry exact duplicate times and 0 — zero — carry a
decrease**. MdlAnim:367 survives retail data
carrying duplicates because the binary search's `<=` branch lands `lo`
on the LAST duplicate — the asserted pair `keyTimes[lo+1] > keyTimes[lo]`
is never itself a duplicate pair for any query time. The writer-side rule
U6 inherits is therefore NON-DECREASING, same as the n3C table.

### 3.3 The cross-block invariants — the names' load-bearing evidence

| prediction | result |
|---|---|
| P-N34: Σ over a file's blk2C records of `(flags>>8)&0x1F` == n34 | **14,571 / 14,571** — the emitter-attach reading, unforceable by the decoder |
| P-LIGHT: Σ of flag bit 26 == the FA0's block-A light count (u8@0x30), 0 where block A absent | **13,812 / 13,812** measurable files, 0 violations (759 COMPOSITED shells unmeasurable — their m_geom is the wire-linked body). *Review reweighting (R-1): block A exists on 26 files, so ~99.8% of the figure is `0 == 0` — the INFORMATIVE population is 26 files / 36 bit-26 records, and the identity's weight is what those carry. The headline number stays (it is what was measured) but its evidentiary weight is the 26* |
| P-EMIT (exploratory): n34 == the FA0's block-J emitter count | 12,264 / 13,812 (88.8%); the 1,548 disagreements all sampled n34 > emitters — n34 also covers attachments beyond block-J emitters (the 0x783510 dispatch's other arms; recorded, not named) |
| blk2C flag-bit census (121,532 records) | bits 0–6: 57,834/36,854/28,737/26,743/25,644/20,860/12,554 · bit 7 and 13–25: **0** · bits 8–12 (emitter counts): 11,073/2,509/717/257/58 · bit 26: **36** (block A is on 26 files) · bit 28: 69,565 (57% of nodes skip the Gr commit) · bits 30/31: 4,027/3,128 |
| blk48 flag census (1,794 records) | **only bit 27 ever set** — 1,300/1,794 looping; `u10` values are hash-like (no small-int structure) |

### 3.4 The node-link byte (blk2C flags bits 0–7)

The low byte's corpus shape (109 distinct values, 0–108, dense — which
is also WHY bit 7 is never set) and the anchors' arrays
(116228: `0,1,2,3,3,3,6,7,6,9,10,6,12,3,14,15,14,…` — each record naming
an earlier one) read as the **skeleton hierarchy link**. Predictions
(P-LINK1: byte < n2C everywhere; P-LINK2: byte ≤ own index — topological
order; discriminator: the (i − b) delta distribution concentrates near
small values if it is a hierarchy, spreads if the bytes are merely
small): **both hold at 121,532 / 121,532 — zero violations** —
self-reference on 56,160 records (every record 0 among them: 14,571
root_zero), and the non-self deltas run 1: 5,608 · 2: 4,339 · 3: 3,660 ·
4: 3,295 … with a 10+ tail of 23,543. *Review correction (R-4): that tail
is 47% of the non-self non-zero deltas — the histogram does NOT cleanly
match the "concentrates low" discriminator this section stated for
itself, and the first draft read it as passing anyway. What carries the
LINK name is the topological bound plus the consumer: `<= own index` is
the discriminating half (the review's shuffled-links control violates it
on 22.6% of records, while `< n2C` survives any shuffle — a multiset
property), and the byte feeds `0x006737C0` per node. The delta histogram
is demoted to color.* **The byte is the node's LINK
(parent/attach reference in topological order)**; whether self-reference
means "root/own transform" is the remaining UNVERIFIED convention.
Consumer side: the byte goes to
`0x006737C0(2, byte)` per node before the node's channels are applied —
GrTrans state selection (`GrTrans.cpp:1622` asserts
`transform < GR_TRANSFORMS`, 5 streams of 0x1400 bytes at `0x00C120C0`)
— so "channel-set" 2/3 in §2 are **GrTrans transform streams**, and the
byte selects a slot within stream 2's state.

### 3.5 The sequence record — one prediction confirmed structurally, one refuted

| prediction | result |
|---|---|
| P-SEQ1: `u32@+0x05 == keyTimesRaw[lo]` on spans with hi > lo | **REFUTED: 181 / 21,535** |
| P-SEQ2: `u32@+0x09 == keyTimesRaw[hi−1]` | **REFUTED: 1 / 21,534** |
| off-by-one rivals (`keys[lo+1]`, `keys[hi]`) | 15 and 12 of 9,321 — no off-by-one rescue; the binding idea is dead |

What the refutation revealed instead (sampled, MEASURED on the failure
records): per file the [start, end] windows are consecutive,
**mostly** non-overlapping ranges on a global timeline (row 291:
2.03–2.17 s, 2.87–3.63 s, 3.67–4.43 s, 4.47–5.23 s, 5.67–6.30 s…) — the
review put a rate on the word this section first stated bare: **9 of 152
multi-window files (5.9%) carry at least one overlapping pair** at its
stride-15 sample, so "non-overlapping" is a ~94% regularity, not a law —
the same timeline
the channel times live on (max 296 s) — while the n3C span key times are
small per-sequence-local values (which is exactly UM §3.7b's
"local-vs-global" shape). So a SEQUENCE is a window of the global track
timeline; its n3C span is a local tag/event track. The n40 run's
absolute-window test (§3.6) checks this reading from a third direction.
Exploratory fields: `f32@+0x13` is 0.0 on 20,420/21,535 spans and never
the span duration (0/21,535); its non-zero values (288.0, 144.0, 370.0,
−95.0 …) are speed-like — UNVERIFIED. `u8@+0x00` is a small enum
(0: 38,774 · 1: 7,123 · 2: 6,945 · 8: 2,563 …). `u32@+0x01` is 0 or
hash-like (top value on 9,835 records) — consistent with the
child-model sequence matching at `0x00793540` but unproven.
`u32@+0x0F` is 0 on 68,139/70,474; its non-zero values are times.

### 3.6 n40 sound events and n3E

Population: 3,415 files with n40 > 0, 12,423 events.

| prediction | result |
|---|---|
| P-N40A: the seq-index prefix is sorted (the client binary-searches it) | **3,415 / 3,415 files** |
| P-N40A': every index < the local n18 | 2,823 / 3,415 — **592 files carry indices ≥ m_seqCount**. Not a layout failure: the consumer resolves its current-sequence selector through the FA8 link array (`0x0078007F`), so a shell's events can be keyed by a linked model's larger sequence space. RECONSTRUCTION for the excess; the worm anchor (all in-bounds) is pinned in the test |
| P-N40B: every `pathIndex` < the container's FA6 record count | **12,423 / 12,423**, and n40 > 0 ⇒ FA6 present on **3,415 / 3,415** — the FA6 ⟺ m_soundPaths join, corpus-proven on top of the compiled chain. *Review BUG B-1, recorded: `n40corpus.py`'s `pathname_count` walked FA6/FAE as u16-terminated groups from offset 0 — but these chunks are `u32 count` + 6-byte records, so it returned count+1 everywhere and this row was checked against a bound ONE LOOSER than the client's. The review re-checked with the true count: **740/740 in bounds on its sample** — the conclusion survives and TIGHTENS* |
| P-N40C: event times — absolute vs relative reading, both measured | absolute (start ≤ t ≤ end) **FAILS**: 2,879 / 11,632. Relative wins: 11,588 / 11,632 (99.6%) — but *review correction (R-3): the claim is DOWNGRADED to PLAUSIBLE/RECONSTRUCTION.* The review's null control — pairing each event with a random OTHER sequence in the same file — already scores **82.8%** (44% of events have `time == 0`, which any non-negative duration passes), so relative-beats-absolute is decisive (25.4% for absolute) while relative-beats-null is modest. And the 99.6% denominator excludes the 791 events (6.4%) of P-N40A′'s out-of-range files — over ALL events it is 11,588/12,423 = 93.3%. The decisive unread evidence: what the caller feeds `[ebp+8]`/`[ebp+0xC]` at `0x00780C70` — neither this study nor the review traced it |
| body tail | `u16@+0x08` is a sparse high-bit flag word (0: 11,950 · 0x8000: 401 · 0x4000: 50 · 0xC000: 16); the last 8 bytes are non-zero on 3,379/12,423 — carried raw |

**n3E / FAE** (6 firing files): every arrA sorted; every arrB record is
**type 0**; every `param` < the container's FAE record count, FAE present
on all 6 — P-N3E holds entirely (rows 18731, 136755, 150245, 150389,
151054, 155178). *Review BUG B-1: this paragraph's first draft printed
FAE counts 7/6/2/7/4/… — those were `pathname_count`'s count+1 phantoms;
the TRUE counts are **6/5/1/6/3/1**, and with them the fit is exact:
max `param` == count − 1 on all six files — tighter evidence than the
loose bound gave.* Non-zero n3E types exist in the
code path but not in this archive — a floor, not a census.

## 4. Flag bits 1 and 2: the consumer-side meaning (UM §6.2)

The parser's tail (`0x00796857–0x00796902`, `dis_00796310_fa1parser.txt`):

* header bit 0 → `m_skeletonFlags |= 4` (COMPOSITED — known, UM §3.8);
* **header bits 1|2 → `m_skeletonFlags |= 1`** — one `test byte [ebx+8],6`,
  one OR: the two header bits are **indistinguishable at runtime**, which
  is consistent with (and explains) their having no corpus correlate —
  no downstream behavior can separate them;
* `m_skeletonFlags |= 2` unconditionally, then CLEARED (`0x007968FF`) iff
  the skeleton is degenerate: `m_seqCount==1 && n38==0 && n2C==1 &&
  blk2C rec 0 has w0==w2==w4==0 && i30>=0 && n50==0 && n48==0`. Bit 1 =
  **"this skeleton animates"**.

Consumers of `m_skeletonFlags & 1` (the bits-1|2 image), all four sites:

| site | module | gated behavior |
|---|---|---|
| `0x007786A6` | MdlApi | animation-rate path: a rate argument of 0.0 falls back to `[B+0x100]` (header f20); result stored as `rate·abs(rate)` on the instance |
| `0x0077973D` | MdlBuild | registration that reads sequence[0]'s in-memory +0x08 (start time) — gated `!(argflag&2) && bit0` |
| `0x0077D384` | MdlBuild | Gr channel-2 reset committing node `[B+0x58]` and node 0 |
| `0x007A2E7C` | MdlCombine (the review placed it via `asserts.py --at`; the first draft said "decomp zone") | **writer**: `if bit0: [B+0x58] = computed value` |

`[B+0x100]`'s fallback when header f20 == 0.0 (`0x007A6D10`, called from
the parser at `0x00796889`): `clamp(max(2·[B+0x48], [B+0x4C]) × 5.2083 /
0.76733, 3000, 16000)` — i.e. derived from the **n14 slot-0 vec3** (which
the parser defaults to `{36, 72, 0}` from `0x00955828`/`0x00A77AC4` — a
radius/height-shaped pair). RECONSTRUCTION: f20 is a default
animation-rate/speed scalar and n14 slot 0 is a body-size vec3; neither
name is asserted by the client, so both stay UNVERIFIED as names, with the
arithmetic recorded. Consumers of `m_skeletonFlags & 2`: `0x0077BA45/4B`
(MdlBuild) — either skeleton's bit feeds the instance's ANIMATED flag
(0x40000 on the Gr instance word), alongside lights/n48/n50 presence.

**What bits 1/2 MEAN in the header remains open**: the parser collapses
them; every consumer behavior above is the collapsed bit. A tool that
wrote the two bits differently could distinguish them; retail data cannot.

## 5. MdlBloat, the second consumer (UM §6.6)

`0x0079E860` (single caller `0x0079DA77`, inside the MdlDecomp:2700
`!PathIsRelative(modelFileName)` export entry): resolves an **anim file**
by path or numeric id — error strings `MdlBloat: unable to find anim file
0x%x` / `%S` / `unable to lock file %x` (`0x00A79AD0/AF8/B20`) — locks it,
`GetChunk(0xFA1)` (`0x0079E9E2`), and calls the walker `0x0079E420` to
re-locate block pointers for the export side. It is neither a validator
nor a rewrite path: it is the **loose/by-id anim-file loader for
MdlDecomp**, and "anim file" names the FA1-only archive class (UM §2.3).
Relevant to U7 only insofar as it confirms the export tooling consumed the
same layout the runtime does.

## 6. What stays unnamed, refuted, or open

* **REFUTED and corrected**: "blk2C payloads are (w0+w4) 16-byte groups +
  w2 20-byte groups" as a record shape — the strides are byte-identical
  but the shape is times-prefix SoA per section. The 2026-08-16 quaternion
  refutation (4/19,460 unit norms) was true OF THAT OVERLAY and is
  reproduced here as the control; the corrected layout's w2 values are
  quaternions (§3).
* The **w4 section's semantic** ("scale") — applier identity + constants
  are suggestive; no instruction proves scale. Stays `aux vec3 channel`.
* **blk48's binding** (texture-coordinate hypothesis) — RECONSTRUCTION,
  §2.4; the Gr side (`0x00674FE0`/`0x006747A0`/channel-set ids) was not
  disassembled.
* blk2C's base-vec3 difference path at `0x00780228`, bit 28's precise
  effect, the mirror table's population, and whether a link byte's
  SELF-reference means root/own-transform (the bound and topological
  order are measured; the convention is not).
* **n44 bodies** (12 B) — consumer not located this pass; n40's bodies'
  last 8–10 bytes (§3 histograms); blk48 record `u32@+0x10`.
* Sequence record `u8@+0x00`, `u32@+0x01` (child-start id-like),
  `u32@+0x0F`, `f32@+0x13` (§3 exploratory only).
* **n3C key TAGS** `{1,2,6,19,20,21}`: the tag-dispatch consumer (likely
  `0x00781170`, called from the advance state machine `0x00782090`, which
  also auto-crossfades 0.1–0.2 s at the start/end window edges) was not
  read this session. The "channel-set" constants 2/3 ARE GrTrans
  transform-stream indices (§3.4, `GR_TRANSFORMS` = 5) — and since tags
  19/20/21 exceed 5, the key tags are a DIFFERENT enum, still unnamed.
* n50/n52/n54/n55/n56/n57 var-arrays: still strides only.
* The m_skel/m_geom object identity (UM §6.3) — evidence here cuts both
  ways (`[esi+8]` tested for skeleton flags then read for geometry lights
  at `0x0077D384`; but the blend CTX carries separate +0x8/+0xC slots).
  U3's question; observations recorded, nothing claimed.

> **Refutation pass (2026-08-16, adversarial, independent).** Posture was
> REFUTE; the reversal survived harder than this document argues it. The
> reviewer re-derived all four samplers' address arithmetic (`base +
> 4·count + N·idx` — impossible under the AoS overlay), re-measured BOTH
> overlays at an equalized tolerance (100.000% vs 0.30%), verified S =
> B+0x38 from both ends (the parser's own B-relative writes land at the
> S-relative offsets the consumers read), and found the renormalization
> gate §2.1 had left on the floor. The hierarchy invariant, sum
> identities, strictness resolution, flag-bits-1/2 exhaustiveness (a
> whole-image scan for `test [reg+0x38]` sites) and all three spot-checked
> disasm dumps reproduced byte-exact. Verdicts: §2.1/§3.1, §2.2/§3.4,
> §3.5, §4 CONFIRMED; §2.6's layout and FA6 join CONFIRMED, its
> sequence-relative time reading PLAUSIBLE only (see R-3 in place). One
> BUG (B-1, the FA6/FAE count+1 — both affected rows re-checked, both
> conclusions tightened), and the R-1/R-2/R-4 weight corrections are
> recorded in place at the rows they amend. The two unforceable test
> checks gained the failing controls the review measured for them
> (AoS ~0.3% unit-norm; rotated links ~23% violations).

## 7. Provenance

All measurements are from the owner's own build-38797 image and archive
via extractors in this repo plus scratch scripts preserved under
`vault/research/anim/`. Assert expressions are quoted singly, each as
evidence for a specific claim with file:line; no bulk dump. Offsets,
strides, VAs and constants appear in bulk as MEASUREMENT per the
2026-08-12 ruling (root `PLAN.md` §7 Q3). No asset bytes are reproduced —
corpus results are counts and histograms. Names committed as ids; the only
authored strings quoted are single assert/error expressions. Second gate:
nothing here derives from any upstream — every layout was read from the
client and tested against the archive; no §6.1 register row is required.
