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
a target with no lead on it**. What the corpus cannot show is a dual attack landing, a
double strike, or the Critical Strikes energy step — §5 is the capture that would.

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
`skilltable.player_corpus` (1,333 rows). **DAGGERS-B1 lands it in the extractor with a
test; until then these counts are one run of an unreviewed script.**

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
| | `0x009F [46, me, 0]` | `0x005C [me, target, 2]` |
| | **`0x00A0 [38, target, me, 2]`** | `0x00A3 [16, target, me, -0.1071]` |
| | **`0x00E5 [me, 780, 0, 0]`** | — |
| | `0x00E3 [me, 780, 0]` | `0x00E3 [me, 780, 0]` |

The energy IS debited, and the recharge (3 s, the table's own `recharge`) is started
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
| **DAGGERS-B1** | `skilltable.py`: read +0x14 and +0x24, emit `combo`, `combo_req`, `weapon_req`; `test_skilltable.py` locks §1's censuses and the 29-row join (ids only — no names in the repo). `content.py` needs no change (no per-field allowlist for kind `skills`). | F1-F3 |
| **DAGGERS-B2** | A dagger item row (item_type 32, offhand empty), `WEAPON_TYPE_ATTRIBUTE` / `WEAPON_TYPE_RATE` entries, `PARTY_WEAPON_ITEMS["daggers"]` — a profession-7 party body cannot resolve a weapon today. | F4, F5 |
| **DAGGERS-B3** | `player_profession` on the `[party.*]` row; today only `--spawn-profession`, unwired to the row's attributes and weapon. | audit |
| **DAGGERS-B4** | Weapon gate on attack skills from `weapon_req`. What retail SENDS on a mismatch is unobserved — ship the refusal the server already uses (`0x00E2`) and label it RECONSTRUCTION. | F3 |
| **DAGGERS-B5** | Chain state per (attacker, target): set on a chain skill's HIT, `0x005C` to the attacker only, clear at 15 s or death; unmet `combo_req` → F7's batch verbatim: energy debited, `0x00E5` recharge, 46, `[38, target, me, 2]`, `0x00E5` 0, `0x00E3`; no damage, no state. | F6, F7 |
| **DAGGERS-B6** | Second strike: duals always, plain swings on the double-strike roll. Wire shape waits on Q1 / Q2. | §3 |
| **DAGGERS-B7** | Critical Strikes: crit chance + energy on a critical hit. Wire shape waits on Q4. | §3 |

B1-B5 need no new capture. B6 and B7 do.

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

**RUN-DAGGERS-1, staged 2026-09-17, not run.** `vault/plans/daggers_chain.txt` — eight
steps, the predictions and their rivals pre-registered in the file's header, one meaning
for F11 ("the chain icon on the target's bar just changed": the tape carries `0x005C`,
only the operator sees what the client drew). Bar 782 / 780 / 775 / 781 and nothing else;
Dagger Mastery 12, Critical Strikes 8. Its floor: ≥ 30 plain swings with ≥ 3 double, one
landed dual with the target alive 16 s later, one re-lead pair, two cold presses each of
780 and 775, three critical hits below full energy.
