# NPCTRACK-R1 — the stairs a fourth time: does the server's copy now stand where the client's does?

**Registered before the run.** `NPCTRACK-R1`. This scores **NPCTRACK-Q1** ([FINDINGS.md](FINDINGS.md)
F7), shipped at the desk on a model that reproduces three existing tapes; it has never met a
client with the model in the loop.

**It is a ONE-CHANGE A/B against three runs that already exist.** `1zCA`, `GROUNDZ-R1` and
`GROUNDZ-R2` are the same route, map, harness and client build, and their halts are the 40 F1
was measured on. The control arm is `--no-npc-client-model`, which is exactly their server.

## 1. THE NUMBERS THIS HAS TO MOVE

At the `0x0028` halts, the server's copy (the halt label) against the client's SYNC copy of the
Hatcher 0.5 s later:

| | p50 | p75 | p90 | halts over 40 u |
|---|---|---|---|---|
| the three pinned runs (F1) | **53.8 u** | 113.4 | 193.3 | **26 / 40** |
| the desk prediction for Q1 (F5's hybrid frame) | 17.5 | 38.0 | 78.3 | 9 / 40 |

## 2. THE EXPOSURE FLOOR

| | floor |
|---|---|
| tape samples with both client copies for agents 1 and 10 | **≥ 200** each |
| `0x0028` halts to agent 10 in the capture | **≥ 8** |
| the review tool's own refusal line absent | — |

**ABORT:** fewer halts than that is **zero trials**, and is written as a targeting failure, not as
evidence for or against Q1. The three pinned runs produced 13 / 14 / 13.

## 3. THE PREDICTIONS

**P1 — THE DRIFT CLOSES.** Copy-vs-client-sync at the halts **p50 ≤ 30 u** (desk 17.5). **REFUTED
IF p50 stays ≥ 40** — then either the model is not the client's (F4 would have to be wrong about a
running client) or the frame is worse live than replayed (Q2).

**P2 — THE TAIL SHRINKS.** Halts over 40 u **≤ 30 %** (desk 9 / 40 = 22 %; measured 65 %).
**REFUTED IF ≥ 50 %.**

**P3 — THE HALT LANDS ON A PARKED BODY.** The client's sync copy is still walking at the last tape
sample before a `0x0028` on **≤ 15 %** of halts (measured 25 %, F3). This is retail's shape (§40.2)
and the model keys the halt on its own parking. **REFUTED IF ≥ 25 %.**

**P4 — NO REGRESSION ON THE WIRE.** Follow orders, re-paths and halts in the same count band as
the pinned runs (47–53 orders, 13–14 halts over ~77 s); the plane-word sequence RUN-1zCA
established; `groundz.ok` on essentially every sample; no follow storm (no two follows to agent 10
inside 0.4 s).

**P5 — THE CONTROL IS RED.** The same route under `--no-npc-client-model` reproduces F1: p50 ≥ 40
u. A control that comes out green convicts the scorer, not the fix.

## 4. The run — scripted, agent-driven, no human aiming

Identical to `1zCA` / `GROUNDZ-R1` / `GROUNDZ-R2`. **HANDS OFF THE KEYBOARD** from the moment the
first command is issued until the capture ends; the walk script is the whole input.

Both commands run from `C:\gd\Rurik`. The harness launches the server itself with `--game-args`,
exactly as `1zCA` / `GROUNDZ-R1` / `GROUNDZ-R2` did. Terminal 1:

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:5 shot:1 S:4 shot:1 W:5 Q:3 E:3 S:4 W:4" --hold 20 --shots 2.0 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

Terminal 2, the tape, started **immediately** — not after the client is up:

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 180 --wait 300 --out vault/research/npctrack/r1-agenttap.jsonl
```

**The control arm (P5) is a second session** with `--no-npc-client-model` appended inside the
harness's `--game-args` string, its tape written to
`vault/research/npctrack/r1-control-agenttap.jsonl`.

## 5. Scoring — decided now

```powershell
python studies/npctrack/review/npcdrift.py vault/research/npctrack/r1-agenttap.jsonl
```

The tool finds the overlapping gamesrv capture itself, refuses below §2's floors, prints F1–F5
for the run and the three verdict lines for P1–P3. P4 is read off the capture's send counts and
the plane words as RUN-1zCA's scoring did; P5 is the same tool on the control tape.

**Score the tape before the screenshots.**
