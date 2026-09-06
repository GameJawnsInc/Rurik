# GROUNDZ-R2 — the stairs a third time: does the correction close the 32.5 u?

**Registered before the run.** `GROUNDZ-R2`. This scores **GROUNDZ-Q5/F9**, shipped after
[RUN-R1](RUN-R1.md) traced the ankle-deep sink to our own stale plane word.

**It is a ONE-CHANGE A/B, and that is unusual enough to say out loud.** RUN-R1 is the
known-bad arm: same route, same map, same harness, same client build. `git log` over the
interval shows exactly one commit touching any server file — `601fd01`, the fix itself. So a
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

**The body teleported onto our point and stayed there.** The cause is in F9's own payload:
`_npc_plane_correct` sends `agent["pos"]` — **the SERVER's copy** — and our copy had drifted
24.04 u from where the client was drawing the body. "Zero-distance" is true of our model and
false of the client's.

**That is the exact harm class this project spent the movement arc removing** — a server
message dragging a drawn body — and F9 shipped it back in on the NPC path, at 24 u, unnoticed
because the prediction that caught it was written for a different reason.

### P4 / P5

**P4:** one correction in 77 s, so no storm — but n=1 is not evidence the rate floor works.
**P5 MET:** 52 follow orders in four word classes `{(29,29): 34, (0,0): 13, (29,0): 3,
(0,29): 2}`, the climb/sit/descend sequence intact; `groundz.ok` 815 of 815 for both agents.

### What this run establishes, and what it costs

**Establishes:** the correction reaches the client and is applied within one tape sample. That
was the open question and it is answered.

**Costs:** a teleport equal to the server-client drift, every time it fires.

**`GROUNDZ-Q6`, registered, NOT patched here:** the correction must carry a point the CLIENT
already believes, not our own copy. The last point we ORDERED it to is knowable server-side and
is what the client walked toward; our copy is not. **Do not patch this blind** — the drift
itself (our copy 24 u from the drawn body on a parked NPC) may be the more interesting defect,
and it belongs to the NPC-tracking arc rather than to this one.

**Until Q6 lands, `--no-plane-repath` is the honest arm for any run where a visible NPC jerk
would matter more than a sunken one.**

