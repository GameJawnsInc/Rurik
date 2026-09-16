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
