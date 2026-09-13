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
| **SLICE-G1** outpost → NPC → quest | The whole dialogue machinery: the offer screen, the in-progress `?`, the turn-in, the option click, the quest log, the overhead markers, and one authored quest whose NAME renders from our own archive record. `_quest_lines` at `authsrv.py:250`, `_handle_interact` at `authsrv.py:622`, `_send_markers` at `authsrv.py:1010` | The giver and objective NPCs are not spawned in ordinary play. **But see SLICE-B1 — this is smaller than the recon reported** | — |
| **SLICE-G2** one Monk hero | Hero creation, the roster row, the commander panel, the 8-slot bar, the `Mo` profession — all rendered on a real client behind the `--hero*` flags. `hero_slots` at `authsrv.py:9214`, `mercenary_info` at `agents.py:760`, `hero_activate` at `agents.py:861` | **Hero follow and hero casting, both absent outright.** `begin_cast` at `authsrv.py:13866` reads player-only pools; `land_skill` at `authsrv.py:17686` lands on the player; `enemy_attack_tick` at `authsrv.py:15579` runs only for hostiles; `allies_of` at `skillread.py:120` hardcodes the player to zero allies | Whether a hero can wear a real human/Monk body rather than the monster-composite path that has been used for every hero rendered so far |
| **SLICE-G3** zone to the explorable | `0x01A5` is decoded end to end, including the trap that the SECOND transfer of a session defers its dial and is released only by a graceful half-close — `close_after_transfer` at `scriptrun.py:233`, `TRANSFER_OPCODES` at `tape.py:429`. **AND the trigger is now measured: 34 of 41 retail transfers are SERVER-INITIATED with no client request at all** (SLICE-F8) | The server never sends `0x01A5` outside tape playback; `state["map_id"]` is written only at connection setup | ~~What the client SENDS to ask for a transfer~~ — **`0x00B1`, destination in field[1], 7 of 7** |
| **SLICE-G4** two monster types, two bars | Content row → agent, with set-level safety checks (`area_population` at `authsrv.py:18375`); autonomous aggro, chase and swing; **NPC skill casting including an ALLY-TARGETED HEAL already ships** (`resolve_heal` at `authsrv.py:14937`, reached from `land_skill`); the client's whole 1,333-row skill table | Per-row skill bar, armour, attack speed and level — `spawn_population` at `authsrv.py:18481` hands every row the global `ENEMY_SKILLS` at `authsrv.py:10664` and sets no `armor_rating` at all. Only 22 of 1,333 skills have a resolvable effect | Which creature each loadable shell actually DRAWS |
| **SLICE-G5** corridor, 2+2, boss | `build_flat` at `mapbuild.py:826` is client-verified for load AND for collision against authored geometry; `GENERATORS` at `mapgen.py:431` makes a new height profile a small addition | A corridor generator; group/pull/patrol/leash semantics (each monster aggros independently) | A non-square footprint has never been live-verified. ~~The boss aura is NOT FOUND as a feature~~ — **the glow is DECODED, [FINDINGS.md](FINDINGS.md) SLICE-F1: one int property on the boss's agent** |
| **SLICE-G6** return, complete | The turn-in path, proven on retail | **Nothing connects a kill to quest state**; **no reward is ever granted** | — |

---

## 2. The build ladder

Ordered so that each item is demonstrable on its own, and so the two long poles
(SLICE-B5, SLICE-B7) start after the cheap items have made the slice inspectable.

| Item | What | Size |
|---|---|---|
| **SLICE-B1** | **The quest giver as content, not as a probe.** The recon lane reported "no code spawns a quest giver in ordinary play", and that is true but misleading: `_quest_lines` at `authsrv.py:250` and `_objective_quests` at `authsrv.py:438` bind by BARE AGENT ID, and `area_population` lets a spawn row choose any id. So a `[spawn.*]` row with `agent_id = 99`, `allegiance = "noncombatant"` IS the giver, with no server change. What is genuinely owed is the row set, a check that `INTERACT` reaches an area-spawned body, and replacing the bare-id binding with a spawn-key one so the quest row stops naming a number | **DONE 2026-09-12** ([FINDINGS.md](FINDINGS.md) SLICE-F11) |
| **SLICE-B2** | **Per-row monster stat blocks.** Thread `skills`, `armor_rating`, `attack_speed` and `level` through `spawn_population`. The entry dict already carries every one of these keys on the legacy single-enemy path (`ENEMY_ARMOR_RATING` at `authsrv.py:9664`, from `creature_armor_rating` at `combatmath.py:87`); the area path simply does not populate them. Until this lands, "two archetypes" cannot mean anything mechanical, and the player's swing against an area-spawned body silently runs with no armour term | **DONE 2026-09-12.** Every default is today's behaviour, so a row that says nothing spawns what it always did; armour is DERIVED from the row's level rather than defaulted; an EMPTY bar is a real answer and does not fall through. `test_population` §6 |
| **SLICE-B3** | **`skill_effect` rows for both bars.** 22 of 1,333 skills resolve today; each new one is a hand-authored row with a wiki citation saying what its scale MEANS. The warrior bar and the monk bar need theirs. **One trap, named now:** both working ally-heals (Restore Condition 276, Mend Ailment 277) are CONDITION-GATED and heal nothing against an unconditioned target, so a convincing monk monster needs an unconditional heal wired as well | **DONE 2026-09-12** ([FINDINGS.md](FINDINGS.md) SLICE-F15): Orison of Healing 281 (the unconditional heal) and Banish 252 rowed -- both CONTESTED-by-generation against GWW's 2026-08-26 balance update, the client's numbers kept; the corridor's bars set; `HERO_SKILLS` defaults to (281, 276); a hostile's HEAL aims at whoever is hurt (`hostile_heal_target`) and is held otherwise, gated on heals only. Two defects found by running and fixed (a re-pick loop that fell out with a heal aimed at the player; Healing Signet at full health). **Unobserved on a client:** the heal landing on a hurt raider -- the level-1 player cannot get one under 90% past its self-heal |
| **SLICE-B4** | **The kill-count verb.** `kill_agent` at `authsrv.py:12282` is a single choke point — one hook, and a quest row gains a kill objective beside its talk objective. The manifest's six-verb census ([studies/presearing/MANIFEST.md](../presearing/MANIFEST.md) §"The six verbs") says dialogue and kill-count are all this slice needs | **DONE 2026-09-12** (the verb; `test_quests` §22). The objective-completion body was EXTRACTED to one `complete_objective` rather than copied -- two copies of the description guard would drift silently. **WIRED 2026-09-12**: `[quest.rurik_bandits]` (1464, record 201 in the slice archive), `objective_kill = "corridor_boss"`, `test_quests` §24 |
| **SLICE-B5** | **The reward grant.** Absent entirely: the completion family is 0 of 22,524 in the corpus and exists only as probe arms in `probequest.py`. The PANEL is proven to render; the GRANT is our own state, and the XP path already exists (`accrue_kill_rewards` at `authsrv.py:3242`). So this is authorship, not archaeology — and it should be labelled as ours rather than dressed as retail's | **DONE 2026-09-12, offline** ([FINDINGS.md](FINDINGS.md) SLICE-F16): `grant_quest_reward` pays `reward_experience` through the kill's own `0x00EE [0, delta]`, credits morale, persists under `--persist`; gold is loudly NOT granted; a `quests_completed` set stops the re-offer. Labelled ours. **PROVEN BY THE OWNER'S HAND, same day** (`+100 experience` in the log) -- and the run found three stock-feel defects, fixed: `INTERACT_RANGE` 250 -> 144 (WIKI touch range), a ROUTED interact-walk through the router (`interact_route`, `--no-interact-route`), and a blank line before the reward |
| **SLICE-B6** | **The corridor.** A `gen_corridor` profile in `mapgen.py`, an `[area.*]` row, and a live run to close SLICE-U4. `_gate_dims` at `terrain.py:875` permits a non-square footprint; nothing has tried one on a client | **DONE 2026-09-12, PROVEN ON A CLIENT** ([FINDINGS.md](FINDINGS.md) SLICE-F13): `[area.corridor]` 32×128, map 168 `explorable = true`, file id 0x5F0B3, in the slice archive. The client compiled it 4096/4096 and meshed EXACTLY the floor (2 trapezoids, x 768..2208 of a 768..2304 floor) -- the slope banks are walls. `deploy` threads `dims = [x, y]`; `test_deploy` §14. **POPULATED AND SERVED 2026-09-12** (SLICE-F14): five spawn rows (2 × Bandit Raider + Academy Monk, tracked templates now, plus a boss raider with `glow = 5` -- int property 29 wired in `spawn_population`), `SERVE VERDICT: PASS` -- the server loaded the rectangle's 2 trapezoids and placed 5 of 5. Open: the aura's render (F2's bit) and the bars (B3) |
| **SLICE-B7** | **Hero follow and hero casting.** The long pole. Split into three, and **two are DONE (2026-09-12)**: **B7a** `allies_of` learns the party — the hardcoded `return set()` for the player is gone, and the asymmetry it had to learn is that the player is not a row in `agents` at all. **B7b** the party body FOLLOWS — the hostile follow with two numbers made arguments (an infinite leash, a 200 u formation stop), not a second follow; **proven on a real client**, 7 follows against 0 under `--no-hero-follow` ([FINDINGS.md](FINDINGS.md) SLICE-F9). **B7c DONE** — the monk hero HEALS the player in a fight, proven on a client (19 casts, cure + heal 55 and 58, against 0 without a bar; [FINDINGS.md](FINDINGS.md) SLICE-F10). It was far smaller than costed: `resolve_heal` was already recipient-parameterised and all six `PLAYER_AGENT_ID` sites are on the DAMAGE path, inert for a heal. **What a hero still cannot do: damage, enchant, swing, or be commanded** | **DONE** |
| **SLICE-B8** | **The transfer, sent by us.** After SLICE-U3. Send `0x0028 → 0x01A5 → 0x0099`, close gracefully per `close_after_transfer`, accept the re-entry, carry state across it. Quest state already survives a reconnect by accident of design — `QUEST_PROGRESS` at `authsrv.py:936` is a module-level singleton and `bind_progress` at `authsrv.py:940` re-points each new connection at it — which is the one piece of zoning that works today | **DONE 2026-09-12, PROVEN ON A CLIENT** ([FINDINGS.md](FINDINGS.md) SLICE-F17): `[portal.*]` rows, `portal_tick` → `send_transfer` (`0x0028 → 0x01A5 → 0x0099` to the gamesrv's SECOND alias, `--transfer-alt`), the tape's `graceful_close`, and a re-entry that stands `--map` down. Harness `20260912T143555`: `[c2]` came back with c1's ids asking for 146 and loaded it. **Assembled 2026-09-12** (SLICE-F18): portal 148 → 168 on the slice archive, `--area errand,corridor` serving two maps on one process with each row on its own map, every portal destination pre-warmed at startup (found by the run: the corridor loaded with NO NAVMESH first). Open: the quest carrier measured across a hop, and the owner's hand-driven pass |
| **SLICE-B9** | **One archive.** See §5 | **DONE 2026-09-12, PROVEN ON A CLIENT** (harness `20260912T105759`: the created map compiled 4096/4096 AND the authored name rendered, one run, one archive) ([FINDINGS.md](FINDINGS.md) SLICE-F12). `toolkit/mapdata/compose.py` + `content/compose.toml`: a manifest row names a pristine snapshot, the areas and the strings; the tool drives `textwrite` and `deploy --install` into ONE archive at `vault/run/slice/` and reads it back through the client's own resolvers -- 6 of 6. The record a string goes in is DERIVED from its consumer's `enc_name`, never typed. `frontier` stands in for the corridor until B6. A new run directory is an uncaged binary path -- the recipe `--verify` prints names the elevated cage step first, because the first launch was refused there |

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
| **SLICE-U4** | Whether the client accepts an elongated map footprint | ~~One live run under SLICE-B6~~ **CLOSED 2026-09-12** (SLICE-F13): it does, with our axes, and meshes the floor only | It does; `_gate_dims` forbids nothing about the aspect ratio and the square case is closed |
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
**DONE 2026-09-12 (SLICE-B9): the assembly is `content/compose.toml` + `compose.py --build`, and
`vault/run/slice/` is the first archive holding an authored string and a created chain together.**

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

## 7. After the ladder — the owner's first full run, 2026-09-12

The six steps of §0 ran end to end by the owner's hand (SLICE-F18): quest from Fisk, the
west portal into the corridor, the fight, the boss, the portal back, the turn-in. **Two
things measured on that run** that no scripted run could: the quest carrier survives two
transfers, and the boss aura is red (SLICE-F2's bit, closed). **Two things reported
against stock** (SLICE-F19): the attack skill, fixed in two halves (C1 the reach at the
strike, C2 the approach — SLICE-F20 measured retail's contract for the second), and the
kiting, which is retail's own rule with one open question (C3):

| Item | What | Status |
|---|---|---|
| **SLICE-C1** | **An attack skill strikes only in reach.** The Power Attack "glitch": press at range, keep running, the strike lands anyway — because retail's client holds the body through the swing and ours does not. `strike_out_of_reach` releases an out-of-reach strike as the measured cancel; `test_castcycle` §2d | **DONE 2026-09-12**, unobserved on a client |
| **SLICE-C2** | **An attack skill from out of range APPROACHES**, as `begin_attack` already does for the ordinary swing. Retail's contract measured on 11 free out-of-reach attack-skill presses (SLICE-F20): E4 + the `0x002A` follow in the press batch, nothing paid; the debit, the property-50 animation and `[8→1]` at ARRIVAL; the strike a windup later. Ours: an approaching entry is a queued cast whose begin instant is arrival (`approaching` in `handle_skill_press`, `attack_skill_arrives`, cast_tick's approach arm); movement or the target's death on the way releases it unpaid with the never-began marker (property 45, 4 of 4 — the owner's second run caught the 59 playing a stop over a chase cut short by W; begun attack skills stop with 49, spells with 59). `test_castcycle` §2e, `test_castcancel` §3. Third run: the body slid through the windup because a keyboard report mid-windup was answered (hold released, lead granted); retail defers it to the strike (2 of 2) — `attack_skill_roots` + a guard arm ahead of both movement arms, `test_castcancel` §3b, `--no-attack-skill-root`. Fourth run: the press while running still slid (the cast-stop halt was scoped non-attack; retail halts an in-reach attack-skill press on a running body, 2 of 2 — scoping removed) and a key held through the windup never moved after the hit (retail's attack E3 releases the hold exactly when a report was withheld, 3 of 3 / 0 of 3 — shipped). Fifth run: the halt convicted; the release alone drew a `0x0047` stop report — retail's strike batch ANSWERS the withheld report itself, so the recv loop now wakes at the strike and replays it through its own arm (`withheld_wake`, `withheld_replay_take`) | **DONE 2026-09-12, every piece OBSERVED on the owner's runs** -- walk-in, W-cancel, the 45 release, the root, the halt, and the replay (sixth run: "body walks after the hit now") |
| **SLICE-C3** | **Does retail's melee hit land on a target that left during the windup?** YES, and no capture was needed: the corpus holds 7 of 7 hostile swings at a running player landing (81–288 u displaced at the last report inside the windup), 33 of 34 player swings and 11 of 11 attack-skill strikes on a moving target (SLICE-F21, `latehitjoin.py`). Reach is judged at the start, never at the landing. Ours dropped the armed swing at three sites; all three land now (`LATE_HIT`, `--no-late-hit` reverts), SLICE-C1's gate retired to the revert arm | **DONE 2026-09-12**, unobserved on a client |
| **SLICE-C4** | **The halt owes a swing.** After F21 kiting was still free: 105 halts, 4 swings on the owner's run — the halt waits for the clock, the runner drifts past the 92 u start reach, the swing tick re-tests the live distance and re-follows a 20 u leg instead. Retail's swing follows its halt within 0.38 s on a lagging copy (5 of 5) and its hostiles open swings on a runner (3 of 45 starts, all landing). A halt whose arrival found the player in reach now owes one swing, opened within 0.5 s with no re-test; the follow tick holds meanwhile (SLICE-F22, `SWING_OWED_AT_HALT`, `--no-owed-swing`). `test_agentlife` §11b | **DONE 2026-09-12**, OBSERVED on the owner's run ("enemy swings when it catches me now") |
| **SLICE-C5** | **Two bugs off the C4 run** (SLICE-F23): the degeneration clock froze across quiet ticks, so a Bleeding applied minutes after the last one charged the whole gap on its first tick (the "instant kill"); and a corpse walked on the keyboard lead chain's re-grants. The clock is stamped every tick; `kill_player` drops every re-issuable order, the grant ticks and movement arms are gated on `player_dead`. `test_effects` §4f/§6a | **DONE 2026-09-12**, unobserved on a client |

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
