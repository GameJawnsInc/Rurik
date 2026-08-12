# The loopback opcode sweep — what 89 of 487 GAME_SMSG opcodes do

**Status: OBSERVED, 2026-08-12.** Our own server sends each catalogued opcode ArenaNet has
never shown us to a client we control on 127.0.0.1, and the client's reaction is the
measurement. Method and every refusal: `toolkit/authsrv/smsgsweep.py`. Readout controls:
`toolkit/authsrv/test_smsgsweep.py` (58 checks). Driver: `toolkit/authsrv/sweeploop.py`.

## 0. Where it stands

| | count | of |
|---|---|---|
| measured | **89** | 487 catalogued |
| ASSERTED — stops the client | **20** | |
| REPLIED — client answered | **1** | |
| SILENT | 68 | |
| remaining to plan | 237 | of the 324 never-seen |

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

## 2. The twenty that stop the client

Each localised to ONE opcode. **The constraint is ours; ArenaNet's assert text stays in
the vault** (`vault/captures/harness/*/crash-dialog.txt`), per `CLAUDE.md`'s provenance
boundary — a derived table may carry the constraint and must leave the expression out.

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
| `0x005F` `0x0060` `0x006F` | crash localised, **assert text NOT read** — see §4 | — |

`0x0038`–`0x003B` are four consecutive opcodes sharing one constraint, which is the
strongest structural hint in the table: a family of four attribute messages.

## 3. The one reply

`0x0000` → the client answers c2s `0x0000`, at 10 ms, reproduced in three runs, the last
with a clean control window holding only the idle-floor ping.

**CONTESTED, and it stays contested.** `0x0000` is always the FIRST opcode in plan order,
so "reply to `0x0000`" and "reply to the first message of the sweep" are not separated.
One run with the plan reordered settles it. Do not quote this as a binding until then.

## 4. What this does not establish

* **68 SILENT means silent on an all-zero payload.** A handler that early-outs on a zero
  id is indistinguishable here from one that does nothing. It is NOT evidence of a
  missing handler: all 477 receive-table entries carry a non-null dispatch pointer
  (`toolkit/clientscan/test_msghandler.py`).
* **Three asserts have no text.** `0x005F`, `0x0060`, `0x006F` are localised to one opcode
  each by the same method as the rest, but their dialogs were captured without the detail
  pane expanded, so the constraint is unknown. The crash is real; the readout missed it.
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

## 6. Next

1. **The zero-branch pass.** Every ASSERTED row is a gate. `--only <op> --set N=1` walks
   the other side, one field at a time. `0x0017` is done; nineteen to go.
2. **Reorder the plan** so `0x0000` is not first, and settle §3.
3. **Recover the three missing asserts** — re-send `0x005F`, `0x0060`, `0x006F` and expand
   the dialog's detail pane before reading it.
4. **Finish the 237.** `sweeploop.py --rounds 20` did 71 opcodes and 20 asserts in about
   35 minutes; yield falls as the asserts cluster, so budget more rounds than opcodes.
5. **The ten table-less opcodes**, `--table-less --limit 1`, deliberately.
