# Reskin: the cheapest route to a custom profession

Sixth document in the arc, and the one that answers the question the other five were
circling. [`RUNS.md`](RUNS.md) closed the server side by experiment — a custom **primary**
is survivable on `0x00A6`, `0x00B7` kills on arrival, the secondary dropdown is compiled
`0..10`. So the remaining question is entirely client-side, and it is a **costing**
question rather than a discovery one.

Nine agents, five independent reads of the binary, one costing pass, three adversarial
verifiers. **Two verifiers refuted parts of the costing and both refutations changed the
plan** — they are recorded here in place, because the corrections are the most useful
thing in the document.

Labels per the arc's vocabulary. Everything below is on build 38797, pinned pristine.

---

## 1. The answer

> **Do not add a twelfth profession. REPURPOSE a shipped one.** The id stays legal, so
> not one bound check, assert or `0..10` loop can fire — and on every axis that makes a
> profession playable, a reskin delivers exactly what a 12th id would.

**Cost: five dwords for the identity tier — 20 bytes, all same-length, zero code bytes.**
Against ~60 edit sites for a 12th id, including code re-emission.

What you give up is a **slot**, not a **capability**: ten professions instead of eleven,
one of them yours.

---

## 2. The three measurements that decide it

**2.1 — Zero slack, universally (OBSERVED, re-verified by two agents independently).**
Every profession-keyed table is packed flush against the next live datum. `s_profChapter`
at `0x00A384F0` is followed immediately by a source-path string; `s_charProfession` at
`0x00A38794` and the abbrev table at `0x00A387E8` are each followed by their own assert
expression; the picker table at `0x00A38868` by another; `s_scaleBase` at `0x00A96B7C` by
a UTF-16 string. **MSVC packed `.rdata` with no padding, so R-WIDEN can never append** —
every table becomes relocate-plus-repoint, turning each "data" edit into a data edit *and*
a code edit.

**2.2 — Seven of the per-profession tables are CODE, not data.** Function `0x005AA230`
alone materialises four `[3 chapter][2 sex][10 profession]` tables as `mov dword ptr
[ebp-N], imm32` ladders into a 240-byte stack frame, with 36 callers and an 8-way jump
table. Widening the profession axis there means re-emitting the blocks, growing the frame,
and moving every `ebp`-relative displacement in the function. **That is code generation,
not patching**, and no data-only plan can even see it.

**2.3 — The bound census was a floor twice over, and a site proves it.** A fifth
profession table at `0x00BEF4A4` (`.data`, entries 1..10 byte-identical to
`s_charProfession`) is read at `0x004D128E` with **no bound check at all** — no `cmp`
anywhere between the load and the indexed push. Every census in this arc keyed on
`cmp reg, 0x0b`, so this site was invisible to all of them. For R-WIDEN it is a must-fix
nobody counted; for R-NEUTER it is untouchable, because there was never an assert to
neuter; **for R-RESKIN it is a fifth same-length dword and it is free.**

---

## 3. R-NEUTER is an instrument, not a route

The arc has listed "R1, five bytes" as a third option since `WORKAROUNDS.md`. It should
stop. `0x00487C11` is the **global** assert-wrapper call, so one NOP disables every bound
and invariant check in a 10 MB binary — and because the reporter is `noreturn`, neutering
makes the *downstream cascade* fall through too. What the fall-through then reads was
measured, and two values are disqualifying:

| Table | index 11 returns | effect |
|---|---|---|
| `s_scaleBase` | `1.0194e-38` | character model scale collapses to ~zero |
| `s_profChapter` | `0x435C3A50` (the ASCII of the following string) | nonsense chapter into every campaign gate |

The name tables return the bytes `prof` as a string id, and the creation-screen icon comes
from an 11-slot **stack** array whose slot 11 is uninitialised — non-deterministic, not
merely wrong. It buys a session that keeps running and shows an invisible, unnamed,
mis-gated character. **Excellent for learning what reads what; not a route to a usable
profession.**

---

## 4. What a reskin actually gets — the honest scope

**WORKS**, all fixed-width slots, no code:

- **Name, abbreviation, picker label** — four tables holding **string ids, not text**, so
  this fits the repo's own "commit the id, resolve the string at run time" rule and needs
  no ArenaNet text in the tree.
- **Campaign availability** — NEWLY DECODED: the creation filter at `0x004DAE20` does
  `test eax,eax / je accept`, so **chapter 0 means offered in every campaign**. One dword.
  *(But see §5.2 — it is not free.)*
- **Attributes** — which the profession owns, which is **primary**, and their names and
  descriptions. **Nine spare attribute rows** exist (ids 26,27,28,45,46,47,48,49,50,
  currently tagged profession 11 with zero skills). The definition table never needs
  reordering: it is quicksorted at startup and binary-searched by key.
- **Skills** — 1 byte per skill row. And the attribute panel needs **no new indexing
  code**: its derivation loop branches only on the attribute's own profession field.
- **Model scale, hair palette, skin palette, starter kit, creation icon.**
- **Armour** — by *redirection* to an existing set (ArenaNet already ships row sharing:
  professions 0, 1, 2, 9 are byte-identical). Not authoring new art.

**DOES NOT WORK** — and these walls are identical for a 12th id:

- **Skill names and descriptions.** A profession's identity text lives in **one** archive
  text file; its 122–199 skills draw name ids from **19–22 different** files. Your custom
  profession has whatever skills you assign it, and they keep their shipped names.
- **Skill icons.** 3,292 of 3,439 are DXTL, which has no DirectX equivalent, and
  skill-icon rows never ship stored — so the compression escape hatch does not exist.
- **Animations.** A different, larger bound; uncosted.
- **The in-game profession glyph.** NOT FOUND — carried unresolved since `FINDINGS.md`.
  A reskin **inherits the host's glyph**, which is an argument *for* it: a wrong-but-present
  glyph beats a missing one.

> **The deliverable's real shape:** a fully playable class with its own name, campaign
> availability, attribute set and primary attribute, skill roster, model scale, palettes,
> starter gear and borrowed armour — whose **skills keep their shipped names and icons**,
> wearing the host profession's glyph. That is a real custom profession for a private
> local server. It is not a from-scratch class with bespoke skill art.

---

## 5. What the verifiers refuted, and it changed the plan

**5.1 — Three Tier-1 addresses were wrong, one landing on the wrong profession.** The
creation-icon record for profession 8 is at `0x0094B470 + 8*7`, **not** `+ 8*8` — the
costing's address is *Paragon's*. The hair and skin palette bases are `0x00A14FB8` and
`0x00A15A78`, each four bytes below what was quoted. And the armour redirect is 4 dwords,
not two 48-byte row copies. *(That icon slot also has a code-side twin in an instruction
immediate, so "zero code bytes" needs a footnote at Tier 1.)*

**5.2 — "Campaign availability is one dword" was over-sold.** `s_profChapter` is also a
bit index into an owned-campaigns mask and the row selector for the player composite.
Writing 0 moves the composite row *and* destroys the fallback that catches exactly that
miss. Worse, **selectable ≠ creatable**: hair, skin and starter-kit entries for profession
8 are **empty** in the other campaigns, so the naive one-dword patch yields a Ritualist
offered in Prophecies with no hair colours, no skin tones and no starter gear — while
clause 4 ("zero asserts") reports green. Split the claim.

**5.3 — The first experiment was untestable as designed, and this is the sharpest catch.**
`s_profChapter[8]` and the picker table are read from **exactly one caller each**, both
inside the character-creation picker — and `studies/divergence` D10 records that **our
server has no creation flow at all**. So the experiment's only genuinely new clause was a
coin toss on an unbuilt path: if Ritualist failed to appear, "we never reached the picker"
explains it completely.

**One thing got upgraded rather than refuted:** the name-table census is now **measured
complete**. Every 4-byte alignment of the image was scanned for all 27 identity string
ids; the rare Factions/Nightfall ids occur exactly twice and once. **There is no fifth
name table.**

---

## 6. The corrected experiment: three runs, control first

**RUN 0 — the control, on a PRISTINE exe, no patch at all.** Set the server's character to
profession **8** and prove it renders as a Ritualist everywhere *before* changing a byte.
Walk every screen the later runs use and record what each says. This establishes which
name consumers our session actually renders — the denominator the completeness clause
needs — and without it runs 1 and 2 are uninterpretable.

**Built for this, 2026-08-13:** `--spawn-profession 8` now drives the **appearance nibble**
too, on both carriers — the `0x0059` dword and the character-select blob, which were
independent constants and disagreed. In-band ids only: the nibble is 4 bits asserted
`< 0xB` at load, so 12 still keeps the legal placeholder. Pinned by four checks.

```
python C:/gd/Rurik/.claude/worktrees/sweet-euler-697883/toolkit/harness/session.py --keep-open --shots 10 --game-args '--probe profession_panel --spawn-profession 8 --map 796'
```

**RUN 0 PASSED, 2026-08-13** (harness `20260813T103437`). `--spawn-profession 8` renders
a Ritualist end to end: `0x0059` carried appearance `0x00800000` (the nibble followed) and
`0x00B7` carried prof 8; no crash dialog, 34 c2s, `missed 0`. **The operator identified it
by the weapon-holding animation**, which is worth more than the confirmation — see §7.

**RUN 1 — the in-world dwords only**, with a **different donor string id per table** (the
original plan collapsed three tables onto one donor and so could not say which table fed
which widget), and never a profession-name id as donor.

**Built 2026-08-13: `toolkit/clientpatch/reskin.py`.** It locates all four name tables
**structurally, never by address** — each `.rdata` table by the assert expression the
compiler emitted immediately after it (each occurring exactly once in the image), then
corroborated by shape, with **the anchor and the shape required to agree**; the `.data`
table by its values against the located name table. It writes **out of place only**, and
refuses `C:\gw`, its own input, and every checkout of this repo. Verified on the pinned
client: the four offsets it derives match the workflow's independently-derived numbers to
the byte.

```
python toolkit/clientpatch/reskin.py --show
python toolkit/clientpatch/reskin.py --profession 8 --name <ID> --abbrev <ID> --out <vault path>
```

**RUN 2 — the `.data` table** `0x00BEF4A4`, whose consumer no document in this arc names.

Character creation is a **separate question**, and one launch settles whether the picker
even renders locally on a server with no creation flow — worth answering before anyone
builds `0x0060`/`0x0084`/`0x008b` handlers.

---

## 7. Open

| Question | Status |
|---|---|
| Does the creation picker render without a server creation flow? | **UNVERIFIED** — one launch, and it gates the whole campaign-availability tier |
| Is `0x00BEF4A4` indexed by profession id? | **INFERRED** — values match `s_charProfession[1..10]`; reached via a vtable slot, so nothing static resolves it |
| Does a static armour row copy survive runtime population? | **UNVERIFIED** — table A's pointers reach past the raw-backed `.data` end at `0x00C02A00` |
| Will the client accept a text file whose row reads compression 0? | **UNVERIFIED** — gates arbitrary authored text; Tier 0 needs no archive write |
| `0x00A79758` — an 11-entry table read with a bound and **no assert**, in the model loader | **PROMOTED to a live lead (§7)** — the animation layer demonstrably reads profession |
| The in-game glyph | **NOT FOUND** |

**Retired by this pass:** the `CpsData` 0x16 stride mystery — it is `2 × 11`, and the
composite lookup is now fully understood.


---

## 7. The animation layer reads profession — and that favours the reskin

**OBSERVED 2026-08-13, run 0.** With `--spawn-profession 8` and no client patch at all,
the operator identified the character as a Ritualist **from the weapon-holding
animation** before reading a single label.

That is a measurement, not a nicety. §4 lists animations under DOES NOT WORK and a
verifier flagged an 11-entry table at `0x00A79758` in the model loader — read with a
bound but **no assert**, index taken from a model-file byte — as *possibly* a
profession→model/shader map, labelled UNVERIFIED because nothing static resolved it.
The animation changing with the profession id is direct evidence that **the animation
layer does read profession**, which promotes that table from a guess to the prime
candidate.

**And it turns a listed weakness into an argument for the route.** A reskin **inherits
the host profession's animations**, so a custom class animates like a Ritualist —
coherent, if not bespoke. A twelfth id would index that table at 11 or 12 instead, and
since it is read with a bound and no assert, the failure would be silent rather than
loud. One more axis on which the legal-id route wins by not being clever.

---

## 8. RUN 1 (2026-08-13): **the reskin works — "Profession: Soul Reaping"**

Harness `20260813T105623`. The first successful profession reskin in this project.

**Donors, picked so a sighting attributes to a table and cannot be confused with a real
profession.** Both are ATTRIBUTE name ids, which belong to no profession, and both were
confirmed to render by direct observation in earlier panel screenshots rather than
assumed:

| table | patched | donor | why this one |
|---|---|---|---|
| `s_charProfession[8]` | 2048 → **2092** | *Soul Reaping* | Necromancer's primary attribute (`s_attrib` row 6, `+0x10 = 1`) |
| `s_charProfessionAbbrev[8]` | 2057 → **2078** | *Fast Casting* | Mesmer's primary (row 0) |

Neither belongs to the Ritualist, so neither can be confused with the host's own attribute
list — which the panel displays a few pixels below.

**The result, from `hold002.png`:**

> **`Profession: Soul Reaping`** — where the client had written *Ritualist*.
>
> And below it, unchanged: **Communing, Restoration Magic, Channeling Magic, Spawning
> Power** — the Ritualist's own four attributes, correct and untouched, because the
> attribute rows were not part of this patch.

**No crash, no assert, run verdict PASS.** Exactly as §1 predicted: the id never left
0..10, so nothing had a bound to check.

### What this settles

1. **`s_charProfession[N]` drives the in-world "Profession:" label.** OBSERVED, by
   changing it and watching the label change.
2. **The reskin route is proven end to end** — locate structurally, patch two dwords out
   of place, launch, read the new name off the screen.
3. **A same-length string-id edit is invisible to the client's own machinery**: the
   attributes, the skill list and the panel all behaved normally around it.

### Method notes worth keeping

- **The patched client must be the ours-DH RUN build**, not the pristine one — a pristine
  client cannot key against our server. `dhbuild.py` was re-run after patching and still
  read **`ours`**: two bytes of string ids leave the DH parameters, the updater kill, the
  mutex NOP and the rename intact.
- **The run client is deliberately read-only** (mode 0555). It was backed up, patched,
  launched, then **restored byte-for-byte** (sha256 compared) with its read-only bit put
  back and the backup deleted. The run directory is exactly as found — it is a shared
  artifact and other sessions launch from it.
- **The harness can open the panel without an operator**: `--walk 'wait:2 K:0.3'` presses
  K, because `parse_walk` accepts any single character as a key. That turns a
  human-in-the-loop probe into an unattended, screenshot-verified run.

### Still open from this run

**The abbreviation donor was not observed.** *Fast Casting* was patched into
`s_charProfessionAbbrev[8]` but the abbreviated form shows in the party window and
nameplate, neither of which renders in a solo session with no party. **UNVERIFIED**, and
one run with a party or a visible nameplate settles it. The picker and `.data` tables are
likewise untested — the picker is character-creation only (§5.3), and the `.data` table's
consumer is still unidentified.


---

## 9. RUN 2 (2026-08-13): the ATTRIBUTE tier — both claims confirmed

Harness `20260813T110552`, unattended (`--walk 'wait:2 K:0.3'` presses K). Four dwords
this time: the profession name again, plus three attribute edits testing two independent
claims about `s_attrib`.

**The table, measured first** (51 rows x 20 B, located by the source-path string that
follows it; `+0x00` owner, `+0x04` attribute id, `+0x08` name id, `+0x0C` desc,
`+0x10` primary):

| profession | attributes |
|---|---|
| 8 (Ritualist) | 32, 33, 34, **36 primary** |
| **11 (reserved)** | **26, 27, 28, 45, 46, 47, 48, 49, 50 — nine SPARE rows** |

**The edits and the prediction, stated before the run:**

| edit | claim under test |
|---|---|
| attr 32 name 2144 -> 2092 | does `+0x08` drive the displayed attribute name? |
| attr 26 owner **11 -> 8** | is the panel's attribute list DERIVED from `+0x00`? |
| attr 26 name 2122 -> 2112 | (so the new row arrives with a word I have seen render) |

> Predicted: **five** attributes instead of four — one renamed, one newly present.

**Observed, `hold002.png`:**

> **Profession: Soul Reaping**
> **Attributes (50 unused points): Strength · Soul Reaping · Restoration Magic ·
> Channeling Magic · Spawning Power**

**Five attributes. Both claims hold.**

1. **`s_attrib +0x08` is the attribute's displayed name.** OBSERVED — *Communing* became
   *Soul Reaping*.
2. **`s_attrib +0x00` decides which profession's list an attribute appears in.** OBSERVED
   — a row parked on the reserved profession 11 moved to 8 and **appeared in the panel**.
   The attribute list is derived from this field, exactly as the costing predicted, and
   needs no per-profession table.
3. **The nine spare rows are usable.** A custom profession is not limited to its host's
   four attributes: there is room for up to nine more.

No crash, verdict PASS, and the run dir was restored byte-for-byte afterwards.

### A harness finding worth keeping

`session.py` already accepts `--exe`, so the obvious way to avoid touching the shared
client is to drop a differently-named patched exe in the run directory (it must live
there to find `Gw.dat`). **That does not work unattended:** the firewall cage is keyed
per executable path, so a new filename is uncaged and `assert_launch_safe` refuses it —
correctly. Caging costs an elevated shell. **So the backup-patch-run-restore cycle on
`Gw.exe` is the only unattended route**, and the uncaged copy was deleted immediately
rather than left in `vault/run`, which is the hazard `isolate_client.ps1`'s own help text
was written about.


---

## 10. RUN 3 (2026-08-13): the SKILL ROSTER — a countable prediction, hit exactly

Harness `20260813T111051` and `20260813T111256`. Six dwords: identity, attributes, and
two skills moved between attributes.

**The design problem, and the fix.** The Skills panel groups by ATTRIBUTE, and with the
full 1,333-skill corpus unlocked the interesting groups sit below the fold — run
`111051` showed the rename working (*Communing* vanished from between *Command* and
*Critical Strikes*, exactly where it had sat) but its counts were unreadable. So the
second run shrank the list to the eight-skill bar with `--unlocks bar`, which makes
every group visible at once and turns the test into arithmetic.

**Edits:** attribute 26 → owned by profession 8, renamed to string 2094; skills **317 and
318** moved from attribute 17 (*Strength*, 4 skills) to attribute 26.

> **Predicted:** *Strength* falls 4 → **2**, a new group appears holding exactly **2**,
> and the total stays 8.

**Observed, `hold002.png`:**

| group | skills |
|---|---|
| **Air Magic** (attribute 26, renamed) | **2** |
| **Strength** (attribute 17) | **2** — was 4 |
| Swordsmanship | 1 |
| Tactics | 2 |
| No Attribute | 1 (*Wild Blow*) |

**Total 8.** Both counts moved by exactly the number of skills moved, in opposite
directions. And the Attributes box lists **Air Magic** beside Soul Reaping, Restoration
Magic, Channeling Magic and Spawning Power — the same row, owned and named.

**`s_skill row+0x29` decides which attribute group a skill belongs to. OBSERVED.**

A count that moves in both directions by the right amount is the strongest shape of
check available here: a codec or a cache that merely *replayed* what it saw would leave
the totals alone.

### The reskin's core is now validated end to end

| Piece | Field | Status |
|---|---|---|
| Profession name | `s_charProfession[N]` | **OBSERVED** (§8) |
| Attribute names | `s_attrib +0x08` | **OBSERVED** (§9) |
| Which attributes a profession owns | `s_attrib +0x00` | **OBSERVED** (§9) |
| Which attribute a skill scales with | `s_skill +0x29` | **OBSERVED** (§10) |
| Nine spare attribute rows available | — | **OBSERVED** (§9) |
| Abbreviation | `s_charProfessionAbbrev[N]` | UNVERIFIED — party/nameplate only |
| Picker label, `.data` table | — | UNVERIFIED — creation screen / unknown consumer |

That is a profession with its own name, its own attributes with their own names, and its
own skills grouped under them — **eleven bytes of same-length edits**, no code, no bound
check touched, no assert neutered.


---

## 11. RUN 4 (2026-08-13): the roster, and the visual identity for free

Harness `20260813T111856` then `20260813T112121`, `--until login` so the run stops on the
character-select screen instead of clicking through it.

**First attempt found a plumbing defect, not a reskin defect.** The roster read
**"Warrior"** for a character that was profession 8 everywhere else. Cause: `--game-args`
reaches the GAMESRV only, by deliberate design — but **the character-select roster is
served on the AUTH channel**, from the character blob. So the authsrv was still on the
default profession. Two answers to one question, which is the same split `appearance_for`
exists to prevent one level down.

Fixed in `session.py`: `--spawn-profession` is now forwarded to the authsrv as well, and
it is the ONLY game flag that is — `--unlocks`, `--probe` and the rest must not reach it,
or the authsrv arms a second idle copy of the same experiment. Five checks pin both
halves, including that the game-channel flags do NOT leak.

**Second attempt, and it delivered more than it was aimed at:**

> The roster reads **`Soul Reaping`** — so the character-select screen reads the same
> `s_charProfession` name table the in-world panel does.
>
> And the character MODEL changed completely: different build, different hair and face,
> and Ritualist starter clothing in place of the Warrior's shorts.

**The appearance nibble carries the whole visual identity.** `RESKIN.md` §4 listed model
scale, hair palette, skin palette and starter kit as four separate Tier-1 edits; setting
the nibble to the host profession delivers all four **for free**, because they are indexed
by the same id. A reskin inherits the host's body — which, with §7's animation finding, is
the second axis where reusing a legal id beats adding a twelfth.

**Still UNVERIFIED: the abbreviation.** The roster shows the full name, so
`s_charProfessionAbbrev` is still unexercised. It renders in the party window and over
nameplates, and our world has neither. Not a blocker — it is one dword, already
patchable, and it will show the moment there is a party.


---

## 12. The recipe: a profession design as a versioned file

`toolkit/clientpatch/recipes/ritualist-demo.toml`, applied with
`reskin.py --recipe FILE`. The command line that produced §§8-11 was eleven flags and
told a reader nothing; the recipe says what the profession IS.

```
python toolkit/clientpatch/reskin.py --recipe toolkit/clientpatch/recipes/ritualist-demo.toml --out <vault path>
```

**Validated end to end** (harness `20260813T112450`): the recipe alone reproduces the
whole result — *Profession: Soul Reaping*, five attributes, and the skill groups at
2 and 2. An explicit `--profession` still overrides the recipe's host, so one design can
be aimed at a different host for a single run without editing the file.

**Everything in a recipe is a NUMBER** — profession, attribute, skill and string ids —
which is what keeps ArenaNet's words out of the tree while the client resolves each
string from the owner's own archive at run time. Eight checks cover it, including that a
row missing its id is REFUSED rather than silently skipped: a design that half-applies
reads as a client bug rather than as a typo.

**The host is Ritualist (8), by the owner's decision, 2026-08-13.** It was also the
cheapest candidate on the evidence: all eleven of its identity string ids live in ONE
archive text file where every other profession's straddle two to four, so it is the
cheapest host to rename once authored text is possible.

---

## 13. Where this stands, and what is left

**REWRITTEN 2026-08-14.** The version this replaces ended "the one real wall left is
TEXT", which was true when written and false eight sections later (section 19). It also
listed the abbreviation as "patched and unexercised" -- it renders (18.14). A standing
list that describes a finished task as the next one is the failure `CLAUDE.md` opens
with, so this section is dated and the runs are named.

### Working, validated in a running client

| | field | run |
|---|---|---|
| Profession name | `s_charProfession[N]` -- **authored** | 19 |
| Abbreviation, on the party roster | `s_charProfessionAbbrev[N]` -- **authored** | 18.14, 19 |
| Attribute names, all five | `s_attrib +0x08` -- **authored** | 9, 19.5 |
| Attribute descriptions, all five | `s_attrib +0x0C` -- **authored** | 20.2 |
| Which attributes the profession owns | `s_attrib +0x00` (nine spare rows to take from) | 9 |
| Which attribute is PRIMARY | `s_attrib +0x10`, moved off the host onto our claimed row | 19.7 |
| Which attribute a skill scales with | `s_skill +0x29` | 10 |
| Model, hair, skin, starter gear | appearance nibble | 11, free |
| Animations | -- | 7, inherited from the host |
| **Inherent primary passive** | **none -- it is SERVER work** | 20 |

Eleven same-length dword edits plus one archive row. No code caves, no injected DLLs, no
grown tables, and every profession id stays inside 0..10 so not one bound check can fire.

### The one wall that is actually left -- CLEARED 2026-08-14, see section 22

**The profession glyph.** ~~Still NOT FOUND, carried unresolved since `FINDINGS.md`.~~
**FOUND** (section 22): one shared 256x128 DDS, file id 152638 / MFT row 12032, 8x4 cells
of 32x32, profession 8 at frames 14/15, selected by the jump table at VA `0x005A5EB8` in
`VnProfessionButton.cpp`. Authoring it is a partial overwrite of one 32x32 region plus a
`datmove`, since the row ships compressed and we write stored.

**There is now no NOT FOUND left in this arc's identity tier.** What remains is unexercised
work, not unknown mechanism.

### CORRECTION 2026-08-14: skill icons were never the second wall

The first version of this rewrite listed skill icons alongside the glyph, on the grounds
that "3,292 of 3,439 are DXTL, a format with no DirectX equivalent, and skill-icon rows
never ship stored". **Both sentences are quotations from
[`../datwrite/FINDINGS.md`](../datwrite/FINDINGS.md) blocker #3, and both were retired on
2026-08-06** by [`../texture/FINDINGS.md`](../texture/FINDINGS.md), which was split out of
that document and opens by saying so: *"the texture layer is open, end to end"*. This
section exists to stop exactly this, and it shipped doing it. The lesson is the one
`CLAUDE.md` states about `PLAN.md` §3 -- a blocker is only current in the document that
owns the arc, and a quotation carries the date of the sentence, not of the paste.

What is actually true, all OBSERVED on a running client:

* The client draws icons **we authored from nothing** -- image, DXT1 encoding, container,
  archive write. `dxt1.pattern_icon` rendered as a sunset on the bar (texture 4b).
* **DXTL is not on the critical path.** The bar reads `+0x90`, which is **DXT1 128x128**;
  DXTL lives at `+0x8c` and is **64x64**. Confirmed again here by decompressing a real
  Ritualist icon and its partner: `ATEX/DXT1/(128,128)` and `ATEX/DXTL/(64,64)`.
* **"Never ship stored" is a fact about what ArenaNet writes, not about what the client
  reads.** Texture 3 arm 0 served a decompressed row *stored* and the client drew it.

### What replaces it is a COSTING question, and it is measured

MEASURED 2026-08-14, offline, against the pinned exe and `vault/dat_study/Gw.dat`:

Counted per ICON rather than per skill, because a write targets a row and 188 skills share
132 of them:

| | |
|---|---|
| Skills on profession 8 (the host) | **188**, every icon id resolving |
| Distinct `+0x90` icons behind them | **132** |
| of those, exclusive to profession 8 | **125** -- the other **7** are also on another profession's skill, so an in-place write changes someone else's bar |
| An authored **128x128** DXT1, one level | 8,212 B -> 8,704 B reservation; **fits in place 16 of 132** |
| An authored **64x64** DXT1, one level | 2,068 B -> 2,560 B reservation; **fits in place 132 of 132** |

The smallest `+0x90` reservation in the whole roster is 6,656 B, which is why the 64x64
row is unanimous rather than merely good.

> **The first version of this table was computed wrongly and the aggregate survived it,
> which is the part worth remembering.** `file_id_table` returns **one-based MFT row
> numbers**; `Archive.entries` is **positional**, `entries[k].index == k + 1`. Indexing
> `entries[row]` therefore measures each row's PREDECESSOR, and `archive.py` says so in
> two docstrings -- `row()`'s opens *"USE THIS WHENEVER YOU HAVE A ROW NUMBER"*. Every
> figure above came out **identical** either way, because skill-icon rows sit in a long
> run of similar sizes and shifting by one does not move the distribution. The per-row
> facts did NOT survive: the run's own arms were re-picked, and two arms had already been
> written into the wrong rows before anything caught it. What caught it was **not** a
> check of ours -- it was `datwrite` refusing the third arm as a relocation, with the
> refusal quoting a reservation that did not match the row it named. An aggregate that is
> robust to an indexing error is not evidence the indexing is right.

The route divided on one unanswered question --
[`../texture/FINDINGS.md`](../texture/FINDINGS.md) §6's *"is the bar's frame inset a fixed
pixel count or a fraction of the texture?"* -- and **it was answered the same day, in the
UV direction, so the roster needs ZERO relocations.** Harness `20260814T002445`: three
in-place `datwrite --replace` arms, five untouched controls, RUN VERDICT PASS with no
assert and no crash dialog. Write-up in
[`../texture/FINDINGS.md`](../texture/FINDINGS.md) §9; the two numbers that carry it:

* A 64x64 and a 128x128 of the **same** picture -- the 64 a box-filtered mipmap of the
  128, so they are the same image by construction rather than by eye -- render at the same
  framing: **15.19/255** mean absolute apart, against **68.9 to 134.6** for the five
  untouched retail icons in the same frame.
* A ruler in slot 3 puts the texture's own inset-20 and inset-10 bands at 0.958 and 0.955
  screen pixels per texel, predicting the second landmark from the first to **0.1 px**.
  The client stretches the whole texture onto a fixed quad; it does not sample a sub-rect.

So `pattern_icon`'s 16-pixel border is a **fraction** (12.5%), not a pixel count, and the
whole roster is authorable with `datwrite --replace` alone -- journalled, byte-for-byte
revertible. **What has NOT been done is the roster**: this run authored three icons, not
132, and nothing in the toolkit yet generates 132 distinct pictures worth looking at. That
is now an art problem rather than a format one, which is a much better place to be stuck.

### 13.1 The roster is drawn, and the client drew it (2026-08-14)

Harness `20260814T051447`. `glyphs.py` draws **132 procedural icons**, `iconset.py`
joins them to the rows profession 8's skills actually point at and arms **125** of them
in place -- the other 7 are icons another profession's skills also use, and are held
back by default. Archive verifies, `datcheck --preflight` **10 of 10**, RUN VERDICT
PASS.

**Eight predictions were written down before the launch and all eight held** -- motif,
palette, polarity and accent, per slot:

| slot | skill | glyph | predicted | OBSERVED |
|---|---|---|---|---|
| 1 | 772 | 11 | starburst, violet, dark-on-lit | as predicted |
| 2 | 773 | 5 | trident, violet, dark-on-lit | as predicted |
| 3 | 787 | 6 | vortex, violet, light-on-deep | as predicted |
| 4 | 788 | 9 | triangle, violet, dark-on-lit | as predicted |
| 5 | 789 | 10 | drop, violet, light-on-deep | as predicted |
| 6 | 790 | 17 | tau, violet, dark-on-lit | as predicted |
| 7 | 791 | 42 | funnel, **galecraft blue**, dark-on-lit | as predicted |
| 8 | 792 | 71 | trident, **stormcall magenta**, light-on-deep, **dot-triad accent** | as predicted |

Slots 2 and 8 are the same motif in different palettes with different polarity and a
different accent frame, which is the case the whole index design exists for -- and it is
the case that was BROKEN twice before it worked (13's own note, and `test_glyphs.py`).

**So the icon tier is closed.** A custom profession can now carry a name, an
abbreviation, five attribute names, five descriptions, a primary marker and 125 skill
icons, none of which is ArenaNet's.

> **`vault/run/reskin-roster/Gw.dat` IS STILL ARMED**, deliberately -- now with 125 icon
> rows as well. Rows 174150 and 174487
> (skills 317 and 318) and 174861 (skill 773) hold authored 64x64/64x64/128x128 icons, so a
> later profession run in that directory will draw a sunset in slots 2 and 8 and a
> calibration ruler in slot 3 -- that is us, not a fault. They were left because **the
> journals expired**: the client moved the MFT during the session, `--revert` correctly
> refused all three rather than write into dead space, and `datwrite` has no verb for the
> explicit restore it recommends. The original payloads are still in the journals' `before`
> fields. Full account in [`../crossbuild/FINDINGS.md`](../crossbuild/FINDINGS.md) §4c --
> and the procedural rule it yields is **revert before you launch, not after**.

### Skill NAMES are no longer a wall -- RECONSTRUCTION, and untested

Section 4 filed skill names under DOES NOT WORK, reasoning that a profession's 122-199
skills draw their name ids from **19-22 different archive text files** while its own
identity lives in one. That was a fact about REPLACING those files. Authored text points
AWAY from them instead, and both halves already exist:

* `repoint_skill.py` repoints a skill's **name, description and icon ids** -- it was built
  for a different question and never aimed at authored strings.
* Text file 98 has **1,012 records still free** (1,024 minus the 12 we wrote), against the
  ~244-398 a full roster needs at name-plus-description per skill.

**Nothing has been run.** The arithmetic fits and the tools exist; that is a plan, not a
result, and it is labelled so deliberately -- section 4's original claim was also
reasonable and was wrong for a reason nobody had tested.

### Unexercised rather than blocked

- **The picker label** is character-creation only and this server has no creation flow.
- **The `.data` table's consumer** is still unidentified; a split-donor run would name it
  the moment a second profession-name surface appears.
- **Campaign availability** is decoded, but 5.2 measured the cost: the naive one-dword
  patch yields a profession offered in Prophecies with no hair colours, no skin tones and
  no starter gear, because those tables are empty for the host outside its own campaign.
- **Armour redirection** -- four dwords, and ArenaNet already ships row sharing between
  professions 0, 1, 2 and 9, so the mechanism is proven in their data and untried in ours.
- **The attribute description RENDER.** Written, resolvable, and never seen: descriptions
  are hover tooltips and the harness drives keys (20.3).

### What a cold session should do first

Read section 20 before proposing any client patch for a game-mechanic effect. The single
most expensive mistake available here is costing a passive as a binary patch when the
client cannot read an attribute rank outside its own UI and never computes damage,
healing, energy or cast time at all.


---

## 14. Offline dive (2026-08-13): text is VIABLE, and the abbreviation has one consumer

Six agents, three parallel reads, no client launched -- the harness was in use. One
verifier held and **closed its own angle's weak link**; the other refuted parts of the
party plan and reordered it.

### 14.1 Authored text: **VIABLE**, by proof of existence

> **ArenaNet's own archive already ships 38,633 stored (compression-0) rows** against
> 138,708 compressed, 177,341 total. Re-derived independently by the verifier straight
> from the MFT bytes, importing nothing from `toolkit/mapdata`, and matching a third
> reader in `studies/datwrite/FINDINGS.md`.

They are ordinary content -- 36,658 `ffna` and 1,950 `ATEX`, **both types that also ship
compressed** -- so storedness is orthogonal to file type. The client-side branch is
OBSERVED byte-for-byte: at `0x00476315` a `test esi,esi / je` on the MFT extraBytes field
takes a path that computes the output size and returns the row's own buffer, **before any
payload byte is inspected and with no reference to file type**.

**VIABLE, not PROVEN:** no text file has ever shipped stored -- 1,089 of 1,089 text rows
are compression 8, 99 per language across 11 languages. The mechanism is generic; the
precedent stops at file type.

**The real cost is placement, not permission.** The eleven profession names span **three**
text files (language-0 indices 1, 2 and 30), and file 1 is 21,376 B compressed against
83,961 B stored -- about 4x its row, so it must relocate. The largest stored row that is
not the MFT or the file-id table is 19,292 B, and `test_datplan` already measured that
88.5% of nominal free space is live shadow-container generations.

**A live footgun, which nearly produced a false refutation:**
`archive.Archive().entries[row]` is **positional** while `textrec.TextIndex._rows[row]` is
keyed by **MFT row number**. Mixing them silently resolves to a different file -- the
verifier's first census "found" a stored text row that was actually a texture. That is the
fixture-resolves-to-the-wrong-thing failure this repo keeps paying for, and it is still
live in our toolkit.

### 14.2 The abbreviation has exactly ONE accessor, and no party gate

Accessor `0x005AB7E0` has **four direct callers, all inside one function** -- `0x00538D60`,
the abbreviated profession-label builder. The NAME accessor has **31**. That builder is
reached from `PtPartyEntry`, the party-search screens, `GmAgentCommander` and
**`GmPosseRoster`** (the verifier's correction; the synthesis had named `GmAgentStatus`).

**The render path contains no party, player-count or guild test.** It needs an agent bound
to the frame carrying professions at `+0x10E`/`+0x10F`, gated on `[edi+8] != 0` and style
bits `0x10000` and `0x1000` (also corrected -- the synthesis said `0x2000000`).

### 14.3 So the abbreviation was blocked by OUR server, not by the client

`0x00A6`'s setter is the **sole write path** to an agent's profession bytes -- one caller,
reached only from that opcode. **Our server sent `0x00A6` only for NPCs, never for the
player's own agent**, and the roster builder reads the agent rather than the player record.

Implemented offline:

| | opcode | payload |
|---|---|---|
| the player's own agent profession | `0x00A6` | after `0x00B7`, reusing the tested builder |
| party size | `0x00B0` | `[player, 1]`, 5 B |
| party leader | `0x00B1` | `[player, player]`, 6 B, self-link |

**Order is the measured part** and is pinned on the syntax tree: `PLAYER_CREATE`, then
SIZE, then LEADER. `0x00B0` fires no event for a fresh entry while `0x00B1` fires only on a
**leader change**, so leader-first is a no-op against the default and nothing is notified.

**Honest scope:** the array and the event are now correct. Whether a party entry actually
DRAWS is UNVERIFIED and needs one client run -- the verifier downgraded that claim and was
right to.

### 14.4 The `.data` table is the in-game Store, and it is dead weight

`0x004D1280` is reached through **slot 7 of a 72-slot vtable** whose owning translation
unit is pinned to `StoreSkillList.cpp` by two independent `.rdata` neighbours. Correction
to section 2.3: indices **1..10** duplicate `s_charProfession` exactly, not 1..8, with only
index 0 differing. Repointing the name table therefore leaves the Store panel showing the
host's original name -- a cosmetic divergence on a screen our server has no opcodes for.
**Dropped from the reskin patch list.**


---

## 15. The cheap home for authored text: ArenaNet ships 1,024 EMPTY string slots

§14 costed authored text as expensive: the eleven profession names span three text files,
and the main one is 21,376 B compressed against ~83,961 B stored, needing a relocation
into an archive whose free space is 88.5% live container generations. **That costing
assumed we must rewrite a file that already holds shipped text. We do not.**

String ids map to text files by `id // 1024`, and each file holds exactly 1,024 records.
An inventory of all 99 language-0 text files by on-disk size (read-only, this session):

| file_index | MFT row | on disk | string ids |
|---|---|---|---|
| **98** | **8295** | **56 B** | **100352..101375** |
| 28 | 3997 | 5,060 B | 28672..29695 |
| 79 | 7994 | 8,208 B | 80896..81919 |
| … | | | |
| 1 | 1911 | 21,376 B | 1024..2047 (holds nine profession names) |
| 30 | 3999 | 69,160 B | 30720..31743 (holds the other two) |

> **File index 98 is 1,024 records and EVERY ONE has an empty payload.** OBSERVED:
> 1,024 of 1,024 empty, and the arithmetic closes exactly — 1024 x 6-byte record header
> + 2-byte (language, file) tail = **6,146 bytes**, which is precisely its decompressed
> size. Empty in language 0, 1 and 2 alike, 56 B on disk in each.

**So ArenaNet ships 1,024 unused string slots, and they are the natural home for our
text.** That changes every term of §14's cost:

- **Size.** A stored replacement is ~6,146 B plus whatever text we write, against
  ~83,961 B for file 1 — about one fourteenth, and comfortably under the 19,292 B
  largest ordinary stored row that already exists.
- **Risk.** The file contains **nothing**, so authoring it cannot break a shipped string.
  §14's plan would have rewritten a file holding nine profession names and everything
  else in its 1,024-record range.
- **Reach.** One file instead of three. The eleven names span files 1, 2 and 30; ids
  100352..101375 are all in one place, and a reskin only needs to repoint
  `s_charProfession[8]` and `s_charProfessionAbbrev[8]` at ids inside it.

### Placement is not a blocker either

`datplan --insert 6400` against the study archive (read-only):

> **best fit of 96 usable runs** — a 13-block run at `0x000003B58E00`, 6,400 bytes plus
> 256 bytes of block padding.

It withheld 6 runs totalling 29.2 MB as live container generations (shadow MFTs and
file-id tables), which is the trap `test_datplan` exists for, and still found 96
candidates. The full diff is computable: payload, MFT header count, MFT row 3's
self-description, and the row itself, with every touched crc recomputed.

### The route, end to end

1. Encode text file 98 as a **stored** (compression-0) payload: 1,024 records, ours in
   the first few slots. Needs a record encoder — the decoder already exists in
   `textrec.py`, so the round trip is testable offline with no archive write.
2. Relocate MFT row 8295 into one of the 96 runs (`datmove`, journalled, byte-for-byte
   revert proven by `test_datmove`), clear `datcheck`'s ten open-time rules.
3. Repoint `s_charProfession[8]` and `s_charProfessionAbbrev[8]` at ids in
   100352..101375 with `reskin.py`, which already does exactly this.
4. One client run: the profession renders **our** word.

**Still UNVERIFIED, and it is the same one §14 named:** no text file has ever shipped
stored, so step 1's output has never been fed to the client. Steps 2-4 are all proven
machinery. The honest statement is that the mechanism is measured, the precedent is not,
and one run settles it.


---

## 16. The party pair is delivered and nothing draws (2026-08-13) -- NEGATIVE

Harness `20260813T152111`, capture `authsrv-20260813T152121-c1.jsonl`, **stock patched
client** (no reskin -- `pinned.identify` reports the ordinary 9-byte .text difference), so
the server change is the only variable. Driven with scripted input, no operator.

All five messages OBSERVED on the wire at +3.36 s, in the intended order:

| opcode | payload | |
|---|---|---|
| `0x0059` | PLAYER_CREATE | the player record |
| `0x00B0` | `b000010001` | party size 1 |
| `0x00B1` | `b10001000100` | self is leader |
| `0x00B7` | prof 8 | the player record's profession |
| `0x00A6` | `a600010000000800` | **the player's own AGENT profession -- new** |

Client healthy throughout: 36 c2s messages, last at +52.92 s, `missed 0`, no crash dialog.
The skills panel opens and reads **Ritualist** with the four Ritualist attributes, so
profession 8 is live everywhere it was before.

> **NO PARTY ENTRY DREW, AND THE ABBREVIATION DID NOT RENDER.**

Measured rather than eyeballed. The harness captures a frame per walk step, and the
top-left party region is **byte-identical across every in-world frame** -- one hash,
2430457683, before and after the `P` press and for the whole hold. Whole-frame diffs:

| transition | pixels changed |
|---|---|
| wait -> **P press** | 15,595 |
| wait -> wait (idle control) | 16,496 |
| wait -> **K press** | **308,636** |

`P` moved the same number of pixels as an idle frame -- that is the animating world, not a
window -- while `K` moved twenty times as many. **`P` did nothing**, and `K` demonstrably
works, so the input path is fine and the null is real.

### What this does and does not settle

**It does not refute §14.3.** The verifier explicitly downgraded that claim in advance to
"the array and the event are correct", never "an entry draws", and this run is exactly the
case it reserved judgement for. The messages are right; the drawing is not established.

**Three candidates, none eliminated by this run, and they are cheap to separate:**

1. **`P` may simply not be the party-window key on this build.** Nothing in this project
   ever measured it -- I assumed it. The frame diff proves the key did nothing, which is
   equally consistent with an unbound key and with a window that refuses to open.
   Cheapest check is offline: find the key binding, or the panel's toggle, in the client.
2. **The style bit.** The verifier measured the abbreviation's render gate as
   `[edi+8] != 0` plus style bits `0x10000` (abbreviation on/off) and `0x1000` (level
   suffix). Whether our frame carries `0x10000` is UNTESTED and nothing we send would set
   it.
3. **The party window may need state beyond the per-player array** -- membership rows,
   an outpost/party context -- that neither `0x00B0` nor `0x00B1` supplies.

The honest summary: **`0x00A6` for the player's own agent and the party pair are now sent
and correct, and they buy nothing visible yet.** They are still worth keeping -- `0x00A6`
is the sole write path to the agent profession bytes that six documents of this arc
wanted, and it costs two messages.


### 16.1 P is dead while every other window opens -- the prerequisites are missing

Operator's reading, and the runs support it: *the party window differs between explorable
areas and outposts, and we may not have met the conditions for it to exist.*

**The explorable field is not the condition.** `--explorable` reaches the wire -- `0x0199`
carries `is_explorable = 1` (payload `...9400 01...`, harness `20260813T152507`) -- and
the top-left party region is byte-identical to the outpost run, one hash across every
frame of both. That field is real and load-bearing elsewhere (it is what
`0x0084D9B0` reads, and it gates the secondary-profession drop-down's enable), but it
does not summon a party window.

**A key sweep separates "our input is broken" from "the window refuses", and it is the
window.** One run, per-step frames, whole-frame pixel diffs (harness `20260813T152713`):

| key | pixels changed | |
|---|---|---|
| **P** (party) | **15,603** | idle magnitude -- nothing opened |
| *wait -> wait* | 16,020 | the idle control |
| **H** (hero) | **133,938** | opened |
| **I** (inventory) | **118,477** | opened |
| **F** (friends) | **31,907** | opened |

So scripted input works, three windows open on demand, and **the party window is the only
one that refuses**. That is a much sharper negative than section 16's: it is not the input
path, not the UI generally, and not the explorable flag.

**What it leaves.** The window needs state we do not send. `0x00B0`/`0x00B1` write the
per-player array and that is measured, but the array is evidently not the gate on the
window's existence. The next step is offline and specific: find the party frame's own
open path and what it tests before it will exist -- the same consumer-backwards method
that named `0x00B6` and the abbreviation builder. `GmPosseRoster` and the `Pt*` modules
named in section 14.2 are the entry points.


---

## 17. The party window's gate, found and opened (2026-08-13)

Seven agents, no client launches. One verifier held the gate analysis; the other **refuted
the fix I was about to implement** and replaced it with retail's own sequence.

### 17.1 One value, two silent refusals

> **`PyCliGetMyPartyId` at `0x00856250`** -- `[[ctx+0x4C]+0x54]` dereferenced, returning 0
> when the pointer is null. It is 0 on our server, because nothing we sent ever wrote it.

It is read in two places, and BOTH refuse silently:

- **Outpost (the case our runs hit).** In GmView's command router `0x004E8BC0` the key is
  mapped to a start-menu item and passed through the availability predicate `0x005318D0`.
  Only two of the 17 items carry P's command `0x0BF`: item `0x0D` requires
  `is_explorable == 1`, and item `0x0E` -- the ONLY item of the 17 with an extra test --
  ends at `cmp esi,0x0E; je` into `call 0x00856250`, the party id. Both unavailable, the
  scan exhausts, and `je 0x004E995A` at `0x004E8C61` lands on the shared default arm,
  which is `pop / mov esp,ebp / pop / ret`. **The key is discarded before P's own arm
  runs.**
- **Explorable.** The arm runs, reaches `0x004EC0B0`, and bails at `0x004EC115` on the
  same party id -- before the only party FrameCreate at `0x004EC1BF` (child `0x66`,
  `CONTROL_PARTY_MAIN`, named by ArenaNet's own assert at GmView.cpp:3099).

**That is why forcing `is_explorable` changed nothing: it moves the refusal from the
router to the frame builder, and both read the same zero.** The frame is never CREATED,
which is exactly what unchanged pixels predict.

**P was bound all along**, triangulated three ways: the default key table (`VK 0x50` ->
command `0x0BF`), the start-menu command table, and the floating-dialog descriptor array
(dialog `0x1E` carrying `0x0BF`). The keybinding hypothesis is dead. *(One control
correction: **F is not a window toggle** -- its arm is a target/agent action -- so its
31,907 px was a weak control. H and I stand.)*

### 17.2 The fix is retail's own sequence, and my first one was wrong

I proposed allocating a party record directly with two messages. **Refuted:** the party
manager's vector must be built the way the client is built around, and the adversarial
pass measured retail's order on the wire, **8 of 8 live connections**, in the position
immediately after `PLAYER_SET_PARTY`:

| opcode | payload | |
|---|---|---|
| `0x01D2` | `d2010100` | party build BEGIN, allocates the record |
| `0x01CB` | `cb010100010001` | ADD the player as a member |
| `0x01D3` | `d3010100` | COMMIT, grows the vector and installs `parties[1]` |
| `0x01B2` | `b201010001` | `m_myParty = parties[1]` |

Twenty bytes. The constraints are asserts rather than taste: `0x01D2` exactly once per
connection (PyCliParty.cpp:1228), `0x01CB` between begin and commit with a matching id and
the player number `0x00B0`/`0x00B1` carry, `0x01D3`'s id equal to `0x01D2`'s
(PyCliParty.cpp:1238), and the id **non-zero** -- `0x01B2` with 0 means "keep current" and
fails SILENTLY, the one failure mode we could not have seen.

### 17.3 Result: it opens

Harness `20260813T162246`, outpost, `is_explorable` left at 0, scripted input.

| transition | pixels |
|---|---|
| wait -> **P** | **281,814** |
| P -> wait (idle) | 13,419 |
| wait -> H (control) | 130,644 |

**Prediction was "unambiguously above the idle control, staked at >60,000". It came in at
281,814** -- larger than the hero panel -- with no crash dialog and all four messages on
the wire as exactly the bytes predicted.

The window is **Party Search**: Players / Heroes / Henchmen tabs, a Party Leader / Size /
District / Description list, Seek Party, Close. That is dialog `0x1E`, whose proc
`0x005638B0` the dive named, and it answers the dive's own open question 3 -- our client
is in the layout where P raises the search dialog rather than the console page.

### 17.4 What this does NOT get, and it is the honest half

**The profession abbreviation still does not render.** The search list is empty -- no
other players exist on our server -- and the roster entry that draws an abbreviation is
`PtPartyEntry`, a different frame from the search dialog. The top-left party region is
still unchanged. So §16's target is not met; what is met is the gate that stood in front
of it, and the arc now has a party window to build on for the first time.


---

## 18. The party ROSTER opens, and the abbreviation renders (2026-08-13)

Harness `20260813T171051`, capture `authsrv-20260813T171058-c1.jsonl`, stock patched
client, `Test Warrior`, profession 1. Scripted input, no operator: `wait:6 P:1 wait:8
H:1 wait:8`.

> **`Party Members [P]` opens, carrying one member row: `W0 Test Warrior`.**

`W` is the Warrior abbreviation. **This is §16's target, met** -- a party row drawing a
profession abbreviation is on screen. *(The frame is `PtPlayer`, not `PtPartyEntry`; §16,
§17.4 and the first draft of this section all had that wrong. Corrected in §18.6.)*

### 18.1 The gate was a PAIR, and each half had been tested alone

The one combination nobody had run is the one that works:

| | outpost | explorable |
|---|---|---|
| **no party record** | P discarded by the key router `0x004E8BC0` (§17.1) | P's arm bails at `0x004EC115` (§17.1) |
| **party record built** | Party **SEARCH**, dialog `0x1E` (§17.3) | **Party Members -- the ROSTER** |

§16.1's explorable run predated the party build; §17.3's party build ran in an outpost.
Both halves were measured, the pair never was. So `is_explorable` is not "not the
condition" as §16.1 concluded -- it is *half* of it, and §16.1's conclusion was drawn from
a run that could not have shown the other half.

**This confirms §17.1's reading of the explorable arm exactly.** `0x004EC115` bailed on
`PyCliGetMyPartyId`; with the party record built that value is 1, the arm reaches the
FrameCreate at `0x004EC1BF` (child `0x66`, `CONTROL_PARTY_MAIN`, GmView.cpp:3099), and
`CONTROL_PARTY_MAIN` is the roster rather than a search container. Prediction stated before
the run, hit.

### 18.2 Wire and controls

Every message OBSERVED in the capture:

| opcode | payload | |
|---|---|---|
| `0x0199` | `990101000000940001...` | INSTANCE_LOAD_INFO, **`is_explorable=1`** |
| `0x01D2` | `d2010100` | party build BEGIN |
| `0x01CB` | `cb010100010001` | ADD member, player 1 |
| `0x01D3` | `d3010100` | COMMIT |
| `0x01B2` | `b201010001` | set mine |
| `0x00B7` | `b70001000000010000` | player profession record, prof 1 |
| `0x00A6` | `a600010000000100` | the player's own agent profession, prof 1 |

All 8 spawn checkpoints PASS, `P` delivered in full (1.00034 s of 1), client exited code 0
with **no error dialog**. Control: `H` opened the Hero panel in the same run, reading
`Test Warrior / Warrior`.

Two independent witnesses, which is why this is not one screenshot: the harness's own
frame `w014.png` and the operator's screenshot both show the window.

### 18.3 A method correction: §16 measured a rectangle that could not have gone red

§16 and §16.1 reported the **top-left** party region as byte-identical, one hash
`2430457683`, across every frame of every run, and read that as evidence of the null.

**The party roster draws at the TOP RIGHT.** That regional hash was over a rectangle the
roster never touches, so it would have stayed constant through a success too -- a check
that cannot fail. The null itself was real and was carried by the *whole-frame* diffs (P
moved 15,595 px against a 16,496 px idle control), which is the number that did the work.
The lesson is the repo's own: an instrument aimed at the wrong place returns a confident
constant, not an error.

### 18.4 The `0` in `W0` is the LEVEL -- and it settles property 36

**OBSERVED.** Operator's call, confirmed in one run. Harness `20260813T172323`,
`--probe level --explorable`, the roster open across all three steps:

| probe step | roster row | frame |
|---|---|---|
| `level -> 1` | **`W1 Test Warrior`** | `w003.png` |
| `level -> 15` | **`W15 Test Warrior`** | `w006.png` |
| `level -> 20` | **`W20 Test Warrior`** | `w019.png` |

The row is `<abbreviation><level>`, so the earlier `W0` was a level of zero -- the value
this server had never sent. Style bit `0x1000`, the "level suffix" of §14.2's render gate,
is on.

**This settles the `level` probe's own question**, open since 2026-08-05 and UPSTREAM-only:
*"Is agent int-property 36 on `0x009F` the character's level?"* Its criterion was stated in
advance -- *"If all three tracked, property 36 is level and this is settled"* -- and all
three tracked. It was corroborated by ldufr and gw-preservation and had **never been
observed by us**; now it has.

**The two level channels are confirmed distinct in the SAME frame**, which is the part no
single readout could have shown. The top-left bar reads `Level: 1` in w003, w006 and w019
alike -- that is the per-PLAYER level, `0x00E9` field 9, which this server does send -- while
the roster row moves 1 -> 15 -> 20 on the per-AGENT property beside it. `authsrv.py`'s own
warning at the field map ("do not confuse this with the per-AGENT level ... probing one
while watching the other is how the first attempt read as a false negative") is now a
measurement rather than a caution.

**A method note.** The probe predicted the effect on the **nameplate**, which our world does
not draw, so the probe as written could not have been scored in this session. The roster is a
second readout for the same property, and it existed only because §18 opened it. The probe's
own note names this failure mode -- aiming at the other channel -- and the fix was a new
place to look rather than a new packet.

**My reasoning was the wrong half.** §18.4 as first written argued that the Hero panel's
`Level: 1` told *against* a level suffix. It does not: it tells against a level suffix
reading the *player* level, which is the distinction the same paragraph then raised and
declined to lead with.

### 18.5 Why this matters to the reskin

The abbreviation is drawn from the profession tables `reskin.py` edits. A reskinned host
profession should now be READABLE on this row -- which makes the party roster the first
place in the client where a custom profession's identity is visible outside the panels,
and the cheapest visual check the arc has.

### 18.6 The static dive, and the two corrections it makes to this section

Thirteen agents (six lenses, six skeptics, one synthesis), no client launches, run
CONCURRENTLY with §18's experiment. **Its central question was overtaken by the run** -- it
was asked "why does our client fail the gate", which was true when it launched and false by
the time it answered, and its synthesis says so honestly ("why our client fails it is,
honestly, not yet established"). Its READINGS of the code stand, and two of them correct
this arc. Both are re-verified here rather than taken on the agents' word.

**Correction 1 -- the member row is `PtPlayer`, not `PtPartyEntry`.** §16.1, §17.4 and
§18's own opening all named `PtPartyEntry` as the frame that draws a member's abbreviation.
PtRoster's member loop at `0x00570527` adds each row through `0x0057056D` ->
`0x00570A80` -> `CtlFrameList` with item proc `0x00574F30` = PtPlayer, whose init asserts
`msg.createParam` (PtPlayer.cpp:442, `0x005747B8`) and `uiMsg.member` (PtPlayer.cpp:445,
`0x005747D4`). **VERIFIED HERE** -- both asserts are at those addresses. `PtPartyEntry` is
the row for a WHOLE PARTY, the unit of the search list, and it draws abbreviations too,
which is how the two came to be conflated.

**Correction 2 -- `is_explorable` is the mission MAP TYPE, and that is WHY it was half the
gate.** The dword this server sends as `is_explorable` in `0x0199` is `context->map`,
written by the `0x0199` handler at `0x0084EE65` into `missionContext+0x238` and read by
`MissionCliGetMap` (`0x0084D9B0`). **`MISSION_MAP_GAME` is ArenaNet's own name for the
value 1**, asserted 9 times in MsCliApi (MsCliApi.cpp:313 among them). PtFrame's child
builder decides on it:

```
0x00564F8F  e8 1c8a2e00   call 0x0084D9B0      ; MissionCliGetMap()
0x00564F94  83 f8 01      cmp  eax, 1          ; MISSION_MAP_GAME
0x00564F97  75 4a         jne  0x00564FE3
0x00564F9B  c745f0 500d5700  mov [ebp-0x10], 0x00570D50   ; PtRoster's frame proc
```

The not-equal branch builds child 1 with proc `0x0056A100` = **PtFormation** (assert
`placement`, PtFormation.cpp:612, `0x0056A264`). **VERIFIED HERE** -- the bytes above, the
`MISSION_MAP_GAME` assert census, and PtFormation's assert.

So §18.1's table is right about what happens and this is the mechanism: **in an outpost the
roster is never the frame that exists** -- the formation panel is -- and P falls through to
the search dialog. "Explorable" is not a flag the party code consults; it is the map-type
dword that selects which panel PtFrame builds. That is a better model than §18.1's "half the
gate", and it predicts the outpost result rather than merely accommodating it.

**And a corroboration of §18.4 from the other side.** UPSTREAM (the dive's, not re-verified
here): the abbreviation builder `0x00538D60` falls through at `0x00538E16` to a LEVEL-ONLY
string when primary and secondary are both zero. The row's format being
`<abbreviation><level>` is what `W1` -> `W15` -> `W20` shows from the wire side.

### 18.7 Live leads from the dive -- none of them needed for what now works

Ranked by what they would buy. None is required for the roster: it draws today.

1. **`0x003C` `(player_number, set=4, clear=7)`** -- present in 9/9 retail connections, 3x
   per player, and **never sent by us in 190 played captures**. Writes `[playerRec+0x34]`
   in the same `ctx+0x80C` stride-0x50 array `0x00B0`/`0x00B1` write. The cheapest unknown
   message in the arc.
2. **`PLAYER_AGENT_ID == PLAYER_NUMBER == 1`** makes every possible player/agent mis-join
   invisible. Retail never has them equal. Worth changing for diagnostic value alone,
   independent of any fix.
3. **The `1 <= party_id <= 20` refusal in `agents.party_build` may be wrong.** Retail's own
   outposts use 25, 37, 45 and 69. NOT re-verified here, and the refusal is cheap while a
   wrong id fails SILENTLY -- check `0x00858897`'s reachability before relaxing it.
4. **Ordering.** Retail sends the party build AFTER the local `WORLD_CREATE_AGENT` (8/8,
   with indices); we send `0x0020` four messages after `0x01CB`. **It works anyway**, so the
   ordering is not load-bearing for the roster -- and that is a measurement, not a
   dismissal.
5. **Do not "fix" `0x01CB`.** Ours is byte-identical to ArenaNet's wire (`cb010100010001`)
   and its field 2 is a player number in 8/8, including four connections where player and
   agent differ. The member record's middle dword is explicitly zeroed at `0x00859894` with
   no reader anywhere.
6. **An honest negative worth keeping:** no message binds a party member slot to an agent.
   The client resolves `player_number -> agent` itself through the ChCliApi array that
   `0x0059`/`0x00B0`/`0x00B1`/`0x003C` populate. This kills the "our member is added before
   the agent exists" hypothesis I raised before the run.

The dive's own top unknown, unresolved: **`0x00C07980`** selects between two frame procs at
`0x004EC175`-`0x004EC1AC` and nobody has found its writer.

### 18.8 `0x003C` sent, three ways: a clean NULL (2026-08-13)

§18.7's best lead, run. Harness `20260813T191759`, capture
`authsrv-20260813T191811-c1.jsonl`, explorable, roster open before the first send.

**First, a correction to the dive's reading of the message.** It reported
`(player_number, set=4, clear=7)`. Censused over ArenaNet's own captures with
`tape.decode_all` -- **423 sends across 12 of 12 live game connections**:

| | |
|---|---|
| mask (second dword) | **7 in 423 of 423** |
| value (first dword) | 4 x287, 5 x60, 0 x48, 7 x12, 6 x12, 1 x4 |

Every value lies inside the mask and the mask never varies, so it is a
**(value, mask)** pair -- three bits cleared then written -- not (set, clear). That
matches the handler's `and` at `0x0080EC26` and `or` at `0x0080EC48` into
`[playerRec+0x34]`. A lone player is `(1, 4, 7)`.

**The sweep, and why it is a sweep.** Retail sends 4 for a solo player, so sending only
4 could not distinguish "the message does nothing" from "we already look like 4". All
three OBSERVED on the wire with the intended bytes:

| t | payload | |
|---|---|---|
| 5.33 s | `3c0001000400000007000000` | value 4 -- retail's own solo value |
| 11.34 s | `3c0001000000000007000000` | value 0 -- all three bits clear |
| 17.34 s | `3c0001000700000007000000` | value 7 -- all three bits set |

> **NOTHING CHANGED.** The party region is **0.000% across all 18 frame transitions**,
> and the send-adjacent whole-frame diffs (0.108%, 0.076%) sit **at or below the 0.104%
> idle median**. Max whole-frame movement in the window was 1.586%, and that was the P
> press opening the roster.

The control that keeps this from being vacuous: **the roster was open the whole time** --
`w010.png` at 23:18:32Z shows `Party Members [P]` carrying `W0 Test Warrior`. A null
measured against a window that was never there would say nothing. Client survived all
three; no error dialog.

**Prediction was a null and the null held**, which is the weaker kind of result to
report and is why the sweep matters: three different values, one open window, no
movement.

**What this does NOT settle**, and both limits are real:

1. **One player.** 0x003C is per-player and our instance has exactly one. The values
   retail varies most (5, 6, 7, 1) appear in its BUSY connections; the solo ones send 4
   three times and nothing else. A three-bit per-player flag may simply have nothing to
   express about a party of one.
2. **Late, not at load.** Retail sends it at t=0.23-0.73 s, inside the instance load;
   ours went at 5-17 s. If the bits are read once when something is BUILT, a later write
   changes a value nobody re-reads. The cheap follow-up is to move it into the burst at
   retail's position -- before `0x0020` -- and diff the load.

So `0x003C` stays on the "never sent by us" list with its reason now measured rather than
assumed, and it is **not** a prerequisite for anything in this section: the roster drew
its row, with an abbreviation and a level, without it.

### 18.9 `0x003C` at retail's own LOAD-TIME position: still nothing (2026-08-13)

§18.8 sent it late and measured a null; the open question it left was whether bits read
once at BUILD time behave differently. Answered: they do not. `--player-flags VALUE` now
sends `0x003C` immediately before `WORLD_CREATE_AGENT`, which is retail's own slot.

**Six runs, four arms, one message the only variable.** All PASS, no error dialog.

| arm | value | `0x003C` on the wire | party region vs control |
|---|---|---|---|
| A, A2 | *(none)* | -- | control |
| B | 4 (retail's lone-player value) | `3c0001000400000007000000` | **0.000%** |
| C | 0 | `3c0001000000000007000000` | **0.000%** |
| D, D2 | 7 | `3c0001000700000007000000` | **0.000%** |

Zero across **every matched frame of every arm**, while the within-arm noise floor reaches
0.007% -- so the instrument is live and reads nothing. Whole-frame differences (0.137%,
0.243%, 0.304%) are the animating world, the same magnitude as §18.8's 0.104% idle median.
The order is confirmed in the capture: `0x003C` and `0x0020` carry the SAME timestamp with
`0x003C` first, and the control emits no `0x003C` at all.

**Not vacuous:** the roster was open in every arm -- the cropped party region shows
`Party Members [P]` carrying `W0 Test Warrior`.

**The client's own traffic is unchanged too**, which is the stronger half: 20 decoded c2s
messages over 9 opcodes in arms A, B and C, identical sets and counts.

#### The excursion that was NOT a finding, and the correction under it

Arm D (value 7) came back with **21** decoded messages over 10 opcodes -- one extra
`0x000C` at t=2.61 s. It survived the obvious explanation: arm D was not the longest
session (C ran 54.16 s to D's 53.57 s) and the message landed at 2.6 s rather than at the
tail. Value 7 sets two bits no solo capture carries, so this looked like the one place the
sweep had bitten.

**Repeats refuted it.** A2, a CONTROL run, produced `0x000C` at t=2.22 s; D2, a second
value-7 run, produced none. Two of six runs carry it, one from each arm -- nondeterministic
client behaviour, not an effect of the flag. Recorded because a single-run signal that
survives one alternative explanation is exactly the shape this project has been burned by
before, and the repeat cost ninety seconds.

**And a correction to how the first comparison was made.** The A-vs-B traffic check was
first run over `frame`/`c2s` records, which carry `plain` bytes and NO opcode field -- so
every one of them counted under a single `None` key and the result was reported as
"identical opcode sets and counts" when it was really "both arms sent 16 frames". The
`decoded` records are the instrument, and they are what found the `0x000C` the frame-level
view had hidden. A comparison that cannot tell two opcodes apart cannot find a difference
between them.

#### What is settled and what is not

**Settled:** `0x003C` is not a prerequisite for anything currently observable here. At
retail's position, with retail's value, it changes neither the screen nor the client's
behaviour -- and the roster draws its row, with an abbreviation and a level, without it.
The flag stays OFF by default: sending a message that demonstrably does nothing would
retire a control for no gain.

**Not settled, both still real:**

1. **One player.** Values 5, 6 and 1 appear only in retail's BUSY connections and are
   untested; a three-bit per-player flag may have nothing to express about a party of one.
2. **A lead from another session, UNVERIFIED and theirs:** three opcodes in
   `PyCliParty.cpp` whose job is to refuse a party action for an **unnamed account**, and
   our loopback account has no account name. Not tested against this arc by either of us,
   and no connection is asserted here -- but it is the first candidate offered for why the
   member row renders as a RED bar, which nothing in §18 explains. Note `asserts.py --file
   PyCliParty` shows no account-name assert in its readable set, and that set is a FLOOR
   rather than a census, so its silence refutes nothing.

### 18.10 The red row is not a fault -- it is a full HEALTH BAR (2026-08-13)

§18.9 filed "why is the member row a red bar" as unexplained and floated an
account-name lead for it. **The question dissolves: red is what a healthy party member
looks like.** No client launch, no disassembly -- the game's own documentation says so.

> **WIKI (GWW, "User interface" §Health bar, rev. 2026-07-15):** "The '''health bar'''
> is a red bar that indicates the status of the character's current health relative to
> their maximum health."
>
> **WIKI (GWW, "User interface" §Party window, rev. 2026-07-15):** "It displays health
> bars for party members, animal companions and some quest and mission allies. **The red
> bars represent the allies' or party members' health.** A disconnected player will have
> its health bar greyed out."

This is the wiki at its strongest by `browse-gw-wiki`'s own test -- *could a player have
seen this from the game window?* -- and it is corroborated inside our own screenshot: the
HUD health bar at the bottom of the frame reads `100` on red and the energy bar reads `25`
on blue. Red is this UI's colour for health everywhere, not a state on the row.

**So the row is CORRECT.** `W0 Test Warrior` on a full-width red bar is a party member at
full health, drawn exactly as retail draws one. The arc has more working than §18 claimed.

**Two things this retires:**

1. **The disconnected reading is refuted, not merely unsupported.** A disconnected player
   is **greyed out**; ours is saturated red. Whatever else an unnamed account may break,
   it is not what colours this row -- and framing that lead as "the first candidate for
   the RED member row" in §18.9 was my error, not the other session's claim. Their lead
   was about party ACTIONS being refused, which is a different question and still open.
2. **The bar's fullness is a readout we were not using.** It is a live per-member health
   display that this server has never deliberately driven.

**The confirmation, when a client is free -- one run, and it is falsifiable.** Set the
player's health to roughly half and the red bar must shrink to roughly half width while
the name stays put. Threshold: the party region moves well above the 0.007% within-arm
floor §18.9 measured, and the change is a horizontal shortening rather than a colour
shift. If instead the bar stays full, the row is drawing a constant and not this player's
health, which would be a different and more interesting result -- so the run is worth its
minute either way.

### 18.11 CONFIRMED: the bar is this player's health, to within half a percent

§18.10's falsifiable run, executed. Harness `20260813T212610`, capture
`authsrv-20260813T212617-c1.jsonl`, explorable, roster open before the first send.
Property 16 (DAMAGE) is a FRACTION of maximum health, so `-0.5` then `-0.25` predicts a
bar at 50% then 25% of its width.

The bar's extent is DETECTED from the baseline frame rather than assumed -- the first
measurement used a hand-placed crop box and read the full bar as "66.7%", which is the
box being wrong, not the bar:

| stage | bar fill | predicted |
|---|---|---|
| baseline | 167 px -- **100.0%** | -- |
| after `-0.5` | 83 px -- **49.7%** | 50% |
| after `-0.25` | 40 px -- **24.0%** | 25% |

> **The party row's red bar IS this member's health.** The row is a live per-member
> health display, it tracks a fraction of maximum exactly as documented, and this server
> can drive it.

Corroborated by the region diffs, which are a second instrument over the same frames: the
party region moved 2.561% on the first cut and a further 1.201% on the second, a ratio of
2.13 against the 2.0 that halving-then-quartering predicts. Both are far above §18.9's
0.007% within-arm floor. The colour never changed and the name never moved, which is what
separates "the bar shortened" from "the row was redrawn".

#### The third step killed the client, and that is a finding too

> **`Assertion: damage.amount <= 0` -- `P:\Code\Gw\AgentView\AvChar.cpp(5893)`**, build
> 38797, 21:26:38, which is the recovery step's own wall clock. Captured automatically
> from the fatal-error dialog.

My recovery step sent damage `+0.75`, reading property 16 as a signed health delta. It is
not: it is DAMAGE, and **the client asserts the sign**.

**And this was already known -- the claim that it was new is retracted.** The `damage`
probe's own note, in the same file I was editing, has said since **2026-08-06** that "a
positive value crashes the client on ArenaNet's own `damage.amount <= 0`". I rediscovered
a documented bound by crashing a client, and then wrote it up as a finding. The measurement
stands (the address `AvChar.cpp:5893` and the build are now on the record beside the
claim); what does not stand is calling it ours. **Read the probe you are editing.**

It costs nothing here. The recovery was a control for "the bar stopped tracking" versus
"the character died", and two cuts landing within 0.3 and 1.0 points of prediction settle
the tracking on their own.

**Worth noting about the instrument:** the run reported `RUN VERDICT: PASS`. That is
correct and not a bug -- the spawn checkpoints passed and the walk completed. The client
was alive the whole time, behind a modal dialog with its message pump stopped, which is
exactly the state `studies/smsgsweep` documents a socket fence cannot see. The crash was
caught because the harness extracts the dialog on **every** run since 2026-08-12; before
that change this would have been a silent 98% frame diff with no explanation.

### 18.12 The recovery step: it does NOT refill, and the prediction failed

Harness `20260813T214241`. The two cuts reproduce EXACTLY -- 100.0%, 49.7%, 24.0%, the
same three numbers as §18.11 on a fresh client -- and then:

| stage | wall | party row | HUD bar |
|---|---|---|---|
| baseline | 21:42:55 | 100.0% | reads 100 |
| damage `-0.5` | 21:42:58 | **49.7%** | reads 50 |
| damage `-0.25` | 21:43:05 | **24.0%** | reads 25 |
| **int property 42 = 100** | 21:43:11 | **24.0%** | **reads 25** |

> **The bar did not move.** Thirteen seconds and nine frames after the recovery, the party
> row is still 24.0% and the HUD still reads **25**. No crash dialog; the client was
> healthy throughout.

**Both readouts agree, which is the useful half.** The party row and the HUD health bar
track each other through every stage -- so the row is not a second, independent copy of
health that we could desynchronise, and the recovery's failure is about the PROPERTY, not
about the row.

#### Where the failed prediction came from, and it is a labelling failure

The step was built on this, from the `damage` probe's docstring:

> Setting health (int property 42) assigns `health_max = value` and `health = 1.f`

That sentence cites **ldufr/Headquarter**, `code/client/agent.c` -- a REIMPLEMENTATION.
Under this repo's own vocabulary that is **UPSTREAM**, not OBSERVED, and I built a
prediction on it as though it were a fact about the retail client. The arc's own rule
(`CLAUDE.md`: "OpenTyria says so is UPSTREAM, not a fact about retail Guild Wars") exists
for exactly this.

There IS a real observation from 2026-08-06 -- "Int property 42 raised a health bar
reading 100" -- and it is compatible with both explanations below, because on that run the
max was being SET rather than re-set to the value it already held.

**Two candidates, and one run separates them:**

1. **Same-value no-op.** Our player's `health_max` is already 100, so assigning 100 changes
   nothing and whatever triggers the refill never fires. This predicts that int property
   42 = **200** refills the bar AND widens what "full" means.
2. **The upstream reading is wrong for retail.** Property 42 does not carry the refill at
   all, and 2026-08-06's observation was the max being established rather than health being
   restored. This predicts 200 changes the maximum with the bar still at a quarter -- or
   does nothing.

The discriminator is one send of int property 42 = 200, watching both bars. **NOT RUN** --
the harness is gated on the owner's go-ahead, and this is a new question rather than the
one that was authorised.

**What is unaffected:** §18.11's confirmation. The bar is this member's health, measured
twice on two clients at 100.0/49.7/24.0. Nothing about the recovery touches that.

### 18.13 Int property 42 is MAXIMUM health, and current health follows it by the same ABSOLUTE DELTA

Harness `20260813T215004`. The discriminator §18.12 asked for, and the answer is none of
the three outcomes that section listed -- including the one this document predicted.

| stage | HUD number | HUD bar | party row | implied |
|---|---|---|---|---|
| baseline | **100** | 100.0% | 100.0% | 100 / 100 |
| damage `-0.75` | **25** | 23.9% | 19.8% | 25 / 100 |
| **int property 42 = 200** | **125** | **61.7%** | **62.3%** | **125 / 200** |
| int property 42 = 100 | **25** | 23.9% | 19.8% | 25 / 100 |

> **`health += (new_max - old_max)`.** 25 + (200 - 100) = **125**, and 125/200 = **62.5%**
> against 61.7% and 62.3% measured on two independent bars. Putting the maximum back
> subtracts the same 100 and returns exactly 25.

This is ordinary Guild Wars behaviour seen from the wire -- a maximum-health increase
GRANTS that health, the way a rune or a health buff does -- and it is reversible, which the
third step establishes rather than assumes.

**Three readings die here, and one of them is this document's own:**

| reading | would have shown | source |
|---|---|---|
| `health = 1.f`, a refill | 200 | ldufr/Headquarter -- **UPSTREAM**, now REFUTED for retail |
| the fraction survives (0.25 x 200) | 50 | **my prediction in §18.12**, REFUTED |
| property 42 is not the maximum | 25 | REFUTED -- it plainly is |

**And it explains §18.12 exactly.** That run set the maximum to 100 when it was already
100: the delta was ZERO, so health did not move. The observation was right and the framing
("a refill that did not fire") was wrong -- there is no refill to fire. The candidate
called "same-value no-op" was correct in outcome and wrong in mechanism.

#### A measurement note, because the numbers are method-dependent

The row bar reads 19.8% here where §18.11 read 24.0% for the same quarter-health state.
Neither is wrong: the two passes use different column thresholds, and the row bar's chrome
sits near the cut-off. **Absolute fill percentages from this method are only good to a few
points; the RATIOS across stages are what carry the result** -- which is why the load-bearing
number is 62.5% predicted against 61.7% and 62.3% on two bars whose absolute readings differ
by four points at the same health. The HUD's printed NUMBER is exact and is what settles it.

`0x009F [42, agent, N]` is therefore the lever for maximum health, and this server can now
set both terms of the party row: `0x00A3 [16, ...]` for current, `0x009F [42, ...]` for
maximum.

### 18.14 The custom abbreviation RENDERS -- RUN 1's open item, closed

Harness `20260813T221128`, explorable, `--spawn-profession 8`, reskinned client.

> **`Fast Casting0 Test Warrior`**

RUN 1 (§8) left this in writing: *"The abbreviation donor was not observed. Fast Casting
was patched into `s_charProfessionAbbrev[8]` but the abbreviated form shows in the party
window and nameplate, neither of which renders in a solo session with no party.
**UNVERIFIED**, and one run with a party or a visible nameplate settles it."*

The party window renders now (§18.1), so this is that run. **Settled:**
`s_charProfessionAbbrev` is the table the party roster reads, and `reskin.py`'s edit
reaches it -- `abbrev 2057 -> 2078` at file `0x00637808`, 8 bytes changed, length
unchanged, DH still `ours`. Profession 8 confirmed on the wire (`0x00B7` prof 8, `0x00A6`
prof 8) and the row reads the donor string where a stock Ritualist would read `Rt` and the
Warrior of §18.1 read `W`.

**This is the first place a custom profession's identity appears outside the panels.**

#### Two things the picture says that the plan did not

1. **The "abbrev" table is a STRING ID, not a length-limited field.** ArenaNet's own
   entries happen to be short (`W`, `Rt`), so "abbreviation" reads like a format
   constraint. It is not: our donor is a full attribute name and the client renders it
   whole, overflowing the space a two-letter code would occupy. Nothing clipped, nothing
   crashed -- but a reskin that wants to LOOK like a profession needs a short donor
   string, and that is an authoring constraint this arc had not written down.
2. **The trailing `0` is the level suffix**, the same one §18.4 asked about and §18.11
   settled. The row's format is `<abbrev><level>`, which is why `W0`, and now
   `Fast Casting0`.

#### Method note: a dedicated run directory rather than mutate a shared one

RUN 1 patched the SHARED run client and restored it byte-for-byte afterwards. Another
session was live this time, so the patch went to `vault/run/reskin-roster/` instead --
assembled by `make_run_dir.py`, 4 GB, touching nothing anyone else launches from.

**That trade has a cost worth recording: the cage is PER BINARY.** A new client under
`vault/run/` has no firewall rule and `assert_launch_safe` refused the launch outright,
naming the binary and quoting `PLAN.md` §6.2. Caging it needs an ELEVATED shell
(`isolate_client.ps1`, no arguments -- it enumerates every client under `vault/run`), which
is an owner action and cost one UAC prompt. That is the control working as designed: it is
what stops an ours-DH client sitting uncaged, which happened for a day once. Budget the
prompt when adding a run directory; the alternative is mutating a shared binary while
somebody else may launch it.


---

## 19. AUTHORED TEXT WORKS: a profession named by our own word (2026-08-13)

Harness `20260813T222031`, explorable, `--spawn-profession 8`, reskinned client reading a
modified archive.

> **`Profession: Stormcaller`** in the Skills and Attributes panel.
> **`Sc0 Test Warrior`** in the party roster.

Neither string exists in anything ArenaNet ships. **We wrote them.** §15's route is
complete, and with it the last blocker on the reskin: until now a custom profession could
only be NAMED things the client already had strings for, and every document in this arc
said so.

### 19.1 The step that had never been taken

§15 was explicit about which part was unproven: *"no text file has ever shipped stored, so
step 1's output has never been fed to the client. Steps 2-4 are all proven machinery. The
honest statement is that the mechanism is measured, the precedent is not, and one run
settles it."*

**Settled. The client reads a compression-0 text file.** Row 8295 went from 56 B
compressed to 6,172 B stored, and the client resolved both ids out of it.

### 19.2 The four steps, each with the check that made it safe

1. **Encode.** `textrec.encode_file` with no strings is **BYTE-IDENTICAL to ArenaNet's own
   row 8295** -- 6,146 B, 1,024 empty records, tail `00 62`. That equality is what says the
   encoder is right *before* anything is written, and the archive could have refused it.
   Ours with two strings is 6,172 B and walks to 1,024 records, tiled, with the strings at
   records 0 and 1.
2. **Relocate.** `datmove` moved the row (`0x8517000` -> `0x3B58E00`, reservation 512 ->
   6,656), journalled to `vault/run/reskin-roster/row8295.journal`, with **0 overlapping
   row pairs** afterwards. `datcheck --preflight` then cleared **10 of 10** of the client's
   own open-time rules on the modified archive.
3. **Repoint.** `recipes/stormcaller.toml`, a new recipe: `name -> 100352`,
   `abbrev -> 100353`. 10 bytes differ, length unchanged. The id map is arithmetic --
   `id = file_index * 1024 + record`, so file 98 starts at 100352.
4. **Run.** Both strings on screen, no crash dialog, `RUN VERDICT: PASS`.

### 19.3 What this does and does not settle

**Does:** authored text is real, not merely viable. A profession can now carry a name and
an abbreviation of the owner's choosing, and the same 1,022 remaining records are available
for attribute names, descriptions and anything else keyed by string id.

**Does not:** the attribute names in this run are still BORROWED (`2094`, `2092` --
visible as "Air Magic" and "Soul Reaping" in the panel). That was deliberate, to keep the
run a single-variable change; they are the same mechanism and cost two more records.

**Provenance is unchanged and worth restating:** no ArenaNet text entered this repo. The
recipe holds numbers, the strings were written by us into the owner's own archive COPY, and
`vault/` is gitignored. This is the pattern `mapbuild.py` already proves -- commit the id,
resolve the string at run time.

### 19.4 The archive question, answered by accident

`PLAN.md` §8 carried an open decision: the text route writes into a 4.2 GB archive and
"needs the owner's call on WHICH archive -- study copy, a fresh copy, or the run client's
own." **The dedicated run directory built for §18.14 answered it.**
`vault/run/reskin-roster/` is a throwaway 4 GB copy that only its own caged client reads,
so the write risked nothing shared and needed no decision at all. Its cost is one UAC
prompt for the per-binary cage (§18.14) and 4 GB of disk.

The journal makes it reversible byte-for-byte:

```
python toolkit/mapdata/datwrite.py --revert C:/gd/Rurik/vault/run/reskin-roster/row8295.journal
```

### 19.5 The whole identity tier, authored (2026-08-13)

Harness `20260813T222809`. Seven strings, all ours, all on one screen:

```
Profession: Stormcaller
Attributes (50 unused points)
    Tempest         Galecraft        Windward
    Thunderhead     Storm Calling
```

| record | id | string | consumer |
|---|---|---|---|
| 0 | 100352 | `Stormcaller` | `s_charProfession[8]` -- panel heading |
| 1 | 100353 | `Sc` | `s_charProfessionAbbrev[8]` -- party roster |
| 2 | 100354 | `Storm Calling` | attr 36, the host's PRIMARY |
| 3 | 100355 | `Tempest` | attr 26, claimed off reserved profession 11 |
| 4 | 100356 | `Galecraft` | attr 32 |
| 5 | 100357 | `Windward` | attr 33 |
| 6 | 100358 | `Thunderhead` | attr 34 |

**Nothing on that screen is ArenaNet's text.** §19's run still borrowed the five attribute
names; this one does not. The profession's whole identity tier -- name, abbreviation and
every attribute it owns -- is now authored, and the panel derives the five-attribute set
from `attr-owner` exactly as §4 predicted.

**The second write needed no relocation.** 6,268 B against the 6,656 B reservation §19.2
took, so `datwrite --replace` wrote it in place (388 B of reservation tail zeroed) and
`datcheck --preflight` stayed **10 of 10**. Second journal beside the first; both revert
byte-for-byte.

### 19.6 A limitation found by tripping over it: reskin.py cannot re-patch its own output

Reading the attribute table out of the ALREADY-patched client failed:

> `name: the 11 dwords before its anchor are [2040, ..., 2047, 100352, 31548, 31549], whose
> first nine are not consecutive. The anchor and the shape disagree, so one of the two
> assumptions is wrong for this build. Refusing.`

That is §5's structural locator working exactly as designed -- it requires the anchor AND
the shape to agree, and our own patch broke the shape by design. **The consequence is a
workflow rule: always patch from a CLEAN client, and express the design cumulatively in
the recipe.** That is what this arc has done by accident so far; now it is a constraint
with a reason, and it is an argument for the recipe file being the versioned artifact
rather than a command line, since the recipe is the only thing that accumulates.

It also means a reskinned client cannot be inspected with `--attrs` or `--show`. Read the
clean build for that; the patched one is an output, not a source.

### 19.7 The primary marker moved off the host (2026-08-13)

Harness `20260813T225039`. Ritualist's own primary is attribute 36 (Spawning Power);
`stormcaller.toml` now puts it on **26** -- the row claimed off the reserved profession 11
-- so the primary belongs to our profession rather than being inherited.

Verified in the BYTES of the patched binary, which is where this claim lives:

| attr | name id | |
|---|---|---|
| **26** | 100355 `Tempest` | **PRIMARY** |
| 32 | 100356 `Galecraft` | |
| 33 | 100357 `Windward` | |
| 34 | 100358 `Thunderhead` | |
| 36 | 100354 `Storm Calling` | *(marker cleared)* |

**Exactly one primary**, which is the check that matters: `--attr-primary` is symmetric on
purpose, because a profession with two primaries is a state the client never ships.

**The panel is visually IDENTICAL, and that is the predicted result rather than a
disappointment.** WIKI (GWW, "Attribute" §Primary and secondary attributes) describes the
primary as a MECHANICAL property -- "effects beyond the linked skills", and unavailable to
a character who takes the profession as secondary -- and describes no panel marker. The
list sorts by attribute id, so the order does not move either.

**What the run actually tested** is therefore not the picture: it is whether the client
ACCEPTS a primary marker on a row ArenaNet ships as a profession-11 spare. It does --
loaded clean, `RUN VERDICT: PASS`, no error dialog. A state the client never ships itself
turns out to be one it tolerates.

**What moving the marker does NOT buy: the inherent passive.** Every shipped primary
carries an effect beyond its skills -- Strength adds armor penetration, Energy Storage adds
maximum energy, Soul Reaping gives energy on a nearby death. Moving the marker moves the
marker. Whether a CUSTOM passive is reachable is a different question and is under
investigation; the architectural hinge is that Guild Wars is server-authoritative for
combat and **we are the server**, so any passive the retail client does not itself compute
is ordinary server work rather than a patch.


---

## 20. Custom primary PASSIVES are server work (2026-08-13)

Eleven agents, five lenses each attacked by a skeptic, no client launches. The owner's
question was whether a custom profession could carry an inherent primary effect the way
every shipped one does -- Strength's armor penetration, Soul Reaping's energy on a nearby
death, Energy Storage's larger pool.

> **All nine effect shapes are SERVER work. No code cave, no hook DLL, no patched
> instruction -- for the mechanic.**

### 20.1 The two structural results that carry it

**No client code outside the UI can read an attribute rank.** Seven accessor wrappers,
**27 direct callers and 0 stored references**, and every caller is an Attributes panel,
build-template, PvP-equipment, skill-list or tooltip module. **And there is no
per-profession dispatch table**: an `FF /2` SIB-disp32 sweep of `.text` finds **0** real
sites against an `FF /4` control finding **1,278** genuine switch tables. The control is
what makes that absence a measurement rather than a failed search -- this project's
recorded failure mode is a confident zero from the wrong range.

**The client's whole health/energy arithmetic is one `fmul` against a maximum we also
set.** The float dispatch has nine non-default arms and every one is `fld [esi+0x24]`
(max health) or `fld [esi+4]` (max energy), `fmul` the wire value -- or a raw absolute.
Damage arrives RESOLVED: there is no armor term anywhere on the path, and **armor
penetration has no wire representation at all**. Critical is a wire FLAG (property 17's
body is `push 1` where 16's is `push 0`), not a client roll. Fast Casting's activation
time is REPLACED wholesale by property 61 in absolute seconds, with no multiply on that
path.

So a custom passive is ordinary server code: decide the number, send the property we
already send. **We are the server, and the client only ever displays what it is told.**

### 20.2 The one genuine client-side cost was TEXT, and it was unpaid

`s_attrib` rows carry a DESCRIPTION at row+0x0C. `reskin.py` parsed that field from its
first day and **never wrote it**, so section 19.7 shipped a profession whose attribute
rendered our authored name `Storm Calling` above ArenaNet's string 2147, which explains
Spawning Power's inherent effect -- an effect our profession does not have.

That matters more than a cosmetic gap, because of 20.1: since the passive itself is
server code, **the description is the only place a custom passive is ever announced to
the player, and the only part of one that lives in the client at all.**

Fixed: `--attr-desc`, plus recipe support, plus three checks in `test_reskin.py`
(51 green). The load-bearing one is not that the flag exists but that the write **moves
nothing else in the row** -- an offset slip lands on `primary` at +0x10 and silently
gives a profession two primaries, a state the client never ships.

All five descriptions are now authored, records 7-11 (ids 100359..100363), and the
primary announces a real effect -- id 100359, "For each rank of Tempest, you gain 2
Energy whenever a nearby creature dies." Resolved from the run archive through
`textrec`'s own reader, which walks the same pointer array the client does
(`0x00BF0210`, located structurally).

### 20.3 Status, stated precisely

| | |
|---|---|
| desc field written in the binary | **OBSERVED** -- 5 `attr-desc` edits, 17 dwords, length unchanged |
| the strings resolve from the archive at those ids | **OBSERVED** -- `textrec --dat`, file 98 records 7-11 |
| the client loads and runs with all of it | **OBSERVED** -- `RUN VERDICT: PASS`, no error dialog |
| **the description RENDERS on screen** | **UNVERIFIED** |

The last row is honest rather than cautious: attribute descriptions are TOOLTIPS, shown
on hover, and the harness drives keys rather than a hovering mouse -- so no frame in this
run could contain one. The names above them do render (19.5) out of the same file, which
makes the descriptions very likely; likely is not measured. One hover settles it.

### 20.4 The cheapest demonstration, not yet run

Implement the passive the tooltip now claims: **2 Energy per rank of Tempest when a
nearby creature dies.** Every piece already exists -- the server owns the death event
(`EFFECT_DEAD`, sent by us), and the dive names the two messages: float property **52**
for the floating "+N" and float property **33** to move the bar, because 52 alone draws a
number and refills nothing.

Two hazards to respect, both crashes rather than bugs: `CharPool.cpp:98 range > 0` means
int property 41/42 = 0 kills the client (and a NEGATIVE passes the `test edi,edi` guard
unchallenged), and `CharPool.cpp:84 fraction <= 1.0f` means float property 33/34 above
1.0 kills it.

**One correction this dive makes to another arc, recorded and NOT acted on:**
`studies/skillcast/FINDINGS.md` section 16.2 infers a property ordering from
`agent+0x124`, a field with no reader on that struct while its neighbours +0x11C and
+0x120 both have one; ArenaNet's own wire says parameter-before-trigger, **11 of 11**
with no counter-examples. That is another arc's document and this session did not
re-derive it, so it is flagged here rather than edited there.

---

## 22. THE PROFESSION GLYPH IS FOUND (2026-08-14)

**The last wall in this arc is down.** It had been NOT FOUND since `FINDINGS.md` and had
survived **three** independent bounded searches. It fell to a fourth pass with four
parallel angles, and the reason it had survived is worth more than the address.

### 22.1 The answer

**MEASURED**, pinned client `2026-07-29_221c13772c7a` against `vault/dat_study/Gw.dat`.
Every line below was re-verified byte by byte by the orchestrator, not taken from the
agent that found it -- and the first attempt at that re-verification FAILED, in the exact
way the finding predicts (see 22.2).

| | |
|---|---|
| Named at | `.rdata` VA `0x00959964` (file offset `0x558964`) |
| Stored as | the pair `{id0 = 0x573D, id1 = 0x0102}` -- **not** a raw file id |
| Decodes to | file id **152638** (`0x2543E`) via `mapchunks.dependency_file_id` |
| Resolves to | **MFT row 12032**, stored 35,460 B compression 8 |
| Which is | a **`DDS ` 256x128, 32 bpp**, masks `R=0x00FF0000 G=0x0000FF00 B=0x000000FF A=0xFF000000`, 131,200 B decompressed (128 B header + 131,072 B pixels, exact) |
| Laid out as | **8 x 4 cells of 32x32** = 32 frames |
| Of which | **22 are distinct.** Cells 22-31 are byte-identical copies of 20 and 21 |
| Selected by | `0x005A5A14 cmp eax, 0xB / ja <assert>`, then `jmp [eax*4 + 0x5A5EB8]` |
| Owned by | `P:\Code\Gw\Ui\Game\Vendor\VnProfessionButton.cpp` -- ArenaNet's own `__FILE__`, loaded at both bracketing asserts |

**The 12-entry jump table at VA `0x005A5EB8`, read out of the bytes.** Each arm is a
`mov eax, imm32` naming the EVEN frame; a `0/1` state bit is then added, and every odd
frame is measurably dimmer than its partner (luma ratio **0.687-0.788**, 11 of 11), so
the pair is lit/unlit:

| prof | 0 None | 1 W | 2 R | 3 Mo | 4 N | 5 Me | 6 E | 7 A | **8 Rt** | 9 P | 10 D | 11 (oob) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frames | 20/21 | 0/1 | 2/3 | 10/11 | 8/9 | 4/5 | 6/7 | 12/13 | **14/15** | 18/19 | 16/17 | 20/21 |

**The sheet position is NOT the profession id** and nothing about the layout suggests
otherwise -- Monk is at frames 10/11, Mesmer at 4/5. Anyone arming a cell from the
sheet's reading order rather than from this table will paint the wrong profession. One of
the four agents did exactly that and was corrected against these bytes.

**Profession 8 (Ritualist, our host) is frames 14/15 = cells (col 6, row 1) and
(col 7, row 1)** -- the teal eye. Consistent with the emblem Guild Wars actually draws
for Ritualist, which is a check the code reading could have failed and did not.

Two properties fall out of ArenaNet's pixels rather than out of the disassembly, so they
could have refuted it:

- **The 22-frame count is recoverable from the archive alone.** Exactly 22 of 32 cells
  are distinct, and the ten repeats are cells 22-31 duplicating 20/21 -- the `None` pair,
  reused as padding. Under a **column-major** walk the unused set would be a different
  set of cells entirely, so **column-major is refuted by the data**, and the row-major
  reading is corroborated by a source the code did not impose.
- **The jump table's out-of-range arm (index 11) points at 20/21**, the same pair as
  `None` -- which is why cells 20/21 are the ones replicated.

### 22.2 Why three searches failed, and it is a reusable correction

**The client NEVER stores a raw u32 file id.** It stores a `{u16 id0, u16 id1}`
dependency pair. Every sweep this project ran for "a run of consecutive dwords that all
resolve through the archive's file-id table" was **structurally blind to every texture
reference in the image** -- not unlucky, blind.

That is not a hypothetical: this session ran two such sweeps hours before the answer
landed and recorded both as negatives (a contiguous sweep, then a strided one over 19
strides). Both were correct about what they measured and both were measuring a byte
pattern that does not occur. **And the orchestrator's own first verification of the
finding repeated the mistake** -- it read `0x00959964` as a dword, got `0x0102573D`,
failed to resolve it, and only then read it as the pair the finding had just explained.
Being told the mechanism was not enough to stop it being applied wrongly one command
later, which is why it is written here at the top rather than as a footnote.

**`FINDINGS.md`'s note on this widget was one clause wrong, and that clause closed the
question for the whole arc.** It recorded that the Vendor control drives its icons from
shared static image lists *"rather than an archive-resolved file id"*. The switch is
real and the image list is real -- but the **list is built at run time from an archive
file id sitting in `.rdata`**. The two halves are at different layers, and the arc's own
question ("archive-resolved **or** a compiled-in image list?") was a false dichotomy that
made the true answer unsayable. It is both.

### 22.3 What it costs to author, and the one thing that is not free

The format half was already closed. What is new is that the glyph is **one shared sheet**,
not eleven per-profession files -- so authoring a custom glyph is a **partial overwrite of
a 32x32 region** of row 12032, leaving the other ten professions' cells untouched.

**It does not fit in place.** The row is stored compressed at 35,460 B (reservation
35,840 B) and the decompressed sheet is 131,200 B, needing 131,584 B. This repo has no
compression-8 encoder, so the write must go out **stored**, which is a **relocation**:
`datmove`, which is proven (`crossbuild` §4b, §4c) and journalled. That is the whole
extra cost, and it is a cost rather than a blocker.

**Still UNVERIFIED:** that this sheet is the only surface a profession emblem appears on.
It is the `VnProfessionButton` sheet -- MEASURED as its sole consumer in this image -- but
whether the character panel, party search or hero panel draw from the same row has not
been checked, and our loopback server may not be able to render any of them. The
character-creation screen definitively does **not** use it: `CrProfession.cpp` has its own
ten-entry table at VA `0x0094B470` of 128x512 `ATEX DXT5` art banners, a different asset
class in different rows, found by the same pass and ruled out as the glyph by the agent
that found it.

### 22.4 OBSERVED (2026-08-14): the Stormcaller emblem is on screen

**The glyph is authored.** Harness `20260814T084922`. The retail client drew an emblem this
project drew from arithmetic, in the profession button row, beside nine of ArenaNet's own.

```
  W      R      Mo     N      Me     E      A      Rt     D      P
shield  paw    ankh   skull  hand   flame  daggers BOLT  crescents disc
                                                   ^^^^
                                                   ours
```

**The write.** `emblem.py` draws a 32x32 BGRA lit/dim pair -- a forked violet bolt over a
swept wind arc on a recessed socket. Those two cells were spliced into the sheet and the
result asserted before anything was written: **exactly cells 14 and 15 differ, the header
is byte-identical, and the other thirty cells are unchanged.** So the nine other
professions in the screenshot are in-frame controls that the write could have damaged and
did not.

Provenance: every pixel is ours. The disc, rim, recess and bolt are arithmetic; **no byte
of ArenaNet's art was read, sampled or averaged, not even the socket colour**, which was
the obvious shortcut. What was taken from the sheet is geometry and ratios -- 32x32 BGRA,
an alpha disc of 725 opaque / 131 partial / 168 clear texels, and the lit/dim luma band
0.687-0.788. Ours measures 732 / 80 / 212 and 0.720, inside the band.

**It needed a relocation, as predicted.** Row 12032 ships compressed (35,460 B, reservation
35,840) and we write stored at 131,200 B, so `datwrite --replace` cannot fit it.
`datmove` moved it `0x4E8F7E00 -> 0xA818400`, journalled: **0 overlapping row pairs
afterwards, all three checksum rules hold, `datcheck --preflight` 10 of 10.** This is the
first time in the project that a relocated row has been read back by a client on a
non-map asset.

### 22.5 Getting it on screen took three runs, and the reason is worth keeping

The glyph's widget is `VnProfessionButton`, built by a vendor frame. That frame opens from
**one s2c message** -- no NPC, no interact, no click -- which is what made this observable
at all. `0x00C3` carries `{byte, dword}` and the **byte is the service selector**:

| run | sent | OBSERVED |
|---|---|---|
| `20260814T084423` | `0x00C3:2=12` (the DWORD) | the account-name dialog -- **prediction failed** |
| `20260814T084804` | `0x00C3:1=12` (the BYTE) | `VnTradeBuy`. Right frame, but its list is empty and it draws **no** profession row |
| `20260814T084922` | `0x00C3:1=16` | **`VnUnlockSkill`** -- ten profession buttons, and ours among them |

Two corrections fall out of that. The recon named the service value correctly
(`TRADE_BUY = 0x0C`, `UNLOCK_SKILL = 0x10`) and the field wrongly, and a whole run was
spent on the dword; the schema said `{byte, dword}` all along and a byte-sized enum
belongs in the byte. And **`VnTradeBuy` was the wrong creator to aim at** even once the
field was right -- it builds eleven buttons per the disassembly, but with an empty item
list it renders none, so the panel that proves the mechanism is the SKILL UNLOCK one.
A reader planning a fourth run should aim at service 16 and nothing else.

**Still UNVERIFIED:** whether any other surface draws from row 12032. It is this sheet's
sole consumer in this image (MEASURED), but the character panel and party search were not
reachable to check, and the party roster is text (18.14) rather than a glyph.

---

## 23. EVERYTHING AT ONCE (2026-08-14): the arc, in one frame

Harness `20260814T090803`, `hold005.png`. One retail client, one screen, and every
authored layer of the arc visible together:

| layer | what is ours | run |
|---|---|---|
| The ground | **Sculpted Vale**, map 143, 64x64. Terrain round trip 4,096/4,096 samples exact, 8 props, **91.87% generated** against 770 B borrowed | 23 |
| Profession name | **`Profession: Stormcaller`** in the Skills panel | 19, 22 |
| Attributes | **Tempest, Galecraft, Windward, Thunderhead, Storm Calling** -- all five authored, all five owned by profession 8 | 19.5 |
| Skill icons | the bar, drawn from arithmetic | M7 |
| **The glyph** | the button row -- our violet bolt at frames 14/15, selected, beside nine of ArenaNet's | 22.4 |

Nothing on that screen is ArenaNet's text or ArenaNet's art except the nine control
emblems and the borrowed structural constants, and both are named.

### 23.1 A second consumer of the profession name, found by the owner clicking it

The `VnUnlockSkill` panel's list heading reads **`Stormcaller Skills`**. That is
`s_charProfession[8]` on a surface this arc had not seen it on -- 19 and 22 knew the
Skills-panel heading and the party roster, and nothing predicted this one. It also
demonstrates, on screen rather than by inference, that **the glyph button and the name
resolve the same profession id**: clicking our emblem selected the profession the client
itself then named Stormcaller.

### 23.2 The panel said WARRIOR first, and the reason is worth writing down

The first attempt at this frame produced `Profession: Warrior` over Strength, Axe Mastery,
Hammer Mastery, Swordsmanship and Tactics, with the reskin patch fully applied and
correct. **The reskin repaints profession 8. The panel displays whatever profession the
SERVER told the client the player is**, and the spawn burst was sending Warrior because
`--spawn-profession 8` was not passed. Nothing was wrong with any patch; the run was
asking the wrong question and would have looked like a failure of the whole tier.

That is the same shape as this arc's other expensive mistakes: a correct artifact
measured through a wrong fixture. It is cheap to avoid -- **any run meant to show the
profession must carry `--spawn-profession 8`** -- and it was caught only because the
owner read the panel and said so.

### 23.3 The two-run sequence, which is not optional

`deploy --install` arms the map head to zero so the client is forced to recompile, so at
the moment the server starts there is no mesh to read; and once the client is up it holds
the archive exclusively. **The run that produces the mesh can never serve it**
(`deploy.serve_run`). Both runs need `RURIK_DAT` pointing at the client's own archive, or
`contentids.preflight` refuses the launch -- which it did here, correctly, naming row
71496 as 9,284 B in the server's archive and 0 B in the client's. Sequence:

```
deploy.py --area sculpt --dat <run>/Gw.dat --install
RURIK_DAT=<run>/Gw.dat session.py --exe <run>/Gw.exe --hold 25 \
    --game-args='--map 143 --area sculpt'                      # client compiles
RURIK_DAT=<run>/Gw.dat session.py --exe <run>/Gw.exe --keep-open --hold 300 \
    --game-args='--map 143 --area sculpt --spawn-profession 8 --probe smsgsweep'
```

Row 71496 read 0 B before the first run and **6,012 B** after it, with our authored
10,714 B Stripped map in the partner row -- so the client compiled our geometry and the
server then pathed against it.
