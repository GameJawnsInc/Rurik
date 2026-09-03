# RUN-1zT — does the world-0 fix actually move the client's copy?

**One question, one arm, ~90 seconds of client time.** Registered before the run,
per the probe rule: a prediction written afterwards can be rationalised into
agreeing with anything.

Behaviour under test: `MOVECODE-1z-t` / `KBD_SYNC`, shipped default ON
(`studies/movecode/FINDINGS.md` §1z-t, merged `49c2291`).

---

## ★ RESULT — RAN 2026-09-03 07:29 and 07:31, **CONFIRMED**

**`agenttap-20260903T073122` (the registered arm, hands off the keyboard):**

| | baseline 09-02 | **this run** |
|---|---|---|
| world-0 vs drawn body, p50 | 237.0 u | **0.0 u** |
| p75 | 340.7 | **1.0** |
| p90 | 431.3 | **17.7** |
| max | 516.1 | **198.9** |

Registered bound was p50 < 150 to confirm. **p50 is 0.0.** Exposure well over
floor: 3,572 u of body translation over 193 moving samples.

> **⚠ CAVEAT ADDED THE SAME EVENING (MOVECODE §1z-u, a skeptic lane).** This
> p50 0.0 is **contaminated by an enslaved body.** From 18.65 s — an arrival
> snap of the 15.747 s lead whose 16.211 s re-report was `heading-rate` refused
> and dropped — the drawn body's walk target equals OUR granted dest **to the
> unit on every later leg** ((9481,8430), (10014,8430), (9511,8950), (9511,8430),
> (8991,8430)), and per-leg body travel is ~520 u for both 3 s and 4 s holds
> (the Q 509 / E 513 / S 504 rows below). **World-0 vs body cannot distinguish
> "world-0 follows the body" from "the body follows world-0."** One release in
> seven produced a `0x0047`, and it followed the leg whose leads were all
> zero-length clip fallbacks. The measurement stands; the *confirmation* does
> not until a lead run is scored with an enslavement detector (async target ==
> granted dest; per-leg travel vs hold). The lead term is OPT-IN as of §1z-u.
>
> **THE DETECTOR EXISTS (MOVECODE-1z-x, same night) AND IT READS THIS CAPTURE
> ENSLAVED.** `python toolkit/clientscan/w0score.py <this tap> --legs <report.json>`
> now prints **MEASURED, CONTAMINATED** for it: the drawn body's target equals a
> server-chosen grant to the unit on **115 of 193 moving samples (59.6%)**, onset
> **17.77 s on the tap's clock** (= the 18.65 s above, which is the gamesrv
> recorder's clock, ~1.0 s ahead), Q / E / S at 100%, and BOTH later W holds moved
> the body nothing (2.9 u and 0 u — HELD KEY, BODY PARKED). The baseline reads FREE
> (0 of 130). The p50 0.0 stands as a number; the confirmation is withdrawn.

**Term 2 is visible as a number rather than an inference.** World-0's own speed
set went from a bare `[288]` on the baseline — against a body running
`{190, 288}` — to **`[190, 216, 288]`**. The `0x002B` family rate is reaching the
client and world-0 now walks the family the body is actually using. The wire
carried 12 `KBD LEAD`, 7 `KBD SPEED-TRUTH`, 1 `KBD STOP-ECHO`.

**Per leg, and this is the shape of the fix:** after the opening `W` leg (body
868 u, world-0 962 u, separation peaking at the run's 198.9 max) every subsequent
leg tracks to within a few units — `S` 743/722 u sep ≤ 24.6, `Q` 509/509 sep
≤ 6.5, `E` 513/509 sep ≤ 6.5, `S` 504/510 sep ≤ 6.3. **The residual is an
acquisition transient on the first leg, not a standing error.**

Enemy control (agent 10's own two copies) stayed p50 5.2 / max 27.9 u — faithful,
as it was before; §40.11's reading that the enemy was never the bug holds.

**The first attempt (`agenttap-20260903T072932`) is a DIFFERENT ARM and is not
the result.** The operator supplied keyboard input alongside the script, so two
input sources drove one body. It confirms too (p50 **123.0** u) but its own max
separation is **854 u — worse than the baseline it beats on the median** — and
its `wait` leg recorded 720 u of travel no script asked for. Kept as a free
second regime (a fix holding its median under double-driven input is worth
knowing) and as the reason §4 now carries a HANDS OFF block.

**The UNVERIFIED item resolved, and in the predicted direction.** §1z-t.8 flagged
that a lead makes grants stop being past-trail nodes, so the AgTrack guard would
stop MATCHing trivially. It did: the baseline was 10/10 `pass/match` with zero
re-pin fires; this run is 12 `pass/match` **plus one `veto/gate2-offmesh` and one
actual `agtrack_repin_fire`**. That is the guard doing its job on an off-mesh
grant, and the arm is additive by construction so it cannot suppress a grant.
**Two things to watch, neither a defect yet:** the clip's `origin-unwalkable`
door opened on **3 of 12** grants (the client's reported position off *our* mesh
— known coverage debt, and the door's fallback is a safe zero-distance lead), and
`agtrack_repin blocked/arrival-risk` fired **7** times, meaning clause 2 wanted a
re-pin and had no fresh accepted report to use.

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

> ### ⚠ HANDS OFF THE KEYBOARD ONCE THE CLIENT IS UP
>
> **`--walk` drives every keypress. The script's own presses ARE the arm.** The
> run opens with `wait:3`, so the character stands still for three seconds and
> looks exactly like a run waiting for you — it is not. A helpful press races
> the script, and the two input sources together produce a regime nobody
> registered.
>
> **This happened on the first attempt of 2026-09-03** and cost a whole run: the
> operator supplied inputs, the `wait` leg recorded 720 u of body travel that no
> script asked for, and the arm's own maximum separation came out at 854 u —
> *worse than the shipped baseline it was meant to beat*, on a fix that in fact
> works. It still confirmed on the median, which was luck.
>
> There is nothing to do while it runs but watch. Better still: **this run needs
> no human aiming at all, so it does not have to be handed over** — see §8.

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

## 8. Who should drive this — and it is not the operator

**This run needs no human aiming, and handing it over was a mistake.** Every
input is scripted (`--walk`), the tap sends nothing (read-only
`ReadProcessMemory`), and the session closes itself. The repo's own boundary is
AIMING, not seeing: world-anchored clicks and appearance verdicts need the
operator, a scripted keyboard walk plus a memory tap does not.

On 2026-09-03 this was written up as a two-terminal runsheet and handed over
anyway. The operator, seeing the opening `wait:3` and no note that the inputs
were scripted, supplied their own — costing one run and producing an arm whose
max separation read WORSE than the baseline on a fix that works. The two-terminal
shape also made the operator the scheduler, which is invented work.

**Next time: offer to drive it.** If the operator would rather watch, they still
should not touch the keyboard, and §4's block says so where the commands are
rather than in prose above them.
