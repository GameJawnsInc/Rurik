# Daggers and the Assassin attack chain

**Arc opened 2026-09-17.** Read-only: the pinned client's skill table (build 38797), the
vault's live capture corpus (32 live captures, 89 connections), and GWW. No client was
launched and no server code changed. Labels are the repo vocabulary from
[studies/character/FINDINGS.md](../character/FINDINGS.md), plus WIKI per
`.claude/skills/browse-gw-wiki`.

**Identifiers.** `DAGGERS-F<n>` = a finding. `DAGGERS-B<n>` = a build step, a thing to do.
`DAGGERS-Q<n>` = an open question a capture must answer. Convention:
[studies/idents/CONVENTION.md](../idents/CONVENTION.md).

---

## 0. The result in one paragraph

Nothing in this repo modelled daggers beyond a 1.33 s interval row. Most of what an
Assassin needs turned out to be **already on disk**: the client's skill record carries the
whole chain grammar in two fields our extractor does not emit (what a skill *counts as*,
what it *must follow*) plus a weapon-requirement mask that gates every profession's
attack skills, and the owner's own 2026-08-19 tape is a level-3 dagger Assassin whose
wire shows the chain indicator message end to end. `0x005C`, which
[studies/newopcodes](../newopcodes/FINDINGS.md) traced through the client but could not
give a game meaning, is the combo icon on the target's health bar; and the single
property-38 "reason 2" in the whole corpus, which [studies/skills](../skills/FINDINGS.md)
§44.4 recorded as "a failed attack skill", failed **because it was an off-hand pressed on
a target with no lead on it**. What that corpus could not show — a dual landing, a double
strike, the Critical Strikes energy step, a re-lead — the owner captured the same day:
**RUN-DAGGERS-1, §6**, which answered all five questions, refuted two of this document's
own predictions, and turned up an attack skill's adjacent damage on the way.

---

## 1. The skill record — three fields (DAGGERS-F1..F3)

`toolkit/clientscan/skilltable.py` parses `combo` (+0x30) and drops it at emit; it does not
read +0x14 or +0x24 at all. The field NAMES are UPSTREAM (GWCA `Skill.h`: `combo_req`,
`weapon_req`, `combo`); the MEANINGS below are ours, each checked against something that
could have refuted it. The client is a second witness that +0x24 and +0x30 are what the
names say: `toolkit/clientscan/typenames.py` records that skill type 14 never reaches the
type-name switch — it is tail-called "with the weapon and combo fields, because an
attack's displayed name depends on the weapon and the chain slot".

Numbers in this section came from a one-off census over all 3,443 rows restricted to
`skilltable.player_corpus` (1,333 rows). **DAGGERS-B1 landed them the same day:**
`skilltable.py` emits all three, and `test_skilltable.py` §9 holds the joins below (and
went red once, usefully — see F3's last line).

### DAGGERS-F1 — `combo` (+0x30, u8): what the skill counts as. CORROBORATED.

`0` none, `1` lead, `2` off-hand, `3` dual. Census: profession 7 holds 12 / 15 / 10 rows at
1 / 2 / 3; **every other profession holds zero**, except one profession-0 row at 1. The
non-attack rows are the refutable part: WIKI says Iron Palm (786) "counts as a lead
attack", Mantis Touch (974) and Palm Strike (1045) count as off-hand, Sneak Attack (2116)
counts as lead — the table has 786 → 1, 974 → 2, 1045 → 2, and 2116 is the lone
profession-0 row. 858 (a spell, three projectiles) → 1.

### DAGGERS-F2 — `combo_req` (+0x14, u32): a BITMASK of what it must follow. CORROBORATED.

| bit | meaning | rows agreeing with GWW's "Must follow …" clause |
|---|---|---|
| `0x01` | must follow a **dual** | 781, 1033, 1643 — 3 of 3 |
| `0x02` | must follow a **lead** | 780, 975, 988, 1021, 1022, 1987, 1988 — 7 of 7 |
| `0x04` | must follow an **off-hand** | 775, 776, 777, 976, 986, 1019, 1020, 1634, 1986, 2135 — 10 of 10 |
| `0x10` | UNVERIFIED — one row (1636), n = 1 | — |

29 skill pages were joined by ArenaNet's own skill id (GWW infobox `id`), fetched
2026-09-17 through the MediaWiki API; **zero disagreements**, including the rows whose
clause is absent and whose word is 0 — every lead, and the off-hands 778, 989, 1635 and
1990, whose condition is a knockdown or an enchantment rather than a chain requirement. Note the bit order is
NOT `1 << (combo - 1)`: dual is bit 0. Outside profession 7 the word is 0 on every
player row. Two Assassin rows with the word set were not joined (784 → `0x02`, 973 →
`0x04`); nothing rests on them.

### DAGGERS-F3 — `weapon_req` (+0x24, u32): a weapon MASK. CORROBORATED by the attribute column.

| bit | weapon | witness (attribute id : rows) |
|---|---|---|
| `0x01` | axe | 18 : 19 |
| `0x02` | bow | 25 : 29, 23 : 4, 24 : 2 |
| `0x08` | daggers | 29 : 26, 35 : 5, 30 : 1 |
| `0x10` | hammer | 19 : 22 |
| `0x20` | scythe | 41 : 13 |
| `0x40` | spear | 37 : 19 |
| `0x80` | sword | 20 : 18 |
| `0xB9` | any melee (axe, daggers, hammer, scythe, sword) | 29 rows over seven attributes |
| `0x46` | any ranged; bit `0x04` is unwitnessed alone | 1 row |

One chain attack does NOT want daggers: 2116, the profession-0 lead, carries `0xB9` — a
chain can be opened with any melee weapon. The test's first draft claimed "every chain
attack wants daggers" and this row refuted it; the claim holds for the Assassin's own 32.

1,132 of 1,333 player rows carry 0. **The server has no weapon gate on an attack skill
today** (the readiness audit found none in `authsrv.py`), so this is a gap for the
Warrior too, not only for the Assassin.

---

## 2. The wire (DAGGERS-F4..F8)

All from `livewire.decode_conn` over the live corpus. The observer is profession 7 in 10
connections over four captures; it holds daggers in exactly one,
**`20260819T132414`** (connections 52606 / 55414), bar `[814, 783, 2, 858, 780, 952, 0, 0]`
(already read in studies/skills §36.10), attributes 29 → 2 and 30 → 1 off `0x003A`.

### DAGGERS-F4 — daggers are ItemType 32. OBSERVED.

`0x006D [agent, leadhand, offhand]` joined to the same tape's `0x0161`: the three bodies
whose `0x01BF` profession byte is 7 all hold item_type **32** in the lead hand and
**nothing in the off hand**. 23 sightings over five captures, hostiles included. So a pair
of daggers is ONE item in the weapon slot — the existing one-weapon path fits, and the
"second dagger" question does not arise on the wire. (`agents.WEAPON_TYPE_DAGGERS = 4` is
the client's `weapon_type` enum, a different space, UPSTREAM.)

### DAGGERS-F5 — the plain swing is the sword's swing at 1.33 s. OBSERVED.

`[4, attacker, target, 0]` then one damage word ~0.55-0.6 s later
(`swing_windup(1.33) = 0.565`). Clean swing-to-swing gaps 1.316-1.344 s, n = 9.
**Double strike: n = 0.** Over 34 plain swings by four dagger wielders no swing carried
two damage words; the sword control (12 swings) did not either, so the counter is
capable of reading 1 and was never asked to read 2. At Dagger Mastery 2 the WIKI rate is
6 %, so 13 observer swings expecting 0.8 is no evidence either way. → DAGGERS-Q2.

### DAGGERS-F6 — `0x005C [me, target, state]` is the chain icon. OBSERVED, 15 sightings.

[studies/newopcodes](../newopcodes/FINDINGS.md) sourced the handler: a no-op unless field
1 is the addressed player, field 3 bounded 0..3 by `GmAgentStatusDot`'s own assert, game
meaning UNVERIFIED with a rival ("an engagement state"). The rival is dead:

- every `state = 1` rides the **same batch** as a `combo = 1` skill (782 / 783 / 858)
  landing on that target — 7 of 7;
- one clean **1 → 2 → 0** (target 137, t = 254.797 / 255.343 / 255.607): state 2 lands
  with off-hand 780's damage word and its `0x00E5`;
- a target that lives keeps the icon **15.66 s** (`20260817T183756`, 335.638 → 351.298);
  the six short lifetimes (0.58-3.7 s) all clear in the instant of that target's `0x00F1`
  dead bit, 6 of 6. WIKI ("Dagger attack"): the icon "lasts for about 15s" and is "only
  visible to the player that initiated the attack chain" — which is the client's field-1
  gate, reached from the other side.

So state = the `combo` value of the last chain skill that HIT, per (attacker, target),
cleared by `0` on a ~15 s clock or the target's death. State 3 is n = 0. Whether a second
lead restarts the clock is n = 0 (no target was ever led twice). Whether a lead that
misses sets it is n = 0 (no lead ever failed). The newopcodes study counted 2 sightings;
it predates the 08-19 tape.

### DAGGERS-F7 — an unmet requirement is property 38, reason 2. OBSERVED, n = 1.

The observer pressed off-hand 780 five times. One press was on a target (217) with no
lead on it: `0x00E4` accept → property 50 → `0x00E5` + **`[38, 217, 27, 2]`** in one
instant, no damage word. That is the corpus's only reason-2, which skills §44.4 already
had and could not explain. Two armed presses connected (one advanced the state; one
raced the target's death); two were refused `0x00E2`.

**The whole batch, and it agrees with WIKI after all (n = 1).** WIKI ("Dagger attack"): a
failed chain attack uses "up the energy cost" and "Failed attacks do not cause the skill
to recharge". The first draft of this section called that CONTESTED, because the close
goes out and a re-press 1.5 s later was refused. Read against an armed press of the same
skill on the same tape, it is not:

| | unarmed, t = 236.134-236.303 | armed, t = 255.193-255.343 |
|---|---|---|
| at property 50 | `0x00A2 [62, me, -0.20]` — 5 of 25 energy | the same |
| at the landing | `0x00E5 [me, 780, 0, 3]` | `0x00E5 [me, 780, 0, 3]` |
| | `0x009F [46, me, 0]` | `0x009F [46, me, 0]` |
| | **`0x00A0 [38, target, me, 2]`** | `0x005C [me, target, 2]` |
| | **`0x00E5 [me, 780, 0, 0]`** | `0x00A3 [16, target, me, -0.1071]` |
| | `0x00E3 [me, 780, 0]` | `0x00E3 [me, 780, 0]` |

(The armed column's 46 was missing from this table's first cut: a `grep` pattern with a
leading space dropped every `[46,` line. `chainjoin.py`'s census has it on 25 of 25 landed
attack-skill hits.) The energy IS debited, and the recharge (3 s, the table's own `recharge`) is started
**and zeroed in the same instant by a second `0x00E5` whose last field is 0**. The
refused re-press was 0.4 s into skill 858's cast, not a recharge. → DAGGERS-Q3 is now a
replication, and asks the same of a failed DUAL.

### DAGGERS-F8 — NOT FOUND in the corpus

A dual attack by the observer (the only 1019 is a hostile's, and its target died 0.7 s
later); two damage words from one dual; state 3; a double strike; the Critical Strikes
energy step — the gain channel is float property 52 on `0x00A2` (`pools.py`), it never
fires on this tape, and it should not: the observer's one critical hit (property 17,
t = 254.797) was struck with attribute 35 at rank 0, where WIKI gives 0 energy.

---

## 3. WIKI rules the server will be built to, until a tape says otherwise

GWW, fetched 2026-09-17. All player-visible, so WIKI is strong here.

- "Daggers" (rev. 2026-03-08): two-handed, max 7-17, 1.33 s, piercing or slashing.
- "Double strike" (rev. 2026-09-09): 2 % inherent + 2 % per Dagger Mastery rank on a
  NORMAL attack; "Dual attacks automatically double strike, while all other attack
  skills are incapable of double striking."
- "Dagger attack" (rev. 2020-06-19): a dual hits twice, "applying the skill effects each
  time, and rolling independently for each strike"; "Failed dual attacks still cause two
  attacks, but none will hit."
- "Critical Strikes" (rev. 2026-07-16): +1 % critical chance per rank; energy per critical
  hit 1 / 2 / 3 / 4 from ranks 3 / 8 / 13 / 18.

---

## 4. Build steps

| id | step | rests on |
|---|---|---|
| **DAGGERS-B1** ✅ 2026-09-17 | `skilltable.py`: read +0x14 and +0x24, emit `combo`, `combo_req`, `weapon_req`; `test_skilltable.py` locks §1's censuses and the 29-row join (ids only — no names in the repo). `content.py` needs no change (no per-field allowlist for kind `skills`). | F1-F3 |
| **DAGGERS-B2** ✅ 2026-09-17 | A dagger item row (item_type 32, offhand empty), `WEAPON_TYPE_ATTRIBUTE` / `WEAPON_TYPE_RATE` entries, `PARTY_WEAPON_ITEMS["daggers"]` — a profession-7 party body cannot resolve a weapon today. | F4, F5 |
| **DAGGERS-B3** ✅ 2026-09-17 | `player_profession` on the `[party.*]` row; today only `--spawn-profession`, unwired to the row's attributes and weapon. | audit |
| **DAGGERS-B4** ✅ 2026-09-17 | Weapon gate on attack skills from `weapon_req`. What retail SENDS on a mismatch is unobserved — ship the refusal the server already uses (`0x00E2`) and label it RECONSTRUCTION. | F3 |
| **DAGGERS-B5** ✅ 2026-09-17 | Chain state per (attacker, target): set on a chain skill's HIT, `0x005C` to the attacker only, clear at 15 s or death; unmet `combo_req` → F7's batch verbatim: energy debited, `0x00E5` recharge, 46, `[38, target, me, 2]`, `0x00E5` 0, `0x00E3`; no damage, no state. | F6, F7 |
| **DAGGERS-B6** ✅ 2026-09-17 | Second strike: duals always, plain swings on the double-strike roll. Wire shape waits on Q1 / Q2. | §3 |
| **DAGGERS-B7** ✅ 2026-09-17 | Critical Strikes: crit chance + energy on a critical hit. Wire shape waits on Q4. | §3 |

B1-B5 needed no new capture; B6 and B7 were built the same evening on §6's shapes. `[party.daggers]` is the playable character: `--party daggers`. **DAGGERS-B8 ✅ 2026-09-17:** an attack skill's ADJACENT damage (F13), `--no-area-damage` the control.

---

## 5. Open questions — the capture

| id | question | why the corpus cannot answer |
|---|---|---|
| **DAGGERS-Q1** | A dual that lands: one property 50 and two damage words? how far apart? `0x005C` state 3, and when? | no observer dual, n = 0 |
| **DAGGERS-Q2** | A double strike on a plain swing: two damage words in one windup? does the next swing still start at 1.33 s? | 34 swings at rank ≤ 2, n = 0 |
| **DAGGERS-Q3** | A failed off-hand replicates F7's batch (energy debited, `0x00E5` recharge then `0x00E5` 0)? A failed DUAL: the same, and do its "two attacks" send two fail words? | n = 1 off-hand, n = 0 dual |
| **DAGGERS-Q4** | The energy step on a critical hit: which message, which batch? | wrong channel read; rank 1 gives 0 energy anyway |
| **DAGGERS-Q5** | A second lead on an armed target: a second `state = 1`? does the 15 s restart? Does state 3 persist 15 s, and does a lead after it go back to 1? | no target led twice |

The regime that answers all five is a **PvP Assassin on the Isle of the Nameless** —
Dagger Mastery 12 (26 % double strike, ~1 swing in 4), Critical Strikes ≥ 8, against a
practice target that does not die inside the 15 s clock, which is the confound that cut
six of seven lifetimes short in F6.

### RUN-DAGGERS-2 — registered 2026-09-17, NOT YET RUN (DAGGERS-Q6..Q9)

Q1–Q5 were answered by RUN-DAGGERS-1 (§6). What it left is what a foe that FIGHTS BACK
does to the chain; the plan is `vault/plans/daggers_n0.txt` (sha256 `41b9031a…`, eight
steps, F11 = "the icon changed" as before), against the **Master of Lightning** (E/W 20;
WIKI bar per `studies/skills` §49: Lightning Javelin, Lightning Orb, Blinding Flash, two
attunements, Aura of Restoration, Bonetti's Defense — he blinds, he blocks, he kills).
Sneak Attack (2116) is dropped: PvE-only, not on the account. The server's answer to each
is RECONSTRUCTION at the call site and is the prediction here.

| id | question | prediction | rival |
|---|---|---|---|
| **DAGGERS-Q6** | A lead whose word is `[38, T, me, 0/1/3]` (block / dodge / miss): is `0x005C` sent? does the off-hand behind it land? | no `0x005C`; the off-hand fails with F7's batch, reason 2 | the state is set at the PRESS; the off-hand lands |
| **DAGGERS-Q7** | A dual whose first strike is blocked: does `[47, me, 0]` and a second roll still follow at 0.5 s? is state 3 sent if only one strike lands? | yes, independent rolls (F10); state 3 only when the SECOND lands (it rides the second word) | either strike landing sets 3 |
| **DAGGERS-Q8** | The attacker's own death with an icon live on the foe; a cold off-hand after resurrection | `[me, T, 0]` in the death batch; the cold off-hand fails | nothing sent, the client clears its own icon, the clock runs out; or the off-hand lands |
| **DAGGERS-Q9** | Under an attack-speed boost (slot 5, if the account has Flurry / Frenzy): the double strike's and the dual's second word | still 0.500 s behind the first, a constant | scales with the swing, ~0.33–0.37 s |

Floor: ≥ 3 leads that did not land with an off-hand pressed behind each, and ≥ 2 that
did; ≥ 1 death with an icon live; ≥ 20 boosted swings with ≥ 2 doubles or Q9 is "not
exposed"; ≥ 1 cold press after resurrection. Scored by `chainjoin.py --capture`.

---

## 6. RUN-DAGGERS-1 — run and scored, 2026-09-17 (DAGGERS-F9..F13)

Capture **`20260917T160915`**, connection 52569, the owner's new PvP Assassin on the Isle
of the Nameless; plan `vault/plans/daggers_chain.txt` sealed and the seals AGREE. Dagger
Mastery 12 and Critical Strikes 8 off `0x003A`, 25 energy at rate 0.0528 (4 pips), PvP
Daggers 7-17 with no energy modifier (the owner's tooltip). The target was the **Master of
Damage** rather than a Suit — it revives itself — with two 480-health neighbours inside
adjacent range, which is what exposed F12. The owner's F11 marks are dense in step 3 and
thin after it; nothing below leans on them. Every number is
`python toolkit/authsrv/chainjoin.py --capture 20260917T160915`, pinned by
`test_daggers.py` §8.

### DAGGERS-F9 — the chain state: sent on a CHANGE, clocked from the LAST HIT. OBSERVED.

24 × `0x005C`: seven 1s, seven 2s, seven 3s, three 0s. **Q5's prediction was REFUTED in
half:** a second and a third lead on a target already at 1 (404.246, 412.539) sent **no**
`0x005C` — the message goes out only when the state changes — **but each restarted the
clock**: that target's 0 came **15.000 s after the third lead**, 31.442 s after the set.
All three clears are 15.000 s after the last chain hit, to the millisecond, and the
August tape's "15.66 s" is the same rule: its lead was 858, three projectiles, the last
landing 0.66 s after the first (corpus-wide 4 of 4, 14.996-15.000). State 3 lasts the same
15.000 s (2 of 2), and an off-hand that follows a dual puts the state back to 2.

### DAGGERS-F10 — the dual strikes twice, half a second apart. OBSERVED, 7 of 7.

Two batches. At the `0x00E5`: the recharge, 46, **the first damage word**. Then
**0.487-0.504 s later**: `0x009F [47, me, 0]`, **the second word**, the adjacent words
(F13), `0x005C [me, target, 3]`, `0x00E3`. **Q1's prediction was REFUTED in its detail:**
the state rides the SECOND strike, behind its word — where a lead's and an off-hand's
ride AHEAD of theirs. The rolls are independent (one dual is a plain word then a
critical). `[47, me, 0]` opens the second strike on 11 of 11, landed or failed — property
47 had no reading in this repo before today.

A COLD dual (4 of 4): `0x00E5` recharge, 46, `[38, target, me, 2]`, `0x00E5` 0 — then
0.499-0.510 s later `[47, me, 0]`, **a second `[38, target, me, 2]`**, `0x00E3`. WIKI's
"Failed dual attacks still cause two attacks, but none will hit", on the wire. The cold
off-hand replicated F7 8 of 8, its re-press accepted 0.36 s later: 12 cold presses, 12
zeroed recharges, energy debited every time (the owner saw the bar drop and the word
"fail").

### DAGGERS-F11 — the double strike. OBSERVED, 16 of 64 plain swings.

25 % at Dagger Mastery 12 (WIKI: 2 % + 2 % a rank = 26 %). The second damage word comes
**0.500 s behind the first** (0.478-0.511), opened by **`0x009F [2, me, 0]`** (16 of 16;
property 2 had no reading either). It has no bracket of its own — the close (1) rode the
FIRST word, 16 of 16 — and **the next swing is not delayed**: start-to-start p50 1.320 s
after a double against 1.329 s after a single. Independent rolls: 11 plain/plain, 4
critical/plain, 1 critical/critical. Half a second is one number at one weapon speed;
whether it scales with an attack-speed boost is n = 0.

### DAGGERS-F12 — Critical Strikes pays on 0x00A3, and draws a callout. OBSERVED, 26 of 26.

Every critical word of the observer's is preceded, in its own batch and in this order, by
**`0x00A3 [52, me, me, +0.08]`** and **`0x00A0 [54, me, me, 2]`** — 2 energy of 25 at rank 8,
WIKI's table. Q4 predicted the value and **got the opcode wrong**: the gain is on the
float-TARGET message with the observer in both agent slots, not on `0x00A2` where a
shrine's refill rides, and the first scoring pass reported "0 gains" because it looked
there. 54 is the floating "+2" `agents.PROP_ENERGY_GAIN_CALLOUT` already named. It is sent
with the pool full too (18 of 18 in the plain-swing minute, no skill pressed), so the server does not clamp the
message, only the pool.

### DAGGERS-F13 — an attack skill's ADJACENT damage is property 55. OBSERVED, 28 of 28.

The owner noticed Death Blossom hitting the neighbours. On the wire: beside each of a
landed dual's two words, **`0x00A3 [55, neighbour, me, -0.0833]`** to each of the two
adjacent foes — 28 words over 7 duals. −0.0833 is **40 of 480**, and 40 is Death Blossom's
20..45 at rank 12 exactly: the adjacent damage ignores armour, is never critical, and is
identical on both strikes, where the target's own word varies with the roll. Property 55
is the word this repo calls the heal; `test_mechanics.py` P1 ("positive in 97 %+") went
red on these 28 and is now judged without this tape, with a P1b that says what this
tape's negatives are.

**DAGGERS-B8, shipped 2026-09-17.** The RADIUS is the client's own: the skill record's
f32 at **+0x6C** (`aoe_range`; the name is UPSTREAM, GWCA). Over the player corpus its four
commonest values are **156, 240, 312 and 1000** — the game's adjacent / nearby / in the
area / earshot radii (WIKI "Area of effect" quotes 240 and 1000 verbatim, and "Range" puts
melee's 144 "slightly smaller than" adjacent) — and Death Blossom's is 156; the tape's two
neighbours stood 78 u and 94 u from the target, inside it. The AMOUNT fell out rather than
being typed: the client's interpolator on 775's scale slot at rank 12 is **40**, the tape's
−40/480. The maximum: `[42, neighbour, 480]` rides ahead of the FIRST adjacent word on each
body and none of the 13 after — hit_enemy's own "first hit declares" rule, which
`armour_ignoring_damage` now takes as `declare_max="stale"`. Opt-in per content row
(`adjacent_damage = "scale"`), because Cyclone Axe is "adjacent" too and is a different
mechanic. The player's strike only; an NPC's cast is still single-target.

**Beyond Death Blossom — what the corpus already holds (a census, not a build).** One
instant, one source, two or more damaged targets, over every live tape: 86 such instants,
73 of them on the PvP arena tape `20260817T231139` and all from **Fire Magic spells** —
186 (`aoe_range` 240, 31 instants of 2-4 targets), 185 (156, 25), 179 (a hex, 240, 9), 197
(156, 4) — on **property 16 with a DIFFERENT value per target** (e.g. −0.1766 / −0.0883 /
−0.1766 on three foes at one instant: one number over three maxima and three armours),
where Death Blossom's 28 adjacent words are property 55 and identical. So an area SPELL
is armour-respecting damage on the ordinary channel to everyone in the radius, and an
attack skill's adjacent damage is armour-ignoring on 55: two mechanics, both with the
radius on the skill row. 185 lands TWO words per target in the same instant (a two-packet
spell). Whether target byte 16 (186, 197) is a ground-target is unread. That is an
Elementalist arc's seed; nothing here builds it.

**On our own client, by the owner's hand, the same evening** (`--party daggers20 --enemies 3
--enemy-cluster 90 --enemy-health 2000`; the first try, `--enemies 3` alone, splashed
nobody — the ring puts neighbours 424 u and 600 u apart, which is what `--enemy-cluster`
is for): "it hit the aoe, ordinary damage numbers." So a NEGATIVE property 55 from the
player onto another body draws as an ordinary damage number on the client — the word
this repo calls the heal is, negative, just damage to the eye. OBSERVED by the operator,
no frame kept.

### What the run did not settle

A lead that MISSES (does it set the state?), a first strike that misses ahead of a double
or a dual's second, the attacker's own death, a chain opened with a non-dagger lead
(2116), and the half second under an attack-speed boost are all n = 0. The server's
answers to each are labelled RECONSTRUCTION at the call site.

---

## 7. On our own client — two scripted loopback runs, 2026-09-17 (DAGGERS-F14)

Harness `20260917T165523` (`--party daggers`) and `20260917T165940` (`--party daggers20`:
the retail run's ranks, Dagger Mastery 12 / Critical Strikes 8, on the same 1-3 daggers),
pin client 38797, map 280, `--enemy --practice-target --explorable`, the presses through
the harness's `skill:` mailbox (the real `handle_skill_press` arm, not a key). Both
reached the map, ran their whole plan and closed with **no assert, no crash dialog and
0 undecodable messages**; the gamesrv logs carry every step (checked BEFORE the frames).

OBSERVED on the client:

- the party panel reads **A3**, the energy bar **25 with four pips** — the profession knob
  and its derived pool are what the client believes;
- the bar's off-hand and dual icons carry the client's own small ✕ until a lead lands —
  the client judges the chain for DISPLAY by itself, from its own skill record;
- a landed Fox Fangs floats −16; a landed **Death Blossom floats TWO −26s, stacked**, with
  the skill's flash and a dagger in the raised hand (`walk17-skill775,10.png`);
- a critical draws a **magenta +2 over the player with the blue energy sparkle**
  (`w021.png` of the second run): `0x00A3 [52, me, me, f]` + `0x00A0 [54, me, me, 2]`,
  transcribed from retail, is what makes it. 8 criticals, 8 callouts, 3 double strikes
  (`[2, me, 0]` + a word) in 19 swings, none of it disturbing the client;
- the cold off-hand, the cold dual's two fail words, `0x005C` 1 → 2, the dual's `[47]`
  batch and the `0x005C` 0 riding the target's death all went to a live client.

**THE CHAIN ICON, by the owner's hand, the same evening** (`--party daggers20
--enemy-health 2000`, the target clicked, 1-2-3 on the bar): "confirmed on the health, the
3 icons, and the 15s fade." So `0x005C` states 1, 2 and 3 each draw their icon on the target
display's health bar of OUR client, and the server's 15 s clear takes it down. OBSERVED by
the operator, no frame kept. NOT reported either way: the silent re-lead (a second lead
changing nothing on screen while pushing the fade out).

NOT SEEN by the scripted runs, and why:

- **the chain icon itself.** It draws on the TARGET DISPLAY's health bar (WIKI), and the
  harness orders attacks without selecting the target client-side, so that bar was never
  on screen. `0x005C` reached the client and did no harm; whether the icon draws needs a
  hand-driven run with the target clicked — the owner's instrument.
- **armour.** The character was a bare Assassin body: the base fixture's Warrior armour
  rows draw nothing on it. **Closed at the desk the same night (DAGGERS-F15):** the five
  pieces the owner's own level-3 Assassin wore on 20260819T132414 are content rows
  (`[item.assassin_*]`, every byte retail's: files 0x800003B0-B4, models 7248-7252, the
  fixture's flags word, armour 10 each) and `[party.daggers]` / `[party.daggers20]` wear
  them through a new `player_armour` row key, validated slot by slot through wearmap at
  launch. The armour maths follows the set through one indirection
  (`agents.worn_piece_key`): the level-3 Assassin's chest rates 10 where the Warrior
  fixture's rated 45. **Seen on our client the same night** (harness `20260917T193532`,
  `--party daggers20`): the five pieces declared with no error and the body draws
  dressed — a green top, dark leggings, boots — where the earlier runs drew it bare
  (`walk3-shot.png`; a scripted run, so the tooltip's `Armor: 10` is unread).
  Two things fell out of the rows: the
  chest carries modifier 556 arg 5 and the boots and legs 558 arg 1 each -- +5 energy
  and +1 regen twice, which IS WIKI "Energy"'s Assassin row (+5 / +2 over the 20 / 2
  base) and the 0.0528 rate that character ran at, so the profession's pool is the
  ARMOUR's. `combatmath.armour_energy_bonus` now READS 556 / 558 off the worn set and
  `apply_party_character` compares 20 / 2 + the sum with what the row types — the
  `daggers` rows come out "pool 25/4 = the armour's", a disagreeing row prints why and
  keeps its numbers (the Warrior fixture's 25 / 3 is the Ranger row, typed before any of
  this was read, and its pieces carry neither word — left alone); and the PvP set of
  20260917T160915 shares four of the five files and wears a different head (0x800004E1).
- the first run's first chain was spent on a CORPSE — the Monk hero had killed the
  100-health target while the player plain-swung, the lead did not hit, and the off-hand
  behind it failed correctly. A press on a dead target is ACCEPTED here; what retail does
  with one is n = 0.

## 8. RUN-DAGGERS-2 — run and scored, 2026-09-17 (DAGGERS-F16..F19)

Live tape `20260917T224104`, the isle connection (`62557`), observer agent 25 — the same
PvP Assassin (Dagger Mastery 12, Critical Strikes 8) with **Frenzy (346) in slot 5**.
22 marks over the 8 sealed steps (`plan_seal.json`, sha256 `41b9031a…`), 8 F11s. The
owner used the **Master of Damage** (agent 70, agents 71 / 72 beside it) for steps 1–4
instead of the Suits, and the **Master of Lightning** (agent 117) for 5–7, and died to
him four times (367.057, 408.587, 446.688, 490.829). Owner's notes: the third F11 of the
control was Death Blossom catching the neighbours (property-55 words on 70 and 71 — the
same accident B8 was built on); step 3 was restarted twice; no F11 was pressed at the
deaths. Scored with `chainjoin.py --capture 20260917T224104` and a per-step timeline
(the timeline and Frenzy census scripts are scratch; the numbers below are theirs).

**Against the seal:** Q6 CONFIRMED (n = 1 miss, three landed pairs as its control);
Q7 half — the second roll after a missed first CONFIRMED, the state-3 discriminator
still n = 0; Q8 CONFIRMED 3 of 3 and 1 of 1 after the resurrection, the rival ("the
client clears its own icon") REFUTED; **Q9 REFUTED — the rival stands**, the half
second scales with the swing. The server changed twice (F18, F19).

### DAGGERS-F16 — a lead that does not land sets nothing. OBSERVED, n = 1 (+ 3 controls).

349.147, blinded: `0x00E5 [me, 782, 0, 2]`, `[46, me, 0]`, **`[38, 117, me, 3]`** (a
miss), `0x00E3` — **no `0x005C`**, the recharge KEPT (no second `0x00E5`, and the 2 s
`0x00E6` follows at 351.141: a miss is not a fail), the 5 energy debited. The Fox Fangs
pressed 0.55 s behind it: F7's batch to the byte — `0x00E5` recharge 3, 46,
`[38, 117, me, 2]`, `0x00E5` 0, `0x00E3`. The three pairs whose lead landed (357.240,
395.754, 442.328) set 1 and then 2 as in RUN-1. A blinded PLAIN swing closes and then
misses — `[1, me, 0]` then `[38, 117, me, 3]` (433.145, 434.310), the close riding a
miss exactly as `hit_enemy`'s Blind path already sends it. The server was already right
(the chain advances inside a LANDED hit only); the label moves from RECONSTRUCTION to
OBSERVED.

### DAGGERS-F17 — a dual whose FIRST strike misses still rolls its second. OBSERVED, n = 1.

443.448, Frenzy up: `0x00E5 [me, 775, 0, 2]`, 46, `[38, 117, me, 3]` — then **0.334 s**
later `[47, me, 0]`, a landed word (−0.1208), **`0x005C [me, 117, 3]`**, `0x00E3`. The
rolls are independent of each other for a miss as F10 found them for a critical, and
state 3 was set with the landed SECOND. The discriminating case — first lands, second
misses — did not occur (n = 0 still); `dual_second_strike` sets 3 if EITHER landed, which
both rivals predict here, and the Moebius readout was never reached (the owner died
2.9 s later, F18). No property-55 words on either strike: nothing stood adjacent to him.

### DAGGERS-F18 — the attacker's death clears the icon ON THE WIRE, behind the death bit. OBSERVED, 3 of 3.

The death batch, one instant, the same order three times (367.057 / 408.587 / 446.688):
`0x00A7 [117, 1, 4]`, `0x00A0 [20, me, 117, 404]`, `[10, me, 229]` (property 10 = the
foe's skill that hit, 229 / 230 on every hit he landed — which two Air Magic skills those
are is UNREAD), the killing word `[16, me, 117, −x]`, **`0x00F1 [me, 18]`**,
**`0x005C [me, 117, 0]`**, `0x009C [me, 85 / 70 / 55]`, `0x00EE`, `[8, me, 1]`,
`0x0044 [me, n]` (effect removals; on the third death Frenzy was up), `[7, me, 24]`,
`0x00F1 [me, 16]`, `[41, me, max energy]`, `[43, me, 0.0]`, `[42, me, max health]`,
`0x002D`, `0x0026 [me, 4]`. The icons were 9.303, 12.329 and 2.906 s old — nowhere near
the 15 s clock — so the 0 is the death's, and the rival (nothing sent, the client clears
its own icon) is refuted. After the resurrection a cold Fox Fangs on him (480.154) failed
with reason 2 and a zeroed recharge, 1 of 1: WIKI's "does not reappear if the user is
resurrected" is the server having nothing to reappear. **The server's clear moved**: it
rode ahead of the status; `kill_player` now sends it between `0x00F1 [me, 18]` and the
morale tick (test_daggers §5 pins the index). Where retail strips the EFFECTS — after
`[8, me, 1]`, between the morale tick and the maxima — is not where `kill_player` strips
them (first); n = 1 with an effect up, and it is a death-batch item, not a daggers one
— closed the same night as MORALE-Q8 (`studies/morale` §1.3: 11 of 12 deaths, the
hold and the strips between the morale pair and the maxima; `kill_player` reordered).

Two side readings off the same batches. **Death penalty scales the BASE pool and the
armour's +5 rides on top**: maximum energy 25 → 22 → 19 → 16 → 13 and health 480 → 408
→ 336 → 264 → 192 at morale 85 / 70 / 55 / 40 — `20 × m + 5` and `480 × m`, which is
`morale.py`'s model (`effective_max`), CORROBORATED 4 of 4 on one character where it
had n = 1. And Critical Strikes pays 2 over the CURRENT maximum: `[52, me, me, 2/22]`
and `2/19` after the first and second deaths (F12's 2/25 before them), with the
`[54, me, me, 2]` unchanged — `test_pools` 2f carries both rows.

### DAGGERS-F19 — the half second is a FRACTION of the swing. OBSERVED, 16 + 4 of 20.

Under Frenzy (`0x0042 [me, 346, 0, instance, f32 8.0]` at the press, `0x00E6 [346, 0]`
4.0 s later) the plain swing went from 1.33 s to **0.891 s** start-to-start (65 boosted
intervals: 51 at 0.877–0.910, 14 at 0.762–0.796; 15 plain ones: 12 at 1.326–1.335,
3 at 1.11–1.165) — 1.333 × 0.67, `attack_interval_factor`'s number. And the second
strike moved WITH it: the double strike's second word **0.320–0.339 s** behind the first
(16 of 16 boosted) against 0.499 / 0.499 plain on the same tape, the dual's
**0.333–0.342** (4 of 4: 254.750, 264.403, 300.545, 443.448) against 0.494 / 0.497.
0.334 / 0.891 = 0.375 = 0.5 / 1.333: the delay is **3/8 of the swing**, and Q9's
prediction (a constant) is refuted. 18 doubles in 81 swings (22 %, WIKI 26 at rank 12).
A sub-mode at ~7/8 of the interval sits in BOTH regimes (14 of 65 boosted, 3 of 15
plain); no mechanism is claimed for it. **Server:** `second_strike_seconds(state)` =
0.5 × `attack_interval_factor`, read at both arming sites (the double strike's and the
dual's); the test pins 0.5 unboosted and 0.335 under a 0.67 factor and locks the sites.

**On our own client the same night** (harness `20260917T232539`, recorder capture
`authsrv-20260917T232611-c1`; `--party daggers20` with Frenzy in slot 5, a 5000-health
practice target; scored off OUR wire by the same joins): plain swings 1.376–1.379 s
start-to-start and the double strike's second word 0.510 s behind the first (2 of 2);
under Frenzy, swings 0.919–0.926 s, the double's second word 0.357–0.358 s (4 of 4) and
the dual's 0.358 / 0.359 s (2 of 2). The delay scales — 0.358 / 0.510 = 0.70 against
retail's 0.334 / 0.499 = 0.67 — so the shipped change is seen on the client. Two
residuals are the TICK's, not the factor's: every interval here sits 10–45 ms above
retail's (1.376 against 1.326–1.335; 0.510 against 0.499) because a 50 ms tick pays out
what the clock has passed, and it is noted in §8 as an open pacing item rather than
chased here.

### What RUN-2 did not settle

A dual whose first strike LANDS and whose second misses (is 3 sent?); Sneak Attack with
a sword (2116 is PvE-only and not on this account — dropped, not deferred); where the
death batch strips effects relative to the morale tick (`kill_player` strips first,
retail after `[8, me, 1]` — n = 1); what property 10 on the victim names; the 7/8 swing
sub-mode. A lead that is BLOCKED (reason 0) rather than missed was not exposed —
Bonetti's Defense never went up in the two minutes; the miss is the same fail-word
family and the server treats them alike.

