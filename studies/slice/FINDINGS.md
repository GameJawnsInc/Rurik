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
