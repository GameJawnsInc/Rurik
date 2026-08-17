# The re-import round trip — rung U6 of the unit-model arc

**2026-08-16.** Deliverables: `toolkit/mapdata/skelwrite.py` (the FA1 and
container writer, the modification seam, the vault-only write path) and
`toolkit/mapdata/test_skelwrite.py` (69 checks, floor 69 after the
adversarial review's fixes -- §6.1; TESTS.md entry in the same commit). Labels are the project vocabulary
([../character/FINDINGS.md](../character/FINDINGS.md)). Artifacts:
`vault/research/unitwrite/2026-08-16-u6/`. The reader this inverts is
`skelfile.py` (U1/U2); the archive discipline is `datwrite.py`/`datmove.py`
([../datwrite/FINDINGS.md](../datwrite/FINDINGS.md)).

## 1. The answer in one page

- **The typed layer is COMPLETE.** An FA1 rebuilt from `skelfile`'s typed
  values — header fields, sequence records, key times+tags, blk2C/blk48
  records with their channel arrays, n40 sound events, the n3E track — plus
  the regions that layer deliberately leaves opaque (n14/n34 records, the
  seven var-array families, the n44 tail, and 3 header bytes) is
  **byte-identical to the source for the complete corpus**:
  **14,571/14,571 FA1 chunks and 21,420/21,420 whole containers, zero
  failures** (MEASURED 2026-08-16, 775 s; `fullpop_census.json`, and the
  committed test reproduces the same numbers under `--all` — 71 checks
  green post-review, corpus pass 780 s — while its default stride pins
  241/241 + 160/160). The carried-bytes truth, by the review's RECURSIVE
  LEAF WALK (§6.1 RISK-1/2): worm 883 of 82,169 (1.07%); shell 1,179 of
  29,495 (4.00% — the shell is the n40-heavy anchor, and 620 of its
  carried bytes are its 62 sound-event raw tails); corpus-wide 1,951,827
  of 371,998,300 = 0.52% (the declared regions alone are 1,827,597 =
  0.49%; the gap is exactly the 12,423 raw tails) — pinned in the test,
  because a writer that drifted back toward carrying typed regions as
  bytes is the memcpy-loader defect (§3). And stated so the container
  number is not over-read: 6,849 of the 21,420 containers carry no FA1
  at all, so their identity tests the framing re-derivation plus
  verbatim chunk copy only; on the FA1 carriers the through-the-typed-
  writer share varies — the worm's container is 63.5% FA1+framing /
  36.5% verbatim other chunks, the shell's 99.0% / 0.9%.
- **One field was caught by the attempt, before identity ever ran**: header
  bytes **+0x09..+0x0B are not padding**. The parser never reads them
  (unitmodels §3.3) and the natural writer design — pack the named fields,
  zero the rest — would have failed identity on **5,208 of 14,571 files**.
  Measured: shell carries `42 00 00`, worm `07 00 00`; 39 distinct 3-byte
  patterns corpus-wide, and every one of the ten most common is a single
  byte at +0x09 with +0x0A/+0x0B zero (the artifact keeps the top ten
  only; the tail 29 patterns are counted but not itemized). The writer
  carries the region opaque (`pad09`). What writes or reads it is
  **NOT FOUND** (§6).
- **Identity, not re-parse equivalence, is the criterion, and the test
  exhibits why**: a deliberately block-swapped writer variant (n34 emitted
  before n14 — adjacent FIXED-size blocks, the exact zone closure cannot
  pin) produces output that **re-parses green and fails identity**, with
  the diff confined to the two blocks. Shown on a synthetic with
  planted-distinct content and on the worm (§4).
- **The datwrite half closes, with its identity levels stated** (§5):
  serialized chunk/container bytes EXACT; the row read back out of a
  rebuilt archive EXACT; the stored form legitimately DIFFERENT
  (compression 8 → stored; no compression-8 encoder exists — the recorded
  wall, exhibited: `datwrite --replace` refuses the 129,368-byte payload
  naming the relocation, and `datmove` succeeds beside it). The
  **515 → 1 → 2817 `alloc.nextStream` chain survives the write intact**,
  partners byte-identical — the check U7's kill/keep depends on.
- **The U7 seam is built and demonstrated, not fired**: scaling worm
  sequence 2's key times ×2 changes exactly key 2 (200000 → 400000), the
  re-serialization differs from the source at exactly that int32 slot —
  at chunk level and at container level — and re-decodes to the scaled
  time. Nothing was deployed anywhere; no client ran.

## 2. What identity proved about the typed layer

The claim under test: every value `skelfile` DECODES can be re-serialized
with no information loss. `extract()` pulls the typed representation
through skelfile's own accessors (one decoder — a private re-parse in the
writer would be a second implementation that could agree by accident);
`encode()` rebuilds the stream in parser order from those values alone.

Results, full population (775 s):

| level | identical | of |
|---|---:|---:|
| FA1 chunk, typed repack | 14,571 | 14,571 |
| whole container (ffna type 2, all chunks) | 21,420 | 21,420 |

(21,421 flags=515 heads minus the known non-ffna row 8316.)

Notes the run forced:

- **Float round-tripping never bit.** f32 → Python float → f32 is
  bit-exact for finite values, and identity at full population is the
  proof no non-finite value hides anywhere the typed layer touches —
  extending anim P5 (0 non-finite in 16.2M channel values) to every f32
  the writer repacks (header f20/f28, sequence f32_13, record bases,
  every blk2C/blk48 channel value).
- **`skelfile.sound_events()` crashed on files with no n40n44 span.** The
  first strided writer run found it: on n40 == n44 == 0 files (72.5% of
  the corpus — 116 of the 160 in the default sample) `_span("n40n44")`
  returned None and the accessor unpacked it. U6 first guarded it in
  `skelwrite.extract()` (its permission boundary was "existing API
  behavior must not change"); the review then granted scoped permission
  and the accessor itself is FIXED — it returns [] and wraps raw_tail in
  `bytes()` — with the regression pinned in `test_skelfile.py` section 2
  (91 checks, floor 83) and the extract guard simplified to match (§6.1).
- **pad09.** See §1. The census artifact keeps the value histogram:
  5,208 of 14,571 files non-zero, 39 distinct patterns, top values
  `06`, `02`, `04`, `03`, `41`, `01`, `07`, `40`, `43` (all at +0x09).
- The opaque fraction over the whole corpus is **0.52%** of all FA1 bytes
  by the review's leaf walk (1,951,827 of 371,998,300; the census's
  declared-regions figure is 1,827,597 = 0.49%, and the difference is
  exactly the n40 bodies' 12,423 ten-byte raw tails); everything else is
  re-derived from typed values.

## 3. Why this identity is not vacuous (the memcpy-loader lesson)

`studies/models/FINDINGS.md` §4.5: a loader that stashes the source block
passes every oracle while decoding nothing. The writer-side analogue — an
encoder that concatenates the reader's `.spans` — would pass byte-identity
on all 14,571 files while proving nothing. The design and the test close
that door from three sides:

1. **The representation has no bytes to concatenate.** `extract()` returns
   typed values only, plus the named opaque regions; the test encodes a
   repr **hand-built from its own literals** (never decoded from anything)
   and requires the output to equal `test_skelfile.synth_anim()`'s bytes —
   two derivations meeting byte-for-byte, and an input a
   spans-concatenating encoder cannot process at all.
2. **The opaque carry is pinned by a recursive leaf walk.** Worm 883 B of
   82,169, shell 1,179 of 29,495, measured and asserted, with the
   declared/undeclared split checked as exactly 10 x n40 beside it. (The
   first pin summed the DECLARED regions only — the review struck it: a
   writer stashing bytes under a NEW key would have moved it by zero, a
   check that could not fail in the direction it advertised.) A
   regression that quietly carried blk2C as bytes — under any key —
   moves a number two files must agree on.
3. **The modification seam uses the same `encode()`.** A memcpy writer
   would emit the unmodified original; the byte-diff check (§5.1) goes
   red.

Refusals are part of the same posture: `encode()` re-walks every opaque
var-array with the reader's own terms and refuses a block that does not
tile; count/list mismatches, diverged start/end aliases, wrong-size pad09
and n2C == 0 (the client's own error 12) are all named `Unwritable`s with
passing controls beside them. The n56 family — 0 corpus carriers, stride
disasm-only — round-trips on two synthetic shapes, the reader's own
fixture pattern with the test's literals.

## 4. The order control — the rationale, exhibited writer-side

Closure tests the SUM of adjacent fixed-size blocks, so the reader cannot
refute their order (unitmodels §3.5); U1 proved that reader-side with
`indep_walk(move_n38=True)`. U6's variant is the writer-side analogue:
`swap_n14_n34()` emits the n34 block before n14. On a synthetic with
planted-distinct block bytes and on the worm (n14 = 2 records, n34 = 10,
contents measured distinct):

- the swapped output **re-parses green** — header intact, every gate
  passes, closure lands on the exact final byte, the typed layer decodes
  without complaint;
- it **fails identity**, with the byte diff confined to
  `[0x58, 0x58 + n14·16 + n34·24)`.

So a writer wrong in exactly the way the walk cannot see is caught by the
identity criterion and by nothing weaker — which is why U6's acceptance
was identity and why re-parse equivalence would have been a check that
cannot fail. (The swap needed distinct content to be non-vacuous:
`synth()`'s uniform 0xAA fill makes the swapped output byte-identical, a
control that cannot fail — the test plants its own bytes.)

## 5. The datwrite half

The rebuilt archive is a 3-row REBUILD in `test_datmove.py`'s fixture
shape, at `vault/exports/unitwrite/rebuilt_worm.dat` (~254 KB): the worm's
three rows copied stored-byte-verbatim from the study archive — root
(flags 515, 90,616 B compression 8) → mid (flags 1, 36,916 B) → tail
(flags 2817, 89 B stored), linked by `alloc.nextStream` at loader-legal
indices (16/17/18; the loader asserts links ≥ 16 and < count) — plus a
253-block free run and a file-id record for 116366. All three checksum
rules verify before any write, and the root row decompresses inside the
rebuild to the same 129,368-byte container the study archive yields.

The write, and the identity level of each check, stated plainly:

| step | level | result |
|---|---|---|
| `rebuild_container(container)` | serialized bytes | EXACT (129,368/129,368) |
| `datwrite.Writer.replace(root, rebuilt)` | — | **REFUSED, naming the relocation** — the recorded wall (datwrite FINDINGS 38: `--replace` writes uncompressed and will not move a row; 129,368 B vs the row's 90,624 B reservation) |
| `datmove.move(root, rebuilt)` | — | succeeds: best-fit into the free run, journalled, old reservation zeroed |
| read the row back (`Archive.read`) | decompressed row payload | EXACT — equals the source container byte-for-byte |
| the stored form | stored bytes | **legitimately different and NOT claimed**: compression 8 × 90,616 B became stored × 129,368 B. No compression-8 encoder exists (datwrite blocker 2); stored is the only form we can author. |

**The nextStream chain survives intact** — the check the rung's contract
made load-bearing, because U7's kill/keep names the untouched mid/tail
rows as the prime suspects if the client rejects: after the move,
root.next still names the mid, mid.next the tail, tail.next 0; all three
flags (515/1/2817) unchanged; the mid and tail rows byte-identical; the
file-id table still names the same root row; all three checksum rules
hold; no two reservations intersect. The chain checker has a
corrupted-chain control beside it proving it can report.

Scale, stated honestly: this is a 3-row rebuild, not a 4.2 GB copy. The
full-scale precedent — a real map row moved 1.6 GB inside the real
archive, then read, compiled from, and left byte-identical by the retail
client across a play session — is `test_datmove.py` / datwrite FINDINGS
39's, and is cited rather than re-run. What that precedent does NOT cover
is U7's actual question (§6).

## 5.1 The U7 seam — byte-diff demonstrated

`scale_sequence_keytimes(t, seq, num, den)`: pure integer arithmetic on
the key table's int32 times over the sequence's `[lo, hi)` span; inexact
division and int32 overflow are refused, never rounded — a retime that
slid off the 1e-5 grid silently would be a different experiment. It
returns the key indices whose value changed, so the byte diff is
PREDICTED before serializing.

Demonstrated on the worm, deterministically: sequence 2 spans keys[2:3) =
[200000]; ×2 → changed = [2]. The re-serialization differs from the
82,169-byte source at bytes ⊆ [keys_off+8, keys_off+12) — the predicted
int32 slot, 3 of its 4 bytes in practice (the high byte is 0x00 in both
values) — and NOWHERE else; at container level the same offsets shifted
by the FA1 payload's position, and nowhere else; re-decoding yields
400000. The refusal is demonstrated on sequence 4 (86666/4, inexact). The
synthetic half does the same end-to-end on `synth_anim()`. (Spans of
different sequences may overlap — the worm runs 10 sequences over 3 keys
— so the seam names key-table slots, not ownership; a retime of one
sequence can move a key another sequence shares, and U7's operator should
pick the target with that in view.)

**ATOMIC since the review (BUG-1), and it matters because this is what
U7 fires.** The first version wrote each key as it validated it, so a
refusal part-way through a span left the repr half-retimed — and still
serializing. The review found the reachable case: the shell's sequence
16 spans two keys [66666, 116666], and scaling by 1/3 refused on the
second with the first already rewritten 66666 → 22222. The fix computes
and validates the WHOLE span before any of it commits, and the test now
pins the property from both sides: a synthetic two-key span with a
non-zero first key, and the shell case itself — each must refuse AND
still encode to the SOURCE bytes afterwards (identity after refusal is
the atomicity proof; the pre-review refusal fixtures were structurally
blind, spanning either a leading zero time or a single key).

Nothing was deployed: no run directory, no client, no archive outside
`vault/exports/`. U7 is the owner's run.

## 6. Honest opens

- **What +0x09..+0x0B mean.** Non-zero on 5,208 of 14,571 files, 39
  distinct patterns, unread by the parser we disassembled. Possibilities
  (all UNVERIFIED): a field for the second FA1 consumer (MdlBloat reads a
  shifted view — anim §5), tool-side residue, or a parser path not yet
  found. The writer carries the region opaque, so U6 does not depend on
  the answer.
- **Whether the client accepts a STORED flags=515 row.** The stored
  fallback's class precedent is thin exactly here: flags=515 ships
  compressed 21,420:1 (datwrite blocker 2), and no client has ever read a
  unit-model row we wrote. The chain is intact and every archive rule
  holds, so if U7's load fails, the gate that fired is the result — the
  contract's kill/keep already frames this, and the stored-form question
  now sits beside the mid/tail suspects as the two named candidates.
- ~~`skelfile.sound_events()`'s latent crash~~ — RESOLVED under the
  review's scoped permission (§6.1): the accessor returns [] on the
  spanless majority, raw_tail is always `bytes`, and the regression is
  pinned in `test_skelfile.py`. Kept visible because the first version of
  this bullet recorded it as blocked on permission, and the record of a
  boundary moving belongs next to the boundary.
- **blk48 coverage at the default stride is 9 files** (deterministic;
  the full population runs under `--all`; the synthetic carries the shape
  regardless). n56 remains corpus-zero: the writer's n56 path, like the
  reader's, is synthetic-only and its stride disasm-only UNVERIFIED.
- **Non-FA1 chunks are carried verbatim by design.** The container writer
  re-derives only the framing (magic, type, chunk headers) and the FA1;
  FA0/FA5/FA6/FA8/FAD/FAE payload authorship is other rungs' work
  (modelfile decodes FA0 but no typed FA0 writer exists). U6's contract
  says exactly this; recorded so nobody reads "container identity" as
  "every chunk is typed".
- The rebuilt-archive fixture writes its journals beside the archive under
  `vault/exports/unitwrite/`; each test run rebuilds from the pinned study
  archive, so the artifacts there are throwaway by construction.

## 6.1 The adversarial review (2026-08-16) — accepted, with fixes

The review's hardest attack CONFIRMED the central claim: 51 mutation
classes over 8 payloads with zero surviving mutants; `encode()`
reproducing both anchors from a deepcopied representation with the
source `Skeleton` deleted; and the full-population identity
independently reproduced at 21,420/21,420 + 14,571/14,571. What it
changed is recorded in place, and summarized:

- **BUG-1 (the one that mattered — U7 fires this code):**
  `scale_sequence_keytimes` was not atomic; a mid-span refusal left a
  half-retimed repr that still serialized, reachable on the shell's
  sequence 16. Fixed by validate-all-then-commit; pinned by
  refusal-then-source-identity checks, synthetic and real (§5.1).
- **BUG-2:** the module docstring called the n40 bodies typed; they are
  8 typed bytes + a 10-byte raw tail, and the raw tails are a fourth
  opaque place. Corrected, and the figures moved with it (below).
- **RISK-1/2:** the opaque-carry pin summed declared regions only and
  could not catch a stash under a new key; replaced by a recursive leaf
  walk, and every published figure restated against the leaf truth —
  worm 883 (1.07%), shell 1,179 (4.00%, not ~1%), corpus 0.52% (§1, §2,
  §3). The declared/undeclared split stays visible everywhere.
- **RISK-3:** the container-identity headline now states the no-FA1
  population (6,849 of 21,420) and the per-anchor typed/verbatim split
  (§1).
- **NITs:** seam byte-diffs asserted as SET EQUALITY against the value
  change, not subset; the resolve_outdir delegation proven by
  monkeypatch instead of docstring prose; three entailed checks folded
  or struck; the chain-corruption control upgraded to corrupt the
  rebuilt archive's own MFT bytes.
- **Scoped skelfile permission**, exercised exactly: the sound_events
  crash fix + `bytes()` raw_tail, regression-pinned in test_skelfile
  (90 → 91 checks, floor 82 → 83).

Post-review counts: default 69 checks green (floor 69), `--all` 71
green, vault-less 33 + declared skip, red by design.

## 7. Provenance

All measurements are from the owner's pinned study archive
(`vault/dat_study/Gw.dat`, build 38797) through extractors in this repo;
scratch scripts and the full-population census JSON are preserved under
`vault/research/unitwrite/2026-08-16-u6/`. No ArenaNet bytes enter the
repo: fixtures are struct.pack synthetics with this repo's own literals;
the rebuilt archive, its journals and every written container live under
the vault. Offsets, strides, sizes and counts appear as MEASUREMENT per
the 2026-08-12 ruling (root `PLAN.md` §7 Q3). Second gate: the writer
inverts our own U1/U2 reader and uses our own datwrite/datmove tooling;
nothing derives from any upstream — no §6.1 register row is required.
