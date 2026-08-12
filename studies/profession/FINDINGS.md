# Can we add an eleventh profession?

Six survey tracks against the vaulted client, the archive, our own captures and 21
mirrored prior-art repositories, each adversarially re-verified by a second reader who
re-ran every disassembly and re-derived every corpus count. This document is the
synthesis. Where a verifier weakened or refuted a survey claim, **the corrected claim is
what appears in the body** and the original is recorded in §12 — the corrections are the
most instructive part of the pass.

**The corrections outrank the survey, and they arrived in two waves.** Three in §12-C were
found during synthesis rather than by any surveyor or verifier: one **dissolves a negative
result that both readers agreed on**, one **reverses a verifier's own "correction" back to
the surveyor's number for a reason neither of them had**, and one **answers a question all
six tracks filed as unresolved**. Five more in §12-E came from a seventh reader asked only
*what is missing* — and those moved the answer further than any single track did, including
**settling this document's own top-ranked risk in five minutes** and **refuting an art
blocker with a study in this same repository that no track opened**. Every §12-E finding
was independently re-run before being folded in, and one of them was wrong. That is a fact
about how this document was made: nothing here was accepted because two agents agreed.

Read §12 before §1 if you want to know how much to trust §1.

No client was launched. `C:\gw` was never touched. The archive and both client builds
were opened `rb`. Nothing was written into the repo or the vault.

## Labels

| Label | Meaning |
|---|---|
| **MEASURED** | Checked against real bytes on this machine, this pass. We say which bytes: file, address, count. |
| **OBSERVED** | Watched happening in a running client, by this repo, at a dated pass. |
| **CLIENT-DATA** | Read out of the shipped client by a third-party tool whose code we read. Somebody else's reading of a primary artifact. |
| **SOURCE-CODE** | Read in some project's source, including ArenaNet's compiled-in asserts. Nobody's source is ground truth. |
| **UPSTREAM** | A reimplementation says so. A reconstruction, not a fact about retail Guild Wars. |
| **INFERRED** | Our reasoning on top of the above. Names the claims it stands on. |
| **CONTESTED** | Sources disagree and this document does not pick a winner. |
| **NOT FOUND** | We looked and there is no answer in what we have. This is a real result. |

Corpus throughout: `vault/client/2026-07-29_221c13772c7a/Gw.exe` (build 38797, 10,483,904 B),
the cross-check build `vault/client/2026-04-30_b174de1f2d8d/Gw.exe`,
`vault/dat_study/Gw.dat` (4,198,489,600 B), and the six live capture sessions under
`vault/captures/live/` (22,524 GAME_SMSG messages — this repo's own pinned figure).

---

## 1. The honest answer

**No — not the thing you asked for. Yes to a different thing, and that different thing
is available today with zero client bytes changed.**

A genuinely new eleventh profession that the client knows about is not reachable, and the
reason is not one wall you could climb. **Profession is not a row in a table. It is a
compiled-in array dimension**, and it is fixed at eleven in at least four structurally
different ways at once:

- as a **literal immediate** `0x0B` in `cmp` instructions at **29 independently-compiled
  bound-check sites across 13 source files** (MEASURED, and the tool that counts them
  states it is a floor — 19,758 assert sites read against an independent sweep finding
  20,131, so it is short by at least 370 image-wide);
- as the **declared size of at least eight distinct backing arrays** — profession name
  string ids, abbreviation string ids, campaign tag, a second name-id array, body scale,
  a costume body table, a costume hat table, and a composite-type count (MEASURED, named
  by the client's own array-size checks);
- as the **inner axis of two 2-D arrays** where the stride 11 is baked into an `imul`
  immediate — the hair-colour and skin-colour palette tables, `[4 races][11 professions]`
  of 8-byte records at VA `0x00A14FBC` and `0x00A15A7C`, both reached through
  `imul edx, esi, 0xb` at VA `0x005A8E7D` and `0x005A8F1D` (MEASURED). **Widening these
  is not appending a row — every race's row moves.** This is the single most
  under-reported shape in the whole pass and no track named it as a distinct patch cost;
- as a **code jump table**, not data: 12 slots at VA `0x005A5EB8` reached through
  `jmp dword ptr [eax*4 + 0x5A5EB8]` behind `cmp eax,0xb / ja` (MEASURED). A new case
  here is code insertion, not a number.

Every one of those tables **butts directly against unrelated data with zero padding** —
in each of the five static arrays checked, index 11 decodes as the first bytes of an
adjacent string or symbol (MEASURED). There is no spare row anywhere.

**And the failure mode is not "renders wrong". It is the end of the session, and that is
now MEASURED rather than inferred.** Every one of those 29 bound checks falls through and
uses the index whether or not the check passed (MEASURED at 11 sites across 8 modules) —
which reads as forgiving until you ask what the assert routine does. All six tracks and
all six verifiers filed that as unresolved, and §1 of an earlier draft of this document
called answering it the single highest-value offline experiment available. **It took five
minutes and it is answered** (MEASURED, build 38797, capstone + pefile, run twice by two
readers independently):

- `asserts.py` reports **one distinct callee across all 19,758 read sites** — every assert
  in the image routes to `0x00487BC0`.
- `0x00487BC0`'s only branch (`je` at `0x00487BF0`) selects between the caller's expression
  pointer and a default at `0x009409FC`; **both paths converge** at `0x00487C01` and fall
  into `call 0x00488210` at `0x00487C11`. The handoff is unconditional, so the `ret 4` at
  `0x00487C26` is unreachable epilogue.
- `0x00488210` contains **zero `ret` instructions** anywhere in its body
  `0x00488210`–`0x004884CC`. Its final instruction is `call 0x005BC094` at `0x004884C8`;
  `int3` padding begins at `0x004884CD` and the next function starts at `0x004884D0`.
- `0x005BC094` is a three-argument wrapper `(arg, 2, 0)` onto `0x005BBF04`, which sets up
  an SEH frame via `fs:[0]` and runs the MSVC CRT terminator chain.

**The assert reporter is noreturn.** That corroborates from the binary what `CLAUDE.md`
already recorded as OBSERVED from the smsgsweep pass — the process stays alive behind a
modal dialog with its message pump stopped and its socket open, measured there at a
31-second gap between the client going silent and the socket resetting. So an out-of-range
profession does not render badly. **It ends the session, and does so silently as far as
the socket is concerned.** See §12-E1.

### The cost split, and which half is which

**Cheap — free, today, zero client changes: behaviour.**
The wire is loose in exactly the way the client is rigid. Profession rides as a plain
`u8` on both direct carriers (GAME_SMSG `0x00A6`, `0x00B7`), and **the setter that
stores it contains no comparison instruction at all** — 0x007F7330 writes both payload
bytes into the agent's character-summary struct and fires an event, and there is not one
`cmp` or `test` against them in the function body (MEASURED, whole function read to its
`ret 8`). Skills, attribute ranks, stat rules, damage, energy, recharge behaviour — the
server owns all of it, and `studies/skills/FINDINGS.md` §5 already established that ~1,300
shipped skill ids are ours to redefine. A "custom profession" made of new behaviour
wearing an existing profession's identity needs **nothing from this document**.

**A month of experiments, and the tail is not bounded: identity.**
Name, abbreviation, icon, campaign badge, character-select portrait, body scale,
hair/skin palette, armour composite, animation set. Every one is a fixed-size client
table, and two of the nine are the re-strided 2-D arrays above. Worse than customarea's
import half, and for the opposite reason: customarea's blocker was *nobody has tried*;
this one's blocker is *we measured the thing and it is a compiled dimension*.

**The genuinely encouraging measurement, and it is in the middle.**
The client's own attribute-definition table has **nine reserved rows inside its existing
bound-checked capacity** — attribute ids 26, 27, 28 and 45–50, carrying the
out-of-range profession sentinel 11 and name/description string ids that resolve to
**empty text records** in the owner's archive (MEASURED, §5). That is nine unallocated
attribute slots, with their string ids already wired into the table, inside a 51-row
array the client bound-checks to exactly 51 in **three independent places** — the two
runtime sites in `ChCliAttrib` and the four static accessors at `0x005A9290`–`0x005A9320`.
And `studies/datwrite/FINDINGS.md` establishes that empty text records are fillable:
**678 string ids are empty plain records in all eleven languages simultaneously**, and
`toolkit/mapdata/datwrite.py` exists and is tested.

**So the reachable thing is (c), not (a) or (b): a new attribute set, with authored
names, under an existing profession id.** That is more than a reskin and less than a
profession. §2 is the menu.

### The one thing that would most change this answer, and it is offline

An earlier draft named the assert reporter here. That is now measured (above), and it
moved the answer **toward** pessimism rather than away from it. The next-most-decisive
offline question is a different one:

**Disassemble `CrProfession.cpp` — roughly `0x004D8750`–`0x004D9500`, ~3 KB — and learn
whether the character-creation profession picker is a loop over a table or hand-placed
controls.** That single fact decides whether (a)'s UI layer is a data edit or a code edit,
and nobody in this pass opened the module named for the thing the question is about.

Two measurements already frame it, and they point opposite ways:

- **Toward data-driven:** the sibling *chapter* picker **is** loop-driven — a back-edge at
  `0x004D884E` proving exactly three iterations over a table at `0x00BEF538` (MEASURED,
  §7). And the generic appearance picker `CrAppearancePick` bounds against a **runtime
  `valueCount`** at `0x004DB536`, not a compile-time constant.
- **Toward hard-coded, and this is the stronger signal:** `CrContext.cpp` bounds an
  appearance property against `CHAR_APPEARANCES` at `0x004DA514` and then asserts, at
  `0x004DA525`/`0x004DA536`/`0x004DA551`, that the property is **not** the profession, sex
  or race member. **Profession is enumerated as a character-appearance property and is one
  of exactly three deliberately routed around the generic data-driven picker** (MEASURED).

Note also what the census says about where the picker's arity is *not* enforced: **not one
of the 29 `CHAR_PROFESSIONS` sites lies in the `CharCreate` directory** (MEASURED — they
land in `ConstChar` ×10, `ConstCostume` ×4, `TemplatesHelpers` ×2, `ConstSealedDeck` ×2,
`CpsTex` ×2, `AcctTemplate` ×2, and one each in `ConstItem`, `ConstComposite`, `CpsPlayer`,
`GmSkTome`, `PvpItemList`, `VnUnlockSkill`, `UiCtlWebLink`). `CrProfession.cpp` carries
exactly **one** assert, at `0x004D8D94` (`CrProfession:123`), and it is a null-check on a
message parameter, not a `CHAR_PROFESSIONS` bound check.
Any experiment predicting that patching the 29 immediates changes what the creation screen
offers is predicting a failure from the wrong module. See L2b.

---

## 2. Three things "a custom profession" could mean

The question has three answers with wildly different costs, and the menu is the honest
deliverable.

| | **(a) A real 11th profession** | **(b) A reskin** | **(c) The middle: new attributes under an existing id** |
|---|---|---|---|
| What it is | Profession id 11, its own row in every client table, its own name, icon, armour | Server-defined skills, stats and behaviour riding on profession 1–10 | A profession-1–10 character whose bar draws on **reserved attribute ids the client already carries** |
| Client binary changes | 29+ immediates, 8+ tables grown, 2 tables **re-strided**, ≥1 jump-table case inserted | **none** | one field per reserved attribute row (profession 11 → an existing id); possibly none |
| `Gw.dat` changes | new name/abbrev text, new icon art, new composite textures | **none** | fill 1–9 **already-referenced empty** text records |
| Art | new body scale, hair/skin palette rows, armour composite set, animation set | none | none |
| Available today | **no** | **yes** | **not yet — one loopback probe away from knowing** |
| Honest cost | client-modding project, unbounded tail, per-build maintenance | zero | days-to-weeks, mostly experiments |
| What you don't get | — | a distinct name, icon, or badge anywhere in any UI | a distinct **profession** name/icon; you get distinct **attribute** names |
| Tooltip / label truth | correct if authored | **lies** (shows shipped text) | attribute names correct if authored; profession label still the host's |

**(b) is the whole of what `studies/skills/FINDINGS.md` §5 already recommends** and it
needs nothing from this pass.

**(c) is this document's actual finding**, and the thing that makes it interesting is
that the reserved slots are not something we would be sneaking past the client — the
client's own table declares them, bound-checks them, and ships string-id pointers for
them into records that are empty on purpose.

**(a) is refused on measurement**, not on effort. See §3.

---

## 3. What the client fixes: the profession dimension

### The constant

`CHAR_PROFESSIONS = 11` — valid ids 0..10, with 0 = None and 1..10 the shipped
professions in the numbering `studies/character/FINDINGS.md` already carries.

**MEASURED**, build 38797: **29 assert sites across 13 source files** name the symbol
exactly; a broader sweep for the word finds **55 sites across 20 files**. The immediate
is `0x0B`, compiled directly as the operand of a `cmp` a few bytes ahead of each
assert-call setup.

**The authoritative list is the tool's, not a transcription.** An earlier draft of this
section carried ~20 hand-copied addresses that were *inconsistently anchored* — some were
the `cmp`, some the assert VA, and several were neither — while omitting sites the census
names. Anything that patches or counts these must derive the set at run time from
`asserts.py --grep CHAR_PROFESSIONS`, not from a list in a document. The 29 sites, by
assert VA and module:line (regenerated this pass; expression text deliberately omitted per
`CLAUDE.md`'s provenance boundary — the row carries the constraint, not ArenaNet's
sentence):

| Module | Sites (assert VA · source line) |
|---|---|
| `ConstChar` ×10 | `0x005AA296`·288 · `0x005AAEF6`·353 · `0x005AAC33`·476 · `0x005AAE49`·593 · `0x005AB5A7`·608 · `0x005AB1A4`·720 · `0x005AB49A`·828 · `0x005ABAB7`·846 · `0x005AB8A0`·988 · `0x005ABA09`·1113 |
| `ConstCostume` ×4 | `0x008EE19E`·1197 · `0x008EE1E1`·1204 · `0x008EE281`·1225 · `0x008EE2C1`·1232 |
| `TemplatesHelpers` ×2 | `0x0058A79B`·29 (primary) · `0x0058A7B7`·30 (secondary) |
| `ConstSealedDeck` ×2 | `0x005AD823`·1690 · `0x005AD97F`·1701 |
| `CpsTex` ×2 | `0x0083217B`·198 · `0x008322B6`·267 |
| `AcctTemplate` ×2 | `0x0091CDD0`·411 · `0x0091CDEA`·412 |
| `ConstItem` | `0x005A91B2`·12039 |
| `ConstComposite` | `0x005AE213`·460 |
| `CpsPlayer` | `0x0083159B`·407 |
| `GmSkTome` | `0x00510F6C`·210 |
| `PvpItemList` | `0x0057A5EC`·579 |
| `VnUnlockSkill` | `0x005A09F1`·218 |
| `UiCtlWebLink` | `0x00884517`·631 |

Ten of the 29 are the `ecx`-first assert shape and 19 the `edx`-first; the tool reports
that split, which is why a fixed-pattern scan for one idiom under-reports.

**Note what is absent: none of the 29 is in the `CharCreate` directory.** The
character-creation modules enforce the picker's arity somewhere else, or not with this
symbol. See §1's offline question and L2b.

The same census on the 2026-04-30 build returns **29 sites / 13 files** as well, with the
backing arrays relocated but byte-identical in content (MEASURED). So the dimension is
not a build-38797 accident.

**The bound is not uniform.** Two sites in the skill-vendor store module check against
`0xFF` rather than 11, at `0x004D03A9`, and disassembly shows the checked value being
packed into a composite sort/filter key (`shl esi,8 / or esi,[…] / shl esi,0x10`) rather
than used as an array index — with an unrelated `0xFFFF`-bounded field checked two
instructions later (MEASURED). **So there is no single global byte replacement that
patches all sites**, and a mechanical "bump every `0x0B`" pass would get at least three
sites wrong (these two, plus the jump table below).

### The backing tables

Named by the client's own array-size checks in one constants module at
`0x005AB7C1`, `0x005AB7F1`, `0x005AB821`, `0x005AB851`, plus the composite and colour
modules. All content MEASURED by direct byte read; **index 11 in every static case
decodes as the start of adjacent unrelated data, never a plausible 12th entry.**

| Symbol | VA | Shape | Contents (ids/values only) | Growth shape |
|---|---|---|---|---|
| `s_charProfession` | `0x00A38794` | 11 × u32 | name string ids **2040–2048**, then **31548, 31549** | append |
| `s_charProfessionAbbrev` | `0x00A387E8` | 11 × u32 | abbreviation string ids **2049–2057**, then **31553, 31554** | append |
| `s_profChapter` | `0x00A384F0` | 11 × u32 | **0,0,0,0,0,0,0,2,2,3,3** | append |
| `s_charProfession` (second, same source name) | `0x00A38868` | 11 × u32 | **2058–2066**, then **31556, 34524** | append |
| `s_scaleBase` | `0x00A96B7C` | 11 × f32 | 1.0, 1.05, 1.0, 0.95, 1.03, 1.05, 1.05, 1.0, 1.03, 1.0, 1.0 (index 11 is a subnormal, 1.019e-38) | append |
| `s_colorInfo` (hair) | `0x00A14FBC` | **[4][11] × 8 B** | reached `imul edx, esi, 0xb` then `[edx*8 + base]` | **re-stride** |
| `s_colorInfo` (skin) | `0x00A15A7C` | **[4][11] × 8 B** | same shape, `imul` at `0x005A8F1D` | **re-stride** |
| costume body / costume hat | `0x00BBD73C` / `0x00BBE680` | 11-entry, 16 B / 4 B stride | reached from `0x008EE1D7` / `0x008EE2B7` | append |
| `s_type[0].count` | — | struct member | bounded at `0x008332E9` | struct edit |
| profession dispatch | `0x005A5EB8` | **12 × code address** | see below | **code insertion** |

Two further profession-keyed lookups are **not memory-resident at all**: at
`0x005AB470` and one other site the compiler materialised a 2 × 10 table as twenty
sequential `mov dword ptr [ebp+off], imm` stack stores, indexed `esi + edi*10` with
profession 0/None excluded by a separate `test esi,esi` guard (MEASURED). **Extending one
of those means inserting instructions**, and the "find the spare row" framing does not
apply to it at all.

**The name and abbreviation ids resolve.** All 11 of each resolve to real text records in
the owner's archive, in the profession order this repo already records (MEASURED via
`textrec.py`). The two Nightfall professions sit in a far, separate id block (31548/31549,
31553/31554) rather than continuing the contiguous 2040–2057 run — consistent with later
allocation, though the *reason* is INFERRED from the gap's size, not read anywhere.

**So a profession's name is authorable the ordinary way** — commit the id, resolve the
string at run time, exactly the pattern `mapbuild.py` already proves. It is the only
piece of profession identity that is.

### The one soft spot, and both verifiers found it independently

The dispatch table at VA `0x005A5EB8` is guarded by `cmp eax,0xb / ja` — an **unsigned**
comparison, so its valid range is **0..11 inclusive, twelve values**, one wider than the
`0..10` every other site enforces. All 12 slots resolve inside `.text`
(bounds `0x00401000`–`0x00938C00`), and **slots 0 and 11 both point at `0x005A5A67`** —
the only repeated address in the table, giving 11 distinct targets across 12 slots
(MEASURED, table dumped in full this pass; both the T1 and T5 verifiers found this
independently and neither surveyor did).

**Consequence that matters:** profession id 11 — the value an eleventh profession would
naturally take — does **not** trip this widget's unmatched-case assert. It silently takes
the same path as profession 0 (None).

Whether that is a real twelfth UI value or ordinary compiler identical-code-folding of
two textually different case bodies is **CONTESTED and this document does not pick a
winner.** Both readings fit every byte measured. It matters, because a mechanical bound
patch that treats this as a genuine 12-way dispatch would be wrong under the second
reading.

**A label correction owed here:** the survey called this a character-creation control. It
is not. Its source module is under the client's **Vendor** UI namespace, not the
`CharCreate` namespace where the actual character-creation state machine lives (MEASURED
via `asserts.py --at`). Its real screen — plausibly a secondary-profession-change vendor
or a profession filter — **was not traced** and is NOT FOUND. That one-step trace
(`--xrefs` on the function entry) bears directly on the CONTESTED reading above and
nobody ran it.

### The gate that needs art, not numbers

One function at `0x008322A0` chains **four** bound checks before doing real work:
profession `< 11` at `0x008322AC`, then `< 6` at `0x008322C8`, `< 8` at `0x008322E1`, and
`< 2` at `0x008322FE`, then calls `0x00777F10` at `0x00832321` — which loads a resource
via a tagged string constant, null-checks the return, and asserts on failure (MEASURED,
both callee and caller disassembled). The client's own vocabulary at the adjacent sites
names the second and third axes *component* and *resolution* (SOURCE-CODE), so this is
the character armour/skin **composite texture** pipeline, gated on profession before any
blit.

**This is the blocker the provenance gate touches.** A new profession needs real
per-combination texture assets to get past it, and we can neither derive ArenaNet-quality
replacements nor commit them if we could. Whether the four axes are one literal
11×6×8×2 array or four independently-sized tables consulted by sub-calls was **not
traced** — NOT FOUND.

Profession also gates hair-colour and skin-colour palette selection through the two
re-strided 2-D tables above (MEASURED) — a consequence surface no track's headline
covered.

### Animations are a different, larger bound

`AvChar` carries an animation bound of **`0x3F` = 63**, checked at `0x007FBC2D`
(MEASURED) — a completely different and much larger constant than `CHAR_PROFESSIONS`.
No profession-named bound check appears among the readable asserts in either character
animation module (34 sites total) or in the generic icon module (8 sites) — **NOT FOUND**,
and weak, because the census is a documented floor. The inference that animation selection
keys off weapon/skill rather than profession is INFERRED from that absence and was not
traced; treat it as a lead, not a result.

---

## 4. What the protocol carries, and who decides

**The wire is loose. It is not the wall, and it is not the lever either.**

### Field widths, from the client's own message-format tables

MEASURED via `msgshape.py` against build 38797 (not from our imported schema):

| Opcode | Direction | Shape | Wire bytes |
|---|---|---|---|
| `0x00A6` | S→C | `agent_id, u8 primary, u8 secondary` | 8 |
| `0x00B7` | S→C | `agent_id, u8, u8, u8` | 9 |
| `0x00B6` | S→C | `agent_id, u32 bitmask` | 10 |
| `0x0059` | S→C | `u32, agent_id, u32 appearance, u8 secondary, u32, u32, string16` | 89 |
| `0x0056` | S→C | six dwords, **two u8**, name string | 46 |
| `0x01BF` | S→C | `string16(20)` name, then two u8 | 50 |
| `0x015A` | S→C | `u32 item_id, u8 profession` | 7 |
| `0x0060` | **C→S** | `u8 chapter, u8 profession` | 4 |

**The narrowest carrier is a 4-bit nibble.** The `0x0059` appearance dword packs primary
profession into bits 20–23 — 16 slots. Our own `authsrv.py` independently documents the
same packing (`face:5, primary_profession:4, hair_style:6, race:2`, low bits first), so
this is two witnesses, one of them ours. Eleven fits; **a sixteenth profession would
not.** The other three carriers are u8/u8/u32 and are not limited this way, so the
constraint is field-specific, not protocol-wide.

**Naming note:** the client's own noun for `0x0060`'s first field is *chapter*, not
*campaign* — recorded in `schema/overrides.json`, and the survey's "u8 campaign" label
contradicts its own source material.

### Who decides — and it is already answered in this repo

`schema/overrides.json`'s entry for GAME_CMSG `0x0060` carries a **refutable prediction
that already passed**: field 2 of the last `0x0060` a client sends predicts the server's
own later `0x00A6` primary for that character, in both sessions, on two different
professions. **The client picks and sends; the server echoes back.** (SOURCE-CODE +
MEASURED — it is our own recorded prediction against our own captures.) No track surfaced
this, and it sits four lines from an entry one of them did cite.

Its consequence for this question is the important part: **the profession picker is a
client-side widget.** A human on an unpatched client cannot make it *send* a profession
the picker has no button for. A custom id must be assigned by the server after the fact,
bypassing the picker — or the creation UI must itself be patched.

### What real ArenaNet traffic actually shows

MEASURED over all six live sessions (22,524 GAME_SMSG), re-derived independently by the
verifier after a field-indexing defect in the first pass:

- **`0x00A6`: 387 instances.** Primaries exactly `{1,2,3,4,5,6}` — never 0, never 7–10.
  Secondaries `{0,1,2,3,4,5,6,8}` (id 8 appears 8 times as a secondary, never as a
  primary). **Primary never equals secondary in 0 of 387**, corroborating the client's own
  paired invariant.
- **`0x00B7`: 29 raw instances across 11 connections.** This **corrects a stale NOT FOUND**
  in `studies/character/FINDINGS.md`, which was accurate for the corpus that existed when
  it was written. Of the 11 connections, 8 fire it exactly once and in every one of those
  the primary byte equals that agent's own `0x00A6` primary (4× profession 4, 4× profession
  2, trailing bytes 0). **Two connections fire it seven times each for the same agent**,
  with the byte progressing over 2–3 seconds — so "sent once per instance load" is wrong,
  and the 21 messages on those two connections have no `0x00A6` counterpart to check
  against at all.
- **`0x00B6`: 11 instances, every one `0x00000000`.** This **contradicts OpenTyria's
  `unlocked_professions = 1 << primary_profession`** (UPSTREAM). All 11 samples are
  early-game characters, so "0 is simply correct for a level-1 core character with no
  unlocks" is an untested alternative reading.
- **`0x0056`'s first trailing byte reads 11 in 5 of 126 messages** — exactly
  `CHAR_PROFESSIONS`, one past the last valid player profession. Independently reproduced
  by `studies/presearing/R4C2-FEASIBILITY.md` through a different pipeline. Whether those
  5 agents are NPC-kind was not confirmed in this pass; if they are, the wire slot is
  reused for a larger-range quantity on non-player agents and says nothing about the
  player enum.

**Corpus caveat that governs all four bullets:** all six live sessions are early-Prophecies
content. The absence of primaries 7–10 is a fact about **this corpus's content coverage**,
not about how the client or ArenaNet's server treats those ids.

### Our own server refuses it first

`toolkit/authsrv/agents.py:166` defines `CHAR_PROFESSIONS_MAX = 6` with the comment
*"observed primaries are 1..6; 0 NEVER occurs"*, and `agent_set_profession` raises on
anything outside `1..6`. **This is not the client's constant** — it is an observed-data
floor from an older, smaller corpus that happens to differ from the real compiled bound
(11) by the letters `_MAX`. It is also the **first** thing that would refuse every
experiment in §10, and no track flagged it as a prerequisite.

**NOT FOUND:** any client-to-server opcode for changing secondary profession
post-creation. `0x0060` occurs 15 of 15 times on character-select connections only
(`studies/reconstruction/FINDINGS.md`), and the live corpus never captures a visit to a
profession-change NPC. Absence of a found opcode, not proof of none.

---

## 5. Attributes — where the spare room actually is

**This section is the pass's real result, and both readers got it wrong in the same way.**

### The table, at its true base

The attribute definition table is **51 records of 20 bytes** at VA `0x00A35740`
(file offset `0x634740`), ids **0..50**, ending at VA `0x00A35B3C` — **exactly where the
adjacent source-path string begins, with zero padding** (MEASURED, dumped in full this
pass).

The base is not where either reader put it. It is derived from the client's own accessors
rather than from a structural scan: four single-field accessor functions at
`0x005A9290`, `0x005A92C0`, `0x005A92F0` and `0x005A9320` each bound-check
`index < 0x33` (51), compute `index * 20` as `lea eax,[esi+esi*4]` then `[eax*4 + base]`,
and read bases `0x00A35740`, `0x00A35748`, `0x00A3574C` and `0x00A35750` — i.e. record
offsets +0x00, +0x08, +0x0C and +0x10. **The lowest of those four is the table base.**
The survey and its verifier both worked from `0x00A35748` — the *name-field* accessor's
base, eight bytes high — and every downstream error follows from that. See §12-C1.

Record layout, MEASURED and matching field-for-field the `AttributeInfo` struct
`studies/skills/FINDINGS.md` already carried from GWCA's scan pattern
(CLIENT-DATA, MIT, one witness):

| Offset | Field | Accessor | Callers |
|---|---|---|---|
| +0x00 | profession id | `0x005A9320` | 6 |
| +0x04 | attribute id (== row index in **51 of 51**) | *none — redundant with the index* | — |
| +0x08 | name string id | `0x005A92F0` | **22** |
| +0x0C | description string id (== name+1 in **50 of 51**) | `0x005A9290` | 1 |
| +0x10 | **primary-attribute flag** — see below | `0x005A92C0` | 5 |

The absence of a +0x04 accessor is itself a check: the field is the index, so nothing
needs to read it. That the four accessors' bases are exactly `base+0/8/0xC/0x10` and that
`id == index` holds in 51 of 51 is what makes the alignment refutable rather than fitted.

The same 51 bound is enforced twice more, independently, on the **runtime** per-character
rank array in `ChCliAttrib` — `cmp ebx,0x33` at `0x00818CC9` and `0x00819244`, both
followed by the identical 20-byte stride arithmetic (MEASURED). A third 51-bounded
structure exists at `0x00C0EEC0` — a runtime pointer array, checked `cmp esi,0x33` at
`0x005A9265` — which nobody has characterised (NOT FOUND).

### The contents: 42 real ids, 9 reserved

MEASURED, complete:

| Profession | Attribute ids | n |
|---|---|---|
| 1 | 17, 18, 19, 20, 21 | 5 |
| 2 | 22, 23, 24, 25 | 4 |
| 3 | 13, 14, 15, 16 | 4 |
| 4 | 4, 5, 6, 7 | 4 |
| 5 | **0**, 1, 2, 3 | 4 |
| 6 | 8, 9, 10, 11, 12 | 5 |
| 7 | 29, 30, 31, **35** | 4 |
| 8 | 32, 33, 34, **36** | 4 |
| 9 | 37, 38, 39, 40 | 4 |
| 10 | 41, 42, 43, 44 | 4 |
| **11 (sentinel)** | **26, 27, 28, 45, 46, 47, 48, 49, 50** | **9** |

This reproduces, id for id, the profession→attribute blocks measured **independently
from the skill table** — `skilltable.py` over 3,443 rows, cross-tabbing the profession
byte at +0x28 against the attribute byte at +0x29 — including both discontinuities
(profession 7 owning 35, profession 8 owning 36). Two separately-compiled client tables
agreeing is corroboration within one build, not across implementations.

It also **settles a numbering dispute** `studies/skills/FINDINGS.md` §1 already
adjudicated on UPSTREAM evidence: ids 26/27/28 are unused and Mysticism sits at 44, not
41. That was three sources against OpenTyria; it is now MEASURED from the client's own
table, and OpenTyria's attribute enum should still not be imported.

### The nine reserved slots resolve to *empty* text records

All 51 name string ids resolve against the owner's archive. The 42 real ids resolve to
real text. **All nine sentinel rows — ids 26, 27, 28, 45, 46, 47, 48, 49, 50 — resolve to
records that are empty** (MEASURED via `textrec.py`; ids 2122/2124/2126 in text file 2 at
records 74/76/78, id 71982 in file 70 at record 302, and ids 100257/100259/100261/100263/100265
in file 97 at records 929–937).

That is the finding worth the section. Nine attribute slots that:
- are inside the client's own bound-checked capacity (51) at **three independent sites**;
- carry real, distinct, already-allocated name and description string ids;
- point those ids at text records that are **empty** — unallocated, not merely unread;
- and sit in a table where `studies/datwrite/FINDINGS.md` has already established that
  empty string records are fillable (**678 empty ids across all eleven languages**, in
  contiguous runs up to 329) and that `Gw.dat` can be written, with every checksum rule
  measured and `datwrite.py`/`datplan.py`/`datcheck.py` shipped and tested.

**GWLP-R's own database independently marks 26/27/28 as reserved** (BSD-style licence;
used here only to verify a value we derived ourselves, per `CLAUDE.md`'s second gate — no
layout, algorithm or table was taken). Its rows assign professions 5, 4 and 2 to those
three ids; **the client's own table assigns 11 to all three.** That divergence is
MEASURED and worth carrying: GWLP-R's DB is a reconstruction here, not a witness.
GWLP-R's DB has no rows at all for 45–50.

### The primary-attribute marker — refuted by both readers, and they were both wrong

The +0x10 field marks, in the corrected alignment, **exactly one attribute per profession
and zero in the sentinel block**: ids `{0, 6, 12, 16, 17, 23, 35, 36, 40, 44}` for
professions `{5, 4, 6, 3, 1, 2, 7, 8, 9, 10}` respectively. Ten flagged rows in 51
(MEASURED).

That set is **exactly, id for id and profession for profession, the ten rows GWLP-R's
database marks `(Primary)`** — a 2013 lineage independent of ldufr/GWCA (MEASURED
comparison; GWLP-R used as verification only). And the Warrior's flagged id, **17**, is
the attribute `studies/skills/FINDINGS.md` already ties to the Warrior's primary from a
wiki cross-check taken through the client's own unlock panel (OBSERVED, in this repo).

**Both the surveyor and the verifier reported this field as NOT a primary-attribute
marker**, on the strength of Elementalist and Assassin blocks showing zero flagged rows
and the Warrior block showing two. Every one of those observations is an artifact of the
8-byte base error, which paired record *i*'s flag with record *i+1*'s profession and id.
The verifier confirmed the wrong result by reproducing the same misaligned read. See
§12-C1.

**A correction owed upstream:** GWCA names this field `is_pve`
(`Include/GWCA/GameEntities/Attribute.h`, MIT). Against the bytes it is not a PvE marker
— no row has it set except the ten primaries, and the six reserved rows most likely to be
PvE-flavoured (45–50) all read 0. `studies/skills/FINDINGS.md` imported that struct with
the field name attached. §12-D.

### What the server controls

The client-side function that writes a character's total attribute-points pool copies its
caller-supplied parameter straight into the per-character struct at +0x434 with **no
points-per-level or points-per-rank formula anywhere in the function body** (MEASURED,
whole function `0x008199E0`–`0x00819A97` read). Consistent with the client trusting
whatever total the server sends.

**NOT FOUND:** the per-rank attribute point-cost curve as a literal. Searched the full
image for the published sequence as u8, u16 LE, u32 LE, and as a cumulative variant —
zero hits for all four. Computed procedurally, stored at another width, or stored
non-contiguously; the negative rules out four encodings, not the concept.

---

## 6. Skills — no room, and no need

Short, because the answer is already in `studies/skills/FINDINGS.md` §5 and this pass
only hardened it.

**The table is full.** `s_skill` holds exactly **3,443 rows of 0xA4 bytes** at file offset
`0x587ED0`, with **zero blank rows** — every row carries a non-zero, table-wide-unique
name string id (MEASURED). The bound on an index is a compile-time immediate `0xD73`
(3,443) baked into machine code at **four** sites in one module (`0x005A88B7`,
`0x005A898A`, `0x005A89C3`, `0x005A89EB`) — **not** read at runtime from the table's own
row-0 count field, so patching that stored count alone would change nothing the client's
own memory-safety checks enforce.

**There is nowhere to grow in place.** The bytes immediately following the last row are
live linker-placed constant data, not padding, and the largest contiguous zero run in the
entire 2,830,336-byte `.rdata` section is **1,055 bytes** — six rows' worth, and located
elsewhere in the section (MEASURED, full-section scan, 296,799 runs). This rules out
appending in place; it does **not** evaluate appending a new PE section or relocating
`.rdata` content, neither of which was attempted.

**The skill record's own profession byte has headroom and it is irrelevant.** It takes
exactly 11 distinct values (0..10) across all 3,443 rows and across the 1,333-row player
corpus alike, well inside its structural 0..255 range, and **nothing bound-checks it** at
the table accessor (MEASURED). Growing *that* field's range is free; it just does not buy
anything, because everything downstream is gated on `CHAR_PROFESSIONS` instead.

**The real cost of a genuinely new skill id is nine relocations, not four immediates.**
`studies/datwrite/FINDINGS.md` measured the skill table's base as referenced by **nine
relocated absolute addresses across three base constants, plus a row-count immediate** —
and its tail abuts the very strings every scanner uses to find the array.

**All 34 skill-related opcodes carry only numeric primitives.** `schema/messages.json`
declares nothing but `{msg_header, agent_id, byte, word, dword, array32, vec2}` across the
24 SMSG and 10 CMSG opcodes this study names (MEASURED against the schema file). But that
is a fact about **the imported schema**, and the schema was imported from OpenTyria: only
**3 of the 34** are validated against real wire bytes from this build, and the source
study flags CMSG shapes as resting on unstated derivation with 0/194 tables carrying the
handler anchor SMSG has. **INFERRED, not MEASURED**, for the other 31 — and no real
capture was checked this pass to strengthen it.

---

## 7. Art, UI and strings — the half that actually decides it

| Piece | Where it lives | Authorable? |
|---|---|---|
| Profession **name**, **abbreviation** | `Gw.dat` text records via string ids in 11-entry PE arrays | **Yes in principle.** Ids resolve at run time; 678 empty string ids exist. Needs the PE array grown. |
| Profession **campaign/chapter tag** | `s_profChapter`, 11 × u32 | Append a row; the value space (0/2/3, with 1 unused) is not decoded — NOT FOUND what the ids name |
| Profession **glyph / icon** | **Format: solved. Consumer: NOT FOUND.** | Authoring a texture the client draws is a **closed problem in this repo** — see below. What is unlocated is *which widget resolves the profession glyph*. The one profession-aware icon-bearing widget found (the Vendor jump-table control) drives its icons from three shared static image lists selected by a hard-coded switch rather than an archive-resolved file id; the party-window / nameplate glyph was not identified. That is a **search** problem, not a format problem. |
| **Body scale** | `s_scaleBase`, 11 × f32 | Append a row. Values cluster 0.95–1.05, implying a shared base humanoid mesh scaled per profession rather than 10 separate meshes — **INFERRED** from the data shape; where the scale is applied was not traced |
| **Hair / skin palette** | two `[4][11]` 2-D arrays with stride 11 in an `imul` immediate | **Re-stride**, not append |
| **Armour composite textures** | the four-axis gate at `0x008322A0` | **No.** Needs real per-combination art; provenance forbids committing it and we cannot derive it |
| **Default armour set** | `GmDefaultArmors`, a hand-authored table of complete item literals per (chapter, profession) slice | Not re-measured this pass — UPSTREAM (`studies/character/FINDINGS.md`, OpenTyria). Its dispatch is by profession count 6/8/8/10 across four slices |
| **Animations** | bound `CHAR_ANIMATIONS = 63`, no profession-named check found | Probably not profession-keyed — **INFERRED from absence**, weak, census is a floor |

**The icon blocker in the paragraph that used to sit here was stale, and this document
reproduced its own §12-A3 error to put it there.** The claim carried forward from
`studies/datwrite/FINDINGS.md` was that *nothing in the entire evidence base makes the game
draw a texture that is not already in `Gw.dat`*, blocked on an unreversed mip-chain framing
and on `DXTL`. **All three clauses are false as of 2026-08-06**, and the counter-example is
this project's own — `studies/texture/FINDINGS.md`, which no track and no verifier opened:

- **OBSERVED (§3, §4b):** the retail client drew a skill icon this project authored from
  nothing — the image, the DXT1 encoding, the container, the archive write, all of it ours.
- The mip-chain framing **is** reversed (§1): a 12-byte header plus 8-byte level records,
  the walk closing exactly on 52,253 of 53,922 rows.
- `DXTL` is **not on the critical path** (§5): the skillbar reads `+0x90`, which is DXT1
  128×128. `DXTL` lives at `+0x8c`, and what consumes `+0x8c` is a separate open question.
- §5's standing summary: *any DXT1 texture at any legal dimension, single-level or full
  chain, written into the archive as a stored entry and drawn by the client.*

So the profession glyph is **not** the same problem as the skill icon wearing a different
hat. The skill-icon problem is solved end to end. The glyph's remaining unknown is
narrower and differently shaped: **which widget resolves it, and whether that widget is
archive-resolved like the skillbar or a compiled-in image list like the Vendor control.**
`toolkit/clientpatch/repoint_skill.py` is the direct precedent for the probe that answers
it, and L2c is that probe.

This matters to the *shape* of the answer, not just its tone: the authored-icon path is
stdlib-only with no ArenaNet bytes in it, which is the strongest evidence in this document
that **(c) stays inside the provenance gate**.

**A structural note that cuts the other way.** The character-creation *chapter* picker is
loop-driven, not hand-placed: a counter at `0x004D8700` onward tests successive bits of an
account-owned-chapters mask and indexes a table at `0x00BEF538`, with the loop's back-edge
at `0x004D884E` (`cmp edi,3 / jb`) proving **exactly three iterations**, and the table
reading as three rows of pointer + flag (MEASURED). So the **campaign-selection layer is
data-driven** even though the profession-identity layer is not. That asymmetry is real and
was not predicted.

---

## 8. Has anyone done this?

**No. Zero, across all 21 mirrored repositories.**

Nobody has added a profession, a skill, or an item the shipped client does not ship, and
there is no discussion of trying. Two independent sweeps — one broad regex pass across the
mirrors, one per-repo pass by the verifier — returned 175 candidate hits between them,
every one incidental (variable names, UI strings, bot scripts using existing professions).
This is the same *nobody tried* verdict `studies/customarea/FINDINGS.md` reached for map
geometry, and it means the same thing: **there is no reference implementation and no
documented failure to learn from.** (NOT FOUND. Searched code and docs in 21 git
snapshots — **not** issue trackers, PRs, or any web forum, so this is "not in what we
hold".)

**A methodological warning worth more than the result.** The verifier demonstrated
concretely that a single `Grep` call scoped to the whole ~1 GB `vault/mirrors/` tree
**silently returns fewer results than the identical search run per-repo** — it missed a
real match and ten real files that a narrower search found. Every NOT-FOUND in this repo
that rests on one whole-tree sweep should be re-run per-repo before it is trusted.

**What the mirrors do say about the profession bound**, all UPSTREAM or SOURCE-CODE and
all one-way (they enforce 0..10, none extends it):

- OpenTyria (C) and Headquarter both validate with an 11-case enum and reject anything
  else. **Same author — one witness, not two.**
- GWLP-R enforces it with a SQL foreign key to a 10-row table (ids 1–10, no None row);
  its Java layer reads the raw 4-bit nibble and passes it unchecked to a JPA `find`, which
  returns null rather than throwing — so an out-of-range id yields a silently-null
  profession, not a clean rejection.
- `gw-preservation/server` (Go) and `sgwlpr` (Scala) treat profession as an **unvalidated
  pass-through**; sgwlpr's own source carries a standing TODO admitting it, and
  gw-preservation reassigns the field unconditionally before any check, with a following
  switch that has no default arm and covers only 6 of the 10 professions.
  **`gw-preservation/*` grants no licence — verify-only.**
- `Fournux/Tyria-Extractor` scores a candidate skill table partly on `profession <= 10`.
  Not clean-room for client structures (its own README credits GWToolbox++/GWCA).

The only plural-professions wire message anyone models is an **unlock bitmask** over an
account (`agent_id` + one bitfield). **Nothing anyone has reverse-engineered supplies the
client with a list of which professions exist** — that list is client-local data.
INFERRED, standing on the absence across two independently-modelled catalogues; it is
absence of a counter-example, not proof.

---

## 9. What would have to be true

Ranked by how badly a wrong one hurts. Each names the experiment that would test it.

| # | Assumption | If wrong | Test |
|---|---|---|---|
| **1** | ~~An assert does not end the session.~~ **RESOLVED AGAINST US, this pass.** The assert reporter is noreturn: one shared callee across all 19,758 sites, an unconditional handoff at `0x00487C11`, zero `ret` in `0x00488210`–`0x004884CC`, terminating in the CRT terminator chain via `0x005BC094` (MEASURED, §1, §12-E1). | Not a risk any more — a **constraint**. Every one of the 29 bound checks is a session-ender, so a patch plan that leaves one site unpatched does not degrade, it stops. | Done. Consequence: **L5 must not run before L2/L2b**, since its failure mode is now indistinguishable from every other assert |
| **2** | **The 9 reserved attribute ids are usable at runtime, not merely present in a table.** Everything (c) offers rests on this. | (c) collapses to (b). The reskin still stands. | **L3** |
| **3** | **The profession dimension can be widened by patching immediates.** | Refuted in *shape* already: two tables carry profession as an `imul`-strided inner axis, one dispatch is code, two lookups are unrolled onto the stack. (a) is not a patching project, it is a relinking project. | **L2**, then **L5** |
| **4a** | **A profession glyph can be authored and drawn.** | (a) yields an iconless profession. | **Largely answered, and favourably.** Authoring a DXT1 texture the client draws is closed end to end — `studies/texture/FINDINGS.md`, OBSERVED 2026-08-06. What remains is *which widget resolves the glyph*: a search problem. **L2c** |
| **4b** | **Armour composite textures can be authored.** | (a) yields a textureless character. | **Unsolved, and the one place provenance genuinely bites**: needs real per-combination art we can neither derive nor commit. Not the same problem as 4a and must not be bundled with it |
| **5** | **The Vendor jump table's index-11 slot is a genuine twelfth value, not code-folding.** | A mechanical bound patch gets this site wrong in a way that looks like it worked. | `--xrefs` on the function entry; one step, never run |
| **6** | **A patched client is durable across ArenaNet updates.** | (a) becomes per-build maintenance of 29+ signatures in one dense module — worse than the DH re-derivation the runbook already requires. | Re-run the whole census on the 2026-04-30 build; **partly done** — the count reproduces 29/13 with relocated bases |
| **7** | **The client does not validate a skill's owning profession at cast time.** | (b) and (c) both sink: a server could not hand a disguised profession an arbitrary bar. | **Largely answered, and favourably** — see below. Residual: nothing has read the *receive* side of opcodes 228/229/230 for a profession check |

**Assumption 7 was called this document's quiet load-bearing unknown, and it is mostly
answered — in a study nobody opened.** `studies/skillcast/FINDINGS.md` §7 reads
`ChCliApiUseSkill` at `0x00816660` end to end and enumerates the client's complete pre-send
gate, in order: an assert that the hotkey index is in range at its head; bail if
`skillId == 0`; bail if the skill is recharging; read the skill's constant row via
`s_skill[]`'s accessor at `0x005A88B0` and branch on the **type** at row `+0x0C`, with
types 0 and `0x11` bailing; then `call 0x00822B80`; then send.

**Profession is not among the gates. Neither is attribute, nor ownership.** And the
negative is stronger than a global one: `profession` appears **zero times in all 1,533
lines** of a study whose entire subject is the cast path (MEASURED — re-run this pass).

That converts assumption 7 from an unbounded unknown into a narrow one. It does **not**
close it: §7 covers the *send* path, and nothing has read the receive side of 228/229/230
for a profession check. But "the client refuses to cast a skill its profession does not
own" is now the less likely reading, and the cheap half of this document stands up better
than the earlier draft implied.

---

## 10. The ladder

Cheapest first, dependency-ordered. Each states its **question**, its **prediction**, and
**what to watch**, before its method — a probe with no stated expectation can be
rationalised into agreeing with anything afterwards.

Every launch rung inherits the house rules and they are written into the rung, not left
to prose: ours-DH build, verified cage, loopback only, `cage.assert_launch_safe`, named
account, archive writes only ever against a **copy** — never `vault/dat_study/Gw.dat`,
never `C:\gw`.

---

**L0 — Prerequisite, not an experiment. Free.**
`toolkit/authsrv/agents.py`'s `CHAR_PROFESSIONS_MAX = 6` refuses every value above 6 and
is **not** the client's constant. It blocks L3 and L4 outright. Rename it to what it is
(an observed-corpus floor), and make the bound a parameter the probes can raise. One
commit, plus the test line.

---

**L1 — Does an assert end the session? ✅ RUN AND RESOLVED, 2026-08-12. Five minutes,
offline, no launch.** Kept in the ladder with its prediction intact, because the
prediction was stated before the method and it is the reason the result can be trusted.

> **Question.** Does `0x00488210` return to its caller?
>
> **Prediction (stated first).** It does **not** return on a normal desktop configuration.
> Standing on: `0x00487BC0` appears to return (`ret 4` at `0x00487C26`), so the question
> devolves onto its callee; `0x00488210` allocates ~512 KB and formats a report; and
> `CLAUDE.md` records the OBSERVED outcome — process alive, message pump stopped, socket
> open. If instead it returns, then an out-of-range profession renders wrong rather than
> ending the session, and the entire pessimistic reading of §3 weakens at once.
>
> **What to watch.** The branch on the global at `0x00BEC120` — an "is a debugger/console
> attached" gate would explain a routine that both reports and returns. Follow to the
> first `ExitProcess`/`TerminateProcess`/`abort` import or to a `ret`.
>
> **Result: the prediction held, and the `ret 4` was a red herring.** `0x00487BC0`'s only
> branch selects between the caller's expression pointer and a default at `0x009409FC`;
> **both arms converge** at `0x00487C01` and fall into `call 0x00488210` at `0x00487C11`,
> so that `ret 4` is unreachable epilogue. `0x00488210` has **zero `ret` instructions** in
> `0x00488210`–`0x004884CC`; its last instruction is `call 0x005BC094` at `0x004884C8`,
> `int3` padding starts at `0x004884CD`, and `0x005BC094` is a `(arg, 2, 0)` wrapper onto
> `0x005BBF04`, which installs an SEH frame and runs the MSVC CRT terminator chain.
> The `0x00BEC120` branch is not a return path. **Noreturn.** Run twice, independently.

**Consequence for the rest of the ladder:** every launch rung below now has the same
failure signature — a live process behind a dead message pump — so rungs must be ordered so
that a failure is *attributable*, and L5 in particular must not run before L2 and L2b.

---

**L2 — The patch-surface census. Offline, an afternoon.**

> **Question.** How many distinct instructions read each of the eight profession-keyed
> tables?
>
> **Prediction.** The name-id table has readers in the tens (the attribute-name accessor's
> **22 callers** is the base rate to compare against), and the two 2-D colour tables have
> few. If **any** single table has readers in the tens, "patch every site" is not a plan
> and (a) should be closed.
>
> **What to watch.** `codescan.py --xrefs` on each base, plus its own documented blindness
> to computed/indirect addressing — a low count here is a floor, so a **low** number proves
> nothing and only a **high** number is decisive.

**Bundle with it, at no extra cost:** `--xrefs` on the Vendor jump-table function entry, to
settle assumption 5.

---

**L2b — Is the profession picker data-driven or hand-placed? Offline, bundle with L2.**

> **Question.** Is the character-creation profession picker a loop over a table with a
> count, or hand-placed controls?
>
> **Prediction.** **Hand-placed, or table-driven over a compile-time-sized table** — i.e.
> not the runtime-`valueCount` shape the generic picker uses. Standing on `CrContext.cpp`
> bounding an appearance property against `CHAR_APPEARANCES` at `0x004DA514` and then
> asserting at `0x004DA525`/`0x004DA536`/`0x004DA551` that the property is **not**
> profession, sex or race — three properties deliberately routed around the generic
> `CrAppearancePick` path, which bounds against a runtime `valueCount` at `0x004DB536`.
> The contrary evidence is the sibling *chapter* picker, which **is** loop-driven (§7). If
> the profession picker turns out to be loop-driven over a runtime count, **(a)'s UI layer
> is a data edit rather than a code edit** and §11's cost for (a) drops materially.
>
> **What to watch.** `codescan.py --dis` across `0x004D8750`–`0x004D9500` (~3 KB), plus
> `--xrefs` on `s_charProfession` (`0x00A38794`) restricted to that range. Watch for a
> back-edge with a compile-time trip count (the chapter picker's `cmp edi,3 / jb` shape)
> versus a load of a count from memory.

**Why this rung exists at all:** *not one* of the 29 `CHAR_PROFESSIONS` sites is in the
`CharCreate` directory, and `CrProfession.cpp` carries exactly one assert — at
`0x004D8D94`, and not a bound check. Nobody in this pass opened the module named for the
subject of the question. Until this runs, any prediction about what the creation screen
does after a bound patch is a prediction about the wrong module.

---

**L2c — Is profession identity id-resolved, like skill identity? One caged loopback
launch, zero authoring, zero archive writes. The cheapest probe in this document.**

> **Question.** Which surfaces resolve a profession's name and glyph through the PE table's
> string ids — and is the glyph archive-resolved like the skillbar, or a compiled-in image
> list like the Vendor control?
>
> **Prediction.** **The name changes everywhere; the glyph does not change anywhere.**
> Standing on: the 11 name and abbreviation string ids all resolve to real text records
> (MEASURED, §3), so re-pointing one at another existing id should change every label drawn
> from it — while the only profession-aware icon widget located drives icons from static
> image lists, so the glyph is predicted **not** to follow. If the glyph *does* follow, the
> profession icon is id-resolved, `studies/texture/FINDINGS.md`'s authored-DXT1 pipeline
> applies directly, and §13's biggest open question closes in one run.
>
> **What to watch.** Which surfaces change and which do not: character-select list, hero
> panel, party window, nameplate, tooltip. The *split* is the measurement — a widget that
> does not follow the id is a widget with its own hard-coded source.
>
> **Control.** A second profession left untouched in the same session. Without it, "nothing
> changed" cannot be told apart from "the patch did not take".

**Method is an existing, tested precedent, not new capability.**
`toolkit/clientpatch/repoint_skill.py` does exactly this shape for skills — its own
docstring calls it *"the only one that needs no archive write, no injected DLL and no new
content: every value we write already exists in the client, so the client can definitely
resolve it."* The profession analogue re-points `s_charProfession[n]`'s name id at a
different **existing** id. Same reasoning, same safety properties, and it needs neither L1
nor L2.

Needs L0 only. **Rank this ahead of L3** — it is the cheapest thing in the document that
can move a NOT FOUND.

---

**L3 — The reserved attribute probe. One caged loopback launch. The cheapest thing that
could refute the encouraging half.**

> **Question.** Does the client accept a rank in attribute id **45** — a slot its own table
> declares, bound-checks and points at an empty text record?
>
> **Prediction.** It is accepted with no assert, because 45 < 51 satisfies every bound
> measured (the definition table's four accessors, both `ChCliAttrib` runtime sites, and the
> pointer array at `0x00C0EEC0`), and the attribute panel renders a row with **blank** name
> and description — because the string ids resolve to empty records, MEASURED. Anything
> else is informative: an assert refutes "the reserved slots are structurally usable"; a
> silently-dropped row says the panel filters on something we have not found.
>
> **What to watch.** `test_harness.py`'s crash-dialog capture (the **only** machine-readable
> evidence a client assert leaves — `Gw.log` does not record asserts and a
> `ConnectionResetError` appears on clean teardown too); the attribute panel; the gamesrv
> log showing the probe's own steps before believing any of it.
>
> **Control.** The same probe against a **real** attribute id of the character's own
> profession must render normally in the same session. A probe whose positive arm is not
> paired with a working control cannot distinguish "the reserved slot failed" from "our
> `0x003A` is wrong".

Needs L0. Does not need L1, L2, or any client patch.

---

**L4 — The profession-11 probe. One caged loopback launch.**

> **Question.** What happens when the client is told an agent's primary profession is 11?
>
> **Prediction.** The byte is **stored without complaint** — the setter at `0x007F7330` has
> no comparison in its body, MEASURED — and then the **first** UI path that indexes a
> profession-keyed table ends the session behind a modal dialog. Under L1's prediction that
> is a session-ender, not a rendering artifact.
>
> **What to watch.** *Which* action triggers it. That names the first table to patch and
> gives an ordering for §3's list. Do three ordinary things in a fixed order and record
> which one is last: open the party window, open the attribute panel, let a nearby agent's
> nameplate render.
>
> **Control.** A quiet window before the first send, to measure what the client says
> unprompted in this session — the smsgsweep pass's own hard-won lesson.

Needs L0. **If the client renders a profession-11 character and survives all three
actions, this document's central reading is wrong and §3 needs rewriting.** That is the
refutation this ladder exists to make cheap.

---

**L5 — The mechanical bound patch. One caged loopback launch, on an ours-DH build.**

> **Question.** Does patching the `0x0B` immediates to `0x0C`, with no table or asset change
> at all, reach the character-creation profession-select screen?
>
> **Prediction.** **No** — and it should fail *before* that screen renders, because at least
> two backing tables are re-strided rather than appended and every array's index-11 read
> lands in adjacent unrelated data. A clean failure here refutes "the count is just a
> compile-time constant to bump" for zero asset-authoring investment.
>
> **The prediction names the wrong module, and that is now known.** None of the 29 sites is
> in `CharCreate`, so a failure "before the screen renders" will come from whichever of
> `ConstChar`/`ConstCostume`/`CpsTex`/… is touched first — **not** from the picker. Rewrite
> this rung's prediction against L2b's answer before running it, or its failure will be
> uninterpretable in exactly the way it was designed to avoid.
>
> **Derive the patch set at run time**, from `asserts.py --grep CHAR_PROFESSIONS` — never
> from a transcribed list, including §3's. The earlier draft's list was inconsistently
> anchored (some entries the `cmp`, some the assert VA, several neither) and patching it as
> written would have written the wrong bytes.
>
> **What to watch.** Whether it fails at all, and **where**. If it renders, the next-cheapest
> follow-up is a single dummy 12th row in the **smallest** append-shaped table
> (`s_profChapter`, 44 bytes) — whose very next bytes are a string another assert depends
> on, which is the fastest way to learn whether "no spare row" is fatal or merely
> inconvenient.

Needs L2 **and L2b**. **Do not run before them** — L1 is settled and its answer makes this
rung's failure mode indistinguishable from every other assert (live process, dead message
pump), so attribution has to come from the static side first. L2 may close (a) outright for
the price of an afternoon, which would make this rung unnecessary rather than merely
premature.

---

**L6 — (c), delivered.** Fill one of the nine reserved attribute slots' empty text records
via `datwrite.py` against an **archive copy**, re-point a reserved row's profession field
at an existing profession, and serve a bar whose skills scale on it.

> **Prediction.** The attribute panel shows an authored attribute name under an existing
> profession, and the server's scaling is honoured because the client never computes it
> (MEASURED: the points-pool writer copies its parameter with no formula).
>
> **What to watch.** `datcheck.py` pre-flight and post-flight, and the archive diff — the
> client's free map is rederived from the entry table at every open, so a write-back can
> move rows nobody wrote (see `studies/customarea/FINDINGS.md` §18).

Needs L3 green. This is the deliverable §2 calls reachable.

---

## 11. Cost, plainly

- **(b) A reskin: zero.** Available today, needs nothing in this document. `studies/skills/FINDINGS.md` §5.
- **L1: done, five minutes.** It did not invert the tone of §3 — it hardened it.
- **L0, L2, L2b: two afternoons, offline, no launch.** L2b is the one that can still move
  (a)'s cost in either direction.
- **L2c: one caged session, zero authoring.** Cheapest thing here that can close a NOT FOUND.
- **L3–L4: two caged sessions.** Highest information per hour once L0 lands.
- **(c) A new attribute set under an existing profession (L6): days to two weeks**, mostly
  experiments, and it inherits the whole `Gw.dat` durability question — which
  `studies/datwrite/FINDINGS.md` names as *the* decisive unknown there, unanswered. Note
  that the texture half of (c) is **not** an unknown: `studies/texture/FINDINGS.md` closed
  it on 2026-08-06.
- **(a) A real eleventh profession: not costed, and deliberately so.** The estimate would
  be dishonest. Two tables need re-striding rather than appending, at least one dispatch
  needs code insertion, two lookups are unrolled onto the stack with no table to grow, the
  armour composite gate needs per-combination art we can neither derive nor commit, and the
  profession glyph's *consumer* was never located. **Each is an unknown-length subproject.**
  An earlier draft said three of them have no known route at all; the corrected count is
  **one** — the armour composites. The glyph has a proven authoring pipeline and an
  unlocated consumer, which is a search, and L2b may yet turn the picker into a data edit.
  A number here would still be a guess dressed as a plan, but the tail is shorter than that
  draft implied.
- **Maintenance:** the DH parameters rotate with every client build, so an ArenaNet update
  already means redoing the patch setup. (a) would add 29+ signatures to re-derive, several
  in one dense module where a recompile is most likely to reorder or inline them.
  Signature-anchored patching does not shrink that burden; it multiplies it.

---

## 12. Corrections ledger

Recorded rather than overwritten, per house style.

### A. Refuted by the verifiers

**A1 — The Vendor control is not a character-creation control.** T1 and T5 both labelled
the 12-slot jump table at `0x005A5EB8` as a character-creation profession button. Its
source module sits under the client's **Vendor** UI namespace; the real character-creation
state machine is a different module in a different directory (MEASURED via `asserts.py --at`).
The byte-level findings stand; the screen does not. Its actual caller was never traced.

**A2 — "The code that reads `s_attrib` was not located."** T3 filed this as a blocker and
a NOT FOUND on the strength of an `--xrefs` scan that returned zero. The scan used a VA one
20-byte record short of the table's real address — a file-offset→VA slip. Re-running the
same tool at the corrected address finds a direct, bound-checked reference immediately,
plus four sibling accessors, one with 22 callers. **This is live, exercised code**, not the
indirect access pattern the tool is documented to miss. *(And the corrected address was
itself still wrong — see C1.)*

**A3 — "No dat-writing tool exists anywhere in this project's evidence base."** T4 carried
this as blocker #4, restating a sentence from `studies/skills/FINDINGS.md` §5 that was true
when written. `toolkit/mapdata/datwrite.py`, `datplan.py` and `datcheck.py` all exist in
this tree, are named in `CLAUDE.md`'s suite, and `studies/datwrite/FINDINGS.md` — **1,836
lines, linked from the very document T4's method says it read in full** — exists to falsify
exactly that sentence. Its real conclusion is more textured and more useful: text needs no
append (678 empty ids), the archive is writable with every checksum measured, and **the
icon is the genuinely unsolved piece**.

**A4 — A fabricated citation.** T6 reported GWLP-R's JPA method as `createProfession`.
No such symbol exists anywhere in the vault; the method is `create`. The NOT-FOUND
conclusion it supported survives an independent per-repo re-sweep; the supporting detail
did not.

**A5 — A disassembly citation that decodes to nothing.** T6 cited `--dis 0x0091cdb0` for a
bound check. That address is mid-instruction and the tool silently returns zero lines. The
underlying bytes are real and reachable from `0x0091cdd0`.

### B. Weakened

**B1 — "`0x00B7` is sent once per instance load, 8 instances."** The correction (it
appears in real traffic at all, overturning a stale NOT FOUND) is real. The count is not:
**29 raw instances across 11 connections**, with two connections firing it **seven times
each** for one agent, the byte progressing over 2–3 seconds. The "8" appears to be an
undisclosed dedup by (session, agent), and it silently excludes the 21 messages that
behave differently from the claim. `0x00B6` likewise is **11** instances, not 8 — all
still zero, so that claim is stronger than stated.

**B2 — The corpus denominator.** "21,543 GAME_SMSG" does not reproduce; an identical
re-run over the same six directories gives **22,524** — exactly this repo's own pinned
figure in `CLAUDE.md`. A five-second grep would have caught it. None of the profession
counts are affected.

**B3 — ">13 profession-keyed 11-entry arrays, all zero-padded."** The zero-padding
adjacency was measured for **five** static tables, not thirteen. The "13" is T1's count of
*source files carrying a bound check* — a different count of a different thing — and at
least one of those files' sites is a compiler-unrolled stack lookup where the "no spare
row" framing does not apply at all.

**B4 — The skill-opcode wire claim.** "No skill metadata has a place to ride on the wire"
is a fact about `schema/messages.json`, which was imported from OpenTyria. Only **3 of 34**
opcodes are wire-validated against this build, and the source study flags CMSG shapes as
weakly evidenced. MEASURED for the schema; **INFERRED** for the wire.

**B5 — "29 or ~28 CHAR_PROFESSIONS sites."** The raw census is **55 sites / 20 files** for
the word and **29 / 13** for the exact symbol; several claims mixed the two denominators.
Both reproduce exactly. And a twelfth site whose assert text does *not* spell the symbol
was independently confirmed to share the identical compiled bound — so the gate is more
pervasive than the symbol census shows, not less.

**B6 — Numeric and citation slips worth carrying.** `make_custom_client.py`'s flag patches
are 3 and 7 bytes, not "4-byte flag flips"; the assert-census shortfall is **370**, not 373
(20,131 sweep vs 19,758 read + 3 named unreadable); `skilltable.py`'s table offset 5,799,632
is `0x587ED0`, not `0x587510`; the register in one disassembly citation was `eax`, not `edx`;
`GmDefaultArmors.h` declares **44** arrays (32 is the sum of four dispatch slices' profession
counts, a different quantity).

### C. Found during synthesis, missed by both surveyor and verifier

**C1 — The attribute table's base is eight bytes lower than either reader used, and that
one error produced a false negative both of them agreed on.**

T3 located the table structurally at file offset `0x634748` and read 50 rows. Its verifier
re-dumped the same bytes, agreed on 50, and explicitly flagged the 50-vs-51 gap as
unexplained and needing resolution before either number is trusted.

Neither read the accessors. The four single-field accessors at `0x005A9290`, `0x005A92C0`,
`0x005A92F0` and `0x005A9320` read bases `0x00A35740`, `0x00A35748`, `0x00A3574C` and
`0x00A35750` — record offsets +0x00, +0x08, +0x0C and +0x10 of a 20-byte record. **The
table base is `0x00A35740`** (file `0x634740`), and `0x00A35748` is the *name-field*
accessor's base. Both readers took a field offset for the table base.

**MEASURED at the corrected base**, this pass:
- **51 records**, ids **0..50**, `id == row index` in **51 of 51**, ending at
  `0x00A35B3C` — exactly where the adjacent source-path string begins, **zero padding**.
  The 50-vs-51 disagreement dissolves: the missing row was row 0, sitting before their base.
- **Attribute id 0 is present**, profession 5, and profession 5 now owns **four** ids
  (0,1,2,3) instead of three — resolving T3-C9's CONTESTED verdict and the "Mesmer is one
  short" discrepancy in one step.
- **T3-C4's arithmetic was right and its verifier's "correction" was wrong.** 42 real ids
  + 9 sentinel = 51 exactly. The verifier changed it to 41 + 9 = 50 because id 0 was
  invisible at the wrong base.

**Why the error survived so well, and this is the instructive part.** The misalignment
paired record *i*'s `(name, desc, flag)` with record *i+1*'s `(profession, id)`. Because
*both* members of the second pair came from the *same* wrong record, the entire
profession→attribute-id mapping came out **correct** — matching the independently-measured
skill table id-for-id, including both discontinuities. That agreement is what made the
read look airtight. The nine sentinel ids came out correct for the same reason. **Only the
flag was shifted**, and the flag was the one field whose meaning was being tested.

**C2 — The refuted "primary attribute" flag is the primary attribute flag.**
Direct consequence of C1. T3-C7 reported the +0x10 field as *not* a primary-attribute
marker, citing Elementalist and Assassin blocks with zero flagged rows and a Warrior block
with two. Its verifier CONFIRMED that refutation by reproducing the same misaligned read —
two agents, same bytes, same wrong base, same wrong conclusion.

At the corrected base the field marks **exactly one attribute per profession and zero in
the nine-row sentinel block**: ids `{0,6,12,16,17,23,35,36,40,44}` for professions
`{5,4,6,3,1,2,7,8,9,10}`. Ten flagged rows in 51 (MEASURED). That set is **exactly** the
set GWLP-R's database marks `(Primary)`, id for id and profession for profession — an
independent 2013 lineage — and the Warrior's flagged id, 17, is the one
`studies/skills/FINDINGS.md` already ties to the Warrior's primary through the client's own
unlock panel (OBSERVED).

A negative result that survived both a survey and an adversarial verification, reversed by
reading the accessors instead of scanning for the table.

**C3 — Every track filed "what does an assert actually do" as unresolved, and this repo
already answers it.** All six surveys and all six verifications hedged on whether an
out-of-range value crashes, blocks, or continues; one verifier disassembled `0x00487BC0`
and gave up following its callee. Two facts already in hand settle it well enough to act
on: `asserts.py`'s own header reports **one distinct callee across all 19,758 sites**
(so the behaviour is uniform), and `CLAUDE.md` records the OBSERVED behaviour from the
smsgsweep pass — *the process stays alive behind a modal dialog with its message pump
stopped and its socket open*, measured at a 31-second gap between the client going silent
and the socket resetting. So "the code falls through and uses the index" is true and
misleading: **the session is over.** **L1 has since run and hardened this from
OBSERVED-elsewhere to MEASURED-in-the-binary — see §12-E1.** Worth noting what the
synthesis got wrong here even while getting the conclusion right: it wrote that
`0x00487BC0` *provably returns*, citing the `ret 4` at `0x00487C26`. That instruction is
unreachable. The right answer was reached through a wrong intermediate step, which is
exactly the kind of thing an unrun experiment leaves standing.

**C4 — Facts left in hand.** `s_profChapter`'s contents `[0,0,0,0,0,0,0,2,2,3,3]` were
measured by two tracks and by `schema/overrides.json` before either, and would have made
"a new profession needs a campaign tag" a measured fact rather than an assertion by array
name. The `arrsize`-based grep that recovers every table's real source symbol name was
implied by three tracks' citations and run by none of the surveyors. Two profession-keyed
colour tables sat inside one survey's own already-printed grep output, unreported.

### E. Found by the completeness critic after synthesis, and re-verified by the orchestrator

A seventh reader was asked only *what is missing* — not to re-check claims. It moved the
answer more than any single track did, and three of its five findings are corrections to
this document rather than gaps in it. Every one below was independently re-run before being
folded in; none was taken on the critic's word.

**E1 — The assert reporter is noreturn, and the document's own top-ranked risk was five
minutes of work.** §9's assumption 1 was ranked the most damaging thing that could be
wrong, and §1 called settling it the highest information-per-hour item available. It was
neither expensive nor open: see §1 and L1 for the measurement. **Re-verified independently
by the orchestrator** — zero `ret` in `0x00488210`–`0x004884CC`, final instruction
`call 0x005BC094` at `0x004884C8`, `int3` at `0x004884CD`, next function at `0x004884D0`.
The lesson is not that the tracks were lazy; it is that **six agents each filed the same
question as "belongs to somebody else's scope"**, and nobody's scope contained it.

**E2 — `studies/texture/FINDINGS.md` exists, is 296 lines, and refutes this document's art
blocker outright.** The doc committed its own §12-A3 error a second time — carrying a stale
sentence forward from `studies/datwrite/FINDINGS.md` without opening the study that
supersedes it. Corrected in §7 and §9-4a. This is now **three** stale-citation corrections
in one pass (A3, E2, and E4 below), all the same failure: a study document quoted from
memory of another study document rather than re-read.

**E3 — Nobody opened `CrProfession.cpp`**, the module named for the subject of the
question, and none of the 29 bound-check sites is in the `CharCreate` directory at all.
Folded into §1 and L2b. The corroborating structure the critic found — `CrContext.cpp`
excluding profession, sex and race from the generic data-driven appearance picker — **cuts
toward this document's pessimism**, and is reported here rather than buried for that reason.

**E4 — `studies/skillcast/FINDINGS.md` largely answers assumption 7**, the stated
load-bearing unknown behind the *cheap* half of the document. Folded into §9. Re-verified:
`profession` appears zero times in its 1,533 lines.

**E5 — §3's address list was not the 29 sites.** Inconsistently anchored and incomplete,
while L5 was specified against it. Regenerated from the tool in §3; L5 now derives its patch
set at run time. Had L5 been run as originally written it would have patched the wrong bytes
and — given E1 — produced a failure indistinguishable from every other assert.

**And the one the critic got wrong, kept because it is the same class of error the whole
document is about.** It reported a provenance violation at `studies/texture/FINDINGS.md`
line ~30 — a verbatim assert expression beside its source path and line, which `CLAUDE.md`
still refuses. **That file contains zero such occurrences** (re-run this pass). The
underlying concern is real and *larger* than reported: **73 occurrences across 17 other
study files**, of which some are bare paths (permitted) and some pair expression text with
path and line (refused). `studies/texture/FINDINGS.md` is simply not among them. A confident
citation of the wrong file, in a finding about citing the wrong file — logged, and handed to
its own pass rather than fixed here.

### D. Corrections this document owes upstream files

- **GWCA** (`Include/GWCA/GameEntities/Attribute.h`, MIT) names the attribute record's
  fifth field `is_pve`. Against the bytes it reads as the **primary-attribute** marker:
  exactly one row per profession, zero in the reserved block, matching GWLP-R's `(Primary)`
  set exactly. No row that would plausibly be PvE carries it.
  **Carried as CONTESTED-resolved, not as a correction owed upstream** — and the
  distinction is deliberate. Our measurement establishes the field's *distribution*; its
  *meaning* still rests on matching one third-party label (GWLP-R's `(Primary)`) against
  another (GWCA's `is_pve`). GWLP-R is genuinely outside the ldufr/GWCA lineage, so the
  match is real corroboration — but issuing a correction against one third-party label on
  the strength of a single other third-party database overstates what we hold. What is
  MEASURED: ten flagged rows in 51, one per profession, none reserved. What is INFERRED:
  that "primary attribute" is what the flag *means*. The Warrior's flagged id 17 matching
  this repo's own OBSERVED unlock-panel read is the one strand that is ours.
- **`studies/skills/FINDINGS.md`** §1 imported that struct from GWCA's scan pattern and
  carried the wrong field name with it. Its `count hardcoded 0x33 (51)` is **MEASURED
  correct** and can be relabelled from CLIENT-DATA. Its §5 line *"no dat writer exists
  anywhere"* is superseded by `studies/datwrite/FINDINGS.md`; its §5 estimate for a new
  skill id (grow the table, update the count at row 0 +0x2c) is superseded by that study's
  **nine relocated absolute addresses across three base constants**.
- **`studies/character/FINDINGS.md`** §b's *"NOT FOUND: no capture holds a `0x00B7` payload
  from anyone"* is superseded — 29 instances across 11 connections in
  `vault/captures/live/`, a corpus that postdates that finding. Its open item citing
  OpenTyria's `unlocked_professions = 1 << primary_profession` should record that all 11
  real `0x00B6` samples are zero.
- **`toolkit/authsrv/agents.py`** — `CHAR_PROFESSIONS_MAX = 6` is an observed-corpus floor,
  not the client's constant (which is 11), and the two names differ by four characters while
  describing different things. It also silently blocks every profession experiment in §10.
- **`schema/overrides.json`**'s `0x0060` entry records a passed refutable prediction —
  *the client chooses the profession and the server echoes it* — that answers the
  "who decides" question directly and is not surfaced in any study's headline.

---

## 13. Open questions and NOT FOUND

These are results.

| Question | Status | What would answer it |
|---|---|---|
| ~~Does the assert reporter at `0x00488210` return?~~ | **CLOSED, 2026-08-12: no.** Noreturn, into the CRT terminator chain | Was L1. Ran in five minutes; §1, §12-E1 |
| Is the character-creation profession picker loop-driven or hand-placed? What is `CrProfession.cpp`'s construction shape? | **NOT FOUND — nobody opened the module** | **L2b**, offline. Decides whether (a)'s UI layer is a data edit or a code edit |
| Which system renders the profession glyph (party window, hero panel, nameplate)? Is it archive-resolved like skill icons, or a compiled-in image list? | **NOT FOUND — but this is a search, not a format problem** | **L2c**, one caged run, zero authoring. Looked in the generic icon module's 8 readable asserts (no profession bound) and in the Vendor control (a hard-coded switch over three static image lists); neither is the nameplate. Note the *format* half is closed — `studies/texture/FINDINGS.md`, OBSERVED |
| Is the Vendor jump table's index-11 slot a real twelfth value or compiler code-folding? | **CONTESTED** | `--xrefs` on the function entry; one step, never run |
| Does the client validate a skill's owning profession **at cast time**? | **NOT FOUND** — only template-decode-time validation located, and that in a reimplementation | The load-bearing unknown behind the cheap half. Belongs to the skills arc |
| What do chapter ids 0/2/3 name, and what is id 1, which no profession maps to? | **NOT FOUND** | No label read from the binary; the 6/2/2 split matching three campaigns is a count-match inference |
| What is the second `s_charProfession`-named array at `0x00A38868` for? Its ids 9/10 are **31556 and 34524** — the only pair in any of the four tables not adjacent | **NOT FOUND** | Both resolve correctly, so it is not a decode error. Purpose unknown |
| What is the 51-entry runtime pointer array at `0x00C0EEC0`, bound-checked identically to `s_attrib`? | **NOT FOUND** | Found this pass, uncharacterised |
| Is the four-axis composite gate one 11×6×8×2 array or four independent tables? | **NOT FOUND** | Trace into `0x00777F10`'s callees |
| The per-rank attribute point-cost curve | **NOT FOUND** | Four encodings searched (u8, u16 LE, u32 LE, cumulative), zero hits. Likely procedural |
| Are the 5 agents carrying `0x0056` byte-1 == 11 NPC-kind? | **Open** | A cross-connection agent-kind join; per-connection scripts cannot see creates from earlier chained tapes |
| Do the reserved attribute ids and the primary flag hold on the 2026-04-30 build? | **Open** | One re-run. If the reserved set moves between builds, (c) is per-build, not permanent |
| Is `s_attrib` write-safe — does anything else in the image reference the reserved rows? | **Open** | `--xrefs` on `0x00A35740`+*n*·20; needed before L6 touches a profession field |
| Real-traffic profession values 7–10 on any opcode | **NOT FOUND** | All six live captures are early-Prophecies. A Factions/Nightfall capture would close it |
| A post-creation "change secondary profession" C→S opcode | **NOT FOUND** | Corpus never captures a visit to the NPC. Absence in what we hold, not proof of none |
| Whether any *other* profession-indexed jump table has a null or unmapped slot | **NOT FOUND** | One table read exhaustively; the 10.5 MB image was not swept for this shape |

---

## 14. How much to trust these sources

| Knowledge | Independent witnesses | Notes |
|---|---|---|
| `CHAR_PROFESSIONS = 11`, the bound-check sites, the backing arrays, the attribute table | **ArenaNet's own binary, re-read twice** | The strongest evidence in this document. Every load-bearing number was disassembled or byte-read by two agents independently, and the two builds agree |
| Profession numbering None=0 … Dervish=10 | **1, possibly counted twice** | `studies/character/FINDINGS.md` labels it CORROBORATED across third-party wire sources; this pass read the client's own table. Those third parties may themselves have read this table, in which case it is one witness — not re-checked |
| The attribute record layout | **1 lineage + 1 measurement** | GWCA's scan pattern (MIT) via `studies/skills/FINDINGS.md`; independently re-derived from the accessors this pass. Its field *names* are somebody's labels — one is wrong (§12-D) |
| The primary-attribute set | **2 genuinely independent** | Measured from the flag field; matched against GWLP-R's DB (a 2013 lineage outside ldufr/GWCA); one member cross-checked against the wiki via this repo's own OBSERVED unlock-panel read |
| The profession bound in reimplementations | **effectively 2** | ldufr's OpenTyria + Headquarter are **one author, one witness**. GWLP-R is a second. `gw-preservation` and `sgwlpr` don't validate at all, so they witness nothing about the bound |
| Wire field widths | **1 + ours** | `msgshape.py` reads the client's own format tables — primary. `schema/messages.json` was imported from OpenTyria, so schema-agrees-with-OpenTyria is **one witness counted twice** |
| **Whether anyone has added a profession** | **0** | No attempt, no discussion, no documented failure, in 21 repositories |

The lineage rule binds throughout: `ldufr` (OpenTyria, Headquarter) and `GWCA`
(GregLando113, JaborGW, gwdevhub/GWToolboxpp) **share an author and count as one witness**;
`Fournux/Tyria-Extractor` credits GWToolbox++/GWCA and is not clean-room for client
structures. `studies/skills/FINDINGS.md` §6 has the identity chain.

**A third non-independence, which §8's 21-repo sweep did not apply.** Per
`studies/texture/FINDINGS.md` §7, `Jonathan-Greve/GuildWarsMapBrowser`,
`gwdevhub/GuildWarsMapBrowser`, `gwdevhub/GWToolboxpp` and
`apoguita/Py4GW_Reforged_Native` are **one ATEX lineage**, and `Fournux/Tyria-Extractor`
cites it. Four repositories, one witness. §8's "zero, across all 21 mirrored repositories"
is unaffected — a negative does not weaken when its sources turn out to be fewer than
counted — but any *positive* claim in this document that leans on more than one of those
four is leaning on one source. None currently does.

**ArenaNet's compiled-in asserts are the most valuable source here and they are a floor,
not a census** — the tool prints its own shortfall on every run (19,758 read + 3 named
unreadable against an independent sweep of 20,131). **Every "no assert names X" answer in
this document is a floor**, including the animation and icon negatives in §7.

---

## 15. Licensing

Second gate, separate from provenance. Per `CLAUDE.md`, a derivation register row in
`PLAN.md` §6.1 must land **before** a module takes an algorithm, layout or constant table
from any upstream.

| Repo | Licence | Bearing |
|---|---|---|
| **GWCA** (GregLando113, JaborGW) | MIT | **No register row exists**, and `studies/skills/FINDINGS.md` already leaned on its `AttributeInfo` scan pattern for the attribute layout. That debt predates this pass and should be settled. The layout is now independently MEASURED, which makes the row cheap to write honestly |
| GameRevision **GWLP-R** | BSD-style | **No register row.** Used here **only to verify a value we derived ourselves** — the primary-attribute set — which is the permitted use even for a no-licence repo. Nothing was taken |
| ldufr **OpenTyria** | Unlicense | Registered. Its attribute enum is **refuted** and must not be imported |
| ldufr **Headquarter** | MIT | Registered |
| th0br0 **sgwlpr** | **AGPLv3** — network use triggers source disclosure | No row; nothing taken. Cited only as evidence that it does not validate |
| Fournux **Tyria-Extractor** | MIT | Not clean-room for client structures |
| `gw-preservation/*`, `Py4GW_Reforged` | **No licence — all rights reserved** | Verify-only per `CLAUDE.md`. Cited here **only** for the negative (they don't validate profession), which is the weakest possible use and takes nothing |

**Provenance constraint on anything built from this document.** The nine reserved attribute
slots are reachable precisely because their identity is **ids**, not bytes: an attribute id,
a name string id, a description string id. Commit the ids; resolve the strings at run time
from the owner's own archive; author the *empty* records rather than copying ArenaNet's
filled ones. Same pattern `mapbuild.py` already proves for FINDINGS 14's five mandatory
chunks, and it is what keeps (c) inside the gate while (a) — which needs armour composites
and a glyph — sits outside it.

---

## 16. Reproduce

Everything below is read-only against the pinned build. `--exe` must be passed explicitly:
`asserts.py`'s default is the owner's install at `C:\gw`, and a prior study's stated
provenance was wrong for exactly this reason.

**Resolve the vault with `vaultpath`, never with a relative `vault/...`.** A git worktree
has no vault of its own, so the relative form silently resolves to nothing — and a tool
handed a path that does not exist is a fixture that turns every assertion behind it into a
no-op. The first draft of this section used the relative form and failed from the very
worktree it was written in.

```
EXE="$(python -c "import sys; sys.path.insert(0,'toolkit'); import vaultpath; \
      print(vaultpath.vault_path('client','2026-07-29_221c13772c7a','Gw.exe'))")"
DAT="$(python -c "import sys; sys.path.insert(0,'toolkit'); import vaultpath; \
      print(vaultpath.vault_path('dat_study','Gw.dat'))")"

# The dimension: 29 sites / 13 files, and 55 / 20 for the broader word.
python toolkit/clientscan/asserts.py --exe $EXE --grep CHAR_PROFESSIONS
python toolkit/clientscan/asserts.py --exe $EXE --grep "(?i)profession"

# The real symbol names behind every profession-keyed table — the grep three
# tracks' citations implied and none of them ran.
python toolkit/clientscan/asserts.py --exe $EXE --grep arrsize

# The 2-D colour tables: profession is the INNER axis, stride 11 in an imul.
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x005a8e40 --count 22
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x005a8ee0 --count 24

# The attribute accessors — read these BEFORE scanning for the table.
# The lowest of the four bases is the table base; anything else is a field offset.
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x005A9290 --count 16
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x005A92C0 --count 16
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x005A92F0 --count 16
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x005A9320 --count 16

# The assert routine is NORETURN (L1, resolved). The `ret 4` at 0x00487C26 is
# unreachable: both arms of the je at 0x00487BF0 converge at 0x00487C01 and fall
# into `call 0x00488210` at 0x00487C11. Then 0x00488210 has NO ret at all, and
# ends at `call 0x005BC094` (0x004884C8) -> 0x005BBF04 -> CRT terminator chain.
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x00487bc0 --count 40
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x00488210 --count 220
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x005bc094 --count 12

# The 29 bound-check sites -- ALWAYS derive the set from here, never from a
# transcribed list. §3's earlier list was inconsistently anchored (§12-E5).
python toolkit/clientscan/asserts.py --exe $EXE --grep CHAR_PROFESSIONS

# The character-creation modules -- note NONE of the 29 sites lands here (L2b).
python toolkit/clientscan/asserts.py --exe $EXE --file CrProfession
python toolkit/clientscan/asserts.py --exe $EXE --file CrContext

# The 51 attribute name ids resolve; the nine reserved ones resolve EMPTY.
python toolkit/clientscan/textrec.py --dat "$DAT" \
    2122 2124 2126 71982 100257 100259 100261 100263 100265
```

Three scratch scripts were written for this synthesis and live in the session scratchpad:
a PE section/VA mapper, a 20-byte-stride dump of the attribute table at the corrected base
`0x634740` (the one that produces §5's table and dissolves §12-C1), and the per-profession
flag count that produces §12-C2. They should be preserved to
`vault/research/profession-2026-08-12/` alongside the tracks' own output, per the
customarea precedent — a reproduce section citing a directory that deletes itself is not a
reproduce section.