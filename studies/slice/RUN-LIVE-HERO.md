# RUN-LIVE-HERO — a level-3 Ranger with a level-3 Warrior hero, Kamadan into the Plains of Jarin

**REGISTERED 2026-09-14, before any launch.** `main` at `a8d2acd5`. The owner: *"ranger with
warrior hero is ready whenever - no Bonetti's Defense for now so nix that. i also managed to
unlock Frenzy as well. let's test the Ranger + Hero (zone out from Kamadan into Plains of Jarin,
kill some creatures or issue commands or whatever. the hero has many of the attacks our test
warrior equips - their bar is Power Attack, Sever Artery, "Watch Yourself!", Healing Signet,
Final Thrust, Frenzy and Resurrection Signet. we can also inspect Frenzy on the player character
in case we don't get rich packet data from heroes. could be a separate run."* One human-driven
session on the secondary account (`RUNBOOK.md` §"Capturing a live session"), the plan sealed by
`livesession.py --plan` before the client launches, the same shape as
[../quests/RUN-LIVE-MANTID.md](../quests/RUN-LIVE-MANTID.md).

**Identifiers.** `JARIN-P<n>` = a prediction registered before the run. `JARIN-Q<n>` = a question
the run is the first chance to answer. Convention:
[studies/idents/CONVENTION.md](../idents/CONVENTION.md).

**Labels** per [studies/character/FINDINGS.md](../character/FINDINGS.md), plus `WIKI`.

## 0. Why this run, in one paragraph

The whole hero ladder (SLICE-H1…H13, [PLAN.md](PLAN.md) §7) was built off retail's **henchmen**
— GWW says heroes and henchmen share one AI, and the corpus holds eleven henchman bodies — and
off pvpui 28's commander clicks captured on **our own** client. What no tape has ever carried is
a **hero**: `0x0074`, `0x01C2` and `0x0072` are 0 in the corpus, every skill-bar message names
the observer, no commander order was ever answered by retail, and no attack-speed stance ever
ran on a retail character. This run is the first retail witness for all of it, on a hero whose
bar overlaps the slice warrior's (Power Attack 322, Sever Artery 382, Healing Signet 1, Final
Thrust 385, Frenzy 346, Resurrection Signet 2 all have content rows). Bonetti's Defense is out
by the owner's word. Frenzy on the player is a conditional step, not a separate run — it only
needs Frenzy on the Ranger's bar, which needs a Warrior secondary; if that is not the case the
step is skipped with two F9s and the hero's own Frenzy carries the question.

## 1. What the corpus holds today, measured (`hero_census.py` / `hero_census2.py`, 65 live connections)

Counted 2026-09-14 with `livewire.live_connections()` / `decode_conn`; the decoded value list
carries the opcode at index 0.

| shape | opcode | corpus |
|---|---|---|
| mercenary/hero info | `0x0074` | **0** |
| party hero add | `0x01C2` | **0** |
| hero activate | `0x0072` | **0** |
| party henchman add | `0x01BF` | 21 |
| stance / lock / hero flag / party flag (c2s) | `0x0015` / `0x0016` / `0x001A` / `0x001B` | **0 / 0 / 0 / 0** |
| stance / lock / hero flag echoes (s2c) | `0x0062` / `0x0063` / `0x0066` | **0 / 0 / 0** |
| party flag | `0x0067` | 4, every one the `[(+inf, +inf), 0]` clear at load |
| skill bar, load-time | `0x00DA` | 64, **every one naming the observer** |
| skill bar, per-slot write | `0x00D9` | 11, every one on the observer |
| attack speed | `0x0035` | 81, **every modifier 1.0** |
| effect apply carrying skill 364 | `0x0042` | 43, every one on the observer (F38: 0 of 369 on anyone else) |
| adrenaline clear | `0x00D0` | 28 |
| knock-down (prop 63) | `0x00A2` | 4 |
| status word carrying value 2 (a condition) | `0x00F1` | 322 |
| instance loads naming map 449 (Kamadan) or any Nightfall map | `0x0199` | **0** (the map ids on tape: 146/148/164, 212, 238, 242, 248, 280/281, 309–312, 416) |

So: no hero, no commander answer, no Nightfall map, no attack-speed change anywhere on
retail's wire. Every prediction below is against a count of zero except the formation, the
engagement rule, the heal, the raise and the effect-list rule, which are corroborations.

## 2. Questions for the owner, BEFORE the run

1. **Is Frenzy on the Ranger's own bar** (Warrior secondary)? Step `frenzyme` runs only if so.
2. **`--mode base`?** Every capture so far declared `base`; the driver refuses without it.
3. **Which hero** (the run names it through `0x0074`'s index; say it in the notes).
4. F9–F11 free of any other binding, and the loopback dry-run green today.

## 3. Preconditions (the runbook's, restated)

* `python toolkit/clientpatch/dhbuild.py` says `stock` + `key_tapped` + **updater LIVE** for
  `run-live/2026-09-01_44fbd68767a8` (build 38888). If ArenaNet has shipped a build since
  2026-09-13 the driver refuses and prints the rebuild; the procedure is the one the tutorial
  run used (`RUNBOOK.md`, "the one to use"), redone in full.
* `python toolkit/harness/dryrun_keycapture.py` (elevated) green today.
* The plan is at `C:\gd\Rurik\vault\plans\hero_jarin.txt`, sha256 `5bbe6f31…9438d3`,
  and `marks.py --check-plan` parses it (**14 steps**). **Then leave the file alone.**
* Human cadence, human hours, one client, never in a competitive context (`PLAN.md` §6.2).

## 4. The legs — floors and predictions, fixed here

A leg under its floor is reported ABORTED, never as "no effect". The hero's own skill use
cannot be scheduled by the operator, so step `fights` is open-ended with a stated stop
condition and an F11 each time Frenzy is seen on the hero.

### Leg A — the hero's rig on retail's wire (steps `town`, `panel`, `zone`, `return`)

* Floor: two instance loads with the hero in the party (a town and a field).
* **JARIN-P1.** The town's load carries `0x0074 MERCENARY_INFO` before `0x01C2 PARTY_HERO_ADD`
  (heroes §14.5's order, ours until now), and **no** `0x0020` create for the hero's agent while
  in Kamadan (SLICE-H2b's stock rule, the owner's *"in the outpost she should be hidden"*).
* **JARIN-P2.** The field's load repeats the rig (per instance, SLICE-F32) and adds the body:
  a create with the henchman's shape (F28), a named item per weapon then `0x006D [hero, item,
  0]` (F33: 12 of 12 henchman bodies), `0x00A6` profession bytes, `0x00B7` and `0x003A` on the
  hero's agent (§14.5's load-bearing order — RECONSTRUCTION until this tape).
* **JARIN-Q1.** Whether `0x0072 HeroActivate` appears on retail at all, and its `inventoryId`
  and `aiMode` fields (heroes §15.2; the field the panel click crashed on, §15.3).
* **JARIN-Q2.** The hero's skill-bar delivery: `0x00DA [hero, 8 ids]` at load (heroes §15.1,
  "accepted, not seen"; 64 of 64 corpus `0x00DA` name the observer), something else, or nothing
  until the panel opens — step `panel` says whether the open sends a c2s.
* **JARIN-Q3.** Plains of Jarin's map id and `0x0199` triple; Kamadan's is 449 by content and
  is on no tape.

### Leg B — the hero fights (step `fights`, and the wire of every other fight)

* Floor: ≥ 3 fights opened by the player; ≥ 2 casts each of Frenzy, "Watch Yourself!" and
  Final Thrust by the hero (F11-marked for Frenzy).
* **JARIN-P3.** The hero's opening start follows the player's inside 6 s, on the player's
  target (F30: 77 of 89, p50 0.50 s).
* **JARIN-P4.** Power Attack, Sever Artery and Final Thrust announce as attack skills `0x00A0
  [50, hero, foe, id]`, close `[46]`, one damage word each (F24/C6); Sever Artery's Bleeding is
  the foe's status word `0x00F1 [foe, word|0x2]` and **no** `0x0042` on anyone (F38).
* **JARIN-P5.** Healing Signet is a prop-55 heal with source = target: `0x00A3 [55, hero, hero,
  +frac]` (MANTID-P14's shape on the player; F34's "the hero heals herself" is ours).
* **JARIN-Q4.** Whether any pool message (`0x00D0`, 28 in corpus) ever names the hero; lean:
  never — only the player's pools are sent, so Final Thrust's adrenaline clear is invisible.
* **JARIN-P6.** Each "Watch Yourself!" puts `0x0042 [me, 364, k]` on the **player's** list, and
  nothing on the hero's; the hero's status word is unchanged. F38's rule from the receiving
  side. (364 is the Tactics shout F37 counted on the owner's own Warrior, 43 corpus rows; that
  it is "Watch Yourself!" is UNVERIFIED here and the run's `0x00A0` prop 60 names it.)
* **JARIN-P7.** Frenzy on the hero — SLICE-F37's UNWITNESSED half: `0x0035 [hero, base, 0.67]`
  at the stance's open and `[hero, base, 1.0]` at its close (81 retail `0x0035` so far, all
  1.0); damage words against the hero doubled inside it. A null with ≥ 2 marked casts means
  retail does not resend, and H13's `attack_speed_tick` is a reconstruction the client
  tolerates but retail never makes.
* **JARIN-P8.** Hostile opening starts name the **Ranger**, not the Warrior hero: F29's rule is
  lowest base armour first (51 of 58), and a Ranger's class armour sits below a Warrior's at
  every level. F28's "the party bodies take the aggro" (162 vs 13) was measured with a Warrior,
  Monk and Elementalist beside the observer; this pair discriminates the two readings.

### Leg C — the commander on retail (steps `guard`, `avoid`, `lock`, `flag`, `pflag`)

* Floor: 3 stance clicks, 1 lock, 1 hero flag placed and removed, 1 party flag placed and removed.
* **JARIN-P9.** Each stance click is c2s `0x0015 [hero, mode]` and retail answers `0x0062 [hero,
  mode]` — the c2s shape is the client's own (pvpui 28.5, captured on our server), the echo is
  what `ChCliHero::SetAiMode` listens for and what ours sends; 0 of either on any tape.
* **JARIN-P10.** Under Guard the hero's first start comes after a hostile's start on the party;
  under Avoid no hero start at all; on Fight it opens (F31's WIKI semantics, unwitnessed).
* **JARIN-P11.** The lock is c2s `0x0016 [hero, target]` → `0x0063 [hero, target]`, and the
  hero's next start names that target with no player start in front of it. **JARIN-Q5:** what
  clears the lock on the wire at the target's death (`0x0063 [hero, 0]`, or nothing).
* **JARIN-P12.** The hero flag is c2s `0x001A [hero, x, y, plane]` → `0x0066` with the same
  fields; the hero walks there by `0x0029` leads and holds; the party flag is the `0x001B` /
  `0x0067` twin and its removal is `0x0067 [(+inf, +inf), 0]` (the load form, 4 of 4).
  **JARIN-Q6:** the c2s form of a flag REMOVAL — never captured; pvpui 28 applied the s2c
  clear idiom to it by analogy.

### Leg D — the player (steps `ranger`, `frenzyme`)

* Floor: one cast of each skill on the Ranger's bar; `frenzyme` ≥ 2 stances or SKIPPED.
* **JARIN-P13.** A bow attack skill is kind 50 with the projectile bracket in front of its
  damage word; every skill is announced by `0x00A0` prop 60.
* **JARIN-P14** (conditional on Frenzy on the player's bar). `0x0035 [me, base, 0.67]` at the
  open, `[me, base, 1.0]` at the close, `0x0042 [me, 346, k]` on the player's list, and damage
  words against the player doubled — the same question as P7 on the agent whose pools and
  list the wire does carry.

### Leg E — a party death (step `death`)

* Floor: none — a question with a stated lean, reportable as a null only against the fights
  that did not produce one.
* **JARIN-P15.** A Resurrection Signet raise is `0x00A0 [60, caster, corpse, 2]`, 3.0 s, then
  `0x00F1 [corpse, 0]` (F28, 5 of 5 on henchmen).
* **JARIN-Q7.** Whether a hero's death carries the morale tick on the hero (`0x009C [hero, 85]`
  and the maxima) the way the player's does, and whether `0x01D8 PARTY_DEFEATED` fires when
  both die (0 in corpus; the tutorial's three allied deaths did not raise it).

### Leg F — the formation (step `walk`)

* **JARIN-P16.** `0x0029` point leads every ~0.5 s ending 100–140 u abeam of the player, never
  a `0x002A` naming the player, no `0x0028` at the player's stop (F28, 750 of 750 on henchmen).

### Not in this run, said so

Bonetti's Defense (the owner's word), knock-down and block (no hammer on either bar; the
Plains' creatures do not carry one), a PvP character with three heroes on the Isle of the
Nameless (its own runsheet), hero equipment changes, the hero's attribute panel.

## 5. The commands (PowerShell; every line runs as written)

```
python toolkit/clientpatch/dhbuild.py
python toolkit/harness/marks.py --check-plan C:\gd\Rurik\vault\plans\hero_jarin.txt
python toolkit/harness/livesession.py --account capture --exe C:\gd\Rurik\vault\run-live\2026-09-01_44fbd68767a8\Gw.exe --confirm --mode base --minutes 60 --plan C:\gd\Rurik\vault\plans\hero_jarin.txt
```

The third line is elevated and is the owner's; the driver sends nothing and clicks nothing.
`--minutes` is a ceiling. It prints the `marks.py` command for the second shell with the
resolved capture directory — **copy it, do not retype it.** After the run, notes go in a
separate `<ordinal><TAB><text>` file (the hero's name, and each F11's meaning if not Frenzy)
and are bound with `marks.py --bind`.

## 6. What gets scored afterwards, and by what

* Leg A: a per-connection census of `0x0074` / `0x01C2` / `0x0072` / `0x00DA` / `0x00D9` by
  agent, against the hero's agent id from `0x01C2`; the create-order check of the hero body
  (F33's item-then-`0x006D` join).
* Leg B: `henchjoin.py` (the engagement join and the hostile-target count, now with a Ranger
  observer); a `0x0042` census by subject (F38's `fx_census.py`); `ias_census.py` for `0x0035`
  by agent and modifier, joined to the F11 marks; the skill-announce census by kind.
* Leg C: a per-step window census (`marks.py --bind`) for the c2s/s2c pairs, and the hero's
  starts inside each stance window.
* Leg D/E/F: the `0x0035` census on the player; `moralescan.py` on the hero's agent; the
  formation join of F28 on this tape.

Each leg's verdict goes into [FINDINGS.md](FINDINGS.md) as a new SLICE-F section with the
label it retires named; a refuted P7 retires H13's resend to its flag, a confirmed one
upgrades it to OBSERVED.

## 7. SCORED 2026-09-14 — capture `20260914T005758`

Run the same night on build 38888. 14 of 14 steps marked, seals AGREE, 4 keys tapped, three
game channels (Kamadan 449 → Plains of Jarin 430 → Kamadan), every direction decoded to the
last byte. The owner's three notes after the run: no F11 on the hero's Frenzy casts (joined by
`0x0042 [hero, 346]` instead — 17 applies), the party flag placed before the hero flag (read in
the order played), and the hero's Resurrection Signet was cast on the player. The single F11
(427.5 s, during step `lock`) was, per the owner afterwards, a note that Frenzy is not on the
player's bar (*"i think ... but i forget exactly"*). The hero is Koss (index 6). The
Ranger has no secondary profession, so step `frenzyme` was skipped with two F9s as written.
The wire is in [FINDINGS.md](FINDINGS.md) SLICE-F39.

| id | verdict | in one line |
|---|---|---|
| P1 | REFUTED in form, CONFIRMED in substance | **no `0x0074` on the tape**; `0x0072 [6, agent, inventoryId, aiMode]` comes BEFORE the party build; no body, items or `0x006D` for the hero in a town |
| P2 | CONFIRMED | the field repeats the rig and adds `0x0161` ×2 → `0x0020` → `0x006D [hero, 778, 779]`, all before the build; `0x00A6`, `0x00B7`, `0x003A` on the hero's agent |
| Q1 | answered | `0x0072` in 3 of 3 instances; inventoryId per instance (200 / 5 / 157); **aiMode persists across the zone** (2 = the last Avoid click) |
| Q2 | answered | `0x00DA [hero, 8 ids, 8 zeros, 1]` at load, beside the player's; the panel open sends nothing |
| Q3 | answered | Plains of Jarin = map 430, `0x0199 [member, 430, 1, …]`; Kamadan `[·, 449, 0, …]` |
| P3 | CONFIRMED | the hero's start 3.0–3.5 s after the player's, on the player's target, 4 of 4 (a melee chase first) |
| P4 | CONFIRMED | `[50, hero, foe, id]`; Sever Artery → `0x00F1 [foe, 0x3]` +0.35 s, 7 of 7; 0 `0x0042` on any foe |
| P5 | ABORTED | the hero never cast Healing Signet |
| Q4 | REFUTED lean | the hero's adrenaline IS on the wire: `0x00CF [hero, 25]` per hit, `[hero, 2]` per hit taken, `0x00D0 [hero]` at each Final Thrust |
| P6 | half | "Watch Yourself!" is **348** (not 364); `0x0042 [player, 348, 1, ·, 10.0]` yes — AND `0x0042 [hero, 348, …]` in the same instant: the hero has an effect list |
| P7 | CONFIRMED, shape corrected | `0x0035 [hero, 1.33, 0.67]` — 19 of 19 in the same instant as the hero's next attack start, never at the apply; no send at the close (1.0 rides the next chain) |
| — | INCONCLUSIVE | Frenzy's double damage: 3/5 hp inside (n = 27), 3 and 2 outside (n = 2) |
| P8 | REFUTED as stated; F29 CONTESTED | where both had hit it, hostiles opened on the Warrior 3 of 5, the Ranger 2 of 5; "last to hit" fits 4 of 5 |
| P9 | CONFIRMED | `0x0015 [hero, mode]` → `0x0062 [hero, mode]`, 4 of 4, 30–50 ms |
| P10 | CONFIRMED | Guard: first start after the hostile engaged; Avoid: 0 starts in 24.6 s under fire; Fight: the chase in the echo's instant |
| P11 | CONFIRMED | `0x0016 [hero, 28]` → `0x0063 [hero, 28]`; the hero's next start on 28 with no player start |
| Q5 | answered | **`0x0063 [hero, 0]` from the server 0.57 s after the kill** |
| P12 | CONFIRMED | `0x001A`/`0x0066` and `0x001B`/`0x0067` pairs, 30–50 ms; the lead ends 0.0 u off either flag; the party flag carries NO slot offset for one hero |
| Q6 | answered | the flag removal's c2s is the `(+inf, +inf)` form, both flags |
| P13 | partial | bow attack skills are kind 50 (394, 392); the projectile bracket unscored; word 38 reason 1 ×3, unnamed |
| P14 | SKIPPED correctly | no secondary profession |
| P15 | CONFIRMED | `0x00A0 [60, hero, player, 2]` 0.63 s after the death, `0x00F1 [player, 0]` 3.0 s later |
| Q7 | answered | a hero's death is the player's tick (status, `0x009C` −15, prop 42, prop 41, energy 0) plus `0x00D0` and its effect closes; `0x0026 [hero, 8]`, rise 9; **no `0x01D8` on the full wipe** |
| — | new | a wipe → 10.6 s → both teleported to the shrine (`0x002C`, plane 19), the hero's body deleted and re-created, both at full health, maxima kept |
| return | half REFUTED | the third connection has the roster and no body; **morale 100 for both** — the penalty is cleared in an outpost |
| P16 | half | 39 leads at p50 0.61 s, 0 `0x002A` to the player, `0x0028` only at the reach; the abeam offset unscored |
| — | new | the hero's casts ride `0x00E3`/`0x00E5`/`0x00E6` (48/35/1) — retail announces a hero's skills on the player's family |
