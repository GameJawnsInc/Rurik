# Item modifiers — the format, decoded

**Arc opened and closed 2026-08-20.** Read-only client analysis (builds 38519, 38797,
38833), the vault's whole live capture corpus, and two renderings this repo had already
watched on a caged client. No client was launched for this and nothing was patched.
Labels are the repo vocabulary from
[studies/character/FINDINGS.md](../character/FINDINGS.md).

---

## 0. The result in one paragraph

Every item on the wire carries a list of 32-bit **modifier words** — `0x0161
CREATE_NAMED_ITEM`'s trailing array, and `content/items.toml` has held literal ones since
the character arc. An item's armour rating, its damage range, its energy bonus and every
"+15% while…" line live in them, and **nobody in this repo had decoded a single one**;
`studies/character/FINDINGS.md` calls it *"the largest hole"* in three separate places, and
[studies/combat](../combat/PLAN.md), [studies/enemy](../enemy/PLAN.md) and
[studies/isle](../isle/PLAN.md) each record the same wall. It is now open. The layout is
**`{identifier: bits 29-20, arg: bits 17-8, arg2: bits 7-0}`** with two skip predicates,
read out of the client's own parser; the identifier space is **157 slots over two jump
tables**, and each one's meaning is recoverable because every handler formats its tooltip
line through TextApi with a **string id** this tool extracts. `toolkit/clientscan/itemmods.py`
does the whole thing structurally, and `test_itemmods.py` checks it against **5,266 real
modifier words** ArenaNet sent us.

**Reopened and closed again the same day, one section down.** Twenty-one of the 157
identifiers render nothing in the tooltip, and the two busiest of those in the wild are
**633** and **617**. 633 turned out to be the item's **attribute requirement**, read by
`ItCliApi.cpp` and compared against the character attribute container the pvpui arc
already owns; 617 is read by **nothing in the client**, on any of the three builds, and
that negative comes with its own positive control. §4.

---

## 1. The format, from the parser rather than from a guess

`ItemName.cpp` is the decoder — its asserts name it (`m_attribRestrict < CHAR_ATTRIBS`,
`attrib < CHAR_ATTRIBS`, and `ItemName:1529 No valid case for switch variable 'eval'`, which
is the giveaway that a switch over modifier kinds exists at all). The walker steps a dword
array and does exactly this to each word:

```
mov  ebx, [edx]                  ; the modifier word
shr  ecx, 0x1e / cmp ecx, 3      ; bits 31..30 == 3   -> skip this word
test ebx, 0x40000                ; bit 18 set         -> skip this word
shr  eax, 0x14 / and eax, 0x3ff  ; bits 29..20 = IDENTIFIER (10 bits)
cmp  eax, 0x201 / ja / je        ; >513 generic table, ==513 special
dec  eax / cmp eax, 0x13 / ja    ; 1..20 -> the special table
jmp  [eax*4 + <table1>]
...
sub  eax, 0x202 / cmp eax, 0x88  ; 514..650 -> the generic table
jmp  [eax*4 + <table2>]
```

and the handlers read their operands back out of the same word:

```
shr ebx, 8 / and ebx, 0x3ff      ; bits 17..8 = ARGUMENT (10 bits)
movzx eax, byte ptr [edx]        ; bits  7..0 = a second value
```

> **`{identifier, arg, arg2}` — 10 bits, 10 bits, 8 bits — with bits 31-30 == 3 and bit 18
> each meaning "step over this word".** OBSERVED.

**The dispatch is 157 slots and 133 distinct bodies**: 20 special (ids 1..20), one at 513,
and 137 generic (514..650). Slots deliberately share handlers, which is itself a check — a
1:1 map would have meant the table read was off by a stride.

## 2. What an identifier MEANS, in ArenaNet's own words

Every handler renders through TextApi, and the id it passes is the template. So the
vocabulary is recoverable without guessing at any of it:

| identifier | strings it formats through | renders |
|---|---|---|
| 572 | 2372 `Armor`, 2438 `%str1%: %num1%` | **Armor: 25** |
| 527 | 2372 `Armor`, 2436 `%str1% +%num1%`, 2476 `vs. %str1% damage` | **Armor +20 (vs. physical damage)** |
| 580 | 2464 `Holds %num1% items` | **Holds 20 items** |
| 584 | 2382 `Dmg`, 2441 `%str2% %str1%: %num1%-%num2%` | the damage RANGE |
| 587 | 2380 `Damage`, 2443 `%str2% %str1%` | the damage TYPE line |
| 570 | 2376 `Chance`, 2392 `skill recharge`, 2432 `Halves %str1% of spells` | **Halves skill recharge of spells** |
| 556 / 558 | 2071 `Energy` / 2072 `Energy recovery` | the energy lines |

Those are Guild Wars item stats, in the game's own phrasing. The ids are what the tool
emits and what the content rows carry; the English resolves at run time from the owner's
archive, which is the `mapbuild.py` pattern and the reason a handful of resolutions can be
quoted here as evidence without any of it being a bulk dump.

## 3. Two witnesses, and the one that could have refuted the layout

**Witness 1 — things this repo has already SEEN.** [studies/newopcodes](../newopcodes/FINDINGS.md)
recorded a caged merchant panel drawing `Armor: 25` and `Armor +20 (vs. physical damage)`
from our own content rows, before anyone knew what the words meant. Decode those same
words now and the argument field is **25** and **20**. The Backpack's `0x24481400` decodes
to argument **20**, and the Backpack holds twenty items.

**Witness 2 — every modifier ArenaNet ever sent us, and this is the refutable one.** The
live corpus holds **1,781 `0x0161` item declarations carrying 5,266 modifier words**. Run
every one through the extraction:

```
5,266 / 5,266 identifiers are ones the client actually dispatches   (100.0%)
35 distinct identifiers over 5,266 words
0 that miss both jump tables
```

A wrong shift or mask spreads identifiers across a 10-bit space and most of them land in
neither table. This is a check the artifact could have failed at any of 5,266 opportunities
and did not, and 35 distinct values out of 1,024 possible is the shape of a real enum
rather than of noise.

**Out of sample:** the locator finds its anchor and both tables on **all three builds**
(38519, 38797, 38833) at three different addresses, reporting 157 slots and 133 handlers
each time. It is located by the parser's own instruction bytes, never by a build-specific
address.

## 4. Who reads a modifier that the tooltip renders nothing for

**Written 2026-08-20, and it replaces this section's own fenced NOT FOUND.** The
first version of §4 recorded that identifiers **633 (×570)** and **617 (×420)** — two
of the three busiest in the wild — dispatch to the walker's loop-continue label, said
"what reads them is not this function", and called it the obvious next thread. It was.
The thread is pulled here, and the two came apart in opposite directions.

**First, what the loop tail actually means.** It is not "this identifier is
meaningless". `ItemName.cpp` is the *name and tooltip* builder, and its dispatch table
sends **21 of its 157 slots** to the loop tail:

```
2, 576, 586, 588, 590, 591, 592, 597, 598, 599, 604,
605, 612, 614, 616, 617, 618, 630, 633, 647, 648
```

**Eight of those twenty-one have a reader somewhere else** — 590, 592, 598, 614, 630,
633, 647 and 648. So the tail reads "this modifier is **data for another subsystem**,
not a line of tooltip text". OBSERVED, and identical on all three builds (38519,
38797, 38833) at three different addresses.

### 4.1 The census: exactly two ways the image can name an identifier

Both are found by their own instruction bytes over the whole of `.text`, so neither can
desync, and both are exhaustive rather than sampled:

| form | shape | who uses it |
|---|---|---|
| **literal** | `and r32,0x3ff00000` then `cmp r32,<id << 20>` | a reader that knows which one it wants |
| **parametric** | `shr eax,0x14 ; and eax,0x3ff ; cmp eax,edx` inside a helper that walks `[this+0x10]` to a `0xC0000000` terminator | the identifier arrives at the **call site** as a pushed immediate |

`toolkit/clientscan/itemmods.py --readers` prints the whole map; `--reads 633` answers
for one. The parametric helpers are `ItCliApi.cpp`'s pair — one returns
`(word>>8)&0x3ff`, the other `word & 0x3ffff` — and their eleven call sites ask for

```
587, 590, 592, 598, 603, 606, 614, 630, 647, 647, 648
```

**seven of which are identifiers `ItemName` renders nothing for.** That is the claim
above, in the client's own call sites rather than in an argument.

> **The `0xC0000000` terminator is a second witness for the bit layout.** ItemName's
> walker skips a word whose bits 31-30 are `3`; these accessors stop on a word that is
> exactly `0xC0000000`. Two subsystems, one sentinel, and neither was used to derive
> the other. OBSERVED.

### 4.2 633 is the item's ATTRIBUTE REQUIREMENT, and the whole chain is named

`0x00847FD0`, in **`ItCliApi.cpp`** (`ItCliApi:65 baseItem` sits sixty bytes away):

```
  *out_attribute = 0x33                 ; 51 = CHAR_ATTRIBS -- "no requirement"
  *out_rank      = 0
  for each modifier word:
      if (word & 0x3ff00000) == 0x27900000:      ; identifier 633 -- WINS
          *out_attribute = (word >> 8) & 0x3ff
          *out_rank      =  word       & 0xff
          return TRUE
      if (word & 0x3ff00000) == 0x00100000:      ; identifier 1 -- last one wins
          *out_attribute = (word >> 8) & 0x3ff
          *out_rank      =  word       & 0xff
  return FALSE
```

The default is **51**, which is the exact bound `ItemName`'s own asserts name
(`ItemName:1202 attrib < CHAR_ATTRIBS`) and the exact row count of `s_attrib`.
Identifier 1 is the same payload by another name, and 633 overrides it.

**And identifier 1 is the one that still draws a tooltip line, which settles the
naming in ArenaNet's own words.** Its handler is the one `ItemName:1202` sits inside,
and the template it formats is string **2473 — `Requires %num1% %str1%`**. That is the
sentence, and 633 carries the two values it needs.

Its caller at `0x0057A8C0`, in **`PvpItemListEntry.cpp`**, finishes the sentence:

```
  GetProperty(frame, 0x0a, &agent)
  GetProperty(frame, 0x56, &item)
  if (ReadAttributeRequirement(item, &attribute, &rank))
      usable = ChCliApi_GetAttribute(agent, attribute)->rank >= rank
```

and `ChCliApi_GetAttribute` is `0x0080D910`, which opens with
**`ChCliApi:4097 attrib < CHAR_ATTRIBS`** and then reads
`[[GetLocalPlayerContext() + 0x2C] + 0xAC]` — **the same character attribute container
the pvpui arc spends §31–§34 on**, and the one our own server now writes. The client
takes the item's required rank, looks up the player's rank in that attribute, and
compares. That is an attribute requirement, end to end, in ArenaNet's own module names.

`ItemName.cpp` reads 633 too, at `0x00923890` — **outside** the switch, in the routine
at `0x009236B0` that assembles the description object, storing rank and attribute into
`[obj]` and `[obj+4]`. Which is why the slot in the dispatch table is inert: the
requirement is not one of the "+N" lines, it is its own line, built elsewhere.

**Three checks the corpus could have failed, and 570 chances to do it** (§7 of
`test_itemmods.py`):

| check | result | why it is not free |
|---|---|---|
| every 633 argument is `< 51` | **570/570**, observed range 1..34 | 51 is `CHAR_ATTRIBS`, from `attribtable.py`'s separate extraction |
| every 633 second value is a reachable rank `1..12` | **570/570**, observed range 1..12 | 12 is the last costed entry of `s_attribPoints`, from `attribpoints.py`'s separate extraction — `[1,2,3,4,5,6,7,9,11,13,16,20,-1]` |
| the attribute is a property of the **skin**, the rank of the **roll** | **63 item model ids, 0 carry two attributes; 38 carry several ranks** | a coincidence has no reason to split that way |

Resolved through `s_attrib`, the requirements land where they should: model 9528 always
attribute 21 at ranks 4–10, model 14403 always attribute 20 at ranks 6–11 — Warrior
weapon attributes on Warrior weapons, Ranger on Ranger, Ritualist on Ritualist, and the
only primaries ever required are two Warrior rows.

### 4.3 617 is read by NOTHING, and that is the finding

Same scan, opposite answer. Across **all three builds**: no literal compare in `.text`
in either encoding, no accessor call site that asks for it, no whole-word compare, and
no identifier table in `.rdata` that contains it (the three `.rdata` hits for the
integer 617 are neighbours of 615/616/618 in unrelated ascending id runs). 420 items in
the live corpus carry it and nothing in the client consults it.

**The positive control is what makes that worth anything**, and it is wired into the
same test rather than asserted here: the identical scan reports **two** readers for 633
and finds eight more identifiers at the accessors. A search that cannot be shown to find
anything cannot report an absence — the lesson `studies/enemy` §6o paid for.

**Bounded, not universal.** `--readers` prints its own limits and they are the real
scope of this negative: an identifier reached through a register or a table rather than
an immediate; a `cmp` scheduled more than 16 bytes after its mask; an accessor whose
body differs from the two patterns above; and **anything the server does with the same
word**, which is invisible from here and is the likeliest home for it.

What 617 *looks* like, measured and deliberately **not named** — there is no client code
to read it out of, so anything beyond the shape would be invention:

- **arg is 0 on 420 of 420.** Only the 8-bit field carries anything.
- **arg2 ∈ {0, 1, 2, 3, 4, 5, 6, 143, 144}**, and 143/144 occur only on items whose
  type field is 5, which also carry a Ranger requirement.
- It sits at index 1–3 of the modifier list, never 0 (633 takes 0 or 1).
- It is *nearly* a property of the skin — constant for 29 of 34 item model ids — and it
  correlates with identifier 587 (the damage-type line) without being a function of it.

Labelled **UNVERIFIED**. The shape is recorded so the next reader starts from data
rather than from this paragraph.

## 5. The rest of the boundary

Two limits from the original decode still stand. The `labels`/`templates` split the tool
reports is **best effort**: several handlers branch or loop before formatting, so a
linear walk cannot always pair a push with its call. The complete ordered `text_ids` list
is what the content rows carry and what `--summary` counts on. And **34 of 157
identifiers extract no text id at all** — of which 21 are now explained (the loop tail),
and eight of those turned out to have readers elsewhere.

One defect worth recording, because it is the same shape as every silent-zero bug in
this repo. The first version of the loop-tail detector called a handler a tail if it
branched back to the loop head, and reported **22** inert identifiers. The extra one was
526, which pushes string 2387, calls TextApi, and then **falls through** into the tail.
It would have been published as "the client renders nothing for 526" while the client
plainly does. The fix is in `loop_tail()`: a body that calls or pushes an immediate on
the way is a renderer, not the loop. `test_itemmods.py` §6 pins the count at 21.

## 6. What this unblocks

- **[studies/character](../character/FINDINGS.md)'s armour rating** — the value it wanted is
  identifier 572's argument, and 527's is the "+N vs. damage type" line.
- **[studies/combat](../combat/PLAN.md)'s weapon damage** — identifiers 584 (range, two
  operands) and 587 (type).
- **[studies/pvpui §34.6](../pvpui/FINDINGS.md)'s `attribute_bonus`** — that field is our own
  declaration of what our item does, deliberately *not* a reading of the modifier words,
  and it was labelled that way because this decode did not exist. It can now be derived
  instead of declared — **but not from the identifier this list first pointed at, and
  that is a correction rather than a refinement.** This bullet used to say the bonus was
  "whichever identifier carries an attribute bonus, and identifier 1's handler is the one
  that bound-checks its argument against `CHAR_ATTRIBS`". Identifier 1 does bound-check
  against `CHAR_ATTRIBS`, and it is the **requirement**, not a bonus: its template is
  string 2473, `Requires %num1% %str1%` (§4.2). Exactly two handlers in the walker treat
  their argument as an attribute index — identifier 1 and identifier **14**, whose
  templates are 2483 `while %str1% is below %num1%` and 27726 `while you control %num1%
  or more minions`, i.e. a conditional, not a bonus either. **So the attribute-bonus
  identifier is still unfound**, and the honest state of §34.6's field is unchanged.
- **A requirement our server can enforce** — the client already does the comparison
  (§4.2), against the same `[charCtx + 0xAC]` attribute store `toolkit/authsrv`'s
  §34 spend path now writes. An item declared with a 633 word will grey out in the
  client's own UI at the ranks it should, with no server work at all.
- **Authoring items that read correctly** — a server can now compose a modifier word for a
  stat it wants rather than copying an opaque literal out of a capture.

`toolkit/clientscan/itemmods.py` (`--decode`, `--summary`, `--readers`, `--reads`,
`--emit-content`, `--all-builds`), `test_itemmods.py` (19 checks, floor 19), and
`vault/content/item_modifiers.toml` (157 rows, `client-table` provenance, ids not words).
