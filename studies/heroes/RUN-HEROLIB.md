# RUN-HEROLIB — does the client address a HERO when editing a build?

**Registered 2026-09-15 20:xx, BEFORE the client was launched.** Everything in
§1–§4 was written first; §5 is filled in afterwards and nothing above it is
edited once the run starts. The rule this follows is `toolkit/authsrv/probes.py`'s
— a probe with no stated expectation can be rationalised into agreeing with
anything afterwards.

## 1. The question, and why only a run can answer it

[FINDINGS §40](FINDINGS.md) shipped the hero skill library, hero bars and hero
attributes on the strength of the corpus and the disassembly. One thing it could
not settle, and said so: **every client-to-server path in that family has ZERO
corpus exposure.** All 32 attribute messages and both `0x005C` bar edits in the
live corpus name the **player**. The operator on those tapes used heroes for AI
mode, lock-target and flags, and never opened a hero's build panel to change it.

So "a retail client sends `0x005C` for a hero" is an inference from the message
being agent-keyed, not an observation. This run is the cheapest thing that can
turn it into one.

**One thing is already known and is NOT the question.** On the retail tape
(`studies/slice/FINDINGS.md` SLICE-F39) the operator *opened* the hero panel and
the client sent nothing beyond its town keepalive cadence. **Opening is silent.**
The question is about **editing**.

## 2. The rig

| | |
|---|---|
| Build | `vault/run/slice/Gw.exe` — ours, loopback-only (`dhbuild.py`: `ours`) |
| Server | `--party slice --persist`, `--unlocks corpus` (1,333 account unlocks) |
| Hero | index 3, academy monk body, agent **200**, commander rig ON |
| Player | agent 1, level 3, bar `[382, 384, 385, 322, 346, 1, 2, 380]` |

**The hero is authored to retail's own observed shape**, in the store rather than
in content: ranks `[[13, 2], [16, 1]]` costing 3 + 1 = **4** of a **10**-point
budget, leaving **6 unspent** — the exact arithmetic capture `20260914T005758`
shows for a level-3 Koss. The slice party row spends all ten, which would grey
out the `+` buttons and make the attribute half of this run unanswerable. Its bar
is `[281, 276, 2, 0, 0, 0, 0, 0]`, so **five slots are empty** to drag into.

The stored player row was made coherent with the slice rig first: its level-7
ranks (9/1/11) cost 126 points against slice's 10-point budget and would have put
`0x0037 [player, −116, 10]` on the wire. `attributes` emptied (falls back to the
content ranks), `level` 3. Titles, factions and xp untouched. Backup taken.

## 3. Predictions, registered

| id | prediction |
|---|---|
| **P1** | A drag into a hero bar slot sends c2s **`0x005C [200, slot, skill, 0]`** — the hero's agent, not the player's. |
| **P2** | A click on a hero attribute `+` sends c2s **`0x000F [200, seq, attribute]`**. |
| **P3** | Merely opening the panel sends **nothing** beyond `0x0009` keepalives — reproducing on our server what the retail tape already showed. |
| **P4** | Our answers land with **zero assertions**: `0x00D9` echoes the slot, the attribute triple retires the prediction, and the panel visibly updates. |

**What would REFUTE each, stated so the run cannot be talked into agreeing.**

* **P1 refuted** if the drag sends nothing at all (the client edits a hero's bar
  purely locally and syncs by some other route), or sends a different opcode, or
  sends `0x005C` naming the **player's** agent 1 while the hero's bar changes.
* **P2 refuted** the same three ways. A named rival worth watching: the client may
  send **`0x0010 ATTRIBUTE_LOAD`** (the whole spread at once) instead of per-point
  `0x000F`. pvpui §32.7 established `0x0010` is a template apply that is
  send-only with no local prediction — if a hero's panel uses that path, our
  per-point handler is the wrong shape for heroes and that is a real finding.
* **P4 refuted** by any assert dialog, or by the panel reverting the change.

## 4. Exposure floor, and the abort — registered BEFORE the run

Zero exposure is not a null. This run answers its question only if the operator
actually performs the edits, so the floor is stated first:

| | requirement |
|---|---|
| **E1** | The hero's build panel OPENS, showing its bar and its attributes. |
| **E2** | **≥ 1** skill actually dragged into a hero bar slot. |
| **E3** | **≥ 1** click on a hero attribute `+`. |

* **E1 fails → the run is ABORTED and scored as nothing.** Not as "the client
  does not send it". The commander-slot click has crashed this client before
  (FINDINGS §15.3) and was only made to work by ordering (§38); if the panel will
  not open, that is a fact about our rig, not about the question.
* **E2 or E3 unmet → that half is VOID**, and only the half that was exercised is
  scored.

## 5. Result — BOTH PREDICTIONS CONFIRMED, and the first attempt crashed the client

Two runs. The first crashed on a defect of ours and is the more instructive of
the pair; the second answered the question.

### 5.1 Run 1 — `20260915T201538` — CRASHED, and it found a real server defect

The operator opened Tahlkora's panel, found **only three skills listed**, and
dragged Restore Condition (276) into an empty slot. The client died:

```
Assertion: unlockedSkills->BitTest(sourceSkillId)
P:\Code\Gw\Ui\Game\GmSkSlot.cpp(206)
Build: 38797   When: 9/15/2026 20:18:16
```

That is exactly the equip validator §40.3 named, firing on an **empty account
container** — and the container was empty because of us. Two sites send
`0x001D`, and the server log has them in this order:

| log line | what went out |
|---|---|
| 151 | `PVP_UPDATE_UNLOCKED_SKILLS(corpus, 1333 bits)` — the instance-load burst |
| 187 | `PVP_UNLOCKED_SKILLS` — **`[[0] * 128]`**, from the `CHAR_CREATION_REQUEST_ARMORS` arm |

The zeroed send fires **after** the real one, so the last word the client heard
on its account library was "nothing is unlocked". **One bug, both symptoms:**
the panel listed only the hero's own three skills because the account half of
the union was gone, and the drag asserted because `BitTest(276)` was false.

The zeros had been there for weeks behind a comment calling them *"correct for a
level 1 character"*. They were written before anything was known to read that
container; §40.3 is what made them load-bearing.

**And the capture holds NO `0x005C` at all** — 0 in 37 decoded c2s messages. So
**the client validates an equip locally and asserts rather than sending.** An
empty account library does not produce a refused drag with a diagnosable wire
trail; it produces a crash with no wire evidence whatsoever. Worth knowing for
any future server that under-populates it.

A second defect, found in the same log before the operator was asked to click:
`hero_build` read `state["charstore_game"]` at a point in the load where it was
still `None` (log line 142 builds the hero block, line 144 opens the store), so
every hero send fell back to the party row. The hero went out with `0 of 10`
points — no unspent points, dead `+` buttons — and the attribute half could not
have been exposed at all.

Both fixed: one source for the account bitmap (`resolve_library`, the same call
the load burst makes), and an order-independent store lookup in `hero_build`.
`test_agentlife` gains a source-level guard that no `0x001D` site may build its
payload from a literal; restoring the old shape reddens it, naming the line.

### 5.2 Run 2 — `20260915T202552` — the rig verified first, then the answer

Verified on the wire **before** the operator was asked to touch anything:

| | run 1 | run 2 |
|---|---|---|
| account library | wiped to zeros after the load | 1,333 unlocks, no zeroed send remains |
| hero attribute points | `0 of 10` | **`6 of 10`** |
| hero attributes | 3, from the party row | **2, from the store** |

Then one drag and one `+` click. **No crash.**

**CORRECTION TO THIS SECTION'S FIRST DRAFT.** It was scored while the run was
still live and reported one drag and one click. The operator kept going, and the
full run carries **twelve** build-editing messages. The counts below are the
complete ones, re-scored from both connections after teardown. Scoring a live
capture is the same defect as a partial suite run reported as a full one.

**P1 CONFIRMED, n = 7.** Every `0x005C` in the run names **agent 200, the hero**:

| # | message | what it did |
|---|---|---|
| 1 | `[200, 3, 284, 0]` | slot 3 ← 284 |
| 2 | `[200, 4, 279, 0]` | slot 4 ← 279 |
| 3 | `[200, 5, 991, 0]` | slot 5 ← 991 |
| 4 | `[200, 4, 0, 0]` | **slot 4 CLEARED** |
| 5 | `[200, 6, 279, 0]` | slot 6 ← 279 |
| 6 | `[200, 7, 310, 0]` | slot 7 ← 310 |
| 7 | `[200, 4, 1685, 0]` | slot 4 ← 1685 |

**Zero refusals.** Every id was inside the hero's library and every slot inside
0..7, so `herolib.refuse_bar_slot` never fired — which is the outcome wanted,
the library having been correct this time.

**Two things this run answers that were not among the predictions.**

* **A skill id of 0 CLEARS a slot, on the wire, from the client.** Message 4 is
  the operator dragging a skill off the bar. `refuse_bar_slot` already treated 0
  as always-legal on the strength of retail's own bars carrying an empty slot in
  the middle; here the client *sends* one, unprompted. OBSERVED.
* **A MOVE is a CLEAR followed by a SET — two messages, and the server never
  sees a duplicate.** Messages 2, 4 and 5 are one gesture: 279 goes into slot 4,
  then slot 4 is cleared, then 279 lands in slot 6. This is most of
  [FINDINGS §40.6](FINDINGS.md)'s duplicate-drag item: the client does not ask
  the server to hold one skill in two slots and does not ask for a swap. It
  decomposes the move itself. What is still unseen is a drag onto an *occupied*
  slot.

**P2 CONFIRMED, n = 5, and BOTH DIRECTIONS.** `0x000F` ×2 and `0x000E` ×3, every
one `[200, 0, 13]` — the hero's agent, sequence 0, Healing Prayers. The named
rival did **not** fire: no `0x0010` template apply anywhere in the run. Our
server answered each with the full triple pvpui §32 specified (`0x0036` ack,
`0x0038` points, `0x003B` attribute) and persisted each.

**The refund arithmetic closes in BOTH directions against the client's own cost
table** — the strongest single result of the run, because a refund that priced
the wrong rank would drift immediately and visibly:

| # | change | cost/refund | unspent after |
|---|---|---|---|
| 1 | raise 2 → 3 | −3 | 3 of 10 |
| 2 | lower 3 → 2 | +3 | 6 of 10 |
| 3 | lower 2 → 1 | +2 | 8 of 10 |
| 4 | lower 1 → 0 | +1 | 9 of 10 |
| 5 | raise 0 → 1 | −1 | 8 of 10 |

Every step is `s_attribPoints[rank]` exactly, and the balance returns to its
start. A refund priced on the rank being *left* rather than the rank being
*reached* would have shown up at step 2.

**The budget arithmetic closes on the client's own cost table, with no free
parameter.** Before: ranks 2 and 1, costing 3 + 1 = 4 of 10, so 6 available.
Raising rank 2 → 3 costs 3. After: 6 + 1 = 7 spent, **3 available** — and the
server's own line reads `3 of 10 point(s) unspent`. A hero's points are spent by
the same rule as a player's, now measured on our own wire rather than inferred
from one retail frame.

**P3 CONFIRMED**, weakly and by construction: the whole c2s census for the run
is 42 messages, 26 of them `0x0009` keepalives, plus the two edits and the load
handshake. Nothing is attributable to opening the panel, which reproduces what
the retail tape already showed.

**P4 CONFIRMED.** Zero assertions across all twelve edits, every one accepted on
screen, every one persisted.

**THE HARNESS SCORED THIS RUN `FAIL`, AND THAT IS NOT A CONTRADICTION — but it
is recorded rather than explained away.** Its rule is that a client which dies
during the hold retracts the verdict, and the operator closed the client while
the hold still had ~420 s to run. The harness's own teardown lines say what
happened:

```
client exited with code 0 during the hold
no error dialog within 12s -- the client exited WITHOUT one, which is a clean
exit rather than a silent crash
RUN VERDICT RETRACTED: the run passed its checkpoints, then the client died
during the hold.
```

Exit code 0, no dialog, and every edit is in the capture **before** the close.
The retraction is a conservative default doing its job; it is not evidence
against the twelve messages. Worth noting for the next run: a hold long enough
that the operator closes the client inside it will always read `FAIL`.

### 5.3 What the run settles, and what it does not

**Settled.** The c2s hero paths are no longer an inference. `0x005C` and
`0x000F` both carry the hero's agent id, our handlers answer them correctly, and
both halves write through to the store. FINDINGS §40.6's first two open items
are closed.

**Not settled by this run.**

* **This is OUR client talking to OUR server.** It is a real retail binary
  (38797, pinned pristine) driven through a real UI, which is why it is worth
  more than the desk work — but the live corpus still holds no retail-server
  instance of either message, and the exact *field* semantics beyond
  `[agent, slot, skill]` and `[agent, seq, attribute]` rest on the echo joins,
  not on ArenaNet's own answers.
* **The duplicate-drag swap is MOSTLY answered, and not by a prediction.** A
  move is a clear plus a set (§5.2), so the server never sees one skill in two
  slots and is never asked to swap. What remains unseen is a drag onto an
  **occupied** slot — every set in this run landed on an empty one.
* **`0x005C`'s fourth field is still 0 in every sighting**, ours and retail's.
* **One trailing unknown, unchanged:** `0x800d` is still unhandled, and `0x005C`
  prints as `0x805c ?` because the catalog carries no name for it — the name is
  ours, from the echo.

---

## 6. RUN-HEROLIB-B — the drag onto an OCCUPIED slot

**Registered 2026-09-15 ~20:5x, BEFORE the client was launched.** §5 answered
the empty-slot case and, unexpectedly, the move case. It left exactly one hole,
and this run is aimed at it.

### 6.1 The question

Every set in run 2 landed on an **empty** slot, and the one move the operator
made was decomposed by the client into a clear plus a set. So the server was
never asked to put a skill where one already sat. Two distinct gestures remain
unseen:

* **B1 — from the PICKER onto an occupied slot.** Replace.
* **B2 — from one occupied slot onto ANOTHER occupied slot.** Swap.

### 6.2 The rig

Same as §2, with the hero's bar seeded **fully occupied**:
`[281, 276, 2, 284, 991, 279, 310, 1685]`. Every id is one the operator's own
drags already carried last run, so none can be refused for library reasons and
confound the readout.

### 6.3 Predictions, registered

| id | prediction |
|---|---|
| **B1** | ONE `0x005C [200, slot, newSkill, 0]`. The displaced skill is simply overwritten and gets no message of its own. |
| **B2** | TWO `0x005C`, one per slot, carrying the exchanged ids — the swap done the same way the move was, by the client decomposing it. |
| **B3** | No new opcode. In particular **`0x005E`** stays absent. |

**The named rival, and it is a real one.** `0x005E` is UPSTREAM-named
`SKILLBAR_SKILL_REPLACE` and has **zero** occurrences in the entire live corpus.
A swap is exactly the gesture such an opcode would exist for. If B2 produces a
`0x005E` instead of two `0x005C`, the upstream name is corroborated by its first
observation and our handler is the wrong shape for swaps. That is the outcome
worth most, and it is the one being watched for.

A second rival for B2: the client may send **clear, set, set** (three messages)
rather than two, reusing the decomposition §5.2 found. Distinguishable by count
and by whether any message carries skill id 0.

**What would refute.** B1 refuted by anything other than a single replace —
including a clear-then-set pair, which would mean the client never overwrites in
place. B3 refuted by any opcode not already in the `0x005C` family.

### 6.4 Exposure floor, and the abort

| | requirement |
|---|---|
| **F1** | **≥ 1** drag from the picker onto an **occupied** slot. |
| **F2** | **≥ 1** drag from one **occupied** slot onto another **occupied** slot. |

Either half alone is scorable; the other is then **VOID**, not a null. Both
unmet means the run is aborted and answers nothing.

**Scored from the WIRE, after teardown.** §5's first scoring was taken live and
under-reported the run six-fold; this one is read only once the client is gone.
The wire is also the right instrument for another reason recorded in §6.5: the
store is currently losing edits, and the capture is immune to that.

### 6.5 A defect this run does NOT fix, recorded before it starts

**Run 2's twelve edits did not survive to the next connection.** The store was
verified mid-run holding the edited bar and ranks; by the time connection c2
opened at 20:34:09 the file held the **seeded** values again, and c2's hero
block went out with them. One login, one roster save (at 20:26, before the
edits), no kill accrual — so the auth-side writer is ruled out, and the game
process is the only candidate left. **The culprit is not identified**, and
guessing at it is how the last two sessions of this arc lost time. It needs its
own instrument: a save-site trace that prints path and mtime on every write.

It does not affect this run's question, which is answered from the wire.

## 7. Result — RUN-HEROLIB-B: **B1 confirmed, B2 and B3 REFUTED, and `0x005E` exists**

Capture `authsrv-20260915T204806-c1.jsonl`, scored after teardown. Bar seeded
fully occupied and verified on the wire before the operator touched anything:
`SKILLBAR_UPDATE(hero agent 200)[281, 276, 2, 284, 991, 279, 310, 1685]`.

Two gestures: a drag from the picker onto occupied slot 1, then a drag of slot 1
onto slot 2. **Both exposure conditions met.** Both messages name agent 200.

### 7.1 B1 CONFIRMED — a replace is ONE `0x005C`

```
0x005C [200, 1, 256, 0]     slot 1: 276 -> 256
```

One message. The displaced skill (276) gets **no message of its own** — it is
simply overwritten, exactly as predicted. Our handler wrote it and echoed
`0x00D9`.

### 7.2 B2 and B3 REFUTED — a SWAP is a single `0x005E`, and this is its FIRST OBSERVATION ANYWHERE

The prediction was two `0x005C`. It is not:

```
0x005E [200, 2, 0, 256, 0]
```

**`0x005E` has ZERO occurrences in the entire live corpus** and this repo had
never sent or received one. The registered rival was that a swap would be
exactly the gesture such an opcode exists for. **It is**, and the upstream name
`SKILLBAR_SKILL_REPLACE` is corroborated by its first sighting.

B3 — "no new opcode, `0x005E` stays absent" — is refuted by the same message.
Registering it as a named rival is what makes this a result rather than a
surprise.

**Our server has NO ARM for it.** The log reads
`UNHANDLED GAME_CMSG 0x805e ? -- schema knows it, this server has no arm for it`.
So the client swapped locally, the server did nothing, and **the two now
disagree about that hero's bar** — the client-predicts/server-confirms split
with the confirm missing. A live divergence, recorded rather than quietly left.

### 7.3 The field reading is CONFOUNDED, and the confound is named rather than resolved

Declared shape is `[agent_id, dword ×4]`, 22 B. Observed: `[200, 2, 0, 256, 0]`.

The gesture was slot index **1** (holding skill 256) dragged onto slot index
**2** (holding skill **2**). So the literal `2` in field 1 is **both** the target
slot index and the target skill id, and the two readings cannot be separated on
this sample:

| reading | field 1 | field 2 | field 3 | field 4 |
|---|---|---|---|---|
| (a) slot-keyed | target **slot** 2 | 0 | source skill 256 | 0 |
| (b) skill-keyed | target **skill** 2 | target copy 0 | source skill 256 | source copy 0 |

**(b) is the better-supported one, and not because it looks neater.** The
client's own guards on this store are named `targetSkill != sourceSkill`
(`ChCliSkill.cpp:515`) and `sourceSkillCopy >= 0` (`:516`), and a slot entry
holds `skillId` at `+0x0C` beside `skillCopy` at `+0x10` (pvpui §30.2). A
four-field payload of *(targetSkill, targetCopy, sourceSkill, sourceCopy)* is
precisely the shape those two asserts describe, and it explains both zeros.

**It is still not settled, and no handler is being written on it.** Building a
swap arm on a reading that one unlucky coincidence could have inverted is how
this arc lost two evenings already.

**The disambiguating run is one drag.** Swap two slots where the target slot
index differs from the target skill id — e.g. drag any slot onto slot 4
(holding 991) or slot 7 (holding 1685). Reading (a) puts the slot index in field
1, reading (b) puts 991 or 1685 there. One message separates them with no free
parameter.

### 7.4 What this does to §40.6's duplicate-drag item

It is now **fully answered**, and in two different ways depending on the gesture:

* **Move to an EMPTY slot** — the client decomposes it into a clear plus a set,
  two `0x005C` (§5.2).
* **Replace an OCCUPIED slot from the picker** — one `0x005C`, the occupant
  overwritten silently (§7.1).
* **Swap two OCCUPIED slots** — one `0x005E` (§7.2).

So the server is never asked to hold one skill in two slots, in any of the three
gestures. `herolib.duplicate_of` remains a diagnostic with no case to model —
but `0x005E` is a real gap in the server, and it is the arc's next item.

---

## 8. RUN-HEROLIB-C — the one drag that separates the two readings

**Registered before launch.** §7.3 left `0x005E`'s field 1 confounded. This
run's fixture is built so the confound cannot recur.

### 8.1 Half of it is already decided, and saying so sharpens the prediction

Run B's sample was `0x005E [200, 2, 0, 256, 0]`, from dragging slot **1**
(holding skill **256**) onto slot **2** (holding skill **2**).

**Field 3 is 256 while the source SLOT was 1.** Those differ, so field 3 is
unambiguously a **skill id**, not a slot index. The source side of this message
is already known to be skill-keyed. Only **field 1** is in doubt, and only
because slot index 2 happened to hold skill id 2.

So the real prediction is narrower than "(a) or (b)": given a skill-keyed
source, a slot-keyed target would be an odd asymmetry.

### 8.2 The fixture

Hero bar seeded `[281, 276, 310, 284, 991, 279, 1685, 256]` — **every id above
7**, so no skill id can collide with any slot index 0..7. Verified before the
operator touches anything.

### 8.3 The gesture, and the exact numbers each reading predicts

**Drag slot 1 (skill 276) onto slot 5 (skill 279).**

| reading | predicted `0x005E` payload |
|---|---|
| **(b) skill-keyed** — registered as the prediction | `[200, 279, 0, 276, 0]` |
| (a) slot-keyed | `[200, 5, 0, 276, 0]` |

Field 1 is `279` or `5`. There is no third possibility that leaves the message
its declared four dwords, and no free parameter in either.

**C1 (the prediction):** field 1 carries the **target skill id**, `279`.
**C2:** fields 2 and 4 stay `0` — the copy indices of two singly-held skills.

**Refuted if** field 1 is `5`, which makes the message target-slot-keyed and
source-skill-keyed, and means a handler must resolve the two sides differently.
That is precisely why no handler was written on run B.

### 8.4 Exposure floor

**G1: ≥ 1 `0x005E`.** Nothing else in this run matters. No `0x005E`, no answer,
and the run is VOID rather than a null — a replace or a clear does not
substitute.

## 9. Result — RUN-HEROLIB-C: **the keying question is SETTLED, the field ORDER is not, and the two samples disagree**

Capture `authsrv-20260915T210512-c1.jsonl`, scored after teardown. Fixture
verified on the wire first: `[281, 276, 310, 284, 991, 279, 1685, 256]`, every
id above 7. Exposure floor **G1 met** — one `0x005E`.

```
0x005E [200, 276, 0, 279, 0]
```

### 9.1 C1 CONFIRMED and C2 CONFIRMED — the message is SKILL-KEYED at both ends

Field 1 is **276** and field 3 is **279**. Both are skill ids; slot indices run
0..7 and the fixture guaranteed no id could masquerade as one. The slot-keyed
reading (a) predicted a `5` in field 1 and there is none.

**So `0x005E` names SKILLS, not slots, on both sides — the question §7.3 was
built to answer.** Fields 2 and 4 are `0`, as predicted (C2), consistent with
the copy indices of two singly-held skills.

That is the result the run was for, and it is decisive.

### 9.2 But the SOURCE/TARGET assignment is REFUTED in the form it was predicted, and the two samples are INCONSISTENT

The registered prediction was field 1 = **target**, on the reasoning that run B's
field 3 held the source. Lining the two samples up against their bars:

| run | bar at the swap | slots dragged | payload | field 1 | field 3 |
|---|---|---|---|---|---|
| B | `[281, 256, 2, 284, 991, 279, 310, 1685]` | 1 → 2 (reported) | `[2, 0, 256, 0]` | `2` = slot **2**'s skill | `256` = slot **1**'s skill |
| C | `[281, 276, 310, 284, 991, 279, 1685, 256]` | 1 → 5 (reported) | `[276, 0, 279, 0]` | `276` = slot **1**'s skill | `279` = slot **5**'s skill |

**Under any fixed labelling these disagree.** If field 1 is the target, run B's
drag went 1 → 2 and run C's went 5 → 1. If field 1 is the source, run B's went
2 → 1 and run C's went 1 → 5. Each reading requires exactly one of the two
reported drag directions to be inverted.

Two other orderings were checked and both fail: **slot order** (run B puts the
higher slot's skill first, run C the lower) and **bar position** (same thing).
Nothing orders both samples consistently.

**The honest conclusion: the direction is carried by one of these two fields, and
which one is NOT determined by the data in hand.** The confound is no longer the
fixture — it is that the drag direction is known only from a verbal report after
the fact, and one of the two reports has to be inverted for the wire to make
sense. That is not a criticism of the report; it is a measurement design that
leaned on memory where it should have leaned on an artifact.

### 9.3 What would settle it, and it does not need a new gesture

The direction has to be recorded by something other than recall. Two options,
either sufficient:

* **Read the OUTCOME, not the input.** After one swap, have the operator report
  the bar's resulting left-to-right order. The bar is fully occupied with
  distinct ids, so the outcome names both ends unambiguously and the payload can
  be joined to it. This needs no new run type — just the readout taken from the
  screen after the drag rather than from the gesture before it.
* **Make the two ends non-interchangeable.** A swap between a slot the server
  can already distinguish — e.g. immediately after a `0x005C` write whose slot is
  known — pins one end from our own log.

**No handler is written on this.** The keying is settled and the direction is
not, and a swap arm that guesses the direction writes the bar backwards half the
time. The divergence stands: `0x005E` is still `UNHANDLED`, logged at line 206
of this run's server log, so the client swapped locally and our copy of that
hero's bar did not move.

### 9.4 A smaller thing this run also settled

Run B's `0x005C` replace **did persist**: the store's bar came into this run as
`[281, 256, 2, ...]`, slot 1 still holding the replacement. So the
store-loses-edits defect of §6.5 is **not** a blanket failure of every write —
it lost the c1→c2 transition in run A specifically. That narrows the search for
its writer, and is recorded here rather than folded into the §6.5 note because
it is evidence, not a theory.

## 10. The lost edits of §6.5 — the writer IDENTIFIED, from the logs already on disk (desk, no run)

§6.5 said the culprit was unidentified and that guessing was how this arc had
lost two evenings, so this section is built the other way round: the run's own
artifacts first, the mechanism second, the fix last, and each labelled.

### 10.1 The timeline, to the second — OBSERVED

Three files from run A (`vault/captures/harness/20260915T202552/` and the
three channel captures its `report.json` names) put the write and the loss in
the same second:

| artifact | event | wall clock |
|---|---|---|
| `authsrv/authsrv-20260915T202612-c1.jsonl` line 18 | `login_ok` — the auth process opens its roster `Store` here, on the SEEDED file | 00:26:12Z |
| `gamesrv/authsrv-20260915T202622-c1.jsonl` | the first game connection opens its own `Store` (log line 144, `PERSIST: sheet from …`); twelve edits go through it | 00:26:22Z → |
| `gamesrv/authsrv-20260915T202622-c1.jsonl` last event | game c1 closes (`ping_summary`, t = 467.18) | **00:34:09Z** |
| `authsrv/authsrv-20260915T202612-c1.jsonl` line 59 | `character_settings` — the client's `0x8009 UPDATE_CHARACTER_SETTINGS`, t = 476.91; **`authsrv.log` line 88: `character settings: req 9, 62B recorded and ACKED, PERSISTED`** | **00:34:09Z** |
| `gamesrv/authsrv-20260915T203409-c2.jsonl` first event | game c2 opens, reads the file (log line 476), sends the seed | **00:34:09Z** |

`report.json`'s endpoint table agrees: game c1 gone at t = 494.35, c2 open at
494.39, on a different loopback alias (`127.0.0.33`) — a map transfer, not an
exit. The auth connection (`127.0.0.1:6112`) stays open from t = 17.5 to 518.4,
across the whole run.

**The writer was in the log the whole time, at line 88.** §6.5 ruled the auth
process out by counting its *roster* saves — "one roster save (at 20:26, before
the edits)" — because that path prints `PERSIST:`. The settings arm prints
`PERSISTED` on a different line, from a different call, and was not counted.
Grep for the save sites, not for one print tag.

### 10.2 The mechanism — OURS, read from `authsrv.py` and `charstore.py`

* The auth process opens `state["charstore"]` at `login OK` (`authsrv.py`,
  the `charstore.Store.open(...)` under `if PERSIST:` in the login arm) and
  holds that object for the life of the auth connection.
* The game process opens its own `Store` per game connection
  (`charstore.find_character` in the instance-load burst, cached as
  `state["charstore_game"]`), and every edit — `set_hero_bar_slot`,
  `set_hero_attributes`, xp, kills, learned skills — saves through it.
* `Store.save()` wrote **the whole file from `self.data`**. So the auth
  process's `update_settings()` (the `UPDATE_CHARACTER_SETTINGS` arm) put the
  login-time snapshot — the seed — back over the file, and c2 opened it 0.0 s
  later.

### 10.3 When the client sends that message — OBSERVED, corpus-wide

`scratch settings_timing.py` over every capture with a wall clock (449 game
captures, 3,476 auth captures, 319 `character_settings` events):

| where the settings write sits | count |
|---|---|
| within 2 s of a game connection's first or last event | **319 of 319** |
| strictly inside a game connection (> 2 s from both ends) | **0** |
| in no game connection's window | 0 |
| more than 5 s before the auth capture's own end (a transfer, not an exit) | 30 |

So the client sends `0x8009` **exactly at a game-connection boundary** — map
transfer or exit to character select — which is the one moment the game
process's next `Store` is about to read the file. The overwrite and the read
collide by construction, not by chance.

**Runs B and C are the control, and they fit.** `20260915T204744` and
`20260915T210446` carry **zero** settings writes: the operator closed the
client from inside the map, the auth log ends in `ConnectionResetError`, and
no `0x8009` was ever sent. Their edits persisted (§9.4). Run A is the only one
of the three with a settings write, and the only one that lost its edits.

### 10.4 Exposure — RECONSTRUCTION from the code, with the corpus as the count

Every `--persist` session since the persistence arc (2026-08-18) in which the
client transferred maps or exited to character select reverted **all** of the
game process's edits since login: xp, kill accrual, attribute ranks, learned
and unlocked skills, hero bars. 319 settings events is the exposure count in
the corpus. No harness verdict checks persistence across a transfer, which is
why a defect this shape survived a month of green runs.

### 10.5 Shipped — the instrument §6.5 asked for, plus two guards

`toolkit/authsrv/charstore.py`:

* **Every `save()` prints one line** — `[charstore] SAVE <path> by
  <file:line in func> -- mtime <before> -> <after>` — path, caller and
  mtime, on by default (`charstore.TRACE`). A store write is rare; the one
  time it mattered nobody could say which process had written last.
* **A stale write is REFUSED.** A `Store` records the file's
  `(mtime_ns, size)` when it reads or writes; `save()` compares, and if the
  file changed underneath it prints `[charstore] charstore: STALE WRITE
  REFUSED -- <path> changed on disk since this Store read it (had …, disk
  now …); another writer's data would have been overwritten by <caller>.
  Call reload() first.` and returns `False`. Printed, **not raised**: a
  raise on the game thread stops the world for the rest of the session, and
  the refusal already loses nothing that is on disk. `Store.reload()` adopts
  the disk copy. The signature is taken *before* the read so a write landing
  between stat and read produces a false stale (a refusal) rather than a
  missed one; two writes of identical size inside one 100 ns NTFS tick would
  still pass, which is stated rather than solved.
* **`update_settings()` is a read-modify-write**: it reloads before applying
  the blob, so the auth roster's write carries the freshest game-side state
  and the client's blob lands beside it.

`test_charstore.py` 72 → **85**, with the run replayed on two `Store`
objects on one file in run A's order (login save → game edits → settings
write → reopen): the edits survive and the blob lands. The negative control
removes the `reload()` and reddens three checks — and shows the two guards
are independent: with the reload gone the settings write is *refused* rather
than applied, so the game's edits still survive; what is lost is only the
blob. The pre-2026-09-15 shape (a snapshot saved blind after another writer)
is refused by name.

### 10.6 What this does NOT settle

`0x005E`'s field order (§9.3) is untouched: that needs the one drag with the
bar's resulting order read off the screen. The `0x005E` handler is still not
written, for the reason §9.3 gives.

## 11. RUN-HEROLIB-D — the swap's direction, with the gesture PRE-REGISTERED and the outcome read off the screen

**Registered 2026-09-15 (night, later), BEFORE the client is launched.** §9.3
named the defect: the drag direction of runs B and C was taken from recall
after the fact, and one of the two recollections has to be inverted for the
wire to make sense. This run records the direction in the registration, has
the operator perform exactly that gesture, and confirms the outcome on screen
before the second gesture. Nothing is remembered afterwards.

### 11.1 The question

`0x005E [agent, skillA, copyA, skillB, copyB]` is skill-keyed at both ends
(§9.1). Which end is the skill the operator **picked up** (the source) and
which is the skill sitting in the slot it was **dropped on** (the target)?

### 11.2 The rig

Same as §8.2: the store still holds hero 3's bar
`[281, 276, 310, 284, 991, 279, 1685, 256]` (verified on disk at registration,
every id above 7), ranks `[[13, 2], [16, 1]]`, budget 10. Server
`--party slice --persist --unlocks corpus`, the slice build under
`vault/run/slice/`. The bar is verified **on the wire** (`0x00DA` for agent
200) before the operator is asked to touch anything; a different bar aborts
the run. This is also the first client run on §10's store guards: every save
prints its trace line, and the transfer/exit settings write now reloads
first.

### 11.3 The gesture — two drags, both pre-registered, using only the two END slots

The end slots are chosen so the operator never has to count: **leftmost** is
slot 0 (skill **281**) and **rightmost** is slot 7 (skill **256**).

| step | the operator does | the bar afterwards |
|---|---|---|
| **D1** | picks up the **LEFTMOST** slot and drops it on the **RIGHTMOST** slot | `[256, 276, 310, 284, 991, 279, 1685, 281]` |
| readout | confirms on screen: *the icon that was leftmost is now rightmost* (yes/no) | |
| **D2** | picks up the **LEFTMOST** slot again and drops it on the **RIGHTMOST** slot | back to the fixture `[281, …, 256]` |
| readout | confirms on screen: *the bar looks as it did at the start* (yes/no) | |

D1 and D2 are the same physical gesture on a bar whose two end skills have
exchanged places, so the source and target **skills are swapped between the
two messages**. That is the internal check with no free parameter: whichever
reading is right, message 2 must be message 1 with its two skill ids
exchanged.

### 11.4 Predictions, registered

| reading | D1 predicts | D2 predicts |
|---|---|---|
| **S — field 1 is the SOURCE (picked-up) skill, field 3 the TARGET** | `[200, 281, 0, 256, 0]` | `[200, 256, 0, 281, 0]` |
| **T — field 1 is the TARGET, field 3 the SOURCE** | `[200, 256, 0, 281, 0]` | `[200, 281, 0, 256, 0]` |

**Registered prediction: S.** Basis: run C is the better-controlled of the two
samples (fixture verified on the wire, ids above 7, one gesture) and under S
its reported 1 → 5 drag reads straight; under T run B's reported 1 → 2 reads
straight instead. One of the two must be right, and this run picks between
them with both directions fixed in advance. There is no third reading that
leaves the message its four dwords with copy indices 0.

**Refuted if** D1 produces the T row, or if D1 and D2 are not mirror images
of each other (which would mean the gesture performed was not the one
registered, and the run is VOID rather than a refutation).

### 11.5 Exposure floor, and the abort

| | requirement |
|---|---|
| **H1** | the fixture bar on the wire at load, exactly |
| **H2** | **≥ 2** `0x005E` from agent 200, in order, the second the mirror of the first |
| **H3** | both on-screen readouts answered *yes* |

One `0x005E` with H3's first readout *yes* is half an answer and is reported
as n = 1; zero is VOID. A *no* on either readout voids that message. **Scored
from the wire after teardown**, never live (§5.2's correction).

### 11.6 What ships on a clean result

A `0x005E` handler: the store's hero bar (or the player's) has the two skills
exchanged through the same referee `0x005C` uses, the edit is persisted, and
the log names both slots. **What the server replies is NOT settled by this
run** — the live corpus holds zero retail `0x005E`, so retail's reply, if
any, is UNOBSERVED. The handler will reply with nothing beyond the store
write, recorded as the open half, because the client has already swapped
locally and a reconstructed echo is a guess.

## 12. Result — RUN-HEROLIB-D: **S CONFIRMED — field 1 is the skill PICKED UP, field 3 the skill in the slot DROPPED ON; the two messages are exact mirror images**

Harness dir `vault/captures/harness/20260915T224108`, game capture
`gamesrv/authsrv-20260915T224140-c1.jsonl`, scored after teardown. The
harness printed `RUN VERDICT: FAIL` because the operator closed the client
inside the hold (exit code 0, no dialog — §5.2's known retraction, not
evidence against anything below).

### 12.1 The floor, all three met

| | requirement | result |
|---|---|---|
| **H1** | the fixture bar on the wire at load | `0x00DA` for agent 200 at t = 3.264: `[281, 276, 310, 284, 991, 279, 1685, 256]` — exact |
| **H2** | ≥ 2 `0x005E`, the second the mirror of the first | **two**, t = 87.779 and t = 95.253, 7.5 s apart |
| **H3** | both on-screen readouts *yes* | operator: "D1 and D2 both yes" |

### 12.2 The two messages, against the registered table

```
t=87.779  0x005E [200, 281, 0, 256, 0]     D1: leftmost (281) dropped on rightmost (256)
t=95.253  0x005E [200, 256, 0, 281, 0]     D2: leftmost (now 256) dropped on rightmost (now 281)
```

| reading | D1 predicted | D1 observed | D2 predicted | D2 observed |
|---|---|---|---|---|
| **S** (registered) | `[281, 0, 256, 0]` | **`[281, 0, 256, 0]`** ✓ | `[256, 0, 281, 0]` | **`[256, 0, 281, 0]`** ✓ |
| T | `[256, 0, 281, 0]` | ✗ | `[281, 0, 256, 0]` | ✗ |

**S is confirmed on both drags and T is refuted on both.** Field 1 is the
**source** — the skill the operator picked up — and field 3 is the
**target** — the skill sitting in the slot it was dropped on. The mirror
check holds exactly: message 2 is message 1 with its two skill ids
exchanged, which is what the same gesture on the swapped bar must produce
under either reading, so the gesture performed was the one registered.
Copy indices `0` in both, as in every earlier sighting (n = 4 now).

### 12.3 What this says about runs B and C

Under S, run C's reported drag (slot 1 → slot 5, `[276, 0, 279, 0]`) reads
straight, and run B's reported drag (slot 1 → slot 2, `[2, 0, 256, 0]`)
must have been **slot 2 → slot 1**: the operator picked up skill 2 and
dropped it on 256. That is the one inverted recollection §9.2 said had to
exist, and it was the earlier, less-controlled run's. Nothing about the wire
changes; only the label on run B's gesture does.

### 12.4 Shipped

* **`herolib.refuse_bar_swap` / `apply_bar_swap`** — reason-string referee
  (same skill both ends → `ChCliSkill.cpp:515`; an id not on the bar; id 0;
  a bar already holding an id twice) and the pure exchange, padded to eight.
* **`authsrv.handle_skillbar_skill_swap`**, dispatched on
  `GAME_CMSG_SKILLBAR_SKILL_SWAP = 0x005E`, agent-keyed like `0x005C`: the
  player's `SKILLBAR` or the hero's stored bar has the two skills exchanged
  and is persisted through `set_character_skillbar` /
  `set_hero_skillbar`. **On success nothing is sent** — retail's reply is
  UNOBSERVED (zero corpus sightings) and the client has already swapped
  locally, so an echo would be a guess about a message retail may not send.
  A **refusal still answers**: both slots are echoed unchanged through
  `0x00D9`, the per-slot message the client is known to accept, so its local
  swap is retired rather than left disagreeing.
* `schema/overrides.json` names GAME_CMSG 94 **`SKILLBAR_SKILL_SWAP`**
  (upstream's `SKILLBAR_SKILL_REPLACE` recorded as the prior name; a replace
  from the picker is one `0x005C`).
* `test_herolib` 24 → **33** (the run's own numbers: D1, D2 restores the
  fixture, symmetry, the four refusals, padding); `test_charstore` 85 →
  **91** (the real handler with a fake send on the player's bar: D1 lands
  and persists, nothing sent, D2 restores, a refusal echoes the on-bar slot
  unchanged and leaves the bar alone, a foreign agent is refused).

### 12.5 This run was also §10's first client exercise

`authsrv.log` line 51 carries the login save's new trace line
(`[charstore] SAVE … by authsrv.py:22694 in handle_portal_login -- mtime
01:05:09Z/1318B -> 02:41:33Z/1318B`). No settings write fired — the client
was closed from inside the map, as in runs B and C — and no game-side save
ran because `0x005E` was still unhandled when the run was made, so the
stale-write guard was not exercised by this run. It will be by the next
transfer.

### 12.6 Still open

* Retail's **reply** to `0x005E`, if any. Needs a live session in which the
  owner swaps two hero-bar slots on the secondary account, at human cadence.
* `0x0065 SKILLBAR_SLOT_FLAGS` and `0x001B` remain unmodelled (§40.6).

## 13. RUN-HEROLIB-E — does a game-side edit SURVIVE the transfer's settings write now? (§10's fix, on a client)

**Registered before launch, 2026-09-15 (night, last).** §10 shipped on a
unit test that replays run A's order on two `Store` objects. Run D did not
exercise it: the client was closed from inside the map, so no
`UPDATE_CHARACTER_SETTINGS` fired. This run makes the settings write fire
after a persisted edit, the way run A lost its twelve.

### 13.1 The rig

Same store as §11.2: hero 3 bar `[281, 276, 310, 284, 991, 279, 1685, 256]`,
ranks `[[13, 2], [16, 1]]`, 6 of 10 unspent (verified on disk at
registration). Same server flags and build. `--hold 300`.

### 13.2 The gesture

| step | the operator does | what it exercises |
|---|---|---|
| **E1** | one `+` on Tahlkora's Healing Prayers (13: 2 → 3) | `0x000F` → `set_hero_attributes` → a game-process `save()` |
| **E2** | returns to character select (logout from the menu) and presses Play again | the auth-channel settings write at the game boundary, then game c2's fresh `Store` |

### 13.3 Predictions, registered

* **P1 (the fix):** game c2's hero block carries rank **3** for attribute 13
  and **3 of 10** unspent — the edit survived the boundary. The pre-fix
  behaviour (run A's) would send the seed: rank 2, 6 of 10.
* **P2 (the instrument):** `gamesrv.log` shows one `[charstore] SAVE … in
  persist_hero_attributes`; `authsrv.log` shows the settings write's
  `[charstore] SAVE … in handle_…` with **no** `STALE WRITE REFUSED` line,
  its "mtime before" equal to the game save's "mtime after" (the reload
  adopted the game's write before saving over it).
* **Refuted if** c2 carries rank 2 / 6 of 10 with a settings write present
  in the auth log. A `STALE WRITE REFUSED` line would mean the reload
  did not run first — also a refutation of P2, and the loss it prevents
  would then show as P1 still holding.

### 13.4 Exposure floor

**J1** ≥ 1 `0x000F` for agent 200 answered and persisted in c1. **J2** a
`character_settings` event in the auth capture after J1. **J3** a game c2
that sends the hero's attributes. Any one missing makes the run VOID: in
particular, a client closed from inside the map (J2 missing) is exactly
run D's null and answers nothing here. Scored from the wire and the logs
after teardown.

## 14. Result — RUN-HEROLIB-E: **VOID on its own floor (J2), and the reason is a new fact: a character-select round trip does NOT send the settings write — only a zone transfer does**

Harness dir `vault/captures/harness/20260915T225832`, auth capture
`authsrv-20260915T225855-c1.jsonl`, scored after teardown (`RUN VERDICT:
FAIL` is the hold's own expiry; the client was left open as asked).

### 14.1 What happened, from the logs

| | evidence |
|---|---|
| **J1 met** | `gamesrv.log:210` `0x800f ATTRIBUTE_INCREASE`; `:212` `[charstore] SAVE … by authsrv.py:14281 in persist_hero_attributes -- mtime 02:58:55Z/1318B -> 03:01:38Z/1318B`; `:213` `hero 3 attributes saved -- 13=3, 16=1, 3 of 10 unspent` |
| **J2 NOT met** | `authsrv.log` carries **no** `character settings` line and the auth capture no `character_settings` event. The logout produced `player status -> 0 (Offline)` (`:79`), a second `REQUEST_GAME_INSTANCE` for the same map 148 (`:91`), and nothing else. |
| **J3 met** | game c2 sent `AGENT_ATTRIBUTE_POINTS(hero agent 200: 3 of 10)` (`:308`) and the hero's `0x003A` (`:319`); the operator saw Healing Prayers at 3 |

**P1's observation is real but proves nothing about §10's fix**: the edit
survived because no settings write ever ran, so there was nothing to
overwrite. By §13.4 the run is VOID for the question it registered.

### 14.2 The fact it found instead — OBSERVED here, CORROBORATED by the corpus

Run A's boundary was a **zone transfer on the game channel** — c1 handed off
to `127.0.0.33` and its auth capture holds exactly **one**
`game_instance_request`. This run's boundary was a **character-select round
trip through the auth channel** — a second `game_instance_request`, same map.
The settings write fired for the first and not the second.

`scratch charselect_census.py` over every auth capture: **15 captures carry
two or more `game_instance_request`s on one auth connection (17 gaps), and
0 of 17 have a `character_settings` event between them** — 12 same-map,
5 map-change. So `UPDATE_CHARACTER_SETTINGS` is sent on an in-game zone
transfer and not on a re-entry from character select. (Consistent with §10.3's
319-of-319 at a game boundary: those boundaries were all handoffs.)

### 14.3 What this means for the fix, and the run that would test it

§10's guards are still exercised only by `test_charstore`. The run that
exercises them on a client is E with **E2 replaced by walking through a
portal** — the slice corridor's own transfer (SLICE-H8 crosses it) — so the
game channel hands off and the settings write fires after the edit. Same
predictions, same floor with J2 read as "a `character_settings` event after
J1". Registered as **RUN-HEROLIB-F** when there is a next five minutes; not
run tonight.

### 14.4 Also recorded

The character-select round trip itself works against this server end to
end: logout → `Offline` → character select → Play → a second instance
request answered → c2 in the map, hero data served from the store. The
first-cut instruction in §13.2 assumed the round trip would carry the write;
the census says it never has, and that assumption is the kind §10.3 exists
to replace with a count.

## 15. RUN-HEROLIB-F — §13's question with the boundary that actually carries the write: a PORTAL

**Registered before launch, 2026-09-15 (night, last).** §14 showed the
character-select round trip never sends `UPDATE_CHARACTER_SETTINGS`; the
zone transfer does (run A, and §10.3's 319). So E2 becomes a walk through
a portal.

### 15.1 The rig

Store as run E left it: hero 3 ranks `[[13, 3], [16, 1]]`, **3 of 10**
unspent, bar unchanged. Same flags and build; `--hold 420` for the walk.

### 15.2 The gesture

| step | the operator does | exercises |
|---|---|---|
| **F1** | one **−** on Tahlkora's Healing Prayers (13: 3 → 2, refund +3 → **6 of 10**) | `0x000E` → `persist_hero_attributes` → a game-process `save()` |
| **F2** | walks through a portal to another map | the game-channel handoff, the auth-channel settings write, game c2's fresh `Store` |

A **minus** rather than a plus because 3 unspent cannot pay rank 4 (cost 4)
and the client greys the plus out; the refund direction is the one the run's
budget allows.

### 15.3 Predictions

* **P1 (the fix):** game c2 serves rank **2** and **6 of 10** for hero 3.
  The pre-fix behaviour would put the on-disk seed back: rank 3, 3 of 10.
* **P2 (the instrument):** `gamesrv.log` shows `[charstore] SAVE … in
  persist_hero_attributes`; `authsrv.log` shows the settings write's own
  `[charstore] SAVE …` with **no** `STALE WRITE REFUSED`, its "mtime before"
  equal to the game save's "mtime after".
* **Refuted if** c2 serves 3 / 3 of 10 with a `character_settings` event
  present after F1; or if a `STALE WRITE REFUSED` line appears.

### 15.4 Exposure floor

**K1** ≥ 1 `0x000E` for agent 200 answered and persisted in c1. **K2** a
`character_settings` event in the auth capture **after** K1 (the whole
point; a run without it is run E again and VOID). **K3** a game c2 that
sends hero 3's attributes. Scored after teardown.

## 16. Result — RUN-HEROLIB-F: **P1 held across a real handoff, but K2 unmet AGAIN — the settings write did not fire, and the corpus says its trigger is neither the transfer nor an edit**

Harness dir `vault/captures/harness/20260915T231050` (`RUN VERDICT: PASS`
this time — the client was still up when the hold ended); auth capture
`authsrv-20260915T231109-c1.jsonl`, game c1 `…231115-c1`, game c2
`…231146-c2`. Scored after teardown.

### 16.1 What happened

| | evidence |
|---|---|
| **K1 met** | `gamesrv.log:203` `0x800e ATTRIBUTE_DECREASE`; `:205` `[charstore] SAVE … in persist_hero_attributes -- mtime 03:11:10Z -> 03:11:38Z`; `:206` `hero 3 attributes saved -- 13=2, 16=1, 6 of 10 unspent` |
| the handoff | `:224` `GAME_SERVER_TRANSFER -> 127.0.0.33:6112, map 168` — the same portal as run A (`ascalon_to_corridor`, 148 → 168); c1's last event 03:11:45Z, c2's first 03:11:46Z |
| **K2 NOT met** | the auth capture holds **no** `character_settings` event and `authsrv.log` no `character settings` line — only the login save's trace at `:51` |
| **K3 met** | `:313` `AGENT_ATTRIBUTE_POINTS(hero agent 200: 6 of 10)` on c2; the operator saw 2 after the warp |

**P1 held on a real game-channel handoff** — the edit survived the very
boundary that lost run A's twelve — **but not because the fix ran**: no
settings write fired, so nothing tried to overwrite it. By §15.4 the run is
VOID for P2 and corroborates P1 only in the weak sense that the handoff
alone does not lose an edit (which §10 already said).

### 16.2 The trigger is NOT what §14 concluded — corpus, two censuses

§14 read the 0-of-17 auth-channel re-entries as "the write rides the zone
transfer". Run F took the same transfer as run A and got no write. So the
question was put to every game connection with a wall clock (449), asking
whether a `character_settings` event landed within 2 s of its close:

| connection carried … | settings at close | no settings |
|---|---|---|
| no bar edit, no attribute edit | **318** | **129** |
| a bar edit (`0x005C`/`0x005E`), no attribute edit | 0 | 4 |
| an attribute edit, no bar edit | 0 | 2 (runs E, F) |
| both | 1 (run A) | 0 |

and, by how the connection ended:

| close followed by another game connection ≤ 3 s (a transfer) | settings | no settings |
|---|---|---|
| | **29** | **16** |
| **not followed (exit / kill)** | **290** | **119** |

**OBSERVED:** the write lands at roughly **seven closes in ten, of either
kind**, and its presence is independent of whether the connection carried an
edit. It is not a dirty-flag push on the bar or the attributes, it is not
transfer-specific, and it is not exit-specific. What decides it is **NOT
FOUND** tonight. (The 0-of-17 in §14 stands as a fact about auth-channel
re-entries; the inference drawn from it was too strong.)

The 62-byte blob itself (`08 00 94 00 … 30 00 00 00 | 05 ed 00 00 | dc 5d
00 0b 00 13 | 5b 00 0b 00 13 | 5c … | 5e … | 5a 00 0b 00 13`) has five
5-byte groups with consecutive leading bytes `5a`–`5e`, which reads like a
five-slot appearance record — armor pieces with a dye word — but that is a
guess and is labelled so.

### 16.3 Where this leaves §10's fix

Exercised by `test_charstore` (the run-A replay) and by nothing else.
Two routes to a client exercise, in cost order:

* **Repeat run F until the write fires.** At ~70 % per close, two or three
  five-minute runs. Cheap, but blind: a null is indistinguishable from bad
  luck until the trigger is known.
* **Find the sender.** The c2s framer for auth opcode `0x8009` in the
  client, and what gates the call — a `codescan` desk item, no run. That
  turns the 70 % into a rule and makes the next run a one-shot.

Neither was done tonight; the owner's minutes were spent. The fix's
correctness rests on the unit replay of run A's exact order, which is the
same order the corpus's 319 writes follow.

## 17. The `0x8009` sender, found statically — and why the write is edit-independent (desk, `codescan`, no run)

> **PARTLY REFUTED BY §18, 2026-09-15 (night, last). Read §18 first.** §17.2 named
> two senders of "opcode 9"; **only `0x00493010` is `UPDATE_CHARACTER_SETTINGS`.**
> `0x00491E50` is **`GAME_CMSG` 9, a different message on a different channel**, and
> its interval is a **payload field, not a gate** — so §17.4's "a periodic sender
> explains the edit-independence" is **WITHDRAWN**. §17.1 (the serializer and the
> `0x8000` mask) and §17.3 (the blob rides `0x8020`) stand.

§16 left the settings write's trigger NOT FOUND: it lands at ~7 of 10 game-connection
closes regardless of whether the connection carried an edit. Read out of the pinned
38797 client (`vault/client/2026-07-29_221c13772c7a/Gw.exe`) with
`toolkit/clientscan/codescan.py` — the disassembler carve-out (1), MEASUREMENT only:
addresses, counts and control flow, no bytes copied.

### 17.1 The serializer, and why the wire says `0x8009` — OBSERVED

The auth outbound serializer is **`0x007DCB10`**. At `0x007DCBCF` it does
`and eax, 0x8000` then `or ax, word ptr [esi]` — it ORs the **`AUTH_CMSG_MASK`
(`0x8000`)** into the 16-bit opcode word. So the wire's `0x8009` is mask `0x8000`
| opcode `9`, and `authsrv.py`'s own `AUTH_CMSG_MASK = 0x8000` is confirmed on the
client side rather than assumed. `UPDATE_CHARACTER_SETTINGS` is auth opcode **9**
(`authsrv.py:9566`; msgtable ch3 AUTH_CMSG, `studies/msgtable/FINDINGS.md`).

### 17.2 TWO call sites stage opcode 9 into it — OBSERVED

A three-level caller walk up from `0x007DCB10`, flagging any function whose body
writes the immediate `9`, finds both inside the `GcAuthCmd` send family
(`0x0049xxxx`, the block `protoscan.py` names `GcAuthCmdSend*`):

| sender | payload | conn global | shape |
|---|---|---|---|
| **`0x00491E50`** | 3 dwords | `0xc034d4` | computes a **millisecond interval** first (`0x3E8`/rate, else `0x28`) — a **rate-driven / periodic** send |
| **`0x00493010`** | 4 dwords | `0xc03524` | a leaf serializer; its only caller `0x00490930` is a **vtable thunk** reading object members `+0x20 / +0x28 / +0x2c / +0x54` and sending them — the **explicit field-serialize** path |

Both are reached indirectly (a command/dispatch table; neither VA is stored as a
plain word), which is why `§16` could not see them from the wire.

### 17.3 Neither carries the 62-byte blob — OBSERVED, and it re-reads our own decode

Both senders push ≤ 5 dwords. The 62-byte settings blob our server logs against
`0x8009` is **not** this message's payload — it rides the separate
`SETTING_UPDATE_CONTENT` (`0x8020`) upload that precedes it in every auth log
(`0x8021` size, `0x8020` content, then `0x8009`). **`0x8009` is a small COMMIT**,
not the blob carrier. Our `update_settings` handler is fed the buffered blob and
happens to log its length beside the commit; the two are separate messages.

### 17.4 Why the write is edit-independent — RECONSTRUCTION

§16's census: the write is present at ~70% of closes and its presence does **not**
depend on whether the connection carried a bar or attribute edit. Two senders of
one opcode, **one of them rate-driven** (`0x00491E50`'s interval math), is exactly
the shape that produces that: the commit fires on a **timer / lifecycle**, not only
on an explicit settings change, so an edit is neither necessary nor sufficient. The
edit-independence §16 measured and the two-site structure agree. Labelled
RECONSTRUCTION because the timer's **condition** — what makes it ~70% rather than
always — is not yet read.

### 17.5 What this settles for §10's fix, and what is left

**Settled:** the client sends `0x8009` from a periodic/lifecycle site independent of
edits, so §10's stale-write hazard is **real on an ordinary session**, not an edge
case that needs an edit to provoke — any connection close can carry the commit that
made the auth roster save over the game process's state. The fix (reload-before-save
+ stale-write refusal) guards the case that actually occurs.

**Left (desk, no run):** follow the vtable/dispatch to each sender's gate and read
`0x00491E50`'s interval condition, to turn "~70%" into a rule and name which site
fires at a close. That is the remaining step toward a one-shot client exercise of
the guard; until then the guard rests on `test_charstore`'s replay of run A's order.

## 18. CORRECTION to §17 — the two "opcode 9" senders are on DIFFERENT CHANNELS, and the interval is a payload field, not a condition

§17 was written from a caller walk that flagged any function staging the
immediate `9`, and it did not check **which channel's** opcode 9 each one was.
The declared shapes settle it, and they disagree with §17.

### 18.1 The shapes decide it — OBSERVED, `schema/messages.json`

| channel | opcode 9 | declared |
|---|---|---|
| **AUTH_CMSG** | `UPDATE_CHARACTER_SETTINGS` | `{dword, string16(20), array8(64)}`, **variable length**, unpack 118 |
| **GAME_CMSG** | — | `{dword, dword}`, **fixed**, unpack **10** |

The serializer takes `(conn, msgptr, slots)` where `slots` counts **struct
dwords including the opcode**, so:

* **`0x00493010` pushes 5 slots** = `{9, req_id, name_ptr, len, blob_ptr}`.
  Its caller `0x00490930` is a `thiscall` thunk filling them from one object:
  `[ecx+0x20]` (a value), `&[ecx+0x2c]` (an inline buffer), `[ecx+0x28]` (a
  count), `&[ecx+0x54]` (a buffer). A dword, a string, and a counted array —
  **AUTH_CMSG 9's declared shape. This is the settings sender.**
* **`0x00491E50` pushes 3 slots** = `{9, interval, flag}` → wire 2 + 4 + 4 =
  **10 bytes, exactly GAME_CMSG 9's declared size**, on a different connection
  global (`0xc034d4`). **It is not the settings message at all.** It is the
  `c2s 0x8009 ?` our own `gamesrv.log` prints as unknown on the GAME channel
  (run E, `:207`) — the `0x8000` mask makes both channels' opcode 9 read
  `0x8009` on the wire, which is what made them look like one message.

### 18.2 The interval is a PAYLOAD FIELD — OBSERVED, and this is what was asked

`0x00491E50` computes `1000 / f(4, 3)` (`0x00659DC0`), falling back to `0x28`
when that returns 0, and stores the result **into the message body** at
`[ebp-0xc]`; `0x00631AA0` is a two-instruction getter (`mov eax, [0xc1100c];
ret`) whose result is normalised to 0/1 and stored at `[ebp-8]`. Then it sends,
**unconditionally** — there is no branch between the computation and the send,
and the function returns a constant 1.

**So there is no interval condition.** A millisecond interval and a boolean are
*what this message carries* (a client-side rate report on the game channel),
not a rule about when anything is sent. §17.4 read the arithmetic as a gate; it
is content.

### 18.3 What actually decides the settings send — and it is not in the sender

`0x00490930`'s address appears exactly once in the image, as an aligned word in
`.rdata` at **`0x0094135C`**, inside a table of `.text` pointers with a **six-dword
stride** whose other slots repeat across records (`0x00490AC0`, `0x00490660`).
That is a per-command descriptor table for the `GcAuthCmd` family — the settings
command's record begins at `0x00941354` and its third slot is the send thunk.

So the send carries **no gate of its own**: it fires whenever that command object
is dispatched. Whatever schedules the command is application-level and above this
table. **The ~70 % of §16 remains NOT FOUND**, and it is now known not to live in
the sender.

### 18.4 What stands from §17, and what this costs

**Stands:** the serializer `0x007DCB10` and its `and eax, 0x8000; or ax, [esi]`
at `0x007DCBCF`, which confirms `AUTH_CMSG_MASK` from the client side (§17.1);
and the blob riding `SETTING_UPDATE_CONTENT` with `0x8009` as a small commit
(§17.3) — now *strengthened*, since the settings sender's own struct carries a
pointer and a count rather than 62 bytes.

**Withdrawn:** §17.4's reconstruction, and with it the claim that §10's hazard was
shown to be "real on an ordinary session" *by that argument*. The hazard is still
real — §16's census measured the write at ~7 of 10 closes **independent of
edits**, which is a wire fact and needs no model of the sender — but §17 reached
it through a function that turned out to be a different message.

**Method note.** The walk flagged "a function that writes the immediate 9" and
`§17` never asked *which table's* 9. One `schema/messages.json` lookup — 118 bytes
variable against 10 bytes fixed — separated them immediately. `CLAUDE.md` calls
this out: a number our own tool produced, cited as if the client had said it. The
check that caught it was the cheapest one available and was skipped because the
caller walk looked conclusive.

## 19. What dispatches the settings command — a DIRTY CHECK on the character summary (desk, `codescan`, no run)

§18 left the trigger not found and said only that it is not in the sender. It is one
level up, and it is a comparison.

### 19.1 The chain, end to end — OBSERVED

```
0x004A8A20   the dispatcher            (3 call sites: 0x004A6BAA, 0x004A7CB8, 0x004A8464)
 0x004A8CC2    call 0x008711E0         <- the GATE, thiscall on the object at 0xC07000
 0x004A8CC7    test eax, eax
 0x004A8CC9    je   0x004A8D1F         <- returns 0: SKIP, nothing is sent
 0x004A8CF0    call 0x00870D80         serialize the summary into a 0x100-byte buffer
 0x004A8D0B    call 0x0048E790         construct + dispatch the command
   0x0048E790    vtable <- 0x00941354, alloc 0xA4, id 0x80000012
                 cmp <len>, 0x40 ; store at +0x28 ; copy 0x14 bytes of the name
   0x00490930    the vtable's send thunk  (slot +8 of the record)
   0x00493010    5 slots {9, req_id, name_ptr, len, blob_ptr}
   0x007DCB10    OR 0x8000 -> the wire's 0x8009
```

**The constructor is confirmed by the client's own words.** `0x0048E790` bounds the
payload at `0x40` and, past it, reports

```
charSummaryBytes <= sizeof(trans->m_event.inCharacterData)
P:\Code\Gw\Net\Cli\GcApi.cpp(4184)
```

`charSummaryBytes` and `inCharacterData` name the payload, `0x40` is
`array8(64)`'s declared capacity and `0x14` the `string16`'s — §18's shape match,
now corroborated by ArenaNet's own assert rather than by our arithmetic alone.

### 19.2 The gate is a dirty check — OBSERVED, from its return polarity

`0x008711E0` is `stdcall` (`ret 0x44` — 17 dwords) on the summary object at
`0xC07000`. Its body is a chain of **21 compares** in its first `0x160` bytes,
each `cmp <passed field>, <stored member>` with `jne` out of the chain, plus an
element-wise loop over an array (`inc edi; add esi, 4; cmp edi, ebx; jb`). The two
exits:

| path | code | meaning |
|---|---|---|
| every field equal, loop ran to completion (`edi == ebx`) | `xor eax, eax; ret 0x44` | **0 — unchanged** |
| any `jne` taken, or the loop cut short | falls to `0x0087131B`/`0x0087131E`, on to the update path | **nonzero — changed** |

So the caller's `test eax, eax; je` means: **the client sends
`UPDATE_CHARACTER_SETTINGS` only when the character summary DIFFERS from the one it
last sent.** Unchanged summary, no message.

### 19.3 This is why the write is edit-independent — and it closes §16's question

§16 measured the write at ~7 of 10 closes with its presence **independent of whether
the connection carried a bar or attribute edit**, and could not say why. It now has a
mechanism: the compared fields are the **character summary** — the appearance/status
record serialized at `0x00870D80` from `0xC07000`, bounded at 64 bytes — and a hero's
skill bar and a hero's attribute ranks **are not among them**. An edit to either
leaves every compared field equal, so it cannot cause the send; something unrelated
changing the summary can, on any connection. Edit-independence is not a coincidence in
the sampling, it is the gate's definition.

**Labelled:** the chain, the assert, and the polarity are OBSERVED. That this
mechanism *accounts for* ~70 % specifically is RECONSTRUCTION — predicting the rate
would need to know which summary fields change per session, which is not measured.
What is settled is the **shape**: a dirty check on a record that does not include the
things this arc edits.

### 19.4 What it means for §10's guard

The settings write fires on a condition **the server cannot see and the operator does
not control**, on any connection close where the summary happens to have moved. That
is precisely the hazard §10's reload-before-save guard exists for: the auth process's
stale snapshot can be flushed over the game process's edits at a moment unrelated to
those edits. Runs E and F did not see it because the summary had not moved, not
because the path is rare — and no run can be *scheduled* to provoke it without
changing a summary field on purpose.

**The cheap way to provoke it, for whoever exercises the guard on a client:** change
something in the summary during the session — the fields are appearance/status, so a
visible change of that kind before zoning should make the compare fail and force the
send. Not attempted here; it is the next run's design, not a claim.

## 20. RUN-HEROLIB-G — force the dirty check to fail, and exercise §10's guard on a client

**Registered before launch, 2026-09-16.** §19 found the gate: the summary is sent
only when it differs from the baseline. Runs E and F produced no write because
nothing had moved. This run moves it **from the server side**, which needs no equip
path and no operator dexterity.

### 20.1 The lever, and the reasoning behind it

§19.2's compare is against the copy the client holds as "what the server has".
Our server serves that baseline at login as the store's `settings_blob`
(`CHARACTER_INFO`). That predicts the whole history of this arc:

| run | stored blob vs. what the client computes | write? |
|---|---|---|
| A | stale (the store had not yet taken the client's own) | **yes** |
| E, F | already equal — run A's write had stored it | no |

So **altering one byte of the stored blob should restore run A's condition.**
This is a prediction the earlier runs can refute: if the blob is not the baseline,
the run comes back null and §19's model is wrong about *what* it compares against
(the gate itself would still stand).

### 20.2 The fixture

`vault/state/characters/loopback_rurik.invalid.json`, backed up to
`…json.pre-summary-test.bak`. One byte of `settings_blob` changed, **byte 59 of 62,
`0x0b` → `0x0c`** — a value inside a trailing 5-byte group, never a length and
never an id, because an invalid id is exactly what the client's own
`Character summary item invalid` (`UiGame.cpp:618`) refuses. Length unchanged at
62 bytes. Hero 3 untouched: ranks `[[13, 2], [16, 1]]`, budget 10.

### 20.3 The gesture

| step | the operator does |
|---|---|
| **G1** | one `+` on Tahlkora's Healing Prayers (13: 2 → 3, leaving 3 of 10) |
| **G2** | walks through the corridor portal, as in run F |

### 20.4 Predictions

* **P1 — the lever works:** a `character_settings` event appears in the auth
  capture (**this is the floor; without it the run is VOID for P2/P3 and refutes
  §20.1's baseline model**).
* **P2 — the guard holds:** game c2 serves hero 3 at rank **3**, **3 of 10** —
  the edit survives a session that *did* carry the write.
* **P3 — the instrument shows the join:** `authsrv.log` carries the settings
  write's `[charstore] SAVE` with **no `STALE WRITE REFUSED`**, and its "mtime
  before" equals the game save's "mtime after".
* **Refuted if** c2 serves rank 2 / 6 of 10 with a settings write present (the
  guard failed), or if a `STALE WRITE REFUSED` line appears (the reload did not
  run first).

### 20.5 Floor

**L1** ≥ 1 `0x000F` for agent 200 persisted in c1. **L2** a `character_settings`
event after L1. **L3** a game c2 serving hero 3's attributes. Scored from the wire
and the logs after teardown. **Restore the backup afterwards either way.**

## 21. Result — RUN-HEROLIB-G: **the lever WORKS, and §10's guard is EXERCISED ON A CLIENT for the first time — the edit survives the very sequence that lost run A's twelve**

Harness dir `vault/captures/harness/20260916T002049`. Scored after teardown.
`RUN VERDICT: FAIL` is the in-hold close again (§5.2's known retraction).

### 21.1 The floor, all three met

| | requirement | result |
|---|---|---|
| **L1** | a hero attribute change persisted in c1 | `gamesrv.log:203` `0x800f`; `:206` `hero 3 attributes saved -- 13=3, 16=1, 3 of 10 unspent` |
| **L2** | a `character_settings` event **after** L1 | `authsrv.log:79` `character settings: req 8, 62B recorded and ACKED, PERSISTED` — **the first one since run A** |
| **L3** | a game c2 serving hero 3's attributes | `gamesrv.log:311` `AGENT_ATTRIBUTE_POINTS(hero agent 200: 3 of 10)` |

### 21.2 P1 CONFIRMED — one byte flipped the client from silent to sending

Runs E and F, same rig and same gestures, produced **no** settings write. This run
changed **one byte of the served `settings_blob`** and the write fired. That is a
controlled pair: the only difference between F and G is that byte.

### 21.3 P2 and P3 CONFIRMED — and the mtime join is exact

```
gamesrv.log:205  [charstore] SAVE ... in persist_hero_attributes
                 -- mtime 04:21:13.676955Z -> 04:21:38.312819Z
authsrv.log:78   [charstore] SAVE ... in handle
                 -- mtime 04:21:38.312819Z -> 04:21:41.629055Z
```

The auth write's **"mtime before" equals the game write's "mtime after", to the
nanosecond**. That is `update_settings()`'s reload adopting the game process's
write before saving over it — the fix of §10 doing its job, visible in the
instrument §6.5 asked for. **No `STALE WRITE REFUSED` line anywhere in the run.**

And c2 served **3 of 10** with rank 13 = 3. The pre-fix behaviour is exactly known
here: it served the seed, 6 of 10, which is what run A got. **This is the first
time the guard has been exercised by a real client**, on the same sequence — game
edit, settings write, reconnect — that lost run A's twelve edits.

### 21.4 A refinement the run forced, and it corrects §20.1

> **CLOSED by §22 (2026-09-16).** The four bytes are positions the client's packer never writes and its unpacker never reads; byte 59 is `item[4].b`, which the dirty check compares. Nothing below is wrong, and "which is which" is now a byte map.

The blob the client sent back differs from the **original** stored blob in more
than the byte that was flipped:

| bytes 32–36 | byte 59 |
|---|---|
| stored (runs E, F, G baseline): `05 ed 00 00 dc` | `0b` (G served `0c`) |
| what the client sent: `05 00 00 00 00` | `0b` |

So the original blob **already disagreed with the client in four bytes** during
runs E and F — and neither sent. Therefore **the served blob is not compared
wholesale**, and §20.1's "the stored blob is the baseline" is too strong. What is
supported: **a byte inside an item group is compared** (flipping one forced the
send), while bytes 33–36 are not — they are plausibly volatile (a transaction or
session value) that the client overwrites without comparing. Which is which is
**NOT FOUND**; §19.2's gate itself is untouched, since it compares *fields*, and
this says only which fields reach it.

### 21.5 Housekeeping

The store was restored from `…json.pre-summary-test.bak` and the backup removed,
as §20.5 registered. That **also reverts this run's hero edit** (back to
`[[13, 2], [16, 1]]`, 6 of 10) and restores the original blob — so the next
session starts from the same fixture E and F used. The evidence for this run lives
in the logs and captures, not in the store. Note for the next run: the restored
blob is the one that did **not** trigger a write, so provoking one again needs the
byte flip again.

## 22. Which fields reach the dirty check — the summary's byte map, read from the packer (desk, `codescan`, no run)

§21.4 left one thing open: the blob G's client sent back differed from the one we
served in **five** bytes, and four of them had been served through runs E and F
without provoking a send. "Which fields reach the gate" was NOT FOUND. It is now a
byte map, and the four bytes are not fields.

### 22.1 The chain, one level deeper than §19 — OBSERVED

§19.1 stopped at "`0x00870D80` serializes the summary". That function copies the
summary object at `0xC07000` into a 0x7C-byte struct on its stack and hands it to a
packer; the packer is what puts bytes on the wire, and a second function is the
unpacker that fills the summary from a served blob. All three read cold from the
pinned build with `codescan.py --dis`, streams aligned from each prologue:

```
0x00870D80   serializer: summary -> struct S (0x7C bytes on its stack), then
   0x0084D4E0  -> jmp 0x009273B0   the PACKER: S -> bytes in the caller's 0x100 buffer
0x00870F90   summary <- served blob:
   0x0084D4F0  -> jmp 0x009274D0   the UNPACKER: bytes -> S, then S -> summary
   (a fresh record: this+0x30 <- 0x6e657762 'newb', this+8..0x14 <- 0, this+0x2C <- 0)
0x008711E0   the GATE (§19.2), 17 stack args from the dispatcher, each one a
             field of the summary the dispatcher has just re-read
```

**The packer, `0x009273B0`.** It reserves `0x25 + 5·count` bytes (`0x00741A90` is a
grow-and-reserve on the output buffer, not a zeroing allocator — the reserved bytes
hold whatever the buffer held) and writes, in order:

| wire offset | width | written from | note |
|---|---|---|---|
| 0 | u16 | constant 8 | version |
| 8 | u32 | S+0x00 | |
| 0x1C | u32 | bit-merged, bits 0–17 | **read-modify-write**: `xor edx,[ebx+0x1c]; and edx,0xf; xor edx,[ebx+0x1c]` keeps the dword's other bits; seven more merges the same way |
| 0xC..0x18 | 4×u32 | S+0x08..0x14 | |
| 0x20 | u8 | S+0x18 | count |
| 2 | u16 | S+0x5C | |
| 4 | u32 | S+0x60 | |
| 0x25+5i | u16, u16, u8 | S+0x1C+4i, S+0x30+4i, S+0x44+4i | one item, five bytes |

**Never written: bytes 0x21–0x24, and bits 18–31 of the dword at 0x1C.** The packer
has no instruction that stores to them; the read-modify-write on 0x1C carries the
buffer's stale bits through.

**The unpacker, `0x009274D0`.** Refuses fewer than 2 bytes; a version word above 8
returns 0; a version below 8 goes through a converter (`0x005EAFA0`, descriptor table
`0xBCB3D8`, not read here) which must yield 8; then zeroes S (0x7C bytes) and reads
word 0, word 2, dword 4, dword 8, dwords 0xC..0x18, byte 0x20 (refuses count > 5 and
a blob shorter than `0x25 + 5·count`), bits 0–17 of dword 0x1C (bit 16 through
`movzx eax, word ptr [ebx+0x1e]; and eax, 1`), and the items. **Never read: bytes
0x21–0x24 and bits 18–31.** So a served blob's residue in those positions cannot
reach the summary object, and therefore cannot reach the gate.

**The struct ↔ summary map**, from the serializer's copy-out and the unpacker's
copy-in (`0x00871024`–`0x0087107C`), which is what joins a wire byte to a compared
member:

```
S+0x00 <-> +0x00    S+0x58 <-> +0x28    S+0x64 <-> +0x34    S+0x70 <-> +0x44
S+0x04 <-> +0x04    S+0x5C <-> +0x2C    S+0x68 <-> +0x38    S+0x74 <-> +0x40
S+0x08..0x14 <-> +0x08..0x14            S+0x6C <-> +0x3C    S+0x78 <-> +0x48
S+0x18 <-> +0x20 (count)   S+0x1C/0x30/0x44 + 4i <-> the 12-byte item entries at +0x18
```

**The gate's 17 arguments**, from the dispatcher's pushes (`0x004A8C87`–`0x004A8CC1`)
and the compares at `0x008711F4`–`0x00871304`:

| arg | dispatcher reads it from | compared against | in the blob |
|---|---|---|---|
| +0x08 | `0x00815FF0()` | +0x34 | flag bit 9 |
| +0x0C | the in-map flag (`[ebp-0x5c]`) | — gates the next three | — |
| +0x10 | the map id (`0x0084D9C0` = ctx+0x44+0x230) | +0x2C, **in map only** | bytes 2–3 |
| +0x14 | `0x0084DCE0()` = ctx+0x44+0x384 | +0x30, **in map only** | bytes 4–7 |
| +0x18 | 16 bytes from the guild module (`0x0083FC00`, or zero) | +0x08..0x14, **in map only** | bytes 12–27 |
| +0x1C | the composite summary's first dword (`0x0082DCA0`, `CpsApi:460 summary`) | +0x00 | bytes 8–11 |
| +0x20 | `0x00815CF0()` = player+0x688 | +0x04 | flag bits 0–3 |
| +0x24 | the composite item count | +0x20 | byte 32 |
| +0x28/2C/30 | the three per-item arrays | each item's a, b, c | bytes 37+5i.. |
| +0x34 | `AvApi 0x007DF810`'s second out-value | +0x38 | flag bits 10–13 |
| +0x38 | `0x0080D5E0(agent)` = agent-table entry +0x2C | +0x28 | flag bits 4–8 |
| +0x3C | `0x00815EA0(3)`, `ChCliApi:5032 vis < CHAR_STATS_VIS` | **never compared** | flag bit 14 |
| +0x40 | player entry +0x34, bit 0 | +0x40 | flag bit 15 |
| +0x44 | ... bit 2 | +0x44 | flag bit 16 |
| +0x48 | ... bit 1 | +0x48 | flag bit 17 |

`+0x3C` is the one member the gate never reads: no `cmp` in `0x008711E0` touches
`[esi+0x3c]`, while the update path stores it (`0x00871378`). The three in-map-only
fields are neither compared nor stored when the flag is clear (`0x0087122C`,
`0x0087131E`), and the position/guild block is additionally skipped for maps whose
table flags carry `0x400` (`0x00871328`–`0x0087133F`).

### 22.2 The byte map, with §21.4's five bytes placed on it

| bytes | field | compared? |
|---|---|---|
| 0–1 | version 8 | (the unpacker's precondition) |
| 2–3 | `last_outpost` | in map |
| 4–7 | `tag` | in map |
| 8–11 | `appearance` (profession nibble at bits 20–23, `UiGame:613`'s bound) | **yes** |
| 12–27 | `guild_hall_id` | in map |
| 28–31 | flags: `campaign`:4 · `level`:5 · `is_pvp`:1 · `secondary`:4 · `helm_shown`:1 · three player-flag bits · **14 unwritten bits** | yes, **except bit 14 and bits 18–31** |
| 32 | `count` | **yes** |
| **33–36** | **unwritten, unread** | **no — not a field** |
| 37+5i | item i: u16 a, u16 b, u8 c | **yes, all three** |

**§21.4's bytes:** 33–36 (`ed 00 00 dc` served, `00 00 00 00` sent) are the unwritten
four; byte 59 is `item[4].b` (offset 37 + 5·4 + 2), compared in the loop at
`0x008712DB`–`0x008712E5`. So E and F served a blob that differed from the client's
own packing **only in positions the client never reads**, and G served one that
differed in one compared field. Both outcomes follow; nothing about the gate was
probabilistic. The whole map is executable: `toolkit/authsrv/charsummary.py`
(`decode`, `encode`, `differing`, `compared_differing`), tested on the run's own two
blobs by `test_charsummary.py` (50 checks).

### 22.3 Reconciled with the upstream layout — and one upstream name REFUTED

`studies/character/FINDINGS.md` already carried this record from three lineages
(OpenTyria's `GmChar.h`, gw-preservation's encoder, sgwlpr) as
`version:u16, last_outpost:u16, last_time_played:u32, appearance:u32,
last_guild_hall_id[16], {campaign:4 | level:5 | is_pvp:1 | secondary:4 | helm_status:2},
number_of_pieces:u8, trailing dword`. Against the packer:

* **Agree, now OBSERVED from the client rather than CORROBORATED across servers:**
  version, `last_outpost`, `appearance`, `last_guild_hall_id`, `campaign`, `level`,
  `is_pvp` (bit 9 — the bit gw-preservation's encoder skips and GWCA's
  `PreGameContext` reads), `secondary`, `number_of_pieces`, and the trailing dword
  being unread — with the addition that it is **unwritten** too, which is why every
  server lineage found it full of `0xDD`.
* **Refined:** `helm_status:2` is two bits from two different reads — bit 14 from
  `CHAR_STATS_VIS(3)`, bit 15 from the player entry's flags — and the gate compares
  15 but not 14. Bits 16–17 are two more player-flag bits no lineage names.
* **REFUTED — `last_time_played`.** The census below reads bytes 4–7 of retail's own
  served blobs as four-character C multichar constants: `'op1'` ×55, `'newb'` ×22 (the
  unpacker's own fresh-record default, `0x6e657762`), `'tuto'`, `'basi'`, `'vale'`,
  `'plai'`, `'lake'`, and decimal map ids — `'0164'` ×15, `'0449'` ×15, `'0242'`,
  `'0248'`, `'0148'`, `'0544'`, `'0281'` — each paired with `last_outpost` of the same
  number. Not a time. What it names is RECONSTRUCTION (a spawn-point tag, with the
  source map's id as the default text); that it is a tag is OBSERVED from 184 retail
  values. `authsrv.py`'s literal comment is amended, its bytes are not.

### 22.4 The census — every summary in the vault, ours and live apart

`python toolkit/authsrv/summarycensus.py` (origin-gated by each capture's own
`origin` record; the two are never pooled). Numbers, not bytes:

| | ours, served (v8) | ours, client-sent | live, served | live, client-sent |
|---|---|---|---|---|
| summaries | 6 | 525 | 161 | 23 |
| malformed | 0 | 0 | 0 | 0 |
| lengths | 62 | 62 ×366, 37 ×147, 47 ×12 | 62 | 62 |
| `level` | 3 | 1 ×451, 0 ×49, 3 ×19, 7 ×6 | 1 ×97, 3 ×31, 20 ×19, 2 ×14 | 20 ×8, 2 ×7, 1 ×6, 3 ×2 |
| `(level, campaign, is_pvp)` | (3,0,0) | (1,0,0) ×451 … | (20,0,1) ×19 — every level-20 is campaign 0 and pvp | (20,0,1) ×8 |
| `last_outpost` | 148 | 148 ×467, 143 ×40, 449, 165–167 | 164 ×70, 148 ×26, 242, 449, 248, 295, 544, 416 | 248 ×7, 148, 242, … |
| `helm_shown` | 0 | 0 | **1 ×161** | 1 ×23 |
| bytes 33–36 | `ed0000dc` | zero ×164, **251 more distinct** | `dddddddd` ×92, zero ×47, `148c0bdd` ×14, … | zero ×12, 10 others |
| flag bits 18–31 | 0 | 0 ×340, **92 more distinct** | `0xdddc0000` ×92, 0 ×54, `0x0adc0000` ×14 | 0 ×21, 2 others |

Four things this settles that the disassembly alone could not:

1. **The unwritten positions are the only place residue appears.** 251 distinct
   values of bytes 33–36 across our 525 client-sent blobs; every other byte position
   takes a handful of values that mean something. Retail's server fills them with
   `0xDD` (92 of 161) — and *only* them: the `0xdddc0000` in bits 18–31 is that fill
   with bits 16–17 overwritten by the packer's merge, which is the read-modify-write
   in §22.1 seen from the wire.
2. **`level` is the level.** Retail serves 20 exactly for the owner's level-20
   characters and 1–3 for the pre-Searing ones; our loopback character is 3 and the
   blob says 3; the 49 zeros and 6 sevens in our client-sent set are harness runs
   that spawned at those levels.
3. **`last_outpost` is where the client packed.** All 184 retail values are outposts;
   ours is 148, the loopback outpost.
4. **The literal's version 6 is converted, not rejected.** 1,459 of our served
   `CHARACTER_INFO`s carry the version-6 literal; every one of the 525 blobs a client
   sent back is version 8. `charsummary.decode` refuses anything but 8 rather than
   guess at the converter.

Our own served-vs-sent pair exists in exactly one capture (G's): `differing` =
`['unwritten', 'items']`, `compared_differing` = `['items']`. That is §21.4's
observation reproduced by the map with no free parameter.

### 22.5 What this closes, and what it does not

* **§21.4 CLOSED.** "The served blob is not compared wholesale" was right for the
  wrong reason: the blob *is* compared field by field, and the four bytes are not in
  any field. §20.1's baseline model stands as written — the served blob IS the
  baseline — with the unwritten positions excluded by construction.
* **§10's guard, from the store's side:** the store round-tripping residue is
  harmless (the unpacker never reads it) and `charstore` keeps serving the client's
  blob verbatim; nothing changes there. A future run that wants the settings write on
  demand has a cleaner lever than a byte flip: `charsummary.encode(...)` with any
  compared field changed.
* **NOT run:** the helm toggle. Bit 14 is uncompared, so toggling "show helmet" alone
  should not send `UPDATE_CHARACTER_SETTINGS`; how retail persists that toggle is
  another message or never — RECONSTRUCTION, and a one-gesture run would settle it.
* **NOT read:** the version converter `0x005EAFA0`, and what `tag` is called in
  ArenaNet's source.

### 22.6 A correction to §19.1's address, found on the way

§19.1 named the dispatcher `0x004A8A20` with three call sites (`0x004A6BAA`,
`0x004A7CB8`, `0x004A8464`). Aligned from that address, the stream shows a function
that ends at `0x004A8ACE` (`ret`, then a single `int3`) and **a second prologue at
`0x004A8AD0`** — and it is the second function that holds the gate call, the
serializer call and `UiGame:613`'s bound check. The three sites call the first, a
UI-control creator (it posts message `0x10000148` and sets `0xC07070/74/78`); the
summary dispatcher's direct callers are **two**, `0x004A6FE8` and `0x004A7836`
(`codescan --xrefs`). §19's chain, gate and polarity are untouched — they were read
from the right bytes — only the function's start and its caller count move.
`studies/profession/MODDABLE.md` §5.1's row `0x004a8a20 3 UiGame character summary`
carries the same off-by-one (its `func_start` walked past a single `int3`); amended
there in place.
