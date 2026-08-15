# Cross-build — the archive-durability tracer, and its prediction

Companion to [PLAN.md](PLAN.md). That document specifies rung 6 as *"Archive-durability
experiment — armed and documented with its prediction stated **before** the next update
lands"*. **The arming happened on 2026-08-13 and the documenting did not**, so for a day
this repo held a complete, byte-verified, reverted-and-re-armed experiment that
`studies/datwrite/FINDINGS.md` still described as unrun and that no file in either tree
referenced. Found by the 2026-08-13 recon survey
([studies/recon/FINDINGS.md](../recon/FINDINGS.md) §5.6); this document is the missing
half, and §3's prediction is what actually closes the rung.

Everything in §1 is re-verified from the bytes by this document's author rather than read
out of the experiment's own metadata, because a self-describing artifact agreeing with
itself is one witness counted twice.

---

## 1. What is armed — OBSERVED

`vault/dat_durability/Gw.dat`, 4,198,489,600 B, cut from `vault/dat_study/Gw.dat`.

| Fact | Value | How verified |
|---|---|---|
| Target row | 46196 | `ARMED.json` |
| Stored offset | `0x437F6800` (1,132,423,168) | read directly |
| Stored length | 784 B | read directly |
| Marker | `RURIK-DURABILITY-20260813`, 25 B at tail offset 759 | **read out of the file at that offset by this author** |
| sha256[:16] before arming | `06dfc3c1ddcdddb8` | `before.json` |
| sha256[:16] after arming | `a81578c51d634208` | **recomputed over the 784 B and matched** |
| MFT entry CRC | `0xAF51D329` → `0xB05C4ECC` | `armed.journal.json` |
| Pre-flight after arming | 10 of 10 of the client's open-time rules clear | `ARMED.json` |
| Revert | proven — reverted and re-armed the same day, `datcheck --diff` exit 0 after the revert | `ARMED.json` |

**The portable key is the part that took an adversarial review to get right, and it is the
transferable lesson.** The tracer was first armed with **row index + stored offset only**,
and `mapchunks.py:117` already says that identifies a row *only against the archive copy it
was measured on*. The one update actually measured moved **304 file ids to a different
row**, so a tracer identified by row alone cannot be followed across the very event it
exists to observe — it would have been unfindable by construction. `ARMED.json` now carries
the two file ids the row resolves to, **`0x22E2C` and `0x1F2E6`**, which is the identity
that survives. (A file id is archive *state*, not a property of the map — bit 31 means
`FcArchive` renamed that row away pending a replacement — so the pair is recorded rather
than one id; `toolkit/test_contentids.py` is the same fact enforced from the other side.)

**~~One offset disagreement is recorded rather than resolved.~~ RESOLVED 2026-08-14: there
was no disagreement.** This paragraph read `entries[46196]` as row 46196 and, when it landed
1,024 bytes past where `datwrite` and `datcheck` said row 46196 was, guessed at "a header or
block-base convention". `Archive.entries` is a **positional list that skips the descriptor**,
so `entries[46196]` is row **46197** — a different, 584-byte file that merely happens to sit
1,024 bytes later. MEASURED on `vault/dat_durability/Gw.dat`:
`entries[46195].offset == archive.row(46196).offset == 0x437F6800`, exactly `datwrite`'s and
`datcheck`'s number, and the 25-byte marker `RURIK-DURABILITY-20260813` is in **that** extent
and not in the other. All three readers agreed all along. See §4b.1's retraction; the same
misreading is still standing, unamended, in `vault/dat_durability/ARMED.json`'s
`offset_note`, where it tells the next operator a false reason for a true instruction.

---

## 2. What is already measured, before the update — OBSERVED

`diff-38519-to-38797.txt` is a full Tier-0/1/2 diff across a real ArenaNet update
(build 38519 → 38797), and it is the empirical answer to *how much does an update move*.
It is a result in its own right and it was also undocumented.

**Tier 0** — `descriptor_count` 177,311 → 177,335; `descriptor_counter` 26,548 → 26,710;
`mft_offset` 4,187,985,920 → 4,173,266,432 (**the table itself moved**, which is why a
reader that seeks to a remembered offset diffs the wrong bytes against themselves and looks
green — `test_datcheck.py` already pins that the MFT is located from a header read in the
same call); `mft_size` 4,255,464 → 4,256,040.

**Tier 1 — 334 changed rows of 177,335 (0.188%)**, classified by FINDINGS 18.5's shapes:

| Shape | Rows |
|---|---:|
| new extent (silent relocation) | 308 |
| row added | 24 |
| row recycled | 1 |
| deleted | 1 |
| UNCLASSIFIED | 0 |

**Tier 2** — `first_stream_rows` 132,604 → 132,628; `records` 170,999 → 171,025;
`released_records` 0 → 1; `rows_named` 132,604 → 132,628; the file-id table's sha256 moved.

**The line the file ends on is the one to carry:** *the entry CRC, the MFT self-CRC and the
header CRC all still verify across a relocation. They are not detectors.* This is the same
fact `test_datmove.py` was built around — two rows sharing blocks breaks an invariant no
checksum sees, because each crc is computed over its own row's bytes.

---

## 3. The prediction, stated before the update — RECONSTRUCTION

House rule: a probe states its expectation first, because one with no stated expectation can
be rationalised into agreeing with anything afterwards. Written 2026-08-13, before any
update has landed on this copy.

**PRIMARY PREDICTION: the authored row survives byte-identical, and the marker reads back at
the same file id.**

The reasoning, so a wrong prediction is diagnosable rather than merely wrong:

1. The measured per-update relocation rate is **308 of 177,335 = 0.174%**. A specific row is
   unlikely to be touched by chance, and row 46196 is **not** in the changed set of the one
   update measured.
2. After arming, the archive is **internally consistent** — `datwrite` recomputed the entry
   CRC, and all 10 of the client's open-time rules pass. Nothing the client itself checks at
   open time can distinguish this row from an untouched one.
3. `FcArchive` relocates for its own reasons (a replacement stream needs a bigger
   reservation, or the allocator recompacts), and none of those reasons references row
   content.

**The three refutation conditions, and what each would mean:**

| Outcome | Reading | Consequence |
|---|---|---|
| **Marker gone, row replaced with ArenaNet content** | The patcher holds an **external manifest** of expected content and repaired a divergence it detected. | The most consequential outcome. Every authoring route that writes into a live archive — E3 re-bloat, custom areas, the reskin's archive half — becomes **per-build and must be re-applied after every update**, and `studies/customarea`'s question (asked three times at :756, :1229, :1952 and never answered) is answered NO. |
| **Marker intact but at a different offset / file id** | A silent relocation, the 308-row shape. | Authoring survives an update but **row indices do not**, so every tool that remembers a row must resolve through the file-id table. Cheapest good outcome. |
| **Row deleted or recycled** | The 1+1 shape. | Authoring survives only where ArenaNet does not reuse the slot — usable but needs a post-update verification pass. |

**A fourth outcome nobody has named, and it is the one to watch for:** the marker survives
and the archive **fails the client's open-time gates afterwards**, because the update changed
something the armed row's reservation depends on. That is a *pass* on durability and a
*fail* on usability, and the two must not be conflated — `datcheck`'s exit codes already
carry the distinction (**exit 1 means the archive changed and is a result; exit 2 means it is
too broken to have findings**), and conflating them once cost a crash being reported as
"the row moved".

**Confidence: low, and deliberately stated as such.** The prediction rests on a single
observed update, and the mechanism that would refute it — an external content manifest — is
exactly the mechanism no measurement in this repo has ever looked for. The prediction is
worth stating because it is falsifiable, not because it is likely to be right.

---

## 4. As staged, the experiment cannot fire — OBSERVED

This is the finding the recon survey surfaced and it is not a detail.

**No file in either tree references `vault/dat_durability`.** `git grep` on `main` is empty,
and `archive.py`'s default reader is `dat_study`. The updater updates **`C:\gw`**, which this
project may never write to and which is not this archive. So the tracer sits on a copy that
no update will ever land on, and step 4 of `PLAN.md` §6's procedure — *"let the update land
on that copy"* — has no mechanism behind it.

**And it cannot simply be moved onto a playable archive**, because `ARMED.json` carries its
own warning: the tracer **overwrites 25 bytes of a COMPRESSED stream**, so map 46196 will not
decompress. It is a durability tracer, not a playable archive. Arming a playable copy means
choosing a row whose payload can absorb the write — or accepting one broken map.

**That trade is the owner's, not a session's**, and it is recorded in
[studies/recon/FINDINGS.md](../recon/FINDINGS.md) §8 LANE C item 1. The two shapes:

- **Arm a row whose stream is stored uncompressed**, so the marker is inert. Costs a search
  for such a row and possibly finds none of useful size.
- **Accept one broken map** on a copy that is otherwise played from. Costs a map, and risks
  the client asserting in a way that contaminates an unrelated session — which is precisely
  the failure `--enemy` was defaulted off to prevent.

Until one is chosen, rung 6 is **armed and documented but not deliverable**, and this
document says so rather than letting the green half imply the whole.

---

## 4b. The PLAY-SESSION half — RUN 2026-08-13, and the authored row survived

§4 says the update experiment cannot fire. The owner's answer was that a private server's
mods should simply be **rebased over an update**, which dissolves the update question —
re-applying is one command (`deploy.py`) and the journals make it reversible.

**What it does not dissolve** is the question `CLAUDE.md`'s own `test_datwrite` entry ends
on: *"what is still unmeasured is DURABILITY across a play session."* That one is sharper,
because the damage would happen **between** updates and no rebase helps. It is also far
cheaper — loopback, no owner decision — so it was run the same day.

**Method.** Three snapshots of `vault/run/2026-07-29_221c13772c7a-probe/Gw.dat`: pristine
(S0), after `deploy.py --area sculpt --install` (S1), after `--launch --hold 120` (S2). The
diff that answers the question is **S1 → S2**, isolating the client's writes from ours.

**PREDICTION, stated before the run.** (1) The authored row survives byte-identical — the
bit-31 mechanism at `datwrite/FINDINGS.md`:589 is a *stale/needs-refresh watchlist* and a
freshly written row with a correct crc should not be on it. (2) The archive changes anyway,
because the client rotates container generations. **(2) is the load-bearing half**: if
nothing changed, the client never wrote and the run is INCONCLUSIVE, not a pass.

**The arm made that vacuity control free**, which is a method point rather than luck: a
re-bloat arm zeroes the Bloated stream, so the client is *required* to write back. The
experiment stopped being "did the client happen to write" and became "does our row survive
a session in which the client demonstrably rewrote this very map".

**RESULT — both predictions held. OBSERVED.**

| | S1 (armed) | S2 (after play) |
|---|---|---|
| Authored Stripped row | `0x388A000`, 10,714 B, crc `0xEF793381` | **identical** |
| Bloated partner (zeroed by the arm) | `0x63C64200`, **0 B**, crc 0 | `0x3D80400`, **6,012 B**, crc `0xEDAE21C3` |
| `descriptor_counter` | 26,788 | 26,792 |
| MFT offset | 4,173,266,432 | 4,177,522,688 (**the table moved**) |
| Tier 1 changed rows | — | **3**, all *new extent (silent relocation)* |
| Tier 2 | — | **unchanged**, the directory invariant both ways |

The authored row had **relocated on install** (10,714 B did not fit its 4,608 B
reservation), the more fragile case, and still came back untouched. The client compiled from
it in the same session: 64 trapezoids from our terrain, height field **4,096/4,096 samples
exact**, environment (639 B) and sound (89 B) carried verbatim, all 8 props present, spawn
landing in exactly one trapezoid.

**So an authored row survives a play session in which the client actively wrote to the
archive.** The two other relocated rows (8315, 8316) are the client's own cache churn.

**Honest scope.** One session, ~120 s, one map, one client, one relocation. It does not
probe the bit-31 watchlist directly — our row is not on it — and says nothing about a
session long enough to trigger whatever rotation the 29-member set participates in. What it
retires is the strong form: *"the client may rewrite an authored row while you play"* is now
measured false for the ordinary case, rather than unmeasured.

### 4c. A second witness, 2026-08-14 — and the guard §4b never exercised

The skill-icon run (`studies/texture/FINDINGS.md` §9, harness `20260814T002445`) is an
independent repeat with three things different: a different archive copy
(`vault/run/reskin-roster/Gw.dat`), **three IN-PLACE replaces** rather than a relocation,
and skill-icon rows rather than a map. 70 s of play.

| | armed | after play |
|---|---|---|
| MFT offset | `0xF8FFF000` | `0xF8BEFE00` — **the table moved** |
| MFT entry count | 177,334 | 177,334 |
| rows 174150 / 174487 / 174861 | 2,068 / 2,068 / 8,212 B, compression 0 | **all three byte-identical** |

So the §4b result reproduces on the easier case as well: an in-place authored row survives a
session, table move included.

**THE TABLE DOES NOT WANDER — IT ALTERNATES BETWEEN TWO SLOTS, and the first draft of this
section had that wrong.** It read "the table moved 4.03 MB EARLIER" and made a point of the
*direction*, which implied a drift the evidence does not support. Every archive copy in the
vault was then sampled, and there are exactly **two** offsets across all seven:

| MFT offset | copies |
|---|---|
| `0xF8FFF000` | `run/2026-07-29…` (177,334), `run/…-c2` (177,341), `run/…-probe` (177,334) |
| `0xF8BEFE00` | `run/reskin-roster` (177,334), `run-live/…` (177,475), `dat_study` (177,341), `dat_c2` (177,341) |

**Copies with identical entry counts appear at BOTH offsets**, so the position is not a
function of table size — it is a phase. The four `row8295*.journal` files from the text arc
record the same two values and no others (`0xF8FFF000`, then `0xF8BEFE00` twice), i.e. this
copy has flipped at least twice. That is the shadow-container rotation `datplan` already
refuses free runs for — *"88.5% of `Gw.dat`'s free space is live container generations the
client rotates through"* — now OBSERVED on the MFT itself rather than inferred from the gaps.

The practical difference between the two readings is large. A drift is rare and bad luck; an
alternation means **the guard below should be expected to fire on roughly every other client
run**, which makes it a routine part of the procedure rather than an edge case. It also means
`0xF8FFF000` was not "where we left it" — our own `datmove` of row 8295 put the table there,
and the client put it back.

**What is new is the failure mode, and §4b could not have found it.** §4b compared
SNAPSHOTS; this run tried to `--revert` its JOURNALS afterwards, and all three refused:

> Every MFT edit here names an address that is no longer the table. Replaying them would
> write into dead space, restore nothing, and still leave the archive verifying — so the
> failure would be invisible.

That guard was written from `test_datcheck`'s reasoning that the table moves. **It has now
fired on real data**, and its description of the alternative is exact: a forced replay would
have written five MFT edits into abandoned bytes and left all three checksum rules PASSING,
which is a revert that reports success and restores nothing.

**The consequence for procedure: a journal is only good until the client next runs.** Revert
before launching, or accept that the row stays as armed. `datwrite` has no verb for the
explicit restore its own refusal recommends — `--replace` writes uncompressed and cannot put
a compression-8 payload back, and `--overwrite` is same-length only — so the three icon rows
above were **left armed on purpose**.

> **CORRECTED 2026-08-14, and this sentence used to be the reassurance.** It read *"with the
> original payloads still recoverable from the journals' `before` fields if anyone wants
> them"*. **No journal for those rows exists.** `datwrite`'s default journal path is
> `DAT.journal.json`, there is no such file beside that archive, and a grep of the **whole
> 45 GB vault** returns nothing mentioning row 174150. The claim was inferred from how
> `--replace` normally behaves rather than checked, and it is the kind of error that only
> surfaces when somebody needs the thing.
>
> **Two further things it got wrong**, both measured the same day: the armed set is **127
> rows, not three** (174150–175682, every one 2,068 B at compression 0 — the profession arc
> armed 124 more after this section was written), and row 174861 is 2,068 B rather than the
> 8,212 B recorded above, having been re-armed since.
>
> **The gap it named is now closed**: `datwrite --restore ROW --from DONOR` is the in-place
> grow `datmove.plan_move`:186 names and refuses. A pristine copy is a better source than a
> journal for exactly this reason — every checkout has one, and it cannot quietly go missing.
> All 127 originals are intact and identical in `vault/client/2026-07-29` **and**
> `vault/dat_study`, two witnesses.

### 4b.1 THE TRAP — RETRACTED 2026-08-14. There is one row convention and both tools use it

> **RETRACTION.** This section originally concluded *"the two tools number MFT rows
> differently, off by exactly one"*, labelled that cause **CORROBORATED**, and left the
> standing instruction *"never compare a row number printed by one tool against one
> printed by another"*. **All three are wrong.** `archive.py` and `datcheck.py` agree on
> every one of the 24 bytes of every row of every archive in the vault. The original text
> is kept below the line because the *shape* of the mistake is the finding, and because
> two later documents were written on top of the wrong version. `test_archive.py` §1c now
> measures the agreement in both directions on a real archive, so this can never again be
> settled by argument.

**What the bytes say**, re-measured 2026-08-14 on `vault/dat_study`, `vault/dat_c2` and
`vault/run/2026-07-29_221c13772c7a-c2`, all three agreeing:

| row | dat_study | dat_c2 (armed) | run copy (after play) | role |
|---|---|---|---|---|
| 71495 | 3,564 B | 3,564 B | 3,564 B | **stream partner of row 71493** — a different map |
| 71496 | 9,284 B | **0 B** | **6,452 B** | **stream head**, file ids `0x5CF20` / `0x287D3` |
| 71497 | 4,544 B | 21,926 B | 11,370 B | stream partner of row 71496 — our authored bytes |

So `--diff` naming **71496** and `deploy.py` naming **head 71496** were naming *the same
row*, correctly, in the same convention. 71496 is the Bloated head `deploy` arms to zero on
purpose so the client must recompile it; the size going 0 → 6,452 B is that recompile
working. Our authored bytes are in the partner, 71497, which is absent from the diff because
nothing touched it. **Both tools were right and there was never a disagreement to explain.**

**Every fact the original cited is true; only the inference is false**, which is the hardest
kind to catch:

* `archive.py[71495]` really is bit for bit what `datcheck` calls row 71496 — because
  `Archive.entries` is a **positional list that skips the descriptor**, so `entries[71495]`
  *is* row 71496 in both tools' numbering. A list subscript was read as a row number.
* `archive.py` really does "report 177,334 rows where datcheck reports 177,335" — because
  that is `len(entries)` against a row count. `Archive.row_count` is the comparable number
  and it is **equal on all ten archives in the vault**.
* `archive.py[2]` really is the MFT row — and so is `datcheck`'s row 3 and `archive.row(3)`.
  Same row. `MFT_SELF_ROW = 3` in both.

**The instruction is withdrawn.** Comparing a row number printed by one tool against one
printed by another is correct and always was. What is *worth* doing, and is now done, is
matching on the **file id** as well: `deploy.py` prints its file id on its own first line and
`datcheck --diff` now prints every row as `row 71496 [file id 0x5CF20, 0x287D3; stream head]`,
so the two outputs carry a token that a bare integer does not — and both verbs print the
convention above their numbers (`datcheck.ROW_CONVENTION`).

**What the wrong version cost, because the point is not the off-by-one:** it was written up
as a fact about the format and then *believed twice more*.
`vault/dat_durability/ARMED.json` carries a note calling the same subscript's 1,024-byte gap
"a header or block-base convention" and telling the next operator which pair to trust
(measured: `entries[46195].offset` **is** `0x437F6800`, the marker is in that extent, and
`entries[46196]` is row 46197 — a different 584-byte file); and §4 of this document repeated
it as an open question. A plausible explanation invented for an off-by-one is more durable
than the off-by-one.

`mapchunks.py`:117's lesson still stands on its own terms — a row index is meaningful only
against the archive copy it was measured on — and that is a fact about **copies**, not about
readers. `test_contentids.py` and `test_mapfile.py` moved to file-id identity for that
reason and were right to.

<details><summary>The original text, kept verbatim. Refuted above.</summary>

`datcheck --diff` reported **row 71496 changed from 0 B to 6,012 B** — and `deploy.py` had
just printed *"installing … head 71496, partner 71497"*. Read together those say the client
rewrote our authored row, which is the alarming result. **It is wrong.**

**The two tools number MFT rows differently, off by exactly one.** Verified empirically on
four adjacent rows by exact `(offset, size, crc)` triples: `archive.py[71495]` is
`0x3D80400 / 6012 B / 0xEDAE21C3`, bit for bit what `datcheck` calls row 71496. `archive.py`
reports **177,334** rows where `datcheck` reports **177,335**, and `archive.py[2]` is the MFT
row itself (`0xF8FFF000`, 4,256,040 B) — so its numbering begins one record earlier.
`deploy.py` prints in `archive.py`'s numbering; `datcheck` prints in its own. **Cause
CORROBORATED by effect and by the row-2 observation; the precise off-by-one site has not been
read out of both readers' code and is UNVERIFIED.**

The consequence is not hypothetical, because it happened here: the row `datcheck` calls
71496 is `archive.py`'s 71495 — **the Bloated partner the arm zeroed**, whose re-bloat is
the whole point of the experiment. Our row is `datcheck`'s 71497, absent from the diff
because it did not change. A reader comparing `deploy`'s row numbers against a `datcheck`
diff mis-attributes by one row, and the direction of the error is the worst available: **it
reads a successful re-bloat as the client having eaten your map.**

This is `mapchunks.py`:117's lesson from a new side. That comment says a row index is
meaningful only against the archive copy it was measured on; this adds that it is meaningful
only against the **reader** it was measured with. `test_contentids.py` and `test_mapfile.py`
both moved to file-id identity for the first reason, and the same fix applies here. Until it
lands: **never compare a row number printed by one tool against one printed by another.**

</details>

### 4d. What is left after 4b and 4c — and why this question got asked twice

**Play-session durability is CLOSED for the ordinary case**, on two witnesses that differ in
archive copy, edit shape and payload kind. It should not be re-opened as an open item, and on
**2026-08-14 it was** — by the same session that had run §4b the day before, which listed it
back onto its own next-actions list and started staging a third run before finding this
section.

The cause was not forgetfulness. `CLAUDE.md`'s `test_datmove` entry ended *"what is still
unmeasured is DURABILITY across a play session"* — the exact sentence §4b quotes as the
question it answered — and nothing updated it when the answer landed. That is this repo's
own opening rule arriving from a new direction: the top of `CLAUDE.md` says status lives in
`PLAN.md` §3 *"and nowhere else"* because three files once disagreed, and here a **result**
did the same thing. A cold session reads the house-rules file, not the study. Corrected
2026-08-14, in the entry itself rather than by adding a pointer. **The general form: when a
study closes a question that a suite entry states as open, the suite entry is part of the
deliverable.**

**What genuinely remains**, none of it blocking and none of it re-running the above:

1. ~~**Session length.**~~ **CLOSED by §4e-ter** the same day: 900 s produced **2** changed
   rows against 120 s's **3**, with the 29 unmoved and the authored rows byte-identical.
   Duration is the wrong axis — the churn is per RUN, not per minute. What is still unmeasured
   is **many sessions**, and a session that loads **many different maps**, which would exercise
   the allocator far harder than any run in this arc has.
2. **The bit-31 watchlist is unprobed**, and neither run could have probed it: our rows are
   not on it. Testing it means deliberately arming a row that *is*, which is a different
   experiment with a different risk profile.
3. **`datwrite` has no explicit-restore verb**, and that is a live state rather than a
   hypothetical — §4c left three skill-icon rows **armed on purpose** in
   `vault/run/reskin-roster/Gw.dat`, because `--replace` writes uncompressed and cannot put a
   compression-8 payload back and `--overwrite` is same-length only, while `--revert` correctly
   refuses once the client has moved the table. The payloads are still recoverable from the
   journals' `before` fields. This is the one item here with an owner.

**One dangling pointer was fixed alongside.** `vault/dat_durability/ARMED.json` cited
`studies/crossbuild/DURABILITY.md` twice — once in `why`, once inside the `NOT_PLAYABLE`
safety warning that says to read it *"before handing it to any client"*. **That file has never
existed in either tree** (the recon survey noted the same dangling name at
`studies/recon/FINDINGS.md`:304). Both now point at this document, §1 and §4. A safety warning
whose citation resolves to nothing is the half of a guard that does no work.

### 4e. The bit-31 watchlist across a play session — PREDICTION, stated before the run

**Why this run and not §4d item 1 on its own.** A long idle session is the weakest of the
three remaining items *by itself*: the arm forces one write at map LOAD, so everything after
the first ~30 s has nothing making the client write, and "nothing changed in minutes 2–15"
cannot separate *our row is safe* from *the client wrote nothing at all*. §4c's MFT
alternation fires per RUN, not per minute, so it does not fill the gap either. The bit-31 set
does: it is a population the client rewrites **unprompted**, which is exactly the liveness a
duration test cannot generate for itself. So the two are one run.

**What bit 31 is — already answered, and that is what makes this cheap.** `archive.py`:486,
read out of the client: `FcArchive` binds `id | 0x80000000` and **deletes the plain name when
it has requested a replacement** (`0x007D7B70`); `DnArchive` re-links the plain id once the
replacement is installed (`0x004766F0`). A bit-31 id means *this row's replacement is
pending*. **No arm is needed and nothing is left armed** — our side of this experiment is
read-only, which is also why it does not wait on §4d item 3.

**Why it is load-bearing on our own content**, rather than a curiosity about ArenaNet's cache:

- **Row 7982 is `donor_row` for all three `content/areas.toml` rows** — plaza, vale and
  sculpt every one of them — and it is named by **two** bit-31 ids, `0x8001B97D` and
  `0x8005E728`.
- **`0x8001B97D` is the recorded `file_id` of two `content/maps.toml` rows**, Ascalon City
  (Pre-Searing) and Lakeside County. If a session resolves that rename, the id our own
  content is written down under stops binding. This is the mechanism `test_contentids.py`
  already exists for, from the other side: `vault/run-live/` binds `0x1B97D` **plainly, to a
  different row**, and carries 9 bit-31 ids where the study copy carries 25.

**Census before the run**, `vault/run/2026-07-29_221c13772c7a-probe/Gw.dat`: **29 bit-31 ids
over 171,025 pairs**, MFT at `0xF8FFF000` (one of §4c's two slots), 177,335 rows. **Four land
on map-flagged rows** — 7982 and 20118, each named twice — which corroborates
`customarea/FINDINGS.md`:967's correction of "two" to **four** from an archive that file never
read. Eight further rows are named by two ids each; those are the aliases `datwrite` saw
zeroed.

**PREDICTION.**

1. **The authored rows survive byte-identical.** High confidence — §4b and §4c both. Fifteen
   minutes adds time, not new client behaviour, unless there is a periodic task nobody has found.
2. **The MFT alternates to `0xF8BEFE00`.** This is the liveness signal, and it is close to a
   coin flip: §4c measured the flip at roughly every other run. **If it does not fire, the run
   needs another liveness witness before any negative below may be reported.**
3. **NONE of the 29 clear.** This is the load-bearing prediction and it is deliberately the
   boring one: the two ids observed clearing did so across a **build update**, which is when
   new content arrives, and a loopback client **has no content source**. A replacement cannot
   install if nothing can deliver it, so the request should stay pending.
4. **The rival, and what it would mean.** If any bit-31 id clears on loopback with no content
   source, then the client resolves replacements from **local** content — generated or
   transcoded, which `datwrite/FINDINGS.md` labels RECONSTRUCTION either way — and bit 31
   becomes a **live hazard for our recorded file ids** rather than an update-time curiosity.
   That is the result that would change what `content/maps.toml` is allowed to store.

**What would make this INCONCLUSIVE**, stated now so it cannot be rationalised later: no MFT
move, no `descriptor_counter` advance and no bit-31 change, all three together, mean the client
wrote nothing and the run measures nothing.

#### 4e-bis. A cross-copy census taken WHILE the client ran — and it weakens prediction 3

Recorded separately and with its ordering stated, because it was gathered **after** the
prediction above was committed (`0e23b34`) and **before** the result: it is evidence, not a
revision. Ten vault copies, censused read-only. `run/-probe` refused with `PermissionError`,
which is itself the liveness witness — the client had the archive open exclusively.

| copies | bit-31 | id pairs | rows | `0x1B97D` |
|---|---|---|---|---|
| `client/2026-07-29` (pristine install), `run/main`, `run/reskin-roster` | **29** | 171,025 | 177,335 | renamed away |
| `dat_study`, `dat_c2`, `dat_durability`, `run/-c2` | **25** | 171,025 | 177,342 | renamed away |
| `client/2026-04-30` | 25 | 170,999 | 177,311 | renamed away |
| **`run-live`** | **9** | **171,138** | **177,476** | **PLAINLY** |

**The population is not constant and the count is not arbitrary**: 29 goes with 177,335 rows
and 25 with 177,342, so the copies that gained 7 rows are exactly the ones that lost 4 renames.

Diffing the SETS rather than the counts is what makes it a mechanism instead of a correlation:

- **Install → study: exactly 4 cleared, and they are TWO ROWS each named twice** — row 11957
  (`0x80022EB3`, `0x8005575D`) and row 177254 (`0x8005D4CA`, `0x8005EC1E`). That reproduces
  `datwrite/FINDINGS.md`:589's *"cleared bit 31 on two of them in place … and zeroed two
  aliases"* from the bytes, and adds what that account does not say: **neither row is a map
  row** — both are `flags 3`.
- **Install → run-live: 20 cleared**, including **both of row 7982's ids** (`0x8001B97D`,
  `0x8005E728`). Row 20118's pair survives, which is why that copy still shows 2 on map rows.

**This weakens prediction 3 and the honest thing is to say so before the result, not after.**
Prediction 3 leaned on *"a loopback client has no content source"*, and `datwrite`:585 already
records a clearing in a session where *"this content was not downloaded"* because the cage
blocked everything non-loopback. That was under-weighted when the prediction was written.

**The sharper, data-derived sub-prediction**, which the run can refute cleanly: the probe copy
sits at the pristine 29 and still carries all four of the loopback-volatile ids. **If anything
clears in this session it will be those four — rows 11957 and 177254 — and NOT the map rows.**
Row 7982's pair should require a real content source, which loopback does not have.

#### 4e-ter. RESULT — harness `20260814T100327`, 900 s unarmed. OBSERVED

The session ran the full 900 s in **our** world, which is asserted rather than assumed: the
server's own log reads `[map] navmesh 0x287D3: 1 planes, 64 trapezoids` and
`area 'sculpt': 3 of 3 placed`.

**The vacuity control passed first**, and it had to, because every headline below is a
negative:

| liveness witness | before | after |
|---|---|---|
| `descriptor_counter` | 26,792 | **26,795** (+3) |
| MFT sha256 | `4a8c691cc1285bde` | `8c9cac19feb6299d` |
| Tier 1 changed rows | — | **2**, both *new extent (silent relocation)* — 8315 (96 B → **92 B**, new crc) and 8316 (28 B, new crc) |
| archive lock | — | `PermissionError` on a mid-run read: the client held it exclusively |

So the client demonstrably wrote — it **rewrote and moved two rows** — and the negatives below
are about a session in which it did.

**RESULTS against the four committed predictions.**

1. ✅ **The authored rows are byte-identical.** Bloated row 71496, 6,012 B at `0x3D80400`,
   sha `284dca56…`; Stripped row 71497, 10,714 B at `0x388A000`, sha `f827165e…` — offset,
   size, crc and sha256 all equal on both. Third witness after §4b and §4c.
2. ❌ **The MFT did NOT alternate** — `0xF8FFF000` on both sides. §4c put the flip at roughly
   every other run and this run did not flip, which is unremarkable at n=1 but has a
   consequence worth carrying: **the alternation is not a usable liveness signal.**
   `descriptor_counter` is, it moved every time, and it is the one to check.
3. ✅ **NONE of the 29 cleared.** Population, rows, slots, offsets, sizes, crcs, flags and
   sha256s all identical — the diff prints *no change in the bit-31 population or any row it
   names*. Prediction 3 held, and it held **after** §4e-bis argued against it.
4. The sub-prediction was **not exercised**: nothing cleared at all, so "if any clears it will
   be rows 11957 and 177254" is untested rather than confirmed. Recorded as untested.

**This answers §4d item 1, and the answer is that duration is the wrong axis.** §4b held for
120 s and saw **3** changed rows; this run held for **900 s** and saw **2**. Seven and a half
times the session length produced no additional disturbance, no bit-31 movement and no
approach to the authored rows. The churn is **per run, not per minute** — which is also what
the MFT alternation's per-run cadence says. §4d item 1 is closed in its stated form; what
remains unmeasured is many SESSIONS, not one long one.

**And it puts `datwrite/FINDINGS.md`:585 into CONTESTED.** That passage attributes the
install→study clearing of 4 ids to a session in which *"this content was not downloaded"*
because the cage blocked all non-loopback traffic. The change is real — §4e-bis reproduces it
from the bytes — but **a controlled loopback session that demonstrably wrote to the archive
cleared nothing**, so "an ordinary loopback play session does it" is not supported. Either it
needs a specific trigger nobody has isolated, or many more sessions than one. n=1 against
n=1; what is now known is that the two disagree, and this is the only one of the two with a
before-census.

**The practical answer for our content.** `0x8001B97D` — the id `content/maps.toml` records
for Ascalon City (Pre-Searing) and Lakeside County, and one of the two names on the
`donor_row = 7982` every `areas.toml` row borrows — **did not move in a loopback session, and
does move in a live one** (§4e-bis: cleared in `run-live`, where `0x1B97D` binds plainly to a
different row). So the hazard is real, live-only, and already gated: that is exactly what
`test_contentids.py` refuses on, and this measurement is the first evidence for *when* the
state it guards actually changes.

**Honest scope.** One session, one map, one client, one archive copy. The negatives are only
as strong as the liveness witness, which is `descriptor_counter` +3 and two rewritten rows —
real, but small. A session that loaded many different maps would exercise the allocator far
harder, and no run in this arc has done that.

**Incidental, not chased**: the gamesrv log carries 10 × `navmesh does not cover` and 7 ×
`ignoring a … jump in the client's reported position` (largest 4,116 u, ours `(5950, 111)` vs
theirs `(1994, 1248)`). A server/client position disagreement on the sculpt map, which is 1.2%
walkable. Unrelated to durability and left for whoever owns movement.

---

## 7. THE UPDATE LANDED — build 38833, 2026-08-14. The tooling's first out-of-sample test

Everything above 38833 was built on **n=2**, two ArenaNet builds ~90 days apart, and every
stability claim in the arc said so. On 2026-08-14 ArenaNet shipped **38,833** and the owner
took it. This section is what the tooling did when it met a build nobody had measured.

**Provenance of the build number:** WIKI (GWW, "Game updates" §Update - August 13, 2026,
read 2026-08-14) gives `Build: 38,833` for a patch of an email-login crash fix, a Bird's
Eye Compass range increase and two map-reveal fixes. **MEASURED independently:**
`buildid.py` reads `38833` out of the image, from the getter at `0x004729E0`, 16 callers.
The wiki was not consulted by the reader; they agree.

**Procedure followed:** `RUNBOOK.md` §0 → §0b, exactly as written, which is the first time
that page has been walked on a real update. The before-state was captured at 17:58 UTC on
2026-08-14 with `--snapshot --dat` (`vault/updatecheck/before-20260814T175822.json`), the
owner then updated and closed the client, and `--after` ran at 22:14.

### 7.1 The result: derivation held, pinning broke, and the split is exactly where the arc predicted

| Tool | On 38833 | Anchoring |
|---|---|---|
| `sigcorpus.py` | **8 of 8 signatures at their exact expected hit counts** | byte shape |
| `buildid.py` | ✅ 38833, getter `0x004729E0`, 54 candidate shapes, one in range | byte shape |
| `asserts.py` | ✅ `single-routine=True`, callee `0x00487BC0`, 19,756 sites, consensus 100.0000% | derived, dual |
| `msgshape.py` | ✅ **25 tables derived, 751 declared, 666 usable, 2,420 cmd slots, 4 of 4 oracles PASS**, invariants over 1,754 descriptors | derived |
| `srctree.py` | ✅ runs | structural |
| `dump_dh_params.py` | ✅ **GO** — g=4, 512-bit prime, struct at VA `0x00A910D8` | byte shape |
| `genericvalue.py` | ❌ **REFUSED**: *"the switch site at `0x008129CC` is ... not a `movzx`/`jmp [table]` pair -- this build moved or restructured the switch"* | **raw VA** |
| `avevents.py` | ❌ blocked — its property map comes from `genericvalue.py` | inherits |

`msghandler.py --classify` also runs and returns **477 receive opcodes, NO_HANDLER 0,
241 forwarder / 236 body** — the same 477-of-477 non-null dispatch that
`studies/review`'s loopback-sweep prediction rests on, and the same split.

**Every tool this arc converted to derivation read the new build. The one class-(a) site the
arc left outstanding is the one that broke, and it took a second tool down with it.**
`PLAN.md` §8.0's next-actions list named `genericvalue.py`'s 32 addresses as an outstanding
job; that job now has a measured consequence rather than a hypothetical one.

**And it failed the RIGHT way.** `genericvalue.py` printed `CANNOT READ THIS BUILD ... This
is a finding, not a crash` and named the address. That is §6.1's "**Yes, hard** — byte
`verify` at the VA, raises on mismatch. **This is the model**" doing its job on a build it
had never seen. The gate is vindicated; what is missing is that only *some* of that module
carries it.

### 7.2 REFINED: "any patch anchored to a raw address is broken by the next build" is too strong

§2 of [PLAN.md](PLAN.md) carries that claim from the 38519 → 38797 gap, labelled
MEASURED / stated limit, n=2. **The third build refines it, and the refinement is not
reassuring — it is worse.**

38797 → 38833 is a **15-day bugfix patch and it moved almost nothing.** MEASURED, all on
the same pair:

| Anchor | 38797 | 38833 |
|---|---|---|
| `Gw.exe` length | 10,483,904 B | **10,483,904 B — identical** |
| build getter | `0x004729E0` | **same** |
| assert callee | `0x00487BC0` | **same** |
| DH struct | VA `0x00A910D8` | **same VA** |
| AgentView allocators | `0x007F2E90` / `0x007F5340` | **same pair** |
| `genericvalue` int-main switch | `0x008129CC` | **restructured** |

So raw addresses did **not** uniformly break. Most survived; one region moved. The honest
statement, and it should replace the old one wherever it is quoted:

> **Whether a raw address survives a build gap depends on the size of the patch, and
> nothing tells you which kind of patch you are looking at from the outside.** Addresses
> broke wholesale across the 90-day gap and mostly held across the 15-day one. A pinned
> tool is therefore not reliably broken by an update — it is *unpredictably* broken, which
> is the worse failure, because a tool that keeps working across most updates earns trust
> it cannot honour on the one that matters. Byte-shape anchoring survived **all three
> builds, 8 signatures, exact hit counts**.

The n is now **3 builds / 2 gaps**, and the two gaps are qualitatively different rather than
two samples of one thing. Do not average them.

### 7.3 The DH struct did not move; its CONTENTS rotated

MEASURED. Struct VA `0x00A910D8` on both 38797 and 38833 — the RVA `0x6910D8` that
`PLAN.md`:803 records as having moved from `0x6843E8` at the previous gap **stayed put this
time**. But the parameters inside it rotated:

| | 38797 | 38833 |
|---|---|---|
| prime fingerprint | `fccfed6d897593eb` | `69957c41e902a1b7` |
| server public fingerprint | `dc1b568d13a81438` | `a451d70af363653c` |

(Fingerprints only. The values are ArenaNet key material, live in `vault/keys/`, and are
never committed — `updatecheck.py` records the fingerprint for exactly this reason.)

**So "the DH parameters rotate with every build" survives its third test, and it is the
rotation that matters operationally, not the struct's address.** `RUNBOOK.md`'s rule holds:
a patched copy from last week keys to nothing.

### 7.4 Two defects the update exposed in the tooling built to handle it

**(a) `updatecheck.py --after` printed a vacuous pass about the new build.** Its one-page
advice ended:

```
Every signature in the corpus still resolves at its expected count -- the byte-shape anchors held.
```

directly beneath `The live install moved from build 38797 to 38833`. **It had not read
38833.** `capture()` collected `signatures` only for `pinned.BUILDS` — the *vaulted* builds,
which by construction cannot change across an update — and gave the live install only
identify/size/build. The line compared the old builds against themselves and printed a pass
about a build it never opened, in the one report whose entire purpose is to say what the new
build did.

This is the repo's own named defect — *a check that cannot fail is not a check* — in the
tool this arc built to catch it, on its first real firing, and it is the same shape as
`msgshape.py`'s `descriptor invariant violations: 0` over zero descriptors that opened the
arc. **FIXED 2026-08-14:** `capture()` now reads the corpus off `C:\gw\Gw.exe` itself and
stores `hits`/`expected`/`ok` per signature; `_advice()` reports the count from that reading,
names the build it read, distinguishes *no reading* and *read failed* from *pass*, and says
where it read. The claim in §7.1 above — 8 of 8 on 38833 — is that fixed path's output, and
was independently confirmed by running `sigcorpus.py --exe` directly first.

**(b) `RUNBOOK.md` §"One-time setup" step 3 omitted `--no-updater-patch`, and following the
page exactly produced a wrong live-capture build.** `make_custom_client.py` kills the updater
**by default**. That is right for the caged loopback build and wrong for `run-live/`, which
`RUNBOOK.md`:849 says must keep its updater *"or a live session cannot stream map content"*.
The page's step 3 named only `--no-dh-patch`, so the first 38833 live build came out
`updater=killed` beside 38797's `updater=LIVE` — a pair meant to differ only in build number.
Caught by `dhbuild.py`'s audit, rebuilt correctly, and the page is fixed.
**Left for a ruling, not resolved here:** `CLAUDE.md`'s launch-rule paragraph says the
updater kill switch is *"wanted on both configurations"*, which contradicts `RUNBOOK.md`:849.
The vault and the evidence agree with `RUNBOOK.md`; `CLAUDE.md` is a house-rules document and
this is the owner's call.

**(c) THE TWO-BUILD ASSUMPTION, and it is a pattern rather than a slip.** The cross-build
tests were all written when the vault held exactly two builds, and **four of them encoded
that number structurally.** Registering a third did not make them go red — it made three of
them *crash*:

| File | What it did | Why three breaks it |
|---|---|---|
| `test_avevents.py`:107 | `a, b = [set(i.allocators) for i in IMGS.values()]` | ValueError on 3 |
| `test_sigcorpus.py`:106 | `(_sa, pa), (_sb, pb) = sorted(PES.items())` | ValueError on 3 |
| `test_sigcorpus.py`:156 | the same unpack again, in §3 | ValueError on 3 |
| `test_msgshape.py`:111 | `EXPECT_ENTRY[stamp]` | KeyError, no 38833 row |
| `test_srctree.py` | `EXPECT_PATHS.get(stamp)` → `None` | **FAILED CLEANLY** — *"has no expected path count in EXPECT_PATHS: add one, measured from a real run — never from a guess"* |

`test_srctree.py` is the one that got it right, and the difference is worth copying: it
looks the build up with `.get()` and turns a missing expectation into a **named failure**
rather than an exception, because — its own comment — *"the registry is what other tools
consult to answer 'which builds do we cover', and an unmeasured build sitting in it silently
is the coverage gap this wiring exists to close."*

**And the deeper problem was not the unpacking — it was the CLAIM.** Three of these
asserted, in one wording or another, *"the addresses are different on the two builds"*, as
the proof that a locator derives rather than looks up. **38833 refutes that as a universal
without touching rule 2:** it shares `0x007F2E90`/`0x007F5340` with 38797 (AgentView
allocators), shares `0x007DE010` (RegisterMsgs), and shares SIG_KEYS' and SIG_MUTEX's
addresses outright, because that gap did not move the code. Read literally, the old checks
say a derivation that returns the same answer on two builds has degenerated into a lookup.
That does not follow: what makes it a derivation is finding the address **without being told
it**, and the proof of that is the pair where they *do* differ. All three are now pairwise —
counts asserted on every build, disjointness required of at least one **pair**, agreeing
pairs printed as measurements. `test_sigcorpus.py` §3 now shows the split directly:
**SIG_DOWNLOAD has 3 distinct address sets over 3 builds** (it moved 144 bytes,
`0x833EC0` → `0x833F50`), while **SIG_KEYS and SIG_MUTEX have 2** — same byte string, same
hit count, same address across the 15-day gap.

**(d) The suite contaminated its own corpus census, and the update made it visible.**
`test_origin.py` asserts *"the whole vault is at most ONE client build"* — the guard behind
deliverable 7, and the thing that keeps opcode-drifting captures from being pooled. It went
red at `{38797: 1828, 38833: 3}`. **All three 38833 files were `test_handshake.py`'s own
output**, written by three runs of the suite during this session, now that the self-test
announces its real build (§7.7).

The fix is not a tolerance, it is the rule `test_handshake.py` already states. Its self-test
output was moved to `vault/captures/selftest/` precisely because mixing it with real captures
*"produced a false timeline during a real debugging session — two self-test captures were
read as evidence of successful client logins that never happened."* The census then walked
the whole tree and counted that directory as corpus, re-creating the contamination one level
up. `selftest` now joins `captures-scrubbed` in the walk's exclusion list.

**And excluding it moved a published figure.** Deliverable 7 records the audit as *"1,122
files, all 38797"*; the census read **1,828** before the exclusion and **1,532** after, so
roughly **296 of the files being counted as research corpus were self-test artifacts.** The
guard keeps its teeth either way: no capture has yet been taken on 38833, and the first real
one will turn this red — correctly.

**A fifth was a claim, not a crash.** `test_pinned.py` asserted *"the two builds differ in
SIZE, so size separates them"* and went red because 38833 ships at **exactly 38797's
10,483,904 bytes**. The red was right and the claim was wrong: size never separated the two
copies *within* a build — this module's founding defect — and now it does not separate
builds either. Inverted to the invariant that holds, **sha256 is the discriminator**, with
`identify()` required to name each build from its own same-size image.

### 7.7 The second build broke the SERVER, by the same `sorted()[-1]` defect the rules name

**Reported from the minimap session, 2026-08-14 ~18:40, and it is the most consequential
thing this update caused.** That session ran two loopback sessions that failed with
`Code=058`: the handshake "succeeded", then 50 unframeable bytes and DESYNC.

**Cause, and it was caused BY this arc's own work.** `authsrv.load_keys()` read:

```python
cands = sorted(f for f in os.listdir(kd) if f.startswith("rurik_dh_"))
p = os.path.join(kd, cands[-1])
```

Newest key file wins, by filename sort. That was harmless while the vault held one key.
Patching 38833 wrote `rurik_dh_2026-08-13_64fae3b1369b.json`, which sorts last — so a
session running the **38797** client got **38833's** key material. The DH triple is patched
per build, so the two ends derived different shared secrets, and the ARC4 stream was noise.

**This is `CLAUDE.md`'s own named defect, verbatim:** *"Never select a build by filename:
`sorted(exes)[-1]` picked the wrong one the day both configurations first existed."* The rule
was written about the client patcher after exactly this happened on 2026-08-06. The same
expression was sitting in the server's key loader, and it went wrong the same way, on the
same trigger — a second artifact existing — eight days later. A rule written in one file
does not protect the identical line in another.

**The symptom is the one the house rules are about.** `CLAUDE.md`: *"a red test names the
broken thing, the client says `Code=058` thirty seconds later and tells you nothing."* This
produced precisely the second thing, to a session that had changed nothing about crypto.

**FIXED 2026-08-14.** The key is now bound to the build **the client itself announces**,
which it sends in its version frame *before* the key exchange (`authsrv.py`:3838), so the
right key is always knowable in time:

- `load_keys()` builds `KEYS_BY_BUILD`, every `rurik_dh_*.json` mapped through
  `pinned.BUILDS` to a build number, and prints each with its tag and build. Newest-wins
  survives only as the *starting* key, because at bind time no client has spoken.
- `handle()` re-selects by the announced build, logging the swap.
- If there is **no** key for the announced build and the loaded one belongs to a different
  *known* build, it **REFUSES by name** rather than deriving a key that cannot work.

Branches proven rather than asserted: client 38797 → no swap; client 38833 → swaps; client
99999 → refuses. The minimap session's exact case is the middle one and now self-corrects.

**And it exposed a latent lie in `test_handshake.py`.** That file hardcoded `BUILD = 38797`
in its version frame while choosing its client exe by *"whichever build the newest key file
belongs to"* — two independent selections. From 2026-08-14 they disagreed: it drove a 38833
client announcing 38797. Nothing noticed, because until now nothing on either side read the
announced build. The new guard read it and aborted the connection — the guard working on the
first thing it was pointed at. `BUILD` is now derived from the exe via `buildid.read()`, with
a check that the exe's build matches the key file the server will load. Floor 16 → 17.

### 7.5 The archive, and an honest confounder

`datcheck --diff` across the update, full output in
`vault/updatecheck/diff-38797-to-38833.txt`:

```
rows 177,335 -> 177,753        descriptor_counter 26,722 -> 26,813
mft_offset 4,173,266,432 -> 4,196,563,456      mft_size 4,256,040 -> 4,266,072
TIER 1: 459 changed rows -- 418 added, 30 recycled, 11 relocated, 0 UNCLASSIFIED
TIER 2: records 171,025 -> 171,208    first_stream_rows 132,628 -> 132,797
        released_records 1 -> 0
```

**0 UNCLASSIFIED again** — FINDINGS 18.5's Tier 1 vocabulary now covers two full updates
with nothing left over.

**The confounder, stated because the number is not what it looks like:** the owner ran the
update with **`-image`**, which forces a full download of every asset. So these 459 rows are
*(the patch's own changes)* **+** *(backfill of content this install had never downloaded)*,
and **this pair cannot separate them.** The 418 additions in particular are far more likely
backfill than patch. Do not quote 459 as "what a content patch does"; the clean figure for
that question is still §2's 334 across 38519 → 38797. What this pair *does* support is the
shape result — the vocabulary held, nothing came back unclassified.

**The claimable-slot collision reproduced, and it is now 3 of 3.** §5.2 of
[DURABILITY.md](DURABILITY.md) found that the previous update recycled **row 35300**, the
exact slot `datplan.plan_insert` deterministically claims, and that a play session then took
35301. This update recycled **both 35300 and 35301** — 35301 went from an erased `0x0 0B`
slot to a live 6,248,664 B row. Three of three observable disturbance events have consumed
the slot our planner would have written into. That is no longer a coincidence to note; it is
a property to design around, and it strengthens DURABILITY §4b's revised prediction that an
authored row placed by `datplan` is more likely than not to be destroyed by a patch.

### 7.5a The update moved the Pre-Searing map, cleared its bit-31, and stranded `content/maps.toml`

**Reported as a symptom by the minimap session** (pre-flight refusing maps 146 and 148),
**diagnosed here from the archives.** `content/maps.toml` gives both `[map.148]` Ascalon City
(Pre-Searing) and `[map.146]` Lakeside County `file_id = 0x8001B97D`, and its provenance note
records *"0x1B97D is MFT row 7982"*. MEASURED against both vaulted archives:

| Archive | `0x8001B97D` (bit-31 form) | `0x0001B97D` (plain) |
|---|---|---|
| 38797 | row **7982** | row 7982 |
| 38833 | **does not bind at all** | row **177262** |

And what those rows now hold on 38833: row **177262** is `ffna` type 3, 2,925,267 B — the map;
row **7982** is `ATEX`, 55,492 B — **a texture**. The row was recycled (it is in §7.5's list of
30) and now holds something unrelated.

**Three things follow, and the third is a design question rather than a fix.**

1. **`mapchunks.py`:117 is confirmed by the event it was written about** — *"an MFT row index
   is meaningful only against the archive copy it was measured on; file ids are the portable
   key."* The file id survived this update; the row index did not, and the row it named now
   answers with a texture. A tool that remembered 7982 gets a confident wrong file.
2. **`maps.toml`'s "BIT 31 STAYS ON, and that is the experiment" is RESOLVED, by the archive
   itself.** That note recorded that sending the masked id crashed the 38797 client
   (`Map.cpp(1762)`), and left open whether the client masks the bit. On 38833 the bit-31 form
   is simply **absent from the id table** and the plain form binds — the pending replacement
   `DnArchive` was holding was installed by the patch. This is the same clearing
   §4e-bis observed from a LIVE session (20 of 29 bit-31 ids cleared, `0x8001B97D` among them,
   *"0x1B97D then binds plainly to a different row"*) — now reproduced by an update, on a
   pristine archive, which lifts that from one witness to two of different kinds.
3. ~~**`content/maps.toml` is now build-coupled and does not say so.**~~ **FIXED
   2026-08-14, and the answer was already written down in the repo.** The framing above —
   "`0x8001B97D` is right for 38797 and wrong for 38833, stamp the rows per archive" —
   is the wrong fix, and `archive.py`'s `file_id_table()` says why: *"A server should send
   the PLAIN LOGICAL ID and serve from an archive that binds it. `0x8001B97D` works
   against `dat_study` only because that copy has the map renamed away."*

   Bit 31 is not a spelling of the id, it is `FcArchive` announcing **a replacement is
   pending**. Recording the renamed form pinned one copy's transient state as the map's
   name, and it stopped being true the moment a copy caught up. **Both rows now carry
   `0x1B97D`**, and the id needs no stamp because it is no longer archive state.

   **The three pairings, MEASURED after the change** (`toolkit/contentids.py`):

   | server archive | client archive | verdict |
   |---|---|---|
   | `dat_study` (pre-update) | `run/2026-07-29…` (pre-update) | **10 of 10 OK**, both row 7982 |
   | `dat_study` (pre-update) | `run/2026-08-13…` (post-update) | **2 FATAL**, exit 2 — correctly |
   | 38833's archive | `run/2026-08-13…` | **10 of 10 OK**, both row 177262 |

   The plain id works on **both** generations, which the renamed form never could — under
   the old value the third row was impossible, because a post-update client binds
   `0x8001B97D` nowhere. What the middle row shows is not a regression but the guard doing
   its job: the update installed a genuinely **different file** (1,300,044 B crc
   `0x33F1A289` against 1,300,036 B crc `0xA0AE500A`), so a post-update client against a
   pre-update server would draw new geometry while the server pathed the old. **Point
   `RURIK_DAT` at a post-update archive to run the new client**; `contentids.preflight`
   refuses the mixed pair by size and crc rather than by row index.

   Three tests moved with it, each an assertion about the old state rather than a defect:
   `test_content.py`'s migration pin (kept, with the old literal as the FROM),
   `test_contentids.py` §0 (now **no content row may name a bit-31 id** — the stronger
   invariant), and its refusal-message check (was pinned to the renamed spelling).

**The durability tracer did not fire and could not have.** `vault/dat_durability/Gw.dat` is
an inert copy no updater touches — §4 above, known before the event. Nothing was lost; the
owner's standing answer is to rebase mods over an update via `deploy.py`. Arming an
updater-reachable archive remains an explicit owner choice.

### 7.6 What was done to the tree

- `pinned.BUILDS` gains `2026-08-13_64fae3b1369b` = **38833**, sha256
  `64fae3b1369b…a13c6`, 10,483,904 B. **The pin did NOT move.** `PINNED` was
  `BUILDS[-1]` and is now an explicit lookup of 38797, because every address in `studies/`
  is measured against 38797 and `genericvalue.py` cannot read 38833 — repointing the default
  would have turned one honest refusal into a wall of red. **Moving the pin is a
  re-measurement arc, not a registration step.**
- **38833 is the first build where size is not a discriminator** — byte-for-byte the same
  length as 38797. `identify()` already loops over every same-size candidate, so it is safe;
  a size check written anywhere else is now a bug.
- `vault/client/2026-08-13_64fae3b1369b/` — full snapshot, every file verified
  byte-identical, exit 0. Only `Gw.exe` and `Gw.dat` changed; the four sibling DLLs hash
  identically to 38797's.
- Both client builds rebuilt and both run directories reassembled. `dhbuild.py` audit:
  **every build is where it belongs**, `run-live/` both `updater=LIVE`.
  `vault/keys/dh_params_2026-08-13_64fae3b1369b.txt` added — without it `classify()`
  returned `unknown` and `make_custom_client.py` **refused to file the binary**, exit 1,
  which is the fail-closed behaviour working.
- Six tests updated for a third build, with floors re-measured from real green runs:
  `test_buildid` 23 → 29, `test_avevents` 19 → 26, `test_pinned` 55 → 61,
  `test_srctree` 30 → 39, `test_msgshape` 37 → 44, `test_sigcorpus` 34 → 35.
  `TESTS.md`'s entries carry the same numbers and the reasons.
- ~~**One item is left for the owner and needs elevation:** the new loopback client at
  `vault/run/2026-08-13_64fae3b1369b/` is **UNCAGED**~~ — **DONE**, out of session, by
  `isolate_client.ps1` in an elevated shell. It carries OUR DH parameters, so it had to be
  caged before launch, and that costs a UAC prompt by design rather than being something a
  session does silently. Recorded because the sequence is the point: patching a new build
  leaves the machine one deliberate manual step short of safe, `test_cage.py` is what says
  so, and it named the exact binary.
- **Suite: 94 green / 0 red / 0 suspect of 94, 4,686 checks, 2,721 s** — a full run of
  `python toolkit/run_suite.py` on the tree with `main` merged in (the terrain T4/T5 and
  minimap S12 arcs), not a partial run reported as a full one. Three runs tell the story:
  **89/5** before any of this, **93/1** after the code fixes, **94/0** once the new
  loopback client was caged. The intermediate red was `test_cage.py` and it was **machine
  state rather than code** — the four code reds were `test_msgshape`, `test_sigcorpus`,
  `test_srctree` and `test_origin`, every one a two-build assumption meeting a third build.
- The new loopback client **is now caged** (`cage.py`: *7 client(s), 0 in the wrong state*),
  so the launch binding holds for all seven builds in the vault.
- The live build needed **two** flags beyond `--no-dh-patch` to match its 38797 predecessor:
  `--no-updater-patch` (§7.4b) and `--key-tap`, without which `livesession.py` refuses the
  build outright. Both are now in `RUNBOOK.md` step 3; only the key tap was already
  documented, and only in the live-capture section rather than in the setup steps.

---

### 7.8 The corpus went two-build, and a correct refusal was the wrong instrument

**OBSERVED 2026-08-15.** The 38833 verification runs of §7.6 wrote real captures into
`vault/captures/authsrv/`. Not fixtures — §7.4d's `selftest/` exclusion had already
handled those, and this is precisely the case that exclusion was scoped *not* to cover.
The research corpus became genuinely two-build:

| Build | Files |
|---|---:|
| 38797 | 1,534 |
| 38833 | 18 |
| unstamped | 953 |

Both pooling consumers went red — `test_movement_fidelity.py` and `test_origin.py`'s
census — and **both were right to.** Opcodes drift between builds (`MOVE_TO_COORD` is
`0x003C` in one client and `0x003E` in another), so a fidelity score pooled over two of
them is about neither. This is deliverable 7's guard doing exactly the job it was built
for, on the first occasion it could.

**The finding is not the red. It is that the red could not be acted on.** A refusal
states a fact about the vault — *two builds are present* — when what a reader needs is a
policy: *which build does this figure describe?* No test settles that by failing, and
the two obvious responses are both wrong in the same way: loosening the guard restores a
meaningless number, and leaving it red parks two real measurements over a condition that
is now permanent and recurs at every update.

**Owner's decision, 2026-08-15: the figures follow the pin.** `pinned.py` deliberately
still pins 38797 (§7.6 — moving it is a re-measurement arc of its own), so the published
figures are figures about 38797 and off-pin captures are excluded rather than blended.
The mechanism is `origin.select_build(paths, build) -> (kept, dropped)`:

- **the build is an argument, not an import.** `origin.py` is on the server path and
  does not depend on `clientscan/pinned.py`; the consumer reads `pinned.BUILD` and passes
  it. The corpus follows the pin automatically when it moves, and the two authorities
  cannot drift apart silently — the staleness failure the top of `CLAUDE.md` is about.
- **unstamped files are KEPT.** 953 of the corpus names no build, because a frame log
  names it once per SESSION and not once per file. "Cannot say" is not "some other
  build", and a strict `== build` filter would silently discard a third of the evidence
  and move every figure for a reason nobody could see.
- **the caller prints what it dropped.** `select_build` returns `dropped` rather than
  logging it, and every call site reports the count — a bounded corpus reported as a
  whole one is the silent-truncation defect this repo keeps re-learning.

**The census's invariant changed shape, and the new one needed a second half.** It used
to assert *one build exists*, which the corpus has outgrown and will keep outgrowing. It
now asserts *selecting to the pin leaves one build* — **and** *the pinned corpus survives
the selection*. The second is not belt-and-braces: **MEASURED, selecting to a pin the
corpus does not hold (99999) passes the first check VACUOUSLY**, because a filter that
keeps nothing also leaves one build. Both predicates run against a nonexistent pin inside
the test as a negative control, and the pair must split — 0 files at 99999 against 1,534
at the real pin.

Scored honestly: the guard worked as designed *and* the arc left an instrument gap it did
not anticipate. Deliverable 7 built the refusal and never built the selection, and a
refusal alone is unusable the moment a second build is legitimately present — which, for
a project that will meet an update every few weeks, is the ordinary case rather than the
exception.

### 7.9 A fourth `sorted()[-1]`, and this one had switched builds without going red

**OBSERVED 2026-08-15**, found while auditing whether the census's remaining pins fail
loudly. `test_atexlevel.py` §7 — the section that pins the ATEX codec's two literal
tables to ArenaNet's own bytes — chose its image like this:

```python
builds = sorted(os.listdir(root))
exe = None
for name in builds:
    candidate = os.path.join(root, name, "Gw.exe")
    if os.path.isfile(candidate):
        exe = candidate          # no break: LAST one wins
```

That is `sorted(...)[-1]` written as a loop, which is why three previous sweeps for the
idiom did not find it. **The fourth instance in four files**, after `authsrv`'s key
selection (§7.7), `drive_client.newest_run_exe` and `contentids.default_client_dat`.

**It was harmless until the vault held a third build, and then it changed answers in
silence.** `2026-08-13_64fae3b1369b` sorts last, so from the moment 38833 was
snapshotted this section stopped validating 38797 — the build its literals were measured
on — and began validating **38833**, which nobody chose and no output named.

**It stayed green, and the reason is the interesting part.** MEASURED across all three
vaulted builds:

| Build | `FORMAT_FLAGS` matches | `RUN_TABLE` matches |
|---|---|---|
| 38519 | **no** | **no** |
| 38797 | yes | yes |
| 38833 | yes | yes |

So the tables **are** build-coupled — 38519 proves it — and 38833 simply did not move
them, consistent with §7.2's finding that this 15-day bugfix moved far less than the
90-day gap did. The section passed for a real reason rather than by accident, but it
passed about the wrong build, and the day a future build moves those tables the red
would read as *"the ATEX codec is broken"* rather than *"you are reading a client nobody
selected."* That is the arc's own defect class arriving inside the arc's own test suite.

**Two fixes, and the second is the one that would have prevented it.**

1. §7 now resolves through `pinned.find(atex.TABLES_BUILD)` — selection by REGISTRY
   rather than by filename order, with the sha256 verified and the live install refused
   — and it **prints the build it read**. A section that opens a client and does not say
   which one is one directory rename away from this bug again.
2. `atex.py` gained `TABLES_BUILD = 38797`. The two VAs named no build at all, which is
   precisely the class-(b) defect §6 states — *"a bare VA with no build is the defect,
   not the VA"* — and the cost was concrete rather than theoretical: with nothing
   recording which build they came from, neither the test nor a reader had anything to
   notice the switch against. Its docstring also pointed at `test_atex.py`, where this
   check has never lived.

The census went **46 → 47** and `test_buildpins.py` went red for it, correctly. That
trade is the right way round and worth stating plainly, because the instinct is to read
any increase as regression: **a counted pin a test resolves through `pinned.find()` is
safer than an uncounted address nobody can tell is stale.**

---

## 8. `genericvalue.py` derived — the arc's one casualty, closed

§7.1 left this module as the update's single measured casualty: it REFUSED build
38833 (`the switch site at 0x008129CC ... is not a movzx/jmp pair`) and took
`avevents.py`'s property map down with it. **Fixed 2026-08-14. Its class-(a) count
is 27 → 0, and the repo's whole census is 73 → 46 — the first time that number has
gone down by a lot.**

### 8.1 The blocker was written down, and it was right

The module's own comment said why it could not be converted, and it was correct on
both counts:

> *"WHY `at` IS STILL PINNED, measured rather than assumed: this instruction shape
> occurs **596 times** in `.text` on build 38797, so it is not an anchor. Making
> these fully derived means anchoring the DISPATCHERS first — they are reached
> from the message handler — which is a separate job and is not this one."*

The update turned "a separate job" into the job. And the anchor it named was
already in the tree: `msgshape.py` derives the client's message tables from
`RegisterMsgs` **by byte shape**, so the receive table is reachable without a
single stored address — and the two dispatchers are simply the handlers for
`AGENT_PROPERTY_UPDATE_INT` (`0x009F`) and `_FLOAT` (`0x00A2`).

### 8.2 The chain, and the count asserted at every link

Each step below is a refusal, not a search. MEASURED on all three vaulted builds.

| Step | What is derived | The assertion |
|---|---|---|
| 1 | the RECV table entry for `0x009F` / `0x00A2` | the handler exists, or refuse |
| 2 | handler → dispatcher | the forwarder makes **exactly 1** call |
| 3 | int dispatcher body | **exactly 2** `movzx`/`jmp` sites: int-pre, then int-main |
| 4 | float dispatcher body | **exactly 1**: float-main |
| 5 | functions each dispatcher calls | **exactly 2** hold a property switch: store, then AgentView |
| 6 | each switch's default | the jump target the most ids share |
| 7 | each switch's id span | read from the `lea`/`cmp`/`ja` guard |
| 8 | each chain's ids and bodies | parsed from its comparisons, after its byte string verifies |
| 9 | each main-switch gate | **exactly 1** `test byte [ctx+0x53C], 2` per dispatcher |

**Every one of those addresses reproduces build 38797's hand-measured value** —
all seven switches, both gates, all six chain case bodies, all five spans.
`test_genericvalue.py` §1 is that claim, and the witness now lives in the test
rather than the module, which is what took the count to zero: under §6's taxonomy
a hand-measured address is class (a) only for as long as the **tool** computes
with it.

### 8.3 The result, and the part a lookup cannot fake

| Build | int-main site | float-main site | int / float ids handled | untouched |
|---|---|---|---|---|
| 38519 | `0x0080C4DC` | `0x0080CBEB` | 47 / 14 | `{40}` |
| 38797 | `0x008129CC` | `0x008130DB` | 47 / 14 | `{40}` |
| 38833 | `0x0081286C` | `0x00812F7B` | 47 / 14 | `{40}` |

**Three builds, three disjoint address sets, one answer.** Main switches disjoint
on all three; `avevents.py` back to 39 of 67 ids queueing an event on all three.
Agreement on the semantics *with* disagreement on the addresses is the signature
of a derivation, and it is the check `test_genericvalue.py` §3 now makes — a
section that previously asserted the opposite, that the older build must REFUSE,
because refusing was the best the pinned module could do.

### 8.4 Two things worth carrying

**The old §3 was not wrong, it was as good as pinning allows.** "This build moved
something, so refuse" is the correct behaviour for a tool that cannot look; it is
just not the same as reading the client. The arc has now produced both shapes in
one module and the difference is visible: round one turned a silent wrong answer
into a loud refusal, round two turned the refusal into an answer. **Only the first
was strictly necessary; the second is what made the tool survive an update.**

**And one check I wrote had to be thrown away, for the reason `PLAN.md` §6 warns
about.** The first draft of §1 grepped `genericvalue.py` for the old literals and
required them absent. It went red — on the module's own docstring, which names the
seven switches and their 38797 addresses. Those are class (b), citations,
*provenance*, and §6 is explicit: **"Add build ids; do not remove addresses."** The
check now asks `buildpins` — the repo's own AST census — for live constants, which
is the distinction that actually matters, and asserts the citations are still there.
That is the same trap that cost a previous session 46 rewritten citations and 46
reverts, and it caught me inside an hour.

---

## 5. What this changes elsewhere

- **`studies/datwrite/FINDINGS.md`** said *"the durability experiment is still unrun"*.
  Corrected in the same commit as this file: it is armed, byte-verified, reverted and
  re-armed — and blocked on delivery, which is a different state from unrun and points at a
  different next action.
- ~~**`vault/updatecheck/`** is dark in a stronger sense: the snapshot exists, **no tool in
  either tree reads or writes it**, and its `archive` key is `{}`. If an update-detection
  path is wanted, that is where it was started and abandoned. NOT FOUND: any consumer.~~
  **SUPERSEDED 2026-08-13/14.** `toolkit/updatecheck.py` is the consumer — it writes the
  baselines and reads them back at `--after` — and on 2026-08-14 it was **used for real**
  against the 38833 update (§7). The empty `archive` key was not a defect in the directory
  but a missing `--dat` on the one baseline that had been taken by hand;
  `before-20260814T175822.json` carries a populated one.
- ~~**`PLAN.md` §7's pre-update checklist** is called *"the highest-value deliverable here"*
  and it is the thing this arc should finish next~~ — **LANDED** as `updatecheck.py`
  (deliverable 8), and §7 above is the record of its first firing, which found two defects
  in it and in `RUNBOOK.md`. It earned the "highest-value" label: it was the reason a
  before-state existed at all when the update arrived.

---

## 6. Labels

| Claim | Label |
|---|---|
| The tracer is present at the stated offset with the stated hash | **OBSERVED** — read from the bytes by this author, twice |
| Revert is byte-identical | **OBSERVED** — `datcheck --diff` exit 0, recorded in `ARMED.json`; not independently re-run here |
| 334 rows change across one update, in the four named shapes | **OBSERVED** — one update, n=1 |
| The authored row will survive an update | **RECONSTRUCTION**, low confidence, §3 |
| An authored row survives a PLAY SESSION in which the client demonstrably rewrote the archive | **OBSERVED** — two witnesses, §4b (relocated row, 10,714 B over a 4,608 B reservation, client recompiled from it) and §4c (three in-place rows, different archive copy). n=2 sessions, ~70–120 s each |
| The MFT alternates between two offsets rather than drifting | **OBSERVED** — §4c, seven vault copies at exactly two values, copies with identical entry counts at both |
| A session longer than ~120 s leaves an authored row alone | **OBSERVED** — §4e-ter, 900 s, third witness; and duration is the wrong axis, 900 s produced 2 changed rows against 120 s's 3 |
| A loopback play session clears no bit-31 id | **OBSERVED**, n=1 with a before-census — §4e-ter, 29 of 29 unmoved in a session where the client rewrote and relocated two rows |
| An ordinary loopback session is what cleared the install→study 4 | **CONTESTED** — `datwrite/FINDINGS.md`:585 says so; §4e-ter's controlled run cleared nothing. The change is real (§4e-bis reproduces it), the cause is not established |
| A LIVE session clears bit-31 map-row ids, including row 7982's | **OBSERVED** — §4e-bis, `run-live` cleared 20 of 29 including `0x8001B97D` and `0x8005E728`; `0x1B97D` then binds plainly to a different row |
| The MFT alternation is a usable liveness signal | **REFUTED** — §4e-ter did not flip; `descriptor_counter` moved and is the one to use |
| The patcher holds no external content manifest | **UNVERIFIED** — never looked for, and it is the assumption the prediction rests on |
| Build 38833 shipped 2026-08-13 | **WIKI** (GWW, "Game updates" §Update - August 13, 2026, read 2026-08-14) for the number and the changelog; **MEASURED** independently by `buildid.py` off the image. Two witnesses sharing no lineage |
| 8 of 8 signatures resolve at their exact hit counts on 38833 | **MEASURED**, §7.1 — `sigcorpus.py --exe` directly, and again through the fixed `updatecheck` path |
| `msgshape` / `asserts` / `buildid` / `srctree` all read 38833; `genericvalue` refuses it | **MEASURED**, §7.1, one run each |
| Raw-address anchoring is *unpredictably* rather than reliably broken by an update | **MEASURED**, n=3 builds / 2 gaps, §7.2. The two gaps differ in kind (90-day vs 15-day); this is induction over two events and must not be quoted as a law |
| The DH struct stayed at `0x00A910D8` while its parameters rotated | **MEASURED**, §7.3, fingerprints only |
| 459 archive rows changed across the update | **MEASURED but CONFOUNDED**, §7.5 — the owner ran `-image`, so patch changes and never-downloaded backfill are inseparable in this pair. Not a "what a patch does" figure |
| The claimable erased row slot is consumed by disturbance events | **OBSERVED, 3 of 3** — §7.5 (35300 *and* 35301 this update) plus DURABILITY §5.2's two. Small n, but no counter-example |
| `updatecheck --after` printed a pass about a build it never opened | **OBSERVED**, §7.4a — reproduced, then fixed; the fix is what produced the §7.1 figure |
| A second key file made `authsrv` hand a 38797 client 38833's DH key | **OBSERVED** — §7.7, two failed loopback sessions from the minimap session, `Code=058`. Root cause read from the source (`sorted(...)[-1]`); fix's three branches proven by direct call |
| `test_handshake.py` drove a 38833 client while announcing build 38797 | **OBSERVED**, §7.7 — latent from the moment the second build was patched, surfaced by the new guard |
| ~296 files counted as research corpus were self-test artifacts | **MEASURED** — §7.4d, census 1,828 → 1,532 once `selftest/` is excluded. Deliverable 7's "1,122 files" figure was over a tree that included them |
| The research corpus is now genuinely two-build, and the pooling refusal alone could not resolve it | **OBSERVED** — §7.8, 1,534 at 38797 against 18 at 38833 plus 953 unstamped. The refusal was correct and unactionable; the figures now FOLLOW THE PIN via `origin.select_build`, unstamped files kept, exclusions printed |
| A pin the corpus does not hold passes the one-build census vacuously | **MEASURED** — §7.8, control at 99999: 0 files, first predicate green, second red. Why the census needs both halves |
| `test_atexlevel.py` §7 silently switched to validating 38833 when the vault gained a third build | **OBSERVED** — §7.9, a fourth `sorted()[-1]` written as a break-less loop. Stayed green because 38833 did not move those tables; 38519 does, so they ARE build-coupled |
| ~~`archive.py`'s offset for row 46196 is wrong by 1,024~~ | **REFUTED** 2026-08-14 — `archive.row(46196).offset == 0x437F6800`, identical to `datwrite`/`datcheck`, marker in that extent. The 1,024 came from reading `entries[46196]`, which is row 46197. §4, §4b.1 |
| ~~`archive.py` and `datcheck.py` number MFT rows differently, off by one~~ | **REFUTED** 2026-08-14 — all 24 bytes of every row agree on all ten vault archives; pinned by `test_archive.py` §1c. The number that differs is `len(entries)` vs `row_count`. §4b.1 |
| There is ONE row convention, ArenaNet's raw MFT index, and every reader and every recorded constant is in it | **OBSERVED** — 10 archives by an independent `struct` walker; 65 recorded constants ≥ 16 re-resolved in both conventions, 26 map-flagged under `row(N)` and 1 under `entries[N]`, zero overlap |
| Rung 6 is deliverable | **NOT FOUND** — no update can reach this copy (§4) |
