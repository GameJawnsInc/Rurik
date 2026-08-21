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
that negative comes with its own positive control. §4. **And the attribute BONUS
is §5** — identifiers **542** (Non-stacking) and **543** (Stacking), found not by
reading templates but by asking which handlers resolve an attribute NAME, which is
also a correction: the fourteen that do were counted as two from an assert list that
says in its own output that it is a floor.

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
| 584 | 2382 `Dmg`, 2441 `%str2% %str1%: %num1%-%num2%` | the damage RANGE — **`arg` is the max, `arg2` the min**, read off `Blunt Dmg: 3-5` on screen (§5.6) |
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

**AND THE MISSING QUANTIFIER, added 2026-08-20: there are SIXTEEN of them.** The two
forms above are the only ways x86 can isolate bits 29-20, so a scan for their bytes over
`.text` is not merely exhaustive-in-principle — it produces a *total*, and that total is
what an absence has to be read against. `--sites` prints it:

```
16 sites isolate a modifier identifier
   13  mask-in-place, then a compare against a literal
    2  shift-then-mask, compared to a REGISTER   (the by-argument accessors)
    1  shift-then-mask, indexed into the jump table   (the tooltip walker)
  158  further mask sites that are NOT modifier code
```

The identifiers named by a literal anywhere in the client are
`[1, 8, 542, 556, 572, 581, 584, 601, 603, 633, 647]`, and the census is **identical on
all three builds**. Two details keep it a census rather than a tidy number:

- **The 158 are counted, not filtered.** `0x3ff00000` is also a double's exponent mask
  and the float band matches it 158 times. Dropping them silently would report item code
  while claiming to report an instruction.
- **One mask can name two identifiers, and the first cut of this missed it.**
  `0x00848004` masks once and compares twice — 633, then identifier **1** eight bytes
  later as its fallback. Stopping at the first compare is the same defect as reading
  `asserts.py`'s module list as a census, from the other side.

`toolkit/clientscan/itemmods.py --readers` prints the whole map; `--reads 633` answers
for one, with the coverage statement attached. The parametric helpers are `ItCliApi.cpp`'s pair — one returns
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

**THE THREE ROUTES THAT ARE NOT IMMEDIATES ARE NOW CLOSED TOO** (2026-08-20). A census
of literal compares still leaves ways to reach an identifier without one, and each was
checked rather than waved at:

| route | result |
|---|---|
| the **by-argument accessors** | 12 direct call sites, asking for `{587, 590, 592, 598, 603, 606, 614, 630, 647, 648}`. Not 617. |
| **indirectly**, via a vtable or a stored pointer | neither accessor's VA occurs as a data word anywhere — 0 at every alignment, all five sections |
| a **second dispatch table** | the image holds exactly **one** identifier-indexed jump table; 617's slot in it is the shared loop tail |
| a mask that keeps **bit 19** | every 617 word in the wild has bit 19 set, so such a reader would compare `0x26980000`. That dword occurs nowhere in `.text`; neither does `0x26900000`. |

And the one place a parse could still hide — **item creation** — does not parse. Walking
outward from `0x0161`'s handler (`0x00846D70`, `ItCliApi.cpp`), **66 functions** are
reachable within three call levels and exactly one touches the modifier array:
`0x00848250`, which asserts the last word is the `0xC0000000` terminator, allocates
`(count+1)*4` bytes and **`memcpy`s the words in verbatim**. It reads one identifier out
of them — 647, gated on item type 43 — and interprets nothing else. **The array the
client stores is the array we sent.**

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
- **It is a property of the item's MODEL, exactly** — `arg2` is single-valued for
  **71 of 71 `model_id`s** over all 420 words. This line used to read "*nearly* a
  property of the skin — constant for 29 of 34" and that was the **file id**, which is a
  different field and is the CONTROL that fails: 5 of its 34 values carry more than one
  `arg2`. The control is what makes the model result readable at all, because any field
  with small enough groups looks deterministic. OBSERVED, `test_itemmods.py` §14.
- Near-misses, recorded so they are not re-run: 633's attribute requirement determines it
  for 13 of 14 values (attribute 25 splits into 143/144); item type, damage type and
  damage range each fail outright.

Labelled **UNVERIFIED**. The shape is recorded so the next reader starts from data
rather than from this paragraph.

**What follows from the model result, labelled.** That the number is redundant with
`model_id` — which the client already has — is **consistent** with nothing reading it.
That the redundancy is the *reason* is RECONSTRUCTION and this arc did not test it. The
reading it most resembles is a server-side classification of the skin that rides along
on the wire; naming it would need ArenaNet's server, a build we do not hold, or a
labelled campaign varying one skin at a time. All three are outside what a client read
can settle, which is why §7 lists this as answered-as-far-as-it-goes rather than open.

## 5. The attribute BONUS — and a correction to how §4 looked for it

**Written 2026-08-20, hours after §4, and it overturns one of §4's own
sentences.** §6 of this document said the attribute-bonus identifier was "still
unfound", on the strength of this reasoning: *exactly two handlers in the walker
treat their argument as an attribute index, identifiers 1 and 14, and neither is
a bonus.* The premise was wrong. It came from the two asserts that name
`attrib < CHAR_ATTRIBS`, and **`asserts.py` prints, in its own output, that its
module lists are a floor and not a census** — it is short by at least 370 sites
it can see but cannot read. Taking a floor for a total is what cost a day here.

### 5.1 The right question: who resolves an attribute NAME

`s_attrib` is 51 records of 20 bytes, and the client reads four of its fields
through four one-line accessors with an identical shape:

```
lea eax, [esi + esi*4]              ; index * 5
mov eax, [eax*4 + <base + k>]       ; * 4  -> stride 20, field k
pop esi ; pop ebp ; ret
```

Their four displacements are `base+0` (profession), `+8` (name string id),
`+12` (description) and `+16` (isPrimary), so **the lowest of the four IS the
table base** and the name accessor is `base+8` — locatable from the shape alone,
with no build-specific address anywhere. `itemmods.py --attributes` does it, and
finds the same fourteen identifiers on all three builds at three different table
addresses:

```
1, 14, 542, 543, 545, 569, 577, 578, 634, 640, 642, 643, 644, 650
```

**Fourteen, not two.** OBSERVED.

### 5.2 542 and 543 are the attribute bonus, and they differ by one word

The two handlers are byte-for-byte the same shape:

```
edi = word & 0xff                       ; arg2
ebx = (word >> 8) & 0x3ff               ; arg   -> THE ATTRIBUTE
name = TextApi(GetAttributeNameId(ebx))
if 1 <= edi <= 3:                       ; a four-entry table, 0xBCAAA8
    name = Format(2443 "%str2% %str1%", grade[edi], name)
...
push 2482 "Non-stacking"                ; 542
push 2481 "Stacking"                    ; 543
Format(dest, 2436 "%str1% +%num1%", string -> name, number -> edi)
```

> **`<Attribute> +N`, with `arg` the attribute and `arg2` the amount — and the
> same `arg2` indexes `{1: Minor, 2: Major, 3: Superior}`, so one number is both
> the bonus and the rune grade.** OBSERVED. 543 appends `Stacking`, 542 appends
> `Non-stacking`, and that is the only difference between them.

Two more in the family are bonuses of a different shape, and neither is what
§34.6 wants:

| id | line | attribute | amount |
|---|---|---|---|
| **577** | `<Attribute> +1` and `N% chance while using skills` (2497) | `arg` | the immediate **1**; `arg2` is the percentage |
| **644** | `+N` (Stacking) to the attribute named by a **companion 542 word**, or literally 56454 `Item's attribute` when there is none | scanned forward from the current word | `arg2` |

644 is worth its line for a second reason: it walks ahead looking for
`(word & 0x3ff00000) == 0x21E00000` — **identifier 542** — which is a third,
independent witness that 542 is the attribute-carrying bonus.

### 5.3 What ArenaNet actually sent us: 26 headpieces

The live corpus holds **26** attribute-bonus words, every one of them identical:

```
0x21F81401  ->  id 543, attribute 20, +1, stacking
```

Attribute 20 resolves through `s_attrib` to name id 2118, **`Swordsmanship`**.
Each of the 26 items carries it alongside `572` (armour rating **80**) and `527`
(`+20 vs. physical damage`), and all 26 share **one item type field, 16** — one
of six types that each appear exactly 77 times in the corpus, which is what a
set of armour slots looks like. A Warrior headpiece with `Swordsmanship +1`. A
bonus scattered across weapon types would have refuted the reading; it is not.

### 5.4 Composing one, and the three bits that make it not obvious

`itemmods.py --attr-bonus 20,1` builds the word, and the check with no free
parameter is that **it must equal the dword retail sent**:

```
identifier 543 << 20 | attribute 20 << 8 | amount 1   =  0x21F01401
what ArenaNet actually sends                          =  0x21F81401
```

The difference is **bit 19**. Bits 31, 30 and 19 are the three the walker never
reads as data — 31-30 only as the `== 3` skip — and across all **5,266** modifier
words in the corpus they are **constant per identifier: 35 identifiers, zero
exceptions**. So they are a fixed prefix of the encoding, not a payload, and a
composer has to carry them. For 543 the prefix is `bits 31-30 = 0, bit 19 = 1`,
measured on those 26 words.

`attribute_bonus_word()` composes the **stacking** form only, and refuses an
attribute `>= 51`. The non-stacking twin is deliberately not composable: **no
capture of ours has ever carried a 542**, so its three prefix bits are unmeasured
and inventing them is exactly the quiet guess this repo labels. NOT FOUND, and
bounded — it needs one capture of a rune.

### 5.5 What this does to pvpui §34.6

`content/items.toml`'s starter hammer declares `attribute_bonus = [[19, 1]]`,
with a comment saying it is **not** a decoding of the item's `modifiers` — and
it was right: its two words decode to `587` (damage type) and `584 arg 5 arg2 3`
(a damage range), and there is no bonus among them. Attribute 19 is name id 2116,
**`Hammer Mastery`**, so the word that would make that declaration real is

```
attribute_bonus_word(19, 1) = 0x21F81301
```

### 5.6 The run: ArenaNet's renderer drew our word

**Applied and run, 2026-08-20, loopback, build 38797.** The hammer's `modifiers`
became `[0x24B80000, 0xA4880503, 0x21F81301]` — one variable, nothing else touched
— and the predictions were written down first
(`vault/captures/harness/20260820T113942`, `…T114403`).

Hovering the equipped weapon:

```
Starter Hammer
Blunt Dmg: 3-5
Hammer Mastery +1 (Stacking)      <- rendered in the client's highlight colour
Two-handed
```

> **The client drew `Hammer Mastery +1 (Stacking)` from a dword this repo
> composed.** OBSERVED. Every field had to be right at once for that line to
> exist: identifier 543, `arg` = 19 the attribute, `arg2` = 1 the amount, and the
> **bit-19 prefix** — `0x21F01401`-style composition from the four fields alone
> would have produced a word for a different identifier. `(Stacking)` is string
> 2481, exactly what §5.2 read out of 543's handler and the one word that
> separates it from 542.

**Two more readings confirmed by accident, and neither was the point.** The same
tooltip renders the item's other two words:

- **`Blunt Dmg: 3-5`** from `584 arg 5 arg2 3` through template 2441
  `%str2% %str1%: %num1%-%num2%`. So **`arg` is the MAXIMUM and `arg2` the
  MINIMUM** of a damage range — §2's table said only "the damage RANGE" and could
  not say which way round. OBSERVED.
- **`Blunt`** from `587 arg 0`, so damage type 0 is Blunt.

**And the client does NOT double-apply it.** The attribute panel, same build, same
item:

```
20     [12] Strength
11  13 [ 9] Axe Mastery
 6   7 [ 7] Hammer Mastery        <- 7, in BLUE
 3   4 [ 3] Swordsmanship
 1   2 [ 1] Tactics
```

Base rank 6 (`content/world.toml`) plus the server's one bonus is **7**, not 8. Had
the client computed effective ranks from equipped gear it would have added the
modifier word on top of our `0x003A` column and shown 8. It shows 7, so
[studies/pvpui §34.6](../pvpui/FINDINGS.md)'s model holds: **the panel reads the
server's effective column and the tooltip reads the item's words, and they are two
independent paths.** This was worth a run precisely because it could have come out
the other way.

Two incidental confirmations in that same frame: the chevrons price off the BASE
(▼6 ▲7 at base 6, which are `s_attribPoints[6]` and `[7]`), and the header reads
**27 unused points** — 200 lifetime minus the 173 those five ranks cost under
`attribspend`'s cost model, to the point.

## 6. The rest of the boundary

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

## 7. What this unblocks

- **[studies/character](../character/FINDINGS.md)'s armour rating** — the value it wanted is
  identifier 572's argument, and 527's is the "+N vs. damage type" line.
- **[studies/combat](../combat/PLAN.md)'s weapon damage** — identifiers 584 (range, two
  operands) and 587 (type).
- **[studies/pvpui §34.6](../pvpui/FINDINGS.md)'s `attribute_bonus`** — that field is our own
  declaration of what our item does, deliberately *not* a reading of the modifier words,
  and it was labelled that way because this decode did not exist. It can now be derived
  instead of declared, and **§5 found the identifier: 543 (Stacking) and its
  non-stacking twin 542**, `<Attribute> +N` with `arg` the attribute and `arg2` the
  amount. This bullet has been wrong twice and both errors are left visible above it in
  the history: it first named identifier 1 as the bonus (1 is the *requirement*, string
  2473 `Requires %num1% %str1%`, §4.2), and then said the bonus was "still unfound" on
  the strength of a two-handler count taken from an assert list that prints its own
  incompleteness — the real count is fourteen (§5.1). The composed word for the starter
  hammer's declared `[[19, 1]]` is **`0x21F81301`** (`Hammer Mastery +1`), and §5.5 says
  why it is not applied here.
- **A requirement our server can enforce** — the client already does the comparison
  (§4.2), against the same `[charCtx + 0xAC]` attribute store `toolkit/authsrv`'s
  §34 spend path now writes. An item declared with a 633 word will grey out in the
  client's own UI at the ranks it should, with no server work at all.
- **Authoring items that read correctly** — a server can now compose a modifier word for a
  stat it wants rather than copying an opaque literal out of a capture.

- **Runes are one capture away** — 542 is the rune form and nothing in our corpus
  carries one, so its three prefix bits are unmeasured and it is not composable (§5.4).
  A single capture of a character wearing an attribute rune closes it.

`toolkit/clientscan/itemmods.py` (`--decode`, `--summary`, `--readers`, `--reads`,
`--sites`, `--attributes`, `--attr-bonus`, `--emit-content`, `--all-builds`),
`test_itemmods.py` (37 checks, floor 37), and `vault/content/item_modifiers.toml`
(157 rows, `client-table` provenance, ids not words).

**617 is answered as far as a client read can answer it** (§4.1, §4.3): sixteen sites in
the whole image can isolate an identifier, the same on three builds, and 617 is named by
none of them; the four non-immediate routes are closed; item creation `memcpy`s the array
without interpreting it. Its one positive property is that `arg2` is a per-`model_id`
constant, 71/71, with the file id as the control that fails. What is left is not a gap in
the search — it is that **ArenaNet's server is not readable from here.**
