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
