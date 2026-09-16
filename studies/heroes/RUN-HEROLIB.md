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
