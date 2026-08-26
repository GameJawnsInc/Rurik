# RETHINK — the drawing board, 2026-08-26 evening

**Owner's stop order, verbatim in intent:** no more policy fixes; design better
instruments (the owner's chosen priority), rethink whether the plan is wrapping
something simpler, review the mistakes. This document is those three
deliverables. **The standing rule until the owner lifts it: NO policy code.**
The instrument builds below are ranked for the owner's pick; nothing here has
been built.

Evidence base: three recon lanes + a scripted skeptic over the whole campaign
record and the live corpus (lane files `rethink-R1-retro.md`,
`rethink-R2-regime.md`, `rethink-R3-instruments.md`, `rethink-skeptic.md` +
scripts, session scratchpad `4beba4a1-…`), plus the P-17 verification run's own
decode (REALFIX.md §0.18). Every load-bearing number below survived skeptic
re-derivation or is quoted WITH the skeptic's correction. Labels per
studies/character/FINDINGS.md.

---

## 1. What the P-17 run actually showed (the scoring is in REALFIX §0.18)

The §0.17 fixes were LIVE and half of them visibly worked — and the run still
failed, because the failures come from a layer below any of them:

- The D2 clip held six leads AT the plaza wall (dests pinned on the wall line —
  the mechanism validated), then the client's reported position penetrated the
  mesh edge by **~0.25 u**, `walkable(origin)` flipped false at the exact
  float, and the clip's **off-mesh-origin escape door** (copied from
  `clip_to_walkable`) disabled clipping at precisely the moment it existed
  for. Two unclipped 766 u leads fired through the wall. (OBSERVED, exact
  floats: reports t=289.41/289.92, `(-4584.32, 5705.25)` / `(-4536.61,
  5705.03)` walkable=False, every neighbor a quarter-unit south true.)
- The client sent **~zero position reports for ~490 s** of click play (all 12
  of the first 496 s's reports sit inside the 5 s wall press). Rule 1's
  keyboard latch never armed — the owner's spam clicks under a held key ALL
  fired (56 immediate answers, 0 `locally-moving` drops in that span). The
  answer-outstanding hold never engaged. The eager void never ran. **Every
  report-triggered guard was inert for the whole session, because the failure
  mode suppresses the signal the guards key on.**
- Cross-floor and other-level clicks were echoed verbatim (retail's own
  measured contract) and the client **order-walked straight lines through the
  ground**. Zero XY jumps exist on the live track in any of the three tapes —
  every felt phase/warp was either a smooth XY walk through blocking geometry
  or a **vertical cut no instrument we run can see**.

---

## 2. The something-simpler: ONE mechanism, measured

> **A fired `0x0029` starts an autonomous straight-line order-walk that ends
> only at the next processed key edge.**

Everything else this campaign has fought is a face of that sentence plus a
server-side trigger that hands it a bad destination. The components, each now
measured:

- **During the order-walk:** the client walks the granted segment at the
  granted speed, collision that blocks its own free input is bypassed
  (P-17(a): the same wall that held free-input penetration to 0.25 u was
  crossed 766 u under an order — n=1; whether that wall is prop- or
  terrain-class is UNRESOLVED, see RETHINK-QA), Z and plane are unconsidered, and
  the teleport branch is armed — **bit 18 clear in 3,510 of 3,511 samples
  across four tapes** (R2b). Key state is ignored; no reports are sent.
- **Keyboard-lead grants are benign because the held key keeps supplying
  edges.** Retail: median next-report after an answered heading grant
  **0.463 s** ≈ the unconditioned baseline 0.500 s (n=649). Ours: 0.352 s
  (n=63). Each fresh report ends the previous order and draws the next — the
  regime is entered and exited ~3×/s and is invisible.
- **Click-shaped grants have no ending edge.** Retail's own client is
  report-silent during click-walks — direction CONFIRMED with **zero
  counterexamples** corpus-wide; the skeptic trimmed the evidence base to
  n≈6 clean walk-exposed silent specimens (7 of R2's 17 "silent" windows were
  ≤1.5 s micro-walks, 9 windows non-independent), so state it at that
  strength. Resumption is always a key edge. **Retail's server operates
  report-blind during click-walks by design.**
- **Our pathological cell is `click-d1` under a HELD KEY** — a grant shape
  retail essentially never exercises (1 of 23 live clicks lands with a key
  genuinely held through it). The held key that let the click fire is not a
  new edge, so nothing ends the order: our click-d1 median
  silence-after-fire is **166 s** against zero-lead's 0.352 s — the same
  bimodal split as retail's, stretched two orders of magnitude by our own
  arming condition. (R2d item 3, edge-vs-shape: RESOLVED for edges on n=1+
  corpus — a released-key zero-lead grant went silent 5.28 s exactly like a
  short click; the shape doesn't matter, the missing edge does.)
- **The `mode` field is a locomotion-speed enum, not a regime flag**
  (R2b, OBSERVED): 1 = 288 u/s run (spans order-following AND free input AND
  parked), 4 = 190.1 u/s backpedal (matching the a2 floor constant 190.08 to
  0.01%), 8 = 216 u/s (strafe, RECONSTRUCTION), 3 = a second 288 class
  (UNVERIFIED which), 9 = the early-out/idle sentinel. Modes 4/8 are a
  one-way free-input signal (83/83 samples); mode 1 says nothing.

**The skeptic's corrected reduction tally** (its criterion: a specimen REDUCES
only if no independent server-side trigger supplies the occasion): ~3 REDUCES,
~6 PARTIALLY, with the honest pattern being **the regime supplies the DAMAGE;
a server-side defect supplies the OCCASION** — F-A's stale flush ticks, R-3's
unguarded site, the clip's escape door, the frozen freshness clock. Fixing
occasions one at a time is what the last four days were; the occasions are
unbounded because every grant is a potential occasion while the order-walk is
what it is.

**What this means for the plan (hypotheses to make measurable, NOT builds):**

- **RETHINK-H1:** the held-key click-answer cell (`click-d1`) should not
  exist — retail has no such cell, and it is the 166 s order factory. Its
  deletion is a policy change and waits on the owner.
- **RETHINK-H2:** retail's long-click answers are **part-way routed**
  (OBSERVED n=4 + the skeptic's fifth: an answer 2,068 u short followed by
  the verbatim echo 4.56 s later). Retail may never grant a segment the
  client couldn't legally walk — the "route waypoints" shape. Whether long
  answers arrive as SEQUENCES of short grants is measurable from the live
  corpus (RETHINK-QB) and would explain how retail lives with a teleport-armed,
  collision-bypassing order-walk: it never orders one across geometry.
- **RETHINK-H3:** with 1+2 in place, the remaining tower (holds, voids,
  freshness, watchdog) may shrink to: echo real clicks retail's way, lead
  keyboard reports retail's way (clipped), and model the silence instead of
  guarding against it. Not evaluable until the instruments below exist.

---

## 3. The mistakes review

R1's full fix ledger (24 rows, `--stop-echo` through §0.17) and failure
classification are in `rethink-R1-retro.md`, with the skeptic's corrections
(`rethink-skeptic.md` attack 3) absorbed here; the ledger is
CONFIRMED-INCOMPLETE without these, so they are named: **the whole REALFIX
L-series was missing** — L1 (first live A/B, VOID: 32% blind windows, one arm
starved to zero grants by protocol design), **L5/L6 (2026-08-21: the shipped
default warps at ~15.7/min; `--zero-lead` NOT significant in the click regime,
RR 0.703 CI spanning 1.0; `--plane-carry` "carries no information at all";
"this regime needs a CLICK-ARM lever")** — measured the day BEFORE F1 shipped
as default; L8 (third consecutive zero-exposure abort); L9 (the protected
cell, Fisher 0.0023); I2 (retired unbuilt). L5/L6 is the sharpest single
lesson in the ledger: the campaign had measured that the click regime was the
live problem five days before the click arc began, and spent the interval on
the keyboard side.

**The failure classes that recur (skeptic-corrected membership):**

1. **Symptom-population fixes scored against the previous tape.** F-B → F-A →
   §0.15 → the §0.16 candidate → §0.17's pair: each aimed at the prior run's
   named population, each verified against the prior tape, each met a
   different cell of the same mechanism in the next run. Five iterations in
   two days.
2. **Guards keyed on a signal the failure suppresses.** Rule 1, the
   outstanding hold, the void, click freshness — all read reports; the order
   regime silences reports. This run: every guard inert for 490 s. (The
   watchdog's None-latch bug does NOT belong here — that was a plain coding
   defect caught by review.)
3. **Instrument columns with assumed semantics.** The point-column snap
   censuses (two full passes built on sample-and-hold `point`), the Q7
   wrong-mesh first pass, the op-62/64 swap in a lane brief, movesync's
   pre-repair bars. New instance risk identified by the skeptic in TWO
   proposed instruments (§4) before they were built — the class is live.
4. **A missing model variable scored as a shape success.** `--client-endpoint`
   met both its registered terms and warped worse — speed truth was absent
   from the model. §0.17's clip met its mechanism and lost to a door term.
5. **Negative claims without a search.** "No scoring tool exists" (the tool
   existed, pre-registered); §4's "no skill-bar field anywhere" precedent.
   MEMORY.md already carries the rule; it still fired this week.
6. **Zero-exposure cells read as nulls** — R6, C2-geography, L8. The
   registered exposure floors caught each; the class persists because designs
   keep putting the exposure behind operator choreography.
7. **Over-fit magnitude/rate readings** (F35's 586-vs-8 over-read; F27's
   "every walk-start").
8. **Un-committed ground truth.** The S2 live-decode scripts — the ONLY
   instrument that has ever measured retail's contract, cited seven times
   across §0.13–0.17 — live in a deletable scratchpad, hardcoded to a dead
   worktree path. The campaign's referee is not in the repo.

**What worked, and is retained as the method** (R1c, all with named saves):
pre-registration with REFUTED-IF clauses (caught F-B and F-A within one run
each); skeptic replay from raw rows (four reversals in one day, all correct);
**the offline counterfactual replay** (killed the §0.16 literal candidate
before it shipped — the only fix-refutation this week that cost zero owner
minutes); exposure floors; mesh model-selection before scoring; adversarial
review with mutation testing (a session-killing TypeError caught pre-run);
positive controls on instruments.

**The standing claims the rethink must NOT casually discard** (R1d): the D1
formula (bit-exact, 3,532 pairs); the stop-ack shape (131/131); the
grant-arms-scheduled-arrival mechanism (byte-read, corrected in detail three
times, core never refuted); the 100 u plane-connected history veto as the
real snap gate (22/22 + 15/15 replay); and — weakest — D2 = our navmesh at
terrain edges only (248/701 ≤3 u), with prop-class geometry an acknowledged
unmodelled remainder.

---

## 4. The instrument program (the owner's pick list)

Ranked by (closes the regime question) × cost, with the skeptic's re-ranking
and two point-column-pattern hazards it caught marked. Full audit:
`rethink-R3-instruments.md`. Structural fact first: **the agent struct has no
Z field** — 2D+plane, OBSERVED in the pinned binary and independently
CORROBORATED by OpenTyria's source. No instrument can read a client Z at any
cost; the Z gap is closable only as a geometry-residual check against OUR
terrain mesh.

| # | Build | Cost | What it closes | Caveat |
|---|---|---|---|---|
| 1 | **Five gamesrv `rec.event` additions**: the flush-hold's refusal row (today a bare `return False` — its engagement is invisible regardless of truth), `kbd_latch_age` on position_report rows, `a2_leg` arm/clear events, `a2_watchdog_due` refusal transitions, and **`clip_why`** on the lead row (`no-mesh` / `origin-unwalkable` / `fallback` / `clipped`) | S each | Guard inertness becomes visible IN the log instead of by absence; `clip_why=origin-unwalkable` would have named P-17(a) directly. Same pattern this file has already shipped three times | none — append-only rows |
| 2 | **Commit the S2 live-decode recipe** as a tested module (`toolkit/authsrv/livewire.py`): the `tape._segments` + `codec` + `origin` loader the retail ground truth depends on | M | Mistake class 8; prerequisite for #6 | validate by reproducing the original S2 numbers on the original tapes |
| 3 | **Promote the offline policy bench** (`skeptic_sim.py` → `toolkit/clientscan/policyreplay.py`): replay any gamesrv log's event stream through a candidate policy, replay-fidelity check first (the shipped policy must reproduce the log's own fires 1:1), survive/suppress/new output, never a ranking | M | Every future policy hypothesis gets the check that killed the §0.16 candidate pre-ship, as standing equipment | fidelity gate before any counterfactual is quoted |
| 4 | **`--live-track-report-gaps`** scoring pass on movetap tapes: per silence >1 s, did `dir` change without a wire report | S | Distinguishes F25's steady-direction silence from order-regime suppression, per episode | **skeptic-flagged**: `dir`'s writer-side semantics are validated only in press contexts — validate against a labeled click-walk episode FIRST or this ships the next point-column trap |
| 5 | **`reqtoken`-stall validation** as the order-following readout (already sampled every row; the §0.11 fence-lock fingerprint generalized) | M | A per-sample IS-ORDER-FOLLOWING flag with zero new plumbing, IF it generalizes | needs 2–3 labeled click-walk episodes outside the input-lock arc |
| 6 | **`height_at()` over our terrain mesh** + a movetap post-hoc join: geometry residuals for reported/segment points | M | The Z/floor blindness — names "through the ground" as a residual instead of a screenshot | **skeptic-flagged**: must be a multi-valued query with an ambiguity flag — a single-valued 2D→Z join is silently wrong exactly at stacked floors, the target case |
| 7 | **Wire-conformance scorer**: every measured retail clause (verbatim echo, one burst per click, drop-under-keyboard, stop grammar, lead in-band-or-clipped, part-way routing) as `check_<clause>()` over any tape, per-clause output, ours/live never pooled | L | Turns each hand-measured contract clause into a standing regression against every future tape | gated on #2 |
| 8 | **Breakpoint tap on 0x005355C0 / 0x00535380** (`commandertrap.py`-class): count MOVE-CMD dispatches with vs. without a c2s send | L | Frame-resolution ground truth on report emission — the only direct observation of a wire-invisible re-dispatch | movetap's own doctrine: build only if 4/5 fail; the mode-enum decode (0x00602660) is superseded — R2b already showed `mode` cannot flag the regime |

**The five-minute item, before anything:** rerun R2b's occupancy join with the
tightened 2 s window (R2d refuter #5) — it hardens the regime numbers this
whole document leans on, from data already on disk.

**Desk checks needing no build and no owner time:** **RETHINK-QA** — is the P-17
plaza wall prop-class or terrain-class in the map data? (Decides whether
§0.15's "prop collision bypassed WHILE TERRAIN HOLDS" clause survives the n=1
crossing of a barrier that had just blocked free input.) **RETHINK-QB** — do
retail's long-click answers arrive as sequences of short grants? (The
part-way/waypoint contract, n=5 so far; decides RETHINK-H2.) Both run from
the existing corpus.

---

## 5. Standing state

- `--d1-lead` remains OPT-IN with §0.17's clip + hold in place; the shipped
  default is byte-identical to pre-campaign. Nothing further ships until the
  owner rules on this document.
- The P-17 scoring of record is REALFIX.md §0.18. The a2-campaign-handoff
  file is historical; **this document is the campaign's entry point** until
  superseded.
- The next owner run, whenever it happens, is an INSTRUMENT run: same play,
  new readouts, zero policy deltas.
