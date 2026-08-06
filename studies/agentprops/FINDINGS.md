# The agent-property dispatch, recovered from the client binary

Build 38797. Static analysis of `vault/run/2026-07-29_221c13772c7a/Gw.exe` as a
file — the client was never launched for this pass, no debugger attached, no
process memory read.

Agent properties are how Guild Wars carries damage, healing, energy, level,
knockdown, animations and casting — one message, one numeric `prop_id`, one
value. Every implementation on disk reconstructs the meaning of those ids from
one 66-entry enum in OpenTyria's `GmAgentProperties.h`, which is a single
lineage and, as `studies/enemy/PLAN.md` §6b–§6i found the hard way, not reliable
enough to build combat on. This document replaces that guessing for the float
path with the client's own jump table.

## Labels

| Label | Meaning |
|---|---|
| **SOURCED** | Measured in the binary's bytes. Addresses are given so it can be re-read. |
| **INFERRED** | Our reading of measured bytes. The bytes are real; the interpretation is ours. |
| **OBSERVED** | Seen against our own running client, in our own logs. |
| **UPSTREAM** | A reconstruction says it. Not ground truth, and corrected below. |

---

## 1. The answer in one page

**The float-property dispatch is a jump table, and it acts on 8 of 47
properties.** Everything else falls to the default case and does nothing on this
path.

| Property | Upstream name | What it does here |
|---|---|---|
| **16** | `DamageModifier1` / Headquarter's `AG_ATTR_DAMAGE` | damage — the one we have driven |
| **33** | `EnergyModifier1` | energy |
| **34** | `HealthModifier1` | health |
| **43** | `EnergyRegen` | energy regeneration |
| **44** | `HealthRegen` | health regeneration |
| **52** | `EnergyModifier2` | energy |
| **55** | `HealthModifier2` / Headquarter's `AG_ATTR_ARMOR_IGNORING` | health |
| **62** | `EnergyModifier4` | energy |

**Damage is a fraction of maximum health, and here is the multiply that makes it
one — SOURCED.** The damage case is three instructions long:

```
0x0081823C   fld  dword ptr [esi+0x24]    ; the agent's maximum health
             fmul dword ptr [ebp+0x0C]    ; × the value the server sent
             fstp dword ptr [ebp+0x0C]    ; → an absolute quantity
```

`studies/enemy/PLAN.md` §6b measured this behaviour from the outside — `-0.25`
against a maximum of 100 arriving as 25 damage. This is the instruction that
does it. A measurement and the code agreeing is the strongest position this
project reaches.

**A correction to Headquarter — SOURCED against UPSTREAM.** `ldufr/Headquarter`
applies `AG_ATTR_DAMAGE` (16), `AG_ATTR_CRITICAL_DAMAGE` (17) and
`AG_ATTR_ARMOR_IGNORING` (55) identically, in one `switch` with three
fall-through cases (`code/client/agent.c:860-867`). **The real client does not.**
16 and 55 have their own dispatch targets; **17 falls to the default case** and
does nothing on this path. Any server modelling critical hits by sending property
17 the way Headquarter reads it will produce no effect at all.

**Death is not in this dispatch.** None of the eight is a death property, which
closes off the last place §6i had left to look on the property channel and says
where to look next (§4).

---

## 2. How the two paths reach the dispatch — SOURCED

Both property messages are thin shims into a shared per-agent record.

```
GAME_SMSG 0x009F  (int)            GAME_SMSG 0x00A3  (float, with target+cause)
  handler 0x0091ED00                 handler 0x0091EDD0
    -> 0x008128F0                      -> 0x00813040
         -> 0x00818170  (3 props)           -> 0x00818210  (jump table, 8 props)
```

Three things fall out of the shims themselves:

- **The value on `0x00A3` is an IEEE float, per the client — SOURCED.** The
  handler loads it with `fld dword ptr [eax+0x10]` before passing it on. Our
  schema types that field as an opaque dword (correctly — the generic
  deserializer only copies bytes), and `toolkit/authsrv/probes.py:_f32` packs
  float bits into it. The client's own `fld` confirms the packing.
- **The first agent slot is the target — SOURCED, and it corroborates an
  OBSERVED result.** `0x00813040` takes the *second* argument (the first agent
  id in the payload) and uses it to index the per-agent record it modifies:
  `imul ecx, esi, 0x34`. `studies/enemy/PLAN.md` §6f established the same thing
  by aiming damage at an NPC and watching the NPC's bar drop.
- **The record is `0x34` bytes per agent**, based at `[context+0x7C]`, bounds
  checked against `[context+0x84]` with the shared `Array.h` / `index < m_count`
  assert. Maximum health lives at `+0x24` of that record.

### The int path handles only three properties — SOURCED

`0x00818170` is a chained-subtract dispatch, not a table:

```
sub edx, 0x20 ; je  -> property 32
sub edx, 9    ; je  -> property 41   (Energy)
sub edx, 1    ; jne -> everything else returns
              ;        property 42 (Health) falls through, handled inline
```

So on the integer path only 32, 41 and 42 do anything to this record. That is
consistent with the OBSERVED behaviour in `studies/enemy/PLAN.md` §6g, where int
property 42 set the maximum and refilled the bar, and it explains why int
property 42 was the only one of four death candidates that visibly did anything.

---

## 3. The jump table, exactly — SOURCED

`0x00818210`:

```
mov   edx, [ebp+8]                     ; prop_id
add   edx, -0x10                       ; properties below 16 are out of range
cmp   edx, 0x2E                        ; ... and above 62
ja    0x0081838B                       ; -> default
movzx edx, byte ptr [edx + 0x8183B8]   ; 47-entry byte table -> case index
jmp   dword ptr [edx*4 + 0x00818394]   ; 9-entry target table
```

| Case | Target | Property |
|---|---|---|
| 0 | `0x0081823C` | 16 |
| 1 | `0x00818276` | 33 |
| 2 | `0x0081828D` | 34 |
| 3 | `0x008182A5` | 43 |
| 4 | `0x008182C5` | 44 |
| 5 | `0x008182E6` | 52 |
| 6 | `0x0081830B` | 55 |
| 7 | `0x00818345` | 62 |
| 8 | `0x0081838B` | **default — the other 39 properties** |

Case 8's target is the same address as the `ja` out-of-range branch, which is
what identifies it as the default rather than a real case. That is an internal
consistency check the table could have failed and did not.

**Trap for anyone re-deriving this.** The `jmp` displacement (`0x818394`) is the
*second* table. Reading `0x8183B8` — the displacement in the `movzx` — as an
array of dwords produces plausible-looking garbage: values like `0x08080808` and
`0x8BEC8B55`, the latter being the bytes of `push ebp; mov ebp, esp`. This pass
made that exact mistake and caught it only because the "addresses" were absurd.

---

## 4. What this does not answer, and where death goes next

**Death is not an agent property**, on either path. The remaining leads, in
order:

1. **`0x005FC380`**, called by `0x00813040` immediately after the record update,
   with the target id and two out-parameters. Not yet read. It is the only other
   thing the damage path does.
2. **The agent view layer.** `P:\Code\Gw\AgentView\AvChar.cpp` is named by the
   assert that `studies/enemy/PLAN.md` §6b crashed on — `damage.amount <= 0` —
   so the view has its own damage handling, and a death *animation* would live
   there rather than in the status record.
3. **The agent's flags word at `+0x20`.** §6h found `0x002D`'s effect gated on
   bit `0x20000` of it. Whatever sets a "dead" state is plausibly another bit in
   the same word, and the writers of that word are enumerable.

**The int path was read only far enough to explain the three properties it
handles.** Properties above 42 on the integer path were not investigated, and
`PublicLevel` (36) — which drives the nameplate and is the one property this
project has OBSERVED the client accept without visible confirmation — is among
them.

---

## 5. Method, and how to reproduce

```bash
python toolkit/clientscan/msghandler.py 0x00A3 --follow
```

`msghandler.py` resolves a handler by table lookup from the message-format tables
recovered in [studies/msgtable](../msgtable/FINDINGS.md), and `--map` lists which
ArenaNet source file each handler asserts in. Walking past the handler into the
call tree was done with a scratch disassembler over the same `Image` class.

**A defect found and fixed during this pass**, recorded because it produced a
wrong reading before it was caught: `read_table()` masked opcodes with `0xFF`,
and 229 of the 477 receive opcodes are above `0xFF`. Lookups for those returned
whichever table entry the walk reached first, with nothing in the output to say
so. See `studies/enemy/PLAN.md` §6i.
