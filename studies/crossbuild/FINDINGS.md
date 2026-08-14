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

## 5. What this changes elsewhere

- **`studies/datwrite/FINDINGS.md`** said *"the durability experiment is still unrun"*.
  Corrected in the same commit as this file: it is armed, byte-verified, reverted and
  re-armed — and blocked on delivery, which is a different state from unrun and points at a
  different next action.
- **`vault/updatecheck/`** is dark in a stronger sense: the snapshot exists, **no tool in
  either tree reads or writes it**, and its `archive` key is `{}`. If an update-detection
  path is wanted, that is where it was started and abandoned. NOT FOUND: any consumer.
- **`PLAN.md` §7's pre-update checklist** is called *"the highest-value deliverable here"*
  and it is the thing this arc should finish next, because it is the half that cannot be run
  retroactively and it needs no delivery decision.

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
| ~~`archive.py`'s offset for row 46196 is wrong by 1,024~~ | **REFUTED** 2026-08-14 — `archive.row(46196).offset == 0x437F6800`, identical to `datwrite`/`datcheck`, marker in that extent. The 1,024 came from reading `entries[46196]`, which is row 46197. §4, §4b.1 |
| ~~`archive.py` and `datcheck.py` number MFT rows differently, off by one~~ | **REFUTED** 2026-08-14 — all 24 bytes of every row agree on all ten vault archives; pinned by `test_archive.py` §1c. The number that differs is `len(entries)` vs `row_count`. §4b.1 |
| There is ONE row convention, ArenaNet's raw MFT index, and every reader and every recorded constant is in it | **OBSERVED** — 10 archives by an independent `struct` walker; 65 recorded constants ≥ 16 re-resolved in both conventions, 26 map-flagged under `row(N)` and 1 under `entries[N]`, zero overlap |
| Rung 6 is deliverable | **NOT FOUND** — no update can reach this copy (§4) |
