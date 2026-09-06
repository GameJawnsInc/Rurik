# NPCTRACK-R2 — the stairs a fifth time, on the tree with the keyboard fixes in: does the frame hold up when the report track stops at the wall?

**Registered before the run.** `NPCTRACK-R2`. Same route, map, harness and client build as
`RUN-R1` and its control; the server is `main` at the commit after `da1ffc2`, which carries
Q1 + F8 (this arc) **and** MOVECODE-1z-cc's two defaults (`MODEL_PLANE_CLIP`, `MODEL_LEG_BOUND`:
the report track no longer dead-reckons 604 u through the staircase side during a silent
keyboard leg). 1z-cd shipped no default. So against `RUN-R1` (09:43) the only server change is
1z-cc — a one-change A/B for **this arc's wire during the silence**, and a second measurement of
Q1's central number, which a race measured once should not be believed on (this repo's own
note: run it twice before a mechanism claim).

## 1. What this has to reproduce, and what it has to move

| | RUN-R1 (Q1 + F8, 09:43) | control (old arm, 10:06) |
|---|---|---|
| copy vs client SYNC at the halt's own instant, p50 | **11.8 u** | 54.8 |
| halts over 40 u | 4 of 23 | 7 of 12 |
| halts landing on a walking client copy | 0 of 23 | 3 of 12 |
| follow orders during the silent leg (cap 25.4–30.3 s) naming a point > 120 u from the body's report | **7** ((10170..10616, 8524)) | — |

## 2. THE EXPOSURE FLOOR

| | floor |
|---|---|
| tape samples with both client copies for agents 1 and 10 | ≥ 200 each |
| `0x0028` halts to agent 10 in the capture | ≥ 8 |
| the silent keyboard leg at the staircase side (one `0x003D`, then no report for ≥ 3 s, then a `0x0047` at the same point) | **≥ 1** — without it P5 has zero trials and says so |

## 3. THE PREDICTIONS

**P1 — Q1 HOLDS TWICE.** Same-instant copy-vs-client-sync at the halts **p50 ≤ 30 u** (R1 11.8;
the desk 17.5). **REFUTED IF ≥ 40** — then R1 was the lucky run and F9's confirmation stands on
one sample.

**P2 — THE TAIL.** Halts over 40 u **≤ 30 %** (R1 17 %). **REFUTED IF ≥ 50 %.**

**P3 — THE HALT LANDS ON A PARKED BODY.** Walking client copy at the halt **≤ 15 %** (R1 0 %).

**P4 — NO REGRESSION ON THE WIRE.** Halts and fresh follows within 12–30 each over ~77 s; no two
follow orders inside 0.4 s; the four plane-word classes present; `groundz.ok` on essentially every
sample; swings 35–50.

**P5 — 1z-cc REACHES THIS ARC'S WIRE.** During the silent leg, **no follow order names a point
more than 120 u from the body's report point** (R1: seven orders at 158–604 u). The report track
is bounded, so the hostile is ordered toward where the player actually stands. **REFUTED IF any
order in the silence is > 200 u from the report** — then the bound is not in force on the follow's
copy of the player, and 1z-cc's fix and this arc's follow read different positions.

**P6 — recorded, not scored.** The model's own `npc_model` rows: parks and holds during the
silence. Under R1 the frame was the lead point 56 u from the copy and the copy held; with the
report track bounded the hold should still be the shape, since the lead and the frame are
unchanged by 1z-cc. Whatever it shows is written down.

## 4. The run — scripted, agent-driven, no human aiming

Both commands from `C:\gd\Rurik`; the harness launches the server with `--game-args`, the tape is
started immediately after and is mandatory (its directory now exists and the tool creates it
anyway). **HANDS OFF THE KEYBOARD** once the client is up; the walk script is the whole input.

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:5 shot:1 S:4 shot:1 W:5 Q:3 E:3 S:4 W:4" --hold 20 --shots 2.0 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 180 --wait 300 --out vault/research/npctrack/r2-agenttap.jsonl
```

## 5. Scoring — decided now

```powershell
python studies/npctrack/review/npcdrift.py vault/research/npctrack/r2-agenttap.jsonl
```

P1–P3 from the tool's instant-metric lines (P1′/P2′ there; the +0.5 s lines are printed and are
not the verdict, F9). P4 and P5 off the capture: the send census and the follow orders' points
inside the silence against the `0x003D`/`0x0047` report point that brackets it.

---

## RESULT — RAN 2026-09-06 12:47, 76 s, agent-driven, main after 1z-cd. **P1, P2, P4 MET; P3 REFUTED (5 of 23, and the mechanism is new, F13); P5 met vacuously on the registered quantity and decisively on the one that discriminates.**

Tape `vault/research/npctrack/r2-agenttap.jsonl` (675 of 675), capture `authsrv-20260906T124708-c1`
(`NPC_CLIENT_MODEL`, `MODEL_LEG_BOUND`, `MODEL_PLANE_CLIP` all true). 23 halts, 38 follow orders,
21 model parks, 5 holds.

| | RUN-R2 | RUN-R1 (09:43) | control (old arm) |
|---|---|---|---|
| copy vs client SYNC at the halt's own instant, p50 / p75 / p90 / max | **6.7 / 17.5 / 53.6 / 84.5** | 11.8 / 35.3 / 72.2 / 78.4 | 54.8 / 90.1 / 131.5 / 177.4 |
| halts over 40 u | 4 of 23 (17 %) | 4 of 23 | 7 of 12 |
| the model's own parks vs the client's copy, p50 / max | 7.5 / 60.2 (n = 21) | 9.3 / 77.8 | — |
| halts on a walking client copy | **5 of 23 (22 %)** | 0 of 23 | 3 of 12 |
| opens / re-paths / halts / out-of-reach halts / swings | 23 / 15 / 23 / 15 / 44 | 23 / 15 / 23 / 15 / 43 | 12 / 39 / 12 / 0 / 41 |

**P1 MET, twice now** — 6.7 u against 11.8, on a run whose only server change from R1 is the
keyboard arc's clip. Q1's number no longer stands on one sample. **P2 MET** (17 %). **P4 MET**:
the wire shape is R1's to the message, nothing inside 0.4 s, four plane-word classes, 675 of
675 `groundz.ok`.

**P3 REFUTED — 5 of 23 halts landed on a walking client copy, and every one of the five is the
same thing.** At the model's park instant the client's copy was parked too, within 0.6–6.4 u of
the model's point and with velocity zero. Between that park and our halt 0.3–2.7 s later the
client's copy **re-targeted itself and walked again** — a new `m_targetPoint` with no order from
us (t = 13.37 → (10596, 8503) with our last order at 12.88 naming (10522, 8431)), 24–143 u of
travel in the half second before the halt. Our `0x0028` then cut a walk the client had started on
its own. That is F13, a fact about the client the arc had not measured, and it moves P3 from a
model-fidelity metric to a question about what the client does between our orders.

**P5 — met on the registered quantity, vacuously:** no follow order went out inside the silence
on this run, and none did on R1 either (F8's hold suppressed them on both; the seven runaway
orders the sheet quoted were the 09:23 capture's, before F8). **The quantities that discriminate
are the report track's drift at the stop and what the hostile did while the player stood at the
wall:**

| capture | server player at the stop, drift | swings inside the silence | holds inside |
|---|---|---|---|
| 09:23 (pre-F8, pre-1z-cc) | 604.1 u | 0 (seven halts at one point instead) | 0 |
| 09:43 R1 (F8, pre-1z-cc) | 603.9 u | 0 (held out of reach for 5 s) | 1 |
| **12:47 R2 (F8 + 1z-cc)** | **98.0 u** | **4** | 0 |

With the report track bounded at the wall, the hostile stood 80 u from a player standing still
and swung four times — the correct behaviour — instead of holding for five seconds against a
player copy 600 u away. 1z-cc reaches this arc's behaviour, and the frame mismatch during the
silence is now the lead's length, not the leg's.

**P6.** Five holds, none inside the silence (there was nothing to hold against); 21 parks at
7.5 u median from the client's copy.
