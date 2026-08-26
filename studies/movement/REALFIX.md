# REALFIX — the real warp fix: candidates, harness, one live A/B

Written 2026-08-20 from the round-5 research workflow (five research lanes, three
adversarial skeptic lanes, no client run). The research record with every number's
derivation is [FINDINGS.md](FINDINGS.md) §"2026-08-20, round 5"; this file is the
buildable spec that round produced.

**Identifiers.** `REALFIX-P<n>` = candidate grant policies. `REALFIX-O<n>` = the
invariant's obligations. `REALFIX-C<n>` = the offline harness's calibration gates.
`REALFIX-M<n>` = exposure metrics. `REALFIX-D<n>` = pre-registered predictions,
numbered by candidate. `REALFIX-H<n>` = harness builds. `REALFIX-L<n>` = live runs.
`REALFIX-U<n>` = substrate and instrument gaps. `REALFIX-Q<n>` = open questions.
`REALFIX-E` = the admissible event definition. `REALFIX-X<n>` = L2 protocol cells.
`REALFIX-W<n>` = L2's measured walk facts. `REALFIX-T<n>` = timing/tooling deltas.
`REALFIX-I<n>` = instrument changes. `REALFIX-F<n>` = fix candidates.
`REALFIX-A<n>` = accuracy-campaign rungs (minted 2026-08-25, §0 below).
Minted 2026-08-22/23: **`REALFIX-I2`** = a click-arm exemption from rule 2,
priced and DEFERRED (L9's pre-registration ruling 1; mandatory only if a run
aborts on exposure a fourth time). **`REALFIX-I3`** = sending `GAME_SMSG 0x0023`,
ArenaNet's own movement-state checksum. ✅ **BUILT AND RUN 2026-08-23**:
positive control 26 of 26 at a client, model arm 25 of 26 — the channel
works and our five-field model is NOT bit-exact, with one match showing the
oracle can say yes. `--checksum-probe {wrong,model}`,
`test_poschecksum.py` floor 20. FINDINGS §"REALFIX-I3 IS BUILT AND THE CLIENT
SPOKE".
Convention: [studies/idents/CONVENTION.md](../idents/CONVENTION.md).

## REALFIX — the buildable spec

**Status, and this banner used to read "NOTHING HERE HAS BEEN BUILT OR RUN" after two things here had been built.** As of 2026-08-21: **REALFIX-C0 and REALFIX-H1 are BUILT** (§4 items 1-2), and **REALFIX-P2 `--zero-lead` is BUILT and unrun** — the flag, its `_heading_grant_ok` predicate and its composition refusals are in `authsrv.py`, locked by `test_position_trust.py` §14, with its prediction printed at startup. **NOTHING HERE HAS BEEN RUN AT A CLIENT.** Every number cited is from the round-5 research draft above and traces to a lane or a FINDINGS line, except where a later dated line re-measures it. Origins are marked; `ours` and `live` are never pooled.

**Read this first, or you will rebuild a refuted thing:** `--stop-echo`, `--heading-grant` and `--client-endpoint` are all built, run and REFUTED (`authsrv.py:1004-1023`, `:1049-1075`, `:1090-1099` — *line refs drifted by 2026-08-25 edits; the blocks now sit near `:1071`/`:1154`/`:1201`*). A stop-arm `0x0029` **is** `--stop-echo`. A heading grant at the client's own unclipped endpoint **is** `--client-endpoint`. Neither is a fresh idea. *But read §0's era analysis before treating any of the three as a verdict on a retail-shaped policy: all three kills date to 2026-08-19, the full-lead-click era, and the 2026-08-25 recon found only three refutations in the whole graveyard that transfer policy-independently (`0x0027` re-arm, the direction/backward guard, "+0.500 u as the fix").*

---

## 0. THE ACCURACY CAMPAIGN (opened 2026-08-25, owner's re-scope: "we need to get it very accurate")

**The re-scope.** The owner ended the checkpoint-shipping mode the evening the
`--resync` disarm run was scored: no default flips, no incremental ship rulings —
movement gets fixed to retail accuracy, and this campaign is the ladder. Grounded by a
four-lane recon (refutation graveyard / retail contract / defect ledger / client
constraints) over this tree at `92a3c93`; every claim below carries its lane's label.

### 0.1 The diagnosis — one debt, four expressions, and scaffolding all the way down

The open movement defects are ONE structural debt: **our grant policy diverges from
retail's in shape, cadence and speed-truth**, and the client — whose every granted
destination arms a scheduled hard arrival (bit 18 cleared on all our grants; the
arrival is a teleport onto `m_targetPoint` at exact tick equality) — expresses that
divergence as the staleness family. The ledger (OBSERVED magnitudes):
**F27** walk-start snap (magnitude = staleness, 18 of 96 owner stops past 190 u, max
748 u); **F33** reconcile-on-answer (346–864 u, gate 1 at 299.33 u); **F35** arrival
drags (8 of 586 fires, 26–3,437 u, ~1 per 2.6 min owner-era, wire-silent); the
**click-leg death** (the client's own click-armed `+0x48` times out because we send
nothing mid-leg, 864 u measured). Everything shipped so far — `--zero-lead`,
`--grant-suppress`, `--cast-stop=pin`'s dead-reckoner, opt-in `--resync` — **bounds**
the divergence; none removes it, and the pin×resync one-`0x002C`-policy conflict plus
the instant-skill divergence (retail does NOT stop a runner for 30 of 30 live shout
presses; our shipped pin does) are costs of the scaffolding itself.

**Retail's contract, measured** (the target; OBSERVED at wire level unless noted):
grants carry the client's own proposed endpoint `reported + vec2 + 0.500·unit(vec2)`
(|vec2| 765–768 u hard-ceilinged), ~31% world-truncated short ALONG the ray to a
median 348 u by a boundary whose navmesh identity is RECONSTRUCTION (Q7); burst
grammar `0x0025 → 0x002B → 0x0029`, `0x0029` always last (3,023 of 3,071); essentially
every `0x003D` answered at one RTT, inter-grant p50 0.490 s, 88.5% of arms superseded
before maturity; stops re-pinned by a zero-distance `0x0029` echo (134 of 172); cast
starts halted by a bare `0x0028` after the `0x00E4` (4 of 4); `0x002C` to the player
essentially never (5 in the whole live corpus); copies' separation p50 83 u with zero
snaps (model-derived). **Why retail survives its own +766 u leads while both our lead
arms warped: speed truth** — `--client-endpoint` met the payload and cadence terms and
warped MORE (14.6 jumps/min), and its record blames the one term it lacked: the player
moved at a median 111.7 u/s while every grant asserted 288. Retail is "safe at all of
its leads only because its v_player ≈ S" (RECONSTRUCTION), and retail ships the two
levers we never have: the `0x002B` family float (backpedal 0.66 witnessed on the wire)
and the D2 clip mixture.

### 0.2 The load-bearing unknowns, in dependency order

1. **REALFIX-Q6 / SPEED TRUTH (the term that killed every lead arm): does a wire
   `0x002B` float steer the SYNC copy's reckoning speed (`+0x5C`/`+0x60`)?** We send
   moveSpeed 1.0 in 621 of 621; the drawn body backpedals at ~189.8 u/s anyway
   (client-side family logic), so during any non-forward or snared movement the copy
   out-reckons the body — the `--client-endpoint` failure mechanism. The decider has
   been named three times and never run: **movetap on `+0x5C`/`+0x60` during sustained
   backpedalling while the server sends `0x002B` floats.** Movetap already reads both
   fields. If the wire CAN set the copy's speed, speed truth is one sender away; if it
   cannot, speed truth must come through lead scaling (retail's harm law
   `L·(S−v)/S`, and its clip mixture may BE that scaling).
2. **The sign-of-lead protection (UNVERIFIED, the campaign's central hypothesis):**
   does a forward-pointing lead make arrival maturation a no-op (the arrival lands
   where the reckoning already is — assert 0x486's own invariant), converting HOLE A's
   wire-silent windows from hazard to irrelevance? Retail's 11.5% matured arms with
   zero snaps say yes by model; nothing of ours has measured it.
3. **REALFIX-Q7 / the D2 clip boundary**: is retail's truncation our walkable navmesh?
   Cheapest: one loopback capture scored against our own `clip_to_walkable`.
4. **Collision-blindness**: the bake is collision-blind (OBSERVED), so must a lead be
   clipped to walkable, or does the arrival teleport make wall-adjacent leads harmful?
   Unmeasured either way.

### 0.3 The rungs

- **REALFIX-A1 — the speed-truth probe. WIRED 2026-08-25 (`--family-rate-probe`),
  the owner run is next.** The pre-build recon SHARPENED the question: the client's
  `0x002B` handler is already statically decoded (`0x005FD9D0` → setter `0x00602990`,
  FINDINGS Q1/Q2) as a **pure store to sync `+0x60` (moveSpeed) and `+0xC4`** — it
  never writes `+0x5C`, arms nothing, and the speed is consumed only at the **next
  grant's bake** as `[+0x60] × [+0x5C]`. So the probe is the dynamic CONFIRMATION
  (verbatim-first) plus the measurement statics can't make. **Prediction, registered
  before the run, ANCHORED TO THE TAPE'S SENT ROWS (the review's correction — never
  to the key the operator holds): (a) movetap `movespeed` reads each probe send's
  float within 1–2 samples of that send and holds UNTIL THE NEXT SEND OF A DIFFERENT
  FAMILY — the store persists, and 64.5% of family-edge reports arrive inside the
  0.5 s grant floor (measured over 18 captures), so the previous family's float
  carried ~0.5–0.7 s into a new leg is the mechanism working, not a refutation;
  (b) `maxspeed` holds 288.0 THROUGHOUT — a `maxspeed` move would implicate `0x0027`,
  which nothing sends; (c) reckoned velocity changes at the `0x0029` that follows the
  probe in the same burst — effectively immediate at the readout's ~10 Hz. REFUTED IF
  `movespeed` holds 1.0 across ≥3 backpedal-family sends (tape's `sent` rows checked
  first for dose) — that dynamically refutes the static handler decode.** Wiring: the
  send rides retail's own burst slot (after the `0x0025`, before the `0x0029` —
  `0x0029` last in every catalogued shape containing it, 3,023 of 3,071 bursts
  catalogued, and no catalogued shape is bare-`0x002B`; the ~1.6% uncatalogued
  remainder is the claim's bound), gated on the zero-lead verdict. Dose, MEASURED by
  replaying the rate policy over 18 recent captures: **~0.9 sends/s on sustained
  backpedal legs, ~0.6/s strafe** (the driver is the client's own report cadence
  thinned by the 0.5 s floor — the first draft's "~2/s" quoted the cap as a cadence),
  and sub-2 s legs can earn ZERO sends — the ~3 s protocol legs avoid that, and one
  send per leg suffices because the store persists. Refused without `--zero-lead`,
  pairwise with `--cancel-answer` (rival `[1.0, mt]` on the same field, cell ordering
  itself tested) and pairwise with `--checksum-probe` (the review's find: its `0x0023`
  rode the same breath ungated — an opcode retail sends zero times — and no matrix
  cell had ever met it); unknown movementTypes skip LOUDLY (census: mt strictly 1..8 —
  re-scanned 2026-08-25, 9,463 reports over 146 captures, extending the in-code
  2026-08-19 census of 7,988/119); the send slot and the mt operand are source-locked
  by ORDER and VERBATIM TEXT after the review showed string counts alone let both
  drift; `_note_wire_move` ignores `0x002B` twice over, so the probe cannot touch the
  resync model or the grant clock. `test_familyrate.py`, floor 26 from the green run.
  Settles FAMILY_RATE (CONTESTED — now TWO wire witnesses: `[0.66, 4]` CANCELWALK-F4
  to the player and `[0.75, 8]` to agent 1019, same capture) as a side effect.
  **Run recipe:** click-free, no casts —
  `python toolkit/harness/session.py --keep-open --hold 300 --game-args "--map 280
  --explorable --family-rate-probe"` plus `python toolkit/clientscan/movetap.py
  --seconds 180`; alternate ~3 s legs of forward / backpedal (S) / strafe (Q or E),
  ~4 reps each, **releasing all keys for ~1 s between legs** (measured: that clears
  the 0.5 s grant floor so the family-edge send fires at leg start instead of ~0.6 s
  in); the readout is movetap's `movespeed` beside `maxspeed`, joined to the gamesrv
  tape's `sent` rows on the wall clock.
- **REALFIX-A2 — the lead-mechanism probe (build + ~15 min owner run).** A NEW
  diagnostic flag (not the refuted arms; new composition cells; audited against the
  zero-lead invariants): D1-shaped forward lead sized by A1's answer, granted at
  report cadence, zero-distance stop-ack at `0x0047`s — the minimal retail shape.
  Scored with movetap + movesync on: arrival continuity at maturation (unknown 2),
  F27 stop staleness, F33 exposure, and the movesync hard bar. This is the
  sign-of-lead experiment; its predictions get registered at build time, one rung
  after A1 answers the speed question.
- **REALFIX-A3 — the full contract, incrementally**: S1/S2/S3 burst grammar, the D2
  clip (per Q7's answer), mid-leg re-grants on click legs (closing the click-leg
  death and HOLE A's 12.9 s silence), the bare-`0x0028` cast start replacing the
  pin's dead-reckoner (retiring the pin×resync conflict and the instant-skill
  divergence at once — gate on activation > 0 per the ledger). Each lever lands with
  registered predictions and its own run; order decided by what A2 measures.
- **REALFIX-A4 — acceptance**: our loopback tapes must be indistinguishable from
  retail under the standing instruments — the movesync hard bar (retail scores ZERO
  of 2,747 intervals over 400 u/s; ours must too), the resyncscore retail-control
  table, arrival-continuity at maturation, and a re-test of every ledger entry (F27
  stops, F33, F35, click-leg, cast-while-running, shouts NOT stopping a runner).

### 0.4 REALFIX-A1 RAN — 2026-08-25 ~20:23, scored: Q6 CLOSED (wire-steerable), and the run's warp decoded F27's gate

**The run** (`authsrv-20260825T202330-c1` × `movetap-20260825T202345`, 641 samples /
51.1 s, wall-clock joined with two millisecond-exact apply-tick pins): the owner mixed
~3 s forward/backpedal/strafe legs with ~1 s releases, click-free (c2s census: 23×
`0x003D`, 15× `0x0047`, nothing else movement-shaped). Scored by two lanes plus a
skeptic who re-derived every load-bearing number from the raw rows (NOT refuted, high
confidence).

**REALFIX-Q6 / SPEED TRUTH: CLOSED — WIRE-STEERABLE, dose-responsively.** All
OBSERVED: 22 of 22 probe sends expressed in sync `+0x60` at the first movetap sample
(17–76 ms); the store held across 931 checks with zero violations (once for 7.3 s
across a pause, nothing client-side reverts it); every one of the tape's 12 movespeed
transitions is probe-attributed; `maxspeed` 288.0 in 641/641 with zero `0x0027`. The
copy CONSUMES the float at the same burst's bake: cached velocity bit-exact
**190.08 = float32(0.66)×288** (a client-side ⅔ table would read 192.0 — the operand
is OUR wire float, discriminated), 216.00, 288.00 — and all 21 distinct armed `+0x48`
stops in the tape fit the floated formula `dist·1000/(288×float)` while the 288-flat
formula misses every non-1.0 cell by 193–914 ms: a three-family dose-response.
**Registration bonus: the two in-code tables reconcile** — FAMILY_RATE's 0.66 is what
the client STORES from the wire; `cast_stop_reckon`'s 0.652 is what the body DOES
(body-truth p50 188.1 u/s, measured in the same tape). One registration correction:
**mt 1 is keyboard-forward** — `[1.0, 1]` is not a click signature; click sends are
distinguished by LABEL, and the definitive click-free check is the c2s census.
The family-edge carry prediction got ZERO exposure (the ~1 s pauses cleared the grant
floor 12 of 12) — untested, not refuted.

**The owner's warp (strafe E ~3 s → release ~1 s → strafe Q ⇒ warp at the press),
decoded bit-level — both events are the F27 walk-start reconcile, and F27 turns out
to be GATED:**

- **Shape (OBSERVED):** at the Q press the drawn body **hard-copies the SYNC copy's
  whole movement block** (§0.5 item 7 names the copy site: `0x006022B0` from the snap
  caller's sweep — no struct copy exists inside `0x006055E0`/`0x00605840` itself) —
  landing 11.9/18.2 u from the copy, `async_stop` going 0 →
  the copy's stop tick BIT-EQUAL (42331/61984), velocity and target copied — on **no
  granted destination** (nearest dest 70.7/172.2 u away), then **walks BACK against
  the held key** for 0.9/1.65 s to the old granted point. The visible symptom is
  jump-plus-rubber-band, not a teleport. F35's signature is absent (both arms
  superseded before maturity, target never `[inf,inf]`, 0 drags in 22 armed grants —
  and three arms that matured inside key-released pauses were no-ops ≤0.1 u:
  maturity-in-pause is inert; the warp is a PRESS event).
- **The gate (OBSERVED, 15/15 press split):** the reconcile fires iff the copy is
  **MID-WALK at the press** AND **the copy's plane mismatches the body's** (sync
  plane 0 vs body 26 at both warps). Six presses at sep 350–509 u — including a
  180° forward→backpedal reversal with the copy proven mid-walk on equal planes —
  did NOT snap. **The old F27 framing ("snap at every walk-start, magnitude =
  staleness") is TOO BROAD**; strafe-specificity was geography (the E-legs crossed
  the plane-0/26 boundary), not strafe mechanics. A rival gate formulation fits
  22/22 grants — **grant `plane_cur` ≠ copy plane** — and OUR OWN plane-carry is
  load-bearing either way: the mid-leg grant carried `dest=26/cur=0`, planting the
  copy on stale plane-0 ground. The cell separating the two formulations (copy idle
  AND `pc` ≠ copy plane) never occurred in this run.
- **Snap magnitude = the reversal grant's own bake distance** (212.4/379.5 u): the
  zero-lead grant to the body's own feet is what teleports the body away from them.
- **Old defect, not minted — but the float enlarges it (SUPPORTED):** the
  movespeed-1.0 counterfactual, computed with floor-exact integer arithmetic and
  robust parked-preconditions, still fires both warps (~100.6 u and ~322 u), so the
  mechanism predates the probe; the 0.75 float widened warp A's vulnerable press
  window 3.5× (832 vs 236 ms) and added ~89 u (1.9×). The flip side is a campaign
  lesson: 1.0-everywhere made one sep-388 u reversal safe BY ACCIDENT (the copy
  out-ran the body and parked before the press). **Speed truth without fixing the
  copy-pinning/chase policy converts accidental safety into more reconcile
  exposure — A2 must carry both.**

**What settles the residuals** (the skeptic's list): (1) a no-probe repeat of the
recipe across the plane boundary — converts the counterfactual to OBSERVED and tests
warp A's thin 236 ms margin (~5 min owner time); (2) a leg engineered to leave the
copy PARKED with grant `plane_cur` ≠ copy plane — the cell separating the two gate
formulations (~5 min); (3) a static read of the client's walk-start reconcile
predicate to NAME the gate (desk, no owner time) — the `0x005355C0`/`0x006055E0`
family FINDINGS already maps. **(3) RAN the same evening — §0.5 is the record: the
gate is named, both formulations above are proxies, and the two owner cells now
carry registered mechanism predictions there.**

**Interim state (unchanged until the campaign lands):** today's defaults stand —
`--zero-lead`, `--grant-suppress`, `--cast-stop=pin`; `--resync` stays opt-in (its
run record: mechanism confirmed at 0.000 u fire cost, 8-of-8 known drags preventable —
`followon-notes/p5-resync-disarm.md` §9). No ship rulings are pending; the scaffolding
retires piece by piece as A3's levers make it redundant.

Attachment points are lines in `toolkit/authsrv/authsrv.py` in this tree.

### 0.5 The static read RAN — 2026-08-25 evening: the gate is NAMED, and it is not a walk-start predicate. It is a plane-stamped history veto.

**Run shape:** five agents against the pinned pristine 38797 — three decode lanes, then a
byte skeptic (re-disassembled every load-bearing VA with three xref positive controls;
24 of 26 checked claims CONFIRMED byte-for-byte, the two refutations non-load-bearing
operand attributions) and an empirical-fit skeptic (replayed the composed predicate
against the A1 tape: **15/15 presses and 22/22 fired grants reproduced**). Labels below
are the survivors of both.

**The mechanism, end to end (OBSERVED unless marked):**

1. **The plane stamp.** The `0x0029` handler (`0x005FD890`) passes wire **field 4
   (`plane_cur`)** to setter `0x00602A40`, which writes it **raw and unconditionally**
   into the SYNC copy's own `m_point.plane` at `agent+0x80` — one instruction,
   `0x00602A74 mov [ebx+0x80],eax` — skipped only on the `-1` sentinel (`0x00602A6F`),
   which a u16 wire field cannot produce (client-internal callers do use it — see 7).
   Field 3 (dest plane) lands in A_SEGMENT `+0x90` and A_TARGET `+0xa4`, never `+0x80`
   on an ordinary grant; the two destination-side exceptions that do reach `+0x80` are
   the ≤1.0-distSq short-circuit (`0x005FEAA0`) and arrival's commit of the destination
   point (tape sample [482] — the `0x00602B20` thread, live). **Nothing compares the
   incoming `pc` to anything: from the setter on, "grant `pc`" IS "copy plane".** Our
   mid-leg `cur=0` carry planted plane 0; the press grant's `pc=26` constituted the flip.
2. **Gate 1 is provably plane-blind.** It calls `0x00709990` with `straightOnly=1`
   (`push 1` at `0x006057C8`, range 300.0 from `[0x946564]`), and `0x00709B3F` reroutes
   both the plane-mismatch and the same-plane-too-far bailouts to the **same raw 2D
   Euclid** already on the FPU stack. No plane word is ever an FPU operand in that
   function — planes appear only in `mov`/`cmp`.
3. **The plane is operative in exactly one place: the 100 u history veto.**
   `seg_match`'s walkable conjunct calls `0x00709990` with `straightOnly=0`
   (`push 0` at `0x00605C40`): the cheap shortcut needs **matching planes AND
   dist²≤1.0** (`cmp` at `0x00709AD1`); anything else goes to a **real navmesh
   pathfind** (`0x00721A30`, called at `0x00709B99`); `pathCount==0` returns exactly
   the **`range+1.0` no-path sentinel** (decoded to the instruction) → no match → the
   veto fails. Both of the fit-skeptic's queued static discriminators were **already
   answered by FINDINGS' 2026-08-20 pseudocode** (FINDINGS.md:2707-2743, RECONCILED):
   the walk is segment-based with a rolling `prev` (`0x0060571A`), and the constructed
   closest point **inherits the node's plane** (`c.plane = a.plane`, w forced 0 at
   `0x00605BD5`) — which is what hands the chain's plane words to the pathfind.
4. **So the decoded decision at every grant is:** SNAP iff *(no history segment within
   100 u whose plane connects to the copy's stamped plane)* AND *(a distance gate
   fires)*. **No code term reads "mid-walk" into the snap decision** (the only `+0x48`
   read in `0x006055E0` is Early-Out A, requiring mode==9 — inert in this run; the
   `+0x48` read at `0x006058D6` only selects the new history node's seed vertex), and
   **no code compares `pc` against the copy's previous plane**.
5. **Both empirical formulations are proxies for this (fit skeptic):** F1's "MID-WALK"
   term is **emergent** — a parked copy's chain holds its arrival node where the copy
   stands (dist 0.0 on a same-plane segment), so parked copies **self-veto** *(§0.8,
   2026-08-26: byte-grounded and STRONGER than written here — the self-veto rides
   seg_match's degenerate arm, which reads no plane word at all, so it holds even
   against a deliberately mismatched stamp; plane-proof, exercised live 8/8)*; F1
   mispredicts two cells when applied beyond presses, REFUTED as mechanism. F2
   (grant `pc` ≠ copy plane, 22/22) is the better proxy because the `pc` stamp rewrites
   the query's plane **ahead of the veto** — but the seam geometry is load-bearing (the
   trail segment straddling the measured y≈−2884 plane-0/26 boundary, islands the
   pathfind cannot connect), so it is not the literal predicate either. The lane's own
   rival hypothesis that plane-mismatch merely proxies a large coordinate delta is
   **REFUTED by the tape**: the correlation is mechanism.
6. **The warps replayed exactly (fit skeptic, on the decoded semantics):** the press
   grant's `pc=26` re-stamps the copy while it stands ON a seam-crossing trail segment
   → cross-plane covering segment fails the veto via the pathfind sentinel → warp B
   (sep 379.5 > 299.33) snaps through **plane-blind gate 1**; the six no-snap presses
   at sep 351–509 u were saved by the **veto** (min node distance 130.9/131.6 u — only
   the segment construction with the copy at dist 0.0 on a same-plane segment explains
   them; gate 1 alone cannot). **Warp A (sep 212–223, below the cut) was the one
   unclosed attribution — narrowed the same night, §0.6:** gate 1 is EXCLUDED at byte
   level, so warp A fired via **gate 2 OR gate 3** (the disjunction CONFIRMED); the
   single-gate pick stays RECONSTRUCTION pending `0x005FF820`'s plane propagation.
   (This sentence originally said the fallback half was "still-UNDECODED" — it was
   not; see §0.6's first paragraph.)
7. **The copy site, closed (byte skeptic's bonus):** no struct-to-struct copy exists
   anywhere in `0x006055E0`/`0x00605840` (FINDINGS.md:3176-3230 already said so — the
   §0.4 phrase "hard-copies the movement block" is tape-observed but the copy rides
   elsewhere): the reconcile that moves the body is **`0x006022B0`**, reached from
   `0x00605FC0`'s tail sweep — `+0x48`-gated dead-reckon via `0x005FF880`, position set
   via `0x00602540`→`0x00600B70`, then **re-issues `0x00602A40` with `field4=-1`** (the
   sentinel skip is intentional API: the reconcile deliberately leaves the plane word
   alone). Also closes the KNOWN MAP's third `0x00605FC0` caller: `0x00602BBD` sits in
   `0x00602B20`'s idle branch.
8. **The press path is clean — and has a door.** An ordinary press sets the facing
   triple, arms the fence, sends `0x003D`, and touches no position/velocity/target
   field (RECONCILED with CANCELWALK.md); every reconcile in the tape is
   grant-synchronous, so "warp at the press" is the reply grant 17–76 ms later. NEW:
   a conditionally-gated fallback exists — `0x008163A0` → `0x0081BDB0` → `0x005FCAA0`
   (**Q5's "gate-free reseed", now decoded**: a 3-instruction trampoline) →
   `0x00605E40` (an instruction-for-instruction twin of `0x00605FC0`'s sweep) →
   `0x006022B0`. Unexercised in this run; whether an ordinary press can reach it is
   open (static gating: only when the primary applier AND `0x0070a170` both fail).
9. **One prior claim REFUTED by the tape** (correction filed in PROBE-GATEFIRE.md
   §(a)): `hist_head` is NOT identically 0 through open stretches on world 0 — the
   chain was alive in **617/641 samples, up to 8 nodes**, appending at grants, stops
   and seam-crossings with the fence open. The 100 u veto **runs with live data**, and
   it — not gate 1 — decided every high-sep no-snap press. Who appends on open
   stretches ~~is the open thread; prime suspect: the same undecoded fallback half~~
   — **CLOSED the same night, §0.6: two routes, and the fallback half is exonerated
   (it appends on no branch).**
10. **Design consequences for A2:** (a) **plane truth joins speed truth** — the `pc`
    word we send re-stamps the copy raw, so A2's grants must carry the agent's true
    current plane, never an echo of a stale word and never 0; (b) ~~the fallback-half
    decode is the next desk item~~ — **RAN the same night, §0.6** (the span was already
    decoded 2026-08-20; the follow-up verified it byte-for-byte and closed the
    appender question); the remaining *optional* desk item is `0x005FF820`'s plane
    propagation, which would promote warp A's gate from a disjunction to a name; (c) the
    two owner cells now carry **registered mechanism predictions**: *parked + `pc`-flip*
    → the veto fails but no distance gate fires at parked separations → **predicts NO
    snap** (this is the cell where the mechanism and F2-as-proxy separate); *no-probe
    warp repro* → **predicts both warps fire** (converts the 1.0-counterfactual to
    OBSERVED). *(Both RAN the same night — §0.8: no-snap outcome CONFIRMED but this
    cell's premise REFUTED — the veto does not fail on a parked copy, it holds
    plane-free on the degenerate arm; and the warp repro converted the B-shape only,
    A-shape unexposed.)*

### 0.6 The fallback-half follow-up — same night: the span was never undecoded, the appender is IDENTIFIED, and warp A narrows to gate 2 ∨ gate 3

**Run shape:** one decode lane + one high-effort skeptic, both re-disassembling from
the pinned pristine 38797; the skeptic ran its xref census with positive controls
(known call sites found before new ones were trusted). **Zero refutations.**

**First, the correction this section exists to file (FB-0, CONTESTED → resolved):
§0.5 called `0x00605753`–`0x0060583D` "still-UNDECODED". It was decoded five days
earlier** — FINDINGS.md's own round-2 section (":3073, THE FALLBACK HALF IS DECODED",
2026-08-20) maps it in full, and both agents' fresh byte reads reproduce it
instruction-for-instruction (57 instructions, same jcc bytes, same three writes to
the `edi` return accumulator). The stale label came from the pseudocode comment at
FINDINGS:2719, which contradicted its own file 350 lines down; `followon-notes/
f33-trigger.md` (2026-08-25) had also independently reached most of this and was not
yet reconciled into §0.5. The comment is fixed in place. *Process lesson, the
grep-before-"never-tried" rule in its nastiest form: the label at the definition
site can contradict the record below it in the same file — grep the file for the
address before calling anything undecoded.*

**The appender question, CLOSED (all OBSERVED, skeptic-confirmed):**
`0x00605840` has exactly **3 direct callers** and its node allocator (`0x00604BB0`)
has exactly one, inside the appender's own body. **The fallback half calls neither on
any branch** (its only calls: two asserts, two `0x005FF820` position bakes, the three
gates, the stack cookie). Open-stretch chain growth is carried by:
1. **Dispatcher path B1** — the append at `0x0060610B` runs **unconditionally on
   every ARMED world-1 dispatch** (`je` at `0x00606016`: `clientControlled != 0 AND
   world == 1` skips the snap test entirely and appends). The per-id AgTrack record
   is **shared across worlds**, so async dispatches feed the very `hist_head` the
   world-0 test walks — the inference PROBE-GATEFIRE §(a) missed. (The same physical
   call is also reached by `clientControlled == 0 AND world == 0`, the ordinary
   unarmed sync append; no route appends on `world == 0 AND clientControlled != 0` —
   that combination reaches the snap test instead.)
2. **A periodic staleness sweep** — caller `0x00604B2A` inside a per-record loop
   (`0x00604880`, stride 0x1c, two callers `0x005FC110`/`0x005FC24A`), gated on
   `hist_head` non-null and **> 0xd05 = 3333 ticks** since the head node's stamp,
   fence-INDEPENDENT; `clientControlled` only selects which world's array it samples.
Only the per-event mapping of the tape's appends onto these two routes remains
UNVERIFIED — nothing rests on it.

**Warp A, narrowed (V-WARP-A):** gate 1 is **EXCLUDED at byte level** — sep 212–223 u
is below the 299.3326 effective cut and the LUT sqrt errs only high, so the `jne` at
`0x006057EA` cannot fire — therefore, on §0.5's premise that the cross-plane sentinel
had already killed the veto, **warp A fired via gate 2 (`pathCount == 0`, `je` at
`0x0060580D`) OR gate 3 (`0x005FEF70` returns 0, `je` at `0x00605820`)** — the
disjunction CONFIRMED from bytes plus tape. Promoting it to a single gate needs
`0x005FF820`'s plane propagation (do the baked query points carry the stamped plane
word?) and gate 2's start-resolver plane-keying — neither disassembled yet, and
neither blocks A2. *(§0.8, 2026-08-26: `0x005FF820` is now decoded — position_at,
two arms, plane from `+0x90` when arrived and `+0x80` otherwise; the gate-2
plane-keying half stays open and its test cell is the mid-walk spoof registered
there.)*

**Byte bonuses:** gate 2's `maxDist` is not a fresh constant load — it consumes **gate
1's leftover 300.0 riding the x87 stack** (`fstp st(1)` at `0x006057E5` leaves it;
`fstp dword [esp]` at `0x006057FA` spends it), one literal serving two gates. The
span reads **zero plane words** (the lone `-0x80` displacement is a world-array
container field off a spilled manager pointer, corroborated at three independent
sites) and **writes zero agent/record fields** — re-confirming §0.5 item 7 from the
other side.

**Ladder impact: none.** A2's design consequences (§0.5 item 10) stand as written;
the owner cells' registered predictions are unchanged.

### 0.7 The two owner cells — run recipe (registered 2026-08-25, before the run)

**One session covers both.** The A1 argv is pinned from the tape itself (`grant_verdict`
rows: `plane_carry: true`, arm `zero-lead`; probe rows present; nothing else surfaced in
1,490 sent rows), so the minimal pair drops exactly one flag:

```
python toolkit/harness/session.py --keep-open --hold 600 --game-args "--map 280 --explorable --zero-lead --plane-carry"
python toolkit/clientscan/movetap.py --seconds 240        # start once in the map; once per cell
```

(~~The §0.3 A1 recipe line abbreviated the game-args~~ — CORRECTED same night:
`--zero-lead` and `--plane-carry` **default ON** since the 2026-08-22 three-state flip
(authsrv.py's default block), so §0.3's line was complete and the explicit flags above
are redundant-but-harmless, kept for legibility. The tape remains the config authority
either way. Same map, same seam area as A1: the y≈−2884 plane-0/26 boundary the
E-strafes crossed.)

**CELL 1 — no-probe warp repro** (first movetap): the A1 warp recipe, ≥3 attempts —
strafe **E ~3 s crossing the seam → release ~1 s → strafe Q**; one extra attempt with a
~2 s release. **PREDICTION (registered §0.5 item 10c): both warps still fire at
movespeed 1.0** (converts the counterfactual to OBSERVED). Warp A's press window is the
thin one (236 ms at 1.0) — an A-shaped miss on one attempt is expected noise, which is
why ≥3 reps; a B-shaped (large-sep) warp should fire reliably.

**CELL 2 — parked + `pc`-flip** (second movetap). Under `--plane-carry`, field 4 lags
one grant — so the flip-at-parked is engineered by making a plane crossing happen inside
a leg too short to fire its own second grant:
1. Stand ~100 u NORTH of the seam (plane-0 side). Hands off **~5 s** (copy parks).
2. ONE quick tap toward the seam (≤0.5 s) that carries the body ACROSS onto plane 26.
   (If a single tap doesn't cross, park closer and retry — the tap's only grant fires at
   its start, dest still plane 0, so the copy stays on plane-0 ground.)
3. Hands off **~5 s** again (copy parked, stamped plane 0).
4. Press and hold strafe (Q or E) **~2 s** — this press is the cell: its grant should
   carry `plane_dest=26 / plane_cur=0` with the copy parked. Release ~2 s.
5. Repeat 4–6 times; include 2 mirror reps (south→north).
**EXPOSURE (pre-registered, the zero-exposure rule):** a press counts only if its
`grant_verdict` row shows `plane_differs: true` AND movetap shows the copy parked (arm
0, velocity 0) at the press. **Floor: ≥3 exposed presses, else the cell ABORTS as
zero-exposure** and the follow-up is a server-side lever, not a re-run.
**PREDICTION (registered §0.5 item 10c): NO snap** — the veto fails but no distance
gate fires at parked separations. **If it snaps anyway, gate 2 is plane-keyed** and
warp A's attribution firms toward gate 2 — either outcome is a finding.

**CELL 2 REVISED — 2026-08-25 ~23:17: the geography design is RETIRED.** The owner
ran it and could not stage the condition — the seam is a **bridge too narrow to
strafe**, and the tap-across choreography never produced the flip. Per the
pre-registration above, the follow-up is a **server-side lever, not a re-run**:
`--pc-spoof` (built the same night, `test_pcspoof.py` floor 23 — the first fired
grant after ≥4.0 s of grant silence sends the flag's plane id as field 4, once per
park; `PC_SPOOF_GAP` sized above A1's 3.054 s leg-cadence maximum and below the
recipe's parks). The cell now runs ANYWHERE on ordinary plane-0 ground:

```
python toolkit/harness/session.py --keep-open --hold 420 --game-args "--map 280 --explorable --pc-spoof 26"
python toolkit/clientscan/movetap.py --seconds 240
```

Per rep, 6 reps: **hands off ≥6 s** (the copy parks; the gap re-arms the spoof) →
**hold a strafe ~2 s** (the press's grant goes out `field4=26`, `pc_spoofed: true`)
→ release. Stay on plane-0 ground (A1 read plane 0 in 641/641 samples away from the
bridge); a rep standing on plane-26 ground is VOID (`plane_differs: false`) — the
census scores it out. **Exposure rule and floor unchanged: ≥3 reps with
`pc_spoofed` AND `plane_differs` both true, else ABORT.** Prediction unchanged, both
outcomes registered above.

### 0.8 The night scored — 2026-08-25 ~23:12 → 26 ~00:00: three runs, two workflows, and the plane story rewritten by a degenerate segment

**Run shape:** the three owner runs (`authsrv-20260825T231037-c1` covering
`movetap-20260825T231250` C1 and `movetap-20260825T231718` C2-geography;
`authsrv-20260825T233109-c1` × `movetap-20260825T233125` the `--pc-spoof` lever run)
scored by two workflows totalling six agents; every load-bearing number below was
re-derived from raw rows by a skeptic, and every load-bearing byte re-disassembled
from the pinned pristine 38797. (One fit lane died mid-run returning a stub; the
skeptic re-did its work from scratch — its numbers are the ones cited.)

**C1 — the no-probe warp repro (§0.7 cell 1): the B-shaped warp is OBSERVED at
movespeed 1.0; the A-shaped stays unexposed.** Exactly 4 snaps (owner reported 4),
full hard-copy signature: `async_stop` → bit-equal with the sync stop tick, press-to-
snap 16.8–41.6 ms (A1's band), landing 15.0–26.8 u off the copy, jump 314.7–334.6 u,
back-walk 1.10–1.24 s landing **0.00 u on the triggering press's own granted dest**.
All four at sep 351.2–374.4 u — above the 299.3326 cut. **The 1.0-counterfactual is
CONVERTED to OBSERVED for the B-shape (4/4, reliable)**; zero A-shaped exposure
occurred (no below-cut flip press ever happened — checked at press level, not just
fire level), so warp A's counterfactual stays SUPPORTED per the zero-exposure rule.
The window's 13 plane-flip grants split 4 fires / 9 saves on a clean press-level
pattern reconciling §0.5–0.6. One CONTESTED flag kept honest: the four landing
points sit 7.6–27.7 u from one ~46–92 s-stale spawn-area grant — noted as
coincidence, not asserted as targeting.

**C2-geography (§0.7 cell 2 as originally staged): the letter of the exposure rule
was MET — and the rule's proxy was broken.** 12 presses, 12/12 parked, 3 with
`plane_differs` true — **exactly the floor**, so "zero-exposure ABORT" was wrong at
the letter. But `plane_differs` compares the carried word against the REPORT's
plane, not against the copy's stamped word, and at mechanism level the true
pc-vs-copy-word flip count was **0 of 8** — the discriminating condition was never
staged, the no-snap null is UNTESTED there, and retiring the geography design was
right for a different reason than registered. The geography itself is now mapped:
**the seam is y = −2884.0 ± 3.9 u; the dominant plank crosses at x ∈ [−6124, −6081],
core ~40–60 u wide** — against the 576 u a 2 s strafe covers. The recipe asked for a
tightrope walk.

**The `--pc-spoof` run: outcome CONFIRMED, reasoning REFUTED — and the refutation is
the finding.** 9/9 spoofed grants exposed by the registered key (8 in-tape; movetap
attached ~6 s late, again), all with the copy parked, park gaps 7.9–12.4 s.
**Zero snaps.** But 7 of 8 presses fired at sep 378–494 u — ABOVE the gate-1 cut,
fence open, `gate_reach: test-runs`, no early-out — so had the veto died, gate 1
must have fired. It did not, and §0.7's registered reasoning ("the veto fails but
no gate fires at parked separations") is **refuted on both clauses**: the
separations were not small, and **the veto did not fail — it HELD**.

**Why it held — byte-grounded, and it closes the operand question:**
1. **q's plane IS the stamped word (Story A, OBSERVED).** The snap test builds its
   query at `0x00605643`–`0x00605663` as a raw 4-dword copy of `source+0x78..0x84`
   — `q.plane = +0x80`, unconditional, unbaked, no branch. And the stamp provably
   precedes the test **in the same message**: setter `0x00602A74` stamps, then
   `0x00602AD3` → bake `0x005FE950` → `0x005FEBEB` → dispatcher `0x00605FC0` →
   `0x0060601C call 0x006055E0`; the tape corroborates (`point[2]` flips to 26
   within 55–96 ms of every spoofed grant). q was 26 at all 8 presses. The rival
   "query rides the destination plane" story is REFUTED at the bytes.
2. **The veto held on seg_match's DEGENERATE arm, which is plane-FREE.** A parked
   copy's chain holds a degenerate covering segment at distance ~0 from q, and the
   degenerate arm (FINDINGS.md:2722-2724: `a == b` → pure 2D distance, strict `>`)
   **reads no plane word and calls no pathfind**. The spoofed label was never
   consulted. **A parked copy's self-veto is PLANE-PROOF — `--pc-spoof` cannot
   ever warp a parked copy**, because it plants a label without moving the body
   onto disconnected geometry. (§0.5 item 5's emergent self-veto: CONFIRMED and
   extended to the mismatched-stamp case; §0.5 item 10c's parked-cell premise:
   REFUTED.)
3. **The bake family is now decoded (the §0.6 "optional" item, done):**
   `0x005FF820` = `position_at(this, out*, when)`, two arms on the agent's own
   `+0x48` — ARRIVED copies `+0x88..0x94` verbatim (plane = **field 3**, `+0x90`);
   otherwise the extrapolator `0x005FFB40` reckons x/y and copies plane from
   **`+0x80`** (`0x005FFBD7`). Neither writes back. Six callers, two newly found:
   the **history appender bakes each node it pushes** (`0x006058BF`, same agent) —
   so a node's plane is an append-time snapshot through the same two arms — and
   the staleness sweep (`0x00604916`). `0x005FF880` is the distinct settle that
   DOES write back `+0x78..0x84`. movetap's `position_at()` model matches the
   bytes field-for-field; the ARRIVED arm has never been observed live
   (0 of 4,115 corpus samples).

**What the whole night does to the mechanism statement:** the plane term enters the
snap decision in exactly ONE place — the **non-degenerate** arm's
mismatch-→-pathfind route — so the discriminator behind every observed fire/save is
**degenerate-vs-non-degenerate covering segment, and real-disconnect-vs-fake-label**,
not any single wire field. F2 ("grant `pc` ≠ copy plane") is re-refuted as a literal
predicate by this same night's C1 tape (two mid-walk flip grants at sep 301.9/355.1
with no snap; five instants with copy-word ≠ `pc` and no snap). Parked players
cannot be warped by plane garbage; **the entire danger surface is a MID-WALK copy
whose covering segment crosses a label mismatch.**

**The one cell left, registered here:** a **MID-WALK spoof over flat connected
ground** — the only configuration that makes the operand observable in behaviour
and the only remaining probe of whether `0x00721A30`'s pathfind fails on a bogus
label over connected (x,y) (statically unproven either way). It doubles as the
gate-2 plane-keying test (warp A's §0.6 residual). The current lever cannot stage
it (parked-first trigger by design); it needs a small trigger variant (fire the
spoof on a mid-leg grant). **Not built tonight — nothing in A2's design blocks on
it**; A2's plane-truth requirement (§0.5 item 10a) stands on the setter decode
alone.

**Instrument flags, for the file:** movetap ends far short of `--seconds` (60.9 s /
81.4 s / 77.5 s against 240 across the night's three tapes, and A1's was 51 s —
systematic, unattributed); C1 showed `fence_state: shut` in 14.9% of samples while
C2 showed none under identical args (unattributed, flagged); the late-attach cost
one press of the lever run's nine.

### REALFIX-P2 · `--zero-lead`

Attachment: heading arm `:9625-9878`, as a third named block after `:9843`. **Stop arm `:10235` untouched. Click arm `:9879` untouched.**

```python
# --- heading arm, authsrv.py:9625, inside `if moving:` ---------------------
reported = tuple(values[1]); plane = values[2]; mt = values[4]
u        = unit(values[3])                 # |vec2| ∈ 765.0..768.0, ours+live

# TRIGGER: every 0x003D while moving. This DROPS the shipped gate at :9758
# (`turned or walking is not True`). NAMED VARIABLE #2 -- on click-free play
# that gate opens on only 11.1/24.3/61.2/80.8% of moving reports (ours,
# 182554/182934/100340/173940), a 1.24x-9x cadence delta; on the click-heavy
# refuted runs it is invisible (182652: 193/193, 171153: 447/447).
# It is cheap HERE and only here: a zero-distance grant takes the <=1.0 u
# short-circuit at 0x005FEA92 and dispatches nothing.

if not _heading_grant_ok(state, now):      # NOT _grant_verdict -- see note
    record("rate-limited"); return

send(GAME_SMSG_AGENT_MOVE_DIRECTION, [PLAYER_AGENT_ID, u, mt], ...)   # :9797 already
send(GAME_SMSG_AGENT_MOVE_TO_POINT,
     [PLAYER_AGENT_ID, list(reported), plane, plane], ...)
#   NO lead.   NO clip: a point the client reported STANDING ON is walkable
#              by witness (O5).   NO staleness gate: age 0 by construction.
#              NO straight-shot gate: the segment is zero-length.
#   NO STOP-ARM GRANT. That is --stop-echo and it is REFUTED (:1012-1017).
```

**⚠ CORRECTION, 2026-08-21 — "a zero-distance grant takes the `<=1.0 u` short-circuit and dispatches nothing" is FALSE of P2's grants, and the cheapness argument above rests on it.** The claim is true of the grant's distance from the **client**, which is zero by construction, and false of its distance from the **SYNC COPY** — and `+0x78` on the copy is the operand `0x005FE950` actually measures (`D8 66 78 fsub dword [esi+0x78]` at `0x005FEB57`; FINDINGS §2.4's own point). The copy is chasing a player at run speed, so it is nowhere near where the player has just reported standing. OBSERVED, replaying P2 through `toolkit/clientscan/grantsim.py` against the four zero-grant `ours` captures: only **6 of 539** synthesized P2 grants take the `<=1.0 u` arm (3 of 130 on `20260811T173940`, 1 of 74 on `182934`, 1 of 317 on `100340`, 1 of 18 on `182554`), and the median `|d|` from the copy is **101 / 383 / 208 / 512 u** respectively. **Every other P2 grant bakes a real leg and dispatches at `0x005FEBEB` — a class-A test instant.** The attachment point and the code block above are unaffected; what this retracts is the ground for dropping the `turned or walking` gate at `:9758` "because it is cheap here", since P2's extra cadence is not free. Price that trade on the numbers rather than on the short-circuit.

**RE-MEASURED 2026-08-21 under the SHIPPED policy, and quote these instead.** The figures above were taken while `lead_policy` carried **no rate limit at all**, because `_heading_grant_ok` did not exist yet. It landed the same day; with it applied the four counterfactual captures give **5 of 358** grants on the `<= 1.0 u` arm (2/63, 1/64, 1/214, 1/17) and medians **143 / 420 / 250 / 512 u** (`173940` / `182934` / `100340` / `182554`). The grant count falls because the 0.5 s floor refuses the reports inside it; every median RISES because the copy has longer to run away between grants. Same conclusion, stated harder.

**⚠ `_grant_verdict` must NOT be called from the heading arm.** It is the *click* arm's policy (`:3004-3011`) and its Rule 1 refuses whenever the local-driving latch is younger than `GRANT_LOCAL_WINDOW = 3.0 s` (`:2942`, `:3027-3029`) — a latch the heading arm arms **ten lines earlier**, at `state["kbd_moving_at"] = time.time() if moving else None` (`:9715`). Age ≈ 0.0 on every call, so under `--grant-suppress` P2/P3 would emit **zero** grants and degenerate into P6 wearing a new name. `TESTS.md:3220-3225` independently prices the same window at 87% of one capture's span. **Build `_heading_grant_ok` as a new pure predicate carrying Rule 2 only (`GRANT_MIN_INTERVAL`), with its own reason string, and record refusals to the same telemetry channel.**

### REALFIX-P3 · `--short-lead=<u|adaptive>`

Attachment: same block. **Identical to P2 except one line.**

```python
MATCH_RADIUS = 99.919968     # UNVERIFIED IN-TREE until §2.6 lands. See note.
REFRESH      = 0.30          # our own report cadence p50, ours, click-heavy
LEAD_FIXED   = min(RUN_SPEED * REFRESH, MATCH_RADIUS - 14.0)   # = 86.0 u

def lead(state):
    if MODE == "fixed": return LEAD_FIXED
    return min(766.0, RUN_SPEED * state["report_gap_p50"])      # adaptive arm

L = lead(state)
D = (reported[0] + L*u[0], reported[1] + L*u[1])
send(GAME_SMSG_AGENT_MOVE_TO_POINT, [PLAYER_AGENT_ID, list(D), plane, plane], ...)
#   UNCLIPPED, deliberately -- so P2 / P3 / --client-endpoint differ on ONE axis:
#   lead = 0 / 86 / 766. Adding clip_to_walkable makes it two variables against
#   BOTH neighbours, and our heading-arm clip suspends collision entirely when
#   our mesh does not cover the player (FINDINGS:3428-3432) so it would not even
#   express retail's D2.
```

**Known exposure before it runs, `ours`, n = 852:** at arrival `q = D` exactly, and `|D(86) − the client's next report|` is p50 **89.4 u**, p90 **136.4 u**, with **45.7% at or beyond the match radius** (turn-conditioned n = 291: p50 41.1 / p90 116.8, 14.8%). **P3 is expected to fail the match on ~46% of arrivals and land in gate-2/gate-3 territory, which nothing offline can price.**

### REALFIX-P1 · `--retail-grant` — fidelity reference, NOT an experiment

```python
state["move_family"] = None                        # NEW KEY -- nothing tracks this today
FAMILY_RATE = {1:1.00,2:1.00,3:1.00, 4:0.66,5:0.66,6:0.66, 7:0.75,8:0.75}   # CONTESTED

# heading arm
endpoint = reported + vec2 + 0.5*u                                  # D1, live, ADJUDICATED
dest, _  = clip_to_walkable(state, endpoint)                        # D2 approximation only
send(0x0025, [PLAYER_AGENT_ID, u, mt])                              # S1
if mt != state["move_family"]:
    send(0x002B, agents.agent_update_speed(PLAYER_AGENT_ID, FAMILY_RATE[mt], mt))
    state["move_family"] = mt                                       # S2
send(0x0029, [PLAYER_AGENT_ID, list(dest), dest_plane, state["plane"]])   # S3, ALWAYS LAST

# stop arm :10235      -- 0x002B then a ZERO-DISTANCE 0x0029. NEVER 0x0028.
# click arm :9879      -- grant the clicked point verbatim, do NOT hold it.
# idle                 -- re-grant on a heading OLDER than 1.0 s (retail's 73 rows,
#                         lag p50 2.58 s). Do NOT build an unsolicited-grant channel.
```

**Planes are `(dest_plane, cur_plane)`, never `(0, 0)`** — field 3 = destination plane, field 4 = current plane, closed from the binary three times (`FINDINGS:3364`, `:3428`, `studies/smsg/FINDINGS.md:130-135`); forcing 0 writes a wrong map index into `agent+0x80`. `authsrv.py:9987` already orders them correctly *(:9987 at its writing — the send now sits near :14700 at HEAD; line refs in this document drift and the structure, not the number, is the anchor)*. `FAMILY_RATE` is **CONTESTED**; the decider is `movetap.py` on `agent+0x5C`/`+0x60` during sustained backpedalling, not the wire — though the wire now carries ~~one row's witness~~ **two rows' witnesses** *(second found 2026-08-25)*: `0x002B [0.66, 4]` answers the backpedal press at `20260824T074002` t=108.376 ([CANCELWALK.md](CANCELWALK.md) F4), agreeing with the table's 4:0.66, and `[0.75, 8]` to agent 1019 at t=43.262 of the same capture agrees with 8:0.75. *That decider is now BUILT: `--family-rate-probe`, REALFIX-A1 (§0.3), floor-22 tested; the owner run is next.* **And the stop arm's "NEVER `0x0028`" gained a caveat 2026-08-24**: right about the c2s side, but retail's s2c stop answer has a second form — a bare s2c `0x0028 [agent]` with no re-pin at t=65.095 of the same capture, selector unread (CANCELWALK-F5).

**Four-variable delta from `--client-endpoint`. Do not run before the lead family; a bad result names none of the four.**

### REALFIX-P5 · `--resync` (built, ~~never run~~ run once WITHOUT grants — see below) · REALFIX-P6 · `--grant-suppress` (built, run once) · REALFIX-P0 (shipped)

No new code. P5 needs `RESYNC_MAX_REPORT_AGE = 100.0/288 = 0.347 s` (already at `:2665`) and the plane refusal already present; score it on `resyncscore`'s yank column, never on the hard bar.

**P5 status, 2026-08-25 — STAGED for the disarm run.** The "never run" above was
corrected by the follow-on recon (`followon-notes/README.md` §2.3,
`followon-notes/refute-lens-empirical.md` §1.3): a
2026-08-20 run fired 18 `0x002C`s but sent **zero grants**, so it never armed an
arrival and tested nothing about the disarm. What is now in place, all tested:
**`RESYNC_SEPARATION` reconciled to 100.0** in both files (owner-delegated ruling,
§4.2a's block in the p5 note; the fence value 299.33 lost on the [100, 299.33)
differential band — 120 of 157 shipped-regime fires sit in it, all refused at the
fence, and the fence's fire set is a strict subset of 100's), **HOLE D's
first-verdict assertion** (`SYNC MODEL NOT SEEDED` prints
loudly once if the placement seed never ran — a silent-inert flag was the p5 note's
reproduced failure), and **P8's lever** (`--resync-separation 2000`, the registered
nothing-fires negative control; refused without `--resync`). The run protocol and
its eight registered predictions are `followon-notes/p5-resync-disarm.md` §8; the
run is the owner's, and P5 is expected to **bound** the snap at 100 u, not remove
it (HOLE B) — the Q10 conversation after the run should price that residual.

### REALFIX-P4 · `0x0027` re-arm — **DO NOT BUILD**

New SMSG constant + new builder + new wire test, for a candidate the mechanism read grades FAILS provably (`0x00602910` rewrites `+0x78` to the runaway point — attribution refined 2026-08-24, [CANCELWALK.md](CANCELWALK.md) §7 F13: the rewrite is the settle `0x005FF880` the setter calls, and it fires only while a leg is armed, `+0x48 ≠ 0`; the verdict is unchanged, and the elimination now also rests on store parity — both copies hold 288.0 from our own create) and the harness cannot score. If it is ever revisited, the schema row is `schema/overrides.json` GAME_SMSG `"39"`: `msg_header + dword(agent) + float(maxSpeed)`, `declared_unpack_size 10`, assert `AgAgent.cpp:2317 maxSpeed >= 0`.

---

## 2. REALFIX-H1 — the offline harness

**New module `toolkit/clientscan/grantsim.py`; new test `toolkit/clientscan/test_grantsim.py`.** Obeys the house rule of its neighbours: *opens vault captures and writes nothing*, never imports `authsrv.py`, defines no bar of its own.

### 2.1 What it is for

**A calibration instrument, a refusal instrument, and an exposure meter — not a ranker.** §6.4 of the research draft is the reason. Any output that orders two candidates on a common scale is out of scope; the file prints exposure per candidate on the candidate's own axis.

### 2.2 Reuse vs. new

Reuse verbatim: `movesync.load_wire_reports / load_grants / steps / hard_steps / denominator / pair / offset_from_stamps`, `resyncscore.sync_track / validate_sync_model / track_from_capture` (whose origin refusal is the gate), `origin.origin_of`, `vaultpath.require_dir`, `checks.Ledger`. New: a `c2s_moves(path)` reader keeping `values[3]` and `values[4]` (which `load_wire_reports` drops); the `≤ 1.0 u` short-circuit; the `+0x48` arrival tick; test-instant enumeration; the match proxy; the reseed; and the two new metrics. **Do not fork `sync_track`'s glide.**

### 2.3 Pipeline

1. **LOAD** — reports and as-sent grants through `movesync` unchanged (a second decoder is a second chance to disagree about what the client said).
2. **SYNTHESIZE** — one pure `policy_<name>(c2s, state) -> [(t, D, plane_dest, plane_cur, kind)]` per candidate.
3. **SIMULATE** the bake byte-exact: `d = D − [+0x78]`; `S = [+0x60]*[+0x5C]`; if `|d|² ≤ 1.0` write `+0x78 = D`, zero velocity, arm `+0x48 = now+1`, **return with no dispatch and no fan-out**; else `vel = unit(d)*S`, `[+0x58] = now`, `[+0x48] = now + trunc(|d|*1000/S)` clamped ≥ 1; read `[+0x78] + vel*((t−[+0x58])*0.001)`; park on arrival.
4. **TEST INSTANTS** — class A (bake, one per grant with `|d| > 1.0`) and class B (arrival SetPosition). **Print as a FLOOR** and label it: child recursion (`0x0060221E`) and the bake's post-dispatch fan-out (`0x005FEC7E`/`0x005FEC9A`/`0x005FECAC`, `0x00602BE5`) multiply both.
5. **MATCH PROXY** — `q` against the client's own report track over `[max(armed_since, t − 5.0), t]`, radius `MATCH_RADIUS`, **straight-line only**. That is correct in this regime, not a simplification: a degenerate segment skips the walkable conjunct, and segment 0 is degenerate exactly when `+0x48 == 0`.
6. **GATE-1 PROXY** — `sep ≥ 299.332591 u` ⇒ SNAP. Exact cut, three independent exhaustive derivations; exactly 300.0 u snaps.
7. **RESEED** — sim ← client position, `armed_since ← t`, modelling the roster-wide wipe at `0x006060A2`/`0x006060A9`.
8. **SCORE** — see 2.4.

### 2.4 Metrics — every capture, every candidate, origins never pooled

- **PRIMARY: survival time and survival distance to first violation**, over `[start, min(first predicted snap, first measured hard step))`, with the censor instant named.
- **REALFIX-M1 · lag age** — the age, in seconds of client travel, of the newest polyline point within the radius of `q`, reported p50/p90/max against the chain's ~5 s block-recycle bound. **This is P2's axis.**
- **REALFIX-M2 · arrival exposure** — fraction of class-B instants with `|D − client track| ≥ MATCH_RADIUS`. **This is P3's axis.**
- **A BRACKET, always, never a skip:** `[snaps with the match test ON, snaps with it OFF]`. The match-on figure is a lower bound and the match-off figure an upper bound. **This replaces the drafted "skip the match test when chord p90 > radius" rule, which fires on 4 of 4 counterfactual and 7 of 11 calibration captures and would degrade the whole plan to the refuted separation-only scorer.**
- Secondary: censored snap count; rate on **both** denominators (per minute of span, and per minute of active time **with the 2.0 s threshold named**); u displaced per active second; separation p50/p90/max; instant count (floor); **and the capture's own report gap p50/p90 and chord p50/p90 printed beside every row.**

### 2.5 Inputs

**CALIBRATION (`ours`):** `20260820T182554 / 182934 / 183311 / 195137 / 195315`; the five movetap pairs `145717·145939`, `150336·150349`, `150522·150537`, `152716·152723`, `171153·171436`; `20260819T182652`; `20260814T100340`; `20260811T173940`. The three undocumented pairs have UNVERIFIED run configuration (no argv in the jsonl headers) — **use them for C1 only, never for a policy attribution.**

**COUNTERFACTUAL (`ours`, zero-grant, §4 of the draft):** `173940` (100.0 s, 158 reports, 9,353 u, chord p50 49.6 / p90 141.6 u — the best), `182934` (114.8 s, 79, 22,586 u, 127.5/514.4), `100340` (719.0 s clean, 274, 43,177 u, 94.8/477.5), `182554` (26.2 s, 21, 6,433 u, **445.9/516.1**).

**Retail (`live`) is never an input** — it has no `ours` grant stream to counterfactual against.

**⚠ Print with every counterfactual result:** the substrate is fast-running (`v_player` p50 262–283 u/s against a declared 288) and click-free (0/5/21/0 clicks), so it is the regime where any lead policy is *least* harmful and where P0 sends ~0 grants and survives by doing nothing. **The instrument prices harm added; it cannot price harm removed.**

### 2.6 THE CALIBRATION GATE — must pass before any counterfactual number is printed

- **REALFIX-C0 · the radius derivation must land first.** `MATCH_RADIUS = 99.919968` has **zero occurrences anywhere in this tree**, no committed reimplementation of the `0x0046E870` LUT sqrt exists to re-derive it (the doc-level ~99.6 figures were corrected with round 5's write-up commit, but a number whose derivation is not committed anywhere is UNVERIFIED in-tree). **Land the exhaustive scan (nine instructions at `0x0046E870`, 256-dword LUT at `0x0093CAC8`) as a committed function with its own check, with gate 1's `89600.0f` → 299.332591 u as the positive control.** Until it lands, carry the nominal `100.0f` (`authsrv.py:2617-2619`) and label the constant UNVERIFIED. **And stop describing the proxy as having "zero free parameters"** — the 5 s window is a block-recycle rule, not a per-node match window. ✅ **MET 2026-08-21**: `grantsim.derive_match_radius()`/`derive_gate1_cut()` are the committed derivation, §C0 of `test_grantsim.py` is the check, and the constant is no longer UNVERIFIED in-tree.
- **REALFIX-C1 · simulator vs memory, glide-conditioned.** Publish the parked fraction beside every pair (53.0 / 58.6 / 83.1 / 8.5 / 3.8%) and the glide-conditioned p50 (27.55 / 23.54 / 24.53 / 20.68 / 14.62 u). **Set the bar from the two high-grant pairs only** (`152716`, `171153` — the regime the candidates create): accept `glide p50 ≤ 25.0 u` and `max ≤ 75.0 u` on those two, with the parked-dominated three reported and not gated. Do not gate on the unconditioned p50; it is diluted.
- **REALFIX-C2 · snap reproduction on as-sent streams.** **(a) STRUCTURAL ZEROS — `173940`, `182554`, `182934` must predict exactly 0.** This is the gate the separation-only scorer fails at 16/12/34 and it is the check that carries. **(b) TOTAL — pinned to a golden fixture, not a band.** Two implementations of the drafted spec gave 69 and 80 against 60 measured; a `[0.7,1.5]×` band drawn after seeing 1.15 is not a gate. Commit a fixture capture with an expected per-capture vector and assert equality. **(c) SEPARATION — `{182652, 195137}` must exceed `{145717, 195315}` by ≥ 3×.** Do **not** gate on the `145717`-vs-`195315` order: it inverts (predicted 1.69 > 1.39, measured 1.31 < 1.39). Print the inversion.
- **REALFIX-C3 · policy replay at message level.** `20260820T195137` carries 199 `grant_verdict` rows, all `(fired=true, reason="off")`, and 199 sent `0x0029`; `20260820T195315` carries 154 rows — **152 `locally-moving` + 2 `grant`** — and 2 sent `0x0029`. Accept exact reproduction, reason for reason. **⚠ This covers the CLICK arm only** (`195137` has 132 decoded `0x003D` and zero heading grants), i.e. only P0 and P6. **Extend it to the heading arm by importing the real `_heading_grant_ok` predicate** — `_grant_verdict`'s own docstring (`:3006-3011`) says it was made side-effect-free so an offline scorer could run the decision rather than a paraphrase that agrees with it by construction — **or stop calling C3 the policy gate.** ✅ **EXTENDED 2026-08-21**: `_heading_grant_ok` landed with `--zero-lead`, `lead_policy` imports and applies it, and `test_grantsim.py` §6b drives both its arms. **It is still not a message-level replay** — no capture holds a heading-arm `grant_verdict` row, because the flag has never been run — so §6b is hand-computed against a synthetic stream and says so, and **REALFIX-L1's first capture upgrades it** onto `195137`/`195315`'s footing. `replay_verdicts` already skips heading rows so that capture cannot redden the click arm on arrival. **Hardened after review, and the two holes are worth naming because both were on C3's own stated ground.** (i) §6b proved the predicate was *importable* and that *something* rate-limited the policy, but nothing proved `lead_policy` **called** it — replacing the call with an inline `fired = _since is None or _since >= 0.5` left the file green, i.e. the paraphrase-that-agrees-by-construction C3 exists to rule out was invisible. It is now locked by perturbing the server's own `GRANT_MIN_INTERVAL` and requiring the policy's grant instants to follow. (ii) The heading-row filter was dead source — no capture to filter — and deleting it changed nothing; it is now driven against a hand-built capture carrying one `arm="zero-lead"` row, one bare `heading-rate` row and one ordinary click row as the positive control. §6b's old "negative control" was also not one (it compared two counts the check above it already pinned) and now rebinds the verdict hook to always fire and requires all six.
- **REALFIX-C4 · nulls.** Match-test deletion must inflate ≥ 1.5× (measured 122 vs 69, 2.0×). Destination rotation must inflate monotonically (69/73/99/133 at k = 0/1/5/17). **Time shift is NOT a valid null on the total** — +0.35 s scores 60, dead on the measured total — so gate it per capture at +3.0 s only (`195137` 8→0 against a measured 8; `182652` 12→5 against 13) and **print the failure**. **And do not claim a geometry/cadence asymmetry**: at matched perturbation scale, rotate-1 is +5.8% and shift-−0.35 s is +10.1%.
- **REALFIX-C5 · sensitivity band.** window {2.5, 5, 10} s × radius {50, 100, 200} u × gate {250, 299.33, 400} u **× match test {ON, OFF}**. Totals over the first three axes span 51–80 against a base of 69; the fourth axis is the one the ranking is not invariant on (§6.4). **Accept: any ordering claim survives the full band including the match-test axis, or no ordering is printed.**

### 2.7 Floors — `toolkit/checks.py`

```python
led = checks.Ledger("grantsim", floor=<PIN FROM THE FIRST GREEN RUN>)
```

Enumerated expectation, ~44: fixtures + origin refusal (2) · C0 radius derivation + gate-1 positive control (2) · C1 two gated pairs × (p50, max) + three reported + n-floors (9) · C2 (a) 3 + (b) golden vector 1 + (c) 1 + inversion printed 1 (6) · C3 click arm 4 + heading arm 2 (6) · C4 match-null 1 + rotation 3 + per-capture shift 2 + matched-scale statement 1 (7) · C5 ranking invariance incl. match-test axis (4) · structural asserts — a ≤1.0 u grant produces no instant, arrival parks, reseed clears `armed_since`, `instants ≥ |{grants: |d| > 1}|`, M1 and M2 both non-empty on their own candidate (6) · refusals that must go red — pooled origins, unknown policy name, a ranking printed outside the invariance band (3). **`CLAUDE.md` is explicit: set the floor from a real green run, never from a guess, and never above what one produces. The 44 is an expectation. Do not ship the literal.**

### 2.8 TESTS.md entry (add in the same commit as the test — `test_srclint.py` §7 checks both directions)

> `toolkit/clientscan/test_grantsim.py` (**WOULD A DIFFERENT GRANT POLICY HAVE SNAPPED — AND THE ANSWER IS THAT THIS FILE CANNOT TELL YOU, ON PURPOSE.** The guard on `toolkit/clientscan/grantsim.py`, which replays a capture's own c2s `0x003D`/`0x003E`/`0x0047` through each candidate policy, drives a byte-exact rebuild of the client's `0x005FE950` bake, and asks the client's own question at the client's own two caller classes. Where `resyncscore` prices an ADDITIVE fix and `grantsuppress` prices the SUBTRACTION, this prices a SUBSTITUTION. **IT IS NOT A RANKER AND ITS TESTS REFUSE TO LET IT BECOME ONE.** §C5 sweeps the match test's PRESENCE alongside its radius, because that is the axis where the ranking inverts: with the match test on, leads 0 and 86 score identically on three of four counterfactual captures (0/0, 0/0, 2/2, 3/2) and only the already-refuted 766 u lead separates; with it off, 766 WINS on three of four (3 vs 10 on `20260820T182554`, 22 vs 23 on `182934`, 30 vs 48 on `20260814T100340`). Any ordering printed outside that band is a red check. **THE HEADLINE IS THE CALIBRATION.** §C2 requires reproducing the measured hard-jump census on eleven `ours` captures across five configurations — 60 measured — and, the check that separates this from its own first draft, **exactly zero** on the three captures that sent zero grants, where an earlier separation-only scorer predicted 16, 12 and 34 because `20260819T145717`'s real separation is p50 1,164 u, movetap-confirmed, with 7 jumps in 320 s. §C2(b) asserts against a golden per-capture vector rather than a ratio band, because two independent implementations of the same written spec gave 69 and 80 against that 60. **§C4 IS WHERE IT ADMITS WHAT IT CANNOT SEE:** deleting the match test doubles the prediction and rotating destinations inflates it monotonically, but shifting every grant by +0.35 s — destroying causality outright — scores 60, dead on the measured total, and at matched perturbation scale the file is MORE cadence-sensitive than geometry-sensitive (rotate-1 +5.8%, shift-−0.35 s +10.1%). **§C1 GATES ON THE GLIDE-CONDITIONED RESIDUAL**, from the two high-grant pairs only, because three of the five calibration pairs are 53–83% parked and their p50 of 0.00 measures the parking, not the model. **AND THE INPUT PLAN INVERTS THE OBVIOUS ONE:** the refuted-run captures carry real grants and real snaps and are therefore CALIBRATION substrate, while the COUNTERFACTUAL substrate is the zero-grant set — because `20260819T182652`, the capture that refuted `--client-endpoint`, yields **3.2 s and 259 u** of client track before its own first teleport contaminates everything after it, and because that zero-grant substrate is fast-running and click-free, which is the regime where every lead candidate is least harmful and where the shipped default survives by sending nothing at all.)

---

## 3. Pre-registered predictions

**Both denominators, per capture, `ours` only, written before any counterfactual stream is synthesized.** Substrate minutes: `173940` 1.667 span / 0.861 active (cov 51.7%); `182554` 0.437 / 0.437 (100%); `182934` 1.913 / 1.018 (53.2%); `100340` 11.98 span, **active coverage unmeasured — span only, and say so**. Baselines to beat: 0 / 0 / 0 jumps and 0 grants on the first three; 2 jumps and 2 grants on `100340`. **Any candidate predicting > 0 on the first three predicts harm the zero-grant control did not have.**

**REALFIX-D2 · P2-ZEROLEAD.** *Structural, and I state it as such rather than dressing it as a discovery:* under zero lead `q` at every class-A instant is a past reported position and at every class-B instant `q = D` is the reported position, so the match passes at distance 0 and **P2 predicts 0.00 snaps/min span and 0.00/min active on all four captures**, match-on. Match-off (the upper bracket) it predicts 10 / 23 / 48 on `182554` / `182934` / `100340` and 0 on `173940`, i.e. **23 / 23 / 4 per minute of span** — publish the bracket, not the arm. **The real prediction is REALFIX-M1, lag age: p90 ≤ 1.2 s on the seven fine-cadence captures and ≥ 1.785 s (one report interval) on `182554`, max ≤ 3.0 s everywhere, against the ~5 s chain bound.** ⇒ **FAILS if** any class-A snap is predicted on a capture whose report gap p90 < 1.0 s, **or if** M1 max reaches 5.0 s on any capture. (The drafted prediction of "≥ 3 snaps on `182554`" is **withdrawn before the run**: no setting of the match test satisfies it together with the other three per-capture claims, and the structural argument says it must be 0.)

> **OFFLINE RESULT against this prediction, 2026-08-21 — recorded beneath it, not folded into it.** The prediction above stands as written and is not edited. What the offline harness produced under the shipped rate limit: the first falsifier **survives** (the one counterfactual capture with report gap p90 < 1.0 s, `173940` at 0.600 s, predicts 0 class-A snaps); the second **does not fire, by 0.06 s** (M1 max 4.94 s on `20260814T100340`); and the non-falsifier bound **"max ≤ 3.0 s everywhere" is violated on two of four captures** (3.32 s on `173940`, 4.94 s on `100340`). The full table, and how much of that the rate limit itself moved, is in §4 item 2. Offline only — L1 measures the real thing.

**REALFIX-D3 · P3-SHORTLEAD (fixed 86 u).** Same 0.00/min on all four match-on, for the same gate-1 reason (86 ≪ 299.33). **The prediction is REALFIX-M2: arrival exposure 40–50% pooled and 10–20% on turn-conditioned intervals**, from the measured 45.7% / 14.8%. ⇒ **FAILS if** M2 < 20% or > 70%; **FAILS as a candidate** if M2 exceeds P2's (structurally 0%) by more than 50 points, which it is predicted to do — i.e. **P3 is pre-registered as strictly more exposed than P2, and the live A/B should therefore run P2 first.** The adaptive arm (`lead = min(766, 288 × gap_p50)`) is predicted to be indistinguishable from fixed on the seven fine-cadence captures and to raise M2 on `182554` (long gap ⇒ long lead ⇒ more drift), **which is the opposite of the intent it was drafted with** — record that before it runs.

**REALFIX-D1 · P1-RETAIL.** **NOT SCOREABLE by this harness** (it models no `0x002B`, so a BACK leg would run at 190.1 u/s while the harness bakes 288 — 1.51× in the operand of both tests). The geometric term only, with S fixed: cycle `766/(288 − v_player)` at the measured p50s = **31.0 / 29.8 / 159 / 95.8 s** ⇒ **1.93 / 2.01 / 0.38 / 0.63 per minute of span** on `173940` / `182934` / `182554` / `100340`, i.e. ≈ 3 / 4 / 0 / 7 snaps, magnitude p50 in the 500–770 u band (heading grants cap the step at 767.7 u, p90 757.5). Per minute of *active* time: 3.72 / 3.78 / 0.38 / (span only). ⇒ **FAILS if** it survives all of `173940` with zero predicted snaps, or if magnitude p50 lands outside 400–800 u. **⚠ carry the substrate bias with every one of these: this is the regime where P1 is least harmful, so a low score is not an acquittal.**

**REALFIX-D5 · P5-CLIENTPIN.** Predicted **0 snaps on every capture** (`0x002C` clears the record before writing). On the clean substrate at a 100.0 u trigger: **20–30 fires per minute of span**, ~40% of reports, `mints_hard` (yank ≥ 520 u) on **< 5%** of fires. ⇒ **FAILS if** `mints_hard` > 10% of fires, or fire rate > 40/min (a per-report teleport channel). **Its own committed pre-registration (1,998 fires, 25.4/min, 42.2% of reports, separations p50 183 / p90 514 / p99 1,415 / max 4,633 u, `authsrv.py:2628-2638`) is pooled over 66 captures across configurations including two refuted ones and its own text says "treat it as a magnitude, not a score" — quote it as a magnitude, never as a baseline.**

**REALFIX-D6 · P6-GRANTSUPPRESS (control).** Must reproduce its own measured A/B (1.39 vs 11.49/min span; 1.54 vs 11.49/min active) and C3's message-level identity. **On the clean substrate it must predict exactly 0 and change nothing; a control that moves here is a bug.**

**REALFIX-D0 · P0-DEFAULT (control).** 0 grants on `173940` and `182554` (0 clicks), ~5 on `182934`, ~21 on `100340` ⇒ **near-perfect survival on the substrate by doing nothing.** ⇒ **The drafted set-level falsifier "the whole set FAILS if P2 and P3 do not both beat P0 on survival" is WITHDRAWN: it fires by construction.** The replacement set-level falsifier: **the set fails if any candidate predicts a class-A snap on a zero-grant capture**, i.e. if a candidate manufactures harm where the control had none.

---

## 4. Run plan

**Offline first, and the offline pass answers a smaller question than it was drafted to answer.**

1. **Land REALFIX-C0** (the radius derivation + the three document corrections). Nothing downstream is quotable without it.
   ✅ **LANDED 2026-08-21** (`17a897a`+`b1e0840`): stdlib PE walk, both exhaustive scans land on the pinned boundaries bit-exact (`0x461C0000`/99.9199680, `0x47AF0000`/299.3325909, exactly-300.0-snaps), reproduced blind by an independent verifier from its own hand-decode of the nine instructions. `MATCH_RADIUS`/`GATE1_CUT` are asserted against their own derivation functions, so a drifted constant reddens.
2. **Land `grantsim.py` + `test_grantsim.py` and pass C1–C5.** Deliverable: the calibration table, the two exposure metrics, the bracket per capture, and an explicit refusal to rank. **Expected outcome: P2 and P3 both score 0 snaps match-on and separate only on M1/M2 — that is a successful run, not a failed one.**
   ✅ **LANDED 2026-08-21**, floor **61** (bare-machine 19), 1 loud skip (C3's heading arm, which waited on `_heading_grant_ok`; **that skip is gone as of the same day** — the predicate landed, `lead_policy` carries the shipped rate limit, §6b drives both its arms, and the floors moved to **68** / bare-machine **26**). Calibration: predicted 69 vs measured 60 (1.15×, per-capture vector IMPLEMENTATION-PINNED), the three structural zeros exact, C2(c) 6.51×, match-deletion null 1.77×, rotation monotone, `rank_or_refuse()` returns None over the full 54-cell band — **the 766 u lead is worst in 27 of 27 match-ON cells and wins in 27 of 27 match-OFF cells**, so no ordering is printed. The expected outcome half-held: P2/P3 separate on M1/M2 as designed, but P2 scores 2/3 marginal match-ON snaps on the two coarse-cadence captures — four of five inside the instrument's own error band, printed with marginality and gap columns, not gated (n=1 non-marginal, the client's own measured teleport). Survived a 33-mutation adversarial campaign: 26 red on first pass, 5 genuine survivors each given a check and proven red, 2 survivals by design with grounds recorded.

   **⚠ REALFIX-M1 PRICED AGAINST REALFIX-D2, 2026-08-21, and it was filed as an incidental until a review caught it.** The build record reported M1's move under the shipped rate limit as "printed, not pinned" — neutral wording for a number that is **P2's own pre-registered primary axis moving toward its own falsifier**. OBSERVED, offline, `ours`, P2 counterfactual, match-ON:

   | capture | report gap p90 | grants | class-A snaps | M1 p50 / p90 / **max** | M1 max, rate limit neutralised |
   |---|---|---|---|---|---|
   | `20260811T173940` | 0.600 s | 63 | 0 | 0.21 / 0.77 / **3.32 s** | 3.32 s |
   | `20260820T182934` | 1.818 s | 64 | 2 | 1.00 / 1.82 / **2.52 s** | 2.00 s |
   | `20260814T100340` | 1.785 s | 214 | 3 | 0.52 / 1.80 / **4.94 s** | 4.55 s |
   | `20260820T182554` | 1.820 s | 17 | 0 | 1.79 / 2.08 / **2.74 s** | 2.74 s |

   Against D2's own text: **"max ≤ 3.0 s everywhere" is offline-violated on two of four** (3.32 and 4.94). **"FAILS if M1 max reaches 5.0 s on any capture" does not fire — by 0.06 s.** The rate limit is responsible for part of that margin and not all of it: it moved `100340` from 4.55 to 4.94 and `182934` from 2.00 to 2.52, while `173940`'s 3.32 s is unchanged by it and was already over 3.0 before `_heading_grant_ok` existed. The mechanism is not a surprise — a 0.50 s floor grants less often, so the copy has longer to run between grants and the newest polyline node within the radius is older — but it is the axis D2 pre-registered, moving the wrong way, and it is 1.2% from the stated trigger. **The other D2 falsifier survives cleanly:** the only counterfactual capture with report-gap p90 < 1.0 s is `173940` at 0.600 s, and it predicts 0 class-A snaps. **Nothing in the tree prints or gates this comparison** — it is offline, on a substrate the instrument's own warning calls the regime where every lead policy is least harmful, and REALFIX-L1 measures the real thing. Carry it into L1 rather than resolving it here: if L1's M1-equivalent runs hot, the first dial is `GRANT_MIN_INTERVAL`, and lowering it trades cadence cost against lag age on a curve this table gives two points of.
3. **Price P5 with the existing `resyncscore`** on its yank column (no new code).
4. **Do not build P4. Do not run P1 before the lead family.**

**THE ONE LIVE A/B — REALFIX-L1, owner-driven.** `--zero-lead` (P2, no stop grant, no `turned` gate) against the shipped default, on one map, one session, arms alternated at fixed intervals, **`movetap.py` running throughout** so the run is two-sided.

✅ **THE ARM IS BUILT AND RUNNABLE, 2026-08-21.** `python toolkit/authsrv/authsrv.py --zero-lead …`; the prediction below is printed verbatim at startup so it cannot be rationalised afterwards — **and as of the review pass that startup banner is pinned by a test**, because deleting its retraction and its three numeric bounds left the whole suite green. It REFUSES to combine with `--heading-grant`, `--client-endpoint` **and `--stop-echo`** — every other arm that answers the player's own movement with a player `0x0029`, all three refuted, all three on the one shared grant clock — and allows `--grant-suppress`, `--resync` and `--click-sweep` with a printed note each. **`--stop-echo` was missing from that list for a day** and `--zero-lead --stop-echo` was accepted silently, which is the exact combination §1's P2 block forbids in capitals; the refusal had been keyed on "answers the same `0x003D`" and `--stop-echo` answers `0x0047`. The rate limit is `_heading_grant_ok` — rule 2 only, at `GRANT_MIN_INTERVAL = 0.5 s`, sharing the server's one grant clock — and a refused heading grant is DROPPED, never held. **A report the position-trust guard REFUSES is still granted verbatim, and the SYNC model follows it**: the client says it is standing there, so the point is on its own history polyline whatever we believe, and granting `state["pos"]` instead would grant a point the player has already left. That is the design, it is now written at the block and driven both directions, and **REALFIX-L1 must expect a movetap separation spike there and read it as the design rather than a defect.** **The FIRST run happened 2026-08-21, the same day** — harness-scripted, click-free keyboard with backpedal legs, identical input both arms, captures `20260821T081744` (P0) / `20260821T082631` (P2), movetap both sides: **66 grants → 0 hard rows ON THE OBSERVED INTERVALS, separation p50 4,402 → 267 u (16×)** — ⚠ **OPERATOR-REFUTED same day as a P2 acquittal: the operator saw arm B warp near the bridge** (FINDINGS §"L1 FIRST RUN IS VOID"); the run's blind windows (32% active coverage) and its geometry-vs-bug confound void every per-event claim, the separation contrast stands, its separation bounds missed-as-written at the report-chord scale the failure signature predicted (1.8 s keyboard cadence vs the 0.3 s the bound assumed, ⚠ plus a ~1 s clock-offset systematic worth up to ~288 u per pairing), and **the P0 prediction failed by protocol design — a click-free walk starves the default build's only grant arm to zero**, so this run prices the cost of silence (the parked copy), not warp removal. FINDINGS §"2026-08-21 — REALFIX-L1 FIRST RUN". ⚠ **THAT SECOND RUN HAPPENED, 2026-08-21, and it did NOT go the way this block expected — REALFIX-L5 + L6, FINDINGS.** Four arms plus a fifth: the shipped default warps at **15.66 and 15.17/min** (a 1.03× bracket), `--zero-lead` is **NOT significant** in this regime (RR 0.703, CI covering 1.000; bin-permutation p = 0.26), and `--plane-carry` carries **no information at all** because the client never left plane 0. **The regime is a DIFFERENT MECHANISM** — grant DISTANCE, not the plane word: click grants land 1,400–2,600 u away, 97–100% of them over the 299.33 u gate-1 cut, and no plane boundary is involved. The composite's zero is **not a fix** (0 of 96 grants could displace the player) and is **not distinguishable from bare `--grant-suppress`** (p = 0.15). **Decisive, but for the opposite conclusion: this regime needs a CLICK-ARM lever, and F1 is not one.**

- **Traffic conditions, from the record's own lessons:** **click-free** (the `turned` gate and the substrate bias both hinge on it), **keyboard held through the whole waiting period** (`FINDINGS:1785-1789` — "any future warp run must keep the keyboard moving through the whole waiting period, or the instrument goes blind exactly when the phenomenon fires"; the default build is blind for 220 of 320 s), and **including a deliberate sustained backpedal leg**, because backpedalling is where `S − v_player` is largest (retail's own backpedal rate is 189.8 u/s = 0.659 × 288, `live`, n = 32) and it is the regime no capture in the vault covers — a substrate gap this leg discharges, named **REALFIX-U4**.
- **PRE-REGISTERED PREDICTION.** P0 arm: 3–6 hard jumps per minute of **active** time (bracketing the measured 4.19) and 100–170 u displaced per active second (bracketing 137.8). **P2 arm: ≤ 1.0/min active and ≤ 40 u per active second.** Separation (movetap-measured, SYNC vs the client's report): P0 arm p50 ≥ 800 u; **P2 arm p50 ≤ 150 u and p90 ≤ 520 u.**
- **PRE-REGISTERED FAILURE SIGNATURE.** If P2 fails, it must fail as **frequent small displacements at the report-chord scale** (33–70 u fine cadence, ~500 u on a keyboard hold), **not** as a rare large teleport. **A P2 arm whose displacement p50 exceeds 520 u refutes the "lag is on the polyline" reading** and sends the arc back to §2.2.
- **WHAT WOULD REFUTE THE INVARIANT ITSELF:** a P2-arm snap recorded while movetap shows separation < 299.33 u and the copy behind the player on ground already walked. That is gate 2, gate 3, or the gate-free `ResyncAllAsync` — and it is the outcome that would make every policy in this document beside the point.
- **RIDE-ALONG, and it is the highest-value item in the arc:** while the client is up, set the breakpoint at `0x0060580D` / `0x00605820` and log `rec.clientControlled` at `[agentMgr+0x1CC+0x20] + id*0x1C` alongside separation. It says which gate fires, whether gate 2 is ever reached, and it can refute the `clientControlled` mechanism outright. **Named in FINDINGS twice, unrun for three rounds.**

**Ladder after L1:** P2 green ⇒ ship it and P3 is unnecessary. P2 green on movement but costly on the non-movement axis (aggro/interaction, because the copy's velocity is zeroed) ⇒ P3 at 86 u is the next rung, carrying its 46% arrival exposure. P2 red ⇒ the invariant's O1 asymmetry is wrong and the arc restarts at §2.2, not at a new policy.

---

---

## 5. Open questions, ranked

**REALFIX-Q1 · Which gate actually fires, and is the `clientControlled` fence real?**
Named in FINDINGS twice, unrun for three rounds, and it is the difference between "the
mechanism predicts 13.8/min" and "the mechanism predicts 176/min and something throttles
it". It can refute the fence mechanism outright and it would give gate 2 its first
observed firing (or confirm n = 0).
**Cheapest: a runtime breakpoint at `0x0060580D` and `0x00605820` during a live desync,
logging `rec.clientControlled` at `[agentMgr+0x1CC+0x20] + id*0x1C` alongside separation.
Ride it along with REALFIX-L1 — the client is already up.**

**REALFIX-Q2 · Does zero lead hold at a client?** Everything in §5–6 says P2 is the only
family that satisfies O1 and O3 with no assumption about the player's speed, and the
offline harness proves it only by tautology (§6.5). Its two named assumptions — the
`now+1` arrival dispatches (RECONSTRUCTION for the 1 ms case), and `RTT × v_player < 100 u`
(UNVERIFIED off loopback) — are both live-only.
**Cheapest: REALFIX-L1 itself, with its pre-registered failure signature (frequent small
displacements at the report-chord scale, p50 ≤ 520 u).**

**REALFIX-Q3 · Do history nodes expire, and is lag strictly safer than lead?** The whole
invariant rests on the asymmetry, and nothing measures it. `seg_match` applies no time
filter, but the 250 ms constant at `0x00604F09` sits in a different function with an
UNVERIFIED role, and the 5000 ms recycle is per *block*, not per node, so the true chain
span is looser and unmeasured.
**Cheapest (static, ~30 min, no client): `codescan --xrefs` on the function containing
`0x00604F09` to establish whether `0x006055E0` or `0x00605840` reach it, then read
`0x00604BB0`/`0x00604C03`'s allocator and sweep end to end. Positive control required —
make the same xref filter find a call site you already know, e.g. `0x00605AF0`'s single
caller.**

**REALFIX-Q4 · Which agent array does gate 3 enumerate?** It decides whether a
server-side crowding guard is even expressible: world[1] means the relevant crowding is
what the *player* sees, world[0] what *we* believe. Nobody has read it, and a second
unknown sits in the same function — the predicate is applied at tens of units by the
sidestep site and at `pathArray[0]` distance by gate 3, and whether its internals are
scale-sensitive (the 60° cone and the 0.0005 s cut both plausibly are) is UNVERIFIED.
**Cheapest (static, ~45 min): read `0x005FEF70` end to end for (i) the neighbour loop's
array base and (ii) how `|to − from|` is consumed.**

✦ **PARTLY ANSWERED 2026-08-21 by REALFIX-L6** — the residue has a shape now, though not yet a site. With bare `--grant-suppress`, **2 grants produced 3 warps**, and every warp landed on a GRANTED destination (0.0 / 27.9 / 114.2 u; control: 200 random track points, best 189 u, 0 of 200 better) **6.9, 8.8 and 35.3 s after the grant** — grant 1 firing twice, and warp 1 landing while the player was keyboarding continuously. **The granted destination is not consumed; it lingers and re-applies.** Which of the sites below re-applies it is still UNVERIFIED and needs a movetap on `+0x48`, which L6 did not carry.

**REALFIX-Q5 · Which of the 13 SetPosition sites can fire with no server message at
all?** This is the question `--grant-suppress` needs answered: round 4 measured 1.39
hard rows/min with 2 grants and never explained the residue. `0x00604A50`, `0x00606394`,
`0x005FF74B` and `0x006028FF` are unexamined, and `0x005FCAA0`'s gate-free reseed is
UNVERIFIED as a live route and is a candidate for the unexplained snaps 12–59 s after the
last grant.
**Cheapest (static, ~30–45 min): walk `--xrefs` up from each unexamined site until it
reaches either a receive-handler VA in the 18-row table at `0x00A52D70` or a non-message
entry point; attribute by module with `asserts.py`. State the indirect-call caveat —
`--xrefs` finds direct branches and stored VAs only.**

**REALFIX-Q6 · Does `0x002B`'s float track the movement family, or is it a buff/snare
channel?** Both arms are simultaneously present (71% modal per family, 214 distinct
floats corpus-wide), no wire rule can arbitrate, and P1's `FAMILY_RATE` table is
unshippable until it is settled. It is also the term the tree blames for
`--client-endpoint`'s failure.
**Cheapest, unchanged from `FINDINGS:1688`: `movetap.py` on `agent+0x5C`/`+0x60` during
deliberate sustained backpedalling, wire logged alongside. Fold it into REALFIX-L1's
backpedal leg — the instrument is already running.**

**REALFIX-Q7 · Is retail's clipped boundary our navmesh?** D2 is the one retail term we
cannot compute, and its identification is RECONSTRUCTION whose stated evidence was
withdrawn this round.
**Cheapest (~2 h incl. a client run, design given): one loopback capture on a map whose
navmesh we have, run TEST E and TEST F against our own `clip_to_walkable` output
(`origin=ours`, scored separately, never pooled). Reproducing ratio ≈ 0.12 and angle
≈ 79° says the mechanism is the same; collinear at 0° says our clip is a leash and
retail's is geometry.**

**REALFIX-Q8 · The three undocumented movetap pairs' run configuration.** `150336`/`150349`,
`150522`/`150537` and **`152716`/`152723`** are all two-sided and none is named in any
study document; `152716` is the `--heading-grant` decisive trial and is currently
recorded as wire-only.
**Cheapest (~20 min, no client): the gamesrv jsonl headers carry no argv, so recover the
configuration from behaviour — the presence and destination geometry of heading-triggered
`0x0029` distinguishes DEFAULT from `--heading-grant` from `--client-endpoint` outright.
Then record the argv in the capture header going forward, so the next arc does not pay
this again.**

**REALFIX-Q9 · The five of twelve corpus teleports landing nowhere near a granted point,
and the 9-of-26 unadjudicated impossible-step rows.** Untouched since round 2, and they
are the population any "the grant stream is the cause" claim has to survive.
**Cheapest: re-run the landing-geometry test with the caller-aware model from §2.3
rather than the grant-proximity heuristic — a class-B arrival instant explains a
teleport with no nearby grant, which the old test could not represent.**

**REALFIX-Q10 · Retail's blind budget.** 268 of 3,098 player grants (8.7%) sit outside
any watched interval and the detector demonstrably misses the corpus's one real retail
teleport. Nothing in the corpus buys this back.
**Cheapest: not a measurement but a procedure — every future warp run keeps the keyboard
moving through the whole waiting period. Already folded into REALFIX-L1.**

---

## 6. REALFIX-L2 — protocol and pre-registration (2026-08-21)

**What this design is built on — REALFIX-W1..W5, five facts nobody in L1 measured, each of which changes what a leg *is*. They are the reason the protocol below can bound a cell instead of hoping for one.

| # | OBSERVED (`ours`, both L1 captures) | consequence |
|---|---|---|
| **W1** | **Every key-down emits a `0x003D` at the exact previous stop position** — 6 of 6 stops in arm B, 4 of 4 in arm A, `moved 0.0 u`, at the leg's own key-down instant (arm B: stop `t=71.966` → HEAD `t=73.735` = 12:27:45.0 = L3's scripted key-down). | Every leg opens with a **zero-distance grant**, so **separation is 0 at every leg start** — corroborated independently in movetap (`sep 0.0` in every pre-leg sample). Legs are therefore *independent trials*, and the separation at any later instant is a controlled quantity, not a nuisance. |
| **W2** | **`0x003D` in free travel is DISTANCE-triggered at ~515 u, not time-triggered.** gap 1.80 s ⇒ chord p50 **513.8 u** (n=26 A + 22 B, max 516.7); gap 2.74 s ⇒ chord p50 **513.4 u** (n=11 A + 7 B, max 514.7). Implied speeds **285.4 u/s** (W) and **190.1 u/s** (S). | Under zero lead the copy sits exactly one chord behind, so **separation saturates at ≈515 u regardless of speed**. This is why P2's sep p90 (523.0) *equals* the chord p90 (514.7) — the L1 write-up called that a coincidence of cadence; it is the trigger rule. It also fixes the **test-instant budget**: 1 grant per 515 u of free travel, full stop. |
| **W3** | **Wall contact collapses the cadence to the 0.50 s floor with chords 30–155 u** (n=57 A, 28 B; implied 100–250 u/s). | **Sustained wall contact is self-protecting under `--zero-lead`**: chord 30–155 u ⇒ separation 30–155 u ⇒ **below the 299.3326 gate-1 cut** ⇒ no snap is reachable. **25 of arm B's 66 grants echoed contact reports and not one of them could have snapped.** ⇒ **L1 never tested candidate B at all.** Candidate B needs a deflection *while* sep > 299.33, which exists only in the **first one or two grants after a fresh contact**, before the cadence rises. Both lanes read the corner-cutting null as a refutation; it is a coverage gap. |
| **W4** | **yaw is exactly calibrated: 1 drag px = −0.0800° of travel heading.** `yaw:250` → **−20.000°**, `yaw:-250` → **+20.000°**, `yaw:200` → **−16.000°** — both arms, to 3 dp, n=6. Travel heading is **exactly constant within a leg**: max deviation **0.000°** across all 16 L1 legs. Backpedal is heading+180.000°. | The harness can **aim by dead reckoning**. Nothing in this protocol needs a world-anchored click. It also kills candidate B's smooth-curvature route outright: measured |dψ/dt| p90 = 0.007 rad/s against the ~0.444 rad/s a 2.5 s node interval needs to bow 100 u. **The only curvature this grammar can produce is a collision deflection**, which is why every B-cell below is a wall cell. |
| **W5** | **Spawn facing is NOT reproducible**: −66.355° (A) vs −65.269° (B) from an identical script — **1.086° apart**. Spawn *position* is exact (9826.0, 8077.0 both arms). | The only aiming residual. Over the longest leg here (1,855 u) it is ±35 u against corridor half-widths of 125–165 u. **A yield risk, not an aiming blocker** — and the protocol re-anchors on geometry rather than carrying it. |

**Map facts, from our own navmesh** (`PathingMap.load(113021)`, map 148: 58 planes, 6,120 trapezoids — OBSERVED from the pathing chunk):

- **Plane 18 is a rectangle**: x ∈ [10860.0, 11123.0], y ∈ [4532.0, 5579.0] — **263 u wide, 1,047 u long, 4 trapezoids**. It is the bridge.
- Its middle band (y 4790–5316) **overlaps plane 0** (bridge over ground); its two end bands do not. This is exactly the case `pathmap.plane_at` is known to get wrong (9 of its 198, all "client says 12, we find 0").
- **Both L1 arms reported x = 10860.0 and x = 11123.0 EXACTLY**, for many consecutive samples. The parapets pin x to the bit — the protocol uses that as its position anchor.
- **The client-visible 0↔18 boundaries are y = 5579.0 and y = 4532.0** (OBSERVED mesh edges; RECONSTRUCTION for the exact line, bracketed by the client's own reports at y 5744/5279 and 4630/4326). The client reports **plane 18 continuously across the overlap band** — it does not flip inside it.
- Approach channels: north apron walkable x ≈ 10875–11125 for y 5579–5700, opening west above y 5700; south apron x ≈ 10850–11150 at y 4400–4530, opening below y 4360. Open plane-0 field: x 10700–12300, y ~2700–4300, with clear straight runs ≥ 3,000 u.

---

### 0. RULE ZERO — the arm-A-twin discrimination rule, applied *before* the protocol

The skeptic proved that **every auxiliary signature both lanes offered also fires in arm A**, which sends zero grants: `clientControlled` 1→0 fires 3×; sync-vs-async plane mismatch fires on 121 of 2,695 samples; `sep > 299.33` fires on 2,695 of 2,695; `gate1 == "above"` on 2,574. So:

> **REALFIX-E, the ONLY admissible event definition.** An **event** is an adjacent-sample step of the **`async_at` (world-1, rendered) track ≥ 150 u**, in a sample pair whose interval is ≤ 0.25 s.
> Threshold grounds: arm A's rendered track never exceeds **33.4 u** over 2,694 intervals; the smallest observed event is **322.4 u**. 150 u sits 4.5× above the control's maximum and 2.1× below the smallest positive.
> **`sep`, `gate1`, `fence_raw`, the plane words and the wire hard bar are NOT identifiers and may not be used to call an event.** They are recorded as *covariates* and reported beside every event and every non-event.

Confirmatory covariates, recorded but never decisive: displacement · commanded heading (expect < 0), distance from the contemporaneous `sync_at` (expect < 50 u), `fence_raw` 1→0 in the same sample, `async_ptr`/`async_id`/`async_count`/`async_world` single-valued across the file (the artifact test that must pass before any event is believed), `async_branch` on both sides of the step, and persistence ≥ 10 samples (the torn-read test).

**Wire-side leg deficit** (rendered path length ÷ v·duration) is a *screening* aid only. It cannot identify: arm A's L4 scores 0.13 with zero events (wall), arm B's L2 scores 0.23 with one. The operator is right that a stall identifies nothing.

---

### 1. THE PROTOCOL

#### 1.1 Invocation

```
python toolkit/harness/session.py --until map --keep-open \
    --game-args="--explorable --no-enemy[ --zero-lead]" \
    --walk "<plan>"
```

`movetap.py` attached **before the client is launched**, not after — arm B lost 23.3 s of wire including plane flip #1 and 7 grants to a late attach. Request a rate the reader can actually meet (`calibrate()` measured ~13 Hz on this machine against a default request of 50): **`--hz 20`**, so the file-level floor is meetable and the per-leg rule below does the real work.

#### 1.2 Leg grammar and its three hard rules

1. **Every leg ≤ 8.0 s, and every leg bounded by a stop.** `walk_legs` already inserts `settle=1.5 s` between steps; the plan adds an explicit `wait:2` before each *measured* leg, so the copy (which needs 515/285.4 = **1.81 s** to converge) is provably co-located at the leg's key-down.
2. **No yaw inside a measured leg.** Yaw is a discrete step between legs (W4); a leg is one constant heading by construction.
3. **The shuttle turns around with `S`, not with yaw.** Facing stays fixed at −90.000° for the whole shuttle: `W` runs south at 285.4 u/s, `S` runs north at 190.1 u/s. This removes the 180° turnaround (2,250 drag px) from the critical path entirely.

**Leg-boundary anchoring is free from the wire (REALFIX-T2b).** A key-up emits `0x0047`; the next key-down emits `0x003D` **at the identical position** (W1). That pair is the leg boundary read on the *wire's own clock*, so the harness's whole-second leg stamps stop being load-bearing for leg assignment. ⚠ **Only when a stop was emitted**: arm B produced **6 stops for 8 legs**, arm A **4 for 8** — a character not moving at key-up emits nothing. **Pre-register: a leg with no `0x0047` is FLAGGED, not scored as stop-bounded**, and its boundary falls back to the (now float, see §2) leg stamp.

#### 1.3 The six cells

The 2×2 the brief asks for is `{angled wall-slide, straight} × {plane-crossing, flat open ground}`, plus the perpendicular crossing. Two amendments, both forced by measurement:

- **The deck is 263 u wide.** An *oblique straight* crossing is geometrically impossible — a 40°-off-normal line covers 313 u of y per 263 u of x and hits a parapet before the copy's mismatch window (~515 u of travel) closes. So the straight-crossing cell **is** the perpendicular crossing; there is no second angle to run. The dose axis moves from *angle* to *separation at the rewriting grant*, which W1+W2 make exactly controllable.
- **The brief's "angled wall-slide on flat open ground" is split.** `X2a` runs the slide **on the deck without crossing** — same location, same wall class, no plane rewrite — which is simultaneously candidate B's clean cell *and* the skeptic's empty confound cell. `X2b` is the brief's literal open-ground version, kept, but its wall geometry is **UNVERIFIED** (our boundary-segment fit disagrees with the raster in the open field) and it is scored from the observed contact, not the intended one.

| id | geometry | plane rewrite | wall deflection | sep at the instant | **A: plane echo** | **B: corner-cutting** | **location confound** |
|---|---|---|---|---|---|---|---|
| **REALFIX-X1** | east/west parapet slide **across** the deck, 40° incidence | **yes** | **yes, ~40°** | ~515 u | **WARP** | **WARP** | warp |
| **REALFIX-X2a** | parapet slide **inside** the deck, never crossing y=5579/4532 | no | **yes, ~40°** | ~515 u | none | **WARP** | warp |
| **REALFIX-X2b** | open-field oblique slide, plane 0 only | no | **yes, 30–50°** | ~515 u | none | **WARP** | none |
| **REALFIX-X3** | deck centreline, perpendicular crossing, **hot** | **yes** | no | ~515 u | **WARP** | none | warp |
| **REALFIX-X4** | open field, straight, no wall, no crossing | no | no | ~515 u | none | none | none |
| **REALFIX-X5** | crossing with a **stop 230 u past the boundary**, so the rewriting grant lands **below the cut** | **yes** | no | ~230 u | none *(gate 1 passes)* | none | warp |
| **REALFIX-X6** | on the deck, above cut, **no** rewrite (harvested from X3's own legs) | no | no | ~515 u | none | none | **warp** |

**The crux is X2a vs X3: exactly one of A and B predicts each.** X6 is the cell the skeptic proved was empty in L1 (`in-corridor, above-cut, no plane rewrite`, n = 0) and it is harvested from the *same legs* as X3 — same location, same run, same separation, differing only in whether the grant rewrote the plane word. X5 is not a mechanism cell at all: it is **REALFIX.md:235's own invariant falsifier**, run deliberately for the first time.

#### 1.4 The plan, leg by leg

**THE ASSEMBLED PLAN, corrected 2026-08-21 and marched clean** (W5 = +0.75, W4 = -0.080152; zero unintended blocked legs; X1 contacts the parapet at 345-760 u and X2a at 282-286 u, matching this section own predictions of 347 and 285 u). Two recorded deviations: **X4 is harvested from the transit and shuttle key-downs rather than staged** (PART 6 below says those already yield 8 open-straight instants; a dedicated anchor costs ~2,100 u of transit each way plus two 180-degree turnarounds), and **the wall cells back out with S rather than turning around**, as the shuttle does. X2a back-out is 1.5 s so no rep re-enters plane 18.

```
yaw:801 wait:2 W:7.5 wait:2 W:1.62 yaw:331 wait:2 W:6.5 wait:2 S:9.8 wait:2 W:6.5 wait:2 S:9.8 wait:2 W:6.5 wait:2 S:9.8 wait:2 W:0.8 wait:2 S:1.2 wait:2 W:0.8 wait:2 S:1.2 wait:2 W:0.8 wait:2 S:1.2 yaw:953 wait:2 W:0.32 yaw:-1452 wait:2 W:6 wait:2 S:4 wait:2 W:6 wait:2 S:4 wait:2 W:6 wait:2 S:4 yaw:111 wait:2 W:2.08 yaw:-111 wait:2 W:4.5 wait:2 S:1.5 wait:2 W:4.5 wait:2 S:1.5 wait:2 W:4.5 wait:2 S:1.5
```


Facing convention: degrees are `atan2(uy, ux)` of the *travel* direction, as the client reports it in `values[3]`. ✅ **`yaw:N` changes it by `−0.0800·N` degrees (W4) is CONFIRMED** by a dedicated sweep, 2026-08-21: **−0.080152 °/px, n = 9 over ±2,000 px, residual max 0.55°** (FINDINGS §"THE YAW CALIBRATION"). ⚠ An earlier line here called W4 REFUTED from readings taken off the L2 capture; that is **WITHDRAWN** — `S` legs reverse the travel bearing 180° and wall-slid legs report the wall's bearing, and neither was controlled for. ⚠ **`REALFIX-W5` IS the broken constant: the spawn facing is +0.75° ± 0.15° (two independent runs), not −65.80°** — a 66.5° error, and the whole reason L2 walked northeast into a wall. The L2 post-mortem's "+44.31°" is **also wrong**: that was the character sliding along a wall (cadence 1.80→0.50 s, speed 94 u/s, bearing swinging +77→+44 and holding). From spawn at +0.75°, the bearing to the bridge's north apron is −63.42° = **`yaw:801`**. **A leg that runs under 80% of `v·duration`, or bends more than 20° mid-leg, is a WALL and is not a datum.**

**PART 0 — transit (2 legs, both stop-bounded).** From spawn (9826.0, 8077.0) at facing ≈ −65.8° ± 1.1°:

```
yaw:-30   W:5.0   wait:2   W:4.2   wait:2
```
Bearing to the north-apron anchor (10990, 5750) is **−63.425°**; `yaw:-30` = +2.4°. Marched clear on our mesh; ends (11001, 5729), i.e. **within 11 u of the anchor in x**. Two legs rather than one 9.2 s leg keeps rule 1.

**PART 1 — the shuttle (facing −90.000°, ×3 cycles).** `yaw:-330` from the transit bearing puts facing at exactly −90.0°.

```
[ wait:2  W:6.5  wait:2  S:9.8 ] × 3
```

Simulated instants (`sim.py`, using W1/W2's report rule and the mesh's plane function):

| leg | reports at (u) | instants produced |
|---|---|---|
| `W:6.5` (1,855 u south) | 0, 515, 1030, 1545 | key-down (sep 0, below) · **X6** @ y5234 · **X3** @ y4720 rewrite 0→18 · **X3** @ y4204 rewrite 18→0 |
| `S:9.8` (1,863 u north) | 0, 515, 1030, 1545 | key-down (sep 309, above, X4) · **X6** @ y4411 · **X6** @ y4925 · **X3** @ y5441 rewrite 0→18 |

**Yield over 3 cycles: 11 × X3 (rewrite, above cut), 9 × X6 (in-corridor, above cut, no rewrite), 3 × X4.** Every X3 and X6 instant lands at sep 514–516 u. Walking cost: **49 s** plus 12 s of waits.

**PART 2 — X5, the cold cell (6 hops around y = 5579).** From the north anchor, facing −90.0°:

```
[ wait:2  W:0.80  wait:2  S:1.20 ] × 3
```
`W:0.80` = 228 u, `S:1.20` = 228 u. Each hop's key-down report sits **228 u** from the previous grant, on the far side of the boundary — a plane rewrite at **sep 228 u, below the 299.3326 cut**, six times. (Simulated key-down sep 228.1–228.3 u.) Walking cost: **6 s**.
⚠ Margin: 228 u vs a 299.33 cut is 71 u of headroom against a hold-timing error measured at 0.0003–0.0009 s of 25 s. Adequate. Do **not** stretch the hop toward 1.0 s.

**PART 3 — X3 done straight, and X6's matched partner, are already in Part 1.** No extra legs.

**PART 4 — X1 and X2a (the slide cells), facing set by yaw, 3 reps each.**

- **X1**, from (10900, 5750), facing **−50.0°**: crosses y=5579 at 223 u (t=0.78 s), contacts the **east parapet x = 11123.0** at 347 u (t=1.22 s) at a **40° incidence**, then slides south at cos40°·285.4 = **219 u/s** to y=4532. `W:6.0`. Reports at 0, 515, 1030, 1545 → the rewrite lands at 515 u *and* the 40° deflection at 347 u is inside that same interval. **Both mechanisms armed on the same grant.** Positive control: this is the L1 configuration that produced E1/E2 (arm B was pinned at x = 11123.0 immediately before E1).
- **X2a**, from (10940, 5560) — 19 u inside the deck's north edge — facing **−50.0°**: contacts x = 11123.0 at 285 u, slides 810 u south, **stops before y = 4532**. `W:4.5` (1,284 u). Reports at 0, 515, 1030 → **2 in-slide instants**, both above cut, **no rewrite**. ×3 = 6.
- Repositioning between reps: `S` back north at the same facing, no yaw.

**PART 5 — X2b (the brief's open-ground slide), 3 reps, marked provisional.** From (11200, 1980) at facing **+10.0°** into the SE wall (fitted bearing +50.2° over y 1900–2150, our mesh): contact at ~592 u, **40° incidence**. `W:6.0`.
⚠ **This is the one cell our mesh cannot pin.** The boundary-segment fit disagrees with the raster in the open field, and the wall jogs at y≈2200. **X2b is scored from the observed report pattern only**, and if no rep yields a valid contact it is reported **NOT MEASURED**, never as a null.

**PART 6 — X4 (open straight), 3 reps.** From (11400, 3900) facing **+200.0°**, `W:7.0` — 1,998 u, marched clear on our mesh. Plus the 8 X4 instants Parts 0 and 1 already produce.

**Total walking ≈ 145 s per arm, plus ~90 s of waits and yaws — under 5 minutes of plan per session.**

#### 1.5 Cell assignment is from the OBSERVED path, never the intended one

Pre-registered, before the run:

- A rep is **X-wall** iff its report stream shows a **≥ 25° deflection** between consecutive chords, *or* the client reports x = 10860.0 / 11123.0 exactly.
- A wall rep is a **valid B instant** only if the report gaps through the slide stay **≥ 1.5 s** (⇒ the slide kept speed ⇒ separation stayed at chord scale). **If the gaps collapse to 0.50 s the rep is RECLASSIFIED as hard contact** — a below-cut instant, not a B test (W3). This is the rule that stops L1's mistake repeating.
- A rep intended as **X3/X6 (no wall)** that reports x = 10860.0 or 11123.0 is **reclassified to X1/X2a**, not discarded.
- Each instant's `sep` is read from **movetap's own `sep`** (`sync_at` vs `async_at`, both from client memory, **no clock alignment of any kind**), never from `movesync.pair`.

#### 1.6 Arms, and their order

1. **Arm P0 (`--explorable`, no `--zero-lead`) FIRST, same plan.** Not as a mechanism control — it sends 0 grants, never enters `agtrack_dispatch`, and **cannot express the signature**. It is the **geometry calibration**: no snaps means no trajectory divergence, so its report stream is the ground truth for where the walls actually are and which reps landed in which cell. L1 ran this arm last and got nothing from it; run first, it pays for itself.
2. **Arm P2 (`+ --zero-lead`), same plan.** The treatment.
3. **Arm F1 (`+ --zero-lead --plane-carry`), same plan** — only if P2 produced ≥ 1 event in X1 or X3. §3.

**Not attempted here, and it stays with the owner**: the round-4 trigger (hold `S` + spam-click, 11.49 hard rows/min under the default build). A held key with simultaneous clicks is not expressible — `walk_legs` runs steps strictly sequentially (`session.py:1029-1030`) — and world-anchored clicking is the owner's side of the boundary. That was REALFIX-L1's second run; it RAN on 2026-08-21 as **REALFIX-L5/L6** (owner-driven, as this paragraph requires), and its result is in FINDINGS — the regime turns out to be a different mechanism and F1 has no purchase on it.

**Nothing else in this protocol needs aiming.** All six cells are harness-scriptable: key holds plus calibrated yaw drags (W4), no world-anchored clicks, no model-appearance verdicts. The single unscriptable quantity is the **absolute spawn facing** (W5, ±1.1°), and §1.5 absorbs it by scoring from observation.

---

### 2. CLOCK ANCHOR

#### 2.1 The whole 1.00 s is on one side, and it is one line

`offset_from_stamps` returns `max(walls), max−min`; measured spread **0.999920 s** (arm A) and **0.999777 s** (arm B). The cause is entirely `authsrv.py:8396`:

```python
kw["wall"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())   # truncated to the second
```

Each row therefore gives `floor(unix) − t = true_offset − frac`, `frac ∈ [0,1)`. **movetap has no such problem** — it stamps `s["t"] = round(time.time(), 4)` (`movetap.py:2795`), full resolution.

> **REALFIX-T1 — the delta.** One line beside it in `Recorder.event`:
> ```python
> kw["wall_unix"] = time.time()
> ```
> `time.get_clock_info('time')` on this machine reports `GetSystemTimePreciseAsFileTime()`, resolution **1e-07 s** (measured, this box). The offset becomes **per row** — `wall_unix − t` — so `perf_counter`↔system-clock drift over a 200 s run cancels as well, and the file's own residual `max(wall_unix−t) − min(wall_unix−t)` is a printable diagnostic rather than an assumption.
>
> **Loader side:** `offset_from_stamps` prefers `wall_unix` when present, falls back to the truncated max-estimator, and **prints which it used and the residual**. Never silently mix (`movesync.py:341`, and both loaders at `:265-272` / `:303-310`).

**REALFIX-T2 — the second clock nobody named.** The harness's leg table is *also* whole-second (`session.py:1027`, `:1077`), worth ±0.5 s = ±143 u on every leg-to-capture mapping in both lanes' analyses. One line each: `"started_unix"`, `"ended_unix"`, `"settled_unix"` = `time.time()` in the `walk_legs` row at `session.py:1079`. Cheap and it removes a systematic that no one had priced.

**REALFIX-T2b** (already free, §1.2): the `0x0047`/`0x003D`-at-the-same-position pair gives the leg boundary on the wire's own clock, for the 6-of-8 legs that emit a stop.

#### 2.2 Expected residual, stated honestly in three parts

After T1 the **clock** error is gone; what remains is **physical** and is not a clock problem:

| term | size | grounds |
|---|---|---|
| clock alignment | **< 1 ms (< 0.3 u)** | two adjacent reads inside `event()`; 1e-7 s clock resolution measured |
| transport, server-send → client-apply | **≤ 6 ms (≤ 1.7 u)** | the capture's own `ping_summary` row: `{"last_ms": 6, "missed": 0}` in `authsrv-20260821T082631-c1.jsonl`, loopback |
| **movetap sample phase** | **≤ 1/f (50 ms = 14 u at 20 Hz)** | the binding term |
| **total, one-sided** | **≤ 0.06 s / ≤ 17 u at 20 Hz** | vs **1.00 s / 288 u** today |

**REALFIX-T3:** the residual is now sample-rate-bound, so `--hz 20` is a *requirement* of the clock fix, not a nicety. If the reader sustains only 12 Hz the residual is 0.09 s / 25 u — still 11× better than today, and it must be **printed as the achieved figure**, never assumed.

#### 2.3 The fiducial is a validator, not the anchor — and the skeptic's correction is adopted verbatim

The five `agent+0x80` flip-to-grant lags are +0.018…+0.107 s, spread 0.089 s. **That spread is invariant under the offset** — under `offset=min` the same five lags read +1.018…+1.107 with the identical 0.089 s spread — so it proves nothing about which branch is true. What excludes the min branch is `ping_summary last_ms = 6` plus 0.089 s being one movetap sample interval at 9.5 Hz. **Do not restate ±0.1 s as a "fiducial spread".**

> **REALFIX-T4 — pre-registered validator. ❌ NOT BUILT as of `facd3ec`; see §5 row 4½.** After T1, for every plane-word-changing grant the lag from the wire send to the observed `agent+0x80` flip must be **≥ 0 and ≤ 1/f_tap + 0.05 s**. A negative lag, or one > 0.25 s, means T1 did not take, and **every cross-tab reverts to being scored on the client-memory `+0x80` anchor alone** — which is where HUNT's plane table already sits, correctly.

**And this stands whatever the clock does:** re-anchoring L1's landing 2×2 on a *fitted mean* lag (+0.077 s) instead of per-event moves E3 (own lag +0.018 s) into the wrong cell and degrades the table to [[2,1],[0,27]] with a phantom warp in the no-rewrite/below-cut cell. **Every landing cross-tab in L2 is anchored per-event on the client-memory `+0x80` flip, and the mean-lag sensitivity is printed beside the table.** The event identification itself needs no alignment at all — it is an adjacent-sample difference inside one movetap file.

#### 2.4 Instrument change: REALFIX-I1, the history chain

Both lanes and the skeptic converge on this and it is the only measurement that turns elimination into observation.

> **Delta (~20 lines, `movetap.py`):** follow `state_record+0x04` (`S_HIST_HEAD`, `movetap.py:256`) → `node+0x04` for up to N nodes, emitting each node's `+0x00` time and `+0x08..+0x14` point **including its plane word**, plus **the client's own plane for both copies at every node** (the skeptic's addition — without it grant #37 stays unadjudicable, and #37 is the only case separating "the plane echo *causes* snaps" from "the plane echo *permits* them").
>
> **Gate it on `sep > 250 u`.** A full sample is ~20 `ReadProcessMemory` calls; 8 unconditional node reads is ~+40% and would drop 9.5 Hz to ~6.8 Hz — fighting §2.2's residual. The match test only matters where gate 1 could fire, so read the chain only there. **This conditional is a design requirement, not an optimisation.**

Then, at each instant, the match test is *recomputed from the sample*: a node inside 100 u of `q` whose plane differs from `q`'s ⇒ candidate A confirmed at the operand; no node inside 100 u ⇒ candidate B revived; a truncated/cleared chain ⇒ the third reading, currently unpriced.

---

### 3. PER-MECHANISM FIX CANDIDATES — F1 is BUILT and unrun; F2a, F2b and F3 are spec'd, NOT built

#### REALFIX-F1 · the plane echo fix — one line and one state slot

✅ **BUILT 2026-08-21 as `--plane-carry`, and UNRUN.** The flag, its state slot, its telemetry and its startup banner are in `authsrv.py`; `test_position_trust.py` §15 locks them at **23 checks (floors 183 vaulted / 175 bare)**, every one proven able to go red — 15 mutations at the landing, then **23 more from an adversarial lane, 22 red and 1 survivor**, and the survivor's fix is the 23rd check (see the second-pass note in §5). **It is a MODIFIER ON `--zero-lead`, enforced rather than documented:** `--plane-carry` alone is REFUSED at startup by `zero_lead_composition` and `main()` raises, because F1 has no send site of its own and an inert flag would run a server identical to the shipped default while the operator's log said "F1 arm". `--zero-lead` alone still runs — it is the arm F1 is measured against. **NOTHING BELOW HAS BEEN RUN AT A CLIENT.** The run it is aimed at is REALFIX-L3's X3 cell, and the F1 arm is `--zero-lead --plane-carry`.

**Site:** the zero-lead send's argument list — `authsrv.py:10294-10296` as drafted, and the shipped attachment is the `if zero_ok:` send inside the `if ZERO_LEAD:` block (the line numbers moved with the flag's own comment block; the block is the anchor, not the number).

```python
## field 3 = the DESTINATION's plane (the newest report's) -- unchanged.
## field 4 = the plane the AUTHORITATIVE COPY is standing on, which under zero
##           lead is the point of the PREVIOUS grant, by construction.
prev_plane = state.get("zl_last_grant_plane", plane)
send(GAME_SMSG_AGENT_MOVE_TO_POINT,
     [PLAYER_AGENT_ID, list(reported), plane, prev_plane], ...)
state["zl_last_grant_plane"] = plane
```

**Grounds, and the caveat travels with it.** Retail's field 3 **leads** field 4: of 1,245 differing rows, **939 (75.4%) lead** at delay p25/p50/p75 = **0.26 / 0.64 / 1.28 s**; independently replicated at 80.3% unbounded and **83.6% under a symmetric ±3.0 s window** (n=825), so the asymmetry attack fails. ⚠ **This is measured over retail's whole AGENT population, which is overwhelmingly NPCs; the player-identified version is UNVERIFIED (87% vs 39% under two identification rules).** F1 is a proposal grounded in NPC grants and must be labelled so.
⚠ **Corpus correction to carry into FINDINGS:3407 and :3790**, which both quote 14 of 987 (1.4%) as retail's rate: read **"1.4% in `20260807T143055`; 12.8% over the live corpus, n = 9,733, per-capture 1.4–30.2%, with `20260817T231139` supplying 51% of the differing rows."**

**The run it changes: REALFIX-L2 Part 1, the X3 instants.**
- Predicted: grants whose field 4 differs from the SYNC copy's `agent+0x80` go to **0** from a baseline of **8 plane-rewriting grants above the cut and 2 below — 10 in the whole L3 run**, of which the late X1 and X2a legs carry 3 (and produced 0 events); no finer per-cell split was recorded, so the denominator is the run. Separation p50/p90 **unchanged within 5%** (F1 touches no position); the **X3 event count goes to 0** (it was 3).
  > ⚠ **CORRECTED 2026-08-21. This line called one quantity both observed and predicted in a single sentence** — it read *"go from the run's observed count (predicted 11 in X3, 3 in X1, 6 in X5) to 0"*. **11/3/6 are §4.1's `instants planned` column for X3/X1/X5: SIMULATED, for a plan that had not been run, and never observed.** FINDINGS's REALFIX-L3 entry says so in as many words — *"the plan yielded 8 above-cut plane-rewriting instants rather than the 11 simulated"* — with X3 = 3 events beside it. The number matters because it is the baseline F1's **primary** falsifier is scored against: 11 rather than 8 makes any F1 result read as a larger improvement than it is. The same triple had reached `authsrv.py`'s `--plane-carry` startup banner labelled "REALFIX-L3 observed", i.e. a prediction printed as an observation inside the artifact whose whole purpose is that the baseline cannot be rationalised after the run; both are corrected and the banner's counts are now pinned by `test_position_trust.py` §15 like every other evidential string in it.
- **Falsified if** any X3 event survives F1, **or** if separation p90 moves by more than 5%, **or** if the field-4 mismatch count is not 0.

**Named limit:** F1 under-corrects when the copy is more than one grant interval behind — after a rate-limit refusal (4 of 70 headings in arm B) or a stall. It is a one-interval correction for a one-interval lag; W2 says that is exactly the lag zero-lead produces at free-travel cadence, and nothing more.

**REJECTED variant, and why it matters:** field 4 = `plane_at(copy_estimate)` from our own navmesh. Refused — `plane_at` is 189/198 and **its 9 failures are exactly bridge-over-ground**, which is this map's site; and our mesh is genuinely ambiguous here by measurement ((10990, 5000) → planes [0, 18]; (10990, 4600) → [18] only). Verify the operand, don't compute it from the one tool known to be wrong about it.

#### REALFIX-F2a · corner-cutting mitigation (i) — grant floor keyed to command changes

**Site:** restore the shipped `turned or walking` gate at `authsrv.py:9758` for the zero-lead arm.
**Rationale under candidate B:** the client pushes a history node on a movement-command change or 2.5 s head age (`0x0060593A`); granting only at command changes puts `q` on a node instead of mid-chord.
**The run it changes: every leg of REALFIX-L2, and it is priced as expected-to-fail.** W4 measured the commanded heading **exactly constant within a leg — max deviation 0.000° over 16 legs**. A command-change-only floor therefore grants **once per leg**: the key-down report and nothing else. Grants on a `W:6.5` shuttle leg fall **4 → 1**, and separation, instead of saturating at 515 u, grows to the full leg length — **up to 1,855 u**. That is the P0 cost-of-silence regime (p50 4,402 u) returning by a different door.
⇒ **Do not spend a live arm on F2a.** It is priced here so the ladder does not.

#### REALFIX-F2b · corner-cutting mitigation (ii) — lower `GRANT_MIN_INTERVAL`

**Site:** `authsrv.py:3047` (`GRANT_MIN_INTERVAL = 0.5`) — but the constant is **shared with the click arm**, so the delta must be a heading-arm-scoped floor inside `_heading_grant_ok` (`:3119`), not a move of the module constant.
**The curve, from the two points REALFIX.md §4's M1 table gives** (OBSERVED, offline, `ours`, P2 counterfactual, match-ON):

| capture | M1 max, floor 0.50 s | M1 max, floor neutralised | Δ | slope |
|---|---|---|---|---|
| `20260814T100340` | 4.94 s | 4.55 s | 0.39 s | **0.78 s of lag age per second of floor** |
| `20260820T182934` | 2.52 s | 2.00 s | 0.52 s | **1.04 s per second of floor** |

A linear read of two points says **0.50 → 0.25 s recovers ~0.20 s and ~0.26 s of M1 max**, moving `100340` from 4.94 to ~4.74 s against D2's 5.0 s trigger, which currently misses by 0.06 s. **Two points support a slope and nothing more; state it that way.**
**The run it changes: NOT REALFIX-L2.** The floor refused **4 of 70** headings in arm B, and this plan's free-travel reports are 1.80–2.74 s apart (W2), so the floor is inert here. **F2b's regime is the round-4 trigger run** (0.30 s report cadence, where the floor binds), and it should be pre-registered there, not here.

#### REALFIX-F3 · defer the grant on a deflection — **INVENTED HERE, unpriced**

Skip the grant when the newest report's position deviates from the straight extrapolation of the previous two reports by more than `MATCH_RADIUS` (99.919968 u). One predicate; state is the last two reports.
**The run it changes: the X1 and X2a legs.** Under B it removes the event; under A it does nothing. Cost: one skipped grant per deflection = **+1 chord (~515 u) of separation exactly at contact**, which is the worst moment to add lag if B is *wrong*.
**Label:** this is not derived from any measurement in the record and has no retail grounding. **Do not build it before X2a returns a positive.**

#### REALFIX-L8 · the overwrite test — PRE-REGISTERED 2026-08-21, before the run

**The question L7 failed to reach twice:** when a lead-carrying click grant DOES escape, does a following zero-lead grant stop it becoming a warp? L5's A3 and L7's treatment both produced **zero** escaping grants, so the composite's zero has never been a demonstrated save.

**No build change is needed, and that was measured rather than assumed.** The three gates a cold-latch click must pass together are rule 1 (`kbd_moving_at is None`, from a `0x0047` stop until the next moving `0x003D`), freshness (`now - pos_seen <= 1.0`, `authsrv.py:12273` — and the STOP refreshes `pos_seen` too, `:12528`), and rule 2 (`now - grant_at > 0.5`, shared clock). Measured over L7's own captures: the window is **non-empty at 41 of 41 stops (control) and 41 of 44 (treatment)**, opens at **stop + 0.00 s** (p90 +0.22 s in the treatment) and is **p50 0.83–1.00 s wide**. Clicks landed inside it 11 and 14 times and were then killed **downstream by the geometry gate** — "not a straight shot" x26, "cannot place them" x1 of 58 clicks. **L7's exposure failure was PLACEMENT, not timing, and not the shared clock.**

**Protocol changes from L7, each keyed to a measured cause:**
1. **Click IMMEDIATELY on release, not after a beat** — L7's "wait ~1 s" put 21 of 58 clicks past the 1.0 s freshness bound. The window opens at the stop.
2. **Three or four rapid clicks per release**, so a human is not aiming at a sub-second target by hand.
3. **Click 400–800 u along OPEN GROUND**, not maximum distance across buildings. Corpus-wide, **48 of 78 warp-causing grants carried a lead under 1,000 u and 8 under 600 u**, so a moderate clear-line click both passes the clip test and clears the 299.33 u cut.
5. **KEEP TURNING — do not walk in a straight line.** Measured per `movementType` over every `ours` capture: straight forward running (type 1, 283 u/s) has an inter-report gap **p90 of 1.80 s**, and 515 u / 283 u/s = **1.82 s** — REALFIX-W2's distance trigger exactly — so **25% of its intervals leave the 1.0 s freshness gate already CLOSED** before a click can land. Every maneuvering type sits at **0–4%** (types 2/3 at 282 u/s: 3–4%; types 7/8 at 210 u/s: 1–3%; types 5/6 at 186 u/s: 0%) — and those per-type speeds **corroborate `FINDINGS`:1201's families independently** (forward {1,2,3} 284.96 u/s, backward {4,5,6} 187.89, side {7,8} ~215) on a larger corpus. ⚠ The one figure NOT to reuse from this sweep is its type-4 p50 of 126 u/s: it is unfiltered and includes wall-slides and stalls, where :1201's 187.89 is the careful number. Those are SLOWER, so the ~512 u distance trigger alone predicts SPARSER reports and the opposite is observed. ⚠ **The mechanism is NOT established here and this block should not be read as establishing it**: `FINDINGS`:1218 already records `0x003D` as distance-triggered at a ~512 u chord **with a ~0.5 s heartbeat fallback**, and every maneuvering type's gap p90 (0.50–0.58 s) is that heartbeat rather than anything about turning. Type 1's p90 of 1.80 s is the chord. Why sustained cruise does not also show the heartbeat is UNVERIFIED and is the open question here; the protocol advice below stands on the measured gap distribution either way. Arc or feather A/D through every leg, and release out of a turn rather than out of a sprint. ⚠ Types 5 and 6 record **zero** following stops in the corpus, which would mean releasing from them never opens the window — but at n = 50 and 77 that is too thin to act on, and the 368 + 286 stops that do exist come from types 1 and 4, so release from a normal forward or moderate-speed leg.

4. **Watch the server terminal** — it prints each refusal reason live, so a bad direction is visible within a second.

**PREDICTIONS, numeric and falsifiable:**
- **Control `--grant-suppress`:** ≥ 8 escaping cold-latch grants, and at the 3-of-3 conversion measured across L6+L7, **5–15 REALFIX-E events**.
- **Treatment `--zero-lead --grant-suppress`:** a comparable count of escaping grants. **If the overwrite is honoured → 0 events despite ≥ 5 escaping grants.** If it is not → an event rate statistically indistinguishable from the control's.
- **ABORT CONDITION, named in advance so it cannot be rationalised afterwards: if the TREATMENT again produces fewer than 3 escaping grants, this is the third consecutive exposure failure and the run answers nothing** — do not score it as a null, and price the build change (a click-arm exemption from rule 2) instead.

**Instrument:** movetap on both arms, full-length; L7 achieved 12.0–13.3 Hz and REALFIX-E on the rendered copy is the verdict, with `--wire-only` printed beside it.

> ⚠★ **RUN 2026-08-22 — the control's predictions both land, and the treatment's ABORT CONDITION FIRED.** Control (`20260822T161838`+tap `161918`): **32 escaping cold-latch grants** (predicted ≥ 8; every immediate fired click had `keyboard_age = None`) plus 16 `deferred-grant` fires from the click arm's coalescing hold, and **16 REALFIX-E events** against the 5–15 band — one above its top, because L6/L7's 1:1 parked-copy conversion does not generalise: 10 of 16 snaps fired MID-GLIDE (landings 116–434 u from any destination), only 6 landed on a granted point. Treatment (`20260822T162502`+tap `162513`): **0 escaping grants — the abort fired, third consecutive exposure failure, the overwrite stays UNTESTED and is not scored as a null.** The cause was NOT L7's preemption: a plane-echo event (mechanism A — `--plane-carry` correctly off per this design) at world-clock 31.2 s stamped plane 18 onto the copy at plane-0-only ground, yanked the operator 251.5 u onto it, and wedged them inside the bridge abutment, after which all 44 clicks died upstream ("off-mesh" ×16, "not a straight shot" ×25). The priced build change (click-arm exemption from rule 2) stands; **any L9 must ALSO stage in the open plane-0 field (§1.4's site list) and pre-register the treatment's `--plane-carry` decision.** Full record: FINDINGS §"REALFIX-L8".

#### REALFIX-L9 · the overwrite test, arena-fixed — PRE-REGISTERED 2026-08-22, before the run

**The question, unchanged through three failed exposures (L5's A3, L7, L8):** when a lead-carrying click grant escapes the cold latch, does the zero-lead stream prevent the warp — and if it does not, do the events land on the clicked destinations?

**Design rulings, each with its grounds:**

1. **NO build change, and the priced exemption is deferred with a pre-commitment.** L8's abort clause ordered the click-arm rule-2 exemption priced. Priced: ~10 lines in the click arm plus telemetry and a `test_position_trust` section. **Not built for L9**, on two grounds. (a) Timing was never the binding constraint: L8's treatment produced **zero click verdict rows** — rule 2 never saw a click; every death was upstream in geometry ("off-mesh" ×16 from inside the bridge, "not a straight shot" ×25) — and L7's preemption, while real, is the tail: the joint cold-latch window opens at **stop + 0.00 s (p90 +0.22 s in the treatment)** over L7's own captures. (b) An exemption inside the treatment makes the tested configuration non-shippable and adds a second variable to the one contrast that matters. **Pre-commitment: if L9's treatment aborts on exposure, the exemption — minted here as REALFIX-I2, an INSTRUMENT flag, not a fix candidate — is MANDATORY for L10. No fourth protocol-only attempt is permitted.**
2. **The arena is part of the protocol and it is binding: the open plane-0 field, x 10700–12300, y ~2700–4300** (§1.4's own site list — clear straight runs ≥ 3,000 u, no plane boundary anywhere). Stay south of y ≈ 4300; never approach the deck or its aprons. A warp that throws the player out (control warps will — L8's reached y 11440): walk back before the next cycle; cycles executed outside the arena still count for positives but not against the choreography. An operator wedged or stuck ends the arm; data to that point stands, with the time noted.
3. **`--plane-carry` is EXCLUDED, and in this arena the exclusion costs nothing:** one plane means no plane can differ (L5 W3's own logic), so the treatment stays the clean composite — byte-identical flags to L7/L8 — and L8's "pre-register the plane-carry decision" item is discharged rather than dodged.
4. **Mechanism-A contamination guard:** any tap sample or event during arena play with either copy's plane ≠ 0 means the arena rule was broken or mechanism A intruded; such an event is classified separately and does NOT enter the overwrite cell. Expected plane census: {0} only.

**Arms, order, and a staging gate.** Arm 1 control `--grant-suppress`; arm 2 treatment `--zero-lead --grant-suppress`. Control first, and it is a gate: **fewer than 8 escaping cold-latch grants in the control means stop and fix the choreography before spending the treatment.** ~4–6 min per arm, ≥ 40 stops. Movetap attached at map-load PASS before play, `--hz 20 --seconds 360`; arm identity earned from the verdict vocabulary (L8's addendum: `deferred-grant`, `heading-rate`, `pending-expired`).

**Protocol.** L8's choreography verbatim — keep turning (arc/feather A/D); release out of a turn; click IMMEDIATELY on release; 400–800 u along open ground — with two refinements. **Spread the 3–4 clicks across the ~1 s window rather than bunching them in the first 0.2 s**: the shared clock frees at latest ~0.5 s after its last stamp while freshness holds to ~1.0 s, so the spread is what covers L7's preemption tail with no build change. **Keyboard 3–4 s between cycles** — the zero-lead stream between windows IS the treatment, and a protocol that only stops and clicks starves the overwrite channel. In the treatment, continue until the server terminal has shown **~10 escaped click grants** (a sent `AGENT_MOVE_TO_POINT` right after a stop+click) or ~6 minutes, whichever first.

**PREDICTIONS, numeric and falsifiable, written before the run:**

- **Control:** ≥ 8 escaping cold-latch grants (L8: 32, map-wide, worse terrain); REALFIX-E events at **0.15–0.5 per fired grant** (L8: 16/48 = 0.33); every event lands ≤ 30 u from the contemporaneous `sync_at`.
- **Treatment exposure:** ≥ 5 escaping cold-latch grants. **ABORT, unchanged from L8: fewer than 3 escapes → fourth consecutive exposure failure → the run answers nothing, is not a null, and ruling 1's pre-commitment fires (REALFIX-I2 mandatory for L10).**
- **The decision cell, given exposure:**
  - **PROTECTED** (overwrite honoured, or protection by any in-band mechanism): **0 treatment REALFIX-E events.** Power stated now, not after: at the control's per-fired-grant conversion (~1/3 — the conservative arm; per-cold-escape it is higher), P(0 events) = **0.13 at 5 escapes, 0.017 at 10**. A zero at fewer than 10 escapes is SUGGESTIVE, not decisive, and the binomial is printed beside the verdict — which is why the treatment runs to ~10.
  - **NOT PROTECTED:** treatment events at a per-escape rate indistinguishable from the control's, landing ≤ 115 u from a granted click destination at 5–35 s lag (L6/L7's measured band).
  - **PREEMPTION-ONLY** (L7's n = 1 mechanism): cold-latch clicks refused `rate-limited` rather than fired. That is an EXPOSURE outcome, counted toward the abort — never a protection claim. The refusal census is printed either way.
- **Anomaly clause:** a treatment event landing > 150 u from every granted destination is outside both hypotheses — it voids the cell and goes to REALFIX-Q5, with its covariates printed.
- **The invariant falsifier is SHARP here for the first time.** One plane means the plane-word excuse that discharged L8's marginal event is unavailable. A treatment event whose last pre-snap `sep` reads < 299.33 u with the copy on walked ground fires `REALFIX.md`:238 as written. The tap's clock-quantisation error (~±14 u per copy at run speed) travels with any such claim.
- **Secondary, printed, not a verdict axis:** the parked-copy contrast (L7 §2's metric) — control separation p50 ≥ 1,000 u, treatment p50 ≤ 500 u outside click windows.

**Blind-budget rules, per L8:** the artifact gate (async identity single-valued) before any event is believed; the > 0.25 s adjacent-pair census printed; a NULL needs tap coverage ≥ 90% of played span — positives are valid regardless; an early tap death leaves the tail UNJUDGED, never counted as a miss.

> ★★ **RUN 2026-08-22, same day — THE PROTECTED CELL, on the fourth attempt.** Control (`20260822T165425`): 11 cold escapes + 16 deferred = 27 full-lead fired grants → 7 REALFIX-E events (0.26/grant, inside the registered 0.15–0.5; the p50≥1,000 u separation secondary MISSED at 621 u — a 27-grant control moves the copy). Treatment (`20260822T165910`): **8 cold escapes + 25 deferred = 33 full-lead fired grants, 33/33 over the cut — and 0 REALFIX-E events** (largest rendered step 51.0 u; wire 0 hard rows from 174 grants; null licensed at 93% coverage, no >0.25 s pairs). Registered binomial: (2/3)⁸ = **0.039** (suggestive-plus, as the registration pre-stated for <10 escapes); per-fired-grant Fisher 7/27 vs 0/33 = **0.0023**; expected events at the control's conversion 8.6, observed 0. The overwrite is honoured MID-FLIGHT (first overwrite 1.18–3.02 s after every escape; sep max 954 u against 1,500–2,800 u leads; copy's closest approach to clicked dests p50 216 u vs the control's parked 37 u/min 0.0), the invariant is observed protecting (92 above-cut samples under continuous bakes, 0 snaps — the copy rides the history polyline), and L6's lingering-destination residue did not manifest under overwrite pressure (33 candidates, 0 events). The exposure fix was the spread clicks plus the click arm's own deferral channel — rule-2 preemption arrives as a ~0.5 s delay, not a suppressor, so **REALFIX-I2 was never needed and stays unbuilt**. One deviation: both arms played the spawn-north field, not the registered arena — the rule's purpose held (every report, sample and plane word is plane 0). Full record: FINDINGS §"REALFIX-L9".

#### REALFIX-F4 · bound the click grant's lead — **REFUTED AT A DESK 2026-08-21, never built**

**Site (had it been built):** the click send at `authsrv.py:11253` — refuse a grant whose destination lies further than a bound *B* from the client's own last report.
**Why it looked right:** the spam-click regime's warps are gate 1 firing on a granted point 1,400–2,600 u away, and a grant inside `MATCH_RADIUS` cannot reach gate 1.
**Why it is refused, measured over the whole `ours` corpus (2,445 grants, 82 attributable warps):** at `MATCH_RADIUS` it refuses **99% of warp-causing grants at a cost of 94% of ALL grants**; at 1,000 u the ratio INVERTS (35% benefit, 45% cost). **The bound does not separate, because a click grant is far BY DEFINITION** — "far grants" and "all click grants" are one population. That makes F4 `--grant-suppress` with extra steps, and the arc already ships that.
**What it rules out generally:** any click-arm policy keyed on the grant's own distance. FINDINGS §"REALFIX-F4 REFUTED AT A DESK".

#### The finding that constrains the whole ladder

At keyboard cadence, **the chord length is set by the client's own 515 u report trigger (W2), not by our grant floor.** We cannot grant more often than reports arrive. So if candidate B fires in X2a, **P2 has no cheap dial** — F2a costs the separation win outright, F2b is inert in this regime, and F3 is invention. That makes X2a the ladder-deciding cell: a positive there sends the arc to P3/§2.2, not to a P2 parameter.

---

### 4. PRE-REGISTERED PREDICTIONS

Written before the run, in counts that can fail. Base rate for a plane-rewriting above-cut grant, from L1: **3 of 4**, Jeffreys 95% CI **[0.284, 0.972]** — n=4, post-hoc, and the interval is wide on purpose. Base rate for an above-cut **non**-rewriting grant, from L1: **0 of 27**, Jeffreys 95% CI **[0.0000, 0.0997]**.

#### 4.1 Primary table

| cell | instants planned | **A: plane echo** predicts | **B: corner-cutting** predicts | **location confound** predicts | **null (P2 is fine)** predicts |
|---|---|---|---|---|---|
| **X1** parapet slide + crossing | 3 | **≥ 1 event** (E[2.3] at p=0.75) | **≥ 1** | ≥ 1 | 0 |
| **X2a** deck slide, no crossing | 6 | **0** | **≥ 2** (E[4.5]) | ≥ 1 | 0 |
| **X2b** open slide, no crossing | ≤ 3 (provisional) | **0** | **≥ 1** | **0** | 0 |
| **X3** centreline crossing, hot | 11 | **≥ 6** (E[8.3]) | **0** | ≥ 6 | 0 |
| **X4** open straight | 11 (3 + 8 from transit/shuttle) | **0** | **0** | **0** | 0 |
| **X5** crossing, below cut | 6 | **0** | **0** | ≥ 2 | 0 |
| **X6** on deck, above cut, no rewrite | 9 | **0** | **0** | **≥ 3** | 0 |

#### 4.2 Discriminations, each with the arithmetic that makes it decisive

- **A vs B — the crux.** `X3 ≥ 6 with X2a = 0` ⇒ **A, B refuted**. `X2a ≥ 2 with X3 = 0` ⇒ **B, A refuted**. Both non-zero ⇒ both live, and X2b + X6 arbitrate.
- **Power on X3's null.** `P(0 events in 11)` = **0.0000** at p=0.75, **0.0005** at p=0.50, **0.0198** at p=0.30 (the CI's lower edge). So **X3 = 0 refutes A at the weakest plausible rate too.**
- **Power on X2a's null.** `P(0 in 6)` = 0.0002 / 0.0156 / **0.1176** at p = 0.75 / 0.50 / 0.30. ⚠ **A B-rate at the bottom of the band survives an X2a null 12% of the time.** If the session budget allows, **run X2a at 6 reps (12 instants)**: `P(0 in 12 | p=0.30)` = **0.0138**. Recommended; stated up front so it is not a post-hoc rescue.
- **The confound cell.** **X6 ≥ 1 event ⇒ both named mechanisms are wrong and the driver is location/geometry.** X6 shares its legs, its separation and its position with X3; only the plane rewrite differs. This is the cell that was **empty (n=0) in L1** and it is the single most important addition in this design.
- **The invariant.** **X5 ≥ 1 event ⇒ REALFIX.md:235 fires** — "a P2-arm snap recorded while movetap shows separation < 299.33 u" — and every policy in that document becomes beside the point. Predicted 0 under both mechanisms. `P(≥1 in 6 | p=0.05)` = 0.265, so a null here is weak evidence and must be labelled as such.
- **Sanity floor.** **X4 ≥ 1 event ⇒ the run is broken or `--zero-lead` is harmful everywhere**; L1 already gives 0 of 27 above-cut same-plane instants, including 7 consecutive seconds at sep 510–520 u with gate 1 "above" and the fence open (arm B L4).
- **Arm P0 (geometry control).** Predicted **0 events in every cell** — it sends 0 grants, so `agtrack_dispatch` is never entered. **P0 ≥ 1 event refutes the whole grant-mediated reading of this arc.** ⚠ P0 is a valid control **for geometry only** and is **vacuous for the mechanism**; the causal weight rests entirely on the within-P2 contrast across cells.

#### 4.3 Blind-budget qualification — the licence for every null

L1's nulls were quoted past their budget. These will not be.

1. **Per-leg coverage rule (the operative licence).** A leg is **scorable for a null** only if movetap covered **≥ 95%** of its span **and** no intra-leg sample gap exceeded **0.30 s**. Otherwise the leg is **VOID for a null and still valid for a positive**. (L1's max intra-leg gaps were 0.176 s / 0.215 s, so this is met by a healthy run — but the *file-level* floor `elapsed × hz × 0.5` is too coarse to license a per-cell null, and neither lane said so.)
2. **The rescue argument must be printed beside every null, not assumed.** "N of M above-cut instants produced no event" carries, in the same sentence: the achieved tap rate, the max intra-leg sample gap, and the sentence *"a persistent 300–470 u displacement cannot hide between samples at this gap"*. Without it, that count is L1's withdrawn "~66 test instants, none snapped" re-entering the record unlabelled — and it is the whole denominator of every ratio in §4.1.
3. **Attach movetap before the client.** Arm B's 23.3 s pre-attach window swallowed plane flip #1, 7 grants and an 18.0 s freeze whose shape matches E1–E3. Any instant inside a pre-attach window is **UNJUDGED**, never counted as a miss.
4. **The hard wire bar is reported and is not the endpoint.** Under `--zero-lead` a snap is a **round trip that ends at the client's last reported position** — net wire displacement 0.0 u, three times in L1. ⚠ **Do not restate this as "the bar cannot fire at any cadence or coverage."** Each L1 event opened a **21.64 / 17.25 / 5.51 s report silence beginning at the snap** — that is the blind-budget defect FINDINGS already booked, not a new and worse class — and the three round trips total **4.16 s**, which at the 0.30 s cadence P2's bounds were calibrated on would carry ~14 report instants.
5. **X2b returns NOT MEASURED, not a null**, if no rep yields a valid contact (§1.5).

#### 4.4 Reporting rules, binding

- **The operator's "angled movement" hypothesis is UNTESTED by L1, not refuted.** Measured |dψ/dt| on the rendered track is p90 = 0.007 rad/s — that walk grammar contains no sustained angled motion at all. X1/X2a/X2b are its first real test.
- **Do not write "the plane echo is the mechanism."** L1 licenses only: *the plane word is **necessary** in that run (0 of 27 above-cut same-plane landings warped) and **not sufficient** — grant #37 (t=147.877, w4=0 onto a sync copy reading plane 18, sep 511.2 u, fence armed, same 18→0 direction as E1, copy stopped) matched every stated precondition and did not warp.* n in the treatment cell is 4.
- **Which plane variable is operative is UNDECIDABLE in L1** — three definitions (w4 ≠ sync `+0x80`; w4 ≠ the previous grant's w4; sync plane ≠ async plane) are collinear there and give identical 2×2s. **REALFIX-I1 is what decides it**, and X5 (which breaks the collinearity by holding sep below the cut while the rewrite still happens) is what separates "causes" from "permits".
- **`clear_record`'s snap-path position is not independent evidence.** `clientControlled` goes 1→0 three times in arm A, which sends zero grants and never enters the dispatcher.
- **The location confound is now measurable rather than fatal.** In L1, all 4 plane-rewriting landings were inside or within ~250 u of the plane-18 corridor, all 27 above-cut controls were outside it, and the separating cell was empty. X6 fills it at n=9 from the same legs.
- **Corner-cutting's exceedances do not survive their own caveat**, and L2 inherits that: a node at every wire report already gives **0 exceedances (max 72.4 u)** against the 99.92 u radius; only the thinned 2.5 s-rule proxy exceeds; the report-lateness bound is **v·gap = 285.4 × 1.80 = 514 u at the p50 gap**, larger than any exceedance either lane measured; and the steady-turn sagitta at the client's own 2.5 s node rule is **1.6 u**. **B's only surviving route is a collision deflection**, which is why every B-cell in §1.3 is a wall cell and why W3's reclassification rule is load-bearing.

---

### 5. WHAT LANDS IN THE TREE, IN ORDER

| # | delta | file:line | size | blocks |
|---|---|---|---|---|
| 1 | **REALFIX-T1** float wall stamp ✅ **LANDED 2026-08-21** | `toolkit/authsrv/authsrv.py:8396` | 1 line | everything wire↔tap |
| 2 | **REALFIX-T1** loader prefers `wall_unix`, prints which and the residual ✅ **LANDED 2026-08-21** | `toolkit/clientscan/movesync.py:341`, `:265`, `:303` | ~10 lines | — |
| 3 | **REALFIX-T2** float leg stamps ✅ **LANDED 2026-08-21** | `toolkit/harness/session.py:1027`, `:1079` | 3 lines | leg assignment |
| 4 | **REALFIX-I1** history-chain walk, gated on `sep > 250 u`, node plane + both copies' planes ✅ **LANDED 2026-08-21** | `toolkit/clientscan/movetap.py` (near `S_HIST_HEAD`, `:256`) | ~20 lines | the A-vs-B adjudication |
| 4½ | **REALFIX-T4** the §2.3 lag validator (`≥ 0`, `≤ 1/f_tap + 0.05 s`) ❌ **NOT BUILT — declared unbuilt 2026-08-21** | nowhere; it exists only in §2.3 | ~15 lines, offline | whether T1's anchor may be used at all |
| 5 | run **arm P0** with the plan (geometry calibration) | — | ~5 min | cell assignment |
| 6 | run **arm P2** with the plan | — | ~5 min | the verdict |
| 7 | **REALFIX-F1** plane carry ✅ **LANDED 2026-08-21 as `--plane-carry`, UNRUN** — items 5–6 produced X3 events (3 of them), which is the condition this row made it conditional on | `toolkit/authsrv/authsrv.py`, the `if ZERO_LEAD:` send | 1 field + 1 slot | the fix A/B |

Items 1–4 are instrument work with no policy content and can land before any client is up. Each needs its `TESTS.md` entry in the same commit (`test_srclint.py` §7 checks both directions), and item 4 needs a `LEDGER` floor set from a real green run.

### ✅ Items 1–4 landed 2026-08-21 — what was built, and the one thing the bytes changed

**T1.** `Recorder.event` writes `kw["wall_unix"] = time.time()` beside the truncated `wall`, which stays (every consumer and every vault fixture reads it, and the whole existing corpus has only that one). Loader side, `movesync.offset_detail` / `offset_line` prefer the float rows — **median** over per-row offsets, max−min as the residual — and fall back to the truncated **max**-estimator otherwise, printing which and the achieved residual. The two families are never pooled: a mixed file uses the float rows and *counts* the truncated ones (`n` vs `n_trunc`). `offset_from_stamps` keeps its two-value return, because `pair`, `resyncscore`, `grantsim` and `test_movesync` §1 all unpack exactly two. **OBSERVED, measured end to end through the real `Recorder` in `test_movesync` §21: 201 rows, offset spread 12–32 µs = 0.004–0.009 u across runs**, against §2.2's predicted "< 1 ms (< 0.3 u)". The same synthetic file scored on truncated stamps gives **0.977 s / 281 u**, and the real `20260819T145717` capture gives **1.000 s / 288 u** — §2.1's figure, reproduced by the shipped printer.

> ⚠ **CORRECTED 2026-08-21: this paragraph first read "200 rows, offset spread 11.4 µs = 0.0033 u" and that point estimate does not reproduce.** It is a live sample of scheduling jitter between two adjacent clock reads, not a deterministic figure: independent runs of the same check give 12.4, 14.3 and 31.7 µs, a 2.8× spread. The row count was also wrong by one — the printer itself says 201 (the reports plus the origin row `Recorder.__init__` emits) and the test asserts `n == len(reports) + 1`. **What survives is the claim §2.2 actually needs**, `< 1 ms (< 0.3 u)`, by ~30× on the worst draw seen; what does not survive is quoting a single draw as a measurement. The two synthetic/vault figures beside it (0.977 s, 1.000 s) are deterministic and reproduce exactly. This is the "error bars before conclusions" rule, and the fix is to quote the range.

**T2.** `walk_legs` records `started_unix` / `ended_unix` / `settled_unix` beside the three whole-second strings. `settled_unix` is read *after* the settle sleep, which is pinned.

**I1.** `movetap.history_chain(read, rec, sep, async_ptr, agent_block, now)` walks `record+0x04 → node+0x04` for at most `HIST_MAX_NODES = 8`, gated on `sep > HIST_SEP_GATE = 250.0 u`, emitting per node `{addr, t, p:[x, y, plane, w], age_ms}` plus the record's own cached vertex, `hist_sync_plane` and `hist_async_plane` (raw `agent+0x80` on both copies — **not** `position_at`'s plane, which on the segment branch returns `+0x90`). Refusal vocabulary, never a silent null: `not-attempted:{below-gate, sep-unread, no-state-record}` · `empty:head-null` (a real state — arming writes `(1, 0)` at `0x00605F48`/`0x00605F4F` and clearing writes `(0, 0)` at `0x006060A2`/`0x006060A9`) · `ok` · `truncated:max-nodes` · `unread:{node-pointer-implausible, node-unreadable, node-revisited, node-time-inverted, node-time-future}`. A partial walk keeps the nodes it read and labels itself; nothing but `ok`/`empty` reads as complete.

> ⚠ **THE COMMITTED COMMENT WAS WRONG ABOUT THE RECORD AND THE BYTES WON.** `movetap.py:257` used to say *"on the RECORD itself only +0x00 and +0x04 are touched by any code read so far, and +0x18 is UNVERIFIED"*. **REFUTED, OBSERVED, build 38797:** the appender writes record `+0x08`…`+0x18` on **both** its paths (`0x00605A0E`…`0x00605A25` and `0x00605A38`…`0x00605A4D`), its own head-match test *reads* `+0x08`/`+0x0C`/`+0x10` (`0x00605948`/`0x0060595B`/`0x0060596B`), and the walker reads `+0x08`…`+0x14` back at `0x0060569A`…`0x006056AC` **before** `0x006056AF` steps to the head. So the record's point is the polyline's **vertex 0**, and `+0x18` is the epoch it is dated to — `m_timeStopMovement` when parked (`0x00605904`), the world clock when not (`0x0060591B`). The `+0x08..+0x14` half of the comment (the node point, `0x0060571A`…`0x0060572F`) was correct. All sixteen node/record displacements are now in `_selftest_fence_bytes`, encoded **from** the module constant and matched at their VAs, so a wrong one produces bytes that are not at that address.

**⚠ The gate's price, MEASURED — §2.4's "~+40%" was optimistic and the conclusion holds harder.** §2.4 argued the `sep > 250 u` conditional from *"a full sample is ~20 `ReadProcessMemory` calls; 8 unconditional node reads is ~+40%"*. The first half was never measured. **OBSERVED, offline, driving the real `sample()` over a whole-sample fake memory whose only variable is where the ASYNC twin stands (100 u vs 4,000 u — same shipped gate, no flag): 8 reads below the gate, 17 for a full 8-node walk, +9 = +112%.** `sample()` issues eight reads, not twenty, so an ungated walk roughly **doubles** the sample rather than adding 40%. This is a read count, not a rate: the Hz cost needs a client, and `movetap.chain_cost()` measures it with two 40-sample passes before every run and `main()` prints both figures. **UNMEASURED against a live client as of this commit — no client was run.**

**What this does NOT settle.** The walk reads nodes; it does not yet recompute the match test at the operand (§2.4's "a node inside 100 u of `q` whose plane differs"), which is offline work on the captures L2 produces. And `HIST_MAX_NODES = 8` is a budget, not a bound on the chain: a block holds 256 nodes and is recycled on a 5,000 ms rule (`0x00604C03`), so `truncated:max-nodes` is a real and expected outcome on a long chain and **must not** be read as "no node within the radius".

**REALFIX-T4 IS NOT BUILT, and this list did not say so.** §2.3's pre-registered validator — for every plane-word-changing grant, the lag from the wire send to the observed `agent+0x80` flip must be **≥ 0 and ≤ 1/f_tap + 0.05 s**, with a negative lag or one > 0.25 s meaning T1 did not take — exists nowhere in the tree but in this document. Items 1–4 above are T1, T2 and I1; **T4 is item 4½ and is UNBUILT as of `facd3ec`.** It matters because it is the validator that decides whether T1's anchor may be used at all: without it, an L2 run can produce a cross-tab anchored on a clock nobody checked. It is offline work on L2's own output (wire `wall_unix` against the movetap `+0x80` flip), so it can be built after the run — but the run must be read knowing the bound has not been applied. Consequence if it is skipped: fall back to what §2.3 already prescribes and score every cross-tab on the client-memory `+0x80` anchor alone.

### ⚠ 2026-08-21, second pass — what a verifier lane and a mutation lane changed

Two adversarial lanes read the landing above: one re-derived the layout from build 38797 before opening the code, one planted 36 mutations. **The node layout SURVIVED intact** — `next +0x04`, `time +0x00`, `point +0x08..+0x14` as x f32 / y f32 / plane i32 / w i32, stride `0x2C`, NULL terminator, all re-confirmed byte-exact from both the allocator/appender and the walker, and every committed fence pattern re-encoded to the disassembled bytes. Extra corroboration the landing under-claimed: the appender's own asserts at `0x006059D0`/`0x006059F7` carry `!state->history->velocity.x` / `.y` from `AgTrack.cpp(0x24D/0x24E)`, so **node `+0x18`/`+0x1C` are named velocity by ArenaNet's own source**, not by our reconstruction. Four things did not survive:

1. **REFUTED — the 5 s recycle is measured on the block's NEWEST node, not its oldest.** `movetap.py`'s comment and its fence-byte meaning string both said "OLDEST", printed inside a green `[PASS]`, and contradicted this repo's own `FINDINGS.md:2894`/`:3674`, which had it right. At `0x00604BFF` the operand is `[eax+edi-0x28]` with `eax` already `count*0x2C` (`0x00604BFC`), i.e. node index `count-1` — and the bump allocator at `0x00604DBB` is what makes `count-1` the last appended. The **sense** was correct and stays: `jle 0x604d04` allocates a fresh `0x2c0c` block at ≤ 5000 ms, so recycling needs the newest node to be **more** than 5 s old, a strictly stronger guarantee. The operand is now encoded FROM `HIST_NODE_STRIDE` in selftest §5 (`HIST_RECYCLE_OPERAND`), so the sentence can go red.
2. **The real reason a chain cannot dangle into a recycled block was never in the tree.** The client **severs every reference first**: `0x00604C30-0x00604C77` zeroes any `node+0x04` landing in `[block+4, block+0x2C04)`, and `0x00604C89-0x00604CC7` walks the record array at `[this+0x20]`, count `[this+0x28]`, stride `0x1C` — the same `T_STATE_ARRAY`/`T_STATE_COUNT`/`STATE_STRIDE` movetap reads — zeroing any `record+0x04` in that range. Four fence cases now pin it. **The one hazard that survives the sever is named rather than fixed:** `0x00604CF9` resets only the block's count (the call above it, `0x00605AA0`, is a list splice that writes no node byte) and the pool is shared across agents, so a stale `next` read before the sever plus a target read after a re-append yields another agent's node. Torn-read test 2 catches its realistic form — a re-appended slot carries the current world clock and is therefore newer than the stale parent — and that is now modelled in §13. The residual window is a re-append in the **same millisecond** as the parent's stamp. **An `age_ms` bound against `HIST_BLOCK_RECYCLE_MS` was proposed and is REFUSED with grounds:** `0x00604BD0`'s `jb 0x604dbb` means the age test is only reached when the current block is FULL, so blocks turn over every 256 appends and a legitimate node may be minutes old.
3. **The future-tolerance's stated ground was wrong.** It read "world-0/world-1 clock skew", with a control fixture beside it that therefore tested a mechanism that cannot occur: `sample()` reads `now` from `AGBASE + world*0x64 + 0x148` with `world` the agent's own `+0x24`, and the appender stamps from the **same slot** (`0x00605893 imul eax,[esi+0x24],0x64` then `0x006058A5 mov edi,[eax+ecx-0x84]`, with `ecx` = AgTrack = AGBASE+0x1CC and `0x1CC-0x84 = 0x148`). One clock. The real ground is **read ordering** — the clock is read before the nodes — so the tolerance is our own sample latency and is now its own constant, `HIST_FUTURE_TOL_MS = 250` (2500 → 250), pinned from both sides in §13.
4. **"Section 9's wiring table … so the chain walk's OUTPUT cannot vanish green" was false as written.** Those rows judge the CALL. Gutting `print_hist_summary` to a bare `return`, deleting its refusal warning, and calling `chain_cost` while printing neither figure each ran **206/206 green**. Fixed by moving the cost text into `chain_cost_line()`, requiring `main()` to `print(chain_cost_line(...))` in the wiring table, and reading both printers' stdout back in §13. Three more fixtures could not express the failure they named — a short read (unreachable through either fake memory), the sync copy's plane word (fixture plane and w were both 0), and the `PTR_MAX` ceiling case (planted its head AT the constant) — all three now discriminate. And the body-vs-signature default binding is real but was credited to the wrong controls: `test_movesync` §17's three pass both parameters explicitly and stayed green when the defaults moved back into the signature; §13 now rebinds the module global and calls without the argument.

**The instrument set as it now stands.** 17 files, **1,403 checks, 0 red**, no full-suite run (run-only-affected), no client and no server launched by this lane: `test_movesync` 177 with the vault / 127 bare-machine (7 declared skips) · `movetap --selftest` **231** (floor 231, zero headroom by design) · `movesync --selftest` 80 · `test_grantsim` 68 · `test_position_trust` 160 · `test_probedoc` 74 · `test_resyncscore` 98 · `test_pinned` 143 · `test_harness` 157 · `test_handshake` 23 · `test_buildpins` 40 · `test_updatecheck` 28 · `test_srclint` 22 · `test_provlint` 19 · `test_identlint` 28 · `test_bareimport` 6 · `test_run_suite` 49. Every fix above was proven by re-applying the mutation that motivated it and watching it redden: **15 mutations re-applied, 15 RED, tree restored byte-identical after each.** One of those fifteen was a survivor of the *fix* — the future-tolerance block's own first draft wrote all three cases as `HIST_FUTURE_TOL_MS ± 1`, so they scaled with the constant and widening it back to 2500 ran green. A fixed 400 ms case now pins it into [40, 400). The class-(a) build-pin census moved 151 → **156** on both sides.

### ⚠ 2026-08-21, REALFIX-F1's second pass — 23 mutations, one survivor, and a baseline that was never observed

An adversarial lane replanted the landing's 15 mutations and 13 of its own, one at a time, replacing on **bytes** so line endings and encoding survive the round trip and refusing to start unless every anchor occurs exactly once. **22 RED, 1 SURVIVED**, tree restored byte-identical after each.

1. **The survivor, and the 23rd check.** Moving `state["zl_last_grant_plane"] = plane` from *after* the `send()` to *before* it, inside the same `if zero_ok:`, ran **green**. The lane read it as a provable no-op — `zl_last_grant_plane` is read once and written once, and nothing between the two observes the slot — and that is right **for a send that returns**. It is not the same program otherwise: `send()` ends in `sock.sendall`, which raises, and the shipped `send()` already says so where it explains its own seq gaps (*"crypt advanced the keystream for a message whose plaintext never reached this file"*). With the write after the send, a message that never reached the wire leaves the slot naming the last plane that did; with it before, the next grant carries the plane of a point the copy was never sent to — the same error the rate-refusal case is about, through a different door. §15 now drives a `0x0029` through a send that dies (`PcDeadWire`) and requires the slot to hold. The two *behavioural* readings of that off-by-one — the write hoisted above the READ, and the write dedented out of `if zero_ok:` — were already red, on `PLANE CHANGE`/`TELEMETRY` and on `NAMED LIMIT` respectively.
2. **The real finding was not in the code.** The startup banner attributed to REALFIX-L3 three numbers L3 never produced: *"REALFIX-L3 observed 11 in X3, 3 in X1, 6 in X5"* — §4.1's **simulated** `instants planned` column, printed as an observation, as the baseline for F1's **primary** falsifier, inside the artifact whose whole purpose is that the baseline cannot be rationalised afterwards. The plan yielded **8** above-cut plane-rewriting grants (10 counting the 2 below the cut), and the same confusion seeded §3's prediction line, which called one quantity both observed and predicted in one sentence. Both corrected; §3 carries the retraction beside the original wording. **It reached a commit through a 15-mutation campaign because it was the one evidential string in that banner nobody pinned** — `87% and 39%`, the 5% band and the X3 count all were — so the counts are now in `pc_wanted` too.
3. **A red that bypassed the ledger.** Dropping the `plane_differs` kwarg at the call site reddened by an uncaught `KeyError` raised inside the check's own arguments, which aborts the run before `LEDGER.verdict()`: the remaining §15 checks never executed and **the floor was never evaluated on that path**. Red is red and the mutation was caught, but that is exactly the machinery CLAUDE.md's *"a run that measured nothing failed"* rule exists to keep. The telemetry checks now read those fields with `.get`, so a missing one FAILS BY NAME — except the refused row, where `None` is the answer and presence is asserted with `in` instead.
4. **Correcting the landing lane's own campaign record.** It reported a first-draft mutation, `if PLANE_CARRY or True:`, as SURVIVED-and-self-inflicted "because it short-circuits to a no-op". **That reasoning is wrong** — `False or True` is `True`, so the guard is always taken and F1 runs unconditionally — and replanted it goes red with four named FAILs (`F1 OFF`, `NO POSITION MOVES`, the flag-off telemetry row, and `STRUCTURE` at *0 blocks*). The dismissal was harmless in effect; a wrong reason for dismissing a survivor is what lets a real one through, which is why it is written down here rather than left in a lane report.

**Counts after this pass:** `test_position_trust` **183** vaulted / **175** bare (2 declared skips), §15 at 23 checks, both floors read off green runs of their own configuration and both landing exactly ON the floor — zero headroom, so unhooking any single check reddens. `test_grantsim` 68 unchanged. No client and no server launched by either lane.
