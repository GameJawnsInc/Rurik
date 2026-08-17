# The assembly resolver: wire → file closure — rung U4

Build 38797, the study archive `vault/dat_study/Gw.dat`, and the three keyed
live captures (`20260807T133758`, `20260807T143055`, `20260810T235916` —
the owner's own sessions against the live service; origin `live`, checked
per directory, never assumed). This is rung U4 of
[../unitmodels/PLAN.md](../unitmodels/PLAN.md); the committed deliverable is
`toolkit/mapdata/unitassembly.py` + `test_unitassembly.py` (55 checks,
floor 55). Labels are the project vocabulary
([../character/FINDINGS.md](../character/FINDINGS.md)).

**How this document was produced.** One session. Six predictions were
stated in the recon script before its first corpus run (§3; scored copy in
`vault/research/unitassembly/2026-08-16-u4/summary.json`); the resolver was
then committed and every number below re-measured THROUGH the committed
module — the corpus figures in this document are the test's pinned
literals, not the recon's. No client was launched; no byte of the binary
was newly read — this rung composes U1's `skelfile.py` and U3's
`mdlrefs.py` and the wire compiler `npcdefs.py`, and adds no disassembly
of its own.

---

## 1. The answer in one page

**Every unit definition the live wire ever declared resolves to a closed
archive file set, 54/54** (MEASURED). Given a definition — the 0x0056
shell file id plus the 0x0057 body ids, from a capture or from a
`content/*.toml` row — the resolver walks exactly what the client's
loaders would touch: shell → FA8 links recursively through a visited set
(the cached by-id loader `0x00794260`'s closure, computed instead of
cached) → bodies → FA5 textures → FA6 sound descriptors → their type-8
chunk-0x1 audio payloads → FAD/FAE. Every id must resolve in
`file_id_table(raw=True)` and every walked container must decode, or the
resolution records a named problem; closure is OUR assertion, the same
posture as U1/U3.

- **54/54 closed and 54/54 geometry-complete** — 1,393 distinct files.
  Per-role distinct: shell 32, body 40, link 134, texture 113, sound 241,
  audio 830, fad 8, **fae_model 0**. Set sizes 3 (def 1400) to 233
  (def 1482), median 158 (def 1470). Deep walk ~60 s.
- **The COMPOSITED rule is derived, not assumed**, and the wire agrees
  with the archive on every definition: `needs_body` (= the shell carries
  no FA0) equals wire presence of 0x0057 **54/54 pooled**. The §5.4
  triple, populations now NAMED (§4): capture 20260807T143055 alone —
  **8/8** 0x0056-only shells carry FA0 (reversed rule 0/8, the failing
  control), **36/36** with-0x0057 shells lack it, 33/33 distinct model
  ids carry it; pooled — 11/11, **43/43 per-definition** (this is the
  population unitmodels §5.4's "43/43" was counting), 40/40 distinct.
  Independently, the FA1 flag bit agrees with FA0-absence on **161/161**
  carriers the closures touch (U1 measured the same equivalence at
  14,571/14,571 archive-wide).
- **The named first case**: definition 1471 = hatcher shell 116228 + body
  116703 resolves to exactly **232 files** (1 shell + 1 body + 15 links +
  3 textures + 44 sounds + 168 audio), pinned id-by-id in the test; the
  worm (1442 = 116366, 0x0056-only) beside it at **75 files**. The
  content rows `npc.hatcher` and `npc.lakeside_worm` resolve to the
  **identical sets** through the same path — which is what lets our
  server serve a definition whose ids come from content rows
  (acceptance 5).
- **Pooling is origin-gated**: capture directories that do not all
  classify as the wanted origin (`origin.py`, three-valued) are refused
  with both origins named; the test proves the refusal beside a positive
  control on synthetic capture directories.
- `npcdefs.Definition` now carries **`model_ids` — the full 0x0057
  list** — because two pooled definitions (1496/1497) carry TWO bodies
  each (116759+116760) and `model_id` alone under-described them. A
  repeated 0x0057 that disagrees is refused, same posture as `declare()`;
  MEASURED: 101 composite messages, zero disagreements (P6).

## 2. The corpus and the entry points

The wire half is `npcdefs.read` unchanged — its interval join, its
byte-exact framing refusals, its declaration-disagreement refusal — via
`definitions_from_captures`, which first requires every capture
directory's `wire.jsonl` to classify as one origin. Pooled: **54 declared
definitions** (44 in 20260807T143055 alone — both figures reproduce
`studies/smsg/FINDINGS.md` §0x0056 and `test_npcdefs.py`'s literals).
0x0057 list lengths by definition, pooled: length-1 ×41, length-2 ×2 —
the four length-2 *messages* unitmodels §5.4 counted are these two
definitions declared twice each.

The content half is `UnitDef.from_content_row`: `file_id` required,
`model_id` optional — exactly the split `content/npcs.toml` ships, where
the worm's missing `model_id` is deliberate and inventing one is the
guess its comment warns about. A row without `file_id` is refused.

## 3. Predictions, stated first, and their scores

Stated in the recon script before its first run; re-scored through the
committed module (the numbers here are the committed run's).

| # | prediction | score |
|---|---|---|
| P1 | 54/54 pooled definitions resolve closed | **HELD** — 54/54, zero problems anywhere |
| P2 | 143055: 8/8 only-0x0056 shells have FA0; 36/36 with-0x0057 lack it; model ids all have FA0 | **HELD** — 8/8, 36/36, and 33/33 *distinct* model ids; the study's "43/43" turned out to be a different population (§4) |
| P3 | COMPOSITED bit ⟺ no-FA0 on every closure FA1 carrier | **HELD** — 161/161 |
| P4 | hatcher content row ≡ wire definition 1471 | **HELD** — identical 232-id sets (and worm ≡ 1442, 75 ids) |
| P5 | every FA8 link target: type-2, FA1 with seq_count ≠ 0, no FA0 | **HELD** — 134/134 distinct link targets |
| P6 | repeated 0x0057 lists never disagree, pooled | **HELD** — 0 disagreements over 101 messages |

Controls that fail, alongside: the reversed COMPOSITED rule scores 0/8
and 0/36; an id outside the raw table leaves a set OPEN with the problem
named; a map file (ffna type 3) as shell is refused, not walked; a
live+ours capture mix refuses with both origins named.

## 4. The "43/43" reconciliation — a population, not a discrepancy

unitmodels §5.4 states the wire cross-check as "8/8, 36/36, 43/43" and
attributes all three to capture 20260807T143055. MEASURED here: that
capture has **33** distinct 0x0057 model ids (33/33 carry FA0), and no
population inside it counts 43. What DOES count 43 is the **pooled
number of definitions carrying a 0x0057** (41 one-body + 2 two-body),
and all 43 have every body carrying FA0 — so the study's figure was the
pooled per-definition count, its caption just did not say so. The fact
it was standing in for is true in every granularity measured: per
definition 43/43 pooled, per distinct model 33/33 (143055) and 40/40
(pooled), per shell 8/8 + 36/36 (143055) and 11/11 + 43/43 (pooled).
The test pins all of them so the next reader does not re-litigate this.
(The related §5.4 aside "56/56 ids resolving" is that capture's distinct
file-id union: 6 only-0x0056 shells + 17 with-0x0057 shells + 33
models = 56 — also reproduced.)

## 5. What the closures look like

MEASURED over the 54 definitions, deep walk (artifact:
`vault/research/unitassembly/2026-08-16-u4/closures.jsonl`, one JSON row
per definition with every file's roles and facts).

- **A unit is mostly sounds, by file count.** Audio payloads are 830 of
  the 1,393 distinct files (60%); sounds + audio together 77%. By bytes
  the ordering inverts: the 113 textures total ~12.8 MB against the 830
  audio files' ~6.5 MB. Model-role files: 201 distinct ffna type-2;
  sound descriptors: 241 type-8; textures/audio are non-ffna containers
  (951 files) — ATEX and MPEG payloads respectively, recorded by magic,
  not walked.
- **Shells are heavily shared.** 54 definitions use only 32 distinct
  shells: 116228 serves EIGHT definitions (1458–1508 — the hatcher's
  shell is Ascalon's generic collector-body shell), 116227 seven,
  116225 five, 82023 three, and three more serve two each. A
  "definition" is a (shell, body) pairing far more often than a file.
- **Five files hold two roles**: 16271, 116225, 116227, 116228, 128436 —
  every one a SHELL that is simultaneously an FA8 LINK target inside
  *other* definitions' closures (116228 is linked from definition 398's
  chain; 128436 from 272's). The client's one cached loader makes this
  free; for the resolver it is why roles are a set, not a scalar.
- **The smallest closure is 3 files** (definition 1400: shell 128436 +
  body 129925 + one texture): a composite shell carrying NO sound list
  and NO links at all. The largest is 233 (1482, a hatcher-shell
  definition with a different body). Median 158.
- **FAE never occurs** — the archive-wide population is 6 chunks and
  none intersects any live-capture unit. The `fae_model` role is
  fixture-covered only; nothing in this corpus exercises it.
- **FAD is rare on units**: 8 distinct targets across 5 definitions
  (301, 391, 397, 1480, 7809). Included under their own role because the
  list is parsed into the geometry object (A+0xFC), with the honest
  caveat that its consumer is unread (U3 §8.1) — whether the client ever
  FETCHES an FAD target is UNVERIFIED, and a caller can filter the role.
- **FA5 null slots exist even here**: exactly 2 across the 54 walks.
  The terminator rule (U3) is load-bearing on real units, not only in
  the archive-wide census.
- **Every one of the 134 distinct link targets** is an FA0-less
  COMPOSITED skeleton with `seq_count != 0` — the exact shape the
  client's per-link gate (`0x00794917`) requires, reproduced through the
  resolver rather than asserted from U3.

## 6. What the closure does and does not claim

- `closed` means: every REFERENCE the id-addressable chunk graph makes
  resolves, and every container on the walk decodes. It does **not**
  include the mid/tail companion streams (0xBB8–0xBC1, 0xFA4/7/B/C):
  those rows are deliberately un-addressable by file id (0 of 21,420
  rows, unitmodels §2.2) and ride the same MFT rows via `nextStream` —
  the client reaches them through the archive's stream linkage, a hop
  U3 left OPEN (§6.1/§8.4). The closure is the complete *file-id*
  reference set; U6's archive writer inherits the streams with the rows.
- `fae_model` recursion is RECONSTRUCTION: FAE is the n3E timed
  model-load event table (U2), a *runtime* load handed to the same
  loader — untestable on this corpus (zero occurrences).
- The `sound → audio` hop uses `mdlrefs.type8_deps`, whose count-less
  fixed-6 framing is MEASURED shape, not a disassembled rule (U3 §8.7).
  All 241 descriptors in these closures decode under it without
  remainder.
- `npcdefs.to_toml` still emits `model_id` singular, so an emitted
  content row for 1496/1497 under-describes their two-body composite.
  Recorded for R4c rather than changed here — the row schema is the
  content compiler's contract, and nothing served today uses those two
  non-combatant definitions.

## 7. Provenance

Every value here is a measurement — ids, counts, sizes, bit states —
made by extractors in this repo (`unitassembly.py` over `archive.py`,
`skelfile.py`, `mdlrefs.py`, `npcdefs.py`) from the owner's own build
38797 archive and the owner's own live captures; per the 2026-08-11
ruling these are the permitted side of the gate, and no asset bytes are
reproduced anywhere (the artifact JSONL holds ids, roles and facts, not
content). The captures are the owner's sessions on the secondary
account; origin is stamped in the artifacts and checked by the tool.
Second gate: nothing here derives from any upstream — the closure
algorithm is the client's own loader shape as U3 disassembled it, and
no third-party table or code was consulted.
