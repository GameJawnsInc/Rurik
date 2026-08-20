# Past the `Gw.dat` write-size wall

**Arc scoping study, 2026-08-17.** Nothing here is built yet. This is the costing that
decides what gets built, and §3 is a **PROPOSAL until the owner adopts it**.

Two independent research passes fed it. §1–§4 and §6 come from five route scouts, each
attacked by its own skeptic; **four of the five verdicts were overturned**, and the
reversals are recorded first because a reversal is the most valuable thing in this
document. §5 comes from a separate pass that followed the client's archive-repair path to
completion — the question [studies/datwrite/FINDINGS.md](../datwrite/FINDINGS.md) named as
decisive and left open. It is here rather than there because it is route-independent: it
sets the risk budget for every rung in §3.

The wall is the one U7 hit on its way out: [studies/unitmodels/PLAN.md](../unitmodels/PLAN.md)
records it as *"the 1.5 MB FA8 animation library (15018) is unwritable — `datmove` refuses
it by name and no compression-8 encoder exists."* Every clause of that is true and the
frame is wrong. **File 15018 never needed 1.5 MB of contiguous space.** It already owns a
1,029,632 B reservation and already ships compressed at 1,029,564 B; the 1.5 MB is what it
*decompresses to*. The real bar is not "beat ArenaNet by 7%" but "match ArenaNet within
3,732 bytes, in place" — a different arc, and a much smaller one. §1.1 has the numbers.

**Labels** are the project vocabulary ([../character/FINDINGS.md](../character/FINDINGS.md)).
This document has two kinds of first-person claim and they are not interchangeable:

- **OBSERVED (mine)** in §1–§4 and the appendix is the synthesis author, who reproduced
  those measurements read-only in this tree before writing.
- **OBSERVED (orchestrator)** marks the four things the session lead ran independently
  afterwards, listed in the appendix — including §5.4's generation census, which nobody in
  either dossier had taken and which the severity of §5 turns on.
- Everything attributed to a scout or a skeptic is labelled as theirs. Where two agents
  produced a number independently, that is said.

**Conditions of the whole study.** Read-only against `vault/dat_study/Gw.dat` through
`toolkit/mapdata/archive.py`, which never opens for writing. Nothing in the vault was
modified. No client and no server was launched. No ArenaNet bytes appear below — only
offsets, sizes, counts, ratios, addresses and chunk ids, plus single asserts cited as
evidence, per `CLAUDE.md`'s measurement/expression boundary.

---

## 0. Corrections, up front

The house rule is that corrections go where they cannot be missed.

| # | What was recorded | What is measured |
|---|---|---|
| **C-1** | The wall is "~1,514,560 bytes of FA1" | That is the **chunk**. The **file** is 1,514,855 B (FA6 184 + FA1 1,514,560 + FA8 82 + framing). Both round to the same 2,959-block reservation, so no plan changes — but every ratio in this arc must use 1,514,855. **OBSERVED (mine)** |
| **C-2** | `U7-RUN.md`: largest usable run 953,856 B | That is `dat_study`'s figure. The archive U7 actually deployed into (`run/2026-08-13_64fae3b1369b`) has a largest usable run of **285,184 B**. Any capacity claim must name its copy. **OBSERVED** (Route B scout, uncontested) |
| **C-3** | Route E scout: "9,593 B of in-place headroom under zlib -9" | **9,589 B.** The DAT framing appends a 4-byte uncompressed-size trailer (`gwdat.py:349-350`), which the scout's zlib figure omitted. **OBSERVED (mine):** zlib -9 raw/-15/memLevel 8 → 1,020,039 B, +4 = 1,020,043 against a 1,029,632 B reservation. |
| **C-4** | Route A scout: "the true ratio of the 1.5 MB payload is unmeasured; bracket ×0.11–×0.77" | It was measured — that morning, in the scout's own scratchpad. True value **×0.6803** under the scout's own encoder, which produces **1,030,604 B: 972 B OVER the reservation**. The optimistic half of the bracket came from a synthetic. **OBSERVED** (Route A skeptic; I did not re-run the prototype, so this is CORROBORATED for me) |
| **C-5** | `datalloc.py:73-76` (was :53-56): growth past EOF is "unrevertible in principle" | **Wrong as stated.** Record the pre-growth size in the journal and `os.truncate` on revert; a scout ran it on a synthetic fixture and it restored to 10-of-10 clear. The docstring describes the current JSON schema, not a property of archives. It should be amended to say *why we still refuse* (concurrency and the u32 ceiling, §4.4), not that we cannot. **OBSERVED** (Route B scout) |
| **C-6** | `datmove` is the relocation verb | `datmove.move()` writes **compression → 0 unconditionally** (`toolkit/mapdata/datmove.py:222-224`) and re-CRCs over the bytes it was handed. Relocating any compression-8 row with it produces a **green archive holding an unreadable file** — the entry CRC is over stored bytes, which are unchanged, so all three checksum rules and all ten open-time rules still pass. **OBSERVED (mine, source read; confirmed by two skeptics independently).** This is the single sharpest trap in the stack and it is live today. |
| **C-7** | — | `archive.py:322` reads the header `mftOffset` as **`<I`**; `datcheck.py:223` and `datwrite.py:101` read it as **`<Q`**. Two of three readers say u64 and the outlier is the one every tool imports. Latent (all 14 vault archives have the high dword zero) and ~93 MB of file growth away from firing silently on the 38833 line. **OBSERVED (mine, all three lines read).** |
| **C-9** | §2.5: *"the population supporting 'the client reads a large stored row' is EMPTY, not thin"* — retail's largest ordinary stored content row is 19,292 B and our one precedent is U7's 29,802 B | **STALE, and by our own hand.** The retail census still reproduces exactly (0 of 38,621 stored rows above 19,292 B, excluding the structural rows). But `datmove` writes compression 0 unconditionally, so **run 5 shipped ELEVEN stored rows above 19,292 B — the largest 765,378 B (file 117797) — and it was deployed and launched by the owner with no assert** (§9.3i/j). The honest framing is now **11× beyond the largest PROVEN-READ stored row and 0.5× the largest DEPLOYED-WITHOUT-CRASH one**, not "the population is empty". This materially de-risks **A5**, whose whole premise was that empty population. **OBSERVED** (run-7 skeptics, two independently, 2026-08-18) |
| **C-8** | — | Two row censuses disagree by 16: 138,708 comp-8 rows (Route E) vs 138,692 (Route C skeptic), against 38,621+12 vs 38,629 comp-0. The sums are 177,341 and 177,321 — `len(entries)` versus live rows. `archive.py:413-431` warns about exactly this and names the study it already corrupted. **Unresolved bookkeeping**, and it is load-bearing for the "661 rows" headline. |
| **C-10** | §9.3g: *"the node bases are **bone lengths**"*, and §11.4's positive-control geometry — node 62 at world z −805.3, a "whole-creature extent of 805" — accumulated down the parent chain | **Both wrong, and the second reproduced the first rather than catching it.** `blk2C` bases are **ABSOLUTE MODEL-SPACE REST POSITIONS**, not parent-relative offsets. **ArenaNet's own mesh is the referee**: file 116703's bounding box is **72.6 units** across, the absolute reading seats all 86 joints **inside the skin** (joint→nearest-vertex median **1.40 u**, max 5.67), and the accumulated reading puts them **532 u away** (median). A forward-kinematics model taking the offset as `base[i] − base[parent[i]]` reproduces every stored rest position to **0.000000** with identity rotations — a check that can fail, and the accumulating model fails it. The *consequence* §9.3g drew is untouched (scaling bases still explodes the skeleton, and run 6 fired), but every distance in §11.4 is ~11× too large and the real numbers are **better**: head ×3 moves the cluster **1.98× the creature's entire extent**, not 0.67×. **OBSERVED (mine, 2026-08-18); the refutation came from a run-7 skeptic and I reproduced it against the mesh.** |
| **C-11** | §16.2: gap A "comes from *tiny and degenerate* payloads"; §13.5: the fix is "a two-symbol distance table inside retail's attested envelope … a size question, not a design one" | **Three corrections, all measured (§17.2).** (1) Payload size is incidental — the trigger is *any block with no matches, or with only distance-1 matches*, and `test_gwenc`'s own **50 KB** `granule straddle x1` fixture emitted a declared-1 table on every run. (2) A two-symbol distance table is **not attested at 2**: retail's declared-distance floor is **5** over all 32,831 comp-8 rows ≤ 2,048 B, its twelve zero-length distance tables (rows 8295–8306) all declare exactly 5, and **no retail row anywhere declares a distance count of 2, 3 or 4**. (3) "A size question" is true for the empty-table route only; the single-symbol-at-index-0 route **cannot** use the zero-length code at n ≥ 2 (`gwdat.py`'s `total == 0` fallback installs symbol `n−1` and no other index) and costs **1 bit per match** in that block — bounded ≈ 0.05 % because the matcher takes maximum-length matches. **OBSERVED** (gap-A recon, 2026-08-19; fix landed §17.2) |
| **C-12** | §13.5 gap D, recorded as an encoder curiosity (`encode(b"")` → 12 B) | **It reached the archive layer.** `datwrite.declaration_fault(gwenc.encode(b""), 8, expect=b"")` returned `None` — the zero-length guard tested the STORED bytes (12, not 0) and the mandatory-`expect` guard tested `is None`, which `b""` passes — so a zero-block comp-8 row could be written into an archive. Retail's smallest comp-8 row is 56 B and holds a block. Closed both sides 2026-08-19/20: `gwenc.encode(b"")` raises, and `declaration_fault` refuses a stream that decompresses to nothing (§17.2, §17.4). **OBSERVED** (gap-A recon; fix in `test_datwrite` §11j) |
| **C-13** | §14.2 hole 3 "fixed": `datalloc`'s comp-8 gate now DECODES instead of matching a two-byte marker — read as the creation path being safe | **The gate refutes FRAMING damage and nothing else, and the fidelity direction reached disk.** `declaration_fault` appeared in `datalloc.py` **zero** times; a `gwenc` stream with a corrupted trailer went to disk through `alloc(confirm=True)` and through `--stream FILE:1:8`, `Archive.read()` handing back 8,191 B instead of 8,192 while `--verify`, preflight 10/10 and the overlap sweep stayed green. Over 528 single-byte flips of one real stream: **132 refused, 394 decoded to the wrong bytes and were ACCEPTED, 2 benign**. Also: `alloc(plan=P)` ran no gate at all, and a doctored plan wrote `extraBytes 8` over plainly stored bytes. **OBSERVED (adversarial verifier, 2026-08-20; closed the same day, §17.5** — `expect=` mandatory with `extraBytes 8`, the gate in `alloc()` as well as `plan_alloc()`, twelve sabotages red**)** |

---

## 1. The wall, in numbers

### 1.1 The decision number

Everything about this arc turns on one comparison, and it is not the free map.

| Bar | Bytes | Ratio | vs ArenaNet's own output |
|---|---|---|---|
| **Retail's actual output** on file 15018 | 1,029,564 | **0.679645** | ×1.000 |
| **In place** — fit the row's own 1,029,632 B reservation (less the 4-byte trailer) | ≤ 1,029,628 | 0.679690 | **×1.0001 — merely MATCH it, within 64 B** |
| **Relocate** — fit the largest usable free run on `dat_study` | ≤ 953,856 | 0.629668 | **×0.9265 — BEAT it by 7.35% (75,708 B)** |
| zlib -9 raw deflate, 32 KB window, memLevel 8, + trailer | 1,020,043 | 0.673361 | ×0.9907 — fits in place, **misses relocation by 66,187 B** |

**OBSERVED (mine).** File id 15018 = row 11196: offset `0x29BF2200`, stored 1,029,564 B, compression 8, reservation 1,029,632 B (2,011 blocks, **68 B slack**), decompressing to 1,514,855 B. `crc32(stored bytes) == the MFT crc`, so `archive.py:34`'s CRC domain is live and a compression-8 write verb is mechanically sound.

**The relocation bar is unreachable and should stop being quoted.** No deflate configuration anyone tried — eighteen across two agents — comes within 66 KB of 0.6297. The in-place bar, by contrast, is *reachable and thin*: **9,589 B of headroom, 0.931% of the reservation**, and that number is measured on **retail's own payload**, not on anything we would author.

### 1.2 The compression bar is a coin flip, not a low bar

This is the Route E reversal and it is the most decision-relevant correction in the dossier.

The scout's headline — *"ArenaNet's compressor is a LOW bar… zlib already beats it by 0.9%"* — rests on **n = 1**. The skeptic sampled the population:

- **120 random comp-8 rows ≥ 700,000 B stored:** zlib -9 beats ArenaNet on 81, **LOSES on 39 (32.5%)**. Aggregate zlib/retail = **0.9981** — a statistical tie, not a 0.9% win. Worst losses are real overflows: row 77197 +7,168 B, row 95089 +5,114 B, row 89174 +4,873 B.
- **250 random rows 4 KB–700 KB:** loses on 60 (24.0%), aggregate 0.9964.
- **80 of the 661 fully-stuck rows:** only 61 (76.2%) fit their own reservation under zlib -9. **19 (23.8%) miss.** Headroom distribution: min −6,494 B, Q1 +788 B, **median +2,896 B**, Q3 +4,737 B, max +11,499 B.

**15018's ~9,589 B sits in the top decile.** It is a favourable draw, not a representative one. [OBSERVED, Route E skeptic]

The scout's robustness argument — *"all 8 deflate configurations tried fit in place"* — is a check that could not fail: the failing configurations were outside the chosen set. The skeptic's full sweep of levels 1–9 × memLevel 8/9 on the real payload: **level 1 → 1,151,970 B (overflow by 122,338), level 2/memLevel 8 → 1,032,089 B (overflow by 2,457), level 2/memLevel 9 → 1,037,137 B (overflow by 7,505)**; only level 3+ fits. And level 8/memLevel 8 reaches 1,017,638 B, **beating** level 9 — so zlib -9 is near the *ceiling* of what deflate does on this content, not a floor an amateur encoder clears by default.

**The consequence, stated plainly: the success/failure boundary for a bespoke compression-8 encoder lies INSIDE deflate's own tuning range.** "An encoder no better than zlib -9" is not a modest target; it is close to the best deflate achieves here. This is the fact that converts Route A/E from VIABLE to EXPENSIVE.

### 1.3 How much of the archive the wall actually covers

**OBSERVED** (Route E scout, count reproduced **exactly** by the Route E skeptic):

- **661 of 138,708 compression-8 rows (0.48%)** have an uncompressed size both > 953,856 B and > their own reservation — unwritable stored, anywhere.
- **Zero** rows exceed the largest gap-measure free run (14,718,976 B).
- **121,139 rows (87.3%)** cannot be rewritten *stored* in place and would need relocation; 17,569 could be rewritten in place today.
- Breakdown of the 661: **352 ffna type 3 (maps), 103 ffna type 2 (model containers — 15018 is one), 31 ATEX, ~140 MPEG audio, 4 DDS, 3 MZ**, remainder unclassified.
- Of the 103 stuck model containers, **79 carry an FA1 animation chunk**: min 957,258, median 1,395,009, max 2,946,637, total 115,113,511 B. **The arc-relevant blocked set is 79 files.**

**Caveat, and the scout named it:** the 661 figure rests on the trailing declared-size u32 for 138,692 of the rows, and `gwdat.py`'s own docstring warns the decoder terminates *at* that value — so "produced == declared" is forced, not checked. 16 rows were validated against real decodes (16/16) and both anchors additionally close their ffna chunk walks to the exact byte. See also correction **C-8**: the denominator itself is disputed by 16 rows.

### 1.4 The 953,856 B ceiling is a policy number, not a capacity number

**OBSERVED (mine, reproduced):**

| | raw free runs | raw total | raw largest | usable | usable total | usable largest | withheld |
|---|---|---|---|---|---|---|---|
| `dat_study/Gw.dat` | 214 | 32,528,384 | 14,718,976 | 208 | 3,367,936 | **953,856** | 6 runs |
| `dat_study_38833/Gw.dat` | 33 | 13,307,392 | 5,636,608 | 28 | 3,513,344 | **2,892,800** | 5 runs |

`datplan.classify_runs` (`datplan.py:279`) withholds **89.6% of `dat_study`'s free bytes (29,160,448 B in 6 runs)** because they carry live MFT / file-id-table container generations. **Four raw runs would fit the 1,515,008 B reservation; all four are withheld.** Total *usable* space is 2.22× what the payload needs — **the blocker is fragmentation and conservatism, not capacity.**

And the ceiling is **play-history state, not a constant.** Largest usable run across the 14 vault archives: 133,632 (`run-live/2026-07-29`) · 285,184 (all three 38833 client/run copies) · 471,552 (`client/2026-04-30`) · 953,856 (all seven 38797-family copies) · 2,892,800 (`dat_study_38833`). **Any plan costed against a specific run size expires the next time the archive is played.** [OBSERVED, Route E scout]

### 1.5 The withholding rule is measurably wrong on one archive, and it is UNSAFE TODAY

Both a scout and a skeptic converged on this independently and it is route-independent:

`datplan.container_signature` (`datplan.py:219-249`) tests a block's **head** for `Mft\x1a` magic. MFT rows are 24 B against 512 B blocks, so **no interior block ever carries a signature** — a stale generation whose header block has been overwritten is invisible *by construction*.

The failure is measured, and it was a **stated prediction that landed to the byte**: `dat_study_38833`'s 2,892,800 B "usable" run at `0xF5923800` is the orphaned tail of a stale MFT generation. `client/2026-08-13` withholds that whole region as one 4,262,912 B run whose head at `0xF57D5000` carries `Mft\x1a` declaring 177,608 entries = 4,262,592 B. In `dat_study_38833` the **live** file-id table occupies `0xF57D5000..0xF5923800` (1,369,664 B, reservation 1,370,112), destroying the magic. **1,370,112 + 2,892,800 = 4,262,912 exactly, and 2,892,480 of the 2,892,800 B (100.0%) lies inside the stale generation's declared extent.** [OBSERVED, Route E scout]

**`datmove.plan_move` on that archive picks precisely `0xF5923800`.** Nothing in the current rule set refuses it. The archive would look clean afterwards — all three CRC rules, alignment, no overlaps — right up until the client rotated its table back onto our payload.

**Fix: withhold by an MFT generation's DECLARED EXTENT, projected across run boundaries, not by a head magic.** `dat_study_38833` is a ready-made regression fixture. This is rung **A3** and it is not optional.

### 1.6 The premise nobody checked: 15018 is not the creature's animation

**OBSERVED (mine — I reproduced this from scratch through `toolkit/mapdata/mdlrefs.py`).** The hatcher shell's FA8 chunk is not a link, it is a **15-record list**, all 15 resolvable in the file-id table, with 15018 merely **first**:

| file id | row | stored | comp | decompressed | FA1 | **sequences** |
|---|---|---|---|---|---|---|
| **116228** (shell) | 13738 | 20,236 | 8 | 29,802 | 29,495 | **242** |
| **15018** | 11196 | **1,029,564** | 8 | 1,514,855 | 1,514,560 | **237** |
| 52518 | 11194 | 63,560 | 8 | 82,974 | 82,961 | 4 |
| 53607 | 11193 | 38,692 | 8 | 50,952 | 50,939 | 3 |
| 66614 | 11192 | 17,024 | 8 | 22,961 | 22,948 | 2 |
| 73940 | 11191 | 144,212 | 8 | 189,686 | 189,655 | 14 |
| 52176 | 11195 | 138,632 | 8 | 178,844 | 178,813 | 8 |
| **87333** | 11141 | **1,161,236** | 8 | 1,354,523 | 1,354,510 | 40 |
| 96978 | 11130 | 161,148 | 8 | 214,868 | 214,855 | 22 |
| 108085 | 11119 | 157,844 | 8 | 203,587 | 203,574 | 2 |
| 109464 | 11118 | 27,948 | 8 | 79,194 | 79,181 | 7 |
| 117797 | 11117 | 536,352 | 8 | 765,378 | 765,365 | 16 |
| 158828 | 11116 | 121,948 | 8 | 159,114 | 159,101 | 10 |
| 202023 | 11115 | 95,000 | 8 | 123,941 | 123,928 | 7 |
| 222949 | 11114 | 7,644 | 8 | 11,878 | 11,865 | 7 |
| 169533 | 13737 | 186,268 | 8 | 241,443 | 241,430 | 6 |

**Thirteen of the fifteen are under 953,856 B stored** — already inside the free run the arc calls the wall. Only 15018 (1,029,564) and 87333 (1,161,236) exceed it. 15018's own FA8 holds 13 records: the 13 the shell duplicates.

Two further measurements of mine that nobody in the dossier took:

- **Sequence density.** Shell FA1: 29,495 B / 242 seqs = **121.9 B per sequence**. 15018: 1,514,560 B / 237 seqs = **6,390.5 B per sequence**. The shell's FA1 is index-shaped; 15018's is payload-shaped. (The Route A scout's synthetic "237 near-identical 6,390 B sequences", which produced the fantasy ×0.1149 ratio, is exactly this division read as if it described the content.)
- **Sequence arithmetic.** Shell declares **242**; 15018 declares **237**; the 15 link targets sum to **385**; grand total 627. So the shell's table is neither a concatenation of the links (385) nor of everything (627). **242 = 237 + 5** is suggestive and is **RECONSTRUCTION, not a finding** — it is exactly what rung **A1** must settle.

**This is the D-skeptic's reversal and I confirm it:** "spread this creature's animation across N files each well under the ceiling" is not a route we would be inventing. It is the mechanism retail already uses **fifteen times on this creature**. In its additive form — author a new FA1 file, `datalloc` it, append a 16th FA8 record — **retail's 15018 is never rewritten and the 1.5 MB wall does not arise.** The client resolves links recursively at load through the cached by-id loader ([studies/unitmodels/FINDINGS.md:683-702](../unitmodels/FINDINGS.md), loop `0x00794850-0x00794926`, loader `0x00794260`), and `MdlAnim 0x0078231C` walks a linked model's animation blocks — **UPSTREAM-of-this-repo disassembly, re-derived by neither me nor the skeptic.**

---

## 2. The five routes, after the skeptics

Verdict vocabulary: **VIABLE** (build it), **EXPENSIVE** (real, buildable, priced far above the scout's estimate), **UNKNOWN** (not scorable on current evidence), **BLOCKED** (refuted; do not re-derive), **CONTESTED** (scout and skeptic disagree and neither won).

| Route | Scout | Skeptic | **After** |
|---|---|---|---|
| **E** — measure the wall / in-place compressed write | VIABLE | refuted, high | **EXPENSIVE** |
| **A** — build a compression-8 encoder | VIABLE | refuted, high | **EXPENSIVE** |
| **D** — `nextStream` continuation | BLOCKED | **confirmed**, high | **BLOCKED** — *and the scout's option space is overturned* |
| **B** — grow the archive past EOF | VIABLE | refuted, high | **CONTESTED** |
| **C** — engineer contiguous free space | VIABLE | refuted, high | **BLOCKED as planned** / EXPENSIVE as a rebuilt route |

### 2.1 Route E — measure the wall, write in place compressed → **EXPENSIVE**

**Scout's claim:** the wall is neither the compression ratio nor the free map — 15018 already owns a 1,029,632 B reservation, zlib -9 fits inside it with headroom, so a compression-8 encoder no better than zlib makes the row writable **in place** and the 953,856 B ceiling irrelevant.

**SKEPTIC OVERTURNED IT, and the evidence is §1.2.** *"The wall is not the compression ratio"* is presented as a property of the archive; it is a property of one row. On the population, zlib and ArenaNet are a **statistical tie** (aggregate 0.9981), 23.8% of stuck rows miss their own reservation, and the median stuck row has 0.3% headroom. The scout measured 15018's ratio *percentile* (35th) and never once compared zlib to retail on any other row — the single measurement that would have tested their own headline.

The skeptic also **upgraded a label in the scout's favour** and it should stand: the 32 KB LZ77 window is **OBSERVED**, not RECONSTRUCTION. `gwdat.py:138-150` gives `DISTANCE_BASE[29]=0x6000` with 13 extra bits → 0x6000..0x7FFF, and `src = len(out)-(back+1)` → window exactly 32,768, deflate's window exactly; combined with `first_four == 2` (min match 3) measured constant across 4,000 rows, **deflate is a fair comparator**.

**One scout risk the skeptic could not sustain, reported honestly:** *"an authored FA1 compresses worse than retail's"* is **measurably small**. U7's edit to 116228 changed 390 of 29,802 bytes and cost **+0.050% compressed**, against 0.940% of headroom. The scout's weakest-sounding risk is their least dangerous one. [OBSERVED, Route E skeptic]

**Cost after the skeptic:** the encoder (§2.2) plus a ~10-line `datwrite` verb. That verb is genuinely small and the mechanics are all proven: `replace()` flattens compression to 0 unconditionally (`datwrite.py:508-511`) and needs an arm that writes `len(new)` as the size, **keeps compression 8**, and CRCs the *stored* bytes — every one of which the `restore`/donor path already does (`datwrite.py:610-614`), sourcing bytes from a donor instead of a caller. I confirmed the CRC domain by measurement (§1.1).

**What would settle the remainder:** one caged loopback run reading a row this project compressed. Nothing on paper touches it — and note that **`datcheck.py` (974 lines) contains ZERO references to compression codes** [OBSERVED, Route E skeptic, by grep], so neither a round trip nor the archive invariants can refute a conforming-but-wrong bitstream. **The client is the only oracle.**

### 2.2 Route A — build a compression-8 encoder → **EXPENSIVE**

**Scout's claim:** the encoder is cheap and already proven — a ~150-line throwaway prototype round-trips literals, dynamic Huffman and full LZ77 through unmodified `gwdat.decompress`, 24/24 synthetic cases plus real FA1 at 1.5 MB scale, in ~4 s. Ratio on the real 1.5 MB payload was reported as **unmeasured**, bracketed ×0.11–×0.77.

**SKEPTIC OVERTURNED IT, three ways, and this is the sharpest reversal in the dossier.**

1. **The measurement the scout called "one read-only measurement nobody has taken" had already been taken — that morning, in the very scratchpad they worked in.** `p15018.bin` (the decompressed payload) and `sweep_dat_study.json` (a 138,708-row census) sat beside the `enc8.py` they wrote. One `ls` of their own working directory converts their central unknown into a number.
2. **Their own prototype, run on the real payload, produces 1,030,604 B — 972 B OVER the 1,029,632 B reservation.** Round-trip OK, 4.1 s. True ratio **×0.6803**, clustered at the *pessimistic* end of their bracket, in three-way agreement with retail (×0.679645) and zlib (×0.677227) inside 0.5%. **The ×0.11 synthetic that anchored the optimistic half is fantasy about this payload.**
3. **The scout stated the bar for a path they had already ruled out.** Their headline was "×0.772 against a required ×0.630". ×0.630 is the *move* cap. Their own risk list concedes the route only pays via in-place `replace`, whose bar is **×0.6797**. For the record, the move path is dead beyond rescue: zlib -9 misses 953,856 by 72,044 B (7.6%), and no encoder quality closes that.

**And the payoff, correctly denominated, is tiny.** Against the 1,029,632 B reservation: prototype **−972 B** (overflow); an encoder *exactly as good as ArenaNet's* **+68 B** (0.0045% of payload); a zlib-9-class encoder **+3,732 B** (0.246%). The reservation cannot grow: row 15018 occupies `[700,391,936, 701,421,568)` and the next allocated row (30044) begins at **exactly** 701,421,568. Zero adjacent free space. [OBSERVED, Route A skeptic]

**THE COST NOBODY HAD PRICED, and it is what makes this EXPENSIVE rather than VIABLE.** The point of the next rung is to *modify* the animation. The skeptic measured elasticity: retiming a random **0.1%** of the payload's u32 slots by ×1.37 (a non-power-of-two retime — U7's ×2/×4 were exponent-only and unusually cheap) costs **+806 B and fits**; **1.0% costs +8,725 B and OVERFLOWS by 4,993 B**; 5.0% costs +43,118 B. **The route delivers a write budget that a one-percent edit destroys.** "The wall is cleared" and "you may change about a quarter of one percent of the entropy" are not the same claim, and only the second is true.

**What survives and is real capability.** The format work is good and neither skeptic broke it:

- The format is **per-block dynamic Huffman + LZ77**: two code tables transmitted per block before the payload (`gwdat.py:344-362`).
- The meta-coder carrying those tables is **static and fully invertible**: a canonical prefix code over exactly 256 tokens, lengths 3..16, defined by `CODE_LENGTH_THRESHOLDS` (14 pairs) + `CODE_LENGTH_SYMBOLS` (256 bytes) at `gwdat.py:103-126`. The scout inverted it — all 256 tokens covered exactly once, no holes, no duplicates. **Serializer ≈ 18 lines, not a research problem.**
- Each meta token packs `(repeat, length)`: `temp>>5 = repeat-1` (1..8), `temp & 0x1F = code length` (0..31); symbols described from the **highest index downward** (`gwdat.py:249-264`).
- Code assignment is canonical but **counts DOWN from all-ones** — equivalently, standard canonical codes bit-complemented (`gwdat.py:295-312`).
- **Distance codes 30 and 31 have extra-bit entries but garbage bases** (a read past the end of Table6). **The alphabet is 0..29, full stop.** An encoder trusting all 46 `DISTANCE_BASE` entries emits nonsense.
- The stream header is **constant across 4,000 sampled rows**: the 4 discarded lead bits are 0 in 4000/4000 and `first_four` is 2 in 4000/4000 (min match 3, identical to deflate) [OBSERVED, Route E skeptic]. **This retires the scout's own "emit 0b1111?" risk with a measurement** — copy the constant header; do not guess.
- **No compressor exists in ANY mirrored lineage.** All five checked: GWMB `xentax.cpp`, gw-preservation `binutil/huffman.go`, Fournux `gw_dat_decompress.rs`, OpenTyria `FaCompress.c` (declares `FaDecompress` only, despite the filename), Headquarter `docs/compress.c`. **NOT FOUND.** Nobody upstream wrote the inverse.

**Two risks nobody could retire.** `gwdat.py` is the only referee, and its own docstring (`gwdat.py:81-84`) says the check that would settle it — diffing against `xentax.cpp` on the same input — **has never been run**; it additionally has a **known divergence** from both upstream lineages on the zero-length code (`gwdat.py:270-288`). A bit-exact round trip through a wrong decoder proves agreement, not correctness. *(Mitigating: the scout instrumented the zero-length counter and it stayed at **0** on every Huffman and LZ run — a real encoder never enters the divergent region. Only the toy all-literals mode does.)*

**Second gate:** `gwenc.py` inverts GWMB's tables and is a derivative work. **Its `PLAN.md` §6.1 register row must exist BEFORE the module does** — the exact retrofit `mapchunks.py` needed (`PLAN.md:1091`).

### 2.3 Route D — `nextStream` continuation → **BLOCKED**, and the scout's option space overturned

**Scout's claim, and the skeptic CONFIRMED it in full** (`refuted=false`, high confidence, re-derived from scratch with predictions written first): `alloc.nextStream` is a **semantic sibling link, not a continuation link**. Chaining cannot spill one payload across two rows.

Three continuation predictions were stated first and all three failed:

- **P1 (chained rows cluster at a max size): FAILS.** n=44,700; min 24, p25 73, median 868, p75 6,672, p95 36,816, max 994,416; 8,120 distinct values; commonest are 41 B (×6,871) and 73 B (×5,983). Exactly one row within 1% of max.
- **P2 (a target is the middle of another blob, no magic): FAILS.** Full population: **43,189 begin `ffna`, 1,510 begin `ATEX`, 1 other.** A model head pointing at a row that starts with a *texture* magic is not a continued payload. The single exception is the pair the unit-model arc already recorded: row 8316 (28 B) → row 8318 (24 B).
- **P3 (the head's chunk walk overruns its own length): FAILS.** 400/400 sampled rows parse as ffna and their chunk tables consume each row's **own** decompressed output to the exact byte. 0 overruns, 0 short walks. `archive.ffna_chunks` raises if the walk does not land exactly (`archive.py:602-628`) — **a check the artifact could have refuted 400 times and did not.**

Supporting: chain lengths are tiny and do not scale with payload (2×350, 3×20,303, 4×724, 5×393). `alloc.stream` is a **slot id, not a position index** — sequences (2,0,11)×18,571, (2,1,0,11)×697, (2,12,1,0,11)×393; the numbers go **down** and skip. The link map is a **perfect corpus-wide bijection** (44,700 links, 44,700 distinct targets, every in-degree exactly 1, 0 dangling), independently reproducing [studies/datwrite/FINDINGS.md:396](../datwrite/FINDINGS.md).

**BLOCKED stands. Do not re-derive it.**

**But the skeptic overturned everything the scout said AFTER the refutation.** The scout asserted "the two routes the measurements actually leave open" and that claim is false — see §1.6. Three things the scout's cost model never mentioned:

- **FA8 additive split** (§1.6): the mechanism retail uses fifteen times on this creature. The scout's cost estimate does not contain the string "FA8".
- **DISPLACEMENT, zero new code:** **117 rows in `dat_study` have a block reservation ≥ 1,514,855 B** (116 file-id addressable; largest row 35300 at 6,247,936 B). `datwrite.replace` writes into an existing reservation and flips compression 8→0 in the same journalled write — **a stored 1,514,855 B payload needs NO free run at all.** Displacing a retail asset is this project's own established install pattern (`datalloc.py:5-8`: map 143 displaced a real retail area and we still do not know which). The scout quoted `datmove`'s 953,856 B refusal as the archive's capacity; **it is the capacity of one verb, RELOCATE.**
- **COALESCING** was tested and collapses into displacement: exactly 2 usable runs reach 1.5 MB by releasing one adjacent row, and both victims (173882, 173887) are file-id-named retail assets. Same price, more moving parts. **Recorded so nobody re-derives it as new.**

**Three label corrections the skeptic made and which stand:** (a) the scout's *strength* is inverted — the full-population P2 test is the **weak** one (`archive.magic()` decompresses only 4 bytes; 4 bytes decoding does not establish a valid container), while the **strong** test, P3's chunk-walk closure, is the one sampled at 400. (b) "Chaining cannot spill one payload across two rows" is a claim about the **client**, and the client-side hop is explicitly untraced here — [studies/mdlrefs/FINDINGS.md:334](../mdlrefs/FINDINGS.md) §8 item 4 lists it OPEN. **The conclusion is RECONSTRUCTION from data self-containment, not OBSERVED.** It points the right way and does not rescue Route D. (c) "177,341 rows" is `len(entries)`, not the row count; `ar.row_count` is 177,342 — the exact trap `archive.py:413-431` warns about (see **C-8**).

### 2.4 Route B — grow the archive past EOF → **CONTESTED**

**Scout's claim:** growth is not built, but `datalloc`'s stated reason is wrong, no open-time rule constrains file size, the retail client grows the archive itself, and a working prototype took ~40 lines.

**What survives, and it is substantial:**

- **No open-time rule constrains size.** The ten rules are enumerated at `datcheck.py:437-591`; **rule 5** (`datcheck.py:478-482`) tests `offset+size > size_on_disk` — a **LOWER** bound. Growing the file makes it strictly *easier* to pass.
- **No header field carries a file size.** The 32-byte header is magic / headerSize=32 / blockSize=512 / crc / mftOffset(u64) / mftSize(u32) / flags — all 32 bytes accounted for. A search of every u32 and u64 header offset in three archives for a value equal to the file size: **zero hits.** The header CRC covers only 0x00..0x0C and reads identically on pristine and grown copies.
- **THE CLIENT GROWS THE ARCHIVE ITSELF.** Two copies in the loopback run dir were cut from a 4,200,829,952 B source and are now **+916,480 B** and **+2,286,592 B**. MFT flush counters 26,853 and 27,270 against the source's 26,813; `run-live/2026-08-13` is byte-identical and never grew. `Gw.log` shows `AuthSrv (127.0.0.1)` — our loopback server, updater killed, no ArenaNet connection. **Growth is the archive layer's own allocator, not a download.** In both copies the growth is the MFT double-buffer bumping past EOF: the trailing region is exactly **4,266,496 B** (one whole MFT reservation), begins with `Mft\x1a` declaring the same 177,753 entries, and ends exactly at EOF.
- **Both grown archives pass 10 of 10 open-time rules and all three checksum rules.** A grown archive is not a degraded archive by any measure this project has.
- **C-5:** growth **is** revertible. Journal `original_size` + `os.truncate` restored a fixture to 10-of-10 clear.

**THE SKEPTIC OVERTURNED THE VERDICT, on four grounds:**

1. **The wall Route B was proposed to break is `classify_runs`' conservatism, not geometry.** `free_runs` on `client/2026-08-13` returns 13,917,696 B over 31 runs including one **contiguous 4,262,912 B run** — 2.8× the payload — and the grown copy has 16,204,288 B with **three** runs ≥ 4.26 MB. Every one is withheld. *"The scout re-measured the number and never asked what it was measuring, then proposed a new file-extending primitive to obtain space the file already has."*
2. **A same-build copy plans successfully today with zero new code.** `datmove.plan_move` on `dat_study_38833/Gw.dat` (build 38833, row 11196 byte-identical) returns a **MovePlan**: row 11196 → 4,120,000,512, reservation 1,515,008 B. So *"Route B is required to unblock U7"* is false as stated. *(But see §1.5 — that same archive's largest usable run is a detector bug. This route and that bug intersect and both must be resolved together.)*
3. **A u32 ceiling the plan walks toward and does not guard** — correction **C-7**, which I verified independently. Measured headroom to 2³²: **93,220,864 B of file** and 97,487,784 B of MFT end on the 38833 run archive, with the MFT riding at the top. **Growth is the only operation in the toolkit that moves an archive toward that cliff**, and the five-piece plan adds `size_on_disk` to `diff()` but no ceiling refusal and no fix to `archive.py:322`. On a 4.2 GB file the owner cannot re-download, that is the wrong omission.
4. **Operational, hit directly:** `run/2026-08-13/Gw.dat` went from readable to `PermissionError` between two passes — **another session holds it open**. A grow-then-run loop races concurrent sessions, and the proposed revert gate ("refuse when size ≠ journalled size") **trips on exactly that**.

**WHY THIS IS CONTESTED AND NOT SETTLED: the two skeptics disagree with each other.** Route B's skeptic scores growth *dominated* — spend the session on in-file relocation. Route C's skeptic scores growth the **cheapest route on the board** and uses it to dominate Route C: *"extend at EOF, write the payload, rewrite row 11196's offset/size/comp/crc — the exact four field writes `move()` already performs. It touches ONE row instead of fifteen, needs ZERO free space, needs ZERO new MFT rows."*

**The experiment that decides it** is rung **A5**, and it is the same run either way, so the disagreement costs nothing to resolve: **extend a copy by 1,515,008 B, write row 11196's payload there DECOMPRESSED BUT OTHERWISE UNMODIFIED, repoint the row, and run it caged.** Because the payload is byte-identical to what the client renders today, any visual change is unambiguous evidence about the **container**, not the content. One run answers three open questions at once: does the client read a 1,514,855 B **stored** row; does it tolerate a row past the old EOF; and does file extension work at all.

**Two gaps that would hide a growth, and they are cheap:** `datcheck --diff` **cannot see it** — `snapshot()` records `size_on_disk` but `diff()` compares only mft_offset/mft_size/header_flags/descriptor_counter/descriptor_count, so a 4 KB bare growth reports `unchanged: True` (`datcheck.py:781-786` vs `:635`). And `mapchunks`' row-index cache stamps `dat_size` (`mapchunks.py:620`), so **every growth silently invalidates it** and forces a full corpus rebuild (the module's own docstring records a 604 s pass).

**One more risk that must not be lost:** the client derives `m_endOfFile` by walking the MFT at open, and on an archive with trailing slack the bump path **overwrites existing physical bytes rather than growing** ([studies/customarea/FINDINGS.md:2271](../customarea/FINDINGS.md)). **An appended payload that is not yet registered in the MFT, or that gets orphaned, sits in a region the client is entitled to reuse.** Register first, or lose it.

### 2.5 Route C — engineer contiguous free space → **BLOCKED as planned**

**Scout's claim:** evacuating the 14 live rows immediately after row 11196 opens **1,520,640 contiguous bytes at the target's own address** for 491,008 B of moves — far cheaper than a general defragmenter.

**THE SKEPTIC KILLED THE PLAN WITH A REPRODUCTION, and this is the cleanest single refutation in the dossier.**

`datmove.plan_move` calls `datplan.best_fit` over the **whole** usable pool (`datmove.py:163-165`), and `move()` **returns each vacated extent to that pool** by zeroing it (`datmove.py:226-227`). Simulating the 14 relocations sequentially with the real `classify_runs`/`best_fit`: **4 of the 14 rows land back INSIDE the window being cleared** — row 30048 best-fits into the 91,648 B extent row 30044 just vacated at `0x29CED800`. **The final contiguous run at `0x29BF2200` is 1,029,632 B: the target's own extent and nothing more. Runs ≥ 2,959 blocks afterwards: none. Zero net gain.**

The proof that this is the scout's gap and not a different simulation: **re-running the identical search with one added rule — destinations may not fall in `[0x29BF2200, 0x29D65600)` — reproduces the scout's destination table EXACTLY, all 14 rows, address for address**, and yields the 1,520,640 B window. **The scout applied a window-exclusion rule in simulation, and it appears nowhere in `datplan`, nowhere in `datmove`, and nowhere in their stated plan.**

**And the piece they costed smallest has to be built from scratch.** `--verbatim` cannot reuse `plan_move`: its **first substantive guard** (`datmove.py:152-158`) refuses precisely the operation class a verbatim move is — *"row 30044 already reserves 91648 B and the payload is 91644 B, so it fits where it is."* A verbatim relocation is **by definition** `payload_size ≤ old_res`. Called live on 5 of the 14 rows, every one refused. So `--verbatim` needs its own planner **and** its own destination selection.

**What is real and should be salvaged from Route C, regardless of which route wins:**

- **C-6, the compression-flattening trap.** This is Route C's genuine contribution and it is live today. Both skeptics confirmed the mechanism.
- **The whole-archive entry-CRC post-flight.** Does not exist; costs **3.3 s** (177,321 live rows, 4,113,234,158 B at 1,233 MB/s), ~30 lines, and reports exactly **2** "mismatches" — rows 1 and 3, the two structural rows with their own CRC rules. **It is the only guard that would catch C-6.**
- **The journal is not crash-safe across invocations.** `Journal.flush` truncates and rewrites the entire JSON on every record with **no fsync** (`datwrite.py:343-347`), so a crash inside a flush destroys that invocation's whole history. A 15-step defrag produces 15 separate journals to be replayed in exact reverse order **by hand**; nothing writes a manifest. And revert **stops working the moment the archive is launched** — `revert` raises when the journalled `mft_offset` differs from the header's, and the client moves the MFT during ordinary play (measured: `0xF8FFF000 → 0xF8BEFE00` in this very archive). **The honest atomicity story for a 4.2 GB archive is copy-verify-swap, not journals.** C: has ~317 GiB free.
- **The scout's synthetic write experiment is a check that could not fail** (the skeptic's label, and it is right): copying bytes and rewriting an offset trivially preserves a payload and a CRC taken over unchanged stored bytes.

**And the scariest measurement in the whole dossier, which applies to every stored-write route:** of **38,628 STORED rows in the retail archive, the largest ordinary content row is 19,292 B** (row 177242). The only two above it are rows 2 and 3 — the file-id table and the MFT, which the client reaches **through the header**, not through the file-id/decompression path. **Zero ordinary stored content rows above 19 KB have ever existed in this archive.** The proposal is 1,514,855 B: **78× retail's largest, 51× the one U7 precedent (29,802 B). The population supporting "the client reads a large stored row" is EMPTY, not thin.**

*(Minor scout facts corrected by the skeptic, none load-bearing: 6 rows are flags 0x203 plus row 30049 at 0x003, not 7 at 0x203; the set is 6 head+partner pairs, 1 orphaned middle link and 1 singleton, not a clean 7+7; row 11196 carries **two** file ids in the raw table, 379789 and 15018. Also verified safe: the MFT is **not** in ascending offset order by row index (14,711 inversions), so the client sorts at open and relocation is order-agnostic; and `next_stream` is a row index (all 44,690 nonzero values in 1..entry_count), so relocation cannot break a chain.)*

*(Incidental, verified: `datcheck.row_fields` (`datcheck.py:260-265`) names entry+0x0C `extra_bytes` while `datmove`/`archive.py` call it `compression`; `datalloc.py:129-131` documents both spellings. Measured across all live rows the field takes only {0, 8} — **it is compression.** Harmless today, but a live naming disagreement inside one module set.)*

---

## 3. The recommended ladder — A1 … A8

Rung shape follows [studies/unitmodels/PLAN.md](../unitmodels/PLAN.md): each rung is a deliverable with a criterion the artifact can refute, and a kill/keep decision. **PROPOSAL until the owner adopts it.**

**Order is deliberate: A1 and A2 are free, read-only, and either one can end the arc.** Nothing gets built until both have run. This is the whole point of the ordering — the dossier contains two separate cases of an expensive plan built on a measurement that was available for free.

| Rung | What | Acceptance criterion (refutable) | Est. |
|---|---|---|---|
| **A1** ✅ **RUN 2026-08-17 — ANSWERED: PER-FILE, selector named, see §8. The encoder LEAVES the critical path** (the file to rewrite is the 20 KB shell, not the 1 MB link). | **Is the sequence index space global across the FA8 link graph, or per-file?** Read-only. Walk the hatcher's 15 link targets (§1.6) with `skelfile`, and either (a) find the client-side selector that maps a requested sequence index to a *file*, or (b) refute globality from the corpus. My own measurement is the starting evidence and the puzzle: shell **242**, 15018 **237**, the 15 links sum to **385**, grand total **627** — so 242 is neither. State the prediction first. | Either: **the index space is global** and adding a 16th linked FA1 is transparent (→ A4 becomes the route, the compressor drops to nice-to-have and this arc mostly ends); or **it is per-file** and the selector is NAMED with its VA and a corpus prediction that could have failed; or **NOT FOUND**, with the search range recorded. Widen past the hatcher before anything leans on it — the FA8 graph is acyclic with max link depth 1 corpus-wide ([studies/unitassembly](../unitassembly/FINDINGS.md)), so one creature is one witness. | 0.5 session |
| **A2** ✅ **RUN 2026-08-17 — GREEN, see §7. The row below is SUPERSEDED**: its elasticity figures did not reproduce, and the edit it names can only move 692 B of a 1.5 MB payload. | **Does a REALISTIC edit still fit? The elasticity gate.** Read-only, no encoder. Take the real 1,514,855 B payload, apply the edit the next rung actually wants through `skelwrite`'s existing seam (`scale_sequence_keytimes`), re-serialize, and compress with zlib -9 raw/-15 (+4 B trailer) as the **optimistic** proxy. | **> 1,029,632 B ⇒ the in-place compressed route is DEAD for that edit, no matter how good `gwenc.py` gets, and no encoder is written.** This has a real chance of going red: the measured elasticity is **+806 B at 0.1% of slots retimed, +8,725 B (OVERFLOW) at 1.0%**. Report the fraction of slots at which it crosses, not a yes/no. | 0.5 session |
| **A3** ✅ **BUILT 2026-08-17 — see §9.1. Seven items, floors 84→112 / 78→87 / 38→44** | **The route-independent safety fixes, and they can all go red.** (a) `container_signature` withholds by an MFT generation's **declared extent** projected across run boundaries, not by a head magic — regression fixture is `dat_study_38833` (§1.5). (b) `archive.py:322` `<I` → `<Q`, plus a synthetic archive with `mftOffset` above 2³² (**C-7**). (c) `datcheck --crc-sweep`, whole-archive, ~30 lines. (d) `datcheck --diff` compares `size_on_disk`. **(e) `datcheck --generations` (§5.4) — count surviving MFT generations and their flush counters, ~40 lines and one pass; nothing in the repo checks today whether a fallback exists before you risk needing one. (f) An explicit refusal in `datwrite.py` on header bytes `0x00..0x0C` (§5.6 rule 2) — the silent-wipe region is currently protected only by absence. (g) Mark the shadow-MFT rotation region as reserved in `datplan`/`datalloc` (§5.4) so no allocator can consume the client's own recovery material.** TESTS.md entries in the same commit — `test_srclint.py` §7 checks both directions. | `plan_move` on `dat_study_38833` for row 11196 **REFUSES** where it currently accepts `0xF5923800`; the u32 test fails before the fix and passes after; the CRC sweep reports exactly 2 structural exceptions (rows 1 and 3) in ~3.3 s and **catches a deliberately compression-flattened row** (C-6) that all ten open-time rules pass. Floors set from a real green run. | 1 session |
| **A4** ✅ **BUILT 2026-08-17 — see §9.2. `toolkit/mapdata/unitauthor.py`, the edit costs +29 B. Awaiting the client run, which is A8 and needs the owner's go-ahead** | **The additive FA8 path, on a SYNTHETIC archive only.** Build with `test_datcheck.py`'s `build_archive`; `datalloc` a new FA1-only file, append a 16th record to a copy of 116228's FA8 chunk (`mdlrefs` encodes the dependency-pair spelling), re-emit the shell with `skelwrite`. Never against a real `Gw.dat`. | Ten open-time rules clear, three CRC rules clear, `datalloc`'s MFT-slack accounting honest, the shell round-trips byte-identically apart from the intended FA8 delta, and the new row is registered **before** any bytes land in a region the client may reuse. **Kill:** if A1 said per-file-with-unknown-selector, this rung cannot state what the client will do with the 16th record and should stop at "archive-legal" rather than claim a route. | 1 session |
| **A5** | **THE CONTAINER EXPERIMENT — one caged run, owner-driven.** On a **copy**: extend the file by 1,515,008 B at EOF, write row 11196's payload there **decompressed but otherwise byte-identical to what renders today**, rewrite offset/size/compression/CRC, zero the old extent, `datcheck --preflight` + `--crc-sweep` + `--check-overlaps` before and after. Write the testing instructions; **do not launch** (standing rule). | Because the payload is byte-identical content, **any visual change is unambiguous evidence about the CONTAINER**. Three answers at once: does the client read a **1,514,855 B stored** row (currently backed by an **empty** population — retail's largest ordinary stored content row is 19,292 B); does it tolerate a row past the old EOF; does file extension work. **This rung settles the Route B contest** (§2.4) — its two skeptics disagree and this is the run both proposed. Recovery is a file copy. Confirm no other session holds the archive open (a `PermissionError` was hit mid-measurement). | 1 session + 1 run |
| **A6** | **The entropy accountant — kill the encoder before a matcher is written.** ~80 lines, no encoder, no bitstream. Instrument the existing decoder (`gwdat.py:349-385`) to emit **retail's own token stream** for row 11196 — per block, literal/length symbols, distance symbols, both table headers — then re-cost that same sequence under a from-scratch canonical-Huffman assignment plus the fixed meta-encoding, and compare to 1,029,564 B. | **Prediction stated first: it lands within 0.5% of 1,029,564 B.** This isolates the two risks the scouts merged: *can our Huffman + meta layer match ArenaNet's* (answered exactly, on tokens we did not have to produce) from *can our LZ77 matcher match zlib's* (not tested here). **Kill: if the accountant cannot reproduce retail's size to within a few hundred bytes on retail's own tokens, the encoder arc is dead.** | 0.5 session |
| **A7** | **`toolkit/mapdata/gwenc.py` + `test_gwenc.py` + the `datwrite` compression-8 arm.** Build the matcher **size-only first** (hash chain, min match 3, 32 KB window, lazy matching) against A6's accountant — no bitstream writer, no round trip — then the writer. Copy the constant stream header (lead bits 0, `first_four = 2`, 4000/4000). Alphabet 0..29. **`PLAN.md` §6.1 register row BEFORE the module exists**, plus THIRD-PARTY-NOTICES. `datwrite` gains a verb that writes `len(new)`, **keeps compression 8**, and CRCs the stored bytes (`restore`/donor path proves every mechanic, `datwrite.py:610-614`). | Hard bar, **CORRECTED 2026-08-18 — this row said `≤ 1,029,628 B` and that is the trailer-EXCLUSIVE figure from §1.1, while every A7a/A7b number is trailer-inclusive. The third recurrence of correction C-3's double-count, and this is the row a cold session reads AS the criterion.** The bar is **≤ 1,029,632 B trailer-inclusive** AND `gwdat.decompress` returns the original bytes. Met: 1,011,244 B, §12–§13. The falsifiable headline in the test is *our compressed size vs ArenaNet's stored size on N real rows*, which can go red. Round-trip over a strided corpus sample. `checks.Ledger` floor from a real green run; TESTS.md in the same commit. **Note the acceptance bar is a RATIO target, not a correctness target** — the success/failure boundary is inside deflate's own tuning range (§1.2), and a level-1-quality matcher misses by 122 KB. | 2–3 sessions |
| **A8** | **SUMMIT: a row THIS PROJECT COMPRESSED, read by the retail client.** Deploy the compression-8 in-place write of 15018 into the loopback build's archive; owner-driven caged run against our server per RUNBOOK. | The client loads the map with the modified archive, does not trip a `MdlLoad`/`MdlSeq`/`MdlAnim` assert (the assert vocabulary is the failure oracle — a crash names its line), and the authored animation is **measured**, not eyeballed. **Kill/keep:** if it fails, the run records **which gate fired** — that failure is itself the result. | 1 run |

**Summit: A8.** What it would prove is the thing nothing else in this stack can: **that our encoder's output is a stream ArenaNet's decompressor accepts, not merely one ours does.** Every route above stops at the same sentence — `datmove.py:62-68`, `datalloc.py:99-106` and `gwdat.py:81-84` each carry a version of it. `datcheck.py` contains **zero** references to compression codes, so no invariant we own can refute a conforming-but-wrong bitstream. **The client is the only oracle, and A8 is the only rung that consults it.**

**A5 is the second summit and it is cheaper.** If A5 says the client happily reads a 1.5 MB stored row past EOF, then A6–A8 are optional infrastructure rather than the arc's critical path, and the honest deliverable becomes "we can write anything, at the cost of a permanently inflated archive."

**Ordering rationale, stated because the dossier shows what happens without it:** A1 and A2 are both free reads that could end the arc, and **both were skipped by scouts who then costed six-session builds on top of the gap.** Route A's central unknown was a file in its own working directory. Route B's premise was `classify_runs`' conservatism read as geometry. A3 goes third because it fixes a measured unsafety (`plan_move` currently aims at a live container arena) that every subsequent rung would otherwise inherit. A6 goes before A7 because it is the cheapest test that can kill the encoder.

---

## 4. What we are not doing, and why

### 4.1 `nextStream` continuation — **BLOCKED**, and the evidence is strong

§2.3. Three predictions stated first, all three failed, scout and skeptic in exact numerical agreement on every load-bearing figure. **Do not re-derive this.** Making concatenation exist would mean modifying the retail loader — permitted under CLAUDE.md carve-out (3), but that is a client-modification arc, and it discards U7's whole premise that the **stock** client renders our data.

**One caveat that must not be lost:** do not read this as *"`nextStream` is useless."* It is load-bearing and fragile — it is the **only** thing that names 44,700 rows (zero of them file-id addressable), the client asserts `nextStream < count` at VA `0x93f0b8`, and the bijection is a corpus-wide invariant a bad write would break **silently**.

### 4.2 Relocating 15018 into a free run — **BLOCKED**, and it is arithmetic

The bar is **×0.9265 of ArenaNet's own output — beat them by 7.35% (75,708 B)**. Eighteen deflate configurations across two agents; the best (level 8/memLevel 8, 1,017,638 B) misses by 63,782 B. The relocation bar should stop appearing in this arc's documents. **The in-place bar (×1.0001) is the only one worth quoting.**

### 4.3 Route C's 14-row local defragmentation, as planned — **BLOCKED**

§2.5. Executed with the only allocator `datmove` has, it produces **zero net gain**: 4 of 14 rows best-fit back into the window being cleared and the final contiguous run is 1,029,632 B. The scout's table is only reproducible with a window-exclusion rule that exists in no module. **A rebuilt Route C — a `--verbatim` verb with its own planner, its own destination selection and a window-exclusion rule — is EXPENSIVE, not blocked**; but it is dominated by A4 and A5, it leaves the archive with 2.9 MB usable and the largest run still 953,856 B (single-use by the scout's own admission), and it multiplies exposure to `classify_runs`' container heuristic by fourteen across destinations that have **never been sabotage-tested at that scale** (12 of 14 are under 64 KB; the heuristic was validated against the 6 large generations).

### 4.4 Reaching for `dat_study_38833`'s 2,892,800 B run — **BLOCKED, twice over**

Two independent reasons, and they are worth writing down together because each alone looks surmountable. **(a)** It moves the build pin as a side effect, against the owner's standing decision to stay at 38797 — both the Route D scout and the Route D skeptic flagged this without prompting. **(b)** §1.5: **100.0% of that run lies inside a stale MFT generation's declared extent.** It is a detector bug, not free space. `plan_move` accepts it today and the archive would look clean right up until the client rotated its table back onto our payload.

### 4.5 Routes scored BLOCKED on evidence that deserves a second look

Over-refusal is this project's documented direction of error, so this subsection is mandatory.

- **`datalloc`'s growth refusal is the one to reopen.** It is scored on a **wrong reason** (**C-5**: growth *is* revertible, one journal field and one syscall), and the client itself grows the archive by up to 2,286,592 B during ordinary offline play — **1.5× the payload this arc needs.** The refusal may still be *right*, but for reasons the docstring does not state: the u32 ceiling (**C-7**, 93 MB away on the 38833 line), the concurrency race (a live `PermissionError`), the `mapchunks` cache invalidation, and the fact that an unregistered appended row sits in a region the client is entitled to reuse. **Amend the docstring to say the real reasons, or the next cold session will refuse growth for a reason that is false and skip a route that is merely expensive** — the exact failure mode CLAUDE.md's provenance and toolchain carve-outs were both written to correct.
- **A literal-only Huffman encoder (no LZ77 matcher) was never costed for ratio.** It is a fraction of A7's cost and its ratio can be measured in an afternoon. Nobody has a number for it on this payload. Fold it into A6.
- **Displacement (§2.3) is not blocked and is not on the ladder as its own rung**, because A4 dominates it. But **117 rows already reserve ≥ 1,514,855 B**, `datwrite.replace` writes into an existing reservation today with zero new code, and displacing a retail asset is this project's own install pattern (`datalloc.py:5-8`). If A1 and A4 both fail, **this is the fallback and it needs no new module** — at the price of one retail asset dead in the loopback copy, the same price map 143 already paid.

---

## 5. Durability — what a bad write actually costs

**This section answers the question [studies/datwrite/FINDINGS.md](../datwrite/FINDINGS.md)
named as decisive and left open**: *"we do not know whether a botched write is recoverable
— the 'Repairing corrupt archive' rescan was located but not followed to completion."* It
has now been followed to completion, attacked by an independent skeptic who re-disassembled
every load-bearing address, and cross-checked by the orchestrator against `asserts.py`.

It belongs in this arc rather than that one because **it is route-independent**. Every rung
in §3 writes to a 4.2 GB file the owner cannot casually re-download, and the risk budget for
all of them is set here.

**All addresses are build 38797** (`vault/client/2026-07-29_221c13772c7a/Gw.exe`, the pinned
pristine client). `C:\gw` is 38833. ArenaNet's own assert line numbers are the stable anchors
for re-deriving: `ExeArchive.cpp` 1558, 1561, 2592, 2615, 2661, 2665, 2679, 2718, 2725, 2727.

### 5.1 "Repair" means DISCARD, not rebuild

**OBSERVED.** The repair is two phases, and ArenaNet's own asserts name both:
`progressNumer < progressDenomForScanMft` (`ExeArchive.cpp:2615`) and
`progressNumer < progressDenomForScanMft + progressDenomForScanFiles` (`:2679`).

**Phase 1, ScanMft** reads the whole file in 1 MiB blocks, steps each block at `blockSize`
stride hunting the descriptor magic `0x1A74664D` with `+0x08 == 0` and `count >= 16`, hands
each hit to `LoadMft`, and keeps the candidate whose `+0x04` flush counter is **strictly
highest**. It is a brute-force hunt for the newest **surviving** MFT generation. It does not
synthesise one, and nothing anywhere reconstructs the `fileId → mftIndex` map from payload
contents.

**Phase 2, ScanFiles** is the destructive half. For every row from `INDEX_FIRST_FILE = 16`
upward carrying `FLAG_ENTRY_USED`, it reads the payload, CRCs it incrementally, and compares.
On a match the row is kept. **On a mismatch it walks the `nextStream` chain back to the
`FLAG_FIRST_STREAM` head and deletes the whole chain** — frees every extent, memsets every
24-byte MFT row, pushes the indices onto the spare stack, and drops the file-id record.

**One wrong CRC costs the entire file, not the bad row.** A row whose extent runs past EOF,
or a `USED` row of size 0 with a nonzero stored CRC, computes CRC 0 and is deleted the same
way — the accumulator is seeded 0 and the read loop is skipped.

Rows 0–15 are never touched: the loop start is clamped to 16, so the file-id table and the
MFT itself are outside ScanFiles' reach.

**The one piece of good news, and it is the whole basis for calling this PARTIALLY
recoverable:** nothing on this path truncates or shortens the file. Deleted payload bytes
remain physically on disk, merely unreferenced.

### 5.2 The real danger is the branch with no log line

**OBSERVED, and this is the finding that matters most.** There are two failure classes at
open and they behave completely differently.

**Class 1 — header gates, which do NOT repair.** File under 32 bytes, MFT magic mismatch,
`headerSize < 0x20`, `blockSize` zero / not a power of two / out of range, and **the 12-byte
header CRC**. All of them return 0 from a six-instruction tail at `0x0047BE38` that contains
**no logging call at all**. That zero funnels into `ArchiveOpen`, which — with the write bit
set — jumps to `ArchiveCreate` and **writes a fresh empty 16-row archive over your 4.2 GB
file**. Silently.

**Class 2 — MFT-level triggers, which do repair**, logging `Repairing corrupt archive`:
`mftSize == 0`; any `LoadMft` rejection (stride, count, extent past EOF, descriptor magic,
descriptor+8, descriptor+0xC, **the MFT self-CRC**, offsets block-aligned and in range, and
every `nextStream` link in `[16, count)` and acyclic by a genuine Floyd tortoise/hare); a
missing file-id directory stream; the reconcile returning 0; and **the dirty flag** — bit 1
of the u32 at header `+0x1C`, which diverts an otherwise clean open into the repair.

**The skeptic's correction, and it makes this worse rather than refuting it:** a **failed
repair returns zero through the same funnel.** If ScanMft finds no surviving MFT generation
that validates, it falls to `xor edi,edi` and returns 0 — indistinguishable at the call site
from a bad header CRC, and landing on the same `ArchiveCreate`. **There are two routes to
total directory loss, and the second is entered from the class that otherwise survives.**

Verified independently by the orchestrator with the project's own stdlib tool, no
disassembler involved: `asserts.py --at 0x0047B650` returns exactly the `ExeArchive.cpp` line
set above, and `--callers` confirms the single funnel — one direct caller of the validating
open, and **zero** callers of `ArchiveCreate`, because it is reached by a jump rather than a
call.

### 5.3 It persists after one launch

**OBSERVED.** The repair path tests `ArchiveOpen`'s third argument (the write bit), asserts
`!m_dirty` (`ExeArchive.cpp:2725`) and `m_writeState == STATE_READY` (`:2727`), calls
BeginModification, and **calls Flush**. The adopted MFT, the file-id table and the header are
persisted. The deletions are permanent on disk after **one** launch.

**Therefore the operational rule is: never launch the client on a suspect archive. Diff it
first.** One launch converts a diagnosable state into an executed deletion.

The one inference in this chain, labelled as such: that the WRITE bit is set for `Gw.dat`
rests on the client demonstrably writing rows during play (`studies/datwrite` §5/§6, OBSERVED)
plus the write callback being installed only on a writable open — not on reading the constant.
The open-mode flags were not chased to the top-level call site. Note the direction: if this
inference is **wrong**, failures return NULL cleanly and everything here is **safer**. Nothing
unverified props up the optimistic reading.

### 5.4 Six generations survive — measured, and it is not a backup

**OBSERVED (orchestrator, read-only scan of `vault/dat_study/Gw.dat`).** Nobody had run this,
and the whole severity assessment turns on it: ScanMft can only recover if an older MFT
generation actually exists in the file.

Scanning all 8,200,175 512-byte-aligned offsets for the descriptor magic with `+0x08 == 0`:

| offset | `+0x04` flush counter | rows | |
|---|---|---|---|
| `0xF8BEFE00` | 26,881 | 177,342 | **live** (matches the header's `mftOffset`) |
| `0xF940E200` | 26,880 | 177,342 | |
| `0xF8FFF000` | 26,879 | 177,342 | |
| `0xF981D400` | 26,872 | 177,342 | |
| `0xF57D5000` | 13,101 | 176,874 | |
| `0xF8699A00` | 8,735 | 176,489 | |

**Six candidates, all six passing ScanMft's shape gate.** The four most recent cluster at the
end of the file, which independently corroborates `studies/customarea` FINDINGS 18.9's reading
of the tail run as a **shadow MFT rotation region rather than free space**.

Three things this does and does not mean:

- **It does** mean MFT damage is not automatically fatal — the recovery mechanism has material
  to work with, and the ArchiveCreate wipe is a second-order risk rather than the default.
- **It is not six restore points.** Adopting generation 26,880 gives a directory one flush
  stale while the data on disk is current; rows written since are unreferenced, and ScanFiles
  then CRC-deletes whatever no longer agrees. It is a rollback with teeth.
- **The scan is an UPPER BOUND.** It checks ScanMft's shape gate only, not `LoadMft`'s full
  validation (self-CRC, alignment, `nextStream` range and acyclicity). Some candidates may not
  survive it.

**Consequence for the ladder: never allocate into the rotation region.** A writer that
overwrites the shadow MFTs destroys the client's own recovery material — the one thing standing
between a bad MFT write and the silent wipe. This is a hard constraint on Routes B and C, and
`datplan`/`datalloc` do not currently know about it.

### 5.5 Two errors in our own documents, both in the dangerous direction

- **`studies/datwrite/FINDINGS.md`: "Any failure logs `Repairing corrupt archive`" is FALSE**,
  and it is the sentence most likely to get someone hurt — it teaches a reader to treat silence
  as safety when silence is the catastrophic branch. Corrected in that file, in the same commit
  as this one.
- **The `blockSize` bound is stated as `<= 0xFFFF`.** The gate is `ja` on `blockSize - 1`, so
  the maximum **accepted** `blockSize` is `0x10000`. Immaterial to any current plan, wrong if
  encoded into a checker.

A third, recorded here because it will bite a re-derivation on 38833: the header magic gate is
a **computed** constant (`call` + `add 0x1a4e4132` + `cmp`), not a literal — unlike the
descriptor magic and the ScanMft probe, which are literal `0x1A74664D`. Anyone searching for a
literal there will fail to find one.

### 5.6 The standing operating procedure

Adopted as this arc's working rules. `--preflight` costs **1.7 seconds** on the real
4,198,489,600-byte archive, so there is no cost argument against any of this.

1. **Never launch any client at an archive that has not passed `datcheck --preflight` in the
   same shell minute.** The launch is the irreversible step, not the write.
2. **Treat the 32-byte file header as the crown jewels, above the MFT.** Bytes `0x00..0x0C`
   and the CRC at `0x0C` are the only region whose corruption triggers the silent wipe.
   `datwrite.py` never touches them and must never gain a mode that does — an explicit refusal,
   not merely an absence.
3. **Confirm a surviving MFT generation exists before risking one** (§5.4). Nothing in the repo
   checks this today; it is rung A3.
4. **Extend the pre-flight to the four repair triggers it misses**: MFT self-CRC (currently only
   in `datwrite --verify`), descriptor `+0x08`, `nextStream` range and acyclicity, and the
   header's own `mftOffset + mftSize` against file size.
5. **Add a full per-entry payload CRC pass**, because ScanFiles turns every stale CRC into a
   whole-file deletion the moment repair fires for an unrelated reason. `test_datcrc.py --full`
   computes it but is a test, not a gate.
6. **Run `datcheck --diff` against a pre-launch snapshot after every session.** No checksum in
   the archive can detect a relocation or a ScanFiles deletion — the post-repair archive is
   fully self-consistent. A 24-byte MFT diff is the only instrument that can tell you a row was
   eaten.
7. **Never revert by byte offset after a repair.** `datwrite --revert` would write the old
   payload to an extent nothing points at any more and report success.
8. **Take the backup.** 3.91 GiB against 316.8 GB free, seconds on this NVMe. For a bad header
   write it is the *only* net — `ArchiveCreate` is unrecoverable by any tool in this repo.
9. **If an archive is already suspect, copy it and inspect the copy offline.** Do not launch to
   find out what happened.
10. **Do not pass `-repair` on any real archive.** It is still untraced to a handler, and since
    the one confirmed silent-wipe branch is `ArchiveCreate`, that is not a flag to characterise
    empirically on a file this size.

### 5.7 What is still open

Recorded rather than smoothed over.

- **The write-back is read from BeginModification + Flush semantics, not from a traced write
  syscall.** The last hop is an indirect call through a slot no literal in the image
  initialises. The experiment that would settle it is designed and is deliberately **not**
  scheduled here: corrupt one expendable non-map row's payload CRC on a **throwaway copy**, set
  bit 1 of `0x1C` to force the repair, snapshot, launch once, diff. Prediction stated in
  advance: the log gains `Repairing corrupt archive`, the session is slow, and that row plus
  every partner in its chain is memset with its file-id record gone, while every other row is
  untouched. **Do not run any variant that touches header bytes `0x00..0x0C`** — that arm has no
  diagnostic value and destroys the archive silently.
- **`-repair` remains UNVERIFIED.** The wide string is referenced from a `{id, flags, namePtr}`
  table where `repair` carries id `0x29` and flags 0 (most neighbours carry `0x300`); id `0x29`
  was not followed to a handler.
- **The reconcile at `0x0047BE50` was not read this pass** — its behaviour is taken from
  `studies/customarea` FINDINGS 18.4 and is CORROBORATED, not re-derived. It is in the trigger
  list on the strength of its return value being tested, which was read.
- **Whether a salvage tool could rebuild deleted rows is untested.** The bytes survive and the
  container magics are scannable, but the `fileId → mftIndex` association lives only in the
  file-id table, so a salvage pass recovers **content without addressing**. Nobody has tried and
  it should not be priced as cheap.
- **Every VA here is 38797 and `C:\gw` is 38833.** Nothing was re-derived against 38833.

---

## 6. The decision the owner actually faces

**Recommendation: run A1 and A2 before anything is built, and expect them to change the arc.** Both are free, read-only, half a session each, and either can end it: A1 may show that the hatcher's animation is *already* addressable as fifteen separately-loaded files — in which case adding a sixteenth is transparent, nothing needs compressing, displacing, shrinking or repinning, and the 1.5 MB wall was never a wall but a description of one row we chose to rewrite. A2 may show that a realistic 1% retime overflows the reservation by 4,993 B — in which case the compression-8 encoder cannot deliver the thing it would be built for, whatever its quality. **The honest cost if both survive is 4–6 sessions to a working `gwenc.py`, and its payoff for file 15018 alone is between 68 and 3,732 bytes of authoring budget** — a route whose success criterion is *matching ArenaNet's own compressor on ArenaNet's own data to within 64 bytes*, with the pass/fail boundary sitting inside deflate's own tuning range and no fallback if it lands short. The encoder is still worth building eventually, but for the archive-wide reason (**121,139 rows cannot be rewritten stored in place**), not for this creature. **The one thing that would change the recommendation is A5:** if the retail client will read a 1,514,855-byte *stored* row placed past the old EOF, then the wall dissolves for every route at the cost of a permanently inflated archive, and the ladder collapses to A3 + A5 + a growth verb with a u32 guard. That population is currently **empty** — retail's largest ordinary stored content row is 19,292 B, and our one precedent is 29,802 B — which is exactly why A5 is one caged run, on a copy, with a byte-identical payload so the answer cannot be confounded by content.

---

## 7. A2 — RUN 2026-08-17. **GREEN**, and the rung as written tested the wrong edit

**OBSERVED (orchestrator), read-only.** A2 asked whether a realistic edit still fits file
15018's own 1,029,632 B reservation, using `zlib` raw deflate as the optimistic proxy —
a kill gate for the in-place compressed route, needing no encoder.

**It does not cross. In any direction tested.** The route is not entropy-limited.

### 7.1 The baseline, and a number worth pausing on

Sweeping 16 raw-deflate configurations (levels 6–9 × memLevel 8–9 × default/filtered), the
best is **1,017,634 B** at level 8 / memLevel 8 / default — **11,994 B under the budget**
(reservation less the 4-byte trailer).

**That is 11,930 bytes SMALLER than ArenaNet's own output of 1,029,564 B.** The stdlib
beats retail's compressor on retail's own payload by 1.2%. The §1.1 framing of the bar as
"match ArenaNet within 3,732 B" was itself pessimistic — it came from `zlib -9`/memLevel 9,
which is *not* the best configuration, and choosing the level by its number rather than by
measurement cost 8,262 B of apparent headroom. **This does not make the encoder free** —
`gwenc.py` must hit this in the *compression-8* format, not deflate, and A6 is still the
rung that tests that. But the bar is a ratio ArenaNet themselves did not reach.

### 7.2 The rung as specified tested the smallest possible edit

Retiming through `skelwrite.scale_sequence_keytimes`, the seam A2 named:

| sequences retimed | key slots moved | deflate | vs baseline |
|---|---|---|---|
| 1 of 237 | 0 | 1,017,634 | +0 |
| 24 (10.1%) | 5 | 1,017,645 | +11 |
| 128 (54.0%) | 72 | 1,017,651 | +17 |
| **237 (100%)** | 167 | 1,017,641 | **+7** |

**Retiming every sequence in the file costs seven bytes.** The reason is structural and it
invalidates the rung as written: **the key table is 173 int32s — 692 bytes of a 1,514,855 B
payload.** At most 0.05% of the input can move. A gate that cannot perturb its input is not
a gate, and this one would have reported GREEN without testing anything.

**This refutes the dossier's elasticity figures** (+806 B at 0.1% of slots, +8,725 B and
overflowing at 1.0%). Those numbers are not reproducible here and cannot be right in the
direction claimed: 692 bytes of moved input cannot cost 8,725 bytes of deflate output.
Recorded as **CONTESTED → refuted**; the ladder's A2 row should be read as superseded by
this section.

### 7.3 The honest version: edits that touch the curves

The mass is in the channels — 86 nodes, **76,008 curve samples** (node 1 alone carries 1,437
rotation quaternions and 2,853 translation vec3s). An authored animation rewrites *those*.
Two edits, applied to the first *n* nodes, FA1 length identical throughout so this is purely
an entropy test:

| edit | 5% of nodes | 25% | 50% | 100% |
|---|---|---|---|---|
| **SCALE** — translations ×2 (the curve-space form of what U7 shipped on node bases) | −11 | −18 | −27 | **−21** |
| **REQUANT** — every float snapped to a 1/1024 grid (a from-scratch exporter's output) | −32,395 | −154,256 | −293,374 | **−467,928** |

All FIT, with margin growing rather than shrinking.

**PREDICTION STATED BEFORE THE RUN, AND REFUTED.** I predicted SCALE would be nearly free
(correct — multiplying a smooth curve by a constant leaves it smooth) and that **REQUANT
would be expensive and might overflow**, on the reasoning that re-rounding destroys the
byte-level regularity deflate exploits. **That is backwards.** Coarser quantization makes
the mantissas *more* repetitive, not less: requantizing every curve in the file compresses
it **46% smaller than retail ships it**. I had conflated "not retail's exact bytes" with
"less regular", and the adversarial case turns out to be the compressible one.

The residual risk this leaves is the opposite of the one A2 was written to catch: not that
an authored payload is too large, but that a *higher-fidelity* one — more samples, finer
grids, denser keys — could be. Nothing measured here bounds that, because every edit above
preserves the sample **count**. **A2's real successor question is whether an authoring
pipeline may add samples, and at what rate the budget is consumed.** It is not on the
ladder and it should be.

### 7.4 Verdict

**A2 is GREEN and does not kill the arc.** The in-place compressed route survives every
edit class tested, with 11,994 B of headroom before any edit and more after most of them.
The encoder's difficulty is *format conformance* (A6, A7), not ratio.

---

## 8. A1 — RUN 2026-08-17. **PER-FILE, the selector is NAMED, and the encoder leaves the critical path**

**Method: blind replication**, the owner's standing pattern for a contested reading. Two
researchers attacked from opposite ends — one the client binary, one the archive corpus —
each assigned ONE hypothesis and told to **refute** it, neither shown the other's
assignment or answer. Then an adjudicator, then a skeptic. **Both blind agents independently
returned PER-FILE**, and the one assigned "GLOBAL" refuted its own hypothesis.

### 8.1 The answer

**[OBSERVED] The sequence index space is PER-FILE, and the selector is a byte in the
sequence record.** Disk record stride is 23 (`0x17`); runtime is 32. The FA1 parser
**deliberately swaps the first two fields**: disk `u32@+0x01` (the KEY) → runtime `+0x00`,
and disk `u8@+0x00` (the SELECTOR) → runtime `+0x04`.

```
007965A0  mov   eax, [edx-4]        ; disk +0x01  ->  runtime +0x00   (the KEY)
007965A6  movzx eax, byte [edx-5]   ; disk +0x00  ->  runtime +0x04   (THE SELECTOR)
```

At `MdlAnim 0x007822F0` that selector is read as a **1-based** index into the model's FA8
link array (`[edx+0x114]`); zero means "this file". The index that reaches it is bounded by
**one file's own count** — `MdlSeq:300` `seqIndex < m_skel->m_seqCount` at `0x00792F38`,
five more sites at `MdlSeq:430/503/582/606`.

**The strong form of the refutation is at the layer where an index is BORN, not where it is
consumed.** The key lookup `0x00792DC0` is a textbook `std::lower_bound` over exactly one
file's array, bounded by that file's `m_seqCount`. It never touches `+0x114`, never touches
the link array, and has **no fall-through** to linked files. Arguing PER-FILE from *not
finding* a load-time merge was the weak form; this is the strong one.

And the runtime record is now **fully enumerated** — `+0x00, 04, 08, 0C, 10, 14, 18, 1C`,
every slot written by that one parser loop. **There is no field left that could carry a
global base, a file id, or a cross-file offset.** That is a closure argument, not an absence.

### 8.2 The evidence, with its controls

| test | result | control / rival |
|---|---|---|
| `links[sel-1]` (1-based) vs `links[sel]`, all 252 shells, all 31,700 nonzero-selector records | **31,700 / 0 — 100.0000%** | 0-based rival **0.82%**; random-other-link null **8.06%** |
| Every FA1's sequence array non-decreasing in `u32@+0x01` (required for `lower_bound` to be correct) | **3,000 / 3,000 files, 40,226 sequences, zero violations** | sorted by `u32@+0x0F` 91.1%; by `start` 58.9% |
| Every linked file's sequence ids also declared by its parent shell | **2,467 / 2,467, coverage exactly 1.0** | rare-id subset 89/89 at 1.0; a random **different-skeleton** shell scores **0 of 89** (median 0.303) |
| `max(u8@+0x00) <= that file's FA8 record count` | **0 violations / 252** | max **equals** the link count on 19 of 19 sampled — tightest margin 0 |
| Files with no FA8 carry selector 0 everywhere | **all 35,399 sequences in 14,319 files** | closed by subtraction, not sampled — 31,700 nonzero in the 252 matches the independent full-population sweep exactly |

**OBSERVED (orchestrator), reproduced from the archive directly:**

| file | records | selector histogram | distinct keys | sorted by key |
|---|---|---|---|---|
| **116228** shell, 15 links | 242 | `0:2, 1:110, 2:3, 3:2, 4:1, 5:13, 6:7, 7:39, 8:20, 9:1, 10:6, 11:14, 12:9, 13:4, 14:6, 15:5` | 224 | ✅ |
| **15018** link, 13 links | 237 | `0:110, 1:4, 2:2, 3:1, 4:13, 5:7, 6:39, 7:20, 8:1, 9:6, 10:15, 11:9, 12:4, 13:6` | 219 | ✅ |
| **116366** worm, 0 links | 10 | `0:10` | 10 | ✅ |

Max selector equals link count in all three. Lay the two histograms side by side with a +1
shift and the structure is plain: **the shell's table is 15018's entire table re-based by
+1** (110↔110, 2↔2, 1↔1, 13↔13, 7↔7, 39↔39, 20↔20, 1↔1, 6↔6, 9↔9, 4↔4, 6↔6, two records
dropped) **plus the shell's own 2 and 5 from link 169533**.

### 8.3 The 242 puzzle is settled, and the old explanation is dead

**242 = 2 + 110 + 125 + 5.** A curated re-index of the whole link graph, not a
concatenation and not a subset. **This kills `242 = 237 + 5`**, which §1.6 carried as a
RECONSTRUCTION — and no arithmetic identity exists to find in its place: sibling shells
82929/82795/18934/82935 declare 246/243/248/246 against link sets each summing to exactly
627.

### 8.4 What it means for the arc — the encoder leaves the critical path

**Adding a 16th FA8 record is NECESSARY, SAFE, and INERT.** Safe and inert is measured, not
assumed: **retail itself ships 410 unselected links across 63 shells**, so an unreferenced
FA8 record is attested 410 times and what the client does with it is nothing. Playback
additionally requires **new sequence records in the shell's own FA1 carrying selector 16**.

**So the file that must be rewritten is the SHELL — 116228, row 13738, 29,802 B decompressed
/ 20,236 B stored in a 20,480 B reservation. Retail's 1,029,564 B link 15018 is never
touched.** U7 already rewrote this exact shell successfully. **The 1.5 MB wall does not arise
on this path at all**, and Routes A and E (the compression-8 encoder) drop off the critical
path for this arc. They remain real and EXPENSIVE for the archive-wide reason; they are no
longer blocking.

Named cost so nobody re-derives it: the shell's FA1 runs **121.9 B per sequence** against
**244 B of stored headroom**, so roughly 2–4 appended records fit before the row must
relocate — and relocating a ~20 KB row is the easy case.

### 8.5 The experiment this hands A4, and it is close to ideal

`0x00804240` is **not a lookup — it is a variant picker**, and the `AvChar:8212` call site
passes a literal `push 0`, so **the client picks uniformly at random among all sequences
sharing a key**. The shell has 242 records over 224 keys, run sizes `{1:216, 2:4, 3:1, 4:1,
5:1, 6:1}` (reproduced above).

**Therefore: append a record carrying an EXISTING key and selector 16.** It joins that key's
equal-key run, and with 216 of 224 keys currently single-variant, a new record on one of them
gives a **50/50 coin flip between retail's animation and ours on every play** — a
self-controlling, unmistakable client-run oracle, with no invented key, no wire question, and
no dependence on what fills the agent's key array.

**A hard authoring constraint, and it must reach the A4 rung text:** the array is
`lower_bound`-searched, so it **must stay sorted by `u32@+0x01`**. A new record is
**inserted in key order, never appended** — a tail append with a low key silently breaks the
binary search for every key after it. Its `lo`/`hi` pair indexes the key-time array and must
stay consistent.

### 8.6 Corrections to standing findings

- **§1.6 above: `242 = 237 + 5` is dead** (§8.3). It was labelled RECONSTRUCTION and is now
  refuted with the exact decomposition.
- **[CONTESTED → retract] `studies/anim/FINDINGS.md`'s "592 files carry indices ≥
  `m_seqCount` … keyed by a linked model's larger sequence space".** In a 2,500-head sample
  all 149 out-of-range values are exactly **65,536 = `0x10000`**, 110 of 149 terminal in the
  sorted array — **a sentinel above any real count** (the largest union measured anywhere is
  627), not a cross-file index. Independently supported here by 0 genuine out-of-range
  selectors across 252/252 shells. The `0x0078007F` link-array mechanism named in that same
  row is correct and is now corroborated; only the "larger sequence space" reading is wrong.
- **A1b is downgraded, not cancelled.** The remaining unknown is real —
  `schema/messages.json` contains **zero** occurrences of `anim`, `sequence`, `seq`, `emote`
  or `gesture`, so *"the server tells the client to play sequence N"* was an assumption of
  the A1 question rather than a measured wire fact. But §8.5's existing-key path does not
  depend on it, so **A1b no longer blocks A4**. Its real target is who fills the per-agent
  key array at `+0x2C`/`+0x34` (`0x007F1AD0` is `rand() % [this+0x34]`, a uniform pick — not
  a state producer).

### 8.7 What would reopen it

Recorded rather than smoothed. (1) A writer of `m_skel+0x6C`/`+0x70` outside the FA1 parser
allocating a merged array — scanned only in the `Engine\Model` band, and `codescan` cannot
see a displacement built in two steps. (2) **Depth-2 chains: 39 FA8 targets themselves carry
FA8**, and `studies/unitassembly`'s max-depth-1 is measured on the 54 *live* closures only,
which is UPSTREAM to this pass. (3) A wire capture showing a raw index rather than a key.

**Not tested by construction: no client was launched.** Whether retail actually plays a 16th
authored link is untested, and **the client remains the only oracle**. That is A4's job.

---

## 9. A3 and A4 — BUILT 2026-08-17. The edit is 29 bytes, and it is waiting on one run

### 9.1 A3, the route-independent safety fixes

Seven items, each with a test that can go red. Floors from real green runs:
`test_datcheck` 84 → 112, `test_datwrite` 78 → 87, `test_datplan` 38 → 44.

| item | what it was | measured after |
|---|---|---|
| **C-7**, `archive.py` `<I` → `<Q` | two of three readers said u64; the outlier was the one every tool imports, and it silently **capped archive growth** | proving it needs no 4 GB file — set the high dword and require the failure to name the full offset, since a `<I` reader truncates, finds the MFT where it always was, and reports success |
| **`datcheck --generations`** | nothing in the repo could count the client's own recovery material | **6 generations on the real archive**, counters 26,881 → 8,735, in **3.4 s**. Reported as an UPPER BOUND (ScanMft's shape gate, not LoadMft's full validation) |
| **`datcheck --crc-sweep`** | a stale payload CRC is invisible to all ten open-time rules and then costs the whole `nextStream` chain | **177,327 payload CRCs recomputed, all matching, 2 structural rows skipped by name, 2.4 s.** 177,327 chances to be wrong is also the evidence the sweep reads rows correctly |
| **`--diff` compares `size_on_disk`** | `snapshot()` had recorded it since it was written and `diff()` never looked, so an archive that **grew** read as unchanged | the control asserts appending past every extent changes **no MFT row** — which is why nothing else could have caught it |
| **`datwrite` refuses `[0x00,0x10)`** | protected by **absence**: no caller wrote there, so nothing checked | tested by reaching for it at every field and at **both sides** of the `0x0F`/`0x10` boundary, each attempt on its own fixture |
| **`datplan` projects declared extents** | a mark is where a signature *sits*; the header says how far the table *reaches*, and a generation running off the end of its run left the next run scoring usable | four of six new checks are controls, because a projection that swallowed everything downstream would withhold the archive and protect nothing |

**One item was removed after a single test run, and the fixtures were right.** The
generation census was briefly a pre-flight item; `build_archive` writes one MFT and is
perfectly healthy, so it turned every synthetic archive red and broke nine isolation
checks. **"Has a fallback" is a property of an archive's HISTORY, not its validity** — and
pre-flight costs 1.7 s precisely because it never reads a payload, which is worth more
than folding one more item in. `--generations` is its own verb, run before an archive is
*risked* rather than before it is *opened*.

### 9.2 A4, the additive path — `toolkit/mapdata/unitauthor.py`

**The edit costs 29 bytes.** On the real hatcher shell:

```
shell 116228 (row 13738)
  links 15 -> 16, new file id 389632 at selector 16
  sequences 242 -> 243, inserted at index 1
  key 805313525: 1 variant(s) -> 2
  container 29802 -> 29831 B (+29)
```

Two of the three things this must get right **cannot fail a checksum, cannot fail any of
`datcheck`'s ten open-time rules, and would present in-game only as "some animations
stopped playing"** — which is why the test is shaped the way it is:

- **The sequence array must stay sorted** by `u32@+0x01`, because the client searches it
  with `std::lower_bound` and an unsorted array silently returns the wrong run. Keys are
  inserted at the **front, middle and end** of the table — a tail-append implementation
  passes the last of those, so one key would not be a test — and §2b unsorts the table by
  hand to prove the refusal fires, with a control first asserting the sabotage really does
  unsort it.
- **The FA8 list is positional.** `links[sel-1]` is how every existing record resolves, so
  the check is that the prior list is a **prefix** of the new one. A reordering breaks
  that; a length check would not notice.
- Archive legality is the ordinary third, and §4 exercises it on a synthetic fixture.

30 checks, floor 30. Sections needing the vault declare a printed skip.

### 9.3 What is NOT established, and it is the whole remaining risk

**No client has been launched.** Everything in §9.2 is archive-legal and self-consistent,
and *self-consistent is exactly the state the two dangerous defects above would also
produce*. `datcheck.py` contains zero references to compression codes and nothing we own
can refute a conforming-but-wrong result. **The client is the only oracle**, and the run
is A8's job, on the owner's go-ahead.

Specifically untested: that the client reads a 16th FA8 record at all; that it accepts a
243-record sequence table; that our appended record is picked as a variant; and that a
**stored** 29,831 B shell in place of a 20,236 B compressed one is loadable — U7 proved a
stored `flags=515` row is acceptable at 29,802 B, so this is a 29-byte extrapolation of a
result we already have rather than a new question.

### 9.3b STAGED AND DEPLOYED 2026-08-17 — every machine-readable gate is green

The edit is in the pinned 38797 run archive
(`vault/run/2026-07-29_221c13772c7a/Gw.dat`), built by
`vault/research/archivewrite/a4stage.py` from `Gw.dat.retail`, which is preserved.
**Nothing was launched.**

```
shell 116228 row 13738: 29,802 -> 29,831 B (+29)
donor 222949 (11,878 B) duplicated as new file id 389632, registered
links 15 -> 16, sequences 242 -> 243 at index 1
key 805313525: 1 variant -> 2   (a 1-in-2 pick per play)

preflight   10 of 10 clear
generations 6 of 6 pass the shape gate
crc sweep   177,320 payload CRCs, 0 bad, 2 structural skipped by name
size        4,198,489,600 B (unchanged), 177,335 rows
```

**The diff is exactly two rows out of 177,335** — row 13738 relocated
`0x1A40CA00 → 0xA314A00` with compression 8 → 0, and row 35301 recycled from a
zero-size spare to the new file. Read back from the archive through the decoders:
16 links, 243 sequences, one record at selector 16, the array still **sorted**,
and the 1 MB link 15018 **byte-identical to retail**.

Two choices worth recording because they are not obvious:

- **The new file is a DUPLICATE of the shell's smallest existing link, not
  authored motion.** This rung asks whether the client accepts a 16th link and a
  243-record table; authored curves would confound it, because "nothing moved"
  could then mean *the client ignored our link* or *our curves were wrong*. Every
  byte in the new row is something the client already reads today, so a failure
  is unambiguously about the **addition**.
- **Flags are copied verbatim (`0x0203`), never synthesised**, per
  `studies/datwrite`'s measured conclusion that the high byte is unexplained by
  ArenaNet's own asserts and read differently by two upstreams. `extra_bytes` is
  0 because that field *is* the compression code under another name, and we write
  the donor's decompressed bytes — the same stored `flags=515` shape U7 already
  put on screen.

One coincidence flagged rather than left to surprise someone: **row 35301 is the
same row `studies/datwrite` observed the CLIENT filling** during a caged session.
It is no longer a spare — it is USED and named in the file-id table — so the
allocator's LIFO spare stack cannot hand it out again. Not a conflict, but the
next diff of that archive will show a row that document already discusses.

### 9.3c THE RUN HAPPENED — 2026-08-17. The client ACCEPTS the addition. The visual half is UNRESOLVED

**Owner-driven, watched remotely over RustDesk. `RUN VERDICT: PASS (target: map)`,
exit 0.** Capture-derived checkpoints, all eight green:

```
client: build 38797, 2026-07-29_221c13772c7a
        (chosen by BUILD and name, never by mtime; skipped 2026-08-13_64fae3b1369b)
cage:   ours build, cleared for 127.0.0.1
[PASS] t+ 14.5s  keyed / PORTAL_ACCOUNT_LOGIN / login accepted / game instance
[PASS] t+ 15.8s  client requested its spawn
[PASS] t+ 16.3s  body is in the map
```

**WHAT IS SETTLED, and it is the rung's whole point.** The retail client **loads an
archive carrying a 16th FA8 link and a 243-record sequence table, reaches the map, and
spawns**, with **no `MdlLoad`/`MdlSeq`/`MdlAnim` assert and no crash**. The hatcher rendered
and animated throughout. Every named rejection risk for the additive path is **REFUTED**:
the 16th link is accepted, the enlarged sequence table is accepted, the relocated 29,831 B
**stored** shell is accepted, and the newly allocated row at file id 389632 resolves. A4's
acceptance criterion is met **at the client**, not merely on disk.

**WHAT IS NOT SETTLED.** Whether our record was ever *picked*. The owner's report is *"mostly
the hatcher doing the raised-arm cast animation; sometimes it feels altered but I'm not sure"*
— which is **not a verdict**, and the fault is the experiment's, not the observer's.

**Two design errors, both mine, both recorded so the next run does not repeat them.**

1. **The signal was too small to see.** The variant sat on **1 key of 224**, so the creature
   had to happen to play that one animation, and the replacement was a *duplicate of another
   working file* — motion that looks broadly plausible even when picked. U7 made the same
   mistake in the opposite direction and the fix is known: **change SHAPE, not timing or
   motion.** Scaling every node base is what produced U7's one-word report, *"deformed"*.
2. **The machine-readable half was lost.** `--shots` skipped **every** screenshot with
   `client not foreground`, so nothing was captured to measure against. A run whose visual
   evidence rests only on an impression has no evidence. **Check the shots actually landed.**

**Owner's instruction for every future visual rung, adopted:** spawn anything that must be
looked at **~150 units to the LEFT or RIGHT of the player, never in front** — the player's
own character model occludes it.

**THE NEXT RUN, designed but NOT run** (the session was stopped for RustDesk lag): make the
linked file a copy whose **node bases are scaled**, and attach the variant to **every
single-variant key** rather than one. Then whatever the creature plays, roughly half of
plays are ours and the difference is a gross deformation rather than a nuance. That is a
yes/no a viewer can call in one second over a laggy link.

### 9.3d RUN 2 IS STAGED, NOT DEPLOYED — the signal is now unmissable

Built by `vault/research/archivewrite/a4stage2.py` from `Gw.dat.retail`, staged at
`vault/exports/archivewrite/a4run2/Gw.a4run2.dat`. **Not deployed, not launched.**

```
donor 222949: 85 of 86 node bases scaled x3 (11,878 B, unchanged length)
link selector 16; 216 single-variant keys of 224 total
sequences 242 -> 458; shell 29,802 -> 34,776 B (+4,974)
216/216 of those keys now have exactly 2 variants
-> ~96% of this creature's animation keys are a coin flip

preflight 10 of 10 | generations 6 of 6 | crc sweep 177,320 payloads, 0 bad
size 4,198,489,600 B unchanged; diff is exactly 2 rows
```

**Both of run 1's design errors are addressed, one each.** Coverage: 216 keys instead
of 1, so the creature cannot avoid the modified branch by simply not performing one
animation. Amplitude: the new file's node bases are scaled x3 rather than duplicated,
so a pick is a *gross deformation* rather than plausible motion — the same edit that
produced U7's one-word report, "deformed", and the reason `feedback-make-the-signal-
unmistakable` says change SHAPE, not timing.

It uses a **different file id** (389633, not run 1's 389632) and is built from retail
rather than from run 1's archive, so the two experiments cannot contaminate each other.

**Prediction, stated before the run:** the client loads it — run 1 already proved the
16-link shape loads — and the hatcher is visibly deformed on roughly half its animation
plays. **If it looks entirely normal, our records are never being selected**, and the
per-file reading of the selector needs re-examining. That is a real result, and it is
the one thing run 1 could not deliver.

### 9.3e RUN 2 RAN — and it is a SUCCESS that reads like a failure

**Owner's report: "no deformation. half the animations are just him standing still."**

**HALF IS THE COIN FLIP.** Our record was selected roughly 50% of the time, exactly as
designed. **The additive authoring path reaches the client's animation picker**: the client
chose a sequence record we wrote, resolved its selector to a file we created, and played
from it. That is the thing runs 1 and 2 existed to establish, and it is established.

What was wrong is the playback WINDOW, and the cause is MEASURED rather than guessed:

- A record's `start`/`end` is a window on the timeline of **the file its selector names**.
  Run 2 copied the **shell's** windows (0 .. 22,883,332) onto records pointing at the
  donor, whose own motion lives in **0 .. 5,600,000**.
- **188 of the 216 windows we wrote sample a region where the donor has no keyframes.**
  The client samples empty space, so nothing moves.
- And the x3 bases never appeared because **a base is ADDED to a SAMPLED translation**
  (`studies/anim` 2.2). No sample, nothing to add it to — the creature stands in its rest
  pose, which is precisely what was reported. The two halves of the report are one cause.

**Retail's own rule, measured and unambiguous:** the shell's six selector-14 records carry
the donor's own windows, **6 of 6 exact**. A record pointing at link *k* must carry a window
valid on link *k*'s timeline. A1 saw this ("the shell's selector-k group is the same
(key,start,end) records as link k's own selector-0 group") and the run-2 design ignored it.
That is the error, and it is mine.

### 9.3f RUN 3 IS STAGED — real keyframes under every window

`vault/research/archivewrite/a4stage3.py` →
`vault/exports/archivewrite/a4run3/Gw.a4run3.dat`. **Not deployed, not launched.**

The fix keeps run 2's 96% coverage instead of narrowing to the donor's seven windows
(2.7%): **spread the donor's keyframes across the shell's whole window range.** Its 485
channel samples spanned 0 .. 5,600,000; scaled x5 they reach **28,000,000**, past the
shell's 22,883,332. Now every one of the 216 records samples something, and a sample is
all the scaled base needs in order to show.

```
channel times x5: 485 samples respread; 85 of 86 node bases scaled x3
links 16 (16th = 389634), sequences 458, 216 at selector 16, sorted
preflight 10 of 10 | generations 6 of 6 | crc sweep 177,320 payloads, 0 bad
size 4,198,489,600 B unchanged; 15018 and 222949 byte-identical to retail
```

Its own file id (389634), built from retail, so runs 1-3 cannot contaminate each other.

**Prediction:** the hatcher is visibly deformed on roughly half its animation plays. If it
still stands still, the window reading is wrong in some further way and the next move is to
narrow to the donor's own seven windows — correct by construction, at 2.7% coverage.

### 9.3g WHY RUNS 2 AND 3 FROZE — adjudicated, and my design was wrong at the root

Three independent lines (link-load, play-path, corpus), then an adjudicator that had to
explain **both** observations. Every figure below was re-measured read-only against
`vault/dat_study/Gw.dat` and the deployed run-3 archive, plus an independent 6,000-id
random sample (seed 1138) that reproduces the corpus rules at 100.0000%.

**H1 (the link never loaded) is REFUTED, and the refutation is clean.** `MdlAnim`
dereferences `links[sel-1]` with **no null check** (`mov edx,[eax+ecx*4-4]` then
`cmp dword [edx+0xB8],edi` seventeen bytes later), so a nulled slot would have been an
access violation on the first pick. Three multi-minute sessions, no crash. The file loads.
Compression is irrelevant on this path — `MdlLoad` never sees the field — and a link needs
no geometry, because the FA8 loop passes NULL for the mesh out-param.

**The failure happens BEFORE the selected file is ever sampled**, and retail's own
invariants say why. The ones I broke:

| rule | retail | run 3 |
|---|---|---|
| **(1)** key K must exist in link *k*'s **own** table | 31,700 / 31,700 | **209 of our 216 records violate it** |
| **(3)** equal-key runs are homogeneous — one key, one file | 0 mixed of 33,077 | **216 of 224 keys mixed** |
| **(4)** start/end/u32_0F/f32_13 copied verbatim from the link's same-key record | 31,700 / 31,700 | only 6 satisfy it |
| **(7)** the key table is a cursor tiled by records in array order | 252 / 252 shells | **92 cursor breaks** |

**Rule 3 kills the whole coin-flip design.** A key is served by exactly one file; variants
live *inside* that file. The A/B flicker I built three runs around is **unattested in
retail**, and no amount of tuning would have made it work.

**The decider, and it is why "no deformation" was the load-bearing half of the report:**
the node bases are **bone lengths** — per-node `|base|` spread 0.0003 across all sixteen
files, `sum|base|` = 3,928.2 in thirteen of them. Had the link's `blk2C` been read at all,
the hatcher would have been a 3× exploded skeleton on half of every animation. Not subtle.
It did not happen.

**Run 3 was strictly WORSE than run 2**, which I did not anticipate: scaling the new file's
channel times ×5 left its own seven records pointing at their original windows, so the file
became internally inconsistent and broke the six records that had been *accidentally*
rule-compliant in run 2.

### 9.3h RUN 4 STAGED — correct by construction, deterministic, two instruments

`vault/research/archivewrite/a4stage4.py` → `vault/exports/archivewrite/a4run4/`.
**Not deployed, not launched.** No inserts, no key-table edits, no coin flips.

- **A. GIANT.** Duplicate link 8 (file 96978, 214,868 B, same 86-node skeleton) with 85
  bases ×3, registered as FA8 record 16; then **flip one byte** on each of the shell's 20
  selector-8 records, 8 → 16. Because the duplicate's records are byte-identical to
  96978's, rules 1/4/5/6 hold **for free** and no run becomes mixed. Verified from the
  result: **rule 1 20/20, rule 3 0 mixed of 224 keys, record count unchanged, shell +6 B.**
- **B. TINY, and it is insurance.** Retail's link 14 (222949) rewritten **in place** with
  85 bases ×0.25. No shell edit — retail's own six selector-14 records already point there.

**Why two.** The base-scaling oracle has never itself been validated: U7 scaled a *shell's*
bases, and no run has proved that scaling a *linked* file's bases is visible. "No
deformation" is now carrying a lot of weight. Two instruments, opposite directions, both
deterministic. **If neither fires, the oracle is dead — and that is the finding.**

**Link 1 (15018, 110 keys, 45% coverage) is the better instrument and does not fit:** a
stored 1,514,855 B duplicate fits **0 of 212** free runs. The arc's original wall, met
again from the other side.

**Prediction:** ~26 of 242 animations change deterministically — 20 play a ~3× exploded
skeleton, 6 a shrunken one, the rest untouched. No crash, no assert, no `Model:` line.

### 9.3i RUN 4 WAS UNINFORMATIVE, AND THE VIDEO SAYS WHY — run 5 stops authoring

**The owner recorded the run** (`2026-08-18 10-29-49.mkv`, 13 s). Frames read directly
rather than inferred: the hatcher cycles **one** animation, the raised-arm cast, and both
models are normally proportioned — no x3 explosion, no x0.25 shrink. The owner's own read
("more to do with cast backswing/cast time than animation deforming") is correct.

**That makes run 4 UNINFORMATIVE, not negative, and the distinction is the finding.** Its
instruments covered 26 of 242 records; the cast is not among them. **Nothing in runs 1-4
has yet tested whether a linked file's node bases are used at all** — every run so far
either broke a rule or aimed at an animation the creature never performs.

**Run 5 therefore stops authoring entirely.** No new link, no sequence-record edit, no key
table, no shell change — the shell is verified **byte-identical to retail**. It rewrites
the hatcher's linked files **in place** with scaled bases and asks one question: does any
animation this creature plays change shape?

```
12 of 13 writable links rewritten (1 refused: 73940 needed 189,952 B, no run fit)
78 of 242 animation records (32%) now play a scaled skeleton
bases alternate x3 / x0.25 by link, so a fired instrument NAMES its file
shell byte-identical to retail; 15018 and 87333 untouched
preflight 10/10 | generations 6/6 | crc 177,319 payloads, 0 bad | size unchanged
```

**The two files we cannot write hold 149 of 242 records — 62% of this creature's animation
set.** A stored rewrite of 15018 needs 1,514,855 B and of 87333 needs 1,354,523 B against a
largest usable run of 953,856 B. **The arc's original wall, met for the third time and now
from the direction that matters**: it is no longer about one animation library we wanted to
edit, it is about most of the creature's animations being unreachable.

**This run is a clean either/or, which is what the last four were not.**

- **Something deforms** → linked-file bases ARE used, the oracle is alive, run 4's
  authoring path is sound, and the remaining problem is only reaching the right file.
- **Nothing deforms** → every animation the hatcher performs comes from 15018 or 87333, and
  the compression-8 wall is *provably* what blocks the arc. That converts a vague failure
  into a costed next step, and it is the single most useful thing this run can return.

### 9.3j RUN 5 CAME BACK NULL — and run 6 is the positive control I owed since run 1

**Owner: "deployed and ran it, still no deformation."** 32% of the creature's animation
records were playing from files whose bone lengths we had scaled x3 or x0.25, and nothing
changed shape.

**TWO READINGS SURVIVE, and only one of them is about the wall.**

- **(a) The cast comes from 15018 or 87333** — the two files we cannot write, holding 149
  of 242 records between them. This is the reading I had been favouring, and it makes the
  compression-8 wall the blocker.
- **(b) LINKED-FILE BASES ARE NEVER USED.** The rest skeleton is *replicated* into every
  animation file — `sum|base|` = 3,928.2 in thirteen of sixteen, measured — but replication
  is not use. If only the SHELL's copy poses the creature, then U7 (shell bases →
  "deformed") and runs 4–5 (link bases → nothing) are both exactly as predicted, and where
  the cast animation lives is irrelevant.

**I had been under-weighting (b), and it is the cheaper explanation.**

**Neither can be believed until the measurement chain is validated, and it never has
been.** Five runs have reported "no deformation" while resting on the assumption that U7's
oracle still works — a different archive, session and camera. **An assumption carrying five
negative results is exactly the thing to test**, and running a positive control first is
ordinary discipline that I skipped.

**Run 6 changes exactly one file: the shell, every node base x3.** No link, no record, no
new file — verified: all 15 links byte-identical to retail, 1 row changed, size unchanged,
preflight 10/10, crc 177,319 payloads 0 bad. It is U7's own edit, larger.

- **It deforms** → the oracle is alive, and with run 5's null result **(b) is CONFIRMED**:
  bone lengths come from the shell, links supply motion channels only. That is good news —
  the shell is 29,802 B and we can already write it, so the arc's authoring lever for shape
  exists and is reachable.
- **It does not deform** → the chain between our writer and the screen is broken, **runs
  1–5 are void**, and that is what to debug. Nothing else should be believed first.

### 9.3k RUN 6 FIRED — **bone lengths come from the SHELL only.** The oracle is alive

**Owner: "yep, extreme deformation now."** Screenshot: the hatcher exploded into splayed
shards, nameplate `Hatcher [Collector]` still on it. One file changed — the shell, 85 node
bases x3 — with all 15 links byte-identical to retail.

**Put beside run 5, this settles it.**

| run | what was scaled | records affected | result |
|---|---|---|---|
| 5 | **12 linked files'** bases, x3 / x0.25 | 78 of 242 (32%) | **nothing** |
| 6 | **the shell's** bases, x3 | all | **extreme deformation** |

**CONFIRMED (OBSERVED): the rest skeleton is REPLICATED into every animation file but only
the SHELL's copy is used.** `sum|base|` = 3,928.2 in thirteen of the sixteen files, and
that replication is not use. Linked files supply **motion channels**; the shell supplies
the **skeleton**. Reading (b) of 9.3j is confirmed and reading (a) — "the cast lives in the
unwritable files" — is **not needed to explain anything**.

**Three consequences, and the first is the one that matters.**

1. **The 1.5 MB wall does NOT block shape authoring.** The lever for a creature's
   proportions is its shell — 29,802 B, comfortably writable, already relocated and
   rendered four times today. What the unwritable files hold is *motion*, not *form*.
2. **The whole chain is validated end to end**: `skelfile` decode → typed repr →
   `skelwrite` encode → `rebuild_container` → `datmove` → archive → **retail renderer**.
   Every "no deformation" in runs 1–5 was a true negative about *linked bases*, not a
   broken pipeline. The control should have run first; it would have saved three runs.
3. **U7's summit is reproduced and enlarged** — same creature, same edit, bigger scale, a
   fresh archive built from retail.

**What runs 1–4 did establish, and it is not nothing:** the client accepts a 16th FA8 link
and a 243-record sequence table (run 1, no assert); our authored records ARE selected by
the client's own variant picker (run 2, "half the animations"); and retail's nine
record-shape invariants are now measured at 100.0000% with an independent sample (9.3g).
The additive path is archive-legal and reaches the picker. What has **never** been shown is
a linked file's *content* changing what appears on screen — because the only property we
tested in a linked file, the bases, is the one property linked files do not own.

### 9.4 The run, when it is authorized

Written now so the design is fixed before anyone is at the keyboard, per the standing rule
that a probe states its prediction first.

**PREDICTION.** The hatcher plays its animations as it does today, except that on the one
key carrying our variant it flips a coin: roughly half of plays show retail's animation and
half show whatever file 389632 contains. If the new link is unreadable, the expected
failure is an `MdlLoad`/`MdlSeq`/`MdlAnim` assert naming its own line — a crash that names
the gate is a *result*, not a lost run.

**Procedure.**
1. `datcheck --generations` and `--crc-sweep` on the run copy **before** anything (§5.6
   rules 1, 3, 4). Take the 3.91 GiB backup — it is the only net for a header write.
2. Author the shell, `datalloc` the new file, place both, `datcheck --preflight` +
   `--crc-sweep` + `--diff` against a pre-write snapshot.
3. Owner launches the caged loopback client per `RUNBOOK.md`, with a **retail control
   first** — U7's third false start was three things animating at once, and its second was
   a server bug that only became visible when the retail control failed identically.
4. `datcheck --diff` after exit. **Never launch on a suspect archive** (§5.3).

**The one thing to get right that is not in the tooling:** the target must be a creature
the harness actually spawns. U7's first run modified the worm while `--enemy` spawns the
hatcher, and the client never read a modified byte.

---

## 10. A6 — RUN 2026-08-18. The entropy layer costs **+8 bytes**, and that is a smaller result than it sounds

`toolkit/mapdata/gwentropy.py` + `test_gwentropy.py`, 91 checks, floor 91, ~43 s. Read-only
against `vault/dat_study/Gw.dat`; no client, no server, nothing under `vault/` written.
`git diff -- toolkit/mapdata/gwdat.py` is **empty**, which is what makes the byte-for-byte
comparisons below evidence rather than a decoder agreeing with itself.

### 10.1 The number, and the prediction it was measured against

**PRE-REGISTERED 2026-08-17** in §3's A6 row, before any of this existed: *"it lands within
0.5% of 1,029,564 B"*, with the kill rule *"if the accountant cannot reproduce retail's size
to within a few hundred bytes on retail's own tokens, the encoder arc is dead."*

**OBSERVED.** Re-costing retail's own token stream for row 11196 under a from-scratch
canonical Huffman plus this format's meta-coder, keeping retail's block partition:

| | retail | ours | delta |
|---|---|---|---|
| stream header | 8 bits | 8 | 0 — 4 discarded lead bits (measured 0) + `first_four` (measured 2) |
| literal/length tables | 11,284 bits | 11,345 | **+61** |
| distance tables | 2,202 bits | 2,200 | **−2** |
| `block_size` fields | 64 bits | 64 | 0 — 16 blocks × 4 bits |
| tokens | 7,877,902 bits | 7,877,902 | **0** |
| extra bits | 344,974 bits | 344,974 | 0 |
| **total** | **8,236,434 bits** | **8,236,493** | **+59 bits** |
| **stored bytes** | **1,029,564** | **1,029,572** | **+8 B, +0.00078%** |

The prediction is met by roughly 640×. **A6 does not kill the encoder arc.**

### 10.2 Why that is weaker evidence than the headline implies — and this is the finding

The skeptic pass makes an argument that must travel with the number: **A6's headline was
close to unfalsifiable.** Huffman optimality is a theorem, so the token term — **7,877,902
of 8,236,434 bits, 95.6% of the stream** — *had* to tie. The extra bits, the `block_size`
fields and the header are retail's by construction. **The only genuinely free term was
13,486 bits of table transmission, against a pre-registered tolerance of 41,184 bits.**

So what A6 actually excluded is a defect in **our own cost model or reconstruction**. That
was worth excluding and the controls below are real. But a green A6 carries much less weight
for the A7 go/no-go than a verdict of "the encoder survives" suggests, because **the
decision-relevant risk was always the LZ77 matcher and A6 does not touch it.** §1.2 stands
unchanged: the success/failure boundary sits inside deflate's own tuning range.

**The number that should be quoted next to +8 B, because it is the one that decides A7.**
Row 11196's table transmission totals 13,486 bits = **1,686 B, which is 25× the row's entire
68 B of reservation slack**. One extra block costs ~843 bits ≈ **105 B — one and a half times
the whole authoring budget**. The row holds 1,021,421 tokens = **15.58 blocks**, so a matcher
that produces merely **+2.7% more tokens buys a 17th block and overflows the reservation on
table overhead alone, before a single token bit is counted.** Retail's block partition was
handed to A6 for free, and it is not a neutral input: across a 16-row sample retail's
non-final blocks use size codes 1, 2, 4, 5, 7, 8 and 13, so partitioning is adaptive in
general even though row 11196's is trivial (`[15 ×15, 9]`).

### 10.3 Two skeptic results that are larger than A6's own

Both were produced while trying to refute the headline, and both are capability rather than
commentary.

- **[OBSERVED] Retail's stored row was RE-EMITTED BYTE-IDENTICALLY.** A skeptic wrote a
  bitstream emitter — table descriptions copied verbatim as raw bit ranges, then every
  recorded token re-encoded through code words derived from the reconstructed lengths via
  `build_table`'s own `next_bits` walk, then the extra bits, padding, terminator word and
  u32 trailer. Row 11196 came back **1,029,564 B, byte-identical to disk, with
  `crc32 == 0xF862D5C4 == the MFT's own recorded CRC`**. Generality: **428 rows re-emitted
  byte-identically, zero failures** — 3 anchors plus 400 random comp-8 rows in 16 B..20 KB
  plus 25 in 100 KB..7 MB, all drawn from **outside** the module's own anchor and witness
  lists. A valid-but-different parse could not reproduce their bytes.
- **[OBSERVED] ArenaNet's table encoder is IDENTIFIED: it is longest-run greedy.** A
  separately written greedy meta-planner reproduces retail's measured table bits
  **bit-exactly on 2,194 of 2,194 tables (100.00%)**. That is why the C5 control comes back
  so clean — not our decoder forcing anything, but us holding their algorithm. The
  optimal DP beats greedy on 26 of 2,194 tables (1.2%), rising with row size, and the
  magnitude is trivial: **152 bits = 19 B across a whole 26-row witness set.**

**Taken together, every piece of a compression-8 encoder now exists except the LZ77
matcher**: the meta-coder cost model is validated, the table encoder's algorithm is named,
the canonical code assignment is proven by byte-identical re-emission, and a bit packer has
been fed to `build_table` on 2,194 tables with **zero refusals** — no `next_bits` overflow,
no `currentSymbol >= symbolCount`, and decoded lengths matching intended lengths every time.
That materially re-prices A7 downward, and it is the strongest reason to keep it on the board.

### 10.4 The literal-only number §4.5 asked for — and it is DEAD

§4.5 recorded that *"a literal-only Huffman encoder (no LZ77 matcher) was never costed for
ratio … nobody has a number for it on this payload."* **OBSERVED:** row 11196 as Huffman
literals with no LZ77 at all is **1,421,280 B — ×1.3805 of retail's output and 391,648 B OVER
the 1,029,632 B reservation.** Ratio 0.9382 of the payload. The token census says why: of
1,021,421 tokens, **988,469 are literals and only 32,952 are matches** — 3.2% of tokens,
carrying the other 32% of the compression. **A literal-only encoder is not a cheap fallback
and should not be costed again.**

### 10.5 Controls, including the ones deliberately broken

C1 (segment accounting closes to zero bits, with the token term **modelled** from
reconstructed length × count rather than read off bit positions, which is the version that
could not fail) closes to **0 bits on 11/11 test rows and 26/26 witness rows**. C2 reproduces
the payload byte-for-byte twice — tracer vs `gwdat.decompress`, and `replay()` from the
recorded token arrays alone with no Huffman table and no bit reader. C3 Kraft equality in
exact `Fraction` arithmetic on 4,450 retail tables. C4 rebuilds the reconstruction into a
full table and diffs all 256 nodes, 24 `trans` rows and every `vals` entry against what
`build_table` produced. **C5, the meta-cost control:** retail's own decoded lengths back
through our DP versus the table bits measured off the reader — the `above` arm (DP costing
MORE than retail, impossible unless our cost model is wrong) fired **zero times in 6,286
opportunities**, and an independent skeptic re-ran it with a separately derived cost table
and real emitted bits for **0 in 2,194 more**.

Each was **broken on purpose** and watched go red: shave one bit off one of the 256 meta
tokens and C5's `below` arm fires; add one and the refuting `above` arm fires; swap two
symbols' code lengths and Kraft stays blind at exactly 0 while C4 names the node
(`node 240: build_table [5, 190], rebuild [5, 277]`). A check nobody has seen fail is what
`checks.py` exists to complain about.

### 10.6 Corrections to this run's own first draft

Recorded here rather than smoothed, because three of the four were over-claims in **our**
favour and one is a rule violation.

- **The framing model is an IDENTITY, not a prediction, and calling it refutable was the
  defect.** `gwentropy.py`'s docstring, its `framing_bytes()` docstring and the TESTS.md
  entry all claimed it *predicts* the MFT's own `size` field, "a field that is not an input
  to the calculation". `ar.raw(e)` slices the payload to `e.size`, so `len(data) == e.size`
  by construction; C1b pins `final_idx == len(data) − 4` and `avail ∈ 0..31`; agreement is
  then forced for every stored size divisible by 4, and **138,708 of 138,708 comp-8 rows
  satisfy that**. It could not fail anywhere in its population — **exactly the "check that
  cannot fail" CLAUDE.md forbids.** All three sites are corrected; it is kept as bookkeeping.
- **"The scout prototype's 972 B miss was essentially all matcher" is a non-sequitur.** That
  prototype's 1,030,604 B used *its* entropy layer on *its* tokens; A6 measured *ours* on
  *retail's*. The +8 B does not transfer across token streams — table cost scales with block
  count and per-block symbol distributions, both of which move when the matcher changes. The
  defensible claim is the weaker one: **our entropy layer is within a few bytes of optimal
  for whatever token stream it is handed.**
- **"Inside the in-place bar of 1,029,628 B by 56 B" is near-vacuous and mis-denominated.**
  Vacuous because re-costing retail's own tokens and finding they fit retail's own
  reservation is not a milestone. Mis-denominated because §1.1 defines 1,029,628 as the
  reservation *less* the 4-byte trailer while `gwentropy`'s `stored` is trailer-*inclusive*;
  the right bar for a trailer-inclusive figure is **1,029,632**. This is correction **C-3**'s
  trailer double-count, live in a second place, and the direction is conservative by 4 B.
- **C5's independence is narrower than "the one check nothing of ours forces."** It is
  genuinely independent of `table_lengths` and of the DP's run logic, but the DP and
  `build_table`'s measured consumption are both driven by the same borrowed
  `CODE_LENGTH_THRESHOLDS` / `CODE_LENGTH_SYMBOLS`. A shared error in *those* is invisible to
  it — the standing §2.2 risk that `gwdat.py`'s diff against `xentax.cpp` has never been run.
- Minor: "four rows come out smaller than retail" is **two** in bytes (−4 and −8); the other
  two are 0 B. And the stated cause (tie-break luck) is incomplete — the DP genuinely beats
  retail's greedy meta-plan on 1.2% of tables, which is a small systematic edge.

### 10.7 What A6 does and does not say

**Does:** our Huffman + meta layer is within +8 B of ArenaNet's on their own tokens for row
11196, and within {−8 … +28} B across a 26-row witness set spanning 88 B to 6,247,580 B and
five content kinds (ATEX, ffna, MPEG, DDS, MZ). Format conformance is not the encoder's
problem. Rung **A7 is not killed and is now cheaper than costed**, because the table encoder
is identified and the code assignment is proven.

**Does not:** say the encoder works. The LZ77 matcher is **completely untested**, it is where
§1.2 puts the whole risk, and §10.2's block-overhead arithmetic says a matcher only 2.7%
worse in token count overflows the reservation on table cost alone. **Nor does A6 restore the
encoder to the critical path for shape authoring** — §9.3k settled that separately, and the
lever there is still the 29,802 B shell.

---

## 11. Run 7 — designed, taken apart, rebuilt, and STAGED (§11.6). The walk is the readout, and it is WRITABLE

A design pass proposed run 7; three skeptics on distinct lenses attacked it and **all three
refuted it**. That rebuild is §11.1–11.5. It was then superseded in turn by A8 and taken
apart again by five more lenses and fourteen refutations: **§11.6 is the run that is staged,
and it is the one to read.** §11.1–11.5 are kept because their reasoning stands — what
expired is 11.5's transport assumption and 11.4's arithmetic (C-10).

### 11.1 The finding that decides the run, and nobody had it before today

**[OBSERVED] The hatcher's most universal animation is served by a WRITABLE file.** Scanning
MFT rows 10,800–14,200 for shells carrying both FA8 and FA1 gives 32 shells; ranking keys by
how many shells carry them puts **base key 3,259,067,510 (1.067 s) in 26–32 of the 32**. It
appears in the hatcher's shell in **all six calibrated weapon-class variants**
(…510/16/23/26/28/29), and **all six are served by selector 10 = file 109464 — 27,948 B
stored, 79,194 B decompressed, comfortably writable, and already relocated successfully in
run 5.** A 1.067 s whole-body cycle present in every creature in the sample is locomotion.

**So the readout does not depend on the weapon byte, the letter table, or the key lattice at
all**, and §5's worry that the animation we can provoke might live behind the compression
wall does not survive. The walk is provokable on demand — the enemy closes from 300 u and
**re-triggers whenever the player moves >120 u** (`ENEMY_DEST_RESEND`) — long, whole-body,
and repeatable within one session.

**Second new fact, and it inverts the design's own conclusion.** File **169533** (row 13737,
immediately beside the shell) holds 5 records, all residue 4 (letter `u`), all exactly
3.000 s, with keys in only **7–8 of 32 shells** — the hatcher family's own animations rather
than generic ones. It is **writable** (186,268 B stored). A 3-second, family-specific,
class-`u` animation is a better cast candidate than anything in 15018, whose class-`u`
records are the universal 0.03–1.17 s ones every creature has. The design put ~82% on the
opposite.

### 11.2 The key lattice — the mechanism is REAL, the strong claim is refuted

**[OBSERVED, two agents independently] The arithmetic exists.** `0x007F1DD0` computes
`key = 0xE0000000 + (23·G mod 2³²) + C(letter)`, hand-disassembled out of the pinned 38797
image: `lea eax,[eax+eax*8]`, `mov bl,[eax*4+0x00A936B0]`, **`imul edx,[ebp+0x10],0x17`** —
the multiplier really is 23 and the table bytes really are letters. From the archive side a
blind pairwise-shift test recovers the design's exact calibration family
`{0,+6,+13,+16,+18,+19}` at 90–100%, and `mod 23` occupies 15 of 23 residues with a max
bucket of 60 while **every other modulus 2..64 except 46 is uniform** with max bucket ≤ 25.
Generating all 756 keys from the client's own tables with zero fitting hits **135 of the
hatcher's 224 distinct keys**, against a random expectation of 4 × 10⁻⁵ and **five control
lattices scoring 0**. Out-of-sample on other shells: 86.9% and 90%. **The circularity charge
does not stick** — the lattice is generated from the binary, so every archive record is
out-of-sample by construction.

**What is refuted, and the design's "absolutely" is the word that fails:**

- **Twelve letters cannot name fifteen occupied residues.** The table the function indexes
  (`0x00A936B0`, stride 36) has **12 rows** — `u s w h b t p r c d y a`. Four observed
  residues (6, 12, 14, 16) map to letters not in it and hold **64 of 242 records (26%)**;
  the other lens puts **90 of 242 (37%)** off-lattice entirely. **Residue 12 alone is 61
  records — 25% of the creature and the largest single class** — is independently off-lattice
  (best delta to every other class scores **zero**), and is emote-shaped: 2.0–17.7 s.
- **The client does not commit to one letter.** Each row carries 8 fallback indices and
  `0x007F1B10` tries 2 action ids × 3 attempts × 8 preferred letters, then sweeps **every
  remaining** letter — ArenaNet's own name is `attempt <= SEQ_FALLBACKS`
  (`AvSeq.cpp:253`). Simulating the real order for row 0: of 64 action ids 39 resolve, only
  20 on `u`. **The correct unwritable share is 85% (33/39), not the design's 72%.**
- **The downstream inference does no work anyway.** The selector byte is *in* each record and
  names the serving file exactly, **242/242**. The lattice moves an unconditional 62%
  unwritable to a class-conditional 72–82% and **measures nothing about the cast**: neither
  the "cast is ~82% 15018" figure (reproduced as 56%) nor "melee and locomotion are 86–92%
  writable" (no large class lands in that band) reproduces.
- **CONTESTED and unresolved:** the weapon byte's offset. One lens reads `[AvChar+0x1BA]`;
  this repo's own `toolkit/authsrv/agents.py:1001` cites GWCA's `AgentLiving::weapon_type` at
  **`+0x1B2`**. And **our server never sets it** — `GAME_SMSG_NPC_UPDATE_WEAPONS` (`0x006D`)
  is sent only in the hero/henchman block (`authsrv.py:7532`), never for the hatcher. The
  design's central probability rests on a runtime value nothing in our stack writes.
- Also CONTESTED between the two readings: whether `G` comes from the 63-row table at
  `0x00A92EC0`. One lens confirms that table (63 × 32 B, `G` at `+0x10`/`+0x14`); the other
  counts **147 distinct `key//23` values on the hatcher's shell alone**, which 63 rows × 2
  slots cannot supply. Both can hold if the table is *one* source of `G`, not the only one.

**Keep the lattice. It is the arc's best new instrument and it is cheap to re-derive. Do not
let it carry a claim about which file serves the cast.**

### 11.3 Decimation — the numbers are right, the edit is not, and it dodges a wall it need not

**[OBSERVED, reproduced by two agents within 0.5%]** Keeping 1 key in 4 takes 15018 from
1,514,855 B to ~388 KB and 87333 from 1,354,523 B to ~342 KB. `blk2C` is 99.49% / 99.91% of
each file, so a quarter of the keys really is a quarter of the file; both FA1s round-trip
through `skelwrite` **byte-identically unmodified**, and `skelwrite.encode` derives its
header words from channel length with no `blk2C` size field, so **a shorter FA1 is
mechanically supported today.**

- **It dodges harder than the design claimed, and therefore differently.** Both decimated
  payloads fit **inside their own existing reservations** (1,029,632 B and 1,161,728 B), so
  no free run and no relocation is needed. **`datmove.plan_move` REFUSES the move the design
  describes** — *"already reserves 1029632 B and the payload is 388215 B, so it fits where it
  is"* — and the executable path is `datwrite.Writer.replace`.
- **And that is worth something concrete:** doing the two shrinks in place first frees
  **1,459,712 B**, which unblocks **73940** — the one link run 5 could not place — taking
  link coverage from 12 of 15 to **15 of 15**. The simulation is validated by reproducing
  run 5's recorded single refusal exactly.
- **1-in-4 is far more aggressive than required.** To fit stored in its own reservation
  15018 needs only keep-2-in-3 and 87333 keep-3-in-4; keep-1-in-2 is comfortable on both.
- **But as an EDIT it is ruinous for this experiment.** Rotation reconstruction error at
  1-in-4 is **p99 46.6°, max 169.3°** on 15018 — the same order as the 180° flip that is
  supposed to *be* the readout. **Decimation would change the picture by itself**, in an
  experiment whose entire question is "did the picture change".
- **The design's safety check is aimed at the wrong thing.** `MdlAnim:367` indexes the key-
  *time* table through the record's `lo`, which decimating `blk2C` channel keys never
  touches — under this edit it is **a check that cannot fail**. `keyCount >= 2` is
  crash-avoidance, not correctness, and a naive `times[::4]` does leave <2 keys on 6 of
  15018's 106 channels.
- **CONTESTED between the lenses, and left open:** per-sequence-window key survival. One
  measures 200 of 237 records in 15018 (84%) losing a channel entirely out of its window and
  calls it the class that froze runs 2 and 3; the other measures that **retail already ships
  42.3% of (rotation channel × window) pairs with <2 keys and 31% with zero**, so a sparse
  window is normal, and scores decimation as content loss (zero-key pairs 4,830 → 7,079)
  rather than a crash. Not resolved here.

### 11.4 The positive control survives, and it was audited rather than taken on trust

> **ITS NUMBERS ARE WRONG — see C-10 and §11.6a.** The hierarchy and the node set
> below are right and independently reproduced; every DISTANCE is ~11× too large,
> because this section accumulated `blk2C` bases down the parent chain and they are
> **absolute rest positions**. Corrected: the head cluster moves **1.98× the whole
> creature's extent**, not 0.67×. The control is stronger than this section claims
> on paper — and **it still did not fire in the run: §11.7b.** "Orthogonal to a
> limb-flip readout", below, is the sentence that did not survive contact.

Nodes 51–64 **are** the head cluster. The hierarchy was rebuilt from `blk2C`'s parent field
(reading the self-link as "continue from the previous node", the only interpretation yielding
a connected tree): spine 0→25, two symmetric limb clusters each with five 3-bone digits at
x = ∓108, and a terminal chain 48→49→50 whose subtree is **exactly {50, 51..64}** — two
mirrored 3-bone horns, a 4-bone jaw chain descending in −y, and four stubs. Bases ×3 takes
node 62 from z −805 to z −1343 against a whole-creature extent of 805. **Unmissable in a
first still, orthogonal to a limb-flip readout, and independent of the picker, the key law
and the file selection.**

### 11.5 What to ship — SUPERSEDED 2026-08-19 by §11.6; kept because its reasoning stands and only its transport assumption expired

**The stripped run, plus the two things the skeptics added.** Flip every rotation key by 180°
in the writable links — **including 109464, which serves the universal walk in all six weapon
classes** — keep the head-cluster ×3 positive control in the same archive, and **provoke the
walk rather than the cast**. No decimation, no large stored rows, no sequence-record edits,
no key-table edits: rules 1, 3, 4 and 7 of §9.3g are untouched rather than merely satisfied,
and the flip is length-preserving so nothing relocates.

**One honest cost of stripping, measured:** without the two in-place shrinks, 73940 has no
run to land in and coverage is **12 of 15 links**, exactly as run 5 recorded. That does not
matter for this readout, because the walk is served by 109464. **Decimation stays on the
shelf as a proven capability for the day something needs 15 of 15** — §11.3's numbers are
sound and its in-place form is safer than the relocation the design proposed.

---

### 11.6 Run 7 IS STAGED — 2026-08-19. A8 rewrote the design, and the skeletal geometry this arc has been using is wrong

`vault/research/archivewrite/a4stage7.py`. **Not deployed, not launched.** Five
adjudication lenses and fourteen refutations; two `kills-the-run` findings, one
of which stands and one of which the corrected geometry retires.

**§11.5's design is superseded, and it is A8 that superseded it.** 11.5 assumed
writes go in as compression 0, which is what runs 4–6 did through `datmove`;
under that assumption 15018 and 87333 are unreachable, coverage is 12 of 15
links, and several rows relocate. Re-measured with the flip applied and costed
through `gwenc`, **fourteen of fifteen links fit their OWN existing reservation
compressed — including both files 11.5 called unreachable** (15018 at +16,544 B
of slack, 87333 at +15,020). So the run **relocates nothing, grows nothing, and
consumes no free run**: exactly 15 rows change in place. Strictly less
disturbance than 11.5's design and strictly more coverage. **222949 is the one
exclusion — 12 B over at every quality dial 0..9 with `optimal` both ways.**
Coverage is **234 of 242 sequence records (96.7%)**; of the 8 missed, 6 are
222949's and **2 carry selector 0, meaning "this file"** — served by the shell's
own `blk2C`, no link involved.

#### 11.6a The correction that reaches backwards — C-10

**`blk2C` bases are ABSOLUTE MODEL-SPACE REST POSITIONS.** §9.3g called them
bone lengths; §11.4 accumulated them down the parent chain; this arc's first
draft of the staging script reproduced the error rather than catching it. **The
referee is ArenaNet's own mesh** (file 116703, bbox **72.6 u**): the absolute
reading seats all 86 joints inside the skin at median **1.40 u** from a real
vertex, the accumulated reading puts them **532 u** away. An FK model taking the
offset as `base[i] − base[parent[i]]` reproduces every stored rest position to
**0.000000** under identity rotations. Full entry: **C-10**.

The consequence §9.3g drew survives untouched — scaling bases still explodes the
skeleton, and run 6 fired. What changes is every distance, and **in the
favourable direction.**

| instrument | under the corrected geometry |
|---|---|
| head cluster ×3, at rest | head nodes move mean **135.8** / max **143.6** = **1.98× the creature's entire extent**; all 72 other nodes move **exactly 0.0000** |
| the flip, over link 109464's own 200 key times | mean joint displacement **83–88**, max **113** = **1.55× extent** |
| both instruments on | the head scale still moves head nodes **up to 151.7 (2.09× extent)** and non-head nodes **exactly 0.0** |

**That last row retires the sharper of the two `kills-the-run` findings.** A
lens charged that the flip destroys the positive control — "the creature
collapses from 805 units to 75, the control's spike reverses" — and proposed
restricting the treatment to an arms-only subtree. Every number in that charge
was computed on the accumulated geometry. Measured correctly, **the two
instruments are additive and disjoint**, so the dose does not change. Two
skeptics reached the same place independently, one of them by refuting the
geometry outright.

They also **fail looking different**, which is what makes both readable: the
head scale changes bone lengths (run 6's "splayed shards"), the flip preserves
every bone length to **0.0000** and only rotates — and it is not a
re-orientation, since the best-fit rigid residual between the retail pose and
the flipped pose is a fifth of the creature against **0.000000** for an actual
whole-body rotation.

#### 11.6b The control's premise is now measured, not trusted

"Normal head = pipeline broken" needs geometry to actually follow nodes 51–64,
and **nothing in this repo had ever checked it** — a lens flagged it as the one
verdict resting on an unmeasured assumption, and this arc has lost runs to a
control taken on trust. Nearest-joint assignment over ArenaNet's own **1,463**
mesh vertices: **308 (21.1%) are nearest a node in 51..64**, **all fourteen**
own at least one vertex, two whole submodels are head-dominated (**270 verts at
77.8%**, 39 at 89.7%), and the head-assigned vertices occupy **z ∈ [−72.6,
−57.3]** — the top fifth of the creature, 10 u wide and centred.
**RECONSTRUCTION**, labelled: this tree does not decode skin weights, so
nearest-joint is a proxy. It is a strong one.

#### 11.6c The edit is settled against the client, not against our own model

- **slot[3] IS the scalar**, read out of `0x00783F10` — the function composing
  quaternion + position into the 3×4 handed to Gr at `0x00671FF0`. `q[3]`
  (`[eax+0xc]`) appears six times and every one is a cross term
  `2(qa·qb ± qc·q3)`, never a bare `1−2(·²+·²)` diagonal; the scalar is by
  definition the component that never appears in a diagonal square. This
  **CORROBORATES** the statistical read (slot 3 carries mean |v| 0.92–0.97
  against 0.05–0.19) rather than merely agreeing with it.
- The multiplier is exactly `M → M · Rot180X` **in the client's own
  arithmetic** — 3.3e−07 over 30,000 real keys, with **five rival compositions
  all off by 2.0**. The check selects one of six rather than confirming itself.
- **The no-op count is 0 of 249,050 keys, and it is an identity.**
  `|Rq − q|² = |Rq + q|² = 2` for every unit q, so every flipped key sits at
  exactly √2 from both `+q` and `−q`. `q ≡ −q` would have been **invisible**;
  it is unreachable, not merely rare.
- The client's shortest-path nlerp is **provably untouched** — 0 branch changes,
  0 gate changes in 1,240,480 samples, residual exactly 0.0, because a constant
  left-multiplication is an isometry and the flip is a signed permutation
  (bit-exact in f32). Side result: **retail already ships 0.12% of blends
  outside the `[0.9,1.1]` renormalize gate**, and the flip leaves that count
  unchanged at 1,527.
- **+X is near-optimal and +Z would have been a near-miss.** The hatcher's bones
  run **95.5% along Z** and the extra rotation lands in the child frame, so 180°
  about X reverses a z-aligned bone: 198.8 u (X) / 202.1 (Y) / **29.3 (Z)**.
  Nobody wrote that down; do not let it be "simplified" to +Z.
- **No retail invariant is broken.** Rules 1/3/4/7 are untouched *by
  construction* — the edit changes zero bytes in the n18 sequence-record span
  and the n3C key-table span in 16 of 16 files — so re-scoring them is not a
  check and the byte-confinement is. The one invariant a rotation edit could
  genuinely break, **per-channel hemisphere continuity (adjacent-key dot ≥ 0,
  100.000000% in retail)**, is preserved exactly for the same isometry reason.
  Two conventions the flip *does* disturb are not invariants: retail ships
  1.996% negative-`w` keys, and 3.3% of channels start more than 1° from
  identity with a measured maximum of **179.43°** — the flip's own magnitude.

#### 11.6d The shell goes in compressed, in place — argued, not defaulted

The alternative was run 6's proven transport (stored, relocated), which would
make the control fail **independently** of the links. It was rejected: it leaves
the fourteen compression-8 link writes with **no witness**, so the run's most
likely informative outcome — giant head, unchanged limbs — could not be told
apart from "the link writes never landed". And the failure it protects against
is not reachable: all sixteen payloads encode to literal `symbol_count` 270–285
and distance `symbol_count` 23–30 with **zero tables under 2**, strictly inside
retail's attested envelope, so **§13.5's gap A is not entered by any row here**.
A shell that failed to decode would not render a normal hatcher anyway — white
box, error 12 at `0x0079644E`, or an AV on the unchecked `links[sel-1]` deref.

#### 11.6e The decision table, replaced — the old one sent a positive result to ABORT

| observation | verdict |
|---|---|
| head grows + limbs contorted | **ANSWERED.** Linked content reaches the screen. |
| head grows + limbs normal | **NEGATIVE — but only after ≥3 logged `walks to` cycles.** Two records are selector 0 and served by the shell, one a **2.000 s whole-body cycle over 46 of 86 nodes** — the shape of a standing idle. A hatcher watched while stationary shows this cell with the run working perfectly. **Never score a negative from a still.** |
| head NORMAL + limbs contorted | **ANSWERED, control invalid. DO NOT ABORT.** The treatment fired; only the control failed. §11.5's table sent this to abort and discarded a positive. |
| head normal + limbs normal | pipeline broken. ABORT — **but run `datcheck --generations` and `--diff` first**: a generation adoption reverts all fifteen rows at once and is the only mechanism producing a clean null on both arms. |
| creature missing / white box | the shell load path failed — the cell that isolates a shell-write problem. |
| assert or access violation | a **RESULT**. Compression layer → fix already costed; `n2C == 0` or a chunk gate → indicts our `skelwrite`; AV with no assert → a link that failed to load. |

#### 11.6f The flag that would have silently voided the run

    python toolkit/harness/session.py --enemy --hold 420 --shots 5 \
        --walk "zoom:-12 pitch:300 alt:3 shot:1 wait:4"

**`--practice-target` is FORBIDDEN here.** It sets `ENEMY_ATTACKS_BACK` False
and the chase loop `continue`s on `not attacks_back` **before a single
MOVE_TO_POINT goes out**, so the creature never walks. Project memory points at
that flag because it is what makes the *player* kill something — a different
goal with the opposite requirement. `--explorable` is unnecessary; nothing in
the chase or attack path reads it. The >120 u re-chase (`ENEMY_DEST_RESEND`) is
one constant with one call site and the server **prints a timestamped line every
time it fires** — that line, not the operator's memory, is what licenses any
claim about what the creature looked like while walking.

**Coverage is better than 11.1 thought**: the corpus's two most universal
animations are rank-1 key 2,307,259,448 (36/36 shells, selector 1 = **15018**)
and rank-2 key 3,259,067,528 (36/36, selector 10 = **109464**) — and A8 makes
**both** writable, so both are flipped. The readout no longer hinges on catching
one cycle.

#### 11.6g What sabotage found, and it is the fifth rung running

Five guards were broken on purpose. Four refused correctly — identity multiplier,
222949's 12-byte overflow, a non-retail source archive, and a below-threshold
head scale. **The fifth passed green: with `HEAD_SCALE = 1.0` the positive
control is a complete no-op and every gate in the script stayed green.** Fixed
with a displacement floor denominated in the creature's own extent (smallest
head-node displacement ≥ 0.5 × span), which now refuses ×1.0 *and* ×1.4. This is
the fifth consecutive rung where a check claimed more than the artifact
delivered, and sabotage is still the only technique that catches it.

Two guards the write path needed and did not have, both now in the script:
**`Writer.replace` has NO identity gate** — writing file A's payload into file
B's row is accepted and every rule this project owns stays green (reproduced end
to end on a synthetic fixture); `restore()` has `check_identity()`, `replace()`
has nothing. And **`flip(flip(q))` is bit-exactly `−q`, the same rotation**, so
staging from an already-deployed archive would restore retail limbs while taking
the head to ×9 — landing precisely on the NEGATIVE cell, produced by a bug.
Every payload is read from `Gw.dat.retail` and the source is fingerprinted
against retail's own stored sizes for all sixteen rows before a byte is flipped.

### 11.7 RUN 7 FIRED — 2026-08-19. **A linked file's CONTENT reaches the screen.** The arc's question is ANSWERED

**Owner, at the keyboard: "their bodies are kind of twisted like pretzels…
idle/walk/cast all have pretzel model animations."** Screenshot: two bodies
folded through themselves, nameplate `Hatcher [Collector]` on one of them.

**That is the answer six runs failed to get.** Runs 1–5 scaled linked-file
*bases* and nothing moved; run 6 scaled the *shell's* bases and the creature
exploded, which proved (§9.3k) that linked bases are never read. The property
linked files actually own — their rotation channels — had never been tested.
Run 7 flipped every rotation key in fourteen of them by 180° and **every
animation the creature plays came back deformed**.

| | |
|---|---|
| verdict | **ANSWERED.** Linked animation content reaches the renderer. |
| treatment | 232,764 rotation keys, 14 linked files, `q → (1,0,0,0)·q` in (x,y,z,w) |
| transport | 15 rows rewritten **in place at compression 8** by our own encoder |
| client | spawn 8 of 8 PASS, **no assert**, `RUN VERDICT: PASS` |
| coverage observed | idle, walk **and** cast all deformed — the owner reports **no normal animation at all** |

#### 11.7a The write path is validated under a CONTENT change, which A8 could not do

A8 proved the client reads a row our encoder compressed **with a byte-identical
payload** — it isolated the compressor, deliberately. Run 7 is the other half:
**fifteen rows whose payloads we authored**, compressed by `gwenc`, written in
place, and the client **rendered from all fifteen**. §13.5's gap A did not fire
on any of them, as §11.6d predicted from the symbol counts.

The post-launch diff (§5.6 rule 6) is the strongest single line in the run:

    rows changed since deploy: 2   -- 8315, 8316, the client's own scratch rows
    growth: None | preflight 10/10 | generations 6/6 | 4,198,489,600 B
    our 15 edited rows still byte-identical to what we deployed: 15/15

**No repair fired, nothing was discarded, no generation was adopted, and the
archive did not grow by a byte.** Rows 8315/8316 move on every launch and are
not a repair. The 1.5 MB wall is not merely passable — a row past it was written
with new content and read back by the retail renderer.

#### 11.7b The control FAILED, and it is recorded as a failure

**The head was not enlarged.** Nodes 51–64 at ×3 should have displaced that
cluster ~2× the creature's own height (§11.6a, and the FK model reproduces every
rest position to 0.000000). It did not read on screen. Two candidates, and this
arc does not get to pick the flattering one:

1. **The binding proxy was wrong.** §11.6b measured 21.1% of mesh vertices as
   *nearest* a node in 51..64 and labelled it **RECONSTRUCTION** because this
   tree does not decode skin weights. Nearest-joint is not binding. If the head
   geometry is weighted elsewhere, scaling those nodes moves nothing visible —
   and the label was carrying exactly that risk.
2. **A pretzeled body makes an enlarged head unreadable**, which two skeptics
   predicted in almost these words.

**ANSWERED 2026-08-19, and it is candidate 1.** The skin binding in the 0xFA0
geometry chunk is now decoded (`toolkit/mapdata/modelfile.py`
`group_transforms`/`vertex_transforms`, `test_modelfile.py` §7, register row in
`PLAN.md` §6.1). Resolving every vertex of file 116703 through it: **ZERO
vertices bind to any node in 51..64.** The head skin binds to **nodes 48 and
49** — submodel 3 (39 verts) to node 49 alone, submodel 2 (270 verts) to 48 and
49 — and the fourteen bones run 7 scaled ×3 carry **no geometry at all**. They
are the horn and jaw bones; nothing is weighted to them. The control could not
have fired, and the run's own bytes say so. **The proxy was the failure**:
"nearest joint" measured proximity, and binding is not proximity — 21.1% of
vertices being spatially nearest those nodes was true and irrelevant. That is
exactly the risk the RECONSTRUCTION label was carrying, and it is the second
proxy to break in one day.

**It does not touch the verdict**, and that is the whole point of §11.6e's
rewrite: the cell we landed in is *head normal + limbs contorted*, which the
corrected table scores **ANSWERED, control invalid, DO NOT ABORT**. **§11.5's
original three-way table sent this exact cell to ABORT.** Had the run gone out
as designed on 2026-08-18, a positive result would have been scored as a broken
pipeline and thrown away. That correction came out of the adjudication pass, not
from the run.

#### 11.7c Two things the run turned up that were not in the design

- **The owner reports NO normal animation — SETTLED 2026-08-19, and it is the
  expected result.** §11.6 predicted two records would survive unflipped because
  they carry **selector 0**. They do, and **both are EMPTY**: `keys[90:90]` and
  `keys[123:123]`, zero keys each, so neither can render anything. Of the
  creature's 242 records, **2 are empty and 6 are served by 222949**, leaving
  **234 of the 240 that can play (97.5%) flipped**. There was never an unflipped
  animation to see. (An adjudication lens called one of them "a 2.000 s
  whole-body cycle over 46 of 86 nodes"; that is wrong — it has no keys.)
  **Corollary, and it is the mirror of §9.3k:** the shell carries **48 rotation
  channels across its 86 nodes and no sequence record selects any of them**. So
  linked files carry a rest skeleton nothing reads, *and* the shell carries
  motion nothing plays. Both halves of that redundancy are now measured.
- **THE FOURTEEN FILES ARE SHARED ANIMATION LIBRARIES — MEASURED 2026-08-19.**
  A whole-archive scan (177,334 rows; 64,245 model-type FFNA; **252 carry an FA8
  link list**) finds **twelve of the fourteen linked by exactly 30 distinct
  shells each**, 15018 by 29 and 169533 by 21 — **30 of 252 shells (11.9%) link
  at least one.** So run 7's edit reached thirty models, not one, and the
  authoring capability this arc delivered is **global, not per-creature**:
  editing a linked animation file changes every model that links it.
  **They are NOT one family cluster** — the obvious deflation, that these are
  just the hatcher's relatives, is refuted: only **8 of the 30** sit in rows
  10,500–14,500 (11196, 11197, 11548, 12241, 12474, 13738, 13739, 13948), so
  22 live elsewhere in the archive. Note **11196 is file 15018 itself**, so a
  linked animation file carries its own FA8 list and the link graph is nested.
  **What is NOT settled** is the owner's screenshot: a second body is pretzeled
  beside the hatcher and it was not identified at the keyboard. The server knows
  only two NPCs (`content/npcs.toml`: the hatcher and a burrowing worm) and
  `--enemy` spawns the hatcher, so the second body is most likely the **player
  character** — which would mean the player's own shell links one of the
  fourteen. **UNVERIFIED**, and the harness stills are all empty (`client not
  foreground`, every shot skipped), so the only visual record is the owner's own
  capture, `2026-08-19 07-30-25.mkv`. Name the models before quoting it.

#### 11.7d What this closes, and what it opens

**Closed:** the arc's animating question, and the encoder arc with it. The route
is `skelfile` → typed repr → `skelwrite` → `rebuild_container` → `gwenc` →
`datwrite.replace(compression=8)` → **retail renderer**, end to end, with 62% of
this creature's animation records no longer unreachable and **no relocation, no
growth and no free-space consumption anywhere in it**.

**Open:** the positive control's premise (does geometry follow nodes 51–64 —
needs skin weights, which `modelfile.py` does not decode); the selector-0 pair;
and whether the linked files are shared across models. None blocks anything.

---

## 12. A7a — RUN 2026-08-18. The matcher ties retail, and the **block partition** is worth 18 KB

`toolkit/mapdata/gwmatch.py` + `test_gwmatch.py`, 62 checks, floor 62, ~28 s. Size-only: a
hash-chain lazy LZ77 emitting tokens in this format's alphabet, costed through `gwentropy`'s
validated model. **No bitstream writer, no round trip.** Two skeptics attacked it on distinct
lenses and **neither refuted it**, both reproducing every headline figure independently.

**Every byte below is TRAILER-INCLUSIVE**, so the bar is **1,029,632 B** — not §1.1's
trailer-exclusive 1,029,628. The §10.6 double-count did not recur; a skeptic checked for it
specifically and found no mixed-denomination number anywhere.

### 12.1 The number

| | bytes |
|---|---|
| retail | 1,029,564 |
| its reservation (the bar) | 1,029,632 — **68 B of slack** |
| best of 18 raw-deflate configurations (level 8 / memLevel 8), re-measured | 1,017,638 |
| **ours, q8, DP partition** | **1,011,244 — 18,388 B of slack, 6,394 B better than zlib** |

**A7 IS NOT KILLED.**

### 12.2 The matcher is a dead heat with ArenaNet's; the partition is what pays

| | ours | retail |
|---|---|---|
| tokens | 1,021,409 | 1,021,421 |
| matches | 32,950 | 32,952 |
| blocks | **109** | **16** |
| table bits | 88,263 | 13,486 |
| token bits | 7,656,124 | 7,877,902 |

**Twelve tokens apart in a million.** The entire 18,320 B win is bought by spending **74,777
more table bits to save 221,778 token bits** — many small blocks, each with tables fitted to
its own local symbol distribution.

**Cross-validation, exact to the byte:** our tokens costed on retail's own `[15×15, 9]`
partition give **1,029,572 B — identical to §10.1's re-cost of retail's OWN tokens.** Two
different token streams, same entropy layer, same partition, same figure. That is strong
independent evidence that the matcher has converged on retail's matcher's quality and that
the win comes from somewhere else.

**A correction to this run's own framing, from the skeptic, and it matters.** The report said
*"the reason is not the matcher but the block partition."* That is framing, not fact: at the
best dial setting, **under retail's own uniform-16 partition we already fit** (1,029,572 ≤
1,029,632, 60 B of slack). The partition buys the **size** of the win and robustness **across
the whole dial** — it is not what turns fail into pass.

**And §1.2's predicted curve is real, on retail's partition.** Forced onto uniform-16, **six
of ten dial settings OVERFLOW**, crossing over at q6: 1,036,724 → 1,029,572. With the
partition searched, **every** dial setting fits — even q0, a chain-depth-1 greedy matcher
strictly worse than deflate level 1. So matcher quality genuinely does sit inside the tuning
range, exactly as §1.2 said; a searched partition is what removes the cliff.

### 12.3 The population, and it reverses §1.2's risk

§1.2's case against the encoder was population-level: zlib and ArenaNet are a statistical
tie, 23.8% of stuck rows miss their own reservation under zlib -9, and three named rows are
real overflows. **[OBSERVED, skeptic, correct one-based row indexing]:**

- **25 random compression-8 rows, 200 KB–1.5 MB: ours beats retail 25 of 25 and fits the
  reservation 25 of 25. Raw deflate level 8 / memLevel 8 fits only 14 of 25.**
- **The three rows §1.2 named as zlib's worst overflows, ours fits all three:** 77197 −108,
  95089 −124, 89174 −316, where zlib overflows by +7,142, +5,800 and +5,259.
- Witness set of 16 rows spanning 88 B to 2,444,804 B and seven content kinds: **11 beat
  retail, 4 tie exactly, 1 loses by 4 B** (row 69251). Largest win row 15850, −46,448 B.

**The honest counterweight, and it is the skeptic's:** on those hard rows the margin is
**0.003–0.01%**. Row 11196's 1.8% is a favourable draw, exactly as §1.2 warned about this
row. The 18,388 B of slack is a property of *this row*, not of the encoder.

**And "the win is the partition" is a row-11196 statement, not a general one.** On row 35300,
where retail **already** partitions finely, we still beat it by **33,156 B** — so across the
population there is a matcher and entropy component too.

### 12.4 The authoring budget, finally denominated in payload bytes

Slack means nothing until it converts into headroom. Measured marginal rate by compressing
prefixes over the last 100 KB: **0.5365 stored bytes per payload byte**. So **18,388 B of
slack ≈ 34,273 B of extra payload — 2.26% payload growth** before overflow, against retail's
own 68 B ≈ **127 payload bytes**. **A ~270× larger authoring budget.** [RECONSTRUCTION]

**This is the number §7.3's unanswered successor question must be answered against.** §7.3
established that authored edits mostly make this payload *smaller* (requantization by 46%)
and that the residual risk is a *higher-fidelity* payload with more samples, which nothing
bounded. **2.26% is now that bound.**

### 12.5 The 109-block shape is attested in retail's own content

The run's one live caveat was that a 109-block stream has never been through a real decoder.
**[OBSERVED, census of 400 random comp-8 rows]** retail's non-final block size codes span
**0 through 15, all occurring**; the smallest (4,096 tokens) appears **69 times**; 44 of 400
rows use a non-final code other than 15; and **row 35300 ships 249 blocks**. Every structural
shape our DP emits — small non-final blocks, mixed codes, >100 blocks — is one ArenaNet's own
encoder ships. *(One lens sampling only rows ≤400 KB found a maximum of 33 blocks and read
the caveat as understated; the other found 249 on a large row. The disagreement is a sampling
artifact and the larger figure is the relevant one.)*

A second consequence: **"retail takes the maximum block size" is true of row 11196 and false
of retail's encoder.** Whatever rule it follows, it is not "always 15" — so "ArenaNet left
12,520 B on the table" is a statement about this row, not about their compressor.

### 12.6 What is still unbuilt, and it is the whole remaining risk

**No bitstream exists.** No table this encoder implies has ever been serialized and rebuilt by
`gwdat.build_table`; every legality check here is a *model* of `build_table`, not
`build_table`. All 218 tables of row 11196 do check out — Kraft defect exactly 0 in exact
`Fraction` arithmetic, canonical assignment never exhausts the code space, deepest code
length **15** against the format's 31 ceiling — **but they hold by luck of the cost path
raising, not by an explicit arm.** That arm belongs in **A7b**, along with the writer itself.
Note that a skeptic already emitted real bits during A6 and had `build_table` accept them on
2,194 tables with zero refusals (§10.3) — but those were *retail's* tables, not ours.

### 12.7 Corrections to this run's own first draft

- **A check that cannot fail, for the second time in two rungs.** The report listed **C1**
  (segment accounting closes to zero bits) among its checks. On *retail's* stream that is a
  genuine measured-versus-modelled closure. **On OUR stream both sides derive from the same
  `token_bits` formula, so it cannot fail** — the identical defect §10.6 corrected for
  `framing_bytes`. Corrected in the test and in TESTS.md. Recording the recurrence rather
  than just the instance: **this defect class survived a rung that had just been corrected
  for it**, which is an argument for checking the "what would a red mean here" question
  against every verdict line rather than once per arc.
- Witness tally was "12 beat, 3 tie, 1 loses" in prose against a numbers table saying
  **11 / 4 / 1**. The table was right.
- `extra_bits` reported 345,045, measured **345,029** — 16 bits, partition-invariant.
- **The orchestrator's brief was wrong and the experiment corrected it.** It said "token
  count matters twice — directly and through the block count it implies" and "minimising
  block count is not a trick retail declined", both implying **fewer blocks is better.** The
  opposite is true: more, smaller blocks win here by 18 KB. The build agent flagged the
  inversion and found the right answer anyway. Recorded because §10.2's block-overhead
  arithmetic — which came from A6's skeptic and which I promoted to "the number that decides
  A7" — is what produced the wrong steer, and it is still correct *as arithmetic about
  retail's partition*; it just is not the constraint it looked like once the partition
  becomes a free variable.

---

## 13. A7b — RUN 2026-08-18. **The writer exists, and it reproduces ArenaNet's own bytes**

`toolkit/mapdata/gwenc.py` + `test_gwenc.py`, 55 checks, floor 55, ~150 s. Three skeptics,
**none refuting**, each reproducing the headline independently. All figures
trailer-inclusive.

### 13.1 The two results

**[OBSERVED] Retail's own stored rows are re-emitted BYTE-IDENTICALLY.** Row 11196 comes
back at 1,029,564 B with `crc32 == 0xF862D5C4 ==` the MFT's own recorded CRC. At scale:
**3,051 distinct rows across five archive files, 197 MB, zero failures**, plus a skeptic's
independent draw of **~5,990 more re-emissions across seven archives by their own seeds,
also zero failures. No failure class, in any archive, any size band, any client build.**

This is the check that does not depend on `gwdat` being a correct decoder, and a skeptic
confirmed it is not smuggling: the writer never touches the trace's recorded bit positions,
and re-emission still succeeds when the trace is round-tripped through a plain dict carrying
**only semantic fields**. Tables are re-planned from code lengths through
`meta_plan(optimal=False)`; code words are re-derived from lengths. The table encoder and the
canonical assignment are genuinely on trial, and perturbing any of bit order, code
assignment, `symbol_count`, meta-tokens, size codes, `first_four`, extra-bit widths or
framing changes the bytes.

**[OBSERVED] Our own encoder emits real bits.** `gwmatch` → `gwenc` → **unmodified
`gwdat.decompress`** returns the exact payload, and row 11196 emits **1,011,244 B — equal to
A7a's modelled figure TO THE BYTE**, 109 blocks, **18,388 B under the 1,029,632 B
reservation.** The A7a number is now an artifact rather than a model.

**§12.6's stated remaining risk is retired.** 328 encoder-implied tables were serialized and
rebuilt by `gwdat.build_table` itself with decoded lengths diffed against intended: **0
refusals, 0 mismatches.** Across a dial × partition stress the build agent ran 1,204 more
tables through it, also zero.

### 13.2 The bit order is corroborated from ArenaNet's own source, not just from our decoder

**[OBSERVED, and this is the strongest independent evidence in the rung]** The client's bit
layer is `P:\Code\Base\Compress\CmpIo.h`, named by its own assert lines. `gwdat`'s
`buf1`/`buf2` are their `m_rackData0`/`m_rackData1` (`CmpIo:60`). **The client has a bit
WRITER, and its preconditions are exactly this writer's** — `CmpIo:138 bitCount < 8 *
sizeof(value)` and `CmpIo:139 !(value & ~((1 << bitCount) - 1))`.

The rule: **bits are MSB-first inside each 32-bit word; words are in file order; each word
is little-endian.** Validated by 7,688,160 bits round-tripped against disk across 48 rows
with zero mismatches, and by three negative controls — big-endian words, LSB-first-in-word
(zlib's order), and MSB-first bytewise — **all three of which differ from disk**, so the
passing arm selects one of four rather than confirming itself.

### 13.3 The framing, measured rather than assumed

- **Prologue:** `data[3] == 0x02` — four zero lead bits then `first_four = 2` — on **138,708
  of 138,708** comp-8 rows in `dat_study`, widened to **258,708 rows across four archives and
  three client builds. One value.**
- **Pad:** `pad = (−consumed_bits) mod 32`, and **every pad bit is zero** — 1,109 stratified
  rows, all 32 pad widths occurring, not one non-zero bit. A control writing them as ones
  gives different bytes that still decode, so they are genuinely free and retail chose zero.
- **The tail word 0x80010008 is the reader's mandatory look-ahead**, constant on **258,708 of
  258,708** rows. Two controls: replacing it with `0xDEADBEEF` or omitting it entirely both
  still decode, so `gwdat` does not need it — **but every retail row has it and the client is
  the only oracle, so it is emitted.** What the value *means* is **NOT FOUND**. It does tell
  us the shape of retail's writer: invariant across all 32 pad widths means they flush the
  partial word with zeros and then write a literal sentinel, rather than shifting out a
  pre-loaded register.
- **A real defect in our own decoder, found by a refutable control.** Hand `gwdat` a stream
  one word shorter than the rule requires and it **silently truncates the payload** rather
  than raising — row 11196 returns 1,514,850 of 1,514,855 B. `Eof` fires inside `next_code`
  *after* the symbol is found, and `decompress` swallows it. Worth knowing before anyone
  trusts a short read.

### 13.4 The zero-length code — and my own brief's premise was wrong

I told the agents *"A6 measured retail never enters it."* **That is false and a skeptic
refuted it.** A6's measurement was about the *scout's prototype encoder*, not about retail,
and I mis-carried it.

**[OBSERVED] Retail enters the zero-length branch: 12 of 138,708 first blocks** carry a
zero-length distance table — rows 8295/8300/8302/8305 each declare n=5, all-skip, with the
zero-bit code consulted 24 times per block.

**And the decisive measurement, which retires half of §2.2's standing risk.** Decoding
ArenaNet's **own** row 8295 with an *upstream-faithful* `build_table` — the length-0 symbol
parked and never read back, exactly as `xentax.cpp` and `binutil/huffman.go` do — **FAILS**
with `zero-length code (table hole)`. So `gwdat`'s repair, which its docstring has always
labelled a divergence from both upstream lineages, **is REQUIRED by ArenaNet's own archive.
The shipping client must implement something equivalent, and using the branch is not a step
outside what the client demonstrably does.** That is a much better position than §2.2's
*"a bit-exact round trip through a wrong decoder proves agreement, not correctness."*

### 13.5 Where our encoder leaves retail's envelope — the real A8 risk

A skeptic asked which paths **B1 structurally cannot cover**, because retail never took them.
Three feared gaps turned out not to exist: **ours is a strict subset of retail** on block
count (retail rows carry 1..37 blocks and use *every* size code 0..15 including as non-final,
so our 109 blocks is more iterations of a covered path, not a new one), on code lengths
(ours lit 0..15 / dist 0..11 against retail's lit 1..16 / dist 0..13), and essentially on the
meta alphabet. In the other direction **B1 is broader than B2 in the bit layer**, exercising
the writer on inputs our encoder never generates.

**What is genuinely uncovered, and it is one thing that matters:**

| gap | retail | ours |
|---|---|---|
| **A. declared `symbol_count == 1`** | **0 of 138,708 first blocks** (min lit 258, min dist 5) | **7 of 208 tables (3.4%)** |
| B. zero-length **literal** table | 0 of 138,708 | 2 of 208 |
| C. declared counts outside retail's envelope | lit ≥ 258, dist ≥ 5 | lit 66/67/98/256/257/258 — 257 alone is 19 of 102 lit tables; dist 1/2/6 |
| D. a zero-block stream | none — smallest row is 56 B and holds a block | `encode(b"")` → 12 B |
| E. three meta indices in the 16-bit catch-all band | absent from a 709-row sample | emitted |

**Gap A is the one to watch.** Retail reaches the zero-length code only through the
`total == 0` fallback with declared ≥ 2; ours reaches it through the `symbol_count < 2` arm
with declared == 1, a branch ArenaNet's own compressor appears never to trigger. Its
correctness rests on `gwdat`'s repair **plus** `gwentropy`'s model of that repair — both
ours, **no external witness anywhere in the rung**. `test_gwenc` §2 exercises it, but its
referee is `build_table`, so it is B2-strength, not B1-strength.

**The mitigation is named and cheap, so this is not a blocker:** the declared-1 empty
distance table costs 20 bits; a two-symbol distance table inside retail's attested envelope
costs a few bits more and sits on a path 138,708 rows witness. **If A8 finds the client
refuses declared == 1, that is the fix — a size question, not a design one.**

### 13.6 Corrections

- **The trailer double-count, for the THIRD time.** §3's A7 ladder row still stated the
  acceptance criterion as `≤ 1,029,628 B` — §1.1's trailer-*exclusive* figure — while every
  A7a/A7b number is trailer-inclusive. Nothing turned on it (1,011,244 clears both), but that
  is the row a cold session reads *as* the criterion. Corrected. See **C-3** and §10.6.
- **Two fixture annotations claimed coverage they did not provide**, in `test_gwenc.py` and
  repeated in TESTS.md: `all 0xFF` was said to make the *literal* table take the all-skip
  zero-length shape (measured: an ordinary 3-symbol table declared 285; the zero-length one
  is the *distance* table), and `incompressible` was said to leave the distance table empty
  (measured: 101 matches and a full 30-symbol table). Both shapes are covered by other
  fixtures — but **nothing asserted the mapping, so the comments drifted from the artifact.**
  That is the same defect §3's window-edge "genuinely REACHED" assertion exists to prevent,
  applied to only one of the fixtures that needed it. Corrected in both files.
- **My brief's zero-length premise was wrong** (§13.4), and the skeptic's refutation of it
  produced the rung's best result. Recorded because the error was mine and it was confident.

### 13.7 What stands between here and A8

**A8 is "a row THIS PROJECT COMPRESSED, read by the retail client."** Still missing:

1. **The `datwrite` compression-8 arm** — a verb that writes `len(new)` as the size, **keeps
   compression 8**, and CRCs the *stored* bytes. Every mechanic is proven by the
   `restore`/donor path (`datwrite.py:610-614`); it was deliberately excluded from A7b so
   that building the writer and wiring it into a 4.2 GB file were not the same change.
2. **The safety gates** of §5.6 — `--preflight`, `--generations`, `--crc-sweep`, `--diff`
   against a pre-write snapshot, and the backup. **Never launch on a suspect archive.**
3. **The owner at the keyboard.** `gwdat` is still ours; §13.2 and §13.4 make it much more
   likely to be right than it was, but only the client can settle it.

---

## 14. The `datwrite` compression-8 arm — and four holes the skeptics drove through it

The verb exists and works. **The more useful output of this rung is that a hostile read found
FOUR ways to reach C-6's failure class through code that had just been written to prevent
it**, and all four are the same shape: a guard whose label claims more than the artifact does.

### 14.1 What was built

**The write verb.** `Writer.replace(row, data, *, compression=..., expect=...)` — the
compression code is now an explicit argument rather than a hardcoded 0, defaulting to
`COMPRESSION_STORED` so every existing caller is untouched. Verified end to end on a
**synthetic** archive: payload → `gwenc.encode` → the verb → a fresh `Archive` handle →
`gwdat.decompress` returns the identical payload; the row afterwards says compression 8, the
right size, and `crc32(stored bytes) == e.crc`.

**`declaration_fault(data, compression, expect, stored_lookalike_ok)`**, shared by `datwrite`
(SystemExit) and `datmove` (Refused). For a compressed write the expected payload is
**mandatory**: the function decompresses what is about to be written and compares, refusing
before any byte reaches the archive. That is the only refutation available, because
**`datcheck.py` has zero references to compression codes** and the entry CRC is over the
*stored* bytes, so a wrong payload passes every checksum rule and all ten open-time rules.

**A safe relocation verb for compressed rows finally exists** — `datmove.move(...,
compression=8, expect=payload)` — which is what correction **C-6** said the toolkit lacked.
C-6 was reproduced live first, on a synthetic archive: `gwenc` bytes relocated with the old
`move()` gave a row marked stored, CRC matching, preflight 10 of 10, sweep 0 bad, and
`Archive.read()` returning compressed garbage. **The guard now refuses that exact call, and a
plaintext move — what all six `a4stage*.py` scripts and `deploy.py`'s subprocess do — still
succeeds unchanged.**

**The recon's proposed guard was measurably wrong and was replaced.** It suggested the
two-byte marker `data[2:4] == b"\x01\x02"` that `datalloc.py:432` (historical; the
decode gate sits at `datalloc.py:560` as of 2026-08-20, and checks fidelity too — §17.5) already used, on a
6,000/6,000-vs-0/6,000 split. Measured against real `gwenc` output the marker **misses 41 of
92 streams** — every payload under ~200 B. `looks_compressed()` decides by **decoding**:
recall **600/600** on real comp-8 rows and **92/92** on `gwenc` streams, with **4 false
positives in all 38,621 real stored rows** (rows 177242/177264/177332/177333, flags 0xFF03)
and, in the population that actually matters, **0 of 1,500 decompressed retail payloads** —
so it is not a practical tax on any authoring caller.

### 14.2 The four holes, all found by skeptics, all fixed

| # | the hole | how it was reached |
|---|---|---|
| **1** | The C-6 arm was gated on **`expect is None`**, and `expect == data` is trivially true for *any* bytes | `datwrite.py --replace N --data s.bin --compression 0 --expect s.bin` with genuine `gwenc` output. **Exit 0, preflight 10 of 10, sweep 0 bad, and a log line indistinguishable from an ordinary stored replace.** |
| **2** | **`--overwrite` never reached `declaration_fault`** and never touches the compression field | Make a row legitimately compression 8, then overwrite its stored bytes with same-length plaintext. Accepted; `verify` 0 failures; **`Archive.read()` returns ZERO BYTES with no exception.** C-6's mirror. |
| **3** | **`datalloc.py:432`** (historical; now `:560`, decoding + fidelity, §17.5) gated compression 8 on the marker alone, never decoding — and this is the row **CREATION** path, the one A8 will use | `b"ab\x01\x02efgh"` passes. Worse, `test_datalloc.py` **asserted that acceptance as correct**, pinning the defect. And in the other direction it *refused* real `gwenc` output from small payloads. |
| **4** | The `toobig` check was **labelled** "a compressed payload past the reservation (still a relocation)" and was not testing that | `pattern(3, 40000)` compresses ~12× to 484 B against a 512 B reservation, so it never reached the relocation guard — it was a second copy of the C-6 check wearing a false label, proven by disabling *only* the C-6 arm and watching this line go red. **"A compressed payload too big for its reservation is refused" was UNTESTED.** |

**Fixes.** (1) The arm now consults the decode whether or not `expect` was given; the override
is a separate, deliberately awkward `stored_lookalike_ok` / `--stored-lookalike-ok` which
**prints a line naming C-6 when taken**, because an override that leaves no trace is the same
defect as no override. The old "hatch" control used bytes that do *not* decode — the harmless
half — so a `hatch_real` check now covers the dangerous one, with a control proving the
override still works. (2) `--overwrite` routes through `declaration_fault` against the row's
*existing* code. (3) `datalloc`'s gate is now `looks_compressed`, and the test assertion that
pinned the defect is inverted, with a two-way control: the marker-carrying fake is refused and
a real sub-200-byte `gwenc` stream is accepted. (4) The fixture is incompressible bytes, so it
genuinely exceeds its reservation and genuinely reaches the relocation refusal.

**Floors: `test_datwrite` 87 → 138, `test_datalloc` 98 → 100**, both from real green runs.

### 14.3 The pattern, stated because it is now the arc's most reliable finding

**This is the FOURTH consecutive rung in which a check claimed more than the artifact
delivered** — §10.6's framing model, §12.7's C1 closure, §13.6's two fixture annotations, and
now four at once. Three of those four shipped *after* the previous one was corrected, in files
whose authors had just read the correction.

The instances differ; the shape does not. **A guard is written, a label is attached
describing what it is *for*, and nothing checks that the artifact reaches the state the label
names.** The `toobig` case is the purest example: the same session caught the identical trap
forty lines below and switched to a PRNG payload for exactly this reason, then missed it here.

What has actually worked, every time, is **sabotage**: disable one arm and count which checks
go red. That is how hole 4 was found, and it is the only technique in this arc that has
reliably distinguished a check from a comment. The lesson for the next rung is not "be more
careful with labels" — it is **break each arm on purpose and require a named check to fail.**

### 14.4 What is still open

- **`gwdat` is still our decoder.** `declaration_fault`'s round trip proves agreement, not
  correctness. §13.5's gap A — a declared `symbol_count == 1`, which our encoder emits and
  retail never does — is exactly the shape that passes here and could still be refused by the
  client. **A8 is the only oracle**, and the fix if it fires is already named.
- **`replace()` computes the reservation from the row's CURRENT size**, so a row already
  shrunk cannot be grown back by this path. Irrelevant for a pristine row, fatal for a second
  write onto a row the first one shrank.
- **The journal cost is real**: writing 15018's whole 1,029,632 B reservation produces ~4.1 MB
  of JSON per record, and `Journal.flush` truncates and rewrites the whole file every time
  with no fsync.
- **A third naming disagreement inside one module set:** `archive.py:287-297` calls the
  `nextStream` field `counter` while `datcheck` and `datalloc` call it `next_stream`. Harmless
  today — an in-place rewrite cannot break the chain, which is by row index — but a reader of
  `archive.py` could think there is a counter to bump.
- **CONTESTED and unresolved:** one skeptic reported `vault/exports/unitwrite/rebuilt_worm.dat`
  rewritten during the run, by `test_skelwrite.py` §3, which calls `datmove.move` against a
  `vault/exports` path by design. No real archive was at risk — it is a small archive the test
  builds itself — but the build agent's "vault files written: 0" and its claim to have run
  `test_skelwrite` cannot both be true. Parallel sessions were active (a client launched at
  19:14), so the mtime is not attributable and no process was touched.

---

## 15. A8 is STAGED — and the deploy and the launch are the owner's

`vault/research/archivewrite/a4stage8.py`. **Built and verified 2026-08-18. Not deployed,
not launched.** The staged archive is
`vault/exports/archivewrite/a4run8/Gw.a4run8.dat`.

### 15.1 The edit, and why it is the narrowest possible test

Take row 11196 (file 15018, the hatcher's animation library), decompress it, and
**re-compress the identical bytes with `gwenc`**, then write it back still marked
compression 8. **The payload a reader gets back is byte-for-byte what ArenaNet ships. The
only thing that changes is who compressed it.**

Five earlier runs in this arc changed *content* and asked whether the change appeared; each
could fail for a dozen reasons between the writer and the screen, and §9.3 records that five
of seven produced no usable verdict. This run has exactly one variable, so **no visible
change is the PASS** and any assert is attributable to the encoder alone.

### 15.2 Measured on the staged archive, independently of the script that built it

| | |
|---|---|
| size on disk | **4,198,489,600 B** — unchanged, growth none |
| `datcheck --preflight` | **10/10** |
| surviving MFT generations | **6/6** |
| payload CRC sweep | **177,319 payloads, 0 bad** |
| row 11196 | size **1,011,244**, compression **8**, crc `0xd03ab671` |
| retail's same row | size 1,029,564, compression 8 — **18,320 B larger** |
| stored bytes differ from retail | **yes** (so the client can tell, i.e. the run is testable) |
| decompresses to | **the identical 1,514,855 B payload**, declared 1,514,855 |
| rows changed | **1** |
| neighbours 13738 / 11141 / 11117 / 8295 / 177242 | **byte-identical to retail** |

18,388 B of the reservation's tail was zeroed. The row fit **in place** — no relocation, no
free run, nothing else moved. The new verify-before-commit arm fired and passed on the way
in: *"verified before writing: 1011244 B decompress to the 1514855 B declared (our decoder;
only the client can settle the rest)."*

### 15.3 The prediction, registered before the launch

**The client reads it and nothing visible changes** — same creature, same animations, no
assert. Confidence high, not total, and the reason is §13.5's **gap A**: we emit a declared
`symbol_count == 1` on 3.4% of tables where retail does so **0 times in 138,708 first
blocks**, so byte-identical re-emission structurally cannot cover it and only our own decoder
vouches for it. Against that, A7b re-emitted 3,051 retail rows byte-identically, and decoding
retail's **own** row 8295 with an upstream-faithful table builder **fails** — so `gwdat`'s one
known divergence is required by ArenaNet's archive rather than being our invention.

**If it asserts, the assert names where**, and gap A's fix is already costed: a two-symbol
distance table inside retail's attested envelope, a few bits larger, on a path 138,708 rows
witness. **A size question, not a design one.**

### 15.4 Two defects in the staging script, both mine, both fixed

- `datwrite.Writer` is **not a context manager** — it has `close()`, and every other caller
  (`datmove`, `datalloc`, `iconset`, `rebloat`) uses `try/finally`. Fixed.
- **`datcheck.diff`'s `growth` is `None` when the file did not grow**, and a dict when it did
  (`datcheck.py:998-1001`). Asserting `growth != 0` failed a run whose archive was perfect —
  the size printed 4,198,489,600 B before *and* after. Fixed to `if d["growth"]:`. Worth
  recording rather than tidying away: **it is the same shape as this arc's four other
  corrections** — a check whose label ("the archive grew") did not match what the artifact
  said — except that this time it produced a false RED rather than a false green, which is
  the harmless direction and the first time in five that the error ran that way.

The script resolves its toolkit from a `--toolkit` argument defaulting to main and **prints
the tree and its HEAD commit** (`[tree] C:\gd\Rurik  HEAD 73b6561`), rather than hardcoding a
foreign worktree the way `a4stage6.py` does. Run scripts live in `vault/research/` and are
gitignored by design, so this one is not in the commit.

### 15.5 What happens next, and it is not ours to do

```bash
python C:\gd\Rurik\vault\research\archivewrite\a4stage8.py --deploy
```

then launch and look at the hatcher. `--retail` puts the baseline back.

**The launch is the irreversible step, not the write** (§5.6 rule 1). The client Flushes, and
a repair deletes the whole `nextStream` chain of any row whose CRC mismatches — permanent
after one launch. The archive it would touch is also shared: `vault/run/.../Gw.dat` was
restored to retail at 21:34 on 2026-08-18 by another session, which is **why §2's claim that
"the deployed archive is run 6" is stale** and why nothing here deployed on its own
initiative.

---

## 16. A8 IS GREEN — the retail client read a row this project compressed

**Deployed and launched 2026-08-18 22:16, loopback, pinned build 38797, agent-driven with
the owner's explicit go-ahead.** Capture `vault/captures/harness/20260818T221652`.

### 16.1 The result

`RUN VERDICT: PASS (target: map)` — **eight of eight capture checkpoints**, from
`client keyed the auth channel` to `body is in the map` at t+17.4 s.

**The creature loaded and performed.** `created agent 10 (Hatcher [Collector]) — hostile`,
spawned 300 units out, walked in (`agent 10 walks to (9826,8077)`), `attacks the player`,
and then **cast repeatedly for the rest of the 150-second hold** — skills 276, 253 and 289
cycling. Walk, melee and cast: the three animation classes the arc has been chasing, all
served out of the creature's link set while row 11196 sat in the archive **compressed by us**.

**No assert, anywhere.** A grep for `assert|Assertion|MdlAnim|MdlSeq|MdlLoad|error|crash|
exception|refus` across the whole capture directory — all three server logs and the report —
returns **no matches**.

**And the archive survived the launch**, which is the check that matters most because the
client Flushes and a repair is permanent after one launch:

| after the run | |
|---|---|
| `datcheck --preflight` | **10/10** |
| payload CRC sweep | **177,319 payloads, 0 bad** |
| size on disk | **4,198,489,600 B**, growth none |
| **row 11196** | **size 1,011,244, compression 8, decompresses to 1,514,855 B, declared 1,514,855** |

**Our row was not repaired and not discarded.** Two rows did change — **8315** (88 → 92 B)
and **8316**, both relocated. Those are the client's own scratch rows, and this
independently reproduces `studies/datwrite` §6's observation from a caged session months
ago ("8315 moved and grew 92 → 96 bytes, 8316 moved"). Same two rows, same behaviour,
ordinary play churn — **not a repair touching anything of ours.**

A screenshot from the middle of the hold shows the player and the Hatcher both rendered with
normal proportions in a normal map. That is the predicted null, and for this run it is
confirmation rather than the readout: **the payload is byte-identical to retail's, so if the
client reads our row at all the animation is identical by construction.**

### 16.2 What this does and does not settle

**Does:** ArenaNet's retail client reads compression-8 bytes produced by
`gwmatch` + `gwenc`, decompresses them to the right payload, and animates from them across
locomotion, melee and casting without complaint. **The encoder arc — A6, A7a, A7b — is
finished and the wall this arc opened against is down.** §2.2's standing worry that
"a bit-exact round trip through a wrong decoder proves agreement, not correctness" is
answered by the only oracle that could answer it.

**One envelope claim is directly widened.** §13.5's gap C noted our encoder declares
literal-table `symbol_count` values below retail's attested floor of 258. **The deployed row
declares a minimum of 257** across its 218 tables, and the client read it. That part of gap C
is retired by direct evidence.

**Does NOT: gap A is untouched, because this payload never reached it.** Measured on the
deployed row itself — 109 blocks, 218 tables, **declared literal counts 257–285, declared
distance counts 24–30, and ZERO tables declaring fewer than 2.** The `symbol_count == 1`
shape our encoder emits on 3.4% of a mixed corpus comes from *tiny and degenerate* payloads,
and a 1.5 MB animation library has none. **So A8 says nothing about gap A**, and the fix
stays costed and unspent: a two-symbol distance table inside retail's attested envelope, a
few bits larger, on a path 138,708 rows witness. Anyone compressing a small file should
assume that branch is still unproven.

**Also not settled:** everything §13.5 lists as reachable only through code paths retail
never took — a zero-block stream, the zero-length *literal* table, and three meta indices in
the 16-bit band. This run exercised one large, ordinary payload, not the envelope's edges.

### 16.3 State of the machine

`vault/run/2026-07-29_221c13772c7a/Gw.dat` **is the A8 archive and is left deployed**, verified
clean after the launch. `a4stage8.py --retail` restores the baseline. The run directory is
shared with other sessions; another restored it to retail at 21:34 the same evening.

---

## 17. The authoring hardening — 2026-08-19/20. From "the encoder is proven on one big row" to "the toolkit authors new content"

**What this rung is.** A6–A8 proved the encoder on ONE large, ordinary payload — row 11196,
re-read by the retail client — and run 7 proved content edits in place. What none of that
covered is what authoring actually does: **small files, new rows, second revisions, and the
undo path** — and every one of those had a named, unproven branch. Five recon agents mapped
the gaps (2026-08-19), three builders closed them, three adversarial verifiers attacked the
builds (one REFUTED a builder — §17.5 — and the refutation was closed the same day), and a
sixth agent built the end-to-end flow test. All offline, on synthetic fixtures; no client run.

### 17.1 The recon corrections that re-shaped the work

The load-bearing ones are C-11/C-12/C-13 in §0. Also measured en route, and worth keeping:
the matcher runs at **~0.19 MB/s** of payload in pure Python (row 11196's 1.44 MB in 7.6 s,
peak working set 82 MB, 80 % of the time in `gwmatch`'s `longest()` match-extension loop) —
fine for the authoring loop, recorded so nobody re-derives it; and the U7-era "write the
full 237-sequence animation set back" payload **never persisted** — `datmove`'s refusal
fired before any journal opened, so re-running that question means re-authoring the payload
(`vault/research/unitwrite/2026-08-17-u7/u7prep_hatcher.py --file-id 15018`), now against an
encoder that exists.

### 17.2 The envelope — gaps A, B, the distance half of C, and D, closed at the writer

**Design: the policy lives in a NEW writer-path function**, `gwentropy.authoring_table
(counts, kind)`, called by `gwmatch._fit_table` with `kind` ∈ {lit, dist}.
`table_for_counts` is UNTOUCHED — it feeds `recost()` (§10.1's +8 B) and `literal_only()`
(§10.4), so those recorded numbers are invariant **by construction**, not by re-measurement.

**The floors, each carrying its census:** distance declared ≥ **5** (the minimum over all
32,831 comp-8 rows ≤ 2,048 B in `dat_study`; 2/3/4 are declared by no retail row anywhere);
literal declared ≥ **257** (the minimum of the 218 tables in the row the client READ, §16.2
— deliberately **not** 258, which would have moved that row's bytes). The empty distance
table becomes the all-skip shape declared 5 — bit-for-bit retail rows 8295–8306. A single
symbol at index 0 becomes a **phantom pair** ({s: 1, neighbour: 1}, note `"huffman"`),
because `gwdat`'s `total == 0` fallback can only install symbol `n−1` — declaring 5 for a
lone symbol at index 1 would decode symbol 4 and garbage the payload, which is why the
task's literal spec ("lift declared to 5") could not be taken literally, and why the
all-skip LITERAL shape (0 of 32,831 rows) is also gone. `gwenc.encode(b"")` now raises
(gap D, the encoder side). Gap E — meta indices in the 16-bit band — is **accepted, not
fixed**, with the reason in `gwenc.py`'s docstring: the bands tile structurally, and
avoiding them would distort the partition DP for no attested benefit.

**The acceptance criterion, measured three ways: the A8 anchor did not move.** Row 11196
encodes to the same 1,011,244 B with crc32 **`0xd03ab671`** — §15.2's own recorded staged-row
crc, i.e. the bytes the retail client read. A verifier reconstructed the PRE-change policy in
memory and compared whole `bytes` objects: identical; the anchor's 218 tables declare lit
257–285 / dist 24–30, so none enters a lifted arm. The crc is now **pinned in `test_gwenc`
§7** so byte drift (not merely size drift) goes red. And `recost()` on retail rows is
unmoved — 900-row sample, zero blocks whose counts reach a patched arm.

**Cost of the lift: zero where it matters.** 120 real small retail rows re-encoded:
**120 unchanged, +0 B total.** Real payloads with one match already declare ≥ 257 naturally.
The whole cost lands on degenerate synthetics (+156 B over the 14-fixture corpus, worst case
RLE at 92→144 B) — the shapes that were the gap. **A verifier fuzzed 118 encodes / 336
tables read back OFF THE WIRE** (traced from emitted bytes, not from the planner): zero
escapes, every payload round-tripping, lit 257–285, dist 5–30, zero-length tables only ever
the attested all-skip distance shape. `test_gwenc` §8 is the standing envelope sweep, with
two sabotage arms (planted faults must be NAMED; the pre-envelope builder restored in
memory must turn the sweep red). Floor 55 → **60**.

**What the envelope does NOT prove: the client.** Every shape our encoder now emits is
attested in retail's archive or in the A8 row — but no retail client has read OUR output on
a small payload or a new row. That is a one-launch question of A8's shape, whenever a
launch is next convenient; until then anyone compressing small files rides attested shapes
plus our decoder, which is a materially better position than gap A's, not a proof.

### 17.3 The grow-back verb — `replace(grow_to=)`, and `restore()` upgraded by the factoring

**The defect (§14.4, now reproduced and priced):** `datwrite.py:821` derived the ceiling
from `e.size`, the row's CURRENT size — an inline fourth copy of `reservation_for()`. Shrink
row 4 of the fixture to 100 B and its own 1,024 B extent caps at 512: the original payload
is refused as "a relocation" with the freed blocks claimed by NOBODY (`claimants()` == []).
On the real archive, row 11196 shrunk once would lose **1,025,536 B of its own space** — and
the authoring loop's second iteration IS a write onto a row the first one shrank. The MFT
records `size`, never a reservation, so the original allocation is unrecoverable from the
archive; the bound has to come from geometry plus the caller.

**Design: an explicit ceiling, never a greedy annex.** `grow_to=` is a keyword-only
statement of the row's entitlement; with it unset, NOT ONE new check runs (asserted, and
every caller in tree and vault is on that path). Greedy geometry-max is rejected in the
docstring because `claimants()` computes each NEIGHBOUR's reservation from its current size
too — geometry cannot tell a free block from a shrunk neighbour's wanted-back one. The gate
is **`Writer._grow_gate`, one copy shared with `restore()`** (checked on the syntax tree),
four conditions where `restore()` had one: claimants; an EOF bound (refused BEFORE the
write — `datcheck` rule 5 tests `offset + size`, not the rounded reservation); the live MFT
against the header's own `mft_offset`/`mft_size`, independent of row 3 (proven by sabotage:
claimants stubbed to [], the MFT arm still fires); and `datplan.classify_runs`' withheld
container runs, quoting `Exclusion.why()` — the largest new risk, since `replace()` never
allocated before. **`restore()` gained conditions 2–4 by the factoring** — and it is the
verb already used on real 4.2 GB copies; a `--restore` into a withheld run was accepted
before and is refused now. The journal record covers the WHOLE new reservation and names
the annexation; post-write, the grow path runs `datmove.overlaps()` and reads the payload
back through the raw handle. The refusal now picks its remedy FROM the geometry: blocks
free → names `--grow-to`; blocks claimed → the old sentence.

**The verifier's strongest result is about the shape of the residual risk.** The recon's
"grow past a shrunk live neighbour" construction is **geometrically impossible** — a grow
runs upward from the row's own offset and must cross the neighbour's head, which claimants
sees at full reservation. The only reachable form is a ZERO-SIZE neighbour (`replace(row,
b"")` — rebloat's own arm), which every allocator in the stack treats as owning no extent;
a stated `grow_to` can then annex the armed head's former blocks. Measured: **fully
revertible** (the journal covers the annexed range), and the follow-on rebloat refuses
loudly rather than silently. Recorded as the design's stated tradeoff, not a defect. Also
recorded: `_grow_gate` judges against the `Writer.__init__` snapshot, like `claimants()`
always has — stated in the docstring. An interrupted grow was killed at **every** put()
boundary and restored byte-identically each time, annexed region included.

### 17.4 The journal — from a liability to a durable file

**Measured first (§14.4 understated it):** hex encoding is 4.00×; `flush()` truncated and
re-serialised the whole document per record — **4.66× write amplification** on a 5-record
fixture replace, **34.1× / 533 MB** on the real `a4run7-flip.journal` (137× the archive
bytes its 60 records protect, quadratic in record count); no fsync anywhere, while `put()`
fsyncs the archive it is supposed to precede; and a torn flush lost the WHOLE journal — an
unhandled `JSONDecodeError` out of `revert()`, a traceback on the one tool that exists for
that moment.

**The fix, and one deliberate deviation from the spec.** Append-only, one record per line,
`os.fsync` per record, opened LAZILY so a refusal still leaves no journal. The spec said
headerless JSONL; the builder kept the file **a valid JSON document at every fsync
boundary** (header once, records appended, only the 3-byte closer rewritten) because
`test_datalloc.py`'s prefix replay reads journals with a plain `json.load(fh)["edits"]` and
59 real journals sit under `vault/` — every reader keeps working with zero migration. Every
measurable goal held anyway: **4.66× → 1.00×**, five truncating opens → one, zero fsyncs →
one per record, each with a sabotage that drops it back. A journal cut mid-record replays
every complete record and REPORTS the dropped byte count; cut mid-header it is a named
refusal; pure junk is refused without opening an archive. A verifier drove **4,743
truncation offsets** without escaping a traceback or losing a durable record. Old-format
replay is checked against a SYNTHESISED journal — the test never opens the vault.
`test_datwrite` floor 138 → **199**.

### 17.5 The creation path — the skeptic's RED, and the fidelity gate it bought

§14.2's hole-3 fix made `datalloc`'s gate DECODE — and that reading was itself the trap
(C-13): decoding refutes **framing** damage only. The stream's trailer is the decode loop's
own bound, so a corrupted trailer "agrees with itself" — over 528 single-byte flips of one
real stream, 394 decoded to the wrong bytes and were ACCEPTED; a corrupted-trailer stream
went to disk through `alloc(confirm=True)` AND the CLI, green everywhere. `datmove` and
`replace()` both refuse the identical bytes; `declaration_fault`'s docstring had already
said the quiet part ("for compression 8 the expected payload is MANDATORY") and `datalloc`
never called it.

**Closed 2026-08-20, `datmove`'s shape:** `Stream` carries `expect=` (mandatory with
`extraBytes 8`) and `stored_lookalike_ok=`; every stream routes through
`datwrite.declaration_fault` — which also brings the compression-0 direction, the stored
lookalike §13 had recorded as an OPEN GAP (hatch cost: 4 in 38,621 real stored rows). The
gate runs in **`alloc()` as well as `plan_alloc()`**, because `alloc(plan=P)` ran neither
and a doctored plan had written `extraBytes 8` over plainly stored bytes; a plan whose
`extra_bytes` disagree with its streams is refused outright. CLI: `--expect FILE`, one
compressed stream per invocation, malformed `--stream` specs refused by grammar instead of
falling through to a file open. Twelve sabotages, all twelve red; the sharpest —
`declaration_fault` stubbed to `None` — puts the corrupted stream back on disk in a green
archive, which is the defect exhibited rather than described. `test_datalloc` floor 142
(was 98 at HEAD) → **177**.

**Also new on this path:** the end-to-end comp-8 allocation itself — until this rung nothing
had ever pushed `alloc(..., confirm=True)` with a real `gwenc` stream and read it back —
and the CLI form `--stream FILE[:FLAGS[:EXTRA]]`. Pre-existing and left open, recorded:
`plan_alloc` accepts a plain id whose bit-31 renamed spelling exists while
`next_free_file_id` skips it (the dual-registration family, worth its own look before
anyone allocates near a renamed id).

### 17.6 The flow test — `test_authorflow.py`, the sequence nothing else measures

Every verb has its own green suite; this arc's two worst defects (C-6, §14.4) were both
**compositional** — green in isolation on the day. So: one synthetic archive, six steps at
compression 8 throughout — AUTHOR (four revisions of an invented file, one of them gap A's
own RLE shape, with both table builders called on the same counts so the old declared-1 and
the new declared-5 sit in one check), CREATE (a new file id, head + partner, `expect=`
declared), REVISE smaller through the real CLI, GROW back with `--grow-to` (the step that
was impossible before this rung), OUTGROW (refused, with the remedy sentence CHOSEN by
geometry — step 4 gets the `--grow-to` branch, step 5 the other) and relocate via
`datmove.move(compression=8, expect=)`, then UNDO — four journals replayed newest first,
**composing back to the pristine fixture byte-for-byte with every intermediate state
checked**, the file id unregistered again. Every step is checked by DECODE, never by a
checksum, because no checksum in this format can tell a comp-8 row holding the wrong
payload from the right one. Step 2b corrupts the authored stream three ways and it now
takes TWO gates to catch them (measured: `looks_compressed` stubbed alone, 1 red;
`declaration_fault` alone, 3; both, 4 — and the corrupted stream reaches disk). Floor
**59**, half a second, no vault, no client.

### 17.7 Process notes, for the next rung

- **The skeptic pattern paid for the fifth consecutive rung** (§14.3 counted four): a
  builder's "proven end to end" was true of framing and the happy path, and the
  fidelity direction reached disk. Sabotage — break one arm, count which checks go red —
  again found what review prose did not.
- **Concurrent builders on disjoint files worked, with one seam**: `test_datwrite`'s new
  §11j names `gwenc._refuse_zero_block`, so `datwrite`+`gwenc` had to land in one commit —
  cross-file coupling through a test is the thing to look for when splitting work.
- Line-citation drift is real cost: ~15 citations into `datalloc.py`/`gwenc.py`/`gwmatch.py`
  moved and were re-resolved against the final tree. Nothing enforces these
  (`test_srclint` has no citation checker); they were repaired by hand because they are
  the repo's audit mechanism, not because anything went red.

### 17.8 What is still open, all named elsewhere but collected here

1. **The client oracle for the new shapes** (§17.2): a one-launch run reading a small
   authored row AND a `datalloc`-created row, when a launch is next convenient.
   **STAGED 2026-08-20 as A9 — §18. RAN the same morning — §18.6, GREEN**: the client
   read the created chain and the small rows; still open afterwards are only the shapes
   no real payload produces (the phantom pairs) and E3's unwitnessed rider.
2. **The FA1 full-set write-back** (§17.1): the payload must be re-authored; the encoder,
   the write verbs and the budget arithmetic all exist now.
   **STAGED 2026-08-20 as A10 — §19.** The U7-era edit turned out to be structurally a
   null; the re-authored payload retimes the PROVEN clock instead, and the stage is
   built, blind-re-derived and byte-reproducible. The launch is the owner's.
3. **A5** stays unrun (stored-size ceiling; §5 D), unchanged by this rung.
4. The renamed-id disagreement in `datalloc` (§17.5), the `_grow_gate` snapshot semantics
   (§17.3), and gap E (accepted, §17.2).

---

## 18. A9 is STAGED — 2026-08-20. The client oracle for §17's shapes, built, gated and adversarially verified; the deploy and the launch are the owner's

**The rung: one loopback launch answers what §17 could not** — does the retail client read
(a) small rows compressed by us, (b) a row `datalloc` CREATED under a new file id, and
(c) the one degenerate table shape reachable on a real payload. Script and runbook:
`vault/research/archivewrite/a9stage.py` + `A9-RUN.md` (gitignored by design, like every
stage in this arc); staged archive `vault/exports/archivewrite/a9/Gw.a9.dat`, 4.2 GB.

### 18.1 The measurement that designed it, four decisive facts

- **All sixteen proven-read files fit their own reservations under our encoder at the DP
  dial — including 222949.** §11.6's "12 B over at every dial" was measured on the *flipped*
  payload; unmodified, ours is 7,644 B — the same size as retail's to the byte, different
  bytes (crc `0x624BFFA2` vs `0xA1A26950`). C-2's rule held: name the copy
  (`run/2026-07-29…/Gw.dat.retail` throughout).
- **The verdict fires at LOAD, not at an animation lottery.** The client's FA8 loop
  (`0x00794850–0x0079492D`) resolves EVERY link at model load and requires
  `m_seqCount != 0` per link — so "the hatcher spawned with normal proportions and
  animated" IS the statement that all fifteen links, including a created row, resolved,
  decompressed and parsed. 100 % readout coverage; no dependence on which of 242 sequence
  records the variant picker rolls.
- **Two of the four target shapes are UNSHIPPABLE on real content, and are recorded, not
  forced**: the phantom-pair distance and phantom-pair literal tables occur zero times over
  17 files × 6 dials, 900 random small rows and the 2,500 most compressible rows in the
  archive. Their client oracle waits for a payload that legitimately produces them.
- **The all-skip declared-5 distance shape lives in exactly one family** — rows 8295–8306
  (twelve 56/60 B rows, 6,146 B payloads, static registered content, definitely not
  scratch). Whether the client reads them at map load is UNRESOLVED — the map-dependency
  search's null FAILED ITS POSITIVE CONTROL (the same list omits the shell, the body and
  15018, all demonstrably loaded), so the null is worth nothing and the arm is a
  zero-cost rider scored "nothing asserted", never the shape oracle.

### 18.2 The edit set (3 rows in place, 3 created, size unchanged, nothing relocated)

**E1, the headline:** file `0x5F0AD` created by `datalloc.alloc` — a 3-stream chain
mirroring 222949's (head = our encode of its 11,878 B payload, 7,644 B, `expect=`
declared; mid and tail = the sibling rows' stored bytes verbatim), landing on rows
[35301 (retail's only spare, reused), 177335, 177336]. Through the Python API — the chain
has two compression-8 streams and the CLI takes one `--expect` per invocation, a §17.5
refusal doing its job. **E2, the reader:** the shell's FA8 record 13 retargeted
222949 → `0x5F0AD` (a 4-byte splice at container offset 29790, exactly 3 bytes differ),
shell re-encoded in place at 20,060 B — transport witnessed by run 7 on this exact row,
which is what keeps an E1 failure attributable (H9). Retargeting touches only the hatcher:
28 other shells link 222949 and keep retail's copy. **E3, the rider:** rows 8295–8306
re-encoded in place, payloads byte-identical, our bytes carrying the attested all-skip
declared-5 shape on the wire (traced).

### 18.3 The nine hazards the A8 skeleton did not guard, all gated

H1 MFT slack (the sharp one: the ACTIVE archive shows one client texture session consumed
ALL nine slack rows and the only spare; the stage leaves 168 B / 7 rows, floor-gated
post-write with zero margin); H2 identity on both writers (file-id walk, chain walk,
payload byte-compares); H3 the retarget gated positively (FA8 decode == retail's fifteen
with index 13 swapped); H4 retarget-squared (size+crc fingerprints — size alone cannot see
a 3-byte, 0-length edit); H5 the id pinned, never recomputed; H6 crc-sweep counts read
from the sweep (+3); H7 our chain ascends where retail's descends (recorded in the
prediction's failure short-list); H8 the shared run directory (deploy refuses without
`--yes`, probes the file handle, and another session WAS in it at 00:11 on 2026-08-20);
H9 the E1/E2 joint-failure cell attributed in advance.

### 18.4 The adversarial pass — GREEN, and the artifact is reproducible

The skeptic's decisive result: **a from-scratch rebuild in an isolated vault produced a
byte-identical 4.2 GB archive** (sha256 `ac3fe9e1…af0caa90`), twice. Its own instruments
(never the builder's code): the whole-file byte diff resolves to **14 regions, every byte
owned by exactly the intended rows** plus the alloc's documented structural writes — no
stray owner anywhere; all pinned constants reproduced; preflight 10/10 / generations 6/6 /
crc sweep 177,322 (+3, 0 bad) on the stage; five hostile-input gate falsifications all
refused loudly with the stage byte-unchanged. Three non-blocking findings, two fixed
same-day (F1: the PRE-write H1 arm was a check that cannot fail — deleted, the binding
post-write gate stands; F2: rebuild-over-stage recopies 4.2 GB — now in the runbook) and
one recorded (F3: `--retail` discarding the client's ATEX rows is followed by a green
launch in two precedents, but "the client recompiles them" stays an inference). One of the
skeptic's own 59 checks went red and **retail's own row was the control that corrected the
skeptic**: `dist_lens [(0, 4)]` on an all-skip table is the installed symbol, not a code
length — both streams carry the identical shape.

### 18.5 The predictions, pre-registered (verbatim in `a9stage.py`'s docstring)

P1 stage gates (all fired green 2026-08-20). P2 the launch: 8/8 checkpoints, hatcher
spawns with normal proportions and walks/attacks/casts — which by §18.1's load-time fact
is the statement that the created row resolved; no assert dialog, and **never click the
dialog** (its default button uploads a crash dump from a patched client to ArenaNet).
P3 post-launch (`--verify-after`): our 16 rows byte-identical, only scratch churn,
`entry_count`/`mft_size`/`mft_offset` unmoved. P4 named failures: missing creature /
white box / error 12 at `0x0079644E` / AV ⇒ the creation path, with H7's chain direction
on the short list; E3 scores "nothing asserted" whatever happens. **The run is the
owner's**: deploy with the client closed, `python toolkit/harness/session.py --enemy
--hold 150 --shots 10`, then `--verify-after`, then `--retail` or leave deployed.
`A9-RUN.md` is the procedure.

### 18.6 A9 RAN — 2026-08-20, ~09:40, owner-driven, and it is GREEN on every pre-registered prediction

**THE RETAIL CLIENT READ A ROW THIS PROJECT CREATED.** Owner at the keyboard, loopback,
pinned build 38797 (the server's own log shows it re-selecting the matching 38797 keyring):
deploy → launch → *"Hatcher with normal animations/proportions"* → owner closed the client
→ `--verify-after`. By §18.1's load-time fact — the FA8 loop resolves EVERY link at model
load and requires `m_seqCount != 0` — a normal, animating hatcher **is** the statement
that the `datalloc`-created chain (file `0x5F0AD`, rows 35301/177335/177336, two of the
three appended to the MFT by us) was resolved by id, decompressed from our compression-8
bytes, and parsed as a skeleton; and that the retargeted 20,060 B shell — a SMALL row
compressed by us — was read on the way there.

**P2, the instrumented half** (capture `vault/captures/harness/20260820T094015`): `created
agent 10 (Hatcher [Collector]) — hostile`, then **37 `walks to` cycles and 54
attack/cast lines** in the gamesrv log — locomotion, melee and casting, the three classes
this arc has always used as the bar (run 7 asked for ≥ 3 walk cycles; this run has 37).
**No `crash-dialog.txt` exists** — the one machine-readable assert channel is absent.
Honest gap: **`report.json` was never written** because the owner closed the client during
the hold, so the 8/8 checkpoint table for this run does not exist; the verdict rests on
the owner's observation, the gamesrv log and the archive sweep, and none of those three
needed it. The capture's only `error` lines are the documented clean-teardown
`ConnectionResetError` (session.py:1155's own caveat). The `377` grep hits are the
logger's `[377]` tag, not file-id mentions — nothing asserted from `Gw.log`, as
pre-committed.

**P3, the archive — every line green**: preflight 10/10, generations 6/6, crc sweep
**177,322 payloads 0 bad** (the +3 from our alloc, per H6), size unchanged, `growth:
None`. Rows changed since deploy: **2 — 8315 and 8316**, the client's own scratch rows,
relocated exactly as in A8 and `studies/datwrite` §6; `tier0` shows only
`descriptor_counter` (the client Flushed — which makes the next line the strong one).
**Our 16 rows are byte-identical to what was deployed, `0x5F0AD` still binds to row
35301, and the chain [35301, 177335, 177336] is intact** — the created rows SURVIVED the
client's Flush, so nothing was repaired or discarded. `entry_count`/`mft_size`/
`mft_offset` unmoved at 177,337 / 4,256,088 / `0xF8FFF000`: **H1's fear did not fire this
session** (the client wanted no MFT slack), and H7 is answered in passing — **the client
accepted our ASCENDING chain** where every retail chain descends.

**What this settles, added to §16.2's ledger:** the creation path is client-proven —
`datalloc` + `gwenc` + the fidelity gate produce rows the retail client loads, for one
chain shape on one build. Small-row compression is client-proven at 20,060 B and at
7,644 B stored. **What it deliberately does not settle:** E3 stays scored *nothing
asserted* — the twelve rider rows came through the launch intact like everything else,
but no instrument shows the client opened them, so the all-skip declared-5 shape still
has no client witness, and the two phantom-pair shapes remain unshippable-and-unproven
(§18.1). The caveat sentence this run retires ("no client has ever read a row this module
allocated") is superseded in `datalloc.py`'s docstring and TESTS.md's entry, scope stated.

**State of the machine after the run: the A9 archive is LEFT DEPLOYED** in
`vault/run/2026-07-29_221c13772c7a/` (verified clean by the sweep above; the owner has not
run `--retail`). `a9stage.py --retail --yes` restores the baseline; the staged copy under
`vault/exports/archivewrite/a9/` stays rebuildable-by-hash either way.

---

## 19. A10 is STAGED — 2026-08-20. The FA1 write-back, re-authored onto the PROVEN clock; the launch is the owner's

**The rung.** §17.8 item 2 asked for the U7-era "full animation set" write-back — the edit
`datmove` refused pre-encoder (*"nothing fits… 953,856 B"*), whose payload never persisted.
Script + runbook: `vault/research/archivewrite/a10stage.py` + `A10-RUN.md`; staged archive
`vault/exports/archivewrite/a10/Gw.a10.dat`. **15 rows rewritten in place at compression 8,
nothing allocated, nothing relocated, MFT untouched.**

### 19.1 The U7-era edit was structurally a NULL, and that is the design's first finding

`u7prep_hatcher.py --file-id 15018` would have scaled the **n3C key table** — 471 B of
1,514,560, 0.031%. That table is not what the sampler reads: **the motion lives in
`blk2C`'s 76,008 per-node channel key times (304,032 B), and the sequence clamp windows
ride the SAME clock** — both max at exactly **22,883,332** on 15018, while the n3C table
maxes at 580,000 and its binding to `start` was already refuted
(`studies/anim/FINDINGS.md:316-318`, 181/21,535). So U7's shell-retime null was
over-determined: it retimed a tag track. Also measured at population for the first time:
**242/242** of the shell's records (and 237/237 of 15018's own — it carries its own FA8
list) hold their `(start, end, u32_0F, f32_13)` verbatim in the file their selector names.
Run 3's failure was breaking that one-sided; this design's whole shape is the fix.

### 19.2 The edit — DESIGN B, and how it got that name

**Scale ONLY the proven clock, ×4:** every `blk2C`/`blk48` channel key time in fourteen
files (222949 dropped — its ×4 fit was +4 B, the knife edge §18.1 already recorded), and
every sequence record's start/end **iff the file its selector names was retimed** — 234 of
the shell's 242 (the 2 selector-0 records address the shell's own unscaled curves; the 6
selector-14 point at untouched 222949), 231 of 15018's 237. **Everything else stays retail
everywhere**: the n3C table, `u32_0F`, `f32_13`, the n40 sound events, n3E.

Two rounds got it there, and both catches are worth the record:
- **The build agent caught the ratified spec contradicting itself** (rule vs count on the
  shell's windows) — and, bigger, that the recon's pinned 15018 number came from a variant
  scaling only its 110 selector-0 windows, leaving **121 records with retail windows over
  ×4 curves** in the file that carries the walk: exactly what the coupling invariant
  forbids. It stopped, measured, adjudicated by the archive, and reproduced the spec's
  pinned number to the byte as an anchor proving the divergence was the rule, not the
  encoder.
- **The first adversarial pass (Design A: n3C/n40/n3E also ×4) was GREEN on everything
  asked — and its F4 found what the design missed**: `u32_0F` is statistically a clock
  into the file's own n3C table (12/12 membership on both FA8 carriers, ~0.01% null), so
  scaling the table while leaving the lookups half-moves a second coupling; and chasing it
  shows no partial scaling preserves both measured couplings. **Design B moves neither
  half.** The membership statistic became a gate with a control that drops 12→1 against a
  ×4 table — Design A's own shipped state, now provably refusable.

### 19.3 The verification — blind re-derivation, with a discriminating control

The skeptic implemented the edit from the ruling prose alone, before reading the builder's
code: **15/15 staged rows byte-identical to its independent derivation**, with a Design-A
control alongside that goes RED on 11 of 15 files — the stage provably encodes Design B.
Also: couplings 242/242 + 237/237 on both match rules with controls that collapse to
≤9/242; **260,240 channel values compared, 0 changed — only clocks moved**, every ratio
exactly 4.0 (shell's own 970 channel times and 222949 at 1.0); whole-4.2 GB diff with
**zero unowned bytes** (the one 4-byte stray resolved to the MFT self-crc the journal
itself announces); envelope clean on all 349 tables; sweep equal to retail's 177,319/0;
**two isolated rebuilds hash-identical to the shipped artifact**; ×16 double-apply
impossible from the code path (the build only ever reads retail, crc-pinned). Fit
highlights (Design B, measured): 15018 **1,016,720 B** (+12,912 slack), 87333
**1,148,528 B** (+13,200), the shell **20,092 B** (+388) — full per-row table in
`A10-RUN.md` §3 and `a10-fingerprints.json`; every row inside its own reservation, every
reservation exactly the gap to the next row, 0 overshoots.

### 19.4 Predictions, pre-registered (verbatim in the docstring) — BOTH branches are findings

**P1**: with the curve clock and the windows ×4 together, the creature animates at **one
quarter speed** — the readout cues in shape-likeness order: **foot slide** (server ground
speed unchanged, cycle ×4), attack swing vs the damage tick, cast vs the server's cast
lifecycle. **P2**: nothing changes → playback rate does not live in the linked key tables
or the windows — sharpening `studies/anim`'s open timing question, and NOT dismissible as
"file not read" (run 7 proved this channel reaches the screen). **P3** ordered failures:
N2 first (×4 puts 15018 at 915.3 s, 3.09× beyond retail's 296.0 s corpus ceiling — the
envelope risk, named, not hidden); unscaled n40/n3C events misaligning is cosmetic and not
the readout; truncate-or-freeze → re-check the coupling gates. **N6**: no within-frame
control exists (both selector-0 records are empty spans), so the owner records a BASELINE
clip of the provoked walk before deploying — and **video, not stills**. Corrections banked
en route: the blast radius is **28 other shells** linking 15018 (30 rows total over the
retimed set, 252 FA8 carriers as the positive control), not the 7 a row-band scan showed;
the recon's "34 of 44" membership denominator is not reproducible (34 of 48 by per-file
distinct; the numerator is exact); and Design B is NOT uniformly smaller than Design A
(66614/73940 +4 B each — encoders are not monotone; a pre-registered prediction refuted
and kept).

### 19.5 State, and the one operational flag

The stage is BUILT and verified; **`--deploy` has not run**. The active run-directory
archive is currently retail-on-all-16-A10-rows (measured — NOT the A9 stage, despite what
two documents briefly claimed; `baseline_premise()` now measures this at deploy time
instead of trusting prose). **H8 is live**: a client ran against the shared run directory
at 11:44 on 2026-08-20 from outside this session — confirm nobody is mid-run before
deploying. Procedure: baseline clip → `a10stage.py --deploy --yes` (client closed) →
`python toolkit/harness/session.py --enemy --warn 0 --hold 420 --shots 10 --walk
"zoom:-12 pitch:300 alt:3 shot:1 wait:4"` → video the walk → `--verify-after` →
`--retail --yes` or leave deployed. Never click the crash dialog.

---

## Appendix — what I verified myself

**OBSERVED (mine), run read-only in `C:/gd/Rurik/.claude/worktrees/great-heyrovsky-7fe716`, vault located via `toolkit/vaultpath.py` → `C:\gd\Rurik\vault`:**

- Row geometry and ratios for both anchors (§1.1) — reproduced byte-exact.
- `zlib -9` raw/-15/memLevel 8 on the real payload → 1,020,039 B; **the +4 trailer correction (C-3) is mine**.
- The free-map table in §1.4 via `datplan.free_runs` / `classify_runs` — 953,856 and 2,892,800 reproduced.
- **The full FA8 link table in §1.6, from scratch through `mdlrefs.RefList`** — 15 records, all 15 resolvable, 15018 first, 13 duplicated inside 15018's own FA8.
- **Sequence counts per linked file and the 242 / 237 / 385 / 627 arithmetic — new, taken by nobody in the dossier.**
- Source cites: `datmove.py:160-192`, `:215-232` (**C-6**); `datwrite.py:488-512`, `:96-106`; `archive.py:316-330` (**C-7**); `datcheck.py:220-228`; `datplan.py:219-249`; `datalloc.py:45-60`.

**Not mine, and labelled as such throughout:** the 661-row sweep, the population compression sampling, the deflate level sweep, the Route C re-entry simulation, the `dat_study_38833` arena prediction, the grown-archive geometry, and every client-side VA. Where two agents agreed on a number independently I say so; where only one produced it, it is theirs.

**No client or server was launched. Nothing under `vault/` was modified. No tracked file was edited. Nothing was committed.**

---

## Appendix B — what the orchestrator verified independently

Four checks, run after both dossiers landed, chosen because each was a claim that would be
expensive to get wrong. All read-only.

1. **The §1.1 headline, re-measured from scratch.** File 15018 → row 11196, offset
   `0x29BF2200`, stored **1,029,564 B**, compression 8, flags `0x0203`, reservation
   **1,029,632 B** (68 B slack), payload **1,514,855 B**, retail ratio **0.679645**. And
   the shell 116228 → row 13738, stored 20,236 B, reservation 20,480 B, payload 29,802 B,
   ratio 0.679015 — **the two rows agree to four decimal places**, which is its own small
   piece of evidence about ArenaNet's encoder being uniform on this data. `zlib -9`
   raw/`-15`/memLevel **9** gives 1,025,896 B (+4 trailer = 1,025,900), fitting the
   reservation by **3,732 B** — the figure §6 quotes as the upper end of the authoring
   budget. (The scout's 1,020,039 B used memLevel 8; both fit, and the difference is inside
   deflate's tuning range, which is itself §1.2's point.)

2. **C-6 confirmed, and narrowed.** `datmove.py` writes
   `struct.pack("<H", 0)` to `ENTRY_COMP_OFF` unconditionally and CRCs over the bytes it
   was handed. This is *coherent* for its designed use — you hand it plaintext, it marks the
   row stored. The trap is that **there is no verbatim relocation mode**: hand it a
   compression-8 row's stored bytes to move them and it produces a row flagged stored while
   the bytes are still compressed, and every checksum rule and all ten open-time rules still
   pass. State the defect as *"no safe relocation verb exists for compressed rows"* rather
   than *"datmove corrupts archives today"* — the distinction matters for A3's scope.

3. **C-7 confirmed exactly.** `archive.py:322` reads the header `mftOffset` as `<I`;
   `datcheck.py:223` and `datwrite.py:101` read it as `<Q`. Two of three say u64 and the
   outlier is the one every tool imports. **This directly caps Route B**: `dat_study`'s live
   MFT sits at `0xF8BEFE00` = 4,173,332,992, which is **121,634,304 bytes** below the u32
   ceiling. Grow the archive past that and `archive.py` silently reads a truncated offset.
   Any growth verb needs this fixed *first*, not as cleanup.

4. **§5.4's generation census — new, and the reason §5 is scored PARTIALLY rather than
   NO.** Full scan of all 8,200,175 512-byte-aligned offsets for the descriptor magic with
   `+0x08 == 0`. Six candidates, counters 26,881 (live) / 26,880 / 26,879 / 26,872 / 13,101
   / 8,735. Upper bound only — shape gate, not `LoadMft`'s full validation. This should
   become `datcheck --generations` in A3; the scan is ~40 lines and one pass of the file.

5. **The §5.2 funnel, cross-checked without a disassembler.** `asserts.py --at 0x0047B650`
   returns ArenaNet's own line set for that function (`ExeArchive.cpp` 2592, 2615, 2661,
   2665, 2679, 2718, 2725 `!m_dirty`, 2727 `m_writeState == STATE_READY`), confirming the
   function identification rests on their line numbers rather than on a string's wording.
   `--callers 0x0047B650` → exactly **1** direct caller; `--callers 0x0047A290`
   (`ArchiveCreate`) → **0**, consistent with it being reached by a jump rather than a call.
   Note `asserts.py`'s own warning that its site counts are a floor, not a census.