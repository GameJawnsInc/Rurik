# RUN-1zCW — the keyboard arm's grant floor, A/B on a scripted oscillating walk

**Registered 2026-09-09 before any launch. Agent-driven: no human aiming, no human at the
keyboard.** MOVECODE-1z-cw shipped `KBD_GRANT_FLOOR = 0.0` from a desk derivation (retail answers
every heading report; 67% of world-0's lag behind the drawn body accrued under the old floor's
refusals). This is its verbatim check: the same script, the shipped arm against
`--kbd-grant-floor 0.5`, scored on the agenttap tape's world-0 vs drawn body.

## 1. The question

Does answering every heading report keep the client's world-0 copy near the drawn body, on a
walk whose reports arrive inside 0.5 s of the previous grant?

## 2. The script

Short legs alternating families, so every heading report lands inside the old floor: a key
switch ends a leg with a `0x0047` (whose stop-echo grant stamps the shared clock) and the next
`0x003D` follows within ~0.1 s; a held key re-reports at ~0.5 s. The body oscillates within
~300 u of the map-146 spawn, where RUN-1zAJ §1b measured 0% off-mesh origins.

```
wait:2 W:0.4 Q:0.4 S:0.4 E:0.4 W:0.8 Q:0.4 S:0.8 E:0.4  (x6)
```

## 3. Arms, order T C T C

**T** (shipped): `--game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"`
**C** (known-bad): the same plus `--kbd-grant-floor 0.5`

Each run: `agenttap.py --agents 1,10 --seconds 75 --out vault/research/movecode/1zcw-<arm><n>-agenttap.jsonl`
started first, then `session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "<script>" --hold 8 --game-args "<arm>"`.
Driver: `studies/movecode/review/floorrun.py`. The capture header's `KBD_GRANT_FLOOR` names the arm.

## 4. Predictions, fixed now

| | registered | scored by |
|---|---|---|
| **P1 exposure** | per run: ≥ 40 zero-lead heading evaluations and ≥ 300 moving tape samples | `floorcensus.py --ours-only --cap` |
| **P2 C reproduces the defect** | C: ≥ 40% of evaluations refused `heading-rate`; world-0 vs body moving p50 ≥ 80 u | same |
| **P3 T** | T: **zero** `heading-rate` and zero `deferred-heading` rows; world-0 vs body moving p50 **< 60 u** and **< 0.5 × C's** on each T/C pair | same |
| **P4 nothing else moves** | 0 crashes, 0 stale-pair splits, client snaps on T ≤ C | `sessionscore.py --cap` |
| **P5 watch, not a verdict** | the scripted harness's short-gap body rate (1z-cu.1's 0.72 × table class) — does it move under T? recorded either way | `modelrate.py <cap>` |

**REFUTED IF** P1 is met on both pairs and T's p50 is not below C's by ≥ 25% on both — then
§1z-cw.1's attribution is wrong (the lag has another owner) and the default is re-examined, not
tuned. **INCONCLUSIVE IF** P1 fails on any run (a script that does not produce reports inside
the floor measures nothing here).

**Not claimed:** anything about the hand-driven corner; the felt reach at halts (`haltreach.py`)
is recorded for the record, with one hostile chasing an oscillating body.

## 5. Result

### Pair 1 (T1 `authsrv-20260909T114746`, C1 `authsrv-20260909T115038`) — INCONCLUSIVE, by §4's own rule

| | T1 (floor 0.0) | C1 (floor 0.5) |
|---|---|---|
| heading evaluations | 50, all fired | 57: 43 fired, **7 refused**, 7 re-baked |
| reports inside 0.5 s of the previous grant (`since_last`) | 6 of 50 | 7 of 57 |
| moving tape samples (at the harness's ~11 Hz) | 140 (13.4 s) | 151 (13.1 s) |
| world-0 vs body, moving, p50 / p90 | **7.6 / 25.9 u** | **13.5 / 28.4 u** |
| client snaps / crashes / stale-pair splits | 0 / 0 / 0 | 0 / 0 / 0 |

P2 failed on C1 (12% refused against the registered 40%) and P1's sample floor failed on
both, so the pair proves nothing about the floor. **Why, read off the harness**: `walk_legs`
sleeps `settle` = 1.5 s after every step, so each leg ends in a `0x0047` and the next leg's
`0x003D` arrives 1.5 s after the stop-echo grant — `since_last` p50 1.72 s, p10 0.50. The
single-step plan cannot produce a heading report inside the old floor; the operator can,
because they steer with the mouse while the body keeps moving. The direction of the 7.6 vs
13.5 u difference is recorded and not scored.

**Amended before pair 2**: (1) a `steer:KEY,PX,SECONDS` walk step — the key held on its own
thread while the view right-drags in quarter-second slices, so the client reports a fresh
heading every slice while walking — and `--settle 0.3`; (2) the script becomes
`steer:W,240,3 steer:S,-240,3 steer:W,-240,3 steer:S,240,3` × 3; (3) P1's sample floor is
time-based for the harness's measured ~11 Hz tape: **≥ 20 s of moving samples**; P2 and P3
stand as registered. The agenttap rate under the harness (10.5–11.5 Hz here) is the
[[movetap-cannot-certify-under-harness]] fact again and is why the floor is in seconds.

### Pairs 2 and 3 (steering script, `--settle 0.3`) — **P1 and P2's refusal half MET, P3's pairing FAILED: REFUTED by §4's own rule**

| arm | floor | capture | evaluations | refused / re-baked | reports inside 0.5 s | moving | world-0 vs body p50 / p90 |
|---|---|---|---|---|---|---|---|
| T2 | 0.0 | `20260909T115701` | 72 | 0 / 0 | 41 of 71 | 27.0 s | **18.7 / 35.0 u** |
| C2 | 0.5 | `20260909T115902` | 126 | **54 / 54** (42.9%) | 53 of 125 | 30.8 s | **21.2 / 45.0 u** |
| T3 | 0.0 | `20260909T120108` | 72 | 0 / 0 | 43 of 71 | 32.6 s | **21.9 / 84.8 u** |
| C3 | 0.5 | `20260909T120301` | 124 | **52 / 52** (41.9%) | 51 of 123 | 26.7 s | **24.8 / 78.2 u** |

P4 held on all four: 0 client snaps, 0 stale-pair splits, 0 crashes, sessionscore HELD. The
steer step did what it was built for — 58% of reports inside the old floor, the control arm
refusing 42–43% of its evaluations, exactly the hand-driven sessions' 57% regime on the
floor's own operand. **And world-0 stayed within ~20 u of the body on both arms.** T/C ratio
0.88 on both pairs, against the registered < 0.5 and the refuted-if bar of ≥ 0.75. The
floor's own cost on this regime is **2–4 u at p50**, not the 100+ u §1z-cw.1 implied.

**What this refutes, precisely.** Not retail's contract (1z-cw.2 stands: ArenaNet answers every
report, and the default stays on that ground, harm-free here). It refutes the CAUSAL reading of
§1z-cw.1's "67% of the lag accrued under a refusal": on the hand-driven sessions refusals and
lag co-occur; on a script that reproduces the refusals without the operator's other habits, the
lag does not follow. The 130–160 u belongs to something the operator does that this script does
not, in the regime where refusals happen. Two readings tested at the desk after the runs, both
refuted on the hand-driven captures: (a) *walk-starts after a stop* — 895 of 934 refusals are
steering re-reports, not walk-starts, and only 6% of the refused-lag sits on walk-starts;
(b) *the copy's family speed lagging the body's* — movespeed ratio p50 1.00 under refusals.
What is left standing and unexplained: **39% of the refused-lag accrued with the copy PARKED
under a steering re-report refusal**, and the hand-driven regime is walls (clipped, wall-slide,
fence-shut and plane-seam leads are 8–24% of the lag on every census) where this script is
open ground. The next census is the parked copy: which grant parked it, and why a refusal
follows.

**Consequence for the next session's registration**: 1z-cw alone is now expected to move the
hand-driven world-0 lag by a few units, not to 100 u; a session under 100 u would mean
something else changed. P5 (watch): the sustained-vs-short body-rate class did not move —
forward 0.980, backpedal 0.649 on these four captures.
