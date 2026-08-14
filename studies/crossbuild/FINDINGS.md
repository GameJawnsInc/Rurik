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

**One offset disagreement is recorded rather than resolved.** `datwrite` and `datcheck`
agree row 46196 is stored at `0x437F6800`; `archive.Archive().entries[46196].offset`
reports 1,132,424,192, **exactly 1,024 higher**. The read above used the `datwrite`/
`datcheck` offset and found the marker there, so that pair is right for this purpose and
`archive.py`'s reading is the one to chase. UNVERIFIED which is correct in general — the
constant 1,024 smells like a header or block-base convention rather than a bug, and nobody
has looked.

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

### 4b.1 THE TRAP, and it nearly produced the opposite conclusion

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
| The patcher holds no external content manifest | **UNVERIFIED** — never looked for, and it is the assumption the prediction rests on |
| `archive.py`'s offset for row 46196 is wrong by 1,024 | **CONTESTED** — two tools disagree; the marker was found at the `datwrite` offset |
| Rung 6 is deliverable | **NOT FOUND** — no update can reach this copy (§4) |
