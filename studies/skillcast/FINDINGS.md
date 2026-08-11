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

**§14 and §15 were added later the same day** and carry the same method into
the next two things R4b needs: effects and conditions (the client names five of
those six opcodes itself), and the agent-property vocabulary (there are two
dispatchers, not one, and their id spaces are disjoint).

**§16 answers the four items §15.4 left open** — and corrects §15.1 while doing
it. The two dispatchers run **seven** switches over the property id, not the
three that were modelled, so three of the four ids §15.1 called unhandled are
handled. Read §16.5 before trusting any "handled by neither" statement above.

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

**There are two agent-property dispatchers, not one, and their id spaces are
disjoint.** Opcodes 159/160 feed an int switch, 162/163 a float switch, and no
property id has a case body in both. A property sent on the wrong one of those
is silently ignored — no error, no log line. The id space runs 0..66, one wider
than OpenTyria's enum, and the client's own `AV_CHAR_STAT_ENERGY == 0` decodes
five pairs of properties at a stroke. (§15.)

**Each dispatcher runs several switches over the property id, and the client's
internal event vocabulary groups the cast family the same way GWCA's names
do.** Every property in the cast and effect families ends by queueing an
AgentView event with a numeric *kind*, and the three families come out as three
contiguous trios — attack `0x03/0x00/0x02`, attack skill `0x15/0x11/0x13`,
skill `0x19/0x16/0x17`, each in started/finished/stopped order. No
reconstruction has these numbers, so their agreement with GWCA's naming is a
second witness rather than an echo. (§16.3.)

**The six `EFFECT_*` opcodes are `BuffSourceAdd`, `BuffSourceRemove`,
`BuffTargetAdd` (twice), `BuffTargetExtendTimed` and `BuffTargetRemove`** — the
client's own log strings. Each agent keeps two buff lists, one for what it is
maintaining and one for what is on it, and a maintained enchantment is the same
`buffId` filed in both. Upkeep versus timed is a structural distinction
(`sourceAgent` versus a float `duration` plus a timestamp), not a type code,
which is a real argument against Headquarter's `effect_type` reading of the one
field the binary would not name. (§14.)

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
compiled every assertion from the same four operations:

```
push  <line>            6A ll                 or  68 ll ll ll ll
mov   edx, <file>       BA <va of "P:\Code\...">
mov   ecx, <expr>       B9 <va of "skill->skillId != 0">
call  <assert>          E8 <rel32>
```

**CORRECTED 2026-08-10, and the correction is this paragraph's own subject.**
The block above is one of *three* shapes, not the shape. The two movs also
occur in the opposite order (75 sites), and a site whose check has two branches
compiles to `push`/`mov ecx`/`jmp` into another site's shared `mov edx`/`call`
tail (63 sites) — where the fifteen-byte pattern above cannot reach it at all.
`asserts.py` now scans all three; `toolkit/clientscan/codescan.py`'s module
docstring carries the worked example.

MEASURED: **19,758 sites on build 38797, and every single one calls the same
routine at VA `0x00487BC0`.** That unanimity is the check — a fifteen-byte
pattern would otherwise be expected to collide with unrelated code, and
19758/19758 agreeing on one callee says the matches are real, *including* the
138 the single-shape scan could not see. `asserts.py` asserts it, so a build
that changes the idiom fails loudly instead of returning a thinner list that
still looks plausible.

The number this document carried until 2026-08-10 was **19,620** — the
edx-first shape alone, printed as the census with nothing marking it as a
floor. Every count in this study that came out of `--file` or `--grep` is
therefore a lower bound as written; re-run before quoting one. The three sites
whose expression pointer no fixed pattern can read are listed by
`asserts.py --unreadable` and are in none of the module lists.

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

The test finds the client itself and says which one it used — the pinned
snapshot if the vault has it, the live install otherwise, and it refuses to
continue if the file size does not match build 38797:

```bash
python toolkit/clientscan/test_skillcast.py
```

The tools take `--exe`, defaulting to `C:\gw\Gw.exe`. **Do not write
`vault/run/...` as a relative path** — a git worktree has no vault of its own
and the walk lands on nothing. Ask `vaultpath.py`:

```bash
EXE="$(python -c "import sys; sys.path.insert(0,'toolkit'); import vaultpath; print(vaultpath.vault_path('run','2026-07-29_221c13772c7a','Gw.exe'))")"
```

```bash
python toolkit/clientscan/asserts.py --exe "$EXE" --file ChCliSkill --unique
python toolkit/clientscan/asserts.py --exe "$EXE" --grep "SkillCopy|hotKeyState"
python toolkit/clientscan/asserts.py --exe "$EXE" --callers 0x00821CC0
python toolkit/clientscan/msgshape.py --census --exe "$EXE"     # the recovery, self-checked
python toolkit/clientscan/msgshape.py 0x00E5 --exe "$EXE"
python toolkit/clientscan/msghandler.py 0x00E2 --exe "$EXE" --follow --depth 3 --annotate
python toolkit/authsrv/probes.py                                # every probe step encodes
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

> **ANSWERED by the owner, 2026-08-06: it is a carve-out.** Read-only analysis
> tooling may use capstone and pefile; everything on the server path, and every
> tool whose byte patterns are fixed, stays standard library. Recorded in
> CLAUDE.md. `toolkit/clientscan/codescan.py` is the second module under it,
> promoted out of scratch after it found the writer of `agent+0xEC` that four
> earlier searches had reported absent (studies/enemy/PLAN.md §6q).
>
> The deciding argument was the one this section anticipated. Keeping the
> exploration in scratch meant the *tools* were lost while their conclusions
> survived, so each new question paid to rebuild them — and §6o's wrong finding
> was produced by exactly that rebuilt-from-memory tooling. The claims still
> want a stdlib checker where one is possible; what changed is that the
> instrument no longer gets thrown away.
Related: `studies/msgtable`'s initializer decoder was left in scratch and lost,
which is why this pass had to rebuild it. It is committed now, with a test that
reproduces that study's own oracle.

---

# 14. Effects, conditions and enchantments — added 2026-08-06

Same method, same session, the next thing R4b needs. `studies/skills` §2 has
this family as six defined opcodes that **no reference server ever sends**, with
type codes from a single uncited source and one **CONTESTED** field name. The
client names five of the six itself.

## 14.1 The client's own function names — SOURCED

Eight log format strings in `.rdata`, each xrefed to exactly one opcode's
handler chain:

```
0x00A955A0  BuffSourceAdd (agent %d, skill %d): BuffId exists on agent already
0x00A95608  BuffSourceRemove (agent %d, buffId %d): No BuffState exists for agent
0x00A95650  BuffSourceRemove (agent %d, buffId %d): BuffId is not on agent
0x00A95690  BuffTargetAdd (agent %d, skill %d, buffId %d): BuffId exists on agent already
0x00A956E0  BuffTargetExtendTimed (agent %d, buffId %d): No BuffState exists for agent
0x00A95730  BuffTargetExtendTimed (agent %d, buffId %d): BuffId not found for agent
0x00A95798  BuffTargetRemove (agent %d, buffId %d): No BuffState exists for agent
0x00A957E0  BuffTargetRemove (agent %d, buffId %d): BuffId is not on agent
```

| Opcode | ldufr's name | The client's own name | Handler chain |
|---|---|---|---|
| 63 `0x3F` | `EFFECT_UPKEEP_ADDED` | **`BuffSourceAdd`** | `0x0091D9A0` → `0x0080EEC0` → `0x0081CC30` |
| 64 `0x40` | `EFFECT_UPKEEP_REMOVED` | **`BuffSourceRemove`** | `0x0091D9D0` → `0x0080EEF0` → `0x0081CDA0` |
| 65 `0x41` | `EFFECT_UPKEEP_APPLIED` | **`BuffTargetAdd`** | `0x0091D9F0` → `0x0080EF10` → `0x0081CE70` |
| 66 `0x42` | `EFFECT_APPLIED` | **`BuffTargetAdd`**, timed variant | `0x0091DA20` → `0x0080EF40` → `0x0081CF20` |
| 67 `0x43` | `EFFECT_RENEWED` | **`BuffTargetExtendTimed`** | `0x0091DA50` → `0x0080EF70` → `0x0081CFD0` |
| 68 `0x44` | `EFFECT_REMOVED` | **`BuffTargetRemove`** | `0x0091DA80` → `0x0080EFA0` → `0x0081D0B0` |

All six live in `P:\Code\Gw\Char\Cli\ChCliBuff.cpp`, reached through a
sub-object at `charContext + 0x508` — a sibling of the skill context at `+0x6F0`
and the skillbar at `+0x700`.

**ldufr's names are structurally right and directionally wrong.** Its
`UPKEEP_ADDED` / `UPKEEP_APPLIED` pair is really `Source` / `Target`: the *same*
buff, filed under two different agents.

## 14.2 Two lists per agent, two record shapes — MEASURED

`0x0064AAE0` finds, and `0x0081C890` creates, a per-agent `BuffState`. Each one
holds **two independent sorted arrays**, both keyed by the dword at record
`+0x08`:

```c
struct BuffState {
    /* +0x00 */ uint32_t agent;
    /* +0x04 */ rtl::Array<SourceBuff> source;   // 16-byte records; opcodes 63/64
    /* +0x14 */ rtl::Array<TargetBuff> target;   // 24-byte records; 65/66/67/68
};

struct SourceBuff {          // 0x10 = 16 bytes.  What this agent is MAINTAINING.
    /* +0x00 */ uint32_t skill;
    /* +0x04 */ uint32_t <unnamed>;
    /* +0x08 */ uint32_t buffId;        // the sort key
    /* +0x0C */ uint32_t targetAgent;
};

struct TargetBuff {          // 0x18 = 24 bytes.  What is ON this agent.
    /* +0x00 */ uint32_t skill;         // GmEffect:882  targetBuff.skill
    /* +0x04 */ uint32_t <unnamed>;     // the CONTESTED field -- 14.4
    /* +0x08 */ uint32_t buffId;        // sort key; GmEffect:1252 m_sourceBuff.buffId
    /* +0x0C */ uint32_t sourceAgent;   // ChCliBuff:235; 0 for a timed buff
    /* +0x10 */ float    duration;      // 0.0f for an upkeep buff
    /* +0x14 */ uint32_t appliedAt;     // GetSkillTimer() at apply; 0 for upkeep
};
```

Strides MEASURED from the compiler's own index arithmetic: `shl edi, 4` at
`0x0081CD62` (16 bytes), and `lea eax,[reg+reg*2]` with `lea edx,[ecx+eax*8]` at
`0x0081CAED` and `0x0081C7F8` (3 × 8 = 24 bytes).

**CORROBORATED against GWCA, with a clarification.** GWCA's 16-byte
`GW::Buff { skill_id; h0004; buff_id; target_agent_id; }` is exactly
`SourceBuff` — the list of what *you* are maintaining, which is the one a
toolbox cares about. Its `h0004` is our unnamed `+0x04`. The 24-byte
`TargetBuff` — what is on an agent, with the duration and the timestamp — is
not in GWCA at all as far as this pass could see.

## 14.3 The six messages, field by field — SOURCED

Wire shapes from the recovered descriptors; field roles from the stores, and
from the log strings' own argument order.

```c
// 63 / 0x3F  BuffSourceAdd            20 wire bytes
{ agent_id targetAgent; agent_id casterAgent; u16 skill; u32 unnamed; u32 buffId; }
//   filed under casterAgent's SOURCE list; targetAgent goes to record +0x0C

// 64 / 0x40  BuffSourceRemove         10 wire bytes
{ agent_id casterAgent; u32 buffId; }

// 65 / 0x41  BuffTargetAdd            20 wire bytes
{ agent_id targetAgent; agent_id sourceAgent; u16 skill; u32 unnamed; u32 buffId; }
//   filed under targetAgent's TARGET list; duration = 0.0f, appliedAt = 0

// 66 / 0x42  BuffTargetAdd, timed     20 wire bytes
{ agent_id targetAgent; u16 skill; u32 unnamed; u32 buffId; float duration; }
//   sourceAgent = 0, appliedAt = GetSkillTimer()

// 67 / 0x43  BuffTargetExtendTimed    18 wire bytes
{ agent_id targetAgent; u32 unnamed; u32 buffId; float duration; }
//   asserts !buffTarget->sourceAgent, then rewrites duration and appliedAt

// 68 / 0x44  BuffTargetRemove         10 wire bytes
{ agent_id targetAgent; u32 buffId; }
```

Two things fall straight out, and neither was available before.

**The source/target split is the maintained-enchantment mechanism.** 63 and 65
carry *identical* wire fields. They differ only in which agent's list the record
lands in, and correspondingly which of the two agent ids ends up at record
`+0x0C`. A maintained enchantment needs both: 63 so the caster's upkeep row
shows a pip, 65 so the target's effect row shows an icon. One `buffId` ties them
together, and 64 and 68 remove them independently.

**Upkeep and timed are distinguished structurally, not by a type code.** An
upkeep buff has `sourceAgent != 0` and `duration == 0.0f`; a timed buff has
`sourceAgent == 0`, a float duration and a timestamp. `BuffTargetExtendTimed`
asserts `!buffTarget->sourceAgent` before touching the timer — you cannot extend
something that is being maintained. That assert is the client stating the
invariant in its own words.

**CORROBORATED — Headquarter, on the two field names it got right.**
`studies/skills` records its `EFFECT_APPLIED` as
`{agent_id, u16 skill_id, u32 effect_type, u32 effect_id, float duration}`. The
binary confirms the shape exactly; confirms field 5 is a float the client stores
as a duration (`fld` at `0x0091DA27`, against a descriptor that types it as a
plain u32); and confirms field 4 is an id, whose name in the client's own words
is `buffId`. Only `effect_type` is left standing on nothing.

**A practical warning, SOURCED, of the same class as the unlock-bitmap crash.**
`GmEffect:3030` asserts
`buffId < (CTL_EFFECT_UPKEEP_TERM - CTL_EFFECT_UPKEEP_FIRST)`, and
`GmEffect:3021` asserts
`skillId < (CTL_EFFECT_SKILL_TERM - CTL_EFFECT_SKILL_FIRST)`. Both index UI
frame-code ranges. A server that hands out large buff ids will assert in the
client the moment the effect UI touches one, so **buff ids are a small dense
space the server must allocate carefully**, not an arbitrary handle.

## 14.4 The one field the binary would not name — CONTESTED

Record `+0x04`, from field 4 of opcodes 63 and 65 and field 3 of opcode 66.
`studies/skills` has it as Headquarter's `effect_type` — codes 0 = condition or
shout, 8 = stance, 11 = maintained enchantment, 14 = enchantment or nature
ritual, single-source and uncited — against GWCA's `attribute_level`.

**Static analysis ran out here.** `ChCliBuff.cpp` stores the field and never
reads it; no assert in the image names it; and the UI event payloads carry the
record *pointer* rather than the field, so the consumer is several frames of UI
code away. **NOT FOUND**, searched three ways: the assert corpus, a string
sweep, and the `GmEffect` consumer chain from event `0x10000055`.

One new piece of evidence, and it cuts against `effect_type`: **the client
already distinguishes upkeep from timed structurally** — different opcodes,
different lists, `sourceAgent` versus `duration`. A type code whose values are
"stance / enchantment / maintained enchantment" would re-encode a distinction
the client has already made by other means. That is an argument, not a proof,
and it is exactly the shape of reasoning this repository distrusts — so it is
written down as an argument, and a probe settles it.

`buff_type_field` sends the same skill with field 3 = 0, then 14, then 12, and
watches whether the icon changes *kind* (effect_type) or only its numbers
(attribute_level). 12 is deliberately not one of Headquarter's four codes: if
the field is that enum, 12 should misbehave where 0 and 14 do not.

## 14.5 What this changes for R4b

- There is **no** condition, hex or enchantment message. Everything rides these
  six, and the `buffId` is the server's handle for one applied effect.
- A duration is a **float in seconds**, and the client stamps its own clock at
  apply time — the same architecture as the skill recharge. The server never
  sends "time remaining"; it sends 67 to change the duration.
- Removing an effect early is 68 with the `buffId`. There is no "expire"
  message: the client owns the countdown.
- A maintained enchantment costs **two** messages, and dropping it costs two
  more.
- Buff ids must be small and densely allocated, or the effect UI asserts.

Two more probes join the queue, after the six in §11:

| # | Probe | Question | Prediction |
|---|---|---|---|
| 7 | `buff_side` | Do 63 and 65 file one buff under two agents? | 65 alone gives one effect icon with no countdown; adding 63 with the same buffId gives a second, separate upkeep indicator; removing either leaves the other. |
| 8 | `buff_type_field` | Is field 3 `effect_type` or `attribute_level`? | If `effect_type`, 0 and 14 render as different *kinds* and an out-of-enum 12 misbehaves. If `attribute_level`, all three look identical and only the tooltip numbers move. |

---

# 15. The agent-property vocabulary — added 2026-08-06

`studies/skills` §2 calls the 66-entry agent-property enum "the one place in the
whole pass where three lineages agree across thirteen years" and says that if
Rurik ever builds a skill-effect oracle, this enum is its vocabulary. Both
halves of that need qualifying. The lineages agree on *some* of it and flatly
contradict each other on ids 8, 18, 23, 35, 49, 53, 58 and 59, and 14 of
OpenTyria's 66 entries are named only by their own number.

The client settles a surprising amount of it **structurally**, without needing
any name at all. `toolkit/clientscan/genericvalue.py` (new, stdlib only)
extracts the mapping and the test re-derives it.

## 15.1 There are two dispatchers, and they are disjoint — MEASURED

```
159 / 0x009F  AGENT_PROPERTY_UPDATE_INT           -.
160 / 0x00A0  AGENT_PROPERTY_UPDATE_INT_TARGET     '->  ChCliApi 0x008128F0
162 / 0x00A2  AGENT_PROPERTY_UPDATE_FLOAT         -.
163 / 0x00A3  AGENT_PROPERTY_UPDATE_FLOAT_TARGET   '->  ChCliApi 0x00813040
```

The non-target variants pass a target agent of 0 and are otherwise identical —
one dispatcher each for int and float, not one for all four. Each has its own
dense switch over the property id, and:

| | ids |
|---|---|
| the int switch has a case body for | **47** |
| the float switch has a case body for | **14** |
| an int-only pre-switch handles, and the main switch does not | **2** (10 and 64) |
| **neither** switch acts on | **4** — ids 5, 8, 40, 51 |
| both switches claim | **0. They are disjoint.** |

47 + 14 + 2 + 4 = 67, and the two handled sets do not overlap by a single id.
**A property id is an INT property or a FLOAT property, and sending one on the
wrong message type is silently ignored** — no error, no log line, no assert.
For a server that is a whole class of bug: health regen (44) sent as an int
does nothing at all and looks exactly like a wrong id.

This also dissolves what looked like a hole. Reading only the int switch, 20
ids appeared unhandled, including `SkillDamage`, `EnergyRegen`, `HealthRegen`,
`CastTimeModifier` and `Knockdown2` — the very things a combat system needs.
Fourteen of them are simply float properties.

**The id space is 0..66 — 67 values.** The int switch's own bound is
`cmp eax, 0x42`, and id 66 has a real case body at `0x00812EBD`.
**OpenTyria's enum stops at 65**, so it is one entry short, and nothing in
either lineage names 66. NOT FOUND.

## 15.2 What the groupings settle — SOURCED and MEASURED

**`AV_CHAR_STAT_ENERGY == 0`, and the 0/1 flag everywhere is energy/health.**
`AvChar.cpp:4320` asserts `stat == AV_CHAR_STAT_ENERGY`, guarded by
`if (stat != 0)` at `0x007F78DB` — so the constant is 0. That one name decodes
five pairs of properties at once, because each pair calls one helper with 0 or 1:

| pair | helper | 0 | 1 |
|---|---|---|---|
| 41 / 42 (int) | `0x007E0310` | energy | health |
| 33 / 34 (float) | `0x007E02C0` | energy modifier | health modifier |
| 43 / 44 (float) | `0x007E0360` | energy regen | health regen |
| 52 / 53 (float) | shared body | energy | health |
| 62 (float) | `0x007E03B0` | energy | — |

OpenTyria's `Energy`/`Health` (41/42) and `EnergyRegen`/`HealthRegen` (43/44)
are **CORROBORATED**. GWCA's `health` (34) and `energygain` (52) are
CORROBORATED and their unnamed twins are now named: 33 is 34's energy twin, and
53 is 52's health twin — which makes OpenTyria's `EnergyModifier3` for 53
**wrong**, since it is the health one.

**Property 10 names the skill responsible for the next damage number, and the
damage handler consumes and clears it.** Property 10 is handled only by the int
pre-switch, and all it does is `charContext + 0x640 = value` (`0x008129DA`).
Two float families then read that dword, pass it on, and **zero it**:

- 16, 17, 18 → one body with a 0 / 1 / 2 selector → `0x007DFB60`, clears +0x640
- 55, 56 → another body with a 0 / 1 selector → `0x007E0130`, clears +0x640

GWCA's comment on 10 — *"The skill responsible for the last damage packet
received"* — is **CORROBORATED exactly**, and the mechanism adds an ordering
constraint no source states: **send property 10 immediately before the damage
property, or the floating number is attributed to nothing.** It also says 18 is
a third member of the 16/17 damage family (GWCA names 16 `damage` and 17
`critical` and leaves 18 unnamed; OpenTyria has `DamageModifier1/2` and
`Value18`), and 56 is the second member of 55's.

**Properties 20 and 21 call the same function, and 21 passes the agent where 20
passes the target.** At `0x00812B6C` the arguments are `(agent, target, value)`;
at `0x00812B7E` they are `(agent, agent, value)`. That is precisely GWCA's
`effect_on_target` / `effect_on_agent` — *"e.g. casting a skill on someone"* vs
*"on myself/location"*. **GWCA is right in a way the binary can demonstrate.**
OpenTyria's `ApplyEffect1`/`ApplyEffect2` is not wrong, just uninformative.

**Properties 6 and 7 are one function with a 1 / 0 flag** — add and remove.
Both lineages agree (`ApplyAura`/`RemoveAura`, `add_effect`/`remove_effect`)
and the binary shows why they are a pair. CORROBORATED.

**Properties 23, 24, 25, 26 and 27 are not actions — they are sticky parameters
for the next animation.** Each is a bare store to five consecutive dwords in the
char context:

```
23 -> +0x550      26 -> +0x55C
24 -> +0x554      27 -> +0x560
25 -> +0x558
```

and property 22 (`ApplyAnimation`) *reads* +0x55C and +0x560, while property 28
(`ApplyAnimationLoop`) reads +0x550 and +0x554, ORs `0x10` into the first, and
then **clears all five**. GWCA's comment on 23 — *"When received before dance,
makes it fancy"* — describes exactly this mechanism, and the binary shows the
whole set works that way, not just 23. So the server must send 23-27 **before**
the 22 or 28 that consumes them, and they do not persist.

**Properties 35 and 63 invoke the same AgentView call.** 35 (int) loads a
compiled-in `0.4f` from `0x00948DAC` and calls `0x007E0490(agent, 0.4f)`; 63
(float) calls `0x007E0490(agent, wireFloat)`. So they are one effect with a
fixed and a variable duration. OpenTyria pairs them as `Knockdown1` /
`Knockdown2`; GWCA calls 35 `interrupted` and 63 `knocked_down`. **The pairing
is settled and the naming is not** — the binary proves they are the same
animation, and 0.4 s is short for a Guild Wars knockdown and about right for an
interrupt stagger. **CONTESTED**, with the relationship now fixed.

**Property 48 is the only skill-ish property that does not reach AgentView.**
It broadcasts UI message `0x10000025` with `{agent, value}` and stops. Every
other member of the cast family calls into `AvApi`. GWCA names it
`instant_skill_activated`; an instant skill is exactly the one with no cast
animation to play. Suggestive, not proof — INFERRED.

**Properties 14 and 15 assert `sourceAgent < 5`** (`ChCliApi:2112`, and again
at 2123). Five is the number of armour pieces, and `probes.py` already carries
the five Prophecies warrior slots. Corroborates OpenTyria's
`AddArmor`/`ArmorColor` weakly but usefully.

## 15.3 The cast family, in one place

Pulling §6 and this section together, the properties an execution engine needs:

| id | dispatcher | reaches | our reading |
|---|---|---|---|
| 4 | int + pre-switch | `AvApi 0x007DFA80` | attack started (3 args) |
| 50 | int + pre-switch | `AvApi 0x007E0100` | attack-skill started (3 args) |
| 60 | int + pre-switch | `AvApi 0x007E0200` → `AvChar` event kind 0x19 | **skill started — the cast animation** (3 args) |
| 1 | int | `AvApi 0x007DFA20` | melee attack finished (agent only) |
| 3 | int | `AvApi 0x007DFA60` | attack stopped (agent only) |
| 46 | int | `AvApi 0x007E00A0` | attack-skill finished (agent only) |
| 49 | int | `AvApi 0x007E00E0` | attack-skill stopped (agent only) |
| 58 | int | `AvApi 0x007E0190` | skill finished (agent only) |
| 59 | int | `AvApi 0x007E01B0` | skill stopped (agent only) |
| 48 | int | UI only | instant skill — no animation |
| 61 | float | `AvApi 0x007E01D0` | cast time modifier |
| 10 | int pre-switch only | `+0x640` | the skill the next damage belongs to |

**The started/finished/stopped shape is the strongest corroboration of GWCA in
this document.** Three properties take `(agent, target, value)` and are grouped
together by the pre-switch; six take only `(agent)` and split cleanly into a
"finished" trio and a "stopped" trio. GWCA's names fit that structure exactly.
OpenTyria's do not: it calls 58 `FightStance`, 49 `InterruptAttack`, 46
`MeleeSkillAttack2`, 3 `MeleeSkillAttack1` and 1 `Value1` — five names that
cannot all be right about six functions of identical shape.

**Do not import OpenTyria's agent-property enum** for anything in the cast
family, for the same reason `studies/skills` says not to import its attribute
enum. Use GWCA's names where it has them, this document's structure where it
does not, and `genericvalue.py` to check which dispatcher owns an id before
sending it.

## 15.4 What this leaves open

- **Ids 5, 8, 40 and 51 are acted on by neither dispatcher.** GWCA names 8
  `disabled` (aftercast, value 1/0) — if that is right, something other than
  `ChCliApi` must consume it, and we did not find what. NOT FOUND.
- **Id 66 has a case body and no name in any source.** NOT FOUND.
- **Id 64 stores an *agent id*, not a value**, at `charContext + 0x6A4`
  (`0x008129E2`, `mov [esi+0x6A4], edi`). A "last something agent" slot.
  NOT FOUND in both lineages.
- The AgentView event kinds each `AvApi` entry point queues would give a second,
  independent grouping. Only one was read this pass (kind `0x19` for property
  60, via `AvChar 0x007F76D0`).

No probe is listed for these: the honest next step is more static reading of
`AvApi.cpp`, not a client run, and §11's queue is already long enough to fill a
session.

**§16 is that reading.** All four are answered or bounded, and one of them
turned out to be answered because §15.1 was wrong.

---

# 16. §15.4's four open items — added 2026-08-06

Same session, same method, same pinned build. Two new stdlib tools:
`toolkit/clientscan/avevents.py` recovers the AgentView event kinds, and
`genericvalue.py` grew from three switches to seven. `test_skillcast.py` gained
a section 7 and 24 more pinned byte strings.

**The headline is a correction, and it is ours.** §15.1 reported ids 5, 8, 40
and 51 as acted on by neither dispatcher. **Three of those four were wrong.**
5 and 51 are handled by the float dispatcher; 8 is handled by the int one. Only
40 is untouched. §16.5 has the cause, which is the same cause as §10's.

## 16.1 The property dispatchers run SEVEN switches, not two — MEASURED

`genericvalue.py` modelled the two main switches and the int pre-switch. That is
three of seven. In dispatch order:

| # | switch | VA | ids | case bodies | shape |
|---|---|---|---|---|---|
| 1 | `int-store` | `0x00818170` | 32, 41, 42 | 3 | compare chain |
| 2 | `int-agentview` | `0x0081BC60` | 4, 8, 13, 50, 60 | 5 | jump table |
| 3 | `int-pre` | inline | 4, 10, 50, 60, 64 | 5 | jump table |
| 4 | `int-main` | inline | 0..66 | 47 | jump table |
| 5 | `float-store` | `0x00818210` | 16, 33, 34, 43, 44, 52, 55, 62 | 8 | jump table |
| 6 | `float-agentview` | `0x0081BD80` | 5, 51, 61 | 3 | compare chain |
| 7 | `float-main` | inline | 16..63 | 14 | jump table |

The cast trio 4 / 50 / 60 appears in three of the seven — `int-agentview`,
`int-pre` and `int-main` — which is a fourth independent grouping of exactly
those three ids, after §6's pre-switch bucket, §15.3's call shapes and §16.3's
event kinds.

Switches 2 and 6 run **only when the message's agent id resolves to an object
of type 1** — the dispatcher calls `0x005FC380(agent, &ptr, &type)` and takes
this branch on `type == 1`. So a property in this group does nothing for an
agent that is not resident and of that type, and nothing says so.

Two of the seven are compare chains, so there is no table to read as data. Their
ids are recorded in `genericvalue.py` as constants **and pinned to the exact
bytes that encode the comparisons** (`chain_ids()` raises rather than returning
a stale map), because a hardcoded answer that survives a build change is the
kind of check this repository refuses to ship.

**Both dispatchers gate the MAIN switch** behind
`test byte ptr [charContext + 0x53C], 2` (`0x008129B6` and `0x008130C2`). With
that bit set the main switch is skipped entirely and only the earlier switches
run. Nothing in the image read here says when it is set. NOT FOUND, and worth a
server's attention: it would look exactly like the client ignoring properties.

## 16.2 Who consumes 5, 8, 40 and 51 — answered for three of the four

### Property 8 — `int-agentview`, and GWCA is right

Case body `0x0081BCF0`, on the resolved agent object:

```
value != 0  ->  obj->flags64 |= 1;  call 0x0081BE90     ; 0x0081BCFB  or  eax,1
value == 0  ->  obj->flags64 &= ~1; call 0x0081C090     ; 0x0081BD11  and eax,-2
```

A one-bit flag at object `+0x64`, set by a non-zero value and cleared by zero,
with a different follow-up call each way. **GWCA's `disabled`, documented as
"(aftercast) value 1/0", is CORROBORATED** — the binary shows precisely a 1/0
flag. OpenTyria's `FreezePlayer` is not contradicted so much as unspecific.

### Properties 5 and 51 — `float-agentview`, and they are 61's siblings

The whole switch is three compares and one body (`0x0081BD80`):

```c
if (propId == 5 || propId == 51 || propId == 61)
    agentObject->f124 = wireFloat;         // 0x0081BD98  fstp [ecx+0x124]
```

**5, 51 and 61 write the same float field.** 61 is `CastTimeModifier` /
`casttime` in both lineages — the one member of the trio anybody named. So 5 and
51, which OpenTyria calls `Value5` and `Value51` and GWCA does not name at all,
are **two more channels onto the cast-time modifier**. INFERRED: three ids
feeding one field are most likely three sources of the same modifier (a skill, a
stance, an item, say) rather than three unrelated things that happen to collide.
That is an argument from structure, and it is the only thing on offer — no
assert and no log string mentions the field.

**And the field is reset by the cast-start properties.** MEASURED at
`0x0081BCE1`: properties 4, 50 and 60 end their `int-agentview` case with
`fldz; fstp [esi+0x124]`. So:

> **Send the cast-start property (4 / 50 / 60) first and the modifier
> (5 / 51 / 61) after.** A modifier sent first is zeroed by the cast that was
> supposed to use it.

That is the opposite ordering from property 10 before the damage property, and
from 23-27 before 22/28. Three sticky-parameter mechanisms in one dispatcher,
two of which want the parameter first and one of which wants it second. INFERRED
from the zeroing; `probes.py` has no probe for it and should get one.

### Property 40 — NOT FOUND, and now that means something

40 has no case body in any of the seven switches. §15.1 could not say that
cleanly because it believed every property was recorded somewhere on the way
past; §16.5 shows it is not. **Nothing in either dispatcher reads, stores or
forwards property 40.** It is a wire id the client accepts and discards.

## 16.3 The AgentView event kinds — the second grouping, and it holds

Every property in the cast and effect families ends the same way: the case body
calls an `AvApi.cpp` entry point, which resolves an AgentView character and
calls a method on it, which **allocates an event, writes a KIND to its first
dword and links it onto two lists**. Two allocators, disjoint kind spaces:

| allocator | payload from | kinds seen | what its neighbours' asserts call the records |
|---|---|---|---|
| `0x007F2E90` | `+0x30` | 22, sparse in `0x00..0x1B` | `action->queueLink` / `action->sequenceLink` (AvChar:1243, 1251) |
| `0x007F5340` | `+0x1C` | 20, **dense `0x00..0x13`** | `effect->effectLink` / `effect->queueLink` (AvChar:2433, 2438) |

The names `action` and `effect` are **INFERRED**, and the inference is this:
neither allocator contains an assert of its own; the asserts above are in the
immediately adjacent functions; **each of those assert pairs names exactly two
links, and each allocator links its fresh record onto exactly two intrusive
lists.** `AvChar:2646-2648` names three outright — `m_actionQueue`,
`m_actionSidelineQueue`, `m_triggerList`. Adjacency plus a matching structure,
not a quotation.

MEASURED, and this is the check that could have failed: **44 call sites across
both allocators, 43 of which resolve to a `push <kind>`.** The one that does not
(`0x007F7A1D`) has its push hoisted above a branch; `avevents.py` reports it
rather than guessing. No property resolves to two different kinds.

### The three families, and why this corroborates GWCA

```
                        started   finished  stopped
  attack          (action)  0x03     0x00      0x02      properties  4,  1,  3
  attack skill    (action)  0x15     0x11      0x13      properties 50, 46, 49
  skill           (action)  0x19     0x16      0x17      properties 60, 58, 59
```

Three families of three, each a tight contiguous block in a space the wire
protocol never mentions. §15.3 argued from the *call shapes* that GWCA's
started/finished/stopped naming fits and OpenTyria's `FightStance` /
`InterruptAttack` / `MeleeSkillAttack2` cannot. The kinds are an independent
second witness: the client's internal event vocabulary groups exactly the same
nine properties into exactly the same three trios. **CORROBORATED, from a
direction no catalogue can reach**, since no reconstruction has these numbers.

Two ids get named by their position:

- **47 is a member of the attack-skill family.** Action kind `0x12`, sitting
  between `attack_skill_finished` (`0x11`) and `attack_skill_stopped` (`0x13`).
  OpenTyria calls it `Value47`; GWCA does not name it. INFERRED.
- **61 (`casttime`) is a member of the skill family.** Action kind `0x18`, the
  one number between `skill_stopped` (`0x17`) and `skill_activated` (`0x19`).
  So the skill block is four contiguous kinds, not three, and the cast-time
  modifier is part of it — which fits 16.2's finding that 60 zeroes the field
  61 writes.

The full 39-property map is in `vault/skillcast/agentview-event-kinds-38797.txt`
and pinned in `test_skillcast.py`'s `EVENT_KINDS`.

**One limitation, stated because it changes an answer.** `avevents.py` follows
straight-line code and unconditional jumps, not the taken side of conditionals.
Property 22 (`ApplyAnimation`) is the case that matters: `0x00812B90` tries
`charContext + 0x55C`, `+0x560`, `+0x558` and finally `+0x550`/`+0x554` in that
order and calls a **different** AvApi entry for whichever is set first, so it can
queue action kind `0x07`, `0x08`, `0x06` or `0x05`. The tool reports `0x07`.
This also refines §15.2: property 22 consumes **four** of the five sticky
parameters in priority order, not two, and clears them all afterwards.

## 16.4 Property 66, and `charContext + 0x6A4` — bounded, not named

### Property 66 is a byte-wide display attribute, and 65's neighbour

`0x00812EBD` → `AvApi 0x007E0550` (`assert(agent)`, AvApi:1474) → two paths:

```c
av = ResolveAvChar(agent);
if (av) {                       // 0x007F7C40
    av->m108->byte7 = (uint8)value;      // 0x007F7C4C  mov [eax+7], dl
    av->byte113     = (uint8)value;      // 0x007F7C4F  mov [ecx+0x113], dl
} else {                        // 0x007F7C60
    globalTable[agent]->byte7 = (uint8)value;
}
```

MEASURED and useful even without a name:

- **The value is a single byte.** A server sending a large int loses everything
  above bit 7, silently.
- **It is remembered for agents that have no AgentView object yet** — the else
  branch writes the same byte into a global agent-indexed table
  (`0x007F58A0`). So it is an *appearance* attribute, applied whenever the agent
  becomes visible, not an event.
- **Property 65 is the same mechanism one field over**: `0x007F7BD0` writes byte
  **+5** of that record where 66 writes **+7**. OpenTyria names 65 `PvPTeam`.
- **65 is guarded and 66 is not.** 65 compares before writing and calls a
  refresh (`0x007F7BE1`: `cmp eax,ebx; je`); 66 writes unconditionally and calls
  nothing. INFERRED: 66 is read by whatever next rebuilds the character, rather
  than driving a redraw itself.

The **name** is still NOT FOUND. It is past the end of OpenTyria's enum, absent
from GWCA, and no assert or log string in the image mentions either offset. A
displacement search for `+0x113` finds the one write and no clean read.

### `charContext + 0x6A4` is read by exactly one accessor, for the character screen

Property 64's store at `0x008129E2` writes `edi`, and `edi` is the **agent id**
(the dispatcher's second argument), not the value — §15.4 had that right. The
consumer:

```
0x00816CF0   call 0x0047F660          ; the module
             mov  eax, [eax+0x2C]     ; -> charContext      <- same two steps
             mov  eax, [eax+0x6A4]    ;    as the store site
             ret
```

MEASURED: **two direct callers, `0x004D33DE` and `0x004D3407`,** both inside one
UI message handler whose asserts name
`P:\Code\Gw\Ui\Game\CharCreate\CharCreate.cpp` (CharCreate:865 `m_context`,
CharCreate:1159 `msg.summaryBytes <= NET_CHARACTER_SUMMARY_MAX`). That handler
is a 104-case switch over UI messages `0x10000030..0x10000097`, and decoding its
index table shows exactly **two** cases reach the accessor:

| UI message | what the case does |
|---|---|
| `0x10000030` | `if (payload[0] == charContext->x6A4) handler_0x004A0B10(payload[1])` |
| `0x1000004E` | `if (payload[0] == charContext->x6A4) handler_0x004DAE70(payload[1])` |

So the slot is an **agent-id filter**: the character screen ignores both UI
messages unless they concern the agent whose id property 64 last stored.
INFERRED, and it is the most that can be claimed: it says what the field is
*for* on one screen, not what the property means in general. Both lineages have
64 as `Value64` / unnamed and this does not name it either. The two clear sites
(`0x008239E2`, `0x00824D3A`) zero `+0x6A4` alongside `+0x640` in the same block
of per-context scratch, which at least bounds its lifetime to one context.

## 16.5 Refuted this pass, including ours again

**1. "Every property is stored into a 52-byte per-agent record before the
switch, at `0x00818170`" — REFUTED, and it was §6's.** That sentence was the
reason §6 could say the twenty apparently-unhandled ids were "not necessarily
unhandled". `0x00818170` is not a universal store. It is a three-way compare
chain — and **`studies/agentprops/FINDINGS.md` §2 already said so**, under the
heading *"The int path handles only three properties — SOURCED"*, before §6 was
written. §6 then published the opposite, in a different study, about the same
address, and nothing caught it: the tests are per-study, and this pass
re-derived the answer from scratch rather than finding it two directories away.
**The correction is agentprops'; all §16 added was noticing.** That is the more
useful half of this entry — a claim can be refuted by a sibling study and stay
in print indefinitely, because nothing here cross-checks one study against
another. `agentprops` §3b has the same problem in the other direction: it counts
"all four dispatch tables" and there are seven.

```
0x00818182   sub edx, 0x20 ; je <32>      sub edx, 9 ; je <41>
             sub edx, 1    ; je <42>      -> 0x00818203: pop/pop/pop/ret 8
```

MEASURED at `0x00818207`: the default **returns having stored nothing**. Its
float twin `0x00818210` is a real jump table but covers only 8 ids. So a
property id that no switch names is genuinely discarded, and the stronger,
correct statement is the one §16.2 can now make about property 40.

The record array is real — `0x34` bytes per entry at `charContext + 0x7C`,
indexed by **agent id**, grown to `agent+1` on every property message and
bounds-checked against `Array.h:587 index < m_count`. It is only the *writing*
of every property into it that was invented.

**2. "5, 8, 40 and 51 are acted on by neither dispatcher" — REFUTED, §15.1's.**
Three of the four are handled. The cause is the one §10 already named in a
different costume: a **partial model of the client produces answers that are
self-consistent and carry no signal that they are wrong.** §10's version was
reading `cmds[]` without the initializer recovery; this one was reading three
switches out of seven. Both times the output looked complete. `genericvalue.py`
now enumerates all seven and `handled_by_nothing()` is the answer to ask for.

**3. "Property 22 reads +0x55C and +0x560" — incomplete, §15.2's.** It reads
four sticky parameters in priority order and picks a different AgentView action
kind for each. Not wrong, just half of it.

**4. "`AvApi.cpp` line ~1318 is property 60's entry point" — off by one
function, §6's.** `0x007E0200` has no assert; AvApi:1318 belongs to
`0x007E0230`, the next function along. The entry points do carry their own line
numbers where they assert `agent`, and those are usable: AvApi:1256 =
`0x007E0130`, 1347 = `0x007E02C0`, 1363 = `0x007E0310`, 1453 = `0x007E04C0`,
1474 = `0x007E0550`.

## 16.6 What §16 changes for a server

- **Check the dispatcher before sending.** `genericvalue.py --id N` now reports
  every switch that acts on an id, not just the main one. Property 40 is the
  only id in 0..66 that does nothing at all.
- **Order matters, in two directions.** Property 10 goes *before* the damage
  property; 23-27 go *before* 22/28; but 5/51/61 must go *after* 4/50/60,
  because the cast-start zeroes the modifier field.
- **Properties 8, 5 and 51 need the agent to be resident and of type 1**, or
  their switches never run.
- **Property 66's value is a byte.** So, on the evidence, is 65's.
- **If properties stop working entirely, suspect `charContext + 0x53C` bit 1**
  rather than the ids.
- The event kinds are the vocabulary to use when talking to ourselves about what
  the client will *do*, since they are the client's own grouping and the wire
  ids are three catalogues' guesses.

## 16.7 Reproducing §16

```bash
python toolkit/clientscan/genericvalue.py --exe "$EXE"
python toolkit/clientscan/genericvalue.py --exe "$EXE" --id 8
python toolkit/clientscan/avevents.py --exe "$EXE"
python toolkit/clientscan/avevents.py --exe "$EXE" --census
python toolkit/clientscan/avevents.py --exe "$EXE" --id 60
python toolkit/clientscan/msghandler.py 0x009F --exe "$EXE" --follow --annotate
python toolkit/clientscan/test_skillcast.py
```

New in `vault/skillcast/` (gitignored): `agentview-event-kinds-38797.txt`.

## 16.8 What §16 leaves open

- **The name of property 66**, and of 40, 47, 5 and 51. Structure placed all of
  them; nothing named them. A probe could: 66 is a byte-wide appearance
  attribute beside `PvPTeam`, so sending 0..255 and watching the character is a
  cheap experiment with a visible answer.
- **When `charContext + 0x53C` bit 1 is set.** NOT FOUND.
- **What reads `AvChar + 0x113`.** The write is the only reference a
  displacement search finds.
- **The remaining 22 action and 20 effect event kinds.** Only the 39 reachable
  from an agent property were followed; the rest are queued by code that has
  nothing to do with the property channel, and reading them would name the
  AgentView vocabulary properly.
**Two probes this pass earned**, committed and executable in
`toolkit/authsrv/probes.py` with their predictions written before the
experiment, after §11's six and §14.5's two. Both are UNRUN.

| # | Probe | Question | Prediction |
|---|---|---|---|
| 9 | `cast_modifier_order` | Must the cast-time modifier arrive *after* the cast-start property? | 61-then-60 casts at the **same** speed as a bare 60, because 60 zeroes the modifier field first. 60-then-61 casts visibly differently. If the two are indistinguishable this probe cannot say whether the ordering does not matter or `+0x124` is not the modifier, and it says so. |
| 10 | `prop66_sweep` | What is property 66? | Uncertain by construction. Something visible changes for at least one byte value, because the byte is stored per agent even for agents with no AgentView object yet. If nothing changes at any value, 66 needs a rebuild the probe cannot trigger. |

Two things about their design are worth reading before running either, because
both come out of §16 rather than out of guesswork:

- **`cast_modifier_order` sends property 61 on `0x00A2`, the float channel.** On
  `0x009F` it would be discarded in silence (§15.1) and the run would look like
  a clean negative. It also depends on `cast_anim`: its step 2 is a bare
  property 60, and if that does not visibly cast, nothing after it can be read.
- **`prop66_sweep` toggles property 65 after every value of 66.** 66's setter
  calls no refresh and 65's does, so the toggle is there to force the redraw
  that would make a latent byte visible. Step 1 is a bare 65 toggle, so whatever
  that does by itself can be discounted from everything after it.
