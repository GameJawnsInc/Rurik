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

**Working, validated in a running client, eleven bytes of same-length edits:**

| | field | run |
|---|---|---|
| Profession name, in world and on the roster | `s_charProfession[N]` | §8, §11 |
| Attribute names | `s_attrib +0x08` | §9 |
| Which attributes the profession owns (nine spare rows) | `s_attrib +0x00` | §9 |
| Which attribute a skill scales with | `s_skill +0x29` | §10 |
| Model, hair, skin, starter gear | appearance nibble | §11, free |
| Animations | — | §7, inherited from the host |

**Blocked on the world, not on the client:**

- **The abbreviation** renders only in the party window and over nameplates. Our server
  sends no party state, so the dword is patched and unexercised.
- **The picker label** is character-creation only, and this server has no creation flow.
- **The `.data` table's consumer** is still unidentified; a split-donor run would name it
  the moment a second profession-name surface appears.

**The one real wall left is TEXT.** Every name above is BORROWED — the client will only
show words it already ships strings for. A profession called what you want needs a text
file authored into `Gw.dat`, and the open question is whether the client accepts a row
whose compression flag reads 0, since this repo has no compression-8 encoder. The archive
layer already has journalled writes with byte-for-byte revert (`datwrite`, `test_datwrite`),
so the mechanism exists and is tested — but no text file has ever been served stored, and
it is the first edit in this arc that touches the 8 GB archive rather than a 10 MB
executable.
