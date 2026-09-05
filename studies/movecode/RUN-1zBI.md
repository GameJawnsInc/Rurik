# RUN-1zBI — the lead under the shipped guard: does the chain's first link still fire?

**Registered before launching**, in [FINDINGS.md](FINDINGS.md) §1z-bi.6 (committed `e32a59b`,
2026-09-05) and repeated here. `MOVECODE-1z-bj` scores it. **One run**, agent-driven, hands
off, the owner away from the keyboard by their own word.

## 1. The question

§1z-bi replayed the seven locks through the fixed guard: five begin with OUR
`gate2-offmesh` `0x002C` halting the drawn body under a held W (205–208 → 0 u/s at −3.8 s
before the press), the 520 u lead is then granted onto the halted body, and the shipped
guard (`GATE2_SEAM_TOL`, §1z-bf) licenses none of the 14 such fires in the corpus. The
derived object is the chain's FIRST LINK. Does it still fire under HEAD with the lead armed?

## 2. The configuration — the shipped default plus the opt-in lead

RUN-1zAO's fourth command **without** `--no-repin-stationary-waiver`: the guard runs as
shipped (gate-2 seam tolerance ON, stationary waiver ON, plane clip and origin test armed
by the lead), the follower present as in every locked run, the same `WSWQESW` route.

## 3. THE PREDICTION, and it can fail

| | expected |
|---|---|
| **P1** | zero `gate2-offmesh` verdicts and zero `AGTRACK RE-PIN` fires of any kind during the W holds |
| **P2** | the drawn body's tape velocity never drops below 150 u/s inside a W hold (no halt) |
| **P3** | the S-press lead lands on a body moving at ≥ 150 u/s at the press, and the body is within 100 u of the sync copy at the lead's ETA |
| — | the lock outcome (`stopcensus` trailing silence ≥ 2) is REPORTED, not scored: a clean run is consistent with a ~4/7 exposure and does not prove the lead safe; a lock with P1–P3 met names a class §1z-bi did not see |

**REFUTED IF** a `gate2-offmesh` re-pin fires (the guard fix has an exposure the corpus
lacks), or the body halts inside a W hold with no `0x002C` within 0.5 s (a client-side halt
of its own).

## 4. EXPOSURE FLOOR and ABORT

A scoreable run has ≥ 2 W holds with the body walking (tape `v` > 150 u/s for ≥ 3 s each)
and a tape whose Hatcher control reads `shut` on 100 % with zero `unread:`. A tape whose
Hatcher ever reads `open` is void (§1z-an.3). If the client never enters the map or the
tape does not attach, the run measured nothing and is written as such.

## 5. The run

> ### ⚠ HANDS OFF THE KEYBOARD ONCE THE CLIENT IS UP
>
> `--walk` drives every keypress; the script opens with `wait:3`. **The run ends on its
> own — ~75 s from launch to the window closing — and nothing is left parked.**

Terminal A (start first; it waits for a client in a map):

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 75
```

Terminal B:

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:5 S:4 W:5 Q:3 E:3 S:4 W:4" --hold 8 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --kbd-lead"
```

## 6. Scoring

`python studies/movecode/review/leadreplay.py <harness id>` (the P1–P3 columns: gate-2
fire, body v before/after, lead at the press, halt distance, arrival), then
`stopcensus.py` for the lock verdict and the tape's own fence block for the control.

---

## RESULT — RAN 2026-09-05 10:48 (harness `20260905T104856`). Scored in [FINDINGS.md](FINDINGS.md) §1z-bj.

| | |
|---|---|
| **P1** | gate-2 clause MET: 0 `gate2-offmesh` verdicts in 38 guard evaluations; the sliver report passed as `match`. One `budget-red` re-pin at 22.09 s onto a body already stationary 0.64 s (0.0 u) — the "of any kind" clause not met |
| **P2** | REFUTED by its own client-side clause: leg 3W dead for 5.0 s (0 u) with the fence OPEN and no `0x002C` in the first 0.64 s; the sync copy never baked the 106 u plane-seam-clipped lead. Reconstructed as the client's avoidance refusal (§1z-be.2) — the Hatcher parked by our follow at 76.3 u in the walk direction, 68.0 u from the lead's target. Not hooked |
| **P3** | MET on the S press: 520 u lead, body 0.4–84 u from the copy over the leg |
| lock | **NONE** — `stopcensus` `YYYYYYY` |
| separation | `w0score` moving-only p50 **26.3 u** / p90 91.9 / max 116.8 over 252 samples, body FREE; the lead-OFF default reads ~515 u on the same statistic |

Tape valid: 668 player samples over 61.5 s, Hatcher control shut, zero `unread:`.

