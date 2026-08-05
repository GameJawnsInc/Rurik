# The message format tables, recovered from the client binary

Build 38797. Static analysis of `vault/run/2026-07-29_221c13772c7a/Gw.exe` as a file — the
client was never launched, no debugger attached, no process memory read.

This study replaces `schema/messages.json`'s provenance note ("NOT authoritative. The arbiter
is the client's own packet-template table, not yet dumped") with the dumped table.

## Labels used throughout

| Label | Meaning |
|---|---|
| **SOURCED** | Measured in the binary's bytes. The offset or VA is given so you can re-read it. |
| **INFERRED** | Our reading of measured bytes. The bytes are real; the interpretation is ours. |
| **UPSTREAM** | A reconstruction says it. Not ground truth, and repeatedly wrong below. |
| **NOT ESTABLISHED** | We looked and could not settle it. Listed in §11 rather than glossed. |

The house rule matters more here than usual, because this task *has* ground truth. Where a
reconstruction and the binary disagree, the binary wins and we say so by name.

---

## 1. The answer in one page

**Found, verified, and complete.** The client's message-format tables are in the binary, they
were recovered in full, and they reproduce all four known-good message shapes exactly.

The way in was that Gw.exe still carries ArenaNet's own `assert()` expression strings,
including the source path `P:\Code\Net\Msg\MsgChannel.cpp`. Those strings name the real data
structures — `cmds[i]`, `MSG_FIELD_COUNT_GET(*cmd)`, `msgs[i].count`, `src->dispatch`,
`channel->m_sendMsgs.Count()` — and their code cross-references lead straight to the parser.

The headline results:

- A field descriptor is **one packed dword**, not the `{type, length}` pair every
  reconstruction models. `cmd = (count << 8) | (log2_elem_size << 4) | type`.
- There are **two descriptor structs**, not one: 12-byte receive `{cmds*, count, dispatch}`
  and 8-byte send `{cmds*, count}`. Neither has a `header` member and neither stores an
  unpack size. OpenTyria's `MsgFormat{header, count, fields, unpack_size}` is wrong on both
  member set and size.
- There are **two channels**, not four catalogs, each with a send and a receive opcode space.
  **751 messages** are registered across 25 tables by 14 calls to one registration function.
- The **0x8000 bit is not a channel mask.** It is a runtime framing flag on the send path. No
  opcode in any table has it set.
- **Oracle: 4 of 4 pass.** `0x001E` → 6 bytes, `0x0029` → 18, `0x002C` → 16, `0x0020` → 23
  fields / 99 bytes, all reproduced from the recovered tables.
- Against our 777-message catalog: **744 of 748 shared messages agree field-for-field**. Four
  disagree, one of which is the correction we had already proven from a live capture — the
  binary rediscovered it independently. Three messages exist in the client that we are blind
  to. Twenty-nine entries we carry are upstream padding for opcodes the client never registers.
- **The +2 opcode drift does not apply to us.** Measured alignment against build 38797 is
  **delta = 0 on all four channels**. The drift documented in `studies/movement/FINDINGS.md`
  is GWCA-versus-ldufr; our catalog is on the same lineage as this build. Do not shift it.

A proposed correction file accompanies this study at
[proposed_overrides.json](studies/msgtable/proposed_overrides.json) — 24 entries. Applying it
alongside the live schema leaves **zero residual disagreement** with the binary. It is a
proposal only; `schema/messages.json` and `schema/overrides.json` were not modified.

---

## 2. What a table entry actually looks like — SOURCED

### 2.1 The field descriptor: one packed dword called a `cmd`

```
cmd = (count << 8) | (log2_elem_size << 4) | type

  type  = cmd & 0xF        bits 0-3   legal 0..12; 13/14/15 trip the default-case assert
  index = (cmd >> 4) & 0xF bits 4-7   log2 of element size, so element size = 1 << index
  count = cmd >> 8         bits 8+    capacity, meaning overloaded per type; never masked
```

Proof, at `MsgChannel.cpp`'s unpack-size helper:

```
0x7de0ea   83 e0 0f              and eax, 0xF          ; type = bits 0-3
0x7de0ed   83 f8 0c              cmp eax, 0xC          ; bound: 0..12
0x7de0f0   0f 87 3b 02 00 00     ja  0x7de331          ; -> "No valid case for switch variable"
0x7de0f6   ff 24 85 48 e3 7d 00  jmp dword ptr [eax*4 + 0x7de348]
0x7de244   c1 e9 04              shr ecx, 4            ; index = bits 4-7
0x7de247   83 e1 0f              and ecx, 0xF
           d3 e0 / 83 f8 02      shl eax, cl / cmp eax, 2   ; asserts 1<<index == sizeof(wchar)
0x7de28b   c1 e8 08              shr eax, 8            ; count — bare shift, no AND anywhere
```

The `index` semantics are pinned by the client's own assertion,
`1 << MSG_FIELD_INDEX_GET(cmds[i]) == sizeof(wchar)`. The `count` field is extracted by a bare
`shr` at twelve separate sites with no masking instruction at any of them.

**`cmds[0]` is the raw opcode, not a packed cmd.** The receive installer uses it directly as an
array subscript: `mov eax,[cmds]` / `mov esi,[eax]` at `0x7dd900`, then
`lea ecx,[esi+esi*2]` / `lea esi,[eax+ecx*4]` at `0x7dd920` — base + `cmds[0]` * 12. Because
`count` includes slot 0, **field count = count − 1**.

**There is no `TYPE_MSG_HEADER` enum value on this build.** The header is a positional
convention, not a field type. Every reconstruction that lists `msg_header` as field 0 is
modelling a convention as if it were data.

**The count field's upper edge is NOT ESTABLISHED and cannot be from this image.** Bits 8-20
are demonstrably in use — the OR of all 2008 field descriptors is exactly `0x001fff7f`, and
the largest count observed is `0x1000` (cmd `0x0010000b` at VA `0xbf9268` and `0xbf92d4`, both
statically present in the file). "count = bits 8-23 with 24-31 reserved" is observationally
identical to "bits 8-31" here, because every cmd is a compile-time constant that is only ever
read — there is no `MSG_FIELD_*_SET` constructor whose write mask would settle it. The narrower
reading "count = bits 8-19" is **refuted** by that `0x1000`.

### 2.2 The field type enum — 13 values, 10 distinct behaviours

All four switches over field type compile to jump tables of exactly 13 entries followed by
`0xCC` padding: validator `0x7de348`, send-from-args `0x7dcec4`, send-from-struct `0x7dd310`,
receive `0x7dc650`. In all four, `{4,8}`, `{5,9}` and `{6,10}` share a jump target — those are
aliases and are statically indistinguishable. `{0,1}` share a target in three of the four; the
**receive** table is the exception (`jt[0]=0x7dc2c8` vs `jt[1]=0x7dc35b`), which is the only
reason type 1 is identifiable at all.

| type | meaning | wire bytes | uses | our schema's name |
|---|---|---|---|---|
| 0 | plain 4-byte scalar | 4 | 127 | `agent_id` |
| 1 | 4-byte scalar, head of the resumable vector chain | 4 | 4 | `float` |
| 2 | vec2 | 8 | 30 | `vec2` |
| 3 | vec3 | 12 | 1 | `vec3` |
| 4 | unsigned int, `count` wire bytes widened to a 4-byte slot | count ∈ {1,2,4} | 1462 | `byte`/`word`/`dword` |
| 5 | fixed raw blob, no length prefix | count | 46 | `blob(count)` |
| 6 | variable array payload; always follows a type 11 | runtime_count << index_of_the_11 | 64 | (folded into the array) |
| 7 | wide UTF-16 string, max `count` chars, index always 1 | 2 + 2·len | 192 | `string16(count)` |
| 8 | alias of 4 | — | 0 | — |
| 9 | alias of 5 | count | 5 | `blob(count)` |
| 10 | alias of 6 | — | 0 | — |
| 11 | array length prefix, max `count` elements of size `1 << index` | **2** | 64 | `array8/16/32(count)` |
| 12 | nested-struct repeat count; parser rewinds to cmd+4 per repetition | **1** | 13 | `nested_struct(count)` |
| 13-15 | invalid, unreachable | — | — | — |

Type 0 maps to `agent_id` rather than `dword` on a count coincidence that is hard to argue
with: across the 748 shared messages the binary has exactly 127 type-0 fields and our schema
has exactly 127 `agent_id` fields.

Three semantic corrections fall out of this table, and each is a live framing hazard:

1. **The array length prefix is always 16 bits**, regardless of element width — `push 0x10`
   with mask `0xffff` at `0x7dc434`. Element width lives in the index nibble as a log2. So
   OpenTyria's `TYPE_ARRAY_8` / `_16` / `_32` do **not** name prefix widths; they name
   **element** widths. Reading them as prefix widths misframes every array.
2. **The only 8-bit count on the wire** is the type-12 nested-struct repeat count (`push 8`
   with mask `0xff` at `0x7dc280`).
3. **An array is two cmds** (type-11 header + type-6 payload) but one schema field, so any
   raw field-count comparison against a reconstruction is off by one per array.

Type 9 *is* used — 5 times, always cmd `0x1409` (a 20-byte blob), always on auth-channel send
opcodes 0x03, 0x05 and 0x19, read straight from static `.data` with no reconstruction involved.
Twenty-byte blobs in authentication messages are SHA-1-shaped (INFERRED). Types 8 and 10 are
unused by all 2008 descriptors and nothing in this binary can separate them from 4 and 6.

### 2.3 The descriptor structs — two shapes

```c
struct MsgFormatRecv {        // 12 bytes
    const u32* cmds;          // +0x00   cmds[0] = opcode
    u32        count;         // +0x04   dwords in cmds[] INCLUDING cmds[0]
    void     (*dispatch)();   // +0x08
};
struct MsgFormatSend {        // 8 bytes — no dispatch member
    const u32* cmds;          // +0x00
    u32        count;         // +0x04
};
```

Strides: `add ebx,0xc` at `0x7dd7ca` (receive), `cmp [esi+ebx*8+4],0` at `0x7dd9b7` and
`add esi,8` at `0x7ddb56` (send). Member offsets are pinned by which assert each comparison
guards — `[ebx+4]` → `msgs[i].count`, `[edi+8]` → `src->dispatch`, `[eax+ecx*4+4]` →
`!dst->count`.

There is a second, fully independent confirmation of both shapes that uses no disassembly at
all: the base-relocation bitmap. Relocations mark which dwords are addresses, and per entry it
reads `(1,0)` for all 237 stride-8 entries and `(1,0,1)` for all 514 stride-12 entries —
pointer/scalar, and pointer/scalar/pointer. OpenTyria's 16-byte four-member struct would have
to show `(0,0,1,0)`, and does not appear anywhere.

`MsgChannel` itself: `+0x18` max unpack bytes, `+0x1c/+0x20/+0x24` `m_sendMsgs`,
`+0x2c/+0x30/+0x34` `m_recvMsgs` (both `rtl::Array`).

### 2.4 Constants

| Constant | Real value | OpenTyria says |
|---|---|---|
| `MSG_MAX_BUFFER_SIZE` | **0x2000 = 8192** (`3d 00 20 00 00` at `0x7dd96d`, `0x7ddb3b`) | 4096 — **wrong** |
| `MSG_FIELD_MAX_STRUCT_COUNT` | 0x80 = 128 (`3d 80 00 00 00` at `0x7de295`) | not modelled |

---

## 3. Where the tables are — SOURCED

`MsgChannel::RegisterMsgs` is at **VA 0x007de010** (file 0x3dd410), `__cdecl(chanSel, arg1,
sendMsgs, sendCount, recvMsgs, recvCount)`. It has **exactly 14 callers**, at
`0x457f92, 0x462662, 0x462adf, 0x4630cf, 0x4630f5, 0x465392, 0x4655ef, 0x4657f2, 0x465862,
0x465882, 0x4664a2, 0x4664c2, 0x491b62, 0x492582`.

There is no fifteenth. The check that settles it: **the literal dword `0x007de010` occurs zero
times in the entire 10,483,904-byte file**, so the function's address is never taken — no
indirect call, no vtable slot, no function-pointer table. There are also no `jmp` thunks to it.

The 25 tables (12 of the 14 registration sites point into `.rdata`; opcode ranges are min/max,
**not** contiguous runs — see §10):

| VA | file | n | channel / direction | note |
|---|---|---|---|---|
| 0xa52d70 | 0x651d70 | 18 | ch0 RECV | **the AgMsg module — contains all four oracle messages** |
| 0xa52e48 | 0x651e48 | 2 | ch0 SEND | |
| 0xa96598 / 0xa965a0 | 0x695598 | 1 / 1 | ch0 SEND / RECV | single-message module |
| 0xb97958 | 0x796958 | 2 | ch0 SEND | telemetry-shaped, fully static |
| 0xbc89b0 | 0x7c79b0 | 15 | ch0 RECV | |
| 0xbc8cb8 | 0x7c7cb8 | 86 | ch0 SEND | largest send table |
| 0xbc8f68 | 0x7c7f68 | 203 | ch0 RECV | **largest table** |
| 0xbc9a10 / 0xbc9a18 | 0x7c8a10 | 1 / 8 | ch0 SEND / RECV | |
| 0xbca740 | 0x7c9740 | 15 | ch0 RECV | |
| 0xbca808 / 0xbca870 | 0x7c9808 | 13 / 31 | ch0 SEND / RECV | |
| 0xbcac48 / 0xbcad58 | 0x7c9c48 | 34 / 56 | ch0 SEND / RECV | |
| 0xbcb030 / 0xbcb0a8 | 0x7ca030 | 15 / 68 | ch0 SEND / RECV | |
| 0xbcb9f8 / 0xbcb788 | 0x7ca9f8 | 27 / 52 | ch0 SEND / RECV | |
| 0xbcbaf0 / 0xbcbb30 | 0x7caaf0 | 8 / 10 | ch0 SEND / RECV | |
| 0xbec384 / 0xbec394 | 0x7eb384 | 2 / 5 | ch0 SEND / RECV | in `.data`; `count` members BSS-zero |
| **0xbec3d0** | 0x7eb3d0 | **46** | **ch3 SEND (AUTH_CMSG)** | in `.data`; `count` members BSS-zero |
| **0xbec540** | 0x7eb540 | **32** | **ch3 RECV (AUTH_SMSG)** | in `.data`; `count` members BSS-zero |

A pleasing corroboration that these are the right objects: ArenaNet's own source path
`P:\Code\Engine\Agent\AgMsg.cpp` sits at VA `0xa52e58`, immediately after the 18-entry agent
message table at `0xa52d70` and its 2-entry send table — the agent/movement module's tables,
with the module's filename parked against them.

---

## 4. Verification — the oracle, 4 of 4 — SOURCED

All four known-good shapes live in the AgMsg receive table at `0xa52d70`. Decoded from the
recovered `cmds` arrays using only the bit layout in §2.1:

| opcode | cmds[] | fields | wire | required | |
|---|---|---|---|---|---|
| 0x001E `WORLD_SIMULATION_TICK` | `1e, 404` | 1 | 6 | 6 | **PASS** |
| 0x0029 `AGENT_MOVE_TO_POINT` | `29, 404, 12, 204, 204` | 4 | 18 | 18 | **PASS** |
| 0x002C `AGENT_UPDATE_POSITION` | `2c, 404, 12, 204` | 3 | 16 | 16 | **PASS** |
| 0x0020 `WORLD_CREATE_AGENT` | `20, 404, 404, 104, 104, 12, 204, 2, 104, 21, 1, 404×7, 2, 12, 204, 404, 12, 204` | 23 | 99 | 23 / 0x63 | **PASS** |

`0x0029` reads `dword + vec2 + word + word` and `0x002C` reads `dword + vec2 + word`, which is
exactly the shape our server already sends and the client already accepts.

Two independent corroborations of the same numbers. First, the tables' own `count` members
give the field counts with no decoding at all: 2, 5, 4, 24 — each one more than the field
count, as §2.1 requires. Second, these four were recomputed from raw `cmds` dwords three times
by separate parties (the reconciling agent, an adversarial agent working from scratch, and the
orchestrator) and agree every time.

This is the result that makes the rest of the study trustworthy. The AgMsg module is also the
*hardest* case in the binary — its `cmds` arrays are 100% zero-filled in the file (see §6) —
so passing 4/4 there exercises the reconstruction at its most exposed point.

---

## 5. Channels, and the 0x8000 question — SOURCED

**Two channels, not four catalogs.** A channel is keyed by a 2-tuple, matched on both
`[obj+0x10]==arg0` and `[obj+0x14]==arg1` (`39 70 10` at `0x7ddb96`, `39 50 14` at `0x7ddb9b`).
All 14 registrations pass `arg1 = 0` and `arg0 ∈ {0, 3}` — thirteen pass 0, only the site at
`0x492582` passes 3. Each channel carries an independent send and receive opcode space, which
is what produces our familiar four catalogs.

That channel 0 is "game" and channel 3 is "auth" is **INFERRED**, not sourced: no string in the
binary maps a channel selector to a name. The reading is supported by ch3 send opcode 0x01
being two 32-character wide strings (an email and password pair) and by the SHA-1-shaped
20-byte blobs on ch3.

The partition is real rather than assumed, and the proof is structural: ch3's opcode range
overlaps ch0's almost completely. If the channel argument did not partition the space, 77
opcodes would collide, and the installer asserts `!dst->count` on every slot it fills — 77
assertions would fire at startup.

### The 0x8000 bit is not a channel mask — SOURCED

Across all 751 entries, **zero opcodes have bit 0x8000 set and zero cmds dwords equal 0x8000.**
The bit appears in the entire Msg subsystem exactly twice, both on the send path:

```
0x7dcbcf   25 00 80 00 00   and eax, 0x8000      ; (conn[+0x54] != 0) ? 0x8000 : 0
0x7dcfca   25 00 80 00 00   and eax, 0x8000      ; via neg/sbb, OR'd into the 16-bit id word
```

So it is a **runtime framing flag on outbound messages**, not a property of the tables and not
a client-to-server catalog mask. This refutes Headquarter's `AUTH_CMSG_MASK`/`GAME_CMSG_MASK =
0x8000` as a description of client behaviour — though the effect we observed on the wire is
consistent with it, because in practice the flag is set on client-to-server traffic.

What the bit *means* is **NOT ESTABLISHED**. The obvious reading — "set once a message has
already been written into the current datagram" — is not sourced. The only reset found
(`0x7dcfb2`) sits behind a compare against an immediate larger than every `.text` VA, so on a
standard frame it appears never to execute. We can source where the bit comes from; we cannot
source when it clears.

---

## 6. Why a naive read of this binary gives wrong answers

This is the trap, and it caught one agent in this very study, so it is worth stating plainly.

The `msgs[]` descriptor tables are static, but many `cmds[]` field arrays live in `.data` and
are written at load time by MSVC dynamic initializers. **A zero dword decodes as a perfectly
legal type-0 (4-byte) field.** So a decoder that reads the file naively produces shapes that
look plausible and are wrong — during this study one pass reported `0x0029` as "four plain
dwords", which totals 18 bytes correctly while getting every field wrong, and reported `0x002C`
as 14 bytes and `0x0020` as 94.

The exact census (SOURCED, and measured three ways):

- 751 `cmds[]` arrays hold 2759 dwords = 751 opcode slots + 2008 field descriptors.
- All 751 opcode slots are statically present. **911** field descriptors are statically
  present. **1097** are written at load time.
- 1101 slots are statically zero: the 1097 written ones, plus **4 that are never written** —
  `0xbf8dbc`, `0xbf9054`, `0xc02014`, `0xc02060`, each `cmds[0]` of a two-dword array
  `{0x00000000, 0x00000404}`. Those are genuine **opcode-0 messages**, one per channel and
  direction, not undecoded holes.
- The zero-fill is not "all or nothing per module" and not per array either: of the 682
  `.data` arrays, 309 are all-static, 357 all-load-time, and **16 are mixed**. In every one of
  the 16, the statically folded elements are exactly the (type-11, type-6) array pairs — which
  independently re-confirms the rule that a type-6 payload always follows a type-11 prefix.
- Separately, four tables (`0xbec384`, `0xbec394`, `0xbec3d0`, `0xbec540` — including **both
  auth tables**) have their `count` member at +0x04 BSS-zero and written at load time, while
  the `cmds` pointer at +0x00 is static. A naive read of those four yields 85 messages of
  length zero, which silently vanish rather than erroring.

### Why we believe the reconstruction anyway — SOURCED

The load-time writes were recovered by finding the initializer stores and constant-propagating
them. That method depends on heuristics, so it was cross-checked against the **PE base
relocation table**, which is loader-authoritative and depends on no heuristic at all: every
absolute address in the image must have a relocation entry, so relocations census exactly which
dwords are addresses and which instructions store them.

- The reloc-derived set of load-time-written cmd slots and the reconstruction's set are
  **identical: 1097 = 1097, symmetric difference empty.** Zero missed writes, zero invented
  writes.
- Walking values backward from each store, pinned at every step by its own relocation entry,
  reproduces **1097 of 1097 values** — from a constant pool of 318 globals in
  `0xbf52c0..0xc016d4`, all statically non-zero in the file and none of them relocated.
- Of the 2759 dwords decoded as cmd slots, **exactly 0 are relocated** — the loader confirms
  every one is a constant, not an address. If any "cmd" had been relocated, that message's
  decode would be wrong.
- All 751 `cmds` pointers are relocated (751/751) and all 514 `dispatch` pointers are relocated
  and land in `.text`.
- The register-base loophole is closed: none of the 682 array base addresses and none of the
  2690 slots ever appears in `.text` as an immediate or an indexed-addressing displacement, so
  there is no write path the relocation census would miss.
- Every slot has **exactly one** store — zero uncovered, zero conflicting. All 373 functions
  containing such stores are entries in the CRT's `__xc_a..__xc_z` initializer table reached
  from `_cinit` at `0x5ae47c`.
- All 2008 descriptors satisfy every invariant the client itself asserts: type ≤ 12; type-7
  index always 1 (192/192); every type-6 preceded by a type-11 (64/64); type-4 count ∈ {1,2,4};
  type-12 count ≤ 128; type-5/9 count non-zero. Zero violations.
- Zero duplicate opcodes in any of the four spaces — and since the installer asserts
  `!dst->count` per slot, a single collision would have fired at boot.

A methodological warning for anyone repeating this, because it produced a wrong intermediate
result before it was caught: naive relocation-operand attribution silently mis-decodes
`C7 05 <disp32> <imm32>` (`mov [abs], imm32`) as `add eax, <disp32>`, because the one-byte
ALU-eax-imm32 opcodes alias the `mod=00 rm=101` modrm byte exactly. Before that was
disambiguated the census read 1051 stores with 46 spurious disagreements; after, 1097 and zero.
Separately, MSVC packs these initializers back-to-back with no `int3` padding, so any approach
that discovers function boundaries first will miss writes — two independent agents hit this
same bug. The safe posture is to derive the write set without ever computing a function
boundary.

---

## 7. How many messages, and how that reconciles with our 777 — SOURCED

| channel / direction | registered | id range | space (max+1) | gaps | our schema |
|---|---|---|---|---|---|
| ch0 RECV — GAME_SMSG | 482 | 0x000-0x1e6 | 487 | 5 | 487 |
| ch0 SEND — GAME_CMSG | 191 | 0x000-0x0c1 | 194 | 3 | 194 |
| ch3 RECV — AUTH_SMSG | 32 | 0x00-0x27 | 40 | 8 | 39 |
| ch3 SEND — AUTH_CMSG | 46 | 0x00-0x3b | 60 | 14 | 57 |
| **total** | **751** | | **781** | 30 | **777** |

The four space sizes — 487 / 194 / 40 / 60 — match ldufr/Headquarter's declared counts exactly.
Our schema's `AUTH_CMSG = 57` and `AUTH_SMSG = 39` are **undercounts** for this build.

The three numbers reconcile per opcode with no residual:

```
777 (ours)   = 748 shared + 29 header-only stubs for opcodes the client never registers
751 (binary) = 748 shared +  3 messages the client has and we lack
781 (space)  = 751 registered + 30 gaps
30 gaps      = the 29 stubs we carry + AUTH_CMSG 0x39, which neither side has
```

**What the 30 gaps are.** Every gap opcode is a zero-field entry in our schema — `fields ==
[msg_header]`, size 2, fixed. Stronger, and this is what closes the question: per channel,
{our zero-field opcodes} equals {the binary's genuine header-only messages} ∪ {the gaps},
exactly, with nothing unaccounted for on either side. Upstream emitted a dense array and padded
every unregistered slot with a header-only stub that is formally indistinguishable from a real
header-only message. That is the entire explanation.

The practical consequence is mild but worth knowing: because the stubs carry no fields, our
server has no shape to serialise for any of them, so nothing is being sent into the void. But
`codec.py` will happily *decode* a 2-byte message for any of these 30 opcodes and keep walking
the stream, where the real client would assert. A misframed stream can therefore appear to
decode into a run of fictitious empty messages rather than failing loudly.

---

## 8. Where our catalog disagrees with the binary

This is the operational payload. Of the 748 messages present in both, **744 have an identical
field signature.** Four differ, and all four differ the same way: **the binary has one more
trailing field than we do.**

| channel | opcode | ours | binary | delta |
|---|---|---|---|---|
| GAME_SMSG | 140 (0x8C) | `dword, dword` — 10 B | `dword, dword, **byte**` — 11 B | +1 |
| GAME_SMSG | 146 (0x92) | `dword, dword` — 10 B | `dword, dword, **word**` — 12 B | +2 |
| GAME_SMSG | 421 (0x1A5) | `blob(24), dword, byte, word, byte, dword` — 38 B | same + **byte** — 39 B | +1 |
| GAME_CMSG | 144 (0x90) | `blob(16)` — 18 B | `blob(16), **byte**` — 19 B | +1 |

**The last row is the one that validates the method.** GAME_CMSG 144 is
`INSTANCE_LOAD_REQUEST_PLAYERS`, already corrected from 18 to 19 bytes in
`schema/overrides.json` on the strength of a live capture — the one where a single unconsumed
byte misframed everything after it and made the rest of the stream invisible. The binary
rediscovers that correction independently, at the exact opcode, with the exact field list:
`cmds[] @ 0xc016fc = [0x90, 0x1005, 0x104]` → `msg_header, blob(16), byte` = 19 bytes. A
correction we earned the hard way falls out of the table for free, which is a good reason to
trust the other three.

Each of the other three was verified the same way — descriptor entry, static `count`, the
adjacency check that the next `cmds` array begins exactly `count` dwords later, and
disassembly of the initializer that writes each zero slot from a statically present constant:

```
GAME_SMSG 0x8C   cmds[] @VA 0xbfff98   entry @VA 0xbc93a0, count=4
                 initializer 0x464650-0x46466e writes 0x404, 0x404, 0x104
GAME_SMSG 0x92   cmds[] @VA 0xbffffc   entry @VA 0xbc93e8, count=4
                 initializer 0x464730-0x46474e writes 0x404, 0x404, 0x204
GAME_SMSG 0x1A5  cmds[] @VA 0xc01b70   entry @VA 0xbcb36c, count=8
                 initializer 0x4661d0-0x466216 writes 0x1805,0x404,0x104,0x204,0x104,0x404,0x104
```

Notably, **zero messages agree on total size but disagree on decomposition.** The "right total,
wrong fields" failure mode that bit this study once does not occur anywhere in the 748.

### Three messages we are completely blind to — SOURCED

All three are on the auth channel, all three are fully static in the file (no reconstruction
involved), and all three are bulk array carriers. On seeing any of them today we would fail to
decode and abandon the rest of the frame.

| channel | opcode | shape | evidence |
|---|---|---|---|
| AUTH_SMSG | 39 (0x27) | `dword, array8(4096)` | cmds @VA 0xbf92d4, entry @VA 0xbec6b4 |
| AUTH_CMSG | 58 (0x3A) | `dword, dword, array8(512)` | cmds @VA 0xbf9020, entry @VA 0xbec518 |
| AUTH_CMSG | 59 (0x3B) | `dword, array8(512)` | cmds @VA 0xbf9034, entry @VA 0xbec520 |

### The `variable_length` flag is wrong on 19 messages — SOURCED

The flag carries no information beyond the field list: bucketing all 777 entries shows it is
exactly `has_variable_field OR has_blob`. It is wrong on precisely the 19 blob-only messages,
because a blob is a type-5 cmd — a fixed `count`-byte payload with **no length prefix on the
wire**. All 19 are fixed-size: GAME_SMSG 0x0116/0x0117/0x0118/0x0124/0x0195/0x01A5, GAME_CMSG
0x0090/0x00B0/0x00B6/0x00B7, AUTH_SMSG 0x0006/0x0008/0x0009/0x0015/0x0023, AUTH_CMSG
0x0002/0x000C/0x0019/0x0025.

### A systematic defect we deliberately did NOT patch — SOURCED

`declared_unpack_size` is neither the binary's wire size nor its unpack size. It is a max-wire
size computed with OpenTyria's prefix conventions, and that formula reproduces the field for
777 of 777 messages — so it is internally consistent and simply built on the wrong prefix
widths (4 bytes assumed for strings, arrays and nested structs; the real widths are 2, 2 and 1).
It therefore **overstates** the true maximum wire size on 188 of the 748 shared messages, by
561 bytes in total (worst cases: GAME_SMSG 402 by 21 bytes, AUTH_CMSG 40 by 14, GAME_SMSG 148
by 10).

This is a documentation defect, not a live framing bug: `toolkit/schema/codec.py` writes the
correct 2-byte prefixes and never reads `declared_unpack_size`. We left it alone on purpose,
because patching 24 entries to a different convention than the other 753 would make the field
mean two different things depending on the row. It will bite anyone who trusts the number.

### The proposed corrections

[proposed_overrides.json](studies/msgtable/proposed_overrides.json) — 24 entries: 3 field-shape
fixes, 3 new messages, and 18 `variable_length` fixes (GAME_SMSG 421 is both a shape fix and a
flag fix). Every `why` cites the `cmds` array and the VA it came from.

Loading it through `codec.py` alongside the live schema applies cleanly and leaves **zero
residual disagreement**: all 751 registered messages then match the binary on field list,
size and flag. `schema/messages.json` and `schema/overrides.json` were not modified.

---

## 9. The opcode drift question, settled — SOURCED

`studies/movement/FINDINGS.md` documents a confirmed +2 opcode drift between the GWCA lineage
and the ldufr lineage, and records that no mirror states which build it came from. That was the
open question this study was best placed to answer.

Method: canonicalise every message on both sides to a field-type-and-size token sequence,
restrict to schema entries with at least one real field so the empty stubs cannot inflate the
score, then count exact matches of our opcode *o* against binary opcode *o + delta*.

| channel | candidates | delta −2 | **delta 0** | delta +2 |
|---|---|---|---|---|
| GAME_SMSG | 444 | 9.2% | **99.3%** (441) | 8.9% |
| GAME_CMSG | 161 | 6.3% | **99.4%** (160) | 6.4% |
| AUTH_SMSG | 31 | ≤12.5% | **100%** (31) | ≤12.5% |
| AUTH_CMSG | 43 | ≤12.5% | **100%** (43) | ≤12.5% |

**Delta = 0 on all four channels**, by a margin no noise floor comes close to.

The direct exhibit confirms it without statistics. Prior work used GAME_CMSG 0x0A/0x0B — a
telemetry/GPU-info-shaped pair present in the build-38771 lineage and absent from GWCA's older
numbering — as the drift marker. In this binary, 0x0A is `blob(16), dword×3, blob(12), dword×7,
string16(64), string16(20)` and 0x0B is `blob(16), dword×4, string16(16), string16(128)`, and
**our schema carries the identical token sequence at the identical opcode.**

So our catalog descends from the same lineage as build 38797. The +2 drift is GWCA-versus-ldufr,
not ldufr-versus-this-build. **It must not be applied to `schema/messages.json`.**

---

## 10. Where the reconstructions are wrong — SOURCED against UPSTREAM

| Claim | Source | Verdict |
|---|---|---|
| Field descriptor is `{type, length}`, two dwords | OpenTyria `msgdefs.h` | **Wrong.** One packed dword. |
| `MsgFormat{header, count, fields, unpack_size}`, 16 bytes | OpenTyria `msgdefs.h` | **Wrong.** Two structs, 12 and 8 bytes, no `header`, no stored unpack size. |
| `TYPE_MSG_HEADER = 1` is a field type | OpenTyria | **Wrong.** No such enum value; the header is positional. |
| `MSG_MAX_BUFFER_SIZE = 4096` | OpenTyria | **Wrong.** 8192. |
| `TYPE_ARRAY_8/16/32` name prefix widths | OpenTyria | **Wrong.** They name *element* widths; the prefix is always 16 bits. |
| `AUTH_CMSG_MASK / GAME_CMSG_MASK = 0x8000` | Headquarter | **Wrong as client behaviour.** A runtime send-path framing flag; not in the tables. |
| Declared counts 487 / 194 / 40 / 60 | Headquarter | **Right**, and our 39 / 57 are undercounts. |
| "GW doesn't have the StoC array in RDATA; it's built from the different StoC modules in DATA" | GWCA comment | **Wrong for this build.** 12 of 14 registration sites point at static `.rdata` tables. What *is* runtime-built is the channel's flat per-opcode array, plus the `cmds` arrays. |

One more, aimed at anyone reading table layout as structure: **table entry order is
source-declaration order, not opcode order.** Only 8 of the 25 tables are monotonic in opcode;
the largest has 15 monotonicity breaks. Every opcode range quoted in §3 is a min/max, not a
contiguous run. The installer indexes by `cmds[0]`, so order genuinely does not matter to the
client — but reconstructing ranges from table position will mislead you.

---

## 11. What we did not establish

Listed rather than glossed, because a confident wrong answer is worse than an honest partial one.

1. **The `count` field's width.** Bits 8-20 are in use; "bits 8-23, reserved above" is
   observationally identical to "bits 8-31" on this image and cannot be separated by static
   analysis, because no code ever *writes* a cmd. Closing it needs a different build or a debug
   binary from the same family carrying a cmd above `0x00ffffff`.
2. **Types 8 and 10.** Never used by any of the 2008 descriptors, and their jump-table targets
   are byte-identical to types 4 and 6 in all four switches. Nothing in this binary separates
   them.
3. **The index nibble for types 0/1/2/3.** It varies (values 0, 1, 2, 5) and the codec provably
   ignores it for those types — the oracle arithmetic proves that. Something outside the four
   switch functions consumes it; we did not find what.
4. **Type 0 versus type 1.** They differ only in the receive path, where type 1 maintains a
   countdown at `mc+0x28`. That type 1 means "float / vector component" is INFERRED from it
   appearing exactly 4 times and only inside agent-position messages (GAME_SMSG 0x20, 0x27,
   0x2B). The obvious next check is whether those dwords are IEEE floats in one of our captures.
5. **The type-12 `(maxCount + 1)` dimensioning** at `0x7de2e5-0x7de30a`. Reproduced faithfully,
   not explained. It may be a sentinel slot, or `count` may store `maxCount - 1` for type 12.
   Only 13 messages exercise it and none is in the oracle.
6. **The 0x8000 bit's reset semantics** (§5).
7. **Channel names.** That 0 is "game" and 3 is "auth" is structural inference; no string maps a
   selector to a name.
8. **One orphan descriptor.** At VA `0xbf9114` there is a complete, statically initialised
   9-dword array — `[0x05, dword, wstring(28), wstring(28), wstring(32), wstring(32),
   wstring(12), wstring(28), wstring(28)]` — sitting in the ch3 RECV pool in the only hole in
   that pool, wedged between AUTH_SMSG 0x16 and 0x0E. **Nothing points at it**; an exhaustive
   pointer scan of `.rdata` and `.data` finds no reference. It looks like an AUTH_SMSG 0x05
   descriptor that was compiled but never registered — 0x05 is one of the 30 gaps. We did not
   determine whether it is dead code or reachable some way we did not find. The other 29 gaps
   have no `cmds` array anywhere in the image, confirmed by three independent scans.

---

## 12. Method, and how to reproduce

1. Parse the PE (32-bit, ImageBase `0x400000`). `.text` VA `0x401000`/file `0x400`; `.rdata` VA
   `0x939000`/file `0x538000`; `.data` VA `0xbec000`/file `0x7eb000` — note `.data` is
   `0x5601b8` virtual but only `0x16a00` raw, so most of it is BSS.
2. Find the assert strings. `P:\Code\Net\Msg\MsgChannel.cpp` is at file `0x68fdf8`; the Net\Msg
   string block runs `0x68fbcc-0x6901d0` and covers five source files (`MsgConn.cpp`,
   `MsgChannel.cpp`, `MsgPerf.cpp`, `MsgUtil.cpp`, `MsgProp.cpp`).
3. Convert to VAs (`VA = 0x939000 + (fo - 0x538000)`) and scan `.text` for `push imm32` of each.
   Every Net/Msg assert xref lands in one ~10.7 KB window, file `0x3db5d3-0x3ddccb`.
4. Disassemble with capstone (`CS_ARCH_X86`, `CS_MODE_32`) around the asserts to recover the bit
   layout, the jump tables, and the struct strides.
5. Scan `.text` for `E8` rel32 calls to `0x7de010` to find the 14 registration sites; read the
   six pushed arguments at each.
6. Reconstruct the load-time-written `cmds` slots, then cross-check against `.reloc` (§6).

Tooling was capstone and pefile only — no IDA, radare2, or objdump. `toolkit/clientscan/`
provided the string-mining patterns.

Working artifacts (scratch, not committed): `msgtable.py` (decoder), `catalog_final.json` (25
tables, 751 messages, each with `cmds`, wire size, unpack size and variability).

**Provenance and honesty.** This pass ran 15 agents across two workflows: six independent
recon and decode attacks, one reconciliation, and eight adversarial verification passes whose
standing instruction was to refute rather than confirm. The adversarial passes did real work —
they overturned the claimed maximum `count`, caught a schema diff that had been filtered on a
flag the same pass had proven unreliable (which is how GAME_SMSG 0x1A5 was found), corrected
which struct member is BSS-zero in the auth tables, and refuted an "all-or-nothing per module"
characterisation of the zero-fill at both granularities. Every such correction is folded into
the text above rather than dropped. The four oracle shapes were independently recomputed from
raw bytes three times, by three different parties, before this document was written.
