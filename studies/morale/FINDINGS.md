# Morale and Death Penalty — what a death costs, on retail's own wire

**Written 2026-08-20.** The question this closes has been open since 2026-08-05:
`0x00E9` field 10 is called `morale` by every lineage, our own probe found that
setting it moves nothing on screen, and the server has shipped it as a zero ever
since with a comment saying so. What "100%" means was nobody's answer.

It is answered now, and not by reasoning: **the live corpus contains player
deaths, fully instrumented**. §1 and §2 are read off them.

> **UPDATED 2026-08-22 — there are TWO, and the second was found by a peer.**
> This document said "exactly one" from 2026-08-20, over a 14-capture corpus. The
> corpus reached 20 captures on 2026-08-21 and the count is now two: the second
> is `20260821T152147` conn `63150`, agent 25, t=490.312 — a **level 20**
> character, where the first was level 2. The energy/adrenaline session hit it
> from the other side (an unexplained `max 17` row in a pool census) and told us.
> The tick is identical, and the arithmetic holds at a completely different
> scale: max health **480 → 408**, max energy **20 → 17**. §1.2 has it.
>
> The lesson is one this repo already wrote down and then walked into anyway:
> `moralescan.py`'s own docstring says a claim of the form *"the only X in the
> corpus"* decays the moment a capture is added. It decayed in two days. Re-run
> the census before quoting it.

**And as of 2026-08-20 the client half is measured too**, over two runs
([RUNS.md](RUNS.md)). `--probe morale` answered what reaches the screen:
`0x009C` draws the death-penalty indicator, `0x00EE`'s delta does not, and the
client **does not** recompute the pool maxima from morale — it displays the
numbers the server sends, including a wrong one we sent on purpose.
`--probe morale_store`, read with `ReadProcessMemory` rather than with eyes,
then answered what the screen could not: **the delta is applied all the same**,
`+=`, in both directions. There are two stores and one number (§2.4).

**Identifiers.** `MORALE-P<n>` = a prediction registered before a probe runs.
`MORALE-Q<n>` = an open question. Convention:
[studies/idents/CONVENTION.md](../idents/CONVENTION.md).

**Labels** per [studies/character/FINDINGS.md](../character/FINDINGS.md), plus
`WIKI` per [the wiki skill](../../.claude/skills/browse-gw-wiki/SKILL.md) —
strong for what a player can see, weak for internals.

---

## 1. The death, in full

`vault/captures/live/20260817T183756`, connection
`10.0.0.210:52294->54.80.22.158:80`, 1,381 messages, framed to
`consumed == total`, `err = None`. The player is agent 27, level 2, and dies at
**t = 78.813** — one tick, twelve messages, seven of them the death. The two
that open the tick are the killing blow itself (`0x00A7`, then `0x00A3`
property 16 — damage — from agent 37); the three not in the table below are a
`WORLD_SIMULATION_TICK`, a `0x002D [27]`, and `0x009F [8, 27, 1]`, which is the
aftercast `disabled` toggle rather than anything to do with dying — it fires 192
times for this player across the corpus and toggles back to 0 at the revive:

| t | opcode | payload | reading |
|---|---|---|---|
| 78.813 | `0x00F1` | `[27, 0x10]` | the death bit — bit 4 of the effects word, which this repo already sends |
| 78.813 | `0x009C` | `[27, 85]` | **morale, absolute, per agent** |
| 78.813 | `0x00EE` | `[10, 0xFFFFFFF1]` | **morale, as a delta: −15** |
| 78.813 | `0x009F` | `[41, 27, 22]` | new maximum **energy**: 25 → 22 |
| 78.813 | `0x00A2` | `[43, 27, 0.0f]` | energy regeneration → 0 while dead |
| 78.813 | `0x009F` | `[42, 27, 102]` | new maximum **health**: 120 → 102 |
| 78.813 | `0x0026` | `[27, 4]` | flags on the dying PLAYER (agents get 8) |

and 10.04 s later, at **t = 88.857**, the same connection resurrects him at a
shrine — the position jumps to (22020, −3792) plane 11 and a dozen far agents
are removed in the same tick:

| t | opcode | payload | reading |
|---|---|---|---|
| 88.857 | `0x00F1` | `[27, 0]` | the death bit clears |
| 88.857 | `0x00A2` | `[43, 27, 0.06f]` | energy regeneration back — **rescaled**, see §2.3 |
| 88.857 | `0x00A2` | `[52, 27, 1.0f]` | energy gain, full pool |
| 88.857 | `0x009F` | `[54, 27, 22]` | int 54 = a floating **"+22"** energy callout, display-only; equals the maximum because a refill from the death-zeroed pool gains all of it. MEASURED 2026-08-22, §2.5 |
| 88.857 | `0x00A2` | `[55, 27, 1.0f]` | armor-ignoring heal, full pool |
| 88.857 | `0x0026` | `[27, 5]` | flags on the revived player |

**The maxima are NOT restored at the resurrection**, and that is the point of
the mechanic: 102/22 stand until something removes the penalty (§3).

**The baseline is on the wire too.** At login (t = 0.897) the same connection
sends `0x009C [27, 100]`, then `0x00E9` with field 10 = 100, then the pools:
`0x009F [41, 27, 25]`, `0x00A2 [43, 27, 0.0528f]`, `0x009F [42, 27, 120]`.
So 100 is the neutral value, sent explicitly, on both channels.

### 1.2 The second death — level 20, same tick, same arithmetic

`vault/captures/live/20260821T152147`, conn `10.0.0.210:63150->52.55.104.238:80`,
5,960 messages. Agent 25 is the player, level 20, morale 100 at login.

| t | what | value |
|---|---|---|
| 0.482 | login: `0x009C`, `0x00E9` field 10 | morale **100** |
| 0.482 | `0x009F` prop 41 / prop 42 | max energy **20**, max health **480** |
| 490.312 | `0x009C [25, 85]` + `0x00EE [10, −15]` | morale **85** |
| 490.312 | `0x009F` prop 41 / prop 42 | max energy **17**, max health **408** |
| 490.312 | `0x00A2` prop 43, prop 44 | both regen rates → **0** while dead |
| 490.312 | `0x00F1 [25, 16]`, `0x0026 [25, 4]` | the death bit, then flags 4 |

**Both maxima are exact under §2's rule.** Level 20 → base health 480, less 15%
= 72, is 408. Base energy 20 less 15% = 3 is 17. And 480 at login is the level
curve's far endpoint, which §2.1 previously had from the wiki alone — it is now
on ArenaNet's wire.

**What this row does NOT do is discriminate base-from-total**, and saying so
matters more than the confirmation. This character carries 20 total energy, so
base *equals* total and both models predict 17; likewise health, where no
equipment bonus is in play. The discriminating datum is still the first death's
25 → 22 (§2.2), and it is still n=1. What the second death adds is the tick
shape at n=2, the arithmetic at a 24× larger pool, and the level-20 endpoint.

### 1.1 Why one sighting was enough even before the second

n=1 is normally where this repo stops. Three things make this one carry:

- **The number appears twice, on two channels, in two encodings, in the same
  tick.** `100 − 15 = 85` is the delta on `0x00EE` and the absolute on `0x009C`.
  A coincidence would have to agree in arithmetic as well as timing.
- **Both maxima move by exactly the predicted amount** (§2), computed from a
  rule written down independently by players (WIKI) and from base values that
  the same tape states (level 2 → 120 health; 25 energy).
- **The corpus-wide census refuses the alternative.** Re-run 2026-08-22 over
  20 live captures and 53 game connections (139,660 messages): `0x00EE` carries
  attr 10 forty-one times and **every non-zero value is a −15** (two of them);
  `0x009C` fires 94 times and **every value that is not 100 is an 85** (the same
  two); `0x00E9` field 10 is 100 in all 53 sightings. The two departures are the
  two deaths, each landing on both channels in one tick. Scanner:
  `toolkit/authsrv/moralescan.py` — re-run it rather than quoting these
  numbers, which have already moved once (43 connections → 53).

---

## 2. The arithmetic — OBSERVED, and it is exact

Morale is a percentage with **100 as neutral**, and it scales the character's
**base** Health and Energy — not the totals.

> WIKI (GWW, "Morale Boost" §Definition): a Morale Boost "increases your base
> Energy and Health by one to ten percent. It is not applied to energy or health
> from equipped armor or weapon sets".
> WIKI (GWW, "Energy" §Maximum energy, footnote): "The 10% bonus from a Morale
> Boost is 10% of (20 + 60) based on the base energy and the energy granted by
> Energy Storage ranks; all other sources do *not* get increased by 10%."

Written out:

```
effective_max = total_max + base * (morale - 100) / 100      morale ∈ [40, 110]
```

### 2.1 Health — 120 → 102

WIKI (GWW, "Health" §Maximum health): a roleplaying character starts at level 1
with 100 health, "+20 health per level up to a maximum of 480 health at level
20". The tape's `0x00E9` field 9 says level 2, so base = total = 120, no
equipment bonus in sight:

```
120 + 120 * (85 - 100)/100  =  120 - 18  =  102        ✔ observed 102
```

Which is a second, free confirmation that **field 9 is the level** — that was
OBSERVED against our own client in 2026-08-05 and has now been watched on
ArenaNet's wire agreeing with ArenaNet's own health arithmetic.

**Both endpoints of that curve are now OBSERVED rather than sourced.** The
level-2 character above carries 120; the second death's level-20 character
carries **480** at login (§1.2). GWW published both numbers, and retail's wire
now agrees with the wiki at each end of a 19-level span.

### 2.2 Energy — 25 → 22, and this is the discriminating one

WIKI (GWW, "Energy" §Maximum energy): "All professions, regardless of level,
have an innate capacity of 20 energy, and 2 pips of energy regeneration. This is
increased by armor…", with a table giving +5 armor energy (total 25) to Ranger,
Dervish and Assassin. So base 20, total 25:

```
25 + 20 * (85 - 100)/100  =  25 - 3  =  22             ✔ observed 22
```

**This is the observation that rules out the obvious wrong model.** Scaling the
*total* gives `25 × 0.85 = 21.25`, which is not 22 and is not an integer — the
naive reading would have had to invent a rounding rule to survive, and would
still have been wrong. The base-only rule needs no rounding at all: base health
is `100 + 20k`, whose 15% is `15 + 3k`, an integer at every level, and base
energy 20's 15% is 3.

### 2.3 The regeneration rescale — a bonus, and it names a constant nobody knew

Energy regeneration rides `0x00A2` property 43 as a **fraction of maximum energy
per second**, and the death tick proves it by holding the absolute rate constant
while the pool shrinks:

```
login   0.0528f × 25 = 1.32 energy/s
revive  0.0600f × 22 = 1.32 energy/s
```

WIKI (GWW, "Energy" §Regeneration): "Each pip of Energy regeneration generates 1
Energy every 3 seconds", and Assassin/Dervish armor adds +2 pips to the base 2.
Four pips at **0.33** each is 1.32 — so the game's pip is 0.33/s, not 1/3, and
`content/world.toml`'s `float_43 = 0.0396`, inherited from gw-preservation with
the comment "REVERSE THIS MORE" and shipped by us as "purpose unknown upstream
too", is exactly `3 × 0.33 / 25`: three pips on a 25-energy character. The
constant was never mysterious, only unlabelled.

`agents.py`'s `PROP_UNKNOWN_FLOAT_43` is renamed `PROP_ENERGY_REGEN` on the
strength of this — the same reasoning that already named property 44
(health regen, `2 hp/s` per pip; the tape carries `0.01667f × 120 = 2.0` on
party members in this very window).

**Two points is a reading, not a law, so the whole corpus was asked the sharper
question** (`moralescan.py --pips`): join every property-43 sighting to that
agent's own property-41 maximum, and ask whether the value is bit-exactly
`f32(f32(q) · pips / max)` for an INTEGER pip count. 59 sightings join, 9
distinct `(max, value)` pairs:

| max | value | bits | n | 0.33 | 1/3 |
|---|---|---|---|---|---|
| 17 | 0.03882353 | `0x3D1F056C` | 1 | **2 pips, exact** | no fit |
| 20 | 0.033 | `0x3D072B02` | 36 | **2 pips, exact** | no fit |
| 22 | 0.06 | `0x3D75C290` | 1 | **4 pips, exact** | no fit |
| 25 | 0.0396 | `0x3D22339C` | 4 | **3 pips, exact** | no fit |
| 25 | 0.0528 | `0x3D5844D1` | 10 | **4 pips, exact** | no fit |
| 30 | 0.044 | `0x3D343959` | 4 | **4 pips, exact** | no fit |
| 17, 22, 25 | 0.0 | `0x00000000` | 3 | 0 pips | 0 pips |

**Six of six non-zero values are exact at 0.33 and none fits 1/3**, on the
bits rather than on a tolerance, with the pip count constrained to a whole
number. The three zeroes are regeneration suspended while dead, and they fit
both quanta trivially at 0 pips — which is why the score above is stated over
the non-zero rows and the tool prints the caveat next to its own total.

**Re-run it rather than trusting this table.** These counts moved once already:
the first pass over this corpus joined 47 sightings and 7 pairs, and the merged
scanner joins 59 and 9 — same conclusion, different denominators. The `max 17`
row is new and NOT claimed as anything here; 17 is what a 20-energy character at
−15% would carry, but the census in §1.1 found only one non-baseline morale in
the corpus, so a second DP-affected agent is a *hypothesis this data does not
settle*.

**And the pip counts are the wiki's own table, read back off the wire.** GWW
("Energy" §Basic armor) gives 20 energy / 2 pips for a Warrior, 25 / 3 for a
Ranger, 25 / 4 for an Assassin or Dervish, 30 / 4 for the casters — which is
exactly the four non-zero rows above, including both 25-energy variants. Three
sources with no shared ancestry agree: the death tick's invariance, the corpus
join, and a table players wrote down.

> **CORROBORATED from a second arc, independently.** The energy/adrenaline
> session (worktree `friendly-chatelet-c2b4dc`) reached `0.33` from a different
> direction — a fit across the corpus plus a 52-of-52 integer-pips join against
> each agent's prop-41 — and reports client-render confirmation: their server
> sends property-62 debits, the client's energy readout tracks the server's
> integration to `floor()` across 15 frames, climbs at exactly the property-43
> rate, and draws **three regeneration arrows** for a 3-pip rate. That is
> UPSTREAM-of-a-peer until their branch lands (`studies/skills` §23,
> `test_pools`); what is checked HERE is the table above, which this repo can
> re-run.

### 2.4 Two stores, one number — MEASURED in the client's own memory

`0x009C` and `0x00EE` do not write the same place, and until 2026-08-20 that was
invisible: retail sends both on the same tick, so no capture can separate them.
Probe `morale_store` walked the attribute store through values only we could
have chosen while `moralestore.py` watched the client's memory (RUNS.md §Run 2):

| what the server sent | the attribute slot |
|---|---|
| `0x00E9` field 10 = 77, then 88, then 66 | 77, 88, 66 — absolute |
| **`0x00EE [10, −13]`** | **53** — applied |
| `0x009C [player, 41]` | **unchanged** |
| **`0x00EE [10, +7]`** | **60** — both directions |
| `0x00E9` field 10 = 100 | 100 — the control |

So:

- **`0x00E9` / `0x00EE` → the player's attribute block.** Absolute set and `+=`
  delta into the same slot. This is what the Hero window reads, and it is
  *silent*: nothing repaints when it changes.
- **`0x009C` → the per-agent morale.** This is what the top-left indicator reads
  (Run 1), and it names an agent because a party member's penalty is drawable
  too.

**A server that sends one and not the other leaves the other stale**, which is
why the death tick sends both — and now for a measured reason rather than
because retail happened to.

**The block's shape came free, and it corroborates the field map from the other
side.** Our three chosen values landed at exactly `attr_id × 8` from the
experience field, each stored **twice, adjacent**:

```
+0/+4     424242  experience    attr 0     0 × 8 = 0
+72/+76   17      level         attr 9     9 × 8 = 72
+80/+84   morale  morale        attr 10   10 × 8 = 80
+104/+108 13      skill points  attr 13   13 × 8 = 104
```

The wire's `attr_id` is an index into that array. `studies/character/STORAGE.md`
§2 described the value/dupe pairing from GWCA's header and could not check it;
this checks it against numbers of ours, at three predicted offsets, with nothing
else in ±0x80 moving.

### 2.5 The death tick's last two unknowns — MEASURED 2026-08-22

Both remaining message-level questions from §1's tables closed in one session,
each by a static walk plus one probe run ([RUNS.md](RUNS.md) Runs 5 and 6).

**Property 43's channel (MORALE-Q3): `0x00A2` and `0x00A3` are two doors to
one store.** Three independent legs, strongest last:

- SOURCED: both opcodes funnel to the float dispatcher `0x00818210`, whose
  case 3 is property 43 (`studies/agentprops` §1d/§3).
- OBSERVED, in a death batch: Run 3 arm A's frames, re-read against its wire,
  show the client drawing three regen arrows for a rate it only ever heard on
  `0x00A3` and integrating at exactly that rate (10 → 13 → 17 → 20 at 0.99/s
  after the first revive).
- OBSERVED, in isolation: `--probe regen_channel` zeroed the rate on `0x00A2`
  (flat bar at 3, five frames), sent six pips on `0x00A3` (climb at 1.94/s
  against the 1.98 sent, arrow count 0 → six), and stopped it again from
  `0x00A2`. One store, written from either channel, in both directions.

Two corollaries. Retail's 52-of-52 preference for `0x00A2` is a fidelity fact
about retail, not a constraint the client enforces — the spawn-burst move to
`0x00A2` stays correct and stays cosmetic. And Run 3's energy "drain" was
never a drain: the client's own death path kills regeneration, that tree's
grace-waived deaths re-armed nothing and its revives refilled nothing, so the
readout showed one re-armed climb window and then flat zero. **The cure in
the energy-arc merge was the handling — the death-zero, the revive refill,
the rate re-send — and the channel move was never load-bearing** (Run 4's
open question, closed).

**Property 54 (MORALE-Q4): a floating "+N" energy callout, and nothing else.**
The int path's pool dispatch ignores 54; its real arm (`0x00812E57`, in a
third dispatch the 2026-08-11 walk under-read — correction filed in
`studies/agentprops`) writes no store and queues AgentView EFFECT event kind
0x0D, whose drain posts UI event `0x1000000F` with the value
(`avevents.py --id 54`). At a live client, `[54, player, 13]` floated a
magenta **"+13"** over the player's head for under ~2 s, `[54, player, 5]`
floated **"+5"**, four sends moved no bar, no maximum and no corner — and the
property-41 positive control moved the maximum on cue. So retail's
`[54, 27, 22]` at the resurrect (§1) is the **"+22" the shrine refill draws**:
the value equals the new maximum only because the client zeroed its pool at
the death and the property-52 gain of 1.0 hands all of it back.
`restore_player_energy` now sends it in retail's position, and
`test_pools.py` §8b pins the batch.

---

## 3. The rules layer — WIKI

What the wire cannot tell us is when a death costs anything and what removes it.
GWW (page "Death Penalty", read 2026-08-20) states:

- **−15% per death**, cumulative, **capped at −60%**; Morale Boosts are capped at
  **+10%**. So morale runs 40…110, which is exactly the range GWCA's header
  annotates (`morale_percent … Ranges from 40 to 110`) — CORROBORATED, and the
  two sources share no ancestry.
- **Pre-Searing Ascalon never incurs DP.** Neither do town deaths during special
  events, non-damage scripted deaths, deaths within 14 s (PvE) of a resurrection,
  or several named PvP arenas.
- **Reset** when the party enters an outpost, when the party resigns, and between
  PvP matches. "Both Morale Boosts and Death Penalties remain until the party
  enters an outpost."
- **A grace window after a resurrection.** "Dying shortly after resurrection
  (5 seconds in PvP, 14 in PvE)" is on the same exception list, and it is the
  one a player notices at the keyboard: without it a party being wiped over and
  over reaches the −60% floor in under a minute, every one of those deaths
  landing while they are still standing up. Implemented as
  `[player.morale].resurrection_grace = 14` and `morale.death_is_free`, gated in
  `death_penalty_due` — the second of the two gates there, the first being the
  map. **Unit-tested; not yet watched at a client** (§7.1).
- **Reduced in PvE by experience: 75 XP removes 1% DP.** (In PvP: killing an
  enemy player removes 2% per living teammate.)
- Morale Boosts counter DP: if the boost exceeds the penalty the difference
  becomes a boost. Bosses give +2%.

**The pre-Searing exception is load-bearing for this repo**, because every map
this server ships is pre-Searing (145–148). A faithful server therefore gives
our own world **no** death penalty — which is why the implementation in §4 gates
acquisition on the map's own content row and ships every row with it off, and
why the switch that turns it on for a probe is a server flag rather than a lie
in the content.

---

## 4. What landed in the server

- `toolkit/authsrv/morale.py` — the arithmetic, pure and offline-testable:
  baseline, floor, ceiling, the base-vs-total rule, the level curve, the XP→DP
  counter and the regeneration rescale. No opcodes, no sends.
- `content/world.toml` `[player.morale]` — every constant the rule layer needs,
  wiki-sourced with the page cited and our own capture check in `verified`.
- `content/maps.toml` `[map_rule.<id>]` — does a death cost anything in this
  map. A separate KIND rather than a field on the map rows, because those rows
  are provenanced for their file ids and spawn points and a wiki-sourced boolean
  hanging under `source = "measured"` would be a quiet mislabel. Absent means
  false; 146 and 148 say false explicitly with the pre-Searing citation, 90 and
  558 say true.
- `authsrv.py` — the player carries a morale value and both pool maxima are
  computed through it (`player_max_health`, `player_max_energy`), so every
  damage fraction, heal and revive is against the penalised pool rather than the
  neutral one. `kill_player` emits retail's tick when `map_death_penalty` says
  the map charges; the revive re-sends the REDUCED maximum; each kill's 26 XP
  feeds the counter; the spawn burst now sends `0x009C [player, 100]`, which
  retail sends at login and we never did.
- `--death-penalty` forces acquisition on regardless of the map, so the mechanic
  can be watched in a world where retail would never fire it — the `--explorable`
  idiom, a switch rather than a lie in the content.
- `toolkit/authsrv/moralescan.py` — the corpus census, because "the only −15 in
  fourteen captures" is a claim that decays the moment a fifteenth is taken.
  **CORRECTED 2026-08-21, by the adrenaline arc, and the census claims are
  UNAFFECTED.** This scanner identified the receiving player by taking the
  FIRST `0x0059` and calling its agent ours, with a comment asserting that is
  what field 2 means. `0x0059` is `AGENT_CREATE_PLAYER`, broadcast for **every**
  player in the instance (16–56 in a busy outpost), so the first one is whoever
  the server sent first: MEASURED, **wrong on 20 of 44 connections**. It now
  anchors on property 41 (MAX ENERGY), which
  [studies/skills](../skills/FINDINGS.md) §23 measured as self-scoped over 97
  sightings, and it does not fall back — no property 41 leaves the flag unset.
  **The two census numbers above are unchanged** (40 `0x00EE` attr-10 sightings
  with only the −15 non-zero; 83 `0x009C` with only the 85), because they count
  values across all agents and never consulted the `mine` flag. A latent defect
  fixed before it was relied on. Full account: `studies/skills` §26.13.

Test: `toolkit/authsrv/test_morale.py`, catalogued in
[TESTS.md](../../TESTS.md).

---

## 5. What this corrects elsewhere in the repo

| Where | Said | Now |
|---|---|---|
| `character/FINDINGS.md` §1 field table | field 10 "**REFUTED as morale**" | The refutation is of the *display*, not the field: sending `0x00E9` with field 10 = 0/40/100/110 moved no indicator. The field IS morale (`0x00EE` attr 10 = −15 on the death tick, GWCA `Morale_Percent`), and the top-left indicator is driven by something else — `0x009C` is the candidate, MORALE-P2 |
| `combat/PLAN.md` §13, `authsrv.py` `GAME_SMSG_AGENT_KILL_REWARD` | `0x009C [agent, 100]` — "n=1, first-witness, uncatalogued", a marker for a non-kill broadcast burst | 83 sightings, one of them 85 on the death tick. `0x009C` = **per-agent morale percentage**. The burst finding stands (the `[10,0]`+`[0,X]` pair is not a kill shape); what changes is that attr 10 is no longer unknown — `[10, 0]` is a morale no-op riding an XP award |
| `agents.py` `PROP_UNKNOWN_FLOAT_43` | "Energy regeneration is the obvious reading and is a GUESS" | Energy regen as a fraction of max per second, OBSERVED by the rescale in §2.3. Renamed |
| `authsrv.py` spawn burst | sends property 43 on `0x00A3` (float-target) | retail sends it on `0x00A2` (plain float). Moved 2026-08-22 (`1d2ce82`, RUNS.md §Run 4); MORALE-Q3 then measured the two channels equivalent (§2.5), so the move is fidelity, not function |
| `authsrv.py` `player_revive_due` docstring | "no PLAYER death was found in either live capture, so this is our agent-death path pointed at PLAYER_AGENT_ID" | There is one now, in the 2026-08-17 capture, and the revive it shows is a **shrine respawn**: position moves, out-of-range agents are removed, pools refill through `0x00A2` 52/55 rather than through property 34 |

---

## 6. Open questions

| id | question | why it is not answered here |
|---|---|---|
| ~~MORALE-Q1~~ | Which message drives the top-left DP indicator: `0x009C`, `0x00EE`, or both? | **ANSWERED 2026-08-20 — `0x009C`.** `[player, 70]` alone drew a red `−30%` chevron at (10,32)–(60,82); `0x00EE [10, −15]` alone drew nothing over three frames and 9.2 s. RUNS.md §Run 1 |
| ~~MORALE-Q2~~ | Does the client recompute the maxima itself from morale, or only display what the server sends? | **ANSWERED 2026-08-20 — it displays ours.** One frame carries it: at t+16.4 the corner reads `−30%` while the bars still read 100 and 25. Properties 41/42 then set them, and the energy bar showed the **14** we sent rather than the 19 its own arithmetic would give |
| ~~MORALE-Q3~~ | `0x00A2` vs `0x00A3` for property 43 | **ANSWERED 2026-08-22 — two doors, one store.** (The separation arm had been ruled not owed that same morning — RUNS.md §Run 4's assessment — and the answer then arrived by a cheaper instrument: a desk re-read plus one probe, no revert built.) Statically both opcodes funnel to dispatcher `0x00818210` case 3; Run 3 arm A's own frames show the client integrating at an A3-sent rate (0.99/s, three arrows); and `--probe regen_channel` walked it in isolation — a `0x00A2` zero flattens the bar, six pips on `0x00A3` restart the climb at 1.94/s with six arrows, a `0x00A2` zero stops it again. The "drain" the energy arc's merge cured was the merge's HANDLING (revive refill + rate re-send), never the channel. §2.5, RUNS.md Run 5 |
| ~~MORALE-Q4~~ | int property 54 at the revive (= 22, the new max energy) | **ANSWERED 2026-08-22 — a floating "+N" energy callout, display-only.** The int path writes no store for 54: its arm queues AgentView EFFECT kind 0x0D → UI event `0x1000000F`. `--probe prop54` sent 13 then 5 and a magenta "+13" / "+5" floated over the player for under ~2 s each, while four sends moved no bar and the property-41 control did. The 22 was the refill amount, equal to the maximum because the client zeroes its pool at death. §2.5, RUNS.md Run 6 |
| MORALE-Q5 | Morale BOOSTS | zero sightings in the corpus. +10% is WIKI only, and the `[40, 110]` range is UPSTREAM (GWCA) |
| MORALE-Q6 | Does DP survive a map change on the wire, and what resets it? | our corpus has no death followed by a zone. WIKI says an outpost resets it; the ATTR_SET at every login carries 100, which is consistent but is not the same claim |
| ~~MORALE-Q7~~ | Does `0x00EE`'s delta update the client's stored morale without repainting? | **ANSWERED 2026-08-20 — yes, it writes.** Read out of the client's own memory: `66 → 53` on a `−13` and `53 → 60` on a `+7`, within one 0.5 s sample each, while `0x009C [player, 41]` moved that slot not at all. Two channels, two stores. RUNS.md §Run 2, §2.4 below |

## 7. The probe — RAN 2026-08-20, GREEN

Loopback, our own client, our own server, agent-piloted with no operator input.
Full sheet: [RUNS.md](RUNS.md) §Run 1. Predictions were registered before the
run and are scored here as written:

| id | prediction | result |
|---|---|---|
| MORALE-P1 | `0x00EE [10, −15]` alone draws the indicator | **REFUTED** — nothing, three frames, 9.2 s |
| MORALE-P2 | `0x009C [player, 85]` alone draws it instead | **CONFIRMED** — red chevron, `−30%`, at 70 |
| MORALE-P3 | the globes do not move until properties 41/42, and then read OUR numbers | **CONFIRMED** — `−30%` displayed beside untouched 100/25 bars, then 14 and 70 |
| MORALE-P4 | `0x009C [player, 110]` draws a BOOST, not a penalty | **CONFIRMED** — the chevron flips up and turns teal, `+10%` |
| control | `0x00EE [10, 0]`, retail's own no-op, changes nothing | **HELD** — eleven frames, 34 s |

**The one that mattered was P3, and it was designed to be able to fail.** The
energy maximum was sent as **14** rather than the 19 that −30% of base 20
actually gives, so a client computing its own answer would have disagreed with
us visibly. It showed 14. Morale is a *display* to the client and an
*arithmetic* to the server, and a server that sends the percentage without the
recomputed pools ships a death penalty that costs the player nothing.

### 7.1 A real death, with the penalty armed — RAN 2026-08-22, GREEN

Two arms, both agent-piloted on loopback: [RUNS.md](RUNS.md) §Run 3, captures
`20260822T140922` and `20260822T141510`. Nothing was placed on the wire by hand
— an enemy killed the player and `kill_player` did the rest.

- **The waiver holds.** Deaths 12.6 s apart from each resurrection: the first
  charged, the next four were waived, the log naming the window each time, and
  the corner sat at `−15%` for 81 s and 27 frames while four more deaths
  happened. The rule the owner remembered is on screen.
- **The expiry, and the whole ladder.** With the hostile limited to a self-heal
  the melee swing needs 16.1 s per death — just outside the window — so every
  death charges: `−15% → −30% → −45% → −60%`, health 85 → 70 → 55 → 40, energy
  22 → 19 → 16 → 13, and then **the corner holds at −60% for the last 27 s**.
  The cap is watched rather than asserted.
- **§2.2's discriminating claim, four more times.** The energy ladder falls by
  exactly 3 a rung — 15% of BASE energy 20, never of the 25 total, which would
  have given 21.25 / 18.06 / 15.35 / 13.05 and matched at no rung.

One honest correction the run forced: `--enemy-hit` scales the melee swing, and
in the first arm the killing blows came from the hostile's SKILL (46 damage a
cast). The flag still produced the fast death it was added for, but it was not
the channel doing the killing, and the run sheet says so.

An earlier attempt at this run was lost to a parallel session's
`session.py --replace` stopping this session's live webgate and authsrv
(client `Code=058`). Nothing was measured that time and nothing about the code
was in doubt.

**What the earlier runs also cost, worth writing down.** The indicator sits at
(10,32)–(60,82) — above the party window, under the title bar. The first crop
of these frames started at y=100, found nothing, and for several minutes read
as a refutation of P1 *and* P2. The HUD also repaints on a delay of roughly
1–4 s rather than on the packet, in 3 of 3 cases; a probe reading it wants ≥5 s
between a send and its screenshot.
