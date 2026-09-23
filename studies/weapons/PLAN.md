# Every weapon type, represented accurately — the plan

**Arc opened 2026-09-18.** A PLAN, not a build: no server code changed, no client was
launched. Read: GWW (`Weapon`, `Attack speed`, `Damage calculation`, `Critical hit`,
`Requirement`, `Range`, `Projectile`, `Line of sight`, `Bow`, `Scythe`, `Spear`, `Staff`,
`Wand`, `Shield`, `Focus item`, `Double strike`, `Customize`, fetched 2026-09-18 through
the in-app browser as `action=raw`), this server's weapon code, and the vault's live
corpus through three scratch censuses (§3 — landing them as a tool is WEAPONS-W0).
Labels are the repo vocabulary ([studies/character](../character/FINDINGS.md)) plus WIKI
per `.claude/skills/browse-gw-wiki`.

**Identifiers.** `WEAPONS-C<n>` = a census finding (OBSERVED on tapes, desk).
`WEAPONS-W<n>` = a work package. `WEAPONS-Q<n>` = an open question, with the instrument
that answers it. `RUN-WEAPONS-<n>` = an owner-driven live capture. Convention:
[studies/idents/CONVENTION.md](../idents/CONVENTION.md).

---

## 0. The plan in one paragraph

The server knows four weapon types (hammer, sword, axe, daggers) and they are all melee;
a caster hero "swings" a staff at 1,248 units with no projectile, nothing has a range, a
weapon's damage type has no reader, and a focus gives no energy (a focus gives its `556`
since §15; the rest of that sentence still stands where §4's rows say so). The dagger arc showed
what closing one type costs and what it buys, and it left two instruments
(`timingjoin.py`, the recorder) and two laws with no free parameter (the hit is half the
duration less 0.1 s; the next swing opens one recovery later). This plan's bet is that
**most of the per-type table is already on the owner's tapes and nobody has read it**:
§3 found that every held weapon's item row on the wire carries its attribute and
requirement, its damage type, its projectile and (for bows) a five-valued class word;
that the projectile launch is the windup law again; and that scythes and spears are in
NPC hands in the corpus without ever having been censused. So the order is **desk first
(W0), one table (W1), then the biggest absent mechanism (W2, ranged delivery), then the
per-type rules (W3–W6)**, with three short captures only for what the corpus cannot hold:
a scythe, a spear, three of the five bows, and range.

## 1. What "accurately represented" means — the contract per type

A weapon type is done when each of these is either matched to retail or written down as
not applicable, **with its evidence label**:

| # | Column | What it covers |
|---|---|---|
| 1 | identity | item type id, hands (one / two / off-hand), linked attribute, the `weapon_req` bit attack skills name it by |
| 2 | clock | swing duration, the windup (hit or launch instant), recovery, IAS / DAS, the after-skill restart |
| 3 | delivery | melee reach, or a projectile: launch message, flight time, arrival message, range, height, stray / obstructed / dodged |
| 4 | damage | range by requirement, scaling (mastery with the level threshold; caster weapons by level), critical chance and the critical's size, damage TYPE against armour |
| 5 | own rule | daggers' double strike (done), scythe's three targets and small critical, hornbow's 10 % penetration, staff energy and recharge, caster weapons' low critical rate |
| 6 | requirement | met / unmet, for weapons, shields and foci |
| 7 | off-hand | shield armour, focus energy |
| 8 | presentation | the item row the client is sent, the model in the hand, the attack animation the client picks |
| 9 | holders | player, hero, henchman, hostile — all four read the same table |

## 2. What the wiki says (WIKI — a prior, never a pin)

| Type | Hands | Max damage | Duration | Damage type | Range | Flight | Own rule |
|---|---|---|---|---|---|---|---|
| Axe | 1 | 6–28 | 1.33 | slashing (some piercing) | melee 144 | — | — |
| Sword | 1 | 15–22 | 1.33 | slashing | melee | — | — |
| Daggers | 2 | 7–17 | 1.33 | piercing / slashing | melee | — | double strike 2 % + 2 %/rank |
| Hammer | 2 | 19–35 | 1.75 | blunt | melee | — | — |
| Scythe | 2 | 9–41 | 1.5 | slashing | melee | — | +2 foes in melee range of the target and within 180 of the player; critical ×2^0.125 not ×2^0.5 |
| Spear | 1 | 14–27 | 1.5 | piercing | 1004 | 0.60 | height affects range and damage |
| Shortbow | 2 | 15–28 | 2.025 | piercing | 1004 | 0.59 | — |
| Flatbow | 2 | 15–28 | 2.025 | piercing | 1498 | 0.88 | high arc |
| Longbow | 2 | 15–28 | 2.475 | piercing | 1498 | 0.59 | — |
| Recurve | 2 | 15–28 | 2.475 | piercing | 1273 | 0.40 | — |
| Hornbow | 2 | 15–28 | 2.7 | piercing | 1273 | 0.59 | 10 % armour penetration |
| Staff | 2 | 11–22 | 1.75 | by attribute | 1248 (spell range, no height) | 0.56 | energy +10, 20 % recharge; damage by LEVEL; very low critical |
| Wand | 1 | 11–22 | 1.75 | by attribute | 1248 | 0.56 | damage by level; very low critical |
| Shield | off | armour 16 | — | — | — | — | unmet: 8 (or 5) |
| Focus | off | energy 12 | — | — | — | — | unmet: 6 (or 3) |

Flight times are "at shortbow range". **GWW contradicts itself on bows**: the `Weapon`
page prints 2.0 / 2.4 s and ranges 1.35 / 1.20; `Attack speed` ("the exact values used by
the game") and `Bow` print 2.025 / 2.475 and 1.48 / 1.2. The corpus already sides with
the second: a player bow and an NPC bow both cycle at **2.476 s** (WEAPONS-C1). Also
WIKI, and each a claim to test rather than a rule to ship: an unmet requirement deals
one third of base damage ([studies/isle](../isle/FINDINGS.md) measured against that and
refused to pin a term); customisation ×1.2; a critical deals the maximum at armour −20;
a player-theorised critical-chance formula; hit locations 3/8 chest, 2/8 legs, 1/8 each
other; height raises bow and spear damage up to 2×.

## 3. What the corpus already holds (OBSERVED, scratch censuses 2026-09-18)

Every live connection, decoded with `livewire.decode_conn`; an "attacker" is an agent with
≥ 3 clean start-to-start gaps (`0x00A0 [4, agent, target, 0]`, no skill between).
75 attackers on 19 tapes.

**WEAPONS-C1 — the launch IS the windup.** `0x00A4` AGENT_PROJECTILE_LAUNCHED follows
its swing's start by **0.771–0.778 s on every 1.75 s weapon** (20+ attackers, 250+
launches; `swing_windup(1.75)` = 0.775) and by **1.137–1.138 s on the 2.476 s bows**
(3 attackers; `swing_windup(2.475)` = 1.1375). The hit is launch + the message's own f32
flight time ([studies/isle](../isle/FINDINGS.md) B5, 13 of 13 within 21 ms; 68 of 68
launches closed by `0x00A7` on `20260913T210901`). So ANIMREF-R1's law needs no ranged
variant: **the windup releases the projectile instead of landing the hit.**
**Pre-registered, no free parameter:** a 1.5 s spear launches at 0.650 s, a 2.025 s bow
at 0.9125 s, a 2.7 s hornbow at 1.250 s; a scythe's word lands at 0.650 s.

**WEAPONS-C2 — item types in hands.** `0x006D [agent, leadhand, offhand]` joined to the
same tape's `0x0161`, 3,467 bodies (1,355 empty-handed): leadhand **26** staff ×611, **1** ×465, **27** sword
×430, **28** ×274, **5** bow ×119, **22** wand ×64, **2** axe ×55, **15** hammer ×50,
**32** daggers ×17, **36** ×16, **35** ×10; off-hand **24** shield ×396, **12** ×67. The
NUMBERS are OBSERVED; the names of 35 (scythe), 36 (spear) and 12 (focus) are UPSTREAM
(GWCA's `ItemType`) until §3's words confirm them — and they half do: 36 carries a
requirement in attribute 37 and piercing damage, 12 carries energy (`556`) and a caster-attribute
requirement, no damage. **Types 1 and 28 are nobody's player weapon**: 1 is a zero-damage slashing prop
(`584` 0–0 on 459 of 465), 28 is the hostile's ranged weapon (a `609` and a `617` word,
no requirement, both arrows and bolts leave it). The server's NPC table must hold them;
the player table must not.

**WEAPONS-C3 — the item row already carries most of the contract.** Modifier identifiers
per held type (identifier = bits 20–29 of the word; `584` range and `587` damage type
were decoded by [studies/itemmods](../itemmods/FINDINGS.md)):

| Word | On | Reads as (RECONSTRUCTION until W0 checks each per attacker) |
|---|---|---|
| `633 (attr, rank)` | every martial weapon, wand, staff, shield, focus | the **requirement**: 18 axe, 19 hammer, 20 sword, 25 bow, 29 daggers, 37 spear; 17 / 21 on shields — this server decodes no 633 and no repo item row carries one |
| `634 (a, b)` | beside every 633 | UNREAD — a second range? (WEAPONS-Q9) |
| `587 (type)` | every weapon | damage type: 0 hammers, 1 bows / daggers / spears (and 4 of 55 axes — GWW's "some axes pierce"), 2 swords / axes / scythes, 3–11 on wands and staves. No reader in the server |
| `617 (0, n)` | bows, wands, staves, some type 28 | the **projectile**, and this one W0's check already ran per shooter: `0x00A4` field 5 equals the shooter's own `617` argument on every weapon shot for **33 of 34** shooters whose weapon carries the word (143 / 144 on bows, 0–6 on wands and staves; the one miss is a type 28 holding 6 and shooting 0), and the 24 shooters whose weapon has NO `617` all shoot 143 but one. Isle B5 had field 5 as "a per-shot handle, REFUTED as a skill id"; it is the weapon's projectile, and the skill-sized values (343, 403, 854 …) are spells' |
| `609 (n)` | bows (0–4, five values) and type 28 (0 / 1) | five bow classes exist; five values sit on bows. Which is which needs a named bow in the owner's hand (RUN-WEAPONS-1B) |
| `556`, `570` | staves, foci | energy (+9 / +10 on 483 staves; +5 / +10 on foci); `570 (16..17, 1)` on staves beside GWW's "halves recharge 10–20 %". The server reads 556 off armour only |

`0x00A4` field 7 is 1 on 117 of 119 arrows (field 5 = 143) and 0 on 353 of 353 wand and staff
bolts; `schema/overrides.json` records the client dropping it. We send what retail sends.

**WEAPONS-C4 — what the corpus does NOT hold.** No scythe or spear attacker with three
clean gaps (the types are held, never swung in front of the recorder); no 2.025 s or
2.7 s attacker, so three of five bow classes are unmeasured; no range measurement for
anything; the OBSERVER's own weapon never appears in `0x006D` (the 19 biggest attackers,
1,029 gaps, are players with no weapon row — WEAPONS-Q8).

**WEAPONS-C5 — a hostile's repeat is not a weapon's duration.** Ranged hostiles with a
0.775 s launch cycle at 1.75, **1.90, 1.985 and 2.125 s** in one fight (agent 80 on
`20260914T180058`: 24 / 44 / 10 / 10 of 91), independent of flight time (0.06–0.49 s);
the player's wand on `20260913T210901` is a clean 1.750. Melee hostiles show 1.48, 1.56,
1.90 and 2.15. That is an AI pacing question and belongs to
[studies/monsterai](../monsterai/FINDINGS.md) (WEAPONS-Q7); the guard it gives this arc
is: **never calibrate a weapon's clock on a hostile.**

## 4. The server today, against the contract

| Column | Today (site in `toolkit/authsrv/authsrv.py` unless named) | Gap |
|---|---|---|
| identity | three dicts keyed on item type, four rows each (`WEAPON_TYPE_ATTRIBUTE` / `_RATE` / `_REQ_BIT`, :11052); `PARTY_WEAPON_BY_PROFESSION` (:10366) names shortbow, spear, scythe with nothing behind them; item rows for hammer, sword, shield, staff, daggers only | nine types have no row; three tables must be one |
| clock | right for whatever key it is given (SLICE-F49..F51, DAGGERS-F20); `[attack_speed.rates]` has all 13 keys, `source = "wiki"` | the bow, spear and scythe rows are unmeasured; the player can only hold four of the keys |
| delivery | melee reach 144 (`ATTACK_REACH`); party casters swing from `PARTY_RANGED_REACH` 1248 with **no projectile**; `0x00A4` / `0x00A7` named in the schema and never sent | the whole ranged half of the game |
| damage | `swing_damage` — item's `584` range, mastery rank with threshold, measured five-point critical table, critical = max at armour −20; **since §16 a wand or staff scales on the character's level (strike level 3 × level, the wiki's no-skill critical)** | 633 never read, no unmet term (by decision, isle), ×1.2 not shipped (by decision), `587` unread |
| own rule | daggers complete | scythe targets and critical, hornbow penetration, staff recharge |
| off-hand | shield `572` armour added at every location; `holds_shield` gates block skills | focus and staff `556` energy unread; unmet shield / focus values |
| presentation | `0x0161` + `0x006D` / `0x006E` / `0x0147` sent for the five rows | an item row per type, from the owner's own tapes (numbers and ids; names by id) |
| holders | hostiles read `attack_speed` / `damage` / `weapon_item` content rows; heroes `HERO_WEAPON` | no row has a range; types 1 and 28 unknown to content |

## 5. Work packages, in order

Each package ends the way the dagger arc's did: a desk check on tapes, the build behind a
control flag, a test with a floor from a green run and its `TESTS.md` entry, a harness run
scored by `timingjoin.py` against the retail column, and the `PLAN-LOG.md` entry.

**WEAPONS-W0 — land the census, read the words (desk, no client).**
`toolkit/authsrv/weaponcensus.py` + `test_weaponcensus.py` (synthetic wire first, vault
section skipped and printed on a bare machine): item types in hands, the modifier census
per type, attackers joined to their weapon rows, launches joined to starts. Then settle,
per attacker rather than in aggregate: `617` = `0x00A4` field 5 (Q1); `609` against the
interval and flight class of the bows that do attack (Q2, partial); `634` (Q9); the
message that names the observer's own weapon (Q8); projectile speed from tapes where the
shooter's position is known (Q3, partial). Second half: **re-source
`[attack_speed.rates]`** — find the duration table in the client (`codescan`, the floats
1.33 / 1.5 / 1.75 / 2.025 / 2.475 / 2.7 adjacent or indexed by item type) so the rows
become `client-table` with an extractor instead of `wiki`. Extend `timingjoin.py` with
`start->launch` and `launch->word vs flight` rows.

**WEAPONS-W1 — one weapon table, a row per type.** `[weapon_type.<key>]` in
`content/world.toml`: item type, hands, attribute, `weapon_req` bit, rate key, delivery
(melee / projectile), projectile id, range, default damage type, each row carrying its own
provenance and label. The three dicts and `PARTY_WEAPON_BY_PROFESSION` read it; source
locks re-pinned by splitting conjuncts, never by bumping counts. An item row per type in
`content/items.toml` built from retail `0x0161` rows on the owner's tapes (file id, model
id, flags, words — measurements; the name stays an id). A `[party.<weapon>20]` row per
type so the harness can put any weapon in the player's hand. No behaviour change for the
four existing types — the known-good arm is the test.

**WEAPONS-W2 — ranged delivery** (the largest absence; wand, staff, five bows, spear, and
type 28 for hostiles). The swing opens as today; at the windup the server sends `0x00A4`
(shooter, the target's position, flight seconds, the weapon's `617` projectile, a handle,
the arrow flag) instead of landing; at launch + flight it sends `0x00A7` and lands the
hit through the existing landing path (word, 46, adrenaline, criticals). Flight =
distance ÷ the class's speed (Q3). Range gates the approach exactly as `ATTACK_REACH`
does for melee (Q4). Both instants join `combat_deadlines`. Bow attack skills ride the
same path (Power Shot's landing is already measured at the windup of 2.475). Heroes and
hostiles stop "swinging" from 1,248 units and shoot. Deliberately NOT in W2: stray,
obstructed, dodged, and height — they need line of sight and a moving-target model, and
get their own package once the straight shot is right. Control flag: `--no-projectiles`.

**WEAPONS-W3 — melee completions. SHIPPED 2026-09-19 (section 26.2): the scythe's extras and its 2^(5/40) critical, on the terms RUN-1A measured.** The axe row and item. The scythe: up to two more
foes in melee range of the target and within 180 of the player, each hit rolled and
worded on its own (wire shape is Q5 — one start and how many `[1]` / 46 / words), and its
critical at 2^(5/40) if Q5 confirms GWW. The sword's short gap after a skill's hit
(inherited from the dagger arc, 9 of 21) is tested here with `--swings` on the two sword
tapes — cross-tab the neighbours first.

**WEAPONS-W4 — damage by type. The rest SHIPPED 2026-09-19, section 30 (W4c was section 16, Q11 section 17, W8 section 26.3); the hornbow's 10 % waits on Q2.** Decode `633` and carry it on item rows; the unmet term
(Q10) is measured before it is modelled — the isle study's refusal stands until then.
Caster weapons scale on level with no mastery (GWW) — checked against the owner's wand
words on `20260913T210901` before shipping. `587` gets its reader: damage type against
armour's `+N vs type` words (the armour side already decodes `527`). Hornbow's 10 %.
The critical table against GWW's formula is a free desk test (Q11). Customisation ×1.2
stays unshipped until a run isolates it (PvP weapons are customised at creation, so the
isle numbers may already contain it — Q12).

**WEAPONS-W5 — off-hand and staff.** `556` energy from a focus or staff joins
`armour_energy_bonus`; `570` recharge on staves; unmet shield and focus values (Q10).

**WEAPONS-W6 — hostiles and heroes on the same table.** Content rows gain a range and a
weapon type; types 1 and 28 become rows; a hostile's repeat delay is handed to monsterai
with C5 as its seed (Q7), not tuned here.

## 6. Captures — only what the corpus cannot hold

> **The runsheet is [RUNSHEET.md](RUNSHEET.md)** (2026-09-18): the four runs written
> out step by step, with the live build verified, the sealed plans already in
> `vault/plans/weapons_1a..3.txt`, an F11 meaning, an exposure floor and an abort per
> run, and the scoring commands. **RUN-2 no longer carries Q16** — §22 answered it
> from the client's own code. This section stays the table; that file is what you
> execute.

Anyone can wield any weapon, and timing, launch, flight, projectile and range do not
depend on meeting a requirement — so **one PvP character on the Isle of the Nameless
covers every clock in two sittings**, with weapons from the PvP equipment panel. House
rules stand: secondary account, human cadence, one client, the driver sends no input,
≤ 8 steps, F11 means one thing per run, predictions sealed first (`vault/plans/`), an
exposure floor and an abort written down.

| Run | Steps (each: equip, F11, 20 plain swings on a Master of Damage suit from one spot, F11) | Answers | Sealed predictions |
|---|---|---|---|
| **RUN-WEAPONS-1A** martial | axe · scythe on ONE suit · scythe with TWO suits adjacent to the target (3 foes hit, the weapon's maximum -- corrected 2026-09-18, this row said three adjacent, which is four) · spear · spear + shield | Q5, Q6, the 1.5 s clock, scythe wire shape and critical, the spear's projectile and flag | scythe and spear start→start 1.500, word / launch at 0.650; spear `0x00A4` field 7 = 1 — **RUN 2026-09-19, capture `20260919T103604`, scored in section 25: every prediction held; the scythe's target-side term measured at [78, 94) u, the spear parked at 755 u** |
| **RUN-WEAPONS-1B** bows and casters | shortbow · flatbow · longbow · recurve · hornbow · staff · wand, all from the same marked spot · **then W9's three presses (§29), the staff in a set: the ACTIVE set's key; an EMPTY set's key; a switch INTO the staff's set from a weapon with no 556 word** | ~~Q2~~ (closed at the desk, §32 -- the five clocks now check the wiki's rates against the client's named classes), Q3 (speed per class — same distance, five flights), the 2.025 and 2.7 clocks, the hornbow's 10 % against the 100-armour suit; **Strength's 1 % a rank (§35: twenty Power Attacks at the character's Strength on the 60-suit -- at Strength 9 a 15-22 sword's ceiling 22 reads 23)**; **one Flare at the suit from the wand (§36: `0x00A4` 343 at 1800 u/s in the E5 batch, the word at the arrival)**; **the Orb block (§39): five Orbs taken standing, five walking straight across at run speed, five sidestepping at each launch -- the lead and the dodge tolerance**; **a hero's Earthquake at the middle Suit (§40: `[58]` then a word and a `[20, suit, hero, 304]` per Suit within 240 u)**; W9's same-set and empty-set replies and the 41 / 43 on a moved maximum | start→launch 0.9125 / 1.1375 / 1.250 / 0.775; flight ratios 0.59 : 0.88 : 0.59 : 0.40 : 0.59; same-set and empty-set presses answered by NOTHING (the smaller claim); the staff switch's batch carries property 41 then 43 |
| **RUN-WEAPONS-2** range | per weapon: stand far, press attack once, let the character walk in; repeat uphill if the Isle allows | Q4 — the distance from shooter to the aim point at the FIRST launch is the range, no free parameter. ~~Q16~~ is **no longer this run's**: §22 answered it from the client's own code (the park threshold has no weapon term), so spend no steps on it | 1004 / 1498 / 1498 / 1273 / 1273; 1248 staff and wand; 1004 spear; the body stands after the first start |
| **RUN-WEAPONS-3** damage (later, needs the right attributes) | met vs unmet requirement on one weapon; a scythe's criticals; hornbow vs longbow on the 100-armour suit | Q10, Q5's critical, W4's penetration | written when W4 opens |

## 7. Open questions

| Id | Question | Instrument |
|---|---|---|
| WEAPONS-Q1 | ~~`0x00A4` field 5 vs the item's `617`~~ **closed §9: 37 of 37; no `617` → 143.** Left: the two arrows with field 7 = 0 | desk |
| WEAPONS-Q2 | Which `609` value is which bow class? **Narrowed §9: 1 and 3 are the two 2.475 s classes. CLOSED at the desk, section 32 (2026-09-19): the client's own 609 handler indexes a five-name table -- 0 Shortbow, 1 Longbow, 2 Flatbow, 3 Recurve Bow, 4 Hornbow -- and 1 and 3 ARE the two 2.475 s classes** | closed; RUN-1B now measures the clocks, not the mapping |
| WEAPONS-Q3 | Projectile speed per class — is flight distance ÷ a constant, and does the arc change it? | desk where positions are known, RUN-1B |
| WEAPONS-Q4 | Range per type in units, and what height does to it | RUN-2 — **read section 25.4 first**: the spear's walk-in parked at 755 u = 0.75 x the wiki's 1004, so RUN-2 must separate the park from the range (one press from the Isle's marked shortbow spot does it) |
| WEAPONS-Q5 | Scythe: duration, how extra targets appear on the wire, the critical's size | **ANSWERED, section 25.3** (2026-09-19): 1.500 s, word at 0.650; an extra is a second word in the same instant, written BEFORE the target's, with its own roll and its own critical; attacker term 180 u confirmed at its edge (hit at 182, missed at 186); target term [78, 94) u centre-to-centre, NOT the 166 u "adjacent"; critical 1.0 < c < 1.40 from one sample, x2^0.5 refuted, x2^0.125 consistent; the cap untested |
| WEAPONS-Q6 | Spear: duration, projectile id, arrow flag, with and without a shield | **ANSWERED, section 25.2** (2026-09-19): 1.500 s, launch at 0.650; projectile 143 by type (the item has no 617), flag 1, `0x00A7` kind 1 = its 587, 1594 u/s; the shield changes nothing |
| WEAPONS-Q7 | A hostile's repeat delay (1.75 / 1.90 / 1.985 / 2.125) | monsterai, desk |
| WEAPONS-Q8 | ~~Which message names the OBSERVER's own weapon type~~ **closed §9: `0x006E` (and `0x0147`)** | — |
| WEAPONS-Q9 | ~~What `634` beside every `633` holds~~ **closed §9: the required weapon's damage range (max, min), in place of `584`** | — |
| WEAPONS-Q10 | The unmet-requirement term — weapon, shield, focus. **SHIPPED as W4's rest, section 30** (2026-09-19): the weapon's is the isle's measured divisor 3.098 (OBSERVED, one hammer at ranks 5–8, studies/isle 9.2), the shield's 8 / 5 and the focus's +3 are WIKI; what RUN-3 still owes is the divisor-vs-strike-level-drop split and a second weapon | RUN-3 |
| WEAPONS-Q11 | ~~Does GWW's critical formula reproduce the five measured rates?~~ **closed §17: NO — 8 / 9 / 11 / 13 / 14 % predicted against 6 / 16 / 19 / 24 / 34 % measured; the table stays the measurement** | — |
| WEAPONS-Q12 | Is ×1.2 already inside the isle study's PvP-weapon numbers? | **CLOSED, section 26.3** (2026-09-19): YES — the isle's own sword carries (585, 120, 0), its tooltip read +20 % and its fit was the customised 18..26 range; 585 is the customisation word, CORROBORATED over 85 corpus items; WEAPONS-W8 reads it |
| WEAPONS-Q13 | The sword's short gap after a skill's hit (from DAGGERS §9) | desk, `timingjoin.py --swings` |
| WEAPONS-Q14 | ~~Dual Shot's second arrow~~ **closed §18: two strike records, each its own roll and word; the 25 % is WIKI, unmeasured** | — |
| WEAPONS-Q15 | ~~A preparation's own word and its substituted arrow~~ **closed §19: shipped as W2e** | — |
| WEAPONS-Q16 | What parks retail's client at range on an attack-follow. **CLOSED at the mechanism, section 22: the threshold `0x005FED20` is `(r1 + r2 + TABLE[kind])^2` and its inputs are six agent fields, NONE a weapon -- so a follow parks at the melee disc whatever is held, retail's client and ours alike, and Q16's premise is refuted. `0x0028`'s handler never writes `+0x98`, which is why all three arms failed; only `0x0029` clears it, and retail sends one to park a shooter 0 of 306 follows.** What remains is an OWNER CHOICE, not a bug | answered; section 22.4 is the choice |

## 8. What this plan refuses

- **No wiki number becomes a pin.** Every §2 cell is a prediction; GWW disagreeing with
  itself on bows is the reminder.
- **No weapon clock is calibrated on a hostile** (C5).
- **No mechanism is built ahead of its wire shape**: scythe targets and stray / dodge wait
  for a tape.
- **No bulk item dump.** Item rows are built one per type from the owner's own tapes, by
  id, under the provenance gate's measurement rule.

## 9. WEAPONS-W0, first half — run 2026-09-18 (desk; no client, no server change)

`toolkit/authsrv/weaponcensus.py` + `test_weaponcensus.py` land §3's scratch censuses as
a tool (five questions per body: types, speeds, attackers, shooters, projectile), and
`timingjoin.py` gains the ranged rows (`swing start->launch`, `launch->word - flight`,
`launch->arrival - flight`) so W2 has its side-by-side column before it is built. Landing
the census moved four of §7's questions and corrected one of §3's numbers.

**WEAPONS-C6 — retail SENDS each body's attack duration, so the rates need no stopwatch.
OBSERVED.** `0x0035 [agent, f32 base, f32 modifier]` goes out at a body's attack start
(JARIN's 19 of 19), and joined to what the body held at that instant it reads: sword
**1.33** ×41, axe 1.33, daggers 1.33 ×22, hammer **1.75** ×9, staff 1.75 ×17, wand 1.75,
the hostile type 28 1.75 ×42, bow **2.475** ×10 — and nothing else for any of them; the
modifier is 1.0 or 0.67 on 153 of 153. `test_weaponcensus.py` compares that measurement
with `[attack_speed.rates]` key by key (two measurements, no literal), so six of the
table's rows are now OBSERVED and the wiki is their second witness, not their source.
Still WIKI-only: scythe, spear, flatbow / shortbow 2.025, hornbow 2.7, and which of
longbow / recurve is which. **Consequence for §6: ONE swing per weapon is enough to read
its duration** — the 20-swing steps are for the windup and the interval's spread, not
for the rate. (The "find the table in the client" half of W0 is withdrawn: the client
holds no such table — `studies/combat/PLAN.md` §17d via `studies/castmech`: duration is `modifier × base`, both
handed to it by this message.)

**WEAPONS-C7 — `634` is the damage range of a weapon WITH a requirement (WEAPONS-Q9,
closed). OBSERVED, an exact partition.** Over every weapon-typed item declared in the
corpus: an item carries `633` **if and only if** it carries `634`, and then it carries
no `584` — axe 28 / 27, bow 99 / 32, hammer 14 / 58, wand 29 / 41, sword 233 / 229,
daggers 10 / 18, spear 2 / 3 (with-requirement / plain-`584`), not one item in both
columns. `634 (max, min)` is the same shape as `584`: requirement-9 daggers
read `(17, 7)`, GWW's 7–17. Shields partition the same way on `572` ↔ `635` (171 / 273)
and foci on `556` ↔ `636` (56 / 19); the client renders `635` through the `Armor: N`
template and `636` through a three-string template of its own, and renders nothing for `634` (the range line
is drawn by the weapon path, not the generic walker). **This server reads `584` only**
(`combatmath.weapon_damage_range`), so a retail-shaped weapon with a requirement would
read as having no range at all — W1's item rows and W4's reader both need `634`.

**WEAPONS-C3, corrected — 37 of 37, not 33 of 34.** The one mismatch was the census: a
last-wins `{agent: hands}` dict gave a REUSED agent id its later body's weapon. Hands are
now a timeline (`hands_timeline` / `held_at`), which a weapon swap needs anyway, and
every shooter whose held weapon carries a `617` shoots exactly that number in `0x00A4`
field 5 — 37 shooters, 0 mismatches, 466 weapon shots, every launch closed by its
`0x00A7` handle, launch + flight against the word p50 4.4 ms. A bow with NO `617` word
shoots **143** (24 of 26; the other two are a skill's projectile leaking through the
weapon-shot filter, left visible rather than tuned away). That closes
[studies/itemmods](../itemmods/FINDINGS.md) §4.3's "read by NOTHING in the client,
UNVERIFIED, deliberately not named": the client never reads `617` because the SERVER
does — it is the projectile the server names in `0x00A4`, which is also why it is a
property of the item's model, 71 of 71.

**WEAPONS-Q8, closed — a player's hands are `0x006E`, not `0x006D`.** `0x006E [agent,
leadhand, offhand, five armour pieces]` names a PLAYER body's two items (the observer's
own `0x0147 [stream, slot, leadhand, offhand]` names the same pair); `0x006D` is every
NPC's. With both read, the 19 player attackers that §3 had as "no weapon row" join:
760+ sword gaps at type 27, the dagger tapes at 32, the hammer at 15, both bows at 5.

**WEAPONS-Q2, narrowed.** The two bows that attack carry `609` = 1 (a hostile's) and
`609` = 3 (the owner's Ranger, item 772 on `20260914T005758`), and both are told 2.475
and cycle at 2.476 — so classes 1 and 3 are the longbow and the recurve in some order,
and 0 / 2 / 4 are the flatbow, shortbow and hornbow. RUN-WEAPONS-1B settles the rest from
`0x0035` alone.

## 10. WEAPONS-W1 — shipped 2026-09-18: one weapon table, a row and an item per type

**The table.** `[weapon_type.<key>]` in `content/world.toml`, eleven rows (axe, sword,
daggers, hammer, scythe, spear, bow, wand, staff, shield, focus): item type, hands,
attribute, `weapon_req` bit, `[attack_speed.rates]` key, delivery, and for the bow the
default projectile 143 and arrow flag 1 — each row `source = "capture"` with what is NOT
measured said in the row (the scythe's and the spear's 1.5 s are WIKI; type 35's name is
UPSTREAM). `authsrv.weapon_type_tables()` builds `WEAPON_TYPE_ROW` and the three dicts
that were four-row literals (`WEAPON_TYPE_ATTRIBUTE` / `_RATE` / `_REQ_BIT`) from it and
REFUSES two rows on one item type or a rate that is no rates key. The known-good arm is
pinned: the four melee rows read exactly what the literals said. The req bits were
checked against something that could refute them — for every type, most skill rows whose
`weapon_req` is exactly its bit carry its attribute (axe 19 of 19, hammer 22 of 22,
scythe 13 of 13, spear 19 of 22, daggers 26 of 32, sword 18 of 21, bow 29 of 42), and for
the bow and the spear that attribute is ALSO the one `633` names on the items themselves.
The hostile-only types 1 and 28 are deliberately not rows.

**The items.** Six retail `0x0161` rows off the owner's tapes, one per type this server
could not hold — `starter_axe` (8–28), `starter_bow` (5–9, `609` = 1, no `617`),
`starter_wand` (3–5, `617` = 0), `starter_scythe` (4–7), `starter_spear` (5–7),
`starter_focus` (energy +5) — each named by the `0x006D` of the body that held it, each
ONE distinct row across every declaration in the corpus, each carrying the generic name
id 8582 and a file both run archives bind (`archive.binds_plainly`).
`combatmath.weapon_damage_range` reads `634` beside `584` (WEAPONS-C7), so a
retail-shaped weapon with a requirement has a range.

**In the player's hands.** `--player-weapon ITEM` / `--player-offhand ITEM` put any item
row in the character's hands, with or without a `--party`; the item's TYPE picks the
attribute, the interval and the req bit, and a two-handed type empties the off hand
(retail names offhand 0 beside every bow, hammer, staff and dagger pair).
`PARTY_WEAPON_ITEMS` resolves the axe, scythe, spear and the five bow keys.

**On the client** (three bounded harness runs, scored off our recorder with
`timingjoin.py`): the bow (`20260918T130414`) — the client draws the bow stance and
crosses out the dagger bar itself, 17 of 17 swings 2.475–2.476 s apart (retail 2.476);
the scythe (`20260918T130610`) — in the hand and swinging, 23 of 23 at 1.500 s, the word
at 0.650–0.651; the spear (`20260918T130729`) — 23 of 23 at 1.500, word at 0.650. No
assert in any log: item types 5, 35 and 36 had never been sent by this server. The
side-by-side also states W2's job in one row: retail's bow RELEASES at 1.138 s and the
word lands 1.347 s after the start; ours lands the word AT 1.138 with no launch, from
melee reach.

Not in W1, by design: no per-type damage rule changed (a wand names no mastery, so its
rank is None and the swing takes the raw-range fallback `hit_enemy` already had — WIKI's
damage-by-level for caster weapons is W4), `587` still has no reader, a party caster keeps
the staff until W2 gives it a projectile, and `starter_bow` does not carry `fires_arrows`
(the gate `swing_preparation_bonus` reads) until its arrows exist.

## 11. WEAPONS-W2a — shipped 2026-09-18: the player's ranged delivery

Two more desk findings first, both off `weaponcensus.py` and both needed to send the
messages honestly.

**WEAPONS-C8 — projectile speed is a round number per weapon class. OBSERVED, by
mutual-shot geometry.** `0x00A4` carries the TARGET's position, so when two bodies shoot
each other the shooter's own position is the aim point of the latest shot AT it; distance
÷ the message's flight time, 80 shots: **1200 u/s** for the hostile-only type 28 (23 of
27, arrows and bolts alike), **1600** for a staff or wand holder (11 of 15), **2800** for
the owner's bow (`609` = 3: 4 of 5 plain shots within 100 of it, and its attack skills'
six arrows at 2779–2813). Flight
is distance over a constant, not a constant time (staff: intercept +0.002 s, slope
1/1593). Speed follows the WEAPON, not the projectile id — arrow 143 flies at 1200 from a
type 28 and 2800 from the bow. By GWW's flight-time ratios 2800 is the recurve, which
makes `609` = 3 the recurve and `609` = 1 the longbow by elimination (RECONSTRUCTION);
GWW's own times at 1004 u imply 1140 / 1700 / 2510 u/s for its three arrow classes — near
the tape's round 1200 / 1600 / 2800 without matching them, so RUN-WEAPONS-1B's prediction
is stated as round numbers: flatbow 1200, shortbow / longbow / hornbow 1600, recurve 2800.

**WEAPONS-C9 — `0x00A7`'s third field is the weapon's `587` damage type. OBSERVED, 61 of
61 weapon shooters.** `schema/overrides.json` has it as "a per-attacker constant paired
with the launch's field 5"; it is the held item's own `587` argument — 1 behind every
arrow, and 6 / 3 / 7 / 11 / 5 / 8 / 4 behind projectiles 0 / 1 / 2 / 3 / 4 / 5 / 6 because
those are the damage types the items carrying those `617` words carry. The two
mismatches in the census are a bow attack skill's arrow (projectile 343, kind 5) leaking
through the weapon-shot filter. The launch's handle counts the shooter's OUTSTANDING
projectiles from 1 (1 / 2 / 3 on 390 / 169 / 58 launches). A shot carries no property 1
(melee's close) and retail's movement hold ends at or a quarter second after the
RELEASE, never at the hit (3 shots read on `20260914T005758`).

**What shipped.** `player_ranged()` reads how the held weapon shoots — the item's `617`
else the type row's default, the row's `arrow`, the item's `587`, and `projectile_speed` /
`range` (a bow's `speed_by_609` / `range_by_609` per class) — and is None for a melee
type, with the feature off, or when no projectile id is known (**the spear stays on the
melee path until a tape names its projectile**). At the windup `_land_player_swing`
calls `launch_player_projectile`: `0x00A4 [me, the target's position, 0, distance ÷
speed, projectile, handle, arrow]`, the hold released there; `projectile_tick` — beside
`second_strike_tick` on both tick sites, its arrivals in `combat_deadlines` — sends
`0x00A7 [me, handle, damage type]` and then lands the hit through `hit_enemy(...,
projectile=True)`, which skips property 1. A target that died in flight is still closed
and lands nothing. `attack_reach()` returns the weapon's range, so a press inside it
opens the shot where the character stands. `--no-projectiles` is the control;
`--enemy-offset X,Y` stands the hostile at range for the harness.

**On the client**, scored by `timingjoin.py` beside retail:

| Row | Retail bow `20260914T005758` | Ours, bow from 900 u (`20260918T132541`) | Retail wand `20260913T210901` | Ours, wand from 700 u (`20260918T132736`) |
|---|---|---|---|---|
| swing start→start | 2.476 | 2.475 × 17 | 1.749 | 1.750 × 21 |
| swing start→launch | 1.138 (1.119–1.157) | 1.138 × 17 | 0.776 (0.762–0.791) | 0.775 × 21 |
| launch→word − flight | −0.000 (±0.020) | +0.001 | 0.000 (±0.018) | +0.001 |
| launch→arrival − flight | −0.000 | 0.000 | 0.000 | 0.000 |

The character stands at range with the arrow nocked and never walks in; no assert; the
wand's bolt (projectile 0, arrow 0) and a focus in the off hand are accepted.

**Named follow-ups, not oversights.** W2b: a press OUTSIDE range still walks the body to
melee distance (the follow ends at the client's own stop disc; stopping at range is a
movement change). A bow ATTACK SKILL still lands through the cast path with no arrow.
Heroes and hostiles still "swing" from `PARTY_RANGED_REACH` with no projectile (W6).
`timingjoin.py`'s `swing start->word` window is 1.5 s, which a long shot outlives (retail
7 of 12, ours 0 of 17 at 900 u) — the ranged rows are the instrument for shots. Ranges
are WIKI until RUN-WEAPONS-2.

## 12. WEAPONS-W6a — shipped 2026-09-18: heroes and hostiles shoot

**The shape is the player's, read off bodies' own shots.** Retail's hostile and henchman
shots are the four messages of §11 exactly — the start, `0x00A4` at the windup, `0x00A7
[shooter, handle, its weapon's 587]` and the word a flight later — and **no property 1**:
the `[finished, damage]` pair `land_swing` sends is melee's (read on `20260914T180058`
agent 81, a type-28 bolt-thrower, and `20260817T231139` agent 14, a henchman's staff;
58 of the corpus's 65 weapon shooters are bodies). The hostile-only item type 28 is ONE
file (111902) across all 278 holdings; its holders are told 1.75 s by `0x0035` (42 of 42),
its projectiles fly at 1200 u/s (WEAPONS-C8), and flight × 1200 over all 305 of its shots
tops out at 1234 u (p99 1146) — so its range is **RECONSTRUCTED as 1248**, the casting
range just above that maximum.

**What shipped.** `weapon_ranged(item)` is the generic reader (`player_ranged()` wraps
it); `body_ranged(agent)` reads what a body HOLDS — `agent["weapon_item"]`, the content
item its `0x006D` names: a party caster's staff, a spawn row's weapon, `--enemy-weapon
ITEM` for the fixture hostile. `land_or_launch` is the one call all three body landing
sites make (the hostile's late-hit branch, its in-reach branch, the ally's): a melee item
lands through `land_swing` as before, a ranged one calls `launch_body_projectile`
(handles count each SHOOTER's own outstanding shots). `body_projectile_tick` — the first
line of `projectile_tick`, so no new tick site — sends `0x00A7` and lands the hit through
`land_swing` with melee's close filtered out of the send (`_without_melee_close`: one
filter, not a flag through six send sites that tests pin as text). Reach: `party_reach`
returns a ranged body's range (a staff's 1248 IS the old `PARTY_RANGED_REACH`, so a
caster's stance is unmoved); a ranged hostile's attack gate reads `body_reach` and its
chase parks at range through `_npc_follow_tick`'s existing `stop_at` — 1248 u is outside
the 1012 u notice radius, so an archer that notices you shoots from where it stands.
`[weapon_type.hostile_ranged]` (type 28, `holder = "hostile"`, arrow flag DERIVED from
the projectile because the type shoots both) and two retail items, `hostile_bow` (no
`617`: arrow 143) and `hostile_bolt` (`617` = 1, kind 3 — retail's pair, 145 of 145);
the player loader REFUSES an item of a hostile-only type. `--no-projectiles` reverts
bodies too.

**On the client**, scored by `timingjoin.py --observer`:

| | start→launch | launch→word − flight | launch→arrival − flight | n |
|---|---|---|---|---|
| retail, 1.75 s weapons (census) | 0.775 | 0.000 ± 0.02 | 0.000 | 432 |
| ours, the party Monk's staff at the leader's target (`20260918T140939`) | 0.775–0.776 | 0.000 | 0.000 | 27 |
| ours, a hostile archer at the player from 700 u (`20260918T141119`) | 0.775 | +0.001 | 0.000 | 12 |

The Monk's swings are 1.750 s apart; the archer halts at 700 u and never walks in. Its
start-to-start gaps are 1.75–3.3 s because the fixture hostile's default BAR casts
between shots (the log interleaves its three skills with the starts; the shortest gap
reads 1.750) — not because the shot clock is off. No assert: item type 28 had never been sent by this server.

**Still open here.** No content spawn row holds a ranged item yet (the mechanism is
content-ready: `weapon_item = "hostile_bow"`). A ranged hostile still CASTS from
wherever it stands. The hostile repeat-delay classes (WEAPONS-C5) are unmodelled. ~~A bow
attack skill, for the player or a body, still lands through the cast path with no arrow~~
— §13, WEAPONS-W2c.

## 13. WEAPONS-W2c — shipped 2026-09-18: attack skills shoot

**The wire shape, OBSERVED on every skill shot in the live corpus** —
`weaponcensus.py --skill-shots`, the complement of the weapon-shot census: a launch whose
shooter's latest event is a skill's (a player's `0x00E5`, a body's `[50 | 60]`
announcement) rather than a `[4]` start. 151 launches by 12 skills, every one closed by
its `0x00A7`, the word at launch + flight (p50 |err| 4.4 ms, n = 150), and **not one with
a 46 within 50 ms of the launch** — the attack trio's close that melee's E5 carries 40 of
40 rides no ranged skill's, player or body. A player's bow skill is **`0x00E5`, `0x00A4`,
`0x00E3` in one batch** (E5→launch 0.000 on 5 of 5 bow skill shots; the E3 rides the E5
because a bow attack skill's aftercast is 0); a body's launch comes **one bow windup after
its announcement** (announce→launch median 1.137 over 44 bow skill shots by hostiles and
henchmen, against `swing_windup(2.475)` = 1.1375). Per skill, one projectile:

| Skill (the client's own text) | shots | `0x00A4` field 5 | flag / kind |
|---|---|---|---|
| 392 Pin Down | 2 | 680 | the bow's (1 / 1 plain; 0 / 5 under Kindle Arrows) |
| 394 Power Shot | 14 | 680 | the bow's |
| 396 Dual Shot | 16 | 680, TWO launches per windup (handles 1 and 2) | the bow's |
| 402 Determined Shot | 8 | 680 | the bow's |
| 404 Poison Arrow | 9 | 143, or 343 under Kindle Arrows | the bow's |
| 1197 Needling Shot | 7 | 143 | the bow's |

The arrow flag, the arrival's kind, the speed and the range follow the WEAPON, not the
skill: Power Shot's 680 flies with flag 1 / kind 1 from a plain bow and flag 0 / kind 5
under Kindle Arrows on the same tape (`20260914T005758`), exactly as the plain arrow does.

**WEAPONS-C10 — the skill record's `+0x88` is the projectile it launches, `+0x84` its
impact visual. OBSERVED, two instruments.** Named by the wire the way ANIMREF-R8 named the
visual pair: the twelve (skill → projectile) pairs above and the spells' — Dancing Daggers
854, Fireball 343, Lightning Orb 403, Lightning Javelin 405 — are reproduced by exactly
that dword, and the two skills that shoot the weapon's own arrow read **2077**, the
table's "none" (the visual slots' own default). `test_weaponcensus` joins the two
instruments over the corpus: the table names the launched projectile on 150 skill shots
and disagrees on none. A preparation carries the arrow it SUBSTITUTES — Kindle Arrows
reads 343, and every plain shot under it flew as 343 with kind 5 — and `+0x84` is the
`[20, target, caster, id]` retail sends at the arrival (344 behind both 343s, 404 behind
the Lightning pair, 855 behind 854; 2077 on every bow attack). `skilltable.py` decodes
both; `projectile` is emitted to `vault/content/skills.toml` (1,333 rows re-emitted from
the pinned build, one added line per row and nothing else moved); `impact_visual` was
decoded and not sent until §19 emitted and sent it.

**What shipped.** `skill_projectile(id)` reads the row's `+0x88` (None for 2077, 0, a row
without the column, no row — a bare machine shoots the weapon's arrow, the honest fallback
`skill_timing`'s zeros already are); `skill_shot_how(how, id)` swaps the skill's
projectile into `weapon_ranged`'s dict and nothing else. **The player:** at the E5 of an
attack skill with a ranged weapon in hand the 46 is NOT sent and, in place of the strike,
`launch_player_skill_shot` sends the `0x00A4` (the E5 batch is `0x00E5`, `0x00A4`,
`0x00E3`, retail's order) with the strike — the skill, its rank, its "+ Damage", its
condition, its knock-down — riding the shot record; `projectile_tick` hands such a shot
to `land_player_skill_shot`: `0x00A7` first, then `hit_enemy(skill_strike=True,
projectile=True)` (the roll plus the bonus as ONE word, no property 1), then on a landed
hit the adjacent damage, the knock-down and the random condition, then the skill's
condition on a live target — the E5 block's order, a flight later. The recharge, the
on-body visual, the effect, the heal, the adrenaline wipe, the self knock-down and the
chain's restart stamp stay at the E5 (retail's next plain start is one recovery behind
the E5). **A body:** `land_skill`'s attack branch, when `body_ranged(agent)` is not None,
launches through `launch_body_projectile` with the strike on the record;
`body_projectile_tick` hands it to `land_body_skill_shot` (`land_swing` with the bonus,
its 46 filtered out beside melee's close — `_without_melee_close` drops both — then the
knock-down, the random condition and the skill's condition). A sword's press, a hammer's
body, `--no-projectiles`: the E5 strike with its 46, unchanged (the known-good arm).

**On the client**, scored by `timingjoin.py` beside the retail bow tape:

| Row | Retail `20260914T005758` (player, recurve, Kindle Arrows up) | Ours, the player's bow at a passive hostile from 800 u (`20260918T152121`) |
|---|---|---|
| E5→launch 394 / 392 | 0.000 / 0.000 | 0.000 / 0.005 |
| E5→E3 394 / 392 | 0.000 / 0.000 | 0.001 / 0.005 |
| skill launch→word − flight | −0.002 (−0.017 .. 0.001), n = 3 | +0.001, n = 4 (394, 404, 402, 392) |
| skill launch→arrival − flight | −0.002, n = 3 | 0.000 (0.000 .. 0.001), n = 4 |

Power Shot at 800 u flew 0.500 s (680, handle 1, flag 1) and landed 5 on a 20,000-health
target; the three that followed flew 0.050 s because the passive hostile, once hit, ran
in — the flight is the distance's, per shot. Pin Down's Crippled landed at the ARRIVAL,
not at the E5. **The 46's absence leaves no movement lock:** the `W:2` leg after the last
E5 produced two `MOVE_SET_HEADING` reports the server answered — the client walks on a
held key straight after a ranged skill's E5, which is the fear the melee comment's "8+
second movement lock" recorded, refuted for the ranged case. No assert.

A body's, scored the same way over our recorder (`weaponcensus.skill_shots` on the
capture): a hostile archer (`hostile_bow`, type 28, 1.75 s) with Power Shot on its bar at
the standing player from 700 u (`20260918T152408`) — **10 Power Shots, announce→launch
0.775 (0.758 .. 0.776; its own weapon's `swing_windup(1.75)` = 0.775), projectile 680 with
the type's flag 1 / kind 1, flight 0.583 (700 ÷ 1200), every launch closed, the word at
launch + flight (max |err| 0.9 ms), no 46**, with 17 plain 143 shots at the same 0.775
between them; the archer shot from where it stood. Retail's bodies with a type-5 bow read
1.137 for the same row because their weapon is the 2.475 s one — the clock is the held
weapon's, which W6a already established for plain shots.

**Not modelled, said here rather than discovered.** Dual Shot's SECOND arrow (retail
launches two at one windup, handles 1 and 2 — 8 pairs on `20260817T231139`); a
preparation's substituted arrow and its own word (under Kindle Arrows every arrival, plain
or skill, carries a second `0x00A3` of a constant −0.03, 4 of 5 — `swing_preparation_bonus`
folds it into one number, which retail does not); `+0x84`'s impact visual; the handle
retail gave the Kindle-tape skill shots (2 with nothing outstanding — ours counts from 1).
One census row is unexplained: a body's launch of 343 attributed to "skill 2" behind a
`[60]` announcement at +0.000 (n = 1; its latest event was probably not its own).

**Still open here.** ~~W2b (a press outside range walks to melee distance)~~ — §14, the
server's half; no content spawn row holds a ranged item; a ranged hostile still casts
from wherever it stands; the hostile repeat-delay classes.

## 14. WEAPONS-W2b — shipped 2026-09-18 (the server's half): the approach ends at the weapon's range

**What was wrong, measured on the client first.** Under the arm every run before today
used, a bow's press on a hostile 1,800 u away sent retail's `0x002A` follow, and then
the SERVER walked its own copy to the 80 u melee disc — the leg's stop point, the
integrator's `dest`, the follow's eta and the skill press's busy estimate were all
`follow_stop_radius` — and the swing waited for that arrival: `20260918T170801`
(`--legacy-ranged-approach`, a frozen practice target south-east of the spawn, on the
mesh with a clear line) opened the first swing 6 s after the press and its first arrow
flew **0.045 s — 72 u**. The reach gate had read the range since W2a; the leg had not.

**Retail, OBSERVED on the four clean ranged approaches the corpus holds** (a press, no
report of any kind, then the start — `20260914T005758` at 221.5 and 581.6,
`20260810T235916` at 90.2, `20260807T143055` at 81.7): the follow is the melee one
exactly (the target's own position, re-issued every 0.5 s while it moves), the start comes
1–5 s later, its batch carries the walk-gate hold `[8, me, 1]` 4 of 4 and **no movement
message precedes or accompanies it**; the one case with no operator input for a whole
swing after the start (90.2) has the second launch 2.5 s on with the distance shrunk by
the target's own approach and nothing more — the body stood where the start left it.
No property on the player carries a range-sized value anywhere on those tapes (scanned:
every int and f32 property in 600–1,700 beside the `0x006E` weapon swaps; only property
21's energy), so the client is not told its range — it knows it.

**What shipped.** `approach_stop(target)`: the melee disc for a melee weapon, the held
weapon's range (`player_ranged()["range"]`, = `attack_reach()`) for a ranged one, never
less than the disc; `_approach_send`'s stop point, the integrator's `dest`, the follow's
eta, `approach_tick`'s arrival test and the skill press's busy estimate all read it. The
wire is unchanged: the same `0x002A` with the target's own position. On the client
(`20260918T170928`, the same target): the follow says "swing at 1498 u in 1.05 s", the
start opens at 1.05 s, the first arrow leaves 1.14 s later — the arm the plan asked for,
against the 6 s and 72 u of the run before it. `--legacy-ranged-approach` reverts.

**What the client did, and why that is not this rung's to fix.** The first arrow's
flight was 0.726 s — 1,162 u at 1,600 u/s — and the next 0.281 s, then 0.045: the body
walked on through the start, the hold and the release at exactly the run speed (336 u in
the 1.1375 s windup, 712 u over the next 2.475 s) to the disc. So `[8, me, 1]` does not
park a client that is on a `0x002A` follow, and retail's client parks itself with no
message. The harness cannot exercise what does it: its `attack:` step is the server
mailbox (`begin_attack` from the action script — the log says so), so the client never
sent its own `0x0026` and never armed its own attack-follow, which is where a client-side
range check would live (RECONSTRUCTION; the alternative, that the client parks on its
attack start, is refuted by this run — our start is retail's start). **The client's
half is RUN-WEAPONS-2's**, which was already the range capture: the owner presses attack
on a hostile beyond range with each weapon and lets the character walk in; where it stops
is both the range (Q4) and this question (Q16). Until then, under the harness a ranged
approach shows the body walking through the shot, and a person at the keyboard should
see it stop.

**Test.** `test_weapons` §8 (68 checks): the stop for a bow and a sword, the follow bit
for bit as before, the leg / `dest` / eta ending 1,498 u short, the arrival ending the
follow with the gate open, the sword's disc unchanged, the revert arm and its flag.

## 15. WEAPONS-W5 — shipped 2026-09-18: a staff's or a focus's energy

**The word is OBSERVED, the rule is WIKI, and the split is stated.** On retail's items
the energy word is `556 (N, 0)`: +5 / +10 / +3 / +4 over 56 foci and +9 / +10 on 483 of
535 staves (the requirement-gated form is `636 (N, 6)` on 19 foci — WEAPONS-Q10's unmet
term, NOT read); a wand, a sword and a shield carry none. **No observing player on any
live tape ever held a focus or a staff** — the scan of every `0x006E` (52 swaps across
the corpus) shows leads of type 5, 15, 22, 27 and 32 and off hands of type 24 or none —
so what retail puts in property 41 with one in hand is UNOBSERVED, and the rule that
`556` raises maximum energy is GWW's ("Focus item", "Staff"). What retail IS seen to send
is property 41 at instance load (97 in the corpus) and the f32 regen rate in property 43
that a larger pool lowers — the two sends `player_max_energy` already feeds.

**What shipped.** `weapon_energy_bonus()` sums the `556` argument on the lead item and
the off hand; `player_max_energy` adds it to the party row's typed pool before
`morale.effective_max`, which scales only the innate 20 — the focus rides like a rune.
The party row's `player_energy` stays the number the armour agrees with (DAGGERS-F15);
the row itself is untouched. `apply_party_character` prints the term. A row naming both
a staff and a focus keeps both by the loader's own rule (the row's off hand wins) and the
words sum — stated, not endorsed. `--no-weapon-energy` reverts. On the client
(`20260918T172315`, a wand and the retail focus): "PLAYER energy = 30" at spawn beside the
row's 25, no assert; the bar the client draws from that number is unread.

**Test.** `test_weapons` §9: the focus +5, the staff +10, a sword and shield 0;
`player_max_energy` the row's pool plus the word and the row's pool alone without one;
the seeded pool's maximum and its property-43 rate over the larger pool; −15 % morale
scaling the innate 20 and leaving the +5 whole; both held summing; the revert arm and
its flag. Floor 74 bare, 75 with the vault.

**Still open here.** Q10 (the unmet requirement: `636` on foci, `633` on staves);
`570 (16..17, 1)` on staves beside GWW's "halves skill recharge 10–20 %" has no reader;
the shield's `572` armour is W4's with `587`. **All three closed since (2026-09-19): Q10
and `587` in section 30, `570` in section 31.**

## 16. WEAPONS-W4c — shipped 2026-09-18: a wand or staff scales on the character's level

**What was wrong.** A wand or staff names no mastery (W1 kept the two caster rows out of
the attribute dict), so `player_weapon_rank` returned None and `hit_enemy` fell to the
raw-range branch: the weapon's `584` with no armour term, no level and no critical — a
level-1 character's 3–5 wand landed 3–5 on anything, a level-20 character's on a
100-armour target too.

**The rule is WIKI, explicit, with its own worked example.** GWW "Damage calculation"
§Caster Weapons: "the damage they deal only scales up with your character level, as
there is no Mastery for these two weapon types. A level 20 player meeting the listed
requirement will deal the listed base damage" — and the page's wand example, 6 × 1.20 ×
2^((3 × 10 − 60) / 40) at level 10, puts the strike level at **3 × level**, the skill
curve `agent_strike_level` already gives bodies' spells. The critical is the same page's
chance formula (Isaiah Cartwright's) with a weapon skill of 0: 0.05 × 2^((8 La − 15 Ld −
100) / 40), 0.8 % at level 1 against level 1, 0.08 % at 20 against 20 — the plan's "very
low", not the martial table measured from rank 8.

**Checked, as §5 asked, against the owner's own wand.** Not on `20260913T210901` — that
character's hands read empty on the wire and its ten 3–5-point hits are unarmed, and the
level-13 character with a 3–5 wand landed nothing — but on `20260807T143055`: player 31 at
level 1 with a 3–5 wand (`584 (5, 3)`, `587` 7) landed **5 on a level-1 creature and 3, 4,
4, 4, 4 on a level-2 one**. With strike level 3 and the creature armour the server already
derives (3 × level: 3 and 6), the rule gives 3–5 and 2.9–4.8: every hit reproduced. So does
the old rank-0 rule after rounding, so the six hits are **CONSISTENT, not discriminating**;
what discriminates is the level-20 case, where the raw branch's 3–5 against any armour was
plainly not retail. The henchmen's staves on `20260817T231139` (level 20, 11–22) land
10–26 on level-20 bodies — strike level 60 under either rule, the rank and the level
coinciding at 20 for a rank-12 mastery.

**What shipped.** `combatmath.swing_damage` takes `strike_level=` and uses it in place
of `attack_strength(rank, level)` when given; `caster_weapon(item)` is a row with `rate`
wand or staff; `caster_strike_level(level)` = 3 × level; `caster_critical_rate(La, Ld)`
the wiki's; `hit_enemy` takes the caster branch ahead of the rank branch when the held
weapon is one, at the character's level (`state["level"]`, else the party row's) against
the target's armour; a BODY holding a wand or staff (`body_swing_damage`) swings at its
own `agent_strike_level` — the party Monk's staff at level 3 lands 8 of a 20-point roll
against 60 armour where its rank-3 mastery gave 9. `--no-caster-level` reverts. **On
the client** (`20260918T173810`, a level-20 character with the 3–5 wand and the focus at
a level-1 practice target, 300 u): the twenty words are **8 × 9, 11 × 6 and 13 × 5** — the
three values a 3, 4 or 5 roll gives at strike level 60 against 3 armour (× 2.69), and
nothing else; the Monk's staff beside it 3, 4 and 6 at its strike level 9. No assert.

**Test.** `test_weapons` §10: which items are caster weapons; the critical's two values
and its missing-level default; the strike level handed straight to `swing_damage`; the
wand through the real `hit_enemy` at 20 / 10 / 20-vs-100 (5, 3, 2); the owner's level-1
hits reproduced; the staff in the listed range at 20; the level-3 body's 8 against the
mastery's 9 with a hammer keeping its mastery; the revert arm and its flag. Floor 84
bare, 85 with the vault.

**Still open here.** Q10 (the unmet requirement's 1/3 — the wiki's number, RUN-WEAPONS-3);
Q12 (×1.2 customisation: the one critical on the owner's tape, 9 of a 3–5 wand at level 1,
is 8.5 with it and 7 without — n = 1); `587` against armour's `527` (no repo armour row
carries one yet). Q11 is §17.

## 17. WEAPONS-Q11 — closed 2026-09-18 (desk): the wiki's critical formula is refuted by the isle's table

GWW "Damage calculation" §Critical hits carries a chance formula attributed to Isaiah
Cartwright's talk page:

```
chance = 0.05 × 2^((8·La + 4·Ws + 6·min(Ws, (La + 4) / 2) − 15·Ld − 100) / 40) × (1 − 0.01·Ws) + 0.01·Ws − WeaponCrit
```

`studies/isle` measured the rate on one level-20 body at one armour rating by a level-20
Warrior (495 events over seven blocks, roughly seventy swings per rank):

| rank | wiki, 20 vs 20 | measured (isle) | ratio |
|---|---|---|---|
| 8 | 8.3 % | 6.25 % | 0.75 |
| 9 | 9.3 % | 15.69 % | 1.68 |
| 11 | 11.5 % | 18.60 % | 1.62 |
| 12 | 12.6 % | 23.68 % | 1.89 |
| 13 | 13.6 % | 34.29 % | 2.52 |

Not a constant factor and not the shape: the formula rises a point per rank where the
table rises five. With a lower target level the formula's base term grows for every rank
at once, so no `Ld` rescues it. **REFUTED as written; the five-point table stays the
measurement and `critical_rate` its interpolation.** The formula's one surviving use is
§16's caster critical, its weapon-skill-0 branch, where nothing has been measured — it is
WIKI-only there, and at 0.08 % (20 vs 20) it is indistinguishable from none, which is what
the plan's "very low" said.

## 18. WEAPONS-W2d — shipped 2026-09-18: Dual Shot's two arrows

**The shape, OBSERVED on eight windups by bodies on `20260817T231139`.** At the windup TWO
`0x00A4` in one instant with consecutive handles (1 and 2, or 2 and 3 when a shot was still
outstanding), one projectile (680), one aim and one flight; each arrow closed by its own
`0x00A7` (together when the flights match, 20 ms apart when they differ by 2 ms) and
**worded on its own** — one of a pair a critical (property 17) while the other is not —
each with the Kindle Arrows word beside it (a constant −0.0072 of the target's pool, twice).
Two independent strikes, then. **The numbers are WIKI**: GWW "Dual Shot" (id 396), "Shoot
two arrows simultaneously at target foe. These arrows deal 25% less damage", and its note
that bonus damage from conjures, preparations and weapon spells is not reduced — which is
what the paired words show. The 25 % itself is unmeasured: those targets' pools are not
broadcast on the tape, so no arrow's points could be read against a plain shot's.

**What shipped.** `[skill_arrows.396]` in `content/world.toml` (`arrows = 2`, `damage_pct
= 75`, provenance wiki + the tape's shape); `skill_arrows(id)` → (count, factor), (1, 1.0)
for every skill without a row; `launch_player_skill_shot` launches `count` shots in one
instant, each carrying the strike with `mult` and a `first` flag; `land_player_skill_shot`
lands each through `hit_enemy(damage_mult=)`, which scales the WEAPON's number beside the
weakness term and leaves the skill's bonus whole, and rides the adjacent damage, the
knock-down and the skill's condition on the first arrow only; a body's `land_skill`
launches as many, its strikes landing through `land_swing` at the full weapon number
(`land_swing` carries no factor — the 75 % is the player's alone, said). On the client
(`20260918T175321`, the bow at a passive hostile from 800 u, three presses): E5, two
launches (handles 1 and 2, 0.500 s), E3 in one batch; two arrivals and two words per press
(5 / 5, 6 / 5, …); no assert.

**Test.** `test_weapons` §11: the row and the default; Dual Shot's E5 sending two launches
with the tape's shape and two strike records; both handles closing and two words of 6
from an 8-point roll (the foe down 12); the condition once; Power Shot's one arrow at
100 % plus its unscaled +10; a hostile archer's Dual Shot launching two and landing two on
the player with the condition once. Floor 91 bare, 92 with the vault.

## 19. WEAPONS-W2e — shipped 2026-09-18: a preparation on the wire

**OBSERVED on the owner's recurve under Kindle Arrows** (`20260914T005758`, one 24 s
episode, 512.1–536.1): every launch flies as the PREPARATION's projectile — 343, the
type-19 record's own `+0x88` — with the arrow flag 0, where the same bow's plain arrow is
143 / 1 before and after; a skill's own projectile (Power Shot's 680) still wins, with the
preparation's flag and kind; the arrival's kind is 5 (fire) on 6 of 6 where the plain
arrow's is 1; and each arrival lands the arrow's word and then a **second word** for the
preparation's bonus — a constant 3, the rank-0 scale, on 5 of 6 — with the impact visual
`[20, target, me, 344]` (`+0x84`) before each word. **WIKI** (GWW "Kindle Arrows", id
433): "your arrows deal fire damage and hit for an additional 3...24 fire damage", and
the note "affected by armor rating and dealt separately from the arrow damage" — the
second word, through the arrow's own armour term.

**What was wrong.** `swing_preparation_bonus` folded the bonus into the arrow's one
number ("one swing, one number on screen"), and its gate — the weapon row's
`fires_arrows` — was on no content row, so the preparation was inert on every bow.

**What shipped.** `fires_arrows = true` on `starter_bow` and `hostile_bow`;
`[skill_effect.433]` (a fire-damage preparation, `damage_type = 5` OBSERVED); the
extractor emits `impact_visual` (+0x84) beside `projectile` (the vault rows re-emitted,
one added line each); `open_preparation(state, agent)`; `skill_impact_visual(id)`;
`player_ranged(state)` substitutes the preparation's projectile, a flag derived from it,
and its kind, the weapon's speed and range untouched (`_land_player_swing` and the E5
block pass the state); `hit_enemy` no longer folds: the arrow's word is the weapon's,
then the impact, then the preparation's own word through the same armour term
(`_prep_scale`, set per branch), the impact before each. `--no-preparation-wire` is the
fold with the plain arrow. **On the client** (`20260918T180500`, Kindle Arrows cast then
plain shots at a passive hostile from 800 u): the episode applied for 24 s at rank 0,
every launch 343, every arrival `0x00A7` kind 5, impact 344, the arrow's word (6 / 9 / 6
…), impact 344, the preparation's 2 (its 3 through the Hatcher's armour term); no assert.

**Test.** `test_weapons` §12: the bows' gate and the wand without it; Kindle Arrows'
row; `open_preparation`; the substitution with and without the episode and without a
state; a skill's own projectile under it; a plain shot through the real loop — the 343 /
0 launch, the arrival's kind 5, the arrow's 8 and the preparation's 3 as two words with the
foe down 11, the impact before each word in the tape's order; the revert arm's one word
of 11 with no impact; the flag. Floor 101 bare, 102 with the vault.

**Not here.** ~~Ignite Arrows' adjacency splash~~ — §24; a
preparation on a BODY's bow (`body_ranged` reads no episode) — §20; which element each
`587` id names beyond fire = 5.


## 24. WEAPONS-W7 -- shipped 2026-09-18: Ignite Arrows explodes, on the target and on every foe adjacent to it

The gap `episodemods.swing_preparation_bonus` has named in its own docstring since the
preparation landed -- *"KNOWN GAP, named: Ignite Arrows' damage is 'to target and all
adjacent foes' -- the adjacency splash is not modelled, only the on-target bonus"* -- is
closed. It is the last rung of this arc that needed neither the owner nor a content
decision.

**The skill, resolved from the client rather than guessed.** `skilltable.py` on build 38797,
with the names resolved through `textrec.TextIndex`, reads **431 = Ignite Arrows**:
`type_code` 19 (preparation), attribute 24 (Wilderness Survival), projectile (`+0x88`)
**735**, impact visual (`+0x84`) **734**, and `aoe_range` **156** -- the same field and the
same number Death Blossom's adjacent damage already reads (DAGGERS-B8). Only two
preparations in the whole table carry a radius: 431 and 434 (Choking Gas).

**WIKI for the rule and the numbers** (GWW "Ignite Arrows", id 431, fetched 2026-09-18):
*"Preparation. For 24 seconds, your arrows explode on contact, dealing 3...18 fire damage to
target and all adjacent foes"*, `causes1 = Fire Damage`, and `{{Skill progression}}` var1
`Fire damage` 3 -> 18, which is the client record's own `scale0` 3 / `scale15` 18. Three of
its Notes are the behaviour, and all three shipped:

* *"will deal **armor-respecting** fire damage to all foes in an area adjacent to the landing
  area of each shot arrow"*;
* *"The explosion occurs **regardless of whether the arrow actually hits** its target (even if
  it misses, strays or is blocked)"*;
* *"**Multiple-arrow attacks** (Dual Shot, Forked Arrow, Triple Shot and Incendiary Arrows)
  will trigger an explosion for each arrow"* -- which W2d's per-arrow strikes already give,
  free, because each arrow runs the landing path on its own.

**NOT OBSERVED, and the row says so.** The live corpus holds **0** launches of projectile
735, **0** applies of 431 and **0** impacts of 734. So the numbers are WIKI, the shape is the
CLIENT's own table, and the WIRE shape is W2e's -- measured on the one preparation retail did
send (Kindle Arrows, `20260914T005758`). This is W2d's provenance pattern exactly: the shape
observed elsewhere, the numbers from the page.

**What shipped.** `preparation_splash(...)`, beside the other adjacent-damage machinery: the
opt-in is the `skill_effect` row's `adjacent_damage` (that rung's own convention, so a
preparation with no row splashes nothing -- Kindle Arrows does not), the radius is the
skills row's `aoe_range`, and each neighbour takes the bonus **through ITS OWN armour term**,
`strike_multiplier(attack_strength(rank), that foe's armour)`. That is why it does not reuse
`strike_adjacent`, which is Death Blossom's and calls `armour_ignoring_damage`: this page
says armor-respecting and that one's measured wire is armour-ignoring, so the two are
different mechanics wearing the same word. Called from three places, which is what the
"regardless of whether the arrow hits" note costs: the landed hit, the blind miss and the
block. `[skill_effect.431]` gains `adjacent_damage = "scale"` and deliberately **no**
`damage_type` -- *"Unlike Kindle Arrows, the damage type of the arrows is not converted to
fire"*, so the arrow keeps the weapon's kind and only the explosion is fire, while the
projectile is still substituted to the record's own 735.
`--no-preparation-splash` reverts.

**On the client** (`20260918T214133`, the bow under Ignite Arrows at three hostiles clustered
90 u apart, the middle one targeted): every launch flies as **735**; the target takes the
arrow's word, then impact **734** and the preparation's own word; then impact 734 and a word
on agent **11** and on agent **12**, both named as the splash, twice over two volleys. No
assert.

**Not modelled, named rather than guessed.** The page also says the explosion occurs
*"before the arrow itself hits"*, where W2e OBSERVED the arrow's word first and the
preparation's second, 6 of 6, on the only preparation retail has sent us. An observation
outranks an ordering claim, so the order here is W2e's and the page's is recorded, not
followed. Choking Gas (434) carries the same 156 radius and is a different effect
(interruption, not damage) -- untouched. Which element each `587` id names beyond fire = 5
is still unread.

## 20. WEAPONS-W2f — shipped 2026-09-18: the body side of W2d and W2e; and Q16 measured, still open

**W2f closes two body gaps W2d and W2e left named.** `body_ranged(agent, state, agent_id)`
now reads the body's own open preparation, so a hostile ranger under Kindle Arrows launches
343 / 0 / 5 exactly as retail's do (`20260817T231139`: 343 / 0 / 5 on every arrow of the
16 shots by bow bodies under a preparation there). `body_preparation_word` lands the
preparation's own second word after the arrow's, with the impact visual, through
`land_swing` (its target the player or a body). `land_swing` gains a `mult`, so a body's
Dual Shot lands each arrow at 75 % of the weapon's number — W2d had noted the body case
landed at the full number. On the client (`20260918T180529`, a hostile bow ranger under a
scripted preparation) the arrivals carry kind 5, the impact and the two words; no assert.

**WEAPONS-Q16, measured and still open: retail's client stops to shoot; ours walks in.**
The harness CAN drive the client's own attack order — `Escape`, `Tab`, `Space` produce a
real `0x0026` (`20260918T184537`, `185402`, `190124`) where the `attack:` mailbox does
not. So Q16 was measurable after all, and what it shows is a movement gap, not a weapon
one. Retail's body, after the approach, keeps shooting from a LARGE distance that shrinks
only slightly (`20260807T143055`: two shots 2044 → 1327 u; `20260810T235916`: 1066 → 601 u)
— it stops near where the follow ended and fires. **Ours walks all the way in**: run L's
successive flights are 1163 → 451 → 67 → 67 u — the body closes to the melee disc over
three shots and stays. The cause is the client's own resolver: given a `0x002A` follow that
names a target (which W2b's server sends, correctly, to the target's own position), the
client walks it to the melee disc `r + r + 56` regardless of the weapon, and nothing in our
start batch stops it there. Two arms were tried against the live client and BOTH failed to
stop it, so both were withdrawn:
  * the walk-gate hold (`[8, me, 1]` at the start) froze the draw animation while the
    follow kept translating — the owner watching `185402` saw "a weird sliding movement
    when the attack animation starts instead of stopping to shoot";
  * a bare `0x0028 [me]` at the start (retail carries one on 6 of 6 first-after-follow
    ranged starts) removed the slide but did NOT clear the stored follow — the body walked
    in with a normal run animation, 1163 → 67 u again (`190124`).
So the stop retail's client obeys is not the hold and not the `0x0028`: it must be a message
that CLEARS the stored follow (`agent+0x98`) at range — a `0x0029` heading or a `0x002C`
placement, per the movement arc's own decode ("a `0x0029` after a `0x002A` clears the
follow", approach_tick's docstring). Reproducing it needs the follow re-issued to the
RANGE point rather than the target, or a clear at arrival, and scored against retail's own
successive flights — the MOVECODE arc's instruments, not this one's. Left OPEN, with the
gap and the two dead ends recorded rather than a third guess shipped. W2b's server half
(the server's own copy stops at range) stands and is unaffected.

## 21. WEAPONS-Q16, the desk check — 2026-09-18: the server-side arms are EXHAUSTED, two rival mechanisms are refuted, and the `0x0028` gets a positive control

The plan's next action for Q16 was a desk check before a third client arm. It ran, it
shipped nothing, and what it bought is four results — three of them negative, which is the
point of running it rather than guessing again.

**(a) The two arms TOGETHER also fail. OBSERVED, on the live client.** §20 withdrew the
walk-gate hold and the bare `0x0028` after each failed alone. The remaining possibility was
that retail's start batch needs BOTH — which is what it carries (§20's census: 7 of 7 clean
ranged first-after-follow starts carry the hold *and* the stop). Built behind
`--no-ranged-follow-stop`, driven by the client's OWN `0x0026` (`--actions "0:play
40:vk:0x1B 42:vk:0x09 44:vk:0x20"`), against a **frozen** practice target 1,800 u out
(harness `20260918T201027`, recorder `authsrv-20260918T201057-c1`): the start batch went out
as retail's — `0x00A0 [4, 1, 10, 0]`, `0x009F [8, 1, 1]`, `0x0028 [1]` in that order at
129.847 — **and the body walked in exactly as before.** Successive flights **0.727 → 0.282 →
0.050 → 0.050 s**, against a target that never moved and an aim point fixed at
`(11099, 6804)`, so the flight is a faithful monotone proxy for the shooter's distance here:
the body closed to the melee disc over three shots and held. **All three server-side arms
are now spent** — hold alone (`20260918T185402`), stop alone (`20260918T190124`), both
(`20260918T201027`) — and not one of them stops the client walking a stored `0x002A`.
WITHDRAWN with the other two; nothing from this arm is on `main`.

**(b) REFUTED: the client is not missing a range word on our bow.** The rival worth
checking before touching movement was that retail's client stops at range because retail's
bow *item record* carries a reach our items omit. It does not, and the decode was already
in the repo: an item's modifier words carry the **damage** range (`584 (max, min)`, `634`
for a weapon with a requirement — WEAPONS-C7) and the damage TYPE (`587`), and no
identifier in [studies/itemmods](../itemmods/FINDINGS.md)'s 157-slot dispatch is an attack
REACH. Decoded side by side, retail's bows and ours carry the same families and nothing
else: retail `20260807T143055` item 469 = `609 / 587 / 617 / 584`, `20260914T005758` items
161 and 164 = `587 / 617 / 586 / 588`; our `starter_bow` = `609 / 587 / 584`,
`hostile_bow` = `609 / 587 / 584`. What names the weapon to the client is the item's TYPE
byte (wire field 3, the builder's `+0x20`), and ours already sends 5 for a bow. **There is
no missing word to add.**

**(c) REFUTED: the follow's destination is not the difference.** The other rival was that
retail aims the follow at a point short of the target. It aims at the target, exactly as
W2b already does: `20260810T235916` sends `0x002A [31, (5670, -4379), 0, 0, 43]` at 91.955
and again at 93.500 — the target agent 43's own position, the target in field 5 — and
`20260914T005758` 221.581 the same shape at agent 26. **So re-aiming our follow at a range
point would DIVERGE from retail's wire, not match it**, and is refused on those grounds
rather than left as an untried idea.

**(d) ★ THE POSITIVE CONTROL, and the sharpest thing this check found: retail's `0x0028`
DOES halt a walk — a KEYBOARD walk — and the body then holds its distance and shoots.**
On `20260914T005758` the observer is walking under its own steering (a `0x003D` report every
~0.5 s, each answered by a `0x0029` heading), presses attack at **508.731**, and the server
answers with a bare **`0x0028` at 508.767** and nothing else. The body then shoots **three
times from one distance** — launches at 513.233 / 515.725 / 518.700 with flights **0.210 /
0.215 / 0.215**, flat — while the target sits still. So the stop is **not inert**: the
client's handler ends a walk it is steering itself. What it demonstrably cannot do is end a
**stored follow**, which is what our case is. That is a control §20 did not have, and it
converts "the `0x0028` does nothing" into the much narrower and more useful **"the `0x0028`
halts a self-steered walk and leaves `agent+0x98` alone"** — consistent with the movement
arc's decode that `0x0029` hardcodes `+0x98 = 0` and `0x002A` supplies it
([studies/movecode](../movecode/FINDINGS.md) §2.2, 1z-al).

**Where that leaves Q16, stated as narrowly as the evidence allows.** The wire our server
sends around a ranged press is now byte-for-byte retail's — the follow, its destination,
its followed-agent field, and the start batch's hold and stop. The client nevertheless
walks ours to the disc. So the stopping distance is decided **inside the client's follow
resolver**, from state the wire does not carry, and the next step is to read that resolver
rather than to send it another message: `codescan` for what the resolver compares the
remaining distance against, with `r + r + 56` (1z-al's measured melee park) as the known
value and the weapon's reach as the thing to find beside it. **That is a MOVECODE rung, not
a weapons one**, and Q16 stays open there. Neither a fourth message nor a re-aimed follow
should be tried before that read.

**That read is done -- section 22, the same day. It closes Q16's mechanism: the threshold has
no weapon term, so the answer is that NOTHING parks a client at range on a follow.**

## 22. WEAPONS-Q16 -- CLOSED at the mechanism, 2026-09-18: the client's follow-park threshold has NO weapon term, and only `0x0029` can end a follow

Section 21 left Q16 with the server-side arms spent and named the next step: read the
resolver rather than send it a fourth message. That read is done, on the pinned pristine
client (build 38797), and it answers the question outright.

### 22.1 The threshold, decoded -- `0x005FED20`, three returns and not a weapon among them

The park arm inside the avoidance solver (`0x006011F0`) compares a squared distance against
a value returned by `call 0x005FED20` (`0x006017AB`), and parks when the distance is inside
it. The local the distance lives in is `[ebp-0x84]`, computed at `0x006015C7..0x00601611` as
`dx*dx + dy*dy` from the two agents' `+0xB0`/`+0xB4` -- a **squared** separation, which is
why the callee returns a **squared** threshold. `0x005FED20` is short enough to read whole:

| gate | return |
|---|---|
| `[ecx+0x1C] != [edx+0x1C]` (`0x005FEDAB`) | `(a.+0xD0 + b.+0xD0)^2` |
| same `+0x1C`, and **either agent's `+0x98` names the other** (`0x005FED41`, `0x005FED4C`) -> `0x005FED82` | `(a.+0xD0 + b.+0xD0 + TABLE[+0x1C])^2` |
| same `+0x1C`, same nonzero `+0xE8`, **neither follows the other** (`0x005FED65`) | `(2 * f(a.+0xEC, b.+0xEC))^2` |

`TABLE` is `arg0[+0x1C * 3 * 4 + 0x20]` (`0x005FED91 lea ecx,[esi+esi*2]`,
`0x005FED95 fadd [eax+ecx*4+0x20]`), a per-kind spacing row off the world context.
**That middle row is `r + r + 56`** -- the rule 1z-al measured from the outside, now read
from the inside, and **it is selected PRECISELY BECAUSE `+0x98` names the other agent.**

> **OBSERVED. The whole function's inputs are `+0x1C`, `+0xE8`, `+0x98`, `+0x10`, `+0xD0`
> and `+0xEC`. There is no weapon, no item, no reach and no range anywhere in it.** A
> `0x002A` attack-follow therefore parks a body at the melee disc **whatever it is holding**
> -- a bow, a wand and a sword are the same to this code. The client cannot stop at a
> weapon's range on a follow, because it has no notion of a weapon's range here.

**`+0xD0` is the collision radius, and this closes MOVECODE's registered-not-started item**
("read the agents' collision radii from the client -- the `r + r + 56` rule is already
decoded; the radius field is not", 1z-dd.6). `--field 0xD0 --in AgAgent`: **8 reads, 0
stores**, every one an `fld`/`fadd` of a float, four of them the two sums above. The name is
a RECONSTRUCTION from its role; the OBSERVED fact is the arithmetic.

### 22.2 Why all three of our arms failed, from the handlers rather than from the runs

* **`0x0028`'s handler `0x005FD7D0`** resolves both world copies and calls the halt
  `0x00602540` on each, then `0x00603990` on `+0x94`. **It never writes `+0x98`.** So a stop
  halts the body and leaves the follow intact, and the movement update it re-runs re-drives
  the body along it. That is the hold arm, the stop arm and both-together, explained without
  reference to any of the three runs.
* **`0x0029`'s handler `0x005FD890`** bounds-checks the point (`0x005FCEC0`), builds it on
  the stack, and **pushes a literal `0` (`0x005FD906`) into the shared setter's followed-agent
  slot.** It is the only message that clears `+0x98`, confirming 1z-al.2 from the other side.

**So the fourth message was never going to exist.** No amount of `0x0028` ends a follow;
only a `0x0029` does, and a `0x0029` is a *move order*, not a stop.

### 22.3 What retail does with that, and the correction it forces on section 21

Census over the whole live corpus -- every `0x002A` naming a target on the observer, and what
reaches the observer before its next swing start (`q16_followend`):

| what ends the observer's attack-follow | n |
|---|---|
| nothing | 131 |
| a `0x0029` | 106 |
| a `0x0028` only | 69 |
| **total** | **306** |

The 106 look at first like retail parking the shooter, and they are not: read the rows and
essentially all of them are a `0x0025` + `0x0029` pair answering the player's **own** `0x003D`
report -- the owner took the controls, and clearing the follow is a *side effect* of steering.
**Retail never sends a `0x0029` to park a ranged attacker at its range.**

**And section 21's (a) must be re-read, because the instrument was not what it looked like.**
Our runs' flight times are computed by `launch_player_projectile` from `_reach_frame` -- the
server's **dead-reckoned mirror of the CLIENT's body**, which models what the client will do
with the wire we sent. The wire is a follow to the target (W2b deliberately left it so), so
the mirror walks to the melee disc, and `0.727 -> 0.282 -> 0.050` at the bow's 1600 u/s is
`1163 -> 451 -> 80 u`. **80 u is `r + r + 56` exactly.** The flights were never an independent
measurement of the client; they are our server correctly predicting the client obeying
22.1. The three arms' failure stands (the client walks in), but the number that showed it is
the mirror's, and it agrees with the binary rather than corroborating it separately.

### 22.4 The verdict, and the one thing that is now the owner's

**Q16's premise is refuted.** It asked what parks retail's client at range on an attack-follow.
Nothing does: given a follow that runs to completion, every client walks to the melee disc
regardless of weapon, retail's and ours alike, and the cases that looked like retail holding
at range are presses made from **inside** range by a player who had walked itself there under
its own steering (§21d's positive control is one: a press at 508.731 answered by a bare stop,
no follow involved, then three shots from one distance).

What is left is not a bug but **a divergence W2b created and a choice about it.** W2b stops
the SERVER's copy at the weapon's range while the wire keeps the client walking to the disc,
so the two disagree about where the body stands. Two ways to end that, and it is the
operator's call because they trade different things:

1. **Revert W2b's server stop** -- the server walks with the client to the disc. Fully
   faithful to retail's wire and to the client's own code, and a ranged press from out of
   range closes to melee, which is what retail does.
2. **Send a `0x0029` at the body's own point when the approach reaches range** -- the one
   message that clears `+0x98` (22.2), so the client parks where the server already thinks
   it is. It makes server and client agree and gives the behaviour a bow player expects,
   **at the cost of a message retail does not send here** (0 of 306 follows).

Recorded, not chosen: (1) is the faithful one and (2) is the one that looks right, and this
repo's rule is faithfulness, so **(1) is the default unless the owner asks for (2)**. Nothing
is shipped either way; W2b's server half stays as it is until that is answered.

> **RETRACTED THE SAME DAY -- section 23.** The operator answered "faithfulness", both
> options were built or costed, and **both are wrong**: (1) loses the range opening retail
> demonstrably has, and (2) sends a message retail never sends. **There is no choice here and
> the shipped arm is already the faithful one.** Read section 23 instead of this list.

## 23. WEAPONS-W2g, TRIED AND WITHDRAWN -- and section 22.4's "owner choice" RETRACTED: what we have is faithful

Section 22.4 offered the operator two ways to end a divergence it said W2b had created, and
the operator answered: **faithfulness.** Acting on that turned both options over and found
the section was wrong. **Neither was right, there is no choice to make, and the shipped arm
is already the faithful one.** Recorded in full because the wrong framing is on `main` above
this, and because the negative it produced is worth more than the change would have been.

### 23.1 What was built, and what the client did with it

22.1 proved the client's park threshold has no weapon term, so a followed body always stops
at the melee disc. `_approach_send`'s own comment (MOVECODE 1z-dm) says "the leg ends where
the client's own resolver will stop the body", and since W2b that was no longer true for a
bow -- the leg ended at the weapon's RANGE. W2g split the two: `approach_leg_stop()` (the
disc, where the body goes) beside `approach_stop()` (the range, where the swing opens), with
`--ranged-leg-at-range` reverting. It tested clean at 115 checks and read correctly.

**On the client it was a plain regression** (`20260918T205234`, then `20260918T205759` after
a second fix), against `20260918T201057` on the shipped arm:

| arm | first swing after the press | flight of each arrow |
|---|---|---|
| shipped (W2b) | **1.17 s** | 0.727 -> 0.282 -> 0.050 s (1163 -> 80 u) |
| W2g, leg at the disc | 6.03 s | 0.050 s throughout (80 u) |

That 6 s is precisely the pre-W2b shape W2b exists to fix -- the body walks to melee and
only then shoots. A second cut moved the approach's **eta** to the gate as well, on the
theory that the eta was what ended the approach; it changed nothing (`20260918T205759`,
first swing still 6.03 s), which is what sent the search to the right place.

### 23.2 ★ WHY, and this is the thing worth keeping: the LEG'S END is what the reach gate reads

The swing does not open when the approach ends. It opens at `attack_tick`'s reach gate,
`math.hypot(agent - _reach_frame(state)) > attack_reach()`, and **`_reach_frame` does not
track the body continuously during a follow.** Its report arm is skipped while the click
latch is set, and the AgTrack mirror gives it nothing here, so it falls through to
`state["pos"]` -- which the run's own telemetry shows barely moves: the leg row for
`20260918T205759` reports `model_moved: 36.0` over the whole 6 s walk, and the swing opens
at `134.70` against the leg's halt at `134.72`.

> **So the leg's END is the event that tells this server the body may shoot.** W2b's leg at
> the weapon's range is not an incidental conflation -- it is the mechanism by which the
> swing opens at range at all. Move the leg to the disc and the gate cannot fire until the
> body reaches the disc, which is exactly what both runs show. OBSERVED.

### 23.3 The verdict, and the retraction

**What we have is faithful, on both things that are observable:**

* **The wire is retail's**, bit for bit -- one `0x002A` at the target's own position with the
  target in field 5 (22.3 and W2b's own check).
* **The swing opens at the weapon's range, which is what retail does.** Over the corpus the
  first launch after a follow reaches **1,284 u on a 1,273 u recurve** (`20260914T005758`
  584.263, flight 0.459 at 2,800 u/s, cross-checked against the aim point and the player's
  own report at 1,283 u); ours opens at 1,498 u and put its first arrow at 1,163 u. The
  flight-as-distance model is validated on that corpus to within about 10 u
  (1208/1207, 1007/1006, 338/338, 1284/1283, 230/230).
* **The body finishing at the melee disc is the client's own arithmetic** (22.1), so retail's
  client does it too. It is not ours to fix and not a defect.

**Retracted: 22.4's two options were both wrong.** Option 1 (revert W2b's server stop) would
have put the swing gate back at the disc and lost the range opening retail demonstrably has.
Option 2 (send a `0x0029` at range) would have added a message retail sends 0 of 306 times.
There is nothing for the operator to choose.

**What is left is one internal inaccuracy, and it is NOT a faithfulness question.**
`state["pos"]` parks at the range point while the client's body walks on to the disc, and no
report corrects it (the client sends none while it walks a follow). It is invisible on the
wire and the swing gate depends on it being exactly where it is. Ending it means giving the
server a body position that tracks the client continuously through a follow instead of one
that jumps at leg ends -- **a MOVECODE change to `_reach_frame`'s sourcing, with W2g's split
waiting behind it**, not a weapons rung. Registered here, not started, and nothing ships
until it is.



## 25. RUN-WEAPONS-1A -- run and scored 2026-09-19: the martial clocks, the scythe's extras and the spear

Capture `20260919T103604`, Isle of the Nameless (map 280), plan `weapons_1a.txt` sealed
and `plan_seals = agree`, exe unchanged across the run, 4 of 4 connections decrypted.
Tools: `weaponcensus.py --capture 20260919T103604 --shooters --attackers`,
`timingjoin.py --capture 20260919T103604 --swings`, and scratch scripts over
`livewire.decode_conn` for the per-swing geometry; every number below re-derives from
the tape.

The observer is agent 25. Its four weapon sets, from its own `0x0147` at the map load:
set 0 axe (item 212, type 2, 6-28 slashing, requirement Axe Mastery 9), set 1 scythe
(209, type 35, 9-41 slashing, Scythe Mastery 9), set 2 spear (210, type 36, 14-27
piercing, Spear Mastery 9), set 3 spear (208) + shield (207, type 24, armour 16,
Tactics 9). Bodies: the Master of Damage, agent 70 at (-2000, 3233), 590 max health;
his suits 71 at (-2073, 3261) and 72 at (-1954, 3315), definition 1067 both, 480 max
health, never moving; the Master of Healing 67, 480 max health, a wanderer that stood
still through its block. Every damage word on the tape is a whole number of points over
the target's max health (SLICE: whole points, truncated) -- agent 70's words are k/590,
the others' k/480.

Operator notes, as given: PvP equipment made for the run, no mods or inscriptions; the
single-target scythe block was done on the Master of Healing because no single-target
angle existed at the Master of Damage; only two bodies could ever be hit there; before
the spear blocks the operator paused attacking, swapped sets, walked out beyond range
and pressed attack once so the character walked itself into range; and in the
multi-target block the operator moved all around looking for a three-target angle,
some swings hitting one body, none hitting three.

### 25.1 Exposure, per block

| block | starts | landed | extras | criticals | start->start p50 | start->word / launch p50 |
|---|---|---|---|---|---|---|
| 1 axe, one suit (70) | 20 | 20 | -- | 0 | 1.330 | word 0.566 |
| 2 scythe, one body (67) | 22 | 22 | 0 | 0 | 1.500 | word 0.650 |
| 3 scythe, two suits beside 70 | 40 | 33 | 29 | 1 | 1.500 between moves | word 0.650 |
| 4 spear, no off-hand (70) | 24 | 24 | -- | 0 | 1.500 | launch 0.636 (see below), word 1.114 |
| 5 spear + shield (70) | 30 | 30 | -- | 2 | 1.500 | launch 0.650, word 1.125 |
| 6 axe again (70) | 11 | 10 | -- | 0 | 1.330 | word 0.565 |

Every floor met (>= 15 landed per block). 147 starts, 139 landed swings, 29 extra words,
**0 fail words** (property 38 never appears -- nothing was blocked, dodged or missed all
run), 168 words in all, 54 launches each closed by its `0x00A7`. The 8 starts without a
word are swings cut by the operator moving or re-targeting (7 in block 3) and the last
start of block 6, cut by the end.

The wire-timestamp bar these instants inherit (`test_tickclock.py`'s convention): the
Isle connection's tick residual closes at -2.3 ms over 404 s with a 301 ms envelope at
one point (160 s, during the walk to the suits) -- below every p50 quoted here by an
order of magnitude. The outpost connection of the same capture is the corpus's third
step connection (one 2.58 s stall, +75.9 ms after it); no clock was read there.

Block 4's launch delay alternates 0.635 / 0.651 while its start->start alternates
1.515 / 1.486: the launches sit on an exact 1.500 s grid (492.385, 493.885, 495.385, ...)
and the wobble is in the start message's wire time, not in the windup. Block 5's starts
sit on the grid and read 0.650.

**The one floor that was mis-specified: "a `0x0035` for each equip".** Retail sent three
for five equips -- 1.33 at the first axe swing, 1.50 at the first scythe swing, 1.33 at
the axe's return -- and NONE at the scythe->spear change (1.50 -> 1.50) or at the
spear->spear+shield change. Across the 29-capture corpus every attacker with a constant
weapon carries exactly one `0x0035` however many swings it makes, and the one body with
19 (agent 30 on `20260914T005758`) alternates its modifier 1.00 / 0.67 over a constant
base. OBSERVED: **`0x0035` is sent at a swing start when the (base, modifier) pair
differs from the last one sent, and not otherwise.** Our server should send it on
change; a per-swing send is a visible divergence.

### 25.2 WEAPONS-Q6, the spear -- ANSWERED

Duration **1.500 s** start->start (n 24 + 30, p50 1.500 in both blocks). Launch at the
windup, **0.650 s** after the start (block 5 p50 0.6503; block 4's 0.636 is the
artefact above). `0x00A4` field 5 (projectile) = **143** on all 54 -- the spear items
carry NO 617 word, so 143 is the type's default rather than an item word, and it is the
same 143 a bow without a 617 word fires (`test_weaponcensus.py` pins that: 24 of 26).
Field 7 (the arrow flag) = **1** on all 54, as predicted. `0x00A7` kind = **1**, the
spear's 587 (piercing) -- WEAPONS-C9 holds for a spear. Flight 0.4705-0.4761 s over
750-759 u from the client's own stop position: **1594 u/s**, one number to the unit
across all 54 (distance against flight correlates at 1.000 with a 0.5 ms intercept) --
the 1600 u/s class, the 6 u/s shortfall being the client's report of its own stop
against the server's body. Launch + flight lands the word to 4.3 ms p50. **The shield
changes nothing:** clock, windup, projectile, flag, kind and flight are identical with
and without it; the census's two spear rows differ only by the spear's item id. The
launch's aim point is not the target's centre: all 54 lie exactly 4.5 u from
(-2000, 3233) at varying angles -- a point on a 4.5 u circle about it.

### 25.3 WEAPONS-Q5, the scythe -- ANSWERED, with one term measured against the wiki

Duration **1.500 s** (block 2: 22 gaps, 1.496-1.503); word at **0.650** (p50 0.6495).
`0x0035` base 1.50 at the first swing.

**How extras appear on the wire.** An extra is a second damage word in the SAME instant
as the target's -- the same wire time to the millisecond on all 29 -- and it is written
BEFORE the target's word, 29 of 29. Extras are their own hits: each rolls its own damage
(the pairs 71 = 5 / 70 = 2 and 71 = 2 / 70 = 5 both occur, so it is not one roll scaled
twice) and its own critical (the block's one critical, at 431.023, is on the extra 71
while the target 70 took a plain 3). No separate swing, no `0x009F`, nothing else.

**Who is an extra.** The operator's reading is exact: 29 swings hit two bodies, 4 hit
one, 7 hit nothing (moving), none hit three. Per-swing geometry from the client's own
position reports (`0x0047` / `0x003D`) against the suits' fixed positions:

* **the attacker term, ~180 u, CONFIRMED at its edge.** Suit 71 (78 u from the target)
  is hit at 181 and 182 u from the player and missed at 186 u -- two hits and two misses
  bracket the wiki's 180 to the precision of the position reports, a few units.
* **the target term is NOT "adjacent".** Suit 72 stands 94 u from the target's centre
  and was never hit: in 17 swings it was inside 180 u of the player (at 55, 63, 70, 73,
  74, 78, 79, 84 u ...), at 4, 7, 11, 21 and 27 degrees off the line to the target as well
  as at 50-100, while 71 at 78 u from the target was hit in every one of those swings.
  Nothing but the distance to the target separates the two suits: same definition, same
  health, same plane, same allegiance (72 was hit directly when targeted at 427.4). So the
  target-side term lies in **[78, 94) u centre-to-centre** for these bodies. The wiki's
  "in melee range of the target" is consistent only if melee range means a disc of that
  order -- our own melee disc is 80 u -- and not the 166 u "adjacent" band. An arc rule
  is refuted outright (72 at 21 degrees and 165 u from the player, missed; 71 at 66
  degrees, hit). Height was not measured; the three suits share plane 0.
* **the cap is untested**, as the runsheet said it would be: with 72 excluded by
  geometry there were never three candidates. To test it the two extras must BOTH stand
  within ~80 u of the target.

**The critical's size.** One scythe critical, and it is enough for one bound: 6 points on
suit 71, whose plain hits in the same block top out at 5 points, four times over. A
plain 5 means 41 x f >= 5 (no roll exceeds 41), so a x2^0.5 critical on the maximum
roll would read >= 7.07, i.e. 7 or more points; a x1 critical would read at most 5. The
observed 6 gives **1.0 < c < 1.40**: the ordinary x2^0.5 (1.414) is refuted by a hair and
the x2^0.125 (1.091) the wiki gives scythes is consistent (it predicts 6 whenever
41 x f >= 5.50). Premises, stated: a critical is the maximum roll times c (GWW "Critical
hit"), truncation to whole points (SLICE), and one armour factor f for every hit on 71 in
the block (all are extras by the same weapon at unchanged attributes). One sample; RUN-3's
met-requirement scythe block will multiply it. The spear's two criticals (5 points
against a plain ceiling of 4 on agent 70) fit x1.09 and x1.41 alike and decide nothing.

Critical rates, for what a low rank gives: scythe 1 of 84 hits, spear 2 of 54, axe 0 of
30. The PvP character's ranks were not set for the run -- the words are 1-5 points on
9-41 and 14-27 weapons -- so these are the unmet-requirement floor, not the table
section 17 interpolates.

### 25.4 The walk-in -- a first data point for Q4 / Q16, and a warning about how RUN-2 reads

The spear's approach is on the tape as section 14 said retail's is: c2s `0x0026 [70, 0]`
at 490.184 from ~1,330 u out, the server's `0x002A` follow carrying the target's own
position at 490.235, no movement message after it except an s2c `0x0028 [25]` at 489.849
and again in the start's own instant (section 22: that handler writes no destination
and parks nothing), and the swing start at 491.744 with the body parked at
(-1949.85, 2480.04) by the client's own report (`0x0047`, unchanged from 527.6 to
590.0) -- **754.6 u from the target's centre, 751.5 u from the first aim point.** The
spear + shield block was pressed from the same spot at 541.586 and fired 53 ms later.

That number is the instrument RUN-2 relies on, and it does not read the way the runsheet
assumed. WIKI says 1004 for a spear; the client parked at **755 = 0.75 x 1004 to within
2 u**, and also 1004 - 250. Either the spear's range is ~755 and the wiki is wrong, or
retail's client parks INSIDE its range by a margin -- in which case "distance at the
first launch" measures the park and not the range for every weapon in RUN-2. The two
margins separate on the bows: multiplicative puts the longbow's park at 1,123 and the
shortbow's at 753, additive at 1,248 and 754. And the Isle offers a free discriminator
that RUN-2 should take in one press: its range-marker bodies stand at a bow's maximum
range from a marked firing spot (`agentroster.py`'s reason to exist). Stand on the mark,
press attack on the Short Bow Target with the shortbow: a shot with no walk says park =
range; a walk of ~250 u first says the margin is real and measures it. Until then this
tape says the spear's range is >= 755 u and its park is 755 u, and Q4's spear row stays
open.

### 25.5 The wire around the run -- the operator's note 1 answered, and a census defect fixed

**The weapon-set switch, first time on any tape.** c2s **`0x0032 [byte set]`** appears in
no other capture of the 29 (corpus census, this run's scratch). Its answer, one batch
40-50 ms later: `0x0148 [1, set]` (the active set), `0x0152 [1, old item, new item]` for
a hand whose item changed, `0x014B [1, item, 136, slot]` when a shield enters or leaves a
set, and **`0x006F [agent, hand, item]`** per hand that changed -- hand 0 lead, 1 off, an
item of 0 for an emptied off-hand. **No fresh `0x006E`**: the player's `0x006E` is sent
once at the create and never again. Before each swap the operator's "stop attacking" is
c2s `0x0028 []`, 4 of 4.

That last fact was a defect in `weaponcensus.py`: its hands timeline read `0x006D` /
`0x006E` only, so every swing of this four-weapon session was filed under the axe, the
spear's `0x00A7` was scored a MISMATCH against the axe's 587, and the SPEEDS table joined
1.50 to type 2. Fixed this run: the timeline now folds `0x006F` slots 0 and 1 (2-7 are
armour; 12 hand-slot messages in the corpus, 6 of them this tape, 1 on a body with no
prior `0x006E`, which starts from empty hands). After the fix the tape reads type 2 at
1.330 x29, type 35 at 1.500 x46, type 36 at 1.500 x52 across two spear items,
`kind == 587` 2 of 2, and `test_weaponcensus.py` is green at 38 checks with no pin moved.

**PvP equipment, in the outpost connection (map 248).** c2s `0x0085 [241]` opens the
panel and is answered by `0x015C [241, seven 7-field rows]`; each creation is c2s
**`0x0086 [241, kind, [mods], 9, flag, 0]`** -- kinds 110, 322, 325, 146, 325 in the
order made, the mods array EMPTY because none were chosen, 9 the requirement's rank,
flag 1 on the one that is an off-hand -- answered by `0x015D [new item id, displaced
item id or 0]`. These four opcodes also appear on `20260917T160915` (the daggers tape),
so they are not first sightings; the empty mods array is. Mapping kind -> weapon is by
creation order only (110 first; the axe was set 0) and stays UNVERIFIED until a tape
makes one weapon at a time; the weapon sets' truth is the map-load `0x0147` above.

**Modifier 585 = 120, a candidate for Q12.** All three created weapons and no NPC's
item carry the word (585, 120, 0). Every PvP-panel item is customised to its maker
(WIKI, "PvP equipment"), and customisation is +20 % damage. RECONSTRUCTION, unverified:
585 is the customisation word and 120 its percentage. If it holds, the x1.2 is inside
every number the isle study took with PvP weapons, and Q12's desk half is answered by
grepping that study's item words for 585. Not pinned; nothing reads it.

**Also on the tape, unread:** s2c `0x008C [140, 21|22, 23..25, 1]` eight times through
the melee blocks; the player's Windborne Speed (`0x0042` skill 160, `0x0027` at 383.04 =
288 x 1.33) applied four times, which is why the walk-in ran at 383 u/s.

### 25.6 What this run leaves open

* the scythe's cap (three candidates never existed) and the exact target-side term (a
  bracket of [78, 94) u from two suits; a third distance would narrow it);
* the critical's size to better than one sample -- RUN-3's scythe block;
* the spear's range against its park distance -- RUN-2's design, section 25.4;
* the meaning of `0x0086`'s kind numbers, of `0x008C`, and of modifier 585.

## 26. After RUN-1A, the owner-free rungs -- 2026-09-19: the spear throws, WEAPONS-W3 ships the scythe's extras and small critical, WEAPONS-W8 reads the customisation word, Q12 closes, W9 is registered

Everything below is what section 25's tape unlocked without another capture. Nothing
here touches the items that still wait for one (the scythe's cap, the critical to more
than one sample, the spear's range against its park).

### 26.1 The spear throws -- W2a's last row

`[weapon_type.spear]` gains `projectile = 143`, `arrow = 1`, `projectile_speed = 1600`
and `range = 1004`, each argued in the row: 143 and 1 are 54 of 54 on the tape; 1600 is
the class the corpus measured with error-cancelling geometry, taken over the tape's
1594 because a ~3 u offset between the client's report of its own stop and the
server's body is the whole gap; 1004 is WIKI's, because the tape says only >= 755
(section 25.4). `weapon_ranged()` needed nothing else -- the row was the gate -- so the
press now opens from 1004 u, the windup releases a `0x00A4 [143, handle, 1]`, and the
`0x00A7` closes it with kind 1. `test_weapons.py` section 15 throws one from 755 u
through the real loop and reads the flight at 755 / 1600. The W2a comment that named
the spear as the type "whose projectile id is unmeasured" now says when that stopped.

### 26.2 WEAPONS-W3 -- the scythe's extra targets and its 2^0.125 critical

**Extras.** `scythe_extras(state, target, attacker_pos)` picks up to
`SCYTHE_EXTRA_MAX` = 2 living hostiles that stand inside `scythe_extra_reach()` of the
target AND `SCYTHE_EXTRA_ATTACKER_REACH` = 180 u of the attacker, nearest the target
first. `scythe_extra_reach()` is r + r + the client's def pad = **80 u** with our radii
-- the disc the follow parks on, read as the wiki's "in melee range of the target". That
is a RECONSTRUCTION placed inside the tape's OBSERVED bracket of [78, 94) (section
25.3), and the constant is a function rather than a literal so a narrower bracket
moves one line. `scythe_extra_hit()` gives each extra its own roll, its own critical,
its own armour term, its own `0x00CF` gain, its first-hit maximum and its word, and
`hit_enemy` runs them BEFORE the target's own gain and word -- retail's order, 29 of 29.
`--no-scythe-extras` reverts. Player-side only: a body's scythe extras are named in
the constants' comment and not built, and bodies roll no criticals here to begin with.
Also named, not modelled: a block or a blind miss on an extra.

**The critical.** `[weapon_type.scythe]` carries `critical_armour_reduction = 5`;
`weapon_critical_reduction(item)` reads it (20, the root-two term, for every row that
says nothing) and `swing_damage` takes it per call, so a scythe's critical is
2^(5/40) = x1.09 where every other weapon's is 2^(20/40) = x1.41. The mechanism is the
one combatmath already had -- a critical is the maximum roll against the target's
armour less a constant -- with the constant made the type's. Section 25.3's bound
(1.0 < c < 1.40 from one critical, no free parameter) is what admits 5 and refuses 20.

**Tests**, `test_weapons.py` section 16, nine checks: 78 u hit and 94 u missed with
both inside 180 of the player and the extra's word first; a gain ahead of each word;
179 u hit and 186 u missed at the attacker's edge; three candidates give two words, the
nearest to the target; a sword in the same geometry hits one body; the revert flag;
the two multipliers 1.091 and 1.414 on a maximum roll; and a forced critical's
scythe-to-sword ratio 2^(-15/40) through the primary hit.

### 26.3 WEAPONS-W8 -- the customisation word, and WEAPONS-Q12 CLOSED

A corpus scan for modifier 585 (this run's scratch, `weaponcensus.items_of` over the
29 live captures): **85 items carry it, every one at arg 120**, and all but one are the
owner's own weapons -- in an own weapon set or a player's `0x006E`; no hostile's item
has it. Among them is the isle study's sword (item 205 on the `20260821` tapes), and
[studies/isle/FINDINGS.md](../isle/FINDINGS.md) records that item's own tooltip as
*"Damage +20% ... customized"* and its damage fit as *"an integer roll over the
customized range 18..26"*. Two witnesses that do not share a source -- the client's
tooltip text as the operator read it, and the corpus distribution -- so **CORROBORATED:
585 is the customisation word and its arg the percentage.** Not OBSERVED from the
binary: `clientscan/itemmods.py` does not name the identifier.

**Q12's desk half is YES.** The isle's numbers were taken on a customised weapon, its
formula was fitted on the x1.2 range, and the study's own scope statement already says
"for a customized martial weapon". Any table that quotes the isle's damage numbers
quotes the customised ones. CLOSED.

**Shipped:** `combatmath.weapon_damage_range()` scales the range's two ends by
arg / 100, integer floor (15-22 with 585 = 120 reads 18-26, the isle's own fit), when an
item carries the word. No repo item does, so nothing the server deals changes today;
an operator's item row that carries it will. `test_weapons.py` section 17, three checks.

### 26.4 WEAPONS-W9 -- registered, not started: the weapon-set switch

Section 25.5 read the switch off the wire for the first time: c2s `0x0032 [set]`,
answered by `0x0148 [1, set]`, `0x0152 [1, old, new]` per changed hand, `0x014B` when a
shield enters or leaves a set, and `0x006F [agent, hand, item]` per hand -- never a
fresh `0x006E`. Our server fills weapon set 0 only and has no handler for `0x0032`.
There is nothing to switch to until the player's other sets hold items, which is a
content decision (the operator's own items, the mod-platform framing) ahead of a wire
rung. Registered so the shape is not re-derived; not costed.

### 26.5 Also checked, nothing to do

* `0x0035`: our server already declares the (base, modifier) pair on a CHANGE, at the
  next attack start (`ATTACK_SPEED_AT_START`, JARIN-S) -- the rule section 25.1
  confirmed on the corpus. A weapon swap that keeps the base sends nothing, as retail's
  scythe-to-spear swap sent nothing.
* The launch's aim point on a 4.5 u circle about the target's centre (section 25.2):
  recorded, not built. One tape, one static target; a second target with a different
  body would say whether 4.5 is a constant or a radius.

## 27. WEAPONS-W9 SHIPPED -- 2026-09-19: the weapon-set switch, read off the 1A tape and reproduced on the client

**What retail does, OBSERVED (`20260919T103604`, the explorable connection, agent 25; scratch
`aw_w9tape` over `livewire.decode_conn`).** At the map load every set's item is declared with
`0x0161` and MOVED (`0x013E [1, item, bag, slot]`): the inactive ones into the backpack (bag 2,
slots 0..6 in creation order -- 206 at 0, the shield 207 at 1, 208 at 2, 209 at 3, 210 at 4,
211 at 6), the active lead 212 into the equipped bag (bag 3) slot 0 beside the armour at 2/3/4;
then the four `0x0147 [1, set, lead, off]` rows name the sets (212, 0), (209, 0), (210, 0),
(208, 207). `0x0148 [1, 0]` precedes the creates. The switch is c2s **`0x0032 [set]`**, and its
reply is ONE batch 40-46 ms later, 4 of 4, a DIFF of the hands:

| press | reply, in order |
|---|---|
| `[1]` axe 212 -> scythe 209 | `0x0148 [1, 1]`, `0x0152 [1, 212, 209]`, `0x006F [25, 0, 209]` |
| `[2]` scythe -> spear 210 | `0x0148 [1, 2]`, `0x0152 [1, 209, 210]`, `0x006F [25, 0, 210]` |
| `[3]` spear -> spear 208 + shield 207 | `0x0148 [1, 3]`, `0x014B [1, 207, 3, 1]`, `0x0152 [1, 210, 208]`, `0x006F [25, 0, 208]`, `0x006F [25, 1, 207]` |
| `[0]` spear + shield -> axe 212 | `0x0148 [1, 0]`, `0x014B [1, 207, 2, 1]`, `0x0152 [1, 208, 212]`, `0x006F [25, 1, 0]`, `0x006F [25, 0, 212]` |

So: the active set first; a shield ENTERING the hands is a `0x014B ITEM_CHANGE_LOCATION` into
the equipped bag's slot 1, a shield LEAVING is one back to the backpack slot it was CREATED in;
`0x0152` carries the lead LEAVING and the lead ENTERING (named `ITEM_SWAP_EQUIPPED` in
`schema/overrides.json`, medium: the client-side effect is unread); and `0x006F` writes one hand
each -- an EMPTIED off hand first, then the lead, then a FILLED off hand. No `0x013E` for either
lead, no fresh `0x006E`, no `0x006D`. In the PvP-equipment outpost (map 248) the same press is
answered by `0x0148 [241, set]` plus `0x014B [241, item, 136, slot]` per made weapon and no
`0x0152` / `0x006F` -- the sets were being FILLED from the panel there, not swapped; the first
field is the instance's inventory key (116 / 241 / 1), which our wire has always sent as 1.

**What ships.** `--weapon-set N=ITEM[+OFFHAND]` (repeatable, N in 1..3; a party row's
`player_weapon_sets = [[N, ITEM, OFFHAND], ...]` goes through the same `configure_weapon_sets`)
fills sets 1-3 with content items -- validated at launch as `--player-weapon` is (a hostile-only
type refused, a two-handed lead's off hand dropped). Item ids 11/12, 13/14, 15/16 for the three
sets' (lead, off), clear of the player's 1-10 and the hero bodies' 210+. `declare_weapon_sets`
at the create: each inactive item `0x0161` then `0x013E` into the backpack (bag 2) at slots in
declaration order, before the `0x0147` rows, which now name every set's items
(`weapon_set_items`). The dispatch arm for `GAME_CMSG_SELECT_WEAPON_SET = 0x0032` calls
`select_weapon_set`, which sends retail's batch above with our ids and then re-aims the server's
own hands through `apply_party_character` -- the swing range, the interval, the off hand's
armour and the attribute follow, and the `0x0035` pair goes out at the next attack start if the
base moved (section 26.5's rule). Two additions retail's tape could not show: (1) set 0's shield
(item 10) is given a backpack slot so it has somewhere to go when set 0 leaves the hands --
RECONSTRUCTION, retail's 207 went back to the slot it was created in and ours is created in the
equipped bag; (2) a set whose 556 energy word differs re-declares the maximum (property 41) and
the rescaled regeneration (43), the morale path's shape -- INFERRED: retail's 1A weapons carried
no 556 (PvP-made, empty mods) so no switch on any tape moved a maximum, and our `starter_scythe`
/ `starter_spear` rows (retail NPC items) carry +5. A same-set press and an empty set send
nothing, NOT OBSERVED either way (the log names both).

**On the client, OBSERVED (harness `20260919T152451`, then `20260919T153354` with the energy
words; `--player-weapon starter_axe --weapon-set 1=starter_scythe --weapon-set 2=starter_spear
--weapon-set 3=starter_spear+starter_shield`, actions `0:play 25:vk:0x71 5:vk:0x72 5:vk:0x73
5:vk:0x70`, hands off).** F2, F3, F4, F1 through `keybd_event` each produced a c2s `0x0032`
carrying 1, 2, 3, 0 -- the F-keys reach the client's binding where the digit keys of
`control.py`'s note never reached the skill bar -- and each was answered by our batch (3 / 3 /
5 / 5 messages, the tape's order). The client's own weapon-set widget (bottom right) highlighted
F2, F3, F4, F1 in turn with the scythe, spear, shield and axe icons it had drawn from the
create's `0x0147` rows, and the body drew the scythe, the spear, the spear with the shield on the
left arm, and the axe (frames `2-vk.png` .. `5-vk.png`, cropped at 3x); no assert, no
disconnect through all four; the reset in the log is the harness's own teardown after the hold.
The energy orb is the re-declaration's own witness: on the first run (no 41 / 43 in the batch)
it read 25 through every frame while the server's pool stood at 30 -- exactly the silent split
the re-send exists to close -- and on the rerun it read **30, 30, 30, 25** after F2, F3, F4, F1,
the client's own integer from our property 41.
`0x0032` is now named `SELECT_WEAPON_SET` (high) in `schema/overrides.json` on the tape's 4 of 4
plus this labelled run.

**Also fixed on the way, since W1 (2026-09-18, `e544b0d4`).** The party block's commander-rig
tail (`hero_activate` .. the `PARTY ... commander rig ON` banner) sat under the `--player-weapon`
branch, so `--player-weapon` WITHOUT `--party` died at launch on an unbound `_pbody`, and
`--party` without a weapon flag skipped the rig. Every W1/W3 run passed both flags, which is why
neither showed; the first W9 launch (`--player-weapon` alone) found it.

**Tests.** `test_weapons.py` section 18 (21 checks, floor 129 -> 150): the four tape batches
with our ids, the server's hands after each (type 35 / 36 / 24 on the arm / 2, the interval per
type), the create's declarations and backpack slots, set 0's shield leaving and returning, the
energy words on a moved maximum and their absence on an unmoved one, the same-set and empty-set
nulls, five launch refusals, the two-handed drop, the party-row door, and the dispatch arm and
flag as source. `test_dispatch` 45, `test_cmsgnames` 16, `test_codec` 29, `test_smsgnames` 15,
`test_itemdetail` 19, `test_transfer` 28, `test_agentlife` 551, `test_srclint` 26,
`test_provlint` 19 green.

**Open after W9.** RUN-W9-2, a swing after a switch on the client (the `0x0035` pair at the next
start and the new interval on screen -- covered by JARIN-S's tests, not yet watched); retail's
reply to a same-set or an empty-set press; whether a switch that moves the maximum re-sends 41 /
43 on retail (needs a set holding a 556 item on a live tape -- the owner's own staff or focus
would do); what the client does with `0x0152` (the two items exchanging slots is the reading);
and the first field of the item family, 116 / 241 / 1 per instance, which ours sends as 1.

## 28. RUN-W9-2 -- run and scored 2026-09-19: the swing after a switch, and the 0x0035 the switch owed

**The question, pre-registered.** §27 shipped W9 and left "a swing after a switch, watched" open,
on the assumption §26.5's `ATTACK_SPEED_AT_START` already covered a base change. It did not, and
the run's job was to find out. Predictions, written before the launch: **P1** on our recorder,
start-to-start ~1.33 s before the switch (axe), ~1.75 s after (hammer); **P2** a `0x0035 [1, 1.75,
1.0]` rides the FIRST swing start after the switch, none before it; **P3** the client draws the
hammer after the switch, no assert.

**Retail's own answer was already on the 1A tape, and it is the mechanism.** The explorable
connection's four switches are axe(1.33) -> scythe(1.5) -> spear(1.5) -> spear+shield(1.5) ->
axe(1.33). Scanning it for `0x0035` to the observer (agent 25): three sends, and their timing is
the finding. `[25, 1.33, 1.0]` at t=263 (the spawn/first swing, axe); `[25, 1.5, 1.0]` at t=323.5
-- **twenty seconds after** the axe->scythe switch at t=303.4, i.e. at the observer's next swing,
not in the switch batch; `[25, 1.33, 1.0]` at t=597.0, **six seconds after** the spear+shield->axe
switch at t=590.7. The two SAME-base switches (scythe->spear, spear->spear+shield) sent **nothing**.
So retail re-declares the `(base, 1.0)` pair at the NEXT ATTACK START after a base change, 2 of 2
each way, and never for a same-base switch -- exactly `ATTACK_SPEED_AT_START`, but keyed on the
weapon's base, which §26.5's rule (the STANCE factor) never armed.

**The gap in our server, and the fix.** `select_weapon_set` changed `WEAPON_ATTACK_SPEED` /
`ATTACK_INTERVAL` through `apply_party_character` but never armed `attack_speed_pending`; only
`attack_speed_tick` (a stance factor change) did. So the server swung at the new interval while the
client, never sent a new `0x0035`, kept animating the old base -- the silent split the pair exists
to close. Fixed: when the base changes, `select_weapon_set` calls `_attack_speed_declare` with the
current stance factor, and `attack_speed_flush` sends it at the next start (the same door JARIN's
stance change uses). A same-base switch arms nothing.

**On our recorder (`authsrv-20260919T160117`, from harness `20260919T160048`; `--enemy
--practice-target --explorable --enemy-health 4000 --player-weapon starter_axe --weapon-set
1=starter_hammer`, `attack:10` then F2 then `attack:10`, hands off).** Start-to-start: six gaps of
**1.330** s (axe), then twelve of **1.750** s (hammer) -- P1, to the millisecond, no jitter. The
switch's `SET_ACTIVE_WEAPON_SET` is at t=35.769 and carries no `0x0035`; the pair `[weapon set 1,
1.75, 1.0]` goes out at t=36.442, which IS the first post-switch `attack_started` -- P2, the pair
rode the start and not the batch, +0.673 s after the switch (retail's was +20 s / +6 s because the
operator waited). The first hammer swing already used 1.75 (the last axe swing was t=34.692; the
gap to 36.442 is 1.75).

**On the client (harness `20260919T160048`).** The body swung the axe at the Hatcher before the
switch (`2-attack.png`) and the hammer after it (`4-attack.png`, the hammer head at the right hand);
no assert, no access violation, no disconnect through the whole chain -- the reset in the log is the
harness teardown. P3.

**Tests.** `test_weapons.py` §18 gains the RUN-W9-2 check (floor 150 -> 151, a vault run 153): the
switch batch carries no `0x0035`, a base-changing switch (axe->scythe 1.5, ->axe 1.33) arms the
pair for the next start, a same-base switch arms nothing -- retail's 2/2 each way. `test_mechanics`
246, `test_playerswing` 191, `test_guards` 45, `test_agentlife` 551, `test_dispatch` 45 green.

**W9 open list, now.** The same-set / empty-set replies (NOT OBSERVED, our smaller claim stands);
`0x0152`'s client effect; the item family's first field (116 / 241 / 1 per instance, ours 1);
whether retail re-sends 41 / 43 on a switch that moves the MAXIMUM ENERGY -- still INFERRED, no 556
item was in any 1A set. RUN-W9-2 itself is closed.

## 29. WEAPONS-W9, the desk close -- 2026-09-19: what the client does with `0x0152`, and the item family's first field

**Two of §28's four opens were the client's to answer, not a tape's, and its handlers answer
both.** Read on the pinned pristine build 38797 with `msghandler.py 0x0152 --follow --annotate
--depth 2` (and `0x0148` beside it); the workers are ItCliInv's and their asserts name them.

**`0x0152`, OBSERVED (binary).** Handler `0x00846840`: fields 2 and 3 are item ids indexing the
item array (`ctx+0xB8`, bound `ctx+0xC0`; a miss asserts `ItCliApi.cpp:2253 item1` / `:2254
item2`); field 1 is hashed into the inventory table at `ctx+0xD4` (`:2257 inventory`); then
`inventory->Swap(item1, item2)` at `0x0084B020`, all ItCliInv.cpp: both must be in a bag (`:687
item1->IsInInventory()`, `:688 item2->IsInInventory()`), both are REMOVED from their bag and slot
(`0x84aeb0`, `:621 bag`, `:622 bag->GetItem(slot) == item` -- the remove worker `0x014B` uses), and
each is ADDED at the OTHER's former bag and slot (`0x849ea0`, `:104 bagParent`, `:105
!bagParent->GetItem(slot)` -- the add worker `0x013E` uses, the destination asserted EMPTY). That is
the whole effect: **the two items exchange locations.** A hand changes only as a consequence -- the
add and remove workers fire the hands-changed refresh (`0x84b270`, `0x84a690`) whenever the touched
bag is type 2 (the equipped bag) and the slot is 0 or 1, the same refresh a `0x014B` into the
equipped bag fires. One more rule, read to its asserts only: when either item sits in a type-4 bag
(a storage pane, on our wire and retail's), the OTHER item -- the one about to land there -- is
first stripped from every equip set it belongs to (`0x84a3a0`, `ItCliInv.cpp:348 !(setMask &
~ITEM_EQUIP_SET_MASK)`, `:375 set < ITEM_PLAYER_EQUIP_SETS`): a weapon swapped into storage leaves
the sets. Nothing in the handler is about the hands, so §27's `ITEM_SWAP_EQUIPPED` (medium) named
the wire's context, not the mechanism. Renamed **`ITEM_SWAP_LOCATIONS`** (high) in
`schema/overrides.json`, beside `ITEM_CHANGE_LOCATION` and `ITEM_ADD_TO_INVENTORY`, and
`authsrv.py`'s constant with it. Widths `[u16, u32, u32]` per `msgshape` agree with messages.json.

**Two consequences for our sender, both now tested.** (1) **The leads rotate.** After our `0x0152
[1, old, new]` the old lead sits in the backpack slot the new one came from, so after one
0 -> 1 -> 2 -> 3 -> 0 cycle every inactive lead is in the NEXT set's created slot (15 at 11's, 11 at
13's, 13 at 15's on our ids). The server keeps no lead-slot state and must never name a lead's slot
from its create; only a shield's `0x014B` names a slot, and a shield's created slot is never taken
by anything else, so it is always free to return to. (2) **A leaving shield goes first.** Because the
add worker asserts the destination EMPTY, a batch that moves one shield OUT of the hands and another
IN must send the leaving `0x014B` before the entering one. `select_weapon_set` already did, in the
tape's order; it is now a constraint with a test, and the test's control feeds the two moves
reversed and watches the model trip `ItCliInv:105`.

**The first field, CLOSED by the catalog.** 116 / 241 / 1 per instance is the inventory key that
`0x0144 ITEM_STREAM_CREATE` registers (overrides 324, read 2026-08-18: `ItCliApi:2010
!inventory`, a key declared once), and the key `0x0147`, `0x0148`, `0x013E`, `0x014B` and `0x0152`
all hash to find their inventory (`0x8445a0` over `ctx+0xD4`; a miss is `ItCliApi:2257`'s
assert). It is a per-connection handle, not a character id -- `authsrv.py`'s
`PLAYER_INVENTORY_KEY = 1` comment already said so for the gold messages. Ours is 1 because we
register 1. Nothing to change.

**Tests.** `test_weapons.py` §18 gains four checks (floor 151 -> 155; a vault run 157): a model of
the three ItCliInv asserts fed the create and the batches -- the rotation after one cycle; two more
cycles and a scramble (3 -> 1 -> 0) with the equipped bag checked against `weapon_set_items` after
every switch; a shield at both ends (sword + shield against spear + shield) with the leaving move
first; and the control that reverses the two moves and trips `ItCliInv:105`. `test_smsgnames` 26 /
9 / 42, `schema/test_smsgnames` 15, `test_catalog` 13, `test_codec` 29, `test_msgmix` 56,
`test_dispatch` 45, `test_itemdetail` 19, `test_transfer` 28, `test_smsgsweep` 118,
`test_cmsgnames` 16, `test_agentlife` 551, `test_guards` 45, `test_pools` 132, `test_mechanics`
246, `test_playerswing` 191, `test_labelrun` 32 green.

**What is left of W9 -- all on ONE live tape, written into RUN-1B's steps (§6).** Retail's reply to
a press on the ACTIVE set and to a press on an EMPTY set (ours send nothing, NOT OBSERVED either
way), and whether a switch that moves the maximum energy re-sends 41 / 43 (INFERRED from the morale
path; a staff in a set does it, and 1B already holds a staff). Nothing else in W9 is open.

## 30. WEAPONS-W4, the rest -- shipped 2026-09-19: the damage type against the vs-type armour, and the `633` requirement

**What §4's W4 still owed after W4c (§16), Q11 (§17) and W8 (§26.3):** `587` had no reader
and every attack on the player counted as physical against the pieces' `+20 vs. physical
damage`; `633` had no reader, so a required weapon swung at its met damage whatever the rank
and a required shield or focus read as having no armour or energy at all (the `635` / `636`
half of WEAPONS-C7's partition). Both are read now. Desk, from the client and the corpus; no
client run -- nothing client-visible changes but the numbers in the damage words and a line
in the launch banner.

**The enum is the client's own, OBSERVED.** `587`'s argument, `0x00A7`'s kind field and the
`vs. %str1% damage` condition all index one fourteen-entry table, `s_charDamage`
(ConstChar.cpp, `damage < arrsize(s_charDamage)`), through two accessors guarded by the same
`cmp esi, 0xe`: `0x005AABA0` returns the type NAME's string id (the tooltip's `Damage` line,
template 2443, from the 587 handler at `0x00924B79`; special identifier 5's handler at
`0x00923C51`) and `0x005AAB70` the ADJECTIVE's (the range line, `Blunt Dmg: 3-5`; the table
studies/isle B2 read). Resolved with `textrec.py`: 0 Blunt, 1 Piercing, 2 Slashing, 3 Cold, 4
Lightning, 5 Fire, 6 Chaos, 7 Dark, 8 Holy, 9 Nature, 10 Sacrifice, 11 Earth, 12 Generic, 13 a
second Dark (the duplicate B2 saw; why, UNVERIFIED); the item accessor's default with no 587 is
14 (`0x008451C6`, `push 0xe`), "no type". CORROBORATED on the corpus (`aw_w4census`, 96
connections, 3,857 items): bows, daggers and spears carry 1, hammers 0, swords and axes 2 (18
swords 5, fiery), wands and staves 3 / 4 / 5 / 6 / 7 / 8 / 11, NPC ranged weapons 0..6 -- and no
item anywhere carries 9, 10, 12 or 13. Kindle Arrows' kind 5 (W2e) reads as Fire. The table is
`content/world.toml [damage_type.table]` (client-table, `consttable.py`, build 38797) and the
wiki's grouping `[damage_type.classes]` -- physical 0 / 1 / 2, elemental 3 / 4 / 5 / 11, the
rest neither (WIKI, GWW "Damage type"; Shadow damage is on the wiki's list and not in the
client's fourteen). `test_weapons` 19 reads both tables back from the pinned client.

**A `527` line's condition is the SPECIAL word right before it, OBSERVED.** The twenty special
identifiers (1..20) are the tooltip's condition suffixes, resolved from their own templates:
1 `Requires %num1% %str1%`, 3 `vs. elemental damage`, 4 `vs. physical damage`, 5 `vs. %str1%
damage` (a named type), 8 `vs. %str1%` (a creature kind), 9 `while attacking`, 10 `while
activating skills`, 12 `while holding an item`, 13 `while using a Preparation`, 14 `while
%str1% is below %num1%`, 17 `while in a Stance`, 18 `while your pet is alive`, 19 `while
affected by a Shout, Echo, or Chant`, 20 `while not affected by [an] %str1%`. On every worn
piece in the corpus the shape is `(572, 4, 527)` (345) or `(572, 3, 527)` (55): the rating,
the condition, then the `+N` it qualifies -- our own pieces' `[572 25, 4, 527 20]` is the
first shape. The named form (5) sits on no item; the situational ones sit only on type-8
upgrade components (`(603, 576, 614, 7, 11, 595, 527)` and kin, where which lines an `11`
scopes is unread). The client has NO reader for 527 (`itemmods --reads 527`: the tooltip
walker only), so the armour rule is the server's alone and the wiki's: a `+N` counts against
the types its condition names (GWW "Damage type", "Armor rating").

**What ships, armour.** `combatmath.armour_of_piece(item, damage_type, ..., met=True)`
replaces the `physical` boolean: `damage_type` is an id from the fourteen or a class name, a
condition word pends for the line after it, 4 admits the physical class, 3 the elemental
one, 5 that one type, 9..20 nothing (not modelled, said once per identifier). `player_armour_at(location, damage_type, state)`,
`offhand_armour(damage_type, state)`, and `land_swing` reads the location against
`body_damage_type(agent)` -- the swinger's own item's 587, "physical" for a creature with no
item (the reading land_swing always made). A spell stays "elemental": the skill records'
damage types are not extracted, so a fire spell and a physical-damage skill read alike
(left). `--no-typed-armour` reverts to every-attack-physical. On our pieces nothing changes for
a sword, an axe, a bow, a hammer, a spear or daggers (all physical); a wand's or staff's
element and a chaos or dark wand now miss the +20, and a `+N vs. elemental` piece, the day
one is worn, meets fire and cold and not a sword.

**What ships, the requirement.** `combatmath.weapon_requirement(item)` reads `633`
`{attribute, rank}`; `requirement_met(item, ranks)`; `player_weapon_rank` takes the item's
633 attribute FIRST and the type table only for an item with none -- a required sword names 20
on 242 of 242 corpus swords, a required wand or staff a caster attribute the type table cannot
know; `player_rank_of(attribute, state)` gives the effective rank from the connection's live
state or, at launch, the seed ranks plus the equipped bonuses. Then: a weapon's damage divides
by **3.098** when the requirement is unmet -- `mult = 1 / 3.098` into `swing_damage` at the
three player sites (the rank branch, the caster branch, the scythe's extras) and at
`body_swing_damage` for a body holding a required item it lacks the rank for; a required
shield's `635` is its armour when met and 8 (a 16-armour shield) or 5 (below 16) when not; a
required focus's `636` is its energy when met and +3 when not (`weapon_energy_bonus(state)`).
The hit sites hand in the Weakness-cut rank (WIKI, GWW "Requirement": Weakness can unmeet a
requirement until it expires). The launch banner gains `weapon: deals slashing, requires
attribute 19 at 9: MET (rank 12)` / `UNMET (rank 3, damage / 3.098)`. `--no-unmet-requirement`
reads and prints and costs nothing.

**Where the numbers come from, and how far to trust them.** The divisor is the isle's rank
ladder (studies/isle/FINDINGS.md 9.1-9.2, capture `20260821T163511`): one hammer at ranks 5 /
6 / 7 / 8, 235 events, per-block divisors 3.133 / 3.073 / 3.105 / 3.082, mean 3.098; the naive 3
and the 10/3 both excluded, the wiki's "approximately two-thirds" the same claim with fewer
digits. OBSERVED -- with the caveat that study wrote: a divisor on the rank-appropriate damage
is ONE of the two parameterisations the ladder admits, the other a strike-level drop, and
both give those four numbers; RUN-WEAPONS-3 separates them and measures a second weapon.
`test_weapons` 19 reproduces the ladder through `swing_damage` with the divisor as the
multiplier: every block's mean within 3 % of the observed 3.864 / 4.296 / 4.637 / 5.093, rank
5's band 3..5 (its eleven 3s) and rank 8's 4..6 (its twenty 6s). The shield's and focus's
unmet values are WIKI (GWW "Requirement" sec. Drawbacks, read 2026-09-19), the
not-randomly-generated arm of each rule because every item this server hands out is made, and
no tape shows either (no observing player held a required shield or focus). The vs-type rule is
WIKI over the client's own tables; no tape shows a typed hit on a `+N vs. elemental` piece
either, and the first would test the grouping row.

**Tests.** `test_weapons.py` gains section 19 (23 checks, floor 155 -> 177; a vault run 180,
the pinned-client read-back being the one vault-only check): the two tables and the classes,
the read-back, the 587 reader on our items, the warrior body against slashing / fire / chaos /
untyped / the old `physical=False`, the elemental, named, situational, unconditioned and
two-line pieces, the chest at 45 vs 25, `body_damage_type`, the revert flag, the source lock on
land_swing's site and both flags, the 633 reader and `requirement_met`, `player_weapon_rank`
via 633 then the table, the factor on the rank handed in, the revert, the isle ladder, a
body's factor, a required shield at 16 / 8 / 5, the held shield through the Strength rank, a
required focus at 12 / 3 and a plain one at 5, and the banner. The old `physical=` keyword is
still taken (True = "physical", False = "elemental") -- `test_agentlife`, `test_mechanics`
and `test_skilldamage` pin it. `test_content` 48, `test_mechanics` 246, `test_skilldamage`
67, `test_pools` 132, `test_playerswing` 191, `test_guards` 45, `test_agentlife` 551,
`test_adrenwire` 77, `test_weaponcensus` 38, `test_itemdetail` 19, `test_labelrun` 32,
`test_dispatch` 45, `clientscan/test_itemmods` 42, `test_srclint` 26 (it caught a
`SystemExit` the read-back's fallback would not have caught on a bare machine), `test_checks`
17, `test_provlint` 19, `test_citelint` 50, `test_bareimport` 8, `test_derivlint` 32 green.

**Left of W4, named.** The hornbow's 10 % armour penetration (WIKI, GWW "Hornbow") waits on
Q2 -- which `609` class is the hornbow is RUN-1B's; identifier `573` (an `Armor: N` variant
with a condition string, on 4 corpus pieces x 5 slots) is unread and such a piece reads as
unarmoured; a spell's own damage type (the skill record's) is not extracted, so spells stay
"elemental"; the scoping of a situational condition over a type-8 upgrade component's lines;
and Q10's split, above. Q10 leaves §7's table as SHIPPED with RUN-3 still owed.

## 31. WEAPONS-W5b -- shipped 2026-09-19: a staff's `570`, "Halves skill recharge of spells", rolled at the completion

**What was open.** §15 (W5) read the staff's `556` energy and left its other inherent word
unread: `570 (16..17, 1)` beside GWW's "halves skill recharge 10-20 %". Read now, on the
corpus, the client and the wiki; no client run -- the wire's shape is unchanged (the `0x00E5`
integer), only its value on the casts the roll wins.

**The word, OBSERVED.** `570` sits on **518 staves and on nothing else** across the corpus's 96
connections (`aw_570census`): (arg, arg2) = (16, 1) x333, (17, 1) x104, (15, 1) x53, (14, 1)
x18, (10, 1) x8, (20, 0) x2; the leading word of the requirement-shape `(570, 633, 587, 617,
556, 634)` (508 items) and of the plain shape `(570, 587, 617, 556, 584)` (8), never preceded by
a condition word. The tooltip handler (`0x009260A2`) renders `arg` through 2439 `%str1%:
%num1%%%` under 2376 `Chance` and the line 2432 `Halves %str1% of spells` with 2392 `skill
recharge` -- "Halves skill recharge of spells (Chance: 16%)"; `arg2` only picks a
display-record variant (both branches format the same strings; unread further). GWW "Staff"
lists the property as inherent: "Halves skill recharge of spells (Chance: 10...20%)", the
corpus's 10..20. The attribute-specific wand / focus form ("Halves skill recharge of Domination
Magic spells") is on no corpus item and is not modelled.

**The rule is WIKI, and no tape can witness it.** Two censuses: no observing player ever cast
holding a staff (their leads were wands, bows, hammers, swords and daggers), and the one hero
whose `0x00E5`s ride the wire (JARIN's, `20260914T005758` agent 30, 35 of them) held a sword
and shield. So the mechanism is GWW's -- "HSR" (read 2026-09-19): it "affects only spells";
an inherent staff mod maxes at 20 %, an inscription at 10 %, a wand's or focus's
attribute-specific one at 20 %; "capped at 50%, i.e. the skill recharge time ... can only be
halved at best" -- and "Recharge time": the recharge "is calculated as the skill finishes
activating", and "effects that alter recharge time round to the nearest second". "Spell" is
the client's own type column (studies/skills 35.3, the namer's words): 4 Hex Spell, 5 Spell,
6 Enchantment Spell, 9 Well Spell, 11 Ward Spell, 24 Item Spell, 25 Weapon Spell -- GWW
"Skill type" lists exactly those six subtypes under Spell. What is ours: a .5 rounds UP (5 -> 3;
the wiki does not say which way), and two 570s are two independent triggers whose union is
one halving (the cap).

**What ships.** `combatmath.half_recharge_chances(items)` (one percent per 570 held),
`is_spell_type`, `halved_recharge(seconds)` = the nearest whole second, .5 up;
`authsrv.half_recharge_roll(items, skill_id)` rolls every chance for a spell and never for
anything else; `HALF_RECHARGE` / `--no-half-recharge`. **The player:** the roll is in
`cast_tick`'s E5 branch, at the completion, over the held lead and off hand; on a win
`cast["recharge"]` becomes the halved integer (what the `0x00E5` carries -- the client's only
source for the sweep), `recharge_s` with it, and the E6 clock is re-based on the E5 instant, so
the `0x00E6` comes when the halved recharge runs out. A cast that failed a chain step (recharge
0, `no_e6`) is never rolled. **A body:** rolled at its cast's START -- a body never swaps
mid-cast, so start and completion read the same item -- over its `weapon_item`; the halved
value goes into `skill_ready` and is stashed as `cast_recharge`, which the hero's own
`0x00E5` pops at the completion (`hero_skill_messages`). **Content:** `hsr_staff` -- the
henchman's staff (caster_staff's four words) plus one composed 570 at arg 20 in the corpus's
own encoding (`0x23A81401`; the 518 carry `0x23A81001` / `0x23A81101` / `0x23A80F01`), source
`invented` and saying so; `--player-weapon hsr_staff` is the harness's way in, and its
tooltip is the client's own rendering of the word. The launch banner reads `weapon: deals
holy, halves spell recharge at 20 %`.

**Tests.** `test_weapons.py` section 20 (12 checks, floor 177 -> 186; a vault run 192, the
three press checks wanting skill 83's row): the item's words and the reader; the rounding
table; the seven spell types against ten non-spells; the roll rigged under, at and over the
chance, on a signet, with no 570, with empty hands, with two 570s and one miss; the revert;
through the real press and `cast_tick` -- a 5 s self spell (83) completing under a winning
roll sends `0x00E5 [me, 83, 0, 3]` with the E6 clock 3 s past the E5, a missing roll sends 5
with 5 s, and the revert sends 5 on a winning roll; a body's items and roll; the source lock on
the stash / pop and the E6 re-base; the banner. `test_castcycle` 54, `test_castcancel` 44,
`test_daggers` 103, `test_pools` 132, `test_agentlife` 551, `test_playerswing` 191,
`test_mechanics` 246, `test_skilldamage` 67, `test_guards` 45, `test_dispatch` 45,
`test_labelrun` 32, `test_content` 48, `clientscan/test_itemmods` 42, `test_srclint` 26,
`test_checks` 17, `test_provlint` 19, `test_derivlint` 32, `test_citelint` 50 green.

**Left, named.** The .5 rounding and the two-trigger union are ours; the first live tape with a
staff in an observing caster's hands (RUN-WEAPONS-1B holds a staff and a wand, and the sealed
plan should add ten casts of one 5 s spell) measures the chance and the rounding at once --
a 5 s spell under a 20 % staff sends 3 about one cast in five. The attribute-specific wand /
focus form and "Halves casting time" (its neighbour on the same items) are not read. A side
finding of the census, outside this rung: on `20260917T160915` / `224104` the observer's skills
775 and 780 (table recharge 2 and 3) were sent with recharge 0, and on `20260916T213125`
skill 1 with 24 where the table says 4 -- three recharges retail sent that are not the client
table's, unexplained here and worth a SLICE look.

## 32. WEAPONS-Q2 CLOSED at the desk, and the hornbow's 10 % shipped -- 2026-09-19: the client's own bow-class names

**Q2 asked which `609` value is which bow class, and named RUN-1B as the instrument (five
bows, five `0x0035` bases).** The client had the answer in a string table. The `609`
tooltip handler (`0x00924F71` on build 38797) opens with `cmp dword [esi+0x20], 5` -- the word
is read on item type 5, a bow, and on nothing else -- then `push dword [ebx*4 + 0xBCAAEC]`
with ebx the word's argument, and formats 69415 `Two-handed %str1%` with that string. The
table's five ids resolve through `textrec.py`: **69416 Shortbow, 69417 Longbow, 69418
Flatbow, 69419 Recurve Bow, 69420 Hornbow** -- so 609 = 0 shortbow, 1 longbow, 2 flatbow, 3
recurve, 4 hornbow. OBSERVED, the client's own words. **And the corpus agrees where it can:**
WEAPONS-C6's only bow durations are `0x0035` base 2.475 on classes 1 and 3 (x10), and 1 and 3
are the Longbow and the Recurve Bow, the wiki's two 2.475 s classes -- a check this table
could have failed. `itemmods.py --bow-classes` is the extractor (located from the handler's
own shape, refused on a build where the shape moved); `content/world.toml [bow_class.table]`
carries the ids and labels; `[bow_class.rules]` is the wiki's half in a row of its own.

**What the class buys, and ships.** (1) **The rate.** `weapon_rate_key(item)` gives a type-5
bow its CLASS's `[attack_speed.rates]` key -- shortbow / flatbow 2.025, longbow / recurve
2.475, hornbow 2.7 (WIKI, the rates row's own provenance; corroborated for 1 and 3) -- at
the character's door (`apply_party_character`) and at the hostile's entry (`--enemy-weapon`),
where every bow used to be the type row's 2.475. A type-28 NPC bow keeps its 1.75: the
handler reads 609 on type 5 only, and retail tells type 28's holders 1.75 (C8). (2) **The
hornbow's 10 %.** WIKI (GWW "Hornbow": "an extra 10% armor penetration"; "Armor penetration":
a BONUS penetration that stacks on the largest base one; "Armor calculation" step 3: the
rating times (1 - p), rounded, then the Special step where a critical's 20 comes off).
`weapon_armour_penetration(item)` is the class row's 0.10 for a hornbow and 0.0 for anything
else; `penetrated_armour(armour, item)` is the wiki's step 3 to the nearest whole number (a
.5 up, ours: 45 -> 41) and sits at every site that reads a target's rating for a hit --
`hit_enemy` (the player's swing, arrow and skill shot alike), the scythe's extras and the
preparation splash (both 0 for their weapons), `land_swing` (a body's hornbow against the
player, BEFORE the casting penalty) and a body's swing on a body. The critical's 20 and
Healing Signet's 40 stay where they were, after it. No base penetration is modelled yet
(Strength's 1 % per rank on attack skills, Penetrating Attack's 10 % -- WIKI, named, not
built), so the hornbow's is the whole term today. (3) The launch banner names the class:
`a hornbow (609 = 4) at 2.7 s, +10 % armour penetration`. `--no-bow-classes` reverts both.

**Unmeasured, and said.** No observing player held a hornbow, a shortbow or a flatbow on any
tape (the owner's bow is the 609 = 3 recurve; the corpus's bows in an observer's hands are
classes 1 and 3), so the three rates and the penetration are the wiki's; RUN-WEAPONS-1B
measures the five clocks (§6) and, with a hornbow on the Master of Damage suits, the 10 %
against the 100-armour suit (a 20-roll at rank 12: 10 on the 60 suit either way, 6 against 100
for a longbow, 7 for a hornbow). The wiki's own anomaly ("sometimes it subtracts slightly
more") is not modelled. Q3 (the projectile speed per class) and the ranges per class are
unchanged: `speed_by_609` / `range_by_609` on the bow row still carry the one measured class.

**Tests.** `test_weapons.py` section 21 (10 checks, floor 186 -> 195; a vault run 202, the
extractor read-back the one vault-only check): the two content rows; the read-back from the
pinned client (handler `0x00924F71`, table `0x00BCAAEC`); the reader on starter_bow (1), the
type-28 bow (None), classes 0..4, a 7, no 609, an axe; the labels and rates per class; the
character's interval with a made hornbow (2.7), flatbow (2.025) and the starter longbow
(2.475); the penetration table 60 -> 54, 45 -> 41, 81 -> 73, 100 -> 90 and none for the rest;
through the real `hit_enemy` a 20-roll hornbow on AR 60 lands as on 54 and out-deals the
longbow's same roll; the revert; the source locks on the five sites, the door and the flag;
the banner. `clientscan/test_itemmods.py` section 15 (floor 42 -> 43): the extractor's handler
is the generic table's 609 entry and its five ids are distinct and the pin's. `test_mechanics`
246, `test_playerswing` 191, `test_skilldamage` 67, `test_pools` 132, `test_guards` 45,
`test_agentlife` 551, `test_dispatch` 45, `test_labelrun` 32, `test_castcycle` 54,
`test_daggers` 103, `test_weaponcensus` 38, `test_content` 48, `test_bareimport` 8,
`test_srclint` 26, `test_checks` 17, `test_provlint` 19, `test_derivlint` 32, `test_citelint`
50 green.

## 33. Identifier `573` read -- 2026-09-19: "Armor: N (depends on level)", a hero's level-scaled piece

**What §30 left.** `573` sat on "four corpus pieces x five slots", unread, and a piece carrying
it read as unarmoured. Read now: the word, its handler, its wearer and the wiki agree.

**The word, OBSERVED.** Twenty items across the corpus and nothing else: one five-piece set
(types 4 / 7 / 13 / 16 / 19, models 17977..17980 and 19012), every piece `(573, 80, 23)` then
`(4, 527 20)` -- the headpiece with a `644` ("Item's attribute +1", the wiki's hero
headpiece) in front -- created into inventory key 5 behind `0x015A ITEM_SET_PROFESSION [..,
item, 1]` (a Warrior) and moved into its bag 18, on the JARIN hero tape (`20260914T005758`,
three connections) and the aggro tape (`20260916T150306`): **the Warrior hero's armour**. The
tooltip handler (`0x009240F4`) draws it from the walker context's level slot (`+0x24`): with a
level, 2438 `Armor: N` where N = arg2 + (arg - arg2) x X / 10; without one, 2440 `Armor: N-N`
with arg2..arg; then 51163 `depends on level` -- so arg2 is the LOW rating and arg the HIGH.
What X is (the caller's tenths) is unread; the server's rule below needs no X. The client has
no reader for 573 outside the tooltip (`itemmods --reads 573`): the number lives on the server.

**The rule, WIKI and CORROBORATED three ways.** GWW "Hero armor" sec. Armor rating (read
2026-09-19): a hero's rating "is dependent solely on their profession and level" -- Warrior /
Paragon 23 at level 1 to 80 at 20, Ranger / Assassin / Dervish 13 to 70, the casters 3 to 60,
three a level; GWW "Hero": "set at an armor rating suitable for the hero's level and
automatically increases in armor rating with the hero level". `(80, 23)` is the Warrior row's
two ends. The rating at level L is the line between them, low + (high - low) x (L - 1) / 19,
which for every wiki row is 3 x L + 20 / 10 / 0 -- the creature formula
`combatmath.creature_armor_rating` already uses (3 x level + a profession bonus of 20 / 10 /
0, the same three rows), the isle's WIKI source and the hero's tape's endpoints agreeing.

**What ships.** `combatmath.LEVEL_SCALED_ARMOUR = 573`, `level_scaled_rating(low, high, level)`
(the line, level clamped to 1..20; no level reads the low end), `armour_of_piece(...,
level=)` reading 573 as the rating beside 572 and 635, `player_armour_at(..., level=)` and the
server's `player_level_of(state)` (the connection's level, else the character's seed) at the
location and off-hand readers. Our heroes rate by `creature_armor_rating` and wear no pieces
on the wire, so nothing changes for them; the reader is what lets a content row carry the
tape's word -- a hero set declared with `573` would rate itself at the wearer's level. No
content row carries one yet.

**Tests.** `test_weapons.py` §19 gains three checks (floor 195 -> 198; a vault run 205): the
line reproduces the wiki's three rows at every level 1..20 and the isle's formula, clamps and
defaults; the corpus's set reads 23 / 35 / 80 at levels 1 / 5 / 20 with its +20 vs. physical
counting for a slashing hit and not a fire one; through `player_armour_at` a level-7
connection reads 61 and a level-20 one 100, no state the seed level. `test_mechanics` 246,
`test_skilldamage` 67, `test_pools` 132, `test_guards` 45, `test_agentlife` 551,
`test_playerswing` 191, `test_srclint` 26, `test_checks` 17, `test_bareimport` 8 green.

**Left.** The tooltip's X (what the caller feeds `+0x24`; the low-end reading at level 1 and
the high at 20 say it is (L - 1) x 10 / 19 or the caller clamps -- unread, and nothing here
depends on it).

## 34. A spell's own damage type -- 2026-09-19: no client column, the wire carries it, the content row names it

**What §30 left.** Every incoming armour-respecting spell read as "elemental" against the
player's typed armour, and a spell's projectile would have carried the held weapon's kind.
Both because nothing read a spell's type. Read now; three sources, one of them a negative.

**The client has no column for it -- a check that could have found one.** Over all 41 dword
columns of the 164-byte `s_skill` record (3,443 named rows), only three range inside the
enum's 0..14 and each is already named: `+0x08` the campaign, `+0x14` the chain mask, `+0x58`
the argument count. The type sits in the authored description ("deals 15...63 fire damage")
and nowhere structured, so the client-table route (`skilltable.py --emit-content`) cannot
carry it. NOT FOUND, and said as a scan rather than an absence.

**The wire carries it, OBSERVED.** A spell's projectile arrives (`0x00A7`, third field) as the
SPELL's type, not the caster's weapon's: Lightning Orb (229) as 4 under an earth staff (587 =
11, `20260917T090355`, x11), under a fire staff (5, `20260917T224104`, x11) and under a
lightning wand (`20260913T210901`, x5); Lightning Javelin (230) as 4 under the same earth and
fire staves (x15); Dancing Daggers (858) as 11, earth, with a hammer (587 = 0, `20260817T183756`,
x3) or daggers (1, `20260819T132414`, x14) in hand; Fireball (186) as 5 under a fire staff
(`20260817T231139`, x35). 79 of 79, the held type ruled out on 54 of them. An attack skill's
shot keeps the weapon's kind (WEAPONS-C10: Power Shot 1 or 5 under Kindle Arrows) -- the two
families differ exactly where the wiki's "damage type" says they should.

**The content row names it.** The source for a skill's type on this server is its
`skill_effect` row: `damage_type` (the client's enum, `[damage_type.table]`) when the row
carries the key, else the wiki's own scale label -- `combatmath.damage_type_from_label`:
"Fire damage" -> the table's "fire" -> 5, "+ Holy damage" -> 8, "Cold damage" -> 3 -- from
`scale_means` then `bonus_scale_means`, else None. Rows 194 (Flare, 5), 312 (Holy Strike, 8)
and 252 (Banish, 8) now carry the key beside 433's (Kindle Arrows, W2e). Whether typed damage
RESPECTS armour stays a separate per-row fact -- `ARMOUR_RESPECTING_MEANS`, now the four
elemental labels (WIKI, GWW "Armor rating": "most spells dealing elemental damage"; "Armor-
ignoring damage": the property "is independent of damage type", shadow, most holy and
typeless skill damage ignore it) -- no row carries the three new labels yet.

**What ships.** `authsrv.spell_damage_type(skill_id)`; `spell_armour_for` resolves an incoming
spell against its OWN type through `player_spell_armour(..., damage_type=)` -- a fire spell
meets 25 on the warrior pieces as before, a physical-damage spell would meet their +20, a holy
or chaos one neither -- "elemental" when no type is read (the old reading, kept as the
default); `skill_shot_how` gives a SPELL's shot its own type as the `0x00A7` kind beside its
own projectile, an attack skill the weapon's. On this server only an attack skill launches a
projectile at its completion (`_shot = player_ranged(state) if (cast["attack"] and target)`
-- a player's Flare lands at the E5 with no `0x00A4`, which is its own open item, WEAPONS-W2's
spell half), so the kind reaches the wire today through a body's skill shot;
`--no-spell-own-type` reverts both halves.

**Tests.** `test_weapons.py` section 22 (6 checks, floor 198 -> 203; a vault run 211, the
tape the one vault-only check): the label table; the four rows and two Nones; the shot's kind
for a spell, an attack skill and the revert; the armour a spell of each class meets (25 / 45 /
25) and the respecting set; the source locks (the E5 gate, the flag, Flare's key); and the
wire's witness -- on `20260819T132414` every Dancing Daggers arrival (14) carries kind 11 with
daggers in the caster's hand. `test_skilldamage` 67, `test_pools` 132, `test_agentlife` 551,
`test_mechanics` 246, `test_content` 48, `test_srclint` 26 green.

**Left.** A player's spell projectile (the `0x00A4` a Flare or an Orb launches on retail at
the E5 -- W2's spell half, not started); the rows for the four wire-measured spells (186 /
229 / 230 / 858 have no `skill_effect` row, so their types live in this section and the
provenance of `[damage_type.table]`, not in content, until a row is written for them); the
base penetration sources (§32).

## 35. The base penetration sources -- 2026-09-19: the client's own slot, the wiki's two tiers, one wire witness

**What §32 left.** The hornbow's 10 % was the whole penetration term; the base sources --
Strength's 1 % per rank on attack skills, Penetrating Attack's own -- were WIKI, named and
unbuilt. Read now, from three places, one of them the tape.

**The rule, WIKI.** GWW "Armor penetration": two tiers. *Base* penetration is "the
non-stackable, fixed amount of penetration listed in a skill's description"; with more than one
source "only the highest value is used". Its table: Strength 1 % per rank "when using attack
skills"; Air Magic spells 25 %, "each one that deals lightning damage"; Penetrating Blow / Chop
20 %; Penetrating / Sundering Attack 10 %; Spear of Lightning 25 %; the Ritualist's Cruel Was
Daoshen (10), Destructive Was Glaive (20) and Sundering Weapon (10). *Bonus* penetration ("armor
penetration +20%") "does stack (adding them together) and add[s] to the largest base": the
hornbow's 10 %, a Sundering upgrade's 20 % at a 10-20 % chance, Judge's Insight's +20 %,
Warrior's Might. GWW "Strength": each rank 1 % on attack skills "that don't already have a
higher amount" -- Penetrating Attack "can still be affected with 11 or more Strength"; "does
not apply to pet attacks". GWW "Armor calculation" step 3: the rating × (1 − p), rounded (its
own examples 60.75 → 61, 98.25 → 98), the Special step (a critical, Healing Signet) after it.
The wiki's own anomaly ("sometimes it subtracts slightly more") stays unmodelled.

**The client's own slot, CORROBORATED.** The scan that found no damage-type column (§34)
found this one. The 164-byte record's bonus slot (`+0x64` / `+0x68`) holds the wiki's
percentage with EQUAL endpoints on every skill the table names: 398 / 1191 hold 10 / 10 (args
= 2, bit clear), 339 / 1136 hold 20 / 20, 1551 holds 25 / 25 (bit set -- formatted into its
description), 1218 / 1732 / 2148 hold 10 / 20 / 10, the PvP copies the same: eight of eight
against the page's table, and the same on all five client snapshots in the vault (2026-04-30 ..
2026-09-01) while 339 / 1136's SCALE moved 5..20 → 10..25 with the 2026-09-01 build (the
page's current number; the pinned 38797 reads the older). The slot is a general hidden-constant
slot (Final Thrust's 50 is a health threshold, Distracting Shot's 20 is seconds), so the content
row names its meaning -- `bonus_scale_means = "Armor penetration %"`, the Final Thrust pattern.
The Air spells do NOT carry theirs -- Lightning Orb's slot holds 1800, Javelin's 1..10,
Lightning Strike's and Chain Lightning's 0 (Lightning Hammer's and Invoke Lightning's do hold
25) -- so that tier is the wiki's attribute rule, keyed on the skill's attribute (8) and its own
type (§34's lightning).

**The wire's one witness, OBSERVED (Air Magic).** studies/skills §50.1 already had it and
did not name it as a penetration measurement: Lightning Orb onto a PvP Warrior's five 80-armour
pieces lands exactly its tooltip (101 × 9) and 2^(60/40) of it bare (286 × 2) -- an effective
60 from 80, which is 80 × 0.75 and nothing else; Javelin 50 / 140, the same step inside
truncation. Nothing more anywhere: `aw_apcensus` over every live connection joined the
player's attack-skill announces (`0x00A0` prop 50 and the `0x00E3` ack) to the damage words
its cause landed and to the player's Strength (`0x003B`). **Strength's term is UNWITNESSED:**
no live tape lands a Warrior's attack skill on a target of known rating -- the isle's
engagement blocks were plain swings (0 casts in any block), the RB2 Warrior at Strength 8
pressed none at a foe, JARIN's Power Attacks (× 11) hit creatures of unknown rating with no
`0x003B` on the tape; none of the five penetration skills was ever announced by a player; the
Assassin's dagger attacks at the Master of Damage (775 / 780 / 782, `20260917T160915` /
`T224104`) carry no Strength.

**What ships.** `combatmath.armour_penetration(base, bonus)` -- the largest of the base tier
plus the sum of the bonus tier -- `strength_penetration(rank)`, `penetrated_rating(armour, p)`
(the wiki's step 3; a .5 up is ours). Content: `[armour_penetration.rules]` (Strength 17 at
0.01 a rank, Air Magic 8 at 0.25 on damage type 4), rows 398 / 1191 / 339 / 1136 / 1551 (`+
Damage` with the slot's label) and rows 229 / 230 (`Lightning damage`, `damage_type = 4`, the
wire's kind from §34 -- so §34's "rows for the four wire-measured spells" is half closed; 186 /
858 stay). `authsrv.skill_base_penetration(skill_id)` (the row's slot, else the Air Magic rule),
`strength_base_penetration(rank, skill_id)` (attack skills only), `player_base_penetration
(state, skill_id)` and `body_base_penetration(agent, skill_id)` (the larger of the two, never
the sum; the EFFECTIVE Strength, so a Weakness on the swinger cuts it as it cuts every rank).
`penetrated_armour(armour, item, base=)` composes the tiers at every rating read: the player's
hit (a plain swing 0; Power Attack at the seed's Strength 9 lands on AR 60 as on 55; Penetrating
Blow as on 48, its own 20 beating the 9; Penetrating Attack as on 54 with a longbow and 48 with
a hornbow, the 10 % plus the bow's 10 %), the scythe's extras, a body's swing on the player and
on a body (a corridor raider at Strength 2: 2 %), and the incoming spell -- `spell_armour_for`
takes the spell's own base off BEFORE the taker's casting penalty (wiki step 4): an Orb onto the
pieces' 25 meets 19, onto retail's 80 the tape's 60. `SCALE_MEANS_DAMAGE` gains the three
elemental labels beside "Fire damage" so a body's Orb deals its scale. The character's door
names the rank (`Strength 9: an attack skill ignores 9 % of the target's armour ...`).
`--no-base-penetration` reverts (the hornbow's bonus stays).

**Tests.** `test_weapons.py` section 23 (11 checks, floor 203 → 208; a vault run 222 -- the six
that read the skills table are vault-only): the rules row and the labels on the seven rows; the
tiers (Chop's 20 over Strength 9, Strength 11 over Penetrating Attack's 10 -- the page's own
sentence -- never their sum, the bonus on top); the wiki's worked examples 61 / 98, 80 → 60,
and the tape's arithmetic (101 = the tooltip because 60 IS the baseline, 286 / 101 = 2^(60/40)
within 1.5 %); the composition; the skills' numbers; the slot read back from the table; through
the real `hit_enemy` at Strength 9 on AR 60: 60 / 55 / 48 / 54 / 48; the revert; the bodies; the
incoming Orb and Javelin at 19; the source locks on the five sites, the door and the flag.
`test_skilldamage` 67, `test_mechanics` 246, `test_pools` 132, `test_agentlife` 551,
`test_playerswing` 191, `test_daggers` 103, `test_effects` 85, `test_content`, `test_srclint`
green.

**Left, and named.** The BONUS side beyond the hornbow: the client's item word **574 `Armor
penetration`** (handler `0x009241AB`, text 2373 -- the Sundering upgrade's "+N % (Chance: M %)")
sits on no corpus item, and Judge's Insight (267) has no row; neither is modelled. Not modelled
either: the Ritualist's ashes (a bundle), Spear of Lightning's line AoE and type conversion,
Javelin's interrupt and line, the wiki's "slightly more" anomaly. RUN-WEAPONS-1B can witness
Strength's term with one attack-skill block on the 60-suit: at Strength 9 a 15-22 sword's
ceiling 22 reads 23 under Power Attack (22 × 2^(5/40) = 23.99, truncated) where 22 is the ceiling
without it -- twenty presses, the maximum is the measurement; written into 1B's row (§6).

## 36. A player's spell projectile -- 2026-09-20: W2's spell half -- the E5 launches it, the arrival lands it

**What W2 left.** A projectile spell -- Flare, Lightning Orb, Dancing Daggers -- landed its
damage at the E5 with nothing in the air, while retail sends a `0x00A4` at the cast's completion
and the word a flight later. §13 shipped the attack-skill half on 2026-09-18; §34 named the
spell half open.

**The shape, OBSERVED.** `weaponcensus.skill_shots` over the live corpus: 94 spell shots, 17 by
the player and 77 by bodies. The player's are all Dancing Daggers -- the corpus's only
player-cast projectile spell (`20260819T132414` × 14 over five casts, `20260817T183756` × 3) --
and every one of them reads the same:

- **The E5 batch carries the first launch.** `0x00E5 [me, 858, 0, 5]`, `[58, me, 0]`, then
  `0x00A4 [me, aim, 0, flight, 854, handle, 0]`, then the hold pulse `[8, me, 0]`, `[8, me, 1]`
  -- one batch, 5 of 5 casts; no visual and no word in it.
- **The rest follow a third of a second apart**, each behind a `[20, target, me, 855]`:
  +0.328 and +0.667 s, +0.328 and +0.659 s after the E5 (4 of 4 later daggers). The `0x00E3`
  comes at the aftercast (+0.760), as ever.
- **Every arrival** is `0x00A7 [me, handle, 11]` -- earth, the spell's own type (§34) -- then
  `[20, target, me, 855]` (the record's `+0x84` impact visual), then the word; the chain's
  `0x005C [me, target, 1]` ("counts as a lead attack": the client's `combo` 1) rides the FIRST
  landed dagger between its visual and its word, 5 of 5, and no other.
- **A dagger reaching an aim its target has left misses:** `0x00A7` then a ground
  `0x00A1 [aim, 0, me, 855, 0, 0]` and no word (2 of 17). The aim is the target's position at
  the launch (the wiki: a trajectory "leading" the target, dodgeable by a change of direction).

A body's spell shot is the same shape from the announcement side: `[60, body, target, skill]`
at the cast start, then at the activation (Fireball +1.487..1.52 s, Orb +2.0, Javelin +1.0)
one batch of `[55, the energy]`, `[58, body, 0]`, the `0x00A4` (77 of 77, `arrow` 0 on all
94); the arrival `0x00A7 [body, handle, the spell's kind]`, `[20, target, body, impact]`
(404 for the Orb, 344 for Fireball), the word -- the Master of Lightning's Orb onto the owner,
11 of 11. Fireball's AoE adds two ground `0x00A1` at the aim (344 with the caster, 333 without)
and a word + `[20]` per foe reached, word first.

**The speed, OBSERVED, a round number per projectile.** `weaponcensus.spell_speeds` (new): the
`0x00A4` aim's distance from the shooter over the launch's own f32 flight, the shooter's
position its latest own `0x0029` point or the destination of a `0x002A` walking somebody to
it, held until the shooter's own next movement message (a standing caster's is good for a
minute; a walker's goes stale as it walks -- a one-second cutoff, tried first, threw away the
Master of Lightning's four standing Orbs and kept 65 u walk-ups). Fireball's 343: **1800 u/s**
on 17 of 23 positioned shots at 85..1166 u (the six others are three degenerate 1 u self-aimed
shots and three walking casters' stale positions: 1588 / 1677 / 1179). Lightning Orb's 403:
**1800** on 13 of 13 (the Master's four at 732..893 u off his own point 40..130 s old, and
nine on `20260917T224104`). Lightning Javelin's 405: **1200** on 9 of 9. Dancing Daggers' 854:
**1200** on 2 of 2 -- the owner's own casts, agent 36 walked to (18373.8, −3595.3) where the
caster stood, daggers 2 and 3 aimed 571.6 and 660.5 u away and flew 0.476 and 0.550 s. The
client's bonus slot on these rows (1800 on 194 / 186 / 229 / 858, the value §35 met while
reading the penetration slot) is **not** the speed: the Daggers fly at 1200 with 1800 in
theirs. Flare (194) was never cast on a live tape; 343 is its record's projectile and
Fireball's, and the id's speed is taken as the projectile's -- the table's one RECONSTRUCTION.
`content/world.toml [spell_projectile.speed]`, `source = "capture"`.

**What ships.** `authsrv.spell_shot_how(skill_id)` -- the record's `+0x88` projectile, flag 0,
the spell's own type as the arrival's kind (14 when its row names none), the table's speed;
None for a spell with no projectile (Lightning Strike, Mind Burn: they land at the E5 as
before), for one no tape has timed, for an attack skill, under `--no-spell-projectiles` or
`--no-projectiles`. In the E5 block the standalone branch launches instead of landing:
`launch_player_spell_shot` sends the first `0x00A4` in the E5's batch (behind the 58, ahead of
the hold pulse) and queues the rest an interval apart (`spell_projectiles`: the row's
`projectiles` / `projectile_interval` -- Dancing Daggers 3 at 0.333, its new `skill_effect`
row, which also carries `Earth damage` / `damage_type = 11`); `spell_queue_tick` (from
`projectile_tick`) sends a queued one behind its `[20, target, me, impact]`; `combat_deadlines`
wakes for a queued launch; `land_player_spell_shot` at the arrival sends the impact visual,
advances the chain on a lead-counting spell's first landing (`0x005C` between the visual and
the word), then lands the spell's own amount through `hit_enemy(exact=…, armed=True)` -- armed
because a landing takes no swing-interval gate (three daggers land inside 0.7 s; the E5's own
exact hit kept the gate and keeps it on the revert arm). `weaponcensus.spell_speeds` is the
extractor. `--no-spell-projectiles` reverts.

**Tests.** `test_weapons.py` section 24 (12 checks, floor 208 → 219; a vault run 234 -- the
tapes' speeds are the one vault-only check): the speed table and Dancing Daggers' row;
`spell_shot_how` on injected rows (Flare 343 / 1800 / fire, the Daggers 854 / 1200 / earth;
nothing for Lightning Strike, an attack skill, an untimed projectile, an unknown skill, or
either flag); through the real press, E5 and `projectile_tick`: Flare's E5 batch is E5, 58,
ONE `0x00A4` [me, the target's position, 0, 0.5 s at 1800, 343, handle 1, flag 0], the hold
pulse -- no word, no visual, the shot a deadline; the arrival `0x00A7 [me, 1, 5]`, `[20, foe,
me, 344]`, the one word; the Daggers' E5 launches one and queues two 0.333 s apart, the two
leave behind their `[20, foe, me, 855]` with handles 2 and 3, the three arrivals each `0x00A7`
[me, h, 11] / visual / word with the chain's `0x005C` on the first only; the revert; the source
locks; and the tapes through the extractor -- every positioned Daggers, Orb and Javelin launch
within 2 % of the table, Fireball's on at least fifteen and seven in ten.

**Left.** A BODY's spell projectile (W6's spell half: 77 body shots on tape; a body's
completion still lands the damage in its batch); the dodge (a projectile reaching an aim its
target has left -- the arrows do not model it either); Fireball's splash and ground visuals;
the Javelin's line; a Flare cast by the owner on a tape -- RUN-WEAPONS-1B's wand can cast one
at the suit (§6): predicts `0x00A4 343` at 1800 u/s in the E5 batch and the word at the
arrival.

## 37. A body's spell projectile -- 2026-09-20: W6's spell half -- the completion launches it, the arrival lands it

**What §36 left.** The player's projectile spells fly; a body's Fireball, Orb or Javelin still
landed its word in the completion batch, against the wire's 77 body shots.

**The shape, OBSERVED (77 of 77).** `[60, body, target, skill]` at the cast start; at the
client's own activation -- 75 of 77 launches within 50 ms of it: Fireball's 1.5 s (35 of 35),
the Orb's 2.0 s (26 of 27), the Javelin's 1.0 s (14 of 15; the two outliers a mid-cast
re-announce at 1.019 and a 0.5) -- one batch of `[55, the energy]`, `[58, body, 0]` and the
`0x00A4 [body, aim, 0, flight, PROJECTILE, handle, 0]`; a flight later `0x00A7 [body, handle,
the spell's kind]`, `[20, target, body, IMPACT]` (404 for the Orb, 344 for Fireball), the
word -- the Master of Lightning's Orb onto the owner, 11 of 11 on `20260917T090355`. Fireball's
AoE adds two ground `0x00A1` at the aim (344 with the caster, 333 without) and a word +
`[20]` per foe reached. No body cast a several-projectile spell on any tape.

**What ships.** `land_skill` computes nothing for a projectile spell at the completion: it
sends its 58 and the caster's visual, then `launch_body_spell_shot` (the first `0x00A4` in
that batch, the rest queued through `body_spell_queue_tick` an interval apart, each behind
its `[20, target, body, impact]` -- the player's shape, RECONSTRUCTION for a body), then the
effect, the condition and the heal as ever, and the ordinary exit. The word rides the flight:
`land_body_spell_shot`, from `body_projectile_tick`, computes the terms against the taker AS
IT STANDS AT THE ARRIVAL -- its armour against the spell's own type and penetration (§34 /
§35), its casting penalty, the caster's strike level, its own episodes, the whole-point word
-- BEFORE the `0x00A7` goes out (the refusal contract: nothing on the wire behind a refused
fraction), then `0x00A7`, the impact visual, the player's adrenaline gain, the word; a
target dead in flight gets the `0x00A7` and nothing else. The terms and the word are factored
out of `land_skill` into `body_spell_terms` / `body_spell_word` so the completion path and the
arrival share one computation; `--no-spell-projectiles` reverts both halves. A hostile's Orb
now lands the spell's 60 against the pieces' 19 (the 25 % came off) at the caster's strike
level, a flight later, exactly the number the completion dealt before -- only the instant and
the batch moved. NOT MODELLED, said here: Fireball's splash and ground visuals (a body's spell
lands on ONE target, as `land_skill` always has), the dodge, a body's energy word (`[55]`) at
the completion.

**Tests.** `test_weapons.py` section 25 (9 checks, floor 219 → 228; a vault run 244): through
the real `land_skill` and `projectile_tick` -- a hostile's Orb completes as `[58, it, 0]` then
ONE `0x00A4` [it, the player's position, 0, 0.5 s at 1800, 403, handle 1, flag 0], no word, no
visual, the caster released, the shot a deadline carrying the spell's 60 as lightning; the
arrival `0x00A7 [it, 1, 4]`, `[20, me, it, 404]`, the word for 60 against 19 at the caster's
strike level; a body's Daggers complete with one 854 and two queued a third of a second apart,
the two behind their `[20, me, it, 855]`, three arrivals each `0x00A7 [it, h, 11]` / visual /
word against 25; a target dead in flight is closed and takes nothing; the revert lands the
word behind the 58; Mind Burn (no projectile) lands at the completion as ever; the source
locks; and the tape -- every Orb launch on `20260917T090355` leaves 2.0 s after its announce
and every Javelin 1.0 s. `test_guards`' caller walk gains the three body-side helpers.

**Left.** Fireball's splash (35 of the 77 are Fireballs, each reaching one to three foes with
its two ground visuals); the dodge for every projectile; the `[55]` energy word a body's
completion carries; the bonus penetration tier (item word 574).

**2026-09-22 (DESKWORK-D5 3(c), read and NOT shipped).** "The `[55]` energy word" is a
mislabel: property 55 is the health-gain channel everywhere else in this repo, and the
body's energy word on the tape is **property 62 on `0x00A2`**, `[62, body, −cost/max]`. It
is **hero-scoped** — 17 of the 48 hero completions on `20260914T005758` carry
`[62, hero, −0.25]` (5 energy over a 20 pool), and 0 of 373 hostile prop-60 cast batches carry
a `[62, hostile]` (the 25 `[62]`s in those batches are the observer's own) — so a HOSTILE's
completion needs nothing. And its placement is not one rule: for the stance 346 (instant,
E4/E5/E3 in one batch) the word rides that batch 17 of 17; for the attack skill 322 it rides
the E4 batch 1 of 11 and a batch of its own 10 of 11. The hero's energy word is therefore
recorded, not sent: which batch carries it for a cast with an activation, and where in the
batch, is the question a hero tape with a 1 s spell would answer.

## 38. Fireball's splash -- 2026-09-20: a burst at the aim -- the explosion, then a word and an impact per foe

**What §37 left.** A body's Fireball flew and landed on ONE target; the tape's 35 Fireball
arrivals each reach one to four foes with two ground visuals at the aim.

**The record marks a burst.** The `s_skill` target byte is 16 on 34 rows, every one with an
`aoe_range` -- Fireball's 240, the wiki's "nearby" (GWW "Area of effect": nearby is 252
gwinches, fifteen named skills at 240; the client's own column is what the server bursts
over, 12 under the wiki's word). Flare's 156 is its Overcast adjacency and its byte is 5: one
target. So `spell_area(skill_id)` is the radius when the byte is 16, else None.

**The shape, OBSERVED (35 of 35, `20260817T231139`, four casters).** `0x00A7 [caster, handle,
5]`; then the IMPACT (`+0x84`, 344) -- `[20, target, caster, 344]` when the ball connected with
its target (14 of 35), else on the GROUND at the aim, `0x00A1 [aim, 0, caster, 344, 0, 0]` (21
of 35: the target had moved; the Daggers' miss in §36 draws the same); then the EXPLOSION,
`0x00A1 [aim, 0, 0, 333, 0, 0]` (35 of 35 -- 333 sits in no column of the 164-byte record,
whose caster visual is 332 and impact 344, so the row carries it as `area_visual`, capture);
then, per foe inside the radius of the aim (1 foe on 15 arrivals, 2 on 11, 3 on 8, 4 on 1; the
announced target among them 31 of 35), the word then `[20, foe, caster, 344]` -- word FIRST
here, where a single-target spell's visual precedes its word (§36 / §37). Each foe's number is
its own: three different fractions in one burst on the tape. `0x00A1` (`GAME_SMSG_0161` in the
schema: vec2, word, agent, word, byte, byte) is the client's effect-at-a-point message; this
server had never sent one.

**What ships.** Both launchers remember the AIM (the target's position at the launch);
`foes_within(state, caster, point, radius)` (a hostile's foes are the player, first, and the
party's bodies; the player's or a party body's are the hostiles; the dead and the caster
never); `send_ground_visual` (`0x00A1`); `land_body_spell_area` -- every foe's terms first
(refusable, nothing sent), then the `0x00A7`, the impact on the target when it stands inside
the area else on the ground at the aim (RECONSTRUCTION: the tape's hit test is finer), the
explosion, then per foe its word (the player through its pool, a body through
`hurt_agent_row`) and its `[20]`; `land_player_spell_area` the same through `hit_enemy`'s
`exact` per hostile. Fireball's `skill_effect` row (`Fire damage`, type 5, `area_visual` 333)
lets the player's and a body's Fireball deal at all. `--no-spell-areas` reverts to one target.
NOT MODELLED, said here: the finer target-or-ground test, the scatter (a single-packet burst
causes none, WIKI), a foe's movement between the launch and the arrival (the rows are read
as they stand at the arrival), a moving target's lead.

**Tests.** `test_weapons.py` section 26 (9 checks, floor 228 → 237; a vault run 254 -- the
tape's bursts are the one vault-only check): the row and the reader (Fireball 240, Flare and
the Orb one target, the flag); `foes_within` on a mixed field (the player and the monk 110 u
off, not the body 400 u off; the hostiles beside the archer, not the far or the dead one, never
the caster; a dead player unreached); through the real `land_skill` and `projectile_tick` a
hostile's Fireball at the player bursts as `0x00A7` / the impact on the player / the explosion
at the aim / the player's word and `[20]` / the monk's word and `[20]`, each its own number,
the far body untouched; with the player 600 u from the aim the impact goes on the GROUND with
the caster's id and only the monk is worded; the player's own Fireball through the press and
the E5 bursts over the target and the hostile 50 u beside it, 60 each, the far one untouched;
the revert is the Orb's single-target shape; the source locks; and the tape: every fire
arrival with an explosion draws the 333 with no agent, the impact on the ground with the
caster's id on at least fifteen and on the target on at least ten, and every worded foe gets
its `[20]`.

**Left.** The finer hit test (target or ground -- 14 / 21 on the tape) and the dodge it
implies, for every projectile; the scatter; the `[55]` energy word; the bonus penetration
tier (item word 574). Of the 34 target-16 rows only Fireball and 193 (Phoenix) are
projectiles; the other 32 are point-blank bursts at the target with no flight
(Aftershock, Shock...), which land through the completion's single-target path today and
would take the same `foes_within` at the target's position -- a rung of its own.

## 39. The hit test -- 2026-09-20: the aim leads the target, a target off the aim at the arrival dodges

**What §36-§38 left.** Every projectile connected wherever its target had gone; retail's
impacts land on the target or on the ground, and an arrow that finds nobody draws a word.

**The mechanism, WIKI.** GWW "Projectile": "A projectile's trajectory is calculated based on
the location and velocity of the target at the time of fire, automatically 'leading'
targets. Projectiles can be dodged by changing speed or direction after they are fired."
GWW "Line of sight": *Dodge* -- "if the target kites (changes direction), causing the
projectile to land in the place where the target would have been"; beside *Obstructed* (a
barrier at the launch) and *Stray* (the target moving toward an obstructed place), neither
modelled; and the practice ground it names is the Isle's Master of Lightning, RUN-1B's caster.

**The shapes, OBSERVED.** An arrow that reaches its aim and finds no target draws the
attack-fail word with reason 1 behind its `0x00A7`, and nothing else: every reason-1 word in
the live corpus rides a `0x00A7` of its attacker in the same instant -- 7 of 7, on four tapes
(`20260913T210901`, `20260914T005758` ×3, `20260914T180058`, `20260921T172025` ×2) -- and none
of the 57 reason-3 words does (the Blind tape's swings). A spell draws its impact on the
ground at the aim, `0x00A1 [aim, 0, caster, impact]`, and no word (the Daggers, 2 of 17,
§36). A burst still explodes and words whoever stands in its area (Fireball: 21 of 35 impacts
on the ground, 31 of 35 announced targets worded, §38).

**The geometry is NOT measurable from the tapes, and two readings were tried.** (1) "A course
change in flight" -- a movement message for the target between the launch and the arrival
(its own `0x0029`, a walk to it, a halt, a speed change; the owner's `0x003E` / `0x0047`)
against the outcome: REFUTED outright. Fireball: 7 misses with no such message and 5 hits
with one; the Daggers: 7 hits with one; a following body steers silently, so the messages
never were the motion. (2) The target's distance from the aim at the arrival, off the
nearest position sample (a walk-to destination naming it, or the owner's own stop position)
within a third of a second: direct hits read 0..104 u and misses 0..140 -- a walker covers 86
u in that third of a second, so the samples cannot bracket a tolerance of tens of units. The
two numbers below are therefore OURS, said so, and RUN-1B measures them.

**What ships.** `track_velocities` (the world tick keeps every body's and the player's
velocity as a finite difference of its model position over `VELOCITY_WINDOW` = 0.25 s; a
stander reads 0, a stale gap 0); `led_aim(shooter, target, velocity, speed)` -- the target's
position plus its velocity times the flight, the flight refined once against the led point --
in both launchers, so the `0x00A4`'s aim IS the led point (a stander is aimed at where it
stands, and hit there, as every test before today assumed); `projectile_connects(state,
shot)` at the arrival -- the target within `DODGE_TOLERANCE` of the aim, 24 u = rA + rB, the
two body radii the client's own follow-stop adds (`BOUNDING_RADIUS`, 12 u, what every
`0x0020` carries; RECONSTRUCTION as the hit radius). Not connected: the player's or a body's
arrow, plain or a skill's, sends `[38, target, attacker, 1]` (`agents.ATTACK_FAIL_DODGE`)
behind the `0x00A7` and nothing else -- no strike, no gain, no condition; a single-target
spell sends its impact on the ground at the aim and no word; a burst's impact goes on the
ground and its area words stand (`send_area_impact` takes the connect test's verdict, not
"inside the area", §38 corrected). `--no-dodge` reverts: the aim is the target's position,
every projectile connects.

**Tests.** `test_weapons.py` section 27 (14 checks, floor 237 → 251; a vault run 269 -- the
corpus's dodge words are the one vault-only check): the numbers; `led_aim` (a target 600 u
off walking across at 288 u/s aimed 97 u ahead; a stander, no speed, the flag); the trail (72
u in a quarter second reads 288 u/s, nothing inside the window, across a stale gap, for an
unknown id, or off); `projectile_connects` (0 / 20 / 24 u hit, 25 / 30 dodge, the flag, no
aim); through the real launch and tick: the player's arrow at a walking hostile aims at the
led point and the flight runs to it, the hostile that kept its course is hit 10 u from the
led point, the one that turned 60 u off draws `0x00A7` then `[38, foe, me, 1]` and no word,
`--no-dodge` neither leads nor misses; a hostile archer's arrow at the player who stepped 60 u
off draws `[38, me, it, 1]`, and at the player walking toward it leads the flight and lands
where the player arrives; the player's Flare at a hostile 100 u off the aim draws
`0x00A1 [aim, 0, me, 344]` and no word, a body's Orb at the player 80 u off the same with the
caster's id; a Fireball whose target stepped 100 u off but stands inside the area draws the
ground impact, the explosion and the player's word; the source locks; the corpus: every
reason-1 word rides its attacker's `0x00A7` (at least seven, none without) and no reason-3.

**RUN-WEAPONS-1B, the Orb block (§6).** Stand in the Master of Lightning's range and take
five Orbs standing (predicts five `[20, me, him, 404]` impacts, the aim = the stop position);
then walk a straight line across his front at run speed under five more (predicts the aim
ahead of the position at the launch by 288 u/s × the flight -- the LEAD -- and five impacts on
the body); then sidestep at each launch under five more (predicts `0x00A1 [aim, 0, him, 404]`
on the ground and no word; the tolerance brackets from the smallest step that missed and the
largest that hit, the client's own move-to coordinates giving the position). The Javelin
(1200 u/s, a longer flight) sharpens the lead's reading.

**Left.** *Obstructed* and *Stray* (line of sight); the lead's own error on a body whose
model steers between samples; the `[55]` energy word; the bonus penetration tier (item word
574).

## 40. A point-blank burst -- 2026-09-20: no flight -- every foe around the target, at the completion

**What §38 left.** The record's target byte 16 marks 34 rows; two fly (Fireball, Phoenix --
§38's flight and burst). The other 32 landed on one target.

**What the 32 are, by the record.** Seven are HEXES on an area (type 4: Panic 52, Soothing
Images 56, Suffering 108, Shadow of Fear 136, Rust 204, Ice Spikes 211, Deep Freeze 234).
Fifteen are areas over TIME -- a duration in the record, ticking at a point: Chaos Storm 77,
Eruption 167, Meteor Shower 192, Searing Heat 196, Fire Storm 197, Maelstrom 215, Ray of
Judgment 830, Churning Earth 844, Spirit Rift 910, Unsteady Ground 1083, Breath of Fire 1094,
Sandstorm 1372, Savannah Heat 1380, Snow Storm 2222. Ten are SINGLE-PACKET bursts -- a spell
(type 5) with no projectile and no duration: Desecrate Enchantments 112, Enfeebling Blood 118,
Plague Sending 149, Feast of Corruption 151, Earthquake 170 (240), Meteor 187 (156),
Rodgort's Invocation 189 (240), Ravenous Gaze 862, Searing Flames 884, Defile Enchantments
1070, Dragon's Stomp 1086 (240). WIKI (GWW "Point blank area of effect"): "a small area of
effect from the location of the user or a target, which does not persist over time"; GWW
"Earthquake": "You invoke an Earthquake at target foe's location. All foes near this location
are knocked down and are struck for 26...100 earth damage."

**The corpus has no witness, and says so.** Over every live tape, every prop-60 announce and
every owner's E5 of a target-16 skill: **Fire Storm, 17 casts, and nothing else** -- an area
over time (its completion batch is `[55 the energy]`, `[58, caster, 0]`, a ground `0x00A1
[point, 0, 0, 350, 0, 0]`, and then ticks once a second at the point with no 58 of their own,
spellhitjoin's "tick" rows). That is a mechanism of its own -- a lasting area with a ground
effect and the scatter it causes (WIKI "Area of effect") -- and NOT built here. A
single-packet burst was never cast on retail in front of this project, so its wire shape is
**RECONSTRUCTION: Fireball's arrival without the flight** (§38): the 58 (a body) or the E5
(the player), then per foe inside the radius of the TARGET's position the word then `[20,
foe, caster, impact]`, the skill's condition and its knock-down on each. Test §28 locks the
absence: the day a burst appears on a tape the lock reddens and the shape gets checked.

**What ships.** `spell_burst(skill_id)` -- the record's `aoe_range` when the target byte is
16, the type byte 5, no projectile and no duration; else None (a projectile burst flies, an
area over time and an area hex stay one target). The player's E5 standalone branch bursts
through `burst_player_spell` (every hostile within the radius of the target's position:
`hit_enemy`'s `exact`, the impact `[20]`, the knock-down and the condition on each landed,
living foe; the block's own condition then stands down). A body's `land_skill` computes every
foe's terms BEFORE its 58 (the refusal contract) and hands the words out at the end through
`burst_body_spell` (the player through its pool, a body through `hurt_agent_row`, each with
its `[20]`, its knock-down and its condition). Earthquake's `skill_effect` row (`Earth damage`,
type 11, `knocks_down`) is the server's one usable burst, on both sides. The same
`foes_within`, the same flag: `--no-spell-areas` reverts to one target. NOT MODELLED, said
here: the fifteen areas over time and the seven area hexes; Earthquake's overcast; line of
sight.

**Tests.** `test_weapons.py` section 28 (6 checks, floor 251 → 257; a vault run 276 -- the
corpus's target-16 announces are the one vault-only check): `spell_burst` on injected rows
(Earthquake 240, Meteor 156; Fireball flies, Fire Storm lasts, Panic is a hex, Flare is one
target, the flag); Earthquake's row; through the real press and E5 the player's Earthquake at
a hostile with a second one 50 u beside it lands a word then a `[20, foe, me, 304]` on each,
60 each, both knocked down, the one 400 u off untouched, nothing in the air; through the real
`land_skill` a hostile's Earthquake at the player lands `[58, it, 0]` then the player's word
(against the pieces' 25 at its strike level) and `[20]`, the monk's word and `[20]`, both
knocked down, the far body untouched; the revert lands one word with no visual and no
knock-down; the source locks; and the corpus: of the record's target-16 skills the only one
ever announced on a live tape is Fire Storm.

**RUN-WEAPONS-1B (§6).** The Suits stand ~150 u apart in a row: a hero with Earthquake
casting at the middle Suit predicts `[58, hero, 0]` then a word and a `[20, suit, hero, 304]`
per Suit within 240 u (three), word first -- the burst's shape on retail, at last.

**Left.** The areas over time (Fire Storm's seventeen casts are the witness: the ground
effect 350, the once-a-second ticks, the scatter); the area hexes; line of sight; the `[55]`
energy word; the bonus penetration tier (item word 574).
