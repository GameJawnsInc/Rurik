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

## CASE 6 — spacebar during a click-walk, and moving while attacking (ANIMREF-RE §39; supersedes the §37 version)

> **RESULT 2026-09-02 14:06 — CLOSED.** *"all three worked as intended"* (arm A,
> capture `authsrv-20260902T140659-c1`; the wire half is FINDINGS §39.6).

> *"we're not supposed to wait to arrive before attacking. spacebar should
> cancel the move and either run to the target to get in range or start
> attacking immediately if they're already in range."* — operator, on the
> first CASE 6 run, 2026-09-02.

> *"movement cancels attacks ... in stock game, once you issue a move command
> you stop autoattacking."* — same run.

Both are now the shipped default. The first is retail's contract as §37.3 read
it and §37.5 got wrong (it built a wait); the second is measured on the live
tapes (§39: 28 of 28 mid-chain moves are followed by a re-press before the
next swing, none by a resumed chain, 39 chains end at a move). Three
questions, three revert flags — one per behaviour, so a miss on one question
names its own flag.

> **Q6a: click a spot two or three steps past the Hatcher, and while you are
> still walking press spacebar with it targeted (it is in reach). Does the
> walk stop and the swing start at once — and was there any jump or hitch at
> the moment you pressed?**

> **Q6b: click a spot far from the Hatcher (a good few seconds' walk) and
> press spacebar a second or two into the walk with it targeted (it is out
> of reach). Does your body abandon the click, turn, run to the Hatcher and
> swing as it stops, without a jump?**

> **Q6c: while auto-attacking the Hatcher, click somewhere or tap a movement
> key. Does the auto-attack stop and STAY stopped until you press spacebar
> again?**

Q6a and Q6b are the press superseding the leg: the server re-pins your body
where its model of the walk puts it (one `0x002C`, the only message that
halts the client's segment without handing the body back to the walk's
start) and then swings or follows. On open ground the re-pin lands within a
few units of where you are; a bent path shows as a visible correction at the
press, and its size is what to report. Q6c is the move rule.

**Arm A — as shipped (all three rules on):**

```powershell
python toolkit/harness/session.py --enemy --hold 120 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

**Arm B — the run you already did, for the record (all three reverted):**

```powershell
python toolkit/harness/session.py --enemy --hold 120 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --press-waits-for-leg --move-keeps-target --no-attack-approach"
```

Arm B is optional — it is the behaviour you refused, and its capture
(`authsrv-20260902T...`) already exists if you ran it. If arm A misses on one
question, the flag for that question alone is the next run:
`--press-waits-for-leg` (Q6a/Q6b), `--no-attack-approach` (Q6b),
`--move-keeps-target` (Q6c).

**Do, in arm A:** Q6a twice, Q6b twice, Q6c twice (once with a click, once
with a key). Nothing else. The Hatcher chases you and nibbles; that is fine.

**Answer three lines:** Q6a *"stops and swings at once, no jump / swings but
jumped roughly N steps / kept walking / did nothing"*; Q6b *"runs to it and
swings on stopping, no jump / jumped at the press / kept walking the click /
did nothing"*; Q6c *"stops and stays stopped / stops then resumes on its own
/ keeps attacking"*.

**Registered predictions, written before the run:** Q6a — the walk stops
where you are and the swing opens within a beat, no visible jump on open
ground. Q6b — the click is abandoned at the press, the body runs to the
Hatcher and the swing opens as it stops about 80 u out, no jump; if the
Hatcher is walking toward you the follow re-paths every half second and the
two of you meet. Q6c — the auto-attack ends at the move and does not resume;
the swing already in flight lands if it was past its landing and is cut if
not (§32's split, unchanged). **If a jump shows on Q6a or Q6b**, the leg
model's end is off by that much for that click — the capture holds the
`PRESS ENDS THE WALK` re-pin and your next report, and the distance between
them is the number.

The wire half I score from the capture:

```powershell
python toolkit/authsrv/animgrammar.py --diff --after <stamp>
```

`pressscore.py` reads the per-press table on these captures but refuses its
fork table: its replay transcribes the §37 rules, and says so.

## CASE 7 — the walk-to-and-attack approach, on its own (ANIMREF-RE §38; CASE 6's Q6b covers it too)

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

**Arm A — as shipped (the approach is the default since §39):**

```powershell
python toolkit/harness/session.py --enemy --hold 120 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

**Arm B — `--no-attack-approach` (the 1500 u reach, no follow):**

```powershell
python toolkit/harness/session.py --enemy --hold 120 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --no-attack-approach"
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
