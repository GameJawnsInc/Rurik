# The loopback opcode sweep — COMPLETE: 334 of 487 GAME_SMSG opcodes

**Status: OBSERVED, 2026-08-12.** Our own server sends each catalogued opcode ArenaNet has
never shown us to a client we control on 127.0.0.1, and the client's reaction is the
measurement. Method and every refusal: `toolkit/authsrv/smsgsweep.py`. Readout controls:
`toolkit/authsrv/test_smsgsweep.py` (58 checks). Driver: `toolkit/authsrv/sweeploop.py`.

## 0. Where it stands

| | count | of |
|---|---|---|
| measured | **324 of 324** | the whole never-seen set |
| ASSERTED — a guard the client wrote caught it | **82** | |
| FAULTED — access violation, no guard at all | **3** | |
| DROPPED_CHANNEL — client re-established and kept playing | **1** | |
| REPLIED — client answered | **3** | |
| SILENT | 235 | |
| DISCONNECTED — transport closed the channel | **6** | the ten table-less, §2c |
| remaining | **0** | the loop stopped on "nothing left to plan" |

Plus the ten opcodes with no receive-table entry, taken deliberately one per run (§2c),
for **334 of 487** measured in total.

**86 crash rows, every one paired to the dialog its own run captured — no gaps.**
Every reading was taken in map 148 with the player alive and the map quiet; `record`
refuses a connection that fails either, and one row measured in map 0 was removed.

The 155 opcodes ArenaNet has sent us are excluded (rebuilt from the tapes by
`--write-seen`: 155 over 12 live connections). So are the ten with no receive-table entry.

## 1. The result that changes how the rest is read

**The degenerate payload is not stumbling into crashes. It is selecting a branch.**

`0x0017`'s handler (`0x00804640`) marshals five dwords — matching the catalogue's five
fields exactly — into `0x00807d90`, which **tests the fifth field against zero and skips a
whole resource load when it is non-zero.** On zero it calls `0x00633d70` with a hardcoded
resource id `0x100000be` and the client asserts below that, in its file layer.

Read out of the binary, then predicted, then confirmed on the wire:

| `0x0017` field 5 | result |
|---|---|
| 0 | ASSERTED — twice, once with the map's hostile and once without |
| 1 | SILENT, client alive |

So every assert below marks **a field whose zero value means something**, and a second
pass with that field set explores the other side of the same gate. That reframes the
whole ASSERTED column from "opcodes we cannot send" into a list of field bindings.

The attribution is not statistical. The crash dump is rebased +0x30000 (`BaseAddr`
`00430000` against an image base of `00400000`) — confirmed rather than assumed, because
the opcode bytes at the dump's `004B7BC0` match static `00487BC0` and the one differing
dword is a relocated absolute operand, `0xbf4440` → `0xc24440`. With that delta, two trace
frames resolve to `0x00804668` and `0x00807dd5`: the return addresses inside `0x0017`'s
own handler and its callee. **The client's own stack names the opcode.**

## 2. The twenty that stop the client — seventeen asserts and three faults

Each localised to ONE opcode. The constraint below is in **our words**, and §2b says why:
not because citing ArenaNet's assert text is refused — `PLAN.md` §7 Q3, refined
2026-08-12, rules that a single assert cited as evidence is a MEASUREMENT and that the
crash dialog is not extraction at all — but because 86 rows is the ACCUMULATION that
`toolkit/provlint.py` exists to stop. Raw text: `vault/captures/harness/*/crash-dialog.txt`.

| opcode | what the payload must satisfy | so the field is |
|---|---|---|
| `0x0017` `0x0019` `0x00A8` | an id reaching the archive's file layer is rejected; zero is not a valid one | a **file/resource id** |
| `0x0023` | a pointer looked up from the payload comes back null | an **object id** |
| `0x0024` `0x002F` | a synchronisation object looked up from the payload comes back null | a **sync/session handle** |
| `0x0033` `0x009E` | the first code unit of an encoded string is below the encoding's base value | an **encoded string** |
| `0x0038` `0x0039` `0x003A` `0x003B` | no attribute-state record exists for the value sent | an **attribute id** |
| `0x0072` | no hero record exists for the value sent | a **hero id** |
| `0x0083` | an inventory bag count is out of bounds | a **bag index or count** |
| `0x0096` | at least one of two mission-completion flag bits must be set; zero sets neither | a **completion-flag mask** |
| `0x0097` | the value selects a switch arm and zero is not one of them | a **closed enum** |
| `0x009D` | no agent exists for the id sent | an **agent id** |
| `0x005F` `0x0060` `0x006F` | no assert at all — the client takes an **access violation** | an unguarded dereference |

`0x0038`–`0x003B` are four consecutive opcodes sharing one constraint, which is the
strongest structural hint in the table: a family of four attribute messages.

## 2b. The constraint census — 86 crash rows, and it maps the catalogue

Grouped by the constraint each opcode's guard enforces, **in our words**. The clustering
is the finding: these are not scattered.

*Why paraphrased, corrected 2026-08-12 — and not for the reason first written here.* This
table originally said the assert text "stays in the vault" as though citing it were
refused. It is not: `PLAN.md` §7 Q3 was refined the same day to rule that **a single
assert cited as evidence is a MEASUREMENT**, that the refusal targets bulk dumps and
decompiled bodies, and that the crash dialog — text the retail client shows any player
who crashes — is not extraction at all. What actually governs 86 rows is the
ACCUMULATION tripwire `toolkit/test_provlint.py` enforces: 10 citations for a new
document, 200 tree-wide against 136 used. Eighty-six is the bulk the rule still means,
so the paraphrase stands — by that limit, not by a prohibition that does not exist. The
raw text is in `vault/captures/harness/*/crash-dialog.txt`, and citing a few of these
individually as evidence is permitted if a later argument needs them.

| n | what must exist / hold | opcodes |
|---|---|---|
| 10 | a **party** record | `0x01C4` `0x01C5` `0x01C6` `0x01C7` `0x01C8` `0x01C9` `0x01CC` `0x01CD` `0x01CE` `0x01D1` |
| 8 | an **inventory** record the payload names | `0x0141` `0x0142` `0x0145` `0x0146` `0x014F` `0x0150` `0x0151` `0x0153` |
| 6 | an **index within a count** — a bounds check on an array | `0x0174` `0x01A1` `0x01AC` `0x01AE` `0x01E1` `0x01E2` |
| 2 | a **skill bar** | `0x01A2` `0x01A3` |
| 6 | an **item** record | `0x0137` `0x0139` `0x0155` `0x0156` `0x0159` `0x0160` |
| 7 | a valid **encoded string** — first code unit at or above the encoding's base | `0x0033` `0x009E` `0x00B9` `0x00C0` `0x017A` `0x019C` `0x01D4` |
| 7 | a loadable **file id** | `0x0017` `0x0019` `0x00A8` `0x00A9` `0x01A4` `0x015F` `0x0162` |
| 4 | an **attribute state** record, reached through the agent | `0x0038` `0x0039` `0x003A` `0x003B` |
| 3 | a non-null **object pointer** | `0x0023` `0x0163` `0x0169` |
| 3 | a **bag** record | `0x0143` `0x0149` `0x014E` |
| 3 | *(no guard — access violation)* | `0x005F` `0x0060` `0x006F` |
| 2 | a **sync/session object** | `0x0024` `0x002F` |
| 2 | a **skill** record | `0x00D1` `0x00D2` |
| 2 | a **guild** record | `0x0118` `0x011E` |
| 1 each | agent, hero data, bag count, mission-completion mask, a closed enum, a game-view frame, a result value, a byte buffer, a non-empty accumulator list, a boss count, two skills that must differ, an upgrade item id, a tournament record, an index within a count, and one whose text is empty | `0x009D` `0x0072` `0x0083` `0x0096` `0x0097` `0x00AB` `0x00AD` `0x00B5` `0x00C5` `0x00D4` `0x00D6` `0x016A` `0x0173` `0x0174` `0x0109` |

**Two contiguous functional blocks fall out of this, and neither cost a live capture.**
`0x0137`–`0x0163` is the **inventory and item** block — 17 crash rows in one stretch, so a
server handing a player an item works exactly there. `0x01C4`–`0x01D1` is the **party**
block — 10 rows, nearly consecutive, and the single largest constraint group in the table.
Both were invisible before this sweep: the static assert map names a source file for only
63 of 477 handlers and says nothing about what a payload must satisfy.

`0x019B` is its own result: it made the client **close the game channel and open a new one
42 ms later**, still running, taking the whole plan again. It is the only DROPPED_CHANNEL
in the set.

## 2c. The ten with no receive-table entry — the family SPLITS

Taken deliberately, one opcode per run, each run a fresh client, each read by shape
because the automatic attributor refuses them by design (a one-send run ending in a close
cannot be told from a harness kill by the capture alone).

| opcode | result |
|---|---|
| `0x000A` `0x000C` `0x000D` `0x000E` | **survived** — client kept answering, ~37 c2s messages after |
| `0x000B` `0x004F` `0x0055` `0x007F` `0x014A` `0x01DA` | **DISCONNECTED** in 2–16 ms |

The disconnect is a **transport-level session error, not a crash**: no assert, no dialog,
`Code=007` on screen and the client alive at character select. That is what "handled below
the message table" looks like from the wire.

**`0x000C` is the control and it is the reason this table means anything.** It is the ping
request the client demonstrably answers (`toolkit/authsrv/test_ping.py`), it has no
receive-table entry, and it survived with 38 c2s messages behind it. So *absent from the
table* does not imply *dangerous* — the family splits 4 to 6, and the earlier assumption
that all ten were channel-killers was wrong. `0x000B`, which ended the pilot, is the odd
one out of an otherwise benign low block.

## 2d. 174 of 477 handlers are a shim over ONE event bus

Found by following `0x0166`'s handler and noticing it was three instructions. Swept over
the whole receive table: **174 of 477 handlers do nothing but push a `0x1000xxxx` id and
call `0x00633d70`.** Event ids run `0x10000006`..`0x10000169`, 149 distinct, 15 shared by
more than one opcode. The map is at `vault/probes/smsgsweep-eventids.json`.

    0x0017 -> 0x100000BE     0x0033 -> 0x10000028
    0x0166 -> 0x10000100     0x0167 -> 0x10000101

Those four were disassembled by hand first and the sweep reproduces all four exactly,
which is the only reason to believe the other 170.

So a third of the GAME_SMSG table is not "message handling" at all — it is a **thin
adapter posting a UI event**, and the real behaviour lives in whatever consumes the id.
Adjacent opcodes post adjacent ids (`0x0166`/`0x0167`), so the id space is itself ordered.

**AND THE OBVIOUS PREDICTION IS WRONG, which is why it is worth writing down.** A shim
that posts an event with an empty payload ought to be more likely to do nothing visible.
It is not:

| | shim (138 measured) | not a shim (196) |
|---|---|---|
| SILENT | 73.9% | 69.9% |
| ASSERTED | 23.9% | 25.0% |

Essentially identical. Being a shim predicts nothing about what the wire does — the guard
that asserts lives *below* the dispatcher, in the consumer, and fires just as often.

A weaker observation, recorded as weak: all three REPLIED opcodes are shims (3 of 138
against 0 of 196), and no shim ever faulted or ended a session. With three replies in
total that is a lean, not a result, and it needs the other 153 opcodes to test.

## 3. The replies

### 3.1 `0x0166` and `0x0167` → c2s `0x0079` — the first clean binding

Both draw an **empty** c2s `0x0079` (header only, no payload fields) within 10 ms.
Replicated in two independent runs, and the second was built as a controlled experiment:

| sent | run 1 | run 2 (replication) |
|---|---|---|
| `0x0164` | silent | silent |
| `0x0165` | silent | silent |
| **`0x0166`** | **→ `0x0079`** | **→ `0x0079`** |
| **`0x0167`** | **→ `0x0079`** | **→ `0x0079`** |

The two silent sends immediately before are internal negative controls, and they also
kill the first-send confound below: `0x0166` was not the first message of either run.
Both control windows held nothing but the idle-floor ping.

Two adjacent opcodes eliciting one empty acknowledgement is the shape of a request/ack
pair. **What they ask for is not established** — only that the client answers.

### 3.2 `0x0000` → c2s `0x0000` — the confound is dead, this is a binding

Reproduced in three runs, but `0x0000` is always the FIRST opcode in plan order, so
"reply to `0x0000`" and "reply to the first message of a sweep" were not separated.

**Settled 2026-08-12 by `--plan --reverse`**: sent THIRD, behind `0x0165` and `0x0164`
which both stayed silent in the same run, `0x0000` still drew c2s `0x0000`. The reply
belongs to the opcode, not to the position. Promoted from CONTESTED to a binding.

### 3.3 What `0x0166` and `0x0167` actually do

Their handlers are the thinnest in the set, and they post to the SAME dispatcher
`0x00633d70` that `0x0017` calls:

    0x0166  ->  0x633d70(0x10000100, NULL, 0)      no message field is read at all
    0x0167  ->  0x633d70(0x10000101, &field1, 0)   field 1 passed by pointer

Adjacent opcodes post **adjacent event ids**, which is why they pair and why both acks
are empty. `0x0017` posts `0x100000be` through the same door. So a slice of the GAME_SMSG
table is a thin shim over one client-side event bus, and the `0x1000xxxx` space is its id
range — which is a structural fact about the client, not about any one message.

## 3.4 Four opcodes NAMED — and the readout's blind spot, demonstrated

Feeding a real encoded string from the corpus (read at run time, never committed) into
the seven string-gated opcodes opened four of them: `0x0033`, `0x009E`, `0x00B9`, `0x00C0`
went from ASSERTED to SILENT. **They were not silent.** Re-run one per run with
`--shots 2`, each produced an obvious and DIFFERENT visible effect:

| opcode | what the client did | evidence |
|---|---|---|
| `0x0033` | opened a window whose own title bar reads **Message of the Day**, body = our string | the client's own words, so this is a NAME and not an inference |
| `0x009E` | printed a **chat line** in Local, `sender: body`, both filled from our string — matching its `agent_id, string16, byte, string16` layout | chat panel |
| `0x00B9` | placed a **framed, closable callout** in the world with our string in it | box + close button, anchored in 3D |
| `0x00C0` | placed **unframed floating text** in the world — no box, no control | bare label |

`0x00B9` and `0x00C0` both put text in the world and are told apart by the frame; neither
is given a formal name here because the client never spelled one out.

**THE BLIND SPOT IS NOW MEASURED, NOT HYPOTHETICAL.** `SILENT` has always meant *the
client sent no c2s message*, and §4 said so — but four of four opcodes tested with a
meaningful payload changed the screen while the wire stayed quiet. A UI update produces
no network traffic, so the instrument cannot see it **by construction**. The 239 SILENT
rows are a statement about the wire and nothing else, and an unknown fraction of them did
something a person watching would have seen.

**OPERATOR REPORT, 2026-08-12, and it widens this from four rows to the whole sweep:**
the client was producing visible UI throughout the sweep runs, not only in the four
isolated above — the operator was watching it happen and chose not to interrupt a run in
progress to tally it. So the blind spot is not a property of these four opcodes or of the
encoded-string family; it applied to every round this instrument ever scored. Labelled
OBSERVED (operator) rather than MEASURED, because no capture of ours recorded it and the
screenshots only exist for the four.

That is also the cheapest remaining upgrade to this whole apparatus: `--shots` plus one
opcode per run turns SILENT rows into named behaviour, and it needs no new decoding.

## 4. What this does not establish

* **SILENT MEANS NO c2s REPLY. IT DOES NOT MEAN NOTHING HAPPENED** — see §3.4, where
  four of four opcodes scored SILENT were opening windows and printing chat.
* **235 SILENT means silent on an all-zero payload.** A handler that early-outs on a zero
  id is indistinguishable here from one that does nothing. It is NOT evidence of a
  missing handler: all 477 receive-table entries carry a non-null dispatch pointer
  (`toolkit/clientscan/test_msghandler.py`).
* **CORRECTED 2026-08-12, and the first version of this line was wrong.** It said the
  dialogs for `0x005F`, `0x0060` and `0x006F` had been captured with the detail pane
  collapsed. They had not — all three say `Exception: c0000005`, an access violation, and
  had done from the moment they were written. The reader only ever grepped for the word
  Assertion, so a whole class of result was invisible by construction and got explained
  away as a capture failure. **An assert and a fault are different findings**: an assert
  names a condition ArenaNet chose to check, a fault means nobody checked. The readout
  classifies both now (`smsgsweep.crash_kind`).
* **One state, one map.** Every reading is a level-1 character standing in one map with
  nothing in progress — no party, no quest, no trade, no combat (`--no-enemy`; see §5).
  An opcode silent here may not be silent mid-mission.
* **Nothing here is a live observation.** Both endpoints are ours. This says what the
  CLIENT does with a message, never that ArenaNet's server sends one.

## 5. Two contaminations found and removed, both silent

**The map was not quiet.** The default world spawns a hostile that killed the player at
t=7.4 and revived at t=17.4, on a ~13 s cycle, and every sweep send landed between a kill
and a revive. Sixteen `SILENT` readings meant "silent on a corpse" and the ledger said
`SILENT`. The `0x00F1` messages were in the capture the whole time; nothing read them.
`record()` now refuses such a run outright. The control run with `--no-enemy` reproduced
`0x0017`'s assert on a live player, so the contamination was of the readings and not of
that attribution. **Found because the operator said what was on screen** — no automated
check was looking.

**The socket lied about when the client died.** A Guild Wars assert leaves the process
ALIVE behind a modal dialog: message pump stopped, socket open. Measured 31.6 s, then
120.8 s, then 30.1 s of silence before the reset arrived. Fencing on the connection scored
**78 opcodes SILENT against a client that was showing a crash dialog** and wrote all 90 to
the ledger. The fence is now the client's own reply to our ping, and a crash belongs to a
window of suspects rather than to the last opcode sent — which had named `0x00A9` when
the assert was near `0x0012`, seventy-eight sends earlier.

Localisation is a measured property, not a constant: at ArenaNet's 5.000 s ping cadence a
crash names twelve opcodes. `authsrv --ping-seconds 0.5` with a dwell of 0.8 names one.

## 5b. The zero-branch pass — the agent_id family

The gate for every opcode whose FIRST field is an `agent_id`, tested by re-sending it with
that field set to the player's live agent id and nothing else changed. Nine opcodes:

| result | opcodes | reading |
|---|---|---|
| **gate was the agent id** — now SILENT | `0x0038` `0x0039` `0x003A` `0x003B` `0x006F` `0x009D` | the whole crash was the missing agent |
| **a SECOND gate behind it** | `0x0083` (bag index still 0), `0x009E` (its string16 still empty), `0x005F` (still faults) | field 1 was necessary, not sufficient |

Six of nine gates closed with one value. **The prediction was half right and both halves
are worth keeping:** `0x009D` was predicted to stop asserting and did; the four
`attribState` opcodes were predicted to keep asserting on their still-zero attribute id
and did NOT — so the attribute state is reached THROUGH the agent, not looked up beside
it. That is a structural fact the assert text alone did not give.

`--set` refuses an index whose declared type differs across the planned opcodes, because a
field index is not a field: `--set 1=1` over these nine is one experiment, and over a
mixed plan it would be nine unrelated ones sharing a report. `--set 0x0083:2=1` names one
opcode and needs no such agreement, which is what lets several second-gate experiments
share one client launch.

## 5c. Where a plausible value was NOT enough — and why guessing stopped

Five more opcodes, each re-sent with the field its assert pointed at set to something
defensible. **None of them opened**, and that is the result:

| opcode | tried | still |
|---|---|---|
| `0x005F` | field 1 = live agent, field 2 = 1 | FAULTED — its field 3 is a `string16`, so it belongs to the encoded-string family below |
| `0x0072` | field 2 = live agent | ASSERTED — so hero data is NOT reached through the agent; its `word` field 1 is the index |
| `0x0083` | field 1 = live agent, field 2 = 1 | ASSERTED — a third gate, its `dword` field 3 |
| `0x0096` | field 1 = 1 | ASSERTED — the mask wants specific bits and bit 0 is not one of them |
| `0x00A8` | field 3 = 1, then = `0x100000be` (a real resource id from `0x0017`'s path) | ASSERTED — so field 3 is not the file id, or neither value names a loadable file |

**Six of fifteen gates closed on a value we could justify; the other nine did not, and the
next attempt on each would be a guess costing a client launch.** `0x0017` was solved by
reading its handler and predicting the gate before sending anything — that is the method
that worked, and it is the one these nine want. `msghandler.py <op> --follow --annotate`.

A limit found while doing it: `--set` indexes into the VALUE list, and `degenerate` stops
at a `nested_struct` because that type swallows the tail. `0x0019` declares four fields
and has three values, so its file id — likely inside the struct — is out of `--set`'s
reach entirely.

## 5d. The handler reads — and the wall they found

Thirteen chains disassembled (`msghandler.py <op> --follow`). Two things came out of the
handler's OWN marshalling, which is measured rather than inferred:

* **`0x0072` pushes only `msg+0xc` and `msg+0x10`** — fields 3 and 4. It never reads the
  `agent_id` at field 2, which is why setting that field did nothing.
* **`0x0096` pushes `msg+0xc`, `+0x10`, `+0x14`** — fields 3, 4, 5. Field 1, which the
  first attempt set, is not read at all.
* **`0x0083` carries a bound of 5** (`cmp eax, 5 / ja` at `0x008118b6`): a six-element
  array, which is the shape of a bag list.

**And then all of them still asserted on the fields the handler does read.** That is the
result, and it is not a failure of the method — it is the answer:

> **These are not payload gates. They are CLIENT-STATE gates.** `charHeroData` wants a
> hero record; this character has no heroes. The completion-flag mask wants a mission
> already finished; nothing is finished. `bagCount` wants bags past the starter. The
> `ptr`/`syncPtr` pair want objects this session never created. **No value on the wire
> opens them**, because the thing being looked up does not exist in a level-1 character
> standing in one map with nothing in progress.

This is §4's "one state, one map" caveat arriving as a measurement instead of a warning.
Reaching these opcodes needs a client with the state, not a better payload — which makes
them a task for a live capture or a much richer server, not for the sweep.

**A methodological correction.** The first pass of this read labelled `[ebp+0xc]` inside
any followed function as "message field 2". That mapping only holds for the handler's
DIRECT callee, which receives the marshalled fields; functions further down take their own
arguments. `0x0023`'s zero-test at `0x0046ed53` was labelled that way, predicted to be the
gate, and was not. The handler's own `push dword ptr [eax + N]` list is the measured part;
anything deeper is inference and is marked as such above.

## 6. Next

1. **The zero-branch pass is CLOSED for the state-gated opcodes** — see §5d; they need a
   client that has heroes, missions and bags, not a better payload. What remains open: Done: `0x0017` (field 5), and the nine-opcode
   `agent_id` family in §5b. Left: the `string16` gates (`0x0033` `0x0060` `0x0097`
   `0x009E`) need a REAL encoded string, which `--set` deliberately will not fake; the
   file-id gates (`0x0019` `0x00A8`); `0x0096`'s flag mask; `0x0072` (`--set 2=`, its
   agent_id is field 2); and the three faults.
2. **Reorder the plan** so `0x0000` is not first, and settle §3.
3. **Recover the three missing asserts** — re-send `0x005F`, `0x0060`, `0x006F` and expand
   the dialog's detail pane before reading it.
4. **Finish the 237.** `sweeploop.py --rounds 20` did 71 opcodes and 20 asserts in about
   35 minutes; yield falls as the asserts cluster, so budget more rounds than opcodes.
5. **The ten table-less opcodes**, `--table-less --limit 1`, deliberately.

---

## 7. The SCREEN pass — 238 SILENT opcodes re-sent one per client, with screenshots

**Status: OBSERVED, 2026-08-13.** §3.4 measured this instrument's blind spot: `SILENT`
means *no c2s reply*, and four of four opcodes tested with a meaningful payload were
drawing windows while the wire stayed quiet. This is the conversion of the other 239.
Method: `toolkit/authsrv/shotloop.py` (one opcode, one FRESH client, a screenshot every
second through a 22 s hold), read by `toolkit/authsrv/shotlabel.py`, controls in
`test_shotlabel.py` (38 checks). 162 minutes, 238 runs, **zero harness failures**.

**One opcode per client launch, and it is a rule rather than a budget.** A window an
earlier opcode opened is still on screen when the next one lands, so it sits inside the
next opcode's own baseline frame; and an opcode may only act BECAUSE of state a previous
one left, which would report a joint effect under one name. `score_run` refuses a
multi-send run outright.

### 7.1 What came back

| | count |
|---|---|
| scored | **221** |
| CHANGED — the screen moved beyond its own drift | **34** |
| QUIET | 187 |
| CRASHED — dialog captured, §7.3 | **8** |
| lost the foreground, re-run | 9 |

### 7.2 The three read so far, and two are NAMED by the client's own words

Read by eye off the page, which is what this apparatus is for:

| opcode | what the client did |
|---|---|
| `0x0101` | the screen goes black and reads **"A Cinematic is in Progress"** — the client's own text, so this is a NAME |
| `0x00C3` `0x00C7` `0x00C8` `0x00C9` `0x00CA` | a modal dialog whose body text is the **account-name / ladder** prompt, with `Accept Name` and `Goodbye` buttons. Five opcodes, one contiguous block, all five scoring 11.10–11.16% over the SAME bounding box (715, 276, 1191, 783) — a family |
| `0x006C` | a large golden burst centred on the player: a world EFFECT, not a panel |

`0x0101` at 94.99% and `0x01AA` at 88.13% both repaint essentially the whole window
(bbox (8, 31, 1928, 1032)); `0x01AA` has not been read yet.

### 7.3 EIGHT OPCODES CRASH — and the wire sweep scored every one of them SILENT

The eight `UNSCORABLE` rows are frames that changed SIZE mid-run, from 1936x1040 to
646x237, **all eight at the same frame index**. That is the client window being replaced
by its error dialog, and `capture_error_dialog` caught all eight:

| opcode | the client's own assert | subsystem |
|---|---|---|
| `0x0105` | `context->script`, `Cinematic\Cli\CiCliApi.cpp(201)` | **cinematic** |
| `0x0122` `0x0125` `0x0126` `0x0130` | `guild`, `GuCliApi.cpp` lines 340, 363, 384, 420 | **guild** |
| `0x0170` | `IsBatching()`, `MsCliTourn.cpp(475)` | **tournament** |
| `0x0172` `0x01B7` | `index < m_count`, `Base\rtl\Array.h(587)` | a bounds check |

**The difference is the encoded string.** The wire sweep sent all-zero payloads; this
pass runs `--encstring`, which puts a REAL encoded string from the owner's own captures
into `string16` fields. So these eight are §5c's "second gate" arriving from the other
side: with the string field valid the handler runs on past its format check and reaches
a CLIENT-STATE gate — no guild, no cinematic script, no tournament batch. §5d's reading
holds and now has eight more instances.

**A contiguous guild block at `0x0122`–`0x0130`** joins §2b's inventory block
(`0x0137`–`0x0163`) and party block (`0x01C4`–`0x01D1`). The census had two guild
opcodes; this makes six, four of them with a line number.

### 7.4 What this does not establish

* **A changed screen is not a named opcode.** The score says pixels moved; whether they
  moved because of this opcode is a judgement, and 34 rows are evidence awaiting a
  reader. Only the three in §7.2 have been read.
* **QUIET is not "nothing happened" either**, for a weaker version of the same reason:
  an effect smaller than the client's own drift, or one that fades between two frames,
  is under this instrument's floor. `0x00C0`'s floating text was measured doing exactly
  that at a 2.3 s cadence, which is why this pass runs at 1 s.
* **Still one state, one map.** Level-1 character, empty map, `--no-enemy`. Every §5d
  caveat applies unchanged.

### 7.5 `0x0191` is a SECOND `DROPPED_CHANNEL`, and it is why one row has no reading

`0x0191` is the one opcode of the 239 with no usable run, and the reason is the result.
Both of its attempts were REFUSED by `shotloop` because the capture held **two** sends of
it — and the second send is the client's doing, not the loop's:

| | run 1 (`20260813T142120`) | run 2 (`20260813T151705`) |
|---|---|---|
| our send | t = 13.5 | t = 13.5 |
| game channel gone | t = 26.436 | t = 25.963 |
| reopened | t = 26.500 | t = 26.028 |
| second gamesrv capture | `…-c2` | `…-c2` |

The client tore the game channel down about **12.6 s after the send**, opened a new one
64–65 ms later, and re-ran the spawn — at which point our probe, which fires on spawn,
sent `0x0191` again on the new connection. **Two of 240 runs did this and both are
`0x0191`**; the consistent offset across two independent runs is what makes it
attributable rather than a coincidental timeout.

That is the shape §2b records for `0x019B`, so the set now has **two** DROPPED_CHANNEL
opcodes rather than one — and like the eight crashes of §7.3, `0x0191` was scored SILENT
by the wire sweep on an all-zero payload and only behaves this way with a real encoded
string.

**It is UNMEASURED on the screen and stays that way honestly.** A run whose probe fires
twice cannot attribute a screen change to one send, so `score_run` refuses it, and no
picture of `0x0191` is claimed. Reading it needs a probe that fires once per SESSION
rather than once per spawn — which is a change to `authsrv.run_probe`, not to this pass.

**READ 2026-08-13, and §7.5's closing paragraph above is now WRONG in the useful
direction — `0x0191` CHANGES THE MAP.** The operator said one of the runs had switched
maps; scored against the baseline before the send, the third attempt
(`20260813T153707`) reads:

| frame | vs baseline | what it is |
|---|---|---|
| +0.5 s | 0.26% | still the courtyard |
| +1.7 s → +5.6 s | **93.73%** | a load screen |
| +8.3 s → +12.2 s | **75.25%** | a DIFFERENT map — stone stairway and canyon wall, not Ascalon City's courtyard, with a different compass |

So every part of the anomaly is one behaviour. The full-window repaint is the map load;
the channel teardown at ~12.6 s and the reopen 65 ms later are the client connecting to
the **new instance**; and the second send is our own probe firing on the new instance's
spawn, because `run_probe` fires per SPAWN. Nothing here is contamination — it is the
opcode doing something the sweep had no way to name from an all-zero payload.

**The score is attributable even though the run has two sends**, because the second one
is 16 s after the first and every frame above precedes it. What `score_run` refuses is
the general case, and rightly: it cannot know that in advance. The reading is recorded
here by hand rather than by loosening that refusal.

`0x0191` is therefore a **map/instance change**, which makes it the most consequential
row of this pass: it is the first opcode found that moves the player between maps, and
`PLAN.md` §3.6's capture campaign wants exactly that.
