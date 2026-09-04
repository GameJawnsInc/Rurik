# RUN-1zAJ — the retract, on a route that can actually carry the arm

**Same question as [RUN-1zAH](RUN-1zAH.md), same two arms, four runs, no human aiming.**
Registered before the run. This is RUN-1zAH re-registered with the two defects its own
result exposed (`studies/movecode/FINDINGS.md` §1z-ai) repaired: **the exposure floor
counted the wrong quantity, and the route spent most of its leads off our navmesh.**
Everything not named here is RUN-1zAH's, verbatim — same build, same flags, same arms,
same scoring, same harm bound.

**Status: REGISTERED, NOT YET RUN.**

---

## 1. What changed, and only this

### 1a. The floor now counts leads that SURVIVE THE CLIP

RUN-1zAH §3 asked for "≥ 8 `KBD LEAD` grants" and every run cleared it with 25–33. The
`lead_clip_why` census then showed **2–4 per run** at full length; the rest were
`origin-unwalkable` (an off-mesh origin degrades the lead to a **zero-distance** grant) or
mesh-clipped short. The arm under test is *a 520 u lead maturing*, and a lead that never
reached full length cannot mature into anything.

**FLOOR: ≥ 8 leads with `lead_clip_why == "clear"` per run.** `gatecensus.py` now prints
this first and names it MET / UNDER FLOOR, so it cannot be read off the wrong number
again. Run it on RUN-1zAH's own captures and it says `UNDER FLOOR (4)`.

### 1b. The route stays where the mesh can carry a lead

Measured at the desk on the server's own `PathingMap`, with `a2_clip_lead`'s exact test
(`walkable(origin)`, then `clip(origin → origin + 520·u)` at the same 2.0 u step) —
`studies/movecode/review/leadroute.py`:

| distance from map-146 spawn | origins off mesh | mean clear headings / 16 |
|---|---|---|
| 0–300 u | **0 %** | **13.6** |
| 400–500 u | 8 % | 12.2–13.2 |
| 700–900 u | 25 % | 10.8–12.2 |

RUN-1zAH's script ranged to **2,091 u** from spawn and its reports read **26 % and 48 %
origin-off-mesh**. So the map was never the problem — the script walked out of the part of
it that works. **The new script oscillates: each forward leg is answered by a backpedal,
so the character stays inside ~300 u of spawn**, where nothing is off mesh and ~85 % of
headings carry a full-length lead.

```
wait:2 W:1.5 S:2 W:1.5 S:2 Q:1.5 E:1.5 W:1.5 S:2 D:1 W:1.5 S:2 Q:1.5 E:1.5
```

13 movement legs (W 432 u forward, S 380 u back — a net drift of ~52 u per pair, ~208 u
over the script; Q/E strafes cancel; D turns in place). **Predicted: 8–12 clear leads per
run** against RUN-1zAH's 2–4.

### 1c. The REFUTES clause names the PERSISTENT lock

RUN-1zAH §2b said *"a held-key leg moving ≤ 50 u"* and that clause fired on a leg whose
lead was **zero-length**, with no `arrival-risk` row at all, following a `gate2-offmesh`
re-pin that fires in all four runs of both arms. It caught a different defect from the one
it was written for. §1z-ai separated the two objects, so this sheet names the one under
test:

> **REFUTES:** arm T shows the **persistent lock** — reported stops ≪ key legs (run A and
> C2: **1 of 7**) **and** legs armed collapsing (7 against a normal 25–33) **and** no
> re-arm afterwards — on a run where a retract fired.

A single parked leg that **recovers on the next leg** is recorded, with its lead length and
whether any `arrival-risk` row covered it, and is **not** a refutation. That is a narrowing
of the clause and it is registered here, before the run, precisely because widening one
afterwards is the move this repo does not make.

## 2. The prediction, registered

| | |
|---|---|
| **Exposure** | ≥ 8 `clear` leads per run (predicted 8–12). **Under 8 = the route still cannot carry the arm**, and the run says so instead of scoring |
| **Mechanism** (RUN-1zAH §2a, unchanged) | retracts fire in arm T where arm C logs `blocked / stale-report`; **every fired retract `prev_d` ≤ 1.0 u**; `kbd_leg act=clear by=0x002C` beside it |
| **CONFIRMS** | arm T shows no persistent lock on either run **and** arm C shows it at least once, **with the clear-lead floor met in every run** |
| **REFUTES, on safety** | any re-pin fired where the last two accepted reports were > 1.0 u apart (`repincheck.py`, exit 1) |
| **REFUTES, on effect** | §1c's persistent lock in arm T on a run where a retract fired |
| **INCONCLUSIVE** | the floor is missed, or arm C never locks (the regime did not produce the defect) |

### ★ One thing derived before the run, so it is not discovered as a surprise

**More clear leads buy more TRIALS, not better odds per lead.** A `clear` lead means our
mesh says nothing stops the body for 520 u — so a freely walking body covers its 512 u
report trigger and **re-aims before the arrival** (§1z-ae.1's photo finish, 8 u apart).
Maturation therefore still needs a body that is **parked while its key is held**, which on
a clear ray requires our mesh and the client's collision to disagree — run A's shape, and
not something this sheet can schedule. So a clean arm T here is weaker evidence than it
looks, and **the honest reading of a clean pair is "the trials went up and the lock did not
appear", not "the fix works."**

## 3. The runs

Pre-flight, arms, commands, HANDS-OFF block and scoring are **RUN-1zAH §4–§5 verbatim**,
with the walk string replaced by §1b's. Order **T, C, T, C**.

**ARM T** (runs 1, 3):

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:2 W:1.5 S:2 W:1.5 S:2 Q:1.5 E:1.5 W:1.5 S:2 D:1 W:1.5 S:2 Q:1.5 E:1.5" --hold 8 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --kbd-lead"
```

**ARM C** (runs 2, 4) — the same, plus `--no-repin-stationary-waiver`:

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:2 W:1.5 S:2 W:1.5 S:2 Q:1.5 E:1.5 W:1.5 S:2 D:1 W:1.5 S:2 Q:1.5 E:1.5" --hold 8 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --kbd-lead --no-repin-stationary-waiver"
```

Tap, per run: `python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 75`

Scoring, per capture: `gatecensus.py` (exposure first), `repincheck.py` (the harm bound,
exit 1 on a violation), `w0score.py` (verdict + per-leg travel).

## 4. Honest limits

- The header now records `agtrack_guard.STATIONARY_WAIVER` in **both** arms (§1z-ai.4 fixed
  the lazy import), so which arm produced a capture is recorded rather than remembered.
- **n is still 2 per arm**, one map, one route, one build.
- The oscillating script has **shorter legs** than RUN-1zAH's, so per-leg travel is not
  comparable to it or to run A; the clear-lead count and the lock signature are.
- A short leg ends in a `0x0047`, which **kills the in-flight lead by design** (§1z-y).
  That is the shipped gate doing its job, and it is another reason maturation stays rare —
  recorded here rather than read as a surprise afterwards.
