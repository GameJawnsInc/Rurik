# SLICE — findings

Arc plan and gates: [PLAN.md](PLAN.md). Status authority stays
[the project PLAN](../../PLAN.md) §3.

**Identifiers.** `SLICE-F<n>` = a finding. The arc's other series (`SLICE-G<n>` gates,
`SLICE-B<n>` build items, `SLICE-U<n>` unknowns) are declared in [PLAN.md](PLAN.md).
Convention: [studies/idents/CONVENTION.md](../idents/CONVENTION.md).

**Everything below was read out of the pinned pristine client, build 38797**
(`vault/client/2026-07-29_221c13772c7a/Gw.exe`, verified PRISTINE) by tools in this
repo: `toolkit/clientscan/consttable.py`, `toolkit/clientscan/codescan.py`,
`toolkit/clientscan/genericvalue.py` and `toolkit/clientscan/asserts.py`. Addresses are
VAs on that build and are build-coupled; re-derive them rather than carrying them
forward.

---

## SLICE-F1 — **SLICE-U1 is CLOSED at the desk: the boss glow's whole path is decoded, and it needed no run**

OBSERVED, 2026-09-11. The plan registered SLICE-U1 as "whether the boss aura is
reachable from the server", predicted that property 29 would be a plain int property on
the agent selecting a row of the client's own `s_glow`, and queued a decode pass. The
prediction holds, and the chain closes end to end in four hops:

```
GAME_SMSG int property 29 [agent, value]
  -> case body            0x00812CBC   push ebx / push edi / call 0x7DFD70
  -> setter               0x007DFD70   obj = 0x00802160(arg0); if (!obj) return;
                                       call 0x007FC160(this=obj, arg1)
  -> forwarder            0x007FC160   this->[+0x15C] |= 0xC00
                                       row = 0x008EDE70(index)
                                       r = row[+4]/255.0
                                       g = row[+5]/255.0
                                       b = row[+6]/255.0
  -> s_glow accessor      0x008EDE70   assert index < 11      ConstGlow.cpp(42)
```

Four things make this stronger than a plausible chain of names:

- **The case body is two pushes and a call.** `0x00812CBC` does nothing but forward the
  property's two operands. There is no interpretation between the wire and the setter.
- **The bound is ArenaNet's own number, not our division.** The accessor opens
  `cmp esi, 0xb` at `0x008EDE77` and asserts `index < arrsize(s_glow)` — so 11 is the
  client's arrsize, and `consttable.py`'s closure to 11 × 8 has a second, independent
  witness. Same shape for `s_aura` in SLICE-F4.
- **The divisor is 255.0.** `0x009495A8` reads as the double `255.0`, so the three bytes
  at `+4/+5/+6` are 0..255 colour components normalised to floats. That is what a colour
  is, and it is why the row cannot be anything else.
- **The middle frame is a forwarder.** `0x007DFD70` passes its `arg1` through untouched,
  which is the shape that says the index is the *server's* value and not something the
  client derives. (`feedback-a-forwarder-names-the-messenger`: the answer was one frame
  out, twice, and both were followed.)

**What this buys the slice.** A boss glow is one int property on the boss's agent —
`[agent_id, glow_index]`, `glow_index` in 0..10. No new opcode, no composite work, no
archive edit. That is a far cheaper boss than the plan costed.

**What it does NOT establish**, and none of these blocks SLICE-B-anything:

- **Whether ArenaNet ever sends property 29.** It is 0 of 22,524 in our corpus. This is a
  fact about what the CLIENT will do when told, which is the right question for a server
  we are writing and is not a claim about retail's own traffic.
- **How a glow is turned OFF.** Index 0 is a populated row, not an "off" sentinel, and
  the forwarder only ever ORs `0xC00` into `+0x15C` — it never clears it. There may be no
  un-set on this path.
- **The channel order.** See SLICE-F2.

## SLICE-F2 — `s_glow` is eleven (id, colour) rows, and the channel order is the one bit left

OBSERVED. `s_glow` at file `0x7A2B58..0x7A2BB0`, 11 × 8 B, index column at `+0x00`. Byte
`+7` is zero in all eleven rows. Read as the client reads it — `+4`, `+5`, `+6`, each
÷ 255.0:

| id | +4 | +5 | +6 | if (R,G,B) | if (B,G,R) |
|---|---|---|---|---|---|
| 0 | 148 | 94 | 0 | `#945E00` | `#005E94` |
| 1 | 0 | 148 | 64 | `#009440` | `#409400` |
| 2 | 0 | 0 | 192 | `#0000C0` | `#C00000` |
| 3 | 0 | 128 | 0 | `#008000` | `#008000` |
| 4 | 128 | 0 | 128 | `#800080` | `#800080` |
| 5 | 192 | 0 | 0 | `#C00000` | `#0000C0` |
| 6 | 167 | 135 | 233 | `#A787E9` | `#E987A7` |
| 7 | 0 | 200 | 200 | `#00C8C8` | `#C8C800` |
| 8 | 181 | 142 | 132 | `#B58E84` | `#848EB5` |
| 9 | 247 | 247 | 140 | `#F7F78C` | `#8CF7F7` |
| 10 | 0 | 96 | 96 | `#006060` | `#606000` |

**The remaining bit is settled by one probe, and it is a good one** — a single value with
an unmistakable readout, which is what `feedback-make-the-signal-unmistakable` asks for.
Send property 29 with **index 5**. Ids 3 and 4 are palindromic and prove nothing; id 5 is
`#C00000` under one reading and `#0000C0` under the other. **Prediction, registered
before the run: the aura renders RED, i.e. `+4` is the red channel.** A blue aura refutes
it and settles the order the other way; anything else says the three floats are not going
where this reading assumes.

## SLICE-F3 — the "s_glow is profession-indexed" reading is NOT supported, and the count that suggested it is a coincidence

The row count is 11, and `CHAR_PROFESSIONS = 11` at `agents.py:255` is "the CLIENT's own
compiled bound: ids 0..10". That coincidence is what made a profession-coloured glow the
obvious first reading, and the published lore agrees that GW1 boss auras are
profession-coloured. **The colours do not support it under either channel order.** Taking
0 = none and 1..10 as the canonical profession order, id 1 (Warrior) reads green in both
readings, and neither id 2 nor id 3 lands on the hue its profession uses in the game's own
UI.

So: **the mapping from a glow id to a meaning is UNKNOWN**, and this finding exists to
stop the next session re-deriving the appealing wrong answer from the same coincidence.
The honest options are that the index is something other than a profession, that the
profession order is not the one assumed, or that the table is not what its neighbours
suggest. Settling it needs the colours seen on screen, which is the same run SLICE-F2
registers.

## SLICE-F4 — `s_aura` is 44 rows of (id, **client file id**, tint/scale), and the file-id reading is MEASURED with controls

OBSERVED. `s_aura` at file `0x7AAEB8..0x7AB0C8`, 44 × 12 B, index column at `+0x00`.
The accessor at `0x008EDF10` opens `cmp esi, 0x2c` — 44 is ArenaNet's own arrsize, and
`lea eax, [esi+esi*2]` / `lea eax, [eax*4 + 0xBABEB8]` gives stride 12 and base
`0xBABEB8` from the client's own arithmetic rather than from our closure.

**Column 3 is `0x64000000` in all 44 rows** — bit-identical to the `scale` word
`content/npcs.toml` carries on both its NPC templates, where it is commented "hue 0,
saturation 0, lightness 0, scale 100%". Two unrelated parts of this project arriving at
the same constant is the kind of cross-check `CLAUDE.md` asks for.

**Column 2 binds as a file id the CLIENT can address — 44 of 44, against two controls
that do not.** Reproduce with `python studies/slice/review/aurabind.py`, which reads
`binds_plainly` at `archive.py:600` against `vault/run/2026-08-20_21511009c460/Gw.dat`:

| set | binds |
|---|---|
| `s_aura` column 2 | **44 of 44** |
| control: the same ids + 1 | 26 of 44 |
| control: 44 random draws from the same range | 22 of 44 |

The controls matter and were the point of the design: the archive is dense in that band,
so ~half of *anything* binds, and 44/44 against a ~55% background is the discrimination.
(`feedback-a-negative-needs-a-positive-control`, applied in the positive direction: a
check that could not have failed would have proved nothing.)

## SLICE-F5 — properties 6 and 7 are apply/remove of ONE function, and that CORROBORATES an upstream name from structure

OBSERVED. The two case bodies are byte-identical but for one immediate:

```
property 6   0x00812AF5   push 1 / push ebx / push edi / call 0x7DFAB0
property 7   0x00812B08   push 0 / push ebx / push edi / call 0x7DFAB0
```

OpenTyria's `GmAgentProperties.h` names them `ApplyAura` and `RemoveAura` — the
`OPENTYRIA` table at `genericvalue.py:183`, UPSTREAM; GWCA independently names them `add_effect` and
`remove_effect`. **The structure agrees with the names without having been told them** —
one function, one boolean, two ids — so this is CORROBORATED rather than UPSTREAM, which
is a stronger label than the table alone could earn. Note what it is not: the *name* is
still borrowed. What we measured is a three-argument call taking an on/off flag.

**Consequence for the slice:** an aura HAS an off switch where the glow (SLICE-F1) appears
not to. If a boss needs to stop glowing — on death, say — property 7 is the lead and
property 29 is not.

## SLICE-F7 — **SLICE-U2: the parade RAN and the client named fifteen creatures for us**

OBSERVED, 2026-09-11, harness `20260911T231549`, build 38797, loopback, agent-driven,
RUN VERDICT PASS. Full run sheet and scoring: [RUN-PARADE.md](RUN-PARADE.md) §4a.

**The control passed, and it is why the rest of the run means anything.** One body was
spawned deliberately without its `0x0057`; it drew the solid white untextured box. The
gamesrv log shows exactly **eleven** `MONSTER_COMPOSITE` sends against fifteen creates —
the eleven rows that carry a body — so the arm was armed on the wire before anything was
judged by eye. Fifteen of fifteen bodies were legible against a floor of twelve of
fourteen.

**Fifteen nameplates, drawn by the client from its own string table:** Wolf, Bandit
Raider, Bandit Firestarter, Plague Worm, River Skale, River Skale Tad, Lord Darrin,
Mesmer Trainer, Ascalonian Townsfolk, Academy Monk, Necromancer, Outfitter, Lieutenant
Fisk, Harner, Harner.

**Ten of the fifteen join to a template on evidence; five do not, and the doc says which.**
The joins rest on allegiance (`band` is carried by exactly two rows), a level pairing
(shell `82023` at levels 1 and 0 → "River Skale" and its "Tad"), uniqueness of a
profession (one Mesmer, one Necromancer), and construction (the two Harners are the
control and its pair). The five unjoined are five human templates against five human
names, and the finisher is a second parade of just those five, which cannot be ambiguous.

**Two results that were not among the questions.**

1. **`content/npcs.toml`'s `lakeside_worm` is named, and the promotion is decisive rather
   than inferred.** That row's note said "Do not promote it to a real name until a client
   renders it." One has: the nameplate read **Plague Worm**. The reason this does not
   depend on picking the right body out of a fifteen-body frame is that a nameplate is the
   client resolving `enc_name`, and the spawned row carries that row's four words
   byte-identically — same words, same string, same plate. `studies/presearing`'s manifest
   independently lists "Plague Worm" among Pre-Searing's quest-only creature types, from a
   wiki pass with no connection to this definition slot; that corroborates and was not
   used to reach it.
2. **The roster's own expectation was wrong, and the run corrected it.** RUN-PARADE
   assumed the warrior/monk pair would come out of Tier A. **Tier A contains no monk** —
   the two bandits are a Warrior and an Elementalist. The pair the slice should use is
   **Bandit Raider** (`def_1421`) plus the **Academy Monk** body spawned HOSTILE, which
   costs nothing because `npcdefs.py`'s own header already states that hostility is a
   property of a spawn and not of a type.

**One registered suspicion refuted.** `def_1420` closes to five files, by far the smallest
in the set, and question 4 asked whether that would show. It did not — it rendered a
normal humanoid. A small closure means a shell reusing its neighbours' files, not a broken
one.

**FINISHED 2026-09-11 by ten ONE-BODY runs, and the finisher corrected the finding above.**
[RUN-PARADE.md](RUN-PARADE.md) §4b carries the table. Two things came out of it:

- **`def_1470` is the Outfitter, not the Academy Monk.** This finding's first pass inferred
  it from the profession byte (`def_1470` is profession 3). That was wrong, and
  **name-matches-profession is refuted as a join key** — a second, independent witness to
  what `studies/monsterai` measured from the other side. The Academy Monk is `def_1486`,
  so **the slice's monk body changed**. The warrior, `def_1421` "Bandit Raider", was
  re-checked alone in an empty world and holds.
- **The method that fixed it is the finding worth keeping.** §4a's own plan said five
  bodies would be unambiguous "because five bodies leave five names"; five bodies in one
  frame is exactly the per-body join that failed the first time, and five names against
  five bodies constrains the set, not the pairing. **One body per world has exactly one
  nameplate** and needs no projection, compass or elimination at all — at eighty seconds a
  run, certainty was cheaper than the argument for doing without it.

Twelve of fifteen are now OBSERVED directly (ten runs plus the two Harners, which are the
control and its pair by construction). The three left rest on a structural argument rather
than a profession one: `82023` is the only shell present twice and "River Skale" / "River
Skale Tad" are the only two names sharing a stem, which leaves Wolf.

## SLICE-F8 — **SLICE-U3: `0x00B1` is the client's travel REQUEST, and 34 of 41 transfers do not have one**

OBSERVED, 2026-09-11, desk pass over the whole live corpus, no client launched.
Reproduce with `python studies/slice/review/transferc2s.py`. 20 captures scanned
(one skipped — no `wire.jsonl`), **41 game-channel `0x01A5` transfers**.

**The signal, and the controls that make it one.** Every c2s opcode was scored as
`in-window / total` precisely because the client sends `0x003D MOVE_SET_HEADING`
constantly, so "it appeared just before the transfer" is true of almost everything and
means nothing:

| opcode | pre | post | total | pre/total | was LAST before |
|---|---|---|---|---|---|
| `0x003D` | 399 | 0 | 3079 | 13.0% | 24 |
| `0x0009` | 79 | 0 | 1390 | 5.7% | 4 |
| `0x0092` | 61 | 0 | 150 | 40.7% | 0 |
| `0x00C1` | 60 | 0 | 844 | 7.1% | 3 |
| **`0x00B1`** | **7** | **0** | **7** | **100.0%** | **7** |

`0x00B1` occurs **seven times in the entire corpus and all seven are inside a
pre-transfer window**, always as the last thing the client says, at **47–85 ms** before
the handoff. Nothing else comes close: the two other 100% rows are `0x005C` (total 2) and
`0x0041` (total 1), and neither was ever last.

**And then the decisive test, which is not a correlation at all.** `0x00B1`'s field[1] is
a word, and it **equals the destination map the following `0x01A5` names, 7 of 7**:

```
[32945, 281, 0, 0, 0, 1] -> map 281  (+84 ms)
[32945, 248, 0, 0, 0, 1] -> map 248  (+70, +63, +55, +56, +47 ms)
[32945, 242, 0, 0, 0, 1] -> map 242  (+85 ms)
```

(32945 is `0x80B1` — the opcode carrying the c2s bit.) The imported shape agrees:
`GAME_CMSG` 177 is `[msg_header, word, byte, word, byte, byte]`, 9 bytes, and the word is
where the map id sits. **Candidate name `MAP_TRAVEL_REQUEST`, confidence MEDIUM** — this
is wire evidence only, with no disassembly behind it, which is a weaker footing than the
`TARGET_SELECT` entry beside it in `schema/overrides.json`. Naming it there is a small
follow-up with its own discipline, not part of this finding.

**THE RESULT THAT ACTUALLY MOVES SLICE-B8, and it is the one nobody expected: 34 of the
41 transfers have no client request at all.** The seven with `0x00B1` all go to
outpost-type maps (248 ×5, 281, 242); the other thirty-four are the server handing the
client onward unprompted — 20 of them into explorables (280 ×16, 146 ×4). So **the
server initiates a transfer whenever it likes, and that is retail's majority case.** The
slice's zoning therefore does **not** depend on decoding this opcode: SLICE-B8 can send
`0x0028 → 0x01A5 → 0x0099` on its own trigger — a player entering a portal region — and be
doing exactly what ArenaNet's server does 83% of the time.

**A second observation, free from the same pass:** `0x0008` appears **41 times in the
post-transfer window and 0 times in any pre-window** (total 49). Every transfer is
followed by the client saying `0x0008` on the dying connection. Unnamed; recorded rather
than chased.

**A method note, because the first version of this pass was wrong in a quiet way.** It
read the destination by joining to the following `0x0099` and taking `values[0]` — which
is the OPCODE, since the codec puts it there. Every one of the 41 rows reported "map 153"
(= `0x0099`). **A constant answer across every row is the shape of a field error, not a
finding**, and it was caught by the answer being implausible rather than by any check.
The fixed read takes the destination off `0x01A5`'s own field[4] and needs no join.

## SLICE-F9 — **the hero follows, on a real client — and the first run measured nothing, which is the more useful half**

OBSERVED, 2026-09-12. Two arms, both registered before either ran.

**The first attempt was an ABORT, not a null, and the harness said PASS.**
`--hero-body-npc def_1486` killed instance bring-up with `KeyError: 'name'`; the hero
body was never created; the run reported **RUN VERDICT: PASS** and produced a full set of
screenshots of a world with no hero in it. Had the prediction been "the hero follows" with
no exposure floor, this run would have been written up as a refutation of the follow.

The cause is a defect class this repo has already paid for once and fixed **in one place
only**. A vault-emitted `def_NNNN` row deliberately carries no name — *"a name comes from a
rendered nameplate or it does not exist"* (`npcdefs.py`) — and `spawn_population` says so
at its own label line, which reads `npc.get("name") or str(row["npc"])` precisely because
indexing it bare "threw inside instance bring-up, where the harness still reported PASS and
the map readback stayed green". **The hero and henchman body sites still indexed it bare.**
Both are now `.get(...) or` the content key. The bug was reachable the moment anybody used
a parade-named template as a hero body, which is exactly what the slice wants to do.

**With that fixed, both arms landed as predicted.**

| arm | creates | `KeyError` | follows by agent 200 |
|---|---|---|---|
| treatment | 2 | 0 | **7**, each "halts at 200 u" |
| `--no-hero-follow` | 2 | 0 | **0** |

Same body created in both, so the arm isolates the follow and not the spawn. The seven
follows report 208 → 252 → 210 u out, which is the hero repeatedly falling behind and
catching up — **that is also the exposure floor being met**, since a player who never moved
produces no follows at all and would have made the null meaningless.

**And the body is the slice's own monk.** The run used `def_1486`, the Academy Monk the
parade picked, so the screenshot is the vertical slice's hero walking behind the player
with a green party arrow and an ally health bar over her.

What this does NOT show: the hero doing anything in a fight. It walks. SLICE-B7c is the
rest.

## SLICE-F10 — **SLICE-B7c: the monk hero heals the player in a fight, and the defect that mattered was invisible to the unit test**

OBSERVED, 2026-09-12, harness `20260912T092508` (treatment) and `20260912T092833` (arm).

**B7c was far smaller than the plan costed, for a reason worth writing down.** `land_skill`
names `PLAYER_AGENT_ID` at six sites, which is what made B7 look like an arc — but
`resolve_heal` was **already** caster- and recipient-parameterised, and `land_skill`
already lands a heal on `cast_target`. All six hardcodings are on the DAMAGE path, and for
a heal every one is inert: `skill_damage` is None, and a heal Spell opens no episode. So a
monk hero needed a tick, a bar and a target policy — not a rewrite.

**What was built.** `ally_cast_tick`, deliberately not a branch inside `enemy_attack_tick`:
that function's shape is the SWING's — melee-reach gate, weapon interval, swing open and
land — and a monk uses none of it. `ally_heal_target` holds the whole policy in one place
and is labelled OURS, because `studies/monsterai` established that ArenaNet's decision
logic is recoverable from nothing. `pick_skill` is reused rather than replaced; its
docstring's "a fixture, not a decision about AI" boundary is as true for an ally.

**THE DEFECT ONLY A RUN COULD FIND.** The first treatment run put **28 party casts on the
wire and resolved ZERO of them.** `enemy_attack_tick` runs before `ally_cast_tick`, and its
`not attacks_back` branch clears `cast_lands_at` **before** the allegiance gate — and a
party body has `attacks_back` False. So every tick armed a cast and the next tick wiped it.
The unit test drove `ally_cast_tick` alone and could not have seen it: *offline agreement
between two of our own components proves nothing*, in the most literal available form. The
regression check now drives both ticks in the world tick's own order, and was **verified to
go red with the fix reverted** (`after=None`).

**Both arms, with the floor met.**

| arm | creates | Bleeding on the player | party casts | heals by 200 |
|---|---|---|---|---|
| treatment | 3 | 12 | 19 | **cured + healed 55 and 58** |
| no `--hero-skills` | 3 | 10 | 0 | 0 |

The floor is the Bleeding count, and it earned its place twice. A run before this one
scored 0 on everything **including the floor** — the harness appends `--no-enemy` unless
its own `--enemy` is passed, so no hostile ever spawned. Registered as an ABORT rather than
read as a refutation of the heal.

**One constraint confirmed from the inside.** The landing check initially failed, correctly:
Restore Condition heals PER CONDITION REMOVED, so against a clean target it cures nothing
and heals nothing. That is SLICE-B3's registered trap arriving as a test failure, and it
means the slice still needs an **unconditional heal** wired before a monk hero looks like a
monk in ordinary play.

**What a hero still cannot do:** damage, enchant, swing, or be commanded. The first two
need `land_skill`'s four remaining sites parameterised; the commander UI's flags and
stances are decoded but wired to nothing.

## SLICE-F11 — **SLICE-B1: the quest giver is CONTENT now, and the parade's names became tracked rows**

OBSERVED, 2026-09-12, harness `20260912T094236`. The offer screen, on a real client, from
an authored spawn row: **"Lieutenant Fisk / Well met. My companion waits nearby with word
I need. Bring it to me. / Reward: 100 Experience / Accept / Decline"**, with the quest's
`!` marker over the giver at instance load.

**The recon's framing was right and its cost was wrong**, which the plan already flagged:
"no code spawns a quest giver in ordinary play" is true, and needed no server change to
fix. `_quest_lines` and `_objective_quests` bind by agent id, and `area_population` lets a
spawn row choose any id — so a row IS the giver.

**What was genuinely owed, and is now done.**

- **Two parade templates promoted into tracked `content/npcs.toml`** with the names the
  client drew: `lieutenant_fisk` (def 1458) and `ascalonian_townsfolk` (def 1490). Each was
  alone in an empty world when its nameplate was read, so the name belongs to that
  definition and nothing else. They are the first templates that HAD to be tracked, because
  a tracked spawn row naming a vault-only template fails on a bare machine — and
  `test_quests` §21 now loads the store with the overlay **switched off** to check exactly
  that, which the suite otherwise never exercises.
- **`quest_agent(row, which)`** — a quest may name its NPC by SPAWN KEY instead of a bare
  number. Both are supported and the key wins; the numbers survive so `probequest.py`'s
  hand-built world still binds, and the spawn rows were given 99 and 98 deliberately so the
  two agree. A key naming no spawn row **raises** rather than falling back, because that
  fallback would leave the quest working in the probe and dead in the world — invisible
  from either side alone.

**One open question, recorded rather than tuned away.** The first run placed the giver at
300 u, beyond `INTERACT_RANGE` (250 u). The server did the right thing — ordered a walk and
HELD the interact — and **the hold never released**: the walk order went out and the client
sent only heartbeats, so `state["pos"]` never came within range (harness
`20260912T093924`). The giver moved to 200 u for a content reason (a quest giver you cannot
talk to is bad content), and the held-interact path is left as a thing to look at, not as a
thing that was fixed.

## SLICE-F12 — **SLICE-B9: ONE archive, and the assembly is a manifest row**

**PRE-REGISTERED 2026-09-12 14:55, before the run.** `compose.py --name slice --build`
assembled `vault/run/slice/` from the pristine 38833 snapshot plus the canonical 38797
client, wrote record 200 ("A First Errand") through `textwrite` (a `datmove` relocation:
the pristine row held 56 B of compression-8 empty records in a 512 B reservation), and
created `frontier`'s chain through `deploy --install` at rows 177753/177754 under
0x5F0B0. Offline verify: 6 of 6, through the client's own resolvers.

**Question.** Does ONE archive carry a created map AND an authored string onto one
screen — the thing §5 says no run directory has ever done?

**Prediction.** One run, `--map 166 --area frontier --probe quest_name_authored`, on
the slice client with `RURIK_DAT` at its archive: (a) `compose.py --readback` reports
the head re-bloated — the client compiled our 64×64 frontier from the created chain,
terrain matching what we authored — and (b) the tracker frames read **"A First
Errand"** after the treatment arm, as harness `20260819T085654` did against
`reskin-roster`. Either half failing alone localises the seam: (a) red with (b) green
means the created chain did not survive the composition; (b) red with (a) green means
the text relocation did not.

**Exposure floor.** The harness reaches "body is in the map" and at least one hold
frame exists after the probe's treatment push. Short of that the run is an ABORT, not a
refutation of either half.

**RESULT — BOTH HALVES OBSERVED, one run, one archive.** Harness `20260912T105759`
(the owner caged the binary; map 166, `--area frontier`, `--probe quest_name_authored`,
`RURIK_DAT` at the slice archive), RUN VERDICT PASS, body in the map at t+24.4 s:

- **(a) the created chain compiled.** `Gw.log`: `Map file '0x05f0b0' failed to load.
  Attempting to re-bloat.` — the documented trigger, from a chain that did not exist in any
  archive before `--build`. `compose.py --readback`, 6 of 6: the client re-compiled the map
  (11,004 B path chunk, **98 trapezoids** built from our terrain), **the compiled height
  field equals the one we authored 4096/4096**, environment and sound payloads carried
  verbatim, 8 props present, the flood seed in exactly one trapezoid.
- **(b) the authored string rendered.** Frame `hold014`: the quest tracker reads
  **"A First Errand: Speak with the scout, then return."** in green beside the quest icon,
  standing on the plaza-generator cobbles of (a). `hold002`, before the treatment push,
  shows the tracker empty — the same before/after as `20260819T085654`, now on an archive
  that also holds a created map. The client's `0x8012` for 1463 was answered with the
  template `0x004C` mid-run, as before.

So §5's sentence — "that assembly has never been done" — is closed by measurement, and the
run also answered the question a copy cannot: the string relocation and the chain creation
**coexist** in one MFT the client then moved (the re-bloat rewrites the head), with nothing
lost on either side.

**THE FIRST ATTEMPT did not start; the cage refused it, correctly.** Launch
`20260912T1457` was refused at `cage.assert_launch_safe`: `vault/run/slice/Gw.exe` is a
NEW binary path and no firewall rule names it — the exact rule the isolate script's own
header says it exists for, since the day a second run directory went uncaged. The cage
needs an elevated shell, the UAC prompt was cancelled, and no client process started. Under
the exposure floor above this is an **ABORT** of the client half, not a null on either
prediction. Nothing about the archive changed: `--verify` still reads 6 of 6 after the
refused launch (the MFT never moved, because nothing opened it). Resume with, elevated:
`& toolkit\clientpatch\isolate_client.ps1 -Exe "C:\gd\Rurik\vault\run\slice\Gw.exe"`,
then the recipe `compose.py --name slice --verify` prints, then `--readback`.

**What the offline half settled, and is OBSERVED against the bytes:**

- **The assembly is a row, not an afternoon.** `content/compose.toml` names a pristine
  snapshot (`client/2026-08-13_64fae3b1369b/Gw.dat`), the areas and the strings; the tool
  copies the pinned build's client by BUILD and name (`drive_client.select_run_exe`, never
  by mtime) and drives the two existing writers. It writes nothing itself, so every guard
  they carry ran unchanged — and one of them fired usefully: on the pristine archive text
  file 98 is a **56 B compression-8 stream of 1,024 empty records in a 512 B reservation**,
  so the first string write is a `datmove` relocation (→ 0x37B3400, 6,656 B), which
  `textwrite` planned and said before doing. `reskin-roster` never showed this because its
  row had already been rewritten stored.
- **The record is derived from the consumer, never typed.** `[[strings]]` names
  `quest = "rurik_first_errand"` and the record comes from that row's `enc_name` through
  `codedstr.decode_id` — 200, id 100552. The test refuses every other shape: a retail name
  (four ids), an id in ArenaNet's own file (0x3D64 → file 15), the identity tier, a consumer
  nothing defines, two consumers disagreeing. So a second quest name is one manifest line
  plus the quest row it belongs to, which is what B4's kill verb was waiting on.
- **The created ids are still clear on 38833, by one.** The highest plain file id in the
  pristine snapshot is 0x5F0AF — three above the 38797 answer `maps.toml` records — so
  0x5F0B0/1/2, chosen against 38797, sit exactly one above the newer table and their bit-31
  siblings bind nothing. `next_free_file_id(ar, 0x5F0B0)` answered 0x5F0B0. A fourth
  ArenaNet build could close that gap; the manifest's provenance records the number.
- **`frontier` allocated cleanly on the newer generation**: rows 177753/177754, 2,032 B
  compression-8 in an 8,192 B reservation from the area's declared budget, id on the head
  only, journal beside the archive, `created_evidence` binding by bytes.

## SLICE-F13 — **SLICE-B6: the corridor, the first rectangular footprint (SLICE-U4)**

**PRE-REGISTERED 2026-09-12 15:15, before the run.** `[area.corridor]` is 32×128 cells
(3,072 × 12,288 u), a 16-cell flat floor along the long axis between four-cell banks of
120 per cell (51.3°, class-2 under both slope sets), closed at both ends, plateau 480 u up
beyond the banks. Offline (`test_deploy` §14): the field is on the lattice (worst moved 0
after the edge was moved onto a multiple of 4 — the first draft's column-10 edge cost one
sample), the encoded terrain decodes back as **32×128 and not 128×32** (tag 0 stores dimY
before dimX; no square map could ever have refuted the reading), the seed measures 0.0°,
the banks 51.3°. Installed into the slice archive under `0x5F0B3` (map 168,
`explorable = true`).

**Question.** Does a retail client compile a non-square authored map, and does it mesh
the floor and NOT the banks or the plateau?

**Prediction.** (a) `Gw.log` shows `Map file '0x05f0b3' failed to load. Attempting to
re-bloat.` and `compose.py --readback` reports the compiled height field equal to the
authored one 4096/4096 — the rectangle compiled with our axes, not transposed (a
transposition fails the client's own `dims.x * XY_DIST == mapRect` assert at
TrnDataBloat:191, so it would show as a crash, not a wrong picture). (b) The mesh's
trapezoids cover the FLOOR only: the spawn (1536, 1536) lands in exactly one trapezoid,
and the compiled mesh's bounding x-extent is within the floor's 768..2304 u (16 cells
from column 8), never reaching the plateau's x < 384 or > 2688. (c) The screenshot shows
the character in a trench with banks on both sides.

**RESULT — ALL THREE HALVES OBSERVED. SLICE-U4 is CLOSED: a retail client compiles a
rectangular authored map, with our axes, and meshes exactly the floor.** Harness
`20260912T111229` (map 168, `--area corridor`, `RURIK_DAT` at the slice archive), RUN
VERDICT PASS, body in the map at t+22.1 s.

- **(a)** `Gw.log`: `Map file '0x05f0b3' failed to load.  Attempting to re-bloat.` Readback
  6 of 6 for the corridor: **the compiled height field equals ours 4096/4096**, environment
  and sound verbatim, the seed in exactly one trapezoid. No assert — so the y,x reading of
  tag 0 and `Terrain.index`'s tile order both hold for a rectangle, which no square map could
  have refuted. (`frontier`'s readback line is FAIL in the same report because this run
  loaded map 168 only; its head is armed, as `--build --fresh` left it.)
- **(b)** The compiled mesh is **2 trapezoids**: x **768..2208**, y **480..11904**. The
  floor is 768..2304 × 384..11904, the plateau begins at x < 384 / x > 2688. So the flood
  filled the floor, stopped at the banks, and never reached the flat plateau above them —
  W20/W23 transfer to a rectangle. The mesh sits one cell inside the floor on its right and
  south edges (the trapezoid excludes the cell whose quad touches the bank), which is the
  walkable-set rule rather than a lost cell.
- **(c)** Frame `hold006`: the character on cobbled floor with a bank of the same texture
  rising to the frame's top edge; the minimap draws a narrow strip.

**What this closes and what it does not.** SLICE-U4 (the client accepts an elongated
footprint) is closed by measurement. What the run does NOT say: whether the SERVER paths
the corridor (`prewarm_pathmap` ran before the head was compiled, so this run served no
collision — the second, unarmed run `deploy --serve` describes), and nothing about a
population, because `[area.corridor]` has no spawn rows yet. Both are the next item, not
this one.

**A defect found on the way, and its guard.** The second `compose.py --build` of the day
re-copied the pristine snapshot over the composed archive: `assemble` took "Gw.dat present
at the source's size" as "already staged", and every archive write changes the size (two
MFT rows, 48 bytes). It then rewrote the string and was **refused by frontier's own
allocation journal** — `datalloc`'s clobber guard, describing a chain the copy no longer
held. Fixed: a plain `--build` never re-copies a present archive; only `--fresh` does, and
`--fresh` removes the journals with it. `test_compose` §4 pins the order of the two tests.

**Refuted if** the client asserts on load (the rectangle itself), or the mesh's x-extent
reaches the plateau (the banks did not stop the flood — W20/W23 do not transfer to a
rectangle), or the compiled heights differ from ours (the tile order is not what
`Terrain.index` says for a rectangle).

**Exposure floor.** "body is in the map" and a non-zero head after the run. Short of that,
ABORT.

## SLICE-F14 — **the corridor populated, and the SERVER serving it**

**PRE-REGISTERED 2026-09-12 15:40, before the run.** Five spawn rows in
`content/world.toml` bind to `area = "corridor"`: two groups of a Bandit Raider
(`def_1421`, tracked now as `npc.bandit_raider`) and an Academy Monk (`def_1486`,
`npc.academy_monk`) 3,000 u apart along the floor, and a boss raider at the north end
carrying `glow = 5` — int property 29 on its agent, SLICE-F2's registered bit. The slice
archive already holds the corridor's COMPILED head from harness `20260912T111229`, so a
second, unarmed run is the first in which the server can read it before the client locks
the archive (`deploy.serve_run`'s reasoning).

**Question.** Does the server path the rectangular corridor it did not compile, and place
the population on it?

**Prediction.** `deploy.serve_run` returns **SERVE_PASS**: the gamesrv's own line
`[map] navmesh 0x5F0B3: 1 planes, 2 trapezoids` names the count `pathmap` reads from the
archive (2), and `area 'corridor': 5 of 5 placed`, none MOVED — every row sits on the
floor by construction. The boss's `0x009F [29, 94, 5]` goes out after its create; whether
the client DRAWS a red aura is not measurable in this run (the boss is 8,900 u from the
camera) and stays F2's open bit.

**RESULT — SERVE_PASS, twice, and a log-finder defect on the way.** Harness
`20260912T115507`: `[map] navmesh 0x5F0B3: 1 planes, 2 trapezoids`, `AREA: corridor -- 5
spawn row(s)`, every body created at its row's coordinates with no MOVED note,
`area 'corridor': 5 of 5 placed`, and `s2c glow 5 on 'corridor_boss' (0x009f, 14B)` after
the boss's create. `deploy.serve_run` nonetheless returned FAILED: "no gamesrv log from
THIS tree" — `harnesslog.log_source` probed the first 8 KiB for the `source:` line and the
gamesrv's start-up banner had put it at **byte 9,350**. Fixed (`SOURCE_PROBE = 65536`,
`test_deploy` §14 plants a line behind a 17 KiB banner and proves the old probe misses
it), and re-run: harness `20260912T115836`, **`SERVE VERDICT: PASS`** in the tool's own
words — "server loaded 0x5F0B3 with 1 plane(s), 2 trapezoids (MATCHES the 2 in the
archive); area 'corridor': 5 of 5 bodies placed".

So the server paths the rectangle it did not compile, and the slice's population — two
groups of a Bandit Raider and an Academy Monk, and a glowing boss raider — stands on it.
**Still open, by design:** whether the client draws the aura (F2's bit; the boss is
8,900 u up the corridor and no frame reaches it), and the skill bars (every body takes the
module default until SLICE-B3).

**Refuted if** the navmesh line names another count (the server's loader reads the
rectangle differently from `pathmap`), or a row is REFUSED as off-mesh (the floor is not
where the rows think it is), or `spawn_population` throws (the gamesrv prints neither
population line — the failure `PLACED_RE`'s comment was written for).

## SLICE-F15 — **SLICE-B3: the bars, the unconditional heal, and a hostile monk that heals whoever is hurt**

**PRE-REGISTERED 2026-09-12 16:20, before the run.** Offline this item is done and
tested: `skill_effect` rows for Orison of Healing 281 (`Heal`, target byte 3) and Banish
252 (`Holy damage`); the corridor's five rows carry bars (raiders 382/322/1, monks
281/252/276, the boss adds 323); `HERO_SKILLS` defaults to (281, 276); and a hostile's
heal now aims at the HURT body via `hostile_heal_target` — `ally_heal_target`'s policy
plus the caster's own health for an `ally` skill — and steps past itself, re-picking on
the same tick, when nobody is under `HERO_HEAL_AT` (`test_agentlife` SLICE-B3, 9 checks:
the hurt ally drawn, the healthy squad skipped with the cursor advanced and Holy Strike
out the same tick, the recharge uncharged, the hurt monk self-healing under Orison and
never under Restore Condition).

**The wiki disagreement, recorded rather than resolved away.** Every `skill_effect` row
before today agreed with the client endpoint for endpoint. Orison is 20→70 in build 38797
and 30→80 on GWW; Banish 20→56 against 20→65. Both pages' histories carry one edit,
**26 August 2026, "+skill balance update Feedback:Game updates/20260826"** — after every
build this repo pins. The rows take the wiki's NAME and the client's NUMBERS, say why, and
a build past 2026-08-26 will move them.

**Question.** In a fight on the corridor, does the hostile monk heal the raider the player
hurt, and does the raider's bar reach the player?

**Prediction.** Harness: `--walk "W:11 attack:90 wait:30 shot:1"`, `--enemy-hit 0.02` so
the player survives the exposure. The gamesrv log shows (a) raider 90 casting 382 / 322 / 1
and monk 91 casting 252 at the player — the bars, not the module default; (b) after the
player's swing lands on 90, **`agent 91 ... casts skill 281`** with `cast_target 90` and a
line `agent 90 healed N ... by 91`; (c) while 90 is unhurt, `agent 91 holds skill 281`
and Banish goes out instead. The frame shows the fight.

**RESULT — two runs, two defects found by running, one half unexposed.**

*Run 1, harness `20260912T122339`.* (a) OBSERVED: raider 90 cast 382, 322 and 1; monk 91
cast 252 (Banish, 49 to the player) and 276 — the bars, not the default. (c) OBSERVED:
`agent 91 holds skill 281: target ally, and nobody is under 90%`, Banish out instead.
**Then the line that should not exist:** `agent 91 casts skill 281 … healed 0 of 60 sent:
160/160 (self)` — a full-health monk healing itself. The re-pick loop was bounded by the
bar's LENGTH and left by exhaustion with whatever the last re-pick returned: two heals and
a recharging Banish is three passes, the third re-picks Orison, and the loop fell out with
it un-targeted and `cast_target` still the player, which the target byte resolves to the
caster. My offline fixture never cycled that far. Fixed — a slot re-picked after being
held this tick ends the search — and the run's own bar is now the known-bad arm in
`test_agentlife` (red with the old loop, green with the fix). (b) NOT EXPOSED: the
player's swings took 90 to 188/200, 94%, and Healing Signet took it back; the floor as
registered ("a swing lands") was met but the threshold was not, which is a floor written
against the wrong quantity (`feedback-floors-must-count-the-arm-not-the-message`).

*Run 2, harness `20260912T123033`, no keyboard leg, 60 s window.* Orison was **held for
the whole fight** — zero `casts skill 281`, the fix observed on a client. Still (b)
unexposed: 196 → 190 → 184/200 (92%) and back to 200 on Healing Signet. **And the raider
cast Healing Signet at 200/200 every 4 s** — `healed 0 of 154 sent` six times — the same
wart from the `self` side, which the need-gate had not covered. Gated now, and narrowed
at the same time: the gate is on skills whose row is a HEAL (`skill_heal`), so Vital
Blessing (target ally, an enchantment) keeps the pre-B3 rule rather than being held for
a need this server cannot judge. Both arms in the test.

**The exposure gap, named.** A level-1 player's swing does 4–6 against a 200-hp raider
with a 4 s self-heal; 90% is 20 damage in one recharge window. The heal-on-hurt half is
proven offline (the hurt ally drawn, healed, the healthy squad skipped) and stays
UNOBSERVED on a client until a run with a harder-hitting player or a lighter raider — a
probe arm, not a content change.

**What the owner saw, both explained by the log.** The character ran EAST: `W` is
camera-forward and the spawn faces +x; the corridor runs +y, and no content field carries a
spawn facing (a small follow-up). The "server ghost" is the harness `attack:` step's own
mechanism — `approach: player walks to agent 90, 2428 u out` — the server walks ITS model
of the player to the target, the hostiles aggro on that model, and the client is brought
to it. Run 2 dropped the keyboard leg and used the approach alone (3,073 u).

**Exposure floor.** The player's swing lands on 90 at least once (90's health drops in
the log). If it never does — reach, aggro pulling 90 away, a dead player — the heal half
is an ABORT, not a null; (a) and (c) still score.

## SLICE-F16 — **SLICE-B5: the reward is granted at turn-in, and it is ours**

OFFLINE, 2026-09-12 (`test_quests` §23, 9 checks, floor 94 → 103). `grant_quest_reward`
pays a turned-in quest's `reward_experience` through **`0x00EE [0, delta]`** — the kill
template's own message, `[0, 26]` on 3 of 3 clean kills, which the client applies `+=` to
the sheet — with a kill's three consequences through the same functions: the wire delta,
the death-penalty credit (`morale_experience`), and the persisted sheet under `--persist`.
The turn-in branch calls it after the two removes and records the quest in a new
`quests_completed` set on the progress carrier, so a turned-in quest is **not offered
again** and its giver's `!` does not come back — the fourth state `_quest_markers`' table
did not have.

**The label.** The completion family (`0x004E`, `0x006C`, `0x0096`, `0x0097`, `0x00FB`) is
0 of 22,524 in the corpus: nobody turned a quest in on a live capture. So what ArenaNet
sends at that moment is NOT FOUND and this is authorship — the number the offer screen
already promised (`Reward: / 100 Experience`, in the description string, SLOT A IS
EXPERIENCE 2026-08-16), paid by the only experience message we have measured. The order
(after the removes) is ours too, and says so.

**Gold is not granted.** No gold message is identified; a row carrying `reward_gold`
draws a line the server prints a loud `NOT GRANTED` for and pays nothing. The content
row keeps the key commented out, and its comment no longer says "nothing is granted".

**OBSERVED on a client, by the owner, 2026-09-12 — harness `20260912T141042`.** The owner
drove the whole quest by hand: accept, walk, talk, walk back, turn in. The log reads
`quest 1463 turned in: +100 experience`, then both markers clear and the window closes.
"Mechanically it all functioned." **And three things felt wrong against stock, all three
real, all three fixed the same afternoon:**

1. *"The interact fires off without having to walk into close range."* `INTERACT_RANGE`
   was 250 u; the owner read it as "probably 2x" stock. WIKI (GWW, "Range", "Touch range
   and melee range", read 2026-09-12): 144 gwinches is "the shortest unit of distance
   used in the game". It is 144 now — the ladder's shortest rung as the best-supported
   number, 250/144 = 1.7 being what "probably 2x" looks like.
2. *"It doesn't automatically path the player to them ... I had to manually move to the
   scout."* The hold had no walk: the bare `0x002A` was measured on 2026-08-19 to drag
   the character through a staircase and was shipped off, and the log line still said
   "walking the player over" while nothing walked. The router (MOVECODE-1z-v) did not
   exist then. `interact_route` now answers an out-of-range interact as a CLICK at a point
   100 u short of the NPC, through the same `router_answer_click` the `0x003E` arm uses —
   the client walks routed legs with its own collision, the integrator advances the model,
   and the existing hold serves on arrival. OURS, on our mesh, `--no-interact-route`
   reverts. The log says which of the three (routed / 0x002A / nothing) actually went out.
3. *"There should be 2 line breaks between the quest dialogue and the reward."* One
   `0x0002 0x0102` run drew a line end; stock draws a blank line. Two runs now.

Also seen in that log and worth the note: **space re-sends `INTERACT`** (`0x0039`, no
movement message) — it is the client's "interact with target" key — so with the routed
walk in place, space walks the player over exactly as it does on stock.

**Not yet observed:** the three fixes on a client. Same hand-driven run, same map.

~~**Not observed on a client, and why.** The turn-in is a click on the giver, a click on
the option, twice — aiming, which is the owner's half of a run
(`feedback-owner-drives-client-runs`). The wire half is the kill's message, already
proven to move the sheet; what a run would add is the sheet moving by 100 on the turn-in
click. One hand-driven run with `--map 146 --area errand`, reading the XP bar before and
after, closes it.~~

## SLICE-F17 — **SLICE-B8: the transfer, sent by us — 148 → 146 on our own trigger**

**PRE-REGISTERED 2026-09-12 17:40, before the run.** Two `[portal.*]` rows: a 200 u
circle 500 u west of the shared arrival point on 148 and on 146, each pointing at the
other (the point is MEASURED walkable on `0x1B97D`'s mesh; 500 u east is not). A player
who was outside a circle and walks in gets `0x0028 → 0x01A5 → 0x0099` — the sequence
retail's server sends unprompted in 34 of 41 corpus transfers (SLICE-F8) — with a
sockaddr for the alias the client is NOT on (the harness gives the gamesrv a second
listener, game host + 30), this connection's `world_id`/`player_id`, the destination and
its `explorable` byte; then the tape's own graceful close (`graceful_close`, extracted
from `close_after_transfer`). On re-entry the VERSION frame's ids match what we issued and
`--map` stands down (`test_transfer`, 22 checks).

**Question.** Does a retail client, handed `0x01A5` by OUR server, re-dial OUR other
alias and load the map we named — and does our server serve it there, on one process,
with the quest carrier intact?

**Prediction.** Harness `--map 148 --walk "S:2 wait:25 shot:1"` (S walks −x from the
+x-facing spawn: 576 u west, into the circle). The gamesrv log shows, in order:
`PORTAL 'ascalon_to_lakeside'`, `TRANSFER to map 146 via 127.0.0.33:6112`, `closed
(transfer)`; then a NEW connection `[c2] GAME version ... map_id=146` with the SAME
world_id/player_id as c1's, `RE-ENTRY after our own transfer ... --map 148 stands down`,
and c2's instance load reaching `INSTANCE_LOAD_FINISH` on 146 with the player at
(9826, 8077). `Gw.log` shows a map load, no assert. The two maps share a file id, so the
screen will look the same — §5 calls that a feature for the first run.

**RESULT — OBSERVED, every predicted line, in order. Harness `20260912T143555`.**

```
[c1] GAME version: build=38797 world_id=1546700710 map_id=148 player_id=327600940
[c1] PORTAL 'ascalon_to_lakeside': the player is 158 u in (radius 200) -- transferring to map 146
[c1] s2c transfer 1/3: AGENT_STOP_MOVING [player] (0x0028, 6B)
[c1] s2c transfer 2/3: GAME_SERVER_TRANSFER -> 127.0.0.33:6112, map 146 (0x01a5, 39B)
[c1] s2c transfer 3/3: MAP_UPDATE_CURRENT 146 (0x0099, 5B)
[c1] closed (transfer) after draining 0 B
[c2] GAME version: build=38797 world_id=1546700710 map_id=146 player_id=327600940
[c2] client asked for map 146 -- a RE-ENTRY after our own transfer ... --map 148 stands down
[c2] s2c MAP_UPDATE_CURRENT ... READY_FOR_MAP_SPAWN ... INSTANCE_LOAD_FINISH ... PARTY_ADD_MEMBER
[c2] s2c KBD STOP-ECHO (9826,8077) plane 0
```

The client re-dialled **our other alias** with the ids we gave it, our server served the
map we named on the same process, and the instance load ran to the end — 148 `[c2]`
lines, 30 of them the client's own. The frame after the wait shows the character at the
arrival plaza, which is what §5 predicted a 148 → 146 hop would look like: nothing, on
purpose, because the two maps share a file. **SLICE-U3's route — the real one, no shim —
is closed.** Note the harness's own limits: its RUN VERDICT and its hold screenshots
belong to c1, so the c2 evidence is the gamesrv log, and `--shots` stopped at the
transfer; a chained verdict is a harness follow-up, not a zoning one.

**What the run does NOT say.** The quest carrier across a hop (nothing was accepted
before walking in — `QUEST_PROGRESS` is process-global and `bind_progress` re-points c2
at it, which is the design, not a measurement); the corridor as a destination (map 168 is
in the slice archive only, so that hop is a run on `vault/run/slice` with a portal row
148 → 168 and `RURIK_DAT` at its archive); and T9's same-endpoint re-dial, which stays
NOT FOUND because the alias changed by design.

**Refuted if** no `[c2]` ever appears (the client did not re-dial: the close's reason
code, or the alias, or the port trap — T9's "the client ignores the advertised port" was
measured on the AUTH channel only); or `[c2]` asks for 148 (the ids did not carry); or
the client asserts on the load. **ABORT** if the portal never fires (the leg did not
reach the circle — a walk-direction or arming fault, scored on the c1 position reports).

## SLICE-F18 — **the slice assembled: outpost → corridor on our portal, one process, two maps, and the kill quest on shipped content**

**PRE-REGISTERED 2026-09-12 18:50, before the run.** Content: `[portal.ascalon_to_corridor]`
(148 → 168, the spot SLICE-F17 proved) and `[portal.corridor_to_ascalon]` (168 → 148 at the
corridor's south end); the 146 pair moved 500 u north as the control. `[quest.rurik_bandits]`
(1464, "Bandits on the Road", record 201 — now in the slice archive, 11 of 11 verified),
`objective_kill = "corridor_boss"`, given by Fisk. The server serves several maps on one
process, so `--area` takes a comma list and a spawn row is placed only on the map it is FOR
(`map = N` on the row, else its area's `map_id`, else anywhere): Fisk is 148's, the five
corridor bodies are 168's. Offline: `test_quests` §24 drives B4's verb on the shipped row
(kill agent 94 → objective met → the giver offers TURN_IN beside the errand's SHOW),
`test_transfer` §6 drives two maps on one process.

**Question.** On the slice archive, does walking into the outpost's west portal load the
CORRIDOR, populated, with Fisk left behind in the outpost?

**Prediction.** `RURIK_DAT` at the slice archive, `--map 148 --area errand,corridor --walk
"S:2 wait:25 shot:1"`. The gamesrv log: c1 places `errand_giver` and `errand_scout` on 148
and says the five corridor rows "belong to another map"; `PORTAL 'ascalon_to_corridor'` →
`TRANSFER to map 168`; `[c2]` asks for 168 → RE-ENTRY; c2's pre-warm loads `navmesh 0x5F0B3:
1 planes, 2 trapezoids`; c2 places `5 of 5` corridor bodies and says the two errand rows
belong to another map; the boss's glow goes out. The frame after the wait shows the
corridor's cobbled trench.

**RESULT — OBSERVED, and the prediction's one miss was a real defect.** Harness
`20260912T144803`: c1 placed `2 of 2` (Fisk and the scout) and held the five corridor rows
back — "belong to another map than 148"; `PORTAL 'ascalon_to_corridor'` → `TRANSFER to map
168`; `[c2]` asked for 168, RE-ENTRY, `--map 148` stood down; c2 held the two errand rows
back and placed `5 of 5` with `glow 5 on 'corridor_boss'`. The frame after the wait is the
corridor's trench with two hostiles on the compass. **But c2 said `NO NAVMESH`**: startup
pre-warms the pinned map only, and by c2's bring-up the client held the archive, so the
corridor's mesh was never read and its bodies were placed on trust. Fixed the same hour —
`portal_reachable` walks the portal graph and every destination is pre-warmed at startup
(`test_transfer` §7) — and re-run as `20260912T145253`: `[map] pre-warming map 168 ...
navmesh 0x5F0B3: 1 planes, 2 trapezoids` at startup, the portal fired at 148 u, c2
re-entered 168 and placed the corridor on its own mesh.

So the slice's shape is assembled: **outpost → corridor on our portal, one process serving
two maps with each map's own population, the kill quest on shipped content** (offline:
kill 94 → objective met → Fisk offers TURN_IN beside the errand). **THE OWNER RAN IT, 2026-09-12, harness `20260912T151631`** — accept, zone, fight, kill
the boss, zone back, turn in — and reported: **"quest survived both hops, boss aura was
red."** Two measurements in one sentence: the quest carrier across two transfers, which
was design and is now OBSERVED; and SLICE-F2's registered bit — index 5 rendered RED, so
`s_glow`'s byte at `+4` is the red channel. That bit is closed. What the owner reported
next is SLICE-F19.

**Refuted if** c2 never comes (the client will not load a created map on a re-entry: the
first time a transfer names one — F13's compile was a first entry), or c2 loads without the
corridor's mesh, or a body is placed on the wrong map. **ABORT** if the portal never fires.

## SLICE-F19 — **combat on the first full run: an attack skill that strikes from anywhere, and what kiting shows**

OBSERVED by the owner, 2026-09-12, harness `20260912T151631`: *"combat still bad though, I
get by with a glitch on Power Attack that allows me to cast it without stopping to complete
the attack animation. Enemies don't attack you if you just constantly kite them, so I was
able to aggro all 5 enemies and slowly whittle the boss down."* The log agrees on every
count: **20 strikes of 322 landed against ONE ordinary swing**, presses from 170 u out with
`action released: the player moves` inside the windup; hostiles **followed 93 times, swung
4 times, hit 0**.

**The attack skill.** WIKI (castmech §4, GWW "Quarterstepping"): "attack skills can not be
accidentally cancelled by moving prematurely" — so this is NOT a missing cancel. On retail
the *client* holds the body through the swing; ours does not (property 8 is view plumbing,
castmech 3c), so a player presses at range, keeps running, and the strike lands wherever
they are. The server's guard is now **reach at the strike**: an attack skill executes on a
target within `attack_reach()` (144 u) at its E5 instant and nowhere else; out of reach it
is released as a cancel — the measured burst, no recharge, costs paid (GWW "Cancel") — and
the log says how far (`strike_out_of_reach`, `test_castcycle` §2d, both arms one number
apart). A press from out of range still activates; on retail that press begins an APPROACH
(the player walks in and strikes on arrival), which the server has for ordinary attacks
(`begin_attack`) and not yet for attack skills. **Named as the follow-up; done the same day as SLICE-C2, SLICE-F20, with retail's contract for it measured.**

**The kiting.** ANIMREF-RE 40 is measured retail: a hostile mid-follow does not swing (0 of
4 multi-follow chases open an attack), it swings after the halt. At equal speed a follower
never halts behind a player who keeps moving — so a player who never stops is never hit,
on retail's own rule, and the four swings that did open landed nothing because the body
had moved by the strike. What made it a *glitch* was the strike from range: with reach
enforced, kiting deals no damage either, and the fight is stand-and-swing on both sides.
Whether retail's melee hit lands on a target that moved out during the windup is NOT
MEASURED here and is the other half of this question.

## SLICE-F20 — **SLICE-C2: an attack skill pressed from out of reach walks in, and retail's contract for it, read off the tapes**

**The question** (SLICE-F19's follow-up): a press of an attack skill with the target past
reach — what does retail's server send, when does it pay and animate, and what cancels it?
Until 2026-09-12 ours activated at the press, paid and animated at once, and then (since
C1) found nothing in reach at the strike and released it. The owner's Power Attack from
170 u was exactly that press.

**Measured, 2026-09-12**, over the 20 live captures (`livewire.decode_conn`, both
directions on one clock, the observer by the self-scoped property 41): **94 c2s `0x0027`
attack-skill presses, 80 accepted, 14 refused** (the §19 charge gate). Of the accepted,
**51 are FREE presses** (E4 within 0.1 s of the press); **11 of those carry a `0x002A`
follow to the target in the same instant** — the out-of-reach cell — and 40 do not.
20260817T231139 t=717.315 (skill 385 → agent 9, a live chain) is the clean instance,
and every other one has the same shape where it is not cut short:

| instant | what retail sends | n |
|---|---|---|
| **the press** (+0.024–0.050 s, ONE batch) | `E4 [me, skill, copy]`, then `[8, me, 0]` and `GV_ATTACK_STOPPED [3, me, 0]` when a chain was live, then **`0x002A [me, target's own point, plane, plane, target]`** — **no debit, no animation** | 11 of 11 |
| **while walking** | the follow re-issued every 0.5 s while the target moves (717.315: +0.552, +1.049) — ANIMREF-RE 38's contract, shared with the ordinary press | — |
| **arrival** (0.23–1.9 s after the press) | **the cost** (`0x00D2 [me, skill, copy]` for adrenal skills, property 62 for energy — 248.991 skill 780 carries `[62, 27, frac]`), then **`0x00A0 [50, me, target, skill]`**, then **`[8, me, 1]`** | 3 of 3 uncut (717.315, 371.949, 657.289); 248.991 the energy one |
| **the strike**, one windup after arrival | `[46, me, 0]`, the adrenaline gain, the damage `0x00A3 [17/16, target, me, f]`, `0x00D0`, `E3` — the R6 execution batch | 717.315: 0.566 s after arrival; 371.949: 0.565 s; `swing_windup(1.33)` = 0.565 |

So an out-of-reach attack-skill press is **a queued cast whose begin instant is
ARRIVAL**, not a clock: E4 at the press, the burst tail at the begin — the same rule
castmech 3b/3c measured for a clock-queued cast (skill 105's debit and animation riding
153's E3) — and the walk in between is the follow the ordinary attack already uses. The
windup law lands the strike where retail lands it.

**What cancels it, also measured:**

- **The player's own movement before arrival** — 20260810T235916 t=276.699 (the ranger's
  Power Shot → 276): follow at +0.034, a `0x003D` at +0.885, then `[45, 31, 0]` + `E2` at
  +0.919 and **no debit ever**. The queued-not-begun cast dropped by movement — our
  existing rule (`_mark_cancelled`, `spare_mid_attack`: an entry with no begin yet is
  droppable whatever its family) reaches it because the approaching entry's `begin_at`
  is +inf. n=1.
- **The target dies on the way** — 525.104 (skill 384 → 12): follow at +0.038, the
  target's death batch at +0.496 carries `[45, 13, 0]` + `E2`. Ours releases the entry
  unpaid from cast_tick's approach arm. n=1.
- **A `0x0026` attack press on the same target during the approach** — 710.693: follow at
  +0.033, c2s `0x0026 [9, 0]` at +0.267, `[45, 11, 0]` + `E2` at +0.300, the follow
  re-issued and the chain's own swing opening at +0.588. **NOT shipped**: n=1, and on ours
  `begin_attack` on the same target simply cooperates with the entry (attack_tick pauses
  its swing while the entry is short of its E3). Recorded for the next reader.
- **Cancelled AFTER arrival** — 657.289 (arrival +0.232, then `[49, 11, 0]` + `E2` at
  +0.796 with the chain's `attack_started` in the same batch) and 248.991 (arrival +0.542,
  `[49, 27, 0]` + `E2` at +0.699, `attack_started` in the batch). Property 49 rides a
  cancel after the begin, property 45 a cancel before it; neither is named in our
  catalog and neither is sent (C1's rule: the release burst stays the measured
  `[8→0], 59, E2`). What cancelled 657.289 is not readable off the wire — the target
  took a hit from another agent 0.1 s earlier — and it is SLICE-C3's question in another
  form (a strike that does not land on a target that moved). NOT MEASURED here.
- **The press engages the chain**: 248.991 — after the skill's release the server opened
  `attack_started [4, 27, 144, 0]` on the target in the SAME batch with no `0x0026` between
  the press and it. n=1. Shipped for the approach case only (`state["attacking"] =
  target` at the press; it is also what keeps attack_tick's own approach arm walking to
  this target rather than a previous one); an in-reach attack-skill press engaging the
  chain is the same n=1 and is left as it was — **ASSUMPTION, both ways, until a second
  witness.**

**Two things this cell does NOT settle.** (1) A press while the caster is BUSY (a cast
short of its E3) with the target out of reach: no corpus press is both queued and out of
reach; ours keeps the clock queue for it and C1's reach gate covers the strike. (2) Whether
retail's in-reach attack-skill press with a swing in flight waits for that swing: the
in-reach free cell's property-50 delay is p50 0.307 s (n=38) against the 0.024–0.05 s
press-burst delay castmech 3b measured on the necromancer and ranger — a warrior with a
live sword chain, so probably the swing in flight completing first. Not this item's
question; recorded because the number was in the way.

**Shipped:** `handle_skill_press` decides `approaching` (attack family, `ATTACK_APPROACH`,
a live target past `attack_reach()` in the client's frame, caster free); the press sends
E4 and the chain stop as before and then `_approach_send` in the same batch, pays and
animates nothing, and appends the entry with `approach = target` and every instant +inf;
`cast_tick`'s approach arm drives `approach_tick` (the ordinary attack's leg, re-paths and
all), releases the entry unpaid if the target is gone, and on arrival
`attack_skill_arrives` writes the clock (E5 = arrival + the windup for the table-0.0 case,
else the listed activation), the begin branch pays and animates, and `[8 → 1]` closes the
arrival burst. `--no-attack-approach` keeps the old press (no follow, strike from
anywhere). `test_castcycle` §2e drives the whole cycle: the press batch, a walking tick
that begins nothing, the arrival burst, the strike from the stop point through C1's gate,
the in-reach control, the two unpaid cancels, the revert arm. **Unobserved on a client**
until the owner's next pass; the hand-run question is one sentence — *press Power Attack
on the boss from across the room: does the character walk in and strike on arrival, and
does W on the way cancel it cleanly?*

**The owner's second run, same day, and what it corrected.** *"It does get cancelled by W,
but I don't think in stock the cancel animation plays over the player's head unless they
actually start the cast. Here we do it even if they cancel a chase-cast."* Right, and the
tapes above already said so: the walk-in IS retail's own follow (the `0x002A` the ordinary
attack uses — the E4 at the press is retail's too, 11 of 11), but our release burst sent
property 59 for every cancelled cast, and 59 is the one that reaches `InterruptSkill` — the
body plays a stop for a cast that never began. The pre-begin drops in the table carry
**property 45 and the bare E2, no 59 and no hold release** — and with this scan the count is
**4 of 4 pre-begin drops with 45** (castmech §3's terminated cast, 276.699, 525.104,
710.693) against **0 of 6 begun cancels**, which is castmech §3e's "queued-drop" candidate
confirmed rather than a one-sample guess. The begun cancels split by family: **59 for a
spell (4 of 4, castmech 3f), 49 for an attack skill (2 of 2: 657.289, 248.991 — the attack
trio's own stop, 50/46/49)**. Shipped as `release_cancelled_cast`'s three-way choice
(`agents.GV_CAST_DROPPED = 45`): never began → `[45]`, E2; begun spell → `[8→0]`, `[59]`, E2;
begun attack skill → `[8→0]`, `[49]`, E2. `test_castcycle` §2d/§2e and `test_castcancel` §3
pin all three. The 49 arm also corrects C1's out-of-reach strike release, which had borrowed
the spell's 59.

**The owner's third run (harness `20260912T170924`): the 45 release is right, the body
still slides.** *"No cancel over the head this time, icon just released. Still sliding
during the Power Attack animation. Stock behavior is needing to stand still during the
cast animation, then able to move again once the attack swing completes (but before the
animation completely plays out, like quarterstepping)."* The log has the mechanism in
four lines: the strike begins on arrival with `[8 → 1]`; a `0x003D` keyboard report
arrives inside the windup; our server answers it — `action released: the player moves`
(`[8 → 0]`) and a KBD LEAD `0x0029` — and the body walks through the strike. **Retail
defers that report, 2 of 2** (`c3_midskill` scan, the same corpus): a `0x003D` at +0.378
and +0.439 s into a 0.565 s attack-skill windup (`20260817T231139` t=693.029, 765.092)
gets **no answer at all** until the strike, where `[46]`, the adrenaline gain, `E3`,
`[8 → 0]` and only then the movement answer (`0x0025`, `0x002B`, `0x0029`) go out in ONE
batch. A spell's mid-cast report is answered at once (59, E2, the grant — 2 of 2 on the
cancel-family capture), so the deferral is the attack family's. Shipped: a guard arm ahead
of both movement arms refuses a moving `0x003D` or a `0x003E` while `attack_skill_roots`
names a begun, unstruck attack skill — no hold release, no chain stop, no lead, no position
take, printed once per cast (`ROOTED: keyboard report refused …`). After the strike (E3 =
E5 for an attack skill) nothing roots, so the next report is answered as before: the
quarterstep. `--no-attack-skill-root` is the revert. `test_castcancel` §3b.

**Residual, named.** Retail answers the *withheld* report itself at the strike, in the E3
batch, behind an `[8 → 0]` that is the E3 release ANIMREF §29 reverted to opt-in
(`--e3-release`, Suspect B unmeasured). Ours releases nothing at the strike and waits for
the client's next report, which the run shows the client re-sending every few hundred
milliseconds against the held gate. One change per run: if the owner reports a hitch
between the hit and moving again, the attack-family E3 release is the next single-flag
A/B, and it is measured (3 of 3 attack-skill E3s carry `[8, me, 0]`).

**The owner's fourth run (harness `20260912T192442`): the root refuses the report — and
two things it could not touch.** *"Still able to cast it while moving and slide, and
holding W enables the cast to go through but doesn't move me after the swing connects."*
The log shows the root working (`ROOTED: keyboard report refused during skill 322's strike
windup`) and the two mechanisms behind the sentence, one at each end of the windup:

1. **The press while running.** An in-reach attack-skill press with a keyboard lead in
   flight: the burst goes out with `[8 → 1]`, but nothing we send stops the leg already
   executing — CANCELWALK-F28's glide, whose fix (the R8/R10 cast-stop, `--cast-stop=pin`
   by default) was scoped NON-ATTACK because "an attack skill's start drives chase movement
   a halt would fight". SLICE-C2 moved that chase to a follow that begins the strike parked,
   so the in-reach press is the only attack case left — and for it the halt is **measured
   where the spell's never was: 2 of 2 in-reach attack-skill presses on a running body are
   answered with a bare `0x0028 [me]` in the press batch** (`20260810T235916` t=284.607;
   `20260817T231139` t=645.377, 0.12 s after a lead the server had just granted), behind the
   `[8 → 1]`. Shipped: the `not is_attack` scoping is gone; the pin-or-nothing machinery runs
   for both families. Slot residual: retail's halt follows the hold, ours keeps the spell's
   chosen slot before the animation — same batch. `--no-cast-stop` reverts (both families).
2. **The held key after the strike.** With W held through the windup, the client's walk gate
   stays set and a held key has no new edge to report — so after the strike nothing arrives
   and nothing releases. Retail's attack-skill E3 carries `[8 → 0]` **exactly when a report
   was withheld during the windup (3 of 3: 717.315, 693.029, 765.092 — and that batch then
   answers the withheld report) and not otherwise (0 of 3: 284.607, 617.247, 645.377, where
   the hold releases on the next input)**. Shipped: the strike releases the hold when
   `moves_refused` is set on the cast, which clears the client's gate and arms its own 250 ms
   resume poll for the held key (ANIMREF §28's decode). Retail also answers the withheld
   report itself in that batch; ours still leaves the grant to the client's next report —
   the residual stands, one step smaller. Same flag as the root, `--no-attack-skill-root`.

`test_cancelwalk` §7 (the attack arm now carries the pin and the halt) and `test_castcancel`
§3b (the release rides the E3 only with a withheld report) pin both. Two changes for one run,
against §29.1's rule, because they are two symptoms with two revert flags: the run can
convict either alone — *press while running: does the body stop?* / *hold W through the
windup: does it move after the hit?*

**The owner's fifth run (harness `20260912T194350`): the halt is convicted, the release
alone is not.** *"Yes, the body stops. No, it doesn't move after the hit lands."* The log: the
strike batch carried the `[8 → 0]` release as shipped, and the client's answer to it was a
**`0x0047` stop report** — not a walk. A held key has no new edge to report, and the client's
own resume poll (ANIMREF §28's decode) does not produce one either: it reported a stop. So the
residual named twice above was the whole mechanism: **retail's strike batch answers the
withheld report itself** — `[8 → 0]`, then `0x0025`, `0x002B`, `0x0029` for the LAST report
withheld (692.825: two withheld, mt 8 then 3; the answer is mt 3) — and the client walks on
that answer with no report of its own (0 c2s between the withheld reports and the strike
answer, 2 of 2). Shipped: the refusal keeps the latest report (`state["withheld_report"]`);
the recv loop's socket timeout is shrunk to the rooting cast's E3 instant (`withheld_wake`,
floor 0.02 s over the tick's 50 ms cadence); once nothing roots, `withheld_replay_take`
sends the release and hands the report back, and the loop dispatches it through the very
movement arm it was refused from — as a batch of one on the quiet wake, or FIRST in a
received batch, ahead of any `0x0047` the client sent against the still-held gate. The tick
no longer releases at E3: a player grant is recv-thread-only (REV-2), so the release and the
answer go out together as retail's do; the split from the E3 itself is the recv wake's
latency, 20–50 ms. `test_castcancel` §3b (floor 40 → 44) pins the keep, the refuse-while-
rooting, the release-and-hand-back, the one-answer-per-report, the nothing-withheld null,
and a source lock on the wake shrink and both replay branches.

**The owner's sixth run: OBSERVED.** *"Body walks after the hit now."* The attack skill's
feel now matches the owner's description of stock at every step measured here: the press from
range walks in and strikes on arrival, W on the way cancels it with nothing over the head, the
press while running stops the body for the windup, the body is rooted through the windup, and
a key held through it walks the moment the hit lands. Left open from this thread: SLICE-C3
(does retail's melee hit land on a target that stepped out during the windup), and the slot
residual (retail's running-press halt follows the hold; ours precedes the animation).

**Refuted if** the owner's press from range still strikes without walking, or the walk
ends and nothing begins (the arrival predicate — `approach_tick`'s eta-or-stop-radius —
disagreeing with the client's own resolver, which C1's gate would then show as a released
strike at 80–144 u), or a queued clock-cast behind an approaching entry begins before the
arrival.

## SLICE-F21 — **SLICE-C3: retail's melee hit lands on a target that moved during the windup — reach is judged at the start, never at the landing**

**The question** (SLICE-F19, SLICE-F20): kiting cost the kiter nothing here, and one reason
was ours to check — an armed swing was dropped the moment its target left reach, at three
sites: the enemy loop (`swing_lands_at` cleared past `enemy_reach()` or when the chase
re-issued), `attack_tick` (the player's swing in flight dropped past `attack_reach()`), and
SLICE-C1's release of an attack skill's strike past reach. Whether retail's landing has a
reach term at all had never been measured. The plan costed a narrated live capture; the
corpus already held the answer.

**Measured, 2026-09-12**, over the 20 live captures (`toolkit/authsrv/latehitjoin.py`): every
`attack_started [4, A, T]` and every attack-skill animation `[50, A, T, skill]`, its outcome,
and whether the target moved inside the windup (the observer's own `0x003D`/`0x003E` reports;
an NPC's `0x0029`/`0x002A`/`0x0025`):

| swing | target moved during the windup | hit | stopped | other |
|---|---|---|---|---|
| a hostile's, at the observing player | 7 | **7** | 0 | 0 |
| the player's own, on an NPC | 34 | **33** | 1 (a retarget) | 0 |
| an attack skill's, on an NPC | 11 | **11** | 0 | 0 |
| NPC on NPC | 78 | 51 | 21 (the chases' retargets) | 6 |

The seven swings at the player are the cleanest, because the player's reports are the
truth: four have a report within 0.5 s before the start and reports inside the windup, and
the displacement at the last report inside is **81, 137, 202 and 288 u** — with another
0.3–0.5 s of running between that report and the hit, so the hit landed with the player
roughly 200–400 u from where the swing opened, against a halt reach of 80 u. The corpus
holds ONE attack-fail word in 1,332 starts (SKILLS-BL), so nothing on retail whiffs for
distance. **Rule, OBSERVED:** reach is judged when a swing OPENS — the halt disc for a hostile
(ANIMREF-RE 40), the press-time reach for the player (ANIMREF-RE 38) — and an armed swing
lands wherever the target went. The "stopped" outcomes are retargets and aggro changes, not
misses.

**Shipped** (`LATE_HIT`, `--no-late-hit` reverts all three): the enemy loop resolves an armed
landing BEFORE its reach/follow gate, so the gate is for the next START only; `attack_tick`'s
out-of-reach branch lands a swing in flight when due (`_land_player_swing`, one site for the
in-reach and out-of-reach landings) and refuses only the next start; SLICE-C1's strike gate is
the revert arm's — an attack-skill strike on a target that stepped out lands (11 of 11), and
the press C1 answered (a strike from 170 u while running) cannot happen since C2's approach,
the root and the running-press halt. The corpse and burrow truncations keep their measured
drops. `test_playerswing` §3 and its reach-telemetry section, `test_agentlife`'s "leaves
range" arm and `test_castcycle` §2d flip to the landing and pin the revert arm.

**What this changes for the owner's kiting report.** A hostile still cannot OPEN a swing on a
body that keeps moving (RE 40, retail's own rule), but every swing it does open — at the
halt, or when the kiter turns, stops or is caught — now lands even if the kiter is 300 u away
by the hit. That is retail's cost of kiting, and it is the only one the tapes show.

**Refuted if** a swing the owner sees connect on the client does no damage, or a swing on a
target that plainly stepped out does damage on retail's client but not here in the same
shape — either would mean the landing has a term the seven swings did not exercise (e.g. a
plane change, or a distance past ~400 u).

## SLICE-F22 — **the halt owes a swing: why kiting stayed free after F21, and retail's halt-then-swing on a runner**

**The owner, after F21** (harness `20260912T203323`): *"kiting still too effective. There's a
delay between when the chase ends, the enemy stops, and the attack begins. I got attacked
when I stood still, but if I just keep moving the enemy never quite settles and starts an
attack."* The log agrees and names the shape: **105 halts, 18 re-paths, 4 swings**. The raider
halts *"arrived 0.20 s ago, 112 u from the player"*, re-follows a 20–40 u leg, halts *"95 u
from the player"*, re-follows, halts — and never swings. Two of our own rules compose into
that: the halt waits for the follow's half-second clock (ANIMREF-RE 40.9, the fix for a
rendered body trailing its copy), and the swing tick that follows the halt **re-tests the
live distance** against the 92 u start reach. A runner drifts 15–30 u in the clock wait,
lands at 95–112 u, and the catch is spent on another 20 u leg.

**Retail, from the same corpus.** The halt IS the arrival and the swing follows it: 0.159 /
0.242 / 0.139 / 0.379 / 0.153 s after the halt, 5 of 5 halted chases (§40.2) — on a server
copy of the player that lags its reports (12–32 u when a report is fresh, 75–85 u at 0.5 s),
so the geometry the swing opens on is the halt's, not the live body's. And retail's hostiles
do open swings on a running player: **3 of the 45 hostile starts at the observer have a move
report 0.10–0.17 s before and 0.17–0.33 s after the start, 77–144 u apart** (337.071 with the
follow point 77 u from the player's report; 193.935; 204.855 — `c4_start` scan, this
session), and every one of them landed (F21). The one halt retail did NOT swing after is
§40.2's mid-chase halt: the copy arriving at a stale point behind a straight runner, re-
followed 0.23 s later — the arrival found nobody in reach.

**Shipped** (`SWING_OWED_AT_HALT`, `SWING_OWED_WINDOW = 0.5` s, `--no-owed-swing` reverts): the
arrival records whether the player's frame was inside `enemy_reach()` at that instant (both
arrival sites, `in_reach_at_arrival`); a halt with that flag stamps `swing_owed_at`; the
enemy loop opens the swing on the tick after the halt **without re-testing the live
distance** for the window (retail's halt→swing maximum 0.379 s, rounded up), consumes the
debt at the START, and lets it expire otherwise; the follow tick starts no new chase while
a swing is owed, so the catch is not spent on a 20 u leg that would block it under the
mid-follow rule. A halt whose arrival found the player out of reach owes nothing and
re-follows as before. The landing is F21's: it lands wherever the runner went.
`test_agentlife` §11b (floor 398 → 406): the stamp, the swing on a runner 330 u away with
no re-test, the follow hold and its expiry, the expired debt, the out-of-reach halt owing
nothing, and the revert arm.

**What this leaves.** The halt clock itself (0–0.5 s) still stands between the catch and the
swing, as it does on retail; a runner who keeps a straight line at equal speed is never
caught on either server (§40.2's mid-chase halt). What changes is the turn, the stop and the
pass-by: every catch now costs one swing that lands. **Unobserved on a client.** Refuted if
the owner's kiter is still never swung at after a catch, or if a swing opens on a body that
was never in reach (the debt stamped on a stale-point halt).

## SLICE-F23 — **two bugs off the C4 run: the degeneration clock froze across quiet ticks (the "instant kill"), and a corpse walked on its own lead chain**

**The owner** (harness `20260912T205237`): *"enemy swings when it catches me now. Weird bugs
though. I think one of his skills, maybe Sever Artery, kills me instantly. I slid around
after dying too."* Both are in the log, and neither is Sever Artery's damage.

**The instant kill is the degeneration clock.** Sever Artery inflicts Bleeding (3 pips,
−6 health/s). `degen_tick` stamped its clock (`degen_at`) only *below* the early return for
"no live effects", so the stamp froze at the last tick of the PREVIOUS Bleeding — across the
death that stripped it and the minutes of quiet after — and the next Bleeding's first tick
charged 3 × 2 × that whole gap. Log 856–865: Bleeding applied at 90/100, `KILL the player
(bled out)` nine lines later with no damage between; 599–693 the same from 55/100. The
clock is stamped on every tick now, live effects or not, so a quiet gap never reaches `dt`.
`test_effects` §4f: a 300 s quiet gap followed by a Bleeding costs nothing on its first tick.

**The slide is our own lead chain.** Right after the KILL: `KBD LEAD RE-GRANT 1 … the copy
arriving at the lead's end, the client silent` — the keyboard-lead chain re-granting the leg
the held key had armed, to a corpse; the client sent nothing. `kill_player` now drops every
order this server could re-issue (the keyboard leg, the integrator's dest, the follow, the
router chain — the movement latches stay with the arms whose writer counts are locked), the
four grant ticks in `handle()` are gated on `player_dead`, and a dead player's movement
report is refused ahead of both movement arms (`refuse_move_while_dead`, printed once per
death, the counter reset at revive). No send: the KILL status is what the client acts on.
`test_effects` §6a. Both unobserved on a client until the next pass; the run question is the
obvious pair — *does Bleeding tick you down at 6 a second now, and does the corpse stay put?*

## SLICE-F24 — **an NPC's attack skill is a swing (the "Power Attack did bleeding" burst), and the corpse is held**

**The owner** (harness `20260912T210558`): *"Power Attack did bleeding which was weird, I think
it ticked normally? I took a bunch of damage on his initial hits and idk why. My corpse didn't
slide, but it did warp slightly."* The bleed ticked normally (C5 held). The rest is two
things.

**The burst.** Log 620–635: Sever Artery announced and its Bleeding applied in the same
instant; Power Attack announced and its 34 landed in the same instant; the two casts ten lines
apart. The raider's bar gives both attack skills a 0.0 activation, `cast_lands_at = now + 0.0`
landed each on the next tick, the round robin picked the other ready skill on the tick after,
and both were announced as spells (`[60]`) and closed as spells (`[58]`). So Sever Artery's
bleed and Power Attack's 34 arrived as one blow, which is what the owner saw and felt.

**Retail's NPC attack skill is a swing** — 177 activations on the live corpus (`c6_npcskill`
scan): announced `[50, npc, target, skill]` every time; the close `[46]` a windup later, p50
**0.564 s** (`swing_windup(1.33)` = 0.565); the next start p50 **1.5 s** after, the weapon's
interval; two `[50]`s by one NPC inside 1 s **once in 177**. Shipped
(`NPC_ATTACK_SKILL_SWINGS`, `--npc-skill-instant` reverts): an attack skill is picked only when
the swing clock is ready, announced with 50, lands `swing_windup(interval)` later (a listed
activation wins, the player's rule) as `[46]` + the weapon hit + its "+ damage" bonus added
after armour (`land_swing(bonus=, skill_id=)`, hit_enemy's order for the player's), then its
effect, condition, visual and heal resolve as for any cast; the chain waits its interval.
Spells keep their table activation, 60 and 58. `test_agentlife` §11c (floor 406 → 412): the
50, the windup, the 46 with weapon damage, the second ready attack skill waiting for the
interval, Power Attack's +30 on top of the weapon hit, and the revert arm's burst.

**The corpse is held.** Retail's death batch for the observing player, 2 of 2
(`20260817T183756` t=353.299, `20260821T152147` t=550.319): `STATUS [me, 16]`, then
**`[8, me, 1]`**, then the 41/42 maxima, `0x002D [me]` and `0x0026 [me, 4]`; no `0x0028`, no
`0x002C`. Property 8 is the client's walk gate (ANIMREF §28), so a retail corpse cannot take a
step; ours sent no hold, and the owner's corpse warped slightly as its copies converged.
`kill_player` sets the hold behind the STATUS now (`test_effects` §6a). `0x002D` (unnamed in
the catalog) and the flags value 4 (ours sends 8, the four NPC deaths') are recorded, not sent
— the next reader with a corpse to explain starts there. Both unobserved on a client. The run
questions: *does a raider's Sever Artery land as one hit with the bleed behind it and Power
Attack a swing later, and does the corpse stay exactly where it fell?*

## SLICE-F25 — **a cast in flight lands too; the death cancels the sync copy's walk (0x002D), and the server's mirror of it stops with it**

**The owner** (after C6): *"corpse still warping. Sometimes the enemy Power Attack or Sever
Artery shows up on his skill monitor but doesn't actually hit me. Could be when I'm moving.
He missed the very first Sever Artery and missed some Power Attacks and Sever Artery casts
throughout the session."* And the hint: *"when I respawned after warping, the enemy was able to
hit me from far away — points to a server/client mismatch."* Three findings, one mechanism
each.

**The announced-but-missing strikes.** F21 hoisted the armed SWING above the enemy loop's
reach gate and left `cast_lands_at` below it. Since C6 an attack skill is a cast with a
windup, and since C4 the halt owes a swing that is often that skill — so the raider announced
Sever Artery at the halt, the runner left 92 u during the windup, and the gate dropped the
cast on the next tick: the skill monitor showed it, nothing landed. *"Could be when I'm
moving"* is exactly right. Retail: attack-skill strikes on a moving target 37 hit / 3 stopped
(NPC on NPC, `latehitjoin`), and **spell casts at a moving observer complete 9 of 9** with
no 59 (`c7_spell` scan) — a cast is announced in reach and lands where its windup ends.
Shipped: the cast landing sits beside the swing landing above the gate (`LATE_HIT`; the
revert arm drops it). `test_agentlife` §11c and its cast section (floor 412 → 414).

**The corpse's copy.** F24's hold gates the client's input, but the client's sync copy was
already walking our last lead when the body died, and the rendered corpse converged onto it
as it arrived — the warp. Retail's death batch carries **`0x002D [me]`** behind the hold, 3 of
3 (§F24's two plus studies/morale §1's t=78.813). ldufr calls it `AGENT_PLAYER_DIE`;
studies/enemy PLAN §6h read the handler and refuted the name: behind a flags test (bit
`0x20000`, set on a moving agent) it zeroes a float pair at `+0xC8/+0xCC` and clears `+0x4C`
— a velocity — and §6i's `moving_die` probe saw a running character stop when it landed. It
sits in the movement family's recv table beside `0x0028`, on the arm the client-controlled
gate reduces to the SYNC copy once the player has moved locally (studies/movement 2436). So
it is the message that stops the corpse's copy where the body fell, and `kill_player` sends
it now (`GAME_SMSG_AGENT_MOVE_CANCEL = 0x002D`, catalog `GAME_SMSG_0045`, one agent field).
`test_effects` §6a.

**The mirror.** The owner's hint. `_npc_frame` judges a hostile's reach against the server's
model of the client's sync copy while the player moves — and only one site ever stopped
that model, the `0x002C` hard-set (`_note_wire_move`): `0x0028` and `0x002D` name no point
and fell through its point check, so after a death the model walked on to the last lead's
end, up to 520 u past the corpse, and the raider's reach was judged there through the
respawn. `_note_wire_move` now stops the model where it stands on either message. The
death batch and the mirror stop are one fix from the two sides of the wire. `test_effects`
§6a (floor 81 → 83) drives the hook with the 0x002D kill_player sends.

Also re-aimed: `test_kbdsync` §11's lead-kill caller count (the approach and the interact-walk
each added a caller; four callers, one rule). All unobserved on a client; the run questions are
the same three sentences: *does every announced strike land, does the corpse stay put, and
does the raider reach you only where you are after a respawn?*

## SLICE-F26 — **the corpse walked our lead to its end: the death kills the lead in flight**

**The owner**, after C7: *"still warped on death, he still attacked me from out of normal
range. The strikes do hit while moving now though."* The strikes are C7's, confirmed. The other
two are one fact, and this time the wire says it to the unit (capture
`authsrv-20260912T223203-c4`, the run's corridor connection, one death):

| instant | what |
|---|---|
| −0.102 s | we granted `KBD LEAD (1732,1133) from (1347,1483)` — a 520 u keyboard lead |
| −0.100 s | the last report before the death: **(1347.1, 1482.6)** |
| 0 | `KILL`, the hold, `0x002D` |
| revive +1.63 s | the first report after the revive: **(1731.8, 1132.7)** — the lead's END, to the unit, **520 u** from where the body fell |
| revive +0.00 s | our raider sent to the death spot: `FOLLOW: agent 90 -> player at (1368,1463)` |
| revive +1.02 s | `agent 90 halts at (1368,1463): parked, 0 u from the player` — a phantom; the body stood 520 u away |

So the client walked our outstanding lead out after the death and its body ended at the
lead's end — that is the warp — and F25's `0x002D` did nothing to our client's copy (its
velocity cancel is gated on a flags bit our player agent evidently does not carry: studies/
enemy PLAN §6h's null, seen a fourth time; §6i's *"appeared to stop"* was the operator's own
hedge). The server, meanwhile, held the body at the death spot (F25's mirror stop did its
job), sent the raider there, and had it halt and swing on nobody while the real body stood
520 u off: *"attacked from out of normal range"* from the client's side of the same fact.

**Shipped.** `kill_player` ends the lead in flight the way a press ends one (MOVECODE-1z-y,
`_kbd_lead_kill`, its fifth caller): a zero-lead `0x0029` at the modelled body — ~30 u past the
last report at the instant of death — so the client's copy parks where the corpse is, the
server's beliefs already agree, and the revive stands the body up where it fell. The `0x002D`
stays in the batch (retail's, measured) and is now known inert on our client. Retail never
leaves this lead shape outstanding, so the repair is ours and says so. `test_effects` §6a
(floor 83 → 84): the corpse fixture carries a real half-second-old lead, the death sends
exactly one movement message, and its point is the modelled body (~144 u along the lead),
not the lead's end and not the last report; `test_kbdsync` §11 counts five kill callers.

**Refuted if** the first report after a revive still sits at the last lead's end, or the
raider still halts "0 u from the player" on a spot the body is not at.

## SLICE-F27 — **the arrival itself owes the swing: the circling kiter, and two measurements that said no to my first two ideas**

**The owner** (after C8): *"corpse stays put now. Attacks are still kiteable though, I'm able to
run around him in circles and he never quite stops to attack."* Harness `20260912T224429`:
**34 halts, 103 follows, 6 swings**; the halts read *"arrived 0.41–0.51 s ago, 106–215 u from
the player"*. F22's owed swing required the LIVE distance at the arrival to be inside 92 u,
and a circler never is at the instant the copy parks at the point it had been chasing.

**Two things the tapes refused first.** (1) *Raise the hostile's start reach to 144.* The
parked retail hostile of `20260817T183756` (agent 37) chained swings at a STANDING player from
an estimated **87 u** (its last follow point pulled 80 u back along its approach, to the
player's stop report; `c9_reach`), and opened on a moving player at ~11 u — 92 stands, 144 is
not supported. (2) *Judge the arrival on the last report instead of the frame.* Retail's copy
lags (§40.2), but the lag is not the mechanism.

**What the tapes said instead** (`c9_halt`): of the **6** hostile halts that ended a chase on
the observer, **5 were followed by a swing within 0.8 s** and 1 by a re-follow — and the one
halt at which the player was still moving (t=330.686) swung. Retail's server halts when ITS
copy of the hostile parks at the disc of ITS copy of the player, so at a retail halt the
target is in reach **by construction**, and the swing follows; F21 lands it wherever the body
went. So the arrival is what owes the swing, not a re-test: both arrival sites set
`in_reach_at_arrival` on any park (disc or leg end). The flag stays a flag for the day a
stale-point rule is measured (the re-follow, 1 of 6). `test_agentlife` §11b (floor 414 →
417): a follow sent at the player, the player 300 u off by the park, the park owes, the halt
stamps, the circler is swung at on the next tick. **OBSERVED on the owner's next run: *"he
stops and swings when I circle now."*** Refuted if the raider swings at halts where the body was never
near — the 1-of-6 case, which would then be worth its own scan.

**Where the combat thread stands, 2026-09-12.** Every item from the owner's first combat report
(F19) through this one is done and observed on the client: the attack skill walks in, roots,
halts a running press and frees a held key at the strike; a hostile that catches you swings
and the swing lands wherever you went; its attack skills are swings with a windup; bleeding
ticks at its rate; the corpse stays where it fell and the raider comes to where you are. Open,
all recorded rather than guessed: the halt-slot residual (F20), the 1-of-6 re-follow (here),
the in-reach press engaging the chain (F20, n=1), and 0x002D's flags gate on our player agent
(F26).

## SLICE-F28 — **the party body's contract, read off retail's own henchmen: the formation, the engagement rule, who the hostiles hit, and what a monk casts**

OBSERVED, 2026-09-12, `toolkit/authsrv/henchjoin.py` over the live corpus. **The owner asked whether
a live capture of a hero was needed and offered to set one up.** The answer the corpus gave first:
`studies/heroes/FINDINGS.md` §0's *"zero live occurrences of the party-add family in 22,524
messages"* was true on 2026-08-12 and is not true now — two later captures carry `0x01BF`
PARTY_HENCHMAN_ADD three times each, **20260817T231139** (three level-20 henchmen, map 167730,
four connections with the bodies created) and **20260819T132414** (three level-3 henchmen, map
157087, one connection with bodies; two more with roster rows only). GWW (*Henchman*, See also)
says heroes and henchmen share one AI, so the party body's behaviour is observable today, on
eleven bodies across five connections, and the hero was authored blind for no reason but that
nobody had re-run the count. (`0x01BF`'s two trailing bytes, "purpose NOT FOUND" in heroes §10.2,
are **profession and level**: the body with byte 3 cast Orison of Healing, Word of Healing, Heal
Other, Healing Breeze and Resurrection Signet; byte 1 used Hamstring, Power Attack, Griffon's
Sweep and Galrath Slash; byte 6 cast Incendiary Bonds, Mind Burn, Fireball and Fire Storm — Monk,
Warrior, Elementalist by the profession enum, at level 20; the second capture's bytes read 2/1/7 at
level 3. Names resolved through the owner's archive, `textrec.py`, for these eighteen ids only.)

**The formation.** A party body walks by **`0x0029` point leads, never by a `0x002A` naming the
leader** — 750 of 750 leads while the observer moved — **one every 0.51 s (p50; p10 0.28, p90
1.49)**, and **no `0x0028` closes the walk** (2–11 halts against 46–192 leads per body; the halts
sit in fights). The lead's END against the observer's latest report: observer moving, **126 u
p50** (p10 69, p90 299); observer standing, **100 u p50** (p10 44, p90 141), **along 0 and
|across| 99 u p50** — the bodies stand ABEAM of the leader; at the observer's stop the last lead
within 3 s ended **141 u p50** from the stop point. Per body the moving medians spread over
along −73…+66 and across −62…+97: no body held one bearing, so the slot TABLE is ours
(RECONSTRUCTION); the radius and the shape are the tape's. Our `HERO_FOLLOW_STOP = 200` was
"a number chosen to look right" and was ~60% too far; the follow was the hostile's `0x002A`
parked by a halt, a shape retail never sends for a party body.

**The engagement rule.** Of 89 opening starts by a party body (no start by it in the previous
3 s): **72 followed the observer's own start or skill press inside 6 s, 58 of those on the
observer's own target**; 5 followed a hostile's start on the party; 12 had neither inside 6 s
(fights the party opened, or ones opened by a hostile's cast, which the join does not count).
So a party body fights when the leader fights, on the leader's target by preference, and also
when hit — GWW's *Hero behavior* in numbers.

**Who the hostiles hit.** Hostile starts named a **henchman 162 times, the observer 13, and
another body 26** — the party bodies walk in front and take the aggro. Ours never look at the
party at all (`enemy_attack_tick` swings at the player only); that is SLICE-H3.

**What a monk casts, and at whom.** The level-20 Monk cast Orison (281), Word of Healing (282),
Heal Other (286) and Healing Breeze (288) at HENCHMEN 12 times and at the observer once —
never at itself (the target byte, SLICE-B3) — with damage on the target inside the previous 5 s
in 8 of 13; it also **auto-attacked** (32 `[4, monk, T]` starts in the long connection: a monk
with a weapon swings between casts). The Warrior used attack skills (kind 50), the Elementalist
spells (kind 60), all at hostiles. **Deaths and resurrection:** the Monk died **5 times** in one
connection (rising edges of the `0x00F1` dead bit) and was raised each time by a party member's
**Resurrection Signet (skill 2, kind 60, 3.0 s to `[id, 0]`)**; the OBSERVER was raised by a
henchman twice (t=651.5, 660.8). A party wipe is not what ends a retail fight; a signet is.

**What this settles for the hero arc (`PLAN.md` §7, SLICE-H1…H6).** The formation and the
follow shape ship now (H2). The engagement rule, hostile targeting, party damage, death and the
signet are the next three rungs, each with its number above to be measured against. **Whether a
hero-specific live capture is still worth taking:** yes, but for different things than the
behaviour — retail's hero pipeline order (`0x0074`/`0x0072`/`0x01C2`, which we author ourselves;
retail sends `0x0072` zero times in the corpus), the hero's skill-bar delivery on the wire (heroes
§4, NOT FOUND), and the commander echoes on retail (`0x0062`/`0x0063`/`0x0066` after a stance
click, a lock, a flag in an explorable). None of those blocks the arc; all would be one short
session on an account that owns a hero, with a marks plan that adds the hero in an outpost,
zones, fights, flags it, sets each stance and locks a target.

**OBSERVED on the owner's run, 2026-09-13 (SLICE-H2):** *"tahlkora shows up and walks beside me
now."* The full rig — body, bar, activation, char table, bags, appearance pair, pipeline-first —
composed on a client for the first time with no assert. **And one stock rule the tapes could not
give, because every henchman session was already in a field:** *"in the outpost she (i.e. her
model) should be hidden. only show in explorable areas."* SLICE-H2b: a town sends the roster row,
the activation, the level and the vitals and withholds the `0x0020` (the panel opens bodiless,
pvpui §28.3); a field creates the body. `party_bodies_here` is the same switch the `0x0199`
is_explorable byte is built from; `--party-body-in-outpost` is every hero rig before it.
Residual, cosmetic: a bodiless roster row has no profession segment ("Lvl 5 Tahlkora" rather than
"Mo5 Tahlkora", heroes §28.8's rule that the row reads the AGENT) — whether `0x00A6` can carry
the bytes for an agent never created is UNTESTED.

**SLICE-H2c, the same day: the owner** — *"she's hidden in the outpost now. stock does show the
profession in outposts though."* Read out of the client rather than guessed (codescan `--dis`
/ `--xrefs`, build 38797): the roster label builder `0x538e40` takes the level from `0x7df7c0`
and the profession pair from `0x7df810`, and **each has two arms** — through the AvChar
(`0x802160`, the agent view: level at `+0x110`, pair at `+0x10e/+0x10f`) when the agent has a
body, else through a **per-agent SUMMARY record** (`[0xbf95f8][agent_id]`, a `0x34`-byte
AvChar.cpp object: `+2/+3` the pair, `+4` the level, `0xff` when absent — the "Lvl 255"
sentinel, closed). **And `0x00A6`'s handler `0x7dffc0` has the same two arms**: the view's
setter `0x7f7330` when a view exists, else `0x7f73a0(agent, primary, secondary)` into the
summary record (its only caller). So the town simply sends the pair for the bodiless hero agent,
ahead of its level (retail's order, `0x00A6 → 0x009F` 130 of 130), and the row reads **"Mo5
Tahlkora"** — OBSERVED, harness `20260913T094444`, the party window that is always open in an
outpost. The rival — `0x0074`'s three leading bytes as level/primary/secondary (upstream's
guess, `--hero-bytes 5,3,0`) — was run first and **refuted**: "Lvl 5 Tahlkora", harness
`20260913T093649`.

**A residual the runs found, and it is not H2c's.** Pressing **P** in an outpost opens Party
Search, and its Heroes tab asserts `heroFrame` (`PtSearchHeroList.cpp:160`, a child-frame lookup
by id in `0x6176c0` returning NULL) the moment a party hero row carries a profession — bodiless
with the pair sent (`094444`) AND with the body standing in town (`094740`, the
`--party-body-in-outpost` arm), while the profession-less row of `093649` opened it cleanly. So
the tab wants something about the account's heroes that our rig never sends (the list it marks
the party's heroes in — NOT FOUND), and any professioned party hero trips it; H2c only made the
hero look like one. The owner's note: *"you don't need to press it in outposts — the Party
Window is always open there."* Recorded as SLICE-H2d, not fixed.


## SLICE-F29 — **hostiles fight the party: retail picks the softest class alive, and the signet is what ends a death**

OBSERVED, 2026-09-13, `henchjoin.py --hostile` over the henchman connections (F28's tapes).
**58 opening starts** by a hostile on a party — the first start by that hostile in 3 s — against
the live party's positions (sample-and-held from creates, leads, destinations and 0x002C; the
observer from its own reports) and the profession of each body (`0x01BF`'s byte, `0x00A6` for the
observer):

| rule | fits |
|---|---|
| the NEAREST live party body | 26 of 58 (and the miss is not small: 231 u p50 further) |
| the last party body to HIT the hostile (10 s) | 11 of 58 |
| either of those | 33 of 58 |
| **the LOWEST BASE-ARMOUR class alive** (GWW's per-profession table: Warrior 80, Ranger 70, casters 60) | **51 of 58** |
| …and the NEAREST within that class | **41 of 58** |

The seven misses are all the observer, a Warrior, at rank 1–2 by distance. The Monk was chosen
at 380–500 u over a Warrior at 64–185 u; when the Monk was down the Elementalist was next; the
Warrior henchman was picked only when no caster stood. Inside a bout the hostile switched
target 12 times in 58 (6 to the nearest, 3 to its last hitter) — **unmodelled**, the pick is kept
while it lives. The rule as shipped is a RECONSTRUCTION fitted to those 58 and says so at
`HOSTILE_TARGETS_PARTY`; the class table is WIKI (*Armor rating*).

**And the client's target byte 6 is "dead ally":** all 11 skills carrying it on build 38797 are
resurrections (Resurrection Signet 2, Resurrect, Rebirth, Restore Life, Vengeance, Flesh of My
Flesh, Resurrection Chant, Renew Life, Death Pact Signet, Signet of Return, Sunspear Rebirth
Signet — names through the owner's archive), `effects.DEAD_ALLY_TARGET`.

**What shipped (SLICE-H3).** Every hostile keeps a `target` — the softest class inside
`AGGRO_RANGE`, nearest within it, kept while it lives, re-picked at its death
(`hostile_target`) — and the whole fight is aimed at it: the chase (`_npc_follow_tick` takes a
`target_id`; the 0x002A names it; the frame it parks against is the body's own position), the
swing (`start_swing` names it, `land_swing` lands on it through `land_swing_on_body` — the same
ENEMY_HIT_FRACTION at the body's own armour, the skill bonus after armour, retail's
[finished, damage] order, property 16 `[16, body, hostile, fraction]`), the cast (`land_skill`'s
damage, effect and condition sites take the cast target), the facing. A party body dies through
`kill_agent` with **no kill reward** (nobody is paid for a party death) and **`revive_due` leaves
it down**: retail's henchman was raised by Resurrection Signet five times in one fight and never
by a timer (F28). The signet is a `skill_effect` row (`scale_means = "Resurrect"`), the monk hero
carries it (`[party.slice]` bar 281/276/2), `ally_cast_tick` casts it at a dead ally **ahead of
any heal** and holds the slot when nobody is dead, and `land_skill` raises the body ([finish],
`[id, 0]`, full health) or the player (`revive_player`, the timer revive's body, callable now).
A dead player no longer stops the hostiles: the fight goes on against the party. Revert:
`--hostile-target-player`. `test_agentlife` §H3 (floor 428 → 442).

**Run on the harness the same day** (`20260913T102921`, the owner aggroed the first raider
by hand): the raider fought the player, re-picked the Monk hero the moment the player died, the
hero cast Orison seven times at the player and the signet at the corpse, took 56 (Power Attack),
22 and 22 on her 100 health and died. **And the first pick was wrong by the rule's own letter:**
the raider noticed the player 600 u out while the hero still stood past `AGGRO_RANGE`, chose the
only candidate, and kept it. Retail's rule is read off OPENING starts, so the pick is now
PROVISIONAL until the bout opens — re-made each tick as bodies come into range — and LOCKED from
the first swing or cast while the target lives (`target_locked`). The owner's note on the same
run, not H3's but the slice's: *"it's too strong to kill since healing signet is so powerful and
i have no actual skills other than power attack that do anything"* — content balance, the
raider's Healing Signet against a level-1 bar; a knob, not a mechanism.

**Not modelled, said here:** the in-bout switch (12 of 58); the signet's 25% energy and its
morale-only recharge (the client table's 0 recharge is what runs, so it is ready every fight);
a hostile's spell at a party body gets no armour term but the body's flat rating.

## SLICE-F30 — **the party fights: it opens on the leader's target half a second after the leader, a caster from where it stands, a melee body by a chase, and lands 4% of the foe a swing**

OBSERVED, 2026-09-13, `henchjoin.py --fight` over the seven henchman connections (F28's tapes),
**89 opening starts by a party body** (no start by it in the previous 3 s):

| what | number |
|---|---|
| a start or press by the observer ON THE SAME TARGET inside 6 s before it | **77 of 89** — p10/p50/p90 **0.09 / 0.50 / 1.55 s** behind it |
| T was the observer's `0x00C1` selection at that instant | **80 of 89** |
| the body's last movement order before it: a `0x0029` point lead / a `0x002A` naming T | 62 / 25 (the Warrior: 9 / **17 of 27**; the Assassin 7 of 7; the Monk 17 / 0; the Elementalist 31 / 0) |
| distance body → T at the start (sample-and-held): Warrior plain swing / attack skill | 134 / 100 u p50 |
| Monk plain swing | **378 u p50** (p10 146, p90 761, max ~1237) |
| Elementalist plain swing | 547 u p50 (p90 1212) |
| plain-swing cadence, one body: Warrior / Monk / Elementalist | 1.48 / **1.91** / 1.89 s p50 (sword-axe 1.33, staff-wand 1.75 by the client's rates) |
| damage fraction of T's MAXIMUM per plain swing (the `0x00A3` dword is the f32 bits): level-20 Monk | **0.038 p50** (p10 0.022, p90 0.049, n=35) |
| level-20 Warrior / Elementalist; level-3 Warrior / Ranger / Assassin | 0.043 / 0.039; 0.043 / 0.125 / 0.043 |
| the bout ended in T's death (0x00F1 dead bit inside 6 s of the body's last start) | **60 of 89** |

So a party body fights when the leader fights, on the leader's target, half a second later; a
**melee** body walks to its foe by a `0x002A` naming it — the hostile's own chase shape — and opens
at melee reach; a **caster** swings from wherever the formation put it, and the Monk's 378 u p50
sits inside GWW's casting range, **1248 u**, which *"is also the range of all caster weapons (i.e.
staffs and wands)"* (WIKI, GWW *Range*, raw wikitext read 2026-09-13; melee/touch 144). The Monk
cast heals between swings (F28). Where a body's damage comes from is not on the wire — its weapon
is never sent — so the *fraction* is what is measured, and it is the number this server sends.

**What shipped (SLICE-H4).** `leader_engaged` is stamped at the player's swing start
(`attack_tick`), at `hit_enemy`'s one-instant swing and at an accepted skill press aimed at a live
hostile; `party_fight_target` picks (1) the leader's target while the stamp is inside
`PARTY_ENGAGE_WINDOW` = 6 s and it lives, (2) else the body's current foe while it lives and the
leader's last engagement is still on it or it has opened on the party, (3) else the nearest hostile
whose H3 pick is LOCKED on a party member (retail's 5 of 89 "party-hit-first"), (4) else nobody —
retail's 12 unexplained opens are not modelled. `ally_attack_tick` (after `ally_cast_tick`; a cast
in flight beats it) opens `[4, body, foe, 0]` and lands a windup later through `land_swing` →
`land_swing_on_body` with **`PARTY_HIT_FRACTION` = 0.038** of the foe's maximum at the foe's own
armour, retail's [finished, damage] order, blind misses as everyone else's; a caster swings from
`PARTY_RANGED_REACH` = 1248 (its slot walk arrived), a melee body (`PARTY_MELEE_PROFESSIONS`
Warrior/Assassin/Dervish) is handed to `_npc_follow_tick` as a chase — a `0x002A` naming the foe,
the hostile's radii and leash — and swings parked at `enemy_reach()`. `hurt_agent_row` (H3's
`hurt_party_body`, generalised) pays the kill reward when the row is hostile and never writes a
hostile's `last_hit` (the player's own swing timer). `ally_cast_tick` casts a **foe** skill (target
byte 5) at the fight target inside casting range and holds the slot otherwise, so Banish on a
party bar goes at the foe and never at an ally; a party attack skill waits for the swing clock
(F24). The body swings at its own weapon's interval — `[party.slice].weapon = "staff"` / `--hero-weapon`,
else `PARTY_WEAPON_BY_PROFESSION` — so Tahlkora swings every 1.75 s. Revert: `--party-no-fight`.
`test_agentlife` §H4 (floor 442 → 457).

**Run on the harness the same day** (`20260913T113735`, `--walk "attack:90"`, the server approach
walking the player 3,073 u up the corridor with the hero in its slot): the raider re-picked the Monk
hero at 1,171 u (H3's softest-class rule, provisional until its first start); the player's swing
opened at 80 u and **the hero fought the raider on the SAME tick** (`fights agent 90 (the leader's
target)`), opened its swing **105 u out**, turning first, and landed **14 on the raider** (200 × 0.038
× the armour term at its rating) — then took 22 (the raider), 49 (the corridor monk's Banish), 22 and
22 and died with a second swing armed, which the corpse dropped; both hostiles re-picked the player,
who died three times in the hold. Retail's shape, the slice's balance (H3's owner's note stands:
the raider's Healing Signet against a level-1 bar, and now a 100-health hero under two hostiles).

**Not modelled, said here:** the 0.5 s p50 the body lags the leader (ours opens on the same tick in
reach); the in-bout retarget; retail's 12 party-first opens; a caster's walk toward a foe beyond
casting range (it stays in formation until the leader closes); the Ranger/Paragon projectile
reaches (one and zero opening swings in the corpus); and **a party caster never heals ITSELF** —
`ally_heal_target` excludes the caster (SLICE-B7c), retail's Monk cast at itself 0 times in 13
(F28), so the hero at 78/100 cast nothing — the same sample says "never" on thirteen casts, which is
a weak never.

## SLICE-F31 — **the commander's orders: stance, lock and flag, echoed since pvpui 28 and obeyed since today**

WIKI, 2026-09-13 (GWW *Hero* §Combat modes, *Hero behavior* §Targeting, *Hero flag*, raw wikitext
read through the browser), because **the live corpus carries no retail commander click at all** —
0 of 61 connections send `0x0015`/`0x0016`/`0x001A`/`0x001B` or receive `0x0062`/`0x0063`/`0x0066`;
the one thing it does carry is **`0x0067` PARTY_FLAG_SET's CLEAR form `[(+inf, +inf), 0]` in the
instance-load batch beside `0x0103`, 3 of 3 connections that carry a `0x0103` at all** (OBSERVED;
none of the three has a party). The wire shapes are pvpui 28.5–28.7's, captured on our own client.

| order | what the wiki says the hero does |
|---|---|
| **Fight** (aiMode 0) | attacks, in priority: called targets, the SELECTED target within spirit range of the hero, foes actively engaged with the party, foes within the hero's aggro range; prefers the lowest armour rating; "will separate from the flag or the controlling player, if necessary" |
| **Guard** (1) | guards the area near the flag or the player, "refraining from combat until actively engaged": the selected foe engaging the party, a foe entering the party's aggro circle; "will not move beyond the guarded area" |
| **Avoid Combat** (2) | "Heroes never attack", not a selected or called target either; kites when attacked |
| **Lock** | "lock your hero unto it until the target gets killed" — the top of the targeting hierarchy (1. locked, 2. called, 3. attacked — F30's rule is the third) |
| **Flag** | the hero moves to the flag "and stay[s] there as long as the flag is active"; the party flag moves "all heroes and henchmen as a single group"; removing a flag sends them "back to the player" |

**What shipped (SLICE-H5).** The four dispatch arms became one `handle_hero_command`: the echo
first, unchanged (the client draws from it, pvpui 28.6), then the order into `hero_command(state,
agent)` — `{ai_mode, lock, flag}` kept on `state` because the body row does not exist in a town —
and `state["party_flag"]`; a flag whose coordinates are `(+inf, +inf)` is the clear (the s2c clear
idiom, applied to the c2s: no retail c2s clear was ever captured). `party_fight_target` reads the
stance and the lock: **Avoid** picks nobody; the **lock** tops the hierarchy while it lives (a dead
lock falls through, "until the target gets killed"); **Guard** keeps only "a hostile that opened on
the party" (and the current foe while it does); **Fight** keeps H4's leader rule and adds the
leader's `0x00C1` selection within `SPIRIT_RANGE` = 2512 and, last, any live hostile inside the
hero's own `AGGRO_RANGE`, lowest armour class first — which makes a Fight-mode hero open on a foe
the moment it comes within 1200 u, as the wiki says and as F30's 12 leader-less retail opens allow.
`enemy_move_tick`'s party branch walks a flagged body to its flag (`party_flag_point`: its own
flag, else the party flag at its slot offset about the flag, "as a single group") by the slot
walk's own `0x0029` shape and holds it there; under Fight the melee chase still separates it from
the flag, under Guard a melee body does not chase. `--party-ignore-commands` reverts (echoes only,
every run before today). `test_agentlife` §H5 (floor 457 → 467); four H4 checks moved their idle
foe out to 1500 u because Fight now attacks on sight.

**Not modelled, said here:** "called" targets (Ctrl-click; no c2s for it is known here); Avoid's
kiting; Guard's "guarded area" as a radius (a Guard body simply does not chase); the flag as a
pathed destination (the lead is the straight point, the corridor legs the follow's own); Fight's
"lowest health under 50%" tie-break; `0x0017` (not the unlock, pvpui 28.11).

## SLICE-F32 — **the hero across the loop: three instances on one process, the roster in the town, the body in the field, the roster again**

**PRE-REGISTERED 2026-09-13, before the run.** `--map 148 --party slice --area errand,corridor`,
walk `wait:6 S:2 wait:24 E:2.8 wait:10 shot:1 wait:30`: S backs the outpost's character (it faces
east) west into `[portal.ascalon_to_corridor]`; in the corridor the character also faces east, so
E strafes it SOUTH into `[portal.corridor_to_ascalon]` 736 u behind the arrival point. Prediction:
c1 (148, a town) sends the roster with the profession pair and no body; the portal fires;
c2 (168, RE-ENTRY) creates the hero body, which walks to its slot behind the strafing leader; the
return portal fires; c3 (148, a second RE-ENTRY) sends the roster again with no body, and the
party window reads "Mo5 Tahlkora" in the outpost. Refuted if c3 never comes (the SECOND transfer
of a session is the one whose dial defers, SLICE-G3's trap), if c3 creates a body in the town, or
if the roster row loses its profession on the third instance.

**RESULT — OBSERVED, harness `20260913T123255`, every prediction met.** c1: `AGENT_SET_PROFESSION(hero
agent 200, 3)`, the level and vitals, "the hero bodies are withheld", `HERO_ACTIVATE`,
`PARTY_HERO_ADD`; `PORTAL 'ascalon_to_corridor'` at 129 u in → `TRANSFER to map 168`, the graceful
close. c2: RE-ENTRY, `created agent 200 (Academy Monk) — hero body`, the activation and the party
add again, six slot walks trailing the leader south (`walks to its slot (1646,1309)` … `(1647,946)`),
`PORTAL 'corridor_to_ascalon'` at 136 u in → `TRANSFER to map 148`. c3: RE-ENTRY with `--map 148`
standing down, the same town sequence as c1 line for line (profession pair, level, vitals,
withheld, activation, party build, `PARTY_SET_MINE`), and the frame after the strafe shows the
outpost with **"Party Formation (2/4) — W1 Test Warrior, Mo5 Tahlkora"**, Fisk's marker up. The
tail of c3 is the perf-counter reply (`0x8009`, GrPerf) until the harness closed the window: no
assert, no `Code=058`. **The hero's orders do not survive a zone**, by construction — `state` is
rebuilt per connection, so a flag, a lock and a stance are the instance's — and that matches the
one retail trace the corpus has: **`0x0067` PARTY_FLAG_SET's clear form `[(+inf,+inf), 0]` in the
load batch beside `0x0103`, 3 of 3 connections that carry a `0x0103`** (F31). Not shipped: we send
no `0x0103`, so the batch has no anchor here, and whether the client keeps a compass flag across a
zone without the clear is untested.

**What this closes and what it leaves.** SLICE-H6's mechanism half: the party rig is per
instance (`_handle_request_players` re-runs it on every load, town and field alike), and three
instances on one process carried it through both portals with the client re-dialling twice.
**The owner's own pass — outpost roster, zone, the corridor fight beside Tahlkora, the return —
is still the owner's** (this run fought nothing; H4's run fought and did not zone). The
hero-specific live capture (F28's last paragraph) stays optional.

## SLICE-F33 — **what a party body holds: retail's henchman gets an item and a 0x006D at its create, and the punch was an empty hand**

**The owner, after H4's run (2026-09-13):** *"Tahlkora attacks, but from long range with a melee
punch animation."* The wire was right (a `[4, body, foe]` from casting range, F30) and the body
was wrong: it held nothing, so the client drew the only unarmed swing it has.

**OBSERVED on retail's own henchmen** (the seven henchman connections, F28's tapes): **every one of
the 12 bodies is followed, in its create batch, by one `0x0161` CREATE_NAMED_ITEM per weapon and a
`0x006D` NPC_UPDATE_WEAPONS `[agent, leadhand, offhand]` naming them** — the Monk `[8, 20, 0]`, the
Warrior `[9, 22, 23]` (a sword and a shield), the Elementalist `[10, 25, 0]`. The Monk's item 20:
file **112081**, type **26** (a staff, by the ItemType enum whose sword 27 and shield 24 the
Warrior's pair confirms), flags `0x22200100`, model 6462, name id 8582 and four modifier words; the
Elementalist carried 94937/26 with the same words but one; another player's own staff was
112081/26 with a value and a requirement word. Their `0x0035` attack speed came only at their
first swing (1.75 for the casters, 1.33 for the Warrior — F30's cadences). The slice run's own
archive binds file 112081 (`archive.binds_plainly`, row 10668).

**What shipped (SLICE-H7).** `[item.caster_staff]` in `content/items.toml`, the Monk henchman's
item byte for byte (a `capture` row, 20260817T231139); `party_weapon_item` maps a body's weapon
class (`[party.KEY].weapon` / `--hero-weapon`, else the profession's) to the item through
`PARTY_WEAPON_ITEMS` — the staff for staff and wand classes, nothing yet for a Warrior's sword and
shield (on the tape, not extracted); the hero body site sends the item and then `0x006D [hero,
item, 0]` right after the body's create, in retail's order, item ids from 210 by slot. So Tahlkora
holds a staff and the client draws a staff's ranged attack. **Unobserved by the owner's own eye**
(the harness frame is static); the wire is retail's shape.

**And the player's bar, the same commit** (the owner: *"let's move to giving the player some actual
skills other than power attack"*). `--skills` now defaults to **`[player.skillbar]`** —
Mighty Blow 351, Heavy Blow 359, Crushing Blow 352, Irresistible Blow 356, Power Attack 322,
Frenzy 346, Healing Signet 1, Resurrection Signet 2 — eight skills the server MODELS on the
starter hammer: the four hammer attacks got `+ Damage` rows (WIKI, each page's progression read
today; the client's endpoints match the wiki's on all four), Frenzy's attack speed and Healing
Signet's heal were already rows, the signet raises the hero. `[player.attributes]` became a hammer
warrior's — Hammer Mastery 12, Strength 9, Tactics 6, Axe 3, Sword 1, the same 173 points — so at
the shipped ranks Mighty Blow adds 34, Heavy Blow 24, Crushing Blow 16, Irresistible Blow 17, Power
Attack 28 and Healing Signet heals 118. `TEST_SKILLBAR` (316–323) stays the probe bar and
`--skills` still overrides. **Not modelled, said in the rows:** Crushing Blow's Deep Wound on a
knocked-down foe and Heavy Blow's knock-down (no knock-down here), Irresistible Blow's damage on
a block (no block), Healing Signet's −40 armour. `test_agentlife` §H7 (floor 467 → 472);
`test_skilldamage`'s two rank locks re-aimed to the shipped ranks.

**The owner's other line, the same day:** *"the monk still outheals our damage ... tone down the
monk's healing so the bandit is killable."* SLICE-H7b, content only: both corridor monk rows'
Orison recharge went from the client table's 2 s to **8 s** (`[spawn.corridor_monk_a/b]`, the note
says why). Sized off harness `20260913T130707`: at rank 12 one Orison is 60 health and the 2 s row
let the energy pool pace it to one every ~3 s (that run: two Orisons, 41 and 28 landed, and eleven
Banishes), more than a level-1 hammer bar and the hero land together; 8 s is ~7 health a second.
The raider's own Healing Signet row is untouched (it cast it 0 times in that run). **Harness
`20260913T134221` after the change** (the player ordered onto the raider, the bar's energy attacks
pressed on their recharges): the monk cast Orison **once** in the opening bout (40 of 60 landed) and
then Banish and Restore Condition, while the raider went 200 → 160 under the player's 7-a-swing and
the hero's 14s — and the harness player, 100 health at AR 45 under the raider and the monk
together, died in ~15 s and every 10 s after, so the run cannot show the kill: the harness presses
no signet, kites nothing and lands Power Attack twice on 25 energy. The heal is toned; whether the
raider now dies is the owner's own hands. The next knobs, if not: the monk's Banish (49 a cast on
the hero, 36 on the player, every 10 s) and the raider's 200 health.

## SLICE-F34 — **low levels: retail's damage at level 3 is single digits, a body casts at its own ranks and swings its own weapon, and the hero heals herself**

**The owner, after H7 (2026-09-13):** *"tahlkora doesn't self heal i think. the monk killed me after
I killed the bandit with her Banish spell. should reduce attributes here, make the player/hero lvl 3
(10 attribute points) and the enemies lvl 2 (5 attribute points). did we research low level weapon
damage at all? idk if we did a range check on their damage."*

**The research, answered.** Yes for the player's own weapon — the starter hammer's 3–5 is the
item's own damage-range word, tooltip-verified on 2026-08-20, and the swing runs the wiki's
formula `base × 2^((5 × rank − armour) / 40)` (combatmath, since the armour arc). **No for
everyone else**: every NPC swing was `ENEMY_HIT_FRACTION` = 10% of the taker's maximum at armour
60 and every NPC skill cast at `ENEMY_SKILL_RANK` = 12 — a model no level can move. So, measured
on the one low-level retail session (20260819T132414, three level-3 henchmen, the observer at
maximum health 140 = level 3 by the wiki's 100/120/140), damage per landed hit, absolute (the
`0x00A3` fraction × the taker's `0x009F 42` maximum):

| who → whom, plain swing | n | p10 / p50 / p90 |
|---|---|---|
| Pre-Searing hostile → the level-3 observer | 3 | 3 / 4 / 5 |
| level-3 henchman (Warrior/Ranger/Assassin) → hostile | 22 | 5 / 6 / 15 |
| the level-3 observer → hostile | 12 | 1 / 2 / 3 |
| henchman attack skill → hostile | 20 | 7 / 19 / 37 |

Single digits everywhere. Our corridor before today: the raider hit the level-1 player for 13, the
monk's Banish for 36 (49 on the hero), the hero swung for 14 — level-20 numbers in a starter zone.

**What shipped (SLICE-H8).** WIKI throughout (GWW *Level*, *Attribute point*, *Damage
calculation*, *Starter Holy Rod*, *Health*), the corpus above as the yardstick:

- **A body's own ranks.** A spawn or party row may carry `attributes = [[id, rank], …]`;
  `agent_skill_rank` resolves a skill's attribute through the client's own skill row to that rank,
  else `ENEMY_SKILL_RANK`. The corridor's raiders carry Strength 2 / Swordsmanship 1 / Tactics 1
  and the monks Healing 2 / Smiting 1 / Protection 1 — level 2's five points — so Orison heals 27
  and Banish deals 22 before armour instead of 60 and 56.
- **A body's own level.** The row's `level` rides the npc dict (the creature armour formula, 3 ×
  level + the profession bonus: 26 for a level-2 Warrior) and the **skill strike level 3 × level**
  (`agent_strike_level`; the level-20 baseline 60 without one), so the level-2 monk's Banish lands
  22 × 2^((6 − 40)/40) ≈ 12 on the player's spell armour rather than 22 × 1.4. Enemies are level 2,
  120 health (the wiki's NPC base at level 2), the boss 160.
- **A body's own weapon.** `damage = [lo, hi]` and `weapon_attribute` on a row (or the held item's
  own range word — the hero's staff decodes to 11–22) run through the same `swing_damage` the
  player's hammer does, at the body's rank and level, against the location's armour: the raiders'
  6–10 (ours, sized) lands **3–5 on the player's armour 45 — retail's 3/4/5**; the hero's Starter
  Holy Rod 3–5 (WIKI) at Healing 3 lands 2–4 on the raider's 26; the player's hammer at Hammer 3
  lands 2–4. A row without a range keeps the fraction, so every earlier fixture is unchanged.
- **The slice's character.** `[party.slice]` carries `player_level = 3`, `player_health = 140`,
  `player_attributes` Hammer 3 / Strength 2 / Tactics 1, `player_points = 10`;
  `apply_party_character` rebinds the agents globals at `--party slice`, over the base world's
  level-1 / 100-health / 200-point rows that forty offline locks price. The hero is level 3 too:
  140 health, Healing 3 / Divine Favor 2 / Protection 1 (its own `0x0037` reads 0 of 10 and its
  `0x003A` its own ranks), armour 25 (a starter set's; the creature formula gave a level-3 body 9,
  which is why she died in four hits).
- **The self-heal.** `ally_cast_tick` picks an ally-kind heal's target through the hurt-most rule
  the hostile monk has had since SLICE-B3, caster included — the client's target byte 3 allows it.
  Retail's Monk cast at itself 0 of 13 (F28) and the owner asked for it anyway; said here.

**One harness attempt (`20260913T162923`) is inconclusive:** the launch banner read `level 3,
health 140, ranks [(19, 3), (17, 2), (21, 1)], points 10`, the client took the level, the 140, the
three-attribute `0x003A`, the hero's own `0 of 10`, selected the raider on the attack order — and the
socket reset ten seconds into the walk with no assert and no crash dialog (a clean exit, the shape
of a closed window; the owner asked for the harness at that moment). Nothing on the wire before it
is new since H7's green runs except those level messages, and the client drew them. The fight at
these numbers is the owner's hands.

**The rerun the owner asked for (`20260913T163333`) and the two knobs after it.** At the new
numbers the fight ran for the whole hold and nobody died: Tahlkora healed herself sixty times
(the self-heal, working), the raider took 2–4 a swing and 3–5 from the player, its monk's Orison
gave it 27 every 8 s — and its own **Healing Signet gave it 88 every 4 s**, ten casts, refilling it
from 44 to full in one; the owner: *"couldn't bring them down, healing signet too strong."* The
signet's 88 is the skill's table at Tactics 1 (82…172), not a rank we can lower, so **SLICE-H8b**:
its recharge on every raider row went to 20 s against the table's 4 — and then, on the owner's
word (*"just remove healing signet from the bandit"*), **off the raider rows entirely**; the bar
is Sever Artery and Power Attack, the boss adds Desperation Blow (retail's counter, −40 armour
while it activates, is not modelled). Rerun
`20260913T163821`: **the raider died** (`KILL agent 90`, its monk healed it twice, the signet once)
— *"able to kill now"* — **and got back up eight seconds later**, because every hostile shared the
test enemy's `REVIVE_AFTER`; the owner: *"that's correct for the training dummies, but not for
normal enemies."* **SLICE-H8c:** the revive is a per-row opt-in — `revives = true` on
`[spawn.test_enemy]` (the practice target, the Isle's dummy shape), nothing on an area row, so a
killed raider stays killed; a missing key still revives (the legacy `--enemy` body and every
offline fixture). Both runs ended in a clean client exit with no assert once the owner took the
keyboard.

`test_agentlife` §H8 (floor 472 → 480); `test_effects`' stance-duration lock reads rank 12 by name
and `test_spawn_burst`'s hand-copied `0x003A` row follows the H7 base ranks (both were red on main
since H7, unrun then). **Not modelled, said here:** knock-down, block, the wiki's level-scaled
damage multiplier column, an NPC's energy at low level, and the hero's own attribute spend.

## SLICE-F35 — **the sword and the shield, Gash's gate and Final Thrust's double, and a hammer bandit that holds its hammer**

**The owner (2026-09-13):** *"the player uses a Sword and Shield. skills: the classic GW sword
combo: Sever Artery (which we have working), Gash (need Deep Wound + conditional application),
Final Thrust (need 50% HP logic). the bandit should be a Hammer Warrior that just has Power
Attack."*

**The items, OBSERVED on the wire.** F33 had left the Warrior's pair "on the tape, not
extracted". A scratch census over `livewire` (every live connection, 2026-09-13) settles two things
at once. First, **every body gets its weapons, not only a henchman's**: `0x006D` NPC_UPDATE_WEAPONS
goes to **3,016 non-party agents** across the corpus against 21 henchman bodies — a sword (type
27) in 403 leadhands, a shield (24) in 338 offhands, a staff (26) in 609, a hammer (15) in 51, a
wand (22) in 57, an axe (2) in 46, a bow (5) in 127 — so a hostile body holding a hammer is retail's
shape, not an extension of it. Second, the **level-3 Warrior henchman of 20260819T132414** (the
low-level session F34 was measured on) carried item 99, a sword — file 175958, type 27, flags
`0x22000100`, model 7937, name id 8582, words `0x24B80200` (587: slashing) and `0xA4880303` (584:
range 3–3) — and item 100, a shield — file 176078, type 24, flags `0x20000200`, model 7938, one
word `0xA3C80000` (572: armour 0). Both files **bind in the slice's own archive**
(`archive.binds_plainly`, rows 76203 and 76325); the owner's own level-20 sword and shield
(22133/27, 497/24, on every 2026-08-17 connection) do not, and the level-20 Warrior henchman's
(39791/27 at 15–22 with a requirement word) is the wrong level.

**What shipped (SLICE-H9).** `[item.starter_sword]` and `[item.starter_shield]` in
`content/items.toml`: the level-3 henchman's bytes, **with two words ours** and said in the rows —
the sword's range word composed as `0xA4880302` for the Starter Sword's **2–3** (WIKI, GWW *Starter
Sword* §Stats) in the tape's own layout (only `arg2` differs from the verbatim 3–3), the shield's
armour word `0xA3C80300` for the Starter Shield's **3** (WIKI, GWW *Starter Shield* §Stats) in the
layout the level-20 shield's `0xA3C80700` (armour 7) uses; `itemmods.py --decode` reads both back
(584 arg 3 arg2 2; 572 arg 3). The server swings the word and the client draws it: one fact, one
place, the hammer row's own discipline. **The character holds them from the party row:**
`[party.slice].player_weapon` / `player_offhand` rebind `agents.PLAYER_WEAPON` /
`PLAYER_OFFHAND` (new; `STARTER_HAMMER` stays the base fixture forty locks read),
`PLAYER_SWING_DAMAGE` (2–3), `WEAPON_ATTACK_SPEED`/`ATTACK_INTERVAL` (a sword's 1.33 s, content
`[attack_speed.rates]`, against the hammer's 1.75), `WEAPON_TYPE_ATTRIBUTE` grew the sword (27 →
Swordsmanship 20) and the axe (2 → 18), and `player_skills` the bar `default_skillbar` hands out.
The load batch declares the offhand, moves it to the equipped bag's cell 1 (UPSTREAM,
`EquippedItemSlot_OffHand`), names it in the weapon set's **fourth field** — `0x0147 [key, set,
lead, off]`, non-zero on retail's wire exactly where the character carries a shield (14 of 56 sets
in 20260817T231139, 0 of 12 in 20260817T180610) — and in `0x006E`'s position 1. **The shield's
armour rides every location** (`offhand_armour`; WIKI, GWW *Shield*: "a bonus to a character's
overall armor rating"): 45 → 48 physical, 25 → 28 elemental. The ranks became Swordsmanship 3 /
Strength 2 / Tactics 1, the same ten points.

**The strikes (SLICE-H10).** Two `skill_effect` rows and three readers, WIKI throughout (GWW *Gash*
and *Final Thrust*, read today; the client's own endpoints are the numbers):

- **Gash (384)** — client `args = 6`, scale 5→20, bonus 5→20; wiki var1 `+ Damage`, var2 `Deep
  Wound duration`, and the description gates BOTH on the target: *"If this attack hits a Bleeding
  foe, you strike for 5…20 more damage and that foe suffers a Deep Wound"*. The row's
  `requires_condition = "Bleeding"` is that gate: `attack_skill_terms` returns no bonus and no
  condition unless a live 478 episode sits on the target (`agent_has_condition`, the effect
  table), else the +damage and a Deep Wound of the bonus slot's seconds through the existing 482
  model (the maximum falls 20%). At Swordsmanship 3: +8 and 8 s.
- **Final Thrust (385)** — the page's own `id = 385` (the client row 386 is something else);
  client `args = 2`, scale 1→40, **bonus 50/50 with the bit clear**, adrenaline 10 strikes,
  recharge 4; wiki: *"Lose all adrenaline. If Final Thrust hits, you deal 5…40 more damage. This
  damage is doubled if your target was below 50% Health"*, Notes: *"only doubles the additional
  damage this skill adds"*. The 50 in the bit-clear slot is the threshold, read through
  `skill_flat_constant` (Rush's-25 shape) under `bonus_scale_means = "Health threshold %"`; the
  double is of the BONUS only, judged on the target as it stands before the strike; and
  `clears_adrenaline = true` pays the loss at the cast's completion — the pool's `clear()` plus
  one `0x00D0 [player]`, the death's and the 25 s wipe's shape (15 of 15 isolated clears in the
  corpus; no Final Thrust cast exists in it to copy). At Swordsmanship 3: +9, +18 below half.
- Both terms serve the NPC arm of `land_skill` unchanged (an NPC's wipe is its own pool's; no
  client holds a copy of it).

**The bandit (SLICE-H11).** All three raider rows: `skills = [[322, 0.0, 3.0]]` (Power Attack
alone; the boss keeps Desperation Blow), `attributes` Hammer Mastery 2 / Strength 1 / Tactics 1
(five points), `weapon_attribute = 19`, `attack_speed = 1.75` (WIKI, GWW *Hammer*), and
**`weapon_item = "starter_hammer"`**: `spawn_population` sends `0x0161` for the item (id `300 +
agent`) and `0x006D [agent, item, 0]` after the body's create — the hero body's H7 site for a spawn
row, and the census above is why. The sized 6–10 still lands 3–5 on armour 45 at Hammer 2.

`test_agentlife` §H9/H10/H11 (floor 480 → 488): the rows, the character (before/after
`apply_party_character`), Gash through the player's own press → `cast_tick` landing on a foe
without and then with Bleeding (4 dealt and no 482; then swing +8 and an 8 s Deep Wound, 100 → 80),
Final Thrust at 30 of 80 and at 70 of 80 (≥ 18 then 9–17, one `0x00D0` each), the three readers,
the NPC arm's terms at the player, the raider rows; `test_population` §7 (73 → 75): the armed row's
`0x0161` + `0x006D` and the bare row's silence, both encoding through the codec. **OBSERVED the
same evening, the owner's own hand pass at level 3:** *"ran it, the skills work as advertised. the
bandit quest was completable"* — the first time the whole slice has been played through on the
sword bar against the hammer raiders, and the balance note that opened H7b/H8b (an unkillable
raider) closes with it. **Not modelled, said here:** the sword's slashing type against anything,
Frenzy on a sword, the eighth bar slot (empty), and — the same list as F34 — knock-down, block.

## SLICE-F36 — **knock-down and block: the corpus's prop 63 at 2.0 s, the client's own "block" word, and five hammer skills that finally do what their pages say**

**The owner (2026-09-13):** *"do knock-down and block next."* Both had been "not modelled, said
here" since H7 (Crushing Blow's Deep Wound on a knocked-down foe, Heavy Blow's knock-down,
Irresistible Blow's damage on a block).

**Knock-down, MEASURED.** A scratch census over every live connection (`kd_census.py`): property 63
occurs **three times in the whole corpus**, all in 20260819T132414 (the level-3 session), every one
`0x00A2 [63, target, 2.0f]` — the **untargeted float channel carrying the duration** — in the same
batch as the caster's `[58]` finish and its `[20, target, caster, 937]` visual (t=183.119, 236.790,
260.791; the caster is agent 30, a party Elementalist, skill 937 an Earth Magic spell; the wiki's
knock-down list is long and the id is not resolved here). No status word follows it (the one
`0x00F1` beside the first is the observer's own Bleeding landing in the same instant). That agrees
with what `studies/animref` §6/D7 had already decoded and parked: prop 63's case body pushes the
wire's own float into the client's knock-down method `0x007E0490(agent, duration)`, where prop 35's
pushes a compiled-in 0.4 s stagger. **WIKI** (GWW *Knock down*): a knocked-down character cannot
move, activate skills with an activation time or aftercast, or switch weapons; 2 seconds unless a
skill says otherwise; cannot be knocked down again until up. **No retail witness exists for an
attack skill's knock-down** — the same property after a strike is RECONSTRUCTION, and the row says
so. Stances do **not** end on a knock-down (GWW *Stance* lists nothing of the kind).

**Block, MEASURED as far as the wire allows.** The attack-fail word `[38, target, attacker, reason]`
occurs **once** in the corpus (a reason-2 "fail"); no retail block is on any tape. The reason
vocabulary is the client's own — the effect drain's kind-7 case switches reason 0 to string 471,
which the owner's archive resolves to "block" (`agents.ATTACK_FAIL_REASONS`, read out of the
client on the Blind arc). **WIKI** (GWW *Block*): a blocked hit deals no damage and yields no
adrenaline to either side; the chance comes from skills, **multiplicatively** (two 50% skills block
75%); no effect on spells.

**What shipped (SLICE-H12).**

- **`knock_down(send, state, agent, …)`**: the corpus's `0x00A2 [63, agent, seconds]` after the
  body's state is settled — a hostile's or party body's swing and cast in flight dropped, its walk
  halted with the NPC halt's own `0x0028`, a `knocked_until` clock; the player's pending casts
  marked cancelled and released by the tick with the measured cancel burst (`_mark_cancelled`), an
  armed swing dropped, movement reports refused by a new arm beside the dead-player and rooted
  arms, a skill press answered with the bare E2 release. Every tick (`enemy_attack_tick`,
  `enemy_move_tick`, `ally_cast_tick`, `ally_attack_tick`, `attack_tick`) steps over a down body.
  A second knock-down while down sends nothing (WIKI). `--no-knock-down` reverts.
- **The skills**, WIKI throughout, the client's own numbers: **Hammer Bash (331)** `knocks_down` +
  `clears_adrenaline`, its 2 s read from the client's bit-clear duration slot (2/2); **Heavy Blow
  (359)** `requires_condition = "Weakness"` gating its +damage AND its knock-down (`attack_skill_terms`
  grew a third term); **Crushing Blow (352)** `bonus_scale_means = "Deep Wound"` with
  `condition_requires = "knocked down"` — the bonus regardless, the 5–20 s wound only on a foe on the
  ground; **Irresistible Blow (356)** `knocks_down_if_blocked` — on a block the row's damage lands
  anyway (armour-ignoring, OURS: the page names no type) and the blocker falls; **Desperation Blow
  (323)** `random_conditions` (Deep Wound 20 / Weakness 20 / Bleeding 25 / Crippled 15, the
  description's own seconds) drawn at a landed hit and `self_knocks_down` — the user falls, hit or
  miss, for the client's 2/2. The corridor boss carries it, so the boss now falls after every
  Desperation Blow and the player can see a knock-down without a hammer bar.
- **Block**: a taker's live episodes' `block_chance` rows through the product rule
  (`block_chance`); `requires_shield` rows count only for a wearer holding a type-24 offhand
  (`holds_shield`). `hit_enemy`, `land_swing` and `land_swing_on_body` roll it right behind the
  Blind miss, send the swing's close and `[38, blocker, attacker, 0]`, and deal nothing; each now
  **returns** `"landed"` / `"blocked"` / `"missed"`, which is what lets a strike's knock-down ride
  a landed hit only. **Bonetti's Defense (380)** is the block skill on the slice bar's eighth slot:
  `block_chance = 75` and `energy_per_melee_block = 5` (the client's two flat slots, named by the
  `_means` labels), `ends_on_skill_use` (closed with a real `0x0044` on the wearer's next accepted
  press), the duration 5–11 s from the client's progression. The energy rides the player's pool and
  a property-52 gain. `--no-block` reverts.
- **Weakness (486)** is modelled as far as the two skills need it: the swinger's WEAPON damage
  × 0.34 (WIKI: "66% less damage with attacks", the bonus untouched); the −1 to attributes is not.

`test_agentlife` §H12 (floor 488 → 502): the body's fall (halt + prop 63, the refused second
fall, no action while down, action on rising), the player's fall (the cancelled cast's release
burst, the E2-only press, the dropped swing, the accepted press on rising), Hammer Bash / Crushing
Blow / Heavy Blow / Desperation Blow through the player's own press → landing, the three readers,
the hostile's Bonetti's blocking a forced roll (the word, no damage, no adrenaline) and letting a
forced miss-roll through, Irresistible Blow's punishment, the player's Bonetti's (the block, +5
energy on the wire, the stance ending on a press), `holds_shield`, Weakness. **OBSERVED the
same night, the owner's hand:** *"knock-down and block work (only saw Desperation Blow work)"* — the
boss's own fall after its blow and the block (Bonetti's on the player's bar); the hammer skills
themselves are on no bar the owner played, so Hammer Bash / Heavy Blow / Crushing Blow /
Irresistible Blow stay desk-and-tests. **Not modelled, said here:** Shield Stance's damage reduction (the row is not
written), Crippled's slow, Weakness's attribute loss, quarterknocking's re-knock at the rise
instant (a down body simply refuses until its clock runs out).

## SLICE-F37 — **attack speed: the server has paced Frenzy since August; the client was never told, and the field that tells it was read out of the client months ago**

**The owner (2026-09-13):** *"attack speed next (Frenzy)."*

**What already existed.** `attack_interval_factor` (episodemods, 2026-08-22) scales every swing's
duration by an open attack-speed episode — Frenzy's flat 33 cuts the hammer's 1.75 to 1.1725, the
wiki's exact table (GWW *Attack speed*, read today: "these skills actually modify the duration of
each attack, not the rate"; hammer +33% = 1.1725, sword 0.8911) — at all seven consumers (the
player's swing gate and windup, the chain restart, the enemy, party and NPC swing clocks), and
`damage_taken_multiplier = 2.0` doubles what a Frenzied taker takes. So Frenzy already *was* faster
on our wire: the STARTs came 33% closer together. **What was missing is the client's half.** The
client animates each swing to the pair GAME_SMSG `0x0035` gave it — `+0xEC` base × `+0xF0`
modifier, multiplied at `0x007F837E`, both asserted non-zero at AvChar.cpp:4791/4792
(`studies/enemy/PLAN.md` 6q, CORROBORATED three ways: "1.0 = none, 0.75 = +25% IAS, 0.67 = +33%
IAS") — and ours declared every agent once, at load or create, modifier 1.0. A Frenzied body was
paced 33% faster and drawn at its old speed.

**What the corpus cannot say, measured rather than assumed.** A census over every live connection
(`ias_census.py`, `ias_cadence.py`): **62 retail `0x0035`s, every modifier 1.0, zero per-agent
changes**; and **no attack-speed stance episode exists on any tape** — Frenzy 346, Flurry and the
rest apply 0 times. The one 33/33-slot skill applied to a retail character, 364, is a Tactics
**shout** (type 15, 5 energy / 20 recharge, 5–13 s) whose swing cadence is unchanged inside its
episodes (10 episodes on the owner's own Warrior, inside/outside p50 ratio 0.97–1.03 at n=64
outside); the two episodes at ratio 0.55 are on a different connection with five outside gaps of
2.4–2.7 s — a walking sample, not a rate. `studies/animref` §8 had already filed the same gap as
REFUTED-BY-METHOD for the windup under a modifier. So whether retail's server *re-sends* `0x0035`
when a stance opens is UNWITNESSED; that the client *multiplies the field in* is READ out of it.

**What shipped (SLICE-H13).** `attack_speed_tick`, right behind `speed_tick` in the world tick:
for the player and every living body, the current `attack_interval_factor` is compared with the
modifier last declared for that agent (1.0 until told otherwise), and on a change — the stance
opening (0.67), expiring, being replaced or cured (1.0) — one `0x0035 [agent, its base, factor]`
goes out; never per tick, never while nothing moved. `send_attack_speed` grew a `modifier`. The
resend is **RECONSTRUCTION** on a field whose meaning is measured, and the row says so;
`--no-attack-speed-sync` is the pre-H13 arm. `test_mechanics` §7b (floor 174 → 181): nothing open
sends nothing; Frenzy opening sends exactly one `[player, base, 0.67]`; a second tick nothing; the
close one `[player, base, 1.0]`; a body under Frenzy its own `[body, 1.33, 0.67]` with the player
not re-declared; the revert arm silent. **Unobserved on a client:** whether the swing animation
visibly quickens under Frenzy on the slice bar is the owner's eye; a live capture with Frenzy
running on the secondary account would witness retail's own resend, or its absence.

## SLICE-F38 — **MANTID-S: four corrections the Factions tutorial tape paid for — the effect list is the player's own, a hex has auras and can punish attacks, Ether Feast, and a skill granted mid-map**

**The owner (2026-09-13):** *"go for it"*, to a plan of three server corrections from capture
`20260913T210901` ([../quests/FINDINGS.md](../quests/FINDINGS.md) §10). Measured first, then
shipped; every item carries its revert flag and its label.

**1. The effect list is the player's own — MEASURED over the whole corpus, then shipped.** A
census of every live connection (`fx_census.py`, 61 connections): **every `0x0042`, `0x0043`
and `0x0044` ever sent names the observing player — 136 / 108 / 125, 0 of 369 on any other
agent**; the tutorial tape holds none at all because the Mesmer wore nothing. A hex, condition
or enchantment on anyone else reaches the client through the status word — `0x00F1` bit
`0x800` for a hex (12 sightings on others), `0x02|bit` for a condition (312) — which
`push_status` has sent since the Deep Wound arc. This server had been sending the player's
icon-list messages to foes, henchmen and party bodies since the effects arc: traffic retail
never produces. **Shipped:** one door, `effect_list_send`, through which all ten `0x0042`/
`0x0044` sites now pass; it sends for the player, keeps sending for a HERO body (no hero tape
exists, UNVERIFIED either way, and the H ladder was observed with the icons), and drops the
rest with a count (`state["effect_list_suppressed"]`). `--effect-list-to-all` is the pre-MANTID
arm. Seven checks in `test_mechanics` §16/§26/§28 and one in `test_skilldamage` had pinned the
refuted shape (a `0x0044` on hostile 11, a `0x0042` on foe 10) and were rewritten to the
measured one, each saying why; the player-side control was added beside the foe-side refusal.

**2. A hex's auras — OBSERVED, content-gated.** Properties 6 and 7 are one client function
with an on/off flag (SLICE-F5); the tape puts `[6, foe, 1]` and `[6, foe, 4]` in the batch
that lands Empathy on a foe (5 of 5) and `[7, foe, 1]`, `[7, foe, 4]` in the batch that kills
it. The ids index a table this repo does not read, so they live on the skill's row
(`[skill_effect.26] auras = [1, 4]`) and are reused for nothing else ("observed context is
part of the claim"): `aura_on` after the status word at apply, `aura_off` on the episode's
removal whoever wears it (expiry is RECONSTRUCTION — only the death was witnessed).

**3. A hex that punishes attacks, and the maximum declared before the fraction — OBSERVED.**
Empathy's damage on the tape: the hexed foe's first swing drew `0x009F [42, foe, 25]` then
`0x00A3 [55, foe, hexer, −0.40]` — the armour-ignoring channel, a NEGATIVE fraction, 0.4 × 25
= 10 = the rank-0 scale — ahead of the foe's own `0x00A7`/`0x00A3` (3 of 3). **Shipped:**
`triggers_on_attack = "Damage"` on a hex's row; `on_attack_triggers` at all three landing sites
(`hit_enemy`, `land_swing`, `land_swing_on_body`) deals the episode's scale from its caster
(episodes now remember `caster`) through `armour_ignoring_damage`, which declares the target's
prop 42 immediately before the word and kills through the same doors a hit does; a foe that
dies to its own swing's punishment never lands the swing. The declaration-before-fraction is
what unit-setup's "health-max is a rare mid-combat correction" was. Empathy's `bonus` (the foe
deals 1..15 less) is NOT modelled, said on the row. `--no-hex-triggers` reverts. **The corpus
check `test_mechanics` §20 P1 ("55 positive in 99%+") is now 97%+**: the negatives are this.

**4. Ether Feast, and a skill granted mid-map.** `[skill_effect.40]`: `scale_means = "Energy
loss"` (a flat 3, bit clear) and `bonus_scale_means = "Heal per energy lost"` (20..65);
`energy_feast` takes the loss off the body's own pool when one is modelled and heals the caster
per point lost — `0x00A3 [55, me, me, +frac]`, the tape's 0.68 × 88 = 60 (3 of 3). A granted
skill is `grant_skill`: `0x00DC SKILL_SET_COPIES [skill, 1]`, `0x00D9 SKILLBAR_UPDATE_SKILL
[player, first empty slot, skill, 0]`, and `0x001C SKILL_UNLOCKED [skill, 0]` unless the
account already knows it (the Resurrection Signet came without one) — the tape's batch, 3 of
3; a full bar learns without equipping (RECONSTRUCTION). Quest rows take `reward_skills = [...]`,
granted in the reward frame ahead of the experience. No shipped quest uses it yet; that is the
operator's content.

**What was already right, now corroborated at n=2.** The death penalty scales the BASE energy
(30 → 27 on the Mesmer; `morale.effective_max` did this since 2026-08-22), experience buys it
back at 75 XP per 1 % (+1 per third 25-XP kill on the tape), and a quest reward's experience
runs through the same credit (`grant_quest_reward` → `morale_experience`): the tape's `0x00EE
[10, 10]` at the 2,000-XP reward is that rule, not a new one. `test_pools` carries the Mesmer's
(4, 27) / (4, 28) rows and its death at (0, 27).

**Tests.** `test_mechanics` §29 (floor 181 → 198): no `0x0042` to a foe but the `0x800` word and
the two auras, the auras off on a strip with no `0x0044`, the player's own `0x0042` unchanged,
the revert arm; the hexed foe's swing punished `[42, foe, 100]` + `[55, foe, player, −0.10]`
ahead of its hit, a foe at 5 dying to it with no hit landing, the revert arm; Ether Feast's
`[55, me, me, 0.60]`; a grant's three messages, no `0x001C` on a known skill, a full bar, and a
quest row's `reward_skills` ahead of the experience. `test_skilldamage` (57 → 58), `test_pools`
(pairs), `test_agentlife` 502, `test_effects` 84, `test_guards` 41 green. **Unobserved on a
client:** whether the foe's hex arrow and auras draw from the word alone (retail's client
draws them from exactly this traffic, which is the argument), and the granted skill appearing
in the bar mid-map.

## SLICE-F39 — **JARIN: the first retail hero on a tape — no `0x0074`, the hero is a second player on the wire, Frenzy's resend rides the next swing, and the commander's every order is echoed**

OBSERVED, 2026-09-14, capture `20260914T005758` (build 38888, base, 14 of 14 plan steps, seals
agree, 4 keys, three game connections: Kamadan 449 → **Plains of Jarin 430** → Kamadan). The
plan is [RUN-LIVE-HERO.md](RUN-LIVE-HERO.md) (sha256 `5bbe6f31…`), scored in its §7. The owner
after the run: *"i didn't press F11 for the hero Frenzy casts, though he did use it. i flipped the
order of the party/hero flags (i did the party one first instead of second). for the resurrection
signet, the hero used it on me."* Frenzy was joined by its `0x0042` instead of the marks; the flag
steps are read in the order played. The Ranger is agent 708 / 29 / 544 and the hero 117 / 30 /
324 across the three instances (agent ids are per instance, for the hero as for the player);
scripts `jarin_score2–4.py` (scratch). One tape throughout; counts are this tape's.

### 39.1 The rig — no `0x0074` in 3 of 3 instances, and the hero gets the player's own character block (JARIN-P1 refuted in form, P2 confirmed, Q1–Q3 answered)

The Kamadan load, in order, one frame (37.73 s):

```
0x0037 [708, 6, 10]   0x00B7 [708, 2, 0, 0]   0x00DA [708, bar]   0x009F [42, 708, 1]   0x009C [708, 100]   0x003A [708, attrs]   0x009F [42, 708, 140]      -- the PLAYER
0x0037 [117, 6, 10]   0x00B7 [117, 1, 0, 0]   0x00DA [117, [322, 382, 348, 1, 385, 346, 0, 2]]   0x009F [42, 117, 140]   0x009C [117, 100]   0x003A [117, [20, 21, 2, 1, 2, 1]]   -- the HERO, the same block
0x0072 [6, 117, 200, 0]                        -- HeroActivate (hero 6 = Koss, the owner's word; agent, inventoryId, aiMode)
0x009F [36, 708, 3]  0x009F [36, 117, 3]  0x00A6 [117, 1, 0]
0x01D2 [86]  0x01CB [86, 72, 1]  0x01C2 [86, 72, 117, 6, 3]  0x01D3 [86]  0x01B2 [86, 1]   -- the party build
```

**No `0x0074 MERCENARY_INFO` anywhere on the tape** — 0 in three instances. The heroes study's
§14.5 order (`0x0074` first, `0x01C2` before `0x0072`) is ours, and its §11.3 proof that `0x0074`
creates `charHeroData` was measured under that order; retail sends `0x0072` **before** the
party build and never sends `0x0074`, so the record is created by `0x0072` itself or by the
character block ahead of it (which, note, is the player's own five-message block addressed to the
hero's agent: attribute points, professions, **the skill bar as `0x00DA [hero, 8 ids, 8 zeros,
1]`**, maximum health, morale, attributes). JARIN-Q2 is answered by that line: the bar is
delivered at load exactly as heroes §15.1 found it accepted; opening the hero panel (step
`panel`) sent nothing beyond the town's c2s cadence (`0x0009` ×2 in 12.5 s, 10 in 50 s).
**`0x0072`'s fields:** `inventoryId` 200 / 5 / 157 (per instance); **`aiMode` 0 / 0 / 2 — the
return to Kamadan carries the last stance clicked in the field (Avoid, 510.66 s)**, so the mode
persists across the zone. `0x01C2 [party, member, heroAgent, heroIndex, level]`: 6 and 3 — **hero index 6 is Koss** (the owner), which agrees with the catalogue's numbering that puts Tahlkora at 3 (`[party.slice]`).
`0x0199 [member, map, explorable, …]`: `[72, 449, 0]`, `[1, 430, 1]`, `[90, 449, 0]` — the first
word is the party-member number `0x01CB` also carries, not an agent.

**A town has no hero body (P1's second half CONFIRMED):** no `0x0020`, `0x0161` or `0x006D` for
agent 117 in Kamadan (the town's item numbered 117 is agent 91's — a coincidence checked). **The
field has one:** `0x0161` for items 778 and 779, then `0x0020 [30, …]`, then `0x006D [30, 778,
779]` — F33's item-then-`0x006D` order, on a hero — all before the party build, in the same frame
as the block.

### 39.2 The hero is a second player on the wire, not a body

Every per-player family the corpus had only ever shown on the observer is sent for the hero:

| family | on the hero, this tape | what it corrects |
|---|---|---|
| effect list `0x0042`/`0x0044` | 24 applies, every close | F38's "the player's own" — `effect_list_visible`'s hero branch, kept "for want of a witness", is **OBSERVED** |
| adrenaline `0x00CF [hero, units]` | 107 rows: 25 per landed hit, **2 per hit taken** (2 % of 140) | authsrv sends `0x00CF` for the player only |
| adrenaline clear `0x00D0 [hero]` | 5 Final Thrusts + 2 deaths, 7 of 7 | same |
| skill messages `0x00E3 [hero, skill, 0]` / `0x00E5 [hero, skill, 0, recharge]` / `0x00E6` | 48 / 35 / 1 | authsrv's "every `0x00E3` in the corpus, 6 of 6, names the PLAYER" — retail announces a hero's casts on the same family (the hero panel's recharge) |
| morale `0x009C` | every tick on both: `[29, 100]` + `[30, 100]` at 238.18, 86 at 410.84, 87 at 534.48 | morale is per party member |
| death tick | `0x00F1 [30, 0x10]`, `0x009C [30, 85]`, `0x00D0 [30]`, `0x0044` per effect, `0x009F [41, 30, 17]`, `0x00A2 [43, 30, 0]`, `0x009F [42, 30, 119]`, `0x0026 [30, 8]` | JARIN-Q7: the player's tick exactly, plus the adrenaline clear and the effect closes |
| attack speed `0x0035` | 19 rows (§39.3) | — |

The body's `0x0026` codes are 8 (death) and 9 (rise) against the player's 4 and 5 (morale study).

### 39.3 Frenzy — retail resends `0x0035`, and it rides the next attack start (JARIN-P7 CONFIRMED, shape corrected)

19 `0x0035` for the hero, **every one in the same instant as a `0x00A0` start by the hero**:
mod 1.0 with the first start of a chain while unstanced (173.35, 197.46, 226.60, 298.47, 382.59,
434.09, 511.72 — Power Attack each time), 0.67 with the first start of a chain while Frenzy was
already open (403.25, a Sever Artery), and **0.67 with the first swing after the stance applied or
re-applied** (176.16 after the apply at 175.50; 181.81 after the re-apply at 181.50; 12 of 12).
**Never at the apply itself**: six applies out of combat (185.8, 212.2, 242.1, 395.7, 410.5,
417.7) had no `0x0035` within 1.5 s, and the close sends nothing — the 1.0 comes with the next
chain's first start. The pair is `[30, 1.33, 0.67]` — the sword's 1.33 base, the 33 % stance.
The player's bow declared `[29, 2.475, 1.0]`, the hostiles `[x, 1.75, 1.0]`, each at its chain's
first start. So SLICE-H13's resend is **OBSERVED in substance**: the client is told the modifier
on the wire, per agent. **Its timing is ours**: `attack_speed_tick` sends at the change; retail
sends at the next start. The client multiplies at animation time either way, so the drawn swing
is the same; the measured shape is "with the start" (JARIN-S).

**The AI's cadence:** Frenzy applied 17 times, re-applied every 4.3–6 s *inside* a fight
(`0x0044 [30, slot]` + `0x0042 [30, 346, 0, slot, 8.0]` while the 8-s episode still ran) —
pressed on recharge (4 s), not on expiry.

**Double damage — INCONCLUSIVE, said so.** Hits on the hero inside Frenzy: 3 or 5 hp (n = 27,
six skale); outside: 3 (foe 35, n = 1) and 2 (foe 28, n = 1). A doubled 2–3 would read 4–6; the
5s fit and the 3s do not, and two outside hits cannot separate a random 2–5 from a doubled 1–3.
A hero cannot be told to withhold the stance; a player Frenzy run can (P14 was skipped — the
Ranger has no secondary, `0x00B7 [29, 2, 0, 0]`).

### 39.4 "Watch Yourself!" is skill 348, and it lands on both lists (JARIN-P6 half)

The hero's `0x00DA` is the owner's listing in the owner's order — Power Attack 322, Sever Artery
382, **"Watch Yourself!" 348**, Healing Signet 1, Final Thrust 385, Frenzy 346, (empty),
Resurrection Signet 2 — so the runsheet's UNVERIFIED 364 was wrong (364 is another Tactics
shout). Seven shouts, each **two applies in one instant**: `0x0042 [29, 348, 1, slot, 10.0]`
and `0x0042 [30, 348, 1, slot, 10.0]` — field 3 = 1 = the hero's Tactics rank (effects.py's rank
reading, a fifth witness), duration 10.0 s, both closed by `0x0044` 10 s later; no status-word
change on either. The player's list, yes; the hero's list **also** (§39.2).

### 39.5 The hero fights (JARIN-P3, P4 CONFIRMED; P5 ABORTED; Q4 refuted; P8 REFUTED as stated)

**Opening:** 3.0–3.5 s after the player's start, on the player's target, 4 of 4 player-opened
fights — the melee body chases first (`0x002A [30, point, 0, 0, foe]`, 52 of 52 naming a hostile,
0 naming the player; `0x0028 [30]` twice, both at the reach). F30's 0.50 s was a caster from
where it stood. **Casts:** 322 ×11, 382 ×7, 385 ×5, 2 ×1 — **no Healing Signet** (P5's floor
unmet). An attack skill is `0x00A0 [50, 30, foe, id]`; +0.56 s `0x00E5 [30, id, 0, recharge]`,
`0x009F [46, 30, 0]`, `0x00CF [30, 25]`, `0x00E3 [30, id, 0]`. **Sever Artery → `0x00F1 [foe,
0x3]` 0.35 s later, 7 of 7** (`0x83` on the caster 54, whose bit 0x80 was already up), and **0
`0x0042` on any foe** (P4 ✓). **Final Thrust → `0x00D0 [30]`** 0.35 s later, 5 of 5 (JARIN-Q4
refuted: the hero's adrenaline is on the wire, gain and clear).

**Who the hostiles opened on** (each hostile's first start or cast on the party):

| hostile | first on | who had hit it before (in order) |
|---|---|---|
| 35 | HERO | player 169.9, hero 173.4 |
| 34 | HERO | player 194.0, hero 197.5 |
| 26 | **RANGER** | player 223.6, hero 226.6 |
| 54 (caster, Guard step) | RANGER (its hex) | nobody |
| 44 (Avoid step) | RANGER | player only |
| 40 | HERO | player 361.9, 400.5, hero 403.2 |
| 28 (lock) | HERO | hero only |
| 42 | RANGER | player 508.8, hero 511.7, player 512.1 |
| 53 | RANGER | player only |

Where both had hit it (5): the Warrior 3, the Ranger 2. F29's **lowest-base-armour** rule (51 of
58 on the level-20 henchman tapes) predicts the Ranger 5 of 5 — **REFUTED here at n = 5**;
"last to hit it" fits 4 of 5 (26 is the miss). F29's corpus had the softest class also the
healer standing back; this pair separates armour from role. CONTESTED; `hostile_target` keeps
F29's rule until a tape with more than five dual engagements decides it.

### 39.6 The commander — every order echoed, obeyed, and one cleared by the server (JARIN-P9–P12 CONFIRMED; Q5, Q6 answered)

| t | c2s | s2c echo | latency | what the hero did |
|---|---|---|---|---|
| 265.90 | `0x0015 [30, 1]` Guard | `0x0062 [30, 1]` | 30 ms | first start 2.3 s after the hostile's cast on the player (296.15 → 298.47) |
| 355.34 | `0x0015 [30, 2]` Avoid | `0x0062 [30, 2]` | 50 ms | 0 starts in 24.6 s while 44 hit the player 8 times |
| 379.93 | `0x0015 [30, 0]` Fight | `0x0062 [30, 0]` | 40 ms | `0x002A` chase **in the echo's instant** (379.97), Power Attack 2.6 s later |
| 418.95 | `0x0016 [30, 28]` lock | `0x0063 [30, 28]` | 50 ms | 17 leads / 8.5 s to 28, Power Attack at 434.09 with no player start on 28 |
| 443.85 | — | **`0x0063 [30, 0]`** | 0.57 s after the killing Final Thrust | **Q5: the server clears the lock on the wire at the kill** |
| 461.96 | `0x001B [(x, y), 0]` party flag | `0x0067 [(x, y), 0]` | 50 ms | lead 1.5 s later ends **0.0 u** off the flag — no slot offset for a one-hero party |
| 471.12 | `0x001B [(+inf, +inf), 0]` | `0x0067 [(+inf, +inf), 0]` | 40 ms | walk back begins in the echo's instant |
| 483.42 | `0x001A [30, (x, y), 0]` hero flag | `0x0066 [30, (x, y), 0]` | 30 ms | lead 0.5 s later ends **0.0 u** off the flag |
| 490.16 | `0x001A [30, (+inf, +inf), 0]` | `0x0066 [30, (+inf, +inf), 0]` | 50 ms | **Q6: the clear's c2s is the s2c's own form**; walk back in the instant |
| 510.66 | `0x0015 [30, 2]` Avoid | `0x0062 [30, 2]` | 30 ms | persisted into the next instance's `0x0072` |

pvpui 28's shapes, captured on our client, are retail's; the echoes ours sends are what retail
sends, 8 of 8. **Ours differs in two places:** the lock is never cleared on the wire at the
target's death, and `party_slot_point` gives the party flag a slot offset that retail does not
apply to a lone hero (JARIN-S).

### 39.7 The wipe, the shrine, the signet (JARIN-P15 CONFIRMED; Q7 answered; the return's morale refuted)

Round one: the hero died at 307.83 (§39.2's tick), the player at 329.64 (`0x00A3 [17, 29, 54,
−0.129]` the blow, then the morale tick, `0x002D [29]`, `0x0026 [29, 4]`). **10.6 s later, one
frame (340.21):** `0x0025` facings and `0x002C` position sets on plane 19 for both (the shrine),
**the hero's body deleted (`0x0021 [30]`) and re-created (`0x009A`, `0x009B`, prop 36, `0x00A6`,
`0x00F0 [30, 16]`, `0x0020`, `0x006D [30, 778, 779]`)**, then both raised: `0x00F1 [·, 0]`,
`0x00A2 [43, ·, 0.04]` energy, **`[52, ·, 1.0]` and `[55, ·, 1.0]` — full health**, the maxima
kept at −15 %, `0x0026 [29, 5]` / `[30, 9]`. **No `0x01D8 PARTY_DEFEATED`** — the second retail
wipe without it (MANTID's scripted one was the first); the code sends it 0 of 2 in PvE.
Round two: the player died at 598.80 (morale 71); **the hero's Resurrection Signet `0x00A0 [60,
30, 29, 2]` 0.63 s later, `0x00F1 [29, 0]` 3.0 s after it** with `0x00A0 [20, 29, 30, 152]` (the
rise's prop-20 effect from the caster) — P15 as F28 measured on henchmen; the hero then died
(609.25, morale 72) and its corpse was deleted at 625.19 as the player walked off. **Kamadan's
load: `0x009C [·, 100]` for both** — the death penalty is cleared on entering an outpost (the
return step's "carried in" REFUTED; GWW says the same, now measured).

### 39.8 The player, and the formation (JARIN-P13 partial, P14 skipped, P16 half)

Bow attack skills `0x00A0 [50, 29, foe, 394]` ×2, `[…, 392]` ×1; preparations and Troll Unguent
as `0x0042 [29, 433, 0, slot, 24.0]`, `[29, 446, 0, ·, 13.0]`, `[29, 455, 0, ·, 8.0]`; the
projectile bracket was not scored. **Word 38 `[38, 29, foe, 1]` three times** — reason 1 on the
Ranger as target, beside F36's reason 0 (block) and 3 (miss). ~~unnamed here, UNVERIFIED (the
client's own string table has it)~~ — **it was already named, four days before this was written:
reason 1 is "dodge"**, string 473, OBSERVED from the client's kind-7 drain switch and the owner's
archive in [../skills/FINDINGS.md](../skills/FINDINGS.md) §44.3 (the whole enum: 0 block, 1 dodge,
2 fail, 3 miss, 4 obstructed, 5 stray; `agents.ATTACK_FAIL_REASONS` carries it). So three of the
hostiles' swings at the Ranger came back as dodges; which mechanic produced them — the word
names the outcome, not the cause — is not scored here and the server sends no reason 1 today.
Corrected 2026-09-14 (a desk grep, no run). The walk step:
39 leads, cadence p50 0.61 s (p10 0.50, p90
1.06) against F28's 0.51; the abeam offset needs the player's reports joined and was not scored.

### What this settles, and what it queues (JARIN-S)

Retail's hero is the player's own message set addressed to a second agent, plus `0x0072` and the
party build; everything the heroes study authored blind is now either witnessed or refuted.
Queued for a server arc, each with the wire above as its floor: (1) the rig in retail's order —
the character block for the hero, `0x0072` before the build, **no `0x0074`** (heroes §11.3's
proof re-run under the new order); (2) `0x00CF`/`0x00D0`/`0x00E3`/`0x00E5`/`0x00E6` for a hero;
(3) `attack_speed_tick` deferred to the next attack start; (4) `0x0063 [hero, 0]` at the locked
target's death; (5) no slot offset on the party flag for a lone hero; (6) the wipe → shrine
teleport, the body re-created, full health, penalty kept, no `0x01D8`; (7) the death penalty
cleared on an outpost load; (8) `0x0026` 8/9 on a body's death and rise; (9) the hero's aiMode
persisted into the next instance's `0x0072`. Left open: Frenzy's doubling (a player run), the
hostile-target rule (n = 5), reason 1, the abeam offset, Healing Signet's shape. *(2026-09-14:
the hostile-target rule and the abeam offset closed in F40.2; reason 1 was "dodge" all along —
skills §44.3, corrected in 39.8 above. Open: Frenzy's doubling, Healing Signet's shape. 2026-09-14 night: Healing Signet's shape shipped in F41; Frenzy's LOOPBACK half observed in F44; retail's half OBSERVED on the owner's live run in F45 — NOT a double, the 38888 row's 175…125 % at Strength, shipped as H17.)*

## SLICE-F40 — **JARIN-S: the hero tape's corrections, shipped — retail's rig without `0x0074`, the hero's pools and skill family on the wire, the resend with the start, the lock cleared at the kill, the wipe to the shrine, the zone carry**

**The owner (2026-09-14):** *"go"*, to SLICE-F39's queue of nine. Shipped the same day, each
behind a measured default with its pre-JARIN arm as the revert flag; the floors are the tape's
(`20260914T005758`) and the corpus's where a count existed. **One thing measured after the fact
first:** MANTID-S's `effect_list_visible` kept the effect list "for a hero, for want of a
witness" by reading a `hero` key on the body row — **and no row ever carried that key**, so the
branch had never fired. The tape witnessed the hero's list (24 applies); the body's create entry
now carries `hero = <index>` and the branch is live. A shipped arm nobody could reach is the
defect class `studies/method` names, from the other side.

| # | correction | the wire it copies | flag |
|---|---|---|---|
| 1 | **The rig in retail's order.** `hero_character_block` — `0x0037`, `0x00B7`, `0x00DA` (the hero's OWN bar, not the player's), prop 41, prop 42, `0x009C`, prop 36, `0x00A6`, `0x003A` — then `0x0072` (with the carried aiMode), both queued AHEAD of the player's create; the body (a field) after it; the party build LAST; **no `0x0074`**. The four legacy sites (vitals, attribs, bar, the last `0x0072`) stand down under it | 37.73 s, 87.21 s, 651.62 s: three instances, one order, 0 `0x0074` | `--hero-rig-legacy` |
| 2 | **A hero's family on the wire.** `hero_pool_gain` (`0x00CF [hero, 25]` per hit landed, `[hero, units]` per hit taken, BEFORE the damage word), `hero_pool_clear` (`0x00D0` at Final Thrust and at death), `hero_skill_messages` (`0x00E5 [hero, skill, 0, recharge]` then `0x00E3` at the completion) and `hero_recharged_tick` (`0x00E6` when the recharge runs out); nothing for a henchman or a hostile | 107 / 7 / 35 / 48 on the hero; 0 on eleven henchman bodies; the `0x00E3` "6 of 6 name the player" note corrected | `--hero-silent-pools` |
| 3 | **The attack-speed resend rides the next start.** `attack_speed_tick` records the changed pair; `attack_speed_flush` sends it in the instant of the agent's next attack start (the player's swing and attack-skill sites, `start_swing`, the ally and hostile attack-skill announces); nothing at the apply, nothing at the close | 19 of 19 with a start; six out-of-combat applies sent nothing | `--attack-speed-at-change` |
| 4 | **The lock is cleared at the kill.** `hero_locks_release` in `kill_agent`: `0x0063 [hero, 0]` and the order dropped | 443.85 s, 0.57 s after the killing Final Thrust | (with `--party-ignore-commands`) |
| 5 | **A lone hero walks to the party flag itself.** `party_flag_point` returns the flag when the party has one body; the slot offsets stay for a group | the lead ended 0.0 u off the flag, 463.51 s | — |
| 6 | **The wipe.** `player_revive_due` with a party: a live body that can resurrect means NO timer; everyone down (or the live ones without a resurrection — this server's placeholder, said so) means `wipe_to_shrine` `WIPE_RESURRECT_AFTER` = 11.4 s after the LAST death — `0x0025` and `0x002C` for the player, every body `0x0021` + `0x0020` + `0x006D` at the shrine (`shrine_x/y/plane` on the map row, else the instance's spawn), everyone raised at full health with the maxima kept, the flags bytes 5 and 9, no `0x01D8` | 340.21 s; the median of 10.0 / 12.2 / 12.8 / 10.6 s on four tapes | `--no-wipe-shrine` |
| 7 | **The penalty clears on an outpost load.** `zone_carry_apply`: morale, its bank and the heroes' morale carried into a FIELD only | `0x009C [·, 100]` for both at 651.62 s after 71 / 72 in the field | `--no-zone-carry` |
| 8 | **The flags bytes.** `0x0026 [player, 4]` closes `kill_player`'s tick, `[player, 5]` the rise; a body's rise `[body, 9]` (its death already sent 8); **and `kill_player`'s order is retail's** — status, the morale tick, the hold, `0x002D`, `0x00D0`, the flags — where the hold and the cancel had ridden between the status and the tick (`test_morale` §5 had been red on it) | 3 of 3 player deaths and rises; 250 body rises; MANTID + JARIN for the order | — |
| 9 | **The stance persists.** `zone_carry_store` at the transfer, keyed by character uuid; the next instance's `0x0072` carries it | Avoid at 510.66 s, `[6, 324, 157, 2]` at 651.62 s | `--no-zone-carry` |

**A hero's morale, per hero.** `hero_morale` / `hero_morale_apply` / `hero_death_tick` /
`hero_morale_experience`: the hero's own −15 at its death (`0x009C [hero, 85]`, `0x00D0`, prop
41, `0x00A2 [43, hero, 0]`, prop 42, in the tape's order), its own bank buying it back with the
kill's XP, its maxima scaled from `base_max_health` / `base_max_energy` on the row (140 → 119 →
101 on the tape); the load block declares them at the carried morale.

**What the tape did to the corpus tests, and what each re-pin found** (the "corpus counts
redden on confirming evidence" rule, six suites):

- `adrenjoin.whose_agent` / `henchjoin.whose_agent`: property 41 is no longer unique on a hero
  tape; the kind-5 create (the fourth word 5 on the observer, 9 on a body) breaks the tie.
- `adrenjoin.scan` gains a third arm, **hero**: a `0x00CF`/`0x00D0`/`0x00D2` naming an agent
  whose OWN `0x00DA` is adrenal. `test_adrenwire`: the census is 1028 / 37 / 59; **three 207s
  above 25 (26, 29, 42)** — a landed hit and a hit taken summed into one tick on the hero, so the
  25 ceiling holds per event, not per message; the sub-strike tail doubled (a 2-unit bite per
  skale swing at 140 health); the spend skills gain the hero's 348 ×7, 382 ×7, 385 ×5; a 207
  names an agent holding ONE of the connection's bars (the Ranger's had no adrenal skill, every
  207 on that tape was the hero's).
- `test_pools`: the Ranger under the penalty adds (3, 22) and (3, 19), the hero (2, 14) — the
  base-scaling rule at n = 4; **the hero's `0x00A2 43` rides one message AHEAD of its prop 41**
  in the block (3 of 3), the one orphan class; **skill 392 charged 14 of 15 — Expertise 1, WIKI's
  4 % per rank, floored**, named by (capture, skill); **the hero's property-41 sequences carry
  no leading 1** (the 1 is the observer's own); **the signet raise put the Ranger's energy at
  5 of 19 = 25 %** (WIKI, Resurrection Signet), where every shrine or timer rise is 1.0; and the
  (3, 19) rate is `f32(0.33 * 3 / 19)` with 0.33 in DOUBLE, one ulp under the oracle's f32-first
  spelling — the two differ on six candidate pairs and every earlier witness happened to agree
  with the oracle, so which spelling retail uses is now CONTESTED, one witness each way.
- `test_skilldamage` §12: the caster 54's skill 222 on the Ranger and on the hero spans two death
  penalties each (the maxima 140 → 119 → 99 / 101) and the hero's Frenzy — the join keys on the
  target, not on its current maximum, so those two pairs are several values by construction; set
  aside by name, a third would be a new fact. **(It came on 2026-09-16 and was the penalty
  split alone — F47: both this and the 43-before-41 exemption are signatures now.)**
- `test_agentlife`'s two load-path locks: `party_bodies_here(state)` now has six sites (the
  zone carry reads it); the town's `0x00A6` lock reads the load path and the block's labels are
  spelled so it still finds the site it was written for.

**Tests.** `test_mechanics` §7b rewritten for the start-time send (the tick records, the flush
sends one, a second start nothing, the close nothing until the next chain, a body's rides
`start_swing` ahead of its own start, both revert arms; floor 198 → 202). `test_agentlife` gains
the JARIN-S section (floor 502 → 522): the family on a hero row and not a henchman's, the
recharge once, the lock released at the kill, the lone hero's flag, the hero's death tick with
its maxima at 85 %, the rise's flags byte, the signet pre-empting the timer, the wipe's fifteen
messages and the placed bodies, the carry into a field and into a town, the block's order with
and without a level, and a source lock on the rig. `test_guards` §6 counts the flags byte.
`test_pools` 108 → 128, `test_adrenwire` 73, `test_skilldamage` 58, `test_morale` 62 (green
again), and the untouched readers: effects 84, castcycle 51, killwindow 21, population 75,
dispatch 45, cancelwalk 124, playerswing 176, castcancel 44, srclint 26.

**Left, said so.** The signet's 25 % energy on the raised player (measured; `revive_player`
still refills to full — a `restore_player_energy` fraction is the change). Frenzy's double
damage (a player run). The hostile-target rule at n = 5. Whether the client draws Koss's
recharge from the new family, tolerates the rig in retail's order (the heroes study's crash
was under OUR order; retail's puts the block before `0x0072` and `0x0072` before the build,
which satisfies both of `HERO_ACTIVATE_FIRST`'s constraints) and stands the party up at the
shrine — the next loopback run, `--party slice`.

### 40.1 On the client, the same day — the rig asserted twice, `0x0073 HERO_INFO` is the record's creator, and the retail rig then ran three instances clean

**The owner:** *"you drive the loopback."* Five harness runs, agent-driven, the slice party
(`--party slice`, Tahlkora on the level-3 Warrior), F32's walk (Ascalon City → the corridor →
back) with `--enemy --enemy-hit 0.02` so the fight in the corridor could not kill the leader.

| run | rig | client | result |
|---|---|---|---|
| `20260914T083127` | retail (F40 as shipped) | `run/2026-07-29` (38797) | **`Assertion: charHeroData` ChCliHero.cpp(199)** at the FIRST load, 08:32:12, in the `0x0072` handler (the dispatcher frame carries opcode 0x72) |
| `20260914T084043` | retail + the block's two `0x0065 [hero, 0]` and its `0x00A2 43` | same | **the same assert** — those are not the creator |
| `20260914T085004` | retail + **`0x0073 HERO_INFO`** ahead of the block | same | the town loaded, the portal fired, **then `pos.y <= worldDims.y1`** in the corridor's create handler — **not the rig**: this client's archive holds no corridor (the slice's authored map lives in `run/slice/Gw.dat`, build 38833; "NO NAVMESH" in the log), so the field had no terrain |
| `20260914T085446` | retail + `0x0073` | **`run/slice`** (~~38833~~ — a MIXED directory: its `Gw.exe` is **build 38797** by its own getter, `buildid.py --exe`; its `Gw.dat` is composed from the 38833 snapshot, `content/compose.toml` `dat_source`. Corrected 2026-09-14, quests §11.4 — the exe's build is what the server's manifest sentinel must match) | **PASS, three instances, no assert**: c1 the town (roster, no body), c2 the corridor (the body created, walking its slot), c3 the town again — the zone carry printed both ways |
| `20260914T090247` | retail + `0x0073`, `--map 168 --party-no-fight --enemy-hit 0.5`, `attack:90` | `run/slice` | the raiders killed Tahlkora (her tick: `0x00F1`, `0x00D0`, the regen stop, flags 8) then the player (status, hold, `0x002D`, `0x00D0`, flags 4 — no penalty tick, the map charges none) — and **one second later the client LEFT on its own**: c2s `0x0008` (its orderly-exit message, 131 in the corpus at every zone) and the socket closed, the final frame loading Ascalon City. The wipe never ran on the wire |

**What the corpus gave when asked properly.** Retail's town preamble carries, once per owned
hero in EVERY instance's load, `0x0073 [6, 3, 1, 0, 243282, 245053, [322, 382, 348, 1, 385, 2],
0, 0]` — Koss's index, level 3, Warrior, no secondary, a dword pair, his own six skills (the bar
less the account-unlocked Frenzy and the empty slot) — inside the player's own block after
`0x009C` and before `0x003A`; **41 across the corpus, every one hero 6**, at level 20 on the
2026-08 tapes (the same account's other character) where no hero was ever in a party and
`0x0074` never appears. It is `0x0074 MERCENARY_INFO`'s twin for a hero the character owns —
heroes §11.3's "what creates `charHeroData`" was answered `0x0074` under a rig that sent no
`0x0073`; retail creates it with this. Named `HERO_INFO` in `overrides.json` (witness, both
asserting runs), built by `agents.hero_info`, sent first in the retail rig. `HERO_RIG_0065`
keeps the block's two `0x0065` and the regen because retail sends them; what they do is
UNVERIFIED (the assert did not care).

**What the clean run showed.** The roster in the outpost reads **"Mo3 Tahlkora"** with the
commander button — the profession segment SLICE-H2c chased through the label builder now
arrives with the block's `0x00B7`/`0x00A6` for the bodiless agent, which closes H2c's residual
from the retail side. Koss's… Tahlkora's panel was not clicked (the crash heroes §15.3 named is
untested under this rig); the hero cast nothing in the 40 s corridor window (the standing
hostile did not reach the party), so the skill family on a client is still the owner's eye.

**Two things the runs cost.** (1) A crashed client leaves the loopback archive's
modification-in-progress bit set (`0x1C bit 0`) and the archive gate refuses the next launch;
the documented remedy (RUNBOOK, the drift section) — copy the clean `run-live` archive over
it — was applied and `dhbuild.py` re-audited. (2) The slice runs must pass `--exe
C:/gd/Rurik/vault/run/slice/Gw.exe`; the harness's build-38797 default has no corridor, and a
run that "zones" into a map the client cannot load asserts on the first create's bounds, which
reads like a rig defect and is not.

**The wipe, on the client, is the client's own defeat rule.** Retail's Plains wipe drew nothing
from the client but its heartbeat and one selection in the 10.6 s before the shrine; ours sent
`0x0008` a second after the last death and left. The difference is not the server's death batch
(the hero's and the player's ticks went out in retail's order) but what the client knows about
resurrection in the map: the Plains' load carried six gadgets with `0x0111`/`0x010E` states
and MANTID's shrine was a gadget whose "glow" the tutorial narrates, while the corridor holds no
shrine at all — and a party that cannot be raised returns to its outpost, which is what GW does.
So `wipe_to_shrine` stands on the desk (`test_agentlife`'s fifteen messages) and is unobserved
on a client; observing it needs a shrine gadget in the corridor (content, with its `0x0111`/
`0x010E` pair) and a server arm for `0x0008` that answers a defeated party's return with the
transfer it asks for. Both are queued, neither is this arc's.

### 40.2 Desk, after the client — the signet's energy, the joins with the hero counted, the shrine as a prop

**The owner:** *"go more desk work."*

**The raise's energy (shipped).** Retail's signet batch on the player (602.45 s): `0x009F [58,
hero, 0]`, `0x00A0 [20, me, hero, 152]`, `0x00E7`/`0x00E3 [hero, 2, 0]`, `0x00F1 [me, 0]`,
`0x00A2 [43, me, rate]`, `0x009F [8, me, 0]`, **`0x00A2 [52, me, 0.2632]` = 5 of the 19
maximum**, `0x009F [54, me, 5]`, `0x00A2 [55, me, 1.0]`, `0x0026 [me, 5]` — WIKI's "100% Health
and 25% Energy", where every shrine or timer rise in the corpus carries 1.0 (the wipe's own,
340.21 s: `[43]`, `[8 = 0]`, `[52, 1.0]`, `[54, 22]`, `[55, 1.0]`). Shipped: `[skill_effect.2]`
carries `resurrect_energy = 0.25`; `resurrect_target` threads it to `revive_player` /
`revive_party_body`; `restore_player_energy` takes a fraction, sets the pool to it
(`EnergyPool.set_fraction`), floats the callout at what was handed back, and sends **the rate
before the gain** — retail's order, where ours had the rate last; the deferred-refill arm
carries the fraction across its tick. A hero's rise now sends its `[43]` and `[52]` too (the
shrine's `[43, 30, 0.039]`, `[52, 30, 1.0]`). `test_agentlife` +3 (floor 527).

**The joins, re-run with the hero counted** (`henchjoin.party_of` now admits a `0x01C2` hero with
its `0x00B7` profession; `whose_agent` breaks the property-41 tie):
- `--fight`: **97 party opening starts, 82 followed the leader's inside 6 s, p50 0.52 s** (F30:
  77 of 89, 0.50 s) — JARIN-P3 CORROBORATED at n = 97; the Warrior hero's chase names its foe
  (`0x002A`, 25 of its 35), a level-3 Warrior's swing lands 3.6 % of the foe's maximum (n = 52).
- `--hostile`: **76 opening starts; the lowest-base-armour set 62 of 76** (F29: 51 of 58),
  the nearest of that set 52, last-hitter 20 — F29's rule survives the Ranger tape, which is
  where its misses gather (the Ranger was T at rank 1 in 12); JARIN-P8's "REFUTED at n = 5"
  is the tail of an 82 % rule, not a rival to it. `hostile_target` stands.
- the formation: **Koss's leads end 187 u p50 from the Ranger, 150 ahead and 100 abeam** (n =
  158), where the eleven henchmen sat −73…+66 along at ~100 abeam — a melee hero runs AHEAD
  of a ranged leader. Cadence p50 0.58 s (F28 0.51), 2 halts against 193 leads (the two attack
  reaches). JARIN-P16's abeam half, measured: the shape is F28's, the slot is not.

**The shrine is a prop, not an agent.** The Plains' load carries no kind-3 create at all
(kinds on the tape: 0 ×52, 1 ×6, 5, 8, 9 ×134); what it carries is **six props** — `0x0111
[id, 0, 1|0]` + `0x010E [id, 16|9, 3]` for 54727, 63755, 49862, 62939, 64234, 47069 — and
**one flipped to state 1 at load, `0x010E [63755, 1, 0]`**, the same shape as MANTID's gate
opening (`[24771, 1, 0]`). The tutorial's props (six, `[id, 1, 1]` at 118.7 s, two back to 0
at 310.1 s) share an id with the Plains (54727). A resurrection shrine is therefore a **prop
in the map file** whose state the server flips, and the corridor's authored map has no prop
table — which is why the client asked to leave on the wipe (40.1) and what a shrine for the
corridor would take: a prop entry in the map (the presentation gap's territory), then the
pair at load. Which of the six is the shrine near (18527, 1372) cannot be read off the wire;
`0x0111`/`0x010E` carry no position. Recorded, not shipped. **Withdrawn as the wipe's blocker
2026-09-14 (F43):** the client left because it was told no COUNTDOWN, not because the map had
no shrine; told `0x0180 [0x575, 5, 0, 10000]` it waits and stands up in the corridor. And the
shrine batch shows the gadgets as kind-3 AGENTS the server creates (`0x0020 [9, 34, 3, …]` at
(18493, 1306) with `0x0111 [63755, 0, 0]` / `0x010E [63755, 1, 1]`, 60 u from the rise point),
so a visible shrine is a server-created agent plus a class id the map's own tables resolve —
not a props-chunk entry.

**Corrections on the way.** `studies/heroes/FINDINGS.md` §11.3 carries the retail creator
(`0x0073`); authsrv's "6 of 6 `0x00E3` name the player" and `effect_list_visible`'s "for want
of a witness" say what JARIN witnessed.

## SLICE-F41 — **the hero loop re-run after the sentinel change (green, every prediction met), and SLICE-H14: Healing Signet costs its caster 40 armour while it is used — WIKI only, the corpus has never seen the signet cast (2026-09-14)**

### 41.1 The loop, as a regression run — harness `20260914T115833`

Two things changed under the load path this morning (quests §11: the manifest's "no map"
sentinel per build; §11.4: the harness passing `--client-build` itself), so F40.1's clean
three-instance recipe was run again, agent-driven, predictions written first: `run/slice`,
`--map 148 --party slice --area errand,corridor --enemy --enemy-hit 0.02`, F32's walk
(`wait:6 S:2 wait:40 shot:1 wait:20 E:2.8 wait:12 shot:1 wait:15`, 97.8 s).

| predicted | measured |
|---|---|
| three connections on one process, 148 → 168 → 148 | `[c1] MANIFEST_DONE[0, map 148]`, `[c2] … 168`, `[c3] … 148` |
| the gamesrv banner reads the harness's flag | `[map] --client-build 38797 (given): the manifest's 'no map' sentinel is 888, the mission mask expected 112 bytes` |
| the hero's record in every instance, a body in the field only | `HERO_INFO(hero 3, level 3, prof 3/0, skills [281, 276, 2])` on c1, c2 and c3; `WORLD_CREATE_AGENT(200) hero body` on **c2 only** |
| the formation walk in the corridor | 6 × `walks to its slot` on c2; `walk4-shot.png`: Tahlkora with her staff beside the Warrior, the party panel reading `W3 Test Warrior / Mo3 Tahlkora` |
| the zone carry printed both ways | `[c2] ZONE: morale 100 and the hero stances carried into the field`, `[c3] ZONE: an outpost -- the death penalty is cleared (retail 0x009C 100); the hero stances carried` |
| no assert, no mask warning, nothing undecodable | `Gw.log` 0 asserts; 0 `MISSION_MASK is`; 0 undecodable |

OBSERVED on our own client (build 38797) against our own server. Nothing here is a claim
about retail; it is the claim that today's two load-path changes broke nothing the hero
ladder had proven.

**A label corrected on the way.** F40.1's table called `run/slice` "38833". It is a MIXED
directory: the exe is **build 38797** by its own getter (`buildid.py --exe`), the archive is
composed from the 38833 snapshot (`content/compose.toml` `dat_source`). The exe's build is
the one the sentinel must match, and the table now says so.

### 41.2 SLICE-H14 — the signet's armour, and why it is WIKI and nothing else

**The owner's queue** (F39's "left open": Healing Signet's shape; `content/world.toml`'s
"NOT modelled, said here: … Healing Signet's -40 armour"). GWW "Healing Signet" (read
2026-09-14, browser): infobox `causes2 = Decreased Armor Rating`; "You have -40 armor while
using this skill"; Notes: "-40 armor results in double damage from skills that are affected
by armor rating"; Anomaly: "the armor penalty from this skill is applied after the armor
cap and the effects of Cracked Armor and armor penetration".

**Asked of the corpus first, and it has nothing.** Over every live game connection, `0x00A0`
announces of skill 1 by property: **none** — prop 60 (the spell announce) names 2 (13×) and
281 (6×) and never 1; prop 50 (the attack-skill announce) names 322 (52×) and never 1; the
only `(·, 1)` pairs are property 38's attack-fail reason 1 (dodge, 39.8). Koss carried the
signet on the JARIN tape and never used it in view of the wire — GWW's own note says heroes
retreat from combat to use it. So there is **no retail hit landing under the penalty to
measure a ratio on**; 2 is the wiki's arithmetic (2 ** (40 / 40)) and the label is WIKI.

**Shipped.** `[skill_effect.1] armour_while_casting = -40` (content; provenance appended).
`casting_armour_penalty(state)` sums that key over the player's pending casts that have
BEGUN and not COMPLETED (`begin_at <= now < e5_at`, not cancelled, not `e5_sent`) — the
activation window, which is what "while using" is — and is ADDED to the capped rating at
the two sites that read one: `land_swing`'s location armour (the hostile's swing on the
player) and the NPC cast's `spell_ar` when the taker is the player. Added after the cap
because the wiki says so, never folded into the bonus `combatmath` caps. The hit log says
`while casting` when it applied. `--no-casting-armour` reverts. Bodies (a hero using the
signet) are NOT covered: their pending casts do not live on `state`, and no tape shows one.
`test_mechanics` §30 (floor 202 → 209): the swing inside the window is exactly double the
quiet swing at a pinned hit location; a completed, a queued-not-begun and a cancelled cast
cost nothing; a row without the key (Power Attack) costs nothing; the revert arm; the
penalty read off the row.

**Labels.** 41.1 OBSERVED (ours). 41.2 WIKI for the rule and the number; the corpus census
(0 of 19 prop-60 announces, 0 of 52 prop-50) is MEASURED; the implementation is a
RECONSTRUCTION on the wiki's stated order. What would change it: any tape with a hit on a
Healing Signet caster during the 2 s — the join is `hs_scan`'s shape, prop 60 → the next
prop-55 loss on the caster inside 2.5 s, against the same cause's other hits.

## SLICE-F42 — **H2d closed: the Party Search Heroes tab's frames are created by `0x0073 HERO_INFO`'s own worker, so JARIN-S had already fixed the assert — read statically, then pressed on the client (2026-09-14)**

**The residual** (F29's H2c note, ladder row H2d): pressing **P** in an outpost asserted
`heroFrame` (`PtSearchHeroList.cpp:160`) the moment a party hero row carried a profession —
harness `20260913T094444` (bodiless, the pair sent) and `094740` (the body in town) — and the
message that fills the tab's list was NOT FOUND.

**Static, on the pin (38797), stdlib plus `codescan`/`msghandler` for the disassembly.** The
three `:160` sites (`0x005688f3`, `0x00568d21`, `0x00568da9`, `asserts.py --file
PtSearchHeroList`) are one child-frame lookup, `0x6176c0(list, id)`, in three places of one
event dispatcher. Its jump table (`0x568e5c`/`0x568e70`, events `0x10000039 + i`) decodes to
exactly three live cases:

| event | case | what it does |
|---|---|---|
| `0x10000039` | `0x568d62` | **CREATES** the hero's child frame (`0x6175f0`, proc `0x571c20`) keyed by `*payload` |
| `0x1000003b` | `0x568d85` | looks the frame up → `:160` if absent → UI message `0x59` (refresh) |
| `0x10000114` (the party manager's rebuild, heroes §11) | `0x568dc9` → `0x568860` | walks every account-hero record (`0x80e2f0` → `charCtx[+0x2C]+0x584`, the `charHeroData` list) and looks each frame up → `:160` if any record has none |

So the tab asserts whenever an account-hero RECORD exists whose CREATE event never reached it.
Who posts `0x10000039`: one site in the image, `0x0081dc2e`, inside **`0x0081db20` — the
record-add worker** (`HeroDataAdd`, heroes §11.3): look the key up in the list at
`charCtx[+0x2C]+0x584` (`0x81d320`); if it exists, log and return (no event); else allocate
(`0x81d6b0`, `ChCliHero:245 heroData`), fill the record from the arguments (two five-dword
blocks among them), and `push 0x10000039; call 0x633d70`. Its one caller is `0x00811560`,
which **both** `0x0073`'s receive stub (`0x0091e270`) and `0x0074`'s (`0x0091e2f0`) call with
their fields as arguments (`msghandler.py 0x0073` / `0x0074`; the `0x0074` stub passes two
zeros where `0x0073` passes fields 8/9). `0x1000003b` is posted twice, from the `0x0072`
worker's region (`0x81d924`, `0x81dd0c` — the functions carrying `ChCliHero:199/245/291`).

So the create event fires on a record's FIRST creation, through either message. That makes
the 09-13 asserts a rig-order or key question rather than a missing-message one — that rig
also reached this worker, through `0x0074` — and which of the two it was is UNREAD (candidates:
the record's key, `0x0074`'s first field under `--hero-bytes`, disagreeing with the hero index
the roster's rows carry, so the rebuild looked up frames by a key no create had used; or the
record created after the window's dispatcher had already subscribed and rebuilt). What is
read is enough for the row: with JARIN-S's `0x0073` ahead of the block, the record is created
once, keyed by the hero index the roster uses, and the event posts.

**Pressed, twice, the asserting runs' own recipe** (`run/slice`, `--map 148 --party slice
--area errand,corridor`, `wait:10 P:0.3 …`), predictions first: no crash dialog, the window
opens, the Heroes tab lists Tahlkora.

| run | walk | result |
|---|---|---|
| `20260914T132429` | P, shot | Party Search opened on the Players tab; no crash dialog, `Gw.log` 0 asserts; `HERO_INFO(hero 3, level 3, prof 3/0, …)` on c1 |
| `20260914T132608` | P, `click:0.387,0.450` (the Heroes tab), shot | **the Heroes tab reads "Mo3 Tahlkora (Added)"** with Add Hero / Kick / Close; no assert |

OBSERVED on our client (38797) against our server. `0x10000039` as the create event and the
`0x0073` chain are OBSERVED (static); "JARIN-S fixed it in passing" is the two readings agreeing
and is labelled as such. Nothing shipped: the ladder row moves to DONE and heroes §11.3 gets
the line. Not read: what the two five-dword blocks in the record are (the wire's u32 pair and
skills are the obvious candidates; the copy is from arguments, not from the message directly).

## SLICE-F43 — **the wipe's leave was a missing COUNTDOWN, not a missing shrine: retail sends `0x0180 INSTANCE_COUNTDOWN [յ, 5, 0, 10000]` 0.58 s after the last death and rises at its expiry; shipped, and the party now stands up in the corridor with "Time until resurrection" on screen (2026-09-14)**

**Where this started.** F40.1 read the client's `0x0008` after our corridor wipe as "a party that
cannot be raised returns to its outpost", and F40.2 costed the fix as a shrine PROP in the
authored map — the presentation gap's territory. Both were wrong in the same way: nobody had
looked at the seconds between the last death and the leave.

### 43.1 Ours, to the tenth: the client waited 9.8 s and left with nothing said to it

Capture `gamesrv/authsrv-20260914T090314-c1` (F40.1's `090247` run): Tahlkora `KILL agent 200`
at 274.52 s, the player's killing blow at 289.64 s, then **only heartbeats** (`CLIENT_PERF` /
`LATENCY_REPORT` at 292.6 and 297.6) until the client's `0x0008` at **299.45 s — 9.81 s after
the last death**. Our `wipe_to_shrine` was due at 11.4 s. So the shrine batch, had it been
faithful to the byte, would still have arrived 1.6 s after the client had gone.

### 43.2 Retail, to the tenth: a countdown at +0.58 s, the shrine batch at its expiry

The hero tape (`20260914T005758`, the Plains connection): Koss `0x0026 [30, 8]` at 307.83 s;
the player's death batch at **329.64 s** (`[8, 29, 1]`, 41/42, `0x002D [29]`, `0x0026 [29,
4]`); at **330.22 s** — 0.58 s later — **three copies of `0x0180 [յ, 5, 0, 10000]`**; and at
**340.21 s** — 10.57 s after the death, 9.99 s after the countdown — the shrine batch: `0x017E
[]`, `0x00BA []` ×3, the gadgets re-created as kind-3 agents with their `0x0111`/`0x010E` pairs,
the hostiles removed, the player and Koss hard-set to the shrine (`0x002C`), both raised. The
client sent nothing but its heartbeat throughout.

`0x0180`'s string field is ONE coded code unit, `0x575`, on all seven ten-second countdowns in
the corpus; the other kinds the corpus holds are `[0x573, 5, 0, 12000]` ×4, `[0x576, 5, N,
30000]` ×4, `[0x7b56, 5, 0, 60000]` ×2, `[0x56b, 4, 0, 180000]` and `[0x569, 4, 0, 0]` ×3 — the
last at the 30-second ones' expiry, a clear. **And F40's "the delay is the median of 10.0 /
12.2 / 12.8 / 10.6" was never one number:** the 12.x wipes are the `12000` countdowns. The rule
is *rise when the countdown you sent expires*; which countdown a map gets is the server's.

### 43.3 Shipped, and pressed on the client

`GAME_SMSG_INSTANCE_COUNTDOWN = 0x0180`; `player_revive_due`'s wipe branch sends the countdown
once, `WIPE_COUNTDOWN_AFTER` (0.58 s) after the last death — three copies, the tape's count,
what each addresses UNREAD — and `wipe_to_shrine` fires at `WIPE_COUNTDOWN_MS` (10000) after
it; `WIPE_RESURRECT_AFTER` is now that sum (10.58 s), not a pinned 11.4. The label word is the
tape's code unit, committed as a string reference the client resolves. `test_agentlife` §7 (+2,
floor 529): the countdown and nothing else at 5 s, once per wipe, the rise at its expiry.

Harness `20260914T140406` (F40.1's recipe, `--enemy-hit 0.9`, the walk long enough for a
level-3 Monk to die under her own Orison), predictions first — three countdowns 0.58 s after
the last death, no `0x0008`, the party standing at 10.58 s:

| t (s) | measured |
|---|---|
| 274.56 | `KILL agent 200` |
| 293.78 | `KILL the player` |
| 294.39 | `INSTANCE_COUNTDOWN(10000 ms)` ×3 — +0.61 s |
| 304.41 | `the wipe: the player stands at the shrine (1536,1536)`, flags 9 / 5 — +10.63 s after the death, +10.02 after the countdown |
| 393.68 | the only `0x0008`: the harness's own teardown, 89 s later |

`walk4-shot.png`: both bodies standing, health 140, and a panel reading **"Time until
resurrection: 00:00"** — the client drew the countdown from our message and counted it down.

### 43.4 What this settles and what it leaves

- **Settled:** the leave was the client's own rule for a death with no countdown told;
  told one, it waits for the expiry. No shrine prop was needed for the party to stand up in
  the authored corridor. F40.2's "what a shrine for the corridor would take" is withdrawn as
  the blocker; it remains what a VISIBLE shrine would take.
- **Residual, cosmetic — then shipped in the same pass:** the panel stayed at `00:00` after
  the rise. Retail's batch opens with `0x017E []`, which `overrides.json` already names
  **INSTANCE_COUNTDOWN_STOP** (the client's own pairing with `0x0180`), then `0x00BA []` ×3
  (unnamed) before the re-instancing. `wipe_to_shrine` now sends the stop first
  (`GAME_SMSG_INSTANCE_COUNTDOWN_STOP`, `test_agentlife` §7 +1). ~~Its effect on the panel is
  UNOBSERVED — the run above predates it; the corpus's kind-4 `[0x569, 4, 0, 0]` at the
  30-second countdowns' expiry is the other candidate.~~ **OBSERVED the same night, §43.5:
  the stop takes the panel down.**

### 43.5 The stop, pressed on the client (2026-09-14, harness `20260914T155025`)

The same recipe as 43.3, the only change the stop at the batch's head; predictions registered
first (the 43.3 skeleton again; NO "Time until resurrection" panel on the post-rise shots; the
stop sent once, first in the batch):

| t (s) | measured |
|---|---|
| 253.48 | `KILL agent 200` |
| 272.24 | `KILL the player` |
| 272.85 | `INSTANCE_COUNTDOWN(10000 ms)` ×3 — +0.61 s |
| 282.87 | `0x017E` first, then `0x002C` the shrine, the two raises — +10.63 s after the death, +10.02 after the countdown |
| 385.91 | the only `0x0008`: the harness's own teardown, 103 s later |

`walk4-shot.png` (~40 s after the rise) and `walk6-shot.png` (~65 s): both bodies standing at
health 140, the party window's two rows, and **no countdown panel anywhere on the screen** —
where 43.3's shot at the same step read "Time until resurrection: 00:00". So `0x017E` is what
takes the panel down; the corpus's kind-4 `[0x569, 4, 0, 0]` clear is a different countdown's
business (the 30-second ones) and is not needed here. Three of three predictions held. The
residual is closed; H15 is OBSERVED in full.
- **The gadgets** (`0x0111`/`0x010E`): their workers live in `Map` (`Map.cpp:1195` pathArray,
  `:2760` renderModels) and key on ids that recur across maps (54727 on the tutorial, Kamadan
  and the Plains) — a class id resolved against the map's own tables, not an agent id; the
  props chunk (`props.py`) carries no such id. A shrine that RENDERS is therefore still the
  arc F40.2 costed; the wipe no longer needs it.

**Labels.** 43.1, 43.3 and 43.5 OBSERVED on our client against our server (build 38797, the slice
archive); 43.2 OBSERVED on retail's wire (n = 1 wipe on this tape, the countdown shape n = 7
across the corpus); "rise when the countdown expires" is CORROBORATED by the 12.x wipes
matching the 12000 countdowns and by our client waiting exactly as long as we told it.

## SLICE-F6 — what the desk cannot settle

Carried so the next session does not re-read the same bytes hoping for more:

1. **The channel order** (SLICE-F2) — one probe, prediction registered.
2. **What a glow id MEANS** (SLICE-F3) — the same probe, if the colours are legible.
3. **Whether the glow can be cleared** (SLICE-F1) — the forwarder only ORs. A probe that
   sets a glow and then tries every plausible clear is a second run, not a desk pass.
4. **Whether retail sends any of this.** Zero occurrences in a 22,524-message corpus over
   twelve connections. A loopback probe measures OUR server driving a retail client, which
   is the right instrument for "does the client draw it" and no instrument at all for "is
   this what ArenaNet sends". Do not let a green loopback run get written up as the
   latter — that is `studies/method`'s standing weakness and this arc is not exempt.

## SLICE-F44 — **Frenzy's doubling, the loopback half: our `damage_taken_multiplier` reaches the client as exactly 2.0× on 11 of 11 hits inside the stance, drawn as −3 against −1 — and the harness gained a `skill:` mailbox because no scripted key press reaches the bar (2026-09-14)**

**What this can and cannot settle, said first.** F39.3's INCONCLUSIVE is about RETAIL — hits on
Koss inside Frenzy on the JARIN tape (3 or 5 hp, n = 27) against two hits outside, which cannot
separate a doubled 1–3 from a random 2–5. Only a live capture with the PLAYER using Frenzy can
settle ArenaNet's rule, and that is the owner's hand at human cadence (F39: "a player Frenzy run
can"). This section observes OUR rule (`content/world.toml` `[skill_effect.346]`
`damage_taken_multiplier = 2.0`, WIKI) on a real client, which until today was
`test_mechanics`-only.

### 44.1 Seven launches that pressed nothing, and why

Registered first: a lone level-1 Warrior (100 hp), the standing Hatcher at `--enemy-hit 0.03`
then `0.01` with `--no-enemy-skills` (its default bar's skill 312 took 46 of 100 and killed the
player before any press), Frenzy in slot 6 of the content bar, pressed twice.

| launch | how the press was sent | what the client sent |
|---|---|---|
| `155829` | `--walk "6:0.3"` (a held key) | nothing — and the run was refused before it: `key:` is an action, not a walk step |
| `160031` | `--walk "6:0.3"` | nothing |
| `160328` | `--actions "42:key:6"` (press_vk, real scan code) | nothing — the player was dead at the press (killed at 38.5 s) |
| `160607` | `key:6` ×2, `--enemy-hit 0.01` | nothing, player alive throughout |
| `160919` | `vk:0x1B` then `key:6` ×2 | the Escape produced a `0x0028` cancel and a `0x0047` — keys DO reach the game — and the 6s still nothing |
| `161346` | the 2026-07-29 build (whose `key:1` had produced a `0x0046` on 2026-08-22) | refused before launch: its archive's modification-in-progress bit was set; restored from `run-live/2026-09-01` per RUNBOOK's drift section (5 of 5 sampled MB identical) |
| `161545` | the 2026-07-29 build, `key:6` ×2 | nothing |

On every shot the chat window's input line reads "(Enter text here to chat)" from world entry
onward, before any press (`155829`'s shot at `wait:8`), and on `161545` the press moved the
chat tab to `# Team`. The digit goes to the chat UI, not the bar; what focuses the input at world
entry on this rig is UNREAD (the 2026-08-22 run's shot shows the chat window in its expanded
state with no input line, and that run is not reproducible today). Not pursued further: the
question was Frenzy, not the harness's keyboard.

### 44.2 The third mailbox: `skill:ID[,TARGET]`

`toolkit/harness/control.py` gained `SKILL_SLOT` beside `interact` and `attack`, with the same
contract and the same caveat: the server runs `handle_skill_press` — the very arm `0x0046`
lands in — with the payload retail's client sends for a self skill (`[0x8046, skill, 0, target,
0]`, the tape's `[380, 0, 0, 0]`), under the dispatch arm's own dead-player guard. Everything
downstream is real: the resource gate, `0x00E4`/`0x00E3`, the recharge, the `0x0042` episode,
the effect visual, the number the client draws. The KEY PRESS is what did not happen, and the
gamesrv prints that every time it fires. A walk verb and an action, for the reason `attack:` is
both. `test_harness` §mailbox +5 (floor 165 → 170).

### 44.3 The run (harness `20260914T162115`), predictions first

Q1 every swing outside the stance is `0.03 × armour_multiplier(location)` — a small set S;
Q2 inside it EXACTLY 2 × a member of S and never a member of S; Q3 after expiry back to S;
Q4 `0x0035 [player, base, 0.67]` at the open and `1.0` at the close; Q5 the player survives;
floor 3 hits inside and 3 outside.

| t (s) | measured |
|---|---|
| 25.27 … | Hatcher swings, `0x00A3 [16, 1, 10, −0.012968]` — the wire's own float, every hit |
| 28.23 | `HARNESS SKILL PRESS 346` → `SKILL_ACTIVATED_BROADCAST(346 via USE_SKILL)`, energy −5, recharge 4 s, `0x0042 EFFECT_APPLY(stance 346, 8.0 s)`, effect visual 601, `0x00E3` |
| 29.40 – 34.90 | five hits at `−0.025937` |
| 36.23 | `0x0044 EFFECT_REMOVE(346, expired after 8.0 s)`; the next hit (36.28) is `−0.012968` again |
| 54.87 – 62.92 | the second press, six hits at `−0.025937`, the expiry, back to `−0.012968` |

- **Q1 held, with S a singleton**: a level-1 Warrior's five locations all read AR 45 (the log's
  `struck the legs / boots / gloves / head / body, AR 45`), so every outside swing is the same
  0.012968 of 100 — 44 of 44.
- **Q2 held**: 11 of 11 hits inside the two windows are 0.025937, and 0.025937 / 0.012968 =
  **2.000000**; none is in S.
- **Q3 held**: the hit 50 ms after the expiry is back in S.
- **Q4 REFUTED as written, and the prediction was the stale one**: no `0x0035` went out at either
  open. F40's item (3) already moved the attack-speed resend to the NEXT ATTACK START (JARIN:
  "Frenzy's resend rides the next swing"), and this player never swung. The prediction was
  copied from H13's pre-JARIN shape; the code is right and the registration was wrong.
- **Q5 held** (63 hp at the second shot). Floor met: 11 / 44.
- **On screen** (`walk4-shot.png`, 2 s after the first press): Frenzy's icon in the effects bar,
  **−3** over the player where the outside hits draw −1 — the client renders 2.594 as 3 and
  1.297 as 1 from the fraction alone.

### 44.4 What this settles and what it leaves

- **Settled, OBSERVED on our client**: the taker's-episode multiplier reaches the wire as an
  exact ×2 of the same swing and the client draws it; the stance opens, holds 8.0 s, and
  expires on the client from our messages alone. The harness can now press any skill for the
  player in a scripted run.
- ~~**Still open, and only a live capture closes it**: whether RETAIL doubles — F39.3 stands.~~
  **Closed the same night, F45: it does not; 175…125 % at Strength, shipped as H17.**
  The recipe for the owner: Frenzy on the bar, one foe, hits before / inside / after, at human
  cadence; the same script as this section scores it.
- **Labels.** 44.3 OBSERVED on our client against our server (build 38797, `run/slice`);
  44.1 OBSERVED (seven launches, one rig); the 2.0 itself is WIKI, unchanged; the chat-input
  focus is UNREAD.

## SLICE-F45 — **WARRIOR-PRE, the owner's live run: retail's Frenzy is NOT a double (0 of 18 hits inside the stance where a double puts them; the client's own 38888 row says 175…125 % at Strength, shipped as SLICE-H17), Healing Signet's −40 armour holds on 5 of 5 hits inside the cast, the quest turn-in is on tape for the first time, and pre-Searing's death countdown is ONE copy 2.3–2.6 s after the kill (2026-09-14)**

**The run.** `vault/captures/live/20260914T180058`, plan `vault/plans/warrior_presearing.txt`
(sealed, sha `c8cd5bc9…`), 21 marks and 9 notes bound with 0.0 ms of two-clock drift, notes in
the capture's `notes.txt`. The owner's pre-Searing Warrior ("Big Wariora", agent 31 on the
field connection; bar `[346, 1]`), Ascalon City → Lakeside County, five game connections (the
town, the field, and three map travels home). What the owner did that the plan did not say:
the quest was one already in the log and was turned in DURING `zone` (note 2); the `baseline`
fight ended in a death because the foe would have taken three minutes (note 3); the return
was a map travel (note 9).

### 45.1 Frenzy: the double is refuted, and the client's table was right

Five stance episodes on the wire, every one opened by the client's `0x0046 [346, 0, 0, 0]` and
answered `0x00E4` / `0x00E5 [346, 0, 4]` / `0x00E3` / `0x0042 [me, 346, 0, 3, 8.0]`, closed by
`0x0044 [me, 3]` at 8.0 s — windows 357.6–365.6, 365.7–370.0 (cut by the death), 433.1–441.1,
441.5–449.5, 451.5–459.5. Damage on the player is `0x00A3 [16 | 17, me, foe, −f]`, f rounded
to a hundredth of max health:

| | foe 80 | foe 81 |
|---|---|---|
| outside (prop 16) | 0.02 ×26, 0.03 ×30, 0.04 ×1, 0.05 ×2, 0.06 ×1 | 0.02 ×4, 0.03 ×8, 0.06, 0.08 |
| outside crits (prop 17) | 0.05 ×12 | 0.05 ×2 |
| inside the stance | **0.05 ×13, 0.03 ×4, 0.06 ×1** | **0.05 ×5, 0.12 ×1** |

A double sends the 0.02 pool to 0.04 and the 0.03 pool to 0.06: **0 of 24 inside hits read
0.04, and 0.06 appears once.** 175…125 % sends 0.02 → 0.03 and 0.03 → 0.05 — exactly the two
values that fill the inside column (22 of 24). REFUTED: `damage_taken_multiplier = 2.0`
(F39.3's INCONCLUSIVE is closed on the player, not the hero). What the tape cannot give is the
rank: no attribute message (`0x003A`/`0x003B`) rides any of the five connections, so the
percent the tape ran at is between 175 and 125 and the client table's Strength scaling is the
witness for the shape. The 38888 row (`skilltable.py`, diffed against 38797): attribute 51 → 17,
bonus 0/0 → 175/125, everything else equal; 145 of the table's rows moved between the two
builds (114 in the corpus set), among them Sever Artery 4 → 3, Gash 6 → 5 and Final Thrust
10 → 8 adrenaline with its scale 1 → 5 — content follow-ups, not shipped here.

**The rank, from the owner (2026-09-14, after the scoring): Big Wariora is Strength 0, so the
stance was 175 %.** That turns the ranges above into a point, and the point says one more
thing. Every one of the 112 hits on the player is an EXACT hundredth of max health (max
distance from a hundredth 0.0 over the tape; `0x009F [42, me, 100]` at load), so the wire
carries integer hit points over 100: outside the stance the foes hit for 2 and 3; inside, 2 ×
1.75 = 3.5 arrived as **3** (four of four, never 4) and 3 × 1.75 = 5.25 as **5**. Retail
TRUNCATES the multiplied damage to a whole point before it goes out; round-half-up would have
sent 4, round-half-even would have sent 4. Our wire sends the float (a 2-point swing under
Frenzy at Strength 0 goes out as 0.035 of max and the client draws −4), so **DAMAGE-INT — the
integer truncation at the send — is registered as the next desk item**, not shipped here: it
touches every damage path and the tests that pin fractional numbers, and it wants the corpus
asked first whether every retail damage word is an integer over its taker's max (this tape: 112
of 112). **Asked and shipped the same night: SLICE-F46 / H18.**

**Also on the tape, as F40 said:** `0x0035 [me, 1.75, 0.67]` rides the NEXT attack start after
each press (358.89 with the `[4, me, foe]` start, 1.3 s after the 357.59 apply; 365.92), and
the close `[me, 1.75, 1.0]` comes with the first start after the last expiry (472.43). Nothing
at the press itself.

**Shipped, SLICE-H17:** `[skill_effect.346]` is the client's own row — `damage_taken_percent =
[175, 125]`, `damage_taken_attribute = 17`, `source = "client-table"`, build 38888 — and
`episodemods.taker_damage` scales by the TAKER's rank in that attribute (`taker_rank`: the
player's from `[player.attributes]`, the one row the player is not in `state["agents"]`; a
body's from its own), rounded to a whole percent the way `skill_scale_value` rounds every set.
The slice player (Strength 9) takes ×1.45 where it took ×2. `test_mechanics` §3 derives the
number from the fixture's own rank and sweeps 0/3/9/15 → 175/165/145/125 (floor 209 → 211).

### 45.2 Healing Signet under fire: −40 armour, 5 of 5

Four casts (`0x0046 [1, 0, 0, 0]` → `0x00E4`, `0x00E5 [1, 0, 4]` exactly 2.0 s later, `0x00E3`,
`0x00E6` 4 s on), each landing `0x00A3 [55, me, me, +0.82]`. **No `0x00A0` prop-60 announce for
the signet** — the corpus's "0 of 19 prop-60 announces name skill 1" stays true because signets
are not announced that way at all; the activation is the `0x00E4` family only. Hits that landed
INSIDE a cast (between the press and the `0x00E5`): 0.04 and 0.06 (cast 1, from foes whose
outside values were 0.02 / 0.03), 0.05 (cast 2), 0.05 (cast 3), 0.06 (cast 4) — every one at
twice the outside pool, none inside the pool. n = 5, one character, one armour: H14's −40 is
CORROBORATED on the wire. The heal 0.82 of max at every cast is the wiki's 82 at Tactics 0 if
max health is 100 (prop 42 reads 100 at load), which the tape does not confirm independently.

### 45.3 The turn-in, on tape for the first time

Quest 54, on the FIELD connection at 290–293 s: `0x0039 [76]` (the interact) → `0x007E` /
`0x0080` / `0x0081` (the dialog) + `0x009F [11, 76, 4]`; `0x003B [8402439]` (the option) → one
batch: **`0x004A QUEST_REMOVE_AND_UNLIST [54]`, `0x004C QUEST_DESCRIPTION [54, …]`, `0x004D
QUEST_SET_MARKER [54, pos, 0, 146]`, `0x0052 QUEST_REMOVE [54]` ×2, four server chat lines
(`0x005D` + `0x005E [1, 10]`), the next dialog (`0x007E` ×2, `0x0080`, `0x0081`), `0x009C [me,
100]`, `0x009F [11, 76, 5]` ×2, `[20, me, 7]`, `[22, 76, …]`, `0x00EE [0, 250]`, `0x00EE [10,
0]`, `0x0140 [2, 25]`.** Then the giver offered the next quest (`0x0049 QUEST_ADD [62, …]`,
`0x0051`, `0x0054`) and the client asked `0x0012 [62]`. **None of F16's five "completion
family" opcodes (`0x004E`, `0x006C`, `0x0096`, `0x0097`, `0x00FB`) appears** — they were names
guessed from the schema, and a quest hand-in is the remove pair plus the reward lines. F16's
one measured guess held: experience rides `0x00EE [0, delta]` (+250). Ours sends the removes
and the `0x00EE`; the `0x004A`, the `0x004C` re-send, the four chat lines, `0x00EE [10, 0]` and
`0x0140 [2, 25]` (25 of something — gold, UNVERIFIED) are the gap, recorded in
[studies/quests/FINDINGS.md](../quests/FINDINGS.md) §12.

### 45.4 Two deaths: one countdown copy, 2.3–2.6 s after the kill

`0x00F1 [me, 16]` at 369.95 → **one** `0x0180 [յ, 5, 0, 10000]` at 372.53 (+2.58 s) → `0x017E`
at 382.52 (+9.99 s after the countdown) with `0x002C [me, (−10822, −13648), 54]` and `0x00F1
[me, 0]`; the second death (569.23) the same shape at +2.29 / +10.00. F43's hero tape sent
THREE copies 0.58 s after the death; pre-Searing sends ONE, two seconds later. Rise-at-expiry
holds on both (10.00 s here to the hundredth). What the copy count keys on (party size? map?)
stays UNREAD, now with a second data point.

### 45.5 Labels

45.1's refutation OBSERVED on retail's wire (24 inside hits, 2 foes, one character); the
percent's shape is the 38888 client table (client-table) with the tape as the witness that it
is not 200; the rank is Strength 0 by the owner's word, which makes 175 % OBSERVED to the point
(2 → 3, 3 → 5) and the truncation OBSERVED n = 4. 45.2 OBSERVED, n = 5, CORROBORATES H14's WIKI row. 45.3
OBSERVED, n = 1 hand-in. 45.4 OBSERVED, n = 2. The hero ladder's last open item (F39.3) is
closed; what remains for Frenzy is our other bars' adrenaline rows against the new table.

## SLICE-F46 — **DAMAGE-INT: retail's damage word is a WHOLE number of hit points, truncated — 1,632 of the 1,668 words across the live corpus whose taker's maximum is on the wire are exact, the 36 that are not all sit where the taker's maximum moved, and ten words are exactly 0.0; ours sent the float and now truncates once at the send with the books rounded the same (shipped as SLICE-H18, 2026-09-14)**

### 46.1 The question, stated before the scan

F45.1 closed with a registration: retail's 2 × 1.75 arrived as 3 (four of four, never 4) and
3 × 1.75 as 5, so the multiplied damage is truncated to whole points — but that was one
character on one tape at one maximum (100). Before touching every damage path the corpus was
asked. **Prediction:** every `0x00A3` property-16 and -17 word whose taker's maximum is known
(a `0x009F [42, taker, max]` earlier on the same connection) is a whole number of points over
that maximum, 100 %; a taker with no maximum on the wire has all its words sharing ONE
denominator ≤ 3000, and that denominator is a plausible max health. **Refutation:** a known-
maximum word like 0.035 over 100 — 3.5 points — anywhere in the corpus. The float32 on the
wire carries a fraction of 100..1000 to better than a thousandth of a point, so "integer" is
|points − round(points)| < 0.01, and the check has no free parameter.

### 46.2 The census (scratchpad `dmgint_corpus.py`, the 24 live tapes)

| | words |
|---|---|
| damage words, property 16 / 17 | 2,143 (1,835 / 308) |
| taker's maximum on the wire | 1,668 |
| … exact whole points over it | **1,632** |
| … not | 36 — every one on `20260817T231139` |
| taker's maximum NOT on the wire | 475 — every taker fits one denominator |
| words exactly 0.0 | 10 |
| heal words, property 55 (known max / exact) | 825 (95 / 93) |

One tape, `20260817T175358`, is skipped: the reader wants a file the directory does not have.

**The 36.** All on the PvP-arena tape, takers 4, 7, 8 and 10, and every one of them is a whole
number of points over the OTHER maximum its taker carried on that connection: taker 7's
maximum is declared 555, 555, 555, 455, 555, 455 over the fight and its 0.1582418 is 88 over
555 or **72 over 455**; taker 8's 0.0288288 under a declared 455 is **16 over 555**; taker 10's
three words at 455.98–457.93 s are 81, 26 and 98 **over the 483** that `0x009F [42, 10, 483]`
declares at 458.15 s; taker 8 on the third connection has 31 over the 384 declared 0.9 s
later. So the maximum reaches the wire AFTER the words computed against it at least twice,
and moves between 555 and 455 without a `0x009F 42` at all for taker 7 (the −100 is an
enchantment's worth, not Deep Wound's −20 %, which would read 444). Which channel moves it in
between is UNVERIFIED; that the words are whole points over it is not in doubt.

**The 475 with no maximum on the wire** each fit one denominator, and the denominators are
max healths: 555 (363 words — the PvP tape's other bodies), 96 (36), 100 (31), 25 (12), 140
(7), 200 (7), 5, 70, 72, 6, 14, 90 (the pre-Searing bestiary's pools).

**The ten zeros.** Seven are on `20260819T132414`, every one from attacker 58 and every one
preceded by `0x009F [1, 58, 0]` on the same tick; the takers (217, 144, 137, 194) took whole-
point hits from other agents seconds either side. Retail's floor is **zero** points, and a
zero-point hit still gets its damage word. What attacker 58 was (a level-0 body? a pet?) is
UNREAD.

**Heals** are the same shape: 93 of 95 known-maximum property-55 words are whole points, and
the two outliers are taker 7 on the PvP tape at 687.55 s — 43 and 67 points over the 455 it
carried at that moment while the scan held 555.

### 46.3 Truncation, not rounding, and once

F45.1's four 3s and one 5 are the direction: round-half-up sends 4 for 3.5 and round-half-even
sends 4; only truncation sends 3. Whether retail ALSO rounds an intermediate — the armour-
scaled base before a stance multiplies it — is UNVERIFIED: outside the stance the foes hit for
2 and 3, inside for 3 and 5, and trunc(2 × 1.75) = 3 = trunc(2.28 × 1.75) both fit. The server
truncates ONCE, at the final number, which is the smallest change the tape derives.

### 46.4 What shipped (SLICE-H18)

`toolkit/authsrv/authsrv.py`: `_whole_points(dealt)` (floor for dealt ≥ 0; NaN and negatives
pass through so `_damage_fraction`'s refusals still see them), applied inside
`_damage_fraction` — the one function every property-16/17 send crosses — AND by each of its
six callers to the number they take off the pool, so the server's books and the client's bar
agree to the point: `hit_enemy`, both branches of `armour_ignoring_damage`, the body swing that
feeds `hurt_agent_row`, the enemy swing on the player, and skill damage. Heals are NOT touched
(integers on retail, 93 of 95, but a different path and a different commit — HEAL-INT is the
registered follow-on). The `if dealt > 0` guards stand, so a hit that truncates to nothing
sends NO word where retail sends a 0.0 in the one shape the corpus has (n = 10, one attacker);
that shape is read before it is copied.

Tests: `test_guards` §9 pins 3.5 → f32(−0.03) = `0xBCF5C28F`, 5.25 → `0xBD4CCCCD`, 0.7 →
`0x80000000` (−0.0) and the NaN/negative pass-through as literals (+4, floor 41 → 45);
`test_mechanics` §3's Frenzy swing is 14 off a 10 at ×1.45 (not 14.5) and §30's "exactly
double" reads `floor(2q) ∈ {2⌊q⌋, 2⌊q⌋ + 1}` — no free parameter, and the quiet 12 / casting
25 it sees is a 12.5 shown as 12; `test_skilldamage`'s Flare lands 36 (36.68 truncated);
`test_agentlife`'s party swing takes 11 off the foe (11.7 truncated). 211 / 530 / 58 / 45
green; `test_srclint` 26, `test_citelint` 50, `test_provlint` 19.

### 46.5 Labels

46.2 OBSERVED on retail's wire (n = 2,143 damage words, 825 heals, 24 tapes; the
scratchpad script is the extractor and this section is its record). 46.3's direction
OBSERVED n = 5 (F45.1); the intermediate rounding UNVERIFIED; the zero word's shape UNREAD
(n = 10, one attacker); the channel that moves a PvP maximum between declarations
UNVERIFIED. The 36 non-integers are NOT a refutation — each is a whole number over a maximum
its taker demonstrably carried — but they are the scan's limit, stated: "last declared
maximum" is wrong by one declaration at least twice on that tape.

### 46.6 HEAL-INT, the same night: the heal word is whole points too (shipped)

The owner: "do the HEAL-INT one too". The heal side of the census, asked on its own before
the edit (scratchpad `healint_corpus.py`; **prediction:** every positive property-55 word with a
known maximum is whole over it outside the PvP tape's moved maxima, and every taker without
one shares a denominator):

| | words |
|---|---|
| positive property-55 words, 11 tapes | 813 |
| taker's maximum on the wire / exact whole points | 85 / **83** |
| taker's maximum not on the wire | 728 |
| … whole over ONE denominator | 644 (480 ×218, 53 ×143, 555 ×92, 210, 169, 185, 48, 66, 427, 15 …) |
| … whole over TWO (a maximum that moved once) | 84 — PvP takers 100 (480 → 408), 93 (480 → 561), 102 (480 → 408) |
| words exactly 0.0 | 0 |
| negative property-55 words (armour-ignoring damage) | 12, all whole (18 over 96; 10 over 25; two over an unknown maximum) |

The two known-maximum outliers are taker 7 on the PvP tape at 687.55 s, 43 and 67 over the
455 it carried while the scan held 555 — 46.2's limit, not a refutation. No heal word is zero,
so whether a heal that truncates to nothing gets a word is UNREAD (none in the corpus).

**Shipped:** `heal_agent` truncates the amount through `_whole_points` AFTER the Deep Wound
cut and before the room is measured, so the wire, the number the client draws and the books
carry the same whole number; the known-bad `--no-overheal-number` arm truncates what landed,
since the room can be fractional. `test_skilldamage` §heal: a 70.4 (an 88 under Deep Wound's
×0.8) goes out as `0x3F333333` (0.70) and lands 70 (+1, floor 58 → 59); `test_mechanics` 211,
`test_agentlife` 530, `test_effects` 84, `test_guards` 45, `test_pools` 128, `test_castcycle` 51
green. OBSERVED, n = 813 heals, and the rounding direction is CORROBORATED by the damage
side only — no heal in the corpus sits on a half-point the way F45.1's 3.5 did, so truncation
(rather than rounding) for HEALS is the damage rule applied by analogy: UNVERIFIED in
direction, whole in magnitude.

### 46.7 ZEROWORD: a hit that lands for nothing still gets its word, and the word is −0.0 (shipped)

The owner: "do the 0.0 word one too". 46.2 counted ten damage words at exactly zero and
asked what shape produces them before copying it. Read off the two tapes that carry them:

* **The sign.** All ten are `0x80000000` — NEGATIVE zero, the damage convention's `−frac`
  with a zero numerator. `_damage_fraction(0.7, 100)` already produces exactly that (§9 of
  `test_guards` pinned it under DAMAGE-INT), so the wire shape was in place; what was
  missing was sending it.
* **`20260819T132414`, seven words, one attacker (agent 58).** Sixteen damage words from 58
  on that connection: nine hits of 10, 19 or 34 points over a 140 maximum, seven of −0.0.
  The split is exact and it is the CLOSE that tells them apart: every non-zero hit is
  preceded by `0x009F [46, 58, 0]` (`GV_ATTACK_SKILL_FINISHED` — an attack skill's strike)
  and every −0.0 by `0x009F [1, 58, 0]` (`GV_MELEE_ATTACK_FINISHED` — a plain swing).
  Agent 58's plain swings deal nothing, seven of seven, and its skills carry all its damage;
  what 58 IS (no level on the wire for it) is UNREAD. No heal word, no effect and no
  attack-fail word sits on the −0.0 tick, so it is not a block, a dodge or a conversion:
  the swing landed, for nothing, and got the trio's close plus a damage word of −0.0.
* **`20260913T210901` (MANTID), three words, three drones (26, 24, 18).** Each drone's
  other words on the level-1 characters are 1 and 2 points (`0.0115`/`0.023` over 87,
  `0.01` over 100) and its third is −0.0 — a swing whose damage after armour fell under a
  point and truncated to nothing (DAMAGE-INT's floor), still sent. Each rides the drone's
  `0x00A7 [drone, 3, 1]` attack frame like its 1- and 2-point neighbours.

So retail's rule, OBSERVED n = 10 on two tapes and two mechanisms: **a landed hit always gets
its damage word, and zero is a value the word carries.** What the client DRAWS for −0.0 —
a "0", or nothing — is UNREAD; it would take a harness run with the operator watching, and
nothing here depends on it.

**Shipped:** the two guarded sites — the enemy swing on the player and skill damage — send
the word when the hit landed with no conversion open, zero included (`dealt > 0 or
conversion is None`); the skill site's early return keys on "no fraction" rather than "no
damage", so a damaging skill that truncated to nothing is no longer printed as "fully
converted". The unguarded sites (`hit_enemy`, the body swing into `hurt_agent_row`,
armour-ignoring damage) already sent whatever the fraction was. **Not shipped, on
purpose:** the fully CONVERTED hit — a Reversal of Fortune that eats the whole swing — still
sends no damage word, because what retail sends there is UNREAD (no full conversion in the
corpus). `test_mechanics` §9: a 0.5-point swing sends `[16, player, foe, 0x80000000]` and
the pool stays 100 (+1, floor 212); `test_skilldamage`: Flare into a rating of 300 (1/64,
0.31 → 0) sends −0.0 and takes nothing (+1, floor 60). Twelve damage-channel tests green.

### 46.8 CONVWORD: the fully converted hit — the corpus cannot say, and the arm is shipped by analogy, labelled

The owner: "do the fully converted hit one too". 46.7 had left the Reversal-of-Fortune arm
alone on the claim that the corpus holds no full conversion. That claim had not been
checked; it is now, two ways, with the prediction stated first (a prevention heal — a heal
on the taker FIRED BY a hit — would show as a heal word on a taker under attack, with a
damage word on the same tick or none):

* **By the enchantment.** Every `0x0042 EFFECT_APPLY` in the 24 tapes, 177 of them, by
  skill: 160 ×60, 364 ×43, 346 (Frenzy) ×22, 348 ×17, 480 ×7 and singles — **no 307**
  (Reversal of Fortune) and none of its family. The player never carried one. Other
  agents' enchantments do not ride `0x0042` at all, so this rules out only the player.
* **By the heal.** All 813 positive property-55 words classified by what shares their tick:
  **659 + 86** self-heals and **25 + 25** heals from another agent close a CAST (`0x009F
  [58, healer, 0]` on the tick), and the remaining **18** are Healing Signet frames
  (`0x00E5`). Zero heal words share a tick with a damage word on their taker. The
  "aimed within 1.2 s" column — 86 + 25 + 6 heals on a taker that had a property-60
  announcement pointed at it — is the HEALER'S own cast announcement (`[60, healer, taker]`),
  not an attack, once read. Positive control: the search finds the 18 Healing Signet
  self-heals of F45.2 under their own frame, and the two-heal ticks of the PvP tape
  (`519.037 s`, agent 12 healed 0.29 and 0.076 by agent 9 on one cast close), so a
  heal-on-a-hit would not have hidden from it.

So: **no prevention heal exists in the corpus**, and retail's damage word for a converted hit
is UNREAD in the strict sense — a negative with its control, not an absence of looking.

**Shipped anyway, by analogy, and labelled.** 46.7's rule — a landed hit always gets its
damage word, zero included — is OBSERVED for two mechanisms (an attacker whose plain swings
deal nothing; a swing truncated under a point). A converted hit is a landed hit whose damage
went somewhere else, and the server had TWO arms for one wire event: a word for every landed
hit except the one Reversal of Fortune ate. It now has one: the enemy swing on the player
and skill damage send the word unconditionally — the remainder when the cap left some, −0.0
when it left none — AFTER the heal word ("healing occurs before damage", GWW). The skill
site's early return now catches only a skill with no damage number. `test_mechanics` §9's
pin FLIPS: it used to assert "NO damage message follows a fully converted swing" (a
RECONSTRUCTION with no witness, now known to have had none) and asserts instead one −0.0
word after the heal, and says in its own text that the witness is missing (floor 212
unchanged; twelve damage-channel tests green). Label: the WORD for a converted hit is
RECONSTRUCTION by analogy, UNVERIFIED on retail; the ORDER heal-then-damage is WIKI.

**SETTLED 2026-09-16 — RUN-SKILLS-RB, `20260916T213125`, [studies/skills/FINDINGS.md](../skills/FINDINGS.md) §48.7:** ten hits under Reversal of Fortune. Heal first (10 of 10), the enchantment stripped on the tick, then the damage word — the negative remainder when the cap left some (3), and **`+0.0` (`0x00000000`) when it left none (7)**. The analogy above had picked the graze's `−0.0`; retail spells the two zeros differently. Shipped the same day (`land_swing`/`land_skill`: `_f32(0.0)` on a conversion that left nothing; `test_mechanics` §9 flipped; `healjoin.conversions()` + `test_skilldamage` §13 lock it). The paragraph below is what settling it was going to take, kept as written.

**What settles it:** one live capture with a prevention enchantment on the bar and a hit
taken under it — Reversal of Fortune (307) or any "the next time you take damage" skill —
and then read the tick: heal word, and beside it a −0.0, a remainder, or nothing. Filed on
the live-run queue, not a harness item: our own server cannot witness retail.

### 46.9 What the client draws for a −0.0 word: a red **0**, no sign (harness `20260914T231303` / `20260914T231524`)

The owner: "do the −0.0 client draw one too if it's offline work". It is — the WORD is retail's
(46.7), the DRAW is the client's, and the loopback client is the retail binary — so this was a
harness question, not a live one, and 46.7 was wrong to file it beside the capture.

**Static first, as far as it went.** The `0x00A3` handler at `0x00813040` runs TWO switches
over the property id: the pool dispatcher at `0x00818210` (agentprops FINDINGS, the
`fmul [ebp+0xc]` arm into `0x00921510`, which is pure CharPool arithmetic — clamp and store,
no drawing) and a second, at `0x008130E2` (index bytes `0x0081328C`, arms `0x00813250`),
whose arms hand the RAW wire float and the cause to per-kind view routines (`0x007DFB60` →
`0x007F6E70`, which appends a kind-2 record `{cause +0x1C, value +0x20, pool +0x24, cause2
+0x28, flags +0x2C}` to the agent view via `0x007F5340`). The number is drawn from that
record later, by a consumer the static pass did not reach; no zero test sits on the path
read. RECONSTRUCTION from the disassembly, two calls deep, stopped there because the run
answers the question outright.

**The run, prediction first.** Two loopback sessions against our own server, the Hatcher
swinging at a level-1 Warrior (AR 45, ×1.297) with `--no-enemy-skills`, six screenshots each
at one-second spacing from 18 s (a swing every 1.375 s, so every shot sits inside a number's
lifetime): **control** `--enemy-hit 0.05` — 5 × 1.297 = 6.48 → 6, the wire `−0.06`; **treatment**
`--enemy-hit 0.005` — 0.65 → 0, the wire `0x80000000`. Predicted: the control draws a red
"−6" on at least one shot (the positive control the colour-null rule demands); the treatment
draws NOTHING. Refutation: a "0" or "−0" glyph where the control's number sits.

| run | wire, every hit on the player | on screen |
|---|---|---|
| `20260914T231303` control | `[16, 1, 10, −0.06]` × 51 (`0xBD75C28F`) | **red "−6"** rising over the player (`w001-step2.png`); by the third shot the player is dead — 6 a swing, 17 swings |
| `20260914T231524` treatment | `[16, 1, 10, −0.0]` × 66 (`0x80000000`) | **red "0"** rising over the player, NO minus sign (`w001-step2.png`, again at `w003-step6.png` with the hit flash); the orb reads 100 throughout |

**Prediction REFUTED: the client draws the zero.** A −0.0 damage word puts a red "0" on the
screen in the damage colour, exactly where a real hit's number goes, and drops the sign —
`int(−0.0)` is 0 and the formatter prints the integer's sign, not the float's. So on retail a
player under agent 58's swings (46.7) saw a stream of red zeros, and a level-1 character under
the MANTID drones saw a "0" among the 1s and 2s. OBSERVED on the retail client binary, n = 2
shots (treatment) with the control's "−6" on the same rig and framing.

**What it changes:** nothing on the wire — 46.7 and 46.8 already send the word — and it closes
the last question about zero. It also settles what a fully converted hit will LOOK like under
46.8's analogy: a blue heal number and a red "0" together, which is a visible claim a live
capture with Reversal of Fortune can now confirm or refute by eye as well as by wire.

### 46.10 PVPMAX: how a moved maximum reaches the observer — the status word moves it, and the explicit `0x009F 42` rides the observer's NEXT LANDED HIT (shipped)

The owner: "do the PvP maximum channel one too". 46.2 had counted 36 damage words on
`20260817T231139` that were whole only over the OTHER maximum their taker carried, and a
`0x009F [42, 10, 483]` arriving 2 s AFTER three words already computed over 483. Read on the
tape, prediction first (a max-health effect's edge in the agent's `0x00F1` status word moves
the maximum at once; the explicit 42 follows late or not at all):

**A false transition, caught before it became a finding.** A candidate list that held both
555 and 444 flip-flopped on every word, because 444 = 0.8 × 555 exactly — a 20-point hit over
555 is also a 16-point hit over 444. Re-fitted on the taker's two REAL maxima only, each word
reads one of them or both, and only the unambiguous ones mark a transition.

**The move itself is the status word.** Every real transition sits on a `0x00F1 [agent,
word]` edge: bit `0x20` (Deep Wound, `effects.py`'s isle decode) set at 631.14 / 687.39 /
756.07 / 543.28 s, and the next damage word on that taker is over 0.8× (480 → 384) or the
capped −100 (555 → 455: 20 % is 111, the wiki's cap binds — `deep_wound_reduction` already
had it from the wiki, now OBSERVED n = 4); the death that clears it (`0x10` set, then the
rise) restores the full maximum; and one rise-with-death-penalty (agent 10, 451.91 s) put its
next words over 483 = 555 − 72, which is 15 % of the 480 base — `morale.py`'s own formula
(`total + base × (morale − 100) / 100`) to the point, on a hostile body; see 46.11 for what
that does and does not say about bodies.

**The explicit maximum is a different message with a different trigger.** All 27 non-player
`0x009F 42`s across the tape's four fighting connections share their tick with `[16|17,
agent, OBSERVER]` and the observer's own close (`[1|46, observer, 0]`), in the order **close,
`0x00CF` gain, `[42, agent, max]`, damage word** (632.47 s and 749.03 s printed in full); no
c2s message precedes them (the "client asked" hypothesis refuted, 0 of 16 with a consistent
request); and of the observer's 90 landed hits on one connection exactly 13 carry one —
**the observer's first hit on the agent, and the observer's first hit after the maximum
moved**, 4 of 4 Deep Wound edges (lag 1.31–1.33 s, one swing, when the player was already
on it) and every rise that changed the maximum (6–34 s, whenever the player next landed
one). Rises that left the maximum where it was (agents 9 and 10, no wound live at death)
drew no 42 on the next hit. Party members' hits on the same agents carry none (taker 8's
31/384 from agent 15 at 543.69 s, between the edge and the observer's 42). The player's OWN
maximum is the isle shape — same batch as the status word (`effects.py`; `0x0037` names
agent 25 there) — so the two rules are: **self, in the batch; others, on your next hit.**

**Shipped:** `hit_enemy` declares `[42, target, max]` between the player's gain and the
damage word when the target's maximum has moved since it was last declared
(`max_declared_on_hit`; a missing key counts as declared, because ours declares a body's
maximum at its create — a separate, measured decision — so retail's first-hit 42, its FIRST
declaration, is not duplicated). `deep_wound_open` / `deep_wound_close` no longer send a
body's 42 in the batch; they mark it stale, and the player's own keeps the isle batch.
`test_mechanics` §16: a foe's Deep Wound batch is the status word alone, the player's next
landed hit declares `[42, foe, 80]` before its damage word, the hit after it carries none
(+2, floor 212 → 214); the condition-heal check on a body no longer expects the restored
maximum in the heal batch. Twelve damage-channel tests green. Labels: the move OBSERVED
(n = 4 wounds, 3 rises, 1 death-penalty rise); the trigger OBSERVED (27 of 27, and the 13-
of-90 exclusion); the tick order OBSERVED (2 printed, 27 consistent); the death-penalty
arithmetic WIKI-consistent, unmodelled for bodies. What the CLIENT does between the edge and
the 42 — whether it scales the drawn number by a locally wounded maximum — is UNREAD and
would take the ZERODRAW harness recipe with a Deep Wound on the foe.

### 46.11 BODYDP: the death penalty on bodies — heroes get it on the wire and already do here; every other body gets NOTHING on the wire, and neither does ours (no change)

The owner: "do the death penalty on bodies one too". 46.10 had filed it as "WIKI, unmodelled for
bodies". Both halves of that were wrong in a useful direction, and the corpus says which
bodies the observer is ever told about (prediction stated before the scan: retail sends
`0x009C [agent, morale]` for every party member at its death, and re-declares its maximum at
`×0.85` of base; a hostile PvP opponent's deaths carry none in a DP-free arena):

* **The player's own** (control): `0x00EE [10, −15]` + `0x009C [me, 85]` + `[42, me, max −
  15 % of base]` on the death tick, then +1 per morale tick — MANTID 100 → 85 → 86 … 89;
  JARIN 140 → 119 → 120, second death 120 → 99 (`0x009C [29, 71]`); the isle 480 → 408.
  Pre-Searing: two deaths, no `0x00EE`, no `0x009C`, the maximum stays 100 — `map_death_penalty`
  already charges nothing there.
* **A hero** (`20260914T005758`, agent 30): its OWN `0x009C [30, 85]` and `[42, 30, 119]` on ITS
  death tick (307.83 s), +1 with the party's morale ticks (`[30, 86]`/120 at 410.8 s, `[30,
  87]`/122 at 534.5 s), and its second death `[30, 72]`/101. This is the JARIN batch
  `hero_died` already sends — `0x009C`, `0x00D0`, prop 41, `0x00A2 [43]`, prop 42 — and
  `hero_morale_experience` already walks each hero's morale up with the player's. DONE before
  this item was written, and now with the second death and the recovery ticks as witnesses.
* **Every other party body:** on `20260817T231139` conn `54071` the observer's `0x01BF` party
  is agents 12, 13, 14; **agent 12 died five times** (620.0 ×4 status words, 648.5) and the
  observer received **no `0x009C` and no `0x009F 42` for it, ever** — 0 of 5. The eleven
  henchman bodies across the corpus never die on tape, but their pools are never on the wire
  either (`hero_body_id`'s "0 on eleven bodies"), so a henchman's death penalty is a fact the
  server keeps to itself. Our server's `hero_died` returns early for a non-hero body and
  sends nothing: **the faithful shape, unchanged.**
* **Hostile bodies:** a hostile player's maximum moved by exactly `morale.py`'s formula once
  (46.10's agent 10, −72 of 555 on a 480 base) — CORROBORATION of the base-scaled rule on a
  third character, n = 1 — while on the other connection agents 7 and 8 died three times each
  and were re-declared at 555 after every rise, and the observer's `0x00EE [10, 40]` at
  634.75 s left its own maximum at 480. Two matches, two rules: WIKI names arenas without a
  death penalty, and which of these two is which is UNREAD (the map ids are not on the
  connection in a form this pass decoded). Nothing to model: this server has no hostile
  player bodies.

**Verdict: no code moves.** Heroes were done (JARIN), everyone else is silent on retail's
wire and silent here. `morale.py`'s docstring gains the hostile-body corroboration. Labels:
the hero's second death and recovery OBSERVED (n = 1 hero, 2 deaths, 3 ticks); the party
member's silence OBSERVED (n = 5 deaths, 1 body); the henchman case NOT FOUND (no death in
the corpus) and inferred from the pools' silence; the arena rule UNREAD.

---

## SLICE-F47 — **the Lakeside re-pin: the owner's aggro tape reddened two corpus locks on CONFIRMING evidence, and both exemptions are now signatures — the hero's 43-before-41 load block (4 of 4) and a death-penalty split that keeps 24 whole points across two maxima (2026-09-16)**

**Desk and corpus. No client run; nothing on the server moves.** The owner's Lakeside aggro
capture (`vault/captures/live/20260916T150306`, RUN-AGGRO-JARIN's successor, with Jarin in the
party) joined the corpus and two suite tests went red on `main` at `ced757ee`:
`test_pools` §2b (an unjoined property 43 the exemption list did not name) and
`test_skilldamage` §12 P2 (a multi-valued cast pair the exemption list did not name). The
"corpus counts redden on confirming evidence" rule says classify first: is the new row the
phenomenon the exemption already names, or a mechanism? Both exemptions were written in one
commit (`b7a78a3a`, JARIN-S, F40) from one tape, and both were NAME lists — a capture and an
agent, a caster-skill-target string — which is the shape that reddens on the very next tape
that confirms the claim. Both did.

### 47.1 The hero's rate rides one message ahead of its maximum — 4 of 4, the same block

The new orphan is agent 379 on the Lakeside town connection, at 0.760 s in the load block.
Read beside JARIN's hero 117 (F40, 0.825 s) the two blocks are the same message for message:

| offset | Lakeside `20260916T150306`, agent 379 | JARIN `20260914T005758`, agent 117 |
|---|---|---|
| 0 | `0x0037 [379, 6, 10]` | `0x0037 [117, 6, 10]` |
| 2 | `0x00DA [379, [322, 382, 348, 1, 385, 346, 0, 2], …]` | the same bar |
| 4 | **`0x00A2 [43, 379, 0x3D0A3D8A]`** — the rate | **`0x00A2 [43, 117, 0x3D0A3D8A]`** |
| 5 | **`0x009F [41, 379, 20]`** — the maximum, NEXT | **`0x009F [41, 117, 20]`** |
| 6 | `0x009F [42, 379, 140]` | `0x009F [42, 117, 140]` |

Same hero, same bar, same rate bits, same order. Across the whole corpus every unjoined
property 43 — JARIN's 30, 117, 324 and now 379 — has the one signature: **the very next
message is that agent's own property 41, at the same timestamp** (scratchpad `sig43.py`,
4 of 4, `dt = 0.0`). The player's own block never does this (Lakeside's observer 642: 41
first). `_scan_corpus` now classifies each orphan by that signature and §2b asserts that
no orphan falls outside it, with JARIN's three kept as the positive control — a fifth hero
tape passes on the signature, a rate that is genuinely unjoined still reddens, and the
assertion can no longer be satisfied by an empty orphan list. **OBSERVED (n = 4, two tapes,
one hero); label unchanged from F40.**

### 47.2 The death-penalty split, and it argues for F46

The new multi-valued pair is caster 48's skill 222 onto agent 29 on the explorable
connection, four hits:

| t (s) | fraction on the wire | target's maximum at the hit | whole points |
|---|---|---|---|
| 299.334 | −0.17143 | 140 | **24** |
| 306.598 | −0.17143 | 140 | **24** |
| 312.595 | −0.17143 | 140 | **24** |
| 366.460 | −0.20168 | 119 | **24** |

One value in points; the fraction moved because the maximum did (140 × 0.85 = 119, the
penalty). That is F46's claim — the word is whole points over the CURRENT maximum — landing
on a pair the P2 lock was built to refuse, and it is exactly the case JARIN-S's comment
predicted would be "a new fact": it is not one, it is the same fact with the second cause
removed. So the exemption is a signature: `spellhitjoin.score` names a `penalty_split` — a
multi-valued pair that is ONE value per target maximum across two or more maxima, every hit's
maximum known — and P2 sets those aside by rule. A new check (+1, floor 60 → 61) then asserts
that every such pair is one value in whole points, which is the check the new row can refute
and the name list could not.

**JARIN's two pairs do NOT pass the signature, and that is the honest reading of them.** The
Ranger's pair (54 → 29) holds −0.17143 AND −0.16429 at the one maximum of 140 — 24 and 23
points, cause unmeasured — and the hero's (54 → 30) holds −0.21311 AND −0.41803 at 122 —
26 and 51, Frenzy's intake (F44, F45). F40's comment called both "several values by
construction" of the penalty; the penalty is part of it and not all of it, so they stay
named, and the test's comment now says why. The 23/24 on the Ranger is a one-point residual
on one tape with no cause offered; it is a note, not a claim.

### 47.3 Method, for the next one

- `git log -L` on both checks → one commit, `b7a78a3a`, one tape. A name list written
  from one tape reddens on the second; write the SIGNATURE the first time.
- The census as of the previous pin (JARIN's 3 orphans, 2 pairs) against the census now
  (4, 3): the delta is one row each, both from the new tape, both matching the named shape.
- The whole-points view is NOT a clean corpus-wide invariant under `spellhitjoin`'s
  maximum join: the RA tape's Mind Burn pair (14 → 8, `20260817T231139`) reads −0.04865 at
  maxima 455 and 555, which is 22.1 and 27.0 points — the last-seen property 42 is not the
  maximum that fraction was computed over. That is why the signature is "one value per
  maximum", not "one value in points", and why the whole-points check is scoped to the
  split pairs. Not chased here; F46.2's census counted its exceptions the same way.

### 47.4 Labels

The 43-before-41 order: **OBSERVED**, 4 of 4, one hero on two tapes. The penalty split at
constant points: **OBSERVED**, n = 1 pair, 4 hits, two maxima. The RA pair's non-integer
points: **NOTED**, unread. Nothing shipped on the server; two locks re-pinned, `test_pools`
128 checks (floor 128), `test_skilldamage` 61 (floor 61), `test_srclint` green.

## SLICE-F48 — **MOVESPEED: retail's speed word read off 501 rows — a 33 % boost is × 1.33, Crippled × 0.5 and it MULTIPLIES a boost (× 0.665, 21 of 21), two boosts cap at × 1.34 (8 of 8), and every episode change re-declares — shipped for both signs, on by default, with the movement composite reading the declared base (2026-09-16)**

**The owner (2026-09-16):** *"let's do movespeed next, both positive and negative … 'Charge!'
… or Windborne Speed … both are probably already on tape somewhere."* They were: 80 applies of
the two, joined to their speed words, plus the Isle's Pin Down.

### 48.1 What existed

`speed_tick` (2026-08-22) declared the player's `0x0027` from a `"Movement speed increase"`
row, behind `--move-speed-effects`, **off by default** because "every REALFIX fence and
copy-model constant was measured at 288 u/s". Only Rush had a row. Shouts opened no episode
(`effects.EFFECT_TYPES` is the five definitional types), so "Charge!" was an icon nowhere;
Crippled was "not modelled" (F45's list); no body ever got a word; and `zeroleadcompose`
refused `--router` beside the flag because the router's chain ETA divided by
`DEFAULT_RUN_SPEED`. Two prior sessions' fear was correct and specific: **six** sites walked
the player's model at 288 whatever the client had been told — the sync lerp
(`_sync_position`), `router_next_due`, the arrival carry's ETA, `a2_leg_note`'s leg speed,
`model_leg_speed`'s base, and the agtrack guard's `RUN_SPEED × age` budget — so a boosted
body would have been modelled 25–33 % behind itself.

### 48.2 The reader first: `speedwords.py`, six predictions, all held

Every `0x0027 [agent, f32]` across the live corpus (**501 words, 17 captures**), joined to
the same-agent `0x0042`/`0x0044`/`0x00F1` inside the 60 ms batch shoulder, ratioed against
the agent's OWN base (the value its restores return to). Predictions in the module's
docstring before the scan; `test_speedwords.py` pins them as exposure floors:

| | prediction | result |
|---|---|---|
| P1 | 160 / 364 applied with nothing open → × 1.33 | **80 / 0** |
| P2 | 481 Crippled applied with nothing open → × 0.5 | **2 / 0** (27 words at 144.0 in all) |
| P3 | Crippled over a boost → × 0.665 = 1.33 × 0.5, MULTIPLICATIVE | **1 / 0 joined; 21 rows at × 0.665, 0 at the additive × 0.83** |
| P4 | a second 33 % boost over an open one → × 1.34 | **8 / 0** (never × 1.33 unchanged, never × 1.77) |
| P5 | the "Charge!" cure batch carries TWO words | **1 / 0** |
| P6 | bases are 288 and 300 | **324 / 154 words** |

The whole ratio table, against own base: × 0.34 (6, the MANTID tape, status 0xC00 — a
−66 % source), × 0.5, × 0.665, × 0.8 (2), × 1.0, × 1.13 (3), × 1.25 (4, one joined to skill
455 Storm Chaser), × 1.33, × 1.34, × 1.5 (5, one Lakeside body, no apply in batch — a
+50 % single source such as Dash), and 10 words of **0.0** (five Isle bodies at once, twice).

**The batch order, verbatim** (`20260818T094648`, agent 25): Pin Down's impact is `0x00CF
[25, 3]`, `0x0042 [25, 481, 13, 95, 13.0]`, `0x00F1 [25, 0x0A]`, `0x0027 [25, 144.0]` at
t = 183.755; the operator's "Charge!" at 185.532 is `0x00E4`, `0x00E5`, `0x00A5`, `0x0042 [25,
364, 10, 96, 10.0]`, **`0x0044 [25, 95]`**, `0x00F1 [25, 0]`, `0x00E3`, **`0x0027 191.52`,
`0x0027 383.04`** — the shout's apply computed over the still-open Crippled, then the cure's
restore; and Windborne over the open shout a second later is `0x0042 [25, 160, 15, 98,
13.0]`, `0x00F1 [25, 0x80]`, `0x0027 385.92`. So retail recomputes and re-declares at every
episode change, in the batch, behind the status word.

### 48.3 The rules, and whose they are

* **Boosts SUM and cap at +34.** WIKI (GWW "Speed boost", rev. 2020-05-09): "Speed boosts can
  be stacked, but movement rate is capped at 34% faster than normal"; OBSERVED × 1.34 on 8 of
  8 second-boost rows. A single source may exceed it (× 1.5 rows).
* **Snares sum and cap at −50, a single source may exceed.** WIKI (GWW "Snare (tactic)",
  rev. 2026-04-24); OBSERVED × 0.34 (n = 6). No content row declares a decrease yet, so the
  arm runs on nothing today.
* **Crippled × 0.5, multiplying the result.** WIKI (GWW "Crippled", rev. 2020-10-23: "you
  move 50% slower"); OBSERVED, and this is the arithmetic the wire settles — × 0.665 on 21 of
  21, × 0.83 on none.
* **Boost × snare: multiplicative, per the WIKI** (GWW "Effect stacking", rev. 2026-09-07:
  Flail with "Fall Back!" is 89.1 %). **CONTESTED by one body**, n = 3: a PvP body on
  `20260817T231139` conn 50513 read × 0.8 in its create batch — beside two `0x006F` item
  changes, which GWW "Bundle" (rev. 2018-05-08: "Some bundles … reduce movement speed") makes
  a bundle pick-up — and took "Charge!" to × 1.13 = 1 + 0.33 − 0.20, additive. A bundle's
  slow is not a skill snare and nothing here models one; the wiki's rule ships and the row
  is on record. UNVERIFIED which of the two a skill snare over a boost would follow.
* **A shout can open an episode when its row says so.** "Charge!" is a Shout (type 15),
  outside `EFFECT_TYPES`; the corpus witnesses 47 applies of it. The content door
  `effects.py`'s docstring reserved — `opens_episode = "shout"` on the `skill_effect` row —
  now exists, read by `apply_effect`; the type list is unchanged and `test_effects` still
  answers None for 364 by type. Its initial effect, `removes_condition = "Crippled"`, is
  OBSERVED once (the Isle's episode ends 11.2 s early in the shout's own millisecond).
* **The percent slot is the row's to name.** 160 / 364 / 319 carry it in the scale slot
  (33 / 33 / 25, bit clear), Storm Chaser 455 in the BONUS slot (25, its scale 1..5 being the
  energy gain) — `move_speed_terms` reads whichever slot the row names.

### 48.4 Shipped

* `episodemods.move_speed_terms` / `move_speed_factor` (the rules above; `move_speed_percent`
  stays for its readers). `authsrv.push_speed` sends one `0x0027` per CHANGE for the player
  and every body, from every site that opens or closes an episode — `apply_effect`,
  `apply_condition`, `effect_tick`, `remove_conditions`, `strip_effects` — right behind
  `push_status`, retail's slot; `speed_tick` is the per-tick backstop. Our cure batch is
  `[0x0042 364, 0x0044, 0x00F1, 0x0027 383.04]`: retail's order with ONE word, since ours
  computes the word after the cure rather than once either side of it.
* **The composite reads the declared base.** The six sites of 48.1 read
  `state["declared_speed_base"]`; `0x0027` to the player feeds `agtrack_guard.on_speed_base`
  (both copies' +0x5C, a pure store on 0x002B's footing — RECONSTRUCTION on the timing); a
  body's word feeds its own `_npc_model_emit`; the chase and the follow budget walk a body at
  `npc_declared_speed` (a crippled hostile closes at half). The `--router` refusal is
  retired with its reason, and `test_router`'s lock is inverted so a re-added gate reddens.
* **On by default; `--no-move-speed-effects` is the revert arm** (icons that move nothing,
  every body at 288, the pre-F48 shape).
* Content: `[skill_effect.160]`, `[364]` (`opens_episode`, `removes_condition`), `[455]`,
  and `[392]` Pin Down (`bonus_scale_means = "Crippled"`, 3→15 s), each with its GWW
  revision and its wire witness.
* Tests: `test_speedwords` (new, 12, floors on exposure), `test_mechanics` §8/§8b (214 → 228:
  383.04, 385.92, 144.0 behind the status, 191.52 and the factor 0.665 asserted not 0.83, the
  cure batch's order, the cap on the sum, a body's own word, the revert arm), `test_effects`
  §4d/§5 now expecting Rush's word behind its apply and expiry.

### 48.5 Live, on the client — RUN-MOVESPEED-1 / 1b (the boosts), agent-driven

Loopback, Isle of the Nameless (map 280), `--skills 364,160`, predictions registered before
launch (the session's `ms_runplan.md`; the suite green first, 208 of 212 with the three reds
classified — two corpus locks reddened by that morning's Lakeside capture on `main` too, one
source lock of this branch's own, moved). Instrument: the gamesrv tape's decoded `0x003D`
reports, which the client sends every ~512 u (1.4–1.8 s apart, not the 0.29 s the plan
assumed), so a leg's speed is `distance / dt` between consecutive reports.

* **RUN-1** (harness `20260916T191507`, tape `authsrv-20260916T191542-c1`; `W:5 skill:364
  W:6 skill:160 W:6 wait:14 W:5`): the shout at t = 9.03 s — `EFFECT_APPLY(shout 364 …
  8.0 s at rank 6)` (the loopback character's Tactics 6: GWW 5…13 → 8 ✓) then
  `AGENT_UPDATE_SPEED_BASE(the player, 383.04 u/s, x1.33)` in the same batch; its expiry
  at 19.27 s restored 288.00; Windborne at 21.52 s (rank 0 → 5.0 s ✓) declared 383.04 and
  restored at 26.56. **P1 and P5 held; P2 (the cap) was UNEXPOSED** — the plan's W:6 leg
  outlived the 8 s shout — and the body hit the Isle's east wall at 18 s (position frozen at
  (−2699, −2411) from then on), so the Windborne legs never moved. Speeds: plain leg 288.1 /
  287.9 / 286.0; boosted 372.8 / 379.4 / 377.1 / 367.5 (× 1.29–1.32).
* **RUN-1b** (harness `20260916T191835`, tape `authsrv-20260916T191905-c1`; `W:3 skill:364
  W:3 skill:160 W:3 wait:12 S:5`): **every prediction held.** 383.04 at the shout (9.03 s);
  **385.92 (× 1.34) when Windborne landed inside it** (16.33 s) — the cap on the sum, and the
  wire says so at once; **383.04 again when the shout expired under the enchantment**
  (17.04 s); 288.00 restored at Windborne's end (21.37 s). Plain leg 288.0 / 288.0; boosted
  370.5 / 378.5 / **383.9** / 370.7 / 377.3 / **383.4** — the two leg-ending intervals read
  the declared 383.04 within 0.25 %, the four full 512 u intervals sit 1.2–3.3 % under it
  (UNVERIFIED why; the plain legs read 288.0 exactly on the same instrument, so it is not
  the instrument's floor); the closing backpedal 187.8 / 187.6 = 0.66 × 288 (the family rate
  on the RESTORED base — at 383 it would read 253). **No `0x002C` of any kind in the run**;
  RUN-1's one was the pre-existing cast-stop pin at the Windborne press (0.75 s activation
  stops the body), not a snap. P3, P4 and P5 held on both runs.

**Labels.** The declarations OBSERVED on our own wire (n = 8 words, 2 runs), matching
retail's arithmetic to the byte; the client walking at the declared base OBSERVED (9 boosted
intervals, ratio 1.29–1.33; 2 at 1.331–1.333); the composite holding OBSERVED (0 re-pins over
2 boosted runs — a small n, and "nothing snapped" is a null on exposure, stated as such).

### 48.6 Live, on the client — RUN-MOVESPEED-2 (the snare and the cure), agent-driven

Same map and bar, `--enemy --enemy-skills 392` (the standing Hatcher with Pin Down alone on
its bar), `W:3 wait:12 W:4 skill:364 W:4`, hold 40 (harness `20260916T192119`, tape
`authsrv-20260916T192147-c1`). **P6, P7 and P8 all held**, and the run exposed a fourth
thing the plan did not ask for:

* **P6 — the inflict.** t = 2.02 s: `agent 10 strikes with skill 392` → `EFFECT_APPLY(Crippled
  on agent 1, buff 1, 13.0 s, inflicted by skill 392)` (the Hatcher's rank 12: GWW 3…15 → 12.6
  → 13 ✓, the Isle's own 13.0) → status word → **`AGENT_UPDATE_SPEED_BASE(the player,
  144.00 u/s, x0.5)`**, retail's batch in retail's order.
* **P7 — the client limps at half.** The crippled W:3 leg: two 0.5 s start-of-leg intervals at
  109.0 / 112.3, then the clean 2.0 s interval **288.3 u in 2.002 s = 144.0 u/s exactly**.
* **P8 — the cure.** t = 28.43 s, "Charge!" pressed while crippled: `EFFECT_APPLY(shout 364 …
  8.0 s)`, `EFFECT_REMOVE(buff 1, Crippled, REMOVED: skill 364's initial effect)`, the status
  word, **383.04** — one batch, and the next full interval reads **371.5 u/s** (× 1.29, the
  same figure as the boost runs).
* **The re-cripple under the shout, unplanned:** Pin Down landed again at 31.75 s inside the
  shout and the wire said **191.52 (x0.665)** — the Isle's own number, produced by our
  arithmetic on our own tape — and the 2.47 s interval straddling it reads 207.8 u/s, which is
  0.22 s at 383.04 plus 2.25 s at 191.52 (208.5 predicted). At the shout's expiry (36.44 s) the
  word fell to 144.00 with the condition still on.
* **What the run also showed:** a crippled level-1 body cannot leave a Hatcher — the player
  was killed at 12.68, 36.70, 58.35 and 79.98 s, each death STRIPPING the condition (288.00
  restored in the death batch, as retail's strip does) and each revive being crippled again
  within 0.6 s. That is the harness character's fragility (the `--enemy-hit` note in the
  runbook), not this arc's; the cripple/cure/re-cripple cycle it produced is exactly the
  exposure the plan wanted.

**Labels.** Inflict, cure and re-cripple OBSERVED on our wire (11 words, 4 cripples, 1 cure,
1 shout expiry under a condition); the client's crippled rate OBSERVED (one clean interval at
144.0, two start-of-leg intervals at 109–112); the boost-over-cripple product on our wire
OBSERVED (191.52, n = 1) and CORROBORATED against retail's 191.52 by construction. The
death-strip restore OBSERVED (4 of 4).

**Open, for the next arc:** a skill SNARE row (a Water hex, a self-snare stance) to exercise
the `Movement speed decrease` arm and settle 48.3's contested boost × snare rule on our own
client — Deep Freeze's −66 % single-source excess would answer both.

## SLICE-F49 — **the swing clock carries its remainder: every attacker on this server was 2–3 % slow, because a start-to-start clock stamped with the tick that opened the swing rounds each interval UP to the 51 ms grid — fixed for the player, enemies and allies, measured on the client (2026-09-18)**

**Found by** scoring a loopback dagger run off our own recorder the way RUN-DAGGERS-2 was
scored off retail (daggers §8 F19). Harness `20260917T232539`: the player's daggers
**1.376–1.379 s** start-to-start (27 ticks of 51 ms) against a nominal 1.333, Frenzy's
0.919–0.926 against 0.893, the Monk hero's hammer **1.786** (35 ticks) against 1.75.
Retail centres on the nominal — RUN-DAGGERS-2's player 1.326–1.335 plain and 0.877–0.910
boosted, and an NPC hammer on the hero tape `20260914T005758` (agent 42, n = 11)
1.742–1.756, mean **1.7495**. OBSERVED both sides; the cause is READ, not inferred:
`attack_tick` gated on `now - last < interval` and then stamped `last = now`, the tick
that happened to open the swing, so the remainder past the due instant was thrown away
every swing (`enemy_attack_tick` and `ally_attack_tick` the same).

**The fix** is one function, `swing_clock_stamp(last, interval, now)`: a swing that opens
within two ticks of being due is stamped at the instant it was DUE; one that opens late
(out of reach, a fresh chain, a cast in between) still restarts from now. The
quantisation then averages out — 26 and 27 ticks alternate, mean 1.333.
`--no-swing-clock-carry` is the control, and `test_playerswing.py` §13 runs it as the
KNOWN-BAD arm first: on a 51 ms grid it produces 27 ticks every time, 1.377 s, which is
the number the harness measured.

**On the client** (harness `20260918T081923`, the same script): daggers **1.326–1.330**
(one 1.379 in 17), Frenzy's alternating **0.868 / 0.919**, the hero's hammer mean
**1.756** over 35 swings. The per-swing spread is still the tick's (±25 ms where retail
shows ±5); the rate is right.

**What it did NOT move, and why.** The same flag fires a second strike at the tick
nearest its instant instead of the first one past it, and the double strike still lands
0.510 s behind the first and the dual's second 0.357 s (retail 0.499 / 0.334). A second
strike is armed ON a tick, so its delay is a whole number of ticks either way, and 10 and
7 ticks already are the nearest to 0.5 and 0.335 s; the rule only bites at other factors
(0.375 s under a 25 % boost: 7 ticks, not 8). A finer second strike needs a finer tick,
not a better rounding — recorded, not chased. Swing LANDINGS (`lands_at = now + windup`)
are one-shots off the real start and were left alone for the same reason.

## SLICE-F50 — **combat one-shots fire at their instant: the world thread wakes early at a combat deadline and runs the combat timers alone — swings, landings, cast phases and second strikes now sit on retail's numbers to the millisecond, with the world tick untouched (2026-09-18)**

**What F49 left.** The swing RATE was right and every single event was still quantised
to the 51 ms tick: 26 and 27 ticks alternating where retail is 1.326–1.335, and a second
strike — armed on a tick, so always a whole number of ticks — at 0.510 / 0.357 s against
0.499 / 0.334. The owner's call: fix it.

**Why not a finer tick.** The world tick also paces movement integration, the `0x001E`
simulation clock, the keep-alive and a dozen tuned behaviours whose tests assume it. The
combat timers do not: `attack_tick`, `cast_tick`, `second_strike_tick`, `chain_tick`,
`enemy_attack_tick`, `ally_cast_tick` and `ally_attack_tick` were READ for a cadence
assumption and have none — each compares absolute time and does nothing when nothing is
due. So the tick stays and the THREAD wakes early: `combat_sleep` replaces the loop's
`time.sleep(TICK_SECONDS)`, sleeps the tick in 10 ms slices (the recv thread arms casts
while it sleeps), and when `combat_deadlines(state)` — the second strike, a swing's
landing or its next due start, a cast's unsent phases, an NPC's landing or due swing —
holds an instant inside the tick, it sleeps to that instant and runs `combat_pass`, the
seven timers in the tick's own order. A deadline already offered to the timers
(`combat_served_at`) is never re-served, so a due swing the timer REFUSES (out of reach,
moving) cannot spin the loop; a fault in an early pass fuses the feature for the session
and the regular tick carries on. Same thread as the world tick by construction, so
SLICE-F10's guarantee stands (`test_guards.py` pins the call chain). F49's half-tick
rounding of the second strike now belongs to the `--no-combat-deadlines` arm only.

**On the client** (harness `20260918T100310`, the same script as F49's two runs; scored
off our own recorder; the fuse never tripped; the world tick still 51.0 ms p50):

| | retail (RUN-DAGGERS-2) | before F49 | after F49 | **after F50** |
|---|---|---|---|---|
| dagger swing, plain | 1.326–1.335 | 1.376–1.379 | 1.326–1.330 / 1.379 | **1.330 × 17 of 17** |
| dagger swing, Frenzy | 0.877–0.910 (p50 0.891) | 0.919–0.926 | 0.868 / 0.919 | **0.891–0.892** |
| double strike, plain / Frenzy | 0.499 / 0.320–0.339 | 0.510 / 0.357 | 0.510 / — | **0.501 / 0.336** |
| dual's second, Frenzy | 0.333–0.342 | 0.358–0.359 | 0.357–0.358 | **0.335–0.336** |
| start → damage word, plain / Frenzy | p50 0.564 / 0.346 | — | — | **0.565–0.566 / 0.346** |
| hero's hammer | (an NPC's mean 1.7495) | 1.786 | mean 1.756 | **1.749–1.750** |

The last-but-one row is a free confirmation of a law nobody had checked there:
ANIMREF-R1's windup, half the interval less 0.1 s, gives 0.5665 and **0.3465** — and
retail under Frenzy reads 0.346 (n = 72). OBSERVED, no free parameter.

**Seen, not explained.** The hero's series carries two short intervals (0.852, 1.073 s)
where its "swing on arrival" reset fired as it repositioned; the log shows three
re-arrivals this run against two in each earlier run, and the run BEFORE either change
had a short of its own (1.277). Not attributable to the wake on n = 1; whether a
re-arrival should swing at once is SLICE-H4's own question.

## SLICE-F51 — **an attack skill's clock, two laws off the dagger tapes with no free parameter: a LISTED activation is the attack's duration and the hit is its WINDUP (Jagged Strike lands 0.15 s in, not 0.5), and after a skill's hit the next swing opens one RECOVERY later, not one windup — both shipped and measured on the client (2026-09-18)**

**Found by** a side-by-side timing census — every timed quantity around the player's
skills on RUN-DAGGERS-2 beside the same joins over our own recorder — after F50 had put
the swings on retail's numbers. Recharges (2.000 / 3.000 / 4.000), the E3 riding the E5,
and the dual's second were already right. Two rows were not.

**(1) A listed activation is the attack's DURATION.** Jagged Strike (782) and Fox Fangs
(780) list 0.5 s. Retail lands them **0.147–0.151 s** after the energy debit (n = 33 over
both tapes; p50 0.150) and **0.063–0.078 s** under Frenzy (n = 8), and the earliest
follow-up press begins **0.499–0.502 s** after the first (0.331 under Frenzy). ANIMREF-R1's
windup law, half the duration less 0.1 s, applied to the ACTIVATION: `swing_windup(0.5)` =
**0.15**, `swing_windup(0.5 × 0.67)` = **0.0675**, and the attacker is occupied for the
activation itself, scaled the same way. OBSERVED, no free parameter. This server landed
them AT 0.5 s — the press handler's own comment: "a LISTED activation still wins, per the
wiki's reading — UPSTREAM, no corpus cycle exercises it yet." Now one does.

**(2) After an attack skill's hit the next swing opens one RECOVERY later** —
`interval − windup(interval)`. Daggers and swords (1.33–1.35 s): **0.75–0.78 s** (n = 19);
under Frenzy 0.543–0.556 against 0.5445 (n = 5); a bow (2.48) 1.33 against 1.34 (n = 1).
ANIMREF-R7b's LAW B had this as "one WINDUP later": its cluster, 0.749..0.783 (21 of 38),
was measured on 1.33 s weapons — where the recovery is 0.77 — and was written down as
`swing_windup(1.75)` = 0.775, the test fixture's hammer, a coincidence only a hammer
satisfies. Our dagger Assassin opened it 0.565 s after the hit (0.346 under Frenzy),
values retail never shows.

**The second mode, characterised and NOT modelled.** Beside each full value sits one
exactly an eighth of the weapon's interval shorter: 0.59–0.61 after a skill (about as
often as the full mode, 13 of 31), 0.435 under Frenzy, and **25 % of the dagger
character's plain swings** (35 of 138: 1.163 for 1.333, 0.78 for 0.891). It is
independent of whether the swing doubled (23 % against 24 %) or crit, not periodic, and
**daggers-only among plain swings** — 0 of 700+ sword and axe swings by three other
characters, 0 of 21 hammer swings. A shortened recovery on a one-in-four roll is a
description, not a mechanism; nothing here sends it.

**Shipped.** `attack_skill_clock(state, activation)` gives (begin → E5, begin → free) and
both scheduling sites read it (the press and the approach's arrival);
`--no-attack-activation-windup` and `--legacy-swing-restart-windup` are the two controls,
each tested as the arm before today. The 15 s chain icon joined `combat_deadlines`.

**On the client** (harness `20260918T112505`, plain and Frenzy chains interleaved with
plain swings): debit → E5 **0.150** for 782 and 780 and **0.067** under Frenzy (were
0.500); Death Blossom 0.565 / 0.345; the next swing **0.766 s** behind a skill's hit
(n = 1; was 0.565); the chain's 0 **15.000 s** behind the last hit (was 15.005).
