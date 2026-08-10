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
