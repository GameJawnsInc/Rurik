# Morale and Death Penalty — what a death costs, on retail's own wire

**Written 2026-08-20.** The question this closes has been open since 2026-08-05:
`0x00E9` field 10 is called `morale` by every lineage, our own probe found that
setting it moves nothing on screen, and the server has shipped it as a zero ever
since with a comment saying so. What "100%" means was nobody's answer.

It is answered now, and not by reasoning: **the live corpus contains exactly one
player death**, and it is fully instrumented. Everything in §1 and §2 is read off
that tick.

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
| 88.857 | `0x009F` | `[54, 27, 22]` | int 54 = the new maximum energy again. UNVERIFIED |
| 88.857 | `0x00A2` | `[55, 27, 1.0f]` | armor-ignoring heal, full pool |
| 88.857 | `0x0026` | `[27, 5]` | flags on the revived player |

**The maxima are NOT restored at the resurrection**, and that is the point of
the mechanic: 102/22 stand until something removes the penalty (§3).

**The baseline is on the wire too.** At login (t = 0.897) the same connection
sends `0x009C [27, 100]`, then `0x00E9` with field 10 = 100, then the pools:
`0x009F [41, 27, 25]`, `0x00A2 [43, 27, 0.0528f]`, `0x009F [42, 27, 120]`.
So 100 is the neutral value, sent explicitly, on both channels.

### 1.1 Why one sighting is enough here

n=1 is normally where this repo stops. Three things make this one carry:

- **The number appears twice, on two channels, in two encodings, in the same
  tick.** `100 − 15 = 85` is the delta on `0x00EE` and the absolute on `0x009C`.
  A coincidence would have to agree in arithmetic as well as timing.
- **Both maxima move by exactly the predicted amount** (§2), computed from a
  rule written down independently by players (WIKI) and from base values that
  the same tape states (level 2 → 120 health; 25 energy).
- **The corpus-wide census refuses the alternative.** Across all 14 live
  captures and 43 game connections: `0x00EE` carries attr 10 forty times and
  **the only non-zero value in the corpus is this −15**; `0x009C` fires 83 times
  and **the only value that is not 100 is this 85**. Scanner:
  `toolkit/authsrv/moralescan.py`.

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

Test: `toolkit/authsrv/test_morale.py`, catalogued in
[TESTS.md](../../TESTS.md).

---

## 5. What this corrects elsewhere in the repo

| Where | Said | Now |
|---|---|---|
| `character/FINDINGS.md` §1 field table | field 10 "**REFUTED as morale**" | The refutation is of the *display*, not the field: sending `0x00E9` with field 10 = 0/40/100/110 moved no indicator. The field IS morale (`0x00EE` attr 10 = −15 on the death tick, GWCA `Morale_Percent`), and the top-left indicator is driven by something else — `0x009C` is the candidate, MORALE-P2 |
| `combat/PLAN.md` §13, `authsrv.py` `GAME_SMSG_AGENT_KILL_REWARD` | `0x009C [agent, 100]` — "n=1, first-witness, uncatalogued", a marker for a non-kill broadcast burst | 83 sightings, one of them 85 on the death tick. `0x009C` = **per-agent morale percentage**. The burst finding stands (the `[10,0]`+`[0,X]` pair is not a kill shape); what changes is that attr 10 is no longer unknown — `[10, 0]` is a morale no-op riding an XP award |
| `agents.py` `PROP_UNKNOWN_FLOAT_43` | "Energy regeneration is the obvious reading and is a GUESS" | Energy regen as a fraction of max per second, OBSERVED by the rescale in §2.3. Renamed |
| `authsrv.py` spawn burst | sends property 43 on `0x00A3` (float-target) | retail sends it on `0x00A2` (plain float). Left alone for now — MORALE-Q3 |
| `authsrv.py` `player_revive_due` docstring | "no PLAYER death was found in either live capture, so this is our agent-death path pointed at PLAYER_AGENT_ID" | There is one now, in the 2026-08-17 capture, and the revive it shows is a **shrine respawn**: position moves, out-of-range agents are removed, pools refill through `0x00A2` 52/55 rather than through property 34 |

---

## 6. Open questions

| id | question | why it is not answered here |
|---|---|---|
| MORALE-Q1 | Which message drives the top-left DP indicator: `0x009C`, `0x00EE`, or both? | needs a client. Probe below |
| MORALE-Q2 | Does the client recompute the maxima itself from morale, or only display what the server sends? | The server sent both maxima explicitly, so the client never had to. A probe that sends morale WITHOUT the maxima separates them |
| MORALE-Q3 | `0x00A2` vs `0x00A3` for property 43 | retail uses the plain channel; we use the target channel and the client has never complained. Both may be accepted |
| MORALE-Q4 | int property 54 at the revive (= 22, the new max energy) | one sighting, no second value, no upstream name |
| MORALE-Q5 | Morale BOOSTS | zero sightings in the corpus. +10% is WIKI only, and the `[40, 110]` range is UPSTREAM (GWCA) |
| MORALE-Q6 | Does DP survive a map change on the wire, and what resets it? | our corpus has no death followed by a zone. WIKI says an outpost resets it; the ATTR_SET at every login carries 100, which is consistent but is not the same claim |

## 7. The probe — `--probe morale`, predictions registered first

Loopback, our own client, our own server. Fixed-position HUD readout, so it is
agent-pilotable under the 2026-08-17 boundary
(`feedback-owner-drives-client-runs`), but it still needs the owner's go-ahead
to launch a client.

| id | step | prediction |
|---|---|---|
| MORALE-P1 | `0x00EE [10, −15]` alone | If the DP indicator appears top-left, attr 10 drives the display and `0x00E9`'s refutation was about the full-set message only |
| MORALE-P2 | `0x009C [player, 85]` alone | If the indicator appears here instead, the display is the per-agent channel, and MORALE-Q1 is answered the other way |
| MORALE-P3 | either of the above, with **no** property 41/42 | If the health/energy globes shrink anyway, the client recomputes the maxima from morale (MORALE-Q2 = client-side). If they do not move, the maxima are the server's job and ours must send them |
| MORALE-P4 | `0x009C [player, 110]` | +10% is the wiki's ceiling and the corpus has never carried a boost. A boost icon rather than a DP icon is the confirmation |

A run that produces MORALE-P1 and MORALE-P3 answers both open questions that
matter for the server, in one session, without a death.
