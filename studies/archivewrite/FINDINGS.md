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
| **C-5** | `datalloc.py:53-56`: growth past EOF is "unrevertible in principle" | **Wrong as stated.** Record the pre-growth size in the journal and `os.truncate` on revert; a scout ran it on a synthetic fixture and it restored to 10-of-10 clear. The docstring describes the current JSON schema, not a property of archives. It should be amended to say *why we still refuse* (concurrency and the u32 ceiling, §4.4), not that we cannot. **OBSERVED** (Route B scout) |
| **C-6** | `datmove` is the relocation verb | `datmove.move()` writes **compression → 0 unconditionally** (`toolkit/mapdata/datmove.py:222-224`) and re-CRCs over the bytes it was handed. Relocating any compression-8 row with it produces a **green archive holding an unreadable file** — the entry CRC is over stored bytes, which are unchanged, so all three checksum rules and all ten open-time rules still pass. **OBSERVED (mine, source read; confirmed by two skeptics independently).** This is the single sharpest trap in the stack and it is live today. |
| **C-7** | — | `archive.py:322` reads the header `mftOffset` as **`<I`**; `datcheck.py:223` and `datwrite.py:101` read it as **`<Q`**. Two of three readers say u64 and the outlier is the one every tool imports. Latent (all 14 vault archives have the high dword zero) and ~93 MB of file growth away from firing silently on the 38833 line. **OBSERVED (mine, all three lines read).** |
| **C-8** | — | Two row censuses disagree by 16: 138,708 comp-8 rows (Route E) vs 138,692 (Route C skeptic), against 38,621+12 vs 38,629 comp-0. The sums are 177,341 and 177,321 — `len(entries)` versus live rows. `archive.py:413-431` warns about exactly this and names the study it already corrupted. **Unresolved bookkeeping**, and it is load-bearing for the "661 rows" headline. |

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

*(Incidental, verified: `datcheck.row_fields` (`datcheck.py:260-265`) names entry+0x0C `extra_bytes` while `datmove`/`archive.py` call it `compression`; `datalloc.py:109-111` documents both spellings. Measured across all live rows the field takes only {0, 8} — **it is compression.** Harmless today, but a live naming disagreement inside one module set.)*

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
| **A7** | **`toolkit/mapdata/gwenc.py` + `test_gwenc.py` + the `datwrite` compression-8 arm.** Build the matcher **size-only first** (hash chain, min match 3, 32 KB window, lazy matching) against A6's accountant — no bitstream writer, no round trip — then the writer. Copy the constant stream header (lead bits 0, `first_four = 2`, 4000/4000). Alphabet 0..29. **`PLAN.md` §6.1 register row BEFORE the module exists**, plus THIRD-PARTY-NOTICES. `datwrite` gains a verb that writes `len(new)`, **keeps compression 8**, and CRCs the stored bytes (`restore`/donor path proves every mechanic, `datwrite.py:610-614`). | Hard bar stated up front: **on the real payload, ≤ 1,029,628 B AND `gwdat.decompress` returns the original bytes.** The falsifiable headline in the test is *our compressed size vs ArenaNet's stored size on N real rows*, which can go red. Round-trip over a strided corpus sample. `checks.Ledger` floor from a real green run; TESTS.md in the same commit. **Note the acceptance bar is a RATIO target, not a correctness target** — the success/failure boundary is inside deflate's own tuning range (§1.2), and a level-1-quality matcher misses by 122 KB. | 2–3 sessions |
| **A8** | **SUMMIT: a row THIS PROJECT COMPRESSED, read by the retail client.** Deploy the compression-8 in-place write of 15018 into the loopback build's archive; owner-driven caged run against our server per RUNBOOK. | The client loads the map with the modified archive, does not trip a `MdlLoad`/`MdlSeq`/`MdlAnim` assert (the assert vocabulary is the failure oracle — a crash names its line), and the authored animation is **measured**, not eyeballed. **Kill/keep:** if it fails, the run records **which gate fired** — that failure is itself the result. | 1 run |

**Summit: A8.** What it would prove is the thing nothing else in this stack can: **that our encoder's output is a stream ArenaNet's decompressor accepts, not merely one ours does.** Every route above stops at the same sentence — `datmove.py:62-68`, `datalloc.py:79-86` and `gwdat.py:81-84` each carry a version of it. `datcheck.py` contains **zero** references to compression codes, so no invariant we own can refute a conforming-but-wrong bitstream. **The client is the only oracle, and A8 is the only rung that consults it.**

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