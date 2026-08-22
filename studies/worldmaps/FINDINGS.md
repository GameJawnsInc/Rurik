# World maps — authored areas that coexist

The arc: retire the two constraints that keep authored areas one-at-a-time and
small — the uncompressed install (every authored map had to be SMALLER than
what ArenaNet compressed into its row) and the displacement mechanism (every
authored area overwrites a live retail map's rows, currently 71496/71497 via
map 143). W1-W4 did that and are landed, the even ones client-proven; W5-W7
carry it forward into the authoring LOOP (headroom, scale, and a walked
region). Client launches are staged A9/A10 style with predictions registered
first. W8-W9 are the arc's first PROBE rungs -- authored maps used as an
instrument to ask the client questions rather than to deliver content -- and
their subject is WORLDMAPS-W7's depth cut.

**Identifiers.** `WORLDMAPS-W<n>` = rungs of this arc's ladder, defined in this
document. Convention: [studies/idents/CONVENTION.md](../idents/CONVENTION.md);
never bare `W1`–`W9`, which collide with `studies/profession` among others.

Labels per [studies/character/FINDINGS.md](../character/FINDINGS.md).

**READ [AUTHORING.md](AUTHORING.md) FIRST if you are here to build a map**, not
to audit a rung. It is the distilled operational half of this document and it
carries the corrections in place; this file is chronological, so a cold reader
meets W17 and W19 several screens before W20 reinterprets them, and meets W13
before the correction that it measured the FLOOD SEED rather than the player's
spawn. Both are recorded here in full -- but in the order they happened, which
is the wrong order to learn them in.

## WORLDMAPS-W1 — deploy installs compressed. LANDED 2026-08-20

**OBSERVED (offline; the client witness is WORLDMAPS-W2's question).**
`deploy.py --install` now compresses the assembled Stripped partner with
`gwenc.encode` and judges replace-vs-relocate on the COMPRESSED size, threading
`--compression 8 --expect <plain blob>` through BOTH writers (`datwrite
--replace` and `datmove --move`) so the deviation cannot reappear on the
relocate arm. `--stored-install` preserves the old behavior byte-for-byte as
the control arm. The readback now asserts what a READER gets back (Archive.read
decompresses), plus a second refusal that the row is MARKED with the code we
asked for — "the payload is right" and "the row is marked the way retail marks
it" are two claims.

**Measured gain, two corpora — do not mix them when quoting.** Against build
38797's real donors (`install_bytes`' docstring, the CLI's own print):
32×32 3,941→1,316 B (33.4%), 64×64 10,654→2,012 B (18.9%), 96×96
21,786→2,828 B (13.0%) — so against map 143's shipped 4,608 B partner
reservation, **96×96 replaces in place where 32×32 was previously the largest
map this toolkit could install at all**. `test_deploy.py` §4's fixtures (no
donor constants) measure 20.2% / 12.7% / 9.7% on the same dims; the test
bounds the claim only as "strictly smaller", never a pinned number.

Retail's own Stripped partners are compression-8; ours were the deviation
(readable in FINDINGS 35–58 of `studies/customarea`, but the deviation). W1
restores the retail shape. `test_deploy.py` floor 35→56 (§7: five real
installs against a hand-laid archive whose reservation the FILE chooses; §5's
AST pins moved with the dispatch and got stronger). Skeptic verdict clean,
zero must-fix; the ten notes are recorded in the arc's workflow output and the
two that were doc-level (RUNBOOK's stale live-constraint sentence, the RUN
note's log-naming ambiguity) were fixed at integration.

**Known consequence, deliberately unwired:** a compressed install SHRINKS the
row (map 143's partner 4,608→1,536 B after a plaza), so iterating small→large
relocates where it used to sit still. `datwrite --replace grow_to=` is exactly
the flag for it and is its own change with its own gate; folding it into W1
would have made a failed install ambiguous between two mechanisms.

## WORLDMAPS-W2 — the first compression-8 MAP row a retail client reads. RAN GREEN 2026-08-20

**OBSERVED (retail client, build 38797, one map, one launch per arm —
agent-driven on the owner's explicit go-ahead; the readouts are mechanical, so
the owner-drives boundary did not bite).** Two arms on the C2 copy, control
first, one flag apart. **The client's re-bloat compiler READ the partner we
compressed and built the identical map**: arm B's readback matches arm A line
for line and both reproduce FINDINGS 56 (6,627 B path chunk, 55 trapezoids,
1024/1024 heights, env/sound verbatim, 5/5 props, spawn in one trapezoid);
the server's own navmesh line named the same 55 on the unarmed second run,
both arms. The partner was never touched by the client — after arm B's
session, still 0x81B5000, still 1,316 B (33.4% of stored), still compression
8 — and the head came back REBUILT at ArenaNet's own trapezoid count.
Post-flight: the diff names exactly the two expected rows, `--assert-safe`
clears everything. Full scoring of P1–P7, artifacts, and two honest caveats
(the sheet's Gw.log capture is clobbered by the serve run's second client;
the serve check's population half hit the server's benign no-rows line in
both arms, orthogonal to compression — since closed on main, `ec5f426`:
`serve_run` gained a third verdict SERVED-UNPOPULATED, and the suspected
content drift did not happen, plaza never had a spawn row and FINDINGS 56's
"5 of 5" is its PROPS readback) are in
`vault/research/worldmaps/WORLDMAPS-W2-RUN.md` §RESULTS.

**What this closes**: the last place an authored map deviated from retail's
own shape, and the in-place size cap — 32×32 before, at least 96×96 measured
now. Scope travels with the witness: one map, one shape, one build.

## WORLDMAPS-W3 — an authored area under its OWN file id. LANDED 2026-08-20

**OBSERVED (offline; the client witness is WORLDMAPS-W4's question).**
`deploy.py --install` now ALLOCATES the map chain when the area's maps.toml
row carries `created = true` and its file id binds nothing in the target
archive: `create_streams` builds `[Stream(b"", 259), Stream(gwenc_stream, 1,
extra_bytes=8, expect=plain)]` and `create_chain` drives
`datalloc.plan_alloc`/`alloc`, journaled, spilling the compression-8 stream
BEFORE the plan (a refused allocation still leaves behind the thing that was
refused). The head is born armed — zero length, the re-bloat trigger — and is
not armed again. A bound id falls through to the normal install (idempotent);
a non-map-chain shape, a taken id, or a bit-31 sibling each refuse by name
(the sibling refusal is the CALLER's because `plan_alloc`'s exact-membership
gap — archivewrite §17.5 — is still open). `create_note()` answers on EVERY
run, including build-only dry runs, so "the create branch would fire" is
previewable without a write.

**The content rows, and one ruling.** `content/maps.toml [map.166]`
(created = true, file id 0x5F0B0, source="invented") and
`content/areas.toml [area.frontier]` (64×64, donors by file id per the sculpt
pattern). The spec said the area "may keep map_id 143" — **not implementable**:
deploy joins area→map row BY map_id, so pointing at 143 resolves the
displacement row and the create branch could never fire. Ratified: the area
points at its own [map.166]; the map id remains a cosmetic label exactly as
[map.143]/[map.144] describe theirs. P1 (the full allocation plan against the
C2 copy, read-only) was independently re-measured and reproduces byte for
byte, row indices and MFT arithmetic included.

**A created row is a THIRD content state, and it nearly deleted a guard**:
`contentids.check` returned FATAL for the unbound created id, which — under
`served=None`, the fail-closed default — would have refused every loopback
launch in the repo. It now records an absent created id as a printed SKIP and
judges it normally the moment an archive binds it; `test_contentids` holds
created rows out of both archive-selecting scans. Floors: test_deploy 56→92,
test_content 39→40, test_contentids 19→20.

**Residuals recorded, none blocking** (skeptic notes, fix pass took the two
must-fixes): the born-armed clause has no check behind it; `created = true`
beside an id that binds a RETAIL map chain silently returns to displacement
(the install fall-through is also the displacement path — a row comment names
it); the create path overwrites an existing `<area>_alloc.json`; contentids'
created-skip fires before the server side is consulted; two of `map_chain`'s
four shape refusals are hand-verified but unexercised by the suite.

## WORLDMAPS-W4 — the created chain meets the client. RAN GREEN 2026-08-20

**OBSERVED (retail client, build 38797, one map, one launch cycle —
agent-driven on the owner's go-ahead, mechanical readouts).** The client
resolved a map chain born under file id 0x5F0B0 — an id nothing had ever
bound — logged FINDINGS 35's exact re-bloat line naming it
(`'0x05f0b0' failed to load.  Attempting to re-bloat.`), compiled our
terrain from the 2,028 B compression-8 partner, wrote the head back REBUILT
(0 -> 6,012 B comp 8, relocated, 64 trapezoids over 1 plane), left the
partner byte-untouched across three sessions, and kept the registration
through its own Flush — the diff names only our two created rows plus the
client's scratch rows 8315/8316, nothing UNCLASSIFIED. Readback 6/6 including
the spawn-in-one-trapezoid check [map.166] recorded as owed; the server's own
navmesh line named the same 64. All ten predictions scored in
`vault/research/worldmaps/WORLDMAPS-W4-RUN.md` §RESULTS, which also records
the run's two lessons: a fresh run directory needs its own firewall CAGE (the
first launch was refused fail-closed — the cage is per-path; owner ran
isolate_client.ps1 and the re-run proceeded), and the launch stages were
split to keep the compile run's Gw.log from the serve sessions (W2's capture
defect, fixed procedurally). The throwaway was delta-captured (PROVEN,
`vault/deltas/worldmaps-w4`, 24,736 B) and deleted — datdelta's first real
customer.

**What this closes**: FINDINGS 36 item 4 (the born-armed, never-bound case);
A9's witness extends from "a created chain is READ" to "a created chain is
COMPILED"; and displacement is retired — the next authored area does not
have to take rows 71496/71497 hostage. Still unestablished, per the sheet:
survival across a client patch, more than one created map per archive (the
C2-lineage MFT slack is exactly one chain), a second created chain in one
session.

## WORLDMAPS-W5 — headroom: an area declares its own budget. LANDED 2026-08-20

**OBSERVED (offline, this tree).** The gap W1 recorded and W4 inherited: a
compressed install SHRINKS the row, and a created partner is sized to its exact
payload — `datalloc.Stream` has no reservation parameter and `_place` computes
`blocks_for(len(data))` — so the *second, larger* install of any area, created or
displaced, relocated. `datwrite.replace(grow_to=)` was the flag for it and had
exactly one caller (`restore()`), because `grow_to` needs a "what this row was
GIVEN" number and **a row's true reservation is recorded nowhere**
(`datwrite.py:875-880`: "the bound therefore has to come from GEOMETRY").

**The answer is that the AREA states it.** `content/areas.toml` rows carry an
optional `reserve_bytes` — an authoring budget with provenance, not an inference
— `datalloc.Stream(reserve=)` honours it in placement block-sizing ONLY (size,
crc, `expect` and every existing gate stay bound to the real payload), and
`deploy.install_partner` spends it: a stream past the row's current reservation
but inside the declared budget now GROWS BACK IN PLACE instead of relocating.
Measured: a created chain given a 2,048 B budget takes a 1,952 B second install
at the same offset, where the same install with no budget relocates. Before this
rung that arm did not exist.

**Two things the skeptic corrected, and both are the interesting half:**

1. **The grow arm is scoped to a row WE created.** The first build gated only on
   the budget, so an area declaring `reserve_bytes` beside a DISPLACED retail row
   would have grown ArenaNet's row into blocks it never gave us. Now
   `install_partner(..., created=)` requires both, the preview mirrors the same
   gate so it cannot promise a verb the install will not pick, and the relocate
   line says why: *"this row was not created by us, so what it was given is
   ArenaNet's statement and not ours."* The control is one field apart and takes
   the opposite verb.
2. **A check that asserted only "it raised, and nothing was written" could not
   fail for its own reason.** `datmove` independently refuses the same lie and
   re-raises the same sentence with the archive byte-identical, so a fallback
   recogniser that misclassified a declaration fault as a claimant conflict
   stayed invisible — MEASURED by breaking it: the run printed "THE GROW GATE
   REFUSED: <a temp-file path>" and relocated around a bad declaration while the
   suite stayed green. The check that catches it is the NEGATIVE on what the run
   SAID it was doing.

Also fixed at the root: a raw `datalloc.Refused` escaped `create_chain` past
deploy's own handler (exit 1 with a stack instead of exit 2 with a remedy), and
`int(area.get("reserve_bytes", 0) or 0)` silently truncated `2048.5` and let
`-512` through — `area_reserve()` now refuses a non-int, a bool and a negative,
naming the file to edit. Floors: `test_deploy` 112→167, `test_datalloc`
177→203. Four sabotages driven by hand, each red on the guard it names.

**Still open, deliberately:** `grow_gate_refusal` joins on datwrite's MESSAGE
TEXT (four markers) and fails SAFE if datwrite rewords — a typed refusal out of
`_grow_gate` is the strong fix and belongs with the residuals pass, since it
touches datwrite, which this rung was told not to.

## WORLDMAPS-W6 — the scale ladder, measured. LANDED 2026-08-20

**OBSERVED (offline, real runs against `vault/run/2026-07-29_221c13772c7a-c2`,
generator `plaza`, donors by file id 0x1B97D→row 7982 and 0x22E2C→row 46196).**
`toolkit/mapdata/mapscale.py` walks a ladder of dims through deploy's own
pipeline and reports what each costs, because the corpus stopped at 96×96 and
`install_bytes`' docstring explicitly refuses to extrapolate its three points:

| dim | cells | authored | comp-8 | % stored | blocks |
|---|---|---|---|---|---|
| 32×32 | 1,024 | 3,822 B | 1,256 B | 32.9% | 3 |
| 64×64 | 4,096 | 10,535 B | 1,956 B | 18.6% | 4 |
| 96×96 | 9,216 | 21,667 B | 2,768 B | 12.8% | 6 |
| 128×128 | 16,384 | 37,026 B | 3,572 B | 9.6% | 7 |
| 192×192 | 36,864 | 80,916 B | 4,232 B | 5.2% | 9 |
| 256×256 | 65,536 | 142,195 B | 4,820 B | 3.4% | 10 |

All six round-trip **100% of samples exactly**; assemble+compress at 256×256 is
0.28 s. **Authored maps compress BETTER the bigger they get** — 64× the cells
costs 37× the stored bytes and only 3.8× the compressed stream, because only
terrain tag 1 is entropy-coded and everything a generator emits around it is
repetitive raw bytes.

**The result that matters is which budget binds: not bytes, ROWS.** A 256×256
partner is ten blocks against a largest usable run of 953,856 B on that copy —
the byte budget is not close to binding at any dim on this ladder. MFT slack is:
the 38797/c2 line has 48 B = 2 rows = exactly **one** more created map; the
38833 copy has 424 B = 17 rows = **eight**. Any multi-area work belongs on the
38833 line; single-region work can stay on the proven 38797 one.

Two guards the skeptic added are worth naming because they are the same defect
class this repo keeps meeting: a `Capacity` restored from a JSON report
manufactured a FALSE placement answer ("no usable run is big enough" for a
stream its own summary said fits by 197×) and now refuses as un-measured, and
`Rung.from_dict` accepted MISSING fields so an empty record claimed a perfect
round trip (`None == None`). Floor 62 (66 under `--big`), 1 declared skip.

**Open, and NOT chosen between two readings:** `dat_study_38833`'s largest
usable run measures 2,892,800 B — *unchanged* after the 2026-08-17
extent-projection fix that `studies/archivewrite` §1.5 says should have withheld
it. Either the fix does not reach that run (a live gap) or §1.5's diagnosis
needs amending. Re-measured read-only 2026-08-20; recorded, not resolved.

## The W3 residual guards, closed. LANDED 2026-08-20

**OBSERVED (offline).** All five residuals W3 recorded, plus the typed refusal
W5 deferred:

- **R1** the born-armed guard (deploy.py reads the ARCHIVE's own `head.size == 0`
  rather than trusting `create`) was live but untested — now tested both ways.
- **R2** `created = true` beside an id that BINDS could silently return to
  displacing a retail map, because `map_chain` checks shape only. The install
  now requires evidence the chain is OURS. **The skeptic caught the first
  design binding that evidence to the archive's PATH**, which refused an honest
  re-deploy of our own chain on a copy — so it binds to the archive's own BYTES
  instead: the `<II`(file_id, head_row) file-id record at the offset the alloc
  journal recorded, which survives a whole-file copy, a rename and a partner
  relocation. That is the cage's lesson (`dhbuild` reads the bytes, never the
  filename) applied on the archive axis. The refusal now names the recoverable
  state first — copy the journal next to the archive — with "allocate under a
  fresh id" as the last resort it actually is.
- **R3** deploy's create path bypassed the refusal datalloc's CLI documents as
  "the only way back from an allocation" and could truncate an existing
  `<area>_alloc.json`; it refuses now, before the spill.
- **R4** contentids decided the created-row skip from the client table alone,
  before the server side was consulted, so a real divergence read as a benign
  pre-creation state. It consults both now.
- **R5** three of `map_chain`'s five refusals had no fixture; one each.
- **R6** `_grow_gate` gained a TYPED refusal so deploy no longer joins on
  datwrite's message text (the text markers stay as a documented fallback, and
  datwrite's messages and behaviour are byte-identical for every existing
  caller).

**And a mutation sweep found what review argued about**: three of the four
structural conjuncts `allocation_recorded` documents were exercised by nothing —
drop any one and the suite stayed green. One bent-journal fixture each (head
flags 259→3, nextStream 17→18, partner flags 1→3) plus a CONTROL that rewriting
a field to the value it already held is still evidence. Post-fix the sweep reads
1+ red per conjunct, 0 for the control.

**One regression this pass introduced and the orchestrator caught at
integration, worth recording because the near-miss is the lesson**: a new
"the check produced findings at all" assertion in `test_contentids` turned a
DOCUMENTED environmental state — another session's client holding a 4 GB copy
open, which the W4 sheet names — into a red suite, where the same file had
skipped and stayed green before. It was nearly waved off as that known flake;
the control that refuted the excuse was running HEAD's own version against the
same locked archive and watching it pass. The guard now skips when nothing
could be READ and still goes red when an archive was read and measured nothing
— verified by driving the readable-but-empty case, which stays red. Floors:
`test_deploy` 167→203, `test_datwrite` 212, `test_contentids` 29.

## WORLDMAPS-W7 — the region walked. RAN GREEN 2026-08-21

**OBSERVED (retail client, build 38797, one map, one launch cycle —
agent-driven on the owner's go-ahead, mechanical readouts).** The client
compiled a **256×256** authored map — 65,536 cells, 16× the largest it had ever
compiled for this project under compression and a created chain together — from
a two-row chain born under `0x5F0B1`, an id nothing had ever bound. It logged
`Perf: Map file '0x05f0b1' failed to load.  Attempting to re-bloat.`, built a
mesh of 60 trapezoids, wrote the head back at **13,584 B** (decoding to 467,132
B of Bloated map — more than twice the largest head it has ever written for us),
left the 4,912 B compressed partner byte-untouched, and kept the registration
through its own Flush. Readback 6/6 including the spawn-in-exactly-one-trapezoid
check `[map.165]` recorded as owed; the server's own independent load named the
same 60 (`SERVED-UNPOPULATED` — the third verdict added the same day, because
the area deliberately carries no spawn rows). The diff names only our two added
rows plus the client's own scratch rows 8315/8316 relocating, nothing
UNCLASSIFIED, and `--assert-safe` clears 10/10 with 177,329 payload CRCs.

**The sharpest result is a prediction that could have failed.** While the sheet
was being written, the client's own 64×64 mesh was measured and revealed a
**depth cut**: ground at or below a threshold bracketed in (43, 47] stored units
is absent from the compiled navmesh — 0 of 1,003 cells at +47 and deeper against
63.6% at +43. Because `gen_plaza`'s dip descends 4 units per cell without limit,
that predicted roughly HALF a 256×256 rect would be missing: **50.55% surviving,
cut at Chebyshev ring 20**. **Measured: 50.54%** (33,120 of 65,536 quad centres
inside the mesh), the mesh beginning at x = 10,464 — grid column 109, ring 20,
exactly where the model put it. A model built at one size predicted the
next-but-two to one part in ten thousand. Registering the naive "coverage holds
at ~88%" would have scored a correct run as a catastrophic scale failure; "the
boundary does not move" is the form of the claim that cannot be satisfied by
accident.

Note the trapezoid COUNT barely moves with size — 55 / 64 / 60 at 32 / 64 / 256
— which follows from the coverage result rather than contradicting it: half the
rect is outside the mesh and what remains is dead-flat apron decomposing into a
few very large trapezoids. Judging on the count alone would have read 60 as a
regression against the 64×64 map's 64, which is exactly the trap
`studies/customarea` FINDINGS 38 records.

Full scoring of P1–P10, and the one procedural deviation — step 2 ran as a
single invocation, so `rebloat.verify` had no before-image and P5 was scored
from the bytes instead (the head's recorded before-state is size 0, born armed;
its after-state decodes as a map with trapezoids, which is `classify`'s own
definition of REBUILT) — are in
`vault/research/worldmaps/WORLDMAPS-W7-RUN.md` §RESULTS. The throwaway was
delta-captured (17 spans, **46,033 B** for 4.2 GB, PROVEN byte-identical) and
deleted.

**Still open, and stated rather than implied**: anything above 256×256 (the
format allows 16,777,216 cells; this run used 65,536); a created row given MORE
blocks than it holds (W5's `reserve_bytes`, deliberately not spent here so a red
result could not be ambiguous between the size and the tail); two created maps
in one archive (the 38797 lineage has rows for exactly one — the 38833 line is
where that ladder belongs); and the depth cut's MECHANISM, which has three
readings — the borrowed environment's water plane, a compiler depth bound, the
borrowed Zones chunk — and one cheap disambiguating run: the same 64×64 map
with `environment = false`.

## WORLDMAPS-W8 — what cuts the deep ground out? NOT the water. 2026-08-21

**OBSERVED (retail client, build 38797, two arms one field apart —
agent-driven).** WORLDMAPS-W7 left the depth cut's mechanism UNVERIFIED with
three readings. This run kills the leading one.

Two arms on the `-probe` copy, both displacing map 143's rows, differing only in
`environment`: **the compiled meshes are identical to the cell** — 64
trapezoids, 7,660 B path chunk, mesh x 1248..6144, 2,582/4,096 = 63.04%
coverage, leftmost column 13, in BOTH. **The borrowed Pre-Searing environment
chunk does not carry the cut.**

**The null is not vacuous, and that is the part worth reading.** Two controls
make it readable: the treatment was verified at the bytes — the installed
partner carries no `0x10000009` and no `0x11000009` while `SOUND` and its deps
are present, decoding to 9,994 B against `sculpt`'s **10,714 B**, a 720 B
difference closing to the byte as 639 (ENV) + 65 (ENV_DEPS) + two 8-byte chunk
headers — and the instrument was shown
to DETECT the cut, because arm A reproduces W7's recorded witness (cut at column
13, 63.04% against 62.99% under a slightly wider sample). A null measured with
an instrument that cannot see the effect, or with a treatment that never
happened, is the failure shape this repo keeps meeting; both are closed here.

Also settled in passing: **a map with no environment chunk compiles and serves
normally** — `stripbuild`'s OPTIONAL table is correct at the client, no assert.
(The re-bloat LOG line survives for arm B only: each launch overwrites `Gw.log`,
so arm B's client clobbered arm A's. Arm A's recompile is proved from the bytes
instead. Third time this defect has cost evidence — bank the log per arm.)

**The evidence got STRONGER under attack**, and two of my own claims were wrong.
An adversarial pass returned *stands* and recovered what the run had not:
**the compiled navmeshes are BYTE-IDENTICAL**, not merely equal on three
statistics — `shoals_rebloat.json`'s journal preserves the exact 6,144 B arm B
overwrote, which is arm A's compiled head, and all ten shared chunks match byte
for byte (path chunk 7,660 B, sha256 `dfa1a5cc…` in both) with the only
difference in either direction being arm A's ENV pair, 41,432 − 40,712 = 720
exactly. **The fallback hypothesis dies at the output side too**: arm B's
COMPILED head carries no `0x20000009` either, so no donor, global or cached
environment was available — and `deploy.readback` could not have caught that,
because `deploy.py:1512-1518` SKIPS the environment assertion when the staged
map has none, a check that cannot fire. (**CLOSED 2026-08-21.** That loop
INVERTS now rather than skipping: an optional chunk the staged map omits gets a
row asserting the compiled map carries none either, printed in the same verdict
block as every other row — so the fact this run recovered by hand out of the
allocation journal is asserted on every future run instead. `test_deploy.py`
§11 drives it present, absent and sabotaged, the sabotage being a compiled map
that DOES carry the chunk we omitted; against the old loop that arm returned
`bad == []`, indistinguishable from the honest absence recorded above. Floor
203 → 213, and reverting the fix reddens 8 of §11's 10 checks.) **And the
client's compiler is deterministic**, shown accidentally: the head before arm A and the head arm A
produced are byte-identical (`78c0174e…`), which is what licenses reading
identical output as "the input did not matter". Two corrections to my own
write-up: `sculpt`'s partner is 10,714 B, not the 10,535 B I lifted from W6's
modelled ladder (a different corpus, no donor constants — the arithmetic did not
close), and "re-bloat line present in both arms" had no surviving artifact for
arm A, because each launch overwrites `Gw.log`.

**What survives**: a depth bound in the compiler itself, or the borrowed 34-byte
Zones chunk. The Zones reading is the cheaper next test and nothing has ever
varied it — every authored area in this project carries the same 32x32
template's copy. Full scoring in
`vault/research/worldmaps/WORLDMAPS-W8-RUN.md` §RESULTS.

## WORLDMAPS-W9 — the Zones swap is IMPOSSIBLE, and that is the finding. 2026-08-21

**OBSERVED (retail client, build 38797, two arms).** The last cheap reading for
WORLDMAPS-W7's depth cut was the borrowed 34-byte Zones chunk — the one thing no
authored area had ever varied. It cannot be varied by a donor swap: **a foreign
zone table breaks the client's map compiler.**

Measured first, so the swap would have been a clean single variable: across all
349 map heads the HEADER chunk has **one** distinct payload archive-wide
(`2411873903000000`, 349/349) while ZONES has **308** — so `constants_file_id`
selects the Zones chunk alone. Ours is the minimal 34-byte form, shared by 25
maps; real maps carry zone material definitions with `.ini` paths and float
arrays up to 15,870 B.

Both arms died inside the re-bloat compile — `Gw.log`'s last line in each is
`Perf: Map file '0x0287d3' failed to load.  Attempting to re-bloat.`, with the
server already through `INSTANCE_LOAD_FINISH`:

| arm | Zones | outcome |
|---|---|---|
| Coastal Gate (466× ours) | 15,870 B | **CRASH**, `c0000005`, write to `0x1acff000` |
| Sparring Basics (60× ours) | 2,030 B | **HANG** at Loading 100%, 98% of a core, 1.19 GB flat |

**What it establishes.** The compile path CONSUMES the Zones chunk — which
beside WORLDMAPS-W8 is a sharp contrast: deleting the environment chunk changed
the compiled mesh not by one byte, while swapping the zone table kills the
compiler. And a zone table is COUPLED to its map: two foreign ones from opposite
ends of the size range, both fatal. **The coupling is not identified.**

**What it does not establish**: anything about the depth cut, since no mesh was
produced. And it REFUTED a piece of the design's own reasoning — I registered
that richer-than-referenced was the safe direction; both arms went richer and
both were fatal.

**Where this leaves the depth cut.** A donor swap is exhausted as a method. The
next rung must author a MODIFIED version of our own 34-byte table (vary one
field, keep the shape), which needs that layout read first — nothing in this
repo has done it. Reading 2, a depth bound in the compiler itself, is now the
only reading no experiment has contradicted.

**The archive survived both**: `--assert-safe` green after each, 10 of 10 rules,
177,318 payload CRCs. Full scoring in
`vault/research/worldmaps/WORLDMAPS-W9-RUN.md` §RESULTS.

## WORLDMAPS-W11 — the lever works, and the bound is a WATER LINE. 2026-08-21

**OBSERVED (retail client, build 38797; one variable against a control measured
twice on the same copy).** `map_flags = 1` on the area row — bit 0 of the Map
Parameters flags dword, top byte untouched — and the excluded ground came back:

| | control (flags 0) | treatment (flags 1) |
|---|---|---|
| trapezoids | 64 | **99** |
| mesh x | 1248 .. 6144 | **0 .. 6144** |
| coverage | 2,582/4,096 = 63.04% | **3,820/4,096 = 93.26%** |

**WORLDMAPS-W10's static chain is confirmed at the client**: the 40.0 constant
at `0x0094DE30`, the all-three-corners test at `0x0072D3ED`, the gate at
`0x0072D3C6`, and the identification of state+0x10 as the flags dword. And the
rule predicts the boundary TO THE COLUMN — column 12's quad has corners 47 and
43 (both past 40, excluded), column 13's has 43 and 39 (one shallower, kept),
and 13 is exactly where the control mesh started.

**WHAT THE NUMBER IS.** Watching the run, the owner reported: *"i was floating
over the water there instead of standing ankle-deep in it like usual."*
**40.0 is a WATER LINE.** Values increase downward in these maps (the apron at
-13 is dry, the dip descends to +229), so "all three corners >= 40.0" means "this
triangle is more than 40 units under water". The shallows are walkable — which
is why the mesh stopped at the last quad with a corner above the line — and with
bit 0 set the submerged floor is meshed too.

**This vindicates W8's intuition while leaving its refutation intact, and the
distinction is the point.** W8 proved the borrowed environment chunk does not
carry the cut (byte-identical meshes with it deleted). True, and the water
reading was still right about WHAT: the water line is a **compiler constant**,
not map content. The env chunk renders water; `0x0094DE30` decides what water
does to the navmesh. No experiment varying map CONTENT could have found it —
which is also why W9's Zones swap was doomed.

**What it gives the project**: authored maps can now have walkable underwater
terrain — lake beds, sunken ruins, a canyon floor below the waterline — via one
content field. And it retires a silent tax: every authored map built here has
been losing its deep ground to a rule nobody knew existed.

**APPLIED to the deliverable areas, 2026-08-21.** , , 
and  now carry , recovering 43.4%, 34.4%, 34.4% and
**49.3%** of their cells respectively -- every map this project ships had been
losing that ground silently. Two rows deliberately do NOT: , because
gen_plaza(32) tops out 31 units down and the rule needs 40, so the flag is a
no-op there AND it is WORLDMAPS-W2's byte-identity control; and the probe rows
//, which exist to reproduce specific measurements
(including two that crash the client) and would stop documenting them if
changed.  is marked SUPERSEDED --  now carries the same shape.
**Every mesh measurement recorded in this document for those four areas was
taken at flags 0** and each row says so beside its own field; re-running them
now will not reproduce those numbers, by design.

**Scope**: one map, one shape, one build, one launch. What bit 0 does BESIDES
ungating this rule is unmeasured. The 276 cells still outside the mesh are
attributed to slope by their scatter across all 64 columns, not by a separate
measurement. Full scoring in
`vault/research/worldmaps/WORLDMAPS-W11-RUN.md` §RESULTS.

## WORLDMAPS-W12 — the flag holds on all four deliverable areas. 2026-08-21

**OBSERVED (retail client, build 38797; four installs, four launches, `harness
rc 0` and every readback row green on each).** WORLDMAPS-W11 measured bit 0 of
the Map Parameters flags on ONE probe row; the four deliverable areas were then
flagged on the strength of it and had not been near a client since. They have
now:

| area | dims | traps flags 0 -> now | coverage now |
|---|---|---|---|
| sculpt | 64 | 64 -> **99** | 3,820/4,096 = **93.26%** |
| frontier | 64 | 64 -> **99** | 3,820/4,096 = **93.26%** |
| vale | 96 | 88 -> **156** | 8,750/9,216 = **94.94%** |
| expanse | 256 | 60 -> **98** | 65,070/65,536 = **99.29%** |

The flags dword reads `0x00000001` off all four compiled heads with the rect
intact. **Every authored area this project ships now reaches its own map edge.**

**Two results carry no free parameter.** `sculpt` assembles sha256-identical to
W11's treatment arm (checked before the run), so its 99 trapezoids and 3,820
cells are a REPRODUCTION of W11 on a different day — W11 independently
re-confirmed. And `frontier` produced the same 99 trapezoids, the same 10,988 B
path chunk and the same 3,820 cells from a **created chain** (`0x5F0B0`, a file
id ArenaNet never shipped) rather than a displaced retail row: the created-chain
path costs the mesh nothing.

**One registered prediction FAILED, and the failure was in how it was stated.**
Expanse was predicted at 96–99% and measured 99.29%. The underlying model was
wrong by −280 cells (−0.43 pt), comfortably inside the ±3 points it was
registered with; the band was written by CLIPPING the upper edge at 99%, because
98.86 + 3 is not a coverage figure, and the clip made it −2.86/+0.14 rather than
±3. The clip is what failed. Across all four maps the model held to ±3, and
**its sign flips with size** — over-predicting at 64 and 96, under-predicting at
256 — which is the shape the two omissions declared beforehand would produce
(ignoring flood reachability over-predicts; scoring by quad centre while the
client emits cell-SPANNING trapezoids under-predicts, and at 256×256 the client
covered 65,536 cells with 98 trapezoids). That attribution is a READING; nothing
in this run separates the two terms.

**Scope.** What bit 0 does BESIDES ungating the depth rule is still unmeasured.
The server did not path against any of these meshes (`--serve` not passed), so
the recovered ground is IN the mesh and has not been walked. Full scoring in
`vault/research/worldmaps/WORLDMAPS-W12-RUN.md` §RESULTS.

## WORLDMAPS-W13/W14 — one bit is a crash or a map, and bit 0 touches exactly one chunk. 2026-08-21

> **CORRECTED 2026-08-21.** This rung was written up as standing the
> PLAYER's spawn on the recovered ground. It did not: `seed_x` is the
> compiler's FLOOD SEED, and the character arrived at map 143's spawn
> (1536, 1536) in both arms. The mechanism below — crash at flags 0, clean
> compile at flags 1 — is unaffected. Full correction at the end of this
> document.

**OBSERVED (retail client, build 38797; four arms one field apart, six launches,
same client and archive in one session).**

**W13 — the ground.** A seed placed at (528, 528), eight columns inside the
region the water rule excludes, on the same 64×64 shape:

| arm | flags | outcome |
|---|---|---|
| `sculpt_deep0` | 0 | **the client CRASHED compiling it** |
| `sculpt_deep1` | 1 | compiled clean; **the flood seed lands in exactly one trapezoid** |

The crash is `Assertion: (dest == vertices + 1) || (dest[-1].pos !=
dest[-2].pos)` at `PathFlood.cpp(681)` — **the same source file as W10's depth
classifier**. It is a degenerate-vertex guard, and read with FINDINGS 34's flood
(which starts from the seed) it says the flood began where no valid triangle
exists and emitted a degenerate path. **One bit is the difference between a
crash and a walkable spawn.** I registered this arm as failing `readback`'s
spawn assertion; it never got that far, so the prediction is CONFIRMED on its
discriminating claim and WRONG on its predicted failure mode.

**The server read it, for the first time.** A second, unarmed run pre-warmed the
map: `[map] navmesh 0x287D3: 1 planes, 99 trapezoids`, matching what `pathmap`
reads from the same bytes — two independent readers — and the first run in this
arc without `collision is OFF`. Every W12 run had served no mesh at all, which
is structural: `--install` arms the head, so the run that PRODUCES a mesh can
never serve it.

**A same-session flags-0 twin was compiled for the first time** and reproduced
every figure held for this shape (64 trapezoids, 7,660 B, 2,582/4,096 = 63.04%,
column 13). **W12's deltas were not measured against a moving baseline.**

**W14 — the bound.** Two compiled heads, same shape, one bit apart, compared by
a raw slice walk over the wire format:

**Exactly two of twelve chunks differ — Map Parameters (`0x2000000C`, at one
byte, offset +21) and Path (`0x20000008`, 7,660 → 10,988 B).** Everything else
is byte-identical, including **Zones** (42 B), which was the chunk to watch as a
flags-reading branch whose output reaches our artifact. **Terrain is
byte-identical at 28,503 B**, which is the determinism control that licenses
reading the rest: had it moved, the diff would have been void rather than
positive.

**Within the compiled artifact, bit 0 changes the Path chunk and nothing else.**

**Scope, and one piece of it is permanent.** Our compiled heads carry 12 chunks;
retail Kamadan carries 24. We emit **no Sight, Shore, Water, VisData or
Collision chunk in either arm**, so no differential over our artifacts can ever
see those branches — a property of what we author, not of the flag. Runtime
effects that are not persisted are likewise invisible here. Traversal onto the
ground from dry land was not tested. The server cannot see the bit at all
(`map_flags`: zero occurrences under `toolkit/authsrv/`). Full scoring in
`vault/research/worldmaps/WORLDMAPS-W13-RUN.md` §RESULTS.

## WORLDMAPS-W15 — authored population stands on the recovered ground. 2026-08-21

**OBSERVED (retail client + our server, build 38797; two arms one bit apart,
same session, same archive).** WORLDMAPS-W12 put the submerged floor into the
navmesh and W13 put the compiler's flood seed on it. Placing a **body** is a
separate gate with its own code — `authsrv.place_on_mesh` re-checks every spawn
and refuses one it cannot find ground for — and every placement this project had
made until now stood on ground the client would have meshed either way.

| | `sculpt` (flags 1) | `sculpt_flags0` (flags 0) |
|---|---|---|
| bodies placed | **6 of 6** | **3 of 6** |
| refusals | 0 | **3, exactly the deep trio** |
| mesh served | 99 traps (matches archive) | 64 traps (matches archive) |

The three deep bodies placed at **exactly** the coordinates asked for — (56,
6006), (380, 652), (44, 2764) — with no `MOVED` annotation. The same three
coordinates on the flags-0 arm were each refused with *"not on the navmesh and
nothing within 480 units is either"*. Their offline margins to the nearest
flags-0 ground were 1,207 / 1,053 / 1,765 units against a 480-unit search, so no
nudge could have rescued them.

**The within-arm control is what makes this a result rather than an
observation.** Three shallow rows placed in BOTH arms at the same coordinates,
including an identical 96-unit nudge on `farside` — so arm 2 was not broken, and
the placement search behaves the same either side of the flag. That control had
authority to void the finding and none to confirm it.

**This is also the first populated `--serve` in the arc**, and the first time
`serve_run`'s population half — which cross-checks the server's count against
our own content reader — has run against a flags-1 mesh. Arm 2's SERVE_FAILED
was registered as the predicted outcome before the run, since `serve_run` marks
`placed != total` as NOT ALL.

**Scope.** Placement is not pathing: nothing here shows a player can WALK onto
that ground, which is still W13's open residual. No encounter was driven, and
whether a body standing in deep water looks right is a visual verdict for the
owner. Full scoring in
`vault/research/worldmaps/WORLDMAPS-W15-RUN.md` §RESULTS.

## WORLDMAPS-W16 — the recovered ground is WALKED, and without the bit the client stops to the unit. 2026-08-21

**OBSERVED (retail client, build 38797; two arms, identical walk plan, same
session).** W12 put the submerged floor in the mesh, W13 stood the spawn on it,
W15 placed bodies on it. None of those is traversal: a walking character is
stopped by the client's own collision against the mesh it compiled.

| | min x reached | vs the flags-0 wall at 1248 |
|---|---|---|
| `walkedge1` (flags 1) | **0** | crossed by 1,248 u |
| `walkedge0` (flags 0) | **1248** | **stopped exactly at it** |

Both started at (1536, 1536) and got the same plan — `yaw:2246 wait:1 W:14
wait:2`, a 180° about-face then one 14-second leg — so no camera calibration
enters the comparison. The flags-1 character walked **1,536 units to x = 0**,
the far edge of the rect. The flags-0 character walked 288 units and halted at
**x = 1248.0**, which is where our offline decode of the client's own compiled
mesh says the ground ends. **A no-free-parameter prediction landing on the
unit**: the client's collision and our decoder agree about where the world
stops.

**The instrument needed a correction and the first run was not a null.** An
initial four-leg sweep gave min x = 1372, which looks like a failure to cross.
The trace says otherwise: leg 1 went EAST (so `W` is +x from the default
camera), and the best westward leg stopped after ~1,728 units, which is exactly
`6 s x 288 u/s` — the leg's duration, not the ground. Scoring that as a negative
would have been a false null manufactured by the rig, and only reading the trace
rather than the summary caught it.

**Found in passing**: an area's `seed_x`/`seed_y` is not where the player
arrives. The seed drives the compile flood and `readback`'s spawn assertion; the
player is placed at the MAP row's `spawn_x`/`spawn_y` unless `--area` is passed.

**Scope.** Walkability, not immersion — the W10/W11 rule is a navmesh rule, and
nothing here measures swimming, drowning or how any of it looks, which is a
visual verdict for the owner. One start line, one heading, and the walk was
one-way. Full scoring in
`vault/research/worldmaps/WORLDMAPS-W16-RUN.md` §RESULTS.

## WORLDMAPS-W17 — the flags dword's TOP BYTE selects the slope set, 35 -> 45 degrees. 2026-08-21

**OBSERVED (retail client, build 38797; two arms one byte apart, same session,
same archive, scored by FINDINGS 48's own ruler).**

`studies/customarea` FINDINGS 48 measured the slope set in force and closed by
naming what it could not settle: *"whether the mode flag can select the other
set on some map kind"*, with that flag's source recorded as **NOT FOUND** by
both FINDINGS 34 and 48. It is found, and the client obeys it.

| | arm A (`0x00000000`) | arm B (`0x02000000`) |
|---|---|---|
| top byte / what the client saw | `0x00` -> **1** | `0x02` -> **2** |
| trapezoids | 7 | **14** |
| ramp pattern | **`WW...`** | **`WWWW.`** |
| verdict | cut 35 — set 15/35/30 | **cut 45 — set 10/45/40** |

**Arm A reproduces FINDINGS 48 exactly**, two weeks later with no free
parameter, so arm B's difference is the flag. **Arm B moved the walkability
boundary from 35° to 45°**: strips at 36.1–37.6° and 41.5–41.9° flipped to
walkable, and the 46.5–47.8° strip correctly stayed out.

**This confirms the whole static chain at the client** — the parser at
`0x0070D920` copying the dword verbatim to `state+0x10`, the top-byte extraction
at `0x00712681`, seven single-caller hops, and `cmp dword ptr [ebp+8], 2` at
`0x0072CA1C`. It also settles **which slot the classifier tests**: arm B landed
on 45, not 40, so the hard cutoff is `+0x94` as read, not `+0x90`.

**The parser's 0→1 normalisation is what made the run work.** Arm A's file byte
is 0 and the client saw 1. Had the treatment used `0x01000000`, the client would
have seen 1 in both arms and produced a clean null that looked like a
refutation. The boundary is 1-vs-2, not 0-vs-nonzero — found before the run.

**Plateau tracks ramp in both arms**, so FINDINGS 48's connectivity-pruning
result holds under the other threshold set too.

**What it gives the project: authored terrain can be steep to 45° by one content
field** — cliff paths, canyon walls, steep valley sides. Bit 0 and bits 24..31
are disjoint fields of one dword, read once, meeting in the same function, so
the water line and the slope set compose.

**Scope.** Top byte 3+ is unvaried (it crosses the `< 3` test at `0x0070D9DE`).
Nothing here WALKS a character up a 42° ramp — W16 established that meshed and
walkable are different questions. The `+0x90` (30→40) companion reading remains
static rather than measured. Full scoring in
`vault/research/worldmaps/WORLDMAPS-W17-RUN.md` §RESULTS.

## WORLDMAPS-W18 — the recovered ground is WALKED, and the measurement needed fixing. 2026-08-21

**OBSERVED (retail client, build 38797; two arms one byte apart, identical walk
plan, same session).** WORLDMAPS-W17 moved the walkability boundary 35° → 45°
with the flags dword's top byte, and closed on W16's distinction: **meshed and
walkable are different questions.**

The ramp map's spawn (1536, 1536) sits directly under **strip 3**, the
36.1–37.6° ramp that flips between the two threshold sets, so walking north
walks up the strip under test.

| measured within | arm A (cut 35) | arm B (cut 45) | separation |
|---|---|---|---|
| whole map (as registered) | 2,686 | 3,072 | 386 u |
| **strip 3's band, x 1248..1824** | **1,728** | **3,072** | **1,344 u** |

**Arm B climbed the 36.9° ramp to y = 3,072**, the far edge, crossing ramp and
plateau. **Arm A stopped at y = 1,728 — the last apron row, to the unit** —
which is exactly where the mesh ends when strip 3 is excluded.

**The registered prediction was REFUTED as written, and the fault was the
measurement.** I registered "max y over the whole trace, separation ≥ 700"; the
unconstrained answer is 386. Arm A's trace reaches x = 1144, inside **strip 2's**
band — the 32.0° ramp, walkable under *both* sets — so the character drifted out
of the strip under test and climbed one that was never in question. Max-y-anywhere
cannot isolate strip 3 when a walkable ramp adjoins it. The corrected band is not
post-hoc: strip 3 is x 1248..1824 by construction of the generator and appears in
the run note's design table written before the run, and **arm A answers 1,728 for
both the wide band and a tight interior**, so the number does not move with the
window.

**Both characters walked far** — 5,238 u and 5,048 u of traced path against a
1,500 u void guard — so arm A's failure to climb is not a failure to move.

**So both levers in this dword recover ground that is genuinely traversable**,
not merely present in the file: the water line (W16) and the slope set (W18).

**The instrument lesson, third of its kind.** W12 clipped a band against a wall,
W16's first plan ran out of leg, W18's measurement could be satisfied by the
wrong feature. All three were faults in how the result was to be READ, caught
only because the arms shared everything but the variable. The rule: **when a map
has more than one feature that could produce the signal, the measurement must
name WHERE, not just how much.**

**Scope.** Strip 4 (41.5–41.9°) also flips and was not walked — it needs its own
start line, since arm A shows how readily a walk wanders between strips. How a
character looks or animates on a 37° slope is the owner's verdict. Full scoring
in `vault/research/worldmaps/WORLDMAPS-W18-RUN.md` §RESULTS.

## CORRECTION 2026-08-21 — W13 measured the FLOOD SEED, not the player's spawn

**An area's `seed_x`/`seed_y` is the compiler's flood seed. It is NOT where the
character arrives.** The arrival point comes from the MAP row:
`content.map_static_config()` builds `id -> (file_id, (spawn_x, spawn_y), plane,
explorable)` from `rows("map")` only, and `seed_x` has exactly three consumers
in `toolkit/` — `deploy.py:374` (passed to `stripbuild.build` as the flood
seed), `deploy.py:1634` (the readback assert) and `mapscale.py`. None is the
player. `authsrv` has no `--spawn` override.

So `sculpt_deep0` and `sculpt_deep1` moved the **flood seed** to (528, 528);
the character arrived at map 143's spawn, **(1536, 1536)**, in BOTH arms — on
ground walkable either way.

**The mechanism finding is untouched and is still the point of W13**: at flags 0
a flood seed on submerged ground crashes the compiler at `PathFlood.cpp(681)`;
at flags 1 the identical seed compiles clean. One bit, crash versus map.

**What was overstated is the framing.** "The player's own spawn stands on it"
was not measured there. That claim is carried by **W15** — bodies placed at
(56, 6006), (380, 652) and (44, 2764), refused at those same points with the bit
clear — and by **W16**, where a character walked to x = 0. Both measured a body
or a character; W13 measured the seed.

**How it was caught, and it is the fourth of these.** W19's two arms were to
differ only in `seed_x`, which would have spawned the character in the same
place twice and produced a fabricated result — P1 refuted and P2 confirmed from
one non-event. An adversarial design review found it before the run, unlike
W12's clipped band, W16's short leg and W18's ambiguous window, which were all
caught after. `deploy.readback`'s row was reworded from "the spawn" to "the
flood seed" in the same commit, because that wording is what made the error easy
to make.

## WORLDMAPS-W19 — 45 degrees is a BOUNDARY, positive and negative in one arm. 2026-08-21

**OBSERVED (retail client, build 38797; two walks, ONE compiled map, one
threshold set, one spawn).** W17 moved the walkability cut 35° → 45° and W18
walked the ground it recovered — but both tested slopes **below** the new cut,
so neither could distinguish "the boundary moved" from "the classifier stopped
excluding things".

| arm | strip | snapped slopes | max y in band | verdict |
|---|---|---|---|---|
| **S4** | 4 | 41.52–42.51° | **3,064** | climbs to the plateau |
| **S5** | 5 | 46.45–47.84° | **1,728** | stopped at the apron top, to the unit |

**Separation 1,336 u inside a single threshold set.** Both arms served the same
`14 trapezoids` map, so there was no fall-back to the cut-35 blob — which would
have failed P1 and passed P2 exactly as a real "boundary is 40" result would.
Both bands were populated (10 and 8 samples), so S5's refusal is measured rather
than an empty window read as a negative.

**Every prediction confirmed as registered** — the first rung in this arc with
no caveat, and that is because the design was adversarially reviewed BEFORE it
ran rather than diagnosed after.

**The review caught a fatal.** The first draft moved the start line with
`seed_x`, which is the compiler's FLOOD SEED and not the player's spawn: both
arms would have started at (1536, 1536), both scoring bands would have been
empty, and P1-refuted/P2-confirmed would have been fabricated from one
non-event. It also caught that `gen_ramp` blends `dz` per column, so every strip
boundary is a wall (gx 18 = 42–59°, gx 24 = 47–63°, gx 30 = 68–85°) and the
draft's bands each contained one. Corrected bands are the uniform-slope spans,
x ∈ [1824, 2304] and [2400, 2880].

**The corrected design needed no new content at all**: the apron is one flat
slab (x 0..3072, y 0..1728), so the start line moves by WALKING EAST before
turning north — one install, two walks, byte-identical archive state, which
dissolves the "are these the same map" question instead of arguing it.

**Scope.** Where between 42.51° and 46.45° the cut actually sits is not settled;
the strips bracket it without bisecting it, and the static read's 45.0 is
consistent but unconfirmed. Class 2 ground (between 40 and 45 under set B) is now
known walkable and traversable, but whether it differs from class 0 in cost or
behaviour was not measured. Full scoring in
`vault/research/worldmaps/WORLDMAPS-W19-RUN.md` §RESULTS.

## WORLDMAPS-W20 — the cut is (43.78, 45.00], and a SECOND threshold governs whether ground meshes at all. 2026-08-21

**OBSERVED (retail client, build 38797; four compiles, one shape, exact-slope
strips).** Built to bisect the 45° cut W19 bracketed to [42.51, 46.45]. It did
that — and turned up something not predicted.

**The instrument.** `deploy.gen_ramp_fine`: strips whose snapped slopes are
EXACT, worst sample moved **0**. Two properties buy that and both were measured:
each `dz` is a multiple of 4, and each strip is eight columns aligned to the
codec's **4×4 sub-blocks** (`snap_block` projects each sub-block independently,
so a boundary inside one quantises the whole block — the first draft's 6-wide
unaligned strips spread by up to 1.4°, which is what limited W19).

**THE HEADLINE, and it was not predicted.** Three runs at cut 45 differing only
in the shallowest strip:

| strips | trapezoids | result |
|---|---|---|
| 43.78 / 45.00 / 46.17 / 47.29 | 2 | apron only |
| **41.19** / 42.51 / 43.78 / 45.00 | 2 | apron only |
| **18.43** / 42.51 / 43.78 / 45.00 | 11 | **`WWW.`** |

**42.51° and 43.78° mesh only when a much shallower strip is present.** The
classifier emits THREE classes from the array at flood-object`+0x90` — `< array[0]`
→ class 0, `> array[1]` → class 1, between → class 2 — and under set B that array
is {40, 45, …}. Every strip in runs 1 and 2 was ≥41.19°, hence **all class 2 and
no class 0 anywhere**, and nothing beyond the apron meshed. **RECONSTRUCTION:
class-2 ground is meshed only where reachable through class-0 ground; adjacency
to the flat (class-0) apron is evidently not enough.**

**The cut**: 43.78° meshed, 45.00° not → **(43.78, 45.00]**, the tightest bracket
held. The cut-35 control on the same map gives `W...` — only the 18.43° strip,
the rest being class 1 outright.

**It does NOT settle strict vs non-strict**, which is what it was built for. Strip
D is 45.00° in OUR measure (doubles, max of two triangles); the client computes
its own float32 per-triangle value. A slope sitting exactly on the threshold is
decided by that difference rather than by the comparison operator — a design
fault, since a value ON a boundary cannot test the boundary's inclusivity unless
both sides compute it identically.

**THIS REINTERPRETS W17 AND W19.** `gen_ramp`'s first three strips (26.6–37.6°)
are class 0 and its strip 4 (41.5–42.5°) is class 2, so W17's `WWWW.` and W19's
climb of strip 4 both occurred **with class-0 strips beside them**. Their
findings about the top byte and about traversability stand; what does not stand
is the reading — mine — that a 41–42° slope is walkable *on its own*. Run 2 says
it is not.

**Process note, recorded because it cost the run its predictions**: I mutated the
strips twice mid-run after a failed positive control, so P1–P4 do not apply
cleanly to the configuration that produced the result and P5 is stale rather than
refuted. The headline was not predicted at all. Full scoring in
`vault/research/worldmaps/WORLDMAPS-W20-RUN.md` §RESULTS.

## WORLDMAPS-W21 — authored props CAN block, and the footprint is honoured to the unit. 2026-08-21

**OBSERVED (retail client, build 38797; one flat map, one prop, two arms one
field apart).** Every prop this project has ever placed was scenery a character
walks through: `Prop.outline` — the prop's footprint, which
`StrippedProps.encode` has always written — was passed as `()` by `deploy` and
never set by anything.

**MEASURED first, offline**: retail props carry footprints only sparsely.
Kamadan's **516 props share 280 outline points**; the biome donor's **864 share
252**. So outline-free props are the retail majority and ours were not
anomalous — what this project could not do was author the *other* kind.

**It can now.** A prop given a 576×576 footprint:

| | control (no footprint) | treatment (576×576) |
|---|---|---|
| mesh inside the footprint | — | **0 of 108 samples walkable** |
| identical box beside it | — | 108 of 108 walkable |
| character max x | **3072**, the map edge | 2846, having gone *around* |
| trapezoids | 10 | 9 |

Scanning the walk line at 2-unit resolution, **the last walkable x is 2640 and
the hole begins at 2642** — authored half-width 288, observed 286. The footprint
is honoured **1:1 in world units**; the `scale` byte does not scale it.

**The character's own path confirms both authored edges to the unit.** It walked
east, stopped with **x pinned at 2640.0** — 2928 − 288, the west edge — for five
consecutive reports while sliding north, then rounded the corner at
**y = 1776** — 1488 + 288, the north edge — and resumed east. That is collision
and slide against the authored polygon.

**The registered prediction was REFUTED because the statistic was wrong**, not
the finding: I registered "max x ≤ 2700", and `max x` cannot distinguish
*blocked* from *blocked and walked around*. The raw trace contains a far stronger
result than the statistic could see. **Fifth instrument fault of this family in
this arc**, and the first where the better answer was already sitting in the data.

**What it gives the project**: authored maps can have obstacles, via one content
field (`prop_outline`).

**Scope.** Whether the footprint's SHAPE is used or only its bounding box is not
settled — a square was authored and a square-consistent hole appeared, which one
walk into one edge cannot distinguish; a non-convex outline would. Whether the
prop MODEL contributes collision of its own is untested (all props here are
`model=0`, and the control shows it blocking nothing alone). Full scoring in
`vault/research/worldmaps/WORLDMAPS-W21-RUN.md` §RESULTS.

## WORLDMAPS-W22 — the footprint is a POLYGON, not a bounding box. 2026-08-21

**OBSERVED (retail client, build 38797; one compile, scored offline).** W21
proved an authored prop footprint is honoured and honoured 1:1 in world units,
but noted that a **square cannot distinguish a polygon from its bounding box or
its convex hull** — for a square all three are the same set.

`area.notch` is W21's `blocker` with one field changed: the ring becomes the
same 576×576 square with its **north-west quadrant removed**, 7 points, closed,
and **non-convex**, so its convex hull is the full square.

| region | walkable samples |
|---|---|
| **the NOTCH** (world x 2640–2928, y 1488–1776) | **29 / 36 — walkable** |
| solid NE / SW / SE quadrants | **0 / 18, 0 / 36, 0 / 18 — holes** |
| outside, west of the prop | 88 / 88 |

**The client used the polygon.** The notch is walkable while every solid
quadrant is a complete hole, and the notch's hull is the full square — so
neither the bounding box nor the convex hull is what the compiler read.

The notch's 7 non-walkable samples all sit **within 24 units of a notch
boundary** (six 24 u inside the east edge, one 24 u inside the north edge), so
the notch is walkable throughout bar a one-sample margin along the cut.

**With W21, this closes the prop-collision question**: an authored footprint is
honoured to the unit, its shape is the polygon including non-convex shapes, and
a prop with no footprint blocks nothing. **Authored maps can have obstacles of
arbitrary planar shape.**

**Scope.** Self-intersecting or open rings are untested — `Prop.closed` records
that 43 of retail's 37,548 outlined props are not closed, so the client
tolerates them, but what it does with them is unknown. Whether the prop MODEL
contributes collision of its own is untested (all `model=0`). Vertical extent is
not a question a flat map can ask. Full scoring in
`vault/research/worldmaps/WORLDMAPS-W22-RUN.md` §RESULTS.

## WORLDMAPS-W23 — class-2 ground cannot be climbed out of flat ground. 2026-08-21

**OBSERVED (retail client, build 38797; two compiles, one field apart, scored
offline).** W20 concluded as a RECONSTRUCTION that class-2 ground meshes only
where reachable through class-0 ground — but on a map that could not carry the
claim, because its class-2 strips DID touch the flat class-0 apron and still did
not mesh, and it varied the steep lateral seams between strips at the same time.

A **uniform** ramp removes strips, seams and neighbours together.

| arm | slope | class | ramp band |
|---|---|---|---|
| `u18` | 18.43° | 0 | **288 / 288 walkable** |
| `u42` | **42.51°** | **2** | **0 / 288** — the mesh stops at y = 1728, the apron's last row |

Same generator, same bands, same flags, same seed, one field different.
**A uniform 42.51° slope rising out of flat ground is not meshed at all.**
W20's rule holds.

**And the rule is now sharper than W20 could state it.** `u42`'s apron IS
class-0 ground and IS adjacent to the ramp, so the condition is neither
"class-0 exists" nor "class-0 adjacent". The one thing W20's run 3 had — where
class-2 strips DID mesh — that neither failing run had is **class-0 ground that
RISES**, carrying the flood to the heights the class-2 ramps occupy.
**HYPOTHESIS, untested: the flood accepts class-2 ground only at heights it has
already reached through class-0 ground.** Falsifiable by a map whose class-0 and
class-2 ramps are separated so the flood cannot cross between them.

**For an author the rule is simple and unchanged: a steep region needs a gentle
approach that climbs with it.** A flat plaza at the foot of a 42° face buys
nothing — the map compiles without the face, and nothing warns you.

**Recorded because it nearly cost the run**: `u18` reported **2 trapezoids**, and
on the fine-ramp maps 2 trapezoids meant "apron only". I read it that way and
called the control failed. A *uniform* ramp decomposes trivially and those two
trapezoids covered the **entire map**. Sixth instrument fault of this arc's
family, second time a summary number stood in for a region check. W20's runs 1
and 2 are unaffected — they were scored by region, not by count.
