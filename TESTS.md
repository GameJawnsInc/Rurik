# The suite — every test in `toolkit/`, and what each one is really checking

**This file is the suite.** A test in the tree but not named here is a test nobody
runs, and `toolkit/test_srclint.py` §7 enforces that in BOTH directions with a check
that can go red. Add the entry in the same commit as the test.

**To run it, do not read this file** — `python toolkit/run_suite.py` discovers tests
from the **disk**, never from prose, for reasons its own docstring records at length
(an earlier runner harvested the list out of `CLAUDE.md` with a regex and silently ran
63 of 71). This file is why each check exists; the disk is what runs.

Split out of `CLAUDE.md` on 2026-08-14, when the catalog had reached **2,458 of that
file's 2,725 lines — 90%** — and the house rules a cold session actually needs were
buried under it. Nothing here was rewritten in the move; only `CLAUDE.md`'s pointer and
`test_srclint.py`'s target changed.

---

Every one of these, in the order they were written:

  `toolkit/schema/test_codec.py` (codec vs. real captured bytes — and
  since 2026-08-11 the `string16` round trip: **22,524 of 22,524** live GAME_SMSG
  re-encode to ArenaNet's own bytes, where 133 in twelve opcodes did not, because
  the field decoded with `errors="replace"` and GW's encoded names carry code
  units in the UTF-16 surrogate range. The failing set was EXACTLY the set whose
  values carried U+FFFD, and the test asserts that as an invariant so it can fail
  in both directions. Three controls sit under it and each catches a different
  wrong implementation: a value CONSTRUCTED from raw code units must encode to
  exactly them — which is what a decoder that stashes the original bytes on the
  value cannot do, and the only thing that catches it, since such a decoder
  round-trips every message it ever saw and survives the mutation control; a
  mutated neighbouring field must read back mutated with the string intact,
  which catches a message-level byte cache; and an astral character must count
  as TWO code units, which is a second bug the first one was hiding — `len(s)`
  counts Python characters, so a surrogate pair wrote a count two bytes short and
  desynced the NEXT message. The check is on that next message),
  `toolkit/schema/test_catalog.py` (our message catalog vs. the client's own
  format tables — 477/477 GAME_SMSG agree field-for-field on build 38797),
  `toolkit/harness/test_harness.py` (the one-command stack, the launch safety
  gate, the live capture tail, and the crash-dialog capture — which is the ONLY
  machine-readable evidence a client assert leaves: `Gw.log` does not record
  asserts, no dump file is written anywhere findable, and a ConnectionResetError
  in the gamesrv log appears on a clean teardown too. The dialog is faked in the
  test so the extraction is checked without crashing a client. Also `hold_key`,
  the held movement key `--walk` drives, against a fake `user32`: that every
  event carries a NON-ZERO scan code, that the key is released on every exit
  path including an exception mid-hold, that losing the foreground cuts the leg
  short, and that a client without focus gets nothing at all. The scan code is
  the one that earned the section — a synthetic keydown with `bScan=0` is
  accepted by a UI reader and silently dropped by the raw input path the client
  reads movement through, so the first version held W for 65 seconds into a
  live client that ignored every one of them while the harness reported
  `held 8.0s of 8.0s` six times. Only the capture could tell the two apart.
  **And section 9a (2026-08-14) is that same defect in the SIBLING the fix
  missed, which is the more useful half of the story.** `hold_key` was fixed
  and `press_vk` was written correct; `press_key` — the one EVERY `key:` action
  goes through, including skill slots 1..8 — kept `keybd_event(vk, 0, 0, 0)`
  and was in **no test at all**, so the trap this section exists for stayed live
  in a second function for three days under a check that could never see it. A
  fix applied to two of three copies of one send is not a fix, and a symbol
  appearing in a test file is not a check. It surfaced only because a `key:K`
  action printed `sent` while the Skills panel never opened and the owner
  pressed K by hand; the blast radius is every scripted skill press since
  2026-08-11, i.e. any run that concluded something from `key:1` was reading a
  DROPPED INPUT rather than a client behaviour. `press_key` now delegates to
  `press_vk` instead of keeping a third copy, a key with no scan code on this
  layout sends nothing rather than falling back to zero (that fallback is the
  original defect wearing a guard), and the fix was verified against a real
  client rather than the fake `user32`: same action script and timing, the
  0.6 s-after frame went from no panel to the panel open.
  **And since 2026-08-12 the harness spawns NO HOSTILE unless `--enemy` is
  passed**, because the standing enemy had wrecked two unrelated tests -- most
  recently FINDINGS 40's movement session, where it killed the character 10 s in
  and `hold_key` cut the last two walk legs to 1.50 s of 5 and 4. It is not
  hard-coded to attack: the chase gate is a real distance test against
  `AGGRO_RANGE = 1200`, but `content/world.toml` puts it **300 units from the
  player's arrival point** with `enabled = true`, so it engages in every map on
  every session, which is the same thing from the outside. `authsrv.py`
  standalone and `world.toml` are unchanged. The three checks that earn the
  section are the warning ones: defaulting the enemy off silently turns every
  combat `--probe` into a run against an empty world, so a probe with no hostile
  must WARN, and must NOT warn with `--enemy` -- a warning that fires either way
  is noise. A contradiction (`--enemy` plus an explicit `--no-enemy`) is refused
  rather than resolved. **And since 2026-08-12 the crash dialog is captured on
  EVERY run**, not just `--keep-open` ones: `capture_error_dialog` was reachable
  only from `hold_open()`, so a plain `--hold N` run captured nothing and rung
  E10a's client asserts survived only because the owner read them off the screen.
  The extraction was never broken -- the assert text sits in a hidden `Edit`
  control the reader already finds, and nothing may CLICK, because the control
  beside it is `&Send report to ArenaNet`. It was a missing call site. The test
  asserts it on the SYNTAX TREE, because "in the finally" and "before
  `close_client`, which destroys the dialog" are both invisible to a grep, with a
  control that the ordering check fails on a reversed finally.
  **And since 2026-08-14, WHICH CLIENT a run launches — by build and by name,
  never by mtime.** `newest_run_exe` was
  `max(glob("vault/run/*/Gw.exe"), key=os.path.getmtime)`. Build 38833 shipped,
  was snapshotted and assembled that afternoon, became "newest", and the harness
  silently changed which client it launches — to a run directory whose `Gw.dat`
  never had the maps 146/148 replacement installed, while the 38797 directory
  still carries it. Nothing failed at the exe: an update turned into a wrong
  answer somewhere downstream instead of an error at the launch. **This is the
  same defect for the third time** — `sorted(exes)[-1]` picked the wrong client
  the day both DH configurations first existed, `pinned.PINNED` was `BUILDS[-1]`
  until the same week, and this was the copy nobody had converted. **Filtering by
  build alone did NOT fix it, which is the half worth reading:** with 38833
  excluded the newest 38797 copy is `reskin-roster`, an experiment copy, still
  beating the canonical directory, because the old exclusion covered exactly one
  spelling of "experiment" (`-probe`) and three exist on disk. So the selector
  asks for the build's own vault STAMP — the name `make_run_dir.py` actually
  assigns — and the build is MEASURED from each candidate's own `mov eax,
  <build>; ret` getter via `buildid.read`, never inferred from the directory
  name, the same rule the vault's DH split lives by. It also works where
  `identify()` cannot: that calls `reskin-roster` "unknown" for want of a
  recorded hash, and its exe says 38797 plainly. `buildid.read` is stubbed for
  the ten constructed cases and run for real against the vault at the end, and
  a positive control asks for a build that IS present so the refusals cannot be
  satisfied by a function that refuses everything. An unreadable candidate is
  skipped and NAMED, because "we could not look" must never narrow the field the
  way "wrong build" does. The floor moved 99 → 108 against a measured 110, two
  below for the two checks that can legitimately skip; this test cannot run
  vault-less at all — `pinned.find()` refuses first — so unlike `test_origin.py`
  there is no empty-vault figure to measure against.
  **And since 2026-08-17, `--hold N` without `--keep-open` HOLDS — it used to be
  silently inert.** `run_client` gates the hold on `a.keep_open` alone, so a
  plain `--hold 60` tore the session down at the verdict, and a healthy client's
  orderly exit — game 0x0008, auth 0x0009, status Offline, then the RST — reads
  exactly like a client-side death: fourteen launches were misdiagnosed that way
  on 2026-08-16 (`studies/isle/FINDINGS.md` "Rung 4"). `--hold` has no meaning
  other than bounding the hold, so `hold_implies_keep_open` implies the hold
  rather than refusing the combination — the resolution the tape chain already
  made for the same reason. The checks pin the implication in all three
  directions (hold alone, neither, keep-open alone) and pin the CALL SITE on the
  syntax tree, because the crash-dialog section above was also a correct
  function that `main()` never called. The floor moved 108 → 136 against a
  measured 138: it had drifted 26 checks stale through five commits, which is
  the ledger's own defect class, caught by its own rule of measuring from a
  green run),
  `toolkit/portal/test_webgate.py`,
  `toolkit/mapdata/test_archive.py` (the archive reader, and since 2026-08-14
  section 1c: that `archive.py` and `datcheck.py` share ONE row convention --
  ArenaNet's raw MFT index -- measured over the whole table in both directions. It
  exists because the OPPOSITE was written down and labelled CORROBORATED:
  `studies/crossbuild/FINDINGS.md` section 4b.1 read `entries[71495]` as a row number,
  concluded the two tools number rows differently, and left the standing instruction
  "never compare a row number printed by one tool against one printed by another".
  Every fact it cited is true and the inference is false -- `entries` is POSITIONAL and
  skips the descriptor, so `entries[k]` IS row k+1 in both tools' numbering, and the
  count that differs is `len(entries)` against `row_count`. The 0-mismatch headline is
  the WEAK half and the file says so twice over: the same sweep runs a second time
  through `datcheck.row_bytes` ITSELF, because the first version compared against a
  struct walker written in the test and a datcheck that changed convention printed
  "0 mismatches over 177,341 rows" and PASSED; and the off-by-one reading must agree on
  exactly 11 rows, all of them the all-zero reserved spares at 4..14, checked both by
  count and by contents. The floor is the other lesson: 26 against a green run of 29 let
  two reviews delete exactly the three checks the section calls load-bearing and still
  print ALL CHECKS PASSED, so it is 32 -- the copy-independent green, MEASURED on five
  archives -- with section 4 raising it to 34 when it runs, because a fixed 32 would hand
  `dat_study` two checks of slack. Both shapes have ZERO headroom. **`magic()` is pinned
  DIFFERENTIALLY (2026-08-15)**: it returns an entry's first four bytes by asking the
  huffman decoder to stop early rather than decoding the whole entry, which is 80x
  cheaper and is how `test_modelexport` classifies 1,795 texture references — so every
  sampled entry is decoded BOTH ways and required equal, strided at 997 so it does not
  sample the same rows as the sweep that uses it (97). A shortcut that is merely usually
  right would move a corpus verdict rather than raise. ~30 s),
  `toolkit/mapdata/test_datcrc.py` (the archive's checksum and allocator rules),
  `toolkit/mapdata/test_datwrite.py` (the only tool that opens the archive `r+b`,
  against a small archive the test builds: that `--verify --replace` actually
  mutates rather than verifying and returning, that a shrinking replace journals
  its whole block reservation and zeroes the freed tail, that revert restores
  byte-for-byte even after something else took the freed blocks, and that the
  reservation refusal holds from both sides. Four defects, none of which could
  fail a checksum -- the archive verified perfectly through all of them.
  **Section 7 (2026-08-14) is `--restore`, the IN-PLACE GROW `datmove.plan_move`
  names and refuses** -- its own docstring ends *"write the in-place grow as its
  own verb with its own test"*, and this is that verb. It puts a row back from a
  DONOR ARCHIVE rather than from a journal, which is the whole design: `--revert`
  expires the moment a client runs (the MFT moves, FINDINGS 4c) **and a journal is
  a file somebody has to still have** -- 127 icon rows were left armed in
  `vault/run/reskin-roster/` on the recorded understanding that their originals
  were "recoverable from the journals' `before` fields", and NO SUCH JOURNAL
  EXISTS anywhere in the vault. A pristine copy cannot go missing that way, and
  two of them agree byte-for-byte. Three things `--replace` cannot do and each is
  a check: it writes **compression 0** and there is no compressor here, so an
  ArenaNet row comes back flattened; it computes the reservation from the row's
  CURRENT size, so a shrunk row can never grow back (2,068 B reserves 2,560 when
  the original needs 7,680) even though the blocks were never handed to anyone;
  and `--overwrite` is same-length only. The donor's WHOLE RESERVATION is copied,
  tail included, because a zero-filled tail verifies and still differs from every
  pristine copy. **Identity is by FILE ID, never by row** -- a row index is a fact
  about the copy, so a donor from another build can hold a valid, wrong file at
  row N and every checksum agrees afterwards; the refusal names both ids, and when
  either row is not addressable it SAYS the check could not run rather than
  implying it passed. **The donor is deliberately NOT guarded** -- `guard()`
  protects what is written, and `vault/dat_study` (refused as a target) is exactly
  what you want as a source, asserted behaviourally in both directions AND on the
  syntax tree, with `Writer.__init__` as the control so "not guarded" is a decision
  rather than an omission. Three sabotages are BUILT AND RUN by rebinding one
  module global each: `claimants()` stubbed to `[]` lets a restore into stolen
  blocks through, `check_identity()` stubbed lets the wrong file through, and a
  donor whose compression is flattened leaves the row at 0 **while the payload
  stays byte-identical** -- which is why the compression field is checked
  separately, since the stored bytes cannot tell those two apart. **Section 8
  (2026-08-16) is `--relink-plain`, the DnArchive re-link minus the download** --
  a copy caught mid-replacement (file-id table holding `id | 0x80000000`,
  studies/maprows/FINDINGS.md §8) has its plain id re-bound to the row the
  rename names, in place, one dword. The fixture's rename is installed longhand
  so the pristine fixture IS the correct post-relink state, which makes the
  strongest check one line: the relinked archive must be BYTE-IDENTICAL to the
  pre-rename file -- table dword, entry-2 crc and MFT self-crc in a single
  comparison. Refusals each get a check: plain already binds, neither spelling
  present, the bit-31 spelling as the argument, and a target row failing its
  own crc (a relink must not make a corrupt row addressable); plan-only without
  `--confirm` writes nothing, and `--revert` restores the renamed state
  exactly. No vault, no client. 78 checks against a floor of 78, was 66),
  `toolkit/mapdata/test_datcheck.py` (the pre-flight and the detector, against a
  5.5 KB archive the test BUILDS -- never a real one, and no vault: every one of
  the ten open-time rules the client itself applies is broken on purpose and must
  go red ALONE. **One of the ten was STRICTER THAN THE CLIENT and was corrected
  2026-08-13**: "no row >= 16 with USED clear" refused ArenaNet's own shipped
  archive -- the owner's `C:\gw\Gw.dat`, opened by the retail client every day,
  carries row 35301 that way and pre-flight answered REFUSE, 9 of 10, while
  `vault/dat_study/Gw.dat` has none and passed. A USED-clear row is a fault only
  when something still POINTS at it; unreferenced, it is a SPARE, which is the
  mechanism `datplan` already records the client using when it claimed 35301.
  The pair that pins it is the same row in the same state differing only in the
  reference, so a regression to reading the flag alone moves exactly one of them, because a gate that reddens at everything is as useless as one
  that reddens at nothing. The isolation half is what earns the run: the fixture
  was relaid twice to make it possible, and it caught the first sabotage of the
  reserved-row rule tripping two unrelated items. It also pins the four shapes of
  FINDINGS 18.5's Tier 1 table -- relocation, recycle, delete, sibling relink --
  plus a fifth, UNCLASSIFIED, because a shape the table does not name must be
  reported and not dropped; that the MFT is located from a header read in the
  same call, since the table MOVES and a reader seeking to a remembered offset
  diffs the wrong bytes against themselves and looks green; and `archive.py`'s
  `RURIK_DAT` override, checked by opening `Archive()` with NO path -- reading
  the constant would pass against a module that never uses it. The lever exists
  because a running client holds an exclusive lock on its own archive, so the
  server and the client can never share one file. Last, the three exit codes are
  held apart through the CLI: `--diff` exits 1 to mean the archive CHANGED, which
  is a result, so an archive too broken to have findings must exit 2 -- it exited
  1 from an uncaught traceback, and a reader of the code would have reported the
  crash as "the row moved".
  **And since 2026-08-14 section 3b pins the OUTPUT, which is the half that prevents
  the mistake and had no checks at all.** `row_identity` was pinned and `format_diff`
  -- the only thing an operator ever reads -- was referenced by no test in the tree, so
  a sabotage reverting it and the `--preflight` banner to their exact pre-fix bare form
  left this file 75/75 and `test_archive` 29/29, both exit 0: the whole human-facing fix
  could be deleted green. EVERY `row N` line in the output must now carry its file id
  and role, asserted over all of them rather than over the one row the fixture changed,
  because the pre-fix `   row 18      relocated` contains the substring `row 18` and
  satisfied the obvious predicate. Section 7 adds the `--preflight` banner through the
  REAL CLI, since that is a separate `print` in `_main` no function-level check can see
  and the revert sabotage's six reds did not include it. It also closes a trap the fix
  itself introduced: `diff(before, path=X, after=<snapshot of Y>)` took its rows from Y
  and its identity from X and reported `identified: True` -- MEASURED, 308 of 315
  changed rows naming a file the after-image does not hold -- and the gate is the MFT
  BYTE FOR BYTE rather than a path compare, because a stale snapshot of the same path is
  the same defect wearing the right name. Floor 75 -> 84),
  `toolkit/mapdata/test_atex.py` (the ATEX texture container, and since
  2026-08-14 rung T1's ATTX capability. **`parse` STILL REFUSES an ATTX row and
  that is the design**: refusing a container whose walk does not close is what
  catches damage, so the trailer is split by a named function and all six
  pre-existing ATTX checks survive unchanged. The only thing that matters about
  `split_trailer` is WHERE THE BOUNDARY COMES FROM -- it is WALKED, and the two
  obvious rivals are built as LIVE functions and run on the same bytes:
  `find(b"ffna")` lands inside level 0's payload, `rfind` inside the trailer.
  Both are given a container BUILT to separate them, because the corpus cannot:
  the sequence occurs **exactly once on 1,648 of 1,648** rows, at the true
  boundary, so `rfind` -- what the scratch probe that scoped the arc used -- is
  right on every row that exists today. **ArenaNet declares the boundary
  herself** and that is the strongest check here: the last 12 bytes are
  `{u32 head length, u32 0, b"XTTA"}` and the word equals the walk on 1,648 of
  1,648, with the total length and head-12 as controls at 0 and 0 -- so the walk
  can be REFUTED by her number instead of only agreeing with itself, and a
  footer that disagrees is refused rather than resolved. The tag spelling is
  itself a correction: the first measurement read `XETA` and a skeptic
  re-measuring found `XTTA` on 1,648 of 1,648 and `XETA` on 0, with the client's
  own writer at VA 0x007582A0 agreeing. The trailer length is a CENSUS, never a
  locator -- a constant nothing re-derives is a landmine -- and the LIMIT of the
  truncation refusal is asserted rather than left to be found: dropping a WHOLE
  record is invisible to any walk-based rule, which first appeared as a bug in
  the check above it (`[:-16]` removed exactly the final 16-byte record) and was
  pinned rather than tuned away. Six one-edit saboteurs were BUILT AND RUN and
  all six redden (5, 4, 7, 1, 2, 8); the `1` is the truncation refusal, the only
  check standing between this module and reporting a truncated container as a
  body that closes plus a garbage trailer. Floor 68, was 50; 45 without a vault.
  ~36 s), and first the write
  guard `--make` never had: `atex.py` was the only binary writer in
  `toolkit/mapdata/` reaching `open(path, "wb")` straight off argv with no refusal
  of any kind, so `--make C:\gw\Gw.dat` would have truncated the owner's 4.2 GB
  archive. Three refusals -- `C:\gw`, `vault/dat_study`, EVERY checkout of this
  repo -- each with a POSITIVE CONTROL that an ordinary scratch path is still
  allowed, because a guard that refuses everything protects nothing and the tool
  then never runs. **The check that would have caught the original defect is the
  syntax-tree one, not the refusals**: a guard can exist, be documented and be
  greppable while never being CALLED, so section 3 asks the AST whether every
  write-mode `open()` takes a `resolve_out`'d path, and BUILDS two saboteurs out of
  one-line edits to the live source -- the pre-fix file restored verbatim from git
  (4 FAILs, naming `open(a.make, "wb")` by line) and the subtler one where the guard
  IS called and its result discarded (2 FAILs, with section 2's eight refusal checks
  all still GREEN, which is the whole argument for the section). A third sabotage, a
  `resolve_out` that refuses everything, reddens exactly the three positive controls
  -- and it found a real defect here, since `Refused` is a SystemExit and a bare call
  in a control is NOT caught by `except Exception`; it killed the run and printed no
  banner, the same trap `vaultpath.require_dir` set for `test_stripbuild.py`.
  `atex.parse` had no test at all and sections 4-5 are its first. The load-bearing
  claim is deliberately not "it parsed": `parse` RETURNS a non-closing container
  rather than refusing one, so the assertion is that the record walk closes to the
  EXACT final byte, checked by a second walker written here out of `int.from_bytes`,
  with the same walk started at 11, 13 and 20 as controls -- **400 of 400 close at 12
  and 0 of 400 at any of the three**, and 20 is the header size `atex.py`'s own
  docstring records as REFUTED, so it is ArenaNet's bytes killing a rival rather than
  our decoder agreeing with itself. **The ATTX asymmetry is the finding**: `parse`
  raises on 106 of 106 ATTX rows and 0 of the 400 ATEX beside them, and the cause is
  NOT the magic -- a relabelled synthetic ATEX parses and closes. An ATTX row is an
  ATEX container with a `ffna` type-7 trailer of **exactly 21,923 bytes on 106 of
  106**, whose CONTENTS are 106 distinct sha256s -- a fixed-size per-texture payload,
  not one shared blob, asserted both ways because the loose reading would have been
  filed as a shared constant -- and cutting the trailer off leaves a container that
  closes exactly, 106 of 106. Nothing here teaches `parse` about ATTX; the day
  someone does, this file goes red and names what changed. Rows are found by a
  partial decompression (`gwdat.decompress(head, out_size=16)`, ~0.5 ms a row against
  ~30 ms), which is what makes the strided sweep affordable. Sections 0-3 need no
  vault and score 33 against a floor of 50. ~26 s; `--all` peeks all 177,341 rows and
  is ESTIMATED, not measured, at ~30 minutes),
  `toolkit/mapdata/test_png.py` (the stdlib PNG codec rung M5's texture
  export writes through -- `zlib` and `struct` and nothing else, because
  `toolkit/` takes no third-party dependency and a test needing PIL to check
  it would defeat the module's only reason to exist. NO vault, no archive, no
  client, no PIL: every image is built in the file out of `bytes`. The round
  trip is deliberately the WEAK half -- two functions that agree prove they
  are inverses and nothing about whether either is PNG -- so section 2 reads
  the emitted bytes with a walker written HERE out of `struct` and `zlib`,
  recomputing every CRC, and section 3 feeds the reader images the WRITER
  CANNOT PRODUCE: the writer only ever emits filter 0, the reader claims all
  five, so a PNG is hand-built for each and one more mixing a different
  filter per row (which is what catches a stale `prev` scanline). Six
  one-edit sabotages were BUILT AND RUN and all six redden -- 8, 4, 2, 1, 2
  and 2 -- and the counts are MEASURED, an earlier draft having carried
  guessed ones of which four were wrong. Two rows earn their place: the
  Paeth predictor is invisible to every round trip here (the writer never
  emits filter 4) so only the hand-built images reach it, and **a reader
  that trusts the stored CRC reddens exactly ONE check**, section 4's
  tamper. The width/height swap reddening only 2 is reported rather than
  tuned, and the reason is stated -- a transposed IHDR gives the reader a
  wrong stride so it REFUSES, and the section aborts into one named failure,
  which is `main()`'s guard working rather than thin coverage. Refusals are
  asserted as `BadPNG` and not as "raises", because a truncated file left as
  `struct.error` in the first version and the difference to a caller is a
  refusal versus a crash in the exporter. 45 checks, ~1 s),
  `toolkit/mapdata/test_atexlevel.py` (the ATEX LEVEL CODEC, solved
  2026-08-14 -- kept apart from `test_atex.py`, which owns the container. A
  level's `code` was never a compression method: it is a 5-BIT MASK OF
  OPTIONAL DECODE PASSES over the block grid, which is why the client's
  validator gates it with `test [eax+4], 0xffffffe0`. Each set bit
  run-length-codes WHICH BLOCKS are one flat colour or alpha; everything
  unclaimed is copied verbatim from the payload tail into three planes, and
  `code == 0` is that copy with no pass at all. **The headline is explicitly
  the weak half**: `decode_level` allocates `blocks * stride` and returns
  exactly that, so "19,175 levels produced the right number of bytes" is TRUE
  BY CONSTRUCTION and an all-zero decoder passes it. The load-bearing check is
  a CODED level scored against its RAW neighbour -- a `code == 0` level needs
  no pass logic, so it is independent ground truth, and mip k+1 is a
  downsample of k: colour median 3.27 against a NULL of 12.47, alpha 2.45
  against 38.63. **The oracle had to be made FORMAT-AWARE and that cost a
  measurement**: scoring every 8-byte format as DXT1 colour put DXTA at 59.19
  against a null of 59.88 -- indistinguishable from noise, reading as "broken
  for 349 of 1,533 containers" -- when the truth is that **DXTA has NO COLOUR
  HALF** and the oracle was reading alpha as colour; scored on its own channel
  it is median 2.36, 472/474 under 8. The decoder was right and the
  MEASUREMENT was wrong, so section 2 pins `has_colour` per format. Sections
  0-4 need no vault and BUILD their own coded containers, hand-encoding runs
  through the client's prefix table. Nine one-edit sabotages were built and
  run; seven redden (12, 7, 6, 5, 4, 3, 3) and **the two that did NOT are why
  the file grew**: "skipped blocks spend run" was invisible because the alpha
  passes run first with the colour bitmap empty (code 9 occurs 4 times in the
  corpus), so section 3(f) builds a two-pass level by hand; and "naive
  nearest-565" was invisible under a one-quantum tolerance, so the bound is
  now 4 -- the client's interpolated index reaches worst-4 where naive is
  worst-7 -- with naive REPRODUCED as a live function. One sabotage still
  reddens nothing and it is NOT a gap: bit 0's gate is "has colour and not
  alpha", so its marking of the alpha bitmap can never be read back, and
  section 2 asserts the gate instead. `--rows` exists so the matrix is
  affordable to re-run. 63 checks with the vault, 48 with neither it nor a
  client image, against a floor of 63),
  `toolkit/mapdata/test_dxt1.py` (the DXT1 codec, which shipped in the texture
  arc with an ENCODER and NO test file at all -- this is the first either
  direction has had, added with rung M5's `decode`/`unpack`/`decode_block`.
  The round trip is an unusually weak half here: DXT1 is LOSSY so the claim
  can only be a bound, and the two directions SHARE `from565` and the palette
  arithmetic, so an error in the shared part cancels exactly and the round
  trip cannot see it. So section 2 recomputes the palette FROM THE SPEC in
  the test -- 565 unpacking with its low-bit replication, the 2/3 and 1/3
  interpolants -- and requires `decode_block` to agree on seven endpoint
  pairs covering BOTH palette forms. **Section 3 is the arm the encoder
  cannot reach**: `encode_block` always forces `c0 > c1` (asserted, three
  ways, so the premise is not assumed), which makes the punch-through palette
  -- one midpoint, index 3 fully TRANSPARENT -- unreachable from any round
  trip, and a decoder missing it renders every cut-out texture (foliage,
  fences, grates) as solid black. Section 4's bounds are DERIVED rather than
  tuned: a flat image must land within one 5-bit quantum (7), and an earlier
  draft asserting 4 went red at 6 with the codec correct and the TEST's
  arithmetic wrong. The planar/interleaved pair is pinned as two live answers
  -- same length, different bytes, cross-decode required to differ -- because
  no size check separates them and the texture arc had to settle it on
  screen. Section 7 reads REAL retail levels and asserts only what the
  archive can refute, and it carries the finding that bounds the whole rung:
  **only 25 of 1,533 ATEX containers have a RAW level 0**, so this decoder
  alone reaches 1.6% of the corpus and the other 98.4% sit behind ATEX level
  compression codes nothing here decodes yet.
  **Section 6 (2026-08-14) is not a codec at all** -- it is `pattern_icon`,
  the picture the arc exists to put on a skillbar, which shipped with
  `safe = min(w,h)/2 - 16` and therefore raised ZeroDivisionError at exactly
  32x32 and drew nonsense below ~40. The 16 was never a pixel count: the
  client stretches the whole texture linearly onto a fixed quad (FINDINGS 9,
  two landmarks in a 64x64 ruler agreeing at 0.955 and 0.958 px per texel), so
  the chrome eats a constant FRACTION, 12.5%. `safe` is now `min(w,h) * 0.375`
  and MIN_ICON = 12 is DERIVED, being where the sun disc stops spanning one
  DXT1 4x4 block. The retired rule is reproduced IN THE TEST as a live
  function, so "128x128 is byte-identical" and "64x64 is not" are two live
  answers rather than arithmetic the test asks the module to confirm about
  itself, and **the load-bearing check is the one the old rule cannot pass at
  any tolerance**: a proportional picture box-filtered 2:1 IS the picture drawn
  at half size -- 2.04/255 against the old rule's 17.74, which is FINDINGS 9's
  arm Q measured offline. Seven one-edit sabotages were BUILT AND RUN and all
  seven redden (9, 4, 12, 10, 4, 5 and 1 check); the last is `min()` swapped
  for `max()` in the refusal, caught by the 64x8 line ALONE, and the zeros
  sabotage is the one that earns the feature checks -- a `pattern_icon`
  returning a field of zeros keeps every "NxN is still drawn" length check
  GREEN. **Two of the seven found defects in the TEST**, and they are this
  file's real lesson: MIN_ICON -> 100000 originally HUNG past a 600 s timeout
  printing no verdict, because the positive controls drew at `dxt1.MIN_ICON`
  and the sabotage asked for a 100000x100000 image -- `test_agentlife`'s
  twelve-of-fourteen in a new shape, a check whose WORKLOAD is computed from
  the symbol under test -- so every size is a literal now; and the reverted
  `safe` killed section 6b outright at its sixth check, so each per-size draw
  is guarded and a crash is a named failure. Sections 1-6 need no vault and
  score 52; 55 by default, 56 under `--all`, and the floor is 55, so a
  vault-less run goes red -- as it always did, against an earlier comment
  claiming a bare machine "still clears the bar"),
  `toolkit/mapdata/test_emblem.py` (the authored profession glyph -- the emblem
  spliced into ArenaNet's own 32-cell sheet at frames 14/15. Most of what makes
  art right is untestable; what IS testable is the set of MEASURED numbers the
  module claims about the sheet, and those rot silently because a wrong one
  yields an emblem that looks fine alone and reads wrong in the row. So the
  lit/dim ratio and the alpha disc are RE-MEASURED from the archive rather than
  compared against copied constants -- ours is required to fall inside the
  sheet's own 0.687-0.788 band, and all 32 cells are required to share one alpha
  profile. The section that earns the file is the BGRA byte order: `cell()`
  returns B,G,R,A because that is what the DDS masks say, and an RGBA writer
  produces a plausible image with red and blue swapped -- our violet bolt would
  render orange with the file size, the alpha and the luma all unchanged, so
  nothing else here would catch it. Floor 11, MEASURED; 17 with a vault -- the
  first version guessed 12/18 and went red on a vault-less run, the same mistake
  test_glyphs.py made hours earlier in the same session. ~2 s),
  `toolkit/mapdata/test_iconset.py` (the 132-row icon ARMER, which is an
  orchestrator over five tested modules -- so this checks only the composition,
  and every section is a way it can destroy 4 GB or arm the wrong rows. Two
  write guards, each with a POSITIVE control, because a guard that refuses
  everything protects nothing: `C:\gw`, and `vault/dat_study`, which `datwrite`
  does NOT refuse -- that refusal exists only here. The row indexing is asked of
  the SYNTAX TREE: `file_id_table` returns one-based ROW NUMBERS while
  `Archive.entries` is POSITIONAL, so `entries[row]` reads the row BEFORE the
  one named, and on 2026-08-14 that put two authored icons into the wrong rows
  with no checksum, no verify and no client able to tell -- it was found only
  because `datwrite` refused a third arm as a relocation and quoted a
  reservation that did not match the row it named. A grep cannot separate
  `a.row(r)` from `a.entries[r]`, so the check counts Subscripts on an
  `entries` attribute and a sabotage must flip it. Section 3 pins that the
  WHOLE plan is checked before the Writer opens, on the AST, because otherwise
  the reservation refusal lands on row 87 of 132 with 86 already written.
  Sections 1-3 need no vault and score 16 against a floor of 16; 20 with one),
  `toolkit/mapdata/test_glyphs.py` (the 132 procedural skill icons a custom
  profession needs -- and mostly, the ARITHMETIC THAT INDEXES THEM, because
  "132 icons came out and they are all different" stayed green through every
  defect this module actually had. All three were index rules that fail
  silently and leave a set that looks fine: polarity split by ground-index
  RANGE gave a motif's six icons six CONSECUTIVE indices and therefore ONE
  polarity block, so the rule meant to separate same-motif pairs never fired
  for them (minimum confusability 10.65, worse than all four vocabularies the
  module was synthesised from); the palette ORDER decides which palettes can
  share a polarity and the first ordering put blue and grey together, the
  worst pair in the set; and without an accent axis a motif's three
  same-polarity siblings differed only in COLOUR (greyscale minimum 6.04 ->
  13.48 once added). So each invariant is asserted directly with the BROKEN
  version reproduced inline as a live function beside it -- and that control
  is where the file's own over-claim showed up: "the pre-fix rule balances
  NONE of them" is false, it balances 4 of 22 by coincidence, and the check
  now asserts a minority against the fix's 22 of 22. Section 5 can fail in
  both directions: the set's minimum pairwise distance must clear a floor AND
  a degenerate set -- one picture hue-rotated 132 times -- must fall under it,
  which it does at 0.02 against 9.92. The safe-area metric had to be rebuilt
  too: the first version took a median of the RED channel and compared all
  three against it, then tested it against a threshold copied from a
  different tool's differently-defined number, and went red at 0.446 on a
  healthy set. Floor 32, MEASURED -- the first version guessed 41 and reported
  "9 did not execute" on a run where nothing was skipped. No vault, no
  archive, no client; ~40 s),
  `toolkit/mapdata/test_textwrite.py` (the FIRST COMMITTED writer of authored
  strings into the archive -- `textrec.encode_file` had existed since the text
  arc with exactly one caller, its own test, using two strings, so every string
  this project has put on a retail screen was written by an ad-hoc script that
  was never committed, which is why `RESKIN.md` can quote the words but not the
  arithmetic. **The claim that earns the file is that `merge` keeps untouched
  records VERBATIM** -- payload, base and bits straight out of the archive, never
  decode-then-re-encode -- because 4 of the 12 records already on screen are
  written down nowhere and re-deriving them from text is how you lose them
  silently. That check is worthless without its control, and the control is the
  point: our records are ALL plain (base 0, bits 0x10, `encode_record`'s own
  defaults), so a merge that drops base and bits is a perfect identity on
  everything this project has ever written. So section 1 builds a fixture with
  146 NON-DEFAULT records, runs both versions, and requires them to differ --
  reported as the first differing OFFSET, because the two are the same LENGTH
  (base and bits live in the header, so dropping them corrupts in place) and a
  length comparison would read as agreement. The identity-tier refusal is
  symmetric: records 0-11 are the profession name, abbreviation and five
  attribute names already on screen, so writing them is refused without
  `--allow-identity` and PERMITTED with it, since a guard that only refuses makes
  the tool unusable. The row is RESOLVED through the client's own text pointer
  table (`textrec.TextIndex.archive_id`) and never remembered -- `RESKIN.md` says
  row 8295 and that is true of one copy, a file id being archive STATE. The size
  model is verified against the artifact rather than quoted: `1024*6 + 2 +
  2*chars` lands on 7,134 B exactly, and the planned write is 12,236 = 7,134 +
  5,102 with no per-record cost, because all 1,024 six-byte headers are already
  paid whether a record is used or not. Plan-before-write is asked of the SYNTAX
  TREE (`plan()` constructs no Writer and calls no move/replace; `main()`
  completes the plan before the first write call), because otherwise a refusal
  lands after some of the file is written. Sections 0-4 build their own 1,024-record
  files out of `struct` and need no vault, no archive and no client, scoring 31
  against a floor of 31; 43 with a vault, two of them being the cross-module
  JOIN -- every skill's recipe string id resolving to its own generated name,
  188 of 188, read back through reskin's own recipe loader rather than compared
  in memory, with a one-id shift collapsing it to 0 of 188. ~2 s),
  `toolkit/mapdata/test_skillnames.py` (the 188 authored skill names a custom
  profession needs -- the text sibling of `glyphs.py`, and like it the file is
  mostly about the INDEX ARITHMETIC, because "188 names came out and they are
  all different" is worth nothing here: `assign()` RAISES on a duplicate, so the
  headline is the guard's own output rather than a measurement of it, and
  `name = "Skill %d" % sid` passes it for all 188. **A per-skill discriminator is
  MANDATORY and that is measured, not assumed**: over profession 8 the motif
  alone gives 22 groups worst-case 12, the whole glyph index gives 125 worst-case
  7, and adding the attribute moves that only to 126 and 6 -- skills sharing an
  icon overwhelmingly share an attribute too (the 7-skill icon is six Thunderhead
  and one Galecraft), so 50 names would have collided. So uniqueness is asserted
  STRUCTURALLY, one check per arm with the arm broken inline as a live function,
  and the load-bearing claim is the one no uniqueness check can see: every
  skill's noun must come from the MOTIF of the glyph `iconset` would actually arm
  for it, 176 of 176, with the neighbouring motif as the control that stops it
  passing vacuously. **The duplicate sabotage FAILED on its first version and the
  reason is kept**: duplicating one noun pool onto its neighbour does not collide,
  because the adjective is strided by the motif -- so the stride carries a
  uniqueness guarantee the design never claimed, and the only motifs it does NOT
  separate are the ones exactly POOL apart, which is where the sabotage now aims
  (with `MOTIFS > POOL` asserted first, or the collision is unreachable and the
  check is vacuous). Two constants where the first draft had one: the measured
  worst group (8) and the pool width (10), because conflating them put the
  generator exactly on its own boundary where one skill moving cells turns it
  into a refusal. Also: `assign()` must not depend on dict order -- it sorts, and
  the unsorted version is reproduced live and required to DIFFER, since the caller
  happens to build its mapping in sorted order and CPython happens to preserve it.
  Sections 0-4 need no vault, no archive and no client and score 26 against a
  floor of 26; 36 with a vault. **The floor comment first said "MEASURED" over two
  GUESSED numbers** -- 30/38 against a real 26/36 -- in a file already citing the
  two earlier times that happened, which makes it the third. ~3 s),
  `toolkit/mapdata/test_rebloat.py` (rung E3's driver, which is the only tool
  here that deliberately DESTROYS a payload — it zeroes a map's Bloated stream
  so the client is forced down the re-bloat path — so almost every check is a
  refusal. **The gate the whole trigger rests on is measured, not assumed**:
  after a zero-length replace, all ten of the client's open-time rules still
  pass and the row reads back as 0 bytes, which is what makes FINDINGS 17.1's
  cheapest provocation usable at all. The arm/revert cycle is the one positive
  claim and it is byte-identical over the WHOLE reservation, because a
  zero-length replace sets size 0 and a reservation is `ceil(size/512)*512`, so
  the row's blocks are released to the client's free map (FINDINGS 18.11) and a
  revert restoring only the payload would look like a success. Four refusals
  cover maps that could not answer the question — already armed, no Stripped
  input, missing Terrain or Props (FINDINGS 34's unguarded `je`s mean NO Path
  chunk is produced even if the client does compile, so such a run could not
  tell that apart from a client that never compiles), and no baseline mesh,
  since without one "a Path chunk exists" is satisfied by bytes we did not
  delete. Two write guards refuse `C:\gw` and `vault/dat_study` case-insensitively
  and below, each with a POSITIVE control that an ordinary copy is allowed —
  a guard that refuses everything protects nothing because the tool never runs.
  Sections 0-3 need no vault and score 22 against a floor of 28. ~20 s),
  `toolkit/mapdata/test_stripbuild.py` (the STRIPPED-map assembler -- the input
  the CLIENT's compiler reads, so most of what it must get right is not
  checkable by decoding our own output and FINDINGS 43 is the run where the
  client agreed. What this file pins is the three rules that run cost, each a
  REFUSAL with a positive control so it cannot be "refuse everything": Zones
  must precede Terrain (terrain bloat asserts `state->zones`); the rect is
  DERIVED as `dims * 96.0` and `build()` has no rect parameter at all, asserted
  on the syntax tree, because the converter asserts
  `dims.x * XY_DIST == mapRect.x1 - mapRect.x0`; and **the Path chunk's boundary
  point is a flood SEED that must stand on walkable ground** -- seeded on a
  sawtooth the client asserts `segments->Count()` at PathData:365 and builds
  nothing, so the refusal names that assert in its message. Its two controls are
  what make it a measurement: the SAME point is accepted on flat ground, so the
  rule is the slope under it rather than where it is, and the far edge reports
  90 degrees rather than a number invented from one row. It also pins the
  `cell_of` trap that shipped broken here -- grid row 0 is world maxY, so the
  obvious `(0, 0)` corner divides to row `dim_y`, one past the end, and the
  first version answered "outside the map rect" for a point plainly inside it.
  Provenance is tested rather than assumed: no bytes literal over two bytes in
  the module, AND the borrowed payloads are grepped for in the source as raw,
  hex, spaced hex and `\x` escapes, because a docstring quote passes a
  syntax-tree scan. The borrowed bytes are read from the owner's archive at
  run time and the report NAMES every borrowed chunk rather than giving one
  percentage; the generated dependency chunk lands byte-identical to ArenaNet's,
  which the archive could have refused. **Since 2026-08-12 props is GENERATED**,
  so BORROWED is Header and Zones alone -- 42 bytes, down from 54, and 98.20%
  of the map ours. **And since the same day the props-deps pairing is a rule
  with teeth (section 3d, for rung e10d): a build placing a prop must pass
  `prop_dep_ids` -- `model` is an INDEX into chunk 0x11000004, generated from
  run-time file ids into retail's own slot right after the props chunk -- and
  a build without props must NOT, because the three zero-prop retail maps are
  exactly the three without the chunk. Both directions refuse, and a model
  index past the list is refused too, since the client's failure mode for an
  unresolvable model has never been measured. And since 2026-08-13 section 3e
  pins the ENVIRONMENT pair (rung e10i): env_payload and env_dep_ids together
  or not at all, landing after the Path chunk in retail's slot, the payload
  counted BORROWED because the chunk is not understood — and since
  2026-08-13 the SOUND pair (rung e10j) under the same rules. Section 3f
  (rung e10l) pins the AUTHORED path: the same two parameters also take a
  typed `EnvChunk`/`SoundChunk`, encoded here and counted GENERATED, with
  raw bytes still counted BORROWED as the control -- one path swallowing
  the other would make the census meaningless. That is earned rather than
  assumed: the client compiled an env chunk this toolkit assembled with a
  GROWN zone list, so every byte after tag9 shifted, and carried it
  verbatim.** Sections 0-3f
  score 46 on
  placeholder constants of our own and need no vault, against a floor of 59 --
  and the vault-less score (27 then, 46 now) was the first number that path
  ever printed, because `vaultpath.require_dir` raises SystemExit, a
  BaseException, so the `except Exception` around it never fired: a vault-less
  run died before the verdict, its `LEDGER.skip` had never executed once (one
  argument where it takes two), and the 30 the comment claimed was a number
  nobody had seen),
  `toolkit/mapdata/test_props.py` (the props chunk `0x10000004`, the last one
  `stripbuild` had to borrow and the one that mattered -- FINDINGS 34 makes it a
  hard gate, so while it was borrowed no map from this toolkit could hold a
  single tree, wall, door or portal. **349 of 349 byte-identical**, and that is
  deliberately the WEAK half: the record is VARIABLE LENGTH (20 bytes plus four
  per outline point), so a codec that stored each record's own length
  round-trips everything and understands nothing -- the memcpy saboteur is BUILT
  and RUN, passes the headline, and is caught by exactly the three mutation
  controls that grow a decoded chunk in place and require the emitted counts to
  move, read back by a walker written here out of `int.from_bytes`. The layout
  is a MEASUREMENT, not a preference: the stride came from an oracle in another
  chunk (slide a window, keep the offsets whose float pair lands in the map
  RECT from Map Parameters -- gaps are 49.1% four and 40.9% sixteen, alternating,
  so 20, with the first hit at offset 10 in all twelve maps), tag 6's stride is
  4 and every other value tested closes only the 200 maps where its count is
  zero, and the rival layout that a stride-20 hexdump suggests -- model u16 at
  the END, five-byte tag-0 header, self-consistent, and what `PROPS.md` was
  written under -- closes for **0 of 349** and is kept as a control. The oracle
  is 285,670 of 285,670 prop positions inside their map's rect. What the corpus
  CANNOT decide is asserted too: tag 6's count must be a u16 because one map
  holds 611 entries, while tag 4's largest is 81, so its width is undecided and
  the check says so -- if it ever reddens the ambiguity is gone.
  **And since 2026-08-12 section 9 is the CROSS-STREAM oracle, FINDINGS 44's
  strongest result promoted out of prose**: the Bloated `0x20000004` tag-0
  section's declared u32 equals `2 + 48*props + 8*points` PREDICTED from the
  Stripped chunk alone -- 349/349 under `--all`, five rival formulas matching
  0 of 335 discriminating maps -- and beneath the size the two streams agree
  record for record via `BloatedProps.corresponds()` (model, position bytes,
  flags, point count, world-coordinate ring, and the scale FORMULA holding
  EXACTLY, which took that reading from INFERRED to compiler-corroborated).
  `BloatedProps` is READ-ONLY and section 3d asserts it has no encode --
  five of its six sections are opaque, so a round trip could only be a
  memcpy. Sections 0-3d
  need no vault and score 81 against a floor of 99; `--all` is 110 checks
  reading BOTH streams of every map, MEASURED 2026-08-12 at 718 s against the
  201 s the Stripped-only sweep took.
  **The client was read AFTERWARDS and agreed**, which is the shape that makes
  this worth trusting: the framing came out of the archive alone, and the
  disassembly of `0x0073E260` -- a DIFFERENT pipeline from the one `PROPS.md`
  was tracing, whose `0x00712200` parses the BLOATED chunk with five-byte
  headers -- confirmed it and settled the one thing the corpus could not, that
  tag 4's count is a u16),
  `toolkit/mapdata/test_modelexport.py` (the MODEL interchange, rung M3: a
  decoded prop mesh split into typed per-field arrays in `vault/exports/
  models/`. **The structural check is the RE-INTERLEAVE and it is the reason
  the rung is trustable**: the exporter DE-INTERLEAVES a vertex block, which is
  a real transformation rather than a copy, so the test puts the exported
  arrays back together with a packer written out of `struct.pack_into` -- no
  code shared with the module -- and compares against the geometry chunk's own
  bytes read FRESH from `Gw.dat`. **519 of 519 sub-models over both reference
  maps, all nine formats.** It did not pass first time and that is the point:
  the exporter's first version silently dropped `dat_fvf` bits 12/13, the
  TANGENT FRAME, 24 bytes a vertex, and produced a perfectly plausible mesh --
  six sub-models of format 12405 failed the re-interleave and nothing else
  could have noticed, because a dropped field costs no vertex, no triangle and
  no radius. Byte-exactness is what forces the two UNNAMED fields (bits 1 and
  3) to be carried as raw bytes, and section 3's two POPULATION guards are
  what stop the check passing vacuously on a sample holding no format that
  carries them -- the default sample has 1 tangent-frame and 6 unnamed-field
  sub-models, `--all` has 10 and 78. The cross-file ORACLE is M1/M2's run
  through the SERIALISED interchange: `f11 == scale * max 2D radius`
  recomputed from the exported position sidecar READ BACK OFF DISK, against
  prop records in a map file this module never opens -- **474/474 and
  664/664**, and required to EQUAL `test_modelfile.py`'s in-memory figures,
  because serialising may not change the geometry. **Section 5 records the
  oracle that ISN'T**: the rung was scoped around checking collision meshes
  against retail outline rings, and on the reference maps the two populations
  are DISJOINT -- 46 props with a ring, 30 on a collision-carrying model,
  **ZERO with both** (Pre-Searing 34/23/0), with the corpus at 28 of 14,095,
  about what independence predicts. The negative is pinned as a measurement
  rather than dropped, and the first reading of it -- "disjoint" from the
  reference maps alone -- was itself the §B4 small-sample trap and is
  corrected in place. **What replaced that oracle is stronger, because the
  decoder cannot force it** (section 6 asserts on `decode`'s own source that
  it validates RENDER indices only): every collision index below its mesh's
  vertex count (2,265/2,265), every mesh a triangle list (28/28) with the
  rival header order `(nv, ni)` at **7/28** pinning `u32 ni` as the first
  field, every collision vertex referenced. **WHICH CHECKS ARE LOAD-BEARING
  WAS MEASURED**, by building eight sabotaged exporters and running the file
  against each -- the table is in the floor comment. Two results earn their
  place: a truncated vertex array reddens NINE checks now and reddened
  NOTHING before section 3's read-backs were guarded, because it raised
  IndexError and killed the process, printing no verdict and no floor
  shortfall (the one failure `checks.py` cannot see, `test_content.py`'s
  shape); and a MEMCPY loader that stashes the source block reddens nothing
  -- correctly, since the files it writes are still right -- while **memcpy
  PLUS a corrupted sidecar is caught by exactly ONE check**, the
  `_sidecar_positions` read that unpacks the file with `struct.unpack` and
  never touches `load_model`, with the re-interleave and both f11 oracles
  passing green beside it. Every other check in the file reads geometry
  through the module's loader, which is why that one must not. The triangle
  lists are checked separately for the same reason -- the re-interleave
  covers vertex BYTES only and the oracle covers positions only, a gap found
  by reading the suite rather than by a sabotage. Sections 0-2 build a model
  geometry from `struct.pack` and score 27 against a floor of 48; `--all` is
  49. ~85 s),
  `toolkit/mapdata/test_modelfile.py` (the prop model decoder -- rung M1 of
  `studies/models/PLAN.md`, the layout customarea §5 measured from scratch
  scripts promoted to committed code -- and the cross-file oracle that makes it
  trustable: the Bloated prop record's `f11` equals scale x the referenced
  model's max 2D vertex radius, a number crossing TWO FILES and eight decode
  steps through committed code (props.py -> dependency pair -> file-id table ->
  MFT row -> geometry chunk -> sub-model walk -> vertex stride), so no decoder
  error at any step survives it. **474/474 and 664/664 at 1e-5** on the
  reference maps' comparable props with the 3D-radius rival pinned collapsed (1
  and 7); `--all` reproduces the full 14-map sample from committed code
  -- 2,048 model files: 1,741 unique / 1 ambiguous / 306 no-close, f11
  **12,782/12,875**, rival 103, twelve (dat_fvf, stride) pairs, ti and n0
  divisible by 3 on 3,834/3,834 -- MEASURED at 227 s against the default's
  121 s. The three failure populations are pinned APART (§A5's lesson: conflating
  them manufactured a false theory) and PER MAP, because Pre-Searing's no-close
  rate is 77/229 against the corpus ~15% and an average would hide both.
  **The stride is the CLIENT'S OWN three tables since M2** (VA 0x00BF5B80/
  0xBF5BC0/0xBF5BE0, accessor 0x00688010), and section 5 re-reads them out of
  the vaulted image through the test's OWN PE walk so the module's literals are
  pinned to ArenaNet's bytes rather than to a transcription, with a read four
  bytes early as the control. **They REPLACED a byte-cost rule of ours, and
  that correction is the lesson the file exists to carry**: the two rules agree
  on all twelve real formats and differ on 60,168 of 65,536 words, so a wrong
  rule closed 1,741 files and satisfied a two-file oracle on 99.15% of props
  while the corpus could never show it. **dat_fvf 0x2C never existed** -- its
  one sighting was our misparse of the ambiguous file 0x1BAE2, which the client's
  tables resolve to a single closure at the common format 21, and the ORACLE
  confirms the fix from a source sharing nothing with the binary: that model's
  props score f11 **0/16 under the retired rule and 16/16 under the client's**,
  which is the whole corpus improvement 12,766 -> 12,782 and shrinks §A5's
  unexplained population from 109 to 93. The retired rule is REPRODUCED as a
  live function so all of that is a difference between two answers rather than
  prose. GWMB's tables ARE these client tables, so §B6's recorded disagreement
  resolves in UPSTREAM's favour -- the direction nobody predicted. The
  ambiguity moved rather than vanished (0x25AA9 at 170/65,842) and both files
  are pinned, because closure is NOT identity (§B5). Section 6 establishes the
  vertex FIELD MAP by refutable prediction rather than by field size (the
  envchunk tag-6 lesson): **normal unit on 90,108/90,108** with the same read
  four bytes early unit on 2.7%, tangent-frame vectors unit 20,034/20,034 and
  93.0% orthogonal against a 26.0% next-vertex control, texcoords 97.8% inside
  +/-16 over a real range of -519.7..520.4 so a consumer must WRAP not clamp,
  and **bit 1's D3DCOLOR reading REFUTED** -- high three bytes zero on 9,128 of
  9,128, ten values all <= 9, so it is an index whose purpose stays UNVERIFIED.
  A sabotage that quietly reads the 3D radius as the 2D
  one was built and run and reddens 5 checks from three directions, the
  synthetic literal plus both maps' oracle and rival. **The block-H fixture
  (2026-08-16, rung U1): block H occurs on 0 of 20,661 archive geometry
  chunks, so the 20,661/20,661 closure was never evidence for the H term --
  a synthetic H-carrying chunk now decodes and closes, the same chunk 4
  bytes short refuses, and streak-systems-with-zero-streaks is refused the
  way the client refuses it (error 0x1D at 0x00795664, a refusal
  `trailing_end` did not implement until the fixture existed to test it).**
  Three scores, each MEASURED rather than subtracted, because the file needs
  TWO vault artifacts that fail independently -- against a floor of 64
  (61 -> 64 with the H fixture, measured green before raising). ~121 s),
  `toolkit/mapdata/test_skelfile.py` (the SKELETON/ANIMATION chunk `0xFA1` --
  rung U1 of `studies/unitmodels/PLAN.md`, the 2026-08-16 recon's verified
  walker promoted to committed code. **The headline is closure, and here
  closure is OUR assertion, not the client's**: the FA1 parser's success path
  at `0x00796905` never compares its cursor to the chunk's end, so
  `cursor == len(payload)` is a check the artifact can refuse -- the study
  measured **14,571/14,571 byte-exact over the complete flags=515
  population**, and `--all` reproduces that number exactly from committed
  code (plus the population identities: 21,421 heads, exactly one non-ffna
  anomaly at the known row 8316). The default run is a deterministic
  stride-89 sample: 241 rows -> 160 FA1 carriers, closure 160/160. **The
  synthetic section is the part no census can replace**: `n56`'s stride
  fires on 0 of 14,571 corpus files (disasm-only, UNVERIFIED), so the
  builder -- which writes payloads from ITS OWN size literals, the
  full-options fixture pinned to a HAND-COMPUTED 623 bytes -- is the only
  place `n56_mult` is testable, and it is sabotaged in both directions
  there, one check per variant. Every sampled payload is also walked by an
  independent straight-line transliteration with hardcoded strides
  (agreement on the closure VERDICT, 160/160 -- the cursors are not compared
  to each other because on success each equals the end by its own
  arithmetic and the comparison could not fail; the review struck this
  file's original claim). The transliteration's moved-n38 variant is the
  ORDER CONTROL with its vacuous half SPLIT: collapses on all files with
  n38 and n3C non-zero, still closes on the n38>0/n3C==0 files where the
  loop runs over unmoved bytes (34 sampled), and the n38==0 population is
  EXCLUDED as untestable rather than counted -- two textually identical
  code paths cannot disagree.
  Sixteen one-term sabotages scored ONLY over the subpopulation that fired
  each term, each held to its MEASURED full-population aliasing ceiling --
  and the ceilings are themselves the file's first correction: "collapses to
  zero" passed at n=160 and at the study's n=600 and was REFUTED at
  n=14,571, where six "clean" variants carry 1-29 survivors (worst 0.2%,
  hdr=0x5C) by the same shifted-read aliasing the study verified for
  n38_mult; survivor rows are printed, exceeding a ceiling is a regression
  (`n38_mult`/`n50_mult` stay under a 25% minority bound, measured 12.0%
  full-population). Invariants
  the decoder cannot force: span binding `lo <= hi <= n3C` over every
  sampled sequence record (628, 0 violations; 50,127 in the study), key
  times NON-DECREASING per span with strictness deliberately NOT asserted
  (10 corpus files carry exact duplicates; ArenaNet's MdlAnim:367 reads a
  different array), the 1/30 s key grid at >= 99%, and **the COMPOSITED
  equivalence** -- FA1 flag bit 0 <=> the container has no geometry chunk,
  two independent places in the archive, 160/160 sampled and 14,571/14,571
  in the study; flag bits 3/5/6/7 checked through the module's OWN
  `flags_presence()` rather than a private copy of its pairs (the review
  caught the test measuring its own inline table while the shipped method
  went uncovered), 640/640. Anchors pinned by byte size: 116228 the
  hatcher's COMPOSITED shell (29,495 B, no geometry), 116366 the
  self-contained worm (82,169 B, also reached via `Skeleton.load`), and
  116703 the 0x0057 body pinned to carry NO FA1 at all -- the absence is
  the composite mechanism's other half. **Section 0b is rung U2's typed
  animation layer** (`studies/anim/FINDINGS.md`): a second builder with
  its own literals packs REAL channel content -- blk2C's times-prefix SoA
  sections (N int32 times then N vec3f / N float4 quaternions; the AoS
  "16-byte group" framing was the wrong overlay and its quaternion
  refutation an artifact of it, re-measured 16,263,916/16,263,916
  unit-norm at full population), blk48's 4-byte sub-header and two vec3
  sections with the bit-27 loop flag, n40's sorted-seq-index-then-18-byte-
  bodies sound events, n3E's {type, param} event track, and the sequence
  record's start/end clamp window (MdlSeq 0x00792F56) -- and `anims()`/
  `tracks()`/`sound_events()`/`event_track()`/`sequences()` must read it
  all back, plus the worm-anchor checks of the invariants the decoder
  cannot force (emitter-attach bits summing to n34, the invariant
  MdlAnim:1121 enforces at runtime, measured 14,571/14,571; 3,919/3,919
  unit quaternions; the sorted sound-event index prefix; every node's
  link byte referencing an earlier-or-self node -- the hierarchy
  invariant, 121,532/121,532 corpus-wide with zero violations). **The
  U2 review added the failing controls those two unforceable checks
  lacked**: a misaligned stride-20 float4 overlay on the same bytes
  (~35% vs the true layout's 100% -- a gap control; the 0.30%-vs-100.000%
  collapse at equal tolerance lives in the corpus run, since the worm's
  near-identity quaternions make any misaligned window score ~35% on
  this anchor), and a deterministic link rotation that must violate the
  `<= own index` half (the `< n2C` half is a multiset property a shuffle
  cannot refute). The sound_events() empty-span regression -- the
  TypeError that stopped U6's first strided-writer run (2026-08-16,
  `studies/unitwrite/FINDINGS.md` §2) -- is pinned TWICE, because two
  arcs fixed and pinned it independently within the hour and the merge
  kept both sides' checks on purpose: the minimal fixture pins
  `sound_events() == []` where n40 == n44 == 0, and section 2
  regression-pins the same answer on every sampled no-n40n44-span
  corpus file (the 72.5% majority class). 92 checks against a floor of
  84 (the mandatory core is 74; the corpus sabotage and order-control
  pools can legitimately empty on another sample and declare skips).
  ~25 s; `--all` reads every head row, ~25-45 min),
  `toolkit/mapdata/test_mdlrefs.py` (the model's REFERENCE-LIST chunks
  `0xFA5/0xFA6/0xFA8/0xFAD/0xFAE` -- rung U3 of `studies/unitmodels/PLAN.md`,
  the one generic reader all five go through (`0x00796DE0`, exactly five call
  sites) decoded under the client's own record rule, read from the scanner
  at `0x00908260` (an 11-instruction scan body): a record is u16 words ended by
  the FIRST ZERO WORD, variable length, NOT fixed 6 bytes. **The headline
  control is a rival that must fail**: the fixed-6 reading closes on every
  FA6/FA8/FAD chunk in the archive (every record there happens to be 2
  wchars), so the test builds the discriminating shape -- FA5's null slots --
  from its own byte literals AND requires the rival to fail on the corpus
  null-slot population in BOTH directions (fails exactly where a null slot
  exists, 104 chunks at the default stride 53; full population 5,393 of
  20,661 FA5 chunks / 11,894 slots). Closure is OUR assertion: the client
  copies exactly the consumed bytes with no cursor-vs-end compare
  (`0x00794B70`) and silently loads an EMPTY list on a malformed record
  (error path `0x00794C27`), where the module raises at a named gate --
  refusals for the no-terminator record, the count overrun, the odd trailing
  byte, and the scanner's end-1 edge (a zero BYTE on the last byte is not a
  zero WORD, `0x0090826B`) are each pinned beside a passing control.
  `--all` decodes every reference chunk on every flags=515 head -- 30,722
  chunks, zero failures -- and pins the population literals: FA6-first
  exactly 388 (reproducing the recon's independent prefix sweep), FA8 252
  chunks / 2,467 records / 394 distinct targets all ffna type-2 with FA1 and
  without FA0 (the §5.3 claims widened 10x past the 25-chunk caveat), FAE
  exactly 6, and every 2-wchar record resolving in `file_id_table(raw=True)`
  via the dependency-pair formula. **The sound-chain oracle** re-runs the
  study's FA6 -> ffna type-8 -> MPEG identification through the committed
  module: the three anchors' 60 distinct type-8 descriptors' own chunk-0x1
  entries, 231/231 valid MPEG-1 Layer III frame headers by field values
  only (nothing copied), with the header oracle itself refused in seven
  synthetic directions first. Anchors: 116228 FA6=30/FA8=15 with first link
  15018, 116366 FA5=5/FA6=16, 116703 FA5=3 and NOTHING else -- the hatcher
  body's FA6-lessness is the composite split's other half. 52 checks
  against a floor of 45 (the FA8/FAE-dependent sections declare skips on a
  sample that misses them). ~25 s; `--all` ~15-20 min),
  `toolkit/mapdata/test_unitassembly.py` (the ASSEMBLY RESOLVER -- rung U4 of
  `studies/unitmodels/PLAN.md`: a unit definition (0x0056 shell + 0x0057
  bodies, from a capture via `npcdefs.py` or a `content/*.toml` row) resolved
  to the CLOSED archive file set the client's loaders would reach -- shell ->
  FA8 links recursive with a visited set (the cached by-id loader
  `0x00794260`'s closure) -> bodies -> FA5 textures -> FA6 sound descriptors
  -> their type-8 chunk-0x1 audio -> FAD/FAE, every id checked against
  `file_id_table(raw=True)` and every walked container decoded, or the
  resolution records a NAMED problem. **The headline is the acceptance
  number**: the three keyed live captures' 54 pooled definitions resolve
  54/54 closed and 54/54 geometry-complete -- 1,393 distinct files, role
  histogram pinned (shell 32, body 40, link 134, texture 113, sound 241,
  audio 830, fad 8, fae_model 0), set sizes 3/158/233 with the carrying
  definitions named. **The COMPOSITED rule is DERIVED, not assumed**
  (`needs_body` reads FA0-absence; the FA1 bit is the independent second
  witness, 161/161 carriers agreeing) and cross-checked against wire
  presence of 0x0057 with every count TRI-VALUED and MEASURED -- with FA0 /
  without / unreadable, one tuple check per population, after the U4
  review caught the first version printing its "reversed rule" as f-string
  arithmetic that was 0 by construction: capture 20260807T143055 alone 8/8
  0x0056-only shells CARRY FA0 (measured reverse 0, unreadable 0), 36/36
  with-0x0057 shells LACK it, 33/33 distinct model ids carry it; pooled
  11/11, 43/43 per-definition (the unitmodels SS5.4 "43/43", whose NOUN
  was wrong -- it counted definitions pooled, not model ids), 40/40
  distinct -- plus `needs_body` == wire-0x0057-presence on all 54, the
  only check covering the seven with-0x0057 definitions outside 143055.
  **The visited set has its own synthetic cycle fixture** (A<->B links plus
  a self-loop through a pre-filled facts cache, under a call budget that
  turns a hang into a red check), because the corpus cannot exercise it:
  the live FA8 graph is acyclic and terminates at depth 1, so the review's
  remove-the-visited-set mutation stayed green on real data and is killed
  by this fixture (re-verified against the mutant). The hatcher pair
  (1471: 116228+116703) is pinned as the full
  232-id set and the worm (1442: 116366) as 75 ids, and the content-row
  entries (`npc.hatcher`/`npc.lakeside_worm`) must resolve to the IDENTICAL
  sets -- one resolution path, two id sources. The origin gate is proved in
  both directions on synthetic capture dirs: live+live pools, live+ours
  REFUSES naming both, UNKNOWN never pools. Controls that fail: an id
  outside the raw table leaves the set OPEN, a map file (ffna type 3) as
  shell is refused not walked, and npcdefs' 0x0057-disagreement refusal is
  FIRED through the decode seam -- an injected conflicting repeat must make
  read() refuse naming the definition and both lists. Two review-flagged
  entailed checks were removed (hatcher!=worm needs_body; a separate
  FAE==0 beside the pinned role dict -- a check that cannot fail
  independently is the recorded defect class). 57 checks, floor 57 --
  nothing legitimately varies; vault-less runs skip sections 2-4 and go
  red on the floor. ~90 s: needs `vault/dat_study` and the three keyed
  live captures),
  `toolkit/mapdata/test_datmove.py` (the RELOCATION verb `datwrite` refuses on
  purpose, and the wall FINDINGS 38 ran into: `--replace` writes uncompressed and
  will not move a row, so authoring only worked where the stream SHRANK. Against
  an archive the test builds with free runs of KNOWN size -- 1, 2 and 6 blocks
  usable plus an 8-block one carrying a planted `Mft` generation -- so "it took
  the 2-block run and not the 6-block one" is a fact about the policy rather than
  about this machine's copy, and the LARGEST run in the archive is the one a
  writer may not have, which is the shape the real archive has. The headline is
  not that the payload came back: a relocation can break one invariant no
  checksum sees, two rows sharing blocks, since each crc is computed over its own
  row's bytes and all three still verify across an overlap. So the load-bearing
  check is that after a move no two reservations intersect AND every other row
  still reads back byte-identical -- with a negative control that corrupts an
  offset by hand and requires the walker to catch it, because a "0 overlaps" that
  has never reported anything else is not a check. The walker is written in the
  test out of `int.from_bytes` and shares no code with `datmove.overlaps`. Five
  sabotages were built and run and all five reddened; the numbers are in the
  floor comment, and the one worth noting is that skipping the old-reservation
  zeroing reddens exactly ONE check. No vault and no client -- and the client half
  is no longer missing: FINDINGS 39 moved a real map's Stripped partner **1.6 GB**
  and the retail client found it, compiled from it and emitted ArenaNet's own bytes,
  with 0 overlapping pairs afterwards on the real 4.2 GB archive. **DURABILITY
  across a play session is MEASURED as of 2026-08-13, and this line said it was
  not until 2026-08-14** -- which is how a session re-opened it as an open item a
  day after running it, so the answer lives here rather than only in the study.
  Two witnesses, `studies/crossbuild/FINDINGS.md` 4b and 4c: an authored row
  survives a session in which the client demonstrably rewrote the archive, on the
  RELOCATED case (10,714 B that did not fit its 4,608 B reservation, byte-identical
  afterwards while the client recompiled its Bloated partner FROM it, 64 trapezoids
  and 4,096/4,096 height samples exact) and on the IN-PLACE case (three icon rows,
  a different archive copy, all three byte-identical). **The arm is what makes the
  vacuity control free** and is the method point worth carrying: a zeroed head
  REQUIRES the client to write, so the run measures survival rather than whether
  the client happened to touch anything -- without it, "nothing changed" is
  INCONCLUSIVE and not a pass. What is still unmeasured is a session long enough to
  trigger whatever rotation the 29-member set participates in, and the bit-31
  watchlist is unprobed because our rows are not on it. **And the MFT ALTERNATES
  between two offsets rather than drifting** -- copies with identical entry counts
  sit at both, so it is a phase and not a function of table size -- which means a
  journal is only good until the client next runs: `--revert` refuses afterwards,
  correctly, because replaying MFT edits into abandoned bytes restores nothing and
  leaves all three checksum rules PASSING),
  `toolkit/mapdata/test_datplan.py` (where a new file may be PUT, against an
  archive the test builds with two shadow containers in it: that placement is
  best fit rather than the head of the largest run, that a run carrying a live
  container generation is withheld whether the signature is at its head or 428
  blocks in, and that the plan names what it withheld instead of dropping it. It
  exists because "free" was measured as the gap between reservations, and by that
  measure 88.5% of `Gw.dat`'s free space is live container generations the client
  rotates through -- so the planner aimed every insert at a complete shadow MFT.
  Its own fixture had to be relaid: the first version's runs ran largest-first
  down the file, which is what the broken code produced, so the ordering check
  passed against the defect.
  **And since 2026-08-14 section 8 asks where an edit POINTS, which thirty checks of
  placement policy never did.** `datplan` carried its own row arithmetic and got three
  of four MFT sites wrong: `mft_offset + (row - 1) * 24` under a line reading "MFT row
  N", "MFT row 3 (the table describing itself)" addressing row 2 -- the FILE-ID TABLE
  -- and "MFT row 2" addressing row 1, the file header. The tool applies nothing, so
  those addresses were handed to a human to apply BY HAND, and this file was green at 30
  the whole time. Every "MFT row N" edit of every plan is now resolved to the 24 BYTES
  THE FIXTURE WROTE THERE by a reader written in the test, with the shipped
  `(row - 1) * 24` kept as the control that must land on row N-1 -- and the bound is
  refused AS a bound, since row 0 reached `entries[-1]` and planned a write to the LAST
  row of the table, which a "some blocker" predicate passes because that row's
  reservation is 0 bytes. Floor 30 -> 38),
  `toolkit/mapdata/test_datalloc.py` (the THIRD write verb: rows that did not
  exist, and the file id that makes the client able to name them. `--replace`
  needs a row, `datmove` needs a row; both start from one ArenaNet made, which is
  why every authored map so far has been installed by DISPLACING a real retail
  area. The fixture carries what the real archive has and `test_datmove`'s does
  not -- an MFT whose size is not a block multiple, so it has genuine growth
  slack and its reservation ends at EOF, a file-id table with headroom inside its
  own reservation, and **an ARMED MAP HEAD beside a genuine spare**. That last
  pairing is the bug this arc found: `datplan.free_rows` tested `size == 0`
  alone, and `rebloat --arm` sets a live map head's size to zero ON PURPOSE, so
  on `vault/dat_c2/Gw.dat` it returned `[71496]` -- the head of map 143, flags
  259, USED, still chained to partner 71497 -- and `plan_insert` prefers
  `erased[0]`. The next insert into that archive would have taken a live map's
  head, orphaned its partner and left the file id resolving to somebody else's
  payload, with all three crc rules still holding. It now asks the client's own
  question, the USED flag. **Three things a one-row insert gets wrong and this
  refuses:** a map is TWO rows chained by `alloc.nextStream` at +0x10 and
  `plan_insert` plans no such field and returns the same row index when called
  twice; a file id is not optional, because the open-time reconcile deletes an
  unnamed USED|FIRST row at index >= 16 and frees its extent, so an unregistered
  row works exactly once; and the MFT can grow ONLY into the slack of its own
  last 512-byte block -- 424 bytes = 17 rows on the 38833 pair, where the gap
  measure claims 4,266,920 -- because the next block is a container generation or
  EOF. The write order is asserted as a property rather than described: payload,
  then rows past the declared count, then the id pair past the declared table
  size, all three invisible; then the two writes that make them exist. **Section
  7 is the one that earns its place** -- it tears the archive at exactly that
  window, proves `Archive()` refuses it (`entry_count * 24 != mft_size`), and
  then proves `--revert` still works, which it did not before `mft_offset_of`
  read the MFT address from the 32-byte header instead of by opening the whole
  table. The recovery path could not open the archive in the one state it exists
  for. Everything is re-derived from raw bytes by readers that import nothing
  from `datalloc`, and the chain is walked three ways -- a Floyd walk out of
  `int.from_bytes`, `mapchunks.MapIndex`, and the corpus-wide orphan list --
  because the first draft asserted `nextStream` once and a sabotage that wrote 0
  there reddened exactly one check. **Section 11 is the one that found a real
  defect in the code it was written against.** It replays every prefix of the
  write out of the journal and asserts the property the order exists to serve:
  no prefix may leave a USED|FIRST_STREAM row that the file-id table does not
  name, because that is the shape the reconcile frees and memsets. The first
  version of `alloc()` wrote every row in one pass and called it invisible --
  true only of APPENDED rows, since a REUSED spare is already inside the declared
  table and goes live the instant it is written. Section 11 reported three FAILs
  against code that was green on every other check in the file: an unnamed head
  on disk, and, with a reused head and an appended partner, a `nextStream`
  pointing past the declared count while the loader asserts `nextStream < count`.
  The order now publishes the id record FIRST and reused rows LAST, taking a
  transient dangling record -- which the client drops -- over an orphan row,
  which it deletes. Eight sabotages, all eight red, counts in the floor comment
  and re-measured after every change. **Also proven at full scale**: a map pair
  allocated into a 4.2 GB copy of the live 38833 archive, preflight 10 of 10 with
  the orphan count rising by exactly one, then reverted byte-identical by sha256.
  No client, though: **no client has ever read a row this verb allocated**, which
  is the same sentence `datmove` carried before FINDINGS 39. Floor 98),
  `toolkit/mapdata/test_bit31.py` (the REPLACEMENT-PENDING census -- the file ids
  carrying bit 31, which `FcArchive` binds when it has requested a replacement
  and deleted the plain name (`archive.py`:486, read out of the client). The
  population is small, it MOVES, and it moves under our own content: **two
  `content/maps.toml` rows are recorded under `0x8001B97D`**, and row 7982 --
  `donor_row` for every `content/areas.toml` row -- is named by two bit-31 ids.
  **The headline is deliberately not the count.** "29 bit-31 ids" is a number an
  almost-right census also prints, and the tool's whole job is to be believed
  when it says NOTHING CHANGED: the 900 s session of 2026-08-14 reported
  `29 -> 29`, and that reading is only worth anything because the two SETS were
  compared -- four ids clearing while four others are newly set leaves the count
  identical and describes a different archive. So `diff` never consults
  `len(bit31)`, and the control is the **count-comparing reading REPRODUCED
  INLINE** as a live function that must answer "no change" on the same pair the
  real one catches, with every one of the five scalars asserted IDENTICAL across
  that swap so none of them could have carried the signal either. The fixture
  holds every shape at once -- a plain id, a bit-31 id on a map-flagged row, two
  ids aliasing ONE row, an id whose MASKED form also binds, and an id naming a
  row the archive does not have. The last is required to be REPORTED rather than
  raised, because the tool describes copies we did not make; the second-to-last
  exists because `archive.py`:475 claims the masked form is never separately
  present, and a census that could not report it could not check it. Two
  sabotages are built and run: dropping `sha256` from `ROW_FIELDS` makes a
  flipped payload byte vanish, and censusing on the wrong high bit finds NOTHING
  and prints **a clean confident zero**, which is why section 0 asserts the exact
  id SET. Section 7 reproduces the cross-copy population from real archives --
  **29 install / 25 study / 9 run-live**, install->study clearing exactly 4 ids
  over TWO rows with NEITHER a map row while install->run-live clears row 7982 --
  and corroborates `customarea/FINDINGS.md`:967's correction of "two map rows" to
  **four** from an archive that file never read.
  **Section 3 is the one an adversarial pass forced, and it is the file's
  argument**: the first version pinned 3 of ROW_FIELDS' entries, and a
  six-lens audit MEASURED that **seven of ten could be deleted with all 63
  checks green** -- including `offset`, which alone is a ROW RELOCATION
  reporting "NO CHANGE", and `masked_also_binds`, the field whose whole
  justification is refuting `archive.py`:477. So there is now one fixture per
  field, each a real archive edit; nine of eleven move their field ALONE and
  the two that cannot are NAMED rather than faked (`size` co-varies with
  `sha256` because a shorter read is a different hash; `row` cannot be
  isolated because pointing an id at another row brings that row's every
  field with it). Then each isolated field is dropped from `ROW_FIELDS` in
  turn and its own fixture is required to go BLIND -- all nine. A
  COMPLETENESS check unions the keys of a live census and requires each to be
  in `ROW_FIELDS` or in a declared `DERIVED` set, which is what would have
  caught the defect the same audit found in the module: **`counter` --
  `alloc.nextStream`, the sibling link -- was censused and never diffed**, so
  a relink on a map row printed "NO CHANGE" and exited 0. The other module
  defects it found were all the same shape, exit 2 leaking out as exit 1: a
  malformed baseline, an archive with no row 2, and a `struct.error` each
  escaped a narrow `except` and left the CLI at 1, which is this tool's word
  for "the population CHANGED". **And the write guard refused checkouts while
  ALLOWING `C:\gw`** -- `--json C:\gw\Gw.dat` would have truncated the
  owner's 4.2 GB archive, the identical defect `atex.py --make` shipped with,
  reintroduced in a new module three days later. Floors are two shapes with
  ZERO headroom each, both MEASURED: 76 bare (`RURIK_VAULT` pointed at
  nothing), 86 with a vault, section 7 raising the floor itself as its last
  act -- because a single fixed floor left the vaulted run eight checks of
  slack and the audit deleted the whole sabotage section inside it. ~5 s),
  `toolkit/mapdata/test_gwdat.py` (the decompressor, including zero-length codes),
  `toolkit/mapdata/test_pathmap.py` (trapezoid walk, A*, line of sight -- and since
  2026-08-13 route()'s LATENCY, because it runs on the thread that owns the world and
  its worst case in the band a hostile chases in was **336 ms, 6.7 tick periods, 11 of
  1,500 routes over a whole 50 ms tick**, which is an intermittent world freeze and the
  hardest failure here to attribute. Section 10 re-measures that rather than quoting
  it: the pre-fix `walkable`, `_string_pull` and component pre-check are reconstructed
  IN the test, three instance attributes over the SAME route() body, so BEFORE and
  AFTER are two live answers in one process. p50 0.395 -> 0.163 ms, max 346.6 -> 19.8,
  **0 of 1,500 over a tick**. The timing table is deliberately the LEAST of it, because
  a router that quietly returns None or a path through a wall is FASTER: every returned
  path is re-run through route()'s own consecutive-`clip` gate over the WHOLE set, the
  None rate is measured before and after on the same pairs and must be EQUAL, and path
  length is compared mean and worst. The sabotage is built and run -- a route() that
  skips smoothing entirely is faster than the real one (max 10.5 ms against 19.8) and
  PASSES the timing check, so the length check is the only thing standing there, and it
  goes red at mean 2.80 and worst 52.6. Five further sabotages were built against the
  fix and five redden; the sixth, `CELL_SLACK = 0.0`, SURVIVED, and `pathmap.py` says
  so at the constant rather than implying a check nobody has. The load-bearing claim is
  that none of it changed an answer: **0 of 1,500 paths differ from what the old code
  returned**, on Kamadan too. Two checks earned their own design notes -- the vacuity
  guard is a TOTAL-time ratio because the `max(before) > 3 ticks` version reddened on
  SAMPLE SIZE and was the only red in a sabotage that broke nothing, and the latency
  assertion re-times its candidates best-of-5 because the first version read 17.9 ms
  green and 52.4 ms red on identical code while four other agents' suites ran in the
  same worktree. Floor 62 against a green 64; ~105 s, `--routes` shrinks section 10),
  `toolkit/mapdata/test_deploy.py` (rung G's one command, `deploy.py`, which
  takes an area row in `content/areas.toml` from geometry to a map the retail
  client compiles. It is an ORCHESTRATOR -- nearly every line it runs belongs to
  a module with its own test -- so this file checks only what is true of the
  COMPOSITION, and each of its three sections is a defect the first runs of the
  command actually had. **The two kinds of borrowing are different**: structural
  constants (Header, Zones) must come from a map shaped like ours, the biome
  (textures, sun, env, sound) from wherever you like, and taking both from
  Pre-Searing pulled in its 7,208-byte Zones chunk and built an 11,115-byte map
  for a 4,608-byte reservation. **The client must own the archive you armed** --
  every run directory has its own `Gw.dat`, and arming the C2 copy while
  launching the default client compiled nothing. That one is asserted on the
  SYNTAX TREE, and its NEGATIVE CONTROL is the check that earns the section: the
  first version asked whether `main()` contained any `join(dirname(dat), ...)`,
  which it does TWICE because the output path defaults that way, so it returned
  True against a sabotaged source and could not fail. The test now runs that
  exact sabotage and requires the answer to flip. Sections 0-1 and 3 need no
  vault and score 10 against a floor of 14),
  `toolkit/mapdata/test_soundchunk.py` (the Sound chunk `0x10000012`, the map's
  ambient-sound layer -- the second of the two chunks rung E10 could only BORROW,
  now decoded and re-encoded byte-identically, **349 of 349**, 27 checks under
  `--all` and 23 by default. The record is a fixed 24 bytes, so byte-identity is
  the WEAK half: section 2 builds the saboteur that stores the record count `k`
  and replays it, and the mutation control appends an emitter and requires the
  emitted `k`@14 and the payload length to move -- read back by a walker written
  out of `int.from_bytes`. The load-bearing check is the cross-chunk oracle: every
  emitter's `(x, y)` lands inside the map's Map Parameters rect (318/318), from a
  chunk this codec never reads, with a 1-byte-shifted read as the control that
  collapses to 0/318; and the client's own load-time invariant `r_lo <= r_mid <=
  r_hi` holds 318/318. The whole layout was corroborated against the loader at VA
  `0x0076afc0` -- the three radii are SQUARED at load for a sqrt-free distance
  compare, and no magic dispatch means a texture-referencing emitter is not
  decoded here. Sections 0-2 need no vault and score 18 against a floor of 21),
  `toolkit/mapdata/test_envchunk.py` (the Environment chunk `0x10000009`, the sky,
  fog, ambient light and horizon water -- the chunk rung (e10i) proved was the
  difference between a black void and a lit world, borrowed whole then and now
  decoded. Re-encodes **349 of 349** byte-identically, 40 checks under `--all` and
  28 by default. The codec keeps record interiors opaque (the loader itself stores
  tag0/1/3/5/6/8 records as raw {ptr,count} and decodes no colour and none of
  tag6's ten floats -- there is NO `1/101` constant in the image, so the authored-
  slider reading is authoring-time only), so byte-identity is the weak half and the
  section COUNTS are what the codec must re-derive: section 2's saboteur stores and
  replays them, and the mutation control grows the zone list and requires the
  emitted count to move. The framing is a set of PARALLEL ARRAYS (tags 0-7) plus a
  spatial ZONE list (tag9) that binds one record of each array to a world-space
  circle -- confirmed against the loader at `0x0071ef70`, whose two `EnvDataImport`
  asserts name the zone array `envArray`. Three corpus-only readings were CORRECTED
  by the disassembly and each is a thing a wrong reading gets wrong on some map: the
  header is 8 bytes not 5, the tag5-width `flag` is the header word at offset 6 not
  tag0's count (they disagree on 168/349), and tag8 is a real 17-byte section not
  part of tag7's tail -- and tag8 turned out to be the map's DEFAULT SELECTOR TUPLE
  (eight u16, one per aspect array) plus the sun byte, which is what makes the
  architecture close: a default and a zone are the same kind of object.
  **A fourth correction is the one to learn from**: tag6, the 57-byte record, was
  called "the main environment record" on the strength of its SIZE alone, and the
  consumer disassembly says it is the WATER record -- `MapWater`'s parameter block,
  whose `+0x05` is the water plane height (the one float the zone blender refuses
  to interpolate) and whose `+0x00` is a 0..3 mode enum the loader validates with
  `cmp eax,3; ja <abort>`. Inferring a name from a size is not a measurement.
  Two oracles, each from a chunk this codec never reads: every dep-reference field
  (tag0@8, tag4, tag5's four slots, tag6@53/@55) is 0xFFFF or below the length of
  the sibling `0x11000009` dep list -- **0 of 5,897 out of bounds**, while the same
  fields read one byte early blow the bound 5,087 times; and **tag8's sun byte
  predicts the STRIPPED TERRAIN chunk's own `angle_index`** (the two quantise one
  authored angle at a ratio of exactly 127/32) on **313 of 349** maps within a
  quantum, with the neighbouring byte scaled identically scoring 0/349 as the
  control. That second one is quoted as the tolerance figure on purpose: the
  exact-match count is ROUNDING-DEPENDENT (`b=48` lands on exactly 190.5, and two
  maps carry it), so the file states the tie rather than picking 307 or 308 quietly.
  Sections 0-2 need no vault and score 17 against a floor of 28. Since
  2026-08-13 it also pins the NAMED aspects (FINDINGS 55): tag1 is post-process
  and tag3 the directional light, named from the client's own shader-constant
  strings rather than by us, and the two checks that carry those names are corpus
  population facts -- saturation is 1.0 on 648 of 741 records and the tint is off
  on 571, which is the shape of a DEFAULT and is what a rival reading would not
  produce),
  `toolkit/mapdata/test_pathchunk.py` (the pathing chunk's WHOLE-CHUNK codec: a
  retail `0x20000008` decoded to typed values and re-encoded byte-identically,
  **349 of 349** under `--all`, 8 by default. Nothing declared is stored --
  every record size, every one of the eight plane-header counts and every
  element count is re-derived on encode -- because a codec that replayed them
  round-trips every file it can walk while understanding nothing. That is not a
  hypothetical: a memcpy sabotage and a replay-the-counts sabotage were both run
  against this file, both printed the 349/349 headline GREEN, and both were
  caught only by the controls that mutate a decoded chunk in place until a
  payload changes length and require the emitted size and count fields to move
  with it — read back by a walker written in the test out of `int.from_bytes`.
  The named control is an encoder that writes tag 11's size as its true data
  length instead of DOUBLE it, which is what retail declares in 11,795 of 11,795
  planes; it is run on ArenaNet's bytes as well as ours. Also: eleven decode
  refusals including the eight-byte header (the terrain chunk's, and using it
  here desyncs the first record), `pathmap.PathingMap` as a second parser
  agreeing field-for-field on the same bytes, and `minimal()` — a mesh authored
  from nothing — landing on row 46196's plane count, two-byte tag 12 and 3x3
  obstacle grid from its rect alone. **Sections 7-9 (2026-08-12) are the OTHER
  stage**: chunk `0x10000008`, the compiler's INPUT, which nothing in this tree
  could read until then — **349/349 byte-identical and 349/349 exactly `19 + 8n`
  bytes**, with the memcpy caught by a mutation control that appends a boundary
  point and requires the emitted u16 count to move (a stashed-blob sabotage keeps
  BOTH round-trip headlines green and reddens only those two). Its framing is NOT
  the Bloated chunk's despite the shared signature — 9-byte header with a `u8`
  version, records with no size field — so each codec is required to REFUSE the
  other's bytes, the failure otherwise being a plausible desync rather than an
  error. Section 9 is the correction it found: the boundary polygon is **carried,
  not compiled** — identical to the Bloated one in 349/349 — and file id `0x9F5E`
  ships a **27-byte** Stripped chunk holding ONE point whose Bloated partner has
  **3,437 trapezoids**, so tag 7 cannot be what the compiler builds a mesh from,
  which is what FINDINGS 17.2's E3 input contract assumed. That case is pinned by
  file id rather than left to the sweep, because a default sample of 8 contains
  no degenerate boundary and the one finding the rung exists for was reachable
  only under `--all` — evidence that skips by default is evidence nobody sees.
  Sections 0-2 and 7 need no vault and score 56 against a floor of 92, so a
  vault-less run goes red. Default ~40 s and 92 checks; `--all` is 99 checks and
  ~17 minutes — MEASURED 2026-08-12 at 434 s for the Bloated sweep and 565 s for
  the Stripped one, which reads BOTH streams of every map, so budget for those
  two numbers rather than for a round one),
  `toolkit/mapdata/test_trnblend.py` (rung T6's second half: WHICH textures a cell
  blends and how each is masked. A cell samples its four corners' tile bytes, and
  where their tile TYPES disagree — tag 4, not the raw byte, which is T2's finding
  from the other side, so two raw tiles sharing a type make no seam — the client
  emits overlays whose alpha covers exactly the disagreeing corners. The masking
  is not ours to invent: each 128x128 quadrant of a terrain texture is an authored
  COVERAGE SHAPE and a 16-entry table maps a 4-bit corner mask to the quadrant
  (plus a 180° rotation flag, plus optionally a second layer) that covers it.
  Section 1 runs that derivation as a check rather than trusting it: the cover
  sets are re-derived HERE from the four unrotated single-layer rows, they must
  equal the client's INDEPENDENT inverse table at `0x00BF7808` (`{12, 2, 5, 8}` —
  a different array, in the lo path, which never reads the first one), and
  predicting all 16 rows must cover each row's own mask on **15 of 16**, the miss
  being the empty mask 0 the grouping loop cannot emit. The six two-layer rows are
  the sharp part — a union of two separately looked-up quadrants has to land
  exactly — and a mirror-in-x rival rotation is scored live at 8 of 16 against the
  real rule's 15, compared to the real count rather than to a threshold, because
  the first version asserted `< 8`, got exactly 8, and a tuned constant measures
  nothing. Section 2 pins the selection loop with a no-bleed check (no overlay may
  cover a corner belonging to the base) and both refusals. **Section 4 is the only
  one that can refute rather than confirm**: it runs `corner_selector` against
  `chunk+0x2B4` as the RUNNING CLIENT filled it, two int3 captures from Lornar's
  Pass tile blocks (8,18) and (4,2), and demands **2048 of 2048 cells exactly**.
  A near-match is a FAIL, not a rounding difference — a stable sort scores 95%/87%
  here, which is precisely how the wrong model survived three rounds of tuning the
  tie-break, the block origin and raw-vs-mapped tile bytes. The client's sort is
  UNSTABLE (a selection-sort comparator network, swap on strict `>`), so equal
  corners come out in swap order and `sorted()` can never reproduce it. Sections
  1–3 are arithmetic and run on a bare machine; section 4 needs the vault and the
  captures and declares `LEDGER.skip` rather than passing vacuously, which is why
  the floor is the vault-less 26 and a full run scores 29),
  `toolkit/mapdata/test_trnvariation.py` (rung T6's first half: which of a terrain
  texture's four 128x128 quadrants each cell samples. The per-cell arithmetic is
  OBSERVED in build 38797 — one PRNG draw per cell ALWAYS, `quadrant = draw & 3`,
  `seed = (tile.x << 16) ^ tile.y` — and the whole-map traversal assembled from it
  is labelled RECONSTRUCTION, which this file can check for internal exactness and
  explicitly cannot check against ArenaNet's output. Two traps kept armed, both of
  them edits a later reader would think were improvements. **The generator is NOT
  `% 2147483647`**: the client computes the modulo by magic-number division whose
  quotient is one too high on ~3.8% of states and corrects with `+0x80000000`,
  which does not cancel it — so section 1 SEARCHES for the disagreeing states
  rather than quoting them, finds 7,579 of 200,000 (3.79%), and requires every one
  to be exactly +1; a tidied-up clean-modulo port makes that check go red instead
  of drifting on one draw in twenty-six. **An authored cell still draws**: tag 3
  overrides the value, not the draw, so forcing one cell must move exactly ONE
  output byte — with a live skip-the-draw rival that moves 458 of 1,024 as the
  control. Section 4 makes the one thing the disassembly did not settle refutable
  rather than prose: the per-ROW reseed reading makes every row of a tile identical
  (1,984/1,984 — a stripe), the per-TILE reading leaves rows independent (23.4%),
  and the default is pinned. No vault, no client, 0.2 s),
  `toolkit/mapdata/test_trnshadow.py` (terrain tag 7 decoded rather than carried:
  that every retail shadow block's run coding closes on 272 rows of 272 samples and
  re-encodes to ArenaNet's own bytes from the bitmap alone, that the 10x10 window
  rule reproduces the stored 128-byte tail while the 8x8 and 12x12 controls do not,
  and that a set bit means IN SHADOW -- checked against tag 9's lightmap, not
  assumed. Sections 2-4 need `vault/dat_study/Gw.dat`; without it the run scores 14
  against a floor of 24 and goes red, because the synthetic half cannot refute
  anything about ArenaNet's format),
  `toolkit/mapdata/test_mapchunks.py` (the map container: that a map is two MFT rows
  and the archive says so -- 349 heads, 349 partners resolved through
  `alloc.nextStream`, all distinct, chain depth exactly 1, and ZERO partners named
  by the file-id table, none of which our decoder can force; that every chunk id in
  every map decomposes into a stage, a chunkType and one of `s_chunkInfo`'s 23
  slots, and never one of the four whose load pointer is NULL and which the client
  would jump through; that a Dependencies chunk re-encodes to ArenaNet's own bytes,
  which is how the pair encoding was found to ALIAS -- `id0 >= 0xFF00` names the
  same file as `(id0 - 0xFF00, id1 + 1)`, retail uses both forms, and no upstream
  says so; and that the vault-side chunk-index cache is DROPPED rather than trusted
  when its stamp disagrees. Sections 1-4 need no vault at all),
  `toolkit/mapdata/test_terrain.py` (the terrain codec, decode and encode: a retail
  terrain chunk decoded to typed values and re-encoded BYTE-IDENTICALLY — 349 of 349
  maps and both tag sequences under `--all`, 27 in a default run. The headline is
  only worth its exit code because of
  what sits around it -- the record framing is re-derived by a second walker that
  imports nothing from the module under test, the record lengths are predicted by
  two u32s read out of a different record, the cell pitch is cross-checked against
  the Map Parameters chunk (rect/dims is exactly 96.0 and nothing else, with the
  (dim-1) divisor as the control that must not be), and thirteen negative controls
  must go red, including one flipped height byte in a real chunk. It also builds a
  32x32 map out of nothing, which needs no vault. Slow-ish: 25 maps is ~55 s,
  `--all` is ~7 minutes),
  `toolkit/mapdata/test_strippedterrain.py` (the OTHER terrain chunk, `0x10000002`,
  which nothing in this tree could read until 2026-08-12 — and its headline is
  deliberately not the round trip. The height field this codec pulls out of a
  canonical-Huffman bit stream and a 4x4 integer transform must EQUAL, sample for
  sample, the one `terrain.py` reads out of the Bloated chunk: a different encoding,
  written by a different subsystem, that the module never looks at. **349 of 349
  maps, 60,468,224 float32 samples** predicted from compressed bits is an oracle a
  codec cannot force; the byte-identical re-encode is 349/349 too and is reported
  beside it as the weaker claim, with the reconstructed/carried split (65.67%) as
  the honest half.
  **Every coding parameter is RE-DERIVED and the decoder refuses a file whose stored
  one disagrees** — both bases are the minima, both widths are bit lengths, the
  symbol set is exactly what the block uses, every alignment pad is zero — so N green
  decodes are N assertions about the derivation rather than N comparisons of a value
  with itself. The one carried thing is which code length each symbol gets, which is
  ArenaNet's frequency model and is not recoverable from the samples. Two controls
  earn the file: the memcpy saboteur is BUILT and RUN, and required to pass the round
  trip while failing the mutation checks, so the file measures which of its own checks
  are load-bearing; and `_forward4` REFUSES a four-vector off the transform's lattice
  where a truncating encoder would silently move a height — the two agree exactly ON
  the lattice, which is why byte-identity cannot see the difference, and the test
  builds the truncating version to show it. It also pins that the client bakes tag 9,
  the lightmap, rather than storing it: the Bloated chunk's shade bytes do not occur
  anywhere in the Stripped one, 349/349. And its angle control reproduces
  `terrain.py`'s own figure from the other side — 63 of 349 maps carry an index where
  the retired `float32(b*pi/508)` differs and it is wrong on all 63, leaving the 286
  that file measured before anyone had read the client's expression. Sections 0-3 need
  no vault and score 57 against a floor of 66. Default ~25 s and 66 checks; `--all` is
  67 checks and ~20 minutes — MEASURED 2026-08-12 at 1,205 s, so budget for that rather
  than for a round number),
  `toolkit/mapdata/test_mapexport.py` (the neutral map interchange — terrain and,
  since 2026-08-13, EVERY PROP PLACEMENT — with the orientation checked against the
  props chunk `0x20000004` through the test's OWN 48-byte walker. The old framing
  "a chunk the exporter never reads" died the day the props sidecar landed and the
  independence that survives is narrower and stated: the terrain path never reads
  props, the props path never touches the height arrays. Prop `z` sampled against
  the exported height field, with three rival layouts that must collapse — on
  Kamadan the fraction of props within 100 units is 0.304
  against 0.070 for the y-flip, 0.033 for the x-flip and **0.085 for not de-tiling
  at all**, which reproduces FINDINGS §4's 0.089 for the flat row-major rival from
  the other side; Pre-Searing is 0.734 against 0.078/0.139/0.137. Kamadan sits below
  FINDINGS' 0.504 corpus median and is reported at its real value rather than
  dropped. Every prop of both maps lands inside the grid under all four layouts, so
  no control loses on sample size. **The props sidecar (format_version 2) joins BOTH
  streams and makes them check each other**: `StrippedProps` for the authoring bytes,
  `BloatedProps` for the compiled basis, f32 scale and placement radius, through
  `corresponds()` — retail satisfies it 349/349, so the exporter REFUSES a
  disagreement, and the dep lists (`0x21000004`/`0x11000004`, measured identical)
  resolve every model index to a file id plus the MFT's (size, crc), because a file
  id is archive state. Section 7 pins the sidecar against the archive — every
  position equal to the independent walk, every model resolving, the sidecar's own
  props-vs-heights fraction reproducing section 5's number — **and the ROTATION
  COMPOSITION, which `props.py` had open: z first, then x, then y (Blender 'ZXY'),
  per-axis signs (−, +, −), reproducing the compiled basis on all 516 and 864
  records, with the multi-axis populations (53, 179) pinned so the rival-order
  control (zyx, which still fails 20 and 95 of them) cannot go vacuous.** The
  12-map probe behind it closed 3,545/3,545 with the nearest rival at 2,070.
  Section 4b's refusals each sit beside a live baseline built from a synthetic
  pair whose Bloated half the test assembles out of `struct.pack`. Also: `detile`
  checked cell-for-cell against
  `terrain.Terrain.index`, a different implementation in a module this rung does not
  own; a sha256 manifest whose negative control flips one mantissa bit of one height
  and must be caught (and the same control on one byte of the props sidecar); and a
  refusal that keeps derived ArenaNet bytes out of the
  working tree — which shipped broken, one `dirname` short, and wrote a 745 KB height
  field into the repo before the test pinned the resolved root.
  Section 6 lost its entry-count gate on 2026-08-13 and the reason is the lesson: it
  skipped whole unless the archive had exactly 177,342 MFT rows "because these row
  constants were measured on it", and it has no row constants -- every row it touches
  comes from `sample_rows`, which selects on `flags == 259` and never on an index. The
  gate could not fail for the reason it was there and did nothing but hide four checks
  and redden the floor on `vault/client/2026-04-30_b174de1f2d8d`, which holds the same
  349 pairs at the same rows with the same crcs. What guards the section is the
  population assertion on the next line -- 349 rows with flags 259 -- which the
  impostor archive of `test_mapfile`'s section 2b reddens at 1.
  **Sections 4c and 8 are rung T4 (2026-08-14), the terrain textures**: the manifest
  (format_version 3) gains a tile→texture table, one row per tile byte naming its
  file id, the MFT's (size, crc) and its PNG under `terrain/` — or the REASON it has
  none, because a table with silent holes cannot be audited. The binding is
  `dep[tile + (1 if tag3b else 0)]` and both halves of the law it rests on are
  REFUSALS the test fires live (dep list too short, too long, tag3b with no extra
  entry, a used tile byte off the table), because the law is MEASURED at 349/349 and
  a map violating it has no honest binding. Section 4c runs the whole thing on a bare
  machine — synthetic ATEX rows behind a fake two-method archive, a hand-packed
  uncompressed DDS for the decode path and a compressed-flagged one for the refusal
  path, the corrupt-a-byte and missing-file negative controls on the PNG digests,
  and a restore that proves the controls measured the corruption rather than the
  fixture. Section 8 exports Kamadan whole — 51 tiles → 51 ATTX images, every
  distinct tile byte in use resolving, checked from the TILES SIDECAR rather than
  the block's claim about itself — plus row 56835, one of the 24 tag3b maps, whose
  extra LEADING dependency is DDS row 0x475C8 and must reach no tile (the corpus's
  8 non-ATTX terrain files are ALL leading entries, 17,089/17,089 tile positions
  being ATTX), and the resolution law over the sampled maps. Sections 0-4c need no
  vault and score 111 against a floor of 185, so a vault-less run goes red. ~74 s,
  MEASURED on `dat_study` 2026-08-14),
  `toolkit/mapdata/test_blenderimport.py` (the Blender half: it runs
  `tools/blender/import_gwmap.py` headless as a SUBPROCESS — the test is stdlib-only
  and never imports `bpy`, which is why the importer may live outside `toolkit/` —
  and checks the mesh Blender actually built. 213,921 vertices and 212,992 quads for
  Pre-Searing, every face a quad, every normal +Z, and the bounding box equal to the
  Map Parameters rect to the bit. The oracle is the props chunk read by the test's
  own walker — the TERRAIN path through both tools never touches it, which since
  2026-08-13 is the honest form of "a chunk neither tool reads", both tools now
  handling props as a separate sidecar/collection sharing nothing with the height
  path: prop `z` looked up in Blender's own vertex buffer **by world coordinate
  rather than
  by lattice index**, scoring 0.7338 — identical to `test_mapexport`'s figure for the
  same map, which was the stated prediction — against 0.078 y-flip and 0.139 x-flip.
  Looking up by index is what the first version did, and an upside-down-map sabotage
  scored the baseline unchanged. The oracle's LIMIT is measured and stated too: a
  one-cell shift of the whole height field scores 0.7477/0.6806/0.7292/0.6944, i.e.
  inside the spread, so it resolves layout and not registration and must not be
  quoted as doing the latter. Three controls: a changed pitch must move the bbox
  off the rect (which is why the importer reads the pitch from the file instead of
  hard-coding the measured 96.0), a reversed row order must change the z digest while
  leaving the bbox identical, and a corrupted sidecar must make Blender exit 66 and
  write nothing — 66 rather than "non-zero" because `blender --background --python`
  exits 0 even when the script raises unless `--python-exit-code` is passed. No
  Blender means every section skips and the run goes red, the way `test_keytap.py`
  does off Windows; `RURIK_BLENDER` and `--blender` override the install path, and
  section 0 is that selector — an explicit path that does not exist is REFUSED
  rather than fallen through to the known install, because it fell through, and a
  run that asked for one Blender measured another and printed green.
  **Section 4 (rung M4, 2026-08-13) is REAL prop geometry**: a `.gwmodel`
  family beside the map export gives each prop ArenaNet's own mesh, instanced
  one datablock per model file id — 664 real props over **152** datablocks on
  Pre-Searing, none shared across different ids, with the 200 whose model does
  not decode keeping their proxy so no placement is lost. **THE Z SIGN IS THE
  MEASUREMENT**: prop geometry must reach ABOVE the terrain under it, scored
  off the objects Blender actually built — **0.961 against 0.032** for a
  control that reflects each mesh about its own placement point (and 73.2%/
  83.3% vs 23.8%/6.5% measured the other way, from the exports, before any of
  this was built). A null that shuffles which model a prop points at does NOT
  collapse, and the file says so rather than burying it — the metric tests the
  SIGN, not identity, and the sign flip is what has to fail. Section 3 passes
  `--proxies-only` EXPLICITLY, because it was getting proxies only from the
  absence of a `models/` directory beside its temp export, so exporting one
  there would have turned the section into a test of something else with every
  check green. **And since
  2026-08-13 the props sidecar reaches Blender as PROXY objects** — outlined props
  as their measured footprint prisms, the rest as cylinders at the measured
  placement radius, never ArenaNet geometry, the proxy height being the one
  invented (display-only) number — checked at all 864 Pre-Searing proxies sitting
  at (x, y, −z) exactly, the proxy OBJECTS scoring the chunk's own 0.7338 against
  the mesh, the outlined population pinned at 34, and a `--no-props` control that
  must import the terrain alone.
  **Sections 2b and 5 are rung T5 (2026-08-14), the ground's material**: one Blender
  material per distinct terrain texture, `material_index` per face from the
  `gw_tile` attribute through the manifest's tile table, and T3's measured UV
  window (the inner 111×111 texels of quadrant 0, corners inset 8.5). The criterion
  is against the SIDECAR rather than the importer's own loop — every tile's slot
  material must be the image the manifest names for that tile byte, and every
  FACE's index, recomputed outside Blender from tiles.u8 through the dump's slot
  table, must sha256-match what Blender read back off its own built polygons: all
  212,992 Pre-Searing faces, not a sample. Section 2b runs it vault-less on
  synthetic textures with one tile whose file id deliberately resolves to nothing,
  which must get its OWN named empty slot rather than falling through to slot 0 —
  the prop-material fall-through defect, refused on the ground — and
  `--no-terrain-textures` is the control on both the synthetic and the real map.
  One check per section also pins the mask's CHANNEL_PACKED alpha mode and
  all-faces-smooth shading, read back off the built scene — the first human look
  at the delivered .blend found Blender premultiplying the un-wired blend mask
  into the Color output, a dark band over clean ground colour on every cell.
  Sections 0-2b need no vault and score 54 against a floor of 110, so a vault-less
  run goes red. ~61 s),
  `toolkit/mapdata/test_blenderroundtrip.py` (the AUTHORING direction, and the
  first thing in this arc to come OUT of Blender: an interchange imported, saved
  to a `.blend`, and exported back by a SEPARATE Blender process — two processes,
  because a round trip inside one scene proves the functions are inverses and
  says nothing about whether the `.blend` carried anything. **ArenaNet's own
  212,992 heights, 212,992 tile bytes and 212,992 shade bytes come back
  byte-identical**, and that headline is the WEAK half: a memcpy sabotage — the
  importer stashing the height array in its stamp and the exporter replaying it
  — keeps all SIX byte-identity checks green, including the retail ones, and is
  caught by exactly two. Those two are section 2, which SCULPTS one vertex in
  Blender by a literal +250.0 and requires exactly that cell to move by exactly
  −250.0 in the stored convention, because the importer negates in and the
  exporter negates back; a run without it is satisfied by a tool that understands
  nothing. Three refusals, each a thing a height field cannot express: a vertex
  dragged 40 units in x leaves its column and the lattice stops filling, a vertex
  nudged 0.5 units STAYS in its column and is caught only by the residual against
  the lattice, and a far-edge vertex holds a value the file has nowhere to put.
  The first two are one defect at two magnitudes and a version with only the
  40-unit case passes a sabotage that deletes the residual check — measured, not
  assumed. The far edge is checked from BOTH its causes, because the count is
  named for its effect: sculpting the edge leaves the stored heights IDENTICAL
  (the drop happened), while sculpting the last REAL column beside it moves that
  cell and puts the same edge vertex on the same list, and an exporter conflating
  them reports the wrong thing about a legitimate edit. It also pins that an
  IDENTITY `matrix_world` multiply is not a bitwise no-op on SIGNED ZERO —
  `-0.0 * 1.0 + 0.0` is `+0.0`, so one cell of 6,144 came back `00000080` for
  ArenaNet's `00000000`, numerically equal and bytewise not, which is exactly what
  a tolerance would have hidden; the comparison reports byte-differs and
  value-differs separately so the next one names itself. Section 4 authors a mesh
  in Blender from NOTHING, with no stamp to carry, and `mapbuild` assembles it
  into a map file that passes all 17 of the client's open-time gates. **And since
  2026-08-13 the exporter picks the terrain by IDENTITY, not census**: a props
  import fills the scene with proxy objects, so "more than one mesh" stopped
  being proof of ambiguity — the terrain is the one mesh carrying the importer's
  stamp, which proxies never do, and the old two-mesh refusal split into an
  unstamped-intruder POSITIVE control (the stamp picks the terrain, the dims pin
  it) and a two-STAMPED-meshes refusal, since a duplicated terrain copies its
  stamp and is genuine ambiguity. **And since 2026-08-14 PROPS ROUND-TRIP** (section 6): a
  retail map's 864 prop placements go into Blender and come back out as a
  props sidecar -- 864/864 on model index, flags and outline, positions
  EXACT and bases to 3.6e-07. That identity is the WEAK half, so the section
  EDITS two different props and requires exactly those two records to move:
  one translated by (+1000, -500, +250) in Blender, which must land as
  (+1000, -500, **-250**) stored -- the terrain's negation, now measured on a
  prop -- and a DIFFERENT one turned 90 degrees about its OWN origin, which
  must move its basis by 1.35 and its position by zero. Two props rather than
  one, because an exporter reading location but not rotation would satisfy a
  single-prop check. The rotation is about the object's own origin on purpose:
  the world-origin form displaced the prop by (-20344, +15804) and would have
  made the position check ambiguous. **It found a real defect**: an OUTLINE
  proxy is imported UNROTATED by design, so deriving its basis from an
  identity matrix wrote an identity basis over the real one -- 31 of 864 props
  silently flattened -- and the stamp now wins for exactly that case, the one
  place in the exporter where it does. An EMPTY prop list writes no sidecar,
  because a mesh authored from nothing has no prop layer and an empty one is a
  different claim; the check that reddened when it did is section 4's "only a
  heights sidecar is written". Sections 0-4
  need no vault and score 67 against a floor of 94. ~62 s),
  `toolkit/mapdata/test_mapfile.py` (the WHOLE-FILE codec: a retail `ffna` map
  payload decoded to a typed container and re-encoded byte-identically — **349 of
  349 Bloated and 349 of 349 Stripped** under `--all`, 6 of each by default. The
  count is only worth its exit code because the chunk table's `size` is RE-DERIVED
  from the encoded payload and never stored: a codec that replayed a stored size
  round-trips every file it can walk, including the seventeen chunk kinds this one
  carries opaquely, and would print 698 of 698 while being a memcpy. So the control
  that matters mutates a decoded chunk IN PLACE until its payload changes length and
  requires the emitted size field to move with it — mutating in place is the whole
  design, because the first version replaced the chunk object and a sabotaged
  stored-size encoder passed it 22 checks to 0. Both stored-size shapes go red now,
  as do a dict-keyed encoder that loses file order and a tolerant chunk walk. The
  Stripped stage is measured, not assumed: its terrain chunk `0x10000002` is a
  different encoding and must come back CARRIED. Sections 1-2 build a whole map file
  out of nothing and need no vault; the run reports the reconstructed/carried byte
  split, which is 34.92% / 65.07% and is the honest half of the result.
  **And since 2026-08-13 the pinned sections are gated on
  IDENTITY rather than on a census, which is what let a second archive in.** The old
  gate compared the whole archive's MFT row count to 177,342 and skipped 13 checks
  otherwise, reasoning that "file ids travel, row indices do not" -- right in general
  and wrong in both directions here. TOO STRICT: `vault/client/2026-04-30_b174de1f2d8d`
  (177,311 rows) holds the same 349 map heads at the same indices with the same sizes
  AND the same crcs, head and partner, **349 of 349**, and its pinned pair is
  byte-for-byte the same file -- MEASURED 2026-08-13, and `vault/run-live` agrees as a
  third. TOO LOOSE: a row count is a fact about the COPY, so any tampered archive with
  177,342 rows passed -- relocation, recycle, rewrite and sibling relink all leave it
  alone. `resolve_pinned` now looks the map up by FILE ID (`test_pathchunk`'s pattern)
  and requires the row it lands on to carry the MFT's own measured (stored size, crc);
  the row is printed, never required. The PARTNER is deliberately NOT in the gate --
  the first version verified both rows there and made section 3's partner check
  unfalsifiable, so partner identity is now a claim the archive can refute. Section 2b
  is the control and needs no vault: it BUILDS an impostor archive carrying the old
  constant's row count and a different file at the pinned id, requires the new gate to
  REFUSE it while the retired rule -- reproduced inline as a live function -- ACCEPTS
  it, then requires the opposite on a 177,311-row copy holding the right file, so the
  two disagree in both directions from two live answers rather than from prose. Four
  more refusals sit under it (an unbound id, an id landing on a non-head, a
  non-archive, a truncated archive), and running the impostor END TO END is what found
  section 7's KeyError -- a sweep where every file failed left the census empty and
  reported a red run as a traceback with no verdict and no ledger. Default is 59 checks
  against a floor of 59, 34 of them on a bare machine (was 50/25). `--all` is
  ~13 minutes, and **has not yet been run against the second archive** -- the gate
  makes the 698-file second witness reachable, it does not make it measured),
  `toolkit/mapdata/test_mapbuild.py` (the AUTHORING direction: a whole Bloated map
  assembled from typed parameters -- dims, a height field, a tile table, a navmesh --
  and row 46196 coming back BYTE-IDENTICAL, 8,471 B. That equality is the weaker half
  and never appears without the census beside it: **7,814 B generated (92.24%), 657 B
  carried (7.76%)**, every carried chunk NAMED, asserted against floors rather than
  printed -- plus the stricter 5,502 B (64.95%) once the terrain arrays that reach the
  encoder as opaque `bytes` are subtracted. A memcpy sabotage keeps that headline
  GREEN and is caught by ten other checks: the controls rebuild the same row with ONE
  parameter changed and require chunk 0x20000002 to move and nothing else, then
  require 0x2000000C alone to move when the content id changes, then grow the tile
  table and require the file, the terrain payload and the chunk table's size field to
  grow with it. **Provenance is the design here.** FINDINGS 14's five mandatory chunks
  are ArenaNet constants (232 B per map) read from the owner's archive AT RUN TIME --
  the builder refuses (`NoConstants`) without one, section 2 reads `mapbuild.py`'s own
  syntax tree and requires no bytes literal over two bytes in it, section 7 takes the
  five payloads it just read from the archive and looks for them in BOTH source files
  (raw, hex, spaced hex, `\x` escapes -- which is how a draft that quoted the Water
  bytes in a docstring was caught, invisible to the syntax-tree scan because it was
  prose), and sections 0-3 run the whole builder on PLACEHOLDER zero constants of our
  own, so they need no vault.
  It also corrects FINDINGS 14: **one of the five is not a constant.** 0x20000006
  (Water) takes two values, so the builder VERIFIES each borrowed constant against the
  map it is rebuilding and NAMES any substitution -- and the sabotage that trusts the
  donor still round-trips row 46196 while breaking row 26209, which is the shape of a
  bug that ships. `gates()` reproduces the loader's open-time rules and its control is
  that ArenaNet's own row 46196 passes all 17 before anything we built is judged; five
  rules are then broken on purpose and must go red ALONE. Section 2 also refuses
  `--out` into EVERY checkout of this repo rather than the one the file sits in: a
  git worktree's repo root is not the main checkout's, and until `working_tree_roots`
  existed a build written to `<main>/toolkit/` was allowed straight into version
  control. Sections 0-3 score 46 against a floor of 98, so a vault-less run goes
  red. ~12 s),
  `toolkit/authsrv/test_spawn_burst.py` (the nine messages that put a body in the
  world, and since 2026-08-15 **the one that killed the client**. Section 4 used to
  read `0x003A`'s payload at a stride of 3 — `triples[0::3]` for the ids,
  `[1::3]` for the ranks — which is our builder's layout checked against itself,
  and it was green while every session ended in `Assertion: level <
  arrsize(s_attribPoints)` / `CharData.cpp(202)`. The wire is COLUMN-MAJOR: the
  handler computes `n = count / 3` and slices ONE flat array at `n` and `2n`, so
  interleaving `(id, rank, rank)` puts attribute IDS in the rank column, and ids
  run to 50 against an `arrsize` of 13. The section now slices the payload **the
  client's way** and checks each column, including that every value the client
  will index `s_attribPoints` with is 0..12. Its last check is a CONTROL and is
  the one that matters: it rebuilds the interleaved layout, slices it the same
  way, and REQUIRES an out-of-range rank to fall out — printing
  `column2=[9, 19, 6, 6, 20]`, the 19 being exactly what the client asserted on,
  at exactly the index it asserted at. Without it the ten checks above are ours
  agreeing with ourselves and would pass on any self-consistent layout. Floor
  34 -> 38. No socket, no client. ~1 s),
  `toolkit/authsrv/test_movement_fidelity.py`,
  `toolkit/authsrv/test_agentlife.py` (WORLD_REMOVE_AGENT and its two refusals,
  that an unframeable opcode stops the framer instead of being framed past, and
  the whole enemy: a hostile that swings back, chases, turns to face you and
  casts — each phase checked as a SHAPE the wire could contradict rather than as
  a message count. Its last section is the one that earned the entry:
  **every combat constant is asserted against a LITERAL written in the test
  file.** That exists because on 2026-08-11 the monster-AI dive sabotaged them
  one at a time and **twelve of fourteen could be set to a wrong value with all
  125 checks green** — `ENEMY_MELEE_RANGE` 150→400, `AGGRO_RANGE` 1200→1100,
  `SWING_WINDUP` 0.899→0.2, all PASS. Only `ENEMY_TURN_RATE` reddened, and it is
  the only constant in the set corroborated to the bit. Not a coverage accident
  but a shape: every other section computed its expectation *from* the symbol
  under test, so the symbol was free to move and the test moved with it. **A
  symbol appearing in a test file is not a check.** The same section reads
  `skilltable.py`'s live table off build 38797 and cross-checks the enemy's bar —
  which is how `authsrv.py`'s claim that all four bar skills are non-elite was
  found false (276 is elite), the comment having been the only witness.
  **And since 2026-08-13 the plan-less probe run, which is the section that
  stopped this file's COLOUR from tracking mutable vault state.** Every check in
  `section_probe_encoding` built its own `Step`; the PRODUCER — `_smsgsweep_steps`
  — was checked by nothing and reads `vault/probes/smsgsweep-plan.json`, which any
  sweep in any session rewrites. So the red of 2026-08-13 was not a defect at all:
  the all-zero sweep FINISHED, `remaining` went to 0, and the refusal step the
  builder returns for an empty plan could not encode. Seven checks now pin both
  answers through a temp file with `plan_path` monkeypatched — no vault, no
  socket, no client. **The half still broken when that section was written is the
  RUNTIME one**: `Step.sends=False` was added for `check_encodable`, and
  `authsrv.run_probe` — the consumer that puts bytes on a socket — was not taught
  about it, so it sent the refusal and relied on the codec to raise. That fails in
  both directions, which is why there are TWO `send` fixtures: a strict one
  (refuses an empty payload the way the codec does) catches the refusal being
  printed as `SEND FAILED … that is a result too — record it` with the `watch`
  line skipped past, and a permissive one (the refusal whose opcode the degenerate
  encoder can fill) catches the packet going on the wire underneath the words
  "nothing was sent". Four sabotages were BUILT AND RUN and all four redden
  different sets (2, 5, 2 and 1) — and the one that earns the POSITIVE CONTROL is
  `run_probe` skipping EVERY step, which reddens the two control checks and
  nothing else, so without them a sweep that fires no packets and prints "probe
  complete" would be indistinguishable from the fix. The flag stays DECLARED and
  never an `if not step.values` shape test, because a malformed valueless step
  that DOES claim to send is exactly what the encoder check exists to catch and
  the two are identical in shape. Floor 214 against a green 223),
  `toolkit/authsrv/test_dispatch.py` (D9(a): that a schema-KNOWN c2s opcode with
  no handler is now VISIBLE rather than falling off the end of the chain --
  19 opcodes and 9.8% of our corpus did, and worse against live shapes. The
  behaviour half is the design, not the `else`: first occurrence prints, the
  rest are counted, the tally lands at disconnect, and a labelled run
  suppresses the ECHO while still COUNTING -- which is the one that would
  silently disable the fix in exactly the sessions an operator is watching.
  The structural half asks the SYNTAX TREE whether both chains end in a real
  `else`, because an `elif` is a lone `If` inside `orelse` and a text grep
  cannot tell them apart -- `test_cmsgnames.py` had a grep that asserted its
  arm's formatting and went red on a line break. Four negative controls must
  go red, including an `elif` in the else's place and an `else` that calls
  something else, since `else: pass` satisfies "has an else" while restoring
  the exact silence D9(a) is about. **And since 2026-08-13 it checks the OTHER half
  of D9(a), which is that making a drop VISIBLE is not the same as not dropping it**:
  2,858 of 17,770 framed c2s (16.1%) reached that `else` over 425 loopback
  connections, and FOUR of them were opcodes `overrides.json` had already NAMED --
  `0x0039` INTERACT (3.2% of ArenaNet's own live c2s and NO arm at all, while
  `0x0033`, which HAS one, has been sent ZERO times in all 17,770 since 2026-08-06
  and is kept anyway because nobody knows why it stopped), `0x0092`
  MISSION_MASK_REPORT (803), `0x00C1` TARGET_SELECT (363) and `0x0040` ROTATE_PLAYER
  (108). It is 8.9% after the arms. The tripwire that would have caught the class is
  ASYMMETRIC on purpose: an arm on an opcode the SCHEMA does not know is a hard
  failure, since the framer refuses the message and the arm is dead code that reads
  as coverage; while a NAMED opcode with no arm is a REPORT against
  `DROPPED_ON_PURPOSE`, seven rows each carrying its reason (the seventh is
  `0x0014` QUEST_SET_ACTIVE, named and dropped on the same day by rung Q1 --
  the check went red on the naming commit before the row landed, which is the
  tripwire working rather than a gap) -- 194 layouts against
  sixteen arms means demanding an arm per layout would be a permanently red test that
  gets deleted, but a name costs somebody a binary read or a narrated live session and
  losing one silently is the defect. The allowlist is checked in BOTH directions,
  because a row for an opcode that IS handled is inert today and silently re-permits
  the drop the day the arm goes. Existence and EFFECT are asked apart:
  `elif opcode == X: pass` satisfies "0x00C1 has an arm" and drops the message just as
  completely -- section 5's `else: pass` lesson one level down -- so a separate check
  requires each new arm's OWN body to assign into `state`. Seven sabotages were BUILT
  AND RUN and all seven redden, three of them reddening exactly ONE check each. The
  one behavioural check is on the trap that has now cost this project three times:
  `0x0040`'s two fields are `dword` and hold float32, so the +inf sentinel reads as
  2,139,095,040 if you take the number instead of the bits. No vault, no socket, no
  client -- deliberately, and it constrains what may be asserted: the capture tree is
  append-only and GROWS WHILE THE TEST RUNS (`0x00C1` went 363 to 429 between two
  reads minutes apart), so every corpus count above is dated prose and not one of them
  is an assertion. 45 checks, ~1 s),
  `toolkit/authsrv/test_population.py` (what LIVES in an authored area -- the
  `content/world.toml` spawn rows carrying `area = NAME`, served by
  `authsrv --area`. R5's criterion is "a new zone in TOML, hot-reloaded,
  walked", and the toolkit could author a zone's GROUND long before anything
  standing on it. **It could not have been written before rung (I)**: its
  load-bearing rule is that a body goes out only where the navmesh says there is
  ground, and until 2026-08-13 the server on an authored map held either
  ArenaNet's geometry for that map id or no mesh at all (FINDINGS 59), so the
  check would have been measuring the wrong map or nothing. It matters because
  an authored area is SPARSE -- the sculpt map is **1.2% walkable by area**, 13
  trapezoids over 64x64, so a coordinate picked by eye is ground about one time
  in eighty, and the shipped positions are trapezoid centres read out of the
  mesh the client itself compiled. The set rules are checked at STARTUP because
  their cost is a wasted client run: `create_agent_world` already refuses a
  duplicate agent id, but by then half the population is in the world. The
  DEFINITION rule is the one with a shape -- sharing an index is ALLOWED within
  one npc template (a definition is per-instance and outlives its agents;
  ArenaNet sends one for 140 re-creates of one worm) and REFUSED across two,
  since the array is a raw index and the second row would silently overwrite the
  first. Placement nudges and REPORTS the distance, or refuses; it never
  silently invents, because a body standing where the server's own collision
  says nothing exists makes everything downstream reason about it wrongly.
  Seven sabotages were BUILT AND RUN and all seven redden, but the two that
  earn the file are the ones that did NOT at first. **One CRASHED instead**:
  refusing any shared definition makes the real rows unloadable, and the
  positive controls called `area_population` directly, so the run died with a
  bare traceback, no verdict banner and no ledger -- the same trap
  `vaultpath.require_dir` set for `test_stripbuild`, and it reads as a broken
  test rather than a caught defect. Every call goes through `accepts()` now.
  **One passed GREEN**: the bounded-search check computed its probe point as
  `-(PLACE_SEARCH_RADIUS + 2*PLACE_SEARCH_STEP)`, so raising the radius to
  100,000 moved the probe with it -- a check that cannot fail, the same defect
  `test_agentlife` records where twelve of fourteen combat constants could be
  set wrong with all 125 checks green. Both constants are now asserted against
  LITERALS written in the test file and the probe distance is a literal too.
  No vault, no socket, no client: the mesh is `pathchunk.minimal()`, authored
  from nothing. Section 4 (2026-08-16, Isle rung 5 gap 2): a vault-emitted
  `def_NNNN` row — which deliberately carries NO name — spawns end to end
  through `spawn_population` with the label defaulting to the npc key, and
  every emitted message encodes through the real codec; the fixture asserts
  the row truly lacks a name so the check can tell the fix from a smuggled
  fixture. 43 checks, ~2 s),
  `toolkit/authsrv/test_ping.py` (the `0x000C`→`0x0009`→`0x000D` round trip that
  drives the client's net graph, and the three places a plausible
  implementation quietly LIES: sending a second request while one is
  outstanding would move the start time and make a bad link report a SHORTER
  round trip — the one direction a latency meter must not fail in; answering an
  unprompted reply would put an invented number on the one readout an operator
  reads as measured, and 0 of 79 in the corpus are unprompted; and sending over
  the client's own 5000 ms cutoff produces a message it DISCARDS at
  `0x0048DA40` before the shift register, so the graph never moves and the
  feature looks dead rather than wrong. Section 8 is not about the feature at
  all — it asserts STRUCTURALLY that `world_tick`, which owns the 5 s timer,
  starts only when `TAPE_EVENTS is None`, because a tape run requires zero
  messages of our own on the channel and `PLAN.md` §3.4 records a run whose
  client assert was un-attributable because our ticker talked over ArenaNet's
  recording. Its control is that guard REVERSED, which is one character from
  correct and would contaminate every tape run. No vault, no socket, no client),
  `toolkit/authsrv/test_tape.py` (R1.5's tape loader: the events ARE the recorded
  stream whole and in order, and a tape whose wire bytes do not account for the
  plaintext -- or that came from our own server -- is refused. Section 6 is the
  straddle: a tape event is a TCP segment, so it builds a capture that splits one
  message across two of them and requires `decode_all` to recover all three while the
  per-EVENT idiom it replaced loses two and INVENTS two more. That idiom cost the
  corpus 4,251 of 22,137 messages and invented 117 (studies/tape T18). It needs no
  vault -- a segmentation defect is not a property of any one capture),
  `toolkit/authsrv/test_behaviourrun.py` (the LIVE behaviour run's analyser and its
  operator script, against a session the test builds out of tuples -- no vault, no
  socket, no client. It labels the MONSTER's behaviour where `labelrun` labels the
  PLAYER's input, so its three refusals are the file: a subject that MOVED between its
  create and its first reaction comes back UNRESOLVED and `separation` returns None,
  because estimating that produced four numbers of which two were wrong by 481 and
  1,594 units; no summary pools across model ids, because pooling three creature models
  is what produced the refuted "269-1594 units" band; and the CONTROL predicate is on
  the CLIENT half only -- its decisive check is a control window carrying 200 server
  messages that must still pass, since a no-traffic predicate reddens in every control
  window of every live capture ever taken. Section 2 pins `labelrun`'s own defect from
  the other side: a mark written a beat LATE loses its step's first message AND steals
  the next step's, asserted on CONTENTS because both windows hold two messages and a
  count comparison could not fail for the right reason -- which was the first version.
  Section 8 requires `narrate()` to write the MARK file BEFORE printing the prompt, and
  greps the analyser for `SendInput`/`keybd_event`/`hold_key`/`click`: the driver sends
  no keystrokes and no clicks, and that is the rule that protects the account),
  `toolkit/authsrv/test_labelrun.py` (the labelled input run, which names GAME_CMSG
  opcodes from what a human was told to do: a message lands in exactly one step's
  window, instance-load traffic is never folded into step 1, and a dirty idle CONTROL
  is reported and exits non-zero rather than letting a misattributed opcode be named),
  `toolkit/authsrv/test_burrow.py` (burrowing, in two halves kept apart: ArenaNet's own
  bytes re-measured from the capture — 140 worm re-creations, ONE burst shape, the two
  2.00 s transition windows — and our own cycle driven with a fake `send`. It exists
  because the study doc was wrong: T3 said burrowing "runs entirely through the two
  opcodes we already implement" and it is five messages, so a test that asserted the
  doc would have locked the error in. Its capture half decodes the tape WHOLE via
  `tape.decode_all` and asserts the byte accounting first, so every count beneath it is
  of all 3,604 messages rather than the 3,500 the per-event idiom read),
  `toolkit/authsrv/test_npcdefs.py` (the capture→content compiler: **126 of 126**
  NPC definitions rebuild BYTE-IDENTICALLY from the extractor's own typed rows —
  rebuilt field by field, never replayed, so a compiler that stored the blob prints
  the same number and cannot pass. Its real check is the interval join: a property
  message belongs to the create IN EFFECT AT ITS TIMESTAMP, because agent ids are
  recycled, and agent 38 at t=18.169 joins to definition 1434 `mon1` while
  last-create-wins gives 1343 `anim` — one of the FIVE NPC health readings in
  existence, wrong, and green on 99.8% of creates. **The first version of this test
  did not catch that**, because the aggregate `{1346: 96, 1434: 8, 1442: 40}` is
  UNCHANGED under the naive join: agent 43 in the other capture observes 1434 = 8
  independently. The redundancy that makes the finding strong is what made the check
  blind. What catches it is the per-definition event counts plus the rule that no
  non-hostile definition may carry a health reading. Three sabotages run, three fail —
  the third by `read()` refusing and naming both speeds rather than averaging. Also:
  six definitions carry an EncString word in the UTF-16 surrogate range and were
  **unsendable by this server until the `string16` fix**. Since 2026-08-16 (Isle
  rung 5) the pins select the three captures BY NAME and the test proves a
  synthetic fourth keyed capture cannot move them — built into the vault and
  removed in a finally — plus the mode plumbing: base+reforged captures refuse
  to pool, a `--mode` contradicting a manifest is refused, and a recorded mode
  is used with no flag at all),
  `toolkit/authsrv/test_agentroster.py` (the per-agent roster reader —
  `studies/isle/PLAN.md` rung 1: every WORLD_CREATE_AGENT **with its coordinates**,
  partitioned by class tag before any masking, because field 2's low 16 bits are a
  definition index ONLY for the NPC class. The sabotage is measured both ways: 331
  player creates masked anyway produce **0 collisions** with declared definitions and
  **72 phantom slots** no 0x0056 ever declared — so an unconditional mask INVENTS
  types rather than corrupting real ones, which is worse because nothing downstream
  can notice. Pins the cross-session station that makes an Isle roster a table rather
  than a session log: slot 1470 / model 116698 / pos (8436, 4819) byte-identical in
  two live sessions THREE DAYS APART, and map 164's whole outpost joining 6/0/0. Also
  the `tuple(v[3:5])` regression: a synthetic create carries decoy values at fields
  3/4 that would read as a plausible position, so decoding the wrong slots cannot
  come back green. Needs `vault/captures/live/`; without it, 2 of a floor of 27 run
  and the floor takes it red),
  `toolkit/authsrv/test_smsgsweep.py` (the loopback opcode sweep's READOUT, against
  captures the test builds out of dicts -- no vault for the scoring half, no socket, no
  client, because a scoring defect is not a property of any one capture. It is mostly
  negative controls, because the 2026-08-12 pilot's four defects each printed a
  CONFIDENT NUMBER rather than an error and three printed the wrong one: the analyser
  read s2c `frame` events where our sends are `sent` events, so it found zero stimuli in
  a run that sent twelve and reported "nothing happened"; the first packet went out
  3.66 s in, INSIDE the client's own instance-load traffic, and a c2s 0x0000 arriving
  5 ms later was scored a reply; `ConnectionResetError` after 0x000B was reported as a
  crash when the session report's own endpoint table says the client lived another 42 s,
  with no assert and no fatal-error dialog -- the final screenshot is a live client on a
  loading screen; and 0x000B is one of the ten opcodes with NO receive-table entry, which
  the plan should never have held. **The fence is the client's own PROOF OF LIFE, not the
  socket, and that is the section worth reading.** A Guild Wars assert leaves the process
  ALIVE behind a modal dialog with its message pump stopped and its socket open: on the
  first full run the client stopped answering at t=17.16 and the reset did not arrive
  until t=48.77, so a socket fence scored **78 opcodes SILENT against a client that was
  showing a crash dialog** and wrote all 90 into the ledger. An opcode is now scored only
  if a c2s message arrived AFTER it, the run ending belongs to a WINDOW rather than to
  one opcode (blaming the last one named 0x00A9 when the assert was near 0x0012), and
  `--only` bisects that window. The cost is stated as its own check: the last ~5 s of
  every run has no proof and is retried. Each defect is pinned by reproducing the broken
  version inline and requiring it to differ. The
  control window is the design: the quiet seconds before the first send measure what the
  client says UNPROMPTED in this session, so the inherited floor {0x0008, 0x0009} --
  measured on a PARKED client -- is corroborated rather than trusted, and a reply on an
  opcode the window also produced is CONTESTED rather than counted. Section 8 rebuilds
  the sweep's DENOMINATOR from the tapes rather than from a file somebody made once:
  **155 opcodes over 12 live connections, and 324 remaining**. Its control is the defect
  that was made writing it -- filtering channels by `:6112` cut the corpus to 52 and said
  so without complaint, because ArenaNet serves the GAME channel on port 80 in 10 of the
  12 canon connections.
  **Section 9 (2026-08-13) is the REGIME**, and it exists because a row was a
  measurement of two things while its key named one. An all-zero send and an
  `--encstring` send are different experiments -- 0x0033, 0x009E, 0x00B9 and 0x00C0 each
  crash the client on an empty payload and go SILENT carrying a real encoded string, two
  of them naming a guard that is ABOUT the string -- and `record` is first-write-wins, so
  nine runs that measured the clearance printed `recorded 0` and changed nothing. Only a
  key with a regime in it could hold both, which is why re-running the recorder was never
  going to fix it. **The axis is the PAYLOAD, not the flag**, read out of the capture's
  own `plain` bytes: 87 opcodes carry a `string16`, only **86** can be filled -- 0x019D's
  sits behind a `nested_struct`, which `degenerate` stops at, so an `--encstring` run of
  it is an ALLZERO experiment; the field-scan version called it encstring and this
  section's predictor-versus-wire check (974 comparisons, two code paths sharing nothing)
  caught it on its first run -- and the remaining 401 go out byte-identically whatever the
  flag says, so a flag-keyed ledger would file 401 duplicate rows for one experiment. The
  load-bearing check is the SABOTAGE: the regime-less `record` is reproduced inline, run
  on the same two fixtures, and required to lose one of the two results, on the TABLE path
  and again on the CRASH path -- the four rows this item is about were written by the
  crash branch, so a regime on the table rows alone would have fixed nothing. Five module
  sabotages were built and run and all five redden (7, 1, 12, 1 and 1 check). Also: an
  old-format row loads, is readable, and is named UNMIGRATED rather than read as
  all-zero; `migrate` loses NO row, REFUSES a key collision instead of letting one win,
  and writes `unknown` EXPLICITLY where a row's capture is a note rather than a file (10
  of the 334 -- the hand-attributed table-less pass, and a refusal branch that fires ten
  times on real data is why it is there); and the write is `os.replace` with a
  stale-stamp refusal, with the positive control that a current stamp is allowed, because
  the ledger is a live vault artifact another session reads while a sweep is running.
  Floor 99, was 64; sections 0 and 2-7 and 9 need no vault and score 94).
  **Section 10 (2026-08-13) is the one that is not about smsgsweep at all**, and it exists
  because every other section runs INSIDE the module: `plan()` resolves the `--set`
  overrides, `apply_set` applies them, `encodable()` encodes them, so the module agreed
  with itself perfectly while **`--set` was putting the DEGENERATE payload on the wire**.
  The consumer is `probes._smsgsweep_steps`, and the regression is the shape worth
  remembering -- `p.get("set")` was CORRECT when `--set` shipped and became a no-op an
  hour later when the qualified `--set 0x0083:2=1` form moved the overrides per ROW; one
  side of a two-module contract moved and the other was not touched, so nothing errored
  and nothing downstream could tell: the plan file is right, the capture is right, and
  `record` scores the capture, so a `--set` run reads as a measurement of the all-zero
  payload wearing the label of the experiment. **Five of `studies/smsgsweep/FINDINGS.md`
  §5c's gate experiments were retracted for it**, settled from the server's own `plain=`
  hexdumps -- the bytes were recorded all along, nothing was reading them. Note what
  section 9 above could NOT do: it checks `planned_regime` against smsgsweep's own
  encoder, so it agrees with the module and never reaches the probe. The section joins
  the two halves and goes through a REAL FILE, which is not decoration -- five sabotages
  were BUILT AND RUN (3, 1, 2, 3 red; the `rows[0]`-for-every-row one reddens the per-row
  check ALONE) and the fifth breaks the TEST instead of the source: the same missing
  `int(k)` cast, handed an in-memory plan with int keys, is invisible and **every check
  PASSES** while the first real run raises TypeError. The plan reaches the probe as JSON,
  so the fixture must too. That sabotage also found a defect in the section's own draft --
  an empty step list was indexed at `got[0]`, so a caught defect printed a bare traceback
  and no verdict banner. Its 8 checks need no vault, no socket and no client, but they DO
  need `content.load()` to succeed, since the builder lives in `probes.py`),
  Section 7b covers `sweeploop.py`, the unattended driver: its stop conditions are a
  PURE function so they can be checked without a client, and its control is that ONE
  barren round must NOT stop -- a single unlocalised crash is normal, and stopping at one
  would end most sweeps early. One check asks the SYNTAX TREE whether the loop
  imports the cage or launches anything itself, because the grep version of that check
  went red on the docstring explaining the rule.
  **And since 2026-08-13 it covers the PLANNER'S EXIT CODE, which the loop discarded.**
  `smsgsweep --plan` exits 2 writing NO plan on all three refusals it had that day, and
  `load_plan()` reads a file out of the vault that cannot tell this round's from the last
  one's --
  so a refusal left the loop launching a real client against a STALE plan and recording
  what it measured under this round's opcodes, silently, since the plan parses and the
  ledger grows. The gate is TWO signals because each covers a hole in the other: the exit
  code, plus whether the plan file MOVED, which is what catches a planner that dies after
  its own checks. The half that needed the most care is the EXEMPTION -- exit 1 is
  "NOTHING TO SEND", which writes an empty plan and is the sweep's only good ending, so a
  blunt `rc != 0` stop would rename completion as breakage, and that control is the one
  the blunt sabotage reddens. **Two controls were VACUOUS in the first version and the
  sabotages are what found it**: the crashed-planner case (Windows returns the exception
  code, which arrives NEGATIVE, so an `rc >= 2` test accepts it) was written with the file
  unmoved, where the freshness half refuses it anyway -- the `rc >= 2` sabotage went 0
  red. Both now pass `moved=True`, and five sabotages redden five different sets. The
  subprocess half points the loop at a planner that exits 2 with a stale plan on disk, and
  asserts the difference between two live answers in one process: `plan_round` hands back
  None while `load_plan()` still answers with the row the old loop would have launched
  against. Last, the ORDER is asked of the syntax tree -- the guard must sit BEFORE the
  launch statement in the round body, with the guard deleted AND the guard moved one past
  the launch as controls, because a client that goes up and is stopped afterwards has
  already measured the wrong opcodes),
  `toolkit/authsrv/test_shotlabel.py` (the SCREEN readout for the 239 SILENT opcodes,
  and the four defects it shipped with. `smsgsweep`'s `SILENT` means *no c2s reply*
  and is blind to anything the client DRAWS, so this joins a run's one send to the
  hold screenshots that bracket it. Every headline it prints is a number a broken
  version also prints, so the file is mostly negative controls and each defect is
  REPRODUCED INLINE -- the passing number is a difference between two live answers.
  **The join is by WALL CLOCK**: the obvious index reading uses the CAPTURE's clock,
  which starts at the server connection and not at the hold, and scored `0x0033`'s
  306x443 Message of the Day panel at **0.00008** because the baseline frame already
  had the window in it (0.05043 joined correctly). **The noise floor is the MEDIAN of
  the idle window**, not the max and not every pre-send pair: the first hold frames
  are a loading screen, which against a world frame is 64% of pixels, and at that
  floor ALL FOUR known positives read QUIET -- and the max fails too once a load
  transition lands inside the window, measured at 81.86% with the flag threshold
  above 100% where nothing can ever be CHANGED. Two pairs is refused, because a
  median of two is their mean. **The stamp is only good to the SECOND**, so a frame
  inside the send's second serves as neither baseline nor after-frame. And it scores
  a STRIP rather than a pair, because `0x00C0`'s floating text fades in ~2 s and at a
  2.3 s cadence lands BETWEEN frames -- one pair scored it 0.190%, below the same
  run's idle noise -- with `sustained` separating a transient from a panel that stays
  and a persistent-effect control that must NOT decay. Section 7 is the one that was
  not in this module at all: `session.Stack._pump` died on a cp1252 console, the
  gamesrv wedged on its next print, the probe sent NOTHING, and the run still
  reported **RUN VERDICT: PASS** -- the only thing still working was the 20 Hz world
  tick, the one send that does not print. Three opcodes were marked done having never
  been sent, so `shotloop` records an opcode only when the run's OWN capture holds its
  send. Section 8 refuses the page into every checkout, with the vault as the positive
  control. No vault, no socket, no client -- the frames are drawn with PIL, which is
  what lets the load-screen and ambiguous-second cases exist at all; without PIL the
  file declares one skip and goes red. 33 checks),
  `toolkit/authsrv/test_rotate.py` (that GAME_CMSG 0x0040 really is ROTATE_PLAYER: the
  client's own assert text and the two ±inf constants are still at their addresses, both
  payload fields are still `dword` and not the `float` they look like, and the finite
  angles agree with atan2 of a nearby heading far past a null model built by shuffling
  the same corpus. Its own first version scored zero because it paired against 0x003D's
  POSITION vec2 instead of its DIRECTION vec2 — both are plausible angles, so the layout
  is now pinned by a check),
  `toolkit/authsrv/test_replay.py` (a captured .raw decrypts back to the plaintext that
  was logged, and does so all-or-nothing across the whole vault — the first reader of a
  .raw, which closes R0a's standing caveat),
  `toolkit/authsrv/test_cmsgnames.py` (the GAME_CMSG names of 2026-08-11, against
  ArenaNet's own CLIENT traffic — the direction nobody had read, because the client ORs
  0x8000 into every game-channel opcode it sends and without masking that off not one
  message decodes. The seven names it inherited all came from labelled runs on OUR server;
  this corpus is ArenaNet's and is narrated, so it can refute them, and it did: 0x0046
  USE_SKILL was named from a caster, and a whole Ranger session casting Power Shot sent
  ZERO of it — attack skills leave on 0x0027, which our server has no dispatch arm for.
  It also pins the bug that produced two fictitious opcodes: decoding the AUTH channel
  against the GAME_CMSG tables does not error, it invents),
  `toolkit/authsrv/test_smsgnames.py` (the twenty GAME_SMSG names of 2026-08-10, against
  ArenaNet's own recorded traffic rather than against our server — 23 invariants the
  corpus could have violated, pooled over BOTH live captures: two characters of different
  professions walking the same three maps, so the character is the variable and the map
  content is not. That cross-character run is what retired the file's own shipped caveat,
  and nothing needed changing to make it pass. The headline one is that summing 0x001E's
  payload across a tape reconstructs that tape's own wall clock to +18 ms worst case over
  13–185 s, which is what kills the heartbeat reading of the opcode that is a third of all
  server traffic. A second settles 0c from ArenaNet's own behaviour rather than our probe:
  one definition, 140 creates, so the client keeps an NPC definition across a removal.
  Its first version had three red checks and every one was worth having: two were the
  ROTATE_PLAYER trap again — 0x002E's fields are marshalled u32 and hold floats, and read
  raw they make the angle check compare garbage to pi AND make the turn-rate check pass
  vacuously — and the third conflated "arrives before its create" with "names an agent
  never created", which are different facts),
  `toolkit/authsrv/test_msgmix.py` (the tool that ranks what to build next, and the
  three ways it answered confidently about a corpus it had not read: it took the
  newest **6 of 439** gamesrv captures, it read the c2s direction off the server's
  OUTBOUND `sent` log so the whole client-to-server half was **0 of 18,668**
  messages, and `948` -- a count of `unhandled` LOG RECORDS, one per (session,
  opcode) FIRST OCCURRENCE -- was in circulation as a message count, two digs having
  disagreed by exactly it. The population split is the half with teeth: **257 of 439
  captures are unattended `smsgsweep` runs**, whose server emits **381 distinct s2c
  opcodes against a played session's 101**, so pooling them makes ours look like it
  sends 421 of 487 and the NEVER-SENT list -- the reason the tool exists -- collapses.
  The split is exercised THROUGH `population()` the way `main()` does it, because the
  first version handed the section two pre-sorted lists and the pooling sabotage broke
  the classifier with every aggregate check still green. A drop is what the server
  ITSELF flagged in THAT session, never an opcode imputed from another:
  `note_unhandled` landed partway through the corpus (2026-08-12T00:19:42Z; 94 older
  captures, 0 of which carry one of its records), so those messages are unmeasurable
  rather than zero and get their own bucket -- and `0x000C` is flagged in 2 messages
  and handled in the other 42, so imputing by opcode over-attributes it 21x. The
  oracle is the server's own `unhandled_summary.total` against the count rebuilt from
  the `decoded` stream, 326 of 326 agreeing on the real vault with no shared code
  between them. Six sabotages BUILT AND RUN as scratch copies through `--module`, all
  six red (4, 11, 9, 5, 2 and 4 checks) against 56 green -- and the first attempt at
  them went red on a FileNotFoundError rather than on a check, which is a control that
  proves nothing while looking like it proved everything. No vault, no socket, no
  client. ~1 s),
  `toolkit/clientscan/test_skilltable.py` (client skill rows vs. the wiki),
  `toolkit/clientscan/test_attribtable.py` (the client's own `s_attrib` table,
  and the numbering verdict it settles. `studies/combat/PLAN.md` carried
  "contiguous 0–41" — OpenTyria's, and the source of `ATTRIBUTE_COUNT = 42` —
  against "gapped 0–44, ids 26/27/28 reserved" as CONTESTED. **Neither is
  wrong; they answer different questions**, and the table shows both at once:
  the INDEX SPACE is contiguous 0..50 (what `0x003A`'s first array is
  bound-checked against, `cmp esi, 0x33`), the ten playable professions own
  exactly **42** of those rows, and the other 9 belong to profession 11 —
  including 26/27/28, which sit immediately before Dagger Mastery at 29 and are
  precisely the "+3 offset" the rival scheme describes. The table is located
  STRUCTURALLY, never by address: rows self-index at `+0x04`, professions fall
  in 1..11, each playable profession has EXACTLY ONE primary, and the real
  rows total 42 — a conjunction proven refutable by three sabotages (breaking
  one self-index, adding a second Warrior primary, moving one attribute to
  profession 11) that each make the locator refuse rather than return a
  confident wrong offset. Section 1 also closes byte-exactly: the row after the
  last is where `ConstAttrib.cpp`'s own path string begins, which only a
  correct count AND stride reach. **Section 4 is the leg with no circularity**
  — the profession column is in `Gw.exe`, the names are in the owner's
  `Gw.dat` and come back through `textrec`, and the claim is that the 42 rows
  the EXE gives a profession are exactly the 42 the ARCHIVE can name: one
  partition drawn twice by two unrelated mechanisms, `named-not-real=[]`,
  `real-not-named=[]`. It skips loudly with no archive, which is why the floor
  is the archive-less 25 of 29 rather than the full count. Two names are pinned
  as literals — `Strength` and `Dagger Mastery` — following this file's
  existing two-name precedent rather than dumping 42; the emitter itself writes
  **no** authored text, committing `name_string_id` for run-time resolution,
  and a check asserts no string leaks into the rows),
  `toolkit/clientscan/test_attribpoints.py` (`s_attribPoints`, its `arrsize`,
  and the **14 it replaces**. A loopback session on build 38833 died on
  `Assertion: level < arrsize(s_attribPoints)` / `CharData.cpp(202)`, and
  `arrsize` turned out to be a number nobody had read: `consttable.py` carried
  this table as **14 x 4** and it is **13 x 4**. The 14 was not a typo — it
  CLOSED on its anchor, had a code reference behind it, and its own row noted
  the anomaly it caused ("the leading 5 … is what `dead data` looks like from
  the outside") without that being enough to overturn it. The cause is the
  mirror of `test_consttable.py` §7b's: `s_worldData` had a free STRIDE, this
  row had a free LEFT EDGE (`pad=None`), so its base was derived from its count
  and its count came from the displacement in the `CharData:202` accessor —
  which indexes `s_attribPoints[level - 1]` with the `- 1` folded by MSVC into
  the displacement. Base four bytes low, count one high, and it closes because
  the two errors are the same error. **A closure is only evidence for the term
  you did not derive from it.** The locator takes `arrsize` from the client's
  own `cmp esi, 0Dh` (in BOTH accessors), the base from the UNBIASED accessor
  at `CharData:208`, and a left edge from `s_appearanceSlot`'s 8 records of 12
  bytes ending exactly on it — three witnesses, none of them the anchor
  arithmetic. Section 2 runs all three vaulted ArenaNet builds and gets the
  same 13 at a DIFFERENT address on 38519, which is what separates a
  structural locator from an address that still happens to work; a vault
  missing a build skips it by name and then goes red on the floor, because the
  cross-build agreement IS the claim. Seven sabotages, one per leg, each
  required to REFUSE — and one of them earned its keep immediately: the
  left-edge leg was computed and reported but not enforced, so the leg the
  write-up leans on could not have failed. It refuses now. The twelve costs
  and their sum of 97 are checked against retail's published numbers, an
  UPSTREAM list the module never reads out of the table. No socket, no client
  launch. ~1 s),
  `toolkit/clientscan/test_areatable.py` (the map table and string-id decoding),
  `toolkit/clientscan/test_maprows.py` (the footprint join that NAMES archive map
  rows, and the negative the arc turned on. `s_missionClientData` -- the client's
  own name for the 888x124 table, out of its accessor's assert at 0x005A8580,
  where `cmp esi, 0x378` and `imul eax, esi, 0x7c` make 888 and 124 ArenaNet's
  numbers rather than our structural inference -- carries the map's FOOTPRINT on
  its continent at +0x48/+0x58, a rect in terrain cells whose SIZE equals the map
  file's own dims at the known 96.0 pitch, **319 of 319**. The headline is the
  weak half: a two-number key over an 84-value alphabet, and random sizes already
  score ~41%. Which checks are load-bearing was MEASURED by setting the pitch to
  64.0 -- six go red and **section 5 is not one of them**, because the random null
  is a ratio and a wrong pitch moves both terms. What catches it is the one-cell
  control (319/319 -> 0/319) and the two ANCHORS, which go to zero candidates:
  row 7982, whose three names came off ArenaNet's own wire in 9 of 9 live
  connections, and row 22371 from `archive.py`'s measured note. Neither was
  derived from the join. **And that sentence held only on a COLD cache, which is
  what section 2 is for (2026-08-13).** `map_dims` caches 349 decompressions and
  its stamp named the archive alone, while `CELL_PITCH` is consumed BEFORE the
  cache is written -- so WARM, the way anyone runs it, the pitch set to 64.0,
  48.0, 100.0, 112.0, 97.0, 96.5, 96.1, 96.01, 96.001 or 96.0000001 each printed
  ALL CHECKS PASSED (23 checks) and exited 0 in 9.2 s. Only `--all`, which
  deletes the cache file, ever saw the six. The fix FOLDS the coding parameters
  into the stamp rather than adding a hand-bumped version integer beside
  `mapchunks.archive_stamp`'s -- a number somebody must remember to bump is the
  same bet that just lost, and a folded value cannot go stale -- and section 2
  asserts the drop BEHAVIOURALLY, moving each parameter and asking `map_dims`,
  because a test reading the stamp's field NAMES passes against a stamp that
  carries them and compares only the old three. Four sabotages, four different
  red sets; the one that earns the section is a `map_dims` that never loads the
  cache, where all five refusals go vacuously GREEN and only the positive control
  reddens. Its wrong values are DERIVED from the live ones, because the literal
  64.0 stops being a mutation in the very arm that sabotages the pitch to 64.0.
  Section 6 pins the refutation -- no dword column of the
  table resolves to a map-flagged row in either the raw or the packed reading --
  so a future build that gains a map-id -> file-id table fails here loudly. The
  tool returns a SET per row on purpose: 888 named areas over 349 files means at
  least 539 must share one. 29 checks; ~9 min on a cold vault cache
  (MEASURED 558.6 s), ~9 s warm),
  `toolkit/clientscan/test_worldmap.py` (the world-map ATLAS reader -- which
  archive file holds each tile of the per-continent picture the compass, the
  mission map and the world map are three crops of. **The headline is the WEAK
  half and the check labels say so**: "492 tiles over three tiers" is close to
  true by construction, since the module walks the count a table declares and
  emits the non-NULL slots, so an all-wrong reader prints 492 too. Four things
  carry it instead. **`count == CX x CY` on 21 of 21 grids**, where `count`
  comes from the tile table at `0x00A37390` and `CX`/`CY` from `s_worldData`
  4 KB away in another translation unit -- asserted on `grids()`, which
  deliberately does NOT refuse a disagreement (`tiles()` does), because a
  function that only ever returns rows that agree makes the agreement
  unfalsifiable; and the test RECOMPUTES it rather than reading `closes`, since
  `return True` is a one-character sabotage and reddens 2. **Every resolved row
  decompresses to magic `ATEX`** -- 484 of 484, on THREE vaulted archives with
  three different row counts, and the eight ids that resolve on NONE of them are
  a LITERAL in the test file rather than a number the module computes. **The
  control is the same walk one dword early**, written in the test out of
  `struct.unpack_from` and sharing no code with the module: 484 resolved and 0
  non-zero trailers collapses to **0 and 492/492**, from both sides. And
  **locating through `consttable` is asserted BEHAVIOURALLY** -- the fixture
  plants a SECOND `s_worldData` under a different anchor, the corpus row is
  pointed at it, and the grids' dimensions must MOVE, because a test that reads
  the constant passes against a module that never uses it. Two results the arc
  did not have: there are **THREE tile tiers, not two** (`0x00A37440`, indexing
  with `worldData+0x18`), which settles `satelliteCX/CY` from the client's own
  `imul edi,[edx+0x18]` beside the assert `chunk.x < worldData.satelliteCX`; and
  **not every tile is 512x512** -- 15 of 484 are 256x256, four of them in the
  CHUNK tier and not at an edge, where FINDINGS says 512x512 off a sample of 4.
  Sections 0-2 and 6-7 build a PE32 image byte by byte -- three synthetic
  getters, planted tile tables, planted NULL slots, a planted `s_worldData` --
  and every refusal in section 1 is a way the module could answer plausibly and
  wrongly: a getter whose bound check and index arithmetic read DIFFERENT
  fields, a loop bound that is not a whole number of records, two getters
  claiming one tier, a slot pointing at bytes the file does not hold.
  **Nineteen one-edit sabotages were BUILT AND RUN and all nineteen redden**
  (9, 8, 5, 4, 3, 3, 3, 3, 2, 2, 2, 2, 1x7); the one that earns its place
  reddens exactly ONE check with nothing else moving, the bound-check versus
  index-arithmetic disagreement, which is invisible on the real image because
  there the two reads agree. `guarded()` is why the several that take out whole
  sections are named red checks and not a traceback with no verdict.
  **THREE of those nineteen scored ZERO red on the file as first written --
  ALL CHECKS PASSED, exit 0 -- and each is a shape this repo has been bitten by
  before.** (1) A `main()` that NEVER CALLS `resolve_out` and writes straight to
  `a.out`: section 6's syntax-tree check read `HERE/worldmap.py` instead of the
  module under test, so it was structurally exempt from `--module`, which is the
  mode the whole sabotage table is measured in -- a section that cannot fail in
  the one mode its own evidence comes from. It reads `wm.__file__` now, and a
  second check requires every WRITE SITE to write the name bound to the guard's
  answer, because the write is `Path(x).write_text` and an `open(..., "w")`-only
  scan finds zero write sites and passes vacuously (`test_atex.py` section 3,
  one level up). (2) A reader that never reads the pair record's TRAILING u32
  and assigns `trailer = 0`: all 492 real records carry zero, so it agreed with
  the independent walker and with the client census, and PLAN rung S3's
  prediction was being confirmed by a constant -- only a planted non-zero in the
  fixture can tell a reader from an assumer. (3) The emitted index stamping
  `pinned.BUILD` on every row: `--exe` takes any file and `pinned.find()` falls
  back to the auto-updating install at `C:\gw`, so condition 2 was recording a
  CONSTANT rather than the build of the image read. The build is measured from
  `pinned.identify()` now, the row names WHICH image, and the control is a
  payload built from an unidentified path that must record `None`. One check was
  also DELETED as one that cannot fail -- `ar.row(n).index == n`, which
  `archive.py:367` asserts internally and would have raised first -- and
  replaced by two the archive can refute. THREE scores, each measured and none
  subtracted: **77 with client and archive, 64 with the client alone, 39 with
  neither** -- floor 77, so a vault-less run goes red. The archive section
  scores a fixed count however many archives a vault holds, and **as of
  2026-08-14 so does section 6's checkout refusal**. It was one check PER working
  tree, and `working_tree_roots()` answers 2 inside a git worktree against 1 in
  the main checkout -- so the old floor of 78 silently required the suite to be
  run from a worktree, and `run_suite.py` in `C:\gd\Rurik` reported "ONLY 77 OF A
  DECLARED FLOOR OF 78 CHECKS RAN". A count that moves with the caller's working
  directory cannot be a floor: the vacuity guard cannot tell it from a lost
  section, which is the one thing it exists to catch. The refusal is now a single
  verdict over every root, naming any it failed to refuse, so each score above is
  one lower than before and the same in both environments. ~2.5 s),
  `toolkit/clientscan/test_skillcast.py`, `toolkit/clientscan/test_textrec.py`,
  `toolkit/clientscan/test_srctree.py` (the Cli/Srv source-tree split, on both
  vaulted builds — and it proves its own negative result can go red first. Since
  2026-08-12 it takes the two STAMPS from `pinned.BUILDS` rather than spelling
  them again, and a build added to that registry with no expected path count here
  FAILS rather than being skipped: this is the only cross-ArenaNet-build test in
  the tree, so an unmeasured build sitting in the registry would leave it claiming
  a coverage nothing provides),
  `toolkit/clientscan/test_sigcorpus.py` (every byte-shape anchor in the repo,
  counted on both vaulted builds — `studies/crossbuild/PLAN.md` §7.2. It is where
  that plan's two derived-but-never-landed signatures live: `WORKAROUNDS.md` §3.5
  derived the attribute accessors (4 hits) and the `imul`-stride colour tables
  (2 hits), recorded the counts in prose, and put neither in code, so nothing
  could re-check them. With `REGISTER_SIG` and `ASSERT_SIG` derived since, the
  corpus is **eight, all reproducing their exact hit counts on both builds** while
  every address they resolve to moved — the two profession signatures by exactly
  0x2350 (9,040) bytes, the figure §3.5 recorded. Exact counts, not "at least
  one": a signature that has quietly become ambiguous still resolves and still
  answers. §2 is rule 2 — no build-specific address in a pattern — and the honest
  version of it: the obvious scan ("no 4-byte window lands in the image range")
  was written, run and **REFUTED by its own output**, flagging `SIG_KEYS` and
  `ASSERT_SIG` on windows straddling instruction boundaries in signatures that
  match both builds. The sound argument replaced it — one byte string matching two
  images whose addresses all moved cannot contain a build-varying byte — plus the
  narrow scan that IS sound, that no signature embeds an address it resolves to.
  §3 is the point: the resolved addresses must be DISJOINT across the builds, or
  the corpus is evidence of nothing. It must NOT be read as "signatures are
  stable" — n=2 over one build gap. Needs the vault. Floor 34, ~4 s),
  `toolkit/clientscan/test_buildid.py` (the client's own build number, read out
  of the binary — `studies/crossbuild/FINDINGS.md` §3, which closes what §8 of
  that plan had recorded as NOT FOUND. `pinned.BUILD` was typed in and the older
  vaulted build's number appeared NOWHERE in the tree, so half the corpus could
  not satisfy `HANDOFF.md`:237's day-one rule that every capture manifest records
  a build id. The obvious place was refuted first: the PE version resource reads
  `FileVersion '1, 0, 0, 1'` on BOTH builds and on four sibling DLLs. The client
  compiles its build as a whole function — `mov eax, <build>; ret`, int3-padded —
  and **the shape is common while the value is not**: 54 such getters on 38797
  and 56 on the older build, exactly ONE of each in the five-digit build range.
  Both counts are asserted, because "one candidate" says nothing without the
  number rejected. The older build is **38519**, which it had never been called
  before. §2 drives the zero-candidate and many-candidate refusals by moving
  `BUILD_MIN`/`BUILD_MAX` on a real image, each with a positive control that the
  real range still resolves. **§3 is what makes the range assumption checkable
  rather than circular**: for 38797 the client says the same number over the
  NETWORK — the schema's stamp, `authsrv.py`'s VERSION frame, the live
  `User-Agent: Gw/38797.0 (Win32)` — and a value derived from bytes agreeing with
  one observed on the wire shares no lineage at all. It also pins that the
  schema's stamp is nested under `provenance` and NOT a top-level key, which is
  how the first version of that check "failed". §4 requires `pinned.BUILDS` to
  match a fresh read, so the registry stays derived rather than hand-edited —
  which is what let build **38833** be added on 2026-08-14 as a measurement
  rather than a typed-in row. That build is the sharpest case for §1's argument:
  its getter is at `0x004729E0`, the SAME address as 38797's, with the same 54
  candidate shapes, so the returned immediate is the *only* thing separating the
  two images and the read still lands on exactly one in-range candidate. The
  ascending-numbers check was also respelled as a sort, because the two-build
  spelling had to be edited the moment a third arrived.
  Needs the vault. Floor 29 (was 23; 38833 adds 6), ~6 s),
  `toolkit/clientscan/test_avevents.py` (the two AgentView event allocators,
  located by ArenaNet's own asserts — `studies/crossbuild/FINDINGS.md` §2.5, and
  the last two addresses in that census. They were literals used to match call
  targets, so on any other build nothing matched and the tool reported that
  NOTHING ALLOCATES ANYTHING: a confident empty answer, not an error. Neither
  allocator contains an assert, but each sits immediately beside a function that
  does, so ACTION is the function immediately BEFORE the one asserting
  `AvChar.cpp:1243` and `:1251`, EFFECT the one immediately AFTER `:2433` and
  `:2438`, with boundaries from MSVC's `int3` padding — the inference that named
  them is now also the locator. **§2 is the check that earns the file**:
  `AvChar:1243` ALONE sits in three distinct functions on both builds, so a
  version taking the first hit is right on 38797 *by luck*, and the first draft
  of this derivation did exactly that and passed; it is the PAIR of lines that
  resolves to one function, and §2 measures both numbers rather than asserting
  the rule. §4 reproduces the ambiguous anchor and requires a refusal, with the
  real anchors resolving afterwards as the positive control. §3 is the half a
  lookup cannot fake: the 38519 build derives a different pair — **not one
  address shared** — and still reproduces the census, 23 action call sites and 22
  kinds on all three. The function-boundary walk is reimplemented in the test out
  of `int3` padding, so it is a second witness rather than a second call to the
  module. **§3 was rewritten 2026-08-14 when 38833 arrived and broke it twice:**
  it unpacked exactly two images (`a, b = [...]`, a ValueError on three), and its
  claim that NOT ONE address is shared *between the builds* is **false** for the
  38797/38833 pair, which derives the same two addresses because that 15-day
  patch did not move them. Read literally it said a derivation returning the same
  answer on two builds has degenerated into a lookup, which does not follow. Now
  pairwise: at least ONE pair must be disjoint — a lookup could not manage that —
  and agreeing pairs are printed as the measurement they are.
  Needs the vault. Floor 26 (was 19; 38833 adds 7), ~50 s),
  `toolkit/clientscan/test_framebus.py` (the frame-bus pairing that twelve quest
  names rest on — `studies/quests/FINDINGS.md` §9, rung Q1. The client's UI does
  not read the wire: a handler in `ChCliApi` posts a numbered frame and UI
  modules subscribe, so "what does opcode X do on screen" has a STATIC answer,
  and it is the strongest evidence available for naming an opcode with no client
  run. FINDINGS had both halves — §1.6's publisher VAs, §2.1's handler bodies —
  in two tables and never joined them per opcode, which is how §7.6 came to say
  "Nothing static will substitute" about a question its own document answered.
  **The regression this file exists for is the CALL WINDOW.** The `push imm32`
  and the `call` that consumes it are not adjacent — the body stages the frame
  payload between them — and a window too short does not error, it returns a
  confident short list: §1.6's own scan used 6 bytes and missed two sites, and
  24 bytes missed `0x0050`'s, whose call sits at +29 behind three payload stores
  (one of them `0x378` == 888, the no-marker map id). §1 plants a call at
  exactly +29 and at BOTH edges of `CALL_WINDOW` on a synthetic PE, so shrinking
  the constant goes red rather than quietly un-measuring an opcode — verified by
  sabotage: reverting it to 24 fails 4 checks and turns `0x0050` into a silent
  negative in both sections. §1 also plants a SUBSCRIBE call that must not count
  as a post, an out-of-band id that must be invisible, and a VA in no section
  that must raise. §2 asserts the eleven-body pairing against the pinned image
  including the two SHARED ids — the two adds agree, the two log-text messages
  agree, and the three marker ops, which share ONE payload layout, do not; the
  payload cannot tell `0x004D`/`0x0051`/`0x0053` apart and the frame id can,
  which is the entire naming argument for those three. Its last check is a
  CONTROL on the measured negatives: `0x004A`'s empty result is scanned over the
  same window as the positives, because a negative produced by a narrower scan
  is an artefact rather than a finding. §1 runs on a bare machine — `framebus.py`
  is a fixed-byte-pattern tool and takes no disassembler — and §2 declares a
  `LEDGER.skip` without the vault, which is why the floor is 14 and not 18. ~1 s),
  `toolkit/clientscan/test_genericvalue.py` (the property-id switches, and that a
  moved build cannot be read as a map — `studies/crossbuild/PLAN.md` §6.
  `genericvalue.py`'s docstring claimed "a build that moves them fails loudly
  instead of returning a stale map that still looks plausible"; that was true of
  `CHAINS`, which carries `verify` bytes, and FALSE of the other 30 addresses in
  the file — the five table switches stored a jump-table and index-table address
  each and checked neither, `read_switch` verified only that an index landed
  inside the table it had just read (internal consistency, which catches a
  corrupt read and not a moved one), and `MAIN_SWITCH_GATE` printed
  "MOVED — results are suspect" and carried on. The table addresses are now read
  out of the `movzx`/`jmp` pair that jumps through them: 10 addresses gone,
  32 → 27, and the rest gated. **ROUND TWO, 2026-08-14, and the file's central
  claim is INVERTED.** Build 38833 shipped, this module refused it outright and
  took `avevents.py`'s property map with it — being right about not knowing beats
  being confidently wrong, and is still not being able to read the client. The 27
  are now **ZERO**: the two dispatchers are the handlers the client's own RECEIVE
  table gives for opcodes `0x009F` and `0x00A2` (so the chain bottoms out in
  `RegisterMsgs`, anchored by byte shape), each handler is a forwarder with
  **exactly one** call, the int dispatcher holds **exactly two** switch sites and
  the float one **exactly one**, each dispatcher calls **exactly two** functions
  holding a property switch — store then AgentView — each default is the jump
  target the most ids share, each span is read from the `cmp`/`ja` guard, and each
  chain's ids are parsed from its comparisons. §1 requires the derivation to
  reproduce every address that used to be typed into the module, which now live
  here as class-(c) expectations; that move is what took the module's census to 0,
  since a hand-measured address is class (a) only while the TOOL computes with it.
  §3 is the inversion: every vaulted build must be READ and all three must agree
  — 47 int ids, 14 float, exactly {40} untouched, main switches disjoint — while
  putting those switches at three DIFFERENT address sets, which is what a
  derivation looks like and a lookup cannot fake. §4 keeps the framing control (a
  site off by ONE byte is refused) and adds four sabotages, one per "exactly N"
  guard, each with the module restored in `finally` and a positive control after.
  Why the old form could not do better is still MEASURED: the `movzx`/`jmp` shape
  occurs **596 times** in `.text`, so it identifies "a switch" and never "this
  switch" — which is why the dispatchers had to be anchored first, and now are.
  Needs the vault throughout. Floor 39, ~20 s),
  `toolkit/clientscan/test_commanderpeek.py` (the live hero-commander reader's
  own instrument check. `commanderpeek.py` reads a running client, so almost
  nothing about it can be tested offline -- except the part that actually
  failed. On 2026-08-16 its `--events` mode walked the UI subscriber map and
  reported **NO SUBSCRIBER** for all three commander events, `0x100001A4`
  included, which is KNOWN LIVE because the party-window button raises it and
  the client asserts inside its handler at `GmView.cpp(5890)`. The reading was
  false, and it fitted the arc's story -- "the event is raised into nothing" --
  so neatly that it would probably have survived review. The cause: the map
  hashes through `0x004920B0`, so a plain bucket walk never sees a real key
  (512/512 slots non-empty, no event-id-shaped value at any offset). The fix
  was a positive control inside the tool: find `0x100001A4` or give no answer.
  §1 proves the gate REFUSES on a synthetic map where the wanted event IS
  present and the control is not -- exactly the shape that would otherwise read
  as a confident SUBSCRIBED; §2 proves it still answers when the control is
  there, so §1 is not vacuous; §3 checks `0x00C07850` and `0x00C11BC4` are
  still loaded by `mov eax,imm32`/`mov ecx,imm32` in the vaulted client, which
  goes red on a rebuild rather than letting the tool read a stale address, and
  SKIPs with its reason when the vault is absent; §4 pins that a NULL context
  is reported rather than dereferenced. Floor 7, instant),
  `toolkit/clientscan/test_msgshape.py` (the client's message-format tables,
  DERIVED from the image instead of remembered — `studies/crossbuild/PLAN.md` §3,
  and the reason that plan put this file first. `msgshape` underpins
  `msghandler.py` and `test_catalog.py`'s 477/477, and its 25 table addresses
  were measured on build 38797, so on the other vaulted build it printed
  `cmd slots 0`, four FAILing oracles, `descriptor invariant violations: 0` — a
  line vacuous over ZERO descriptors and byte-identical to the healthy build's —
  and **exited 0**, while `msgshape.py 0x00E5` answered "opcode 0x00e5 is in no
  table on this build", which is a claim about ArenaNet's client and was false.
  651 of 751 entries had died at one `continue`, and a `continue` is not a
  refusal. `RegisterMsgs` is now anchored by a 17-byte shape carrying no address,
  its 14 callers are enumerated, and the six pushed `__cdecl` immediates give
  back every table. The headline — the derivation reproduces `TABLES_38797`
  EXACTLY on 38797 — is deliberately the WEAK half, since a function that
  returned the constant would pass it; §2 is the half that cannot be faked, the
  same code recovering 25 tables and 751 entries from a build sharing **not one**
  table address, with every entry COUNT identical (the tables moved, the protocol
  did not). §0's negative control is the routine's own 7-byte prologue at 56 and
  57 hits, so "take the first hit" would resolve the wrong routine silently —
  which is why the −0x22 delta is VERIFIED after a match rather than searched
  for, and both the zero-hit and many-hit refusals are driven by swapping the
  pattern, each with a positive control that the real one still resolves
  afterwards. §3 drives `measured_nothing()` with a doctored table set and pairs
  it with real builds, because a predicate answering True to everything would
  pass the vacuity check alone. Needs the vault throughout. Floor 37, ~35 s),
  `toolkit/clientscan/test_pinned.py` (which `Gw.exe` a tool actually reads, and
  the guard on it going red — `studies/crossbuild/PLAN.md` §5. `pinned.find()`
  used to answer with `os.path.isfile` and return, so `identify()`, the only
  function that hashes anything, was reachable from `main()` and two unrelated
  tests and from NOTHING on the path the twelve static-analysis tools take; its
  last fallback was the auto-updating install at `C:\gw`, returned with the string
  "may not be 38797" and no refusal, which for build-specific addresses is a
  confident wrong number rather than an error. The load-bearing checks are the
  ones a size gate cannot pass: a file of build 38797's EXACT size with wrong
  bytes must be refused — that is the module's founding defect, since the vault
  holds two copies of 38797 at the same length 144 bytes apart — and `find()`
  given an empty vault and a live install that EXISTS must refuse rather than
  substitute it, which is the configuration the old code got wrong. Each refusal
  carries a positive control, and the one that earns the file is running the SAME
  planted file with `verify=False` and requiring it BACK: without it, "it refused"
  is satisfied by a `find()` that refuses everything, and a guard that refuses
  everything protects nothing because the tool never runs. Also that the older
  client — a genuine pristine build — is `unknown` when asked about AS 38797,
  while identifying as itself unscoped, so the refusal is the scoping rather than
  a broken hash; and that each stamp is its own pristine sha256 prefix, so a
  mistyped hash cannot sit in the registry looking plausible. **The size
  invariant was INVERTED 2026-08-14 and the old one is the lesson.** It asserted
  "the two builds differ in SIZE, so size separates them" and went red the day
  38833 was registered, because 38833 ships at 10,483,904 B — byte-for-byte
  38797's length — while being a different build. The red was right and the
  claim was wrong: size never separated the two copies *within* a build, and it
  no longer separates builds either. It now asserts the invariant that actually
  holds, **sha256 is the discriminator**, prints any size collision as a
  measurement, and proves the collision is survivable by requiring `identify()`
  to name each build from its own image — the behaviour the registry's safety
  now rests on, rather than a property of what the vault happens to hold.
  `LIVE_INSTALL` is
  monkeypatched to a temp path so both fallback branches run on every machine
  rather than only one with `C:\gw`. **§5 and §6 are the PROBE GATE**
  (`studies/crossbuild/FINDINGS.md` §2.1): `itemprobe.py` and `agentprobe.py`
  hold three raw RVAs and did not import `pinned` at all, and they read a LIVE
  client at `module_base + RVA` — so on another build they do not compute a wrong
  answer, they dereference whatever else is mapped there and print it as an agent
  array. `pinned.assert_build()` now hashes the running process's own `Gw.exe`
  (via `keytap.module_info`) and refuses. §5's decisive check is that it refuses
  the OTHER vaulted client — a genuine ArenaNet build and still the wrong one —
  which caught a real defect while the gate was being written: the first version
  called `identify()` unscoped, and unscoped it considers every registered build,
  so it accepted the older client. §6 asserts the ORDERING on the syntax tree,
  because "gates before it reads" is invisible to a grep — a file with both names
  in the wrong order greps identically — with a reversed probe that must be
  rejected and a correct one that must be accepted. `--any-build` is the
  deliberate override, because a gate that makes a tool unusable the day a build
  ships is one somebody deletes. Without a vault §4 skips and the run scores 43
  against a floor of **61** (was 55; 38833 adds 6), so it goes red — the 43 was
  measured with `RURIK_VAULT` pointed at an empty directory, not derived by
  subtraction. ~2 s),
  `toolkit/clientscan/test_msghandler.py` (the receive-handler classifier, which is
  the loopback opcode sweep's PREDICTION stated before it runs. Three corrections it
  pins, each to a claim that was in circulation: **477 of 477 table entries carry a
  non-null dispatch**, so the sweep has no "inert by construction" bucket and a silent
  result is a fact about the readout rather than about reachability; the never-seen
  denominator is **324, not 332** — 332 is `487 − 155` over the schema while the
  receive table holds 477, and the difference is exactly the ten opcodes catalogued
  with no receive entry; and **"absent from the table" does not mean "inert"**, because
  `0x000C`/`0x000D` are two of those ten and are the latency round trip the client
  demonstrably acts on, handled below the message table. It also CORROBORATES something
  `agents.py` had as inferred: the client's own dispatch pairs 0x009F/0x00A0 to one
  callee and 0x00A2/0x00A3 to another, splitting GWCA's four generic-value shapes
  exactly along the int/float line, with the with-target member of each pair carrying
  one extra field. Its control is the base rate — 241 forwarders over 215 callees with
  only 8 shared at all — because a pairing means nothing if sharing is common),
  `toolkit/clientscan/test_codescan.py` (the attack-speed chain, the two
  decoding traps that hid it, and §7's three under-reporting defects — a
  `--field` that knew one displacement encoding of two, a `--xrefs` that swept
  one alignment of four, and an assert scan that knew one of the idiom's three
  shapes. Each pinned at a named address with the reason it was missed, because
  all three answered a clean confident zero. Its stdlib half runs without
  capstone: `asserts.py` takes no disassembler on purpose, and its under-count
  silently narrows every `--in <module>` range on the capstone side. §8 and §9
  are the same failure from the other direction, found 2026-08-11: the assert
  census grouped by BASENAME and printed the path of whichever colliding file
  held the lowest VA, so nine rows summed two modules under one of their names
  while the other vanished. The two biggest rows of that report described no
  file in the image — `Base\rtl\Array.h` (4431) and `Base\rtl\List.h` (3288)
  printed as 4433 and 3295 under their `.cpp` siblings — and `PrApi` merged the
  preferences module (67) with the props module (19), 2.4 MB apart, so "props
  has no PrApi.cpp" read as absence. §8's FIRST check is the negative control,
  the collision itself, and it reproduces the old grouping inline so 67/19 is a
  difference between two live answers rather than a number the test asked the
  code to confirm about itself; the basename sabotage reddens 9 of its 19. §9
  pins the consequence downstream, where `module_bounds` matches a substring and
  therefore silently WIDENS `--in PrApi` to 2.4 MB — with `--in AvChar`, which
  legitimately catches the adjacent `AvCharAnim.cpp`, as the control that must
  keep reading differently, since a warning that fires the same way on both is
  noise. **§10 (2026-08-13) is the same defect a THIRD time, from the direction
  that makes the footer's encoding list not enough.** `--field` searched MEMORY
  OPERANDS and nothing else, so `--field 0x6bc` answered **14** without
  `0x00813AD1 add ecx, 0x6bc` — the writer reached from GAME_SMSG 0x00B6's
  handler, i.e. the writer of the very field studies/profession/RUNS.md §13 was
  hunting — plus four more `add ecx` sites and an `add ebx`. Five of 19, from a
  report whose footer disclaimed disp8 and disp16 and therefore read as
  complete. The constant is not a displacement at all: `81 c1 bc 06 00 00`
  carries 0x6BC in its IMMEDIATE field, which the test reads off the bytes
  (`disp_size == 0`) rather than asking the scanner about. The old
  displacement-only rule is REPRODUCED inline out of capstone and struct and
  required both to reach 14 and to MISS that address, so 14 against 19 is a
  difference between two live answers — §8's pattern. The other half is the
  controls on the new `A` (address-taking) class, because widening `A` is the
  lazy way to pass: a real load stays `R`, a real store stays `W`, no `A` row
  may claim `is_write` (§2's two-writers claim reads that field), and `lea`
  moved from `R` to `A` because it touches no memory. `sub reg, -imm` is
  searched too and pinned against real bytes — `sub ecx, -0x19` at 0x00622199,
  whose immediate byte is 0xE7 and which therefore needs its own anchor and its
  own sweep; 265 sites of `sub eax, -0x80` are why that sweep is paid for. The
  one filter is NAMED and controlled: a narrow destination is dropped, and
  `add al, 0xe` at 0x00479BC8 is decoded and proved to exist before the check
  that it is excluded. Three sabotages built and run, three redden. 106 checks
  with capstone (was 83) and 35 without — §10 needs a disassembler for every
  claim and declares one skip, so the stdlib floor is unmoved),
  `toolkit/clientscan/test_consttable.py` (the `Gw\Const\*.cpp` table locator, and
  the correction it made to the recon that commissioned it. MSVC emits a translation
  unit's static data and its string literals in source order, so every one of these
  tables is followed immediately by a string -- its `__FILE__` path or an assert
  expression -- and `base + count*stride` lands on that string's first byte. The recon
  predicted **12 of 14** close with two 4-byte non-closures, "alignment padding, a
  `-1` sentinel". Re-derived from the bytes: **24 of 24 close**, 17 flush against
  their left neighbour, **four** at exactly +4 (MSVC 8-alignment, and all four are
  alignment), and **no sentinel non-closure exists** -- `s_attribPoints`'s
  `FF FF FF FF` is the LAST ELEMENT of the array and `arrsize` counts it, so the
  array lands on the anchor. What sentinels really cause is a third shape, a table
  whose left neighbour is not a string at all, which is why `s_skill`,
  `s_missionClientData` and `s_attribPoints` declare no left edge -- and for
  `s_attribPoints` that free left edge cost it a wrong COUNT for four days: it
  shipped here as 14 x 4 and is 13 x 4, corrected 2026-08-15, §7c below. **The headline is
  deliberately the WEAK half**, because `base + count*stride == anchor` is
  definitional unless the two terms come from DIFFERENT witnesses: eight tables take
  their count from their own ascending index column and their base from the previous
  string, and all 24 bases are corroborated by the client's own accessor loading that
  exact address (29 references, minimum 1). Two of those bases are checked against
  implementations that share no method with the anchor -- `skilltable.locate_table`,
  which finds `s_skill` by its SELF-DECLARED count in row 0, and
  `reskin.locate_attrib`, which corroborates `s_attrib` with an id column and a
  profession-range check. **The blind spot is measured rather than argued away**: a
  stride that DIVIDES the true one closes on the same base with a multiple of the
  count -- `s_eula` reads as 99 x 4 instead of 33 x 12 -- and only an index column can
  refute it, so the surviving rival strides are printed per row (`s_effect` 0,
  `s_eula` [4, 36, 44, 132]). That is
  not hypothetical: `s_glow` was entered in this corpus as 2 x 44, CLOSED on the
  correct base with a plausible record, and is 11 x 8. Three sabotages built and run
  and three redden -- a first-hit anchor, a +/- 4 pad tolerance, and the code witness
  dropped -- which is why `pad` is a declared exact number and never a tolerance
  (4 bytes is a whole record for the eight stride-4 tables here).
  **And since 2026-08-14 section 7b is the blind spot's OTHER victim, caught rather
  than survived.** `s_worldData` shipped here as **20 x 24** with
  `stride_from="record shape, UNSETTLED"` -- it closed, on the CORRECT base, with the
  code reference corroborating it, so every check this module owns was satisfied by
  the wrong answer for as long as the row existed. It is **10 x 48**, and what
  settled it is not arithmetic available to this file: the table's own accessor at
  `0x005A93B0` scales the index by 3 and shifts it left 4, and the section finds that
  site by its SHAPE rather than at a remembered address -- the `lea`+`shl` pair alone
  occurs 22 times, so it is the trailing absolute `add` that makes it a witness, and
  the whole 7-byte pattern occurs exactly **once**, loading the very base the anchor
  arithmetic produced. Read as BYTES, since carve-out (1) scopes capstone to two named
  files and this is neither. **The count is ArenaNet's too** -- `cmp esi, 0xa` guards
  `index < arrsize(s_worldData)` at `ConstWorld.cpp:41`, whose `__FILE__` string IS
  this row's anchor, so the assert and the table are one measurement from two
  directions -- and the row DECLARES it (the `s_missionClientData` shape) with a check
  that dropping the declaration reddens, because the number would be unchanged and the
  provenance would not. **24 is still in the rival list and saying so is the doctrine
  working**: every divisor of 48 closes on the same base, and the closure never could
  have refuted it. What can is a COLUMN -- `+0x14` is 512, the client's own
  `CONST_WORLD_CHUNK_SIZE`, on all ten 48-byte records and ragged on the twenty
  24-byte ones -- and that is a stated LIMIT of `rival_strides`, which tests closure
  and the index column and never column coherence. Four sabotages built and run
  (3, 5, 2 and 1 red); a draft of the floor comment GUESSED those counts and had three
  of four wrong. The one that does NOT redden under the pre-fix row is the informative
  one: the left-edge corroboration passes at 20 x 24, because 24 divides 480 and two
  readings of the SAME 480 bytes cannot see a divisor stride. Only the code witness
  can. Floor 61 -> 69.
  **Section 7c, added 2026-08-15, is 7b's MIRROR, and it is the row that reached a
  player.** `s_worldData` had a free stride; `s_attribPoints` had a free left edge
  (`pad=None`), so its base was derived from its count and its count came from the
  displacement in the `CharData:202` accessor -- which indexes
  `s_attribPoints[level - 1]`, with MSVC folding the `- 1` into the displacement.
  Base four bytes low, count one high, and it closed perfectly because the two errors
  are the same error. `(base-4, 14)` and `(base, 13)` land on the identical anchor, so
  nothing in this module could ever have chosen; the section reproduces both readings
  live and shows that what separates them is the CONTENT (13 opens on a strictly
  increasing run, 14 opens on a stray `5`) and three outside witnesses, all from
  `attribpoints.py`: the client's own `cmp esi, 0Dh` in both accessors, the UNBIASED
  accessor at `CharData:208`, and `s_appearanceSlot`'s 8 records of 12 bytes ending
  exactly on the corrected base. The twelve values sum to **97**, retail's published
  cost of a rank-12 attribute, against 102 for the 14-element reading -- an UPSTREAM
  number this module never used. The row's own note had called the stray `5` "dead
  data" and that was not enough to overturn it, which is the lesson: **a closure is
  only evidence for the term you did not derive from it**, and a table with a spare
  element at the front is a table whose left edge is wrong. Floor 69 -> 74. The cost
  of the four days it survived is in `studies/combat/PLAN.md` §14 -- a modal assert
  box, twice, from a server that had built `0x003A`'s rank column against a bound
  nobody had read. It is also the
  first `source = "client-table"` extraction in this repo's history: `--emit-effect`
  writes all **2,077** `s_effect` rows with provenance per row, keyed by the ARRAY
  INDEX rather than the id column (one record's id is not its index, and keying by id
  would drop row 2036 and mint a 2077), and the test loads them through `content.py`
  and then REMOVES the build from one row and requires the load to FAIL, so the 2,077
  are proved to have passed condition 2 rather than skipped it. Sections 0-4 build a
  small PE32 image byte by byte and need no vault, scoring 28 against a floor of 69,
  so a vault-less run goes red. ~15 s),
  noise. **§10, added 2026-08-12, is the both-build run** —
  `studies/crossbuild/PLAN.md` §4. `asserts.py` compared every site's call target
  against `ASSERT_VA_38797`, a literal, so the older vaulted build came back
  `single-routine=False` with a warning and `studies/srvtree/FINDINGS.md`:262-268
  recorded its assert corpus as not trustworthy — which matters downstream,
  because `codescan --in` takes its module ranges from here and an under-count
  narrows every search inside it silently. The callee is now derived two ways
  that must agree: the modal call target of ~19,700 sites (**one** distinct
  callee, 100.0000%, on both builds) and a 27-byte signature carrying no address.
  The assertion is the SHAPE COUNTS — 19,758 = 19,620 + 75 + 63 on 38797,
  19,680 = 19,544 + 74 + 62 on the older build — because a bare
  `single-routine=True` is satisfied by a scan that found two sites, and all
  three shapes must be present or the consensus is over one spelling of the idiom
  rather than the idiom. Its negative control is that the routine's own prologue
  is NOT unique, 56 hits, which is why the signature anchors in the body and the
  −11 delta is verified after a match rather than searched for. Both floors were
  re-measured rather than incremented: 93 with capstone, 45 stdlib-only),
  `toolkit/test_buildpins.py` (the build-coupled census — `studies/crossbuild/`
  `PLAN.md` §6, and the number that replaces `PLAN.md` §6:803's "ongoing":
  **68 live constants across 7 files**, against 360 prose citations and 133 test
  expectations. The one thing it must prove is that those three are told apart,
  because class (a) and class (b) are **the same string** — `0x00487BC0` in a
  docstring is provenance that `PLAN.md` §7 Q3 protects, and in an assignment it
  is a per-build liability. §1 puts the same address in a docstring and in code
  in one synthetic module, requires opposite verdicts, then reproduces the grep
  inline and shows it returns 2 and cannot say which is which. That is not
  pedantry: citations outnumber live constants 360 to 68, so a grep-built census
  is 84% noise and invites "scrub the addresses", which is the reading that cost
  a session of rewrites and all 46 reverted. Every exclusion was MEASURED from a
  real false positive in the first run — bit flags, the image base, all-ones
  masks, two-digit literals, and the map file id `0x345CC` cited in five modules;
  dropping the RVA bucket moved the count 104 → 68 and 21 files → 7 — and every
  exclusion carries a positive control that a real address survives it, since a
  filter that drops everything produces a very clean census of zero. The
  instrument excludes itself and says so. `--diff` exits **1 for a changed
  census, which is a result**, 0 for unchanged, the same contract `datcheck.py`
  draws. No vault, no client, no socket. Floor 40, ~2 s),
  `toolkit/test_updatecheck.py` (the before/after update commands —
  `studies/crossbuild/PLAN.md` §11, and the one deliverable of that arc that
  expires if nobody runs it in time: an update is not schedulable and half the
  arc's measurements need a BEFORE state. **§1 is provenance and is the check
  that would matter most if it failed** — the baseline records the DH parameters
  as a FINGERPRINT (generator, bit length, sha256 prefix) and never the values,
  so the test reads the REAL prime and B out of the vaulted client and requires
  neither to appear anywhere in the serialised baseline, in decimal or either hex
  spelling. §2 pins the distinction the report exists to draw: a signature that
  moved to a NEW ADDRESS with the same hit count still resolves and must NOT be
  flagged, because that is what a healthy update looks like and a report that
  shouted about it would be deleted after the first real one — while a changed
  HIT COUNT is flagged `RE-DERIVE`. §3 drives all three exit codes **through the
  process**, which is how the exit-2 contract was found broken: `CannotRun`
  subclasses `SystemExit`, and `SystemExit("some text")` carries the text as its
  code, so the process was exiting 1 and "could not run" was indistinguishable
  from "something moved" to anything reading the code. Asking the exception for
  its `.code` had passed. §4 refuses the baseline into any checkout of this repo,
  including the other one. Floor 26, ~60 s),
  `toolkit/test_checks.py` (the check on the checker — see below),
  `toolkit/test_run_suite.py` (the suite RUNNER, which did not exist until
  2026-08-13 — 66 test files and **0 scripts that ran them**, so every "the suite is
  green" in this repo's history was a human pasting paths into a shell, which is how
  2026-08-06 reported twenty of twenty-three green with both omitted files red.
  Running N subprocesses is trivial; REPORTING HONESTLY about them is not, and the
  ad-hoc runner this replaces got the count wrong **three times in one day, each time
  in the direction that looks like success**. Every check here reproduces one. (1) It
  harvested the file list out of CLAUDE.md's prose with
  `toolkit/[\w/]+test_\w+\.py`, which cannot match `toolkit/test_checks.py` — the `+`
  demands a character between the slash and `test_` — so it ran **63 of 71** and
  printed "62 green of 63", a partial run presented as a full one. (2) Fixed, it found
  70 of 71: `test_handshake.py` is named only inside a FENCED CODE BLOCK, so the
  document is not a parseable index and never was — the list now comes from the DISK,
  which `test_srclint.py` already binds to CLAUDE.md in both directions with a check
  that can go red. (3) Reading the LAST line for the banner scored `test_handshake.py`
  and `test_webgate.py` at **0 checks while they exited 0**, because both print after
  their banner — so the runner was accusing two green files of silent vacuity, the
  worst thing a test can be, and the total came out 26 short. **The distinction that
  fixes it is in the return value**: `checks` is `None` when no banner was found and
  never 0, because 0 is a measurement ("it ran and asserted nothing") and None is the
  absence of one, and a summing caller must be able to tell them apart. `rc == 0` with
  no banner is **SUSPECT**, never a pass. The controls are what keep the widened
  search honest: a mid-line MENTION of the phrase must not be read as the banner (a
  docstring quoting it would otherwise set the count to 99), a genuine `(0 checks)`
  must survive as 0, a malformed count is SUSPECT rather than silently 0, and a
  non-zero exit is FAIL even when a banner is present, because `checks.py` prints the
  banner before the verdict on some paths so the exit code is the authority.
  Discovery is a WALK and not a glob, with a fixture holding a test one level deeper
  than `toolkit/*/test_*.py` reaches and a `__pycache__` copy that must not be run.
  The cross-check is against a DIFFERENT SOURCE — the disk walk against a scan of
  CLAUDE.md, sharing no code — with a non-empty guard first, because two empty sets
  compare equal. And `--only` matching nothing exits 2: "no tests matched" with exit 0
  is a green run over nothing, which is this repo's oldest defect. **Section 6 covers
  DEFECT 4, which is about wall clock rather than counting**: serial, this suite
  measured 2,794 s over 94 files on 2026-08-14, and `toolkit/test_scrub.py` was 584 s
  of it — while sorting near the END of the alphabet, so a pool fed in path order
  starts its longest file last and idles behind it (~14 min instead of ~10). The
  runner schedules longest-known-first from a gitignored `.suite-timings.json`, and an
  UNRECORDED file goes first rather than last, because an unmeasured cost that turns
  out to be large must not become the tail. The load-bearing check is that the
  schedule is a **permutation** — a scheduler that drops a file makes the suite
  quietly smaller and the run FASTER, which reads as success and is the same defect as
  (1) from a third side — and both cache-read failures (missing, corrupt) must yield
  `{}`, because a malformed HINT must degrade the packing and never stop the run. No
  **Section 7 is `--since`, the only feature in the runner that can make the suite
  SMALLER**, so both of its failure modes are reproduced rather than reasoned about.
  Under-selection is the dangerous one — a fast green run over exactly the code that
  moved — and over-selection is the one that makes the feature pointless, which is how
  it gets switched off. Dependencies come from a real graph: `ast` imports, plus SPAWN
  edges, because `test_handshake.py` does not import `authsrv.py`, it launches it as a
  subprocess, and an import-only graph leaves it unselected when the server changes.
  **Spawn edges are read from non-docstring string literals, and the docstring control
  is what keeps that honest**: scanning raw source text instead put a one-decoder
  change at **90 of 94 tests** (MEASURED 2026-08-14, this repo cites modules in prose
  constantly); restricting the scan put the same change at 22. The refusals are the
  other half — a `content/*.toml` or `CLAUDE.md` change ESCALATES to the full suite
  rather than guessing, because those are read at run time by tests that never import
  them and no graph can see the edge; one such file among Python ones still forces the
  full run; and a diff git could not produce is a full run, not an empty one, which is
  why `changed_since` returns `None` and never `set()`. **The exit rule is a pure
  function so it can be checked without spawning 94 processes to learn it**: green AND
  complete is the only 0, green-but-partial is 3 — `--only` included, which always was
  a partial run and exited 0 for as long as the runner existed — and a failure
  OUTRANKS partiality, because 3 on a run with a red file hides the failure behind a
  caveat. No vault, no socket, no client; the halves under test are pure functions
  over a string, a tree and a dict, so testing the thing that runs the whole suite runs
  none of it — section 7 builds a synthetic `toolkit/` and the one check that touches
  a real repo only asks git to reject a bogus ref. **DEFECT 5 is in section 1**: a
  failing test whose entire explanation goes to STDERR was reported as
  `FAIL … (no output)`, which names nothing and sends the reader to run the file by
  hand — `test_movement_fidelity.py` exits 1 with a completely empty stdout when it
  refuses to pool two client builds, and that is how it read on 2026-08-14. The note
  now falls back to stderr, with a control that stdout still wins when it has a line:
  stderr is a fallback, not a louder channel. The banner search stays on stdout alone,
  because a verdict line is stdout by construction. 49 checks, ~2 s),
  `toolkit/test_srclint.py` (every `toolkit/` file, for a name a function reads that
  nothing could have bound: `ast.parse` and the whole suite passed a `NameError` into
  a live session on 2026-08-10. It also pins the checker's own vacuity failure — the
  first version treated every function local as a module binding and scored the real
  defect zero. **And since 2026-08-12 it checks THIS LIST against the tree, both
  directions**: a `test_*.py` under `toolkit/` that no line here names, and a name
  here with no file behind it. The rule was written down from the day the list
  existed and enforced by nothing — it names three tests that went unrun for days —
  and on the day the check was added a runner reported `51 of 51 green` over a tree
  holding 52 test files, which is the same defect from the other side and worse,
  because the count was self-consistent),
  `toolkit/test_scrub.py` (the credential scrub, that no secret survives it, that the
  one field it CANNOT clean — a `plain` frame payload, which carries the account email as
  UTF-16 and is therefore invisible to the ASCII leak check — is reported rather than
  silently passed through, and that its record arithmetic is pinned to a snapshot so a
  live server appending to `vault/captures/` cannot make it disagree with itself, and
  -- since 2026-08-13 -- that `vault/state`, the portal's issued-session store, is
  EXCLUDED BY CONSTRUCTION rather than merely unwalked. Five cleartext records sat
  outside the scrub root, each with an `email`, a 36-character `user_id` and a
  36-character `token`, and the trap the shape carries is that `sessionstore.issue()`
  keys the map BY THE TOKEN, so the credential is present twice and only one of the
  two is a value -- a scrubber that reused `scrub_record` alone emits a record whose
  `token` field reads `tokn1xxx...` under a key that is still the real token, with
  every record-level check green. That sabotage is built and run and reddens three
  checks including the leak check. Nine sabotages in total, all nine red against a
  green baseline, and the two that earn the sections are the paired ones: a scrub that
  BLANKS every field passes the leak check perfectly and is caught only by the positive
  control that `issued_utc` survives byte-identical, and section 10's positive control
  is GREEN under a deleted `state/` refusal and RED under a refusal that matches
  everything -- either alone would be satisfied by the wrong tool. The race answer is
  deliberately NOT a `Snapshot`: `sessionstore._write` replaces the whole file via
  `os.replace` and prunes 200 records to 100, so a legitimate rewrite SHRINKS it and a
  size pin would report the server doing its job as corruption; `audit_state_text` is
  pure over a string, the file is read once, and the harvest and the census both come
  from that one read. Sections 9-11 are synthetic throughout and need no vault; the
  only claim about the real store is that its census carries no value out of it.
  **Section 12 (2026-08-14) is the CAPTURE path's missing report, and it is the
  `plain` defect's shape one level up.** `scrub_state_json` has counted and NAMED
  the fields it does not recognise since it was written; `scrub_record` had no
  such report, so any unlisted key fell through its trailing `else` and was
  copied verbatim with nothing counted and nothing said. `record_field_is_handled`
  existed and only the STATE path called it. It was found by a field this repo
  added itself -- `marks.py` writes operator marks as `{t, kind, text}` and `text`
  is a free-text line a human types during a live session. **MEASURED over the
  real vault: 57 fields, 1,219,853 values**, among them `key`, `keys`,
  `key_from`, `user_agent`, `cipher`, `blob`, `header`, `tail`, `name`, `label`,
  `values`, `host`, `peer`. `KNOWN_BENIGN` is the structural subset and is
  deliberately NOT everything that occurs -- the payload-shaped and free-text
  names are LEFT OFF so the first run reports them, since a list that blessed
  them on sight would restore the silence it replaces, and the sabotage that
  pads the list is built and run to prove the list is load-bearing. Copying is
  still the behaviour, because inventing a cleaning for an unclassified field is
  worse than reporting it; the report carries NAMES ONLY, on the module's own
  rule that a manifest quoting the value would be the leak itself, and that is
  asserted. Two positive controls keep it from becoming noise: an all-structural
  record must report NOTHING, and a SECRET or OPAQUE field must not be counted as
  unrecognised. Section 12 is synthetic throughout.
  **All 57 were then CLASSIFIED by reading each field's PRODUCER**, and the three
  names that looked worst were the three the read defused: `key` is a KEYBOARD
  KEY NAME (`session.py`:823), `key_from` is a LABEL naming which keyring entry
  decrypted a channel (`livesession.py`:432), and `user_agent` is one fixed
  18-character string in all 862 occurrences. **`values` is the one that looked
  genuinely dangerous and was MEASURED instead of assumed** -- 16,428 strings on
  opcodes including PORTAL_ACCOUNT_LOGIN, SEND_COMPUTER_HASH and
  CHANGE_PLAY_CHARACTER, and **0 of the 5,565 secrets this tool already
  recognises appear in it** over 53,794 records, so the existing leak check was
  right and the alarm was wrong. It stays REPORTED anyway, with `error`, because
  machine fingerprints and a character name are on nobody's list and silencing
  them would decide that by omission. 57 fields became 3. The rest split three
  ways: structural (silent), payload-shaped (`OPAQUE_KEYS`, counted), and
  NETWORK endpoints (their own `NETWORK_STAT`, counted -- the owner's LAN address
  rides in them and the live capture FILENAMES carry it anyway, so cleaning the
  field alone would be a comfort rather than a control).
  **Section 13 exists because that widening was a REGRESSION and it was caught
  rather than shipped**: `leaked()` strips `OPAQUE_KEYS` before searching, so
  growing that tuple from 2 entries to 8 widened the leak check's blind spot by
  six fields and the suite went green MORE EASILY -- the direction a weakening
  always shows up in. So the exclusion is measured per field: search the tree
  UNFILTERED and diff against `leaked()`. All six new fields hide **0**, and the
  positive control is that the exclusion IS hiding something -- **32 values in
  `payload`**, the DH numbers that cross the wire in the clear -- because six
  checks reading zero with a broken search would look identical. The first
  version of that section was O(secrets x values), 5,565 against ~1M, and did not
  finish. **Section 14 (2026-08-15) is why this file is no longer the slowest in the
  suite.** The leak search was still O(secrets x text) — 6,716 secrets against 179 MB,
  in three places, and always in the WORST case, because a green run finds nothing and
  so no scan ever exits early. `search_all` reduces it exactly rather than
  heuristically: a secret is built from some alphabet, so any occurrence lies wholly
  inside a maximal run of those characters; collect the DISTINCT runs, join them with a
  separator outside the alphabet so no join can manufacture a match, and search that
  (1,193,853 runs, a 19.5 MB haystack from 179 MB). **584 s → 183 s.** Because this is
  an optimisation of a security check, section 14 proves it equal to the naive
  comprehension rather than asserting it — five shaped cases, the load-bearing one
  being a secret EMBEDDED inside a longer token, which a tokenising search would miss
  and which is exactly what a half-working scrubber leaves; a secret spanning two runs
  that must NOT be reported; and agreement on the real 179 MB corpus. Two rejected
  approaches are recorded in the docstring so they are not re-tried: a single compiled
  alternation of all 6,716 secrets is SLOWER than the naive loop (9.4 s vs 3.8 s for
  200 patterns), and a per-file search cannot answer the cross-file question
  `leaked()` exists to ask. 78 checks against a floor of 76, the two `vault/state`
  ones declaring a skip; there is no bare-machine shape to floor separately, since
  `main()` opens with `require_dir("captures")`. ~3m),
  `toolkit/test_content.py` (the content store, that its provenance and licence
  refusals actually refuse -- and, since 2026-08-13, that the REAL `vault/content/`
  overlay loads, which is the one input this file never read. Every other check in it
  passes `vault_dir=""` or a temp dir, and the bare `content.load()` it opened with was
  a fixture rather than a claim, so when the overlay shipped **2,077 effect rows citing
  an extractor that had not been committed**, `_check_extracted` refused them correctly,
  `content.load()` raised for the server, the harness and `deploy.py` -- and this file
  did not go red. It DIED at the first line of `main()` and printed no verdict, no
  ledger and no floor shortfall, which is the one failure `checks.py` cannot see: "a run
  that measured nothing failed" cannot fire in a process that never reaches its verdict.
  The load is now guarded and the failure is a named check. Which of the four new checks
  are load-bearing was MEASURED by four sabotages, and the two that earn the section are
  the ones the pre-existing checks SURVIVE: deleting the extractor reddens 3 while both
  synthetic overlay checks stay green, and emptying the overlay reddens exactly 1;
  gutting the existence check and dropping the vault from `load()`'s directory list are
  caught synthetically too. The same sabotage found the pre-existing check next door
  crashing rather than reddening -- `World.get()` RAISES on a missing key, so a dropped
  overlay killed the section at its third check and the two after it never ran. What the
  contribution check CANNOT decide is stated at the call site rather than implied by its
  label: it is a total, so one file of several renamed aside does not move it, and there
  is nothing tracked to check a per-file expectation against. **And the mutation target
  is chosen by PARSING for a source in `EXTRACTED`, never by grepping for
  `extractor = "`**, because an extractor on a row outside that set is INERT -- `capture`
  rows carry the field and nothing validates it -- so the grep version picked a row with
  no condition-1 claim to break, got no refusal, and reddened naming the gate while the
  gate was fine. It did that within minutes of landing, when a parallel session removed
  `effects.toml` and left `npcs.toml`, whose rows are all `capture`; the honest answer
  there is the skip it now declares. Floor 39, the MEASURED vault-less score; 40 on an
  overlay with no extracted-source row, 42 with one),
  `toolkit/test_contentids.py` (the pre-flight that a run's TWO archives agree
  about what `content/maps.toml`'s file ids NAME. **A file id is archive STATE,
  not a property of the map** -- bit 31 means `FcArchive` renamed that row away
  pending a replacement, so the same map is `0x8001B97D` in one copy and
  `0x1B97D` on a different row in another, and both are right for their own copy
  (`studies/maprows/FINDINGS.md` §8). The server reads one archive for the
  navmesh and the client opens its own for the geometry, and nothing checked they
  matched. **THIS FILE'S SUBJECT HAD THE BUG IT WAS WRITTEN TO CATCH, fixed
  2026-08-14:** `contentids` asked `archive.file_id_table()`, which registers a
  bit-31 id under BOTH spellings, so it cleared a pair whose client could not
  bind the id at all -- it printed `10 of 10 agree` and the run died at
  `Code=007`. The client's lookup is an EXACT 32-bit compare with no masking
  (`0x0047AA20`), so the client's half now reads `file_id_table(..., raw=True)`
  while the SERVER's half keeps the masked table, because that is what our own
  reader really does -- measured, not assumed: the gamesrv log resolved
  `navmesh 0x1B97D` against an archive binding only `0x8001B97D`. **That
  asymmetry is the fix and §1b is its regression guard**; reverting the one
  `raw=True` reddens 7 checks. The POSITIVE CONTROL is what earns the file and it
  is not synthetic, but it MOVED: it was `vault/run-live/`, and as of 2026-08-14
  both run-live copies bind every content id plainly, so that control had gone
  vacuous. It is now found by PROPERTY -- any `vault/run/` archive that fails to
  bind a content id raw -- which today is the 38797-era copy, the exact pairing
  that died at `Code=007`. The check must go FATAL on EXACTLY the two Pre-Searing
  rows while the other eight stay green -- a guard that reddens on all ten says
  nothing. §2b states, rather than assumes, that the DEFAULT server pairing is
  cross-generation and correctly refused (point `RURIK_DAT` at a same-generation
  archive to run). `default_client_dat()` now mirrors
  `drive_client.newest_run_exe()` by mtime instead of taking the alphabetically
  first directory -- those were different archives AND different answers, so the
  pre-flight was auditing a copy no run was going to open. Identity is the MFT
  entry's size and crc, never the row, because row
  indices do not survive a patch; a one-bit crc mutation must be caught, since
  two archives resolving one id to different FILES is worse than a failed launch
  (the run produces data and looks like it worked). Section 4 asserts the
  LOOPBACK GATE on the syntax tree -- a live run answers to ArenaNet's own ids
  and must never be refused on our rows, and "the call is inside the RUN_ROOT
  branch" is invisible to a grep; the sabotage that removes the gate reddens it
  alone. **Floor 12, deliberately BELOW the healthy score of 23**: §1b, §2 and
  §2b all need the vault to hold an archive that is mid-replacement on a content
  id, which is a condition we want to go away -- a floor of 23 would turn a
  HEALED vault into a red suite. The mandatory core is §0+§1+§3+§4. **§5, added
  2026-08-15, pins the SCOPING**: `preflight(served=...)` narrows what is fatal
  to the maps a run actually loads, because the guard's own rationale is per-map
  and refusing a map-449 run over map 148's row had blocked EVERY loopback run
  in the repo -- this file's own docstring names that cost ("one that refuses
  everything gets deleted the first time it blocks a run"). §5 is SYNTHETIC, so
  unlike §1b/§2/§2b it can never skip and joins the mandatory core, taking the
  floor to 19. The check that matters most is the fail-closed one: an EMPTY set
  must refuse exactly as `None` does, because a caller whose `--map` parse came
  back empty must not thereby clear the whole table. Out-of-scope disagreements
  are demoted and PRINTED, never hidden, and returned with level `fatal`
  intact. ~10 s),
  `toolkit/test_quests.py` (the quest table and the coded string its prose goes
  on the wire as. Asked for by name in `studies/quests/FINDINGS.md` §7.9, whose
  reason is the one CLAUDE.md opens with -- a quests table with nothing checking
  it is a wish. **Its subject is the first authored PROSE this project has ever
  put on a wire**, and the sharp edge is that a coded string reads a word
  `< 0x100` as a MARKER and `>= 0x100` as a `0x100`-biased varint, so an ASCII
  sentence is entirely sub-`0x100` and is not text to that parser at all --
  §5 asserts exactly that about our own rows, which is what makes `bare` a
  CONTROL PREDICTED TO FAIL rather than a style option. §4 is the refutable
  half: `template` framing must add exactly `0x0BA9 0x0107 … 0x0001` and
  stripping it must return the bare text character for character, because a
  framing that reordered or dropped a unit would still fit the field and still
  pass the width check. §2 does NOT read a provenance field back out of a dict
  -- `rows()` returns rows with provenance already stripped, so that would be a
  decoration; it WRITES a quest row without one and requires the loader to
  refuse it, with the well-formed row as the positive control. §6 breaks each
  refusal on purpose, including the off-by-three where 126 units fit `bare` and
  do not fit `template` -- an error that would only ever show up on screen.
  **What it deliberately does NOT assert is which framing is correct**: only a
  client can say, and asserting one here would be two of our own components
  agreeing and calling it evidence. No vault, no client, no socket, so nothing
  can skip. §7 pins the two field widths APART -- `0x0080`'s dialog line is
  `string16(122)` and `0x004C`'s description is `string16(128)`, six units
  distant, and the check that earns its place is the one asserting a line which
  FITS the description field is REFUSED for the dialog one; a single shared
  constant would pass everything else and put that error where only a screen
  could find it. Floor 17 against a healthy 22, and the derivation is in the
  file: 13 checks are row-count independent and each quest row adds 4 (5 with a
  `giver_dialogue`), so 17 is what the smallest table that can exist executes;
  §0 already catches an empty one. ~2 s),
  `toolkit/test_provlint.py` (an ACCUMULATION TRIPWIRE on assert citations in prose,
  and the story of why it is only that is worth more than the file. `content.py`
  enforced the provenance gate's permitted side from the day it was written; the same
  ruling's refusal of "verbatim assert expressions with their source path and line"
  applied to prose and was checked by nobody, so 134 citations sat in sixteen docs.
  Read literally that made all 134 refusable, and 46 were scrubbed — **and then all 46
  were REVERTED** — before and after the owner asked whether provenance was starting
  to cost more than it protected. **It was**,
  and `PLAN.md` §7 Q3 was refined the same day: **a single assert cited as evidence is
  a MEASUREMENT; the refusal targets BULK dumps and decompiled bodies**, and the crash
  dialog — text the retail client shows any player who crashes — is not extraction.
  This repo's recorded provenance mistakes are REFUSALS, not disclosures. So the 104
  remaining are permitted, `smsg` keeps the 65 quotes that make its opcode naming
  auditable, and the test allows it 85 while an unlisted doc gets 10. The ceiling was
  checked in the direction that matters: a 12-row dump appended to a document that
  argues from none trips it. **The lesson to carry, not the code:** a rule read at
  maximum strictness generated a session of rewrites against negligible risk, and every
  one was a net LOSS once measured — the paraphrases ran longer and dropped the exact
  symbol (`MissionCliIsGameMaster()` became "a game-master predicate"), and four crash
  dialogs became second-hand reports of a primary artifact. Revert cost one command.
  The cheap part — a tripwire with real headroom — was the only part worth keeping. There
  is NO standing obligation to hand-grep for citations the three machine patterns miss;
  a dump is a paste and keeps its format. Section 3 is still the load-bearing one —
  fifteen PERMITTED forms (a location, a bound, a field name, a VA) that must not be
  flagged, because the docs are built out of them. `Module:123` is indistinguishable
  from prose without a vocabulary, so pass 1 harvests one and section 4 pins that
  `Build: 38797` is not a source location while `AgMsg:208` is; the upstream denylist
  is checked in the direction that can do damage, since `MapData` was on it for a
  draft on the strength of GWLP-R's `MapData.scala`. No vault, no socket, no client),
  `toolkit/clientpatch/test_cage.py` (the launch gate: which binary may be aimed at
  which server, both directions — slow, ~1 min, it queries the Windows Firewall once
  per client),
  `toolkit/clientpatch/test_dhbuild.py` (whose DH a build carries, that hostile
  filename order can no longer pick the wrong one, and that a build cannot be
  assembled into the directory meant for the other kind),
  `toolkit/clientpatch/test_keytap_patch.py` (the R0b key-tap code cave: build_cave's
  edges resolve, the planted client changes only the tap and the cave, and the patcher
  refuses a changed or already-tapped binary),
  `toolkit/clientpatch/test_footprint.py` (PLAN A2's compass-footprint patcher: the two
  rects at `s_missionClientData[map]+0x48`/`+0x58` that the `0x0199` map-type byte picks
  between, and whose ORIGIN decides which part of the continent atlas a map's compass
  crops. The read is pinned against an INDEPENDENT reader -- `consttable.Table.record`,
  what `maprows.py` and the whole minimap arc used -- because the failure this file
  exists for does not raise: `Table.base` is already a FILE OFFSET, the first `locate()`
  treated it as a VA and ran it through `rva_to_off`, and it printed four plausible
  int32 from 0x400B90 bytes short. Containment could not catch that, since containment
  only asks whether the bytes that moved sat inside the range it was TOLD to write --
  so `sane_rect` refuses the exact garbage tuple that bug produced, and is checked to
  ACCEPT the real rect so it is not a predicate that refuses everything. Also: writing
  rect A leaves the adjacent B untouched, the output guard refuses the input itself,
  `C:\gw` and every checkout while PERMITTING the vault, and the guard is asserted on
  the SYNTAX TREE to be called exactly once from `main()` -- a guard that exists and is
  never called being the failure `test_atex.py` §3 names),
  `toolkit/clientpatch/test_reskin.py` (the profession reskin -- repointing a SHIPPED
  profession's name string ids, which `studies/profession/RESKIN.md` chose over adding a
  twelfth id because `.rdata` has zero slack and seven of the profession tables are
  `mov imm32` ladders rather than data. Four tables are located STRUCTURALLY, never by
  address: each `.rdata` one by the assert expression the compiler emitted immediately
  after it (each occurring exactly once) and then corroborated by shape, with the
  ANCHOR AND THE SHAPE REQUIRED TO AGREE -- five negative controls break one assumption
  each and must be refused alone, including a duplicated anchor, a missing one, and an
  ambiguous match on the fourth table, which is the `.data` one read at `0x004D128E`
  with NO bound check at all and therefore the most dangerous edit here. The headline
  is deliberately NOT "4 bytes changed": that was this file's first version and it went
  red for the right reason -- 2048 to 2041 is `00 08` to `F9 07`, so the high bytes are
  zero in both and only TWO bytes move. How many bytes a dword write disturbs depends
  on the values, so the invariant is CONTAINMENT (every changed byte inside the intended
  dword) plus a read-back, since containment alone also passes a write that changed
  nothing. The output guards refuse in-place, `C:\gw`, and EVERY checkout of this repo
  (a worktree root is not the main checkout's -- it reports 2), each with a positive
  control that an ordinary path is allowed. Sections 0-2 build their own buffers and
  need no vault; section 3 skips without one. Since 2026-08-13 it also covers the
  ATTRIBUTE table (`s_attrib`, located by the source path that follows it; the
  primary-marker verb is SYMMETRIC because a set-only one would leave two primaries
  on a profession, a state the client never ships), the SKILL roster (two
  single-byte fields, with a check that NOTHING outside the targeted bytes moves --
  a stride error would smear edits across neighbouring rows and still pass a spot
  check), and the RECIPE file, where a profession design is versioned as numbers
  only so no ArenaNet text enters the tree. ~2 s),
  `toolkit/harness/test_accounts.py` (the account selector, and that the primary is
  refused),
  `toolkit/harness/test_marks.py` (the pre-registered operator-mark channel — §10.5.1's
  {t, kind, text} writer on `wire.jsonl`'s own clock, which two studies call a
  precondition for the next live run. Its criterion is that a mark taken at a segment's
  instant lands on THAT SEGMENT'S own `t`, against a capture the REAL `wirecapture.
  open_capture` wrote — two modules, two epochs, one answer, and nothing this file
  computes can force it. **Every headline here is a number a broken version also prints**,
  so 25 one-edit sabotages of `marks.py` and 5 of `wirecapture.py` were BUILT AND RUN; all
  30 redden, thirteen redden exactly ONE check, and the file's floor comment names each.
  The three that earn the file are the three a skeptic passed with **all 139 checks green,
  exit 0**: `self.user32["Send" + "Input"](...)`, `attrgetter("Send" + "Input")` and an
  ALIASED subscript — working keyboard writers on a real `ctypes.WinDLL`, past the very
  control CLAUDE.md's live-automation rule turns on, because detector 3 scanned
  `ast.Attribute` off a base spelled `user32` and matched `getattr`/`setattr` by name. The
  scan was widened (subscripts, aliases, 20 dynamic-lookup spellings, a `"<computed>"` key
  that can never be whitelisted) but the answer is the CAPABILITY: `Hotkeys.__init__` now
  BINDS its four functions and lets the handle go out of scope, and the check is on the
  OBJECT — a scan says what it noticed, a class with no handle says what exists.
  **Three constants were free to move the same way**: `VK_F9/F10/F11` were compared
  against the module's own symbols, so a `marks.py` taking GLOBAL hotkeys on ESCAPE,
  ENTER and SPACE — swallowed away from Guild Wars for a whole session — passed
  everything, and even the refusal message relabelled 0x1B as "VK_F9". They are literals
  now, with the binding ORDER beside them. `test_agentlife.py`'s twelve-of-fourteen, in
  the file that cites it twenty lines earlier. **The module was also a writer with NO
  destination guard**: one `open(self.path, "w")` off argv, zero guard calls, and `--out`
  at a 4,096-byte file named `Gw.dat` replaced it with 533 bytes before the first mark —
  `atex.py --make C:\gw\Gw.dat` in a new module. Four refusals now (the owner's install,
  `vault/dat_study` before the vault allow, EVERY checkout, and any path that ALREADY
  EXISTS), each with a positive control, and the syntax tree is asked whether
  `resolve_out` runs BEFORE the `open`. **The check that tests that guard wrote into the
  tree**: aimed at the TEST's `HERE` rather than the module's own `working_tree_roots()`,
  it created `toolkit/harness/plan_marks.jsonl` on 24 sabotage runs — the exact write the
  guard exists to prevent, through the check that tests it. **Five hotkey leaks are
  measured, not argued**, against a fake keeping its OWN OS-side ledger: `RegisterHotKey`
  RAISING (the branch only fired on a falsy RETURN and the `atexit` hook went on AFTER the
  loop, so there was no net at all), the same through `with Hotkeys()`, Ctrl-C mid-loop,
  `UnregisterHotKey` returning 0 (discarded — and a real one returns 0 with WinError 1419
  on a key that is still held), and Ctrl-C INSIDE teardown, where `except Exception` misses
  the BaseException and the id had already been popped so `atexit`'s retry could never
  reach it. The backstop under all five is now MEASURED: a hard-killed process releases
  VK_F24 at +0.0 s, with a live 1409 control while it lived. **The clock claim was two
  witnesses restating each other.** `t_perf` and `t_wall` are sampled adjacently in ONE
  process, so their difference only ever measures the OS-wide (QPC − system time) offset
  against itself — a capture whose published epoch was 0.9 s off the epoch its segments
  were stamped from BOUND, with both channels reporting 0.0001 ms of skew — and 0.250 s is
  ~50,000x the phenomenon it is named for (two processes agree to 5 µs over 12 spawns,
  drifting at −0.004 ppm). So `wire_t` is restored as the THIRD channel, the only one on
  the segment axis; the boundary is pinned at 250 ms binds / 250.001 ms refuses, because
  any value in (0.249, 0.600) used to leave every behavioural check green; the marks
  file's own epoch sits 31 s after the capture's, because with them equal a binder reading
  either epoch from the WRONG FILE passed 139 green; and the diagnosis grew a third word —
  fed one +0.5 s wall step it answered "a stamping fault at those marks" (it was one clock
  event) AND "it is a RATE" (it was a step), the two hypotheses it could express, both
  wrong. **And a mark an HOUR after a capture that ended at t=12.0 bound silently**, which
  is reachable because the sniffer has a `--seconds` ceiling and `livesession` keeps the
  session going when it dies: disjoint is now REFUSED, a partial overlap is REPORTED,
  because "the network went quiet" and "the sniff stopped" are not separable from the
  artifact. The readout's own vacuity is fixed too — zero marks printed "worst |dperf −
  dwall| = 0.0 ms", a run that measured nothing reporting the best possible measurement.
  **The failure MODE was the structural problem, not coverage**: of 109 sabotages against
  the old file, twelve died with a traceback at checks 17–126 and FOUR HUNG past 120 s —
  no banner, no ledger, no floor line, so the declared floor was unreachable as a guard
  and any one of four one-line defects in `run()` blocked the whole suite. `guarded()`
  turns a section crash into a NAMED failing check and `BoundedHotkeys` bounds the one
  call `run()` makes every pass, so all four are red now and the floor prints its
  shortfall. Four `any(got)` rows were DELETED as strictly weaker restatements of the line
  above them — a check that cannot fail independently is floor, not coverage. No vault, no
  socket, no client, no Windows: every hotkey check runs on a fake `user32` and every
  clock is injected, which is the shape `test_keytap.py` could not have. 179 checks
  against a floor of 179; ~1.2 s. **`bind()` has still never run against a byte ArenaNet
  sent** — `wire_epoch` refuses all ten `wire.jsonl` in the vault, and not for the reason
  the refusal used to give: measured, every one carries NEITHER epoch, because `t0_wall`
  landed 2026-08-11 and the newest live capture is 2026-08-10),
  `toolkit/harness/test_keytap.py` (the ReadProcessMemory key reader — RPM round-trip,
  ASLR-correct module-base resolution, cross-process, and a clean failure on an unmapped
  address; Windows-only, skips whole otherwise),
  `toolkit/harness/test_wirecapture.py` (the off-wire ciphertext capture's pure half:
  IPv4/TCP parse, direction from endpoints, TCP-seq reassembly that reports gaps rather
  than hiding them, a capture that reads back stamped `origin: live`, an honest
  refusal when WinDivert is absent — and the live shape: direction decided by port when
  the server's address cannot be known in advance, several connections kept on separate
  sequence spaces, and the single-stream reader refusing rather than merging them),
  `toolkit/harness/test_livesession.py` (the live driver's offline half and guards:
  splitting the plaintext handshake off a wire stream and decrypting the rest — grounded
  on a real session's own ciphertext, reached from the wire side — a both-direction
  `assemble` that self-checks and stamps `origin: live`; `assemble_live` pairing a keyring
  to several connections and, the one that matters, decrypting nothing and writing no file
  when the right key is absent; and that the guards refuse the primary account, an ours-DH
  client aimed live, and a run with no `--confirm`),
  `toolkit/test_origin.py` (whose server a capture came from, and that ours and
  ArenaNet's can never be pooled — **and since 2026-08-13 which BUILD, which is
  the same argument one level down**. `HANDOFF.md`:237 has required a build id in
  every capture manifest since day one and `origin.py` carried no build field at
  all; that was survivable only while there was one build, and `MOVE_TO_COORD` is
  `0x003C` in one client and `0x003E` in another, so a figure pooled across two
  is about neither. `build_of` mirrors `origin_of` including the part it learned
  the hard way: a build stated on the origin record is CHECKED against the file's
  own `version` record and REFUSED when they disagree, because a stamp nothing
  checks is an unfalsifiable self-declaration. `BUILD_UNKNOWN` is a distinct third
  value, never "probably the pinned one", and `require_single_build` refuses a
  two-build corpus — `test_movement_fidelity.py`, the pooling consumer, calls it.
  **And since 2026-08-15 it also SELECTS, which is the half a refusal cannot
  supply.** The refusal fired for real the day after build 38833 shipped: its
  verification runs left genuine 38833 captures in `captures/authsrv/`, and both
  pooling consumers went red. Correctly — but a red states a fact about the vault
  (two builds are present) when what a reader needs is a policy (which build the
  figure describes), and a test cannot settle a policy by failing at it. Owner's
  decision: **the figures follow the pin**, so `origin.select_build(paths, build)`
  keeps the pinned build plus the unstamped files, drops anything stamped
  otherwise, and returns what it dropped so the caller can print it. The build is
  an ARGUMENT — `origin.py` is on the server path and does not import
  `clientscan/pinned.py`; the consumer reads `pinned.BUILD` and passes it, so the
  corpus follows the pin automatically and the two cannot drift. Unstamped files
  are KEPT: "cannot say" is not "some other build", and a strict filter would
  silently discard a third of the evidence. The census asserts the pair that
  actually protects a number — selection leaves one build, **and** the pinned
  corpus survives it, since a filter that keeps nothing also "leaves one build".
  Unknown is TOLERATED by default and that is measured rather than lax: roughly
  **38%** of the research corpus names no build — 930 of 2,464 MEASURED
  2026-08-14, 556 of 1,678 when this was written. Treat the fraction as the
  claim and the absolute counts as a timestamp: the suite writes captures on
  every run, so these moved twice during the session that recorded them and any
  exact figure here is stale by the next green run. It is that high because a
  frame log names the build once
  per SESSION not once per file, so refusing on unknown would refuse nearly every
  real corpus and the guard would be deleted in a week — it may never be silent,
  so the count comes back in the reason, and `allow_unknown=False` exists.
  **The vault census answers what `studies/crossbuild/PLAN.md` §10 left
  UNVERIFIED — no corpus figure pools builds — and is scoped to the RESEARCH
  corpus: `selftest/` is excluded from the walk the way `captures-scrubbed/`
  already is, and since 2026-08-14 that scoping is load-bearing.** Build 38833
  shipped, and the suite's own runs began writing 38833-stamped fixtures into
  `captures/selftest/` — `test_handshake` drives whichever client the newest
  key matches (`studies/crossbuild/FINDINGS.md` §7.7) — so a census over the
  whole vault went red over its own byproducts, and would go red again on every
  future suite run. Two sessions hit that red in parallel and fixed it two
  ways: one NAMED the off-pin files in an allowlist, which the producer refutes
  (the suite itself writes them, so the list stales on every run), and one
  excluded the fixtures, which stands — a self-test artifact is not research
  data, and counting it re-creates one level up the contamination `selftest/`
  was split out to prevent. Two checks survive from the allowlist branch: the
  pooling refusal is EXERCISED on a real mixed pair (the fixtures supply a
  genuine 38833 file, found by reading each candidate's bytes, never by
  filename — a refusal that has never fired on a real artifact is the same
  class of thing as a green test that asserts nothing), and the census's 38797
  is cross-checked against `clientscan/pinned.py` so a moved pin turns the
  census red until it is re-decided rather than silently re-aimed. A REAL
  second-build capture in the research corpus still turns the census red — that
  is the point, not a defect.
  **And the scoping was checked against the thing it protects, not just made
  green:** the pooled consumer never saw the selftest files in the first place —
  `game_channel_captures()` globs only `captures/authsrv/` and
  `captures/gamesrv/`, never the whole tree, and calls `require_single_build` on
  top, so it would still refuse a real mixed corpus. Scoping a census green and
  the contamination being absent are different claims and only the second one
  matters. (Noted while checking it, and undesigned rather than argued: the two
  censuses in this file walk with DIFFERENT exclusions — the origin census still
  counts `selftest`, 2,782 files against the build census's 2,464. Harmless
  today, because a selftest capture really is ours and the ours/live claim stays
  true, but it is the kind of asymmetry to settle before leaning on either
  count. Both figures MEASURED 2026-08-14 and both drift per the note above; the
  ~320-file gap between them is the durable part.) A vault-less
  run scores 23 against a floor of 23, measured with `RURIK_VAULT` pointed at an
  empty directory rather than derived by subtraction; a vault run scores 30),
  `toolkit/authsrv/test_castcycle.py` (the four-opcode cast cycle against
  ArenaNet's own template — six complete cycles, two live captures, same order
  every time: E4 at the press, E5 at cast end carrying the recharge in whole
  seconds, E3 an aftercast later, E6 at E5+recharge to within 13.7 ms on all
  six. The section that earns the entry is the QUEUE LAW: skill 105's two
  cycles both exceed its 2.0 s activation by exactly the previous cast's
  remaining aftercast, so E4 fires at accept but the cast begins when the
  caster FREES — the naive press+activation model is refuted by +0.64 s and
  +0.57 s residuals in the corpus, and the test drives two back-to-back
  presses through exactly that schedule. Timing is tested by REWINDING the
  pending entries, never by sleeping; the zero-recharge inversion pins that
  E6 waits for its E3 because the corpus never shows them inverted; and the
  real-content section presses skill 153 and requires E5 to carry recharge 8,
  the value ArenaNet's own wire echoed — it SKIPS loudly on a machine with no
  vault overlay, where sections 1–3 still run on a stubbed skill_timing),
  `toolkit/authsrv/test_killwindow.py` (the kill window, checked against
  ArenaNet's own kills. Our server sent one message when an agent died —
  `0x00F1` with the death bit — where the real service sends three: status,
  then a `0x00EE` reward, then `0x0026` value 8, same tick, same agent. **The
  oracle is the corpus, not a literal**: §2 re-derives the live template out of
  `vault/captures/live/*` on every run, so adding or re-decoding a capture
  moves the expectation instead of leaving a stale constant behind. §1 keeps
  literals only so a vault-less machine still checks something — including that
  the reward encodes to `ee00000000001a000000`, ArenaNet's exact bytes.
  **§3 is what the file is really guarding.** The corpus holds a
  richer-LOOKING template — a `0x00EE` PAIR, `[10,0]` then `[0,X]` — that is
  not a kill shape: 6 of its 7 sightings fire 6.8–31.5 s from any death inside
  a broadcast burst always preceded by `0x009C [agent, 100]`, and the seventh
  landed on the Wolf's kill tick, whose `0x009C` marker is what gives the
  coincidence away. Copying it would have looked like more fidelity and been
  less, so §3 asserts we do not. Two counts here corrected earlier passes and
  are asserted so they cannot drift back: the corpus holds **5 deaths, not 4**
  (agent 38 dies twice on one connection, and the second carries neither
  reward nor flags — a repeated `EFFECT_DEAD` awards nothing), and `0x0026`'s
  histogram over both captures is **{9: 200, 8: 4}**, against an `authsrv.py`
  comment that had called value 8 a single sighting from one capture's count.
  Proven red by setting the reward to the Wolf's contaminated 126. Floor 6, the
  vault-less §1),
  `toolkit/authsrv/test_skilldamage.py` (skill damage: the client's own
  numbers at the player's own rank, replacing `ENEMY_SKILL_FRACTION = 0.25` —
  a flat quarter of the player's maximum for every skill, admitted invention.
  **The sections that refuse are the point.** The client's table gives a
  magnitude and does NOT say what it means: `scale0/15` is `+ Damage` on Power
  Attack and `Healing` on Restore Condition, and `type_code` cannot
  discriminate because a Spell can heal or harm. **Three of the four skills on
  our own enemy's bar are not damage**, so a decode that read endpoints and
  dealt them would have had the enemy "damaging" the player with a heal for
  10–70 and an enchantment for 40–200 — an invention wearing a measurement's
  clothes, and worse than the flat fraction because it would look principled.
  The meaning therefore comes from GWW's own `{{Skill progression}}` variable
  names, quoted verbatim into `content/world.toml` with a per-skill citation;
  §3 asserts the five non-damage skills return **None rather than 0**, and is
  proven red by relabelling Restore Condition's `Healing` as `Holy damage`.
  §1 reproduces both endpoints for four skills — values GWW independently
  lists, so a match is two witnesses rather than our decoder agreeing with
  itself. §2 walks Holy Strike's whole ladder (3 per rank, exactly) and pins
  that rank 20 **extrapolates to 70 rather than saturating**, because the
  client's interpolator never compares rank against 15 and a "sensible" clamp
  is exactly what someone would add. §4 pins that a disabled `skill_arguments`
  bit REFUSES: Rush's scale slot holds 25 — the "move 25% faster" in its
  description — so a decode ignoring the bitfield returns a plausible number
  instead of refusing. §5 proves the **unresolved** rounding tie-break
  (studies/combat 8c: the client adjusts by ±1.0, not ±0.5) cannot bite,
  because no skill in the effect table lands on a .5 at any rank 0–15 — the
  open question is shown to cost nothing rather than assumed to. §6 is the
  chain steps 7 and 8 exist to join: Power Attack reads Strength 12 and
  Desperation Blow reads Tactics 1, identical 10→40 tables landing 22 points
  apart, which is precisely what "the server models no attribute ranks" used
  to cost. §7 asserts a `+ Damage` bonus rides the swing as ONE damage
  message, since two would draw two numbers on screen for one hit),
  `toolkit/authsrv/test_guards.py` (the guard contract for combat's computed
  values: a `_fraction` refusal must land BEFORE any send or state change, not
  after — the client dies on `fraction <= 1.0f` at CharPool.cpp:84 with no
  server-side symptom, and on the connection thread an escaping ValueError
  additionally closes the socket, because `handle`'s except tuple never named
  it. Written RED-FIRST against the pre-guard tree (studies/combat/PLAN.md,
  amendment C8b) and the red run is quoted in the file's docstring: hit_enemy
  with a poisoned out-of-range HIT_FRACTION raised only AFTER
  GV_ATTACK_STARTED was on the wire, the target's health was bookkept
  100 → 0 unsent, and the swing timer was eaten — three FAILs, each now a
  check. Every section carries an in-range CONTROL asserting the real
  constant still sends the full effect burst, because a guard that refuses
  everything would pass every refusal check. Dormant while every fraction is
  a literal constant; load-bearing the day studies/combat step 8 computes
  them from the client's skill table),
  `toolkit/mapdata/test_unitexport.py` (the UNIT body export, rung U5: FA0
  geometry + FA5 textures + the FA1 skeleton SIDECAR through the `.gwmodel`
  interchange (`unitexport.py`), and the Blender viewer measured headless
  (`tools/blender/import_gwunit.py`). The anchors are the burrowing worm
  116366 (FA0 + the 82,169-byte FA1) and the hatcher body 116703 (FA0, NO
  skeleton -- and its export must SAY so, so "old export" can never read as
  "no skeleton"). The models-arc RE-INTERLEAVE holds on both (7/7
  sub-models, test_modelexport's packer imported rather than copied -- it
  shares no code with any module under test); `unit_<id>.fa1.bin` off disk
  IS the archive's 0xFA1 payload byte-for-byte; and every typed skeleton
  value read back off disk -- 10 sequences' lo/hi/start/end/durations, the
  3-entry key table, 20 node links and channel key counts, 6 sound events,
  98 field comparisons -- must equal a FRESH `skelfile.Skeleton` decode of
  the archive bytes, with tamper controls either side proving the
  comparison can fail. The pose that shipped is the FLAT placement, and the
  measurement that makes it the BIND POSE rather than a guess is pinned:
  all 18 channel-carrying nodes' bases fall INSIDE the stored mesh's own
  bbox -- 18 of 20 total; the two channel-less ones sit at the origin,
  outside the mesh's y-range, carrying no positional claim. The U5 review
  measured the statistic's power (rotated bases 1/18, scaled 0/18, the
  hatcher's 1,463 vertices vs this bbox 0/1463) and its limit (a
  component-shuffle passes: cloud occupancy, not per-node correspondence
  -- exactly what is claimed). The spans-tiling check runs on the worm's
  REAL payload too (review RISK-1: five span kinds the synthetic never
  builds; it is rung U6's precondition). No sub-model-to-node binding is
  measured (3 sub-models, 20 nodes), so per-vertex posing would be
  invention, and a COMPOSITED shell (116228) is REFUSED with its MESSAGE
  asserted -- naming the mechanism and rung U4, not a bare raises() that
  cannot tell composited from absent. Section 3 drives Blender as a subprocess and measures
  the SCENE, never an eyeball: counts and bbox against the position sidecar
  (z negated, the M4 convention), all 20 node empties at their RAW bases
  with parent = measured link, and the RENDER -- an orthographic silhouette
  whose alpha coverage must be non-zero where the hidden-everything control
  frame measures EXACTLY zero, and whose pixel WIDTH must match the extent
  predicted from the export's own bbox through the dump's ortho scale,
  +/-4 px (worm 38 vs 36.3, hatcher 120 vs 121.6 -- a 3.35x spread; the
  HEIGHT half is res/1.1 identically whenever the model is taller than
  wide, a framing constant, and is labeled so). The first contact with
  real data paid twice: 18/20 empties were measured OFF their bases --
  background Blender had not evaluated the parent's matrix_world before the
  parent-inverse was taken from it -- and the hatcher's thin silhouette
  refuted the guessed 0.02 coverage floor at 0.0147 -- and that number has
  a measured CAUSE, pinned by the --opaque control: the hatcher's bound
  diffuse texture carries alpha ~0 on 99.9% of its texels and the inherited
  prop convention wires texture alpha as transparency, so the default
  render is a floating head over an invisible torso; --opaque at least
  triples the coverage (0.0147 -> 0.1932), and what the alpha channel MEANS
  on a unit texture stays NOT DECODED with the AMAT chain. Floor 72 from
  the green run (71 -> 72 with the review's real-data tiling check);
  sections 0-1 (synthetics + the resolve_outdir refusal with its positive
  controls and the mapexport delegation check) score 28 vault-less and go
  RED; with the archive but no Blender, 53, also RED),
  `toolkit/mapdata/test_skelwrite.py` (the RE-IMPORT ROUND TRIP, rung U6:
  the FA1/container WRITER
  (`skelwrite.py`): decode -> extract -> encode must be BYTE-IDENTICAL, and
  identity is the criterion precisely because re-parse equivalence cannot
  be -- the walk pins no order between adjacent fixed-size blocks, so the
  test's `swap_n14_n34` writer variant emits output that RE-PARSES GREEN
  (walk closes, every gate passes) while failing identity with the diff
  confined to the two swapped blocks, demonstrated on a synthetic with
  planted-distinct block content (uniform fill would make the swap
  invisible) AND on the worm, whose n14/n34 contents are measured distinct.
  What keeps identity from being vacuous is the memcpy-loader lesson
  (models FINDINGS 4.5) applied writer-side, pinned three ways: a typed
  repr HAND-BUILT from the test's own literals -- never decoded from any
  payload, so a spans-concatenating encoder cannot even run on it -- must
  encode to `synth_anim()`'s exact bytes; the anchors' opaque-carry totals
  are pinned by a RECURSIVE LEAF WALK over every bytes-like leaf in the
  repr (worm 883 of 82,169 B = 1.07%, shell 1,179 of 29,495 = 4.00% --
  the shell is n40-heavy, 620 of its bytes the 62 sound-event raw tails;
  the declared/undeclared split is asserted as exactly 10 x n40 beside
  it. The U6 review struck the first version, which summed the DECLARED
  regions only and so could not catch a writer stashing bytes under a
  new key); and the U7 seam (`scale_sequence_keytimes`, pure int32,
  inexactness and overflow REFUSED, and since the review ATOMIC -- the
  whole span validates before any key commits, with the refusal-then-
  identity check on a two-key span pinning it: the pre-fix writer left
  the shell's seq 16 half-retimed 66666 -> 22222 and still serialized)
  must land its modification at EXACTLY the byte set the value change
  predicts (set equality, not subset) -- worm sequence 2 x2 flips key
  2's int32 slot, at chunk and at container level, and re-decodes to
  the scaled time. U6's
  measured finding is recorded as a pin: header bytes +0x09..+0x0B, which
  the parser never reads, are NOT zero (shell 0x42, worm 0x07; 5,208 of
  14,571 corpus FA1s non-zero, 39 distinct patterns), so the typed layer
  carries them opaque rather than assuming them. Identity runs on both
  anchors plus the container-only hatcher body, a deterministic stride-89
  corpus pass (241/241 containers, 160/160 FA1s, 9 blk48 carriers so the
  typed blk48 repack meets real data), and under `--all` the COMPLETE
  population: 21,420/21,420 containers and 14,571/14,571 FA1s
  byte-identical (MEASURED 2026-08-16, 848 s). Refusals are named `Unwritable`s beside passing
  controls: count/list mismatch, diverged start/end aliases, truncated
  opaque var-array (each opaque block must TILE under its own terms before
  it is emitted), wrong-size pad09, n2C == 0 (the client's own error 12),
  fa1= against a no-FA1 container, non-type-2 ffna -- and an
  n56-carrying synthetic (0 corpus files can exercise that stride) must
  round-trip, in two shapes. Section 3 is the datwrite half with its
  identity levels STATED: serialized chunk/container bytes EXACT;
  decompressed row payload read back out of a REBUILT archive EXACT; the
  STORED form legitimately different (compression 8 x 90,616 B ->
  stored x 129,368 B -- no compression-8 encoder exists, datwrite study
  blocker 2). The rebuilt archive carries the worm's REAL rows
  byte-verbatim in test_datmove's fixture shape at loader-legal indices
  (>= 16): the 515 -> 1 -> 2817 `alloc.nextStream` chain, whose survival
  is the load-bearing check because U7's kill/keep names the untouched
  mid/tail rows as prime suspects -- after the move the chain links, the
  flags, and both partners' bytes are unchanged (the failing control
  corrupts the rebuilt archive's OWN MFT bytes -- root nextStream and
  mid flags -- and requires both faults reported by name through the
  real on-disk layout, the review's upgrade over mutating a parse), the
  file-id table still names the same row, all three checksum rules hold,
  and no two reservations intersect. The recorded WALL is exhibited, not
  just cited: `datwrite.replace` refuses the 129,368-B payload naming
  the relocation, and `datmove` -- the verb built for exactly that
  refusal -- succeeds beside it. The resolve_outdir delegation is proven
  by monkeypatch (patching mapexport's changes skelwrite's answer),
  refutable where the struck docstring-prose check was not. Floor 69
  MEASURED from the green default run (66 pre-review); --all runs 71,
  its two stride-1-only population pins added; vault-less runs execute
  the synthetic sections only, 33 checks plus a declared skip, RED on
  the floor by design -- and the first vault-less run DIED with no
  verdict because `require_dir` raises SystemExit past `except Exception`,
  the exact unguarded-exception failure the models-arc review named, now
  guarded and commented. ~40 s default; nothing outside the vault is ever
  written -- the rebuilt archive and its journals live under
  `vault/exports/unitwrite/`).
