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
