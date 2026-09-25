# What the client sends, and why it sent it

`schema/messages.json` carries field layouts for **194 `GAME_CMSG` opcodes and names for
none of them**. `authsrv.py` names 11 by hand at its dispatch. This file is the record of
opcodes named from evidence — a human performing a named action while the server marks
the window it happened in (`toolkit/authsrv/labelrun.py`, procedure in `RUNBOOK.md`).

Labels are the vocabulary in [../character/FINDINGS.md](../character/FINDINGS.md).
The tape runs that made this possible are [../tape/FINDINGS.md](../tape/FINDINGS.md).

---

## 1. The run

**2026-08-10, capture `gamesrv/authsrv-20260810T151946-c1.jsonl`.** The Lakeside County
tape (`:64103`) played to completion, then 18 prompted steps. Movement was dead — nothing
answers under a tape ([../tape/FINDINGS.md](../tape/FINDINGS.md) T6) — so the operator
pressed inputs into a frozen world.

**Both controls clean: `idle_a` 0 messages, `idle_b` 0 messages.** The operator moved the
mouse during `idle_a` and it sent nothing. Every attribution below rests on those two rows.

Two operator corrections are folded in below and both change what may be claimed:

* **Clear Target was unbound.** The prompt said "press Escape"; the operator clicked the
  nameplate button. `0x0028` therefore **cannot** be attributed to a key.
* **This map is full of Plague Worms**, which burrow — a standard GW mechanic that hides
  them from targeting. That is almost certainly what `0x00C1 [285]` is doing in the
  `target_clear` window, and it is what the tape's agent-id churn actually was.

---

## 2. Named from evidence

### C1 — `0x0046` field 1 is a SKILL ID, not a bar slot. OBSERVED, twice.

```
skill_1  ->  0x0046 [32838, 153, 0, 284, 0]
skill_2  ->  0x0046 [32838, 105, 0, 284, 0]
skill_8  ->  (nothing)
```

153 and 105, from slots **1 and 2**. A slot index would read 0 and 1. The client's own
tables resolve them to `'Vampiric Gaze'` and `'Deathly Swarm'`
([../tape/FINDINGS.md](../tape/FINDINGS.md) T4), which are the skills the recorded
character actually carries.

This is now **two independent witnesses on different days**: an unplanned five minutes on
the Ascalon tape, and a prompted step here. Field 3 is the target agent id (284, the
agent targeted two steps earlier).

**And the client validates slot occupancy locally.** Slot 8 is empty on that bar and
pressing 8 sent *nothing at all* — the client does not ask the server about a skill it
does not have.

### C2 — `0x0064` is chat, it carries the text verbatim, and EMOTES GO THROUGH IT. OBSERVED.

```
chat_say     ->  0x0064 [32868,   0, "!rurik one"]
emote_dance  ->  0x0064 [32868, 284, "/dance"]
```

The operator typed `rurik one`; the client sent `!rurik one` — it **prefixes the channel
itself** (`!` = all). This is the one step whose payload was predictable in advance, and
it matched.

`/dance` went out on the **same opcode**, as literal text. So emotes are not a separate
message type on the wire: they are chat lines the server parses. That is a real
simplification for our server, and it was not predicted.

Field 1 differs — 0 for chat, 284 for the emote — and **why is UNVERIFIED**. 284 was the
targeted agent, but the target was also 284 during `chat_say`, so "current target" does
not explain it. Do not build on this field.

### C3 — `0x00C1` is target-select, and `0` clears it. CORROBORATED.

```
target_tab    ->  0x00C1 [276]  0x00C1 [273]  0x00C1 [274]     (Tab pressed three times)
target_clear  ->  0x00C1 [285]  0x00C1 [0]
attack        ->  0x00C1 [284]  then  0x0026 [284]
```

Tab cycles: three presses, three different agents, all of them worms. The clear form
carries agent id **0**, which was predicted from 2026-08-10's stray observation and
confirmed here.

### C4 — `0x0026` is attack/interact, and it is DISTINCT from target-select. OBSERVED.

`0x0026 [32806, 284, 0]` in the `attack` window, immediately after `0x00C1 [284]`. Two
opcodes, one action: select, then act on the selection.

Whether `0x0026` is *attack* specifically or a general *interact* remains **UNVERIFIED** —
the `interact_npc` step was cut from the script, and `gateway` (§3) sent no interact at
all. One labelled run separating a hostile from a friendly click would settle it.

### C5 — `0x003D` field 4 is a DIRECTION, not a position. OBSERVED, and checkable.

Movement was dead, so the position field never changed across the whole run — every
`0x003D` carries the same `(-8088.86, -6705.80)`. The fourth field changed constantly, and
**its magnitude is very nearly constant**:

```
( 766.82,    0.00)  |v| = 766.816       (-194.27,  742.84)  |v| = 767.819
( 764.93,  -11.42)  |v| = 765.018       (-642.94,  418.44)  |v| = 767.111
(-280.79, -713.55)  |v| = 766.805       (-766.76,  -23.33)  |v| = 767.111
( 592.22, -487.11)  |v| = 766.812       (-758.95,   96.17)  |v| = 765.018
                       spread over 8 samples: 2.80 on ~766.8, or 0.37%
```

A fixed-length vector that rotates is a **heading**. This CORROBORATES the UPSTREAM name
`TURN_TO_DIRECTION` from a property the schema itself does not state — and it is the kind
of check the artifact can refute, since a position field would have wandered with the
character. (It could not have: the character could not move. That is what makes the
constancy meaningful rather than circular.)

Why the magnitude is ~766.8 rather than 1.0 is **NOT FOUND**.

### C6 — `0x0040` is FLOATS, and the schema types them as dwords. OBSERVED.

`camera` predicted SILENCE and was **refuted** — 8 × `0x0040` plus one `0x003D` and one
`0x0047`. Reinterpreting the two dword fields as IEEE-754 float32:

| raw | as float | raw | as float |
|---|---|---|---|
| `0x00000000` | `0.0` | `0x3F800000` | `1.0` |
| `0xBFF90C83` | `-1.9457` | `0x3F800000` | `1.0` |
| `0xFF800000` | **`-inf`** | `0x3F800000` | `1.0` |
| `0xBF3035EA` | `-0.6883` | `0x3F800000` | `1.0` |
| `0x7F800000` | **`+inf`** | `0x3F800000` | `1.0` |

Field 2 is **exactly 1.0 in all ten samples**. Field 1 reaches **±infinity**, which an
angle in radians never does but a ratio — a slope, a tangent — does exactly when it passes
through vertical. That is a hint, not a finding: what field 1 *means* is **UNVERIFIED**.

What is actionable now: `schema/messages.json` types both as `dword`, and they are
floats. That is a concrete `overrides.json` correction with evidence behind it.

> **C6 is superseded by C13 below, on both counts, and the table above is the only part
> that survives.** The ten raw dwords are correct observations; the two sentences drawn
> from them are not. The typing sentence is wrong — the client's own SEND table says
> `[u32, u32]`, so `dword` was right all along and the "correction" would have been a
> decoding bug. And "±infinity, which an angle in radians never does" is the inference
> that kept this opcode unnamed for three days. It is exactly backwards.

### C7 — Camera movement is NOT purely client-side. OBSERVED, prediction refuted.

The prediction was that rotating the camera sends nothing. It sent ten messages. Compare
`inventory` and `map_open`, which predicted silence and **got** silence — so the client
is not simply chatty, and the camera is genuinely different from opening a window.

### C8 — Two more opcodes witnessed, weakly labelled.

* `0x004F [32847, 0, 4, 1]` from dragging one inventory item to another slot. Field
  layout unread; **UNVERIFIED** beyond "inventory move sends this".
* `0x0032 [32818, 1]` from switching weapon sets. The `1` plausibly indexes the set.
  **UNVERIFIED.**
* `0x0028 [32808]`, three times, in the `target_clear` window — **no payload at all**.
  The operator clicked a UI button rather than pressing a key, so this cannot be
  attributed to Escape or to any keystroke. Witnessed, unexplained.

---

## 3. Corrections to earlier claims

### The keepalive is NOT an unconditional timer. Corrects [../tape/FINDINGS.md](../tape/FINDINGS.md) T5.

T5 said `0x0009` fires "at a dead-regular 5.0 s cadence... independent of anything on
screen". The second half is right and the implication was wrong. In this capture:

```
0x0009: 37 in the whole file, 0 inside any labelled step
```

All 37 landed **during the tape**. The moment the recording stopped and the server went
silent, the client stopped sending it — through three and a half minutes of active play.
So it is not a heartbeat the client emits regardless; it is tied to server traffic.
Whether it is a reply, or a timer the server's messages reset, is **UNVERIFIED**.

### The agent-id churn was worms burrowing. Refines [../tape/FINDINGS.md](../tape/FINDINGS.md) T3.

T3 recorded agent 281 created and removed 19 times in 186 s, and 19 of 45 ids reused, as
corroboration that a removed id is not poisoned (D1). The operator identifies the
mechanic: **Plague Worms burrow**, and GW hides a burrowed creature from targeting.

D1's conclusion stands and gets sharper. This is not spawn-and-death churn — it is one
creature going away and coming back, and **ArenaNet hands it the same agent id every
time**. `WORLD_REMOVE_AGENT` is how the client is told a creature is untargetable, not
only how it is told one died. Our server's `remove_agent` is therefore on the critical
path for a mechanic we have not modelled at all.

### `gateway` sent no zone message. OBSERVED.

Walking into the exit produced only movement (`0x003D` ×4, `0x003E` ×2, `0x0047`). There
is no client-initiated "take me to the next map" message in that window — consistent with
the transfer being server-initiated, and with the tape's silence meaning nothing could
start it.

---

## 3b. Run 2 — the town script, 2026-08-10

Capture `gamesrv/authsrv-20260810T160945-c1.jsonl`. Ascalon City tape `:60935`, truncated
before its handoff ([../tape/FINDINGS.md](../tape/FINDINGS.md) T8), then 14 prompted steps.
Movement was dead again, which cost two steps and gave a result the working case could not.

**Grading, stated before the findings.** `idle_a` is **dirty**: 2 messages, `0x003D` and
`0x0047`. The operator confirms an accidental movement, and the timing bounds it — both
land at **+0.0 s and +0.1 s of a 12 s window**, continuing a turn that began at t=54.0 s,
*before* the mark at t=54.5 s. `idle_b` is spotless after a dozen actions, which is the
control that shows the clock never drifted. So: **step 1's own result (the idle floor) is
void; steps 3–12 are unaffected**, because the contamination is confined to 0.1 s at the
very start and touches no other window. That judgement is the reason `report` now prints
*when* contamination landed.

Two steps produced nothing usable and both are the same cause: the operator could not
walk, so `merchant` never reached a merchant (it recorded movement attempts instead) and
`camera` — see C11 — is the one that mattered.

### C9 — `0x0039` is INTERACT, and `0x0026` is ATTACK. C4 SETTLED.

```
target_npc     ->  0x00C1 [45]   then  0x0039 [32825, 45, 0]
interact_npc   ->  0x0039 [32825, 45, 0]  x3
target_player  ->  0x00C1 [499]        and NOTHING ELSE
```

Clicking an **NPC** sends target-select *and* `0x0039`. Clicking a **player** sends
target-select alone. The combat run's attack on a hostile sent `0x0026`, not `0x0039`.

Three allegiances, three behaviours, two distinct opcodes — so `0x0026` is **attack
specifically**, and C4's open question is closed. This is what the town script existed to
ask, and it is the one thing it delivered cleanly.

`0x00C1` is now CORROBORATED across worm, NPC and player: it is target-select and nothing
more, exactly as C3 predicted.

### C10 — `0x0064` field 1 is the current target, and plain chat has none. Answers C2.

Six samples across both runs:

| typed | field 1 | text sent |
|---|---|---|
| `rurik one` | **0** | `"!rurik one"` |
| `rurik two` | **0** | `"!rurik two"` |
| `/dance` (run 1) | 284 | `"/dance"` |
| `/dance` (run 2) | 499 | `"/dance"` |
| `/sit` | 499 | `"/sit"` |
| `/me waves` | 499 | `"/me waves"` |

499 is the player targeted two steps earlier; 284 was run 1's targeted worm. **Plain chat
carries 0; every slash command carries the current target.** That is the field C2 said not
to build on, and it now has a consistent reading across two sessions, two maps and three
target allegiances. RECONSTRUCTION — six samples, no counterexample.

`/sit` and `/dance` are byte-identical in shape, so a persistent emote is not distinguished
on the wire. Emotes really are just chat lines.

### C11 — C7 IS REFUTED. The camera is client-side after all.

The `camera` step sent **nothing**. Run 1's sent ten messages, and C7 concluded from that
one run that camera rotation reaches the server.

What run 2 shows is where `0x0040` actually comes from: it appears **only in `merchant`
and `gateway`** — the two windows where the operator was trying to *walk* — and in both it
arrives sandwiched between `0x003D` heading updates and `0x0047` move-cancel, with the same
pair of values each time (`inf, 1.0` then `-3.0183, 1.0`).

So `0x0040` is **movement-related, not camera**, and run 1's camera step must have carried
movement input alongside the rotation. A refutation seen once in one map was a fact about
one map — which is exactly why the town script re-predicted TRAFFIC and asked again.

**C6 stands and is reconfirmed**: the fields are floats, the second is exactly 1.0, the
first reaches ±inf. Ten more samples, same shape. The schema still types them as dwords.

> **That paragraph is what a small sample sounds like when it agrees with itself.** Twenty-two
> samples, all 1.0, from two runs of the same script in the same world. The vault held 559
> and 126 of them are not 1.0. See C13. The "movement-related, not camera" half survives and
> is now explained rather than merely observed.

### C12 — `0x003D`'s last field is NOT a direction index. TESTED AND REFUTED.

Inside the `gateway` window the trailing small integer looked like a clean eight-way
compass — 11 consecutive samples where each value sat in its own arc. Across **all 26
samples in both runs it collapses**: value `1` spans 0.0°–359.1°, value `2` spans
24.6°–354.4°.

Recorded so it is not re-derived. Whatever that field is, it is not the absolute heading,
and a hypothesis that survives one window is not a finding.

---

## 3c. `0x0040` settled, 2026-08-10, from the binary

### C13 — `0x0040` is `ROTATE_PLAYER`. Field 1 is an ANGLE IN RADIANS. OBSERVED. Supersedes C6.

The labelled runs could not have got here, and it is worth being precise about why. A
labelled run tells you **when** a message is sent. It cannot tell you that an infinity is
a sentinel constant the client stores rather than a number it computed — and the
infinities are the whole reason an angle looked impossible. C6 reasoned "±inf rules out
radians, but fits a slope through vertical", and that one sentence held the opcode at
`MOVE_UNKNOWN_FLOATS` while the answer sat in the vault.

**Leg 1 — the client names it.** Build 38797 has exactly **one** site that sends `0x0040`:
the 12-byte wrapper at `0x009207B0`, found by enumerating all 174 callers of the channel
send `0x007DCF00` and recovering the opcode immediate at each. Its public entry
`0x008165C0` range-checks its float argument against the assert text

    (rotation >= -1.0f) && (rotation <= 1.0f)      P:\Code\Gw\Char\Cli\ChCliApi.cpp:5562

and then tail-calls the sender. **The client's own word for the quantity is `rotation`.**

**Leg 2 — the infinities are a literal.** The sender at `0x0081BE90` loads `+inf` from
`.rdata 0x00948654` when `rotation > 0` and `-inf` from `0x0094E538` when `rotation < 0`,
and sets field 2 to `|rotation|`. When `rotation` is exactly `0` it sends
`atan2(current facing)` with field 2 = `1.0` instead. So an infinity means *"turning
continuously, sign gives the direction"* — a sentinel, not a ratio. The second sender
(`0x0081BA80`, steering) computes `field1 = atan2(desired direction)` and
`field2 = min(1, |wrap(target − facing)| / (π/3))`, and **refuses to send below 0.1**.

**Leg 3 — the wire agrees, and had all along.** Over **559** samples in 55 game-channel
streams: field 1 is never NaN; all **163** finite values lie inside ±π (max 3.0190) — which
163 arbitrary dwords do not do; **13** of them equal `atan2(dir.y, dir.x)` of a nearby
`0x003D` **direction** vector to float32 round-off and 30 fall within 0.05 rad, against a
null model built by shuffling this same corpus whose 95th percentile is **5**. Field 2's
minimum across all 559 is **0.10133** — just above the client's own 0.1 send gate, which is
a number that could easily have come out wrong and did not.

The cleanest single sample is the live one: `vault/captures/live/20260807T143055` conn
`:60935` msg 52, field1 = `1.0821444988250732` rad = 62.0026°, which is exactly atan2 of
the direction its three preceding `0x003D` messages carry. Its field 2 is `0.118851`.

**What C6 got wrong, in both directions.** The typing sentence — "the schema types them as
dwords and they are floats" — reads as a bug report and is not one: the client's own SEND
table says `[u32, u32]`, wire 10 bytes. The values are floats; the *wire type* is `u32`.
Acting on C6 would have broken decoding of a message we now understand.
And "field 2 is exactly 1.0" was true of its ten samples and false as a generalisation:
**433 of 559**, with 105 at 0.425 and a tail to 0.10133. That distribution **corroborates**
[../divergence/FINDINGS.md](../divergence/FINDINGS.md) R3, which measured 411/536 and 105
before these runs existed — it is not a new refutation, and R3 had it first.

**Frequencies here describe our harness, not a player.** 536 of the 559 are
`drive_client.py` clicking fixed window fractions; 22 are the 2026-08-10 loopback runs (17
of those tape-loaded); **1** is live. The name does not rest on any of those counts — it
rests on the binary, which is build-truth and corpus-independent.

**UNVERIFIED, deliberately: which sign is a left turn.** Bracketing the infinities against
the next heading gives 121/189 and 106/169 — real but far too weak to write down, and
`overrides.json` makes no left/right claim. Two labelled steps ("hold turn-left for three
seconds", then right) settle it in a minute.

**UPSTREAM** ldufr/Headquarter numbers `ROTATE_PLAYER = 0x0040` and always has. That is a
second witness we did not need and did not use; its derivation-register row was added at
[../../PLAN.md](../../PLAN.md) §6.1 *before* the name landed, because three separate plans
were about to import its vocabulary into a tracked schema file with no row at all — the
`gwdat.py` shape.

Pinned by `toolkit/authsrv/test_rotate.py`, whose own first version scored **0 of 163**
because it paired against `0x003D`'s **position** vec2 instead of its **direction** vec2.
Both are perfectly plausible angles. That is C5 being needed a second time, and the field
index is now pinned by a check rather than by a comment.

---

## 4. The count

| | witnessed | added |
|---|---|---|
| before 2026-08-10 | 15 | — |
| after the combat run | 20 | `0x0028` `0x0032` `0x0040` `0x004F` `0x0064` |
| after the town run | **23** | `0x0039` `0x0092` `0x0093` |

`0x0092` and `0x0093` arrived during the instance load rather than from a prompted
action, so they are witnessed and unlabelled.

Named with evidence: **C1** `0x0046` skill id · **C3** `0x00C1` target-select ·
**C4/C9** `0x0026` attack vs `0x0039` interact · **C5** `0x003D` heading ·
**C13** `0x0040` ROTATE_PLAYER (was C6 "floats") · **C10** `0x0064` chat text + target.

194 opcodes have layouts. 23 have been seen and 7 are named. That ratio is the argument
for running this again — the two runs cost about twelve minutes of play between them.

**And one of the seven was named by neither run.** `0x0040` came out of the client's
binary, after the labelled runs had witnessed it twice and both times drawn the wrong
conclusion from it. The two methods answer different questions — a run says *when*, the
image says *what* — and the runs' own evidence had been sufficient to refute C6 since
2026-08-04, sitting unread in 559 samples nobody had counted past twelve. Worth
remembering the next time a shape looks unnameable: check whether the corpus is small
before concluding the message is hard.

---

## 5. Next

1. **A second labelled run with the gaps closed** — `interact_npc` (settles C4), a
   friendly vs hostile click, `/sit` against `/dance` (does a persistent emote differ?),
   several more skill slots, and a merchant. The script is cheap to extend and each run
   is six minutes.
2. **Write C1, C3, C5 and C6 into `schema/overrides.json`** with this capture cited —
   particularly C6's float typing, which is a decoding bug in every reader we have.
3. **Model burrowing** (§3). It is the first GW mechanic we have direct evidence for that
   our server has no concept of, and it runs entirely through `0x0020`/`0x0021`, which are
   already implemented.

## C14 — the CLIENT half, read for the first time, from ArenaNet's own traffic

**OBSERVED, 2026-08-11.** GAME_CMSG goes from **7 names of 194 to 16**. The seven it
had were all earned by labelled runs against OUR OWN server (`labelrun.py`); this
corpus is ArenaNet's, and it is an independent witness that can refute them. One of
them did not survive.

**Two things had to be true before a single message could be read.**

1. **The client ORs `0x8000` into every game-channel opcode it sends.** `MsgConn`'s
   send computes `((conn+0x54) != 0 ? 0x8000 : 0) | msg[0]`. Without masking that off,
   *nothing* decodes — not one message. With it, both captures frame to their exact
   byte count. `codec.decode_stream` already took a `mask` parameter, so no code
   change was needed; nobody had passed it. This is also where `studies/divergence`
   D4's unexplained client reply `0x8009` came from: it is GAME_CMSG `0x0009`.
2. **Timing had to be rebuilt.** `livesession.assemble` writes one c2s blob per
   connection, so order survives and time does not. `toolkit/authsrv/cmsgstream.py`
   recovers it: the wire log stamps every TCP segment, segments reassemble in seq
   order, ARC4 runs continuously, so plaintext offset P sits at stream offset
   P + len(handshake) and the segment covering it carries the time.

**That turns a narrated session into a labelled run against ArenaNet's server** —
which is what `labelrun.py` does on ours, except with real traffic. The operator
wrote down what they did; the server's own messages date the anchors:

| t | anchor, from the server's own messages | narrated action |
|---|---|---|
| 18.7 s | map 148 | Ascalon City — Town Crier, Sir Tydus |
| 62.9 s | GAME_SERVER_TRANSFER → map 146 | "left to Lakeside County" |
| **99.5 s** | CHAR_STATUS_DEAD | the River Skale Queen |
| 261.7 s | → map 164 | "gatewayed to Ashford Abbey" |
| 271.5 s | → map 146 | back to Lakeside |
| 285.8, 294.4 s | skill activated ×2 | Power Shot |
| **294.9 s** | CHAR_STATUS_DEAD | the worm |

### THE HEADLINE: `0x0046` USE_SKILL is half a story, and the other half is unhandled

| | `0x0046` USE_SKILL | `0x0027` | server skill-activated |
|---|---|---|---|
| Necromancer | **4** | 0 | 4 |
| Ranger | **0** | **3** | 2 |

A whole narrated session of a Ranger casting Power Shot sent **zero** `0x0046`.
Attack skills leave on **`0x0027`**, and two of its three sends are followed by the
server's own skill-activated at **1.19 s and 1.17 s** — the same response `0x0046`
gets, which is what makes them two halves of one thing rather than unrelated
messages. Field 1 is constant (the skill) and field 3 varies (the target).

**Our server has no dispatch arm for `0x0027`.** The only mention of that number
anywhere in `authsrv.py` is a comment about a *GAME_SMSG* of the same number in a
different channel. So a Warrior, Ranger, Assassin, Paragon or Dervish pressing an
attack skill against us gets silence. ~~— and per D9(b) a schema-unknown c2s opcode
discards whatever shared its TCP read, so it is a correctness bug, not a missing
feature.~~ **CORRECTED 2026-08-11: it is a missing feature, and the D9(b) clause was
backwards.** `0x0027` is schema-**known** (`GAME_CMSG_0039`, declared size 15), and
landing on the silent-ignore path *means* schema-known — that is D9(**a**), which
ignores without touching the buffer. D9(b) covers schema-*unknown* opcodes only, and is
itself fixed now. Nothing was ever discarded on this path. `probes.py`'s
`use_skill_capture` predicted this branch and had never been run; this corpus runs it.
**The gap is closed regardless** — `authsrv.py` dispatches `0x0027` and `0x0046` through
one arm as of 2026-08-11.

### The nine new names

`0x000A` SEND_MACHINE_SPEC · `0x0012` REQUEST_QUEST_INFO · `0x003B`
NPC_SERVICE_SELECT · `0x003E` MOVE_TO_COORD · `0x0047` MOVE_CANCEL_REPORT_POSITION ·
`0x0060` CHAR_CREATE_SET_CHAPTER_PROFESSION · `0x0084` CHAR_CREATE_SET_EQUIP_COLOR ·
`0x0088` INSTANCE_LOAD_REQUEST_SPAWN_POINT · `0x0092` MISSION_MASK_REPORT.
`0x0026`, `0x003D` and `0x00C1` were re-derived and now stand on the client's own
words rather than on our own labelled runs.

Two worth calling out for the *kind* of evidence:

- **`0x0092` MISSION_MASK_REPORT.** Its sender's only assert is
  `missionMaskBytes <= MISSION_MASK_BYTES` (MsCliMsg.cpp:181), and the bit setter's
  is `mission < MISSIONS` (MsCliMan.cpp:368) — so MISSIONS = 888. **Our own stdlib
  `areatable.py` independently reads exactly 888 AreaInfo records out of the same
  build.** Two instruments that know nothing about each other, agreeing on a number.
  **ADDENDUM 2026-09-13 — build 38888 moved both numbers, and the wire noticed first.**
  The first live tape of 38888 (`20260913T210901`, Shing Jea Monastery, conn `:63677`)
  stopped framing its c2s stream at byte 31 of 1,303: `array8 count 116 exceeds
  declared cap 112`, on a 120-byte 0x0092 with 0x0093 framing cleanly right after it.
  160 c2s 0x0092 on every earlier live tape are exactly 112 bytes, so this is a client
  change and not a decoder defect. OBSERVED on the pristine 38888 image, each with its
  38797 control: the SEND descriptor reads `array8[116]` (cmd `0x740b`, was `0x700b`);
  the MsCliMsg.cpp:181 compare is `cmp esi, 0x74` at 0x00852e98 (was `0x70` at
  0x00852948); both MsCliMan.cpp `mission < MISSIONS` sites compare against `0x381` =
  897 (was `0x378` = 888); and `areatable.py` reads exactly 897 records out of 38888
  — the same two-instrument agreement, at the new number. RECONSTRUCTION:
  `MISSION_MASK_BYTES = 4 * ceil(MISSIONS / 32)` reproduces both builds (28 dwords →
  29), so the mask is dword-granular and nine new AreaInfo rows spilled it. The cap
  is corrected in `schema/overrides.json` (GAME_CMSG 146, the first c2s FIELD
  correction that file carries; `test_codec.py`'s `LAYOUT_FIXED` names it), not in
  `messages.json`, which is stamped `validated_against_build 38797` where 112 is
  right. After the change the 38888 channel frames to its last byte in both
  directions. Cross-build note for [../crossbuild/FINDINGS.md](../crossbuild/FINDINGS.md):
  this is the first constant a live tape refuted before a scanner did.
- **`0x0047` vs `0x003E`** have a byte-identical layout (vec2 + u32), so only values
  tell them apart: `0x0047`'s vec2 is within 200 units of the player's own reported
  position **9/9**, `0x003E`'s **0/3**. A report and a destination are opposite
  meanings and the wire separates them cleanly.

### The ledger, and a defect it exposed in our own reader

**12 NAMED · 6 PARTIAL · 2 that were never GAME_CMSG at all.**

The last two are ours. The first reader of this corpus fed the **auth** connection
through the GAME_CMSG tables and produced two confident "opcodes", `0x0001` and
`0x0005`, which reached the naming pass as real findings. They are the first four
bytes of the auth c2s plaintext — one auth message's header and a field — read as
two game messages. **Decoding the wrong channel does not error, it invents.**
`cmsgstream.py` now files connections by channel from the capture's own file names
and refuses to guess, and `test_cmsgnames.py` pins it.

The six PARTIALs are all the same shape and it is worth naming: the mechanism is
solid and the NOUN is ours. `INSTANCE_LOAD_READY`, `LEAVE_GAME_SERVER`,
`CLIENT_PERF_REPORT` are role labels with no client word behind them, and the
refutation pass struck them on the same standard the proposals themselves had used
to reject rivals. That is the standard working in both directions.

---

## DESKWORK-D1 — the c2s send-site census, and the hero kick it found (2026-09-22)

DESKWORK-D1, steps 1 and 2. Two things settled here: a permanent, bare-machine
census of every c2s send site in the client, and the hero-kick message it
confirms — `c2s 0x001F`, OBSERVED once on a live tape, the client action
`studies/heroes/FINDINGS.md` §3.3 had recorded as NOT FOUND.

**CORRECTED 2026-09-22 (the fix pass), and read this before quoting the first
cut.** The first version of this section, committed the same day, made three
claims the two reviewers refuted from the bytes: (1) that the 40-site framer
was "the AUTH channel" — it is a calling convention, and it carries GAME
`0x0009`, `0x0092` and `0x0008` on the game connection; (2) that the two
framers' VAs "swapped order" between 38797 and 38888 — they did not; (3) that
7 of 214 sites "pass the opcode in a register (a forwarding thunk)" — six store
it beyond a 64-byte window and one pushes a static buffer. All three are
corrected below; the numbers that stand (214 = 40 + 174, the five anchors, the
`0x0016` correction) were reproduced independently by both reviewers.

### The census — `toolkit/clientscan/sendsites.py`

Every "c2s NOT FOUND" verdict in this repo rested on a scratch enumeration that
was never committed, and one searched the wrong family. This is the committed
recipe, and it runs with no `capstone` (CLAUDE.md carve-out (1) scopes the
disassembler to two named files; a census that must be re-run after every
ArenaNet build cannot need a pip install), so it is a byte scan over `gwpe` +
`asserts` + `buildid`.

**TWO framers, by CALLING CONVENTION — neither is a channel. MEASURED (38797).**
The client wraps each outbound message in a small function that stores the
opcode into a stack buffer, fetches a connection, and calls one of:

| framer (38797) | arguments | sites | example |
|---|---|---|---|
| `0x007DCF00` | `(conn, nbytes, buf)` | **174** | `0x0091FF30` (0x001F): `push buf; push 8; push conn` |
| `0x007DCB10` | `(conn, buf, ndwords)` | **40** | `0x00491E50` (0x0009): `push 3; push buf; push conn` |

**214 sites in all.** The submitted survey counted only the first; a census that
claims it cannot go stale must enumerate both. On 38888 they are `0x007DD360`
(174) and `0x007DCF70` (40); the dword framer is the LOWER VA on both builds.
They are found by a **masked prologue signature**, never a hardcoded VA.

**The CHANNEL is the connection argument, read per row.** Both framers take the
connection as their first argument, and the same framer is called with either:

- **`game`** — the site calls the GAME-connection getter, a 6-byte function
  `mov eax,[abs]; ret` (`0x00491DE0` on BOTH builds, returning `[0x00C034D4]` on
  38797 and `[0x00C06514]` on 38888), or pushes/loads that global directly.
  Derived per build as the dominant `call X; push eax` before a framer call
  (171 of 214 sites). **175 rows**, including THREE on the dword framer:
  `0x00491E50` (opcode `0x0009`, 2,687 c2s on the live game wire), `0x00852930`
  (`0x0092`, 305 on the wire; `0x00852E80` on 38888) and `0x00491D30` (`0x0008`,
  a STATIC buffer in `.rdata` pushed as an image address). A census that
  attributed the channel per framer reported GAME `0x0009` and `0x0092` as
  having NO send site — the exact false-NOT-FOUND this tool exists to prevent.
- **`auth`** — the site pushes `[reg+0x14]` of a struct loaded from the AUTH
  global (`[0x00C03524]` on 38797, `[0x00C06564]` on 38888; derived per build as
  the dominant absolute load in those sites' windows). **35 rows**, all on the
  dword framer, none on the byte framer. The label is the nearest assert module
  of its wrappers (GcAuthCmd) — a LABEL, not a name the client gave.
- **`?`** — **4 rows**, named, not guessed: three sites in `0x004923D0`
  (opcodes `0x0001`, `0x0002`, `0x0016`; `mov esi,[ebp+8]` — the connection
  struct is a PARAMETER, so its channel is the caller's) and one in an AgTrack
  function (`0x006047A0` / `0x00604C00`, opcode `0x000D`; `mov eax,[esi+0x1c]`
  — a struct field). The window cannot name them and the footer counts them.

**A site's opcode is the imm32 store INTO THE SLOT THE FRAMER IS HANDED, read
over the whole containing function.** The store is `C7 45 D <imm32>` or
`C7 85 D32 <imm32>`; the tie is a `lea reg,[ebp+D]` with the same displacement
in the same function. MEASURED on both builds: **214 of 214 sites resolve, all
CONFIDENT**, one of them static. The farthest store sits **235 bytes** before
its call (`0x00920A70`, opcode `0x004D`); `0x002B` COMPASS_DRAW (`0x00920230`)
stores at +0x1B and calls at +0x75. The first cut's 64-byte window missed
`0x000A`, `0x000B`, `0x002B`, `0x0045`, `0x004C`, `0x004D` and the static
`0x0008`, and its docstring explained the gap as "register thunks" — false. The
confidence tie is what separates the true `0x0040` wrapper `0x009207B0` from a
coincidental `mov [ebp-0x48], 0x40` size local in `0x0091FB20`. The length
column is the last `push imm` in the arg-setup tail (bytes for the byte framer,
dwords for the dword framer; `0x00A2`'s push comes AFTER its store and is read
correctly, 4).

**Five anchors, pinned per build.** MEASURED, each resolving to ONE game-channel
wrapper:

| opcode | 38797 | 38888 | length |
|---|---|---|---|
| `0x0040` ROTATE_PLAYER | `0x009207B0` | `0x00921130` | 12 |
| `0x0016` HERO_LOCK_TARGET | `0x0091FD00` | `0x00920680` | 12 |
| `0x00B1` travel | `0x0085C280` | `0x0085C7C0` | — |
| `0x001E` hero ADD | `0x0091FF00` | `0x00920880` | 8 |
| `0x001F` hero KICK | `0x0091FF30` | `0x009208B0` | 8 |

**The survey's `0x0016` VA is REFUTED.** DESKWORK-D1's route put the 38797
`0x0016` wrapper at `0x0091FD60`. That VA is nobody's wrapper start on 38797: it
lies 16 bytes INSIDE the `0x0017` wrapper (entry `0x0091FD50`; the bytes at
`0x0091FD60` are `f8 50 6a 08 c7 45 f8 17`, mid-instruction). The true 38797
`0x0016` wrapper is `0x0091FD00`. `0x0091FD60` IS the `0x0016` wrapper on 38833
and 38849 — `schema/overrides.json`'s HERO_LOCK_TARGET row records it for 38833
— so the survey conflated builds. The census reads each wrapper's own bytes and
is self-correcting; the byte scan is the arbiter, not the survey text.

**The known-bad arms.** A wrong framer VA yields zero rows from `census()`, and
the CLI REFUSES a zero-row or a not-two-framers result with exit status 2 — the
first cut printed `coverage: 0 sites` at exit 0, which on a drifted build reads
as a clean "no c2s opcodes". `test_sendsites.py` (floor 85) identifies both
snapshots with `buildid.of_image`, pins the framers, the 214 = 40 + 174, every
row resolved, the per-row channels (175/35/4 and the three game sites on the
dword framer), the recovered far stores, the anchors and their lengths, the
`0x0017` wrapper start, the AUTH `0x0016` homonym, and both refusals.

### The hero kick — `c2s 0x001F HERO_KICK`, OBSERVED n=1

**Capture `20260916T150306`, connection `10.0.0.210:62321`.** The hero (index 6,
Koss) loads into the party at t=151.746:

- `s2c 0x0073` HERO_INFO `[6, 3, 1, 0, 243282, 245053, [322, 382, 348, 1, 385, 2], 0, 0]`
- `s2c 0x0072` HERO_ACTIVATE `[6, 379, 96, 2]` — hero 6, **agent 379**, inventory **96**, aiMode 2
- `s2c 0x01C2` PARTY_HERO_ADD `[28, 68, 379, 6, 3]` (t=151.784) — party 28, **owner player 68**, agent 379
- `s2c 0x0144 [96, 1]` — Koss's OWN inventory container, declared at load
- `s2c 0x00B0 [68, 2]` — the party size at load counts the hero

Then the kick, at **t=158.676**:

- `c2s 0x001F [6]` — the payload is the hero index (livewire prints the header
  word `32799` = `0x801F` first).

and its reply batch **42 ms later, at t=158.7182**, one 41-byte plaintext chunk
whose first 35 bytes are, in this order:

- `s2c 0x0075 [379]` — the hero agent
- `s2c 0x01C3 [28, 68, 379]` — PARTY_HERO_REMOVE (RECV table `0x00bcb788`, the
  SAME table as `0x01C2` PARTY_HERO_ADD — its roster-remove mirror)
- `s2c 0x00F8 [379]` — the despawn sweep
- `s2c 0x003E [379]` — AGENT_VIEW_UNLINK
- `s2c 0x00B0 [68, 1]` — PLAYER_PARTY_SIZE(player 68, size 1)
- `s2c 0x0145 [96]` — destroys the hero's inventory container 96

(the remaining 6 bytes are `0x001E [62]`, a routine message). `test_herokick.py`
encodes `hero_kick_batch(379, 68, 28, 96, 1)` through the codec and compares it
to those 35 bytes **byte for byte**, with a rotated batch as the known-bad arm.

The identity fields are proven from this one connection: **379** is the hero's
agent id (`0x0072`, `0x01C2`), **68** the owner player number (`0x00B0`,
`0x0199` INSTANCE_LOAD_INFO field 1, `0x01C2`), **28** the party id (`0x01C2`
field 1, the first argument of `agents.party_hero_add`), and **96** the hero's
inventory container (`0x0072` field 3 = inventoryId; `0x013E`/`0x0144` fill it at
load; `0x0145` destroys it at the kick). Across the 35 LIVE captures (96 game
connections) this is the ONLY c2s `0x001F`, and `0x0075`, `0x01C3`, `0x00F8`
and `0x0145` each occur exactly once, all in this batch (both reviewers' census).

**The kick holds across a zone. OBSERVED.** The two subsequent loads on the same
tape — connection `50807` (map 449) and `56865` (map 430) — send `0x0073`
HERO_INFO for hero 6 (still an owned hero, in the catalog) but **no `0x0072` and
no `0x01C2`** (not in the party). A kicked hero is owned-but-not-in-party, and
that asymmetry is the acceptance the server's `--persist` kick reproduces.

**What the witness does NOT cover.** The connection's `0x0199` is
`[68, 449, 0, 3, 0, 0]` — Kamadan, an outpost — and none of its 130 `0x0020`
creates carries agent 379: the hero was a roster entry with NO BODY. So the tape
says nothing about kicking a hero that has a body, and nothing about whether the
client offers a kick in a field at all — **UNOBSERVED**. And 96 was Koss's own
container: retail's `0x0145` is per hero.

**The loopback witness.** `vault/captures/gamesrv/authsrv-20260913T093718-c1.jsonl`
carries `c2s 0x001F [3]` at t=27.085 and `c2s 0x001F [40]` at t=29.755, both on
the server's `unhandled` path. That run owned ONE hero, index 3 (HERO_ACTIVATE
hero 3, agent 200, inventory 2, map 148 — also a town), so **`[3]` is a second,
independent witness that the field is the hero index**. **`[40]` names no hero
and is UNEXPLAINED** (40 = 0x28, the client's HEROES bound; possibly a
sentinel); the handler drops it as unowned. **That the operator pressed the
kick button is RECONSTRUCTION** — nothing in the capture records the click.
Until now the server armed only HERO_AI_MODE / LOCK_TARGET / FLAG_PLACE /
PARTY_FLAG_PLACE; the kick had no arm.

**What the server now does (`handle_hero_kick`, behind `--no-hero-kick`).**

- The batch, in retail's order, with OUR ids — OBSERVED.
- The party size counts the remaining heroes — OBSERVED for "heroes count" (the
  load frame `[68, 2]` with one hero). The LOAD path still sends
  `1 + henchman` without heroes; that under-count is named in `PLAN.md` §8.1.
- `0x0145` goes out ONLY for a key `--hero-bags` declared and no remaining party
  hero still names. OURS is one `--hero-inventory` key shared by every hero
  slot, and the client's `0x0145` handler (`0x008462B0` on 38797, a lookup on
  `inventoryTable`) asserts `inventory` at **ItCliApi:2024** on a key it cannot
  find — undeclared (the default rig: bags off, key 0; the first cut sent
  `0x0145 [0]`, which `studies/smsgsweep` measured as the crash) or already
  destroyed (a second kick). The omission is logged.
- A hero WITH a body leaves through `remove_agent` (`0x0021`) FIRST —
  **RECONSTRUCTION** (see above: the witness had no body). The first cut popped
  `state["agents"]` and told the client nothing, and claimed retail "does NOT
  send 0x0021", which the tape cannot support.
- Its standing orders (`hero_cmd`) are cleared; `hero_locks_release` and
  `handle_hero_command` iterate the PARTY, so a kicked hero holds no lock and
  takes no orders.
- Under `--persist` the kick is written to the character store and seeded back
  on the next connection. `--no-hero-kick` reads NO stored kick (a revert that
  left a saved kick in force was not a revert), and **`--reset-hero-kicks`** clears
  the store at the character's first load — the un-kick until the ADD ships,
  because the sandbox always passes `--persist` and one press would otherwise
  drop a hero from the party for good. `sandbox.store_state` shows
  `kicked_heroes`.

`c2s 0x001F` is named **HERO_KICK** in `schema/overrides.json` (medium, OBSERVED
n=1). The add (`0x001E`) stays static-only — its wrapper is `0x0091FF00`, no
retail tape carries it — and is the next step. **Still owed: one loopback click**
on a real client; the wire, the store and the source locks are proven offline
(`test_herokick.py`, floor 52).

### The retail c2s triage — `toolkit/authsrv/c2striage.py` (DESKWORK-D1 step 3, 2026-09-23)

**The question.** Which client actions does our server ignore? Every earlier answer
was a one-off script over one capture (`test_dispatch.py`'s own docstring quotes a
2026-08-13 sweep of the LOOPBACK corpus), and `test_dispatch` §7 could only ask of
opcodes something had already NAMED. This is the committed recipe, over ArenaNet's
own wire: `python toolkit/authsrv/c2striage.py` walks every origin=LIVE game
connection (`livewire.live_connections`, the refuse-to-mix loader) and, per c2s
opcode, counts sends / captures / connections, asks the schema for a name, asks the
dispatch chain for an arm (the same syntax-tree harvester `test_dispatch` uses,
imported from it), asks `test_dispatch.DROPPED_ON_PURPOSE` — the ONE place a drop
reason lives — whether the drop is deliberate, and records retail's first s2c within
1.5 s in two columns: strict, and with `0x001E` WORLD_SIMULATION_TICK skipped,
because the clock follows everything within 20–500 ms and is never an answer.
`--static` joins the send-site census (`sendsites.py`) on the pinned build for the
wrapper VA, its caller count and the nearest assert module — a LABEL for where the
client sends from, not a name. `--write` commits the census to
`toolkit/authsrv/retail_c2s.json` (counts and replies only; status and name are read
off the tree at test time so the file cannot go stale); a zero-connection run is
REFUSED with exit 2.

**MEASURED 2026-09-23: 96 live game connections over 29 captures (of 35 origin=LIVE),
13,320 c2s messages, 57 distinct GAME_CMSG opcodes; 0 connections with a receipt
shortfall.** 31 handled, 8 already on the allowlist, **18 UNTRIAGED** — seen on
retail, unhandled, unnamed, and not dropped on purpose (the route estimated ~19):

| opcode | sends | conns | shape | first s2c, clock skipped | wrapper (38797) / module | decision |
|---|---|---|---|---|---|---|
| `0x0008` | 84 | 84 | header only | none 66 of 84 | `0x00491D30` GcGameCmd, STATIC buffer | dropped, unnamed |
| `0x000B` | 29 | 29 | blob16, 4 dwords, string16 ×2 | load burst | `0x00491820` (the `0x000A` builder) | dropped, unnamed — the OS name and client version string; `0x000A`'s companion |
| `0x000C` | 2 | 2 | header only | none consistent | — | dropped, n=2 |
| `0x000D` | 31 | 30 | header only | `0x019F` 11 | NOT FOUND on the game channel | dropped — a load-sequence marker between `0x0090` and `0x0092` |
| `0x0013` | 2 | 1 | header only | `0x00A2` 1 | `0x0091FC30` CharMsg, 0 direct callers | dropped, n=2 |
| `0x0023` | 1 | 1 | byte, agent_id | `0x0034` | `0x00920030` CharMsg | dropped, n=1 |
| `0x0041` | 1 | 1 | agent_id, byte | movement | `0x00920800` CharMsg | dropped, n=1 |
| `0x0044` | 1 | 1 | dword | `0x009F` | `0x009208B0` CharMsg | dropped, n=1 |
| `0x0045` | 5 | 3 | array8, 50 bytes; 4 distinct over 5 (bytes 14–15 vary) | none 2 of 5 | `0x00920980` CharMsg, 1 caller | dropped — a client-state report |
| **`0x004F`** | 4 | 2 | byte, word, byte | **`0x014B` 3 of 4 first, 4 of 4 in sequence; `0x006F` beside it 3 of 4** | `0x00920DE0` CharMsg | **NAMED `ITEM_MOVE` (medium)**; dropped until step 8 |
| `0x0051` | 6 | 2 | agent_id, byte | agent updates | `0x00920E90` CharMsg | dropped — bursts on one low agent id |
| `0x0063` | 3 | 3 | header only | `0x009F`/`0x0020` | `0x00921950` CiCommand | dropped — a load-time marker (after `0x0092` on 2 of 3) our client never sends |
| `0x0085` | 2 | 2 | word | `0x015C` 2 of 2 in sequence | `0x0084C860` ItCliMsg | dropped — PvP equipment panel, owner's want first |
| `0x0086` | 6 | 2 | word, word, array16, 3 bytes | `0x015D` in sequence | `0x0084C890` | dropped — the pair's other half |
| `0x0089` | 5 | 5 | header only | load burst | `0x008526E0` | dropped — the 5 character-creation connections |
| `0x008B` | 5 | 5 | string16(20), blob8, dword | `0x0099` 5 of 5, then `0x0188` | `0x00852740` MsCliMsg | dropped — character creation's name commit (the string is a typed character name) |
| **`0x009F`** | 3 | 1 | word agent_id | **`0x00B0` 3 of 3, then `0x01BF`** | `0x0085BE40`, 1 caller | **NAMED `HENCHMAN_ADD` (medium)**; dropped until step 5 |
| **`0x00B1`** | 10 | 10 | word, byte, word, byte, byte | **`0x01D9` 9 of 10, then `0x01A5`, `0x0099`** | `0x0085C280`, 0 direct callers | **NAMED `MAP_TRAVEL` (medium)**; dropped until step 7 |

Loopback counts for the same opcodes (UNHANDLED events, one per connection per
opcode, over the 1,557 loopback connection logs under `vault/captures/gamesrv` —
1,553 plus 4 in `hop2/`; "3,107 gamesrv captures" in the first cut was the
directory's entry count, `.jsonl` and `.raw` together): `0x0008` 1,027, `0x000B`
1,395, `0x000C` 76, `0x000D` 1,384, `0x0023` 2, `0x0044` 1, `0x0045` 8. These are
FLOORS — an UNHANDLED row was only logged from about 2026-08-11, so an older log can
decode a c2s without one, which is how `0x004F` has ONE loopback decode (2026-08-10)
and zero UNHANDLED rows. The other ten our client has never sent. So four of the
eighteen had been falling off the dispatch chain on
nearly every loopback connection for weeks, unremarked — the class the reverse
guard exists for.

**Three names, each from an OBSERVED reply chain, each medium, each ALSO on the
allowlist until its arm ships** (a name in `overrides.json` obliges an arm or a
reason — `test_dispatch` §7): `0x009F` HENCHMAN_ADD — `[agent]` of the outpost
henchman, answered within 31–132 ms by `0x00B0` PLAYER_PARTY_SIZE and THEN the
`0x01BF` roster row, 3 of 3 on `20260819T132414 :53419` (**size before row**; the
hero KICK answers row `0x01C3` then size, so the hero ADD below mirrors the
henchman, not the kick); `0x00B1` MAP_TRAVEL — `[map_id, 0, 0, 0, 1]` answered by
`0x01D9 [2, 1, '']` then the transfer pair `0x01A5`/`0x0099`, 10 of 10 in sequence,
followed by c2s `0x0008` every time; `0x004F` ITEM_MOVE — `[byte, word, byte]`
answered by `0x014B` ITEM_CHANGE_LOCATION (4 of 4) with `0x006F` beside it on 3 of
4, on `20260917T090355 :53310` (three sends) and `20260919T103604 :58638` (one);
fields 2–3 are the DESTINATION bag and slot — `0x014B`'s own reply `[_, item, bag,
slot]` echoes them 4 of 4 (`[4, 2, 1]` → `[1, 213, 2, 1]`, `[1, 136, 6]` → `[241,
17730, 136, 6]`) — CORROBORATED from the reply; field 1 (4, 6, 5, 1) is UNVERIFIED.
**CORRECTED in the D1 fix pass (2026-09-23):** the first cut of this row cited
`20260913T210901` and `20260914T005758`, which hold no `0x004F`, said `0x006F`
followed 4 of 4, and claimed zero loopback arrivals — there is ONE loopback decode
(`authsrv-20260810T151946-c1`, t=334.0, `[0, 4, 1]`), from before UNHANDLED logging.
The route's "one caller
`0x004A791F`" for the travel wrapper is not what the census reads — `0x0085C280` has
NO direct caller on 38797 (reached through a pointer); the survey text stays
unverified there. The fifteen others are UNNAMED on purpose: a name is DESKWORK-D2's
product, and each allowlist row says what was measured and what would name it.

**What the first-reply column is and is not.** A CORRELATION on a busy wire. The
kick's own row shows it: c2s `0x001F` at t=158.676 is followed at 21 ms by an
outpost `0x0029` (some other agent moving) and only at 42 ms by its batch, so even
the clock-skipped column names `0x0029`, not `0x0075`. Where a reply is real it is
unmistakable (`0x009F` → `0x00B0` 3 of 3; `0x00B1` → `0x01D9` 9 of 10 first, 10 of 10
in sequence); where it is not, the column says so by scattering. A tape-locked test
pins a batch by BYTES (`test_herokick` §1), never by this column.

**The guard.** `test_dispatch.py` §10 reads `retail_c2s.json` (no vault, as that
test insists) and reddens on any opcode retail sent that is neither handled, named
nor dropped on purpose — with floors on the file (57 opcodes, 96 connections; the
corpus is append-only) so an empty or shrunken census cannot pass vacuously, and
two known-bad arms (an undecided `0x00FE` in a fixture census; the `0x0008` row
deleted). Its orphan rule widens: an allowlist row may answer "why is this opcode
RETAIL SENDS dropped" as well as "why is this NAMED one dropped".
`test_c2striage.py` (floor 34) drives the walker on a synthetic stream (the check
the vault cannot give — on a real tape every c2s has SOME s2c after it, so a walker
pointed one message off would still fill every column), re-derives the census from
the vault, holds the committed file to it (a new tape with a new opcode reddens
until `--write` runs and the opcode is triaged), and proves acceptance (c): **zero
retail c2s opcodes are neither named nor `DROPPED_ON_PURPOSE` with a reason**, over
the file and over the live census.

### The hero add — `c2s 0x001E HERO_ADD`, RECONSTRUCTION (DESKWORK-D1 step 4, 2026-09-23; corrected by the fix pass the same day)

**CORRECTED 2026-09-23 (the D1 fix pass), and read this list before the section.**
Two reviewers re-derived the first cut from the tapes and the binary; the census and
the batch's shape held, and six claims did not. They are corrected in place below and
the first cut's wording is quoted where it matters: (1) the send gate `0x0084D9B0` is
not "a flag word" — it is **`MissionCliGetMap()`**, and the client sends `0x001E` (and
the kick) **in an outpost only**; the inference "the kick fired on loopback, so the gate
is not what kept the add off our wire" is withdrawn. (2) The retail load order was
misquoted in exactly the part the add left out: retail declares the hero's **inventory
container before its block**, and `0x0073` sits inside the *player's* block. (3) The
add re-activated a hero naming an inventory key the kick had **destroyed** — the
`ItCliApi:488` chain pvpui §26.2 already priced; it now re-declares the key. (4) The
"default ON" rationale held only for the commander rig; in the legacy rig (plain
`--hero`) the load never sends `0x0072`, so the add now **refuses** there. (5) The body's
formation slot compacted after a kick — two bodies on one slot and one item id; it is
now the hero's **owned** slot. (6) `0x0018`'s bit = hero index is CORROBORATED on 15 of
the 17 comparable connections, not 34, and the 2 contrary show the mask is the
**account's** superset. Also: `0x009A` under `--hero-char` was missing from the batch;
`HEROES_PARTY_MAX` was not read by `main()`; the `ChCliAttrib:313` dependency was
unrecorded; the loopback denominator was 1,557 connection logs, not 3,107.

**Two nulls first, both measured.** No retail tape carries a c2s `0x001E` — 0 of 96
live game connections (`c2striage.py`, the 57-opcode census above) — and no loopback
connection log does either: 0 of 1,557 (`vault/captures/gamesrv`, 1,553 plus 4 in
`hop2/`) hold a decoded or unhandled `GAME_CMSG` 30 (the kick's `0x001F` is in one).
Our own client has never sent the add to our server, so unlike the kick there is no
loopback witness to lean on; the whole arm is RECONSTRUCTION and every message in it
is labelled below. `schema/overrides.json` GAME_CMSG 30 carries the name at **low**
confidence for that reason (static only).

**What is READ, statically (38797; `sendsites.py`, `msghandler.py --callers`,
`codescan.py --dis`).** The game-channel wrapper is `0x0091FF00` (site `0x0091FF1F`,
8 bytes; `0x00920880` on 38888, `0x0091FF60` on 38833/38849, `0x00915CC0` on 38519),
its one caller inside ChCliApi `0x0080E250`: `cmp esi, 0x28 / jl` then `test esi,
esi / jne` — the assert pair `hero < HEROES` (ChCliApi:4446, line `0x115E`) and
`hero != 0` (:4447) — then `call 0x0084D9B0; test eax, eax; jne skip; push hero; call
0x0091FF00`. **The gate is `MissionCliGetMap()`**: `0x0084D9B0` is `mov eax,
[ctx+0x44]; mov eax, [eax+0x238]; ret`, the function `studies/maprows/FINDINGS.md`
already names (OBSERVED, from the compiled comparisons: `MISSION_MAP_OUTPOST == 0` by
QuestLog:261, `MISSION_MAP_GAME == 1` by MsCliApi:251), so the send happens only when
the instance is an **outpost**, and **the kick's twin `0x0080E2A0`** (asserts `hero <=
HEROES` :4459, `!= 0` :4460, then the same call and `call 0x0091FF30`) **has the same
gate**. Consequences the first cut missed: in a field the client sends neither the add
nor the kick; the retail kick witness *was* an outpost; the loopback kick witness
(20260913T093718) ran with our `0x0199` explorable byte 0; and the add's field-body
arm is reachable from a real client only under `--party-body-in-outpost`, because
`party_bodies_here` and the `0x0199` byte are built from the same switch. The survey's
two callers hold: `msghandler --callers 0x0080E250` gives `0x00562FB0` (PtSearch, after
PtSearch:774 `m_activeList == LIST_HEROES`) and `0x00577A3F` (UiCtlInstance).
`values[1]` is the hero INDEX by the wrapper's own bounds and the kick's two witnesses
(`[6]` retail, `[3]` loopback) — the shape `0x001F` shares.

**Retail's load order for one hero, as the tape has it.** Heroes §38: the commander is
created SYNCHRONOUSLY on `0x01C2` from state other messages install, so the hero
pipeline must precede the roster row. The kick tape's load (`20260916T150306 :62321`,
151.746–151.784 s) shows the order, and it is this — not the first cut's "the hero
agent's `0x0037`, `0x00B7`, `0x00DA`, `0x0065` ×2, `0x0073`, `0x003A`, `0x0144`, then
`0x0072`": the **player's** block (agent 642: `0x0037`, `0x00B7`, `0x00B6`, `0x00DA`,
`0x009F` ×2, `0x009C`, **`0x0073 [6, …]` inside it**, `0x003A`, …), then **the hero's
inventory container** — `0x0144 [96, 1]`, `0x013F [96, 2, 21, 226, 9, 0]` and seven
`0x0161`+`0x013E` items into 96 — then **hero 379's block** (`0x0037`, `0x00B7`,
`0x00DA`, `0x0065`, `0x00A2` 43, `0x009F` 41/42, `0x009C`, `0x0065`, `0x003A`), then
`0x0072 [6, 379, 96, 2]` at 151.747; the world's creates (no `0x0020` for 379 — an
outpost); then at 151.784 `0x009A [379, 100 << 24]`, `0x009F` 36 (level), `0x00A6`, …,
`0x00B0 [68, 2]` (the size already counting the hero), `0x00B1`, and the build window
`0x01D2 [28]`, `0x01CB [28, 68, 1]`, `0x01C2 [28, 68, 379, 6, 3]`, `0x01D3`, `0x01B2`.
Inventory → block → activate → char table → size → row. **The only mid-session ADD on
any tape is the henchman's** (`0x009F`, 3 of 3 on `20260819T132414`): `0x00B0 [14,
n+1]` THEN the `0x01BF` row, same millisecond, no build window — size before row,
bare. The kick goes the other way (`0x01C3` row, then `0x00B0`), so the add mirrors the
henchman add and the load, not the kick.

**Handler asserts, read before sending anything mid-session (38797, `msghandler
--follow --annotate`, `codescan --dis`).** `0x01C2` (`0x00856B80` → `0x00858F50`) looks
the party up by id, grows the row array, writes the six fields, fires event
`0x1000011E` and calls `0x7DFED0(owner)`; the only assert in range is Array:369 — **no
build-window gate**, so a bare `0x01C2` is not refused by its handler (RECONSTRUCTION
that it is accepted: no tape shows one bare). `0x0018` (`0x00804670` → `0x00807CF0`)
resizes an array at `ctx+0x28+0xB4` to the count sent, copies, fires `0x100000BF` —
any count accepted. `0x009A` (`0x0091EC40` → `0x00812640`): Array:587 only, no
create-once, so re-registering an agent is legal. `0x0144` (`0x00846260`) asserts
**ItCliApi:2010 `!inventory`** — a key may be declared ONCE; `0x013F` (`0x00846040`)
asserts ItCliApi:1942 `inventory` and **ItCliInv:129 `!m_bagEquip`** — one equipped bag
per container; `0x0145` (`0x008462B0`) asserts ItCliApi:2024 / ItCliInv:1042
`inventory` — the key must exist. **`0x0037`'s creator asserts ChCliAttrib:313
`!attribState`** (heroes §13.1) — the one create-once assert in the block, which the
first cut's read left out: the block is legal only for an agent whose attribState is
gone, and `hero_kicked` guarantees that — a kick THIS connection sent `0x00F8`, whose
sweep removes the agent's `+0xAC` attribState (pvpui §31.1), and a kick seeded from the
store means the load skipped the block for this hero. **Whether the kick destroys the
hero record was READ rather than assumed** (the review asked): the `0x0075` worker
`0x0081DC50` and the `0x00F8` sweep's `+0x584` remover `0x0081D880` have the same body —
find the agent-keyed ACTIVATION record (`0x0081D270`, the 36-byte-stride array), look
the hero record up by its hero id in the array at container `+0x10` (`0x0081D320`,
asserting ChCliHero:291 / :119 `charHeroData` if absent), write **`heroData->agentId =
0`**, memmove the activation record out of its array, decrement the count, fire
`0x1000003B`. **Neither deletes the hero record.** `0x0075` returns quietly (a
`0x0046ED40` log) when there is no activation record; the sweep jumps to its return —
which is why retail's own batch can carry both. So after a kick the record `0x0072`
asserts on (ChCliHero:199) exists with `agentId` 0, and `0x0072` — the only writer of
`heroData->agentId` — re-creates the activation record. **`0x0073` is therefore NOT
re-sent**, and that is now CORROBORATED statically rather than inferred from retail's
next loads (which, the review noted, send `0x0073` for every owned hero regardless).

**What the server now does (`handle_hero_add`, behind `--no-hero-add`).**

- Refuses, sending NOTHING: an index that is not an owned hero; a hero not kicked
  (already in the party); an eighth hero — `HEROES_PARTY_MAX = 7`, one name for the
  client's own cap (PtPlayer:332 `heroIndex < arrsize(m_heroAgentId)`,
  GmHeroCommander:214), now read by `--hero`, `--party` **and** the handler, whose
  check is DEFENSIVE (both command-line gates cap the OWNED set, and an add is of an
  owned kicked hero, so it cannot fire from any command line today); and **the legacy
  rig** — not `HERO_RIG_RETAIL`, or `HERO_ACTIVATE` off, which plain `--hero N` is.
  That rig's load sends `0x0074` for party heroes only and never `0x0072`, so after a
  persisted kick and a zone the client holds no hero record for the kicked hero and
  the batch would assert ChCliHero:199 on its `0x0072` (heroes §11.3). The add is armed
  for the **commander rig** — what `--party` sets (`hero_activate`, `hero_char`,
  `hero_inventory 2`, `hero_bags`, `hero_pipeline_first`), the only rig whose load
  sends `0x0072` at all; `--reset-hero-kicks` stays the way back in the legacy rig.
  What retail's client expects back from a refused add is NOT FOUND (no tape).
- Sends, in the commander rig's own load order with the size/row pair adjacent:
  **(0)** if a kick's `0x0145` destroyed the heroes' inventory key
  (`state["hero_inv_destroyed"]`), the key back FIRST — `hero_inventory_declare`, the
  load's own `0x0144 [key, 0]` + equipped bag `0x013F`, one function for both callers
  (retail declares the hero's container before its block; declared once per key, so
  only after a destroy; nothing with `--hero-bags` off); **(1)** `hero_character_block`
  (the load's own; §14's gates cleared the same way); **(2)** `0x0072`; **(3)** `0x009A
  [agent, 100 << 24]` under `--hero-char` — the load registers party heroes only, so a
  hero kicked across a zone would otherwise be unregistered and the commander click
  would hit Array:587 again (pvpui §27); **(4)** in a FIELD, the body through
  `hero_body_create` at the hero's **owned** slot (`hero_owned_slot`: its position in
  `hero_slots()`, never its index among the party heroes — with heroes [5, 6, 7] and 5
  kicked at load, 6 and 7 hold slots 1 and 2 and items 211 and 212, and the re-added 5
  takes 0 and 210; the first cut's rule gave 5 hero 6's slot and item), BEFORE the roster
  row, which is where the commander rig's own load puts it (body at index 52 of that
  load, `0x01C2` at 61 — the first cut sent it after and called that the load's order);
  **(5)** `0x00B0` with the hero counted and **(6)** a bare `0x01C2` with the load path's
  own arguments `[1, PLAYER_NUMBER, agent, hero, HERO_MSG14]`. A town gets no body, as at
  load, and since the client sends the add in an outpost only, the body arm is
  reachable only under `--party-body-in-outpost`.
- Clears the stored kick under `--persist` (`set_hero_kicked(..., kicked=False)`), so
  the next zone-in parties the hero again — the kick's acceptance (b) in reverse.
- **The kick learned one guard from this**: it records the `0x0145` it sends, and
  never destroys a key it already destroyed (kick → kick sends no second `0x0145`;
  kick → add → kick destroys a live key each time, because the add re-declared it).
- **The load path's `0x00B0` under-count is fixed with it**, now behind
  `--party-size-no-heroes` (the revert arm the first cut shipped without):
  `_party_size` counts `party_hero_slots`, as retail's load `[68, 2]` does.

**`0x0018` ships with it, from the sandbox's owned set — a labelled policy.** Retail
sends ONE dword on all 34 live connections that carry `0x0018`: `[64]` (bit 6) on 19,
`[224]` (bits 5, 6, 7) on 15. **Bit = hero index is CORROBORATED on 15 of the 17
connections that also carry `0x0073` to compare against; on the other 2**
(`20260914T005758 :51659` and `20260916T150306 :62321`, the kick tape) **the mask is
`[224]` while `0x0073` names hero 6 alone** — the mask is a SUPERSET of the character's
heroes there, i.e. the **account's** unlock set, not the roster. (The first cut said
"CORROBORATED on 34 connections" for the owned-set reading.) This server has no
account-level hero state, so `hero_unlock_mask()` builds retail's shape from
`hero_slots()` as a stand-in, keeps OpenTyria's all-ones with no hero authored or under
`--no-hero-unlock-mask`, and the sender stays ONE site — the PvP-arm burst whose `0x001D`
comment records the 2026-09-15 crash (a second sender of unlock state wiped the skill
library and asserted GmSkSlot:206). What consumes the mask is NOT FOUND statically (the
handler fires event `0x100000BF`); the route's reading that the Party Search hero list
draws from it is UNVERIFIED and the loopback click is what tests it.

**The default is ON for the commander rig, and here is the evidence for that call.**
Against: the request is unwitnessed and the bare `0x01C2` unwitnessed. For: in the
commander rig every message the arm sends is one that rig's load already sends this
client for this hero, in that load's order (heroes §38: zero asserts in it); the
create-once asserts in the batch are each cleared by construction (`!attribState` by
the kick's `0x00F8` or the load's skip; `!inventory` by re-declaring only after a
destroy); the kick it inverts is OBSERVED; the only mid-session add on tape is bare
and size-then-row; and the owner's ask is add AND kick from the party panel. Where the
claim does not hold — the legacy rig — the handler refuses instead of sending. The flag
is the control arm; a client assert on the click flips it off and names the gate.

**Tests.** `test_heroadd.py` (floor 78, from 48): the batch op-for-op against
`hero_character_block` and the order predicate `add_order` (known-bad: a rotated batch,
the KICK's row-then-size, a re-sent `0x0073`/`0x0074`, a body AFTER the row, an
inventory re-declaration that is not first); the rig gate (HERO_ACTIVATE off refused,
`--hero-rig-legacy` refused, the commander rig as control); the three refusals with an
unowned index that IS in the kicked set (so only the owned check can refuse it — the
first cut's arm was vacuous) and the seventh-hero control; the round trip under
`--persist`; the field arm's body BEFORE the roster pair, the owned slots with [5, 6, 7]
and 5 kicked (the first cut's collision shown), the re-create, the town as known-bad;
the sandbox rig — kick destroys key 2 and records it, the add re-declares `0x0144 [2, 0]`
+ `0x013F` first and registers `0x009A`, kick → add → kick destroys the live key again,
kick → kick never twice, two heroes keep the key, bags off re-declares nothing, char off
sends no `0x009A`; the `0x00F8` in the kick batch; the mask's values and flag; source
locks by syntax tree with mutations — the arm, the three flags, the rig test before the
un-kick, `hero_kicked` in the handler, both `hero_body_create` callers passing
`hero_owned_slot`, `_party_size` behind `PARTY_SIZE_COUNTS_HEROES` (a flagless count
fails), `hero_inventory_declare` with two callers and the flag's set/clear sites, one
`0x0018` sender, `main()` reading `HEROES_PARTY_MAX`. `test_herokick` 53 and
`test_agentlife` 552 unchanged in count on the edited load path.

**Runsheet — the two clicks, still owed (one loopback session, the owner's hands).**
Not run here; this is what to do and what each outcome means. Rewritten by the fix
pass: the first cut's command ran the legacy rig (where the add now refuses), sent the
owner to a field for the body arm (where the client never sends the add), and named a
log line the arm-off path does not print.

1. **The rig is the sandbox's** — the commander rig, the one the add is armed for. Use
   the Orchestrator's Compile with at least one hero ticked (it passes `--party sandbox
   … --persist`), or by hand in the game-catalog terminal:
   `python toolkit/authsrv/authsrv.py --bind 127.0.0.3 --port 6112 --vault vault/captures/gamesrv --hero 6 --hero-activate --hero-char --hero-bags --hero-inventory 2 --persist`
   (the other terminals per `RUNBOOK.md`; launch the loopback client as usual). **Stay
   in the outpost for the clicks** — the client's `MissionCliGetMap()` gate sends
   `0x001E`/`0x001F` from an outpost only. For the body arm add `--party-body-in-outpost`
   (a field never gets the click).
2. **Kick.** Party window → the hero's row → its remove button. Expect the row to
   leave and the gamesrv log to print `HERO_KICK: hero 6 (agent 200) removed from the
   party; size now 1` (and `PERSIST: hero 6 kicked`, and with the sandbox rig
   `INVENTORY_DESTROY(key 2)`). A row that stays with no `HERO_KICK` line means no c2s
   reached us; with `--no-hero-kick` the log prints `HERO_KICK ignored (--no-hero-kick)`.
3. **Add.** Party window → the hero list (Party Search's Heroes tab, or the hero
   panel's add) → the hero. The outcomes, each with its reading:
   - the log prints `HERO_ADD: inventory key 2 re-declared (0x0144 + 0x013F)` then
     `HERO_ADD: hero 6 (agent 200) back in the party; size now 2` and the row returns →
     the add is CORROBORATED on our client (the batch, order, re-declaration and bare
     `0x01C2` accepted); under `--party-body-in-outpost` a body ~150 u beside the player
     → the field arm too; **then click the hero's row in the party window** — the equip
     walk (ItCliApi:488) is what the re-declared key exists for;
   - the log prints nothing after the click → the client did NOT send: the UI offered
     no add for this hero (what the `0x0018` mask means to the client is UNVERIFIED —
     retry with `--no-hero-unlock-mask`, whose all-ones mask is what every earlier run
     sent), or the instance was not an outpost;
   - the log prints `HERO_ADD(n) refused: ...` → read the reason: an index we do not
     own, a hero already in, or `the load ran the LEGACY hero rig` (the command lacks
     `--hero-activate`, or has `--hero-rig-legacy`) — the number and the reason in the
     line are the evidence;
   - the client asserts → copy the dialog's `File.cpp(N)`; `--no-hero-add` is the revert
     while it is read. The static read could not exclude a gate in the roster row
     (`0x01C2` bare) or the commander (heroes §38); ItCliApi:488 / ItCliApi:2010 would
     mean the inventory bookkeeping is wrong; ChCliHero:199 would refute the
     "kick keeps the hero record" reading above.
4. **Kick again** (the kick → add → kick path): expect `INVENTORY_DESTROY(key 2)` a
   second time and no assert — the key was re-declared, so the second destroy is legal.
5. **Persist across a zone.** After an add, leave the town through its portal into the
   sandbox area and come back (the world map's travel `0x00B1` is dropped on purpose
   until step 7, so do not use it) and confirm the hero loads in the party (`0x0072` /
   `0x01C2` in the log); after a kick, that it does not — and then add it back from the
   outpost, which is the kick → zone → add path (the load skipped the block, so the
   add's `0x0037` is legal; the load registered no `0x009A` for it, so the add's does).

### The hero skill toggle — `c2s 0x0019 HERO_SKILL_TOGGLE`, RECONSTRUCTION (DESKWORK-D1 step 6, 2026-09-23)

**Desk work, no client launched.** The route asked whether `0x0019 [hero, slot < 8]`
means "toggle this slot's suppression" or "use this skill now", and what the client
expects back. Both were answered from the binary, the corpus and the wiki; nothing was
run.

**The message, statically (38797; `sendsites.py`, `codescan.py --xrefs/--dis`,
`msghandler.py --callers`, `asserts.py --at`).** The game wrapper is `0x0091FD80` (12
bytes; `0x00920700` on 38888, `0x0091FDE0` on 38833/38849, `0x00915B40` on 38519), and
the census's "0 callers" is because it is reached by a tail `jmp` from ChCliApi
`0x0080E000`, which asserts the hotKey bound (below 8; ChCliApi, source line 4359) and — unlike its neighbours
`0x0080E030`/`0x0080E050`, the `0x001A`/`0x001B` senders, which gate on
`MissionCliGetMap() == 1` — has **no map gate**. The schema's shape holds: `[agent_id,
dword]` = the hero's AGENT and the panel slot. `0x0080E000` has two callers, both in the
UI, and **both send only under a modifier:**

- **GmSkSlot's click, `0x00543480`** (the skill-slot widget, `this+4` the agent, `+8`
  the hotKey, `+0x10` the slot's skill): the agent must be a hero (`0x0080E390`, the
  `+0x584` activation table), the slot non-empty, and a QUERY event `0x100001A7` (fired
  with an out-parameter) must answer nonzero; only then `0x0080E000(agent, hotKey)`.
  Otherwise the click falls through to the plain paths (`0x00816060(9, agent)` etc.).
- **GmView's hero-hotkey handler, `0x004E8A20`** (`(heroIndex, hotKey)`; it walks the
  hero list through `0x00524D70`/`0x0080E2F0`, takes `heroData+4` as the agent, and
  requires the slot to hold a skill via the hotKeyState getter `0x00816EA0`,
  ChCliApi:6253): `test [0xC078D4], 0x10000` → send `0x0019`; else, in an explorable,
  the CLIENT-SIDE use path — `0x00816FE0` / `0x0080E0A0` / `0x0080E070`, thin wrappers
  over ChCliSkill's hotKeyState methods (`0x00821260` sends `0x001C` via `0x0091FE50`,
  `0x005C` via `0x009210F0`).

`0xC078D4` is GmView's flags word — bit `0x10000` is set once (`0x004E97C5`) and read at
three GmView sites (`0x004E554A`, `0x004E8AC1`, `0x004ED360`), and the query event
`0x100001A7` is one of a block GmView subscribes to one handler (`0x004ED21B`,
`0x100001A3`…`0x100001B5`), so both senders gate on the same GmView-held modifier state.
**So `0x0019` is the MODIFIED hero-skill action and the plain one never leaves the
client.** GWW names the modified action (WIKI, GWW "Guide to Hero Basics and
Optimization" §Forced skill use → *Suppress*; the page "Hero Control panel" redirects
there; raw wikitext read 2026-09-23 through the browser): *"Hold down your suppress key
(standard: left shift) and left-click on the hero's skill in the hero control panel to
suppress it. It'll be marked with a stroke-through red circle."* The same section's
*Force* entry is the plain click: *"By clicking on a skill in the hero control panel you
force the hero to use it."* The route's pre-registered reading —
**toggle, not use** — stands; its "ctrl-click" is corrected to the suppress key (Shift
by default; Ctrl only if rebound).

**The corpus.** c2s `0x0019`: **0 of 96** live game connections (`retail_c2s.json` has
no row) and **0 of 1,557** loopback connection logs (no UNHANDLED opcode-25 row, no
decoded one). s2c `0x0064`: **0** on the live corpus. s2c `0x0065`: **8**, every one
`[hero, 0]`, twice per hero in the load block (heroes 117, 30, 324, 379). One of those
heroes then casts: agent 30 on `20260914T005758 :56011` opens 50 casts (`0x00E4`) after
its `[30, 0]` — so **mask 0 is not "all suppressed", and bit = 1 is the suppressed
slot** (polarity RECONSTRUCTION from that one witness; the direction the wiki's prose
implies).

**What the client needs back.** Its hotKeyState mask (`+0xA4`, pvpui §30.2) is written
FROM THE WIRE by two handlers, both read to the end and **assert-free**: `0x0064`
(`0x0091E040 → 0x00810820 → 0x00822050`: find the agent's entry, `bts`/`btr` the bit,
fire event `0x1000005A {agent, bit, value}`; an unknown agent returns silently) and
`0x0065` (`0x0091E060 → 0x00810850 → 0x008220D0`: write the whole byte, diff eight bits,
one event per changed bit). GmSkSlot subscribes to `0x1000005A` (`0x00542470`), which is
the redraw. (This paragraph used to say the mask is written *only* by those two; the fix
pass below found four more writers, all the client's own — the bar edits and the `0x00DA`
setter — and the server now follows them.) **The server answers with the whole mask, `0x0065 [hero agent, mask]`** —
retail's only observed writer of the field (8 of 8), the message the load already sends
this agent; `--hero-skill-toggle-per-bit` sends the route's pre-registered `0x0064
[agent, slot, value]` instead, a message no retail tape carries.

**The model (`handle_hero_skill_toggle`, behind `--no-hero-skill-toggle`, default ON).**
A per-hero 8-bit mask in party state (`state["hero_skill_disabled"]`), bit = slot of the
PANEL's bar — the eight slots `hero_character_block` sends in `0x00DA`, now built by one
function (`hero_panel_bar_ids`) so the mask and the bar index the same array. The click
flips the bit and sends the mask; the hero's BODY refuses to pick a suppressed skill:
`pick_skill` skips a slot whose skill id is in the row's `skill_disabled_ids`, a set the
handler, `hero_body_create` and `sync_hero_body_bar` keep current from the mask joined
to the panel bar **by skill id**, because the body's `skills` list drops empty slots and a
bar with a hole (`[322, 0, 348, …]`) would otherwise suppress the wrong skill. Under
`--persist` the mask is written to the hero's row (`charstore` `disabled_slots`, 0..255,
validated) and the next load's two `0x0065` rows carry it, so the struck-through slot
survives a zone; the default wire is byte-identical (`[hero, 0]`, retail's value).
Refused with nothing sent (retail's refusal NOT FOUND): an agent that is not a party
hero, a slot outside 0..7, an EMPTY panel slot (both client senders check the slot
holds a skill before sending). `test_heroskilltoggle.py` (floor 53) drives all of it,
with the KNOWN-BAD join by list index. `schema/overrides.json` GAME_CMSG 25 names it
HERO_SKILL_TOGGLE at LOW (static only).

**What this does NOT cover, said plainly.** The plain hero-skill click (order the hero to
use a skill now) is the client-side path above — ChCliSkill's use method `0x00821260`
(ChCliSkill:219) sends `0x001C` through `0x0091FE50`, explorable-gated, and nothing else
(the first cut also named `0x005C` here; that is the BAR EDIT's sender, `0x008212C0`,
ChCliSkill:258 — not part of the use path); whether retail's server re-sends `0x0065` on
a bar edit is UNOBSERVED. Whether suppression follows the SLOT or the SKILL on a
rearrangement was written up as UNOBSERVED too, and that was wrong — the client's own
code answers it, and the fix pass below records the answer and moves the server to it.

**Runsheet — the owner's click (one loopback session, the sandbox rig; the toggle is
independent of the outpost gate, so a field works too).**

1. Start the sandbox as usual (the hero-add runsheet's command, with `--persist`), load
   in with at least one hero in the party, and open its skill bar: the party window's
   hero row, or the hero's own panel (the hero control panel via its portrait).
2. **Hold the suppress key — Left Shift by default (`Options → Control` names it
   "Suppress"; Ctrl only if the owner rebound it) — and left-click one of the hero's
   skills.** Expect the skill to draw a struck-through red circle and the gamesrv log to
   print `HERO_SKILL_TOGGLE: hero 6 (agent 200) slot N (skill S) SUPPRESSED; mask 0x00 ->
   0x..; the body skips it`. That line is the OBSERVED half: the client did send `0x0019`
   for this click and the shape is `[agent, slot]`. The red circle is the client
   accepting `0x0065` as the mask writer. Click the same skill again with Shift held →
   `released`, the circle gone.
3. In a field, watch the hero for a minute: it must never cast the suppressed skill
   (the log's per-cast lines name the skill id) and must keep casting the others.
4. Outcomes: **no log line** → the click did not send (a different modifier is bound to
   Suppress; check `Options → Control`), or the click was a plain one (the hero used the
   skill instead — that is the `0x001C`/`0x005C` path, not this arm). **A `refused:`
   line** → read its reason (an empty slot, a non-party hero). **The circle does not
   appear but the log line does** → the client did not redraw on `0x0065`; retry with
   `--hero-skill-toggle-per-bit` (`0x0064`), which separates "wrong message" from "wrong
   polarity". **The hero still casts it** → the body's join is wrong; the log's
   `now casts […]` line after a bar edit and the mask line are the evidence to file.
   The client asserting on either message would refute the static read (`0x00822050`
   / `0x008220D0` have no assert); `--no-hero-skill-toggle` is the revert.
5. **A hero bar swap while a skill is suppressed** (the fix pass's arm): with a skill
   struck through, drag it onto another slot of the hero's bar. Expect the red circle to
   travel WITH the skill on screen (the client's own routine) and the log to print
   `HERO_SKILL_TOGGLE: hero 6 mask 0x.. -> 0x.. -- the client's 0x005E swap exchanged
   bits A and B (0x00821460); suppression follows the skill`; the hero must still never
   cast that skill and must cast the one now in its old slot. A `not in _dis`-style
   miss shows as the hero casting the struck-through skill.

**Fix pass (2026-09-23, the same day; two reviews read).** Three things the first cut had
wrong, each re-derived from the client before it was changed:

- **The client edits the mask itself, and suppression follows the SKILL** (EVID-D1C-1,
  the blocker). `codescan.py --field 0xA4 --in ChCliSkill --writes` on 38797 finds **six**
  stores to hotKeyState `+0xA4`, not two: the `0x0065` handler (`0x008220D0`, the whole
  byte, at `0x00822102`); the `0x0064` handler (`0x00822050`, one bit, at `0x0082208D`);
  the `0x00DA` bar setter (`0x008223B0` → `mov [esi+0xA4], 0` at `0x00822751`, BEFORE it
  refills the slots — so a `0x0065` must FOLLOW `0x00DA` or the mask is lost); the
  whole-bar sender `0x00821390` (mask = 0 at `0x00821431`); the **`0x005C` sender
  `0x008212C0`** (ChCliSkill, source line 258; after it sends, the `btr` of bit `hotKey` in `+0xA4` at `0x00821356` —
  a SET clears the written slot's bit); and the **`0x005E`/`0x005F` sender `0x00821460`**
  (asserts `hotKey1` :332 and `hotKey2` :333; it sends `0x005E` through `0x009211C0`
  when both slots hold a skill, `0x005F` through `0x00921220` when one is empty, exchanges
  the two `0x14`-byte hotKey entries, and at `0x0082157D..0x008215A7` reads `+0xA4`,
  `bts`/`btr`s bit `hotKey1` from the old bit `hotKey2` and vice versa, and writes it back
  before firing `0x1000005E`). So after a swap the client draws the circle on the SKILL's
  new slot, while the first cut's server kept the bit on the old slot and its body cast
  the struck-through skill (the reviewer's `swap_demo`: bar `[322, 382, 348, …]`, slot 2
  suppressed, `0x005E [200, 322, 0, 348, 0]` → the body's picks began `348, 382, …`).
  **Now:** `handle_skillbar_skill_swap`'s hero branch exchanges the two bits and
  `handle_skillbar_skill_set`'s clears the set slot's, through `hero_mask_write` (session
  cache, the store under `--persist`, one log line), before `sync_hero_body_bar` re-joins
  the body — RECONSTRUCTION of the client's own arithmetic; the server's mask is a mirror
  of the client's. `0x005F` (a move into an empty slot) moves the bit the same way and is
  NOT armed on our wire (UNHANDLED); `test_heroskilltoggle.py` §3 drives both handlers and
  keeps the per-slot reading as the KNOWN-BAD arm.
- **The legacy rig drew no stored mask** (EVID-D1C-3, minor): the non-retail hero path
  (`HERO_SKILLBAR and not _rig_retail`) sent `0x00DA` with no `0x0065` after it, and
  `0x008223B0` zeroes the mask on every `0x00DA`, so under `--persist` a stored mask was
  skipped by the body and not drawn. Now a `0x0065` follows the bar there when — and only
  when — a mask is stored; the default wire is byte-identical.
- **A suppressed resurrection was still cast** (ENG-B2, blocker): `ally_cast_tick`'s
  "the dead first" loop picks a resurrection off the bar itself and never asked
  `pick_skill`; with Resurrection Signet struck through and the player dead, the hero
  raised the player anyway. The loop now skips a suppressed id (`_s[0] not in _dis`);
  §3b casts it once released, as the control.
- **Without `--persist` the toggle read a stale bar** (ENG-M1, major): `hero_panel_bar_ids`
  read the store's bar, else the row's, so a slot the client had just filled by `0x005C`
  was refused as EMPTY. Both bar-edit handlers now write the session's bar
  (`state["hero_bars"]`) whether or not a store is attached, and the panel expression
  reads it first (§3c).
- Smaller: the store's setter refuses a bool mask (the first cut's test let `True` store
  1); the all-suppressed log line says the hero stands; the GWW citation above is the page
  itself, not a search summary; `0x005C` is named as the bar edit, not the use path.

### Inventory — `c2s 0x004F ITEM_MOVE` and `0x0030 EQUIP_ITEM` armed on an item store (DESKWORK-D1 step 8, 2026-09-23)

**Desk work, no client launched.** Step 3 named `0x004F` from its reply chain with
field 1 UNVERIFIED and `0x0030` had been dropped since 2026-09-13 as "no state for it
yet". This step re-derived both from the tapes and the client, built the state, and
armed them. Everything below is on `toolkit/authsrv/itemstore.py` (the pure leaf: cells,
plans, refusals) and `test_itemmoves.py` (floor 102, the bare-machine core), which replays
every batch below **value for value against a transcription with retail's own ids** and,
with the vault present, **from the decoded tapes themselves** (§1b, `livewire.decode_conn`;
the fix pass added it — the first cut's "byte for byte" named a check the file did not
make).

**`0x004F`'s field 1, settled from the client.** The wrapper `0x00920DE0` (38797) packs
three dword arguments into the wire's `[byte, word, byte]`; it is reached by a tail
`jmp` from ItCliApi `0x00816AF0`, whose callers sit in **GmItemHelpers `0x00526900`**
(asserts `sourceItemId` :279, `ItemCliValidate(sourceItemId)` :280, `quantity` :281,
`targetBag < ITEM_BAG_SLOTS` :282, `quantity == sourceQuantityTotal` :310,
`sourceAgentId` :356). **Its gate is `0x008454F0(item)`**: the item's PARENT bag
(`item+0xC`) must be of **type 2 — the EQUIPPED bag** — and the answer is then the item's
slot byte (`item+0x50`); for any other bag it answers 9, and `0x00526900` branches to the
local path at `0x00526AC3` and sends nothing. The three arguments it pushes are that slot,
the target bag's id (`0x00844870(targetBag)`) and the target slot. (The first cut read the
gate as "the item's bag has model `0x15` = 21": `0x00844800` writes 21 into its first
out-parameter as the DEFAULT for any item that is not itself a bag container — it is
overridden only for an item of byte `+0x20` == 3 with a bag object at `+8` — so the `cmp
[ebp+8], 0x15` at `0x0052698C` refuses a dragged BAG (a non-empty one at `0x0052699C`) and
a backpack sword gets 21 too. Same conclusion, different mechanism; corrected by the fix
pass, EVID-D1C-2.) **So field 1 is the item's slot in the equipped bag and the source bag
is implied**; the general bag-to-bag move is another message and is on no tape. The hero
form is `0x0050 [agent, slot, bag, slot]` (`0x00920E30`). **CORROBORATED 4 of 4 by the
tapes' own cells at the moment of each move:** on `20260917T090355 :53310` the load's
`0x013E` put head 213 at (bag 3, slot 4), boots 214 at (3, 5), gloves 215 at (3, 6) — bag
3 being the type-2 equipped bag — and the three moves were `[4, 2, 1]`, `[6, 2, 2]`, `[5,
2, 3]` (head, gloves, boots, each from its cell); on `20260919T103604 :58638` item 17730
was set 0's OFF HAND (`0x0147 [241, 0, 24945, 17730]`), loaded at (231, 1) at 90.764 —
but it LEFT that cell on the set-1 switch (`0x014B [241, 17730, 136, 1]` at 150.310) and
came BACK to it by the `0x0152 [241, 13467, 17730]` at 224.681 (13467 having been placed
at (231, 1) by a `0x013E` at 176.813), so it sat at (231, 1) again when `[1, 136, 6]` moved
it at 232.975; that chain, not the load cell, is its witness (EVID-D1C-7). Step 3's "field
1 is UNVERIFIED" is retired; the route's "move item to bag/slot" was half the message.

**The replies, from the tapes.** A move: `0x014B [key, item, bag, slot]` (4 of 4) and
`0x006F [agent, visual slot, 0]` (the three field moves; not the outpost one). An equip
into an **empty** slot: `0x014B [key, item, equipped bag, slot]` + `0x006F [agent, visual
slot, item]` — 4 of 4, all in a field (`:60877`'s wand `[40]` → `[1, 40, 3, 0]` + `[9, 0,
40]`; `:53310`'s re-equips `[213]` → `[1, 213, 3, 4]` + `[25, 6, 213]`, `[215]` → `(3, 6)`
+ visual 5, `[214]` → `(3, 5)` + visual 3). An equip onto an **occupied** slot: **`0x0152
[key, occupant, item]` ALONE** — 4 of 4 on `20260819T132414 :53419` (Shing Jea, an
outpost: `[3451]` → `[159, 2767, 3451]`, `[1469]` → `[159, 3451, 1469]`, and back twice),
no `0x006F`, no `0x0147` within 2 s; the client's handler exchanges the two items' bag
and slot (weapons §29), so the occupant lands in the cell the item came from.

**Two slot orders, and both lineages were right about different arrays.** Retail's
equipped BAG follows ldufr's order (Legs 3, **Head 4, Boots 5, Gloves 6** — the cells
above), while the `0x006E`/`0x006F` VISUAL array follows GWLP-R's (Boots 3, Legs 4,
Gloves 5, Head 6 — newopcodes `0x006F`, corroborated again here: bag 4 → visual 6, 6 →
5, 5 → 3). The WHOLE permutation is OBSERVED at once on `:53310`'s load (the fix pass,
EVID-D1C-6): `0x013E` put items 209..215 at (3, 0)..(3, 6) and the `0x006E` that followed
read `[25, 209, 210, 211, 214, 212, 215, 213, 0, 0]` — bag 0→0, 1→1, 2→2, 3→4 (legs),
4→6 (head), 5→3 (boots), 6→5 (gloves); the first cut had attributed 0/1/2 to "the wand,
the off hand and the body slot's shared numbering" and left legs without a witness. `studies/character` §"CONTESTED" was a question about the visual array and
was decided right; the bag array was never asked. This server puts armour into the
equipped bag at the VISUAL slot (`STARTER_ARMOUR`, `wearmap.SLOT_*`) — legal, a bag cell
is opaque to the client — so OUR bag→visual mapping is the identity;
`itemstore.RETAIL_VISUAL_OF_BAG_SLOT` and `RETAIL_BAG_SLOT_OF_TYPE` carry retail's for
the replay, and the KNOWN-BAD arms show either mapping applied to the other array
misses the tape.

**The `0x006F` rule.** Retail rode it on every own-agent equip and unequip in a FIELD
(7 of 7) and on none in an OUTPOST (0 of 5: the four swaps and the off-hand move). For
the swaps that is CONFOUNDED (swap vs outpost); the outpost unequip breaks the tie
toward the outpost, and the set switch in a field (weapons §27: `0x0152` then three
`0x006F`) agrees. The server sends the visual in a field only, by the `0x0199`
explorable byte's own rule (`instance_is_field`); the field-swap visual is
RECONSTRUCTION and labelled at the send.

**Client asserts, read before sending.** `0x014B` (`0x00846520`): ItCliApi:2126 `item`,
and the shared add worker's ItCliInv:105 — the destination slot must be EMPTY, which is
why a filled destination is REFUSED rather than sent. `0x0152` (`0x00846840`):
ItCliApi:2253/2254 `item1`/`item2`, :2257 `inventory`, ItCliInv:687/688 both items in a
bag — which is why a set switch after an emptied hand may never send a `0x0152` with a
0 (below). `0x006F` (`0x0091E1E0 → 0x008110F0`): no assert.

**The model (`itemstore.py`; `handle_item_move`, `handle_equip_item`, behind
`--no-item-moves`, default ON).** The dress (REQUEST_ITEMS) now decides every item's
cell first — `item_layout_begin`: the constants' layout (weapon at equipped 0, the five
armour pieces at their slots, an off hand at 1, set items in the backpack, costumes at
7/8), then under `--persist` the character's stored cells through `itemstore.restore` —
and every placement sends the decided cell through `item_cell`, byte-identical to every
earlier run when nothing is stored. The two handlers plan against that store: a move
needs an item at the source slot and an EMPTY, declared, in-range destination in a
non-equipped bag; an equip needs a known, not-yet-worn item whose wire TYPE has a slot
(armour and costumes per type; a weapon type's `hands` row: one/two → 0, off → 1); a
two-handed lead entering while an off hand is worn sends the off hand to the backpack's
first free slot FIRST (RECONSTRUCTION from the set switch's shape); an off hand beside a
worn two-hander is refused (retail's answer NOT FOUND). Refusals send nothing. The
`0x006E` array and the player's `0x006D` lead are built from the store, so they cannot
disagree with the bag. **The hands and the weapon sets:** an equip into slot 0/1
rewrites the ACTIVE set's items (`SET_ITEMS_OVERRIDE`, read by `weapon_set_items`) and
the server's swing model through `apply_party_character`, the door a set switch uses;
a hand EMPTIED by `0x004F` is the open edge — the swing model keeps the last weapon's
numbers (an unarmed player mid-session is not modelled; `--no-weapon` is the
launch-time unarmed rig) and the log says so; `select_weapon_set` then enters the empty
hand by `0x014B` and never sends a `0x0152` with a 0. **Persistence:** every accepted
cell is written to the character's `item_locations`; the next dress restores armour and
set items where they were left, but **a stored HAND change is not restored** (slots 0/1
belong to the set machinery — logged, not applied); an illegal or colliding stored cell
discards the whole store for that login with the reason.

**What is UNOBSERVED and modelled anyway (each labelled at its site):** which set
record retail rewrites on an equip (its four swaps re-sent no `0x0147`); the field swap's
visual; a two-hander displacing a shield; the general bag-to-bag move (no tape carries
it; our client would send it on a drag between two bags — the log will show the opcode
as UNHANDLED, and that is the next arm). The PvP equipment panel (`0x0085`/`0x0086`)
stays out of scope. `schema/overrides.json` GAME_CMSG 79 and 48 carry the derivation;
`test_dispatch`'s allowlist lost both rows and `test_c2striage` §4 now requires both
ARMED.

**Runsheet — the owner's clicks (one loopback session; a FIELD for the visuals, the
sandbox rig as usual, with `--persist`).**

1. **Drag an armour piece out of the paper doll into the backpack** (Inventory → the
   equipped pane → drag the head or gloves onto an empty backpack cell). Expect the log
   line `ITEM_MOVE(equipped 6 -> bag 2 slot N): 2 message(s), item 7 -> bag 2 slot N`
   (the head; gloves are slot 5, item 6), the piece to appear in the backpack cell and
   the body to lose it (in a field). The log line is the OBSERVED half: the client sent
   `0x004F [source slot, bag, slot]` for a drag out of the equipped bag. **No log line
   but the item moved on screen** → the client sent a different opcode; the gamesrv
   log's `UNHANDLED` line names it (the general move — the next arm). **A `refused:`
   line** → read the reason (a filled cell; a bag we do not declare; a cell RESERVED for
   a worn set item's return — with `--weapon-set 1=…+starter_shield` and set 1 active,
   the shield's home cell is one). Then let a body hit you a few times: a hit on the head
   location now lands against a bare location (the log's `AR 0` on that location; the
   fix pass, ENG-B5) — a spell still meets the fixture's piece there (the open edge).
2. **Double-click the piece in the backpack.** Expect `EQUIP_ITEM(7): 2 message(s), item
   7 -> bag 1 slot 6` and the piece back on the body. Then **double-click a weapon set's
   lead in the backpack** (a `--weapon-set 1=starter_sword` launch puts item 11 there):
   expect `EQUIP_ITEM(11)` with a `0x0152` in the sent list (the hammer goes to the
   sword's cell) and `ITEMS: the hands are now lead 11 (starter_sword)`; the body draws
   the sword and its swing is the sword's interval.
3. **Drag a backpack item onto another EMPTY backpack cell.** This is the general move
   that is on no tape: expect NO `ITEM_MOVE` line and an `UNHANDLED` line naming the
   opcode; the client will show the item back where it was (nothing was answered).
   Copy the opcode into the study — it is what names the next arm.
4. **Zone and come back** (the portal, not the world map). Expect the head where it was
   left (backpack) — the log's `ITEMS: item 7 (armour, warrior_head) dressed at bag 2
   slot N -- the character's stored cell` line — and the weapon in hand whatever was
   done to it (the hand rule; the log prints `not restored (the weapon sets own slots
   0/1)` if it was moved). If the sword was equipped over the hammer before the zone,
   the new instance still creates item 1 as the HAMMER and item 11 as the sword (`ITEMS:
   the swing model is set 0's again`); two swords and no hammer would refute the fix.
5. The client asserting on `0x014B`/`0x0152` would refute the static read (ItCliApi:2126
   / :2253); `--no-item-moves` is the revert.

**Fix pass (2026-09-23, the same day; two reviews read).** Reproduced in memory against
the branch before each change, then fixed with a test that reddens without it:

- **Saved cells were never read back** (ENG-B1, blocker). REQUEST_ITEMS — the dress — is
  answered BEFORE REQUEST_PLAYERS, which is where the load attaches `charstore_game`
  (harness `20260922T175325`'s gamesrv log: c2s `0x8091` at line 84, the dress at 98, c2s
  `0x8090` at 132), so `item_layout_begin` read the store as absent on every real
  connection and restored nothing; the test had pre-seeded the store into the state.
  It now looks the store up itself (`find_character`, the pattern `hero_build` uses for
  the same reason); the test dresses a BARE state, with the no-store control.
- **The restored set-item slot was thrown away** (ENG-M2, major, latent behind B1):
  `declare_weapon_sets` re-assigned `WEAPON_SET_BACKPACK_SLOTS` from the constants after
  the dress had written the restored slots. It now leaves the map alone once a layout ran.
- **An accepted move could fill a worn set item's return cell** (ENG-B3, blocker): the
  next set switch then sent `0x014B` into a filled cell (the add worker's ItCliInv:105).
  `reserved_backpack_slots` names those cells; `plan_move` refuses one, `plan_equip`'s
  displaced off hand avoids one, and `select_weapon_set` — for the restored layout that
  can still fill one — sends the leaving off hand to a free cell instead and moves the
  reservation (the switch is refused before anything is sent when no cell is free).
- **An equip rewrote the launch-level records, and the next connection duplicated or
  lost weapons** (ENG-B4, blocker): `_item_hands_mirror` wrote set 0's record and
  `WEAPON_SETS[k]`, and the next dress created item 1 from the rewritten record (two
  swords, no hammer) or named an undeclared shield in `0x0147`. The per-session truth is
  `SET_ITEMS_OVERRIDE` alone; the records are never written from an equip; the dress
  re-applies set 0's record to the swing-model globals FIRST (which also closes the
  older set-switch form of the same bug); a set switch reads the swing model off the
  items now in the hands, not the record, so an equipped sword stays the sword on F1/F2.
- **Removed armour still protected** (ENG-B5, blocker): `player_armour_at` read the
  fixture. It now reads the item store: a piece out of the equipped bag leaves a BARE
  location (a rating of 0 plus the shield's bonus — RECONSTRUCTION; what retail deals to a
  bare location is on no tape). Open edge, said at the site: the spell path rolls its
  location inside `combatmath` with no state and still meets the removed piece.
- The record: the gate above (EVID-D1C-2), the 17730 chain (EVID-D1C-7), the whole visual
  permutation (EVID-D1C-6), the vault-gated replay from the decoded tapes (EVID-D1C-4),
  `schema/overrides.json` GAME_CMSG 79's head re-cut so one row no longer contradicts
  itself (EVID-D1C-5); `--outpost` over `--explorable` pinned (the reviewer's
  `visual_always` mutant survived without it); the `--no-item-moves` help text says what
  the flag does NOT revert (the lead rule, the store-built `0x006E`); three readability
  leftovers cleaned.

### Inventory, the owner's confirmation — the doll reads BAG slots, retail's bag order from every tape, and `c2s 0x0072` (DESKWORK-D1 step 8, the confirmation pass, 2026-09-23)

**The owner's client session (loopback, the sandbox rig; gamesrv capture
`authsrv-20260923T163355-c1`) confirmed** the drag out of the paper doll, the stored-cell
restore, the equip into an empty slot and the occupied-slot swap on our own client — the
"Inventory" runsheet's steps 1, 2 and 4 — **and found two defects.** Identifiers below:
`EVID-D1D-<n>`, this pass's evidence rows, the same series as the fix pass's `EVID-D1C`.

**Defect 1 — the paper doll's rows (EVID-D1D-1, OBSERVED, the owner's screenshot).** Retail's
armour column reads head, chest, arms, legs, feet top to bottom; ours read **legs, chest,
head, feet, arms**. The mechanism is two numberings the "Inventory" section already named
and then mis-assigned: the doll draws each **equipped-BAG slot** at a fixed row — head 4,
chest 2, arms 6, legs 3, feet 5, retail's ldufr-order bag — and this server dressed the
bag with the **VISUAL** numbering (body 2, boots 3, legs 4, gloves 5, head 6:
`STARTER_ARMOUR`'s third column, `wearmap.SLOT_*`). So the row that draws bag slot 4 showed
our legs, the row for 6 our head, the row for 3 our boots and the row for 5 our gloves —
exactly the observed order. That section's "a bag cell is opaque to the client" is
REFUTED: the bag cell is what the doll reads; only the BODY reads `0x006E`.

**Retail's bag order, re-derived from every tape (EVID-D1D-2, OBSERVED, n = 96
connections).** `test_itemmoves.py` §1c decodes every live game connection
(`livewire.decode_conn`): the type-2 bag from `0x013F`, each item's wire type from its own
`0x0161`, every `0x013E`/`0x014B` into that bag. Wire type 7 (body) sits at slot **2** ×110,
19 (legs) at **3** ×110, 16 (head) at **4** ×112, 4 (boots) at **5** ×111, 13 (gloves) at
**6** ×111 — one slot per type, on all 96 connections, zero exceptions; shields (24) at 1
×51, every weapon type at 0. The `0x006E` after each load, joined by item id, reads bag
0→0 ×40, 1→1 ×23, 2→2, 3→4, 4→6, 5→3, 6→5 ×98 each — the whole permutation the fix pass
had OBSERVED once on `:53310` (EVID-D1C-6) now stands on the corpus, and it is
`itemstore.RETAIL_VISUAL_OF_BAG_SLOT` / `RETAIL_BAG_SLOT_OF_TYPE` unchanged.

**The fix.** The dress puts the armour into the equipped bag at **retail's** cells
(`item_layout_defaults` → `equipped_bag_slot(type, visual)`, `itemstore.bag_slot_table`),
and every reader of an equipped cell goes through the pair `item_bag_slot_table()` /
`item_visual_of()`: the `0x006E` build (`worn_array` through the permutation — the array
is **byte-identical** to before, pinned), `plan_move`'s and `plan_equip`'s `0x006F`,
`plan_equip`'s slot per type, the refusal checks, the hands mirror (slots 0/1 are the
identity in both orders). `STARTER_ARMOUR`'s third column stays the visual slot (the
import-time `wearmap.check_content_row`, `test_armour`, `test_daggers` and `compositetrap`
read it as one). **`--equipped-visual-order`** is the revert arm and reproduces the
defect; the KNOWN-BAD arms in `test_itemmoves` show the visual table missing the measured
slot on four of five pieces and the identity mapping putting the head at visual 4.

**A stale persisted cell (EVID-D1D-3).** No store on this machine carries an
`item_locations` row (grep over `vault/state/`, 2026-09-23: zero files), so nothing is
migrated. The rule for one that did: an armour piece's or costume's equipped cell is
decided by its TYPE and can only ever equal the default, so `itemstore.restore` REFUSES any
stored equipped cell that is not the default (a hand cell is the existing keep-hands
rule), notes it as "written under the pre-2026-09-23 visual numbering or a foreign
store", and `item_layout_begin` DROPS it from the store (`charstore.drop_item_location`)
with a log line — never reinterpreted; under the revert arm the same rule holds against
that arm's defaults (the test's control). **The log label** `ITEM_MOVED_TO_LOCATION(...
-> equipped 6) [stored cell: bag 2 slot 2]` printed the constant beside other bytes; all
six placement sites now print the SENT cell (`dress_cell_label`: `-> bag 2 slot 2
[stored cell]`, `-> equipped 4`).

**Defect 2 — a drag between two backpack cells is unanswered (EVID-D1D-4, OBSERVED, our
client, n = 1).** The sword (item 11) from backpack cell 0 to cell 4 sent `c2s 0x0072`
`[11, 2, 4]` (frame `72800b000000020004`, t = 18.418, 20:34:13Z), UNHANDLED, and the client
put it back. On **no** retail tape (0 of 96 live connections, `retail_c2s.json`, 13,320
c2s) and 1 of 1,581 loopback logs.

**Read statically, 38797 and 38888 (EVID-D1D-5).** `msgshape` SEND table `0x00bcac48`
`[u32, u16, u8]`, 9 bytes = messages.json `GAME_CMSG_0114`, and the codec consumes the
owner's frame to the byte. Send wrapper `0x0084C400` (site `0x0084C435`, a 16-byte buffer;
38888 `0x0084C950`), ONE caller `0x008478DA` in ItCliApi **`0x00847860`**`(itemId,
bagIndex, slot)` (38888 `0x00847DB0`, the same body at +0x550): asserts `inventory`
(ItCliApi:1505); a bagIndex of −1 asks `0x0084A7A0` and 21 = none returns; item =
itemTable[itemId] (ctx+0xB8, bound ctx+0xC0); if item→bag (+0xC) IS the target bag and
item→slot (+0x50) IS the slot it **returns without sending**; else pushes `[itemId,
bag->id (+8), slot]`. Its ONE caller is `0x00526AE0` — inside **GmItemHelpers
`0x00526900`, the `0x004F` drag helper**, at the non-equipped path `0x00526AC3` that the
"Inventory" section (and `itemstore.py`, `authsrv.py`, overrides row 79) said "sends
nothing". **REFUTED (EVID-D1D-6)**, read to the call rather than the branch: a bag item →
`0x00847AF0` → **`c2s 0x007D` `[item, bag, slot]`** (msgshape SEND `[u32, u16, u8]`, 9 B;
wrapper `0x0084C690`, callers `0x00847B96` / `0x00847BAA` inside that function), a WHOLE
item (quantity == `0x00845120`'s total) → `0x00847860` → `0x0072`, a partial quantity →
`0x008477C0` → **`c2s 0x0075` `[item, quantity, bag, slot]`** (`[u32, u32, u16, u8]`, 13 B;
wrapper `0x0084C4D0`, its one caller `0x00847846`) — the two siblings named by the fix pass
from `sendsites --all` + `msgshape` on 38797 (EVR-6), both on NO retail tape and NOT armed.
**Nothing on the HELPER → SENDER path checks the destination's occupancy.** Whether the
inventory UI routes a drop onto an OCCUPIED or STACKABLE target through this helper at all
is **UNVERIFIED** (the fix pass, EVR-4; this paragraph first said "a drop onto a filled
cell reaches the wire" as a read fact): `0x00526900`'s three callers — `0x004E88E2`,
`0x004EA2E4`, `0x004EA7A2` (`codescan --xrefs`) — are unread, and two of them query the
drop target first (`0x00633C10`). The runsheet's step 3 settles it on the client. `0x004F`
names the item by its equipped SLOT; `0x0072` names it by ID; both are one helper's.

**Named and armed (RECONSTRUCTION).** `schema/overrides.json` GAME_CMSG 114
**`ITEM_MOVE_BY_ID`**, medium (the mechanism OBSERVED once on our client, the fields from
the sender; retail's reply NOT FOUND). `handle_item_move_by_id` → `itemstore.plan_move_by_id`,
labelled at every send: an EMPTY cell of a declared bag → `0x014B [key, item, bag, slot]`
(retail's reply to every `0x004F` move into a backpack cell, 4 of 4; the add worker wants
the cell empty, ItCliInv:105, and it is — the item store being the ONLY map of the bags,
the merchant's purchases included since the fix pass, ENG-2); an OCCUPIED cell → `0x0152
[key, occupant, item]` (retail's reply to every occupied-slot equip, 4 of 4; the swap
handler exchanges any two bagged items — weapons §29: ItCliInv:687/688 hold, :105 holds
after both removes); an equipped SOURCE → `0x004F`'s own batch; the equipped bag as
DESTINATION → the equip's batch only at the item's type's slot, else refused (a piece in
another piece's cell is defect 1); the delegated batches carry the ITEM_MOVE_BY_ID
RECONSTRUCTION tag too. Refused, nothing sent: an unknown item, an undeclared bag, a slot
past the bag, a STORAGE bag (types 4/5 — no tape carries a move into one: every `0x014B`
on 96 live connections lands in a type-1 or type-2 bag and every `0x0152` is between
those two; and the client's swap strips a set item landing in a type-4 bag from its equip
sets, ItCliInv:348/375, which the set machinery does not model — the fix pass, ENG-7), the
item's own cell (the client never sends it — its arrival means the store and the client
disagree), an EMPTY RESERVED cell (a worn OFF HAND's return cell — leads come back by
`0x0152` or to a free cell, so their homes are not reserved; an occupied reserved cell is
a swap — ENG-6). The cells persist under `--persist` (a bought item's does not: the dress
never re-declares a purchase), the set machinery's home slot follows
(`WEAPON_SET_BACKPACK_SLOTS`), `--no-item-move-by-id` is the revert arm; `test_c2striage`
§4 requires it named, armed and on NO live tape, so the day a retail tape carries one the
check reddens and names the witness.

**Runsheet — the owner's clicks (one loopback session, the sandbox rig, `--weapon-set
1=starter_sword`, `--persist`), the predictions stated first.**

1. **Open the inventory (I) and look at the paper doll.** PREDICTION: top to bottom
   **head = `warrior_head` (item 7, bag 4), chest = `warrior_body` (3, bag 2), arms =
   `warrior_gloves` (6, bag 6), legs = `warrior_legs` (5, bag 3), feet = `warrior_boots`
   (4, bag 5)** — retail's order; the body on screen unchanged (the `0x006E` bytes are).
   The log's `ITEM_MOVED_TO_LOCATION(warrior_head -> equipped 4)` line is the server's
   half. The OLD order (legs, chest, head, feet, arms) → `--equipped-visual-order` was
   passed, or the fix did not land. ANY OTHER order → the doll's row-to-slot map is not
   what the screenshot implied: write the order down; it refutes EVID-D1D-1's mechanism,
   not the tape's bag order.
2. **Drag the sword (item 11) from backpack cell 0 to another EMPTY backpack cell.**
   **A** = the sword stays in the new cell and the log reads `ITEM_MOVE_BY_ID(item 11 ->
   bag 2 slot N) [RECONSTRUCTION]: 1 message(s), item 11 -> bag 2 slot N`. **B** = it
   snaps back: an `ITEM_MOVE_BY_ID ignored (--no-item-move-by-id)` line means the revert
   flag is on; an `UNHANDLED 0x0072` line means the RUNNING SERVER does not carry this
   branch at all (a stale sandbox stack — the failure CONFIRM-2026-09-23 §3 records; check
   the ports and the build); a `refused:` line names why (a storage bag, a reserved cell,
   the item's own cell). Then drag it back (A again, slot 0). A client assert on `0x014B`
   (ItCliApi:2126, ItCliInv:105) refutes the empty-cell arm.
3. **Drag the sword ONTO an occupied backpack cell** (with `--weapon-set
   1=starter_sword+starter_shield`, the shield's cell). A = the two exchange places and the
   log shows one `0x0152`. A client assert on `0x0152` (ItCliApi:2253/2254/2257,
   ItCliInv:687/688) refutes the swap arm; then relaunch with `--no-item-move-by-id`,
   which switches off the WHOLE `0x0072` arm (there is no swap-only switch — the empty-cell
   move goes dark with it), and record the swap as refuted. If the client sends NOTHING for
   the drop onto the shield (the sword snaps back with no `0x0072` in the log), the UI
   never routes an occupied drop through the helper — EVID-D1D-5's UNVERIFIED clause
   answered the other way; record that too.
4. **Zone and come back.** The sword where it was left (`ITEMS: item 11 (set 1 lead,
   starter_sword) dressed at bag 2 slot N -- the character's stored cell`). F2 then puts
   the sword in hand and the HAMMER in cell N (the leads exchange cells by `0x0152`), and
   F1 returns the sword to cell N (the home slot followed).

**The fix pass on this section (2026-09-23, two reviews — an evidence refuter and an
engineering reviewer; their tokens `EVR-n` / `ENG-n` are quoted as written).** The
evidence held: both re-derived the bag order and the visual permutation from all 96
connections and reproduced the owner's doll with no free parameter (rows by `0x006E`
position, by type and by `0x013E` arrival order each predict a correct doll and are
refuted); the `0x0072` chain, the 1505 assert, the early return and the `[u32, u16, u8]`
widths held on both builds; the capture is `authsrv-20260923T163355-c1` (the task's
`163319` is the sandbox RUN id, not a file). What moved, all on `test_itemmoves`
(floor 137 → 158 bare, 183 vaulted) and `test_purchase` (27 → 35): **(ENG-1 / EVR-1)**
the dress cell was keyed by wire TYPE, and `wearmap.WORN_TYPES` lets a legs-class piece
(19) be worn at the boots or gloves location, so such a row put two pieces in bag 3 — two
`0x013E` into one cell, ItCliInv:105 on the second, and the revert arm could not
reproduce the old layout for it; `equipped_bag_slot(visual_slot)` is now keyed by the
worn LOCATION through the inverse permutation (a bijection; it agrees with the type table
for every piece in its own location), and an in-game re-equip of an off-location piece
still goes by TYPE (the client's equip path reads the type) — said, open. **(ENG-2 /
EVR-2)** the merchant kept its own backpack map, never registering a purchase in the
item store, so a purchase could land on the dressed sword and a drag onto a bought item's
cell planned a bare `0x014B` into a FILLED cell (reachable under a merchant probe only;
the same gap already existed for `0x004F`); purchases are now placed in the store
(`itemstore.place` handed in by the wrapper, so `merchant.py` still imports nothing),
chosen clear of the store and the reserved cells, popped by the sale, re-keyed on a move
and never persisted. **(ENG-3)** the `0x0072` handler's `visual_of` had no known-bad arm
(the mutation survived); it is locked and the real handler is driven through both
delegates (visual 6 for the head). **(ENG-5 / EVR-8)** the planners' defaults were the
revert pair; they are retail's now, the identity asked for by name; the `0x006E` comment
that called the wire a refutation of ldufr's order — the misreading behind defect 1 — is
scoped to the visual array. **(ENG-6)** every set item's home was reserved, but only an
OFF HAND returns by `0x014B` (leads exchange by `0x0152` or leave to a free cell), so a
drag onto the hammer sitting in the sword's home after F2 was refused with a false
reason; off hands only, occupancy before reservation. **(ENG-7)** storage bags refused as
destinations (above), and the delegated batches tagged. **(ENG-8)** `test_c2striage`'s
catalogue entry and §1c's all-connections requirement. **(EVR-3 / ENG-4, EVR-7)** the
runsheet's steps 2–4 above, corrected in place (an instruction, not a record). **(EVR-4,
EVR-6)** EVID-D1D-6 above, corrected in place the same day it was written. **Declined:
EVR-5** (merge `main` first — this branch does not merge itself; the orchestrator's merge
will meet main's `1ce515a1` in PLAN.md 8.1's D1 bullet and PLAN-LOG's top, and main's
closures of the kick/add clicks must win there; this section should then link
[../deskwork/CONFIRM-2026-09-23.md](../deskwork/CONFIRM-2026-09-23.md), which is on main
only).

### The display mode — `s2c 0x00EF` CHAR_VISIBILITY_FLAGS, `c2s 0x0057` SET_CHAR_VISIBILITY_FLAGS, and the InvVisibilityStatus drop-down (DESKWORK-D1, the owner's answer, 2026-09-23)

**The question** ([../deskwork/CONFIRM-2026-09-23.md](../deskwork/CONFIRM-2026-09-23.md) §5,
the owner's answer): the inventory panel carries, beside the cape (top-left), the headgear
(top-right) and the two costume slots (lower-left), a per-slot DISPLAY MODE drop-down —
Always Show (an eye), Hide in Towns and Outposts, Hide in Combat Areas, Always Hide (a
circled bar) — and on retail it governs both the paper doll's figure and the world model.
Retail's screenshot shows the eye on all four; ours (`20260923T185124`, frame `w001-step4`)
shows the circled bar on all four, the doll bare-headed in the outpost, the world body
still helmed. **Four slots, not three** — the top-left eye is the cape's. Identifiers:
`EVID-D1E-<n>`. Everything static is build 38797, the pinned pristine client, read with
`codescan.py`, `asserts.py`, `msgshape.py`, `sendsites.py`; every tape number is
`livewire.decode_conn` over every `origin=LIVE` game connection (96), reproducible by
`test_visstatus.py` §2.

**(a) The state and the s2c that carries it (EVID-D1E-1, OBSERVED on the wire; the binary
read).** The drop-down (`InvVisibilityStatus.cpp`; the widget class is 0x008EC760/0x008EC790
with statics 0x1088770/74/78, the image lists asserted at lines 328/339/350) reads ONE dword
through the getter 0x00815EF0 — `ctx->[0x2c]->[0x7c8]`, the character context. The per-bit
tester 0x00815EA0 asserts `vis < CHAR_STATS_VIS` (ChCliApi.cpp:5032) and the bound it
compares is 8: eight bits, ArenaNet's own enum name. The kind masks are the table at
0xBA38D4 — **0x03 cape, 0x0C headgear, 0x30 costume body, 0xC0 costume head** — and the
byte's ONLY writer image-wide is 0x00814BE0(value, mask): `flags = (flags & ~mask) |
value`, then frame 0x1000006C `{mask, flags}` to the bus (`codescan --field 0x7C8` over the
whole image: that writer, the tester, the getter and three context resets are every hit;
the +0x7C8 hits at 0x006Exxxx are another struct). The writer's one caller is the RECV stub
0x0091F7F0, which pushes `[msg+4], [msg+8]` — **GAME_SMSG 0x00EF `[u32 value, u32 mask]`**,
10 B (msgshape RECV table 0x00BC8F68, identical to `messages.json` GAME_SMSG_0239). On the
tapes: **exactly one per connection on 95 of 96 live connections, always `[0xFF, 0xFF]`,
immediately after `0x00E9` CHARACTER_UPDATE_FACTIONS on 95 of 95 and before `0x003C`** (the
one without it is `20260807T133758 :54560`). So retail's default for the owner's characters
is every slot Always Show — which is the retail screenshot — and our server never sent the
message at all: the client read an unsent zero. The bit meanings, from the drop-down's own
tables (0xBA3854/74/94/B4, read by 0x008ECD00; the lookup 0x008ECD90 takes the first row
whose `bits & mask == flags & mask`): both bits set = Always Show, the LOW bit alone =
Hide in Towns and Outposts, the HIGH bit alone = Hide in Combat Areas, neither = Always
Hide; the code→icon map (0x008EC7F5) draws the eye for Always Show and the circled bar for
Always Hide, which is why the zero read as Always Hide on every slot. **Kind 1 is the
headgear from a second direction**: the tester's one caller is UiGame's roster-blob packer
(0x004A8C59), and `CHAR_STATS_VIS(3)` — the headgear's HIGH bit — is the roster blob's
"helm_shown" bit 14 that three server lineages named ([../character/FINDINGS.md](../character/FINDINGS.md),
[../heroes/RUN-HEROLIB.md](../heroes/RUN-HEROLIB.md) §22.5's open "helm toggle" question, now
answered: it is another message, `0x0057`/`0x00EF`, not the settings write).

**(b) The c2s the drop-down sends, and what retail answers (EVID-D1E-2, the sender READ;
the reply RECONSTRUCTION).** The widget's "selected" arm (0x008ECF30, `msg 8`) recomputes
the current code from the getter, finds the chosen code's row, and calls
0x00816C10(`bits & mask`, `mask`) — a `jmp` thunk to the send wrapper 0x00920FE0, which
`sendsites.py` lists as **GAME_CMSG 0x0057, 12-byte buffer, CharMsg**; msgshape's SEND table
0x00BC8CB8 gives `[u32, u32]`, 10 B, identical to GAME_CMSG_0087. The thunk has exactly one
direct caller (the widget), which is also the answer to a question the c2s triage's
"callers 0" column raised: the CharMsg wrappers are reached through the 0x8161xx thunk band
(`0x0030`'s at 0x008161D0), so a wrapper's caller count is the thunk's, not the sender's.
**`0x0057` is on no tape** — 0 of 13,320 c2s over 96 live connections — so retail's reply is
not witnessed. What the binary settles about it: the client applies nothing locally (the
sender's arm writes no state; the byte's only writer is `0x00EF`'s handler), so a server
that answered nothing would leave the icon unchanged; the answer that reaches the writer
is `0x00EF`, and `[value, mask]` through `(flags & ~mask) | value` is exactly the request's
own arithmetic. Our server answers that (RECONSTRUCTION) — one client run settles whether
retail's echo is `[value, mask]` or `[flags, 0xFF]`; both land identically in the writer.

**(c) How the WORLD model applies the mode (EVID-D1E-3: the negative OBSERVED statically,
the mechanism RECONSTRUCTION; the tapes CONSISTENT but not discriminating — corrected by
the fix pass, below).** The readers of the byte, counted at the GETTER 0x00815EF0 rather
than at `--field`'s direct hits (the fix pass, ENG-VIS-3/EVR-VIS-4 — the landing said "two
readers", which was the `--field` scan's view): **eight direct callers** (`codescan
--xrefs`). Three are the drop-down's (0x008EC6E3 the icon, 0x008ECEA8 the menu, 0x008ECF5B
the "selected" arm). One is **GmAgentDoll** (0x005384E1 in 0x005384B0) — the paper doll's
figure — which subscribes to frame 0x1000006C (0x0053761C) and picks the regime with
`MissionCliGetMap()` (0x0084D9B0, OBSERVED 0 = OUTPOST, 1 = GAME,
[../minimap/FINDINGS.md](../minimap/FINDINGS.md)): **in a town it tests the HIGH bit of
each pair (0x2/0x8/0x20/0x80), in a field the LOW bit (0x1/0x4/0x10/0x40)**, and a clear bit
hides that kind on the figure (the costumes are also hidden in a field whose map flags carry
0x40000 without 0x40000000 — a PvP rule this server never meets). Three more are UI
(0x005046F8; 0x00508C91, which gates bag slots 7/8 on the town bits 0x20/0x80; 0x0050CDFE,
the same on the field bits 0x10/0x40). The eighth, 0x0081DE5E, is the ONE outside UI: in
0x0081DDD0, a `ChCliObserver.cpp` record builder (the asserts inside it; past ChCliApi's
assert range), called from 0x0080E3F5/0x0080E485, which copies the player's equipped bag
slots 2..6 into a record and overrides with bag 7 under 0x10 (0x0081DED4) and bag 8 under
0x40 (0x0081DEBD) — the costume FIELD bits, no regime test, into a record and not onto a
body. The bit tester 0x00815EA0 has one caller (the roster packer, (a)); the writer has one
(`0x00EF`'s stub); and the frame id 0x1000006C occurs at exactly **six** `.text` sites and
in no data section (the writer 0x00814C17, the doll's subscribe 0x0053761D, four in the
widget) — a raw scan of the image, not a decoder's view. So the doll follows the mode
client-side, and **the world body does not read the byte at all**: none of the eight
getter callers, the tester's caller or the six frame sites is on the agent-view or
composite path, and the AvApi dresser 0x007DFCE0 has three direct callers, all ChCliApi
message workers (the `0x006E` bulk write and the `0x006F` slot write among them). The world
body therefore wears exactly what the server's visual array says, and the server must leave
the hidden piece out — RECONSTRUCTION from that negative.

**What the tapes say about it, corrected (the fix pass, EVR-VIS-1/ENG-VIS-2).** The landing
quoted "`0x006E`'s head slot 0 on 756 of 2,245 outpost bodies and 0 of 48 field bodies"
(and `0x0048`'s cape bit, 855 of 2,246 vs 0 of 48) as corroboration. **It is not**: joining
each `0x006E` to the connection's equipped bag (the body whose armour ids all sit in it is
the owner's own — `test_itemmoves` 1c's recipe), **every one of the 48 field bodies is the
owner's OWN body** under `0x00EF [0xFF, 0xFF]`, and **every one of the 756 bare outpost
heads is a STRANGER** whose mode and inventory the tape does not carry; the comparison was
strangers in towns against the owner in fields, and a tape with no strip at all gives the
same numbers. The own body carries its equipped helm on 50 of 50 outpost loads and 48 of 48
field loads under Always Show — consistent with the strip, not discriminating. What the
tapes DO show, OBSERVED, is retail tailoring the own `0x006E` per regime on the **weapon**:
**no outpost `0x006E` carries one (0 of 2,245 bodies, visuals 0 and 1 both zero — the
owner's own 50 among them, with a weapon in the equipped bag on all 50), while in a field
every body whose bag holds one carries it (40 of 40; the other 8 field loads have no bag
weapon and carry none)**. That is the precedent for a server-side, regime-keyed visual
array; the head strip itself is unwitnessed on any body whose mode is known (every owner
character on tape is Always Show: `0x00EF [0xFF, 0xFF]` on 95 of 95) and stays RECONSTRUCTION. (The
cape's world half is `0x0048` AGENT_SET_TABARD_VISIBLE — the [smsg
study](../smsg/FINDINGS.md)'s reading, a guild lookup gated per agent, is exactly a
server-resolved cape mode; this server has no guild and keeps sending 0.) **NOT FOUND**: how
retail re-dresses the LOCAL body after a mid-session mode change in an outpost — the item
study found no `0x006F` on outpost equips (0 of 5), so retail's outpost path for the body
is unwitnessed; the `0x006F` handler is regime-blind, so sending it is safe on our client.
**Open, out of this arc's scope** (the engineering review's side note): our TOWN `0x006E`
carries the weapon at visual 0, which retail's never does (0 of 2,245) — a pre-existing
divergence worth its own item. (Closed the same day: §"The town weapon" below.)

**Shipped** ([`toolkit/authsrv/visstatus.py`](../../toolkit/authsrv/visstatus.py) is the leaf;
`test_visstatus.py`, 63 bare / 73 vaulted after the fix pass): `0x00EF [flags, 0xFF]` at
load right after our `0x00E9` — retail's position RELATIVE TO `0x00E9` (95 of 95; retail's
whole load runs `0x00E9, 0x00EF, 0x006E, 0x018E` on 81 of 95 while our burst sends `0x018E`
earlier, a pre-existing order the client's context resets do not disturb — EVR-VIS-7) — the
byte loaded by `visstatus.load_flags` (the store's int under `--persist`, else 0xFF) and the
payload by `load_message`, both driven by the test; `c2s 0x0057` handled —
`(flags & ~mask) | value`, the echo `0x00EF [value, mask]`, then `0x006F [player, slot, item
or 0]` for each kind whose view under the CURRENT regime changed (head 6, costumes 7/8; the
cape has no slot), persisted per character (`charstore` `vis_flags`, validated 0..255);
refused with nothing sent: an empty mask, bits beyond the eight, a value outside its mask.
The body's `0x006E` is `visible_worn` over `player_worn_array` — the ONE copy of the dressed
array (ENG-VIS-6): a kind the mode hides in this regime (the `0x0199` byte's own rule,
`instance_is_field`) leaves the array. **The equip path is gated too (the fix pass's one
blocker, ENG-VIS-1/EVR-VIS-2)**: every item batch (`0x004F`, `0x0030`, `0x0072`) commits
through `_item_moves_commit`, which sends it through `visible_slot_writes` — a `0x006F` that
would put an item into the player's visual 6/7/8 while the mode hides that kind here goes
out as item 0 (the slot is already 0 on the body and the client's `0x006F` handler is
regime-blind). The landing sent it unfiltered, so in a field under Hide in Combat Areas an
unequip and re-equip of the helm re-helmed the world body while the doll and the load hid it.
**`--no-visibility-status` reverts** to today's behaviour (no `0x00EF`, `0x0057` ignored, the
full array, the equip's `0x006F` unfiltered). Schema: `0x00EF` CHAR_VISIBILITY_FLAGS (high),
`0x0057` SET_CHAR_VISIBILITY_FLAGS (medium — sender read, reply unwitnessed).

**Refuted on the way.** (1) The first proc found under the module's assert range,
0x008EBDD0 (`msg.code` switch at line 343, `s_backgroundImageList` at 407), is
`InvElementSlot.cpp`'s slot control (its file string at 0xBA3824), not the widget — its click
arm starts an item DRAG (a `GmCtlItemImage` of kind 0x2A), which read like a menu for ten
minutes; the widget is the class registered from 0x008ECE90/0x008ECF30 with the
`InvVisibilityStatus.cpp` file string at 0xBA38E4. (2) `sendsites.py`'s "callers 0" on the
CharMsg wrappers is not "unreachable": the wrappers are reached through `jmp` thunks in the
0x8161xx–0x816Cxx band. (3) The three-slot count in the task: the retail screenshot has four
eyes and ours four circled bars. (4) By the fix pass: the landing's `CODE_STRING_ID` had
codes 3/4/5 as 0x32E/0x32F/0x330 — the switch's case bodies taken in ADDRESS order; through
the jump table at 0x008ECE3C (and the menu builder's copy at 0x008ED080) code 3 is 0x330,
4 is 0x32E, 5 is 0x32F, so the headgear/costume menu reads 0x32C/0x32D/0x32E/0x330 and the
cape's own two strings are 0x32F/0x331 (EVR-VIS-3; the table is pinned against the address
order). (5) The landing's "two readers of the byte" was `--field`'s view; the getter has
eight callers, one of them outside UI ((c) above). (6) The landing's tape "corroboration"
was a population confound ((c) above).

**The fix pass (2026-09-23, the same day).** Two reviews — an evidence refuter that
re-derived (a)–(c) from the tapes and the pinned client before reading the landing, and an
engineering review that drove the handlers and mutated the tree in memory — found no
blocker in the wire evidence and one in the code: the equip path's `0x006F` ignored the mode
(fixed, above; the refuter's EVR-VIS-2, the engineer's ENG-VIS-1). Moved besides: the tape
"corroboration" relabelled in all five places and replaced by the weapon precedent (EVR-VIS-1/
ENG-VIS-2); the string table (EVR-VIS-3); the reader census (ENG-VIS-3/EVR-VIS-4); the load's
default and restore, which no test pinned — the engineer's mutation of the burst to a zero
default (the defect itself) ran green — now `load_flags`/`load_message` driven with a KNOWN-BAD
zero and the burst's calls locked (ENG-VIS-4/EVR-VIS-6); the two tautological §2 checks
dropped for a decode-ok count and one identification's two tallies (ENG-VIS-5/EVR-VIS-8);
one worn-array copy (ENG-VIS-6); the runsheet's field step given its `--persist`
precondition (EVR-VIS-5); the position wording (EVR-VIS-7); `test_provlint`'s comment
naming QuestLog:261's enum value (EVR-VIS-8). **Declined**: driving the whole
`_handle_request_players` burst under a fake send (EVR-VIS-6's first form — no test in the
tree drives it, and the burst needs a live connection's state; the helpers it calls are
driven instead, and its call sites are locked, which is what the mutations needed).

**Runsheet and PREDICTIONS (pre-registered).** *Default launch* (the orchestrator, no
owner): press `I` — beside the headgear, the cape and both costume slots the icon is the
**eye** (code 0/1 → icon 0), and the doll's figure **wears the helm** in the outpost; the
gamesrv log carries `CHAR_VISIBILITY_FLAGS(0xff: ...)` right after `CHARACTER_UPDATE_FACTIONS`.
Under `--no-visibility-status`: the circled bar on all four and a bare-headed doll (the
20260923T185124 frame, reproduced). *One owner step*: click the eye beside the headgear and
choose **Hide in Towns and Outposts** in the outpost — the icon becomes the second icon,
the doll's figure loses the helm (client-side, from `0x00EF [0x4, 0xC]`), and the world body
loses the helm too (from our `0x006F [1, 6, 0]`; the log line names both sends). A/B
against `--no-visibility-status`: the choice sends `0x0057 [4, 12]` (the log says
`SET_CHAR_VISIBILITY_FLAGS ignored`) and NOTHING changes — icon, doll and body all stay.
*The field step needs `--persist`* (EVR-VIS-5: without it every new game connection starts
at 0xFF, so a returned helm would mean the reset, not the regime rule): with the mode kept
in the store, `--explorable` (or a zone) — press `I` first: the icon beside the headgear is
STILL the second icon (the byte survived), and the helm is back on doll and body (the low
bit is set); then `Hide in Combat Areas` there hides both; drag the helm to the backpack and
double-click it back: the body stays bare (the fix pass's filter; under
`--no-visibility-status` it re-helms). Relaunch under `--persist`: the mode is remembered
(`vis_flags` in the store), the icon shows it at `I`. What a run cannot settle alone:
retail's exact echo bytes (b); the cape's third and fourth menu TEXTS (string ids 0x32F/0x331,
unread — their icons 2 and 3 are read from the widget's table).

### The town weapon — the outpost body's empty hands, `select_weapon_set` through the one gate, `--no-town-weapon-strip` (DESKWORK-D1, 2026-09-23)

**The question** (the display-mode fix pass's side note in (c) above; `PLAN.md` §8.1's D1
bullet): our TOWN `0x006E` carried the weapon at visual 0 where retail's never does. The
premise was re-derived from the tapes before anything was built — with a finer join than the
fix pass's — and then closed. Identifiers: `EVID-D1W-<n>` (this document's `EVID` word, a
third series; each token is one census fact). Every number below is `livewire.decode_conn`
over every `origin=LIVE` game connection (96, all decoding closed), the regime read from the
`0x0199` INSTANCE_LOAD_INFO byte (47 outpost connections, 44 field, 5 with no `0x0199` and no
`0x006E` — character-select traffic), reproduced by
[`test_townweapon.py`](../../toolkit/authsrv/test_townweapon.py) §2 as floors.

**(a) The load (EVID-D1W-1, OBSERVED).** `0x006E [agent, lead, off, five armour, two costumes]`:
every OUTPOST body is empty-handed on BOTH visuals — **0 of 2,245** carry a lead or an off
hand. That count is 2,195 strangers and the owner's OWN body on 50 loads, and the own body is
the one whose inventory the tape carries: it is the `0x006E` whose armour ids all sit in ONE
type-2 (equipped) bag of the connection — **not** "any type-2 bag", because a hero's equipped
bag is type 2 too, four connections carry more than one, and the first pass of this census
counted a hero's shield as the player's (refutation (1) below). That bag holds a lead on all
50 outpost loads (28 lead only, 22 lead + off hand) and the body shows neither. In a FIELD the
same join gives 48 own loads: 8 with no bag weapon carry none, 17 with a lead alone carry
visual 0 and leave 1 empty, 23 with lead + off hand carry both — **40 of 40 leads, 23 of 23
off hands**, and never a hand the bag lacks. So the own array reflects the bag in a field and
is empty-handed in a town, under one inventory, on the same character. (The fix pass's "0 of
2,245 / 40 of 40" counted visual 0 only and any type-2 bag; both numbers survive the finer
join, and the off hand is now counted too.)

**(b) The changes (EVID-D1W-2, OBSERVED).** `0x006F [agent, slot, item]` never writes a hand
in an outpost — on ANY agent, 0 writes to slot 0 or 1 across the 47 outpost connections —
while the own field body's hands are written 11 times. Fourteen outpost hand changes are on
tape, and none is answered with a hand `0x006F`: the **four weapon-set switches** (c2s
`0x0032` on `20260919T103604 :58638` at t=150.257 / 159.967 / 172.746 / 224.632 — `0x0148`
then the `0x014B` / `0x0152` rows only, e.g. `[0x0148 [241, 1], 0x014B [241, 17730, 136, 1],
0x014B [241, 23247, 136, 2]]`); the **four double-click equips** of a weapon onto the occupied
lead hand (c2s `0x0030` on `20260819T132414 :53419` — a type-27 sword and a type-32 weapon,
`0x0152 [159, occupant, item]` alone, twice for the double press); the **off hand dragged
out** (c2s `0x004F [1, 136, 6]` on `:58638` — `0x014B [241, 17730, 136, 6]` alone); and the
**PvP equipment panel's five creations** straight into equipped slot 0 or 1 (c2s `0x0086` on
`:58638` — axe 23247, scythe 12689, spear 13633 and spear 23652 to `(231, 0)`, shield 13467
to `(231, 1)`, each a `0x0161` + `0x013E` + `0x015D` + `0x005D` + `0x005E` + `0x013A` burst
with no `0x006F`). In a FIELD the four switches of the same capture's `:56576` (agent 25,
RUN-WEAPONS-1A) each carry the hands: `0x006F [25, 0, 209]`, `[25, 0, 210]`, `[25, 0, 208] +
[25, 1, 207]`, `[25, 1, 0] + [25, 0, 212]` — the W9 batches `test_weapons` §18 replays.

**(c) The rule is the SLOT, not the regime (EVID-D1W-3, OBSERVED: one own-body armour write
and 31 strangers' against fourteen hand changes with none).** The same
PvP panel in an outpost created a HEAD piece — c2s `0x0086 [46, 274, [], 9, 4, 0]` on
`20260917T160915 :58557` at t=73.505; the reply creates item 23284 (type 16) into equipped
`(843, 4)` and carries **`0x006F [336, 6, 23284]`** — the one own-body `0x006F` on any outpost
connection. The STRANGERS corroborate it: across the 47 outpost connections retail wrote 31
`0x006F` onto other agents' ARMOUR slots — slot 2 ×6, 3 ×4, 4 ×7, 5 ×4 (and one emptying it),
6 ×5 (and two emptying it), 7 ×2 — and 0 onto a hand (the fix pass's census, the review's
WEAP-R2; the own field body's 11 hand writes are the only hand `0x006F` on tape). Armour
visuals are written in a town; the hands are not. This refines
`itemstore.py`'s VISUALS paragraph ("0x006F rode … none in an OUTPOST, 0 of 5"): all five it
counted were hand changes, and the confound it left open (the outpost or the swap?) resolves
to neither — it is the slot. The display-mode pass's own filter is unaffected (it works on
slots 6/7/8, which a town does write), and its "no `0x006F` on outpost equips" negative stays
true for the hands.

**(d) Heroes and NPCs (EVID-D1W-4, OBSERVED; nothing changed).** No hero body exists in an
outpost on retail: 3 party heroes (`0x01C2`'s agent ids) over the outpost connections, none
created (`0x0020` / `0x0021`), none with a `0x006D`; the field's one hero has both. Ours
withholds hero bodies in a town already (`PARTY_BODY_IN_OUTPOST`, SLICE-H2b), so there is no
hero hand to strip and nothing was built. Retail's outpost NPCs DO carry weapons — `0x006D`
lead non-zero on 466 of 1,653 outpost `0x006D` MESSAGES (206 lead only, 260 both hands; 23
off hand only), which is 403 of 1,510 distinct (connection, agent) bodies, against 2,994 of
3,502 messages (1,777 of 2,082 bodies) in fields — so the empty hands are the PLAYER body's
rule, not a town's; NPC hands are reported and untouched. (This section's first record
counted messages and called them bodies — the review's WEAP-R3.)

**(e) Why the server does it (RECONSTRUCTION from a measured negative).** The client's
`0x006E` / `0x006F` handlers (0x0091E1C0 / 0x0091E1E0) reach the AvApi dresser (0x007DFCE0)
through ChCliApi message workers (0x00810E30–0x008110B0 / 0x008110F0–0x008112E8). This
section's first record cited "(c) of The display mode" for "no regime test on the path" — but
that census was of the display FLAGS' readers and never looked for a regime read (the review's
WEAP-R1). The fix pass measured it: `msghandler.py 0x006E --follow --depth 2` and the same for
`0x006F` disassemble the handler, the worker and every function the worker calls directly —
fifteen functions, the dresser's own fifteen-instruction body among them (a lookup 0x00802160,
the assert stub, then `call 0x007F70B0`) — and none holds a direct call to `MissionCliGetMap`
(0x0084D9B0) or the map-flags reader (0x0084D950); of `MissionCliGetMap`'s 37 direct callers
(`codescan --xrefs`), none lies in those functions. NOT searched: 0x007F70B0 and deeper, and
indirect calls — a bounded negative, not a proof. Our own town `0x006E` did carry the hand (the
run `20260923T210546`'s c1 wire, seq 100: `[1, 1, 0, 3, 4, 5, 6, 7, 0, 0]` under a map-148
outpost load) and the body stood armed. The shape is OBSERVED; that the SERVER strips (rather
than the client ignoring a hand in a town) is what the run below settles on our client — if the
body is empty-handed only under the strip, the array is the channel. **REFUTED on the client
2026-09-24 and CORRECTED in (f) below: the array is ONE of three carriers into a single
client-side hand store, and our own load's player `0x006D` — a message retail never sends the
own body — was re-arming what the array had emptied.**

**Refuted or refined on the way.** (1) The first census pass reported one field own body with
an off hand in the bag and visual 1 empty (`20260914T005758 :56011`, t=87.209): the "bag off
hand" 779 sat in a HERO's type-2 bag beside the player's bow — a join artifact, fixed by
identifying the own bag as the one holding the body's armour. (2) `itemstore.py`'s "0 of 5"
is true and incomplete: a sixth outpost own-body `0x006F` exists and is the head's ((c)). (3)
`test_weapons` §18 replayed the FIELD connection's W9 batches from states with no `map_id` —
an implicit town under `map_explorable(None)` — so with the strip on, the section reddened on
a regime it never declared; it now sets `EXPLORABLE`. (4) The transition question ("entering
a field from an outpost; returning") needs nothing built: every load builds a fresh array
from the bag (`player_worn_array`) and the strip is per load, so the field load carries the
hands and the return to the outpost leaves them out; the 50 own outpost loads above include
such returns.

**Open (the fix pass, the review's WEAP-R2; reported, not built).** The town ARMOUR equip.
`plan_equip` / `plan_move` append a `0x006F` only when `visuals` is True — a field — so a helm
equipped in a town rides `0x014B` alone; retail, per (c), writes armour visuals in outposts
(31 strangers' writes, the own PvP head). No own armour equip in an outpost is on tape, so
whether retail answers a town `0x0030` of a helm with `0x006F [agent, 6, item]` is
RECONSTRUCTION from the PvP head's precedent — probably one message short of retail, and the
display mode's hiding-mode equip in a town ((c) of that section, its open (b)) is the same
question. `PLAN.md` §8.1's D1 bullet carries it.
**SHIPPED (the CLEANUP-3 lane, 2026-09-24; `townweapon.visual_planned`,
`authsrv.item_visuals_planned`, `--no-town-armour-visuals`).** Established first on the real
handlers (the lane's scratch, tree `054b2c15`): a TOWN `0x0030` of the head rode `0x014B [1, 7, 1,
4]` alone and a `0x004F` out `0x014B [1, 7, 2, 9]` alone, the `0x0072` drag likewise, while the
FIELD carried `0x006F [1, 6, 7]` / `[1, 6, 0]` — the planners were handed
`visuals=instance_is_field(state)`, so a town armour change never reached the world body (the
doll changed, the body kept the old piece). The fix plans the visuals PER SLOT (`visual_planned`,
handed to `itemstore` as a callable: a field every slot; a town an armour or costume slot by
default and NEVER a hand — the lane first planned the town's hands too and left them to the gate's
strip, and under `--no-town-weapon-strip` a town hammer equip then sent `0x006F [player, 0, item]`,
which no run ever did: the review's RV-2, re-cut so the strip governs the weapon-set switch alone,
as its contract says) and leaves the one gate as it was: `visstatus` still zeroes a hidden kind,
and `_item_moves_commit` now counts what the gate returned (RV-3), so a town head equip now sends `0x014B` + `0x006F
[player, 6, 7]`, the hammer beside it still `0x014B` alone, and under Hide in Towns the head's
visual goes out ZEROED `[player, 6, 0]`. The town armour write is labelled RECONSTRUCTION at the
send and logged (`TOWN ARMOUR: …`, naming the item as SENT — `item 7 hidden by the display mode,
sent 0` under a hiding mode, the review's RV-4 — and in every flag combination, the gate's
both-flags-off shortcut now applying to a field only, RV-5): retail writes outpost armour visuals
(the own PvP head `[336, 6, 23284]`, 31 strangers'), but no own outpost `0x0030` of an armour
piece is on any tape.
`--no-town-armour-visuals` is the pre-lane arm (`0x014B` alone, KNOWN-BAD). Tests:
`test_townweapon.py` §1 / §3 (floor 55 → 66 → 72 → 73 bare, 88 vaulted: 66/81 at the lane's commit,
72/87 after the review's six, 73/88 with the review's second round — the figure here said 66/81
until RV2-1), `test_itemmoves.py` §4's town check re-cut with the KNOWN-BAD arm beside it (floor
159 → 160), `test_visstatus.py` 63 → 64 bare / 74 vaulted (RV-1); each new check inverted in a
scratch copy and red. The display mode's hiding-mode equip in a town is now pinned (zeroed, not
dropped) in `test_townweapon.py`'s BOTH RULES check and in `test_visstatus.py`'s town equip — the
latter pinned the pre-lane `0x014B` alone and was RED at the lane's commit until the review re-cut
it (RV-1). RV-3's commit count has a discriminator since the second round (RV2-3): since RV-2 no
handler batch holds a write the gate drops, so the two handler counts were the same whether the log
counted the planned batch or the gate's (the bug planted in a scratch copy left the whole test
green, 72 checks); a direct `_item_moves_commit` of a batch holding a town hand `0x006F` (strip ON)
now pins "1 message(s)" where the planned count says 2, and that check alone reddens under the
plant.
**Owed: one client run** — a town helm change with the body watched (the PLAN-LOG entry's
runsheet).

**Shipped** ([`toolkit/authsrv/townweapon.py`](../../toolkit/authsrv/townweapon.py) is the
leaf — `strip_hands`, `drops`, `filter_hand_writes`, stdlib, no repo import;
`test_townweapon.py` 35 bare / 46 vaulted, TESTS.md). The load: `visible_worn` — the display
mode's gate over `player_worn_array`, the ONE dressed copy — zeroes visuals 0 and 1 in a town
after the mode's strip, and logs `TOWN WEAPON: the body's 0x006E leaves out the lead hand
(item N, visual 0) …`. The changes: `visible_slot_writes` — the gate every item batch commits
through — DROPS (not zeroes: retail sends nothing) a player `0x006F` into visual 0 or 1 in a
town, under either display-mode setting, and `select_weapon_set`'s three direct hand sends
(the off hand emptied, the lead, the off hand entering) now build a batch that passes the same
gate, so the only direct player `0x006F` sender left in `authsrv.py` is
`handle_visibility_flags`' (slots 6/7/8; locked by the test). In a field nothing moved: the
load carries the hands and F1–F4 carry retail's `0x006F` pair in retail's order. The equipped
BAG and the item store are untouched, so the paper doll and the weapon-set panel still show
the weapon a town body does not; the server's swing model is untouched (a town never swings).
**`--no-town-weapon-strip` reverts** to every run before this day (the town body armed, the
switch's `0x006F` sent in a town — KNOWN-BAD, driven by the test). No schema change (no new
opcode; the hands were already `weaponcensus.py`'s slots 0/1).

**RUN 2026-09-24: prediction (1) REFUTED on the client, and the switch half a visible
regression** (studies/deskwork/CONFIRM-2026-09-24.md §1): the body holds the weapon whatever
the town `0x006E` carries (A1 = A4), and after an outpost F2 it keeps the OLD weapon while the
doll changes (A2); `--no-town-weapon-strip`'s `0x006F` redraws it (A4b). The first runsheet
(prediction (1) "no weapon in either hand" under the default; its `--walk` with `vk:` steps did
not parse — `vk:` is an `--actions` step) is superseded by the carrier fix's runsheet below.

**RUN 2026-09-24 after the merge (T1-T3, studies/deskwork/CONFIRM-2026-09-24.md §7): the
carrier is OBSERVED.** Withholding the player's town `0x006D` alone makes the body stand
EMPTY-HANDED at load (T1, the doll still holding the hammer) and after F2 (T2, the doll showing
the sword and shield); `--town-player-weapons`, the same wire plus that one message, reproduces
CONFIRM-2's stale hammer after F2 (T3). The rival below (the client arming the body from the
equipped bag once at load) is refuted: with the message withheld nothing arms it. The
CORROBORATED labels below stand as the record of what was known before this run. **The
owner's answer to the one-word question (2026-09-24): on retail no weapon is shown on the body
in a town, only on the paper doll** — the wire's picture (0 own `0x006D`, empty-handed town
`0x006E`) and now ours.

**RUN 2026-09-24, the FIELD (F1-F3, studies/deskwork/CONFIRM-2026-09-24.md §8): the field
shield is OBSERVED.** The load's player `0x006D` is now withheld in a field too (retail: 0 of 44).
A sword-and-shield field body keeps the shield at load (F1), swings the sword and lands 37 hits
with no assert (F2), and `--field-player-weapons`, the same wire plus that one message, erases the
shield again (F3). The own body gets no `0x006D` in either regime now, as on retail.

**(f) The carrier (the CONFIRM-2 desk fix, 2026-09-24).** The question the run left — WHAT
draws a town body's weapon, and what does retail send when it changes — was put to the same
96 connections with predictions stated first (`weaponcensus.py`'s "every NPC, never a player"
for the own `0x006D`; nothing agent-addressed on a switch; NPC redraws through `0x006D`),
then to the binary. **EVID-D1W-5, OBSERVED: retail sends the OWN body no `0x006D`
NPC_UPDATE_WEAPONS at all** — 0 of 46 outpost connections with a controlled agent (47 carry a
`0x0199`; `20260807T133758 :54560` has 91 messages and no `0x0022`, `0x006E` or `0x006D`, so
it cannot witness — the fix pass, EVREF-TF-4) and 0 of 44 field carry one addressed to
`0x0022`'s controlled agent; and across the corpus no (connection, agent) ever gets both a
`0x006E` and a `0x006D` (outpost 1,981 / 1,510 bodies, field 44 / 2,081, overlap 0: the
`0x006E` goes to players, the `0x006D` to NPCs, and ours sent both to the player). Our load
has sent one for the player since 2026-08-06 (`NPC_UPDATE_WEAPONS(leadhand = item 1)`), and
it sits two messages after the `0x006E` in all four CONFIRM-2 logs, under the strip too.
**EVID-D1W-6, OBSERVED:** within 5 s of every outpost own hand change — the four `0x0032`
switches, the four `0x0030` double-click equips, the `0x004F` move and the PvP panel's five
`0x0086` creations straight into equipped 0/1 on `:58638` (the axe, scythe, spear, shield and
spear of (b)), **14 of 14** (the first record pinned 9; the fix pass added the five, EVREF-TF-2
/ TF-R4, and the evidence review widened the window to 60 s with the same result) — nothing
addressed to the own agent is a `0x006D` or a hand `0x006F` (t=224.632's switch draws
movement rows only, `0x0029`/`0x002B`; the `0x004F` its `0x0025`/`0x0029`/`0x002B`/`0x0028`/
`0x00F1`; the `0x0086` head creation on `:58557` draws its `0x006F [336, 6, 23284]`, the
armour precedent of (c)); outpost strangers with more than one `0x006D` never change hands
(0 of 1,510 bodies — 1,443 with one, 21 with two, 46 with three or more, all repeating the
same pair) while field bodies do (6), and the field's four own switches carry their hand
`0x006F`. So the redraws exist and retail uses neither in a town. **EVID-D1W-7, read from
build 38797 (made precise by the fix pass, EVREF-TF-6):** the client keeps **one
visual-equipment store per agent, at record+0x24, slots 0..8**, and the `0x006D` worker
(0x00810B70, from the handler 0x0091E1A0; slots 0..1 — `inc ebx; cmp ebx, 2` at 0x00810DD6 —
BOTH written unconditionally), the `0x006E` worker (0x00810E30, slots 0..8) and the `0x006F`
worker (0x008110F0) all write it through the one setter **0x0081BE10** — its only three
direct callers (`codescan --xrefs 0x0081BE10`: 0x00810BCB, 0x00810E8B, 0x00811145), each
resolving the agent through 0x005FC380 (kind 1) and storing `[record + slot*4 + 0x24] =
item`; a slot-0 write also puts the item's type byte at record+0x48, or **0x2E when the item
is 0** (0x0081BE3D). Its reader, bounded to direct calls: the AvApi dresser 0x007DFCE0 has
exactly those three workers as callers (0x00810D5E, 0x0081101E, 0x008112D0), and its callee
0x007F70B0's other four direct callers (0x007E0764 / 0x007E0773 / 0x007E0879 / 0x007E0887)
take slots 0/1 from the getter 0x0080D4C0 over the same record — so every direct path into
the avatar's hand equip draws from the store the three messages write (indirect and vtable
paths, and stores to +0x24 outside the setter, NOT searched). Last writer wins — **and that
half is OBSERVED on our client, in a FIELD** (the engineering review's control, TF-R1):
harness run `20260923T154229`, wire record `authsrv-20260923T154308-c1.jsonl` seq 111
`0x006E [1, 1, 10, 3, 4, 5, 6, 7, 0, 0]` (the shield, item 10, at visual 1) then seq 113
`0x006D [1, 1, 0]`, and `walk1-wait.png` cropped at (860,500,1080,740) shows the sword in the
right hand and NO shield, while CONFIRM-2 A4b's `0x006F [1, 1, 12]` draws the same
starter-shield model on the left arm. So the town reading of all four frames — the `0x006E`
emptied the store, our `0x006D` re-armed it with the hammer (A1 = A4), the town switch's
dropped `0x006F` left it there (A2), the revert arm's `0x006F` overwrote it (A4b) — is
**CORROBORATED** (the binary plus the field frame), and OBSERVED for the town lead is owed to
the runsheet's ARM 1, the first run to withhold the message: no CONFIRM-2 run withheld it (it
went out at gamesrv.log line 151 in all four), so a client that armed the body from the
equipped bag once at load would give the same four frames — the runsheet's rival (EVREF-TF-1
/ TF-R2, the fix pass's relabel at every site). **(e) is corrected:** the array is not "the
channel" but one of three carriers into that store; retail's town body is bare because every
carrier leaves it bare; and the stale weapon the owner saw was most likely OUR message, not
a retail quirk — **there is no redraw to invent.**

**Shipped (the carrier fix).** `send_player_weapons` in `authsrv.py` — the load's player
`0x006D` now has ONE sender, gated by `townweapon.player_weapons_sent(field)`: **withheld in a
town** under the strip (the log: `TOWN WEAPON: the player's 0x006D (lead item 1) is not sent
-- a town; retail sends the own body none (0 of 46 outpost connections with a controlled
agent, OBSERVED), and it is the likeliest carrier … (… CORROBORATED, this run the
observation)`), sent in a field.
Two revert arms: **`--no-town-weapon-strip`** restores every pre-2026-09-23 carrier at once —
the town `0x006E` armed, the switch's `0x006F`, AND the `0x006D` — the pre-pass-4 wire exactly;
**`--town-player-weapons`** (new, default OFF) restores the `0x006D` alone with the strip on —
CONFIRM-2's own picture, KNOWN-BAD, and the A/B for the run below. Nothing new goes on the
wire; in a field nothing moved. `test_townweapon` 45 bare / 60 vaulted: the three census
pins above against the tape, `send_player_weapons`' four arms with both revert flags as
KNOWN-BAD (yesterday's default — the town `0x006D` sent — reddens the town pin), vacuity (an
emptied hand), the TOWN F2 through the real `select_weapon_set` with no `0x006F` and no
`0x006D`, and the source locks (one `0x006D` sender naming the player; the flag declared and
wired). The docstrings of `townweapon.py`, `visible_worn` and `visible_slot_writes` and the
`--no-town-weapon-strip` help no longer call the array the channel.

**Runsheet and PREDICTIONS (pre-registered; the orchestrator runs it after the merge).**
Outpost, server `--weapon-set 1=starter_sword+starter_shield`; harness
`--actions "0:play 40:vk:0x71"` (F2, timed from the Play click, fires before the walk) and
`--walk "wait:3 shot:1 i:0.4 wait:2 shot:1"`; the body crop is about (860,500,1080,740) of the
1936x1040 frame. *Default* — the gamesrv log has `TOWN WEAPON: the player's 0x006D (lead
item 1) is not sent` and **no** `NPC_UPDATE_WEAPONS(leadhand` line on c1, the `0x006E`
labelled `[hands empty: a town]`, then `SET_ACTIVE_WEAPON_SET(1)` and `TOWN WEAPON: the body's
0x006F for the lead hand (item 11), the off hand (item 12) is not sent`; shot 1 (after F2):
the body stands **EMPTY-HANDED — no hammer, no sword, no shield**; shot 2 (the inventory
open): the doll holds the **sword and shield**, set 2 active, the hammer in the backpack; no
assert. *A/B, `--town-player-weapons`* — `NPC_UPDATE_WEAPONS(leadhand = item 1)` in the log;
shot 1: the body **holds the HAMMER** after F2 (CONFIRM-2's A2 reproduced) while the doll
shows the sword and shield. *Rivals:* the default's body holding the hammer anyway means a
third carrier (the client reading the equipped bag) and refutes this fix; holding the sword
means the client redraws from the `0x0152` swap and both records are wrong. **A note for the
reader:** the task that produced this fix expected "the body must hold the sword and shield
after F2" — that picture is NOT retail's (0 of 2,245 outpost `0x006E` messages — 1,981
bodies — carry a hand, and no own `0x006D`), and sending it would be an invention.
*Unexercised under the default* (the engineering review, TF-R6): combat in an outpost with no
hand declared — the empty `0x006E` leaves the client's per-agent type byte (record+0x48) at
the setter's 0x2E, where the `0x006D` used to put the hammer's type; an outpost run with
`--enemy` and no `--explorable` would be the first swing from that state. Probably retail's
own empty-handed state; not run. **The owner's one-word question**, on retail, in any
outpost: *does your character hold a weapon at all while standing in an outpost?* The wire
says no. A "yes" means the retail client draws from data this census cannot see, and the fix
moves.

**Open after (f) — corrected by the fix pass (TF-R1).** The FIELD's player `0x006D` is a
**defect**, not a divergence: retail sends none there either (0 of 44) and ours sends
`[player, lead, 0]` two messages after the `0x006E` — and the `0x006D` worker writes BOTH
slots, so its zero off hand is the last hand write and **every sword-and-shield field load
loses its shield on the body** (EVID-D1W-7's field frame; 48 harness runs carry the slice's
`WEAPON_SET[0] leadhand=1 offhand=10`). The first record said "the body is right
regardless"; it is not. Two fixes, both outside this town lane and a field run's choice:
carry the bag's off hand (`itemstore.hand_items(...)[1]`) as the third field, so the last
writer agrees with the `0x006E`; or withhold it in a field too, as retail does — UNVERIFIED
for the swing path, because the send site's history (the 2026-08-06 ItCliApi.cpp(400)
assert) was about a wrong VALUE and says nothing about absence, and the `0x006D` worker does
more than the setter for slot 0 (a type-6 branch through 0x008451E0 / 0x00633D70 and a
nine-way jump table at 0x00810E04 that the `0x006E` worker may or may not share — NOT read).
Beside it, the send site's pre-existing `or WEAPON_ITEM_ID` fallback names the hammer for an
EMPTIED lead (item 1, by then in the backpack; unreachable at load, pinned by
`test_townweapon`). `PLAN.md` §8.1's D1 line carries both.

**The fix pass (2026-09-24, the evidence review's EVREF-TF-1..7 and the engineering review's
TF-R1..R8; every finding's evidence re-derived before it was applied).** The carrier claim
relabelled from OBSERVED to CORROBORATED wherever it stood — the `send_player_weapons` log
line, `townweapon.py`'s THE CARRIER, both flags' help, the census pin's message, CONFIRM-2 §5
— because no run has withheld the message and the runsheet's own rival would give the same
frames; the field frame (TF-R1) cited as the on-client control that earns OBSERVED for
last-writer-wins itself (EVREF-TF-1 / TF-R2, the blockers). The field `0x006D`'s "harmless"
text corrected in five places and the shield opened as its own item; the field wire NOT
changed (TF-R1, the other blocker). The own-addressed pin widened from 9 to all 14 outpost
hand changes with the PvP panel's five `0x0086` hand creations (EVREF-TF-2 / TF-R4). The
`send_player_weapons` VACUITY check, which the town gate made unable to fail on its own (a
mutation of `player_weapons_sent` reddened it together with the TOWN check), replaced by a
FIELD pin of the emptied-lead fallback that reddens when the fallback is fixed (EVREF-TF-3 /
TF-R3). "0 of 47" made "0 of 46 with a controlled agent", pinned (EVREF-TF-4); the revert-arm
log line worded per arm — the `0x006E` is ARMED under `--no-town-weapon-strip` (EVREF-TF-5);
the store called what it is, with its direct readers named and the review's overlap census
reproduced (EVREF-TF-6); "2,245 bodies" made "2,245 messages, 1,981 bodies" in the study,
the leaf, the flag comments and the test, and the garbled KNOWN-BAD message rewritten
(EVREF-TF-7 / TF-R7); the town-combat note added above (TF-R6). Declined: squashing the two
commits (TF-R5 — both hashes are cited by two reviews; the merge message is to say d267ab3b
was red on `test_itemmoves`' source lock until 8a73d855); editing the PLAN-LOG entry's title
(append-only — the fix-pass entry on top corrects it by name, the log's own rule).
`test_townweapon` stays 45 bare / 60 vaulted: one check replaced, conjuncts added.

**The fix pass (2026-09-23, the combined review's WEAP-R1–R8; no blocker, no major; every
finding's evidence re-derived before it was applied, and none declined).** (e) re-labelled and
MEASURED — the flags census the first record cited was not a regime census; the handlers' path
disassembled to depth 2 with its unsearched edge named (R1). The strangers' 31 outpost armour
`0x006F` cited in (c), and the town ARMOUR-equip gap recorded as Open here and in `PLAN.md`
§8.1 (R2). "Bodies" made "messages" in (d), the leaf, the test and TESTS.md, with the
distinct-body count beside it — 403 of 1,510 (R3). The source lock's regex widened to every
`*send(` spelling, `_send(` / `hsend(` / `psend(` included (R4). The burst's `0x006E` label
built from the ARRAY — `(+armour) [hands empty: a town]` in a town, `(weapon+armour)` in a
field — and locked; the runsheet above reads the new label (R5). The own body cross-checked
against `0x0022` WORLD_UPDATE_CONTROLLED_AGENT: the armour join names exactly the controlled
agents that have a `0x006E` on 91 of 91 regime connections (47 outpost, 44 field; four
connections' `0x0022` also names a second, bodiless agent for a moment — value 1 between the
own body's 3 and 1), pinned as a conjunct in `test_townweapon` §2 (R6). The merge sweep's list
is to include every test that imports `authsrv` as a module, not only the text readers (R7,
process — the fix pass's own sweep does). `itemstore.py`'s "the same outpost sessions" made
"the same outpost (map 248) on two sessions" — `0x0199 [.., 248, 0, ..]` on both `:58638`
(20260919) and `:58557` (20260917) (R8). `test_townweapon`: floor 35 → 36 bare (the label
lock), 46 → 48 vaulted (the cross-check), each from a real green run.

### World-map travel — `c2s 0x00B1 MAP_TRAVEL`, the `s2c 0x0094` unlock state, and the transfer it hands off (DESKWORK-D1 step 7, 2026-09-23)

**The question.** The retail c2s triage (step 3) named `0x00B1` MAP_TRAVEL medium
and left it `DROPPED_ON_PURPOSE`: an arm that transferred the client to an unbuilt
map would strand it, and the route asked two prior things — what the world map's
click gates on, and the unlocked-outpost state nothing models. Both are answered
here from the tapes and the binary, and the arm ships.

**The request, re-derived from the tapes (OBSERVED, 10 of 10 on 10 connections over
6 captures; `livewire.decode_conn`).** Every c2s `0x00B1` is `[map_id, 0, 0, 0, 1]`
(word map_id, byte, word, byte, byte). The destination map varies (248 ×5, 148 ×2,
281, 242, 449); **the trailing four fields were `0, 0, 0, 1` on all ten and never
varied** — region / district / language / a flag are the candidates the field widths
suggest, UNVERIFIED because nothing on the tape moves them. The reply is
`0x01D9 [2, 1, '']` then the transfer pair `0x01A5` GAME_SERVER_TRANSFER and `0x0099`
MAP_UPDATE_CURRENT — **10 of 10 in sequence, 9 of 10 with `0x01D9` the first non-clock
s2c** (the tenth interleaves an ambient `0x001E`/`0x0029` first, the same busy-wire
effect the kick's row shows) — then the server hangs up and the client re-dials the
transfer address, sending c2s `0x0008` every time. **No `0x0028` AGENT_STOP_MOVING
precedes it** (the player is standing in an outpost), unlike a portal transfer where
the moving body is stopped first (SLICE-B8). The `0x01D9` batch is OBSERVED; the two
bytes' and the empty string's meaning is UNVERIFIED — its worker `0x0085a290` sets a
state at `[ctx+0x54]` and fires UI notifications (`0x1000012a`/`12d`/`130`), with no
assert gating it, so a bare send is accepted (RECONSTRUCTION that it is; the
client-confirmation run is the witness). Retail's `0x01D9` rides its own TCP segment
18.6–42.2 ms before the pair's (10 of 10); ours go out back to back — the gap is
UNREPRODUCED, worth reproducing only if the client run shows a UI race.

**The send gate, statically (38797; `sendsites.py`, `codescan.py --xrefs/--dis`,
`asserts.py`; corrected by the fix pass).** The travel wrapper `0x0085C280` has no
direct CALL — `sendsites.py` counts calls — and is NOT "reached through a pointer":
`codescan --xrefs` finds 0 stored words holding its VA and exactly one direct reference,
the one-instruction thunk `0x008576E0` (`jmp 0x85c280`), whose one caller is the `call`
at `0x004A791F`. **The route's "one caller `0x004A791F`" was right**; the landing's
pointer sentence was wrong. That call sits in `0x004A78C0`, which reads a UI record's
`[+0x20]`: `== 1` sends `0x00B1` (the travel path), `== 0` and `== 2` take sibling thunks
`0x008576D0`/`0x008576F0`. Before that switch, `0x004A78C0` ITSELF calls the three
map-state getters at `0x004A78ED`/`F6`/`FF` — `0x0084DE70` (`missionContext+0x2a8`
bit 1), `0x0084DF60` (bit 4) and `0x0084DEC0` (`missionContext+0x190` bit 0) — and a
failed getter branches to `0x004A795A`, which continues into further calls rather than
returning (the refuter read it as a UI-frame confirm path): an immediate-vs-deferred
branch, not send-vs-drop. `0x004A78C0` has three direct callers. What the world map
OFFERS as a clickable destination is the unlock state below; the send itself carries
whatever record the UI built.

**The unlock state nothing modelled — `s2c 0x0094` (schema 148: five `array32`) — and
the SECOND writer the fix pass found.** Our server sent no `0x0094` (grep `authsrv.py` at
`3b2df394`), but the client's set was NOT empty: **`s2c 0x0099` MAP_UPDATE_CURRENT's
handler `0x0091ec20` pushes `[msg+8]`, `[msg+4]` and calls `0x00812600`, which loads
`[[ctx]+0x2c] + 0x60c` — the SAME store `0x0094`'s fifth CopyBits fills (`lea ecx,
[esi+0x60c]` at `0x00812343`) — and calls `0x0059d130`, which ends `bts eax, edx` at
`0x0059d239` (word `map>>5`, bit `map&31`).** OBSERVED in the binary. Our server has
always sent `0x0099 [map, 0]` at every load and in every transfer, so before this arc
the client's arr4 held the current map plus every map zoned into; what `0x0094` adds is
the OTHER served outposts, all at once. `0x0094`'s handler `0x0091eb10 -> 0x008122f0`
copies the five arrays into `charCtx +0x5cc/+0x5dc/+0x5ec/+0x5fc/+0x60c` through
Array::CopyBits `0x00473550` — a REPLACE, **no create-once, no ordering gate**,
`Array:130` `Bytes() >= bytes` the only assert on the path (`ChCliApi:1641` sits at
`0x00811AB9`, the fog accumulator — the landing misplaced it here) — so it is safe to
send in any load state; and CopyBits grows the store before that check, so our 28-dword
(38797) / 29-dword (38888) arr4 against retail's constant 27 cannot assert
(RECONSTRUCTION; the width is ours).
**MEASURED over the 96 live connections, 29 sightings on 29 connections:** arr4 is a
map-id bitmap, bit index == map id, 27 dwords on 29 of 29; arr0-3 are EMPTY on 27 of 29,
and on the two Kamadan-character logins (`20260914T005758`, `20260916T150306`) arr0 and
arr1 carry 18 dwords with bit 544 set — UNVERIFIED what they are (mission completion is a
candidate); all four are sent empty as a labelled choice. **arr4 is the client's
KNOWN-MAPS set, not an outpost list:** ids our content marks explorable are set in it —
280 Isle of the Nameless on 14 of 29, 146 Lakeside County on 5 of 29 (168 is set on 29 of
29, but our row 168 is a created chain in a reused slot and says nothing of retail's
type). Offering only enabled non-explorable content maps is OUR policy, RECONSTRUCTION.
**Cadence:** retail sends `0x0094` ONCE PER LOGIN — on a login's first map-loading
connection (28 of 29 first of their capture; the 29th is `20260919T103604`'s second
login), on 0 of 61 connections that arrive from a transfer, all 10 world-map-travel
arrivals included — after `0x0199` and before the fog pair `0x008B`/`0x008A` on 29 of 29
(and after the connection's first `0x0099`, 29 of 29). In-session unlocks then arrive as
`0x0099 [map, 1]`: one on the corpus, `[281, 1]` on `20260817T231139` conn `54071`
(map 310) at +783.2 s, the second field's only non-zero in 268 `0x0099`. **THE JOIN,
which replaces the landing's "across 22 connections EVERY map the client then sent
`0x00B1` to had its arr4 bit set at load" (9 of 10, and no 22 exists):** every one of the
10 `0x00B1` destinations had its arr4 bit set BEFORE the click — 9 by the login's
`0x0094` (248 ×5, 242, 148 ×2, 449), and 281 by that `0x0099 [281, 1]` 24 s before the
owner clicked it (its bit was CLEAR in the login's `0x0094`, which the landing's own
parenthetical admitted while the sentence claimed the opposite). The client already
models this id space: `c2s 0x0092` MISSION_MASK_REPORT reports one bit per map id back
(`authsrv.mission_mask_bytes`). **LABELS:** arr4 == the known-maps bitmap, bit == map
id — OBSERVED (29 sightings, both handlers' offsets); its two writers (`0x0094` replaces,
`0x0099` sets one bit) — OBSERVED in the binary; arr0-3 — UNVERIFIED; **that a set arr4
bit is what the world map offers as a pin — CORROBORATED by the join (a set bit preceded
every click, by one writer or the other) and RECONSTRUCTION** until the owner opens `M`
on our client and sees our outposts; the click's other preconditions are the getters
inside `0x004A78C0` above.

**What the server now does (`handle_map_travel`, `maptravel.py`, behind
`--no-map-travel`; the login's `0x0094` behind `--no-map-unlock`; as corrected by the
fix pass).**

- **At LOGIN, once — not on every load.** Right after `INSTANCE_LOAD_INFO` and before
  the fog-init pair (retail's bracket, 29 of 29), `send(0x0094, payload)` from
  `maptravel.unlock_message`: arr0-3 empty, arr4 with bit == map id for every travelable
  content map. **Travelable = enabled, NOT explorable, with a KNOWN spawn, and warmed** —
  the `(0, 0)` placeholder rows (`[map.194]`, `[map.55]`: "not a coordinate") are
  withheld, and so is any destination whose navmesh did not load at startup
  (`TRAVEL_UNSERVABLE`, filled by `main()`'s prewarm: 165, 166, 167 on this archive
  generation, whose created-chain files are not installed). The offer on this archive is
  therefore `[143, 144, 148, 242, 248, 310, 449]`. The bitmap is
  `mission_mask_bytes(MAP_ID_COUNT) // 4` dwords wide (28 on 38797; retail's 27, labelled);
  an id past the width is logged as overflow, never dropped silently. **Not resent on a
  re-entry after our own transfer**: `send_transfer` writes a one-shot
  `TRANSFER_ARRIVALS[(world, player)] = (dest, issued_at)` and the load pops it
  (`maptravel.arrival_skips_unlock`, TTL 300 s; consumed whatever the answer, so a later
  relaunch on the same map gets its `0x0094` — `TRANSFERS_ISSUED` is never popped, which
  is why it could not serve). A resend would REPLACE arr4 and wipe what `0x0099`
  accumulated for maps outside our set. **The order matters because of the second
  writer**: our `0x0094` precedes the burst's `0x0099 [map, 0]`, so the replace comes
  first and the current map's bit is set after it — our bitmap may omit the map you are on
  (an explorable under `--map 168`). **One `0x0094` site in the server**, counted over
  every spelling across `toolkit/authsrv/*.py` by `test_maptravel` (a duplicate sender of
  unlock state wiped a library and crashed a client on 2026-09-15). A labelled policy
  (RECONSTRUCTION of the offer from our content), the shape of the hero add's `0x0018`
  from the owned set.
- **On `c2s 0x00B1`**, `plan_travel(WORLD, cur_map, dest, exclude=TRAVEL_UNSERVABLE)`
  decides: **accept** a travelable map that is not the one you are on → `send(0x01D9,
  [2, 1, ''])` then `send_transfer(..., send_stop=False)` (the pair `0x01A5`/`0x0099`, no
  `0x0028`) then a graceful close; the client re-dials and the re-entry serves the
  destination. The transfer carries the party, heroes and kicked-hero store through
  `zone_carry_store`, exactly as a portal does (SLICE-B8 / JARIN). **refuse, with NOTHING
  sent** (retail's refusal reply is NOT FOUND on any tape — no live `0x00B1` went
  unanswered, none targeted the current map): the map you are already on, a map with no
  served content row, an explorable, a `(0, 0)`-placeholder row, an unwarmed destination.
  Each refusal logs its reason.
- **The prewarm** (`83754cc6`, corrected): every travelable destination's navmesh is read
  at startup through ONE shared archive and file table, gated as the portal prewarm is on
  `--map` (the harness hands `--map` to the gamesrv alone, so the auth-only instance pays
  nothing) and on the ARM (`a.no_map_travel`, read off the argparse namespace — the
  landing's `MAP_UNLOCK_ENABLED` gate was read ~1,000 lines before the flag block set it
  and never acted). MEASURED: 17.4 s → 13.0 s over the 12-map content set with the shared
  archive (the rest is each map's own decompression), and startup to the listening line
  17.7 s → **8.1 s** with `--map 449` once the placeholder rows left the set; 2.9 s under
  `--no-map-travel`; 1.8 s without `--map`. The harness's listen deadline
  (`session.Stack.start`) 20 → 60 s with this as the reason. A failed prewarm is worded
  as "unwarmed, WITHHELD as a destination", not "this run serves NO collision".
- `0x00B1` came OFF the `DROPPED_ON_PURPOSE` allowlist in the landing (`test_dispatch`
  §10, `test_c2striage`); `overrides.json` GAME_CMSG 177's `why` records the arm and, now,
  the two writers, the join and the thunk.

**What a run cannot settle alone, and the runsheet exists for.** Whether a set arr4 bit
is SUFFICIENT for the world map to offer a pin (the join shows one preceded every click;
sufficiency is the owner's `M` press); retail's acceptance of a bare `0x01D9`
(RECONSTRUCTION, no tape shows one out of the travel sequence); the three trailing
`0x00B1` fields' meaning (UNVERIFIED); the `0x01D9` → pair segment gap (UNREPRODUCED).
The landing said maps 194 and 310 "would strand the body": 194 and **55** carry the
`(0, 0)` placeholder and the gate now withholds both; **310's spawn is retail's own
measured arrival** (`(5089, 940)` on plane 4, one trapezoid — its row's provenance), not a
placeholder, and it is offered.

**RUN 2026-09-24 and BLOCKED — do not run as written** (studies/deskwork/CONFIRM-2026-09-24.md
§3): `M` on 449 asserts (its continent has no fog init, as the warning below says), and no
fog-initialised view carries a second pin.

**Runsheet (the orchestrator runs it after the merge; loopback client, caged; the
owner's hands for `M` and the click — a world-map click on an outpost is a travel
order).** Through the harness, which supplies the gamesrv's `--transfer-alt` (every proven
transfer used a second alias; re-dialling the endpoint just cut is NOT FOUND, tape T9):

    python toolkit/harness/session.py --replace --keep-open --hold 900 --game-args "--map 449 --persist"

or standalone, then a caged loopback client:

    python toolkit/authsrv/authsrv.py --map 449 --persist --transfer-alt 127.0.0.31

The gamesrv log at startup prints `pre-warming map N: a travel destination` for 143, 144,
148, 165, 166, 167, 242, 248 and 310, then `travel destinations WITHHELD (unwarmed):
[165, 166, 167]`; at the login's load, `MAP_TRAVEL_UNLOCK [7 destination(s) in arr4]`
right after `INSTANCE_LOAD_INFO` and before `MAP_EXPLORATION_INIT_BEGIN`. PREDICTIONS:

1. **Press `M` in Kamadan.** The world map offers our served outposts as clickable pins,
   each on whichever continent view the client files it under: Great Temple of Balthazar
   (248), Pre-Searing Ascalon (148), map 242, map 310, the two test slots 143/144 — and
   Kamadan itself (its bit from the burst's `0x0099`). Lion's Arch and Kaineng Center do
   NOT appear (withheld: placeholder spawns); 165/166/167 do NOT appear (withheld:
   unwarmed). If NO pin but Kamadan's appears, a set arr4 bit is not sufficient — record
   it. (Fog init must be on, the default; never press `M` on a map whose fog init was
   skipped — `GmMapView.cpp(1731)`.)
2. **Click Great Temple of Balthazar (248).** The gamesrv log prints `MAP_TRAVEL to map
   248: 0x01D9 then the transfer pair; the client re-dials`, then on the new connection
   `MAP UNLOCK: a re-entry after our own transfer -- 0x0094 NOT resent`; the client fades
   and loads the Great Temple; the party, any heroes and a stored kick survive (the
   carry). Press `M` there: the same pins (Kamadan's bit stays — the load's `0x0099` set
   it and nothing replaced arr4).
3. **Travel back to Kamadan, then relaunch the client** (`--persist`): the fresh login's
   load prints `MAP_TRAVEL_UNLOCK [...]` again (the one-shot marker was consumed) and `M`
   shows every pin. If it shows only Kamadan, the marker was not consumed — record it.
4. **If the UI lets you select the map you are on**: the log prints `MAP_TRAVEL(map 449)
   refused: already on map 449; nothing sent`, and nothing happens.
5. **Control, `--no-map-travel`** (`--game-args "--map 449 --persist --no-map-travel"`):
   the pins are unchanged (the unlock is still sent; no prewarm lines at startup); a click
   on Great Temple logs `MAP_TRAVEL ignored (--no-map-travel)` and nothing happens — the
   arm is the lever.
6. **Control, `--no-map-unlock`** (`--game-args "--map 449 --persist --no-map-unlock"`):
   the world map shows **Kamadan's pin and no other** — arr4 holds only what `0x0099` set.
   (The landing predicted an EMPTY map; that was wrong, and an owner seeing one pin would
   have been scored against the wrong expectation.) If a pin appears for a map never
   zoned into, `0x0099` is not arr4's only other writer — record it.

**The fix pass (2026-09-23, the same day).** Two reviews of the landing — an evidence
refuter that re-derived the lane from the 96 live connections and the pinned client before
reading the notes, and an engineering review with ten mutation arms and startup timings —
found the ARM sound (the `0x00B1` shape, the `0x01D9` → `0x01A5` → `0x0099` batch, the
refusals, the allowlist move; 10 of 10 reproduced) and the UNLOCK half's evidence not.
Every contested measurement was re-derived here before a line changed, and every one of
theirs held. Moved: the second writer of arr4, `0x0099`'s `bts`, named and its order
against `0x0094` locked (TRAV-EV-1, blocker); "every destination set at load across 22
connections" restated as 9 of 10 at load and 10 of 10 counting `0x0099`, the 22 dropped,
the join added to the tape section (TRAV-EV-2 / ENG-TRAV-1, blockers); "arr0-3 empty on
every tape" restated as 27 of 29 (ENG-TRAV-2, blocker); the per-load resend after the fog
pair, labelled "as retail does", replaced by once-per-login before the fog pair with the
one-shot arrival marker (TRAV-EV-3 / ENG-TRAV-3); arr4 relabelled the known-maps set with
the explorables it carries, and the width divergence named (TRAV-EV-5 / ENG-TRAV-11); the
constant-against-constant KNOWN-BAD replaced by `travel_batch_ok` on the real handler's
output with `0x01D9` dropped, the gate locked by context, the one-sender guard widened to
every spelling, the payload pinned, the flags locked contiguously — the engineer's four
uncaught mutations (M5–M7, M9) now redden (TRAV-EV-4 / ENG-TRAV-6/7); the offer and the
arm withhold `(0, 0)`-placeholder rows and unwarmed destinations (ENG-TRAV-8 /
TRAV-EV-9); the prewarm gated on `--map` and the arm, shared, costed, and the harness
deadline raised (ENG-TRAV-4/5, TRAV-EV-8); the runsheet given `--transfer-alt` through the
harness and `--map 449`, its `--no-map-unlock` prediction corrected (ENG-TRAV-9);
`ChCliApi:1641` dropped from the `0x0094` path (TRAV-EV-6); "reached through a pointer"
corrected to the direct jmp thunk and the route's caller credited (TRAV-EV-7 /
ENG-TRAV-10); the timing gap labelled (TRAV-EV-10); PLAN.md §8.1 trimmed to the open
confirmation, the sweep count named, the prewarm recorded (ENG-TRAV-12). **Declined**:
relabelling "arr4 gates the world map" CONTESTED (ENG-TRAV-1's suggestion) — the 281 case
does not contest it once the second writer is counted, since 281's bit WAS set before the
click, by `0x0099`; CORROBORATED-by-the-join and RECONSTRUCTION-until-`M` is the honest
pair. Also declined: reproducing the 18.6–42.2 ms segment gap (TRAV-EV-10, a nit —
labelled instead), and an explicit `travel = true` content column (ENG-TRAV-8's
alternative) — the mechanical gates (spawn known, mesh warmed) withhold exactly the rows
the reviews named without a schema change to a shared content file.

### The party family — `c2s 0x009F HENCHMAN_ADD`, and the hireable marker `0x0071` (DESKWORK-D1 step 5, 2026-09-23)

**Re-derived from the tape, no client launched.** Route step 5 asked the party
family 0x98–0xB2 from HENCHMAN_ADD's witness: how outpost henchmen exist before
the add, what the add's agent ids point at, what happens to the henchman after,
and what the party carries into the explorable. The witness is capture
`20260819T132414`, connection `:53419` (an outpost, map 242, Shing Jea
Monastery, player 14, party 11), with the field side on the same capture's
`:52606` (map 238) and the return on `:55414` (map 242 again). The second
henchman capture `20260817T231139` corroborates the field shape (four loads,
maps 309–312, three level-20 henchmen).

**How the outpost henchmen exist — OBSERVED.** Six henchmen stand in the outpost
as ordinary kind-9 NPC bodies, agents 1..6. Each is brought up like any NPC —
`0x0056`/`0x0057` definition (defs 3485–3490), then a pre-create burst sent
TWICE per connection (once at the load with the definitions, again as the body
is created 5–9 s later): `0x009B` name, `0x009F [36, agent, 3]` the displayed
level, `0x00A6` profession, **`0x0071 [agent]`**, then `0x00F0`, `0x0020` create
(kind 9, speed 300), `0x0161` for its weapon item and `0x006D` — 24 of 24 sends
in that order (the landing wrote `0x009A` here; no `0x009A` reaches agents 1..6
in the outpost, it is the field's). **Two of those messages no other kind-9 NPC
gets: `0x0071`, and the level property 36.** Both were sent for exactly those six
agents and for **none** of the 38 other kind-9 NPCs on `:53419` (44 in all; 35
others of 41 on `:55414`), in **both** outpost connections and **never** in the
field; across all 96 live connections `0x0071` appears on 11, every one an
outpost (maps 242, 281, 449). Its handler (`0x0091E220 → 0x008113D0`, `codescan
--dis`) **binary-search-inserts** the agent id into a sorted dword set at
`[ctx+0x2c]+0x574` — the same object `0x00B0`'s per-player array (`+0x80C`)
lives in, not the party manager at `[ctx+0x4c]` that `0x01BF` and `0x01B2` use
(the landing said "party context"); a duplicate id is skipped and no agent is
looked up. The set's enumerator `0x0080E200` is called from `PtSearch` (asserts
PtSearch:365 `listFrame`, PtSearch:1116 `partySearchTab < LISTS`), which ties
the set to the party-search panel's lists from code. So `0x0071` is what marks
an agent HIREABLE — the set the party window's henchman list offers.
`GAME_SMSG_PARTY_HENCHMAN_HIREABLE` (medium: the handler read, the 6-of-6
correlation, the whole-corpus census; `schema/overrides.json` GAME_SMSG 113;
GWCA's offset numbering names its own `0x0071` differently and is not leaned
on). Their `0x0020` allegiance dword is `'play'` (ALLEGIANCE_PLAYER), 6 of 6 on
both outpost connections, where every other kind-9 NPC there is `'nonc'` (43 of
43, 36 of 36) — the third discriminator, and the one the server does not
reproduce (below).

**The add — OBSERVED, 3 of 3.** c2s `0x009F [word agent_id]` carries the standing
henchman's agent id (`[4]`, `[2]`, `[6]` at t=126.234/128.201/130.186), each
answered 31–132 ms later by **`0x00B0` PLAYER_PARTY_SIZE then the `0x01BF`
roster row, in one plaintext chunk** — SIZE BEFORE ROW (the hero KICK answers
row `0x01C3` then size, so the henchman is the size-then-row shape, and the hero
ADD was armed to mirror the henchman). The party grows 1 → 2 → 3 → 4. The three
adds' agent ids point at the standing NPCs (agents 4, 2, 6); **the NPC is NOT
destroyed** — no `0x0021` follows, it keeps standing in the outpost.

**`0x01BF`'s two trailing bytes, settled.** `agents.party_henchman_add`'s
docstring records them NOT FOUND ("GWCA and OpenTyria call them profession and
level ... no naming assert"). The wire settles it: byte4 == the agent's `0x00A6`
profession (2/1/7 for agents 4/2/6, 3 of 3) and byte5 == its `0x0056` LEVEL
(3, the Shing Jea level-3 henchmen). **PROFESSION and LEVEL, CORROBORATED** from
two independent server messages. The `0x01BF` NAME is the agent's `0x009B` proper
name, which **differs on the wire** from its `0x0056` definition name (e.g. agent
4: `0x009B` `[0x5985, 0x8759, 0x86AC, 0x3CA8]` vs def 3489's
`[0x3EB8, 0xC34C, 0xC676, 0x41EC]`).

**The field carry — OBSERVED, with one NOT FOUND.** On zone into the explorable
(`:52606`, map 238) the party window is rebuilt (`0x01D2`/`0x01CB`/`0x01D3`/
`0x01B2`/`0x01BE`) and each party henchman gets, in the add order (4, 2, 6):
`0x00B0`, `0x00B1 [0, 1]`, `0x01BF [1, 28|29|30, name, prof, 3]` and a fresh
world body (`0x009A`, `0x009B`, `0x0020` kind 9, `0x006D`) at NEW agent ids
28/29/30. Two independent captures agree the field's `0x00B0` for the henchmen
**climbs by 2 per row** (2, 4, 6), where the outpost climbs by 1 — the mechanism
for the doubling is **NOT FOUND** (recorded, not modelled). On return to the
outpost (`:55414`) the party PERSISTS: the six henchmen are re-created standing
and the window is rebuilt with `0x01BF` for the outpost agent ids again.

**The rest of 0x98–0xB2 — what each send is, at the confidence the evidence
gives.** All 27 wrappers sit in `PyCliParty` (asserts `0x00857A91..0x0085AC3E`;
`sendsites.py` widths agree with `msgshape` SEND descriptors, 27 of 27). The
`0x9F`, `0xA0` and `0xA1` wrappers are called from **three sibling functions**
(`0x00858410`, `0x00858450`, `0x00858490`, one thunk each at
`0x00856670/90/B0`; the landing said "one caller function"), each asserting
PyCliParty:516/525/534 `m_partyClient` and each gated on the party-client "is
mine" flag bit `0x80` (`test byte [this+0x10], 0x80`; `0x01B2`'s worker
`0x00858790` ORs it in when arg2 != 0). Reading `0xA0` as "add by player agent"
and `0xA1` as "add by player name" is inference from the sibling shape and the
string width, UNVERIFIED. On retail's wire, over 96 live connections, the range
carries exactly two opcodes: `0x009F` ×3 (one connection) and `0x00B1` ×10; no
other `0x98–0xB2` c2s was ever sent, so every other row below is static only.

| c2s | SEND shape (msgshape, static) | wrapper → caller(s) (sendsites, 38797) | retail witness | UPSTREAM name (GWCA, its numbering is ours + 2) | label |
|---|---|---|---|---|---|
| `0x98` | `[]` (4 B) | `0x0085BCF0` ← `0x00857B8C` | 0 | — | UNVERIFIED |
| `0x99` | `[]` | `0x0085BD20` ← `0x00857C2C` | 0 | — | UNVERIFIED |
| `0x9A` | `[]` | `0x0085BD50` ← `0x0085649E` | 0 | — | UNVERIFIED |
| `0x9B` | `[u8]` (8 B) | `0x0085BD80` ← `0x008583E1`, `0x008583F5` | 0 | — | UNVERIFIED |
| `0x9C` | `[u16]` | `0x0085BDB0` ← `0x00857AE4` | 0 | — | UNVERIFIED |
| `0x9D` | `[u16]` | `0x0085BDE0` ← `0x00857CA4` | 0 | — | UNVERIFIED |
| `0x9E` | `[u16]` | `0x0085BE10` ← `0x00857EE4` | 0 | — | UNVERIFIED |
| **`0x9F`** | `[u16]` agent | `0x0085BE40` ← `0x0085843A` (in `0x00858410`, PyCliParty:516, `&0x80`) | **3 of 3** | INVITE_NPC | **HENCHMAN_ADD, OBSERVED, armed** |
| `0xA0` | `[u16]` | `0x0085BE70` ← `0x0085847A` (sibling, :525) | 0 | INVITE_PLAYER | UNVERIFIED (a second player) |
| `0xA1` | `[string16(20)]` (44 B) | `0x0085BEA0` ← `0x008584BA` (sibling, :534) | 0 | INVITE_PLAYER_NAME | UNVERIFIED (a second player) |
| `0xA2` | `[]` | `0x0085BEF0`, 0 direct callers (pointer-reached) | 0 | LEAVE_GROUP | UNVERIFIED; single-player-doable, unwitnessed |
| `0xA3` | `[]` | `0x0085BF20` ← `0x0085A806` | 0 | — | UNVERIFIED |
| `0xA4` | `[u8, string16(64)]` (136 B) | `0x0085C0D0` ← `0x0085A978`, `0x0085AB35` | 0 | — | UNVERIFIED |
| `0xA5` | `[u8]` | `0x0085C140` ← `0x0085ABFA` | 0 | — | UNVERIFIED |
| `0xA6` | `[u16, u32, u8]` (16 B) | `0x0085C170` ← `0x0085ABE7` | 0 | — | UNVERIFIED |
| `0xA7` | `[]` | `0x0085C1C0` ← `0x0085AC25` | 0 | RETURN_TO_OUTPOST | UNVERIFIED; a run in a field could name it |
| **`0xA8`** | `[u16]` agent | `0x0085BF50` ← `0x0085A84A` (in `0x0085A820`, PyCliParty:1650, `&0x80`) | 0 (**1 on our client**, CONFIRM-2 §2 step 6) | KICK_NPC | **HENCHMAN_KICK, CORROBORATED on our client; armed as RECONSTRUCTION** (the kick, below) |
| `0xA9` | `[u16]` | `0x0085BF80` ← `0x0085A88A` | 0 | KICK_PLAYER | UNVERIFIED (a second player) |
| `0xAA` | `[u8, string16(32), u16]` (76 B) | `0x0085BFB0` ← `0x0085A8B2` | 0 | — | UNVERIFIED |
| `0xAB` | `[]` | `0x0085C010` ← `jne` at `0x0085A8C4` (in `0x0085A8C0`, the `&0x80` gate and nothing else: `test byte [ecx+0x10], 0x80; jne; ret`; that gate's one caller is the thunk `0x008574C0` — `call 0x47f660; ecx = [eax+0x4c]+4; jmp` — itself called from `0x0056330E`). The one reference in the image is a conditional tail-jump, which `codescan --xrefs` did not scan until 2026-09-25; the row said "0 direct callers" until then | 0 | SEARCH_CANCEL | UNVERIFIED |
| `0xAC` | `[u16]` | `0x0085C040` ← `0x0085B4E9` | 0 | — | UNVERIFIED |
| `0xAD` | `[u16]` | `0x0085C070` ← `0x0085B519` | 0 | — | UNVERIFIED |
| `0xAE` | `[u8]` | `0x0085C0A0` ← `0x0085BB4B` | 0 | — | UNVERIFIED |
| `0xAF` | `[u8]` | `0x0085C1F0` ← `0x0085AC50` | 0 | — | UNVERIFIED |
| `0xB0` | `[blob16, u8]` (24 B) | `0x0085C220`, 0 direct callers | 0 | — | UNVERIFIED |
| **`0xB1`** | `[u16, u8, u16, u8, u8]` (24 B) | `0x0085C280`, 0 direct callers | **10 of 10** | TRAVEL | **MAP_TRAVEL, OBSERVED — step 7's lane** |
| `0xB2` | `[u8]` | `0x0085C2E0`, 0 direct callers | 0 | — | UNVERIFIED |

The `0xA3..0xAF` callers carry `PyCliParty` `m_partyClient` asserts
(`:1650/:1659/:1692/:1719/:1755/:1797`). **INVITE and ACCEPT (a player joining)
need a second player and are out of scope for a single-player server.** The
henchman **KICK** (`0xA8` by the UPSTREAM reading) and **LEAVE PARTY** (`0xA2`)
were named only UPSTREAM at this step — no tape carries either c2s or its reply
(`0x01C0`, UPSTREAM-named PARTY_HENCHMAN_REMOVE, is 0 of 96 live connections) —
so neither was armed here; arming would be RECONSTRUCTION with no witnessed
reply, and the route says refuse to guess. The KICK was then named on our own
client (CONFIRM-2 §2 step 6, 2026-09-24) and armed as a labelled RECONSTRUCTION
the same day — "The kick" below; the LEAVE (`0xA2`) stays unarmed and unnamed
(no run has sent it).

**Shipped.** `henchparty.py` (leaf): `henchman_add_batch` (0x00B0 + 0x01BF, the
tape order, `agents.py`'s own builders), `hireable_bringup` (the level property
36 then `hireable_mark`'s 0x0071, sent BEFORE the create as retail does — the
count and the rest of the burst's order are RECONSTRUCTION, `create_agent_world`'s
own), `party_is_full`. `authsrv.handle_henchman_add` hires a standing hireable
henchman: 0x00B0 then 0x01BF, the NPC kept; it refuses — nothing sent, retail's
refusal reply NOT FOUND — an agent that is not a hireable henchman of this
outpost, one already in the party, and one over the cap. **ONE party count**
(`party_member_count`: player + heroes + the launch henchman + the hired
henchmen) is what the cap compares against and, through `party_size_on_wire`
(heroes behind `--party-size-no-heroes` as the load's own 0x00B0), what the
henchman add, the hero KICK and the hero ADD all put in 0x00B0 — the landing left
the two hero sites on their old `1 + henchman + heroes`, so with a hired
henchman in the party the kick sent one short and the hero add could take the
party to 5 of 4 (the fix pass's blocker; the hero add now refuses at the same
cap). The cap `OUTPOST_PARTY_CAP` is **one constant, 4**, the client's AreaInfo
`max_party` for the maps we serve (148/146/242/449; 248/280 read 8, 55/238 read
6 — a per-map table is the next step); `--henchman-cap N` (N ≥ 1) overrides.
`spawn_population` sends the level and the mark for a `hireable` row in an
OUTPOST only (a field creates the body and says why it marks nothing) and
records the row. Content: three standing henchmen (labelled the Fighter, Archer
and Cutthroat of Shing Jea's roster — the wire carries ids, the labels are
ours) in our served outpost (Ascalon City, map 148), `noncombatant` where
retail's are `'play'` (RECONSTRUCTION — every party-body path in the server keys
on ALLEGIANCE_PLAYER, so a `'play'` standing NPC would follow and fight; the
rows say so). Revert `--no-henchman-add`. `0x009F` off the DROPPED_ON_PURPOSE
allowlist; `schema/overrides.json` GAME_CMSG 159 says handled, GAME_SMSG 113
names 0x0071. Tests: `test_henchparty.py` (the batch byte-for-byte against the
tape's three replies; the refusals; the hero kick/add sizes and the hero add's
cap with hired henchmen present, the landing's sum as the KNOWN-BAD; the spawn
order and the field gate; source locks each paired with a mutation that reddens
it; floor 49 bare, 64 with the vault).

**What is armed vs deferred.** The OUTPOST add is OBSERVED end to end and
armed. The FIELD-body carry and the outpost RE-JOIN are OBSERVED on the tape but
**not armed in this step** — they reuse the existing hero/henchman body machinery
(`hero_body_create`, the launch `HENCHMAN_BODY` block) and cross-zone persistence
(charstore), which is the next increment; today a hired henchman is a roster row
and a standing NPC in the outpost, and a zone starts a fresh instance without it.
The `0x00B0`-climbs-by-2 field rule is NOT FOUND and must be settled before the
field size is trusted. **The allegiance** (`'play'` on retail) is deferred with
the field carry: serving it needs a `standing` gate on `party_bodies` and its
callers. **The map**: retail's Ascalon City (148, AreaInfo type 10) offers no
henchmen — `0x0071` is on 0 of the 11 live connections to 148, and only on maps
of types 13 (242, 449) and 11 (281) — so whether the client's list works on a
type-10 map is UNVERIFIED until the run; Kamadan (449, our `FALLBACK_MAP_ID`
with geometry) is the retail outpost with hireables if it does not.

**The fix pass (2026-09-23, two reviews).** An evidence refuter re-derived every
tape claim above (all reproduce, most byte for byte) and an engineering review
drove the handlers and mutated the tree in memory. Moved here: **HENCH-EVR-1 /
ENG-HENCH-1** (the blocker) — the hero kick and hero add did not count hired
henchmen and the hero add had no map cap; one count now (`party_member_count`,
`party_size_on_wire`), the hero add refuses at the cap, driven with the
landing's sum as the KNOWN-BAD and a raised cap as the vacuity guard.
**HENCH-EVR-2 / ENG-HENCH-2** — the test's floor of 27 was above its own bare
run of 23 ("27 bare" was false); the floor is the measured bare core, 49.
**HENCH-EVR-3 / ENG-HENCH-8** — "locks with mutations" named mutations the test
did not carry; every lock now runs on a mutated copy of its function's text and
must go red; the "no 0x0021" check ran against an empty agents table and could
not have seen a destroy — the NPC is seeded now. **ENG-HENCH-3** — the
allegiance: the tape's `'play'` recorded and labelled, the switch deferred with
its reason (above), not made. **HENCH-EVR-4** — the runsheet named
PyCliParty:1228/1238 as the `0x01BF` handler's asserts; those are the
`0x01D2/0x01D3` build window's (`agents.party_build`); `asserts.py --at
0x00858CB0` shows the worker's only assert is Array:587 at `0x00858D10`, in its
agent-dedupe loop. **HENCH-EVR-5/6 / ENG-HENCH-6** — the mark's position and
the level property, moved to retail's; `0x009A` corrected to `0x009F [36]`.
**HENCH-EVR-7** — the set's location and its PtSearch reader. **HENCH-EVR-8** —
retail's 148 has no hireables, recorded. **HENCH-EVR-9/10 / ENG-HENCH-10** — the
cap is a constant, the help text and the log say so, N < 1 refused.
**HENCH-EVR-10 / ENG-HENCH-4** — `hench_assassin`'s provenance quoted the
`0x0056` fifth dword as 0; it is 1 (3486/3487 too), `npc_properties` sends 0,
said as an unmodelled divergence. **HENCH-EVR-11 / ENG-HENCH-11** —
`--party-size-no-heroes` honoured on the wire size, the outpost-only rule
enforced at the spawn. **ENG-HENCH-9** — overrides 159 was stale and 113
unnamed; the leaf's constants locked equal to authsrv's. **HENCH-EVR-13 /
ENG-HENCH-12** — §8.1 trimmed to the pointer and the owed run. **HENCH-EVR-14 /
ENG-HENCH-13** — the three sibling callers, 38 others, PARTY_HENCHMAN_REMOVE
labelled UPSTREAM, the 27-row table, the runsheet's cap step and kick warning.
**Declined**: making the code commit green at its own tree (HENCH-EVR-12 /
ENG-HENCH-7) — the branch merges as one unit and its history is not rewritten;
arming the field carry and re-join (ENG-HENCH-5) — the scope's deferral stands
and the reviewer accepted it; a per-map cap table — a `client-table` content
row per map with its build, its own increment.

**RUN 2026-09-24, harness-driven: steps 1–5 and 7 HELD, step 6 named the kick c2s `0x00A8
[agent]`** (studies/deskwork/CONFIRM-2026-09-24.md §2); the list shows on type-10 map 148 and
`noncombatant` blocks nothing. **At max_party the client does NOT refuse the add itself — it
SENDS it and the server refuses.** OBSERVED twice, `vault/captures/harness/20260924T085818` and
`20260924T205051` (`gamesrv.log`): with the party at 4 of 4 (player + hero + two hired henchmen,
map 148, cap 4) the third click reached the server as `c2s 0x809f HENCHMAN_ADD` and the log
printed `HENCHMAN_ADD(33) refused: the party already holds 4 members … nothing sent (retail's
refusal reply NOT FOUND)`. (This sentence used to say the client refuses it itself, and
CONFIRM-2 §2 step 4 recorded the same; both were wrong — the record is corrected in "The
refusal at the cap", below.)

**The kick — `c2s 0x00A8 HENCHMAN_KICK`, armed as RECONSTRUCTION (the CLEANUP-3 lane,
2026-09-24; `henchparty.py` THE KICK, `handle_henchman_kick`, `--no-henchman-kick`).**
The prediction was written before the client was read (the lane's scratch): the schema's
`0x01C0` is two words; its handler removes a roster row keyed by agent id from the object
`0x01BF` writes; an unknown party or agent returns silently; the reply is row-then-size after
the hero kick; no teardown rows; nothing persisted because the hire is not. All held.

*The request — OBSERVED on our client, read from the sender.* CONFIRM-2 §2 step 6 (run
`20260924T090622`): the Henchmen tab's Kick on the hired Lukas sent `a8 80 1f 00` — one word,
agent 31, the id the `0x009F` add had hired — and the client kept the row. The `0xA8` wrapper
`0x0085BF50` has ONE direct caller (`codescan --xrefs`), `0x0085A84A` inside `0x0085A820`, which
asserts PyCliParty:1650 `m_partyClient`, tests the party-client "is mine" bit `0x80` at
`[this+0x10]` and sends the agent; it removes no row itself — the row stays until a reply, which
is what the screen showed. The UPSTREAM name KICK_NPC is CORROBORATED by the click. 0 of 96 live
connections carry it (c2striage), so its reply is on no tape.

*The reply that removes the row — read from the handler, build 38797.* `msghandler.py 0x01C0
--follow`: handler `0x00856B30` sits in RECV table `0x00bcb788` with `0x01BF`'s (`0x00856B00`)
and `0x01C3`'s (`0x00856BB0`), resolves the same party manager (`[ctx+0x4c]+4`) and calls worker
`0x00858DE0(party = [msg+4], agent = [msg+8])` — the schema's two words, CORROBORATED. The worker
finds the party (id 0 → the own party at `[mgr+0x50]`, else `[mgr+0x3c][id]`; past the count or
null → returns silently), walks the party's stride-`0x34` row array at `[party+0x14]` ×
`[party+0x1c]` — the array `0x01BF`'s worker `0x00858CB0` inserts into (its `[edi+0x14]` /
`[edi+0x1c]`, stride `0x34`) — for a row whose first dword is the agent (no match → returns
silently; the only assert in the loop is Array:587 `index < m_count`, the count re-read each
iteration, unreachable by wire input), then Array:942, a memmove of the tail down one row
(`0x0046DBB0`), `dec [party+0x1c]`, the dirty flag `[party+0x78] = 1` (the flag `0x01C3`'s worker
sets too), and then — unless the party is the manager's `[mgr+0x4c]` one (`cmp esi, [eax+0x4c];
je` at `0x00858EB3`/`B6`, jumping past both calls; `0x01BF`'s worker carries the same guard at
`0x00858D9D`; the review's RV-8) — frame-bus event `0x1000011c` through `0x00633D70` with `{party
or 0 when it is the own party, agent}`, and `0x007DFED0(agent)` — a per-agent refresh called by all four roster workers
(`0x01BF` at `0x00858DC9`, `0x01C0` at `0x00858EDF`, `0x01C2` at `0x0085901A`, `0x01C3` at
`0x0085916E`) that looks the agent up (`0x00802160`) and returns when it is not found. OBSERVED
(the disassembly). The party lookup is `0x01C3`'s worker `0x00859030`'s — the same logic on `esi`
where `0x01C3`'s is on `ecx`, not the same bytes — and that pairing is what makes `0x01C3` the
witness: `0x01BF`'s and `0x01C2`'s workers look the party up through the manager's `[mgr+0x4c]`
FIRST (`mov edi, [esi+0x4c]; cmp [edi], ebx` at `0x00858CC1`–`C8`; `mov edi, [ebx+0x4c]; cmp
[edi], esi` at `0x00858F5E`–`65`) and only then `[mgr+0x50]` / `[mgr+0x3c][id]`, while `0x01C0`'s
and `0x01C3`'s go straight to `[mgr+0x50]` / `[mgr+0x3c][id]` (`0x00858DF0`–`E0A`;
`0x0085904B`–`65`) with no `[mgr+0x4c]` step. Our `0x01C2 [1, …]` add AND `0x01C3 [1, …]` kick are
both CONFIRMED on the client (the hero pair, CONFIRM 2026-09-23), so `[mgr+0x3c][1]` is the object
the first-lookup path used too: the two lookups agree for our id, and party id 1 resolves for
`0x01C0` — CORROBORATED (the review's second round, RV2-5). `schema/overrides.json` now names GAME_CMSG 168
HENCHMAN_KICK and GAME_SMSG 448 PARTY_HENCHMAN_REMOVE, both medium.

*What the server sends — RECONSTRUCTION.* `henchparty.henchman_kick_batch`: `0x01C0 [1, agent]`
THEN `0x00B0 PLAYER_PARTY_SIZE` — row before size, the hero kick's shape (the only kick on any
tape); the add is size-then-row, and no tape decides the henchman kick's order. No `0x0075` /
`0x00F8` / `0x003E` / `0x0145`: those tear down a hero's agent record and container, the
henchman's NPC keeps standing (the add created no body and destroyed none), and a `0x00F8` or
`0x003E` for a standing agent would sweep a body the client draws. The henchman leaves
`state["party_henchmen"]` (the ONE count: with a hero and two henchmen a kick's `0x00B0` says 3,
and the freed slot takes the third henchman), stays hireable, can be re-added. Refused with
nothing sent (`henchparty.kick_refusal`; retail's refusal reply NOT FOUND, as is the request): a
malformed request, an agent that is not a hired henchman of this party — a hireable never hired,
a stranger, a hero's agent, the player's own — and the LAUNCH henchman (`--henchman`), refused with
its own reason: its `0x01BF` row is the load's, not a hire; its count is a launch global and no
`0x0071` marks it hireable, so a kick could neither be counted per connection nor undone by the
panel; not modelled (the review's RV-6). Whether the panel offers a Kick on the launch row at all
is UNVERIFIED: nothing in the sender `0x0085A820` excludes it (after the PyCliParty:1650 assert it
tests only the party's "is mine" bit, `[esi+0x10] & 0x80`, and calls the `0xA8` wrapper with the
agent it was given; one direct caller, `0x00857451`), but no run has clicked one, and the refusal
holds either way (RV2-4). Not persisted: the hire is not (a zone starts a
fresh instance without it — the deferred field carry), so a stored kick would outlive the thing
it kicked. Default ON — the reply is two table operations the client already performs for our
party id and the add's own size message; `--no-henchman-kick` is CONFIRM-2's picture (the word
sent, the row stays). Tests: `test_henchparty.py` §1k, §2 (g)–(l) ((l) the launch henchman's
refusal, the review's RV-6), §4 (four locks, each with a mutation that reddens it; a store write
added is one, the launch guard dropped another), floor 49 → 79 → 82 bare / 97 vaulted (the review
added (l) ×2 and the launch-guard mutation; the figure here said 79 / 94 until RV2-1); each new
check was inverted in a scratch copy and went red (the lane's `redden.py`, the review's
`fixer_redden.py`). **Owed: one client
click** — the runsheet's kick launch (the PLAN-LOG entry): the row leaving the panel, the counter
down one, the NPC still standing, and the re-add.

**Runsheet (owner's hands, one loopback session — not run here).** Each step
names what the log and the screen should show; the questions are pre-registered.
1. Launch the game catalog with the outpost henchmen served, in the outpost, WITH the one-hero party so the cap is reachable:
   `python toolkit/authsrv/authsrv.py --bind 127.0.0.3 --port 6112 --vault vault/captures/gamesrv --map 148 --area outpost_henchmen --party slice` (the other terminals per `RUNBOOK.md`; launch the loopback client). Three henchmen stand near the arrival point (labelled Fighter / Archer / Cutthroat); the gamesrv log prints, for each, `level 3 on hireable agent 31/32/33 (prop 36, before its create)` then `PARTY_HENCHMAN_HIREABLE(agent 31/32/33)` BEFORE its `created agent` line. The party window shows the player and the hero (size 2).
2. **Open the party window's henchmen list.** Expect the three listed, each with level 3 and its profession (W / R / A). **If the list is EMPTY**, the first suspects, in order: the map (retail offers no henchmen on 148, a type-10 map — relaunch on Kamadan, `--map 449 --area outpost_henchmen` needs the rows' `map` widened first) and the allegiance (`noncombatant` here, `'play'` on retail). Either outcome is a result: record it in this section.
3. **Add one** (click a henchman → its add button). Expect the row in the party, the party counter at 3, and the log `HENCHMAN_ADD: <label> (agent 31) joined the party; size now 3`. A row that does not appear with no `HENCHMAN_ADD` line means no c2s reached us (the client refused the click itself — the allegiance is then the suspect).
4. **Add a second.** Size 4 = the cap (player + hero + 2). **Add the third** → refused: the log prints `HENCHMAN_ADD(33) refused: the party already holds 4 members (heroes and henchmen), the served cap (OUTPOST_PARTY_CAP=4 ...)`, nothing is sent, the window does not change. (Retail's reply to a refused add is NOT FOUND. **RAN 2026-09-24, twice: the client's panel does NOT grey the add at max_party — the click SENDS `0x009F` and the server refuses it**, `20260924T085818` and `20260924T205051`; the player sees nothing and the button stays live. "The refusal at the cap", below, is what was searched for the reply and the opt-in `--party-full-reply CODE` that gives one.)
5. **The hero and the count** (the fix pass's blocker on screen): kick the hero (the party panel's X on its row). Expect the counter at 3 and `HERO_KICK: ... size now 3` — the landing would have said 1. Re-add the hero (Party Search → the hero): 3 < 4, so it goes THROUGH — counter 4, `HERO_ADD: ... size now 4`. Kick the hero again (counter 3), add the third henchman (counter 4), then re-add the hero → REFUSED at the cap: `HERO_ADD(3) refused: the party already holds 4 members (heroes and henchmen), the served cap`, nothing sent, the counter stays 4.
6. **Do NOT click the X on a hired henchman's row** as part of this run: the henchman kick is not armed; its c2s (`0xA8` by the UPSTREAM reading, unwitnessed) lands in the connection's unhandled census at the end of the log — if you do click it, copy that census line, it names the opcode and closes the KICK question for the next step.
7. **Control:** relaunch with `--no-henchman-add` (same flags otherwise). The henchmen do not appear in the party window's list (no `0x0071`, no level line in the log), and a click, if the panel offers one, prints `HENCHMAN_ADD ignored (--no-henchman-add)`.
8. **Walk into the explorable** (through the town portal): the henchmen do NOT follow (the field carry is deferred, above) — the expected incomplete state; the run confirms the outpost add itself. If the client ASSERTS on any add, copy the dialog's `File.cpp(N)`: the `0x01BF` worker's only assert is Array:587 (`index < m_count`) at `0x00858D10`, inside its agent-dedupe loop, which wire input cannot reach, and an unknown party id returns silently — so any assert here is new information, not a known branch.

**The refusal at the cap — what retail sends back is NOT FOUND; the carrier the client holds; `--party-full-reply CODE`, opt-in (desk-partyfull, 2026-09-25).**
The question: on our server a party at its map's cap (map 148, `max_party` 4 by `areatable.py`, `OUTPOST_PARTY_CAP = 4`) still receives the player's Add Henchman click — **OBSERVED twice, `20260924T085818` and `20260924T205051`: `c2s 0x809f HENCHMAN_ADD` at 4 of 4, then `HENCHMAN_ADD(33) refused … nothing sent`** — and the refusal is silent: no feedback, the button stays live. What does retail's server send when it refuses an add because the party is full? The prediction was written before a tape was decoded (the lane's scratch `prediction.md`): no tape carries a refused add (P1); the `0x9F` sender checks no size before sending, and any "party is full" text is a server-sent string id on the refusal channel, outside 1934–1993 (P2); UPSTREAM names nothing (P3). P1 and P3 held; P2 held on the sender and was WRONG on the text — the sentence is a client-side const text and the server-side mechanism is a code byte, not a string id.

*The tapes — NOT FOUND, bounded.* Over the 35 LIVE captures / 96 game connections (`c2striage.py` re-run 2026-09-25: 13,320 c2s, 57 opcodes, `connections_not_ok` 0): retail's client sent `0x009F` **3 times on one connection** (`:53419`, the adds above) and **never** `0x001E` HERO_ADD, `0x00A0`/`0x00A1` (the player invites), or anything else in `0x98–0xAF`. The own party reached its map's cap **exactly once** — `:53419`, player 14, `0x00B0` 1 → 2 → 3 → 4 by those three adds (map 242, `max_party` 4) — and **nothing was attempted past it** (0 c2s of any party opcode after the third reply; the scan is per player number, `0x00B0` being `[word player, byte size]`). Forty-four other connections show SOME player's `0x00B0` at the map's cap (towns broadcast every party's size) with no own-party request on any of them. Retail's server-composed lines: every `0x005D`/`0x005E` on the corpus, keyed by the body's first coded id and the channel, is **44 distinct keys** (1737 ×34, 1960 ×20, 1961 ×17, 73531 ×16, …), and **none is a party-block id** — not 2582–2624, not 51802/51803, not 57757/57759/57807, not 93729. And the four one-byte party error carriers below are **on no tape at all** (`0x01B4`/`0x01B6`/`0x01B8`/`0x01BC`/`0x01D6`/`0x01E3`/`0x01E5`/`0x01E6`: 0 of 96 connections). So the reply is NOT FOUND in every form the wire could carry it.

*The client, build 38797 — the mechanism, OBSERVED from the binary and CONFIRMED on our client for one row.* The `0x9F` sender `0x00858410` (and its `0xA0`/`0xA1` siblings) tests only the party's "is mine" bit and sends — **no size compare**; its thunk `0x00856670` has three UI callers (`0x00562F60` in PtSearch beside the `m_activeList == LIST_HEROES` assert, `0x0056427A` in PtFrame — "henchman if the agent is not a player, else `0xA0`", `0x0056BA86`), none of which compares a party size in the 30 instructions before the call. Four one-byte s2c messages in the party RECV table `0x00bcb788` — **`0x01B8` → `0x00856A10` → worker `0x00858A80`, `0x01BC` → `0x00856AA0` → `0x00858C00`, `0x01D6` → `0x00856E70` → `0x0085A240`, `0x01E3` → `0x00857380` → `0x0085A380`** — each hand their byte to ONE function, **`0x00858300`**: `mov esi, [eax*4 + 0x00B97968]` indexes a dword table of **81 string ids (rows 0..80)** — the lane wrote 82 / 0..81 and the review of 2026-09-25 (RV-1) corrected it from two witnesses, both re-read from the bytes by the fixer: `0x00B97AAC`, 81 rows past the base, is row 0 of the NEXT table, which `0x01E5`/`0x01E6`'s workers `0x0085A400`/`0x0085A740` read zero-based as `mov esi, [eax*4 + 0x00B97AAC]`; and **81 = `0x51` is the client's own "no error, send" sentinel** — the `0x98` sender computes `and esi, 0x19; add esi, 0x38` (a party of its own → 81, else row 56) and `cmp esi, 0x51; je <send>` at `0x00857B4E`, the send followed by `or [edi+0x10], 1`, with the same compare at `0x0085A93C` / `0x0085AAF6` / `0x0085AB84`; so a byte of 81 would show the next table's row 0 — a placeholder id (100298) falls back to row 43's, rows 47/48/69/71 take number/string arguments, and the sentence is composed through `0x007C93F0`/`0x007C9410`. **`0x00858300` composes the row and returns it; it posts nothing** (its four `ret`s at `0x00858354`/`77`/`83`/`A6`, no call to `0x0082CE20` — the review's RV-2; the lane had the shower posting). The `0x01B8`/`0x01BC`/`0x01D6` workers then post it on chat channel 10 (`push 0xa; call 0x0082CE20`) and fire a frame-bus event (`0x10000117` / `0x10000119` / `0x1000012C`); **`0x01E3`'s worker `0x0085A380` fires `0x1000013A` with `{code, 8, text}` and posts no chat line.** Three of the four first CLEAR a request-in-flight bit of `[party+0x10]` — `0x01B8` bit 0 (the bit the `0x98`/`0x99` senders set at `0x00857B91`/`0x00857C31`, right after their wrapper calls; GWCA's `PARTY_ACCEPT_INVITE`/`PARTY_ACCEPT_CANCEL`), `0x01D6` bit 1 (set at `0x0085A80B`), `0x01E3` bit 2 (set by the `0xA5`/`0xA6`/`0xA7`/`0xAA` senders) — so each is the error reply to a request that set its bit; **`0x01BC` clears nothing and is the free-standing party error prompt.** The same shower serves the client's LOCAL pre-checks: the `0x98`/`0x99` senders compute a row (56 "must be the leader", 57 "must be in a party", 43) and show it through `0x00858300` with the same event `0x10000119` before deciding whether to send. **This path is CONFIRMED on our own client**: the 2026-08-13 smsgsweep sent each of `0x01B8`/`0x01BC`/`0x01D6` with byte 0 and the operator read the table's row-0 sentence on screen (`0x01BC` with a centre-screen popup as well), and `0x01E6` with byte 0 showed row 0 of the second table (`0x00B97AAC`, **8 rows, 0..7** — the ids end at `0x00B97AC8` and the workers' own placeholder-assert file string sits at `0x00B97ACC`, passed with line 200 at `0x0085A42C`/`0x0085A761`; the yes/no travel prompts, read by `0x01E5`/`0x01E6`'s workers `0x0085A400`/`0x0085A740`; the review's RV-6b — the lane's report had said 20 rows). `schema/overrides.json` 440/444/470/486 name those four **after the row-0 sentences** (`ACCOUNT_UNNAMED_NOTICE` / `_PROMPT` / `_NOTICE_ALT`, `MISSION_ENTRY_CONFIRM`) — a naming of the byte-0 case, not of the carrier; the carrier is "party error, code byte → row" (proposed rename in the lane's report; not changed here). **The table has NO row that says the party is full.** Its party rows (ids only; the sentences resolve at run time from the owner's archive, `textrec.py`): 37 → #2595, the henchman already in your party (the exact sentence for our "already in the party" refusal); 44 → #2600; 49 → #2603; 53 → #2607; 56/57 → #2610/#2611; 62 → #57807; **64 → #2616, the merged party would be too large; 66 → #2617; 69 → #57809 (templated, a number of heroes/henchmen); 78/79 → #89154/#89155, no more than 4/2 henchmen.** The sentence a player would expect — **#57757, "You cannot add %str1% because your party is full."** (templated on the name; #57759 beside it, "%str1% is already in your party.") — is **NOT in that table and NOT a server-sent string: it is row 267 of a 4,962-row CLIENT const-text table** (base `0x00BB19B8`, the `Const*` getter at `0x008EDF89` returns `count 0x1362, base`; #57757 has exactly one dword occurrence in the image and it is that row, between the skills window's view labels). So retail's client CAN refuse an add locally with the name in the sentence, and if it does, its server never sees the click and sends nothing — which would make today's silent server-side refusal faithful, and the defect the missing CLIENT-side gate. **Why our client sent instead is UNVERIFIED**: the const-text user could not be isolated statically (an imm32 scan for index 267 is swamped by the assert idiom's line numbers), and no run has shown #57757 on screen. Both readings stay open; neither is a tape.

*UPSTREAM.* GWCA names our `0x01BC` `GAME_SMSG_INSTANCE_CANT_ENTER` (no packet struct): the gwdevhub copy (`GWToolboxpp/Dependencies/GWCA`, `Opcodes.h:193`) numbers it `0x01BC` as we do, with `PARTY_HENCHMAN_ADD` at `0x01BF`; the GregLando113 and JaborGW forks (`Opcodes.h:291` / `:193`) run one below in this range — `0x01BB`, their `0x01BE` HENCHMAN_ADD our `0x01BF` (the review's RV-5; the lane had written "both mirrors, one below"). Py4GW_Reforged's `opcodes.h:195` also says `0x01BC`, a no-grant upstream and so verification only. The name agrees across all four; none names our `0x01B8`/`0x01D6`/`0x01E3`. OpenTyria names the c2s (`GAME_CMSG_PARTY_INVITE_NPC` = `0x009F`, our numbering) and has no handler for it (`GmParty.c`'s henchman loop is commented out); Headquarter names nothing party-full. A reference, not a witness.

*Decision — RECONSTRUCTION, DEFAULT OFF.* Nothing OBSERVED supports a reply, so nothing ships enabled. What ships is `--party-full-reply CODE` (opt-in; `henchparty.party_full_reply`, `authsrv.PARTY_FULL_REPLY_CODE`, `party_full_refusal_note`): an add refused at the cap — henchman `0x009F` and hero `0x001E`, the same branch in both handlers — is answered with **ONE `0x01BC [CODE]`** (3 bytes, `bc 01 <code>` through the codec), the carrier that clears no bit, whose row the operator picks from the table above (64 and 78 are the nearest sentences; the flag's help names both); the leaf refuses a CODE outside 0..80 at launch (81, the client's own no-error sentinel, would show the next table's row 0 — the lane's max of 81 let exactly that byte through; the review's RV-1). The default sends nothing — today's silent refusal, which is also what retail's server does if its client gates locally. The other two refusals ("not hireable", "already in the party") stay silent under the flag; row 37 is the exact sentence for the second and is recorded here, not armed. Tests: `test_henchparty.py` (m) — the reply's bytes, the off arm, six bad codes (81 first), both handlers ARMED (exactly one `0x01BC [64]`, nothing added, the hero stays kicked), the refusal line naming the follow-up and RECONSTRUCTION, the two other refusals silent when armed, the VACUITY GUARD (armed + `--henchman-cap 8`: the henchman add goes through with no `0x01BC`) and its HERO half (the review's RV-3 — armed, the kicked hero re-added into a party BELOW the cap, 3 of 4, goes through as `0x00B0` = 4 + `0x01C2` with no `0x01BC`; vaulted, a bare machine declares the skip — a `0x01BC` sent after a successful hero add had survived every other check), the OFF arm; §4 locks on both handlers' cap branches (the reply once, after the cap check, with the note; mutations: dropped, moved ahead of the check, the note replaced), on `main()`'s wiring (assignment and validation dropped) and on `serverargs.py`'s declaration; floor 82 → **108 bare / 124 vaulted** (107 / 122 at the lane's commit; +1 bare for code 81 and +1 vaulted for the hero half at the review). Every new check was inverted in a scratch COPY (the lane's `redden.py`: nine inversions — the leaf returning nothing, the handlers' sends and notes removed, the reply moved ahead of the cap check, the reply sent at the top of the handler, `None` sending a row with the range check dropped, the module default flipped on, the table's max renumbered, the test copy's own lock made vacuous, the flag undeclared and unwired) and each went red under at least one; the review's two fixes the same way (the fixer's `fix_redden.py`, a scratch COPY again: the max back at 81 reddens the 81-refused check, the five range-named checks and the module lock (7, bare — row 80 is still served, so the ends check needs the table one row SHORT, max 79, which reddens those 7 and the ends check, 8); the reviewer's own mutation — a `0x01BC` sent after the hero add's bare batch — reddens the hero half, vaulted, and nothing else, which is the gap RV-3 named).

**Runsheet (owner's hands, one loopback session — not run here; the questions are pre-registered).**
1. Launch as the party-family runsheet's step 1 with the flag: `python toolkit/authsrv/authsrv.py --bind 127.0.0.3 --port 6112 --vault vault/captures/gamesrv --map 148 --area outpost_henchmen --party slice --party-full-reply 64`. Expect the launch line `[party] --party-full-reply 64: an add refused at the cap … is answered with 0x01BC PARTY_ERROR_PROMPT [code 64]`.
2. Add two henchmen (size 4 = the cap), then click the third. Expect the log's `HENCHMAN_ADD(33) refused … 0x01BC PARTY_ERROR_PROMPT [code 64] follows (--party-full-reply; RECONSTRUCTION …)` and, on screen, **the row-64 sentence (the merged party being too large) in chat and as a centre-screen popup** — the shape the 2026-08-13 sweep saw for row 0. Record: did the popup appear; did the chat line appear; did the panel change in any way (it should not); did anything assert. A missing popup with the chat line present says the popup is the sweep's byte-0 row's, not the carrier's.
3. Kick the hero (size 3), add the third henchman (size 4), re-add the hero from Party Search → the same `0x01BC` from `HERO_ADD(3) refused … follows`. Record the screen as in 2.
4. Relaunch with `--party-full-reply 78` and repeat 2: the row that says no more than 4 henchmen. Record which of the two sentences reads better for a 4-cap outpost; that is the operator's choice the flag exists for — neither is retail's.
5. Control: relaunch WITHOUT the flag and repeat 2: `… nothing sent (retail's refusal reply NOT FOUND)`, no chat line, no popup — CONFIRM-2's picture.
6. The open client question, if the owner is in a live session on the secondary account under the standing rules: with a party at an outpost's cap, hover and click a henchman's Add once — is the button greyed, does a sentence appear WITHOUT a server round-trip (#57757 with the henchman's name would be the client-side text), or does the party grow? One click, no repetition; the capture will show whether `0x009F` left the client at all. That single observation would settle which side of the wire the refusal lives on.
