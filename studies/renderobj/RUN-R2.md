# GROUNDZ-R2 — the stairs a third time: does the correction close the 32.5 u?

**Registered before the run.** `GROUNDZ-R2`. This scores **GROUNDZ-Q5/F9**, shipped after
[RUN-R1](RUN-R1.md) traced the ankle-deep sink to our own stale plane word.

**It is a ONE-CHANGE A/B, and that is unusual enough to say out loud.** RUN-R1 is the
known-bad arm: same route, same map, same harness, same client build. `git log` over the
interval shows exactly one commit touching any server file — `aadc3bb`, the fix itself. So a
difference between R1 and R2 is the correction, or it is noise, and nothing else.

## 1. THE NUMBER THIS HAS TO MOVE

RUN-R1, during its 22 s hold, with our own navmesh putting **both** bodies on plane-29 ground:

| | client plane | ground z |
|---|---|---|
| player | 29 | −695.904 |
| Hatcher | **0** | −663.403 |

**32.5 u apart, the Hatcher below.** That is the target.

## 2. THE EXPOSURE FLOOR — the scenario has to arise at all

The correction only fires when a hostile **arrives on a plane different from the one its last
order carried, and then stands still**. That happened in R1; it is not guaranteed to happen
again, because it depends on where the follow's arrival lands relative to the stair edge.

| | floor |
|---|---|
| tape samples with `groundz.ok` for both agents | **≥ 200** |
| samples with the player's plane column reading **29** | **≥ 20** |
| a parked stretch (Hatcher `\|v\|` = 0) of **≥ 3 s** while the player is on plane 29 | **≥ 1** |

**ABORT:** without that parked stretch the run has **zero trials** on the fix and is written as
a targeting failure. It is emphatically **not** evidence the fix works — the same words
RUN-FEEL earned, and the reason they are here in advance.

## 3. THE PREDICTIONS

**P1 — THE CORRECTION FIRES.** At least one `PLANE CORRECT` send to agent 10 in the capture.
**REFUTED IF zero while §2's parked stretch happened** — then the branch is not reached and F9
is wrong about where it lives.

**P2 — THE SINK CLOSES, and this is the one that matters.** In the parked stretch, the
Hatcher's client plane column **equals** the plane our navmesh assigns its own x/y, and the
height gap to the player is **well under 32.5 u**. **REFUTED IF the gap is still ~32 u** — then
the word is being corrected on the wire and the client is ignoring it, which would send the fix
back to the decode.

**P3 — THE CLIENT ACCEPTS A ZERO-DISTANCE GRANT.** The body does **not** move, snap or
re-orient when the correction lands. **REFUTED IF** its drawn position jumps within 0.5 s of a
`PLANE CORRECT` — a zero-distance grant should be inert on position by construction, and if it
is not, the message is the wrong vehicle.

**P4 — IT IS NOT A STORM.** `PLANE CORRECT` sends stay in single figures over the run, and none
lands inside `FOLLOW_REPATH_INTERVAL` of the previous one. **REFUTED IF** they arrive at tick
rate — the rate floor would then not be doing its job.

**P5 — NO REGRESSION.** The follow still opens, re-paths, arrives and halts; the plane words
still show the climb/sit/descend sequence RUN-1zCA established; `groundz.ok` still holds on
essentially every sample.

## 4. The run

Identical to RUN-R1 and RUN-1zCA, so all three are comparable leg for leg. Agent-driven,
scripted, no human aiming.

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:5 shot:1 S:4 shot:1 W:5 Q:3 E:3 S:4 W:4" --hold 20 --shots 2.0 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 180 --wait 300 --out vault/research/renderobj/r2-agenttap.jsonl
```

## 5. Scoring

Read §2 first and stop there if it fails. Then P1 off the capture, P2 off the tape's plane and
`groundz` columns joined to `pathmap.planes_at`, P3 off the tape around each correction, P4 off
the send timestamps, P5 against RUN-1zCA's order sequence.

**Score the wire and the tape before the screenshots**, then check one hold frame against
`hold007.png` from RUN-1zCA — the operator's own evidence for the sink, and the fairest visual
comparison available.

---

## RESULT — RAN 2026-09-06 02:40, 77 s. **The mechanism is CONFIRMED and my own payload is WRONG.** P1 met, P2 **zero trials**, **P3 REFUTED** — the correction teleports the body by however far our copy has drifted, 24.04 u here.

### P1 — MET, and better than asked: the client accepts it in 90 ms

One `PLANE CORRECT` fired, at t=22.17, telling the Hatcher plane 0 (it had 29). The tape,
with no mesh involved anywhere:

| t | client plane | ground z |
|---|---|---|
| 22.12 | 29 | −664.92 |
| **22.21** | **0** | **−654.72** |

**The plane word changed on the very next sample** — under 90 ms — and the client immediately
re-resolved its height by 10.2 u. GROUNDZ-F9's mechanism is confirmed: a zero-distance
`0x0029` does carry the plane, and the client acts on it at once.

### P2 — ZERO TRIALS, and the metric I registered was wrong anyway

The Hatcher parked at (11249, 9112), where **our navmesh has no trapezoid at all**: over 213
parked samples the plane column agrees with our mesh 0 times, disagrees 0 times, and is
unadjudicable 213 times. **We cannot tell whether its plane was right.** RUN-R1's own parked
stretch, by contrast, disagreed on 213 of 213 — (10375, 8293), client 0, our mesh 29.

So the scenario did not recur, and per §2 this scores **nothing** on the sink in either
direction. It is not evidence the fix works.

**And §1's target number was a bad metric, which is my error, not the run's.** "The height gap
to the player" measures the STAIRCASE'S SLOPE when the two bodies stand at different points —
R2's 43.8 u gap is larger than R1's 32.5 u while the planes MATCH. The metric that means
something is the one above: does the Hatcher's client plane equal the plane our mesh assigns
its own x/y. RUN-R1's 32.5 u should be quoted as *"the run where the plane was demonstrably
wrong"*, never as a threshold to beat.

### P3 — REFUTED. The grant is not zero-distance from the CLIENT's side

| t | drawn body | distance to our grant point |
|---|---|---|
| 22.12 | (10061.30, 8539.38) | 24.04 u |
| 22.21 | (10061.03, 8539.30) | 24.04 u |
| **22.30** | **(10054.72, 8562.50)** | **0.00 u** |

**The body moved 24.04 u onto our point and stayed there.** The cause is in F9's own payload:
`_npc_plane_correct` sends `agent["pos"]` — **the SERVER's copy** — and our copy had drifted
24.04 u from where the client was drawing the body. "Zero-distance" is true of our model and
false of the client's.

**CORRECTED 2026-09-06, and the correction matters: it WALKED, it did not teleport.** This
section first said "teleported", read off raw `m_point` deltas — the sample-and-hold column
this repo's own notes forbid quoting motion from. Re-measured through `w0score.live()`
(`AgAgent::position_at`, clamp first): the step across the correction is **18.43 u at 189 u/s**,
then 5.61 u at 63 u/s, then still — a decelerating walk over ~0.2 s into the point. Whole run,
**1 of 814 steps implies > 400 u/s on `live()` against 36 on the raw column**, which is the
artifact measured rather than argued.

**So the cost is a 24 u WALK of a parked hostile, not a snap.** That is milder than the warp
class this project removed for the player, and the original wording overstated it. It is still
movement we caused and P3 still fails — but it fails as a twitch, not as a teleport.

### P4 / P5

**P4:** one correction in 77 s, so no storm — but n=1 is not evidence the rate floor works.
**P5 MET:** 52 follow orders in four word classes `{(29,29): 34, (0,0): 13, (29,0): 3,
(0,29): 2}`, the climb/sit/descend sequence intact; `groundz.ok` 815 of 815 for both agents.

### What this run establishes, and what it costs

**Establishes:** the correction reaches the client and is applied within one tape sample. That
was the open question and it is answered.

**Costs:** a teleport equal to the server-client drift, every time it fires.

**`GROUNDZ-Q6`, and its first answer is a REFUTATION** (2026-09-06). The obvious repair — carry
the last point we ORDERED instead of our own copy — was measured before being written, and it
is **worse**: at the correction the last ordered point sat **48.45 u** from the drawn body
against our copy's 24.04, and across the run the ordered point is a median **195.4 u** away
(p90 421, max 574). It cannot be otherwise: the follow order names the **player's** position and
the client parks ~80 u short of it at its own disc.

**The follow message is not a safer vehicle either.** Of 52 `0x002A` in this run, 31 landed on
an already-parked body and the largest movement in the 0.35 s after was **83.23 u** (p50 0.00).
A `0x002A` on a parked body moves it too.

**So of the three candidates, F9's own payload is the CLOSEST**: our copy 24 u, the last order
48 u, the follow's target 195 u median. There is no server-side point that reliably sits on the
drawn body, because the server never learns where the client put an NPC — which is the same gap
`agenttap` exists to cover.

**Q6 therefore reduces to the DRIFT**, not to the payload: our copy sitting 24 u from the drawn
body of a *parked* hostile is the defect underneath, and it belongs to the NPC-tracking arc —
**[studies/npctrack/FINDINGS.md](../npctrack/FINDINGS.md)**, opened 2026-09-06, which measured it
at a median 53.8 u over 40 halts and shipped the client's own model as the server's copy
(NPCTRACK-Q1). (Time base note: the `t` values in this file's tables are CAPTURE seconds; the
tape's own clock starts 1.16 s later. The 90 ms claim holds in wall time: the plane word
changed +43 ms after the correction's send.)
**Do not patch this blind** — the drift
itself (our copy 24 u from the drawn body on a parked NPC) may be the more interesting defect,
and it belongs to the NPC-tracking arc rather than to this one.

**Until Q6 lands, `--no-plane-repath` is the honest arm for any run where a visible NPC jerk
would matter more than a sunken one.**

