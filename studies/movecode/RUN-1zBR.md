# RUN-1zBR — the wall press: does the stationary waiver's SURVIVING branch ever help, or ever harm?

**Registered before launching.** `MOVECODE-1z-br`. One run, agent-driven, hands off, owner
away. This is the experiment PLAN §7 **Q15** turns on, and it is registered *because* my own
recommendation on Q15 has now flipped once already (§1z-bo.9 said keep, §1z-bq.5 said delete).
A recommendation that has moved twice on desk work should be settled by the client.

## 1. What is being asked

§1z-bn's clause refuses `{0x0047 stop → 0x003D walk-start}` and **keeps** the other two
orderings. Everything we know about the kept branch is negative:

- §1z-bo.9 — of 82 real re-pin fires, the 22 the waiver carried are **all** on the refused
  pair; **zero** on a kept pair.
- §1z-bq.2 — the waiver's founding specimen is on the refused pair too, and would have cost
  ~394 u.
- §1z-bq.1 — the kept branch's *condition* is common: **355** stale coincident pairs on kept
  orderings across 1,310 captures.
- **New, and it is why this run exists:** of those 355, **not one** ever had the guard
  evaluating a re-pin risk while reading that pair. 349 have no guard row at all, 5 are idle
  (`match` / `not-tested`). *(A sixth looked like a risk and was my own join artifact: the
  guard row 0.5 s later was reading `{0x0047 → 0x003D}` by then. A report pair and a guard
  decision are different events and must be joined by the guard's state, not by a time window
  — §1z-bo.9 did this correctly and stands.)*

So the kept branch is **unwitnessed in both directions**: never seen to help, never seen to
harm. Q15 cannot be answered from the archive, and the honest question is whether the state is
**structurally unreachable** or merely **unvisited**.

**It is reachable, and cheaply.** A `{0x003D → 0x003D}` coincident pair means the client
reported a walk-start twice at the same point — a body that was told to move and *could not*.
That is a body pressed into geometry. Raycasting map 146 from RUN-1zBO's own spawn
`(9826.0, 8077.0)`: **`S` meets non-walkable ground at 376 u — 1.31 s of held key** — and `D`
at 424 u. Hold the key past that and the body is parked against a wall with our lead still
walking away from it.

**That is RUN-1zAB run A's intended scenario**, which §1z-bq.2 has just shown run A was never
an instance of.

## 2. The configuration

RUN-1zBO's arm — `--kbd-lead` ON, the shipped clause ON — with a route built to press into
geometry rather than to run in the open:

`wait:8 S:8 W:4 D:8 S:6`

`S:8` walks 376 u and then presses into the wall for ~6.7 s; `W:4` backs off; `D:8` presses the
other wall at 424 u; `S:6` repeats the first. Four wall contacts, two headings.

## 3. THE PREDICTION

**P1 — EXPOSURE, and it gates everything.** At least **one** coincident (`d² ≤ 1.0`) stale
(> 0.347222 s) report pair on a **kept** ordering — `{0x003D → 0x003D}` or
`{0x003D → 0x0047}` — occurring **while a keyboard lead is in flight**.
**REFUTED IF none.** Then the body pressed into a wall does not produce the pair (most likely
it stops reporting entirely rather than re-reporting), the kept branch may be unreachable in
practice, and that is a real answer to Q15 — but it is a *different* answer from the one this
run is aimed at and must be written as such.

**P2 — THE DECISIVE ONE. Does the guard ever want to re-pin while reading a kept pair?**
At least one `agtrack_repin` row whose **pair at that instant** is a kept ordering, coincident
and stale, with a risk `why` (`arrival-risk` / `budget-red` / `gate1-red` / `gate2-offmesh`).
Join on the guard's own state at the decision instant, never on a time window.
**REFUTED IF none** — the waiver's surviving branch is then unreachable even when the
condition is manufactured deliberately, which closes Q15 in favour of deletion on much stronger
grounds than the archive gives.

**P3 — AND IF IT DOES: WHAT IS THE HARM?** This is the number Q15 actually needs, and both
outcomes are informative:
- **harm ≈ 0 u** — the body really is parked at the wall, the re-pin lands on it, and the
  waiver is doing exactly what §1z-ah claimed. **Q15 flips back to KEEP** and §1z-bq.5's
  recommendation is withdrawn a second time.
- **harm large** — the waiver licenses a rewind even on a kept pair, which would mean the
  clause is too narrow and the right fix is deletion, not refinement.

Harm is measured as the distance from the point we would re-pin to, to where the body actually
is by the client's own `AgAgent::position_at` (`w0score`'s live column, grouped on object
address, **never raw `m_point`**).

**P4 — THE WALL IS REAL.** The body's own travel on the `S:8` leg is **≈ 376 u**, not the
~2300 u a free 8 s run would give, confirming it met geometry where the raycast says. A leg
that travels freely means the route missed the wall and P1's null is a targeting failure.

**P5 — CONTROLS.** Both DLL controls FIRED, ring not full.

## 4. EXPOSURE FLOOR and ABORT

P4 first: at least two legs must actually stop against geometry, or the route missed and the
run scores nothing. Then P1's one kept pair with a lead in flight.

**Decided now:** P2 refuted is a *strong* result for deletion and must not be reported as
"inconclusive". P3 with harm ≈ 0 flips the recommendation and must be reported as loudly as
§1z-bq.5 was, including that my recommendation will then have moved three times.

## 5. The run

> ### ⚠ HANDS OFF THE KEYBOARD AND MOUSE ONCE THE CLIENT IS UP
>
> The driver starts the tape, the harness and the hook. **It ends on its own, ~2–3 min.**
> The character will walk into a wall and stay there. That is the experiment.

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --walk "wait:8 S:8 W:4 D:8 S:6" --hold 30 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --kbd-lead"
```

with `agenttap.py --agents 1 --seconds 100` and
`movehook/attach.py --minutes 1.1 --out vault/research/movecode/1zbr`.

## 6. Scoring

`waiverbenefit.py` and `waiverlive.py` re-run against this capture — they are the instruments
that produced the archive's negatives, so they must be the ones that score the positive if
there is one. Plus the per-decision pair join used in §1z-bq.2, and `w0score`'s live column for
P3's harm.

---

## RESULT — RAN 2026-09-05 16:13. Scored in [FINDINGS.md](FINDINGS.md) §1z-br.

Harness `20260905T161301`, PASS. **P1 REFUTED, which this sheet pre-registered as a real
answer.**

| | |
|---|---|
| **P1** | **REFUTED — zero kept-pair windows.** Both coincident stale pairs in the run are `{0x0047 → 0x003D}`, the refused ordering |
| **P2** | not reached (gated by P1). The two waiver-load-bearing decisions were both on the refused pair and both `blocked / stale-report`; `0x002C` sent = **0** |
| **P3** | not reached |
| **P4** | **MET on the capture, not on my prediction.** The raycast headings in §1 were WRONG — the client's `S` moves in −x, not +y — but the body parked twice regardless: 0.0 u across 1.73 s, and **0.0 u across 11.45 s** on the `D:8` leg |
| **P5** | MET — both controls FIRED |

**The refutation is structural and is the finding.** A body that parks emits a `0x0047`; the
next thing it emits when told to move again is a `0x003D` at that same point — which *is* the
refused pair. The keyboard path reaches a parked body only through the ordering §1z-bn already
refuses, so the waiver's surviving branch cannot be manufactured there.

**Where it does live:** of the 180 stale coincident `{0x003D → 0x003D}` pairs in the corpus,
**124 have a click in flight** and only 19 are keyboard-only. The kept branch is predominantly
a click phenomenon, and clicks are a different mover from the keyboard lead.

**Q15:** strengthened toward deletion; the click path is the named remaining gap.
