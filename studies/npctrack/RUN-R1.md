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

Terminal 2, the tape, started **immediately** — not after the client is up. **WITHOUT THIS FILE THE
RUN SCORES NOTHING: P1–P3 read the client's copies, which only the tape carries.** The first
attempt (below) ran without it.

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

---

## RESULT — RAN 2026-09-06 09:23, 77 s, default arm, **WITHOUT THE TAPE.** P1–P3 ZERO TRIALS; **P4 REFUTED on the wire, and the cause is fixed (NPCTRACK-F8)**; P5 not run.

**The tape was never written, and that was this sheet's fault.** The operator ran the tape command
both times; `agenttap.py` found the client and then died at `open()` with `FileNotFoundError`,
because it created a directory only for its DEFAULT path and this sheet named a new arc's
directory that did not exist yet. (The first write-up here said the tool creates the directory
before writing a byte — wrong, and corrected the same morning when the operator pasted the
traceback.) The tool now makes the directory for an explicit `--out` too. Everything P1–P3 need
(the client's sync copy at each halt) is on the tape and nowhere else, so per §2 this is a
targeting failure: **zero trials on Q1's central claim, in either direction.** A second attempt at
09:38 was cut at 5 s when the tape crashed again; its capture is on the F8 build and shows one
follow, one halt, and the first `npc_model` row.

**What the capture alone could say — P4, and it went RED.**

| | this run | the three pinned runs |
|---|---|---|
| follow opens / re-paths / halts | **37 / 14 / 37** | 13 / 37 / 13 · 14 / 33 / 14 · 13 / 39 / 13 |
| halts with the copy > 92 u from the server's player | **27 of 37** | 0 of 40 |
| smallest gap between two follow orders | 0.508 s | — |
| swings by agent 10 | 41 | 42 · 45 · 43 |
| plane-word classes on the follows | (0,0) 16, (29,29) 18, (29,0) 13, (0,29) 4 | the same four |

Not a per-tick storm (no two orders inside 0.4 s) but a **half-second loop**: halt, fresh follow
0.05 s later, park, halt. Seven halts at (10081, 8565) between t=26.46 and 29.81 while the label
said the player was 237 → 394 → 537 u away.

**The mechanism, read off the capture.** At t=25.34 the client sent one `0x003D` heading from
(10012, 8524); the server answered a `0x0025` and a lead grant to (10120, 8524) and armed a
keyboard leg. **Then nothing for five seconds** — and the `0x0047` at 30.32 reports (10012, 8524)
again: the body never moved (the route's W leg into the staircase side). The server's report
track dead-reckoned `state["pos"]` to (10616, 8524), 604 u from the body; the client's world-0
copy sat at our lead point, 56 u from the hostile's copy. **The model parked at once in that
frame, exactly as the client's resolver would** (inside 80 u, inside the cone). The follow-open
test, unchanged from the old integrator, then read the report track — 537 u away — and opened a
fresh follow, which parked at once again. The pinned runs had the same silent stretch (RUN-R2's
T1 = 317 u at its t=26.87); the old integrator hid it by walking its copy to 80 u from the
fictional player and swinging from there.

**The fix — NPCTRACK-F8, shipped 2026-09-06.** The open rule runs in both frames: a copy already
inside the swing reach of where the CLIENT believes the player stands, and inside the ±60° cone of
the leg it would be ordered, is not re-followed until that belief moves; it does not swing either,
because the swing reads the server's own player. During the mismatch it stands where the client
draws it. `test_agentlife` `section_client_model` pins the hold and the release (three checks for
the old two); green 333. The model now also records every disc park and every hold into the
capture (`npc_model` rows with the frame it used), so the next run explains a park without a tape.

**P5 was not run** (no control session).

## RE-RUN — the same sheet, the tape mandatory

§4's two commands, unchanged; the server build now carries F8 and the tape tool creates its
directory. Score with §5. The registered
predictions stand as written, plus one from this run: **P4b — halts with the copy > 92 u from the
server's player ≤ 5 of ~13**, against this run's 27 of 37 (the pinned runs' 0 of 40 is the old
integrator's construction, not a bar).
