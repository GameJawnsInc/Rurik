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

## RESULT — not yet run.
