# Tape runs — what a recording of ArenaNet's server does to our client

R1.5's instrument is `toolkit/authsrv/tape.py` (loader) plus `play_tape` in
`authsrv.py` (player). What a tape *is*, and the three things it is not, are in
`tape.py`'s docstring; the feasibility argument that preceded the first run is
[../divergence/FINDINGS.md](../divergence/FINDINGS.md) §4. **This file is the log of
what actual runs observed**, because the tape is now a standing instrument rather than
a one-off experiment and its results will accumulate.

Claim labels are the vocabulary in
[../character/FINDINGS.md](../character/FINDINGS.md): OBSERVED, UPSTREAM,
RECONSTRUCTION, CORROBORATED, CONTESTED, UNVERIFIED, NOT FOUND.

---

## 1. The runs

Both from `vault/captures/live/20260807T143055`, the 2026-08-07 secondary-account
session. Both played into a caged loopback client with the auth channel synthesised by
our own server and the game channel replaced entirely by the recording.

| # | date | connection | map | events | outcome |
|---|---|---|---|---|---|
| 1 | 2026-08-10 | `:60935` | 148 Ascalon City | 1,209 / 1,209 | clean. Ended at the map transition: the client dialled `54.198.7.73:6112` from the recorded `GAME_SERVER_INFO` and the cage refused it (`Code=005`). |
| 2 | 2026-08-10 | `:64103` | 146 Lakeside County | 1,074 / 1,074 | clean, ran to completion, **combat rendered**. Operator kept the client after the tape ended and probed it. |

Run 1's findings — the client does not validate identity, and the earlier
`AgAgent.cpp(978)` assert was our own world tick talking over the recording — are in
`PLAN.md` §3.4. Everything below is run 2.

### 1.1 Which tape, and why it was nearly the wrong one

The capture holds four game connections. Naming them needs the `map_id` in each
connection's own c2s `VERSION` body (`<5I>` at offset 4: build, unk1, world_id, map_id,
player_id), resolved through the client's `AreaInfo` table:

| connection | map | first seen | events | combat |
|---|---|---|---|---|
| `:63158` | 0 (character select) | 7.5 s | 14 | — |
| `:60935` | **148** Ascalon City | 17.0 s | 1,209 | — |
| `:62994` | **146** Lakeside County | 65.9 s | 780 | attack-speed only |
| `:64102` | **164** Ashford Abbey | 213.8 s | 118 | — |
| `:64103` | **146** Lakeside County | 228.2 s | 1,074 | **yes** |

There are *two* Lakeside tapes. The chronological successor to Ascalon is `:62994`, and
it is the one that was nearly played; the combat is in the operator's **second** visit,
`:64103` — 4 × `SKILL_ACTIVATED` and roughly ten times the target-property traffic
(22 vs 3 `0x00A0`, 17 vs 2 `0x00A3`). **Pick a tape by decoding it, never by position in
the session.**

### 1.2 Pre-flight that matters

All four tapes name the **same** `map_file_id 113021` in their `0x0195`
`INSTANCE_LOAD_SPAWN_POINT`, differing only in spawn coordinates. The Gw.dat drift fix
that run 1 needed (`RUNBOOK.md`, "The two run directories drift apart") therefore covers
every tape in this capture — both archives now resolve 113021 to MFT row 177262.

That three different pre-Searing maps share one `map_file_id` is OBSERVED and
**UNVERIFIED as to why**. Do not build on it; it may mean the field is a region rather
than a map, or that pre-Searing Ascalon is one terrain file. It has not been checked.

---

## 2. What run 2 establishes

### T1 — A recording drives combat. OBSERVED.

1,074 of 1,074 events, 53,544 B, 186.2 s, **0 non-tape sends** — measured from the
gamesrv's own capture by counting `sent` records whose label is not `tape[…]`. Since our
server contributed nothing, everything the operator saw came from the recording.

The tape frames to 3,604 `GAME_SMSG` messages across **105 distinct opcodes, of which
our server can name 42**. It included 188 `WORLD_CREATE_AGENT`, 163 `WORLD_REMOVE_AGENT`,
351 `AGENT_MOVE_TO_POINT`, 1,511 `WORLD_SIMULATION_TICK` and 4 `SKILL_ACTIVATED`.

Operator's account: *"i walk over to a Wolf enemy, attack it from range, then cast my
Vampiric Gaze (skill 1) and Deathly Swarm (skill 2) on it and fight it until victory."*
The tape agrees, message for message:

| what was seen | in the tape |
|---|---|
| walking to the Wolf | agent 31 (never removed) moves, 1.7 → 39.7 s |
| the Wolf | agent 40, created 0.7 s, removed 68.5 s |
| Vampiric Gaze | `0x00E3 SKILL_ACTIVATED [227, 31, 153, 0]` at 10.5 s and 20.3 s |
| Deathly Swarm | `0x00E3 SKILL_ACTIVATED [227, 31, 105, 0]` at 13.2 s and 23.0 s |

**This is the first time this project has rendered combat.** No semantics were required
to do it: 63 of the 105 opcodes involved have no name anywhere in the repo.

### T2 — The client rendered a map it never asked for. OBSERVED.

The client's own game `VERSION` carried **`map_id=148`** (Ascalon City — the map its
character record held). The tape's `0x0199 INSTANCE_LOAD_INFO` declared **146**
(Lakeside County). The client loaded and rendered Lakeside County.

`--map 146` was passed but is **not** the explanation: `--game-args` reaches the gamesrv
only, and although `MAP_OVERRIDE` does rewrite `state["map_id"]` there, tape mode never
reads it — the whole preamble that would use it is skipped. The client genuinely asked
for 148 and was genuinely told 146.

This is the same family of result as run 1's identity finding: **the client does not
cross-check what it requested against what it is told.** The map it draws follows the
tape's `0x0195 map_file_id`, not its own `map_id`.

### T3 — Agent-id reuse, from ArenaNet's own server, at scale. CORROBORATES D1.

`../divergence/FINDINGS.md` D1 asked whether a removed agent id is poisoned. It was
closed on 2026-08-09 with a hand-built probe against the client. This tape answers it
again from the other direction — ArenaNet's own traffic:

```
agent 281: create@1.7s REMOVE@6.7s create@12.8s REMOVE@18.7s … create@181.5s REMOVE@186.0s
           (19 create/remove cycles in 186 seconds)
agent 284: 19 cycles.   agents 273/274/275/276: 5–6 cycles each.
19 of the 45 agent ids the tape uses are created more than once.
```

The client accepted every one of them and never complained. Id reuse after
`WORLD_REMOVE_AGENT` is not merely permitted; on ArenaNet's server it is **routine and
high-frequency**. This is corroboration by an independent witness, not our probe agreeing
with itself.

### T4 — `GAME_CMSG 0x0046` field 1 is a skill id. OBSERVED, ground-truthed.

After the tape, the operator pressed skills. The client sent:

```
149.7s  0x0046 USE_SKILL [32838, 153, 0, 281, 0]
155.7s  0x0046 USE_SKILL [32838, 153, 0, 273, 0]
157.3s  0x0046 USE_SKILL [32838, 153, 0, 273, 0]
157.5s  0x0046 USE_SKILL [32838, 153, 0, 273, 0]
158.0s  0x0046 USE_SKILL [32838, 105, 0, 273, 0]
```

The operator named the two skills independently, *before* the payloads were decoded. The
client's own tables then confirm them:

| operator said | field 1 | client skill table | client string table |
|---|---|---|---|
| Vampiric Gaze (slot 1) | **153** | prof 4 / attr 4, 10 energy, 1.0 s cast, 8 s recharge | name id 25126 → **'Vampiric Gaze'** |
| Deathly Swarm (slot 2) | **105** | prof 4 / attr 5, 10 energy, 2.0 s cast, 6 s recharge | name id 25030 → **'Deathly Swarm'** |

So **field 1 is the skill id, not the skillbar slot** — the values are not 0 and 1 — and
field 3 is the target agent id. This is a labelled human action matched against two
independent client-derived tables, which is as strong as evidence in this repo gets.
Method note: the corroborating tables come from `skilltable.py` and `textrec.py` reading
the client, and the operator's label came first, so this is not our decoder forcing the
answer.

### T5 — Two more c2s opcodes acquire candidate meanings. RECONSTRUCTION.

Neither is confirmed; both are consistent across every occurrence in the run.

* **`0x00C1 [req, agent_id, 0]`** — target select, `0` clears. 24 sends, alternating
  between an agent id and 0, and it **precedes every `USE_SKILL` with the matching id**
  (`[281]`@148.2 s → skill→281@149.7 s; `[273]`@155.5 s → skill→273@155.7 s).
* **`0x0026 [req, agent_id, 0]`** — attack or interact. 6 sends, each immediately after a
  `0x00C1` naming the same agent (`[274]`@152.5 s → `0x0026 [274]`@152.6 s).

Also CORROBORATED, since the operator labelled the action: `0x003D TURN_TO_DIRECTION`
(29 sends, carrying position + facing — what held-key movement produces) and
`0x003E MOVE_TO_COORD` (8 sends, position only — what a click produces). Those names were
UPSTREAM; a labelled walk now supports them.

And **`0x0009 [req, 16, 0]` is a client keepalive**: 37 sends at 5.0 s intervals from
4.6 s to 184.7 s, dead regular, independent of anything on screen. OBSERVED.

### T6 — A tape answers nothing, and the client tolerates it. OBSERVED.

Tape mode never replies to c2s — the dispatch `continue`s. The operator's report is the
behavioural consequence: *"gateways and attacking and casting blocked."* The client sent
121 well-formed messages across 15 opcodes, received **no** answer to any of them, and
neither crashed nor disconnected; it was still sending `0x00C1` and `0x000C` after the
tape completed.

This is a property of the instrument, not a defect, but it is the ceiling on what a tape
can test and it should be stated whenever a tape run is reported: **a tape shows a load
and a populated, animated world; it cannot show control.**

### T7 — A tape's visible length and its real length are not the same. OBSERVED.

The operator held all input until they believed the tape had ended, judging by their
character standing still — and then reported input starting "after the tape ended", while
the measurement shows their first message at 86.2 s of a 186.2 s tape. Both accounts are
correct:

```
the recorded PLAYER agent (31) moves:  1.7s → 39.7s, then never again
all other agents keep moving:          throughout, to 186.2s
operator's first input:                86.2s
tape actually completes:               186.2s
```

The recorded operator walked, fought, and then **stood still for the last 146 seconds**
while the world carried on around them. From the seat, that is indistinguishable from the
tape ending. Nothing is wrong with the tape.

**Consequence for the procedure:** `play_tape` already prints `tape N/1074` progress and
a `tape complete` line to the gamesrv terminal. A tape run's operator should be told to
watch *that*, not the avatar, before treating the client as free. Recorded in
`RUNBOOK.md`.

---

## 3. What run 2 did not settle

* **Control.** Out of scope by construction (T6). Unchanged from `tape.py`'s docstring.
* **Session-embedded absolute time** — `../divergence/FINDINGS.md` §4.2 item 5. Still
  UNVERIFIED. Run 1's apparent evidence was retracted as our own contamination; run 2
  produced no assert at all, which is consistent with the field not existing *and* with
  it existing and being ignored. Not tested.
* **Why three maps share `map_file_id 113021`** (§1.2).
* **Whether `0x0026` is attack specifically** rather than a general interact — the
  operator tested attacking and gateways in the same window, and a gateway is also an
  interact. One labelled run separating the two would settle it.

---

## 4. Next, in order of value

1. **Chain the tapes across a map transition.** Run 1 ended when the client dialled
   ArenaNet for the next instance. Catch that dial and hand it `:62994`'s tape instead;
   four instance tapes become one continuous session. This is the largest single increase
   in what the instrument covers.
2. **Diff our server against a tape at matching points in the load.** The tape is the
   first oracle this project has that it did not write itself, which turns D2–D11 from a
   list into a failing test.
3. **A labelled input run.** Play any tape, then have the operator perform *named*
   actions one at a time with pauses between. Run 2 got T4 and T5 as a by-product of an
   unplanned five minutes; a deliberate 10-minute pass would name most of the c2s
   catalog, and it needs no new capture and no live session.
