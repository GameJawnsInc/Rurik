# MOVECODE — replicating stock movement from the client's own code

**Owner's ruling, 2026-08-26:** *"static analysis + DLL hooks... normal
library/language restrictions are off for this — it's too important to try and
reverse engineer in our limited, unintrusive fashion we've been using."*

**Identifiers.** `MOVECODE-B<n>` = build steps, `MOVECODE-Q<n>` = open questions,
`MOVECODE-P<n>` = pre-registered predictions. Convention:
[studies/idents/CONVENTION.md](../idents/CONVENTION.md).

This document is the arc's entry point. It scopes the tools, states what is
already known (a great deal — read §2 before proposing any work), and orders the
questions by what closes the movement model fastest.

---

## 1. Why this arc exists

Five owner-driven verification runs on 2026-08-26 took the server's click policy
from "phases through walls" to "routes over our own navmesh at retail's measured
cadence" — and the character still warps. The scored record is
[studies/movement/ROUTER.md](../movement/ROUTER.md) §§6–10; the closing finding
is §10 and it is the reason this arc exists:

> Any divergence between the client's own position and the server-fed copy —
> from *any* cause, including a legal route the player simply declines to walk —
> is resolved by the CLIENT snapping. Every fix so far removed one *source* of
> divergence; the resolution mechanism itself is untouched.

**Run 5 is the specimen that ends the server-side phase.** With `--router` alone
(the keyboard lead channel provably off: all grants `arm=zero-lead`, zero
`a2_leg` rows), the routing origin was *perfect* — 0 u error against the client's
own last report — and all four clicks still routed **away** from their
destinations through one identical waypoint, because our decode of map 280 reads
the player's open ground as a pocket. The warp itself: our world tick walked our
copy toward that westward waypoint, the player walked east, and the client
reported 650 u west in 217 ms (2,995 u/s) landing within ~40 u of our model.

**Two client-code questions fall out, and neither is answerable from the wire:**

- **Q-A — the arrival/reconcile rule.** What decides that the client's rendered
  body moves to where the server thinks it is, and when.
- **Q-B — mesh fidelity.** Our pathing decode's connectivity disagrees with the
  client's in at least one region (plus run 4's 138–146 u `dest-off-mesh` gaps).

---

## 2. READ THIS FIRST: most of the mechanism is already decoded

**The single most important fact for the first session: the campaign has already
disassembled the movement tick, the grant path and the desync test, and the
answer to "why does it teleport" is very probably already written down.** The
full symbol table — every address, struct offset, confidence label and citation —
was assembled 2026-08-26 and is the arc's starting point. Do not re-derive it.

### 2.1 The teleport is not a mystery — our grants arm it, always

Traced end to end in `studies/movement/FINDINGS.md` (build 38797):

| Step | Address | What happens |
|---|---|---|
| `0x0029` handler | `0x005FD890` | builds `{x, y, plane, 0}`, calls the shared setter |
| the shared setter | `0x00602A40` | writes `m_segmentPoint` (`+0x88`), `m_targetPoint` (`+0x9C`), plane (`+0x80`) — **and passes `isWaypoint=0`, which CLEARS `m_flags` bit 18 (`0x40000`)** |
| the bake | `0x005FE950` | one-time: arrival tick `+0x48` and velocity `+0xB0/+0xB4` from `maxSpeed × moveSpeed` |
| the tick's arrival test | `0x006001EB` | `now == +0x48` — **exact equality, not `>=`** |
| the branch | `0x0060029F` | `test [esi+0x20], 0x40000` — **bit CLEAR → TELEPORT**; bit SET → re-bake/glide |
| the teleport | `0x006020B0` | copies `+0x9C`'s 16 bytes into `+0x78/+0x7C/+0x80/+0x84`, zeroes velocity. No path solve, no collision check, no distance guard. |

**Every `0x0029` we send arms a hard arrival at the granted point, scheduled for
an exact tick.** While the client is gliding toward that point the teleport is
invisible — it lands where the body already is. The moment the body is somewhere
else (the player walked off under keyboard control, our route pointed the wrong
way, the grant was stale), the scheduled tick yanks it back. That is a
sufficient mechanism for run 5's 650 u jump, and it is consistent with the
timing: grant at t=8.884 toward a point ~428 u away, baked arrival ≈ t=10.37,
observed jump t=10.190.

**MOVECODE-Q1 is therefore the arc's first question and it is a static one:**
`m_flags` bit 18 has **two unreconciled readings on record** — "isWaypoint /
glide-vs-teleport selector" (read at `0x0060029F`) and "is moving" (a different
write site around `0x005FE534`–`0x005FE56C`). Nobody has swept both in one pass.
If bit 18 is genuinely a wire-reachable glide selector, *a large part of this
campaign's remaining warp budget is a one-field fix.*

### 2.2 The snap is decoded too — including its gates

`0x00605FC0` (AgTrack dispatch) → `0x006055E0` (the match test):

- **Never evaluated per frame.** Exactly 3 direct callers, all message-driven
  (the bake's tail, the teleport's tail, one arm of SetPosition). Separation can
  grow unbounded between them — measured to 3,648 u with no snap.
- **The test:** is the SYNC agent's dead-reckoned `+0x78` within **100.0 u** of
  the client's own history chain (coarse, ≥2500 ms-resampled leg-starts)?
  Match → no snap. Miss → three fallback gates, **any one failing snaps**:
  1. straight-line separation vs 300.0 f — effective cut **299.332591 u** because
     the client's LUT sqrt (`0x0046E870`) over-estimates one-sidedly;
  2. `MapFindPath` (`0x00709E90`) returning `pathCount == 0` — meaning **the
     START could not be resolved on the navmesh**, not that the goal is
     unreachable;
  3. a step-clearance predicate (`0x005FEF70`) returning 0.
- **On a snap the correction is a whole-roster reseed** (`0x006022B0` for every
  agent in world 1), not a single-agent nudge.

That gate-2 detail is directly load-bearing for Q-B: **the client has its own
navmesh query, and we can call the same map data.** Comparing our
`pathmap.route()` against the client's own `MapFindPath` on identical inputs
turns "our mesh disagrees" from an inference into a measurement.

### 2.3 The build pin — every address above is build **38797**

`vault/client/2026-07-29_221c13772c7a/Gw.exe`. `session.py --exe` defaults to the
*newest* build (38833) — the `sorted()[-1]` trap this repo has hit three times.
**Always name the 38797 directory explicitly.** Treat every constant as
`(address, 38797)`; behavioural claims may survive a build bump, addresses will
not.

---

## 3. The questions, ranked by what they close

| # | Question | Closes | Answerable by |
|---|---|---|---|
| **Q1** | Is `m_flags` bit 18 one bit doing double duty ("isWaypoint" *and* "is moving"), or two readings of the same mask that were never reconciled? Is there **any** wire path that sets it? | The teleport-on-every-grant mechanism — potentially the whole warp class | **Static**, first |
| **Q2** | Does our `pathmap` decode agree with the client's own navmesh resolution? Specifically: is run 5's "pocket" a decode bug, a missing layer, or real geometry the client also refuses? | Q-B (mesh fidelity), ROUTER-Q1/Q11's `dest-off-mesh` gaps, the tour-shaped routes | **Hook** on `0x00709E90` + differential vs `pathmap.route()` |
| **Q3** | What does `agent+0x98` do? (`0x002A`'s one extra wire field writes it; two internal re-issuers preserve it across a re-grant; **no reader was ever traced**.) | Whether `0x002A` is a better grant primitive than `0x0029` — "the one untried lead" | **Static**, then hook to confirm |
| **Q4** | Is the "exactly 3 callers of `0x00605FC0`" claim complete for *indirect* calls? Every xref count in the record came from `codescan --xrefs`, **direct branches only**. | Whether the snap really is message-only (a load-bearing assumption of the whole model) | **Hook** on entry, long session |
| **Q5** | Does `0x0027` (UPDATE_SPEED_BASE) re-aim a stale in-flight destination as the record claims — the only lever that re-issues a grant without naming a new point? | A possible cancel/re-aim primitive we have never used | Static + a labelled probe |
| **Q6** | What is the client's own arrival test *for the player's own input-driven walk* (not a granted leg)? | How a stock server's grants interleave with local input without fighting | Hook on `0x005355C0`/`0x00535380` |
| **Q7** | `facing == 9` — legal under the mask, no jump-table entry, and one half of a no-snap early-out. Genuine state or sentinel? | A no-snap condition we may be able to hold deliberately | Hook logging writes to `agent+0xC4` with call stacks |

Q1 and Q2 are the arc's critical path. Q3–Q7 are real but secondary.

---

## 4. The build plan

Each step names what it answers and how it can fail. **No step ships without the
falsifiable control described in §5.2.**

### MOVECODE-B1 — the bit-18 reconciliation (static, no client run)

Sweep every write and every read of `[agent+0x20]` bit `0x40000` in one pass with
`codescan.py`; produce a table of sites with their functions and the condition
each is under. Decide: one bit, two roles, or two masks confused. Then answer
the wire question — is there any received-message path that *sets* it?

**Deliverable:** a table in `studies/movecode/FINDINGS.md` + a pre-registered
prediction for B3. **Cost: S. Do this first — it may reprice everything below.**

### MOVECODE-B2 — `movehook`, the persistent movement tap (native)

Extends the **proven** `trnblock.c` pattern (§5.1). One injected 32-bit DLL, a
persistent `int3` at a chosen site that re-emulates the overwritten instruction
and stays armed, capturing every occurrence into a ring buffer written to
`vault/research/movecode/`.

Initial sites, in priority order:
1. `0x0060029F` — the glide-vs-teleport branch. Log: agent id, `+0x20`, `+0x48`,
   `+0x78/+0x7C` (where the body *is*), `+0x9C..` (where it is being sent), the
   branch taken. **This single site produces a ledger of every teleport the
   client performs and why.**
2. `0x00605FC0` — AgTrack dispatch entry. Log the caller's return address
   (closes Q4: static 3 callers vs dynamic call origins) and the test's verdict.
3. `0x006055E0` — the match test's operands and which gate failed. This turns
   "the client snapped" into "the client snapped because gate 2 returned
   pathCount==0 at plane 44".

**Cost: M** (the pattern exists; the work is site selection and the capture
record's schema). **This is the arc's main instrument.**

### MOVECODE-B3 — the navmesh differential (hook + offline)

Hook `0x00709E90` (`MapFindPath`) at entry and exit: capture `(from, to, range,
maxCount)` and `(pathCount, P[])`. Replay every captured query through our own
`pathmap.route()`/`walkable()` and score agreement.

**This is the Q7-of-this-arc**: a per-query, bit-checkable comparison between the
client's navmesh answer and ours, on the owner's own map data. Run 5's pocket
either reproduces (our decode is wrong, and the differential names where) or does
not (the client agrees, and the route was legal but ugly — a route-quality
problem, ROUTER-Q10).

**Cost: M.** Gated on B2's harness.

### MOVECODE-B4 — the stock-behaviour corpus

With B2 armed, capture a labelled session: scripted key-holds and camera drags
(agent-pilotable per §5.4), the owner driving anything world-anchored. Produce
the reference the whole arc is for — **what the client does with each grant
shape**, as a table of (grant, client state, outcome: glide / teleport / snap).

**Cost: M.** This is the "extremely faithful-to-stock" evidence base.

### MOVECODE-B5 — the rectifier

Only after B1–B4: rewrite the server's movement authority against the measured
model rather than against inference. Scope deliberately unwritten — B1–B4 decide
what it is. Candidates the record already suggests: never leaving a scheduled
hard arrival armed at a point the player is not walking to; using `0x0027`'s
re-aim (Q5) instead of a fresh grant; keeping separation inside the 100 u history
band rather than the 299 u gate.

---

## 5. What already exists — reuse, do not rebuild

### 5.1 `toolkit/clientscan/trnhook/` — the proven hook, and its lessons

- **`trnblock.c` is the pattern for B2**: patches a `call rel32` with `0xCC`,
  and on every hit **re-emulates the overwritten call** (push return address, set
  EIP to callee) before continuing — so the breakpoint stays armed and captures
  *every* occurrence. Ring buffer, `NCAP=1024`. Reports hit-vs-stored counts and
  every distinct id seen, so "the hook never fired" is distinguishable from "the
  target never appeared."
- **`build.ps1`**: MSVC, **x86 — `Gw.exe` is 32-bit**; verifies the output PE's
  machine field is `0x014C`. Links kernel32 only — **no third-party library, so
  no new §6.1 row is owed for the DLL itself.**
- **`inject.py`**: remote `LoadLibraryA` via `CreateRemoteThread`, resolving the
  export by walking the *target's* PE export table (this process is 64-bit, the
  target is WOW64 — their kernel32 images differ). Pure ctypes.
- **`autoinject.py`, and the trap it exists for**: terrain builds **once at map
  load** — a hook armed seconds late sees `hits 0`. Measured window: **~7
  seconds**. It polls `tasklist` at **25 ms** and injects the instant the pid
  appears; **start it before launching the client.** If movement state initialises
  once per map load, this applies identically.
- **Hardware breakpoints armed in-process (32-bit) were DEAD in this client** —
  proven by a control that armed an address the process was provably executing
  and saw nothing; two commits of conclusions were retracted. **But**
  `gatetrace.py` later used Dr0–Dr3 successfully from the **native (64-bit)
  debug context**. These may not be in tension. **Do not assume either
  generalises — test against this arc's own targets (MOVECODE-Q8).**

### 5.2 The control discipline that makes a hook trustworthy

`trnint3.c` runs two falsifiable controls *before* its measurement is believed,
and records which passed:

- **Control A (free):** the DLL executes an `int3` in a buffer it allocated
  itself — proves the VEH is alive without touching a client byte.
- **Control B:** patches a byte the client's *own EIP was sampled executing* —
  proves patch-and-delivery on real client code.

**Copy this.** A movement hook that reports "0 teleports" is worthless unless
Control B says the machinery would have caught one.

### 5.3 Everything else

| Tool | Use |
|---|---|
| `clientscan/msghandler.py` | opcode → handler by table lookup; how nearly every address in §2 was found |
| `clientscan/codescan.py` | disassembly + `--xrefs` (**direct branches only** — the limit behind Q4) |
| `clientscan/commandertrap.py` | the Windows-debugger reference: `DebugActiveProcess` + DR registers, **writes nothing into the client**. The cheapest tier — prefer it where it suffices |
| `clientscan/gatetrace.py` | already attaches to the loopback client and reads the walk-start applier's gate operands at a key press |
| `clientscan/movetap.py` | the ctypes poller: resolves AGBASE, both world arrays, both clocks. Polling, 9.4–12.9 Hz — **the limitation B2 beats**. Traps: `point` is sample-and-hold; score on `live` |
| `harness/keytap.py` | cross-process `ReadProcessMemory` with ASLR-correct module bases, pure ctypes |
| `mapdata/pathmap.py` | `route()`, `walkable()`, `clip()`, `nearest_walkable()` — B3's other half |
| `clientpatch/dhbuild.py` | **mandatory** before any launch: which build may point where |

### 5.4 The rules that still bind (only the dependency rule was lifted)

- **Provenance gate.** Addresses, offsets, strides, layouts are **permitted in
  bulk** — on three conditions: *the extractor is in this repo and the row names
  it, the row records the build, provenance is per row.* Still refused:
  decompiled function **bodies** and **bulk dumps of assert strings**. A single
  assert cited as evidence for one claim is a measurement — keep it, with file
  and line. **The direction of error in this repo is over-refusal.**
- **Second gate (a licence question, untouched by the dependency relaxation).**
  A `PLAN.md` §6.1 row is owed **before a line links against it** for: any
  detour/hook library (MinHook BSD-2, Detours MIT), any hooking *technique*
  copied from a published writeup, and any GWCA-class notes consulted. GWCA is
  MIT (attribution required); **Py4GW_Reforged and gw-preservation grant
  nothing** — they may only *verify* a value we derived ourselves. Three GWCA
  mirrors exist in the vault and **they disagree** — cite the maintained
  `gwdevhub__GWToolboxpp/Dependencies/GWCA` path; an archived one is off by one
  opcode past a point. Run `python toolkit/derivlint.py` once any module names an
  upstream.
- **Capstone/pefile carve-out names exactly two files** (`msghandler.py`,
  `codescan.py`). A new disassembling module needs the carve-out extended
  explicitly — put it to the owner rather than assuming.
- **Tests.** `checks.Ledger` with a floor set from a **bare-machine** run
  (`skip()` lowers the floor by *zero* — a session lost a day to believing
  otherwise). `TESTS.md` entry in the same commit or `test_srclint.py` §7 goes
  red. Precedent to copy: `test_commandertrap.py` exercises its debugger plumbing
  against a throwaway **32-bit `cmd.exe` under WOW64**, reserving skips for the
  sections that genuinely need the vaulted client.
- **Launch binding.** Hook development uses the `ours`-DH loopback build under
  `vault/run/` — never `run-live/`, never pointed at ArenaNet. Never select a
  build by filename. Never patch or launch anything under `C:\gw` (read-only).
- **Vault stays local.** Hook logs, dumps and traces go under `vault/` via
  `vaultpath.py`.
- **The owner drives world-anchored input.** Agents may script key-holds,
  calibrated camera drags, fixed-position UI clicks and memory polls. Agents may
  **not** click on world geometry or render verdicts on model appearance. Announce
  every launch, and bound it: `--keep-open` alone parks the window forever —
  always pair with `--hold SECONDS`.

---

## 6. Open process questions for the owner

1. **Where do the offset/address tables live?** `content/*.toml` rows with
   `source = "client-table"` inherit `content.py`'s enforcement automatically; a
   plain Python module inherits nothing and needs the discipline copied by hand.
2. **Does a hook DLL need a `test_*.py`?** `trnhook/` has none and `srclint`
   therefore imposes nothing on it — **silence, not a ruling.** Recommend: yes,
   wrapping build+inject+read with skips for no-compiler / no-client /
   not-elevated, per `test_commandertrap.py`.
3. **Extend the capstone/pefile carve-out** to any new disassembling module, or
   keep new modules byte-pattern-only?
4. **MinHook/Detours, or hand-rolled?** The `trnblock.c` precedent is hand-rolled
   and owes no row. A library is more robust and owes a row + notices entry
   *before* first use.

---

## 7. The first session's opening moves

1. `git rev-parse --show-toplevel` — confirm the tree. Read
   `studies/movement/ROUTER.md` §10 (why this arc exists) and §2 above (what is
   already known). **Do not re-derive the symbol table.**
2. **MOVECODE-B1, the bit-18 sweep.** Static, cheap, no client. It may reprice
   the entire arc — if bit 18 is a wire-reachable glide selector, say so loudly
   before building any hook.
3. Register the word: this document's legend line is the registration; check
   `MOVECODE-` is still free before the first commit.
4. Put §6's four process questions to the owner **before** the first native
   commit, not after.
5. Then B2, with Controls A and B green before a single measurement is quoted.

**The standard that got the router arc its four honest results: pre-register the
prediction, name what would refute it, and score the run against the rows rather
than the impression.** The last five runs each produced a real finding because
the prediction was written down first. Keep that.
