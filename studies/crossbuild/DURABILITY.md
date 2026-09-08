# The archive-durability experiment — armed 2026-08-13, prediction stated first

> **⚠ Imported 2026-08-14 from `claude/studies-crossbuild-plan-e32afb`, which sat
> unmerged from 2026-08-13 while `main` continued this same arc. It is the BRANCH's
> durability record, kept because the tooling it describes was cherry-picked with it.
> Where this file and [FINDINGS.md](FINDINGS.md) disagree, **FINDINGS.md on `main` is
> the live record** — it carries eleven further commits, including the play-session
> durability result of 2026-08-13/14 and the `RESOLVED` annotations this file predates.
> One thing it gets RIGHT and is worth keeping: §3.2's `entries[i].index == i + 1`. The
> claim `main` retracted (in `d135f8d`, "there was never a second convention, and I
> invented one") was FINDINGS.md §4b.1's inference that `archive.py` and `datcheck.py`
> number rows differently — they do not, and this file never said they did.**


**This is a trap set before the event it measures.** `studies/crossbuild/PLAN.md` §9 is the
one deliverable of that arc which cannot be finished on demand: it needs an ArenaNet content
patch to land, and the *before* state has to exist first. The house rule is that a probe
states its prediction before it runs, because a probe with no stated expectation can be
rationalised into agreeing with anything afterwards. So this file is written now, and
nothing below may be edited once the update lands — corrections go underneath, dated.

**Labels** are [studies/character/FINDINGS.md](../character/FINDINGS.md)'s, plus **MEASURED**.

---

## 1. The question, and the two parked ones it unblocks

What does an ArenaNet **content patch** do to a row we authored? Nobody knows. What *is*
known is one step short of it — `studies/datwrite/FINDINGS.md` §6: a `Gw.dat` write survives
a full **play session** unrepaired, and the allocator has only ever been observed relocating
the client's own scratch rows (8315/8316 moved, 8315 grew 92 → 96 B). MEASURED, n=2.

Two questions depend on the answer and are both explicitly parked:

- **Is a custom area durable or per-build?** `studies/customarea/FINDINGS.md`:756, :1229,
  :1952 — asked three times. §16-P10 partly closes it in the study's favour at :1954 (an
  identical struct layout at a relocated VA), but :1961 leaves the accepted chunk versions
  unchecked, and that is the decisive half.
- **The 29 of 171,025 file ids carrying bit 31** — a stale/needs-refresh watchlist the client
  cleared on two entries in one session. `studies/datwrite/FINDINGS.md`:589 calls it a
  durability signal nobody has pulled on.

---

## 2. THE DELIVERY PROBLEM — read this before trusting the arming

**An inert copy in the vault will never receive an update, so the trap as `PLAN.md` §9
describes it cannot spring on its own.** This is a defect in that plan's step 4 ("let the
update land on that copy"), and it only becomes visible when you try to do it.

The updater updates the archive **the client it belongs to opens**. `RUNBOOK.md`:740-757
records exactly this from the other side: `run-live/` has its updater ENABLED — it must, or
a live session cannot stream map content — and *"a live run writes new content into its own
`Gw.dat`"*. `run/`, the loopback build, has the updater killed on purpose and its archive
therefore drifts behind.

So there are three ways to actually run this experiment, and they are not equivalent:

| Route | What it measures | What it costs |
|---|---|---|
| **A. Arm `vault/run-live/…/Gw.dat`** | the real question: our authored row, in the archive a live, updater-enabled client opens | a live session runs against a MODIFIED archive. That is an owner decision, not a tooling one — it touches the account-safety posture `PLAN.md` §6.2 governs, and it needs the harness |
| **B. Arm the scratch copy, then point an updater-enabled client at it** | the same thing, one step removed | assembling a run directory around the armed copy, plus the same live-session decision |
| **C. Retroactive, on ArenaNet's own rows** | what a patch does to *rows in general* — relocation, recycle, delete, sibling relink — but **not** to a row we authored | nothing. Both builds' archives are already vaulted. See §5 |

**What is armed below is route A/B's *payload*, staged on a scratch copy.** It is deliberately
not placed in `run-live/`: that is the decision the owner has to make, and arming it silently
would be making it for them.

---

## 3. What was armed — MEASURED 2026-08-13

Working copy: `vault/dat_durability/Gw.dat` (4,198,489,600 B), cut from
`vault/dat_study/Gw.dat`. Never `C:\gw` (the owner's install, refused by `datwrite`) and
never `vault/dat_study` itself (the source snapshot every other copy is cut from, also
refused). Both refusals were relied on rather than tested here; `test_datwrite.py` owns them.

| | |
|---|---|
| Baseline | `before.json` — 177,342 rows, descriptor counter 26881, MFT sha256 `e73ada6c91ef7309` |
| Tracer | row **46196**, 784 stored bytes at **`0x437F6800`** |
| Marker | `RURIK-DURABILITY-20260813`, 25 bytes at the tail (offset 759) |
| Stored sha256 | `06dfc3c1ddcdddb8` → `a81578c51d634208` |
| MFT row crc | `0xAF51D329` → `0xB05C4ECC` |
| Journal | `armed.journal.json` |
| Identifiers | `ARMED.json` — in the vault, because it names archive contents |

**The archive still passes all ten of the client's open-time rules after arming** (`datcheck
--preflight`, 10 of 10 clear), and `--diff` against the baseline detects it and exits 1.

**Reversibility is proven, not assumed.** The tracer was reverted and re-armed during this
session: after `datwrite --revert`, `datcheck --diff` exited **0** — byte-identical to the
pre-arm baseline. `test_datwrite.py` already asserts revert against a built fixture; this is
the same claim against the real 4.2 GB archive.

### 3.1 This copy is a TRACER, not a playable archive

The marker overwrites 25 bytes of a **compressed** stream, so map 46196 will not decompress.
That is fine for measuring whether the row survives an update and **not** fine for handing to
a client. If the owner takes route A or B, the tracer must be re-made as something a client
can load — an authored map via `mapbuild`, not a corrupted row — because a live client
opening this archive and loading that map is an unnecessary crash.

### 3.2 Two things this turned up

**`archive.py` and `datwrite`/`datcheck` disagree about where row 46196 is, by 1024 bytes.**
`datwrite` wrote at `0x437F6800` and `datcheck --diff` reports the row at `0x437F6800`, so
those two agree; `archive.Archive().entries[46196].offset` reports `1132424192`, exactly 1024
higher. Caught because the first arming attempt seeded its payload from `archive.py`'s offset
and the read-back verification then found no marker there. The arm was reverted and redone
from the bytes actually stored at `datwrite`'s offset. **RESOLVED 2026-08-13, and it is not an offset bug — it is an OFF-BY-ONE INDEX.**
`archive.py` builds its entry list from `mft_offset + 24`, skipping row 0, so
`archive.entries[i].index == i + 1`: `entries[46196]` **is row 46197**. Measured on the pinned
build, `entries[46195].offset` equals `datcheck`'s row-46196 offset to the byte. `Entry.index`
is correct and `file_id_table()`'s use of `entries[1]` for row 2 is correct under this
convention; what is wrong is indexing the LIST by row number, which is the obvious thing to
do and what this session did. Worth a docstring line in `archive.py`, and worth checking any
caller that subscripts `entries` by a row index.

**`datcheck` classifies an in-place content change as `new extent (silent relocation)`.** The
diff above prints `before 0x437F6800 784B` and `after 0x437F6800 784B` — same offset, same
size, only the crc differs — and still labels it a relocation. Nothing relocated. That label
is wrong for this shape, and it matters for step 4 of §6, where the whole job is classifying
what an update did: a genuine relocation and an in-place overwrite would report identically.
The plan's own instruction to report **UNCLASSIFIED rather than force a shape** is the right
instinct and the Tier 1 table appears to be missing a shape for "same extent, new content".

---

## 4. THE PREDICTION, stated before the update

Stated in full so it can be scored, not hedged so it cannot.

**Primary prediction: the authored row SURVIVES a content patch untouched — same row index,
same reservation, same checksum — unless the patch itself writes to that row's file id.**

The reasoning, and it is an argument rather than a measurement, which is why this is a
prediction: an update is a content delivery, and the client's allocator has only ever been
observed relocating **its own scratch rows** (`datwrite` §6). A patch that rewrote unrelated
rows would have to walk the MFT re-laying files it did not change, which is work with no
purpose.

**Confidence: moderate.** The strongest reason to doubt it is §1's bit-31 watchlist — 29 file
ids the client marks stale and has been seen clearing. If an authored row's id lands on that
list, "untouched" is exactly what it will not be.

What each outcome would mean:

| Outcome | Implies |
|---|---|
| **Survives, byte-identical** | A custom area is a durable artifact, not a per-build one. The E3 and custom-area routes cost a one-time authoring step, not a per-update one. The strongest result available. |
| **Relocated** (same content, new row/offset) | Durable in content, not in address — which is what `mapchunks.py`:117 has said all along: *file ids are the portable key, a row index is meaningful only against the archive copy it was measured on.* Every tool that remembers a row index needs re-checking; every tool that remembers a file id is fine. |
| **Recycled or deleted** | A custom area is per-build. E3 and the custom-area route need a re-application step after every update, and that step belongs in `RUNBOOK.md` §"One-time setup" beside the client patch. |
| **Overwritten in place** (row survives, content is ArenaNet's) | The worst outcome and the one that would be silent: the archive still verifies, the row still exists, and the map is quietly theirs again. This is the case `datcheck --diff` exists to catch, and it is why the checksum is recorded rather than just the row index. |

**Predicted secondary observation:** the bit-31 count will CHANGE. 29 of 171,025 is a
watchlist, an update is exactly the event that would service it, and if it comes back 29 with
the same ids I will have learned something about what that flag is not.

---

## 4b. THE PREDICTION'S REASONING IS REFUTED — 2026-08-13, before any update

§4 stands as written above, because a prediction edited after the evidence is worthless. But
it must be read with this, and **the reasoning behind it does not survive.**

§5's retroactive diff ran, and two adversarial passes attacked what it seemed to show. Both
refuted it. The details are in §5.2 and §5.3; the correction to §4 is:

**"0.19% of rows changed" is the wrong denominator, and I used it wrong.** It measures the
fraction of *ArenaNet's live, allocated rows* that were disturbed. An authored row does not
live there. It lives in the archive's **scratch resources** — the erased MFT slots and the
free runs — which are exactly what the client's allocator works. Measured against the region
an authored row actually occupies, the update's disturbance rate is **79.70% by free block
and 2 of 2 by claimable row slot.**

**The revised prediction, and it is the opposite of §4's:** an authored row placed by
`datplan` is **more likely than not to be destroyed** by a content patch. §4's "survives
untouched" is retained above as the stated-first prediction and is now expected to be
**wrong**. What §4 got right is the *shape* of the outcomes and that the checksum, not the
row index, is the test; what it got wrong is the base rate.

---

## 5. The retroactive diff — MEASURED 2026-08-13

Both builds' archives are vaulted, so a real before-and-after pair across the update this
project lived through already existed. It has now been diffed.

```
rows 177,311 -> 177,335          descriptor_counter 26,548 -> 26,710
mft_offset 4,187,985,920 -> 4,173,266,432        mft_size 4,255,464 -> 4,256,040
TIER 1: 334 changed rows -- 308 relocated, 1 recycled, 1 deleted, 24 added, 0 UNCLASSIFIED
TIER 2: file-id records 170,999 -> 171,025, released_records 0 -> 1
```

**Scored against the predictions made before the run.** "Some UNCLASSIFIED" — **REFUTED**,
there were none; FINDINGS 18.5's Tier 1 vocabulary covered every change. "The §3.2
mislabelling will bite at scale" — **REFUTED**: all 310 changed body rows genuinely moved
offset, **zero in-place rewrites**, so the label was accurate on this pair. The gap is still
real (§3.2's synthetic case proves the classifier cannot tell them apart) but it did not
misfire here. "The bit-31 count will change" — **CONFIRMED**, 25 → 29.

Every figure above was re-derived independently from the two MFTs by a second reader that
shares no code with `datcheck`, and reproduced its 334 and its 308/1/1/24 split exactly.

### 5.1 What the update actually did, and it is not what "relocation" suggests

- **306 of the 310 changed rows are named by a *different file id* in NEW.** So "row N
  relocated" mostly means *a different file now lives at row N* — the row index was reused,
  not the file moved. This is `mapchunks.py`:117's point arriving as a measurement: a row
  index is meaningful only against the copy it was measured on.
- **The MFT did not migrate; the client re-laid its container ring.** NEW's live MFT sits at
  `0xF8BEFE00`, the exact address OLD's stale generation 26,175 occupied. The archive's entire
  growth — 1,992,472 B — is the overrun of **one** evicted live file (row 35300, 6,247,580 B)
  pushed to the tail, ending exactly at EOF.
- The MFT is **not** last in either build: OLD has a shadow generation after it, NEW has 14.7 MB
  of shadow generations plus one live row.
- Stride derives to 24 B from the data alone (the gcd of the two table sizes *is* 24), so
  +576 B is exactly +24 rows. +162 on the descriptor counter is 162 MFT commits.

### 5.2 REFUTED: the denominator, and the collision our own planner walks into

`datplan.free_rows()` on OLD returns exactly **`[35300]`** — the single claimable erased slot.
**The update recycled row 35300.** That is Tier 1's one "row recycled", and it is the row
`plan_insert` would have put an authored file in. The append branch collides too: with no
erased slot, `plan_insert` appends at row 177311, and NEW row 177311 is the first of the 24
added rows.

**It happened twice, and the second time was not an update.** NEW's one claimable erased row
is 35301; in `vault/dat_study/Gw.dat` — same build, after the owner's client ran it — row
35301 is taken and `free_rows()` returns `[]`. `datplan.py`'s own docstring already recorded
that from the other side, without anyone connecting it to durability.

And the payload region: of OLD's 137 usable free runs (4,571 blocks), NEW writes into
**3,643 blocks — 79.70%**, with the bias running against us (98.9% of blocks in runs >64
blocks, which is where a map-sized file would go).

**Two of two observable disturbance events consumed the slot `plan_insert` deterministically
claims.** n=2 is not a law, but it is not a coincidence to plan around either.

### 5.3 REFUTED: the trap as armed could not have told the outcomes apart

This is the more useful refutation, because it is about the instrument rather than the world.
Measured by injecting each of §4's four outcomes into a real snapshot and running `datcheck`'s
own `format_diff()`:

- **`datcheck` prints only the first 40 changed rows**, ascending. 300 of the 334 real changes
  sit below 46196, so the tracer prints at rank ~301 — inside `... 295 more`. **Row 46196
  appears in the printed diff under none of the four outcomes.**
- **"Relocated" and "overwritten in place" produce byte-identical output.** `classify_row`'s
  extent test cannot separate them. §4 calls one "durable in content" and the other "the worst
  outcome and the one that would be silent".
- **The exit code carries no information about the tracer**: all four outcomes exit 1, because
  the rest of the update changed 334 rows.
- **The trap was armed with the non-portable key.** `ARMED.json` recorded row index and stored
  offset and no file id, while 304 file ids changed row across this one update.

**Fixed 2026-08-13:** `ARMED.json` now records the tracer's file ids — **`0x22E2C` and
`0x1F2E6`** — and a readout warning. After an update, find the tracer by resolving those ids
to a row and reading that row for the marker; or grep the archive for the marker directly.
**Do not read the printed page.**

---

## 5.4 What can still be measured NOW, without waiting

~~Route C~~ — **RUN, see §5 above.** What follows is what it was, kept because the two
commands are still how you reproduce it: **both builds' archives are vaulted** —
`vault/client/2026-04-30_b174de1f2d8d/Gw.dat` (4,196,497,128 B) and
`vault/client/2026-07-29_221c13772c7a/Gw.dat` (4,198,489,600 B). They are a real
before-and-after pair across the update this project already lived through, and nobody has
diffed them.

```bash
python toolkit/mapdata/datcheck.py --dat <old>/Gw.dat --snapshot old.json
python toolkit/mapdata/datcheck.py --dat <new>/Gw.dat --diff old.json
```

That answers what a content patch does to rows **in general** — how many move, whether the
Tier 1 shapes (relocation, recycle, delete, sibling relink) cover what actually happened, and
whether anything comes back UNCLASSIFIED. It does **not** answer the authored-row question,
because no authored row existed then. Exit 1 means the archive changed, which is the
expected result and not an error.

**It was run**, 2026-08-13, and §5 is the result. The judgement that half this question did
not need an update turned out to be right and then some: it did not just characterise the
update, it **refuted the prediction's reasoning** and **found the trap unable to read its own
result**. Both are in §5.2 and §5.3.

---

## 6. When the update lands

1. **Do not accept it before** `python toolkit/updatecheck.py --before --snapshot` (exit 0).
2. Let it land on whichever archive route A or B put the armed row in.
3. `python toolkit/mapdata/datcheck.py --dat <copy> --diff before.json`. **Exit 1 means the
   archive changed and is a RESULT; exit 2 means it is too broken to have findings.** Do not
   conflate them — that distinction once cost a crash being reported as a moved row.
4. Classify every change by FINDINGS 18.5's Tier 1 shapes, and report **UNCLASSIFIED**
   rather than forcing a shape that does not fit.
5. Score §4's prediction in public, right or wrong, and record the bit-31 count beside it.
