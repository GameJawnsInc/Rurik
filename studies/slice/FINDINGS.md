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
