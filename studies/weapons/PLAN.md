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
weapon's damage type has no reader, and a focus gives no energy. The dagger arc showed
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
| damage | `swing_damage` — item's `584` range, mastery rank with threshold, measured five-point critical table, critical = max at armour −20 | 633 never read, no unmet term (by decision, isle), ×1.2 not shipped (by decision), `587` unread, caster weapons would scale on a mastery they do not have |
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

**WEAPONS-W3 — melee completions.** The axe row and item. The scythe: up to two more
foes in melee range of the target and within 180 of the player, each hit rolled and
worded on its own (wire shape is Q5 — one start and how many `[1]` / 46 / words), and its
critical at 2^(5/40) if Q5 confirms GWW. The sword's short gap after a skill's hit
(inherited from the dagger arc, 9 of 21) is tested here with `--swings` on the two sword
tapes — cross-tab the neighbours first.

**WEAPONS-W4 — damage by type.** Decode `633` and carry it on item rows; the unmet term
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

Anyone can wield any weapon, and timing, launch, flight, projectile and range do not
depend on meeting a requirement — so **one PvP character on the Isle of the Nameless
covers every clock in two sittings**, with weapons from the PvP equipment panel. House
rules stand: secondary account, human cadence, one client, the driver sends no input,
≤ 8 steps, F11 means one thing per run, predictions sealed first (`vault/plans/`), an
exposure floor and an abort written down.

| Run | Steps (each: equip, F11, 20 plain swings on a Master of Damage suit from one spot, F11) | Answers | Sealed predictions |
|---|---|---|---|
| **RUN-WEAPONS-1A** martial | axe · scythe on ONE suit · scythe on the three adjacent suits · spear · spear + shield | Q5, Q6, the 1.5 s clock, scythe wire shape and critical, the spear's projectile and flag | scythe and spear start→start 1.500, word / launch at 0.650; spear `0x00A4` field 7 = 1 |
| **RUN-WEAPONS-1B** bows and casters | shortbow · flatbow · longbow · recurve · hornbow · staff · wand, all from the same marked spot | Q2 (609 ↔ class), Q3 (speed per class — same distance, five flights), the 2.025 and 2.7 clocks | start→launch 0.9125 / 1.1375 / 1.250 / 0.775; flight ratios 0.59 : 0.88 : 0.59 : 0.40 : 0.59 |
| **RUN-WEAPONS-2** range | per weapon: stand far, press attack once, let the character walk in; repeat uphill if the Isle allows | Q4 — the distance from shooter to the aim point at the FIRST launch is the range, no free parameter | 1004 / 1498 / 1498 / 1273 / 1273; 1248 staff and wand; 1004 spear |
| **RUN-WEAPONS-3** damage (later, needs the right attributes) | met vs unmet requirement on one weapon; a scythe's criticals; hornbow vs longbow on the 100-armour suit | Q10, Q5's critical, W4's penetration | written when W4 opens |

## 7. Open questions

| Id | Question | Instrument |
|---|---|---|
| WEAPONS-Q1 | `0x00A4` field 5 is the item's `617` argument (33 of 34, §3) — what decides it when the weapon has no `617`, and the two arrows with field 7 = 0 | desk, W0 |
| WEAPONS-Q2 | Which `609` value is which bow class? | desk (interval + flight), then RUN-1B |
| WEAPONS-Q3 | Projectile speed per class — is flight distance ÷ a constant, and does the arc change it? | desk where positions are known, RUN-1B |
| WEAPONS-Q4 | Range per type in units, and what height does to it | RUN-2 |
| WEAPONS-Q5 | Scythe: duration, how extra targets appear on the wire, the critical's size | RUN-1A |
| WEAPONS-Q6 | Spear: duration, projectile id, arrow flag, with and without a shield | RUN-1A |
| WEAPONS-Q7 | A hostile's repeat delay (1.75 / 1.90 / 1.985 / 2.125) | monsterai, desk |
| WEAPONS-Q8 | Which message names the OBSERVER's own weapon type | desk, W0 |
| WEAPONS-Q9 | What `634` beside every `633` holds | desk, W0 (itemmods method: read it off a tooltip) |
| WEAPONS-Q10 | The unmet-requirement term — weapon, shield, focus | RUN-3 |
| WEAPONS-Q11 | Does GWW's critical formula reproduce the five measured rates? | desk |
| WEAPONS-Q12 | Is ×1.2 already inside the isle study's PvP-weapon numbers? | desk, then RUN-3 |
| WEAPONS-Q13 | The sword's short gap after a skill's hit (from DAGGERS §9) | desk, `timingjoin.py --swings` |

## 8. What this plan refuses

- **No wiki number becomes a pin.** Every §2 cell is a prediction; GWW disagreeing with
  itself on bows is the reminder.
- **No weapon clock is calibrated on a hostile** (C5).
- **No mechanism is built ahead of its wire shape**: scythe targets and stray / dodge wait
  for a tape.
- **No bulk item dump.** Item rows are built one per type from the owner's own tapes, by
  id, under the provenance gate's measurement rule.
