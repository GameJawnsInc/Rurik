# How we find things out — the techniques, and whose they are

**Written 2026-08-29**, from the MOVECODE arc's obstacle dig and the R5 runs, but the
techniques are older than that arc and none of them is specific to it.

**This file mints NO identifiers**, so no word is registered and nothing here needs
checking against [studies/idents/CONVENTION.md](../idents/CONVENTION.md).

**What this is:** a cold-start answer to *"where does a given number in this repo
actually come from, and how much should I trust it?"* — written because the answer is
four different things depending on the number, and the difference is invisible once a
figure has been quoted twice.

**What this is NOT:** the confidence vocabulary itself (that is
[studies/character/FINDINGS.md](../character/FINDINGS.md), and it is not restated here);
the provenance gate (`CLAUDE.md`, and read its second sentence); or status (`PLAN.md`
§3, and nowhere else).

---

## 1. Four layers, and they are not equally trustworthy

| Layer | Source | Trust |
|---|---|---|
| **1. ArenaNet's own words** | assert strings compiled into `Gw.exe` | highest — their statement about their own code |
| **2. The disassembly** | instruction order, offsets, call censuses | high for *what*, ours for *what it means* |
| **3. The data file** | `Gw.dat` chunks, decoded via an upstream layout | a hypothesis, until self-checked |
| **4. Our instruments** | the hook, the scorers, the router | ours entirely, and where our errors live |

Most published mistakes in this repo are a layer-4 artifact wearing a layer-1 costume:
a number measured by our own tool, quoted later as if the client had said it.

---

## 2. Layer 1 — asserts, and the three different jobs they do

ArenaNet shipped `assert(...)` expressions with source paths and line numbers, and the
retail client prints them in its crash dialog to any player who crashes. `asserts.py`
extracts them. They do three distinct jobs:

**(a) A map of the engine.** `P:\Code\Engine\Map\Path\{PathApi, PathData,
PathDataImport, PathBsp, PathBuild, PathDir, PathFlood, PathObstacle}.cpp` — nine files.
That is how we know the pathing subsystem's shape, that obstacles are a module of their
own, and that something is *imported* at load rather than stored.

**(b) Oracles for our own decode.** These are the most valuable and the most
under-used. Each is a claim ArenaNet's code makes about data we can read:

* `PathDir.cpp`: `m_trapezoid->portalLeft < pathMap.portalCount` — our decode holds on
  **3,051 and 3,095** set values, no exception.
* `PathData.cpp`: `src.x < 131071.0f && src.x > -131071.0f` — **273,522 of 273,522**.
* `PathDataImport.cpp`: `!pairRef->portal->pair` — the pairing is **resolved at import,
  not stored**, so the file carries an id to resolve *through*. That one assert is why
  cross-plane connectivity works at all: linking trapezoid → portal → paired portal
  takes Kamadan from 61 components to 4.

**(c) Behavioural facts.** `ChCliBase:164` and `:248` assert that the keyboard-walk and
click-walk entry points run only for the local player. `PathObstacle:176 radius >= 0`
identified the `0x0072xxxx` cluster as the obstacle module.

**The limit, and it has bitten:** `asserts.py`'s count is a **floor**, not a census — it
is short by ~370 sites. So *"no assert names X"* is never evidence that X does not
exist. Anchor a negative on a data structure instead.

**The provenance boundary here is size and source, not kind.** A *single* assert cited
as the evidence for a claim, with its file and line, is a measurement and stays. A
**bulk dump** is ArenaNet's expression and is refused. `CLAUDE.md` carries the ruling and
[studies/provenance/FINDINGS.md](../provenance/FINDINGS.md) the full record — including
the day 46 citations were scrubbed and all 46 reverted.

---

## 3. Layer 2 — what the disassembly gives, and what it does not

Everything with a hex address is measured out of **one pinned build (38797)**. Name
`--exe` explicitly; the default picks 38833 and every movehook address is 38797.

What it gives directly:

* **Struct offsets.** `m_point` is at agent+0x78 and is 16 bytes — `float x, float y,
  int plane, int`. That layout is the reason the plane channel exists at all, and we
  carried the plane in every captured record for weeks before scoring it (§1z-c of the
  MOVECODE findings).
* **Instruction ORDER, which settles causality questions no amount of reasoning can.**
  `0x00602B7B mov [edi],eax` writes the authoritative position *before* the geometry
  query at `0x00602B90`, and the query's result gates only a copy into +0x68. That is
  how we know the client's collision consult is non-gating — read off the order, not
  inferred from behaviour.
* **A test's SHAPE as evidence about design.** The arrival test at `0x006001EB` is
  `now == +0x48`, **exact equality**. An equality test on a clock is only sane if the
  function is *scheduled* for that tick, which is what identified it as a timer callback
  rather than a per-frame poll — later confirmed by capture.
* **Call censuses.** `codescan --xrefs` gives direct `rel32` callers; scanning all
  sections for the address stored as a data word closes the vtable/address-taken hole.
  `0x0070A150`: exactly 5 callers, zero stored VA words image-wide.

What it does **not** give, and where we have been wrong:

* **Meaning.** Calling +0x68 "the display copy" is unlabelled reconstruction — nobody
  has shown who reads it.
* **Reliable exclusions.** A static argument once *ruled out* `AgTimer::Advance` as the
  tick's dispatcher (it pushes no args; the tick is `ret 8`). One breakpoint refuted
  that. **Static reasoning is good at finding candidates and bad at eliminating them.**
* **Indirect flow.** `--xrefs` sees direct branches only.

---

## 4. Layer 3 — an upstream hypothesis, made into evidence by self-checking

The `Gw.dat` pathing layout (trapezoids 44 bytes, portals 9, tag 8 holds planes) comes
from **GuildWarsMapBrowser's ImHex pattern** — upstream, credited in
`THIRD-PARTY-NOTICES.md`, registered in `PLAN.md` §6.1. It is labelled a **hypothesis,
not a spec**, and it is *one lineage*: the two repositories carrying it are a fork pair,
so their agreement is one witness counted twice.

What makes it evidence anyway is that **the layout is self-checking and it checks out**:

* The plane walk consumes tag 8 **to the exact byte** — Kamadan's tag 8 is 193,629 bytes
  and 39 planes of ten sub-records land on 193,629 with nothing left over. A wrong
  element size desyncs inside the first plane.
* Every sub-record's length equals a count that came from a different part of the file.
* Neighbour links are **symmetric 14,950 of 14,950** on the stronger test upstream's own
  naming predicts (a link across a top edge answered across a bottom edge). Nothing in
  our decoder forces that.

And where upstream is wrong we found it: tag 11's size field is exactly twice the data
it describes, on all 39 planes.

**The generalisable move: prefer a check the artifact can REFUTE.** A chunk walk that
must close to the byte, or offsets landing where the source's own field names say they
do, beats any assertion our decoder forces true.

---

## 5. Layer 4 — the instruments, which are entirely ours

### 5.1 The hook (`toolkit/clientscan/movehook/`)

An injected DLL that plants persistent `int3` breakpoints and services them from a
vectored exception handler. Three design choices carry it:

**Entry sites only.** Every hooked function begins `55 push ebp`, so the handler
re-emulates **exactly one instruction shape** instead of an arbitrary one per site.
That is what let it stay hand-rolled with no MinHook or Detours — and `gensites.py`
refuses any row whose first byte is not `0x55`, so the property cannot rot.

**`[esp]` at an entry is still the caller's return address**, because `push ebp` has not
run yet. This is the highest-yield trick in the file: it turns "this function ran" into
"**this caller** ran". It answered which of five callers bakes a given arrival, and it
refuted the static exclusion in §3 by naming `AgTimer::Advance` from two records.

**Two controls in every capture, and they are why a zero can mean anything.**
*Control A* allocates memory, writes our own `0xCC`, and executes it — if it does not
fire, our handler is dead and nothing else in the capture means anything. *Control B*
samples a live client thread's EIP and plants a breakpoint on **real client code** — if
it does not fire, patching client code is unproven, so a zero is not evidence of
absence. A site whose patch failed is recorded as `NEVER ARMED` rather than as `hits 0`,
because those are different claims: one is about the client, the other about us.

### 5.2 The scorers

`route()`, `clip()`, `containing()`, `noclipscore.py`'s three sections — all ours. So
are the sampling decisions, and **that is where our errors live**. Two worked examples
from one week:

* A no-clip detector built on `clip()` reported **zero walked off-mesh** on a capture
  containing a deliberate, repeated no-clip. `clip()` is plane-blind; the body was
  walking through a prop's carved hole.
* Its replacement read **zero** again on a capture taken specifically to catch a bridge
  walk. `containing()` unions all 68 planes, so a body on a deck and a body on the
  ground beneath it are the same query.

Both zeros were structural properties of our instrument, published as facts about the
client. **When a metric disagrees with the operator, the metric is the suspect.**

---

## 6. The discipline that catches this, and what each part is for

**Label every claim, at the call site as well as in the doc.** The vocabulary is in
[studies/character/FINDINGS.md](../character/FINDINGS.md).

**A positive control.** A detector that only ever says "clean" is indistinguishable from
a broken one. Make the same filtered search find something you already know before
believing what it cannot find. The plane test's control is a body on the plane the mesh
*does* offer: it must **not** fire, or every run would read as a no-clip.

**Zero exposure is not a null.** A treatment arm that never met its condition has zero
trials, not a clean result. Pre-register an exposure floor and an abort; report
"unexercised" in those words. A run scored below its floor is re-run, not reported
through.

**A prediction, stated before the run, with a REFUTED-IF clause.** A probe with no
stated expectation can be rationalised into agreeing with anything afterwards.

**Two instruments, or one theorem measured twice.** Scoring the same dissociation from
the server log and then from the client's own memory is corroboration — they share no
code. Checking `walkable()` against `containing()` is *not*: the docstring says they are
bit-for-bit the same test. Before claiming agreement, find the regime where the two
would have to diverge and check the corpus reaches it.

**A run that measured nothing failed.** Every test routes its verdict through
`toolkit/checks.py` and declares a floor; fewer checks than the floor is a FAIL naming
the shortfall. This exists because two suites printed ALL CHECKS PASSED while measuring
nothing.

**Adversarial review.** Every analysis lane gets a skeptic told to refute it, working
from raw artifacts rather than the lane's scratch files. In the obstacle dig the
decisive finding of the whole pass was a *skeptic's*, made while refuting its own lane.

---

## 7. A worked example — the stuck client, by layer

The 2026-08-29 capture of a client that had stopped responding to move commands
(MOVECODE findings §1z-c), sorted by where each statement comes from:

| Statement | Layer | Label |
|---|---|---|
| All 49 of the client's path queries start from plane 41 at a point the mesh gives only plane 0 | 4 (hook) + 3 (mesh) | **OBSERVED** |
| The walker never ran — two sites, 0 hits, both controls green | 4 | **OBSERVED** |
| `m_point` carries the plane, and an install copies it unchanged | 2 | **OBSERVED** |
| The point-resolve indexes `pt.plane` into a plane array | 2 | **RECONSTRUCTION** (partially reversed) |
| *Therefore* the client could not resolve its position, so no path was driven | inference | **RECONSTRUCTION** |
| Zero-length grants caused the lock | — | **REFUTED** by its own control: the healthy run has 76/76 and does not lock |

The gap in row 5 is why the next measurement is named rather than assumed: a tap on
`MapFindPath`'s four return sites turns "asked from an impossible plane" into "got
pathCount 0". **Naming the measurement that would close an inference is cheaper than
arguing about the inference.**

---

## 8. Standing weaknesses — the ones to state out loud in any write-up

* **We assume our decode's plane indices are the client's.** Same file, so it should
  hold; "should" is doing work, and §7's finding rests on it.
* **Our `route()` is more forgiving than the client's pathfinder.** It returns a path
  from the impossible plane *and* from the correct one — so our server will happily
  grant legal routes to a client that cannot move.
* **Event-driven sampling.** The hook fires on solver events, so gaps of 8.9–19.8 s sit
  exactly over the interesting windows. No per-frame site is known; the tick was
  measured and refuted as a denominator. Score **chords and intervals**, not point
  samples, until that is solved.
* **One agent id names TWO objects.** Group trajectories on the `ecx` address, never on
  the id.
* **Mesh selection by coverage score picks the WRONG map** on at least one capture. Pin
  the mesh; never select it.
