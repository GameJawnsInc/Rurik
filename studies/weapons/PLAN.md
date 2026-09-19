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
| **RUN-WEAPONS-2** range | per weapon: stand far, press attack once, let the character walk in; repeat uphill if the Isle allows | Q4 — the distance from shooter to the aim point at the FIRST launch is the range, no free parameter; **and Q16 (W2b's client half): does the character STOP at range on its own press, and do the flights hold across swings** | 1004 / 1498 / 1498 / 1273 / 1273; 1248 staff and wand; 1004 spear; the body stands after the first start |
| **RUN-WEAPONS-3** damage (later, needs the right attributes) | met vs unmet requirement on one weapon; a scythe's criticals; hornbow vs longbow on the 100-armour suit | Q10, Q5's critical, W4's penetration | written when W4 opens |

## 7. Open questions

| Id | Question | Instrument |
|---|---|---|
| WEAPONS-Q1 | ~~`0x00A4` field 5 vs the item's `617`~~ **closed §9: 37 of 37; no `617` → 143.** Left: the two arrows with field 7 = 0 | desk |
| WEAPONS-Q2 | Which `609` value is which bow class? **Narrowed §9: 1 and 3 are the two 2.475 s classes** | RUN-1B (`0x0035` alone) |
| WEAPONS-Q3 | Projectile speed per class — is flight distance ÷ a constant, and does the arc change it? | desk where positions are known, RUN-1B |
| WEAPONS-Q4 | Range per type in units, and what height does to it | RUN-2 |
| WEAPONS-Q5 | Scythe: duration, how extra targets appear on the wire, the critical's size | RUN-1A |
| WEAPONS-Q6 | Spear: duration, projectile id, arrow flag, with and without a shield | RUN-1A |
| WEAPONS-Q7 | A hostile's repeat delay (1.75 / 1.90 / 1.985 / 2.125) | monsterai, desk |
| WEAPONS-Q8 | ~~Which message names the OBSERVER's own weapon type~~ **closed §9: `0x006E` (and `0x0147`)** | — |
| WEAPONS-Q9 | ~~What `634` beside every `633` holds~~ **closed §9: the required weapon's damage range (max, min), in place of `584`** | — |
| WEAPONS-Q10 | The unmet-requirement term — weapon, shield, focus | RUN-3 |
| WEAPONS-Q11 | ~~Does GWW's critical formula reproduce the five measured rates?~~ **closed §17: NO — 8 / 9 / 11 / 13 / 14 % predicted against 6 / 16 / 19 / 24 / 34 % measured; the table stays the measurement** | — |
| WEAPONS-Q12 | Is ×1.2 already inside the isle study's PvP-weapon numbers? | desk, then RUN-3 |
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
the shield's `572` armour is W4's with `587`.

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

**Not here.** Ignite Arrows' adjacency splash (named since the preparation landed); a
preparation on a BODY's bow (`body_ranged` reads no episode) — §20; which element each
`587` id names beyond fire = 5.

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


