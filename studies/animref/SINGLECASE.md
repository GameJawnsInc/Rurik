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
python toolkit/harness/session.py --enemy --hold 90 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
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

## CASE 6 — spacebar after a click-walk (ANIMREF-RE §37; the open item since §36)

> **Q6a: click a spot two or three steps away, and as you arrive (or a beat
> after) press spacebar with the Hatcher targeted. Does the swing start within
> a beat of arriving? Arm A vs arm B.**

> **Q6b: click a spot FAR away — at least a four-second walk — and press
> spacebar about three seconds into the walk. Arm A: does the swing wait until
> you arrive? Arm B: does it fire while you are still walking?**

Q6a is the operator's symptom (§36: click-last presses answered 60.6 % against
~91 % for stop-last). Q6b is the question that separates the derived bound
from *any* constant: every leg on the three scored captures was under 455 u, so
those tapes cannot tell a 1.5 s constant from the leg time. A four-second walk
can.

**Arm A — as shipped (the latch ends when the leg does):**

```powershell
python toolkit/harness/session.py --enemy --hold 120 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

**Arm B — the same run with §34's 3.0 s constant back:**

```powershell
python toolkit/harness/session.py --enemy --hold 120 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --click-latch-window"
```

**Do, in each arm:** Q6a three or four times (short click, spacebar on
arrival), then Q6b twice (long click, spacebar mid-walk). Nothing else.

**Answer two lines:** Q6a *"A fires on arrival / A still waits / no
difference"*; Q6b *"A waits until arrival and B fires mid-walk / both wait /
both fire mid-walk"*.

**Registered predictions, written before the run:** A answers Q6a on
arrival (the retrodiction says every one of the 13 starved presses on the
14:32 capture opens under this bound) and waits on Q6b until the body stops;
B reproduces the §36 deficit on Q6a and fires mid-walk on Q6b at the 3.0 s
mark. **If A still waits on Q6a**, the leg model's start or speed is wrong for
your click and the capture will show it — score it with

```powershell
python toolkit/authsrv/pressscore.py
```

which prints, for the newest capture, every press with its last input, the
modelled leg, the latency to the swing, and which gate refused each tick.
**If A fires mid-walk on Q6b**, the straight-line leg is shorter than the path
the client took (a bend) — the error the model states, and the size of it is
the number to bring back.

## CASE 7 — the walk-to-and-attack approach (ANIMREF-RE §38; run AFTER CASE 6)

> **Q7a: stand three or four steps from the Hatcher — clearly farther than a
> weapon's reach — and press spacebar. Arm A: does your body walk to it and
> swing as it stops, without any jump? Arm B: does it swing from where you
> stand?**

> **Q7b: click-walk AWAY from the Hatcher, and when you have stopped at the
> end of that walk, press spacebar. Arm A: does the body walk back and swing —
> and was there any jump or hitch at the moment you pressed?**

> **Q7c: stand within a step or two and press spacebar. Both arms: does it
> swing at once, as before?**

Q7a is the operator's "i can also attack from far away" (§36.4): the shipped
reach was 1500 u, never measured; retail answers a standing press at once
inside ~83–110 u and from ≥ 205 u sends a follow first, and the client's own
collision stop ends the follow 80 u out. Q7b is the snap guard: after a
click-walk the server's copy of you sits at the walk's START, and a follow
sent from there would hand your body back to it — so under arm A a `0x002C`
re-pin at the modelled end of your walk precedes the follow. On open ground
that lands within a few units of where you stand; a bent path shows as a
visible correction, and its size is what to report. Q7c is the control:
nothing inside reach changed.

**Arm A — `--attack-approach` (the candidate):**

```powershell
python toolkit/harness/session.py --enemy --hold 120 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --attack-approach"
```

**Arm B — today's default (the 1500 u reach, no approach):**

```powershell
python toolkit/harness/session.py --enemy --hold 120 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

**Do, in each arm:** Q7a twice, Q7b twice, Q7c once. Nothing else. Note the
Hatcher chases you when you are within its aggro range and stops short of you
on its own; that is fine — the follow re-paths to where it is every half
second.

**Answer three lines:** Q7a *"A walks and swings on stopping / A swings while
still walking / A never swings; B swings from afar"*; Q7b *"A walks back with
no jump / A jumps at the press (roughly how far) / A does nothing"*; Q7c
*"both swing at once / something else"*.

**Registered predictions, written before the run:** A walks to the Hatcher
and the swing opens as the body stops about 80 u out, with no `0x0028` and no
second movement message unless the Hatcher moved (then one re-path per
0.5 s); B swings from wherever you stand, as every build before did. On Q7b, A
re-pins once (a `0x002C` labelled `APPROACH RE-PIN` in the capture) and the
body does not visibly move at the press on open ground. Q7c is identical in
both arms. **If A swings before the body stops**, the server's copy arrived
first — a start latency to measure from the capture (the follow's label says
when the swing was due). **If A never swings**, the follow was refused or the
client stopped short of 80 u; the capture holds the follow and your next
report. Score with

```powershell
python toolkit/authsrv/animgrammar.py --diff --after <stamp>
```

`pressscore.py` reads the per-press table on an arm-A capture but refuses its
fork table, because its replay does not transcribe the follow leg yet and says
so.

## Notes that apply to all of them

- **`--enemy-hit 0.02` is in every `--enemy` command on purpose.** `--enemy`
  makes the Hatcher chase and attack back, which the cases need; the DEFAULT hit
  kills you in about seven seconds, which no case needs. 0.02 is a nibble: it
  still chases, still swings, you still live. (Added 2026-09-02 after the
  operator was killed mid-CASE 6.)

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
