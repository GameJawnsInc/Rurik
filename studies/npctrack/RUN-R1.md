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

## RE-RUN — the same sheet, the tape mandatory (RAN 09:43 — see the second RESULT below)

§4's two commands, unchanged; the server build now carries F8 and the tape tool creates its
directory. Score with §5. The registered
predictions stand as written, plus one from this run: **P4b — halts with the copy > 92 u from the
server's player ≤ 5 of ~13**, against this run's 27 of 37 (the pinned runs' 0 of 40 is the old
integrator's construction, not a bar).

---

## RESULT — RAN 2026-09-06 09:43, 77 s, default arm (Q1 + F8), **WITH THE TAPE.** P1 and P2 REFUTED as registered — **and the registered metric is the thing that failed**; at the halt's own instant the drift is **11.8 u** against the pinned runs' 46–68. P3 MET. P4b refuted, explained. P5 not run.

Tape `vault/research/npctrack/r1-agenttap.jsonl` (812 of 812 samples ok for both agents), capture
`authsrv-20260906T094349-c1`. Exposure: 23 halts, 38 follow orders, 21 model disc parks, 6 holds.

### P1 / P2 as registered — REFUTED, by a comparator that measures the wrong thing on this arm

| | copy vs client SYNC, **0.5 s after** the halt (registered) | over 40 u | client walking within 0.5 s of the halt |
|---|---|---|---|
| this run | **p50 76.6**, p90 146.2 | 16 of 23 | **17 of 23** |
| the pinned runs | 63.3 / 47.9 / 56.0 | 26 of 40 | 4 / 4 / 4 |

The registered metric reads the client's copy half a second after the halt. On the corridor
integrator that was fair — the hostile then stood in reach and swung, and the client stood too
(4 of 13 walking). Under the model the halt is followed by a fresh follow 0.05 s later whenever the
player kept moving (F8's hold releases the moment the client's frame is out of reach), and the
client's copy has walked 100 u or more by the time the registered metric looks. **The metric
measured the re-follow, not the drift.** That is the parked-comparator trap this repo already has a
note for, committed by the person who wrote the note, in a metric registered against the old arm's
dynamics without asking whether the new arm keeps them.

### The same quantity at the halt's OWN instant — the drift is closed

| | copy vs client SYNC **at the halt** | p75 | p90 | max | over 40 u |
|---|---|---|---|---|---|
| `1zCA` | 59.3 | 112.5 | 482.6 | 612.3 | 8 of 13 |
| `GROUNDZ-R1` | 45.7 | 75.5 | 178.3 | 193.3 | 9 of 14 |
| `GROUNDZ-R2` | 68.0 | 158.0 | 259.7 | 432.3 | 9 of 13 |
| **this run** | **11.8** | **35.3** | **72.2** | **78.4** | **4 of 23** |

On the pinned runs the two metrics agree to within 10 u (the client stood after the halt), so the
old arm's number is the same either way; on this run they differ by 65 u, and the instant one is
the comparison the arc registered in words if not in code. **And the model's own disc rows say
the same thing without any halt at all:** at each of the 21 parks the server recorded, the
server's copy against the client's sync copy at that instant is **p50 9.3 u, max 77.8** — the copy
parks where the client's copy parks. The two worst parks (77.5 and 77.8 u at 19.7 s and 20.6 s)
are the two where the live frame sat 33–35 u behind the true world-0 (the mirror's error,
NPCTRACK-Q2), exactly the residual F5 predicted.

**Read as registered: P1 and P2 are REFUTED. Read at the instant the halt was sent: the drift
went from 46–68 u to 11.8 u and the over-40 tail from two-thirds to one-sixth.** Both readings are
printed by the review tool now, with the walking count as the confound's witness. The corrected
metric is registered for the control run below as P1′ / P2′, with the pinned runs' same-instant
numbers as its bar.

### P3 — MET

The client's sync copy was still walking at the last sample before a `0x0028` on **0 of 23** halts
(pinned: 10 of 40). The halt lands on a parked body, every time.

### P4 — the wire, and P4b REFUTED with its reason

| | this run | pinned |
|---|---|---|
| follow opens / re-paths / halts | 23 / 15 / 23 | 13 / 33–39 / 13–14 |
| halts with the copy > 92 u from the server's player (P4b) | **15 of 23** | 0 of 40 |
| smallest gap between follow orders | 0.508 s | — |
| swings | 43 | 42–45 |
| plane-word classes | (0,0) 28, (29,0) 3, (29,29) 4, (0,29) 3 | the same four |
| `groundz.ok` | 812 of 812 | — |

No storm (nothing inside 0.4 s). More halts and opens than the old arm, fewer re-paths, about the
same message total (84 against 76). **P4b's 15 is the frame mismatch made visible, not a loop:**
while the player walks, the server's report track leads the client's world-0 copy by ~100 u (the
disc rows print both: e.g. at 13.3 s the frame at x=10521 and the server's player at x=10622). The
copy parks at the disc around world-0 — as the client's does — which is ~180 u short of the
server's player, so "out of reach" is true in the server's frame and false in the client's. The
old arm never printed this because its copy walked to 80 u from the server's player regardless.
Retail's mid-chase halt (§40.2, chase 3) is the same shape at a lower rate, because retail's
server player IS the frame.

### P5 — not run

No control session was driven. The three pinned runs are that arm on that route and stand in for
it on both metrics (46–68 u same-instant); a same-day control under `--no-npc-client-model` would
still be the cleaner reading and is registered below.

### Verdict

**Q1 holds at the instant the server acts** — 9 u at the park, 12 u at the halt, against 46–68 u
before — **and the prediction as registered failed**, because I registered a comparator that
assumed the old arm's dynamics. Both go on the record. The residual is the frame (Q2, the mirror's
error), and the visible cost is the halt-and-re-follow cadence behind a running player (Q6).

## RE-REGISTERED — the control run, and the corrected predictions

`--no-npc-client-model` appended inside `--game-args`, tape to
`vault/research/npctrack/r1-control-agenttap.jsonl`, scored by the same tool. **P1′:** the
control's same-instant p50 ≥ 40 u (the pinned runs read 46–68). **P2′:** the control's same-instant
over-40 fraction ≥ 50 %. **P3′:** the control's cut fraction ≥ 20 % (pinned 25 %). A control that
comes out at 12 u convicts the tape, not the fix. **RAN 10:06 — see CONTROL RESULT below.**

---

## CONTROL RESULT — RAN 2026-09-06 10:06, 77 s, `--no-npc-client-model`, with the tape. **P1′, P2′, P3′ all MET: the old arm reproduces the old drift on the instant metric, same route, same morning.** The scorer stands.

Agent-driven (no aiming, the operator's "go"); tape `vault/research/npctrack/r1-control-agenttap.jsonl`
(817 of 817), capture `authsrv-20260906T100642-c1` (header `NPC_CLIENT_MODEL: false`, no
`npc_model` rows). Wire shape identical to the pinned runs: 12 opens, 39 re-paths, 12 halts, 0
halts out of reach, 41 swings, nothing inside 0.4 s.

| copy vs the client's sync copy | control (old arm, 10:06) | Q1 + F8 (09:43) | the three pinned runs |
|---|---|---|---|
| **at the halt's own instant, p50** | **54.8** | **11.8** | 59.3 / 45.7 / 68.0 |
| p75 / p90 / max | 90.1 / 131.5 / 177.4 | 35.3 / 72.2 / 78.4 | — |
| halts over 40 u | 7 of 12 (58 %) | 4 of 23 (17 %) | 26 of 40 |
| halts landing on a walking client copy | 3 of 12 (25 %) | 0 of 23 | 10 of 40 |
| drawn hostile → drawn player at the halt, p50 | 83.5 | 101.0 | 115–125 |

**P1′ MET** (54.8 ≥ 40), **P2′ MET** (58 % ≥ 50 %), **P3′ MET** (25 % ≥ 20 %). The two arms differ by
the thing under test and nothing else, and the control lands inside the pinned runs' band.

**The registered +0.5 s metric read 21.6 u on this control** — it would have called the OLD arm
"MET" on P1 as registered. So that metric is unreliable in both directions, not merely against
the new arm: on the old arm a halt out of reach is followed by a fresh follow too (3 of 12 walking
within 0.5 s here, 12 of 40 on the pinned runs), and the walk closes the gap the halt had opened.
The instant metric is the instrument; the +0.5 s one is retired from the verdict lines and kept
only as the record of what was registered.

**One more positive control, free:** F4's model in the true frame reproduces this tape's client
copy to 10.2 u at the halts (2 of 12 over 40 u) — a fourth tape, the same result.

**Two things this control does not settle.** The drawn hostile parks closer to the drawn player on
the old arm here (83.5 u against 101 on the model arm) — one run each, and the model arm's
hostile keeps re-following a running player where the old arm's server stood and swung from an
imaginary spot; which the operator prefers to look at is a question for their next session, not
for a tape. And the mid-chase halt cadence (Q6) is the model arm's alone: 23 halts against 12.
