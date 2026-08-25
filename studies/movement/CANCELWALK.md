# CANCELWALK — the single press that cancels the cast but does not move

**Opened 2026-08-24**, on the handover at the end of
[../castmech/FINDINGS.md](../castmech/FINDINGS.md) §3g: pressing a movement key
mid-cast cancels the cast (landed, verified at a client) but does **not** move
the player on our server; a second press is needed. Stock Guild Wars moves on
the single press (owner-verified against retail 2026-08-23). §3g registered
this as a movement-policy question because the obvious fix — grant a lead —
is REALFIX's refuted family.

**Evidence reader: `toolkit/authsrv/cancelwalk.py`** — read-only over the
vault; every number in §3 reproduces by running it. Captures: **live**
`20260824T074002` (origin `live`, build 38849, the castmech cancel-family run,
sealed plan) and **ours** `captures/gamesrv/authsrv-20260824T081335-c1.jsonl`
(origin `ours`, build 38797, the §3g acceptance run on the Isle of the
Nameless).

**Identifiers.** `CANCELWALK-F<n>` = findings, labelled per
[../character/FINDINGS.md](../character/FINDINGS.md). `CANCELWALK-H<n>` =
rival hypotheses for the freeze. `CANCELWALK-R<n>` = pre-registered runs;
their predictions are stated here before any run happens. Convention:
[../idents/CONVENTION.md](../idents/CONVENTION.md).

## 0. HANDOFF — read this before anything else (written 2026-08-24, end of session)

**This document is long and its early sections are superseded. Read §0, then
§7.6–§7.9, then §8 (both runs, scored at §8.1a/§8.2a). §2–§5 are the arc's
history and several of their claims are corrected later — every correction is
filed in place, but §0 is the only summary that is current.**

### What the arc was, and that it is ANSWERED

*Symptom:* a movement key pressed mid-cast cancels the cast but does not move
the player; a second press is needed. **Cause, measured from the client's own
memory and our wire (§7.6, §7.7):**

1. At cast start our server sends generic-value **property 8 → 1**. That sets
   `byte[ChCliBase+0x64]` bit 0 — **GATE B** of the local walk-start applier
   `0x0081A8F0`. Correct behaviour: it is what an action hold is *for*.
2. The movement press re-dispatches once, the applier reads the gate **still
   set**, and bails at `0x0081AD0F`. The key edge is spent.
3. Our `[8→0, 59, E2]` clears the gate ~a frame later — **but the client's
   applier already ran, in its own frame, a full round trip earlier. No answer
   content can win that race** (which is why R1's zero bytes froze, R2–R4's
   leads only moved the body by *ordering* it, and R6 was irrelevant).
4. **Nothing re-runs the walk-start**, because the movement input path is
   **level-sampled per frame and gated on the DIRECTION CHANGING**
   (evaluator `0x005355C0`, 50 ms throttle; the key-down handler dispatches
   nothing). A steady held key with a steady camera = delta 0 = no
   re-dispatch, however long you hold.
5. A **second press** produces a direction change. So does a **camera turn** —
   and that path passes `arg6 = 0`, sending **no c2s `0x003D`**, so it is
   invisible on the wire. Retail's captures walk on the single press because
   their operator was turning the camera (§7.7 F26: retail walks +28.8 u due
   west and +23.9 u WNW while reporting only a stale *north* vec2).

**Evidence strength:** gate B set at the press → freeze **4 of 4**; clear at
the press → walk **3 of 3** (§7.9 F29). Property 8 drives the bit **5 of 5 and
5 of 5** (§7.6 F22). **And H10 is CONFIRMED by its deliberate run (R9,
§8.2a F32): hold + camera-turn → self-walk 3 of 3, beginning at the gate
clear and BEFORE any wire event; hold + still camera → no self-walk 3 of 3.
The freeze half of the arc is CLOSED, and "not a server bug" is OBSERVED,
not merely supported.** One vocabulary update from the same run: above
gate 1's ~299 u cut the freeze *looks* like "warp back, walk forward,
stop" — that is F27's staleness plus our own grant executing (§8.2a
F32/F33), not a new mechanism.

### THE ONE ACTIONABLE ITEM, and its fix is already built

**CANCELWALK-F28 — the FLOAT-FORWARD is a real defect in OUR server.** The
action hold gates the walk-*start*; it does **not** stop a leg already in
flight. Cast while running and the body glides at **288.0 u/s for the whole
cast** (measured: ~690 u across one cast, velocity never below 288). Guild Wars
stops you when you start casting; we never send anything that does.

**The message that fixes it already exists in the tree** — s2c `0x0028`
AGENT_STOP_MOVING, which **halts when in motion and no-ops when parked**
(schema `GAME_SMSG "40"`). `agents.agent_stop_moving()` is the builder,
`GAME_SMSG_AGENT_STOP_MOVING` the constant, both landed and tested
(`test_cancelwalk.py` §6, floor 46). It was built for **R6** and was VOID there
because it was fired at **stops**, where it can only no-op (§7.4a). **Fired at
CAST START it is the right message for a real bug.**
*Wired 2026-08-24:* **`--cast-stop` (CANCELWALK-R8, §8)** sends it at the
free-caster non-attack cast start, first in the cast-begin tail — refused
without `--zero-lead` and with any other CANCELWALK lever;
`test_cancelwalk.py` §7 drives the lattice and the burst, and the change
survived a three-agent adversarial review (§8.1's residual list is its
yield). ***R8 RAN the same evening (§8.1a): the halt works 3 of 3*** —
speed 288 → 0.0 by the first sample after the burst, zero drift through
the whole cast, standstill/Esc no-ops 2 of 2 — ***but F31: the halt lands
the body on the SYNC COPY's position, a backward snap equal to the copy's
staleness (110–207 u here), not a stop-in-place.*** **RULED 2026-08-25
(PLAN §7 Q10): REFUSED as a ship — "the stock game doesn't warp."** The
halt arm stays runnable as R10's control; the no-warp successor is
**`--cast-stop=pin` (CANCELWALK-R10, §8.3, wired 2026-08-25)**: a
dead-reckoned `0x002C` hard-set at the body's true position first, then
the halt, which then lands on co-located copies and cannot snap.
**R10 awaits its owner-driven run; nothing ships without a ruling.**

### What is CLOSED — do not re-open without new evidence

- Message **order**, answer **timing**, `0x002B`, `0x0025` presence, the
  `0x0027`/speed-base family, property 59, the `≤1.0 u` short-circuit story,
  the dedup gate, GATE A and GATE C (`+0x10C` read **0** in all 552 samples),
  H8 (`+0x50` is a move-request correlation token; nothing branches on it),
  and **any cancel-instant answer content as the fix**. §7.5 has the full list
  with the measurement that killed each.

### What MOVED to another arc

- **The WARP is a grant-cadence defect and belongs to REALFIX, not here**
  (§7.8 F27, §7.9 F30). Our zero-lead policy grants only on c2s `0x003D`, and
  the client only *sends* `0x003D` on direction change — so a long straight leg
  produces ONE report at its start and the sync copy is left behind by the
  whole leg; stops grant nothing at all. The next walk-start reconciles the
  drawn body onto the stale copy in one frame. **Magnitude tracks staleness
  exactly**: 256 u stale → 256 u warp; 31 u stale → 31 u warp. Priced: 5 of 28
  stops leave the copy past ~190 u. Candidates named at §7.8 (`--resync`,
  REALFIX-P5, built and never run, is the only one whose refutation does not
  already stand). **No recommendation made; the ruling is the owner's.**
  *R9's session sharpened the price (§8.2a F33): sep reached 346–555 u at
  ordinary presses — the worst on record — and above gate 1's ~299 u cut
  the client's own reconcile FIRES (observed 7 of 7), so the staleness is
  no longer only a walk-start snap: it detonates on grant arrival too.*

### Instruments, and which to use

- **`toolkit/clientscan/movetap.py`** — the working instrument. Rows carry
  `gate_a/gate_b/gate_c/walk_suppressed` (`controller_read()`, R7 as a poll),
  the R5 field set (`reqtoken`, `dir`, raw stop/point/velocity, both copies),
  and the fence/gate-1/history fields. Needs **no elevation**. Selftest floor
  **250**.
- **`toolkit/clientscan/gatetrace.py` — REFUSES TO RUN, and must stay that
  way** until five measured blockers are fixed (§7.4e). The first would **kill
  the client** on the first breakpoint hit. If a trap is ever genuinely needed,
  rebuild it on `commandertrap.py`'s `HwTrap`, never on the hand-rolled loop.
- `--cancel-answer=…` and `--stop-answer=ack` are diagnostics, off by default,
  refused without `--zero-lead` and refused with each other. `--cast-stop`
  (R8, §8) joins them under the same licensing, refused with either — and it
  shares R6's opcode, so that pair has its own refusal cell.

### The run recipe that works

```
python toolkit/harness/session.py --keep-open --enemy --hold 300 --game-args "--map 280
  --explorable --practice-target --skills 105,153,322"
python toolkit/clientscan/movetap.py --seconds 180
```
**Run both instruments.** A wire-only run cannot tell a walk from a warp
(§7.4c F16) and cannot see the gates. **Walk before each cast** — a standstill
session is zero-exposure for anything movement-shaped (§7.4a). Align the two
captures on the **wall clock** both files carry (`movetap.t` and the gamesrv
origin's `wall_unix`), never by trajectory fit (§7.4d correction 1).

### R8 and R9 RAN and are ruled on; what remains is R10's run (§8.3)

1. **CANCELWALK-R9 RAN — H10 CONFIRMED 6 of 6 (§8.2a F32).** The freeze
   half of the arc is **CLOSED**. Bonus yield: gate 1 caught firing for
   the first time (F33), explaining the operator's "warps" as F27
   staleness (sep 346–555 u measured) meeting the client's own
   reconcile — filed to REALFIX.
2. **CANCELWALK-R8 RAN — the halt works 3 of 3 with cost F31 (§8.1a),
   and the owner REFUSED it as a ship (2026-08-25, PLAN §7 Q10: "the
   stock game doesn't warp").** The successor is wired:
   **`--cast-stop=pin` (CANCELWALK-R10, §8.3)** — dead-reckoned `0x002C`
   re-pin at the body's true position, then the halt.
   **R10 RAN 2026-08-25 (§8.3d) and the mechanism WORKS**: every
   registered bar passed at the four reckoned casts (backward 0.00 on
   all four — F31 dead; the backpedal reckoned at 0.652 exactly; model
   residual −0.1 u), the click-walk suppression fired with no warp at
   the cast, and the operator's warp 11 s later is **F33's
   reconcile-on-answer** meeting 864.5 u of click-silence staleness
   (REALFIX's debt — settled by two blind skeptics from rival ends).
   **The run's own yield is CANCELWALK-F34**: the then-wired bare
   `0x0028` on a refused reckon warped a genuinely PARKED body 167.6 u
   backward onto a still-converging sync copy at a stop-then-cast —
   "no-ops when parked" holds only when the COPY is parked too.
   **FIXED the same day (§8.3e): PIN-OR-NOTHING** — the pair fires
   whole or not at all, a bare `0x0028` never fires, refusals print
   their door to the console. What remains is the **completion run,
   three reps, §8.3e**: the stop-then-cast F34 regression rep, the
   second-cast rep (forgotten in R10's run), and a 3+ s dead-straight
   leg cast (THIN in R10's run — reports flowed to within 0.97 s of
   every reckoned cast).

### Session handoff, 2026-08-25 — where to pick this up

**Branch `claude/cancelwalk-movement-arc-1fff44`, worktree
`.claude/worktrees/cancelwalk-movement-arc-1fff44`.** The 2026-08-24
list that stood here (fix §8.3a's five findings → re-run the two dead
review agents → re-register → run) is **done through its third item,
2026-08-25 evening**:

1. ~~Fix §8.3a's B1 and B2, then the three REALs.~~ **DONE — §8.3b**,
   with the fixes driven by `test_cancelwalk.py` (floor 82 → 98).
2. ~~Re-run the two review agents that died on a usage limit.~~
   **DONE — §8.3b's re-review block**: the mutation probe went 13 of
   13 RED (the registered M1–M7 plus six over the fixes themselves);
   the lattice/routing skeptic found no blocker, and its 3 REALs +
   2 NITs (banners, a wire-plane test gap, doc staleness, the
   legacy-bool hole, an unfollowable hint) are fixed (floor → 100).
3. ~~Re-register R10's predictions and add a click-walk cast.~~
   **DONE — §8.3c.**
4. ~~The owner-driven run.~~ **RAN 2026-08-25, scored at §8.3d** —
   every bar passed at the reckoned casts, and the run yielded
   **CANCELWALK-F34** (the bare `0x0028` on a refused reckon warped a
   parked body 167.6 u onto a converging copy), **fixed the same day
   as PIN-OR-NOTHING (§8.3e)**.
5. **NEXT: the completion run — three short reps, §8.3e**: the
   stop-then-cast F34 regression rep, the second-cast rep, and one
   cast 3+ s into a dead-straight leg. Score against §8.3e; the
   refusal labels now live on the gamesrv console line, so keep that
   terminal's scrollback (or its log) with the two tapes.

Standing constraints for whoever continues: `test_cancelwalk.py` floor
is **102**; the flag ships OFF and its default is an owner ruling; the
`halt` arm stays runnable as R10's control and is REFUSED as a ship.

---

## 1. Method, and why order claims here are readings rather than inferences

`cmsgstream.timed()` decodes both directions of the live game channel onto one
clock. Messages in one TCP segment share a timestamp, Python's sort is stable,
and per-connection input order is stream-offset order — so equal-time rows
print in **byte order**. Every burst below is one segment. The framing is
exact (the castmech run's connections frame to the last byte, §3f).

## 2. What the handover believed, in three sentences

Mid-cast the client is held and its key-down edge is spent on the cancel;
retail moves the player anyway because its `0x0029` carries a real destination
(+768 u along the heading), a server-authoritative move order; ours grants the
player's own reported position, so there is nothing to walk to. §3g's one
proposed no-warp experiment was message ORDER (grant before vs after the
release burst). §2 of this document exists to be measured against; §3 is what
the measurements actually say, and they overturn most of it.

## 3. Findings

**CANCELWALK-F1 — OBSERVED. Retail's movement answer rides AFTER the release
burst, and our order already matches.** All three movement-triggered cancels
(t=81.660 W, 98.779 click, 128.805 W) and the mid-windup stop (114.641) put
`[8→0, 59(/3), E2]` first and the movement tail (`0x0025`/`0x002B`/`0x0029`)
last, `0x0029` always final. Our §3g answer is the same shape in the same
order (seq 224–228: 8→0, 59, E2, 0025, 0029). This **corrects castmech §3f's
"retail puts the grant first in both" (it had it backwards) and closes §3g's
order experiment at a desk: there is no order delta to test.** The click-arm
note in §3f ("we place the grant before the burst on the click arm") remains a
real fidelity mismatch on that arm, cosmetic until shown otherwise.

**CANCELWALK-F2 — OBSERVED. The mid-action `0x003D` reports a LATCHED heading,
and retail's cancel-instant grant is that stale vector applied blind.** vec2 is
bit-identical `(13.093545913696289, 767.5670776367188)` at t=64.757 (the last
report of the pre-cast walk), 81.625, 114.609 and 128.774 — three presses
across 47 s carrying one stale value — and the backpedal press at 108.336
carries its exact negation with mt=4. The granted destination is
`reported + vec2 + 0.5·û` **exactly, 3 of 3** (2315.182, 2779.766, 2780.207
in y) — REALFIX's D1 formula, confirmed at cancel instants. So retail's
"lead" points wherever the client last walked, not where the player is going:
ordinary heading-arm bookkeeping, not an authored move order.

**CANCELWALK-F3 — OBSERVED. The retail client does NOT walk toward the
granted point; it self-walks its own live direction the moment the burst
clears the hold.** At t=128.805 the grant points `(+0.017, +1.000)` and the
client walks 23.8 u in `(-0.787, +0.617)`; at t=114.641 same grant direction
and the client walks 28.8 u due west (cos ≈ 0). At t=81.660 the walk tracks
the grant ray exactly (cos = +1.000) — but that is the unmoved-camera case:
the player had just walked north and never turned, so own-direction ≡ the
latched vec2 ≡ the grant direction, all one quantum. Walk distances match the
key-held window at run speed (95.9 u ≈ 0.33 s × 288; 23.8 u ≈ 0.10 s × 288),
and each release produces `0x0047`, answered by a stop re-pin. **This refutes
§2's mechanism sentence: the destination does not steer the body. The
`0x0029` moves the sync copy and nothing else — REALFIX-O1's model, holding
even at the cancel instant.**

**CANCELWALK-F4 — OBSERVED. `0x002B` is movement-family bookkeeping, not a
cancel message, and it is not the enabler.** It appears exactly on family
transitions: `[1.0, 1]` when a stop-family gives way to movement (98.779,
128.805), `[1.0, 9]` answering `0x0047` stops (64.356, 82.037, 109.376,
114.782, 128.955), `[0.66, 4]` at the backpedal press (108.376) — **a live
wire witness for REALFIX-P1's CONTESTED `FAMILY_RATE` row 4:0.66**. The W
cancel at 81.660 carries **no** `0x002B` and the client walks; our client has
never received one and self-walks normally. Refused as the missing message.

**CANCELWALK-F5 — OBSERVED. Retail's stop answer has a second form.** At
65.095 a `0x0047` stop is answered by bare s2c `0x0028 [agent]` — no
`0x002B`, no re-pin — where every other observed stop gets
`0x002B [1.0, 9]` + zero-distance `0x0029`. What selects between them is
unread. Caveat to REALFIX-P1's stop-arm note ("NEVER `0x0028`"), which is
right about the c2s side and now needs this s2c footnote.

**CANCELWALK-F6 — OBSERVED. The freeze survives ~25 client frames, killing
every timing hypothesis.** Ours, t=5.417: the mid-cast W arrives as `0x003D`
(mt=1), our answer goes out in the same instant in retail's order, and the
client holds the movement episode open to t=6.234 (`0x0047`, **same
coordinate, 0.0 u**) — 0.818 s with the key down, the hold released (§3g:
the animation stops on screen), and zero motion. A same-frame race cannot
explain 25 frames of stillness. The second press (t=7.502, mt=4) gets the
same-shaped zero-lead answer and walks immediately — so nothing about our
answer freezes an ordinary press; only the cancel instant is broken.

## 4. Elimination

Four observations bound the answer: retail cancel 1 walks, retail cancel 4
walks, our cancel press freezes, our ordinary press walks.

| candidate delta | vs retail c1 (walks) | vs retail c4 (walks) | verdict |
|---|---|---|---|
| message order | identical (F1) | identical (F1) | **eliminated** |
| `0x0025` presence | retail c1 has none, we send one | retail c4 sends one too | eliminated — present and absent both walk |
| `0x002B` missing | c1 walks without it | c4 has it | eliminated (F4) |
| answer timing | +35 ms vs same-instant | same | **eliminated** (F6: 25 frames) |
| `0x0029` destination | **they lead, we zero** | **they lead, we zero** | **the only delta present against BOTH** |
| build 38849 vs 38797 | — | — | residual; unfalsifiable on loopback |
| cast-start state | start bursts match structurally (E4/A2 62/A0 60/9F 8→1; retail adds A2 44 on the *target*) | same | residual |

The destination delta survives — but F3 forbids the handover's reading of it
(the client does not walk *to* the grant). What is left is a narrower claim:

**CANCELWALK-H1 (primary) — RECONSTRUCTION.** While the client has a mid-hold
movement request outstanding (its `0x003D` sent during an action hold), a
`0x0029` granting a point at its own reported position reads as *refusal —
stay put*, and a grant strictly ahead reads as *permission* — after which the
client self-walks its own direction (F3). Ordinary presses are not gated
because no request is outstanding (F6's second press).

**CANCELWALK-H2** — the compound (a `0x0025` present with no `0x002B`)
freezes it; needs two coincidences retail never exhibits together; disfavored.

**CANCELWALK-H3** — the client's movement lock is set wrong at CAST START,
and no cancel-instant answer can clear it; the visible candidates (A2 44
rides the target; property 62's value encoding) touch nothing movement-shaped.

**CANCELWALK-H4** — build drift between 38849 and 38797 in the resume path.
Movement code this old drifting between adjacent builds is unlikely; noted
because nothing here can falsify it.

## 5. Pre-registered runs — predictions first, one change per run

All on loopback, operator-driven (world-anchored input; the §3g protocol),
Isle of the Nameless, ≥3 cancelled casts per run. **Readout is the wire, not
the screen**: a run PASSES a cast if the client's own reports move ≥ 30 u
within 0.5 s of the cancel press with no second press; ≤ 5 u is a freeze.
Each run also includes one **direction-discriminator cast**: rotate the
camera ≳ 90° after the previous walk, then W mid-cast — the latched vec2 (and
so any granted lead) then points away from the camera's W, and the walk
vector names which one the client obeyed.

- **CANCELWALK-R1 · `--cancel-answer=suppress`** — the release burst alone at
  the cancel instant; no `0x0025`, no `0x0029` on that report. Zero warp
  exposure (we send less; the copy just keeps its park).
  *Predictions:* H1 → **freeze** (no permission at all; sharpest H1 test in
  the refusal direction). H2 → **walk** (the freezer is withheld). H3/H4 →
  freeze.
- **CANCELWALK-R2 · `--cancel-answer=retail-lead`** — retail-verbatim tail at
  the cancel instant only: `0x0025` (heading-change-gated as now), `0x002B
  [1.0, mt]` on family transition, `0x0029` at `reported + vec2 + 0.5·û`.
  **Diagnostic, never ship** — this is the refuted lead family, licensed for
  one instant on loopback because the readout completes before any cost
  lands. *Predictions:* H1 → **walk on the single press**, and the
  discriminator cast walks in the CLIENT's direction, not the grant's (F3
  reproduced on our build). H2 → walk (the `0x002B` completes the compound) —
  R1 separates. H3/H4 → freeze.
  *Pre-registered cost:* the copy bakes a ≤ 768.5 u leg along a stale vector.
  Under `--zero-lead` + no stop echo nothing re-pins it until the next
  accepted report's grant (rate floor 0.5 s), so a `+0x48` resync inside that
  window may snap visibly (p50 re-arm 2.89 s says usually it will not). A
  warp AFTER the walk readout does not bear on the walk verdict; it is the
  known price of leads and the reason R2 cannot ship.
- **CANCELWALK-R3 · `--cancel-answer=lead:16`** — run only if R2 walks and R1
  froze: same tail with the lead cut to 16 u. *Predictions:* H1-binary (any
  nonzero offset is permission) → walk; H1-with-threshold → freeze, and the
  threshold gets bisected. A 16 u lead at a provably-stationary instant is
  the only form with a shippable safety story: the copy's excursion (≤ 16 u
  past the player) is smaller than the ~86 u park-lag the shipped
  configuration already carries at every stop (measured in the §3g capture:
  the copy parks at the last granted point, 86.2 u behind where the player
  stopped), and the next report re-pins it.

**Decision table.** R1 walks → the fix is deletion (suppress the
cancel-instant grant); ship after a REALFIX-style composition audit. R1
freezes + R2 walks → H1 confirmed; bisect with R3 toward the smallest
permission that walks; any shipped form needs its own REALFIX audit (O5 is
not by-witness for a led point; the stop-arm re-pin question re-opens because
retail's own hygiene pairs cancel-leads with stop re-pins). R1 and R2 both
freeze → content at the cancel instant is insufficient; the arc moves to H3
(compare cast-start values field-by-field against retail's; then the client's
input latch via the clientscan/trnhook tooling) with H4 logged as the
residual. **No arm ships from this ladder directly; a run's PASS licenses a
candidate, and shipping stays a separate, audited step** — the lead family's
refutation stands for every steady-state grant regardless of outcome.

## 5a. R1–R3 RAN, same day — H1 confirmed sharper than predicted (2026-08-24)

Operator-driven, loopback, Isle pin, captures
`authsrv-20260824T095712` (R1), `100352` (R2), `100643` (R3);
`score_runs`-style readout of every cancel instant, press, answer and the
motion after.

- **R1 suppress: FROZEN, 2 of 2** — burst-only answers, 0.0 u at the release
  report both times. **CANCELWALK-H2 is REFUTED** (it predicted a walk).
- **R2 retail-lead: WALKS, 3 of 3 — to the granted point exactly.** Cancel 3
  lands at **+768.1 u, the granted coordinate to the decimal, and parks
  there** (four consecutive reports at the same point). The release arrives
  mid-glide (`0x0047` at +0.08 s, +19 u) and the body glides on regardless.
  The leg is straight and unclipped — the operator walked through stair
  collision. **H3/H4 in their strong form ("no cancel-instant answer can
  unfreeze") are REFUTED.**
- **R3 lead:16: WALKS 16.0 u exactly and parks, 2 of 3** — key still held,
  nothing until a fresh edge. (The third cast's 96 u run contains a second
  press: a mid-walk `0x003D` edge at +0.25 s.)

**CANCELWALK-F7 — OBSERVED, and it reframes H1.** At the cancel instant our
client (build 38797) executes the answering `0x0029` as a **click-order**:
it walks the granted leg to completion, straight-line, key state ignored,
and parks at the granted point. Zero-lead = "click where you stand" = the
freeze. This is the click arm's own mechanism expressing on the heading arm
at the one instant the client is not self-driving. Two corollaries: the mid-
cast vec2 on OUR build is **live**, not retail's latch (every walk went the
way the operator pressed — R2 cancel 2's vec2 points where the operator had
turned), and the pre-registered warp cost never materialised — the body
walks the leg WITH the copy, so nothing diverges to snap.

**The residual retail divergence stands, now cleanly bounded**: retail's
38849 client walked its own live direction *against* the grant (F3) and
stopped on release; our 38797 walks the grant and ignores release. Same
answer shape, different client behaviour — build drift (H4) or unread
client state (H3), and for OUR pinned build it no longer matters: the
contract is measured, and the server can be built against it.

### CANCELWALK-R4 · `--cancel-answer=<lead-form>,stop` — pre-registered before its run

What stock feel still lacks under a bare lead: release-to-stop. R2's own
capture supplies the trigger — the client **reports the release mid-glide**
— and retail's stop arm answers every such report with `0x002B [1.0, 9]` +
a zero-distance `0x0029` re-pin (F4/F5). R4 sends exactly that pair,
**scoped to the in-flight cancel leg**: a window armed at the lead send
(leg ÷ 288 u/s + 1 s slack), consumed by the first `0x0047` inside it,
cleared by any subsequent grant. The general stop arm stays silent —
`--stop-echo`'s refutation (teleport 9.9 s later, walk back) was measured
in ordinary self-driven play, which the window never covers, and the re-pin
is a zero-distance order at the client's **own** reported point, which
cannot move anybody even if this reading is wrong.

*Predictions:* release mid-leg **stops the body at the reported point**; a
press held past the leg still parks at the lead, its window expiring
unconsumed; the leg still cannot be steered mid-flight and still crosses
geometry (unclipped — a ship-time clip is a named open term, priced by the
stairs observation). If the body
does **not** stop, a zero-distance order does not supersede an executing
leg, and the stop side moves to a client read. *Registered lead for the
run: 288 u ≈ one second of walking — long enough that a normal press-and-
release never parks, short enough that a hold parks in ~1 s.*

### 5b. R4 RAN — every prediction confirmed, operator and wire agreeing (2026-08-24)

`--cancel-answer=lead:288,stop`, capture `authsrv-20260824T103556-c1`, three
cancelled casts. **Tap:** the release reports +97.6 u mid-glide, the
`CANCELWALK STOP` re-pin answers it (t=9.555), and the next report three
seconds later is at the **same point** — release-to-stop works, and R2's
identical release (answered with nothing, glide to 768) is the control.
**Held:** both casts park at **+288.0 u exactly, the granted point to the
decimal**, stop windows expiring unconsumed (0x0047 at +3.76 s and +2.05 s,
both past the 2.0 s window, neither needing an answer). Operator report:
"worked as you described." **CANCELWALK-R4 PASSES.** The licensed ship
candidate is: cancel-instant lead + scoped stop re-pin. Ship-time terms,
unchanged: clip the leg (the stairs phasing is real — and the clip must
measure from the REPORTED point, not our model's), choose the lead
(288 = park after ~1 s of held walking; retail's 766 triples the runaway),
promote the flag out of the experiment namespace, and the audited-exception
review against REALFIX's zero-lead invariants. **Defaults are an owner
ruling in this repo; none is made here.**

## 6. Against the handover's three questions

1. *Is a lead grant safe in this one instant?* Reframed: the lead does not
   steer the body (F3), so "safe" is the wrong first question — the live
   question is whether it is the **permission** the client waits for (H1).
   Safety-wise, a bounded lead at a stationary instant costs less than the
   copy's existing ~86 u stop-lag; 768 u along a stale vector remains
   diagnostic-only.
2. *Does order matter?* No — closed at a desk (F1). The §3f order claim was
   backwards; ours already matches retail.
3. *Is there a third message?* No. `0x002B` is family bookkeeping (F4),
   refuted as the enabler by retail's own cancel 1; the only other batch
   member is the heartbeat `0x001E`. Retail's cancel answers contain nothing
   else.

## 7. The state-diff round — the wire closes, and the gate asymmetry is read (2026-08-24)

R2–R4 solved the freeze on our pinned build; what they left is §5a's residual —
at the cancel instant our 38797 client executes the grant as a click-order while
retail's 38849 self-walks its live direction — and the premise, forced by R1/F1/F6,
that the differentiator is PRIOR STATE, not the cancel-instant answer. This round
diffed that prior state from both ends at a desk: the wire (retail `20260824T074002`
vs ours `captures/gamesrv/authsrv-20260824T081335-c1` and R1's `…095712-c1`) and
the pinned 38797 binary (`vault/client/2026-07-29_221c13772c7a/Gw.exe`, read-only).
Method notes that carry: the retail capture holds TWO game connections and the
outpost's own "agent 25" is an unrelated creature — every row below is the
explorable connection's, split first; ours decoded 617/617 and 5364/5364 with zero
residual bytes. Every load-bearing claim was adversarially re-derived by an
independent agent (the wire diff by raw-histogram recount; the two binary reads
instruction-by-instruction), and the client-side reads were in fact performed
TWICE by independent readers — every structural claim below reproduced in both.

### 7.1 Findings

**CANCELWALK-F8 — OBSERVED (skill identity UPSTREAM/CORROBORATED). The `0x0027`
"best lead" is dead: the pre-first-cast cluster is the scheduled expiry of a
Windborne Speed enchantment, not cast preparation.** The apply burst sits at
t=53.605: `0x0042` BUFF_ADD `[25, skill 160, rank 15, buffId 54, f32 13.0]`, two
prop-6 visual-effect adds (ids 13, 11), `0x00F1 [25, 128]`, `0x0027 [25, 383.04]`
(= 288 × 1.33). t=66.587 is its exact mirror — `0x0044 [25, 54]`, prop-7 removes
of the same ids, `0x00F1 [25, 0]`, `0x0027 [25, 288.0]` — at Δ = 12.982 s against
the decoded 13.0 s duration. Skill 160 = Windborne Speed (UPSTREAM, GWCA
`Skills.h`; the +33%/13 s arithmetic is OBSERVED). Corpus scale: 473 `0x0027`
across 20 live captures, **281 targeting non-player agents**, cycling ~13.0 s
wherever the buff is maintained, never cast-adjacent; in `074002` the session
holds three `0x0027`, all in the first 15 s of the connection, and nothing recurs
within ±5 s of any later cancel. The first cast landing 277 ms after the expiry
is an independent 13 s clock coinciding, not a trigger. The expiry precedes the
first cancel press by 15.0 s of silence.

**CANCELWALK-F9 — OBSERVED. The pre-press state diff, verified by independent
recount: value-parity on every wire-written field checked, AND three retail-only
movement-machine regimes we have never sent.** Parity first: `0x0020`
WORLD_CREATE_AGENT is byte-identical bar agent id and facing — same type dword,
**same 288.0 base speed** (our `agents.py` DEFAULT_RUN_SPEED seeds it; there is
no client-side 288.0 default — `0x43900000` appears nowhere in the image, positive
control 100.0f found 264×, and the constructor `0x005FDE30` seeds BOTH world
copies from the create message); `0x0199` INSTANCE_LOAD_INFO identical
`[409,1,280,1,0,0,0]`; both status words 0 at press; both buff lists empty at
press. Our two captures' pre-press inventories are structurally identical to each
other, so the hand-off is deterministic. The retail-only movement set (full-file
census on ours, positive-controlled):

- **`0x0028` AGENT_STOP_MOVING `[25]` ×1 at t=65.0948**, 36.8 ms after the
  player's own `0x0047` stop — the LAST movement-family s2c before the casts
  (F5's second stop form). Ours: zero, ever; our pre-cast stop was answered by
  nothing but heartbeat.
- **`0x002B [rate, family]` ×4** to the player, including `[1.0, 9]` at 64.3555
  answering a stop, **paired with a zero-distance `0x0029` re-pin at the stop's
  reported point** (0.0 u). Ours: zero, ever.
- **The led/re-grant regime**: 18 player grants pre-burst for 13 `0x003D` +
  3 `0x0047`, leads 169.6–1086.4 u, plus 4 strictly-unsolicited mid-leg re-grants
  (54.786, 57.524, 59.872, 64.273) keeping the sync copy continuously led. Ours:
  strictly one zero-lead grant per accepted report, plane 0, throughout.

Two textures recorded, not elevated: our `0x0025` sometimes rides reports that
get no `0x0029` (retail's six all co-time with grants) — cadence is plausibly
exposure, UNVERIFIED as mechanism; and an exposure confounder — retail cancels
its SECOND cast after a completed first, ours cancels the first-ever cast of the
session — closable in one loopback run (complete one cast before the cancelled
one). A prior inventory's "missing prop62" delta was a mis-decode and is
corrected: both sides send prop62 (retail −0.5 = 10/20 pool, ours −0.4 = 10/25);
the cast-start bursts match structurally.

**CANCELWALK-F10 — OBSERVED, twice-read and twice-verified. The `0x003D` emitter
funnel is unique, and the SEND gate and the WALK gates are different tests on the
same controller object — the exact shape of "sends the report, does not walk."**
The only 0x003D wire-buffer builder in the image is the 28-byte packer
`0x009206D0` (`{op 0x3D, pos.xy, plane, dir.xy, mt}`; the adjacent `0x00920720`
is the 16-byte `0x003E` builder — the family is a positive control). Its single
caller chain: key-edge layer (5 sites + one vtable slot) → MOVE-CMD `0x00535380`
(direction-changed flag, last-dir cache `0xC07C2C/30/34`) → MOVE-DISPATCH
`0x008163A0` → packer → channel send `0x007DCF00`. The report's POSITION operand
is sampled from the **ASYNC (drawn) body** (`[mgr+0x14C]` via `0x005FC400`) — the
binary root of "a held client reports a latched point." Inside MOVE-DISPATCH the
local self-walk is applied by `0x0081A8F0` on `context->playerControlledChar`
(assert-witnessed) BEFORE the send, and the send fires iff the direction-changed
flag is set — **independent of whether the walk started**. The walk applier
bails to `0x0081AD0F` (which stashes an +inf "no heading" sentinel into
controller `+0x694/+0x698`, arms nothing, and still returns into the send path)
on any of: **GATE A** `[ChCliBase+0x10C] & 0x100` (`0x0081A931`) — read at
exactly TWO sites image-wide, this applier and the `0x003E` applier `0x0081AEE4`,
against a 285-site census of `+0x10C` accesses: a dedicated suppress-self-walk
bit; **GATE B** `byte [ChCliBase+0x64] & 1` (`0x0081A93C`) — semantics
UNVERIFIED, and a DIFFERENT field from AgAgent+0x64 and from AgentView+0x64, do
not conflate; **GATE C** bit 4 of the same word — excluded at cancel instants
because the pre-send gate tests the same bit and the send fired. Deeper in the
survivor path sit the navmesh query (`0x709D30` == 0 exits early with no flag
set) and **GATE-A′, the dedup**: `0x0081AA5B` skips ASYNC-MOVE-START when the
new direction is within epsilon of the cached one AND the mode is unchanged.
**No writer of GATE A's bit or GATE B's bit was found** — no `or`/`bts` idiom
touches them; `+0x10C` is initialized wholesale from an agent-type template at
construction (`0x0081A609`) and reassigned wholesale (`0x00F1`'s handler stores
the word, F9: value 0 on both clients at press). The suppress state, whatever
sets it, is a **local client write no capture can carry**.

**CANCELWALK-F11 — OBSERVED (mechanism), CORROBORATED (in-tree prior). The async
body's drivability is a latch: ASYNC-MOVE-START `0x005FC6E0` arms
`clientControlled = 1` (AgTrack record +0x00, setter `0x00605F10`, input-only
call sites — the `0x0081AA88 → 0x005FC6E0` chain PROBE-GATEFIRE already named)
and writes the body's facing via `0x00602660`; the clearer `0x00605F70` runs on
the server-grant SNAP branch (`0x0060602E`).** An unarmed body is grant-driven —
which is F7's click-order shape. Two scope notes, both load-bearing: the latch is
armed only through the gated applier path, so "latch clear at the press" is the
downstream OBSERVABLE of any upstream bail, not a rival cause; and press-time
snap-clear cannot be the freeze mechanism — R1 sent ZERO bytes at its cancel
instants and froze anyway.

**CANCELWALK-F12 — OBSERVED. Property 59 is AgentView-only and closes as a
movement candidate.** Full depth, both readers agreeing: `0x007E01B0` →
`0x00802160` (resolver, type-1 check, silent no-op on miss) → `0x007F76A0`
(kind 0x17 skill_stopped) → `0x007F2E90`: one 0x48-byte event record spliced
onto the per-view action queue and the global sequence list. Complete store set
= the record + two queue tails. No movement field, no command-layer call, no
`+0x64`, no `+0x10C`; the hold release belongs to property 8's `→0` (§16.2's
read). Positive control: the same method finds the sibling paths' extra stores.

**CANCELWALK-F13 — OBSERVED, verifier corrections carried. The s2c `0x0027`
receive path is read to its leaves and the store is value-equal on both builds;
the message is dead as a differentiator in both directions.** Handler
`0x005FD700` applies setter `0x00602910` to the SYNC then the ASYNC copy; the
setter's only direct field store is an unconditional `fstp [esi+0x5C]`
(`0x00602947`); it calls the settle `0x005FF880` (which dead-reckons `+0x78`
ONLY when `+0x48 ≠ 0` — **REALFIX-P4's "`0x00602910` rewrites `+0x78`" is
refined: the rewrite is the settle it calls, gated on an armed leg**) and
re-issues the outstanding grant only when the target is not the +inf sentinel.
On a parked agent the message reduces to storing 288 over 288. Readers of
`+0x5C`: the destination bake and the avoidance predicate (shared by every
movement path including the self-walk) **plus a third reader the first census
missed, in AgTrack at `0x00605897/9F`** — the unqualified "only readers" form is
retired. The elimination is reader-independent: both copies hold 288.0 from our
own create (F9), measured 4,115/4,115 in movetap samples on a build that has
never received a `0x0027`. Do not build a `0x0027` sender to fix cancelwalk;
REALFIX-P4's DO-NOT-BUILD stands reinforced.

**CANCELWALK-F14 — OBSERVED. The cancel-instant zero-lead grant takes the
ordinary BAKE arm at 86.18 u — the handover's ≤1.0 u short-circuit
reconstruction is refuted — and the freeze reframes: the drawn body is already
standing on the destination.** Instrumented replay of `grantsim.simulate()`'s
own locals (arm counts cross-validated against the function's own tallies):
`081335`'s four player grants are `t=3.466 |d|=0.0` (seed), **`t=5.418
|d|=86.18` BAKE (the cancel instant)**, `t=7.502 |d|=0.0` (post-arrival
re-issue), `t=12.308 |d|=89.53` (ordinary heading grant). The copy was parked at
the seed because keyboard walking had sent it nothing (one report refused
`heading-rate`); the grant's destination is the player's own reported point, so
the sync copy walks an invisible 86 u catch-up leg that ends under the player's
feet while the screen shows nothing. R1's capture confirms zero cancel-instant
bytes at the verdict log (`cancelwalk-suppress, fired:false`), with five
ordinary pre-cancel grants (0.0/173.5/56.6/103.0/37.0 u).

**CANCELWALK-F15 — OBSERVED. The frozen press fired BOTH dedup legs, so the
bail is upstream of the dedup — the suppress gates (or the navmesh exit), not
the direction cache.** At the canonical freeze (`081335` t=5.417) the press
carried vec2 `(765.2, −46.0)` (≈east), mt=1; the pre-cast walk's last leg
(t=3.748) was `(555.5, −529.1)` (≈SE), mt=3 — **cos ≈ 0.76 (~40°) off the cache
AND a mode change**. GATE-A′ skips only on direction-within-epsilon AND
mode-unchanged, so had control reached it, ASYNC-MOVE-START would have run and
armed the body. Zero motion for 25 frames says control never got there. The
navmesh variant survives only in a direction-dependent form: the second press
walked from the bit-identical coordinate 2.085 s later (mt=4, ≈NW), so a
position-keyed navmesh zero is excluded by F6's own instants.

### 7.2 The join

The wire says (F9) retail's client entered its cast with the movement machine
explicitly closed — a `0x0028` stop-ack, `0x002B` family writes, a continuously
led sync copy — and ours entered with none of that ever written, at value-parity
on every field a message carries. The binary says (F10/F11) the local walk-start
reads controller state the send path never reads, its writers are local, and the
body's drivability is a latch armed only through that gated path. Those are one
claim from two ends: **the differentiator is client-local state the walk gate
reads and the wire does not carry; the only wire-shaped candidates left are the
stop-closure/family messages whose HANDLERS may write that state — unread — and
everything value-carried is eliminated.** The wire front is otherwise closed.

### 7.3 Surviving candidates, ranked

Constraints any candidate must satisfy: R1 froze with zero cancel-instant bytes;
the second press walks ~2 s later from the same coordinate; retail self-walks
the same edge; F15's bail is upstream of the dedup.

1. **CANCELWALK-H5 (primary) — RECONSTRUCTION.** GATE A (`+0x10C` bit 0x100) or
   GATE B (`+0x64` bit0) is SET on our build when the cancel edge runs the
   applier — set at/for the cast hold, cleared by the time an ordinary press
   works — while retail's client reaches its cancel edge with the bit already
   clear. The writer is untraced (F10: wholesale template/word stores only).
   *Refuted by:* the bit reading CLEAR at a frozen press (R7), or R5 showing the
   walk-start signature present.
2. **CANCELWALK-H6 — RECONSTRUCTION.** Stop-closure prior state: our client
   enters the cast with its last movement episode never server-closed (no
   `0x0028`, no `[1.0,9]`+re-pin — F9), and whatever state that leaves is what
   keeps H5's bit set (or otherwise blocks the applier) at the cancel edge on
   our build only. This is the only surviving candidate the SERVER can act on,
   and it is cheap to test (R6). *Strained by:* the second press walking with
   the episode equally unclosed. *Refuted by:* R6 still freezing.
3. **CANCELWALK-H7 — RECONSTRUCTION, weak.** Direction-dependent navmesh/path
   degeneracy at the press instant (the query's inputs include the heading;
   position-keyed forms are excluded by F15). *Refuted by:* R5 showing no
   walk-start signature (a gate bailed before the query), or R7's bit read.
4. **CANCELWALK-H4 (residual, carried).** Build drift in the cast-hold/resume
   path. Unfalsifiable on loopback; moot for our pinned build (the R4 contract
   stands regardless).

Episode-level companion, not a press-time rival: the latch snap-clear (F11)
explains why the body stays grant-driven for a whole R2–R4 leg, but R1 kills it
as the freeze mechanism.

### 7.4 The next instruments — pre-registered before any run

**CANCELWALK-R5 · the movetap state poll (the owner-offered run).** Loopback,
Isle pin, shipped `--zero-lead` (the freeze must occur), ≥3 cancelled casts plus
one ordinary-press positive control in-session; cast/cancel input operator-driven
per the §3g protocol; the poll is a fixed memory readout and agent-pilotable.
movetap already fetches the full 0xD0-byte AgAgent block for BOTH copies every
poll, so **Tier 1 is decode-only, zero new cross-process reads**: expose async
`+0x48/+0x78/+0x7C/+0xB0/+0xB4/+0x9C/+0xC4`, plus `+0xBC/+0xC0` (facing cache)
and `+0x50` (the move-request correlation token allocated at the walk-start,
zeroed by the halt `0x005FC5C0`) on both copies. **Tier 2** (only if Tier 1
leaves the ranking open): `clientControlled` = AgTrack record +0x00 — movetap
already resolves AgTrack for its fence walk, check whether rec+0x00 is already
in hand before plumbing anything. The ChCliBase bits themselves are a different
object movetap does not resolve; that read is R7's.
*Predictions:* H5/H6 (bit set) → walk-start signature ABSENT at the frozen
press: async `+0x50/+0xC4/+0x60` unchanged across the press, velocity stays 0,
`clientControlled` stays 0 — while the ordinary-press control shows all of them
change within one poll (control fails ⇒ the run is void, not confirmatory).
H7 → signature PRESENT but degenerate: `+0x50` takes the press's mt yet no leg
bakes. Either way the facing pair classifies its own writer: updating at the
frozen press puts it before the gates (timeline marker); only at the ordinary
press, behind them (second signature bit).

**CANCELWALK-R6 · the stop-closure run (cheapest, and the only server-side
lever left).** One loopback run with a diagnostic arm that answers the pre-cast
`0x0047` the way retail answered its last one — a one-shot `0x0028 [agent]`
(and, as a second arm, retail's other form: `0x002B [1.0, 9]` + zero-distance
re-pin) — everything else the shipped zero-lead configuration. *Predictions:*
H6 → the single mid-cast press now WALKS; H5-without-H6, H7, H4 → still
freezes. A freeze here also retires F5's residual ("the one unread player-
targeting pre-press delta") as a cancelwalk candidate. The same session can
close F9's exposure confounder: complete one cast before the cancelled one.
**BUILT same day: `--stop-answer=ack`** — s2c `0x0028 [player]` answering
EVERY player `0x0047` (the server cannot know which stop precedes a cast, and
the handler no-ops on a parked body, so every-stop is one-shot-equivalent at
zero warp exposure; the schema's own handler read says the halt zeroes the
queued-move store `agent+0x50`, the very field R5 samples). Refused without
`--zero-lead` and with `--cancel-answer` (one lever per run); `repin` is
**deliberately unbuilt and refuses with the reason** — answering ordinary
stops with `[1.0,9]`+re-pin is the refuted `--stop-echo`'s wire effect, which
R4 escaped only by scoping to an in-flight leg, and a pre-cast stop cannot be
scoped that way; if ack freezes and the repin form is still wanted, it gets
its own licensing paragraph here first. `test_cancelwalk.py` §6, floor 46
after the adversarial review pass (two agents at f08d69a: the flag lattice
enumerated and every illegal cell refused exactly once, the licensing
argument verified at code level — 0x0028 is not in `_note_wire_move`'s
opcode set, so no grant clock — and a five-mutation probe; its one REAL
finding, a payload corruption the wire-shape check could not see, closed by
routing the send through `agents.agent_stop_moving()` and driving that same
builder from the test). The run command, operator-driven:

    python toolkit/harness/session.py --keep-open --enemy --game-args "--map 280
      --explorable --practice-target --skills 105,153,322 --stop-answer=ack"

**CANCELWALK-R7 · the flag read at the edge.** If R5 lands signature-absent and
R6 freezes: read `[ChCliBase+0x10C]` bit8 and `[ChCliBase+0x64]` bit0 at a
frozen press — one-shot int3/trnhook at `0x0081A931`/`0x0081A93C` (arm before
launch; the injection window is map-load), or plumb the controller object into
movetap. This separates H5's two bits from each other and from H7 directly.

**R5's Tier-1 instrument is BUILT (2026-08-24), owner's choice after R6.** The
fields land in `movetap.sample()` as decode-only additions — every byte was
already inside the `0xD0` block the poll fetches for **both** copies, so the
read budget is unchanged (the check asserting that is in the section below).
Row keys, per copy: `reqtoken` (`+0x50` — **this doc called it `planner` for
one day and the noun was WRONG; §7.4d has the corrected read**: it is the
move-request correlation token the applier allocates per SUCCESSFUL walk-start
call, so `0 → N` detects that the applier RAN and nothing branches on it),
`dir` (`+0xBC/+0xC0`, the facing pair), and raw `stop`/`point_raw`/
`vel_raw` — raw rather than dead-reckoned, because `position_at` advances on
the world clock alone and would show motion on a body that never moved. The
twin's are prefixed `async_` and come out of `gate1_read`, where its block is
already in hand. `test_movesync.py` §17 wraps the 9-check section with two
controls that redden it on a one-dword offset slip — the failure that would
**void** R5 rather than break it, since a wrong offset returns a confident
never-changing number, which is exactly what H5 predicts.

*The readout, and it is a DIFF across one press instant, not a level:* sample
through a cancelled cast, then compare the row before the press with the rows
after. **H5/H6 → signature ABSENT**: `async_reqtoken`, `async_dir`,
`async_vel_raw` and the async mode all unchanged across the frozen press (the
applier bailed before any store). **H7 → signature PRESENT but degenerate**:
`async_reqtoken` takes a fresh value and/or `async_dir` turns to the press's
heading, yet `async_vel_raw` stays `[0, 0]` and no leg bakes. **The
positive control is mandatory and interpretive, not confirmatory**: one
ORDINARY press in the same session must move all of them within a poll — if
it does not, the instrument is not reading the walking body and the run is
VOID, which is a control interpreting a null and has no authority over any
positive. R6's own lesson applies to the protocol: **the operator must walk
and stop before the cast**, so the session contains a real walk for that
control and the pre-cast state matches the canonical freeze rather than
R6's standstill.

### 7.4a R6 RAN — VOID for H6 (zero exposure), but a clean standstill freeze that weakens H6 (2026-08-24)

`--stop-answer=ack`, capture `authsrv-20260824T135521-c1`, operator-driven, map
280 explorable (`INSTANCE_LOAD_INFO [409,1,280,1,0,0,0]`, identical to R2/R4;
the jsonl header's `map_id 148` is the login-outpost handshake). Six operator
actions, all present on the wire: one normal cast (t=20.5, completes with E5 at
22.5 and E3 recharge at 23.3), one Esc cancel (t=32.2), two W taps (37/38 and
43/45), one W hold (cast 53.7, press 54.7, released 57.0 — held 2.2 s), one
camera-rotated W hold (cast 63.8, press 64.9 — vec2 `(46.0, 765.8)`, rotated
~90° off the earlier `(766, ±14)`, so the discriminator's camera turn is
confirmed on the wire). **The arm fired: five s2c `0x0028 [1]` stop-acks, one
per player `0x0047`.** Every movement cancel **FROZE, 0.0 u** (4 of 4): each W
press reported the spawn point, was answered with the burst + zero-lead grant +
stop-ack, and the client's own next `0x0047` re-reported the same spawn point.
Operator: "didn't move at all, for any command." The wire agrees.

**But the run is VOID as a test of H6 — zero exposure — and the reason is a
pre-registration miss.** The operator cast from a **standstill**: every position
report all session is the spawn `(-6036.0, -2519.0)`, distinct positions = `{spawn}`
(contrast the canonical freeze `081335`, which walked through **8** distinct
positions before its cast). The `0x0028` handler halts the body **only when the
in-motion flag is set** (`[agent+0x20] & 0x20000`; schema GAME_SMSG "40") and is a
**no-op on a parked body** — so every stop-ack we sent did **nothing** at the
client. Retail's F9 stop-ack answered a **real walk's stop** (retail ran the
led/re-grant regime, then stopped at t=65.058, got the `0x0028` at 65.095); ours
answered a body that had never moved. The treatment was on the wire and never in
the client's state machine. H6's registration (§7.4) named "the pre-cast `0x0047`"
but did **not** pre-register a movement-exposure floor — that the player must have
**walked and stopped** before the cancelled cast — which is exactly the
[[feedback-zero-exposure-is-not-a-null]] failure: a treatment arm that never met
its condition has zero trials, not a null. **H6 is NOT refuted; it is untested.**

**The unconfounded finding this run does deliver, and it is worth the run:** the
freeze reproduces from a **pure standstill**, with the body at its cleanest
possible state (fresh spawn, never moved, `agent+0x50` never dirtied). Since the
canonical freeze had a prior walk and this one had none, and both froze
identically, **an unclosed movement episode is not NECESSARY for the freeze** —
which weakens H6 as the *differentiator* independent of the void treatment, and
strengthens **H5**: the walk-suppress state is set by the **cast hold itself**,
needing no movement history, exactly F10's local-write picture. A structural
caveat that shifts weight toward R5 over a re-run: our `0x0028` always arrives
*after* the client's own `0x0047` (36–37 ms here; 37 ms in retail too), i.e. after
the client already parked itself — so even a walk-first re-run may find the
handler no-ops on an already-stopped body, and a wire-only arm may be unable to
deliver R6's treatment at all. **Two ways forward, owner's call (§7.4b).**

### 7.4b The decision R6 leaves — re-run with exposure, or go to R5

- **Re-run R6 with a movement-exposure floor**: operator **walks a few steps,
  stops, then casts** before each cancelled press, so the pre-cast `0x0047`
  answers a real stop. Cheap (same server, same flag). Risk: the ack may still
  no-op if the client parks before it lands (the 37 ms caveat above) — in which
  case R6 is shown structurally inert and H6 needs R5/R7 to settle anyway.
- **Skip to R5** (the movetap poll, §7.3's instrument): reads the walk-start
  signature and the suppress bits directly, does not depend on getting the
  exposure condition right, and the standstill freeze already points at H5. This
  is the more decisive path and the one the owner offered.

### 7.4c R5 RAN — the instrument earned itself: the WIRE criterion was about to score a WARP as a walk (2026-08-24)

`movetap-20260824T141620` (451 samples, 50 Hz, 40 s) paired with gamesrv
`authsrv-20260824T141556-c1`, shipped configuration (no diagnostic flag),
walk-first protocol as registered. Three cancelled casts plus ordinary presses.
Clocks aligned by trajectory fit — `server_t = async_clock/1000 + 1.16 s`,
median report-to-track residual 14.1 u over 53 reports, and the same offset
falls out of an independent nearest-position median (1.181), so the windows
below are anchored rather than assumed.

**CANCELWALK-F16 — OBSERVED, and it is the reason R5 was worth building. Two of
the three mid-cast presses produced motion the §5 WIRE criterion would have
scored as walks; the memory read says only ONE of them was a local walk.**
Per press, reading the ASYNC (drawn) body:
- **Cancel 1** (t=41.238, token 0 at the press) — **THIS BULLET IS CORRECTED AT §7.4d: the walk-start DID run (288.0 u/s in the pressed direction, token 0→4); what follows describes only the snap that rode with it.** Nothing for ~190 ms, then
  the body **JUMPS 182 u** to `[-6086.59, -2523.03]` — onto the SYNC copy,
  `sep` collapsing 227.6 → 17.2 — and glides on with a baked velocity. A local
  walk-start does not teleport the body. This is the grant regime driving it
  (F7's click-order shape), and the client's own next report is 77.6 u from the
  press point, which the wire criterion reads as "walked".
- **Cancel 2** (t=50.747, token **24** at the press): a genuine local
  walk-start — token 24→1, a velocity baked, **no position jump**, then a
  smooth glide away from the granted point (which was zero-lead at the body's
  own feet and could not have steered it). The press worked.
- **Cancel 3** (t=56.536, token 0 at the press): token, `dir`,
  `vel_raw` and the position **all unchanged for ~900 ms**. **Signature
  ABSENT** — the canonical freeze, now read from the client's own memory.
**The positive control passes and is what licenses the rest**: five ordinary
presses in the same session all moved (17.5–170.5 u within 400 ms), so the
instrument is reading the walking body.

**CANCELWALK-F17 — OBSERVED (n=3, and the n is the point). The freeze is NOT
deterministic under a held cast, which weakens H5's simplest form.** One
mid-cast press ran the walk-start normally while two did not. Whatever
suppresses the walk is therefore **not set by the cast hold alone** — H5 as
written ("the cast hold sets the bit") predicts all three freeze. The one field
that separates them is the async body's request token (`+0x50`) at the press
instant: **0 on both non-starters, 24 on the one that walked.** Ordinary
presses from token 0 walk fine (5 of 5 above), so the condition is
**COMPOUND** — a held cast AND token 0 — not the token alone. **⚠ THIS WHOLE
PARAGRAPH IS RETRACTED AT §7.4d**: cancel 1's token was also 0 and it DID run
the walk-start, so the correlation does not exist and the field is not a
planner. Left standing, struck, because a hypothesis is only honestly retired
where it was raised.

**CANCELWALK-H8 — ⚠ REFUTED THE SAME DAY at §7.4d, before any run: `+0x50` is a
move-request correlation token that NOTHING branches on, and cancel 1 walked
with it at 0. The paragraph below is what was registered; read §7.4d for what
killed it.** (RECONSTRUCTION, n=3, offered as the next thing to test, not as a
finding.) Mid-cast, the local walk-start refuses on a body
whose queued-move store is clear, and proceeds on a body that still carries a
stale one — i.e. the gated path is *fresh walk-start* and a body with an armed
planner resumes through a different door. Provenance of cancel 2's stale 24 is
itself suggestive: it was left behind by the warp at async_clock 48449, where
the body was snapped to a stop **without** its planner being cleared. *Refuted
by:* a mid-cast press with `planner ≠ 0` that freezes, or one with
`planner = 0` that walks. **This also predicts R6's null**: `--stop-answer=ack`
CLEARS the queued move (that is what the `0x0028` handler does), so on H8 it
could only ever push the client toward the freezing state — which is what 4 of
4 did.

**CANCELWALK-F18 — OBSERVED. The warp the operator reported is the DRAWN body
being snapped onto the LAGGING SYNC copy, it is sub-gate-1, and it is NOT new.**
Three events at 1,129 / 2,221 / 1,840 u/s against a 288 u/s cap, each landing on
the sync copy (`sep` → 13.6 / 17.2 / **0.00 exactly**, the last one on our own
granted point `(-5548.11, -2186.87)` from t=49.013 to the decimal). What it is
**not**, each excluded rather than assumed: **not gate 1** (`gate1 = below` on
all 451 samples, max `sep` 265.8 u against the 299.33 cut); **not `0x002C`**
(the session sent 24 movement messages, all `0x0029`); **not gate-3 crowding**
(the only other agent is 350–382 u from every landing, orders of magnitude
outside a combined radius). **Not caused by this session's work either** — the
same signature is present in the pre-existing corpus at far worse magnitudes
(`20260822T161918`: 16 violations, max 81,179 u/s, `sep` max 5,472 u, 1,328
gate-1-above samples), and **today's run is the mildest on record with any**
(3 violations, `sep` max 265.8, zero gate-1-above). What made it visible *now*
is the walk-first protocol R5 required: R6's standstill session could not
produce it. **It does contradict REALFIX-O1's "the `0x0029` moves the sync copy
and nothing else" at these instants** — the drawn body is arriving at the sync
copy's position — and the mechanism is unread. Filed for the movement arc;
a sub-gate-1 rubber-band class that the hard-jump bar has never counted.

**Methodological note, and it generalises past this arc.** §5's readout rule —
"the client's own reports move ≥ 30 u within 0.5 s" — is a WIRE test, and F16
shows a warp satisfies it. Any future cancel scoring must either read the body
(R5's fields) or check that the displacement is smooth and away from both the
granted point and the sync copy. The wire cannot tell a walk from a yank.

### 7.4d H8 IS REFUTED, and TWO OF MY OWN §7.4c READINGS WITH IT (2026-08-24)

H8 was minted, tested at a desk, and killed the same day — by the tape already
on disk, before any client run. Three corrections, in the order they bite.

**CORRECTION 1 — the clock alignment was avoidable and wrong.** §7.4c aligned
the movetap and gamesrv captures by trajectory fit (offset 1.16 s, residual
14.1 u). **Both files carry a unix wall clock**: movetap rows have `t`, the
gamesrv origin row has `wall_unix`, so `server_t = movetap_t − 1787595356.470`
is EXACT (residual 0.006 s against the fit's 0.150). The fitted windows happened
to land within 48 ms and the qualitative readings survived, but the method was
wrong and is retired: **align on the wall clock, never on the trajectory.**

**CORRECTION 2 — cancel 1 DID run the walk-start; §7.4c's F16 says it did not,
and F16 is wrong on that point.** Re-scored on the exact clock: at the press the
async body's velocity is `[263.083, 117.18]` — magnitude **288.0 u/s exactly**,
direction `(0.9135, 0.4069)` — and the press's own `vec2` is
`[701.402, 312.412]`, direction `(0.9134, 0.4069)`. **The body walked at full
run speed in the direction the operator pressed**, and a fresh request token was
allocated (0 → 4). What ALSO happened, in the same instant, is a **182 u SNAP**
onto the sync copy. So cancel 1 is *walk-start + warp*, not *warp instead of
walk-start*. The corrected scoreboard is **2 of 3 mid-cast presses WALKED**
(c1 token 0→4, c2 token 24→1) **and 1 FROZE** (c3, token 0→0, nothing for
900 ms). F16's headline — that the wire criterion cannot tell a walk from a
yank — **stands and is if anything sharper**: cancel 1 both walked AND warped,
and the wire shows only a 77.6 u displacement that looks like neither.

**CORRECTION 3 — `+0x50` is not a planner, and H8 has no mechanism.** The name
was mine and it was wrong. **OBSERVED, three witnesses, positive-controlled:**
`+0x50` is a **MOVE-REQUEST CORRELATION TOKEN**. The local applier increments a
counter at `ChCliBase+0x68` (`0x0081ABD7 inc [ebx+0x68]`) and passes it as arg5
to AgApi `MoveToPoint` `0x005FC7A0`, which stores it (`0x005FC8ED mov
[esi+0x50],eax`); the server command dispatcher `0x00606120` writes it from the
message's own field +8 on its STOP/MOVE cases; and **every read in the image is
the same payload push** into the completion notifier `0x00603D40`
(`ff7650 push [esi+0x50]`, guarded by `cmp [esi+0x24],1`), after which it is
zeroed. Its one comparison site is `0x0081B58D cmp eax,[esi+0x68]` — a "is this
completion for my latest request?" test on the COUNTER, not on the agent field.
**Nothing branches on `+0x50`**: zero cmp/test operands image-wide, and zero
accesses of any kind inside the applier `0x0081A8F0`'s entire transitive closure
(131 functions, two independent enumerations, each positive-controlled by
finding `+0x50` where it does exist and by reproducing the tree's known `+0x5C`
readers). **So H8 — "the walk-start refuses on a cleared queued-move store" —
names a mechanism that does not exist, and is REFUTED at the data too**: cancel
1 had token 0 at the press and walked anyway.

**CANCELWALK-F19 — OBSERVED. The field survives the rename as a BETTER
instrument, and this is the one piece of R5 that gets stronger.** A fresh token
is allocated on every SUCCESSFUL walk-start call and on nothing else, so
`0 → N` is **direct evidence the applier reached `0x005FC7A0` rather than
bailing at a gate** — a positive walk-start detector rather than the state
variable it was mistaken for. `movetap` now names it `reqtoken`; capture
`movetap-20260824T141620` predates the rename and carries the old `planner`
key.

**CANCELWALK-F20 — OBSERVED, and it is what the operator actually saw. The
warp is a walk-start reconciliation, and its size is OUR separation.** Of the
eight walk-starts-from-rest in the capture, **two snapped the drawn body onto
the sync copy** (170.5 u and 182.1 u), and those two carry the largest
pre-press separations in the run (194.9 u and 227.6 u); a third at 191.1 u did
not snap, so the trigger is not a clean threshold at this n. The snapped body
then walks the pressed direction at full speed. **The separation is the term
the SERVER owns**: zero-lead grants at the client's own reported point, rate-
limited to one per 0.5 s, let the sync copy fall 120–230 u behind (p50 122 u
this run), and the reconciliation pays that debt in one frame. This is a
REALFIX-shaped cost of the shipped policy, not a cancel-path defect, and it is
filed there.

**What survives all of this.** The freeze is **intermittent** (1 of 3 here,
against 100% in every earlier run) and **nothing `movetap` samples
distinguishes the cases.** The sharpest pair in the corpus makes that
concrete: press `t=56.536` (FROZE) and press `t=58.138` (WALKED) report the
**same position** `(-5292.289, -2536.575)`, 1.6 s apart, are answered with a
**byte-identical** `0x0029` (`2900010000005062a5c534891ec500000000`), and every
sampled field matches — token 0/0, velocity 0/0, `gate1 below`, fence `shut`,
mode 1. **The one difference is that the first is mid-cast and the second is
not**, which is the arc's original symptom restated, and it lives in state
`movetap` cannot see (ChCliBase and the AgentView are different objects it does
not resolve). The sampler's ~0.089 s median interval against a walk-start
latency of 0.083–0.131 s means it can miss the decision entirely.

**CANCELWALK-R7 is therefore the instrument, and it is now the ONLY one that
can answer this**: a hardware-execute-breakpoint gate trace on the applier
`0x0081A8F0` — Dr0–Dr3, no client code modified, the `trnhook` pattern already
in this tree — reading GATE A (`[ChCliBase+0x10C] & 0x100`), GATE B
(`byte[+0x64] & 1`) and the navmesh exit at the frozen press. The applier is
**not** a per-frame function (one direct caller, `0x00816470`; it fired 8 times
in 60 s here), so the trace is cheap. Useful detail for building it: the two
failure exits differ in shape but **not** in return value — a gate bail
(`0x0081AD0F`) calls `0x005FCA80` and returns 1, the navmesh-empty exit
(`0x0081ACFA`) returns 0, and the success path also returns 1 — so a hook must
read the gate operands, not the result.

### 7.4e R7: BUILT, ADVERSARIALLY REVIEWED, AND THE REVIEW MOVED THE INSTRUMENT (2026-08-24)

R7 was built as a hardware-breakpoint gate trace (`toolkit/clientscan/gatetrace.py`)
and reviewed before it was ever pointed at a client. **The review found five
BLOCKERS, each measured on a real WOW64 target with a positive control, and the
first one would have KILLED THE OPERATOR'S CLIENT on the first breakpoint
hit** — so the file now REFUSES to run and the arc took a cheaper instrument
instead.

**The blockers, kept because each is a reusable lesson:**
1. A 64-bit debugger attached to a WOW64 target receives
   `STATUS_WX86_SINGLE_STEP` (0x4000001E), **not** `EXCEPTION_SINGLE_STEP`
   (0x80000004). The dispatch matched zero hits, handed every exception back to
   a client with no handler, and killed it within one frame of arming, having
   measured nothing (demonstrated: 266,734 events, all 0x4000001E, victim exit
   0x4000001E). **This was a REGRESSION, not a discovery** —
   `commandertrap.py`, in the same directory and already in the suite, defines
   both WX86 constants and its header explains this exact failure. The file was
   modelled on `trnhook/debugread.py`, which carries the same latent defect.
   *Grep the directory before copying the nearest precedent.*
2. `DebugSetProcessKillOnExit(False)` called BEFORE `DebugActiveProcess` fails
   with ERROR_INVALID_HANDLE and does nothing, so kill-on-exit stays TRUE; with
   no try/finally and a `keytap.read_at` that RAISES, any error takes the client
   with it (measured both orderings: before → victim dead, after → victim alive).
3. The debug registers were never cleared on detach, leaving the client carrying
   four enabled breakpoints with no debugger to receive them.
4. The control was disarmed through the WOW64 SHADOW while armed in the NATIVE
   context — by the file's own thesis, a different register set.
5. No `EFLAGS.RF`, so an execute breakpoint re-faults forever: 230,759 traps in
   8 s against the 8 the victim's real executions warranted.

**And the justification for building it was wrong on both halves.** §7.4d
argued a breakpoint was needed because the operands "live on an object movetap
does not resolve and are read and discarded inside one frame". Neither holds:
they are **persistent object fields**, and the object is **two dereferences**
from a `ctx` that `movetap.resolve()` already returns and both call sites
already discard. MOVE-DISPATCH's own first instructions say so, read out of the
image at 0x008163A7: `call 0x0047F660` / `mov eax,[eax+0x2C]` /
`mov esi,[eax+0x680]` / `mov eax,[esi+0x10C]`.

**CANCELWALK-R7 SHIPS AS A POLL, NOT A TRAP.** `movetap.controller_read()`
walks `[[ctx+0x2C]+0x680]` and decodes both operands, adding four reads to a
poll that already runs: rows now carry `ctrl_status`, `ctrl_flagbyte`,
`gate_a`, `gate_b`, `gate_c` and `walk_suppressed`. Every failure is named
(`no-ctx`, `ctrl-ctx-unreadable`, `controller-null`, `operands-unreadable`) and
leaves the gates `None` — **never `False`, which is the value H5 predicts**, so
a failed read cannot manufacture the finding. Guarded by 10 new checks in
`movetap --selftest` (floor 240 → 250) driven over a fake memory.

**What the trap would still buy, and it is the only thing:** a poll at ~11 Hz
cannot see a bit SET and CLEARED inside one frame. If the poll shows the gates
CLEAR at a frozen press, that residual is the remaining question — and reviving
`gatetrace.py` then means fixing all five blockers by driving
`commandertrap.py`'s `HwTrap` (which already has the WX86 codes, `EFLAGS.RF`, a
runaway guard, disarm-all and a tested detach) rather than the hand-rolled loop.
The pure half (`gate_verdict`/`reconcile`/`run_verdict`) and its guard are sound
and kept; only the process half is unsafe, and `UNSAFE_TO_RUN` makes `trace()`
raise rather than run, checked by calling it.

**A guard defect the review also caught, worth its own line because it was
false in five documents:** `test_gatetrace.py` declared floor 42 with section 1
calling `LEDGER.skip(..., 9)` in the belief that a skip lowers the floor by its
count. It does not — `Ledger.skip(label, why)` takes two strings and lowers
nothing — so the file was RED on any machine without the vault snapshot while
this document, TESTS.md, PLAN.md, the file's own comment and a commit message
all claimed it "drops to 33 on a bare machine". Floors are now the
bare-machine numbers and both configurations are green.

**Predictions for the poll, unchanged from the trap's and still registered
before any run:** H5 → at a FROZEN press `walk_suppressed` is true and
`gate_a`/`gate_b` names which bit; at a WALKING press both clear. H7 → all
three gates clear at a frozen press. Neither → gates clear and the refusal is
downstream (the dedup at 0x0081AA5B, or ASYNC-MOVE-START). **GATE C should
never be set at a press that reached the wire**, since MOVE-DISPATCH tests the
same bit before sending `0x003D` — C reading set would falsify the READING, not
a hypothesis.

**The run, and it needs no elevation and no debugger:**

    python toolkit/harness/session.py --keep-open --enemy --game-args "--map 280
      --explorable --practice-target --skills 105,153,322"
    python toolkit/clientscan/movetap.py --seconds 180

Walk-first, ≥3 cancelled casts, ordinary presses as the in-session control.

### 7.6 R7 RAN — THE GATE IS FOUND, IT IS PROPERTY 8's BIT, AND IT IS OURS (2026-08-24)

`movetap-20260824T163558` (552 samples, `ctrl_why: ok` on **all 552**) paired
with gamesrv `authsrv-20260824T163550-c1`, aligned on the wall clock both files
carry. Five casts, four cancelled by a movement press. The poll read the
walk-start applier's gate operands directly, and the answer is unambiguous.

**CANCELWALK-F21 — OBSERVED. GATE A and GATE C are never set; the live gate is
GATE B, and my "primary" hypothesis named the wrong bit.** `[ctrl+0x10C]` is
**0 in all 552 samples**, so neither bit 0x100 (GATE A, the "dedicated
suppress-self-walk bit" the read-site census made primary) nor bit 0x10
(GATE C) is ever involved. The flag byte `[ctrl+0x64]` alternates **2 and 3** —
bit 0, GATE B, toggling — 170 samples set, 382 clear. H5's shape is right and
its operand was wrong: **the census argument ("read at only two sites, a
dedicated bit") predicted the wrong one of the two candidates**, which is what
a structural argument can do when a measurement is available and unmade.

**CANCELWALK-F22 — OBSERVED, 5 of 5 and 5 of 5. GATE B is property 8's bit, and
THE SERVER DRIVES IT.** Every SET window opens within 0.04–0.10 s of one of our
`0x009F` property-8 → 1 sends and closes within 0.06 s of the matching → 0:

| our prop8 → 1 | gate B set at | our prop8 → 0 | gate B clear at |
|---|---|---|---|
| 12.656 | 12.69 | 23.533 | 23.47 |
| 28.205 | 28.30 | 29.257 | 29.19 |
| 36.497 | 36.54 | 37.681 | 37.69 |
| 43.204 | 43.28 | 44.238 | 44.25 |
| 50.262 | 50.35 | 51.362 | 51.33 |

Five windows, five casts, no unexplained transition. This **joins the arc to
`studies/skillcast` §16.2**, which read property 8's case body as "a one-bit
flag at object `+0x64`, set by a non-zero value and cleared by zero" — the same
offset, now caught in the act on the object the walk-start applier gates on.
Property 8 is not merely "animation plumbing": **it is the walk-suppress gate.**

**CANCELWALK-F23 — OBSERVED, 3 of 3 frozen and 1 of 1 walking. The freeze is
the applier reading a bit our answer has not cleared yet.** At the last sample
before each of the three frozen presses, `gate_b` is **SET** and the body never
moves (velocity 0.0, position bit-identical, for the whole window); the bit
clears ~90 ms *after* the press. At the one press that walked, `gate_b` was
already **CLEAR** at the press sample and the body was at **288.0 u/s in
exactly the pressed direction** — async velocity `(+0.956, −0.294)` against the
press's own `vec2` direction `(+0.956, −0.294)`, so that one is a genuine local
walk-start, not a grant-driven order (a 318 u snap rode along with it, F18's
class again).

**AND THE OBVIOUS ALTERNATIVE IS REFUTED BY THE SAME DATA.** "The frozen ones
were taps" does not survive: the key was held **0.834 s, 1.334 s and 0.849 s**
after the three frozen presses (press → its own `0x0047` release), i.e. for
~0.75 s *after* the bit cleared, and the body still never moved. **Clearing the
hold does not re-evaluate a held key on our build.**

**THE MECHANISM, end to end, OBSERVED except where marked:**
1. Cast starts; we send property 8 → 1; GATE B is set. The client's local
   walk-start is now suppressed — which is correct, that is what an action hold
   is for.
2. The player presses a movement key. **The client's applier runs on that key
   edge, in its own frame, reads GATE B still SET, and bails** (`0x0081AD0F`).
   No walk. The key edge is spent.
3. The press reaches us ~one round trip later; we answer `[8→0, 59, E2]`; GATE B
   clears about a frame after that.
4. **Nothing re-runs the walk-start**, because no new key edge exists — and the
   held key does not produce one. The body stays still for as long as the key
   is down.
5. The second press finds GATE B clear and walks. **That is the double-press
   symptom, exactly.**

**What this closes and what it opens.** It closes the arc's central question:
the differentiator is a bit we set, read by the client one round trip before we
clear it, and *no cancel-instant answer content can win that race* — which is
why R1 (zero bytes) froze, why R2–R4's leads only moved the body by ordering it
to a point, and why R6's stop-ack could not matter. It opens a sharper one, and
it is a **desk** question: retail's client walks on the single press (F3, "self-
walks its own live direction the moment the burst clears the hold"), so on
retail *something re-starts the walk when the hold clears*. `skillcast` §16.2
already read property 8's value-0 path as scheduling a DEFERRED action —
`0x0081C090` sets a state bit in `+0x110`, computes a due time into `+0x114`
(`0x006044E0()` + 0xFA) and registers it through `0x009217C0`. **Reading that
deferred action to depth is the next step, and it costs nothing.** If it is a
"return to ready" that re-invokes the walk-start when a movement key is held,
the whole arc lands on why it does not fire here.

**Registered predictions, scored:** H5 **CONFIRMED in shape, corrected in
operand** — a controller bit does suppress the walk at a frozen press, and it
is GATE B, not GATE A. H7 (navmesh/path degeneracy) is **REFUTED for these
presses**: the applier never reached the navmesh query, because a gate above it
bailed. GATE C never set, as the reading predicted (it would have falsified the
model, since the press reached the wire).

### 7.7 THE ARC LANDS: the resume path is INPUT-CHANGE-triggered, and our runs never triggered it (2026-08-24)

§7.6 left one question: retail walks on the single press, so something must
re-start the walk when the hold clears. Two desk reads, adversarially verified
instruction-by-instruction, answer it — and the answer is not the deferred
action.

**CANCELWALK-F24 — OBSERVED. Property 8's clear schedules a RE-FACE, not a
walk resume.** `0x0081C090` arms a 250 ms timer (`0x006044E0` is
`AgTimerMgr::GetTimeMs`, and ArenaNet names the unit itself — the assert at
`0x00604487` is `AgTimer:122 (int)(timer->GetTargetMs() - m_time) >= 0`). The
object is an AgTimer node; `ChCliBase`'s vtable at `.rdata 0x00A95428` has two
slots and slot 1 (`0x0081B940`) is the callback, fired by `AgTimerMgr::Advance`
`0x00603FE0` through `call [eax+4]`. Its leaf for this slot is `0x0081BA80`,
and it is a **turn-to-angle**: `atan2` of the latched heading → AgApi
`0x005FC900` → c2s `0x0040 ROTATE_PLAYER`. It writes `ChCliBase +0x104/+0x108`
and AgAgent `+0x54/+0xB8/+0xC8/+0xCC`, **never the velocity pair
`+0xB0/+0xB4`** (writer census: none of `0x00602CC0`, `0x005FF880`,
`0x00601F70` touches it), and it **refuses to run unless the body is already
standing still**. It cannot resume a walk. *The 250 ms had nothing to do with
our freeze.*

**CANCELWALK-F25 — OBSERVED, and this is the arc's answer. The movement input
path is LEVEL-sampled per frame and dispatch is gated on the DIRECTION
CHANGING — not on a key edge, and not on the hold.** The evaluator
`0x005355C0` runs every frame from the GmView frame message (`0x004E28B0`,
with a float dt). It calls MOVE-CMD `0x00535380` only when the movement
direction differs by more than a threshold (`0x00535CF7` / `0x00535D7F` /
`0x00535E7C`), behind a 50 ms throttle (`0x00535E21`); the key-down handler
`0x00536120` dispatches nothing at all. So:
- **A steady held key with a steady camera produces delta 0**, MOVE-CMD is
  never called after the first frame, and the walk applier is never re-entered.
  **That is our freeze**, and it is why the key being held 0.83–1.33 s past the
  bit's clear (F23) changed nothing.
- **A camera turn with the key held DOES re-dispatch**, at up to 20 Hz — and
  the `0x00535E9F` site passes arg6 = 0, so those re-entries send **no c2s
  `0x003D`** and are invisible on the wire.

**CANCELWALK-F26 — OBSERVED, and it closes the retail comparison from retail's
own tape.** If F25 is right, retail's walking cancels must show a walk whose
direction differs from the only vec2 it ever reported. They do, checked in
`20260824T074002`: each cancel press emits ONE `0x003D` carrying the latched
`(+0.017, +1.000)` (north) and then nothing until the stop —
- t=81.625 → stop at +95.9 u **north**, direction (+0.017, +1.000): matches the
  report, the unmoved-camera case;
- t=114.609 → stop at +28.8 u **due west**;
- t=128.774 → stop at +23.9 u **WNW**.
Two of three walked a direction the client **never sent**, with no second
`0x003D` and no `0x0040` in the window. That is exactly F25's wire-invisible
re-dispatch signature. **F3's "the client self-walks its own live direction"
is now mechanised: the live direction arrived through re-dispatches the wire
cannot see, and they happened because retail's operator was turning the camera
while the key was down.**

**THE COMPLETE MECHANISM, and nothing in it is a defect in our server.**
1. Cast starts; our property 8 → 1 sets the hold (F22). Correct.
2. The movement press re-dispatches once (direction changed from none to
   something), the applier reads the hold still SET, bails. The press is spent.
3. Our `[8→0, 59, E2]` clears the hold a round trip later (F22/F23).
4. **Whether the body now walks depends entirely on whether the INPUT DIRECTION
   changes again.** Holding a key with a still camera never does — no
   re-dispatch, no walk, however long the key is held. Turning the camera does
   — and the applier, now finding the hold clear, walks.
5. A second key press is one way to produce a direction change. **A camera turn
   is another, and it is the one retail's captures were doing.**

**CANCELWALK-H10 — the prediction this makes, registered before any run.** On
OUR build, unchanged, shipped configuration: press a movement key mid-cast
**and turn the camera while holding it** → **the player walks**, with the walk
beginning at the camera turn rather than at the press, and **no second `0x003D`
on the wire**. If it walks, the arc is closed and the "freeze" is not a server
bug at all but the client's own input model meeting a still camera. *Refuted
by:* the body staying still through a camera turn with the key held, which
would put the re-dispatch claim back on the bench.

### 7.7a Corrections owed to earlier sections, none of them smoothed over

- **`studies/skillcast/FINDINGS.md` §16.2** is incomplete in four ways, each
  re-derived here: `0x0081C090` has **FOUR** gates, not three (the fourth,
  `0x0081C0AD`, requires `+0x110` bit 0 CLEAR — an already-armed re-entrancy
  guard, so a second property 8 → 0 before the timer fires is a NO-OP); the
  state bit is **bit 0**; `0xFA` is **250 MILLISECONDS**, named by ArenaNet's
  own `AgTimer:122`; and `0x009217C0` is not a register but a **min-recompute
  and re-key with a cancel path** when the mask is zero. Also: §16.2's "the
  value-1 path stores its float to `+0x100`" names the right field but an
  **unreachable instruction** — the case body sets the bit *before* calling
  `0x0081BE90`, whose own gate is therefore always taken, so the reachable
  store is the bail's `fldz; fstp [esi+0x100]` at `0x0081C003`. And its summary
  "everything is view-object-local, no gameplay state" is too strong: the
  deferred action's terminal effect is a **c2s `0x0040`**.
- **CANCELWALK-F10 is WRONG on two points and incomplete on a third.** The
  `+inf` "no heading" sentinel lands in the **CONTEXT** `+0x694/+0x698`, not
  the controller. The "5 key-edge sites plus a vtable slot" caller list is a
  false positive — they are all **one function**, and the vtable word is not a
  caller. And `+0x10C` **does** have a runtime setter (`0x0081C020`), so F10's
  "no writer found, the suppress state is a local write we cannot trace" was
  half an artifact of an incomplete search.
- **`+0x64` bit 1 is FLAG_CONTROLLED**, named by ArenaNet
  (`ChCliBase:521`/`578`). So §7.6's measured byte decomposes exactly:
  **3 = FLAG_CONTROLLED | action-hold** during a cast, **2 = FLAG_CONTROLLED**
  otherwise. And bit 0 has exactly **two writers image-wide** in the ChCliBase
  band (`0x0081BD02`/`0x0081BD14`) — property 8's case body, confirming F22
  from the writer side.

### 7.8 THE WARP HAS A CAUSE, and it is our grant cadence meeting F25 (2026-08-24)

Operator run `authsrv-20260824T182739-c1`, reported sequence *move → stop →
turn camera → cast → move-to-cancel*, "and it warped me". **No `movetap` ran
alongside, so this section says nothing about the gates** — it is a wire-only
reading, and that limit is the reason it makes no claim about H10.

**CANCELWALK-F27 — OBSERVED. The warp is the drawn body reconciling onto a sync
copy our own grant cadence left a quarter of the map behind, and the arithmetic
closes to 41 ms.** At the cancel press (t=16.088) the player reports
`(-6058, -2530)`; 0.501 s later `(-6280, -2391)` — **261.9 u, i.e. 523 u/s
against a 288 u/s run speed**, so walking cannot produce it. It decomposes
exactly:
- an instant **256.2 u snap** back onto the stale sync copy at `(-6314, -2519)`
  — the point granted at t=13.537 and never updated since;
- then a **132.4 u walk** in `(+0.257, +0.966)` ≈ the pressed north, which at
  288 u/s takes **0.460 s** against the 0.501 s window. The 41 ms of slack is
  the snap's own frame.

**WHY THE COPY WAS 256 u STALE, and this is the part that is new.** Our
zero-lead policy grants on c2s `0x003D` and on nothing else. **F25 says the
client emits `0x003D` only when the movement DIRECTION CHANGES** — so a long
straight leg produces **one** report, at its start. Here the player turned east
at 13.536, we granted `(-6314, -2519)` (where they were *at that instant*), and
they then walked 256 u east on that single report while the copy sat at the
grant. The `0x0047` stop at 14.437 produced no grant either — the stop arm is
deliberately silent (`--stop-echo` is REFUTED). So the copy was left behind by
**the entire length of the last straight leg**, and the next walk-start paid it
in one frame.

**It is not rare, and it is now priced.** Staleness at every `0x0047` stop
(player position vs the last granted point), four captures:

| capture | stops | `0x003D` | staleness p50 | max | over ~190 u |
|---|---|---|---|---|---|
| `141556` | 7 | 46 | 73.7 u | 227.6 u | 3 of 7 |
| `163550` | 13 | 55 | 24.8 u | 345.9 u | 1 of 13 |
| `182739` | 4 | 8 | 12.7 u | 256.3 u | 1 of 4 |
| `081335` | 4 | 8 | 89.5 u | 120.1 u | 0 of 4 |

**5 of 28 stops leave the copy past the ~190–230 u band where F20 measured the
snap firing** — about one stop in six, which is exactly the intermittency the
operator reports. The `0x003D` column is the mechanism in miniature: 8 reports
across a whole session of walking in `182739`, because the operator walked in
straight lines.

**This joins the arc's two loose ends into one statement.** F25 (the client
reports on direction change) and F18/F20 (the drawn body snaps onto the copy at
a walk-start when the gap is large) are the same story from two sides: **our
re-pin trigger is hostage to a client reporting rule we only understood today,
so the straighter the player walks, the further the copy falls behind, and the
next walk-start snaps them back.** The freeze and the warp were never the same
bug — the freeze is the action-hold race (§7.6/§7.7) and **the warp is a grant-
cadence defect, which is REALFIX's, not this arc's.**

**Candidates that would actually address it, none run, no recommendation
made here:** `--resync` (REALFIX-P5, `0x002C`, hard-sets BOTH copies, built and
never run, and its trigger is literally "our model has drifted N units") is the
one whose refutation does not already stand; a stop-arm grant is `--stop-echo`
and IS refuted; a time-based re-grant during a straight leg has no flag today.
**Filed to the movement arc. The ruling on which, if any, is the owner's.**

### 7.9 A run with BOTH instruments: H10 supported, the mini-warp is F27 at small scale, and a REAL BUG falls out (2026-08-24)

`movetap-20260824T183544` + `authsrv-20260824T183537-c1`, operator-driven, both
instruments running. Three cancelled casts, plus — at the end, deliberately —
**a cast started while running**.

**CANCELWALK-F28 — OBSERVED, and it is a genuine defect in OUR server, not a
client quirk. The action hold gates the walk-START; it does not stop a leg
already in flight.** At t=38.268 the operator cast **while running east** (no
`0x0047` before it; the last report is a moving one at 37.820). Our
`prop8 → 1` lands at 38.269 and `gate_b` goes true at 38.31 — and the drawn
body **keeps gliding at 288.0 u/s for the entire cast**, from `(-6167, -2493)`
to `(-5488, -2617)`: **~690 u of travel while casting**, velocity never
dropping below 288.0 in any sample. That is the operator's "float-forward". In
Guild Wars, starting a spell while running stops you; ours does not, because
the only thing we send is a hold that suppresses *starting* a walk.
**THE FIX IS ALREADY BUILT AND ALREADY TESTED.** s2c `0x0028`
AGENT_STOP_MOVING halts the agent **when in motion and no-ops on a parked
body** (schema GAME_SMSG "40", handler read) — exactly the semantics required,
and exactly the message built for R6, where it was VOID for the stop-closure
hypothesis (§7.4a) because it was fired at stops, where it can only no-op.
**Fired at CAST START it is the right message for a real bug.** `agents.py`
already has the builder (`agent_stop_moving`), `authsrv.py` the constant.
Sending it needs an owner ruling and its own registered run; nothing is
proposed as a default here.

**CANCELWALK-F29 — OBSERVED. The gate correlation is now 7 of 7 across two
runs, and this run's walks support H10.** In this session: cancel 1 (15.830)
had `gate_b` **SET** at the press and **froze** — zero velocity, position
bit-identical, for the whole window; cancels 2 (25.071) and 3 (34.608) had
`gate_b` **CLEAR** at the press and **walked**. With §7.6's four, that is
**SET → freeze 4 of 4, CLEAR → walk 3 of 3.** And the two walks here did **not**
begin at the press: velocity stays 0.0 for **0.46 s and 0.43 s** after it, then
snaps to 288.0 with the gate already clear. **A press does not start a walk;
something later does** — which is F25's re-dispatch, and the operator reports
turning the camera. H10 is **SUPPORTED, not yet confirmed**: the poll cannot
see the re-dispatch itself (arg6 = 0 sends no `0x003D`), so what it shows is a
walk beginning ~0.45 s after the press with no wire event to explain it, which
is the shape H10 predicts and no other candidate does.

**CANCELWALK-F30 — OBSERVED. The "mini warp" is F27's mechanism at small
scale, which is the best evidence yet that F27 is right.** Before cancel 3 the
last grant (33.130) named `(-6138, -2527)`; the player then walked 31 u further
and stopped at `(-6107, -2526)` — a stop that produces no grant, so the copy
stayed 31 u behind. The poll shows the drawn body sitting at
`(-6137.52, -2526.8)` **before** the press: it had already snapped back onto
the stale copy during the cast. **A 31 u staleness produced a 31 u warp**,
where §7.8's 256 u staleness produced a 256 u warp. Same mechanism, magnitude
tracking staleness exactly — and it confirms the snap is not threshold-only:
small gaps produce small, still-visible warps.

**What this run leaves.** The freeze/walk question is answered and quantified
(F29). The warp has a cause and a magnitude law (F27/F30) and belongs to
REALFIX. **The float-forward is new, is ours, and has a message already sitting
in the tree that does exactly what it needs** — the one built for a hypothesis
it turned out not to serve.

### 7.5 Measured dead this round — do not retry

- `0x0027`/speed-base as differentiator, trigger, or fix (F8/F13) — and the
  buff cluster wholesale: a baseline-restore 15 s pre-press on an independent
  clock. REALFIX-P4 stands, with its mechanism sentence refined (F13).
- Property 59 as a movement candidate (F12).
- The ≤1.0 u short-circuit reconstruction of the cancel grant (F14 — it is an
  86 u bake to the player's own feet).
- The GATE-A′ dedup as the freeze mechanism (F15 — both legs fired and it froze
  anyway), and position-keyed navmesh zeros (F15).
- Press-time latch snap-clear (F11 scope note — R1 froze on zero bytes).
- Value-carried wire state as the differentiator (F9 — parity verified by
  independent recount). What stays live on the wire side is exactly one thing:
  the stop-closure HANDLER state, and R6 prices it — **and R6 ran it: VOID for
  H6 on zero exposure (§7.4a), with H8 now predicting its null independently.**
- **Scoring a cancel from the wire alone** (F16 — a 182 u warp satisfies §5's
  ≥ 30 u criterion; read the body, or check the displacement is smooth and away
  from both the granted point and the sync copy).
- **Gate 3 / crowding, `0x002C`, and gate 1 as the warp mechanism** (F18 —
  nearest agent 350+ u, none sent, `below` on all 451 samples). The sub-gate-1
  warp class is OPEN, and it is the movement arc's, not this one's.
- **"The cast hold alone sets the walk-suppress state"** — H5's simplest form
  (F17 — one mid-cast press ran the walk-start normally).
- **CANCELWALK-H8 in every form** (§7.4d): `+0x50` is a move-request
  correlation token, **nothing branches on it** anywhere in the applier's
  131-function closure, and cancel 1 walked with the token at 0. Do not
  re-mint a hypothesis on that field, and do not call it a planner.
- **Aligning two captures by trajectory fit** when both carry a wall clock
  (§7.4d correction 1 — `movetap.t` and the gamesrv origin's `wall_unix`).
- **Reading a walk verdict off `+0x50`'s VALUE.** It detects that the applier
  ran (`0 → N`); it is not a distance, an index, or a cause (F19).

## 8. R8 and R9 — registered before their runs, both owner-driven (2026-08-24)

Written at a desk after §7.9. **Both runs RAN the same evening — §8.1a and
§8.2a are the scored results, each adversarially recounted by an
independent agent from the raw captures before a word was written here.**
Both used §0's recipe — both instruments, walk-first, wall-clock
alignment — and both were owner-driven. Each registration carries its own
exposure floor, because §7.4a is what a registration without one costs.

### 8.1 CANCELWALK-R8 · `--cast-stop` — the F28 float-forward fix, wired and unrun

**The code is in the tree (2026-08-24):** `--cast-stop` sends one s2c
`0x0028` AGENT_STOP_MOVING `[player]` at every free-caster **non-attack**
cast start, **first in the cast-begin TAIL** — before the animation and the
prop-8 hold; the E4 press-ack and the debits precede it, so do not score
"not first in the burst" as a misfire when reading the capture. Details
that are choices, named as such: the tail SLOT is unwitnessed (retail
never captured a cast-while-running start) and chosen so the movement
family closes before the action family opens; the scoping is NON-ATTACK
(`not is_attack` — spells are the measured family, and an attack skill's
start drives chase movement a halt would fight). Refused without
`--zero-lead` and with `--cancel-answer`, `--stop-answer` (same opcode,
two triggers — its own cell) or `--arrival-carry` (the halt cuts short a
leg the F1b queue modelled as arriving); all three pairwise cells sit
ABOVE the requires-zero-lead checks, pairwise-first. `test_cancelwalk.py`
§7 drives the lattice, the burst order and both scoping branches; floor 59.

**The change was adversarially reviewed the same day** (three agents:
lattice driven live through 16 cells and real argv, send-site semantics
re-derived at code level, and a 6-mutation probe — 6 of 6 caught, tree
restored clean). Its findings are fixed in the follow-up commit, and three
of them survive as **NAMED residuals, each zero-exposure in this run's
spell-only protocol and each a ship-time term**:
1. **Instant non-attack skills** (shouts, stances, signets) also take the
   halt under this gate — a divergence from retail, which does not stop a
   runner for them.
2. **A non-attack ADRENAL skill's halt** lands between its `0x00D2` and
   the naming property, breaking a measured 39-of-39 adjacency.
3. **The queued begin sends nothing**, and its "body already stopped at
   the first cast's start" premise fails two ways: a spell queued behind
   an attack-headed chain, and a spell queued during an aftercast whose
   hold a movement press already released (`cancel_on_move` releases the
   hold but cannot cancel an aftercast entry or roll back the busy
   window, so a camera-turn walk can be in flight at the begin).
The review also verified the licensing claims at code level: `grant_at` is
written only by `_note_wire_move`, which `send()` consults only for
`0x0029`/`0x002A`/`0x002C` — the halt cannot stamp the grant clock; and
the R8 send is reachable from exactly one site (the free-caster player
burst), with `begin_cast`, the aftercast pulse, the swing sites and every
replay path excluded by read. One transport note: `send()` writes each
message with its own `sendall`, so in-burst ORDER is guaranteed by
same-thread sequencing over one TCP stream, one-segment delivery is not —
nothing in R8 rests on segmentation.

*Protocol:* ≥3 casts started WHILE RUNNING — press the skill mid-stride
with no stop first, F28's own shape (the last pre-cast report is a MOVING
one, no `0x0047` before the cast) — plus ≥1 cast from standstill (the
no-op control) and ≥1 ordinary cancelled cast (the freeze must stay a
freeze). Both instruments; **the wire alone is blind to the entire
question** — a straight glide emits no `0x003D` (F25), so neither the
defect nor the fix appears on it.

*Predictions, registered before any run:*
- Cast while running → the drawn body HALTS within ~0.15 s of the cast
  start: movetap velocity 288 → 0 and the position parks through the
  activation, against F28's measured ~690 u glide. The sync copy halts
  too (the handler stops both), so `sep` does not grow during the cast.
  *(RAN: the halt confirmed exactly — but "parks" happens ON THE SYNC
  COPY, not in place; §8.1a F31.)*
- Cast from standstill → no change in any sampled field — the handler's
  no-op half, the licensing claim measured on our own build for the first
  time.
- The cancel-instant freeze is UNTOUCHED in both arms: gate-B correlation
  (F29) holds at every press, because the flag changes nothing at the
  cancel instant.
- Whether the halt makes the client REPORT (`0x0047` at the halt point) is
  unmeasured and both outcomes are compatible — recorded so the run notes
  it rather than being surprised by it. Either way the general stop arm
  stays silent.

*Exposure floor (the §7.4a lesson):* a cast counts for the treatment arm
only if the body was IN MOTION at the `prop8 → 1` send (movetap velocity
> 0 at the last sample before it); fewer than 3 such casts is a VOID arm,
not a null.

*Decision:* halts as predicted → the candidate is licensed; shipping (and
whether the default flips) is an owner ruling after a REALFIX-style
composition audit, and nothing here ships on. Does NOT halt → the
`0x0028`-halts-in-motion reading (schema GAME_SMSG "40", handler read) is
wrong on our build for this instant, and the fix moves to a client read
before any other message is tried.

### 8.1a R8 RAN — the halt works 3 of 3, and it lands the body ON THE SYNC COPY (2026-08-24)

Captures `authsrv-20260824T213701-c1` + `movetap-20260824T213708`
(operator: 3 walk casts, 1 normal, 1 Esc-cancelled — all five identified
in the tape, each cast's burst carrying exactly one R8 `0x0028`, sent
0.2–0.9 ms before its prop-8 hold row; observed burst order E4 → debit →
`0x0028` → animation → hold, the wired slot). Every number below was
independently recounted by an adversarial verifier writing its own
reader; both alternative explanations it was ordered to attempt are
refuted in the data.

**The halt: CONFIRMED, 3 of 3, exposure floor met exactly.** All three
treatment casts qualify on both prongs (movetap 288.0 u/s into the cast
AND the last wire event a moving `0x003D` at −0.12/−0.43/−0.80 s, no
`0x0047` since — W was down, F28's exact glide state). Speed is **0.0 by
the first sample after the burst** (+0.03/+0.03/+0.06 s) and stays 0.00 u
of drift through the full ~2 s hold. F28's ~690 u float-forward is gone.
*Killed alternatives:* "the client stopped itself" — no `0x0047` exists
between the last moving report and any cast, and a key-release stop halts
in place, which this does not (next paragraph); "a later press's
walk-start reconciliation" — the snap sits inside the burst's own sample
window with the `USE_SKILL` the only c2s anywhere near it, and the body
then sits motionless for 2 s.

**CANCELWALK-F31 — OBSERVED, adversarially recounted. The `0x0028` halt
does not stop the body where it is: it lands it on the SYNC COPY's
current integrated position.** All three halts are an exactly-backward
snap (cos vs pre-velocity = −1.000): **156.9 / 110.1 / 207.1 u**, each
landing at `sep` 0.00. The magnitude equals the pre-cast separation when
the copy is parked (156.9 = 156.9, 207.1 = 207.1 exactly) and is less
when the copy was still integrating a fresh grant (110.1 vs 138.5 — the
copy advanced 28.8 u meanwhile, and the body landed on its LIVE
position). `gate1` reads `below` on **all 471 samples** (max sep 280.8,
under the 299.33 cut), so this is **not** gate 1 firing — it is the
`0x0028` handler's own behaviour: halt = adopt the server-authoritative
copy's state. The schema-"40" reading ("halts both copies") was right and
incomplete; where the drawn body ends up was never in it.
**Consequence, and it is the fix's price: the visible quality of
`--cast-stop` is hostage to grant-cadence staleness (F27).** With the
copy 100–200 u behind (ordinary straight-leg running), every running cast
teleports the player that far backward. Retail stops you where you are.

**Controls: CONFIRMED 2 of 2, and the report question answered.** The
standstill cast and the Esc-cancelled cast changed nothing in any sampled
field (0.0 u across and during; the no-op half of the licensing claim,
now measured on our own build). The client **never reports the
server-ordered halt** — the sole post-halt `0x0047` in the tape is the
Esc release's own, reporting a long-held standstill point. Two knock-ons
recorded: the server's wire-side picture of the player stays "moving"
indefinitely after a halted running cast (11–20 s here) until the next
direction change; and the next walk restarts FROM the snapped-to point,
whose reports the zero-lead arm then re-grants — the snap coherently
becomes the new truth.

**Freeze untouched: CONFIRMED.** The two between-rep presses that landed
during aftercast holds found gate B set and froze until a second edge —
F29's behaviour, unchanged under the flag. `gate_b` mirrors the prop-8
envelope on 471/471 samples with zero mismatches (F22 as state
mirroring; the ~1 ms release→re-hold flip pairs at cast boundaries are
invisible at the 107 ms poll and produce no observable edge).

**Verdict per the registered decision table: the candidate is LICENSED,
with F31 as a named cost.** The halt semantics are exactly as licensed;
where the body lands is the sync copy, so shipping this as-is trades
F28's forward glide (~690 u, every running cast) for a backward warp
equal to the copy's staleness (~100–200 u typical, F27's term). The
serious fix pairs it with staleness reduction — REALFIX's ground
(`--resync`/P5, or cadence work). **The ruling is the owner's; nothing
ships on by default.**

**RULED 2026-08-25 (PLAN §7 Q10): REFUSED AS A SHIP.** *"The stock game
doesn't warp, i am not going to accept a fix that still warps."* The bare
halt stays runnable (`--cast-stop=halt`) as a measured diagnostic and as
R10's control arm; the no-warp successor is **`--cast-stop=pin`,
registered at §8.3**.

### 8.2 CANCELWALK-R9 · H10's confirmation — does turning the camera un-freeze a held key?

(Rewritten for the operator the same day it was registered — the first
version was analyst-facing and the owner said so. The predictions and
floors are unchanged in substance; no run had happened.)

**The question, plainly.** When a movement press cancels a cast and then
freezes you, the arc's answer says why: the press arrived while the
cast-hold bit was still set, so the client threw it away — and holding the
key afterwards does nothing, because the client only acts on movement
input when the DIRECTION CHANGES, and a held key with a still camera is a
direction that never changes. Turning the camera changes it (W means
"camera-forward"), so the same held key should start walking the moment
you turn — and this particular walk-start is invisible on the wire, since
that input path sends no `0x003D`. We believe this because retail's own
tape shows it (F26: retail walked west while its client had only ever
reported north) and because our own two walks in §7.9 began 0.43–0.46 s
after the press with nothing on the wire to explain them — but nobody has
done it ON PURPOSE on our build. R9 is that: freeze yourself deliberately,
then turn the camera with the key still held, and see whether the turn
alone un-freezes you. No new code; this is the shipped server.

**Operator script.** Two terminals:

    python toolkit/harness/session.py --keep-open --enemy --hold 300 --game-args "--map 280
      --explorable --practice-target --skills 105,153,322"
    python toolkit/clientscan/movetap.py --seconds 300

Then, in the game:

1. **Warm-up:** press W, walk a couple of seconds, release. (Scoring
   needs one ordinary walk to prove the instrument is reading you.)
2. **A "turn" rep:** walk a few steps, release W, wait until you have
   fully stopped. Cast any skill on the bar. When the cast bar is about
   halfway, **press W and KEEP IT HELD** — the cast cancels. Immediately
   hold RIGHT-MOUSE and **drag the camera around — a quarter turn or
   more — and keep dragging for about 2 seconds** with W still held.
   Then release everything. Keep dragging rather than one quick flick:
   a flick that finishes before the server's un-hold reaches the client
   is spent while the gate is still shut, but continuous turning retries
   many times a second.
3. **A "still" rep:** same walk → stop → cast → press-W-at-half-bar and
   keep it held — but now **touch nothing else for about 2 seconds**: no
   mouse drag, no other keys. Just the held W. Then release.
4. Alternate steps 2 and 3 until you have **at least 3 of each**.
   (Scoring discards reps where the freeze never actually occurred —
   some presses land after the hold already cleared and walk normally —
   so 3–4 per arm is what survives the floor of 2.)
5. One more ordinary walk press at the end, then let the session close.

Two things to avoid in BOTH kinds of rep: don't turn with A/D (keyboard
turning is a different input path than the one under test and
contaminates the arm), and don't press W a second time (a second press
un-freezes by the known route and the rep measures nothing).

**What it should feel like if H10 is right:** in the turn reps you start
walking WHILE you drag, roughly half a second after the press, in
whatever direction the camera is facing at that moment; in the still reps
you stay planted for the whole two seconds — the familiar freeze.

**Scoring — the analyst's job after the run; none of it is visible at the
keyboard.** Align the two captures on the wall clock both carry (§7.4d
correction 1). A rep COUNTS only if movetap shows `gate_b` SET at the
press — the freeze actually occurred (F29's condition); a press that
landed after the gate cleared is an ordinary press wearing a rep's
clothes, not exposure. **≥2 counted reps per arm, or that arm is VOID
rather than a null** (§7.4a). The warm-up walks must move every movetap
field within a poll, or the instrument was not reading the walking body
and the run is VOID — a failed control voids a null; it has no authority
over a positive.

*Predictions, registered before any run:*
- H10 → every counted turn rep WALKS: the walk begins once the gate is
  clear while the turn continues (within ~0.15 s of the clear: the 50 ms
  input throttle plus a frame or two), in the camera's live direction at
  that instant, with NO second `0x003D` and no `0x0040` in the window.
  Every counted still rep stays frozen — velocity 0, position
  bit-identical — for the full hold.
- Refuted → a counted turn rep still frozen through the drag (the
  re-dispatch claim goes back on the bench), or a counted still rep that
  walks with no camera input and no wire event (something else
  re-dispatches, and F29's 0.43–0.46 s onsets need a new explanation).
- Either way the gate correlation (SET → freeze, CLEAR → walk, 7 of 7)
  is predicted to hold at every counted press; a violation outranks H10
  and reopens §7.6.

*Decision:* H10 confirmed → §0's "the freeze is not a server bug at all"
is promoted from SUPPORTED to OBSERVED and the freeze half of the arc
CLOSES, leaving R8 as the arc's only open item. H10 refuted → §7.7's F25
mechanism is incomplete for our build, and the residual goes back to a
desk read of the evaluator `0x005355C0`'s other dispatch conditions before
any further run.

*(§8.3, the R10 registration, is filed after §8.2a — it exists because of
§8.1a's F31 and the owner's ruling on it.)*

### 8.2a R9 RAN — H10 CONFIRMED 6 of 6, and gate 1 is caught FIRING for the first time (2026-08-24)

Captures `authsrv-20260824T213927-c1` + `movetap-20260824T213933`, shipped
server (zero `0x0028` sends, verified). Operator report: "turn rep warped
me, still rep only with W holds forward walk for ~300 u then stops" —
**both phenomena are fully explained below, and neither is what it looks
like.** Every claim was adversarially recounted by an independent agent
from the raw files; all three alternative readings it was ordered to
attempt are refuted.

**Exposure: 6 of 6, both floors met.** Six cancelled casts (3 turn, 3
still — the classification is exact on the wire: turn reps have 5/2/8
further `0x003D` in their windows, still reps have zero). Every cast was
preceded 0.17–0.40 s by the client's OWN `0x0047` (the operator released
W; the client stopped itself, in place), every press is a single `0x003D`
coincident with the cancel release, and `gate_b` was SET at the last
sample before **all six** presses. The in-session ordinary walks moved
every sampled field — the instrument control passes.

**CANCELWALK-F32 — OBSERVED. H10 is CONFIRMED: the walk restart is the
input-direction change, and the restart itself puts nothing on the
wire.**
- **Turn reps, 3 of 3: a genuine self-walk.** The drawn body reaches
  288.0 u/s at +0.04/+0.16/+0.04 s after the press — at or immediately
  after the gate-B clear (+0.06/+0.05/+0.04 s) — and **before the first
  further `0x003D`** (+0.25/+0.50/+0.25 s), with zero c2s of any kind
  between press and onset. The walk then curves continuously with the
  camera, passes through in-rep grant points at full speed without
  pausing, and ends beyond the last grant. *Killed alternatives:*
  chained click-orders (motion is continuous through and past every
  grant), and walk-caused-by-the-further-report (onset precedes it,
  3 of 3).
- **Still reps, 3 of 3: NO self-walk, ever.** The motion the operator saw
  is OUR OWN ANSWER executing: the press's zero-lead grant drives the
  body (snapped onto the copy, next finding) back along the stale leg and
  **parks it 0.5/0.6/0.6 u from the granted point** at +1.2/+1.4/+1.7 s,
  where it stays while W is still held; the client reports the park only
  on the eventual release (+2.7–3.1 s). *Killed alternative:* a held-W
  self-walk would overrun the grant by 400+ u in that time. One trap for
  future readers: the park path is exactly collinear with the press
  heading (the copy sits behind the body along the last pre-cast leg), so
  grant-driven parking **masquerades as a facing-direction walk** — the
  exact stop at the granted point is the discriminator.
- **Wire-invisibility, refined:** the RESTART is wire-silent (3 of 3), as
  F25/H10 claim; sustained turned walking then reports `0x003D` on
  direction change at 0.25–0.5 s cadence. No tension with F26 — retail's
  walking cancels lasted 0.08–0.33 s, too short to reach a report window.

**CANCELWALK-F33 — OBSERVED, 7 of 7. GATE 1 FIRES, for the first time in
this arc's instrumented history, and it is what the operator called "the
warp".** Every snap in the session — the five press-time snaps
(305–453 u), cast 3's mid-cast snap (365.5 u, gate B still set), and rep
1's mid-walk snap (523.7 u at sep 555.3, coincident with an ordinary
report→grant exchange) — fires exactly at a `gate1` **above → below**
transition: sep 346–555 with `gate1: above` in the samples before, sep
~0–26 with `below` after. 206 of 1,248 samples sat above the 299.33 cut
in this session, against **zero** in R8's (max sep 280.8) and zero in
F18's (max 265.8) — which is why no earlier run ever saw one fire. The
press snap is **universal, not still-rep-specific**: turn reps 1 and 5
snapped 445.3/332.1 u before self-walking (rep 3 skipped it only because
the mid-cast snap had already zeroed its sep). Two sub-details left
open, labelled: the exact trigger site of the mid-cast firing is unread
(no grant lands in its window; the sync copy's own click-order arrival is
the candidate), and one in-walk grant at sep ~312 — barely above the
cut — did not snap, so the firing condition is near but not exactly the
bare sep threshold.

**What this changes.** (1) The freeze half of the arc **CLOSES**: per the
registered decision table, §0's "the freeze is not a server bug at all"
is promoted from SUPPORTED to OBSERVED — the double-press symptom is the
client's input model meeting a still camera, end to end. (2) The
registered still-arm prediction ("position bit-identical") was **wrong as
written**: no self-walk occurred (the H10-relevant content holds), but
the body moved under our own grant after a gate-1 snap — the registered
refutation arm ("walks with no wire event") does not fire, because the
motion has a wire cause we sent. (3) **What a player actually experiences
at a cancel press under the shipped configuration is dominated by F27's
staleness, not by the freeze**: above the gate-1 cut (~300 u of straight
walking — easy to reach) a cancel press LOOKS like "warp back, walk
forward, stop", and below it like the classic freeze. The staleness
measurements here (sep 346–555 at ordinary presses) are the worst on
record and are **filed to REALFIX with F27**, where the cadence question
already lives.

### 8.3 CANCELWALK-R10 · `--cast-stop=pin` — the no-warp halt, wired and registered before its run (2026-08-25)

**Why it exists:** R8's halt works (§8.1a) and was **REFUSED as a ship by
owner ruling** (PLAN §7 Q10: *"the stock game doesn't warp"*) because of
F31 — the `0x0028` lands the body on the sync copy, a backward warp equal
to the copy's staleness. Retail never warps because retail's regime keeps
its copy continuously current (F9's led/re-grant cadence). The no-warp
form must therefore bring the copy to the BODY before halting.

**The mechanism, wired 2026-08-25:** at the same cast-start site, before
the `0x0028`, the server **dead-reckons the player's true position** —
`last accepted report + unit(vec2) × rate × 288 u/s × dt` — and sends one
s2c `0x002C` AGENT_UPDATE_POSITION there. The `0x002C` hard-sets **both**
copies, zeroes velocity and kills any leg (the decoded
`0x00602B20`/`0x006020B0` behaviour `_note_wire_move` already models; no
grant clock stamped), so the `0x0028` that follows lands on co-located
copies and **cannot snap**. What makes the reckoning honest:
- **Straight legs are exactly the legs that never report** (F25), so the
  extrapolation is exact where F31's 110–207 u cases live; F27's own
  arithmetic closed this model to 41 ms.
- ~~**Rates are OBSERVED where used:** mt 1 = 288.0 (everywhere) and
  mt 4 = 0.66 × 288 = 190.1 (R8's own tape: the mt=4 press's walk-onset
  speed). Other families default 1.0, UNVERIFIED and labelled.~~
  **SUPERSEDED by §8.3a's B2 and fixed at §8.3b:** the rates are the
  census families — {1,2,3} 1.0 and {4,5,6} 0.652 OBSERVED, {7,8} 0.75
  LABELLED, anything else refused `unverified-rate`. The struck table
  reckoned a kiting or strafing cast at 288 and hard-set it forward.
- ~~**The extrapolated segment is navmesh-clipped** (the `pm.clip`
  primitive, with `clip_to_walkable`'s standing-outside suspension).~~
  **SUPERSEDED by §8.3a's REAL 2 and fixed at §8.3b:** the clip stands,
  the suspension does not — a wire hard-set gets no standing-outside
  pass; `off-mesh`/`no-mesh` refuse. The struck clause would have
  shipped a raw ray of up to ~3.7 k u from exactly the positions where
  our trapezoids are known-wrong.
- **Every refusal door is named and scorable from the capture** — the
  `0x0028`'s label carries the reckon verdict (`pin:reckoned`,
  `pin:parked`, `pin:pinned-parked`, `pin:report-refused`, …):
  believed-parked sends no `0x002C` (retail sends nothing at standstill
  casts either); a pin newer than the last report refuses (the halt is
  never client-reported, so a second cast would otherwise extrapolate a
  leg the body never walked — R8's second-cast trap); `pos_rejects > 0`
  refuses (`_resync_verdict`'s refused-report hole, guarded here for the
  same reason: a hard-set computed from a pre-refusal point is the warp
  through a new door). A refused reckon degrades to R8's measured halt —
  a snap, never F28's glide.

**Lattice:** same refusals as `halt` (requires `--zero-lead`; refused
with `--cancel-answer`, `--stop-answer`, `--arrival-carry`) **plus
`--resync`** — two `0x002C` policies whose position models fight (the pin
extrapolates PAST the last report; the resync teleports BACK to it).
`test_cancelwalk.py` §7 drives the parser, every reckon door, the pin
burst (0x002C-then-0x0028 order, payload, labels, the second-cast guard
live) and the lattice; floor 82 *(now 100 — §8.3b's fixes took it to 98
and the re-review's yield to 100)*.

**⚠ The protocol, predictions and failure signatures below are
SUPERSEDED by §8.3c** — the re-registration against the §8.3b-fixed arm.
They stand as the record of what was registered before §8.3a's review;
score no run against them (the old forward-teleport signature would
misattribute a rate-regime miss, and the protocol is blind to the
click-walk cast B1 was about).

*Protocol:* identical to R8's (§8.1) — ≥3 casts started WHILE RUNNING
mid-stride, ≥1 from standstill, ≥1 ordinary cancelled cast, both
instruments, walk-first, wall-clock alignment. Same exposure floor: ≥3
in-motion casts or the arm is VOID. One addition: **at least one running
cast pressed ~3+ s into a long straight leg** — the high-staleness case
where F31's warp was largest and the reckoning earns its keep.

*Predictions, registered before any run:*
- Cast while running → the body halts within ~0.15 s **with no backward
  component > 20 u and total across-halt displacement ≤ ~35 u** (one
  poll of forward travel at 288); the `0x002C`'s own labelled point lies
  within ~32 u of the movetap body position at the send; `sep` ≈ 0
  through the cast. F31's 110–207 u backward snap does not reproduce.
- Cast from standstill → the reckon refuses (`pin:parked`), no `0x002C`
  goes out, the `0x0028` no-ops: nothing changes in any sampled field.
- A second cast with no report between → `pin:pinned-parked`, no
  `0x002C` (the guard observed live, not just in the test).
- The cancel-instant freeze and the gate-B correlation are untouched
  throughout.
- *Failure signatures, pre-registered:* a backward snap > 20 u at a
  `pin:reckoned` cast means the reckon aimed at the wrong point — read
  the `0x002C` label for where, and the movetap track for where the body
  actually was (the delta names the model error: rate, clip, or a
  mid-leg camera curve). A forward TELEPORT ≫ 35 u means a stale
  moving-belief slipped the guards, and the guard set is incomplete.

*Decision:* pin meets the no-warp bar → it is the ship candidate for the
owner's ruling, and F28 closes with it. Pin fails backward → the
reckoning model is wrong somewhere the failure signature localises; fix
and re-run before any other message is tried. Pin fails forward → the
belief guards gain the missing door first. **Defaults are an owner
ruling; nothing ships on from this run.**

### 8.3a ⚠ DO NOT RUN R10 YET — the adversarial review found TWO BLOCKERS, and it did not finish (2026-08-25)

**Status: the review pass over `b14aa1e` is INCOMPLETE.** Of three agents,
one finished (the reckon/send-site skeptic, verdict below); the lattice/
routing reviewer and the 7-mutation prober both **died mid-run on an
account usage limit**, having applied nothing (the prober never started;
the tree was verified clean afterwards). **Re-running those two is part of
the next session's work.** What follows is the finished agent's yield,
recorded before its fixes because a finding that lives only in a
transcript is a finding that dies with the session.

**Both blockers say the same thing in two voices: the pin arm can still
warp the player, so R10 as wired does not yet meet the owner's bar.**

- **CANCELWALK-B1 (BLOCKER) — a cast during a CLICK-to-move walk warps
  backward by up to the whole click leg, and the arm scores it
  `pin:parked`.** `kbd_moving_at` is armed only by the `0x003D` arm, and
  click movement never arms it (nor does the client report position while
  click-walking — this file's own click-arm comments measure 37 s of
  silence, and the resync block 12.9 s). So the reckon refuses
  (`parked`, or `no-heading` when the click interrupted a keyboard leg)
  **while the `0x0028` still fires on a moving body** — landing it on a
  sync copy that under the shipped `--grant-suppress` sits parked at the
  leg's start (corpus separation p50 **1,164 u**, max 3,648 u). That is
  strictly worse than the 110–207 u F31 warp the owner refused, and
  §8.3's prediction table scores it "nothing changes". *Fix direction:*
  a click-in-flight belief armed in the `0x003E` arm; when live,
  **suppress the `0x0028` itself** (degrading to F28's glide, which is
  not a warp) or refuse the whole cast-stop with a `click-walk` label.
  Either way R10's protocol gains a click-walk cast and a
  `pin:parked`-with-motion failure signature.
- **CANCELWALK-B2 (BLOCKER) — the rate table covers only mt 1 and mt 4,
  so a kiting or strafing cast hard-sets the player FORWARD past the
  registered ≤ 35 u bar.** This file's own census gives forward {1,2,3}
  284.96 u/s, backward {4,5,6} 187.89, side {7,8} ~215, with mt 5–8 at
  3.2% of 7,988 corpus records; `rate = 0.66 if heading_mt == 4 else
  1.0` reckons all of them at 288. Overshoot ~45 u typical, 130–180 u at
  the straight-leg report-gap mode, and the pre-registered
  forward-teleport signature would **misattribute it to a stale belief
  rather than to a fresh rate error**. *Fix direction:* use the census
  family rates ({1,2,3} 1.0, {4,5,6} 0.652 — both OBSERVED — and {7,8}
  0.75 labelled), or refuse with an `unverified-rate` label for mt
  outside {1,2,3,4}, degrading to the halt like every other door.

**Three REAL findings, none of which is a warp but each of which is a
real defect:**
1. **The `0x002C` pairs an extrapolated POSITION with the last report's
   stale PLANE**, splitting a "position and plane are one fact"
   invariant that `--resync` never breaks (its payload is the report
   itself). The hard-set's slot 2 becomes the client's *reached* plane
   (`agent+0x80`), and the click arm already documents a stale value
   there as active corruption with fall-through-under-stairs as the
   symptom. `pm.plane_at(est, prefer=client_plane)` exists
   (`toolkit/mapdata/pathmap.py`, 189/198 agreement measured) and is not
   consulted. *Fix:* resolve the plane at `est`; refuse (new label,
   degrade to halt) when it returns None.
2. **The standing-outside suspension puts an UNCLIPPED extrapolation on
   the wire.** `clip_to_walkable`'s "off the mesh ⇒ suspend the check"
   rule is safe there because its output feeds only `state["dest"]`, the
   server's private model; here the same rule ships a raw ray — up to
   ~3.7 k u — into a hard-set of both copies, from exactly the positions
   (5.5% of stops, mesh edges) where our trapezoids are known-wrong.
   *Fix:* for a wire consumer the honest degradation is refusal —
   `(None, None, "off-mesh")`.
3. **The pin leaves the server's own integrator gliding.**
   `state["pos"]`/`state["dest"]` are untouched, so the 20 Hz tick walks
   the blend up to ~765 u past the pinned body for the cast's duration,
   and every `state["pos"]` consumer (enemy AI, the click arm's
   freshness checks) acts on a phantom. Survivable — nothing broadcasts
   from the tick, and the next report is still inside the 900 u trust
   budget because `est` and `dest` lie on the same ray — but wrong.
   *Fix:* park the model at the pin (`state["dest"] = None`, and
   defensibly `state["pos"] = est`).

**What the review CONFIRMED, so the next session need not re-derive it:**
the arithmetic core is sound (heading normalised via `hypot`, `dt` sign
guarded, `pm.clip`'s signature and tuple-return contract match the call
site); the `0x002C` routes through `send()`'s `_note_wire_move` hook,
leaving the sync model coherently parked at `est` with `ac_queue`
dropped and **no** `grant_at` stamp; belief coherence holds within the
keyboard regime (heading/`heading_mt`/`client_pos_at` all written from
the same `0x003D`; refused reports masked by the `pos_rejects` guard;
first-cast-of-session refuses `no-report`; the cancelling report itself
correctly re-opens the pin guard; **the R8 second-cast trap is genuinely
closed** by `pinned-parked`); the next `0x003D` after a pin is accepted;
and the burst order matches R8's measured slot. Also INFO: the measured
39-of-39 `0x00D2`→naming adjacency is untouched in every measured case
(all attack skills, which the scoping excludes); the pin widens the
unmeasured adrenal-non-attack insertion from one message to two.

### 8.3b The five findings FIXED, before any run (2026-08-25)

**All five of §8.3a's findings are fixed in place; `test_cancelwalk.py`
drives each fix and the floor rises 82 → 98.** The re-registration of
R10's predictions (§8.3c) waits on the two re-run review agents, because
a registration written before the review finishes would be the same
mistake §8.3a exists to prevent.

- **B1 fixed — the click-in-flight latch, and it gates BOTH arms.**
  `state["click_moving_at"]`: armed in the `0x003E` arm on EVERY click,
  answered or refused alike (the client paths it itself either way — 5
  of 5, cos 0.994–1.000, on the capture where we answered nothing);
  cleared by the next report of either kind (the `0x003D` and `0x0047`
  arms — the client speaking again is the only honest end of a leg it
  walks silently). A latch left stale by a completed click costs
  nothing: the body it guards is then parked, where the suppressed
  `0x0028` was a no-op anyway. When the latch is live the send site
  suppresses the WHOLE cast-stop — no `0x002C`, no `0x0028`, for `pin`
  and `halt` alike — degrading to F28's glide, a defect but not a warp,
  and prints the scorable `pin:click-walk` line (the label normally
  rides the `0x0028`; with it suppressed, the gamesrv log line IS the
  record). The halt arm is deliberately inside the gate: R8's measured
  3-of-3 was keyboard casts, so no measured control behaviour is lost,
  and a runnable diagnostic that can throw the body 3,648 u serves
  nothing. `cast_stop_reckon` gains the same door as its FIRST check,
  outranking even `no-report` — a first-ever movement that is a click
  must not fire the halt through another label — so an offline replay
  of the pure policy scores a click cast the way the wire behaved.
- **B2 fixed — the census family rates.** `{1,2,3}` 1.0 and `{4,5,6}`
  0.652 (both OBSERVED — FINDINGS.md's 284.96/187.89 at n=184/114;
  R8's own mt=4 tape corroborates at 190.1 against 0.652×288 = 187.8),
  `{7,8}` 0.75 (the census's ~215, n=48, the weak row — LABELLED). An
  mt outside 1..8 refuses `unverified-rate` and degrades to the halt
  like every other door: the census says 0 and 9 never appear over
  7,988 records, so that door is about a future build.
- **REAL 1 fixed — the plane is resolved AT `est`.**
  `pm.plane_at(est, prefer=client_plane)`, never the report's plane
  copied forward; `None` refuses (`no-plane`). The test proves the
  report's plane never rides the wire: a fake mesh answering 5 against
  a report saying 12 sends 5. *(As first written this was proven only
  at the pure reckon — the burst seeds all had plane 0 with a
  prefer-echoing mesh, so a payload mutation would have stayed green.
  The re-run review caught the gap and the report-12/mesh-5 case now
  runs at the BURST too, asserting the sent `0x002C`'s plane field.)*
- **REAL 2 fixed — no standing-outside suspension on the wire.** The
  reckon now REQUIRES the mesh and a walkable start: `no-mesh` and
  `off-mesh` refuse rather than ship a raw unclipped ray into a
  hard-set of both copies. The test that used to assert the suspension
  now asserts its opposite, with the reversal recorded at the check.
- **REAL 3 fixed — a sent pin parks the server's own model.**
  `state["pos"] = est`, `state["dest"] = None`, written at the pin
  send, so the 20 Hz tick stops walking a phantom up to ~765 u past
  the pinned body for the cast's duration.

**What did NOT change:** the lattice (all §8.3 refusal cells stand),
`parse_cast_stop`, the burst order (0x002C → 0x0028 → animation →
hold), the second-cast guard, and every belief the reckon already
read. The flag still ships OFF; defaults are an owner ruling.

**The re-run review pass — the two dead agents, re-run against the
fixed arm (2026-08-25, later the same day): NO BLOCKER.**
- **The 13-mutation probe: 13 of 13 RED, 0 MISSED**, in a disposable
  worktree, tree verified clean after. The registered M1–M7 (M5 adapted
  to the census table) all caught; six new mutations covering the §8.3b
  fixes themselves — the click gate deleted (both arms' wire checks
  red), the click door demoted below `no-report`, the report's plane
  shipped, the suspension restored, the park deleted, the
  `unverified-rate` door deleted — all caught. One weaker-guard note:
  under M7 the named check fired but a direct `cast_stop_pin` subscript
  then aborted the section, so its tail ran as a traceback; hardened to
  `.get()` so a missing pin note is a named FAIL.
- **The lattice/routing/test skeptic: 0 BLOCKERs, 3 REAL, 2 NIT — the
  warp-relevant surface survived every refutation attempt.** Verified
  clean live: the full composition sweep (every `cast_stop` cell against
  every lever, refusal order intact, pin×resync pairwise-first both
  ways; the B1 gate needs no lattice cell — the suppression is
  unconditional on `--grant-suppress`, and `--click-sweep` cannot
  co-fire with a pin on the same cast because any click suppresses the
  whole cast-stop); the argparse routing (`nargs='?'` swallows nothing,
  refusals fire before any socket binds); and the test's checks all
  capable of failing. The REALs were all operator-facing text, fixed in
  place: **both startup banners and the composition pin-note were never
  re-cut at the fix commit** (an armed run would have printed the
  superseded registration — rates, the do-not-run blocker text, and "the
  0x0028 goes out ALONE ... every path is scorable from the capture",
  false for click-walk where the console line is the record); **the R1
  wire-plane test gap** (above); and **the §0/§8.3/PLAN §8 staleness**
  (floors, "fix both" as if pending) — all refreshed. The NITs, both
  taken: `zero_lead_composition(cast_stop=True)` — the legacy bool —
  now raises a loud ValueError instead of arming every shared cell
  while matching neither mode's note, and the `--no-zero-lead`
  default-flip hint no longer rides pairwise refusals where following
  it costs a wasted restart. Floor 98 → **100**.

### 8.3c R10 RE-REGISTERED against the fixed arm (2026-08-25) — supersedes §8.3's protocol, predictions and failure signatures where they conflict

**Why re-registered:** §8.3's registration was written against the arm
§8.3a's review then found two warps in. The fixes are §8.3b's; this
section is the registration the owner-driven run actually runs under.
Everything §8.3 registered that survives is restated by reference, not
re-derived.

*Protocol — §8.3's stands in full* (≥3 casts started WHILE RUNNING
mid-stride, ≥1 from standstill, ≥1 ordinary cancelled cast, ≥1 running
cast ~3+ s into a long straight leg, both instruments, walk before each
cast, wall-clock alignment; exposure floor ≥3 in-motion casts or the arm
is VOID) *plus:*
- **NEW, required (B1): at least one cast pressed DURING a
  click-to-move walk** — click a distant point, press the skill
  mid-leg. This is the case §8.3a proved the old registration was blind
  to; without it the B1 fix goes unmeasured and the arm's no-warp claim
  is untested in its worst measured regime (corpus sep p50 1,164 u).
- **Recommended (B2 exposure): make one of the ≥3 running casts a
  backpedal (S-held) cast**, so the 0.652 family rate is measured. The
  arm is not VOID without it, but B2's fix then goes unmeasured and the
  §8.3a overshoot case stays theoretical either way — say so in the
  scoring rather than letting the gap pass silently.

*Predictions, registered before any run:*
- **Keyboard running cast → unchanged from §8.3:** halt within ~0.15 s,
  no backward component > 20 u, total across-halt displacement ≤ ~35 u,
  the `0x002C`'s labelled point within ~32 u of the movetap body
  position at the send, `sep` ≈ 0 through the cast; F31's 110–207 u
  snap does not reproduce.
- **Backpedal cast (if performed):** same bars, the reckon riding
  0.652 × 288 = 187.8 u/s; the old table's ~45–180 u forward miss does
  not occur.
- **Standstill → `pin:parked`,** no `0x002C`, the `0x0028` no-ops,
  nothing changes in any sampled field (unchanged).
- **Second cast with no report between → `pin:pinned-parked`,** no
  `0x002C` (unchanged).
- **Click-walk cast (NEW):** the gamesrv log prints the
  `pin:click-walk` suppression line; **NO `0x002C` and NO `0x0028` go
  out**; the body does NOT halt — it keeps click-walking through the
  cast (F28's glide, deliberately unfixed in this regime because no
  belief can place the body); **no warp at the cast or its end
  attributable to the cast-stop**; movetap shows continuous motion
  through the press; the cast/cancel machinery is otherwise untouched.
- The cancel-instant freeze and the gate-B correlation are untouched
  throughout (unchanged).

*Failure signatures, re-registered — these SUPERSEDE §8.3's:*
- **Backward snap > 20 u at `pin:reckoned`** → the reckon aimed at the
  wrong point; the `0x002C` label says where it aimed, the movetap
  track says where the body was, and the delta names the model error
  (unchanged from §8.3).
- **Forward miss ≫ 35 u at `pin:reckoned` now has TWO named causes,
  separated in this order BEFORE blaming the guards.** (1) **Rate-regime
  error:** compare movetap's measured speed over the report gap with
  the label's family rate. The unexplained slow regime (sustained
  plateaus at ½ and ⅓ of each family's cruise, 27% of forward moving
  time — movement FINDINGS.md) means the body can genuinely travel
  slower than any constant; a miss ≈ (family rate − measured speed) ×
  gap is that residual — bounded, known, NOT a guard hole. (2) **Stale
  belief:** movetap's speed matched the family rate and the pin still
  landed long — a belief slipped the guards and the guard set is
  incomplete. §8.3's signature attributed every forward miss to (2),
  which §8.3a showed would misattribute a B2-class rate miss; B2 is
  fixed, but (1) remains physically possible and must not be scored
  as (2).
- **NEW (the B1 class): any refusal label OTHER than `click-walk`
  printed while movetap shows the body MOVING at the press** —
  `pin:parked` with motion, `pin:no-report` with motion — is a belief
  hole: a motion regime our beliefs cannot see. Name the regime before
  any re-run.
- **A `pin:click-walk` suppression while movetap shows the body
  PARKED** is the stale-latch case. It costs nothing at that cast (the
  `0x0028` would have no-opped), but score it: a frequent stale latch
  means the clear sites are wrong.
- ~~**`no-plane` / `off-mesh` / `no-mesh` / `unverified-rate`** degrade
  to the bare halt (a snap bounded by the copy's staleness); expected
  rare in the test map's interior; each is scorable from the `0x0028`'s
  label, so count them rather than inferring they never fired.~~
  **SUPERSEDED by §8.3e (F34):** every refusal now suppresses the whole
  cast-stop — no bare halt exists — and the label rides the console
  line instead of a `0x0028`. Count the console lines. (R10's run
  counted zero of these doors firing.)

*Decision — unchanged from §8.3:* pin meets the no-warp bar → it is the
ship candidate for the owner's ruling, and F28 closes with it. Fails
backward → the model error the signature localises; fix and re-run
before any other message is tried. Fails forward → separate rate-regime
from belief per the signature FIRST; only a belief miss adds a guard.
**Defaults are an owner ruling; nothing ships on from this run.**

### 8.3d R10 RAN — every §8.3c bar PASSES where exposed, F31 is dead at the reckon, and the run's own yield is a NEW warp through the parked door (2026-08-25)

**The run:** owner-driven, 2026-08-25 ~13:09. Tapes:
`vault/captures/movetap/movetap-20260825T130918.jsonl` (1,143 rows) +
`vault/captures/gamesrv/authsrv-20260825T130906-c1.jsonl` (2,657 rows),
wall-clock aligned (epoch spread 3.3 ms). Scored by four agents — a
pinned-cast scorer, TWO BLIND warp-attribution skeptics given rival
hypotheses with each other's answers withheld, and an exposure auditor
— and the decisive numbers re-checked by hand at row level.

**Headline: the pin mechanism WORKS — but the arm as wired still fails
the no-warp bar, through a door §8.3c scored as "nothing changes".**

**The four `pin:reckoned` casts — every bar PASSES:**

| cast (t) | 0x002C vs body | across-halt | backward | at rest by | sep thru cast |
|---|---|---|---|---|---|
| 24.7 (mt 1) | 8.10 u | 8.09 u | 0.00 u | +0.059 s | 0.00 |
| 34.0 (mt 1) | 6.66 u | 6.66 u | 0.00 u | +0.027 s | 0.00 |
| 43.3 (mt 1) | 8.19 u | 8.20 u | 0.00 u | +0.050 s | 0.00 |
| 52.0 (mt 4) | 4.12 u | 4.12 u | 0.00 u | +0.047 s | 0.00 |

Bars: ≤32 / ≤35 / ≤20 u / ~0.15 s / ≈0. Pre-cast sep 218–260 u
collapses to 0.00 at every pin — the pin co-locates the copies —
**F31's 110–207 u backward snap does not reproduce, 4 of 4.** Burst
order and plane field correct on all four; motion resumes cleanly
after every cast (worst post-cast excursion 6.4 u over one frame).
**B2 is measured working:** cast 4 is the backpedal by three
independent witnesses (wire mt=4; pre-cast speed 187.8 u/s =
0.652 × 288 exactly; async_dir opposite travel), its pin error 4.12 u
where the old rate-1.0 table would have overshot **+53.7 u forward**;
the reckon's model residual is **−0.1 u on all four casts** (gaps
0.535–0.968 s).

**B1 is measured working, and the warp the operator saw is NOT the
cast-stop's.** The click (`0x003E`, t=85.245) armed the latch; the
cast at t=86.281 went out as animation + hold with **no 0x0028 and no
0x002C** (consecutive seqs 1981–1984 — nothing was elided), and the
`pin:click-walk` suppression line is in the gamesrv console log
(line 400). The body glided at ~288 u/s through the whole cast — the
registered F28 degradation — with **no warp at the cast**. The warp
came 11 s later, and the blind pair closed it from both ends:
- *Nothing-sent skeptic:* zero movement-capable sends between the
  click and the first post-warp report (t=97.409); the whole tape
  holds exactly four `0x002C`, all at the reckoned casts, all pre-t=70.
- *Mechanism skeptic:* the jump is 836.2 u between two client reports
  32 ms apart, landing on the body→copy line to 0.0000 u against a
  copy staleness of 864.5 u (96.7% — R9's F33 shape, which paired at
  94.3%). **F27's walk-start snap is REFUTED for this event** (the
  body sat pre-snap ≥29.3 ms AFTER the press; the landing point
  misses the parked copy by 28.2 u and matches the ANSWER-advanced
  copy to 0.45 u): **this is F33's reconcile-on-answer**, fired when
  our zero-lead answer to the first post-silence report arrived with
  sep 864.5 u above gate 1's cut. The sync copy had sat bit-still for
  26.04 s (321 identical samples) because the click was
  geometry-refused (stale) and click legs never report — F25/F27's
  regime, REALFIX's filed debt expressing through click silence.
- *Filed to REALFIX, a sharpening:* answer-arrival is NOT sufficient
  for the F33 snap — an in-walk answer at sep 505–519 u converged
  without snapping (widening R9's known non-fire from ~312 u), while
  this walk-START answer at 864.5 u snapped. The trigger looks like
  the walk-start reconcile meeting an arriving answer, not any answer.

**Also observed, unregistered: the click leg DIED at the cast.** The
body glided ~600 u through cast + aftercast, froze at exactly
(−4196, −2348) within 24 ms of the cast-end machinery, ~890 u into a
~4,600 u leg, and never resumed — wire-silent and parked 9.0 s, which
is what parked the staleness at 864.5 u for the F33 snap to spend.
Mechanism UNVERIFIED (client-side; nothing we sent names that point).
Retail stops a caster at cast START, so the ~890 u of travel is our
F28 divergence, but "the leg does not resume after a cast" may itself
be retail-like — unmeasured either way.

**Exposure audit:** in-motion casts 4/3 ✓; standstill ×2 clean ✓; the
t=70.2 cast confirmed cancelled by a W tap ✓; click-walk cast ✓;
backpedal recommendation ✓. **THIN:** the ≥3 s straight-leg case never
met the reckon — reports flowed to within 0.97 s of every reckoned
cast, so the worst tested extrapolation is ~277 u (it landed 4.2 u
off; F31's own regime was 110–207 u, so the magnitude that mattered IS
covered — what is untested is a multi-second gap). **NO-EXPOSURE:**
the second-cast `pin:pinned-parked` rep (forgotten; and it needs a
reckoned cast first — a parked cast leaves no pin to refuse).
**B1-class signature check: all three `pin:parked` labels were
CORRECT** — the body was genuinely parked at each press (3.97 s /
13.45 s / 0.30 s), no belief hole.

**CANCELWALK-F34 — the run's blocker-class yield: the `pin:parked`
door's bare `0x0028` WARPED a parked body 167.6 u backward onto a
still-converging sync copy (t=98.793, 1 of 3 parked casts).**
Row-level, re-checked by hand: the body parks at (−5325.1, −2453.8)
at its own 0x0047 stop (report 0.30 s fresh, belief CORRECT) while
the sync copy is still walking in from the post-F33 leg (sep 240.5 →
167.6 over four samples, `gate1=below` throughout — not a gate-1
event); between the rows bracketing the 0x0028 send the body jumps
167.6 u east — against its walk direction — onto the copy's exact
position (sep → 0.00), ~2,100 u/s, a teleport. **So "halts when in
motion, no-ops when parked" is refuted in this regime: the handler's
motion test evidently answers for the SYNC COPY, not the drawn body.**
R8's standstill no-ops (2 of 2) and this run's other two parked casts
(0.00 u drift) were all long parks with converged copies — the no-op
claim held only where the copies already agreed. The regime is
ordinary play, not an artifact: **stop-then-cast inside the copy's
convergence window** — the kite-stop-cast pattern — needs only a cast
within ~a second of a stop that followed any leg the copy lagged.

*Fix direction — PIN-OR-NOTHING, and why the alternatives lose:*
every reckon refusal should SUPPRESS the `0x0028` (send nothing),
exactly as `click-walk` already does — the pin pair fires whole or
not at all. (a) *Keep the bare halt* (current): warps by the copy's
lag through the parked door — measured, 167.6 u, fails Q10. (b) *Pin
at the last report when parked:* fixes THIS case (the report was
0.30 s fresh and exactly right) but hard-sets a stale point in the
camera-turn regime — a walk that sends no 0x003D (F26) under a
parked belief — which is the warp through yet another door. (c)
*Suppress:* never warps in ANY regime; the cost is that a WRONG
parked belief now degrades to F28's glide instead of a snap — and
Q10's own text prices that trade: the glide is a defect, the warp is
refused. The safety-net rationale for the bare halt ("a wrong parked
belief degrades to a snap, never a glide") is Q10-inverted and dies
here. The halt arm (R8's control) is untouched — it exists to snap.

### 8.3e F34 FIXED — PIN-OR-NOTHING — and the COMPLETION RUN registered (2026-08-25)

**The fix, wired the same day:** every reckon refusal now suppresses
the whole cast-stop, exactly as `click-walk` already did — **the pin
pair fires whole or not at all, and a bare `0x0028` never fires.** The
refusal's label rides the gamesrv console line (`pin:<door>`), which is
the scorable record; `test_cancelwalk.py` captures the console in the
burst driver and asserts the label there, drives the parked and
pinned-parked casts to wire silence, and pins the gate's three sites
(armed/disarmed/consulted once each) — floor 100 → **102**. The halt
arm (R8's control) is untouched: it exists to snap. §8.3c/§8.3d
sentences that promised "degrade to the bare halt" are superseded by
this section wherever they conflict.

**Why suppression and not a parked-pin, restated from §8.3d:** a pin
at the last report fixes the measured case (the report was 0.30 s
fresh) but hard-sets a stale point under a camera-turn walk (F26's
wire-invisible regime) — the warp through another door. Suppression
never warps in any regime; its cost is that a WRONG parked belief now
glides (F28) instead of snapping, and Q10 prices that trade: the glide
is a defect, the warp is refused.

**The completion run — three reps, registered before any run.** The
§8.3c bars stand for anything repeated; new exposure:

1. **The F34 regression rep (required):** walk a few seconds, release,
   and cast within ~1 s of stopping — the stop-then-cast inside the
   copy's convergence window. *Predicted:* the console prints
   `pin:parked`, NOTHING goes on the wire, and the body does not move
   by our hand — movetap shows zero displacement bracketing the cast
   while the sync copy finishes converging on its own. (This exact
   sequence warped 167.6 u under the previous wiring.)
2. **The second-cast rep (required, forgotten in R10's run):** cast
   while running (a reckoned pin fires), let the halt land, then cast
   AGAIN quickly without moving. *Predicted:* `pin:pinned-parked` on
   the console, nothing sent — the R8 second-cast trap observed live
   at last.
3. **The long-leg rep (required, THIN in R10's run):** run a
   dead-straight line for 3+ s — no camera drift, no strafing — and
   cast mid-stride. Straight cruise is what silences `0x003D` (the
   1.80 s chord mode; maneuvering wakes the ~0.5 s heartbeat), so
   arc-free running is the point of the rep. *Predicted:* the same
   §8.3c bars at a report gap ≥ 2 s — the reckon's extrapolation
   earning its keep past the 277 u it has been tested to.

*Failure signatures:* **any body displacement bracketing a REFUSED
cast is a regression of F34's fix** — read the console for which door
and movetap for the magnitude; the §8.3c signatures (backward =
model error; forward = rate-regime FIRST, then belief; a non-click
refusal label with motion = a B1-class belief hole) carry over
unchanged for pinned casts.

*Decision:* all three reps land as predicted → the pin arm has met the
no-warp bar in every measured regime, and it goes to the owner as the
ship candidate for F28, with the known residuals named (refusal-path
casts glide; the click-leg-death observation; the slow-plateau rate
residual). Any rep fails → its signature localises the error; fix and
re-run. **Defaults are an owner ruling; nothing ships on from this
run.**
