# The companion chunks and the object model — rung U3

Build 38797, read from the vaulted stock `Gw.exe`
(`vault/client/2026-07-29_221c13772c7a/Gw.exe`) and from
`vault/dat_study/Gw.dat` — no client was launched for any of this. This is
rung U3 of [../unitmodels/PLAN.md](../unitmodels/PLAN.md); the evidence base
it starts from is [../unitmodels/FINDINGS.md](../unitmodels/FINDINGS.md) §5
(cited below as **UM**), and the committed deliverable is
`toolkit/mapdata/mdlrefs.py` + `test_mdlrefs.py`. Labels are the project
vocabulary ([../character/FINDINGS.md](../character/FINDINGS.md)).

**How this document was produced.** One session: the reference-list decoder
was written from the disassembly, then a four-shard sweep decoded every
reference chunk on every `flags=515` head THROUGH the committed module
(artifacts: `vault/research/mdlrefs/2026-08-16-u3/`, five predictions stated
in `refsweep.py` before the run and scored in §3); the object-identity and
mid/tail questions were settled by direct disassembly of the pinned binary
(every VA below was printed by `codescan.py --dis` this session). Corpus
work is single-witness here but doubly framed: the record rule's rival is
run beside it everywhere, and the population identities cross-check UM's
independently written censuses at six points (§3.4).

---

## 1. The answer in one page

- **The record rule is committed code and closes everything.** All five
  list chunks (FA5/FA6/FA8/FAD/FAE) go through one client-side reader whose
  scanner ends a record at the FIRST ZERO u16 WORD (`0x00908274`). The
  committed decoder replicates it exactly and closes **30,722 of 30,722
  reference chunks over the complete flags=515 head population** — zero
  failures — while the rival fixed-6 framing dies on exactly the **5,393
  FA5 chunks carrying null slots** (11,894 slots), both directions
  (MEASURED, §3). The FA6-first population is **exactly 388** and closes
  388/388, reproducing UM's independent prefix sweep.
- **FA6 ⟺ m_soundPaths is confirmed at the consumer** (SOURCE-CODE, §4):
  MdlAnim:2040's compiled body reads the bound from `m_skel+0x80` and
  indexes the pointer array at `m_skel+0x84` — the exact offsets the loader
  fills from FA6. The chain UM §5.2 flagged as unverified end-to-end is now
  one function's printed instructions.
- **The object identity is settled: m_skel and m_geom are TWO OBJECTS of
  two different classes** (SOURCE-CODE, §5). Two constructors in
  MdlBuild.cpp (0x15C-byte class A, 0x11C-byte class B, distinct vtables),
  one name-keyed cache holding both kinds, FA0/FA5/FAD parsed into A,
  FA1/FA6/FA8/FAE into B, and the render-side holder keeping `m_geom` at
  +0x8 and `m_skel` at +0xC. UM §3.2's "dual writers of +0xA4" dissolves:
  the two writers target two different fields of two different objects that
  happen to share a displacement.
- **The mid/tail chunk families are classified** (SOURCE-CODE, §6): the
  TAIL family (0xFAC/0xFA4/0xFA7/0xFAB) is consumed at RUNTIME by
  MdlApi.cpp; the MID family (0xBB8–0xBC1, 0xFA3, 0xFAA) is consumed by
  MdlDecomp.cpp — the decompile/export path — and the mid ids MIRROR the
  model's own chunk ids 1:1 through a compiled pairing table
  (0xBB8↔0xFA0, 0xBB9↔0xFA1, 0xBBB↔0xFA5, 0xBBC↔0xFA6, 0xBC0↔0xFAD,
  0xBC1↔0xFAE, 0xBBE↔0xFA9, and two tail pairings 0xBBA↔0xFA4,
  0xBBF↔0xFAB).
- **FA8 is widened 10× and holds**: 252 chunks / 2,467 records / 394
  distinct targets — every one ffna type-2, every one carrying FA1, none
  carrying FA0 (MEASURED, §7). 284 of the 311 FA1-only heads are FA8
  targets, closing most of UM §6.8's coverage question.
- **Two population surprises** (§3.3): chunk `0xFA9` EXISTS in the archive
  — 2 heads, byte-identical 5,340-byte payloads, not a reference list —
  refining UM §2.2's NOT FOUND; and FAE's population is exactly 6 chunks /
  22 records whose targets are all COMPLETE geometry-bearing models — the
  inverse of FA8's.

---

## 2. The record rule, from the client's own scanner

### 2.1 The reader chain, re-verified

SOURCE-CODE. The wrapper `0x00796DE0` has **exactly five** direct call
sites (xref sweep, every alignment): `0x00794540` (FA5 → +0xC0/+0xC4),
`0x0079455B` (FAD → +0xFC/+0x100), `0x007947BD` (FA6 → +0x80/+0x84),
`0x007947D6` (FA8 → +0x10C/+0x110), `0x00794815` (FAE → +0x9C/+0xA0) —
confirming UM §5.1's set and offsets instruction-by-instruction. The
wrapper fetches the chunk (`0x00907C70`), reads `u32 count` at offset 0,
hands `payload+4 .. end` to the per-list reader `0x00794B70` (single
caller), which calls the scanner `0x00908260` once per record:

    0090826B  dec edx                 ; limit = end - 1
    0090826C  mov esi, [edi]          ; record start
    00908270  cmp esi, edx / jae FAIL
    00908274  cmp word ptr [eax], 0   ; THE TERMINATOR TEST
    00908278  lea ecx, [eax + 2]
    0090827B  je FOUND                ; zero word ends the record
    0090827D  mov eax, ecx
    0090827F  cmp eax, edx / jb 0x908274
    FAIL:  return NULL                ; no zero word in bounds
    FOUND: *cursor = ecx; return record start

A record is therefore a run of u16 words ended by the first zero word —
**variable length**, ArenaNet's `pathName` (MdlLoad:2201
`PathIsRelative(pathName)`, assert VA `0x00794883`) — and the fixed-6
reading is not the rule even though every FA6/FA8/FAD record in this
archive happens to be 2 wchars. Three semantics the committed decoder
replicates or deliberately tightens, each stated in its docstring:

- **The end-1 edge**: a word at byte `p` is readable only while
  `p < len-1`, so an odd trailing byte is unreachable and a zero BYTE on
  the last byte is not a zero WORD (fixture-pinned).
- **The client silently loads an empty list on a malformed record** —
  `0x00794B70`'s error path (`0x00794C27`) returns 0 with no assert, and
  the wrapper leaves count 0 / array NULL. The module raises `Undecodable`
  at a named gate instead: an unreadable list is a finding, not an absence.
- **The client never compares its final cursor to the chunk end** — the
  reader allocates `count×4 + consumed` and copies exactly the consumed
  bytes (`0x00794BB4–0x00794C09`, an array of per-record pointers over one
  blob). So `cursor == len(payload)` is OUR closure assertion, and §3's
  30,722 green walks are real checks, the same posture `skelfile.py` takes.

The scanner `0x00908260` itself has five callers (`0x0071554C`,
`0x00771C22`, ours, `0x0079D9C8`, `0x0082C696`) — it is a generic Riff.cpp
wide-string scanner; only the `0x00794B70` path is this module's subject.
The chunk helpers' TU is ArenaNet's `Base\Services\Riff.cpp` (assert sweep
at `0x00907905`: Riff.cpp 22 sites), the reader/loader TU is MdlLoad.cpp.

### 2.2 A recorded divergence inside our own tree

`modelfile.texture_refs()` (M5) implements FA5 as "2 bytes if `id0 == 0`,
else 6" — a rule that agrees with the terminator rule on every record shape
that exists (0- and 2-wchar) and would diverge on a 1-wchar record
(4 bytes: `id0, 0`), where modelfile would consume 6 bytes and the client
4. MEASURED at full population: records of length other than 0 and 2 wchars
occur on **0 of 30,722 chunks**, so the divergence is vacuous on this
archive and `modelfile.py` is left untouched; `mdlrefs.decode_records` is
the client-faithful rule, and a U6 re-serializer should frame by it.

---

## 3. The full-population sweep, predictions first

Five predictions were written into `refsweep.py` before the run
(`vault/research/mdlrefs/2026-08-16-u3/`); the run decoded every reference
chunk on all 21,421 flags=515 heads through the committed module.

### 3.1 Scored

| # | prediction | result |
|---|---|---|
| P1 | every FA6/FA8/FAD/FAE chunk closes; FA6-first is exactly 388 | **HELD** — 0 decode failures anywhere; FA6-first 388, closing 388/388 |
| P2 | fixed-6 closes all FA6/FA8/FAD/FAE; fails exactly on FA5's null-slot chunks | **HELD** — rival/null agreement 30,722/30,722 both directions |
| P3 | every 2-wchar id resolves in `file_id_table(raw=True)` | **HELD** — 0 unresolved of 107,747 records |
| P4 | FA8 population ≈ the stride-4 estimate (~232); targets all type-2, no FA0, all FA1 | **HELD with a corrected count** — 252 chunks (estimate was low), targets 394/394 clean |
| P5 | the head signature census lands near UM §2.3's ×4.0002 estimates | **HELD** (§3.4), with FAE at 6 vs "≈8" and one signature the estimate could not see (FA9) |

### 3.2 The populations (MEASURED, exact)

| chunk | chunks | records | null slots | null chunks | rival fixed-6 fails |
|---|---:|---:|---:|---:|---:|
| FA5 | 20,661 | 83,106 | 11,894 | 5,393 | 5,393 (exactly the null chunks) |
| FA6 | 3,734 | 11,709 | 0 | 0 | 0 |
| FA8 | 252 | 2,467 | 0 | 0 | 0 |
| FAD | 6,069 | 10,443 | 0 | 0 | 0 |
| FAE | 6 | 22 | 0 | 0 | 0 |

FA5's chunk count **equals the FA0-first population** (20,661): every
geometry-bearing head carries a texture list, and no head carries FA5
without FA0. The one non-ffna head is the known row 8316 (UM §2.2).
UM §5.1's stride-7 figures (390 null chunks / 876 slots of 2,215 FA5
sampled) were a floor; the full population is ~2.4× denser in nulls than
that sample suggested.

### 3.3 Two surprises

- **`0xFA9` exists.** Heads 176432 and 176439 carry signature
  `FA0,FA5,FA9,FA1` — the two payloads are **byte-identical** (5,340 B) and
  are NOT a reference list (`u32 1, u32 1, u32 0`, then floats; the module
  correctly refuses at `G02_close`). UM §2.2 recorded FA9 as NOT FOUND over
  its strided sweeps; the full population finds it. The client fetches it
  at `0x00796C4A` into a dedicated parser (`0x00796C30`, MdlLoad region) —
  a fetch site this session had already located from the code side before
  the corpus produced the chunk (§6.2's pairing 0xBBE↔0xFA9). Contents
  UNVERIFIED.
- **FAE is a linked-model list whose targets all carry geometry.** 6
  chunks (5× `FA6,FAE,FA1`, 1× `FA6,FAE,FA1,FA8`), 22 records, and every
  target is ffna type-2 with `FA0+FA1+FA5+FAD` (20) or
  `FA0+FA1+FA5+FA6+FAD` (2) — complete self-contained models, the exact
  inverse of FA8's uniformly FA0-less targets. What the consumer does with
  the +0x9C/+0xA0 arrays is still UNVERIFIED; the population is now pinned
  at 6, not "≈8".

### 3.4 Cross-checks against UM's independent scanners

The sweep's per-signature census (chunk-table order, exact): FA1-carrying
heads sum to **14,571** (= the U1 walker's population exactly); FA6 total
3,734 = 2,649+697+191+191+5+1 across its six signatures; FA8 252 =
191+60+1; FAD 6,069 = 2,747+2,625+697; FA1-only heads **311** (UM
estimated ≈312); FA6-first 388 (UM's adversarial prefix sweep: 388). Six
figures, three independently written scanners, zero disagreement.

---

## 4. The FA6 ⟺ m_soundPaths join, confirmed at the consumer

SOURCE-CODE. UM §5.2 chained this across two agents and asked U3 to
confirm the consumer end. The compiled body of MdlAnim:2040 (assert VA
`0x00780D68`, expression `pathIndex<m_skel->m_soundPathCount`):

    00780D55  mov esi, [eax - 8]        ; pathIndex, from the anim record
    00780D58  mov eax, [edi + 0xc]      ; m_skel (holder +0xC, see §5)
    00780D5B  cmp esi, [eax + 0x80]     ; the BOUND: m_skel+0x80
    00780D61  jb ok                     ; else assert line 0x7F8 = 2040
    00780D77  mov ecx, [edi + 0xc]
    00780D7A  mov eax, [ecx + 0x84]     ; the ARRAY: m_skel+0x84
    00780D80  mov esi, [eax + esi*4]    ; m_soundPaths[pathIndex]

The loader writes FA6's `(count, array)` to exactly +0x80/+0x84
(`0x007947A9–0x007947BD`, re-verified). The element fetched is a 4-byte
pathName pointer (the reader's per-record pointer array, §2.1), which the
consumer hands to the same path helpers (`0x470300`, `0x47E020`) the FA8
loop uses. The join UM made across agents is now one function's printed
instructions: **`m_soundPathCount`/`m_soundPaths` ARE the FA6 list.**

---

## 5. The object identity: two objects, and the +0xA4 tension dissolves

SOURCE-CODE throughout; this settles UM §3.2/§6.3 from OPEN to an answer.

### 5.1 Two constructors, one cache

The cached by-id loader `0x00794260` (cache global `0xF26F10`, confirmed)
looks up a **{kind, name}** key and holds TWO kinds per name:

- kind **1** → constructor **`0x0077B7C0`** (MdlBuild.cpp:989): one
  allocation of **0x15C bytes + inline name at +0x15C**, vtable
  `0xA77624`, shared init `0x007797F0(this, 1, name)`, intrusive list node
  at +0x150..+0x158. Call it **class A**.
- kind **0** → constructor **`0x0077B8E0`** (MdlBuild.cpp:829): one
  allocation of **0x11C bytes + inline name at +0x11C**, vtable
  `0xA77620`, shared init `0x007797F0(this, 0, name)`, and a float-fill of
  +0x48..+0x6C — three vec3 slots — from constants at
  `0x955828`/`0xA77AC4`/zero. Call it **class B**.

Distinct sizes, distinct vtables, one shared partial-init and a common
flags dword at +0x38 on both (a shared base; `0x007945D5` sets bit 6 of
A+0x38, the FA1 parser sets bits of B+0x38 = `m_skeletonFlags`).

### 5.2 The wiring: which parser writes which object

Inside `0x00794260` after the name resolves to bytes (ffna type gate
accepts **2 or 5** — `0x007943F1/0x007943F9`, type 5 loadable as a model
is a new observation, unexplored):

- **Class B gets the skeleton side**: `0x00794444–0x00794446` calls the
  loader `0x00794780` with `this = objB` — so FA6 (+0x80), FAE (+0x9C),
  FA8 (+0x10C/+0x110/+0x114) and the FA1 parser (`0x00796310`, reached
  with `this = objB` at `0x00794966`) all write **B**.
- **Class A gets the geometry side**: `0x00794533/0x0079454C` store FA5 →
  A+0xC0/+0xC4 and FAD → A+0xFC/+0x100, and the FA0 parser (`0x007952A0`,
  same `u32 == 0x26` version gate) is called with `this = objA`
  (`0x0079458D`).
- **The consumers hold both**: `m_geom = [holder+0x8]` (MdlAnim:1121
  `cmp edx,[eax+0x60]` m_emitterCount; :1122 +0x98 m_streakCount; :1956
  +0x48 m_lightCount — every offset matching UM §4's geometry-object
  fields) and `m_skel = [holder+0xC]` (MdlAnim:2040, §4; also a loop bound
  at B+0xAC, `0x007802AE`, unnamed).
- **FA8 links resolve to class B objects**: the recursion loop passes
  `(name, 0, &slot, 0)` — kind 0 only — at `0x007948F7–0x007948FF`, then
  requires the linked B's `m_seqCount` non-zero (`cmp [ecx+0x6C], 0` at
  `0x00794917`). A "linked model" is a linked SKELETON object, which is
  why 394/394 FA8 targets carry FA1 (§7).

### 5.3 The dual +0xA4, dissolved

    FA0 parser:  00795577  mov eax, [ebx + 0x44]    ; header num_models
                 0079557A  mov [edi + 0xa4], eax    ; edi = objA
                 00795582/00795588  gates: 0 refused, > 0xFE refused

    FA1 parser:  00796601  movzx eax, word [ebx + 0x52]  ; header n52
                 00796605  mov [edi + 0xa4], eax    ; edi = objB

`A+0xA4` is `m_geoCount` (MdlCombine:1923's bound). `B+0xA4` is the stored
n52 count — a different field of a different class that shares nothing but
the displacement. Every "geometry-family offset the FA1 parser also
writes" in UM §3.2 is the same artifact: two layouts compared by number.
The recorded tension was an illusion of the one-object assumption, and the
question moves from OPEN to **ANSWERED: two objects, per-kind cache, role
fixed at construction** (SOURCE-CODE). A pleasant corollary: class B's
constructor pre-fills the three vec3 slots at +0x48 that UM §3.3's n14
records overwrite by slot index — defaults, then data.

---

## 6. The mid/tail chunk families, classified

The get-chunk helper `0x00907C70` has exactly **30** direct call sites
(xref, every alignment); each was decoded back to its pushed chunk-id
constant this session. Beyond the model-file ids (FA0 ×1, FA1 ×2, the
generic wrapper ×1) and non-model users (map region `0x713xxx–0x714xxx`
with register ids; sound-service sites pushing chunk 1/2 at
`0x757FD0/0x758045`, `0x7B8DD7/0x7B9124`, `0x851Dxx`; one
`AcctTemplate.cpp` site pushing 0xFA3 at `0x0091C276` — a different
container namespace, recorded so nobody joins it to the model FA3), the
mid/tail families split cleanly by consumer TU:

### 6.1 Tails: runtime consumption in MdlApi.cpp

| chunk | fetch VA | consumer |
|---|---|---|
| 0xFAC | `0x007783C2` | fn `0x00778350` (MdlApi): the tail's 12-byte manifest — gate `size >= 0xC && u32@0 == 1`, exposes `u32@+4` and `u32@+8` as out-params (`0x007783DC–0x007783F4`) |
| 0xFA4 | `0x00778418` | same fn → parser `0x00778BB0` |
| 0xFA7 | `0x00778450` | same fn → parser `0x00778A90` |

The FAC/FA4/FA7 reader `0x00778350` has four direct callers, and they name
what the tail stream IS: `Engine\Map\Props\PrCollision.cpp`
(`0x0073A86C`), `Engine\Map\Zones\ZnDef.cpp` (`0x0076ECB2`), and two
MdlTex sites (`0x0078DD9B`, beside MdlTex:2888
`! (curr->flags & MODEL_FLAG_COLLISION_END)`; `0x0078E598`). With FAB's
`planes` going to the sight builder, the tail family reads as the model's
COLLISION/VISIBILITY payload, consumed by the map-side systems
(RECONSTRUCTION from consumer identity; chunk contents still unread).
| 0xFAB | `0x00778531` | fn `0x007784A0` (MdlApi:1431–1433, args named `flags`/`planeCounts`/`planes`) — 0xFAB carries PLANE data. Two callers: MdlTex (`0x0078DA93`, beside MdlTex:2842/2843 `fileName`/`pathFlatGeosets`) and **Engine\Map\Sight\StBuild.cpp** (`0x007412E0`) — the sight builder reads it |

Both functions obtain their container the same way: resolve a file
argument to bytes via `0x00470B60`, require `ffna` **type 2**
(`0x00907F60` + `cmp eax, 2`), and open a Riff context over the bytes
(`0x009078E0`, Riff.cpp — asserts `dataBytes`/`data` at Riff:162/163,
checks the `ffna` magic at `0x009079C0`; its first argument is a FLAGS
word, bit 0 = borrow-don't-copy — not a stream index). **How the file
argument maps to the MFT's `nextStream` chain was not traced** — the
mid/tail rows' non-addressability (0/21,420 file-id rows, UM §2.2) means
the handle must come from the archive's stream linkage, but the hop from
`0x00470B60` down into the file service is beyond this session; OPEN,
with the search stopping at that named function.

### 6.2 Mids: decompile-side consumption in MdlDecomp.cpp — a 1:1 mirror

The big MdlDecomp function at `0x0079CFC0` reads mid chunks from one
container and pairs each with a model chunk accessed through
`0x00907FB0` — and that accessor is the WRITE side: its own asserts are
`riff` (Riff:315) and `riff->flags & (RIFF_CREATE_WRITE |
RIFF_CREATE_APPEND)` (Riff:317, VA `0x0090800A`), so the paired container
is being APPENDED, not read (paired close `0x00908160`). The direction is
therefore: read mid chunk 0xBBn, write/translate into chunk 0xFAn of an
output model container — the mid stream holds what the decompiler needs
to reconstruct the authoring-side model file:

| mid id | fetch VA | paired model/tail chunk | pairing VA |
|---|---|---|---|
| 0xBB8 | `0x0079CFFB` | 0xFA0 (geometry) | `0x0079D000` |
| 0xBB9 | `0x0079D237` | 0xFA1 (skeleton) | `0x0079D23C` |
| 0xBBA | `0x0079D421` | 0xFA4 (a TAIL chunk) | `0x0079D42B` |
| 0xBBB | table slot 0 (`0x0079D067`) | 0xFA5 | table slot 0 (`0x0079D085`) |
| 0xBBC | table slot 1 (`0x0079D070`) | 0xFA6 | table slot 1 (`0x0079D08C`) |
| 0xBBD | `0x0079D957` | none — walked directly (8-byte header + data, `0x0079D97E`) in the fn carrying MdlDecomp:2739/2740 `PathIsRelative(filename)` / `!PathIsRelative(relativeTo)` — a FILENAME/path chunk |
| 0xBBE | `0x0079D14C` | **0xFA9** | `0x0079D151` |
| 0xBBF | `0x0079D60A` | 0xFAB (a TAIL chunk) | `0x0079D617` |
| 0xBC0 | table slot 2 (`0x0079D077`) | 0xFAD | table slot 2 (`0x0079D093`) |
| 0xBC1 | table slot 3 (`0x0079D07E`) | 0xFAE | table slot 3 (`0x0079D09A`) |
| 0xFA3 | `0x0079C125` | fetched directly from the mid container in a helper beside MdlDecomp:2819/2831 (`seq->sequence`, `seqInfoCount`) — sequence-adjacent |
| 0xFAA | `0x0079C183` | same helper family |

(The four-entry table loop runs `0x0079D0A1–0x0079D13C`, ids at
`[ebp-0x6C..]` paired against `[ebp-0x5C..]`.) The mid family is therefore
**the model's chunk-id space mirrored into the mid stream** — per-model-
chunk companion data that the decompile/export path (MdlDecomp, where
the `MDLEXP_` vocabulary lives, UM §3.10) expands back into the model's
own chunk-id space on write, plus a filename chunk (0xBBD) and two
sequence-adjacent ids (0xFA3/0xFAA). The pairing
0xBBE↔0xFA9 predicted a model chunk 0xFA9 from the code side before the
corpus sweep found its 2 carriers (§3.3) — a small blind cross-check that
landed.

`0xBB0–0xBB7`, `0xFA2`: no fetch site among the 30, and no corpus
occurrence — NOT FOUND, stated as: every direct `0x00907C70` call site
classified; indirect fetches (register-held ids at `0x0079D0AA`'s loop are
the four table slots above; the map-region sites take variable ids) not
exhaustively enumerated beyond those.

What the acceptance asked — fetch-site VAs and consumer TUs per chunk id —
is the two tables above. What remains open on this front: the semantic
CONTENTS of every mid/tail chunk (only 0xFAC's 12-byte manifest and
0xBBD's role are pinned), and the `nextStream` hop (§6.1).

---

## 7. FA8 widened, and the FA1-only class mostly explained

MEASURED at full population (was: 25 chunks / 257 records, UM §5.3's own
caveat): **252 chunks, 2,467 records, 394 distinct targets** —

- 394/394 resolve in `file_id_table(raw=True)`; all ffna type-2;
  **0 carry FA0; 0 lack FA1** — the §5.3 claims hold at 10× the evidence.
- Target signatures: `FA1` only 284, `FA1,FA6` 71, `FA1,FA6,FA8` 32,
  `FA1,FA8` 7 (39 targets themselves carry FA8 — the recursion the loader
  resolves through its cache, UM §5.3).
- **The FA1-only class is 311 heads (exact), and 284 of them are FA8
  targets** — 91.3% of UM §6.8's "partially explained" class is now
  explained as link targets. The remaining **27** FA1-only heads are
  referenced by no FA8 chunk on any head: reached some other way
  (0x0056 shells? mid-stream references?) — OPEN, now with an exact count
  and the row list derivable from the sweep artifacts.
- The loader-side mechanics (§5.2): links resolve as class-B (skeleton)
  objects, `m_seqCount != 0` enforced per link at `0x00794917`.

---

## 8. What is still open

1. **FAD and FAE semantics** — framing closed, populations exact (6,069 /
   6), consumers of A+0xFC and B+0x9C unread.
2. **The 27 uncovered FA1-only heads** (§7).
3. **FA9's 5,340-byte payload** (2 identical copies; version-1 header +
   floats; parser `0x00796C30` unread) and its mid companion 0xBBE.
4. **The `nextStream` hop** from `0x00470B60` to the MFT chain (§6.1) —
   how the client opens mid/tail containers it cannot address by file id.
5. **Mid/tail chunk contents** beyond 0xFAC's manifest and 0xBBD's role.
6. **ffna type 5** accepted by the model loader's gate (§5.2) — what is it?
7. **The type-8 descriptor's reader** — `type8_deps`' count-less fixed-6
   framing is MEASURED shape (len % 6 == 0 on every sampled descriptor),
   not a disassembled rule; the sound-service fetch sites
   (`0x757FD0/0x758045`) are located but unread.
8. **B+0xAC** (a MdlAnim loop bound, `0x007802AE`) and the rest of class
   B's unnamed fields; class A/B vtable contents (`0xA77620/0xA77624`).

## 9. Provenance

Every measurement is from the owner's own build-38797 image and archive,
via extractors in this repo (`codescan.py`, `asserts.py`, `archive.py`,
`mapchunks.py`, the new `mdlrefs.py`) plus session scratch scripts that
import them; no client was launched. Assert expressions are quoted singly
with file:line as evidence for specific claims; no bulk dump. No asset
bytes are reproduced — the MPEG identification counts frame-header field
validity (`test_mdlrefs.py` §3, 231/231) and copies no audio; the FA9
payload appears above as its own header words only, a layout measurement,
not content. Sweep artifacts (JSONL of rows/counts/ids — measurements per
the 2026-08-11 ruling) are in `vault/research/mdlrefs/2026-08-16-u3/`.
Second gate: nothing here derives from any upstream; every layout was read
from the binary or the archive this session.
