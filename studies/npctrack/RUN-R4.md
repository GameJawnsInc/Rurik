# NPCTRACK-R4 — the stairs on the F14 tree: does the mirror's avoidance pass hold OUT OF SAMPLE, and does the guard stay quiet under it?

**Registered before the run.** `NPCTRACK-R4`. F14 was derived from the binary and validated on
seven tapes; the shipped default (`MIRROR_AVOID`) changed the kinematics of the one object the
keyboard re-pin guard predicts snaps from, and every number it carries was fitted on captures
that predate it. This run is the same route on a tape the pass has never seen. Same map,
harness, client build and script as `RUN-R2`/`RUN-R3`; server `main` at `e23ebed` (F14 + F15).
Agent-driven, no human aiming.

## 1. Exposure

| | floor |
|---|---|
| tape samples with both client copies for agents 1 and 10 | ≥ 200 each |
| `0x0028` halts to agent 10 | ≥ 8 |
| waypoint legs on the player's sync copy (the tape's own sidesteps) | **≥ 2** — the first press and the last W leg on every run so far |
| a lead ending inside the parked hostile's disc (the wall) | ≥ 1 — the tape shows the copy halt (both target blocks invalid, `stop = 0`) |

## 2. Predictions

**P1 — THE PASS HOLDS OUT OF SAMPLE.** `avoidcensus.py --tape --cap` on the new tape: **every
waypoint leg the tape shows is matched by a mirror sidestep in the same grant window, and every
halt the mirror predicts is confirmed by the tape**, with at most ONE disagreement of either
kind (the seven-tape census had one cascade). **REFUTED IF ≥ 3** disagreements, or a predicted
halt the tape does not show.

**P2 — THE FRAME, OUT OF SAMPLE.** Mirror vs the client's world-0 while moving **p90 ≤ 30 u**
(the seven tapes: 16–25 with the pass, 76–105 without). **REFUTED IF ≥ 60 u.**

**P3 — Q1 STANDS A FOURTH TIME.** Same-instant copy-vs-client-sync at the halts p50 ≤ 30 u
(6.7 / 11.8 / 15.7 so far). REFUTED IF ≥ 40.

**P4 — THE GUARD STAYS QUIET.** `0x002C` re-pins sent: **0** (R1, R2 and R3: 0 of 0). A
sidestepping or halting mirror must not manufacture a predicted snap. **REFUTED IF ≥ 2.**

**P5 — NO REGRESSION ON THE WIRE.** Halts and fresh follows within 12–30 each over ~77 s; no two
follow orders inside 0.4 s; swings 35–50; `groundz.ok` on essentially every sample.

**P6 — recorded, not scored.** `parkcensus.py --tape --cap`: the disc parks at a standing
player land 0–18 u inside the disc (F15's 36 of 37); a park deeper than 30 u or outside by more
than 5 u is written down.

## 3. The run — scripted, agent-driven

Both from `C:\gd\Rurik`; the tape first (it waits for `Gw.exe`), then the harness. **HANDS OFF
THE KEYBOARD** once the client is up; the walk script is the whole input. The client exits with
the harness after the hold (~80 s from launch).

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 180 --wait 300 --out vault/research/npctrack/r4-agenttap.jsonl
```

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:5 shot:1 S:4 shot:1 W:5 Q:3 E:3 S:4 W:4" --hold 20 --shots 2.0 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

## 4. Scoring — decided now

```powershell
python studies/npctrack/review/avoidcensus.py --tape vault/research/npctrack/r4-agenttap.jsonl --cap <capture>
python studies/npctrack/review/parkcensus.py --tape vault/research/npctrack/r4-agenttap.jsonl --cap <capture>
python studies/npctrack/review/npcdrift.py vault/research/npctrack/r4-agenttap.jsonl
```

P1/P2 from `avoidcensus`, P3 from `npcdrift`'s instant lines, P4/P5 from the capture's send
census, P6 from `parkcensus`.

---

## RESULT — RAN 2026-09-06 15:13, 78 s, agent-driven, `main` at `ab4556c`. **P1–P5 MET, P6 as F15 predicts. F14 holds on a tape it never saw.**

Capture `authsrv-20260906T151305-c1` (`MIRROR_AVOID`, `NPC_CLIENT_MODEL`, `MODEL_LEG_BOUND`,
`MODEL_PLANE_CLIP` all true in the header), tape `r4-agenttap.jsonl` 609 of 609 paired
samples over 180 s. 38 follow orders, 22 halts, 21 model parks, 4 holds, 29 leads.

| | RUN-R4 | the seven fitted tapes |
|---|---|---|
| **P1** tape sidesteps matched / model-only / tape-only | **3 / 0 / 0**, waypoint error p50 0.1 max 0.3 u, stamps within 27–41 ms | 24 / 1 / 1, p50 0.2 |
| **P1** halts predicted / confirmed by the tape | **1 / 1** — the wall lead `(10118, 8527)`, 102 u, ending 48.5 u from the parked hostile; the copy at `(10016, 8527)`, v = 0, both target blocks invalid, from the sample before the stamp | 14 / 14 |
| **P2** mirror vs the client's world-0 while moving, p50 / p90 / max (n = 146) | **17.4 / 25.1 / 36.3** | 10.1 / 19.9 / 105 (76–105 p90 on the revert arm) |
| **P3** Q1 same-instant at the halts, p50 / over 40 u | **9.1 u / 2 of 22** | 6.7 / 11.8 / 15.7 |
| **P4** `0x002C` re-pins sent | **0** | 0 / 0 / 0 |
| **P5** follows / halts / min follow gap / `groundz.ok` | 38 / 22 / 0.509 s / 609 of 609 | R2: 38 / 23 / — |
| **P6** disc parks at a standing player: inside the disc by | **n = 8, mean 6.9 u, all inside (64.4–78.6)** | n = 37, mean 8.4, 36 of 37 |

**The three sidesteps are the route's three** (9.08 s the first press, 17.81 s the S press after
the shot, 47.67 s the last W leg), each fired at the setter with the hostile parked 64–75 u dead
ahead, waypoint 90 u to the left, the model's fire 27–41 ms before the tape's leg (the stamp
lag). No grant fired that the tape did not, none the tape shows was missed. The hybrid frame at
the 22 halts under the shipped mirror: p50 14.6 / p90 22.9 u, against npcdrift's pre-F14 mirror
on the same tape at p90 39.6. **P6, the moving-player parks that read up to 100 u** (21.76 s,
37.47 s): both are world-0's own sidestep right after the park — the player reversed into the
parked hostile, world-0 stepped 90 u aside at 288 u/s, and the sample caught it mid-step. Not a
park outside the disc; another instance of the mechanism.

**What this run does not say:** nothing about a hostile that moves while the copy sidesteps
(this route parks it first), nothing about a second hostile, nothing about the mesh arm of the
computer (no waypoint fell off the mesh here either). The seven-tape census plus this one make
27 sidesteps and 15 halts reproduced against 2 disagreements, all on one map and one route.
