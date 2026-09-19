# The skill-template codec: the format, and why the client blanks a code

**Opened and closed 2026-09-19.** Labels per
[studies/character/FINDINGS.md](../character/FINDINGS.md): OBSERVED, UPSTREAM,
RECONSTRUCTION, CORROBORATED, CONTESTED, UNVERIFIED, NOT FOUND. Everything below is
read off the pinned pristine build **38797**
(`vault/client/2026-07-29_221c13772c7a/Gw.exe`) unless a line says otherwise.

**Identifiers.** `TEMPLATES-F<n>` = a finding. `TEMPLATES-Q<n>` = an open question.
Convention: [studies/idents/CONVENTION.md](../idents/CONVENTION.md).

## 0. Why this arc exists

Two things converged.

**One, a standing NOT FOUND of our own.** [studies/profession/MODDABLE.md](../profession/MODDABLE.md)
§9 has carried *"Does the skill-template codec's profession field have its own width?
**NOT FOUND — never asked, and it is a serialisation ceiling that leaves the
machine**"*, with "read the template encoder reached from `0x0058A790`" as the thing
that would answer it. A custom profession that cannot be written into a build code
cannot be pasted to another player, so the answer caps
[MODDABLE](../profession/MODDABLE.md)'s whole route independently of everything in its §1.

**Two, a public claim with a screenshot.** A forum post argued that the "Load from
Skills Template" window's behaviour has nothing to do with unlock status, and made five
specific assertions about when it shows a bar and when it shows nothing. The post came
with two client-produced template codes and their windows. Five falsifiable claims plus
two strings the client itself emitted is a better experiment than anything we would have
designed, so this arc scores them.

**The answer to MODDABLE's question first, because it is one line.** The profession
field is **4, 6, 8 or 10 bits, chosen per code**, so a profession id up to **1023**
serialises. It is not a byte and it is not a ceiling —
`CHAR_PROFESSIONS` is 11.

## 1. The five claims, scored

| # | The claim | Verdict |
|---|---|---|
| 1 | *"You can view any skillbar no matter what skills you have unlocked"* | **CONFIRMED** — §5. The decode path reads no account state at all, and the whole closure is enumerated |
| 2 | *"The template code only decodes correctly if all skills are loadable (non-PvP)"* | **CONFIRMED** — §4. A single byte, `s_skill[id] + 0x33`, must equal 1 for every non-empty slot. All 177 `pvp_only` rows fail it |
| 3 | *"The same thing happens when you have a skillbar with skills from a non matching profession"* | **CONFIRMED** — §3, clause 6c, and demonstrated on the poster's own second code (§7.1) |
| 4 | *"You can display temporary skills … but if you then copy and paste the template code it's just empty"* | **CONFIRMED, and the mechanism is an asymmetry** — §6. The encoder cannot look a skill up; the decoder does. The client hands you a code it will not read back |
| 5 | *"It does display the PvP version of the skill if you're in a PvP area (yes, including guild halls)"* | **CONFIRMED, and the parenthesis is a separate branch** — §8. `(AreaInfo.flags & 0x40000) \|\| AreaInfo.type == 4`, and `type == 4` is the guild halls, all seventeen |

One correction to our own tree on the way in: **`0x0058A790` is not the codec.**
[MODDABLE](../profession/MODDABLE.md) §8a called it "the function that formats **skill
templates**" on the strength of its two profession bound-checks
(`TemplatesHelpers:29 templatePrimaryProfession < CHAR_PROFESSIONS`, and `:30` for the
secondary), and it does bound-check two professions — but it formats the *window's
label*, the "⟨name⟩'s Skills and Attributes" line, through the coded-string builder at
`0x007C9410`. The codec is in `AcctTemplate.cpp`, four functions at `0x0091CB90`–
`0x0091D2C1`. MODDABLE's *instinct* was right (that function is one hop from the
template system and does gate on profession); its address was one module out.

## 2. TEMPLATES-F1 — the wire format. OBSERVED, transcribed instruction by instruction

Four functions, and it is worth naming which is which because the interesting result in
§6 is a difference between two of them:

| VA | What it is |
|---|---|
| `0x0091CFC0` | `SkillTemplateEncode(data, codeOut)` — sets up a bit writer, calls the field writer, base64s the result. Assert `AcctTemplate:549 code` |
| `0x0091CD50` | the field writer. **Calls exactly two functions in its entire body** (§6) |
| `0x0091D160` | `SkillTemplateDecode(code, dataOut, errOut)` — base64, header, then the field reader. Asserts `AcctTemplate:574 code`, `:575 skillData`, `:576 error` |
| `0x0091CB90` | the field reader **and the validator** — one function, returning one boolean (§3) |

**The alphabet is standard base64**, read out of the image at `0x00BC87D8` rather than
assumed, and the client `strchr`s into it and writes the **index** as six bits
(`0x0091C394`). So a code is a string of digits, not of bytes: there is no padding
character and no `=` anywhere in the format. Bits are little-endian within each field
and the character stream is the bit stream six at a time.

```
 4 bits   0xE          header    literally `push 0xE` at 0x0091CD5C
 4 bits   0x0          header
 2 bits   profSel      selector
 w bits   profPrimary  w = profSel * 2 + 4          <- MODDABLE's question
 w bits   profSecondary
 4 bits   attribCount
 4 bits   attribSel    selector
   x attribCount:
 a bits     attribId   a = attribSel + 4
 4 bits     rank
 4 bits   skillSel     selector
   x 8, always:
 s bits     skillId    s = skillSel + 8
```

**A selector is computed, not stored twice.** The client takes `bsr(max(values, 1)) + 1`
— `0x0046E110` is a bare `bsr eax, ecx` — and maps it onto the selector's own grid:
professions step **two** bits per selector step and are floored at 4
(`0x0091CD8E`: `if nbits < 5 then sel = 0 else sel = (nbits - 3) >> 1`), attributes and
skills step **one** bit and are floored at 4 and 8 respectively
(`0x0091CE76`, `0x0091CF3D`, both the `cmp/sbb/lea/not/and` idiom for `max(0, nbits-k)`).
So the encoding is minimal for its contents, which matters in §7.2.

**The character count is `ceil(pad8(bits) / 6)`, not `ceil(bits / 6)`.** The writer
drains the bit buffer six at a time until it reports empty (`0x0091C3B0`), and the
buffer's granularity is a byte — `0x005E8A40` pads the partial one on flush. That is why
a 126-bit template is **22** characters and not 21, and it is one of the five things
§7.1's exact round trip pins at once.

**The three ceilings a server inherits if it ever emits one**, each cited to its own
site because they are dialogs on a retail client rather than guards:

- `AcctTemplate:406  bitCountEncoding < 4` — so `w <= 10`, i.e. profession id < 1024
- `AcctTemplate:423  data.attribCount < 16`, and `:422 data.attribCount < arrsize(data.attrib)` bounds it at 12
- `AcctTemplate:465  data.skill[index] < SKILLS`

**Table sizes, all the client's own and all cross-checked against a structural read of
the table itself:** `SKILLS` = **3443** (`ConstSkill:3833 index < arrsize(s_skill)`, and
`skilltable.py` locates a 3443-row table by an unrelated conjunction of constraints);
`CHAR_ATTRIBS` = **51**; `CHAR_PROFESSIONS` = **11**.

**A header nibble of 0xF is refused outright** (`0x0091D268`), and a nibble `<= 13`
falls straight through to the fields with no second nibble read (`0x0091D266`). Nothing
the current encoder writes takes that second path; it is transcribed, not understood,
and §9 keeps it as a stated gap rather than a claim.

## 3. TEMPLATES-F2 — the decoder is a validator, and it returns one bit

`0x0091CB90` reads the fields and, in the same pass, AND-s together a chain of
predicates into `ebx`. The caller gets **one boolean** and no reason; an empty window is
all the player ever sees. The clauses, in the order the function computes them:

| # | Clause | Site |
|---|---|---|
| 1 | `profPrimary != CHAR_PROFESSION_NONE` | `0x0091CBC6` |
| 2 | `profPrimary < 11` | `0x0091CBCA` |
| 3 | `profSecondary < 11` | `0x0091CBCF` |
| 4 | `attribCount < 12` | `0x0091CBE9` |
| 5a | per attribute: `rank <= 12` | `0x0091CC37` |
| 5b | per attribute: `id < 51` | `0x0091CC49` |
| 5c | per attribute: its owning profession is **not** "none", and **is** the template's primary or secondary | `0x0091CC54` → `0x005A9320` |
| 5d | if the attribute is a **primary attribute**, its owner is the template's **primary** profession | `0x0091CC7F` → `0x005A92C0`, then `0x0091CC91` |
| 6a | per non-zero slot: `id < 3443` | `0x0091CCD5` |
| 6b | per non-zero slot: **`s_skill[id] + 0x33 == 1`** | `0x0091CCF8` |
| 6c | per non-zero slot: if the skill has a profession at all, it is the template's primary or secondary | `0x0091CD0D` |
| 7 | the bit reader never ran past the end of the code | `0x0091CD30` → `0x004C9A20` |

Three of these are worth a sentence each.

**Clause 6a–6c skip a zero.** `0x0091CCD1` short-circuits an empty slot, so a
three-skill bar is legal and its five empty slots are not checked. That is why the
poster's first code (five skills, three blanks) fails on its skills and not on its
blanks.

**Clause 5c/5d is the same rule the attribute-*apply* path enforces**, and we already
had that from the other side: [studies/profession/ATTRIBUTES.md](../profession/ATTRIBUTES.md):443
records `0x00818DF0` checking "membership in the character's primary/secondary pair …
plus, if the row's primary flag is set (`0x005A92C0`), exact equality with the primary".
Two independent sites, two arcs apart, same conjunction — which is a real corroboration
rather than one reading restated, because neither site calls the other.

**Clause 7 means a truncated code fails rather than decoding to garbage.** The reader
returns **zero** for bits that are not there and raises a flag at `reader+0x00`
(`0x005E87D3`); `0x004C9A20` is a one-instruction getter for exactly that flag.

**And the whole thing is context-free.** `0x0091CB90` makes calls to exactly five
functions in its entire body: the bit reader (nine times), the skill-row getter, the
attribute→profession getter, the attribute→primary-flag getter, and the overrun getter.
There is no call to the thread-context getter `0x0047F660`, no `AreaInfoGetRow`, and
nothing that could reach an unlock container. That is claim 1 answered, and the
enumeration is exhaustive over the function body rather than a search that came back
empty.

## 4. TEMPLATES-F3 — `s_skill + 0x33 == 1` is the loadable flag, and it is a 3-site predicate

`0x005A88B0` is `s_skill`'s row getter: it asserts `ConstSkill:3833 index < arrsize(s_skill)`
and returns `0x00988ED0 + id * 0xA4`. So the decoder's `cmp byte ptr [eax + 0x33], 1` is
a test on the same field `toolkit/clientscan/skilltable.py` already reads and calls
`equip_family`.

**The field is tested at exactly three sites in the image, and all three compare it
against the literal 1.** Found by taking every one of the 101 direct callers of
`0x005A88B0` and decoding forward for a `+0x33` access off the returned register:

| Site | What the caller does with it |
|---|---|
| `0x0091CCF8` | the decoder's clause 6b — the whole code is rejected |
| `0x008076DF` | `AcctCliTemplate`, reading a **stored** template: it walks the eight slots and **zeroes each offending one individually** before `rep movsd`-ing the 140-byte struct out |
| `0x00816E19` | `FindNextLoadableSkill(campaign, profession, cursor, out)` — the enumerator behind the skill picker, which only ever returns family-1 rows |

The middle row is a second, different behaviour and it explains the shape of the thing
the poster saw: **a pasted code fails whole; a stored template loses the offending slots
and keeps the rest.** Same predicate, two consumers, two failure modes.

**The census, over all 3443 rows of build 38797.** `equip_family` takes four values:

| value | rows | what is in it |
|---|---|---|
| 0 | 1041 | 662 with no profession, 151 `pve_only`, **and all 177 `pvp_only` rows** |
| **1** | **1333** | 1234 with a profession, 94 `pve_only`, 4 flagged `not_playable`, 1 with no profession |
| 2 | 607 | 429 with no profession |
| 3 | 462 | 461 with no profession — this is where the poster's monster skills are |

> **Zero of the 177 `pvp_only` rows are in family 1.** That is claim 2, exhaustively:
> the PvP version of a skill can never satisfy clause 6b, so a code carrying one is
> always blanked.

Two things this also settles, neither of which was the question:

- **`skilltable.player_corpus` has been right for the wrong reason.** It already defines
  "the player-usable corpus" as `equip_family == 1`, and its 1333 rows are the 1333 the
  client's own picker enumerates and its own decoder demands. That was our naming guess;
  it is now the client's rule, with three sites.
- **The four `not_playable` rows inside family 1** are an anomaly worth recording rather
  than smoothing: they would pass clause 6b. `TEMPLATES-Q1`.

## 5. TEMPLATES-F4 — no unlock state is consulted anywhere in the decode

Claim 1, stated as the measured negative it is. The decoder's own body is enumerated in
§3. Walking the transitive closure of both codec entry points gives the same answer with
a control attached:

| closure from | functions reached | reaches `0x0047F660` (the context getter)? |
|---|---|---|
| `0x0091D160` decode | 1215 | **no** |
| `0x0091CFC0` encode | 1210 | **no** |
| `0x0084D950` (a one-hop control) | 1187 | yes |
| `0x0058B000` (a two-hop control) | 1199 | yes |

The controls are the point: a 1215-function closure that misses the getter, beside a
1187-function closure that finds it, is not a scan that was simply too small. The
walker is approximate — it stops each function at its first `ret` and follows `jmp`
targets as calls — so the closure numbers are a shape, not a census; §3's enumeration
of the decoder's own five callees is the exact version.

This is the half of the forum argument that was actually in dispute, and it lines up
with what [studies/skills/FINDINGS.md](../skills/FINDINGS.md) §9 measured on a live
client from the other direction: unlock state does not gate whether a bar skill *draws*.
§47.3 of the same file found where unlock state **is** load-bearing —
`GmSkSlot.cpp:206 unlockedSkills->BitTest(sourceSkillId)`, the equip/drag validator, on
the **account** set. Display, no; equipping, yes. The template window is display.

## 6. TEMPLATES-F5 — the asymmetry: the encoder cannot filter, because it cannot look anything up

This is claim 4's mechanism and the most useful single fact in the arc.

**`0x0091CD50`, the field writer, calls exactly two functions in its whole body:**
`0x0046E110` (`bsr`) and `0x005E88A0` (the bit writer). It never calls `0x005A88B0`.
Neither does anything else in the encoder's closure (§5's table: `SkillGetRow` is absent
from `0x0091CFC0`'s 1210 functions and present in `0x0091D160`'s 1215). The encoder's
only skill-related check is the assert `AcctTemplate:465 data.skill[index] < SKILLS`,
which is a bound on the array index and nothing else.

> So the client will encode **any** id it is handed — a monster skill, a temporary
> skill, a PvP version — and then refuse the string it just produced. The code box shows
> you something you cannot paste back.

The UI does normalise ids before encoding, but in the direction that makes this worse,
not better. `TemplatesCode`'s pre-encode loop at `0x00586410`–`0x00586459` walks the
eight slots, maps any **PvP** id to its PvE twin (§8), remaps 3068 → 411, and *then*
calls the encoder. So a copied code is always in PvE form — which is why claim 5 is
about the *display* and not about the string.

`TEMPLATES-Q2`: the decoder has exactly **one** caller in the image, `0x005867E5`, the
"Template Code" text field's own change handler. Every other consumer of a template
(saved templates, the storage menu) works on the 140-byte struct and never sees a code.
So the entire rejection behaviour in this arc is reachable only by typing or pasting
into that one box. That is worth knowing before anyone designs around it.

## 7. Verification: the client's own codes, re-encoded

### 7.1 One exact round trip, and it is the load-bearing check

Both codes come from the forum screenshot — i.e. ArenaNet's client produced them and we
did not. Decoding them with the spec in §2 and re-encoding gives:

```
OQAAQoB/MafqiIC9gRbyZA   ->   OQAAQoB/MafqiIC9gRbyZA        identical, 22 of 22
```

**That single identity pins the field order, all three width rules, the bit order, the
alphabet and the byte-padding at once** — change any one of them and the string differs.
It is the only assertion in this arc whose input we did not manufacture, and it could
have failed at any of those five points. `toolkit/test_skilltemplate.py` §2 holds it.

What the two codes say, and it is exactly what the poster's two screenshots show:

| code | reads as | the client's verdict, clause by clause |
|---|---|---|
| `OgAAQHIIIJIKIVIAAAAAAA` — *"Nature Lurker (1)'s Skills"* | profession **2** / none, no attributes, skills `[519, 520, 521, 522, 533, 0, 0, 0]` | **BLANK**, on five counts, and **every one is clause 6b** — all five ids are `equip_family` **3**. None is `pvp_only`. The thread said "a monster only skill"; family 3 is what that is |
| `OQAAQoB/MafqiIC9gRbyZA` — *"Single Lurker's Skills"* | profession **1** / none, no attributes, skills `[104, 831, 2010, 2218, 136, 2109, 1745, 1650]` | **BLANK**, on five counts, and **every one is clause 6c** — all eight skills are family 1 and perfectly loadable, but five of them belong to professions 4, 4, 10, 8 and 7 on a `1/0` template |

**Two codes, two different clauses of the same conjunction, and the poster named both.**
The second is claim 3 in its purest form: nothing is wrong with any of those eight
skills, and the bar still will not display.

The professions are cross-checked rather than assumed: profession 1's single primary
attribute is 17, which [studies/skills/FINDINGS.md](../skills/FINDINGS.md) §9 measured as
Strength; skill 411 (profession 2) resolves to *Charm Animal* and 104 (profession 4) to
*Death Nova*. Warrior, Ranger, Necromancer — the conventional order, confirmed from
three unrelated places rather than taken from an upstream enum.

### 7.2 The one thing that does not reconcile, stated rather than smoothed

The Nature Lurker code declares a **12-bit** skill field for a bar whose largest id is
533, where §2's rule computes **10**. It decodes cleanly and self-consistently — the
width is read from the stream, not assumed, and the five ids it yields are four
consecutive rows plus one nearby, which is not what a wrong width produces — but our
encoder will never emit it, so it cannot round-trip.

Three candidate explanations: the string as transcribed from the screenshot differs from
the original; the code was produced by something other than this build's encoder; or the
width rule has a term §2 misses. **The third is the one that matters and it is
disfavoured**, because the other code's max id (2218) needs exactly 12 bits by the same
rule and round-trips to the character. Left open as `TEMPLATES-Q3`; a code produced by
our own client in a caged session would settle it in one press. The content reading in
§7.1 does not depend on it: a wider-than-minimal field decodes the same values.

## 8. TEMPLATES-F6 — the PvP substitution, both directions, and what "a PvP area" is

Claim 5. `s_skill + 0x2C` (`linked_id`) is the twin pointer, and **all 177 `pvp_only`
rows link back to a family-1 row**; 156 family-1 rows link forward to their PvP twin.
`0x00000D73` (= `SKILLS`) is the "no link" sentinel.

Thirteen sites in the image inline the same three-line helper after a `SkillGetRow`, and
they come in **two polarities** — which is the finding, because a reader who checks one
site concludes the mapping only goes one way:

```
row = SkillGetRow(id); linked = row->linked_id;
if (linked != 0xD73 && <test row->flags & 0x400000>) id = linked;
```

- `jne` form — substitute when `FLAG_PVP_ONLY` is **clear**, i.e. **PvE → its PvP twin**.
  Eight sites, including `0x0058C70B` in **TemplatesSummary**.
- `je` form — substitute when the flag is **set**, i.e. **PvP → its PvE twin**. Five
  sites, including `0x00585C0E` and `0x00586418` in **TemplatesCode** (the pre-encode
  normalisation of §6), `0x0058B01D` in TemplatesSummary, and `0x00541F20` in `GmSkSlot`.

`0x400000` is `FLAG_PVP_ONLY`, which `skilltable.py` already carries as a named constant.

**The gate on the PvE→PvP site is computed once, at the top of the icon-fill function
(`0x0058C640`), and it is two conditions:**

```
0058C661  call 0x0084D950        ; AreaInfo[currentMap].flags   (row +0x10)
0058C666  test eax, 0x40000
0058C66B  jne  set               ;   -> show PvP versions
0058C66D  call 0x0084DE30        ; AreaInfo[currentMap].type    (row +0x0C)
0058C67C  cmp  eax, 4
0058C67F  jne  clear
0058C681  set: [ebp-0x14c] = 1
```

Both getters resolve the current map id out of the context and index `AreaInfo` through
`0x005A8580`, so the offsets line up with the row layout
[studies/isle/PLAN.md](../isle/PLAN.md) and `areatable.py` already use.

**The census over all 888 AreaInfo rows**: **137** rows carry `flags & 0x40000` and
**17** rows have `type == 4`, and the two sets are **disjoint** — 154 maps in total.

> **All seventeen `type == 4` rows are guild halls.** Resolved through the owner's own
> archive: Warrior's Isle, Hunter's Isle, Wizard's Isle, Burning Isle, Druid's Isle,
> Isle of the Dead, The Underworld, Isle of Weeping Stone, Isle of Jade, Uncharted Isle,
> Corrupted Isle, Isle of Solitude and four more. That is the poster's parenthetical —
> *"yes, including guild halls"* — and it reads as a surprise in the post because it
> **is** a separate branch: a guild hall does not carry the flag.

**And an independent corroboration of what `0x40000` means, from a row we wrote down
before we knew.** [studies/isle/PLAN.md](../isle/PLAN.md) records, as OBSERVED, row 280
*Isle of the Nameless* with `flags 0x420000` and row 784 *Isle of the Nameless (PvP)*
with `flags 0x40000`, and quotes the wiki as saying the difference between the two maps
is that in the PvP one "all skills are converted to PvP versions". `0x420000` does not
contain `0x40000`; `0x40000` does. The flag we just found the gate on separates exactly
the pair the wiki says it separates, and neither reading knew about the other.

### 8.1 One hardcoded pair that the `linked_id` mechanism does not cover

Beside the general rule, the same loop carries a literal swap in each direction:
`0x0058B041` maps **3068 → 411** on the way into a code, and `0x0058C73B` maps
**411 → 3068** on the way to the screen, the latter gated on `0x005AD620` — a hardcoded
list of **15 map ids**: 796 and 823–836, which resolve to **Codex Arena** and the
fourteen random arenas.

411 is *Charm Animal*; 3068 is *Charm Animal (Codex)*. Both carry `linked_id = 3443`,
the sentinel — so the pair genuinely has no link to ride, which is presumably why it is
written out by hand. Recorded because a server or a tool reproducing the display rule
needs it, and because it is the kind of thing that looks like a decoding bug when you
meet it cold.

## 9. What this does NOT establish

- **The `<= 13` header path.** The current encoder never writes it and nothing in the
  corpus exercises it. Transcribed, not understood.
- **That the family values 0, 2 and 3 mean anything in particular.** Only `== 1` is
  tested anywhere in the image, so "loadable / not loadable" is all the client asserts;
  the three-way split among the rest is our observation about the data, not a reading of
  its meaning. `TEMPLATES-Q4`.
- **The `error` out-parameter's polarity.** `0x0091D160` writes **3** into it on entry
  and **0** on the failure path, and the one caller ignores it. The assert names it
  `error` (`AcctTemplate:576`); the values behave like a version. Not resolved, and
  nothing here depends on it.
- **Anything about the equipment template** (`AcctTemplate:221/222/511–513`,
  decoder `0x008048E0`). Same file, same shape, not read. `TEMPLATES-Q5`.
- **Any of this on another build.** One build, 38797. The four VAs are build-specific by
  construction; the *format* should not be, and `skilltemplate.py` holds no addresses,
  which is what makes it survivable.

## 10. What shipped

- **`toolkit/skilltemplate.py`** — the format (`decode`/`encode`/`Template`) as pure
  stdlib arithmetic with no client and no vault, plus `validate`, which is §3's
  conjunction clause by clause and **returns the reasons the client never tells you**.
  The two halves are deliberately separate: `validate` takes its three table lookups as
  injected callables, so the format half stays dependency-free and runs on a bare
  machine, and the CLI fills them from `clientscan/` when a vault is present.
- **`toolkit/test_skilltemplate.py`** — 51 checks with the vault, 35 without and a
  declared skip. §2 is the one that carries weight (§7.1); §5 runs the conjunction
  against the real tables with a **passing** control first, so a validator that refused
  everything could not score.
- **[studies/profession/MODDABLE.md](../profession/MODDABLE.md) §9's row is closed**,
  and its `0x0058A790` pointer corrected in place.

| Open | |
|---|---|
| `TEMPLATES-Q1` | four `not_playable` rows sit inside family 1 and would pass clause 6b |
| `TEMPLATES-Q2` | the decoder has exactly one caller — the code box. Nothing else in the client ever reads a code |
| `TEMPLATES-Q3` | §7.2's non-minimal skill width. One caged press would settle it |
| `TEMPLATES-Q4` | what families 0, 2 and 3 distinguish, if anything |
| `TEMPLATES-Q5` | the equipment template codec, untouched |
