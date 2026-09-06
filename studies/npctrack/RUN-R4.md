# NPCTRACK-R4 — the stairs on the F14 tree: does the mirror's avoidance pass hold OUT OF SAMPLE, and does the guard stay quiet under it?

**Registered before the run.** `NPCTRACK-R4`. F14 was derived from the binary and validated on
seven tapes; the shipped default (`MIRROR_AVOID`) changed the kinematics of the one object the
keyboard re-pin guard predicts snaps from, and every number it carries was fitted on captures
that predate it. This run is the same route on a tape the pass has never seen. Same map,
harness, client build and script as `RUN-R2`/`RUN-R3`; server `main` at `6a1664d` (F14 + F15).
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
