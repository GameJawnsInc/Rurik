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
wherever it stands. The hostile repeat-delay classes (WEAPONS-C5) are unmodelled. A bow
attack skill, for the player or a body, still lands through the cast path with no arrow.
