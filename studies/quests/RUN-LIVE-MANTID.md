# RUN-LIVE-MANTID — the Factions tutorial on a Mesmer, one live capture

**REGISTERED 2026-09-13, before any launch.** `main` at `12947b9c`. The owner: *"i want to take a
mesmer through the factions tutorial quest ... the quest is called Mantid Hatchlings. it runs
through a variety of mechanics."* This is the capture `PLAN.md` §8 named on 2026-08-17 ("the
Factions tutorial, start to Shing Jea Monastery"), designed now: **one human-driven session on
the secondary account** (`RUNBOOK.md` §"Capturing a live session"), the plan sealed by
`livesession.py --plan` before the client launches, one F9 at each of Instructor Ng's
"left-click me when you are ready" pauses.

**Identifiers.** `MANTID-P<n>` = a prediction registered before the run. `MANTID-Q<n>` = a
question the run is the first chance to answer. Convention:
[studies/idents/CONVENTION.md](../idents/CONVENTION.md).

**Labels** per [studies/character/FINDINGS.md](../character/FINDINGS.md), plus `WIKI` per the
wiki skill.

## 0. Why one run and not a marked leg per mechanic

The owner asked whether a corpus run needs every section marked by hand (F11). It does not,
and F11 is the wrong key for sections in any case:

- **The wire narrates most mechanics itself.** Every cast is named by `0x00A0` prop 60, quest
  state by `0x0049`/`0x0054`/`0x0052`, a level by prop 36 and a level-up by prop 37, a death by
  `0x00F1`'s bit 4, an item by `0x0161`. The scoring tools join on opcodes, not on marks.
- **Sections are plan steps; F9 advances them.** F11 stamps an instant with no text, for a
  surprise you annotate afterwards by ordinal. The plan is hashed before launch, so the marks
  mean what was predicted, not what was remembered.
- **Where marks earn their keep is the tutorial's UI lessons** — the chest, the pickup, the
  equip, the log open, the attribute spend — which the wire does not self-narrate, and which
  are exactly what this capture is for. Ng's cadence makes that cheap: one F9 per click on Ng.

## 1. What the corpus holds today, measured (`tut_census.py`, 61 live connections, 153,688 messages)

Counted 2026-09-13 with `livewire.live_connections()` / `decode_conn`; the decoded value list
carries the opcode at index 0, so a property message reads `[op, prop, agent, value]`.

| shape | opcode | corpus | on the three Factions tapes (2026-08-17) |
|---|---|---|---|
| quest add | `0x0049` | 14 | **0** |
| quest objectives update | `0x0054` | 46 | 0 |
| quest complete (`0x0052` ×2 then `0x004A`) | `0x0052` | 22 | 0 |
| description request (c2s) | `0x0012` | 40 | 5 |
| skill unlocked | `0x001C` | **2** (both pre-Searing, `20260819T132414`) | 0 |
| chest reward effect | `0x006C` | **0** | 0 |
| temporary skill equip | `0x0082` | **0** | 0 |
| party defeated | `0x01D8` | **0** | 0 |
| cinematic | `0x0101` / `0x0105` | **0 / 0** | 0 |
| skill-bar slot flags | `0x0065` | 0 | 0 |
| attribute spend (c2s `0x000F` → `0x0036` + `0x0038`) | | 15 / 30 / 31, all on the PvP-UI runs | 0 |
| level-up event | prop 37 | **2** | 0 |
| a level changing on one agent | prop 36 | 1 | 0 |
| death bit on any agent | `0x00F1` & 0x10 | 140 | 1 |
| item into a bag | `0x013E` | 493 | 90 |

Two corrections to the 2026-08-17 shopping list in `PLAN.md` §8, so this run is not sold on
stale goods: **a level changing on one agent was OBSERVED on 2026-08-19**
([../unitsetup/FINDINGS.md](../unitsetup/FINDINGS.md) "THE LEVEL-UP, OBSERVED" — the burst is
prop 37, prop 42, `0x0039`, `0x0038`, three `0x00EE` rows), and **a death with its penalty
was OBSERVED twice** ([../morale/FINDINGS.md](../morale/FINDINGS.md) §1). Both legs below
therefore CORROBORATE at a new level (1 → 2 or 3; a scripted rather than a combat death)
instead of discovering. **Secondary profession selection is NOT in this quest** — it comes
after the headmaster quests in Shing Jea — and the list's item stays open.

## 2. Questions for the owner, BEFORE the run

1. **New Mesmer, created under capture, or an existing one?** Step `create` covers both;
   say which, because creation was salvaged once (`20260817T180610`) and a second witness is
   worth having.
2. **`--mode base`?** Every Factions capture so far declared `base`; the driver refuses
   without it and nothing on the wire records it afterwards.
3. **F9–F11 free** of any other binding on the machine, and the loopback dry-run green today.

## 3. Preconditions (the runbook's, restated)

* `python toolkit/clientpatch/dhbuild.py` says `stock` + `key_tapped` for the `run-live` build,
  and **updater LIVE** — Monastery Overlook must stream into the live build's own `Gw.dat`.
* `python toolkit/harness/dryrun_keycapture.py` (elevated) green today.
* The plan file is at `C:\gd\Rurik\vault\plans\mantid_hatchlings.txt` and
  `python toolkit/harness/marks.py --check-plan C:\gd\Rurik\vault\plans\mantid_hatchlings.txt`
  parses it (20 steps). **Then leave the file alone.**
* Human cadence, human hours, one client, never in a competitive context (`PLAN.md` §6.2).

## 4. The legs — floors and predictions, fixed here

The quest, per GWW (*Mantid Hatchlings*, read 2026-09-13): given by Instructor Ng at Monastery
Overlook; objectives "Meet Instructor Ng at the gate / Defeat [18..0] more mantid hatchlings /
See Instructor Ng for your reward"; reward 2,000 XP + Resurrection Signet (id 2); after the
scripted death at the resurrection shrine a Mesmer receives **Empathy (id 26)** and **Ether
Feast (id 40)**. Kisai and Mai fight with full henchman bars (Mai casts Viper's Defense).
A Mantid Hatchling is **level 0**, stationary, no skills; Mantid Drone Hatchlings follow.

A leg under its floor is reported ABORTED, never as "no effect".

### Leg A — the quest lifecycle on a real quest (steps `offer`, `gate`, `party`, `last`)

* Floor: the accept, ≥ 10 kills witnessed (≥ 10 `0x0054` on the tutorial connection), the
  turn-in.
* **MANTID-P1.** Accept: `0x0049` + `0x0054` + `0x004C` + `0x0051` unsolicited, and the client
  sends `0x0012` anyway (the responder rule, 4/4 in `20260807T143055`).
* **MANTID-P2.** Each kill is one `0x0054` on the same quest id carrying the objective text
  with the count decremented; no `0x0049`/`0x004A` between accept and turn-in.
* **MANTID-P3.** Turn-in is `0x0052` twice then `0x004A` (3/3).
* **MANTID-Q1.** The quest's id, and whether "[18..0]" is a server-side count in the string or a
  client-side template argument.

### Leg B — skills as rewards (steps `skills`, `last`)

* Floor: both grants on the wire and the bar redrawn with them.
* **MANTID-P4.** `0x001C SKILL_UNLOCKED` ×2 (26, 40), then `0x00DA SKILLBAR_UPDATE`
  re-declared mid-map as `[26, 40, 0, 0, 0, 0, 0, 0]`; at the reward a third `0x001C` for 2.
* **MANTID-Q2.** Whether `0x0082 EQUIP_TEMPORARY_SKILL` (0 in corpus, named on screen only) is
  what places a granted skill in the bar, or `0x00DA` alone does.

### Leg C — the scripted death and the resurrection (step `death`)

* Floor: one death of the player and one rise.
* **MANTID-P5.** The morale tick exactly as measured twice: `0x00F1 [me, 0x10]`, `0x009C [me,
  85]`, `0x00EE [10, −15]`, prop 41 and prop 42 at −15 % (100 → 85 health at level 1), prop 43
  → 0, `0x0026 [me, 4]`.
* **MANTID-P6.** **No damage word** (`0x00A3` prop 16) in front of the death: a scripted kill is
  a bare status flip. The two corpus deaths both open with the killing blow; this one should not.
* **MANTID-P7.** `0x01D8 PARTY_DEFEATED` fires when Kisai and Mai are down too — the first
  retail witness (0 in corpus; named on screen 2026-08-13).
* **MANTID-P8.** The rise: `0x00F1 [me, 0]`, props 52 and 55 at 1.0, `0x0026 [me, 5]`, the
  maxima **not** restored, and `0x009C [me, 100]` only on the Monastery connection (step `ludo`).

### Leg D — the level-up from level 1, and the attribute spend on a roleplaying character (steps `last`, `spend`)

* Floor: one prop 37 on the player; ≥ 2 attribute clicks acknowledged.
* **MANTID-P9.** In the reward frame: prop 37 = L, prop 42 = 100 + 20 × (L − 1), `0x0039` =
  the wiki's total (L2 5, L3 10, L4 15), `0x0038` = the same number available.
* **MANTID-P10.** Each spend click: c2s `0x000F` then `0x0036` ack + `0x0038` available — the
  `studies/pvpui` §32 protocol, measured only on a PvP character until now.

### Leg E — the chest, the pickup, the equip (steps `chest`, `equip`)

* Floor: one pickup into a bag, one equip.
* **MANTID-P11.** The weapon's `0x0161` precedes its `0x013E` on the same connection
  (621/621); `0x006E` for our agent then names that id in position 0.
* **MANTID-P12.** `0x006C CHEST_REWARD_EFFECT` does **not** fire for a tutorial chest.

### Leg F — the Mesmer's hex on a foe, and the heal (step `hex`)

* Floor: ≥ 3 Empathy casts on a foe that then attacks, ≥ 3 Ether Feast casts.
* **MANTID-P13.** Empathy lands as `0x0042` on the FOE's id carrying 26; each of that foe's
  swings while hexed carries a damage word on the foe with the player as source.
* **MANTID-P14.** Ether Feast's heal is `0x00A2 [55, me, fraction]` worth 60 at Inspiration 0.
* **MANTID-Q3.** The `0x0042` flag word for a hex versus an enchantment — no foe-side effect
  is in the corpus (`studies/skillcast` §14.5's `buff_type_field` probe was ours, not retail's).

### Leg G — gadgets, cinematics, quiet controls (steps `arrive`, `look`, `log`, `gate2`, `shrine`, `danger`, `monastery`)

* Floor: none — these are questions with a stated lean, and a null is reportable as a null
  only because the still stretches are the control.
* **MANTID-Q4.** Whether the tutorial's two gates and the shrine are agents whose state changes
  ride agent-level messages, or something else; lean: agents.
* **MANTID-Q5.** Whether any cinematic plays and what drives it (`0x0101`/`0x0105`, 0 in corpus).
* **MANTID-P15.** Looking around and opening the quest log send nothing beyond the client's
  cadence.
* **MANTID-P16.** One game connection from creation to Ludo; the Monastery is a second.

### Not in this run, said so

Secondary profession selection (after the headmaster quests), a mission completion
(`0x004E`/`0x0096`/`0x0097`/`0x00FB`, the quests study's largest hole), the hero and PvP
sessions the owner has queued (a level-3 Ranger with a level-3 Warrior hero; a PvP character
with three heroes on the Isle of the Nameless) — each is its own runsheet.

## 5. The commands (PowerShell; every line runs as written)

```
python toolkit/clientpatch/dhbuild.py
python toolkit/harness/marks.py --check-plan C:\gd\Rurik\vault\plans\mantid_hatchlings.txt
python toolkit/harness/livesession.py --account capture --exe C:\gd\Rurik\vault\run-live\2026-09-01_44fbd68767a8\Gw.exe --confirm --mode base --minutes 90 --plan C:\gd\Rurik\vault\plans\mantid_hatchlings.txt
```

The build is 38888, rebuilt 2026-09-13 after the driver refused the stale 38849 copy. `--minutes` is a
ceiling and the driver's default of 10 is too short for this quest. The third line is elevated and is the owner's; the driver sends nothing and clicks nothing. It
prints the `marks.py` command for the second shell with the resolved capture directory —
**copy it, do not retype it.** After the run, notes go in a separate `<ordinal><TAB><text>`
file and are bound with `marks.py --bind`.

## 6. What gets scored afterwards, and by what

* Leg A: a quest-lifecycle join on the tutorial connection (promote `tut_census.py` to
  `toolkit/authsrv/questjoin.py`: every `0x0049`/`0x0054`/`0x0052`/`0x004A` by quest id with
  the c2s `0x003B`/`0x0012` beside it).
* Leg B: the `0x001C`/`0x00DA`/`0x0082` census on the same connection.
* Leg C/D: `moralescan.py` for the tick; the level-up differencing method of the unit-setup
  study (the reward is the control).
* Leg E: the `0x0161` → `0x013E` → `0x006E` order check the Q11 runs used.
* Leg F: `henchjoin.py --hostile` for the damage words; a `0x0042` census by target.
* Leg G: a per-step window census (`marks.py --bind`, then everything inside each step).

Each leg's verdict goes into `FINDINGS.md` here as a new section with the label it retires
named; the schema's `name: null` rows that a leg names get their `overrides.json` entry with
the capture as the witness.
