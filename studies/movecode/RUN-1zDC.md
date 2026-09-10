# RUN-1zDC — the still-report class, MANUFACTURED: a scripted A/B in the corner

**REGISTERED 2026-09-10, before any launch.** `main` at `f06f547f`. Agent-driven — no human
aiming: the harness walks the body into the corner, orders the swings through its mailbox, and
taps a key into the wall on a schedule. Scores MOVECODE-1z-db + 1z-dd (the displacement gate on
BOTH doors of `cancel_on_move`), which two hand-driven attempts at RUN-1zDB could not expose
(§1z-dd.1, §1z-dd.8: a steadily held key sends no report).

## 1. Why a script, and why this shape

The class is **a `0x003D` whose position did not change, arriving inside a 0.775 s windup**. A
tap of a movement key with the body wedged in the corner sends exactly that (this morning's leg A,
14.34–17.03 s: six taps, six reports at (10488, 8117.1) with drift 0.0, no `0x0047`), and the
harness's `attack:10` reaches `begin_attack` through a mailbox polled every 50 ms tick.

**The retarget is load-bearing.** Under HEAD a still report keeps the target (1z-dd), so a plain
repeat press is a `repeat` (retail does not re-arm the swing clock, ANIMREF-RE 37.3) and the
tap's keyboard latch — never ended by a stop, because a tap into a wall sends none — would pause
the chain until the next press: after the first swing, arm A would open no second one while taps
continued (§1z-dd.4's prediction, at full strength). A press on a DIFFERENT target resets the gate
and stamps the press in both arms, so each cycle is a fresh chain: the swing at 10 opens at the
press, the tap lands ~0.15 s into its windup, identically for A and B. Hostile 11 is the second
target (`--enemies 2`; it spawns 300 u north of the arrival point, hostile 10 300 u east).

## 2. The arms

* **Arm A — HEAD.** `MOVE_CANCEL_NEEDS_DISPLACEMENT = True` (both doors gated).
* **Arm B — KNOWN-BAD.** `--no-move-cancel-displacement`: the tap's report cancels the swing
  and forgets the target.

One behavioural default. `--enemies 2 --enemy-hit 0.005 --no-enemy-skills --skills 0,…` are
shared and are not defaults under test.

## 3. The plan (identical in both arms)

Walk, along the owner's own observed path (mesh chords: 144 u S, 355 u E, 145 u E, 242 u NE
into the corner — the last is cut by the corner itself, which is the point):

```
wait:2 yaw:375 yaw:375 yaw:375 W:0.5 wait:0.8 yaw:-370 yaw:-370 yaw:-369 W:1.23 wait:0.8
yaw:-81 W:0.5 wait:0.8 yaw:-531 W:1.0 wait:1.5
```

then 20 cycles of `attack:10 W:0.3 wait:0.5 attack:11 wait:0.8` at `--settle 0.1`: the swing at
10 opens at the press (mailbox ≤ 50 ms), the tap's `0x003D` arrives ~0.15 s later, the retarget
to 11 at ~1.1 s (its swing lands at ~1.9 s, before the next press at 2.1 s).

## 4. Predictions, fixed BEFORE the run

* **Floors.** ≥ 12 `player swings at 10` per arm; in arm B ≥ 8 windups containing a sub-1 u
  `0x003D` (expected: 20). Hostile 10 dies in arm A around cycle 12–13 (5–12 damage a swing on
  100 HP) and is back 8 s later; cycles against its corpse are `dead-target` rows, not swings.
* **P1.** Arm B: still-cancels ≥ 50 % of swings at 10 (expected ~100 %, `cancel:movement`).
  Arm A: **0** — no `cancel:movement`, no `move-ended-order`, and a `chain cancel SUPPRESSED`
  print for every tap that landed in a windup.
* **P2.** Arm A lands ≥ 80 % of its swings at 10; arm B ≤ 50 %.
* **P3.** Every non-landing swing at 10 carries a `swing_verdict` row, either arm.
* **P5, a free read.** Arm A's `chain_pause` rows show `charged` > 0 on the kept-target chain
  (the tap→press interval, ~0.4–0.9 s a cycle) — §1z-dd.4's freeze, measured small; arm B's
  show `no-target`.
* **The walk.** The body is within 60 u of (10488, 8117) at the first press, on the tape; both
  hostiles park within 120 u of it.

**ABORT:** the body is not within 60 u of the corner at the first press (the taps then MOVE it,
the reports are not still, and both arms cancel on a real move — visible as tap reports with
displacement > 1 u); or arm B under its floor. Then neither arm is readable.

## 5. The run

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10,11 --seconds 100 --wait 300 --out vault/research/movecode/1zdc1-agenttap.jsonl
```

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --settle 0.1 --hold 3 --walk "wait:2 yaw:375 yaw:375 yaw:375 W:0.5 wait:0.8 yaw:-370 yaw:-370 yaw:-369 W:1.23 wait:0.8 yaw:-81 W:0.5 wait:0.8 yaw:-531 W:1.0 wait:1.5 attack:10 W:0.3 wait:0.5 attack:11 wait:0.8 …(×20)" --game-args "--map 146 --explorable --no-enemy-skills --enemies 2 --enemy-hit 0.005 --skills 0,0,0,0,0,0,0,0"
```

Arm B: the same with `1zdc2` and `--no-move-cancel-displacement` appended to the game args.
HANDS OFF THE KEYBOARD AND MOUSE for the whole run (~75 s each); the harness owns the input.

## 6. Scoring

`swingcensus.py --cap` on both; the exposure/verdict script on both; the tape join for the walk.
