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

## The one that needs a LIVE run, when you want it

§17: the swing windup law is `interval/2 − 0.1 s`, but **every swing in the
whole corpus rides attack-speed modifier 1.0** — 62 of 62 — so where the
−0.1 attaches under IAS is unmeasurable from what we have, and the client's
own duration math has no additive term to read it from. One live capture on
the secondary account **with an attack-speed stance actually running**
(Frenzy, Flurry, Tiger Stance) settles it, and the first swing under the
stance is the datum. That is a capture-campaign item, not a loopback run,
and it needs your go-ahead — `RUNBOOK.md` §"Capturing a live session".
