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

## 4. The boundary — what this does NOT claim

**`ItemName.cpp` is the NAME AND TOOLTIP builder, not every consumer of a modifier.** Two
of the busiest identifiers in the wild — **633 (×570) and 617 (×420)** — dispatch to the
loop-continue label, i.e. this subsystem renders *nothing* for them, deliberately. They are
on real retail items and plainly mean something; what reads them is not this function.
Recorded as a fenced NOT FOUND rather than as a gap, and it is the obvious next thread.

So the honest form of the result: **the DISPLAY vocabulary is decoded** — which is exactly
what "Armor: 25" is made of — and whether a given modifier also drives combat arithmetic
elsewhere is a separate question this arc did not ask.

Two more limits worth stating. The `labels`/`templates` split the tool reports is **best
effort**: several handlers branch or loop before formatting, so a linear walk cannot always
pair a push with its call. The complete ordered `text_ids` list is what the content rows
carry and is what `--summary` counts on. And **34 of 157 identifiers extract no text id at
all** — inert here, by the same boundary as above.

## 5. What this unblocks

- **[studies/character](../character/FINDINGS.md)'s armour rating** — the value it wanted is
  identifier 572's argument, and 527's is the "+N vs. damage type" line.
- **[studies/combat](../combat/PLAN.md)'s weapon damage** — identifiers 584 (range, two
  operands) and 587 (type).
- **[studies/pvpui §34.6](../pvpui/FINDINGS.md)'s `attribute_bonus`** — that field is our own
  declaration of what our item does, deliberately *not* a reading of the modifier words,
  and it was labelled that way because this decode did not exist. It can now be derived
  instead of declared, which is a real follow-on rather than a cleanup: it needs whichever
  identifier carries an attribute bonus, and identifier 1's handler is the one that
  bound-checks its argument against `CHAR_ATTRIBS` (51).
- **Authoring items that read correctly** — a server can now compose a modifier word for a
  stat it wants rather than copying an opaque literal out of a capture.

`toolkit/clientscan/itemmods.py` (`--decode`, `--summary`, `--emit-content`,
`--all-builds`), `test_itemmods.py` (12 checks, floor 12), and
`vault/content/item_modifiers.toml` (157 rows, `client-table` provenance, ids not words).
