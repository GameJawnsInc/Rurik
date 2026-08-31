# ANIMREF owner runs — two questions, asked BEFORE the run

**Written 2026-08-31.** Both are loopback, caged, synthetic credential,
self-terminating (`--hold` bounds them — no window is left on your screen).
PowerShell, from `C:\gd\Rurik`. Run one, answer one line, stop.

Everything else in the arc is settled or does not need a client. These two
cannot be settled without you: **one is a model-appearance verdict** (I can
prove the bytes are on the wire and in retail's own batch order; I cannot
see the screen), **and one is the thing you actually complained about**,
where my evidence is a number and yours is the feel.

---

## CASE 1 — do the on-body effect visuals actually appear? (ANIMREF-R8)

> **Q: while the Hatcher casts at you, do you see an effect play ON your
> character that was not there before? Arm A vs arm B — is one of them
> visibly richer?**

R8 wired properties 20/21, the on-body effect visual. The ids are not
invented: they are read from the client's own `s_skill` record (+0x78 caster,
+0x7c recipient), and the corpus predicts both the value and the channel at
656/658. The verbatim run proves the client **accepts** them — 0 undecodable,
no assert, four casts firing their real ids. What no instrument here can
answer is whether anything *renders*.

**Arm A — as shipped:**

```powershell
python toolkit/harness/session.py --enemy --hold 90 --game-args "--map 146 --explorable --enemy-hit 0.02"
```

**Arm B — the same run with the channel off:**

```powershell
python toolkit/harness/session.py --enemy --hold 90 --game-args "--map 146 --explorable --enemy-hit 0.02 --no-skill-visuals"
```

**Do, in each arm:** stand still and let the Hatcher cast at you a few times
(it casts 253, 276, 289, 312 on its own — no aiming, no clicking). Watch your
own character's body.

**Answer one line:** *"A shows an effect / no difference / A looks wrong."*

If A is visibly richer, the id table is right end-to-end and R8 is done. If
there is no difference, the ids reach the client but nothing draws — which is
a real finding (it would mean the visual needs a resource the client only
loads in some other context) and it is worth more than a guess either way.
`--enemy-hit 0.02` keeps you alive so you can watch rather than respawn.

---

## CASE 2 — is the quarterstep actually fixed, by feel? (ANIMREF-R6/R7)

> **Q: press an attack skill with the Hatcher targeted, then immediately try
> to walk. Can you quarterstep now — and does it feel like stock?**

You reported *"i can't quarterstep, attacks block movement longer than
stock"*. I reproduced it unattended (a held W travelled **0.0 u for six
seconds** after a press), traced it to two server divergences, and fixed
both. The same measurement now shows a tap at press+2.1 s moving, a tap at
+4.2 s at full stride, and a held key running the whole hold at baseline
speed. That is a number. Whether it *feels* like stock is yours.

**Arm A — as shipped:**

```powershell
python toolkit/harness/session.py --enemy --hold 90 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 322,105,0,0"
```

**Arm B — the fix reverted, for contrast:**

```powershell
python toolkit/harness/session.py --enemy --hold 90 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 322,105,0,0 --legacy-attack-finish"
```

**Do, in each arm:** target the Hatcher, press slot 1 (322), and try to walk
the instant you press. Repeat three or four times.

**Answer one line:** *"A quartersteps / A still blocks / B is worse."*

Arm B should be clearly worse — it is the pre-fix wire, and its attack-skill
press also deals no damage mid-chain. If A still blocks for you where the
instrument says it moves, the residue is the first-tap partial engagement
§14 names, and that is the next thing to chase.

---

## CASE 3 — the one that decides the quarterstep fix (ANIMREF-R7a)

> **Q: with `--move-keeps-chain`, auto-attack the Hatcher and then hold W.
> Do you MOVE — and does your character keep swinging when you stop?**

This is the fork the whole fix hangs on, and it cannot be settled from the
desk. Retail keeps the chain alive through movement (87 of 100 mid-chain
moves carry no `attack_stopped`) and that is what makes the slide work: you
move AND keep attacking. Our server closes the chain on every movement
message. Removing that is ANIMREF-R7a — and when it shipped default-ON the
client froze completely, so it is opt-in today.

**But that freeze was only ever measured after an attack-SKILL press**,
where the client sits in animation state 0x11/0x15 (FINDINGS §15). A plain
auto-attack sits in state 3. Whether state 3 moves without the stop message
was never tested, and it is the difference between "LAW A ships for the
auto-attack case and the quarterstep comes back" and "the client genuinely
needs that message and the fix is somewhere else".

**Arm A — chain kept alive (the retail wire):**

```powershell
python toolkit/harness/session.py --enemy --hold 90 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --move-keeps-chain"
```

**Arm B — as shipped, for contrast:**

```powershell
python toolkit/harness/session.py --enemy --hold 90 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02"
```

**Do, in each arm:** stand in open ground (NOT against a wall — a scripted
run of mine wasted itself on exactly that), click the Hatcher to auto-attack,
let a swing or two land, then hold W right as the damage hits.

**NO INSTRUMENT SCORES THIS ONE.** The commands set up the two server arms
and nothing else; the verdict is yours by feel. **Quarterstepping cannot be
driven from the harness** — owner's ruling 2026-08-31, and it is a real
boundary rather than a preference: a scripted plan can prove the body
travelled N units, which is not the same claim as "the slide happens when I
press at the damage and it feels like stock". Four scripted runs of mine
measured travel and were each answering a slightly different question than
the one asked. Travel is a necessary condition, not the finding.

**Answer one line:** *"A slides / A frozen / A slides but stops attacking."*

* **A slides** → LAW A ships for the auto-attack case, default ON, and your
  stock quarterstep is back.
* **A frozen** → our client needs the stop message to move at all, LAW A
  cannot ship in any form, and the residue is client-side (§15's
  movement-start gate) rather than a wire fix.
* **A slides but stops attacking** → the movement is fine and the CHAIN is
  what dies; the fix is then in `attack_tick`'s target handling, not in the
  movement door.

## The one that needs a LIVE run, when you want it

§17: the swing windup law is `interval/2 − 0.1 s`, but **every swing in the
whole corpus rides attack-speed modifier 1.0** — 62 of 62 — so where the
−0.1 attaches under IAS is unmeasurable from what we have, and the client's
own duration math has no additive term to read it from. One live capture on
the secondary account **with an attack-speed stance actually running**
(Frenzy, Flurry, Tiger Stance) settles it, and the first swing under the
stance is the datum. That is a capture-campaign item, not a loopback run,
and it needs your go-ahead — `RUNBOOK.md` §"Capturing a live session".
