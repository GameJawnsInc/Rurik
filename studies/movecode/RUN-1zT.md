# RUN-1zT — does the world-0 fix actually move the client's copy?

**One question, one arm, ~90 seconds of client time.** Registered before the run,
per the probe rule: a prediction written afterwards can be rationalised into
agreeing with anything.

Behaviour under test: `MOVECODE-1z-t` / `KBD_SYNC`, shipped default ON
(`studies/movecode/FINDINGS.md` §1z-t, merged `49c2291`).

---

## 1. The question

> During an ordinary keyboard walk, is the client's WORLD-0 copy of the player
> now near the body the client DRAWS?

Nothing else. Not warps-per-minute, not a scoreboard, not an A/B — the owner's
standing direction for this arc is that a run is a single verbatim check of a
derived object, not a measurement campaign.

## 2. The prediction, registered

| | |
|---|---|
| **Baseline (already captured, 2026-09-02)** | world-0 vs drawn body **p50 237 u**, p90 431, max 516 |
| **CONFIRMS** | p50 **< 150 u** |
| **REFUTES** | p50 **> 200 u**, or the operator sees a NEW visible warp class |
| **Between 150 and 200** | INCONCLUSIVE — say so, do not round to the nearer bound |
| Offline counterfactual says | p50 0 / p90 13 / max 86 |
| The model's own error is | p90 16 u — so anything under 150 is comfortably outside it |

**There is no control arm and none is needed.** The before-picture is
`vault/research/animref/agenttap-20260902T213401.jsonl`, taken on the shipped
default four days earlier with the same client, map and instrument. Re-running
the old behaviour would spend operator minutes reproducing a number we already
hold. (If a control is ever wanted anyway: `--game-args "--legacy-kbd-sync"`.)

## 3. The exposure floor — this run can fail by measuring nothing

`w0score.py` REFUSES a verdict unless the drawn body actually translated
**≥ 500 u** across **≥ 20** moving samples. This is not ceremony:

> **In Guild Wars, A and D TURN IN PLACE. Q and E strafe.**

Every A and D leg of the 2026-09-02 kite travelled **0 u** — four of its nine
legs measured nothing, and the 15 s "report gap" that looks like a defect in
that capture is the client correctly saying nothing while the body rotates. The
walk below is **W/S for translation and Q/E for strafe** for exactly that
reason. A run that repeats `S:4 D:4 A:5 W:4` scores turn-in-place legs as
movement.

Second exposure term, and it is what scores term 2: the walk must include
**backpedal (S)** so a non-1.0 movement family occurs. On the baseline the drawn
body ran at `{190, 288}` u/s while world-0 only ever ran at 288 — the missing
`0x002B`. `w0score.py` prints both speed sets; if the fix is live, world-0's set
should now contain 190 too.

## 4. The run

**Announce it first — the machine is shared and `Gw.exe` fights for input
focus.** Check no other client is running, and that no sibling session holds the
harness. Two terminals; every line is `python …` or PowerShell.

**Terminal A — start the tap FIRST.** It waits for a client to reach a map, so
starting it early is free.

```powershell
python toolkit/clientscan/w0score.py --baseline
```

That is the scorer's positive control and costs no client time; it must print
`[PASS] control reproduces: live p50 237.0 / max 516.1`. If it does not, stop —
the scorer is wrong and nothing it says about the new capture will mean anything.

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 75
```

**Terminal B — the session.** This launches the patched loopback client, drives
a scripted keyboard walk, and closes itself. **Total ≈ 90 s from launch to the
window closing**; nothing is left parked on screen.

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:5 S:4 W:5 Q:3 E:3 S:4 W:4" --hold 8 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

`--exe` is not optional: `session.py` defaults to the newest build and every
address in this arc is **38797**. `--enemy-hit 0.02` keeps the Hatcher chasing
without killing the operator (the default kills in ~7.5 s). `--enemy` is kept so
the enemy control travels with the run for free.

**Watch the gamesrv console for the banner.** It must say:

```
[map] MOVECODE-1z-t KBD_SYNC ON by default -- ...
      TERMS LIVE  lead 520 u + navmesh clip, 0x002B family rate, 0x0047 stop echo
```

If it says `ONE TERM IS OFF`, the run is a diagnostic arm and not the shipped
default — say so when reporting it. Wire labels to expect: `KBD LEAD (x,y) from
(rx,ry)`, `KBD SPEED-TRUTH 0x002B [rate, mt]`, `KBD STOP-ECHO (x,y)`.

## 5. Scoring

```powershell
python toolkit/clientscan/w0score.py
```

(Newest capture by default; pass a path to pick one. Add
`--legs vault/captures/harness/<stamp>/report.json` for the per-leg breakdown,
which is where a turn-in-place leg announces itself.)

It prints the verdict against §2's registered bounds, refuses one on zero
exposure, and shows the enemy control (agent 10's own two copies, which stayed
p50 2.3 u on the baseline and should stay small).

## 6. What each outcome means

- **CONFIRMED (p50 < 150).** §1z-t closes. Then check the **second-order**
  question this run also answers for free: did the operator's enemy symptoms
  (swings from range / warping into the body) go with it? ANIMREF-RE §40.13
  predicts they should, with **no enemy-side change**. If they persist while
  world-0 tracks, the enemy has a second cause and §40.12 item 2 (agent-vs-agent
  collision, the `0x006011F0` dig) moves up.
- **REFUTED (p50 > 200).** Do **not** tune the lead — that is the treadmill this
  arc was pulled off. Each term has its own revert (`--no-kbd-lead`,
  `--no-kbd-speed-truth`, `--no-kbd-stop-echo`) so a single follow-up run
  convicts ONE term. The offline counterfactual says the stop echo carries most
  of the win, so `--no-kbd-stop-echo` is the first arm to try.
- **A NEW visible warp class**, at any p50, refutes independently and is more
  important than the number. The two candidates named in advance: the lead
  ordering a walk through geometry our navmesh does not refuse (the clip's
  known ~5.7% false-clip remainder, and it carries no prop geometry), and the
  AgTrack guard behaving differently now that grants are no longer past-trail
  nodes — **UNVERIFIED, and scored from the same capture**:

```powershell
python -c "import json,collections; rows=[json.loads(l) for l in open(r'vault/captures/gamesrv/<stamp>.jsonl',encoding='utf-8') if l.strip()]; c=collections.Counter((r.get('kind'),r.get('code'),r.get('why')) for r in rows if str(r.get('kind','')).startswith('agtrack')); [print(v,k) for k,v in c.most_common()]"
```

On the baseline that printed `pass/match` 10 of 10 with zero re-pin fires. The
arm is additive by construction — it can never suppress or alter a grant — so
the worst case is extra `0x002C` re-pins bounded ≤100 u at the client's own
reported position. More fires is the guard working, not a regression; what would
matter is fires clustering where the operator sees something.

## 7. Honest limits, before the fact

- **n is small.** One map, one operator, one route. The derivation rests on 9
  live captures plus one capture with world-0 ground truth; this run adds a
  second of the latter.
- **This run cannot price the click path.** `KBD_SYNC` touches only the
  `0x003D` and `0x0047` arms; clicking during the walk exercises code this
  change did not touch and whose own failures are unrelated.
- **The scorer's model is not in play here** — `w0score.py` reads the client's
  own memory through the client's own accessor. The counterfactual numbers in
  §2 come from a model, and the model is not what is being tested.
