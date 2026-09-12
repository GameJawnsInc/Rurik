# The vertical slice — what is missing, and in what order

**Written 2026-09-11** from a six-lane recon sweep over this tree at `8581f578`, plus
direct verification of the load-bearing claims at the call sites. This document is the
arc's plan. **Status authority stays [PLAN.md](../../PLAN.md) §3** — nothing here
reports a rung as landed, and when one lands it is dated and stamped there, not here.

**Identifiers.** `SLICE-G<n>` = a gate of the slice; `n` is the owner's own step number,
so `SLICE-G3` is always "zone to the explorable". `SLICE-B<n>` = a build item, a thing to
do. `SLICE-U<n>` = an unknown — a thing that must be MEASURED before the build item
depending on it can be honestly costed. Convention:
[studies/idents/CONVENTION.md](../idents/CONVENTION.md).

---

## 0. The ask, and the owner's decisions

The slice the owner asked for, 2026-09-11:

1. Start in an outpost, take a quest from an NPC.
2. One hero unlocked, a Monk hero.
3. Zone to an explorable area; the quest is to kill a monster.
4. Two authored monster types with different skill bars — one warrior, one monk that heals.
5. A straight-corridor explorable: two groups of two, then the quest boss. A real boss
   with the stock game's aura if time permits.
6. Return to the outpost; the quest completes.

**Owner's decisions, 2026-09-11, taken on this document's first draft:**

- **SLICE-U3 (zoning) takes the REAL route.** No reconnect shim. The server learns to
  send `0x01A5 GAME_SERVER_TRANSFER` and to be re-entered, rather than the client being
  quit to character select between maps. Recorded because the shim was offered and
  declined: a shim would have reached a playable slice sooner and would not have been
  kept.
- **SLICE-U2 (monster appearance) is settled by a MODEL PARADE**, not by picking ids off
  a table. The owner did not name two creatures, and under SLICE-U2 naming them first
  would not have helped: what the repo lacks is not a preference but a rendered
  observation of what each shell draws.
- **SLICE-U1 (the boss aura) gets the decode pass**, rather than shipping a boss as
  scaled health and a nastier bar with the glow deferred.

---

## 1. The six gates

Three buckets throughout, and the distinction is the whole point of the table: **PROVEN**
means a retail client did it and somebody watched; **UNBUILT** means we know how and
nobody has written it; **UNKNOWN** means a measurement is missing and the cost cannot be
stated until it is taken.

| Gate | PROVEN today | UNBUILT | UNKNOWN |
|---|---|---|---|
| **SLICE-G1** outpost → NPC → quest | The whole dialogue machinery: the offer screen, the in-progress `?`, the turn-in, the option click, the quest log, the overhead markers, and one authored quest whose NAME renders from our own archive record. `_quest_lines` at `authsrv.py:211`, `_handle_interact` at `authsrv.py:352`, `_send_markers` at `authsrv.py:741` | The giver and objective NPCs are not spawned in ordinary play. **But see SLICE-B1 — this is smaller than the recon reported** | — |
| **SLICE-G2** one Monk hero | Hero creation, the roster row, the commander panel, the 8-slot bar, the `Mo` profession — all rendered on a real client behind the `--hero*` flags. `hero_slots` at `authsrv.py:8792`, `mercenary_info` at `agents.py:760`, `hero_activate` at `agents.py:861` | **Hero follow and hero casting, both absent outright.** `begin_cast` at `authsrv.py:13380` reads player-only pools; `land_skill` at `authsrv.py:16956` lands on the player; `enemy_attack_tick` at `authsrv.py:15082` runs only for hostiles; `allies_of` at `skillread.py:120` hardcodes the player to zero allies | Whether a hero can wear a real human/Monk body rather than the monster-composite path that has been used for every hero rendered so far |
| **SLICE-G3** zone to the explorable | `0x01A5` is decoded end to end, including the trap that the SECOND transfer of a session defers its dial and is released only by a graceful half-close — `close_after_transfer` at `scriptrun.py:233`, `TRANSFER_OPCODES` at `tape.py:429`. **AND the trigger is now measured: 34 of 41 retail transfers are SERVER-INITIATED with no client request at all** (SLICE-F8) | The server never sends `0x01A5` outside tape playback; `state["map_id"]` is written only at connection setup | ~~What the client SENDS to ask for a transfer~~ — **`0x00B1`, destination in field[1], 7 of 7** |
| **SLICE-G4** two monster types, two bars | Content row → agent, with set-level safety checks (`area_population` at `authsrv.py:17631`); autonomous aggro, chase and swing; **NPC skill casting including an ALLY-TARGETED HEAL already ships** (`resolve_heal` at `authsrv.py:14440`, reached from `land_skill`); the client's whole 1,333-row skill table | Per-row skill bar, armour, attack speed and level — `spawn_population` at `authsrv.py:17732` hands every row the global `ENEMY_SKILLS` at `authsrv.py:10221` and sets no `armor_rating` at all. Only 22 of 1,333 skills have a resolvable effect | Which creature each loadable shell actually DRAWS |
| **SLICE-G5** corridor, 2+2, boss | `build_flat` at `mapbuild.py:826` is client-verified for load AND for collision against authored geometry; `GENERATORS` at `mapgen.py:385` makes a new height profile a small addition | A corridor generator; group/pull/patrol/leash semantics (each monster aggros independently) | A non-square footprint has never been live-verified. ~~The boss aura is NOT FOUND as a feature~~ — **the glow is DECODED, [FINDINGS.md](FINDINGS.md) SLICE-F1: one int property on the boss's agent** |
| **SLICE-G6** return, complete | The turn-in path, proven on retail | **Nothing connects a kill to quest state**; **no reward is ever granted** | — |

---

## 2. The build ladder

Ordered so that each item is demonstrable on its own, and so the two long poles
(SLICE-B5, SLICE-B7) start after the cheap items have made the slice inspectable.

| Item | What | Size |
|---|---|---|
| **SLICE-B1** | **The quest giver as content, not as a probe.** The recon lane reported "no code spawns a quest giver in ordinary play", and that is true but misleading: `_quest_lines` at `authsrv.py:211` and `_objective_quests` at `authsrv.py:250` bind by BARE AGENT ID, and `area_population` lets a spawn row choose any id. So a `[spawn.*]` row with `agent_id = 99`, `allegiance = "noncombatant"` IS the giver, with no server change. What is genuinely owed is the row set, a check that `INTERACT` reaches an area-spawned body, and replacing the bare-id binding with a spawn-key one so the quest row stops naming a number | a session |
| **SLICE-B2** | **Per-row monster stat blocks.** Thread `skills`, `armor_rating`, `attack_speed` and `level` through `spawn_population`. The entry dict already carries every one of these keys on the legacy single-enemy path (`ENEMY_ARMOR_RATING` at `authsrv.py:9221`, from `creature_armor_rating` at `combatmath.py:87`); the area path simply does not populate them. Until this lands, "two archetypes" cannot mean anything mechanical, and the player's swing against an area-spawned body silently runs with no armour term | a session |
| **SLICE-B3** | **`skill_effect` rows for both bars.** 22 of 1,333 skills resolve today; each new one is a hand-authored row with a wiki citation saying what its scale MEANS. The warrior bar and the monk bar need theirs. **One trap, named now:** both working ally-heals (Restore Condition 276, Mend Ailment 277) are CONDITION-GATED and heal nothing against an unconditioned target, so a convincing monk monster needs an unconditional heal wired as well | a day |
| **SLICE-B4** | **The kill-count verb.** `kill_agent` at `authsrv.py:11800` is a single choke point — one hook, and a quest row gains a kill objective beside its talk objective. The manifest's six-verb census ([studies/presearing/MANIFEST.md](../presearing/MANIFEST.md) §"The six verbs") says dialogue and kill-count are all this slice needs | a session |
| **SLICE-B5** | **The reward grant.** Absent entirely: the completion family is 0 of 22,524 in the corpus and exists only as probe arms in `probequest.py`. The PANEL is proven to render; the GRANT is our own state, and the XP path already exists (`accrue_kill_rewards` at `authsrv.py:2820`). So this is authorship, not archaeology — and it should be labelled as ours rather than dressed as retail's | a day |
| **SLICE-B6** | **The corridor.** A `gen_corridor` profile in `mapgen.py`, an `[area.*]` row, and a live run to close SLICE-U4. `_gate_dims` at `terrain.py:875` permits a non-square footprint; nothing has tried one on a client | a session |
| **SLICE-B7** | **Hero follow and hero casting.** The long pole. Split into three, and **two are DONE (2026-09-12)**: **B7a** `allies_of` learns the party — the hardcoded `return set()` for the player is gone, and the asymmetry it had to learn is that the player is not a row in `agents` at all. **B7b** the party body FOLLOWS — the hostile follow with two numbers made arguments (an infinite leash, a 200 u formation stop), not a second follow; **proven on a real client**, 7 follows against 0 under `--no-hero-follow` ([FINDINGS.md](FINDINGS.md) SLICE-F9). **B7c REMAINS:** the hero does not CAST. `begin_cast` reads player-only pools and `land_skill` names `PLAYER_AGENT_ID` at six sites, so it needs a recipient parameter and an ally target-selection tick | **B7c: a session or two** |
| **SLICE-B8** | **The transfer, sent by us.** After SLICE-U3. Send `0x0028 → 0x01A5 → 0x0099`, close gracefully per `close_after_transfer`, accept the re-entry, carry state across it. Quest state already survives a reconnect by accident of design — `QUEST_PROGRESS` at `authsrv.py:668` is a module-level singleton and `bind_progress` at `authsrv.py:671` re-points each new connection at it — which is the one piece of zoning that works today | an arc |
| **SLICE-B9** | **One archive.** See §5 | a session |

**Not in this ladder, and deliberately:** quest state per character and on disk. It is a
real defect — `QUEST_PROGRESS` is process-global, so two characters against one server
share one quest log, and `charstore.py` has no quest fields — but nothing in the slice
exercises it, and naming it here is cheaper than building it now.

---

## 3. The unknowns, and how each is settled

| Item | The unknown | How it is settled | Prediction, stated first |
|---|---|---|---|
| **SLICE-U1** | Whether the boss aura is reachable from the server | ~~Decode pass — see §4~~ **CLOSED 2026-09-11 at the desk, prediction held: [FINDINGS.md](FINDINGS.md) SLICE-F1.** A boss glow is ONE int property on the boss's agent, `[agent_id, index]`, index 0..10 | Property 29 is applied by the server as a plain int property on the boss's agent, and the value selects a row of the client's own `s_glow` table |
| **SLICE-U2** | What each loadable creature shell DRAWS | ~~The model parade — registered, not yet run~~ **RAN 2026-09-11 and SCORES: [FINDINGS.md](FINDINGS.md) SLICE-F7, [RUN-PARADE.md](RUN-PARADE.md) §4a.** 15 of 15 legible, control drew its box, fifteen nameplates, ten joined to a template on evidence. **The slice's pair is Bandit Raider (`def_1421`) + the Academy Monk body (`def_1486`) spawned hostile** -- both confirmed alone in an empty world by the ten one-body finisher runs, after the profession-byte join put the Academy Monk on the wrong row | Most render a recognisable creature; a minority draw the white untextured box that a withheld composite produces, and that failure is self-announcing. **HELD: 14 creatures, 1 box, and the box was the one we withheld** |
| **SLICE-U3** | What the client sends to request a transfer | ~~Desk study first, no run~~ **DONE 2026-09-11, [FINDINGS.md](FINDINGS.md) SLICE-F8: `0x00B1` carries the destination map and is the last c2s before the handoff, 7 of 7 — but 34 of 41 transfers have NO request, so SLICE-B8 does not depend on it** | There is a c2s immediately before the tail, and it is one of the seven opcodes the live client sends that our labelled loopback runs never produced. **HELD, and then some**: `0x00B1` is such an opcode, and its field[1] IS the destination |
| **SLICE-U4** | Whether the client accepts an elongated map footprint | One live run under SLICE-B6 | It does; `_gate_dims` forbids nothing about the aspect ratio and the square case is closed |
| **SLICE-U5** | Whether a hero can wear a human/Monk body | One run, once SLICE-B7 has something worth dressing | Untested either way. Recorded so the answer is not assumed from the monster-composite path having worked |

**SLICE-U2 is why the owner's "suggestions" question could not be answered by naming two
creatures.** Only the Hatcher (`file_id` 116228, `model_id` 116703) has ever been WATCHED
rendering; the `profession` byte is not a species hint — the arc that measured it found a
"Warrior" on a legless worm. Thirty-one other shells are proven to resolve closed against
the archive, so they will load; what they draw is unrecorded. The parade converts that
from a per-session guess into a table.

---

## 4. The boss aura — the decode RAN, and it went further than the pass was scoped for

**Superseded by [FINDINGS.md](FINDINGS.md) SLICE-F1..F6, 2026-09-11.** This section is
kept as the question it started as; the answers are there.

What it started as: **NOT FOUND as a feature** — no aura, no glow, no boss flag, no
boss-scaled stats anywhere in this tree — with two structurally real leads, the client's
int-property case for 29 and the located-but-undecoded `s_aura` / `s_glow` tables.

**What the decode pass actually returned, in one line each:**

- **The whole path closes with no run** (SLICE-F1). Wire property 29 → `0x00812CBC`, which
  is two pushes and a call → the setter at `0x007DFD70` → a forwarder → `s_glow[index]`,
  bound `< 11` by the client's own `cmp esi, 0xb`, three bytes ÷ 255.0. **A boss glow is
  ONE int property on the boss's agent.** That is a far cheaper boss than this plan
  costed, and SLICE-G5's "if time permits" is no longer the right framing.
- **`s_aura`'s middle column is a client file id**, 44 of 44 binding against controls at
  26/44 and 22/44 (SLICE-F4), and its third column is `0x64000000` — the same tint/scale
  word `content/npcs.toml` already carries.
- **Properties 6 and 7 are apply/remove of one function**, differing by a single pushed
  immediate (SLICE-F5), which CORROBORATES OpenTyria's names from structure rather than
  taking them on trust.
- **The appealing wrong answer is named and refused** (SLICE-F3): 11 rows matches
  `CHAR_PROFESSIONS = 11`, the lore says boss auras are profession-coloured, and the
  colours do not support it under either channel order.

**One bit is left and it has a registered prediction** (SLICE-F2): send property 29 with
index 5 and the aura renders RED if `+4` is the red channel. Ids 3 and 4 are palindromic
and would have proven nothing, which is why the probe names 5.

The standing caveat travels with all of it: a loopback probe measures OUR server driving a
retail client. That is exactly the right instrument for "does the client draw a glow when
told to", and no instrument at all for "is this what ArenaNet sends" — which remains 0 of
22,524.

---

## 5. Two things nobody had written down

**The archive-integration problem (SLICE-B9).** `vault/run/` holds six run directories,
each a separate `Gw.dat` with different authored content. The quest name renders only
against `reskin-roster`; the created map chains (165/166/167) live only in a July probe
directory and in none of the current run dirs. The slice needs **one archive** carrying
the corridor geometry, the quest string, and any authored creature names at once. That
assembly has never been done, and every previous run reached its result by running against
whichever archive happened to hold the one thing it was testing.

**The retail zoning pair is mechanically cheap and visually null.** Map 148 (Ascalon City,
outpost) and map 146 (Lakeside County, explorable) carry the SAME `file_id` 113021 and the
SAME arrival point (9826, 8077) in `content/maps.toml` — Pre-Searing is one continuous
terrain, and 146's row says outright that the coordinate is Ascalon's, reused, because
gw-preservation records no spawn for Lakeside. So 148 → 146 is the cheapest possible test
of SLICE-B8 — same archive, same mesh, known-good arrival, one byte of `is_explorable`
different — and it will look like nothing happened. **That is a feature for the first
milestone and a trap for the demo**, so SLICE-B8 splits: prove the transfer against
148 → 146, then re-point it at the authored corridor, which is a different `file_id` and
needs SLICE-B9 first.

---

## 6. What this document does not claim

- **No effort figure here is measured.** "a session / a day / an arc" is judgement from
  the shape of the change, and the repo's own history says the direction of error is
  optimism — R3 was estimated at "a quarter, not a week" and took six hours, and the
  hero arc was estimated at nothing like the two arcs it consumed.
- **The six lanes that produced the survey were recon, not audit.** Each read a subject
  and reported; where a lane's conclusion is load-bearing here it was re-checked at the
  call site, and one was CORRECTED in the process (SLICE-B1 — "no code spawns a quest
  giver" is true and is not the cost it implies). Lane conclusions not re-checked are
  marked by their absence from the citation list, which is the honest signal.
- **Nothing here says the slice is close.** Four gates rest on plumbing a retail client
  has already exercised; two rest on logic nobody has written. The hero is the long pole
  and it is a whole arc on its own.
