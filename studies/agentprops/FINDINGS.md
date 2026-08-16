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

**There are TWO dispatches, not one, and reading only the first produces a wrong
answer.** `0x00813040` updates the status record via `0x00818210` (the table
above) and then dispatches *again* on the same `prop_id` through a second table —
byte index at `0x0081328C`, 48 entries covering properties 16–63, targets at
`0x00813250`, **14 real cases**. The two do not agree on which properties matter:

| | record dispatch `0x818210` | second dispatch `0x813040` |
|---|---|---|
| properties acted on | 8 | 14 |
| handles 17, 18 | no | **yes** |
| handles 53, 56, 61, 63 | no | **yes** |

**Properties 16, 17 and 18 are three damage KINDS.** In the second dispatch they
converge on one call with a discriminator:

```
prop 16 -> push 0 \
prop 17 -> push 1  >  jmp 0x00813101 -> call 0x007DFB60(target, cause, value, …)
prop 18 -> push 2 /
```

So Headquarter's instinct to group 16 and 17 is right, and it identifies a third
kind (18) that OpenTyria leaves unnamed. **An earlier draft of this document said
17 "falls to the default case and does nothing" — that was written from the
record dispatch alone and is wrong.** What is true is narrower: 17 does not
modify the health record, but it does raise a damage notification. A plausible
reading, untested, is that a critical hit arrives as a 16 for the health change
plus a 17 for the annotation.

**The two health channels are not the same kind of quantity — SOURCED.** Within
the record dispatch:

```
prop 16 DAMAGE          fld  dword ptr [esi+0x24]   ; maximum health
prop 55 ARMOR_IGNORING  fmul dword ptr [ebp+0x0C]   ; × the value  -> a FRACTION
                        (byte-identical between the two)

prop 34 HealthModifier1 fld  dword ptr [ebp+0x0C]   ; the value, RAW
                        -> ABSOLUTE, and a different callee (0x009215F0)
```

**Property 34 is the only health property that takes a real quantity rather than
a proportion.** A server that treats the health properties uniformly is wrong by
a factor of maximum health on whichever one it guesses wrong, and neither
direction is signalled anywhere in the message.

**Death is not a named case in either dispatch** — but the read produced a
better death candidate than any of the five guesses that preceded it.
`studies/enemy/PLAN.md` had only ever sent properties 16 and 42. **Properties 34,
55 and 56 are health properties the client dispatches and this project has never
sent**, and 34 is absolute, so it is the only thing we hold that can name zero.
Damage cannot: it floors at 1 however hard it is hit. That is the `health_props`
probe.

---

## 1b. Tested against the client, and both readings held — OBSERVED

Probe `health_props`, 2026-08-06, build 38797, against a hostile NPC with
maximum health set to 100.

| Sent | Client showed |
|---|---|
| property 16 = `-0.5` (control) | **50 damage, with a floating number** |
| property 34 = `-50.0` | **no number at all**, bar 50 → **~0** |
| property 34 = `-1000.0` | nothing — the bar was already at the floor |
| property 55 = `-1.0` | **100 damage, with a floating number** |

**Absolute versus fraction is confirmed, and it could have been refuted.** If 34
had been a fraction, `-50.0` against a maximum of 100 would have arrived as 5000
and the disassembly would have been wrong. It arrived as exactly 50. And `-1.0`
on property 55 arrived as exactly 100 — the whole bar — which is the fraction
reading landing on the nose.

**Property 34 is silent.** No floating number, where 16 and 55 both produce one.
That matches the second dispatch, where 16/17/18 converge on the damage
notifier and 34 has its own separate case: **34 changes health without claiming
anybody did it.** For an emulator that is the more useful of the two — it is how
you would set an NPC's starting health, apply regeneration, or heal, without
spraying combat numbers over the screen.

**And the finding that matters most: health reached zero and nothing died.** The
bar emptied and the agent kept standing. Combined with §3b, this is decisive:

> **Zero health is not death, client-side, and no agent property is death.**

---

## 1c. Death is bit 4 of the agent effects word — OBSERVED, both directions

Probe `death`, 2026-08-06, build 38797, against a hostile NPC.

| Sent | Client showed |
|---|---|
| property 16 = `-0.5` (control) | 50 damage — the session reproduces |
| `AGENT_UPDATE_EFFECTS` (`0x00F1`), effects = **`0x10`** | **dead** — the body drops, the nameplate and the target both disappear |
| `AGENT_UPDATE_EFFECTS`, effects = **`0`** | **resurrected**, at ~0–1 health, and needs re-clicking to retarget |

**`0x00F1 [agent_id, effects]` with bit 4 set kills an agent, and clearing it
brings the agent back.** Bidirectional, which is the strong form of the result:
plenty of things can break an agent once, but a mechanism that reverses cleanly
is the mechanism itself rather than a symptom of it.

This was predicted from the binary before it was sent — §2's two uses of the
`+0x30` word — so it is a reading confirmed by measurement rather than a guess
that happened to work. **Seven earlier attempts, all guesses at a death
*message*, all failed** (`studies/enemy/PLAN.md` §6f–§6i). Death was never a
message.

Three consequences worth having:

- **Death drops the client's target.** The nameplate goes with the body, so a
  server cannot assume a client still has a dead agent selected.
- **Reviving does not restore health.** The body came back at ~0–1, because the
  death path had already zeroed the pools (§2, `fldz` into `0x009215F0` and
  `0x00921780`). A resurrect is therefore **two** operations: clear the bit, then
  set health. Sending only the first leaves a living agent that dies to any
  scratch.
- **It explains the refill mystery.** Int property 42 always refilled the health
  bar, in every probe that used it, because the health path checks
  `!((effects >> 4) & 1)` first. The client only refills an agent it does not
  believe is dead. That behaviour was OBSERVED days before the reason was found.

  **SUPERSEDED 2026-08-13 (note added 2026-08-16): the refill reading itself
  was wrong.** Property 42 grants a delta — `health += (new_max − old_max)` —
  and never refills: measured by HUD numbers rather than bar fills, raising the
  max gave exactly old health plus the difference, reversibly, and re-sending
  the current maximum is a no-op (harness 20260813T215004,
  `../profession/RESKIN.md` §18.13; encoded at
  `toolkit/authsrv/agents.py:118-132`). The death-bit gate this bullet
  describes still stands on its own evidence; what it "explained" was a
  mis-reading of bar fills. See `../unitsetup/FINDINGS.md` §7, resolution 1.

**The effects word is a bitfield and only bit 4 is identified.** The other 31
bits are unread. Nothing here says what they are, and the client's own handler
tests only this one at `0x008183F0` — the rest are consumed elsewhere.

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

## 3b. The dispatch tables, and none of them is death — SOURCED

> **CORRECTED 2026-08-06. There are SEVEN switches, not four**, and this section
> read four of them. The heading used to read *"All four dispatch tables"*; the
> word *all* was wrong and it was load-bearing, because the argument below closes
> the death question **by enumeration**. An enumeration over four sevenths is not
> an enumeration. `studies/skillcast/FINDINGS.md` §16.1 has the full set and
> `toolkit/clientscan/genericvalue.py` is now the executable authority —
> `consumers(img)` reports every switch that acts on an id and
> `handled_by_nothing(img)` reports the ids none does.
>
> **The conclusion survives, and it survives on better evidence than it had.**
> None of the three missing switches contains a death case either: the int main
> switch dispatches to `AvApi` and the UI, and the two AgentView switches carry
> five ids between them (4, 8, 13, 50, 60 and 5, 51, 61). Death was independently
> found afterwards, and it is not a property at all — §1c, bit 4 of the agent
> effects word. So this section reached a true answer by an argument weaker than
> the one it stated.

Each property message updates a status record and then dispatches again — more
than once, which is the part this section originally missed. In dispatch order:

| # | Path | Table | Range | Real cases |
|---|---|---|---|---|
| 1 | int, record | `0x00818170` | chained `sub`, not a table | 3 — properties 32, 41, 42 |
| 2 | int, AgentView | bytes `0x0081BD44` → `0x0081BD30` | properties 4–60 | 5 — 4, 8, 13, 50, 60 |
| 3 | int, second | bytes `0x00812EE0` → `0x00812ED0` | properties 4–64 | 4 — {4, 50, 60}, {10}, {64}, and one generic case for the other 55 |
| 4 | **int, main** | bytes `0x00812FE0` → `0x00812F20` | properties 0–66 | **47** |
| 5 | float, record | bytes `0x008183B8` → `0x00818394` | properties 16–62 | 8 — 16, 33, 34, 43, 44, 52, 55, 62 |
| 6 | float, AgentView | chained `cmp`, not a table | 5, 51, 61 | 3, sharing one body |
| 7 | float, second | bytes `0x0081328C` → `0x00813250` | properties 16–63 | 14 |

Rows 2 and 6 run **only when the message's agent resolves to an object of type
1**, and rows 4 and 7 are skipped entirely when bit 1 of `charContext + 0x53C`
is set. Rows 2, 4 and 6 are the ones this section did not have.

**No case in any of the seven is death.** Together with the OBSERVED result in
§1b — health driven to zero on a live agent, which kept standing — the property
channel is closed as a route to death, and it is closed by enumeration rather
than by another failed guess. §1c then found death elsewhere, which is the real
confirmation.

### What §2's "only three properties" got right, and who noticed

§2's reading of `0x00818170` — *"on the integer path only 32, 41 and 42 do
anything to this record"* — is **correct and was correct first**.
`studies/skillcast` §6 later published the opposite about the same address,
claiming every property is recorded there, and nothing in this repository caught
it for two days: the tests are per-study, and the next pass re-derived the answer
from scratch rather than finding it one directory away. Recorded here as well as
there, because a correction filed only in the study that was wrong is invisible
from the study that was right.

### A false lead, killed and recorded so nobody re-chases it

The image contains the literal string `"owner dead"`, which is the only
death-shaped string in 10 MB and looks irresistible. It is `EOWNERDEAD` from the
C++ standard library, sitting in a pointer table between `"value too large"` and
`"protocol error"`, alongside `"host unreachable"` and `"bad file descriptor"`.
It has nothing to do with agents. **NOT FOUND** stands.

---

## 4. What this does not answer, and where death goes next

**Death is not an agent property, and zero health is not death.** Both are now
settled by enumeration plus measurement rather than by guessing. Seven candidate
mechanisms have been eliminated: `AGENT_PLAYER_DIE` on an NPC and on the player,
`AGENT_ALLY_DESTROY`, float health = 0, int health = 0, damage past the floor,
and an absolute health modifier past zero.

The remaining leads, best first:

1. **The agent effects word.** `GAME_SMSG_AGENT_INITIAL_EFFECTS` (`0x00F0`) and
   `AGENT_UPDATE_EFFECTS` (`0x00F1`) carry a bitfield, and OpenTyria's own agent
   struct has a `uint32_t effects` beside health and level. A "dead" bit in a
   state word fits every negative above: it would explain why no property and no
   dedicated message kills, and why the client keeps an agent standing at zero
   health until told otherwise. **Read `0x00F1`'s handler before sending
   anything** — that is what the last two rounds of this arc taught.
2. **The agent's flags word at `+0x20`.** `studies/enemy/PLAN.md` §6h found
   `0x002D`'s whole effect gated on bit `0x20000` of it. Whatever marks an agent
   dead is plausibly another bit in the same word, and its writers are
   enumerable.
3. **`0x005FC380`**, called by `0x00813040` right after the record update with
   the target id and two out-parameters. Still unread, and still the only other
   thing the damage path does.

**Not investigated:** what the int path's generic case (`0x008129B0`, ~55
properties) actually does. `PublicLevel` (36) goes there, and it is the property
this project has OBSERVED the client accept three times without ever confirming
a visible effect.

> **CORRECTED 2026-08-16, by running the executable authority §3b names.**
> Both halves of the paragraph above are stale.
> `genericvalue.py --id 36` derives that 36 does NOT fall to a generic case —
> it has a real int-main case body at `0x00812D6E` (build 38797, pinned
> pristine), and disassembly (`codescan.py --dis 0x00812D6E`) shows two
> container calls keyed on the agent id against manager+0x7CC (`0x00817BE0`,
> then `0x0080BC90` returning the per-agent entry), a store of the value to
> **entry+0x2C**, and a call to `0x007DFE10(agent, value)` — a persistent
> per-agent write plus a notification, SOURCED. And "never confirming a
> visible effect" expired separately: prop 36 = 1/15/20 moved the party-roster
> level readout `W1`/`W15`/`W20` exactly
> (`../profession/RESKIN.md`, harness 20260813T172323). See
> `../unitsetup/FINDINGS.md` §8 Q4 and §7 resolution 3.

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

## 1d. Property 34 is a FRACTION too — OBSERVED, from a crash and then from the code

**2026-08-11.** §1's reading had property 16 a fraction of maximum health and property
34 an absolute quantity. **Both are fractions.** The difference is only who multiplies,
and the client says so in three instructions.

**How it surfaced.** `revive_due` sent property 34 with `max_health` — 100.0 — and the
client asserted two seconds after the first kill this server drove to a revive:

```
Assertion: fraction <= 1.0f      P:\Code\Gw\Char\CharPool.cpp(84)     Build: 38797
```

**Reading a crash trace at all needs one step nothing here had recorded: it is
ASLR-rebased.** The dump's `BaseAddr: 007A0000` against the PE's `ImageBase 0x00400000`
makes every address in it **+0x3A0000** from the file. Disassembling the raw trace
addresses yields plausible-looking garbage — `int1`, `aas`, `xchg ebp, eax` — rather than
an error, which is the failure mode worth naming. Subtract 0x3A0000 first.

**The dispatcher, at `0x00818210`:**

```
00818216  mov   esi, ecx                          ; this
0081821D  mov   edx, [ebp+8]                      ; the PROPERTY ID
00818222  add   edx, -0x10                        ; ids start at 16
00818225  cmp   edx, 0x2e
00818228  ja    0x81838b                          ; 16..62 or the client ignores it
0081822E  movzx edx, byte ptr [edx+0x8183b8]      ; index byte, one per id
00818235  jmp   dword ptr [edx*4+0x818394]        ; nine arms
```

| property | index | arm | what it does |
|---|---|---|---|
| **16** `PROP_DAMAGE` | 0 | `0x0081823C` | `fld [esi+0x24]` (the MAX) / **`fmul [ebp+0xc]`** / → `0x00921510` |
| 33 (unnamed by us) | 1 | `0x00818276` | raw value → `0x009215F0`, pool at `esi` |
| **34** `GV_HEALTH` | 2 | `0x0081828D` | raw value, **no fmul** → `0x009215F0`, pool at `esi+0x20` |
| 43 (unnamed by us) | 3 | `0x008182A5` | `fld [esi+4]` / `fmul` |
| 44 `GV_CHANGE_HEALTH_REGEN` | 4 | `0x008182C5` | |
| 52 `GV_ENERGY_GAIN` | 5 | `0x008182E6` | |
| 55 `GV_ARMOR_IGNORING` | 6 | `0x0081830B` | |
| 62 `GV_ENERGY_SPENT` | 7 | `0x00818345` | |
| **39 of the 47 ids**, incl. 42 and 61 | 8 | `0x0081838B` | the `ja` default. Ids 17–32, 35–41, 45–51, 53–54 and 56–61 all land here — the client acts on only **8** of the 47 it accepts. 42 is an INT-channel property, correctly absent |

`0x009215F0 + 0x23 = 0x00921613`, which is the crash's own return address, so
**`0x009215F0` is the CharPool method whose line 84 asserts `fraction <= 1.0f`** and
property 34 is what it range-checks.

**The decode is checked rather than fitted.** Every property this repo had already named
independently — 16, 44, 52, 55, 62 — lands on a *distinct* arm, and the ones we named that
land on the default include 42, which we know is int-channel. A mis-derived table would not
sort our own constants that way.

**The default is the common case, and the first version of this table hid that** by listing
only the ids we happen to have names for: **39 of the 47 accepted ids fall to arm 8**. The
client accepts the range 16..62 and acts on eight values in it. So "property N is in range"
says almost nothing, and an unnamed id is far more likely to be silently ignored than
handled.

**Why nothing found this in twenty sessions: the bound is `<=`, so it only fires
positive.** Every value ever put on this channel was damage — `-HIT_FRACTION`, and the
`-50.0` behind `GV_HEALTH`'s note. A negative passes however absurd it is. The whole
damage side of the arc tested that bound vacuously.

**CONTESTED, and left that way on purpose.** `GV_HEALTH`'s old note — "a DELTA, we
measured -50.0 as -50 health" (§1b) — cannot be read off arm 2, which applies no scaling
and hands the value to something that calls it a fraction; -50.0 as a fraction is -50× the
pool, which empties it, and that is not "50 off a 100 max". **One probe settles it: send
-0.5 at a 100-max agent and see whether 50 comes off.** Not run — the harness was in use.

## 1e. Property 34 is a SETTER — OBSERVED, and it refutes §1b, §1d *and* the probe's own prediction

**2026-08-11**, probe `pool_fraction`, build 38797, capture
`authsrv-20260811T144527`. Read off the **player's health orb**, which shows a number
rather than a bar — the probe is handed `PLAYER_AGENT_ID`, which §1d's write-up had
wrong when it said to watch the hostile.

| step | sent | orb |
|---|---|---|
| baseline | max health 100 (int property 42) | **100** |
| control | property 16 = **-0.10** | **90** |
| the question | property 34 = **-0.50** | **1** |
| again | property 34 = **-0.50** | **1** |

**Property 34 sets the pool to `fraction × maximum`.** `-0.5` sets it to `-50`, which
clamps to the floor of 1 — and does so *again* on the second send, because a setter is
idempotent where a delta is not.

**Every rival dies on the third row.** A delta of `0.5 × 100` from 90 predicts **40**.
An absolute delta of `0.5` predicts **89.5**. The floor is what happened.

**Three claims are corrected here, and one of them is this probe's own.**

**§1b — "a DELTA, not a setter" — is exactly backwards.** Its measurement sent `-50.0`
at a bar *already down to 50*, and read the resulting empty bar as "it arrived as exactly
50". Both hypotheses predict an empty bar there, so the row could not discriminate; §1b's
own next line records the follow-up doing nothing because "the bar was already at the
floor", which is the floor being observed twice and read as a subtraction once. §1b's
*other* rows are unaffected and remain good: property 16 at `-0.5` gave exactly 50 on a
full bar, and property 55 at `-1.0` gave exactly 100.

**§1d had the arithmetic right and the meaning wrong.** Arm 2 really does apply no `fmul`
— but that is because `0x009215F0` does the scaling itself as part of setting, not
because the value reaches the pool unscaled. "A fraction the client does not scale" was a
conclusion drawn one frame too early.

**And the prediction stated in `probes.py` before the run was refuted.** It said FRACTION,
meaning "the bar drops to about half". The argument *is* a fraction, so the label was
right and the behaviour it predicted was wrong — which is the failure mode a probe with a
written prediction exists to catch, and it is left in the file rather than tidied away.

**It also explains the crash, better than §1d did.** `CharPool.cpp:84` asserts
`fraction <= 1.0f` because **a setter cannot exceed the maximum**. `revive_due`'s
`max_health` was not merely a number too large; it was the wrong *kind* of number. And
`1.0` is right for the strongest possible reason: it sets the pool full, which is what a
revive means, from a pool the client's death path had zeroed.

**Still not established:** whether the floor of 1 is the pool's own clamp (as §1's
`PROP_DAMAGE` note says: "Floors at 1: cannot kill") or something in this path
specifically. Both sends landed there, so this run cannot separate them.

---

## 1f. `Health non-zero on resurrect` — the client's own complaint, and what it checks

**[OBSERVED] 2026-08-13.** `Gw.log` carries an `Error:` line our own s2c produces, and it
has been there the whole time: **49 occurrences across the vault's harness reports** —
47 `Test Warrior: Health non-zero on resurrect` (the player) and 2
`Corpse of Hatcher [Collector]: …` (an NPC). `studies/reconstruction` §4.11 counted it at
19 and listed it as one of three game-logic complaints worth reading; nothing had read it.

**The check is measured, not inferred.** The string is UTF-16 in `.rdata` at
`0x00A94044`, and exactly one instruction in the image references it —
`push 0xa94044` at `0x007FE16C`, reached from:

    007FE134  fld  dword ptr [edi + 0x134]      ; A
    007FE13D  fld  dword ptr [edi + 0x130]      ; B
    007FE14C  fcom st(1)                        ; ... selects the MINIMUM of A and B
    007FE161  fldz
    007FE163  fucompp                           ; min(A, B) == 0.0 ?
    007FE16A  jnp  0x7fe183                     ; equal -> skip the log
    007FE16C  push 0xa94044                     ; not equal -> log it, severity 2

So the client requires **`min(f32 @ +0x130, f32 @ +0x134) == 0.0` at the moment a
character is resurrected**, and says so when it is not. Two adjacent floats on the
character object, both expected empty on a corpse: the shape of the two pools the death
path zeroes at `0x008183F0` (§1c's `fldz`).

**What we send, in both revive paths** (`revive_due`, `player_revive_due`):

    AGENT_UPDATE_STATUS(agent, 0)        clears the death bit  -- the resurrect
    AGENT_PROPERTY_UPDATE_INT(HEALTH_MAX)
    AGENT_PROPERTY_UPDATE_FLOAT_TARGET(GV_HEALTH, fraction 1.0)

**[UNVERIFIED] Why it fires is NOT established, and two readings survive.** Either the
resurrect check runs deferred — a frame or a tick after the message that cleared the bit —
by which time our two pool sends have already landed and refilled it; or something
leaves a pool non-zero before the bit clears. The three messages leave in one burst
microseconds apart, and nothing here can separate those from the log alone: `Gw.log`
lines carry no timestamps, so they cannot be joined to the capture.

**The experiment, which needs one client and about a minute.** Send the death-bit clear
**alone**, wait a tick, then send `HEALTH_MAX` and the fraction; a run with an enemy
(`--enemy`) produces a kill/revive cycle every ~13 s, so one hold gives several. The log
line disappearing is the result; it staying is the more interesting one, because it
would rule out ordering and point at the pools never having been zeroed.

### 1f-RESULT. The experiment ran, and it is ORDERING

**[OBSERVED] 2026-08-13.** Three harness runs of the same shape (`--enemy --keep-open
--hold 150..180`, so the hostile kills the player every ~14 s and each run gives a dozen
revives), differing ONLY in how long the two pool refills wait after the death bit
clears:

| refill defer | session | revives | `Health non-zero on resurrect` |
|---|---|---|---|
| **0.00 s** (the shipped burst) | 196.6 s | 13 | **13** |
| 0.05 s (one tick) | 167.7 s | 11 | **0** |
| 0.25 s (five ticks) | 197.7 s | 13 | **0** |

**One complaint per revive with the burst, none with a single tick between.** So of §1f's
two surviving readings the FIRST is right: the client's resurrect check runs after the
message that clears the death bit is processed, and our refills were landing before it,
refilling the pools the client was about to inspect. The pools were being zeroed
correctly all along -- nothing was ever wrong with the death path.

**The death counts scale with session length** (14 in 196 s, 12 in 167 s), which is the
control that matters: a deferred refill that failed to arrive would leave the player
standing up empty and dying instantly, and the cycle would speed up. It did not.

`REVIVE_REFILL_DEFER` is now `TICK_SECONDS` by default -- expressed as one tick rather
than 0.05 so it stays one tick if the rate moves -- and `RURIK_REVIVE_DEFER=0` restores
the burst, which is what keeps the control above reproducible. `test_agentlife` pins both
halves as a PAIR: the revive must not carry the refill, and the deferred half must
actually send it. Either check alone is satisfied by a broken server.

**The agent path now defers too, and its measurement status is NOT the player's.**
`revive_due` sent the same three messages in the same burst, and the client's resurrect
check is on the CHARACTER rather than on whose it is -- 2 of the vault's 49 complaints
name `Corpse of Hatcher [Collector]`. It has the same one-tick defer as of 2026-08-13.

**MEASURED 2026-08-13, unattended.** Two runs identical but for the constant, each
21 player hits and 3 agent deaths:

| refill defer | agent revives | `Corpse of Hatcher [Collector]: Health non-zero on resurrect` |
|---|---|---|
| **0.00 s** (burst) | 3 | **3** |
| 0.05 s (one tick) | 3 | **0** |

So the agent path is the player path: same check, same cause, same fix, and now the same
standard of evidence.

**Getting there needed two things, and both were mis-diagnosed first.** `hit agent` was
0 for four runs, read first as a wrong keybind and then as synthetic keys missing the
client's raw input path. Neither:

1. **The player loses the fight.** The Hatcher deals 25 into a 100 HP player -- four
   hits -- while killing it takes seven, so the player is dead before landing one.
   `--practice-target` makes the standing hostile neither chase nor attack, which is a
   real creature's behaviour rather than a test switch: WIKI (GWW, "Practice target",
   rev. 2014-02-07) -- practice targets are stationary NPCs, there are allied and
   hostile ones, "They do not use any skills", and a slain hostile one resurrects after
   30 s at full health. The content field it sets, `attacks_back`, already existed and
   already gated both the attack tick and the chase; only the switch was missing.
2. **An OUTPOST forbids attacking.** With a passive target the player survived and STILL
   landed nothing -- `0x00C1` TARGET_SELECT went out on every `C` press and no attack
   followed. `--explorable` fixes it and the run went from 0 hits to 21, with the
   client's attack arriving as `0x0026`.

**The recipe, which is the reusable part** (also in `RUNBOOK.md`):

```
python toolkit/harness/session.py --enemy --keep-open --game-args "--practice-target --explorable" --hold 30   --actions "0:play 20:vk:0x43 1:vk:0x20 25:vk:0x43 1:vk:0x20 25:vk:0x43 1:vk:0x20"
```

`0x43` is `C` (select closest), `0x20` is `Space` (attack). `Tab` (`0x09`) also works and
selects the NEXT target. Three attack commands gave 21 hits and 3 kills in 30 s.

**Do not "fix" this by reordering on the strength of the reading above.** The severity is
2 and nothing visible is wrong — the bar refills correctly, OBSERVED twice in §1e — so
this is a correctness complaint from the client about our message order, not a symptom
anybody has seen. It earns an experiment, not a guess.
