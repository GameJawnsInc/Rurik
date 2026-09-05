# RUN-1zBS — the double walk-start under the lead: can the waiver's refused half be witnessed?

**Registered 2026-09-05, `MOVECODE-1z-bs`, as OPTIONAL and NOT RUNNABLE TODAY.** It is
registered so that the next session does not re-derive the design, and it is optional because
PLAN §7 Q15 does not wait on it: the desk finding it would confirm (§1z-bs) already shipped
`WAIVER_NEWEST_MUST_BE_STOP`, and on every capture held that clause and deleting the waiver are
one object. What this run would add is the first *witnessed* rewind through the pair 1z-bn kept
— the known-bad arm this arc has never produced for that branch.

## 1. What is being asked

§1z-bs.3: a leg that opens on a coincident **double walk-start** — two `0x003D` at one point,
the second when a second key lands or the heading changes before the body leaves — is kept by
1z-bn's clause, and under a keyboard lead the guard's arrival-risk want 1–2.4 s later finds
`stationary()` True, waives the freshness gate, and fires a `0x002C` at the leg's start. The
guard replay (test §15) says so; the corpus has 446 such pairs in owner play and **zero under the
lead**. The shipped clause refuses them. So:

> On the **revert** arm (`--waiver-walkstart-pair-stands`), do chord-opened legs get rewound
> while plain legs in the same run do not? On the **shipped** arm, is the want present and
> blocked (`stale-report`) on the same openings?

The revert arm is the informative one. The shipped build can only show zero.

## 2. The configuration — DESIGNED, and the instrument it needs does not exist

**The blocker (OBSERVED from source, d2 lane).** `session.py::parse_walk` accepts one key per
step and raises on a two-character head; `walk_legs` calls `dc.hold_key`, which blocks for the
whole hold and releases in a `finally`, then sleeps a fixed 1.5 s settle. **The harness has
never pressed two keys at once.** The run needs a walk verb for two OVERLAPPING timed holds —
press key 1, press key 2 after an offset, release both — with both releases in one `finally`
(`keybd_event` is global desktop state; a stuck pair is worse than a stuck key), a `parse_walk`
unit test in `test_harness.py`, and a `TESTS.md` line in the same commit.

**The chord is W+Q or W+E, never W+A.** The harness's single keys map `W → movementType 1`,
`S → 4`, `Q → 7`, `E → 8`; the diagonals are `1→2 = +26.57°` (W+Q) and `1→3 = −26.57°` (W+E)
over n = 671 corpus transitions. **A and D are turn keys**: RUN-1zBR's `D:8` leg emitted zero
wire messages while the camera-relative heading rotated ~119°, and Q/E in the same run moved
the body 511.8 / 511.9 u. W+A would rotate, emit a stream of heading changes, and destroy the
report silence the design needs.

**The offset is 0.2–1.5 s, not 10–50 ms.** The corpus's moving double walk-starts sit at pair
gaps of 0.217–1.602 s; 20 of 22 sub-45 ms pairs are a parked body flicking keys. Sweep the
offset — 0.2 / 0.5 / 1.0 / 1.5 s — rather than plan on one value, and expect the client's
reported point to advance from rest within 20 ms (p50 3.67 u), so **coincidence is a lottery**:
22 of 205 leg-opening chord adds in the corpus (10.7 %) were coincident, 10 of 205 coincident
and stale. Whether a 0.2–1.5 s second-key offset produces a coincident pair at all is the
first thing the run measures (P0).

**Forward chords, not backward.** A forward leg reports at 512 u ≈ 1.80 s and RUN-1zBO's guard
wanted a re-pin 1.17–1.59 s into its forward legs (0.2–0.6 s of margin); a backward leg's
silence is 2.74 s and its wants land at 2.21–2.71 s (0.03 s of margin).

**Route.** RUN-1zBO's arm — `--kbd-lead` ON, map 146, no enemy, `wait:8` opening, the camera
never touched (any `yaw`/`pitch` step emits heading reports that close the stale window). Then
cycles of `<chord W+Q, offset, 2.5 s>`, `S:4`, `<chord W+E, offset, 2.5 s>`, `S:4` — the two
forward chords cancel in y, the two backward legs return ~750 u each, net drift ~−80 u in x per
cycle from spawn `(9826, 8077)` inside the box RUN-1zBO/1zBR proved open (x 8500–11450,
y 7100–9500). **Sixteen cycles, 32 chord openings, ~5 min**; `--hold 30`, `agenttap.py
--agents 1 --seconds 340`, `movehook/attach.py --minutes 5.5`.

Two arms, same binary, same route, one flag: **A** shipped; **B** `--waiver-walkstart-pair-
stands`. Run B first: if B produces no exposure, A measures nothing either.

## 3. THE PREDICTION

**P0 — THE INSTRUMENT WORKED, and it gates everything.** At least **25 of 32** chord openings
put two c2s `0x003D` on the wire, the second carrying movementType 2 or 3. **REFUTED IF fewer**
— a harness result, not a Q15 result; no null from the run is quotable.

**P1 — EXPOSURE.** At least **2** chord openings produce a coincident (d² ≤ 1.0) stale
(> 0.347222 s) `{0x003D → 0x003D}` pair with the lead in flight (`kbd_leg arm` within 0.3 s).
Expected ~3.4 at the corpus rate; P(≥ 2) ≈ 0.87 at n = 32. **REFUTED IF fewer than 2** — the
client's reported point advances too fast for a second key to catch it still on demand. That is
a fact about the client and the harness, **not** an answer about the waiver; publish the
d-versus-offset curve and stop.

**P2 — THE DECISIVE ONE, arm B.** On at least one such pair, an `agtrack_repin` row whose
**standing pair at that instant** (join on the guard's own state, never a time window) is
`{0x003D → 0x003D}`, coincident and stale, reads **`due` / arrival-risk** with `blocked_by`
None — and a `0x002C` fires. **REFUTED IF none while P1 is met** — then read the `kbd_leg
act="arm"` row's `dest` first: a re-arm whose dest equals the report point is a zero-length
lead that cannot mature (route failure, not a guard result).

**P3 — THE HARM, arm B.** The body is rewound: `w0score`'s `live` column, grouped on the
object address, shows a backward step of **300–460 u** on the chord leg (the want lands
1.2–1.6 s after the pair and the diagonal runs at ~285 u/s), and the client's `setposition` hook
site fires. **harm ≈ 0 u would mean the body was parked** and would send Q15 back the other way —
say so before launching, as RUN-1zBR did.

**P4 — THE SAME OPENINGS ON ARM A** read `blocked` / `stale-report` on the chord pair, zero
`0x002C`, no backward step: the clause moves the precondition, not the prediction.

**P5 — THE CONTROL.** The plain `S:4` legs open on `{0x0047 → 0x003D}` and fire zero `0x002C`
on both arms (RUN-1zBO's 7 of 7). Note in advance: after the first chord fire on arm B the
controls are no longer state-matched (§1z-bp.1); they control the opening-pair class only.

**P6 — DLL controls** FIRED, ring not full; the flags row read off the capture
(`agtrack_guard.WAIVER_NEWEST_MUST_BE_STOP` true on A, false on B).

## 4. EXPOSURE FLOOR and ABORT

P0 at 25 of 32, then P1 at 2. A leg travelling under 150 u is a collision; more than 6 of them
means the route left open ground and the denominator is not 32. **Decided now:** P1 null is a
harness limit and is not written as a Q15 answer; P2 null with P1 met is a strong result for
deletion (the guard would not even want a re-pin on a manufactured kept pair) once the zero-
length-lead check is clean; P3 with harm ≈ 0 flips Q15 to keep and must be reported as loudly
as §1z-bq.5 was.

## 5. The run

Not launchable until the chord verb exists. When it does, the command is RUN-1zBO's with the
route above and, for arm B, `--waiver-walkstart-pair-stands` inside `--game-args`; hands off
the keyboard and mouse once the client is up; it ends on its own in ~5–6 min.

## 6. Scoring

`waiverclick.py --list` on the capture (the pair join and the want join are the ones that
produced the corpus null, so they score the positive if there is one); `waiverbenefit.py` for the
carried-fire census; `w0score`'s `live` column for P3; the `setposition` hook count for P3's
client-side witness.
