# ANIMREF single-case tests — one question, one command, one answer

**Written 2026-08-31, after R5.** R5 was an omnibus: six actions in one four-minute
run, with the questions asked afterwards. Two of the six came back "idk", and that
is the sheet's fault, not the operator's — **a question you are asked after the run
is a memory test, not an experiment.**

So this file replaces that shape. Every case below is:

* **one question**, printed here before the run, phrased so the answer is
  yes / no / a number — never "did it look right";
* **one command**, copy-paste, self-terminating;
* **an A/B where one exists** — the same command with one flag, so the answer is
  a *comparison* rather than a judgement about an absolute;
* **60–90 seconds**, one thing to do.

Run one. Answer one line. Stop. Nothing here needs the others.

Common preamble for every case: PowerShell, from `C:\gd\Rurik`. All of them are
caged loopback launches on the synthetic credential. `--hold N` bounds the
session — it tears itself down by itself.

---

## CASE 1 — the quarterstep regression (R5's finding #4)

> **Q: after your character swings, how soon can you move?
> Arm A vs arm B — is one of them worse?**

This is the live defect and it is the only case that matters until it is settled.
The suspect is mine: ANIMREF-R3 fix 3 widened a zero-activation attack skill's
E4→E5 window from **0 s to ~0.775 s** on the 1.75 s hammer. Before R5 that arm
could not be switched off — the flag was missing, which is why this case exists
at all.

**Arm A — as shipped:**

```powershell
python toolkit/harness/session.py --enemy --hold 90 --game-args "--map 146 --explorable --no-enemy-skills --skills 322,105,0,0"
```

**Arm B — the same run with fix 3 reverted:**

```powershell
python toolkit/harness/session.py --enemy --hold 90 --game-args "--map 146 --explorable --no-enemy-skills --skills 322,105,0,0 --legacy-attack-e5"
```

**Do, in each arm:** press slot 1 (322, the attack skill) with the Hatcher
targeted, then **immediately try to walk**. Repeat three or four times.

**Answer one line:** *"A blocks longer / B blocks longer / no difference."*

If A is worse, fix 3 is the cause and it comes back out (the E5 timing is
corpus-derived and right; the movement lock it implies is not something the
corpus ever asked for). If both block the same, the cause is older than this
arc and Case 2 takes over.

## CASE 2 — is the auto-attack itself blocking movement?

> **Q: with NO skills on the bar at all, does a plain auto-attack block
> movement any longer than you expect from stock?**

```powershell
python toolkit/harness/session.py --enemy --hold 90 --game-args "--map 146 --explorable --no-enemy-skills --skills 0,0,0,0,0,0,0,0"
```

**Do:** click the Hatcher to auto-attack, let two or three swings land, and try
to walk away between them.

**Answer:** *"blocks / does not block"* — and if it blocks, roughly how long
(a beat / half a second / a second).

An empty bar removes every cast path, so a positive here indicts the swing
machinery itself and clears the whole cast lifecycle at a stroke.

## CASE 3 — the untargeted cast animation (R5's P1, now isolated)

> **Q: with nothing targeted, press slot 1. Does your character play a cast
> animation — yes or no?**

R5 answered this "yes" from memory and the wire agrees (the untargeted `0x009F`
form went out and the full cycle completed). This case exists to make that a
deliberate observation rather than a recollection, and to give it its A/B.

**Arm A — as shipped (untargeted casts ride `0x009F`):**

```powershell
python toolkit/harness/session.py --enemy --hold 60 --game-args "--map 146 --explorable --no-enemy-skills --skills 148,0,0,0"
```

**Arm B — the old always-`0x00A0` form:**

```powershell
python toolkit/harness/session.py --enemy --hold 60 --game-args "--map 146 --explorable --no-enemy-skills --skills 148,0,0,0 --legacy-cast-form"
```

**Do:** click empty ground to clear any target, then press slot 1. Twice.
Skill 148 is a self enchantment, so it needs no target.

**Answer:** *"A animates / B animates / both / neither."*

## CASE 4 — does the hit land mid-swing? (R5's P3)

> **Q: does the damage number appear roughly HALFWAY through the swing
> animation, or at its very start or end?**

```powershell
python toolkit/harness/session.py --enemy --hold 90 --game-args "--map 146 --explorable --no-enemy-skills --skills 0,0,0,0"
```

**Do:** attack the Hatcher and watch **one** swing at a time. Only the timing of
the number against the animation matters.

**Answer:** *"start / middle / end."*

No A/B: both windup models put the hit in the same half, so a comparison would
not discriminate. This is a sanity check on the law, not a measurement — the
measurement is already the corpus's (retail 565.2 ms at 1.33 s, ours 610.9).

## CASE 5 — the NPC cast finish (R5's P6, deferred)

> **Q: when the Hatcher finishes casting, does it return to its ready stance
> promptly, or hold the cast pose?**

```powershell
python toolkit/harness/session.py --enemy --hold 90 --game-args "--map 146 --explorable"
```

Note there is **no `--no-enemy-skills`** here — this is the one case that wants
the Hatcher casting. Stand back and watch it; do not fight.

**Answer:** *"returns promptly / holds the pose."*

---

## Notes that apply to all of them

- **Say "I did not get to it"** rather than guessing. A skipped case costs
  nothing; a guessed one costs a wrong conclusion and the run that chases it.
- Every arm writes `vault/captures/gamesrv/authsrv-<stamp>-c1.jsonl`, and I
  score the wire half from it with
  `python toolkit/authsrv/animgrammar.py --diff --after <stamp>`. **You never
  need to report anything the wire can hold** — only what the screen showed.
- If two arms are run back to back, tell me which stamp was which; the captures
  are otherwise indistinguishable and the A/B collapses.
- Nothing here needs `--practice-target`, and it should not be used: it stops
  the hostile chasing and attacking, which removes the material in cases 1, 2
  and 4.
