# The cast lifecycle, read out of the client

`studies/skills/FINDINGS.md` §8 lists four open questions about casting. All
four had real handler addresses and nobody had read what the handlers do. This
is that read: purely static, against the pinned build-38797 `Gw.exe` in the
vault. No client was launched, no packet was sent, nothing was patched.

**Nothing here is OBSERVED.** Reading disassembly tells you what code does, not
what the game means. The strongest label anything below can carry is SOURCED —
the client's own words, in ArenaNet's own identifiers — and most of it is
INFERRED from those words. §11 is the probe queue that would convert the useful
half into observations, ranked cheapest-and-most-decisive first, and every probe
in it is committed and executable in `toolkit/authsrv/probes.py`.

## Labels used throughout

| Label | Meaning |
|---|---|
| **SOURCED** | ArenaNet's own text or code, quoted: an assert expression, a log format string, a compiled constant. The client said it, not us. |
| **MEASURED** | We counted it in the image ourselves, and `toolkit/clientscan/test_skillcast.py` re-counts it. |
| **INFERRED** | Our reading of what SOURCED/MEASURED facts mean. This is where the mistakes will be. |
| **CORROBORATED** | The binary and an independent reconstruction agree, and the reconstruction is named. |
| **CONTESTED** | Sources disagree; the binary is recorded as the tiebreak and the loser is named. |
| **REFUTED** | We believed it during this pass and the artifact said no. §10 keeps these so nobody retries them. |
| **NOT FOUND** | We looked, and recorded where. |
| **UPSTREAM** | A reconstruction says this. Not a fact about retail Guild Wars. |

---

## The answer in one page

**`skill_instance` is the bar slot's *copy index*, and the client says so in
words.** The handler shared by opcodes 226 and 227 logs
`"Pending skill %u copy %d not found"` with the message's second and third
fields as its two arguments. Every lifecycle handler resolves the affected bar
slot by matching **both** `slot+0x0C == field 2` and `slot+0x10 == field 3`, and
a `ChCliApi` accessor hands those same two members back to the UI as
`charCliSkillId` and `charCliSkillCopy` — named by `GmSkSlot.cpp`'s own asserts.
GWCA supplied only the name `skill_instance`; every other lineage records it as
NOT FOUND. (§3.)

**Slot+0x10 is filled straight out of `SKILLBAR_UPDATE`'s second array — the
one every catalogue calls `pvp_masks`.** So the server assigns the copy index
per slot at skillbar-load time; it is not a per-cast counter and not a slot
number. It also has a job: when the bar is reloaded with the trailing byte set
to 0, the client merges the old bar into the new one keyed on
`(skill_id, copy)`, preserving recharge and adrenaline for slots whose pair did
not change. That is what the field is *for*. (§4.)

**Opcode 228 does not animate anything, and for your own character it does
nothing at all.** Its handler asks for the local player's agent id and returns
immediately if the message names it — because `ChCliApiUseSkill` already
inserted the pending-cast entry when you pressed the key, by calling *the same
function* opcode 228 dispatches to. That function is refcounted precisely so
the two paths compose. The cast animation comes from the property channel:
agent property 60 reaches `AvApi` and queues an AgentView event carrying the
skill id. This answers §8's animation question and corroborates the movement
pass's architecture — the client predicts, the server confirms. (§6, §7.)

**The two unnamed opcodes are recharge-state messages, not lifecycle
messages.** 231 writes `recharge = 0xFFFFFFFF` and tells the UI the remaining
time is `+infinity` — a disable. 232 sets the recharge clock from an IEEE
**float** field (seconds × 1000.0) and reports a second number alongside it,
which reads as remaining-vs-total. Neither is the "skill done" message the
named catalogue lacks. (§5.)

**Opcode 211 writes a second skill bitmap that nothing in the image reads.**
Its write path has exactly one caller — its own handler — and unlike 219 it
broadcasts no UI notification. (§8.)

**And one methodological result that outranks all of the above for anyone
repeating this work.** More than half the client's field descriptors are zero
in the file and written by load-time initializers, and a zero decodes as a
perfectly legal four-byte field. The first draft of this study read opcode
0x00E5 as four dwords totalling 18 bytes. It is `agent_id, u16, u32, u32`
totalling 16, exactly as ldufr's catalogue always said, and **nothing in the
output hinted that the first reading was wrong.** §10 has the details; the
recovery is now in `msgshape.py` and the test reproduces `studies/msgtable`'s
four-message oracle, which the naive reader got wrong 4 for 4.

---

## 1. Method, and the two tools this needed

The method is `studies/msgtable`'s, and CLAUDE.md's: read the client's own
words rather than reason about its bytes. ArenaNet compiled its assert
expressions into the shipping image as ASCII, and they are written in
ArenaNet's identifiers.

`toolkit/clientscan/asserts.py` (new, stdlib only) enumerates them. MSVC
compiled every assertion to the same four instructions:

```
push  <line>            6A ll                 or  68 ll ll ll ll
mov   edx, <file>       BA <va of "P:\Code\...">
mov   ecx, <expr>       B9 <va of "skill->skillId != 0">
call  <assert>          E8 <rel32>
```

MEASURED: **19,620 sites on build 38797, and every single one calls the same
routine at VA `0x00487BC0`.** That unanimity is the check — a fifteen-byte
pattern would otherwise be expected to collide with unrelated code, and
19620/19620 agreeing on one callee says the matches are real. `asserts.py`
asserts it, so a build that changes the idiom fails loudly instead of returning
a thinner list that still looks plausible.

937 distinct `P:\Code\...` paths exist in the image. The ones this study lives
in:

```
P:\Code\Gw\Char\Cli\ChCliSkill.cpp     the skillbar and the pending-cast array
P:\Code\Gw\Char\Cli\ChCliApi.cpp       the public accessors, and UseSkill
P:\Code\Gw\Char\CharMsg.cpp            the client-to-server senders
P:\Code\Gw\Ui\Game\GmSkSlot.cpp        one bar slot; names the fields it caches
P:\Code\Gw\AgentView\AvApi.cpp         the animation layer
```

`toolkit/clientscan/msgshape.py` (new, stdlib only) decodes wire shapes from
the format tables, and recovers the load-time initializer writes rather than
trusting the file. See §10 — that recovery is the difference between this
study and a wrong one.

`toolkit/clientscan/msghandler.py` gained `--annotate`, `--depth` and
`--callers`. With them the decisive evidence is one command:

```bash
python toolkit/clientscan/msghandler.py 0x00E2 --follow --depth 3 --annotate --exe <pinned exe>
```

which prints, among the rest,
`push 0xa95c94   ; "Pending skill %u copy %d not found"`.

---

## 2. The structure everything hangs on — SOURCED and MEASURED

The client keeps one record per agent that has a skillbar, in a sorted array
binary-searched by agent id. ArenaNet's name for the record is visible in its
asserts: `ChCliSkill.cpp` says `hotKeyState` (line 718) and
`hotKey < arrsize(hotKeyState->hotKey)` (lines 124, 177, 205, 681). A *hot key*
is a bar slot, and `CHAR_SKILL_HOTKEYS` is the bound — 8, compared as an
immediate at every one of those sites.

```c
struct HotKey {                  // 0x14 = 20 bytes
    /* +0x00 */ uint32_t adrenaline_a;   // GWCA's name; zeroed on recharge
    /* +0x04 */ uint32_t adrenaline_b;   // GWCA's name; zeroed on recharge
    /* +0x08 */ uint32_t recharge;       // ABSOLUTE ms timestamp. 0 = ready,
                                         // 0xFFFFFFFF = disabled
    /* +0x0C */ uint32_t skillId;        // named by GmSkSlot:807
    /* +0x10 */ uint32_t skillCopy;      // named by GmSkSlot:808
};
struct HotKeyState {             // 0xBC = 188 bytes
    /* +0x00 */ uint32_t agent;          // the binary-search key
    /* +0x04 */ HotKey   hotKey[8];      // ends at +0xA4
    /* +0xA4 */ uint32_t disabledMask;   // bit n = hotKey[n] is disabled
    /* +0xA8 */ rtl::Array<Pending> pendingSkills;   // count at +0xB0
    /* +0xB8 */ uint32_t h00B8;          // compared against an argument; unread here
};
struct Pending {                 // 8 bytes, array kept sorted by key
    /* +0x00 */ uint32_t key;            // (skillId << 16) | skillCopy
    /* +0x04 */ uint32_t refCount;       // named by ChCliSkill:955
};
```

MEASURED, each pinned by a byte string the test re-checks:

| Fact | Where | Bytes |
|---|---|---|
| record stride 0xBC | `0x00820FBE` | `imul edi, eax, 0xbc` |
| slots start at +4 | `0x00822BC1` | `lea esi, [eax+4]` |
| slots end at +0xA4 | `0x00822BC4` | `add eax, 0xa4` |
| slot stride 0x14 | `0x00822BDB` | `add esi, 0x14` |
| pending array at +0xA8 | `0x00822F2D` | `lea esi, [eax+0xa8]` |
| pending key packing | `0x00822F33`/`36` | `shl ebx,0x10` / `add ebx,[ebp+0x10]` |
| new entry refCount = 1 | `0x0082303D` | `mov [eax+edi*8+4], 1` |

**CORROBORATED against GWCA**, whose 2026 `Skillbar`/`SkillbarSkill` structs
match this byte for byte — `agent_id` at +0, `skills[8]` at +4, `disabled` at
+0xA4, `cast_array` at +0xA8, `h00B8` at +0xB8, total 0xBC. Two corrections:

- **`SkillbarSkill.event` at +0x10 is `skillCopy`.** GWCA's name is not wrong
  about the offset, only about what lives there. §3.
- **`Skillbar.disabled` at +0xA4 is a per-slot bit mask**, not a flag: the
  accessor at `0x00821090` returns `(mask >> hotKey) & 1`.

**CONTESTED, settled against apoguita.** `Py4GW_Reforged_Native` models the
tail as `{h00A8[2], casting, h00B4[2]}`. The binary shows a 16-byte
`rtl::Array` at +0xA8 with capacity at +0xAC, count at +0xB0 and allocator at
+0xB4 — grown by `rtl::Array::Reserve` at `0x004739C0`, memmove-inserted, and
memmove-removed. GWCA's `SkillbarCastArray cast_array` is right; the older
layout is not. Anything Rurik writes about "the client's casting field" should
follow GWCA.

The six public accessors, all in `ChCliApi.cpp` around lines 6253-6288, each
of which asserts `agent || (context->clientFlags & CHAR_CLIENT_FLAG_SYNTH)`:

| VA | Reads | Returns |
|---|---|---|
| `0x00816EA0` | slot +0x0C and +0x10 | `(skillId, skillCopy)` out-params |
| `0x00816EF0` | slot +0x04 | adrenaline_b |
| `0x00816F40` | `+0xA4` | is slot `hotKey` disabled |
| `0x00816F90` | `+0xA8` keyed on the slot's own pair | is this slot casting |
| `0x00816FE0` | `+0xB8` | equality against an argument |
| `0x00817030` | slot +0x08 | remaining recharge |

The recharge accessor is worth spelling out because it defines two sentinel
values a server must respect:

```
recharge == 0            -> return 0            (ready)
recharge == 0xFFFFFFFF   -> return 0x7FFFFFFF   (INT_MAX remaining)
now >= recharge          -> return 1            (expired, not yet cleared)
otherwise                -> return recharge - now
```

GWCA's `GetRecharge()` models only the last line. **CORROBORATED in substance,
incomplete in the sentinels.**

---

## 3. `skill_instance` — answered

> §8: *"What is `skill_instance`, the third dword in all three lifecycle
> messages? NOT FOUND in every lineage. Only a real capture of a real cast
> would settle it, and there is no real server."*

**SOURCED.** The client's own log string, at VA `0x00A95C94`, emitted by the
handler that opcodes 226 and 227 share when the pending lookup fails:

```
Pending skill %u copy %d not found
```

Its two arguments are the message's second and third fields, pushed in that
order at `0x008230DE`-`0x008230E2`. ArenaNet's word for the third dword is
**copy**.

Four independent confirmations that this is the bar slot's copy index and not
something else:

1. **Every lifecycle handler matches on it.** Opcodes 229, 230, 231 and 232
   walk `hotKey[0..7]` and act on the slot where `+0x0C == field 2` **and**
   `+0x10 == field 3`. A slot *number* would not need a linear search; a global
   cast counter could not be compared against a resident bar field at all.
   (`0x00822BD1`/`0x00822BD6` and the identical pairs in the other three.)
2. **The accessor names it.** `ChCliApi` `0x00816EA0` → `ChCliSkill`
   `0x00821200` returns slot `+0x0C` into its third out-param and slot `+0x10`
   into its fourth, and `GmSkSlot.cpp` asserts on exactly those two returns:
   `charCliSkillId == m_skillId` (line 807) and
   `charCliSkillCopy == m_skillCopy` (line 808). A skill bar slot in the UI
   caches an id *and* a copy.
3. **The pending-cast key packs them together**: `key = (skillId << 16) | copy`.
   Which also bounds it — the copy index must fit in 16 bits, and
   `GmCtlSkListGroup:254` independently asserts `skillId < (1 << 16)`.
4. **The vocabulary is everywhere in `ChCliSkill.cpp`**: `sourceSkillCopy >= 0`
   (line 516), `(unsigned)sourceSkillCopy < copies` (line 1082), `copies`
   (line 1126), `!m_inventoryCountSortArray.Find(targetSkill)` (line 1066).
   The same module keeps a sorted `(skillId, count)` array of how many copies
   of each skill the character owns, and a "replace skill X copy N with skill
   Y" operation.

**INFERRED**, and this is the part a probe should settle: a *copy* is one owned
instance of a skill id, so two bar slots holding the same skill id are
disambiguated by it. In ordinary play every copy index will be **0**, which is
why nothing has ever broken from OpenTyria sending eight zeros by accident (its
`GameSrv_SendSkillbarUpdate` declares `n_pvp_masks = 8` and never writes the
array, so `BuildMsg`'s memset supplies them).

---

## 4. Where the client learns a slot's copy — SOURCED

**`SKILLBAR_UPDATE`'s second array is not `pvp_masks`.** Opcode 218's handler
chain reaches `0x008223B0`, whose per-slot loop is two stores:

```
0x008227A8   mov [ebx + 0x0c], eax     ; slot.skillId  = firstArray[i]
0x008227B3   mov [ebx + 0x10], eax     ; slot.skillCopy = secondArray[i]
```

`ebx` walks the eight slots at stride 0x14. The second array feeds exactly the
field every lifecycle message matches against. The name `pvp_masks` comes from
ldufr's catalogue and is carried into `schema/messages.json`; nothing in the
client treats it as a mask.

`SKILLBAR_UPDATE_SKILL` (opcode 217) does the same thing for one slot, at
`0x00822320`: assert `hotKey < arrsize(hotKeyState->hotKey)`, **zero the whole
20-byte slot** (so adrenaline and recharge reset), then write field 3 into
`+0x0C` and field 4 into `+0x10`.

**And the trailing byte of 218 is a mode flag.** MEASURED at `0x008223E4` and
`0x0082241E`:

| bar exists? | trailing byte | what happens |
|---|---|---|
| no | 0 | the message is **dropped entirely** |
| no | non-zero | the record is created |
| yes | non-zero | plain overwrite; adrenaline and recharge reset |
| yes | 0 | **merge**: the old eight slots are copied out, sorted by `(skillId, copy)`, and any new slot whose pair matches an old one inherits the old `adrenaline_a`, `adrenaline_b` and `recharge` |

That merge is what the copy index is *for*: swapping one skill on a live bar
must not reset the other seven cooldowns, and `(skillId, copy)` is the identity
that survives the reload. OpenTyria's uncited `unk1 = 1` therefore means
"create/replace", which is the right choice on the map-entry path and the wrong
one for a mid-instance bar edit.

**Corrected wire shapes** — see §10 for why an earlier draft of this section
said something different:

| Opcode | Shape from the client's own descriptors | Wire |
|---|---|---|
| 217 `SKILLBAR_UPDATE_SKILL` | `agent_id, u8 slot, u16 skillId, u32 skillCopy` | 13 |
| 218 `SKILLBAR_UPDATE` | `agent_id, array32[8] skills, array32[8] **skillCopy**, u8 mode` | 11..75 |

Both agree with ldufr's field widths exactly. Only the third field's *name*
changes, and it changes from a guess to the client's own word.

---

## 5. Opcodes 231 and 232 — named

> §8: *"Are opcodes 231 and 232 the missing 'skill done' / 'instant skill'
> messages?"*

**No, on both counts.** Both are recharge-state messages, and neither touches
the pending-cast array that the lifecycle messages 226/227/228 manipulate.

### 231 (`0x00E7`) — skill disabled

Shape `agent_id, u16 skillId, u32 skillCopy`, 12 wire bytes: identical to
`SKILL_RECHARGED`. Handler `0x00822D10`:

```
find the slot by (skillId, skillCopy)
adrenaline_a = 0; if (adrenaline_b) fire UI event 0x10000059; adrenaline_b = 0
recharge = 0xFFFFFFFF                                    ; 0x00822DC3
broadcast UI event 0x1000005D with {agent, skillId, skillCopy, +inf, +inf}
```

The float is the constant at `0x00948654`, which is `0x7F800000` — **positive
infinity**. Combined with the recharge accessor's `0xFFFFFFFF -> INT_MAX`
sentinel, 231 says "this skill is unavailable and no countdown applies". The
best short name is **`SKILL_DISABLED`**; nothing in the image spells it out, so
that name is ours (INFERRED) and marked as such.

Note the asymmetry that makes 231 refutable: `SKILL_RECHARGE` (229) explicitly
*skips* both 0 and `0xFFFFFFFF` when computing its timestamp (`0x00822C44`:
`test eax,eax; je bump; cmp eax,-1; jne done; inc eax`). Two reserved values,
and 230 and 231 write one each.

### 232 (`0x00E8`) — recharge with a fractional remaining time

Shape `agent_id, u16 skillId, u32 skillCopy, u32 A, u32 B`, 20 wire bytes. The
message-format table types field B as a plain 4-byte unsigned, but the
**handler loads it with `fld`** (`0x0091F707`, `d9 40 14`): it is an IEEE float
on the wire, and the generic deserializer never interprets it. Handler
`0x00822DF0`:

```
find the slot by (skillId, skillCopy)
if (B != 0.0f) recharge = GetSkillTimer() + (int)(B * 1000.0)   ; 0x00943898 = 1000.0
else           recharge = 0
broadcast UI event 0x1000005D with {agent, skillId, skillCopy, B, (float)A}
```

Compare 229, which does `recharge = GetSkillTimer() + field4 * 1000` with an
**integer** `imul ..., 0x3e8` and puts the same value in *both* UI floats. So:

- **SOURCED**: 229's fourth field is in whole **seconds** — Headquarter's
  single-source, uncited name `recharge_sec` is CORROBORATED by the ×1000.
- **SOURCED**: 232's field B is in seconds too, but fractional.
- **INFERRED**: the UI event carries `(remaining, total)`; they are equal in
  229 and 231 and differ in 232, and `A` is never used for anything except
  being handed to the UI beside `B`. A cooldown sweep needs a total to draw an
  angle against, and 232 is the only message that supplies one separately. The
  `skill_partial` probe tests exactly this by watching the sweep's starting
  angle.

The plausible role of 232 — a mid-instance resync, where a cooldown is already
partly elapsed — is **NOT FOUND**. Nothing in the image says when it is sent,
because the client only receives it.

### 226 / 227, and the duplicate name

MEASURED: opcodes 226 and 227 resolve to the **same** dispatch pointer
(`0x0091F650`), while 225 and 228 differ. So the client is physically incapable
of distinguishing `SKILL_INTERUPTED` from `SKILL_CANCEL`/`SKILL_ACTIVATED` —
they are one message with three names in the reconstructions. What the shared
handler does is release one reference on the pending-cast entry:

```
assert(pending->refCount)                        ; ChCliSkill:955
if (--pending->refCount == 0) {
    remove the entry from the sorted array
    broadcast UI event 0x1000005B {agent, skillId, skillCopy, 0}
}
```

and, when the lookup fails, log `"Pending skill %u copy %d not found"` at
level 2. `opcodes.h` defining 227 twice on consecutive lines is therefore
harmless *to the client* — but anyone importing that table still gets a silent
collision, which is what `studies/skills` warned about.

---

## 6. What triggers the cast animation — answered

> §8: *"What actually triggers the cast animation — 228, a property update, or
> the client's own prediction? No source we have answers it."*

**The property channel.** SOURCED, three steps:

1. `AGENT_PROPERTY_UPDATE_INT` (opcode 159) — whose real shape is
   `u32 prop_id, agent_id, u32 value`, prop_id first, CORROBORATING what
   `studies/skills` §2 already said — dispatches into `ChCliApi` at
   `0x008128F0`.
2. That function has two switches over the property id. In the first, MEASURED
   from its jump tables at `0x00812ED0`/`0x00812EE0`, **properties 4, 50 and 60
   — and only those three of the 61 in range — share one case body.** Our
   sources name 50 `CastAttackSkill`/`attack_skill_activated` and 60
   `CastSkill`. Three lineages agreeing on the *names* is one thing; the
   binary putting exactly those three in one bucket is an independent
   structural fact.
3. The case for property 60 calls `0x007E0200` in
   `P:\Code\Gw\AgentView\AvApi.cpp` (line ~1318, `assert(agent)`), which
   resolves the AgentView agent and calls `0x007F76D0`: allocate an AgentView
   event of kind **0x19**, store the target agent at `+0x30` and the **skill
   id** at `+0x34`. Property 50 goes to the same layer via `0x007E0100`,
   property 59 (`InterruptSkill`) to `0x007E01B0`.

**Opcode 228 never reaches AgentView.** Its handler (`0x008148F0`) touches only
the pending-cast array and a UI notification — and it does not even do that for
your own character:

```
0x008148FC   call 0x0080D3E0          ; the local player's agent id
0x00814904   cmp  eax, ecx            ; ecx = the message's agent_id
0x00814906   je   0x0081491A          ; ... return, having done nothing
```

INFERRED that `0x0080D3E0` returns the local player's agent id, on two grounds:
it asserts `!(playerId & CHAR_CLASS_BASE_MASK)` on its input (`ChCliApi:4809`)
and maps a player index through an array to a single dword; and that dword is
written into UI event `0x10000059`'s payload at `0x00822C16`, the same one-word
payload that `0x00822D8D` fills with the *message's* `agent_id`. Same field,
same type.

**INFERRED, and this is the useful conclusion for R4b:** opcode 228 is a
skill-bar bookkeeping message for *other* agents' casts, not a "start
animating" instruction, and the animation of any agent — including other
players — is driven by agent property 60. A server that sends 228 and expects
an animation will see nothing.

MEASURED, and refutable: `0x00812FE0` is a 67-entry index into a 48-entry jump
table, so the client's generic-value switch handles property ids **0..66** —
67 values, where our sources describe 66 — and 20 of them fall to the default
with no case body: `{5, 8, 10, 16, 17, 18, 33, 34, 40, 43, 44, 51, 52, 53, 55,
56, 61, 62, 63, 64}`. Among those are `SkillDamage = 10`, `EnergyRegen = 43`,
`HealthRegen = 44`, `CastTimeModifier = 61` and `Knockdown2 = 63`. That does
**not** mean they are unhandled — every property is stored into a 52-byte
per-agent record before the switch, at `0x00818170` — only that they have no
special behaviour in `ChCliApi`. The full mapping is dumped to
`vault/skillcast/generic-value-switch-38797.txt`.

---

## 7. What the client sends, and why 228 is refcounted — SOURCED

`ChCliApiUseSkill` is at `0x00816660`; `ChCliApi:5613` asserts
`hotKey < CHAR_SKILL_HOTKEYS` at its head. In order, it:

1. resolves the slot's `(skillId, skillCopy)` through the same accessor
   `GmSkSlot` uses;
2. bails if `skillId == 0`;
3. bails if `GetRecharge(agent, hotKey) != 0` — **the client refuses to send a
   cast while the skill is recharging**, so a server that never sends 229/230
   will get exactly one cast per skill per session;
4. reads the skill's constant row (`ConstSkill`'s `s_skill[]` accessor at
   `0x005A88B0`) and branches on the **type** at row `+0x0C` — CORROBORATING
   GWCA's `SkillType type` at that offset from an unrelated direction. Type 0
   and type 0x11 bail;
5. calls **`0x00822B80`** with `(agent, skillId, skillCopy)`;
6. sends the message.

Step 5 is the headline. `0x00822B80` is *the function opcode 228 dispatches
to*. MEASURED: it has exactly **two** direct callers in the whole image — the
opcode-228 handler and this one. So the client optimistically inserts its own
pending-cast entry when you press the key, and the server's confirmation, if it
arrives for someone else's benefit, increments the refcount rather than
duplicating the entry. **That is what `Pending.refCount` is for**, and it is
why 228 self-suppresses for the local player: without the suppression the
refcount would reach 2 and one `SKILL_ACTIVATED` would not release it.

CORROBORATED with Headquarter, which is a headless *client* and models exactly
this: send `USE_SKILL`, set `casting = true` optimistically, wait for 228 to
set `casting_confirmed`. The binary says the optimism is not Headquarter's
invention.

### `USE_SKILL`, and a second cast message nobody has named

The sender is in `P:\Code\Gw\Char\CharMsg.cpp` at `0x009208E0`: it writes
`0x46` into a 0x14-byte buffer and copies its four arguments into `+4`, `+8`,
`+0xC`, `+0x10` in order. The arguments, from step 6 above, are
`(skillId, skillCopy, arg3, arg4)`.

```c
// GAME_CMSG 70 / 0x0046, 15 wire bytes
struct UseSkill { uint32 skillId; uint32 skillCopy; AgentId target; uint8 flag; };
```

Field widths CORROBORATE ldufr exactly. The **names** are new: field 2 is the
skill copy, which Headquarter guesses is `flags` and apoguita's sniffer guesses
is `type`. **CONTESTED, and the binary is the client.**

And when the skill's type is **14**, the same four arguments go to a *different*
sender at `0x00920170`, which writes opcode **`0x27` = 39 decimal** — 15 bytes,
`agent_id, u32, u32, u8`. Opcode 39 is unnamed in every source we mirror. Type
14 is, from this build's own skill table, **attack skills**: rows 320-323 are
Hamstring, Wild Blow, Power Attack and Desperation Blow, 311 rows in total.
INFERRED, therefore: **the client has two cast messages, and the split is
attack-skill versus everything else** — which lines up with the property
vocabulary's parallel track (`CastAttackSkill = 50` beside `CastSkill = 60`,
`attack_skill_finished = 46` beside `skill_finished = 58`). The
`use_skill_capture` probe settles this with no packets from us: the current
test bar happens to be four non-attack skills and four attack skills, so
pressing keys 1-4 and 5-8 should produce two different opcodes.

---

## 8. Opcode 211 — what it is, and what it is not

> §8: *"What is opcode 211 — a third unlock-list-shaped message?"*

Shape confirmed: `array32[128]`, 4..516 wire bytes, byte-identical to opcodes
29 and 219. MEASURED, all three land in **different places**:

| Opcode | Destination | UI event |
|---|---|---|
| 29 `PVP_UPDATE_UNLOCKED_SKILLS` | *account* context + 0x124 | `0x100000C4` |
| 211 (unnamed) | ChCliSkill context + **0x00** | none |
| 219 `UPDATE_UNLOCKED_SKILLS` | ChCliSkill context + **0x10** | `0x1000005F` |

All three go through the same `rtl::BitArray::SetBytes` at `0x00473550`, which
grows the array to `ceil(bytes/4)` dwords, zero-fills the tail and asserts
`Bytes() >= bytes`.

**SOURCED, and a correction worth having:** the bitmap `GmSkSlot.cpp` calls
`unlockedSkills` and bit-tests before letting a skill onto the bar
(`unlockedSkills->BitTest(sourceSkillId)`, line 206) is fetched by
`0x00804840`, which returns *account context + 0x124* — **opcode 29's
bitmap, not 219's.** 219's bitmap is the character-level "do you own this
skill" set: `0x00821880` bit-tests it before consulting the per-skill copies
array, and `0x00811820` bit-tests it and broadcasts the answer as UI event
`0x100000A5`.

**Opcode 211's array has no reader we could find.** Three searches, and what
each of them can and cannot see:

- MEASURED: its write path `0x00821CC0` has exactly **one** direct caller, its
  own message handler. Nothing else writes that array.
- MEASURED: the ChCliSkill context has exactly **eight** entry points from
  `ChCliApi` (`add ecx, 0x700` at `0x008145B1`, `0x00814684`, `0x00814721`,
  `0x00814741`, `0x00814761`, `0x0081477E`, `0x00816E64`, `0x00816E8E`). Seven
  of the eight reach methods that touch only `+0x10`/`+0x18` (219's bitmap) or
  `+0x20`/`+0x28` (the copies array). Only `0x00821CC0` touches `+0x00`.
- MEASURED: a displacement search of `.text` for `mov`/`lea`/`cmp` against
  `[reg + 0x700..0x70C]` finds only the context's constructor and destructor.

**The limitation, stated because it matters:** a reader living *inside*
`ChCliSkill.cpp` would address the array as `[this]`/`[this+8]` with no
displacement, and none of the three searches above can see that. So this is
**NOT FOUND**, not "proven dead" — and the `unlock_211` probe exists so that a
null result is a recorded null rather than an untried question.

---

## 9. Where the reconstructions stand after this pass

| Claim | Source | Verdict against the binary |
|---|---|---|
| `Skillbar` is 0xBC bytes, `skills[8]` at +4, `cast_array` at +0xA8 | GWCA 2026 | **CORROBORATED**, byte for byte |
| `SkillbarSkill.event` at +0x10 | GWCA | **CONTESTED → it is `skillCopy`** |
| `Skillbar.disabled` at +0xA4 | GWCA | CORROBORATED; it is a per-slot **bit mask** |
| `Skillbar` tail is `{h00A8[2], casting, h00B4[2]}` | apoguita Py4GW | **REFUTED** — +0xA8 is a 16-byte `rtl::Array`, count at +0xB0 |
| `GetRecharge() = recharge - GetSkillTimer()` | GWCA | CORROBORATED, but misses the 0 and -1 sentinels |
| `SkillType type` at skill row +0x0C | GWCA | CORROBORATED — the client branches on it |
| `skill_instance` (name only) | GWCA, GWLP-R | **Named**: ArenaNet calls it `copy` |
| 218's second array is `pvp_masks` | ldufr, and `schema/messages.json` | **REFUTED** — it fills `HotKey.skillCopy` |
| 218's trailing byte `unk1 = 1` | OpenTyria, uncited | **Named**: create/replace vs preserve-state merge |
| 229's fourth field is `recharge_sec` | Headquarter, uncited | **CORROBORATED** — the handler multiplies by 1000 |
| 226 and 227 share a handler RVA | ldufr's extracted table | **CORROBORATED** on our build at `0x0091F650` |
| `USE_SKILL` field 2 is `flags` / `type` | Headquarter / apoguita | **REFUTED** — it is the skill copy |
| `USE_SKILL` is 15 bytes, `u32,u32,agent_id,u8` | ldufr | **CORROBORATED** exactly |
| the client casts optimistically, server confirms | Headquarter | **CORROBORATED** from the client's own code |
| 231/232 are "skill done" / "instant skill" | this project's own guess | **REFUTED** — both are recharge-state messages |

---

## 10. Readings this pass refuted, including our own

Kept so nobody retries them, in the manner of `pathmap.py`'s `Portal` docstring.

**1. "The skill lifecycle messages are all plain dwords" — REFUTED, and it was
ours.** The first draft of `msgshape.py` read the `cmds` arrays straight out of
the file and reported opcode 0x00E5 as four dwords, 18 wire bytes; 0x00E2 as
three dwords, 14 bytes; and `USE_SKILL` as four dwords, 18 bytes. Every one of
those is self-consistent, totals a believable number, and is wrong. The cause
is documented in `studies/msgtable` §6 and I walked straight into it anyway:
**1099 of the 2420 cmd slots on this build are zero in the file and written by
MSVC load-time initializers, and `0x00000000` decodes as a perfectly legal
type-0 four-byte field.** The tell was the msgtable oracle — 0x0029
`AGENT_MOVE_TO_POINT` came out as four dwords when that study had it as
`dword, vec2, u16, u16` — and without that oracle there would have been no
signal at all.

`msgshape.py` now recovers the initializer stores by a linear byte walk over
`.text`, accepting only stores whose destination is already a known cmd slot:

```
A1 <src32> ... A3 <dst32>        mov eax,[src] ; mov [dst],eax
8B 0D <src32> ... 89 0D <dst32>  the same through ecx/edx/ebx/esi/edi
B8 <imm32> ... A3 <dst32>        mov eax,imm   ; mov [dst],eax
C7 05 <dst32> <imm32>            mov [dst],imm
```

MEASURED: **1097 of the 1099** zero slots recovered — the identical count
`studies/msgtable` arrived at from PE base relocations, a method sharing
nothing with this one — the remaining two being that study's genuinely
never-written opcode-0 slots. All four oracle messages reproduce exactly, and
all 2008 descriptors satisfy the six invariants the client asserts about them,
with zero violations. A slot neither the file nor a store accounts for now
comes back as `None` and prints as `?`; it is never guessed past.

**The corrected shapes agree with ldufr's catalogue in every field width.** The
naive read would have had us "correcting" a source that was right.

**2. "The second array of 218 might be `pvp_masks` after all, and `skillCopy`
is filled from somewhere else" — considered and refuted** by the two adjacent
stores at `0x008227A8` and `0x008227B3`. There is no other writer of
`HotKey.skillCopy` except opcode 217.

**3. "Opcode 228 starts the animation" — refuted.** Its handler does not reach
`AvApi`, and for the local player it returns before doing anything at all.

**4. "219 is the bitmap that gates the skill picker" — refuted.** `GmSkSlot`'s
`unlockedSkills` is the account bitmap that opcode **29** fills. This does not
contradict `studies/skills` §9's OBSERVED result that the unlock bitmap gates
the picker — our server sends 29 and 219 together, so that experiment could not
separate them. A probe that sends only one of the two would.

---

## 11. The probe queue — what static analysis cannot settle

All six are committed and executable, with their predictions written before the
experiment, in `toolkit/authsrv/probes.py`. `python toolkit/authsrv/probes.py`
encodes every step against the live schema before a client run is spent.

Ranked cheapest and most decisive first.

| # | Probe | Question | Prediction |
|---|---|---|---|
| 1 | `use_skill_capture` | What does the client send on a key press? | **No packets from us.** Keys 1-4 (types 15/3/16/3) send CMSG 70; keys 5-8 (all type 14, attack skills) send CMSG **39**. Both 15 bytes. Fields of 70: `{skillId, skillCopy, target, u8}`, copy = 0. |
| 2 | `skill_copy` | Is field 3 the bar slot's copy index, delivered by 218's second array? | Load the bar with copies = 7. A recharge addressed to copy 0 does **nothing**; the same one addressed to copy 7 greys the slot and counts down. |
| 3 | `cast_anim` | 228 or property 60? | 228 addressed to the local player does nothing visible whatsoever. Property 60 with a skill id plays the animation. Step 4 should put `"Pending skill … copy … not found"` in `Gw.log`. |
| 4 | `skill_disable` | Is 231 "disabled"? | 231 freezes an in-flight cooldown permanently dark; a following 230 clears it instantly, long before the original duration elapses. |
| 5 | `skill_partial` | Is 232's float field seconds-remaining, and field 4 the total? | `field4 = 40, field5 = 10.0f` counts **ten** seconds, and the sweep starts about a quarter dark. `field5 = 2.5f` gives a fractional sweep 229 cannot express. |
| 6 | `unlock_211` | What is opcode 211? | **Nothing observable.** A null result is the expected result and worth recording; any visible effect refutes §8 and is more interesting still. |

Two more that need no probe machinery, only a session:

- **Does 218 with a trailing byte of 0 preserve cooldowns?** Start a recharge,
  then resend the identical bar with mode 0 and again with mode 1. Prediction:
  mode 0 keeps the countdown running, mode 1 resets it to ready.
- **Does the client refuse to send `USE_SKILL` while recharging?** Send 229 for
  30 seconds and hammer the key. Prediction: not one CMSG leaves the client
  until 230 arrives or the timer expires.

---

## 12. Reproducing this

```bash
EXE=vault/run/2026-07-29_221c13772c7a/Gw.exe

python toolkit/clientscan/test_skillcast.py                    # everything above, checked
python toolkit/clientscan/asserts.py --exe $EXE --file ChCliSkill --unique
python toolkit/clientscan/asserts.py --exe $EXE --grep "skillCopy|pending"
python toolkit/clientscan/msgshape.py --census --exe $EXE      # the recovery, self-checked
python toolkit/clientscan/msgshape.py 0x00E5 --exe $EXE
python toolkit/clientscan/msghandler.py 0x00E2 --exe $EXE --follow --depth 3 --annotate
python toolkit/clientscan/msghandler.py --callers 0x00822B80 --exe $EXE
python toolkit/authsrv/probes.py                               # every probe step encodes
```

Bulk extractions live in `vault/skillcast/` (gitignored, client-derived):
`message-shapes-38797.txt` (all 751 tables), `asserts-skill-modules-38797.txt`,
`assert-modules-38797.txt`, `generic-value-switch-38797.txt`.

## 13. A house rule this pass did not break, and one question for the owner

CLAUDE.md says *"Python 3, standard library only. No third-party dependencies
anywhere in `toolkit/`."* `msghandler.py` has imported capstone and pefile
since before this pass — there is no reasonable stdlib x86 disassembler, and
the rule and the file have simply coexisted.

This pass did not widen it. Both new modules — `asserts.py` and `msgshape.py` —
are stdlib only, and so is the test, which means every *claim* in this document
is checkable on a bare machine even though the exploration that produced them
used a disassembler. That was a deliberate choice and it cost something: the
initializer recovery in `msgshape.py` is a byte walk rather than a proper
disassembly, and it is honest about the two slots it cannot account for.

**The question for the owner is whether analysis tooling gets an explicit
carve-out in CLAUDE.md**, or whether `msghandler.py` should be treated as a
debt to pay down. It is flagged here rather than silently resolved either way.
Related: `studies/msgtable`'s initializer decoder was left in scratch and lost,
which is why this pass had to rebuild it. It is committed now, with a test that
reproduces that study's own oracle.
