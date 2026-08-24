# Cast and attack animation mechanics: canceling, damage timing, quarterstepping, backswing

**2026-08-22.** The question, as the owner put it: how do cast animations,
animation canceling, damage actually being applied, movement during the attack
animation (the wiki's word is **quarterstepping**), and the backswing interact?

Method: a GWW pass through the browser (ten mechanics pages plus two skill
pages, per `browse-gw-wiki`), one new offline measurement over the two live
captures (`castgaps.py`, below — no client run, no new capture), and
reconciliation against what `studies/combat/PLAN.md` §17–§19,
`studies/skillcast/FINDINGS.md` and `studies/reconstruction/FINDINGS.md`
already measured. Labels per [studies/character/FINDINGS.md](../character/FINDINGS.md),
plus **WIKI** per the skill's labeling rule: strong for what a player could see
from the game window, weak for internals, and — because GWW shares no ancestry
with the code lineages — wiki + wire agreeing is real CORROBORATION.

**Identifiers.** `CASTMECH-M<n>` = a model claim this study makes.
`CASTMECH-P<n>` = a probe or capture item registered before it is run.
Convention: [studies/idents/CONVENTION.md](../idents/CONVENTION.md).

---

## The answer in one page

**One timing model covers auto-attacks, attack skills and spells, and the wiki
and the wire tell the same story from opposite sides.**

- **An attack is one interval with the hit just before the middle.** The wiki
  says an attack connects "half-way through the interval" and the rest is
  "return to a neutral state"; the wire, measured three independent ways, puts
  the connect point at **0.45–0.47** of the declared interval — NPC swings
  0.4540 (n=41), the player's clean auto-attacks 0.4583/0.4669 (n=2), and now
  the player's bow attack skill 0.4601/0.4595 (n=2, §2). The second half of the
  interval — the wiki's "return to neutral", the owner's **backswing** — has
  **no wire event of its own**: damage and `MELEE_ATTACK_FINISHED` are one
  instant, 40 of 40 (§17b), and nothing follows until the next
  `ATTACK_STARTED`. The backswing is client-side animation filling a
  server-side wait. (CASTMECH-M1, §2.)
- **The ¾ s aftercast is on ArenaNet's wire, per skill, as the E5→E3 gap.**
  NEW MEASUREMENT (§3): in all four Necromancer spell cycles E3 trails E5 by
  0.749–0.765 s — the client table's `+0x40 = 0.75` plus milliseconds of
  latency — and in both Ranger attack-skill cycles E5 and E3 share one
  timestamp, matching that skill's `+0x40 = 0.0`. So `0x00E3` is not "skill
  activated"; it is **the busy state ending** — aftercast over, character free.
  Our emitter's `e3_at = e5_at + aftercast` (`authsrv.py:7431`) is therefore
  OBSERVED retail behaviour, not an invention. (CASTMECH-M2.)
- **Cancel and interrupt are one client mechanism and two server timings.**
  Opcodes 226 (`0x00E2`) and 227 (`0x00E3`) share a dispatch pointer — the
  client cannot tell them apart (skillcast §5); both release the pending-cast
  entry. What distinguishes a cancel from an interrupt from a normal
  completion is **which other messages come with the release**: completion is
  E5-then-E3 an aftercast apart; the corpus's one terminated cast (§4) is an
  E4 answered by a lone E2 **with no E5 ever** — busy ended, no recharge
  started — which is exactly GWW's cancel contract: costs paid, **no
  recharge, no aftercast**. An interrupt should be a release **plus** a
  recharge-start (wiki: interrupted skills go on full recharge); no interrupt
  exists in the corpus to confirm the wire shape. (CASTMECH-M3, -P1.)
- **Quarterstepping is legal because the swing gate and the animation are
  different things.** The wiki technique — move in the window after the hit
  lands, re-order the attack in time, lose nothing — works precisely because
  the next swing's start is governed by a server-side interval from the last
  swing's start, while the backswing being canceled is client animation the
  server never hears about. Movement before the hit cancels an auto-attack
  (the swing dies, no damage); movement cannot cancel an attack skill at all.
  (§5, CASTMECH-M4.)
- **The skill queue the wiki documents is the queue law the wire fit.** GWW
  (2012): a queued skill "will begin activating as soon as activation
  completes for the first skill or after any aftercast delay ends". The
  emitter's QUEUE LAW (2026-08-14): E4 at accept, cast begins when the caster
  frees — fits 4/4 Necromancer cycles ≤14 ms. Same sentence, fourteen years
  apart, independent witnesses. CORROBORATED. (§6.)

---

## 1. Vocabulary: the wiki's words for the owner's words

| Owner's term | GWW's term and page | Note |
|---|---|---|
| cast animation | activation ("Activation time") | driven on our wire by agent property 60, §16a of combat/PLAN |
| animation canceling | cancel ("Cancel", "Auto attack") | movement key or Esc; weapon swap for the rest |
| damage actually applied | "the attack will connect" ("Activation time") | mid-interval; projectiles add flight time |
| quarterstepping | **"Quarterstepping"** — the page exists | rev. 2011-05-03; PvP glossary |
| backswing | "return to a neutral state" / "animation delay" | **GWW has no page or occurrence of "backswing"** — searched, zero hits. The concept is the second half of the attack interval ("Activation time") and the "Animation delay" section of "Aftercast delay" |

Pages read, with revision dates for the citations below: Aftercast delay
(2026-08-03), Activation time (2026-04-30), Attack speed (2026-07-03), Cancel
(2014-08-16), Auto attack (2020-08-12), Quarterstepping (2011-05-03),
Quarterknocking (2012-07-10), Skill queue (2012-07-25), Interrupt
(2025-10-25), Knock down (2026-08-05), Power Shot (2026-06-28), Troll Unguent
(2026-07-05).

---

## 2. The attack cycle: where the hit lands, and what the backswing is

**WIKI (GWW, "Attack speed" §Attack durations, rev. 2026-07-03).** Attack
speed is a property of the weapon or creature type, and the page publishes the
exact intervals "used by the game": axe/daggers/sword 1.33, scythe/spear 1.5,
**hammer/staff/wand 1.75**, bone fiend 1.86, pet/attack-spirit 2.0,
flatbow/shortbow 2.025, **longbow/recurve 2.475**, hornbow 2.7, melee minion
3.1. IAS/DAS scale the *duration* of each attack (so stated percentages
understate/overstate the rate change: +33% IAS ≈ +49% DPS), capped at +33%
and −50%.

Two of those table rows are already **CORROBORATED against our wire from the
other side**: the live player's declared attack speeds are 1.75 (Necromancer
session — wand/staff) and 2.475 (Ranger session — longbow/recurve), noted in
combat/PLAN §17b before anyone had looked at this table. And the client-side
IAS multipliers `studies/enemy/PLAN.md` §"+0xF0 modifier" measured — 0.75 for
+25%, 0.67 for +33% — are this page's numbers as duration factors.

**WIKI (GWW, "Activation time" §Attack skills, rev. 2026-04-30).** The damage
application rule, stated by players from twenty years of watching:

> "half-way through the interval, a melee attack will connect with its target
> and a ranged attack will launch its projectile; the remaining half will be
> used to return the character to a neutral state."

Attack skills **without** a stated activation take "the first half of the
character's next attack interval" to connect. Attack skills **with** a stated
activation connect at half the *stated* time (Savage Shot ½ s → fires at
¼ s) — and they "bypass the return-to-neutral delay from the previous attack",
which is the sanctioned form of backswing-canceling and the reason chained
attack skills compress damage. Attack-skill activation scales with IAS/DAS and
is untouched by cast-time effects (Fast Casting, Migraine).

**The wire's number for "half-way" is 0.45–0.47, five ways** (CASTMECH-M1):

| witness | value | n | where |
|---|---|---|---|
| NPC swings, windup ÷ declared speed | mean 0.4540, sd 0.0520 | 41 | combat/PLAN §17b |
| our server's published constant, fit earlier | `SWING_WINDUP_RATIO = 0.4458` | — | independent pass, §17b |
| player auto-attacks, cleaned of skill damage | 0.4583, 0.4669 | 2 | combat/PLAN §19 |
| player bow attack skill: E4→E5 ÷ 2.475 | **0.4601, 0.4595** | 2 | **NEW, §3 below** |
| WIKI, "half-way through the interval" | 0.5 | — | "Activation time" |

The wiki says half; every measured value sits just under half, tightly. Do
**not** silently resolve this to 0.5: the measured constant is the one the
corpus supports, the wiki's "half" is the idealized player statement of the
same quantity, and the two agreeing to within 10% from unrelated methods is
the corroboration. (The client itself holds no landing fraction at all —
combat/PLAN §17d: attack duration is `modifier × base`, one float handed to a
queueing call, and no windup constant exists in the image. The landing moment
is **server-authored**, which is why the corpus is the only exact witness.)

**What the backswing is, then.** The second half of the interval exists on the
wire only as silence: damage and `GV_MELEE_ATTACK_FINISHED` are the same
instant (40/40, §17b), and nothing else arrives until the next
`ATTACK_STARTED`. For ranged attacks the projectile launches at the connect
point and damage lands at projectile arrival — `0x00A4`'s f32 flight time
predicts the damage message to mean |err| 9.3 ms, 13/13
(`studies/isle/FINDINGS.md` B5). The backswing is the client animating the
wait; the server's only clock is the interval.

---

## 3. NEW: the aftercast is on the wire, per skill — the E5→E3 gap

**OBSERVED, 2026-08-22**, by `toolkit/authsrv/castgaps.py` over both live
captures, all game connections, `decode_all` strict (framed to the last byte;
the two cast-bearing connections carry 3,604 and 1,246 messages). Prediction
stated first, in the tool's docstring: if `0x00E3` marks aftercast end, the
Necromancer's spell cycles (skills 153 and 105, client table `+0x40 = 0.75`)
show E5→E3 ≈ 0.75 s and the Ranger's attack-skill cycles (394 Power Shot,
`+0x40 = 0.0`) show ≈ 0; if E3 is instead a fixed follow-on, all six show the
same gap; if E3 rides milliseconds behind E5 everywhere, the model in our
emitter is an invention.

| conn | skill | E4 | E5 | E3 | E6 | E4→E5 | **E5→E3** | E5→E6 |
|---|---|---|---|---|---|---|---|---|
| necro `:64103` | 153 (act 1.0) | 8.741 | 9.744 | 10.493 | 17.747 | 1.003 | **0.749** | 8.003 |
| necro | 105 (act 2.0) | 9.850 | 12.493 | 13.240 | 18.492 | 2.643 † | **0.748** | 6.000 |
| necro | 153 | 18.511 | 19.511 | 20.269 | 27.525 | 1.000 | **0.758** | 8.014 |
| necro | 105 | 19.690 | 22.261 | 23.026 | 28.270 | 2.571 † | **0.765** | 6.009 |
| ranger `:49163` | 394 (act 0.0) | 12.951 | 14.0895 | 14.0895 | 17.093 | 1.1387 | **0.000** | 3.003 |
| ranger | 394 | 21.543 | 22.6807 | 22.6807 | 25.684 | 1.1374 | **0.000** | 3.003 |

† the queue-law cycles: E4 accepted during the previous cast's aftercast, and
E5 lands activation + *remaining aftercast* after E4 (12.493 − 10.493 = 2.000;
22.261 − 20.269 = 1.992). The other numbers re-derive `authsrv.py:4374`'s
E6 = E5 + recharge (8/6/3 s, all six within 14 ms).

Three results (CASTMECH-M2):

1. **E5→E3 is the client table's own `+0x40`, per skill, 6/6** — 0.75 within
   +2% for the spells (a few ms of the same server latency every other gap
   carries), and exactly zero for the attack skill, where E5 and E3 share a
   timestamp (one segment). The per-skill discrimination is what kills the
   rival "fixed 0.75 constant" reading — Power Shot refutes it.
2. **`0x00E3`'s meaning is therefore "the caster is free"** — aftercast over —
   not "skill activated". The name `SKILL_ACTIVATED` (carried from the
   catalogs into `schema/overrides.json`) describes the client's *handler*
   (release the pending entry, skillcast §5); the *timing* is the busy state
   ending. Our emitter already schedules it this way from the content row's
   `aftercast` field; that choice is now OBSERVED rather than inherited.
3. **The Ranger's E4→E5 gap is the windup of §2.** Power Shot has **no stated
   activation** (WIKI, "Power Shot", id 394 — the infobox carries no
   activation key; energy 10, recharge 3), so by the wiki's rule it takes the
   first half of the bow's interval to connect. Measured: 1.1387 and 1.1374 s
   against a declared 2.475 — **0.4601 / 0.4595** of the interval, identical
   to the NPC windup band. The wiki's rule, the client table's 0.0, and the
   corpus's windup constant lock together on one number measured to 1.3 ms
   consistency across two presses eight seconds apart.

**Corrections to `studies/combat/PLAN.md` this measurement lands** (noted
there, dated today):

- **§0a's CONTESTED orphan is resolved, and it is not an orphan.** The two
  readers disagreed on which Ranger E4 lacks a tail (t=21.543 vs t=5.027).
  It is t=5.027 — 21.543 opens a complete cycle (row 6 above) — and it is
  not tailless: it is answered at t=5.912 by the corpus's single **`0x00E2`**,
  0.885 s after accept. 0b's pairing was right.
- **P4's `0x00E2` is one half of a two-message arc**: E4 accept → E2 release,
  with **no E5 between and no E5 ever after** — a cast attempt that ended
  without completing and without starting a recharge. See §4.

---

## 3b. The press burst, the stop shapes, and three properties — added 2026-08-22

Measured while implementing §7's wins, same method (offline decode of both
live captures, `decode_all` strict). OBSERVED throughout.

**The press burst is six messages in a fixed byte order, 2 of 2** (necro
t=18.5110 pressing 153, ranger t=21.5433 pressing 394 — both with a live
auto-attack chain):

```
0x00E4  [agent, skill, copy]            press accepted
0x009F  [8,  agent, 0]                  property 8 -> 0
0x009F  [3,  agent, 0]                  GV_ATTACK_STOPPED -- the chain closes
0x00A2  [62, agent, f32]                the energy debit
0x00A0  [60|50, agent, target, skill]   the cast animation -- 60 for the
                                        spell, 50 (CastAttackSkill) for
                                        Power Shot: the family split is real
0x009F  [8,  agent, 1]                  property 8 -> 1
```

**And the negative is measured too:** the necro's presses at t=8.741 (no
chain had ever started) and t=9.850 (press 1 had already paused it) carry
no STOPPED. A press stops the chain only when the chain is live.

**Property 3 corpus-wide: 7 occurrences, all `[3, agent, 0]`.** Two are the
press-burst instances above; one (ranger t=16.5783, the `[8→0, 3]` pair
standing alone) lands 57–90 ms after two c2s target-selects — §17c's cancel
candidate, now with its wire shape; the rest close NPC chains.

**Property 58 (`skill_finished`) is on the live wire — five times, every
one `[58, agent, 0]` at a cast-end instant** (all four necromancer E5s plus
one other-agent cast end). This REFUTES the "0 of 21,543" premise under
which our server deliberately leaves it unsent (`authsrv.py`, the cast-
animation comment; the count presumably came from a search of the wrong
channel or value). Wiring it is registered work, not a settled absence.

**Property 8 pairs — 17 `[8, agent, 0]` and 17 `[8, agent, 1]` — bracket
the press burst** (0 right after E4, 1 at the burst's end). GWCA's name for
8 is `disabled`; the client dispatches it through `int-agentview`
(skillcast §16.1). *(This paragraph closed "what it means is UNREAD and it
stays unsent" — both halves ended 2026-08-22: the handler and its follow-up
calls are read in skillcast §16.2, the full trigger census is §3c below,
and `authsrv.action_hold` now sends it in the measured contexts.)*

**Property 45 appears exactly once in the corpus** — `[45, agent, 0]`
immediately before the terminated cast's E2 (§3). It is not in the cast
trios (attack-skill = 50/46/49, skill = 60/58/59), no catalog names it, and
one attack-skill sample does not license sending it for spell cancels — it
stays unsent, recorded here.

**The queued cast's animation and debit fire at CAST-BEGIN, not at the
press.** At both of 153's E3 instants (10.4929, 20.2689) the wire carries
`[60, 31, 40, 105]` and the property-62 debit — skill 105's press burst,
deferred to the moment the caster freed. Our server sends both at the press
always; for a queued cast that is early by the previous cast's remaining
aftercast. Recorded divergence.

**The auto-attack resumes at the aftercast's end, on the wire:** `[4, 31,
40, 0]` (ATTACK_STARTED) rides the E3 instant on both of skill 105's cycles
(13.2404, 23.0259). The pause-for-cast-plus-aftercast and the restart at E3
are what `attack_tick` now reproduces.

---

## 3c. The instants, message by message — added 2026-08-22, second pass

Same method and same corpus as §3b (offline `decode_all` over both live
captures, every player-visible connection framed to the last byte; census
scripts scratchpad, castgaps.py's pattern). OBSERVED throughout. This pass
was run to answer the wiring questions §3b registered, and it answers all
of them.

**Property 58's position is the slot immediately after the cast end, 5 of
5.** All four necromancer spell E5s are followed — next message, same
instant — by `[58, 31, 0]`; the fifth `[58, 36, 0]` (another agent, second
connection, t=24.2587) sits in the same relative slot, immediately before
that cast's target-facing property-20 message. The full E5 batch, 4 of 4
on the necromancer:

```
0x00E5  [31, skill, 0, recharge]      E5 opens its own batch
0x009F  [58, 31, 0]                   skill_finished, next slot
0x00A0  [20, 40, 31, value]           the target-facing properties follow
(0x009F [42, 31, 100], 0x00A3 [55, ...] pairs, skill-dependent)
0x009F  [8, 31, 0]  then  [8, 31, 1]  the prop-8 pulse closes the batch
```

So "E5 before the damage", which `cast_tick`'s comment used to carry as
OURS and UNMEASURED, is retail's own order — and 58 goes between them.

**The attack-skill cast end is silent, 2 of 2.** Both Power Shot (394) E5
instants carry: E5, one `0x00A4`, then E3 in the same batch (aftercast
0.0) — **no 58, no 46** (the attack trio's own finished id), **no prop-8
pulse**. 58 is the non-attack family's cast-end property; nothing in the
corpus licenses a finished property for an attack skill's E5. Wired
family-scoped in `cast_tick` the day this was measured.

**The queued cast-begin burst is three messages, 2 of 2** (skill 105
beginning at 153's E3 instants, t=10.4929 and 20.2689):

```
0x00E3  [31, 153, 0]                  the previous cast's aftercast ends
0x00A2  [62, 31, f32]                 the queued cast's energy debit
0x00A0  [60, 31, 40, 105]             its cast animation
```

No E4 (that went at the press), no prop 8, no 0x00D2. Debit before
animation — the same relative order as the press burst.

**The corpus's one terminated cast never paid.** The ranger's E4 at
t=5.0269 is answered by the bare 0x00E2 at 5.912 with NOTHING between: no
debit, no animation, no prop 8 — an accepted press whose cast never began
and never cost anything. Together with the begin burst above this puts the
payment at CAST-BEGIN, not at accept.

**Property 8, all 30 player-agent events mapped, and it is a stateful
transition wire.** Every event rides a context where an action takes or
releases the agent, and a toggle to the value already held is never sent
(the ranger's t=12.9508 press burst carries only `[8,31,1]` — the flag was
still 0, so there was no →0 to send; every other accepted immediate press
carries the full 0-then-1 bracket):

- **→1 (an action takes hold):** the player's own ATTACK_STARTED instants
  (`[4, 31, x, 0]`, 4 of 4 across three connections, each with the unnamed
  one-dword `0x0028 [31]` in the same batch); the accepted immediate press
  burst's end (4 of 4); the E5 pulse's second half (4 of 4 — GWCA's
  "(aftercast)" note, the cast releasing and the aftercast taking hold in
  one batch).
- **→0 (the action releases):** the press burst right after E4, BEFORE the
  GV_ATTACK_STOPPED when one fires (2 of 2 with a stop, order [8→0] then
  [3, 31, 0]); the E5 pulse's first half; movement instants (heading +
  move-to-point in the same batch, 4×); the standalone chain stops — §17c's
  retarget cancel t=16.5783 and the capture-end stop t=23.8241 are both
  `[8→0][3,31,0]` adjacent pairs; the target's death (t=20.1637, n=1); and
  the attack skill's arrow landing its damage (t=14.4832, n=1 — the same
  batch also carries movement, so those two contexts are confounded).
- **Never on:** queued presses (2 of 2), queued cast-begins (2 of 2),
  attack-skill E5s (2 of 2), the terminated cast's E2 (1 of 1).

Other agents get the same wire: `[8, 725, 1]…[8, 725, 0]` and
`[8, 176, 1]…[8, 176, 0]` bracket ~100 ms NPC actions on the second
connections. What the CLIENT does with the property — a 1/0 flag on the
type-1 agent-view object, view-local, animation-facing — is
`studies/skillcast/FINDINGS.md` §16.2's read.

---

## 3d. The cancel opcode is `0x0028`, and the first operator run found it — 2026-08-23

The §7 wins' loopback acceptance ran (operator-driven, caged, run
`20260823T101329`, 4,455 records) and split clean: the windup, the
press-stop and the chain rules passed on screen — the auto-attack resume
even landed **at the same wire instant as the E3**, t=118.630, exactly the
retail template — while **checklist item 1 failed**: no input could cancel
a cast. The capture names the reason, and it closes CASTMECH-P2 on the way:

- **The client sends NO movement c2s while it holds a cast.** During the
  run's one 2.0 s cast (105 at t=58.787), the operator pressed all three
  cancel inputs — WASD, a ground click, Esc — and the window carries zero
  `0x003D`/`0x003E`. So `cancel_on_move`, wired to the movement arms, is
  **unreachable mid-cast by construction**, and the client does not
  predict a cancel either (the activation ran to completion on screen):
  it ASKS, and waits. That answers P2's "who owns cancel detection" — the
  server does, through a message we were dropping.
- **What the client sends instead is `0x0028`**, header-only, previously
  seen once corpus-wide and unnamed (combat/PLAN P1). This run has NINE,
  every one inside a held action: three during the cast at the operator's
  three cancel presses, the rest during swing windups. OBSERVED; the name
  **CANCEL_ACTION is INFERRED** from that context and goes to
  `schema/overrides.json` only after a re-run shows the grant working.
- **The double-press the operator reported** — a movement key cancels but
  does not move; the second press moves — is the same mechanism seen from
  the outside: press 1 becomes the `0x0028` request (no movement is sent
  with it), and with the request dropped on the floor, press 2's movement
  is the first message that does anything. Stock is one press
  (operator-verified against retail the same day), because retail grants
  the request.

**Wired the same day**: `GAME_CMSG_CANCEL_ACTION = 0x0028` and
`cancel_action()` — every pre-E5 pending entry marked (no attack-skill
exemption through this door: the wiki's "most quick attack skills cannot
be canceled" is the *client withholding the request*, so one that arrived
is granted), the hold released `[8→0]` only when something was actually
cancelled (an aftercast keeps holding), the live chain closed with the
`[8→0]`-then-STOPPED pair, the attack order forgotten, the tick answering
each mark with the bare E2. `test_castcancel` §6, floor 20.

**Still open after the re-run confirms or refutes:** whether granting the
`0x0028` also collapses the double-press (the client may move on its own
next input once released, or may need the movement re-pressed — stock
needs one press, so a surviving double-press means the client is waiting
on something we still do not send, with the live cancel's unnamed
property 45 the first suspect); and whether the cast **animation** stops
at the E2 alone or plays out (we still send no property 59 — zero corpus
occurrences — and no 45).

---

## 3e. The cancel-family live capture — predictions registered 2026-08-23, BEFORE the run

Run 2 of the loopback acceptance (`20260823T102742`) moved the failure into
the client: every cast cancel now fires server-side (two by the movement
door, two by the `0x0028` door — hold release + bare E2, `Gw.log` clean, no
pending-lookup failure), the movement grants go out in the same instant
(0x0025 + 0x0029, `grant_verdict fired`), **and the client plays the
activation to completion anyway** — while the swing cancels, whose burst
carries the attack family's stop (property 3), visibly stop on screen. The
symmetric candidate for casts is property 59 (`skill_stopped`, same trio as
the screen-proven 60/58, SOURCED dispatch into AvApi) — but it has zero wire
occurrences, the corpus's one cancel released property 45 instead, and
**re-reading that cancel's c2s side shows it is not a precedent at all**:
aligned clocks (offset 271.67 s) put the press mid-run — the skill QUEUED,
never began, the client was never held, and the "cancel" was a steering
change. **No cancel of a BEGUN action exists in any capture.** So the
release burst for a begun cast gets measured, not guessed: shopping-list
item 5 of `studies/combat/PLAN.md` §3, focused. Plan
`vault/plans/cancel_family.txt` (9 steps, sha256 `9e8a241c…`).

Predictions, stated first:

- **CASTMECH-P7** — W once, mid-cast, on retail: the client walks on that
  single press (operator-confirmed stock behaviour), and the server's
  same-batch answer carries the release burst for a begun cast. WHICH
  property rides beside the E2 is the question: 59 (structural), 45 (the
  queued precedent), 8→0, some combination, or none. No prediction is
  privileged; whatever appears gets wired verbatim.
  > **ANSWERED §3f: `[8→0, 59, E2]`, 4 of 4.** 59 — the structural
  > candidate. 45 does not appear at all. P8, P9 and P10 answered with it.
- **CASTMECH-P8** — Esc mid-cast: the client sends `0x0028` (as ours does),
  retail answers it, and the answer's shape tells us what our `0x0028`
  grant is missing. If retail's client instead sends nothing and
  self-cancels, the 0x0028 reading needs revisiting.
- **CASTMECH-P9** — W once mid-windup: one press walks; the answer's stop
  burst against ours ([8→0, 3] + grants). If retail's differs, the delta
  names why our client freezes for a press after a stopped swing.
- **CASTMECH-P10** — the completion control re-witnesses the E5 burst
  (58, the 8-pulse) on a second account/build for free.

---

## 3f. The cancel-family capture RAN: property 59 is the missing message — 2026-08-24

Live, operator-driven, secondary account, sealed plan
(`vault/plans/cancel_family.txt`, sha256 `9e8a241c…`, 9 steps, 10 marks, all
advanced). Capture `20260824T074002`: two game connections, **both frame to
the last byte** (41,552/41,552 and 29,340/29,340). Marks carry `wire_t`, so
every event below is on the capture clock with the tape rebased by `t0`.

**THE ANSWER, and it is one property.** Every cancelled cast is answered in
ONE batch, same order, **4 of 4** — W mid-cast, Esc, ground click, W again:

```
0x0029 [41, agent, pos, 0, 0]     the movement grant   <- only when MOVEMENT triggered it
0x009F [159,  8, agent, 0]        the action hold releases
0x009F [159, 59, agent, 0]        GV_SKILL_STOPPED
0x00E2 [226, agent, skill, 0]     the pending entry releases
```

t = 81.660 (W), 88.946 (Esc — the three alone, no grant), 98.779 (click,
grant + `0x002B` rate), 128.805 (W again). **Property 59 occurs at exactly
those four instants in the whole capture and nowhere else**, so it is the
cast family's stop rather than a general marker — and property 45, the
queued-drop shape §3e flagged as the rival candidate, appears **zero** times.
CASTMECH-P7 and P8 are ANSWERED and agree with each other.

**Why our client played the animation out.** 59 is the one that reaches
AgentView (`InterruptSkill`, `0x007E01B0`, `studies/skillcast` §6) — the
layer that owns the body. We sent the hold release and the E2 and no 59:
**the E2 settles the skill BAR, 59 stops the BODY.** The operator's
2026-08-23 report — "the animation does stop visually when cancelled" for
swings but not casts — is exactly that split, because the swing path already
had its own stop (property 3).

**The swing pair, and it is the OPPOSITE order** (CASTMECH-P9): W mid-windup
t=114.641 and Esc mid-windup t=119.425, 2 of 2 —

```
0x009F [159, 3, agent, 0]         GV_ATTACK_STOPPED
0x009F [159, 8, agent, 0]         then the hold releases
```

— where the press and retarget bursts carry `[8→0, then 3]` (§3c; the
t=16.578 retarget). Both orders are measured at their own door and **neither
is tidied to match the other**.

**CASTMECH-P10, free:** the completion control re-witnesses §3c's E5 burst on
a different account and build — E4/60/`8→1` … E5/58/`8→0`/`8→1` … E3/`8→0` …
E6. One correction falls out of it: §3c said "the corpus's E3 instants never
toggle property 8", and here **E3 carries `8→0`** (t=69.670). The older
corpus's E3s did not; this one does. Recorded, not resolved — the hold's
full state machine is still only partly read.

### 3f-i. A claim of mine, REFUTED — §3d's central inference

§3d said *"the client sends NO movement c2s while it holds a cast"*, and
built the `0x0028` door on it. **Retail's client sends movement mid-cast**:
`0x003D` at t=81.625 and t=128.774 (W), `0x003E` at t=98.743 (click).
`0x0028` appears **twice**, and both are the **Esc** steps (t=88.916,
119.380). So `0x0028` is Esc's message — the CANCEL_ACTION name survives —
but it is *not* the only door, and the client was never mute.

The inference was drawn from one loopback window where the operator's inputs
happened to be Esc presses; re-reading run `20260823T102742` shows its first
cancel **was** a `0x003D` (t=7.233), which our own movement door answered.
The window was too small and I generalised from it. What the run really
showed was the missing 59, which no amount of c2s reading would have found.

**The double-press follows from the same gap** (the operator's stock
comparison: one press cancels *and* moves). Our server granted the movement
in the same instant — `0x0025`+`0x0029`, `grant_verdict fired` — but with no
59 the client's action state never cleared, so it neither walked nor stopped
animating until a second input. The re-run is the check.

**Wired the same day**: `release_cancelled_cast()` sends `[8→0, 59, E2]`
inline on the connection thread — retail answers the input in its own
instant, and the tick keeps ownership of removal (`released`), so F10's
single-writer rule is untouched. Both doors call it; the swing pair is
reordered to `[3, 8→0]` at the two doors that measured it. `test_castcancel`
20 checks, floor 20.

**Still open:** we place the movement grant *before* our cancel burst on the
click arm and *after* it on the keyboard arm; retail puts the grant first in
both. Cosmetic against a client that acts on the properties, but unmeasured
and therefore recorded.

---

## 3g. The cancel is DONE; the walk-on-cancel is a ZERO-LEAD interaction — 2026-08-24

Loopback acceptance of §3f, map 280 (Isle of the Nameless — the first map
this arc pinned that has a real spawn; map 90's is `0.0, 0.0` under its own
"No spawn point known" note, which is why the run before it could not move
at all). Capture `20260824T081335`.

**The cancel half PASSES, on screen and on the wire.** Three cancelled casts
— one by W, two by Esc — each answered `[8→0, 59, E2]` in the input's own
instant, and the operator reports the casting animation now **stops**. That
is §3f's measured burst reproducing at a client, and it closes what the
2026-08-23 run failed: the missing property was 59.

**What remains is one press producing no motion, and it is NOT the cancel
path.** Isolated in this capture: the mid-cast W (t=5.417) cancels and the
client's own next report (t=6.234) is the SAME coordinate; the next W
(t=7.502), with nothing held, moves it (t=7.735, 7.953). Same grant shape
both times — `0x0025` direction + `0x0029` **zero-lead** — so the grant is
not what differs. What differs is whether an action was held.

**The mechanism, INFERRED and cross-arc.** Under keyboard movement the CLIENT
walks itself and our grant only keeps the sync copy honest; mid-cast the
client is held, does not self-walk, and its key-down edge is spent on the
cancel. Retail moves the player anyway because its grant carries a real
destination — `0x0029` at **+768 u along the heading** (t=81.660: reported
`(-5996.0, 1547.1)`, granted `(-5982.9, 2315.2)`), which is a server-
authoritative move order. Ours grants the player's own position, so there is
nothing to walk to.

**AND THE OBVIOUS FIX IS THE DEAD FAMILY — do not "just add a lead."**
`authsrv.py`'s zero-lead block (REALFIX-P2) records that **every** candidate
granting a point AHEAD warped: `--heading-grant` at pos+vec2 clipped (766 u)
and `--client-endpoint` at reported+vec2+0.5 u (766 u), both refuted by runs.
Zero lead is the only setting satisfying the client's own desync invariant
(O1/O3), because the client's history polyline extends only backwards while
it holds no destination. Retail can lead because its server owns the true
position; we cannot.

So walk-on-cancel is a **movement-policy** question, not a cancel one, and it
belongs to that arc with this capture as its evidence. Registered rather than
patched here. The one no-warp experiment available is ORDER — retail puts the
grant BEFORE `[8→0, 59, E2]` and we put it after (§3f's open item) — but the
analysis above predicts order alone will not supply the missing destination,
so it is worth one run and not worth a blind ship.

---

## 4. Canceling: three doors in, one wire shape out

**WIKI (GWW, "Cancel", rev. 2014-08-16).** During activation, a skill is
canceled by **a movement key** or by **Cancel Action** (default Esc, "usually
faster and more reliable"). The contract:

> the skill does not activate; **initial costs are still incurred** (energy,
> adrenaline, overcast — health sacrifice normally is not); **the skill does
> not need to recharge; the aftercast delay will not activate.**

Most *quick attack skills* resist Esc — but **swapping weapons from within the
inventory cancels them** mid-use ("most commonly seen in higher level GvG
ranger duels"). And WIKI (GWW, "Auto attack", rev. 2020-08-12): auto-attacking
is canceled by moving or by Cancel Action; a single deliberate basic attack is
"begin auto attacking, wait for the attack to end, and move or press this
key".

**WIKI (GWW, "Quarterstepping", rev. 2011-05-03)** adds the asymmetry that
matters for a server: keyboard movement mid-swing "increases the risk of
accidentally cancelling an attack before it lands", and the technique "works
in exactly the same manner with attack skills as autoattacks, **except that
attack skills can not be accidentally cancelled by moving prematurely**". So:

| action under way | movement | Esc | weapon swap |
|---|---|---|---|
| spell / other activated skill | cancels | cancels | (unrecorded) |
| auto-attack swing, before the hit | cancels the swing | cancels | — |
| attack skill, before the hit | **does not cancel** | mostly refused | cancels |
| aftercast | impossible — cannot move (§6) | — | — |

**Cancel vs interrupt vs knockdown — three different endings, WIKI:**

| | recharge? | aftercast? | anti-interrupt protects? | queued skill |
|---|---|---|---|---|
| cancel ("Cancel") | **no** | no | n/a | (kept — nothing says otherwise) |
| interrupt ("Interrupt", rev. 2025-10-25) | **yes, full** | no | yes (Mantra of Resolve etc.) | **un-queued** |
| knockdown / death / disable ("Interrupt", "Knock down") | stops the action, "technically different game mechanics" | — | **no** — KD interrupts through Mantra of Concentration | — |

Interrupts can hit "any skill with an activation time and all attacks" — but
not aftercast, running, emotes, or zero-activation skills. Attack skills'
effects trigger half-way in (§2), so their interrupt window is only the first
half. Dazed makes every successful attack an interrupt of spells.

**The wire shape (CASTMECH-M3).** The client physically cannot distinguish
cancel from interrupt: 226 and 227 share one dispatch pointer whose whole job
is releasing the pending-cast entry (skillcast §5). The distinctions above are
carried by **what else the server sends**:

- **completion**: E5 (recharge starts) … E3 (busy ends) an aftercast later;
- **cancel**: the release alone — §3's E4→E2 pair, with no E5 ever, matches
  GWW's "does not need to recharge / no aftercast" exactly. n=1, and the
  *cause* of that termination is UNVERIFIED (P4 called it burrow-correlated;
  a self-cancel fits the shape equally well);
- **interrupt** (predicted, UNVERIFIED): the release **plus** a recharge
  start — E2 followed by an E5-shaped message carrying the full recharge, or
  by `0x00E7`/`0x00E8` (both zero occurrences in the corpus). No interrupt has
  ever been captured; CASTMECH-P1 below.

The animation half of a cancel is the property channel, same as the cast
itself: property 60 starts the cast animation (combat/PLAN §16a, operator-
confirmed both ways), property 59 is `InterruptSkill` with its own AgentView
path (skillcast §6), and the client's internal event trios end in
started/finished/**stopped** for all three families (skillcast §16.3). Our
server sends none of the stop/interrupt properties today.

---

## 5. Quarterstepping and the backswing: why free movement is free

**WIKI (GWW, "Quarterstepping", rev. 2011-05-03).** The technique: "Attack the
target and, just before the hit lands, click to move in the direction of
desired repositioning, then click the attack key … just in time to initiate
the attack again without losing a beat." It "exploits the game mechanic which
allows a small amount of movement after each attack". Because it ends the
attack, the freed window can also be spent on weapon swaps or pre-positioning
toward the next target. Best practiced on the Isle of the Nameless dummies;
prime use is body-blocking and skills that want a moving target (Bull's
Strike, Protector's Strike).

**The model that makes all of it consistent (CASTMECH-M4, INFERRED):**

1. the server gates **swing starts** on the attack interval measured from the
   previous swing's start;
2. the hit lands at ~0.46 into the swing (§2), after which the swing's work
   is done;
3. the backswing is client animation, cancelable by anything (movement, the
   next queued action) with **no wire consequence**;
4. moving before the hit kills the in-flight swing (its damage never
   happens); moving after the hit costs nothing **provided the re-ordered
   attack is pressed before the gate opens**, so the next swing starts on
   schedule.

Two rival readings and why they lose: *(a) a persistent cooldown with a grace
period* would make the re-press timing irrelevant, against the wiki's
insistence on "just in time"; *(b) no gate at all* — a fresh swing started the
moment the previous hit lands would land its hit at ~0.92 of the natural
interval, i.e. quarterstep-spamming would be a universal ~8% IAS, which two
decades of PvP would not have missed. The sanctioned compression exception is
explicit and different: attack skills **with stated activation** bypass the
previous attack's backswing (§2) — WIKI, "Activation time" §Notes:
Executioner's after Eviscerate lands 1.33 s later, Agonizing Chop lands ½ s
later "which is almost three times as fast", and ranger interrupts were given
aftercast precisely "to hinder damage compression".

**What our server does today, against this** (divergences, mostly already on
record in combat/PLAN §17e): the player's swing has no windup at all
(STARTED + damage + FINISHED in one call); nothing can cancel an in-flight
swing or cast; `GV_ATTACK_STOPPED` is defined and never sent; and movement
during a swing/cast/aftercast is not policed at all — our client-driven
movement messages are applied whenever they arrive. A quarterstep against our
server currently *works trivially* (nothing to cancel, no gate to miss),
which is fidelity by coincidence, not by model.

---

## 6. The queue, the aftercast, and knockdown

**WIKI (GWW, "Aftercast delay", rev. 2026-08-03).** Aftercast is "the period
after successfully activating certain skills, during which players **cannot
move or activate other skills**" — and cannot auto-attack. Almost always ¾ s.
Who has it: all spells, signets (except Dolyak), chants, echoes, glyphs,
rituals, forms (except the elite Norn three), five listed zero-activation
skills — and **not**: zero-activation skills generally (stances, shouts,
flash enchantments), attack skills with stated activation ("noticeably
interrupts and some dagger skills" — though ranged ones DO carry it, §2),
Prophecies/Core preparations (Factions/Nightfall preparations DO), most
non-foe-targeted shadow steps. Named exceptions in both directions on the
page. Fast Casting does not touch it; "there are no other known mechanisms to
reduce or cancel aftercast delay" beyond situational triggers like a form
change. Attack skills without activation have instead an **animation delay**
(bow/dagger/hammer ¾ s, other weapons ½ s) already folded into the attack
interval. Trivia: before 2008-03-06, PBAoE spells carried 1.75 s.

The per-skill reality of "almost always ¾, sometimes 0" is exactly what the
client table's `+0x40` float encodes (0.75/0.75/0.0 for 153/105/394 —
`studies/skills` §the-struct, `studies/reconstruction` row 10), and §3 put it
on the wire. A skill-by-skill sweep of `+0x40` against this page's exception
lists is a free third-witness check the next time `skilltable.py` output is
regenerated (CASTMECH-P4).

**WIKI (GWW, "Skill queue", rev. 2012-07-25).** One slot; a second attempt
replaces the first; "queued skills will begin activating as soon as
activation completes for the first skill **or after any aftercast delay
ends**"; out-of-range use queues the skill and walks you into range; shouts
fail instead of queueing. This is the QUEUE LAW verbatim (combat/PLAN step 3:
E4 at accept, cast begins when the caster frees, 4/4 cycles ≤14 ms) — the
2012 sentence and the 2026 fit are independent, and the two queue-law cycles
in §3's table († rows) are the wire's own copy. An interrupt un-queues the
queued skill ("Interrupt"); a plain cancel is not said to.

**WIKI (GWW, "Knock down", rev. 2026-08-05; "Quarterknocking", rev.
2012-07-10).** A knocked-down character (2 s; 3 with Stonefist; up to 4)
cannot move, cannot switch weapons, and cannot activate anything with an
activation time **or an aftercast delay** — which is why aftercast-bearing
skills "must be queued" (Aftercast page) and why a skill pressed during the
KD activates at a predictable instant after getting up. Quarterknocking is
timing the *next* knockdown or interrupt onto that instant — the queue law
weaponized. A target can be re-knocked "the instant they begin to rise".
Anomaly recorded on the page: a foe knocked down mid-cast "often keep[s]
casting for 1-2 seconds more … then it spontaneously fails", and a mid-flight
projectile from a knocked-down creature stalls until the KD ends.

---

## 7. What is settled, what is ours, what is next

**Settled by this pass** (wiki + wire + client table in agreement):

- the connect point at ~0.46 of the interval, all attacker classes (M1);
- E3 = aftercast end, per skill from `+0x40`; the four-opcode cycle now has
  every gap named: E4→E5 activation (via queue law), E5→E3 aftercast,
  E5→E6 recharge (M2);
- the queue law is retail's documented skill queue (§6);
- cancel-no-recharge as a wire shape (E4→E2, no E5), n=1 (M3);
- quarterstepping's existence and rules; backswing = interval second half,
  client-side only (M4).

**Still OURS / UNVERIFIED**, in rough order of value:

| id | question | how to settle |
|---|---|---|
| CASTMECH-P1 | the interrupt wire shape: does E2 come with a recharge-start (E5? E7/E8?) when a cast is genuinely interrupted, vs alone for a cancel? | live capture, shopping-list item 5 of combat/PLAN §3 (engineered interrupts, n≥2 causes) — or loopback: send E2 mid-sweep and watch whether the client's bar treats the skill as recharging |
| CASTMECH-P2 | does the client *predict* a movement-cancel (stop the cast bar on a move press) or wait for the server's E2? | loopback: begin a cast, script a move press, send no E2 — does the bar keep filling? Settles who owns cancel detection |
| CASTMECH-P3 | the swing gate model (M4's three-way): does a re-press after a quarterstep land the next hit on the original schedule? | capture: operator quarterstepping the Isle dummies at fixed cadence vs mashing — hit-to-hit deltas discriminate gate-from-start (1.33 I) from no-gate (0.92 I) |
| CASTMECH-P4 | `+0x40` sweep vs the Aftercast page's exception lists (Dolyak 0? Ranger interrupts 0.75? Factions preparations 0.75?) | offline, next `skilltable.py` regeneration; pure client-table read with WIKI as the cross-witness |
| CASTMECH-P5 | movement lockout during aftercast on OUR wire: retail refuses movement for 0.75 s post-cast; our server applies move messages whenever they arrive | decide and label: either police `cast_busy_until` in the move handler or record the divergence beside §17e's |
| CASTMECH-P6 | the player's windup at scale (n=2 clean auto-attack samples) | the §19 NEEDS-CAPTURE stands: 20+ swings, in range, no skills |

**For the server, the cheap wins in order:** (1) arm the player's swing with
the same windup the agents already have (§17e item 1 — M1 now gives the
constant three independent legs); (2) a cancel path — accept a move/cancel
c2s during an in-flight cast or swing, drop the scheduled hit, emit E2 and
`GV_ATTACK_STOPPED`/property 59, charge no recharge (M3's shape); (3) the
backswing needs **nothing** — it is client animation, and modeling it
server-side would be modeling a fiction.

> **WINS 1 AND 2 LANDED 2026-08-22** (`002f20f`, `2c8d3ba`, `3dcf9d5`), and
> the §3b measurements sharpened win 2 on the way: the STOPPED rides the
> press burst immediately after E4 (2/2, with the measured negative — no
> close when no chain is live), a retarget stops the swing in flight (the
> 16.578 shape), movement cancels the cast with the bare E2 and the wiki's
> attack-skill asymmetry per entry, the chain pauses while a cast is short
> of its E3 and resumes on the first tick after it (retail's own instant),
> and property 59 is deliberately NOT sent — zero corpus occurrences stands,
> and the properties the corpus does show at these instants (8, 45, 58) are
> §3b's registered follow-up, not silent additions. Win 3 was honoured by
> writing no code. Tests: `test_playerswing.py` (floor 23),
> `test_castcancel.py` (floor 15).
>
> **THE §3b REGISTER CLOSED 2026-08-22, same day, second pass (§3c).** 58 is
> sent at the cast end (non-attack, the measured slot); the attack-skill
> press animates with 50; the queued cast pays and animates at CAST-BEGIN;
> and property 8 is wired as the view's action-hold flag, transition-only,
> in its measured contexts, after the client handler read (skillcast §16.2).
> **Property 45 alone stays unsent** — one corpus occurrence, no catalog
> name, no handler read; still registered, not silent. Tests:
> `test_castcycle.py` (floor 20), `test_playerswing.py` (floor 24),
> `test_castcancel.py` (floor 15), `test_pools.py` 9/11e.

---

## 8. Reproducing this

```bash
python toolkit/authsrv/castgaps.py
```

reads both live captures through `vaultpath`/`tape.resolve_capture` (worktree-
safe), decodes every game connection whole, refuses partial frames, prints
§3's event list and gap table, and states its prediction in the docstring
before the numbers. Wiki pages were read through the browser per
`browse-gw-wiki` (the in-app browser passes GWW's WAF; scripted HTTP does
not), with revision timestamps pulled once via the on-page MediaWiki API.
